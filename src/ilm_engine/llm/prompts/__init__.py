"""Versioned prompt files (ADR-006): `<task>.v<N>.md` with front matter `task`, `version`, `schema`.

A prompt's text is part of every LLM cache key and of the run manifest, so it must never change under
the same version: `prompts.lock` pins the sha256 of every prompt file and a test fails if a file was
edited without a new version (a new file `<task>.v<N+1>.md`).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent
LOCK_FILE = PROMPT_DIR / "prompts.lock"

_NAME = re.compile(r"^(?P<task>[a-z][a-z0-9_]*)\.(?P<version>v[1-9][0-9]*)\.md$")
_FRONT_MATTER = re.compile(r"\A---\n(?P<meta>.*?)\n---\n(?P<body>.*)\Z", re.DOTALL)


class PromptError(ValueError):
    """A prompt file is missing or malformed."""


@dataclass(frozen=True)
class Prompt:
    task: str
    version: str  # "v1"
    schema: str  # output schema name
    text: str  # the prompt body, without front matter
    sha256: str  # of the whole file


def _parse(path: Path) -> Prompt:
    match = _NAME.match(path.name)
    if not match:
        raise PromptError(f"prompt file name must be <task>.v<N>.md: {path.name}")
    raw = path.read_text(encoding="utf-8")
    parsed = _FRONT_MATTER.match(raw)
    if not parsed:
        raise PromptError(f"{path.name}: missing front matter")
    meta = dict(line.split(":", 1) for line in parsed.group("meta").splitlines() if ":" in line)
    meta = {key.strip(): value.strip() for key, value in meta.items()}
    for key in ("task", "version", "schema"):
        if not meta.get(key):
            raise PromptError(f"{path.name}: front matter lacks {key!r}")
    if (meta["task"], meta["version"]) != (match.group("task"), match.group("version")):
        raise PromptError(f"{path.name}: front matter task/version do not match the file name")
    return Prompt(
        task=meta["task"],
        version=meta["version"],
        schema=meta["schema"],
        text=parsed.group("body").strip() + "\n",
        sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )


def available(directory: Path = PROMPT_DIR) -> dict[str, list[str]]:
    """Task → sorted versions present in `directory`."""
    versions: dict[str, list[str]] = {}
    for path in sorted(directory.glob("*.md")):
        match = _NAME.match(path.name)
        if match:
            versions.setdefault(match.group("task"), []).append(match.group("version"))
    return {task: sorted(found, key=lambda v: int(v[1:])) for task, found in versions.items()}


def load_prompt(task: str, version: str | None = None, directory: Path = PROMPT_DIR) -> Prompt:
    """The prompt for `task` at `version` (default: the highest version)."""
    versions = available(directory).get(task)
    if not versions:
        raise PromptError(f"no prompt for task {task!r}")
    chosen = version or versions[-1]
    if chosen not in versions:
        raise PromptError(f"no version {chosen!r} of prompt {task!r}; available: {', '.join(versions)}")
    return _parse(directory / f"{task}.{chosen}.md")


def load(task: str, version: str | None = None) -> tuple[str, str]:
    """`(text, version)` of a prompt."""
    prompt = load_prompt(task, version)
    return prompt.text, prompt.version


def current_hashes(directory: Path = PROMPT_DIR) -> dict[str, str]:
    return {path.name: _parse(path).sha256 for path in sorted(directory.glob("*.md"))}


def write_lock(directory: Path = PROMPT_DIR) -> Path:
    """Re-pin every prompt file (run after adding a new prompt version)."""
    lock = directory / LOCK_FILE.name
    lock.write_text(json.dumps(current_hashes(directory), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return lock
