"""End-to-end: the whole pipeline on the sample, twice, must give identical outputs (ADR-011)."""

import hashlib
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app
from ilm_engine.enrichment.models import Enrichment
from ilm_engine.integrity.hashing import file_sha256
from ilm_engine.pipeline.steps import STEP_NAMES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
VOLATILE = {"started_at", "finished_at"}
runner = CliRunner()


def hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def stable_manifest(directory: Path) -> dict:
    manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
    for key in VOLATILE:
        manifest.pop(key)
    for step in manifest["steps"]:
        step.pop("duration_ms")
        step.pop("status")
    return manifest


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    base = tmp_path_factory.mktemp("e2e")
    data_before = {path.name: file_sha256(path) for path in DATA.iterdir() if path.is_file()}
    args = [
        "run",
        "--input",
        str(DATA),
        "--out",
        str(base / "out"),
        "--store",
        str(base / "store"),
        "--cache-dir",
        str(base / "cache"),
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    out = base / "out" / PUB_REF
    first_hashes, first_manifest = hashes(out), stable_manifest(out)
    second = runner.invoke(app, [*args, "--no-cache"])
    assert second.exit_code == 0, second.output
    yield {
        "out": out,
        "first": (first_hashes, first_manifest),
        "second": (hashes(out), stable_manifest(out)),
        "data_before": data_before,
        "output_text": first.output,
    }
    for path in (base / "store").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


def test_two_runs_give_identical_outputs(runs):
    first, second = runs["first"][0], runs["second"][0]
    assert set(first) == set(second)
    differing = [name for name in first if first[name] != second[name] and name != "run_manifest.json"]
    assert differing == [], f"outputs differ between identical runs: {differing}"


def test_manifest_identical_except_timestamps(runs):
    assert runs["first"][1] == runs["second"][1]


def test_every_step_ran(runs):
    lines = [line.split() for line in runs["output_text"].splitlines()]
    statuses = {parts[1]: parts[0] for parts in lines if len(parts) == 2 and parts[1] in STEP_NAMES}
    assert len(statuses) == 21 and set(statuses.values()) == {"ran"}


def test_all_decisions_output_files_written(runs):
    names = set(runs["first"][0])
    expected = {
        "run_manifest.json",
        "document_report.json",
        "metadata.json",
        "structure.json",
        "origin_map.json",
        "annotations.json",
        "citations.json",
        "related_works.json",
        "knowledge_units.json",
        "entities.json",
        "relationships.json",
        "search_index.json",
        "validation_report.json",
        "review_queue.json",
        "enrichment.json",
        "enrichment.db",
        "review.html",
        "graph.html",
    }
    assert expected <= names, expected - names


def test_headline_numbers(runs):
    enrichment = Enrichment.model_validate_json((runs["out"] / "enrichment.json").read_text(encoding="utf-8"))
    assert enrichment.stats["blocks"] == 594 and enrichment.stats["units"] == 75
    refs = [a for a in enrichment.annotations if a.link_method == "source_ref"]
    assert len(refs) == 300 and all(a.status == "verified" for a in refs)
    assert sum(len(a.target_block_ids) - 1 for a in enrichment.annotations) == 16
    assert sum(a.type == "nested_footnote" for a in enrichment.annotations) == 1


def test_data_folder_unchanged(runs):
    assert {path.name: file_sha256(path) for path in DATA.iterdir() if path.is_file()} == runs["data_before"]
