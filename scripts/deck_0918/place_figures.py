"""Place the 0918 figures into a copy of Simon's deck. The original is not touched.

slide 3: the picture's image is swapped in place (same aspect, same axes), so the hand-drawn
arrows and boxes over it keep their targets and z-order. Slides 4-5: the cropped variant
picture becomes the new figure at full width. Slides 10/11/13/14/16/17: the empty content
placeholder is replaced by the figure, fitted to the placeholder's box. Comments are kept.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"C:/Users/sh3qm/code/ibis_comparison/.codex_deps/presentation/python")
from pptx import Presentation  # noqa: E402
from pptx.util import Emu  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).parent
SRC = Path(r"C:/Users/sh3qm/AppData/Local/Temp/claude/c--Users-sh3qm-code-ibis-comparison/4830c25e-e99f-44a8-8aaf-2a359f268df1/scratchpad/0918")  # a copy of Simon's original
FIG = Path(r"C:/Users/sh3qm/code/ibis_comparison/results/meeting_deck_2026-09-18/figures")
OUT = Path(r"C:/Users/sh3qm/code/ibis_comparison/results/meeting_deck_2026-09-18/0918_Simon_IBIS_figures_v3.pptx")
E = 914400
R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"

prs = Presentation(SRC / "0918_Simon_IBIS.pptx")
slides = list(prs.slides)


def aspect(p):
    w, h = Image.open(p).size
    return w / h


def swap_image(slide, pic, png, reset_crop=False):
    _, rid = slide.part.get_or_add_image_part(str(png))
    pic._element.blipFill.find(
        "{http://schemas.openxmlformats.org/drawingml/2006/main}blip").set(R_EMBED, rid)
    if reset_crop:
        pic.crop_left = pic.crop_right = pic.crop_top = pic.crop_bottom = 0.0


def fit(png, x, y, w, h):
    a = aspect(png)
    if w / h > a:                       # box wider than the figure: height-limited
        nw, nh = h * a, h
    else:
        nw, nh = w, w / a
    return x + (w - nw) / 2, y + (h - nh) / 2, nw, nh


def pic_of(slide):
    return next(sh for sh in slide.shapes if "Picture" in sh.__class__.__name__)


# slide 3: in place
s = slides[2]
p = pic_of(s)
assert abs(p.width / p.height - aspect(FIG / "recap_pad.png")) < 0.01
swap_image(s, p, FIG / "recap_pad.png")
# the two highlighter strokes marked entries of the old five-entry legend; on the new
# three-entry legend they would sit on the wrong names
# Ink is stored as mc:AlternateContent (a content part, with a picture fallback), which
# python-pptx does not list as a shape: remove the whole wrapper from the shape tree.
tree = s.shapes._spTree
gone = 0
for el in list(tree):
    names = {c.get("name") for c in el.iter() if c.tag.endswith("}cNvPr")}
    if names & {"Ink 10", "Ink 11"}:
        tree.remove(el)
        gone += 1
assert gone == 2, f"expected two ink strokes, removed {gone}"

# slides 4, 5: new figure, full width, centred in the space under the title
for idx, png in ((3, "ex2_stress_levels.png"), (4, "inv_chain_stress_levels.png")):
    s = slides[idx]
    p = pic_of(s)
    swap_image(s, p, FIG / png, reset_crop=True)
    x, y, w, h = fit(FIG / png, 0.45 * E, 1.25 * E, 12.43 * E, 5.9 * E)
    p.left, p.top, p.width, p.height = int(x), int(y), int(w), int(h)

# slides 6-8 (schematics) and 10/11/13/14/16/17: into the empty content placeholder's box,
# or the same box where a slide has no content placeholder
for idx, png in ((5, "schematic_io_buf.png"), (6, "schematic_ex2.png"), (7, "schematic_inv_chain.png")):
    s = slides[idx]
    ph = next((sh for sh in s.placeholders if sh.placeholder_format.idx == 10), None)
    box = (ph.left, ph.top, ph.width, ph.height) if ph is not None else (int(0.33 * E), int(1.14 * E), int(12.33 * E), int(5.95 * E))
    if ph is not None:
        assert not ph.has_text_frame or not ph.text_frame.text.strip(), f"slide {idx + 1} placeholder not empty"
        ph._element.getparent().remove(ph._element)
    x, y, w, h = fit(FIG / png, *box)
    s.shapes.add_picture(str(FIG / png), int(x), int(y), int(w), int(h))

for idx, png in ((9, "four_panel_io_buf.png"), (10, "real_gate_io_buf.png"),
                 (12, "four_panel_ex2.png"), (13, "real_gate_ex2.png"),
                 (15, "four_panel_inv_chain.png"), (16, "real_gate_inv_chain.png")):
    s = slides[idx]
    ph = next(sh for sh in s.placeholders if sh.placeholder_format.idx == 10)
    assert not ph.has_text_frame or not ph.text_frame.text.strip(), f"slide {idx + 1} placeholder not empty"
    x, y, w, h = fit(FIG / png, ph.left, ph.top, ph.width, ph.height)
    ph._element.getparent().remove(ph._element)
    s.shapes.add_picture(str(FIG / png), int(x), int(y), int(w), int(h))

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
print("wrote", OUT)
