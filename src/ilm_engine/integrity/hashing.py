"""Integrity hashes (DECISIONS §5, ADR-017).

Every hash is `sha256:<64 hex>`. Block and content hashes cover the exact original text with no
normalization, so any change to a single code point changes the hash.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ilm_engine.canonical.models import Block, CanonicalBook

_CHUNK_SIZE = 1 << 20


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def block_hash(text: str) -> str:
    """Hash of a block's exact text (UTF-8 bytes)."""
    return _sha256(text.encode("utf-8"))


def canonical_json(obj: Any) -> bytes:
    """Deterministic UTF-8 JSON: sorted keys, no whitespace, non-ASCII kept as is."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_hash(book: CanonicalBook | Iterable[Block]) -> str:
    """`canonical_content_hash` over `[block_id, kind, text, marker, refs]` of all blocks in reading order.

    Accepts the blocks directly so an adapter can compute the hash before it builds the book.
    """
    blocks = book.blocks.values() if isinstance(book, CanonicalBook) else book
    rows = [
        [
            block.block_id,
            block.kind,
            block.text,
            block.marker,
            [[ref.start, ref.end, ref.to] for ref in block.refs],
        ]
        for block in sorted(blocks, key=lambda block: block.order)
    ]
    return _sha256(canonical_json(rows))


def file_sha256(path: str | Path) -> str:
    """Hash of a file's bytes, read in chunks."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
