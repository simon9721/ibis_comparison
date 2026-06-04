from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results" / "hspice_rsf_io_buf_inv_chain_2026-06-04"


@dataclass(frozen=True)
class Case:
    key: str
    title: str
    source_dir: Path
    ibis_name: str
    ibis_model: str
    model_type: str
    supply_v: float
    rise_start_ns: float
    fall_start_ns: float
    edge_ps: float
    high_time_ns: float
    native_stop_ns: float
    spice_stop_ns: float
    pybis_raw_name: str
    ref_raw_name: str
    pybis_pad_signal: str
    pybis_load_signal: str
    ref_pad_signal: str
    ref_load_signal: str


CASES = [
    Case(
        key="io_buf",
        title="io_buf",
        source_dir=ROOT / "clean_ibis_vs_pybis_matched_pkg",
        ibis_name="io_buf.ibs",
        ibis_model="driver",
        model_type="io",
        supply_v=3.3,
        rise_start_ns=1.0,
        fall_start_ns=9.0,
        edge_ps=5.0,
        high_time_ns=8.0,
        native_stop_ns=12.0,
        spice_stop_ns=14.0,
        pybis_raw_name="tb_ibis_vs_pybis_rsf_12n_batch.raw",
        ref_raw_name="tb_refspice_rsf_14n_batch.raw",
        pybis_pad_signal="v(pad)",
        pybis_load_signal="v(ntst)",
        ref_pad_signal="v(pad_ref)",
        ref_load_signal="v(ntst_ref)",
    ),
    Case(
        key="inv_chain",
        title="inv_chain",
        source_dir=ROOT / "inv_chain" / "clean_ibis_vs_pybis_matched_pkg",
        ibis_name="t2b_0615_v5.ibs",
        ibis_model="driver2",
        model_type="output",
        supply_v=1.8,
        rise_start_ns=1.0,
        fall_start_ns=4.0,
        edge_ps=5.0,
        high_time_ns=3.0,
        native_stop_ns=6.5,
        spice_stop_ns=7.0,
        pybis_raw_name="tb_ibis_vs_pybis_rsf_6p5n_batch.raw",
        ref_raw_name="tb_refspice_rsf_7n_batch.raw",
        pybis_pad_signal="v(pad)",
        pybis_load_signal="v(ntst)",
        ref_pad_signal="v(pad_ref)",
        ref_load_signal="v(ntst_ref)",
    ),
]


@dataclass
class IbisWaveform:
    kind: str
    r_fix: float
    v_fix: float
    time_s: np.ndarray
    v_typ: np.ndarray


def ns(value_s: np.ndarray | float) -> np.ndarray | float:
    return value_s * 1e9


def ps(value_s: np.ndarray | float) -> np.ndarray | float:
    return value_s * 1e12


def clean_path(path: Path) -> str:
    return path.as_posix()


def copy_common_files(case: Case, bench_dir: Path) -> None:
    bench_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(case.source_dir / case.ibis_name, bench_dir / case.ibis_name)
    if case.key == "io_buf":
        shutil.copy2(case.source_dir / "io_buf.sp", bench_dir / "io_buf.sp")
        shutil.copy2(case.source_dir / "hspice_ngspice.mod", bench_dir / "hspice_ngspice.mod")
    elif case.key == "inv_chain":
        shutil.copy2(case.source_dir / "invchain_ref_ngspice.sub", bench_dir / "invchain_ref_ngspice.sub")
        shutil.copy2(case.source_dir / "HL18G-S3.7S.lib", bench_dir / "HL18G-S3.7S.lib")
    else:
        raise ValueError(case.key)


def make_native_deck(case: Case) -> str:
    high = case.supply_v
    edge = f"{case.edge_ps:g}p"
    rise = f"{case.rise_start_ns:g}n"
    fall = f"{case.fall_start_ns:g}n"
    fall_edge_end = f"{case.fall_start_ns + case.edge_ps * 1e-3:g}n"
    rise_edge_end = f"{case.rise_start_ns + case.edge_ps * 1e-3:g}n"

    if case.model_type == "io":
        ibis_instance = f"""Ven en_sig 0 DC {high:g}
VPU pu_ref 0 DC {high:g}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {high:g}
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig en_sig dig_q pc_ref gc_ref
+ file='{case.ibis_name}'
+ model='{case.ibis_model}'
+ typ=typ
+ power=off
+ ramp_rwf=2
+ ramp_fwf=2

Rdig dig_q 0 1k
"""
        probes = "V(in_dig) V(pad_ibis) V(ntst_ibis) V(dig_q)"
    else:
        ibis_instance = f"""VPU pu_ref 0 DC {high:g}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {high:g}
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='{case.ibis_name}'
+ model='{case.ibis_model}'
+ buffer=2
+ typ=typ
+ power=off
+ ramp_rwf=2
+ ramp_fwf=2
"""
        probes = "V(in_dig) V(pad_ibis) V(ntst_ibis)"

    return f"""* Generated HSPICE native IBIS RSF bench for {case.title}
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL(0 0 {rise} 0 {rise_edge_end} {high:g} {fall} {high:g} {fall_edge_end} 0)

{ibis_instance}
TIBIS pad_ibis 0 ntst_ibis 0 Z0=50 TD=30p
RIBIS ntst_ibis 0 50

.probe tran {probes}
.tran 10p {case.native_stop_ns:g}n
.end
"""


def make_spice_deck(case: Case) -> str:
    high = case.supply_v
    edge = f"{case.edge_ps:g}p"
    rise = f"{case.rise_start_ns:g}n"
    high_time = f"{case.high_time_ns:g}n"

    if case.key == "io_buf":
        body = f"""Vin in_src 0 PULSE(0 {high:g} {rise} {edge} {edge} {high_time} 20n)
Rin in_src in_dig 1

Vdd_ref vdd_ref_src 0 DC {high:g}
Voe_ref oe_ref_src 0 DC {high:g}
Rvdd_ref vdd_ref_src vdd_ref 1
Roe_ref oe_ref_src oe_ref 1
Cdec_ref vdd_ref 0 10p

.include 'hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF
TREF pad_ref 0 ntst_ref 0 Z0=50 TD=30p
RREF ntst_ref 0 50

.probe tran V(in_dig) V(pad_ref) V(ntst_ref) V(in_sense_ref)
"""
    elif case.key == "inv_chain":
        body = f"""Vin in_src 0 PULSE(0 {high:g} {rise} {edge} {edge} {high_time} 20n)
Rin in_src in_dig 1

Vdd_ref vdd_ref_src 0 DC {high:g}
Rvdd_ref vdd_ref_src vdd_ref 1
Cdec_ref vdd_ref 0 10p

.include 'invchain_ref_ngspice.sub'

XREF in_dig pad_ref vdd_ref 0 invchain_ref
TREF pad_ref 0 ntst_ref 0 Z0=50 TD=30p
RREF ntst_ref 0 50

.probe tran V(in_dig) V(pad_ref) V(ntst_ref)
"""
    else:
        raise ValueError(case.key)

    return f"""* Generated HSPICE transistor/subcircuit RSF bench for {case.title}
.option post=2 probe accurate
.temp 27

{body}
.tran 10p {case.spice_stop_ns:g}n
.end
"""


def run_hspice(deck: Path, out_prefix: str) -> tuple[int, Path]:
    cmd = ["hspice", "-i", deck.name, "-o", out_prefix]
    completed = subprocess.run(
        cmd,
        cwd=deck.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    stdout_path = deck.parent / f"{out_prefix}.stdout.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8", errors="replace")
    return completed.returncode, stdout_path


def parse_ibis_waveforms(path: Path) -> list[IbisWaveform]:
    lines = path.read_text(errors="replace").splitlines()
    waveforms: list[IbisWaveform] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped not in ("[Rising Waveform]", "[Falling Waveform]"):
            i += 1
            continue
        kind = "Rising" if "Rising" in stripped else "Falling"
        i += 1
        r_fix = None
        v_fix = None
        samples: list[tuple[float, float]] = []
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped or stripped.startswith("|"):
                i += 1
                continue
            if stripped.startswith("["):
                break
            lower = stripped.lower()
            if lower.startswith("r_fixture"):
                r_fix = float(stripped.split("=", 1)[1].strip())
                i += 1
                continue
            if lower.startswith("v_fixture"):
                v_fix = float(stripped.split("=", 1)[1].strip().rstrip("Vv"))
                i += 1
                continue
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    samples.append((parse_ibis_time(parts[0]), parse_ibis_voltage(parts[1])))
                except ValueError:
                    pass
            i += 1
        if r_fix is not None and v_fix is not None and samples:
            arr = np.asarray(samples, dtype=float)
            waveforms.append(IbisWaveform(kind, r_fix, v_fix, arr[:, 0], arr[:, 1]))
    if not waveforms:
        raise RuntimeError(f"No IBIS waveforms found in {path}")
    return waveforms


def parse_ibis_time(value: str) -> float:
    return parse_scaled_ibis_value(
        value,
        {
            "": 1.0,
            "s": 1.0,
            "fs": 1e-15,
            "ps": 1e-12,
            "p": 1e-12,
            "ns": 1e-9,
            "n": 1e-9,
            "us": 1e-6,
            "u": 1e-6,
            "ms": 1e-3,
            "m": 1e-3,
        },
    )


def parse_ibis_voltage(value: str) -> float:
    return parse_scaled_ibis_value(
        value,
        {
            "": 1.0,
            "v": 1.0,
            "mv": 1e-3,
            "uv": 1e-6,
            "nv": 1e-9,
            "kv": 1e3,
        },
    )


def parse_scaled_ibis_value(value: str, units: dict[str, float]) -> float:
    text = value.strip().rstrip(",")
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([A-Za-z]*)", text)
    if not match:
        raise ValueError(value)
    unit = match.group(2).lower()
    if unit not in units:
        raise ValueError(value)
    return float(match.group(1)) * units[unit]


def choose_waveform(waveforms: list[IbisWaveform], kind: str) -> IbisWaveform:
    candidates = [wf for wf in waveforms if wf.kind == kind]
    if not candidates:
        raise RuntimeError(f"No {kind} waveform found")
    return min(candidates, key=lambda wf: (abs(wf.r_fix - 50.0), abs(wf.v_fix - 0.0)))


def build_ibis_rsf(time_s: np.ndarray, case: Case, rise_wf: IbisWaveform, fall_wf: IbisWaveform) -> np.ndarray:
    out = np.empty_like(time_s)
    low_v = float(rise_wf.v_typ[0])
    rise_end_v = float(rise_wf.v_typ[-1])
    fall_end_v = float(fall_wf.v_typ[-1])
    rise_start_s = case.rise_start_ns * 1e-9
    fall_start_s = case.fall_start_ns * 1e-9
    for idx, t in enumerate(time_s):
        if t < rise_start_s:
            out[idx] = low_v
        elif t < fall_start_s:
            dt = t - rise_start_s
            out[idx] = np.interp(dt, rise_wf.time_s, rise_wf.v_typ) if dt <= rise_wf.time_s[-1] else rise_end_v
        else:
            dt = t - fall_start_s
            out[idx] = np.interp(dt, fall_wf.time_s, fall_wf.v_typ) if dt <= fall_wf.time_s[-1] else fall_end_v
    return out


def resolve(data: dict[str, np.ndarray], wanted: str) -> np.ndarray:
    if wanted in data:
        return data[wanted]
    lower = wanted.lower()
    for key, value in data.items():
        if key.lower() == lower:
            return value
    raise KeyError(f"{wanted} not found; available: {', '.join(sorted(data))}")


def optional_ngspice_trace(case: Case, raw_name: str, signal: str) -> tuple[np.ndarray, np.ndarray] | None:
    path = case.source_dir / raw_name
    if not path.exists():
        return None
    data = parse_ngspice_raw(path)
    return data["time"], resolve(data, signal)


def crossing_time(time_s: np.ndarray, values: np.ndarray, threshold: float, start_s: float, end_s: float, rising: bool) -> float | None:
    mask = (time_s >= start_s) & (time_s <= end_s)
    t = time_s[mask]
    y = values[mask]
    if len(t) < 2:
        return None
    delta = y - threshold
    for i in range(len(t) - 1):
        a = delta[i]
        b = delta[i + 1]
        if rising and a <= 0 <= b:
            frac = 0.0 if b == a else -a / (b - a)
            return float(t[i] + frac * (t[i + 1] - t[i]))
        if not rising and a >= 0 >= b:
            frac = 0.0 if b == a else a / (a - b)
            return float(t[i] + frac * (t[i + 1] - t[i]))
    return None


def rmse_on_common_grid(
    ref_t: np.ndarray,
    ref_y: np.ndarray,
    other_t: np.ndarray,
    other_y: np.ndarray,
    start_s: float,
    end_s: float,
) -> tuple[float, float]:
    start = max(start_s, float(ref_t[0]), float(other_t[0]))
    end = min(end_s, float(ref_t[-1]), float(other_t[-1]))
    if end <= start:
        return float("nan"), float("nan")
    n = min(5000, max(100, int((end - start) / 1e-12)))
    grid = np.linspace(start, end, n)
    diff = np.interp(grid, other_t, other_y) - np.interp(grid, ref_t, ref_y)
    return float(np.sqrt(np.mean(diff * diff))), float(np.max(np.abs(diff)))


def finite_stop_ns(data: dict[str, np.ndarray]) -> float:
    return float(ns(resolve(data, "time")[-1]))


def plot_case(
    case: Case,
    native: dict[str, np.ndarray],
    spice: dict[str, np.ndarray],
    rise_wf: IbisWaveform,
    fall_wf: IbisWaveform,
    plot_dir: Path,
) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    t_native = resolve(native, "time")
    t_spice = resolve(spice, "time")
    y_native_pad = resolve(native, "v(pad_ibis)")
    y_native_load = resolve(native, "v(ntst_ibis)")
    y_spice_pad = resolve(spice, "v(pad_ref)")
    y_spice_load = resolve(spice, "v(ntst_ref)")
    y_input = resolve(native, "v(in_dig)")

    t_max = min(float(t_native[-1]), float(t_spice[-1]), case.native_stop_ns * 1e-9)
    ibis_time = t_native[t_native <= t_max]
    ibis_pad = build_ibis_rsf(ibis_time, case, rise_wf, fall_wf)

    ng_pybis_pad = optional_ngspice_trace(case, case.pybis_raw_name, case.pybis_pad_signal)
    ng_ref_pad = optional_ngspice_trace(case, case.ref_raw_name, case.ref_pad_signal)
    ng_pybis_load = optional_ngspice_trace(case, case.pybis_raw_name, case.pybis_load_signal)
    ng_ref_load = optional_ngspice_trace(case, case.ref_raw_name, case.ref_load_signal)

    windows = [
        ("full", 0.0, t_max),
        (
            "rise zoom",
            (case.rise_start_ns - 0.05) * 1e-9,
            min((case.rise_start_ns + 3.5) * 1e-9, (case.fall_start_ns - 0.1) * 1e-9, t_max),
        ),
        ("fall zoom", (case.fall_start_ns - 0.05) * 1e-9, min((case.fall_start_ns + 2.3) * 1e-9, t_max)),
    ]

    def draw(path: Path, ylabel: str, native_y: np.ndarray, spice_y: np.ndarray, ibis_y: np.ndarray | None, ng_pybis, ng_ref) -> None:
        fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharey=False)
        for ax, (label, start, end) in zip(axes, windows):
            ax.plot(ns(t_native), native_y, label="HSPICE native IBIS", linewidth=2.0, color="#1f77b4")
            ax.plot(ns(t_spice), spice_y, label="HSPICE SPICE subckt", linewidth=1.8, color="#d62728", linestyle="--")
            if ibis_y is not None:
                ax.plot(ns(ibis_time), ibis_y, label="IBIS VT table stitch", linewidth=1.5, color="black", linestyle=":")
            if ng_pybis is not None:
                ax.plot(ns(ng_pybis[0]), ng_pybis[1], label="ngspice pybis", linewidth=1.1, color="#2ca02c", alpha=0.75)
            if ng_ref is not None:
                ax.plot(ns(ng_ref[0]), ng_ref[1], label="ngspice refspice", linewidth=1.1, color="#9467bd", alpha=0.75)
            ax.plot(ns(t_native), y_input, label="input", linewidth=0.9, color="0.45", alpha=0.65)
            ax.axvline(case.rise_start_ns, color="0.25", linestyle=":", linewidth=0.8)
            ax.axvline(case.fall_start_ns, color="0.25", linestyle=":", linewidth=0.8)
            ax.set_xlim(ns(start), ns(end))
            ax.set_title(label)
            ax.set_xlabel("Time (ns)")
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.25)
        handles, labels = axes[0].get_legend_handles_labels()
        fig.suptitle(f"{case.title}: HSPICE native IBIS vs HSPICE SPICE RSF", y=0.99)
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.96), ncol=3, fontsize=9)
        fig.tight_layout(rect=(0, 0, 1, 0.89))
        fig.savefig(path, dpi=180, bbox_inches="tight")
        plt.close(fig)

    draw(plot_dir / f"{case.key}_hspice_rsf_pad_overlay.png", "Pad voltage (V)", y_native_pad, y_spice_pad, ibis_pad, ng_pybis_pad, ng_ref_pad)
    draw(plot_dir / f"{case.key}_hspice_rsf_load_overlay.png", "Load voltage (V)", y_native_load, y_spice_load, None, ng_pybis_load, ng_ref_load)


def metrics_for_case(
    case: Case,
    native: dict[str, np.ndarray],
    spice: dict[str, np.ndarray],
    rise_wf: IbisWaveform,
    fall_wf: IbisWaveform,
) -> list[dict[str, object]]:
    t_native = resolve(native, "time")
    t_spice = resolve(spice, "time")
    y_native_pad = resolve(native, "v(pad_ibis)")
    y_native_load = resolve(native, "v(ntst_ibis)")
    y_spice_pad = resolve(spice, "v(pad_ref)")
    y_spice_load = resolve(spice, "v(ntst_ref)")
    t_max = min(float(t_native[-1]), float(t_spice[-1]), case.native_stop_ns * 1e-9)
    low = float(rise_wf.v_typ[0])
    high = float(rise_wf.v_typ[-1])
    threshold = 0.5 * (low + high)
    rise_start = case.rise_start_ns * 1e-9
    fall_start = case.fall_start_ns * 1e-9

    rows: list[dict[str, object]] = []
    for node, native_y, spice_y in [
        ("pad", y_native_pad, y_spice_pad),
        ("load", y_native_load, y_spice_load),
    ]:
        native_rise = crossing_time(t_native, native_y, threshold, rise_start, fall_start, True)
        spice_rise = crossing_time(t_spice, spice_y, threshold, rise_start, fall_start, True)
        native_fall = crossing_time(t_native, native_y, threshold, fall_start, t_max, False)
        spice_fall = crossing_time(t_spice, spice_y, threshold, fall_start, t_max, False)
        rmse, maxabs = rmse_on_common_grid(t_native, native_y, t_spice, spice_y, 0.0, t_max)
        rows.append(
            {
                "case": case.key,
                "node": node,
                "threshold_v": threshold,
                "native_rise_50_ns": ns(native_rise) if native_rise is not None else "",
                "spice_rise_50_ns": ns(spice_rise) if spice_rise is not None else "",
                "native_minus_spice_rise_50_ps": ps(native_rise - spice_rise) if native_rise is not None and spice_rise is not None else "",
                "native_fall_50_ns": ns(native_fall) if native_fall is not None else "",
                "spice_fall_50_ns": ns(spice_fall) if spice_fall is not None else "",
                "native_minus_spice_fall_50_ps": ps(native_fall - spice_fall) if native_fall is not None and spice_fall is not None else "",
                "native_vs_spice_rmse_mv": rmse * 1e3,
                "native_vs_spice_maxabs_mv": maxabs * 1e3,
                "native_stop_ns": finite_stop_ns(native),
                "spice_stop_ns": finite_stop_ns(spice),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_readme(rows: list[dict[str, object]], run_rows: list[dict[str, object]]) -> None:
    lines = [
        "# HSPICE RSF io_buf and inv_chain Comparison",
        "",
        "Generated by `py -3 scripts\\run_hspice_rsf_io_buf_inv_chain.py`.",
        "",
        "This bundle mirrors the clean ngspice RSF workflow for the two source-correlation cases:",
        "",
        "- `io_buf`: native HSPICE IBIS model `driver` from `io_buf.ibs` vs HSPICE transistor subcircuit from `io_buf.sp`.",
        "- `inv_chain`: native HSPICE IBIS model `driver2` from `t2b_0615_v5.ibs` vs HSPICE transistor subcircuit `invchain_ref`.",
        "",
        "Both cases use a rise-steady-fall input, a `50 ohm`, `30 ps` ideal observation line, and a `50 ohm` load to ground.",
        "",
        "## Artifacts",
        "",
        "- `run_summary.csv`: HSPICE return codes and generated `.tr0` paths.",
        "- `metrics_summary.csv`: 50% crossing and native-vs-SPICE error metrics.",
        "- `*/benches/`: copied source files, generated HSPICE decks, `.lis`, `.tr0`, and stdout captures.",
        "- `*/plots/`: pad and load overlays with full, rise-zoom, and fall-zoom panels.",
        "",
        "## Run Status",
        "",
        "| Case | Flow | Return code | TR0 |",
        "|---|---:|---:|---|",
    ]
    for row in run_rows:
        lines.append(f"| `{row['case']}` | `{row['flow']}` | `{row['returncode']}` | `{row['tr0']}` |")
    lines.extend(["", "## Metrics", "", "| Case | Node | Rise native-SPICE | Fall native-SPICE | RMSE | Max abs |", "|---|---|---:|---:|---:|---:|"])
    for row in rows:
        def fmt_ps(value: object) -> str:
            return "" if value == "" else f"{float(value):.2f} ps"

        lines.append(
            f"| `{row['case']}` | `{row['node']}` | "
            f"{fmt_ps(row['native_minus_spice_rise_50_ps'])} | "
            f"{fmt_ps(row['native_minus_spice_fall_50_ps'])} | "
            f"{float(row['native_vs_spice_rmse_mv']):.2f} mV | "
            f"{float(row['native_vs_spice_maxabs_mv']):.2f} mV |"
        )
    lines.append("")
    lines.append("Positive crossing delta means HSPICE native IBIS crossed later than HSPICE SPICE.")
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    all_metric_rows: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []
    for case in CASES:
        case_dir = OUT_DIR / case.key
        bench_dir = case_dir / "benches"
        plot_dir = case_dir / "plots"
        copy_common_files(case, bench_dir)

        native_deck = bench_dir / f"{case.key}_native_ibis.sp"
        spice_deck = bench_dir / f"{case.key}_spice_subckt.sp"
        native_deck.write_text(make_native_deck(case), encoding="ascii")
        spice_deck.write_text(make_spice_deck(case), encoding="ascii")

        for flow, deck, prefix in [
            ("native_ibis", native_deck, f"{case.key}_native_ibis"),
            ("spice_subckt", spice_deck, f"{case.key}_spice_subckt"),
        ]:
            rc, stdout_path = run_hspice(deck, prefix)
            tr0 = deck.parent / f"{prefix}.tr0"
            run_rows.append(
                {
                    "case": case.key,
                    "flow": flow,
                    "returncode": rc,
                    "deck": clean_path(deck.relative_to(OUT_DIR)),
                    "stdout": clean_path(stdout_path.relative_to(OUT_DIR)),
                    "tr0": clean_path(tr0.relative_to(OUT_DIR)) if tr0.exists() else "",
                }
            )
            print(f"{case.key} {flow}: rc={rc}, tr0={tr0.exists()}")
            if rc != 0 or not tr0.exists():
                raise RuntimeError(f"HSPICE failed for {case.key} {flow}; see {stdout_path}")

        native = parse_hspice_tr0(bench_dir / f"{case.key}_native_ibis.tr0")
        spice = parse_hspice_tr0(bench_dir / f"{case.key}_spice_subckt.tr0")
        waveforms = parse_ibis_waveforms(bench_dir / case.ibis_name)
        rise_wf = choose_waveform(waveforms, "Rising")
        fall_wf = choose_waveform(waveforms, "Falling")
        plot_case(case, native, spice, rise_wf, fall_wf, plot_dir)
        all_metric_rows.extend(metrics_for_case(case, native, spice, rise_wf, fall_wf))

    write_csv(OUT_DIR / "run_summary.csv", run_rows)
    write_csv(OUT_DIR / "metrics_summary.csv", all_metric_rows)
    write_readme(all_metric_rows, run_rows)
    print(f"Wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
