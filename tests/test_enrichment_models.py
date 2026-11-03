"""The real examples from 03-data-contracts.md must validate against the enrichment models."""

import pytest
from pydantic import ValidationError

from ilm_engine.enrichment.models import (
    Anchor,
    Annotation,
    Citation,
    ConfidenceFactors,
    Fact,
    InternalRef,
    Issue,
    KnowledgeUnit,
    MetadataField,
    Relationship,
    RelationshipAttrs,
    ReviewItem,
    ValidationResult,
    Work,
)

PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
B135_TEXT = (
    "٨ - هند بنت عتيق بن عابد (١) بن عبد اللَّه بن عمر بن مخزوم؛ أسلمت (٢) وتزوجت، ولم يُروَ عنها شيءٌ (٣)."
)
B135_HASH = "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989"
UNITS_LLM = {
    "method": "llm_consensus",
    "step": "units",
    "step_version": "1.0.0",
    "model_id": "claude-sonnet-5-5",
    "prompt_id": "extract_biography",
    "prompt_version": "v1",
}


def anchor(start: int, end: int, quote: str, block_id: str = "b000135", page: int = 25, **extra) -> dict:
    block_hash = extra.pop("block_hash", B135_HASH)
    return {
        "pub_ref": PUB_REF,
        "page": page,
        "scan_page": page,
        "block_id": block_id,
        "start": start,
        "end": end,
        "quote": quote,
        "block_hash": block_hash,
        **extra,
    }


def fact(**overrides) -> dict:
    data = {
        "fact_id": "ku_0123456789ab#f1",
        "predicate": "converted_to_islam",
        "object": True,
        "evidence": [anchor(60, 65, "أسلمت")],
        "origin": "author_text",
        "assertion": "stated",
        "confidence": 0.9,
        "sensitive": [],
        "review_status": "auto_approved",
        "provenance": UNITS_LLM,
    }
    return {**data, **overrides}


def test_anchor_example():
    item = Anchor.model_validate(anchor(78, 97, "ولم يُروَ عنها شيءٌ", status="valid"))
    assert item.status == "valid" and item.quote_truncated is False and item.bbox is None


def test_anchor_offsets_ordered():
    with pytest.raises(ValidationError, match="start 97 > end 78"):
        Anchor.model_validate(anchor(97, 78, ""))


def test_anchor_hash_format():
    with pytest.raises(ValidationError, match="block_hash"):
        Anchor.model_validate(anchor(0, 1, "٨", block_hash="abc"))


def test_issue_examples():
    Issue.model_validate(
        {
            "issue_id": "iss_3f1c00000000",
            "code": "page_count_mismatch",
            "severity": "info",
            "target_kind": "book",
            "target_id": PUB_REF,
            "message": "Source claims 72 pages, 68 held.",
            "details": {"claimed": 72, "held": 68, "missing_pages": [1, 2, 4, 18]},
            "provenance": {"method": "rule", "step": "document_analysis", "step_version": "1.0.0"},
        }
    )
    with pytest.raises(ValidationError, match="code"):
        Issue.model_validate(
            {
                "issue_id": "iss_x",
                "code": "not_a_code",
                "severity": "info",
                "target_kind": "book",
                "target_id": PUB_REF,
                "message": "",
                "provenance": {"method": "rule", "step": "x", "step_version": "1"},
            }
        )


def test_metadata_field_example():
    field = MetadataField.model_validate(
        {
            "value": {"name": "أبو الحسن علي بن عمر بن أحمد الدارقطني", "death_hijri": 385},
            "sources": [
                {"kind": "existing_metadata", "path": "metadata.source_attributes.author.death.hijri"},
                {
                    "kind": "book_content",
                    "anchors": [
                        anchor(
                            24,
                            51,
                            "سنةٍ خمسٍ وثمانين وثلاث مئة",
                            block_id="b000049",
                            page=9,
                            block_hash="sha256:b4f1f176241242ffbd6fa49106557dc458dd6be7240bbbf54855ba3c6edd9292",
                        )
                    ],
                },
            ],
            "assertion": "stated",
            "origin": "editor_text",
            "confidence": 0.95,
            "conflicts": [],
            "review_status": "auto_approved",
        }
    )
    assert field.sources[1].anchors[0].block_id == "b000049"


def test_annotation_example():
    item = Annotation.model_validate(
        {
            "annotation_id": "ann_000000000001",
            "type": "footnote",
            "source_block_id": "b000105",
            "marker_anchor": anchor(0, 3, "١ -", block_id="b000105", page=21),
            "target_block_ids": ["b000109"],
            "marker_text": "١ -",
            "link_method": "source_ref",
            "is_entry_note": True,
            "status": "verified",
            "provenance": {"method": "structural", "step": "annotations", "step_version": "1.0.0"},
        }
    )
    assert item.origin == "editor_footnote"


def test_citation_and_internal_ref_examples():
    Citation.model_validate(
        {
            "citation_id": "cit_000000000001",
            "title_raw": "الإصابة",
            "title_normalized": "الاصابه",
            "work_id": "wrk_000000000001",
            "author_hint": None,
            "locators": [{"raw": "(٨/ ١٥٧)", "volume": 8, "page": 157}],
            "anchor": anchor(15, 22, "الإصابة", block_id="b000139"),
            "context": "footnote",
            "origin": "editor_footnote",
            "resolution": "alias_table",
            "confidence": 0.95,
            "provenance": {"method": "rule", "step": "citations", "step_version": "1.0.0"},
        }
    )
    InternalRef.model_validate(
        {
            "internal_ref_id": "ann_000000000002",
            "kind": "entry_number",
            "anchor": anchor(60, 74, "ترجمة رقم (٣٣)", block_id="b000063", page=11),
            "target_unit_id": "ku_000000000033",
            "target_entry_no": 33,
            "status": "resolved",
            "provenance": {"method": "rule", "step": "citations", "step_version": "1.0.0"},
        }
    )


def test_work_id_must_be_ours():
    data = {
        "source_work_id": None,
        "title": "الإصابة في تمييز الصحابة",
        "title_normalized": "الاصابه في تمييز الصحابه",
        "aliases": ["الإصابة"],
        "author_name": "ابن حجر",
        "author_entity_id": None,
        "status": "catalog",
    }
    Work.model_validate({**data, "work_id": "wrk_0123456789ab"})
    with pytest.raises(ValidationError, match="work_id"):
        Work.model_validate({**data, "work_id": "wrk_01M0CJEXJ1ZJM9AEM1GYTHTYZE"})


def test_knowledge_unit_entry_8_example():
    unit = KnowledgeUnit.model_validate(
        {
            "unit_id": "ku_0123456789ab",
            "genre": "biography",
            "sub_type": "ansab",
            "unit_type": "biographical_entry",
            "entry_no": 8,
            "section_id": "sec_0123456789ab",
            "anchors": [
                anchor(
                    0,
                    102,
                    B135_TEXT,
                )
            ],
            "note_annotation_ids": ["ann_0123456789ab"],
            "subject_entity_id": "ent_0123456789ab",
            "payload": {"person_surface": "هند بنت عتيق بن عابد", "person_span": [4, 24], "gender": "f"},
            "facts": [
                fact(),
                fact(fact_id="ku_0123456789ab#f2", predicate="married", evidence=[anchor(70, 76, "وتزوجت")]),
                fact(
                    fact_id="ku_0123456789ab#f3",
                    predicate="has_narration",
                    object=False,
                    evidence=[anchor(78, 97, "ولم يُروَ عنها شيءٌ")],
                ),
            ],
            "origin": "author_text",
            "confidence": 0.9,
            "review_status": "auto_approved",
            "issues": [],
            "provenance": {"method": "rule", "step": "units", "step_version": "1.0.0"},
        }
    )
    assert [item.predicate for item in unit.facts] == ["converted_to_islam", "married", "has_narration"]
    assert KnowledgeUnit.model_validate_json(unit.model_dump_json()) == unit


def test_fact_needs_evidence():
    with pytest.raises(ValidationError, match="evidence"):
        Fact.model_validate(fact(evidence=[]))


def test_inferred_fact_must_be_ai_generated():
    inferred = {"assertion": "inferred", "predicate": "child_of"}
    Fact.model_validate(fact(origin="ai_generated", **inferred))
    with pytest.raises(ValidationError, match="ai_generated"):
        Fact.model_validate(fact(origin="author_text", **inferred))


def test_confidence_bounded():
    with pytest.raises(ValidationError, match="confidence"):
        Fact.model_validate(fact(confidence=1.2))


def relationship(**overrides) -> dict:
    data = {
        "relation_id": "rel_0123456789ab",
        "type": "sibling_of",
        "subject_entity_id": "ent_000000000009",
        "object_entity_id": "ent_000000000010",
        "attrs": {"kind": "full", "via_parent_entity_id": "ent_00000000000a", "group_id": "grp_0123456789ab"},
        "evidence": [anchor(12, 25, "ابنا أبي هالة", block_id="b000137")],
        "origin": "author_text",
        "assertion": "stated",
        "confidence": 0.9,
        "review_status": "auto_approved",
        "provenance": UNITS_LLM,
    }
    return {**data, **overrides}


def test_relationship_examples():
    assert Relationship.model_validate(relationship()).attrs.kind == "full"
    inferred = Relationship.model_validate(
        relationship(
            attrs={"kind": "maternal"},
            origin="ai_generated",
            assertion="inferred",
            confidence=0.75,
            review_status="pending_review",
        )
    )
    assert inferred.attrs.group_id is None
    assert Relationship.model_validate(relationship(attrs={})).attrs == RelationshipAttrs()


def test_inferred_relationship_must_be_ai_generated():
    with pytest.raises(ValidationError, match="ai_generated"):
        Relationship.model_validate(relationship(assertion="inferred"))


def test_umm_walad_is_a_mother_status_not_a_sibling_kind():
    assert RelationshipAttrs(mother_status="umm_walad").kind is None
    with pytest.raises(ValidationError):
        RelationshipAttrs(kind="umm_walad")


def test_validation_result_example_and_schema_alias():
    result = ValidationResult.model_validate(
        {
            "target_kind": "fact",
            "target_id": "ku_0123456789ab#f1",
            "schema_valid": True,
            "evidence_found": True,
            "evidence_match": "exact",
            "model_outputs": [{"model_id": "claude-sonnet-5-5", "value": True}],
            "agreement": "agree",
            "factors": {"base": 0.75, "evidence": 1.0, "schema": 1.0, "agreement": 1.2, "penalties": {}},
            "confidence": 0.9,
            "threshold": 0.8,
            "decision": "auto_approved",
        }
    )
    assert result.factors.schema_ == 1.0
    assert result.model_dump()["factors"]["schema"] == 1.0
    assert ConfidenceFactors(base=0.95, evidence=1, schema_=1, agreement=1).model_dump()["schema"] == 1


def review_item(**overrides) -> dict:
    data = {
        "review_id": "rev_0123456789ab",
        "target_kind": "unit",
        "target_id": "ku_0123456789ab",
        "reason": ["sensitive"],
        "sensitive": ["hadith_grading"],
        "required_role": "scholar_reviewer",
        "priority": 0,
        "confidence": 0.9,
        "proposed_value": {"grading": {"term": "daif", "reason": "لكثرة المجاهيل"}},
        "anchors": [
            anchor(
                115,
                142,
                "وإسناده ضعيف لكثرة المجاهيل",
                block_id="b000228",
                page=35,
                block_hash="sha256:13fb65ec7c5a52241bae650ed6dffd510c5ad6d6409f49f156bc78588325a0ce",
            )
        ],
        "context_block_ids": ["b000228"],
        "pdf": {"file": "demo_book_daraqutni_v1.pdf", "page": 35},
        "issues": ["iss_0123456789ab"],
    }
    return {**data, **overrides}


def test_review_item_example():
    assert ReviewItem.model_validate(review_item()).status == "pending_review"


def test_sensitive_review_requires_scholar():
    with pytest.raises(ValidationError, match="scholar_reviewer"):
        ReviewItem.model_validate(review_item(required_role="editor_reviewer"))
