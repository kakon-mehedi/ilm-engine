"""Person entities (step `entities`, 02-architecture L11).

- One entity per entry subject, named by the nasab parser, with the mention anchored at the name.
- Fixed authorities: the Prophet (`ent_prophet`; aliases رسول الله, النبي, ﷺ), the book's author (from
  the card, with the Shamela author id) and its editor.
An elliptic subject ("٩ - وهند.") has only an ism; its chain and gender come from the group closure in
the relations step (T-082).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.config import Config
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import (
    Anchor,
    BookMetadata,
    Entity,
    Issue,
    KnowledgeUnit,
    PersonName,
    Provenance,
)
from ilm_engine.ids import make_id, natural_key
from ilm_engine.nlp.nasab import display_name, parse_name
from ilm_engine.nlp.normalize import normalize, normalize_with_map
from ilm_engine.validation.confidence import decide, score

STEP = "entities"
PROPHET_ID = "ent_prophet"
PROPHET_ALIASES = ["رسول الله", "النبي", "ﷺ"]
MAX_MENTIONS = 20
_PROVENANCE = Provenance(method="rule", step=STEP, step_version="1.0.0")
_PROPHET = re.compile(r"رسول\s+الل[َّ]*ه|النب[ِيّ]+(?![ء-ي])")


@dataclass
class Entities:
    entities: list[Entity]
    unit_subjects: dict[str, str]  # unit_id → entity_id
    issues: list[Issue] = field(default_factory=list)

    def by_id(self) -> dict[str, Entity]:
        return {entity.entity_id: entity for entity in self.entities}


def entity_id(pub_ref: str, name: str, anchor: Anchor | None) -> str:
    """`ent` + `normalized canonical name|first anchor` (ADR-011)."""
    where = f"{anchor.block_id}:{anchor.start}" if anchor else "none"
    return make_id("ent", pub_ref, natural_key(normalize(name), where))


def _anchor(book: CanonicalBook, block_id: str, start: int, end: int) -> Anchor:
    block = book.block(block_id)
    return Anchor(
        pub_ref=book.book.pub_ref,
        page=block.page,
        scan_page=book.page(block.page, block.volume).scan_page,
        block_id=block_id,
        start=start,
        end=end,
        quote=block.text[start:end],
        block_hash=block.block_hash,
    )


def _person(
    identifier: str,
    name: PersonName,
    gender: str,
    mentions: list[Anchor],
    roles: list[str],
    config: Config,
    **extra: object,
) -> Entity:
    confidence = score(config, "rule").score
    canonical = display_name(name.full_surface)
    return Entity(
        entity_id=identifier,
        entity_type="person",
        canonical_name=canonical,
        canonical_name_normalized=normalize(canonical),
        name=name,
        gender=gender,  # type: ignore[arg-type]
        mentions=mentions,
        roles=roles,  # type: ignore[arg-type]
        confidence=confidence,
        review_status=decide(config, confidence),
        provenance=_PROVENANCE,
        **extra,  # type: ignore[arg-type]
    )


def subject_entities(
    book: CanonicalBook, units: list[KnowledgeUnit], config: Config
) -> tuple[list[Entity], dict[str, str]]:
    entities, subjects = [], {}
    for unit in units:
        person = unit.payload.get("person") or {}
        span = person.get("span")
        if not span:
            continue
        anchor = _anchor(book, unit.anchors[0].block_id, span[0], span[1])
        name = PersonName(
            ism=person.get("ism"),
            kunya=person.get("kunya"),
            laqab=person.get("laqab"),
            nisba=list(person.get("nisba", [])),
            nasab=list(unit.payload.get("nasab", [])),
            full_surface=anchor.quote,
        )
        identifier = entity_id(book.book.pub_ref, name.full_surface, anchor)
        entities.append(
            _person(identifier, name, person.get("gender", "unknown"), [anchor], ["subject"], config)
        )
        subjects[unit.unit_id] = identifier
    return entities, subjects


def prophet_entity(book: CanonicalBook, origins: dict[str, str], config: Config) -> Entity:
    mentions = []
    for block in book.blocks_in_order():
        if origins.get(block.block_id) != "author_text":
            continue
        for match in _PROPHET.finditer(block.text):
            mentions.append(_anchor(book, block.block_id, match.start(), match.end()))
            if len(mentions) >= MAX_MENTIONS:
                break
        if len(mentions) >= MAX_MENTIONS:
            break
    name = PersonName(ism="محمد", full_surface="رسول الله ﷺ")
    entity = _person(
        PROPHET_ID,
        name,
        "m",
        mentions,
        [],
        config,
        aliases=PROPHET_ALIASES,
        external_ids={"authority": "prophet"},
    )
    return entity.model_copy(
        update={"canonical_name": "رسول الله ﷺ", "canonical_name_normalized": normalize("رسول الله ﷺ")}
    )


def _front_matter_mention(book: CanonicalBook, text: str) -> Anchor | None:
    """First front-matter block (pages ≤ 19) containing `text` as a name."""
    needle = normalize(text)
    for block in book.blocks_in_order():
        if block.page > 19 or block.kind == "footnote":
            continue
        normalized = normalize(block.text)
        if needle and needle in normalized:
            name = parse_name(block.text)
            if name is not None:
                return _anchor(book, block.block_id, name.span[0], name.span[1])
    return None


def _source_author_id(book: CanonicalBook) -> str | None:
    attributes = book.raw_extras.get("top", {}).get("metadata", {}).get("source_attributes", {})
    value = attributes.get("source_author_id")
    return str(value) if value is not None else None


def book_people(book: CanonicalBook, metadata: BookMetadata, config: Config) -> list[Entity]:
    """The author (with the source's author id) and the editor."""
    people = []
    author = metadata.author.value if isinstance(metadata.author.value, dict) else None
    if author and author.get("name"):
        parsed = parse_name(author["name"])
        name = parsed.to_person_name() if parsed else PersonName(full_surface=author["name"])
        mention = _front_matter_mention(book, author["name"].split()[-1])
        source_id = _source_author_id(book)
        people.append(
            _person(
                entity_id(book.book.pub_ref, name.full_surface, mention),
                name,
                "m",
                [mention] if mention else [],
                ["author"],
                config,
                external_ids={"shamela_author": source_id} if source_id else {},
            )
        )
    editor = metadata.editor.value
    if isinstance(editor, str) and editor:
        parsed = parse_name(editor)
        name = parsed.to_person_name() if parsed else PersonName(full_surface=editor)
        mention = _front_matter_mention(book, editor)
        people.append(
            _person(
                entity_id(book.book.pub_ref, editor, mention),
                name,
                "m",
                [mention] if mention else [],
                ["editor"],
                config,
            )
        )
    return people


def build_entities(
    book: CanonicalBook,
    units: list[KnowledgeUnit],
    metadata: BookMetadata,
    origins: dict[str, str],
    config: Config,
) -> Entities:
    subjects, unit_subjects = subject_entities(book, units, config)
    entities = [prophet_entity(book, origins, config), *book_people(book, metadata, config), *subjects]
    return resolve_aliases(book, Entities(entities, unit_subjects))


# --- Alias resolution and de-duplication (T-081) ----------------------------------------------------------

FRONT_MATTER_LAST_PAGE = 19


def same_person(a: PersonName, b: PersonName) -> bool:
    """Same ism and ≥ 2 shared chain names, or same kunya and nisba. Never the ism alone."""
    if a.ism and a.ism == b.ism and len(a.nasab) >= 2 and len(b.nasab) >= 2 and a.nasab[:2] == b.nasab[:2]:
        return True
    return bool(a.kunya and a.kunya == b.kunya and a.nisba and set(a.nisba) & set(b.nisba))


def _name_mentions(book: CanonicalBook, entity: Entity) -> list[tuple[Anchor, PersonName]]:
    """Full-name mentions of `entity` in the front matter (its ism followed by its first ancestor)."""
    name = entity.name
    if name is None or not name.ism or not name.nasab:
        return []
    needle = f"{normalize(name.ism)} بن {normalize(name.nasab[0])}"
    found = []
    for block in book.blocks_in_order():
        if block.page > FRONT_MATTER_LAST_PAGE or block.kind == "footnote":
            continue
        mapped = normalize_with_map(block.text)
        for match in re.finditer(re.escape(needle), mapped.text.replace("ابن ", "بن ")):
            start = mapped.starts[match.start()]
            kunya = re.search(r"(?:أبو|أبي|أبا)\s+\S+\s+$", block.text[:start])
            start = kunya.start() if kunya else start
            parsed = parse_name(block.text[start:], offset=start)
            if parsed is not None:
                found.append(
                    (_anchor(book, block.block_id, parsed.span[0], parsed.span[1]), parsed.to_person_name())
                )
    return found


def _nisba_mentions(book: CanonicalBook, nisba: str) -> list[Anchor]:
    pattern = re.compile(rf"(?<![ء-ي]){re.escape(normalize(nisba))}(?![ء-ي])")
    found = []
    for block in book.blocks_in_order():
        mapped = normalize_with_map(block.text)
        for match in pattern.finditer(mapped.text):
            start, end = mapped.to_original(match.start(), match.end())
            found.append(_anchor(book, block.block_id, start, end))
    return found


def resolve_aliases(book: CanonicalBook, result: Entities) -> Entities:
    """Merge duplicate persons, collect alias spellings, flag same-name people with conflicting chains."""
    entities = list(result.entities)
    merged: dict[str, str] = {}  # removed entity id → kept entity id
    for i, keep in enumerate(entities):
        if keep.entity_id in merged or keep.name is None:
            continue
        for other in entities[i + 1 :]:
            if (
                other.entity_id not in merged
                and other.name is not None
                and same_person(keep.name, other.name)
            ):
                merged[other.entity_id] = keep.entity_id

    nisba_owners: dict[str, list[str]] = {}
    for entity in entities:
        if entity.entity_id not in merged and entity.name:
            for nisba in entity.name.nisba:
                nisba_owners.setdefault(normalize(nisba), []).append(entity.entity_id)

    by_id = {e.entity_id: e for e in entities}
    updated: dict[str, Entity] = {}
    for entity in entities:
        if entity.entity_id in merged:
            continue
        mentions = list(entity.mentions)
        aliases = set(entity.aliases)
        for removed, kept in merged.items():
            if kept == entity.entity_id:
                mentions += by_id[removed].mentions
                aliases.add(by_id[removed].canonical_name)
        for anchor, _ in _name_mentions(book, entity):
            mentions.append(anchor)
            aliases.add(anchor.quote)
        for nisba in entity.name.nisba if entity.name else []:
            if nisba_owners.get(normalize(nisba)) == [entity.entity_id]:  # the only person with this nisba
                for anchor in _nisba_mentions(book, nisba)[:MAX_MENTIONS]:
                    mentions.append(anchor)
                    aliases.add(anchor.quote)
        unique = {(m.block_id, m.start, m.end): m for m in mentions}
        aliases.discard(entity.canonical_name)
        updated[entity.entity_id] = entity.model_copy(
            update={
                "mentions": sorted(unique.values(), key=lambda m: (book.block(m.block_id).order, m.start)),
                "aliases": sorted(aliases),
            }
        )

    issues = list(result.issues)
    named = [(e, e.name) for e in updated.values() if e.name and e.name.ism and len(e.name.nasab) >= 2]
    people = [e for e, _ in named]
    names = {e.entity_id: name for e, name in named}
    for i, a in enumerate(people):
        for b in people[i + 1 :]:
            left_name, right_name = names[a.entity_id], names[b.entity_id]
            if (
                left_name.ism == right_name.ism
                and left_name.nasab[0] == right_name.nasab[0]
                and left_name.nasab[:2] != right_name.nasab[:2]
            ):
                for left, right in ((a, b), (b, a)):
                    updated[left.entity_id] = updated[left.entity_id].model_copy(
                        update={
                            "disambiguation": "ambiguous",
                            "candidates": sorted({*updated[left.entity_id].candidates, right.entity_id}),
                        }
                    )
                issues.append(
                    make_issue(
                        book.book.pub_ref,
                        "ambiguous_entity",
                        "warning",
                        "entity",
                        a.entity_id,
                        f"{a.canonical_name!r} and {b.canonical_name!r}: same name, conflicting lineages.",
                        STEP,
                        details={"candidates": [a.entity_id, b.entity_id]},
                        key=b.entity_id,
                    )
                )
    subjects = {unit: merged.get(entity, entity) for unit, entity in result.unit_subjects.items()}
    return Entities([updated[e.entity_id] for e in entities if e.entity_id in updated], subjects, issues)
