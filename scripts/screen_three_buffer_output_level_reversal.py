#!/usr/bin/env python3
"""Screen pulse widths for true pad-level interrupted transitions on three buffers."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
for path in (LOCAL_DEPS, ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import run_three_buffer_pad_matched_replay as pad
import run_three_buffer_realistic_pulse_campaign as base
from spice_tool_paths import default_hspice


DEFAULT_OUT = ROOT / "results" / "three_buffer_output_level_reversal_screen_2026-08-11"
EDGE_NS = 0.050
LOAD = (50.0, 2.0)
PARTIAL_LOW = 0.05
PARTIAL_HIGH = 0.95
WIDTHS_NS = {
    "io_buf": (0.25, 0.375, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00),
    "inv_chain": (0.050, 0.075, 0.100, 0.125, 0.150, 0.175, 0.200, 0.225, 0.250, 0.275, 0.300),
    "ex2": (0.100, 0.150, 0.200, 0.300, 0.400, 0.500, 0.600, 0.750, 1.000, 1.250),
}

BLACK = "#111111"
GRAY = "#777777"
BLUE = "#0072B2"
RED = "#CC3311"
GRID = "#D9DEE5"


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


def interp(wave: dict[str, np.ndarray], key: str, time_ns: float) -> float:
    return float(np.interp(time_ns, wave["time_ns"], wave[key]))


def level(wave: dict[str, np.ndarray], start_ns: float, stop_ns: float) -> float:
    mask = (wave["time_ns"] >= start_ns) & (wave["time_ns"] <= stop_ns)
    return float(np.median(wave["pad_v"][mask]))


def evaluate(
    wave: dict[str, np.ndarray],
    pattern: str,
    width_ns: float,
    low_v: float,
    high_v: float,
) -> dict[str, object]:
    swing = max(high_v - low_v, 1e-12)
    if pattern == "short_high":
        reverse_threshold_ns = 5.0 + width_ns + 0.5 * EDGE_NS
        mask = (wave["time_ns"] >= 5.0) & (wave["time_ns"] <= 12.0)
        local = wave["pad_v"][mask]
        local_t = wave["time_ns"][mask]
        index = int(np.argmax(local))
        extreme_v = float(local[index])
        excursion = (extreme_v - low_v) / swing
        command_progress = (interp(wave, "pad_v", reverse_threshold_ns) - low_v) / swing
        before = interp(wave, "pad_v", float(local_t[index]) - 0.02)
        after = interp(wave, "pad_v", float(local_t[index]) + 0.02)
        turns = before < extreme_v - 1e-5 and after < extreme_v - 1e-5
    else:
        reverse_threshold_ns = 10.0 + width_ns + 0.5 * EDGE_NS
        mask = (wave["time_ns"] >= 10.0) & (wave["time_ns"] <= 18.0)
        local = wave["pad_v"][mask]
        local_t = wave["time_ns"][mask]
        index = int(np.argmin(local))
        extreme_v = float(local[index])
        excursion = (high_v - extreme_v) / swing
        command_progress = (high_v - interp(wave, "pad_v", reverse_threshold_ns)) / swing
        before = interp(wave, "pad_v", float(local_t[index]) - 0.02)
        after = interp(wave, "pad_v", float(local_t[index]) + 0.02)
        turns = before > extreme_v + 1e-5 and after > extreme_v + 1e-5
    return {
        "reverse_threshold_ns": reverse_threshold_ns,
        "pad_at_reverse_v": interp(wave, "pad_v", reverse_threshold_ns),
        "pad_progress_at_reverse": command_progress,
        "output_extreme_v": extreme_v,
        "output_excursion_fraction": excursion,
        "output_turn_time_ns": float(local_t[index]),
        "output_direction_reversed": turns,
        "pad_mid_at_command": PARTIAL_LOW <= command_progress <= PARTIAL_HIGH,
        "partial_output_reversal": PARTIAL_LOW <= excursion <= PARTIAL_HIGH and turns,
    }


def choose(rows: list[dict[str, object]], device_id: str) -> dict[str, object]:
    candidates: list[tuple[tuple[float, ...], float, list[dict[str, object]]]] = []
    for width in WIDTHS_NS[device_id]:
        group = [
            row for row in rows
            if row["device"] == device_id and abs(float(row["width_ns"]) - width) < 1e-12
        ]
        native = [row for row in group if row["reference"] == "hspice_native_ibis"]
        transistor = [row for row in group if row["reference"] == "hspice_transistor"]
        if len(native) != 2 or len(transistor) != 2:
            continue
        native_pass = sum(bool(row["partial_output_reversal"]) for row in native)
        transistor_pass = sum(bool(row["partial_output_reversal"]) for row in transistor)
        shared_directions = [
            pattern for pattern in ("short_high", "short_low")
            if all(
                bool(row["partial_output_reversal"])
                for row in group if row["pattern"] == pattern
            )
        ]
        all_excursions = [float(row["output_excursion_fraction"]) for row in native + transistor]
        score = sum(abs(value - 0.5) for value in all_excursions)
        # Prefer a width that is a true partial output reversal in both directions
        # and both references. Fall back conservatively while keeping the gate counts.
        preferred_shared = "short_high" in shared_directions
        rank = (
            -int(preferred_shared),
            -len(shared_directions),
            -min(native_pass, transistor_pass),
            -(native_pass + transistor_pass),
            score,
        )
        candidates.append((rank, width, group, shared_directions))
    if not candidates:
        raise RuntimeError(f"No screening rows for {device_id}")
    rank, width, group, shared_directions = min(candidates, key=lambda item: item[0])
    return {
        "device": device_id,
        "selected_ui_ns": width,
        "selected_data_rate_gbps": 1.0 / width,
        "native_partial_directions": sum(
            bool(row["partial_output_reversal"])
            for row in group if row["reference"] == "hspice_native_ibis"
        ),
        "transistor_partial_directions": sum(
            bool(row["partial_output_reversal"])
            for row in group if row["reference"] == "hspice_transistor"
        ),
        "stress_direction": "+".join(shared_directions) if shared_directions else "none_shared",
        "selection_score": rank[4],
        "selection_gate": (
            "BOTH_REFERENCES_BOTH_DIRECTIONS" if len(shared_directions) == 2
            else "BOTH_REFERENCES_ONE_DIRECTION" if len(shared_directions) == 1
            else "BEST_AVAILABLE_PARTIAL_OUTPUT"
        ),
    }


def plot_device(out: Path, device_id: str, rows: list[dict[str, object]], selection: dict[str, object]) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(15.5, 5.6), constrained_layout=True, sharey=True)
    for axis, pattern, title in zip(axes, ("short_high", "short_low"), ("short high", "short low")):
        for reference, color, marker, label in (
            ("hspice_native_ibis", BLACK, "o", "HSPICE native IBIS"),
            ("hspice_transistor", GRAY, "s", "HSPICE transistor"),
        ):
            selected = sorted(
                [
                    row for row in rows
                    if row["device"] == device_id
                    and row["pattern"] == pattern
                    and row["reference"] == reference
                ],
                key=lambda row: float(row["width_ns"]),
            )
            axis.plot(
                [1000.0 * float(row["width_ns"]) for row in selected],
                [100.0 * float(row["output_excursion_fraction"]) for row in selected],
                color=color,
                marker=marker,
                linewidth=2.2,
                label=label,
            )
        axis.axhspan(100.0 * PARTIAL_LOW, 100.0 * PARTIAL_HIGH, color=BLUE, alpha=0.08)
        axis.axvline(1000.0 * float(selection["selected_ui_ns"]), color=RED, linestyle="--", linewidth=1.8)
        axis.set_title(title)
        axis.set_xlabel("pulse width / PRBS UI (ps)")
        axis.grid(True, color=GRID, linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("output excursion (% loaded swing)")
    axes[0].legend(loc="best")
    figure.suptitle(f"{device_id}: true output-level reversal screening", fontsize=17)
    path = out / "plots" / f"{device_id}_output_reversal_screen.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--timeout-s", type=int, default=240)
    args = parser.parse_args()
    out = args.study_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    pad.OUT = out

    rows: list[dict[str, object]] = []
    references: list[dict[str, object]] = []
    for device in base.DEVICES:
        profile = base.Profile("fast_5ps", "fast-edge IBIS", device.fast_ibis)
        control = base.PulseCase("long_control", EDGE_NS, "rise_fall", 10.0, 22.0, "long control")
        native_control, native_row = pad.run_native_reference(device, profile, control, LOAD, args.hspice, args.timeout_s)
        transistor_control, transistor_row = pad.run_transistor_reference(device, control, args.hspice, args.timeout_s)
        references.extend((native_row, transistor_row))
        levels = {
            "hspice_native_ibis": (level(native_control, 3.0, 4.8), level(native_control, 13.0, 14.8)),
            "hspice_transistor": (level(transistor_control, 3.0, 4.8), level(transistor_control, 13.0, 14.8)),
        }
        print(f"[{device.device_id}] {len(WIDTHS_NS[device.device_id])} widths", flush=True)
        for width in WIDTHS_NS[device.device_id]:
            for pattern in ("short_high", "short_low"):
                case = base.PulseCase(
                    f"{pattern}_output_screen_{base.width_tag(width)}",
                    EDGE_NS,
                    pattern,
                    width,
                    22.0,
                    "output reversal screen",
                )
                native, native_row = pad.run_native_reference(device, profile, case, LOAD, args.hspice, args.timeout_s)
                transistor, transistor_row = pad.run_transistor_reference(device, case, args.hspice, args.timeout_s)
                references.extend((native_row, transistor_row))
                for reference, wave in (
                    ("hspice_native_ibis", native),
                    ("hspice_transistor", transistor),
                ):
                    low_v, high_v = levels[reference]
                    rows.append({
                        "device": device.device_id,
                        "profile": profile.profile_id,
                        "pattern": pattern,
                        "width_ns": width,
                        "edge_ns": EDGE_NS,
                        "reference": reference,
                        "loaded_low_v": low_v,
                        "loaded_high_v": high_v,
                        **evaluate(wave, pattern, width, low_v, high_v),
                    })
        write_csv(out / "screening_metrics.csv", rows)
        write_csv(out / "reference_manifest.csv", references)

    selections = [choose(rows, device.device_id) for device in base.DEVICES]
    write_csv(out / "selected_ui.csv", selections)
    for selection in selections:
        plot_device(out, str(selection["device"]), rows, selection)

    lines = [
        "# Three-Buffer True Output-Level Reversal Screen",
        "",
        "A passing event must reverse direction after reaching 5%-95% of the loaded output swing and must not complete the original full swing.",
        "",
        "| Buffer | Selected UI | Data rate | Shared stress direction | Native partial directions | Transistor partial directions | Gate |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for row in selections:
        lines.append(
            f"| {row['device']} | {1000.0 * float(row['selected_ui_ns']):.0f} ps | "
            f"{float(row['selected_data_rate_gbps']):.3f} Gb/s | {row['stress_direction']} | {row['native_partial_directions']}/2 | "
            f"{row['transistor_partial_directions']}/2 | {row['selection_gate']} |"
        )
    lines.extend([
        "",
        "- `screening_metrics.csv`: pad-at-command and final output-excursion evidence for every width.",
        "- `selected_ui.csv`: per-buffer UI selected for the follow-on PRBS study.",
        "- `plots/`: output excursion versus pulse width for native IBIS and transistor references.",
    ])
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
