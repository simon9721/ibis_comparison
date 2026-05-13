"""Run the clean edge-family stress points across refspice/pybis flows.

This follows the ngspice refspice stress screen and ports the two useful
2 ns / 30 cm cases to:

- ngspice + io_buf.sp
- ngspice + pybis
- Xyce + io_buf.sp
- Xyce + pybis edge15_flat4p2
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import (  # noqa: E402
    build_eye,
    estimate_signal_levels,
    load_waveform,
    plot_eye_overlay,
    resolve_signal_key,
    sanitize_waveform,
)


NGSPICE = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")
XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")
OUT_DIR = ROOT / "results" / "edge_family_stress_crossflow_2026-05-11"

VLO = 0.0
VHI = 3.3
TR = 200e-12
N_BITS = 200
SKIP_UI = 10
STIMULUS_NAME = "PRBS7"
STIMULUS_STATES: list[int] | None = None
XYCE_PYBIS_MODEL_FILE = "driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub"
XYCE_PYBIS_MODEL_LABEL = "edge15_flat4p2"

R_BASE = 0.05
L_BASE = 3.46e-9
C_BASE = 1.384e-12
G_BASE = 1e-6
TD_SECTION = math.sqrt(L_BASE * C_BASE)


@dataclass(frozen=True)
class StressCase:
    key: str
    ui_s: float
    length_scale: int
    loss_scale: float
    note: str
    n_sections_override: int | None = None

    @property
    def n_sections(self) -> int:
        return self.n_sections_override or 10 * self.length_scale

    @property
    def section_length_scale(self) -> float:
        return 10.0 * self.length_scale / self.n_sections

    @property
    def stop_s(self) -> float:
        return N_BITS * self.ui_s

    @property
    def channel_delay_s(self) -> float:
        return self.n_sections * self.section_length_scale * TD_SECTION


@dataclass(frozen=True)
class Flow:
    key: str
    simulator: str
    model: str
    fmt: str
    plot_color: str


CASES = [
    StressCase("ui2_len30cm_loss1", 2e-9, 3, 1.0, "2 ns UI, 30 cm channel"),
    StressCase("ui2_len30cm_loss5", 2e-9, 3, 5.0, "2 ns UI, 30 cm channel, R/G loss x5"),
]

DEFAULT_CASES = CASES
COARSE_CASES = [
    StressCase(
        "ui2_len30cm_loss5_coarse10",
        2e-9,
        3,
        5.0,
        "2 ns UI, 30 cm channel, R/G loss x5, 10 coarse sections",
        n_sections_override=10,
    )
]
CONTEXT_STATES = [int(ch) for ch in "00001001101011110000000100110101111000"]


def make_flows() -> list[Flow]:
    return [
        Flow("ngspice_refspice", "ngspice", "io_buf.sp", "ngspice", "#1f77b4"),
        Flow("ngspice_pybis", "ngspice", "pybis", "ngspice", "#ff7f0e"),
        Flow("xyce_refspice", "Xyce", "io_buf.sp", "xyce", "#2ca02c"),
        Flow("xyce_pybis", "Xyce", f"pybis {XYCE_PYBIS_MODEL_LABEL}", "xyce", "#d62728"),
    ]


FLOWS = make_flows()


def rel_include(path: Path, cwd: Path) -> str:
    return Path(os.path.relpath(path.resolve(), cwd.resolve())).as_posix()


def prbs7(n_bits: int) -> list[int]:
    reg = [1] * 7
    bits = []
    for _ in range(n_bits):
        bit = reg[6] ^ reg[5]
        bits.append(reg[6])
        reg = [bit] + reg[:6]
    return bits


def stimulus_states() -> list[int]:
    if STIMULUS_STATES is not None:
        return list(STIMULUS_STATES)
    return [0 if bit == 1 else 1 for bit in prbs7(N_BITS)]


def prbs_rows(ui_s: float) -> list[tuple[float, float]]:
    states = stimulus_states()
    rows: list[tuple[float, float]] = []
    v_prev = VHI if states[0] else VLO
    rows.append((0.0, v_prev))
    for i, state in enumerate(states):
        v_next = VHI if state else VLO
        t_start = i * ui_s
        if v_next != v_prev:
            if rows[-1][0] < t_start - 1e-15:
                rows.append((t_start, v_prev))
            rows.append((t_start + TR, v_next))
        else:
            if rows[-1][0] < t_start - 1e-15:
                rows.append((t_start, v_prev))
        v_prev = v_next
    t_final = N_BITS * ui_s
    if rows[-1][0] < t_final - 1e-15:
        rows.append((t_final, v_prev))
    return rows


def format_pwl(rows: list[tuple[float, float]], node: str) -> str:
    lines = [
        f"* Inline {STIMULUS_NAME} V-source PWL stimulus",
        f"* {N_BITS} bits, UI={rows[-1][0] / N_BITS * 1e9:.3f} ns, tr/tf={TR * 1e12:.0f} ps",
    ]
    t0, v0 = rows[0]
    lines.append(f"Vstim  {node}  0  PWL({t0:.9e} {v0:.4f}")
    for i, (t_val, v_val) in enumerate(rows[1:], 1):
        suffix = ")" if i == len(rows) - 1 else ""
        lines.append(f"+ {t_val:.9e}  {v_val:.4f}{suffix}")
    return "\n".join(lines)


def format_channel(case: StressCase, simulator: str) -> str:
    sec_scale = case.section_length_scale
    r_sec = R_BASE * sec_scale * case.loss_scale
    l_sec = L_BASE * sec_scale
    c_sec = C_BASE * sec_scale
    g_sec = G_BASE * sec_scale * case.loss_scale
    lines = [
        f"* Generated {case.n_sections}-section RLGC ladder for {simulator}",
        f"* length_scale={case.length_scale}, loss_scale={case.loss_scale:g}",
        f"* section_length_scale={sec_scale:g} cm-equivalent sections",
        f"* nominal one-way delay={case.channel_delay_s * 1e9:.3f} ns",
    ]
    left = "tx_out"
    for i in range(1, case.n_sections + 1):
        a = f"s{i}a"
        b = "n10b" if i == case.n_sections else f"s{i}b"
        lines.extend(
            [
                f"RCH{i:<3d} {left:<8s} {a:<8s} {r_sec:.9g}",
                f"LCH{i:<3d} {a:<8s} {b:<8s} {l_sec:.9e}",
                f"CCH{i:<3d} {b:<8s} 0        {c_sec:.9e}",
            ]
        )
        if simulator == "ngspice":
            lines.append(f"GCH{i:<3d} {b:<8s} 0        value={{{g_sec:.9e}*v({b},0)}}")
        else:
            lines.append(f"RGCH{i:<3d} {b:<8s} 0        {1.0 / g_sec:.9g}")
        left = b
    return "\n".join(lines)


def make_deck(case: StressCase, flow: Flow, cwd: Path) -> tuple[str, str]:
    step_s = min(10e-12, case.ui_s / 100.0)
    stop = f"{case.stop_s:.9e}"
    step = f"{step_s:.9e}"

    if flow.key == "ngspice_refspice":
        text = f"""* {case.key} / {flow.key}
.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10
{format_pwl(prbs_rows(case.ui_s), "in_src")}
Rin    in_src  in_dig  1

Vdd_ref  vdd_ref_src  0  DC 3.3
Voe_ref  oe_ref_src   0  DC 3.3
Rvdd_ref vdd_ref_src  vdd_ref  1
Roe_ref  oe_ref_src   oe_ref   1
Cdec_ref vdd_ref      0        10p

.subckt SPICE_BUF in oe out in_sense vdd vss
.include '{rel_include(ROOT / "models" / "hspice_ngspice.mod", cwd)}'
.include '{rel_include(ROOT / "models" / "io_buf.sp", cwd)}'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF
RCH_TX  pad_ref tx_out 1u
{format_channel(case, "ngspice")}
RTERM   n10b 0 50

.save V(in_dig) V(pad_ref) V(tx_out) V(n10b) V(in_sense_ref)
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran {step} {stop} uic
.end
"""
        return text, f"{case.key}_{flow.key}.raw"

    if flow.key == "ngspice_pybis":
        text = f"""* {case.key} / {flow.key}
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7
{format_pwl(prbs_rows(case.ui_s), "in_dig")}
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include '{rel_include(ROOT / "ngspice_pybis" / "driver_OutputInput_Typical.sub", cwd)}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
RCH_TX  pad tx_out 1u
{format_channel(case, "ngspice")}
RTERM   n10b 0 50

.save V(in_dig) V(pad) V(tx_out) V(n10b)
.tran {step} {stop}
.end
"""
        return text, f"{case.key}_{flow.key}.raw"

    if flow.key == "xyce_refspice":
        text = f"""* {case.key} / {flow.key}
{format_pwl(prbs_rows(case.ui_s), "in_src")}
Rin    in_src  in_dig  1

Vdd_ref  vdd_ref_src  0  DC 3.3
Voe_ref  oe_ref_src   0  DC 3.3
Rvdd_ref vdd_ref_src  vdd_ref  1
Roe_ref  oe_ref_src   oe_ref   1
Cdec_ref vdd_ref      0        10p

.subckt SPICE_BUF in oe out in_sense vdd vss
.include '{rel_include(ROOT / "models" / "hspice_ngspice.mod", cwd)}'
.include '{rel_include(ROOT / "models" / "io_buf.sp", cwd)}'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF
RCH_TX  pad_ref tx_out 1u
{format_channel(case, "xyce")}
RTERM   n10b 0 50

.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.options output initial_interval=10p
.tran {step} {stop} uic
.print tran format=csv time V(in_dig) V(pad_ref) V(tx_out) V(n10b) V(in_sense_ref)
.end
"""
        return text, f"{case.key}_{flow.key}.cir.csv"

    if flow.key == "xyce_pybis":
        text = f"""* {case.key} / {flow.key}
{format_pwl(prbs_rows(case.ui_s), "in_dig")}
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3

.include '{rel_include(ROOT / "xyce_pybis" / XYCE_PYBIS_MODEL_FILE, cwd)}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
RCH_TX  pad tx_out 1u
{format_channel(case, "xyce")}
RTERM   n10b 0 50

.ic V(pad)=0 V(tx_out)=0 V(n10b)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
* Gear avoids Xyce trap timestep collapse in the pybis B-source/T-line latch
* while preserving the same 10 ps output grid and original nonlinear limits.
.options timeint method=gear maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
.options output initial_interval=10p
.tran {step} {stop} uic
.print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
.end
"""
        return text, f"{case.key}_{flow.key}.cir.csv"

    raise ValueError(flow.key)


def run_flow(case: StressCase, flow: Flow, timeout_s: float = 240.0) -> dict[str, object]:
    flow_dir = OUT_DIR / "runs" / case.key / flow.key
    flow_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".sp" if flow.simulator == "ngspice" else ".cir"
    deck = flow_dir / f"{case.key}_{flow.key}{suffix}"
    deck_text, output_name = make_deck(case, flow, flow_dir)
    deck.write_text(deck_text, encoding="ascii")
    output = flow_dir / output_name
    output.unlink(missing_ok=True)
    log = flow_dir / f"{case.key}_{flow.key}.log"

    if flow.simulator == "ngspice":
        cmd = [str(NGSPICE), "-b", "-r", output.name, deck.name]
    else:
        cmd = [str(XYCE), deck.name]

    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=flow_dir,
            timeout=timeout_s,
            capture_output=True,
            text=True,
        )
        timed_out = False
        return_code: int | str = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = "timeout"
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    wall_s = time.time() - started
    log.write_text(
        "COMMAND: " + " ".join(cmd) + "\n"
        f"CASE: {case.key}\nFLOW: {flow.key}\n"
        f"RETURN_CODE: {return_code}\nTIMED_OUT: {timed_out}\n"
        f"WALL_SECONDS: {wall_s:.3f}\n\n"
        "STDOUT:\n" + stdout + "\n\nSTDERR:\n" + stderr,
        encoding="utf-8",
    )

    return {
        "case": case.key,
        "flow": flow.key,
        "simulator": flow.simulator,
        "model": flow.model,
        "return_code": return_code,
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(deck.relative_to(ROOT)).replace("\\", "/"),
        "output": str(output.relative_to(ROOT)).replace("\\", "/"),
        "log": str(log.relative_to(ROOT)).replace("\\", "/"),
        "output_exists": output.exists(),
    }


def crossing_events(time: np.ndarray, voltage: np.ndarray, level: float, ui_s: float):
    above = voltage >= level
    idx = np.where(above[:-1] != above[1:])[0]
    events = []
    last_t = -math.inf
    for i in idx:
        t0, t1 = time[i], time[i + 1]
        v0, v1 = voltage[i], voltage[i + 1]
        if v1 == v0:
            continue
        tc = t0 + (level - v0) * (t1 - t0) / (v1 - v0)
        if tc < time[0] + SKIP_UI * ui_s:
            continue
        if tc - last_t < 0.45 * ui_s:
            continue
        events.append((float(tc), "rise" if v1 > v0 else "fall"))
        last_t = float(tc)
    return events


def first_crossing(time, voltage, level, start, stop, direction) -> float:
    mask = (time >= start) & (time <= stop)
    t = time[mask]
    v = voltage[mask]
    if len(t) < 2:
        return float("nan")
    above = v >= level
    if direction == "rise":
        idx = np.where((~above[:-1]) & above[1:])[0]
    else:
        idx = np.where(above[:-1] & (~above[1:]))[0]
    if len(idx) == 0:
        return float("nan")
    i = idx[0]
    if v[i + 1] == v[i]:
        return float("nan")
    return float(t[i] + (level - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i]))


def bit_at(time, voltage, level, t) -> str:
    if t < time[0] or t > time[-1]:
        return "x"
    return "1" if np.interp(t, time, voltage) >= level else "0"


def context_for_event(time, voltage, level, event_t, ui_s) -> str:
    return (
        bit_at(time, voltage, level, event_t - 1.35 * ui_s)
        + bit_at(time, voltage, level, event_t - 0.35 * ui_s)
        + "->"
        + bit_at(time, voltage, level, event_t + 0.35 * ui_s)
        + bit_at(time, voltage, level, event_t + 1.35 * ui_s)
    )


def summarize(values):
    finite = np.asarray([v for v in values if math.isfinite(v)], dtype=float)
    if len(finite) == 0:
        return float("nan"), float("nan"), float("nan")
    return float(np.median(finite)), float(np.std(finite)), float(np.max(finite) - np.min(finite))


def analyze_output(case: StressCase, flow: Flow, output: Path):
    data = load_waveform(output, fmt=flow.fmt)
    t_in, v_in = sanitize_waveform(data["time"], data["v(in_dig)"])
    t_out, v_out = sanitize_waveform(data["time"], data[resolve_signal_key(data, "v(n10b)")])
    in_mid = 0.5 * (float(np.min(v_in)) + float(np.max(v_in)))
    levels = estimate_signal_levels(v_out)
    events = crossing_events(t_in, v_in, in_mid, case.ui_s)
    x_grid = np.linspace(-0.6 * case.ui_s, 1.4 * case.ui_s + case.channel_delay_s, 1600)

    event_rows = []
    traces = {"rise": [], "fall": []}
    contexts = {"rise": [], "fall": []}
    stop = max(5e-9, 2.5 * case.ui_s + case.channel_delay_s)
    for edge_idx, (event_t, direction) in enumerate(events):
        if event_t + x_grid[0] < t_out[0] or event_t + x_grid[-1] > t_out[-1]:
            continue
        t50 = first_crossing(t_out, v_out, levels["v_mid"], event_t, event_t + stop, direction)
        if direction == "rise":
            t20 = first_crossing(t_out, v_out, levels["v20"], event_t, event_t + stop, "rise")
            t80 = first_crossing(t_out, v_out, levels["v80"], event_t, event_t + stop, "rise")
            slew = t80 - t20 if math.isfinite(t20) and math.isfinite(t80) else float("nan")
        else:
            t80 = first_crossing(t_out, v_out, levels["v80"], event_t, event_t + stop, "fall")
            t20 = first_crossing(t_out, v_out, levels["v20"], event_t, event_t + stop, "fall")
            slew = t20 - t80 if math.isfinite(t20) and math.isfinite(t80) else float("nan")

        trace = np.interp(event_t + x_grid, t_out, v_out)
        context = context_for_event(t_in, v_in, in_mid, event_t, case.ui_s)
        traces[direction].append(trace)
        contexts[direction].append(context)
        event_rows.append(
            {
                "case": case.key,
                "flow": flow.key,
                "simulator": flow.simulator,
                "model": flow.model,
                "direction": direction,
                "edge_index": edge_idx,
                "context": context,
                "input_crossing_ns": event_t * 1e9,
                "output_50_delay_ps": (t50 - event_t) * 1e12 if math.isfinite(t50) else float("nan"),
                "slew_20_80_ps": slew * 1e12 if math.isfinite(slew) else float("nan"),
            }
        )

    summary_rows = []
    for direction in ("rise", "fall"):
        subset = [row for row in event_rows if row["direction"] == direction]
        if not subset:
            continue
        matrix = np.array(traces[direction])
        median_trace = np.median(matrix, axis=0)
        residual_mv = (matrix - median_trace) * 1e3
        delay_med, delay_std, delay_p2p = summarize([row["output_50_delay_ps"] for row in subset])
        slew_med, slew_std, slew_p2p = summarize([row["slew_20_80_ps"] for row in subset])
        summary_rows.append(
            {
                "case": case.key,
                "flow": flow.key,
                "simulator": flow.simulator,
                "model": flow.model,
                "direction": direction,
                "ui_ns": case.ui_s * 1e9,
                "length_cm": case.length_scale * 10,
                "loss_scale": case.loss_scale,
                "channel_delay_ui": case.channel_delay_s / case.ui_s,
                "t_end_ns": t_out[-1] * 1e9,
                "completed": bool(t_out[-1] >= case.stop_s - 1e-12),
                "edges": len(subset),
                "contexts": ";".join(sorted(set(contexts[direction]))),
                "delay_50_median_ps": delay_med,
                "delay_50_std_ps": delay_std,
                "delay_50_p2p_ps": delay_p2p,
                "delay_50_p2p_ui": delay_p2p / (case.ui_s * 1e12),
                "slew_20_80_median_ps": slew_med,
                "slew_20_80_std_ps": slew_std,
                "slew_20_80_p2p_ps": slew_p2p,
                "trace_residual_p95_mV": float(np.percentile(np.abs(residual_mv), 95)),
                "trace_residual_max_mV": float(np.max(np.abs(residual_mv))),
                "v_min": float(np.min(v_out)),
                "v_max": float(np.max(v_out)),
            }
        )

    plot_flow_edge_family(case, flow, x_grid, traces, contexts, summary_rows)
    plot_flow_eye(case, flow, t_out, v_out, levels)
    return event_rows, summary_rows, (t_out, v_out)


def plot_flow_edge_family(case, flow, x_grid, traces, contexts, summary_rows):
    fig, axes = plt.subplots(2, 2, figsize=(13, 7.5), sharex=True)
    colors = {
        "00->10": "#1f77b4",
        "10->11": "#17becf",
        "10->10": "#4c78a8",
        "00->11": "#72b7b2",
        "01->00": "#ff7f0e",
        "11->01": "#d62728",
        "11->00": "#f58518",
        "01->01": "#e45756",
    }
    for col, direction in enumerate(("rise", "fall")):
        ax = axes[0, col]
        ax_res = axes[1, col]
        matrix = np.array(traces[direction])
        if matrix.size == 0:
            ax.set_title(f"{direction}: no edges")
            continue
        median_trace = np.median(matrix, axis=0)
        seen = set()
        for trace, context in zip(matrix, contexts[direction]):
            label = context if context not in seen else None
            seen.add(context)
            color = colors.get(context, "#777777")
            ax.plot(x_grid * 1e9, trace, color=color, alpha=0.32, lw=0.7, label=label)
            ax_res.plot(x_grid * 1e9, (trace - median_trace) * 1e3, color=color, alpha=0.28, lw=0.65)
        ax.plot(x_grid * 1e9, median_trace, color="#111111", lw=2.0, label="median")
        matching = [row for row in summary_rows if row["direction"] == direction]
        extra = ""
        if matching:
            row = matching[0]
            extra = (
                f"delay p2p={row['delay_50_p2p_ps']:.1f} ps, "
                f"slew p2p={row['slew_20_80_p2p_ps']:.1f} ps"
            )
        ax.set_title(f"{direction.capitalize()} family ({extra})")
        ax.set_ylabel("V(n10b) (V)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8, loc="best")
        ax_res.axhline(0.0, color="#111111", lw=1.0)
        ax_res.set_title(f"{direction.capitalize()} residuals vs median")
        ax_res.set_xlabel("Time from input 50% crossing (ns)")
        ax_res.set_ylabel("Residual (mV)")
        ax_res.grid(True, alpha=0.25)
    fig.suptitle(f"{case.key} / {flow.key}: receiver edge families", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT_DIR / "plots" / f"{case.key}_{flow.key}_edge_families.png", dpi=170)
    plt.close(fig)


def plot_flow_eye(case, flow, time, voltage, levels):
    t_eye, eye_slices = build_eye(
        time,
        voltage,
        case.ui_s,
        skip_ui=SKIP_UI,
        n_interp=2000,
        n_ui=2,
        phase_ui=0.0,
    )
    plot_eye_overlay(
        t_eye,
        eye_slices,
        title=f"{case.key} / {flow.key}: 2-UI eye",
        outfile=str(OUT_DIR / "plots" / f"{case.key}_{flow.key}_eye_overlay.png"),
        n_ui=2,
        levels=levels,
        max_traces=500,
    )


def plot_case_transient_overlays(case: StressCase, waveforms: dict[str, tuple[np.ndarray, np.ndarray]]):
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.0), sharey=True)
    windows = [(0.0, 80.0), (40.0, 60.0)]
    for ax, (x0, x1) in zip(axes, windows):
        for flow in FLOWS:
            if flow.key not in waveforms:
                continue
            time, voltage = waveforms[flow.key]
            t_ns = time * 1e9
            mask = (t_ns >= x0) & (t_ns <= x1)
            ax.plot(t_ns[mask], voltage[mask], color=flow.plot_color, lw=1.0, alpha=0.9, label=flow.key)
        ax.set_xlim(x0, x1)
        ax.set_ylabel("V(n10b) (V)")
        ax.set_title(f"{x0:.0f}-{x1:.0f} ns")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best", fontsize=8)
    axes[-1].set_xlabel("Time (ns)")
    fig.suptitle(f"{case.key}: receiver transient overlay", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT_DIR / "plots" / f"{case.key}_transient_overlay.png", dpi=170)
    plt.close(fig)


def plot_summary(summary_rows):
    for case in CASES:
        rows = [row for row in summary_rows if row["case"] == case.key]
        if not rows:
            continue
        labels = [f"{row['flow']}\n{row['direction']}" for row in rows]
        x = np.arange(len(labels))
        fig, axes = plt.subplots(3, 1, figsize=(13, 9.5), sharex=True)
        metrics = [
            ("delay_50_p2p_ui", "50% delay spread (UI)"),
            ("slew_20_80_p2p_ps", "20-80 slew spread (ps)"),
            ("trace_residual_p95_mV", "Trace residual p95 (mV)"),
        ]
        for ax, (key, ylabel) in zip(axes, metrics):
            ax.bar(x, [float(row[key]) for row in rows], color="#4c78a8")
            ax.set_ylabel(ylabel)
            ax.grid(axis="y", alpha=0.25)
        axes[-1].set_xticks(x)
        axes[-1].set_xticklabels(labels, rotation=25, ha="right")
        fig.suptitle(f"{case.key}: edge-family metric comparison", fontsize=13)
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        fig.savefig(OUT_DIR / "plots" / f"{case.key}_metrics_summary.png", dpi=170)
        plt.close(fig)


def write_csv(path: Path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_readme(run_rows, summary_rows):
    lines = [
        "# Cross-Flow Edge-Family Stress Comparison",
        "",
        "This ports the two clean ngspice-refspice stress points to pybis and Xyce.",
        "The goal is to see whether the more realistic eye/edge-family behavior is",
        "preserved across the comparison flows.",
        f"Stimulus: `{STIMULUS_NAME}`, {N_BITS} bits, skip {SKIP_UI} UI for edge metrics.",
        "Xyce pybis uses Gear order 1 time integration to avoid trap timestep collapse",
        "in the pybis B-source/T-line latch.",
        "",
        "Flows:",
        "",
        "- ngspice + transistor-level `io_buf.sp`",
        "- ngspice + pybis",
        "- Xyce + transistor-level `io_buf.sp`",
        f"- Xyce + pybis `{XYCE_PYBIS_MODEL_LABEL}`",
        "",
        "## Run Status",
        "",
        "| Case | Flow | Return | Timed out | Wall s | Output |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in run_rows:
        lines.append(
            "| {case} | {flow} | {return_code} | {timed_out} | {wall_s:.2f} | {output_exists} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Edge-Family Metrics",
            "",
            "| Case | Flow | Direction | Delay p2p | Delay p2p UI | Slew p2p | Residual p95 |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary_rows:
        lines.append(
            "| {case} | {flow} | {direction} | {delay_50_p2p_ps:.1f} ps | "
            "{delay_50_p2p_ui:.4f} UI | {slew_20_80_p2p_ps:.1f} ps | "
            "{trace_residual_p95_mV:.1f} mV |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `run_summary.csv`: command status",
            "- `stress_summary.csv`: aggregate edge-family metrics",
            "- `stress_events.csv`: per-edge measurements",
            "- `plots/*_eye_overlay.png`: 2-UI eye views",
            "- `plots/*_edge_families.png`: input-referenced edge-family overlays",
            "- `plots/*_transient_overlay.png`: transient overlays per stress case",
            "- `plots/*_metrics_summary.png`: compact metric comparison per stress case",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="ascii")


def reset_out_dir():
    resolved = OUT_DIR.resolve()
    expected_parent = (ROOT / "results").resolve()
    if resolved.parent != expected_parent:
        raise RuntimeError(f"Refusing to remove unexpected output dir: {resolved}")
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "plots").mkdir(parents=True, exist_ok=True)


def configure_suite(argv: list[str] | None = None) -> float:
    global CASES, OUT_DIR, N_BITS, SKIP_UI, STIMULUS_NAME, STIMULUS_STATES
    global XYCE_PYBIS_MODEL_FILE, XYCE_PYBIS_MODEL_LABEL, FLOWS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        choices=[
            "prbs200",
            "coarse10",
            "coarse10_context",
            "coarse10_edge50",
            "coarse10_edge60",
            "coarse10_tanh10",
            "coarse10_tanh15",
        ],
        default="prbs200",
        help="stress suite to run",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=None,
        help="per-simulation timeout in seconds",
    )
    parser.add_argument(
        "--n-bits",
        type=int,
        default=None,
        help="override PRBS bit count for non-context suites",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="write results to this directory; relative paths are resolved from repo root",
    )
    args = parser.parse_args(argv)

    def finish(timeout_s: float) -> float:
        global N_BITS, STIMULUS_NAME, OUT_DIR
        if args.n_bits is None:
            pass
        else:
            if STIMULUS_STATES is not None:
                raise ValueError("--n-bits is only valid for PRBS suites")
            old_bits = N_BITS
            N_BITS = args.n_bits
            STIMULUS_NAME = f"PRBS7-{N_BITS}"
            OUT_DIR = OUT_DIR.with_name(OUT_DIR.name.replace(f"_{old_bits}b_", f"_{N_BITS}b_"))
        if args.out_dir is not None:
            out_dir = args.out_dir
            if not out_dir.is_absolute():
                out_dir = ROOT / out_dir
            OUT_DIR = out_dir
        return timeout_s

    if args.suite == "coarse10":
        CASES = COARSE_CASES
        N_BITS = 80
        SKIP_UI = 10
        STIMULUS_NAME = "PRBS7-80"
        STIMULUS_STATES = None
        XYCE_PYBIS_MODEL_FILE = "driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub"
        XYCE_PYBIS_MODEL_LABEL = "edge15_flat4p2"
        FLOWS = make_flows()
        OUT_DIR = ROOT / "results" / "edge_family_stress_crossflow_coarse10_80b_2026-05-11"
        return finish(args.timeout_s or 700.0)
    if args.suite == "coarse10_edge50":
        CASES = COARSE_CASES
        N_BITS = 80
        SKIP_UI = 10
        STIMULUS_NAME = "PRBS7-80"
        STIMULUS_STATES = None
        XYCE_PYBIS_MODEL_FILE = "driver_OutputInput_Typical_xyce_relaxed92_edge50_tailflat4p2.sub"
        XYCE_PYBIS_MODEL_LABEL = "edge50_flat4p2"
        FLOWS = make_flows()
        OUT_DIR = ROOT / "results" / "edge_family_stress_crossflow_coarse10_80b_edge50_2026-05-11"
        return finish(args.timeout_s or 300.0)
    if args.suite == "coarse10_edge60":
        CASES = COARSE_CASES
        N_BITS = 80
        SKIP_UI = 10
        STIMULUS_NAME = "PRBS7-80"
        STIMULUS_STATES = None
        XYCE_PYBIS_MODEL_FILE = "driver_OutputInput_Typical_xyce_relaxed92_edge60_tailflat4p2.sub"
        XYCE_PYBIS_MODEL_LABEL = "edge60_flat4p2"
        FLOWS = make_flows()
        OUT_DIR = ROOT / "results" / "edge_family_stress_crossflow_coarse10_80b_edge60_2026-05-11"
        return finish(args.timeout_s or 300.0)
    if args.suite == "coarse10_tanh10":
        CASES = COARSE_CASES
        N_BITS = 80
        SKIP_UI = 10
        STIMULUS_NAME = "PRBS7-80"
        STIMULUS_STATES = None
        XYCE_PYBIS_MODEL_FILE = "driver_OutputInput_Typical_xyce_relaxed10.sub"
        XYCE_PYBIS_MODEL_LABEL = "tanh10"
        FLOWS = make_flows()
        OUT_DIR = ROOT / "results" / "edge_family_stress_crossflow_coarse10_80b_tanh10_2026-05-11"
        return finish(args.timeout_s or 300.0)
    if args.suite == "coarse10_tanh15":
        CASES = COARSE_CASES
        N_BITS = 80
        SKIP_UI = 10
        STIMULUS_NAME = "PRBS7-80"
        STIMULUS_STATES = None
        XYCE_PYBIS_MODEL_FILE = "driver_OutputInput_Typical_xyce_relaxed15.sub"
        XYCE_PYBIS_MODEL_LABEL = "tanh15"
        FLOWS = make_flows()
        OUT_DIR = ROOT / "results" / "edge_family_stress_crossflow_coarse10_80b_tanh15_2026-05-11"
        return finish(args.timeout_s or 300.0)
    if args.suite == "coarse10_context":
        CASES = COARSE_CASES
        N_BITS = len(CONTEXT_STATES)
        SKIP_UI = 2
        STIMULUS_NAME = "context38"
        STIMULUS_STATES = CONTEXT_STATES
        XYCE_PYBIS_MODEL_FILE = "driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub"
        XYCE_PYBIS_MODEL_LABEL = "edge15_flat4p2"
        FLOWS = make_flows()
        OUT_DIR = ROOT / "results" / "edge_family_stress_crossflow_coarse10_context38_2026-05-11"
        return finish(args.timeout_s or 500.0)
    else:
        CASES = DEFAULT_CASES
        N_BITS = 200
        SKIP_UI = 10
        STIMULUS_NAME = "PRBS7"
        STIMULUS_STATES = None
        XYCE_PYBIS_MODEL_FILE = "driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub"
        XYCE_PYBIS_MODEL_LABEL = "edge15_flat4p2"
        FLOWS = make_flows()
        OUT_DIR = ROOT / "results" / "edge_family_stress_crossflow_2026-05-11"
        return finish(args.timeout_s or 240.0)


def main(argv: list[str] | None = None) -> int:
    timeout_s = configure_suite(argv)
    if not NGSPICE.exists():
        raise FileNotFoundError(NGSPICE)
    if not XYCE.exists():
        raise FileNotFoundError(XYCE)
    reset_out_dir()
    run_rows = []
    all_events = []
    all_summary = []

    for case in CASES:
        waveforms = {}
        for flow in FLOWS:
            print(f"Running {case.key} / {flow.key}", flush=True)
            run_row = run_flow(case, flow, timeout_s=timeout_s)
            run_rows.append(run_row)
            if run_row["return_code"] == 0 and run_row["output_exists"]:
                output = ROOT / str(run_row["output"])
                try:
                    events, summary, waveform = analyze_output(case, flow, output)
                    all_events.extend(events)
                    all_summary.extend(summary)
                    waveforms[flow.key] = waveform
                except Exception as exc:  # keep failed analysis visible in run summary
                    run_row["analysis_error"] = str(exc)
                    print(f"  analysis failed for {case.key} / {flow.key}: {exc}", flush=True)
            else:
                print(f"  skipped analysis: rc={run_row['return_code']}", flush=True)
        plot_case_transient_overlays(case, waveforms)

    write_csv(OUT_DIR / "run_summary.csv", run_rows)
    write_csv(OUT_DIR / "stress_events.csv", all_events)
    write_csv(OUT_DIR / "stress_summary.csv", all_summary)
    plot_summary(all_summary)
    write_readme(run_rows, all_summary)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
