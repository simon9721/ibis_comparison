#!/usr/bin/env python3
"""Summarize load portability of the three-buffer pad-matched replay baseline."""

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


STUDY = ROOT / "results" / "three_buffer_pad_matched_replay_load_portability_2026-08-04"
OUT = STUDY / "portability_evidence"
FLOWS = ("pad_voltage", "pad_slew")
CASES = ("long_control", "short_high_500ps", "short_low_500ps")
LOADS = tuple((r, c) for r in (25.0, 50.0, 100.0) for c in (0.0, 2.0, 10.0) if (r, c) != (50.0, 2.0))
METRICS = ("pad_rmse_mv", "ku_rmse", "kd_rmse")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_outcomes(metrics: list[dict[str, str]]) -> list[dict[str, object]]:
    lookup = {
        (row["device"], row["profile"], float(row["load_ohm"]), float(row["load_pf"]), row["case_id"], row["flow"]): row
        for row in metrics
    }
    result = []
    for device in ("io_buf", "inv_chain", "ex2"):
        for profile in ("slow_1ns", "fast_5ps"):
            for load in LOADS:
                for case in CASES:
                    legacy = lookup.get((device, profile, *load, case, "legacy"))
                    if legacy is None:
                        continue
                    for flow in FLOWS:
                        row = lookup.get((device, profile, *load, case, flow))
                        if row is None:
                            continue
                        ratios = {}
                        for metric in METRICS:
                            try:
                                denominator = float(legacy[metric])
                                ratios[f"{metric}_ratio"] = float(row[metric]) / denominator if denominator > 0 else float("nan")
                            except (KeyError, TypeError, ValueError):
                                ratios[f"{metric}_ratio"] = float("nan")
                        finite = [value for value in ratios.values() if np.isfinite(value)]
                        result.append({
                            "device": device,
                            "profile": profile,
                            "load_ohm": load[0],
                            "load_pf": load[1],
                            "case_id": case,
                            "flow": flow,
                            "status": row.get("status", ""),
                            "classification": row.get("classification", ""),
                            **ratios,
                            "worst_error_ratio": max(finite) if len(finite) == 3 else float("nan"),
                            "mapping_ambiguous": row.get("mapping_ambiguous", ""),
                            "native_envelope_ok": row.get("native_envelope_ok", ""),
                        })
    return result


def plot_case(outcomes: list[dict[str, object]], case_id: str, number: str) -> Path:
    row_order = [(device, profile) for device in ("io_buf", "inv_chain", "ex2") for profile in ("slow_1ns", "fast_5ps")]
    lookup = {
        (row["device"], row["profile"], float(row["load_ohm"]), float(row["load_pf"]), row["flow"]): row
        for row in outcomes if row["case_id"] == case_id
    }
    fig, axes = plt.subplots(2, 1, figsize=(15.5, 8.7), constrained_layout=True)
    for axis, flow in zip(axes, FLOWS):
        values = np.full((len(row_order), len(LOADS)), np.nan)
        for i, (device, profile) in enumerate(row_order):
            for j, load in enumerate(LOADS):
                row = lookup.get((device, profile, *load, flow))
                if row:
                    values[i, j] = float(row["worst_error_ratio"])
        image = axis.imshow(values, aspect="auto", cmap="RdYlGn_r", vmin=0.0, vmax=2.0)
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                axis.text(j, i, f"{values[i, j]:.2f}" if np.isfinite(values[i, j]) else "FAIL", ha="center", va="center", fontsize=8)
        axis.set_title(
            f"{'Voltage only' if flow == 'pad_voltage' else 'Voltage + slew'} | worst of pad/Ku/Kd error ratios",
            loc="left", fontweight="bold",
        )
        axis.set_yticks(range(len(row_order)), [f"{device} | {profile}" for device, profile in row_order])
        axis.set_xticks(range(len(LOADS)), [f"{r:g}R\n{c:g}pF" for r, c in LOADS])
        fig.colorbar(image, ax=axis, fraction=0.025, pad=0.015)
    fig.suptitle(f"Load portability | {case_id} | below 1 means all three metrics improve", fontsize=17, fontweight="bold")
    path = OUT / "plots" / f"{number}_{case_id}_worst_ratio.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def write_readme(outcomes: list[dict[str, object]], figures: list[Path]) -> None:
    short_low = [row for row in outcomes if row["case_id"] == "short_low_500ps"]
    short_high = [row for row in outcomes if row["case_id"] == "short_high_500ps"]
    passes_low = [row for row in short_low if row["classification"] == "COEFFICIENT_AND_PAD_IMPROVED"]
    passes_high = [row for row in short_high if row["classification"] == "COEFFICIENT_AND_PAD_IMPROVED"]
    lines = [
        "# Pad-Matched Replay Load Portability",
        "",
        "The replay map was calibrated only at `50 ohm || 2 pF`. These rows test eight other 25/50/100 ohm and 0/2/10 pF combinations.",
        "",
        "## Result",
        "",
        f"- 500 ps short-low all-three improvements: `{len(passes_low)}` of `{len(short_low)}` pad-flow rows.",
        f"- 500 ps short-high all-three improvements: `{len(passes_high)}` of `{len(short_high)}` pad-flow rows.",
        "- A heatmap value below one means pad, Ku, and Kd all beat legacy; the cell displays the worst of the three ratios.",
        "- Numeric failure, ambiguity, and envelope/discontinuity classification remain hard caveats even when a ratio is below one.",
        "",
        "## Figures",
        "",
    ]
    lines.extend(f"- `{path.relative_to(STUDY).as_posix()}`" for path in figures)
    lines += ["", "## Data", "", "- `load_case_outcomes.csv`", "- `../candidate_metrics.csv`"]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    metrics = read_csv(STUDY / "candidate_metrics.csv")
    outcomes = build_outcomes(metrics)
    write_csv(OUT / "load_case_outcomes.csv", outcomes)
    figures = [
        plot_case(outcomes, "short_low_500ps", "01"),
        plot_case(outcomes, "short_high_500ps", "02"),
        plot_case(outcomes, "long_control", "03"),
    ]
    write_readme(outcomes, figures)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
