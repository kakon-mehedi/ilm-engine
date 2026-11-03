import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app
from ilm_engine.enrichment.models import Enrichment
from ilm_engine.eval.gold import evaluate, load_gold

ROOT = Path(__file__).resolve().parents[1]
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
runner = CliRunner()


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    base = tmp_path_factory.mktemp("eval")
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
    yield base / "out"
    for path in (base / "store").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


def test_eval_prints_metrics_and_writes_report(out):
    result = runner.invoke(app, ["eval", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "precision" in result.output and "recall" in result.output and "f1" in result.output
    report = json.loads((out / PUB_REF / "eval_report.json").read_text(encoding="utf-8"))
    assert report["gold"]["entries"] == 75 and report["matched"] == 75
    assert report["precision"] == report["recall"] == report["f1"] == 1.0
    assert report["chain_agreement"]["checked"] > 30 and report["chain_agreement"]["rate"] == 1.0


def test_wrong_subject_is_a_miss_and_false_positive(out):
    enrichment = Enrichment.model_validate_json(
        (out / PUB_REF / "enrichment.json").read_text(encoding="utf-8")
    )
    eight = next(u for u in enrichment.knowledge_units if u.entry_no == 8)
    nine = next(u for u in enrichment.knowledge_units if u.entry_no == 9)
    swapped = [
        u.model_copy(update={"subject_entity_id": eight.subject_entity_id}) if u.entry_no == 1 else u
        for u in enrichment.knowledge_units
    ]
    report = evaluate(enrichment.model_copy(update={"knowledge_units": swapped}), load_gold())
    assert [m["entry_no"] for m in report["missed"]] == [1]
    assert report["recall"] == round(74 / 75, 4) and report["false_positives"][0]["entry_no"] == 1
    assert nine.subject_entity_id != eight.subject_entity_id
