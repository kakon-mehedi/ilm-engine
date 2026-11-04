import pytest

from ilm_engine.config import load_config
from ilm_engine.enrichment.models import PersonName
from ilm_engine.extractors.entities import build_entities, same_person
from ilm_engine.extractors.units import assemble_units, detect_entries
from ilm_engine.nlp.normalize import normalize
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
    return build_entities(sample_book, units, card_metadata(sample_book, config)[0], origins, config), {
        u.entry_no: u for u in units
    }


def test_daraqutni_mentions_merge_into_one_entity(built):
    result, _ = built
    [author] = [e for e in result.entities if "author" in e.roles]
    blocks = {m.block_id for m in author.mentions}
    assert {"b000004", "b000043", "b000083"} <= blocks
    assert len(author.aliases) >= 3
    assert any("\u0651" in alias and normalize(alias) == "الدارقطني" for alias in author.aliases)  # الدَّارقطني
    assert not [e for e in result.entities if e is not author and e.name and e.name.nisba == ["الدارقطني"]]


def test_hind_8_and_9_stay_separate(built):
    result, units = built
    assert result.unit_subjects[units[8].unit_id] != result.unit_subjects[units[9].unit_id]


def test_never_merge_on_ism_alone():
    assert not same_person(
        PersonName(ism="هند", full_surface="هند"),
        PersonName(ism="هند", nasab=["عتيق", "عابد"], full_surface="هند"),
    )
    assert same_person(
        PersonName(ism="علي", nasab=["عمر", "أحمد"], full_surface="a"),
        PersonName(ism="علي", nasab=["عمر", "أحمد", "مهدي"], full_surface="b"),
    )
    assert same_person(
        PersonName(ism=None, kunya="أبو الحسن", nisba=["الدارقطني"], full_surface="a"),
        PersonName(ism="علي", kunya="أبو الحسن", nisba=["الدارقطني"], full_surface="b"),
    )


def test_mentions_exact(built, sample_book):
    for entity in built[0].entities:
        for anchor in entity.mentions:
            assert sample_book.block(anchor.block_id).text[anchor.start : anchor.end] == anchor.quote
