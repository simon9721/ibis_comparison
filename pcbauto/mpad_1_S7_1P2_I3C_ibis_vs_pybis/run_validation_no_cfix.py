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


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
PYBIS_REPO = PROJECT_ROOT / "tools" / "pybis2spice"
if str(PYBIS_REPO) not in sys.path:
    sys.path.insert(0, str(PYBIS_REPO))

from pybis2spice import pybis2spice, subcircuit  # noqa: E402


SOURCE_IBIS = PROJECT_ROOT / "pcbauto" / "Arbel_I3C_IBIS.ibs"
LOCAL_IBIS = ROOT / "Arbel_I3C_IBIS.ibs"
MODEL_NAME = "mpad_1_S7_1P2_I3C"
COMPONENT_NAME = "Arbel"
CORNER = "Typical"

CONVERTED_SUB = ROOT / f"{MODEL_NAME}-OutputInput-{CORNER}-no_cfix.sub"
CSV_PATH = ROOT / "validation_summary_no_cfix.csv"
MD_PATH = ROOT / "validation_summary_no_cfix.md"
PLOT_DIR = ROOT / "plots_no_cfix"

NGSPICE_BIN = PROJECT_ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

TARGET_R_FIX = 1000.0
TARGET_C_FIX = 20e-12
RISE_START_NS = 5.0
FALL_START_NS = 35.0
STOP_NS = 70.0


@dataclass
class Fixture:
    label: str
    v_fix: float


@dataclass
class Waveform:
    time_s: np.ndarray
    v_typ: np.ndarray
    r_fix: float
    v_fix: float
    c_fix: float


FIXTURES = [
    Fixture(label="vfix_0p0", v_fix=0.0),
    Fixture(label="vfix_1p2", v_fix=1.2),
]


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


def choose_waveform(data_model, kind: str, target_v_fix: float) -> Waveform:
    candidates = data_model.vt_rising if kind == "rising" else data_model.vt_falling
    best = None
    best_score = None

    for wf in candidates:
        score = (
            abs(float(wf.r_fix) - TARGET_R_FIX),
            abs(float(wf.v_fix[0]) - target_v_fix),
            abs(float(wf.c_fix[0]) - TARGET_C_FIX),
        )
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
        c_fix=float(best.c_fix[0]),
    )


def read_subckt_name(path: Path) -> str:
    for line in path.read_text().splitlines():
        if line.startswith(".SUBCKT "):
            return line.split()[1]
    raise RuntimeError(f"Could not find .SUBCKT line in {path}")


def bench_path_for(fixture: Fixture) -> Path:
    return ROOT / f"{MODEL_NAME}_fixture_1k_20pf_{fixture.label}_no_cfix.sp"


def raw_path_for(fixture: Fixture) -> Path:
    return ROOT / f"{MODEL_NAME}_fixture_1k_20pf_{fixture.label}_no_cfix.raw"


def plot_path_for(kind: str, fixture: Fixture) -> Path:
    return PLOT_DIR / f"{MODEL_NAME}_{kind}_{fixture.label}_no_cfix.png"


def write_bench(subckt_path: Path, subckt_name: str, vcc: float, enable_active_low: bool, fixture: Fixture, c_fix: float):
    pulse_width_ns = FALL_START_NS - RISE_START_NS
    include_path = subckt_path.as_posix()
    en_level = 0.0 if enable_active_low else vcc
    bench_text = "\n".join(
        [
            ".temp 50",
            ".options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12",
            f"Vin in_src 0 PULSE(0 {vcc} {RISE_START_NS}n 5p 5p {pulse_width_ns}n {2*STOP_NS}n)",
            "Rin in_src in_dig 1",
            f"Ven en_sig 0 DC {en_level}",
            f"Vdd vdd 0 DC {vcc}",
            f"Vfix vfix 0 DC {fixture.v_fix}",
            f".include '{include_path}'",
            f"XDRV pad in_dig en_sig vdd 0 {subckt_name}",
            f"Rload pad vfix {TARGET_R_FIX}",
            f"Cload pad 0 {c_fix}",
            ".save V(in_dig) V(pad)",
            f".tran 25p {STOP_NS}n",
            ".end",
            "",
        ]
    )
    bench_path_for(fixture).write_text(bench_text, encoding="utf-8")


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
        "combined_rms_error_v": float(np.sqrt(np.mean(np.concatenate([rise_err, fall_err]) ** 2))),
    }


def plot_edge(sim_time_s: np.ndarray, sim_pad: np.ndarray, sim_in: np.ndarray, waveform: Waveform,
              edge_kind: str, fixture: Fixture):
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    t_ns = sim_time_s * 1e9
    start_ns = RISE_START_NS if edge_kind == "rise" else FALL_START_NS
    edge_t_ns = waveform.time_s * 1e9 + start_ns
    sim_edge = np.interp(edge_t_ns * 1e-9, sim_time_s, sim_pad)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(edge_t_ns, waveform.v_typ, label=f"IBIS {edge_kind}", linewidth=2)
    ax.plot(edge_t_ns, sim_edge, label=f"pybis {edge_kind} (no C_fixture in solve)", linewidth=2, linestyle="--")
    ax.plot(t_ns, sim_in, "--", label="input", linewidth=1.0, alpha=0.65, color="gray")
    ax.set_xlim(start_ns - 2, start_ns + waveform.time_s[-1] * 1e9 + 2)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title(f"{MODEL_NAME} {edge_kind} overlay ({fixture.label.replace('_', ' = ').replace('p', '.')}, no C_fixture)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_path_for(edge_kind, fixture), dpi=170)
    plt.close(fig)


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_IBIS.resolve() != SOURCE_IBIS.resolve():
        shutil.copyfile(SOURCE_IBIS, LOCAL_IBIS)

    ibis = pybis2spice.get_ibis_model_ecdtools(str(LOCAL_IBIS))
    data_model = pybis2spice.DataModel(ibis, MODEL_NAME, COMPONENT_NAME)
    for wf in data_model.vt_rising + data_model.vt_falling:
        wf.c_fix[:] = 0.0

    vcc = float(data_model.v_range[0])
    enable_active_low = str(getattr(data_model, "enable", "")).lower() == "active-low"

    subcircuit.generate_spice_model(
        io_type="Output",
        subcircuit_type="InputDriven",
        ibis_data=data_model,
        corner=CORNER,
        output_filepath=str(CONVERTED_SUB),
    )
    subckt_name = read_subckt_name(CONVERTED_SUB)

    rows = []
    for fixture in FIXTURES:
        rise = choose_waveform(data_model, "rising", fixture.v_fix)
        fall = choose_waveform(data_model, "falling", fixture.v_fix)

        write_bench(CONVERTED_SUB, subckt_name, vcc, enable_active_low, fixture, TARGET_C_FIX)
        bench_path = bench_path_for(fixture)
        raw_path = raw_path_for(fixture)

        proc = subprocess.run(
            [str(NGSPICE_BIN), "-b", "-r", str(raw_path.name), str(bench_path.name)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"ngspice failed for {fixture.label}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

        traces = parse_ngspice_raw(raw_path)
        sim_time_s = traces["time"]
        sim_pad = traces["v(pad)"]
        sim_in = traces["v(in_dig)"]

        metrics = compute_metrics(sim_time_s, sim_pad, rise, fall)
        plot_edge(sim_time_s, sim_pad, sim_in, rise, "rise", fixture)
        plot_edge(sim_time_s, sim_pad, sim_in, fall, "fall", fixture)

        rows.append(
            {
                "model": MODEL_NAME,
                "component": COMPONENT_NAME,
                "corner": CORNER,
                "fixture_label": fixture.label,
                "fixture_v_fix_v": fixture.v_fix,
                "fixture_r_fix_ohm": TARGET_R_FIX,
                "fixture_c_fix_f": TARGET_C_FIX,
                "vcc_v": vcc,
                "enable": data_model.enable,
                **metrics,
                "rise_plot": plot_path_for("rise", fixture).name,
                "fall_plot": plot_path_for("fall", fixture).name,
                "bench_file": bench_path.name,
                "raw_file": raw_path.name,
                "subckt_file": CONVERTED_SUB.name,
            }
        )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md_lines = [
        "# Arbel I3C Validation (Without C_fixture In Solve)",
        "",
        f"- Source IBIS: `{LOCAL_IBIS}`",
        f"- Component: `{COMPONENT_NAME}`",
        f"- Model: `{MODEL_NAME}`",
        "- Converted mode: `InputDriven`",
        f"- Corner: `{CORNER}`",
        "- Bench family: `1 kOhm` to `V_fixture` in parallel with `20 pF` to ground",
        "- Extraction mode: `C_fixture forced to 0 during Ku/Kd solve`",
        "",
        "| Fixture | Rise RMS (V) | Rise Max (V) | Fall RMS (V) | Fall Max (V) | Rise Plot | Fall Plot |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        md_lines.append(
            f"| `{row['fixture_label']}` | {row['rise_rms_error_v']:.6f} | {row['rise_max_abs_error_v']:.6f} | "
            f"{row['fall_rms_error_v']:.6f} | {row['fall_max_abs_error_v']:.6f} | "
            f"`{row['rise_plot']}` | `{row['fall_plot']}` |"
        )
    MD_PATH.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Wrote no-cfix validation artifacts to {ROOT}")
    for row in rows:
        print(
            f"{row['fixture_label']}: rise RMS={row['rise_rms_error_v']:.6f} V, "
            f"fall RMS={row['fall_rms_error_v']:.6f} V, combined RMS={row['combined_rms_error_v']:.6f} V"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
