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
        if t.startswith("  "):          # an indented line is a sub-item of the one above it
            p.level = 1
        r = p.add_run()
        r.text = t.replace("**", "").strip()
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
slide("6 · What the file gives, and what is missing",
      ["The file records Ku(t) on one full transition — and Ku(t) is the map applied to the "
       "gate. One curve, two unknowns.",
       "We now know the map is a real, fixed, measurable curve. So the missing factor is the "
       "gate's trajectory.",
       "**A full transition only ever visits the two ends of the gate's travel** — it starts "
       "at rest and finishes at the rail. Any gate that agrees at the ends reproduces the whole "
       "full-swing waveform, so the file cannot pick one.",
       "**That is exactly why our GUP passes the full-swing check and fails under stress.**"],
      notes="The file is not wrong; it is blind in a specific way. Our GUP reproduces the "
            "vendor's own full-swing waveform - that is how it was built - and the endpoints "
            "are all the full swing constrains.")

slide("7 · One stressed pulse is the measurement that reaches the gate",
      ["Cutting the input short stops the clock partway through the gate's travel. What the pad "
       "does next depends on where the gate had got to.",
       "**Each stressed width is one sample of the interior of the same path** — here the "
       "five widths stop the gate at 0.76, 0.80, 0.84, 0.88 and 0.94.",
       "So the stress sweep is a sampling grid, not a robustness check — and one pad "
       "measurement per buffer, taken from outside the chip, is the extra input track 1 needs."],
      F24 / "sampling_grid_ex2.png",
      notes="Grey is the full transition. The five coloured curves follow it and peel off at "
            "different points. This is the justification for asking the user for one stressed "
            "pad run, and for the 50-90 percent depth ladder.")

slide("8 · What shape may the gate be?  Measure a stage",
      ["A sample only helps if we know what gate shapes are possible — five samples cannot "
       "pick a curve out of all curves.",
       "So probe every stage under a short pulse and compare with what a **linear** filter would "
       "give (its own step response, superposed).",
       "**Every stage under-reaches, and the gap compounds down the chain: at the pad the linear "
       "prediction says 1.00 where the transistor does 0.50.**"],
      F24 / "stage_nonlinear_ex2.png",
      notes="This rules out RC cascades, delay-plus-RC and superposition - which is what the "
            "shipped model is built from. Data: predriver_stages_2026-09-09, whose own module "
            "computes the superposition.")

slide("9 \u00b7 The physics that explains it, and the four numbers it forces",
      ["A CMOS inverter driving a large load is a **current source** while its input sits at the "
       "rail \u2014 its device is in saturation \u2014 and becomes a **resistor** only near the "
       "destination rail, in triode. A constant current into a gate capacitance is a ramp.",
       "**That picture forces exactly four numbers per stage, and no more** \u2014 named below. "
       "s_dn is the same picture on the way back.",
       "**All four are fitted to the file's own Ku(t), so they cost no measurement.** "
       "(p, the drive's curvature under a partial input, is assumed: full swing cannot see it.)"],
      F24 / "stage_law.png",
      notes="The four are not free knobs: each names something the circuit has. x_lin is pinned "
            "at 0.45 on most buffers, inside the 0.37-0.63 the real probed stages fitted. This "
            "slide answers 'what are the equations and where do the numbers come from'.")

slide("10 · What we build",
      ["**input  →  K identical current-limited stages  →  gate g  →  the map  "
       "→  Ku  →  the file's own I-V tables  →  the pad**",
       "",
       "Each stage:   dv/dt = s_up·h(u)·min(1, (1−v)/x_lin)  −  "
       "s_dn·h(1−u)·min(1, v/x_lin),   with h(u) = clip((u − vt)/(1 − vt), 0, 1)",
       "",
       "All K stages share one set of the four numbers — a real tapered predriver is "
       "approximately that, and letting them differ makes the fit degenerate.",
       "**Two things are still unknown: how many stages, and the shape of the map.** Neither can "
       "be fitted to the file — that is what the stressed run is spent on."],
      size=17,
      notes="The map here is the two-parameter MOSFET-shaped curve, not the measured one: track "
            "1 has no probe. Its shape is one of the two things the stressed run selects.")

slide("11 · Where every number comes from",
      ["**From the file alone:** C_comp — kept unless the file's own arithmetic rejects it, "
       "since Ku cannot exceed 1 and ex2's declared 5.0 pF implies 1.24 — and s_up, s_dn, "
       "vt, x_lin, fitted to the file's Ku(t).",
       "**From the one stressed pad run:** the stage count K and the map's shape. The file "
       "narrows K to a band of about three and cannot choose inside it: at K = 7 and K = 9 it "
       "fits to the same four decimal places, while the gate they predict runs from extinguished "
       "to almost intact.",
       "**The run is spent twice, in order:** first it sets the amplitude by moving vt, then it "
       "picks among the nine candidates (3 stage counts × 3 shapes) on the whole pad waveform.",
       "**Not on the peak** — the first step has just matched the peak for every candidate, "
       "so the peak has no information left to rank them with."],
      size=17,
      notes="The peak point is the one that cost a night's work: ranking on the peak selects "
            "chains that turn on 155-300 ps late and hit the right height with the wrong pulse "
            "under it.")

slide("12 · Where the file-only recipe stands",
      ["**12 of 12 buffers within ±10 % on the worst stressed pulse; mean 6.9 %.**",
       "On inv_chain the file-only build reaches 5.1 %, against 25.8 % for a build that uses the "
       "probed silicon — the shape choice matters more than the measurement.",
       "**What it costs:** the full transition is worse than the shipped model on 10 of 12 "
       "buffers, and a stressed pulse train is still lost on ex2 and io_buf. We buy accuracy in "
       "the interior with accuracy at the endpoints."],
      ROOT / "results/track1_summary_2026-09-23/endtoend.png",
      notes="Grey is the shipped model, blue the build using probed silicon, red the file-only "
            "one. Full numbers in docs/track1_recipe.md.")

slide("13 · What this does not cover yet",
      ["**Direction.** Everything here is a short HIGH pulse. Only io_buf has been run pulling "
       "down, where the model is 16–21 points too shallow — its pull-down chain never "
       "turns on at all on a short pulse.",
       "**Depth.** The ladder samples 50–90 % of the travel. Below 50 % is unsampled.",
       "**Trains.** One pulse at a time; a stressed train is still lost on two of three buffers.",
       "**The recipe has seen the answer key.** Two of the three candidate map shapes were "
       "chosen by looking at results on these same twelve buffers. A thirteenth buffer may need "
       "a shape the grid does not contain."],
      notes="Better said than asked. The direction gap is the one that would most change the "
            "headline number.")

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
