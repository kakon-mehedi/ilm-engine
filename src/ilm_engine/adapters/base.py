"""Source adapter protocol (ADR-002).

An adapter converts one source format (one `source_code`, one or more schema versions) into the
canonical book. Supporting a new format means adding an adapter, never editing the pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ilm_engine.canonical.models import CanonicalBook


@runtime_checkable
class SourceAdapter(Protocol):
    adapter_id: str  # e.g. "shamela_v3"
    source_code: str  # e.g. "src-shamela"
    schema_versions: frozenset[str]  # source schema versions this adapter reads, e.g. {"3.0"}
    adapter_version: str  # our adapter's own version, e.g. "1.0.0"

    def detect(self, raw: dict[str, Any]) -> bool:
        """True if `raw` is in this adapter's format (used when the input declares no key)."""
        ...

    def to_canonical(self, raw: dict[str, Any], pdf_path: Path | None = None) -> CanonicalBook:
        """Convert the raw source document into the canonical book."""
        ...
