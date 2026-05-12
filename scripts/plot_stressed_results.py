"""Plot clear transient and eye-diagram results for the stressed context38 case.

Loads already-completed simulation data from:
  results/edge_family_stress_crossflow_coarse10_context38_2026-05-11/runs/

Produces in:
  results/stressed_results_2026-05-11/
    transient_overview.png          -- 3-panel full + 2 zooms, all flows
    rise_family_comparison.png      -- 4-panel (one per flow) rise families
    fall_family_comparison.png      -- 4-panel (one per flow) fall families
    eye_comparison_grid.png         -- 2x2 grid of 2-UI eye diagrams
    rise_anomaly_detail.png         -- zoom on the 10->11 fast rise anomaly
    metrics_comparison.png          -- bar chart: delay/slew/residual by flow+direction
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import (
    build_eye,
    estimate_signal_levels,
    load_waveform,
    plot_eye_overlay,
    resolve_signal_key,
    sanitize_waveform,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
RUN_DIR = ROOT / "results" / "edge_family_stress_crossflow_coarse10_context38_2026-05-11" / "runs" / "ui2_len30cm_loss5_coarse10"
OUT_DIR = ROOT / "results" / "stressed_results_2026-05-11"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UI_S = 2e-9
SKIP_UI = 2
N_UI_EYE = 2
CONTEXT38_STOP_NS = 76.0     # full context38 run is 38 bits × 2ns

# Channel: 10 coarse sections, scale=3, loss=5 -> ~3.96 ns one-way delay
# (used only to size the edge-family search window)
CHANNEL_DELAY_S = 3.96e-9

FLOWS = [
    dict(key="ngspice_refspice",  label="ngspice + io_buf.sp",        fmt="ngspice", color="#1f77b4"),
    dict(key="ngspice_pybis",     label="ngspice + pybis",            fmt="ngspice", color="#ff7f0e"),
    dict(key="xyce_refspice",     label="Xyce + io_buf.sp",           fmt="xyce",    color="#2ca02c"),
    dict(key="xyce_pybis",        label="Xyce + pybis (partial 24ns)",fmt="xyce",    color="#d62728"),
]

CONTEXT_COLORS = {
    "00->10": "#1f77b4",
    "10->11": "#e31a1c",   # RED -- the anomaly
    "10->10": "#4c78a8",
    "00->11": "#72b7b2",
    "01->00": "#ff7f0e",
    "11->01": "#d62728",
    "11->00": "#f58518",
    "01->01": "#e45756",
    "01->10": "#6baed6",
    "01->11": "#9ecae1",
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def find_output(flow_key: str) -> Path:
    d = RUN_DIR / flow_key
    for p in d.iterdir():
        if p.suffix in (".raw",) or p.name.endswith(".cir.csv"):
            return p
    raise FileNotFoundError(f"No output found in {d}")


def load_flow(flow: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    """Returns (t_in, v_in, t_out, v_out) or None."""
    try:
        path = find_output(flow["key"])
        data = load_waveform(path, fmt=flow["fmt"])
        t_in, v_in = sanitize_waveform(data["time"], data["v(in_dig)"])
        out_key = resolve_signal_key(data, "v(n10b)")
        t_out, v_out = sanitize_waveform(data["time"], data[out_key])
        return t_in, v_in, t_out, v_out
    except Exception as exc:
        print(f"  WARNING: could not load {flow['key']}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Edge analysis (inline, simplified from run_edge_family_stress_crossflow.py)
# ---------------------------------------------------------------------------

def crossing_events(time: np.ndarray, voltage: np.ndarray, level: float):
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
        if tc < time[0] + SKIP_UI * UI_S:
            continue
        if tc - last_t < 0.45 * UI_S:
            continue
        events.append((float(tc), "rise" if v1 > v0 else "fall"))
        last_t = float(tc)
    return events


def first_crossing(time, voltage, level, start, stop, direction) -> float:
    mask = (time >= start) & (time <= stop)
    t, v = time[mask], voltage[mask]
    if len(t) < 2:
        return float("nan")
    above = v >= level
    idx = np.where((~above[:-1]) & above[1:])[0] if direction == "rise" else np.where(above[:-1] & (~above[1:]))[0]
    if len(idx) == 0:
        return float("nan")
    i = idx[0]
    if v[i + 1] == v[i]:
        return float("nan")
    return float(t[i] + (level - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i]))


def bit_at(time, voltage, level, tc) -> str:
    if tc < time[0] or tc > time[-1]:
        return "x"
    return "1" if float(np.interp(tc, time, voltage)) >= level else "0"


def context_label(time, voltage, level, event_t) -> str:
    return (
        bit_at(time, voltage, level, event_t - 1.35 * UI_S)
        + bit_at(time, voltage, level, event_t - 0.35 * UI_S)
        + "->"
        + bit_at(time, voltage, level, event_t + 0.35 * UI_S)
        + bit_at(time, voltage, level, event_t + 1.35 * UI_S)
    )


def extract_edge_families(t_in, v_in, t_out, v_out):
    """Returns dict with 'rise' and 'fall' each having traces, contexts, delays, slews."""
    in_mid = 0.5 * (float(np.min(v_in)) + float(np.max(v_in)))
    levels = estimate_signal_levels(v_out)
    events = crossing_events(t_in, v_in, in_mid)
    x_grid = np.linspace(-0.6 * UI_S, 1.4 * UI_S + CHANNEL_DELAY_S, 1600)
    stop = max(5e-9, 2.5 * UI_S + CHANNEL_DELAY_S)

    result = {"rise": [], "fall": [], "x_grid": x_grid, "levels": levels}
    for event_t, direction in events:
        if event_t + x_grid[0] < t_out[0] or event_t + x_grid[-1] > t_out[-1]:
            continue
        t50 = first_crossing(t_out, v_out, levels["v_mid"], event_t, event_t + stop, direction)
        if direction == "rise":
            t20 = first_crossing(t_out, v_out, levels["v20"], event_t, event_t + stop, "rise")
            t80 = first_crossing(t_out, v_out, levels["v80"], event_t, event_t + stop, "rise")
        else:
            t80 = first_crossing(t_out, v_out, levels["v80"], event_t, event_t + stop, "fall")
            t20 = first_crossing(t_out, v_out, levels["v20"], event_t, event_t + stop, "fall")
        slew = abs(t20 - t80) if math.isfinite(t20) and math.isfinite(t80) else float("nan")
        delay = (t50 - event_t) * 1e12 if math.isfinite(t50) else float("nan")
        trace = np.interp(event_t + x_grid, t_out, v_out)
        ctx = context_label(t_in, v_in, in_mid, event_t)
        result[direction].append({"trace": trace, "context": ctx, "delay_ps": delay, "slew_ps": slew * 1e12, "event_t": event_t})

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def annotate_stats(ax, edges, direction, fontsize=8.5):
    delays = [e["delay_ps"] for e in edges if math.isfinite(e["delay_ps"])]
    if not delays:
        return
    p2p = max(delays) - min(delays)
    ax.text(
        0.98, 0.97,
        f"n={len(delays)}  delay p2p={p2p:.0f} ps",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=fontsize, color="#333333",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#aaaaaa", alpha=0.85),
    )


def plot_edge_family_panel(ax, ax_res, edges, x_grid, direction, show_legend=True):
    if not edges:
        ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", va="center", color="gray")
        return
    traces = np.array([e["trace"] for e in edges])
    median = np.median(traces, axis=0)
    seen = set()
    for edge in edges:
        ctx = edge["context"]
        color = CONTEXT_COLORS.get(ctx, "#888888")
        lw = 1.8 if ctx == "10->11" else 0.6
        alpha = 0.9 if ctx == "10->11" else 0.30
        label = ctx if (ctx not in seen and show_legend) else None
        seen.add(ctx)
        ax.plot(x_grid * 1e9, edge["trace"], color=color, lw=lw, alpha=alpha, label=label)
        ax_res.plot(x_grid * 1e9, (edge["trace"] - median) * 1e3, color=color, lw=lw * 0.8, alpha=alpha * 0.85)
    ax.plot(x_grid * 1e9, median, color="#111111", lw=2.0, label="median" if show_legend else None, zorder=5)
    ax_res.axhline(0.0, color="#111111", lw=1.2)
    annotate_stats(ax, edges, direction)
    if show_legend:
        ax.legend(fontsize=7, loc="lower right", ncol=2)


# ---------------------------------------------------------------------------
# Plot 1: Transient overview
# ---------------------------------------------------------------------------

def plot_transient_overview(waveforms: dict):
    fig, axes = plt.subplots(3, 1, figsize=(13, 9.5), sharey=True)
    windows = [(0.0, 76.0), (0.0, 30.0), (18.0, 28.0)]
    titles = ["Full context38 run (0–76 ns)", "First 30 ns", "Zoom: 18–28 ns (contains 10->11 rise events)"]

    for ax, (x0, x1), title in zip(axes, windows, titles):
        for flow in FLOWS:
            if flow["key"] not in waveforms:
                continue
            t_in, v_in, t_out, v_out = waveforms[flow["key"]]
            t_ns = t_out * 1e9
            mask = (t_ns >= x0) & (t_ns <= x1)
            if not np.any(mask):
                continue
            ax.plot(t_ns[mask], v_out[mask], color=flow["color"], lw=0.9, alpha=0.92, label=flow["label"])
        ax.set_xlim(x0, x1)
        ax.set_ylabel("V(n10b) (V)")
        ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.22)
        ax.legend(loc="upper right", fontsize=8)

    # Mark known 10->11 input events in the zoom panel
    ax_zoom = axes[2]
    # context38 sequence: 0000100110101111000000010011010111100...
    context38 = [int(ch) for ch in "00001001101011110000000100110101111000"]
    t_events = []
    for i in range(1, len(context38)):
        if context38[i] == 1 and context38[i - 1] == 0:
            t_edge = i * UI_S
            if 18e-9 <= t_edge <= 28e-9:
                # check if previous-previous is also 0 (would be 00->1x) or 1 (10->1x)
                ctx = (
                    str(context38[i - 2]) if i >= 2 else "x"
                ) + str(context38[i - 1]) + "->" + str(context38[i]) + (str(context38[i + 1]) if i + 1 < len(context38) else "x")
                t_events.append((t_edge * 1e9, ctx))

    for t_e, ctx in t_events:
        color = "#e31a1c" if "->1" in ctx and ctx[1] == "0" else "#888888"
        ax_zoom.axvline(t_e, color=color, lw=1.2, ls="--", alpha=0.7, zorder=0)

    axes[-1].set_xlabel("Time (ns)")
    fig.suptitle(
        "Stressed case: UI=2 ns, 30 cm RLGC, loss×5 (10 coarse sections)\n"
        "Receiver output V(n10b) — all flows",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = OUT_DIR / "transient_overview.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(f"  Saved {out.name}")


# ---------------------------------------------------------------------------
# Plot 2 & 3: Rise / fall family comparison (4-panel, one per flow)
# ---------------------------------------------------------------------------

def plot_family_comparison(families: dict, direction: str):
    fig = plt.figure(figsize=(15, 9))
    gs = gridspec.GridSpec(2, 4, hspace=0.42, wspace=0.32, figure=fig)

    for col, flow in enumerate(FLOWS):
        fkey = flow["key"]
        if fkey not in families:
            ax = fig.add_subplot(gs[0, col])
            ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", va="center", color="gray", fontsize=10)
            ax.set_title(flow["label"], fontsize=9)
            ax.set_visible(True)
            continue
        fam = families[fkey]
        edges = fam[direction]
        x_grid = fam["x_grid"]
        ax_top = fig.add_subplot(gs[0, col])
        ax_bot = fig.add_subplot(gs[1, col])
        plot_edge_family_panel(ax_top, ax_bot, edges, x_grid, direction, show_legend=(col == 0))
        ax_top.set_title(flow["label"], fontsize=8.5)
        ax_top.set_ylabel("V(n10b) (V)" if col == 0 else "")
        ax_top.set_xlabel("")
        ax_bot.set_xlabel("Time from input 50% (ns)" if col == 1 else "")
        ax_bot.set_ylabel("Residual (mV)" if col == 0 else "")
        ax_top.grid(True, alpha=0.22)
        ax_bot.grid(True, alpha=0.22)
        # Annotate 10->11 count
        n_anomaly = sum(1 for e in edges if e["context"] == "10->11")
        if n_anomaly > 0:
            ax_top.set_facecolor("#fff8f8")

    cmap_label = "10->11 highlighted in red — anomalous fast rise in pybis only"
    fig.suptitle(
        f"{'Rising' if direction == 'rise' else 'Falling'} edge families — stressed case\n"
        f"(UI=2 ns, 30 cm, loss×5)   {cmap_label if direction == 'rise' else ''}",
        fontsize=11,
    )
    out = OUT_DIR / f"{direction}_family_comparison.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(f"  Saved {out.name}")


# ---------------------------------------------------------------------------
# Plot 4: Eye diagram 2×2 grid
# ---------------------------------------------------------------------------

def plot_eye_grid(waveforms: dict):
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    axes_flat = axes.flatten()

    for i, flow in enumerate(FLOWS):
        ax = axes_flat[i]
        fkey = flow["key"]
        if fkey not in waveforms:
            ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", va="center", color="gray")
            ax.set_title(flow["label"], fontsize=9)
            continue
        t_in, v_in, t_out, v_out = waveforms[fkey]
        # Check if we have enough data for an eye
        if t_out[-1] < (SKIP_UI + N_UI_EYE + 1) * UI_S:
            ax.text(0.5, 0.5, f"partial data only\n(ends {t_out[-1]*1e9:.1f} ns)", transform=ax.transAxes, ha="center", va="center", color="gray", fontsize=9)
            ax.set_title(flow["label"], fontsize=9)
            continue
        levels = estimate_signal_levels(v_out)
        try:
            t_eye, eye_slices = build_eye(t_out, v_out, UI_S, skip_ui=SKIP_UI, n_interp=2000, n_ui=N_UI_EYE, phase_ui=0.0)
        except Exception as exc:
            ax.text(0.5, 0.5, f"eye failed:\n{exc}", transform=ax.transAxes, ha="center", va="center", color="red", fontsize=8)
            ax.set_title(flow["label"])
            continue

        n_traces = len(eye_slices)
        for trace in eye_slices[:500]:
            ax.plot(t_eye * 1e9, trace, color=flow["color"], lw=0.35, alpha=0.12)
        ax.set_xlim(t_eye[0] * 1e9, t_eye[-1] * 1e9)
        ax.axhline(levels["v_mid"], color="#333333", lw=0.8, ls="--", alpha=0.6)
        ax.axhline(levels["v20"], color="#999999", lw=0.6, ls=":", alpha=0.5)
        ax.axhline(levels["v80"], color="#999999", lw=0.6, ls=":", alpha=0.5)
        ax.set_title(flow["label"], fontsize=9)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("V(n10b) (V)")
        ax.grid(True, alpha=0.2)
        ax.text(0.02, 0.97, f"n={n_traces} UI", transform=ax.transAxes, va="top", fontsize=8, color="#555555")

    fig.suptitle(
        "2-UI Eye Diagrams — stressed case (UI=2 ns, 30 cm RLGC, loss×5)\n"
        "Note: Xyce+pybis partial data only (~24 ns, timed out)",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = OUT_DIR / "eye_comparison_grid.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(f"  Saved {out.name}")


# ---------------------------------------------------------------------------
# Plot 5: Rise anomaly detail — zoom on 10->11 events
# ---------------------------------------------------------------------------

def plot_rise_anomaly_detail(families: dict):
    """Side-by-side: ngspice_refspice vs ngspice_pybis rise families, zoomed."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)

    compare_flows = ["ngspice_refspice", "ngspice_pybis"]
    for ax, fkey in zip(axes, compare_flows):
        flow = next(f for f in FLOWS if f["key"] == fkey)
        if fkey not in families:
            ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", va="center")
            ax.set_title(flow["label"])
            continue
        fam = families[fkey]
        edges = fam["rise"]
        x_grid = fam["x_grid"]
        if not edges:
            ax.text(0.5, 0.5, "no rise edges found", transform=ax.transAxes, ha="center", va="center")
            continue

        for edge in edges:
            ctx = edge["context"]
            is_anomaly = ctx == "10->11"
            color = CONTEXT_COLORS.get(ctx, "#888888")
            ax.plot(
                x_grid * 1e9,
                edge["trace"],
                color=color,
                lw=2.2 if is_anomaly else 0.7,
                alpha=1.0 if is_anomaly else 0.3,
                label=None,
            )
            if is_anomaly:
                delay = edge["delay_ps"]
                ax.annotate(
                    f"10->11\ndelay={delay:.0f} ps" if math.isfinite(delay) else "10->11\n(no 50% cross)",
                    xy=(x_grid[0] * 1e9 + 0.5, float(np.interp(x_grid[0] + 0.5e-9, x_grid, edge["trace"]))),
                    xytext=(1.0, 0.25),
                    textcoords="axes fraction",
                    fontsize=8,
                    color="#e31a1c",
                    arrowprops=dict(arrowstyle="->", color="#e31a1c", lw=1.2),
                )

        # Build legend patches for unique contexts present
        from matplotlib.lines import Line2D
        seen_ctx = sorted(set(e["context"] for e in edges))
        handles = [Line2D([0], [0], color=CONTEXT_COLORS.get(c, "#888"), lw=1.5, label=c) for c in seen_ctx]
        ax.legend(handles=handles, fontsize=8, loc="lower right")

        other_delays = [e["delay_ps"] for e in edges if e["context"] != "10->11" and math.isfinite(e["delay_ps"])]
        anomaly_delays = [e["delay_ps"] for e in edges if e["context"] == "10->11" and math.isfinite(e["delay_ps"])]
        stats_text = ""
        if other_delays:
            stats_text += f"Other rise: {min(other_delays):.0f}–{max(other_delays):.0f} ps\n"
        if anomaly_delays:
            stats_text += f"10->11 rise: {min(anomaly_delays):.0f}–{max(anomaly_delays):.0f} ps  ← ANOMALY" if fkey != "ngspice_refspice" else f"10->11 rise: {min(anomaly_delays):.0f}–{max(anomaly_delays):.0f} ps"

        ax.text(0.02, 0.97, stats_text, transform=ax.transAxes, va="top", fontsize=8.5,
                color="#333333", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cccccc", alpha=0.9))
        ax.set_title(flow["label"], fontsize=10)
        ax.set_xlabel("Time from input 50% crossing (ns)")
        ax.set_ylabel("V(n10b) (V)")
        ax.grid(True, alpha=0.22)
        ax.set_xlim(x_grid[0] * 1e9, x_grid[-1] * 1e9)

    fig.suptitle(
        "Rise edge families: 10->11 anomaly in pybis model\n"
        "Red traces = '10->11' context (previous bit=1, rise after 1 UI of 0)",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    out = OUT_DIR / "rise_anomaly_detail.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(f"  Saved {out.name}")


# ---------------------------------------------------------------------------
# Plot 6: Metrics bar chart comparison
# ---------------------------------------------------------------------------

def plot_metrics_comparison(families: dict):
    rows = []
    for flow in FLOWS:
        fkey = flow["key"]
        if fkey not in families:
            continue
        for direction in ("rise", "fall"):
            edges = families[fkey][direction]
            delays = [e["delay_ps"] for e in edges if math.isfinite(e["delay_ps"])]
            slews = [e["slew_ps"] for e in edges if math.isfinite(e["slew_ps"])]
            if not delays:
                continue
            rows.append({
                "label": flow["label"].replace(" + ", "\n+ "),
                "direction": direction,
                "color": flow["color"],
                "delay_p2p": max(delays) - min(delays),
                "slew_p2p": (max(slews) - min(slews)) if slews else 0.0,
                "n": len(delays),
            })

    if not rows:
        print("  WARNING: no metrics to plot")
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    metrics = [("delay_p2p", "50% delay spread p2p (ps)"), ("slew_p2p", "20-80% slew spread p2p (ps)")]

    for ax, (metric_key, ylabel) in zip(axes, metrics):
        rise_rows = [r for r in rows if r["direction"] == "rise"]
        fall_rows = [r for r in rows if r["direction"] == "fall"]
        all_labels = [r["label"] for r in rise_rows]
        x = np.arange(len(all_labels))
        w = 0.35
        bars_rise = ax.bar(x - w / 2, [r[metric_key] for r in rise_rows], width=w, label="rise", color=[r["color"] for r in rise_rows], alpha=0.85)
        bars_fall = ax.bar(x + w / 2, [r[metric_key] for r in fall_rows] if fall_rows else [0] * len(x), width=w, label="fall", color=[r["color"] for r in fall_rows] if fall_rows else ["gray"] * len(x), alpha=0.55, hatch="//")
        ax.set_xticks(x)
        ax.set_xticklabels(all_labels, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=9)
        # Value labels on bars
        for bar in bars_rise:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.01 * ax.get_ylim()[1], f"{h:.0f}", ha="center", va="bottom", fontsize=7)

    fig.suptitle("Edge-family metric comparison — stressed case (UI=2 ns, 30 cm RLGC, loss×5)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = OUT_DIR / "metrics_comparison.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(f"  Saved {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading waveforms...")
    waveforms = {}
    for flow in FLOWS:
        print(f"  {flow['key']}...", end=" ", flush=True)
        result = load_flow(flow)
        if result is not None:
            waveforms[flow["key"]] = result
            t_in, v_in, t_out, v_out = result
            print(f"OK  ({t_out[-1]*1e9:.1f} ns, {len(t_out)} points)")
        else:
            print("FAILED")

    print("\nExtracting edge families...")
    families = {}
    for flow in FLOWS:
        fkey = flow["key"]
        if fkey not in waveforms:
            continue
        t_in, v_in, t_out, v_out = waveforms[fkey]
        fam = extract_edge_families(t_in, v_in, t_out, v_out)
        families[fkey] = fam
        r_n = len(fam["rise"])
        f_n = len(fam["fall"])
        r_delays = [e["delay_ps"] for e in fam["rise"] if math.isfinite(e["delay_ps"])]
        print(f"  {fkey}: rise={r_n} edges, delay range {min(r_delays):.0f}–{max(r_delays):.0f} ps" if r_delays else f"  {fkey}: rise={r_n} (no valid delays), fall={f_n}")

    print("\nGenerating plots...")
    plot_transient_overview(waveforms)
    plot_family_comparison(families, "rise")
    plot_family_comparison(families, "fall")
    plot_eye_grid(waveforms)
    plot_rise_anomaly_detail(families)
    plot_metrics_comparison(families)

    print(f"\nAll plots saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
