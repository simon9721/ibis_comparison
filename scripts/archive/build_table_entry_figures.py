#!/usr/bin/env python3
"""Where each reversal rule re-enters the falling table, drawn in table space.

The simulated Ku traces for t-matching and value matching look nearly identical
-- both collapse almost vertically at the reversal -- which makes it impossible
to see, from the waveform alone, that the two rules chose different entry
points, or to rule out a bug.

Plotting the tables themselves settles it. The falling Ku table is a cliff: it
leaves 0.94 and is under 0.03 within 500 ps, while the rising Ku table needs the
full 6 ns to climb. So every entry rule lands on a curve that is already at or
near zero, and the choice of entry point buys only a few hundred picoseconds.
The near-vertical drop is the table's own shape, not a discontinuity the
solver invented.

Two figures:

  table space   the rising and falling Ku and Kd tables against time-since-edge,
                with the exit point and both rules' entry points marked
  real time     both methods and native IBIS on one axis, so the gap the two
                entry rules actually produce is visible at its true size

    py -3.14 scripts/build_table_entry_figures.py
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for q in (ROOT / ".codex_deps" / "presentation" / "python", ROOT, ROOT / "scripts",
          ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from pybis2spice import pybis2spice as pb, subcircuit as sc  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
OUT = ROOT / "results" / "ibis_intro_figures_2026-08-25" / "figures_methods"

DEVICE = "io_buf"
WIDTH_PS = 1634.0
ELAPSED_NS = 1.6342
EDGE_NS = 5.0

RISING = "#1B6B4F"
FALLING = "#AE4E19"
NATIVE = "#000000"
TMATCH = "#C02626"
VMATCH = "#7B2CBF"
GATE = "#1F6FB2"
DPI = 180


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def style(axis, title=None):
    axis.grid(alpha=0.3, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=12)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")
    if title:
        axis.set_title(title, fontsize=18, fontweight="bold", pad=12)


def matched_time(k_table, col, target):
    """The entry time the model's own inverse map returns for `target`.

    Deliberately not a hand-rolled first-crossing search. The falling Kd curve
    sits near zero across most of the table, so "where does Kd equal 0.019" has
    no unique answer, and a first-crossing search and the shipped map disagree by
    1.45 ns. Only the map the netlist actually embeds explains the waveform.
    """
    inv_x, inv_t = sc.inverse_time_lookup_table(k_table[:, 0], k_table[:, col])
    return float(np.interp(target, inv_x, inv_t))


def first_crossing(t, values, target):
    """Earliest time the table passes through `target`, or nan."""
    idx = np.where(np.diff(np.sign(values - target)) != 0)[0]
    if not len(idx):
        return float("nan")
    i = idx[0]
    lo, hi = values[i], values[i + 1]
    if hi == lo:
        return float(t[i])
    return float(t[i] + (target - lo) / (hi - lo) * (t[i + 1] - t[i]))


def tables():
    device = next(d for d in base.DEVICES if d.device_id == DEVICE)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                        model_name=device.model, component_name=device.component)
    kr = pb.solve_k_params_output(data, corner=1, waveform_type="Rising")
    kf = pb.solve_k_params_output(data, corner=1, waveform_type="Falling")
    return kr, kf


def table_space_figure(path, kr, kf):
    tr, tf = kr[:, 0] * 1e9, kf[:, 0] * 1e9
    fig, axes = plt.subplots(2, 1, figsize=(14.2, 8.4), sharex=True)

    entries = {}
    for axis, col, name in ((axes[0], 1, "Ku"), (axes[1], 2, "Kd")):
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        axis.plot(tr, kr[:, col], color=RISING, lw=3.2, label=f"rising table {name}", zorder=3)
        axis.plot(tf, kf[:, col], color=FALLING, lw=3.2, label=f"falling table {name}", zorder=3)

        now = float(np.interp(ELAPSED_NS, tr, kr[:, col]))
        t_val = matched_time(kf, col, now)
        entries[name] = (now, t_val)

        axis.plot([ELAPSED_NS], [now], "o", ms=13, color=RISING,
                  mec="white", mew=2, zorder=6,
                  label=f"where we are at the reversal ({now:.3f})")
        axis.plot([ELAPSED_NS], [float(np.interp(ELAPSED_NS, tf, kf[:, col]))], "s", ms=12,
                  color=TMATCH, mec="white", mew=2, zorder=6,
                  label="t-matching enters here")
        if np.isfinite(t_val):
            axis.plot([t_val], [now], "D", ms=11, color=VMATCH, mec="white", mew=2,
                      zorder=6, label=f"{name} on its own would enter here")
        axis.axvline(ELAPSED_NS, color="#8A8A8A", ls="--", lw=1.6, zorder=1)
        axis.set_ylabel(name, fontsize=15)
        axis.set_ylim(-0.15, 1.25)
        style(axis)
        axis.legend(fontsize=11.5, loc="upper right", framealpha=0.94, ncol=2)

    axes[0].set_title(
        f"{DEVICE}  |  {WIDTH_PS:.0f} ps pulse  |  where each rule re-enters the falling table",
        fontsize=18, fontweight="bold", pad=12)
    axes[1].set_xlabel("Time since the edge, along the table (ns)", fontsize=13)
    axes[0].set_xlim(0.0, 3.0)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return entries


def real_time_figure(path, t_rev):
    paths = {
        "t-matching": (MATRIX / "time_match_hybrid" / "waveforms" /
                       f"{DEVICE}_short_high_w{int(round(WIDTH_PS))}ps.csv", TMATCH),
        "Ku/Kd value matching": (MATRIX / "coeff_match" / "waveforms" /
                                 f"{DEVICE}_short_high_w{int(round(WIDTH_PS))}ps.csv", VMATCH),
    }
    fig, axes = plt.subplots(2, 1, figsize=(14.2, 8.4), sharex=True)
    first = True
    for label, (path_in, colour) in paths.items():
        if not path_in.exists():
            continue
        d = load(path_in)
        t = d["time_ns"]
        for axis, coeff in zip(axes, ("ku", "kd")):
            if first:
                axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
                axis.plot(t, d[f"hspice_{coeff}"], color=NATIVE, lw=3.2,
                          label="HSPICE native IBIS", zorder=3)
            axis.plot(t, d[f"pybis_{coeff}"], color=colour, lw=2.4, label=label, zorder=4)
        first = False
    for axis, coeff in zip(axes, ("ku", "kd")):
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1)
        axis.set_ylabel(coeff.replace("k", "K"), fontsize=15)
        axis.set_ylim(-0.25, 1.3)
        style(axis)
    axes[0].set_title(
        f"{DEVICE}  |  {WIDTH_PS:.0f} ps pulse  |  both rules, same axis",
        fontsize=18, fontweight="bold", pad=12)
    axes[0].legend(fontsize=12.5, loc="upper right", framealpha=0.94)
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    axes[0].set_xlim(EDGE_NS + 1.2, EDGE_NS + 3.2)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def discontinuity_figure(path, t_rev):
    """The step each rule asks the solver to take, next to one that takes none.

    Both replay rules leave the rising table at one coefficient value and resume
    the falling table at another, so Ku moves discontinuously. The gate-state
    model integrates a hidden state through the reversal instead, so its Ku is
    continuous by construction -- which is the whole argument for it.
    """
    series = [
        ("HSPICE native IBIS", "hybrid", "hspice", NATIVE, 3.2),
        ("t-matching", "time_match_hybrid", "pybis", TMATCH, 2.4),
        ("Ku/Kd value matching", "coeff_match", "pybis", VMATCH, 2.4),
        ("gate-state", "hybrid", "pybis", GATE, 2.4),
    ]
    stem = f"{DEVICE}_short_high_w{int(round(WIDTH_PS))}ps.csv"
    fig, axes = plt.subplots(2, 1, figsize=(14.2, 8.4), sharex=True)
    for axis in axes:
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
    steps = {}
    for label, method, source, colour, lw in series:
        path_in = MATRIX / method / "waveforms" / stem
        if not path_in.exists():
            continue
        d = load(path_in)
        t = d["time_ns"]
        for axis, coeff in zip(axes, ("ku", "kd")):
            axis.plot(t, d[f"{source}_{coeff}"], color=colour, lw=lw, label=label, zorder=3)
        # How fast Ku gives up the drop, not how far it moves. An earlier attempt
        # summed the excursion in the window and ranked gate-state worst, which is
        # backwards: gate-state travels furthest precisely because it keeps
        # moving instead of jumping. What separates the methods is the rate.
        ku = d[f"{source}_ku"]
        start = float(ku[int(np.searchsorted(t, t_rev))])
        window = (t >= t_rev) & (t <= t_rev + 1.5)
        floor = float(np.min(ku[window]))
        reached = np.where(ku[window] <= start - 0.9 * (start - floor))[0]
        if len(reached):
            steps[label] = float(t[window][reached[0]] - t_rev) * 1000.0
    for axis, coeff in zip(axes, ("Ku", "Kd")):
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1)
        axis.set_ylabel(coeff, fontsize=15)
        axis.set_ylim(-0.25, 1.3)
        style(axis)
    axes[0].set_title(
        f"{DEVICE}  |  {WIDTH_PS:.0f} ps pulse  |  the step demanded at the reversal",
        fontsize=18, fontweight="bold", pad=12)
    axes[0].legend(fontsize=12.5, loc="upper right", framealpha=0.94)
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    axes[0].set_xlim(t_rev - 0.25, t_rev + 0.75)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    kr, kf = tables()
    tf = kf[:, 0] * 1e9
    entries = table_space_figure(out / "9_table_entry.png", kr, kf)
    t_rev = EDGE_NS + WIDTH_PS / 1000.0
    real_time_figure(out / "10_both_rules_real_time.png", t_rev)
    steps = discontinuity_figure(out / "11_reversal_discontinuity.png", t_rev)

    print(f"{DEVICE} short_high {WIDTH_PS:.0f} ps, reversal at elapsed {ELAPSED_NS:.4f} ns\n")
    for name, (now, t_val) in entries.items():
        col = 1 if name == "Ku" else 2
        at_t = float(np.interp(ELAPSED_NS, tf, kf[:, col]))
        print(f"  {name}: {now:.4f} at the reversal")
        print(f"     t-matching     enters the falling table at {ELAPSED_NS:.4f} ns"
              f"  -> {name} = {at_t:.4f}")
        print(f"     value matching enters at {t_val:.4f} ns"
              f"  -> {name} = {now:.4f} by construction")
    # The balanced policy the model actually runs averages the two matched
    # times, so neither coefficient lands exactly where its own map asked.
    t_ku, t_kd = entries["Ku"][1], entries["Kd"][1]
    if np.isfinite(t_ku) and np.isfinite(t_kd):
        print(f"\n  the balanced policy averages them: entry at "
              f"{0.5 * (t_ku + t_kd):.4f} ns")
    print(f"\n  falling Ku leaves {kf[0, 1]:.3f} and is under 0.03 by "
          f"{first_crossing(tf, kf[:, 1], 0.03):.3f} ns")
    print(f"  rising Ku reaches only {float(np.interp(ELAPSED_NS, kr[:, 0] * 1e9, kr[:, 1])):.3f}"
          f" in that time")
    print("\n  Ku after the reversal: time to give up 90% of the drop")
    for label, value in sorted(steps.items(), key=lambda kv: kv[1]):
        print(f"     {label:24s} {value:6.1f} ps")
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
