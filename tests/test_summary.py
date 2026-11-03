import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app

ROOT = Path(__file__).resolve().parents[1]
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
runner = CliRunner()


@pytest.fixture(scope="module")
def summary(tmp_path_factory):
    base = tmp_path_factory.mktemp("summary")
    args = ["--out", str(base / "out")]
    assert (
        runner.invoke(
            app,
            [
                "run",
                "--input",
                str(ROOT / "data"),
                *args,
                "--store",
                str(base / "store"),
                "--cache-dir",
                str(base / "cache"),
            ],
        ).exit_code
        == 0
    )
    result = runner.invoke(app, ["eval", *args])
    assert result.exit_code == 0 and "summary:" in result.output
    yield (base / "out" / PUB_REF / "SUMMARY.md").read_text(encoding="utf-8")
    for path in (base / "store").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


def test_summary_counts(summary):
    assert "| blocks | 594 |" in summary
    assert "| knowledge units | 75 |" in summary
    assert "| footnote refs resolved | 300 / 300 |" in summary
    assert "| continued footnotes joined | 16 |" in summary
    assert "| nested footnotes | 1 |" in summary


def test_summary_review_and_eval(summary):
    assert "## Review queue" in summary and "| reason: sensitive |" in summary
    assert "## Evaluation against the printed index" in summary and "| precision | 1.0 |" in summary
