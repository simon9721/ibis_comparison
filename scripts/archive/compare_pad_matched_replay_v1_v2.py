#!/usr/bin/env python3
"""Compare cached V1 and V2 pad-matched replay evidence."""

from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

import matplotlib.pyplot as plt
import numpy as np


V1 = ROOT / "results" / "three_buffer_pad_matched_replay_2026-08-04" / "event_evidence"
V2 = ROOT / "results" / "three_buffer_pad_matched_replay_v2_2026-08-04" / "event_evidence"
OUT = V2.parent / "v1_vs_v2"
PAD_FLOWS = ("pad_voltage", "pad_slew")
METRICS = ("pad_rmse_mv_ratio", "ku_rmse_ratio", "kd_rmse_ratio")
GROUPS = tuple(
    (device, profile)
    for device in ("io_buf", "inv_chain", "ex2")
    for profile in ("slow_1ns", "fast_5ps")
)
COLORS = {"v1": "#CC6677", "v2": "#0072B2"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def number(row: dict[str, str], field: str) -> float:
    try:
        return float(row[field])
    except (KeyError, TypeError, ValueError):
        return float("nan")


def load_rows() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for version, directory in (("v1", V1), ("v2", V2)):
        for row in read_csv(directory / "case_outcomes.csv"):
            if row.get("flow") not in PAD_FLOWS:
                continue
            result.append({"version": version, **row})
    return result


def plot_long_controls(rows: list[dict[str, object]]) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(16.5, 9.0), sharex=True, constrained_layout=True)
    x = np.arange(len(GROUPS), dtype=float)
    width = 0.36
    for axis, flow in zip(axes, PAD_FLOWS):
        for offset, version in ((-width / 2, "v1"), (width / 2, "v2")):
            values = []
            for device, profile in GROUPS:
                selected = [
                    row for row in rows
                    if row["version"] == version and row["flow"] == flow
                    and row["case_id"] == "long_control"
                    and row["device"] == device and row["profile"] == profile
                ]
                if not selected:
                    values.append(np.nan)
                    continue
                ratios = [number(selected[0], metric) for metric in METRICS]
                values.append(max(ratios) if all(np.isfinite(ratios)) else np.nan)
            axis.bar(x + offset, values, width=width, color=COLORS[version], label=version.upper())
            for xpos, value in zip(x + offset, values):
                if not np.isfinite(value):
                    axis.text(xpos, 0.08, "numeric\nfail", color=COLORS[version],
                              ha="center", va="bottom", fontsize=9, fontweight="bold")
        axis.axhline(1.0, color="#111111", lw=1.5, ls="--")
        axis.set_ylabel("Worst pad/Ku/Kd\nerror ratio vs legacy")
        axis.set_title("Voltage only" if flow == "pad_voltage" else "Voltage + absolute slew", loc="left", fontweight="bold")
        axis.grid(axis="y", color="#D9DEE5", lw=0.8)
        axis.legend(frameon=False, ncol=2)
    axes[-1].set_xticks(x, [f"{d}\n{p}" for d, p in GROUPS])
    fig.suptitle("V2 restores the inactive legacy path on normal controls", fontsize=20, fontweight="bold")
    path = OUT / "plots" / "01_long_control_preservation_v1_v2.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def normalized_class(value: str) -> str:
    if value == "COEFFICIENT_AND_PAD_IMPROVED":
        return "all three improve"
    if value == "PAD_ONLY_FALSE_PASS":
        return "pad only"
    if value in {"PAD_MAPPING_AMBIGUOUS", "COEFFICIENT_ARTIFACT", "NUMERIC_FAIL"}:
        return "hard caveat"
    return "no clear improvement"


def plot_short_outcomes(rows: list[dict[str, object]]) -> Path:
    categories = ("all three improve", "pad only", "hard caveat", "no clear improvement")
    colors = ("#228833", "#EEAA33", "#CC3311", "#999999")
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.6))
    fig.subplots_adjust(left=0.06, right=0.98, bottom=0.11, top=0.80, wspace=0.09)
    for axis, direction in zip(axes, ("short_high", "short_low")):
        bottoms = np.zeros(2)
        for category, color in zip(categories, colors):
            values = []
            for version in ("v1", "v2"):
                selected = [
                    row for row in rows
                    if row["version"] == version
                    and str(row["case_id"]).startswith(direction)
                ]
                values.append(sum(normalized_class(str(row["classification"])) == category for row in selected))
            axis.bar((0, 1), values, bottom=bottoms, color=color, label=category)
            bottoms += np.asarray(values, dtype=float)
        axis.set_xticks((0, 1), ("V1", "V2"))
        axis.set_ylabel("Case/flow rows")
        axis.set_title(direction.replace("_", "-"), fontweight="bold")
        axis.grid(axis="y", color="#D9DEE5", lw=0.8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.89), ncol=4, frameon=False)
    fig.suptitle("Pad retiming remains direction-specific", y=0.97, fontsize=20, fontweight="bold")
    path = OUT / "plots" / "02_short_pulse_outcomes_v1_v2.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def write_report(rows: list[dict[str, object]], figures: list[Path]) -> None:
    lines = [
        "# Pad-Matched Replay V1 vs V2",
        "",
        "V1 continuously filtered the final legacy coefficients, even when replay was inactive. V2 replaces that with an exact inactive legacy bypass and uses held/replay values only during the reverse-edge transaction.",
        "",
        "## Counts",
        "",
    ]
    for version in ("v1", "v2"):
        for direction in ("short_high", "short_low"):
            selected = [
                row for row in rows
                if row["version"] == version and str(row["case_id"]).startswith(direction)
            ]
            good = sum(row["classification"] == "COEFFICIENT_AND_PAD_IMPROVED" for row in selected)
            material = sum(
                row["classification"] == "COEFFICIENT_AND_PAD_IMPROVED"
                and all(number(row, metric) < 0.95 for metric in METRICS)
                for row in selected
            )
            lines.append(
                f"- `{version}` `{direction}`: `{good}/{len(selected)}` rows improve all three numerically; "
                f"`{material}/{len(selected)}` improve all three by at least 5%."
            )
    lines += [
        "",
        "## Figures",
        "",
        *(f"- `{path.relative_to(V2.parent).as_posix()}`" for path in figures),
        "",
        "## Data",
        "",
        "- `v1_v2_case_outcomes.csv`",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not (V2 / "case_outcomes.csv").exists():
        raise FileNotFoundError("Run the V2 event-evidence analysis first")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    write_csv(OUT / "v1_v2_case_outcomes.csv", rows)
    figures = [plot_long_controls(rows), plot_short_outcomes(rows)]
    write_report(rows, figures)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
