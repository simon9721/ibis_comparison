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
from pybis2spice import subcircuit  # noqa: E402


IBIS_PATH = ROOT / "pcbauto" / "Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs"
COMPONENT_NAME = "A11486_IBIS-00001760"
MODEL_NAME = "I3C_TX_0p125mA_tx"
CORNER = "Typical"
SUBCKT_TYPE = "InputDriven"
IO_TYPE = "Output"

OUT_DIR = ROOT / "results" / "hibiki_i3c_tx_0p125ma_1160ohm_ngspice_2026-05-28"
CONVERTED_DIR = OUT_DIR / "converted"
BENCH_DIR = OUT_DIR / "benches"
RAW_DIR = OUT_DIR / "raw"
PLOT_DIR = OUT_DIR / "plots"

NGSPICE_BIN = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

VDD = 1.2
R_LOAD = 1160.0
RISE_START_NS = 10.0
FALL_START_NS = 130.0
STOP_NS = 220.0
MAX_STEP_PS = 10.0


@dataclass
class LoadCase:
    tag: str
    v_fixture: float
    load_node: str
    title: str


LOAD_CASES = [
    LoadCase(
        tag="1160ohm_to_0v",
        v_fixture=0.0,
        load_node="0",
        title="1160 ohm load to 0 V",
    ),
    LoadCase(
        tag="1160ohm_to_1p2v",
        v_fixture=VDD,
        load_node="vfix",
        title="1160 ohm load to 1.2 V",
    ),
]


def parse_ngspice_raw(path: Path) -> dict[str, np.ndarray]:
    data = path.read_bytes()
    marker = b"Binary:\n"
    idx = data.find(marker)
    if idx < 0:
        raise RuntimeError(f"Binary marker not found in {path}")

    header = data[:idx].decode("latin1")
    nvars = None
    npts = None
    variables = []
    reading_vars = False
    for line in header.splitlines():
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
        if line.upper().startswith(".SUBCKT "):
            return line.split()[1]
    raise RuntimeError(f"Could not find .SUBCKT in {path}")


def generate_model(data_model) -> Path:
    CONVERTED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CONVERTED_DIR / f"{MODEL_NAME}_OutputInput_Typical.sub"
    subcircuit.generate_spice_model(
        io_type=IO_TYPE,
        subcircuit_type=SUBCKT_TYPE,
        ibis_data=data_model,
        corner=CORNER,
        output_filepath=str(out_path),
    )
    return out_path


def write_bench(case: LoadCase, subckt_path: Path, subckt_name: str) -> Path:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    bench_path = BENCH_DIR / f"{MODEL_NAME}_{case.tag}_rsf.sp"
    pulse_width_ns = FALL_START_NS - RISE_START_NS
    fixture_lines = []
    if case.load_node != "0":
        fixture_lines.append(f"Vfixture {case.load_node} 0 DC {case.v_fixture}")

    lines = [
        f"* {MODEL_NAME} pybis2spice ngspice matched-load experiment, {case.title}",
        ".temp 25",
        ".options method=gear maxord=2 reltol=1e-4 abstol=1e-12 vntol=1e-7 gmin=1e-12",
        f"Vin in_dig 0 PULSE(0 {VDD} {RISE_START_NS}n 5p 5p {pulse_width_ns}n {2 * STOP_NS}n)",
        f"Ven en_sig 0 DC {VDD}",
        f"Vdd vdd 0 DC {VDD}",
        *fixture_lines,
        f".include '{subckt_path.as_posix()}'",
        f"XDRV pad in_dig en_sig vdd 0 {subckt_name}",
        f"Rload pad {case.load_node} {R_LOAD}",
        ".save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)",
        f".tran {MAX_STEP_PS}p {STOP_NS}n",
        ".end",
        "",
    ]
    bench_path.write_text("\n".join(lines), encoding="utf-8")
    return bench_path


def run_ngspice(bench_path: Path, raw_path: Path) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(NGSPICE_BIN), "-b", "-r", str(raw_path), str(bench_path)],
        cwd=BENCH_DIR,
        capture_output=True,
        text=True,
    )
    raw_path.with_suffix(".log").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"ngspice failed for {bench_path}")


def window_average(time_s: np.ndarray, values: np.ndarray, start_ns: float, stop_ns: float) -> float:
    mask = (time_s >= start_ns * 1e-9) & (time_s <= stop_ns * 1e-9)
    if not np.any(mask):
        return float("nan")
    return float(np.mean(values[mask]))


def crossing_time_ns(
    time_s: np.ndarray,
    values: np.ndarray,
    start_ns: float,
    stop_ns: float,
    target: float,
    rising: bool,
) -> float:
    mask = (time_s >= start_ns * 1e-9) & (time_s <= stop_ns * 1e-9)
    t = time_s[mask] * 1e9
    y = values[mask]
    if len(t) < 2:
        return float("nan")

    for i in range(1, len(y)):
        y0 = y[i - 1]
        y1 = y[i]
        hit = y0 <= target <= y1 if rising else y0 >= target >= y1
        if hit and y1 != y0:
            frac = (target - y0) / (y1 - y0)
            return float(t[i - 1] + frac * (t[i] - t[i - 1]))
    return float("nan")


def edge_metrics(time_s: np.ndarray, pad: np.ndarray) -> dict[str, float]:
    low_before = window_average(time_s, pad, 8.0, 9.8)
    high_hold = window_average(time_s, pad, 110.0, 125.0)
    low_after = window_average(time_s, pad, 200.0, 220.0)

    rise_span = high_hold - low_before
    fall_span = high_hold - low_after
    rise_10 = low_before + 0.1 * rise_span
    rise_50 = low_before + 0.5 * rise_span
    rise_90 = low_before + 0.9 * rise_span
    fall_90 = low_after + 0.9 * fall_span
    fall_50 = low_after + 0.5 * fall_span
    fall_10 = low_after + 0.1 * fall_span

    t_r10 = crossing_time_ns(time_s, pad, RISE_START_NS, RISE_START_NS + 50.0, rise_10, True)
    t_r50 = crossing_time_ns(time_s, pad, RISE_START_NS, RISE_START_NS + 50.0, rise_50, True)
    t_r90 = crossing_time_ns(time_s, pad, RISE_START_NS, RISE_START_NS + 50.0, rise_90, True)
    t_f90 = crossing_time_ns(time_s, pad, FALL_START_NS, FALL_START_NS + 50.0, fall_90, False)
    t_f50 = crossing_time_ns(time_s, pad, FALL_START_NS, FALL_START_NS + 50.0, fall_50, False)
    t_f10 = crossing_time_ns(time_s, pad, FALL_START_NS, FALL_START_NS + 50.0, fall_10, False)

    return {
        "low_before_v": low_before,
        "high_hold_v": high_hold,
        "low_after_v": low_after,
        "rise_swing_v": rise_span,
        "fall_swing_v": fall_span,
        "rise_10_ns": t_r10,
        "rise_50_ns": t_r50,
        "rise_90_ns": t_r90,
        "rise_10_90_ns": t_r90 - t_r10,
        "fall_90_ns": t_f90,
        "fall_50_ns": t_f50,
        "fall_10_ns": t_f10,
        "fall_90_10_ns": t_f10 - t_f90,
    }


def plot_case(case: LoadCase, traces: dict[str, np.ndarray], metrics: dict[str, float], out_path: Path) -> None:
    time_ns = traces["time"] * 1e9
    pad = traces["v(pad)"]
    vin = traces["v(in_dig)"]
    ku = traces["v(xdrv.ku)"]
    kd = traces["v(xdrv.kd)"]

    fig, axes = plt.subplots(4, 1, figsize=(11.5, 13.5), sharex=False)
    fig.suptitle(f"{MODEL_NAME}: ngspice pybis, {case.title}", fontsize=14, y=0.995)

    axes[0].plot(time_ns, pad, linewidth=2.0, label="pad")
    axes[0].axhline(metrics["low_before_v"], color="#777777", linestyle=":", linewidth=1.1, label="pre-rise/final levels")
    axes[0].axhline(metrics["high_hold_v"], color="#777777", linestyle=":", linewidth=1.1)
    axes[0].axhline(metrics["low_after_v"], color="#777777", linestyle=":", linewidth=1.1)
    axes[0].set_title("Full rise-steady-fall output")
    axes[0].set_ylabel("Pad (V)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")
    ax0b = axes[0].twinx()
    ax0b.plot(time_ns, vin, color="#777777", alpha=0.35, linewidth=1.0)
    ax0b.set_ylabel("Input (V)", color="#777777")
    ax0b.tick_params(axis="y", labelcolor="#777777")

    axes[1].plot(time_ns, pad, linewidth=2.0, label=f"rise 10-90 = {metrics['rise_10_90_ns']:.3f} ns")
    axes[1].axvline(metrics["rise_10_ns"], color="#2ca02c", linestyle="--", linewidth=1.2, label="10/90 crossings")
    axes[1].axvline(metrics["rise_90_ns"], color="#2ca02c", linestyle="--", linewidth=1.2)
    axes[1].set_xlim(RISE_START_NS - 1.0, RISE_START_NS + 25.0)
    axes[1].set_title("Rising edge zoom")
    axes[1].set_ylabel("Pad (V)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    axes[2].plot(time_ns, pad, linewidth=2.0, label=f"fall 90-10 = {metrics['fall_90_10_ns']:.3f} ns")
    axes[2].axvline(metrics["fall_90_ns"], color="#d62728", linestyle="--", linewidth=1.2, label="90/10 crossings")
    axes[2].axvline(metrics["fall_10_ns"], color="#d62728", linestyle="--", linewidth=1.2)
    axes[2].set_xlim(FALL_START_NS - 1.0, FALL_START_NS + 25.0)
    axes[2].set_title("Falling edge zoom")
    axes[2].set_ylabel("Pad (V)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best")

    axes[3].plot(time_ns, ku, label="Ku", linewidth=1.7)
    axes[3].plot(time_ns, kd, label="Kd", linewidth=1.7)
    axes[3].set_title("pybis switching coefficients")
    axes[3].set_ylabel("Coefficient")
    axes[3].set_xlabel("Time (ns)")
    axes[3].grid(True, alpha=0.3)
    axes[3].legend(loc="best")

    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_overlay(case_traces: dict[str, dict[str, np.ndarray]], out_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.2), sharex=True)
    for label, traces in case_traces.items():
        time_ns = traces["time"] * 1e9
        axes[0].plot(time_ns, traces["v(pad)"], linewidth=2.0, label=label)
        axes[1].plot(time_ns, traces["v(in_dig)"], linewidth=1.2, alpha=0.6, label=label)
    axes[0].set_title(f"{MODEL_NAME}: 1160 ohm load comparison")
    axes[0].set_ylabel("Pad (V)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")
    axes[1].set_ylabel("Input (V)")
    axes[1].set_xlabel("Time (ns)")
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    for path in (CONVERTED_DIR, BENCH_DIR, RAW_DIR, PLOT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    ibis = pybis2spice.get_ibis_model_ecdtools(str(IBIS_PATH))
    data_model = pybis2spice.DataModel(ibis, MODEL_NAME, COMPONENT_NAME)
    subckt_path = generate_model(data_model)
    subckt_name = read_subckt_name(subckt_path)

    rows = []
    traces_by_title = {}
    for case in LOAD_CASES:
        bench_path = write_bench(case, subckt_path, subckt_name)
        raw_path = RAW_DIR / f"{MODEL_NAME}_{case.tag}_rsf.raw"
        run_ngspice(bench_path, raw_path)
        traces = parse_ngspice_raw(raw_path)
        metrics = edge_metrics(traces["time"], traces["v(pad)"])
        plot_path = PLOT_DIR / f"{MODEL_NAME}_{case.tag}_ngspice.png"
        plot_case(case, traces, metrics, plot_path)
        traces_by_title[case.title] = traces

        rows.append(
            {
                "model": MODEL_NAME,
                "case": case.tag,
                "r_load_ohm": R_LOAD,
                "v_fixture_v": case.v_fixture,
                **metrics,
                "bench": str(bench_path.relative_to(OUT_DIR)),
                "raw": str(raw_path.relative_to(OUT_DIR)),
                "plot": str(plot_path.relative_to(OUT_DIR)),
            }
        )

    plot_overlay(traces_by_title, PLOT_DIR / f"{MODEL_NAME}_1160ohm_overlay.png")

    csv_path = OUT_DIR / "matched_load_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    readme = [
        f"# {MODEL_NAME} 1160 ohm matched-load ngspice run",
        "",
        f"- Source IBIS: `{IBIS_PATH.relative_to(ROOT)}`",
        f"- Component: `{COMPONENT_NAME}`",
        f"- Corner: `{CORNER}`",
        f"- Converted model: `{subckt_path.relative_to(OUT_DIR)}`",
        "- Simulator: ngspice via pybis2spice InputDriven subcircuit",
        f"- Load: `{R_LOAD:g} ohm`",
        f"- Stimulus: `0 V -> {VDD} V -> 0 V`, rise at `{RISE_START_NS} ns`, fall at `{FALL_START_NS} ns`",
        "",
        "This is not a direct IBIS VT-table validation because the source IBIS only provides VT tables with `R_fixture=50 ohm`. These runs test the converted pybis/ngspice model under a 1160 ohm load.",
        "",
        "Important interpretation note: a 1160 ohm DC termination changes the load line, so these are not full-swing capacitive I3C bus edges. The `1160ohm_to_0v` case settles near half supply, while the `1160ohm_to_1p2v` case biases the pad high and can exceed VDD because the IBIS pullup IV curve is being evaluated against a 1.2 V fixture.",
        "",
        "| Case | Low before | High hold | Low after | Rise swing | Rise 10-90 | Fall 90-10 | Plot |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        readme.append(
            f"| `{row['case']}` | `{float(row['low_before_v']):.4f} V` | `{float(row['high_hold_v']):.4f} V` | "
            f"`{float(row['low_after_v']):.4f} V` | `{float(row['rise_swing_v']):.4f} V` | "
            f"`{float(row['rise_10_90_ns']):.3f} ns` | `{float(row['fall_90_10_ns']):.3f} ns` | `{row['plot']}` |"
        )
    readme.extend(
        [
            "",
            "Generated files:",
            "",
            "- `matched_load_summary.csv`",
            f"- `plots/{MODEL_NAME}_1160ohm_overlay.png`",
            f"- `plots/{MODEL_NAME}_1160ohm_to_0v_ngspice.png`",
            f"- `plots/{MODEL_NAME}_1160ohm_to_1p2v_ngspice.png`",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(readme), encoding="utf-8")

    print(f"Wrote 1160 ohm matched-load artifacts to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
