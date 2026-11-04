import json
from pathlib import Path

import pytest

from ilm_engine.adapters.ocr_team_v1 import OcrTeamV1Adapter
from ilm_engine.adapters.registry import resolve
from ilm_engine.adapters.shamela_v3 import ShamelaV3Adapter
from ilm_engine.config import load_config
from ilm_engine.processors.document_analysis import analyze
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build
from ilm_engine.storage.json_store import dumps
from ilm_engine.tools.update_golden import readable_diff

GOLDEN = Path(__file__).resolve().parent / "golden" / "ocr_team_v1"


@pytest.fixture(scope="module")
def raw():
    return json.loads((GOLDEN / "input.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def book(raw):
    return OcrTeamV1Adapter().to_canonical(raw)


def test_registry_resolves_both_adapters(raw, sample_raw):
    assert isinstance(resolve(raw), OcrTeamV1Adapter)
    assert isinstance(resolve(sample_raw), ShamelaV3Adapter)


def test_golden(book):
    expected, actual = (GOLDEN / "expected_canonical.json").read_bytes(), dumps(book)
    assert actual == expected, readable_diff(expected, actual)


def test_mapping(book):
    assert book.book.pub_ref == "ocr_DEMO0001@r1" and book.source.source_code == "src-ocr-team"
    assert [block.kind for block in book.blocks_in_order()][:3] == ["heading", "text", "footnote"]
    assert all(block.refs == [] for block in book.blocks.values())
    assert book.block("p1f1").marker == "١" and book.page(2).scan_page == 6


def test_bbox_kept_in_raw_extras(book):
    assert book.block("p1l2").raw_extras == {"bbox": [60, 140, 480, 30]}
    assert book.raw_extras["blocks"]["p2l2"] == {"bbox": [60, 140, 480, 30], "confidence": 0.97}


def test_e03_steps_run_without_code_changes(book):
    report, issues = analyze(book, load_config())
    assert report.block_total == 6 and report.missing_printed_pages == [3]
    assert any(issue.code == "missing_page" for issue in issues)
    structure = build(book)
    assert [s.title for s in structure.sections[1:]] == ["مقدمة المحقق", "مقدمة المؤلف"]
    origins = assign(book, load_config())
    assert origins.blocks["p1l2"] == "editor_text" and origins.blocks["p2l2"] == "author_text"
    assert origins.blocks["p1f1"] == "editor_footnote"


def test_malformed_input_fails_closed():
    from ilm_engine.adapters.shamela_v3 import SourceFormatError

    with pytest.raises(SourceFormatError):
        OcrTeamV1Adapter().to_canonical({"format": "ocr-team", "version": "1.0"})
