import hashlib
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app
from ilm_engine.enrichment.models import Enrichment

ROOT = Path(__file__).resolve().parents[1]
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
runner = CliRunner()


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    base = tmp_path_factory.mktemp("graph")
    result = runner.invoke(
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
    yield base
    for path in (base / "store").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_graph_html_nodes(base):
    out = base / "out" / PUB_REF
    enrichment = Enrichment.model_validate_json((out / "enrichment.json").read_text(encoding="utf-8"))
    html = (out / "graph.html").read_text(encoding="utf-8")
    assert "cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/" in html
    assert f"{len(enrichment.entities) + len(enrichment.works)} nodes" in html
    assert "could not be loaded (offline)" in html  # degrades without the CDN


def test_cypher_merges_every_entity(base):
    out = base / "out" / PUB_REF
    enrichment = Enrichment.model_validate_json((out / "enrichment.json").read_text(encoding="utf-8"))
    cypher = (out / "graph.cypher").read_text(encoding="utf-8")
    for entity in enrichment.entities:
        assert f'MERGE (n:Person {{id: "{entity.entity_id}"}})' in cypher


def test_rebuild_derived_reproduces_identical_files(base):
    out = base / "out" / PUB_REF
    names = ["search_index.json", "graph.html", "graph.cypher"]
    before = {name: digest(out / name) for name in names}
    for name in names:
        (out / name).unlink()
    result = runner.invoke(app, ["rebuild-derived", str(out), "--store", str(base / "store")])
    assert result.exit_code == 0, result.output
    assert {name: digest(out / name) for name in names} == before
