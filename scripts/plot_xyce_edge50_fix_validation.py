"""Plot Xyce edge50 Gear fix validation overlays."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "xyce_edge50_prbs80_fix_validation_2026-05-12"
PLOTS_DIR = OUT_DIR / "plots"

SERIES = [
    (
        "baseline trap timeout",
        ROOT
        / "results"
        / "edge_family_stress_crossflow_coarse10_80b_edge50_2026-05-11"
        / "runs"
        / "ui2_len30cm_loss5_coarse10"
        / "xyce_pybis"
        / "ui2_len30cm_loss5_coarse10_xyce_pybis.cir.csv",
        "#7f7f7f",
    ),
    (
        "gear1 nl8 pass",
        OUT_DIR / "runs" / "gear1_nl8" / "gear1_nl8.cir.csv",
        "#1f77b4",
    ),
    (
        "gear2 nl50 pass",
        OUT_DIR / "runs" / "gear2_nl50" / "gear2_nl50.cir.csv",
        "#2ca02c",
    ),
]


def load_xyce_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = [h.lower() for h in next(reader)]
        rows = []
        for row in reader:
            try:
                rows.append([float(x) for x in row])
            except ValueError:
                continue
    arr = np.asarray(rows, dtype=float)
    return {name: arr[:, i] for i, name in enumerate(header)}


def key(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    for name in names:
        if name.lower() in data:
            return data[name.lower()]
    raise KeyError(names)


def plot_window(data_sets: list[tuple[str, dict[str, np.ndarray], str]]) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True)
    for label, data, color in data_sets:
        t_ns = key(data, "time") * 1e9
        mask = (t_ns >= 118.0) & (t_ns <= 130.0)
        axes[0].plot(t_ns[mask], key(data, "v(pad)")[mask], label=label, color=color, lw=1.4)
        axes[1].plot(t_ns[mask], key(data, "v(n10b)")[mask], label=label, color=color, lw=1.4)
        axes[2].plot(t_ns[mask], key(data, "v(xdrv:nx)")[mask], label=label, color=color, lw=1.4)

    for ax in axes:
        ax.axvline(122.0, color="#d62728", ls="--", lw=1.0, alpha=0.8)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=8)
    axes[0].set_ylabel("pad V")
    axes[1].set_ylabel("rx V")
    axes[2].set_ylabel("NX ns")
    axes[2].set_xlabel("Time (ns)")
    fig.suptitle("Xyce edge50 PRBS80: Gear fix through the 122 ns stall region")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(PLOTS_DIR / "prbs80_gear_fix_122ns_window.png", dpi=180)
    plt.close(fig)


def plot_full_rx(data_sets: list[tuple[str, dict[str, np.ndarray], str]]) -> None:
    fig, ax = plt.subplots(figsize=(13, 4.5))
    for label, data, color in data_sets:
        t_ns = key(data, "time") * 1e9
        ax.plot(t_ns, key(data, "v(n10b)"), label=label, color=color, lw=1.0)

    ax.axvline(122.0, color="#d62728", ls="--", lw=1.0, alpha=0.8)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("rx V")
    ax.set_title("Xyce edge50 PRBS80 receiver transient: baseline timeout vs Gear pass")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "prbs80_gear_fix_full_rx_overlay.png", dpi=180)
    plt.close(fig)


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data_sets = [(label, load_xyce_csv(path), color) for label, path, color in SERIES]
    plot_window(data_sets)
    plot_full_rx(data_sets)
    print(f"Wrote {PLOTS_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
