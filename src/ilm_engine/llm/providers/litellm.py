"""LiteLLM provider: any OpenAI-compatible endpoint, including self-hosted vLLM (ADR-006).

Used for the independent verifier/judge family. `model` is a LiteLLM model string
(`<provider>/<model>`), `api_base` an optional endpoint. Requires the `llm` extra.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from ilm_engine.llm.gateway import register_provider
from ilm_engine.llm.providers.anthropic import SYSTEM_PROMPT, ProviderConfigError, strict_schema
from ilm_engine.llm.providers.base import LLMRequest, ProviderResponse


class LiteLLMProvider:
    name = "litellm"

    def __init__(
        self,
        default_model: str = "",
        api_base: str | None = None,
        completion: Callable[..., Any] | None = None,
        max_tokens: int = 16000,
    ) -> None:
        self.default_model = default_model
        self.api_base = api_base
        self.max_tokens = max_tokens
        self._completion = completion

    def _get_completion(self) -> Callable[..., Any]:
        if self._completion is None:
            try:
                import litellm
            except ImportError as exc:
                raise ProviderConfigError(
                    "LLM provider 'litellm' is selected but litellm is not installed; install the 'llm' extra"
                ) from exc
            self._completion = litellm.completion
        return self._completion

    def build_params(self, request: LLMRequest) -> dict[str, Any]:
        if not request.model:
            raise ProviderConfigError("LLM provider 'litellm' needs a model (llm.verifier.model)")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": request.prompt or SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(request.input, ensure_ascii=False, sort_keys=True)},
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
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.task,
                    "schema": strict_schema(request.output_schema),
                    "strict": True,
                },
            },
        }
        if self.api_base:
            params["api_base"] = self.api_base
        return params

    def complete(self, request: LLMRequest) -> ProviderResponse | None:
        response = self._get_completion()(**self.build_params(request))
        usage = getattr(response, "usage", None)
        return ProviderResponse(
            text=response.choices[0].message.content or "",
            model=getattr(response, "model", None) or request.model,
            usage={
                "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            },
        )


register_provider("litellm", LiteLLMProvider)
