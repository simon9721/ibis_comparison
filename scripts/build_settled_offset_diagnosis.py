#!/usr/bin/env python3
"""Trace the io_buf short-high settled offset from the pad back to the command.

The 2026-08-20 stress figures show io_buf short-high leaving the pad elevated
for several nanoseconds after the reversal at targets 90/60/50, while 80 and 70
return cleanly. This walks that back one layer at a time:

    pad  <-  Ku  <-  pwl(GUP)  <-  GUP  <-  GUPTARGET  <-  command capacitor

Left column is the shipped edge-integrating command, right column the
transport-delay command, on the same five cases. Time is measured from the
reversal so the five widths overlay.

    py -3.14 scripts/build_settled_offset_diagnosis.py
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / ".codex_deps" / "presentation" / "python", ROOT / "scripts",
          ROOT / "tools" / "pybis2spice", ROOT):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402
from run_stress_method_matrix import case_tag, stress_cases  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27"

DEVICE, DIRECTION, EDGE_NS = "io_buf", "short_high", 5.0
COLUMNS = [("hybrid", "edge-integrating command  (shipped)"),
           ("delay_cmd", "transport-delay command")]
ROWS = [("guptarget", "GUPTARGET   the command"),
        ("ku", "Ku"),
        ("pad", "Pad voltage (V)")]
# Ordered so the colours run with the target, not with the pulse width.
COLOURS = {90: "#1B4F8F", 80: "#2E8B57", 70: "#8A8A2E", 60: "#C05621", 50: "#B4243C"}
DPI = 180


def raw(method: str, tag: str):
    hits = glob.glob(str(MATRIX / method / "ngspice_runs" / DEVICE / "*" / "*" /
                         "cases" / f"{tag.split(DEVICE + '_')[1]}_*" /
                         "ngspice_gate_state" / "run.raw"))
    if not hits:
        return None
    r = parse_ngspice_raw(Path(hits[0]))
    k = {x.lower(): x for x in r}
    d = {n[7:-1]: np.asarray(r[k[n]]) for n in k if n.startswith("v(xdrv.")}
    d["pad"] = np.asarray(r[k["v(pad)"]])
    return np.asarray(r[k["time"]]) * 1e9, d


def cases():
    for device, direction, widths in stress_cases():
        if device == DEVICE and direction == DIRECTION:
            return widths
    return []


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

    fig, axes = plt.subplots(3, 2, figsize=(15.6, 11.6), sharex=True)
    settled = {}
    for col, (method, heading) in enumerate(COLUMNS):
        for target, width_ps in cases():
            got = raw(method, case_tag(DEVICE, DIRECTION, width_ps))
            if got is None:
                continue
            t, v = got
            rel = t - (EDGE_NS + width_ps / 1000.0)
            colour = COLOURS[target]
            for row, (node, _) in enumerate(ROWS):
                axes[row][col].plot(rel, v[node], color=colour, lw=2.0,
                                    label=f"{target}%  ({width_ps:.0f} ps)")
            hold = (rel >= 1.0) & (rel <= 2.5)
            settled[(method, target)] = (float(v["guptarget"][hold].mean()),
                                         float(v["ku"][hold].mean()),
                                         float(v["pad"][hold].mean()) * 1e3)
        axes[0][col].set_title(heading, fontsize=16, fontweight="bold", pad=12)

    for row, (node, ylabel) in enumerate(ROWS):
        for col in range(2):
            axis = axes[row][col]
            axis.axvline(0.0, color="#8A8A8A", ls="--", lw=1.6)
            axis.set_xlim(-0.4, 6.0)
            style(axis)
            if node == "guptarget":
                axis.set_ylim(-0.05, 1.08)
            elif node == "ku":
                axis.set_ylim(-0.06, 0.30)
        axes[row][0].set_ylabel(ylabel, fontsize=13)
    axes[0][0].legend(fontsize=11, loc="upper right", framealpha=0.94, ncol=2)
    for col in range(2):
        axes[2][col].set_xlabel("Time from the reversal (ns)", fontsize=12.5)
    fig.suptitle(f"{DEVICE}  |  {DIRECTION.replace('_', ' ')}  |  "
                 "command, Ku and pad after the reversal",
                 fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    fig.savefig(out / "01_command_to_pad.png", dpi=DPI)
    plt.close(fig)

    print(f"{'':>6} {'edge-integrating command':^34} | {'transport-delay command':^34}")
    print(f"{'tgt':>6} {'GUPTARGET':>11}{'Ku':>11}{'pad mV':>11} | "
          f"{'GUPTARGET':>11}{'Ku':>11}{'pad mV':>11}    (mean over +1.0 to +2.5 ns)")
    for target, _ in cases():
        row = f"{target:>5}%"
        for method, _ in COLUMNS:
            if (method, target) not in settled:
                row += f" {'--':>11}{'--':>11}{'--':>11} |"
                continue
            g, k, p = settled[(method, target)]
            row += f" {g:11.4f}{k:11.4f}{p:11.2f} |"
        print(row.rstrip(" |"))
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
