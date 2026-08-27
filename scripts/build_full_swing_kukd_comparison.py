#!/usr/bin/env python3
"""Full-swing Ku/Kd from three independent sources, on one set of axes.

The transistor-derived coefficients are the point of the figure. They come from
running the transistor through the same two fixtures the IBIS file was
characterised with and solving the output equation at every timestep -- the IBIS
V-T tables are never read. That procedure has to be validated somewhere it can
be checked, and a clean full transition is exactly that place: all three sources
are describing the same uninterrupted edge, so they should agree.

    silicon        transistor through two fixtures, solved
    HSPICE native  probed from the BIBIS element (xv_pu / xv_pd)
    pybis          probed from the generated ngspice subcircuit

    py -3.14 scripts/build_full_swing_kukd_comparison.py
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

SOURCE = ROOT / "results" / "ibis_intro_figures_2026-08-25"
OUT = ROOT / "results" / "full_swing_kukd_comparison_2026-08-27"

# device label, csv, edge time, window around the transition
CASES = [
    ("io_buf", SOURCE / "waveforms" / "io_buf_short_high_w10000ps.csv", 5.0, (4.4, 18.0)),
    ("inv_chain", SOURCE / "waveforms" / "inv_chain_short_high_w3000ps.csv", 5.0, (4.8, 8.6)),
]

SILICON = "#111111"
NATIVE = "#2B6CA3"
PYBIS = "#C02626"
DPI = 180


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(rows[0])}


def trmse(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    a, b, t = a[ok], b[ok], t[ok]
    return float(np.sqrt(np.trapezoid((a - b) ** 2, t) / (t[-1] - t[0])))


def style(axis):
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=11.5)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")


def figure(path: Path, label: str, d: dict[str, np.ndarray], window) -> None:
    t = d["time_ns"]
    fig, axes = plt.subplots(2, 1, figsize=(14.2, 8.6), sharex=True)
    for axis, coeff in zip(axes, ("ku", "kd")):
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        axis.plot(t, d[f"silicon_{coeff}"], color=SILICON, lw=3.4,
                  label="silicon  (transistor through two fixtures)", zorder=4)
        axis.plot(t, d[f"hspice_{coeff}"], color=NATIVE, lw=2.4,
                  label="HSPICE native IBIS", zorder=3)
        axis.plot(t, d[f"pybis_{coeff}"], color=PYBIS, lw=2.0, ls=(0, (5, 2.4)),
                  label="pybis  (ngspice)", zorder=5)
        axis.set_ylabel(coeff.replace("k", "K"), fontsize=15)
        axis.set_ylim(-0.15, 1.25)
        axis.set_xlim(*window)
        style(axis)
    axes[0].set_title(f"{label}  |  full transition  |  Ku and Kd from three sources",
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

    print(f"{'case':<12} | {'Ku  sil-nat':>12}{'sil-pyb':>10}{'nat-pyb':>10}"
          f" | {'Kd  sil-nat':>12}{'sil-pyb':>10}{'nat-pyb':>10}")
    for n, (label, path, _edge, window) in enumerate(CASES, start=1):
        if not path.exists():
            print(f"{label:<12} | missing {path}")
            continue
        d = load(path)
        figure(out / f"{n:02d}_{label}_full_swing_kukd.png", label, d, window)
        t = d["time_ns"]
        row = f"{label:<12} |"
        for coeff in ("ku", "kd"):
            s, h, p = (d[f"silicon_{coeff}"], d[f"hspice_{coeff}"], d[f"pybis_{coeff}"])
            row += f" {trmse(s, h, t):11.4f}{trmse(s, p, t):10.4f}{trmse(h, p, t):10.4f} |"
        print(row.rstrip(" |"))
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
