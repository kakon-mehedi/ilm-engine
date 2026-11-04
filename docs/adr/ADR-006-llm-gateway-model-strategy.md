# ADR-006: LLM gateway, provider-agnostic, routed by task difficulty

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§3.4 asks for suitable commercial LLM APIs and open-weight models for each task. §3.7 asks for model comparison and independent validation. Models and prices change often, and some clients cannot send text to external APIs. The MVP must also run **without any API key**, so reviewers can execute it.

The tasks in the sample vary widely in difficulty:
- **Trivial and structural:** footnote links (already in `refs`) and entry numbers. No LLM needed.
- **Medium:** entity spans in nasab chains, e.g. "هند بنت عتيق بن عابد بن عبد اللَّه بن عمر بن مخزوم" (`b000135`).
- **Hard:** group closure and gender. "١٠ - وهالة؛ ابنا أبي هالة…" (`b000137`) means entries 9 and 10 are the two sons of Abu Hala. So entry 9, "هند", is male (Hind ibn Abi Hala), unlike entry 8, Hind bint Atiq.

## Decision

- All model calls go through `llm/gateway.py`: `complete_structured(task, prompt_id, prompt_version, input, schema) -> (obj, meta)`.
- Providers: `null` (the default; returns `needs_llm`), `anthropic`, and `litellm` (any OpenAI-compatible endpoint, including self-hosted vLLM). The provider is chosen by config, never hard-coded.
- **Routing by task tier** (config `llm.routes`):
  - Tier S (bulk classification, NER candidates): Claude Haiku 5.5, or a fine-tuned open model (Qwen/Jais class) on vLLM.
  - Tier M (unit and relation extraction): Claude Sonnet 5.5 (primary).
  - Tier L (hard disambiguation, discrepancy resolution): Claude Opus 5.5.
  - **Verifier/judge:** a model from a **different family**, via `litellm` (e.g. a GPT- or Gemini-class model, or a self-hosted Qwen), so errors are less correlated.
- Temperature 0, structured JSON output validated by Pydantic, and one repair retry.
- A response cache keyed by `sha256(model_id + prompt_id + prompt_version + canonical input)` (`llm/cache.py`).
- Prompts are versioned files, `llm/prompts/<task>.v<N>.md`. Their versions are recorded in `run_manifest.json`.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Gateway + tiered routing + cross-family verifier (chosen)** | Swap models by config; cost control; independent validation; offline MVP | Gateway code to maintain |
| B. One large commercial model for everything | Simplest | Expensive at scale; correlated errors (self-verification); vendor lock-in |
| C. Open-weight only | Data stays in-house; cheap per token | Lower quality on classical Arabic without fine-tuning; GPU operations |
| D. Direct SDK calls in each extractor | Quick | Model choice scattered; no central cache, logging or cost tracking |

## Consequences

- **+** Privacy-sensitive deployments can route everything to self-hosted models.
- **+** Cost is controlled per tier, and most tokens go to cheap tiers.
- **−** Different providers return slightly different JSON. Pydantic validation plus a repair retry absorbs that.
- **−** Model upgrades change outputs. Prompt and model versions in the manifest make the change visible (ADR-011).

## Compliance / how verified

- Tests run with the `null` provider and check that LLM-only tasks produce `needs_llm` issues instead of failing.
- Cache test: a second identical call makes zero provider requests.
- Manifest test: every LLM-derived fact records `model_id` and `prompt_version`.

## Related

ADR-007, ADR-008, ADR-014, ADR-015.
