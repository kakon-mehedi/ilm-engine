"""Adapter registry: `(source_code, schema_version)` → adapter, failing closed (ADR-002).

Inputs normally declare their key (`pub.source_code`, `metadata.af_schema`). An input without a
declared key is offered to each adapter's `detect()`. Nothing is ever guessed: an unknown key raises
`UnknownSchemaError`, and more than one matching adapter raises `AmbiguousAdapterError`.
"""

from __future__ import annotations

from typing import Any

from ilm_engine.adapters.base import SourceAdapter
from ilm_engine.enrichment.models import Issue, Provenance
from ilm_engine.ids import make_id, natural_key

AdapterKey = tuple[str, str]


class AdapterError(Exception):
    """Base class for adapter resolution errors."""


class UnknownSchemaError(AdapterError):
    """No adapter is registered for the input's `(source_code, schema_version)`."""

    def __init__(self, key: tuple[str | None, str | None], issue: Issue) -> None:
        super().__init__(issue.message)
        self.key = key
        self.issue = issue


class AmbiguousAdapterError(AdapterError):
    """More than one adapter claims the same input."""


class DuplicateAdapterError(AdapterError):
    """An adapter is already registered for this key."""


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    return value if isinstance(value, dict) else {}


def declared_key(raw: dict[str, Any]) -> tuple[str | None, str | None]:
    """The `(source_code, schema_version)` the input declares, if any."""
    pub, metadata = _section(raw, "pub"), _section(raw, "metadata")
    source_code = pub.get("source_code") if isinstance(pub.get("source_code"), str) else None
    schema = metadata.get("af_schema")
    return source_code, (str(schema) if schema is not None else None)


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[AdapterKey, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> SourceAdapter:
        """Register `adapter` for each of its schema versions; returns it (usable as a decorator)."""
        if not adapter.schema_versions:
            raise ValueError(f"adapter {adapter.adapter_id!r} declares no schema versions")
        keys = [(adapter.source_code, version) for version in sorted(adapter.schema_versions)]
        for key in keys:
            if key in self._adapters:
                existing = self._adapters[key].adapter_id
                raise DuplicateAdapterError(f"{key} is already handled by adapter {existing!r}")
        for key in keys:
            self._adapters[key] = adapter
        return adapter

    def keys(self) -> list[AdapterKey]:
        return sorted(self._adapters)

    def resolve(self, raw: dict[str, Any]) -> SourceAdapter:
        """The single adapter for `raw`; raises `UnknownSchemaError` or `AmbiguousAdapterError`."""
        key = declared_key(raw)
        if key[0] is not None and key[1] is not None:
            adapter = self._adapters.get((key[0], key[1]))
            if adapter is None:
                raise UnknownSchemaError(key, _unknown_schema_issue(raw, key, self.keys()))
            return adapter

        matches = {id(adapter): adapter for adapter in self._adapters.values() if adapter.detect(raw)}
        if len(matches) > 1:
            names = ", ".join(sorted(adapter.adapter_id for adapter in matches.values()))
            raise AmbiguousAdapterError(f"input matches several adapters: {names}")
        if not matches:
            raise UnknownSchemaError(key, _unknown_schema_issue(raw, key, self.keys()))
        return next(iter(matches.values()))


def _unknown_schema_issue(
    raw: dict[str, Any], key: tuple[str | None, str | None], known: list[AdapterKey]
) -> Issue:
    pub, revision = _section(raw, "pub"), _section(raw, "revision")
    pub_id, rev = pub.get("id"), revision.get("r")
    target = f"{pub_id}@r{rev}" if pub_id and isinstance(rev, int) else str(pub_id or "unknown")
    return Issue(
        issue_id=make_id("iss", target, natural_key("unknown_schema_version", f"{key[0]}|{key[1]}")),
        code="unknown_schema_version",
        severity="error",
        target_kind="book",
        target_id=target,
        message=f"No adapter for source_code={key[0]!r}, schema_version={key[1]!r}; input not processed.",
        details={
            "source_code": key[0],
            "schema_version": key[1],
            "known": [f"{code}@{version}" for code, version in known],
        },
        provenance=Provenance(method="rule", step="adapt", step_version="1.0.0"),
    )


default_registry = AdapterRegistry()
register = default_registry.register
resolve = default_registry.resolve
