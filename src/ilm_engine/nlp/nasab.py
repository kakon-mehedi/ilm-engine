"""Nasab (lineage chain) parser for Arabic personal names.

`parse_name` reads a name from the start of a text such as
"هند بنت عتيق بن عابد (١) بن عبد اللَّه بن عمر بن مخزوم؛ أسلمت":
an optional kunya (أبو/أبي/أبا/أم + word), the ism, descriptors (الأكبر, -الأوسط-), the chain of
ancestors joined by بن/ابن/بنت, and trailing nisbas (الدارقطني). Footnote markers such as "(١)" are
skipped, and the name ends at punctuation (؛ ، . :) or at the first word that cannot continue it, so
verbs like "أسلمت" are never part of a name.

Name parts are returned without diacritics ("عبد اللَّه" → "عبد الله"); `raw` and `span` give the
exact original surface. Dual and plural forms (ابنا, بنو) are handled by the relation extractor (T-082).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from ilm_engine.enrichment.models import PersonName

Gender = Literal["m", "f", "unknown"]

_MARKS = re.compile("[ً-ٰٟـ]")
_TOKEN = re.compile(r"\S+")
_FOOTNOTE_MARKER = re.compile(r"^\((?:[٠-٩0-9]+|[ء-ي])\)$")
_STOP_PUNCTUATION = set(".,،؛;:!?؟")
_TRAILING = _STOP_PUNCTUATION | {")"}

_CONNECTORS = {"بن": "m", "ابن": "m", "بنت": "f"}
_KUNYA_PREFIXES = {"أبو", "أبي", "أبا", "أم"}
_COMPOUND_PREFIXES = {"عبد", "عبيد", "أبو", "أبي", "أبا", "أم", "ذي", "ذو", "رسول"}
_DESCRIPTORS = {"الأكبر", "الأصغر", "الأوسط", "الكبرى", "الصغرى", "الوسطى", "أكبر", "أصغر", "أوسط"}
# Words that never belong to a name although they may follow one.
_NON_NAME = {
    "هو",
    "هي",
    "وهو",
    "وهي",
    "له",
    "لها",
    "وله",
    "ولها",
    "أمه",
    "أمها",
    "أمهم",
    "أمهما",
    "روى",
    "روت",
    "الذي",
    "التي",
    "ولم",
    "لم",
    "قاله",
    "يقال",
    "ويقال",
    "وقيل",
    "قيل",
    "وقال",
    "قال",
    "كان",
    "وكان",
    "من",
    "عن",
    "في",
    "على",
    "إلى",
    "مع",
    "ابنا",
    "بنو",
    "بنات",
    "وأخته",
    "وأختهم",
}
_FEMININE = {
    "فاطمة",
    "زينب",
    "رقية",
    "أمامة",
    "أميمة",
    "صفية",
    "عاتكة",
    "جمانة",
    "أروى",
    "آمنة",
    "أمينة",
    "لبابة",
    "حفصة",
    "أسماء",
    "عائشة",
    "خديجة",
    "مارية",
    "قريبة",
    "جميلة",
    "سعيدة",
    "فكيهة",
}
# Names that begin with و, so a leading و is not stripped as a conjunction.
_WAW_NAMES = {"وائل", "وهب", "وهيب", "وكيع", "واقد", "وحشي", "ورقة", "وابصة", "وردان", "واثلة"}


@dataclass(frozen=True)
class Name:
    ism: str | None
    gender: Gender
    kunya: str | None
    laqab: str | None
    nisba: tuple[str, ...]
    chain: tuple[str, ...]  # ancestors in order (nasab)
    raw: str  # exact original surface
    span: tuple[int, int]  # offsets of `raw` in the input text (plus `offset`)

    def to_person_name(self) -> PersonName:
        return PersonName(
            ism=self.ism,
            kunya=self.kunya,
            laqab=self.laqab,
            nisba=list(self.nisba),
            nasab=list(self.chain),
            full_surface=self.raw,
        )


def clean(word: str) -> str:
    """Remove diacritics and tatweel; letters (hamza forms included) are kept."""
    return _MARKS.sub("", word)


_INLINE_MARKER = re.compile(r"\s*\((?:[٠-٩0-9]+|[\u0621-\u064a])\)")


def display_name(surface: str) -> str:
    """A name surface for display: footnote markers removed, diacritics removed, spaces collapsed."""
    return " ".join(clean(_INLINE_MARKER.sub(" ", surface)).split())


@dataclass
class _Token:
    core: str  # cleaned word without wrapping brackets or trailing punctuation
    start: int  # original offsets of the core
    end: int
    stops: bool  # trailing punctuation ends the name after this token


def _tokens(text: str) -> list[_Token]:
    tokens = []
    for match in _TOKEN.finditer(text):
        start, end = match.start(), match.end()
        stops = False
        while end > start and text[end - 1] in _TRAILING:
            stops = stops or text[end - 1] in _STOP_PUNCTUATION
            end -= 1
        if text[start] == "(" and end < len(text) and _FOOTNOTE_MARKER.match(text[start : end + 1]):
            end += 1  # keep the marker's closing bracket: "(١)"
        elif text[start] == "(":
            start += 1  # editor's bracketed insertion: "(وحارثة)"
        tokens.append(_Token(clean(text[start:end]), start, end, stops))
    return tokens


def _is_marker(token: _Token) -> bool:
    return bool(_FOOTNOTE_MARKER.match(token.core))


def _is_nisba(word: str) -> bool:
    return (
        word not in _NON_NAME
        and word.startswith("ال")
        and len(word) > 3
        and (word.endswith("ي") or word.endswith("ية"))
    )


def _is_name_word(word: str) -> bool:
    return bool(word) and word not in _NON_NAME and word not in _CONNECTORS and not word.startswith("-")


def parse_name(text: str, offset: int = 0) -> Name | None:
    """Parse the name at the start of `text`; `offset` is added to `span`. None if there is no name."""
    tokens = _tokens(text)
    position = 0
    first_start: int | None = None
    last_end = 0  # end of the last consumed token
    name_end = 0  # end of the last name part (trailing footnote markers are not part of the surface)
    stopped = False

    def take() -> _Token:
        nonlocal position, first_start, last_end, stopped
        token = tokens[position]
        position += 1
        if first_start is None and not _is_marker(token):
            first_start = token.start
        last_end = token.end
        stopped = token.stops
        return token

    def peek() -> _Token | None:
        return tokens[position] if position < len(tokens) and not stopped else None

    def take_element() -> str | None:
        """One name element, joining compounds: "عبد الله", "أبي طالب"."""
        while (token := peek()) is not None and _is_marker(token):
            take()
        token = peek()
        if token is None or not _is_name_word(token.core):
            return None
        nonlocal name_end
        word = take().core
        if word in _COMPOUND_PREFIXES and (following := peek()) is not None and _is_name_word(following.core):
            word = f"{word} {take().core}"
        name_end = last_end
        return word

    while tokens and _is_marker(tokens[0]):  # "أمهم (٢) أم الفضل": the name starts after the marker
        tokens.pop(0)
    if not tokens:
        return None
    head = tokens[0]
    conjoined = head.core.startswith("و") and (len(head.core) > 3 or head.core[1:] in _KUNYA_PREFIXES)
    if conjoined and head.core not in _WAW_NAMES:
        conjunction = head.start + 1
        while conjunction < head.end and _MARKS.match(text[conjunction]):
            conjunction += 1
        tokens[0] = _Token(head.core[1:], conjunction, head.end, head.stops)

    kunya: str | None = None
    ism: str | None = None
    if tokens[0].core in _KUNYA_PREFIXES:
        kunya = take_element()
        if kunya is not None and " " not in kunya:
            kunya = None  # a bare أبو/أم is not a kunya
        if kunya is not None and (following := peek()) is not None and _is_name_word(following.core):
            if not _is_nisba(following.core) and following.core not in _DESCRIPTORS:
                ism = take_element()
    else:
        ism = take_element()
    if ism is None and kunya is None:
        return None

    laqab: str | None = None
    nisba: list[str] = []
    chain: list[str] = []
    gender_from_connector: str | None = None
    while (token := peek()) is not None:
        word = token.core
        if _is_marker(token):
            take()
        elif word.strip("-") in _DESCRIPTORS and not chain:
            laqab = laqab or take().core.strip("-")
            name_end = last_end
        elif word in _CONNECTORS:
            saved = (position, last_end, stopped)
            take()
            element = take_element()
            if element is None:
                position, last_end, stopped = saved  # a dangling connector is not part of the name
                break
            gender_from_connector = gender_from_connector or _CONNECTORS[word]
            chain.append(element)
        elif _is_nisba(word):
            nisba.append(take().core)
            name_end = last_end
        else:
            break

    assert first_start is not None
    return Name(
        ism=ism,
        gender=_gender(ism, kunya, gender_from_connector),
        kunya=kunya,
        laqab=laqab,
        nisba=tuple(nisba),
        chain=tuple(chain),
        raw=text[first_start:name_end],
        span=(first_start + offset, name_end + offset),
    )


def _gender(ism: str | None, kunya: str | None, connector: str | None) -> Gender:
    if connector == "f" or (kunya or "").startswith("أم ") or ism in _FEMININE:
        return "f"
    if connector == "m" or (kunya or "").startswith("أب"):
        return "m"
    return "unknown"
