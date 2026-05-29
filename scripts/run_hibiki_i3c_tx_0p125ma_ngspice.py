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

OUT_DIR = ROOT / "results" / "hibiki_i3c_tx_0p125ma_ngspice_2026-05-28"
CONVERTED_DIR = OUT_DIR / "converted"
BENCH_DIR = OUT_DIR / "benches"
RAW_DIR = OUT_DIR / "raw"
PLOT_DIR = OUT_DIR / "plots"

NGSPICE_BIN = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

VDD = 1.2
RISE_START_NS = 10.0
FALL_START_NS = 130.0
STOP_NS = 220.0
MAX_STEP_PS = 10.0
R_FIXTURE = 50.0


@dataclass
class Waveform:
    time_s: np.ndarray
    v_typ: np.ndarray
    r_fix: float
    v_fix: float


@dataclass
class FixtureCase:
    tag: str
    v_fixture: float
    load_node: str
    title: str


FIXTURES = [
    FixtureCase(
        tag="vfixture_0v",
        v_fixture=0.0,
        load_node="0",
        title="50 ohm to 0 V fixture",
    ),
    FixtureCase(
        tag="vfixture_1p2v",
        v_fixture=1.2,
        load_node="vfix",
        title="50 ohm to 1.2 V fixture",
    ),
]


def parse_ngspice_raw(path: Path) -> dict[str, np.ndarray]:
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


def read_subckt_name(path: Path) -> str:
    for line in path.read_text().splitlines():
        if line.upper().startswith(".SUBCKT "):
            return line.split()[1]
    raise RuntimeError(f"Could not find .SUBCKT in {path}")


def choose_waveform(data_model, kind: str, v_fixture: float) -> Waveform:
    candidates = data_model.vt_rising if kind == "rising" else data_model.vt_falling
    best = None
    best_score = None
    for wf in candidates:
        score = abs(float(wf.r_fix) - R_FIXTURE) + abs(float(wf.v_fix[0]) - v_fixture)
        if best is None or score < best_score:
            best = wf
            best_score = score
    if best is None:
        raise RuntimeError(f"No {kind} waveform found for {MODEL_NAME}")
    return Waveform(
        time_s=np.asarray(best.data[:, 0], dtype=float),
        v_typ=np.asarray(best.data[:, 1], dtype=float),
        r_fix=float(best.r_fix),
        v_fix=float(best.v_fix[0]),
    )


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


def write_bench(fixture: FixtureCase, subckt_path: Path, subckt_name: str) -> Path:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    bench_path = BENCH_DIR / f"{MODEL_NAME}_{fixture.tag}_rsf.sp"
    pulse_width_ns = FALL_START_NS - RISE_START_NS
    vfix_lines = []
    if fixture.load_node != "0":
        vfix_lines.append(f"Vfixture {fixture.load_node} 0 DC {fixture.v_fixture}")

    lines = [
        f"* {MODEL_NAME} pybis2spice ngspice validation, {fixture.title}",
        ".temp 25",
        ".options method=gear maxord=2 reltol=1e-4 abstol=1e-12 vntol=1e-7 gmin=1e-12",
        f"Vin in_dig 0 PULSE(0 {VDD} {RISE_START_NS}n 5p 5p {pulse_width_ns}n {2*STOP_NS}n)",
        f"Ven en_sig 0 DC {VDD}",
        f"Vdd vdd 0 DC {VDD}",
        *vfix_lines,
        f".include '{subckt_path.as_posix()}'",
        f"XDRV pad in_dig en_sig vdd 0 {subckt_name}",
        f"Rload pad {fixture.load_node} {R_FIXTURE}",
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
    log_path = raw_path.with_suffix(".log")
    log_path.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"ngspice failed for {bench_path}\n{log_path.read_text()}")


def stitched_reference(time_s: np.ndarray, rise: Waveform, fall: Waveform) -> np.ndarray:
    ref = np.full_like(time_s, rise.v_typ[0])
    rise_t = rise.time_s + RISE_START_NS * 1e-9
    fall_t = fall.time_s + FALL_START_NS * 1e-9

    rise_mask = (time_s >= rise_t[0]) & (time_s <= rise_t[-1])
    ref[rise_mask] = np.interp(time_s[rise_mask], rise_t, rise.v_typ)

    hold_mask = (time_s > rise_t[-1]) & (time_s < fall_t[0])
    ref[hold_mask] = rise.v_typ[-1]

    fall_mask = (time_s >= fall_t[0]) & (time_s <= fall_t[-1])
    ref[fall_mask] = np.interp(time_s[fall_mask], fall_t, fall.v_typ)

    after_fall = time_s > fall_t[-1]
    ref[after_fall] = fall.v_typ[-1]
    return ref


def compute_metrics(time_s: np.ndarray, pad: np.ndarray, rise: Waveform, fall: Waveform) -> dict[str, float]:
    rise_t = rise.time_s + RISE_START_NS * 1e-9
    fall_t = fall.time_s + FALL_START_NS * 1e-9
    sim_rise = np.interp(rise_t, time_s, pad)
    sim_fall = np.interp(fall_t, time_s, pad)
    rise_err = sim_rise - rise.v_typ
    fall_err = sim_fall - fall.v_typ
    return {
        "rise_rmse_mv": float(np.sqrt(np.mean(rise_err**2)) * 1000.0),
        "rise_max_abs_mv": float(np.max(np.abs(rise_err)) * 1000.0),
        "fall_rmse_mv": float(np.sqrt(np.mean(fall_err**2)) * 1000.0),
        "fall_max_abs_mv": float(np.max(np.abs(fall_err)) * 1000.0),
        "sim_initial_v": float(pad[0]),
        "sim_final_v": float(pad[-1]),
        "rise_ibis_final_v": float(rise.v_typ[-1]),
        "fall_ibis_final_v": float(fall.v_typ[-1]),
    }


def relative_mv(y: np.ndarray, v_fixture: float) -> np.ndarray:
    return (y - v_fixture) * 1000.0


def plot_fixture(
    fixture: FixtureCase,
    traces: dict[str, np.ndarray],
    rise: Waveform,
    fall: Waveform,
    ref: np.ndarray,
    out_path: Path,
) -> None:
    time_s = traces["time"]
    t_ns = time_s * 1e9
    pad = traces["v(pad)"]
    vin = traces["v(in_dig)"]
    ku = traces.get("v(xdrv.ku)")
    kd = traces.get("v(xdrv.kd)")

    fig, axes = plt.subplots(4, 1, figsize=(11.5, 13.5), sharex=False)
    fig.suptitle(f"{MODEL_NAME}: ngspice pybis validation, {fixture.title}", fontsize=14, y=0.995)

    axes[0].plot(t_ns, relative_mv(pad, fixture.v_fixture), label="ngspice pybis pad", linewidth=2.0)
    axes[0].plot(t_ns, relative_mv(ref, fixture.v_fixture), label="IBIS VT stitched reference", linewidth=1.9, linestyle="--")
    axes[0].set_title("Full rise-steady-fall output, plotted relative to V_fixture")
    axes[0].set_ylabel("Pad - V_fixture (mV)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")
    ax0b = axes[0].twinx()
    ax0b.plot(t_ns, vin, color="#777777", alpha=0.35, linewidth=1.0, label="input")
    ax0b.set_ylabel("Input (V)", color="#777777")
    ax0b.tick_params(axis="y", labelcolor="#777777")

    rise_t_ns = rise.time_s * 1e9 + RISE_START_NS
    axes[1].plot(rise_t_ns, relative_mv(rise.v_typ, fixture.v_fixture), label="IBIS rise", linewidth=2.0)
    axes[1].plot(
        rise_t_ns,
        relative_mv(np.interp(rise_t_ns * 1e-9, time_s, pad), fixture.v_fixture),
        label="ngspice pybis rise",
        linewidth=1.9,
        linestyle="--",
    )
    axes[1].set_title("Rising waveform zoom")
    axes[1].set_xlim(RISE_START_NS - 2.0, RISE_START_NS + rise.time_s[-1] * 1e9 + 4.0)
    axes[1].set_ylabel("Pad - V_fixture (mV)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    fall_t_ns = fall.time_s * 1e9 + FALL_START_NS
    axes[2].plot(fall_t_ns, relative_mv(fall.v_typ, fixture.v_fixture), label="IBIS fall", linewidth=2.0)
    axes[2].plot(
        fall_t_ns,
        relative_mv(np.interp(fall_t_ns * 1e-9, time_s, pad), fixture.v_fixture),
        label="ngspice pybis fall",
        linewidth=1.9,
        linestyle="--",
    )
    axes[2].set_title("Falling waveform zoom")
    axes[2].set_xlim(FALL_START_NS - 2.0, FALL_START_NS + fall.time_s[-1] * 1e9 + 4.0)
    axes[2].set_ylabel("Pad - V_fixture (mV)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best")

    if ku is not None and kd is not None:
        axes[3].plot(t_ns, ku, label="Ku", linewidth=1.6)
        axes[3].plot(t_ns, kd, label="Kd", linewidth=1.6)
        axes[3].set_ylabel("Coefficient")
    else:
        axes[3].plot(t_ns, vin, label="Input", linewidth=1.6)
        axes[3].set_ylabel("Input (V)")
    axes[3].set_title("pybis switching coefficients")
    axes[3].set_xlabel("Time (ns)")
    axes[3].grid(True, alpha=0.3)
    axes[3].legend(loc="best")

    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_fixture_comparison(rows: list[dict[str, object]]) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    labels = []
    rise = []
    fall = []
    for row in rows:
        labels.append(str(row["fixture"]))
        rise.append(float(row["rise_rmse_mv"]))
        fall.append(float(row["fall_rmse_mv"]))
    x = np.arange(len(labels))
    width = 0.36
    ax.bar(x - width / 2, rise, width, label="Rise RMSE")
    ax.bar(x + width / 2, fall, width, label="Fall RMSE")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Error vs IBIS VT table (mV)")
    ax.set_title(f"{MODEL_NAME}: ngspice vs IBIS table error summary")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "error_summary.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    for path in (CONVERTED_DIR, BENCH_DIR, RAW_DIR, PLOT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    ibis = pybis2spice.get_ibis_model_ecdtools(str(IBIS_PATH))
    data_model = pybis2spice.DataModel(ibis, MODEL_NAME, COMPONENT_NAME)
    subckt_path = generate_model(data_model)
    subckt_name = read_subckt_name(subckt_path)

    rows = []
    for fixture in FIXTURES:
        rise = choose_waveform(data_model, "rising", fixture.v_fixture)
        fall = choose_waveform(data_model, "falling", fixture.v_fixture)
        bench_path = write_bench(fixture, subckt_path, subckt_name)
        raw_path = RAW_DIR / f"{MODEL_NAME}_{fixture.tag}_rsf.raw"
        run_ngspice(bench_path, raw_path)

        traces = parse_ngspice_raw(raw_path)
        ref = stitched_reference(traces["time"], rise, fall)
        metrics = compute_metrics(traces["time"], traces["v(pad)"], rise, fall)
        plot_path = PLOT_DIR / f"{MODEL_NAME}_{fixture.tag}_ngspice_vs_ibis.png"
        plot_fixture(fixture, traces, rise, fall, ref, plot_path)

        rows.append(
            {
                "model": MODEL_NAME,
                "fixture": fixture.tag,
                "v_fixture_v": fixture.v_fixture,
                "r_fixture_ohm": R_FIXTURE,
                "rise_v_initial_v": float(rise.v_typ[0]),
                "rise_v_final_v": float(rise.v_typ[-1]),
                "fall_v_initial_v": float(fall.v_typ[0]),
                "fall_v_final_v": float(fall.v_typ[-1]),
                **metrics,
                "bench": str(bench_path.relative_to(OUT_DIR)),
                "raw": str(raw_path.relative_to(OUT_DIR)),
                "plot": str(plot_path.relative_to(OUT_DIR)),
            }
        )

    plot_fixture_comparison(rows)

    csv_path = OUT_DIR / "validation_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    readme_lines = [
        f"# {MODEL_NAME} ngspice validation",
        "",
        f"- Source IBIS: `{IBIS_PATH.relative_to(ROOT)}`",
        f"- Component: `{COMPONENT_NAME}`",
        f"- Corner: `{CORNER}`",
        f"- Converted model: `{subckt_path.relative_to(OUT_DIR)}`",
        "- Simulator: ngspice via pybis2spice InputDriven subcircuit",
        f"- Stimulus: `0 V -> {VDD} V -> 0 V`, rise at `{RISE_START_NS} ns`, fall at `{FALL_START_NS} ns`",
        f"- Fixtures simulated: `50 ohm` to `0 V`, and `50 ohm` to `{VDD} V`",
        "",
        "The 0.125 mA driver has a small 50 ohm fixture swing. Plots show `pad - V_fixture` in millivolts so the waveform is readable.",
        "",
        "| Fixture | Rise swing | Fall swing | Rise RMSE | Fall RMSE | Plot |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        rise_swing = (float(row["rise_v_final_v"]) - float(row["rise_v_initial_v"])) * 1000.0
        fall_swing = (float(row["fall_v_final_v"]) - float(row["fall_v_initial_v"])) * 1000.0
        readme_lines.append(
            f"| `{row['fixture']}` | `{rise_swing:.3f} mV` | `{fall_swing:.3f} mV` | "
            f"`{float(row['rise_rmse_mv']):.3f} mV` | `{float(row['fall_rmse_mv']):.3f} mV` | "
            f"`{row['plot']}` |"
        )
    readme_lines.extend(
        [
            "",
            "Generated files:",
            "",
            "- `validation_summary.csv`",
            "- `plots/error_summary.png`",
            f"- `plots/{MODEL_NAME}_vfixture_0v_ngspice_vs_ibis.png`",
            f"- `plots/{MODEL_NAME}_vfixture_1p2v_ngspice_vs_ibis.png`",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    print(f"Wrote Hibiki validation artifacts to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
