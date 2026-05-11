"""Build the final accepted PRBS7 + 50 ohm RLGC comparison folder.

This script intentionally uses physical clock/UI folding only. It does not
edge-align rising/falling transitions.
"""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eye_diagram import (  # noqa: E402
    build_eye,
    estimate_signal_levels,
    load_waveform,
    measure_eye,
    measure_transitions,
    plot_eye,
    plot_eye_contour,
    plot_eye_overlay,
    plot_transitions,
    resolve_signal_key,
    sanitize_waveform,
)


UI = 5e-9
SKIP_UI = 10
N_UI = 2
N_INTERP = 2000
OUT_DIR = ROOT / "results" / "final_prbs_rlgc_comparison_2026-05-11"


@dataclass(frozen=True)
class Case:
    key: str
    label: str
    simulator: str
    model: str
    setup: str
    path: Path
    fmt: str
    signal: str = "v(n10b)"


CASES = [
    Case(
        key="ngspice_refspice",
        label="ngspice + io_buf.sp",
        simulator="ngspice",
        model="io_buf.sp transistor-level",
        setup="direct transistor model, PRBS7, new 50 ohm RLGC, Rterm=50",
        path=ROOT / "ngspice_refspice" / "tb_refspice_prbs7_new50ohm_batch.raw",
        fmt="ngspice",
    ),
    Case(
        key="xyce_refspice",
        label="Xyce + io_buf.sp",
        simulator="Xyce",
        model="io_buf.sp transistor-level",
        setup="direct transistor model, PRBS7, new 50 ohm RLGC, Rterm=50",
        path=ROOT / "xyce_refspice" / "tb_refspice_prbs7_new50ohm_xyce.cir.csv",
        fmt="xyce",
    ),
    Case(
        key="ngspice_pybis",
        label="ngspice + pybis",
        simulator="ngspice",
        model="pybis2spice direct",
        setup="direct pybis, PRBS7, new 50 ohm RLGC, Rterm=50, no uic",
        path=ROOT
        / "results"
        / "prbs_rlgc_clean_2026-05-10"
        / "ngspice"
        / "tb_clean_prbs_rlgc_ngspice.raw",
        fmt="ngspice",
    ),
    Case(
        key="xyce_pybis",
        label="Xyce + pybis edge15_flat4p2",
        simulator="Xyce",
        model="pybis2spice Xyce continuation",
        setup=(
            "edge/latch tanh15 + KUR/KDR flat tail after 4.2 ns, "
            "BE/non-LTE timestep controls"
        ),
        path=ROOT
        / "results"
        / "prbs_rlgc_clean_2026-05-10"
        / "xyce"
        / "tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir.csv",
        fmt="xyce",
    ),
]


def ns(value: np.ndarray) -> np.ndarray:
    return value * 1e9


def decimate(time: np.ndarray, voltage: np.ndarray, max_points: int = 20000):
    if len(time) <= max_points:
        return time, voltage
    step = int(math.ceil(len(time) / max_points))
    return time[::step], voltage[::step]


def read_case(case: Case):
    data = load_waveform(case.path, fmt=case.fmt)
    sig_key = resolve_signal_key(data, case.signal)
    time, voltage = sanitize_waveform(data["time"], data[sig_key])
    return time, voltage


def crossing_metrics(time: np.ndarray, voltage: np.ndarray, ui: float, levels):
    threshold = levels["v_mid"]
    above = voltage >= threshold
    idx = np.where(above[:-1] != above[1:])[0]

    rise = []
    fall = []
    for i in idx:
        t0, t1 = time[i], time[i + 1]
        v0, v1 = voltage[i], voltage[i + 1]
        if v1 == v0 or t1 < time[0] + SKIP_UI * ui:
            continue
        tc = t0 + (threshold - v0) * (t1 - t0) / (v1 - v0)
        delay = tc % ui
        if v1 > v0:
            rise.append(delay)
        else:
            fall.append(delay)

    def median_or_nan(values):
        return float(np.median(values)) if values else float("nan")

    rise_med = median_or_nan(rise)
    fall_med = median_or_nan(fall)
    split = rise_med - fall_med
    return {
        "rise_50_delay_ns": rise_med * 1e9,
        "fall_50_delay_ns": fall_med * 1e9,
        "rise_fall_50_split_ns": split * 1e9,
        "rise_fall_50_split_ui": split / ui,
        "rise_crossings": len(rise),
        "fall_crossings": len(fall),
    }


def build_case_artifacts(case: Case):
    time, voltage = read_case(case)
    levels = estimate_signal_levels(voltage)
    transitions = measure_transitions(time, voltage, levels=levels)
    t_eye, eye_slices = build_eye(
        time,
        voltage,
        UI,
        skip_ui=SKIP_UI,
        n_interp=N_INTERP,
        n_ui=N_UI,
        phase_ui=0.0,
    )
    eye_metrics = measure_eye(t_eye, eye_slices, n_ui=N_UI, levels=levels)
    crossing = crossing_metrics(time, voltage, UI, levels)

    case_dir = OUT_DIR / "eyes" / case.key
    case_dir.mkdir(parents=True, exist_ok=True)
    stem = case.key
    sig_clean = "vn10b"

    title = f"{case.label} - physical clock-folded eye"
    plot_eye(
        t_eye,
        eye_slices,
        eye_metrics,
        UI,
        title=title,
        outfile=str(case_dir / f"{stem}_{sig_clean}_eye.png"),
        n_ui=N_UI,
        levels=levels,
    )
    plot_eye_overlay(
        t_eye,
        eye_slices,
        title=f"{title} (overlay)",
        outfile=str(case_dir / f"{stem}_{sig_clean}_overlay.png"),
        n_ui=N_UI,
        levels=levels,
    )
    plot_eye_contour(
        t_eye,
        eye_slices,
        title=f"{title} (contour)",
        outfile=str(case_dir / f"{stem}_{sig_clean}_contour.png"),
        n_ui=N_UI,
        levels=levels,
    )
    plot_transitions(
        time,
        voltage,
        UI,
        title=f"{case.label} - receiver transient",
        outfile=str(case_dir / f"{stem}_{sig_clean}_trans.png"),
        levels=levels,
    )

    row = {
        "key": case.key,
        "label": case.label,
        "simulator": case.simulator,
        "model": case.model,
        "setup": case.setup,
        "waveform": str(case.path.relative_to(ROOT)),
        "format": case.fmt,
        "signal": case.signal,
        "completed_1000ns": bool(time[-1] >= 999.9e-9),
        "samples": len(time),
        "t_start_ns": time[0] * 1e9,
        "t_end_ns": time[-1] * 1e9,
        "v_min": float(np.min(voltage)),
        "v_max": float(np.max(voltage)),
        "level_low": levels["v_low"],
        "level_high": levels["v_high"],
        "level_mid": levels["v_mid"],
        "eye_height_mV": eye_metrics["eye_height"] * 1e3,
        "eye_width_ps": eye_metrics["eye_width"] * 1e12,
        "v_eye_high": eye_metrics["v_eye_high"],
        "v_eye_low": eye_metrics["v_eye_low"],
        "rise_time_ps": transitions["rise_time"] * 1e12,
        "fall_time_ps": transitions["fall_time"] * 1e12,
        "overshoot_mV": transitions["overshoot_abs"] * 1e3,
        "undershoot_mV": transitions["undershoot_abs"] * 1e3,
        "fold_mode": "clock",
        "phase_ui": 0.0,
        "n_ui": N_UI,
        "skip_ui": SKIP_UI,
        "eye_slices": eye_slices.shape[0],
        **crossing,
    }
    return row, time, voltage


def write_csv(path: Path, rows):
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_receiver_overlays(waveforms):
    plots_dir = OUT_DIR / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    colors = {
        "ngspice_refspice": "#1f77b4",
        "xyce_refspice": "#2ca02c",
        "ngspice_pybis": "#ff7f0e",
        "xyce_pybis": "#d62728",
    }

    for name, xlim in [
        ("rx_transient_overlay_full.png", None),
        ("rx_transient_overlay_0_120ns.png", (0.0, 120.0)),
        ("rx_transient_overlay_30_80ns.png", (30.0, 80.0)),
    ]:
        fig, ax = plt.subplots(figsize=(12, 5))
        for case, time, voltage in waveforms:
            t_plot, v_plot = decimate(time, voltage)
            ax.plot(
                ns(t_plot),
                v_plot,
                lw=1.1,
                alpha=0.85,
                color=colors.get(case.key),
                label=case.label,
            )
        if xlim:
            ax.set_xlim(*xlim)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("V(n10b) (V)")
        ax.set_title("Accepted PRBS7 + 50 ohm RLGC receiver transient")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best", fontsize=9)
        fig.tight_layout()
        fig.savefig(plots_dir / name, dpi=160)
        plt.close(fig)


def plot_metric_bars(rows):
    plots_dir = OUT_DIR / "plots"
    labels = [r["label"] for r in rows]
    metrics = [
        ("eye_height_mV", "Eye height (mV)", "rx_eye_height_bar.png"),
        ("eye_width_ps", "Eye width (ps)", "rx_eye_width_bar.png"),
        ("rise_time_ps", "Rise time 20-80 (ps)", "rx_rise_time_bar.png"),
        ("fall_time_ps", "Fall time 20-80 (ps)", "rx_fall_time_bar.png"),
        ("rise_fall_50_split_ui", "Rise/fall 50% split (UI)", "rx_rise_fall_split_bar.png"),
    ]
    for key, ylabel, filename in metrics:
        values = [float(r[key]) for r in rows]
        fig, ax = plt.subplots(figsize=(11, 4.8))
        x = np.arange(len(labels))
        ax.bar(x, values, color=["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(f"Accepted PRBS7 + RLGC: {ylabel}")
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(plots_dir / filename, dpi=160)
        plt.close(fig)


def compare_pairs(waveforms):
    plots_dir = OUT_DIR / "plots"
    pairs = [
        ("refspice_xyce_minus_ngspice.csv", "ngspice_refspice", "xyce_refspice"),
        ("pybis_xyce_minus_ngspice.csv", "ngspice_pybis", "xyce_pybis"),
    ]
    by_key = {case.key: (case, time, voltage) for case, time, voltage in waveforms}
    rows = []
    for filename, ref_key, test_key in pairs:
        ref_case, ref_t, ref_v = by_key[ref_key]
        test_case, test_t, test_v = by_key[test_key]
        t0 = max(ref_t[0], test_t[0])
        t1 = min(ref_t[-1], test_t[-1])
        grid = np.linspace(t0, t1, 20001)
        ref_interp = np.interp(grid, ref_t, ref_v)
        test_interp = np.interp(grid, test_t, test_v)
        diff = test_interp - ref_interp
        row = {
            "comparison": f"{test_case.label} minus {ref_case.label}",
            "reference": ref_case.key,
            "test": test_case.key,
            "points": len(grid),
            "t_end_ns": t1 * 1e9,
            "rmse_mV": float(np.sqrt(np.mean(diff * diff)) * 1e3),
            "max_abs_error_mV": float(np.max(np.abs(diff)) * 1e3),
            "mean_error_mV": float(np.mean(diff) * 1e3),
        }
        rows.append(row)
        write_csv(plots_dir / filename, [row])

    write_csv(OUT_DIR / "pairwise_error_summary.csv", rows)


def write_readme(rows):
    lines = [
        "# Final PRBS7 + 50 Ohm RLGC Comparison",
        "",
        "Date: 2026-05-11",
        "",
        "This folder is the frozen accepted benchmark for the current open-source",
        "IBIS comparison work. It intentionally excludes HSPICE because the matched",
        "HSPICE `io_buf.sp` run is not ready yet.",
        "",
        "## Accepted Benchmark",
        "",
        "- PRBS7 stimulus",
        "- 5 ns UI, 200 Mbps",
        "- 200 ps input rise/fall",
        "- 1000 ns transient",
        "- new 50 ohm 10-section RLGC channel",
        "- 50 ohm receiver termination",
        "- physical clock/UI-grid eye folding only",
        "",
        "Ideal T-line PRBS results are stress tests and are not part of this",
        "accepted result folder.",
        "",
        "## Cases",
        "",
        "| Case | Model | Completed | Eye height | Eye width | Rise/Fall 50 split |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            "| {label} | {model} | {completed_1000ns} | {eye_height_mV:.1f} mV | "
            "{eye_width_ps:.1f} ps | {rise_fall_50_split_ui:.3f} UI |".format(**r)
        )
    lines.extend(
        [
            "",
            "## Key Files",
            "",
            "- `final_metrics_summary.csv`: combined per-case metrics",
            "- `pairwise_error_summary.csv`: Xyce-vs-ngspice error summaries",
            "- `plots/rx_transient_overlay_0_120ns.png`: receiver overlay",
            "- `plots/rx_transient_overlay_30_80ns.png`: early transition zoom",
            "- `eyes/*/*_overlay.png`: physical clock-folded eye overlays",
            "",
            "## Xyce pybis Status",
            "",
            "The Xyce pybis case is a practical continuation setup, not a direct",
            "unmodified pybis pass. It uses `edge15_flat4p2`: edge/latch `tanh15`",
            "conditioning plus a flat rising KUR/KDR table tail after 4.2 ns.",
            "This is the best full 1000 ns PRBS/RLGC path found so far, but the",
            "direct/minimally modified Xyce pybis question remains open.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="ascii")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    waveforms = []
    for case in CASES:
        print(f"Processing {case.label}: {case.path.relative_to(ROOT)}")
        row, time, voltage = build_case_artifacts(case)
        rows.append(row)
        waveforms.append((case, time, voltage))

    write_csv(OUT_DIR / "final_metrics_summary.csv", rows)
    plot_receiver_overlays(waveforms)
    plot_metric_bars(rows)
    compare_pairs(waveforms)
    write_readme(rows)
    print(f"Wrote final comparison folder: {OUT_DIR}")


if __name__ == "__main__":
    main()
