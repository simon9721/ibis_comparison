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
CURR_RAW = ROOT / "results" / "ngspice_kukd_ab_context38_2026-05-11" / "runs" / "current_kukd" / "ui2_len30cm_loss5_coarse10_ngspice_pybis_current_kukd.raw"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base.configure_suite(["--suite", "coarse10_context"])
    case = base.CASES[0]
    ui_ns = case.ui_s * 1e9

    data = load_waveform(CURR_RAW, fmt="ngspice")
    t_in, v_in = sanitize_waveform(data["time"], data[resolve_signal_key(data, "v(in_dig)")])
    t_out, v_out = sanitize_waveform(data["time"], data[resolve_signal_key(data, "v(n10b)")])

    events, _, _ = base.analyze_output(
        case,
        base.Flow("ngspice_pybis", "ngspice", "current", "ngspice", "#d62728"),
        CURR_RAW,
    )
    e1011 = [e for e in events if e["direction"] == "rise" and e["context"] == "10->11"]

    # Build decoded bit stream at UI centers from input signal.
    n_bits = int(round(case.stop_s / case.ui_s))
    centers_ns = (np.arange(n_bits) + 0.5) * ui_ns
    bits = []
    for tc in centers_ns:
        v = float(np.interp(tc * 1e-9, t_in, v_in))
        bits.append(1 if v >= 1.65 else 0)

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(13.5, 7.6), sharex=True, gridspec_kw={"height_ratios": [2.4, 1.2]})

    ax0.plot(t_in * 1e9, v_in, color="#444444", lw=1.2, label="input v(in_dig)")
    ax0.plot(t_out * 1e9, v_out, color="#d62728", lw=1.4, label="output v(n10b)")

    for e in e1011:
        tx = float(e["input_crossing_ns"])
        ax0.axvline(tx, color="#b2182b", lw=2.0, alpha=0.9)
        ax0.axvspan(tx - ui_ns, tx + ui_ns, color="#fddbc7", alpha=0.25)
        ax0.text(tx + 0.10, 1.55, f"1011 window\ncenter edge {tx:.1f} ns", color="#b2182b", fontsize=9)

    ax0.set_ylabel("Voltage (V)")
    ax0.set_ylim(-0.15, 1.65)
    ax0.set_title("Where 1011 happens: highlighted 4-bit windows around the 0->1 edge")
    ax0.grid(True, alpha=0.25)
    ax0.legend(loc="best")

    # Bit-strip panel.
    for i, b in enumerate(bits):
        x0 = i * ui_ns
        x1 = (i + 1) * ui_ns
        fill = "#2ca02c" if b == 1 else "#9ecae1"
        ax1.axvspan(x0, x1, color=fill, alpha=0.35)
        ax1.text((x0 + x1) * 0.5, 0.5, str(b), ha="center", va="center", fontsize=9)

    for e in e1011:
        tx = float(e["input_crossing_ns"])
        ax1.axvline(tx, color="#b2182b", lw=2.0, alpha=0.9)
        ax1.axvspan(tx - ui_ns, tx + ui_ns, color="#fddbc7", alpha=0.35)
        ax1.text(tx - 0.9 * ui_ns, 0.92, "1", color="#b2182b", fontsize=9)
        ax1.text(tx - 0.1 * ui_ns, 0.92, "0", color="#b2182b", fontsize=9)
        ax1.text(tx + 0.1 * ui_ns, 0.92, "1", color="#b2182b", fontsize=9)
        ax1.text(tx + 0.9 * ui_ns, 0.92, "1", color="#b2182b", fontsize=9)
        ax1.text(tx - 0.15, 1.03, "10->11", color="#b2182b", fontsize=10)

    ax1.set_ylim(0.0, 1.08)
    ax1.set_yticks([])
    ax1.set_ylabel("Bits")
    ax1.set_xlabel("Time (ns)")
    ax1.grid(True, axis="x", alpha=0.2)

    out = OUT_DIR / "ab_1011_context_explainer.png"
    fig.tight_layout()
    fig.savefig(out, dpi=190)
    plt.close(fig)
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
