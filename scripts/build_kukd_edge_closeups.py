#!/usr/bin/env python3
"""Ku and Kd on the rising and the falling edge, as separate close-ups.

The full-record figures put a 3 ns transition and a 10 ns plateau on one axis,
so the part worth looking at occupies a fifth of the width. Each edge gets its
own figure here, cropped to the transition, with Ku and Kd stacked.

Silicon is solved on a uniform 5 ps grid (see build_silicon_kukd_conditioning);
native IBIS and pybis come from the comparison record, whose grid is coarser --
median 26 ps, and only one sample across io_buf's settled plateau. Fine detail
in the black trace that is absent from the other two is a grid difference, not
a disagreement.

    py -3.14 scripts/build_kukd_edge_closeups.py
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

INTRO = ROOT / "results" / "ibis_intro_figures_2026-08-25" / "waveforms"
SILICON_DIR = ROOT / "results" / "silicon_kukd_conditioning_2026-08-27" / "waveforms"
OUT = ROOT / "results" / "silicon_kukd_figures_2026-08-27"

SILICON = "#111111"
NATIVE = "#2B6CA3"
PYBIS = "#C02626"
DPI = 180

# device, comparison csv, silicon csv, rising window, falling window
#
# A window has to hold *both* coefficients, not just the one the edge is named
# after. io_buf turns its pullup off 0.068 ns after the input falls but does not
# turn the pulldown on for 1.831 ns, so a window cropped to the Ku fall cuts the
# Kd rise off the right-hand side entirely. The same asymmetry is what opens the
# dead zone in the transport-delay command.
CASES = [
    ("io_buf", INTRO / "io_buf_short_high_w10000ps.csv",
     SILICON_DIR / "io_buf_full_transition.csv", (4.85, 9.5), (14.85, 18.6)),
    ("inv_chain", INTRO / "inv_chain_short_high_w3000ps.csv",
     SILICON_DIR / "inv_chain_full_transition.csv", (4.90, 6.2), (7.90, 9.0)),
]


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(rows[0])}


def style(axis):
    axis.grid(alpha=0.3, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=12)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")


def crossings(t, y, window, levels=(0.8, 0.5, 0.2), rising=True):
    """Where the coefficient passes each level inside the window."""
    m = (t >= window[0]) & (t <= window[1])
    t, y = t[m], y[m]
    out = {}
    for lvl in levels:
        hit = float("nan")
        for i in range(1, len(y)):
            up = y[i - 1] < lvl <= y[i]
            down = y[i - 1] > lvl >= y[i]
            if (rising and up) or (not rising and down):
                hit = t[i - 1] + (lvl - y[i - 1]) * (t[i] - t[i - 1]) / (y[i] - y[i - 1])
                break
        out[lvl] = hit
    return out


def figure(path: Path, device: str, edge: str, comp, sil, window) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13.0, 8.8), sharex=True)
    for axis, coeff in zip(axes, ("ku", "kd")):
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        axis.axhline(0.0, color="#8A8A8A", lw=1.0)
        axis.axhline(1.0, color="#8A8A8A", lw=1.0)
        axis.plot(comp["time_ns"], comp[f"hspice_{coeff}"], color=NATIVE, lw=2.2,
                  label="HSPICE native IBIS", zorder=3)
        axis.plot(comp["time_ns"], comp[f"pybis_{coeff}"], color=PYBIS, lw=2.0,
                  ls=(0, (5, 2.2)), label="pybis", zorder=4)
        axis.plot(sil["time_ns"], sil[f"silicon_{coeff}"], color=SILICON, lw=2.8,
                  label="silicon (transistor)", zorder=5)
        axis.set_ylabel(coeff.replace("k", "K"), fontsize=15)
        axis.set_xlim(*window)
        axis.set_ylim(-0.18, 1.22)
        style(axis)
    axes[0].set_title(f"{device}  |  full transition  |  {edge} edge  |  Ku and Kd",
                      fontsize=17, fontweight="bold", pad=12)
    axes[0].legend(fontsize=12, loc="center right", framealpha=0.94)
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    n = 8  # continues the numbering of the gathered set
    for device, comp_path, sil_path, rise_win, fall_win in CASES:
        if not (comp_path.exists() and sil_path.exists()):
            print(f"missing data for {device}")
            continue
        comp, sil = load(comp_path), load(sil_path)
        for edge, window, rising in (("rising", rise_win, True),
                                     ("falling", fall_win, False)):
            n += 1
            name = f"{n:02d}_edge_{device}_{edge}.png"
            figure(out / name, device, edge, comp, sil, window)
            print(f"\n{device} {edge} edge, Ku level crossings (ns)")
            print(f"{'level':>7}{'silicon':>11}{'native':>11}{'pybis':>11}"
                  f"{'nat-sil':>11}{'pyb-sil':>11}")
            s = crossings(sil["time_ns"], sil["silicon_ku"], window, rising=rising)
            h = crossings(comp["time_ns"], comp["hspice_ku"], window, rising=rising)
            p = crossings(comp["time_ns"], comp["pybis_ku"], window, rising=rising)
            for lvl in (0.8, 0.5, 0.2):
                print(f"{lvl:7.1f}{s[lvl]:11.4f}{h[lvl]:11.4f}{p[lvl]:11.4f}"
                      f"{(h[lvl] - s[lvl]) * 1e3:10.1f}p{(p[lvl] - s[lvl]) * 1e3:10.1f}p")
    print(f"\nwrote to {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
