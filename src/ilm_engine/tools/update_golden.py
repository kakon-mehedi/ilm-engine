"""Regenerate the adapter golden files (developer tool; run only on explicit request).

    uv run ilm-engine dev regen-goldens --yes
    uv run python -m ilm_engine.tools.update_golden

The golden input is an excerpt of the sample book (printed pages 21 and 25 with all metadata), so
the files are derived from the confidential sample and are git-ignored like `data/`. The golden test
compares the adapter's canonical JSON with `expected_canonical.json` byte for byte.
"""

from __future__ import annotations

import copy
import difflib
import json
import sys
from pathlib import Path
from typing import Any

from ilm_engine.adapters.shamela_v3 import ShamelaV3Adapter
from ilm_engine.storage.json_store import dumps

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE = REPO_ROOT / "data" / "demo_book_daraqutni.json"
GOLDEN_DIR = REPO_ROOT / "tests" / "golden" / "shamela_v3"
EXCERPT_PAGES = (21, 25)  # b000104–b000112 and b000134–b000146


def excerpt(raw: dict[str, Any], pages: tuple[int, ...] = EXCERPT_PAGES) -> dict[str, Any]:
    """The source document reduced to `pages` (all other sections kept)."""
    reduced = copy.deepcopy(raw)
    reduced["content"]["pages"] = [page for page in reduced["content"]["pages"] if page["n"] in pages]
    return reduced


def canonical_bytes(raw: dict[str, Any]) -> bytes:
    return dumps(ShamelaV3Adapter().to_canonical(raw))


def readable_diff(expected: bytes, actual: bytes, limit: int = 60) -> str:
    lines = list(
        difflib.unified_diff(
            expected.decode("utf-8").splitlines(),
            actual.decode("utf-8").splitlines(),
            "expected_canonical.json",
            "adapter output",
            lineterm="",
        )
    )
    more = f"\n... {len(lines) - limit} more diff lines" if len(lines) > limit else ""
    return "\n".join(lines[:limit]) + more


def regenerate(sample: Path = SAMPLE, golden_dir: Path = GOLDEN_DIR) -> list[Path]:
    raw = excerpt(json.loads(sample.read_text(encoding="utf-8")))
    golden_dir.mkdir(parents=True, exist_ok=True)
    input_path, expected_path = golden_dir / "input_excerpt.json", golden_dir / "expected_canonical.json"
    input_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    expected_path.write_bytes(canonical_bytes(raw))
    return [input_path, expected_path]


def main() -> int:
    for path in regenerate():
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
