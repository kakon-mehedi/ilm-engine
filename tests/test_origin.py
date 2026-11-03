import pytest

from ilm_engine.config import load_config
from ilm_engine.processors.origin import assign

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def origin_map(sample_book):
    return assign(sample_book, load_config(PUB_ID))


def test_all_footnotes_editor_footnote(origin_map, sample_book):
    footnotes = [b for b in sample_book.blocks.values() if b.kind == "footnote"]
    assert len(footnotes) == 317
    assert {origin_map.blocks[b.block_id] for b in footnotes} == {"editor_footnote"}


@pytest.mark.parametrize(
    "block_id, origin",
    [
        ("b000098", "author_text"),
        ("b000093", "transmission_isnad"),
        ("b000018", "editor_text"),
        ("b000135", "author_text"),
        ("b000109", "editor_footnote"),
        ("b000081", "transmission_isnad"),  # manuscript title page, p.17 (override)
        ("b000588", "transmission_isnad"),  # copyist note, end of p.72 (override)
        ("b000587", "author_text"),
    ],
)
def test_sample_blocks(origin_map, block_id, origin):
    assert origin_map.blocks[block_id] == origin


def test_every_block_exactly_one_origin(origin_map, sample_book):
    assert set(origin_map.blocks) == set(sample_book.blocks)
    assert "ai_generated" not in origin_map.blocks.values()
    assert sum(origin_map.counts().values()) == 594


def test_isnad_found_by_rule_without_override(sample_book):
    rules_only = assign(sample_book, load_config())
    assert (
        rules_only.blocks["b000093"] == "transmission_isnad"
        and rules_only.rules["b000093"] == "isnad_formula"
    )
    assert rules_only.blocks["b000081"] == "editor_text"  # needs the per-book override


def test_overrides_listed(origin_map):
    applied = {tuple(item.get("pages", item.get("blocks"))): item for item in origin_map.overrides_applied}
    assert applied[(17, 17)]["origin"] == "transmission_isnad" and "b000081" in applied[(17, 17)]["changed"]
    assert applied[("b000588", "b000589")]["changed"] == ["b000588", "b000589"]


def test_spans(origin_map):
    first = origin_map.spans[0]
    assert first.origin == "editor_text" and first.start_page == 3
    isnad = next(s for s in origin_map.spans if s.rule == "isnad_formula")
    assert (isnad.start_block_id, isnad.end_block_id, isnad.block_count) == ("b000093", "b000093", 1)
    author = next(s for s in origin_map.spans if s.start_block_id == "b000098")
    assert author.origin == "author_text" and author.end_block_id == "b000587" and author.end_page == 72
    assert sum(s.block_count for s in origin_map.spans) == 594 - 317


def test_json(origin_map):
    data = origin_map.to_json()
    assert data["counts"]["editor_footnote"] == 317 and data["blocks"]["b000135"] == "author_text"
