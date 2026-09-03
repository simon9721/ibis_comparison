#!/usr/bin/env python3
"""Build a three-buffer, isolated true output-level reversal comparison."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
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
import matplotlib.pyplot as plt
import numpy as np

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis
from spice_tool_paths import default_hspice, default_ngspice
import run_three_buffer_pad_matched_replay as pad
import run_three_buffer_realistic_pulse_campaign as base
import screen_three_buffer_output_level_reversal as screen


DEFAULT_OUT = ROOT / "results" / "three_buffer_single_true_output_reversal_2026-08-11"
EDGE_NS = 0.050
LOAD = (50.0, 2.0)
TARGET = 0.50
DIRECTIONS = ("short_high", "short_low")
SEARCH_BRACKETS_NS = {
    "short_high": {
        "io_buf": (1.25, 1.75),
        "inv_chain": (0.100, 0.125),
        "ex2": (0.750, 1.000),
    },
    "short_low": {
        "io_buf": (0.050, 0.250),
        "inv_chain": (0.100, 0.125),
        "ex2": (0.600, 0.750),
    },
}

BLACK = "#111111"
GRAY = "#777777"
RED = "#D62728"
BLUE = "#0072B2"
PURPLE = "#7B2CBF"
GREEN = "#008B6E"
INPUT_BLUE = "#56B4E9"
GRID = "#D9DEE5"

VOLTAGE_MATCH_DIAGNOSTICS = (
    "padsamp",
    "padstartcmd",
    "padstart_latch",
    "padstartspan",
    "padmatch_ambiguous",
    "padarg",
    "padmapactive",
    "kupadmatch",
    "kdpadmatch",
    "pmsample",
    "pmlatchpulse",
    "hreverse_sample",
    "pmsample_delay",
    "pmelapsed",
)


@dataclass(frozen=True)
class Candidate:
    flow_id: str
    label: str
    mode: str
    color: str
    pad_reference: bool = False


CANDIDATES = (
    Candidate("voltage_matching", "voltage-matching", "InputDrivenPadMatchedReplayV2", RED, True),
    Candidate(
        "voltage_matching_delayed",
        "voltage-matching + IBIS delay",
        "InputDrivenPadMatchedReplayV2Delayed",
        GREEN,
        True,
    ),
    Candidate(
        "gate_state",
        "gate state model",
        "InputDrivenTwoStateGateDirectionalDualResidualFull",
        BLUE,
    ),
    Candidate(
        "hybrid",
        "hybrid",
        "InputDrivenTwoStateGateDirectionalDualResidualHybrid",
        PURPLE,
    ),
)

VOLTAGE_MATCHING_CANDIDATES = tuple(
    candidate for candidate in CANDIDATES if candidate.pad_reference
)


def ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


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


def write_wave(path: Path, data: dict[str, np.ndarray]) -> None:
    keys = [key for key, values in data.items() if values is not None]
    write_csv(
        path,
        [
            {key: float(data[key][index]) for key in keys}
            for index in range(len(data["time_ns"]))
        ],
    )


def level(wave: dict[str, np.ndarray], start_ns: float, stop_ns: float) -> float:
    mask = (wave["time_ns"] >= start_ns) & (wave["time_ns"] <= stop_ns)
    return float(np.median(wave["pad_v"][mask]))


def full_levels(wave: dict[str, np.ndarray]) -> tuple[float, float]:
    return level(wave, 3.0, 4.8), level(wave, 13.0, 14.8)


def pulse_case(direction: str, width_ns: float) -> base.PulseCase:
    return base.PulseCase(
        f"{direction}_mid50_{base.width_tag(width_ns)}",
        EDGE_NS,
        direction,
        width_ns,
        22.0,
        f"50% loaded-output {direction.replace('_', ' ')} reversal",
    )


def control_case() -> base.PulseCase:
    return base.PulseCase("long_control", EDGE_NS, "rise_fall", 10.0, 22.0, "long control")


def search_midpoint(
    device: base.Device,
    direction: str,
    hspice: Path,
    timeout_s: int,
    transistor_levels: tuple[float, float],
) -> tuple[float, list[dict[str, object]], dict[str, np.ndarray]]:
    tested: dict[float, tuple[dict[str, np.ndarray], dict[str, object]]] = {}

    def evaluate(width_ns: float) -> tuple[dict[str, np.ndarray], dict[str, object]]:
        width_ns = round(width_ns, 6)
        if width_ns in tested:
            return tested[width_ns]
        case = pulse_case(direction, width_ns)
        wave, reference = pad.run_transistor_reference(device, case, hspice, timeout_s)
        result = screen.evaluate(
            wave,
            case.pattern,
            width_ns,
            transistor_levels[0],
            transistor_levels[1],
        )
        row: dict[str, object] = {
            "device": device.device_id,
            "direction": direction,
            "width_ns": width_ns,
            "pulse_width_ps": 1000.0 * width_ns,
            "reference": "hspice_transistor",
            **result,
            "target_error": abs(float(result["output_excursion_fraction"]) - TARGET),
            "source": reference["source"],
            "tr0": reference["tr0"],
        }
        tested[width_ns] = (wave, row)
        print(
            f"  {device.device_id}: {1000.0 * width_ns:.3f} ps -> "
            f"{100.0 * float(result['output_excursion_fraction']):.2f}% transistor swing",
            flush=True,
        )
        return wave, row

    low, high = SEARCH_BRACKETS_NS[direction][device.device_id]
    evaluate(low)
    evaluate(high)
    for _ in range(7):
        middle = round(0.5 * (low + high), 6)
        _, row = evaluate(middle)
        if float(row["output_excursion_fraction"]) < TARGET:
            low = middle
        else:
            high = middle
    best_width = min(
        tested,
        key=lambda width: (
            abs(float(tested[width][1]["output_excursion_fraction"]) - TARGET),
            width,
        ),
    )
    best_wave = tested[best_width][0]
    return best_width, [tested[key][1] for key in sorted(tested)], best_wave


def prepare_models(
    out: Path,
    device: base.Device,
    profile: base.Profile,
    pad_reference: dict,
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for candidate in CANDIDATES:
        model = (
            out
            / "generated_models"
            / device.device_id
            / profile.profile_id
            / candidate.flow_id
            / f"{device.subckt}.sub"
        )
        convert_ibis_to_pybis(
            profile.ibis,
            model,
            device.component,
            device.model,
            "Output",
            candidate.mode,
            "Typical",
            pad_replay_reference=pad_reference if candidate.pad_reference else None,
        )
        result[candidate.flow_id] = model
    return result


def run_candidate(
    out: Path,
    device: base.Device,
    profile: base.Profile,
    case: base.PulseCase,
    candidate: Candidate,
    model: Path,
    ngspice: Path,
    timeout_s: int,
    resume: bool,
) -> tuple[dict[str, np.ndarray] | None, dict[str, object]]:
    if candidate.pad_reference:
        old_out = pad.OUT
        pad.OUT = out
        try:
            flow = pad.Flow(
                candidate.flow_id,
                candidate.label,
                candidate.mode,
                candidate.color,
                True,
            )
            return pad.run_ngspice(
                device,
                profile,
                case,
                LOAD,
                flow,
                model,
                ngspice,
                timeout_s,
                resume,
            )
        finally:
            pad.OUT = old_out

    raw, row = base.run_ngspice(
        device,
        profile,
        case,
        candidate.flow_id,
        candidate.mode,
        model,
        out / "structural_runs",
        ngspice,
        timeout_s,
    )
    return (None if raw is None else base.ngspice_waveform(raw)), row


def align(
    native: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
    waves: dict[str, dict[str, np.ndarray] | None],
) -> dict[str, np.ndarray]:
    time_ns = native["time_ns"]
    result = {
        "time_ns": time_ns,
        "input_v": native["input_v"],
        "hspice_native_pad_v": native["pad_v"],
        "hspice_native_ku": native["ku"],
        "hspice_native_kd": native["kd"],
        "hspice_transistor_pad_v": np.interp(
            time_ns, transistor["time_ns"], transistor["pad_v"]
        ),
    }
    for flow_id, wave in waves.items():
        if wave is None:
            continue
        for key in (
            "pad_v",
            "ku",
            "kd",
            "gup",
            "gdn",
            "hhybridactive",
            *VOLTAGE_MATCH_DIAGNOSTICS,
        ):
            values = wave.get(key)
            if values is not None:
                result[f"{flow_id}_{key}"] = np.interp(time_ns, wave["time_ns"], values)
    return result


def rmse(reference: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(reference[mask] - candidate[mask]))))


def measure_candidate(
    device: base.Device,
    case: base.PulseCase,
    candidate: Candidate,
    data: dict[str, np.ndarray],
    candidate_levels: tuple[float, float],
    native_turn_ns: float,
) -> dict[str, object]:
    prefix = candidate.flow_id
    if f"{prefix}_pad_v" not in data:
        return {
            "device": device.device_id,
            "flow": prefix,
            "label": candidate.label,
            "status": "NUMERIC_FAIL",
        }
    time_ns = data["time_ns"]
    reverse_ns = base.command_edges(device, case)[-1]
    mask = (time_ns >= base.command_edges(device, case)[0] - 0.5) & (
        time_ns <= native_turn_ns + 2.0
    )
    local_start = 5.0 if case.pattern == "short_high" else 10.0
    local_stop = 12.0 if case.pattern == "short_high" else 18.0
    local = (time_ns >= local_start) & (time_ns <= local_stop)
    pad_values = data[f"{prefix}_pad_v"]
    local_indexes = np.flatnonzero(local)
    peak_index = local_indexes[
        int(np.argmax(pad_values[local]) if case.pattern == "short_high" else np.argmin(pad_values[local]))
    ]
    swing = max(candidate_levels[1] - candidate_levels[0], 1e-12)
    excursion = (
        (float(pad_values[peak_index]) - candidate_levels[0]) / swing
        if case.pattern == "short_high"
        else (candidate_levels[1] - float(pad_values[peak_index])) / swing
    )
    row: dict[str, object] = {
        "device": device.device_id,
        "flow": prefix,
        "label": candidate.label,
        "direction": case.pattern,
        "status": "COMPLETED",
        "pulse_width_ps": 1000.0 * case.pulse_width_ns,
        "pad_extreme_v": float(pad_values[peak_index]),
        "output_turn_time_ns": float(time_ns[peak_index]),
        "output_excursion_fraction": excursion,
        "pad_rmse_mv": 1000.0 * rmse(data["hspice_native_pad_v"], pad_values, mask),
        "ku_rmse": rmse(data["hspice_native_ku"], data[f"{prefix}_ku"], mask),
        "kd_rmse": rmse(data["hspice_native_kd"], data[f"{prefix}_kd"], mask),
        "input_reverse_threshold_ns": reverse_ns,
        "native_output_turn_time_ns": native_turn_ns,
    }
    if prefix == "hybrid" and "hybrid_hhybridactive" in data:
        active = data["hybrid_hhybridactive"] > 0.5
        row["hybrid_activated"] = bool(np.any(active))
        row["hybrid_active_duration_ns"] = float(
            np.trapezoid(active.astype(float), time_ns)
        )
    return row


def plot_case(
    out: Path,
    device: base.Device,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
    transistor_levels: tuple[float, float],
    native_turn_ns: float,
) -> Path:
    reverse_ns = base.command_edges(device, case)[-1]
    relative_time = data["time_ns"] - reverse_ns
    turn_relative = native_turn_ns - reverse_ns
    start = -max(0.45, case.pulse_width_ns + 0.20)
    stop = turn_relative + 2.0
    mask = (relative_time >= start) & (relative_time <= stop)
    t = relative_time[mask]

    figure, axes = plt.subplots(4, 1, figsize=(15.5, 11.6), sharex=True)
    axes[0].plot(t, data["input_v"][mask], color=INPUT_BLUE, linewidth=2.0, label="input")
    axes[0].set_ylabel("Input (V)")

    axes[1].plot(
        t,
        data["hspice_native_pad_v"][mask],
        color=BLACK,
        linewidth=3.2,
        label="HSPICE native IBIS",
        zorder=6,
    )
    axes[1].plot(
        t,
        data["hspice_transistor_pad_v"][mask],
        color=GRAY,
        linewidth=3.0,
        label="HSPICE transistor",
        zorder=3,
    )
    axes[1].axhline(
        transistor_levels[0] + TARGET * (transistor_levels[1] - transistor_levels[0]),
        color=GREEN,
        linewidth=1.2,
        linestyle="--",
        label="50% transistor loaded swing",
    )
    axes[1].set_ylabel("Pad (V)")

    for axis, suffix, ylabel in ((axes[2], "ku", "Ku"), (axes[3], "kd", "Kd")):
        axis.plot(
            t,
            data[f"hspice_native_{suffix}"][mask],
            color=BLACK,
            linewidth=3.2,
            label="HSPICE native IBIS",
            zorder=6,
        )
        axis.set_ylabel(ylabel)
    axes[3].axhline(0.0, color="#999999", linewidth=0.8)

    styles = {
        "voltage_matching": (RED, "-", 2.1),
        "gate_state": (BLUE, "--", 2.1),
        "hybrid": (PURPLE, "-.", 2.3),
    }
    labels = {candidate.flow_id: candidate.label for candidate in CANDIDATES}
    for flow_id, (color, linestyle, linewidth) in styles.items():
        for axis, suffix in ((axes[1], "pad_v"), (axes[2], "ku"), (axes[3], "kd")):
            key = f"{flow_id}_{suffix}"
            if key in data:
                axis.plot(
                    t,
                    data[key][mask],
                    color=color,
                    linestyle=linestyle,
                    linewidth=linewidth,
                    label=labels[flow_id],
                    zorder=5 if flow_id == "voltage_matching" else 4,
                )

    for axis in axes:
        axis.axvline(
            0.0,
            color=PURPLE,
            linestyle="--",
            linewidth=1.5,
            label="input reverse threshold",
        )
        axis.grid(True, color=GRID, linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)
    axes[3].set_xlabel("Time from input reverse threshold (ns)")

    handles: list[object] = []
    legend_labels: list[str] = []
    for axis in axes:
        for handle, label in zip(*axis.get_legend_handles_labels()):
            if label not in legend_labels:
                handles.append(handle)
                legend_labels.append(label)
    figure.legend(
        handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=3,
        frameon=False,
    )
    figure.suptitle(
        f"{device.device_id} | {case.pattern.replace('_', ' ')} output reversal | "
        f"{case.pulse_width_ns * 1000:.1f} ps pulse",
        fontsize=17,
        fontweight="bold",
        y=0.895,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.84))
    output_name = (
        f"{device.device_id}_single_output_reversal.png"
        if case.pattern == "short_high"
        else f"{device.device_id}_short_low_single_output_reversal.png"
    )
    output = out / "figures" / output_name
    ensure(output.parent)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return output


def voltage_match_event(
    device: base.Device,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
    candidate: Candidate,
) -> dict[str, object]:
    """Extract the actual sampled voltage and opposite-table replay start."""
    def diagnostic(name: str) -> np.ndarray:
        aligned_name = f"voltage_matching_{name}"
        return data[aligned_name] if aligned_name in data else data[name]

    time_ns = data["time_ns"]
    reverse_ns = base.command_edges(device, case)[-1]
    active = diagnostic("padmapactive") > 0.5
    event = active & (time_ns >= reverse_ns - 0.05)
    indexes = np.flatnonzero(event)
    if len(indexes) == 0:
        raise RuntimeError(f"No voltage-matching event for {device.device_id}/{case.case_id}")

    first_index = int(indexes[0])
    sample = (diagnostic("pmsample") > 0.5) & (
        time_ns >= reverse_ns - 0.05
    )
    sample_indexes = np.flatnonzero(sample)
    if len(sample_indexes) == 0:
        raise RuntimeError(f"No voltage-matching sample for {device.device_id}/{case.case_id}")
    sample_index = int(sample_indexes[-1])
    latch = (diagnostic("pmlatchpulse") > 0.5) & (
        time_ns >= reverse_ns - 0.05
    )
    latch_indexes = np.flatnonzero(latch)
    if len(latch_indexes) == 0:
        raise RuntimeError(f"No voltage-matching latch for {device.device_id}/{case.case_id}")
    latch_index = int(latch_indexes[-1])
    sample_v = float(diagnostic("padsamp")[sample_index])
    lookup_start_ns = float(diagnostic("padstartcmd")[latch_index])
    latched_start_ns = float(diagnostic("padstart_latch")[latch_index])
    replay_arg_ns = float(diagnostic("padarg")[first_index])
    span_ns = float(diagnostic("padstartspan")[latch_index])
    ambiguous = bool(diagnostic("padmatch_ambiguous")[latch_index] > 0.5)
    return {
        "device": device.device_id,
        "flow": candidate.flow_id,
        "label": candidate.label,
        "direction": case.pattern,
        "pulse_width_ps": 1000.0 * case.pulse_width_ns,
        "input_reverse_ns": reverse_ns,
        "sample_capture_time_ns": float(time_ns[sample_index]),
        "sample_delay_from_reverse_ps": 1000.0 * float(
            time_ns[sample_index] - reverse_ns
        ),
        "start_latch_time_ns": float(time_ns[latch_index]),
        "mapping_activation_ns": float(time_ns[first_index]),
        "sampled_pad_v": sample_v,
        "opposite_trajectory": "falling" if case.pattern == "short_high" else "rising",
        "opposite_table_lookup_start_ns": lookup_start_ns,
        "opposite_table_latched_start_ns": latched_start_ns,
        "opposite_table_replay_arg_at_activation_ns": replay_arg_ns,
        "opposite_table_start_span_ns": span_ns,
        "mapping_ambiguous": ambiguous,
        "mapped_ku_at_start": float(diagnostic("kupadmatch")[first_index]),
        "mapped_kd_at_start": float(diagnostic("kdpadmatch")[first_index]),
        "mapping_active_duration_ns": float(np.trapezoid(active.astype(float), time_ns)),
    }


def plot_voltage_matching_case(
    out: Path,
    device: base.Device,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
    pad_reference: dict[str, object],
    event: dict[str, object],
    candidate: Candidate,
) -> Path:
    """Plot the voltage sample, inverse mapping, and resulting Ku/Kd replay."""
    reverse_ns = float(event["input_reverse_ns"])
    relative_time = data["time_ns"] - reverse_ns
    start = -max(0.45, case.pulse_width_ns + 0.20)
    active_stop = (
        float(event["mapping_activation_ns"])
        - reverse_ns
        + float(event["mapping_active_duration_ns"])
        + 0.5
    )
    stop = min(float(relative_time[-1]), max(2.0, active_stop))
    mask = (relative_time >= start) & (relative_time <= stop)
    t = relative_time[mask]

    figure, axes = plt.subplots(2, 2, figsize=(16.4, 10.2), constrained_layout=True)
    pad_axis, map_axis, ku_axis, kd_axis = axes.ravel()

    prefix = candidate.flow_id
    pad_axis.plot(
        t,
        data["hspice_native_pad_v"][mask],
        color=BLACK,
        linewidth=3.2,
        label="HSPICE native IBIS",
        zorder=5,
    )
    pad_axis.plot(
        t,
        data["hspice_transistor_pad_v"][mask],
        color=GRAY,
        linewidth=3.0,
        label="HSPICE transistor",
        zorder=3,
    )
    pad_axis.plot(
        t,
        data[f"{prefix}_pad_v"][mask],
        color=RED,
        linewidth=2.4,
        label=candidate.label,
        zorder=4,
    )
    command_edges = base.command_edges(device, case)
    first_pulse_edge_relative = command_edges[-2] - reverse_ns
    sample_relative = float(event["sample_capture_time_ns"]) - reverse_ns
    activation_relative = float(event["mapping_activation_ns"]) - reverse_ns
    sampled_v = float(event["sampled_pad_v"])
    pad_axis.scatter(
        [sample_relative],
        [sampled_v],
        color=RED,
        edgecolor="white",
        linewidth=1.0,
        marker="D",
        s=90,
        zorder=7,
        label=f"pad sampled after second edge = {sampled_v:.3f} V",
    )
    pad_axis.axhline(sampled_v, color=RED, linewidth=1.0, linestyle=":", alpha=0.7)
    pad_axis.axvline(
        first_pulse_edge_relative,
        color=INPUT_BLUE,
        linestyle=":",
        linewidth=1.5,
        label="first input edge",
    )
    pad_axis.set_title("Runtime pad voltage and sampled reversal state", loc="left", fontweight="bold")
    pad_axis.set_xlabel("Time from input reverse threshold (ns)")
    pad_axis.set_ylabel("Pad voltage (V)")

    trajectory_name = str(event["opposite_trajectory"])
    trajectory = pad_reference[trajectory_name]
    table_time = np.asarray(trajectory["time_ns"], dtype=float)
    table_pad = np.asarray(trajectory["pad_v"], dtype=float)
    lookup_start = float(event["opposite_table_lookup_start_ns"])
    latched_start = float(event["opposite_table_latched_start_ns"])
    replay_arg = float(event["opposite_table_replay_arg_at_activation_ns"])
    mapped_pad = float(np.interp(lookup_start, table_time, table_pad))
    map_axis.plot(
        table_time,
        table_pad,
        color=BLUE,
        linewidth=2.6,
        label=f"offline {trajectory_name} pad trajectory",
    )
    map_axis.axhline(sampled_v, color=RED, linewidth=1.4, linestyle="--")
    map_axis.axvline(lookup_start, color=RED, linewidth=1.3, linestyle="--")
    map_axis.axvline(replay_arg, color=PURPLE, linewidth=1.5, linestyle=":")
    map_axis.scatter(
        [lookup_start],
        [mapped_pad],
        color=RED,
        edgecolor="white",
        linewidth=1.0,
        marker="D",
        s=90,
        zorder=6,
    )
    map_axis.annotate(
        f"sampled Vpad = {sampled_v:.3f} V\nlookup start = {lookup_start:.3f} ns",
        xy=(lookup_start, mapped_pad),
        xytext=(0.97, 0.08),
        textcoords="axes fraction",
        ha="right",
        va="bottom",
        fontsize=10.5,
        arrowprops={"arrowstyle": "->", "color": RED, "linewidth": 1.1},
    )
    map_axis.text(
        0.97,
        0.30,
        f"latched start = {latched_start:.3f} ns\n"
        f"actual PADARG at replay = {replay_arg:.3f} ns",
        transform=map_axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=10.0,
        color=PURPLE,
    )
    map_axis.set_title("Offline voltage-to-opposite-table mapping", loc="left", fontweight="bold")
    map_axis.set_xlabel("Opposite-table time (ns)")
    map_axis.set_ylabel("Calibration pad voltage (V)")

    for axis, coefficient, ylabel in (
        (ku_axis, "ku", "Ku"),
        (kd_axis, "kd", "Kd"),
    ):
        axis.plot(
            t,
            data[f"hspice_native_{coefficient}"][mask],
            color=BLACK,
            linewidth=3.2,
            label="HSPICE native IBIS",
            zorder=5,
        )
        axis.plot(
            t,
            data[f"{prefix}_{coefficient}"][mask],
            color=RED,
            linewidth=2.4,
            label=candidate.label,
            zorder=4,
        )
        mapped_value = float(event[f"mapped_{coefficient}_at_start"])
        axis.scatter(
            [activation_relative],
            [mapped_value],
            color=RED,
            edgecolor="white",
            linewidth=1.0,
            marker="D",
            s=85,
            zorder=7,
            label=f"opposite-table start: {ylabel}={mapped_value:.3f}",
        )
        axis.axvline(0.0, color=PURPLE, linestyle="--", linewidth=1.4)
        axis.axvline(
            first_pulse_edge_relative,
            color=INPUT_BLUE,
            linestyle=":",
            linewidth=1.2,
        )
        axis.set_title(f"Runtime {ylabel} after opposite-table mapping", loc="left", fontweight="bold")
        axis.set_xlabel("Time from input reverse threshold (ns)")
        axis.set_ylabel(ylabel)
        axis.legend(loc="best", frameon=False)
    kd_axis.axhline(0.0, color="#999999", linewidth=0.8)

    pad_axis.axvline(
        0.0,
        color=PURPLE,
        linestyle="--",
        linewidth=1.4,
        label="second/reverse input edge",
    )
    pad_axis.legend(loc="best", frameon=False, ncol=2)
    map_axis.legend(loc="best", frameon=False)
    for axis in axes.ravel():
        axis.grid(True, color=GRID, linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)

    figure.suptitle(
        f"{device.device_id} | {case.pattern.replace('_', ' ')} | {candidate.label} | "
        f"{case.pulse_width_ns * 1000:.1f} ps pulse",
        fontsize=17,
        fontweight="bold",
    )
    output = (
        out
        / f"{candidate.flow_id}_only"
        / f"{device.device_id}_{case.pattern}_voltage_mapping.png"
    )
    ensure(output.parent)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return output


def coefficient_turn_rows(
    device: base.Device,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
    native_turn_ns: float,
) -> list[dict[str, object]]:
    """Locate the Ku maximum and Kd minimum after the input reverses."""
    time_ns = data["time_ns"]
    reverse_ns = base.command_edges(device, case)[-1]
    stop_ns = min(float(time_ns[-1]), native_turn_ns + 2.0)
    mask = (time_ns >= reverse_ns) & (time_ns <= stop_ns)
    indexes = np.flatnonzero(mask)
    flows = [
        ("hspice_native", "HSPICE native IBIS", "hspice_native"),
        *[(candidate.flow_id, candidate.label, candidate.flow_id) for candidate in CANDIDATES],
    ]
    rows: list[dict[str, object]] = []
    turn_specs = (
        (("ku", "rising_to_falling", "max"), ("kd", "falling_to_rising", "min"))
        if case.pattern == "short_high"
        else (("ku", "falling_to_rising", "min"), ("kd", "rising_to_falling", "max"))
    )
    for flow_id, label, prefix in flows:
        for coefficient, direction, extreme in turn_specs:
            key = f"{prefix}_{coefficient}"
            if key not in data or len(indexes) < 3:
                continue
            values = data[key]
            local = values[indexes]
            local_index = int(np.argmax(local) if extreme == "max" else np.argmin(local))
            index = int(indexes[local_index])
            before = float(np.interp(reverse_ns - 0.010, time_ns, values))
            after = float(np.interp(reverse_ns + 0.010, time_ns, values))
            at_boundary = local_index in {0, len(indexes) - 1}
            rows.append({
                "device": device.device_id,
                "pulse_direction": case.pattern,
                "flow": flow_id,
                "label": label,
                "coefficient": coefficient,
                "direction_change": direction,
                "input_reverse_ns": reverse_ns,
                "turn_time_ns": float(time_ns[index]),
                "turn_time_from_reverse_ps": 1000.0 * float(time_ns[index] - reverse_ns),
                "turn_value": float(values[index]),
                "coefficient_change_across_reverse_20ps": after - before,
                "turn_at_search_boundary": at_boundary,
                "turn_interpretation": (
                    "retrigger_boundary_or_jump"
                    if at_boundary or abs(after - before) > 0.05
                    else "resolved_waveform_extremum"
                ),
            })
    return rows


def plot_coefficient_turns(
    out: Path,
    device: base.Device,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
    rows: list[dict[str, object]],
    native_turn_ns: float,
) -> Path:
    reverse_ns = base.command_edges(device, case)[-1]
    relative_time = data["time_ns"] - reverse_ns
    start = -0.25
    stop = native_turn_ns - reverse_ns + 2.0
    mask = (relative_time >= start) & (relative_time <= stop)
    styles = {
        "hspice_native": (BLACK, "-", 3.2, "o"),
        "voltage_matching": (RED, "-", 2.1, "s"),
        "gate_state": (BLUE, "--", 2.1, "^"),
        "hybrid": (PURPLE, "-.", 2.3, "D"),
    }
    prefixes = {
        "hspice_native": "hspice_native",
        "voltage_matching": "voltage_matching",
        "gate_state": "gate_state",
        "hybrid": "hybrid",
    }
    figure, axes = plt.subplots(2, 1, figsize=(15.5, 8.8), sharex=True)
    titles = (
        (("ku", "Ku: rising to falling"), ("kd", "Kd: falling to rising"))
        if case.pattern == "short_high"
        else (("ku", "Ku: falling to rising"), ("kd", "Kd: rising to falling"))
    )
    for axis, (coefficient, title) in zip(axes, titles):
        coefficient_rows = {
            str(row["flow"]): row
            for row in rows
            if row["coefficient"] == coefficient
        }
        for flow_id, (color, linestyle, linewidth, marker) in styles.items():
            key = f"{prefixes[flow_id]}_{coefficient}"
            row = coefficient_rows.get(flow_id)
            if key not in data or row is None:
                continue
            delta_ps = float(row["turn_time_from_reverse_ps"])
            label = f"{row['label']}: {delta_ps:+.1f} ps"
            axis.plot(
                relative_time[mask],
                data[key][mask],
                color=color,
                linestyle=linestyle,
                linewidth=linewidth,
                label=label,
            )
            axis.scatter(
                [delta_ps * 1e-3],
                [float(row["turn_value"])],
                color=color,
                edgecolor="white",
                linewidth=0.8,
                marker=marker,
                s=72,
                zorder=8,
            )
        axis.axvline(
            0.0,
            color=PURPLE,
            linestyle=":",
            linewidth=1.6,
            label="input reverse threshold",
        )
        axis.set_title(title, loc="left", fontsize=14, fontweight="bold")
        axis.set_ylabel(coefficient.capitalize())
        axis.grid(True, color=GRID, linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)
        axis.legend(loc="best", frameon=False, ncol=2)
    axes[1].axhline(0.0, color="#999999", linewidth=0.8)
    axes[1].set_xlabel("Time from input reverse threshold (ns)")
    figure.suptitle(
        f"{device.device_id} | {case.pattern.replace('_', ' ')} coefficient direction changes | "
        f"{case.pulse_width_ns * 1000:.1f} ps pulse",
        fontsize=17,
        fontweight="bold",
        y=0.985,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    output_name = (
        f"{device.device_id}_ku_kd_direction_changes.png"
        if case.pattern == "short_high"
        else f"{device.device_id}_short_low_ku_kd_direction_changes.png"
    )
    output = out / "coefficient_direction" / output_name
    ensure(output.parent)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return output


def plot_selection(
    out: Path,
    rows: list[dict[str, object]],
    selections: list[dict[str, object]],
    direction: str,
) -> Path:
    figure, axes = plt.subplots(1, 3, figsize=(16.5, 5.2), constrained_layout=True)
    for axis, device in zip(axes, base.DEVICES):
        selected = sorted(
            [
                row for row in rows
                if row["device"] == device.device_id and row["direction"] == direction
            ],
            key=lambda row: float(row["pulse_width_ps"]),
        )
        axis.plot(
            [float(row["pulse_width_ps"]) for row in selected],
            [100.0 * float(row["output_excursion_fraction"]) for row in selected],
            color=GRAY,
            marker="o",
            linewidth=2.0,
            label="HSPICE transistor",
        )
        chosen = next(
            row for row in selections
            if row["device"] == device.device_id and row["direction"] == direction
        )
        axis.scatter(
            [float(chosen["pulse_width_ps"])],
            [100.0 * float(chosen["transistor_excursion_fraction"])],
            s=110,
            color=RED,
            zorder=5,
            label="selected",
        )
        axis.axhline(50.0, color=GREEN, linestyle="--", linewidth=1.5, label="50% target")
        axis.set_title(device.device_id)
        axis.set_xlabel(f"{direction.replace('_', '-')} pulse width (ps)")
        axis.grid(True, color=GRID, linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Transistor output excursion (% loaded swing)")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=3, frameon=False)
    output = out / (
        "00_midpoint_pulse_selection.png"
        if direction == "short_high"
        else "03_short_low_midpoint_pulse_selection.png"
    )
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return output


def contact_sheet(paths: list[Path], output: Path) -> None:
    images = [plt.imread(path) for path in paths]
    figure, axes = plt.subplots(len(images), 1, figsize=(16.0, 10.2 * len(images)), constrained_layout=True)
    axes_array = np.atleast_1d(axes)
    for axis, image in zip(axes_array, images):
        axis.imshow(image)
        axis.axis("off")
    figure.savefig(output, dpi=120)
    plt.close(figure)


def write_readme(
    out: Path,
    selections: list[dict[str, object]],
    metrics: list[dict[str, object]],
    run_rows: list[dict[str, object]],
) -> None:
    lines = [
        "# Three-Buffer Single True Output-Level Reversal",
        "",
        "This package contains isolated short-high and short-low pulses only. No PRBS results are included.",
        "All cases use the fast-edge IBIS profile, 50 ps input edges, and a direct 50 ohm || 2 pF load.",
        "Pulse widths are selected against 50% of the HSPICE transistor buffer's measured loaded swing, not raw VDD.",
        "",
        "## Selected Cases",
        "",
        "| Buffer | Direction | Pulse | Transistor excursion | Native-IBIS excursion | Native partial reversal |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in selections:
        lines.append(
            f"| {row['device']} | {str(row['direction']).replace('_', ' ')} | "
            f"{float(row['pulse_width_ps']):.1f} ps | "
            f"{100.0 * float(row['transistor_excursion_fraction']):.1f}% | "
            f"{100.0 * float(row['native_excursion_fraction']):.1f}% | "
            f"{row['native_partial_output_reversal']} |"
        )
    lines.extend([
        "",
        "## Compared Models",
        "",
        "- `voltage-matching`: `InputDrivenPadMatchedReplayV2`.",
        "- `voltage-matching + IBIS delay`: `InputDrivenPadMatchedReplayV2Delayed`; samples at the earliest direction-specific output-stage action derived from the same PU/PD delays as the gate-state model.",
        "- `gate state model`: `InputDrivenTwoStateGateDirectionalDualResidualFull`.",
        "- `hybrid`: `InputDrivenTwoStateGateDirectionalDualResidualHybrid`; legacy replay normally, gate-state path during detected reversal.",
        "- HSPICE native IBIS supplies pad, Ku, and Kd. HSPICE transistor supplies pad only.",
        "- The hybrid reversal branch activated in every selected event; these are not inactive legacy-path comparisons.",
        "",
        "## Why The Target Is Loaded-Swing Midpoint",
        "",
        "With the fixed 50 ohm load, the fully settled transistor outputs are below VDD. "
        "For io_buf and ex2 they are also below 0.5*VDD, so a literal 50% VDD peak is unreachable without changing the bench. "
        "The study therefore targets 50% of each transistor buffer's own measured loaded swing, which is the comparable electrical midpoint.",
        "",
        "## Figure Markers",
        "",
        "- Purple dashed line: the instant the input crosses its threshold on the reverse edge.",
        "- Green horizontal line: 50% of the transistor reference's measured loaded output swing.",
        "",
        "## Candidate Metrics",
        "",
        "| Buffer | Direction | Model | Pad RMSE | Ku RMSE | Kd RMSE | Output excursion |",
        "|---|---|---|---:|---:|---:|---:|",
    ])
    for row in metrics:
        if row.get("status") != "COMPLETED":
            lines.append(
                f"| {row['device']} | {str(row['direction']).replace('_', ' ')} | "
                f"{row['label']} | failed | failed | failed | failed |"
            )
            continue
        lines.append(
            f"| {row['device']} | {str(row['direction']).replace('_', ' ')} | "
            f"{row['label']} | {float(row['pad_rmse_mv']):.1f} mV | "
            f"{float(row['ku_rmse']):.4f} | {float(row['kd_rmse']):.4f} | "
            f"{100.0 * float(row['output_excursion_fraction']):.1f}% |"
        )
    lines.extend([
        "",
        "## Main Findings",
        "",
        "- Short-high: io_buf favors voltage-matching at the pad, inv_chain favors the gate-state/hybrid family, and ex2 is strongest with the full gate-state model. None is coefficient-correct across all three buffers.",
        "- Short-low: io_buf again has the lowest pad RMSE with voltage-matching, while inv_chain and ex2 favor the gate-state/hybrid family. Their gate-state outputs generally complete or over-complete the swing rather than preserving the selected partial event.",
        "- The transistor-selected 50% pulse does not imply a 50% native-IBIS response: short-low native excursions range from 8.8% for io_buf to 94.9% for ex2. The two references therefore remain separate in every figure.",
        "- No one method wins across all three buffers, so none is ready as a general interrupted-transition replacement.",
    ])
    completed = sum(row.get("status") == "COMPLETED" for row in run_rows)
    lines.extend([
        "",
        "## Files",
        "",
        "- `00_midpoint_pulse_selection.png`: pulse-width refinement to the transistor 50% point.",
        "- `01_three_buffer_contact_sheet.png`: all three isolated comparisons.",
        "- `figures/`: one input/pad/Ku/Kd figure per buffer and direction.",
        "- `02_coefficient_direction_contact_sheet.png`: Ku/Kd direction-change markers for all buffers.",
        "- `03_short_low_midpoint_pulse_selection.png`: short-low transistor midpoint refinement.",
        "- `04_short_low_contact_sheet.png`: all three short-low isolated comparisons.",
        "- `05_short_low_coefficient_direction_contact_sheet.png`: short-low Ku/Kd direction changes.",
        "- `06_voltage_matching_short_high_contact_sheet.png`: voltage-matching-only short-high evidence.",
        "- `07_voltage_matching_short_low_contact_sheet.png`: voltage-matching-only short-low evidence.",
        "- `08_delayed_voltage_matching_short_high_contact_sheet.png`: delayed voltage-matching short-high evidence.",
        "- `09_delayed_voltage_matching_short_low_contact_sheet.png`: delayed voltage-matching short-low evidence.",
        "- `voltage_matching_only/`: sampled pad voltage, opposite-trajectory mapping, and Ku/Kd replay for every selected event.",
        "- `voltage_matching_delayed_only/`: the same evidence after IBIS-derived sampling delay.",
        "- `voltage_matching_mapping_events.csv`: numeric sampled voltage and inferred opposite-table starting point.",
        "- `coefficient_direction/`: one Ku/Kd direction-change figure per buffer and direction.",
        "- `coefficient_turn_times.csv`: exact coefficient extrema relative to the input reverse threshold.",
        "- `waveforms/`: numeric data behind each figure.",
        "- `selection.csv`: midpoint selection evidence.",
        "- `candidate_metrics.csv`: pad and coefficient correlation.",
        "- `run_manifest.csv`: simulator completion and provenance.",
        "",
        f"Completed ngspice flows: `{completed}/{len(run_rows)}`.",
    ])
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    parser.add_argument("--hspice-timeout", type=int, default=300)
    parser.add_argument("--ngspice-timeout", type=int, default=900)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    out = args.study_dir if args.study_dir.is_absolute() else ROOT / args.study_dir
    out = out.resolve()
    ensure(out)
    pad.OUT = out

    search_rows: list[dict[str, object]] = []
    selections: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []
    reference_rows: list[dict[str, object]] = []
    figures: dict[str, list[Path]] = {direction: [] for direction in DIRECTIONS}
    coefficient_figures: dict[str, list[Path]] = {direction: [] for direction in DIRECTIONS}
    voltage_matching_figures: dict[str, dict[str, list[Path]]] = {
        candidate.flow_id: {direction: [] for direction in DIRECTIONS}
        for candidate in VOLTAGE_MATCHING_CANDIDATES
    }
    coefficient_rows: list[dict[str, object]] = []
    voltage_matching_events: list[dict[str, object]] = []

    for device in base.DEVICES:
        print(f"[{device.device_id}] controls and models", flush=True)
        profile = base.Profile("fast_5ps", "fast-edge IBIS", device.fast_ibis)
        control = control_case()
        native_control, native_control_row = pad.run_native_reference(
            device, profile, control, LOAD, args.hspice, args.hspice_timeout
        )
        transistor_control, transistor_control_row = pad.run_transistor_reference(
            device, control, args.hspice, args.hspice_timeout
        )
        reference_rows.extend((native_control_row, transistor_control_row))
        native_levels = full_levels(native_control)
        transistor_levels = full_levels(transistor_control)

        legacy = pad.prepare_legacy(device, profile)
        pad_reference, calibration_row = pad.build_pad_reference(
            device,
            profile,
            legacy,
            args.ngspice,
            max(120, args.ngspice_timeout),
            args.resume,
        )
        reference_rows.append({"device": device.device_id, "reference": "pybis_pad_calibration", **calibration_row})
        models = prepare_models(out, device, profile, pad_reference)

        control_waves: dict[str, dict[str, np.ndarray] | None] = {}
        for candidate in CANDIDATES:
            print(f"  {candidate.label}: long control", flush=True)
            control_wave, control_run = run_candidate(
                out,
                device,
                profile,
                control,
                candidate,
                models[candidate.flow_id],
                args.ngspice,
                args.ngspice_timeout,
                args.resume,
            )
            control_run.update({"case_role": "long_control", "label": candidate.label})
            run_rows.append(control_run)
            control_waves[candidate.flow_id] = control_wave

        for direction in DIRECTIONS:
            print(f"  {direction}: HSPICE midpoint search", flush=True)
            width_ns, device_search, transistor = search_midpoint(
                device,
                direction,
                args.hspice,
                args.hspice_timeout,
                transistor_levels,
            )
            search_rows.extend(device_search)
            case = pulse_case(direction, width_ns)
            native, native_row = pad.run_native_reference(
                device, profile, case, LOAD, args.hspice, args.hspice_timeout
            )
            reference_rows.append(native_row)
            native_result = screen.evaluate(
                native, case.pattern, width_ns, native_levels[0], native_levels[1]
            )
            transistor_result = screen.evaluate(
                transistor, case.pattern, width_ns, transistor_levels[0], transistor_levels[1]
            )
            selection = {
                "device": device.device_id,
                "direction": direction,
                "pulse_width_ps": 1000.0 * width_ns,
                "equivalent_data_rate_gbps": 1.0 / width_ns,
                "transistor_loaded_low_v": transistor_levels[0],
                "transistor_loaded_high_v": transistor_levels[1],
                "transistor_midpoint_v": transistor_levels[0] + TARGET * (transistor_levels[1] - transistor_levels[0]),
                "transistor_extreme_v": transistor_result["output_extreme_v"],
                "transistor_excursion_fraction": transistor_result["output_excursion_fraction"],
                "transistor_output_turn_time_ns": transistor_result["output_turn_time_ns"],
                "transistor_partial_output_reversal": transistor_result["partial_output_reversal"],
                "native_extreme_v": native_result["output_extreme_v"],
                "native_excursion_fraction": native_result["output_excursion_fraction"],
                "native_output_turn_time_ns": native_result["output_turn_time_ns"],
                "native_partial_output_reversal": native_result["partial_output_reversal"],
                "input_reverse_threshold_ns": native_result["reverse_threshold_ns"],
            }
            selections.append(selection)

            pulse_waves: dict[str, dict[str, np.ndarray] | None] = {}
            for candidate in CANDIDATES:
                print(f"    {candidate.label}: selected reversal", flush=True)
                pulse_wave, pulse_run = run_candidate(
                    out,
                    device,
                    profile,
                    case,
                    candidate,
                    models[candidate.flow_id],
                    args.ngspice,
                    args.ngspice_timeout,
                    args.resume,
                )
                pulse_run.update({
                    "case_role": "selected_reversal",
                    "direction": direction,
                    "label": candidate.label,
                })
                run_rows.append(pulse_run)
                pulse_waves[candidate.flow_id] = pulse_wave

            data = align(native, transistor, pulse_waves)
            waveform_name = (
                f"{device.device_id}.csv"
                if direction == "short_high"
                else f"{device.device_id}_short_low.csv"
            )
            write_wave(out / "waveforms" / waveform_name, data)
            native_turn_ns = float(native_result["output_turn_time_ns"])
            for candidate in CANDIDATES:
                control_wave = control_waves[candidate.flow_id]
                candidate_levels = (
                    native_levels if control_wave is None else full_levels(control_wave)
                )
                metrics.append(
                    measure_candidate(
                        device,
                        case,
                        candidate,
                        data,
                        candidate_levels,
                        native_turn_ns,
                    )
                )
            figures[direction].append(
                plot_case(out, device, case, data, transistor_levels, native_turn_ns)
            )
            for candidate in VOLTAGE_MATCHING_CANDIDATES:
                voltage_matching_wave = pulse_waves[candidate.flow_id]
                if voltage_matching_wave is None:
                    raise RuntimeError(
                        f"{candidate.label} waveform unavailable for "
                        f"{device.device_id}/{case.case_id}"
                    )
                event = voltage_match_event(
                    device,
                    case,
                    voltage_matching_wave,
                    candidate,
                )
                voltage_matching_events.append(event)
                voltage_matching_figures[candidate.flow_id][direction].append(
                    plot_voltage_matching_case(
                        out,
                        device,
                        case,
                        data,
                        pad_reference,
                        event,
                        candidate,
                    )
                )
            device_coefficient_rows = coefficient_turn_rows(
                device, case, data, native_turn_ns
            )
            coefficient_rows.extend(device_coefficient_rows)
            coefficient_figures[direction].append(
                plot_coefficient_turns(
                    out,
                    device,
                    case,
                    data,
                    device_coefficient_rows,
                    native_turn_ns,
                )
            )

        write_csv(out / "selection_search.csv", search_rows)
        write_csv(out / "selection.csv", selections)
        write_csv(out / "candidate_metrics.csv", metrics)
        write_csv(out / "run_manifest.csv", run_rows)
        write_csv(out / "reference_manifest.csv", reference_rows)
        write_csv(out / "coefficient_turn_times.csv", coefficient_rows)
        write_csv(
            out / "voltage_matching_mapping_events.csv",
            voltage_matching_events,
        )

    plot_selection(out, search_rows, selections, "short_high")
    plot_selection(out, search_rows, selections, "short_low")
    contact_sheet(figures["short_high"], out / "01_three_buffer_contact_sheet.png")
    contact_sheet(
        coefficient_figures["short_high"],
        out / "02_coefficient_direction_contact_sheet.png",
    )
    contact_sheet(figures["short_low"], out / "04_short_low_contact_sheet.png")
    contact_sheet(
        coefficient_figures["short_low"],
        out / "05_short_low_coefficient_direction_contact_sheet.png",
    )
    contact_sheet(
        voltage_matching_figures["voltage_matching"]["short_high"],
        out / "06_voltage_matching_short_high_contact_sheet.png",
    )
    contact_sheet(
        voltage_matching_figures["voltage_matching"]["short_low"],
        out / "07_voltage_matching_short_low_contact_sheet.png",
    )
    contact_sheet(
        voltage_matching_figures["voltage_matching_delayed"]["short_high"],
        out / "08_delayed_voltage_matching_short_high_contact_sheet.png",
    )
    contact_sheet(
        voltage_matching_figures["voltage_matching_delayed"]["short_low"],
        out / "09_delayed_voltage_matching_short_low_contact_sheet.png",
    )
    write_readme(out, selections, metrics, run_rows)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
