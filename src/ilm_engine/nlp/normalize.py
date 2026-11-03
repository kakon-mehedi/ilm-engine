"""Arabic search normalization (ADR-012, FR-050).

The normalized text is a DERIVED copy used only for matching, search and comparison; the original is
never modified. `normalize_with_map` also returns, for every normalized character, the span of the
original text it came from, so a match found in the normalized copy maps back to exact original
offsets (evidence guard, ADR-007).

Rules, in order (ADR-012):
 1. Unicode NFC;
 2. remove harakat and tanwin (U+064B–U+065F, incl. shadda and sukun), the superscript alef (U+0670),
    Quranic marks and invisible format characters ("اللَّه" → "الله" follows from this rule);
 3. remove tatweel (U+0640);
 4. أ/إ/آ/ٱ → ا;
 5. ى → ي, and ة → ه (`search` profile only);
 6. ؤ → و, ئ → ي;
 7. Arabic-Indic digits → 0–9;
 8. honorifics ("صلى الله عليه وسلم", "صلى الله عليه وآله وسلم", "ﷺ", with or without the
    surrounding dashes) → token `<SAW>`;
 9. collapse whitespace and trim.

Profiles: `search` applies every rule; `match` (evidence matching) keeps ة distinct from ه.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

NORMALIZER_VERSION = "1.0.0"
HONORIFIC_TOKEN = "<SAW>"

Profile = Literal["search", "match"]

_REMOVED = frozenset(
    [chr(c) for c in range(0x064B, 0x0660)]  # harakat, tanwin, shadda, sukun, maddah/hamza marks
    + ["ٰ", "ـ"]  # superscript alef, tatweel
    + [chr(c) for c in range(0x0610, 0x061B)]  # Quranic honorific marks
    + [chr(c) for c in range(0x06D6, 0x06EE) if c not in (0x06E5, 0x06E6)]  # Quranic annotation marks
    + ["​", "‌", "‍", "‎", "‏", "؜", "﻿"]  # zero-width and bidi marks
)

_LETTERS = {
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ى": "ي",
    "ؤ": "و",
    "ئ": "ي",
    **{chr(0x0660 + d): str(d) for d in range(10)},  # Arabic-Indic digits
    **{chr(0x06F0 + d): str(d) for d in range(10)},  # Extended (Persian) Arabic-Indic digits
}
_SEARCH_ONLY = {"ة": "ه"}

# Matched after rules 1–7, so it is written in normalized form (ى→ي, آ→ا).
_HONORIFIC = re.compile(r"\s*-?\s*(?:صلي الله عليه (?:واله )?وسلم|ﷺ)\s*-?\s*")


@dataclass(frozen=True)
class NormalizedText:
    """Normalized text plus, per character, the original span `[starts[i], ends[i])` it came from."""

    text: str
    starts: tuple[int, ...]
    ends: tuple[int, ...]

    @property
    def index_map(self) -> tuple[int, ...]:
        """Original offset of every normalized character."""
        return self.starts

    def to_original(self, start: int, end: int) -> tuple[int, int]:
        """Map a normalized span `[start, end)` to the original span covering it."""
        if not 0 <= start < end <= len(self.text):
            raise ValueError(f"span [{start}, {end}) outside normalized text of length {len(self.text)}")
        return self.starts[start], self.ends[end - 1]


# One normalized character with the original span it came from.
_Char = tuple[str, int, int]


def normalize(text: str, profile: Profile = "search") -> str:
    """Normalized copy of `text` for search (`search`) or evidence matching (`match`)."""
    return normalize_with_map(text, profile).text


def normalize_with_map(text: str, profile: Profile = "search") -> NormalizedText:
    """Normalize `text` and keep the mapping back to original offsets."""
    if profile not in ("search", "match"):
        raise ValueError(f"unknown normalization profile {profile!r}")
    letters = {**_LETTERS, **_SEARCH_ONLY} if profile == "search" else _LETTERS

    chars: list[_Char] = []
    for char, start, end in _nfc_clusters(text):
        if char in _REMOVED:
            if chars:  # a removed mark belongs to the letter before it
                previous = chars[-1]
                chars[-1] = (previous[0], previous[1], max(previous[2], end))
            continue
        chars.append((letters.get(char, char), start, end))

    chars = _replace_honorifics(chars)
    chars = _collapse_whitespace(chars)
    return NormalizedText(
        text="".join(char for char, _, _ in chars),
        starts=tuple(start for _, start, _ in chars),
        ends=tuple(end for _, _, end in chars),
    )


def _nfc_clusters(text: str) -> list[_Char]:
    """NFC per cluster (base character + following combining marks); every output character keeps
    the span of its whole cluster, so composition and mark reordering never lose an offset."""
    out: list[_Char] = []
    start = 0
    while start < len(text):
        end = start + 1
        while end < len(text) and unicodedata.combining(text[end]):
            end += 1
        out.extend((char, start, end) for char in unicodedata.normalize("NFC", text[start:end]))
        start = end
    return out


def _replace_honorifics(chars: list[_Char]) -> list[_Char]:
    current = "".join(char for char, _, _ in chars)
    out: list[_Char] = []
    position = 0
    for match in _HONORIFIC.finditer(current):
        out.extend(chars[position : match.start()])
        span_start, span_end = chars[match.start()][1], chars[match.end() - 1][2]
        out.extend((char, span_start, span_end) for char in f" {HONORIFIC_TOKEN} ")
        position = match.end()
    out.extend(chars[position:])
    return out


def _collapse_whitespace(chars: list[_Char]) -> list[_Char]:
    out: list[_Char] = []
    for char, start, end in chars:
        if char.isspace():
            if not out or out[-1][0] == " ":
                continue
            char = " "
        out.append((char, start, end))
    if out and out[-1][0] == " ":
        out.pop()
    return out
