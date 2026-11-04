import json
from pathlib import Path

GOLD = Path(__file__).resolve().parents[1] / "eval" / "gold_index_sample.json"


def test_gold_sample_is_complete_and_well_formed():
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    entries = gold["entries"]
    assert gold["source"] == "printed_index"
    assert gold["pdf_pages"] == [76, 77, 78, 79]
    assert gold["entry_count"] == len(entries) == 75
    assert sorted(entry["entry_no"] for entry in entries) == list(range(1, 76))
    for entry in entries:
        assert set(entry) == {"name", "entry_no", "pdf_page", "line", "uncertain"}
        assert entry["name"].strip() and entry["pdf_page"] in gold["pdf_pages"]
        assert entry["uncertain"] is False


def test_known_rows():
    by_no = {
        entry["entry_no"]: entry["name"] for entry in json.loads(GOLD.read_text(encoding="utf-8"))["entries"]
    }
    assert by_no[1] == "فاطمة بنت رسول الله ﷺ"
    assert by_no[8] == "هند بنت عتيق"
    assert by_no[9] == "هند بن أبي هالة"
    assert by_no[32] == "أروى بنت الحارث"
    assert by_no[75] == "عبدالله الأصغر"
