#!/usr/bin/env python3
"""What the fixtures do to the V-T waveforms, and to the Ku/Kd solved from them.

The deck's fixture slide shows a *stressed* case. This is the step before that:
the full-swing transition the two-fixture extraction actually characterises on --
the first thing the fixtures produce -- and the coefficients that come out of it.

Same five fixtures as `scripts/archive/test_kukd_fixture_variants.py`, same
topology, same solve. The only change is the stimulus: a pulse long enough for the
pad to settle at both ends, so the transition is complete rather than truncated.

    pad -- Vsense -- Lfixture --+-- Rfixture -- Vfixture
                                |
                            Cfixture
                                |
                               gnd

Two fixture voltages per variant, 0 and VCC, because that pair is what the solve
needs -- one equation each for

    Ku i_pu(V) + Kd i_pd(V) = i_gc(V) + i_pc(V) + i_fix - C_comp dV/dt

The fixture current is measured at the sense source rather than computed as
(v_fix - v_pad)/r_fix, which stops being true the moment an inductor is in series.

Ten HSPICE runs per device, cached: a completed run is reused, so re-running this
is free once the first pass is done.

    py -3.14 scripts/build_fixture_characterisation_figures.py
    py -3.14 scripts/build_fixture_characterisation_figures.py --device io_buf
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts", ROOT / "scripts" / "archive",
           ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
import test_kukd_fixture_variants as fx  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

OUT = ROOT / "results" / "fixture_characterisation_2026-09-04"
FIGS = ROOT / "results" / "meeting_deck_2026-09-04" / "figures"

# Long enough that the pad settles at both ends -- this is a characterisation
# waveform, not a stress case. The edge is the 50 ps the IBIS files were
# regenerated at, so the fixture is the only thing changing.
EDGE_NS, WIDTH_NS, STOP_NS = 0.050, 6.0, 16.0
RISE_NS = 5.0

# Same five as the stressed study, in the same order, so the two slides read the
# same way. Colours match that study's figure too.
VARIANTS = fx.VARIANTS
COLOURS = fx.COLOURS

plt.rcParams.update({"font.size": 14, "axes.titlesize": 15, "axes.labelsize": 14,
                     "xtick.labelsize": 12, "ytick.labelsize": 12,
                     "legend.fontsize": 11})
FIGSIZE = (12.2, 5.4)


def solve_all(device, case, hspice: Path, timeout_s: int):
    """(variant, runs, solution) per fixture. runs is the (0 V, VCC) pair."""
    ibis = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                        model_name=device.model, component_name=device.component)
    out = []
    for variant, l_fix, c_fix in VARIANTS:
        tag = f"l{l_fix * 1e9:g}n_c{c_fix * 1e12:g}p"
        try:
            runs = [fx.run_variant(device, case, v, l_fix, c_fix,
                                   OUT / "hspice" / device.device_id / tag / name,
                                   hspice, timeout_s)
                    for v, name in ((0.0, "vfix_0"), (device.supply_v, "vfix_vcc"))]
        except RuntimeError as error:
            print(f"  {variant:<20} skipped: {error}")
            continue
        out.append((variant, runs, fx.solve_from_measured(ibis, runs)))
        print(f"  {variant:<20} solved")
    return out


def vt_figure(device_id: str, solved, window, baseline_only: bool = False) -> None:
    """The V-T waveforms themselves: one panel per fixture voltage.

    The baseline gets its own figure. Overlaid with the others it is the black
    curve underneath four brighter ones, and the inductive fixtures ring hard
    enough at the reversal to set the y-axis -- which buries the very thing the
    baseline is there to show, the clean rise and fall.
    """
    series = solved[:1] if baseline_only else solved
    fig, ax = plt.subplots(1, 2, figsize=FIGSIZE, sharey=True)
    for a, idx, title in ((ax[0], 0, "V-T into the 0 V fixture"),
                          (ax[1], 1, "V-T into the VCC fixture")):
        for (variant, runs, _), colour in zip(series, COLOURS):
            t_s, pad, _ = runs[idx]
            a.plot(t_s * 1e9, pad, color=colour, lw=2.2, label=variant)
        a.set_xlim(*window)
        a.set_title(title, loc="left", fontweight="bold")
        a.set_xlabel("Time (ns)")
        a.grid(alpha=0.3)
    ax[0].set_ylabel("Pad (V)")
    ax[0].legend(loc="best")
    what = "the R-only baseline" if baseline_only else "five fixtures"
    tag = "vt_baseline" if baseline_only else "vt"
    fig.suptitle(f"{device_id} | full swing | V-T on {what}",
                 fontsize=16, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"fixture_char_{tag}_{device_id}.png", dpi=200)
    plt.close(fig)
    print(f"  fixture_char_{tag}_{device_id}.png")


def kukd_figure(device_id: str, solved, window, baseline_only: bool = False) -> None:
    """Ku and Kd solved from each fixture pair, overlaid."""
    series = solved[:1] if baseline_only else solved
    fig, ax = plt.subplots(1, 2, figsize=FIGSIZE, sharey=True)
    for a, col, name in ((ax[0], 1, "Ku"), (ax[1], 2, "Kd")):
        for (variant, _, sol), colour in zip(series, COLOURS):
            a.plot(sol[:, 0] * 1e9, sol[:, col], color=colour, lw=2.2,
                   label=variant)
        # The band a physical coefficient lives in; anything outside it is the
        # solve being forced, not the device.
        a.axhspan(-0.05, 1.05, color="#EAF1F7", zorder=0)
        a.set_xlim(*window)
        a.set_ylim(-0.35, 1.45)
        a.set_title(name, loc="left", fontweight="bold")
        a.set_xlabel("Time (ns)")
        a.grid(alpha=0.3)
    ax[0].set_ylabel("coefficient")
    ax[0].legend(loc="best")
    what = ("from the R-only baseline" if baseline_only
            else "re-solved on each fixture")
    tag = "kukd_baseline" if baseline_only else "kukd"
    fig.suptitle(f"{device_id} | full swing | Ku and Kd {what}",
                 fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / f"fixture_char_{tag}_{device_id}.png", dpi=200)
    plt.close(fig)
    print(f"  fixture_char_{tag}_{device_id}.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--device", action="append",
                    choices=[d.device_id for d in base.DEVICES])
    ap.add_argument("--hspice", type=Path, default=None)
    ap.add_argument("--hspice-timeout", type=int, default=900)
    args = ap.parse_args()
    hspice = args.hspice or default_hspice()
    wanted = set(args.device or ["io_buf"])

    OUT.mkdir(parents=True, exist_ok=True)
    for device in base.DEVICES:
        if device.device_id not in wanted:
            continue
        print(f"\n{device.device_id}  full swing, {WIDTH_NS * 1000:.0f} ps pulse")
        case = base.PulseCase(f"full_swing_{WIDTH_NS * 1000:.0f}ps", EDGE_NS,
                              "short_high", WIDTH_NS, STOP_NS, "full swing")
        solved = solve_all(device, case, hspice, args.hspice_timeout)
        if len(solved) < 2:
            print("  not enough fixtures solved to overlay")
            continue
        # Out to +3 ns so the falling edge into the VCC fixture has room to
        # settle -- at +1.5 the inductive fixtures were still ringing at the
        # right-hand edge of the plot.
        window = (RISE_NS - 0.3, RISE_NS + WIDTH_NS + 3.0)
        for baseline_only in (True, False):
            vt_figure(device.device_id, solved, window, baseline_only)
            kukd_figure(device.device_id, solved, window, baseline_only)

        # How far each fixture moved the coefficients away from the R-only
        # baseline, over the same window the figures show.
        ref = solved[0][2]
        for variant, _, sol in solved[1:]:
            ku, kd, worst = fx.compare(ref, sol)
            print(f"    vs baseline  {variant:<20} Ku RMSE {ku:7.4f}   "
                  f"Kd RMSE {kd:7.4f}   worst {worst:7.4f}")
    print(f"\nwrote {OUT.relative_to(ROOT)} and figures in {FIGS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
