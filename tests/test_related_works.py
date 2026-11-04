import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.related_works import related_works, title_relation
from ilm_engine.processors.citations import extract
from ilm_engine.processors.origin import assign

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def inputs(sample_book):
    config = load_config(PUB_ID)
    origins = assign(sample_book, config).blocks
    return extract(sample_book, origins, config), origins, config


@pytest.fixture(scope="module")
def result(sample_book, inputs):
    citations, origins, config = inputs
    return related_works(sample_book, citations, origins, config)


def works_by_id(result):
    return {w.work_id: w for w in result.works}


def test_two_same_topic_works_from_preface(result, sample_book):
    same = [r for r in result.relations if r.type == "same_topic_as"]
    titles = {works_by_id(result)[r.object_work_id].title for r in same}
    assert titles == {"الأُخوة الذين رُويَ عنهم الحديث", "تسمية من رُويَ عنه من أولاد العشرة"}
    for relation in same:
        [anchor] = relation.evidence
        assert (
            anchor.block_id == "b000018"
            and relation.origin == "editor_text"
            and relation.assertion == "stated"
        )
        assert sample_book.block("b000018").text[anchor.start : anchor.end] == anchor.quote
    spans = sorted((r.evidence[0].start, r.evidence[0].end) for r in same)
    assert spans == [(151, 182), (216, 250)]


def test_editor_combined_edition(result):
    tahqiq = [r for r in result.relations if r.type == "tahqiq_of"]
    assert len(tahqiq) == 2
    edition = works_by_id(result)[tahqiq[0].subject_work_id]
    assert edition.title == "الرّواة من الأُخوة والأخوات" and edition.author_name == "باسم فيصل أحمد الجوابرة"
    assert (tahqiq[0].evidence[0].start, tahqiq[0].evidence[0].end) == (362, 389)


def test_every_cited_work_is_a_cites_edge(result, inputs):
    citations, _, _ = inputs
    this = next(w for w in result.works if w.status == "this_book")
    cited = {c.work_id for c in citations.citations if c.work_id and c.work_id != this.work_id}
    edges = {r.object_work_id: r for r in result.relations if r.type == "cites"}
    assert cited == set(edges) and all(r.subject_work_id == this.work_id for r in edges.values())
    isaba = next(w for w in result.works if w.title == "الإصابة في تمييز الصحابة")
    assert edges[isaba.work_id].count == 145 and len(edges[isaba.work_id].evidence) == 5


def test_title_patterns():
    assert title_relation("شرح صحيح البخاري") == ("sharh_of", "صحيح البخاري")
    assert title_relation("حاشية على الروض المربع") == ("hashiyah_of", "الروض المربع")
    assert title_relation("مختصر تاريخ دمشق") == ("mukhtasar_of", "تاريخ دمشق")
    assert title_relation("الإصابة") is None


def test_synthetic_sharh_citation_gives_candidate(sample_book, inputs):
    citations, origins, config = inputs
    footnote = sample_book.block("b000109")
    text = footnote.text + ' انظر "شرح صحيح البخاري" (٣/ ١٠).'
    changed = footnote.model_copy(update={"text": text})
    book = sample_book.model_copy(update={"blocks": {**sample_book.blocks, "b000109": changed}})
    result = related_works(book, extract(book, origins, config), origins, config)
    [sharh] = [r for r in result.relations if r.type == "sharh_of"]
    names = works_by_id(result)
    assert (
        names[sharh.subject_work_id].title == "شرح صحيح البخاري"
        and names[sharh.object_work_id].title == "صحيح البخاري"
    )
    assert (
        sharh.assertion == "inferred"
        and sharh.origin == "ai_generated"
        and sharh.review_status == "pending_review"
    )
