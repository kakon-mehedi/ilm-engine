"""Provider interface: turn one request into raw text; validation, caching and retries are the gateway's."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMRequest:
    task: str  # prompt id, e.g. "extract_biography"
    prompt_version: str  # e.g. "v1"
    input: Any  # JSON-serializable task input (block ids, texts, ...)
    output_schema: dict[str, Any]  # JSON Schema of the expected output
    model: str
    temperature: float = 0.0
    prompt: str | None = None  # rendered prompt text (versioned prompt files, T-093)
    repair_of: str | None = None  # previous raw output that failed validation
    repair_errors: str | None = None


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model: str  # the model that actually answered
    usage: dict[str, int] = field(default_factory=dict)  # {"input_tokens": .., "output_tokens": ..}


class LLMProvider(Protocol):
    name: str  # "null" | "fixture" | "anthropic" | "litellm"
    default_model: str

    def complete(self, request: LLMRequest) -> ProviderResponse | None:
        """Raw response, or None when this provider cannot answer (the null provider)."""
        ...
