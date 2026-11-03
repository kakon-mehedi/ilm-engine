import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.units import assemble_units, detect_entries, with_section_membership
from ilm_engine.processors.annotations import build as build_annotations
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build as build_structure
from ilm_engine.search import semantic
from ilm_engine.search.lexical import build_index, search

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def index_and_units(sample_book):
    config = load_config(PUB_ID)
    origins = assign(sample_book, config).blocks
    structure = build_structure(sample_book)
    units, _ = assemble_units(
        sample_book,
        detect_entries(sample_book, origins, config),
        build_annotations(sample_book).annotations,
        structure,
        config,
    )
    units = with_section_membership(sample_book, units, structure)
    return build_index(sample_book, units), units


def test_feature_off_by_default():
    assert load_config().features.semantic_search is False


def test_falls_back_to_lexical_without_model(index_and_units, monkeypatch, tmp_path):
    monkeypatch.setattr(semantic, "_model", lambda name=semantic.MODEL_NAME: None)
    index, _ = index_and_units
    assert semantic.vectors(index, tmp_path) is None
    assert semantic.hybrid_search(index, "هند بنت عتيق", cache_dir=tmp_path) == search(index, "هند بنت عتيق")


@pytest.mark.skipif(not semantic.is_available(), reason="sentence-transformers / BGE-M3 not installed")
def test_sons_of_abbas_in_top_5(index_and_units, tmp_path):
    index, units = index_and_units
    abbas = {u.unit_id for u in units if u.payload.get("section_subject") == "العباس بن عبد المطلب"}
    hits = semantic.hybrid_search(index, "أبناء العباس", limit=5, cache_dir=tmp_path)
    assert any(hit.doc_id in abbas for hit in hits)
