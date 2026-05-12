"""Diagnose whether PRBS receiver eyes contain real edge-family variation.

The eye tool should not invent edge spread. This script checks the transient
data directly by using each input transition as the timing reference, then
overlaying the corresponding receiver response without aligning to the output
50% crossing.
"""

from __future__ import annotations

import csv
import math
import sys
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
    estimate_signal_levels,
    load_waveform,
    resolve_signal_key,
    sanitize_waveform,
)


UI = 5e-9
SKIP_UI = 10
OUT_DIR = ROOT / "results" / "edge_family_diagnostics_2026-05-11"


@dataclass(frozen=True)
class Case:
    key: str
    label: str
    path: Path
    fmt: str
    signal: str = "v(n10b)"


CASES = [
    Case(
        key="ngspice_refspice",
        label="ngspice + io_buf.sp",
        path=ROOT / "ngspice_refspice" / "tb_refspice_prbs7_new50ohm_batch.raw",
        fmt="ngspice",
    ),
    Case(
        key="xyce_refspice",
        label="Xyce + io_buf.sp",
        path=ROOT / "xyce_refspice" / "tb_refspice_prbs7_new50ohm_xyce.cir.csv",
        fmt="xyce",
    ),
    Case(
        key="ngspice_pybis",
        label="ngspice + pybis",
        path=ROOT
        / "results"
        / "prbs_rlgc_clean_2026-05-10"
        / "ngspice"
        / "tb_clean_prbs_rlgc_ngspice.raw",
        fmt="ngspice",
    ),
    Case(
        key="xyce_pybis",
        label="Xyce + pybis edge15_flat4p2",
        path=ROOT
        / "results"
        / "prbs_rlgc_clean_2026-05-10"
        / "xyce"
        / "tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir.csv",
        fmt="xyce",
    ),
]


def crossing_events(
    time: np.ndarray,
    voltage: np.ndarray,
    level: float,
    min_separation: float = 0.45 * UI,
) -> list[tuple[float, str]]:
    """Return de-bounced threshold crossings after the startup skip."""
    above = voltage >= level
    raw_idx = np.where(above[:-1] != above[1:])[0]
    events: list[tuple[float, str]] = []
    last_t = -math.inf
    for idx in raw_idx:
        t0, t1 = time[idx], time[idx + 1]
        v0, v1 = voltage[idx], voltage[idx + 1]
        if v1 == v0:
            continue
        tc = t0 + (level - v0) * (t1 - t0) / (v1 - v0)
        if tc < time[0] + SKIP_UI * UI:
            continue
        if tc - last_t < min_separation:
            continue
        direction = "rise" if v1 > v0 else "fall"
        events.append((float(tc), direction))
        last_t = float(tc)
    return events


def first_crossing(
    time: np.ndarray,
    voltage: np.ndarray,
    level: float,
    start: float,
    stop: float,
    direction: str,
) -> float:
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


def bit_at(time: np.ndarray, voltage: np.ndarray, level: float, t: float) -> str:
    if t < time[0] or t > time[-1]:
        return "x"
    return "1" if float(np.interp(t, time, voltage)) >= level else "0"


def context_for_event(time: np.ndarray, voltage: np.ndarray, level: float, event_t: float) -> str:
    prev_bit = bit_at(time, voltage, level, event_t - 1.35 * UI)
    before_bit = bit_at(time, voltage, level, event_t - 0.35 * UI)
    after_bit = bit_at(time, voltage, level, event_t + 0.35 * UI)
    next_bit = bit_at(time, voltage, level, event_t + 1.35 * UI)
    return f"{prev_bit}{before_bit}->{after_bit}{next_bit}"


def summarize(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return {"median": float("nan"), "std": float("nan"), "p2p": float("nan")}
    return {
        "median": float(np.median(finite)),
        "std": float(np.std(finite)),
        "p2p": float(np.max(finite) - np.min(finite)),
    }


def process_case(case: Case):
    data = load_waveform(case.path, fmt=case.fmt)
    t_in, v_in = sanitize_waveform(data["time"], data["v(in_dig)"])
    out_key = resolve_signal_key(data, case.signal)
    t_out, v_out = sanitize_waveform(data["time"], data[out_key])

    in_mid = 0.5 * (float(np.min(v_in)) + float(np.max(v_in)))
    out_levels = estimate_signal_levels(v_out)
    events = crossing_events(t_in, v_in, in_mid)
    x_grid = np.linspace(-1.0e-9, 5.0e-9, 1600)

    rows = []
    traces: dict[str, list[np.ndarray]] = {"rise": [], "fall": []}
    contexts: dict[str, list[str]] = {"rise": [], "fall": []}
    for edge_index, (event_t, direction) in enumerate(events):
        if event_t + x_grid[0] < t_out[0] or event_t + x_grid[-1] > t_out[-1]:
            continue
        trace = np.interp(event_t + x_grid, t_out, v_out)
        t50 = first_crossing(
            t_out,
            v_out,
            out_levels["v_mid"],
            event_t,
            event_t + 5e-9,
            direction,
        )
        if direction == "rise":
            t20 = first_crossing(t_out, v_out, out_levels["v20"], event_t, event_t + 5e-9, "rise")
            t80 = first_crossing(t_out, v_out, out_levels["v80"], event_t, event_t + 5e-9, "rise")
            slew = t80 - t20 if math.isfinite(t20) and math.isfinite(t80) else float("nan")
        else:
            t80 = first_crossing(t_out, v_out, out_levels["v80"], event_t, event_t + 5e-9, "fall")
            t20 = first_crossing(t_out, v_out, out_levels["v20"], event_t, event_t + 5e-9, "fall")
            slew = t20 - t80 if math.isfinite(t20) and math.isfinite(t80) else float("nan")

        context = context_for_event(t_in, v_in, in_mid, event_t)
        traces[direction].append(trace)
        contexts[direction].append(context)
        rows.append(
            {
                "case": case.key,
                "label": case.label,
                "direction": direction,
                "edge_index": edge_index,
                "input_crossing_ns": event_t * 1e9,
                "context": context,
                "output_50_delay_ps": (t50 - event_t) * 1e12 if math.isfinite(t50) else float("nan"),
                "slew_20_80_ps": slew * 1e12 if math.isfinite(slew) else float("nan"),
            }
        )

    summary_rows = []
    for direction in ("rise", "fall"):
        dir_rows = [row for row in rows if row["direction"] == direction]
        if not dir_rows:
            continue
        trace_matrix = np.array(traces[direction])
        median_trace = np.median(trace_matrix, axis=0)
        residual_mv = (trace_matrix - median_trace) * 1e3
        delay_stats = summarize(np.array([row["output_50_delay_ps"] for row in dir_rows]))
        slew_stats = summarize(np.array([row["slew_20_80_ps"] for row in dir_rows]))
        summary_rows.append(
            {
                "case": case.key,
                "label": case.label,
                "direction": direction,
                "edges": len(dir_rows),
                "contexts": ";".join(sorted(set(contexts[direction]))),
                "delay_50_median_ps": delay_stats["median"],
                "delay_50_std_ps": delay_stats["std"],
                "delay_50_p2p_ps": delay_stats["p2p"],
                "slew_20_80_median_ps": slew_stats["median"],
                "slew_20_80_std_ps": slew_stats["std"],
                "slew_20_80_p2p_ps": slew_stats["p2p"],
                "trace_residual_p95_mV": float(np.percentile(np.abs(residual_mv), 95)),
                "trace_residual_max_mV": float(np.max(np.abs(residual_mv))),
            }
        )

    plot_case(case, x_grid, traces, contexts, summary_rows)
    return rows, summary_rows


def plot_case(case: Case, x_grid: np.ndarray, traces, contexts, summary_rows) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 7.5), sharex=True)
    colors = {
        "00->10": "#1f77b4",
        "10->11": "#17becf",
        "01->00": "#ff7f0e",
        "11->01": "#d62728",
    }

    for col, direction in enumerate(("rise", "fall")):
        trace_matrix = np.array(traces[direction])
        ax = axes[0, col]
        ax_res = axes[1, col]
        if trace_matrix.size == 0:
            ax.set_title(f"{direction}: no edges found")
            continue
        median_trace = np.median(trace_matrix, axis=0)
        seen_labels = set()
        for trace, context in zip(trace_matrix, contexts[direction]):
            color = colors.get(context, "#777777")
            label = context if context not in seen_labels else None
            seen_labels.add(context)
            ax.plot(x_grid * 1e9, trace, color=color, lw=0.7, alpha=0.35, label=label)
            ax_res.plot(
                x_grid * 1e9,
                (trace - median_trace) * 1e3,
                color=color,
                lw=0.65,
                alpha=0.30,
            )
        ax.plot(x_grid * 1e9, median_trace, color="#111111", lw=2.0, label="median")
        matching = [row for row in summary_rows if row["direction"] == direction]
        title_extra = ""
        if matching:
            row = matching[0]
            title_extra = (
                f"delay p2p={row['delay_50_p2p_ps']:.1f} ps, "
                f"slew p2p={row['slew_20_80_p2p_ps']:.1f} ps"
            )
        ax.set_title(f"{direction.capitalize()} edge family ({title_extra})")
        ax.set_ylabel("V(n10b) (V)")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best", fontsize=8)

        ax_res.axhline(0.0, color="#111111", lw=1.0)
        ax_res.set_title(f"{direction.capitalize()} residuals vs median")
        ax_res.set_xlabel("Time from input 50% crossing (ns)")
        ax_res.set_ylabel("Residual (mV)")
        ax_res.grid(True, alpha=0.25)

    fig.suptitle(f"{case.label}: receiver edge families, input-clock referenced", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{case.key}_edge_families.png", dpi=170)
    plt.close(fig)


def plot_summary(summary_rows: list[dict[str, object]]) -> None:
    labels = [f"{row['label']}\n{row['direction']}" for row in summary_rows]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    metrics = [
        ("delay_50_p2p_ps", "50% delay spread (ps)"),
        ("slew_20_80_p2p_ps", "20-80 slew spread (ps)"),
        ("trace_residual_p95_mV", "Trace residual p95 (mV)"),
    ]
    for ax, (key, ylabel) in zip(axes, metrics):
        values = [float(row[key]) for row in summary_rows]
        ax.bar(x, values, color="#4c78a8")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(labels, rotation=25, ha="right")
    fig.suptitle("Edge-family variation measured directly from transient data", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT_DIR / "edge_family_variation_summary.png", dpi=170)
    plt.close(fig)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_readme(summary_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Edge Family Diagnostics",
        "",
        "This folder checks whether the accepted PRBS/RLGC transient data contains",
        "multiple visibly different rising and falling receiver edge families.",
        "",
        "Method:",
        "",
        "- detect each `v(in_dig)` 50% crossing after the first 10 UIs",
        "- extract `v(n10b)` from -1 ns to +5 ns around that input crossing",
        "- do not align traces to the output crossing",
        "- measure output 50% delay spread, 20-80% slew spread, and residual",
        "  spread relative to the median edge shape",
        "",
        "Main result:",
        "",
        "The accepted 5 ns UI / 50 ohm RLGC data has very little edge-family",
        "variation. The eye tool is not collapsing a wide family of edges into",
        "one template; the transient waveforms themselves are already close to",
        "template-like for each edge polarity.",
        "",
        "## Summary",
        "",
        "| Case | Direction | Edges | 50% delay p2p | 20-80 slew p2p | Residual p95 | Residual max |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {label} | {direction} | {edges} | {delay_50_p2p_ps:.2f} ps | "
            "{slew_20_80_p2p_ps:.2f} ps | {trace_residual_p95_mV:.2f} mV | "
            "{trace_residual_max_mV:.2f} mV |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `edge_family_summary.csv`: aggregate variation metrics",
            "- `edge_family_events.csv`: one row per detected edge",
            "- `*_edge_families.png`: per-case rising/falling overlays and residuals",
            "- `edge_family_variation_summary.png`: compact bar-chart summary",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    all_events = []
    all_summary = []
    for case in CASES:
        print(f"Processing {case.label}: {case.path.relative_to(ROOT)}")
        events, summary = process_case(case)
        all_events.extend(events)
        all_summary.extend(summary)
    write_csv(OUT_DIR / "edge_family_events.csv", all_events)
    write_csv(OUT_DIR / "edge_family_summary.csv", all_summary)
    plot_summary(all_summary)
    write_readme(all_summary)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
