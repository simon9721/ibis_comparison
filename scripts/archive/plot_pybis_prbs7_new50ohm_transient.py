from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "ngspice_pybis" / "tb_pybis_prbs7_new50ohm.raw"
OUT_DIR = ROOT / "plots" / "validation"
OUT_PNG = OUT_DIR / "pybis_prbs7_new50ohm_chin_vs_load.png"
EXPECTED_STOP_S = 1000e-9
MIN_VALID_STOP_S = 990e-9


def ns(time_s):
    return time_s * 1e9


def require_complete_run(data):
    if len(data["time"]) == 0:
        raise RuntimeError("Raw has no transient points")
    last_time = float(data["time"][-1])
    if last_time < MIN_VALID_STOP_S:
        raise RuntimeError(
            f"Raw ended at {last_time * 1e9:.3f} ns, expected about {EXPECTED_STOP_S * 1e9:.3f} ns"
        )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = parse_ngspice_raw(RAW)
    require_complete_run(data)

    t_ns = ns(data["time"])

    plt.rcParams.update(
        {
            "figure.figsize": (12, 6),
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
        }
    )

    fig, ax = plt.subplots()
    ax.plot(t_ns, data["v(tx_out)"], linewidth=1.4, label="Channel input v(tx_out)")
    ax.plot(t_ns, data["v(n10b)"], linewidth=1.8, label="Load node v(n10b)")

    ax.set_title("pybis2spice PRBS7 Transient: Channel Input vs Load")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(OUT_PNG)


if __name__ == "__main__":
    main()
