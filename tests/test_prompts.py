import json
import shutil

import pytest

from ilm_engine.llm.prompts import (
    LOCK_FILE,
    PROMPT_DIR,
    PromptError,
    available,
    current_hashes,
    load,
    load_prompt,
)

TASKS = ["entry_facts", "group_bounds", "entity_disambiguation", "genre_classify", "judge", "metadata_verify"]


def test_all_prompts_present():
    assert sorted(available()) == sorted(TASKS)


@pytest.mark.parametrize("task", TASKS)
def test_loader_returns_text_and_version(task):
    text, version = load(task)
    assert version == "v1" and text.strip() and not text.startswith("---")
    prompt = load_prompt(task, "v1")
    assert prompt.task == task and prompt.schema


@pytest.mark.parametrize("task", TASKS)
def test_prompts_require_verbatim_quotes_and_null(task):
    text = load_prompt(task).text.lower()
    assert "quote" in text and ("exact" in text or "character for character" in text)
    assert "null" in text


def test_prompt_files_match_the_lock():
    """Editing a prompt without bumping its version changes its hash and fails here."""
    locked = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    assert current_hashes() == locked, "a prompt changed: add <task>.v<N+1>.md and re-run write_lock()"


def test_edit_without_version_bump_is_detected(tmp_path):
    directory = tmp_path / "prompts"
    shutil.copytree(PROMPT_DIR, directory, ignore=shutil.ignore_patterns("*.py", "__pycache__"))
    locked = json.loads((directory / "prompts.lock").read_text(encoding="utf-8"))
    path = directory / "judge.v1.md"
    path.write_text(path.read_text(encoding="utf-8") + "Be lenient.\n", encoding="utf-8")
    assert current_hashes(directory)["judge.v1.md"] != locked["judge.v1.md"]


def test_highest_version_is_default(tmp_path):
    directory = tmp_path / "prompts"
    shutil.copytree(PROMPT_DIR, directory, ignore=shutil.ignore_patterns("*.py", "__pycache__"))
    text = (directory / "judge.v1.md").read_text(encoding="utf-8").replace("version: v1", "version: v2")
    (directory / "judge.v2.md").write_text(text, encoding="utf-8")
    assert load_prompt("judge", directory=directory).version == "v2"
    assert load_prompt("judge", "v1", directory=directory).version == "v1"


def test_errors():
    with pytest.raises(PromptError, match="no prompt"):
        load_prompt("unknown_task")
    with pytest.raises(PromptError, match="no version"):
        load_prompt("judge", "v9")


def test_mismatched_front_matter_rejected(tmp_path):
    (tmp_path / "judge.v1.md").write_text(
        "---\ntask: other\nversion: v1\nschema: X\n---\nBody\n", encoding="utf-8"
    )
    with pytest.raises(PromptError, match="do not match"):
        load_prompt("judge", directory=tmp_path)
