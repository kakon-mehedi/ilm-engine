import copy
import json
import logging
from pathlib import Path

import pytest

from ilm_engine.adapters.shamela_v3 import ShamelaV3Adapter

DATA = Path(__file__).resolve().parents[1] / "data" / "demo_book_daraqutni.json"


@pytest.fixture(scope="module")
def raw():
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def book(raw):
    return ShamelaV3Adapter().to_canonical(raw)


def test_unknown_block_field_preserved(raw):
    changed = copy.deepcopy(raw)
    changed["content"]["pages"][22]["blocks"][1]["foo"] = 1
    block_id = changed["content"]["pages"][22]["blocks"][1]["b"]
    book = ShamelaV3Adapter().to_canonical(changed)
    assert book.raw_extras["blocks"][block_id]["foo"] == 1
    assert book.block(block_id).raw_extras == {"foo": 1}


def test_quality_kept_verbatim(book, raw):
    assert book.raw_extras["top"]["quality"]["auto"]["detail"]["claimed"] == 72
    assert book.raw_extras["top"]["quality"] == raw["quality"]


def test_meta_and_timeline_kept_verbatim(book, raw):
    top = book.raw_extras["top"]
    assert top["_meta"] == raw["_meta"] and top["timeline"] == raw["timeline"]
    assert top["work"] == raw["work"] and top["editions"] == raw["editions"]


def test_unmapped_subkeys_of_mapped_sections(book):
    top = book.raw_extras["top"]
    assert top["pub"]["listing_title"] == "الإخوة والأخوات - الدارقطني"
    assert "id" not in top["pub"] and "source_code" not in top["pub"]
    assert top["revision"]["origin"] == "adapter_upgrade"
    assert top["metadata"]["source_extras"][0]["raw"] == "مقدمة المحقق"
    assert top["metadata"]["source_attributes"]["source_author_id"] == "223"
    assert "toc" not in top["metadata"]["source_attributes"]
    assert top["content"] == {"page_count": 68}


def test_sample_blocks_and_pages_have_no_extras(book):
    assert book.raw_extras["blocks"] == {}
    assert all(page.raw_extras == {} for page in book.pages)


def test_unknown_page_field_preserved(raw):
    changed = copy.deepcopy(raw)
    changed["content"]["pages"][0]["ocr_confidence"] = 0.97
    assert ShamelaV3Adapter().to_canonical(changed).pages[0].raw_extras == {"ocr_confidence": 0.97}


def test_unknown_top_level_section_preserved(raw):
    changed = copy.deepcopy(raw)
    changed["new_section"] = {"x": 1}
    assert ShamelaV3Adapter().to_canonical(changed).raw_extras["top"]["new_section"] == {"x": 1}


def test_unmapped_fields_logged_once(raw, caplog):
    changed = copy.deepcopy(raw)
    changed["content"]["pages"][0]["blocks"][0]["foo"] = 1
    with caplog.at_level(logging.WARNING, logger="ilm_engine"):
        ShamelaV3Adapter().to_canonical(changed)
    [record] = [r for r in caplog.records if "unmapped source fields" in r.getMessage()]
    assert "top.timeline" in record.fields and any(field.endswith(".foo") for field in record.fields)
