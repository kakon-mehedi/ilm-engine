import json
import re
from pathlib import Path

import pytest

from ilm_engine.nlp.nasab import clean, parse_name

DATA = Path(__file__).resolve().parents[1] / "data" / "demo_book_daraqutni.json"
ENTRY = re.compile(r"(?<![٠-٩(/])([٠-٩]+) ?- ")


@pytest.fixture(scope="module")
def entries() -> dict[int, tuple[str, int]]:
    """Entry number → (block text, offset just after "N - ") for the 75 sample entries."""
    data = json.loads(DATA.read_text(encoding="utf-8"))
    found: dict[int, tuple[str, int]] = {}
    digits = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    for page in data["content"]["pages"]:
        if page["n"] < 21:
            continue
        for block in page["blocks"]:
            if block["kind"] == "text":
                for match in ENTRY.finditer(block["text"]):
                    found.setdefault(int(match.group(1).translate(digits)), (block["text"], match.end()))
    return found


def parse_entry(entries, number):
    text, start = entries[number]
    name = parse_name(text[start:], offset=start)
    assert name is not None
    assert text[name.span[0] : name.span[1]] == name.raw
    return name


def test_ticket_example_hind_bint_atiq():
    name = parse_name("هند بنت عتيق بن عابد (١) بن عبد اللَّه بن عمر بن مخزوم؛ أسلمت (٢) وتزوجت")
    assert name.ism == "هند"
    assert name.gender == "f"
    assert list(name.chain) == ["عتيق", "عابد", "عبد الله", "عمر", "مخزوم"]
    assert name.raw == "هند بنت عتيق بن عابد (١) بن عبد اللَّه بن عمر بن مخزوم"


def test_ticket_example_daraqutni():
    name = parse_name("أبو الحسن علي بن عمر بن أحمد الدارقطني")
    assert name.kunya == "أبو الحسن"
    assert name.ism == "علي"
    assert list(name.chain) == ["عمر", "أحمد"]
    assert list(name.nisba) == ["الدارقطني"]
    assert name.gender == "m"


def test_all_75_sample_entries_parse(entries):
    assert sorted(entries) == list(range(1, 76))
    for number in entries:
        parse_entry(entries, number)


def test_entry_8_offsets_in_block(entries):
    name = parse_entry(entries, 8)
    assert name.span == (4, 58)


@pytest.mark.parametrize(
    "number, kunya, ism, laqab, chain, nisba, gender",
    [
        (1, None, "فاطمة", None, [], [], "f"),
        (4, "أم كلثوم", None, None, [], [], "f"),  # "وأم كلثوم": conjunction stripped
        (7, None, "إبراهيم", None, ["رسول الله"], [], "m"),
        (9, None, "هند", None, [], [], "unknown"),  # male: gender is resolved later by relations
        (15, None, "زينب", None, ["علي", "أبي طالب"], [], "f"),
        (29, "أبو سفيان", None, None, [], [], "m"),
        (35, None, "عبيد الله", None, [], [], "unknown"),
        (39, "أم حبيب", None, None, [], [], "f"),
        (59, None, "عبد الرحمن", "الأكبر", [], [], "unknown"),
        (61, "أم الوليد", None, None, ["عمر"], [], "f"),
        (66, None, "عبد الله", "أكبر", ["أبي جهم", "حذيفة"], ["العدوي"], "m"),
        (67, None, "حارثة", None, ["وهب"], ["الخزاعي"], "m"),
        (69, None, "عبد الرحمن", None, ["يزيد", "جارية"], ["الأنصاري"], "m"),
        (70, None, "عبد الرحمن", "الأوسط", ["عمر"], [], "m"),
        (75, None, "عبد الله", "الأصغر", ["عمر"], [], "m"),
    ],
)
def test_sample_entries(entries, number, kunya, ism, laqab, chain, nisba, gender):
    name = parse_entry(entries, number)
    assert (name.kunya, name.ism, name.laqab, list(name.chain), list(name.nisba), name.gender) == (
        kunya,
        ism,
        laqab,
        chain,
        nisba,
        gender,
    )


def test_trailing_footnote_marker_not_in_surface(entries):
    assert parse_entry(entries, 39).raw == "أم حَبيب"


def test_conjunction_not_in_surface(entries):
    name = parse_entry(entries, 44)  # "وَصَفِيّة"
    assert name.ism == "صفية" and name.raw == "صَفِيّة"


def test_ibn_inside_chain_treated_as_bin():
    name = parse_name("عبد الله ابن قرط بن رزاح")
    assert name.ism == "عبد الله" and list(name.chain) == ["قرط", "رزاح"] and name.gender == "m"


def test_stops_at_verbs_and_punctuation():
    assert parse_name("القاسم؛ وبه كان يكنى").raw == "القاسم"
    assert parse_name("زينب بنت علي بن أبي طالب، فزوجها أبوها").chain == ("علي", "أبي طالب")
    assert parse_name("الحارث بن العباس أمه هذلية").raw == "الحارث بن العباس"


def test_dangling_connector_not_consumed():
    name = parse_name("علي بن")
    assert name.raw == "علي" and name.chain == ()


def test_waw_names_keep_their_waw():
    assert parse_name("وهب بن منبه").ism == "وهب"
    assert parse_name("وائل بن حجر").ism == "وائل"


def test_no_name():
    assert parse_name("") is None
    assert parse_name("وقال هشام") is None
    assert parse_name("(١)") is None


def test_offset_applied():
    assert parse_name("زينب بنت عمر", offset=10).span == (10, 22)


def test_to_person_name_contract():
    person = parse_name("أبو الحسن علي بن عمر بن أحمد الدارقطني").to_person_name()
    assert person.kunya == "أبو الحسن" and person.nasab == ["عمر", "أحمد"] and person.nisba == ["الدارقطني"]
    assert person.full_surface == "أبو الحسن علي بن عمر بن أحمد الدارقطني"


def test_clean_keeps_letters():
    assert clean("عبد اللَّه") == "عبد الله"
    assert clean("أُمامة") == "أمامة"
