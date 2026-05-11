from pathlib import Path

import matplotlib.pyplot as plt

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
RAW_REF = ROOT / "ngspice_refspice" / "tb_validation_refspice_fallonly_batch.raw"
RAW_IBIS = ROOT / "ngspice_pybis" / "tb_validation_fallonly_ngspice_pybis_batch.raw"
OUT_DIR = ROOT / "plots" / "validation"
EXPECTED_STOP_S = 8e-9
MIN_VALID_STOP_S = 7e-9


def ns(time_s):
    return time_s * 1e9


def style_axis(ax, title, ylabel="V"):
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def require_complete_run(data, label):
    if len(data["time"]) == 0:
        raise RuntimeError(f"Incomplete raw for {label}: no usable transient points were written.")
    last_time = float(data["time"][-1])
    if last_time < MIN_VALID_STOP_S:
        raise RuntimeError(
            f"Incomplete raw for {label}: ended at {last_time * 1e9:.3f} ns, "
            f"expected about {EXPECTED_STOP_S * 1e9:.3f} ns. Refusing to generate a misleading plot."
        )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ref = parse_ngspice_raw(RAW_REF)
    ibis = parse_ngspice_raw(RAW_IBIS)
    require_complete_run(ref, "reference fall-only comparison")
    require_complete_run(ibis, "converted fall-only comparison")

    plt.rcParams.update({
        "figure.figsize": (11, 5.5),
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    fig_pad, ax_pad = plt.subplots()
    ax_pad.plot(ns(ref["time"]), ref["v(pad_ref)"], label="Reference SPICE pad", linewidth=2.0)
    ax_pad.plot(ns(ibis["time"]), ibis["v(pad)"], label="Converted IBIS-SPICE pad", linewidth=2.0)
    ax_pad.plot(ns(ref["time"]), ref["v(in_dig)"], "--", label="Input", linewidth=1.5, alpha=0.9)
    style_axis(ax_pad, "Falling-Edge Comparison: Reference SPICE vs Converted IBIS-SPICE")
    ax_pad.legend(loc="best")
    fig_pad.tight_layout()
    fig_pad.savefig(OUT_DIR / "refspice_vs_pybis_fallonly_pad.png", dpi=180, bbox_inches="tight")
    plt.close(fig_pad)

    fig_load, ax_load = plt.subplots()
    ax_load.plot(ns(ref["time"]), ref["v(ntst_ref)"], label="Reference SPICE load", linewidth=2.0)
    ax_load.plot(ns(ibis["time"]), ibis["v(ntst)"], label="Converted IBIS-SPICE load", linewidth=2.0)
    ax_load.plot(ns(ref["time"]), ref["v(in_dig)"], "--", label="Input", linewidth=1.5, alpha=0.9)
    style_axis(ax_load, "Falling-Edge Load Comparison: Reference SPICE vs Converted IBIS-SPICE")
    ax_load.legend(loc="best")
    fig_load.tight_layout()
    fig_load.savefig(OUT_DIR / "refspice_vs_pybis_fallonly_load.png", dpi=180, bbox_inches="tight")
    plt.close(fig_load)

    print(OUT_DIR / "refspice_vs_pybis_fallonly_pad.png")
    print(OUT_DIR / "refspice_vs_pybis_fallonly_load.png")


if __name__ == "__main__":
    main()
