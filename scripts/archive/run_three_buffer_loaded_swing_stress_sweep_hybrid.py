#!/usr/bin/env python3
"""Add the dual-residual hybrid to the cached loaded-swing stress sweep."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
for path in (LOCAL_DEPS, ROOT, ROOT / "scripts", ROOT / "tools" / "pybis2spice"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis
from spice_tool_paths import default_ngspice
import run_three_buffer_loaded_swing_stress_sweep as original
import run_three_buffer_realistic_pulse_campaign as base


DEFAULT_BASELINE = ROOT / "results" / "three_buffer_loaded_swing_stress_sweep_2026-08-14"
DEFAULT_OUT = ROOT / "results" / "three_buffer_loaded_swing_stress_sweep_hybrid_2026-08-18"
HYBRID_MODE = "InputDrivenTwoStateGateDirectionalDualResidualHybrid"

BLACK = "#111111"
GRAY = "#777777"
RED = "#D62728"
PURPLE = "#6F2DBD"
EDGE = "#8B8B8B"
GRID = "#D9DEE5"


def hybrid_display_label(mode: str) -> str:
    if mode == "InputDrivenHybridV3AlignedReplay":
        return "Hybrid V3 aligned replay (new)"
    if mode == "InputDrivenTwoStateGateDirectionalDualResidualHybrid":
        return "Previous hybrid (gate-state on reversal)"
    return mode


def ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


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
    ensure(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_waveform(path: Path) -> dict[str, np.ndarray]:
    rows = read_csv(path)
    if not rows:
        raise ValueError(f"empty waveform: {path}")
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def write_waveform(path: Path, data: dict[str, np.ndarray]) -> None:
    write_csv(
        path,
        [
            {key: float(values[index]) for key, values in data.items()}
            for index in range(len(data["time_ns"]))
        ],
    )


def device_by_id(device_id: str) -> base.Device:
    return next(device for device in base.DEVICES if device.device_id == device_id)


def make_case(row: dict[str, str]) -> base.PulseCase:
    direction = row["direction"]
    target = int(round(float(row["target_percent"])))
    width_ns = float(row["pulse_width_ps"]) / 1000.0
    return base.PulseCase(
        f"{direction}_swing{target}",
        original.EDGE_NS,
        direction,
        width_ns,
        22.0,
        f"{target}% loaded-output reversal",
        target / 100.0,
    )


def prepare_models(
    baseline: Path,
    out: Path,
    device: base.Device,
    profile: base.Profile,
    hybrid_mode: str = HYBRID_MODE,
) -> tuple[Path, Path]:
    gate_source = (
        baseline
        / "generated_models"
        / device.device_id
        / profile.profile_id
        / "gate_state"
        / f"{device.subckt}.sub"
    )
    gate_copy = (
        out
        / "generated_models"
        / device.device_id
        / profile.profile_id
        / "gate_state"
        / f"{device.subckt}.sub"
    )
    ensure(gate_copy.parent)
    if not gate_copy.exists():
        shutil.copy2(gate_source, gate_copy)

    hybrid = (
        out
        / "generated_models"
        / device.device_id
        / profile.profile_id
        / "hybrid"
        / f"{device.subckt}.sub"
    )
    if not hybrid.exists():
        convert_ibis_to_pybis(
            profile.ibis,
            hybrid,
            device.component,
            device.model,
            "Output",
            hybrid_mode,
            "Typical",
        )
    return gate_copy, hybrid


def interp(source: dict[str, np.ndarray], target_time: np.ndarray, key: str) -> np.ndarray:
    return np.interp(target_time, source["time_ns"], source[key])


def add_hybrid(
    baseline: dict[str, np.ndarray],
    hybrid: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    result = dict(baseline)
    target_time = baseline["time_ns"]
    for key in ("pad_v", "ku", "kd"):
        result[f"hybrid_{key}"] = interp(hybrid, target_time, key)
    for key in (
        "gup",
        "gdn",
        "guptarget",
        "gdntarget",
        "kugate",
        "kdgate",
        "kuleg",
        "kdleg",
        "kutarget",
        "kdtarget",
        "hfall_after_rise",
        "hrise_after_fall",
        "hreverseraw",
        "hsettled",
        "hhybridactive",
        "kures",
        "kdres",
        "guprate",
        "gdnrate",
        "v3revedge",
        "v3activate",
        "v3sample",
        "v3kuvissamp",
        "v3kdvissamp",
        "v3kugatesamp",
        "v3kdgatesamp",
        "v3alignerrku",
        "v3alignerrkd",
        "v3gatealigned",
        "v3kuanchor",
        "v3kdanchor",
        "v3dir",
        "v3trku",
        "v3trkd",
        "v3tfku",
        "v3tfkd",
        "v3kustart",
        "v3kdstart",
        "v3t0",
        "v3elapsed",
        "v3kuarg",
        "v3kdarg",
        "v3kuprogress",
        "v3kdprogress",
        "v3kureplay",
        "v3kdreplay",
        "v3enderrku",
        "v3enderrkd",
        "v3done",
        "hv3active",
        "hv3pending",
        "v3prehold",
    ):
        if key in hybrid:
            result[f"hybrid_{key}"] = interp(hybrid, target_time, key)
    return result


def mask_between(time_ns: np.ndarray, start_ns: float, stop_ns: float) -> np.ndarray:
    return (time_ns >= start_ns) & (time_ns <= stop_ns)


def rmse(reference: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> float:
    if not np.any(mask):
        return float("nan")
    return float(np.sqrt(np.mean(np.square(candidate[mask] - reference[mask]))))


def max_error(reference: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> tuple[float, int]:
    indexes = np.flatnonzero(mask)
    if len(indexes) == 0:
        return float("nan"), 0
    local = np.abs(candidate[indexes] - reference[indexes])
    position = int(indexes[int(np.argmax(local))])
    return float(local.max()), position


def active_intervals(time_ns: np.ndarray, values: np.ndarray) -> list[tuple[float, float]]:
    active = values > 0.5
    starts = np.flatnonzero(active & np.r_[True, ~active[:-1]])
    stops = np.flatnonzero(active & np.r_[~active[1:], True])
    return [(float(time_ns[left]), float(time_ns[right])) for left, right in zip(starts, stops)]


def coefficient_diagnostic_rows(
    selection: dict[str, str],
    device: base.Device,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    time_ns = data["time_ns"]
    stress_ns, reverse_ns = base.command_edges(device, case)[-2:]
    crop_start = float(selection["crop_start_ns"])
    crop_stop = float(selection["crop_stop_ns"])
    masks = {
        "active": mask_between(time_ns, crop_start, crop_stop),
        "before_reverse": mask_between(time_ns, stress_ns, reverse_ns),
        "after_reverse": mask_between(time_ns, reverse_ns, crop_stop),
    }
    rows: list[dict[str, object]] = []
    for flow, prefix in (("gate_state", "gate_state"), ("hybrid", "hybrid")):
        row: dict[str, object] = {
            "device": device.device_id,
            "direction": selection["direction"],
            "target_percent": float(selection["target_percent"]),
            "pulse_width_ps": float(selection["pulse_width_ps"]),
            "flow": flow,
            "stress_edge_ns": stress_ns,
            "reverse_edge_ns": reverse_ns,
            "crop_start_ns": crop_start,
            "crop_stop_ns": crop_stop,
        }
        total_sse = 0.0
        post_sse = 0.0
        for coefficient in ("ku", "kd"):
            reference = data[f"hspice_native_{coefficient}"]
            candidate = data[f"{prefix}_{coefficient}"]
            for phase, mask in masks.items():
                row[f"{coefficient}_{phase}_rmse"] = rmse(reference, candidate, mask)
            error, index = max_error(reference, candidate, masks["active"])
            row[f"{coefficient}_max_error"] = error
            row[f"{coefficient}_max_error_time_ns"] = float(time_ns[index])
            row[f"{coefficient}_native_at_reverse"] = float(np.interp(reverse_ns, time_ns, reference))
            row[f"{coefficient}_model_at_reverse"] = float(np.interp(reverse_ns, time_ns, candidate))
            row[f"{coefficient}_native_min"] = float(np.min(reference[masks["active"]]))
            row[f"{coefficient}_native_max"] = float(np.max(reference[masks["active"]]))
            row[f"{coefficient}_model_min"] = float(np.min(candidate[masks["active"]]))
            row[f"{coefficient}_model_max"] = float(np.max(candidate[masks["active"]]))
            row[f"{coefficient}_max_step"] = float(np.max(np.abs(np.diff(candidate[masks["active"]]))))
            active_error = candidate[masks["active"]] - reference[masks["active"]]
            post_error = candidate[masks["after_reverse"]] - reference[masks["after_reverse"]]
            total_sse += float(np.sum(np.square(active_error)))
            post_sse += float(np.sum(np.square(post_error)))
        pre_mean = 0.5 * (
            float(row["ku_before_reverse_rmse"]) + float(row["kd_before_reverse_rmse"])
        )
        post_mean = 0.5 * (
            float(row["ku_after_reverse_rmse"]) + float(row["kd_after_reverse_rmse"])
        )
        if max(pre_mean, post_mean) < 0.08:
            mechanism = "LOW_COEFFICIENT_ERROR"
        elif pre_mean >= 0.15 and post_mean >= 0.15:
            mechanism = "BASE_AND_RECOVERY_MISMATCH"
        elif post_mean > max(0.10, 1.5 * pre_mean):
            mechanism = "REVERSAL_RECOVERY_DOMINATED"
        elif pre_mean >= 0.15:
            mechanism = "BASE_TRANSITION_DOMINATED"
        else:
            mechanism = "MIXED_COEFFICIENT_MISMATCH"
        row["coefficient_error_mechanism"] = mechanism
        row["post_reverse_sse_fraction"] = post_sse / total_sse if total_sse else 0.0
        if flow == "hybrid" and "hybrid_hhybridactive" in data:
            active_values = data["hybrid_hhybridactive"]
            active = active_values > 0.5
            intervals = active_intervals(time_ns, active_values)
            row["hybrid_active"] = bool(intervals)
            row["hybrid_active_interval_count"] = len(intervals)
            row["hybrid_active_duration_ns"] = sum(stop - start for start, stop in intervals)
            row["hybrid_active_intervals_ns"] = ";".join(
                f"{start:.6f}:{stop:.6f}" for start, stop in intervals
            )
            starts = np.flatnonzero(active & np.r_[True, ~active[:-1]])
            stops = np.flatnonzero(active & np.r_[~active[1:], True])
            for coefficient in ("ku", "kd"):
                final = data[f"hybrid_{coefficient}"]
                legacy = data.get(f"hybrid_{coefficient}leg")
                gate = data.get(f"hybrid_{coefficient}gate")
                entry_jumps = [abs(float(final[index] - final[max(index - 1, 0)])) for index in starts]
                exit_jumps = [
                    abs(float(final[min(index + 1, len(final) - 1)] - final[index]))
                    for index in stops
                ]
                row[f"hybrid_{coefficient}_entry_jump"] = max(entry_jumps, default=0.0)
                row[f"hybrid_{coefficient}_exit_jump"] = max(exit_jumps, default=0.0)
                if legacy is not None and gate is not None:
                    row[f"hybrid_{coefficient}_entry_source_gap"] = max(
                        (abs(float(gate[index] - legacy[index])) for index in starts),
                        default=0.0,
                    )
                    row[f"hybrid_{coefficient}_exit_source_gap"] = max(
                        (abs(float(gate[index] - legacy[index])) for index in stops),
                        default=0.0,
                    )
            worst_switch_jump = max(
                float(row.get("hybrid_ku_entry_jump", 0.0)),
                float(row.get("hybrid_ku_exit_jump", 0.0)),
                float(row.get("hybrid_kd_entry_jump", 0.0)),
                float(row.get("hybrid_kd_exit_jump", 0.0)),
            )
            row["hybrid_switch_discontinuity"] = worst_switch_jump > 0.10
        rows.append(row)
    return rows


def v3_structural_row(
    selection: dict[str, str],
    data: dict[str, np.ndarray],
) -> dict[str, object] | None:
    """Summarize the V3 latch, timer, and replay handoff independently of accuracy."""
    required = {
        "hybrid_hv3active",
        "hybrid_v3elapsed",
        "hybrid_v3kuarg",
        "hybrid_v3kdarg",
        "hybrid_v3kuanchor",
        "hybrid_v3kdanchor",
    }
    if not required.issubset(data):
        return None
    time_ns = data["time_ns"]
    active = data["hybrid_hv3active"] > 0.5
    starts = np.flatnonzero(active & np.r_[True, ~active[:-1]])
    stops = np.flatnonzero(active & np.r_[~active[1:], True])
    active_indexes = np.flatnonzero(active)

    def max_backstep(key: str) -> float:
        if len(active_indexes) < 2:
            return 0.0
        values = data[key][active_indexes]
        return float(max(0.0, -float(np.min(np.diff(values)))))

    if len(starts):
        first = int(starts[0])
        before = max(first - 1, 0)
        ku_entry_jump = abs(float(data["hybrid_ku"][first] - data["hybrid_ku"][before]))
        kd_entry_jump = abs(float(data["hybrid_kd"][first] - data["hybrid_kd"][before]))
        ku_anchor_error = abs(float(data["hybrid_ku"][first] - data["hybrid_v3kuanchor"][first]))
        kd_anchor_error = abs(float(data["hybrid_kd"][first] - data["hybrid_v3kdanchor"][first]))
        gate_aligned = bool(data.get("hybrid_v3gatealigned", np.zeros_like(time_ns))[first] > 0.5)
        ku_start_ns = float(data.get("hybrid_v3kustart", np.zeros_like(time_ns))[first])
        kd_start_ns = float(data.get("hybrid_v3kdstart", np.zeros_like(time_ns))[first])
    else:
        ku_entry_jump = kd_entry_jump = ku_anchor_error = kd_anchor_error = float("nan")
        gate_aligned = False
        ku_start_ns = kd_start_ns = float("nan")

    finite = all(np.all(np.isfinite(data[key])) for key in required | {"hybrid_ku", "hybrid_kd"})
    if len(active_indexes):
        ku_active_min = float(np.min(data["hybrid_ku"][active_indexes]))
        ku_active_max = float(np.max(data["hybrid_ku"][active_indexes]))
        kd_active_min = float(np.min(data["hybrid_kd"][active_indexes]))
        kd_active_max = float(np.max(data["hybrid_kd"][active_indexes]))
    else:
        ku_active_min = ku_active_max = kd_active_min = kd_active_max = float("nan")
    coefficient_range_ok = (
        len(active_indexes) > 0
        and ku_active_min >= -0.2
        and ku_active_max <= 1.2
        and kd_active_min >= -0.2
        and kd_active_max <= 1.2
    )
    elapsed_backstep = max_backstep("hybrid_v3elapsed")
    kuarg_backstep = max_backstep("hybrid_v3kuarg")
    kdarg_backstep = max_backstep("hybrid_v3kdarg")
    handoff_ok = (
        len(starts) == 1
        and ku_entry_jump <= 0.02
        and kd_entry_jump <= 0.02
        and ku_anchor_error <= 0.02
        and kd_anchor_error <= 0.02
        and elapsed_backstep <= 1e-6
        and kuarg_backstep <= 1e-6
        and kdarg_backstep <= 1e-6
    )
    return {
        "device": selection["device"],
        "direction": selection["direction"],
        "target_percent": float(selection["target_percent"]),
        "active_interval_count": len(starts),
        "active_start_ns": float(time_ns[starts[0]]) if len(starts) else float("nan"),
        "active_end_ns": float(time_ns[stops[-1]]) if len(stops) else float("nan"),
        "ku_entry_jump": ku_entry_jump,
        "kd_entry_jump": kd_entry_jump,
        "ku_anchor_error": ku_anchor_error,
        "kd_anchor_error": kd_anchor_error,
        "ku_start_ns": ku_start_ns,
        "kd_start_ns": kd_start_ns,
        "start_disagreement_ns": abs(ku_start_ns - kd_start_ns),
        "gate_anchor_accepted": gate_aligned,
        "max_elapsed_backstep_ns": elapsed_backstep,
        "max_kuarg_backstep_ns": kuarg_backstep,
        "max_kdarg_backstep_ns": kdarg_backstep,
        "ku_active_min": ku_active_min,
        "ku_active_max": ku_active_max,
        "kd_active_min": kd_active_min,
        "kd_active_max": kd_active_max,
        "coefficient_range_ok": coefficient_range_ok,
        "finite": finite,
        "handoff_status": "PASS" if handoff_ok and finite else "FAIL",
        "structural_status": "PASS" if handoff_ok and finite and coefficient_range_ok else "FAIL",
    }


def comparison_metric_rows(
    selection: dict[str, str],
    data: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    time_ns = data["time_ns"]
    mask = mask_between(time_ns, float(selection["crop_start_ns"]), float(selection["crop_stop_ns"]))
    rows: list[dict[str, object]] = []
    for flow, prefix in (("gate_state", "gate_state"), ("hybrid", "hybrid")):
        row: dict[str, object] = {
            "device": selection["device"],
            "direction": selection["direction"],
            "target_percent": float(selection["target_percent"]),
            "pulse_width_ps": float(selection["pulse_width_ps"]),
            "flow": flow,
        }
        for signal, scale in (("pad_v", 1000.0), ("ku", 1.0), ("kd", 1.0)):
            reference_key = "hspice_native_pad_v" if signal == "pad_v" else f"hspice_native_{signal}"
            candidate_key = f"{prefix}_{signal}"
            error, index = max_error(data[reference_key], data[candidate_key], mask)
            suffix = "mv" if signal == "pad_v" else ""
            row[f"{signal}_rmse_{suffix}".rstrip("_")] = scale * rmse(
                data[reference_key], data[candidate_key], mask
            )
            row[f"{signal}_max_error_{suffix}".rstrip("_")] = scale * error
            row[f"{signal}_max_error_time_ns"] = float(time_ns[index])
        rows.append(row)
    return rows


def style_axis(axis: plt.Axes) -> None:
    axis.grid(True, color=GRID, linewidth=0.8)
    axis.spines[["top", "right"]].set_visible(False)


def outlined(line: plt.Line2D, width: float = 4.2) -> None:
    line.set_path_effects(
        [path_effects.Stroke(linewidth=width, foreground="white"), path_effects.Normal()]
    )


def plot_pad(
    output: Path,
    device: base.Device,
    selection: dict[str, str],
    case: base.PulseCase,
    data: dict[str, np.ndarray],
    hybrid_label: str,
) -> None:
    start = float(selection["crop_start_ns"])
    stop = float(selection["crop_stop_ns"])
    mask = mask_between(data["time_ns"], start, stop)
    time_ns = data["time_ns"][mask]
    reverse_ns = base.command_edges(device, case)[-1]
    figure, axis = plt.subplots(figsize=(14.2, 6.0), constrained_layout=True)
    axis.plot(time_ns, data["hspice_transistor_pad_v"][mask], color=GRAY, linewidth=4.8,
              label="HSPICE transistor", zorder=1)
    axis.plot(time_ns, data["hspice_native_pad_v"][mask], color=BLACK, linewidth=3.7,
              label="HSPICE native IBIS", zorder=2)
    gate_line, = axis.plot(time_ns, data["gate_state_pad_v"][mask], color=RED, linewidth=2.2,
                           label="gate-state model", zorder=3)
    hybrid_line, = axis.plot(time_ns, data["hybrid_pad_v"][mask], color=PURPLE, linewidth=2.2,
                             label=hybrid_label, zorder=4)
    outlined(gate_line)
    outlined(hybrid_line)
    axis.axvline(reverse_ns, color=EDGE, linewidth=1.3, linestyle="--", label="reverse edge")
    axis.set_title(
        f"{device.device_id} | {selection['direction'].replace('_', ' ')} | "
        f"target {float(selection['target_percent']):.0f}%",
        fontsize=16,
        fontweight="bold",
    )
    axis.set_xlabel("Time (ns)")
    axis.set_ylabel("Pad voltage (V)")
    axis.legend(loc="best", frameon=False, ncol=2)
    style_axis(axis)
    ensure(output.parent)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def plot_coefficients(
    output: Path,
    device: base.Device,
    selection: dict[str, str],
    case: base.PulseCase,
    data: dict[str, np.ndarray],
    hybrid_label: str,
) -> None:
    start = float(selection["crop_start_ns"])
    stop = float(selection["crop_stop_ns"])
    mask = mask_between(data["time_ns"], start, stop)
    time_ns = data["time_ns"][mask]
    reverse_ns = base.command_edges(device, case)[-1]
    figure, axes = plt.subplots(2, 1, figsize=(14.2, 8.4), sharex=True, constrained_layout=True)
    for axis, coefficient, ylabel in ((axes[0], "ku", "Ku"), (axes[1], "kd", "Kd")):
        axis.plot(time_ns, data[f"hspice_native_{coefficient}"][mask], color=BLACK,
                  linewidth=4.0, label="HSPICE native IBIS", zorder=2)
        gate_line, = axis.plot(time_ns, data[f"gate_state_{coefficient}"][mask], color=RED,
                               linewidth=2.2, label="gate-state model", zorder=3)
        hybrid_line, = axis.plot(time_ns, data[f"hybrid_{coefficient}"][mask], color=PURPLE,
                                 linewidth=2.2, label=hybrid_label, zorder=4)
        outlined(gate_line)
        outlined(hybrid_line)
        axis.axvline(reverse_ns, color=EDGE, linewidth=1.3, linestyle="--")
        axis.axhline(0.0, color="#B7BBC1", linewidth=0.9)
        axis.set_ylabel(ylabel)
        style_axis(axis)
    axes[1].set_xlabel("Time (ns)")
    axes[0].legend(loc="best", frameon=False, ncol=3)
    figure.suptitle(
        f"{device.device_id} | {selection['direction'].replace('_', ' ')} | "
        f"target {float(selection['target_percent']):.0f}%",
        fontsize=16,
        fontweight="bold",
    )
    ensure(output.parent)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def correlation(x: list[float], y: list[float]) -> float:
    if len(x) < 2 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return float("nan")
    return float(np.corrcoef(np.asarray(x), np.asarray(y))[0, 1])


def aggregate_rows(
    metrics: list[dict[str, object]], diagnostics: list[dict[str, object]]
) -> list[dict[str, object]]:
    diagnostic_lookup = {
        (row["device"], row["direction"], row["target_percent"], row["flow"]): row
        for row in diagnostics
    }
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in metrics:
        groups.setdefault((str(row["device"]), str(row["direction"]), str(row["flow"])), []).append(row)
    result: list[dict[str, object]] = []
    for (device, direction, flow), rows in sorted(groups.items()):
        rows.sort(key=lambda item: -float(item["target_percent"]))
        severity = [100.0 - float(row["target_percent"]) for row in rows]
        ku = [float(row["ku_rmse"]) for row in rows]
        kd = [float(row["kd_rmse"]) for row in rows]
        pad = [float(row["pad_v_rmse_mv"]) for row in rows]
        diag = [
            diagnostic_lookup[(row["device"], row["direction"], row["target_percent"], row["flow"])]
            for row in rows
        ]
        result.append({
            "device": device,
            "direction": direction,
            "flow": flow,
            "mean_pad_rmse_mv": float(np.mean(pad)),
            "mean_ku_rmse": float(np.mean(ku)),
            "mean_kd_rmse": float(np.mean(kd)),
            "stress_vs_pad_rmse_correlation": correlation(severity, pad),
            "stress_vs_ku_rmse_correlation": correlation(severity, ku),
            "stress_vs_kd_rmse_correlation": correlation(severity, kd),
            "mean_post_reverse_sse_fraction": float(np.mean([float(item["post_reverse_sse_fraction"]) for item in diag])),
            "dominant_mechanisms": ";".join(sorted({str(item["coefficient_error_mechanism"]) for item in diag})),
            "hybrid_triggered_cases": sum(bool(item.get("hybrid_active", False)) for item in diag),
            "case_count": len(rows),
        })
    return result


def plot_rmse_trends(out: Path, metrics: list[dict[str, object]]) -> None:
    styles = {
        ("short_high", "gate_state"): (RED, "o", "short-high gate-state"),
        ("short_high", "hybrid"): (PURPLE, "s", "short-high hybrid"),
        ("short_low", "gate_state"): ("#D97706", "^", "short-low gate-state"),
        ("short_low", "hybrid"): ("#1769AA", "D", "short-low hybrid"),
    }
    figure, axes = plt.subplots(2, 3, figsize=(17.5, 10.0), sharex=True)
    for column, device in enumerate(item.device_id for item in base.DEVICES):
        for row_index, (metric, ylabel) in enumerate((("ku_rmse", "Ku RMSE"), ("kd_rmse", "Kd RMSE"))):
            axis = axes[row_index, column]
            for (direction, flow), (color, marker, label) in styles.items():
                rows = [
                    item for item in metrics
                    if item["device"] == device and item["direction"] == direction and item["flow"] == flow
                ]
                rows.sort(key=lambda item: -float(item["target_percent"]))
                axis.plot(
                    [float(item["target_percent"]) for item in rows],
                    [float(item[metric]) for item in rows],
                    color=color,
                    marker=marker,
                    linewidth=2.2,
                    markersize=6,
                    label=label,
                )
            axis.set_ylabel(ylabel)
            axis.set_title(device, fontweight="bold")
            style_axis(axis)
        axes[1, column].set_xlabel("Transistor loaded-swing target at reversal (%)")
    for axis in axes.flat:
        axis.set_xlim(92, 48)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=4, frameon=False)
    figure.suptitle("Ku/Kd agreement versus reversal stress", fontsize=17, fontweight="bold", y=0.98)
    figure.subplots_adjust(top=0.90, bottom=0.14, hspace=0.30, wspace=0.20)
    ensure(out.parent)
    figure.savefig(out, dpi=180)
    plt.close(figure)


def plot_pre_post(out: Path, diagnostics: list[dict[str, object]]) -> None:
    styles = {
        ("gate_state", "before"): ("#F08A84", "o", "gate-state before reverse"),
        ("gate_state", "after"): (RED, "^", "gate-state after reverse"),
        ("hybrid", "before"): ("#B99BEA", "s", "hybrid before reverse"),
        ("hybrid", "after"): (PURPLE, "D", "hybrid after reverse"),
    }
    figure, axes = plt.subplots(2, 3, figsize=(17.5, 10.0), sharex=True)
    for row_index, direction in enumerate(original.DIRECTIONS):
        for column, device in enumerate(item.device_id for item in base.DEVICES):
            axis = axes[row_index, column]
            for (flow, phase), (color, marker, label) in styles.items():
                rows = [
                    item for item in diagnostics
                    if item["device"] == device and item["direction"] == direction and item["flow"] == flow
                ]
                rows.sort(key=lambda item: -float(item["target_percent"]))
                values = [
                    0.5 * (
                        float(item[f"ku_{phase}_reverse_rmse"])
                        + float(item[f"kd_{phase}_reverse_rmse"])
                    )
                    for item in rows
                ]
                axis.plot(
                    [float(item["target_percent"]) for item in rows],
                    values,
                    color=color,
                    marker=marker,
                    linewidth=2.2,
                    markersize=6,
                    label=label,
                )
            axis.set_title(f"{device} | {direction.replace('_', ' ')}", fontweight="bold")
            axis.set_ylabel("Mean Ku/Kd RMSE")
            style_axis(axis)
    for axis in axes[-1]:
        axis.set_xlabel("Transistor loaded-swing target at reversal (%)")
    for axis in axes.flat:
        axis.set_xlim(92, 48)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=4, frameon=False)
    figure.suptitle("Coefficient error before and after the reverse edge", fontsize=17, fontweight="bold", y=0.98)
    figure.subplots_adjust(top=0.90, bottom=0.14, hspace=0.30, wspace=0.20)
    ensure(out.parent)
    figure.savefig(out, dpi=180)
    plt.close(figure)


def plot_switch_jumps(out: Path, diagnostics: list[dict[str, object]]) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(18.0, 6.6), sharey=True)
    for axis, device in zip(axes, (item.device_id for item in base.DEVICES)):
        rows = [item for item in diagnostics if item["device"] == device and item["flow"] == "hybrid"]
        rows.sort(key=lambda item: (
            original.DIRECTIONS.index(str(item["direction"])),
            -float(item["target_percent"]),
        ))
        labels = [
            ("H" if item["direction"] == "short_high" else "L")
            + f"{float(item['target_percent']):.0f}"
            for item in rows
        ]
        x = np.arange(len(rows))
        ku = [
            max(float(item.get("hybrid_ku_entry_jump", 0.0)), float(item.get("hybrid_ku_exit_jump", 0.0)))
            for item in rows
        ]
        kd = [
            max(float(item.get("hybrid_kd_entry_jump", 0.0)), float(item.get("hybrid_kd_exit_jump", 0.0)))
            for item in rows
        ]
        axis.bar(x - 0.18, ku, width=0.36, color="#C83E4D", label="Ku switch jump")
        axis.bar(x + 0.18, kd, width=0.36, color="#1769AA", label="Kd switch jump")
        axis.axhline(0.10, color=BLACK, linestyle="--", linewidth=1.2, label="0.10 discontinuity gate")
        axis.set_xticks(x, labels, rotation=45)
        axis.set_title(device, fontweight="bold")
        axis.set_xlabel("H/L = short-high/short-low; number = target %")
        style_axis(axis)
    axes[0].set_ylabel("Absolute coefficient jump")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=3, frameon=False)
    figure.suptitle("Hybrid path-switch discontinuity", fontsize=17, fontweight="bold", y=0.98)
    figure.subplots_adjust(top=0.85, bottom=0.24, wspace=0.03)
    ensure(out.parent)
    figure.savefig(out, dpi=180)
    plt.close(figure)


def write_readme(
    out: Path,
    baseline: Path,
    summary: list[dict[str, object]],
    metrics: list[dict[str, object]],
    diagnostics: list[dict[str, object]],
    hybrid_mode: str = HYBRID_MODE,
) -> None:
    hybrid_rows = [row for row in metrics if row["flow"] == "hybrid"]
    gate_rows = [row for row in metrics if row["flow"] == "gate_state"]
    lookup = {(row["device"], row["direction"], row["target_percent"]): row for row in gate_rows}
    improved = {signal: 0 for signal in ("pad_v_rmse_mv", "ku_rmse", "kd_rmse")}
    for row in hybrid_rows:
        gate = lookup[(row["device"], row["direction"], row["target_percent"])]
        for signal in improved:
            improved[signal] += float(row[signal]) < float(gate[signal])
    triggered = sum(bool(row.get("hybrid_active", False)) for row in diagnostics if row["flow"] == "hybrid")
    discontinuous = sum(
        bool(row.get("hybrid_switch_discontinuity", False))
        for row in diagnostics
        if row["flow"] == "hybrid"
    )
    is_v3 = hybrid_mode == "InputDrivenHybridV3AlignedReplay"
    handoff_clean = sum(
        max(
            float(row.get("hybrid_ku_entry_jump", 0.0)),
            float(row.get("hybrid_kd_entry_jump", 0.0)),
        ) <= 0.02
        for row in diagnostics
        if row["flow"] == "hybrid"
    )
    if is_v3:
        description = (
            "This pilot reuses cached HSPICE/native-IBIS, transistor, and full gate-state "
            "references and runs only the corrected V3 aligned-replay candidate in ngspice."
        )
        verdict = (
            f"V3 fixes the replay handoff structurally ({handoff_clean}/{len(hybrid_rows)} "
            "entries within 0.02), but it improves pad/Ku/Kd versus full gate-state in only "
            f"pad {improved['pad_v_rmse_mv']}/{len(hybrid_rows)}, Ku "
            f"{improved['ku_rmse']}/{len(hybrid_rows)}, and Kd "
            f"{improved['kd_rmse']}/{len(hybrid_rows)} cases. The opposite full-transition tables do not predict "
            "interrupted recovery generally, so V3 is not promoted to the full stress sweep."
        )
    else:
        description = (
            "This is a separate extension of the August 14 loaded-swing sweep. It reuses the "
            "exact cached HSPICE native-IBIS, HSPICE transistor, and full gate-state waveforms, "
            "then runs only the selected hybrid in ngspice."
        )
        verdict = (
            "The present hybrid is diagnostic, not validated. It contains some full-model "
            "errors and regresses the strongest `ex2` short-high result."
        )
    lines = [
        "# Three-Buffer Loaded-Swing Stress Sweep With Hybrid",
        "",
        description,
        "",
        f"Baseline source: `{baseline.relative_to(ROOT)}`",
        f"Hybrid mode: `{hybrid_mode}`",
        "",
        "## Coverage",
        "",
        f"- Hybrid simulations completed: `{len(hybrid_rows)}/{len(hybrid_rows)}`.",
        f"- Hybrid detector activated: `{triggered}/{len(hybrid_rows)}` cases.",
        f"- Hybrid path-switch discontinuity above 0.10: `{discontinuous}/{len(hybrid_rows)}` cases.",
        f"- Entry handoff within 0.02: `{handoff_clean}/{len(hybrid_rows)}` cases.",
        f"- Hybrid improved versus full gate-state: pad `{improved['pad_v_rmse_mv']}/{len(hybrid_rows)}`, Ku `{improved['ku_rmse']}/{len(hybrid_rows)}`, Kd `{improved['kd_rmse']}/{len(hybrid_rows)}`.",
        f"- Overall verdict: {verdict}",
        "",
        "## Aggregate Results",
        "",
        "| Buffer | Direction | Flow | Pad RMSE | Ku RMSE | Kd RMSE | Post-reverse SSE | Triggered |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['device']} | {str(row['direction']).replace('_', ' ')} | {row['flow']} | "
            f"{float(row['mean_pad_rmse_mv']):.2f} mV | {float(row['mean_ku_rmse']):.4f} | "
            f"{float(row['mean_kd_rmse']):.4f} | {100.0 * float(row['mean_post_reverse_sse_fraction']):.1f}% | "
            f"{row['hybrid_triggered_cases']}/{row['case_count']} |"
        )
    lines.extend([
        "",
        "## Files",
        "",
        "- `comparison_metrics.csv`: active-window pad/Ku/Kd errors for full gate-state and hybrid.",
        "- `coefficient_diagnostics.csv`: before/after-reverse coefficient errors, extrema, reverse-edge values, and hybrid activation intervals.",
    ])
    if is_v3:
        lines.append(
            "- `v3_structural_diagnostics.csv`: V3 anchors, independent table starts, timer monotonicity, handoff continuity, and active coefficient range."
        )
    lines.extend([
        "- `summary_by_device_direction.csv`: aggregate trends and stress correlation.",
        "- `KUKD_ANALYSIS.md`: detailed native-IBIS, gate-state, and hybrid interpretation.",
        "- `analysis_plots/`: stress trends, pre/post-reversal split, and hybrid switch-jump evidence.",
        "- `figures/<buffer>/<direction>/swing_<target>/`: two clean figures plus aligned numeric waveforms.",
        "- `all_figures_flat/`: presentation-friendly copies of all figures.",
        "- `ngspice_runs/`: hybrid decks, raw files, and logs.",
        "",
        "No HSPICE simulation was launched by this runner.",
    ])
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-study-dir", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    parser.add_argument("--ngspice-timeout", type=int, default=900)
    parser.add_argument("--device", action="append", choices=[item.device_id for item in base.DEVICES])
    parser.add_argument("--direction", action="append", choices=list(original.DIRECTIONS))
    target_percentages = [int(round(100.0 * value)) for value in original.TARGETS]
    parser.add_argument("--target-percent", action="append", type=int, choices=target_percentages)
    parser.add_argument("--hybrid-mode", default=HYBRID_MODE)
    args = parser.parse_args()

    baseline = args.baseline_study_dir.resolve()
    out = args.study_dir.resolve()
    ensure(out)
    selections = read_csv(baseline / "selection.csv")
    selected_devices = set(args.device or [device.device_id for device in base.DEVICES])
    selected_directions = set(args.direction or original.DIRECTIONS)
    selected_targets = set(args.target_percent or target_percentages)
    hybrid_label = hybrid_display_label(args.hybrid_mode)
    selections = [
        row for row in selections
        if row["device"] in selected_devices
        and row["direction"] in selected_directions
        and int(round(float(row["target_percent"]))) in selected_targets
    ]
    selections.sort(key=lambda row: (
        [item.device_id for item in base.DEVICES].index(row["device"]),
        original.DIRECTIONS.index(row["direction"]),
        -float(row["target_percent"]),
    ))

    metric_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []
    v3_rows: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []
    source_rows: list[dict[str, object]] = []
    flat_rows: list[dict[str, object]] = []
    model_cache: dict[str, Path] = {}
    profile_cache: dict[str, base.Profile] = {}

    for index, selection in enumerate(selections, start=1):
        device = device_by_id(selection["device"])
        profile = profile_cache.setdefault(
            device.device_id, base.Profile("fast_5ps", "fast-edge IBIS", device.fast_ibis)
        )
        if device.device_id not in model_cache:
            _, model_cache[device.device_id] = prepare_models(
                baseline, out, device, profile, args.hybrid_mode
            )
        case = make_case(selection)
        target = int(round(float(selection["target_percent"])))
        print(
            f"[{index}/{len(selections)}] {device.device_id} {selection['direction']} {target}%",
            flush=True,
        )
        baseline_case = (
            baseline / "figures" / device.device_id / selection["direction"] / f"swing_{target}"
        )
        baseline_waveform = baseline_case / "waveforms.csv"
        data = read_waveform(baseline_waveform)
        raw, run_row = base.run_ngspice(
            device,
            profile,
            case,
            "hybrid",
            args.hybrid_mode,
            model_cache[device.device_id],
            out / "ngspice_runs",
            args.ngspice,
            args.ngspice_timeout,
        )
        run_rows.append(run_row)
        if raw is None:
            raise RuntimeError(
                f"hybrid failed for {device.device_id}/{selection['direction']}/{target}: "
                f"{run_row.get('log', '')}"
            )
        data = add_hybrid(data, base.ngspice_waveform(raw))
        case_dir = out / "figures" / device.device_id / selection["direction"] / f"swing_{target}"
        ensure(case_dir)
        write_waveform(case_dir / "waveforms.csv", data)
        plot_pad(case_dir / "01_pad_voltage.png", device, selection, case, data, hybrid_label)
        plot_coefficients(case_dir / "02_ku_kd.png", device, selection, case, data, hybrid_label)
        metric_rows.extend(comparison_metric_rows(selection, data))
        diagnostic_rows.extend(coefficient_diagnostic_rows(selection, device, case, data))
        v3_row = v3_structural_row(selection, data)
        if v3_row is not None:
            v3_rows.append(v3_row)
        source_rows.append({
            "device": device.device_id,
            "direction": selection["direction"],
            "target_percent": target,
            "baseline_waveform": str(baseline_waveform.relative_to(ROOT)),
            "hybrid_raw": run_row.get("raw", ""),
            "hybrid_log": run_row.get("log", ""),
            "hspice_reused": True,
        })
        for plot_index, plot_name, plot_type in (
            (1, "01_pad_voltage.png", "pad_voltage"),
            (2, "02_ku_kd.png", "ku_kd"),
        ):
            order = 2 * (index - 1) + plot_index
            flat_name = (
                f"{order:02d}_{device.device_id}_{selection['direction']}_"
                f"{target}pct_{plot_type}.png"
            )
            ensure(out / "all_figures_flat")
            shutil.copy2(case_dir / plot_name, out / "all_figures_flat" / flat_name)
            flat_rows.append({
                "order": order,
                "buffer": device.device_id,
                "direction": selection["direction"],
                "target_percent": target,
                "figure_type": plot_type,
                "filename": flat_name,
            })
        write_csv(out / "comparison_metrics.csv", metric_rows)
        write_csv(out / "coefficient_diagnostics.csv", diagnostic_rows)
        write_csv(out / "v3_structural_diagnostics.csv", v3_rows)
        write_csv(out / "run_manifest.csv", run_rows)
        write_csv(out / "source_manifest.csv", source_rows)
        write_csv(out / "all_figures_flat" / "figure_manifest.csv", flat_rows)

    summary = aggregate_rows(metric_rows, diagnostic_rows)
    write_csv(out / "summary_by_device_direction.csv", summary)
    plot_rmse_trends(out / "analysis_plots" / "01_kukd_rmse_vs_stress.png", metric_rows)
    plot_pre_post(out / "analysis_plots" / "02_pre_vs_post_reverse_error.png", diagnostic_rows)
    plot_switch_jumps(out / "analysis_plots" / "03_hybrid_switch_jumps.png", diagnostic_rows)
    write_csv(out / "selection.csv", [{**row, "baseline_study": str(baseline.relative_to(ROOT))} for row in selections])
    write_readme(out, baseline, summary, metric_rows, diagnostic_rows, args.hybrid_mode)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
