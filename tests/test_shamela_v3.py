import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from ilm_engine.adapters.registry import resolve
from ilm_engine.adapters.shamela_v3 import ShamelaV3Adapter, SourceFormatError
from ilm_engine.integrity.hashing import content_hash

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "demo_book_daraqutni.json"
PDF = ROOT / "data" / "demo_book_daraqutni_v1.pdf"


@pytest.fixture(scope="module")
def raw():
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def book(raw):
    return ShamelaV3Adapter().to_canonical(raw, PDF)


def test_sample_resolves_to_shamela_v3(raw):
    assert isinstance(resolve(raw), ShamelaV3Adapter)


def test_pages(book):
    assert len(book.pages) == 68
    numbers = [page.n for page in book.pages]
    assert numbers[0] == 3 and numbers[-1] == 72
    assert sorted(set(range(1, 73)) - set(numbers)) == [1, 2, 4, 18]
    page = book.page(25)
    assert (
        page.scan_page == 25
        and page.source_key == "21"
        and page.source_url == "https://shamela.ws/book/26/21"
    )


def test_blocks(book):
    assert len(book.blocks) == 594
    assert Counter(block.kind for block in book.blocks.values()) == {
        "text": 260,
        "footnote": 317,
        "heading": 15,
        "toc_heading": 2,
    }
    assert [block.order for block in book.blocks_in_order()] == list(range(594))
    assert sum(len(page.block_ids) for page in book.pages) == 594


def test_refs_continues_toc(book):
    assert sum(len(block.refs) for block in book.blocks.values()) == 300
    assert sum(block.continues for block in book.blocks.values()) == 16
    assert len(book.metadata.toc) == 17
    entry = book.metadata.toc[8]
    assert entry.index == 8 and entry.source_page_key == "21" and entry.depth == 1


def test_book_ref_and_source(book):
    assert book.book.pub_ref == "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
    assert book.book.source_work_id == "wrk_01M0CJEXJ1ZJM9AEM1GYTHTYZE"
    assert book.book.edition_id == "edt_01M49AFMMYHV5DGF9B2CQQBVBB"
    source = book.source
    assert (source.source_code, source.schema_version, source.adapter_id, source.adapter_version) == (
        "src-shamela",
        "3.0",
        "shamela_v3",
        "1.0.0",
    )
    assert source.source_book_key == "26" and source.source_adapter_semver == "1.3.0"
    assert source.source_declared_hash == "1f974ece9429393b052de38052876b65ed195f83d3b6d55773691f2599f5c582"
    assert source.source_declared_hash_verified is False


def test_block_b000135(book):
    block = book.block("b000135")
    assert len(block.text) == 102 and block.text[60:65] == "أسلمت"
    assert block.page == 25 and block.order == 134 and block.kind == "text"
    assert block.block_hash == "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989"
    assert [(r.start, r.end, r.to) for r in block.refs][0] == (0, 3, "b000139")
    assert [(s.cls, s.start, s.end, s.text, s.meaning) for s in block.spans][0] == (
        "c2",
        25,
        28,
        "(١)",
        "unknown",
    )


def test_span_classes_verbatim(book):
    classes = Counter(span.cls for block in book.blocks.values() for span in block.spans)
    assert classes == {"c2": 230, "c5": 64, "c1": 8, "c4": 2}


def test_footnote_markers(book):
    assert book.block("b000139").marker == "٨ -"
    assert book.block("b000215").marker == "أ"


def test_metadata(book):
    meta = book.metadata
    assert meta.title_as_source == "الإخوة والأخوات"
    assert meta.author_name == "أبو الحسن علي بن عمر بن أحمد الدارقطني" and meta.author_death_hijri == 385
    assert meta.editor == "باسم فيصل أحمد الجوابرة"
    assert meta.publisher == "دار الراية للنشر والتوزيع، الرياض - السعودية"
    assert (meta.year_hijri, meta.year_gregorian) == (1413, 1993)
    assert (meta.category_id, meta.category_name) == ("27", "الأنساب")
    assert meta.claimed_page_count == 72 and meta.page_numbering == "matches_print"
    assert len(meta.card) == 7 and meta.card[0] == {
        "label": "الكتاب",
        "value": "الإخوة والأخوات",
        "group": "title",
    }


def test_quality_and_scan(book):
    quality = book.quality
    assert (quality.status, quality.passed, quality.claimed_pages, quality.held_pages) == (
        "imperfect",
        True,
        72,
        68,
    )
    assert quality.tolerance == "5%" and quality.archive_code == "E-VAL-SHORT"
    assert book.scan == {
        "available": True,
        "volumes": [1],
        "file": "demo_book_daraqutni_v1.pdf",
        "page_count": 80,
    }


def test_scan_without_pdf(raw):
    book = ShamelaV3Adapter().to_canonical(raw)
    assert book.scan["file"] == "demo_book_daraqutni_v1.pdf" and book.scan["page_count"] is None


def test_input_not_mutated(raw):
    before = copy.deepcopy(raw)
    ShamelaV3Adapter().to_canonical(raw, PDF)
    assert raw == before


def test_deterministic(raw, book):
    again = ShamelaV3Adapter().to_canonical(raw, PDF)
    assert again == book
    assert again.canonical_content_hash == book.canonical_content_hash == content_hash(book)


def test_missing_required_field(raw):
    broken = copy.deepcopy(raw)
    del broken["content"]["pages"][3]["blocks"][0]["text"]
    with pytest.raises(SourceFormatError, match=r"content.pages.3.blocks.0.text|'text'"):
        ShamelaV3Adapter().to_canonical(broken)
    broken = copy.deepcopy(raw)
    del broken["revision"]
    with pytest.raises(SourceFormatError, match="revision.r"):
        ShamelaV3Adapter().to_canonical(broken)


def test_detect(raw):
    adapter = ShamelaV3Adapter()
    assert adapter.detect(raw) is True
    assert adapter.detect({"pub": {"source_code": "src-ocr-team"}, "content": {"pages": []}}) is False
