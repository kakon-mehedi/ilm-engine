import hashlib
import json
from pathlib import Path

import pytest

from ilm_engine.canonical.models import Block
from ilm_engine.validation.evidence import anchor_status, locate

DATA = Path(__file__).resolve().parents[1] / "data" / "demo_book_daraqutni.json"
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"


def make_block(block_id: str, text: str, page: int = 25) -> Block:
    digest = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
    return Block(block_id=block_id, order=0, page=page, volume=1, kind="text", text=text, block_hash=digest)


@pytest.fixture(scope="module")
def b135() -> Block:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    text = next(b["text"] for p in data["content"]["pages"] for b in p["blocks"] if b["b"] == "b000135")
    return make_block("b000135", text)


def find(quote, block, **kwargs):
    return locate(quote, block, pub_ref=PUB_REF, scan_page=block.page, **kwargs)


def test_exact_match(b135):
    found = find("أسلمت", b135)
    assert (found.anchor.start, found.anchor.end) == (60, 65)
    assert found.factor == 1.0 and found.match == "exact" and found.occurrences == 1
    anchor = found.anchor
    assert anchor.quote == "أسلمت" and anchor.block_id == "b000135" and anchor.page == anchor.scan_page == 25
    assert anchor.block_hash == "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989"


def test_normalized_match_maps_to_original(b135):
    found = find("اسلمت", b135)
    assert (found.anchor.start, found.anchor.end) == (60, 65)
    assert found.factor == 0.9 and found.match == "normalized"
    assert found.anchor.quote == "أسلمت"


def test_normalized_match_without_diacritics(b135):
    found = find("ولم يرو عنها شيء", b135)
    assert (found.anchor.start, found.anchor.end) == (78, 97)
    assert found.anchor.quote == "ولم يُروَ عنها شيءٌ" and found.factor == 0.9


def test_quote_not_in_block(b135):
    assert find("ولد في مكة", b135) is None


def test_empty_quote(b135):
    assert find("", b135) is None and find("  ", b135) is None


def test_quote_from_another_block_not_accepted(b135):
    assert find("تزوجها عليّ في السَّنة الثانية من الهجرة", b135) is None


def test_multiple_occurrences_nearest_hint():
    block = make_block("b1", "هند بنت عتيق، وهند بن أبي هالة، وهند بن زرارة")
    near_second = find("هند", block, hint_start=16)
    assert near_second.anchor.start == 15 and near_second.occurrences == 3
    assert near_second.ambiguity_penalty == 1.0


def test_multiple_occurrences_without_hint_first_and_penalized():
    block = make_block("b1", "هند بنت عتيق، وهند بن أبي هالة")
    found = find("هند", block)
    assert found.anchor.start == 0 and found.ambiguity_penalty == 0.9


def test_anchor_quote_is_always_original_text(b135):
    for quote in ["اسلمت", "وتزوجت", "عبد الله بن عمر"]:
        found = find(quote, b135)
        assert b135.text[found.anchor.start : found.anchor.end] == found.anchor.quote


def test_honorific_variant_matches():
    block = make_block("b1", "فأردفه رسول الله -صلى الله عليه وسلم- على راحلته")
    found = find("رسول الله ﷺ على راحلته", block)
    assert found is not None and found.match == "normalized"
    assert block.text[found.anchor.start : found.anchor.end].startswith("رسول الله")


def test_anchor_status(b135):
    anchor = find("أسلمت", b135).anchor
    assert anchor_status(anchor, b135) == "valid"
    assert anchor_status(anchor, None) == "orphaned"
    changed = make_block("b000135", b135.text.replace("أسلمت", "اسلمت"))
    assert anchor_status(anchor, changed) == "stale"
