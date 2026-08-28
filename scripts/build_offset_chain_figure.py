#!/usr/bin/env python3
"""One case, one column, one link of the causal chain per panel.

Reads top to bottom. Each panel is the input to the panel below it, so the
question "where does the pad offset come from" is answered by looking upward
until the traces stop separating:

    GUPCMD      the command capacitor          <- the defect is created here
    GUPTARGET   after the clamp                <- and two cases are hidden here
    GUP         the gate state
    KUGATE      pwl(GUP), the map
    Ku          KUGATE + KURES
    pad         what the load sees

Two cases are drawn against each other rather than all five: 60%, the worst
offset, and 70%, which reads clean. They differ only in pulse width, so any
separation between them is the defect and nothing else.

    py -3.14 scripts/build_offset_chain_figure.py
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

DATA = ROOT / "results" / "settled_offset_diagnosis_2026-08-27" / "command_probe"
OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27"

BAD, GOOD = (60, 1792), (70, 1989)
BAD_C, GOOD_C = "#C05621", "#2E8B57"
EDGE_NS = 5.0
DPI = 170

# node, label, what the panel is showing, y limits
CHAIN = [
    ("gupcmd", "GUPCMD", "the command capacitor", (-0.03, 0.06)),
    ("guptarget", "GUPTARGET", "after the clamp  min(max(x,0),1)", (-0.03, 0.06)),
    ("gup", "GUP", "the gate state follows the command", (-0.03, 0.06)),
    ("ku", "Ku", "the map, plus the residual", (-0.03, 0.10)),
    ("pad", "Pad (V)", "what the load sees", (-0.02, 0.12)),
]


def load(target: int, width: int) -> dict[str, np.ndarray]:
    rows = list(csv.reader((DATA / f"swing_{target}_w{width}ps.csv")
                           .open(newline="", encoding="utf-8")))
    values = np.array([[float(x) for x in r] for r in rows[1:]])
    d = {name: values[:, i] for i, name in enumerate(rows[0])}
    d["rel_ns"] = d["time_ns"] - (EDGE_NS + width / 1000.0)
    return d


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    bad, good = load(*BAD), load(*GOOD)
    fig, axes = plt.subplots(len(CHAIN), 1, figsize=(12.4, 13.6), sharex=True)

    for axis, (node, label, caption, ylim) in zip(axes, CHAIN):
        axis.axhline(0.0, color="#5A5A5A", lw=1.2)
        axis.plot(good["rel_ns"], good[node], color=GOOD_C, lw=2.6,
                  label=f"{GOOD[0]}%  ({GOOD[1]} ps)")
        axis.plot(bad["rel_ns"], bad[node], color=BAD_C, lw=2.6,
                  label=f"{BAD[0]}%  ({BAD[1]} ps)")
        axis.set_ylim(*ylim)
        axis.set_xlim(-0.2, 7.0)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=11)
        for spine in axis.spines.values():
            spine.set_color("#3A4753")
        axis.set_ylabel(label, fontsize=14)
        axis.text(0.988, 0.90, caption, transform=axis.transAxes, ha="right", va="top",
                  fontsize=11.5, color="#40505E",
                  bbox=dict(fc="white", ec="#C3CCD6", pad=3.5))
        # settled value of each trace, read where both have stopped moving
        for d, colour in ((good, GOOD_C), (bad, BAD_C)):
            hold = (d["rel_ns"] >= 2.60) & (d["rel_ns"] <= 2.95)
            value = float(d[node][hold].mean())
            axis.text(0.012, 0.88 if colour == BAD_C else 0.68,
                      f"{value:+.4f}", transform=axis.transAxes, fontsize=12,
                      family="monospace", color=colour, va="top")

    axes[0].axvline(0.0, color="#8A8A8A", ls="--", lw=1.5)
    for axis in axes:
        axis.axvline(0.0, color="#8A8A8A", ls="--", lw=1.5)
    axes[0].legend(fontsize=12, loc="upper right", framealpha=0.94,
                   bbox_to_anchor=(1.0, 0.72))
    axes[-1].set_xlabel("Time from the reversal (ns)", fontsize=13)
    fig.suptitle("io_buf  |  short high  |  the same defect at every layer",
                 fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.977))
    fig.savefig(out / "03_offset_chain.png", dpi=DPI)
    plt.close(fig)

    print("settled values, read at +2.60 to +2.95 ns from the reversal")
    print(f"{'layer':<12}{f'{GOOD[0]}% (clean)':>16}{f'{BAD[0]}% (offset)':>17}{'separation':>13}")
    for node, label, _, _ in CHAIN:
        g = float(good[node][(good["rel_ns"] >= 2.60) & (good["rel_ns"] <= 2.95)].mean())
        b = float(bad[node][(bad["rel_ns"] >= 2.60) & (bad["rel_ns"] <= 2.95)].mean())
        print(f"{label:<12}{g:16.5f}{b:17.5f}{b - g:13.5f}")
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
