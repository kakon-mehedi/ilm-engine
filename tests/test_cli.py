import copy
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app
from ilm_engine.pipeline.steps import STEP_NAMES
from ilm_engine.schema_export import TOP_LEVEL_MODELS, schemas

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
runner = CliRunner()


@pytest.fixture
def dirs(tmp_path):
    paths = {"out": tmp_path / "out", "store": tmp_path / "store", "cache": tmp_path / "cache"}
    yield paths
    for path in paths["store"].rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


def run(dirs, *args):
    return runner.invoke(
        app,
        [
            "run",
            *args,
            "--out",
            str(dirs["out"]),
            "--store",
            str(dirs["store"]),
            "--cache-dir",
            str(dirs["cache"]),
        ],
    )


def test_list_steps():
    result = runner.invoke(app, ["run", "--list-steps"])
    assert result.exit_code == 0 and result.output.split() == list(STEP_NAMES)


def test_run_on_data_folder_finds_json_and_pdf(dirs):
    result = run(dirs, "--input", str(DATA))
    assert result.exit_code == 0, result.output
    out = dirs["out"] / PUB_REF
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert {Path(item["path"]).name for item in manifest["inputs"]} == {
        "demo_book_daraqutni.json",
        "demo_book_daraqutni_v1.pdf",
    }
    assert manifest["adapter"]["id"] == "shamela_v3" and manifest["counts"]["blocks"] == 594
    assert (dirs["store"] / PUB_REF / "demo_book_daraqutni.json").is_file()


def test_second_run_is_fully_cached(dirs):
    run(dirs, "--input", str(DATA))
    result = run(dirs, "--input", str(DATA))
    assert result.exit_code == 0
    assert {line.split()[0] for line in result.output.splitlines() if line.split()[-1] in STEP_NAMES} == {
        "cached"
    }


def test_unknown_schema_exits_2(dirs, tmp_path):
    raw = json.loads((DATA / "demo_book_daraqutni.json").read_text(encoding="utf-8"))
    broken = copy.deepcopy(raw)
    broken["metadata"]["af_schema"] = "9.9"
    path = tmp_path / "book.json"
    path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    result = run(dirs, "--input", str(path))
    assert result.exit_code == 2
    assert "failed" in result.output and "adapt" in result.output


def test_unknown_llm_provider_rejected(dirs):
    result = run(dirs, "--input", str(DATA), "--llm", "gpt")
    assert result.exit_code != 0 and "--llm" in result.output


def test_verify_ok_then_detects_tampering(dirs):
    run(dirs, "--input", str(DATA))
    out = dirs["out"] / PUB_REF
    ok = runner.invoke(app, ["verify", str(out), "--store", str(dirs["store"])])
    assert ok.exit_code == 0, ok.output
    assert ok.output.startswith("OK " + PUB_REF)
    stored = dirs["store"] / PUB_REF / "demo_book_daraqutni.json"
    os.chmod(stored, 0o644)
    stored.write_bytes(stored.read_bytes() + b" ")
    os.chmod(stored, 0o444)
    failed = runner.invoke(app, ["verify", str(out), "--store", str(dirs["store"])])
    assert failed.exit_code == 1 and "original store check failed" in failed.output


def test_verify_detects_changed_output(dirs):
    run(dirs, "--input", str(DATA))
    out = dirs["out"] / PUB_REF
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    (out / "structure.json").write_text("{}", encoding="utf-8")
    manifest["outputs"].append({"path": "structure.json", "sha256": "sha256:" + "0" * 64, "bytes": 2})
    (out / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    failed = runner.invoke(app, ["verify", str(out), "--store", str(dirs["store"])])
    assert failed.exit_code == 1 and "output changed or missing: structure.json" in failed.output


def test_verify_without_manifest_fails(tmp_path):
    result = runner.invoke(app, ["verify", str(tmp_path)])
    assert result.exit_code == 1


def test_schema_export_writes_one_file_per_model(tmp_path):
    result = runner.invoke(app, ["schema", "export", "--out", str(tmp_path / "schemas")])
    assert result.exit_code == 0
    files = sorted(path.name for path in (tmp_path / "schemas").iterdir())
    genres = ["aqeedah", "biography", "fiqh", "hadith", "history", "seerah", "tafsir"]
    assert files == sorted(
        [f"{model.__name__}.json" for model in TOP_LEVEL_MODELS] + [f"genre_{g}.json" for g in genres]
    )
    span = json.loads((tmp_path / "schemas" / "CanonicalBook.json").read_text(encoding="utf-8"))["$defs"][
        "Span"
    ]
    assert "class" in span["properties"]


def test_committed_schemas_are_current():
    """Models changed without `ilm-engine schema export --out schemas`?"""
    committed = {path.name: path.read_bytes() for path in (ROOT / "schemas").glob("*.json")}
    assert committed == schemas()
