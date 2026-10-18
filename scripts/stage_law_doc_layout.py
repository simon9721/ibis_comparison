#!/usr/bin/env python3
"""Place the double-column figures and tables of the IEEE paper so that pages fill.

Each wide figure or table is a one-column section between two continuous section breaks (the
IEEE Word template's own method): the text above it is balanced across the two columns, the
block spans the page, and the text below resumes in two columns. The block sits exactly where it
is inserted, so the only thing that can go wrong is a block that does not fit the rest of its
page, which Word then moves to the next page, leaving the foot of the page blank.

This pass places the blocks one at a time, with Word's own pagination as the oracle: build the
paper with the first k-1 blocks placed, export it to PDF through Word, read where every paragraph
starts, and insert the k-th block before the first paragraph, on or after the page of its first
mention, under which it fits. Three rules shape the choice:

    - the room under a paragraph accounts for the column balancing: a break before a paragraph
      at height y in column 2 pulls the columns level at about half the text above it;
    - a block is not put under a remnant of one to five text lines, which balancing would smear
      across both columns; it goes under no text at all, or under at least six lines, and under
      at least twelve when the remnant holds a display equation (balancing ignores keep-with-next
      and split equation (20) between the columns at six);
    - figures keep their numbering order on the page, and so do tables: a block is never
      anchored before the anchor of the previous block of its kind.

Output: results/stage_law_doc_2026-10-01/layout_plan.json, read by the builder, and the built
stage_law_paper_v4_ieee.docx.

    py -3.14 scripts/stage_law_doc_layout.py [--verbose]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_stage_law_doc as bd  # noqa: E402

PAGE_H_IN = 11.0
TOP_IN, BOTTOM_IN, LEFT_IN = 0.75, 1.0, 0.625
TEXT_H_IN = PAGE_H_IN - TOP_IN - BOTTOM_IN
COL_SPLIT_IN = LEFT_IN + 3.6          # lines starting right of this are in column 2
MARGIN_IN = 0.25                       # kept free under a block
MIN_LINES_ABOVE = 6                    # a remnant shorter than this is not balanced above a block
MIN_LINES_ABOVE_EQ = 12                # ... and shorter than this when it holds a display equation
_EQ_NUM = re.compile(r"\(\d{1,2}\)\s*$")   # an equation line ends with its number
TEXT_PT = 9.5                          # body text is 10 pt; captions and tables are 8 pt


def export_pdf(docx: Path, pdf: Path) -> None:
    ps = (f'$w = New-Object -ComObject Word.Application; $w.Visible = $false; '
          f'$d = $w.Documents.Open("{docx}", $false, $true); $d.ExportAsFixedFormat("{pdf}", 17); '
          f'$d.Close($false); $w.Quit()')
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)


def norm(s: str) -> str:
    for a, b in (("’", "'"), ("–", "-"), ("—", "-"), ("ﬁ", "fi"), ("ﬂ", "fl")):
        s = s.replace(a, b)
    return " ".join(s.lower().split())


def read_pages(pdf: Path):
    """Per page: the normalised text, its lines as dicts (y from the top margin, column, font size,
    text), and the lowest content edge (inches from the top margin)."""
    import pymupdf
    pages = []
    for p in pymupdf.open(str(pdf)):
        low, lines = 0.0, []
        for b in p.get_text("dict")["blocks"]:
            low = max(low, b["bbox"][3])
            for ln in b.get("lines", []):
                txt = norm("".join(sp["text"] for sp in ln["spans"]))
                if txt:
                    x0, y0, x1, _ = ln["bbox"]
                    col = 0 if (x1 - x0) / 72 > 3.7 else (1 if x0 / 72 < COL_SPLIT_IN else 2)
                    size = max(sp["size"] for sp in ln["spans"])
                    lines.append(dict(y=y0 / 72 - TOP_IN, col=col, size=size, text=txt))
        lines.sort(key=lambda l: (l["col"] == 2, l["y"]))
        pages.append(dict(text=norm(p.get_text()), lines=lines, low_in=low / 72 - TOP_IN))
    return pages


def paragraph_positions(prefixes, pages):
    """(page, column, height) at which each paragraph starts, scanning pages in order; (0, 0, None)
    if not found. A paragraph starts a line, so its prefix is matched at the start of a line."""
    out, page = [], 0
    for pre in prefixes:
        key = norm(pre)
        if len(key) < 20:
            out.append((0, 0, None))
            continue
        head = key[:25]
        hit = (0, 0, None)
        for q in range(page, len(pages)):
            cands = [(l["y"], l["col"]) for l in pages[q]["lines"] if l["text"].startswith(head)]
            if cands:
                y, c = min(cands)
                hit, page = (q + 1, c, y), q
                break
            if key in pages[q]["text"]:
                hit, page = (q + 1, 0, None), q
                break
        out.append(hit)
    return out


def block_extents(pages, placed):
    """Per page, (top, bottom) of every placed block on it. A block is found by its caption line
    ('Fig. N.' below a figure, 'TABLE N' above a table); its small-print lines run from the caption
    to the first body-text line below it, and its top is the caption less the registered height
    for a figure, the caption itself for a table."""
    out = {}
    for key, h, label, is_table in placed:
        for q, pg in enumerate(pages):
            ys = [l["y"] for l in pg["lines"] if l["size"] < TEXT_PT
                  and (l["text"] == label if is_table else l["text"].startswith(label))]
            if not ys:
                continue
            cap = min(ys)
            next_text = min((l["y"] for l in pg["lines"] if l["size"] >= TEXT_PT and l["y"] > cap), default=99.0)
            small = [l["y"] for l in pg["lines"] if l["size"] < TEXT_PT and cap <= l["y"] < next_text]
            bottom = max(small) + 0.15
            top = cap - 0.05 if is_table else cap - (h - 0.4)
            out.setdefault(q + 1, []).append((top, bottom))
            break
    return out


def room_under(pages, blocks, page, col, y):
    """(room in inches, text lines above, remnant holds an equation) for a block inserted before a
    paragraph at (col, y) of `page`: the room left once the text above it is balanced across the
    two columns, how many body-text lines in column 1 stand between the nearest block above and
    the paragraph, and whether a display equation stands among them."""
    lines = pages[page - 1]["lines"]
    above_blocks = [b for t, b in blocks.get(page, []) if b <= y + 0.05]
    if above_blocks:
        s = max(above_blocks)
    elif page == 1:
        s = min((l["y"] for l in lines if l["col"] == 1), default=0.0)
    else:
        s = 0.0
    rem = [l for l in lines if (l["col"] == 1 and s - 0.02 < l["y"] < y - 0.02)
           or (col == 2 and l["col"] == 2 and l["y"] < y - 0.02)]
    n_above = sum(1 for l in rem if l["size"] >= TEXT_PT)
    has_eq = any(_EQ_NUM.search(l["text"]) for l in rem)
    before = (y - s) if col == 1 else (TEXT_H_IN - s) + (y - s)
    room = TEXT_H_IN - (s + max(before, 0.0) / 2) - MARGIN_IN
    return room, n_above, has_eq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--resume", action="store_true", help="continue from _layout_partial.json")
    args = ap.parse_args()
    os.environ["STAGE_LAW_FAST"] = "1"
    d = bd.load_data()
    work = bd.DOC
    plan: dict = {}
    placed: list = []
    last_anchor = {"fig": None, "tab": None}       # prefix before which the previous block of the kind went
    floats, _ = bd.main(d, {}, out_path=work / "_layout_probe.docx", limit=0)
    partial = work / "_layout_partial.json"
    k0 = 0
    if args.resume and partial.exists():
        plan = json.loads(partial.read_text(encoding="utf-8"))
        k0 = len(plan)
        for f in floats[:k0]:
            label = f"{bd.F(f['key']).lower()}." if f["key"] in bd.FIGS else f"table {bd.T(f['key']).split()[1].lower()}"
            placed.append((f["key"], f["height"], label, f["key"] not in bd.FIGS))
            kind = "fig" if f["key"] in bd.FIGS else "tab"
            last_anchor[kind] = next(iter(plan[f["key"]].values()))
        print(f"resuming after {k0} placed blocks")
    for k, f in enumerate(floats):
        if k < k0:
            continue
        docx = work / f"_layout_it{k}.docx"
        _, prefixes = bd.main(d, plan, out_path=docx, limit=k)
        pdf = work / f"_layout_it{k}.pdf"
        export_pdf(docx, pdf)
        pages = read_pages(pdf)
        positions = paragraph_positions(prefixes, pages)
        blocks = block_extents(pages, placed)
        idx = {pre: i for i, pre in enumerate(prefixes) if pre}
        kind = "fig" if f["key"] in bd.FIGS else "tab"
        i_m = idx.get(f["after"], 0)
        mention = next((positions[j][0] for j in range(i_m, -1, -1) if positions[j][0]), 1)
        start = i_m + 1
        if last_anchor[kind] in idx:
            start = max(start, idx[last_anchor[kind]])
        choice, why = None, ""
        for j in range(start, len(prefixes)):
            pg, col, y = positions[j]
            if not pg or y is None or pg < mention:
                continue
            if pg > mention + 3:
                break
            room, n_above, has_eq = room_under(pages, blocks, pg, col, y)
            if 0 < n_above < (MIN_LINES_ABOVE_EQ if has_eq else MIN_LINES_ABOVE):
                continue
            if room >= f["height"]:
                choice, why = (j, pg, col, y), f"room {room:.1f}, {n_above} lines above"
                break
        if choice is None:                             # a page of its own after the mention
            for j in range(start, len(prefixes)):
                pg, col, y = positions[j]
                if pg and y is not None and pg > mention:
                    choice, why = (j, pg, col, y), "no fitting anchor; first paragraph of a later page"
                    break
        if choice is None:
            plan[f["key"]] = {"after": f["after"]}
            last_anchor[kind] = f["after"]
            where = "after its mention (no anchor found)"
        else:
            j, pg, col, y = choice
            plan[f["key"]] = {"before": prefixes[j]}
            last_anchor[kind] = prefixes[j]
            where = f"p{pg} before '{prefixes[j][:32]}' (col {col}, y {y:.1f}; {why})"
        label = f"{bd.F(f['key']).lower()}." if f["key"] in bd.FIGS else f"table {bd.T(f['key']).split()[1].lower()}"
        placed.append((f["key"], f["height"], label, f["key"] not in bd.FIGS))
        partial.write_text(json.dumps(plan, indent=1), encoding="utf-8")
        print(f"{k + 1:2d}/{len(floats)} {f['key']:13s} h={f['height']:.1f} mention p{mention}: {where}")
        if args.verbose:
            short = [f"{i + 1}:{TEXT_H_IN - p['low_in']:.1f}" for i, p in enumerate(pages[:-1]) if TEXT_H_IN - p["low_in"] > 1.0]
            print(f"      layout with {k} placed: {len(pages)} pages; short pages: {' '.join(short) or 'none'}")
    bd.PLAN.write_text(json.dumps(plan, indent=1), encoding="utf-8")
    bd.main(d, plan)
    pdf = work / "_layout_final.pdf"
    export_pdf(bd.OUT, pdf)
    pages = read_pages(pdf)
    short = [f"{i + 1}:{TEXT_H_IN - p['low_in']:.1f}" for i, p in enumerate(pages[:-1]) if TEXT_H_IN - p["low_in"] > 1.0]
    print(f"final: {len(pages)} pages, {sum(max(0.0, TEXT_H_IN - p['low_in']) for p in pages[:-1]):.1f} in blank at page feet; "
          f"short pages (in): {' '.join(short) or 'none'}")
    for p in list(work.glob("_layout_*.docx")) + list(work.glob("_layout_*.pdf")) + [partial]:
        p.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
