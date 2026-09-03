from pathlib import Path

import matplotlib.pyplot as plt

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "ngspice_refspice" / "tb_validation_refspice_rsf_batch.raw"
OUT_DIR = ROOT / "plots" / "validation"
EXPECTED_STOP_S = 14e-9
MIN_VALID_STOP_S = 13e-9


def ns(time_s):
    return time_s * 1e9


def style_axis(ax, title, ylabel="V"):
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def require_complete_run(data):
    if len(data["time"]) == 0:
        raise RuntimeError("Incomplete raw for reference-only RSF validation: no usable transient points were written.")
    last_time = float(data["time"][-1])
    if last_time < MIN_VALID_STOP_S:
        raise RuntimeError(
            f"Incomplete raw for reference-only RSF validation: ended at {last_time * 1e9:.3f} ns, "
            f"expected about {EXPECTED_STOP_S * 1e9:.3f} ns. Refusing to generate a misleading plot."
        )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = parse_ngspice_raw(RAW)
    require_complete_run(data)
    time_ns = ns(data["time"])

    plt.rcParams.update({
        "figure.figsize": (11, 5.5),
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    fig, ax = plt.subplots()
    ax.plot(time_ns, data["v(pad_ref)"], label="Reference SPICE pad", linewidth=2.0)
    ax.plot(time_ns, data["v(ntst_ref)"], label="Reference SPICE load", linewidth=2.0)
    ax.plot(time_ns, data["v(in_dig)"], "--", label="Input", linewidth=1.5, alpha=0.9)
    style_axis(ax, "Reference SPICE Rise-Steady-Fall Validation")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "refspice_only_rsf.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(OUT_DIR / "refspice_only_rsf.png")


if __name__ == "__main__":
    main()
