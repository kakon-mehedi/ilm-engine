# ADR-014: Agents only where needed (four agents)

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

The assignment is titled "Agentic AI", and it also asks (§3) to "distinguish which tasks are best handled through conventional programming, NLP, LLMs or agentic workflows". An agent (an LLM that decides its next action and uses tools in a loop) is powerful, but it costs more, is less predictable and is harder to test than a fixed step.

Most work on the sample is deterministic:
- resolving the 300 `refs`;
- building the section tree from 15 headings and 2 TOC headings;
- finding the 75 entry numbers;
- joining the 16 continued footnotes.

Only a few tasks need open-ended decisions or tool use:
- choosing a genre schema per section;
- deciding which cited work "الإصابة" (with locator `(٨/ ١٥٧)` in `b000139`) refers to in a catalog;
- resolving a disagreement between models by re-reading the source.

A common anti-pattern is to call every stage an "agent". Most stages here are deterministic and gain nothing from autonomy.

## Decision

Exactly four agents exist, implemented in production with LangGraph. In the MVP they are plain functions behind the same interface.

| Agent | Decides | Tools |
|---|---|---|
| **Genre Router** | primary and secondary genre per section; which plugins to run | category metadata, heading text, sample blocks, genre classifier |
| **Genre Extractor** (one per plugin) | which candidates become units; how to fill the schema | candidate list, block reader, schema validator |
| **Related-Works / Citation Resolver** | which catalog work a citation or mention refers to | catalog search, title normalizer, author lookup |
| **Discrepancy Resolver** | how to settle model disagreement or a validation conflict | re-read source blocks, call second model, open issue |

Everything else is a **worker**: a deterministic function (`processors/*`, `validation/*`, `storage/*`). Each agent has a step budget (max tool calls, max tokens) and must end with a schema-valid output or an issue.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Four bounded agents + deterministic workers (chosen)** | Agentic where it adds value; testable; cheap | Agent boundaries need discipline |
| B. Agent for every stage | Looks "agentic" | Costly, non-deterministic, hard to test; violates repeatability |
| C. No agents (pure pipeline + single LLM calls) | Simplest | Weak at catalog lookup and dispute resolution, which need iterative tool use |
| D. Fully autonomous planner agent | Flexible | Unbounded cost; unsafe for religious content |

## Consequences

- **+** Clear answer to "programming vs NLP vs LLM vs agentic" (see the table in the architecture doc).
- **+** Agents can be replaced by better models without touching workers.
- **−** Agent traces must be logged (Langfuse in production; JSON trace in the MVP) to stay debuggable.

## Compliance / how verified

- Architecture review: only modules under `agents/` (production) or the four named functions (MVP) may call `llm/gateway.py` in a loop.
- Test: each agent stops within its step budget on the sample and returns valid output or an issue.

## Related

ADR-006, ADR-013, ADR-018.
