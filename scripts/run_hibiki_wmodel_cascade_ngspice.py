from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ngspice_lab import (
    DEFAULT_NGSPICE,
    IbisDutConfig,
    StimulusConfig,
    get_trace,
    parse_ngspice_raw,
    prepare_ibis_dut,
    pwl_source,
    stimulus_points,
)
from run_hibiki_wmodel_baseline_ngspice import (
    BASELINE_LENGTH_MM,
    COMPONENT_NAME,
    IBIS_PATH,
    LADDER_SECTIONS,
    MAX_STEP_PS,
    MODEL_NAME,
    R_LOAD_OHM,
    VDD,
    WMODEL_PATH,
    WTrace,
    append_rlgc_ladder,
    parse_wmodel,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "hibiki_i3c_tx_0p125ma_wmodel_cascade_ngspice_2026-05-29"


def write_bench(traces: list[WTrace], subckt_path: Path, subckt_name: str) -> tuple[Path, Path, float]:
    bench_dir = OUT_DIR / "benches"
    raw_dir = OUT_DIR / "raw"
    bench_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    stimulus = StimulusConfig(
        kind="pulse_train",
        v_low=0.0,
        v_high=VDD,
        start_ns=10.0,
        edge_ps=5.0,
        high_ns=20.0,
        low_ns=20.0,
        pulses=5,
    )
    points, stop_ns = stimulus_points(stimulus)
    bench_path = bench_dir / "hibiki_wmodel_cascade.sp"
    raw_path = raw_dir / "hibiki_wmodel_cascade.raw"

    source_node = "src_driver"
    cascade_nodes = ["after_trace01", "after_trace02", "pad_cascade"]
    lines = [
        "* Hibiki I3C_TX_0p125mA_tx through cascaded Wmodel baseline RLGC traces",
        "* Cascade order: Trace01 -> Trace02 -> Trace03.",
        "* Baseline conversion uses Ro/Lo/Go/Co only; Rs and Gd are documented but ignored.",
        f"* Wmodel source: {WMODEL_PATH.as_posix()}",
        f"* Baseline length per trace: {BASELINE_LENGTH_MM:g} mm, ladder sections per trace: {LADDER_SECTIONS:d}",
        ".temp 25",
        ".options method=gear maxord=2 reltol=1e-4 abstol=1e-12 vntol=1e-7 gmin=1e-12",
        f"Vin in_dig 0 {pwl_source(points)}",
        f"Ven en_sig 0 DC {VDD:g}",
        f"Vdd vdd 0 DC {VDD:g}",
        f".include '{subckt_path.as_posix()}'",
        "",
        f"Xhibiki {source_node} in_dig en_sig vdd 0 {subckt_name}",
    ]

    previous_node = source_node
    for trace, next_node in zip(traces, cascade_nodes):
        lines.append("")
        lines.append(f"* {trace.model_name}: Ro/Lo/Go/Co baseline, Rs={trace.rs_skin:g} ignored, Gd={trace.gd_dielectric:g} ignored")
        append_rlgc_ladder(lines, trace, previous_node, next_node)
        previous_node = next_node
    lines.append(f"RLOAD_cascade pad_cascade 0 {R_LOAD_OHM:g}")

    save_vars = ["V(in_dig)", f"V({source_node})", "V(after_trace01)", "V(after_trace02)", "V(pad_cascade)", "V(xhibiki.ku)", "V(xhibiki.kd)"]
    lines.extend(
        [
            "",
            ".save " + " ".join(save_vars),
            f".tran {MAX_STEP_PS:g}p {stop_ns:g}n",
            ".end",
            "",
        ]
    )
    bench_path.write_text("\n".join(lines), encoding="utf-8")
    return bench_path, raw_path, stop_ns


def run_ngspice(bench_path: Path, raw_path: Path) -> Path:
    log_path = raw_path.with_suffix(".log")
    proc = subprocess.run(
        [str(DEFAULT_NGSPICE), "-b", "-r", str(raw_path), str(bench_path)],
        cwd=bench_path.parent,
        capture_output=True,
        text=True,
    )
    log_path.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"ngspice failed. See {log_path}")
    return log_path


def first_crossing_time(t_ns: np.ndarray, y: np.ndarray, level: float, window: tuple[float, float]) -> float | None:
    mask = (t_ns >= window[0]) & (t_ns <= window[1])
    tx = t_ns[mask]
    yy = y[mask]
    for idx in range(1, len(tx)):
        y0 = yy[idx - 1]
        y1 = yy[idx]
        if (y0 <= level <= y1) or (y1 <= level <= y0):
            if math.isclose(y0, y1):
                return float(tx[idx])
            frac = (level - y0) / (y1 - y0)
            return float(tx[idx - 1] + frac * (tx[idx] - tx[idx - 1]))
    return None


def write_metrics(waveforms: dict[str, np.ndarray]) -> Path:
    csv_path = OUT_DIR / "cascade_waveform_metrics.csv"
    time = get_trace(waveforms, "time")
    if time is None:
        raise RuntimeError("Raw file missing time trace")
    t_ns = time * 1e9
    nodes = [
        ("driver_side", "v(src_driver)"),
        ("after_trace01", "v(after_trace01)"),
        ("after_trace02", "v(after_trace02)"),
        ("far_end", "v(pad_cascade)"),
    ]
    rows = []
    for label, trace_name in nodes:
        wave = get_trace(waveforms, trace_name)
        if wave is None:
            continue
        first_rise = (t_ns >= 10.0) & (t_ns <= 35.0)
        rise_min = float(np.min(wave[first_rise])) if np.any(first_rise) else float(np.min(wave))
        rise_max = float(np.max(wave[first_rise])) if np.any(first_rise) else float(np.max(wave))
        v10 = rise_min + 0.1 * (rise_max - rise_min)
        v50 = rise_min + 0.5 * (rise_max - rise_min)
        v90 = rise_min + 0.9 * (rise_max - rise_min)
        t10 = first_crossing_time(t_ns, wave, v10, (10.0, 35.0))
        t50 = first_crossing_time(t_ns, wave, v50, (10.0, 35.0))
        t90 = first_crossing_time(t_ns, wave, v90, (10.0, 35.0))
        rows.append(
            {
                "node": label,
                "trace": trace_name,
                "min_v": float(np.min(wave)),
                "max_v": float(np.max(wave)),
                "first_rise_10pct_time_ns": t10 if t10 is not None else "",
                "first_rise_50pct_time_ns": t50 if t50 is not None else "",
                "first_rise_90pct_time_ns": t90 if t90 is not None else "",
                "first_rise_10_90_ns": (t90 - t10) if t10 is not None and t90 is not None else "",
            }
        )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def write_conversion_summary(traces: list[WTrace]) -> Path:
    csv_path = OUT_DIR / "cascade_wmodel_conversion.csv"
    rows = []
    total_delay_ns = 0.0
    for order, trace in enumerate(traces, start=1):
        delay_ns = trace.delay_s_per_m * (BASELINE_LENGTH_MM / 1000.0) * 1e9
        total_delay_ns += delay_ns
        per_mm = trace.per_mm()
        rows.append(
            {
                "order": order,
                "trace": trace.tag,
                "wmodel_name": trace.model_name,
                "baseline_length_mm": BASELINE_LENGTH_MM,
                "cumulative_length_mm": order * BASELINE_LENGTH_MM,
                "z0_ohm_ideal": trace.z0_ohm,
                "delay_ns_for_trace": delay_ns,
                "cumulative_ideal_delay_ns": total_delay_ns,
                "rs_ignored": trace.rs_skin,
                "gd_ignored": trace.gd_dielectric,
                **per_mm,
            }
        )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def plot_results(waveforms: dict[str, np.ndarray]) -> list[Path]:
    plot_dir = OUT_DIR / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    time = get_trace(waveforms, "time")
    if time is None:
        raise RuntimeError("Raw file missing time trace")
    t_ns = time * 1e9
    series = [
        ("input stimulus", "v(in_dig)", "#888888", 1.2, 0.35, "-"),
        ("driver side", "v(src_driver)", "#9467bd", 1.8, 1.0, "-"),
        ("after Trace01", "v(after_trace01)", "#1f77b4", 1.8, 1.0, "-"),
        ("after Trace02", "v(after_trace02)", "#ff7f0e", 1.8, 1.0, "--"),
        ("after Trace03 / far end", "v(pad_cascade)", "#2ca02c", 2.2, 1.0, "-"),
    ]
    paths = []

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    for label, trace_name, color, lw, alpha, ls in series:
        wave = get_trace(waveforms, trace_name)
        if wave is not None:
            ax.plot(t_ns, wave, color=color, lw=lw, alpha=alpha, ls=ls, label=label)
    ax.set_title(f"Hibiki {MODEL_NAME}: cascaded Wmodel baseline traces")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    out = plot_dir / "hibiki_wmodel_cascade_full_overlay.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    paths.append(out)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    vin = get_trace(waveforms, "v(in_dig)")
    far = get_trace(waveforms, "v(pad_cascade)")
    if vin is not None:
        ax.plot(t_ns, vin, color="#888888", lw=1.2, alpha=0.35, label="input stimulus")
    if far is not None:
        ax.plot(t_ns, far, color="#2ca02c", lw=2.4, label="far end after Trace03")
    ax.set_title("Cascaded Wmodel baseline: far-end waveform")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    out = plot_dir / "hibiki_wmodel_cascade_far_end_only.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    paths.append(out)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    if vin is not None:
        ax.plot(t_ns, vin, color="#888888", lw=1.2, alpha=0.35, label="input stimulus")
    if far is not None:
        ax.plot(t_ns, far, color="#2ca02c", lw=2.4, label="far end after Trace03")
    ax.set_xlim(8.5, 18.0)
    ax.set_ylim(-0.04, 0.62)
    ax.set_title("Cascaded Wmodel baseline: far-end first rising edge")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    out = plot_dir / "hibiki_wmodel_cascade_far_end_first_rise_zoom.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    paths.append(out)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    for label, trace_name, color, lw, alpha, ls in series:
        wave = get_trace(waveforms, trace_name)
        if wave is not None:
            ax.plot(t_ns, wave, color=color, lw=lw, alpha=alpha, ls=ls, label=label)
    ax.set_xlim(8.5, 18.0)
    ax.set_ylim(-0.04, 0.62)
    ax.set_title("Cascaded traces: first rising edge zoom")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    out = plot_dir / "hibiki_wmodel_cascade_first_rise_zoom.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    paths.append(out)

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.6), sharex=True)
    for label, trace_name, color, lw, alpha, ls in series[1:]:
        wave = get_trace(waveforms, trace_name)
        if wave is not None:
            axes[0].plot(t_ns, wave, color=color, lw=lw, alpha=alpha, ls=ls, label=label)
    ku = get_trace(waveforms, "v(xhibiki.ku)")
    kd = get_trace(waveforms, "v(xhibiki.kd)")
    if ku is not None:
        axes[1].plot(t_ns, ku, color="#d62728", lw=1.5, label="Ku")
    if kd is not None:
        axes[1].plot(t_ns, kd, color="#1f77b4", lw=1.5, label="Kd")
    axes[0].set_title("Cascade nodes and pybis coefficients")
    axes[0].set_ylabel("Voltage (V)")
    axes[1].set_ylabel("Coefficient")
    axes[1].set_xlabel("Time (ns)")
    for ax in axes:
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
    out = plot_dir / "hibiki_wmodel_cascade_nodes_plus_kukd.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    paths.append(out)

    return paths


def write_readme(traces: list[WTrace], bench_path: Path, raw_path: Path, log_path: Path, conversion_csv: Path, metrics_csv: Path, plots: list[Path]) -> None:
    ideal_total_delay_ns = sum(trace.delay_s_per_m * (BASELINE_LENGTH_MM / 1000.0) * 1e9 for trace in traces)
    lines = [
        f"# Hibiki {MODEL_NAME} with cascaded Wmodel baseline traces",
        "",
        "This run cascades the three Wmodel traces in this order:",
        "",
        "1. `Wmodel_Trace01::Sig`",
        "2. `Wmodel_Trace02::Sig`",
        "3. `Wmodel_Trace03::Sig`",
        "",
        "Important limitations:",
        "",
        "- The HSPICE W-element definitions are not directly usable as ngspice channels.",
        "- This run converts only `Ro`, `Lo`, `Go`, and `Co` into RLGC ladders.",
        "- `Rs` skin-effect loss is ignored in this baseline.",
        "- `Gd` dielectric-loss is ignored; in this file it is zero for all three traces.",
        f"- `Wmodel.sp` has model definitions but no channel instance length, so each trace assumes `{BASELINE_LENGTH_MM:g} mm`.",
        "",
        "Simulation setup:",
        "",
        f"- IBIS: `{IBIS_PATH.relative_to(ROOT)}`",
        f"- Component: `{COMPONENT_NAME}`",
        f"- Model: `{MODEL_NAME}`",
        f"- Stimulus: five `20 ns` high / `20 ns` low pulses, `5 ps` input edge",
        f"- Load: `{R_LOAD_OHM:g} ohm` to ground at the end of Trace03",
        f"- Total assumed channel length: `{BASELINE_LENGTH_MM * len(traces):g} mm`",
        f"- Ideal LC delay estimate for full cascade: `{ideal_total_delay_ns:.3f} ns`",
        f"- RLGC ladder sections: `{LADDER_SECTIONS}` per trace, `{LADDER_SECTIONS * len(traces)}` total",
        "",
        "Artifacts:",
        "",
        f"- Bench: `{bench_path.relative_to(OUT_DIR)}`",
        f"- Raw: `{raw_path.relative_to(OUT_DIR)}`",
        f"- Log: `{log_path.relative_to(OUT_DIR)}`",
        f"- Conversion summary: `{conversion_csv.relative_to(OUT_DIR)}`",
        f"- Waveform metrics: `{metrics_csv.relative_to(OUT_DIR)}`",
    ]
    for plot in plots:
        lines.append(f"- Plot: `{plot.relative_to(OUT_DIR)}`")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    traces = parse_wmodel(WMODEL_PATH)
    subckt_path, subckt_name = prepare_ibis_dut(
        IbisDutConfig(
            label="hibiki_wmodel_cascade",
            ibis=str(IBIS_PATH),
            component=COMPONENT_NAME,
            model=MODEL_NAME,
            corner="Typical",
        ),
        OUT_DIR / "converted",
    )
    bench_path, raw_path, _stop_ns = write_bench(traces, subckt_path, subckt_name)
    log_path = run_ngspice(bench_path, raw_path)
    waveforms = parse_ngspice_raw(raw_path)
    conversion_csv = write_conversion_summary(traces)
    metrics_csv = write_metrics(waveforms)
    plots = plot_results(waveforms)
    write_readme(traces, bench_path, raw_path, log_path, conversion_csv, metrics_csv, plots)
    (OUT_DIR / "run_config.json").write_text(
        json.dumps(
            {
                "baseline_length_mm_per_trace": BASELINE_LENGTH_MM,
                "trace_order": [trace.model_name for trace in traces],
                "total_length_mm": BASELINE_LENGTH_MM * len(traces),
                "ladder_sections_per_trace": LADDER_SECTIONS,
                "r_load_ohm": R_LOAD_OHM,
                "vdd": VDD,
                "wmodel": str(WMODEL_PATH.relative_to(ROOT)),
                "ibis": str(IBIS_PATH.relative_to(ROOT)),
                "model": MODEL_NAME,
                "component": COMPONENT_NAME,
                "conversion": "Ro/Lo/Go/Co only; Rs/Gd ignored",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote cascaded Wmodel baseline run to {OUT_DIR}")
    for plot in plots:
        print(f"Plot: {plot}")


if __name__ == "__main__":
    main()
