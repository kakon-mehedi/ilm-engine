"""Relationships (step `relations`, 02-architecture L12): sibling groups from closing phrases (T-082).

The author lists siblings one entry at a time and closes the group with a phrase naming the parent:
"١٠ - وهالة؛ ابنا أبي هالة مالك بن النبّاش" (dual: the last two entries), "٢١ - وعاتكة بنو عبد المطلب"
(plural: every entry since the previous closure in the section). A closure counts only inside an entry's
own text, shortly after the name. Each group gives `sibling_of` for every pair and `child_of` to the
parent; elliptic subjects ("وهند") inherit the parent's lineage and, from a masculine closure, gender.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.config import Config
from ilm_engine.enrichment.models import (
    Anchor,
    Entity,
    Issue,
    KnowledgeUnit,
    PersonName,
    Provenance,
    Relationship,
    RelationshipAttrs,
)
from ilm_engine.ids import make_id, natural_key
from ilm_engine.nlp.nasab import clean, parse_name
from ilm_engine.nlp.normalize import normalize
from ilm_engine.validation.confidence import decide, score

STEP = "relations"
MAX_DISTANCE = 80  # characters between the entry's name and its closing phrase
_CLOSURE = re.compile(r"(?<![ء-ي])(?P<word>ابنا|ابنتا|بنو|بنات)\s+(?P<parent>[^.،؛:\n]+)")
_MARKER = re.compile(r"\s*\((?:[٠-٩0-9]+|[ء-ي])\)")
DUAL = {"ابنا", "ابنتا"}
MASCULINE = {"ابنا", "بنو"}


@dataclass
class Group:
    group_id: str
    word: str
    parent_text: str
    anchor: Anchor
    members: list[KnowledgeUnit]
    grammar_ok: bool


@dataclass
class Relations:
    relationships: list[Relationship]
    entities: list[Entity]
    groups: list[Group] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)


def _anchor(book: CanonicalBook, block_id: str, start: int, end: int) -> Anchor:
    block = book.block(block_id)
    while end > start and block.text[end - 1].isspace():
        end -= 1
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


def find_groups(book: CanonicalBook, units: list[KnowledgeUnit]) -> list[Group]:
    groups: list[Group] = []
    last_closure: dict[str, int] = {}  # section → index of the unit that closed the previous group
    ordered = sorted(units, key=lambda u: u.entry_no or 0)
    for index, unit in enumerate(ordered):
        first = unit.anchors[0]
        text = book.block(first.block_id).text
        span = (unit.payload.get("person") or {}).get("span") or [first.start, first.start]
        match = _CLOSURE.search(text, span[1], first.end)
        if match is None or match.start() - span[1] > MAX_DISTANCE:
            continue
        section_units = [i for i, u in enumerate(ordered) if u.section_id == unit.section_id and i <= index]
        previous = last_closure.get(unit.section_id, -1)
        candidates = [ordered[i] for i in section_units if i > previous]
        if match.group("word") in DUAL:
            members = candidates[-2:]
            grammar_ok = len(members) == 2
        else:
            members = candidates
            if match.group("word") == "بنات":
                members = [u for u in members if (u.payload.get("person") or {}).get("gender") != "m"]
            grammar_ok = len(members) >= 2
        last_closure[unit.section_id] = index
        anchor = _anchor(book, first.block_id, match.start(), match.end())
        groups.append(
            Group(
                group_id=make_id("grp", book.book.pub_ref, natural_key(first.block_id, match.start())),
                word=match.group("word"),
                parent_text=_MARKER.sub("", match.group("parent")).strip(),
                anchor=anchor,
                members=members,
                grammar_ok=grammar_ok,
            )
        )
    return groups


def _parent_entity(book: CanonicalBook, group: Group, config: Config) -> tuple[Entity, PersonName]:
    parsed = parse_name(group.parent_text)
    name = parsed.to_person_name() if parsed else PersonName(full_surface=group.parent_text)
    canonical = clean(name.full_surface).strip()
    confidence = score(config, "rule").score
    entity = Entity(
        entity_id=make_id(
            "ent",
            book.book.pub_ref,
            natural_key(normalize(canonical), f"{group.anchor.block_id}:{group.anchor.start}"),
        ),
        entity_type="person",
        canonical_name=canonical,
        canonical_name_normalized=normalize(canonical),
        name=name,
        gender="m" if group.word in ("ابنا", "ابنتا", "بنو", "بنات") else "unknown",
        mentions=[group.anchor],
        confidence=confidence,
        review_status=decide(config, confidence),
        provenance=Provenance(method="rule", step=STEP, step_version="1.0.0"),
    )
    return entity, name


def sibling_groups(
    book: CanonicalBook, units: list[KnowledgeUnit], entities: list[Entity], config: Config
) -> Relations:
    pub_ref = book.book.pub_ref
    by_id = {entity.entity_id: entity for entity in entities}
    groups = find_groups(book, units)
    relationships: list[Relationship] = []
    new_entities: list[Entity] = []
    for group in groups:
        parent, parent_name = _parent_entity(book, group, config)
        new_entities.append(parent)
        penalties = [] if group.grammar_ok else ["grammar_mismatch"]
        confidence = score(config, "rule", penalties=penalties).score
        status = decide(config, confidence)
        provenance = Provenance(method="rule", step=STEP, step_version="1.0.0")
        member_ids = [u.subject_entity_id for u in group.members if u.subject_entity_id in by_id]

        lineage = [parent_name.ism] if parent_name.ism else []
        lineage += list(parent_name.nasab)
        parent_label = parent_name.kunya or parent_name.ism or parent.canonical_name
        for member_id in member_ids:
            member = by_id[member_id]
            updates: dict[str, object] = {}
            if member.name is not None and not member.name.nasab and lineage:
                connector = "بنت" if member.gender == "f" else "بن"
                canonical = f"{member.name.ism or member.canonical_name} {connector} {parent_label}"
                updates.update(
                    name=member.name.model_copy(update={"nasab": lineage}),
                    canonical_name=canonical,
                    canonical_name_normalized=normalize(canonical),
                    disambiguation="resolved",
                )
            if member.gender == "unknown" and group.word in MASCULINE:
                updates["gender"] = "m"  # dual/plural masculine closure (e.g. "ابنا" covers entry #9 "وهند")
            if updates:
                by_id[member_id] = member.model_copy(update=updates)

        for subject, obj in itertools.combinations(member_ids, 2):
            relationships.append(
                Relationship(
                    relation_id=make_id("rel", pub_ref, natural_key("sibling_of", subject, obj)),
                    type="sibling_of",
                    subject_entity_id=subject,
                    object_entity_id=obj,
                    attrs=RelationshipAttrs(
                        kind="unknown", via_parent_entity_id=parent.entity_id, group_id=group.group_id
                    ),
                    evidence=[group.anchor],
                    origin="author_text",
                    assertion="stated",
                    confidence=confidence,
                    review_status=status,
                    provenance=provenance,
                )
            )
        for member_id in member_ids:
            relationships.append(
                Relationship(
                    relation_id=make_id("rel", pub_ref, natural_key("child_of", member_id, parent.entity_id)),
                    type="child_of",
                    subject_entity_id=member_id,
                    object_entity_id=parent.entity_id,
                    attrs=RelationshipAttrs(group_id=group.group_id),
                    evidence=[group.anchor],
                    origin="author_text",
                    assertion="stated",
                    confidence=confidence,
                    review_status=status,
                    provenance=provenance,
                )
            )
    return Relations(relationships, [*by_id.values(), *new_entities], groups)
