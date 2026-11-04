"""Null provider (default): answers nothing, so the MVP runs without any API key.

LLM-dependent items then carry the issue `needs_llm` and go to review.
"""

from __future__ import annotations

from ilm_engine.llm.providers.base import LLMRequest, ProviderResponse


class NullProvider:
    name = "null"
    default_model = "null"

    def complete(self, request: LLMRequest) -> ProviderResponse | None:
        return None
