"""Document analysis (step `document_analysis`): counts, gaps and source-quality reconciliation.

Produces `document_report.json` (03-data-contracts §5) and its issues. Nothing here interprets content;
it measures what the canonical book holds and compares it with what the source claims.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.config import NON_CONTENT_PAGES, Config, PagesConfig
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import DocumentReport, Issue

STEP = "document_analysis"


def classify_gaps(missing: list[int], pages: PagesConfig) -> dict[int, str]:
    """Class of each missing printed page from the per-book override; `unknown` without one."""
    return {page: pages.gaps.get(page, "unknown") for page in missing}


def analyze(book: CanonicalBook, config: Config | None = None) -> tuple[DocumentReport, list[Issue]]:
    pages_config = config.pages if config is not None else PagesConfig()
    pub_ref = book.book.pub_ref
    blocks = book.blocks_in_order()
    numbers = sorted({page.n for page in book.pages})
    held, claimed = len(book.pages), book.metadata.claimed_page_count
    missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers)) if numbers else []
    pdf_count = book.scan.get("page_count")
    scan_pages = {page.scan_page for page in book.pages}

    by_text: dict[str, list[str]] = defaultdict(list)
    for block in blocks:
        if block.text.strip():
            by_text[block.text].append(block.block_id)

    issues: list[Issue] = []
    gap_classes = classify_gaps(missing, pages_config)
    for page, page_class in gap_classes.items():
        non_content = page_class in NON_CONTENT_PAGES
        issues.append(
            make_issue(
                pub_ref,
                "missing_page",
                "info" if non_content else "warning",
                "page",
                str(page),
                f"Printed page {page} is not in the source ({page_class}).",
                STEP,
                details={
                    "page": page,
                    "class": page_class,
                    "evidence": "scan_page" if page in pages_config.gaps else None,
                },
            )
        )
    content_missing = [
        page for page, page_class in gap_classes.items() if page_class not in NON_CONTENT_PAGES
    ]
    if claimed is not None and claimed != held:
        quality = book.quality
        short_pct = round(100 * (claimed - held) / claimed, 2)
        tolerance = quality.tolerance if quality else None
        note = ""
        if (
            quality
            and quality.passed
            and tolerance
            and tolerance.endswith("%")
            and short_pct > float(tolerance[:-1])
        ):
            note = f" The source check passed although {short_pct}% short exceeds its {tolerance} tolerance."
        if not content_missing:
            note += " No content pages missing: every gap is a non-content page."
        issues.append(
            make_issue(
                pub_ref,
                "page_count_mismatch",
                "warning" if content_missing else "info",
                "book",
                pub_ref,
                f"Source claims {claimed} pages, {held} held; missing printed pages: "
                f"{', '.join(map(str, missing)) or 'none'}.{note}",
                STEP,
                details={
                    "claimed": claimed,
                    "held": held,
                    "missing_pages": missing,
                    "source_passed": quality.passed if quality else None,
                    "short_pct": short_pct,
                    "tolerance_pct": float(tolerance[:-1]) if tolerance and tolerance.endswith("%") else None,
                    "gaps": {str(page): page_class for page, page_class in gap_classes.items()},
                    "content_pages_missing": content_missing,
                },
            )
        )

    report = DocumentReport(
        pub_ref=pub_ref,
        page_count_held=held,
        page_count_claimed=claimed,
        printed_page_range=(numbers[0], numbers[-1]) if numbers else (0, 0),
        missing_printed_pages=missing,
        pdf_page_count=pdf_count,
        pdf_pages_not_in_json=sorted(set(range(1, pdf_count + 1)) - scan_pages) if pdf_count else [],
        block_counts=dict(sorted(Counter(block.kind for block in blocks).items())),
        block_total=len(blocks),
        ref_count=sum(len(block.refs) for block in blocks),
        refs_from_footnotes=sum(len(block.refs) for block in blocks if block.kind == "footnote"),
        continued_footnotes=sum(block.continues for block in blocks),
        span_class_counts=dict(sorted(Counter(span.cls for block in blocks for span in block.spans).items())),
        empty_blocks=[block.block_id for block in blocks if not block.text.strip()],
        duplicate_blocks=[ids for ids in by_text.values() if len(ids) > 1],
        source_quality=book.quality,
        issues=[issue.issue_id for issue in issues],
        page_classes={
            **{f"printed:{page}": page_class for page, page_class in gap_classes.items()},
            **{
                f"scan:{page}": page_class
                for page, page_class in sorted(pages_config.pdf_extra_pages().items())
            },
        },
    )
    return report, issues


def resolvable_refs(book: CanonicalBook) -> tuple[int, int]:
    """(refs whose target block exists, all refs)."""
    refs = [ref for block in book.blocks.values() for ref in block.refs]
    return sum(ref.to in book.blocks for ref in refs), len(refs)
