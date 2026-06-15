from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_ngspice_raw  # noqa: E402


DEFAULT_DRIVER_RAW = ROOT / "hspice" / "sparam_ngspice" / "tb_ibis_sparam_batch_vector_3r3c.raw"
DEFAULT_SWEEP_DIR = (
    ROOT / "hspice" / "sparam_ngspice" / "regenerated_skrf" / "vector_3r3c" / "channel_sweep"
)
DEFAULT_OUT = ROOT / "hspice" / "sparam_ngspice" / "regenerated_skrf" / "plots"


def ns(raw: dict[str, np.ndarray]) -> np.ndarray:
    return raw["time"] * 1e9


def setup_axes(ax: plt.Axes, title: str, ylabel: str = "Voltage (V)") -> None:
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, which="major", color="#d7dde6", linewidth=0.8)
    ax.grid(True, which="minor", color="#eef1f5", linewidth=0.5)
    ax.minorticks_on()


def plot_driver_full(raw_path: Path, out_path: Path) -> None:
    raw = parse_ngspice_raw(raw_path)
    t = ns(raw)

    fig, axes = plt.subplots(2, 1, figsize=(11, 7.2), sharex=True, constrained_layout=True)
    fig.suptitle("ngspice + passive scikit-rf S-parameter channel", fontsize=15, fontweight="bold")

    axes[0].plot(t, raw["v(in_dig)"], color="#555555", linewidth=1.8, label="digital input")
    setup_axes(axes[0], "Stimulus", "Voltage (V)")
    axes[0].set_ylim(-0.2, 3.5)
    axes[0].legend(loc="upper right", frameon=False)

    axes[1].plot(t, raw["v(pad)"], color="#0067b1", linewidth=1.8, label="driver pad")
    axes[1].plot(t, raw["v(ntst)"], color="#c43c2f", linewidth=1.8, label="receiver / channel output")
    setup_axes(axes[1], "Channel Waveforms")
    axes[1].set_xlim(0, 12)
    axes[1].set_ylim(-0.25, 1.75)
    axes[1].legend(loc="upper right", frameon=False)

    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_driver_edges(raw_path: Path, out_path: Path) -> None:
    raw = parse_ngspice_raw(raw_path)
    t = ns(raw)
    pad = raw["v(pad)"]
    threshold = 0.5 * (float(np.nanmin(pad)) + float(np.nanmax(pad)))

    rise_idx = np.where((pad[:-1] < threshold) & (pad[1:] >= threshold))[0]
    fall_idx = np.where((pad[:-1] >= threshold) & (pad[1:] < threshold))[0]
    rise_center = float(t[rise_idx[0]]) if len(rise_idx) else 3.5
    fall_candidates = [idx for idx in fall_idx if t[idx] > 8.0]
    fall_center = float(t[fall_candidates[0]]) if fall_candidates else 10.0

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    fig.suptitle("Passive S-parameter channel: edge detail", fontsize=15, fontweight="bold")

    for ax, title, xlim in (
        (axes[0], "Rising Edge", (rise_center - 1.1, rise_center + 1.9)),
        (axes[1], "Falling Edge", (fall_center - 0.9, fall_center + 1.1)),
    ):
        ax.plot(t, raw["v(pad)"], color="#0067b1", linewidth=2.0, label="driver pad")
        ax.plot(t, raw["v(ntst)"], color="#c43c2f", linewidth=2.0, label="receiver / channel output")
        setup_axes(ax, title)
        ax.set_xlim(*xlim)
        ax.set_ylim(-0.25, 1.75)
        ax.legend(loc="best", frameon=False)

    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def load_case(sweep_dir: Path, name: str) -> dict[str, np.ndarray]:
    return parse_ngspice_raw(sweep_dir / f"{name}.raw")


def plot_channel_sweep(sweep_dir: Path, out_path: Path) -> None:
    cases = [
        ("amp1p5_edge5_ideal", "5 ps edge, ideal source", "#0067b1"),
        ("amp1p5_edge5_r50", "5 ps edge, 50 ohm source", "#c43c2f"),
        ("amp1p5_edge500_ideal", "500 ps edge, ideal source", "#008751"),
        ("amp1p5_edge500_r50", "500 ps edge, 50 ohm source", "#7a4cc2"),
    ]

    fig, axes = plt.subplots(2, 1, figsize=(11, 7.0), sharex=True, constrained_layout=True)
    fig.suptitle("Passive channel-only smoke cases", fontsize=15, fontweight="bold")

    for name, label, color in cases:
        raw = load_case(sweep_dir, name)
        t = ns(raw)
        axes[0].plot(t, raw["v(pad)"], color=color, linewidth=1.6, label=label)
        axes[1].plot(t, raw["v(ntst)"], color=color, linewidth=1.6, label=label)

    setup_axes(axes[0], "Input Port")
    axes[0].set_ylim(-0.2, 1.65)
    axes[0].legend(loc="upper right", frameon=False, fontsize=9)

    setup_axes(axes[1], "Output Port")
    axes[1].set_xlim(0, 12)
    axes[1].set_ylim(-0.35, 1.9)
    axes[1].legend(loc="upper right", frameon=False, fontsize=9)

    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot passive scikit-rf S-param ngspice smoke results.")
    parser.add_argument("--driver-raw", type=Path, default=DEFAULT_DRIVER_RAW)
    parser.add_argument("--sweep-dir", type=Path, default=DEFAULT_SWEEP_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    outputs = [
        args.out / "passive_driver_full.png",
        args.out / "passive_driver_edges.png",
        args.out / "passive_channel_sweep.png",
    ]

    plot_driver_full(args.driver_raw, outputs[0])
    plot_driver_edges(args.driver_raw, outputs[1])
    plot_channel_sweep(args.sweep_dir, outputs[2])

    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
