import pytest

from ilm_engine.config import load_config
from ilm_engine.processors.metadata import card_metadata, content_metadata
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def result(sample_book):
    config = load_config(PUB_ID)
    record, _ = card_metadata(sample_book, config)
    return content_metadata(
        sample_book, record, assign(sample_book, config).blocks, build(sample_book), config
    )


def finding(result, field):
    return [f for f in result[1] if f.field == field]


def test_death_year_from_b000049(result):
    deaths = finding(result, "author.death_hijri")
    b49 = [f for f in deaths if f.anchors[0].block_id == "b000049"]
    assert b49 and b49[0].value == 385
    anchor = b49[0].anchors[0]
    assert (anchor.start, anchor.end, anchor.quote) == (24, 51, "سنةٍ خمسٍ وثمانين وثلاث مئة")


def test_death_year_on_title_page(result):
    deaths = finding(result, "author.death_hijri")
    assert any(f.anchors[0].block_id == "b000005" and f.value == 385 for f in deaths)


def test_author_field_has_book_content_source(result):
    record = result[0]
    assert record.author.value["death_hijri"] == 385
    kinds = [source.kind for source in record.author.sources]
    assert kinds[0] == "existing_metadata" and "book_content" in kinds
    anchors = [a.block_id for s in record.author.sources if s.kind == "book_content" for a in s.anchors]
    assert "b000049" in anchors


def test_title_page_title_and_editor(result):
    [title] = finding(result, "title")
    assert title.value == "الأُخوة والأَخوات" and title.anchors[0].block_id == "b000001"
    [editor] = finding(result, "editor")
    assert editor.value == "الدكتور باسم فيصل أحمد الجوابرة" and editor.anchors[0].block_id == "b000008"
    [author] = finding(result, "author.name")
    assert author.anchors[0].block_id == "b000004"


def test_volume_note_part_1_of_2(result):
    note = result[0].volume_note
    assert note.value == {"part": 1, "of_at_least": 2}
    assert [a.block_id for a in note.sources[0].anchors] == ["b000002", "b000591"]


def test_anchors_match_exactly(result, sample_book):
    for item in result[1]:
        for anchor in item.anchors:
            assert sample_book.block(anchor.block_id).text[anchor.start : anchor.end] == anchor.quote


def test_needs_llm_without_provider(result):
    assert [i.code for i in result[2]] == ["needs_llm"]
