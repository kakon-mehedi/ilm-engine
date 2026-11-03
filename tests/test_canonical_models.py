import hashlib

import pytest
from pydantic import ValidationError

from ilm_engine.canonical.models import Block, BookRef, CanonicalBook, Page, Span

# Real block b000135 (entry 8, page 25) from the sample book.
B135_TEXT = (
    "٨ - هند بنت عتيق بن عابد (١) بن عبد اللَّه بن عمر بن مخزوم؛ أسلمت (٢) وتزوجت، ولم يُروَ عنها شيءٌ (٣)."
)
B135_HASH = "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989"
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"


def text_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def block_b135(**overrides) -> dict:
    data = {
        "block_id": "b000135",
        "order": 1,
        "page": 25,
        "volume": 1,
        "kind": "text",
        "text": B135_TEXT,
        "refs": [
            {"start": 0, "end": 3, "to": "b000139"},
            {"start": 25, "end": 28, "to": "b000140"},
            {"start": 66, "end": 69, "to": "b000141"},
            {"start": 98, "end": 101, "to": "b000142"},
        ],
        "spans": [
            {"class": "c2", "start": 25, "end": 28, "text": "(١)", "meaning": "footnote_marker"},
            {"class": "c2", "start": 66, "end": 69, "text": "(٢)", "meaning": "footnote_marker"},
            {"class": "c2", "start": 98, "end": 101, "text": "(٣)", "meaning": "footnote_marker"},
        ],
        "block_hash": B135_HASH,
    }
    return {**data, **overrides}


def book_data(**overrides) -> dict:
    heading = "* وأخوة أولاد رسول اللَّه -صلى الله عليه وسلم- من أُمهم خديجة:"
    footnote = "(١) انظر: الإصابة (٨/ ١٥٧)."
    data = {
        "book": {
            "pub_id": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ",
            "revision": 6,
            "pub_ref": PUB_REF,
            "source_work_id": "wrk_01M0CJEXJ1ZJM9AEM1GYTHTYZE",
            "edition_id": "edt_01M49AFMMYHV5DGF9B2CQQBVBB",
        },
        "source": {
            "source_code": "src-shamela",
            "source_book_key": "26",
            "schema_version": "3.0",
            "source_adapter_semver": "1.3.0",
            "adapter_id": "shamela_v3",
            "adapter_version": "1.0.0",
            "claim_type": "faithful_to_source",
            "source_declared_hash": "1f974ece9429393b052de38052876b65ed195f83d3b6d55773691f2599f5c582",
        },
        "metadata": {
            "title_as_source": "الإخوة والأخوات",
            "author_as_source": "أبو الحسن علي بن عمر بن أحمد الدارقطني (ت ٣٨٥ هـ)",
            "author_name": "أبو الحسن علي بن عمر بن أحمد الدارقطني",
            "author_death_hijri": 385,
            "editor": "باسم فيصل أحمد الجوابرة",
            "publisher": "دار الراية للنشر والتوزيع، الرياض - السعودية",
            "edition": "الأولى، ١٤١٣ هـ - ١٩٩٣ م",
            "year_hijri": 1413,
            "year_gregorian": 1993,
            "category_id": "27",
            "category_name": "الأنساب",
            "claimed_page_count": 72,
            "page_numbering": "matches_print",
            "card": [{"label": "الكتاب", "value": "الإخوة والأخوات", "group": "book"}],
            "toc": [{"index": 8, "title": heading, "source_page_key": "21", "depth": 1}],
        },
        "quality": {
            "status": "imperfect",
            "passed": True,
            "claimed_pages": 72,
            "held_pages": 68,
            "short_pct": 5.555555555555555,
            "tolerance": "5%",
            "archive_code": "E-VAL-SHORT",
        },
        "scan": {"available": True, "volumes": [1], "file": "demo_book_daraqutni_v1.pdf", "page_count": 80},
        "pages": [
            {
                "volume": 1,
                "n": 25,
                "scan_page": 25,
                "source_key": "21",
                "source_url": "https://shamela.ws/book/26/21",
                "block_ids": ["b000134", "b000135", "b000139"],
            }
        ],
        "blocks": {
            "b000134": {
                "block_id": "b000134",
                "order": 0,
                "page": 25,
                "volume": 1,
                "kind": "heading",
                "text": heading,
                "block_hash": text_hash(heading),
            },
            "b000135": block_b135(),
            "b000139": {
                "block_id": "b000139",
                "order": 2,
                "page": 25,
                "volume": 1,
                "kind": "footnote",
                "text": footnote,
                "marker": "٨ -",
                "block_hash": text_hash(footnote),
            },
        },
        "raw_extras": {"timeline": [{"kind": "revision", "r": 6}]},
        "canonical_content_hash": "sha256:" + "0" * 64,
    }
    return {**data, **overrides}


@pytest.fixture
def book() -> CanonicalBook:
    return CanonicalBook.model_validate(book_data())


def test_contract_example_hash_matches_text():
    assert text_hash(B135_TEXT) == B135_HASH
    assert len(B135_TEXT) == 102
    assert B135_TEXT[60:65] == "أسلمت"
    assert B135_TEXT[78:97] == "ولم يُروَ عنها شيءٌ"


def test_block_is_frozen(book):
    with pytest.raises(ValidationError, match="frozen"):
        book.block("b000135").text = "x"


def test_nested_models_are_frozen(book):
    with pytest.raises(ValidationError, match="frozen"):
        book.pages[0].n = 1
    with pytest.raises(ValidationError, match="frozen"):
        book.book = book.book


def test_round_trip_is_lossless(book):
    restored = CanonicalBook.model_validate_json(book.model_dump_json())
    assert restored == book
    assert restored.model_dump_json() == book.model_dump_json()
    assert restored.block("b000135").text == B135_TEXT


def test_span_serializes_with_contract_name(book):
    span = book.block("b000135").model_dump()["spans"][0]
    assert span["class"] == "c2" and "cls" not in span


def test_span_accepts_python_name():
    assert Span(cls="c5", start=0, end=0, text="").cls == "c5"


def test_kind_rejects_unknown():
    with pytest.raises(ValidationError, match="kind"):
        Block.model_validate(block_b135(kind="paragraph"))


def test_unknown_field_rejected():
    with pytest.raises(ValidationError, match="Extra inputs"):
        Block.model_validate(block_b135(colour="red"))


def test_block_hash_format_enforced():
    with pytest.raises(ValidationError, match="block_hash"):
        Block.model_validate(block_b135(block_hash="56770406fa03"))


def test_offsets_outside_text_rejected():
    with pytest.raises(ValidationError, match="outside text"):
        Block.model_validate(block_b135(refs=[{"start": 100, "end": 103, "to": "b000142"}]))


def test_span_text_must_match_block_text():
    spans = [{"class": "c2", "start": 25, "end": 28, "text": "(٢)"}]
    with pytest.raises(ValidationError, match="span text"):
        Block.model_validate(block_b135(spans=spans))


def test_text_is_not_normalized():
    text = "الأُخوة  والأَخوات‏"
    block = Block.model_validate(block_b135(text=text, refs=[], spans=[], block_hash=text_hash(text)))
    assert block.text == text


def test_pub_ref_must_match_pub_id_and_revision():
    with pytest.raises(ValidationError, match="does not match"):
        BookRef(pub_id="pub_X", revision=6, pub_ref="pub_X@r5", source_work_id=None, edition_id=None)


def test_blocks_key_must_match_block_id():
    data = book_data()
    data["blocks"]["b000135"] = block_b135(block_id="b000136")
    with pytest.raises(ValidationError, match="differs from block_id"):
        CanonicalBook.model_validate(data)


def test_block_order_must_be_contiguous():
    data = book_data()
    data["blocks"]["b000135"] = block_b135(order=5)
    with pytest.raises(ValidationError, match="0..N-1"):
        CanonicalBook.model_validate(data)


def test_page_cannot_list_unknown_blocks():
    data = book_data()
    data["pages"][0]["block_ids"].append("b999999")
    with pytest.raises(ValidationError, match="unknown blocks: b999999"):
        CanonicalBook.model_validate(data)


def test_duplicate_page_rejected():
    data = book_data()
    data["pages"].append(dict(data["pages"][0]))
    with pytest.raises(ValidationError, match="duplicate page 25"):
        CanonicalBook.model_validate(data)


def test_block_lookup(book):
    assert book.block("b000135").page == 25
    with pytest.raises(KeyError, match="b000999"):
        book.block("b000999")


def test_blocks_in_order(book):
    assert [block.block_id for block in book.blocks_in_order()] == ["b000134", "b000135", "b000139"]


def test_page_lookup(book):
    page = book.page(25)
    assert isinstance(page, Page) and page.source_key == "21"
    assert book.page(25) is book.page(25)
    with pytest.raises(KeyError, match="page 18"):
        book.page(18)


def test_page_lookup_survives_round_trip(book):
    assert CanonicalBook.model_validate_json(book.model_dump_json()).page(25).scan_page == 25


def test_defaults(book):
    assert book.canonical_schema_version == "1.0"
    assert book.source.source_declared_hash_verified is False
    footnote = book.block("b000139")
    assert footnote.continues is False and footnote.refs == [] and footnote.raw_extras == {}


def test_schema_version_fixed():
    with pytest.raises(ValidationError, match="canonical_schema_version"):
        CanonicalBook.model_validate(book_data(canonical_schema_version="2.0"))
