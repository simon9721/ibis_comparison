"""
RSF comparison plot using two SEPARATE raw files instead of a combined bench.

Loads:
  - ngspice_refspice/tb_validation_refspice_rsf_batch.raw
  - ngspice_pybis/tb_validation_rfr_ngspice_pybis_12n_batch.raw

Both benches use the same RSF stimulus:
  - Rise at ~1ns (5ps edges)
  - High for 8ns
  - Fall at ~9ns
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
RAW_REF = ROOT / "ngspice_refspice" / "tb_validation_refspice_rsf_batch.raw"
RAW_PYBIS = ROOT / "ngspice_pybis" / "tb_validation_rfr_ngspice_pybis_12n_batch.raw"
OUT_DIR = ROOT / "plots" / "validation"

EXPECTED_STOP_NS = 12.0
MIN_VALID_STOP_NS = 11.0


def ns(time_s):
    return time_s * 1e9


def style_axis(ax, title, ylabel="V"):
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def check_raw(data, label, min_ns=MIN_VALID_STOP_NS):
    if len(data["time"]) == 0:
        raise RuntimeError(f"{label}: no data points found in raw file.")
    last_t = float(data["time"][-1]) * 1e9
    if last_t < min_ns:
        raise RuntimeError(
            f"{label}: ended at {last_t:.3f} ns, expected >= {min_ns:.0f} ns. "
            "Refusing to generate a misleading plot."
        )
    return last_t


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading refspice RSF raw: {RAW_REF}")
    ref = parse_ngspice_raw(RAW_REF)
    ref_last = check_raw(ref, "refspice RSF")
    print(f"  -> {len(ref['time'])} rows, last={ref_last:.3f} ns")

    print(f"Loading pybis 12n-RFR raw: {RAW_PYBIS}")
    pybis = parse_ngspice_raw(RAW_PYBIS)
    pybis_last = check_raw(pybis, "pybis 12n-RFR")
    print(f"  -> {len(pybis['time'])} rows, last={pybis_last:.3f} ns")

    # Determine the common time window (12ns)
    t_max_ns = min(ref_last, pybis_last, EXPECTED_STOP_NS)

    time_ref_ns = ns(ref["time"])
    time_pybis_ns = ns(pybis["time"])

    # Trim to common window
    ref_mask = time_ref_ns <= t_max_ns + 0.001
    pybis_mask = time_pybis_ns <= t_max_ns + 0.001

    plt.rcParams.update({
        "figure.figsize": (11, 5.5),
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    # --- Pad voltage comparison ---
    fig_pad, ax_pad = plt.subplots()
    ax_pad.plot(
        time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask],
        label="Reference SPICE pad", linewidth=2.0
    )
    # pybis raw uses "v(pad)" not "v(pad_ibis)"
    pybis_pad_key = "v(pad)" if "v(pad)" in pybis else "v(pad_ibis)"
    ax_pad.plot(
        time_pybis_ns[pybis_mask], pybis[pybis_pad_key][pybis_mask],
        label="Converted IBIS-SPICE pad", linewidth=2.0, linestyle="--"
    )
    # Use refspice input for reference (same stimulus)
    ax_pad.plot(
        time_ref_ns[ref_mask], ref["v(in_dig)"][ref_mask],
        "--", label="Input (shared)", linewidth=1.5, alpha=0.8, color="gray"
    )
    style_axis(ax_pad, "Rise-Steady-Fall Pad Comparison: Reference SPICE vs Converted IBIS-SPICE\n(separate standalone reruns)")
    ax_pad.legend(loc="best")
    fig_pad.tight_layout()
    out_pad = OUT_DIR / "refspice_vs_pybis_rsf_pad_separate.png"
    fig_pad.savefig(out_pad, dpi=180, bbox_inches="tight")
    plt.close(fig_pad)
    print(f"Saved: {out_pad}")

    # --- Load voltage comparison ---
    fig_load, ax_load = plt.subplots()
    ax_load.plot(
        time_ref_ns[ref_mask], ref["v(ntst_ref)"][ref_mask],
        label="Reference SPICE load", linewidth=2.0
    )
    pybis_ntst_key = "v(ntst)" if "v(ntst)" in pybis else "v(ntst_ibis)"
    ax_load.plot(
        time_pybis_ns[pybis_mask], pybis[pybis_ntst_key][pybis_mask],
        label="Converted IBIS-SPICE load", linewidth=2.0, linestyle="--"
    )
    ax_load.plot(
        time_ref_ns[ref_mask], ref["v(in_dig)"][ref_mask],
        "--", label="Input (shared)", linewidth=1.5, alpha=0.8, color="gray"
    )
    style_axis(ax_load, "Rise-Steady-Fall Load Comparison: Reference SPICE vs Converted IBIS-SPICE\n(separate standalone reruns)")
    ax_load.legend(loc="best")
    fig_load.tight_layout()
    out_load = OUT_DIR / "refspice_vs_pybis_rsf_load_separate.png"
    fig_load.savefig(out_load, dpi=180, bbox_inches="tight")
    plt.close(fig_load)
    print(f"Saved: {out_load}")

    # --- Ku/Kd comparison (pybis) ---
    if "v(xdrv.ku)" in pybis and "v(xdrv.kd)" in pybis:
        fig_ku, ax_ku = plt.subplots()
        ax_ku.plot(
            time_pybis_ns[pybis_mask], pybis["v(xdrv.ku)"][pybis_mask],
            label="Ku", linewidth=2.0
        )
        ax_ku.plot(
            time_pybis_ns[pybis_mask], pybis["v(xdrv.kd)"][pybis_mask],
            label="Kd", linewidth=2.0
        )
        style_axis(ax_ku, "IBIS-SPICE Waveform Shaping: Ku/Kd factors")
        ax_ku.legend(loc="best")
        fig_ku.tight_layout()
        out_ku = OUT_DIR / "refspice_vs_pybis_rsf_kukd_separate.png"
        fig_ku.savefig(out_ku, dpi=180, bbox_inches="tight")
        plt.close(fig_ku)
        print(f"Saved: {out_ku}")

    print("Done.")


if __name__ == "__main__":
    main()
