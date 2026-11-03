"""Anthropic provider (primary extractor, ADR-006), using the official `anthropic` SDK (`llm` extra).

Structured output uses `output_config.format` with the task's JSON Schema. Current Claude models reject
sampling parameters and forced `tool_choice`, so no temperature is sent; repeatability comes from the
gateway's response cache. Credentials are resolved by the SDK (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`
or an `ant auth login` profile) when the provider is first used.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from ilm_engine.llm.gateway import register_provider
from ilm_engine.llm.providers.base import LLMRequest, ProviderResponse
from ilm_engine.log import get_logger

log = get_logger("llm.anthropic")

DEFAULT_MODEL = "claude-sonnet-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM_PROMPT = (
    "You extract structured information from classical Arabic book text. Return only JSON that matches "
    "the schema. Every fact needs a verbatim quote copied from the input; return null for anything that "
    "is not in the text."
)


class ProviderConfigError(RuntimeError):
    """The provider was selected but cannot be used (package or credentials missing)."""


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Copy of a Pydantic JSON Schema with `additionalProperties: false` on every object."""
    result = copy.deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                node.setdefault("additionalProperties", False)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(result)
    return result


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        default_model: str = DEFAULT_MODEL,
        client: Any | None = None,
        max_tokens: int = 16000,
        fallbacks: bool = True,
    ) -> None:
        self.default_model = default_model
        self.max_tokens = max_tokens
        self.fallbacks = fallbacks
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise ProviderConfigError(
                    "LLM provider 'anthropic' is selected but the anthropic SDK is not installed; "
                    "install the 'llm' extra (uv sync --extra llm)"
                ) from exc
            try:
                self._client = anthropic.Anthropic()
            except anthropic.AnthropicError as exc:
                raise ProviderConfigError(
                    "LLM provider 'anthropic' is selected but no credentials were found; set "
                    "ANTHROPIC_API_KEY or run `ant auth login`"
                ) from exc
        return self._client

    def build_params(self, request: LLMRequest) -> dict[str, Any]:
        """Request parameters for `messages.create` (exposed for tests and logging)."""
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": json.dumps(request.input, ensure_ascii=False, sort_keys=True)}
        ]
        if request.repair_of is not None:
            messages += [
                {"role": "assistant", "content": request.repair_of},
                {
                    "role": "user",
                    "content": f"That output failed validation:\n{request.repair_errors}\nFix it.",
                },
            ]
        params: dict[str, Any] = {
            "model": request.model,
            "max_tokens": self.max_tokens,
            "system": request.prompt or SYSTEM_PROMPT,
            "messages": messages,
            "output_config": {
                "format": {"type": "json_schema", "schema": strict_schema(request.output_schema)}
            },
        }
        if self.fallbacks:
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"
        return params

    def complete(self, request: LLMRequest) -> ProviderResponse | None:
        client = self._get_client()
        params = self.build_params(request)
        if self.fallbacks:
            response = client.beta.messages.create(**params)
        else:
            response = client.messages.create(**params)

        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            log.warning(
                "model declined the request",
                extra={"task": request.task, "category": getattr(details, "category", None)},
            )
        text = next((block.text for block in response.content if block.type == "text"), "")
        usage = getattr(response, "usage", None)
        return ProviderResponse(
            text=text,
            model=response.model,
            usage={
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            },
        )


register_provider("anthropic", AnthropicProvider)
