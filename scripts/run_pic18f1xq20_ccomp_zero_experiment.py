from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
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
IBIS_PATH = IBIS_DIR / "PIC18F1xQ20_vqfn20_LV.ibs"
CONVERTED_DIR = IBIS_DIR / "converted_inputdriven_typical" / "PIC18F1xQ20_vqfn20_LV" / "Output"
OUT_DIR = IBIS_DIR / "ccomp_zero_experiment_vqfn20"
MODEL_DIR = OUT_DIR / "models"
BENCH_DIR = OUT_DIR / "benches"
RAW_DIR = OUT_DIR / "raw"
PLOT_DIR = OUT_DIR / "plots"
NGSPICE_BIN = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

COMPONENT_NAME = "PIC18F1xQ20"
TARGET_R_FIX = 50.0
TARGET_V_FIX = 0.0
RISE_START_NS = 50.0
FALL_START_NS = 700.0
STOP_NS = 1300.0

MODELS = [
    "ptc_i3c_std",
    "io_vrefh10_slctrl",
    "io_vrefh10_std",
    "io_vrefh5_std",
    "io_zxover_std",
    "io_dig_slctrl",
]


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


def make_ccomp_zero_model(src: Path, dst: Path) -> tuple[str, str]:
    text = src.read_text(encoding="utf-8")
    base_name = read_subckt_name(src)
    zero_name = f"{base_name}_CComp0"
    text = text.replace(f".SUBCKT {base_name} ", f".SUBCKT {zero_name} ", 1)
    text = text.replace(f".SUBCKT {base_name}\n", f".SUBCKT {zero_name}\n", 1)
    text = text.replace(".param C_comp = ", ".param C_comp_original = ", 1)
    text = text.replace(".param C_comp_original = ", ".param C_comp_original = ", 1)
    text = text.replace(".param C_comp_original = ", ".param C_comp_original = ", 1)
    lines = text.splitlines()
    out_lines = []
    inserted = False
    for line in lines:
        out_lines.append(line)
        if line.startswith(".param C_comp_original ="):
            out_lines.append(".param C_comp = 0")
            inserted = True
    if not inserted:
        raise RuntimeError(f"Could not find C_comp parameter in {src}")
    dst.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return base_name, zero_name


def enable_voltage(enable_mode, vcc: float) -> float:
    if enable_mode == "Active-Low":
        return 0.0
    return vcc


def write_bench(model_name: str, base_model_path: Path, zero_model_path: Path,
                base_name: str, zero_name: str, vcc: float, en_v: float, bench_path: Path):
    pulse_width_ns = FALL_START_NS - RISE_START_NS
    bench_text = "\n".join(
        [
            ".temp 27",
            ".options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12",
            f"Vin in_src 0 PULSE(0 {vcc} {RISE_START_NS}n 5p 5p {pulse_width_ns}n {2*STOP_NS}n)",
            "Rin in_src in_dig 1",
            f"Ven en_sig 0 DC {en_v}",
            f"Vdd vdd 0 DC {vcc}",
            f".include '{base_model_path.as_posix()}'",
            f".include '{zero_model_path.as_posix()}'",
            f"XBASE pad_base in_dig en_sig vdd 0 {base_name}",
            f"XZERO pad_zero in_dig en_sig vdd 0 {zero_name}",
            f"Rload_base pad_base 0 {TARGET_R_FIX}",
            f"Rload_zero pad_zero 0 {TARGET_R_FIX}",
            ".save V(in_dig) V(pad_base) V(pad_zero)",
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


def crossing_time(time_s: np.ndarray, voltage: np.ndarray, threshold: float, rising: bool):
    for i in range(1, len(time_s)):
        if rising and voltage[i - 1] < threshold <= voltage[i]:
            return float(np.interp(threshold, [voltage[i - 1], voltage[i]], [time_s[i - 1], time_s[i]]))
        if (not rising) and voltage[i - 1] > threshold >= voltage[i]:
            return float(np.interp(threshold, [voltage[i - 1], voltage[i]], [time_s[i - 1], time_s[i]]))
    return float("nan")


def compute_metrics(sim_time_s: np.ndarray, sim_pad: np.ndarray, rise: Waveform, fall: Waveform):
    rise_abs_t = rise.time_s + RISE_START_NS * 1e-9
    fall_abs_t = fall.time_s + FALL_START_NS * 1e-9
    rise_sim = np.interp(rise_abs_t, sim_time_s, sim_pad)
    fall_sim = np.interp(fall_abs_t, sim_time_s, sim_pad)

    rise_err = rise_sim - rise.v_typ
    fall_err = fall_sim - fall.v_typ
    rise_threshold = 0.5 * (float(rise.v_typ[0]) + float(rise.v_typ[-1]))
    fall_threshold = 0.5 * (float(fall.v_typ[0]) + float(fall.v_typ[-1]))
    rise_dt = crossing_time(sim_time_s, sim_pad, rise_threshold, True) * 1e9 - RISE_START_NS
    rise_ibis = crossing_time(rise.time_s, rise.v_typ, rise_threshold, True) * 1e9
    fall_dt = crossing_time(sim_time_s, sim_pad, fall_threshold, False) * 1e9 - FALL_START_NS
    fall_ibis = crossing_time(fall.time_s, fall.v_typ, fall_threshold, False) * 1e9
    return {
        "rise_rms_error_v": float(np.sqrt(np.mean(rise_err ** 2))),
        "rise_max_abs_error_v": float(np.max(np.abs(rise_err))),
        "fall_rms_error_v": float(np.sqrt(np.mean(fall_err ** 2))),
        "fall_max_abs_error_v": float(np.max(np.abs(fall_err))),
        "rise_cross_delta_ns": float(rise_dt - rise_ibis),
        "fall_cross_delta_ns": float(fall_dt - fall_ibis),
    }


def plot_case(model_name: str, time_s: np.ndarray, v_in: np.ndarray, v_base: np.ndarray, v_zero: np.ndarray,
              ref: np.ndarray, rise: Waveform, fall: Waveform, out_path: Path):
    t_ns = time_s * 1e9
    rise_t_ns = rise.time_s * 1e9 + RISE_START_NS
    fall_t_ns = fall.time_s * 1e9 + FALL_START_NS
    fig, axes = plt.subplots(3, 1, figsize=(10, 11), constrained_layout=True)

    axes[0].plot(t_ns, ref, label="IBIS reference", linewidth=2)
    axes[0].plot(t_ns, v_base, label="pybis original", linewidth=2)
    axes[0].plot(t_ns, v_zero, label="pybis C_comp=0", linewidth=2)
    axes[0].plot(t_ns, v_in, "--", label="input", linewidth=1.0, alpha=0.7)
    axes[0].set_title(f"{model_name}: effect of zeroing runtime C_comp")
    axes[0].set_xlabel("Time (ns)")
    axes[0].set_ylabel("Voltage (V)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(rise_t_ns, rise.v_typ, label="IBIS rise", linewidth=2)
    axes[1].plot(rise_t_ns, np.interp(rise_t_ns * 1e-9, time_s, v_base), label="original rise", linewidth=2)
    axes[1].plot(rise_t_ns, np.interp(rise_t_ns * 1e-9, time_s, v_zero), label="C_comp=0 rise", linewidth=2)
    axes[1].set_xlim(RISE_START_NS - 5, RISE_START_NS + rise.time_s[-1] * 1e9 + 10)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_ylabel("Voltage (V)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(fall_t_ns, fall.v_typ, label="IBIS fall", linewidth=2)
    axes[2].plot(fall_t_ns, np.interp(fall_t_ns * 1e-9, time_s, v_base), label="original fall", linewidth=2)
    axes[2].plot(fall_t_ns, np.interp(fall_t_ns * 1e-9, time_s, v_zero), label="C_comp=0 fall", linewidth=2)
    axes[2].set_xlim(FALL_START_NS - 5, FALL_START_NS + fall.time_s[-1] * 1e9 + 10)
    axes[2].set_xlabel("Time (ns)")
    axes[2].set_ylabel("Voltage (V)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for path in (OUT_DIR, MODEL_DIR, BENCH_DIR, RAW_DIR, PLOT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    ibis = pybis2spice.get_ibis_model_ecdtools(str(IBIS_PATH))
    rows = []

    for model_name in MODELS:
        data_model = pybis2spice.DataModel(ibis, model_name, COMPONENT_NAME)
        vcc = float(data_model.v_range[0])
        en_v = enable_voltage(data_model.enable, vcc)
        rise = choose_waveform(data_model, "rising")
        fall = choose_waveform(data_model, "falling")

        src_model = CONVERTED_DIR / f"{model_name}-Output-Typical.sub"
        base_copy = MODEL_DIR / f"{model_name}-Output-Typical.sub"
        zero_copy = MODEL_DIR / f"{model_name}-Output-Typical-CComp0.sub"
        shutil.copy2(src_model, base_copy)
        base_name = read_subckt_name(base_copy)
        _, zero_name = make_ccomp_zero_model(src_model, zero_copy)

        bench_path = BENCH_DIR / f"{model_name}_compare_ccomp0.sp"
        raw_path = BENCH_DIR / f"{model_name}_compare_ccomp0.raw"
        write_bench(model_name, base_copy, zero_copy, base_name, zero_name, vcc, en_v, bench_path)

        proc = subprocess.run(
            [str(NGSPICE_BIN), "-b", "-r", raw_path.name, bench_path.name],
            cwd=BENCH_DIR,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"ngspice failed for {model_name}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

        generated_raw = BENCH_DIR / raw_path.name
        generated_raw.replace(RAW_DIR / raw_path.name)
        raw_path = RAW_DIR / raw_path.name
        traces = parse_ngspice_raw(raw_path)
        time_s = traces["time"]
        v_in = traces["v(in_dig)"]
        v_base = traces["v(pad_base)"]
        v_zero = traces["v(pad_zero)"]
        ref = build_stitched_reference(time_s, rise, fall)

        base_metrics = compute_metrics(time_s, v_base, rise, fall)
        zero_metrics = compute_metrics(time_s, v_zero, rise, fall)
        base_score = max(base_metrics["rise_rms_error_v"], base_metrics["fall_rms_error_v"],
                         base_metrics["rise_max_abs_error_v"], base_metrics["fall_max_abs_error_v"])
        zero_score = max(zero_metrics["rise_rms_error_v"], zero_metrics["fall_rms_error_v"],
                         zero_metrics["rise_max_abs_error_v"], zero_metrics["fall_max_abs_error_v"])

        plot_path = PLOT_DIR / f"{model_name}_ccomp0_compare.png"
        plot_case(model_name, time_s, v_in, v_base, v_zero, ref, rise, fall, plot_path)

        rows.append(
            {
                "model_name": model_name,
                "c_comp_pf": float(data_model.c_comp[0] * 1e12),
                "original_rise_rms_v": base_metrics["rise_rms_error_v"],
                "original_fall_rms_v": base_metrics["fall_rms_error_v"],
                "original_rise_max_abs_v": base_metrics["rise_max_abs_error_v"],
                "original_fall_max_abs_v": base_metrics["fall_max_abs_error_v"],
                "original_rise_dt_ns": base_metrics["rise_cross_delta_ns"],
                "original_fall_dt_ns": base_metrics["fall_cross_delta_ns"],
                "original_score": base_score,
                "ccomp0_rise_rms_v": zero_metrics["rise_rms_error_v"],
                "ccomp0_fall_rms_v": zero_metrics["fall_rms_error_v"],
                "ccomp0_rise_max_abs_v": zero_metrics["rise_max_abs_error_v"],
                "ccomp0_fall_max_abs_v": zero_metrics["fall_max_abs_error_v"],
                "ccomp0_rise_dt_ns": zero_metrics["rise_cross_delta_ns"],
                "ccomp0_fall_dt_ns": zero_metrics["fall_cross_delta_ns"],
                "ccomp0_score": zero_score,
                "score_delta_original_minus_ccomp0": base_score - zero_score,
                "plot_file": plot_path.name,
            }
        )

    csv_path = OUT_DIR / "summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# C_comp Zero Experiment",
        "",
        "- Package variant: `vqfn20`",
        "- Source IBIS: `PIC18F1xQ20_vqfn20_LV.ibs`",
        "- Comparison target: corresponding `R_fixture=50`, `V_fixture=0` IBIS waveforms",
        "- Note: this only zeros `C_comp` in the runtime SPICE model.",
        "- The precomputed `Ku/Kd` tables are still the ones extracted with the original `C_comp` present.",
        "",
        "| Model | C_comp (pF) | Original Score | C_comp=0 Score | Improvement (`orig - zero`) | Plot |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in sorted(rows, key=lambda item: item["score_delta_original_minus_ccomp0"], reverse=True):
        lines.append(
            f"| `{row['model_name']}` | {row['c_comp_pf']:.3f} | {row['original_score']:.6f} | "
            f"{row['ccomp0_score']:.6f} | {row['score_delta_original_minus_ccomp0']:.6f} | "
            f"`{row['plot_file']}` |"
        )
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote C_comp experiment artifacts to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
