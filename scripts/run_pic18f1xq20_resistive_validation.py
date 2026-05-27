from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
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
IBIS_PATH = IBIS_DIR / "PIC18F1xQ20_vqfn20_LV.ibs"
CONVERTED_DIR = IBIS_DIR / "converted_inputdriven_typical" / "PIC18F1xQ20_vqfn20_LV" / "Output"
OUT_DIR = IBIS_DIR / "validation_resistive_typical_vqfn20"
BENCH_DIR = OUT_DIR / "benches"
RAW_DIR = OUT_DIR / "raw"
PLOT_DIR = OUT_DIR / "plots"

NGSPICE_BIN = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"
COMPONENT_NAME = "PIC18F1xQ20"
MODELS = ["io_dig_std", "io_dig_slctrl", "ptc_i3c_std"]

TARGET_R_FIX = 50.0
TARGET_V_FIX = 0.0
RISE_START_NS = 50.0
FALL_START_NS = 700.0
STOP_NS = 1300.0


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


def write_bench(model_name: str, subckt_path: Path, subckt_name: str, vcc: float, bench_path: Path):
    pulse_width_ns = FALL_START_NS - RISE_START_NS
    include_path = subckt_path.as_posix()
    bench_text = "\n".join(
        [
            ".temp 27",
            ".options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12",
            f"Vin in_src 0 PULSE(0 {vcc} {RISE_START_NS}n 5p 5p {pulse_width_ns}n {2*STOP_NS}n)",
            "Rin in_src in_dig 1",
            f"Ven en_sig 0 DC {vcc}",
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


def compute_metrics(sim_time_s: np.ndarray, sim_pad: np.ndarray, rise: Waveform, fall: Waveform):
    rise_abs_t = rise.time_s + RISE_START_NS * 1e-9
    fall_abs_t = fall.time_s + FALL_START_NS * 1e-9
    rise_sim = np.interp(rise_abs_t, sim_time_s, sim_pad)
    fall_sim = np.interp(fall_abs_t, sim_time_s, sim_pad)

    rise_err = rise_sim - rise.v_typ
    fall_err = fall_sim - fall.v_typ

    return {
        "rise_rms_error_v": float(np.sqrt(np.mean(rise_err ** 2))),
        "rise_max_abs_error_v": float(np.max(np.abs(rise_err))),
        "fall_rms_error_v": float(np.sqrt(np.mean(fall_err ** 2))),
        "fall_max_abs_error_v": float(np.max(np.abs(fall_err))),
        "rise_final_sim_v": float(rise_sim[-1]),
        "rise_final_ibis_v": float(rise.v_typ[-1]),
        "fall_final_sim_v": float(fall_sim[-1]),
        "fall_final_ibis_v": float(fall.v_typ[-1]),
    }


def plot_model(model_name: str, sim_time_s: np.ndarray, sim_pad: np.ndarray, sim_in: np.ndarray,
               rise: Waveform, fall: Waveform, ref: np.ndarray, out_path: Path):
    t_ns = sim_time_s * 1e9
    rise_t_ns = rise.time_s * 1e9 + RISE_START_NS
    fall_t_ns = fall.time_s * 1e9 + FALL_START_NS

    fig, axes = plt.subplots(3, 1, figsize=(10, 11), constrained_layout=True)

    axes[0].plot(t_ns, sim_pad, label="pybis pad", linewidth=2)
    axes[0].plot(t_ns, ref, label="IBIS stitched reference", linewidth=2)
    axes[0].plot(t_ns, sim_in, "--", label="input", linewidth=1.2, alpha=0.8)
    axes[0].set_title(f"{model_name}: resistive 50 ohm validation")
    axes[0].set_xlabel("Time (ns)")
    axes[0].set_ylabel("Voltage (V)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(rise_t_ns, rise.v_typ, label="IBIS rise", linewidth=2)
    axes[1].plot(rise_t_ns, np.interp(rise_t_ns * 1e-9, sim_time_s, sim_pad), label="pybis rise", linewidth=2)
    axes[1].plot(t_ns, sim_in, "--", label="input", linewidth=1.0, alpha=0.6)
    axes[1].set_xlim(RISE_START_NS - 5, RISE_START_NS + rise.time_s[-1] * 1e9 + 10)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_ylabel("Voltage (V)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(fall_t_ns, fall.v_typ, label="IBIS fall", linewidth=2)
    axes[2].plot(fall_t_ns, np.interp(fall_t_ns * 1e-9, sim_time_s, sim_pad), label="pybis fall", linewidth=2)
    axes[2].plot(t_ns, sim_in, "--", label="input", linewidth=1.0, alpha=0.6)
    axes[2].set_xlim(FALL_START_NS - 5, FALL_START_NS + fall.time_s[-1] * 1e9 + 10)
    axes[2].set_xlabel("Time (ns)")
    axes[2].set_ylabel("Voltage (V)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    for path in (OUT_DIR, BENCH_DIR, RAW_DIR, PLOT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    ibis = pybis2spice.get_ibis_model_ecdtools(str(IBIS_PATH))
    rows = []

    for model_name in MODELS:
        data_model = pybis2spice.DataModel(ibis, model_name, COMPONENT_NAME)
        rise = choose_waveform(data_model, "rising")
        fall = choose_waveform(data_model, "falling")
        vcc = float(data_model.v_range[0])

        subckt_path = CONVERTED_DIR / f"{model_name}-Output-Typical.sub"
        subckt_name = read_subckt_name(subckt_path)
        bench_path = BENCH_DIR / f"{model_name}_resistive_50ohm.sp"
        raw_path = RAW_DIR / f"{model_name}_resistive_50ohm.raw"

        write_bench(model_name, subckt_path, subckt_name, vcc, bench_path)

        proc = subprocess.run(
            [str(NGSPICE_BIN), "-b", "-r", str(raw_path.name), str(bench_path.name)],
            cwd=BENCH_DIR,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"ngspice failed for {model_name}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

        raw_generated = BENCH_DIR / raw_path.name
        raw_generated.replace(raw_path)
        traces = parse_ngspice_raw(raw_path)
        sim_time_s = traces["time"]
        sim_pad = traces["v(pad)"]
        sim_in = traces["v(in_dig)"]

        ref = build_stitched_reference(sim_time_s, rise, fall)
        metrics = compute_metrics(sim_time_s, sim_pad, rise, fall)
        plot_path = PLOT_DIR / f"{model_name}_ibis_vs_pybis_resistive_50ohm.png"
        plot_model(model_name, sim_time_s, sim_pad, sim_in, rise, fall, ref, plot_path)

        rows.append(
            {
                "model": model_name,
                "ibis_file": IBIS_PATH.name,
                "rise_r_fix_ohm": rise.r_fix,
                "rise_v_fix_v": rise.v_fix,
                "fall_r_fix_ohm": fall.r_fix,
                "fall_v_fix_v": fall.v_fix,
                **metrics,
                "plot_file": plot_path.name,
                "raw_file": raw_path.name,
                "bench_file": bench_path.name,
            }
        )

    csv_path = OUT_DIR / "validation_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md_lines = [
        "# PIC18F1xQ20 Resistive Validation",
        "",
        f"- Source IBIS: `{IBIS_PATH}`",
        "- Package variant: `vqfn20`",
        "- Converted mode: `InputDriven`",
        "- Corner: `Typical`",
        "- Bench: direct `50 ohm` termination to ground to match `R_fixture=50`, `V_fixture=0`",
        f"- Input pulse: rise at `{RISE_START_NS} ns`, fall at `{FALL_START_NS} ns`",
        "",
        "| Model | Rise RMS Err (V) | Rise Max Abs Err (V) | Fall RMS Err (V) | Fall Max Abs Err (V) | Plot |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in rows:
        md_lines.append(
            f"| `{row['model']}` | {row['rise_rms_error_v']:.6f} | {row['rise_max_abs_error_v']:.6f} | "
            f"{row['fall_rms_error_v']:.6f} | {row['fall_max_abs_error_v']:.6f} | "
            f"`{row['plot_file']}` |"
        )

    (OUT_DIR / "validation_summary.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote validation artifacts to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
