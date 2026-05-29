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

OUT_DIR = ROOT / "results" / "hibiki_i3c_tx_0p125ma_1160ohm_ground_5pulse_ngspice_2026-05-28"
CONVERTED_DIR = OUT_DIR / "converted"
BENCH_DIR = OUT_DIR / "benches"
RAW_DIR = OUT_DIR / "raw"
PLOT_DIR = OUT_DIR / "plots"

NGSPICE_BIN = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

VDD = 1.2
R_LOAD = 1160.0
LOAD_NODE = "0"
START_NS = 10.0
HIGH_NS = 20.0
LOW_NS = 20.0
PULSE_COUNT = 5
EDGE_PS = 5.0
STOP_NS = START_NS + PULSE_COUNT * (HIGH_NS + LOW_NS) + 20.0
MAX_STEP_PS = 10.0


@dataclass
class EdgeResult:
    edge_index: int
    edge_type: str
    input_edge_ns: float
    t_10_ns: float
    t_50_ns: float
    t_90_ns: float
    t_10_90_ns: float
    low_v: float
    high_v: float


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


def input_transitions() -> list[tuple[float, float]]:
    transitions = [(0.0, 0.0)]
    t_ns = START_NS
    level = VDD
    for _ in range(PULSE_COUNT * 2):
        transitions.append((t_ns, transitions[-1][1]))
        transitions.append((t_ns + EDGE_PS * 1e-3, level))
        t_ns += HIGH_NS if level == VDD else LOW_NS
        level = 0.0 if level == VDD else VDD
    transitions.append((STOP_NS, transitions[-1][1]))
    return transitions


def pwl_string() -> str:
    items = []
    for t_ns, value in input_transitions():
        items.append(f"{t_ns:.6g}n")
        items.append(f"{value:.6g}")
    return " ".join(items)


def write_bench(subckt_path: Path, subckt_name: str) -> Path:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    bench_path = BENCH_DIR / f"{MODEL_NAME}_1160ohm_ground_5pulse.sp"
    lines = [
        f"* {MODEL_NAME} pybis2spice ngspice, 5 pulses, 1160 ohm to ground",
        ".temp 25",
        ".options method=gear maxord=2 reltol=1e-4 abstol=1e-12 vntol=1e-7 gmin=1e-12",
        f"Vin in_dig 0 PWL({pwl_string()})",
        f"Ven en_sig 0 DC {VDD}",
        f"Vdd vdd 0 DC {VDD}",
        f".include '{subckt_path.as_posix()}'",
        f"XDRV pad in_dig en_sig vdd 0 {subckt_name}",
        f"Rload pad {LOAD_NODE} {R_LOAD}",
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


def average_between(time_ns: np.ndarray, values: np.ndarray, start_ns: float, stop_ns: float) -> float:
    mask = (time_ns >= start_ns) & (time_ns <= stop_ns)
    if not np.any(mask):
        return float("nan")
    return float(np.mean(values[mask]))


def crossing_time(time_ns: np.ndarray, values: np.ndarray, target: float, start_ns: float, stop_ns: float, rising: bool) -> float:
    mask = (time_ns >= start_ns) & (time_ns <= stop_ns)
    t = time_ns[mask]
    y = values[mask]
    for i in range(1, len(y)):
        if rising:
            hit = y[i - 1] <= target <= y[i]
        else:
            hit = y[i - 1] >= target >= y[i]
        if hit and y[i] != y[i - 1]:
            frac = (target - y[i - 1]) / (y[i] - y[i - 1])
            return float(t[i - 1] + frac * (t[i] - t[i - 1]))
    return float("nan")


def edge_metrics(time_ns: np.ndarray, pad: np.ndarray) -> list[EdgeResult]:
    edges: list[EdgeResult] = []
    edge_times = [START_NS + i * (HIGH_NS if i % 2 == 0 else LOW_NS) for i in range(PULSE_COUNT * 2)]
    # HIGH_NS and LOW_NS are equal in this script, but keep explicit transition construction readable.
    edge_times = [START_NS + i * HIGH_NS for i in range(PULSE_COUNT * 2)]

    for i, edge_ns in enumerate(edge_times, start=1):
        rising = i % 2 == 1
        if rising:
            low_v = average_between(time_ns, pad, edge_ns - 4.0, edge_ns - 0.5)
            high_v = average_between(time_ns, pad, edge_ns + HIGH_NS - 5.0, edge_ns + HIGH_NS - 1.0)
            v10 = low_v + 0.1 * (high_v - low_v)
            v50 = low_v + 0.5 * (high_v - low_v)
            v90 = low_v + 0.9 * (high_v - low_v)
            t10 = crossing_time(time_ns, pad, v10, edge_ns, edge_ns + 15.0, True)
            t50 = crossing_time(time_ns, pad, v50, edge_ns, edge_ns + 15.0, True)
            t90 = crossing_time(time_ns, pad, v90, edge_ns, edge_ns + 15.0, True)
            label = "rise"
        else:
            high_v = average_between(time_ns, pad, edge_ns - 4.0, edge_ns - 0.5)
            low_v = average_between(time_ns, pad, edge_ns + LOW_NS - 5.0, edge_ns + LOW_NS - 1.0)
            v90 = low_v + 0.9 * (high_v - low_v)
            v50 = low_v + 0.5 * (high_v - low_v)
            v10 = low_v + 0.1 * (high_v - low_v)
            t10 = crossing_time(time_ns, pad, v90, edge_ns, edge_ns + 15.0, False)
            t50 = crossing_time(time_ns, pad, v50, edge_ns, edge_ns + 15.0, False)
            t90 = crossing_time(time_ns, pad, v10, edge_ns, edge_ns + 15.0, False)
            label = "fall"
        edges.append(
            EdgeResult(
                edge_index=i,
                edge_type=label,
                input_edge_ns=edge_ns,
                t_10_ns=t10,
                t_50_ns=t50,
                t_90_ns=t90,
                t_10_90_ns=t90 - t10,
                low_v=low_v,
                high_v=high_v,
            )
        )
    return edges


def plot_full(time_ns: np.ndarray, vin: np.ndarray, pad: np.ndarray, ku: np.ndarray, kd: np.ndarray, edges: list[EdgeResult]) -> Path:
    out_path = PLOT_DIR / f"{MODEL_NAME}_1160ohm_ground_5pulse_full.png"
    fig, ax = plt.subplots(figsize=(12.0, 5.8))
    ax.plot(time_ns, vin, color="#555555", linewidth=1.8, label="input stimulus")
    ax.plot(time_ns, pad, color="#1f77b4", linewidth=2.2, label="pad response")
    for edge in edges:
        ax.axvline(edge.input_edge_ns, color="#bbbbbb", linewidth=0.8, alpha=0.45)
    ax.set_title(f"{MODEL_NAME}: 5-pulse input and pad overlay, 1160 ohm to ground")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.set_xlim(0.0, STOP_NS)
    ax.set_ylim(-0.06, 1.28)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_edge_overlay(time_ns: np.ndarray, pad: np.ndarray, edges: list[EdgeResult]) -> Path:
    out_path = PLOT_DIR / f"{MODEL_NAME}_1160ohm_ground_5pulse_edge_overlay.png"
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharey=True)
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, PULSE_COUNT))

    rise_edges = [edge for edge in edges if edge.edge_type == "rise"]
    fall_edges = [edge for edge in edges if edge.edge_type == "fall"]
    for idx, edge in enumerate(rise_edges):
        mask = (time_ns >= edge.input_edge_ns - 2.0) & (time_ns <= edge.input_edge_ns + 16.0)
        axes[0].plot(time_ns[mask] - edge.input_edge_ns, pad[mask], linewidth=2.0, color=colors[idx], label=f"rise {idx + 1}")
    for idx, edge in enumerate(fall_edges):
        mask = (time_ns >= edge.input_edge_ns - 2.0) & (time_ns <= edge.input_edge_ns + 16.0)
        axes[1].plot(time_ns[mask] - edge.input_edge_ns, pad[mask], linewidth=2.0, color=colors[idx], label=f"fall {idx + 1}")

    axes[0].set_title("Rising-edge overlay")
    axes[1].set_title("Falling-edge overlay")
    for ax in axes:
        ax.axvline(0.0, color="#777777", linestyle=":", linewidth=1.0)
        ax.set_xlabel("Time from input edge (ns)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
    axes[0].set_ylabel("Pad (V)")

    fig.suptitle(f"{MODEL_NAME}: repeated-edge comparison, 1160 ohm to ground", fontsize=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def write_outputs(bench_path: Path, raw_path: Path, full_plot: Path, overlay_plot: Path, edges: list[EdgeResult]) -> None:
    csv_path = OUT_DIR / "edge_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(edges[0].__dict__.keys()))
        writer.writeheader()
        writer.writerows([edge.__dict__ for edge in edges])

    rise_edges = [edge for edge in edges if edge.edge_type == "rise"]
    fall_edges = [edge for edge in edges if edge.edge_type == "fall"]
    mean_rise = np.mean([edge.t_10_90_ns for edge in rise_edges])
    mean_fall = np.mean([edge.t_10_90_ns for edge in fall_edges])
    mean_high = np.mean([edge.high_v for edge in rise_edges])
    mean_low = np.mean([edge.low_v for edge in rise_edges])

    readme = [
        f"# {MODEL_NAME} 1160 ohm ground-terminated 5-pulse ngspice run",
        "",
        f"- Source IBIS: `{IBIS_PATH.relative_to(ROOT)}`",
        f"- Component: `{COMPONENT_NAME}`",
        f"- Corner: `{CORNER}`",
        "- Simulator: ngspice via pybis2spice InputDriven subcircuit",
        f"- Termination: `{R_LOAD:g} ohm` from pad to ground",
        f"- Input: `{PULSE_COUNT}` high pulses, `{HIGH_NS:g} ns` high and `{LOW_NS:g} ns` low",
        f"- Rise/fall edge setting: `{EDGE_PS:g} ps`",
        "",
        f"Average settled low/high levels are approximately `{mean_low:.4f} V` and `{mean_high:.4f} V`. The average rise 10-90 is `{mean_rise:.3f} ns`; the average fall 90-10 is `{mean_fall:.3f} ns`.",
        "",
        "| Edge | Type | Input edge | 50% crossing | 10-90 / 90-10 | Low | High |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for edge in edges:
        readme.append(
            f"| `{edge.edge_index}` | `{edge.edge_type}` | `{edge.input_edge_ns:.3f} ns` | "
            f"`{edge.t_50_ns:.3f} ns` | `{edge.t_10_90_ns:.3f} ns` | "
            f"`{edge.low_v:.4f} V` | `{edge.high_v:.4f} V` |"
        )

    readme.extend(
        [
            "",
            "Generated files:",
            "",
            f"- `{bench_path.relative_to(OUT_DIR)}`",
            f"- `{raw_path.relative_to(OUT_DIR)}`",
            "- `edge_summary.csv`",
            f"- `{full_plot.relative_to(OUT_DIR)}`",
            f"- `{overlay_plot.relative_to(OUT_DIR)}`",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(readme), encoding="utf-8")


def main() -> int:
    for path in (CONVERTED_DIR, BENCH_DIR, RAW_DIR, PLOT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    ibis = pybis2spice.get_ibis_model_ecdtools(str(IBIS_PATH))
    data_model = pybis2spice.DataModel(ibis, MODEL_NAME, COMPONENT_NAME)
    subckt_path = generate_model(data_model)
    subckt_name = read_subckt_name(subckt_path)
    bench_path = write_bench(subckt_path, subckt_name)
    raw_path = RAW_DIR / f"{MODEL_NAME}_1160ohm_ground_5pulse.raw"
    run_ngspice(bench_path, raw_path)

    traces = parse_ngspice_raw(raw_path)
    time_ns = traces["time"] * 1e9
    pad = traces["v(pad)"]
    edges = edge_metrics(time_ns, pad)

    full_plot = plot_full(time_ns, traces["v(in_dig)"], pad, traces["v(xdrv.ku)"], traces["v(xdrv.kd)"], edges)
    overlay_plot = plot_edge_overlay(time_ns, pad, edges)
    write_outputs(bench_path, raw_path, full_plot, overlay_plot, edges)
    print(f"Wrote 1160 ohm ground-terminated 5-pulse artifacts to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
