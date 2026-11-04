import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.units import assemble_units, detect_entries
from ilm_engine.processors.annotations import build as build_annotations
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build as build_structure

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def assembled(sample_book):
    config = load_config(PUB_ID)
    origins = assign(sample_book, config).blocks
    annotations = build_annotations(sample_book).annotations
    structure = build_structure(sample_book)
    units, issues = assemble_units(
        sample_book, detect_entries(sample_book, origins, config), annotations, structure, config
    )
    return units, issues, {a.annotation_id: a for a in annotations}, structure


def unit(assembled, number):
    return next(u for u in assembled[0] if u.entry_no == number)


def test_75_units_and_entry_footnotes(assembled):
    units, issues, _, _ = assembled
    assert len(units) == 75 and [u.entry_no for u in units] == list(range(1, 76))
    with_note = [u for u in units if "tarjama_annotation" in u.payload]
    assert len(with_note) == 74
    [missing] = [i for i in issues if i.code == "entry_without_footnote"]
    assert missing.details["entry_no"] == 32 and missing.target_id == unit(assembled, 32).unit_id


def test_unit_8(assembled, sample_book):
    eight = unit(assembled, 8)
    by_id = assembled[2]
    targets = [by_id[a].target_block_ids[0] for a in eight.note_annotation_ids]
    assert targets == ["b000139", "b000140", "b000141", "b000142"]
    section = assembled[3].section(eight.section_id)
    assert section.heading_block_id == "b000134"
    [anchor] = eight.anchors
    assert (anchor.block_id, anchor.start, anchor.end) == ("b000135", 0, 102)
    assert eight.payload["tarjama_annotation"] == "b000139"


def test_payload_person(assembled):
    payload = unit(assembled, 8).payload
    assert payload["person"]["ism"] == "هند" and payload["person"]["gender"] == "f"
    assert payload["person"]["span"] == [4, 58]
    assert payload["nasab"] == ["عتيق", "عابد", "عبد الله", "عمر", "مخزوم"]
    assert unit(assembled, 4).payload["kunya"] == "أم كلثوم"


def test_unit_envelope(assembled):
    eight = unit(assembled, 8)
    assert (eight.genre, eight.sub_type, eight.unit_type, eight.origin) == (
        "biography",
        "ansab",
        "biographical_entry",
        "author_text",
    )
    assert eight.confidence == 0.95 and eight.review_status == "auto_approved" and eight.facts == []


def test_entry_note_first(assembled):
    by_id = assembled[2]
    for u in assembled[0]:
        if u.note_annotation_ids and "tarjama_annotation" in u.payload:
            assert by_id[u.note_annotation_ids[0]].is_entry_note


def test_entries_sharing_a_block_split_notes(assembled):
    by_id = assembled[2]
    n18, n19 = unit(assembled, 18), unit(assembled, 19)
    assert not set(n18.note_annotation_ids) & set(n19.note_annotation_ids)
    for u in (n18, n19):
        assert all(by_id[a].marker_anchor.start >= u.anchors[0].start for a in u.note_annotation_ids)
