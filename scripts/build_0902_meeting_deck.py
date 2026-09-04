#!/usr/bin/env python3
"""Build the meeting deck for the deliverables in 0902_plan.md.

Every figure is a real result — measured data, redrawn only for size. Numbers are
quoted from the plan and from the study directories it points at, including the
results that overturned earlier claims; those stay on the slides, because a
reviewer who spots a reversal afterwards trusts the rest less.

Figures come from `scripts/build_deck_figures.py`, not from the print versions in
the results directories. The print figures are 11–13 inches wide and up to 13 tall
with ~10 pt labels; measured in the first draft of this deck, shrinking them into
a slide box put their axis text at **3.9–5.6 pt**. The redraws are 12.2 x 5.2 in
with 15–19 pt fonts, so at a 12.2 in box the scale is 1.0 and text is the size it
claims to be.

    py -3.14 scripts/build_deck_figures.py     # first, if results changed
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
F = R / "meeting_deck_2026-09-04" / "figures"

FIG = {
    "error_budget": F / "error_budget.png",
    "clean_edge": F / "clean_edge.png",
    "offset_chain": F / "offset_chain.png",
    "offset_removed": F / "offset_removed.png",
    "shift_depth": F / "shift_vs_depth.png",
    "ccomp": F / "ccomp.png",
    "ku_cap": F / "ku_cap.png",
    "variant_kukd": F / "variant_kukd.png",
}

# One figure box, sized so the redraw lands at scale 1.0 and still clears the
# takeaway band at 6.63.
FULL = dict(x=0.55, y=1.28, w=12.2, h=5.2)


def mono(deck, slide, text, x, y, w, size=17.0):
    """Monospaced block, sized to its own content.

    Height is derived from the line count rather than guessed: a fixed height left
    a third of the slide empty under every table in the first draft. 17 pt is
    comfortably legible projected, and the box grows to match.
    """
    # Guard against a stale call from when this took an explicit height: a
    # leftover `mono(..., w, 2.8)` silently set the font to 2.8 pt and rendered a
    # table nobody could read, which is exactly the failure this deck is trying to
    # avoid.
    if size < 8:
        raise ValueError(f"mono(): size={size} pt is a height, not a font size")
    lines = len(text.splitlines()) or 1
    h = lines * (size / 72.0) * 1.22 + 0.30
    return deck.add_code_box(slide, text, x, y, w, h, size=size)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    missing = [k for k, v in FIG.items() if not v.exists()]
    if missing:
        print("missing figures: " + ", ".join(missing)
              + "\n  run: py -3.14 scripts/build_deck_figures.py")
        return 1

    d = GreenDeck()
    d.set_title_slide(
        "Getting pybis closer to the transistor",
        "IBIS buffer modelling — status\n4 September 2026")

    # ---------------------------------------------------------------- 1. goal
    s = d.add_slide("What we are trying to do", section="Where we are")
    d.add_bullets(s, [
        "The transistor netlist in HSPICE is ground truth.",
        "Native IBIS is the bar to beat, not the target.",
        "Everything here is measured against the transistor.",
    ], 0.7, 1.4, 5.9, 2.2)
    d.add_text(s, "Two things move in any comparison — the IBIS implementation and "
                  "the SPICE engine. We separated them, and the engine is not the "
                  "source.", 0.7, 3.9, 12.0, 1.2, size=17)
    d.add_takeaway(s, "We are near the format's floor on clean edges. The distance "
                      "worth attacking is under stress.")
    d.add_notes(s, "Lead with this. Full-swing accuracy is close to as good as the "
                   "format allows, so effort belongs on truncated pulses.")

    # -------------------------------------------------- 2. the error budget
    s = d.add_slide("Where the error actually comes from", section="Where we are")
    d.add_picture_contain(s, FIG["error_budget"], x=0.55, y=1.35, w=12.2, h=4.9)
    d.add_takeaway(s, "The format costs ~35 ps. Our command layer costs ~5 ps on "
                      "top. We are near the floor on clean edges.")

    # ------------------------------------------------------- 3. clean edge fig
    s = d.add_slide("On a clean edge, all three agree", section="Where we are")
    d.add_picture_contain(s, FIG["clean_edge"], **FULL)
    d.add_takeaway(s, "The gap left on the falling edge is what the format costs. "
                      "We did not create it.")

    # -------------------------------------------------------- 3. two defects
    s = d.add_slide("Under stress there are two problems",
                    section="The two defects")
    d.add_text(s, "Stress means a truncated pulse: the input reverses before the "
                  "pad finishes its transition. Targets are 90/80/70/60/50% of the "
                  "transistor's settled swing.", 0.7, 1.3, 12.0, 1.0, size=17)
    mono(d, s, "The offset         a settled-state Ku error, on 90/60/50 only.\n"
               "                   A ~6 ns tail that looks permanent on a\n"
               "                   10 ns plot -- not a true DC offset.\n\n"
               "The timing shift   falling 50% crossing 69-99 ps late, on\n"
               "                   every case, where native IBIS is\n"
               "                   5-26 ps early.", 0.7, 2.6, 12.0)
    d.add_takeaway(s, "One is an amplitude error that decays. The other is a timing "
                      "error that does not.")

    # ---------------------------------------------------------- 4. the offset
    s = d.add_slide("Where the offset comes from", section="The two defects")
    d.add_picture_contain(s, FIG["offset_chain"], **FULL)
    d.add_takeaway(s, "GUPCMD is a capacitor across 1e15 ohm. A truncated pulse "
                      "strands charge with no path to remove it.")
    d.add_notes(s, "The sign of the stranded charge flips with the timestep, so it "
                   "is an integration error. Any fix by tuning a coefficient is a "
                   "coin flip, which is why the retuned version helped on some "
                   "cases and not others.")

    # ------------------------------------------------------ 5. delay_cmd fixes
    s = d.add_slide("delay_cmd removes it", section="The two defects")
    d.add_picture_contain(s, FIG["offset_removed"], **FULL)
    d.add_takeaway(s, "Level-driven commands fix the offset. This part is settled.")
    d.add_notes(s, "delay_cmd is level-driven: the command is a function of the "
                   "current input level, not of accumulated edge history, so it "
                   "returns to exactly zero and strands nothing. On this case the "
                   "pedestal goes from 97.9 mV to 5.2 mV against the transistor's "
                   "2.1 mV. Across all 29 matched stress cases RMSE goes from "
                   "108.6 to 92.2 mV, the only build that beats native IBIS.")

    # ------------------------------------------------- 6. but not the timing
    s = d.add_slide("It does not fix the timing", section="The two defects")
    d.add_text(s, "The open question was whether the offset and the timing shift "
                  "were one mechanism showing up twice. If they were, delay_cmd "
                  "would already fix both. Its amplitude had been measured; its "
                  "timing never had.", 0.7, 1.3, 12.0, 1.4, size=17)
    mono(d, s, "We measured it.\n\n"
               "  delay_cmd improved the timing on 0 of 19 stress cases.\n\n"
               "  -> the shift persists once the stranded charge is gone\n"
               "  -> they are two defects, not one\n"
               "  -> the offset has a fix; the shift has no mechanism yet",
         0.7, 3.0, 12.0)
    d.add_takeaway(s, "A cheap experiment closed a question that was open for "
                      "weeks, with the less convenient answer.")
    d.add_notes(s, "State the caveat honestly: delay_cmd has a known 1.25 ns dead "
                   "zone after a reversal where neither device is commanded on, "
                   "which is why predriver_cmd was previously preferred.")

    # ----------------------------------------------------- 7. shift vs depth
    s = d.add_slide("The shift grows as the pulse is truncated",
                    section="The two defects")
    d.add_picture_contain(s, FIG["shift_depth"], **FULL)
    d.add_takeaway(s, "Not a fixed penalty. It grows with truncation on every "
                      "buffer we have tried.")

    # -------------------------------------------------------- 8. golden test
    s = d.add_slide("The core reconstruction is sound", section="Confidence")
    d.add_bullets(s, [
        "A golden-waveform test replays a model's own V-T tables into the fixture "
        "that produced them.",
        "Self-contained: no transistor, no native IBIS, no engine confound. We had "
        "never done this.",
        "pybis reproduces all three buffers' own golden waveforms.",
    ], 0.7, 1.4, 6.6, 2.8)
    mono(d, s, "figure of merit   0.03 - 0.41 %\ntiming shift      +4 to +8 ps\n\n"
               "three buffers, both edges,\nboth fixtures", 7.5, 1.5, 5.2)
    d.add_text(s, "It is now the standing health check, and it settled the C_comp "
                  "question.", 0.7, 4.4, 12.0, 0.8, size=17)
    d.add_takeaway(s, "Whatever is wrong under stress, it is not the I-V times "
                      "Ku(t) reconstruction.")

    # ------------------------------------------------------------- 9. C_comp
    s = d.add_slide("C_comp is handled correctly", section="Confidence")
    d.add_picture_contain(s, FIG["ccomp"], **FULL)
    d.add_takeaway(s, "I had this backwards first. The golden-waveform test "
                      "overturned my own claim that pybis over-applies C_comp.")

    # ------------------------------------------------------- 10. engine split
    s = d.add_slide("Is it the engine or the model?", section="Method")
    d.add_text(s, "Every native-vs-pybis number changes two things at once: the "
                  "IBIS implementation and the SPICE engine. We wrote a translator "
                  "so the same model runs in both.", 0.7, 1.3, 12.0, 1.0, size=17)
    mono(d, s, "                          50% crossing\n\n"
               "  pybis in ngspice            5.3371 ns\n"
               "  pybis in HSPICE             5.3375 ns     engine  -0.5 ps\n"
               "  native IBIS in HSPICE       5.3319 ns     model   +5.6 ps",
         0.7, 2.6, 12.0)
    d.add_text(s, "The engine is not the source, provided ngspice is converged. At "
                  "a 1 ps step it was an aliasing outlier that doubled the apparent "
                  "lag.", 0.7, 4.7, 12.0, 1.0, size=17)
    d.add_takeaway(s, "Converged, the two engines agree to half a picosecond.")

    # ---------------------------------------------------------- 11. fixtures
    s = d.add_slide("What fixtures do to the extracted Ku/Kd", section="Method")
    d.add_bullets(s, [
        "The control reproduces the shipped solve to 2.4e-08, so the method is "
        "exact.",
        "In quiet regions Ku is load-independent to four decimals. It is a device "
        "property, not a fixture artifact.",
        "A resonant R+L+C fixture corrupts Ku for 1.14 ns, reaching 0.26 of error.",
    ], 0.7, 1.5, 12.0, 3.0)
    d.add_text(s, "Added L and C are safe individually. The resonant combination "
                  "has to be avoided when characterising.",
               0.7, 4.6, 12.0, 1.0, size=17)
    d.add_takeaway(s, "The two-fixture extraction is trustworthy, as long as the "
                      "fixture is not resonant.")

    # -------------------------------------------------------- 12. the Ku cap
    s = d.add_slide("The 1.25 max|Ku| cap rejects good models",
                    section="What should change")
    d.add_picture_contain(s, FIG["ku_cap"], x=0.55, y=1.35, w=12.2, h=4.9)
    d.add_takeaway(s, "A high max|Ku| is a real signature of a large die "
                      "capacitance driven fast, not a corrupted extraction.")
    d.add_notes(s, "For ex2 the displacement current is 5 pF x 3.3 V / 200 ps = "
                   "82 mA against a ~51 mA drive. It exceeds the device, so the "
                   "two-fixture solve has to push Ku above 1. Healthy baselines "
                   "differ per silicon -- inv_chain 1.03, io_buf 1.18, ex2 1.28 -- "
                   "so no absolute number works. It should be a within-buffer "
                   "outlier test.")
    d.add_notes(s, "I proposed the wrong cause first, Miller feedthrough, and built "
                   "a nomiller variant to test it. It came back identical to the "
                   "control. Those caps are 20.5 fF against C_comp's 5 pF, 0.41%, "
                   "250x too small, which is arithmetic I should have done before "
                   "building the variant. The null result still rules out the small "
                   "capacitor and points at C_comp.")

    # ------------------------------------------------------ 13. new buffers
    s = d.add_slide("New buffers, and what they are for",
                    section="What should change")
    d.add_bullets(s, [
        "Nine variants of inv_chain and ex2 built in HSPICE with the real "
        "transistor library: slower predriver, halved output devices, skewed PMOS, "
        "Miller caps removed, plus an open-drain build.",
        "The point is to test whether what we learned on three buffers holds "
        "across different silicon.",
        "Same characterisation, same stress axis, so the comparison is like for "
        "like.",
    ], 0.7, 1.4, 12.0, 2.8)
    d.add_text(s, "Running now: the same 90-50% stress axis on all nine, with Ku "
                  "and Kd solved from the transistor for every case.",
               0.7, 4.5, 12.0, 1.0, size=17)
    d.add_takeaway(s, "Ku and Kd show what the pad trace hides.")

    # -------------------------------------------------- 14. variant figure
    s = d.add_slide("The coefficients under stress",
                    section="What should change")
    d.add_picture_contain(s, FIG["variant_kukd"], **FULL)
    d.add_takeaway(s, "The gate-state build starts moving before the transistor "
                      "does. Visible in Ku, invisible in the pad.")

    # ------------------------------------------------------------- 15. status
    s = d.add_slide("Where this leaves us", section="Summary")
    d.add_bullets(s, [
        "Settled: C_comp is right, the engine is not a confounder, pybis "
        "reproduces its own golden waveforms, and delay_cmd fixes the offset.",
        "Open: the timing shift has no candidate mechanism, and it grows with "
        "truncation on every buffer tried.",
        "Open: the 1.25 max|Ku| cap needs replacing before it rejects more good "
        "models.",
    ], 0.7, 1.4, 12.0, 3.0)
    d.add_text(s, "Two rules worth not re-learning: any bench for this model must "
                  "start with a real edge, never a held level. And ngspice must be "
                  "converged before drawing any conclusion from it.",
               0.7, 4.7, 12.0, 1.4, size=17)

    path = d.save(OUT)
    print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
