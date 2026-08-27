#!/usr/bin/env python3
"""The clamp between the command capacitor and the gate, and what it hides.

`GUPTARGET` is `min(max(GUPCMD, 0), 1)`. The shipped decks save only the
clamped node, which is exactly the wrong one for asking whether the command is
correct: an error that pushes GUPCMD below zero is erased by the clamp and the
case reads clean. Probing the unclamped node on the five io_buf short-high
targets shows all five commands are corrupted, not three.

Reads the slim CSVs written by ``extract_command_probe.py``; the raw ngspice
records are ~100 MB and are not kept.

    py -3.14 scripts/build_command_clamp_figure.py
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

CASES = [(90, 2484), (80, 2226), (70, 1989), (60, 1792), (50, 1634)]
COLOURS = {90: "#1B4F8F", 80: "#2E8B57", 70: "#8A8A2E", 60: "#C05621", 50: "#B4243C"}
EDGE_NS = 5.0
DPI = 180


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(rows[0])}


def style(axis):
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=11)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(15.6, 9.4), sharex=True)
    rows = []
    for target, width in CASES:
        path = DATA / f"swing_{target}_w{width}ps.csv"
        if not path.exists():
            print(f"missing {path}")
            continue
        d = load(path)
        rel = d["time_ns"] - (EDGE_NS + width / 1000.0)
        colour = COLOURS[target]
        for row, (unclamped, clamped) in enumerate([("gupcmd", "guptarget"),
                                                    ("gdncmd", "gdntarget")]):
            axes[row][0].plot(rel, d[unclamped], color=colour, lw=2.0,
                              label=f"{target}%  ({width} ps)")
            axes[row][1].plot(rel, d[clamped], color=colour, lw=2.0)
        # Settled values are read just before the restoring term is released,
        # which happens a fixed 2.989 ns after the reversal on every case.
        hold = (rel >= 2.60) & (rel <= 2.95)
        rows.append((target, float(d["gupcmd"][hold].mean()),
                     float(d["guptarget"][hold].mean()),
                     float(d["gdncmd"][hold].mean()),
                     float(d["gdntarget"][hold].mean())))

    for row, (label, lo, hi) in enumerate([("pullup command", -0.06, 0.09),
                                           ("pulldown command", 0.93, 1.06)]):
        for col, kind in enumerate(("GUPCMD / GDNCMD   unclamped",
                                    "GUPTARGET / GDNTARGET   after the clamp")):
            axis = axes[row][col]
            axis.axhline(0.0 if row == 0 else 1.0, color="#5A5A5A", lw=1.4, ls="-")
            axis.axvline(0.0, color="#8A8A8A", ls="--", lw=1.6)
            axis.set_ylim(lo, hi)
            axis.set_xlim(0.3, 4.5)
            style(axis)
            if row == 0:
                axis.set_title(kind, fontsize=15, fontweight="bold", pad=11)
        axes[row][0].set_ylabel(label, fontsize=13)
    axes[0][0].legend(fontsize=11, loc="upper right", framealpha=0.94, ncol=2)
    for col in range(2):
        axes[1][col].set_xlabel("Time from the reversal (ns)", fontsize=12.5)
    fig.suptitle("io_buf  |  short high  |  the command capacitor before and after the clamp",
                 fontsize=17, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out / "02_command_clamp.png", dpi=DPI)
    plt.close(fig)

    print("settled just before the restoring term is released (+2.60 to +2.95 ns)")
    print(f"{'tgt':>5} | {'GUPCMD':>10}{'GUPTARGET':>11}  {'hidden?':<10}"
          f"| {'GDNCMD':>10}{'GDNTARGET':>11}  hidden?")
    for target, gc, gt, dc, dt in rows:
        gu_hidden = "yes" if abs(gc - gt) > 1e-6 else "no"
        gd_hidden = "yes" if abs(dc - dt) > 1e-6 else "no"
        print(f"{target:>4}% | {gc:10.6f}{gt:11.6f}  {gu_hidden:<10}"
              f"| {dc:10.6f}{dt:11.6f}  {gd_hidden}")
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
