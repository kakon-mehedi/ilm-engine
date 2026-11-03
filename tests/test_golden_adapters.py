"""Adapter contract test: the canonical JSON of the golden excerpt must not change silently.

The golden files are derived from the confidential sample and are git-ignored; create them with
`uv run ilm-engine dev regen-goldens --yes`. Normal test runs never rewrite them.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.adapters.shamela_v3 import ShamelaV3Adapter
from ilm_engine.cli import app
from ilm_engine.storage.json_store import dumps
from ilm_engine.tools.update_golden import GOLDEN_DIR, canonical_bytes, excerpt, readable_diff

INPUT, EXPECTED = GOLDEN_DIR / "input_excerpt.json", GOLDEN_DIR / "expected_canonical.json"
pytestmark = pytest.mark.skipif(
    not EXPECTED.is_file(), reason="golden files absent: ilm-engine dev regen-goldens --yes"
)


@pytest.fixture(scope="module")
def golden_input():
    return json.loads(INPUT.read_text(encoding="utf-8"))


def test_adapter_output_matches_golden(golden_input):
    expected, actual = EXPECTED.read_bytes(), canonical_bytes(golden_input)
    assert actual == expected, "adapter output changed:\n" + readable_diff(expected, actual)


def test_excerpt_holds_required_blocks(golden_input):
    ids = {block["b"] for page in golden_input["content"]["pages"] for block in page["blocks"]}
    assert {f"b{n:06d}" for n in [*range(104, 113), *range(134, 147)]} <= ids
    assert [page["n"] for page in golden_input["content"]["pages"]] == [21, 25]


def test_changed_mapping_fails_with_readable_diff(golden_input):
    book = ShamelaV3Adapter().to_canonical(golden_input)
    changed = book.model_copy(update={"source": book.source.model_copy(update={"adapter_version": "9.9.9"})})
    diff = readable_diff(EXPECTED.read_bytes(), dumps(changed))
    assert '-    "adapter_version": "1.0.0",' in diff and '+    "adapter_version": "9.9.9",' in diff


def test_excerpt_function_keeps_other_sections(golden_input):
    reduced = excerpt(golden_input, pages=(21,))
    assert [page["n"] for page in reduced["content"]["pages"]] == [21] and reduced[
        "metadata"
    ] == golden_input["metadata"]


def test_regen_requires_explicit_confirmation():
    before = EXPECTED.read_bytes()
    result = CliRunner().invoke(app, ["dev", "regen-goldens"])
    assert result.exit_code == 1 and "--yes" in result.output
    assert EXPECTED.read_bytes() == before


def test_golden_files_are_not_tracked():
    gitignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "tests/golden/shamela_v3/" in gitignore
