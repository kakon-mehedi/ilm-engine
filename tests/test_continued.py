import pytest

from ilm_engine.processors.annotations import build


@pytest.fixture(scope="module")
def result(sample_book):
    return build(sample_book)


def test_16_continuation_links(result):
    assert len(result.continuation_of) == 16
    assert len([i for i in result.issues if i.code == "continued_footnote_joined"]) == 16
    assert {i.severity for i in result.issues if i.code == "continued_footnote_joined"} == {"info"}


def test_b000103_joins_b000097(result, sample_book):
    assert result.continuation_of["b000103"] == "b000097"
    assert sample_book.block("b000103").page == 20 and sample_book.block("b000097").page == 19
    [annotation] = [
        a for a in result.annotations if a.target_block_ids and a.target_block_ids[0] == "b000097"
    ]
    assert annotation.target_block_ids == ["b000097", "b000103"]


def test_continued_parts_are_previous_page_last_footnotes(result, sample_book):
    pages = [page.n for page in sample_book.pages]
    for part, previous in result.continuation_of.items():
        part_page, previous_page = sample_book.block(part).page, sample_book.block(previous).page
        assert pages.index(previous_page) == pages.index(part_page) - 1
        assert sample_book.block(previous).text.rstrip().endswith("=")


def test_nested_footnote_printed_last_is_skipped(result):
    # p.33 ends with the nested note b000215 ("أ"); b000220 continues b000214, which ends with "=".
    assert result.continuation_of["b000220"] == "b000214"


def test_every_part_in_exactly_one_annotation(result):
    owners = result.by_target()
    for part in result.continuation_of:
        assert len(owners[part]) == 1


def test_originals_untouched(result, sample_book):
    assert sample_book.block("b000103").continues is True and sample_book.block("b000103").refs == []
