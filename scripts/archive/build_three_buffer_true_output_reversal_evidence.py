#!/usr/bin/env python3
"""Build clean isolated-pulse evidence for true output-level reversals."""

from __future__ import annotations

import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
if str(LOCAL_DEPS) not in sys.path:
    sys.path.insert(0, str(LOCAL_DEPS))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


STUDY = ROOT / "results" / "three_buffer_pad_matched_replay_v2_true_output_2026-08-11"
SCREEN = ROOT / "results" / "three_buffer_output_level_reversal_screen_2026-08-11"
CASES = {
    "io_buf": (1.75, "short_high_custom_1p75ns"),
    "inv_chain": (0.100, "short_high_custom_100ps"),
    "ex2": (0.750, "short_high_custom_750ps"),
}

BLACK = "#111111"
GRAY = "#777777"
RED = "#CC3311"
BLUE = "#0072B2"
PURPLE = "#7B2CBF"
ORANGE = "#E69F00"
GRID = "#D9DEE5"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
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


def load_wave(path: Path) -> dict[str, np.ndarray]:
    values = np.genfromtxt(path, delimiter=",", names=True, dtype=float, encoding="utf-8")
    return {name: np.asarray(values[name], dtype=float) for name in values.dtype.names or ()}


def plot_case(
    device: str,
    width_ns: float,
    data: dict[str, np.ndarray],
    turn_ns: float,
    output: Path,
) -> None:
    reverse_ns = 5.0 + width_ns + 0.025
    start_ns = max(0.0, 5.0 - max(0.2, 0.25 * width_ns))
    stop_ns = min(float(data["time_ns"][-1]), max(turn_ns + max(0.6, width_ns), reverse_ns + 3.0 * width_ns))
    mask = (data["time_ns"] >= start_ns) & (data["time_ns"] <= stop_ns)
    time = data["time_ns"][mask] - reverse_ns
    figure, axes = plt.subplots(4, 1, figsize=(15.5, 9.5), sharex=True, constrained_layout=True)
    axes[0].plot(time, data["input_v"][mask], color=BLUE, linewidth=2.0)
    axes[0].set_ylabel("input (V)")
    axes[1].plot(time, data["hspice_native_pad_v"][mask], color=BLACK, linewidth=3.5, label="HSPICE native IBIS")
    axes[1].plot(time, data["hspice_transistor_pad_v"][mask], color=GRAY, linewidth=2.8, label="HSPICE transistor")
    axes[1].plot(time, data["pad_voltage_pad_v"][mask], color=RED, linewidth=2.1, label="pad-match V2")
    axes[1].set_ylabel("pad (V)")
    for axis, signal in ((axes[2], "ku"), (axes[3], "kd")):
        axis.plot(time, data[f"hspice_native_{signal}"][mask], color=BLACK, linewidth=3.5, label="HSPICE native IBIS")
        axis.plot(time, data[f"pad_voltage_{signal}"][mask], color=RED, linewidth=2.1, label="pad-match V2")
        axis.set_ylabel(signal.capitalize())
    axes[3].axhline(0.0, color="#999999", linewidth=0.8)
    axes[3].set_xlabel("time from input reverse threshold (ns)")
    turn_relative = turn_ns - reverse_ns
    for axis in axes:
        axis.axvline(0.0, color=PURPLE, linestyle="--", linewidth=1.5)
        axis.axvline(turn_relative, color=ORANGE, linestyle=":", linewidth=1.6)
        axis.grid(True, color=GRID, linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[1].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.985, 0.985), ncol=3)
    figure.suptitle(f"{device} | true output reversal | {width_ns * 1000:.0f} ps pulse", fontsize=17)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def main() -> int:
    screen_rows = read_csv(SCREEN / "screening_metrics.csv")
    summary: list[dict[str, object]] = []
    plots: list[Path] = []
    evidence = STUDY / "evidence"
    for device, (width_ns, case_id) in CASES.items():
        wave_path = STUDY / device / "waveform_data" / device / "fast_5ps" / "r50_c2pf" / f"{case_id}.csv"
        data = load_wave(wave_path)
        native_screen = next(
            row for row in screen_rows
            if row["device"] == device
            and row["pattern"] == "short_high"
            and row["reference"] == "hspice_native_ibis"
            and abs(float(row["width_ns"]) - width_ns) < 1e-12
        )
        transistor_screen = next(
            row for row in screen_rows
            if row["device"] == device
            and row["pattern"] == "short_high"
            and row["reference"] == "hspice_transistor"
            and abs(float(row["width_ns"]) - width_ns) < 1e-12
        )
        metrics = read_csv(STUDY / device / "candidate_metrics.csv")
        v2 = next(row for row in metrics if row["flow"] == "pad_voltage")
        low_v = float(native_screen["loaded_low_v"])
        high_v = float(native_screen["loaded_high_v"])
        swing_v = high_v - low_v
        candidate_peak = float(np.max(data["pad_voltage_pad_v"]))
        plot = evidence / "plots" / f"{device}_true_output_reversal.png"
        plot_case(device, width_ns, data, float(native_screen["output_turn_time_ns"]), plot)
        plots.append(plot)
        summary.append({
            "device": device,
            "pulse_width_ps": width_ns * 1000.0,
            "data_rate_equivalent_gbps": 1.0 / width_ns,
            "native_output_excursion_fraction": float(native_screen["output_excursion_fraction"]),
            "transistor_output_excursion_fraction": float(transistor_screen["output_excursion_fraction"]),
            "pad_v2_output_excursion_fraction": (candidate_peak - low_v) / swing_v,
            "native_output_turn_time_ns": float(native_screen["output_turn_time_ns"]),
            "pad_v2_pad_rmse_mv": float(v2["pad_rmse_mv"]),
            "pad_v2_ku_rmse": float(v2["ku_rmse"]),
            "pad_v2_kd_rmse": float(v2["kd_rmse"]),
            "pad_v2_active": v2.get("pad_map_triggered", ""),
            "mapping_ambiguous": v2.get("mapping_ambiguous", ""),
            "waveform_csv": str(wave_path.relative_to(ROOT)),
            "figure": str(plot.relative_to(ROOT)),
        })

    images = [plt.imread(path) for path in plots]
    figure, axes = plt.subplots(len(images), 1, figsize=(16.0, 7.6 * len(images)), constrained_layout=True)
    for axis, image in zip(np.atleast_1d(axes), images):
        axis.imshow(image)
        axis.axis("off")
    contact = evidence / "00_true_output_reversal_contact_sheet.png"
    figure.savefig(contact, dpi=130)
    plt.close(figure)
    write_csv(evidence / "true_output_reversal_metrics.csv", summary)

    lines = [
        "# Three-Buffer True Output-Level Reversal Evidence",
        "",
        "All cases use the fast-edge IBIS, 50 ps input edges, and a direct 50 ohm || 2 pF load.",
        "The purple line is the input reverse threshold; the orange line is the later native-pad turning point.",
        "",
        "| Buffer | Pulse | Native excursion | Transistor excursion | V2 excursion | Pad RMSE | Ku RMSE | Kd RMSE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['device']} | {float(row['pulse_width_ps']):.0f} ps | "
            f"{100.0 * float(row['native_output_excursion_fraction']):.1f}% | "
            f"{100.0 * float(row['transistor_output_excursion_fraction']):.1f}% | "
            f"{100.0 * float(row['pad_v2_output_excursion_fraction']):.1f}% | "
            f"{float(row['pad_v2_pad_rmse_mv']):.1f} mV | {float(row['pad_v2_ku_rmse']):.4f} | "
            f"{float(row['pad_v2_kd_rmse']):.4f} |"
        )
    lines.extend([
        "",
        "- `plots/`: one clean input/pad/Ku/Kd figure per buffer.",
        "- `00_true_output_reversal_contact_sheet.png`: all three cases.",
        "- `true_output_reversal_metrics.csv`: numeric evidence and source waveform paths.",
    ])
    (evidence / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
