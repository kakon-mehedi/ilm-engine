import pytest

from ilm_engine.processors.annotations import build, join_continuations, link_nested, resolve_refs


@pytest.fixture(scope="module")
def result(sample_book):
    return build(sample_book)


def test_exactly_one_nested_footnote(result):
    nested = [a for a in result.annotations if a.type == "nested_footnote"]
    [annotation] = nested
    assert annotation.target_block_ids == ["b000215"] and annotation.source_block_id == "b000210"
    anchor = annotation.marker_anchor
    assert (anchor.start, anchor.end, anchor.quote) == (30, 33, "(أ)")
    assert annotation.link_method == "marker_match" and annotation.status == "verified"


def test_nested_issue(result):
    [issue] = [i for i in result.issues if i.code == "nested_footnote"]
    assert issue.target_id == "b000215"
    assert issue.details == {
        "parent_footnote": "b000210",
        "parent_start": 30,
        "parent_end": 33,
        "candidates": 1,
    }


def test_no_unlinked_footnotes_on_sample(result):
    assert [i for i in result.issues if i.code == "unlinked_footnote"] == []


def test_301_annotations_cover_every_footnote(result, sample_book):
    assert len(result.annotations) == 301
    covered = set(result.by_target())
    footnotes = {b.block_id for b in sample_book.blocks.values() if b.kind == "footnote"}
    assert footnotes == covered


def test_orphan_footnote_is_unlinked(sample_book):
    orphan = sample_book.block("b000215").model_copy(update={"marker": "ب"})
    book = sample_book.model_copy(update={"blocks": {**sample_book.blocks, "b000215": orphan}})
    result = link_nested(book, join_continuations(book, resolve_refs(book)))
    [issue] = [i for i in result.issues if i.code == "unlinked_footnote"]
    assert issue.target_id == "b000215" and not any(a.type == "nested_footnote" for a in result.annotations)
