#!/usr/bin/env python3
"""Update the 2026-09-11 deck. Inserted, in order:

  after 'Fix from last time' (old 6):  the cmd_clean command slide
  after 'New fix: result' (old 8):     two identical pulses (does the error accumulate?)
  old 9 'More SPICE buffer mockups' -> variant table (open-drain included)
  after it:                            six variant slides, message titles, + wrap-up
  after the wrap-up:                   four open-drain slides

Each picture slide has a 'How to read it' box and a 'What it shows' box (and the same text in
the speaker notes). Everything else in the deck is untouched.

    py -3.14 scripts/build_0911_deck.py --src <path to 0911_Simon_IBIS.pptx> --out <path>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
from pptx import Presentation  # noqa: E402
from pptx.util import Inches, Pt  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from PIL import Image  # noqa: E402

FIGS = ROOT / "results" / "meeting_deck_2026-09-11" / "figures"

CMD_SLIDE = ("New fix: enforce clean targets at source — the command", "cmd_clean_command.png",
             ["Panel 1: the input pulse (io_buf, 1792 ps). Panel 2: the command node that tells the gate what to do. Panel 3: the pull-up gate state that follows it.",
              "Orange = original build, green = cmd_clean. Look at panel 2 after the falling edge."],
             ["The original command is a capacitor charged by an edge packet: a short pulse leaves it stranded at −0.08 and it leaks away over ~4 ns. "
              "cmd_clean makes the command a delayed copy of the input level, so it is exactly 0 or 1 by construction and needs no cleanup.",
              "Everything on the next two slides (GUP, Ku, pad) follows from this one change."])

TWO_PULSE_SLIDE = ("Two identical pulses: does the error accumulate?", "two_pulses.png",
                   ["Same pulse twice. Top row: 6 ns gap, everything has settled before the second pulse. Bottom row: gap equal to the width (50 % duty), the second pulse lands on the tail of the first.",
                    "Left io_buf at 1792 ps (the slide 9 case), right ex2 at 858 ps. Dashed lines are the input edges. The title gives, per pulse, each model's peak-time shift and peak error against the transistor."],
                   ["Settled gap: pulse 2 repeats pulse 1 to within 10 ps and 2 mV on both buffers. Nothing carries over once the pad and the internal nodes are back at rest.",
                    "Unsettled gap: the error does not grow either, it changes. ex2's second pulse starts from the tail, so the transistor peaks higher and the models' overshoot turns into −70 mV. "
                    "On io_buf native collapses (+517 mV, its pull-up latches on) while cmd_clean stays within 2 mV. The error is per pulse, set by the state the pulse starts from, not a debt that accumulates."])

VARIANT_SLIDES = [
    ("Twelve buffers: the pulse width that reaches 50 % is set by the predriver", "variants_same_stress.png",
     ["Transistor only, no models. Left: the five ex2 variants; right: the four inv variants.",
      "Every curve is the pad at 50 % depth (the pulse made just short enough that the pad reaches half its full swing), normalised to that variant's own full swing, time from the input reversal.",
      "The legend gives the pulse width each variant needed to reach 50 %."],
     ["The width that reaches 50 % is set by the predriver: slowpre needs 1094 ps where base needs 812; stage4 needs 83 ps where base8 needs 102.",
      "Within a family the shape after the reversal is the same; the output stage sets the amplitude, the predriver sets the timing. This is the first hint that the stress problem lives in the predriver."]),
    ("The stressed overshoot is universal: every push-pull variant, ours and native alike", "variants_model_vs_si.png",
     ["One panel per variant, all at 50 % depth. Black = HSPICE transistor (truth). Green dashed = ours, the cmd_clean gate-state model of slides 7 to 9. Blue = HSPICE's own IBIS model on the same file.",
      "Blue dotted = native 'dead'. At full swing native reads these files correctly (same pad, Ku, Kd as the shipped file). It fails only when the stressed reversal lands inside the rising table's lead-in: "
      "our tables are sampled at 2.7 ps and carry sub-mV ripple there, HSPICE's two-waveform solver leaves its states slightly off at that instant and never recovers, with no warning. "
      "Tables at 8 ps spacing, or smoothed, survive the same reversal. A simulator artefact, not our setup.",
      "The title of each panel gives the peak error."],
     ["Our model peaks 34 to 71 % too high on all nine variants. Wherever native's solver runs (inv base8, skewp, weak) it fails the same way, within 3 % of ours.",
      "So the fix of slides 7 to 9 solved io_buf's problem and left a bigger one untouched on the other eleven buffers, and that problem is in the IBIS mechanism itself, not in our converter."]),
    ("It is a law: the shorter the pulse, the larger the overshoot", "variants_depth_waves.png",
     ["Top row ex2 base, bottom row inv base8. Left to right the pulse gets shorter: 90, 80, 70, 60, 50 % depth.",
      "Same colours as before; the vertical dashed line is the input reversal. Read the black peak against the green peak in each panel."],
     ["The transistor's peak falls with the pulse width. The models' peak barely moves, so the error grows smoothly from a few percent to +71 % (ex2) and +64 % (inv).",
      "A smooth, monotone law on every push-pull buffer means one mechanism, not noise. The next two slides find it."]),
    ("What controls it: the predriver's timing relative to the pulse, not the output devices", "variants_change_waves.png",
     ["Every panel is 50 % depth. Top row ex2: base, then the predriver halved (slowpre), then the output stage halved (weak). Bottom row inv: base8, then half the stage count (stage4), then half drive everywhere (weak).",
      "Compare each panel's peak error with its family's base panel on the left."],
     ["ex2: halving the output stage changes nothing (+71 → +66 %); halving the predriver takes a third off (+45 %).",
      "inv: stage count and drive both take a third to a half off, because on a 100 ps pulse the output stage's own speed limits the pad as well. Either way the error follows timing relative to the pulse, which is exactly what the command layer represents."]),
    ("Why: the model's pull-up is still fully on when the transistor's has already begun to close", "variants_mechanism_waves.png",
     ["Top row: Ku, the fraction of the pull-up that is 'on', for the transistor (black), ours (green) and native (blue). Bottom row: the pads.",
      "The red vertical line is the instant the transistor's pad peaks. Read the two Ku values printed at that line."],
     ["When the transistor's pad peaks, its pull-up is only 26 to 38 % on: its predriver, interrupted by the reversal, is already closing the gate.",
      "Ours is still 90 to 114 % on, because a delayed command cannot be interrupted, so our pad keeps rising. Over 68 cases this 'entry excess' explains the peak error with r = 0.89. This is the root cause: the command is a delay, and a delay cannot be caught half way."]),
    ("Two regimes: io_buf is caught mid-gate (last week's fix); the eleven need an interruptible command", "variants_regime_waves.png",
     ["Left io_buf (1792 ps pulse), right ex2 (858 ps), from the same stress matrix. Top: Ku; bottom: pad. Dashed = input reversal, red = transistor's pad peak.",
      "io_buf's annotation reads the gate just before the reversal (the solved Ku is unusable within ~90 ps of it); ex2's reads it at the pad peak."],
     ["io_buf: the gate is slower than the pulse, so the reversal catches it still opening (Ku 0.47 and rising). Both models follow through the peak; the error is the residual afterwards, which is what slides 5 to 9 fixed.",
      "ex2: the pad peaks 700 ps after the reversal, by which time the transistor has closed its gate again (Ku 0.37 and falling) while both models are still at 0.9. The other ten variants are in ex2's regime; for them the command itself has to become something a reversal can interrupt."]),
]

WRAPUP = ("What the twelve buffers say",
          ["The stress error is not a property of one buffer or of our converter: every push-pull variant overshoots, native included, by the same law.",
           "Its size is set by the predriver's timing relative to the pulse, the one thing an IBIS file does not describe.",
           "The mechanism is a command that cannot be interrupted: a delayed edge turns the model fully on while the transistor's gate is already closing.",
           "io_buf is the exception because its gate is slower than the pulse; last week's residual fixes belong to that regime only.",
           "Next: replace the delay by a chain of current-limited stages fitted from the file's own tables, so a reversal can catch it half way (prototype results next week)."])

OD_SLIDES = [
    ("Open-drain 1/4: full swing, one pulse, every build", "od_fullswing.png",
     ["Open-drain ex2: the pull-up transistor is removed, a 50 Ω resistor to VCC holds the pad high, the buffer can only pull it down and let it go. One 3 ns LOW pulse; dashed lines are the input edges. Top: pad. Bottom: Kd, the fraction of the pull-down that is on.",
      "Black = transistor (its Kd solved from this bench, C_comp 3 pF). Blue = native. Orange dotted = our legacy build, the only open-drain build the converter had until this week. Grey = the new gate-state build. Green dashed = the chain recipe on top of it.",
      "On this bench the release is nearly as fast as the pull-down because 50 Ω × 2 pF is only 100 ps; with a weaker pull-up the release would show the classic slow open-drain rise."],
     ["The legacy build was wrong before any edge: it rested pulled-low (1.33 V) and was 120 to 140 ps late; the converter simply had no gate-state path for Open_drain.",
      "The gate-state build now runs the pull-down half of the push-pull machinery: right rest state, right Kd shape, 130 ps late on the pull-down and 80 ps on the release. The chain brings both edges within 35 ps of the transistor. Native is 35 ps early on both."]),
    ("Open-drain 2/4: under stress, the same story as the push-pull eleven", "od_stress.png",
     ["Short LOW pulses, 750 to 620 ps, the transistor's depth falling from 90 % to 4 %. Top: pad. Bottom: Kd, the fraction of the pull-down that is on. Same colours as the previous slide; the legacy build is left off here (it looks like native, only worse).",
      "Read the transistor's Kd peak against each model's Kd peak in the bottom row."],
     ["The transistor's Kd at the minimum falls with depth, 0.77 → 0.02: its predriver is interrupted before the gate opens. Native (and the legacy build) stay at 1.0 at every width, so they pull the pad all the way down every time (up to 1.9 V too far).",
      "The gate-state build follows partly (1.02 → 0.74). The chain, fitted on the file's own tables plus one stressed pad point, follows to the calibration depth and stays within ~200 mV below it. Open-drain shows the push-pull mechanism with nothing else in the way."]),
    ("Open-drain 3/4: the pull-down's own curve, and why the pull-up's does not fit it", "od_kd_map.png",
     ["Left: the transistor's Kd plotted against its own gate voltage n4 (0 = released, 1 = fully on), one colour per pulse width, full swing included. Right: the same map with one point per width, taken at the pad minimum.",
      "Red dashed = a MOSFET-shaped fit (threshold, power, saturation). Grey dotted = the pull-up curve we used for the push-pull buffers."],
     ["All eight widths fall on one curve (rms 0.008): the output stage is a static map of the gate on the open-drain too.",
      "The NMOS turns on at 20 % of its gate swing where the PMOS curve assumed 52 %. With the wrong threshold the chain's depth law is far too soft; with the measured one it tracks. Push-pull stress never exposed this because those pulses never cut into the pull-down's turn-on."]),
    ("Open-drain 4/4: three variants, four builds", "od_summary.png",
     ["One column per open-drain variant (base, pull-down halved, predriver halved). Top: model low minus transistor low in mV against depth (negative = pulls too far). Bottom: Kd at the transistor's pad minimum.",
      "Orange = legacy, grey = gate-state, green = chain, blue = native. The dotted vertical line is the one width used to calibrate the chain."],
     ["On base and od_slowpre the gate-state build beats native at every depth; on od_weak native malfunctions outright (it drives the pad above the rail), so ours is the only working IBIS model there.",
      "The chain is within 14 % of the transistor from 90 % depth down to the calibration point on all three, and over-drives below it: the transistor's cliff at the shallow end is sharper than the chain's, the same missing degree of freedom seen on the pulse trains."]),
]

VARIANT_TABLE = [
    ("family", "variant", "what changed in the silicon", "what it tests", "stress runs"),
    ("ex2 (3.3 V, 3-stage predriver, extracted layout)", "base", "as shipped, rebuilt through the same generator", "reference", "5 depths"),
    ("", "weak", "both output devices at half width", "output drive strength", "5 depths"),
    ("", "skewp", "output PMOS at half width", "rise/fall asymmetry", "5 depths"),
    ("", "slowpre", "all three predriver stages at half width", "predriver speed (the command)", "5 depths"),
    ("", "nomiller", "gate-to-drain caps removed", "Miller feedthrough", "5 depths"),
    ("", "opendrain", "pull-up removed, Model_type Open_drain", "single-device, single-fixture IBIS", "8 low-pulse widths"),
    ("", "od_weak", "open-drain, pull-down at half width", "open-drain drive", "8 widths"),
    ("", "od_slowpre", "open-drain, predriver at half width", "open-drain predriver", "8 widths"),
    ("inv (1.8 V, tapered inverter chain)", "base8", "8 stages, ×2 taper, Wn 1 / Wp 2 µm", "reference", "7 depths"),
    ("", "stage4", "4 stages, same final drive", "predriver depth (stage count)", "7 depths"),
    ("", "skewp", "Wp = Wn (weak PMOS)", "rise/fall asymmetry", "5 depths"),
    ("", "weak", "half drive at every stage", "drive at fixed timing structure", "5 depths"),
]


def clear_content_placeholders(s):
    for sh in list(s.placeholders):
        if sh.placeholder_format.idx != 0:
            sh._element.getparent().remove(sh._element)


def add_text(s, left, top, width, height, heading, lines, size=10, bullets=True):
    tb = s.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = heading
    r.font.bold = True
    r.font.size = Pt(size + 1)
    r.font.color.rgb = RGBColor(0x1F, 0x6F, 0x78)
    for line in lines:
        p = tf.add_paragraph()
        r = p.add_run()
        r.text = ("• " if bullets else "") + line
        r.font.size = Pt(size)
    return tb


def add_picture_slide(prs, layout, title, png, how, what):
    s = prs.slides.add_slide(layout)
    s.shapes.title.text = title
    clear_content_placeholders(s)
    box_l, box_t, box_w, box_h = Inches(0.3), Inches(0.9), Inches(12.7), Inches(4.45)
    im = Image.open(FIGS / png)
    ar = im.width / im.height
    w = box_w
    h = int(w / ar)
    if h > box_h:
        h = box_h
        w = int(h * ar)
    left = box_l + int((box_w - w) / 2)
    s.shapes.add_picture(str(FIGS / png), left, box_t, width=w, height=h)
    add_text(s, Inches(0.35), Inches(5.4), Inches(6.2), Inches(2.0), "How to read it", how, size=10)
    add_text(s, Inches(6.75), Inches(5.4), Inches(6.2), Inches(2.0), "What it shows", what, size=10)
    s.notes_slide.notes_text_frame.text = "How to read: " + " ".join(how) + "\nWhat it shows: " + " ".join(what)
    return s


def add_text_slide(prs, layout, title, lines):
    s = prs.slides.add_slide(layout)
    s.shapes.title.text = title
    clear_content_placeholders(s)
    tb = s.shapes.add_textbox(Inches(0.6), Inches(1.3), Inches(12.0), Inches(5.5))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for line in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        r = p.add_run()
        r.text = "• " + line
        r.font.size = Pt(18)
        p.space_after = Pt(14)
    return s


def variant_table_slide(s):
    clear_content_placeholders(s)
    tb = s.shapes.add_textbox(Inches(0.35), Inches(0.85), Inches(12.6), Inches(0.5))
    tb.text_frame.word_wrap = True
    tb.text_frame.text = ("Twelve buffers from the two extracted designs, each changing one thing. Push-pull variants were run at 5 to 7 stressed depths "
                          "(90 % down to 50 %); the open-drain ones at 8 short-LOW pulse widths into 50 Ω to VCC. Results on the next slides.")
    for p in tb.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(11)
    rows, cols = len(VARIANT_TABLE), 5
    shape = s.shapes.add_table(rows, cols, Inches(0.35), Inches(1.45), Inches(12.6), Inches(5.6))
    table = shape.table
    for j, w in enumerate([2.6, 1.2, 3.9, 3.2, 1.7]):
        table.columns[j].width = Inches(w)
    for i, row in enumerate(VARIANT_TABLE):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(10.5 if i else 11)
                    r.font.bold = (i == 0) or (j == 1)
    table.cell(1, 0).merge(table.cell(8, 0))
    table.cell(9, 0).merge(table.cell(12, 0))
    table.cell(1, 0).text = VARIANT_TABLE[1][0]
    table.cell(9, 0).text = VARIANT_TABLE[9][0]
    for i in (1, 9):
        for p in table.cell(i, 0).text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(11)
                r.font.bold = True


def move_slide(prs, old_index, new_index):
    sld = prs.slides._sldIdLst
    el = list(sld)[old_index]
    sld.remove(el)
    sld.insert(new_index, el)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    prs = Presentation(str(args.src))
    layout = prs.slides[8].slide_layout
    n0 = len(prs.slides)  # 14 in the source deck

    variant_table_slide(prs.slides[8])
    prs.slides[8].shapes.title.text = "More SPICE buffer mockups: twelve variants"

    # build the new slides at the end, then move them into place (last first so indices stay simple)
    new = []
    new.append(("cmd", add_picture_slide(prs, layout, *CMD_SLIDE)))
    new.append(("two", add_picture_slide(prs, layout, *TWO_PULSE_SLIDE)))
    for t, png, how, what in VARIANT_SLIDES:
        new.append(("var", add_picture_slide(prs, layout, t, png, how, what)))
    new.append(("wrap", add_text_slide(prs, layout, *WRAPUP)))
    for t, png, how, what in OD_SLIDES:
        new.append(("od", add_picture_slide(prs, layout, t, png, how, what)))
    # target positions (0-based) in the final order:
    #   0-5 original 1-6 | 6 cmd | 7-8 original 7-8 | 9 two | 10 table (orig 9) | 11-16 variants | 17 wrap | 18-21 od | 22.. original 10-14
    order = ["cmd", "two", "var", "var", "var", "var", "var", "var", "wrap", "od", "od", "od", "od"]
    targets = [6, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
    for j, tgt in enumerate(targets):
        move_slide(prs, n0 + j, tgt)
    toc = prs.slides[1]
    for sh in toc.placeholders:
        if sh.placeholder_format.idx != 0 and sh.has_text_frame:
            for p in sh.text_frame.paragraphs:
                if p.text.strip() == "More SPICE buffer mockups":
                    p.runs[0].text = "More SPICE buffer mockups: twelve variants, stressed results, open-drain"
    prs.save(str(args.out))
    print("wrote", args.out, "slides:", len(prs.slides))
    for i, s in enumerate(prs.slides, 1):
        print(f"  {i:2d} {(s.shapes.title.text if s.shapes.title is not None else '')}".encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
