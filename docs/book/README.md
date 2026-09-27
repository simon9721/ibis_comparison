# Semiconductor Modeling (Leventhal & Green, Springer 2006) as JSON

Extracted from `silicon modeling book.pdf` (OCR text) by `scripts/extract_book_json.py`.

* `sections.json`: numbered sections with printed and PDF page numbers.
* `pages.json`: one record per PDF page with the printed page number, chapter, section in force and the OCR text.
* `index.json`: PDF pages per keyword.
* `citations.md` / `citations.json`: the passages that support each finding of the stress investigation.

Cite as printed page (p.) with the PDF page in brackets: the PDF page is the printed page plus 10 to 15 depending on the part.
`py -3.14 scripts/extract_book_json.py --find "phrase"` greps with page references.
