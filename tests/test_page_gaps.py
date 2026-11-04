import pytest

from ilm_engine.config import load_config
from ilm_engine.processors.document_analysis import analyze, classify_gaps

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def analysis(sample_book):
    return analyze(sample_book, load_config(PUB_ID))


def test_missing_pages_classified(analysis):
    report, issues = analysis
    assert report.missing_printed_pages == [1, 2, 4, 18]
    gaps = {issue.details["page"]: issue.details["class"] for issue in issues if issue.code == "missing_page"}
    assert gaps == {1: "cover", 2: "publisher_page", 4: "basmala", 18: "blank"}
    assert {issue.severity for issue in issues if issue.code == "missing_page"} == {"info"}
    assert all(i.details["evidence"] == "scan_page" for i in issues if i.code == "missing_page")


def test_page_count_mismatch_downgraded(analysis):
    _, issues = analysis
    [issue] = [i for i in issues if i.code == "page_count_mismatch"]
    assert issue.severity == "info" and "no content pages missing" in issue.message.lower()
    assert issue.details["content_pages_missing"] == []


def test_pdf_extra_pages_are_printed_indexes(analysis):
    report, _ = analysis
    assert {key: value for key, value in report.page_classes.items() if key.startswith("scan:")} == {
        f"scan:{page}": "printed_indexes" for page in range(73, 81)
    }
    assert report.page_classes["printed:18"] == "blank"


def test_without_override_gaps_are_reported_unclassified(sample_book):
    report, issues = analyze(sample_book, load_config())
    gaps = [i for i in issues if i.code == "missing_page"]
    assert [i.details["page"] for i in gaps] == [1, 2, 4, 18]
    assert {i.details["class"] for i in gaps} == {"unknown"} and {i.severity for i in gaps} == {"warning"}
    [mismatch] = [i for i in issues if i.code == "page_count_mismatch"]
    assert mismatch.severity == "warning"


def test_classify_gaps():
    pages = load_config(PUB_ID).pages
    assert classify_gaps([1, 50], pages) == {1: "cover", 50: "unknown"}
