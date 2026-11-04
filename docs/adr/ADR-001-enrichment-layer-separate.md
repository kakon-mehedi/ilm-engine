# ADR-001: Enrichment layer is stored separately from the original book

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

The assignment (§1, §6) requires: "The original book content must remain unchanged. All additional information will be maintained in a separate structured enrichment layer and linked to the corresponding book content."

The sample input is a Shamela-derived archive record (`src-shamela`, `claim_type: faithful_to_source`, revision `pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6`). It already has stable block IDs (`b000001` … `b000594`) and character-offset `refs` from text to footnotes (300 refs, all targets exist). That makes linking without copying feasible.

The book has several voices in one file: the author (al-Daraqutni), the transmitters (isnad, page 19), and the muhaqqiq's introduction and 317 footnotes. Mixing our output into the text would blur these voices even more.

## Decision

- Treat the original JSON and PDF as **read-only inputs**. No step writes to `data/` or `store/originals/`.
- Keep all derived information (metadata, structure, annotations, citations, units, entities, relationships, validation, review) in a **separate enrichment layer**: JSON files in `output/<pub_ref>/` plus `enrichment.db` in the MVP, and PostgreSQL in production (ADR-005).
- Every enrichment record links to the original through **anchors** (ADR-003). It never carries an edited copy of the source text. A `quote` field is allowed only as a verifiable excerpt (`text[start:end] == quote`).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Separate layer linked by anchors (chosen)** | Original stays byte-identical; enrichment can be regenerated, versioned and reviewed independently; clean author vs AI separation | Needs stable anchors and stale-anchor handling (ADR-017) |
| B. Inline annotation in the source JSON (add fields to blocks) | Simple to read; one file | Modifies the original (violates §6); every re-run rewrites the source; conflicts with new source revisions |
| C. Copy text into enrichment records (denormalized) | Fast reads, no join | Copies drift from the original; impossible to prove the text was not altered; doubles storage |
| D. Standoff annotation in a separate TEI/XML file | Scholarly standard | Heavy tooling; our input is JSON; adds a format conversion with no MVP benefit |

## Consequences

- **+** Satisfies §6 bullets 1–3 directly and makes them testable.
- **+** A new source revision (r7) does not destroy existing enrichment; only changed blocks are reprocessed (ADR-017).
- **+** Enrichment can be published separately (e.g. as an API) without re-publishing the book.
- **−** Readers need a join (anchor → block) to show context. The MVP ships a resolver in `storage/json_store.py`.
- **−** Source revision changes must be detected and handled (ADR-017).

## Compliance / how verified

- Invariant test (E02): the SHA-256 of every file in `data/` is identical before and after `ilm-engine run`.
- Test: every `quote` equals `block.text[start:end]`; no enrichment record stores free source text outside `quote`.
- Code rule: only `storage/*` may write files, and only under `output/` and `store/`.

## Related

ADR-003 (anchors), ADR-005 (storage), ADR-010 (origin layers), ADR-017 (integrity).
