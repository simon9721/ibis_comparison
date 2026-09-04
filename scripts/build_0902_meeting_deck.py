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
       ("clean_edge", "stress_pad", "stress_kukd", "timing_shift",
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
        "Getting our IBIS model closer to the transistor",
        "IBIS buffer modelling — status\n4 September 2026")

    # ------------------------------------------------------------------- goal
    s = d.add_slide("What we are comparing", section="Where we are")
    points(d, s, [
        "HSPICE transistor — ground truth",
        "HSPICE native IBIS — the bar to beat, not the target",
        "Our IBIS model in ngspice — measured against the transistor",
    ])
    d.add_text(s, "Falling 50% crossing on io_buf at full swing, later than the "
                  "transistor:", 0.7, 2.9, 12.0, 0.5, size=17)
    points(d, s, [
        "native IBIS          +34.6 ps",
        "our model, stock     +38.4 ps",
        "our model, gate-state  +43.5 ps",
    ], y=3.5)
    d.add_text(s, "So the IBIS format itself costs about 35 ps, which native pays "
                  "too. Our command layer costs about 5 ps on top.",
               0.7, 5.5, 12.0, 0.8, size=17)
    d.add_notes(s, "Lead with this. Full-swing accuracy is close to as good as the "
                   "format allows, so the effort belongs on truncated pulses.")

    # ------------------------------------------------------------ clean edge
    s = d.add_slide("At full swing all three agree", section="Where we are")
    points(d, s, [
        "The three curves sit on top of each other through the transition.",
        "What is left on the falling edge is the format's ~35 ps, not our layer.",
    ])
    d.add_picture_contain(s, FIG["clean_edge"], **WIDE)

    # ---------------------------------------------------------------- stress
    s = d.add_slide("Defect 1: the pad does not settle",
                    section="The two defects")
    points(d, s, [
        "The input reverses before the pad finishes its transition.",
        "Left: our pad comes back up where the transistor does not. "
        "Right: Ku stays part-on instead of returning to zero.",
    ])
    d.add_picture_contain(s, FIG["stress_pad"], **LEFT)
    d.add_picture_contain(s, FIG["stress_kukd"], **RIGHT)
    d.add_notes(s, "Two separate defects. The offset is a settled-state Ku error, "
                   "on the 90/60/50 targets only -- a ~6 ns tail that looks "
                   "permanent on a 10 ns plot. The timing shift is the falling 50% "
                   "crossing 69-99 ps late on every case, where native IBIS is "
                   "5-26 ps early.")

    # ------------------------------------------------------- the timing shift
    s = d.add_slide("Defect 2: our crossing is late", section="The two defects")
    points(d, s, [
        "A separate defect: the 50% crossing arrives later than native IBIS.",
        "Over the five stress cases per device — io_buf native +11..+18 ps, ours "
        "+27..+34;  inv_chain native −6..−5, ours +8..+12;  ex2 both early.",
    ])
    d.add_picture_contain(s, FIG["timing_shift"], **WIDE)
    d.add_notes(s, "The plan quotes 69-99 ps late where native is 5-26 ps early. "
                   "That is not reproducible from the data on disk with this "
                   "metric -- what the stress matrix shows is about 15 ps later "
                   "than native on io_buf and inv_chain, and on ex2 both are early "
                   "with ours the closer. The defect is real and device-dependent, "
                   "but smaller and less one-sided than the plan states.")

    # ------------------------------------------------------------ the offset
    s = d.add_slide("The offset: charge stranded in the command capacitor",
                    section="The two defects")
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
    s = d.add_slide("How delay_cmd works", section="The two defects")
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
    s = d.add_slide("delay_cmd removes the offset", section="The two defects")
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
    s = d.add_slide("It does not fix the timing", section="The two defects")
    points(d, s, [
        "If the offset and the timing shift were one mechanism, delay_cmd would "
        "fix both. Its amplitude had been measured; its timing never had.",
    ])
    d.add_text(s, "We measured it:", 0.7, 2.4, 12.0, 0.5, size=17)
    points(d, s, [
        "delay_cmd improved the timing on 0 of 19 stress cases",
        "the shift persists once the stranded charge is gone",
        "they are two defects, not one",
    ], y=3.0)
    d.add_text(s, "The offset has a fix. The timing shift has no candidate "
                  "mechanism yet, and it grows as the pulse is truncated — on all "
                  "nine buffer variants tested so far.",
               0.7, 5.1, 12.0, 1.0, size=17)

    # ----------------------------------------------------------- confidence
    s = d.add_slide("The core reconstruction is sound", section="Confidence")
    points(d, s, [
        "A golden-waveform test replays a model's own V-T tables into the fixture "
        "that produced them — no transistor, no native IBIS, no engine confound.",
        "We had never done this before. It is now the standing health check.",
    ])
    d.add_text(s, "Our model against its own golden waveforms, three buffers, both "
                  "edges, both fixtures:", 0.7, 3.1, 12.0, 0.5, size=17)
    points(d, s, [
        "figure of merit   0.03 – 0.41 %",
        "timing shift      +4 to +8 ps",
    ], y=3.7)
    d.add_text(s, "So whatever is wrong under stress, it is not the I-V × Ku(t) "
                  "reconstruction.", 0.7, 5.0, 12.0, 0.8, size=17)

    # --------------------------------------------------------------- C_comp
    s = d.add_slide("C_comp is handled correctly", section="Confidence")
    points(d, s, [
        "Nominal C_comp beats zero on all 12 tables, and the margin scales with "
        "the die capacitance.",
    ])
    d.add_text(s, "50% crossing shift against the transistor, with C_comp at "
                  "nominal and set to zero:", 0.7, 2.2, 12.0, 0.5, size=17)
    points(d, s, [
        "50 Ω, 0 pF     +6.7 ps        −277.8 ps",
        "500 Ω, 2 pF    −0.2 ps          −0.9 ps",
        "1 kΩ, 5 pF     −1.3 ps          −1.1 ps",
    ], y=2.8)
    d.add_text(s, "I had this backwards at first. I misapplied the book's "
                  "double-counting diagnostic and reported that our model "
                  "over-applies C_comp; the golden-waveform test overturned it.",
               0.7, 4.9, 12.0, 1.1, size=17)

    # --------------------------------------------------------------- engine
    s = d.add_slide("Is the difference the engine or the model?",
                    section="Method")
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
    s = d.add_slide("What fixtures do to the extracted Ku/Kd", section="Method")
    points(d, s, [
        "Ku re-solved on five different characterisation fixtures, against the "
        "R-only baseline. Through the transition all five sit on top of each other.",
        "The resonant L+C fixture rings for nanoseconds after the reversal; L and "
        "C on their own do not.",
    ])
    d.add_picture_contain(s, FIG["fixture_vt"], **LEFT)
    d.add_picture_contain(s, FIG["fixture_ku"], **RIGHT)
    d.add_notes(s, "The control reproduces the shipped solve to 2.4e-08, so the "
                   "method is exact. In quiet regions Ku is load-independent to "
                   "four decimals, which is the point: the extraction is a device "
                   "property, not a fixture artifact. On io_buf the mean Ku error "
                   "is 0.011 for C alone, 0.14-0.16 for L, and the worst-case "
                   "excursion reaches 7.9 on L 2 nH. Practical rule: avoid a "
                   "resonant fixture when characterising.")

    # --------------------------------------------------------------- Ku cap
    s = d.add_slide("The 1.25 max|Ku| cap rejects good models",
                    section="What should change")
    d.add_text(s, "ex2 variants, across all seven characterisation edge rates:",
               0.7, 1.3, 12.0, 0.5, size=17)
    points(d, s, [
        "slowpre   predriver halved      328 ps      1.047",
        "base      control               200 ps      1.283",
        "nomiller  Miller caps removed   208 ps      1.299",
        "skewp     output PMOS halved    160 ps      1.589",
        "weak      both devices halved   152 ps      1.779",
    ], y=1.9)
    d.add_text(s, "It follows C_comp × dV/dt against the device drive. For ex2 that "
                  "is 82 mA of displacement current against a ~51 mA drive — it "
                  "exceeds the device, so the solve has to push Ku above 1.\n"
                  "Healthy baselines differ per silicon: inv_chain 1.03, io_buf "
                  "1.18, ex2 1.28. No absolute number works; it should be a "
                  "within-buffer outlier test.",
               0.7, 4.9, 12.0, 1.6, size=17)
    d.add_notes(s, "I proposed the wrong cause first -- Miller feedthrough -- and "
                   "built the nomiller variant to test it. It came back identical "
                   "to the control. Those caps are 20.5 fF against C_comp's 5 pF, "
                   "0.41%, 250x too small, which is arithmetic I should have done "
                   "before building the variant.")

    # ---------------------------------------------------------- new buffers
    s = d.add_slide("Nine new buffer variants, same stress axis",
                    section="What should change")
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
