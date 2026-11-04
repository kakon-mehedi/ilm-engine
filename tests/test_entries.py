import re

import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.units import detect_entries
from ilm_engine.processors.origin import assign

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def origins(sample_book):
    return assign(sample_book, load_config(PUB_ID)).blocks


@pytest.fixture(scope="module")
def detection(sample_book, origins):
    return detect_entries(sample_book, origins, load_config(PUB_ID))


def test_exactly_75_entries_without_gaps_or_duplicates(detection):
    assert [entry.entry_no for entry in detection.entries] == list(range(1, 76))
    assert detection.issues == []
    assert {entry.found_by for entry in detection.entries} == {"regex"}


def test_entry_32_mid_sentence(detection, sample_book):
    entry = detection.by_number()[32]
    anchor = entry.anchors[0]
    assert anchor.block_id == "b000294" and anchor.quote.startswith("٣٢ - أروى")
    assert anchor.start == 23
    assert sample_book.block("b000294").text[anchor.start : anchor.end] == anchor.quote


def test_entries_18_and_19_share_a_block(detection):
    numbers = detection.by_number()
    assert numbers[18].block_id == numbers[19].block_id == "b000217"
    assert numbers[18].anchors[0].end <= numbers[19].anchors[0].start


def test_entry_8_whole_block(detection):
    [anchor] = detection.by_number()[8].anchors
    assert (anchor.block_id, anchor.start, anchor.end) == ("b000135", 0, 102)


def test_entry_31_stops_before_32(detection):
    first = detection.by_number()[31].anchors[0]
    assert first.block_id == "b000294" and first.end <= 23 and first.quote.startswith("٣١ - وأُمية")


def test_multi_block_entry(detection, sample_book):
    multi = [entry for entry in detection.entries if len(entry.anchors) > 1]
    assert multi, "some entries continue into following author blocks"
    for entry in multi:
        assert all(sample_book.block(anchor.block_id).kind == "text" for anchor in entry.anchors)


def test_editor_numbered_lists_not_counted(sample_book, origins):
    """The editor's numbered lists (pages 6–12, e.g. b000022 "١ - ") match the pattern but are not entries."""
    config = load_config(PUB_ID)
    assert re.search(config.entries.regex, sample_book.block("b000022").text)
    everything = {block_id: "author_text" for block_id in origins}
    unfiltered = detect_entries(
        sample_book,
        everything,
        config.model_copy(update={"entries": config.entries.model_copy(update={"start_page": 1})}),
    )
    assert len(unfiltered.entries) > 75
    entries = detect_entries(sample_book, origins, config).entries
    assert all(
        origins[e.block_id] == "author_text" and sample_book.block(e.block_id).page >= 21 for e in entries
    )


def test_gap_reported_after_fallback(sample_book, origins):
    blanked = {**origins, "b000294": "editor_text"}  # hide entries 31 and 32
    detection = detect_entries(sample_book, blanked, load_config(PUB_ID))
    gaps = sorted(issue.details["entry_no"] for issue in detection.issues if issue.code == "numbering_gap")
    assert gaps == [31, 32]


def test_fallback_rescues_a_missed_number(sample_book, origins):
    config = load_config(PUB_ID)
    strict = config.model_copy(
        update={"entries": config.entries.model_copy(update={"regex": r"(?<![٠-٩(/:])([٠-٩]+) - (?!أروى)"})}
    )
    detection = detect_entries(sample_book, origins, strict)
    rescued = detection.by_number()[32]
    assert rescued.found_by == "fallback" and rescued.block_id == "b000294"
    assert [i for i in detection.issues if i.code == "numbering_gap"] == []
