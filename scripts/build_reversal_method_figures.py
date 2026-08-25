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
# coeff_match is the working implementation of value matching, not a variant of
# it: the v1 `...Full` build drives the pad from a match against nothing before
# the first edge, and v1 hybrid still mixes a stale elapsed-time coordinate into
# the replay argument at the reversal. So the plain name belongs to v2, and the
# broken builds are named for what is wrong with them.
# The two working rules keep slide numbers, continuing the intro set. The broken
# builds keep an "x_" prefix instead: they belong in an appendix showing the
# defect, not in the numbered flow, and a number would imply otherwise.
METHODS = [
    ("5", "time_match_hybrid", "t_matching", "t-matching", "#C02626",
     "at the reversal, enter the opposite table at the same elapsed time"),
    ("6", "coeff_match", "value_matching", "Ku/Kd value matching", "#7B2CBF",
     "enter the opposite table where it already holds the present Ku and Kd"),
    ("x", "time_match", "t_matching_ungated", "t-matching (ungated build)", "#C02626",
     "the same rule with the replay path forced on from t=0"),
    ("x", "value_match_full", "value_matching_ungated",
     "Ku/Kd value matching (ungated build)", "#D97706",
     "the same rule with the replay path forced on from t=0"),
]

# A method is only as good as the case it is shown on. io_buf short_high at
# 1634 ps is coeff_match's *best* of the thirty (33 mV); its worst is io_buf
# short_low at 180 ps (283 mV), where it drives the pad to the opposite rail
# while the transistor only dips halfway. Both are built, and the filenames say
# which is which.
CASES = {
    "best": ("io_buf", "short_high", 1634.0, (4.6, 8.6)),
    "worst": ("io_buf", "short_low", 180.4, (9.6, 13.6)),
}
EDGE_NS = {"short_high": 5.0, "short_low": 10.0}
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


def pad_figure(path, d, colour, label, title, t_rev, window):
    t = d["time_ns"]
    fig, axis = plt.subplots(figsize=WIDE)
    axis.plot(t, d["silicon_pad"], color=TRANSISTOR, lw=5.0,
              label="HSPICE transistor", zorder=2)
    axis.plot(t, d["hspice_pad"], color=NATIVE, lw=3.0,
              label="HSPICE native IBIS", zorder=3)
    axis.plot(t, d["pybis_pad"], color=colour, lw=2.4, label=label, zorder=4)
    axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1,
                 label="reverse edge")
    axis.set_xlim(*window)
    axis.set_xlabel("Time (ns)", fontsize=13)
    axis.set_ylabel("Pad voltage (V)", fontsize=13)
    style(axis, title)
    axis.legend(fontsize=12.5, loc="best", framealpha=0.92)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def kukd_figure(path, d, colour, label, title, t_rev, window):
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
    axes[0].set_xlim(*window)
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

    for case_name, (device, direction, width_ps, window) in CASES.items():
        edge_ns = EDGE_NS[direction]
        t_rev = edge_ns + width_ps / 1000.0
        stem = f"{device}_{direction}_w{int(round(width_ps))}ps.csv"
        print(f"\n=== {case_name}: {device} {direction} {width_ps:.0f} ps")

        for index, key, slug, label, colour, rule in METHODS:
            path = MATRIX / key / "waveforms" / stem
            if not path.exists():
                print(f"  {label}: no converged run at this case")
                continue
            d = load(path)
            title = f"{device}  |  {width_ps:.0f} ps pulse  |  {label}"
            stub = f"{index}_{slug}_{case_name}"
            pad_figure(out / f"{stub}_pad.png", d, colour, label,
                       f"{title}  |  pad voltage", t_rev, window)
            kukd_figure(out / f"{stub}_kukd.png", d, colour, label,
                        f"{title}  |  Ku and Kd", t_rev, window)

            t = d["time_ns"]
            w = (t >= edge_ns) & (t <= t_rev + 3.0)
            # Short-low drives the pad down, so the excursion of interest is the
            # minimum there and the maximum on short-high.
            pick = (lambda a: a[w].min()) if direction == "short_low" else (lambda a: a[w].max())
            print(f"  {label}")
            print(f"     pad excursion  transistor {pick(d['silicon_pad']):.3f} V"
                  f"   native IBIS {pick(d['hspice_pad']):.3f} V"
                  f"   model {pick(d['pybis_pad']):.3f} V")
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
