#!/usr/bin/env python3
"""Build event-level evidence for the three-buffer pad-matched replay study."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
for path in (ROOT, ROOT / "scripts", ROOT / "tools" / "pybis2spice"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np

import run_three_buffer_pad_matched_replay as campaign


STUDY = ROOT / "results" / "three_buffer_pad_matched_replay_2026-08-04"
REPORT = STUDY / "event_evidence"
PAD_VERSION = "v1"
PAD_FLOWS = ("pad_voltage", "pad_slew")
METRICS = ("pad_rmse_mv", "ku_rmse", "kd_rmse")
METRIC_LABELS = ("Pad RMSE ratio", "Ku RMSE ratio", "Kd RMSE ratio")


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


def read_wave(path: Path) -> dict[str, np.ndarray]:
    rows = read_csv(path)
    if not rows:
        return {}
    return {
        field: np.asarray([float(row[field]) for row in rows], dtype=float)
        for field in rows[0]
    }


def as_float(row: dict[str, object], key: str) -> float:
    try:
        return float(row.get(key, float("nan")))
    except (TypeError, ValueError):
        return float("nan")


def cases() -> dict[str, object]:
    return {
        case.case_id: case
        for case in campaign.primary_cases() + campaign.load_cases()
    }


def rescore_cached_waveforms(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    devices = {device.device_id: device for device in campaign.base.DEVICES}
    case_map = cases()
    rescored: list[dict[str, object]] = []
    for row in rows:
        device = devices[row["device"]]
        case = case_map[row["case_id"]]
        load = (float(row["load_ohm"]), float(row["load_pf"]))
        wave_path = (
            STUDY / "waveform_data" / row["device"] / row["profile"]
            / campaign.load_tag(load) / f"{row['case_id']}.csv"
        )
        if not wave_path.exists():
            rescored.append(dict(row))
            continue
        data = read_wave(wave_path)
        flow = next(flow for flow in campaign.FLOWS if flow.flow_id == row["flow"])
        rescored.append(campaign.score(device, None, case, load, data, flow, dict(row)))
    campaign.classify(rescored)
    return rescored


def case_outcomes(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], dict[str, dict[str, object]]] = {}
    for row in rows:
        if float(row["load_ohm"]) != 50.0 or float(row["load_pf"]) != 2.0:
            continue
        key = (row["device"], row["profile"], row["case_id"], row["flow"])
        grouped[key] = {"row": row}

    result: list[dict[str, object]] = []
    for device in ("io_buf", "inv_chain", "ex2"):
        for profile in ("slow_1ns", "fast_5ps"):
            for case in campaign.primary_cases():
                baseline = grouped.get((device, profile, case.case_id, "legacy"), {}).get("row")
                if baseline is None:
                    continue
                for flow in PAD_FLOWS:
                    row = grouped.get((device, profile, case.case_id, flow), {}).get("row")
                    if row is None:
                        continue
                    outcome = row.get("classification", "CHECK")
                    ratios = {
                        f"{metric}_ratio": (
                            as_float(row, metric) / as_float(baseline, metric)
                            if as_float(baseline, metric) > 0 and np.isfinite(as_float(row, metric))
                            else float("nan")
                        )
                        for metric in METRICS
                    }
                    candidate_jump = max(
                        as_float(row, "reverse_ku_step"), as_float(row, "reverse_kd_step")
                    )
                    reference_jump = max(
                        as_float(row, "native_reverse_ku_step"),
                        as_float(row, "native_reverse_kd_step"),
                        as_float(baseline, "reverse_ku_step"),
                        as_float(baseline, "reverse_kd_step"),
                    )
                    result.append({
                        "device": device,
                        "profile": profile,
                        "case_id": case.case_id,
                        "flow": flow,
                        "status": row.get("status", ""),
                        "classification": outcome,
                        **ratios,
                        "pad_map_triggered": row.get("pad_map_triggered", ""),
                        "mapping_ambiguous": row.get("mapping_ambiguous", ""),
                        "event_start_span_ns": row.get("event_start_span_ns", ""),
                        "candidate_reverse_jump": candidate_jump,
                        "reference_reverse_jump": reference_jump,
                        "reverse_jump_excess": candidate_jump - reference_jump,
                        "native_envelope_ok": row.get("native_envelope_ok", ""),
                    })
    return result


def plot_error_ratios(outcomes: list[dict[str, object]]) -> Path:
    cases_order = [case.case_id for case in campaign.primary_cases() if case.pattern != "rise_fall"]
    rows_order = [
        (device, profile, flow)
        for device in ("io_buf", "inv_chain", "ex2")
        for profile in ("slow_1ns", "fast_5ps")
        for flow in PAD_FLOWS
    ]
    lookup = {
        (row["device"], row["profile"], row["flow"], row["case_id"]): row
        for row in outcomes
    }
    fig, axes = plt.subplots(3, 1, figsize=(17.5, 12.0), constrained_layout=True)
    cmap = plt.get_cmap("RdYlGn_r").copy()
    cmap.set_bad("#C8CDD3")
    for axis, metric, label in zip(axes, METRICS, METRIC_LABELS):
        values = np.full((len(rows_order), len(cases_order)), np.nan)
        for i, (device, profile, flow) in enumerate(rows_order):
            for j, case_id in enumerate(cases_order):
                row = lookup.get((device, profile, flow, case_id))
                if row:
                    values[i, j] = float(row[f"{metric}_ratio"])
        image = axis.imshow(values, aspect="auto", cmap=cmap, vmin=0.0, vmax=2.0)
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                if np.isfinite(values[i, j]):
                    axis.text(j, i, f"{values[i, j]:.2f}", ha="center", va="center", fontsize=7)
                else:
                    axis.text(j, i, "FAIL", ha="center", va="center", fontsize=7)
        axis.set_title(f"{label} (candidate / legacy; below 1 is improvement)", loc="left", fontweight="bold")
        axis.set_xticks(range(len(cases_order)), [item.replace("short_", "") for item in cases_order], rotation=25, ha="right")
        axis.set_yticks(
            range(len(rows_order)),
            [f"{device} | {profile} | {'V' if flow == 'pad_voltage' else 'V+slope'}" for device, profile, flow in rows_order],
        )
        fig.colorbar(image, ax=axis, fraction=0.02, pad=0.01)
    path = REPORT / "plots" / "01_error_ratio_heatmaps.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_outcome_matrix(outcomes: list[dict[str, object]]) -> Path:
    cases_order = [case.case_id for case in campaign.primary_cases() if case.pattern != "rise_fall"]
    rows_order = [
        (device, profile, flow)
        for device in ("io_buf", "inv_chain", "ex2")
        for profile in ("slow_1ns", "fast_5ps")
        for flow in PAD_FLOWS
    ]
    categories = [
        "COEFFICIENT_AND_PAD_IMPROVED", "NO_CLEAR_IMPROVEMENT",
        "PAD_ONLY_FALSE_PASS", "PAD_MAPPING_AMBIGUOUS",
        "COEFFICIENT_ARTIFACT", "NUMERIC_FAIL",
    ]
    labels = ["all improve", "mixed/no", "pad only", "ambiguous", "artifact", "numeric fail"]
    colors = ["#2E8B57", "#E6B84A", "#E67E22", "#7B2CBF", "#C73E1D", "#444444"]
    lookup = {
        (row["device"], row["profile"], row["flow"], row["case_id"]): row
        for row in outcomes
    }
    values = np.full((len(rows_order), len(cases_order)), len(categories) - 1, dtype=int)
    annotations = np.full(values.shape, "", dtype=object)
    for i, key in enumerate(rows_order):
        for j, case_id in enumerate(cases_order):
            row = lookup.get((*key, case_id))
            if row:
                category = row["classification"]
                values[i, j] = categories.index(category) if category in categories else 1
                annotations[i, j] = labels[values[i, j]]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(-0.5, len(colors) + 0.5), cmap.N)
    fig, axis = plt.subplots(figsize=(17.5, 7.0), constrained_layout=True)
    image = axis.imshow(values, aspect="auto", cmap=cmap, norm=norm)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            axis.text(j, i, annotations[i, j], ha="center", va="center", fontsize=7, color="white" if values[i, j] >= 3 else "#111111")
    axis.set_title("Pad-matched replay outcomes at 50 ohm || 2 pF", loc="left", fontweight="bold")
    axis.set_xticks(range(len(cases_order)), [item.replace("short_", "") for item in cases_order], rotation=25, ha="right")
    axis.set_yticks(
        range(len(rows_order)),
        [f"{device} | {profile} | {'V' if flow == 'pad_voltage' else 'V+slope'}" for device, profile, flow in rows_order],
    )
    colorbar = fig.colorbar(image, ax=axis, ticks=range(len(labels)), fraction=0.03, pad=0.02)
    colorbar.ax.set_yticklabels(labels)
    path = REPORT / "plots" / "02_outcome_matrix.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_jump_excess(outcomes: list[dict[str, object]]) -> Path:
    selected = [row for row in outcomes if row["case_id"] != "long_control"]
    groups = [
        (device, profile, flow)
        for device in ("io_buf", "inv_chain", "ex2")
        for profile in ("slow_1ns", "fast_5ps")
        for flow in PAD_FLOWS
    ]
    medians = []
    maxima = []
    for group in groups:
        values = [float(row["reverse_jump_excess"]) for row in selected if (row["device"], row["profile"], row["flow"]) == group and np.isfinite(float(row["reverse_jump_excess"]))]
        medians.append(float(np.median(values)) if values else np.nan)
        maxima.append(float(np.max(values)) if values else np.nan)
    x = np.arange(len(groups))
    fig, axis = plt.subplots(figsize=(17.0, 6.3), constrained_layout=True)
    axis.bar(x - 0.18, medians, width=0.36, color="#0072B2", label="median")
    axis.bar(x + 0.18, maxima, width=0.36, color="#CC3311", label="worst case")
    axis.axhline(0.2, color="#111111", lw=1.5, ls="--", label="artifact margin")
    axis.axhline(0.0, color="#777777", lw=1.0)
    axis.set_ylabel("Candidate reversal jump minus max(native, legacy)")
    axis.set_xticks(x, [f"{d}\n{p}\n{'V' if f == 'pad_voltage' else 'V+slope'}" for d, p, f in groups], rotation=20, ha="right")
    axis.set_title("Additional Ku/Kd discontinuity introduced at reversal", loc="left", fontweight="bold")
    axis.grid(axis="y", color="#D9DEE5", lw=0.8)
    axis.legend(frameon=False, ncol=3)
    path = REPORT / "plots" / "03_reversal_jump_excess.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def write_readme(outcomes: list[dict[str, object]], figures: list[Path]) -> None:
    short = [row for row in outcomes if row["case_id"] != "long_control"]
    counts: dict[str, int] = {}
    for row in short:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    triggered = sum(str(row["pad_map_triggered"]).lower() == "true" for row in short)
    ambiguous = sum(str(row["mapping_ambiguous"]).lower() == "true" for row in short)
    all_improved = [
        row for row in short
        if row["classification"] == "COEFFICIENT_AND_PAD_IMPROVED"
    ]
    material_improved = [
        row for row in all_improved
        if all(float(row[f"{metric}_ratio"]) < 0.95 for metric in METRICS)
    ]
    numeric_high = sum(str(row["case_id"]).startswith("short_high") for row in all_improved)
    numeric_low = sum(str(row["case_id"]).startswith("short_low") for row in all_improved)
    material_high = sum(str(row["case_id"]).startswith("short_high") for row in material_improved)
    material_low = sum(str(row["case_id"]).startswith("short_low") for row in material_improved)
    controls = [row for row in outcomes if row["case_id"] == "long_control"]
    control_numeric_failures = sum(row["classification"] == "NUMERIC_FAIL" for row in controls)
    control_worst_ratios = [
        max(as_float(row, f"{metric}_ratio") for metric in METRICS)
        for row in controls
        if all(np.isfinite(as_float(row, f"{metric}_ratio")) for metric in METRICS)
    ]
    control_median = float(np.median(control_worst_ratios)) if control_worst_ratios else float("nan")
    control_max = float(np.max(control_worst_ratios)) if control_worst_ratios else float("nan")
    lines = [
        "# Pad-Matched Replay Event Evidence",
        "",
        "This report rescored cached waveforms only. No HSPICE or ngspice simulation was run by this analysis step.",
        "",
        "## Finding",
        "",
        "- Sampling pad voltage at reversal is not a sufficient internal-state coordinate across these three buffers.",
        "- The corrected crossing-based inverse exposes repeated pad values at widely separated trajectory times; adding absolute pad slew does not consistently make that mapping unique.",
        f"- The pad-matched variants improve pad, Ku, and Kd numerically in `{len(all_improved)}` short-pulse rows (`{numeric_high}` short-high, `{numeric_low}` short-low).",
        f"- `{len(material_improved)}` rows improve all three by at least 5% (`{material_high}` short-high, `{material_low}` short-low). Thus no short-high result is a material all-three improvement.",
        "- Several pad waveforms improve while one coefficient does not. Those are pad-only false passes, not model success.",
        "- The short-low result is real directional progress, especially for ex2 at 250 ps and 500 ps. It does not establish a general retrigger model because short-high remains open.",
        f"- Long-control audit for `{PAD_VERSION}`: `{control_numeric_failures}` numeric failures; median/worst of the per-row worst pad/Ku/Kd error ratio is `{control_median:.3f}` / `{control_max:.3f}`.",
        "",
        "## Counts",
        "",
        f"- Short-pulse pad-flow rows: `{len(short)}`",
        f"- Triggered rows: `{triggered}`",
        f"- Mapping-ambiguous rows: `{ambiguous}`",
    ]
    for key in sorted(counts):
        lines.append(f"- `{key}`: `{counts[key]}`")
    lines += ["", "## Figures", ""]
    lines.extend(f"- `{path.relative_to(STUDY).as_posix()}`" for path in figures)
    lines += [
        "", "## Data", "",
        "- `case_outcomes.csv`: per-case error ratios, trigger/ambiguity state, envelope result, and reversal-jump excess.",
        "- `candidate_metrics_rescored.csv`: corrected event-local metrics for every nominal campaign flow.",
        "",
        "## Interpretation",
        "",
        "A Ku/Kd value outside [0,1] is not automatically wrong. The rejection rule used here is whether the candidate exceeds the native-IBIS envelope or adds a reversal discontinuity beyond both native IBIS and legacy pybis. This avoids clipping legitimate extracted-coefficient overshoot while still detecting algorithm-created spikes.",
    ]
    (REPORT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=STUDY)
    parser.add_argument("--pad-version", choices=("v1", "v2"), default="v1")
    return parser.parse_args()


def main() -> int:
    global STUDY, REPORT, PAD_VERSION
    args = parse_args()
    STUDY = args.study_dir if args.study_dir.is_absolute() else ROOT / args.study_dir
    STUDY = STUDY.resolve()
    REPORT = STUDY / "event_evidence"
    PAD_VERSION = args.pad_version
    campaign.FLOWS = campaign.V2_FLOWS if PAD_VERSION == "v2" else campaign.V1_FLOWS
    campaign.PAD_FLOWS = tuple(flow.flow_id for flow in campaign.FLOWS if flow.pad_reference)
    REPORT.mkdir(parents=True, exist_ok=True)
    original = read_csv(STUDY / "candidate_metrics.csv")
    rescored = rescore_cached_waveforms(original)
    write_csv(REPORT / "candidate_metrics_rescored.csv", rescored)
    outcomes = case_outcomes(rescored)
    write_csv(REPORT / "case_outcomes.csv", outcomes)
    figures = [
        plot_error_ratios(outcomes),
        plot_outcome_matrix(outcomes),
        plot_jump_excess(outcomes),
    ]
    write_readme(outcomes, figures)
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
