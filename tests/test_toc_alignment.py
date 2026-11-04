import pytest

from ilm_engine.processors.structure import build, title_similarity


@pytest.fixture(scope="module")
def structure(sample_book):
    return build(sample_book)


def test_all_17_toc_entries_matched(structure):
    assert len(structure.toc_alignment) == 17
    assert all(row.heading_block_id for row in structure.toc_alignment)
    assert len({row.heading_block_id for row in structure.toc_alignment}) == 17


def test_author_intro_source_page_15_is_printed_19(structure):
    row = next(r for r in structure.toc_alignment if r.title == "مقدمة المؤلف")
    assert (row.source_page_key, row.printed_page, row.offset, row.heading_block_id) == (
        "15",
        19,
        4,
        "b000090",
    )


def test_offsets(structure):
    assert structure.page_offsets == [2, 3, 4]  # over all pages (DECISIONS §7: 2 → 3 → 4)
    assert sorted({row.offset for row in structure.toc_alignment}) == [3, 4]  # TOC entries only
    [issue] = [i for i in structure.issues if i.code == "toc_page_offset"]
    assert issue.severity == "info" and issue.details["offsets"] == [3, 4]


def test_two_toc_without_block_issues(structure):
    issues = [i for i in structure.issues if i.code == "toc_without_block"]
    assert sorted(i.details["page"] for i in issues) == [5, 19]
    assert {i.severity for i in issues} == {"info"}


def test_no_heading_without_toc(structure):
    assert [i for i in structure.issues if i.code == "heading_without_toc"] == []


def test_titles_compared_after_normalization():
    toc = "وأخوة أولاد رسول الله -صلى الله عليه وسلم- من أمهم خديجة"
    heading = "* وأخوة أولاد رسول اللَّه -صلى الله عليه وسلم- من أُمهم خديجة:"
    assert title_similarity(toc, heading) == 1.0
    assert title_similarity("تعريف مختصر بالإمام الدارقطني", "تعريف مختصر بالإمام الدّارقطني (١):") == 1.0
    assert title_similarity("مقدمة المحقق", "الأخوة من ولد العباس") < 0.6


def test_alignment_in_structure_json(structure):
    data = structure.to_json()
    assert len(data["toc_alignment"]) == 17 and data["page_offsets"] == [2, 3, 4]
