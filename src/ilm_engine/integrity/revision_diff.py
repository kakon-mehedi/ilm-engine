"""Revision diff and stale anchors (ADR-017).

When a new revision of a book arrives, blocks are matched by `block_id` and compared by `block_hash`:
- unchanged → enrichment is carried over as is (same IDs);
- changed → anchors on the block become `stale` (issue `anchor_stale`) and the block is re-processed;
- removed → anchors become `orphaned` (issue `anchor_stale`), their records are withdrawn;
- added → processed normally.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.enrichment.models import Anchor, Issue, Provenance
from ilm_engine.ids import make_id, natural_key


@dataclass(frozen=True)
class RevisionDiff:
    old_pub_ref: str
    new_pub_ref: str
    unchanged: tuple[str, ...]
    changed: tuple[str, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def to_reprocess(self) -> frozenset[str]:
        """Block IDs an incremental run must process again."""
        return frozenset(self.changed) | frozenset(self.added)


def diff(old_book: CanonicalBook, new_book: CanonicalBook) -> RevisionDiff:
    """Compare two revisions block by block (`block_id` + `block_hash`), in reading order."""
    old, new = old_book.blocks, new_book.blocks
    return RevisionDiff(
        old_pub_ref=old_book.book.pub_ref,
        new_pub_ref=new_book.book.pub_ref,
        unchanged=tuple(b for b in new if b in old and old[b].block_hash == new[b].block_hash),
        changed=tuple(b for b in new if b in old and old[b].block_hash != new[b].block_hash),
        added=tuple(b for b in new if b not in old),
        removed=tuple(b for b in old if b not in new),
    )


def restatus_anchors[T](obj: T, revision: RevisionDiff) -> T:
    """Copy of `obj` (a model, list or dict of records) with anchors on changed blocks `stale` and on
    removed blocks `orphaned`; everything else is returned unchanged."""
    changed, removed = set(revision.changed), set(revision.removed)
    return _walk(obj, changed, removed)  # type: ignore[no-any-return]


def _walk(obj: Any, changed: set[str], removed: set[str]) -> Any:
    if isinstance(obj, Anchor):
        if obj.block_id in removed:
            return obj.model_copy(update={"status": "orphaned"})
        if obj.block_id in changed:
            return obj.model_copy(update={"status": "stale"})
        return obj
    if isinstance(obj, BaseModel):
        updates = {}
        for name in type(obj).model_fields:
            value = getattr(obj, name)
            new_value = _walk(value, changed, removed)
            if new_value is not value:
                updates[name] = new_value
        return obj.model_copy(update=updates) if updates else obj
    if isinstance(obj, list):
        items = [_walk(item, changed, removed) for item in obj]
        return items if any(a is not b for a, b in zip(items, obj, strict=True)) else obj
    if isinstance(obj, dict):
        values = {key: _walk(value, changed, removed) for key, value in obj.items()}
        return values if any(values[key] is not obj[key] for key in obj) else obj
    return obj


def anchors_in(obj: Any) -> list[Anchor]:
    """Every anchor inside `obj`, in traversal order."""
    if isinstance(obj, Anchor):
        return [obj]
    if isinstance(obj, BaseModel):
        return [anchor for name in type(obj).model_fields for anchor in anchors_in(getattr(obj, name))]
    if isinstance(obj, list | tuple):
        return [anchor for item in obj for anchor in anchors_in(item)]
    if isinstance(obj, dict):
        return [anchor for value in obj.values() for anchor in anchors_in(value)]
    return []


def stale_anchor_issues(records: Any, revision: RevisionDiff) -> list[Issue]:
    """One `anchor_stale` issue per changed or removed block that existing records anchor to."""
    counts = Counter(anchor.block_id for anchor in anchors_in(records))
    issues = []
    for block_id, status in [(b, "stale") for b in revision.changed] + [
        (b, "orphaned") for b in revision.removed
    ]:
        if not counts[block_id]:
            continue
        verb = "changed" if status == "stale" else "was removed"
        message = (
            f"Block {block_id} {verb} in {revision.new_pub_ref}; {counts[block_id]} anchor(s) are {status}."
        )
        issues.append(
            Issue(
                issue_id=make_id("iss", revision.new_pub_ref, natural_key("anchor_stale", block_id)),
                code="anchor_stale",
                severity="warning",
                target_kind="block",
                target_id=block_id,
                message=message,
                details={"status": status, "anchors": counts[block_id], "previous": revision.old_pub_ref},
                provenance=Provenance(method="rule", step="integrity_verify", step_version="1.0.0"),
            )
        )
    return issues
