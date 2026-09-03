from pathlib import Path

import matplotlib.pyplot as plt

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "ngspice_pybis" / "tb_validation_rfr_ngspice_pybis_batch.raw"
OUT_DIR = ROOT / "plots" / "validation"


def ns(time_s):
    return time_s * 1e9


def style_axis(ax, title, ylabel="V"):
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = parse_ngspice_raw(RAW)
    time_ns = ns(data["time"])

    plt.rcParams.update({
        "figure.figsize": (11, 8),
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    fig, axes = plt.subplots(2, 1, sharex=False)

    axes[0].plot(time_ns, data["v(in_dig)"], "--", label="Input", linewidth=1.5, alpha=0.9)
    axes[0].plot(time_ns, data["v(pad)"], label="Pad", linewidth=2.0)
    axes[0].plot(time_ns, data["v(ntst)"], label="Load", linewidth=2.0)
    style_axis(axes[0], "pybis2spice Rise-Fall-Rise Validation")
    axes[0].legend(loc="best")

    axes[1].plot(time_ns, data["v(xdrv.ku)"], label="Ku", linewidth=2.0)
    axes[1].plot(time_ns, data["v(xdrv.kd)"], label="Kd", linewidth=2.0)
    style_axis(axes[1], "pybis2spice Rise-Fall-Rise Coefficients")
    axes[1].legend(loc="best")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "validation_rfr_outputs.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(OUT_DIR / "validation_rfr_outputs.png")


if __name__ == "__main__":
    main()
