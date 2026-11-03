# Sample input

The sample book used to develop and test the pipeline was provided by the client and is **not committed** to this repository (the files in this folder are git-ignored).

To run the pipeline, place these two files here:

| File | Description |
|---|---|
| `demo_book_daraqutni.json` | Digitized book in the archive's JSON format (`src-shamela`, `af_schema 3.0`, revision 6): *al-Ikhwa wa al-Akhawat* by al-Daraqutni (d. 385 AH), ed. Basim Faysal al-Jawabira, Dar al-Raya, Riyadh, 1413 AH / 1993 |
| `demo_book_daraqutni_v1.pdf` | Scan of the same printed edition (80 pages, image-only; `scan_page` in the JSON equals the PDF page number) |

Expected properties (checked by the tests): 68 pages (`n` 3–72), 594 blocks (260 text, 317 footnote, 15 heading, 2 toc_heading), 300 footnote references.

The pipeline treats this folder as **read-only**: no step ever writes here, and an integrity test fails if any file in it changes during a run.
