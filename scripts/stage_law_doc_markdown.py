#!/usr/bin/env python3
"""A markdown rendering of the stage-law paper, for review before the Word layout pass.

The builder (scripts/build_stage_law_doc.py) calls `markdown_of_body` on the assembled document
body, before the floats are placed and the package is zipped, so the preview carries exactly the
text, equations, tables and figures of the .docx: headings by paragraph style, display equations
linearized into fenced blocks (fractions as (num)/(den), sub- and superscripts as _{} and ^{}),
tables as pipe tables, figures as image links into figures/ with their captions. It can also be
run on a finished .docx:

    py -3.14 scripts/stage_law_doc_markdown.py results/stage_law_doc_2026-10-01/stage_law_paper_v6_ieee.docx
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"w": W, "m": M}


def _q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _math(e) -> str:
    """Linearize OMML into readable text."""
    t = etree.QName(e).localname
    kids = lambda name: [c for c in e if etree.QName(c).localname == name]            # noqa: E731
    sub = lambda name: "".join(_math(c) for k in kids(name) for c in k)               # noqa: E731
    if t == "t":
        return e.text or ""
    if t == "f":
        return "(" + sub("num") + ")/(" + sub("den") + ")"
    if t == "sSub":
        return sub("e") + "_{" + sub("sub") + "}"
    if t == "sSup":
        return sub("e") + "^{" + sub("sup") + "}"
    if t == "sSubSup":
        return sub("e") + "_{" + sub("sub") + "}^{" + sub("sup") + "}"
    if t == "rad":
        return "sqrt(" + sub("e") + ")"
    if t == "acc":
        pr = e.find(_q(M, "accPr"))
        ch = pr.find(_q(M, "chr")).get(_q(M, "val")) if pr is not None and pr.find(_q(M, "chr")) is not None else "^"
        return sub("e") + ch
    if t == "d":
        pr = e.find(_q(M, "dPr"))
        beg, end = "(", ")"
        if pr is not None:
            b, en = pr.find(_q(M, "begChr")), pr.find(_q(M, "endChr"))
            if b is not None:
                beg = b.get(_q(M, "val"), "")
            if en is not None:
                end = en.get(_q(M, "val"), "")
        return beg + ", ".join("".join(_math(c) for c in k) for k in kids("e")) + end
    if t == "func":
        return sub("fName") + "(" + sub("e") + ")"
    if t == "nary":
        pr = e.find(_q(M, "naryPr"))
        ch = "∫"
        if pr is not None and pr.find(_q(M, "chr")) is not None:
            ch = pr.find(_q(M, "chr")).get(_q(M, "val"), "∫")
        return ch + "_{" + sub("sub") + "}^{" + sub("sup") + "} " + sub("e")
    if t == "eqArr":
        return " ; ".join("".join(_math(c) for c in k) for k in kids("e"))
    if t.endswith("Pr"):
        return ""
    return "".join(_math(c) for c in e)


def _para_text(p, images: dict[str, str]) -> tuple[str, str, bool]:
    """(style, text, is_display_equation) of a paragraph; figures become image links."""
    st = p.find("w:pPr/w:pStyle", NS)
    style = st.get(_q(W, "val")) if st is not None else ""
    out, display = [], p.find(".//m:oMathPara", NS) is not None
    for c in p.iter():
        tag = etree.QName(c).localname
        if c.tag == _q(M, "oMath"):
            out.append(("" if display else " `") + _math(c).strip() + ("" if display else "` "))
        elif c.tag == _q(W, "t") and not any(a.tag == _q(M, "oMath") for a in c.iterancestors()):
            rpr = c.getparent().find("w:rPr", NS)
            txt = c.text or ""
            if rpr is not None and txt.strip():
                if rpr.find("w:b", NS) is not None:
                    txt = f"**{txt}**"
                elif rpr.find("w:i", NS) is not None:
                    txt = f"*{txt}*"
            out.append(txt)
        elif tag == "blip":
            rid = c.get(_q(R, "embed"))
            out.append(f"![]({images.get(rid, rid)})")
    text = "".join(out)
    text = re.sub(r"\*\*(\s*)\*\*", r"\1", text)
    return style, text.strip(), display


def markdown_of_body(body, images: dict[str, str], title: str = "") -> str:
    """Render a document body. `images` maps a relationship id to the image path to link."""
    lines: list[str] = []
    eq_buf: list[str] = []

    def flush_eq():
        if eq_buf:
            lines.append("```")
            lines.extend(eq_buf)
            lines.append("```")
            lines.append("")
            eq_buf.clear()

    for el in body:
        tag = etree.QName(el).localname
        if tag == "p":
            style, text, display = _para_text(el, images)
            if display:
                eq_buf.append(text)
                continue
            flush_eq()
            if not text:
                continue
            if style == "Title":
                lines += [f"# {text}", ""]
            elif style == "Date":
                lines += [f"*{text}*", ""]
            elif style == "Heading1":
                lines += [f"## {text}", ""]
            elif style == "Heading2":
                lines += [f"### {text}", ""]
            elif style == "Heading3":
                lines += [f"#### {text}", ""]
            elif style in ("ImageCaption", "TableCaption"):
                lines += [f"*{text}*", ""]
            elif style == "CaptionedFigure":
                lines += [text, ""]
            elif style == "Bibliography":
                lines += [text, ""]
            else:
                lines += [text, ""]
        elif tag == "tbl":
            flush_eq()
            rows = []
            for tr in el.findall("w:tr", NS):
                cells = []
                for tc in tr.findall("w:tc", NS):
                    cells.append(" ".join(_para_text(p, images)[1] for p in tc.findall("w:p", NS)).replace("|", "\\|"))
                rows.append(cells)
            if rows:
                n = max(len(r) for r in rows)
                rows = [r + [""] * (n - len(r)) for r in rows]
                lines.append("| " + " | ".join(rows[0]) + " |")
                lines.append("|" + "---|" * n)
                for r in rows[1:]:
                    lines.append("| " + " | ".join(r) + " |")
                lines.append("")
    flush_eq()
    head = f"# {title}\n\n" if title and not any(l.startswith("# ") for l in lines[:3]) else ""
    return head + "\n".join(lines).rstrip() + "\n"


def markdown_of_docx(docx: Path, figures_dir: str = "figures") -> str:
    """Render a finished .docx; images are linked by their media name (fig1.png ...), which the
    builder maps to the figure files when it writes the preview itself."""
    with zipfile.ZipFile(docx) as z:
        doc = etree.fromstring(z.read("word/document.xml"))
        rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
    images = {r.get("Id"): f"{figures_dir}/{Path(r.get('Target')).name}" for r in rels
              if r.get("Type", "").endswith("/image")}
    return markdown_of_body(doc.find(_q(W, "body")), images)


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = src.with_suffix(".md")
    out.write_text(markdown_of_docx(src), encoding="utf-8")
    print("wrote", out)
