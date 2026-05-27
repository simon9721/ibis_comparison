"""
Long-hold RSF comparison plot using two separate raw files.

Loads:
  - ngspice_refspice/tb_validation_refspice_rsf_longhold_batch.raw
  - ngspice_pybis/tb_validation_rsf_longhold_ngspice_pybis_batch.raw

Both benches use the same long-hold RSF stimulus:
  - Rise at ~1ns (5ps edges)
  - High until ~21ns
  - Fall at ~21ns
"""

from pathlib import Path

import matplotlib.pyplot as plt

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
RAW_REF = ROOT / "ngspice_refspice" / "tb_validation_refspice_rsf_longhold_batch.raw"
RAW_PYBIS = ROOT / "ngspice_pybis" / "tb_validation_rsf_longhold_ngspice_pybis_batch.raw"
OUT_DIR = ROOT / "plots" / "validation"

EXPECTED_STOP_NS = 24.0
MIN_VALID_STOP_NS = 23.0


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

    ref = parse_ngspice_raw(RAW_REF)
    ref_last = check_raw(ref, "refspice longhold RSF")

    pybis = parse_ngspice_raw(RAW_PYBIS)
    pybis_last = check_raw(pybis, "pybis longhold RSF")

    t_max_ns = min(ref_last, pybis_last, EXPECTED_STOP_NS)
    time_ref_ns = ns(ref["time"])
    time_pybis_ns = ns(pybis["time"])
    ref_mask = time_ref_ns <= t_max_ns + 0.001
    pybis_mask = time_pybis_ns <= t_max_ns + 0.001

    plt.rcParams.update({
        "figure.figsize": (11, 5.5),
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    fig_pad, ax_pad = plt.subplots()
    ax_pad.plot(
        time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask],
        label="Reference SPICE pad", linewidth=2.0
    )
    ax_pad.plot(
        time_pybis_ns[pybis_mask], pybis["v(pad)"][pybis_mask],
        label="Converted IBIS-SPICE pad", linewidth=2.0, linestyle="--"
    )
    ax_pad.plot(
        time_ref_ns[ref_mask], ref["v(in_dig)"][ref_mask],
        "--", label="Input (shared)", linewidth=1.5, alpha=0.8, color="gray"
    )
    style_axis(ax_pad, "Long-Hold RSF Pad Comparison: Reference SPICE vs Converted IBIS-SPICE")
    ax_pad.legend(loc="best")
    fig_pad.tight_layout()
    out_pad = OUT_DIR / "refspice_vs_pybis_rsf_longhold_pad_separate.png"
    fig_pad.savefig(out_pad, dpi=180, bbox_inches="tight")
    plt.close(fig_pad)
    print(f"Saved: {out_pad}")

    fig_load, ax_load = plt.subplots()
    ax_load.plot(
        time_ref_ns[ref_mask], ref["v(ntst_ref)"][ref_mask],
        label="Reference SPICE load", linewidth=2.0
    )
    ax_load.plot(
        time_pybis_ns[pybis_mask], pybis["v(ntst)"][pybis_mask],
        label="Converted IBIS-SPICE load", linewidth=2.0, linestyle="--"
    )
    ax_load.plot(
        time_ref_ns[ref_mask], ref["v(in_dig)"][ref_mask],
        "--", label="Input (shared)", linewidth=1.5, alpha=0.8, color="gray"
    )
    style_axis(ax_load, "Long-Hold RSF Load Comparison: Reference SPICE vs Converted IBIS-SPICE")
    ax_load.legend(loc="best")
    fig_load.tight_layout()
    out_load = OUT_DIR / "refspice_vs_pybis_rsf_longhold_load_separate.png"
    fig_load.savefig(out_load, dpi=180, bbox_inches="tight")
    plt.close(fig_load)
    print(f"Saved: {out_load}")


if __name__ == "__main__":
    main()
