"""Structure (step `structure`): the section tree of a book from its headings (02-architecture L4).

Every `toc_heading` and `heading` block opens a section. `toc_heading` sections are level 1; a heading
takes the depth of the TOC entry on its source page (`Page.source_key == TocEntry.source_page_key`),
else level 2. A section runs from its heading to the block before the next heading of the same or a
higher level, and all sections hang under one root section for the book. Each block belongs to exactly
one deepest section.

TOC alignment (T-033): a TOC entry matches a heading on the page whose Shamela key equals the entry's
`source_page` (not the printed page number), confirmed by normalized title similarity.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher

from ilm_engine.canonical.models import Block, CanonicalBook, TocEntry
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import Issue, Origin, Provenance, Section
from ilm_engine.ids import make_id, natural_key
from ilm_engine.nlp.normalize import normalize

STEP = "structure"
STEP_VERSION = "1.0.0"
AUTHOR_INTRO_TITLE = "مقدمة المؤلف"
_PROVENANCE = Provenance(method="structural", step=STEP, step_version=STEP_VERSION)
MIN_TITLE_SIMILARITY = 0.6
_MARKER = re.compile(r"\((?:[٠-٩0-9]+|[\u0621-\u064a])\)")
_DECORATION = re.compile(r"[*\[\]:.؛،]")


def title_key(text: str) -> str:
    """Heading/TOC title for comparison: footnote markers, '*', brackets and punctuation removed."""
    return normalize(_DECORATION.sub(" ", _MARKER.sub(" ", text)))


def title_similarity(a: str, b: str) -> float:
    left, right = title_key(a), title_key(b)
    if not left or not right:
        return 0.0
    if left in right or right in left:
        return 1.0
    return round(SequenceMatcher(None, left, right).ratio(), 3)


@dataclass(frozen=True)
class TocAlignment:
    toc_index: int
    title: str
    source_page_key: str
    printed_page: int | None
    offset: int | None  # printed page n - source page key
    heading_block_id: str | None
    similarity: float


@dataclass
class Structure:
    root_section_id: str
    sections: list[Section]  # root first, then document order
    block_section: dict[str, str]  # block_id → deepest section_id
    issues: list[Issue] = field(default_factory=list)
    toc_alignment: list[TocAlignment] = field(default_factory=list)
    page_offsets: list[int] = field(default_factory=list)  # distinct n - source key over all pages

    def section(self, section_id: str) -> Section:
        for section in self.sections:
            if section.section_id == section_id:
                return section
        raise KeyError(f"unknown section {section_id!r}")

    def to_json(self) -> dict[str, object]:
        return {
            "root_section_id": self.root_section_id,
            "sections": self.sections,
            "toc_alignment": [asdict(item) for item in self.toc_alignment],
            "page_offsets": self.page_offsets,
        }


@dataclass
class _Open:
    heading: Block
    level: int
    toc: TocEntry | None
    start: int  # index into reading order
    end: int = -1
    children: list[int] = field(default_factory=list)
    parent: int | None = None


def align_toc(book: CanonicalBook) -> tuple[dict[str, TocEntry], list[TocAlignment], list[Issue]]:
    """Match TOC entries to heading blocks: same source page key, confirmed by title similarity.

    Returns heading block → TOC entry, one alignment row per TOC entry, and the alignment issues.
    """
    pub_ref = book.book.pub_ref
    pages_by_key = {page.source_key: page for page in book.pages}
    headings_by_key: dict[str, list[Block]] = {}
    for block in book.blocks_in_order():
        if block.kind in ("heading", "toc_heading"):
            key = next(
                page.source_key for page in book.pages if (page.volume, page.n) == (block.volume, block.page)
            )
            headings_by_key.setdefault(key, []).append(block)

    matched: dict[str, TocEntry] = {}
    rows: list[TocAlignment] = []
    issues: list[Issue] = []
    for entry in book.metadata.toc:
        page = pages_by_key.get(entry.source_page_key)
        scored = [
            (title_similarity(entry.title, block.text), block)
            for block in headings_by_key.get(entry.source_page_key, [])
            if block.block_id not in matched
        ]
        best = max(scored, key=lambda item: item[0], default=(0.0, None))
        heading = best[1] if best[0] >= MIN_TITLE_SIMILARITY else None
        if heading is not None:
            matched[heading.block_id] = entry
        rows.append(
            TocAlignment(
                toc_index=entry.index,
                title=entry.title,
                source_page_key=entry.source_page_key,
                printed_page=page.n if page else None,
                offset=page.n - int(entry.source_page_key)
                if page and entry.source_page_key.isdigit()
                else None,
                heading_block_id=heading.block_id if heading else None,
                similarity=best[0],
            )
        )
        if heading is not None and heading.kind == "toc_heading":
            issues.append(
                make_issue(
                    pub_ref,
                    "toc_without_block",
                    "info",
                    "section",
                    heading.block_id,
                    f"TOC entry {entry.title!r} has no heading heading on page {heading.page}; "
                    "the source placed it as a toc_heading at the top of the page.",
                    STEP,
                    details={
                        "toc_index": entry.index,
                        "page": heading.page,
                        "source_page_key": entry.source_page_key,
                    },
                )
            )
        elif heading is None:
            issues.append(
                make_issue(
                    pub_ref,
                    "toc_without_block",
                    "warning",
                    "book",
                    pub_ref,
                    f"TOC entry {entry.title!r} (source page {entry.source_page_key}) matches no heading.",
                    STEP,
                    details={"toc_index": entry.index, "source_page_key": entry.source_page_key},
                    key=str(entry.index),
                )
            )
    for blocks in headings_by_key.values():
        for block in blocks:
            if block.block_id not in matched:
                issues.append(
                    make_issue(
                        pub_ref,
                        "heading_without_toc",
                        "info",
                        "block",
                        block.block_id,
                        f"Heading on page {block.page} has no TOC entry.",
                        STEP,
                        details={"page": block.page},
                    )
                )
    offsets = sorted({row.offset for row in rows if row.offset is not None})
    if len(offsets) > 1:
        issues.append(
            make_issue(
                pub_ref,
                "toc_page_offset",
                "info",
                "book",
                pub_ref,
                f"TOC source pages differ from printed pages by {', '.join(map(str, offsets))}; "
                "aligned through the source page key, not the page number.",
                STEP,
                details={"offsets": offsets, "by_toc_index": {row.toc_index: row.offset for row in rows}},
            )
        )
    return matched, rows, issues


def build(book: CanonicalBook) -> Structure:
    pub_ref = book.book.pub_ref
    blocks = book.blocks_in_order()
    toc_of, alignment, issues = align_toc(book)

    opened: list[_Open] = []
    for index, block in enumerate(blocks):
        if block.kind not in ("heading", "toc_heading"):
            continue
        toc = toc_of.get(block.block_id)
        level = 1 if block.kind == "toc_heading" else (toc.depth if toc else 2)
        opened.append(_Open(block, level, toc, index))

    # A section ends before the next heading of the same or a higher level; the parent is the nearest
    # preceding section of a lower level.
    for position, section in enumerate(opened):
        following = next((s.start for s in opened[position + 1 :] if s.level <= section.level), len(blocks))
        section.end = following - 1
        for earlier in range(position - 1, -1, -1):
            if opened[earlier].level < section.level:
                section.parent = earlier
                opened[earlier].children.append(position)
                break

    root_id = make_id("sec", pub_ref, natural_key("root", blocks[0].block_id))
    ids = [
        make_id("sec", pub_ref, natural_key(s.toc.index if s.toc else "h", s.heading.block_id))
        for s in opened
    ]
    intro = next((i for i, s in enumerate(opened) if s.heading.text.strip() == AUTHOR_INTRO_TITLE), None)

    def provisional_origin(position: int) -> Origin:
        # Refined per block by the origin step (T-034); the editor's part precedes the author's intro.
        return "editor_text" if intro is not None and position < intro else "author_text"

    sections = [
        Section(
            section_id=root_id,
            title=book.metadata.title_as_source or book.book.pub_ref,
            level=0,
            heading_block_id=None,
            toc_index=None,
            toc_source_page_key=None,
            start_block_id=blocks[0].block_id,
            end_block_id=blocks[-1].block_id,
            start_page=blocks[0].page,
            end_page=blocks[-1].page,
            parent_id=None,
            children=[ids[i] for i, s in enumerate(opened) if s.parent is None],
            origin="author_text",
            provenance=_PROVENANCE,
        )
    ]
    for position, section in enumerate(opened):
        sections.append(
            Section(
                section_id=ids[position],
                title=section.heading.text,
                level=section.level,
                heading_block_id=section.heading.block_id,
                toc_index=section.toc.index if section.toc else None,
                toc_source_page_key=section.toc.source_page_key if section.toc else None,
                start_block_id=section.heading.block_id,
                end_block_id=blocks[section.end].block_id,
                start_page=section.heading.page,
                end_page=blocks[section.end].page,
                parent_id=ids[section.parent] if section.parent is not None else root_id,
                children=[ids[child] for child in section.children],
                origin=provisional_origin(position),
                provenance=_PROVENANCE,
            )
        )

    block_section = {block.block_id: root_id for block in blocks}
    for position, section in sorted(enumerate(opened), key=lambda item: item[1].level):
        for index in range(section.start, section.end + 1):
            block_section[blocks[index].block_id] = ids[position]  # deeper levels overwrite shallower
    page_offsets = sorted({page.n - int(page.source_key) for page in book.pages if page.source_key.isdigit()})
    return Structure(root_id, sections, block_section, issues, alignment, page_offsets)
