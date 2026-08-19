#!/usr/bin/env python3
"""Build a compact cross-buffer value-match evidence figure from cached CSVs."""

from __future__ import annotations

import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


RESULT = ROOT / "results" / "inv_chain_ex2_value_matched_replay_2026-08-04"
CASES = (
    ("inv_chain", "fast_5ps", "short_pulse_50ps_high", "inv_chain | fast model | 50 ps high pulse", (4.85, 6.0)),
    ("ex2", "slow_1ns", "short_pulse_500ps_high", "ex2 | slow model | 500 ps high pulse", (4.75, 8.0)),
)

FLOW_STYLE = {
    "hspice": ("HSPICE native IBIS", "#111111", 4.0),
    "legacy": ("legacy pybis", "#777777", 2.2),
    "v2_balanced": ("value-match balanced", "#7a3db8", 2.2),
    "v2_split": ("value-match split Ku/Kd", "#d33f24", 2.0),
}


def read_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {key: np.asarray([float(row[key]) for row in rows]) for key in rows[0]}


def main() -> None:
    fig, axes = plt.subplots(3, 2, figsize=(18.0, 10.0), sharex="col")
    for column, (device, profile, case_id, title, limits) in enumerate(CASES):
        data = read_csv(RESULT / "waveform_data" / device / profile / f"{case_id}.csv")
        time = data["time_ns"]
        for row, (suffix, ylabel) in enumerate((("pad_v", "Pad voltage (V)"), ("ku", "Ku"), ("kd", "Kd"))):
            axis = axes[row, column]
            for flow_id, (label, color, width) in FLOW_STYLE.items():
                key = f"hspice_{'pad' if suffix == 'pad_v' else suffix}" if flow_id == "hspice" else f"{flow_id}_{suffix}"
                axis.plot(
                    time,
                    data[key],
                    color=color,
                    linewidth=width,
                    label=label,
                    zorder=6 if flow_id == "hspice" else 5 if flow_id == "v2_split" else 4,
                    marker="x" if flow_id == "v2_split" else None,
                    markevery=35 if flow_id == "v2_split" else None,
                    markersize=3.0,
                )
            axis.axvline(5.0, color="#888888", linestyle="--", linewidth=1.0)
            reverse = 5.05 if device == "inv_chain" else 5.5
            axis.axvline(reverse, color="#888888", linestyle="--", linewidth=1.0)
            axis.set_xlim(*limits)
            axis.grid(True, color="#d9dee5", linewidth=0.75)
            axis.spines[["top", "right"]].set_visible(False)
            if column == 0:
                axis.set_ylabel(ylabel)
        axes[0, column].set_title(title, fontsize=15, fontweight="bold")
        axes[2, column].set_xlabel("Time (ns)")
        axes[2, column].axhline(0.0, color="#999999", linewidth=0.8)

    handles = [Line2D([0], [0], color=color, lw=width, label=label) for label, color, width in FLOW_STYLE.values()]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.955))
    fig.suptitle("Value-matched replay: cross-buffer evidence", fontsize=19, fontweight="bold", y=0.995)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.88, bottom=0.08, wspace=0.15, hspace=0.12)
    output = RESULT / "plots" / "value_match_cross_buffer_evidence.png"
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
