from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PYBIS_REPO = ROOT.parent / "spice" / "pybis2spice"
if str(PYBIS_REPO) not in sys.path:
    sys.path.insert(0, str(PYBIS_REPO))

from pybis2spice import pybis2spice as pb  # noqa: E402


CASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = CASE_DIR / "models"
BENCH_DIR = CASE_DIR / "benches"
RAW_DIR = CASE_DIR / "raw"
PLOT_DIR = CASE_DIR / "plots"

IBIS_PATH = ROOT / "PIC18F1xQ20_LV_IBIS_Models" / "PIC18F1xQ20_vqfn20_LV.ibs"
CONVERTED_DIR = (
    ROOT
    / "PIC18F1xQ20_LV_IBIS_Models"
    / "converted_inputdriven_typical"
    / "PIC18F1xQ20_vqfn20_LV"
    / "Output"
)
NGSPICE_BIN = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

COMPONENT_NAME = "PIC18F1xQ20"
TARGET_R_FIX = 50.0
TARGET_V_FIX = 0.0
RISE_START_NS = 50.0
FALL_START_NS = 700.0
STOP_NS = 1300.0

GOOD_MODEL = "ptc_i2c_std"
BAD_MODEL = "ptc_i3c_std"
MODELS = [GOOD_MODEL, BAD_MODEL]


@dataclass
class Waveform:
    time_s: np.ndarray
    v_typ: np.ndarray
    r_fix: float
    v_fix: float


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


def read_subckt_name(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(".SUBCKT "):
            return line.split()[1]
    raise RuntimeError(f"Could not find .SUBCKT line in {path}")


def write_bench(subckt_name: str, sub_path: Path, vcc: float, en_v: float, bench_path: Path):
    pulse_width_ns = FALL_START_NS - RISE_START_NS
    text = "\n".join(
        [
            ".temp 27",
            ".options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12",
            f"Vin in_src 0 PULSE(0 {vcc} {RISE_START_NS}n 5p 5p {pulse_width_ns}n {2*STOP_NS}n)",
            "Rin in_src in_dig 1",
            f"Ven en_sig 0 DC {en_v}",
            f"Vdd vdd 0 DC {vcc}",
            f".include '{sub_path.as_posix()}'",
            f"XDRV pad in_dig en_sig vdd 0 {subckt_name}",
            f"Rload pad 0 {TARGET_R_FIX}",
            ".save V(in_dig) V(pad)",
            f".tran 100p {STOP_NS}n",
            ".end",
            "",
        ]
    )
    bench_path.write_text(text, encoding="utf-8")


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
        "fall_rms_error_v": float(np.sqrt(np.mean(fall_err ** 2))),
        "rise_max_abs_error_v": float(np.max(np.abs(rise_err))),
        "fall_max_abs_error_v": float(np.max(np.abs(fall_err))),
        "rise_cross_delta_ns": float(rise_dt - rise_ibis),
        "fall_cross_delta_ns": float(fall_dt - fall_ibis),
    }


def plot_overlay(model_name: str, time_s: np.ndarray, v_in: np.ndarray, sim_pad: np.ndarray, ref: np.ndarray,
                 rise: Waveform, fall: Waveform, out_path: Path):
    t_ns = time_s * 1e9
    rise_t_ns = rise.time_s * 1e9 + RISE_START_NS
    fall_t_ns = fall.time_s * 1e9 + FALL_START_NS

    fig, axes = plt.subplots(3, 1, figsize=(10, 11), constrained_layout=True)

    axes[0].plot(t_ns, ref, label="IBIS reference", linewidth=2)
    axes[0].plot(t_ns, sim_pad, label="Converted model", linewidth=2)
    axes[0].plot(t_ns, v_in, "--", label="Input", linewidth=1.0, alpha=0.7)
    axes[0].set_title(f"{model_name}: IBIS vs converted model")
    axes[0].set_xlabel("Time (ns)")
    axes[0].set_ylabel("Voltage (V)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(rise_t_ns, rise.v_typ, label="IBIS rise", linewidth=2)
    axes[1].plot(rise_t_ns, np.interp(rise_t_ns * 1e-9, time_s, sim_pad), label="Converted rise", linewidth=2)
    axes[1].set_xlim(RISE_START_NS - 5, RISE_START_NS + rise.time_s[-1] * 1e9 + 10)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_ylabel("Voltage (V)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(fall_t_ns, fall.v_typ, label="IBIS fall", linewidth=2)
    axes[2].plot(fall_t_ns, np.interp(fall_t_ns * 1e-9, time_s, sim_pad), label="Converted fall", linewidth=2)
    axes[2].set_xlim(FALL_START_NS - 5, FALL_START_NS + fall.time_s[-1] * 1e9 + 10)
    axes[2].set_xlabel("Time (ns)")
    axes[2].set_ylabel("Voltage (V)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_k_tables(good_dm, bad_dm, out_path: Path):
    g_r = pb.solve_k_params_output(good_dm, corner=1, waveform_type="Rising")
    g_f = pb.solve_k_params_output(good_dm, corner=1, waveform_type="Falling")
    b_r = pb.solve_k_params_output(bad_dm, corner=1, waveform_type="Rising")
    b_f = pb.solve_k_params_output(bad_dm, corner=1, waveform_type="Falling")

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)

    axes[0, 0].plot(g_r[:, 0] * 1e9, g_r[:, 1], label=f"{GOOD_MODEL} Ku", linewidth=2)
    axes[0, 0].plot(b_r[:, 0] * 1e9, b_r[:, 1], label=f"{BAD_MODEL} Ku", linewidth=2)
    axes[0, 0].set_title("Rising Ku")
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].legend()

    axes[0, 1].plot(g_r[:, 0] * 1e9, g_r[:, 2], label=f"{GOOD_MODEL} Kd", linewidth=2)
    axes[0, 1].plot(b_r[:, 0] * 1e9, b_r[:, 2], label=f"{BAD_MODEL} Kd", linewidth=2)
    axes[0, 1].set_title("Rising Kd")
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()

    axes[1, 0].plot(g_f[:, 0] * 1e9, g_f[:, 1], label=f"{GOOD_MODEL} Ku", linewidth=2)
    axes[1, 0].plot(b_f[:, 0] * 1e9, b_f[:, 1], label=f"{BAD_MODEL} Ku", linewidth=2)
    axes[1, 0].set_title("Falling Ku")
    axes[1, 0].set_xlabel("Elapsed time (ns)")
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()

    axes[1, 1].plot(g_f[:, 0] * 1e9, g_f[:, 2], label=f"{GOOD_MODEL} Kd", linewidth=2)
    axes[1, 1].plot(b_f[:, 0] * 1e9, b_f[:, 2], label=f"{BAD_MODEL} Kd", linewidth=2)
    axes[1, 1].set_title("Falling Kd")
    axes[1, 1].set_xlabel("Elapsed time (ns)")
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend()

    for ax in axes.flat:
        ax.set_ylabel("Coefficient")

    fig.suptitle("Solved Ku/Kd: good vs bad case")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_iv_tables(good_dm, bad_dm, out_path: Path):
    v = np.linspace(0.0, 3.3, 600)

    def curves(dm):
        pu_ref = pb.get_reference(dm.pullup_ref, dm.v_range, 1)
        pd_ref = pb.get_reference(dm.pulldown_ref, 0, 1)
        pc_ref = pb.get_reference(dm.pwr_clamp_ref, dm.v_range, 1)
        gc_ref = pb.get_reference(dm.gnd_clamp_ref, 0, 1)
        return {
            "pu_raw": pb.get_current_data_from_iv_data(v, dm.iv_pullup, pu_ref, 1),
            "pu_adj": pb.get_current_data_from_iv_data(v, dm.iv_pullup, pu_ref, 1, iv_data_adjust=dm.iv_pwr_clamp),
            "pd_raw": pb.get_current_data_from_iv_data(v, dm.iv_pulldown, pd_ref, 1),
            "pd_adj": pb.get_current_data_from_iv_data(v, dm.iv_pulldown, pd_ref, 1, iv_data_adjust=dm.iv_gnd_clamp),
            "pc": pb.get_current_data_from_iv_data(v, dm.iv_pwr_clamp, pc_ref, 1),
            "gc": pb.get_current_data_from_iv_data(v, dm.iv_gnd_clamp, gc_ref, 1),
        }

    g = curves(good_dm)
    b = curves(bad_dm)

    fig, axes = plt.subplots(3, 2, figsize=(12, 11), constrained_layout=True)
    series = [
        ("pu_raw", "Pullup raw"),
        ("pd_raw", "Pulldown raw"),
        ("pc", "Power clamp"),
        ("gc", "Ground clamp"),
        ("pu_adj", "Pullup adjusted (PU-PC)"),
        ("pd_adj", "Pulldown adjusted (PD-GC)"),
    ]

    for ax, (key, title) in zip(axes.flat, series):
        ax.plot(v, g[key] * 1e3, label=GOOD_MODEL, linewidth=2)
        ax.plot(v, b[key] * 1e3, label=BAD_MODEL, linewidth=2)
        ax.set_title(title)
        ax.set_xlabel("Pad voltage (V)")
        ax.set_ylabel("Current (mA)")
        ax.grid(True, alpha=0.3)
        ax.legend()

    fig.suptitle("IV and clamp behavior: good vs bad case")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_summary(results: dict[str, dict], good_dm, bad_dm, out_path: Path):
    lines = [
        "# Good vs Bad PTC Std Comparison",
        "",
        "- Package: `PIC18F1xQ20_vqfn20_LV`",
        f"- Good case: `{GOOD_MODEL}`",
        f"- Bad case: `{BAD_MODEL}`",
        "- Fixture: direct `50 ohm` to ground",
        "- IBIS waveform target: nearest `R_fixture=50`, `V_fixture=0` rising/falling pair",
        "",
        "## Why this pair",
        "",
        f"- `{GOOD_MODEL}` is a strong same-family good case.",
        f"- `{BAD_MODEL}` is the repeated severe outlier.",
        "- Both are PTC `std` models from the same package file, so the comparison stays focused on model behavior.",
        "",
        "## Model facts",
        "",
        f"- `{GOOD_MODEL}`: `C_comp = {good_dm.c_comp[0] * 1e12:.3f} pF`, enable `{good_dm.enable}`",
        f"- `{BAD_MODEL}`: `C_comp = {bad_dm.c_comp[0] * 1e12:.3f} pF`, enable `{bad_dm.enable}`",
        "",
        "## Overlay metrics",
        "",
        "| Model | Rise RMS (V) | Fall RMS (V) | Rise Max Abs (V) | Fall Max Abs (V) | Rise dT (ns) | Fall dT (ns) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in [GOOD_MODEL, BAD_MODEL]:
        m = results[name]
        lines.append(
            f"| `{name}` | {m['rise_rms_error_v']:.6f} | {m['fall_rms_error_v']:.6f} | "
            f"{m['rise_max_abs_error_v']:.6f} | {m['fall_max_abs_error_v']:.6f} | "
            f"{m['rise_cross_delta_ns']:.3f} | {m['fall_cross_delta_ns']:.3f} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    for path in (MODEL_DIR, BENCH_DIR, RAW_DIR, PLOT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    ibis = pb.get_ibis_model_ecdtools(str(IBIS_PATH))
    results = {}
    data_models = {}

    for model_name in MODELS:
        data_model = pb.DataModel(ibis, model_name, COMPONENT_NAME)
        data_models[model_name] = data_model
        src = CONVERTED_DIR / f"{model_name}-Output-Typical.sub"
        dst = MODEL_DIR / src.name
        shutil.copy2(src, dst)
        subckt_name = read_subckt_name(dst)

        vcc = float(data_model.v_range[0])
        en_v = 0.0 if data_model.enable == "Active-Low" else vcc
        rise = choose_waveform(data_model, "rising")
        fall = choose_waveform(data_model, "falling")

        bench_path = BENCH_DIR / f"{model_name}.sp"
        raw_path = RAW_DIR / f"{model_name}.raw"
        write_bench(subckt_name, dst, vcc, en_v, bench_path)

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
        generated_raw.replace(raw_path)
        traces = parse_ngspice_raw(raw_path)
        time_s = traces["time"]
        v_in = traces["v(in_dig)"]
        v_pad = traces["v(pad)"]
        ref = build_stitched_reference(time_s, rise, fall)

        metrics = compute_metrics(time_s, v_pad, rise, fall)
        results[model_name] = metrics

        overlay_name = (
            "good_overlay_ptc_i2c_std.png" if model_name == GOOD_MODEL else "bad_overlay_ptc_i3c_std.png"
        )
        plot_overlay(model_name, time_s, v_in, v_pad, ref, rise, fall, PLOT_DIR / overlay_name)

    plot_k_tables(data_models[GOOD_MODEL], data_models[BAD_MODEL], PLOT_DIR / "kukd_good_vs_bad.png")
    plot_iv_tables(data_models[GOOD_MODEL], data_models[BAD_MODEL], PLOT_DIR / "vi_tables_good_vs_bad.png")
    write_summary(results, data_models[GOOD_MODEL], data_models[BAD_MODEL], CASE_DIR / "README.md")
    print(f"Wrote good/bad comparison artifacts to {CASE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
