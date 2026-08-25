#!/usr/bin/env python3
"""Full swing: the gate-state model against legacy pybis, on one axis.

The claim the deck needs is that gate-state changes nothing on an ordinary
transition -- it only earns its keep when an edge is interrupted. On a full
swing there is no reversal, so the two should be indistinguishable, and this
figure is the evidence rather than the assertion.

Gate-state here is the pure build, where Ku and Kd are functions of the hidden
states GUP and GDN rather than of time since the edge. Not the hybrid: the
hybrid hands off to matched replay in a window around a reversal, and on a case
with no reversal that handoff never fires, so it would prove nothing about the
gate-state formulation itself.

The two runs have their own time grids, so the separation is measured by
interpolating gate-state onto the legacy grid rather than by subtracting rows.

    py -3.14 scripts/build_full_swing_gate_state_figure.py
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

BASE = ROOT / "results" / "ibis_intro_figures_2026-08-25"
OUT = BASE / "figures_methods"

# io_buf at 10 ns is absent on purpose: the pure gate-state build does not
# converge there, ngspice collapsing the timestep 2.1 ns into the falling edge.
# 6 ns clears the same transition and does converge, so the comparison is made
# at a width both models can actually run.
CASES = {
    "io_buf": (6000.0, BASE / "legacy_full_swing", (4.0, 14.0)),
    "inv_chain": (3000.0, BASE, (4.9, 8.9)),
}

NATIVE = "#000000"
LEGACY = "#1F6FB2"
GATE = "#1B6B4F"
DPI = 180
WIDE = (14.2, 6.0)
STACK = (14.2, 8.4)


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


def separation(legacy, gate, key, window):
    """Worst gap between the two models inside the plotted window."""
    t = legacy["time_ns"]
    m = (t >= window[0]) & (t <= window[1])
    other = np.interp(t[m], gate["time_ns"], gate[key])
    return float(np.max(np.abs(legacy[key][m] - other)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    for device, (width_ps, legacy_base, window) in CASES.items():
        stem = f"{device}_short_high_w{int(round(width_ps))}ps.csv"
        legacy_csv = legacy_base / "waveforms" / stem
        gate_csv = BASE / "gate_state_full_swing" / "waveforms" / stem
        if not legacy_csv.exists() or not gate_csv.exists():
            missing = [p for p in (legacy_csv, gate_csv) if not p.exists()]
            print(f"{device}: missing {missing[0].relative_to(ROOT)}")
            continue
        legacy, gate = load(legacy_csv), load(gate_csv)
        title = f"{device}  |  full transition  |  gate-state vs legacy"
        stub = f"17_full_swing_gate_state_vs_legacy_{device}"

        fig, axis = plt.subplots(figsize=WIDE)
        axis.plot(legacy["time_ns"], legacy["hspice_pad"], color=NATIVE, lw=4.2,
                  label="HSPICE native IBIS", zorder=2)
        axis.plot(legacy["time_ns"], legacy["pybis_pad"], color=LEGACY, lw=2.6,
                  label="legacy (ngspice)", zorder=3)
        axis.plot(gate["time_ns"], gate["pybis_pad"], color=GATE, lw=2.2,
                  ls=(0, (5, 2.4)), label="gate-state", zorder=4)
        axis.set_xlim(*window)
        axis.set_xlabel("Time (ns)", fontsize=13)
        axis.set_ylabel("Pad voltage (V)", fontsize=13)
        style(axis, f"{title}  |  pad voltage")
        axis.legend(fontsize=12.5, loc="best", framealpha=0.92)
        fig.tight_layout()
        fig.savefig(out / f"{stub}_pad.png", dpi=DPI)
        plt.close(fig)

        fig, axes = plt.subplots(2, 1, figsize=STACK, sharex=True)
        for axis, coeff in zip(axes, ("ku", "kd")):
            axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
            axis.plot(legacy["time_ns"], legacy[f"hspice_{coeff}"], color=NATIVE, lw=4.2,
                      label="HSPICE native IBIS", zorder=2)
            axis.plot(legacy["time_ns"], legacy[f"pybis_{coeff}"], color=LEGACY, lw=2.6,
                      label="legacy (ngspice)", zorder=3)
            axis.plot(gate["time_ns"], gate[f"pybis_{coeff}"], color=GATE, lw=2.2,
                      ls=(0, (5, 2.4)), label="gate-state", zorder=4)
            axis.set_ylabel(coeff.replace("k", "K"), fontsize=15)
            axis.set_ylim(-0.25, 1.3)
            style(axis)
        axes[0].set_title(f"{title}  |  Ku and Kd", fontsize=18, fontweight="bold", pad=12)
        axes[0].legend(fontsize=12.5, loc="center right", framealpha=0.92)
        axes[1].set_xlabel("Time (ns)", fontsize=13)
        axes[0].set_xlim(*window)
        fig.tight_layout()
        fig.savefig(out / f"{stub}_kukd.png", dpi=DPI)
        plt.close(fig)

        print(f"{device} full swing at {width_ps:.0f} ps, gate-state against legacy")
        print(f"  worst separation  pad "
              f"{separation(legacy, gate, 'pybis_pad', window) * 1000:.1f} mV")
        for coeff in ("ku", "kd"):
            print(f"                    {coeff.replace('k', 'K')}"
                  f"  {separation(legacy, gate, f'pybis_{coeff}', window):.3f}")
        for name, d in (("legacy", legacy), ("gate-state", gate)):
            mm = (d["time_ns"] >= window[0]) & (d["time_ns"] <= window[1])
            print(f"  {name:11s} against native IBIS: "
                  f"{np.max(np.abs(d['pybis_pad'][mm] - d['hspice_pad'][mm])) * 1000:.1f} mV")
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
