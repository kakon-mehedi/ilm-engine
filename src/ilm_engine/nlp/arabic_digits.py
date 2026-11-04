"""Arabic-Indic digits, number words and volume/page locators (EC-065).

These helpers convert numbers for numeric fields only; the original string is always kept as well.
"""

from __future__ import annotations

import re

_DIGITS = {chr(0x0660 + d): str(d) for d in range(10)} | {chr(0x06F0 + d): str(d) for d in range(10)}
_TO_ARABIC = str.maketrans({str(d): chr(0x0660 + d) for d in range(10)})

# Harakat, tanwin, shadda, sukun, superscript alef and tatweel.
_MARKS = re.compile("[ً-ٰٟـ]")
_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})


def to_int(text: str) -> int:
    """`'٧٥'` → 75. Accepts Arabic-Indic, Persian and ASCII digits; surrounding whitespace is ignored."""
    stripped = text.strip()
    converted = "".join(_DIGITS.get(char, char) for char in stripped)
    if not converted.isascii() or not converted.isdigit():
        raise ValueError(f"not a number: {text!r}")
    return int(converted)


def to_arabic_digits(number: int) -> str:
    """`32` → `'٣٢'`."""
    if isinstance(number, bool) or not isinstance(number, int) or number < 0:
        raise ValueError(f"expected a non-negative integer, got {number!r}")
    return str(number).translate(_TO_ARABIC)


def _key(word: str) -> str:
    return _MARKS.sub("", word).translate(_LETTERS)


def _forms(value: int, *words: str) -> dict[str, int]:
    return {_key(word): value for word in words}


_UNITS = (
    _forms(1, "واحد", "واحدة", "أحد", "إحدى")
    | _forms(2, "اثنان", "اثنين", "اثنا", "اثني", "اثنتان", "اثنتين", "اثنتا", "اثنتي")
    | _forms(3, "ثلاث", "ثلاثة")
    | _forms(4, "أربع", "أربعة")
    | _forms(5, "خمس", "خمسة")
    | _forms(6, "ست", "ستة")
    | _forms(7, "سبع", "سبعة")
    | _forms(8, "ثمان", "ثماني", "ثمانية")
    | _forms(9, "تسع", "تسعة")
)
_TEN = _forms(10, "عشر", "عشرة")
_TENS = (
    _forms(20, "عشرون", "عشرين")
    | _forms(30, "ثلاثون", "ثلاثين")
    | _forms(40, "أربعون", "أربعين")
    | _forms(50, "خمسون", "خمسين")
    | _forms(60, "ستون", "ستين")
    | _forms(70, "سبعون", "سبعين")
    | _forms(80, "ثمانون", "ثمانين")
    | _forms(90, "تسعون", "تسعين")
)
_HUNDRED = _forms(100, "مئة", "مائة", "مئه", "مايه")
_HUNDREDS_DUAL = _forms(200, "مئتان", "مئتين", "مائتان", "مائتين")
_THOUSAND = _forms(1000, "ألف", "ألفا", "آلاف")
_THOUSANDS_DUAL = _forms(2000, "ألفان", "ألفين")

# Joined hundreds: ثلاثمئة, أربعمائة, ... (the unit is written without ة).
_JOINED_HUNDRED = re.compile(r"^(ثلاث|اربع|خمس|ست|سبع|ثمان|تسع)(مئه|مائه|ميه)$")


def _value(token: str) -> tuple[str, int] | None:
    """(kind, value) of a single normalized word, or None if it is not a number word."""
    for kind, table in (
        ("unit", _UNITS),
        ("ten", _TEN),
        ("tens", _TENS),
        ("hundred", _HUNDRED),
        ("hundreds", _HUNDREDS_DUAL),
        ("thousand", _THOUSAND),
        ("thousands", _THOUSANDS_DUAL),
    ):
        if token in table:
            return kind, table[token]
    joined = _JOINED_HUNDRED.match(token)
    if joined:
        return "hundreds", _UNITS[joined.group(1)] * 100
    return None


def _number_word(word: str) -> tuple[str, int] | None:
    token = _key(word)
    found = _value(token)
    if found is None and token.startswith("و") and len(token) > 1:  # conjunction: وثمانين
        found = _value(token[1:])
    return found


def words_to_int(text: str) -> int:
    """`'خمس وثمانين وثلاث مئة'` → 385. Diacritics are ignored; words before or after the number
    phrase (e.g. "سنة") are skipped, an unknown word inside it raises `ValueError`."""
    words = text.split()
    values = [_number_word(word) for word in words]
    indexes = [i for i, value in enumerate(values) if value is not None]
    if not indexes:
        raise ValueError(f"no Arabic number words in {text!r}")
    phrase = values[indexes[0] : indexes[-1] + 1]
    if None in phrase:
        unknown = words[indexes[0] + phrase.index(None)]
        raise ValueError(f"unknown word {unknown!r} inside number phrase {text!r}")

    # Arabic orders units before tens and writes multipliers after their unit ("ثلاث مئة",
    # "ثلاثة آلاف", "ثلاثة عشر"), so a multiplier applies only to the part just before it.
    parts: list[tuple[str, int]] = []
    for kind, value in phrase:  # type: ignore[misc]
        previous = parts[-1] if parts else None
        if kind == "ten" and previous and previous[0] == "unit":
            parts[-1] = ("teen", previous[1] + 10)
        elif kind == "hundred" and previous and previous[0] == "unit":
            parts[-1] = ("hundreds", previous[1] * 100)
        elif kind == "thousand" and previous and previous[0] in ("unit", "teen", "tens"):
            parts[-1] = ("thousands", previous[1] * 1000)
        else:
            parts.append((kind, value))
    return sum(value for _, value in parts)


_LOCATOR = re.compile(r"^\(?\s*(?:([0-9٠-٩۰-۹]+)\s*/\s*)?([0-9٠-٩۰-۹]+)\s*\)?$")


def parse_locator(raw: str) -> tuple[int | None, int]:
    """`'(٨/ ١٥٧)'` → `(8, 157)`; `'(١٥٧)'` → `(None, 157)` (volume/page)."""
    match = _LOCATOR.match(raw.strip())
    if not match:
        raise ValueError(f"not a volume/page locator: {raw!r}")
    volume, page = match.groups()
    return (to_int(volume) if volume else None), to_int(page)
