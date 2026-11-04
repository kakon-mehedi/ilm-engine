"""Build the `RunContext` for one book: config, LLM gateway and paths (shared by the CLI and the web UI)."""

from __future__ import annotations

import json
from pathlib import Path

from ilm_engine.config import load_config
from ilm_engine.llm.cache import ResponseCache
from ilm_engine.llm.gateway import LLMGateway, get_provider
from ilm_engine.pipeline.runner import RunContext


def prepare_context(
    inputs: dict[str, Path], out: Path, store_root: Path, cache_dir: Path, llm: str | None = None
) -> RunContext:
    """`inputs` as returned by `find_inputs`; `llm` overrides the configured provider."""
    raw = json.loads(inputs["json"].read_text(encoding="utf-8"))
    pub_id = raw.get("pub", {}).get("id") if isinstance(raw.get("pub"), dict) else None
    config = load_config(pub_id)
    provider_name = llm or config.llm.provider
    if provider_name in ("anthropic", "litellm"):
        route = config.llm.extractor
        extra = {"api_base": route.api_base} if provider_name == "litellm" and route.api_base else {}
        provider = get_provider(provider_name, default_model=route.model, **extra)
    else:
        provider = get_provider(provider_name)
    gateway = LLMGateway(provider, temperature=config.llm.temperature, cache=ResponseCache(cache_dir / "llm"))
    return RunContext(
        config=config,
        inputs=inputs,
        out_root=out,
        llm=gateway,
        options={"llm": provider_name, "store_root": store_root},
    )
