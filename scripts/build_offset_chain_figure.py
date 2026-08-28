#!/usr/bin/env python3
"""The settled offset traced through one buffer, one case, one link per panel.

Figure 03 reads top to bottom. Each panel is the input to the panel below it,
so the pad offset can be followed upward until it reaches the layer that
created it:

    GUPCMD      the command capacitor          <- created here
    GUPTARGET   after the clamp
    GUP         the gate state
    Ku          the map of the gate, plus the residual
    pad         what the load sees

Only the 60% case is drawn. An earlier version put 60% and 70% side by side to
contrast a bad case with a good one, which is misleading: 70% is *not* good.
Its command error is -0.0056 and the clamp erases it, so a reader comparing the
two would conclude the defect is case-dependent when in fact all five cases
carry it. That comparison belongs in figure 02, where the clamp is the subject.

Figure 04 is the same case before and after the restore-term fix.

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

BASE = ROOT / "results" / "settled_offset_diagnosis_2026-08-27"
PROBE = BASE / "command_probe"
FIX = BASE / "fix_probe"
MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20" / "hybrid" / "waveforms"

CASE = (60, 1792)
EDGE_NS = 5.0
INK = "#C05621"
SHIPPED_C = "#8A8A8A"
FIXED_C = "#1B6B4F"
SILICON_C = "#111111"
NATIVE_C = "#2B6CA3"
DPI = 170

CHAIN = [
    ("gupcmd", "GUPCMD", "the command capacitor", (-0.02, 0.06)),
    ("guptarget", "GUPTARGET", "after the clamp  min(max(x,0),1)", (-0.02, 0.06)),
    ("gup", "GUP", "the gate state follows the command", (-0.02, 0.06)),
    ("ku", "Ku", "the map of the gate, plus the residual", (-0.02, 0.10)),
    ("pad", "Pad (V)", "what the load sees", (-0.01, 0.13)),
]


def load(path: Path, width: int) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) for x in r] for r in rows[1:]])
    d = {name: values[:, i] for i, name in enumerate(rows[0])}
    d["rel_ns"] = d["time_ns"] - (EDGE_NS + width / 1000.0)
    return d


def silicon(width: int) -> dict[str, np.ndarray]:
    """The transistor and native-IBIS references for the same stimulus.

    Only the last two panels have a reference to draw: GUPCMD, GUPTARGET and
    GUP are internal to the model and silicon has no counterpart for them.
    That is the point of the figure -- the offset is only *visible* at Ku and
    the pad, and only *explicable* in the three panels above them.
    """
    rows = list(csv.reader((MATRIX / f"io_buf_short_high_w{width}ps.csv")
                           .open(newline="", encoding="utf-8")))
    values = np.array([[float(x) for x in r] for r in rows[1:]])
    d = {name: values[:, i] for i, name in enumerate(rows[0])}
    d["rel_ns"] = d["time_ns"] - (EDGE_NS + width / 1000.0)
    return d


REFERENCE = {"ku": ("silicon_ku", "hspice_ku"), "pad": ("silicon_pad", "hspice_pad")}


def draw_reference(axis, ref, node, label=False):
    if node not in REFERENCE:
        return
    sil, nat = REFERENCE[node]
    axis.plot(ref["rel_ns"], ref[nat], color=NATIVE_C, lw=1.8,
              label="HSPICE native IBIS" if label else None, zorder=2)
    axis.plot(ref["rel_ns"], ref[sil], color=SILICON_C, lw=3.4,
              label="HSPICE transistor" if label else None, zorder=3)


def settled(d: dict[str, np.ndarray], node: str) -> float:
    hold = (d["rel_ns"] >= 2.60) & (d["rel_ns"] <= 2.95)
    return float(d[node][hold].mean())


def style(axis, label, caption, ylim):
    axis.axhline(0.0, color="#5A5A5A", lw=1.2)
    axis.axvline(0.0, color="#8A8A8A", ls="--", lw=1.5)
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


def chain_figure(out: Path, target: int, width: int) -> None:
    d = load(PROBE / f"swing_{target}_w{width}ps.csv", width)
    ref = silicon(width)
    fig, axes = plt.subplots(len(CHAIN), 1, figsize=(12.0, 13.2), sharex=True)
    for n, (axis, (node, label, caption, ylim)) in enumerate(zip(axes, CHAIN)):
        draw_reference(axis, ref, node, label=(node == "ku"))
        axis.plot(d["rel_ns"], d[node], color=INK, lw=2.8,
                  label="gate-state model" if node == "ku" else None, zorder=4)
        style(axis, label, caption, ylim)
        axis.text(0.012, 0.90, f"model settles at {settled(d, node):+.4f}",
                  transform=axis.transAxes, fontsize=12.5, family="monospace",
                  color=INK, va="top")
        if node in REFERENCE:
            sil = REFERENCE[node][0]
            axis.text(0.012, 0.72, f"transistor    {settled(ref, sil):+.4f}",
                      transform=axis.transAxes, fontsize=12.5, family="monospace",
                      color=SILICON_C, va="top")
        if node == "ku":
            axis.legend(fontsize=11, loc="upper right", framealpha=0.94,
                        bbox_to_anchor=(1.0, 0.80))
    axes[-1].set_xlabel("Time from the reversal (ns)", fontsize=13)
    fig.suptitle(f"io_buf  |  short high  |  target {target}%  ({width} ps)  |  "
                 "the offset at every layer", fontsize=17, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.977))
    fig.savefig(out / "03_offset_chain.png", dpi=DPI)
    plt.close(fig)


def fix_figure(out: Path, target: int, width: int) -> None:
    ship = load(FIX / f"as_shipped_swing{target}_w{width}ps.csv", width)
    fixed = load(FIX / f"gate_and_tau_swing{target}_w{width}ps.csv", width)
    ref = silicon(width)
    fig, axes = plt.subplots(len(CHAIN), 1, figsize=(12.0, 13.2), sharex=True)
    for axis, (node, label, caption, ylim) in zip(axes, CHAIN):
        draw_reference(axis, ref, node, label=(node == "ku"))
        axis.plot(ship["rel_ns"], ship[node], color=SHIPPED_C, lw=3.2,
                  label="as shipped   gate 2.958 ns, tau 1.127 ns", zorder=4)
        axis.plot(fixed["rel_ns"], fixed[node], color=FIXED_C, lw=2.2,
                  ls=(0, (5, 2.2)), label="fixed   gate 1.831 ns, tau 0.250 ns",
                  zorder=5)
        style(axis, label, caption, ylim)
        axis.text(0.012, 0.90,
                  f"{settled(ship, node):+.4f}  ->  {settled(fixed, node):+.4f}",
                  transform=axis.transAxes, fontsize=12.5, family="monospace",
                  color="#2A3742", va="top")
    axes[0].legend(fontsize=11.5, loc="upper right", framealpha=0.94,
                   bbox_to_anchor=(1.0, 0.74))
    axes[-1].set_xlabel("Time from the reversal (ns)", fontsize=13)
    fig.suptitle(f"io_buf  |  short high  |  target {target}%  ({width} ps)  |  "
                 "before and after the restore-term change",
                 fontsize=17, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.977))
    fig.savefig(out / "04_offset_fix.png", dpi=DPI)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=BASE)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    target, width = CASE

    chain_figure(out, target, width)
    fix_figure(out, target, width)

    ship = load(FIX / f"as_shipped_swing{target}_w{width}ps.csv", width)
    fixed = load(FIX / f"gate_and_tau_swing{target}_w{width}ps.csv", width)
    print(f"io_buf short high {target}% ({width} ps), settled at +2.60 to +2.95 ns")
    print(f"{'layer':<12}{'as shipped':>13}{'fixed':>13}{'change':>13}")
    for node, label, _, _ in CHAIN:
        a, b = settled(ship, node), settled(fixed, node)
        print(f"{label:<12}{a:13.5f}{b:13.5f}{b - a:13.5f}")
    print(f"\nwrote {out.resolve()}\\03_offset_chain.png")
    print(f"wrote {out.resolve()}\\04_offset_fix.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
