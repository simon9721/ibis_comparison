#!/usr/bin/env python3
"""Turn `silicon modeling book.pdf` (Leventhal & Green, Semiconductor Modeling, Springer 2006;
Acrobat paper-capture OCR, no bookmarks) into queryable JSON under docs/book/.

    docs/book/sections.json   every numbered section from the printed contents: number, title,
                              printed page, pdf page, chapter
    docs/book/pages.json      every pdf page: pdf_page, printed_page (parsed from the running
                              header), chapter, section (the deepest numbered heading in force),
                              text
    docs/book/index.json      keyword -> list of pdf pages, for the terms this project cares about

    py -3.14 scripts/extract_book_json.py
    py -3.14 scripts/extract_book_json.py --find "internal buffer delay"      # grep with page refs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
PDF = ROOT / "silicon modeling book.pdf"
OUT = ROOT / "docs" / "book"

KEYWORDS = [
    "C_comp", "Ccomp", "V-T", "Ramp", "dV/dt", "R_fixture", "V_fixture", "Vinh", "Vinl", "Vmeas",
    "Open_drain", "open drain", "open-drain", "Pullup", "Pulldown", "Miller", "pre-driver",
    "internal buffer delay", "lead-in", "black-box", "black box", "behavioral", "macromodel",
    "golden", "correlat", "threshold voltage", "saturation", "quiescent", "quasi-static",
    "superposition", "nonlinear", "propagation delay", "history", "internal node", "die capacitance",
    "pad capacitance", "Ku", "multiplier", "scaling", "transistor-level", "encrypted", "fixture",
    "entire waveform", "two waveforms", "reflected wave", "overshoot", "time step", "edge rate",
]


def load_pages():
    import fitz
    doc = fitz.open(str(PDF))
    return [page.get_text() for page in doc]


def printed_page(text: str):
    """The running header carries the printed page number: '116 \\nChapter 4' or
    '10. Key Concepts ... \\n303'. Take the first small integer in the first four lines."""
    for line in text.strip().splitlines()[:4]:
        m = re.fullmatch(r"\s*(\d{1,3})\s*", line)
        if m and 1 <= int(m.group(1)) <= 780:
            return int(m.group(1))
    return None


def parse_contents(pages):
    """Sections from the printed CONTENTS pages (pdf pages 6-13). The OCR puts each entry as
    'n.m Title' (or 'n Title' for a chapter, or a bare number then the title on the next
    line) followed by a line holding only the printed page number."""
    text = "\n".join(pages[5:13])
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    secs = []
    i = 0
    while i < len(lines):
        m = re.fullmatch(r"(\d{1,2}(?:\.\d{1,2})?)(?:\s+(.+))?", lines[i])
        if m:
            number, title = m.group(1), (m.group(2) or "").strip()
            j = i + 1
            while j < len(lines) and not re.fullmatch(r"\d{1,3}", lines[j]) and j - i <= 4:
                title = (title + " " + lines[j]).strip()
                j += 1
            if j < len(lines) and re.fullmatch(r"\d{1,3}", lines[j]) and title:
                title = re.sub(r"\s*\.{2,}\s*\d*$", "", title).strip(" .")
                secs.append({"number": number, "title": title, "printed_page": int(lines[j])})
                i = j + 1
                continue
        i += 1
    return secs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--find", default=None, help="print pages whose text contains this (case-insensitive) with printed page refs")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.find and (OUT / "pages.json").exists():
        pages = json.loads((OUT / "pages.json").read_text(encoding="utf-8"))
        pat = re.compile(re.escape(args.find), re.I)
        for p in pages:
            for m in pat.finditer(p["text"]):
                s = max(0, m.start() - 160)
                e = min(len(p["text"]), m.end() + 160)
                snip = re.sub(r"\s+", " ", p["text"][s:e])
                print(f"[pdf {p['pdf_page']} / p.{p['printed_page']} / {p['section']}] ...{snip}...")
        return 0

    raw = load_pages()
    parsed = [printed_page(t) for t in raw]
    # OCR noise can put a stray number in a running header. A parsed number is trusted when a
    # page within the next three confirms the sequence, or when it continues the previous
    # trusted number; anything else is interpolated from the last trusted number.
    def confirmed(i):
        v = parsed[i]
        return v is not None and any(parsed[j] == v + (j - i) for j in range(i + 1, min(i + 4, len(parsed))))
    printed = [None] * len(parsed)
    last = None
    for i, pp in enumerate(parsed):
        if confirmed(i) or (last is not None and pp is not None and last - 1 <= pp <= last + 5):
            printed[i] = pp
        elif last is not None:
            printed[i] = last + 1
        if printed[i] is not None:
            last = printed[i]
    secs = parse_contents(raw)
    # map each section (in contents order) to the first pdf page carrying its printed number
    # at or after the previous section's page, so a stray number in the front matter cannot
    # claim a chapter-22 heading for page 18
    cursor = 14
    for s in secs:
        s["pdf_page"] = None
        target = s["printed_page"]
        hit = next((i for i in range(cursor, len(printed)) if printed[i] == target), None)
        if hit is None:
            # chapter-opener pages carry no running header and their interpolated number can
            # skip the target: take the first page just past it
            hit = next((i for i in range(cursor, len(printed))
                        if printed[i] is not None and target < printed[i] <= target + 3), None)
        if hit is not None:
            s["pdf_page"] = hit + 1
            cursor = hit
        s["chapter"] = int(s["number"].split(".")[0])
    secs = [s for s in secs if s["pdf_page"]]
    secs.sort(key=lambda s: (s["pdf_page"], s["number"]))

    pages = []
    cur = None
    back = [("Glossary", 707), ("Bibliography", 733), ("Index", 745)]   # from the printed contents
    for i, t in enumerate(raw):
        pdf = i + 1
        for s in secs:
            if s["pdf_page"] <= pdf:
                cur = s
        section = f"{cur['number']} {cur['title']}" if cur else None
        chapter = cur["chapter"] if cur else None
        for name, first in back:
            if printed[i] is not None and printed[i] >= first and cur and cur["chapter"] == 23:
                section, chapter = name, None
        pages.append({
            "pdf_page": pdf,
            "printed_page": printed[i],
            "chapter": chapter,
            "section": section,
            "text": t,
        })
    (OUT / "sections.json").write_text(json.dumps(secs, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "pages.json").write_text(json.dumps(pages, indent=0, ensure_ascii=False), encoding="utf-8")
    index = {}
    for k in KEYWORDS:
        flags = 0 if k in ("Ku",) else re.I
        index[k] = [p["pdf_page"] for p in pages if re.search(re.escape(k), p["text"], flags)]
    (OUT / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Semiconductor Modeling (Leventhal & Green, Springer 2006) as JSON\n\n"
        "Extracted from `silicon modeling book.pdf` (OCR text) by `scripts/extract_book_json.py`.\n\n"
        "* `sections.json`: numbered sections with printed and PDF page numbers.\n"
        "* `pages.json`: one record per PDF page with the printed page number, chapter, section in force and the OCR text.\n"
        "* `index.json`: PDF pages per keyword.\n"
        "* `citations.md` / `citations.json`: the passages that support each finding of the stress investigation.\n\n"
        "Cite as printed page (p.) with the PDF page in brackets: the PDF page is the printed page plus 10 to 15 depending on the part.\n"
        "`py -3.14 scripts/extract_book_json.py --find \"phrase\"` greps with page references.\n",
        encoding="utf-8")
    print(f"pages {len(pages)}, sections {len(secs)}, printed numbers parsed on {sum(p is not None for p in printed)} pages")
    for s in secs:
        if s["chapter"] in (4, 10, 11, 12, 13, 16, 17, 20, 22):
            print(f"  {s['number']:>6} {s['title'][:60]:60s} p.{s['printed_page']:<4} pdf {s['pdf_page']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
