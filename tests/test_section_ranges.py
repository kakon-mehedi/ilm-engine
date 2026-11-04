import pytest

from ilm_engine.nlp.normalize import normalize
from ilm_engine.processors.structure import build

KHADIJA = "* وأخوة أولاد رسول اللَّه -صلى الله عليه وسلم- من أُمهم خديجة:"


@pytest.fixture(scope="module")
def structure(sample_book):
    return build(sample_book)


def test_b000135_in_khadija_section(structure, sample_book):
    title = structure.section(structure.block_section_id("b000135")).title
    assert title == sample_book.block("b000134").text
    assert normalize(title) == normalize(KHADIJA)  # same words; the source's mark order differs


def test_page_25_maps_to_that_section(structure):
    section_id = structure.block_section_id("b000135")
    assert structure.page_index()[25] == [section_id]
    assert structure.to_json()["page_index"]["25"] == [section_id]


def test_section_blocks(structure):
    section_id = structure.block_section_id("b000135")
    blocks = structure.section_blocks(section_id)
    assert blocks[0] == "b000134" and "b000135" in blocks
    assert blocks[-1] == structure.section(section_id).end_block_id


def test_shallow_versus_deep_blocks(structure):
    editor_intro = structure.block_section_id("b000012")
    deep, shallow = structure.section_blocks(editor_intro), structure.section_blocks(editor_intro, deep=False)
    assert "b000030" in deep and "b000030" not in shallow
    assert set(shallow) < set(deep)


def test_page_index_covers_every_page(structure, sample_book):
    assert sorted(structure.page_index()) == sorted(page.n for page in sample_book.pages)


def test_page_with_two_sections(structure):
    page6 = structure.page_index()[6]  # editor intro continues, then "عملي فى الكتاب" starts
    assert len(page6) == 2


def test_unknown_block(structure):
    with pytest.raises(KeyError):
        structure.block_section_id("b999999")
