"""Fixture provider: replays recorded responses from `tests/fixtures/llm/<request key>.json`.

Used by CI and tests; it never touches the network. A request without a recorded response raises
`FixtureMissingError`, so a changed prompt or input cannot silently pass.
"""

from __future__ import annotations

import json
from pathlib import Path

from ilm_engine.llm.cache import request_key
from ilm_engine.llm.providers.base import LLMRequest, ProviderResponse

DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "llm"


class FixtureMissingError(LookupError):
    """No recorded response exists for a request."""


class FixtureProvider:
    name = "fixture"

    def __init__(self, directory: str | Path = DEFAULT_FIXTURE_DIR, default_model: str = "fixture") -> None:
        self.directory = Path(directory)
        self.default_model = default_model

    def path_for(self, request: LLMRequest) -> Path:
        key = request_key(request.model, request.task, request.prompt_version, request.input)
        suffix = ".repair" if request.repair_of is not None else ""
        return self.directory / f"{key}{suffix}.json"

    def complete(self, request: LLMRequest) -> ProviderResponse | None:
        path = self.path_for(request)
        if not path.is_file():
            raise FixtureMissingError(
                f"no recorded LLM response for task {request.task!r} {request.prompt_version}: {path}"
            )
        record = json.loads(path.read_text(encoding="utf-8"))
        return ProviderResponse(
            text=record["text"], model=record.get("model", request.model), usage=record.get("usage", {})
        )


def record_fixture(directory: str | Path, request: LLMRequest, text: str, model: str | None = None) -> Path:
    """Write a fixture for `request` (used to record responses for tests)."""
    provider = FixtureProvider(directory)
    path = provider.path_for(request)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"task": request.task, "prompt_version": request.prompt_version, "model": model or request.model}
    path.write_text(
        json.dumps({**record, "text": text}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path
