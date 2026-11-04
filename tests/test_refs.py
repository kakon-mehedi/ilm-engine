import pytest

from ilm_engine.canonical.models import Ref
from ilm_engine.processors.annotations import is_entry_marker, marker_key, resolve_refs


@pytest.fixture(scope="module")
def result(sample_book):
    return resolve_refs(sample_book)


def test_300_annotations_all_resolved(result):
    assert len(result.annotations) == 300
    assert {a.status for a in result.annotations} == {"verified"}
    assert [i for i in result.issues if i.code == "broken_ref"] == []


def test_refs_at_offset_zero_and_entry_notes(result, sample_book):
    assert sum(a.marker_anchor.start == 0 for a in result.annotations) == 59
    entry_notes = {a.target_block_ids[0] for a in result.annotations if a.is_entry_note}
    assert len(entry_notes) == 74
    assert all(is_entry_marker(sample_book.block(b).marker) for b in entry_notes)


def test_b000018_ref(result):
    [annotation] = [
        a for a in result.annotations if a.source_block_id == "b000018" and a.marker_anchor.start == 38
    ]
    assert annotation.marker_anchor.end == 41 and annotation.target_block_ids == ["b000020"]
    assert annotation.link_method == "source_ref" and annotation.origin == "editor_footnote"


def test_entry_note_example(result):
    [annotation] = [
        a for a in result.annotations if a.source_block_id == "b000105" and a.marker_anchor.start == 0
    ]
    assert annotation.marker_anchor.quote == "١ -" and annotation.target_block_ids == ["b000109"]
    assert annotation.is_entry_note and annotation.marker_text == "١ -"


def test_anchor_quotes_are_original_text(result, sample_book):
    for annotation in result.annotations:
        anchor = annotation.marker_anchor
        assert sample_book.block(anchor.block_id).text[anchor.start : anchor.end] == anchor.quote


def test_broken_ref_to_missing_block(sample_book):
    block = sample_book.block("b000135")
    broken = block.model_copy(update={"refs": [Ref(start=25, end=28, to="b999999")]})
    book = sample_book.model_copy(update={"blocks": {**sample_book.blocks, "b000135": broken}})
    result = resolve_refs(book)
    [annotation] = [a for a in result.annotations if a.source_block_id == "b000135"]
    assert annotation.status == "unlinked" and annotation.target_block_ids == []
    [issue] = [i for i in result.issues if i.code == "broken_ref"]
    assert issue.details["to"] == "b999999"


def test_span_not_matching_marker(sample_book):
    block = sample_book.block("b000135")
    wrong = block.model_copy(update={"refs": [Ref(start=25, end=28, to="b000141")]})  # (١) → marker ٢
    book = sample_book.model_copy(update={"blocks": {**sample_book.blocks, "b000135": wrong}})
    [annotation] = [a for a in resolve_refs(book).annotations if a.source_block_id == "b000135"]
    assert annotation.status == "candidate"


def test_marker_key():
    assert marker_key("(١)") == marker_key("١") == "١"
    assert marker_key("٨ -") == "٨ -"


def test_ids_deterministic(sample_book, result):
    assert [a.annotation_id for a in resolve_refs(sample_book).annotations] == [
        a.annotation_id for a in result.annotations
    ]
