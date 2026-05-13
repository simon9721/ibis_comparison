from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import run_edge_family_stress_crossflow as base
from eye_diagram import load_waveform, resolve_signal_key, sanitize_waveform

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "ngspice_kukd_ab_context38_2026-05-11" / "plots"

BASE_RAW = ROOT / "results" / "ngspice_kukd_ab_context38_2026-05-11" / "runs" / "baseline_pre_kukd" / "ui2_len30cm_loss5_coarse10_ngspice_pybis_baseline_pre_kukd.raw"
CURR_RAW = ROOT / "results" / "ngspice_kukd_ab_context38_2026-05-11" / "runs" / "current_kukd" / "ui2_len30cm_loss5_coarse10_ngspice_pybis_current_kukd.raw"


def load_sig(path: Path):
    data = load_waveform(path, fmt="ngspice")
    t_in, v_in = sanitize_waveform(data["time"], data[resolve_signal_key(data, "v(in_dig)")])
    t_out, v_out = sanitize_waveform(data["time"], data[resolve_signal_key(data, "v(n10b)")])
    return t_in, v_in, t_out, v_out


def y_limits(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    lo = min(float(np.min(a)), float(np.min(b))) - 0.05
    hi = max(float(np.max(a)), float(np.max(b))) + 0.05
    return lo, hi


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base.configure_suite(["--suite", "coarse10_context"])
    case = base.CASES[0]

    b_ti, b_vi, b_to, b_vo = load_sig(BASE_RAW)
    c_ti, c_vi, c_to, c_vo = load_sig(CURR_RAW)

    b_events, _, _ = base.analyze_output(case, base.Flow("ngspice_pybis", "ngspice", "baseline", "ngspice", "#1f77b4"), BASE_RAW)
    c_events, _, _ = base.analyze_output(case, base.Flow("ngspice_pybis", "ngspice", "current", "ngspice", "#d62728"), CURR_RAW)

    b_1011 = [e for e in b_events if e["direction"] == "rise" and e["context"] == "10->11"]
    c_1011 = [e for e in c_events if e["direction"] == "rise" and e["context"] == "10->11"]

    # Plot 0: explicit context timeline on input.
    fig, ax = plt.subplots(figsize=(13, 3.8))
    ax.plot(c_ti * 1e9, c_vi, color="#444444", lw=1.8, label="input v(in_dig)")
    y_hi = float(np.max(c_vi))
    rise_events = [e for e in c_events if e["direction"] == "rise"]
    for e in rise_events:
        tx = float(e["input_crossing_ns"])
        ctx = str(e["context"])
        if ctx == "10->11":
            ax.axvline(tx, color="#d62728", lw=2.0, alpha=0.95)
            ax.text(tx + 0.10, y_hi * 0.83, f"10->11\n{tx:.1f} ns", color="#b2182b", fontsize=9)
        else:
            ax.axvline(tx, color="#888888", lw=0.7, alpha=0.35)
    ax.set_xlim(0.0, case.stop_s * 1e9)
    ax.set_ylim(-0.15, y_hi + 0.2)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("V(in_dig) (V)")
    ax.set_title("Input context timeline: 10->11 events are thick red lines")
    ax.grid(True, alpha=0.2)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ab_context_timeline.png", dpi=190)
    plt.close(fig)

    # Plot 1: full transient comparison with baseline stop marker
    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.plot(c_to * 1e9, c_vo, color="#d62728", lw=1.4, label="current Ku/Kd (optimized)")
    ax.plot(b_to * 1e9, b_vo, color="#1f77b4", lw=1.2, label="baseline pre-Ku/Kd")
    ax.axvline(b_to[-1] * 1e9, color="#1f77b4", ls="--", lw=1.0, alpha=0.8, label=f"baseline end {b_to[-1]*1e9:.2f} ns")
    for i, e in enumerate(c_1011):
        tx = float(e["input_crossing_ns"])
        ax.axvline(tx, color="#d62728", lw=1.9, alpha=0.8)
        ax.text(tx + 0.10, 1.55 - 0.11 * i, f"10->11 @ {tx:.1f} ns", color="#b2182b", fontsize=9)
    for e in b_1011:
        tx = float(e["input_crossing_ns"])
        ax.axvline(tx, color="#1f77b4", lw=1.3, ls=":", alpha=0.7)
    ax.set_xlim(0.0, case.stop_s * 1e9)
    lo, hi = y_limits(b_vo, c_vo)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("V(n10b) (V)")
    ax.set_title("NGspice transient: baseline vs optimized Ku/Kd (10->11 labeled)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ab_transient_full.png", dpi=180)
    plt.close(fig)

    # Plot 1b: absolute-time waveform with only 10->11 labels.
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(c_to * 1e9, c_vo, color="#d62728", lw=1.6, label="current Ku/Kd")
    ax.plot(b_to * 1e9, b_vo, color="#1f77b4", lw=1.2, label="baseline pre-Ku/Kd")
    for e in c_1011:
        tx = float(e["input_crossing_ns"])
        ax.axvline(tx, color="#d62728", lw=2.0, alpha=0.85)
        ax.annotate(
            f"10->11\n{tx:.1f} ns",
            xy=(tx, 1.33),
            xytext=(tx + 0.35, 1.48),
            arrowprops={"arrowstyle": "->", "color": "#b2182b", "lw": 1.0},
            color="#b2182b",
            fontsize=9,
        )
    ax.axvline(b_to[-1] * 1e9, color="#1f77b4", ls="--", lw=1.0, alpha=0.8, label=f"baseline end {b_to[-1]*1e9:.2f} ns")
    ax.set_xlim(0.0, case.stop_s * 1e9)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("V(n10b) (V)")
    ax.set_title("Absolute-time transient with explicit 10->11 markers")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ab_transient_with_10to11_labels.png", dpi=190)
    plt.close(fig)

    # Plot 2: zoom around known anomaly window
    fig, ax = plt.subplots(figsize=(12, 5.5))
    x0, x1 = 18.0, 28.0
    mb = (b_to * 1e9 >= x0) & (b_to * 1e9 <= x1)
    mc = (c_to * 1e9 >= x0) & (c_to * 1e9 <= x1)
    ax.plot(c_to[mc] * 1e9, c_vo[mc], color="#d62728", lw=1.8, label="current Ku/Kd")
    ax.plot(b_to[mb] * 1e9, b_vo[mb], color="#1f77b4", lw=1.5, label="baseline pre-Ku/Kd")
    for e in c_1011:
        tx = float(e["input_crossing_ns"])
        if x0 <= tx <= x1:
            ax.axvline(tx, color="#d62728", ls="-", lw=1.9, alpha=0.8)
            ax.text(tx + 0.05, 1.52, "10->11", color="#b2182b", fontsize=10)
    for e in b_1011:
        tx = float(e["input_crossing_ns"])
        if x0 <= tx <= x1:
            ax.axvline(tx, color="#1f77b4", ls=":", lw=1.3, alpha=0.8)
    ax.set_xlim(x0, x1)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("V(n10b) (V)")
    ax.set_title("Zoom 18-28 ns: includes 10->11 context rise event")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ab_transient_zoom_18_28ns.png", dpi=190)
    plt.close(fig)

    # Plot 3: edge-aligned 10->11 overlays (output vs input crossing reference)
    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    t_rel = np.linspace(-0.8e-9, 2.8e-9, 1200)

    for i, e in enumerate(c_1011):
        t0 = float(e["input_crossing_ns"]) * 1e-9
        y = np.interp(t0 + t_rel, c_to, c_vo)
        ax.plot(t_rel * 1e9, y, color="#d62728", lw=1.5, alpha=0.75, label="current 10->11" if i == 0 else None)

    for i, e in enumerate(b_1011):
        t0 = float(e["input_crossing_ns"]) * 1e-9
        # Only use valid interpolation span for partial baseline run
        span = (t0 + t_rel >= b_to[0]) & (t0 + t_rel <= b_to[-1])
        y = np.interp((t0 + t_rel)[span], b_to, b_vo)
        ax.plot((t_rel[span]) * 1e9, y, color="#1f77b4", lw=1.7, alpha=0.85, label="baseline 10->11" if i == 0 else None)

    ax.axvline(0.0, color="#333333", lw=1.0, ls="--", alpha=0.7)
    ax.text(0.04, 1.57, "input crossing t=0", color="#333333", fontsize=9)
    ax.set_xlabel("Time from input 50% crossing (ns)")
    ax.set_ylabel("V(n10b) (V)")
    ax.set_title("10->11 edge-aligned output traces")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ab_10to11_edge_aligned.png", dpi=190)
    plt.close(fig)

    print(f"Saved: {OUT_DIR / 'ab_context_timeline.png'}")
    print(f"Saved: {OUT_DIR / 'ab_transient_full.png'}")
    print(f"Saved: {OUT_DIR / 'ab_transient_with_10to11_labels.png'}")
    print(f"Saved: {OUT_DIR / 'ab_transient_zoom_18_28ns.png'}")
    print(f"Saved: {OUT_DIR / 'ab_10to11_edge_aligned.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
