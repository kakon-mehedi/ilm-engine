"""LLM gateway: the only path from pipeline code to a model (ADR-006).

`complete_json` sends one structured-output request through the configured provider, at temperature 0,
with a response cache, JSON extraction, Pydantic schema validation and one repair retry. Swapping
models or providers is configuration only; every caller sees the same `LLMResult`.

The null provider answers nothing: the result then has `needs_llm=True` and the caller records the
issue `needs_llm` on the affected item (`needs_llm_issue`).
"""

from __future__ import annotations

import importlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from pydantic import BaseModel, ValidationError

from ilm_engine.enrichment.models import Issue, Provenance
from ilm_engine.ids import make_id, natural_key
from ilm_engine.llm.cache import ResponseCache, cache_key
from ilm_engine.llm.providers.base import LLMProvider, LLMRequest, ProviderResponse
from ilm_engine.llm.providers.fixture import FixtureProvider
from ilm_engine.llm.providers.null import NullProvider
from ilm_engine.log import get_logger

log = get_logger("llm.gateway")

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class LLMResult[T: BaseModel]:
    output: T | None  # validated against the schema; None if no provider answer or still invalid
    model: str
    provider: str
    task: str
    prompt_version: str
    raw: str | None
    cached: bool = False
    repaired: bool = False  # needed the one schema-repair retry (schema factor 0.9)
    schema_valid: bool = False
    needs_llm: bool = False  # no provider answered (null provider)
    errors: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


class LLMGateway:
    def __init__(
        self,
        provider: LLMProvider,
        model: str | None = None,
        temperature: float = 0.0,
        cache: ResponseCache | None = None,
    ) -> None:
        self.provider = provider
        self.model = model or provider.default_model
        self.temperature = temperature
        self.cache = cache

    def complete_json[T: BaseModel](
        self,
        task: str,
        prompt_version: str,
        input: Any,
        schema: type[T],
        prompt: str | None = None,
        model: str | None = None,
    ) -> LLMResult[T]:
        """Structured completion validated against `schema`."""
        model = model or self.model
        request = LLMRequest(
            task=task,
            prompt_version=prompt_version,
            input=input,
            output_schema=schema.model_json_schema(),
            model=model,
            temperature=self.temperature,
            prompt=prompt,
        )
        key = cache_key(self.provider.name, model, task, prompt_version, input)
        cached = self.cache.get(key) if self.cache is not None else None
        if cached is not None:
            replay = ProviderResponse(cached["text"], cached["model"], cached.get("usage", {}))
            repair = cached.get("repair")
            replay_repair = ProviderResponse(repair["text"], repair["model"], {}) if repair else None
            return self._validate(request, schema, replay, replay_repair, cached=True)

        response = self.provider.complete(request)
        if response is None:
            log.info(
                "no LLM provider answer; item needs_llm", extra={"task": task, "provider": self.provider.name}
            )
            return LLMResult(None, model, self.provider.name, task, prompt_version, None, needs_llm=True)

        output, errors = _parse(response.text, schema)
        repair_response = None
        if output is None:
            repair_request = replace(request, repair_of=response.text, repair_errors=errors)
            repair_response = self.provider.complete(repair_request)

        if self.cache is not None:
            record: dict[str, Any] = {"text": response.text, "model": response.model, "usage": response.usage}
            if repair_response is not None:
                record["repair"] = {"text": repair_response.text, "model": repair_response.model}
            self.cache.put(key, record)
        return self._validate(request, schema, response, repair_response, cached=False)

    def _validate[T: BaseModel](
        self,
        request: LLMRequest,
        schema: type[T],
        response: ProviderResponse,
        repair: ProviderResponse | None,
        cached: bool,
    ) -> LLMResult[T]:
        output, errors = _parse(response.text, schema)
        raw, repaired = response.text, False
        if output is None and repair is not None:
            output, errors = _parse(repair.text, schema)
            raw, repaired = repair.text, True
        if output is None:
            log.warning("LLM output failed schema validation", extra={"task": request.task, "errors": errors})
        return LLMResult(
            output=output,
            model=response.model,
            provider=self.provider.name,
            task=request.task,
            prompt_version=request.prompt_version,
            raw=raw,
            cached=cached,
            repaired=repaired,
            schema_valid=output is not None,
            errors=None if output is not None else errors,
            usage=response.usage,
        )


def _parse[T: BaseModel](text: str, schema: type[T]) -> tuple[T | None, str | None]:
    """Validate the JSON in `text` (bare, or in a ```json fence) against `schema`."""
    fenced = _FENCE.search(text)
    candidate = (fenced.group(1) if fenced else text).strip()
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    try:
        return schema.model_validate(data), None
    except ValidationError as exc:
        return None, str(exc)


_PROVIDERS: dict[str, Callable[..., LLMProvider]] = {
    "null": NullProvider,
    "fixture": FixtureProvider,
}


def register_provider(name: str, factory: Callable[..., LLMProvider]) -> None:
    _PROVIDERS[name] = factory


def get_provider(name: str, **options: Any) -> LLMProvider:
    """Provider by config name; `anthropic`/`litellm` register themselves when their extra is installed."""
    if name not in _PROVIDERS and name.isidentifier():
        try:  # provider modules register themselves on import
            importlib.import_module(f"ilm_engine.llm.providers.{name}")
        except ModuleNotFoundError:
            pass
    if name not in _PROVIDERS:
        raise ValueError(f"unknown LLM provider {name!r}; known: {', '.join(sorted(_PROVIDERS))}")
    return _PROVIDERS[name](**options)


def needs_llm_issue(pub_ref: str, target_kind: str, target_id: str, task: str, step: str) -> Issue:
    """The `needs_llm` issue for an item the null provider could not process."""
    return Issue(
        issue_id=make_id("iss", pub_ref, natural_key("needs_llm", target_id, task)),
        code="needs_llm",
        severity="info",
        target_kind=target_kind,  # type: ignore[arg-type]
        target_id=target_id,
        message=f"LLM task {task!r} was not run (no LLM provider configured); the item needs review.",
        details={"task": task},
        provenance=Provenance(method="rule", step=step, step_version="1.0.0"),
    )
