"""Human-readable progress for `ilm-engine run`: what each step does and what it found.

The runner calls a `StepListener` before and after every step; `Narrator` turns those calls into
lines such as `Pipeline_01 ✓ Got the input: book.json + scan.pdf (68 pages). Moving to adapt →`.
Summaries read the step's own result, so they report real numbers, and never fail the run.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ilm_engine.enrichment.models import StepRecord
    from ilm_engine.pipeline.runner import RunContext, Step


@dataclass(frozen=True)
class StepStory:
    phase: str
    title: str
    doing: str
    summary: Callable[[RunContext], str]


def _data(ctx: RunContext, step: str, key: str) -> Any:
    return ctx.results[step].data[key]


def _ingest(ctx: RunContext) -> str:
    files = " + ".join(path.name for path in ctx.inputs.values())
    return f"Got the input: {files}"


def _adapt(ctx: RunContext) -> str:
    adapter, counts = _data(ctx, "adapt", "adapter"), _data(ctx, "adapt", "counts")
    return (
        f"Detected format {adapter['source_code']} v{adapter['schema_version']} → adapter "
        f"{adapter['id']}; canonical book has {counts['pages']} pages, {counts['blocks']} blocks "
        f"(pub_ref {ctx.pub_ref})"
    )


def _integrity_register(ctx: RunContext) -> str:
    stored = _data(ctx, "integrity_register", "stored")
    verified = "verified" if stored.source_declared_hash_verified else "not reproducible (kept our own)"
    return (
        f"Copied {len(stored.files)} original file(s) to a read-only store and hashed them; "
        f"publisher's declared hash {verified}"
    )


def _document_analysis(ctx: RunContext) -> str:
    report = _data(ctx, "document_analysis", "report")
    return (
        f"{report.page_count_held} pages held, {report.block_total} blocks, {report.ref_count} footnote "
        f"markers, {len(report.missing_printed_pages)} printed page(s) missing, "
        f"{len(ctx.results['document_analysis'].issues)} quality note(s)"
    )


def _structure(ctx: RunContext) -> str:
    structure = _data(ctx, "structure", "structure")
    return f"Built {len(structure.sections)} sections and aligned them with the table of contents"


def _origin(ctx: RunContext) -> str:
    counts = Counter(str(origin) for origin in _data(ctx, "origin", "origins").values())
    parts = ", ".join(f"{count} {name}" for name, count in counts.most_common())
    return f"Labelled who speaks in every block: {parts}"


def _field(field: Any) -> str:
    value = getattr(field, "value", None)
    if isinstance(value, dict):
        value = value.get("name")
    return "?" if value is None else str(value)


def _metadata(ctx: RunContext) -> str:
    record = _data(ctx, "metadata", "metadata")
    return (
        f"Title «{_field(record.title)}», author «{_field(record.author)}», editor "
        f"«{_field(record.editor)}»; {len(record.missing_fields)} field(s) missing"
    )


def _genre(ctx: RunContext) -> str:
    decision = _data(ctx, "genre", "genre")
    secondary = ", ".join(decision.secondary) or "none"
    return f"Genre {decision.primary} (secondary: {secondary}) → {decision.primary} extractor selected"


def _annotations(ctx: RunContext) -> str:
    annotations = _data(ctx, "annotations", "annotations").annotations
    continued = sum(len(a.target_block_ids) - 1 for a in annotations)
    return f"Linked {len(annotations)} footnotes to their markers ({continued} continued across pages joined)"


def _citations(ctx: RunContext) -> str:
    counts = _data(ctx, "citations", "counts")
    works = len(_data(ctx, "citations", "citations").works)
    return (
        f"Found {counts['citations']} citations of {works} works and {counts['internal_refs']} "
        "cross-references inside the book"
    )


def _related_works(ctx: RunContext) -> str:
    counts = _data(ctx, "related_works", "counts")
    return f"Resolved {counts['works']} works and {counts['work_relations']} work-to-work relations"


def _units(ctx: RunContext) -> str:
    counts = _data(ctx, "units", "counts")
    return f"Extracted {counts['units']} knowledge units (biographical entries) with {counts['facts']} facts"


def _entities(ctx: RunContext) -> str:
    return f"Identified {len(_data(ctx, 'entities', 'entities'))} people and linked each entry to its subject"


def _relations(ctx: RunContext) -> str:
    relationships = _data(ctx, "relations", "relationships")
    by_assertion = Counter(r.assertion for r in relationships)
    return (
        f"Found {len(relationships)} family relationships ({by_assertion['stated']} stated, "
        f"{by_assertion['inferred']} inferred); {len(_data(ctx, 'relations', 'entities'))} people in total"
    )


def _search_index(ctx: RunContext) -> str:
    mode = "lexical + semantic" if _data(ctx, "search_index", "semantic") else "lexical (BM25)"
    return f"Indexed {_data(ctx, 'search_index', 'counts')['search_documents']} documents, {mode}"


def _validate(ctx: RunContext) -> str:
    results = _data(ctx, "validate", "validation").results
    decisions = Counter(str(result.decision) for result in results)
    parts = ", ".join(f"{count} {name}" for name, count in decisions.most_common())
    return f"Checked evidence and confidence for {len(results)} records: {parts}"


def _review_queue(ctx: RunContext) -> str:
    items = _data(ctx, "review_queue", "review_items")
    sensitive = sum(bool(item.sensitive) for item in items)
    return f"Queued {len(items)} items for human review ({sensitive} sensitive → scholar only)"


def _store(ctx: RunContext) -> str:
    counts = _data(ctx, "store", "db_counts")
    return f"Saved the enrichment to SQLite: {sum(counts.values())} rows in {len(counts)} tables"


def _export(ctx: RunContext) -> str:
    return "Wrote enrichment.json, graph.html and graph.cypher"


def _integrity_verify(ctx: RunContext) -> str:
    integrity = _data(ctx, "integrity_verify", "integrity")
    return f"Originals unchanged; all {integrity['anchors_checked']} source anchors still match the text"


def _manifest(ctx: RunContext) -> str:
    return "Recorded run ID, code and config versions, and every input/output hash in run_manifest.json"


INPUT, UNDERSTAND, NOTES, EXTRACT, SEARCH, REVIEW, PUBLISH, VERIFY = (
    "Phase 1 · Input and adapters",
    "Phase 2 · Understand the document",
    "Phase 3 · Footnotes and citations",
    "Phase 4 · Knowledge extraction",
    "Phase 5 · Search",
    "Phase 6 · Validation and human review",
    "Phase 7 · Store and publish",
    "Phase 8 · Integrity and reproducibility",
)

STORIES: dict[str, StepStory] = {
    "ingest": StepStory(INPUT, "Ingest", "Reading the book JSON and locating the PDF scan", _ingest),
    "adapt": StepStory(
        INPUT, "Adapter", "Choosing the source adapter and building the canonical book", _adapt
    ),
    "integrity_register": StepStory(
        INPUT,
        "Protect originals",
        "Storing the original files read-only and hashing them",
        _integrity_register,
    ),
    "document_analysis": StepStory(
        UNDERSTAND,
        "Document analysis",
        "Counting pages, blocks and footnotes; checking quality",
        _document_analysis,
    ),
    "structure": StepStory(UNDERSTAND, "Structure", "Building sections and the page index", _structure),
    "origin": StepStory(
        UNDERSTAND, "Origin", "Separating author text, isnad, editor text and editor footnotes", _origin
    ),
    "metadata": StepStory(
        UNDERSTAND, "Metadata", "Extracting title, author, editor and publisher", _metadata
    ),
    "genre": StepStory(
        UNDERSTAND, "Genre routing", "Classifying the genre to pick the right extractor", _genre
    ),
    "annotations": StepStory(NOTES, "Footnotes", "Linking footnote markers to footnote text", _annotations),
    "citations": StepStory(
        NOTES, "Citations", "Finding cited works and internal cross-references", _citations
    ),
    "related_works": StepStory(
        NOTES, "Related works", "Resolving cited works against known titles", _related_works
    ),
    "units": StepStory(
        EXTRACT, "Knowledge units", "Splitting the book into entries and extracting facts", _units
    ),
    "entities": StepStory(EXTRACT, "Entities", "Recognising people and merging aliases", _entities),
    "relations": StepStory(
        EXTRACT, "Relationships", "Extracting family relationships with evidence", _relations
    ),
    "search_index": StepStory(
        SEARCH, "Search index", "Building the normalized Arabic search index", _search_index
    ),
    "validate": StepStory(
        REVIEW, "Validation", "Verifying every quote against the source and scoring confidence", _validate
    ),
    "review_queue": StepStory(
        REVIEW, "Review queue", "Routing uncertain and sensitive items to reviewers", _review_queue
    ),
    "store": StepStory(PUBLISH, "Store", "Writing the enrichment layer to the database", _store),
    "export": StepStory(PUBLISH, "Export", "Writing enrichment.json and the knowledge graph", _export),
    "integrity_verify": StepStory(
        VERIFY, "Integrity check", "Re-checking originals and every source anchor", _integrity_verify
    ),
    "manifest": StepStory(VERIFY, "Manifest", "Writing the run manifest for reproducibility", _manifest),
}


def summarize(step: str, ctx: RunContext, record: StepRecord) -> str:
    """What the step found, from its own result; the status when the result has no such data."""
    try:
        return STORIES[step].summary(ctx)
    except Exception:  # narration must never break a run
        return record.status


class Narrator:
    """A `StepListener` that writes one header per phase and two lines per step."""

    def __init__(self, write: Callable[[str], None]) -> None:
        self.write = write
        self.phase: str | None = None

    def started(self, index: int, total: int, step: Step, ctx: RunContext) -> None:
        story = STORIES.get(step.name)
        if story is None:
            return
        if story.phase != self.phase:
            self.phase = story.phase
            self.write(f"\n━━ {story.phase} ━━")
        self.write(f"Pipeline_{index:02d}/{total} ▶ {story.title}: {story.doing}...")

    def finished(
        self, index: int, total: int, step: Step, ctx: RunContext, record: StepRecord, next_step: str | None
    ) -> None:
        story = STORIES.get(step.name)
        if story is None:
            return
        if record.status == "failed":
            self.write(f"Pipeline_{index:02d}/{total} ✗ {story.title} failed.")
            return
        summary = summarize(step.name, ctx, record)
        mark = "✓" if record.status == "ran" else "↺"
        cached = " (from cache)" if record.status == "cached" else ""
        moving = f" Moving to {STORIES[next_step].title} →" if next_step in STORIES else " Done."
        self.write(
            f"Pipeline_{index:02d}/{total} {mark} {summary}{cached} [{record.duration_ms} ms].{moving}"
        )
