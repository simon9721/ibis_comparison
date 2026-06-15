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

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402


DEFAULT_HSPICE_TR0 = ROOT / "hspice" / "sparam" / "tb_ibis_sparam.tr0"
DEFAULT_NGSPICE_RAW = ROOT / "hspice" / "sparam_ngspice" / "tb_ibis_sparam_batch_vector_3r3c.raw"
DEFAULT_OUT = ROOT / "hspice" / "sparam_ngspice" / "regenerated_skrf" / "plots"


def crossing(t: np.ndarray, y: np.ndarray, threshold: float, direction: str, after: float) -> float:
    if direction == "rise":
        candidates = np.where((y[:-1] < threshold) & (y[1:] >= threshold))[0]
    elif direction == "fall":
        candidates = np.where((y[:-1] >= threshold) & (y[1:] < threshold))[0]
    else:
        raise ValueError(direction)
    candidates = [idx for idx in candidates if t[idx] >= after]
    if not candidates:
        return float("nan")
    idx = candidates[0]
    t0, t1 = float(t[idx]), float(t[idx + 1])
    y0, y1 = float(y[idx]), float(y[idx + 1])
    if y1 == y0:
        return t0
    return t0 + (threshold - y0) * (t1 - t0) / (y1 - y0)


def setup(ax: plt.Axes, title: str) -> None:
    ax.set_title(title, loc="left", fontsize=10.5, fontweight="bold")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, which="major", color="#d7dde6", linewidth=0.8)
    ax.grid(True, which="minor", color="#eef1f5", linewidth=0.5)
    ax.minorticks_on()


def plot_compare(hspice_tr0: Path, ngspice_raw: Path, out_path: Path) -> dict[str, float]:
    h = parse_hspice_tr0(hspice_tr0)
    n = parse_ngspice_raw(ngspice_raw)

    ht = h["time"] * 1e9
    nt = n["time"] * 1e9
    threshold = 0.75

    pairs = [
        ("Driver Pad", h["v(pad_ibis)"], n["v(pad)"], 2.2, 5.2, 9.2, 10.7),
        ("Receiver Node", h["v(rx_node)"], n["v(ntst)"], 2.7, 5.6, 9.5, 10.9),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14.5, 7.4), constrained_layout=True)
    fig.suptitle(
        "HSPICE native IBIS/S-param vs ngspice pybis/passive scikit-rf S-param",
        fontsize=14,
        fontweight="bold",
    )

    for row, (title, hy, ny, r0, r1, f0, f1) in enumerate(pairs):
        for col, (subtitle, xlim) in enumerate(
            [
                ("Full Waveform", (0, 12)),
                ("Rising Edge", (r0, r1)),
                ("Falling Edge", (f0, f1)),
            ]
        ):
            ax = axes[row][col]
            ax.plot(ht, hy, color="#1f5a99", linewidth=1.9, label="HSPICE")
            ax.plot(nt, ny, color="#cf4337", linewidth=1.7, linestyle="--", label="ngspice")
            if col:
                ax.axhline(threshold, color="#555555", linewidth=0.8, linestyle=":", label="0.75 V")
            setup(ax, f"{title}: {subtitle}")
            ax.set_xlim(*xlim)
            ax.set_ylim(-0.22, 1.72)
            if row == 0 and col == 0:
                ax.legend(loc="lower right", frameon=False)
            elif row == 0 and col == 1:
                ax.legend(loc="lower right", frameon=False)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)

    metrics = {}
    for prefix, t, pad, rx in (
        ("hspice", h["time"], h["v(pad_ibis)"], h["v(rx_node)"]),
        ("ngspice", n["time"], n["v(pad)"], n["v(ntst)"]),
    ):
        metrics[f"{prefix}_pad_rise50_ns"] = crossing(t, pad, threshold, "rise", 1e-9) * 1e9
        metrics[f"{prefix}_rx_rise50_ns"] = crossing(t, rx, threshold, "rise", 1e-9) * 1e9
        metrics[f"{prefix}_pad_fall50_ns"] = crossing(t, pad, threshold, "fall", 9e-9) * 1e9
        metrics[f"{prefix}_rx_fall50_ns"] = crossing(t, rx, threshold, "fall", 9e-9) * 1e9
        metrics[f"{prefix}_pad_min_v"] = float(np.nanmin(pad))
        metrics[f"{prefix}_pad_max_v"] = float(np.nanmax(pad))
        metrics[f"{prefix}_rx_min_v"] = float(np.nanmin(rx))
        metrics[f"{prefix}_rx_max_v"] = float(np.nanmax(rx))

    metrics["hspice_rx_pad_rise_delay_ps"] = (
        metrics["hspice_rx_rise50_ns"] - metrics["hspice_pad_rise50_ns"]
    ) * 1e3
    metrics["ngspice_rx_pad_rise_delay_ps"] = (
        metrics["ngspice_rx_rise50_ns"] - metrics["ngspice_pad_rise50_ns"]
    ) * 1e3
    metrics["hspice_rx_pad_fall_delay_ps"] = (
        metrics["hspice_rx_fall50_ns"] - metrics["hspice_pad_fall50_ns"]
    ) * 1e3
    metrics["ngspice_rx_pad_fall_delay_ps"] = (
        metrics["ngspice_rx_fall50_ns"] - metrics["ngspice_pad_fall50_ns"]
    ) * 1e3
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot HSPICE vs ngspice passive S-param comparison.")
    parser.add_argument("--hspice-tr0", type=Path, default=DEFAULT_HSPICE_TR0)
    parser.add_argument("--ngspice-raw", type=Path, default=DEFAULT_NGSPICE_RAW)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT / "hspice_vs_ngspice_passive_sparam.png",
    )
    args = parser.parse_args()

    metrics = plot_compare(args.hspice_tr0, args.ngspice_raw, args.out)
    print(args.out)
    for key in sorted(metrics):
        print(f"{key},{metrics[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
