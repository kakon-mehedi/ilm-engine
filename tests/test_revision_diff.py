import copy
import json
from pathlib import Path

import pytest

from ilm_engine.adapters.shamela_v3 import ShamelaV3Adapter
from ilm_engine.enrichment.models import Anchor, Fact, Provenance
from ilm_engine.integrity.revision_diff import anchors_in, diff, restatus_anchors, stale_anchor_issues
from ilm_engine.validation.evidence import locate

DATA = Path(__file__).resolve().parents[1] / "data" / "demo_book_daraqutni.json"


@pytest.fixture(scope="module")
def raw():
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def r6(raw):
    return ShamelaV3Adapter().to_canonical(raw)


def revision(raw, edit=None, drop=None, add=None):
    """A simulated r7 of the sample with one block edited, dropped or added."""
    copy_ = copy.deepcopy(raw)
    copy_["revision"]["r"] = 7
    for page in copy_["content"]["pages"]:
        for block in list(page["blocks"]):
            if block["b"] == edit:
                block["text"] = block["text"].replace("أسلمت", "اسلمت")
            if block["b"] == drop:
                page["blocks"].remove(block)
                for other in page["blocks"]:
                    other["refs"] = [ref for ref in other.get("refs") or [] if ref["to"] != drop]
        if add and page["n"] == 72:
            page["blocks"].append({"b": add, "kind": "text", "text": "نص جديد"})
    return ShamelaV3Adapter().to_canonical(copy_)


def anchor(book, quote, block_id):
    block = book.block(block_id)
    return locate(quote, block, pub_ref=book.book.pub_ref, scan_page=block.page).anchor


def fact(evidence):
    return Fact(
        fact_id="ku_0123456789ab#f1",
        predicate="converted_to_islam",
        object=True,
        evidence=evidence,
        origin="author_text",
        assertion="stated",
        confidence=0.9,
        review_status="auto_approved",
        provenance=Provenance(method="rule", step="units", step_version="1.0.0"),
    )


def test_edit_of_one_block(raw, r6):
    r7 = revision(raw, edit="b000135")
    result = diff(r6, r7)
    assert result.changed == ("b000135",)
    assert result.added == () and result.removed == ()
    assert len(result.unchanged) == 593
    assert result.to_reprocess == {"b000135"}
    assert (result.old_pub_ref, result.new_pub_ref) == (r6.book.pub_ref, "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r7")


def test_anchors_on_changed_block_become_stale_others_untouched(raw, r6):
    result = diff(r6, revision(raw, edit="b000135"))
    on_135 = [anchor(r6, "أسلمت", "b000135"), anchor(r6, "ولم يُروَ عنها شيءٌ", "b000135")]
    elsewhere = anchor(r6, "فاطمة", "b000105")
    records = [fact(on_135), fact([elsewhere])]
    updated = restatus_anchors(records, result)
    assert [a.status for a in anchors_in(updated[0])] == ["stale", "stale"]
    assert updated[1] is records[1] and elsewhere.status == "valid"
    assert [a.status for a in on_135] == ["valid", "valid"]  # originals are not mutated


def test_stale_issue_per_block(raw, r6):
    result = diff(r6, revision(raw, edit="b000135"))
    records = [fact([anchor(r6, "أسلمت", "b000135"), anchor(r6, "وتزوجت", "b000135")])]
    [issue] = stale_anchor_issues(records, result)
    assert issue.code == "anchor_stale" and issue.target_id == "b000135"
    assert issue.details == {"status": "stale", "anchors": 2, "previous": r6.book.pub_ref}


def test_removed_block_orphans_its_anchors(raw, r6):
    result = diff(r6, revision(raw, drop="b000136"))
    assert result.removed == ("b000136",) and result.changed == ()
    updated = restatus_anchors({"units": [anchor(r6, "وهند", "b000136")]}, result)
    assert updated["units"][0].status == "orphaned"
    assert stale_anchor_issues(updated, result)[0].details["status"] == "orphaned"


def test_added_block_is_reprocessed(raw, r6):
    result = diff(r6, revision(raw, add="b009999"))
    assert result.added == ("b009999",) and result.to_reprocess == {"b009999"}


def test_identical_revision_has_no_changes(raw, r6):
    result = diff(r6, ShamelaV3Adapter().to_canonical(raw))
    assert result.changed == result.added == result.removed == () and len(result.unchanged) == 594
    records = [fact([anchor(r6, "أسلمت", "b000135")])]
    assert restatus_anchors(records, result) is records
    assert stale_anchor_issues(records, result) == []


def test_restatus_handles_plain_anchor(raw, r6):
    result = diff(r6, revision(raw, edit="b000135"))
    assert isinstance(restatus_anchors(anchor(r6, "أسلمت", "b000135"), result), Anchor)
