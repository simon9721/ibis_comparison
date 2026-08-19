#!/usr/bin/env python3
"""Summarize the inv_chain s2ibispy slow/fast HSPICE sanity runs."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_hspice_tr0  # noqa: E402


STUDY = REPO / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27"
TRANSISTOR_TR0 = (
    REPO
    / "results"
    / "inv_chain_gate_state_clean_comparison_2026-07-27"
    / "cases"
    / "edge_1ps_base_50r_2pf"
    / "hspice_transistor"
    / "edge_1ps_base_50r_2pf_hspice_transistor.tr0"
)

COLORS = {
    "transistor": "#222222",
    "slow_1ns": "#d97706",
    "fast_5ps": "#2563eb",
}
LABELS = {
    "transistor": "HSPICE transistor",
    "slow_1ns": "HSPICE IBIS, s2ibispy 1 ns",
    "fast_5ps": "HSPICE IBIS, s2ibispy 5 ps",
}


def crossing_time(time: np.ndarray, value: np.ndarray, level: float, start: float, stop: float, rising: bool) -> float:
    mask = (time >= start) & (time <= stop)
    t = time[mask]
    v = value[mask]
    delta = v - level
    if rising:
        indices = np.where((delta[:-1] <= 0) & (delta[1:] > 0))[0]
    else:
        indices = np.where((delta[:-1] >= 0) & (delta[1:] < 0))[0]
    if not len(indices):
        return float("nan")
    idx = int(indices[0])
    return float(t[idx] + (level - v[idx]) * (t[idx + 1] - t[idx]) / (v[idx + 1] - v[idx]))


def main() -> int:
    data = {
        "slow_1ns": parse_hspice_tr0(STUDY / "hspice_sanity" / "slow_1ns" / "run.tr0"),
        "fast_5ps": parse_hspice_tr0(STUDY / "hspice_sanity" / "fast_5ps" / "run.tr0"),
        "transistor": parse_hspice_tr0(TRANSISTOR_TR0),
    }

    grid = np.linspace(4e-9, 20e-9, 16001)
    transistor_pad = np.interp(
        grid,
        np.asarray(data["transistor"]["time"]),
        np.asarray(data["transistor"]["v(pad_sp)"]),
    )

    rows: list[dict[str, object]] = []
    for flow_id, flow in data.items():
        time = np.asarray(flow["time"])
        pad_name = "v(pad_sp)" if flow_id == "transistor" else "v(pad_ibis)"
        pad = np.asarray(flow[pad_name])
        pad_grid = np.interp(grid, time, pad)
        row: dict[str, object] = {
            "flow_id": flow_id,
            "pad_rmse_vs_transistor_mV": float(np.sqrt(np.mean((pad_grid - transistor_pad) ** 2)) * 1e3),
            "pad_min_V": float(np.min(pad_grid)),
            "pad_max_V": float(np.max(pad_grid)),
            "pad_rise_50_crossing_ns": crossing_time(time, pad, 0.9, 5e-9, 12e-9, True) * 1e9,
            "pad_fall_50_crossing_ns": crossing_time(time, pad, 0.9, 15e-9, 20e-9, False) * 1e9,
            "ku_min": "",
            "ku_max": "",
            "kd_min": "",
            "kd_max": "",
        }
        if flow_id != "transistor":
            row.update(
                {
                    "ku_min": float(np.min(flow["v(ku)"])),
                    "ku_max": float(np.max(flow["v(ku)"])),
                    "kd_min": float(np.min(flow["v(kd)"])),
                    "kd_max": float(np.max(flow["v(kd)"])),
                }
            )
        rows.append(row)

    metrics_path = STUDY / "hspice_sanity_metrics.csv"
    with metrics_path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True, constrained_layout=True)
    for flow_id in ("transistor", "slow_1ns", "fast_5ps"):
        flow = data[flow_id]
        pad_name = "v(pad_sp)" if flow_id == "transistor" else "v(pad_ibis)"
        axes[0].plot(
            np.asarray(flow["time"]) * 1e9,
            flow[pad_name],
            color=COLORS[flow_id],
            linewidth=2.8 if flow_id == "transistor" else 2.1,
            label=LABELS[flow_id],
            zorder=4 if flow_id == "transistor" else 3,
        )
    for flow_id in ("slow_1ns", "fast_5ps"):
        flow = data[flow_id]
        time_ns = np.asarray(flow["time"]) * 1e9
        axes[1].plot(time_ns, flow["v(ku)"], color=COLORS[flow_id], linewidth=2.1, label=LABELS[flow_id])
        axes[2].plot(time_ns, flow["v(kd)"], color=COLORS[flow_id], linewidth=2.1, label=LABELS[flow_id])

    axes[0].set_ylabel("Pad voltage (V)")
    axes[1].set_ylabel("Ku")
    axes[2].set_ylabel("Kd")
    axes[2].set_xlabel("Time (ns)")
    axes[0].set_title("inv_chain: s2ibispy slow/fast native-IBIS sanity check")
    axes[0].legend(loc="best", frameon=False, ncol=3)
    axes[1].legend(loc="best", frameon=False, ncol=2)
    for axis in axes:
        axis.axvline(5.0005, color="#666666", linestyle="--", linewidth=1.2)
        axis.axvline(15.0005, color="#666666", linestyle="--", linewidth=1.2)
        axis.grid(True, color="#dddddd", linewidth=0.8)
        axis.set_xlim(4, 19)
    axes[1].axhline(0, color="#999999", linewidth=0.8)
    axes[2].axhline(0, color="#999999", linewidth=0.8)

    plots = STUDY / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    fig.savefig(plots / "hspice_sanity_slow_fast.png", dpi=160)
    plt.close(fig)

    print(metrics_path)
    print(plots / "hspice_sanity_slow_fast.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
