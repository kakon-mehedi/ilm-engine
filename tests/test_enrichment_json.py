import json
import os
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app
from ilm_engine.enrichment.models import Enrichment

ROOT = Path(__file__).resolve().parents[1]
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    base = tmp_path_factory.mktemp("enrichment")
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--input",
            str(ROOT / "data"),
            "--out",
            str(base / "out"),
            "--store",
            str(base / "store"),
            "--cache-dir",
            str(base / "cache"),
        ],
    )
    assert result.exit_code == 0, result.output
    yield base / "out" / PUB_REF
    for path in (base / "store").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


@pytest.fixture(scope="module")
def enrichment(out):
    return Enrichment.model_validate_json((out / "enrichment.json").read_text(encoding="utf-8"))


def test_validates_against_schema(enrichment):
    committed = json.loads((ROOT / "docs" / "enrichment.schema.json").read_text(encoding="utf-8"))
    assert committed == Enrichment.model_json_schema(by_alias=True, mode="serialization")
    assert enrichment.enrichment_schema_version == "1.0" and enrichment.pub_ref == PUB_REF


def test_every_unit_and_fact_has_anchor_and_origin(enrichment):
    assert len(enrichment.knowledge_units) == 75
    for unit in enrichment.knowledge_units:
        assert unit.anchors and unit.origin
        for fact in unit.facts:
            assert fact.evidence and fact.origin


def test_contents_and_stats(enrichment):
    stats = enrichment.stats
    assert (stats["blocks"], stats["pages"], stats["units"], stats["annotations"]) == (594, 68, 75, 301)
    assert stats["sections"] == 18 and stats["entities"] >= 75 and stats["relationships"] > 0
    assert enrichment.metadata.genre_primary.value == {"genre": "biography", "sub_type": "ansab"}
    assert (
        enrichment.source.adapter == "shamela_v3@1.0.0"
        and enrichment.source.source_declared_hash_verified is False
    )
    assert len(enrichment.review_queue_ids) == stats["review_items"]


def test_lists_sorted_by_id(enrichment):
    for name, key in [
        ("knowledge_units", "unit_id"),
        ("entities", "entity_id"),
        ("annotations", "annotation_id"),
        ("issues", "issue_id"),
    ]:
        ids = [getattr(item, key) for item in getattr(enrichment, name)]
        assert ids == sorted(ids), name


def test_run_id_matches_manifest(out, enrichment):
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == enrichment.run_id


def test_sqlite_counts(out):
    db = sqlite3.connect(out / "enrichment.db")
    counts = {
        t: db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        for t in ("block", "knowledge_unit", "annotation")
    }
    assert counts["block"] == 594 and counts["knowledge_unit"] == 75 and counts["annotation"] >= 301
