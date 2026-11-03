import json
from pathlib import Path

import pytest

from ilm_engine.adapters.shamela_v3 import ShamelaV3Adapter
from ilm_engine.storage.json_store import ProtectedPathError
from ilm_engine.storage.sqlite_store import SqliteStore
from ilm_engine.validation.evidence import locate

ROOT = Path(__file__).resolve().parents[1]
PROV = {"method": "rule", "step": "units", "step_version": "1.0.0"}


@pytest.fixture(scope="module")
def book():
    return ShamelaV3Adapter().to_canonical(
        json.loads((ROOT / "data" / "demo_book_daraqutni.json").read_text())
    )


def anchor(book, quote, block_id):
    block = book.block(block_id)
    return locate(quote, block, pub_ref=book.book.pub_ref, scan_page=block.page).anchor.model_dump()


@pytest.fixture
def enrichment(book):
    pub_ref = book.book.pub_ref
    return {
        "pub_ref": pub_ref,
        "source": {"adapter": "shamela_v3@1.0.0"},
        "structure": {
            "root_section_id": "sec_root00000000",
            "sections": [
                {
                    "section_id": "sec_000000000001",
                    "title": "أولاد رسول الله",
                    "level": 1,
                    "heading_block_id": "b000104",
                    "toc_index": 7,
                    "toc_source_page_key": "17",
                    "start_block_id": "b000104",
                    "end_block_id": "b000133",
                    "start_page": 21,
                    "end_page": 24,
                    "parent_id": "sec_root00000000",
                    "children": [],
                    "origin": "author_text",
                    "provenance": PROV,
                }
            ],
        },
        "annotations": [
            {
                "annotation_id": "ann_000000000001",
                "type": "footnote",
                "source_block_id": "b000135",
                "marker_anchor": anchor(book, "(١)", "b000135"),
                "target_block_ids": ["b000140"],
                "marker_text": "١",
                "link_method": "source_ref",
                "is_entry_note": False,
                "status": "verified",
                "origin": "editor_footnote",
                "provenance": PROV,
            }
        ],
        "internal_refs": [
            {
                "internal_ref_id": "ann_000000000002",
                "kind": "entry_number",
                "anchor": anchor(book, "ترجمة رقم (٣٣)", "b000063"),
                "target_unit_id": "ku_000000000033",
                "target_entry_no": 33,
                "status": "resolved",
                "provenance": PROV,
            }
        ],
        "knowledge_units": [
            {
                "unit_id": "ku_000000000008",
                "genre": "biography",
                "sub_type": "ansab",
                "unit_type": "biographical_entry",
                "entry_no": 8,
                "section_id": "sec_000000000001",
                "anchors": [anchor(book, book.block("b000135").text, "b000135")],
                "note_annotation_ids": [],
                "subject_entity_id": "ent_000000000008",
                "payload": {"gender": "f"},
                "facts": [
                    {
                        "fact_id": "ku_000000000008#f1",
                        "predicate": "converted_to_islam",
                        "object": True,
                        "evidence": [anchor(book, "أسلمت", "b000135")],
                        "origin": "author_text",
                        "assertion": "stated",
                        "confidence": 0.95,
                        "sensitive": [],
                        "review_status": "auto_approved",
                        "provenance": PROV,
                    }
                ],
                "origin": "author_text",
                "confidence": 0.95,
                "review_status": "auto_approved",
                "issues": [],
                "provenance": PROV,
            }
        ],
        "entities": [
            {
                "entity_id": "ent_000000000008",
                "entity_type": "person",
                "canonical_name": "هند بنت عتيق",
                "canonical_name_normalized": "هند بنت عتيق",
                "name": None,
                "gender": "f",
                "mentions": [anchor(book, "هند بنت عتيق", "b000135")],
                "disambiguation": "unique",
                "confidence": 0.95,
                "review_status": "auto_approved",
                "provenance": PROV,
            }
        ],
        "relationships": [],
        "issues": [
            {
                "issue_id": "iss_000000000001",
                "code": "entry_without_footnote",
                "severity": "info",
                "target_kind": "unit",
                "target_id": "ku_000000000032",
                "message": "Entry 32 has no note.",
                "provenance": PROV,
            }
        ],
        "validation": [
            {
                "target_kind": "fact",
                "target_id": "ku_000000000008#f1",
                "confidence": 0.95,
                "decision": "auto_approved",
            }
        ],
    }


def test_blocks_store_hashes_not_text(tmp_path, book):
    store = SqliteStore(tmp_path / "enrichment.db")
    counts = store.load({"pub_ref": book.book.pub_ref}, book=book, origins={"b000135": "author_text"})
    assert counts["block"] == 594 and counts["book"] == 1
    columns = [row[1] for row in store.query("PRAGMA table_info(block)")]
    assert "text" not in columns
    assert store.query("SELECT origin, page, scan_page, block_hash FROM block WHERE block_id='b000135'") == [
        ("author_text", 25, 25, book.block("b000135").block_hash)
    ]
    assert store.query("SELECT adapter, source_declared_hash_verified FROM book") == [("shamela_v3@1.0.0", 0)]


def test_load_records_and_anchors(tmp_path, book, enrichment):
    counts = SqliteStore(tmp_path / "enrichment.db").load(enrichment, book=book)
    assert counts["knowledge_unit"] == 1 and counts["fact"] == 1 and counts["entity"] == 1
    assert counts["annotation"] == 2  # footnote + internal reference
    assert counts["section"] == 1 and counts["issue"] == 1 and counts["validation"] == 1
    assert counts["anchor"] == 5  # marker, internal ref, unit span, fact evidence, entity mention


def test_loading_twice_does_not_duplicate(tmp_path, book, enrichment):
    store = SqliteStore(tmp_path / "enrichment.db")
    first = store.load(enrichment, book=book)
    second = store.load(enrichment, book=book)
    assert first == second


def test_reload_replaces_changed_record(tmp_path, book, enrichment):
    store = SqliteStore(tmp_path / "enrichment.db")
    store.load(enrichment, book=book)
    enrichment["knowledge_units"][0]["facts"] = []
    store.load(enrichment, book=book)
    assert store.query("SELECT COUNT(*) FROM fact") == [(0,)]


def test_record_json_round_trip(tmp_path, book, enrichment):
    store = SqliteStore(tmp_path / "enrichment.db")
    store.load(enrichment, book=book)
    [(payload,)] = store.query("SELECT payload FROM knowledge_unit")
    assert json.loads(payload) == {"gender": "f"}
    [(quote,)] = store.query("SELECT quote FROM anchor WHERE owner_kind='fact'")
    assert quote == "أسلمت"


def test_manifest_and_review_items(tmp_path, book):
    store = SqliteStore(tmp_path / "enrichment.db")
    review = {
        "review_id": "rev_000000000001",
        "target_kind": "unit",
        "target_id": "ku_1",
        "priority": 0,
        "required_role": "scholar_reviewer",
        "status": "pending_review",
    }
    counts = store.load(
        {"pub_ref": book.book.pub_ref, "review_items": [review]},
        manifest={"run_id": "run_000000000001", "pub_ref": book.book.pub_ref},
    )
    assert counts["run"] == 1 and counts["review_item"] == 1


def test_refuses_protected_location():
    with pytest.raises(ProtectedPathError):
        SqliteStore(ROOT / "data" / "enrichment.db")
