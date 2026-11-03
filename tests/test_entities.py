import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.entities import PROPHET_ID, build_entities
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
    metadata, _ = card_metadata(sample_book, config)
    return build_entities(sample_book, units, metadata, origins, config), {u.entry_no: u for u in units}


def subject(built, number):
    result, units = built
    return result.by_id()[result.unit_subjects[units[number].unit_id]]


def test_one_entity_per_entry_subject(built):
    result, units = built
    assert len(result.unit_subjects) == 75 and len(set(result.unit_subjects.values())) == 75
    assert len([e for e in result.entities if e.entity_type == "person"]) >= 75


def test_entry_8_entity(built, sample_book):
    hind = subject(built, 8)
    assert hind.gender == "f" and hind.name.nasab[0] == "عتيق"
    [mention] = hind.mentions
    assert (mention.block_id, mention.start, mention.end) == ("b000135", 4, 58)
    assert sample_book.block("b000135").text[mention.start : mention.end] == mention.quote


def test_entry_9_is_a_separate_hind(built):
    nine, eight = subject(built, 9), subject(built, 8)
    assert nine.entity_id != eight.entity_id and nine.name.ism == "هند" and nine.name.nasab == []
    assert nine.gender == "unknown"  # resolved to male by the group closure (T-082)


def test_prophet_authority(built, sample_book):
    prophet = built[0].by_id()[PROPHET_ID]
    assert set(prophet.aliases) == {"رسول الله", "النبي", "ﷺ"} and prophet.gender == "m"
    assert prophet.mentions and all(
        sample_book.block(a.block_id).text[a.start : a.end] == a.quote for a in prophet.mentions
    )


def test_author_and_editor(built):
    people = {e.roles[0]: e for e in built[0].entities if e.roles and e.roles[0] in ("author", "editor")}
    author = people["author"]
    assert author.name.kunya == "أبو الحسن" and author.name.nisba == ["الدارقطني"]
    assert author.external_ids == {"shamela_author": "223"} and author.mentions[0].block_id == "b000004"
    assert people["editor"].mentions[0].block_id == "b000008"
