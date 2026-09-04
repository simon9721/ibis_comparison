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
        "offset_chain", "command_node", "command_pad", "offset_removed",
        "fixture_vt", "fixture_ku", "variant_pad", "variant_kukd")}

# One wide figure under two lines of text, and the pair layout beside it.
WIDE = dict(x=0.55, y=2.02, w=12.2, h=4.95)
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
    s = d.add_slide("The offset: charge stranded in the command capacitor",
                    section="Delaying the input command")
    points(d, s, [
        "GUPCMD is a capacitor across 1e15 ohm, charged once per input edge.",
        "A truncated pulse leaves charge in it with no resistive path out.",
    ])
    d.add_picture_contain(s, FIG["offset_chain"], **WIDE)
    d.add_notes(s, "The sign of the stranded charge flips with the timestep, so it "
                   "is an integration error. Any fix by tuning a coefficient is a "
                   "coin flip, which is why the retuned version helped on some "
                   "cases and not others.")

    # --------------------------------------------------- how delay_cmd works
    s = d.add_slide("How delay_cmd works", section="Delaying the input command")
    points(d, s, [
        "gate-state: GUPCMD is a capacitor across 1e15 Ω, given a fixed packet of "
        "charge on each input edge — an integrator with no DC path.",
        "delay_cmd: GUPCMD is driven straight from the present input level.",
    ])
    d.add_picture_contain(s, FIG["command_node"], **LEFT)
    d.add_picture_contain(s, FIG["command_pad"], **RIGHT)
    d.add_notes(s, "One line of the generated subcircuit separates them. "
                   "gate_state: CGUPCMD across RGUPCMD 1e15 with BGUPCMDON "
                   "injecting a packet per edge. delay_cmd: BGUPCMD GUPCMD 0 "
                   "V = V(PUCMDLVL). On the tail after the reversal gate_state "
                   "sits at -0.144 and creeps back over ~3 ns; delay_cmd is at "
                   "exactly 0. On this particular bench the stranded charge is "
                   "negative and the command clamp removes it before it reaches "
                   "Ku, so the two pads agree to 5 mV -- the pad consequence on "
                   "the right is the case where the charge is positive.")

    # ------------------------------------------------------------- delay_cmd
    s = d.add_slide("delay_cmd removes the offset", section="Delaying the input command")
    points(d, s, [
        "The command returns to exactly zero, so nothing is stranded.",
        "The pedestal goes from 97.9 mV to 5.2 mV, against the transistor's 2.1.",
    ])
    d.add_picture_contain(s, FIG["offset_removed"], **WIDE)
    d.add_notes(s, "On this case the pedestal goes from 97.9 mV to 5.2 mV against "
                   "the transistor's 2.1 mV. Across all 29 matched stress cases "
                   "RMSE goes from 108.6 to 92.2 mV, the only build that beats "
                   "native IBIS. Caveat to state: delay_cmd has a 1.25 ns dead zone "
                   "after a reversal where neither device is commanded on.")

    # -------------------------------------------------- but not the timing
    s = d.add_slide("It does not fix the timing", section="Delaying the input command")
    points(d, s, [
        "delay_cmd improved the timing on 0 of 19 stress cases — so the offset and "
        "the shift are two mechanisms, not one.",
        "Our 50% crossing still arrives after native's: io_buf +27..+34 ps against "
        "native's +11..+18.",
    ])
    d.add_picture_contain(s, FIG["timing_shift"], **WIDE)
    d.add_notes(s, "The plan quotes 69-99 ps late where native is 5-26 ps early. "
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
        "Slower predriver, halved output devices, skewed PMOS, open-drain.",
        "Characterised and stressed exactly like the three base buffers.",
    ])
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
        "delay_cmd removes the settled offset",
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
