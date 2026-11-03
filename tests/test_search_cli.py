import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app

ROOT = Path(__file__).resolve().parents[1]
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
runner = CliRunner()


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    base = tmp_path_factory.mktemp("search")
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


def test_search_daraqutni_prints_pages_and_arabic(out):
    result = runner.invoke(app, ["search", "الدارقطني", "--book", PUB_REF, "--out", str(out)])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines and all(" p." in line for line in lines)
    assert any("الدارقطني" in line or "الدَّارقطني" in line for line in lines)


def test_book_defaults_to_only_run(out):
    result = runner.invoke(app, ["search", "هند بنت عتيق", "--out", str(out), "--limit", "1"])
    assert result.exit_code == 0 and "unit" in result.output and "b000135" in result.output


def test_origin_column(out):
    result = runner.invoke(app, ["search", "أسلمت", "--out", str(out), "--limit", "3"])
    assert "author_text" in result.output


def test_no_results(out):
    assert "no results" in runner.invoke(app, ["search", "zzzz", "--out", str(out)]).output
