# Evaluation data

This folder holds **evaluation data only**. Nothing here is pipeline input: the pipeline never reads it
while enriching a book. It is used by `ilm-engine eval` (T-131, T-132) to measure entity extraction
against human ground truth.

## `gold_index_sample.json`

A transcription of the editor's printed index of narrators with biographies
(فهرس الرواة المترجم لهم في الكتاب) from the scan of the sample book, PDF pages 76–79.

- **What it contains:** all 75 index rows, each with the person's `name` as printed, the `entry_no`
  (the index column is رقم الترجمة, the biographical entry number 1–75, not a page number),
  the `pdf_page` and the `line` on that page.
- **Why it is ground truth:** the editor compiled the index by hand, independently of our pipeline.
  The scan has no text layer and OCR is out of scope, so the rows were transcribed from 200 dpi
  renders of the pages.
- **How it was checked:** every entry number 1–75 occurs exactly once, and each name was confirmed
  against the book text: the person's name appears right after the matching `N - ` entry marker in
  the author's text (75 of 75).
- **Uncertain readings:** none; each row carries `uncertain: false` so a later reviewer can flag one.

PDF pages 73–75 hold the hadith index (فهرس الأحاديث) and page 80 the general contents
(الفهرس الإجمالي); they are not part of this sample.
