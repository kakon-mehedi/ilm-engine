import pytest

from ilm_engine.config import load_config
from ilm_engine.processors.citations import extract, title_key
from ilm_engine.processors.origin import assign

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def result(sample_book):
    config = load_config(PUB_ID)
    return extract(sample_book, assign(sample_book, config).blocks, config)


def test_counts_by_raw_title(result):
    counts = result.counts_by_title()
    # الإصابة: 145 quoted citations in the footnotes (the ticket and DECISIONS §7 say 144; every one of the
    # 145 is a real citation, see T-053 follow-ups). The other counts match.
    assert counts["الإصابة"] == 145
    assert (counts["أسد الغابة"], counts["السير"], counts["الطبقات الكبرى"]) == (67, 59, 45)
    assert (counts["الاستيعاب"], counts["التهذيب"]) == (31, 32)


def test_b000109_tabaqat_locator_and_anchor(result, sample_book):
    [citation] = [
        c for c in result.citations if c.anchor.block_id == "b000109" and c.title_raw == "الطبقات الكبرى"
    ]
    [locator] = citation.locators
    assert (locator.volume, locator.page, locator.raw) == (8, 19, "(٨/ ١٩)")
    anchor = citation.anchor
    assert sample_book.block("b000109").text[anchor.start : anchor.end] == anchor.quote == "الطبقات الكبرى"
    assert citation.context == "footnote" and citation.origin == "editor_footnote"


def test_alias_resolution(result):
    by_title = {c.title_raw: c for c in result.citations}
    assert (
        by_title["الإصابة"].resolution == "alias_table" and by_title["الإصابة"].title_normalized == "الاصابه"
    )
    assert by_title["الطبقات"].work_id == by_title["الطبقات الكبرى"].work_id


def test_ambiguous_short_title(result):
    tahdhib = [c for c in result.citations if c.title_raw == "التهذيب"]
    assert {c.resolution for c in tahdhib} == {"unresolved"} and {c.work_id for c in tahdhib} == {None}
    issues = [i for i in result.issues if i.code == "ambiguous_entity" and i.details["title"] == "التهذيب"]
    assert len(issues) == 32 and len(issues[0].details["candidates"]) == 2


def test_manuscript_is_not_a_work(result):
    assert not any(title_key(c.title_raw) == title_key("الأصل") for c in result.citations)


def test_chained_locators_and_author_hint(result):
    [kabir] = [c for c in result.citations if c.anchor.block_id == "b000228" and c.title_raw == "الكبير"]
    assert [(loc.volume, loc.page, loc.number) for loc in kabir.locators] == [
        (3, 166, None),
        (None, None, 3258),
    ]
    [hinted] = [c for c in result.citations if c.anchor.block_id == "b000215" and c.title_raw == "المؤتلف"]
    assert hinted.author_hint == "للمصنّف"  # "المؤتلف" (٣/ ١٢٤٢) للمصنّف


def test_self_citation_resolves_to_this_book(result):
    own = [c for c in result.citations if title_key(c.title_raw) == title_key("الأخوة")]
    this = next(w for w in result.works if w.status == "this_book")
    assert own and {c.work_id for c in own} == {this.work_id}


def test_unknown_titles_become_stubs(result):
    stubs = {w.work_id for w in result.works if w.status == "stub"}
    assert any(c.work_id in stubs and c.resolution == "unresolved" for c in result.citations)


def test_every_anchor_is_exact(result, sample_book):
    for citation in result.citations:
        anchor = citation.anchor
        assert sample_book.block(anchor.block_id).text[anchor.start : anchor.end] == anchor.quote
