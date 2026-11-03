import pytest

from ilm_engine.config import load_config
from ilm_engine.processors.metadata import card_metadata, content_metadata, metadata_conflicts
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def result(sample_book):
    config = load_config(PUB_ID)
    record, _ = card_metadata(sample_book, config)
    record, findings, _ = content_metadata(
        sample_book, record, assign(sample_book, config).blocks, build(sample_book), config
    )
    return metadata_conflicts(sample_book, record, findings)


def test_title_variant_with_both_forms_and_anchor(result):
    record, issues = result
    [issue] = [i for i in issues if i.code == "title_variant"]
    assert issue.details["variants"] == ["الإخوة والأخوات", "الأُخوة والأَخوات"]
    assert issue.details["equal_after_normalization"] is True and issue.severity == "info"
    assert [a.block_id for a in issue.anchors] == ["b000001"]
    assert record.title_variants == ["الإخوة والأخوات", "الأُخوة والأَخوات"]
    assert record.title.value == "الإخوة والأخوات"  # recorded, not resolved


def test_author_name_with_bin_mahdi_is_additive_conflict(result):
    record, issues = result
    conflicts = [i for i in issues if i.code == "metadata_conflict"]
    p17 = [i for i in conflicts if i.anchors[0].block_id == "b000083"]
    assert p17 and p17[0].severity == "info" and p17[0].details["additive"] is True
    assert p17[0].details["text_chain"][-1] == "مهدي"
    assert any(c["block_id"] == "b000083" for c in record.author.conflicts)


def test_missing_contains_isbn(result):
    assert "isbn" in result[0].missing_fields


def test_issue_ids_listed_on_record(result):
    record, issues = result
    assert {i.issue_id for i in issues} <= set(record.issues)
