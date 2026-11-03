import json
from pathlib import Path

import pytest

from ilm_engine.adapters.shamela_v3 import ShamelaV3Adapter

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_JSON = ROOT / "data" / "demo_book_daraqutni.json"
SAMPLE_PDF = ROOT / "data" / "demo_book_daraqutni_v1.pdf"


@pytest.fixture(scope="session")
def sample_raw() -> dict:
    return json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sample_book(sample_raw):
    """The sample book as the adapter produces it (with the PDF reference)."""
    return ShamelaV3Adapter().to_canonical(sample_raw, SAMPLE_PDF)
