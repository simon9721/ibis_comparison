#!/usr/bin/env python3
"""What do the transistor and native IBIS actually DO under stress?

Everything measured on the stress cases so far has been scalar -- a 50% crossing
and an RMSE. That hides the shape, and the shape turns out to matter, because
these truncated pulses are *partial excursions*: on io_buf short_high the pad
peaks at 0.57-1.22 V out of a 3.3 V rail, so none of them reach the half-swing
level a "50% crossing" would normally be measured against.

Plotting them shows something the scalars never surfaced: **native IBIS
systematically under-swings the transistor** on every width, by 60-124 mV, while
pybis tracks the peak to within 3-29 mV. That matters for how defect B is stated,
because a waveform that peaks lower reaches any fixed threshold at a different
time -- so part of "native is early, we are late" is an amplitude difference
being read as a timing difference.

    py -3.14 scripts/plot_stress_shapes.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SRC = ROOT / "results" / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
OUT = ROOT / "results" / "stress_shapes_2026-09-03"
SUPPLY = 3.3
TX, NAT, PYB = "#111111", "#2B6CA3", "#C02626"


def load(path: Path):
    rows = list(csv.DictReader(path.open()))
    col = lambda k: np.array([float(r[k]) for r in rows])  # noqa: E731
    return col("time_ns"), col("silicon_pad"), col("hspice_pad"), col("pybis_pad")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(SRC.glob("io_buf_short_high_*.csv"))
    if not files:
        print(f"no waveforms under {SRC}")
        return 1
    pick = [files[0], files[len(files) // 3], files[2 * len(files) // 3], files[-1]]

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.6))
    for ax, f in zip(axes.ravel(), pick):
        t, si, hs, py = load(f)
        width = f.stem.split("_w")[1]
        ax.plot(t, si, color=TX, lw=3.0, label="HSPICE transistor")
        ax.plot(t, hs, color=NAT, lw=2.1, ls=(0, (5, 2.2)), label="native IBIS")
        ax.plot(t, py, color=PYB, lw=2.0, ls=(0, (2, 1.6)), label="pybis (delay_cmd)")
        ax.axhline(SUPPLY / 2, color="#8A8A8A", lw=1.0, ls=":")
        ax.text(t[0] + 0.02 * (t[-1] - t[0]), SUPPLY / 2 + 0.05,
                "half swing (1.65 V) — never reached", fontsize=8.5, color="#5A5A5A")
        ax.set_title(f"io_buf short_high, {width}    "
                     f"peaks: tx {si.max():.3f}  native {hs.max():.3f}  pybis {py.max():.3f} V",
                     fontsize=10.5, fontweight="bold")
        ax.set_ylim(-0.15, max(SUPPLY / 2 + 0.25, si.max() + 0.3))
        ax.set_ylabel("Pad (V)", fontsize=10)
        ax.set_xlabel("Time (ns)", fontsize=10)
        ax.grid(alpha=0.28)
    axes[0, 0].legend(fontsize=9.5, loc="upper right")
    fig.suptitle("Stressed io_buf: the pulses are partial excursions, and native IBIS under-swings",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "stress_shapes.png", dpi=170)
    plt.close(fig)

    # peak-amplitude error across every width
    ws, en, ep = [], [], []
    for f in files:
        t, si, hs, py = load(f)
        ws.append(int(f.stem.split("_w")[1].rstrip("ps")))
        en.append((hs.max() - si.max()) * 1e3)
        ep.append((py.max() - si.max()) * 1e3)
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.axhline(0, color=TX, lw=2.2, label="HSPICE transistor (reference)")
    ax.plot(ws, en, "o-", color=NAT, lw=2.2, ms=6, label="native IBIS")
    ax.plot(ws, ep, "s-", color=PYB, lw=2.2, ms=6, label="pybis (delay_cmd)")
    ax.set_xlabel("pulse width (ps)", fontsize=11)
    ax.set_ylabel("peak error vs transistor (mV)", fontsize=11)
    ax.set_title("Peak amplitude under stress: native under-swings on every width",
                 fontsize=13, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "stress_peak_error.png", dpi=170)
    plt.close(fig)
    print(f"native peak error: {min(en):.0f} to {max(en):.0f} mV")
    print(f"pybis  peak error: {min(ep):.0f} to {max(ep):.0f} mV")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
