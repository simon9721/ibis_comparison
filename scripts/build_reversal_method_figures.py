#!/usr/bin/env python3
"""Slide figures for the two reversal-entry rules that did not work.

Two policies, each shown as a pad plot and a Ku/Kd plot, on the same io_buf case
the intro figures use:

    t-matching       at the reversal, enter the opposite table at the same
                     elapsed offset the current one had reached
    value-matching   enter the opposite table where it already holds the Ku and
                     Kd the model has right now

Both are the `...ReplayFull` builders, which replace the whole waveform path
rather than only the reversal. That matters for how these read: neither trace
is wrong only after the reverse edge, and the figures show it. `coeff_match` is
built alongside as the guarded variant that leaves the normal transition alone.

No annotations by request -- traces, a reverse-edge marker, and a legend. The
transistor is on the pad plots because "failed" only means something against
the thing being reproduced.

    py -3.14 scripts/build_reversal_method_figures.py
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

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
OUT = ROOT / "results" / "ibis_intro_figures_2026-08-25" / "figures_methods"

TRANSISTOR = "#808080"
NATIVE = "#000000"

# Same policy colours as the reversal-discontinuity analysis, so a reader who
# has seen that chart carries the mapping over.
METHODS = [
    ("time_match", "t-matching", "#C02626",
     "at the reversal, enter the opposite table at the same elapsed time"),
    ("value_match_full", "Ku/Kd value matching", "#D97706",
     "enter the opposite table where it already holds the present Ku and Kd"),
    ("coeff_match", "Ku/Kd value matching (guarded)", "#7B2CBF",
     "the same rule, applied only at the reversal"),
]

DEVICE = "io_buf"
WIDTH_PS = 1634.0
EDGE_NS = 5.0
WINDOW = (4.6, 8.6)
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


def pad_figure(path, d, colour, label, title, t_rev):
    t = d["time_ns"]
    fig, axis = plt.subplots(figsize=WIDE)
    axis.plot(t, d["silicon_pad"], color=TRANSISTOR, lw=5.0,
              label="HSPICE transistor", zorder=2)
    axis.plot(t, d["hspice_pad"], color=NATIVE, lw=3.0,
              label="HSPICE native IBIS", zorder=3)
    axis.plot(t, d["pybis_pad"], color=colour, lw=2.4, label=label, zorder=4)
    axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1,
                 label="reverse edge")
    axis.set_xlim(*WINDOW)
    axis.set_xlabel("Time (ns)", fontsize=13)
    axis.set_ylabel("Pad voltage (V)", fontsize=13)
    style(axis, title)
    axis.legend(fontsize=12.5, loc="upper left", framealpha=0.92)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def kukd_figure(path, d, colour, label, title, t_rev):
    t = d["time_ns"]
    fig, axes = plt.subplots(2, 1, figsize=STACK, sharex=True)
    for axis, coeff in zip(axes, ("ku", "kd")):
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        axis.plot(t, d[f"hspice_{coeff}"], color=NATIVE, lw=3.0,
                  label="HSPICE native IBIS", zorder=3)
        axis.plot(t, d[f"pybis_{coeff}"], color=colour, lw=2.4, label=label, zorder=4)
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1)
        axis.set_ylabel(coeff.replace("k", "K"), fontsize=15)
        axis.set_ylim(-0.25, 1.3)
        style(axis)
    axes[0].set_title(title, fontsize=18, fontweight="bold", pad=12)
    axes[0].legend(fontsize=12.5, loc="center right", framealpha=0.92)
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    axes[0].set_xlim(*WINDOW)
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

    t_rev = EDGE_NS + WIDTH_PS / 1000.0
    stem = f"{DEVICE}_short_high_w{int(round(WIDTH_PS))}ps.csv"

    for index, (key, label, colour, rule) in enumerate(METHODS, start=5):
        path = MATRIX / key / "waveforms" / stem
        if not path.exists():
            print(f"  {key}: no converged run at this case")
            continue
        d = load(path)
        pad_figure(out / f"{index}_{key}_pad.png", d, colour, label,
                   f"{label}: pad voltage", t_rev)
        kukd_figure(out / f"{index}_{key}_kukd.png", d, colour, label,
                    f"{label}: Ku and Kd", t_rev)

        t = d["time_ns"]
        w = (t >= EDGE_NS) & (t <= t_rev + 2.0)
        pre = (t >= WINDOW[0]) & (t <= EDGE_NS)
        print(f"{label}  ({rule})")
        print(f"   peak pad   transistor {d['silicon_pad'][w].max():.3f} V"
              f"   native IBIS {d['hspice_pad'][w].max():.3f} V"
              f"   model {d['pybis_pad'][w].max():.3f} V")
        print(f"   pad before the pulse: model {d['pybis_pad'][pre].max():.3f} V")
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
