from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import math
import shutil
import struct
import subprocess
import sys

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PYBIS_REPO = ROOT.parent / "spice" / "pybis2spice"
if str(PYBIS_REPO) not in sys.path:
    sys.path.insert(0, str(PYBIS_REPO))

from pybis2spice import pybis2spice  # noqa: E402


IBIS_DIR = ROOT / "PIC18F1xQ20_LV_IBIS_Models"
CONVERTED_ROOT = IBIS_DIR / "converted_inputdriven_typical"
OUT_DIR = IBIS_DIR / "validation_resistive_all_typical"
BENCH_DIR = OUT_DIR / "benches"
TRACE_DIR = OUT_DIR / "trace_npz"
PLOT_DIR = OUT_DIR / "outlier_plots"
NGSPICE_BIN = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

COMPONENT_NAME = "PIC18F1xQ20"
TARGET_R_FIX = 50.0
TARGET_V_FIX = 0.0
RISE_START_NS = 50.0
FALL_START_NS = 700.0
STOP_NS = 1300.0
MAX_FULL_POINTS = 5000
TOP_OUTLIERS_TO_PLOT = 16


@dataclass
class Waveform:
    time_s: np.ndarray
    v_typ: np.ndarray
    r_fix: float
    v_fix: float


def parse_ngspice_raw(path: Path):
    data = path.read_bytes()
    marker = b"Binary:\n"
    idx = data.find(marker)
    if idx < 0:
        raise RuntimeError(f"Binary marker not found in {path}")

    header = data[:idx].decode("latin1")
    lines = header.splitlines()
    nvars = None
    npts = None
    variables = []
    reading_vars = False

    for line in lines:
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":", 1)[1])
        elif line.strip() == "Variables:":
            reading_vars = True
        elif reading_vars and line.startswith("\t"):
            variables.append(line.split()[1])

    if nvars is None or npts is None or len(variables) != nvars:
        raise RuntimeError(f"Could not parse ngspice raw header for {path}")

    payload = data[idx + len(marker):]
    if npts == 0:
        npts = len(payload) // (8 * nvars)
    values = struct.unpack("<" + "d" * (nvars * npts), payload[: 8 * nvars * npts])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))
    return {name: arr[:, i] for i, name in enumerate(variables)}


def choose_waveform(data_model, kind: str) -> Waveform:
    candidates = data_model.vt_rising if kind == "rising" else data_model.vt_falling
    best = None
    best_score = None

    for wf in candidates:
        score = abs(float(wf.r_fix) - TARGET_R_FIX) + abs(float(wf.v_fix[0]) - TARGET_V_FIX)
        if best is None or score < best_score:
            best = wf
            best_score = score

    if best is None:
        raise RuntimeError(f"No {kind} waveform found for {data_model.model_name}")

    return Waveform(
        time_s=np.asarray(best.data[:, 0], dtype=float),
        v_typ=np.asarray(best.data[:, 1], dtype=float),
        r_fix=float(best.r_fix),
        v_fix=float(best.v_fix[0]),
    )


def read_subckt_name(path: Path) -> str:
    for line in path.read_text().splitlines():
        if line.startswith(".SUBCKT "):
            return line.split()[1]
    raise RuntimeError(f"Could not find .SUBCKT line in {path}")


def enable_voltage(enable_mode, vcc: float) -> float:
    if enable_mode == "Active-Low":
        return 0.0
    return vcc


def write_bench(model_name: str, subckt_path: Path, subckt_name: str, vcc: float, en_v: float, bench_path: Path):
    pulse_width_ns = FALL_START_NS - RISE_START_NS
    include_path = subckt_path.as_posix()
    bench_text = "\n".join(
        [
            ".temp 27",
            ".options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12",
            f"Vin in_src 0 PULSE(0 {vcc} {RISE_START_NS}n 5p 5p {pulse_width_ns}n {2*STOP_NS}n)",
            "Rin in_src in_dig 1",
            f"Ven en_sig 0 DC {en_v}",
            f"Vdd vdd 0 DC {vcc}",
            f".include '{include_path}'",
            f"XDRV pad in_dig en_sig vdd 0 {subckt_name}",
            f"Rload pad 0 {TARGET_R_FIX}",
            ".save V(in_dig) V(pad)",
            f".tran 100p {STOP_NS}n",
            ".end",
            "",
        ]
    )
    bench_path.write_text(bench_text, encoding="utf-8")


def build_stitched_reference(sim_time_s: np.ndarray, rise: Waveform, fall: Waveform):
    ref = np.full_like(sim_time_s, rise.v_typ[0])
    rise_t = rise.time_s + RISE_START_NS * 1e-9
    fall_t = fall.time_s + FALL_START_NS * 1e-9

    rise_mask = (sim_time_s >= rise_t[0]) & (sim_time_s <= rise_t[-1])
    ref[rise_mask] = np.interp(sim_time_s[rise_mask], rise_t, rise.v_typ)

    hold_mask = (sim_time_s > rise_t[-1]) & (sim_time_s < fall_t[0])
    ref[hold_mask] = rise.v_typ[-1]

    fall_mask = (sim_time_s >= fall_t[0]) & (sim_time_s <= fall_t[-1])
    ref[fall_mask] = np.interp(sim_time_s[fall_mask], fall_t, fall.v_typ)

    after_mask = sim_time_s > fall_t[-1]
    ref[after_mask] = fall.v_typ[-1]
    return ref


def decimate_trace(time_s: np.ndarray, *series: np.ndarray):
    n = len(time_s)
    if n <= MAX_FULL_POINTS:
        idx = np.arange(n)
    else:
        idx = np.linspace(0, n - 1, MAX_FULL_POINTS).astype(int)
        idx = np.unique(idx)
    return (time_s[idx],) + tuple(values[idx] for values in series)


def crossing_time(time_s: np.ndarray, voltage: np.ndarray, threshold: float, rising: bool):
    for i in range(1, len(time_s)):
        if rising and voltage[i - 1] < threshold <= voltage[i]:
            return float(np.interp(threshold, [voltage[i - 1], voltage[i]], [time_s[i - 1], time_s[i]]))
        if (not rising) and voltage[i - 1] > threshold >= voltage[i]:
            return float(np.interp(threshold, [voltage[i - 1], voltage[i]], [time_s[i - 1], time_s[i]]))
    return math.nan


def compute_metrics(sim_time_s: np.ndarray, sim_pad: np.ndarray, rise: Waveform, fall: Waveform):
    rise_abs_t = rise.time_s + RISE_START_NS * 1e-9
    fall_abs_t = fall.time_s + FALL_START_NS * 1e-9
    rise_sim = np.interp(rise_abs_t, sim_time_s, sim_pad)
    fall_sim = np.interp(fall_abs_t, sim_time_s, sim_pad)

    rise_err = rise_sim - rise.v_typ
    fall_err = fall_sim - fall.v_typ

    rise_threshold = 0.5 * (float(rise.v_typ[0]) + float(rise.v_typ[-1]))
    fall_threshold = 0.5 * (float(fall.v_typ[0]) + float(fall.v_typ[-1]))
    rise_cross_ibis_ns = crossing_time(rise.time_s, rise.v_typ, rise_threshold, True) * 1e9
    rise_cross_sim_ns = crossing_time(sim_time_s, sim_pad, rise_threshold, True) * 1e9 - RISE_START_NS
    fall_cross_ibis_ns = crossing_time(fall.time_s, fall.v_typ, fall_threshold, False) * 1e9
    fall_cross_sim_ns = crossing_time(sim_time_s, sim_pad, fall_threshold, False) * 1e9 - FALL_START_NS

    return {
        "rise_rms_error_v": float(np.sqrt(np.mean(rise_err ** 2))),
        "rise_max_abs_error_v": float(np.max(np.abs(rise_err))),
        "fall_rms_error_v": float(np.sqrt(np.mean(fall_err ** 2))),
        "fall_max_abs_error_v": float(np.max(np.abs(fall_err))),
        "rise_cross_ibis_ns": float(rise_cross_ibis_ns),
        "rise_cross_sim_ns": float(rise_cross_sim_ns),
        "rise_cross_delta_ns": float(rise_cross_sim_ns - rise_cross_ibis_ns),
        "fall_cross_ibis_ns": float(fall_cross_ibis_ns),
        "fall_cross_sim_ns": float(fall_cross_sim_ns),
        "fall_cross_delta_ns": float(fall_cross_sim_ns - fall_cross_ibis_ns),
        "rise_final_sim_v": float(rise_sim[-1]),
        "rise_final_ibis_v": float(rise.v_typ[-1]),
        "fall_final_sim_v": float(fall_sim[-1]),
        "fall_final_ibis_v": float(fall.v_typ[-1]),
    }


def store_compact_trace(path: Path, model_name: str, package_name: str, sim_time_s: np.ndarray, sim_pad: np.ndarray,
                        sim_in: np.ndarray, ref: np.ndarray, rise: Waveform, fall: Waveform):
    full_t, full_pad, full_in, full_ref = decimate_trace(sim_time_s, sim_pad, sim_in, ref)
    rise_abs_t = rise.time_s + RISE_START_NS * 1e-9
    fall_abs_t = fall.time_s + FALL_START_NS * 1e-9
    np.savez_compressed(
        path,
        model_name=model_name,
        package_name=package_name,
        full_t_ns=full_t * 1e9,
        full_pad_v=full_pad,
        full_in_v=full_in,
        full_ref_v=full_ref,
        rise_t_ns=rise_abs_t * 1e9,
        rise_ibis_v=rise.v_typ,
        rise_sim_v=np.interp(rise_abs_t, sim_time_s, sim_pad),
        fall_t_ns=fall_abs_t * 1e9,
        fall_ibis_v=fall.v_typ,
        fall_sim_v=np.interp(fall_abs_t, sim_time_s, sim_pad),
    )


def plot_from_trace(npz_path: Path, out_path: Path):
    data = np.load(npz_path)
    fig, axes = plt.subplots(3, 1, figsize=(10, 11), constrained_layout=True)

    axes[0].plot(data["full_t_ns"], data["full_pad_v"], label="pybis pad", linewidth=2)
    axes[0].plot(data["full_t_ns"], data["full_ref_v"], label="IBIS stitched reference", linewidth=2)
    axes[0].plot(data["full_t_ns"], data["full_in_v"], "--", label="input", linewidth=1.1, alpha=0.8)
    axes[0].set_title(f"{str(data['package_name'])} / {str(data['model_name'])}")
    axes[0].set_xlabel("Time (ns)")
    axes[0].set_ylabel("Voltage (V)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(data["rise_t_ns"], data["rise_ibis_v"], label="IBIS rise", linewidth=2)
    axes[1].plot(data["rise_t_ns"], data["rise_sim_v"], label="pybis rise", linewidth=2)
    axes[1].set_xlim(float(data["rise_t_ns"][0]) - 5, float(data["rise_t_ns"][-1]) + 10)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_ylabel("Voltage (V)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(data["fall_t_ns"], data["fall_ibis_v"], label="IBIS fall", linewidth=2)
    axes[2].plot(data["fall_t_ns"], data["fall_sim_v"], label="pybis fall", linewidth=2)
    axes[2].set_xlim(float(data["fall_t_ns"][0]) - 5, float(data["fall_t_ns"][-1]) + 10)
    axes[2].set_xlabel("Time (ns)")
    axes[2].set_ylabel("Voltage (V)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def create_aggregate_plots(rows: list[dict]):
    ranked = sorted(rows, key=lambda row: row["combined_score"], reverse=True)
    top = ranked[: min(20, len(ranked))]

    labels = [f"{row['package_name']}/{row['model_name']}" for row in top]
    scores = [row["combined_score"] for row in top]
    fig, ax = plt.subplots(figsize=(12, max(5, len(top) * 0.35)), constrained_layout=True)
    ax.barh(labels[::-1], scores[::-1])
    ax.set_xlabel("Combined score = max(rise/fall RMS/max abs error)")
    ax.set_title("Worst PIC18F1xQ20 waveform matches")
    fig.savefig(OUT_DIR / "top_outliers_bar.png", dpi=150)
    plt.close(fig)

    rise_rms = np.asarray([row["rise_rms_error_v"] for row in rows], dtype=float)
    fall_rms = np.asarray([row["fall_rms_error_v"] for row in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    ax.scatter(rise_rms, fall_rms, alpha=0.8)
    ax.set_xlabel("Rise RMS error (V)")
    ax.set_ylabel("Fall RMS error (V)")
    ax.set_title("All models: rise vs fall RMS error")
    ax.grid(True, alpha=0.3)
    fig.savefig(OUT_DIR / "rise_vs_fall_rms_scatter.png", dpi=150)
    plt.close(fig)


def collect_jobs():
    jobs = []
    for package_dir in sorted(CONVERTED_ROOT.iterdir()):
        if not package_dir.is_dir():
            continue
        ibis_path = IBIS_DIR / f"{package_dir.name}.ibs"
        out_dir = package_dir / "Output"
        if not ibis_path.exists() or not out_dir.exists():
            continue

        ibis = pybis2spice.get_ibis_model_ecdtools(str(ibis_path))
        for sub_path in sorted(out_dir.glob("*-Output-Typical.sub")):
            model_name = sub_path.name.replace("-Output-Typical.sub", "")
            data_model = pybis2spice.DataModel(ibis, model_name, COMPONENT_NAME)
            if data_model.vt_rising is None or data_model.vt_falling is None:
                continue
            jobs.append((package_dir.name, ibis_path, sub_path, data_model))
    return jobs


def main() -> int:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for path in (OUT_DIR, BENCH_DIR, TRACE_DIR, PLOT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    jobs = collect_jobs()
    rows = []
    total = len(jobs)

    for idx, (package_name, ibis_path, subckt_path, data_model) in enumerate(jobs, start=1):
        rise = choose_waveform(data_model, "rising")
        fall = choose_waveform(data_model, "falling")
        vcc = float(data_model.v_range[0])
        en_v = enable_voltage(data_model.enable, vcc)
        subckt_name = read_subckt_name(subckt_path)

        case_slug = f"{package_name}__{data_model.model_name}"
        bench_path = BENCH_DIR / f"{case_slug}.sp"
        raw_path = BENCH_DIR / f"{case_slug}.raw"
        trace_path = TRACE_DIR / f"{case_slug}.npz"
        write_bench(data_model.model_name, subckt_path, subckt_name, vcc, en_v, bench_path)

        proc = subprocess.run(
            [str(NGSPICE_BIN), "-b", "-r", raw_path.name, bench_path.name],
            cwd=BENCH_DIR,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            rows.append(
                {
                    "package_name": package_name,
                    "model_name": data_model.model_name,
                    "status": "failed",
                    "error": proc.stderr.strip() or proc.stdout.strip(),
                }
            )
            print(f"[{idx}/{total}] FAIL {package_name}/{data_model.model_name}")
            continue

        traces = parse_ngspice_raw(raw_path)
        raw_path.unlink(missing_ok=True)
        sim_time_s = traces["time"]
        sim_pad = traces["v(pad)"]
        sim_in = traces["v(in_dig)"]

        ref = build_stitched_reference(sim_time_s, rise, fall)
        metrics = compute_metrics(sim_time_s, sim_pad, rise, fall)
        store_compact_trace(trace_path, data_model.model_name, package_name, sim_time_s, sim_pad, sim_in, ref, rise, fall)

        combined_score = max(
            metrics["rise_rms_error_v"],
            metrics["rise_max_abs_error_v"],
            metrics["fall_rms_error_v"],
            metrics["fall_max_abs_error_v"],
        )
        row = {
            "package_name": package_name,
            "model_name": data_model.model_name,
            "ibis_file": ibis_path.name,
            "status": "ok",
            "enable_mode": data_model.enable or "None",
            "rise_r_fix_ohm": rise.r_fix,
            "rise_v_fix_v": rise.v_fix,
            "fall_r_fix_ohm": fall.r_fix,
            "fall_v_fix_v": fall.v_fix,
            "trace_file": trace_path.name,
            "bench_file": bench_path.name,
            "combined_score": combined_score,
            **metrics,
        }
        rows.append(row)
        print(
            f"[{idx}/{total}] OK {package_name}/{data_model.model_name} "
            f"rise_rms={metrics['rise_rms_error_v']:.4f} fall_rms={metrics['fall_rms_error_v']:.4f}"
        )

    ok_rows = [row for row in rows if row["status"] == "ok"]
    ok_rows.sort(key=lambda row: row["combined_score"], reverse=True)
    for rank, row in enumerate(ok_rows, start=1):
        row["outlier_rank"] = rank

    for row in ok_rows[:TOP_OUTLIERS_TO_PLOT]:
        trace_path = TRACE_DIR / row["trace_file"]
        plot_path = PLOT_DIR / f"{row['outlier_rank']:02d}_{row['package_name']}__{row['model_name']}.png"
        plot_from_trace(trace_path, plot_path)
        row["outlier_plot"] = plot_path.name

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with (OUT_DIR / "validation_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    create_aggregate_plots(ok_rows)

    md_lines = [
        "# PIC18F1xQ20 Resistive Validation (All Output Models)",
        "",
        "- Converted mode: `InputDriven`",
        "- Corner: `Typical`",
        "- Bench: direct `50 ohm` termination to ground",
        "- IBIS comparison target: waveform block nearest `R_fixture=50`, `V_fixture=0`",
        "",
        f"- Cases attempted: `{len(rows)}`",
        f"- Cases successful: `{len(ok_rows)}`",
        f"- Cases failed: `{len(rows) - len(ok_rows)}`",
        "",
        "## Worst 20 by combined score",
        "",
        "| Rank | Package | Model | Rise RMS (V) | Fall RMS (V) | Rise Max Abs (V) | Fall Max Abs (V) | Rise dT (ns) | Fall dT (ns) |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in ok_rows[:20]:
        md_lines.append(
            f"| {row['outlier_rank']} | `{row['package_name']}` | `{row['model_name']}` | "
            f"{row['rise_rms_error_v']:.6f} | {row['fall_rms_error_v']:.6f} | "
            f"{row['rise_max_abs_error_v']:.6f} | {row['fall_max_abs_error_v']:.6f} | "
            f"{row['rise_cross_delta_ns']:.3f} | {row['fall_cross_delta_ns']:.3f} |"
        )

    md_lines.extend([
        "",
        "## Best 20 by combined score",
        "",
        "| Rank | Package | Model | Rise RMS (V) | Fall RMS (V) |",
        "| ---: | --- | --- | ---: | ---: |",
    ])
    for row in list(reversed(ok_rows[-20:])):
        md_lines.append(
            f"| {row['outlier_rank']} | `{row['package_name']}` | `{row['model_name']}` | "
            f"{row['rise_rms_error_v']:.6f} | {row['fall_rms_error_v']:.6f} |"
        )

    if len(rows) != len(ok_rows):
        md_lines.extend(["", "## Failures", ""])
        for row in rows:
            if row["status"] == "failed":
                md_lines.append(f"- `{row['package_name']}/{row['model_name']}`: {row['error']}")

    (OUT_DIR / "validation_summary.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote full validation results to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
