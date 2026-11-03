"""Knowledge units of biography books (step `units`): entry detection (T-070) and assembly (T-071).

An entry starts at each match of `config.entries.regex` ("N - ") in `author_text` blocks from
`config.entries.start_page` and ends before the next match or at the end of its block; when its block
holds no later match, it continues through the following author-text blocks (footnotes are skipped)
until the next heading or match. The numbering must run 1..N: before a gap is reported, a looser
pattern re-scans the author's text (the naive pattern once missed #32, which is mid-sentence).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ilm_engine.canonical.models import Block, CanonicalBook
from ilm_engine.config import Config
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import Anchor, Annotation, Fact, Issue, KnowledgeUnit, Origin, Provenance
from ilm_engine.extractors.genres.biography import UnitSchema as BiographyUnit
from ilm_engine.ids import make_id, natural_key
from ilm_engine.nlp.arabic_digits import to_int, words_to_int
from ilm_engine.nlp.nasab import parse_name
from ilm_engine.nlp.normalize import normalize_with_map
from ilm_engine.processors.structure import Structure
from ilm_engine.validation.confidence import decide, score

STEP = "units"
FALLBACK_REGEX = re.compile(r"([٠-٩]+)\s*[-–]\s*")


@dataclass
class Entry:
    entry_no: int
    anchors: list[Anchor]  # the entry's own text spans, in reading order
    found_by: str = "regex"  # regex | fallback

    @property
    def block_id(self) -> str:
        return self.anchors[0].block_id


def unit_id(pub_ref: str, entry: Entry) -> str:
    """Knowledge-unit ID of an entry: `ku` + `entry_no|block_id|start` (ADR-011)."""
    first = entry.anchors[0]
    return make_id("ku", pub_ref, natural_key(entry.entry_no, first.block_id, first.start))


@dataclass
class EntryDetection:
    entries: list[Entry]
    issues: list[Issue] = field(default_factory=list)

    def by_number(self) -> dict[int, Entry]:
        return {entry.entry_no: entry for entry in self.entries}


def _anchor(
    book: CanonicalBook, block: Block, start: int, end: int, scan_pages: dict[tuple[int, int], int]
) -> Anchor:
    text = block.text
    while end > start and text[end - 1].isspace():
        end -= 1
    return Anchor(
        pub_ref=book.book.pub_ref,
        page=block.page,
        scan_page=scan_pages[(block.volume, block.page)],
        block_id=block.block_id,
        start=start,
        end=end,
        quote=text[start:end],
        block_hash=block.block_hash,
    )


def detect_entries(book: CanonicalBook, origins: dict[str, Origin], config: Config) -> EntryDetection:
    pattern = re.compile(config.entries.regex)
    scan_pages = {(page.volume, page.n): page.scan_page for page in book.pages}
    blocks = [
        block
        for block in book.blocks_in_order()
        if block.page >= config.entries.start_page and block.kind in ("text", "heading")
    ]
    author = [block for block in blocks if origins.get(block.block_id) == "author_text"]
    matches = {block.block_id: list(pattern.finditer(block.text)) for block in author if block.kind == "text"}

    entries: list[Entry] = []
    for position, block in enumerate(author):
        found = matches.get(block.block_id, [])
        for index, match in enumerate(found):
            end = found[index + 1].start() if index + 1 < len(found) else len(block.text)
            anchors = [_anchor(book, block, match.start(), end, scan_pages)]
            if index + 1 == len(found):  # the last entry of the block may continue in the next blocks
                for following in author[position + 1 :]:
                    if following.kind == "heading" or matches.get(following.block_id):
                        break
                    anchors.append(_anchor(book, following, 0, len(following.text), scan_pages))
            entries.append(Entry(to_int(match.group(1)), anchors))

    issues = _check_numbering(book, entries, author, scan_pages)
    entries.sort(key=lambda entry: (entry.entry_no, book.block(entry.block_id).order, entry.anchors[0].start))
    return EntryDetection(entries, issues)


def _check_numbering(
    book: CanonicalBook, entries: list[Entry], author: list[Block], scan_pages: dict[tuple[int, int], int]
) -> list[Issue]:
    pub_ref = book.book.pub_ref
    issues: list[Issue] = []
    numbers = [entry.entry_no for entry in entries]
    for number in sorted({n for n in numbers if numbers.count(n) > 1}):
        blocks = [entry.block_id for entry in entries if entry.entry_no == number]
        issues.append(
            make_issue(
                pub_ref,
                "numbering_duplicate",
                "warning",
                "book",
                pub_ref,
                f"Entry number {number} occurs {len(blocks)} times.",
                STEP,
                details={"entry_no": number, "blocks": blocks},
                key=str(number),
            )
        )
    if not numbers:
        return issues
    known = set(numbers)
    for number in range(1, max(numbers) + 1):
        if number in known:
            continue
        rescued = _fallback(book, number, author, scan_pages)
        if rescued is not None:
            entries.append(rescued)
            continue
        issues.append(
            make_issue(
                pub_ref,
                "numbering_gap",
                "warning",
                "book",
                pub_ref,
                f"No entry numbered {number} (also not found by the fallback pattern).",
                STEP,
                details={"entry_no": number},
                key=str(number),
            )
        )
    return issues


def _fallback(
    book: CanonicalBook, number: int, author: list[Block], scan_pages: dict[tuple[int, int], int]
) -> Entry | None:
    """A looser re-scan for one missing entry number (no lookbehind, dash variants)."""
    for block in author:
        for match in FALLBACK_REGEX.finditer(block.text):
            if to_int(match.group(1)) == number:
                return Entry(
                    number, [_anchor(book, block, match.start(), len(block.text), scan_pages)], "fallback"
                )
    return None


# --- Unit assembly (T-071) -------------------------------------------------------------------------------


def _in_unit(anchor: Anchor, spans: list[Anchor]) -> bool:
    return any(anchor.block_id == span.block_id and span.start <= anchor.start < span.end for span in spans)


def assemble_units(
    book: CanonicalBook,
    detection: EntryDetection,
    annotations: list[Annotation],
    structure: Structure,
    config: Config,
    genre: str = "biography",
    sub_type: str | None = "ansab",
) -> tuple[list[KnowledgeUnit], list[Issue]]:
    """One `biographical_entry` unit per detected entry, with its notes, section and parsed person."""
    pub_ref = book.book.pub_ref
    confidence = score(config, "rule").score
    units: list[KnowledgeUnit] = []
    issues: list[Issue] = list(detection.issues)
    for entry in detection.entries:
        identifier = unit_id(pub_ref, entry)
        first = entry.anchors[0]
        notes = sorted(
            (
                a
                for a in annotations
                if a.type != "nested_footnote" and _in_unit(a.marker_anchor, entry.anchors)
            ),
            key=lambda a: (not a.is_entry_note, book.block(a.source_block_id).order, a.marker_anchor.start),
        )
        entry_note = next(
            (a for a in notes if a.is_entry_note and a.marker_anchor.start == first.start), None
        )
        unit_issues = []
        if entry_note is None:
            issue = make_issue(
                pub_ref,
                "entry_without_footnote",
                "info",
                "unit",
                identifier,
                f"Entry {entry.entry_no} ({first.block_id}) has no entry-level footnote.",
                STEP,
                details={"entry_no": entry.entry_no},
                anchors=[first],
            )
            issues.append(issue)
            unit_issues.append(issue.issue_id)

        block_text = book.block(first.block_id).text
        number = re.match(r"\s*[٠-٩0-9]+\s*-\s*", block_text[first.start : first.end])
        name_start = first.start + (number.end() if number else 0)
        name = parse_name(block_text[name_start : first.end], offset=name_start)
        section_id = structure.block_section_id(first.block_id)
        heading = structure.section(section_id).heading_block_id
        person = (
            {
                "surface": name.raw,
                "span": list(name.span),
                "ism": name.ism,
                "kunya": name.kunya,
                "laqab": name.laqab,
                "nisba": list(name.nisba),
                "gender": name.gender,
            }
            if name
            else {"surface": "", "gender": "unknown"}
        )
        payload = BiographyUnit.model_validate(
            {
                "entry_no": entry.entry_no,
                "person": person,
                "nasab": list(name.chain) if name else [],
                "kunya": name.kunya if name else None,
                "laqab": name.laqab if name else None,
                "section_heading_block": heading,
                "tarjama_annotation": entry_note.target_block_ids[0]
                if entry_note and entry_note.target_block_ids
                else None,
            }
        )
        units.append(
            KnowledgeUnit(
                unit_id=identifier,
                genre=genre,  # type: ignore[arg-type]
                sub_type=sub_type,
                unit_type="biographical_entry",
                entry_no=entry.entry_no,
                section_id=section_id,
                anchors=entry.anchors,
                note_annotation_ids=[a.annotation_id for a in notes],
                subject_entity_id=None,  # linked by the entities step (T-080)
                payload=payload.model_dump(mode="json", exclude_none=True),
                facts=[],
                origin="author_text",
                confidence=confidence,
                review_status=decide(config, confidence),
                issues=unit_issues,
                provenance=Provenance(method="rule", step=STEP, step_version="1.0.0"),
            )
        )
    return units, issues


# --- Rule-based unit facts (T-072) -----------------------------------------------------------------------

# (predicate, value or None for a computed value, pattern on the `match`-normalized text)
_B, _E = r"(?<![\u0621-\u064a])", r"(?![\u0621-\u064a])"  # word boundaries for Arabic letters
FACT_RULES: list[tuple[str, Any, re.Pattern[str]]] = [
    ("converted_to_islam", True, re.compile(_B + r"[وف]?اسلم(?:ت)?" + _E)),
    ("married", True, re.compile(_B + r"[وف]?تزوج(?:ت|ها|هم)?" + _E)),
    ("has_narration", False, re.compile(_B + r"و?لم يرو عن(?:ه|ها|هما|هم) شي?ء")),
    ("is_sahabi", False, re.compile(_B + r"و?لا صحبة له" + _E)),
    ("is_sahabi", True, re.compile(_B + r"و?له صحبة" + _E)),
    # Only a place ("بالطائف") or a time phrase ("في شهر ربيع الأول") may stand between the verb and the
    # year, so "ومات أبو سفيان بن الحارث سنة عشرين" (another person's death) is not this entry's fact.
    ("death_hijri", None, re.compile(_B + r"[وف]?(?:مات|توفي)(?: ب\S+| في(?: \S+){1,3})? سنة [^.،()]+")),
]
_YEAR = re.compile(r"سنة (?P<year>.+)$")


def _fact_value(predicate: str, value: Any, matched: str) -> Any:
    if value is not None:
        return value
    year = _YEAR.search(matched)
    if year is None:
        return None
    digits = re.search(r"[٠-٩0-9]+", year.group("year"))
    try:
        return to_int(digits.group(0)) if digits else words_to_int(year.group("year"))
    except ValueError:
        return None


def rule_facts(
    book: CanonicalBook, unit: KnowledgeUnit, origins: dict[str, Origin], config: Config
) -> list[Fact]:
    """Facts the entry's own text states, matched on normalized text and anchored on the original."""
    confidence = score(config, "rule").score
    facts: list[Fact] = []
    seen: set[tuple[str, str, int]] = set()
    for span in unit.anchors:
        block = book.block(span.block_id)
        normalized = normalize_with_map(block.text, "match")
        lo = next(
            (i for i, start in enumerate(normalized.starts) if start >= span.start), len(normalized.text)
        )
        hi = next((i for i, start in enumerate(normalized.starts) if start >= span.end), len(normalized.text))
        for predicate, value, pattern in FACT_RULES:
            for match in pattern.finditer(normalized.text, lo, hi):
                start, end = normalized.to_original(match.start(), match.end())
                while end > start and block.text[end - 1].isspace():
                    end -= 1
                if (predicate, block.block_id, start) in seen or any(
                    f.predicate == predicate
                    and f.evidence[0].block_id == block.block_id
                    and f.evidence[0].start <= start < f.evidence[0].end
                    for f in facts
                ):
                    continue
                fact_value = _fact_value(predicate, value, match.group(0))
                if fact_value is None:
                    continue
                seen.add((predicate, block.block_id, start))
                anchor = Anchor(
                    pub_ref=span.pub_ref,
                    page=block.page,
                    scan_page=span.scan_page,
                    block_id=block.block_id,
                    start=start,
                    end=end,
                    quote=block.text[start:end],
                    block_hash=block.block_hash,
                )
                facts.append(
                    Fact(
                        fact_id=f"{unit.unit_id}#f{len(facts) + 1}",
                        predicate=predicate,
                        object=fact_value,
                        evidence=[anchor],
                        origin=origins.get(block.block_id, unit.origin),
                        assertion="stated",
                        confidence=confidence,
                        review_status=decide(config, confidence),
                        provenance=Provenance(method="rule", step=STEP, step_version="1.0.0"),
                    )
                )
    return sorted(facts, key=lambda f: (book.block(f.evidence[0].block_id).order, f.evidence[0].start))


def with_rule_facts(
    book: CanonicalBook, units: list[KnowledgeUnit], origins: dict[str, Origin], config: Config
) -> list[KnowledgeUnit]:
    updated = []
    for unit in units:
        facts = rule_facts(book, unit, origins, config)
        renumbered = [
            fact.model_copy(update={"fact_id": f"{unit.unit_id}#f{i}"}) for i, fact in enumerate(facts, 1)
        ]
        updated.append(unit.model_copy(update={"facts": renumbered}))
    return updated


def with_llm_facts(
    book: CanonicalBook,
    units: list[KnowledgeUnit],
    annotations: dict[str, Annotation],
    origins: dict[str, Origin],
    structure: Structure,
    config: Config,
    gateway: Any,
    verifier: Any = None,
) -> tuple[list[KnowledgeUnit], list[Issue], dict[str, list[dict[str, Any]]]]:
    """Add evidenced LLM facts (T-094, consensus T-102) for predicates the rules did not state.

    Returns the units, the issues, and per-fact model outputs (for review items).
    """
    from ilm_engine.extractors.llm_extract import UnitInput, extract_unit_facts
    from ilm_engine.validation.consensus import reconcile

    scan_pages = {block_id: book.page(b.page, b.volume).scan_page for block_id, b in book.blocks.items()}
    updated: list[KnowledgeUnit] = []
    issues: list[Issue] = []
    outputs: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        footnotes = [
            book.block(target)
            for annotation_id in unit.note_annotation_ids
            for target in annotations[annotation_id].target_block_ids
        ]
        heading_id = structure.section(unit.section_id).heading_block_id
        unit_input = UnitInput(
            unit_id=unit.unit_id,
            pub_ref=book.book.pub_ref,
            entry=[book.block(anchor.block_id) for anchor in unit.anchors],
            footnotes=footnotes,
            heading=book.block(heading_id) if heading_id else None,
        )
        outcome = extract_unit_facts(gateway, unit_input, config, origins, scan_pages, verifier=verifier)
        issues += outcome.issues
        if outcome.result is None or outcome.result.output is None:
            updated.append(unit)
            continue
        consensus = reconcile(outcome.facts, outcome.result, outcome.verifier, unit_input, config, scan_pages)
        issues += consensus.issues
        known = {fact.predicate for fact in unit.facts}
        facts = list(unit.facts)
        for item in consensus.facts:
            if item.fact.predicate in known:
                continue
            fact_id = f"{unit.unit_id}#f{len(facts) + 1}"
            facts.append(item.fact.model_copy(update={"fact_id": fact_id}))
            outputs[fact_id] = item.model_outputs
        updated.append(unit.model_copy(update={"facts": facts}))
    return updated, issues, outputs
