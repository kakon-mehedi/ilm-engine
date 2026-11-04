import json

import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.units import assemble_units, detect_entries
from ilm_engine.processors.annotations import build as build_annotations
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build as build_structure
from ilm_engine.search.lexical import build_index, search, tokens

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def units(sample_book):
    config = load_config(PUB_ID)
    origins = assign(sample_book, config).blocks
    result, _ = assemble_units(
        sample_book,
        detect_entries(sample_book, origins, config),
        build_annotations(sample_book).annotations,
        build_structure(sample_book),
        config,
    )
    return result


@pytest.fixture(scope="module")
def index(sample_book, units):
    return build_index(sample_book, units)


def test_diacritic_variants_give_identical_results(index):
    plain, marked = search(index, "الدارقطني"), search(index, "الدَّارقطني")
    assert plain and [hit.doc_id for hit in plain] == [hit.doc_id for hit in marked]


def test_hind_bint_atiq_ranks_unit_8_first(index, units):
    eight = next(u for u in units if u.entry_no == 8)
    [first, *_] = search(index, "هند بنت عتيق")
    assert first.doc_id == eight.unit_id and first.kind == "unit"
    assert first.anchor["block_id"] == "b000135"


def test_spelling_variant_of_title(index):
    assert [h.doc_id for h in search(index, "الاخوة")] == [h.doc_id for h in search(index, "الأُخوة")]


def test_hits_carry_original_anchors(index, sample_book):
    for hit in search(index, "أسلمت", limit=5):
        anchor = hit.anchor
        assert sample_book.block(anchor["block_id"]).text.startswith(anchor["quote"])


def test_index_is_json_and_deterministic(sample_book, units, index):
    assert json.dumps(index, ensure_ascii=False, sort_keys=True) == json.dumps(
        build_index(sample_book, units), ensure_ascii=False, sort_keys=True
    )
    indexed = {d["doc_id"] for d in index["documents"] if d["kind"] == "block"}
    wordless = {
        b.block_id for b in sample_book.blocks.values() if not tokens(b.text)
    }  # "* * * * *" separators
    assert indexed == set(sample_book.blocks) - wordless and len(wordless) == 11


def test_kind_filter_and_unknown_query(index):
    assert {h.kind for h in search(index, "هند", kinds={"unit"})} == {"unit"}
    assert search(index, "zzzz") == []


def test_tokens():
    assert tokens("رسول الله -صلى الله عليه وسلم-") == ["رسول", "الله", "<SAW>"]
