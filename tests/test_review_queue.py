import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app

ROOT = Path(__file__).resolve().parents[1]
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
runner = CliRunner()


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("review")
    args = [
        "run",
        "--input",
        str(ROOT / "data"),
        "--out",
        str(base / "out"),
        "--store",
        str(base / "store"),
        "--cache-dir",
        str(base / "cache"),
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    yield base, args
    for path in (base / "store").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


def queue(base):
    return json.loads((base / "out" / PUB_REF / "review_queue.json").read_text(encoding="utf-8"))


def test_queue_contents(run_dir):
    items = queue(run_dir[0])
    by_target = {item["target_id"]: item for item in items}
    assert "b000215" in by_target and "structural_issue" in by_target["b000215"]["reason"]
    grading = [i for i in items if "hadith_grading" in i["sensitive"]]
    assert grading and all(i["required_role"] == "scholar_reviewer" and i["priority"] == 0 for i in grading)
    assert any("b000228" in i["context_block_ids"] for i in grading)
    assert any("needs_llm" in i["reason"] for i in items)
    inferred = [
        i
        for i in items
        if i["target_kind"] == "relationship" and (i["proposed_value"] or {}).get("assertion") == "inferred"
    ]
    assert inferred


def test_priority_order(run_dir):
    priorities = [item["priority"] for item in queue(run_dir[0])]
    assert priorities == sorted(priorities)


def test_review_html_offline_and_rtl(run_dir):
    html = (run_dir[0] / "out" / PUB_REF / "review.html").read_text(encoding="utf-8")
    assert '<html lang="ar" dir="rtl">' in html and "<mark>" in html and "#page=" in html
    assert "http://" not in html and "https://" not in html


def test_apply_decisions_status_audit_training_and_rerun(run_dir):
    base, args = run_dir
    items = queue(base)
    editable = [i for i in items if not i["sensitive"]][:2]
    decisions = [
        {
            "review_id": editable[0]["review_id"],
            "decision": "approved",
            "reviewer_id": "r1",
            "reviewer_role": "editor_reviewer",
            "decided_at": "2026-11-03T10:00:00+00:00",
        },
        {
            "review_id": editable[1]["review_id"],
            "decision": "edited",
            "new_value": {"note": "fixed"},
            "reviewer_id": "r1",
            "reviewer_role": "editor_reviewer",
            "decided_at": "2026-11-03T10:01:00+00:00",
        },
    ]
    path = base / "decisions.json"
    path.write_text(json.dumps(decisions), encoding="utf-8")
    result = runner.invoke(app, ["review", "apply", str(path), "--book", PUB_REF, "--out", str(base / "out")])
    assert result.exit_code == 0, result.output
    out = base / "out" / PUB_REF
    statuses = {i["review_id"]: i["status"] for i in queue(base)}
    assert statuses[editable[0]["review_id"]] == "approved" and statuses[editable[1]["review_id"]] == "edited"
    assert len((out / "review_audit.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    training = (out / "training_examples.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(training) == 2 and json.loads(training[1])["output"] == {"note": "fixed"}

    rerun = runner.invoke(app, args)
    assert rerun.exit_code == 0
    statuses = {i["review_id"]: i["status"] for i in queue(base)}
    assert statuses[editable[0]["review_id"]] == "approved"


def test_sensitive_item_needs_scholar(run_dir):
    base, _ = run_dir
    sensitive = next(i for i in queue(base) if i["sensitive"])
    path = base / "bad.json"
    path.write_text(
        json.dumps(
            [
                {
                    "review_id": sensitive["review_id"],
                    "decision": "approved",
                    "reviewer_id": "r2",
                    "reviewer_role": "editor_reviewer",
                    "decided_at": "2026-11-03T10:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["review", "apply", str(path), "--book", PUB_REF, "--out", str(base / "out")])
    assert result.exit_code == 1 and "scholar" in result.output
