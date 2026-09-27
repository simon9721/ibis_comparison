#!/usr/bin/env python3
"""Build the meeting deck for the deliverables in 0902_plan.md.

Style follows the earlier deck that read better than this one's first draft:

* **Simulation figures only.** No bar charts, no scatter plots, no schematics.
  A number is explained by listing it, not by drawing it as a bar.
* **Short bullets, then the picture.** Two or three lines stating the point, and
  the rest of the slide is the waveform.
* **Pad and coefficients side by side** for the same case, so the pad shape and
  the Ku/Kd behind it are read together.

Numbers are quoted from the plan and from the study directories it points at,
including the results that overturned earlier claims; those stay on the slides,
because a reviewer who finds a reversal afterwards trusts the rest less.

    py -3.14 scripts/build_deck_figures.py     # first, if results changed
    py -3.14 scripts/build_0902_meeting_deck.py
    powershell -ExecutionPolicy Bypass -File scripts/render_deck_slides.ps1 `
        -Deck results/meeting_deck_2026-09-04/ibis_pybis_status_2026-09-04.pptx
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tools.presentation_kit import GreenDeck  # noqa: E402

R = ROOT / "results"
OUT = R / "meeting_deck_2026-09-04" / "ibis_pybis_status_2026-09-04.pptx"
F = R / "meeting_deck_2026-09-04" / "figures"

FIG = {k: F / f"{k}.png" for k in
       ("recap_pad", "recap_kukd",
        "clean_edge", "stress_pad", "stress_kukd", "timing_shift",
        "offset_chain",
        # Last week's two pages, redrawn with cmd_clean as a third curve.
        # scripts/build_cmd_clean_slides.py, both on io_buf 1792 ps.
        "cmd_clean_gate_and_ku", "cmd_clean_pad",
        "fixture_vt", "fixture_ku", "variant_pad", "variant_kukd")}

# One wide figure under two lines of text, and the pair layout beside it.
WIDE = dict(x=0.55, y=2.02, w=12.2, h=4.95)
# For figures that carry their own title line: no bullets, so the picture starts
# right under the rule and gets the rest of the slide.
TALL = dict(x=0.55, y=1.35, w=12.2, h=5.75)
LEFT = dict(x=0.45, y=2.28, w=6.1, h=4.75)
RIGHT = dict(x=6.75, y=2.28, w=6.1, h=4.75)


def points(deck, slide, items, y=1.28, size=17.0):
    """The two or three lines that state the point, above the figure."""
    return deck.add_bullets(slide, items, 0.7, y, 12.1, 0.75 * len(items),
                            size=size, spacing=3)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    missing = [k for k, v in FIG.items() if not v.exists()]
    if missing:
        print("missing figures: " + ", ".join(missing)
              + "\n  run: py -3.14 scripts/build_deck_figures.py")
        return 1

    d = GreenDeck()
    d.set_title_slide(
        "IBIS Simulation Short Pulse Handling",
        "Simon Hwang\nDr. Chulsoon Hwang\nDr. Zhiping Yang\n9/4/2026")

    # ---------------------------------------------------------------- contents
    s = d.add_slide("Table of contents")
    points(d, s, [
        "Issue recap",
        "Delaying the input command",
        "RLC fixture effects on V-t waveforms and Ku/Kd",
        "Pybis in HSPICE vs. NgSPICE",
        "More SPICE buffer mockups",
    ], y=1.5)

    # ------------------------------------------------------------ issue recap
    s = d.add_slide("Issue recap", section="Issue recap")
    points(d, s, [
        "A short pulse reverses before the pad has finished its transition.",
        "Through the edge all three agree. Our pad stays high afterwards.",
    ])
    d.add_picture_contain(s, FIG["recap_pad"], **WIDE)

    s = d.add_slide("Issue recap — the coefficients", section="Issue recap")
    points(d, s, [
        "Ku(t) and Kd(t) assume the transition starts from a settled state.",
        "When the reverse edge arrives first, they are still replayed from fully "
        "settled, and Ku does not return to zero.",
    ])
    d.add_picture_contain(s, FIG["recap_kukd"], **WIDE)

    # ------------------------------------------------------------ the offset
    s = d.add_slide("The offset: the command bucket never empties",
                    section="Delaying the input command")
    points(d, s, [
        "GUPCMD is a bucket: one fixed pour in on the rising edge, one back out "
        "on the falling edge.",
        "On a truncated pulse the two pours are not equal, and there is no drain "
        "— so some is left.",
    ])
    d.add_picture_contain(s, FIG["offset_chain"], **WIDE)
    d.add_notes(s, "The sign of the stranded charge flips with the timestep, so it "
                   "is an integration error. Any fix by tuning a coefficient is a "
                   "coin flip, which is why the retuned version helped on some "
                   "cases and not others.")

    # ------------------------------------------- last week's two pages, redrawn
    s = d.add_slide("GUP and Ku", section="Delaying the input command")
    d.add_picture_contain(s, FIG["cmd_clean_gate_and_ku"], **TALL)
    d.add_notes(s, "Last week's page, with cmd_clean added as a third curve. Same "
                   "case, same colours -- fix_old is the purple that was labelled "
                   "'fix' last week. On the tail, 1.0 to 1.7 ns after the "
                   "reversal, the command GUPCMD sits at +0.036 original, +0.024 "
                   "fix_old, +0.000 cmd_clean. The gate state is a lag on the "
                   "command, so it copies that straight through, and Ku scales it "
                   "by about 1.18. fix_old does eventually clear, but not until "
                   "8.7 ns -- the restore gate does not open until the reversal "
                   "plus 3.0 ns, and the pad has been holding the offset since "
                   "7.5. That is why last week's approach drove the command back "
                   "to a clean 0 and still left the pedestal: it was late, not "
                   "wrong. cmd_clean is at zero from the start because the "
                   "command is read off the present input level rather than "
                   "accumulated from past edges. The code calls that build "
                   "delay_cmd.")

    s = d.add_slide("Pad voltage", section="Delaying the input command")
    d.add_picture_contain(s, FIG["cmd_clean_pad"], **TALL)
    d.add_notes(s, "The same three builds at the pad, against both references. "
                   "Measured on the same 1.0 to 1.7 ns window: transistor 5.9 mV, "
                   "native IBIS 6.2, original 76.3, fix_old 51.9, cmd_clean 4.0. "
                   "fix_old removes a third of the pedestal; cmd_clean removes "
                   "all of it. Across all 29 matched stress cases RMSE goes from "
                   "108.6 to 92.2 mV, the only build that beats native IBIS. "
                   "Caveat worth stating out loud: cmd_clean has a dead zone of "
                   "about 0.9 ns after a reversal, the gap between the fitted "
                   "on-delay and off-delay, where neither device is commanded on. "
                   "At a 500 ps delay it gives 0.043 V where the original gives "
                   "0.122; above about 1.2 ns the two are identical.")

    # -------------------------------------------------- but not the timing
    s = d.add_slide("It does not fix the timing", section="Delaying the input command")
    points(d, s, [
        "cmd_clean improved the timing on 0 of 19 stress cases — two mechanisms, "
        "not one.",
        "Our 50% crossing still arrives after native's: io_buf +27..+34 ps against "
        "native's +11..+18.",
    ])
    d.add_picture_contain(s, FIG["timing_shift"], **WIDE)
    d.add_notes(s, "Why it cannot help: the edge timing is set by the gate lag and "
                   "the Ku(t) map, and cmd_clean changes neither -- it changes only "
                   "how the command that drives them is generated. Measured on one "
                   "truncated pulse, the 50% crossing of every node moves by single "
                   "digits: GUPCMD -4.5 ps, GUP -8.2, Ku -13.6, pad -7.5, against a "
                   "model-to-transistor shift of 27 to 46 ps. cmd_clean changes what "
                   "is left behind, not how fast the edge moves. "
                   "The plan quotes 69-99 ps late where native is 5-26 ps early. "
                   "That is not reproducible from the data on disk with a "
                   "50%-of-excursion metric. The stress matrix gives io_buf native "
                   "+11..+18 against ours +27..+34; inv_chain native -6..-5 "
                   "against ours +8..+12; ex2 both early with ours closer. The "
                   "defect is real and device-dependent, but smaller and less "
                   "one-sided than the plan states. It also grows as the pulse is "
                   "truncated, on all nine buffer variants tested so far.")

    # --------------------------------------------------------------- engine
    s = d.add_slide("Is the difference the engine or the model?",
                    section="Pybis in HSPICE vs. NgSPICE")
    points(d, s, [
        "Every native-vs-ours number changes two things at once. We wrote a "
        "translator so the same model runs in both simulators.",
    ])
    d.add_text(s, "Falling 50% crossing:", 0.7, 2.3, 12.0, 0.5, size=17)
    points(d, s, [
        "our model in ngspice     5.3371 ns",
        "our model in HSPICE      5.3375 ns     engine:  −0.5 ps",
        "native IBIS in HSPICE    5.3319 ns     model:   +5.6 ps",
    ], y=2.9)
    d.add_text(s, "The engine is not the source — provided ngspice is converged. "
                  "At a 1 ps step it was an aliasing outlier that doubled the "
                  "apparent lag.", 0.7, 5.0, 12.0, 1.0, size=17)

    # ------------------------------------------------------------- fixtures
    s = d.add_slide("What fixtures do to the extracted Ku/Kd", section="RLC fixture effects")
    points(d, s, [
        "Five fixtures, Ku re-solved on each. In the quiet regions all five "
        "agree to four decimals.",
        "Series inductance disturbs it, and only on io_buf.",
    ])
    d.add_picture_contain(s, FIG["fixture_vt"], **LEFT)
    d.add_picture_contain(s, FIG["fixture_ku"], **RIGHT)
    d.add_notes(s, "The control reproduces the shipped solve to 2.4e-08, so the "
                   "method is exact, and in the quiet regions Ku is "
                   "load-independent to four decimals -- the extraction really is "
                   "a device property, not a fixture artifact.  "
                   "Ku RMSE against the R-only baseline:  "
                   "io_buf C 0.011 / L0.5 0.142 / L2 0.164 / L+C 0.159;  "
                   "inv_chain C 0.007 / L0.5 0.004 / L2 0.007 / L+C 0.009;  "
                   "ex2 C 0.028 / L0.5 0.008 / L2 0.022 / L+C 0.032.  "
                   "Correction worth stating: the plan says added L and C are "
                   "safe individually and the resonant combination is the "
                   "problem. The measurement does not support that. On io_buf L "
                   "alone is the worst case (0.164, peak 7.9) and L+C is no "
                   "worse (0.159, peak 5.2); on the other two devices everything "
                   "stays under 0.03. The real rule is that series inductance "
                   "disturbs the solve, by an amount that depends on the buffer.")

    # ---------------------------------------------------------- new buffers
    s = d.add_slide("Nine new buffer variants, same stress axis",
                    section="More SPICE buffer mockups")
    points(d, s, [
        "Built in HSPICE from the real transistor library, then characterised and "
        "stressed exactly like the three base buffers.",
    ], y=1.28)
    d.add_code_box(s, """inv_chain          stages    Wn        Wp       what it changes

  base8            8 (x2)    1.0 um    2.0 um   reference
  stage4           4         1.0 um    2.0 um   predriver depth halved
  skewp            8 (x2)    1.0 um    1.0 um   Wp = Wn, rise slower than fall
  weak             8 (x2)    0.5 um    1.0 um   half drive at every stage

ex2                device change                what it changes

  base             none                         reference
  weak             mx15-19 + mx24-28  x0.5      output stage at half width
  skewp            mx24-28            x0.5      output PMOS halved, rise slows
  slowpre          mx11-14 + mx20-23  x0.5      predriver, delays the onset
  nomiller         n4->out caps removed         tests Miller feedthrough
  opendrain        mx24-28 removed              NMOS only, no path to VCC""",
                   0.7, 2.15, 12.0, 4.35, size=14.5)
    d.add_notes(s, "Plus an open-drain build of ex2. The nomiller variant came "
                   "back identical to the control -- those caps are 20.5 fF "
                   "against C_comp's 5 pF, 0.41%, so they cannot matter. The null "
                   "result still rules out the small capacitor and points at "
                   "C_comp.")

    s = d.add_slide("A variant under the same stress",
                    section="More SPICE buffer mockups")
    points(d, s, [
        "Same characterisation, same stress axis, so the comparison is like for "
        "like across the family.",
    ], y=1.28)
    d.add_picture_contain(s, FIG["variant_pad"], **LEFT)
    d.add_picture_contain(s, FIG["variant_kukd"], **RIGHT)
    d.add_notes(s, "Ku and Kd here come from the transistor itself, by driving it "
                   "into two fixtures and running the same two-equation solve the "
                   "model uses. That is a ground-truth coefficient target, not "
                   "native IBIS's opinion.")

    # --------------------------------------------------------------- status
    s = d.add_slide("Where this leaves us", section="Summary")
    d.add_text(s, "Settled:", 0.7, 1.3, 12.0, 0.5, size=17)
    points(d, s, [
        "C_comp is handled correctly",
        "the SPICE engine is not a confounder",
        "our model reproduces its own golden waveforms",
        "cmd_clean removes the settled offset",
    ], y=1.9)
    d.add_text(s, "Open:", 0.7, 4.2, 12.0, 0.5, size=17)
    points(d, s, [
        "the timing shift has no candidate mechanism, and grows with truncation",
        "the 1.25 max|Ku| cap needs replacing with a within-buffer outlier test",
    ], y=4.8)
    d.add_notes(s, "Two rules worth not re-learning: any bench for this model must "
                   "start with a real edge, never a held level, because it "
                   "initialises pulldown-on and latches state only on an edge. And "
                   "ngspice must be converged before drawing any conclusion.")

    path = d.save(OUT)
    print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size/1024:.0f} KB, "
          f"{len(d.prs.slides._sldIdLst)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
