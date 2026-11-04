import json
from pathlib import Path

import pytest

from ilm_engine.nlp.normalize import HONORIFIC_TOKEN, NORMALIZER_VERSION, normalize, normalize_with_map

DATA = Path(__file__).resolve().parents[1] / "data" / "demo_book_daraqutni.json"


def sample_texts() -> dict[str, str]:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    return {block["b"]: block["text"] for page in data["content"]["pages"] for block in page["blocks"]}


@pytest.fixture(scope="module")
def texts() -> dict[str, str]:
    return sample_texts()


def test_diacritic_variants_share_one_key():
    assert normalize("الدَّارقطني") == normalize("الدارقطني") == normalize("الدَّارَقُطْنِيّ") == "الدارقطني"


def test_honorific_forms_share_one_token():
    written = normalize("رسول اللَّه -صلى الله عليه وسلم-")
    assert written == normalize("رسول الله ﷺ") == f"رسول الله {HONORIFIC_TOKEN}"
    assert normalize("النبي صلى الله عليه وآله وسلم قال") == f"النبي {HONORIFIC_TOKEN} قال"
    assert normalize("النبي -صلى اللَّه عليه وسلم- قال") == f"النبي {HONORIFIC_TOKEN} قال"


def test_allah_spellings():
    assert normalize("اللَّه") == normalize("اللّه") == normalize("الله") == "الله"
    shadda_fatha = "اللَّه"
    fatha_shadda = "اللَّه"
    assert normalize(shadda_fatha) == normalize(fatha_shadda) == "الله"


@pytest.mark.parametrize(
    "original, expected",
    [
        ("أسلمت", "اسلمت"),
        ("إسناده", "اسناده"),
        ("آخر", "اخر"),
        ("ٱلحمد", "الحمد"),
        ("فى الكتاب", "في الكتاب"),
        ("مؤمن", "مومن"),
        ("سائل", "سايل"),
        ("الإصابة", "الاصابه"),
        ("قـــال", "قال"),
        ("علىٰ", "علي"),
        ("سنة ٣٨٥", "سنه 385"),
        ("رقم ۱۲", "رقم 12"),
        ("  هند \n بنت\tعتيق  ", "هند بنت عتيق"),
        ("هند‏بنت", "هندبنت"),
    ],
)
def test_search_rules(original, expected):
    assert normalize(original) == expected


def test_title_variants_equal_after_normalization():
    assert normalize("الإخوة والأخوات") == normalize("الأُخوة والأَخوات") == normalize("الاُخوة والاخوات")


def test_match_profile_keeps_ta_marbuta():
    assert normalize("الإصابة", profile="match") == "الاصابة"
    assert normalize("الإصابة", profile="search") == "الاصابه"


def test_unknown_profile_rejected():
    with pytest.raises(ValueError, match="profile"):
        normalize("هند", profile="loose")  # type: ignore[arg-type]


def test_original_text_unchanged():
    original = "أَسْلَمَتْ"
    normalize(original)
    assert original == "أَسْلَمَتْ"


def test_empty_text():
    result = normalize_with_map("")
    assert result.text == "" and result.starts == () and result.ends == ()


def test_index_map_property_on_b000135(texts):
    """Every normalized character maps to the original character it came from."""
    original = texts["b000135"]
    result = normalize_with_map(original)
    assert len(result.text) == len(result.index_map) == len(result.ends)
    for i, char in enumerate(result.text):
        start, end = result.starts[i], result.ends[i]
        assert 0 <= start < end <= len(original)
        if char == " ":
            assert original[start:end].strip() == "" or HONORIFIC_TOKEN in normalize(original[start:end])
        else:
            assert char in normalize(original[start:end]), (i, char, original[start:end])
    assert list(result.starts) == sorted(result.starts)


def test_normalized_match_maps_back_to_original_quote(texts):
    original = texts["b000135"]
    result = normalize_with_map(original)
    for normalized_quote, quote, start, end in [
        ("اسلمت", "أسلمت", 60, 65),
        ("ولم يرو عنها شيء", "ولم يُروَ عنها شيءٌ", 78, 97),
    ]:
        position = result.text.index(normalized_quote)
        assert result.to_original(position, position + len(normalized_quote)) == (start, end)
        assert original[start:end] == quote


def test_honorific_maps_to_whole_original_phrase():
    original = "رسول اللَّه -صلى الله عليه وسلم- قال"
    result = normalize_with_map(original)
    position = result.text.index(HONORIFIC_TOKEN)
    start, end = result.to_original(position, position + len(HONORIFIC_TOKEN))
    assert original[start:end].strip() == "-صلى الله عليه وسلم-"


def test_to_original_rejects_bad_span():
    result = normalize_with_map("هند")
    with pytest.raises(ValueError):
        result.to_original(2, 1)
    with pytest.raises(ValueError):
        result.to_original(0, 4)


def test_map_is_consistent_for_every_sample_block(texts):
    for block_id, original in texts.items():
        result = normalize_with_map(original)
        assert result.text == normalize(original), block_id
        assert all(0 <= s < e <= len(original) for s, e in zip(result.starts, result.ends, strict=True)), (
            block_id
        )
        assert HONORIFIC_TOKEN not in original


def test_sample_honorific_count(texts):
    # EC-062: written out 134 times plainly, plus 3 times with diacritics ("صلى اللَّه عليه وسلم");
    # the ﷺ glyph does not occur.
    assert sum(normalize(text).count(HONORIFIC_TOKEN) for text in texts.values()) == 137
    assert not any("ﷺ" in text for text in texts.values())


def test_version():
    assert NORMALIZER_VERSION == "1.0.0"
