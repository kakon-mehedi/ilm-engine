import importlib

from typer.testing import CliRunner

import ilm_engine
from ilm_engine.cli import app

SUBPACKAGES = [
    "adapters",
    "canonical",
    "enrichment",
    "eval",
    "extractors",
    "extractors.genres",
    "integrity",
    "llm",
    "llm.providers",
    "nlp",
    "pipeline",
    "processors",
    "search",
    "storage",
    "validation",
]


def test_version_command_prints_package_version():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == ilm_engine.__version__


def test_all_subpackages_import():
    for name in SUBPACKAGES:
        importlib.import_module(f"ilm_engine.{name}")
