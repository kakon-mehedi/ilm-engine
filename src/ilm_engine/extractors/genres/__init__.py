"""Genre plugins (ADR-013): one schema module per genre, listed by `registry()`.

Each module exposes `GENRE`, `SUB_TYPES`, `UNIT_TYPES`, a Pydantic `UnitSchema` for the genre payload,
`sensitive_fields` (payload field → ADR-009 category; these fields always go to review) and
`prompt_task`. The MVP implements biography (ansab) and hadith takhrij candidates; the other five ship
their schemas so the contract is complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from pydantic import BaseModel

from ilm_engine.extractors.genres import aqeedah, biography, fiqh, hadith, history, seerah, tafsir

_MODULES: tuple[ModuleType, ...] = (fiqh, hadith, tafsir, seerah, aqeedah, history, biography)


@dataclass(frozen=True)
class GenrePlugin:
    genre: str
    sub_types: tuple[str, ...]
    unit_types: tuple[str, ...]
    unit_schema: type[BaseModel]
    sensitive_fields: dict[str, str]
    prompt_task: str


def registry() -> dict[str, GenrePlugin]:
    return {
        module.GENRE: GenrePlugin(
            genre=module.GENRE,
            sub_types=tuple(module.SUB_TYPES),
            unit_types=tuple(module.UNIT_TYPES),
            unit_schema=module.UnitSchema,
            sensitive_fields=dict(module.sensitive_fields),
            prompt_task=module.prompt_task,
        )
        for module in _MODULES
    }
