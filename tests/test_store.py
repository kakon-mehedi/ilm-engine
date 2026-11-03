import json
import os
import stat
from pathlib import Path

import pytest

from ilm_engine.integrity.hashing import file_sha256
from ilm_engine.integrity.store import MANIFEST_NAME, OriginalStoreError, ingest, load, verify

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_JSON = ROOT / "data" / "demo_book_daraqutni.json"
SAMPLE_PDF = ROOT / "data" / "demo_book_daraqutni_v1.pdf"
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
DECLARED = "1f974ece9429393b052de38052876b65ed195f83d3b6d55773691f2599f5c582"


@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    yield tmp_path / "originals"
    for path in (tmp_path / "originals").rglob("*"):  # let pytest clean up read-only files
        if path.is_file():
            os.chmod(path, 0o644)


def test_ingest_copies_read_only_and_verifies(store_root):
    stored = ingest(SAMPLE_JSON, SAMPLE_PDF, PUB_REF, declared_hash=DECLARED, store_root=store_root)
    assert stored.directory == store_root / PUB_REF
    assert set(stored.files) == {"demo_book_daraqutni.json", "demo_book_daraqutni_v1.pdf"}
    for name in [*stored.files, MANIFEST_NAME]:
        assert stat.S_IMODE((stored.directory / name).stat().st_mode) == 0o444
    assert stored.files["demo_book_daraqutni.json"].sha256 == file_sha256(SAMPLE_JSON)
    assert stored.files["demo_book_daraqutni_v1.pdf"].bytes == SAMPLE_PDF.stat().st_size
    assert verify(PUB_REF, store_root) is True


def test_sample_files_unchanged_by_ingest(store_root):
    before = {path: (file_sha256(path), path.stat().st_mode) for path in (SAMPLE_JSON, SAMPLE_PDF)}
    ingest(SAMPLE_JSON, SAMPLE_PDF, PUB_REF, declared_hash=DECLARED, store_root=store_root)
    assert {path: (file_sha256(path), path.stat().st_mode) for path in (SAMPLE_JSON, SAMPLE_PDF)} == before


def test_modified_copy_fails_verification(store_root):
    stored = ingest(SAMPLE_JSON, None, PUB_REF, store_root=store_root)
    copy = stored.path("demo_book_daraqutni.json")
    os.chmod(copy, 0o644)
    copy.write_bytes(copy.read_bytes().replace("أسلمت".encode(), "اسلمت".encode(), 1))
    os.chmod(copy, 0o444)
    assert verify(PUB_REF, store_root) is False


def test_writable_copy_fails_verification(store_root):
    stored = ingest(SAMPLE_JSON, None, PUB_REF, store_root=store_root)
    os.chmod(stored.path("demo_book_daraqutni.json"), 0o644)
    assert verify(PUB_REF, store_root) is False


def test_missing_copy_fails_verification(store_root):
    stored = ingest(SAMPLE_JSON, SAMPLE_PDF, PUB_REF, store_root=store_root)
    stored.path("demo_book_daraqutni_v1.pdf").unlink()
    assert verify(PUB_REF, store_root) is False


def test_unknown_pub_ref_fails_verification(store_root):
    assert verify("pub_X@r1", store_root) is False


def test_declared_hash_not_reproducible_emits_issue(store_root):
    stored = ingest(SAMPLE_JSON, SAMPLE_PDF, PUB_REF, declared_hash=DECLARED, store_root=store_root)
    assert stored.source_declared_hash == DECLARED and stored.source_declared_hash_verified is False
    [issue] = stored.issues
    assert issue.code == "source_hash_unverified" and issue.severity == "info"
    assert issue.target_id == PUB_REF and issue.provenance.step == "integrity_register"
    manifest = json.loads((stored.directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["source_declared_hash_verified"] is False


def test_declared_hash_matching_file_bytes_is_verified(tmp_path, store_root):
    source = tmp_path / "book.json"
    source.write_text('{"a": 1}', encoding="utf-8")
    stored = ingest(source, None, "pub_T@r1", declared_hash=file_sha256(source), store_root=store_root)
    assert stored.source_declared_hash_verified is True and stored.issues == []


def test_reingest_same_files_is_a_no_op(store_root):
    first = ingest(SAMPLE_JSON, SAMPLE_PDF, PUB_REF, store_root=store_root)
    manifest = (first.directory / MANIFEST_NAME).read_bytes()
    second = ingest(SAMPLE_JSON, SAMPLE_PDF, PUB_REF, store_root=store_root)
    assert second.files == first.files
    assert (first.directory / MANIFEST_NAME).read_bytes() == manifest


def test_reingest_different_files_refused(tmp_path, store_root):
    source = tmp_path / "book.json"
    source.write_text("v1", encoding="utf-8")
    ingest(source, None, "pub_T@r1", store_root=store_root)
    source.write_text("v2", encoding="utf-8")
    with pytest.raises(OriginalStoreError, match="immutable"):
        ingest(source, None, "pub_T@r1", store_root=store_root)
    assert verify("pub_T@r1", store_root) is True


def test_missing_input_raises(tmp_path, store_root):
    with pytest.raises(FileNotFoundError):
        ingest(tmp_path / "absent.json", None, "pub_T@r1", store_root=store_root)


def test_load_and_path(store_root):
    ingest(SAMPLE_JSON, None, PUB_REF, store_root=store_root)
    stored = load(PUB_REF, store_root)
    assert stored.path("demo_book_daraqutni.json").read_bytes() == SAMPLE_JSON.read_bytes()
    with pytest.raises(KeyError):
        stored.path("other.pdf")
