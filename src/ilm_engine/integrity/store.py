"""Read-only store of original inputs (ADR-017).

`ingest` copies the source JSON and PDF once into `store/originals/<pub_ref>/`, records their hashes in
`manifest.json` and makes every file read-only (0444). The pipeline reads only from there. Originals are
immutable: ingesting the same files again is a no-op, ingesting different files for the same `pub_ref`
is refused. `verify` re-hashes the stored files against the manifest.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ilm_engine.enrichment.models import FileHash, Issue, Provenance
from ilm_engine.ids import make_id, natural_key
from ilm_engine.integrity.hashing import file_sha256

DEFAULT_STORE_ROOT = Path("store") / "originals"
MANIFEST_NAME = "manifest.json"
READ_ONLY = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH  # 0o444


class OriginalStoreError(Exception):
    """The store refuses an operation that would change an original."""


@dataclass(frozen=True)
class StoredOriginal:
    pub_ref: str
    directory: Path
    files: dict[str, FileHash]  # keyed by stored file name
    source_declared_hash: str | None
    source_declared_hash_verified: bool
    issues: list[Issue] = field(default_factory=list)

    def path(self, name: str) -> Path:
        if name not in self.files:
            raise KeyError(f"{name!r} is not stored for {self.pub_ref}")
        return self.directory / name


def ingest(
    json_path: str | Path,
    pdf_path: str | Path | None,
    pub_ref: str,
    declared_hash: str | None = None,
    store_root: str | Path = DEFAULT_STORE_ROOT,
) -> StoredOriginal:
    """Copy the inputs into the store (read-only) and return what is stored. Sources are only read."""
    sources = [Path(json_path)] + ([Path(pdf_path)] if pdf_path is not None else [])
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
    names = [source.name for source in sources]
    if len(set(names)) != len(names) or MANIFEST_NAME in names:
        raise OriginalStoreError(f"input file names must be distinct and not {MANIFEST_NAME!r}: {names}")

    directory = Path(store_root) / pub_ref
    source_hashes = {source.name: _file_hash(source, source.name) for source in sources}
    verified = _declared_hash_verified(declared_hash, source_hashes.values())

    if (directory / MANIFEST_NAME).exists():
        stored = load(pub_ref, store_root)
        if {name: item.sha256 for name, item in stored.files.items()} != {
            name: item.sha256 for name, item in source_hashes.items()
        }:
            raise OriginalStoreError(
                f"{pub_ref} is already stored with different files; originals are immutable"
            )
        return stored

    directory.mkdir(parents=True, exist_ok=True)
    for source in sources:
        target = directory / source.name
        shutil.copyfile(source, target)
        if _file_hash(target, source.name) != source_hashes[source.name]:
            raise OriginalStoreError(f"copy of {source} does not match its source")
        os.chmod(target, READ_ONLY)

    manifest = {
        "pub_ref": pub_ref,
        "files": [item.model_dump() for item in source_hashes.values()],
        "source_declared_hash": declared_hash,
        "source_declared_hash_verified": verified,
        "ingested_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    manifest_path = directory / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, READ_ONLY)
    return load(pub_ref, store_root)


def load(pub_ref: str, store_root: str | Path = DEFAULT_STORE_ROOT) -> StoredOriginal:
    """What the store holds for `pub_ref`, from its manifest."""
    directory = Path(store_root) / pub_ref
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"{pub_ref} is not in the original store ({manifest_path})")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = {item["path"]: FileHash.model_validate(item) for item in manifest["files"]}
    declared = manifest.get("source_declared_hash")
    verified = bool(manifest.get("source_declared_hash_verified"))
    issues = [] if declared is None or verified else [_unverified_hash_issue(pub_ref, declared)]
    return StoredOriginal(pub_ref, directory, files, declared, verified, issues)


def verify(pub_ref: str, store_root: str | Path = DEFAULT_STORE_ROOT) -> bool:
    """True if every stored file still exists, is read-only and matches its recorded hash."""
    try:
        stored = load(pub_ref, store_root)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return False
    for name, expected in stored.files.items():
        path = stored.directory / name
        if not path.is_file() or path.stat().st_mode & 0o222:
            return False
        if _file_hash(path, name) != expected:
            return False
    return True


def _file_hash(path: Path, name: str) -> FileHash:
    return FileHash(path=name, sha256=file_sha256(path), bytes=path.stat().st_size)


def _declared_hash_verified(declared: str | None, files: Iterable[FileHash]) -> bool:
    """A declared hash is verified only if it equals the hash of one of the stored files' bytes."""
    if declared is None:
        return False
    bare = declared.removeprefix("sha256:").lower()
    return any(item.sha256.removeprefix("sha256:") == bare for item in files)


def _unverified_hash_issue(pub_ref: str, declared: str) -> Issue:
    return Issue(
        issue_id=make_id("iss", pub_ref, natural_key("source_hash_unverified", pub_ref)),
        code="source_hash_unverified",
        severity="info",
        target_kind="book",
        target_id=pub_ref,
        message="Source-declared content hash could not be reproduced; integrity relies on our own hashes.",
        details={"source_declared_hash": declared},
        provenance=Provenance(method="rule", step="integrity_register", step_version="1.0.0"),
    )
