"""Static, read-only reviewer view `review.html` (ADR-016): RTL Arabic, highlighted quotes, PDF links.

The page has no external resources, so it opens offline. Decisions are not made in the page; reviewers
record them in `review_decisions.json` and run `ilm-engine review apply`.
"""

from __future__ import annotations

from html import escape

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.enrichment.models import ReviewItem

REASON_LABELS = {
    "sensitive": "Sensitive (scholar review)",
    "discrepancy": "Discrepancy",
    "low_confidence": "Low confidence",
    "needs_llm": "Needs LLM",
    "structural_issue": "Structural issue",
}

_CSS = """
:root { --bg: #fbfaf7; --fg: #1d1d1f; --muted: #6b6b70; --card: #ffffff; --line: #e3e0d8; --mark: #ffe08a;
        --sensitive: #b42318; --accent: #1f5f8b; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #16171a; --fg: #ececef; --muted: #a0a0a8; --card: #202227; --line: #33353b; --mark: #6b5a1e;
          --sensitive: #f97066; --accent: #7cb8e4; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
       font: 16px/1.6 system-ui, "Noto Naskh Arabic", "Amiri", serif; }
header, main { max-width: 960px; margin: 0 auto; padding: 16px; }
h1 { font-size: 1.4rem; margin: 0 0 4px; }
.meta { color: var(--muted); font-size: .9rem; direction: ltr; text-align: left; }
article { background: var(--card); border: 1px solid var(--line); border-radius: 10px;
          padding: 14px 16px; margin: 12px 0; }
article.sensitive { border-inline-start: 4px solid var(--sensitive); }
.labels { direction: ltr; text-align: left; font-size: .85rem; color: var(--muted);
          display: flex; gap: 8px; flex-wrap: wrap; }
.label { border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; }
.label.sensitive { color: var(--sensitive); border-color: var(--sensitive); }
blockquote { margin: 10px 0; padding: 8px 12px; border-inline-start: 3px solid var(--line); }
mark { background: var(--mark); color: inherit; border-radius: 3px; }
a { color: var(--accent); }
"""


def _context(book: CanonicalBook, item: ReviewItem) -> str:
    parts = []
    for block_id in item.context_block_ids[:3]:
        block = book.blocks.get(block_id)
        if block is None:
            continue
        spans = sorted(
            (a.start, a.end) for a in item.anchors if a.block_id == block_id and not a.quote_truncated
        )
        html, position = [], 0
        for start, end in spans:
            if start < position:
                continue
            html.append(escape(block.text[position:start]))
            html.append(f"<mark>{escape(block.text[start:end])}</mark>")
            position = end
        html.append(escape(block.text[position:]))
        parts.append(
            f'<blockquote dir="rtl" lang="ar"><small>{escape(block_id)} · p.{block.page}</small><br>'
            f"{''.join(html)}</blockquote>"
        )
    return "".join(parts)


def render(book: CanonicalBook, items: list[ReviewItem], pdf_href: str | None = None) -> str:
    cards = []
    for item in items:
        labels = "".join(
            f'<span class="label{" sensitive" if reason == "sensitive" else ""}">'
            f"{escape(REASON_LABELS[reason])}</span>"
            for reason in item.reason
        )
        labels += "".join(
            f'<span class="label sensitive">{escape(category)}</span>' for category in item.sensitive
        )
        confidence = "—" if item.confidence is None else f"{item.confidence:.2f}"
        page = item.pdf.get("page") if item.pdf else None
        link = f' · <a href="{escape(pdf_href)}#page={page}">PDF page {page}</a>' if pdf_href and page else ""
        cards.append(
            f'<article class="{"sensitive" if item.sensitive else ""}" id="{escape(item.review_id)}">'
            f'<div class="labels">{labels}<span>{escape(item.target_kind)} {escape(item.target_id)}</span>'
            f"<span>priority {item.priority} · confidence {confidence} · "
            f"{escape(item.required_role)} · {escape(item.status)}</span>"
            f"{link}</div>{_context(book, item)}</article>"
        )
    return (
        '<!doctype html>\n<html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Review queue</title><style>{_CSS}</style></head><body>"
        f'<header><h1>Review queue</h1><p class="meta">{escape(book.book.pub_ref)} · {len(items)} items · '
        "decisions go to review_decisions.json, then <code>ilm-engine review apply</code></p></header>"
        f"<main>{''.join(cards)}</main></body></html>\n"
    )
