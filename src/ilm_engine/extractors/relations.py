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
from ilm_engine.nlp.nasab import display_name, parse_name
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
    canonical = display_name(name.full_surface)
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


# --- Relation kinds and mothers (T-083) ------------------------------------------------------------------

_LETTERS_B, _LETTERS_E = r"(?<![ء-ي])", r"(?![ء-ي])"
_MOTHER = re.compile(_LETTERS_B + r"و?ام(?P<pronoun>ه|ها|هما|هم)" + _LETTERS_E)
_UMM_WALAD = re.compile(_LETTERS_B + r"(?:ل)?(?:ام ولد|امهات اولاد)" + _LETTERS_E)
_MATERNAL_SIBLING = re.compile(_LETTERS_B + r"و?(?:اخته|اخوه) لامه" + _LETTERS_E)


@dataclass
class MotherStatement:
    unit: KnowledgeUnit
    scope: list[KnowledgeUnit]
    anchor: Anchor
    name: PersonName | None  # None for an unnamed umm walad
    umm_walad: bool


def _normalized_spans(
    book: CanonicalBook, unit: KnowledgeUnit, pattern: re.Pattern[str]
) -> list[tuple[str, int, int]]:
    from ilm_engine.nlp.normalize import normalize_with_map

    found = []
    for span in unit.anchors:
        text = book.block(span.block_id).text
        mapped = normalize_with_map(text[: span.end], "match")
        for match in pattern.finditer(mapped.text):
            start, end = mapped.to_original(match.start(), match.end())
            if start >= span.start:
                found.append((span.block_id, start, end))
    return found


def mother_statements(
    book: CanonicalBook, units: list[KnowledgeUnit], groups: list[Group]
) -> list[MotherStatement]:
    """ "أمه X" (this entry), "أمهما X" (the dual group / last two entries), "أمهم X" (the group the entry
    closes, else every entry since the previous closure or mother statement in the section)."""
    ordered = sorted(units, key=lambda u: u.entry_no or 0)
    closed_by = {g.members[-1].unit_id: g for g in groups if g.members}
    statements = []
    last_closure: dict[str, int] = {}
    for index, unit in enumerate(ordered):
        group = closed_by.get(unit.unit_id)
        found = _normalized_spans(book, unit, _MOTHER)
        for block_id, start, end in found:
            text = book.block(block_id).text
            word = normalize(text[start:end], "match")
            pronoun = "هما" if word.endswith("هما") else "هم" if word.endswith("هم") else "ه"
            after = _MARKER.sub(" ", text[end:])
            umm_walad = normalize(after, "match").lstrip().startswith("ام ولد")
            name_from = end
            if umm_walad:
                named = re.search(r"يقال لها:?\s*", text[end:])
                name_from = end + named.end() if named else -1
            parsed = parse_name(text[name_from:], offset=name_from) if name_from >= 0 else None
            if parsed is None and not umm_walad:
                continue
            section = [u for u in ordered[: index + 1] if u.section_id == unit.section_id]
            if pronoun == "ه":
                scope = [unit]
            elif pronoun == "هما":
                scope = group.members if group and len(group.members) == 2 else section[-2:]
            else:
                previous = last_closure.get(unit.section_id, -1)
                scope = group.members if group else [u for u in section if ordered.index(u) > previous]
            anchor_end = parsed.span[1] if parsed else end
            statements.append(
                MotherStatement(
                    unit=unit,
                    scope=scope,
                    anchor=_anchor(book, block_id, start, anchor_end),
                    name=parsed.to_person_name() if parsed else None,
                    umm_walad=umm_walad,
                )
            )
        if group is not None or found:
            last_closure[unit.section_id] = index
    return statements


def relation_kinds(
    book: CanonicalBook, units: list[KnowledgeUnit], result: Relations, config: Config
) -> Relations:
    """Set `kind` / `mother_status` on sibling relations and add `mother_is` relations."""
    pub_ref = book.book.pub_ref
    confidence = score(config, "rule").score
    provenance = Provenance(method="rule", step=STEP, step_version="1.0.0")
    entities = {e.entity_id: e for e in result.entities}
    relationships = list(result.relationships)
    mother_of: dict[str, tuple[str | None, str]] = {}  # child entity → (mother entity, status)

    for statement in mother_statements(book, units, result.groups):
        mother_id: str | None = None
        if statement.name is not None:
            canonical = display_name(statement.name.full_surface)
            mother_id = make_id("ent", pub_ref, natural_key(normalize(canonical), "mother"))
            if mother_id not in entities:
                entities[mother_id] = Entity(
                    entity_id=mother_id,
                    entity_type="person",
                    canonical_name=canonical,
                    canonical_name_normalized=normalize(canonical),
                    name=statement.name,
                    gender="f",
                    mentions=[statement.anchor],
                    confidence=confidence,
                    review_status=decide(config, confidence),
                    provenance=provenance,
                )
        status = "umm_walad" if statement.umm_walad else "named"
        for member in statement.scope:
            if not member.subject_entity_id:
                continue
            mother_of[member.subject_entity_id] = (mother_id, status)
            if mother_id:
                relationships.append(
                    Relationship(
                        relation_id=make_id(
                            "rel", pub_ref, natural_key("mother_is", member.subject_entity_id, mother_id)
                        ),
                        type="mother_is",
                        subject_entity_id=member.subject_entity_id,
                        object_entity_id=mother_id,
                        attrs=RelationshipAttrs(mother_status=status),  # type: ignore[arg-type]
                        evidence=[statement.anchor],
                        origin="author_text",
                        assertion="stated",
                        confidence=confidence,
                        review_status=decide(config, confidence),
                        provenance=provenance,
                    )
                )

    # Closures with "لأم ولد" / "لأمهات أولاد": the mother was an umm walad (NOT maternal siblings).
    umm_walad_groups = {g.group_id for g in result.groups if _UMM_WALAD.search(normalize(g.parent_text))}
    updated: list[Relationship] = []
    for relation in relationships:
        if relation.type != "sibling_of":
            updated.append(relation)
            continue
        attrs = relation.attrs
        a, b = mother_of.get(relation.subject_entity_id), mother_of.get(relation.object_entity_id)
        if attrs.group_id in umm_walad_groups:
            attrs = attrs.model_copy(update={"kind": "paternal", "mother_status": "umm_walad"})
        elif a and b and a[0] and a[0] == b[0]:
            attrs = attrs.model_copy(update={"kind": "full", "mother_status": "named"})
        elif attrs.via_parent_entity_id:
            known = a or b
            attrs = attrs.model_copy(
                update={"kind": "paternal", "mother_status": known[1] if known else "unknown"}
            )
        updated.append(relation.model_copy(update={"attrs": attrs}))

    # "وأخته لأمه: <next entry>" → stated maternal sister (full if they also share a father).
    ordered = sorted(units, key=lambda u: u.entry_no or 0)
    for index, unit in enumerate(ordered[:-1]):
        spans = _normalized_spans(book, unit, _MATERNAL_SIBLING)
        following = ordered[index + 1]
        if not spans or not unit.subject_entity_id or not following.subject_entity_id:
            continue
        block_id, start, end = spans[0]
        left, right = entities[unit.subject_entity_id], entities[following.subject_entity_id]
        same_father = bool(
            left.name and right.name and left.name.nasab[:1] and left.name.nasab[:1] == right.name.nasab[:1]
        )
        updated.append(
            Relationship(
                relation_id=make_id(
                    "rel", pub_ref, natural_key("sibling_of", left.entity_id, right.entity_id, "maternal")
                ),
                type="sibling_of",
                subject_entity_id=left.entity_id,
                object_entity_id=right.entity_id,
                attrs=RelationshipAttrs(kind="full" if same_father else "maternal", mother_status="named"),
                evidence=[_anchor(book, block_id, start, end)],
                origin="author_text",
                assertion="stated",
                confidence=confidence,
                review_status=decide(config, confidence),
                provenance=provenance,
            )
        )
    return Relations(updated, list(entities.values()), result.groups, result.issues)


# --- Inferred relations from section headings (T-084) ---------------------------------------------------

PROPHET_SUBJECTS = {normalize("رسول الله ﷺ"), normalize("رسول الله"), normalize("النبي")}


def _subject_entity(
    subject: str, entities: dict[str, Entity], book: CanonicalBook, config: Config, anchor: Anchor
) -> str:
    """The section subject's entity: the Prophet authority, an entity with that exact name, or a new one."""
    from ilm_engine.extractors.entities import PROPHET_ID

    key = normalize(subject)
    if key in PROPHET_SUBJECTS:
        return PROPHET_ID
    for entity in entities.values():
        if entity.canonical_name_normalized == key:
            return entity.entity_id
    parsed = parse_name(subject)
    name = parsed.to_person_name() if parsed else PersonName(full_surface=subject)
    identifier = make_id("ent", book.book.pub_ref, natural_key(key, "section_subject"))
    confidence = score(config, "rule").score
    entities[identifier] = Entity(
        entity_id=identifier,
        entity_type="person",
        canonical_name=display_name(subject),
        canonical_name_normalized=key,
        name=name,
        gender="m",
        mentions=[anchor],
        confidence=confidence,
        review_status=decide(config, confidence),
        provenance=Provenance(method="rule", step=STEP, step_version="1.0.0"),
    )
    return identifier


def inferred_relations(
    book: CanonicalBook, units: list[KnowledgeUnit], result: Relations, config: Config
) -> Relations:
    """`child_of` the section subject for every entry of a "أولاد / ولد / ذرية X" section, and maternal
    siblings for a "من أمهم X" heading: inferred, `ai_generated`, evidence = heading + entry, reviewed."""
    pub_ref = book.book.pub_ref
    entities = {e.entity_id: e for e in result.entities}
    stated = {(r.type, r.subject_entity_id) for r in result.relationships if r.assertion == "stated"}
    confidence = score(config, "llm").score
    status = "pending_review" if config.review.inferred_always_review else decide(config, confidence)
    provenance = Provenance(method="rule", step=STEP, step_version="1.0.0")
    added: list[Relationship] = []
    by_section: dict[str, list[KnowledgeUnit]] = {}
    for unit in sorted(units, key=lambda u: u.entry_no or 0):
        by_section.setdefault(unit.section_id, []).append(unit)

    def relation(
        type_: str, subject: str, obj: str, evidence: list[Anchor], attrs: RelationshipAttrs
    ) -> Relationship:
        return Relationship(
            relation_id=make_id("rel", pub_ref, natural_key(type_, subject, obj, "inferred")),
            type=type_,  # type: ignore[arg-type]
            subject_entity_id=subject,
            object_entity_id=obj,
            attrs=attrs,
            evidence=evidence,
            origin="ai_generated",
            assertion="inferred",
            confidence=confidence,
            review_status=status,  # type: ignore[arg-type]
            provenance=provenance,
        )

    for section_units in by_section.values():
        payload = section_units[0].payload
        heading = payload.get("section_heading_anchor")
        subject = payload.get("section_subject")
        if not heading or not subject:
            continue
        heading_anchor = Anchor.model_validate(heading)
        parent_id = _subject_entity(subject, entities, book, config, heading_anchor)
        mother = payload.get("section_mother")
        for unit in section_units:
            child = unit.subject_entity_id
            if not child or ("child_of", child) in stated:
                continue  # a stated parent (closure phrase) outranks the heading
            evidence = [heading_anchor, unit.anchors[0]]
            if mother:
                # "وأخوة أولاد رسول الله من أمهم خديجة": these are the Prophet's children's maternal siblings.
                children = [
                    u.subject_entity_id
                    for other in by_section.values()
                    for u in other
                    if u.subject_entity_id
                    and other[0].payload.get("section_subject") == subject
                    and not other[0].payload.get("section_mother")
                ]
                for sibling in children:
                    added.append(
                        relation(
                            "sibling_of",
                            child,
                            sibling,
                            evidence,
                            RelationshipAttrs(kind="maternal", mother_status="named"),
                        )
                    )
            else:
                added.append(relation("child_of", child, parent_id, evidence, RelationshipAttrs()))
    return Relations([*result.relationships, *added], list(entities.values()), result.groups, result.issues)
