from __future__ import annotations

import csv
import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ngspice_lab import (
    DEFAULT_NGSPICE,
    IbisDutConfig,
    StimulusConfig,
    clean_label,
    get_trace,
    parse_ngspice_raw,
    prepare_ibis_dut,
    pwl_source,
    stimulus_points,
)


ROOT = Path(__file__).resolve().parents[1]
IBIS_PATH = ROOT / "pcbauto" / "Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs"
WMODEL_PATH = ROOT / "pcbauto" / "Wmodel.sp"
OUT_DIR = ROOT / "results" / "hibiki_i3c_tx_0p125ma_wmodel_baseline_ngspice_2026-05-29"
MODEL_NAME = "I3C_TX_0p125mA_tx"
COMPONENT_NAME = "A11486_IBIS-00001760"

# Wmodel.sp has model definitions only, not W-element instances, so the physical
# channel length is not present in the file. Use a board-like 100 mm baseline.
BASELINE_LENGTH_MM = 100.0
LADDER_SECTIONS = 80
R_LOAD_OHM = 1160.0
VDD = 1.2
MAX_STEP_PS = 10.0


@dataclass
class WTrace:
    model_name: str
    tag: str
    lo_h_per_m: float
    co_f_per_m: float
    ro_ohm_per_m: float
    go_s_per_m: float
    rs_skin: float
    gd_dielectric: float

    @property
    def z0_ohm(self) -> float:
        return math.sqrt(self.lo_h_per_m / self.co_f_per_m)

    @property
    def delay_s_per_m(self) -> float:
        return math.sqrt(self.lo_h_per_m * self.co_f_per_m)

    def per_mm(self) -> dict[str, float]:
        return {
            "r_ohm_per_mm": self.ro_ohm_per_m / 1000.0,
            "l_nh_per_mm": self.lo_h_per_m * 1e9 / 1000.0,
            "g_us_per_mm": self.go_s_per_m * 1e6 / 1000.0,
            "c_pf_per_mm": self.co_f_per_m * 1e12 / 1000.0,
        }


def _extract_param(block: str, name: str) -> float:
    match = re.search(
        name + r"\s*=\s*(?:\+\s*)?([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise ValueError(f"Missing Wmodel parameter {name}")
    return float(match.group(1))


def parse_wmodel(path: Path) -> list[WTrace]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    traces = []
    for match in re.finditer(r"\.Model\s+(\S+)\s+W\s+(.*?)(?=\n\s*\.Model|\Z)", text, flags=re.IGNORECASE | re.DOTALL):
        model_name = match.group(1)
        block = match.group(2)
        tag_match = re.search(r"Trace(\d+)", model_name, flags=re.IGNORECASE)
        tag = f"trace{tag_match.group(1)}" if tag_match else clean_label(model_name).lower()
        traces.append(
            WTrace(
                model_name=model_name,
                tag=tag,
                lo_h_per_m=_extract_param(block, "Lo"),
                co_f_per_m=_extract_param(block, "Co"),
                ro_ohm_per_m=_extract_param(block, "Ro"),
                go_s_per_m=_extract_param(block, "Go"),
                rs_skin=_extract_param(block, "Rs"),
                gd_dielectric=_extract_param(block, "Gd"),
            )
        )
    if not traces:
        raise ValueError(f"No W MODELTYPE=RLGC definitions found in {path}")
    return traces


def append_rlgc_ladder(lines: list[str], trace: WTrace, src_node: str, pad_node: str) -> None:
    per_mm = trace.per_mm()
    length_per_section_mm = BASELINE_LENGTH_MM / LADDER_SECTIONS
    r_seg = max(per_mm["r_ohm_per_mm"] * length_per_section_mm, 1e-9)
    l_seg_nh = max(per_mm["l_nh_per_mm"] * length_per_section_mm, 1e-12)
    c_seg_pf = max(per_mm["c_pf_per_mm"] * length_per_section_mm, 1e-12)
    g_seg_s = max(per_mm["g_us_per_mm"] * 1e-6 * length_per_section_mm, 0.0)

    node_a = src_node
    for index in range(1, LADDER_SECTIONS + 1):
        node_b = pad_node if index == LADDER_SECTIONS else f"ch_{trace.tag}_{index}"
        mid = f"ch_{trace.tag}_{index}_rl"
        lines.append(f"RCH_{trace.tag}_{index} {node_a} {mid} {r_seg:g}")
        lines.append(f"LCH_{trace.tag}_{index} {mid} {node_b} {l_seg_nh:g}n")
        lines.append(f"CCH_{trace.tag}_{index} {node_b} 0 {c_seg_pf:g}p")
        if g_seg_s > 0.0:
            lines.append(f"RGCH_{trace.tag}_{index} {node_b} 0 {1.0 / g_seg_s:g}")
        node_a = node_b


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
    bench_path = bench_dir / "hibiki_wmodel_baseline.sp"
    raw_path = raw_dir / "hibiki_wmodel_baseline.raw"

    lines = [
        "* Hibiki I3C_TX_0p125mA_tx through Wmodel baseline RLGC conversion",
        "* Baseline conversion uses Ro/Lo/Go/Co only; Rs and Gd are documented but ignored.",
        f"* Wmodel source: {WMODEL_PATH.as_posix()}",
        f"* Baseline length: {BASELINE_LENGTH_MM:g} mm, ladder sections: {LADDER_SECTIONS:d}",
        ".temp 25",
        ".options method=gear maxord=2 reltol=1e-4 abstol=1e-12 vntol=1e-7 gmin=1e-12",
        f"Vin in_dig 0 {pwl_source(points)}",
        f"Ven en_sig 0 DC {VDD:g}",
        f"Vdd vdd 0 DC {VDD:g}",
        f".include '{subckt_path.as_posix()}'",
    ]

    save_vars = ["V(in_dig)"]
    for trace in traces:
        src_node = f"src_{trace.tag}"
        pad_node = f"pad_{trace.tag}"
        inst_name = f"X{trace.tag}"
        lines.append("")
        lines.append(f"* {trace.model_name}: Ro/Lo/Go/Co baseline, Rs={trace.rs_skin:g} ignored, Gd={trace.gd_dielectric:g} ignored")
        lines.append(f"{inst_name} {src_node} in_dig en_sig vdd 0 {subckt_name}")
        append_rlgc_ladder(lines, trace, src_node, pad_node)
        lines.append(f"RLOAD_{trace.tag} {pad_node} 0 {R_LOAD_OHM:g}")
        save_vars.extend([f"V({src_node})", f"V({pad_node})", f"V({inst_name.lower()}.ku)", f"V({inst_name.lower()}.kd)"])

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


def write_trace_summary(traces: list[WTrace]) -> Path:
    csv_path = OUT_DIR / "wmodel_baseline_conversion.csv"
    rows = []
    for trace in traces:
        per_mm = trace.per_mm()
        rows.append(
            {
                "trace": trace.tag,
                "wmodel_name": trace.model_name,
                "baseline_length_mm": BASELINE_LENGTH_MM,
                "ladder_sections": LADDER_SECTIONS,
                "ro_ohm_per_m": trace.ro_ohm_per_m,
                "lo_h_per_m": trace.lo_h_per_m,
                "go_s_per_m": trace.go_s_per_m,
                "co_f_per_m": trace.co_f_per_m,
                "rs_ignored": trace.rs_skin,
                "gd_ignored": trace.gd_dielectric,
                "z0_ohm_ideal": trace.z0_ohm,
                "delay_ns_for_baseline_length": trace.delay_s_per_m * (BASELINE_LENGTH_MM / 1000.0) * 1e9,
                **per_mm,
            }
        )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def _first_crossing_time(t_ns: np.ndarray, y: np.ndarray, level: float, window: tuple[float, float]) -> float | None:
    mask = (t_ns >= window[0]) & (t_ns <= window[1])
    tx = t_ns[mask]
    yy = y[mask]
    if len(tx) < 2:
        return None
    for idx in range(1, len(tx)):
        y0 = yy[idx - 1]
        y1 = yy[idx]
        if (y0 <= level <= y1) or (y1 <= level <= y0):
            if math.isclose(y0, y1):
                return float(tx[idx])
            frac = (level - y0) / (y1 - y0)
            return float(tx[idx - 1] + frac * (tx[idx] - tx[idx - 1]))
    return None


def write_waveform_metrics(traces: list[WTrace], waveforms: dict[str, np.ndarray]) -> Path:
    csv_path = OUT_DIR / "waveform_metrics.csv"
    time = get_trace(waveforms, "time")
    if time is None:
        raise RuntimeError("Raw file missing time trace")
    t_ns = time * 1e9
    rows = []
    for trace in traces:
        pad = get_trace(waveforms, f"v(pad_{trace.tag})")
        src = get_trace(waveforms, f"v(src_{trace.tag})")
        if pad is None:
            continue
        first_rise_mask = (t_ns >= 10.0) & (t_ns <= 30.0)
        rise_min = float(np.min(pad[first_rise_mask])) if np.any(first_rise_mask) else float(np.min(pad))
        rise_max = float(np.max(pad[first_rise_mask])) if np.any(first_rise_mask) else float(np.max(pad))
        rise_10 = rise_min + 0.1 * (rise_max - rise_min)
        rise_90 = rise_min + 0.9 * (rise_max - rise_min)
        t10 = _first_crossing_time(t_ns, pad, rise_10, (10.0, 30.0))
        t90 = _first_crossing_time(t_ns, pad, rise_90, (10.0, 30.0))
        rows.append(
            {
                "trace": trace.tag,
                "pad_min_v": float(np.min(pad)),
                "pad_max_v": float(np.max(pad)),
                "src_min_v": float(np.min(src)) if src is not None else "",
                "src_max_v": float(np.max(src)) if src is not None else "",
                "first_rise_10pct_time_ns": t10 if t10 is not None else "",
                "first_rise_90pct_time_ns": t90 if t90 is not None else "",
                "first_rise_10_90_ns": (t90 - t10) if t10 is not None and t90 is not None else "",
            }
        )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def plot_results(traces: list[WTrace], waveforms: dict[str, np.ndarray]) -> list[Path]:
    plot_dir = OUT_DIR / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    time = get_trace(waveforms, "time")
    if time is None:
        raise RuntimeError("Raw file missing time trace")
    t_ns = time * 1e9
    vin = get_trace(waveforms, "v(in_dig)")
    styles = {
        "trace01": {"color": "#1f77b4", "ls": "-", "lw": 2.2, "zorder": 4},
        "trace02": {"color": "#ff7f0e", "ls": "--", "lw": 2.1, "zorder": 5},
        "trace03": {"color": "#2ca02c", "ls": "-", "lw": 2.0, "zorder": 3},
    }
    paths = []

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    if vin is not None:
        ax.plot(t_ns, vin, color="#555555", lw=1.3, alpha=0.45, label="input stimulus")
    for trace in traces:
        pad = get_trace(waveforms, f"v(pad_{trace.tag})")
        if pad is not None:
            style = styles.get(trace.tag, {"color": None, "ls": "-", "lw": 2.0, "zorder": 3})
            ax.plot(t_ns, pad, label=f"{trace.tag} pad", **style)
    ax.set_title(f"Hibiki {MODEL_NAME}: Wmodel baseline channel comparison")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    out = plot_dir / "hibiki_wmodel_baseline_pad_overlay.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    paths.append(out)

    fig, axes = plt.subplots(len(traces), 1, figsize=(11.5, 8.2), sharex=True)
    for ax, trace in zip(axes, traces):
        src = get_trace(waveforms, f"v(src_{trace.tag})")
        pad = get_trace(waveforms, f"v(pad_{trace.tag})")
        if src is not None:
            ax.plot(t_ns, src, color="#9467bd", lw=1.6, label="driver side")
        if pad is not None:
            style = styles.get(trace.tag, {"color": None, "ls": "-", "lw": 2.0, "zorder": 3})
            ax.plot(t_ns, pad, label="load side", **style)
        ax.set_title(f"{trace.tag}: {trace.model_name}, Z0~{trace.z0_ohm:.1f} ohm")
        ax.set_ylabel("V")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
    axes[-1].set_xlabel("Time (ns)")
    out = plot_dir / "hibiki_wmodel_baseline_source_vs_load.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    paths.append(out)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    if vin is not None:
        ax.plot(t_ns, vin, color="#555555", lw=1.2, alpha=0.35, label="input stimulus")
    for trace in traces:
        pad = get_trace(waveforms, f"v(pad_{trace.tag})")
        if pad is not None:
            style = styles.get(trace.tag, {"color": None, "ls": "-", "lw": 2.0, "zorder": 3})
            ax.plot(t_ns, pad, label=f"{trace.tag} pad", **style)
    ax.set_xlim(8.5, 16.0)
    ax.set_ylim(-0.03, 0.62)
    ax.set_title("First rising edge zoom")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    out = plot_dir / "hibiki_wmodel_baseline_first_rise_zoom.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    paths.append(out)

    return paths


def write_readme(
    traces: list[WTrace],
    bench_path: Path,
    raw_path: Path,
    log_path: Path,
    plots: list[Path],
    summary_csv: Path,
    metrics_csv: Path,
) -> None:
    lines = [
        f"# Hibiki {MODEL_NAME} with Wmodel baseline channel conversion",
        "",
        "This is a first-pass ngspice-compatible baseline conversion of `pcbauto/Wmodel.sp`.",
        "",
        "Important limitations:",
        "",
        "- The HSPICE W-element definitions are not directly usable as ngspice channels.",
        "- This run converts only `Ro`, `Lo`, `Go`, and `Co` into an RLGC ladder.",
        "- `Rs` skin-effect loss is ignored in this baseline.",
        "- `Gd` dielectric-loss is ignored; in this file it is zero for all three traces.",
        "- `Wmodel.sp` has model definitions but no channel instance length, so this run assumes `100 mm`.",
        "",
        "Simulation setup:",
        "",
        f"- IBIS: `{IBIS_PATH.relative_to(ROOT)}`",
        f"- Component: `{COMPONENT_NAME}`",
        f"- Model: `{MODEL_NAME}`",
        f"- Stimulus: five `20 ns` high / `20 ns` low pulses, `5 ps` input edge",
        f"- Load: `{R_LOAD_OHM:g} ohm` to ground at the far end of each trace",
        f"- Channel length assumption: `{BASELINE_LENGTH_MM:g} mm`",
        f"- RLGC ladder sections: `{LADDER_SECTIONS}`",
        "",
        "Artifacts:",
        "",
        f"- Bench: `{bench_path.relative_to(OUT_DIR)}`",
        f"- Raw: `{raw_path.relative_to(OUT_DIR)}`",
        f"- Log: `{log_path.relative_to(OUT_DIR)}`",
        f"- Conversion summary: `{summary_csv.relative_to(OUT_DIR)}`",
        f"- Waveform metrics: `{metrics_csv.relative_to(OUT_DIR)}`",
    ]
    for plot in plots:
        lines.append(f"- Plot: `{plot.relative_to(OUT_DIR)}`")
    lines.extend(["", "Trace summary:", ""])
    lines.append("| Trace | Wmodel | Z0 approx | Delay for 100 mm | Rs ignored |")
    lines.append("|---|---|---:|---:|---:|")
    for trace in traces:
        delay_ns = trace.delay_s_per_m * (BASELINE_LENGTH_MM / 1000.0) * 1e9
        lines.append(f"| `{trace.tag}` | `{trace.model_name}` | `{trace.z0_ohm:.2f} ohm` | `{delay_ns:.3f} ns` | `{trace.rs_skin:g}` |")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    traces = parse_wmodel(WMODEL_PATH)
    converted_dir = OUT_DIR / "converted"
    subckt_path, subckt_name = prepare_ibis_dut(
        IbisDutConfig(
            label="hibiki_wmodel_baseline",
            ibis=str(IBIS_PATH),
            component=COMPONENT_NAME,
            model=MODEL_NAME,
            corner="Typical",
        ),
        converted_dir,
    )
    bench_path, raw_path, _stop_ns = write_bench(traces, subckt_path, subckt_name)
    log_path = run_ngspice(bench_path, raw_path)
    waveforms = parse_ngspice_raw(raw_path)
    summary_csv = write_trace_summary(traces)
    metrics_csv = write_waveform_metrics(traces, waveforms)
    plots = plot_results(traces, waveforms)
    write_readme(traces, bench_path, raw_path, log_path, plots, summary_csv, metrics_csv)
    (OUT_DIR / "run_config.json").write_text(
        json.dumps(
            {
                "baseline_length_mm": BASELINE_LENGTH_MM,
                "ladder_sections": LADDER_SECTIONS,
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
    print(f"Wrote Wmodel baseline run to {OUT_DIR}")
    for plot in plots:
        print(f"Plot: {plot}")


if __name__ == "__main__":
    main()
