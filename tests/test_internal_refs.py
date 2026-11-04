import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.units import detect_entries, unit_id
from ilm_engine.processors.citations import internal_refs
from ilm_engine.processors.origin import assign

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def units(sample_book):
    config = load_config(PUB_ID)
    entries = detect_entries(sample_book, assign(sample_book, config).blocks, config).entries
    return {entry.entry_no: unit_id(sample_book.book.pub_ref, entry) for entry in entries}


@pytest.fixture(scope="module")
def result(sample_book, units):
    return internal_refs(sample_book, units)


def refs_in(result, block_id):
    return [ref for ref in result.refs if ref.anchor.block_id == block_id]


def test_b000063_links_to_entry_33(result, units):
    [ref] = refs_in(result, "b000063")
    assert ref.kind == "entry_number" and ref.target_entry_no == 33
    assert ref.target_unit_id == units[33] and ref.status == "resolved"
    assert ref.anchor.quote == "ترجمة رقم (٣٣)" and (ref.anchor.start, ref.anchor.end) == (60, 74)


def test_hadith_number_is_not_an_internal_ref(result, sample_book):
    assert "رقم: ١٣٨٢" in sample_book.block("b000133").text
    assert refs_in(result, "b000133") == []


def test_numbered_backward_refs_resolve(result, units):
    [ref] = refs_in(result, "b000570")  # "تقدمت برقم (٧٤)"
    assert ref.kind == "entry_number" and ref.target_unit_id == units[74]


def test_forward_refs_unresolved(result):
    forward = [ref for ref in result.refs if ref.kind == "forward"]
    assert {ref.anchor.block_id for ref in forward} >= {"b000055", "b000169", "b000226", "b000228"}
    assert {ref.status for ref in forward} == {"unresolved"}


def test_page_backward_ref_keeps_page(result):
    [ref] = refs_in(result, "b000491")  # "تقدمت ترجمته (ص: ٢٨)"
    [issue] = [i for i in result.issues if i.target_id == ref.internal_ref_id]
    assert (
        ref.kind == "backward"
        and issue.code == "unresolved_internal_ref"
        and issue.details["printed_page"] == 28
    )


def test_words_containing_taqaddum_are_ignored(result):
    assert refs_in(result, "b000044") == []  # "التقدم في القراءات"
    assert all(ref.kind != "backward" for ref in refs_in(result, "b000214"))  # "متقدم"
    assert refs_in(result, "b000458") == []  # "يتقدم"


def test_anchors_exact(result, sample_book):
    for ref in result.refs:
        assert (
            sample_book.block(ref.anchor.block_id).text[ref.anchor.start : ref.anchor.end] == ref.anchor.quote
        )


def test_feminine_suffix_keeps_page(result):
    [ref] = refs_in(result, "b000492")  # "تقدمت ترجمتها (ص: ٢٨)"
    assert ref.anchor.quote == "تقدمت ترجمتها (ص: ٢٨)"


def test_comma_before_number(result, units):
    [ref] = refs_in(result, "b000493")  # "تقدمت ترجمتها، برقم (١٤)"
    assert ref.target_unit_id == units[14]


def test_number_after_citation_locator_is_hadith_number(result):
    assert refs_in(result, "b000214") == []  # '"الكبير" (١/ ٣٢) رقم (٩٩)'
