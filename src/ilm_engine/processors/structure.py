"""Structure (step `structure`): the section tree of a book from its headings (02-architecture L4).

Every `toc_heading` and `heading` block opens a section. `toc_heading` sections are level 1; a heading
takes the depth of the TOC entry on its source page (`Page.source_key == TocEntry.source_page_key`),
else level 2. A section runs from its heading to the block before the next heading of the same or a
higher level, and all sections hang under one root section for the book. Each block belongs to exactly
one deepest section.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ilm_engine.canonical.models import Block, CanonicalBook, TocEntry
from ilm_engine.enrichment.models import Issue, Origin, Provenance, Section
from ilm_engine.ids import make_id, natural_key

STEP = "structure"
STEP_VERSION = "1.0.0"
AUTHOR_INTRO_TITLE = "مقدمة المؤلف"
_PROVENANCE = Provenance(method="structural", step=STEP, step_version=STEP_VERSION)


@dataclass
class Structure:
    root_section_id: str
    sections: list[Section]  # root first, then document order
    block_section: dict[str, str]  # block_id → deepest section_id
    issues: list[Issue] = field(default_factory=list)

    def section(self, section_id: str) -> Section:
        for section in self.sections:
            if section.section_id == section_id:
                return section
        raise KeyError(f"unknown section {section_id!r}")

    def to_json(self) -> dict[str, object]:
        return {"root_section_id": self.root_section_id, "sections": self.sections}


@dataclass
class _Open:
    heading: Block
    level: int
    toc: TocEntry | None
    start: int  # index into reading order
    end: int = -1
    children: list[int] = field(default_factory=list)
    parent: int | None = None


def _toc_by_key(book: CanonicalBook) -> dict[str, list[TocEntry]]:
    entries: dict[str, list[TocEntry]] = {}
    for entry in book.metadata.toc:
        entries.setdefault(entry.source_page_key, []).append(entry)
    return entries


def build(book: CanonicalBook) -> Structure:
    pub_ref = book.book.pub_ref
    blocks = book.blocks_in_order()
    page_key = {(page.volume, page.n): page.source_key for page in book.pages}
    toc_on_page = _toc_by_key(book)
    used: set[int] = set()

    opened: list[_Open] = []
    for index, block in enumerate(blocks):
        if block.kind not in ("heading", "toc_heading"):
            continue
        candidates = [
            entry
            for entry in toc_on_page.get(page_key[(block.volume, block.page)], [])
            if entry.index not in used
        ]
        toc = candidates[0] if candidates else None
        if toc is not None:
            used.add(toc.index)
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
    return Structure(root_id, sections, block_section)
