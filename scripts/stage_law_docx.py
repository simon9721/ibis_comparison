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


def equation(latex: str, number: int | None = None) -> str:
    num = _run(f"  ({number})", upright=True) if number is not None else ""
    body = omml(latex)[len("<m:oMath>"):-len("</m:oMath>")]
    return ('<w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr><m:oMathPara><m:oMathParaPr>'
            f'<m:jc m:val="center"/></m:oMathParaPr><m:oMath>{body}{num}</m:oMath></m:oMathPara></w:p>')


def table(header: list[str], rows: list[list[str]], widths: list[int], caption: str | None = None,
          size: int = 18) -> str:
    """widths in twentieths of a point (dxa); they should sum to about 9600."""
    def cell(text, w, head=False):
        runs = inline(f"**{text}**" if head and "$" not in text and text else text, size=size)
        if text.startswith("$") and text.endswith("$"):
            runs += _text_run("\u200b", size=size)      # keeps a math-only cell inline, left-aligned
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="Compact"/>'
                f'<w:jc w:val="left"/></w:pPr>{runs}</w:p></w:tc>')

    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    head = "<w:tr><w:trPr><w:tblHeader/></w:trPr>" + "".join(cell(h, w, True) for h, w in zip(header, widths)) + "</w:tr>"
    body = "".join("<w:tr>" + "".join(cell(c, w) for c, w in zip(r, widths)) + "</w:tr>" for r in rows)
    cap = para(caption, "TableCaption") if caption else ""
    return (cap + f'<w:tbl><w:tblPr><w:tblStyle w:val="Table"/><w:tblW w:type="dxa" w:w="{sum(widths)}"/>'
            '<w:tblBorders><w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tblBorders>'
            '<w:tblLayout w:type="fixed"/>'
            '<w:tblLook w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" '
            f'w:noVBand="0" w:val="0020"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{head}{body}</w:tbl>'
            + '<w:p><w:pPr><w:pStyle w:val="Compact"/></w:pPr></w:p>')


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
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"')

    def __init__(self, source: Path, workdir: Path):
        if workdir.exists():
            shutil.rmtree(workdir)
        with zipfile.ZipFile(source) as z:
            z.extractall(workdir)
        self.dir = workdir
        self.images: list[tuple[str, Path]] = []
        (self.dir / "word" / "media").mkdir(exist_ok=True)

    def figure(self, png: Path, caption: str, width_in: float = 6.4) -> str:
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
        return (f'<w:p><w:pPr><w:pStyle w:val="CaptionedFigure"/><w:jc w:val="center"/></w:pPr>{drawing}</w:p>'
                + para(caption, "ImageCaption"))

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
