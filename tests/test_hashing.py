import hashlib
import json
from pathlib import Path

import pytest

from ilm_engine.canonical.models import Block
from ilm_engine.integrity.hashing import block_hash, canonical_json, content_hash, file_sha256

DATA = Path(__file__).resolve().parents[1] / "data" / "demo_book_daraqutni.json"


def make_block(block_id: str, order: int, text: str, **extra) -> Block:
    return Block(
        block_id=block_id,
        order=order,
        page=25,
        volume=1,
        kind="text",
        text=text,
        block_hash=block_hash(text),
        **extra,
    )


def sample_blocks() -> list[Block]:
    """Every block of the sample book, built the way an adapter would."""
    data = json.loads(DATA.read_text(encoding="utf-8"))
    blocks = []
    for page in data["content"]["pages"]:
        for raw in page["blocks"]:
            blocks.append(
                Block(
                    block_id=raw["b"],
                    order=len(blocks),
                    page=page["n"],
                    volume=page["volume"],
                    kind=raw["kind"],
                    text=raw["text"],
                    marker=raw.get("marker"),
                    continues=bool(raw.get("continues")),
                    refs=raw.get("refs") or [],
                    spans=raw.get("spans") or [],
                    block_hash=block_hash(raw["text"]),
                )
            )
    return blocks


def test_block_hash_is_stable_and_not_normalized():
    assert block_hash("أسلمت") == block_hash("أسلمت")
    assert block_hash("أسلمت") != block_hash("اسلمت")
    assert block_hash("أسلمت") == "sha256:" + hashlib.sha256("أسلمت".encode()).hexdigest()


def test_block_hash_sees_diacritic_order():
    # Same visible text, different code-point order (shadda/fatha), as found in the sample.
    shadda_fatha = "اللَّه"
    fatha_shadda = "اللَّه"
    assert block_hash(shadda_fatha) != block_hash(fatha_shadda)


def test_block_hash_of_sample_block_b000135():
    text = next(block.text for block in sample_blocks() if block.block_id == "b000135")
    assert block_hash(text) == "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989"


def test_canonical_json_is_deterministic_and_utf8():
    assert canonical_json({"b": 1, "a": "هند"}) == canonical_json({"a": "هند", "b": 1})
    assert canonical_json({"b": 1, "a": "هند"}) == '{"a":"هند","b":1}'.encode()


def test_content_hash_identical_across_two_builds():
    first = sample_blocks()
    second = sample_blocks()
    assert first is not second
    assert content_hash(first) == content_hash(second)
    assert content_hash(first).startswith("sha256:") and len(content_hash(first)) == 71


def test_content_hash_follows_reading_order_not_input_order():
    blocks = [make_block("b1", 0, "أ"), make_block("b2", 1, "ب")]
    assert content_hash(blocks) == content_hash(list(reversed(blocks)))


@pytest.mark.parametrize(
    "changed",
    [
        make_block("b2", 1, "ج"),
        make_block("b9", 1, "ب"),
        make_block("b2", 1, "ب", marker="١"),
        make_block("b2", 1, "ب", refs=[{"start": 0, "end": 1, "to": "b3"}]),
    ],
)
def test_content_hash_changes_with_any_hashed_field(changed):
    base = [make_block("b1", 0, "أ"), make_block("b2", 1, "ب")]
    assert content_hash(base) != content_hash([base[0], changed])


def test_content_hash_ignores_spans_and_continues():
    base = [make_block("b1", 0, "أب")]
    styled = [
        make_block("b1", 0, "أب", spans=[{"class": "c5", "start": 0, "end": 1, "text": "أ"}], continues=True)
    ]
    assert content_hash(base) == content_hash(styled)


def test_content_hash_does_not_reproduce_declared_source_hash():
    declared = json.loads(DATA.read_text(encoding="utf-8"))["content"]["content_sha256"]
    assert content_hash(sample_blocks()) != f"sha256:{declared}"


def test_file_sha256(tmp_path):
    path = tmp_path / "x.bin"
    payload = b"\x00" * (3 << 20) + "هند".encode()
    path.write_bytes(payload)
    assert file_sha256(path) == "sha256:" + hashlib.sha256(payload).hexdigest()
    assert file_sha256(str(path)) == file_sha256(path)


def test_file_sha256_of_sample_is_stable():
    assert file_sha256(DATA) == file_sha256(DATA)
