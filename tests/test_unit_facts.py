import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.units import assemble_units, detect_entries, with_rule_facts
from ilm_engine.processors.annotations import build as build_annotations
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build as build_structure

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def units(sample_book):
    config = load_config(PUB_ID)
    origins = assign(sample_book, config).blocks
    detection = detect_entries(sample_book, origins, config)
    assembled, _ = assemble_units(
        sample_book,
        detection,
        build_annotations(sample_book).annotations,
        build_structure(sample_book),
        config,
    )
    return {u.entry_no: u for u in with_rule_facts(sample_book, assembled, origins, config)}


def test_unit_8_facts(units):
    facts = [
        (f.predicate, f.object, f.evidence[0].start, f.evidence[0].end, f.evidence[0].quote)
        for f in units[8].facts
    ]
    assert facts == [
        ("converted_to_islam", True, 60, 65, "أسلمت"),
        ("married", True, 70, 76, "وتزوجت"),
        ("has_narration", False, 78, 97, "ولم يُروَ عنها شيءٌ"),
    ]
    first = units[8].facts[0]
    assert (
        first.fact_id == units[8].unit_id + "#f1"
        and first.origin == "author_text"
        and first.assertion == "stated"
    )
    assert first.confidence == 0.95 and first.review_status == "auto_approved"


def test_every_fact_anchor_exact(units, sample_book):
    count = 0
    for unit in units.values():
        for fact in unit.facts:
            anchor = fact.evidence[0]
            assert sample_book.block(anchor.block_id).text[anchor.start : anchor.end] == anchor.quote
            assert any(
                a.block_id == anchor.block_id and a.start <= anchor.start < a.end for a in unit.anchors
            )
            count += 1
    assert count > 10


def test_companion_status(units):
    sahaba = [(n, f.object) for n, u in units.items() for f in u.facts if f.predicate == "is_sahabi"]
    assert (67, True) in sahaba  # "(وحارثة) بن وهب الخُزاعي وله صحبة"


def test_no_false_islam_from_al_islam(units):
    for unit in units.values():
        for fact in unit.facts:
            if fact.predicate == "converted_to_islam":
                assert "الإسلام" not in fact.evidence[0].quote


def test_death_years(units):
    deaths = {n: f.object for n, u in units.items() for f in u.facts if f.predicate == "death_hijri"}
    assert deaths[7] == 10  # "وتوفي في شهر ربيع الأول سنة عشر"
    assert 32 not in deaths  # "ومات أبو سفيان بن الحارث سنة عشرين" is someone else's death
    for unit in units.values():
        for fact in unit.facts:
            assert fact.evidence[0].quote == fact.evidence[0].quote.strip()
