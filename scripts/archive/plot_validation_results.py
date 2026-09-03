from pathlib import Path
import struct

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
SPISIM_DIR = ROOT / "SimIbis_FreeSpice_From_SPISim"
NG_DIR = ROOT / "ngspice_pybis"
OUT_DIR = ROOT / "plots" / "validation"


def parse_ngspice_raw(path: Path):
    data = path.read_bytes()
    marker = b"Binary:\n"
    idx = data.find(marker)
    if idx < 0:
        raise RuntimeError(f"Binary marker not found in {path}")

    header = data[:idx].decode("latin1")
    lines = header.splitlines()

    nvars = None
    npts = None
    variables = []
    reading_vars = False

    for line in lines:
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":", 1)[1])
        elif line.strip() == "Variables:":
            reading_vars = True
        elif reading_vars and line.startswith("\t"):
            variables.append(line.split()[1])

    if nvars is None or npts is None or len(variables) != nvars:
        raise RuntimeError(f"Could not parse ngspice raw header for {path}")

    payload = data[idx + len(marker):]
    # npts=0 in header is a known ngspice quirk when data is present; derive from file size
    if npts == 0:
        npts = len(payload) // (8 * nvars)
    values = struct.unpack("<" + "d" * (nvars * npts), payload[: 8 * nvars * npts])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))

    return {name: arr[:, i] for i, name in enumerate(variables)}


def ns(time_s):
    return time_s * 1e9


def style_axis(ax, title, ylabel="V"):
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    coef = parse_ngspice_raw(SPISIM_DIR / "Ibs2Spc_Coef.raw")
    ramp = parse_ngspice_raw(SPISIM_DIR / "Ibs2Spc_Ramp.raw")
    ours = parse_ngspice_raw(NG_DIR / "tb_validation_pulse_ngspice_pybis_batch.raw")

    plt.rcParams.update({
        "figure.figsize": (11, 11.5),
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    fig1, axes = plt.subplots(3, 1, sharex=False)

    axes[0].plot(ns(coef["time"]), coef["v(ninp)"], label="Input")
    axes[0].plot(ns(coef["time"]), coef["v(nout)"], label="Output")
    axes[0].plot(ns(coef["time"]), coef["v(ntst)"], label="Load")
    style_axis(axes[0], "SPISim Waveform-Based Validation")
    axes[0].legend(loc="best")

    axes[1].plot(ns(ramp["time"]), ramp["v(ninp)"], label="Input")
    axes[1].plot(ns(ramp["time"]), ramp["v(nout)"], label="Output")
    axes[1].plot(ns(ramp["time"]), ramp["v(ntst)"], label="Load")
    style_axis(axes[1], "SPISim Ramp-Based Validation")
    axes[1].legend(loc="best")

    axes[2].plot(ns(ours["time"]), ours["v(in_dig)"], label="Input")
    axes[2].plot(ns(ours["time"]), ours["v(pad)"], label="Output")
    axes[2].plot(ns(ours["time"]), ours["v(ntst)"], label="Load")
    style_axis(axes[2], "pybis2spice -> ngspice Validation")
    axes[2].legend(loc="best")

    fig1.suptitle("Short Validation Benches", y=0.99, fontsize=14)
    fig1.tight_layout(rect=[0, 0, 1, 0.97])
    fig1.savefig(OUT_DIR / "validation_outputs_comparison.png", dpi=160, bbox_inches="tight")
    plt.close(fig1)

    fig2, axes2 = plt.subplots(2, 1, sharex=False)

    axes2[0].plot(ns(coef["time"]), coef["v(xibis.nkux)"], label="NKUX")
    axes2[0].plot(ns(coef["time"]), coef["v(xibis.nkdx)"], label="NKDX")
    style_axis(axes2[0], "SPISim Effective Switching Coefficients")
    axes2[0].legend(loc="best")

    axes2[1].plot(ns(ours["time"]), ours["v(xdrv.ku)"], label="Ku")
    axes2[1].plot(ns(ours["time"]), ours["v(xdrv.kd)"], label="Kd")
    style_axis(axes2[1], "pybis2spice Effective Switching Coefficients")
    axes2[1].legend(loc="best")

    fig2.suptitle("Coefficient Behavior Comparison", y=0.99, fontsize=14)
    fig2.tight_layout(rect=[0, 0, 1, 0.97])
    fig2.savefig(OUT_DIR / "validation_coefficients_comparison.png", dpi=160, bbox_inches="tight")
    plt.close(fig2)

    print("Wrote:")
    print(OUT_DIR / "validation_outputs_comparison.png")
    print(OUT_DIR / "validation_coefficients_comparison.png")


if __name__ == "__main__":
    main()
