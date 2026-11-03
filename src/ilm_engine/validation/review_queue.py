"""Human review queue (step `review_queue`, ADR-016; Argilla in production).

Items come from every validation result that is not auto-approved and from the issues a person must
look at. Each target gets one `ReviewItem` with all its reasons, its evidence anchors, the blocks to read
and the PDF page. Priority: sensitive (scholar review) → model disagreement → low confidence → needs_llm
→ structural issues; within a priority, lowest confidence first.

`apply_decisions` records reviewer decisions (`review_decisions.json`), enforces the scholar role for
sensitive items, keeps an audit trail and exports approved/edited items as training examples (ADR-015).
Decisions are keyed by the deterministic review ID, so a rerun of the pipeline re-applies them.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.enrichment.models import Anchor, Issue, ReviewDecision, ReviewItem, ValidationResult
from ilm_engine.ids import make_id, natural_key
from ilm_engine.integrity.revision_diff import anchors_in
from ilm_engine.storage.json_store import to_jsonable, write_bytes_atomic

PRIORITY = {"sensitive": 0, "discrepancy": 1, "low_confidence": 2, "needs_llm": 3, "structural_issue": 4}
ISSUE_REASONS = {
    "sensitive_content": "sensitive",  # brings the anchors of the sensitive passage (e.g. a grading footnote)
    "model_disagreement": "discrepancy",
    "ambiguous_entity": "discrepancy",
    "metadata_conflict": "discrepancy",
    "needs_llm": "needs_llm",
    "nested_footnote": "structural_issue",
    "unlinked_footnote": "structural_issue",
    "broken_ref": "structural_issue",
    "unresolved_internal_ref": "structural_issue",
    "numbering_gap": "structural_issue",
    "numbering_duplicate": "structural_issue",
    "toc_without_block": "structural_issue",
    "evidence_not_found": "structural_issue",
    "schema_invalid": "structural_issue",
}
DECISION_STATUS = {
    "approved": "approved",
    "rejected": "rejected",
    "edited": "edited",
    "reprocess_requested": "reprocess_requested",
}
AUDIT_FILE = "review_audit.jsonl"
TRAINING_FILE = "training_examples.jsonl"


class ReviewError(ValueError):
    """A decision cannot be applied (unknown item or insufficient role)."""


def _block_ids(anchors: Iterable[Anchor]) -> list[str]:
    return list(dict.fromkeys(anchor.block_id for anchor in anchors))


def build_queue(
    book: CanonicalBook,
    results: list[ValidationResult],
    issues: list[Issue],
    records: dict[str, Any],
    decisions: list[ReviewDecision] = (),  # type: ignore[assignment]
) -> list[ReviewItem]:
    """The review items of one run. `records` maps target IDs to the record (unit, fact, entity, …)."""
    pub_ref = book.book.pub_ref
    pdf_file = book.scan.get("file")
    pending: dict[str, dict[str, Any]] = {}

    def entry(kind: str, target: str) -> dict[str, Any]:
        return pending.setdefault(
            target,
            {
                "kind": kind,
                "reasons": set(),
                "sensitive": set(),
                "issues": set(),
                "confidence": None,
                "anchors": [],
            },
        )

    for result in results:
        if result.decision == "auto_approved":
            continue
        item = entry(result.target_kind, result.target_id)
        item["confidence"] = result.confidence
        if result.sensitive:
            item["reasons"].add("sensitive")
            item["sensitive"].update(result.sensitive)
        if result.confidence < result.threshold:
            item["reasons"].add("low_confidence")
        if not item["reasons"]:
            item["reasons"].add("low_confidence")  # pending by policy (e.g. inferred relations)
        item["model_outputs"] = result.model_outputs

    for issue in issues:
        reason = ISSUE_REASONS.get(issue.code)
        if reason is None:
            continue
        item = entry(issue.target_kind, issue.target_id)
        item["reasons"].add(reason)
        item["issues"].add(issue.issue_id)
        item["anchors"] += issue.anchors
        if issue.code == "model_disagreement":
            item["model_outputs"] = issue.details.get("model_outputs", [])
        if issue.code == "sensitive_content":
            item["sensitive"].update(issue.details.get("categories", []))
        if issue.code == "ambiguous_entity" and issue.target_kind == "entity":
            item["reasons"].add("sensitive")
            item["sensitive"].add("narrator_disambiguation")

    decided = {decision.review_id: decision for decision in decisions}
    items = []
    for target, item in pending.items():
        record = records.get(target)
        # Issue anchors explain why the item is here, so they come before the record's own anchors.
        anchors = list(
            dict.fromkeys([*item["anchors"], *(anchors_in(record) if record is not None else [])])
        )[:10]
        reasons = sorted(item["reasons"], key=lambda r: PRIORITY[r])
        review_id = make_id("rev", pub_ref, natural_key(target, reasons[0]))
        first = anchors[0] if anchors else None
        decision = decided.get(review_id)
        items.append(
            ReviewItem(
                review_id=review_id,
                target_kind=item["kind"],
                target_id=target,
                reason=reasons,  # type: ignore[arg-type]
                sensitive=sorted(item["sensitive"]),  # type: ignore[arg-type]
                required_role="scholar_reviewer" if item["sensitive"] else "editor_reviewer",
                priority=PRIORITY[reasons[0]],
                confidence=item["confidence"],
                proposed_value=to_jsonable(record) if record is not None else None,
                model_outputs=item.get("model_outputs", []),
                anchors=anchors,
                context_block_ids=_block_ids(anchors),
                pdf={"file": pdf_file, "page": first.scan_page if first else None} if pdf_file else {},
                issues=sorted(item["issues"]),
                status=DECISION_STATUS[decision.decision] if decision else "pending_review",  # type: ignore[arg-type]
            )
        )
    return sorted(
        items, key=lambda i: (i.priority, i.confidence if i.confidence is not None else 1.0, i.review_id)
    )


def load_decisions(path: Path) -> list[ReviewDecision]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ReviewDecision.model_validate(item) for item in data]


def apply_decisions(out_dir: Path, decisions: list[ReviewDecision]) -> dict[str, int]:
    """Apply reviewer decisions to `out_dir` (review_queue.json): status, audit, training export."""
    queue_path = out_dir / "review_queue.json"
    items = {item["review_id"]: item for item in json.loads(queue_path.read_text(encoding="utf-8"))}
    for decision in decisions:
        item = items.get(decision.review_id)
        if item is None:
            raise ReviewError(f"unknown review item {decision.review_id}")
        if item["sensitive"] and decision.reviewer_role not in ("scholar_reviewer", "admin"):
            raise ReviewError(
                f"{decision.review_id} is sensitive ({', '.join(item['sensitive'])}): needs scholar_reviewer"
            )

    audit, training = [], []
    for decision in decisions:
        item = items[decision.review_id]
        before = item["status"]
        item["status"] = DECISION_STATUS[decision.decision]
        audit.append(
            {
                "review_id": decision.review_id,
                "decided_at": decision.decided_at,
                "reviewer_id": decision.reviewer_id,
                "reviewer_role": decision.reviewer_role,
                "decision": decision.decision,
                "old_status": before,
                "old_value": item["proposed_value"],
                "new_value": decision.new_value,
                "reason": decision.reason,
            }
        )
        if decision.decision in ("approved", "edited"):
            output = decision.new_value if decision.decision == "edited" else item["proposed_value"]
            provenance = (
                (item["proposed_value"] or {}).get("provenance", {})
                if isinstance(item["proposed_value"], dict)
                else {}
            )
            training.append(
                {
                    "task": item["target_kind"],
                    "review_id": decision.review_id,
                    "source": "human_review",
                    "input_block_ids": item["context_block_ids"],
                    "input_text": [anchor["quote"] for anchor in item["anchors"]],
                    "evidence": item["anchors"],
                    "output": output,
                    "decision": decision.decision,
                    "reviewer_role": decision.reviewer_role,
                    "prompt_version": provenance.get("prompt_version"),
                    "model_id": provenance.get("model_id"),
                }
            )

    ordered = sorted(
        items.values(),
        key=lambda i: (
            i["priority"],
            i["confidence"] if i["confidence"] is not None else 1.0,
            i["review_id"],
        ),
    )
    write_bytes_atomic(
        queue_path, (json.dumps(ordered, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    )
    previous = load_decisions(out_dir / "review_decisions.json")
    merged = {d.review_id: d for d in [*previous, *decisions]}
    payload = [d.model_dump(mode="json") for d in sorted(merged.values(), key=lambda d: d.review_id)]
    write_bytes_atomic(
        out_dir / "review_decisions.json", (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    )
    _append_lines(out_dir / AUDIT_FILE, audit)
    _append_lines(out_dir / TRAINING_FILE, training)
    return {"applied": len(decisions), "training_examples": len(training)}


def _append_lines(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    existing = path.read_bytes() if path.is_file() else b""
    lines = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode(
        "utf-8"
    )
    write_bytes_atomic(path, existing + lines)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
