import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.entities import build_entities
from ilm_engine.extractors.relations import relation_kinds, sibling_groups
from ilm_engine.extractors.units import assemble_units, detect_entries
from ilm_engine.processors.annotations import build as build_annotations
from ilm_engine.processors.metadata import card_metadata
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build as build_structure

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def built(sample_book):
    config = load_config(PUB_ID)
    origins = assign(sample_book, config).blocks
    units, _ = assemble_units(
        sample_book,
        detect_entries(sample_book, origins, config),
        build_annotations(sample_book).annotations,
        build_structure(sample_book),
        config,
    )
    people = build_entities(sample_book, units, card_metadata(sample_book, config)[0], origins, config)
    linked = [u.model_copy(update={"subject_entity_id": people.unit_subjects[u.unit_id]}) for u in units]
    result = relation_kinds(
        sample_book, linked, sibling_groups(sample_book, linked, people.entities, config), config
    )
    return result, {u.entry_no: u.subject_entity_id for u in linked}


def sibling(result, a, b):
    return next(
        r
        for r in result.relationships
        if r.type == "sibling_of" and {r.subject_entity_id, r.object_entity_id} == {a, b}
    )


def mother_names(result, child):
    names = {e.entity_id: e.canonical_name for e in result.entities}
    return [
        names[r.object_entity_id]
        for r in result.relationships
        if r.type == "mother_is" and r.subject_entity_id == child
    ]


def test_umm_walad_is_not_maternal(built):
    result, ids = built
    relation = sibling(result, ids[40], ids[41])  # b000349 "ابنا العباس لأم ولد"
    assert relation.attrs.kind == "paternal" and relation.attrs.mother_status == "umm_walad"
    assert relation.evidence[0].block_id == "b000349"


def test_same_named_mother_gives_full_siblings(built):
    result, ids = built
    relation = sibling(result, ids[62], ids[63])  # "ابنا عمر، أمهما أم كلثوم بنت علي بن أبي طالب"
    assert relation.attrs.kind == "full"
    assert mother_names(result, ids[62]) == mother_names(result, ids[63]) == ["أم كلثوم بنت علي بن أبي طالب"]


def test_mother_of_single_entry(built):
    result, ids = built
    assert mother_names(result, ids[7]) == ["مارية بنت شمعون القبطية"]  # "أمه مارية بنت شمعون القبطية"


def test_umm_walad_mother_named(built):
    result, ids = built
    [relation] = [r for r in result.relationships if r.type == "mother_is" and r.subject_entity_id == ids[72]]
    assert relation.attrs.mother_status == "umm_walad"


def test_plural_mother_statement_covers_section_entries(built):
    result, ids = built
    for number in range(33, 40):  # "أمهم أم الفضل لبابة بنت الحارث" closes #33–#39
        assert mother_names(result, ids[number]) == ["أم الفضل لبابة بنت الحارث بن حزن الهلالية"]


def test_maternal_sister_statement(built):
    result, ids = built
    relation = sibling(result, ids[71], ids[72])  # "وأخته لأمه:" then "٧٢ - زينب بنت عمر"
    assert relation.attrs.kind in ("full", "maternal") and relation.assertion == "stated"


def test_no_umm_walad_marked_maternal(built):
    for relation in built[0].relationships:
        if relation.attrs.mother_status == "umm_walad" and relation.type == "sibling_of":
            assert relation.attrs.kind != "maternal"


def test_evidence_exact(built, sample_book):
    for relation in built[0].relationships:
        anchor = relation.evidence[0]
        assert sample_book.block(anchor.block_id).text[anchor.start : anchor.end] == anchor.quote
