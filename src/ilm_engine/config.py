"""Configuration loader: `config/default.yaml` deep-merged with `config/books/<pub_id>.yaml`.

Unknown keys are rejected (fail closed). `Config.config_hash` identifies the merged configuration
and is recorded in `run_manifest.json`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    field_validator,
    model_validator,
)

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

_PUB_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

Origin = Literal["author_text", "transmission_isnad", "editor_text", "editor_footnote", "ai_generated"]
SensitiveCategory = Literal[
    "prophetic_attribution",
    "hadith_grading",
    "fiqh_ruling",
    "aqeedah_proposition",
    "narrator_disambiguation",
]


class ConfigError(ValueError):
    """Raised when a configuration file is missing, malformed or fails validation."""


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Threshold(_Section):
    default: float = Field(ge=0, le=1)
    overrides: dict[str, float] = {}

    @field_validator("overrides")
    @classmethod
    def _in_unit_range(cls, value: dict[str, float]) -> dict[str, float]:
        for category, threshold in value.items():
            if not 0 <= threshold <= 1:
                raise ValueError(f"threshold for {category!r} must be within [0, 1], got {threshold}")
        return value


class ReviewConfig(_Section):
    threshold: Threshold
    inferred_always_review: bool = True
    sensitive_categories: list[SensitiveCategory]


class BaseFactors(_Section):
    rule: float
    llm: float


class EvidenceFactors(_Section):
    exact: float
    normalized: float
    none: float


class SchemaFactors(_Section):
    valid: float
    repaired: float
    invalid: float


class AgreementFactors(_Section):
    agree: float
    judge_resolved: float
    single: float


class PenaltyFactors(_Section):
    ambiguous_entity: float
    grammar_mismatch: float
    ocr_noise: float
    ambiguous_quote: float


class ConfidenceConfig(_Section):
    base: BaseFactors
    evidence: EvidenceFactors
    schema_: SchemaFactors = Field(alias="schema")
    agreement: AgreementFactors
    penalties: PenaltyFactors


class EntriesConfig(_Section):
    regex: str
    start_page: int = Field(ge=1)

    @field_validator("regex")
    @classmethod
    def _compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"invalid regular expression: {exc}") from exc
        return value


class ModelRoute(_Section):
    provider: Literal["anthropic", "litellm"]
    model: str = Field(min_length=1)
    api_base: str | None = None

    @property
    def family(self) -> str:
        return model_family(self.model)


class LlmConfig(_Section):
    provider: Literal["null", "fixture", "anthropic", "litellm"]
    temperature: float = Field(ge=0)
    extractor: ModelRoute
    verifier: ModelRoute | None = None

    @model_validator(mode="after")
    def _independent_verifier(self) -> Self:
        # ADR-008: consensus needs a second, independent model family.
        if self.verifier is not None and self.verifier.family == self.extractor.family:
            raise ValueError(
                f"llm.verifier ({self.verifier.model}) is the same model family ({self.verifier.family}) "
                f"as llm.extractor ({self.extractor.model}); choose a different family"
            )
        return self


class FeaturesConfig(_Section):
    semantic_search: bool
    camel_tools: bool


PageClass = Literal[
    "cover", "publisher_page", "basmala", "blank", "title_page", "printed_indexes", "content", "unknown"
]
NON_CONTENT_PAGES = frozenset(
    {"cover", "publisher_page", "basmala", "blank", "title_page", "printed_indexes"}
)


class PagesConfig(_Section):
    gaps: dict[int, PageClass] = {}
    pdf_extra: dict[str, PageClass] = {}

    @field_validator("pdf_extra")
    @classmethod
    def _ranges(cls, value: dict[str, PageClass]) -> dict[str, PageClass]:
        for key in value:
            if not re.fullmatch(r"\d+(-\d+)?", key):
                raise ValueError(f"pdf_extra keys are page ranges like '73-80', got {key!r}")
        return value

    def pdf_extra_pages(self) -> dict[int, PageClass]:
        pages: dict[int, PageClass] = {}
        for key, page_class in self.pdf_extra.items():
            first, _, last = key.partition("-")
            for page in range(int(first), int(last or first) + 1):
                pages[page] = page_class
        return pages


class OriginOverride(_Section):
    pages: tuple[int, int] | None = None
    blocks: tuple[str, str] | None = None
    origin: Origin
    note: str

    @model_validator(mode="after")
    def _one_range(self) -> Self:
        if (self.pages is None) == (self.blocks is None):
            raise ValueError("an origin override sets exactly one of 'pages' or 'blocks'")
        # Block IDs are zero-padded (b000135), so string order is document order.
        span: tuple[int, int] | tuple[str, str] = self.pages or self.blocks  # type: ignore[assignment]
        if span[0] > span[1]:  # type: ignore[operator]
            raise ValueError(f"origin override range is reversed: [{span[0]}, {span[1]}]")
        return self


class OriginConfig(_Section):
    overrides: list[OriginOverride] = []


class Config(_Section):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    review: ReviewConfig
    confidence: ConfidenceConfig
    entries: EntriesConfig
    llm: LlmConfig
    features: FeaturesConfig
    pages: PagesConfig
    origin: OriginConfig

    _config_hash: str = PrivateAttr(default="")

    @property
    def config_hash(self) -> str:
        """`sha256:<hex>` of the merged configuration as canonical JSON."""
        return self._config_hash


_FAMILIES = (
    ("claude", "anthropic"),
    ("anthropic", "anthropic"),
    ("gpt", "openai"),
    ("openai", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
    ("gemini", "google"),
    ("gemma", "google"),
    ("qwen", "qwen"),
    ("llama", "meta"),
    ("mistral", "mistral"),
    ("mixtral", "mistral"),
    ("jais", "jais"),
    ("deepseek", "deepseek"),
    ("command", "cohere"),
)


def model_family(model: str) -> str:
    """Model family of a model id, e.g. `claude-sonnet-5-5` → anthropic, `openai/gpt-x` → openai.

    LiteLLM-style ids (`<provider>/<model>`) are judged by the model name, so a Claude model served
    through any proxy is still the anthropic family.
    """
    name = model.lower().rsplit("/", 1)[-1]
    for prefix, family in _FAMILIES:
        if name.startswith(prefix):
            return family
    return name.split("-", 1)[0]


def load_config(pub_id: str | None = None, config_dir: Path | None = None) -> Config:
    """Load the default configuration, deep-merged with the book override for `pub_id` if one exists."""
    config_dir = config_dir or DEFAULT_CONFIG_DIR
    default_path = config_dir / "default.yaml"
    if not default_path.is_file():
        raise ConfigError(f"default configuration not found: {default_path}")
    merged = _read_yaml(default_path)
    sources = [default_path]

    if pub_id is not None:
        if not _PUB_ID_PATTERN.match(pub_id):
            raise ConfigError(f"invalid pub_id for a config file name: {pub_id!r}")
        book_path = config_dir / "books" / f"{pub_id}.yaml"
        if book_path.is_file():
            merged = _deep_merge(merged, _read_yaml(book_path))
            sources.append(book_path)

    try:
        config = Config.model_validate(merged)
    except ValidationError as exc:
        names = " + ".join(str(path) for path in sources)
        raise ConfigError(f"invalid configuration ({names}):\n{exc}") from exc

    canonical = json.dumps(
        config.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    config._config_hash = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return config


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"cannot parse {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping at the top level")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge `override` into a copy of `base`: mappings merge recursively, every other value replaces."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
