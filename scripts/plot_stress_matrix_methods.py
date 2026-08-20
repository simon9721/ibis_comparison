#!/usr/bin/env python3
"""Overlay every method's pad against silicon, at the extremes of the stress axis.

The per-case plots the comparison script writes show one method at a time,
which answers "is this model right" but not "which model is least wrong". This
puts them on shared axes at the mildest and harshest stress level for each
buffer and direction, so a method that only works in one regime is visible as
such rather than averaging into a single number.

Silicon is drawn heaviest because it is the thing being matched; HSPICE native
IBIS is drawn next because it is the bar, having exactly the information the
models have.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
sys.path.insert(0, str(ROOT / "scripts"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from run_stress_method_matrix import METHODS, case_tag, stress_cases  # noqa: E402

SILICON = "#111111"
NATIVE = "#2B6CA3"
# Distinct enough to separate on a shared axis without becoming a rainbow.
METHOD_COLORS = {
    "gate_state": "#C02626",
    "delay_cmd": "#1B7F5A",
    "predriver_cmd": "#7B2CBF",
    "legacy": "#8A8A8A",
    "coeff_match": "#D97706",
    "pad_match": "#0E7490",
    "pad_match_slew": "#9A3412",
    "hybrid": "#A16207",
}


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path,
                        default=ROOT / "results" / "stress_method_matrix_2026-08-20")
    args = parser.parse_args()
    root = args.matrix if args.matrix.is_absolute() else ROOT / args.matrix
    out_dir = root / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    available = [(key, label) for key, _, label in METHODS
                 if (root / key / "waveforms").exists()]
    if not available:
        print(f"no method output under {root}")
        return 1

    grouped: dict[str, list[tuple[str, list[tuple[int, float]]]]] = {}
    for device, direction, widths in stress_cases():
        grouped.setdefault(device, []).append((direction, widths))

    written = 0
    for device, entries in grouped.items():
        fig, axes = plt.subplots(len(entries), 2, figsize=(13.0, 4.1 * len(entries)),
                                 squeeze=False)
        drew_any = False
        for row, (direction, widths) in enumerate(entries):
            # Mildest and harshest stress the sweep found for this direction.
            extremes = [widths[0], widths[-1]]
            for column, (target, width_ps) in enumerate(extremes):
                axis = axes[row][column]
                tag = case_tag(device, direction, width_ps)
                edge_ns = 5.0 if direction == "short_high" else 10.0
                t_rev = edge_ns + width_ps / 1000.0
                drew_reference = False
                for key, _ in available:
                    path = root / key / "waveforms" / f"{tag}.csv"
                    if not path.exists():
                        continue
                    d = load(path)
                    t = d["time_ns"]
                    if not drew_reference:
                        axis.plot(t, d["silicon_pad"], color=SILICON, lw=2.8,
                                  label="silicon (transistor)", zorder=5)
                        axis.plot(t, d["hspice_pad"], color=NATIVE, lw=1.8,
                                  label="HSPICE native IBIS", zorder=4)
                        axis.axvline(t_rev, color="0.5", ls="--", lw=1.0, zorder=1)
                        axis.set_xlim(edge_ns - 0.2, t_rev + 4.0)
                        drew_reference = True
                        drew_any = True
                    axis.plot(t, d["pybis_pad"], lw=1.4,
                              color=METHOD_COLORS.get(key, "#444444"),
                              label=key, zorder=3)
                axis.set_title(f"{device} {direction.replace('_', '-')} · "
                               f"{target}% swing · {width_ps:.0f} ps", fontsize=10)
                axis.set_ylabel("Pad (V)")
                axis.grid(alpha=0.25)
                if row == len(entries) - 1:
                    axis.set_xlabel("Time (ns)")
        if not drew_any:
            plt.close(fig)
            continue
        handles, labels = axes[0][0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=min(5, len(labels)),
                   fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.01))
        fig.suptitle(f"{device} — every method against silicon, mildest and harshest stress",
                     fontsize=12)
        fig.tight_layout(rect=(0, 0.04, 1, 0.97))
        path = out_dir / f"{device}_methods.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        written += 1
        print(f"wrote {path.relative_to(ROOT)}")

    if not written:
        print("no cases complete yet")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
