import pytest

from ilm_engine.nlp.arabic_digits import parse_locator, to_arabic_digits, to_int, words_to_int


@pytest.mark.parametrize(
    "text, expected", [("٧٥", 75), ("٣٢", 32), ("٠", 0), (" ٣٨٥ ", 385), ("۱۲", 12), ("1413", 1413)]
)
def test_to_int(text, expected):
    assert to_int(text) == expected


@pytest.mark.parametrize("text", ["", "٣٢ - ", "٣a", "-٥", "٣.٥", "²"])
def test_to_int_rejects_non_numbers(text):
    with pytest.raises(ValueError):
        to_int(text)


def test_to_arabic_digits():
    assert to_arabic_digits(32) == "٣٢"
    assert to_arabic_digits(0) == "٠"
    assert to_int(to_arabic_digits(1413)) == 1413


@pytest.mark.parametrize("value", [-1, 1.5, True, "٣"])
def test_to_arabic_digits_rejects_invalid(value):
    with pytest.raises(ValueError):
        to_arabic_digits(value)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("خمس وثمانين وثلاث مئة", 385),
        ("سنةٍ خمسٍ وثمانين وثلاث مئة", 385),  # b000049, with tanwin and a leading "سنة"
        ("خَمْسٍ وَثَمَانِينَ وَثَلاثِ مِائَةٍ", 385),
        ("خمس وثمانين وثلاثمائة", 385),
        ("ثلاثة", 3),
        ("عشرة", 10),
        ("ثلاثة عشر", 13),
        ("أحد عشر", 11),
        ("اثنا عشر", 12),
        ("عشرين", 20),
        ("خمس وعشرين", 25),
        ("مئة", 100),
        ("مائتين", 200),
        ("خمس مئة", 500),
        ("تسعمائة وتسعة وتسعين", 999),
        ("ألف وأربعمائة وثلاثة عشر", 1413),
        ("ثلاثة آلاف", 3000),
        ("ألفين", 2000),
        ("سنة ست وخمسين ومائة للهجرة", 156),
    ],
)
def test_words_to_int(text, expected):
    assert words_to_int(text) == expected


def test_words_to_int_rejects_text_without_numbers():
    with pytest.raises(ValueError, match="no Arabic number words"):
        words_to_int("هند بنت عتيق")


def test_words_to_int_rejects_unknown_word_inside_phrase():
    with pytest.raises(ValueError, match="unknown word"):
        words_to_int("خمس هند وثمانين")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("(٨/ ١٥٧)", (8, 157)),
        ("(٨/١٥٧)", (8, 157)),
        ("٣/ ١٦٦", (3, 166)),
        ("(١٥٧)", (None, 157)),
        ("( 8 / 157 )", (8, 157)),
    ],
)
def test_parse_locator(raw, expected):
    assert parse_locator(raw) == expected


@pytest.mark.parametrize("raw", ["", "(ص: ١٣٣)", "(رقم: ١٣٨٢)", "(٨/)", "٨ - "])
def test_parse_locator_rejects_other_forms(raw):
    with pytest.raises(ValueError):
        parse_locator(raw)
