"""Citations (step `citations`, FR-062, ADR-018): works the editor's footnotes cite.

A citation is a quoted title ("…" or «…») in a footnote, optionally followed by locators — `(vol/ page)`,
`(page)`, `(ص: n)`, `(رقم: n)` — and an author hint ("للمصنّف", "لابن ماكولا"). Titles are resolved to
`Work` records through `config/works_aliases.yaml`; a short title that may mean several works stays
unresolved (`ambiguous_entity`), an unknown title becomes a stub work for review, and quoted words that
are not books ("الأصل" = the manuscript) are skipped.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from ilm_engine.canonical.models import Block, CanonicalBook
from ilm_engine.config import DEFAULT_CONFIG_DIR, Config
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import Anchor, Citation, Issue, Locator, Origin, Provenance, Work
from ilm_engine.ids import make_id
from ilm_engine.nlp.arabic_digits import to_int
from ilm_engine.nlp.normalize import normalize
from ilm_engine.validation.confidence import score

STEP = "citations"
LIBRARY = "library"  # work IDs are library-wide, not per book
_PROVENANCE = Provenance(method="rule", step=STEP, step_version="1.0.0")

_TITLE = re.compile(r'["«“](?P<title>[^"»”\n]{1,80})["»”]')
_LOCATOR = re.compile(
    r"[،,:]?\s*\(\s*(?:"
    r"(?P<vol>[٠-٩0-9]+)\s*/\s*(?P<page>[٠-٩0-9]+)"
    r"|ص:\s*(?P<page_label>[٠-٩0-9]+)"
    r"|رقم:\s*(?P<number>[٠-٩0-9]+)"
    r"|(?P<single>[٠-٩0-9]+)"
    r")\s*\)"
)
_AUTHOR_HINT = re.compile(
    r"[،,]?\s*(للمصن[ّ]?ف|لابن\s+[^\s،.(]+|لأبي\s+[^\s،.(]+(?:\s+[^\s،.(]+)?|للحافظ\s+[^\s،.(]+)"
)
_MARKER = re.compile(r"\s*\((?:[٠-٩0-9]+|[ء-ي])\)\s*")


class _WorkEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    author: str | None = None
    aliases: list[str] = []


class WorksAliases(BaseModel):
    model_config = ConfigDict(extra="forbid")
    works: list[_WorkEntry] = []
    ambiguous: dict[str, list[str]] = {}
    not_works: list[str] = []
    this_book: list[str] = []


def load_aliases(path: Path | None = None) -> WorksAliases:
    path = path or DEFAULT_CONFIG_DIR / "works_aliases.yaml"
    return WorksAliases.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def title_key(title: str) -> str:
    """Comparable title: footnote markers removed, normalized (ADR-012)."""
    return normalize(_MARKER.sub(" ", title))


def work_id(title: str) -> str:
    return make_id("wrk", LIBRARY, title_key(title))


@dataclass
class Catalog:
    """Resolution of cited titles against the alias table, plus works created on the way."""

    aliases: WorksAliases
    book: CanonicalBook
    works: dict[str, Work] = field(default_factory=dict)
    by_key: dict[str, str] = field(default_factory=dict)  # normalized alias → canonical title
    ambiguous: dict[str, list[str]] = field(default_factory=dict)
    skip: set[str] = field(default_factory=set)
    self_titles: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        for entry in self.aliases.works:
            for name in [entry.title, *entry.aliases]:
                self.by_key[title_key(name)] = entry.title
        self.ambiguous = {title_key(name): candidates for name, candidates in self.aliases.ambiguous.items()}
        self.skip = {title_key(name) for name in self.aliases.not_works}
        own = [self.book.metadata.title_as_source or "", *self.aliases.this_book]
        self.self_titles = {title_key(name) for name in own if name}

    def this_book(self) -> Work:
        title = self.book.metadata.title_as_source or self.book.book.pub_ref
        return self._work(title, self.book.metadata.author_name, "this_book", self.book.book.source_work_id)

    def _work(
        self,
        title: str,
        author: str | None,
        status: str,
        source_id: str | None = None,
        alias: str | None = None,
    ) -> Work:
        identifier = work_id(title)
        existing = self.works.get(identifier)
        aliases = sorted(
            {*(existing.aliases if existing else []), *([alias] if alias and alias != title else [])}
        )
        work = Work(
            work_id=identifier,
            source_work_id=source_id or (existing.source_work_id if existing else None),
            title=title,
            title_normalized=title_key(title),
            aliases=aliases,
            author_name=author or (existing.author_name if existing else None),
            author_entity_id=None,
            status=status,  # type: ignore[arg-type]
        )
        self.works[identifier] = work
        return work

    def resolve(self, raw: str) -> tuple[Work | None, str, list[str]]:
        """(work, resolution, ambiguous candidates) for a cited title."""
        key = title_key(raw)
        if key in self.self_titles:
            return self.this_book(), "alias_table", []
        if key in self.ambiguous:
            return None, "unresolved", self.ambiguous[key]
        if key in self.by_key:
            canonical = self.by_key[key]
            entry = next(item for item in self.aliases.works if item.title == canonical)
            return self._work(canonical, entry.author, "catalog", alias=raw), "alias_table", []
        return self._work(raw, None, "stub"), "unresolved", []


@dataclass
class Citations:
    citations: list[Citation]
    works: list[Work]
    issues: list[Issue] = field(default_factory=list)

    def counts_by_title(self) -> dict[str, int]:
        return dict(sorted(Counter(citation.title_raw for citation in self.citations).items()))

    def counts_by_work(self) -> dict[str, int]:
        return dict(sorted(Counter(c.work_id for c in self.citations if c.work_id).items()))

    def to_json(self) -> dict[str, Any]:
        return {
            "citations": self.citations,
            "counts_by_title": self.counts_by_title(),
            "counts_by_work": self.counts_by_work(),
        }


def _locators(text: str, position: int) -> tuple[list[Locator], int]:
    locators = []
    while match := _LOCATOR.match(text, position):
        found = match.groupdict()
        locators.append(
            Locator(
                raw=match.group(0).lstrip("،,: "),
                volume=to_int(found["vol"]) if found["vol"] else None,
                page=to_int(found["page"] or found["single"]) if found["page"] or found["single"] else None,
                number=to_int(found["number"]) if found["number"] else None,
                page_label=found["page_label"],
            )
        )
        position = match.end()
    return locators, position


def extract(
    book: CanonicalBook, origins: dict[str, Origin], config: Config, aliases: WorksAliases | None = None
) -> Citations:
    catalog = Catalog(aliases or load_aliases(), book)
    catalog.this_book()
    pub_ref = book.book.pub_ref
    scan_pages = {(page.volume, page.n): page.scan_page for page in book.pages}
    rule = score(config, "rule").score
    citations: list[Citation] = []
    issues: list[Issue] = []
    for block in book.blocks_in_order():
        if block.kind != "footnote":
            continue
        for match in _TITLE.finditer(block.text):
            raw = match.group("title").strip()
            if title_key(raw) in catalog.skip or not title_key(raw):
                continue
            locators, end = _locators(block.text, match.end())
            hint = _AUTHOR_HINT.match(block.text, end)
            work, resolution, candidates = catalog.resolve(raw)
            start = match.start("title") + (len(match.group("title")) - len(match.group("title").lstrip()))
            anchor = _anchor(block, start, start + len(raw), pub_ref, scan_pages)
            citation = Citation(
                citation_id=make_id("cit", pub_ref, f"{block.block_id}|{start}|{title_key(raw)}"),
                title_raw=raw,
                title_normalized=title_key(raw),
                work_id=work.work_id if work else None,
                author_hint=hint.group(1) if hint else None,
                locators=locators,
                anchor=anchor,
                context="footnote",
                origin=origins.get(block.block_id, "editor_footnote"),
                resolution=resolution,  # type: ignore[arg-type]
                confidence=rule if resolution == "alias_table" else score(config, "llm").score,
                provenance=_PROVENANCE,
            )
            citations.append(citation)
            if candidates:
                issues.append(
                    make_issue(
                        pub_ref,
                        "ambiguous_entity",
                        "warning",
                        "citation",
                        citation.citation_id,
                        f"Cited title {raw!r} may mean {' or '.join(candidates)}; left for review.",
                        STEP,
                        details={"title": raw, "candidates": candidates},
                        anchors=[anchor],
                    )
                )
    return Citations(citations, sorted(catalog.works.values(), key=lambda w: w.work_id), issues)


def _anchor(
    block: Block, start: int, end: int, pub_ref: str, scan_pages: dict[tuple[int, int], int]
) -> Anchor:
    return Anchor(
        pub_ref=pub_ref,
        page=block.page,
        scan_page=scan_pages[(block.volume, block.page)],
        block_id=block.block_id,
        start=start,
        end=end,
        quote=block.text[start:end],
        block_hash=block.block_hash,
    )
