from collections import Counter

import pytest

from ilm_engine.processors.structure import build


@pytest.fixture(scope="module")
def structure(sample_book):
    return build(sample_book)


def by_heading(structure, block_id):
    return next(s for s in structure.sections if s.heading_block_id == block_id)


def test_seventeen_sections_plus_root(structure):
    assert len(structure.sections) == 18
    assert structure.sections[0].level == 0 and structure.sections[0].parent_id is None
    assert Counter(s.level for s in structure.sections[1:]) == {1: 12, 2: 5}


def test_introductions(structure):
    editor = by_heading(structure, "b000012")
    author = by_heading(structure, "b000090")
    assert editor.title == "مقدمة المحقق" and editor.start_page == 5 and editor.level == 1
    assert author.title == "مقدمة المؤلف" and author.start_page == 19 and author.level == 1
    assert editor.end_block_id == "b000089"  # up to the block before the next level-1 section


def test_levels_from_toc_depth(structure):
    assert by_heading(structure, "b000026").level == 2  # عملي فى الكتاب, depth 2
    assert by_heading(structure, "b000113").level == 2  # ومن الذكور
    assert by_heading(structure, "b000134").level == 1


def test_parents_and_children(structure):
    editor = by_heading(structure, "b000012")
    work = by_heading(structure, "b000026")
    assert work.parent_id == editor.section_id and work.section_id in editor.children
    root = structure.sections[0]
    assert editor.section_id in root.children and work.section_id not in root.children


def test_every_block_in_exactly_one_deepest_section(structure, sample_book):
    assert set(structure.block_section) == set(sample_book.blocks)
    assert structure.block_section["b000001"] == structure.root_section_id  # title page before any heading
    assert structure.block_section["b000135"] == by_heading(structure, "b000134").section_id
    assert structure.block_section["b000030"] == by_heading(structure, "b000026").section_id


def test_section_ranges_follow_reading_order(structure, sample_book):
    order = {block_id: block.order for block_id, block in sample_book.blocks.items()}
    for section in structure.sections:
        assert order[section.start_block_id] <= order[section.end_block_id]


def test_provisional_origin(structure):
    assert by_heading(structure, "b000041").origin == "editor_text"
    assert by_heading(structure, "b000134").origin == "author_text"


def test_ids_deterministic(sample_book, structure):
    assert [s.section_id for s in build(sample_book).sections] == [s.section_id for s in structure.sections]
