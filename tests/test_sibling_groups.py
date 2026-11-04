import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.entities import build_entities
from ilm_engine.extractors.relations import sibling_groups
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
    result = sibling_groups(sample_book, linked, people.entities, config)
    return result, {u.entry_no: u.subject_entity_id for u in linked}


def group_of(result, number_ids, *numbers):
    ids = {number_ids[n] for n in numbers}
    return [g for g in result.groups if {u.subject_entity_id for u in g.members} == ids]


def test_9_and_10_grouped_by_abna_abi_hala(built):
    result, ids = built
    [group] = group_of(result, ids, 9, 10)
    assert group.word == "ابنا" and group.anchor.block_id == "b000137" and group.grammar_ok
    siblings = [
        r for r in result.relationships if r.type == "sibling_of" and r.attrs.group_id == group.group_id
    ]
    assert [(r.subject_entity_id, r.object_entity_id) for r in siblings] == [(ids[9], ids[10])]
    parents = {
        r.subject_entity_id: r.object_entity_id
        for r in result.relationships
        if r.type == "child_of" and r.attrs.group_id == group.group_id
    }
    assert set(parents) == {ids[9], ids[10]} and len(set(parents.values())) == 1
    parent = next(e for e in result.entities if e.entity_id == parents[ids[9]])
    assert parent.name.kunya == "أبي هالة" and parent.name.ism == "مالك"


def test_entry_9_becomes_male_hind_ibn_abi_hala(built):
    result, ids = built
    nine = next(e for e in result.entities if e.entity_id == ids[9])
    assert nine.gender == "m" and nine.canonical_name == "هند بن أبي هالة" and nine.name.nasab[0] == "مالك"
    eight = next(e for e in result.entities if e.entity_id == ids[8])
    assert eight.gender == "f"


def test_18_to_21_banu_abd_al_muttalib(built):
    result, ids = built
    [group] = group_of(result, ids, 18, 19, 20, 21)
    assert group.word == "بنو" and group.anchor.block_id == "b000218"
    assert (
        len(
            [r for r in result.relationships if r.type == "sibling_of" and r.attrs.group_id == group.group_id]
        )
        == 6
    )


def test_other_groups(built):
    result, ids = built
    assert group_of(result, ids, 40, 41) and group_of(result, ids, 62, 63) and group_of(result, ids, 64, 65)
    assert group_of(result, ids, 22, 23, 24, 25, 26)


def test_narrative_dual_is_not_a_closure(built):
    result, _ = built
    assert not any(g.anchor.block_id in ("b000147", "b000414") for g in result.groups)


def test_banat_keeps_daughters_only(built):
    result, ids = built
    [group] = [g for g in result.groups if g.word == "بنات"]
    assert ids[42] not in {u.subject_entity_id for u in group.members}  # الحارث بن العباس


def test_evidence_exact(built, sample_book):
    for relation in built[0].relationships:
        anchor = relation.evidence[0]
        assert sample_book.block(anchor.block_id).text[anchor.start : anchor.end] == anchor.quote
