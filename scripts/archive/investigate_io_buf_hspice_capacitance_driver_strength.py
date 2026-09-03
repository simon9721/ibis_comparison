from __future__ import annotations

import argparse
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


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402


OUT = ROOT / "results" / "io_buf_hspice_capacitance_driver_strength_2026-07-23"
RUNS = OUT / "runs"
PLOTS = OUT / "plots"
IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
FAST_IBIS = (
    ROOT
    / "results"
    / "io_buf_fast_edge_retest_2026-06-05"
    / "source"
    / "io_buf.ibs"
)
IO_BUF_SP = ROOT / "models" / "io_buf.sp"
ORIGINAL_MODEL = ROOT.parent / "s2ibispy" / "tests" / "hspice.mod"
MODIFIED_MODEL = ROOT / "models" / "hspice_ngspice.mod"
CHARACTERIZATION_T0_TR0 = OUT / "characterization_t0_edge" / "run.tr0"
VDD = 3.3
EDGE_RISE_NS = 5.0
EDGE_FALL_NS = 15.0


@dataclass(frozen=True)
class Flow:
    flow_id: str
    label: str
    kind: str
    model_path: Path | None = None
    supply_fixture: bool = False


FLOWS = [
    Flow("native_ibis", "Native IBIS, old slow-edge file", "ibis", IBIS),
    Flow("native_ibis_fast", "Native IBIS, regenerated 5 ps file", "ibis", FAST_IBIS),
    Flow(
        "transistor_original_ideal",
        "Transistor, original HSPICE model, ideal supply",
        "transistor",
        ORIGINAL_MODEL,
        False,
    ),
    Flow(
        "transistor_original_fixture",
        "Transistor, original HSPICE model, 1 ohm supply",
        "transistor",
        ORIGINAL_MODEL,
        True,
    ),
    Flow(
        "transistor_modified_fixture",
        "Previous transistor reference, modified model",
        "transistor",
        MODIFIED_MODEL,
        True,
    ),
]

COLORS = {
    "native_ibis": "#111111",
    "native_ibis_fast": "#009688",
    "transistor_original_ideal": "#d62728",
    "transistor_original_fixture": "#1f77b4",
    "transistor_modified_fixture": "#9467bd",
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def fmt(value: float) -> str:
    return f"{value:.12g}"


def case_id(c_pf: float, r_ohm: float) -> str:
    c_text = f"{c_pf:g}".replace(".", "p")
    r_text = f"{r_ohm:g}".replace(".", "p")
    return f"c{c_text}pf_r{r_text}"


def native_deck(c_pf: float, r_ohm: float) -> str:
    return f"""* io_buf native-IBIS capacitance/driver-strength investigation
.title io_buf native IBIS C={fmt(c_pf)}pF R={fmt(r_ohm)}ohm
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(0n 0 5n 0 5.001n 3.3 15n 3.3 15.001n 0 25n 0)
Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rdig dig_q 0 1k
Rload pad 0 {fmt(r_ohm)}
Cload pad 0 {fmt(c_pf)}p

.probe tran V(in_dig) V(pad) V(ku) V(kd) I(VPU) I(VPD)
.tran 0.001n 25n
.end
"""


def transistor_deck(c_pf: float, r_ohm: float, supply_fixture: bool) -> str:
    if supply_fixture:
        supply = """Vdd_src vdd_src 0 DC 3.3
Rvdd vdd_src vdd_ref 1
Cdec vdd_ref 0 10p
Voe_src oe_src 0 DC 3.3
Roe oe_src oe_ref 1"""
    else:
        supply = """Vdd_src vdd_ref 0 DC 3.3
Voe_src oe_ref 0 DC 3.3"""
    return f"""* io_buf transistor capacitance/driver-strength investigation
.title io_buf transistor C={fmt(c_pf)}pF R={fmt(r_ohm)}ohm
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(0n 0 5n 0 5.001n 3.3 15n 3.3 15.001n 0 25n 0)
{supply}

.include 'hspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XBUF in_dig oe_ref pad in_sense vdd_ref 0 SPICE_BUF
Rload pad 0 {fmt(r_ohm)}
Cload pad 0 {fmt(c_pf)}p

.probe tran V(in_dig) V(pad) V(vdd_ref) V(xbuf.n2) V(xbuf.n3) I(Vdd_src)
.tran 0.001n 25n
.end
"""


def run_hspice(
    flow: Flow,
    c_pf: float,
    r_ohm: float,
    hspice: Path,
    timeout_s: int,
    rerun: bool,
) -> Path:
    run_dir = RUNS / case_id(c_pf, r_ohm) / flow.flow_id
    ensure_dir(run_dir)
    stem = "run"
    deck = run_dir / f"{stem}.sp"
    tr0 = run_dir / f"{stem}.tr0"
    if flow.kind == "ibis":
        assert flow.model_path is not None
        shutil.copy2(flow.model_path, run_dir / "io_buf.ibs")
        text = native_deck(c_pf, r_ohm)
    else:
        assert flow.model_path is not None
        shutil.copy2(IO_BUF_SP, run_dir / "io_buf.sp")
        shutil.copy2(flow.model_path, run_dir / "hspice.mod")
        text = transistor_deck(c_pf, r_ohm, flow.supply_fixture)
    deck.write_text(text, encoding="ascii")
    if tr0.exists() and not rerun:
        return tr0
    log = run_dir / "hspice_stdout.log"
    with log.open("w", encoding="utf-8") as handle:
        try:
            completed = subprocess.run(
                [str(hspice), "-i", deck.name, "-o", stem],
                cwd=run_dir,
                stdout=handle,
                stderr=subprocess.STDOUT,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"HSPICE timeout: {run_dir}") from exc
    if completed.returncode != 0 or not tr0.exists():
        raise RuntimeError(
            f"HSPICE failed for {flow.flow_id}, C={c_pf} pF, R={r_ohm} ohm; see {log}"
        )
    return tr0


def signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray | None:
    by_name = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = by_name.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    return None


def parse_spice_number(token: str) -> float:
    match = re.fullmatch(
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)([fpnumkgt]?)",
        token.strip(),
        re.IGNORECASE,
    )
    if match is None:
        raise ValueError(token)
    scale = {
        "": 1.0,
        "f": 1e-15,
        "p": 1e-12,
        "n": 1e-9,
        "u": 1e-6,
        "m": 1e-3,
        "k": 1e3,
        "g": 1e9,
        "t": 1e12,
    }[match.group(2).lower()]
    return float(match.group(1)) * scale


def first_ibis_waveform(path: Path, section: str) -> tuple[np.ndarray, np.ndarray]:
    target = f"[{section.lower()}]"
    in_section = False
    started = False
    time_s: list[float] = []
    voltage: list[float] = []
    for raw in path.read_text(encoding="latin-1").splitlines():
        line = raw.strip()
        if line.startswith("["):
            if started:
                break
            in_section = line.lower() == target
            continue
        if not in_section or not line or line.startswith("|"):
            continue
        tokens = line.split()
        if len(tokens) < 2:
            continue
        try:
            time_s.append(parse_spice_number(tokens[0]))
            voltage.append(parse_spice_number(tokens[1]))
            started = True
        except ValueError:
            continue
    if not time_s:
        raise ValueError(f"No [{section}] data found in {path}")
    return np.asarray(time_s) * 1e9, np.asarray(voltage)


def crossing(
    t_ns: np.ndarray,
    y: np.ndarray,
    threshold: float,
    start_ns: float,
    stop_ns: float,
    rising: bool,
    which: str = "first",
) -> float:
    mask = (t_ns >= start_ns) & (t_ns <= stop_ns)
    tt = t_ns[mask]
    yy = y[mask]
    if len(tt) < 2:
        return float("nan")
    if rising:
        indexes = np.where((yy[:-1] < threshold) & (yy[1:] >= threshold))[0]
    else:
        indexes = np.where((yy[:-1] > threshold) & (yy[1:] <= threshold))[0]
    if len(indexes) == 0:
        return float("nan")
    i = int(indexes[-1] if which == "last" else indexes[0])
    dy = yy[i + 1] - yy[i]
    if abs(dy) < 1e-30:
        return float(tt[i])
    return float(tt[i] + (threshold - yy[i]) * (tt[i + 1] - tt[i]) / dy)


def measure(
    flow: Flow,
    c_pf: float,
    r_ohm: float,
    data: dict[str, np.ndarray],
) -> dict[str, object]:
    t_ns = np.asarray(data["time"], dtype=float) * 1e9
    pad = signal(data, "v(pad)")
    if pad is None:
        raise KeyError(f"pad not found in {sorted(data)}")
    low_mask = (t_ns >= 2.0) & (t_ns <= 4.5)
    high_mask = (t_ns >= 12.0) & (t_ns <= 14.5)
    v_low = float(np.median(pad[low_mask]))
    v_high = float(np.median(pad[high_mask]))
    amplitude = v_high - v_low
    rise_50 = crossing(
        t_ns, pad, v_low + 0.5 * amplitude, EDGE_RISE_NS, 12.0, True
    )
    rise_times = [
        crossing(
            t_ns,
            pad,
            v_low + 0.1 * amplitude,
            EDGE_RISE_NS,
            rise_50,
            True,
            "last",
        ),
        rise_50,
        crossing(
            t_ns,
            pad,
            v_low + 0.9 * amplitude,
            rise_50,
            12.0,
            True,
        ),
    ]
    fall_50 = crossing(
        t_ns, pad, v_low + 0.5 * amplitude, EDGE_FALL_NS, 22.0, False
    )
    fall_times = [
        crossing(
            t_ns,
            pad,
            v_low + 0.9 * amplitude,
            EDGE_FALL_NS,
            fall_50,
            False,
            "last",
        ),
        fall_50,
        crossing(
            t_ns,
            pad,
            v_low + 0.1 * amplitude,
            fall_50,
            22.0,
            False,
        ),
    ]
    i_load = v_high / r_ohm
    rout = (VDD - v_high) / i_load if i_load > 0 else float("nan")
    row: dict[str, object] = {
        "case_id": case_id(c_pf, r_ohm),
        "flow": flow.flow_id,
        "flow_label": flow.label,
        "c_load_pf": c_pf,
        "r_load_ohm": r_ohm,
        "v_low_v": v_low,
        "v_high_v": v_high,
        "amplitude_v": amplitude,
        "rise_10_delay_ns": rise_times[0] - EDGE_RISE_NS,
        "rise_50_delay_ns": rise_times[1] - EDGE_RISE_NS,
        "rise_90_delay_ns": rise_times[2] - EDGE_RISE_NS,
        "rise_10_90_ns": rise_times[2] - rise_times[0],
        "fall_90_delay_ns": fall_times[0] - EDGE_FALL_NS,
        "fall_50_delay_ns": fall_times[1] - EDGE_FALL_NS,
        "fall_10_delay_ns": fall_times[2] - EDGE_FALL_NS,
        "fall_90_10_ns": fall_times[2] - fall_times[0],
        "pad_peak_v": float(np.max(pad[(t_ns >= 4.5) & (t_ns <= 18.0)])),
        "pad_min_v": float(np.min(pad[(t_ns >= 4.5) & (t_ns <= 18.0)])),
        "load_current_high_ma": i_load * 1e3,
        "effective_pullup_r_ohm": rout,
    }
    if flow.kind == "ibis":
        ku = signal(data, "v(ku)")
        kd = signal(data, "v(kd)")
        if ku is not None:
            row["ku_50_delay_ns"] = (
                crossing(t_ns, ku, 0.5, EDGE_RISE_NS, 12.0, True) - EDGE_RISE_NS
            )
        if kd is not None:
            row["kd_off_50_delay_ns"] = (
                crossing(t_ns, kd, 0.5, EDGE_RISE_NS, 12.0, False) - EDGE_RISE_NS
            )
    else:
        n2 = signal(data, "v(xbuf.n2)")
        n3 = signal(data, "v(xbuf.n3)")
        vdd = signal(data, "v(vdd_ref)")
        if n2 is not None:
            row["n2_pu_gate_50_delay_ns"] = (
                crossing(t_ns, n2, VDD / 2, EDGE_RISE_NS, 12.0, False)
                - EDGE_RISE_NS
            )
        if n3 is not None:
            row["n3_pd_gate_50_delay_ns"] = (
                crossing(t_ns, n3, VDD / 2, EDGE_RISE_NS, 12.0, False)
                - EDGE_RISE_NS
            )
        if vdd is not None:
            row["vdd_high_v"] = float(np.median(vdd[high_mask]))
            row["vdd_droop_mv"] = (VDD - float(np.median(vdd[high_mask]))) * 1e3
    return row


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_wave(c_pf: float, r_ohm: float, flow: Flow) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    data = parse_hspice_tr0(RUNS / case_id(c_pf, r_ohm) / flow.flow_id / "run.tr0")
    t_ns = np.asarray(data["time"], dtype=float) * 1e9
    pad = signal(data, "v(pad)")
    assert pad is not None
    return t_ns, pad, data


def add_edge_lines(ax: plt.Axes) -> None:
    ax.axvline(EDGE_RISE_NS, color="#777777", ls="--", lw=1.0)
    ax.axvline(EDGE_FALL_NS, color="#777777", ls="--", lw=1.0)
    ax.grid(True, alpha=0.22)


def plot_baseline() -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13.2, 8.0), sharex=True, constrained_layout=True)
    reference_flow = next(flow for flow in FLOWS if flow.flow_id == "transistor_original_ideal")
    reference_t, reference_y, _ = load_wave(2.0, 50.0, reference_flow)
    for flow in FLOWS:
        t, pad, _ = load_wave(2.0, 50.0, flow)
        axes[0].plot(
            t,
            pad,
            color=COLORS[flow.flow_id],
            lw=2.8 if flow.flow_id in {"native_ibis", "native_ibis_fast"} else 2.1,
            ls="--" if flow.flow_id == "native_ibis_fast" else "-",
            label=flow.label,
        )
        if flow.flow_id != reference_flow.flow_id:
            ref = np.interp(t, reference_t, reference_y)
            axes[1].plot(
                t,
                (pad - ref) * 1e3,
                color=COLORS[flow.flow_id],
                lw=1.9,
                ls="--" if flow.flow_id == "native_ibis_fast" else "-",
                label=flow.label,
            )
    axes[0].set_ylabel("pad voltage (V)")
    axes[0].set_title("Baseline: 50 ohm || 2 pF, 1 ps input edges", loc="left", fontweight="bold")
    axes[0].legend(loc="upper center", ncol=2, fontsize=9)
    axes[1].axhline(0.0, color="#111111", lw=1.0)
    axes[1].set_ylabel("pad minus original-model transistor (mV)")
    axes[1].set_xlabel("time (ns)")
    for ax in axes:
        ax.set_xlim(4.5, 18.0)
        add_edge_lines(ax)
    fig.savefig(PLOTS / "01_baseline_model_card_supply_decomposition.png", dpi=180)
    plt.close(fig)


def plot_cap_sweep(rows: list[dict[str, object]]) -> None:
    cap_rows = [row for row in rows if float(row["r_load_ohm"]) == 50.0]
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2), constrained_layout=True)
    for flow in FLOWS:
        subset = sorted(
            [row for row in cap_rows if row["flow"] == flow.flow_id],
            key=lambda row: float(row["c_load_pf"]),
        )
        c = np.asarray([float(row["c_load_pf"]) for row in subset])
        d = np.asarray([float(row["rise_50_delay_ns"]) for row in subset])
        s = np.asarray([float(row["rise_10_90_ns"]) for row in subset])
        axes[0].plot(c, d, marker="o", color=COLORS[flow.flow_id], lw=2.0, label=flow.label)
        axes[1].plot(c, s, marker="o", color=COLORS[flow.flow_id], lw=2.0, label=flow.label)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xlabel("external load capacitance (pF)")
        ax.grid(True, which="both", alpha=0.22)
    axes[0].set_ylabel("input-to-pad 50% delay (ns)")
    axes[0].set_title("Delay versus capacitance", loc="left", fontweight="bold")
    axes[1].set_ylabel("pad 10%-90% rise time (ns)")
    axes[1].set_title("Slew versus capacitance", loc="left", fontweight="bold")
    axes[1].legend(loc="best", fontsize=8.5)
    fig.savefig(PLOTS / "02_capacitance_delay_and_slew.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.0), sharey=True, constrained_layout=True)
    for ax, c_pf in zip(axes, [0.001, 10.0]):
        for flow in FLOWS:
            t, pad, _ = load_wave(c_pf, 50.0, flow)
            ax.plot(t, pad, color=COLORS[flow.flow_id], lw=2.1, label=flow.label)
        ax.set_xlim(4.5, 12.0)
        ax.set_title(f"Cload = {c_pf:g} pF", loc="left", fontweight="bold")
        ax.set_xlabel("time (ns)")
        add_edge_lines(ax)
    axes[0].set_ylabel("pad voltage (V)")
    axes[1].legend(loc="lower right", fontsize=8.2)
    fig.savefig(PLOTS / "03_capacitance_endpoint_waveforms.png", dpi=180)
    plt.close(fig)


def plot_strength(rows: list[dict[str, object]]) -> None:
    load_rows = [row for row in rows if float(row["c_load_pf"]) == 2.0]
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2), constrained_layout=True)
    markers = {
        "native_ibis": "o",
        "native_ibis_fast": "s",
        "transistor_original_ideal": "x",
        "transistor_original_fixture": "^",
        "transistor_modified_fixture": "D",
    }
    for flow in FLOWS:
        subset = sorted(
            [row for row in load_rows if row["flow"] == flow.flow_id],
            key=lambda row: float(row["r_load_ohm"]),
        )
        r = np.asarray([float(row["r_load_ohm"]) for row in subset])
        vh = np.asarray([float(row["v_high_v"]) for row in subset])
        current = np.asarray([float(row["load_current_high_ma"]) for row in subset])
        axes[0].plot(
            r,
            vh,
            marker=markers[flow.flow_id],
            ms=8,
            markerfacecolor="white" if flow.flow_id in {"native_ibis", "native_ibis_fast"} else None,
            markeredgewidth=1.8,
            color=COLORS[flow.flow_id],
            lw=2.0,
            label=flow.label,
        )
        axes[1].plot(
            vh,
            current,
            marker=markers[flow.flow_id],
            ms=8,
            markerfacecolor="white" if flow.flow_id in {"native_ibis", "native_ibis_fast"} else None,
            markeredgewidth=1.8,
            color=COLORS[flow.flow_id],
            lw=2.0,
            label=flow.label,
        )
    axes[0].set_xscale("log")
    axes[0].set_xlabel("resistive load to ground (ohm)")
    axes[0].set_ylabel("settled high pad voltage (V)")
    axes[0].set_title("Loaded high level", loc="left", fontweight="bold")
    axes[1].set_xlabel("settled high pad voltage (V)")
    axes[1].set_ylabel("load current (mA)")
    axes[1].set_title("Pullup drive curve", loc="left", fontweight="bold")
    for ax in axes:
        ax.grid(True, which="both", alpha=0.22)
    axes[1].legend(loc="best", fontsize=8.3)
    fig.savefig(PLOTS / "04_driver_strength_load_sweep.png", dpi=180)
    plt.close(fig)


def plot_internal_timing() -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12.8, 7.4), sharex=True, constrained_layout=True)
    old_native_flow = next(flow for flow in FLOWS if flow.flow_id == "native_ibis")
    fast_native_flow = next(flow for flow in FLOWS if flow.flow_id == "native_ibis_fast")
    transistor_flow = next(flow for flow in FLOWS if flow.flow_id == "transistor_original_ideal")
    t, pad, native = load_wave(2.0, 50.0, old_native_flow)
    ku = signal(native, "v(ku)")
    kd = signal(native, "v(kd)")
    assert ku is not None and kd is not None
    tf, padf, fast_native = load_wave(2.0, 50.0, fast_native_flow)
    kuf = signal(fast_native, "v(ku)")
    kdf = signal(fast_native, "v(kd)")
    assert kuf is not None and kdf is not None
    axes[0].plot(t, ku, color="#d62728", lw=2.1, label="old IBIS Ku")
    axes[0].plot(t, kd, color="#1f77b4", lw=2.1, label="old IBIS Kd")
    axes[0].plot(tf, kuf, color="#d62728", lw=1.8, ls="--", label="5 ps IBIS Ku")
    axes[0].plot(tf, kdf, color="#1f77b4", lw=1.8, ls="--", label="5 ps IBIS Kd")
    axes[0].plot(t, pad / max(np.max(pad), 1e-12), color="#111111", lw=1.7, label="old IBIS pad")
    axes[0].plot(tf, padf / max(np.max(padf), 1e-12), color="#009688", lw=1.7, label="5 ps IBIS pad")
    axes[0].set_ylabel("normalized value")
    axes[0].set_title("Native IBIS switching variables", loc="left", fontweight="bold")
    axes[0].legend(loc="best")

    t2, pad2, transistor = load_wave(2.0, 50.0, transistor_flow)
    n2 = signal(transistor, "v(xbuf.n2)")
    n3 = signal(transistor, "v(xbuf.n3)")
    assert n2 is not None and n3 is not None
    axes[1].plot(t2, 1.0 - n2 / VDD, color="#d62728", lw=2.3, label="pullup gate enable, 1 - n2/VDD")
    axes[1].plot(t2, n3 / VDD, color="#1f77b4", lw=2.3, label="pulldown gate enable, n3/VDD")
    axes[1].plot(t2, pad2 / max(np.max(pad2), 1e-12), color="#111111", lw=1.8, label="transistor pad, normalized")
    axes[1].set_ylabel("normalized value")
    axes[1].set_xlabel("time (ns)")
    axes[1].set_title("Direct transistor internal output-stage controls", loc="left", fontweight="bold")
    axes[1].legend(loc="best")
    for ax in axes:
        ax.set_xlim(4.5, 10.0)
        add_edge_lines(ax)
    fig.savefig(PLOTS / "05_internal_switching_timing.png", dpi=180)
    plt.close(fig)


def plot_stored_vt_source_check() -> dict[str, float]:
    old_t, old_v = first_ibis_waveform(IBIS, "Rising Waveform")
    fast_t, fast_v = first_ibis_waveform(FAST_IBIS, "Rising Waveform")
    direct = parse_hspice_tr0(CHARACTERIZATION_T0_TR0)
    direct_t = np.asarray(direct["time"], dtype=float) * 1e9
    direct_v = signal(direct, "v(pad)")
    if direct_v is None:
        raise KeyError(f"pad not found in {CHARACTERIZATION_T0_TR0}")

    traces = [
        ("Old slow-edge IBIS stored V-T table", old_t, old_v, "#111111", 2.7),
        ("Regenerated 5 ps IBIS stored V-T table", fast_t, fast_v, "#009688", 2.5),
        ("Direct transistor, original model, 5 ps input", direct_t, direct_v, "#d62728", 2.0),
    ]
    times: dict[str, float] = {}
    fig, ax = plt.subplots(figsize=(11.2, 5.8), constrained_layout=True)
    for label, t_ns, voltage, color, width in traces:
        final = float(np.median(voltage[t_ns >= min(5.5, float(np.max(t_ns)) - 0.2)]))
        t50 = crossing(t_ns, voltage, 0.5 * final, 0.0, 6.0, True, "last")
        times[label] = t50
        ax.plot(t_ns, voltage, color=color, lw=width, label=label)
        ax.axvline(t50, color=color, ls="--", lw=1.2, alpha=0.8)
        ax.text(
            t50 + 0.035,
            0.5 * final,
            f"{t50:.3f} ns",
            color=color,
            fontsize=9,
            va="bottom",
        )
    ax.set_xlim(0.0, 4.5)
    ax.set_ylim(-0.08, 1.68)
    ax.set_xlabel("time from characterization edge (ns)")
    ax.set_ylabel("50 ohm fixture voltage (V)")
    ax.set_title(
        "Stored IBIS V-T timing versus its transistor characterization source",
        loc="left",
        fontweight="bold",
    )
    ax.grid(True, alpha=0.22)
    ax.legend(loc="lower right", fontsize=9)
    fig.savefig(PLOTS / "06_stored_vt_table_vs_source_transistor.png", dpi=180)
    plt.close(fig)
    return {
        "old_ibis_vt_rise_50_ns": times["Old slow-edge IBIS stored V-T table"],
        "fast_ibis_vt_rise_50_ns": times["Regenerated 5 ps IBIS stored V-T table"],
        "direct_transistor_vt_rise_50_ns": times[
            "Direct transistor, original model, 5 ps input"
        ],
    }


def delay_fits(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    cap_rows = [row for row in rows if float(row["r_load_ohm"]) == 50.0]
    for flow in FLOWS:
        subset = sorted(
            [row for row in cap_rows if row["flow"] == flow.flow_id],
            key=lambda row: float(row["c_load_pf"]),
        )
        x = np.asarray([float(row["c_load_pf"]) for row in subset])
        y = np.asarray([float(row["rise_50_delay_ns"]) for row in subset])
        low_cap = x <= 2.0
        slope, intercept = np.polyfit(x[low_cap], y[low_cap], 1)
        predicted = intercept + slope * x[low_cap]
        result.append(
            {
                "flow": flow.flow_id,
                "flow_label": flow.label,
                "fit_range_pf": "<=2",
                "delay_intercept_ns": float(intercept),
                "delay_slope_ns_per_pf": float(slope),
                "fit_rmse_ps": float(np.sqrt(np.mean((predicted - y[low_cap]) ** 2)) * 1e3),
            }
        )
    return result


def lookup(
    rows: list[dict[str, object]],
    flow: str,
    field: str,
    c_pf: float = 2.0,
    r_ohm: float = 50.0,
) -> float:
    for row in rows:
        if (
            row["flow"] == flow
            and float(row["c_load_pf"]) == c_pf
            and float(row["r_load_ohm"]) == r_ohm
        ):
            return float(row[field])
    return float("nan")


def write_readme(
    rows: list[dict[str, object]],
    fits: list[dict[str, object]],
    vt_check: dict[str, float],
) -> None:
    fit_by_flow = {row["flow"]: row for row in fits}
    native_delay = lookup(rows, "native_ibis", "rise_50_delay_ns")
    fast_native_delay = lookup(rows, "native_ibis_fast", "rise_50_delay_ns")
    original_ideal_delay = lookup(rows, "transistor_original_ideal", "rise_50_delay_ns")
    original_fixture_delay = lookup(rows, "transistor_original_fixture", "rise_50_delay_ns")
    modified_delay = lookup(rows, "transistor_modified_fixture", "rise_50_delay_ns")
    native_vh = lookup(rows, "native_ibis", "v_high_v")
    fast_native_vh = lookup(rows, "native_ibis_fast", "v_high_v")
    original_vh = lookup(rows, "transistor_original_ideal", "v_high_v")
    modified_vh = lookup(rows, "transistor_modified_fixture", "v_high_v")
    native_r = lookup(rows, "native_ibis", "effective_pullup_r_ohm")
    fast_native_r = lookup(rows, "native_ibis_fast", "effective_pullup_r_ohm")
    original_r = lookup(rows, "transistor_original_ideal", "effective_pullup_r_ohm")
    modified_r = lookup(rows, "transistor_modified_fixture", "effective_pullup_r_ohm")
    supply_effect_ps = (original_fixture_delay - original_ideal_delay) * 1e3
    model_effect_ps = (modified_delay - original_fixture_delay) * 1e3
    correct_gap_ps = (native_delay - original_ideal_delay) * 1e3
    fast_correct_gap_ps = (fast_native_delay - original_ideal_delay) * 1e3
    previous_gap_ps = (native_delay - modified_delay) * 1e3
    native_fit = fit_by_flow["native_ibis"]
    fast_native_fit = fit_by_flow["native_ibis_fast"]
    original_fit = fit_by_flow["transistor_original_ideal"]
    slope_gap = (
        float(native_fit["delay_slope_ns_per_pf"])
        - float(original_fit["delay_slope_ns_per_pf"])
    )
    fast_slope_gap = (
        float(fast_native_fit["delay_slope_ns_per_pf"])
        - float(original_fit["delay_slope_ns_per_pf"])
    )
    fast_fall_gap_ps = (
        lookup(rows, "native_ibis_fast", "fall_50_delay_ns")
        - lookup(rows, "transistor_original_ideal", "fall_50_delay_ns")
    ) * 1e3
    text = f"""# io_buf HSPICE Capacitance and Driver-Strength Investigation

## What Was Tested

- Long 1 ps-edge pulse, 3.3 V supply.
- External capacitance: `1 fF` through `10 pF`, with a `50 ohm` load.
- Resistive load: `25`, `50`, `100`, `200`, and `1000 ohm`, with `2 pF`.
- HSPICE native IBIS.
- HSPICE native IBIS using the regenerated 5 ps-characterization file.
- Direct transistor `io_buf.sp` using the original HSPICE model card used to generate the IBIS file.
- The same transistor with the existing 1 ohm supply fixture.
- The previous transistor reference using the ngspice-modified MOS model card.

## Baseline Finding: 50 ohm || 2 pF

- Old slow-file native-IBIS 50% rise delay: `{native_delay:.4f} ns`.
- Regenerated 5 ps-file native-IBIS 50% rise delay: `{fast_native_delay:.4f} ns`.
- Direct transistor, original model and ideal supply: `{original_ideal_delay:.4f} ns`.
- Previous transistor reference: `{modified_delay:.4f} ns`.
- Old-file native-versus-correct-transistor delay gap: `{correct_gap_ps:.1f} ps`.
- Regenerated-file native-versus-correct-transistor delay gap: `{fast_correct_gap_ps:.1f} ps`.
- Previous gap: `{previous_gap_ps:.1f} ps`.
- The 1 ohm supply fixture changes 50% delay by only `{supply_effect_ps:+.1f} ps`.
- Changing from the original MOS card to the ngspice-modified card changes it by `{model_effect_ps:+.1f} ps`.

Two stale-reference effects were present. The previous HSPICE transistor reference used a MOS card modified for ngspice numerical behavior, and the short-pulse studies selected `hspice/sparam/io_buf.ibs`, which is the old slow-edge IBIS file. The original HSPICE MOS card and the regenerated 5 ps IBIS file are the appropriate pair for this audit.

## Direct Stored-Table Source Check

- Old IBIS first rising V-T table 50% time: `{vt_check['old_ibis_vt_rise_50_ns']:.4f} ns`.
- Regenerated 5 ps IBIS first rising V-T table 50% time: `{vt_check['fast_ibis_vt_rise_50_ns']:.4f} ns`.
- Cached direct transistor characterization, original model and 5 ps input: `{vt_check['direct_transistor_vt_rise_50_ns']:.4f} ns`.

The regenerated stored table and its direct transistor source agree within `{abs(vt_check['fast_ibis_vt_rise_50_ns'] - vt_check['direct_transistor_vt_rise_50_ns']) * 1e3:.1f} ps`. The old file stores the slower response directly; this is not a transient initialization artifact.

## Driver Strength

At 50 ohm:

- Native IBIS settled high: `{native_vh:.4f} V`; effective pullup resistance: `{native_r:.2f} ohm`.
- Regenerated native IBIS settled high: `{fast_native_vh:.4f} V`; effective pullup resistance: `{fast_native_r:.2f} ohm`.
- Original-model transistor settled high: `{original_vh:.4f} V`; effective pullup resistance: `{original_r:.2f} ohm`.
- Previous modified-model transistor settled high: `{modified_vh:.4f} V`; effective pullup resistance: `{modified_r:.2f} ohm`.

The load sweep in `plots/04_driver_strength_load_sweep.png` shows the nonlinear pullup drive curve directly. Static strength and dynamic delay are separate checks.

## Capacitance Diagnosis

For external capacitance up to 2 pF, the fitted 50% delay laws are:

- Native IBIS: `{float(native_fit['delay_intercept_ns']):.4f} ns + {float(native_fit['delay_slope_ns_per_pf']):.4f} ns/pF * Cload`.
- Regenerated 5 ps native IBIS: `{float(fast_native_fit['delay_intercept_ns']):.4f} ns + {float(fast_native_fit['delay_slope_ns_per_pf']):.4f} ns/pF * Cload`.
- Original-model transistor: `{float(original_fit['delay_intercept_ns']):.4f} ns + {float(original_fit['delay_slope_ns_per_pf']):.4f} ns/pF * Cload`.
- Difference in capacitance slope: `{slope_gap:+.4f} ns/pF`.
- Regenerated-file difference in capacitance slope: `{fast_slope_gap:+.4f} ns/pF`.

The regenerated-file and correct-transistor capacitance slopes differ by only `{abs(fast_slope_gap):.4f} ns/pF`. Capacitance therefore does not explain the unusual waveform; it exposes the same nearly constant timing offset already stored in the old IBIS V-T tables.

Remember that the IBIS model already contains `C_comp = 1.2 pF`. The sweep values are external capacitance added to both models; `1 fF` is the practical near-zero external-load point.

## Conclusion

- The unusual HSPICE comparison was primarily a reference-selection problem: an old slow-characterized IBIS file was compared with a transistor deck using a different, modified MOS card.
- With the regenerated 5 ps IBIS and the original HSPICE MOS card, the 50 ohm || 2 pF rise and fall gaps are only `{fast_correct_gap_ps:.1f} ps` and `{fast_fall_gap_ps:.1f} ps`.
- Static pullup strength also agrees: `{fast_native_r:.2f} ohm` effective IBIS output resistance versus `{original_r:.2f} ohm` for the source transistor.
- External capacitance from 1 fF to 10 pF behaves consistently in the regenerated IBIS and source transistor; it is not the root cause.
- Earlier short-pulse results remain valid measurements of the old file's playback behavior, but the core short-pulse baseline must be repeated with the regenerated 5 ps IBIS before drawing production conclusions.

## Figures

- `plots/01_baseline_model_card_supply_decomposition.png`
- `plots/02_capacitance_delay_and_slew.png`
- `plots/03_capacitance_endpoint_waveforms.png`
- `plots/04_driver_strength_load_sweep.png`
- `plots/05_internal_switching_timing.png`
- `plots/06_stored_vt_table_vs_source_transistor.png`

## Data

- `metrics.csv`: every flow/capacitance/load measurement.
- `delay_fit_summary.csv`: low-capacitance delay intercept and slope.
- Every run keeps its `.sp`, `.tr0`, `.lis`, and stdout log under `runs/`.
"""
    (OUT / "README.md").write_text(text, encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--timeout-s", type=int, default=180)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args()

    for path in [IBIS, FAST_IBIS, IO_BUF_SP, ORIGINAL_MODEL, MODIFIED_MODEL, args.hspice]:
        if not path.exists():
            raise FileNotFoundError(path)
    ensure_dir(OUT)
    ensure_dir(RUNS)
    ensure_dir(PLOTS)

    combinations = {(c_pf, 50.0) for c_pf in [0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]}
    combinations.update({(2.0, r_ohm) for r_ohm in [25.0, 50.0, 100.0, 200.0, 1000.0]})

    rows: list[dict[str, object]] = []
    total = len(combinations) * len(FLOWS)
    index = 0
    for c_pf, r_ohm in sorted(combinations):
        for flow in FLOWS:
            index += 1
            print(
                f"[{index}/{total}] {flow.flow_id}: C={c_pf:g} pF, R={r_ohm:g} ohm",
                flush=True,
            )
            tr0 = run_hspice(
                flow,
                c_pf,
                r_ohm,
                args.hspice,
                args.timeout_s,
                args.rerun,
            )
            rows.append(measure(flow, c_pf, r_ohm, parse_hspice_tr0(tr0)))

    rows.sort(key=lambda row: (float(row["c_load_pf"]), float(row["r_load_ohm"]), str(row["flow"])))
    write_csv(OUT / "metrics.csv", rows)
    fits = delay_fits(rows)
    write_csv(OUT / "delay_fit_summary.csv", fits)
    plot_baseline()
    plot_cap_sweep(rows)
    plot_strength(rows)
    plot_internal_timing()
    vt_check = plot_stored_vt_source_check()
    write_csv(OUT / "stored_vt_source_check.csv", [vt_check])
    write_readme(rows, fits, vt_check)
    print(OUT)


if __name__ == "__main__":
    main()
