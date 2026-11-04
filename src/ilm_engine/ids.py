"""Deterministic identifiers (DECISIONS §4, ADR-011).

Our IDs are `<prefix>_<sha256(pub_ref + "|" + natural_key)[:12]>`: the same input always yields the
same ID, so reruns are repeatable and diffable. Source IDs (`b000135`, `pub_…`, `wrk_01M0…`) are kept
as they are and never generated here.
"""

import hashlib

PREFIXES = frozenset({"sec", "ku", "ent", "rel", "ann", "cit", "wrk", "iss", "rev", "run", "grp"})
"""Allowed ID prefixes: DECISIONS §4 plus `grp` for sibling groups (DECISIONS §12c)."""

_HASH_LENGTH = 12


def pub_ref(pub_id: str, revision: int) -> str:
    """Book reference for one revision: `pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6`."""
    if not pub_id or "@" in pub_id:
        raise ValueError(f"invalid pub_id: {pub_id!r}")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise ValueError(f"revision must be a non-negative integer, got {revision!r}")
    return f"{pub_id}@r{revision}"


def natural_key(*parts: str | int) -> str:
    """Join natural-key parts with `|`, e.g. `natural_key(8, "b000135", 0) == "8|b000135|0"` (ADR-011)."""
    if not parts:
        raise ValueError("a natural key needs at least one part")
    return "|".join(str(part) for part in parts)


def make_id(prefix: str, pub_ref: str, natural_key: str) -> str:
    """Deterministic ID `<prefix>_<12 hex>` for a record of the book `pub_ref`.

    Only `run` IDs may include a timestamp in their natural key; every other natural key must be
    derived from the content alone.
    """
    if prefix not in PREFIXES:
        raise ValueError(f"unknown ID prefix {prefix!r}; allowed: {', '.join(sorted(PREFIXES))}")
    if not pub_ref:
        raise ValueError("pub_ref must not be empty")
    if not natural_key:
        raise ValueError("natural_key must not be empty")
    digest = hashlib.sha256(f"{pub_ref}|{natural_key}".encode()).hexdigest()
    return f"{prefix}_{digest[:_HASH_LENGTH]}"
