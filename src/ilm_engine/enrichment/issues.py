"""Issue construction shared by every step (DECISIONS §9 codes, deterministic IDs)."""

from __future__ import annotations

from typing import Any

from ilm_engine.enrichment.models import Anchor, Issue, IssueCode, Provenance, Severity
from ilm_engine.ids import make_id, natural_key


def make_issue(
    pub_ref: str,
    code: IssueCode,
    severity: Severity,
    target_kind: str,
    target_id: str,
    message: str,
    step: str,
    details: dict[str, Any] | None = None,
    anchors: list[Anchor] | None = None,
    key: str | None = None,
    method: str = "rule",
    step_version: str = "1.0.0",
) -> Issue:
    """An issue whose ID is derived from `code` + `target_id` (+ `key` when one target has several)."""
    natural = natural_key(code, target_id, key) if key is not None else natural_key(code, target_id)
    return Issue(
        issue_id=make_id("iss", pub_ref, natural),
        code=code,
        severity=severity,
        target_kind=target_kind,  # type: ignore[arg-type]
        target_id=target_id,
        message=message,
        anchors=anchors or [],
        details=details or {},
        provenance=Provenance(method=method, step=step, step_version=step_version),  # type: ignore[arg-type]
    )
