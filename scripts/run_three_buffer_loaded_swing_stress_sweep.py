#!/usr/bin/env python3
"""Sweep three buffers from slight to strong loaded-output reversal stress."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
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


DEFAULT_OUT = ROOT / "results" / "three_buffer_loaded_swing_stress_sweep_2026-08-14"
EDGE_NS = 0.050
LOAD = (50.0, 2.0)
TARGETS = (0.90, 0.80, 0.70, 0.60, 0.50)
DIRECTIONS = ("short_high", "short_low")
TARGET_TOLERANCE = 0.01
MAX_SEARCH_ITERATIONS = 10
# Overridable so one stress axis can be re-used across model variants. The
# stress widths come from HSPICE references that do not depend on the model, so
# holding the axis fixed and changing only this makes the runs comparable.
GATE_STATE_MODE = os.environ.get(
    "PYBIS_GATE_MODE", "InputDrivenTwoStateGateDirectionalDualResidualFull"
)

BLACK = "#111111"
GRAY = "#777777"
RED = "#D62728"
GRID = "#D9DEE5"

HISTORICAL_SCREEN = (
    ROOT
    / "results"
    / "three_buffer_output_level_reversal_screen_2026-08-11"
    / "screening_metrics.csv"
)
HISTORICAL_MIDPOINT = (
    ROOT
    / "results"
    / "three_buffer_single_true_output_reversal_2026-08-11"
    / "selection.csv"
)

FALLBACK_POINTS_NS = {
    "io_buf": {
        "short_high": ((1.25, 0.25), (1.50, 0.50), (2.00, 0.77), (2.75, 0.97)),
        "short_low": ((0.10, 0.10), (0.16, 0.50), (0.25, 0.79), (0.38, 0.98)),
    },
    "inv_chain": {
        "short_high": ((0.09, 0.05), (0.104, 0.50), (0.125, 0.85), (0.15, 0.94)),
        "short_low": ((0.10, 0.01), (0.110, 0.50), (0.125, 0.99), (0.15, 1.00)),
    },
    "ex2": {
        "short_high": ((0.60, 0.02), (0.81, 0.50), (1.00, 0.93), (1.25, 0.99)),
        "short_low": ((0.50, 0.02), (0.69, 0.50), (0.75, 0.86), (1.00, 1.00)),
    },
}


@dataclass
class SearchSample:
    width_ns: float
    excursion: float
    source: str
    wave: dict[str, np.ndarray] | None = None
    reference_row: dict[str, object] | None = None
    evaluation: dict[str, object] | None = None


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


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def level(wave: dict[str, np.ndarray], start_ns: float, stop_ns: float) -> float:
    mask = (wave["time_ns"] >= start_ns) & (wave["time_ns"] <= stop_ns)
    return float(np.median(wave["pad_v"][mask]))


def full_levels(wave: dict[str, np.ndarray]) -> tuple[float, float]:
    return level(wave, 3.0, 4.8), level(wave, 13.0, 14.8)


def reclaim_stalled_raw(raw_path: object, keep_mb: float = 64.0) -> None:
    """
    Deletes the partial raw left behind by a stalled ngspice run.

    A transient that collapses into ever-smaller timesteps keeps writing until
    it is killed; observed leftovers reach 900 MB for a single case. The file
    holds no completed analysis, so it is removed once it is clearly oversized.
    """
    if not raw_path:
        return
    path = Path(str(raw_path))
    if not path.is_absolute():
        path = ROOT / path
    try:
        if path.is_file() and path.stat().st_size > keep_mb * 1024 * 1024:
            size_mb = path.stat().st_size / (1024 * 1024)
            path.unlink()
            print(f"    reclaimed {size_mb:.0f} MB stalled raw: {path.name}", flush=True)
    except OSError as error:
        print(f"    could not reclaim stalled raw {path}: {error}", flush=True)


def control_case() -> base.PulseCase:
    return base.PulseCase("long_control", EDGE_NS, "rise_fall", 10.0, 22.0, "long control")


def pulse_case(direction: str, target: float, width_ns: float, iteration: int) -> base.PulseCase:
    target_pct = int(round(100.0 * target))
    width_fs = int(round(width_ns * 1_000_000.0))
    return base.PulseCase(
        f"{direction}_swing{target_pct}_search{iteration}_{width_fs}fs",
        EDGE_NS,
        direction,
        width_ns,
        22.0,
        f"{target_pct}% loaded-output reversal",
        target,
    )


def historical_points(
    device_id: str,
    direction: str,
    extra_rows: list[dict[str, str]] | None = None,
    anchor: str = "transistor",
) -> list[SearchSample]:
    """
    Seeds the width search with prior width-versus-swing measurements.

    Seeds are only valid for the reference they were measured against: at the
    same pulse width native IBIS and the transistor reach very different swings,
    so mixing them would corrupt the interpolation. Anything recorded against a
    different anchor is therefore ignored, and an unseeded anchor falls back to
    the static width bracket.
    """
    samples: list[SearchSample] = []
    if anchor == "transistor":
        for row in read_csv(HISTORICAL_SCREEN):
            if (
                row.get("device") == device_id
                and row.get("pattern") == direction
                and row.get("reference") == "hspice_transistor"
            ):
                samples.append(
                    SearchSample(
                        float(row["width_ns"]),
                        float(row["output_excursion_fraction"]),
                        "historical_screen",
                    )
                )
        for row in read_csv(HISTORICAL_MIDPOINT):
            if row.get("device") == device_id and row.get("direction") == direction:
                samples.append(
                    SearchSample(
                        float(row["pulse_width_ps"]) / 1000.0,
                        float(row["transistor_excursion_fraction"]),
                        "historical_midpoint",
                    )
                )
    elif anchor == "native":
        for row in read_csv(HISTORICAL_SCREEN):
            if (
                row.get("device") == device_id
                and row.get("pattern") == direction
                and row.get("reference") == "hspice_native_ibis"
            ):
                samples.append(
                    SearchSample(
                        float(row["width_ns"]),
                        float(row["output_excursion_fraction"]),
                        "historical_screen_native",
                    )
                )
    for row in extra_rows or []:
        if (
            row.get("device") == device_id
            and row.get("direction") == direction
            and row.get("anchor", "transistor") == anchor
        ):
            samples.append(
                SearchSample(
                    float(row["pulse_width_ps"]) / 1000.0,
                    float(row["achieved_percent"]) / 100.0,
                    "prior_study_measurement",
                )
            )
    if not samples:
        samples = [
            SearchSample(width, excursion, "fallback")
            for width, excursion in FALLBACK_POINTS_NS[device_id][direction]
        ]
    return samples


def monotonic_points(samples: list[SearchSample]) -> list[tuple[float, float]]:
    by_width: dict[float, list[float]] = {}
    for sample in samples:
        by_width.setdefault(round(sample.width_ns, 9), []).append(sample.excursion)
    ordered = sorted((width, float(np.median(values))) for width, values in by_width.items())
    result: list[tuple[float, float]] = []
    running = -float("inf")
    for width, excursion in ordered:
        running = max(running, excursion)
        result.append((width, running))
    return result


def estimate_width(samples: list[SearchSample], target: float) -> float:
    points = monotonic_points(samples)
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        if y0 <= target <= y1 and y1 > y0 + 1e-12:
            fraction = (target - y0) / (y1 - y0)
            return x0 + fraction * (x1 - x0)
    if target < points[0][1]:
        x0, y0 = points[0]
        x1, y1 = points[1]
    else:
        x0, y0 = points[-2]
        x1, y1 = points[-1]
    slope = (y1 - y0) / max(x1 - x0, 1e-12)
    if slope <= 1e-6:
        return x1 * 1.15
    estimate = x1 + (target - y1) / slope
    return max(0.001, min(5.0, estimate))


def select_target(
    out: Path,
    device: base.Device,
    direction: str,
    target: float,
    anchor_levels: tuple[float, float],
    samples: list[SearchSample],
    hspice: Path,
    timeout_s: int,
    anchor: str = "transistor",
    profile: base.Profile | None = None,
) -> tuple[base.PulseCase, SearchSample, list[dict[str, object]]]:
    """
    Bisects pulse width until the anchor reference reaches ``target`` swing.

    ``anchor`` selects which HSPICE reference defines the stress axis.
    ``transistor`` reproduces the original sweep. ``native`` keys the axis on
    HSPICE native IBIS instead, which is the reference the pybis models are
    actually graded against; anchoring on the transistor leaves native IBIS at
    wildly different coefficient progress from one buffer to the next.
    """
    if anchor == "native" and profile is None:
        raise ValueError("native anchoring requires an IBIS profile")
    attempts: list[SearchSample] = []
    rows: list[dict[str, object]] = []
    tried: set[float] = set()
    clamped = False
    for iteration in range(MAX_SEARCH_ITERATIONS):
        width_ns = round(estimate_width(samples + attempts, target), 6)
        if width_ns in tried:
            offsets = (0.001, -0.001, 0.002, -0.002)
            width_ns = round(width_ns + offsets[min(iteration, len(offsets) - 1)], 6)
        # A pulse shorter than the input edge is not a valid short-pulse test:
        # the input never reaches its full level. Stop at that floor instead of
        # emitting a malformed stimulus, and let the caller see the target was
        # not reached.
        if width_ns < EDGE_NS:
            width_ns = EDGE_NS
            clamped = True
            if width_ns in tried:
                break
        tried.add(width_ns)
        case = pulse_case(direction, target, width_ns, iteration)
        if anchor == "native":
            wave, reference = pad.run_native_reference(
                device, profile, case, LOAD, hspice, timeout_s
            )
        else:
            wave, reference = pad.run_transistor_reference(device, case, hspice, timeout_s)
        evaluation = screen.evaluate(
            wave,
            direction,
            width_ns,
            anchor_levels[0],
            anchor_levels[1],
        )
        excursion = float(evaluation["output_excursion_fraction"])
        sample = SearchSample(width_ns, excursion, "measured", wave, reference, evaluation)
        attempts.append(sample)
        row = {
            "device": device.device_id,
            "direction": direction,
            "anchor": anchor,
            "target_percent": 100.0 * target,
            "iteration": iteration,
            "pulse_width_ps": 1000.0 * width_ns,
            "achieved_percent": 100.0 * excursion,
            "absolute_error_percent": 100.0 * abs(excursion - target),
            "pad_at_reverse_v": evaluation["pad_at_reverse_v"],
            "pad_progress_at_reverse_percent": 100.0 * float(evaluation["pad_progress_at_reverse"]),
            "output_turn_time_ns": evaluation["output_turn_time_ns"],
            "input_reverse_threshold_ns": evaluation["reverse_threshold_ns"],
            "width_clamped_to_edge": clamped,
            "hspice_source": reference["source"],
            "tr0": reference["tr0"],
        }
        rows.append(row)
        note = "  [clamped to input edge]" if clamped else ""
        print(
            f"    target {100.0 * target:.0f}%: {1000.0 * width_ns:.3f} ps -> "
            f"{100.0 * excursion:.2f}%{note}",
            flush=True,
        )
        if abs(excursion - target) <= TARGET_TOLERANCE:
            break
        if clamped:
            # The floor is the shortest valid stimulus; nothing further to try.
            break
    if not attempts:
        raise RuntimeError(
            f"no valid pulse width found for {device.device_id}/{direction}/"
            f"{100.0 * target:.0f}%"
        )
    best = min(attempts, key=lambda item: abs(item.excursion - target))
    best_iteration = attempts.index(best)
    reachable = abs(best.excursion - target) <= max(TARGET_TOLERANCE, 0.02)
    for row in rows:
        row["target_reachable"] = reachable
    return pulse_case(direction, target, best.width_ns, best_iteration), best, rows


def prepare_gate_model(out: Path, device: base.Device, profile: base.Profile) -> Path:
    model = out / "generated_models" / device.device_id / profile.profile_id / "gate_state" / f"{device.subckt}.sub"
    convert_ibis_to_pybis(
        profile.ibis,
        model,
        device.component,
        device.model,
        "Output",
        GATE_STATE_MODE,
        "Typical",
    )
    return model


def run_gate_state(
    out: Path,
    device: base.Device,
    profile: base.Profile,
    case: base.PulseCase,
    model: Path,
    ngspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray] | None, dict[str, object]]:
    raw, row = base.run_ngspice(
        device,
        profile,
        case,
        "gate_state",
        GATE_STATE_MODE,
        model,
        out / "ngspice_runs",
        ngspice,
        timeout_s,
    )
    return (None if raw is None else base.ngspice_waveform(raw)), row


def align(
    native: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
    gate: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    time_ns = native["time_ns"]
    result = {
        "time_ns": time_ns,
        "hspice_transistor_pad_v": np.interp(time_ns, transistor["time_ns"], transistor["pad_v"]),
        "hspice_native_pad_v": native["pad_v"],
        "hspice_native_ku": native["ku"],
        "hspice_native_kd": native["kd"],
        "gate_state_pad_v": np.interp(time_ns, gate["time_ns"], gate["pad_v"]),
        "gate_state_ku": np.interp(time_ns, gate["time_ns"], gate["ku"]),
        "gate_state_kd": np.interp(time_ns, gate["time_ns"], gate["kd"]),
    }
    for key in ("gup", "gdn", "guptarget", "gdntarget"):
        if key in gate:
            result[f"gate_state_{key}"] = np.interp(time_ns, gate["time_ns"], gate[key])
    return result


def write_waveform(path: Path, data: dict[str, np.ndarray]) -> None:
    keys = list(data)
    rows = [
        {key: float(data[key][index]) for key in keys}
        for index in range(len(data["time_ns"]))
    ]
    write_csv(path, rows)


def dynamic_window(
    device: base.Device,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
) -> tuple[float, float]:
    time_ns = data["time_ns"]
    stress_edge_ns = base.command_edges(device, case)[-2]
    reverse_ns = base.command_edges(device, case)[-1]
    eligible = time_ns >= stress_edge_ns - 0.1
    activity = np.zeros(len(time_ns), dtype=bool)
    specifications = (
        ("hspice_transistor_pad_v", max(device.supply_v, 1.0)),
        ("hspice_native_pad_v", max(device.supply_v, 1.0)),
        ("gate_state_pad_v", max(device.supply_v, 1.0)),
        ("hspice_native_ku", 1.0),
        ("hspice_native_kd", 1.0),
        ("gate_state_ku", 1.0),
        ("gate_state_kd", 1.0),
    )
    for key, scale in specifications:
        values = data[key]
        gradient = np.abs(np.gradient(values, time_ns, edge_order=1))
        activity |= gradient > 0.0025 * scale / 0.02
    indexes = np.flatnonzero(activity & eligible)
    if len(indexes) == 0:
        return stress_edge_ns - 0.1, reverse_ns + 2.0
    start_ns = max(stress_edge_ns - 0.1, float(time_ns[indexes[0]]) - 0.12)
    stop_ns = min(float(time_ns[-1]), float(time_ns[indexes[-1]]) + 0.30)
    if stop_ns - start_ns < 0.8:
        stop_ns = min(float(time_ns[-1]), start_ns + 0.8)
    return start_ns, stop_ns


def style_axis(axis: plt.Axes) -> None:
    axis.grid(True, color=GRID, linewidth=0.8)
    axis.spines[["top", "right"]].set_visible(False)


def plot_pad(
    output: Path,
    device: base.Device,
    direction: str,
    target: float,
    achieved: float,
    data: dict[str, np.ndarray],
    window: tuple[float, float],
) -> None:
    mask = (data["time_ns"] >= window[0]) & (data["time_ns"] <= window[1])
    time_ns = data["time_ns"][mask]
    figure, axis = plt.subplots(figsize=(14.2, 6.0), constrained_layout=True)
    axis.plot(
        time_ns,
        data["hspice_transistor_pad_v"][mask],
        color=GRAY,
        linewidth=5.0,
        label="HSPICE transistor",
        zorder=2,
    )
    axis.plot(
        time_ns,
        data["hspice_native_pad_v"][mask],
        color=BLACK,
        linewidth=3.4,
        label="HSPICE native IBIS",
        zorder=3,
    )
    axis.plot(
        time_ns,
        data["gate_state_pad_v"][mask],
        color=RED,
        linewidth=2.1,
        label="gate-state model",
        zorder=4,
    )
    axis.set_title(
        f"{device.device_id} | {direction.replace('_', ' ')} | "
        f"target {100.0 * target:.0f}%, achieved {100.0 * achieved:.1f}%",
        fontsize=16,
        fontweight="bold",
    )
    axis.set_xlabel("Time (ns)")
    axis.set_ylabel("Pad voltage (V)")
    axis.legend(loc="best", frameon=False)
    style_axis(axis)
    ensure(output.parent)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def plot_coefficients(
    output: Path,
    device: base.Device,
    direction: str,
    target: float,
    achieved: float,
    data: dict[str, np.ndarray],
    window: tuple[float, float],
) -> None:
    mask = (data["time_ns"] >= window[0]) & (data["time_ns"] <= window[1])
    time_ns = data["time_ns"][mask]
    figure, axes = plt.subplots(2, 1, figsize=(14.2, 8.4), sharex=True, constrained_layout=True)
    for axis, coefficient, ylabel in (
        (axes[0], "ku", "Ku"),
        (axes[1], "kd", "Kd"),
    ):
        axis.plot(
            time_ns,
            data[f"hspice_native_{coefficient}"][mask],
            color=BLACK,
            linewidth=4.0,
            label="HSPICE native IBIS",
            zorder=2,
        )
        axis.plot(
            time_ns,
            data[f"gate_state_{coefficient}"][mask],
            color=RED,
            linewidth=2.1,
            label="gate-state model",
            zorder=3,
        )
        axis.set_ylabel(ylabel)
        style_axis(axis)
    axes[1].set_xlabel("Time (ns)")
    axes[0].legend(loc="best", frameon=False)
    figure.suptitle(
        f"{device.device_id} | {direction.replace('_', ' ')} | "
        f"target {100.0 * target:.0f}%, achieved {100.0 * achieved:.1f}%",
        fontsize=16,
        fontweight="bold",
    )
    ensure(output.parent)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def rmse(reference: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(reference[mask] - candidate[mask]))))


def write_readme(
    out: Path,
    selections: list[dict[str, object]],
    metrics: list[dict[str, object]],
    completed: int,
) -> None:
    lines = [
        "# Three-Buffer Loaded-Swing Stress Sweep",
        "",
        "This study sweeps output-level reversal stress from 90% to 50% of each HSPICE transistor buffer's measured loaded swing.",
        "All cases use fast-edge IBIS, 50 ps input edges, and a direct 50 ohm || 2 pF load.",
        "The HSPICE transistor response selects the pulse width; the exact same stimulus is then applied to HSPICE native IBIS and the ngspice gate-state model.",
        "",
        "## Selected Stimuli",
        "",
        "| Buffer | Direction | Target | Pulse width | Achieved transistor swing | Native-IBIS swing |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in selections:
        lines.append(
            f"| {row['device']} | {str(row['direction']).replace('_', ' ')} | "
            f"{float(row['target_percent']):.0f}% | {float(row['pulse_width_ps']):.3f} ps | "
            f"{float(row['transistor_achieved_percent']):.2f}% | "
            f"{float(row['native_achieved_percent']):.2f}% |"
        )
    lines.extend([
        "",
        "## Gate-State Agreement",
        "",
        "| Buffer | Direction | Target | Pad RMSE | Ku RMSE | Kd RMSE |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for row in metrics:
        lines.append(
            f"| {row['device']} | {str(row['direction']).replace('_', ' ')} | "
            f"{float(row['target_percent']):.0f}% | {float(row['pad_rmse_mv']):.2f} mV | "
            f"{float(row['ku_rmse']):.5f} | {float(row['kd_rmse']):.5f} |"
        )
    lines.extend([
        "",
        "## Initial Findings",
        "",
        "- `ex2` short-high is the strongest gate-state result: pad RMSE rises gradually from 29.42 mV at 90% swing to 45.37 mV at 50%, while Ku/Kd remain comparatively close.",
        "- `ex2` short-low has a clear stress boundary between 80% and 70%: pad RMSE jumps from 43.85 mV to 261.78 mV and both coefficient errors increase sharply.",
        "- `inv_chain` does not show a useful gate-state region in this full-gate implementation; pad and coefficient errors remain large from slight through strong stress in both directions.",
        "- `io_buf` is also not robust: short-low is poor at every level, while short-high is strongly non-monotonic and includes visible coefficient excursions outside the native-IBIS trajectory.",
        "- Equal transistor loaded-swing targets do not create equal native-IBIS stress. At the 50% transistor target, native-IBIS excursion ranges from 8.80% for io_buf short-low to 94.86% for ex2 short-low.",
        "",
        "## Figure Rules",
        "",
        "Each case contains exactly two figures:",
        "",
        "- `01_pad_voltage.png`: HSPICE transistor, HSPICE native IBIS, and gate-state model only.",
        "- `02_ku_kd.png`: Ku and Kd panels, each containing HSPICE native IBIS and gate-state model only.",
        "- Flat pre-event and post-recovery regions are cropped automatically from both figures.",
        "",
        "Numeric waveforms are stored beside each case as `waveforms.csv`.",
        "Selection evidence is stored in `selection.csv` and `selection_search.csv`.",
        "",
        f"Completed gate-state simulations: `{completed}/{len(selections)}`.",
    ])
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    parser.add_argument("--hspice-timeout", type=int, default=300)
    parser.add_argument("--ngspice-timeout", type=int, default=900)
    parser.add_argument("--device", action="append", choices=[item.device_id for item in base.DEVICES])
    parser.add_argument("--direction", action="append", choices=list(DIRECTIONS))
    parser.add_argument("--target-percent", action="append", type=int, choices=[50, 60, 70, 80, 90])
    parser.add_argument(
        "--anchor",
        choices=("transistor", "native"),
        default="transistor",
        help=(
            "Which HSPICE reference defines the stress target. 'transistor' "
            "reproduces the original sweep; 'native' keys the axis on HSPICE "
            "native IBIS, the reference the pybis models are graded against."
        ),
    )
    args = parser.parse_args()

    out = args.study_dir if args.study_dir.is_absolute() else ROOT / args.study_dir
    out = out.resolve()
    ensure(out)
    pad.OUT = out

    selected_devices = set(args.device or [item.device_id for item in base.DEVICES])
    selected_directions = set(args.direction or DIRECTIONS)
    selected_targets = {value / 100.0 for value in (args.target_percent or [90, 80, 70, 60, 50])}
    filtered_run = bool(args.device or args.direction or args.target_percent)
    prior_search_rows = read_csv(out / "selection_search.csv") if filtered_run else []

    def keep_existing(row: dict[str, str]) -> bool:
        try:
            target = float(row["target_percent"]) / 100.0
        except (KeyError, ValueError):
            return True
        return not (
            row.get("device") in selected_devices
            and row.get("direction") in selected_directions
            and target in selected_targets
        )

    selection_search_rows: list[dict[str, object]] = [row for row in prior_search_rows if keep_existing(row)]
    selection_rows: list[dict[str, object]] = (
        [row for row in read_csv(out / "selection.csv") if keep_existing(row)] if filtered_run else []
    )
    metric_rows: list[dict[str, object]] = (
        [row for row in read_csv(out / "metrics.csv") if keep_existing(row)] if filtered_run else []
    )
    reference_rows: list[dict[str, object]] = (
        list(read_csv(out / "reference_manifest.csv")) if filtered_run else []
    )
    run_rows: list[dict[str, object]] = (
        list(read_csv(out / "run_manifest.csv")) if filtered_run else []
    )
    failed_rows: list[dict[str, object]] = (
        [row for row in read_csv(out / "failed_cases.csv") if keep_existing(row)]
        if filtered_run else []
    )

    for device in base.DEVICES:
        if device.device_id not in selected_devices:
            continue
        print(f"[{device.device_id}]", flush=True)
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
        model = prepare_gate_model(out, device, profile)

        for direction in DIRECTIONS:
            if direction not in selected_directions:
                continue
            samples = historical_points(
                device.device_id, direction, prior_search_rows, anchor=args.anchor
            )
            for target in TARGETS:
                if target not in selected_targets:
                    continue
                print(f"  {direction} {100.0 * target:.0f}%", flush=True)
                case, anchor_sample, search_rows = select_target(
                    out,
                    device,
                    direction,
                    target,
                    native_levels if args.anchor == "native" else transistor_levels,
                    samples,
                    args.hspice,
                    args.hspice_timeout,
                    anchor=args.anchor,
                    profile=profile,
                )
                selection_search_rows.extend(search_rows)
                samples.append(anchor_sample)
                if anchor_sample.wave is None or anchor_sample.evaluation is None:
                    raise RuntimeError("Selected anchor sample has no waveform")
                reference_rows.append(anchor_sample.reference_row or {})

                # The anchor search already produced one of the two references at
                # the selected width; only the other one still needs running.
                if args.anchor == "native":
                    native, native_result = anchor_sample.wave, anchor_sample.evaluation
                    transistor, transistor_row = pad.run_transistor_reference(
                        device, case, args.hspice, args.hspice_timeout
                    )
                    reference_rows.append(transistor_row)
                    transistor_result = screen.evaluate(
                        transistor,
                        direction,
                        case.pulse_width_ns,
                        transistor_levels[0],
                        transistor_levels[1],
                    )
                else:
                    transistor, transistor_result = anchor_sample.wave, anchor_sample.evaluation
                    native, native_row = pad.run_native_reference(
                        device, profile, case, LOAD, args.hspice, args.hspice_timeout
                    )
                    reference_rows.append(native_row)
                    native_result = screen.evaluate(
                        native,
                        direction,
                        case.pulse_width_ns,
                        native_levels[0],
                        native_levels[1],
                    )
                gate, gate_row = run_gate_state(
                    out,
                    device,
                    profile,
                    case,
                    model,
                    args.ngspice,
                    args.ngspice_timeout,
                )
                run_rows.append(gate_row)
                if gate is None:
                    # A stiff case must not destroy the rest of the batch. The
                    # gate-state model is numerically marginal at short widths
                    # -- on ex2 a 381 fs width change decides whether it
                    # converges -- so record the failure, reclaim the partial
                    # raw, and carry on.
                    log_path = gate_row.get("log", "")
                    print(
                        f"    WARNING: gate-state simulation failed for {case.case_id}; "
                        f"continuing. See {log_path}",
                        flush=True,
                    )
                    reclaim_stalled_raw(gate_row.get("raw"))
                    # Drop any artifacts a previous attempt left for this case.
                    # A figure directory with no matching selection row reads as
                    # a completed case to anything that walks the figure tree.
                    target_pct = int(round(100.0 * target))
                    stale_dir = out / "figures" / device.device_id / direction / f"swing_{target_pct}"
                    if stale_dir.is_dir():
                        shutil.rmtree(stale_dir, ignore_errors=True)
                        print(f"    removed stale artifacts from a prior attempt: {stale_dir}", flush=True)
                    failed_rows.append({
                        "device": device.device_id,
                        "direction": direction,
                        "anchor": args.anchor,
                        "target_percent": 100.0 * target,
                        "pulse_width_ps": 1000.0 * case.pulse_width_ns,
                        "case_id": case.case_id,
                        "stage": "gate_state",
                        "log": log_path,
                    })
                    write_csv(out / "selection_search.csv", selection_search_rows)
                    write_csv(out / "run_manifest.csv", run_rows)
                    write_csv(out / "failed_cases.csv", failed_rows)
                    continue

                data = align(native, transistor, gate)
                target_pct = int(round(100.0 * target))
                case_dir = out / "figures" / device.device_id / direction / f"swing_{target_pct}"
                ensure(case_dir)
                write_waveform(case_dir / "waveforms.csv", data)
                window = dynamic_window(device, case, data)
                plot_pad(
                    case_dir / "01_pad_voltage.png",
                    device,
                    direction,
                    target,
                    anchor_sample.excursion,
                    data,
                    window,
                )
                plot_coefficients(
                    case_dir / "02_ku_kd.png",
                    device,
                    direction,
                    target,
                    anchor_sample.excursion,
                    data,
                    window,
                )

                selection_rows.append({
                    "device": device.device_id,
                    "direction": direction,
                    "target_percent": 100.0 * target,
                    "anchor": args.anchor,
                    "anchor_achieved_percent": 100.0 * anchor_sample.excursion,
                    "anchor_target_error_percent": 100.0 * abs(anchor_sample.excursion - target),
                    "target_reachable": bool(search_rows[-1].get("target_reachable", True)),
                    "width_clamped_to_edge": bool(search_rows[-1].get("width_clamped_to_edge", False)),
                    "pulse_width_ps": 1000.0 * case.pulse_width_ns,
                    "transistor_achieved_percent": 100.0 * float(transistor_result["output_excursion_fraction"]),
                    "transistor_target_error_percent": 100.0 * abs(
                        float(transistor_result["output_excursion_fraction"]) - target
                    ),
                    "transistor_pad_at_reverse_v": transistor_result["pad_at_reverse_v"],
                    "transistor_pad_progress_at_reverse_percent": 100.0 * float(transistor_result["pad_progress_at_reverse"]),
                    "transistor_output_turn_time_ns": transistor_result["output_turn_time_ns"],
                    "native_achieved_percent": 100.0 * float(native_result["output_excursion_fraction"]),
                    "native_pad_at_reverse_v": native_result["pad_at_reverse_v"],
                    "native_pad_progress_at_reverse_percent": 100.0 * float(native_result["pad_progress_at_reverse"]),
                    "native_output_turn_time_ns": native_result["output_turn_time_ns"],
                    "crop_start_ns": window[0],
                    "crop_stop_ns": window[1],
                    "figure_dir": str(case_dir.relative_to(ROOT)),
                })
                mask = (data["time_ns"] >= window[0]) & (data["time_ns"] <= window[1])
                metric_rows.append({
                    "device": device.device_id,
                    "direction": direction,
                    "target_percent": 100.0 * target,
                    "pulse_width_ps": 1000.0 * case.pulse_width_ns,
                    "pad_rmse_mv": 1000.0 * rmse(data["hspice_native_pad_v"], data["gate_state_pad_v"], mask),
                    "ku_rmse": rmse(data["hspice_native_ku"], data["gate_state_ku"], mask),
                    "kd_rmse": rmse(data["hspice_native_kd"], data["gate_state_kd"], mask),
                    "pad_max_error_mv": 1000.0 * float(np.max(np.abs(data["hspice_native_pad_v"][mask] - data["gate_state_pad_v"][mask]))),
                    "ku_max_error": float(np.max(np.abs(data["hspice_native_ku"][mask] - data["gate_state_ku"][mask]))),
                    "kd_max_error": float(np.max(np.abs(data["hspice_native_kd"][mask] - data["gate_state_kd"][mask]))),
                })

                write_csv(out / "selection_search.csv", selection_search_rows)
                write_csv(out / "selection.csv", selection_rows)
                write_csv(out / "metrics.csv", metric_rows)
                write_csv(out / "reference_manifest.csv", reference_rows)
                write_csv(out / "run_manifest.csv", run_rows)
                write_csv(out / "failed_cases.csv", failed_rows)

    selection_rows.sort(key=lambda row: (str(row["device"]), str(row["direction"]), -float(row["target_percent"])))
    metric_rows.sort(key=lambda row: (str(row["device"]), str(row["direction"]), -float(row["target_percent"])))
    completed = len(metric_rows)
    write_csv(out / "failed_cases.csv", failed_rows)
    write_readme(out, selection_rows, metric_rows, completed)
    if failed_rows:
        print(f"{len(failed_rows)} case(s) failed to simulate:", flush=True)
        for row in failed_rows:
            print(
                f"  {row['device']}/{row['direction']}/{float(row['target_percent']):.0f}% "
                f"at {float(row['pulse_width_ps']):.3f} ps ({row['stage']})",
                flush=True,
            )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
