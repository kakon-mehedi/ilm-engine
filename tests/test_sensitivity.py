from ilm_engine.config import load_config
from ilm_engine.extractors.genres import registry
from ilm_engine.extractors.genres.hadith import parse_takhrij
from ilm_engine.validation.confidence import decide
from ilm_engine.validation.sensitivity import (
    categories,
    enforce,
    payload_categories,
    sensitive_issue,
    tag_block,
)


def tags_of(book, block_id, genres=()):
    block = book.block(block_id)
    return tag_block(block, book.book.pub_ref, book.page(block.page).scan_page, genres)


def test_b000228_grading_is_sensitive_even_when_confident(sample_book):
    tags = tags_of(sample_book, "b000228")
    grading = [tag for tag in tags if tag.category == "hadith_grading"]
    assert grading and grading[0].anchor.quote == "وإسناده ضعيف"
    status = enforce(decide(load_config(), 0.95), categories(tags))
    assert decide(load_config(), 0.95) == "auto_approved" and status == "pending_review"


def test_the_8_c1_spans_are_prophetic_attribution(sample_book):
    span_tags = [
        tag
        for block in sample_book.blocks.values()
        for tag in tags_of(sample_book, block.block_id)
        if tag.rule == "span_class"
    ]
    assert len(span_tags) == 8 and {tag.category for tag in span_tags} == {"prophetic_attribution"}
    b131 = [tag for tag in span_tags if tag.anchor.block_id == "b000131"]
    assert b131 and (b131[0].anchor.start, b131[0].anchor.end) == (31, 66)


def test_prophetic_formula_lexicon(sample_book):
    block = sample_book.block("b000135")
    fake = block.model_copy(
        update={"text": "قال رسول الله -صلى الله عليه وسلم-: إنما الأعمال بالنيات", "spans": [], "refs": []}
    )
    assert [tag.category for tag in tag_block(fake, "p@r1", 25)] == ["prophetic_attribution"]


def test_fiqh_lexicon_only_in_fiqh_books(sample_book):
    block = sample_book.block("b000135").model_copy(update={"text": "ولا يجوز ذلك", "spans": [], "refs": []})
    assert tag_block(block, "p@r1", 25) == []
    assert categories(tag_block(block, "p@r1", 25, genres=["fiqh"])) == ["fiqh_ruling"]


def test_plain_entry_is_not_sensitive(sample_book):
    assert tags_of(sample_book, "b000135") == []


def test_schema_fields(sample_book):
    unit = parse_takhrij(sample_book.block("b000228").text)
    plugin = registry()["hadith"]
    assert payload_categories(unit.model_dump(), plugin.sensitive_fields) == ["hadith_grading"]
    assert payload_categories({"hukm": {"label": "haram"}}, registry()["fiqh"].sensitive_fields) == [
        "fiqh_ruling"
    ]


def test_issue(sample_book):
    tags = tags_of(sample_book, "b000228")
    issue = sensitive_issue(
        sample_book.book.pub_ref, "unit", "ku_1", categories(tags), [t.anchor for t in tags]
    )
    assert issue.code == "sensitive_content" and issue.details["categories"] == ["hadith_grading"]


def test_enforce_keeps_non_auto_statuses():
    assert enforce("rejected", ["hadith_grading"]) == "rejected"
    assert enforce("auto_approved", []) == "auto_approved"
