import json
from pathlib import Path

import pytest

from ilm_engine.enrichment.models import Issue, Provenance
from ilm_engine.storage.json_store import (
    REPO_ROOT,
    JsonStore,
    ProtectedPathError,
    dumps,
    ensure_writable,
    write_bytes_atomic,
)

PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"


def issue() -> Issue:
    return Issue(
        issue_id="iss_0123456789ab",
        code="page_count_mismatch",
        severity="info",
        target_kind="book",
        target_id=PUB_REF,
        message="Source claims 72 pages, 68 held.",
        details={"missing_pages": [1, 2, 4, 18], "claimed": 72},
        provenance=Provenance(method="rule", step="document_analysis", step_version="1.0.0"),
    )


def test_writing_into_data_raises(tmp_path):
    with pytest.raises(ProtectedPathError):
        write_bytes_atomic(REPO_ROOT / "data" / "x.json", b"{}")
    with pytest.raises(ProtectedPathError):
        write_bytes_atomic("data/x.json", b"{}")
    assert not (REPO_ROOT / "data" / "x.json").exists()


def test_writing_into_store_originals_raises():
    with pytest.raises(ProtectedPathError):
        ensure_writable(REPO_ROOT / "store" / "originals" / PUB_REF / "x.json")
    with pytest.raises(ProtectedPathError):
        JsonStore(PUB_REF, out_root=REPO_ROOT / "store" / "originals")


def test_traversal_into_data_raises(tmp_path):
    with pytest.raises(ProtectedPathError):
        ensure_writable(REPO_ROOT / "output" / ".." / "data" / "x.json")


def test_similar_names_are_allowed(tmp_path):
    assert ensure_writable(tmp_path / "data_copy" / "x.json")
    assert ensure_writable(REPO_ROOT / "store" / "other" / "x.json")


def test_two_writes_are_byte_identical(tmp_path):
    store = JsonStore(PUB_REF, out_root=tmp_path)
    first = store.write("document_report.json", {"issues": [issue()], "b": 1, "a": "هند"}).read_bytes()
    second = store.write("document_report.json", {"a": "هند", "issues": [issue()], "b": 1}).read_bytes()
    assert first == second


def test_canonical_format(tmp_path):
    store = JsonStore(PUB_REF, out_root=tmp_path)
    path = store.write("metadata.json", {"b": [1, 2], "a": "الإخوة والأخوات"})
    text = path.read_text(encoding="utf-8")
    assert text == '{\n  "a": "الإخوة والأخوات",\n  "b": [\n    1,\n    2\n  ]\n}\n'
    assert path == tmp_path / PUB_REF / "metadata.json"


def test_models_serialized_by_contract_alias(tmp_path):
    from ilm_engine.canonical.models import Span

    store = JsonStore(PUB_REF, out_root=tmp_path)
    store.write("annotations.json", [Span(cls="c2", start=0, end=3, text="(١)")])
    assert store.read("annotations.json") == [
        {"class": "c2", "end": 3, "meaning": "unknown", "start": 0, "text": "(١)"}
    ]


def test_round_trip_and_listing(tmp_path):
    store = JsonStore(PUB_REF, out_root=tmp_path)
    store.write("structure.json", {"sections": []})
    store.write("validation_report.json", [issue()])
    assert store.read("validation_report.json")[0]["code"] == "page_count_mismatch"
    assert [path.name for path in store.files()] == ["structure.json", "validation_report.json"]
    assert store.exists("structure.json") and not store.exists("entities.json")


def test_unknown_output_name_rejected(tmp_path):
    with pytest.raises(ValueError, match="not an output file"):
        JsonStore(PUB_REF, out_root=tmp_path).write("notes.json", {})


def test_invalid_pub_ref_rejected(tmp_path):
    for bad in ["", "../x", ".hidden"]:
        with pytest.raises(ValueError):
            JsonStore(bad, out_root=tmp_path)


def test_atomic_write_leaves_no_temp_files(tmp_path):
    store = JsonStore(PUB_REF, out_root=tmp_path)
    store.write("entities.json", [])
    assert [path.name for path in (tmp_path / PUB_REF).iterdir()] == ["entities.json"]


def test_failed_serialization_keeps_previous_file(tmp_path):
    store = JsonStore(PUB_REF, out_root=tmp_path)
    store.write("entities.json", [1])
    with pytest.raises(TypeError):
        store.write("entities.json", [object()])
    assert json.loads(Path(store.path("entities.json")).read_text()) == [1]


def test_dumps_has_trailing_newline():
    assert dumps({}) == b"{}\n"
