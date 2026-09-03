"""
Overlay original refspice and no-coupling refspice RSF pad waveforms.
This isolates how much of the edge spike is caused by the explicit
control-to-output parasitic caps in io_buf.sp.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
RAW_ORIG = ROOT / "ngspice_refspice" / "tb_validation_refspice_rsf_batch.raw"
RAW_NC = ROOT / "ngspice_refspice" / "tb_validation_refspice_rsf_nocoupling_batch.raw"
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
    orig = parse_ngspice_raw(RAW_ORIG)
    nc = parse_ngspice_raw(RAW_NC)

    plt.rcParams.update({
        "figure.figsize": (11, 5.5),
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    for tag, xlim in [("rise_zoom", (0.95, 1.45)), ("fall_zoom", (8.95, 9.45)), ("full", (0.0, 12.0))]:
        fig, ax = plt.subplots()
        ax.plot(ns(orig["time"]), orig["v(pad_ref)"], label="Reference SPICE pad", linewidth=2.0)
        ax.plot(ns(nc["time"]), nc["v(pad_ref)"], label="Reference SPICE pad (no explicit n2/n3->out caps)", linewidth=2.0, linestyle="--")
        ax.plot(ns(orig["time"]), orig["v(in_dig)"], "--", label="Input", linewidth=1.5, alpha=0.8, color="gray")
        ax.set_xlim(*xlim)
        title = {
            "rise_zoom": "Reference SPICE Rise Zoom: original vs no explicit coupling caps",
            "fall_zoom": "Reference SPICE Fall Zoom: original vs no explicit coupling caps",
            "full": "Reference SPICE RSF: original vs no explicit coupling caps",
        }[tag]
        style_axis(ax, title)
        ax.legend(loc="best")
        fig.tight_layout()
        out = OUT_DIR / f"refspice_original_vs_nocoupling_rsf_{tag}.png"
        fig.savefig(out, dpi=180, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
