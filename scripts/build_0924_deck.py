#!/usr/bin/env python3
"""The 2026-09-24 deck: the track-1 story told in the order the evidence arrived.

Every earlier telling started from the method and worked back to the evidence. This one runs
the other way, which is how the work actually went:

    1  we can probe our own test chips, so measure the map: pair Ku(t) with the gate at each
       instant and read off Ku as a function of the gate
    2  show that map works - the real gate through the measured map tracks the transistor at
       every stress level, where native IBIS and our gate-state model do not
    3  show why the gate-state model fails: the real gate changes shape as the pulse shortens
       and GUP keeps one shape, and that shape difference is the whole error
    4  only then the motivation: reproduce the real gate's shape from what is in the file
    5+ the method, and what it does not yet cover

Figures: `scripts/build_0924_deck_figures.py` (this deck) and the 09-18 deck's schematics.
Style and layout come from Simon's own 0918 deck, whose slides are not carried over.

Output: results/meeting_deck_2026-09-24/0924_track1_story.pptx

    py -3.14 scripts/build_0924_deck.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))

from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.util import Pt  # noqa: E402
from PIL import Image  # noqa: E402

OUTDIR = ROOT / "results" / "meeting_deck_2026-09-24"
F24 = OUTDIR / "figures"
F18 = ROOT / "results" / "meeting_deck_2026-09-18" / "figures"
BASE = ROOT / "results" / "meeting_deck_2026-09-18" / "0918_Simon_IBIS_figures_v3.pptx"
OUT = OUTDIR / "0924_track1_story.pptx"
E = 914400
GREEN = RGBColor(43, 122, 67)
ORANGE = RGBColor(192, 86, 33)

prs = Presentation(BASE)
LAYOUT = prs.slides[2].slide_layout          # Simon's own content layout
# start from an empty deck on his template: his slides belong to his deck, not this one
lst = prs.slides._sldIdLst
for sid in list(lst):
    rid = sid.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    prs.part.drop_rel(rid)
    lst.remove(sid)


def bullets(slide, items, size=18):
    ph = next(sh for sh in slide.placeholders if sh.placeholder_format.idx == 10)
    lines = sum(max(1, -(-len(t) // 108)) for t in items)
    h = int((0.33 * lines + 0.12 * len(items) + 0.1) * E)
    ph.left, ph.top, ph.width, ph.height = int(0.45 * E), int(1.08 * E), int(12.45 * E), h
    tf = ph.text_frame
    tf.clear()
    for k, t in enumerate(items):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        bold = t.startswith("**")
        r = p.add_run()
        r.text = t.replace("**", "")
        r.font.size = Pt(size)
        if bold:
            r.font.bold = True
            r.font.color.rgb = GREEN
        p.space_after = Pt(4)
    return ph.top + h


def picture(slide, png, top, bottom=7.15 * E, left=0.45 * E, width=12.45 * E):
    w, h = Image.open(png).size
    a = w / h
    avail = bottom - top - 0.1 * E
    pw, ph_ = (width, width / a) if width / a <= avail else (avail * a, avail)
    slide.shapes.add_picture(str(png), int(left + (width - pw) / 2), int(top + 0.08 * E),
                             int(pw), int(ph_))


def slide(title, items=(), png=None, notes="", size=18):
    s = prs.slides.add_slide(LAYOUT)
    s.shapes.title.text = title
    y = bullets(s, list(items), size) if items else int(1.1 * E)
    if png is not None:
        picture(s, png, y)
    else:
        ph = next((sh for sh in s.placeholders if sh.placeholder_format.idx == 10), None)
        if ph is not None and not items:
            ph._element.getparent().remove(ph._element)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


# --------------------------------------------------------------------------- 0
slide("Reproducing the real gate from the IBIS file",
      ["Simon Huang  ·  24 September 2026",
       "",
       "The story in one line: the output stage is a static map of its own gate, so a stressed "
       "pad is right when the gate's shape is right — and the gate is the thing IBIS does not "
       "record.",
       "",
       "**1  measure the map   2  show it works   3  show why our gate fails   "
       "4  reproduce the gate from the file**"],
      notes="Order matters here: every earlier version started from the method. This one starts "
            "from the measurement, because that is how the work went and it makes the method's "
            "motivation earned rather than asserted.")

# --------------------------------------------------------------------------- 1  the probe
slide("1 · We can look inside our own test chips",
      ["These are our designs, so the transistor netlist is available and every internal node "
       "can be probed. A customer using a vendor's IBIS file cannot do this — which is the "
       "whole problem, and the reason to do it once, carefully.",
       "**The node that matters is the output stage's gate** — ex2's n4 below. Everything the "
       "pad does is decided there."],
      F18 / "schematic_ex2.png",
      notes="ex2's predriver is three stages; n4 (orange) is the gate of the output device. "
            "Probes ran on predriver_stages_2026-09-09; the same schematics exist for io_buf "
            "and inv_chain on the 09-18 deck.")

# --------------------------------------------------------------------------- 2  the map
slide("2 · Measuring the map: pair Ku(t) with the gate, instant by instant",
      ["The IBIS file gives Ku(t) on one full transition. The probe gives the gate on the same "
       "run. At each instant we have both numbers — so plot one against the other.",
       "**The pairing is the map.** No fitting: it is read off a single full-swing run."],
      F24 / "map_from_probe_ex2.png",
      notes="Left: Ku(t) from the file and the probed n4(t), with five instants marked. Right: "
            "the same five instants plotted Ku against gate. This is the measured Ku-vs-gate "
            "map, and it is what the next slides drive.")

# --------------------------------------------------------------------------- 3  does it work
for dev, extra in (("ex2", "Within ±5 % at every level, where native IBIS runs +71 % at the "
                           "deepest and our own gate-state model +74 %."),
                   ("inv_chain", "Within +2…+9 %, where native IBIS runs +87 % at the deepest. "
                                 "Our gate-state model looks good at 70–90 % for the wrong "
                                 "reason — see the backup slide on Vinh.")):
    slide(f"3 · Does the measured map work?  {dev}",
          ["Drive that measured map with the transistor's own gate, and compare the pad against "
           "the transistor at all five stress levels.",
           f"**{extra}**"],
          F24 / f"works_levels_{dev}.png",
          notes="Build: gate_replay_silicon_full in gate_cascade_prototype_2026-09-09 — the real "
                "gate replayed through the map measured at full swing. The same replay through "
                "the IBIS-implied map is fine on ex2 (-3…-6 %) and collapses on inv_chain "
                "(-14 to -69 %), which is why the measured map is the one shown here.")

slide("3 · So the output stage is not the problem",
      ["Given the right gate, the map reproduces the pad at every stress level, on both buffers.",
       "The map itself is a fixed curve — it has no memory, and it does not change with the "
       "pulse. Measured hysteresis between the rising and falling branches is 0.07–0.10.",
       "**Everything that is wrong with our model is therefore in the gate.**"],
      notes="This is the pivot of the deck. It licenses spending the rest of the time on the "
            "gate's shape and nothing else.")

# --------------------------------------------------------------------------- 4  why
slide("4 · Why our gate fails: the real gate changes shape, GUP does not",
      ["Our GUP is a fixed delay then an RC ramp. Truncating the input truncates that one shape.",
       "The real gate is already moving long before GUP starts, and it turns round earlier.",
       "**Compare the two at each stress level — the mismatch grows as the pulse shortens.**"],
      F24 / "gate_shape_ex2.png",
      notes="Grey: the full-swing gate. Black: the real gate under the stressed pulse. Purple: "
            "our GUP. Note that the real gate leaves zero around 0.5 ns while GUP is still flat "
            "until 1.1 ns, and that GUP's peak arrives after the real gate's.")

slide("4 · What that shape difference does downstream",
      ["Same map, two gates. The top row is Ku, the bottom row the pad.",
       "**GUP holds Ku high long after the real gate has let go — and the pad overshoot is "
       "exactly that extra area.** +74 % at 50 % stress, +4 % at 90 %."],
      F24 / "ku_consequence_ex2.png",
      notes="This is the causal chain end to end: gate shape -> Ku -> pad. At 90 % stress the "
            "two gates nearly coincide and the error nearly vanishes, which is why the failure "
            "only shows up under stress.")

# --------------------------------------------------------------------------- 5  motivation
slide("5 · So the problem is now a precise one",
      ["We know what a correct model needs: **the real gate's shape**, and the map.",
       "We have both — by probing. A customer with only the vendor's IBIS file has neither.",
       "",
       "**The question for track 1: how much of that gate shape can be recovered from the IBIS "
       "file plus one measurement taken at the pad, with nothing probed inside?**",
       "",
       "Two things have to come from somewhere: how fast the gate travels, and the map's shape. "
       "The next slides are about where each one can come from."],
      notes="This is the motivation slide, and it only works because slides 2-4 have already "
            "shown that the gate's shape is the entire error. Earlier versions of this deck "
            "asserted the motivation before showing that.")

# --------------------------------------------------------------------------- 6  method, briefly
slide("6 · What the file can and cannot give",
      ["The file records Ku(t) on one full transition. Ku(t) is the map applied to the gate — "
       "a product of the two things we need separately.",
       "**A full transition only ever visits the two ends of the gate's travel**, so any gate "
       "and map that agree at the ends reproduce the whole full-swing waveform. The file cannot "
       "separate them.",
       "**A truncated pulse stops the clock partway** — it is the only measurement that reaches "
       "the interior of the gate's path from outside the chip.",
       "That is why track 1 needs exactly one stressed pad run, and why the five stress levels "
       "are a sampling grid rather than a robustness sweep."],
      notes="This is the piece the written doc calls the sampling argument. It is the bridge "
            "from the motivation to the method, and it explains why one extra measurement is "
            "both necessary and sufficient in principle.")

slide("6 · Status of the file-only recipe",
      ["Built from the IBIS file plus one stressed pad run: C_comp from the file's own Ku ≤ 1 "
       "bound, a chain of current-limited stages fitted to the file's Ku(t), and two choices — "
       "the stage count and the map's shape — made by the one stressed run.",
       "**12 of 12 buffers within ±10 % on the worst stressed pulse; mean 6.9 %.**",
       "Cost: the full transition is worse than the shipped model on 10 of 12, and a stressed "
       "pulse train is still lost on ex2 and io_buf.",
       "",
       "**The method half of this deck needs its own pass — the equations, where each parameter "
       "comes from, and why that stage law. Flagged, not hidden.**"],
      notes="Deliberately short. The user's own feedback was that the method needs a proper "
            "walkthrough rather than a circuit diagram and a ramp; that is the next piece of "
            "work, and docs/track1_recipe.md carries the full procedure meanwhile.")

# --------------------------------------------------------------------------- backup
slide("Backup · inv_chain's input threshold",
      ["inv_chain's IBIS file declares Vinh 2.0 V on a 1.8 V part, so our input comparator fires "
       "late and trims about 29 ps off every pulse.",
       "That trim cancels most of the gate-state model's overshoot, which is why it reads −2 % "
       "at 70 % stress on the previous slides while native IBIS reads +32 %.",
       "**It is a defect that flatters us, not a result.** With the threshold at mid-supply the "
       "shipped error roughly doubles."],
      F18 / "vinh_inv.png",
      notes="Carried from the 09-18 deck so the inv_chain numbers on slide 3 are not read as a "
            "win. review_2026-09-09 item 12B has the measurement.")

OUTDIR.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
print(f"wrote {OUT.relative_to(ROOT).as_posix()}  ({len(prs.slides._sldIdLst)} slides)")
