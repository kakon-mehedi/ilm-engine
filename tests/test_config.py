import shutil
from pathlib import Path

import pytest

from ilm_engine.config import DEFAULT_CONFIG_DIR, ConfigError, load_config

SAMPLE_PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """A writable copy of the repository config folder."""
    target = tmp_path / "config"
    shutil.copytree(DEFAULT_CONFIG_DIR, target)
    return target


def test_sample_book_threshold_default():
    assert load_config(SAMPLE_PUB_ID).review.threshold.default == 0.80


def test_defaults_match_decisions():
    config = load_config()
    assert config.review.threshold.overrides == {"fiqh_ruling": 0.95}
    assert config.review.sensitive_categories == [
        "prophetic_attribution",
        "hadith_grading",
        "fiqh_ruling",
        "aqeedah_proposition",
        "narrator_disambiguation",
    ]
    assert config.confidence.base.rule == 0.95
    assert config.confidence.base.llm == 0.75
    assert config.confidence.agreement.agree == 1.2
    assert config.entries.regex == "(?<![٠-٩(/])([٠-٩]+) ?- "
    assert config.entries.start_page == 21
    assert config.llm.provider == "null"
    assert config.llm.temperature == 0
    assert config.features.semantic_search is False
    assert config.features.camel_tools is False
    assert config.origin.overrides == []


def test_book_override_merges_without_dropping_defaults():
    config = load_config(SAMPLE_PUB_ID)
    overrides = config.origin.overrides
    assert [(o.pages or o.blocks, o.origin) for o in overrides] == [
        ((3, 16), "editor_text"),
        ((17, 17), "transmission_isnad"),
        (("b000093", "b000093"), "transmission_isnad"),
        (("b000098", "b000587"), "author_text"),
        (("b000588", "b000589"), "transmission_isnad"),
    ]
    assert config.review == load_config().review
    assert config.entries == load_config().entries


def test_nested_override_keeps_sibling_keys(config_dir: Path):
    (config_dir / "books" / "pub_TEST.yaml").write_text("review:\n  threshold:\n    default: 0.9\n")
    config = load_config("pub_TEST", config_dir)
    assert config.review.threshold.default == 0.9
    assert config.review.threshold.overrides == {"fiqh_ruling": 0.95}
    assert len(config.review.sensitive_categories) == 5


def test_book_without_override_file_uses_defaults():
    assert load_config("pub_WITHOUT_OVERRIDES").config_hash == load_config().config_hash


def test_config_hash_is_stable():
    first = load_config(SAMPLE_PUB_ID).config_hash
    assert first.startswith("sha256:") and len(first) == len("sha256:") + 64
    assert load_config(SAMPLE_PUB_ID).config_hash == first


def test_config_hash_changes_with_one_value(config_dir: Path):
    before = load_config(config_dir=config_dir).config_hash
    default = config_dir / "default.yaml"
    default.write_text(default.read_text(encoding="utf-8").replace("start_page: 21", "start_page: 22"))
    assert load_config(config_dir=config_dir).config_hash != before


def test_book_override_changes_config_hash():
    assert load_config(SAMPLE_PUB_ID).config_hash != load_config().config_hash


def test_unknown_key_raises_clear_error(config_dir: Path):
    (config_dir / "books" / "pub_TEST.yaml").write_text("review:\n  treshold_typo: 0.5\n")
    with pytest.raises(ConfigError, match=r"pub_TEST\.yaml(.|\n)*treshold_typo(.|\n)*Extra inputs"):
        load_config("pub_TEST", config_dir)


def test_unknown_top_level_key_raises(config_dir: Path):
    (config_dir / "books" / "pub_TEST.yaml").write_text("unexpected: true\n")
    with pytest.raises(ConfigError, match="unexpected"):
        load_config("pub_TEST", config_dir)


@pytest.mark.parametrize(
    "override, message",
    [
        ("- {origin: editor_text, note: x}", "exactly one of"),
        ("- {pages: [1, 2], blocks: [b1, b2], origin: editor_text, note: x}", "exactly one of"),
        ("- {pages: [5, 3], origin: editor_text, note: x}", "reversed"),
        ("- {pages: [1, 2], origin: invented_origin, note: x}", "origin"),
    ],
)
def test_invalid_origin_override_rejected(config_dir: Path, override: str, message: str):
    (config_dir / "books" / "pub_TEST.yaml").write_text(f"origin:\n  overrides:\n    {override}\n")
    with pytest.raises(ConfigError, match=message):
        load_config("pub_TEST", config_dir)


def test_invalid_entry_regex_rejected(config_dir: Path):
    (config_dir / "books" / "pub_TEST.yaml").write_text("entries:\n  regex: '([0-9'\n")
    with pytest.raises(ConfigError, match="invalid regular expression"):
        load_config("pub_TEST", config_dir)


def test_pub_id_cannot_escape_config_folder():
    with pytest.raises(ConfigError, match="invalid pub_id"):
        load_config("../default")


def test_missing_default_config(tmp_path: Path):
    with pytest.raises(ConfigError, match="default configuration not found"):
        load_config(config_dir=tmp_path)


def test_config_is_immutable():
    config = load_config()
    with pytest.raises(Exception, match="frozen"):
        config.entries.start_page = 1  # type: ignore[misc]
