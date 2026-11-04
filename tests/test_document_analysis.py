from ilm_engine.processors.document_analysis import analyze, resolvable_refs


def test_report_counts(sample_book):
    report, _ = analyze(sample_book)
    assert report.block_total == 594
    assert report.block_counts == {"footnote": 317, "heading": 15, "text": 260, "toc_heading": 2}
    assert report.page_count_held == 68 and report.page_count_claimed == 72
    assert report.printed_page_range == (3, 72)
    assert report.ref_count == 300 and report.refs_from_footnotes == 0
    assert report.continued_footnotes == 16
    assert report.span_class_counts == {"c1": 8, "c2": 230, "c4": 2, "c5": 64}
    assert report.source_quality.claimed_pages == 72


def test_all_refs_resolvable(sample_book):
    assert resolvable_refs(sample_book) == (300, 300)


def test_pages_and_pdf(sample_book):
    report, _ = analyze(sample_book)
    assert report.missing_printed_pages == [1, 2, 4, 18]
    assert report.pdf_page_count == 80
    assert report.pdf_pages_not_in_json == [1, 2, 4, 18, 73, 74, 75, 76, 77, 78, 79, 80]


def test_page_count_mismatch_issue(sample_book):
    report, issues = analyze(sample_book)
    [issue] = [i for i in issues if i.code == "page_count_mismatch"]
    assert issue.details["claimed"] == 72 and issue.details["held"] == 68
    assert issue.details["source_passed"] is True and issue.details["short_pct"] == 5.56
    assert issue.details["tolerance_pct"] == 5.0
    assert "exceeds its 5% tolerance" in issue.message
    assert issue.issue_id in report.issues and issue.target_id == sample_book.book.pub_ref


def test_empty_and_duplicate_blocks(sample_book):
    report, _ = analyze(sample_book)
    assert report.empty_blocks == []
    for group in report.duplicate_blocks:
        texts = {sample_book.block(block_id).text for block_id in group}
        assert len(group) > 1 and len(texts) == 1


def test_deterministic(sample_book):
    assert analyze(sample_book) == analyze(sample_book)
