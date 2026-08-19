#!/usr/bin/env python3
"""Generate an apples-to-apples runtime Ku/Kd comparison from cached data."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
STUDY_DIR = ROOT / "results" / "io_buf_correct_hspice_vs_pybis_2026-07-23"
SOURCE_CSV = (
    STUDY_DIR
    / "cases"
    / "edge_1ps_base_50r_2pf"
    / "aligned_correct_references_vs_pybis.csv"
)
OUTPUT_DIR = STUDY_DIR / "runtime_kukd_comparison"
PLOT_DIR = OUTPUT_DIR / "plots"

RISE_NS = 5.0
FALL_NS = 15.0
IMPULSE_END_OFFSET_NS = 0.05

FLOWS = (
    ("native", "HSPICE native IBIS runtime", "#111111", "-", 3.0),
    ("legacy", "ngspice legacy pybis runtime", "#e68600", "--", 2.2),
    (
        "directional_residual",
        "ngspice gate-state directional+residual runtime",
        "#d62728",
        "-.",
        2.2,
    ),
)


def load_data() -> dict[str, np.ndarray]:
    data = np.genfromtxt(SOURCE_CSV, delimiter=",", names=True)
    return {name: np.asarray(data[name], dtype=float) for name in data.dtype.names}


def select_segments(
    time_ns: np.ndarray,
    segments: list[tuple[float, float]],
) -> list[np.ndarray]:
    masks = []
    for start, stop in segments:
        mask = (time_ns >= start) & (time_ns <= stop)
        if np.count_nonzero(mask) >= 2:
            masks.append(mask)
    return masks


def time_weighted_rmse(
    time_ns: np.ndarray,
    error: np.ndarray,
    segments: list[tuple[float, float]],
) -> float:
    total_integral = 0.0
    total_duration = 0.0
    for mask in select_segments(time_ns, segments):
        t = time_ns[mask]
        e = error[mask]
        total_integral += float(np.trapezoid(e * e, t))
        total_duration += float(t[-1] - t[0])
    if total_duration <= 0.0:
        return float("nan")
    return float(np.sqrt(total_integral / total_duration))


def max_abs_error(
    time_ns: np.ndarray,
    error: np.ndarray,
    segments: list[tuple[float, float]],
) -> float:
    values = [np.abs(error[mask]) for mask in select_segments(time_ns, segments)]
    if not values:
        return float("nan")
    return float(np.max(np.concatenate(values)))


def metric_rows(data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    time_ns = data["time_ns"]
    windows = {
        "full_active": [(4.5, 20.0)],
        "rise_impulse_50ps": [(RISE_NS - 0.005, RISE_NS + IMPULSE_END_OFFSET_NS)],
        "fall_impulse_50ps": [(FALL_NS - 0.005, FALL_NS + IMPULSE_END_OFFSET_NS)],
        "outside_impulses": [
            (4.5, RISE_NS - 0.005),
            (RISE_NS + IMPULSE_END_OFFSET_NS, FALL_NS - 0.005),
            (FALL_NS + IMPULSE_END_OFFSET_NS, 20.0),
        ],
        "rise_main_body": [(RISE_NS + IMPULSE_END_OFFSET_NS, FALL_NS - 0.1)],
        "fall_main_body": [(FALL_NS + IMPULSE_END_OFFSET_NS, 20.0)],
    }
    rows: list[dict[str, object]] = []
    for flow_id, label, _, _, _ in FLOWS[1:]:
        ku_error = data[f"{flow_id}_ku"] - data["native_ku"]
        kd_error = data[f"{flow_id}_kd"] - data["native_kd"]
        for window_name, segments in windows.items():
            rows.append(
                {
                    "flow": flow_id,
                    "flow_label": label,
                    "reference": "HSPICE native IBIS runtime",
                    "window": window_name,
                    "segments_ns": ";".join(f"{a:g}:{b:g}" for a, b in segments),
                    "ku_time_weighted_rmse": time_weighted_rmse(
                        time_ns, ku_error, segments
                    ),
                    "kd_time_weighted_rmse": time_weighted_rmse(
                        time_ns, kd_error, segments
                    ),
                    "ku_max_abs_error": max_abs_error(time_ns, ku_error, segments),
                    "kd_max_abs_error": max_abs_error(time_ns, kd_error, segments),
                }
            )
    return rows


def edge_range_rows(data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    time_ns = data["time_ns"]
    rows: list[dict[str, object]] = []
    for edge_name, edge_ns in (("rise", RISE_NS), ("fall", FALL_NS)):
        mask = (time_ns >= edge_ns - 0.005) & (
            time_ns <= edge_ns + IMPULSE_END_OFFSET_NS
        )
        for flow_id, label, _, _, _ in FLOWS:
            rows.append(
                {
                    "edge": edge_name,
                    "flow": flow_id,
                    "flow_label": label,
                    "window_start_ns": edge_ns - 0.005,
                    "window_stop_ns": edge_ns + IMPULSE_END_OFFSET_NS,
                    "ku_min": float(np.min(data[f"{flow_id}_ku"][mask])),
                    "ku_max": float(np.max(data[f"{flow_id}_ku"][mask])),
                    "kd_min": float(np.min(data[f"{flow_id}_kd"][mask])),
                    "kd_max": float(np.max(data[f"{flow_id}_kd"][mask])),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_aligned_data(data: dict[str, np.ndarray]) -> None:
    fields = [
        "time_ns",
        "input_v",
        "native_ku",
        "native_kd",
        "legacy_ku",
        "legacy_kd",
        "directional_residual_ku",
        "directional_residual_kd",
    ]
    rows = [
        {field: f"{float(data[field][index]):.12g}" for field in fields}
        for index in range(len(data["time_ns"]))
    ]
    write_csv(OUTPUT_DIR / "normal_runtime_kukd_aligned.csv", rows)


def add_edge_markers(ax: plt.Axes) -> None:
    ax.axvline(RISE_NS, color="#777777", lw=1.1, ls=":", label="_nolegend_")
    ax.axvline(FALL_NS, color="#777777", lw=1.1, ls=":", label="_nolegend_")


def plot_signal(
    ax: plt.Axes,
    data: dict[str, np.ndarray],
    signal: str,
    xlim: tuple[float, float],
) -> None:
    time_ns = data["time_ns"]
    mask = (time_ns >= xlim[0]) & (time_ns <= xlim[1])
    for flow_id, label, color, linestyle, linewidth in FLOWS:
        ax.plot(
            time_ns[mask],
            data[f"{flow_id}_{signal}"][mask],
            color=color,
            ls=linestyle,
            lw=linewidth,
            label=label,
        )
    ax.axhline(0.0, color="#888888", lw=0.8)
    add_edge_markers(ax)
    ax.set_xlim(*xlim)
    ax.set_ylabel(signal.capitalize())
    ax.grid(True, alpha=0.22)


def save_full_transition(data: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), sharex=True)
    plot_signal(axes[0], data, "ku", (4.5, 20.0))
    plot_signal(axes[1], data, "kd", (4.5, 20.0))
    axes[0].set_title(
        "Normal complete pulse: runtime Ku/Kd comparison using the 5 ps IBIS"
    )
    axes[0].legend(loc="upper center", ncol=3, fontsize=10)
    axes[1].set_xlabel("time (ns)")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "01_runtime_full_transition.png", dpi=180)
    plt.close(fig)


def save_edge_zoom(
    data: dict[str, np.ndarray],
    edge_name: str,
    xlim: tuple[float, float],
    output_name: str,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), sharex=True)
    plot_signal(axes[0], data, "ku", xlim)
    plot_signal(axes[1], data, "kd", xlim)
    axes[0].set_title(
        f"Normal {edge_name} edge: immediate runtime coefficient behavior"
    )
    axes[0].legend(loc="upper right", fontsize=10)
    axes[1].set_xlabel("time (ns)")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / output_name, dpi=180)
    plt.close(fig)


def save_main_body(data: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(17, 9), sharex="col")
    plot_signal(axes[0, 0], data, "ku", (5.05, 10.0))
    plot_signal(axes[1, 0], data, "kd", (5.05, 10.0))
    plot_signal(axes[0, 1], data, "ku", (15.05, 20.0))
    plot_signal(axes[1, 1], data, "kd", (15.05, 20.0))
    axes[0, 0].set_title("Rising main body, after first 50 ps")
    axes[0, 1].set_title("Falling main body, after first 50 ps")
    axes[0, 0].legend(loc="center right", fontsize=9)
    axes[1, 0].set_xlabel("time (ns)")
    axes[1, 1].set_xlabel("time (ns)")
    fig.suptitle(
        "Runtime Ku/Kd after excluding the immediate edge-impulse window",
        fontsize=16,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "04_runtime_main_transition_body.png", dpi=180)
    plt.close(fig)


def metric_value(
    rows: list[dict[str, object]],
    flow: str,
    window: str,
    field: str,
) -> float:
    row = next(item for item in rows if item["flow"] == flow and item["window"] == window)
    return float(row[field])


def write_readme(metric_data: list[dict[str, object]]) -> None:
    legacy_full_ku = metric_value(
        metric_data, "legacy", "full_active", "ku_time_weighted_rmse"
    )
    legacy_full_kd = metric_value(
        metric_data, "legacy", "full_active", "kd_time_weighted_rmse"
    )
    legacy_body_ku = metric_value(
        metric_data, "legacy", "outside_impulses", "ku_time_weighted_rmse"
    )
    legacy_body_kd = metric_value(
        metric_data, "legacy", "outside_impulses", "kd_time_weighted_rmse"
    )
    gate_full_ku = metric_value(
        metric_data,
        "directional_residual",
        "full_active",
        "ku_time_weighted_rmse",
    )
    gate_full_kd = metric_value(
        metric_data,
        "directional_residual",
        "full_active",
        "kd_time_weighted_rmse",
    )
    readme = f"""# Fast-IBIS Runtime Ku/Kd Comparison

This package makes the primary comparison apples-to-apples. Every plotted
coefficient is a runtime signal from the same normal complete-pulse bench:

- HSPICE native IBIS runtime `Ku/Kd`.
- ngspice legacy pybis runtime `Ku/Kd`.
- ngspice directional+residual gate-state runtime `Ku/Kd`.

No HSPICE or ngspice simulations were rerun. The figures and metrics use the
cached aligned data from the corrected 5 ps IBIS study.

## Runtime Finding

- Legacy pybis full-window time-weighted Ku/Kd RMSE versus HSPICE is
  `{legacy_full_ku:.5f}` / `{legacy_full_kd:.5f}`.
- Outside the first 50 ps impulse after each edge, legacy pybis Ku/Kd RMSE is
  `{legacy_body_ku:.5f}` / `{legacy_body_kd:.5f}`.
- The legacy model therefore reproduces the main normal coefficient
  trajectories closely, while its immediate edge impulses differ from HSPICE.
- The current gate-state model full-window Ku/Kd RMSE is
  `{gate_full_ku:.5f}` / `{gate_full_kd:.5f}`.
- The gate-state result is invalid as a model-quality claim because its offline
  endpoint/reconstruction gate failed before runtime.

## Offline Diagnostic Is Separate

HSPICE does not provide an exported offline Ku/Kd table in this workflow.
The existing `../figures/fast_ibis_reconstruction_gate.png` compares only:

1. pybis offline-derived coefficient tables, and
2. the gate-state model's offline reconstruction of those tables.

It must not be described as an offline HSPICE-versus-pybis comparison.

## Figures

- `plots/01_runtime_full_transition.png`
- `plots/02_runtime_rising_edge_zoom.png`
- `plots/03_runtime_falling_edge_zoom.png`
- `plots/04_runtime_main_transition_body.png`

## Numeric Data

- `runtime_metrics.csv`: time-weighted RMSE and maximum error by analysis window.
- `runtime_edge_ranges.csv`: Ku/Kd minima and maxima in each 50 ps edge window.
- `normal_runtime_kukd_aligned.csv`: the actual aligned runtime samples.
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="ascii")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data()
    metrics = metric_rows(data)
    write_csv(OUTPUT_DIR / "runtime_metrics.csv", metrics)
    write_csv(OUTPUT_DIR / "runtime_edge_ranges.csv", edge_range_rows(data))
    write_aligned_data(data)
    save_full_transition(data)
    save_edge_zoom(
        data,
        "rising",
        (4.995, 5.08),
        "02_runtime_rising_edge_zoom.png",
    )
    save_edge_zoom(
        data,
        "falling",
        (14.995, 15.08),
        "03_runtime_falling_edge_zoom.png",
    )
    save_main_body(data)
    write_readme(metrics)
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
