"""Run ngspice refspice stress cases that should expose edge-family spread.

The accepted 5 ns UI / 10 cm channel case is too gentle to show much
pattern-dependent edge timing. This runner keeps the same transistor-level
driver and changes only UI, channel length, and simple R/G loss scaling.
"""

from __future__ import annotations

import csv
import math
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
OUT_DIR = ROOT / "results" / "edge_family_stress_ngspice_2026-05-11"

VLO = 0.0
VHI = 3.3
TR = 200e-12
N_BITS = 200
SKIP_UI = 10

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
    loss_scale: float = 1.0
    note: str = ""

    @property
    def n_sections(self) -> int:
        return 10 * self.length_scale

    @property
    def stop_s(self) -> float:
        return N_BITS * self.ui_s

    @property
    def channel_delay_s(self) -> float:
        return self.n_sections * TD_SECTION


CASES = [
    StressCase("ui5_len10cm_loss1", 5e-9, 1, 1.0, "accepted baseline"),
    StressCase("ui2_len10cm_loss1", 2e-9, 1, 1.0, "data-rate stress"),
    StressCase("ui1_len10cm_loss1", 1e-9, 1, 1.0, "stronger data-rate stress"),
    StressCase("ui5_len30cm_loss1", 5e-9, 3, 1.0, "longer channel only"),
    StressCase("ui2_len30cm_loss1", 2e-9, 3, 1.0, "long channel plus faster UI"),
    StressCase("ui1_len30cm_loss1", 1e-9, 3, 1.0, "channel delay exceeds UI"),
    StressCase("ui2_len10cm_loss5", 2e-9, 1, 5.0, "loss-only stress"),
    StressCase("ui2_len30cm_loss5", 2e-9, 3, 5.0, "long lossy stress"),
]


def prbs7(n_bits: int) -> list[int]:
    reg = [1] * 7
    bits = []
    for _ in range(n_bits):
        bit = reg[6] ^ reg[5]
        bits.append(reg[6])
        reg = [bit] + reg[:6]
    return bits


def prbs_rows(ui_s: float) -> list[tuple[float, float]]:
    bits = prbs7(N_BITS)
    rows: list[tuple[float, float]] = []
    v_prev = VLO if bits[0] == 1 else VHI
    rows.append((0.0, v_prev))
    for i, bit in enumerate(bits):
        v_next = VLO if bit == 1 else VHI
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


def format_pwl(rows: list[tuple[float, float]]) -> str:
    lines = [
        "* Inline PRBS7 V-source PWL stimulus",
        f"* {N_BITS} bits, UI={rows[-1][0] / N_BITS * 1e9:.3f} ns, tr/tf={TR * 1e12:.0f} ps",
    ]
    t0, v0 = rows[0]
    lines.append(f"Vstim  in_src  0  PWL({t0:.9e} {v0:.4f}")
    for i, (t_val, v_val) in enumerate(rows[1:], 1):
        suffix = ")" if i == len(rows) - 1 else ""
        lines.append(f"+ {t_val:.9e}  {v_val:.4f}{suffix}")
    return "\n".join(lines)


def format_channel(case: StressCase) -> str:
    r_sec = R_BASE * case.loss_scale
    g_sec = G_BASE * case.loss_scale
    lines = [
        f"* Generated {case.n_sections}-section RLGC ladder",
        f"* length_scale={case.length_scale}, loss_scale={case.loss_scale:g}",
        f"* nominal one-way delay={case.channel_delay_s * 1e9:.3f} ns",
    ]
    left = "tx_out"
    for i in range(1, case.n_sections + 1):
        a = f"s{i}a"
        b = "n10b" if i == case.n_sections else f"s{i}b"
        lines.extend(
            [
                f"RCH{i:<3d} {left:<8s} {a:<8s} {r_sec:.9g}",
                f"LCH{i:<3d} {a:<8s} {b:<8s} {L_BASE:.9e}",
                f"CCH{i:<3d} {b:<8s} 0        {C_BASE:.9e}",
                f"GCH{i:<3d} {b:<8s} 0        value={{{g_sec:.9e}*v({b},0)}}",
            ]
        )
        left = b
    return "\n".join(lines)


def write_deck(case: StressCase, case_dir: Path) -> Path:
    step_s = min(10e-12, case.ui_s / 100.0)
    deck = f"""* Edge-family stress: ngspice refspice, {case.key}
* {case.note}
* UI={case.ui_s * 1e9:.3f} ns, stop={case.stop_s * 1e9:.3f} ns
* channel_sections={case.n_sections}, channel_delay={case.channel_delay_s * 1e9:.3f} ns, loss_scale={case.loss_scale:g}

.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10

{format_pwl(prbs_rows(case.ui_s))}
Rin    in_src  in_dig  1

Vdd_ref  vdd_ref_src  0  DC 3.3
Voe_ref  oe_ref_src   0  DC 3.3
Rvdd_ref vdd_ref_src  vdd_ref  1
Roe_ref  oe_ref_src   oe_ref   1
Cdec_ref vdd_ref      0        10p

.subckt SPICE_BUF in oe out in_sense vdd vss
.include '../../../../models/hspice_ngspice.mod'
.include '../../../../models/io_buf.sp'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF

RCH_TX  pad_ref tx_out 1u
{format_channel(case)}
RTERM   n10b 0 50

.save V(in_dig) V(pad_ref) V(tx_out) V(n10b) V(in_sense_ref)
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran {step_s:.9e} {case.stop_s:.9e} uic

.end
"""
    case_dir.mkdir(parents=True, exist_ok=True)
    path = case_dir / f"{case.key}.sp"
    path.write_text(deck, encoding="ascii")
    return path


def run_ngspice(case: StressCase, deck: Path, raw: Path, log: Path, timeout_s: float = 180.0):
    raw.unlink(missing_ok=True)
    started = time.time()
    proc = subprocess.run(
        [str(NGSPICE), "-b", "-r", raw.name, deck.name],
        cwd=deck.parent,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    wall_s = time.time() - started
    log.write_text(
        "COMMAND: " + " ".join([str(NGSPICE), "-b", "-r", raw.name, deck.name]) + "\n"
        f"CASE: {case.key}\n"
        f"RETURN_CODE: {proc.returncode}\n"
        f"WALL_SECONDS: {wall_s:.3f}\n\n"
        "STDOUT:\n" + proc.stdout + "\n\nSTDERR:\n" + proc.stderr,
        encoding="utf-8",
    )
    return proc.returncode, wall_s


def crossing_events(time: np.ndarray, voltage: np.ndarray, level: float, ui_s: float):
    above = voltage >= level
    idx = np.where(above[:-1] != above[1:])[0]
    events: list[tuple[float, str]] = []
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


def analyze_case(case: StressCase, raw: Path):
    data = load_waveform(raw, fmt="ngspice")
    t_in, v_in = sanitize_waveform(data["time"], data["v(in_dig)"])
    t_out, v_out = sanitize_waveform(data["time"], data[resolve_signal_key(data, "v(n10b)")])
    in_mid = 0.5 * (float(np.min(v_in)) + float(np.max(v_in)))
    levels = estimate_signal_levels(v_out)
    events = crossing_events(t_in, v_in, in_mid, case.ui_s)
    x_grid = np.linspace(-0.6 * case.ui_s, 1.4 * case.ui_s + case.channel_delay_s, 1600)

    event_rows = []
    traces = {"rise": [], "fall": []}
    trace_contexts = {"rise": [], "fall": []}
    for edge_idx, (event_t, direction) in enumerate(events):
        if event_t + x_grid[0] < t_out[0] or event_t + x_grid[-1] > t_out[-1]:
            continue
        t50 = first_crossing(
            t_out,
            v_out,
            levels["v_mid"],
            event_t,
            event_t + max(5e-9, 2.5 * case.ui_s + case.channel_delay_s),
            direction,
        )
        if direction == "rise":
            t20 = first_crossing(t_out, v_out, levels["v20"], event_t, event_t + max(5e-9, 2.5 * case.ui_s + case.channel_delay_s), "rise")
            t80 = first_crossing(t_out, v_out, levels["v80"], event_t, event_t + max(5e-9, 2.5 * case.ui_s + case.channel_delay_s), "rise")
            slew = t80 - t20 if math.isfinite(t20) and math.isfinite(t80) else float("nan")
        else:
            t80 = first_crossing(t_out, v_out, levels["v80"], event_t, event_t + max(5e-9, 2.5 * case.ui_s + case.channel_delay_s), "fall")
            t20 = first_crossing(t_out, v_out, levels["v20"], event_t, event_t + max(5e-9, 2.5 * case.ui_s + case.channel_delay_s), "fall")
            slew = t20 - t80 if math.isfinite(t20) and math.isfinite(t80) else float("nan")

        trace = np.interp(event_t + x_grid, t_out, v_out)
        context = context_for_event(t_in, v_in, in_mid, event_t, case.ui_s)
        traces[direction].append(trace)
        trace_contexts[direction].append(context)
        event_rows.append(
            {
                "case": case.key,
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
        trace_matrix = np.array(traces[direction])
        median_trace = np.median(trace_matrix, axis=0)
        residual_mv = (trace_matrix - median_trace) * 1e3
        delay_med, delay_std, delay_p2p = summarize([row["output_50_delay_ps"] for row in subset])
        slew_med, slew_std, slew_p2p = summarize([row["slew_20_80_ps"] for row in subset])
        summary_rows.append(
            {
                "case": case.key,
                "note": case.note,
                "direction": direction,
                "ui_ns": case.ui_s * 1e9,
                "length_cm": case.length_scale * 10,
                "loss_scale": case.loss_scale,
                "channel_delay_ns": case.channel_delay_s * 1e9,
                "channel_delay_ui": case.channel_delay_s / case.ui_s,
                "stop_ns": case.stop_s * 1e9,
                "edges": len(subset),
                "contexts": ";".join(sorted(set(trace_contexts[direction]))),
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
    plot_case(case, x_grid, traces, trace_contexts, summary_rows)
    plot_eye_for_case(case, t_out, v_out, levels)
    return event_rows, summary_rows


def plot_case(case: StressCase, x_grid, traces, contexts, summary_rows) -> None:
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
    title = (
        f"{case.key}: UI={case.ui_s * 1e9:.3g} ns, "
        f"length={case.length_scale * 10} cm, loss x{case.loss_scale:g}, "
        f"channel delay={case.channel_delay_s / case.ui_s:.2f} UI"
    )
    fig.suptitle(title, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT_DIR / "plots" / f"{case.key}_edge_families.png", dpi=170)
    plt.close(fig)


def plot_eye_for_case(case: StressCase, time: np.ndarray, voltage: np.ndarray, levels) -> None:
    t_eye, eye_slices = build_eye(
        time,
        voltage,
        case.ui_s,
        skip_ui=SKIP_UI,
        n_interp=2000,
        n_ui=2,
        phase_ui=0.0,
    )
    title = (
        f"{case.key}: 2-UI eye, UI={case.ui_s * 1e9:.3g} ns, "
        f"length={case.length_scale * 10} cm, loss x{case.loss_scale:g}"
    )
    plot_eye_overlay(
        t_eye,
        eye_slices,
        title=title,
        outfile=str(OUT_DIR / "plots" / f"{case.key}_eye_overlay.png"),
        n_ui=2,
        levels=levels,
        max_traces=500,
    )


def plot_summary(summary_rows):
    labels = [f"{row['case']}\n{row['direction']}" for row in summary_rows]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(4, 1, figsize=(15, 12), sharex=True)
    metrics = [
        ("delay_50_p2p_ps", "50% delay spread (ps)"),
        ("delay_50_p2p_ui", "50% delay spread (UI)"),
        ("slew_20_80_p2p_ps", "20-80 slew spread (ps)"),
        ("trace_residual_p95_mV", "Trace residual p95 (mV)"),
    ]
    for ax, (key, ylabel) in zip(axes, metrics):
        ax.bar(x, [float(row[key]) for row in summary_rows], color="#4c78a8")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(labels, rotation=35, ha="right")
    fig.suptitle("ngspice refspice edge-family stress matrix", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT_DIR / "plots" / "stress_matrix_summary.png", dpi=170)
    plt.close(fig)


def write_csv(path: Path, rows) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_readme(run_rows, summary_rows):
    clean_stress = sorted(
        [
            row
            for row in summary_rows
            if 0.005 <= float(row["delay_50_p2p_ui"]) <= 0.20
        ],
        key=lambda r: float(r["delay_50_p2p_ui"]),
        reverse=True,
    )
    overstress = sorted(
        [row for row in summary_rows if float(row["delay_50_p2p_ui"]) > 0.50],
        key=lambda r: float(r["delay_50_p2p_ui"]),
        reverse=True,
    )
    lines = [
        "# ngspice Refspice Edge-Family Stress Study",
        "",
        "Goal: find a transient setup where real pattern-dependent edge spread is",
        "visible before changing the eye tool. This uses ngspice plus the",
        "transistor-level `io_buf.sp` model as the raw reference.",
        "",
        "Stress knobs:",
        "",
        "- reduce UI from 5 ns to 2 ns and 1 ns",
        "- increase channel length from 10 cm to 30 cm by adding RLGC sections",
        "- optionally scale simple conductor/dielectric loss with `R` and `G`",
        "",
        "The primary metric is 50% delay peak-to-peak in UI. Bigger values mean",
        "the edge family should visibly thicken in an eye diagram, but very large",
        "multi-UI values mean the eye is already severely closed and edge pairing",
        "is no longer a clean jitter measurement.",
        "",
        "## Recommended Clean Stress Points",
        "",
        "These cases show real edge spread without pushing the response into",
        "multi-UI ambiguity. They are the best next targets for pybis and Xyce.",
        "",
        "| Case | Direction | Delay p2p | Delay p2p UI | Slew p2p | Residual p95 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in clean_stress[:8]:
        lines.append(
            "| {case} | {direction} | {delay_50_p2p_ps:.1f} ps | "
            "{delay_50_p2p_ui:.4f} UI | {slew_20_80_p2p_ps:.1f} ps | "
            "{trace_residual_p95_mV:.1f} mV |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Over-Stress Cases",
            "",
            "These are useful for forcing eye closure, but not ideal for measuring",
            "ordinary jitter because one output transition can be influenced by",
            "multiple input bits.",
            "",
            "| Case | Direction | Delay p2p | Delay p2p UI | Slew p2p |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in overstress[:8]:
        lines.append(
            "| {case} | {direction} | {delay_50_p2p_ps:.1f} ps | "
            "{delay_50_p2p_ui:.4f} UI | {slew_20_80_p2p_ps:.1f} ps |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `stress_summary.csv`: aggregate metrics by case and edge direction",
            "- `stress_events.csv`: per-edge measurements",
            "- `run_summary.csv`: simulator return codes and runtimes",
            "- `plots/stress_matrix_summary.png`: compact comparison plot",
            "- `plots/*_edge_families.png`: per-case edge-family overlays",
            "- `plots/*_eye_overlay.png`: actual 2-UI eye overlays for each stress case",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    if not NGSPICE.exists():
        raise FileNotFoundError(NGSPICE)
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "plots").mkdir(parents=True, exist_ok=True)

    run_rows = []
    all_events = []
    all_summary = []
    for case in CASES:
        case_dir = OUT_DIR / "runs" / case.key
        deck = write_deck(case, case_dir)
        raw = case_dir / f"{case.key}.raw"
        log = case_dir / f"{case.key}.log"
        print(
            f"Running {case.key}: UI={case.ui_s * 1e9:.3g} ns, "
            f"length={case.length_scale * 10} cm, loss x{case.loss_scale:g}",
            flush=True,
        )
        try:
            rc, wall_s = run_ngspice(case, deck, raw, log)
        except subprocess.TimeoutExpired:
            rc, wall_s = "timeout", float("nan")
        run_rows.append(
            {
                "case": case.key,
                "ui_ns": case.ui_s * 1e9,
                "length_cm": case.length_scale * 10,
                "loss_scale": case.loss_scale,
                "channel_delay_ns": case.channel_delay_s * 1e9,
                "channel_delay_ui": case.channel_delay_s / case.ui_s,
                "return_code": rc,
                "wall_s": wall_s,
                "raw": str(raw.relative_to(ROOT)).replace("\\", "/"),
                "log": str(log.relative_to(ROOT)).replace("\\", "/"),
            }
        )
        if rc == 0 and raw.exists():
            events, summary = analyze_case(case, raw)
            all_events.extend(events)
            all_summary.extend(summary)
        else:
            print(f"  skipped analysis for {case.key}: rc={rc}", flush=True)

    write_csv(OUT_DIR / "run_summary.csv", run_rows)
    write_csv(OUT_DIR / "stress_events.csv", all_events)
    write_csv(OUT_DIR / "stress_summary.csv", all_summary)
    plot_summary(all_summary)
    write_readme(run_rows, all_summary)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
