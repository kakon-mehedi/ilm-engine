"""Integrity invariants on a real run (ADR-017)."""

import json
import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app
from ilm_engine.integrity.hashing import file_sha256
from ilm_engine.integrity.verify import check_anchors, iter_anchors

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
runner = CliRunner()


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    base = tmp_path_factory.mktemp("invariants")
    before = {p.name: file_sha256(p) for p in DATA.iterdir() if p.is_file()}
    result = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(DATA),
            "--out",
            str(base / "out"),
            "--store",
            str(base / "store"),
            "--cache-dir",
            str(base / "cache"),
        ],
    )
    assert result.exit_code == 0, result.output
    yield base, before
    for path in (base / "store").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


def test_data_files_unchanged_by_run(run):
    _, before = run
    assert {p.name: file_sha256(p) for p in DATA.iterdir() if p.is_file()} == before


def test_every_anchor_in_every_output_is_exact(run, sample_book):
    out = run[0] / "out" / PUB_REF
    total = 0
    for path in sorted(out.glob("*.json")):
        checked, problems = check_anchors(
            sample_book, json.loads(path.read_text(encoding="utf-8")), path.name
        )
        assert problems == [], [str(p) for p in problems[:3]]
        total += checked
    assert total > 1000


def test_manifest_records_integrity(run):
    manifest = json.loads((run[0] / "out" / PUB_REF / "run_manifest.json").read_text(encoding="utf-8"))
    assert (
        manifest["integrity"]["originals_unchanged"] is True
        and manifest["integrity"]["anchors_checked"] > 500
    )


def test_verify_ok(run):
    base, _ = run
    result = runner.invoke(app, ["verify", str(base / "out" / PUB_REF), "--store", str(base / "store")])
    assert result.exit_code == 0, result.output
    assert "anchors verified" in result.output


def test_corrupted_anchor_offset_is_named(run, tmp_path):
    base, _ = run
    copy = tmp_path / PUB_REF
    shutil.copytree(base / "out" / PUB_REF, copy)
    path = copy / "knowledge_units.json"
    units = json.loads(path.read_text(encoding="utf-8"))
    units[0]["anchors"][0]["start"] += 1
    path.write_text(json.dumps(units, ensure_ascii=False), encoding="utf-8")
    manifest_path = copy / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["outputs"]:
        if item["path"] == "knowledge_units.json":
            item["sha256"] = file_sha256(path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = runner.invoke(app, ["verify", str(copy), "--store", str(base / "store")])
    assert result.exit_code == 1
    assert "knowledge_units.json[0].anchors[0]" in result.output and "b000105" in result.output


def test_iter_anchors_paths():
    data = {"a": [{"block_id": "b1", "start": 0, "end": 1, "quote": "x", "block_hash": "h"}]}
    assert [path for path, _ in iter_anchors(data)] == ["$.a[0]"]
