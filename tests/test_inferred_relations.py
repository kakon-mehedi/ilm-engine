import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.entities import PROPHET_ID, build_entities
from ilm_engine.extractors.relations import inferred_relations, relation_kinds, sibling_groups
from ilm_engine.extractors.units import assemble_units, detect_entries, with_section_membership
from ilm_engine.processors.annotations import build as build_annotations
from ilm_engine.processors.metadata import card_metadata
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build as build_structure

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def built(sample_book):
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
    people = build_entities(sample_book, units, card_metadata(sample_book, config)[0], origins, config)
    linked = [u.model_copy(update={"subject_entity_id": people.unit_subjects[u.unit_id]}) for u in units]
    result = sibling_groups(sample_book, linked, people.entities, config)
    result = inferred_relations(
        sample_book, linked, relation_kinds(sample_book, linked, result, config), config
    )
    return result, {u.entry_no: u.subject_entity_id for u in linked}


def test_fatima_child_of_prophet(built):
    result, ids = built
    [relation] = [
        r
        for r in result.relationships
        if r.type == "child_of" and r.subject_entity_id == ids[1] and r.object_entity_id == PROPHET_ID
    ]
    assert relation.assertion == "inferred" and relation.origin == "ai_generated"
    assert [a.block_id for a in relation.evidence] == ["b000104", "b000105"]


def test_no_inferred_relation_auto_approved(built):
    inferred = [r for r in built[0].relationships if r.assertion == "inferred"]
    assert inferred and {r.review_status for r in inferred} == {"pending_review"}
    assert {r.origin for r in inferred} == {"ai_generated"}


def test_khadija_section_maternal_siblings(built):
    result, ids = built
    maternal = [
        r
        for r in result.relationships
        if r.type == "sibling_of" and r.assertion == "inferred" and r.subject_entity_id == ids[8]
    ]
    assert maternal and {r.attrs.kind for r in maternal} == {"maternal"}
    assert ids[1] in {r.object_entity_id for r in maternal}
    assert maternal[0].evidence[0].block_id == "b000134"


def test_stated_parent_outranks_heading(built):
    result, ids = built
    parents = [r for r in result.relationships if r.type == "child_of" and r.subject_entity_id == ids[18]]
    assert [r.assertion for r in parents] == ["stated"]  # "بنو عبد المطلب" closure, no inferred duplicate
