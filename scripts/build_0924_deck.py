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
    # only the LAST emphasised line gets the accent colour: a slide where three bullets shout
    # is a slide where none of them does. Earlier emphasis stays bold, in the body colour.
    last_em = max((i for i, t in enumerate(items) if t.startswith("**")), default=-1)
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
            if k == last_em:
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
      F24 / "map_summary.png",
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
      F24 / "what_we_have.png",
      notes="This is the motivation slide, and it only works because slides 2-4 have already "
            "shown that the gate's shape is the entire error. Earlier versions of this deck "
            "asserted the motivation before showing that.")

# --------------------------------------------------------------------------- 6  method, briefly
slide("6 · What the file fixes, and what it leaves open",
      ["The file gives Ku(t) — a complete waveform, with shape at every instant. Shape is not "
       "what is missing.",
       "**What is missing is the split.** Ku(t) = map(gate(t)) fixes the composition and nothing "
       "more: pick any gate trajectory, and the map is forced to be whatever reproduces Ku(t). "
       "Every such pair matches the file exactly.",
       "With no probe we cannot measure the map, so its shape has to be assumed — and the "
       "assumed shape and the measured one are not the same curve.",
       "**Assume a different map and the fit hands you a different gate. That is the whole "
       "difficulty.**"],
      F24 / "prior_shape.png",
      size=16,
      notes="Slide 10 in the earlier cut explained where Ku(t) itself comes from - the "
            "two-fixture solve. It is now a backup slide: this audience knows it.")

slide("7 · So we need one more measurement — and a stressed pulse is the one",
      ["A full transition cannot separate them. A truncated one can: the chain then produces a "
       "**different** gate trajectory, and where it turns round depends on how fast the gate was "
       "really travelling.",
       "Each stressed width stops the gate at a different height on the same path — here at "
       "0.76, 0.80, 0.84, 0.88 and 0.94.",
       "**So the five stress levels are five independent tests of the split, and one pad "
       "measurement is what track 1 asks the user for.**"],
      F24 / "sampling_grid_ex2.png",
      notes="Grey is the full transition; the coloured curves follow it and peel off at "
            "different points. This is why the recipe needs exactly one extra measurement.")

slide("8 · But a few samples need a family of shapes to choose from",
      ["Five samples cannot pick a curve out of all possible curves. They can pick one out of a "
       "small family — so what family does this circuit actually produce?",
       "Probe every stage under a short pulse and compare against what a **linear** filter would "
       "give: its own step response, superposed.",
       "**Every stage under-reaches, and the gap compounds down the chain — at the pad the "
       "linear prediction says 1.00 where the transistor does 0.50. So the family is not "
       "linear.**"],
      F24 / "stage_nonlinear_ex2.png",
      size=17,
      notes="This rules out RC cascades, delay-plus-RC and superposition - which is what the "
            "shipped model is built from.")

slide("9 · The family: a stage is a current source with a threshold",
      ["A CMOS inverter driving a large load is a **current source** while its input sits at the "
       "rail, because its conducting device is in saturation. Only near the destination rail does "
       "it leave saturation and become a resistor.",
       "**A constant current into a gate capacitance is a ramp, tapering at the end** — which "
       "is what the measured stages do."],
      F24 / "stage_law.png",
      notes="Left: the input and the threshold it must pass. Right: the output the constant "
            "current produces. The next slide turns this picture into the four numbers.")

slide("10 · The four numbers that picture requires",
      ["Written out, the stage law has exactly four free numbers and no more. Each one is a "
       "named part of the picture on the last slide, not a fitting coefficient.",
       "**Three are fitted to the file and cost nothing. One, vt, is fitted and then re-set by "
       "the single stressed run — that is step 4.**"],
      F24 / "four_numbers.png",
      notes="Colours tie each term of the equation to its row. u is the stage's input, v its "
            "output, both on their own 0-to-1 swing.")

slide("11 · What each of the four actually does",
      ["Each swept on its own about the value the fit chose, on the 810 ps pulse. The thick black "
       "trace is the fitted value.",
       "**Look at the vt panel: pushed high enough the gate never leaves the floor — a chain "
       "can extinguish a short pulse, not merely shrink it.**"],
      F24 / "knobs.png",
      notes="Simulated with the project's own stage model from the fitted values the 09-17 film "
            "exported.")

slide("12 · Why a chain of K of them",
      ["The real predriver **is** a chain — the schematic earlier showed three inverters between "
       "ex2's input and its output gate, and the stage walk watched a pulse lose height at each.",
       "We cannot see how many a vendor's part has, so the count K is a parameter. The stages are "
       "held **identical**: a real tapered predriver approximately is, and letting them differ "
       "makes the fit degenerate.",
       "**Everything to the right of the gate is the file's own, untouched — the map and the "
       "I-V tables. We are only building the left-hand box.**"],
      F24 / "model_blocks.png",
      size=17,
      notes="Degenerate: a free fit splits the delay into one sluggish stage plus one quick one, "
            "reproduces the full swing slightly better, and predicts a stressed gate of 0.23 "
            "against a measured 0.76.")

slide("13 · Step 1 — C_comp, rejected by the file's own arithmetic",
      ["Ku is a fraction of the device's own current, so it cannot exceed 1. Solve the file at a "
       "range of assumed C_comp and watch what the solve returns.",
       "**ex2's declared 5.0 pF makes the file imply Ku = 1.24 — impossible. The file rejects "
       "its own declared value.**",
       "So: keep what the file declares unless it implies Ku > 1, then take the value at which Ku "
       "just reaches 1. That reads 2.64 pF here, against 1.70 measured with a probe — 55 % "
       "off, and it still works, because the stressed peak is not sharp in C_comp."],
      F24 / "ccomp_reject.png",
      size=17,
      notes="C_comp is not a model parameter: it is a number the file's own Ku tables were "
            "solved with, so a wrong value inflates the curve everything downstream is fitted to.")

slide("14 · Step 2 — the four numbers, fitted to the file's Ku(t)",
      ["The four are searched until the chain's output, put through the map, reproduces **the "
       "file's own full-swing Ku(t)** — the black curve. Nelder–Mead, three restarts.",
       "Error 0.284 down to 0.0098, landing on s_up 2.59, s_dn 2.38, vt 0.51, x_lin 0.66.",
       "**No measurement is involved: the target is a curve the file already contains.**"],
      F24 / "fit_search.png",
      notes="Every trial the optimiser actually took, exported live by the 09-17 film. What it "
            "does NOT give us is K, or the map's shape.")

slide("15 · Step 3 — what the file cannot choose",
      ["Left: the fit error against the file's Ku(t), for every stage count. Past K = 3 it is "
       "**flat** — the file has nothing left to say.",
       "Right: the three candidates inside that band, on one 810 ps pulse. Same file, same fit "
       "quality, **three completely different buffers**.",
       "**The map's shape is under-determined in the same way** (slide 7). Three stage counts "
       "× three map shapes = nine candidates."],
      F24 / "k_choice.png",
      notes="The three shapes are (0.50, 0.70), (0.40, 0.60) and (0.40, 0.90). Note on the right "
            "that all three already match the peak - that is the calibration, and it is why the "
            "peak cannot be what chooses.")

slide("16 · Step 4 — the stressed run, first job: set the amplitude",
      ["Now the measured waveform enters. **Fitted to the file alone the chain leaves the 810 ps pad 28 % low** — the file can set the shape, but not the amplitude.",
       "So bisect vt against the measured peak. The two spikes are the bracket being probed first: vt = 0 overshoots by 26 %, vt = 0.7 kills the pulse entirely at −99 %. Then halve. Ten runs, landing on vt 0.487 and +1.4 %.",
       "**Why vt and not the drive rates? The rates were fitted to reproduce the full swing, and moving them breaks it. vt changes when the chain hands off, not how fast it runs.**"],
      F24 / "bisection.png",
      notes="Every iteration the calibration actually wrote, recovered from the netlists it "
            "emitted. The vt here is the film's ex2 case; the deck's own K = 3 build lands on "
            "0.632 from a different starting fit.")

slide("17 · Step 5 — the stressed run, second job: pick one",
      ["All nine candidates are now calibrated, so **all nine hit the measured peak** — the "
       "calibration put it there. Right-hand panel: ranked on the peak every one is within 2.5 %, "
       "in no meaningful order.",
       "Left-hand panel: score each one against the **whole** measured waveform instead, over the "
       "pulse and its return. Now they separate, from 59 mV to over 200.",
       "**That ranking is the choice. The recipe keeps the top row — here K = 3 with the "
       "0.50/0.70 shape, which is also the best of the nine outright.**"],
      F24 / "pick_rank.png",
      size=17,
      notes="Ranking on the peak instead picks a chain that arrives up to 300 ps late with four "
            "times the waveform error. The nine waveforms themselves are the backup slide.")

slide("18 · The recipe, end to end",
      ["**From the file alone:** C_comp, kept unless its own Ku > 1 test rejects it; then s_up, "
       "s_dn, vt, x_lin fitted to the file's Ku(t) at each stage count in the band.",
       "**Left undetermined by the file:** the stage count and the map's shape — nine "
       "candidates in all.",
       "**From one stressed pad run, in order:** bisect vt until the peak matches, then pick the "
       "candidate whose whole waveform matches.",
       "**Nothing is probed.** The only measurement is a pad voltage, from outside the chip."],
      F24 / "model_blocks.png",
      size=16,
      notes="The same block diagram as slide 12, now with the recipe attached to it. This is the "
            "slide to leave up during questions.")

slide("Where the file-only recipe stands",
      ["**12 of 12 buffers within ±10 % on the worst stressed pulse; mean 6.9 %.**",
       "On inv_chain the file-only build reaches 5.1 %, against 25.8 % for a build that uses the "
       "probed silicon — the shape choice matters more than the measurement.",
       "**What it costs:** the full transition is worse than the shipped model on 10 of 12 "
       "buffers, and a stressed pulse train is still lost on ex2 and io_buf. We buy accuracy in "
       "stressed accuracy with full-swing accuracy."],
      ROOT / "results/track1_summary_2026-09-23/endtoend.png",
      notes="Grey is the shipped model, blue the build using probed silicon, red the file-only "
            "one. Full numbers in docs/track1_recipe.md.")

slide("What this does not cover yet",
      ["**Direction.** Everything here is a short HIGH pulse. Only io_buf has been run pulling "
       "down, where the model is 16–21 points too shallow — its pull-down chain never "
       "turns on at all on a short pulse.",
       "**Depth.** The ladder samples 50–90 % of the travel. Below 50 % is unsampled.",
       "**Trains.** One pulse at a time; a stressed train is still lost on two of three buffers.",
       "**The recipe has seen the answer key.** Two of the three candidate map shapes were "
       "chosen by looking at results on these same twelve buffers. A thirteenth buffer may need "
       "a shape the grid does not contain."],
      F24 / "coverage.png",
      notes="Better said than asked. The direction gap is the one that would most change the "
            "headline number.")

# --------------------------------------------------------------------------- backup
slide("Backup · where Ku(t) comes from",
      ["The file holds the I-V curves and recordings of one transition into **two different "
       "loads**. At any instant the pad took some current, and both branches supplied it.",
       "Two loads give two equations in the same two unknowns, so one instant gives Ku and Kd "
       "outright — no fitting. Repeat at every instant and the result is Ku(t)."],
      F24 / "solve_ku.png",
      notes="Moved out of the main line: this audience knows where Ku comes from.")

slide("Backup · the nine candidates as waveforms",
      ["The same nine as step 5, drawn rather than ranked: all sharing the measured peak because "
       "the calibration put it there, and separating in the tail.",
       "**The one the recipe picks sits on the transistor.**"],
      F24 / "calib_select.png",
      notes="This was the main slide before; the ranking says the same thing more directly.")

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
# an open deck is locked by PowerPoint, so fall back to a versioned name rather than fail and
# lose the build (the repo rule: never save over a deck someone has open)
dest = OUT
try:
    prs.save(dest)
except PermissionError:
    dest = OUT.with_name(OUT.stem + "_v2.pptx")
    prs.save(dest)
    print(f"  {OUT.name} is open in PowerPoint; wrote a versioned copy instead")
print(f"wrote {dest.relative_to(ROOT).as_posix()}  ({len(prs.slides._sldIdLst)} slides)")
