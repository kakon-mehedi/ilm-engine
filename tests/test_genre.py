import json

import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.genres import registry
from ilm_engine.extractors.genres.hadith import UnitSchema as HadithUnit
from ilm_engine.extractors.genres.hadith import parse_takhrij, sensitive_categories
from ilm_engine.processors.genre import metadata_fields, route

GENRES = {"fiqh", "hadith", "tafsir", "seerah", "aqeedah", "history", "biography"}


@pytest.fixture(scope="module")
def decision(sample_book):
    return route(sample_book, load_config())


def test_sample_is_biography_ansab_with_hadith(decision):
    assert (decision.primary, decision.sub_type) == ("biography", "ansab")
    assert "hadith" in decision.secondary
    assert decision.signals["hadith"]["takhrij"] >= 3 and decision.confidence == 0.95


def test_signals_have_anchored_evidence(decision, sample_book):
    anchors = decision.evidence["hadith"]
    assert anchors and all(sample_book.block(a.block_id).text[a.start : a.end] == a.quote for a in anchors)
    assert all(sample_book.block(a.block_id).kind == "footnote" for a in anchors)


def test_all_seven_schemas_registered():
    plugins = registry()
    assert set(plugins) == GENRES
    for plugin in plugins.values():
        assert plugin.unit_schema.model_json_schema()["title"] == "UnitSchema"
        assert plugin.prompt_task


def test_sensitive_fields_declared_and_marked():
    plugins = registry()
    assert plugins["hadith"].sensitive_fields["grading"] == "hadith_grading"
    assert plugins["fiqh"].sensitive_fields == {"hukm": "fiqh_ruling"}
    assert plugins["aqeedah"].sensitive_fields == {"proposition": "aqeedah_proposition"}
    schema = plugins["hadith"].unit_schema.model_json_schema()
    assert schema["properties"]["grading"]["sensitive"] is True


def test_b000228_takhrij_with_sensitive_grading(sample_book):
    unit = parse_takhrij(sample_book.block("b000228").text)
    assert unit.grading.label_raw == "ضعيف" and unit.grading.label == "daif"
    assert unit.grading.reason == "لكثرة المجاهيل" and unit.grading.quote == "وإسناده ضعيف لكثرة المجاهيل"
    assert sensitive_categories(unit) == ["hadith_grading"]
    first = unit.takhrij[0]
    assert (first.collector, first.work, first.volume, first.page, first.number) == (
        "الطبراني",
        "الكبير",
        3,
        166,
        3258,
    )
    assert any(ref.work == "أسد الغابة" and (ref.volume, ref.page) == (2, 55) for ref in unit.takhrij)


def test_non_takhrij_footnote(sample_book):
    assert parse_takhrij("انظر ترجمته في الإصابة") is None


def test_hadith_payload_round_trip(sample_book):
    unit = parse_takhrij(sample_book.block("b000228").text)
    assert HadithUnit.model_validate(json.loads(unit.model_dump_json())) == unit


def test_genre_metadata_fields(decision):
    primary, secondary = metadata_fields(decision, load_config())
    assert primary.value == {"genre": "biography", "sub_type": "ansab"}
    assert primary.assertion == "inferred" and primary.origin == "ai_generated"
    assert [field.value["genre"] for field in secondary] == decision.secondary


def test_no_category_falls_back_to_content(sample_book):
    bare = sample_book.model_copy(
        update={"metadata": sample_book.metadata.model_copy(update={"category_name": None})}
    )
    decision = route(bare, load_config())
    assert decision.primary == "hadith" and decision.confidence == 0.75
