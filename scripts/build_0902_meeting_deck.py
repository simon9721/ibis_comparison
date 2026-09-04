#!/usr/bin/env python3
"""Build the meeting deck for the deliverables in 0902_plan.md.

Every figure is a real result file from `results/`; nothing is redrawn or
schematised for the slide. Numbers are quoted from the plan and from the study
directories it points at, including the results that overturned earlier claims --
those are on the slides rather than left out, because a reviewer who spots the
reversal later trusts the rest less.

    py -3.14 scripts/build_0902_meeting_deck.py
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

FIG = {
    "full_swing": R / "defect_b_full_swing_2026-09-03" / "defect_b_full_swing.png",
    "offset_chain": R / "settled_offset_diagnosis_2026-08-27" / "03_offset_chain.png",
    "offset_fix": R / "settled_offset_diagnosis_2026-08-27" / "04_offset_fix.png",
    "dead_zone": R / "settled_offset_diagnosis_2026-08-27" / "05_delay_cmd_dead_zone.png",
    "shift_depth": R / "timing_shift_decomposition_2026-09-03" / "timing_shift_vs_depth.png",
    "golden": R / "golden_waveform_test_2026-09-03" / "golden_waveform_test.png",
    "ccomp": R / "pybis_ccomp_converged_2026-09-03" / "ccomp_validation.png",
    "variant_kukd": (R / "variant_stress_cases_2026-09-04" / "inv_base8"
                     / "depth50_w102ps" / "kukd.png"),
}

# Portrait figures need the text beside them; wide ones sit under it.
TALL = dict(x=7.9, y=1.15, w=5.0, h=5.15)
WIDE = dict(x=0.7, y=3.05, w=12.0, h=3.25)
HALF = dict(x=6.9, y=1.5, w=6.0, h=4.3)


def mono(deck, slide, text, x, y, w, h, size=12.0):
    return deck.add_code_box(slide, text, x, y, w, h, size=size)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    missing = [k for k, v in FIG.items() if not v.exists()]
    if missing:
        print("missing figures: " + ", ".join(missing))
        return 1

    d = GreenDeck()
    d.set_title_slide(
        "Getting pybis closer to the transistor",
        "IBIS buffer modelling — status\n4 September 2026")

    # ---------------------------------------------------------------- 1. goal
    s = d.add_slide("What we are actually trying to do", section="Where we are")
    d.add_bullets(s, [
        "The transistor netlist in HSPICE is ground truth. Native IBIS is the bar "
        "to beat, not the target.",
        "Everything below is measured against the transistor, never against "
        "native IBIS.",
        "Two things are in play at once in any comparison — the IBIS "
        "implementation and the SPICE engine. We separated them (slide 10).",
    ], 0.7, 1.3, 6.0, 2.6)
    mono(d, s, """falling 50% crossing vs transistor, io_buf full swing

  native IBIS            +34.6 ps
  pybis InputDriven      +38.4 ps
  pybis gate-state       +43.5 ps""", 7.2, 1.4, 5.5, 2.2)
    d.add_text(s, "On a clean edge about 80% of the distance to the transistor is "
                  "the IBIS format itself — native pays it too. Our command layer "
                  "costs roughly 5 ps on top.", 7.2, 3.8, 5.5, 1.2, size=14)
    d.add_takeaway(s, "We are already near the format's floor on clean edges. "
                      "The distance worth attacking is under stress.")
    d.add_notes(s, "Lead with this. It reframes the goal: full-swing accuracy is "
                   "close to as good as the format allows, so effort belongs on "
                   "truncated pulses.")

    # ------------------------------------------------------- 2. full swing fig
    s = d.add_slide("On a clean edge, all three agree closely",
                    section="Where we are")
    d.add_text(s, "io_buf, full swing into 50 Ω and 2 pF. Native IBIS and stock "
                  "pybis sit almost on top of each other; both are slightly late "
                  "on the falling edge against the transistor.",
               0.7, 1.15, 12.0, 0.8, size=15)
    d.add_picture_contain(s, FIG["full_swing"], **WIDE)
    d.add_source(s, "results/defect_b_full_swing_2026-09-03/")
    d.add_notes(s, "The gap that remains on the falling edge is the ~35 ps the "
                   "format costs. It is not something our command layer created.")

    # -------------------------------------------------------- 3. two defects
    s = d.add_slide("Under stress there are two separate problems",
                    section="The two defects")
    d.add_text(s, "Stress here means a truncated pulse — the input reverses "
                  "before the pad finishes its transition. Targets are 90/80/70/"
                  "60/50% of the transistor's settled swing.",
               0.7, 1.2, 12.0, 0.7, size=15)
    mono(d, s, """The offset          a settled-state Ku error, on 90/60/50 only.
                    Not a true DC offset -- a ~6 ns tail that
                    looks permanent on a 10 ns plot.

The timing shift    falling 50% crossing 69-99 ps late vs the
                    transistor, on every case, where native
                    IBIS is 5-26 ps *early*.""", 0.7, 2.1, 12.0, 2.6, size=13)
    d.add_text(s, "They were assumed to be one mechanism, because truncation "
                  "triggers both. We tested that, and they are not — see slide 7.",
               0.7, 4.9, 12.0, 0.8, size=15)
    d.add_takeaway(s, "One is an amplitude error that decays; the other is a "
                      "timing error that does not.")

    # ---------------------------------------------------------- 4. the offset
    s = d.add_slide("The offset: a command capacitor with no DC path",
                    section="The two defects")
    d.add_bullets(s, [
        "GUPCMD is a capacitor across 1e15 Ω, charged by a fixed packet on each "
        "input edge.",
        "A truncated pulse strands charge in it, and there is no resistive path "
        "to remove that charge.",
        "The stranded charge maps through the gate state into Ku, and Ku into the "
        "pad — that is the chain on the right.",
        "The sign of the stranded charge flips with the timestep, which is why "
        "tuning it looked like it worked and then did not.",
    ], 0.7, 1.3, 7.0, 3.4)
    d.add_picture_contain(s, FIG["offset_chain"], **TALL)
    d.add_source(s, "results/settled_offset_diagnosis_2026-08-27/")
    d.add_notes(s, "The last bullet matters: it is an integration error, so any "
                   "fix by tuning a coefficient is a coin flip.")

    # ------------------------------------------------------ 5. delay_cmd fixes
    s = d.add_slide("delay_cmd removes the offset", section="The two defects")
    d.add_bullets(s, [
        "delay_cmd is level-driven: the command is a function of the current "
        "input level, not of accumulated edge history.",
        "So it returns to exactly zero and strands nothing.",
    ], 0.7, 1.3, 7.0, 1.4)
    mono(d, s, """settled pad offset at reversal

  gate-state (as shipped)   63.9 mV
  delay_cmd                  3.7 mV
  transistor                 7.5 mV
  native IBIS                6.4 mV

across all 29 matched stress cases
  RMSE  108.6 mV -> 92.2 mV
  the only build that beats native IBIS""", 0.7, 2.8, 7.0, 3.0, size=12.5)
    d.add_picture_contain(s, FIG["offset_fix"], **TALL)
    d.add_takeaway(s, "Level-driven commands fix the offset. This part is settled.")

    # ------------------------------------------------- 6. but not the timing
    s = d.add_slide("But it does not fix the timing — they are two mechanisms",
                    section="The two defects")
    d.add_text(s, "The open question in the plan was whether the offset and the "
                  "timing shift were one mechanism showing up twice. If they "
                  "were, delay_cmd would already fix both. Its amplitude had been "
                  "measured; its timing never had.",
               0.7, 1.2, 12.0, 1.1, size=15)
    mono(d, s, """We measured it.  delay_cmd improved the timing on 0 of 19 stress cases.

  -> the shift persists when the stranded charge is gone
  -> they are genuinely two defects, not one
  -> the offset has a fix; the timing shift has no candidate mechanism yet""",
         0.7, 2.5, 12.0, 1.9, size=13)
    d.add_text(s, "Worth stating plainly: delay_cmd also has a known 1.25 ns dead "
                  "zone after a reversal where neither device is commanded on, "
                  "which is why predriver_cmd was previously preferred.",
               0.7, 4.6, 12.0, 1.0, size=14)
    d.add_takeaway(s, "A cheap experiment closed a question that had been open "
                      "for weeks — with the less convenient answer.")

    # ----------------------------------------------------- 7. shift vs depth
    s = d.add_slide("The timing shift grows as the pulse is truncated",
                    section="The two defects")
    d.add_text(s, "Measured against the transistor across the depth family. The "
                  "shift is not a fixed penalty — it grows as the pulse gets "
                  "shorter, on every buffer we have tried.",
               0.7, 1.15, 12.0, 0.8, size=15)
    d.add_picture_contain(s, FIG["shift_depth"], **WIDE)
    d.add_source(s, "results/timing_shift_decomposition_2026-09-03/")
    d.add_notes(s, "Nine buffer variants later confirmed this: the shift grows on "
                   "9 of 9, and full swing and stress carry opposite signs, so "
                   "neither number is a proxy for the other.")

    # -------------------------------------------------------- 8. golden test
    s = d.add_slide("The core reconstruction is sound", section="Confidence")
    d.add_bullets(s, [
        "A golden-waveform test replays a model's own V-T tables into the fixture "
        "that produced them.",
        "It is self-contained — no transistor, no native IBIS, no engine "
        "confound. We had never done this before.",
        "pybis reproduces all three buffers' own golden waveforms: "
        "figure of merit 0.03–0.41%, shift +4 to +8 ps.",
        "It is now the standing health check, and it settled the C_comp question.",
    ], 0.7, 1.3, 6.0, 3.4)
    d.add_picture_contain(s, FIG["golden"], **TALL)
    d.add_takeaway(s, "Whatever is wrong under stress, it is not the I-V × Ku(t) "
                      "reconstruction itself.")

    # ------------------------------------------------------------- 9. C_comp
    s = d.add_slide("C_comp is handled correctly", section="Confidence")
    d.add_text(s, "Nominal C_comp beats zero on all 12 tables, and the margin "
                  "scales with the die capacitance — ex2 at 5 pF needs a −124 to "
                  "−178 ps correction without it. I had this backwards at first: "
                  "I misapplied the book's double-counting diagnostic and reported "
                  "that pybis over-applies C_comp. The golden-waveform test "
                  "overturned that.",
               0.7, 1.15, 12.0, 1.4, size=15)
    d.add_picture_contain(s, FIG["ccomp"], **WIDE)
    d.add_source(s, "results/pybis_ccomp_converged_2026-09-03/")

    # ------------------------------------------------------- 10. engine split
    s = d.add_slide("Is it the engine or the model?", section="Method")
    d.add_text(s, "Every native-IBIS-vs-pybis number changes two things at once: "
                  "the IBIS implementation and the SPICE engine. We wrote a "
                  "translator so the same pybis model runs in both.",
               0.7, 1.2, 12.0, 0.9, size=15)
    mono(d, s, """                              50% crossing

  pybis model in ngspice          5.3371 ns
  pybis model in HSPICE           5.3375 ns      engine:  -0.5 ps rising, -0.0 falling
  native IBIS in HSPICE           5.3319 ns      model:   +5.6 ps""",
         0.7, 2.3, 12.0, 1.8, size=12.5)
    d.add_bullets(s, [
        "The engine is not the source of the difference — provided ngspice is run "
        "converged.",
        "That proviso is real: at a 1 ps step ngspice was an aliasing outlier that "
        "doubled the apparent lag and inflated a whole validation sweep.",
    ], 0.7, 4.3, 12.0, 1.4)
    d.add_source(s, "results/pybis_engine_model_decoupling_2026-09-03/")

    # ---------------------------------------------------------- 11. fixtures
    s = d.add_slide("What fixtures do to the extracted Ku/Kd", section="Method")
    d.add_bullets(s, [
        "The control reproduces the shipped solve to 2.4e−08, so the method is "
        "exact.",
        "In quiet regions Ku is load-independent to four decimals — the "
        "extraction is a device property, not a fixture artifact.",
        "A resonant R+L+C fixture corrupts Ku for 1.14 ns, reaching 0.26 of error.",
    ], 0.7, 1.4, 12.0, 2.4)
    d.add_text(s, "Practical conclusion: added L and C are safe individually. The "
                  "resonant combination has to be avoided when characterising.",
               0.7, 4.0, 12.0, 0.9, size=15)
    d.add_takeaway(s, "The two-fixture extraction is trustworthy — as long as the "
                      "fixture is not resonant.")

    # -------------------------------------------------------- 12. the Ku cap
    s = d.add_slide("The 1.25 max|Ku| cap rejects good models",
                    section="What should change")
    mono(d, s, """ex2 variants, all seven edge rates

  variant                          output edge   max|Ku|
  slowpre  (predriver halved)         328 ps      1.047
  base     (control)                  200 ps      1.283
  nomiller (Miller caps removed)      208 ps      1.299
  skewp    (output PMOS halved)       160 ps      1.589
  weak     (both output devices /2)   152 ps      1.779""",
         0.7, 1.3, 7.6, 2.7, size=12)
    d.add_bullets(s, [
        "Monotonic in C_comp × dV/dt against the device drive.",
        "For ex2: 5 pF × 3.3 V / 200 ps = 82 mA of displacement current against a "
        "~51 mA drive. It exceeds the device, so the solve must push Ku above 1.",
        "Healthy baselines differ per silicon — inv_chain 1.03, io_buf 1.18, "
        "ex2 1.28 — so no absolute number works.",
    ], 8.5, 1.3, 4.3, 3.0)
    d.add_text(s, "I proposed the wrong cause first: gate-to-drain (Miller) "
                  "feedthrough. The nomiller variant came back identical to the "
                  "control. Those caps are 20.5 fF against C_comp's 5 pF — 0.41%, "
                  "250× too small — which is arithmetic I should have done before "
                  "building the variant. The null result still helps: it rules out "
                  "the small capacitor and points at C_comp.",
               0.7, 4.2, 12.0, 1.5, size=14)
    d.add_takeaway(s, "A high max|Ku| is a real signature of a large die "
                      "capacitance driven fast. The cap should be a within-buffer "
                      "outlier test.")

    # ------------------------------------------------------ 13. new buffers
    s = d.add_slide("New buffers, and what they are for",
                    section="What should change")
    d.add_bullets(s, [
        "We built nine variants of inv_chain and ex2 in HSPICE using the real "
        "transistor library — slower predriver, halved output devices, skewed "
        "PMOS, Miller caps removed, plus an open-drain build.",
        "The point is to test whether what we learned on three buffers holds "
        "across different silicon, rather than being a property of one netlist.",
        "Each one goes through the same s2ibispy characterisation and the same "
        "stress axis, so the comparison is like for like.",
    ], 0.7, 1.3, 6.0, 3.2)
    d.add_picture_contain(s, FIG["variant_kukd"], **HALF)
    d.add_text(s, "Ku and Kd for one stressed case. The coefficients show things "
                  "the pad trace hides — here the gate-state build starts moving "
                  "before the transistor does.",
               0.7, 4.8, 6.0, 1.1, size=14)

    # ------------------------------------------------------------- 14. status
    s = d.add_slide("Where this leaves us", section="Summary")
    d.add_bullets(s, [
        "Settled — C_comp is handled correctly; the engine is not a confounder; "
        "pybis reproduces its own golden waveforms; the offset has a working fix "
        "in delay_cmd.",
        "Open — the timing shift has no candidate mechanism, and it grows with "
        "truncation on every buffer tried.",
        "Open — the 1.25 max|Ku| cap needs replacing with a within-buffer outlier "
        "test before it rejects more good models.",
        "Running now — the same stress axis applied to all nine variants, with "
        "Ku/Kd solved from the transistor for each case.",
    ], 0.7, 1.3, 12.0, 3.6)
    d.add_text(s, "Two rules that cost us real time, worth not re-learning: any "
                  "bench for this model must start with a real edge and never a "
                  "held level, because it initialises pulldown-on and latches "
                  "state only on an edge. And ngspice must be converged before any "
                  "conclusion is drawn from it.",
               0.7, 5.0, 12.0, 1.3, size=14)

    path = d.save(OUT)
    print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size/1024:.0f} KB, "
          f"{len(d.prs.slides.__iter__.__self__._sldIdLst)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
