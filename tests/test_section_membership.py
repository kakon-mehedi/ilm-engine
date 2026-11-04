import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.units import (
    assemble_units,
    detect_entries,
    section_subject,
    with_section_membership,
)
from ilm_engine.processors.annotations import build as build_annotations
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build as build_structure

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def units(sample_book):
    config = load_config(PUB_ID)
    origins = assign(sample_book, config).blocks
    structure = build_structure(sample_book)
    assembled, _ = assemble_units(
        sample_book,
        detect_entries(sample_book, origins, config),
        build_annotations(sample_book).annotations,
        structure,
        config,
    )
    return {u.entry_no: u for u in with_section_membership(sample_book, assembled, structure)}


def test_abbas_section(units, sample_book):
    abbas = [u for u in units.values() if u.payload.get("section_heading_block") == "b000339"]
    assert abbas and {u.payload["section_subject"] for u in abbas} == {"العباس بن عبد المطلب"}


def test_prophet_children_section(units):
    first = units[1]
    assert (
        first.payload["section_heading_block"] == "b000104"
        and first.payload["section_subject"] == "رسول الله ﷺ"
    )


def test_heading_anchor_is_evidence(units, sample_book):
    anchor = units[1].payload["section_heading_anchor"]
    assert anchor["block_id"] == "b000104" and anchor["quote"] == sample_book.block("b000104").text


def test_khadija_section_mother(units):
    eight = units[8]
    assert eight.payload["section_subject"] == "رسول الله ﷺ" and eight.payload["section_mother"] == "خديجة"


@pytest.mark.parametrize(
    "title, subject",
    [
        ("* الأُخوة من وَلد عبد المطلب بن هاشم بن عبد مَناف:", "عبد المطلب بن هاشم بن عبد مناف"),
        ("* الأُخوة من ولد الحارث بن عبد المطلب؛ وكان أكبر ولد أبيه وبه كان يكنى", "الحارث بن عبد المطلب"),
        ("* [الأُخوة مِن ذُريّة أبي بكر الصدّيق]:", "أبي بكر الصديق"),
        ("مقدمة المحقق", None),
    ],
)
def test_section_subject(title, subject):
    assert section_subject(title)[0] == subject
