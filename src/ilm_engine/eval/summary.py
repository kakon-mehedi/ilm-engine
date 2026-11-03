"""Run summary `output/<pub_ref>/SUMMARY.md`: what one run produced, in one readable page.

Reads the run's own outputs (enrichment, annotations, review queue, run manifest) and, when present,
`eval_report.json` (T-131).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ilm_engine.storage.json_store import write_bytes_atomic


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _table(rows: list[tuple[str, Any]], header: tuple[str, str] = ("", "count")) -> list[str]:
    lines = [f"| {header[0]} | {header[1]} |", "|---|---:|"]
    lines += [f"| {name} | {value} |" for name, value in rows]
    return lines


def build_summary(out_dir: Path) -> str:
    enrichment = _load(out_dir / "enrichment.json")
    if enrichment is None:
        raise FileNotFoundError(f"no enrichment.json in {out_dir}")
    manifest = _load(out_dir / "run_manifest.json") or {}
    report = enrichment["document_report"]
    queue = _load(out_dir / "review_queue.json") or []
    evaluation = _load(out_dir / "eval_report.json")
    annotations = enrichment["annotations"]
    relationships = enrichment["relationships"]

    ref_links = [a for a in annotations if a["link_method"] == "source_ref"]
    resolved = sum(1 for a in ref_links if a["status"] == "verified")
    continuations = sum(len(a["target_block_ids"]) - 1 for a in annotations)
    nested = sum(1 for a in annotations if a["type"] == "nested_footnote")
    relation_kinds = Counter(f"{r['type']} ({r['assertion']})" for r in relationships)
    issues = Counter(issue["code"] for issue in enrichment["issues"])
    reasons = Counter(reason for item in queue for reason in item["reason"])

    lines = [
        f"# Run summary: {enrichment['pub_ref']}",
        "",
        f"Run `{enrichment['run_id']}` · code `{manifest.get('code_version', '?')}` · "
        f"config `{str(manifest.get('config_hash', '?'))[:19]}` · "
        f"adapter `{enrichment['source']['adapter']}`",
        "",
        "## Book",
        "",
        *_table(
            [
                ("pages held / claimed", f"{report['page_count_held']} / {report['page_count_claimed']}"),
                ("blocks", report["block_total"]),
                *[(f"blocks: {kind}", count) for kind, count in sorted(report["block_counts"].items())],
                ("sections", enrichment["stats"]["sections"]),
            ]
        ),
        "",
        "## Enrichment",
        "",
        *_table(
            [
                ("knowledge units", enrichment["stats"]["units"]),
                ("facts", enrichment["stats"]["facts"]),
                ("footnote refs resolved", f"{resolved} / {len(ref_links)}"),
                ("continued footnotes joined", continuations),
                ("nested footnotes", nested),
                ("citations", enrichment["stats"]["citations"]),
                ("works", len(enrichment["works"])),
                ("entities", enrichment["stats"]["entities"]),
                *[(f"relations: {kind}", count) for kind, count in sorted(relation_kinds.items())],
            ]
        ),
        "",
        "## Review queue",
        "",
        *_table([("items", len(queue)), *[(f"reason: {r}", c) for r, c in sorted(reasons.items())]]),
        "",
        "## Issues by code",
        "",
        *_table(sorted(issues.items()), ("code", "count")),
        "",
    ]
    if evaluation:
        chain = evaluation.get("chain_agreement") or {}
        lines += [
            "## Evaluation against the printed index",
            "",
            *_table(
                [
                    ("gold entries", evaluation["gold"]["entries"]),
                    ("precision", evaluation["precision"]),
                    ("recall", evaluation["recall"]),
                    ("F1", evaluation["f1"]),
                    ("lineage agreement", f"{chain.get('agree')} / {chain.get('checked')}"),
                    ("missed", len(evaluation["missed"])),
                ],
                ("metric", "value"),
            ),
            "",
        ]
    integrity = manifest.get("integrity", {})
    lines += [
        "## Integrity",
        "",
        f"- canonical content hash: `{enrichment['source']['canonical_content_hash']}`",
        f"- source-declared hash verified: {enrichment['source']['source_declared_hash_verified']}",
        f"- originals unchanged: {integrity.get('originals_unchanged', 'not checked')}",
        f"- outputs listed in the manifest: {len(manifest.get('outputs', []))}",
        "",
    ]
    return "\n".join(lines)


def write_summary(out_dir: Path) -> Path:
    return write_bytes_atomic(out_dir / "SUMMARY.md", build_summary(out_dir).encode("utf-8"))
