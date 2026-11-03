import pytest

from ilm_engine.config import load_config
from ilm_engine.processors.metadata import card_metadata, detect_language, parse_edition


@pytest.fixture(scope="module")
def metadata(sample_book):
    record, _ = card_metadata(sample_book, load_config("pub_01M0CJECV4ZHFTP02BJQ6D3STJ"))
    return record


def test_card_values(metadata):
    assert metadata.title.value == "الإخوة والأخوات"
    assert metadata.author.value["name"] == "أبو الحسن علي بن عمر بن أحمد الدارقطني"
    assert metadata.author.value["death_hijri"] == 385
    assert metadata.editor.value == "باسم فيصل أحمد الجوابرة"
    assert metadata.publisher.value == "دار الراية للنشر والتوزيع، الرياض - السعودية"
    assert metadata.edition.normalized["number"] == 1
    assert metadata.year_hijri.value == 1413 and metadata.year_gregorian.value == 1993
    assert metadata.category.value == "الأنساب" and metadata.category.normalized == {"id": "27"}
    assert metadata.edition.normalized["declared_pages"] == 72
    assert metadata.volumes.value == 1 and metadata.language.value == "ar"


def test_provenance_of_card_fields(metadata):
    field = metadata.editor
    assert [(s.kind, s.path) for s in field.sources] == [
        ("existing_metadata", "metadata.source_attributes.editor")
    ]
    assert field.assertion == "stated" and field.confidence == 0.95 and field.review_status == "auto_approved"
    assert metadata.language.sources[0].kind == "book_content"


def test_genre_left_for_genre_step(metadata):
    assert metadata.genre_primary.value is None and metadata.genre_secondary == []


def test_parse_edition():
    assert parse_edition("الأولى، ١٤١٣ هـ - ١٩٩٣ م") == {
        "number": 1,
        "year_hijri": 1413,
        "year_gregorian": 1993,
    }
    assert parse_edition("الثانية") == {"number": 2, "year_hijri": None, "year_gregorian": None}


def test_language(sample_book):
    assert detect_language(sample_book) == "ar"


def test_missing_fields_reported(sample_book):
    bare = sample_book.model_copy(
        update={"metadata": sample_book.metadata.model_copy(update={"editor": None})}
    )
    record, _ = card_metadata(bare, load_config())
    assert "editor" in record.missing_fields and record.editor.value is None
