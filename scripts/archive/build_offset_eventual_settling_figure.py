#!/usr/bin/env python3
"""Show that the io_buf short-high offset eventually decays to zero.

Uses the cached command-probe CSV only. No simulation is launched.
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27"
SOURCE = OUT / "command_probe" / "swing_60_w1792ps.csv"
REFERENCE = (
    ROOT / "results" / "stress_method_matrix_2026-08-20" / "hybrid"
    / "waveforms" / "io_buf_short_high_w1792ps.csv"
)
REVERSE_NS = 5.0 + 1.792
RESTORE_START_NS = 2.958
MODEL_C = "#C05621"
REFERENCE_C = "#2B6CA3"


def load_csv(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(value) for value in row] for row in rows[1:]])
    return {name: values[:, index] for index, name in enumerate(rows[0])}


def permanent_threshold_time(time: np.ndarray, values: np.ndarray, limit: float) -> float:
    inside_from_here = np.logical_and.accumulate((np.abs(values) < limit)[::-1])[::-1]
    hits = np.flatnonzero(inside_from_here)
    return float(time[hits[0]]) if len(hits) else float("nan")


def main() -> int:
    data = load_csv(SOURCE)
    reference = load_csv(REFERENCE)
    time = data["time_ns"] - REVERSE_NS
    keep = (time >= 0.0) & (time <= 8.0)
    time = time[keep]
    command = data["gupcmd"][keep]
    pad = data["pad"][keep]
    reference_time = reference["time_ns"] - REVERSE_NS
    native_pad = np.interp(time, reference_time, reference["hspice_pad"])

    pad_1mv_ns = permanent_threshold_time(time, pad, 1e-3)
    native_pad_1mv_ns = permanent_threshold_time(time, native_pad, 1e-3)
    command_001_ns = permanent_threshold_time(time, command, 1e-3)

    fig, axes = plt.subplots(2, 1, figsize=(13.0, 8.2), sharex=True)
    for axis in axes:
        axis.axhline(0.0, color="#555555", lw=1.1)
        axis.axvline(RESTORE_START_NS, color="#777777", ls="--", lw=1.5,
                     label="cleanup starts")
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.set_xlim(0.0, 8.0)
        axis.tick_params(labelsize=11.5)

    axes[0].plot(time, command, color=MODEL_C, lw=3.0,
                 label="leftover pullup command")
    axes[0].axvline(command_001_ns, color=MODEL_C, ls=":", lw=1.8,
                    label=f"below 0.001 after {command_001_ns:.2f} ns")
    axes[0].set_ylabel("GUPCMD", fontsize=14)
    axes[0].set_ylim(-0.005, 0.055)
    axes[0].legend(loc="upper right", fontsize=11.5, framealpha=0.95)

    axes[1].plot(time, pad * 1e3, color=MODEL_C, lw=3.0,
                 label="gate-state pad")
    axes[1].plot(time, native_pad * 1e3, color=REFERENCE_C, lw=3.0,
                 label="HSPICE native IBIS pad")
    axes[1].axvline(pad_1mv_ns, color=MODEL_C, ls=":", lw=1.8,
                    label=f"gate-state within +/-1 mV after {pad_1mv_ns:.2f} ns")
    axes[1].axvline(native_pad_1mv_ns, color=REFERENCE_C, ls=":", lw=1.8,
                    label=f"native IBIS within +/-1 mV after {native_pad_1mv_ns:.2f} ns")
    axes[1].axhspan(-1.0, 1.0, color="#DDE8DF", alpha=0.7, lw=0)
    axes[1].set_ylabel("Pad voltage (mV)", fontsize=14)
    axes[1].set_xlabel("Time after the falling/reversal edge (ns)", fontsize=13)
    axes[1].set_ylim(-8.0, 125.0)
    axes[1].legend(loc="upper right", fontsize=11.5, framealpha=0.95)

    fig.suptitle("io_buf | short high | temporary offset settling", fontsize=18,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    figure_path = OUT / "06_offset_eventually_settles.png"
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)

    full_time = reference["time_ns"]
    full_keep = (full_time >= 4.5) & (full_time <= 14.5)
    full_time = full_time[full_keep]
    full_series = {
        name: reference[name][full_keep]
        for name in (
            "hspice_ku", "hspice_kd", "hspice_pad",
            "pybis_ku", "pybis_kd", "pybis_pad",
        )
    }

    fig, axes = plt.subplots(3, 1, figsize=(13.0, 10.2), sharex=True)
    panels = (
        ("ku", "Ku", (-0.15, 1.15)),
        ("kd", "Kd", (-0.15, 1.15)),
        ("pad", "Pad voltage (V)", (-0.08, 1.05)),
    )
    for axis, (signal, ylabel, ylim) in zip(axes, panels):
        axis.plot(full_time, full_series[f"hspice_{signal}"], color=REFERENCE_C,
                  lw=3.2, label="HSPICE native IBIS")
        axis.plot(full_time, full_series[f"pybis_{signal}"], color=MODEL_C,
                  lw=2.8, label="gate-state hybrid")
        axis.axhline(0.0, color="#555555", lw=1.0)
        axis.axvline(5.0, color="#777777", ls="--", lw=1.5)
        axis.axvline(REVERSE_NS, color="#777777", ls="--", lw=1.5)
        axis.set_ylabel(ylabel, fontsize=14)
        axis.set_ylim(*ylim)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=11.5)
    axes[0].legend(loc="upper right", fontsize=11.5, framealpha=0.95)
    axes[0].text(5.0, 1.07, "rising edge", ha="center", va="bottom",
                 fontsize=11.5, color="#555555")
    axes[0].text(REVERSE_NS, 1.07, "falling edge", ha="center", va="bottom",
                 fontsize=11.5, color="#555555")
    axes[-1].set_xlim(4.5, 14.5)
    axes[-1].set_xlabel("Time (ns)", fontsize=13)
    fig.suptitle("io_buf | short high | 1792 ps | full event", fontsize=18,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    full_figure_path = OUT / "07_full_event_kukd_pad.png"
    fig.savefig(full_figure_path, dpi=180)
    plt.close(fig)

    full_csv_path = OUT / "07_full_event_kukd_pad.csv"
    with full_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "time_ns", "hspice_native_ku", "gate_state_hybrid_ku",
            "hspice_native_kd", "gate_state_hybrid_kd",
            "hspice_native_pad_v", "gate_state_hybrid_pad_v",
        ])
        writer.writerows(zip(
            full_time,
            full_series["hspice_ku"], full_series["pybis_ku"],
            full_series["hspice_kd"], full_series["pybis_kd"],
            full_series["hspice_pad"], full_series["pybis_pad"],
        ))

    sample_path = OUT / "06_offset_eventually_settles.csv"
    sample_times = np.arange(1.0, 8.1, 1.0)
    with sample_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "time_after_reversal_ns", "gupcmd", "gate_state_pad_mv",
            "hspice_native_ibis_pad_mv",
        ])
        for sample_time in sample_times:
            writer.writerow([
                f"{sample_time:.1f}",
                f"{np.interp(sample_time, time, command):.7f}",
                f"{np.interp(sample_time, time, pad) * 1e3:.7f}",
                f"{np.interp(sample_time, time, native_pad) * 1e3:.7f}",
            ])

    print(figure_path)
    print(sample_path)
    print(full_figure_path)
    print(full_csv_path)
    print(f"pad permanently within 1 mV after {pad_1mv_ns:.3f} ns")
    print(f"native IBIS pad permanently within 1 mV after {native_pad_1mv_ns:.3f} ns")
    print(f"GUPCMD permanently below 0.001 after {command_001_ns:.3f} ns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
