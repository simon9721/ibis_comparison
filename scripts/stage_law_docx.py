#!/usr/bin/env python3
"""Small WordprocessingML toolkit for scripts/build_stage_law_doc.py.

No python-docx, pandoc or LibreOffice on this machine, so the document is assembled as XML:

    omml(latex)          a LaTeX subset -> Office Math (native, editable Word equations)
    para / heading / equation / table / figure      block builders returning XML strings
    Package              unzip a .docx, replace part of its body, add images, zip it back

The LaTeX subset is what the stage-law derivation needs: sub/superscripts, \\frac, \\sqrt,
\\hat, \\text, \\left..\\right delimiters, Greek and operator symbols, upright function names.
"""
from __future__ import annotations

import re
import shutil
import struct
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SYM = {
    "alpha": "α", "tau": "τ", "theta": "θ", "Delta": "Δ", "cdot": "⋅",
    "le": "≤", "ge": "≥", "in": "∈", "triangleq": "≜", "to": "→",
    "circ": "∘", "star": "⋆", "times": "×", "approx": "≈", "pm": "±",
    "ldots": "…", "infty": "∞", "neq": "≠", "prime": "′", "mid": "|",
    "quad": " ", ",": " ", " ": " ", "{": "{", "}": "}", "%": "%", "_": "_",
}
FUNC = {"min", "max", "clip", "rms", "argmin", "arg", "exp", "ln"}


def _run(text: str, upright: bool = False) -> str:
    pr = '<m:rPr><m:sty m:val="p"/></m:rPr>' if upright else ""
    return f'<m:r>{pr}<m:t xml:space="preserve">{escape(text)}</m:t></m:r>'


class _P:
    """Recursive-descent parser for the LaTeX subset."""

    def __init__(self, s: str):
        self.t = re.findall(r"\\[A-Za-z]+|\\.|[{}_^]|\s+|.", s)
        self.t = [x for x in self.t if not x.isspace()]
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self):
        x = self.t[self.i]
        self.i += 1
        return x

    def group(self) -> str:
        """One argument: a braced group or a single atom."""
        if self.peek() == "{":
            self.take()
            out = self.seq(("}",))
            self.take()
            return out
        return self.atom()

    def raw_group(self) -> str:
        assert self.take() == "{"
        depth, out = 1, []
        while True:
            x = self.take()
            if x == "{":
                depth += 1
            elif x == "}":
                depth -= 1
                if depth == 0:
                    return "".join(out)
            out.append(x)

    def seq(self, stop) -> str:
        out = []
        while self.peek() is not None and self.peek() not in stop:
            out.append(self.item())
        return "".join(out)

    def item(self) -> str:
        base = self.atom()
        sub = sup = None
        while self.peek() in ("_", "^"):
            if self.take() == "_":
                sub = self.group()
            else:
                sup = self.group()
        if sub is not None and sup is not None:
            return f"<m:sSubSup><m:e>{base}</m:e><m:sub>{sub}</m:sub><m:sup>{sup}</m:sup></m:sSubSup>"
        if sub is not None:
            return f"<m:sSub><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"
        if sup is not None:
            return f"<m:sSup><m:e>{base}</m:e><m:sup>{sup}</m:sup></m:sSup>"
        return base

    def atom(self) -> str:
        x = self.take()
        if x == "{":
            out = self.seq(("}",))
            self.take()
            return out
        if x.startswith("\\"):
            name = x[1:]
            if name == "frac":
                n, d = self.group(), self.group()
                return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"
            if name == "sqrt":
                return ('<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/>'
                        f"<m:e>{self.group()}</m:e></m:rad>")
            if name in ("hat", "tilde", "bar"):
                ch = {"hat": "̂", "tilde": "̃", "bar": "̅"}[name]
                return f'<m:acc><m:accPr><m:chr m:val="{ch}"/></m:accPr><m:e>{self.group()}</m:e></m:acc>'
            if name == "text":
                # the tokenizer dropped whitespace; \text uses ~ for a space
                return ('<m:r><m:rPr><m:nor/></m:rPr><m:t xml:space="preserve">'
                        f'{escape(self.raw_group().replace("~", " "))}</m:t></m:r>')
            if name == "left":
                beg = self.take()
                beg = {"\\{": "{", ".": ""}.get(beg, beg)
                inner = self.seq(("\\right",))
                self.take()
                end = self.take()
                end = {"\\}": "}", ".": ""}.get(end, end)
                return (f'<m:d><m:dPr><m:begChr m:val="{escape(beg)}"/><m:endChr m:val="{escape(end)}"/>'
                        f"<m:grow/></m:dPr><m:e>{inner}</m:e></m:d>")
            if name in FUNC:
                return _run(name, upright=True)
            if name in SYM:
                return _run(SYM[name], upright=name in ("quad", ",", " "))
            raise ValueError(f"unknown command \\{name}")
        if x == "~":
            return _run(" ", upright=True)
        if x == "-":
            x = "−"
        return _run(x, upright=not x.isalpha())


def omml(latex: str) -> str:
    p = _P(latex)
    out = p.seq(())
    assert p.peek() is None, f"unparsed tail in {latex!r}"
    return f"<m:oMath>{out}</m:oMath>"


# ----------------------------------------------------------------------------- blocks
def _text_run(text: str, bold=False, italic=False, size=None) -> str:
    pr = ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + (f'<w:sz w:val="{size}"/>' if size else "")
    pr = f"<w:rPr>{pr}</w:rPr>" if pr else ""
    return f'<w:r>{pr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def inline(text: str, size=None) -> str:
    """Runs for `text`: $math$, **bold**, *italic*; everything else plain."""
    out = []
    for part in re.split(r"(\$[^$]+\$|\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not part:
            continue
        if part.startswith("$"):
            out.append(omml(part[1:-1]))
        elif part.startswith("**"):
            out.append(_text_run(part[2:-2], bold=True, size=size))
        elif part.startswith("*"):
            out.append(_text_run(part[1:-1], italic=True, size=size))
        else:
            out.append(_text_run(part, size=size))
    return "".join(out)


def para(text: str, style: str = "BodyText", jc: str | None = None, keep_next=False) -> str:
    ppr = f'<w:pStyle w:val="{style}"/>' + ("<w:keepNext/>" if keep_next else "") + (f'<w:jc w:val="{jc}"/>' if jc else "")
    return f"<w:p><w:pPr>{ppr}</w:pPr>{inline(text)}</w:p>"


def heading(text: str, level: int = 2) -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr>{inline(text)}</w:p>'


def equation(latex: str, number: int | None = None, size: int | None = None) -> str:
    """A display equation. Four backslashes in `latex` (two at run time) start a new line: each
    line is its own paragraph (Word lays several m:oMath of one m:oMathPara out on a single
    line), with no space between them and the number on the last. `size` (half-points) shrinks
    the math runs, for equations that are too wide for an IEEE column at 10 pt."""
    num = _run(f"  ({number})", upright=True) if number is not None else ""
    lines = [ln.strip() for ln in latex.split("\\\\")]
    out = []
    for i, ln in enumerate(lines):
        body = omml(ln)[len("<m:oMath>"):-len("</m:oMath>")]
        math = f"<m:oMath>{body}{num if i == len(lines) - 1 else ''}</m:oMath>"
        if size:
            rpr = f'<w:rPr><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
            math = re.sub(r"<m:r>(<m:rPr>.*?</m:rPr>)?", lambda m: "<m:r>" + (m.group(1) or "") + rpr, math)
        sp = ('<w:spacing w:before="60" w:after="0"/>' if i == 0 and len(lines) > 1 else
              '<w:spacing w:before="0" w:after="60"/>' if i == len(lines) - 1 and len(lines) > 1 else
              '<w:spacing w:before="0" w:after="0"/>' if len(lines) > 1 else "")
        keep = "<w:keepNext/><w:keepLines/>" if i < len(lines) - 1 else "<w:keepLines/>"
        out.append(f'<w:p><w:pPr><w:pStyle w:val="Equation"/>{keep}{sp}</w:pPr><m:oMathPara><m:oMathParaPr>'
                   f'<m:jc m:val="center"/></m:oMathParaPr>{math}</m:oMathPara></w:p>')
    return "".join(out)


def ieee_caption(label: str, title: str) -> str:
    """IEEE table caption: 'TABLE I' and the title, small capitals, centred, 8 pt."""
    pr = '<w:rPr><w:smallCaps/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr>'
    return (f'<w:p><w:pPr><w:pStyle w:val="TableCaption"/><w:keepNext/><w:jc w:val="center"/>'
            f'<w:spacing w:before="60" w:after="0"/>{pr}</w:pPr>{_text_run(label, size=16).replace("<w:rPr>", "<w:rPr><w:smallCaps/>")}</w:p>'
            f'<w:p><w:pPr><w:pStyle w:val="TableCaption"/><w:keepNext/><w:jc w:val="center"/>'
            f'<w:spacing w:before="0" w:after="60"/>{pr}</w:pPr>'
            + inline(title, size=16).replace("<w:rPr>", "<w:rPr><w:smallCaps/>") + "</w:p>")


def table(header: list[str], rows: list[list[str]], widths: list[int], caption: str | None = None,
          size: int = 18, caption_xml: str = "", spacer: bool = True, jc: str | None = None) -> str:
    """widths in twentieths of a point (dxa): about 9600 for a full page, 5000 for one IEEE column.
    `caption_xml` is placed before the table as given (an IEEE caption); `caption` is the older
    single italic caption paragraph."""
    def cell(text, w, head=False, keep=True):
        runs = inline(f"**{text}**" if head and "$" not in text and text else text, size=size)
        if text.startswith("$") and text.endswith("$"):
            runs += _text_run("\u200b", size=size)      # keeps a math-only cell inline, left-aligned
        # keepNext on the caption and the header row only: a header is never left alone at the foot of
        # a page, a long table may still split (its header repeats, w:tblHeader), and Word is not
        # tempted to move a whole table to the next page
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="Compact"/>'
                f'{"<w:keepNext/>" if keep else ""}<w:jc w:val="left"/></w:pPr>{runs}</w:p></w:tc>')

    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    head = ("<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>"
            + "".join(cell(h, w, True) for h, w in zip(header, widths)) + "</w:tr>")
    body = "".join("<w:tr><w:trPr><w:cantSplit/></w:trPr>"
                   + "".join(cell(c, w, keep=False) for c, w in zip(r, widths)) + "</w:tr>"
                   for i, r in enumerate(rows))
    cap = caption_xml or (para(caption, "TableCaption", keep_next=True) if caption else "")
    jcx = f'<w:jc w:val="{jc}"/>' if jc else ""
    return (cap + f'<w:tbl><w:tblPr><w:tblStyle w:val="Table"/><w:tblW w:type="dxa" w:w="{sum(widths)}"/>{jcx}'
            '<w:tblBorders><w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tblBorders>'
            '<w:tblLayout w:type="fixed"/>'
            '<w:tblLook w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" '
            f'w:noVBand="0" w:val="0020"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{head}{body}</w:tbl>'
            + ('<w:p><w:pPr><w:pStyle w:val="Compact"/></w:pPr></w:p>' if spacer else ""))


def table_height_pt(header, rows, widths, size=16) -> float:
    """A generous estimate of a table's height for a fixed-size text box."""
    pt = size / 2.0
    cw = pt * 0.5 * 20                       # one average character, in twips, at this size
    total = 0.0
    for r in [header] + rows:
        lines = 1
        for c, w in zip(r, widths):
            txt = re.sub(r"[$\\{}^_*]", "", c)
            lines = max(lines, -(-len(txt) * cw // max(w - 160, 200)))
        total += lines * pt * 1.25 + 3.0
    return total * 1.12 + pt * 1.5


IEEE_PAGE = ('<w:pgSz w:w="12240" w:h="15840"/>'
             '<w:pgMar w:top="1080" w:right="900" w:bottom="1440" w:left="900" w:header="720" w:footer="720" w:gutter="0"/>')
IEEE_TEXT_WIDTH_IN = 7.25
IEEE_COL_WIDTH_IN = 3.5


def ieee_sect_pr(cols: int = 2, continuous: bool = False) -> str:
    typ = '<w:type w:val="continuous"/>' if continuous else ""
    c = '<w:cols w:num="2" w:space="360"/>' if cols == 2 else '<w:cols w:num="1"/>'
    return f"<w:sectPr>{typ}{IEEE_PAGE}{c}<w:docGrid w:linePitch=\"240\"/></w:sectPr>"


def section_break(cols: int) -> str:
    """An (almost invisible) paragraph that ends a section of `cols` columns, continuous."""
    return (f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>'
            f'<w:rPr><w:sz w:val="2"/></w:rPr>{ieee_sect_pr(cols, continuous=True)}</w:pPr></w:p>')


def ieee_styles(styles_xml: Path) -> None:
    """Rewrite the paragraph styles of the source document for IEEE Transactions typography:
    Times New Roman 10 pt justified body with a first-line indent, small-capital centred section
    heads, italic subsection heads, 8 pt captions, tables and references."""
    s = styles_xml.read_text(encoding="utf-8")
    s = re.sub(r"<w:docDefaults>.*?</w:docDefaults>",
               '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
               'w:cs="Times New Roman" w:eastAsia="Times New Roman"/><w:sz w:val="20"/><w:szCs w:val="20"/>'
               '<w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA"/></w:rPr></w:rPrDefault>'
               '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
               "</w:docDefaults>", s, flags=re.S)
    times = ('<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" '
             'w:eastAsia="Times New Roman"/>')
    new = {
        "Normal": '<w:style w:default="1" w:styleId="Normal" w:type="paragraph"><w:name w:val="Normal"/><w:qFormat/>'
                  f'<w:pPr><w:jc w:val="both"/></w:pPr><w:rPr>{times}<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>',
        "BodyText": '<w:style w:styleId="BodyText" w:type="paragraph"><w:name w:val="Body Text"/><w:basedOn w:val="Normal"/>'
                    '<w:link w:val="BodyTextChar"/><w:qFormat/><w:pPr><w:spacing w:after="0" w:before="0"/>'
                    '<w:ind w:firstLine="200"/><w:jc w:val="both"/></w:pPr><w:rPr><w:sz w:val="20"/></w:rPr></w:style>',
        "FirstParagraph": '<w:style w:customStyle="1" w:styleId="FirstParagraph" w:type="paragraph"><w:name w:val="First Paragraph"/>'
                          '<w:basedOn w:val="BodyText"/><w:next w:val="BodyText"/><w:qFormat/><w:pPr><w:ind w:firstLine="200"/></w:pPr></w:style>',
        "Equation": '<w:style w:customStyle="1" w:styleId="Equation" w:type="paragraph"><w:name w:val="Equation"/>'
                    '<w:basedOn w:val="Normal"/><w:next w:val="BodyText"/><w:pPr><w:spacing w:before="60" w:after="60"/>'
                    '<w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr></w:style>',
        "Heading1": '<w:style w:styleId="Heading1" w:type="paragraph"><w:name w:val="Heading 1"/><w:basedOn w:val="Normal"/>'
                    '<w:next w:val="BodyText"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="240" w:after="120"/>'
                    f'<w:jc w:val="center"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr>{times}<w:smallCaps/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>',
        "Heading2": '<w:style w:styleId="Heading2" w:type="paragraph"><w:name w:val="Heading 2"/><w:basedOn w:val="Normal"/>'
                    '<w:next w:val="BodyText"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="160" w:after="60"/>'
                    f'<w:jc w:val="left"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr>{times}<w:i/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>',
        "Heading3": '<w:style w:styleId="Heading3" w:type="paragraph"><w:name w:val="Heading 3"/><w:basedOn w:val="Normal"/>'
                    '<w:next w:val="BodyText"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="120" w:after="40"/>'
                    f'<w:ind w:firstLine="200"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr>{times}<w:i/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>',
        "Title": '<w:style w:styleId="Title" w:type="paragraph"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/>'
                 '<w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="0" w:after="240"/><w:jc w:val="center"/></w:pPr>'
                 f'<w:rPr>{times}<w:sz w:val="48"/><w:szCs w:val="48"/></w:rPr></w:style>',
        "Date": '<w:style w:styleId="Date" w:type="paragraph"><w:name w:val="Date"/><w:next w:val="BodyText"/><w:qFormat/>'
                '<w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="0" w:after="360"/><w:jc w:val="center"/></w:pPr>'
                f'<w:rPr>{times}<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>',
        "Caption": '<w:style w:styleId="Caption" w:type="paragraph"><w:name w:val="Caption"/><w:basedOn w:val="Normal"/>'
                   '<w:pPr><w:spacing w:before="40" w:after="120"/><w:jc w:val="both"/></w:pPr>'
                   f'<w:rPr>{times}<w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr></w:style>',
        "TableCaption": '<w:style w:customStyle="1" w:styleId="TableCaption" w:type="paragraph"><w:name w:val="Table Caption"/>'
                        '<w:basedOn w:val="Caption"/><w:pPr><w:keepNext/><w:jc w:val="center"/></w:pPr></w:style>',
        "ImageCaption": '<w:style w:customStyle="1" w:styleId="ImageCaption" w:type="paragraph"><w:name w:val="Image Caption"/>'
                        '<w:basedOn w:val="Caption"/><w:pPr><w:spacing w:before="40" w:after="60"/></w:pPr></w:style>',
        "CaptionedFigure": '<w:style w:customStyle="1" w:styleId="CaptionedFigure" w:type="paragraph"><w:name w:val="Captioned Figure"/>'
                           '<w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="0" w:after="0"/><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr></w:style>',
        "Compact": '<w:style w:customStyle="1" w:styleId="Compact" w:type="paragraph"><w:name w:val="Compact"/><w:basedOn w:val="Normal"/>'
                   '<w:qFormat/><w:pPr><w:spacing w:after="10" w:before="10"/><w:ind w:firstLine="0"/><w:jc w:val="left"/></w:pPr>'
                   '<w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr></w:style>',
        "Bibliography": '<w:style w:customStyle="1" w:styleId="Bibliography" w:type="paragraph"><w:name w:val="Bibliography"/>'
                        '<w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="40"/><w:ind w:left="300" w:hanging="300"/><w:jc w:val="both"/></w:pPr>'
                        '<w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr></w:style>',
        "Abstract": '<w:style w:customStyle="1" w:styleId="Abstract" w:type="paragraph"><w:name w:val="Abstract"/>'
                    '<w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="0" w:after="100"/><w:ind w:firstLine="0"/><w:jc w:val="both"/></w:pPr>'
                    '<w:rPr><w:b/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>',
    }
    for sid, xml in new.items():
        pat = re.compile(r'<w:style [^>]*w:styleId="' + sid + r'"[^>]*>.*?</w:style>', re.S)
        if pat.search(s):
            s = pat.sub(lambda m: xml, s, count=1)
        else:
            s = s.replace("</w:styles>", xml + "</w:styles>")
    styles_xml.write_text(s, encoding="utf-8")


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        head = fh.read(24)
    return struct.unpack(">II", head[16:24])


class Package:
    """An unpacked .docx whose body can be rebuilt and to which images can be added."""

    NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
          'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
          'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"')

    def __init__(self, source: Path, workdir: Path):
        if workdir.exists():
            shutil.rmtree(workdir)
        with zipfile.ZipFile(source) as z:
            z.extractall(workdir)
        self.dir = workdir
        self.images: list[tuple[str, Path]] = []
        (self.dir / "word" / "media").mkdir(exist_ok=True)

    def _pic(self, png: Path, width_in: float):
        """Register `png` and return (inline drawing run, cx, cy) at `width_in`."""
        n = len(self.images) + 1
        rid = f"rIdFig{n}"
        self.images.append((rid, png))
        shutil.copyfile(png, self.dir / "word" / "media" / f"fig{n}.png")
        w, h = png_size(png)
        cx = int(width_in * 914400)
        cy = int(cx * h / w)
        drawing = (
            f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="{100 + n}" name="Figure {n}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/>'
            '</wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{100 + n}" name="fig{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            "</wp:inline></w:drawing></w:r>")
        return drawing, cx, cy

    def figure(self, png: Path, caption: str, width_in: float = 6.4) -> str:
        drawing, _, _ = self._pic(png, width_in)
        return (f'<w:p><w:pPr><w:pStyle w:val="CaptionedFigure"/><w:jc w:val="center"/></w:pPr>{drawing}</w:p>'
                + para(caption, "ImageCaption"))

    _boxes = 0

    def float_box(self, content_xml: str, width_in: float, height_in: float, valign: str = "auto") -> str:
        """A paragraph holding a floating text box that spans the page width (both columns),
        placed at the top of the page (Word stacks several top-aligned boxes on one page in
        anchor order; a bottom-aligned box is not kept clear of a top-aligned one, so "bottom"
        is only for a page that carries one float), text above and below."""
        Package._boxes += 1
        n = Package._boxes
        if valign == "auto":
            valign = "top"
        cx, cy = int(width_in * 914400), int(height_in * 914400)
        return (
            '<w:p><w:pPr><w:pStyle w:val="Compact"/><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>'
            '<w:rPr><w:sz w:val="2"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="2"/></w:rPr><w:drawing>'
            f'<wp:anchor distT="91440" distB="91440" distL="114300" distR="114300" simplePos="0" '
            f'relativeHeight="{251659264 + n}" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="0">'
            '<wp:simplePos x="0" y="0"/>'
            '<wp:positionH relativeFrom="margin"><wp:align>center</wp:align></wp:positionH>'
            f'<wp:positionV relativeFrom="margin"><wp:align>{valign}</wp:align></wp:positionV>'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapTopAndBottom/>'
            f'<wp:docPr id="{900 + n}" name="Float {n}"/><wp:cNvGraphicFramePr/>'
            '<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
            f'<wps:wsp><wps:cNvSpPr txBox="1"/><wps:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></wps:spPr>'
            f'<wps:txbx><w:txbxContent>{content_xml}</w:txbxContent></wps:txbx>'
            '<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="t" anchorCtr="0">'
            '<a:noAutofit/></wps:bodyPr></wps:wsp></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r></w:p>')

    float_heights: dict = {}

    def figure_float(self, png: Path, caption: str, width_in: float = 7.1, valign: str = "auto", key: str = "") -> str:
        """A double-column figure: picture and caption in a floating box at the top (or bottom) of the page."""
        drawing, cx, cy = self._pic(png, width_in)
        chars_per_line = int(width_in * 72 / (8 * 0.47))
        lines = -(-len(re.sub(r"[$\\{}^_*]", "", caption)) // chars_per_line) + 1
        height_in = cy / 914400 + (lines * 9.6 + 14) / 72
        if key:
            self.float_heights[key] = height_in
        content = (f'<w:p><w:pPr><w:pStyle w:val="CaptionedFigure"/><w:jc w:val="center"/></w:pPr>{drawing}</w:p>'
                   + para(caption, "ImageCaption"))
        return self.float_box(content, width_in, height_in, valign)

    def table_float(self, caption_xml: str, table_xml: str, height_pt: float, width_in: float = 7.1,
                    valign: str = "auto", key: str = "") -> str:
        """A double-column table with its IEEE caption in a floating box."""
        height_in = (height_pt + 2 * 9.6 + 18) / 72
        if key:
            self.float_heights[key] = height_in
        return self.float_box(caption_xml + table_xml, width_in, height_in, valign)

    # ---- spanning blocks in the flow: a one-column section between two continuous breaks. The text
    # before the block is balanced across the columns, the block spans the page, the text after it
    # resumes in two columns; nothing is dragged, and the block sits exactly where it is inserted.
    def figure_span(self, png: Path, caption: str, width_in: float = 7.1, key: str = "") -> str:
        drawing, cx, cy = self._pic(png, width_in)
        chars_per_line = int(IEEE_TEXT_WIDTH_IN * 72 / (8 * 0.47))
        lines = -(-len(re.sub(r"[$\{}^_*]", "", caption)) // chars_per_line)
        height_in = cy / 914400 + (lines * 9.6 + 10) / 72
        if key:
            self.float_heights[key] = height_in
        return (section_break(2)
                + f'<w:p><w:pPr><w:pStyle w:val="CaptionedFigure"/><w:jc w:val="center"/></w:pPr>{drawing}</w:p>'
                + para(caption, "ImageCaption") + section_break(1))

    def table_span(self, caption_xml: str, table_xml: str, height_pt: float, key: str = "") -> str:
        height_in = (height_pt + 2 * 9.6 + 14) / 72
        if key:
            self.float_heights[key] = height_in
        return section_break(2) + caption_xml + table_xml + section_break(1)

    def finish(self, out: Path):
        rels = self.dir / "word" / "_rels" / "document.xml.rels"
        s = rels.read_text(encoding="utf-8")
        add = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                      f'relationships/image" Target="media/fig{i}.png"/>' for i, (rid, _) in enumerate(self.images, 1))
        rels.write_text(s.replace("</Relationships>", add + "</Relationships>"), encoding="utf-8")
        ct = self.dir / "[Content_Types].xml"
        s = ct.read_text(encoding="utf-8")
        if 'Extension="png"' not in s:
            s = s.replace("<Default Extension=\"xml\"", '<Default Extension="png" ContentType="image/png"/><Default Extension="xml"')
        ct.write_text(s, encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(ct, "[Content_Types].xml")
            for f in sorted(self.dir.rglob("*")):
                if f.is_file() and f.name != "[Content_Types].xml":
                    z.write(f, f.relative_to(self.dir).as_posix())
