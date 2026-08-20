#!/usr/bin/env python3
"""Compare Ku/Kd from silicon against pybis and against HSPICE's IBIS engine.

Silicon's Ku/Kd come from applying pybis's own two-fixture solve to the
transistor rather than to an IBIS model, so for the first time the coefficients
can be compared against ground truth instead of against another model.

Four cases are chosen to show the range of outcomes rather than a flattering
subset: one where pybis is close, one where pybis tracks silicon and HSPICE's
IBIS engine does not, one where the engine invents a response silicon never
produces, and one where pybis is the weakest of the three.

Cached data only; no simulator is launched.
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
for path in (LOCAL_DEPS, ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SRC = ROOT / "results" / "silicon_kukd_recovery_2026-08-19"
SWEEP = ROOT / "results" / "three_buffer_native_anchored_stress_sweep_2026-08-19"
OUT = ROOT / "results" / "silicon_vs_pybis_kukd_figures_2026-08-19"

SILICON = "#111111"
NATIVE = "#2b6ca3"
MODEL = "#c02626"

CASES = [
    ("io_buf", "short_low", 70,
     "pybis tracks silicon's recovery; the IBIS engine clamps to the rail instead"),
    ("inv_chain", "short_high", 50,
     "silicon does not respond at all — both models invent a dip, the engine's is deeper"),
    ("io_buf", "short_high", 70,
     "all three broadly agree — the well-behaved case"),
    ("ex2", "short_low", 70,
     "silicon barely moves; both models over-respond badly, pybis later and rougher"),
]


def load(device: str, direction: str, target: int) -> dict[str, np.ndarray]:
    path = SRC / "waveforms" / f"{device}_{direction}_{target}.csv"
    if not path.exists():
        return {}
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, body = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: body[:, i] for i, name in enumerate(header)}


def reversal_ns(device: str, direction: str, target: int) -> float:
    for row in csv.DictReader((SWEEP / "selection.csv").open(newline="", encoding="utf-8")):
        if (row["device"], row["direction"]) == (device, direction) and int(float(row["target_percent"])) == target:
            base = 5.0 if direction == "short_high" else 10.0
            return base + float(row["pulse_width_ps"]) / 1000.0
    return float("nan")


def crop(t: np.ndarray, t_rev: float, direction: str) -> np.ndarray:
    edge = 5.0 if direction == "short_high" else 10.0
    return (t >= edge - 0.15) & (t <= t_rev + 3.2)


def draw(axis, t, window, series, t_rev, ylabel):
    for name, colour, width, values in series:
        axis.plot(t[window], values[window], color=colour, lw=width, label=name, zorder=3)
    axis.axvline(t_rev, color="0.45", ls="--", lw=1.1, zorder=1)
    axis.axhspan(-0.05, 1.05, color="0.93", zorder=0)
    # The two-fixture solve goes briefly ill-conditioned at the sharp input
    # edge, where both devices are near off and the fixtures stop giving
    # independent information. Those few-picosecond spikes reach several times
    # the signal and would otherwise flatten every real feature in the panel,
    # so the view is set from the bulk of the data and the spikes clip.
    stacked = np.concatenate([values[window] for _, _, _, values in series])
    finite = stacked[np.isfinite(stacked)]
    if len(finite):
        low, high = np.percentile(finite, [0.5, 99.5])
        pad = max(0.12, 0.10 * (high - low))
        axis.set_ylim(min(low - pad, -0.15), max(high + pad, 1.15))
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.25, zorder=0)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)
    made = 0

    fig_all, axes_all = plt.subplots(2, 2, figsize=(15.0, 8.4))
    for slot, (device, direction, target, headline) in enumerate(CASES):
        data = load(device, direction, target)
        if not data:
            print(f"missing: {device} {direction} {target}")
            continue
        t = data["time_ns"]
        t_rev = reversal_ns(device, direction, target)
        window = crop(t, t_rev, direction)
        # The coefficient that was on and must come back is the interesting one.
        coeff = "kd" if direction == "short_high" else "ku"

        fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.2), sharex=True)
        for axis, which in zip(axes, ("ku", "kd")):
            draw(axis, t, window, [
                ("silicon (transistor)", SILICON, 2.8, data[f"silicon_{which}"]),
                ("HSPICE native IBIS", NATIVE, 1.7, data[f"native_{which}"]),
                ("pybis gate-state", MODEL, 1.7, data[f"model_{which}"]),
            ], t_rev, which.replace("k", "K"))
        axes[0].set_title(f"{device}  {direction.replace('_', '-')}  {target}% — {headline}",
                          fontsize=11)
        axes[0].legend(fontsize=9, ncol=3, loc="best")
        axes[1].set_xlabel("Time (ns)")
        axes[1].annotate("reverse edge", xy=(t_rev, axes[1].get_ylim()[0]),
                         xytext=(6, 6), textcoords="offset points", fontsize=8, color="0.35")
        fig.tight_layout()
        fig.savefig(OUT / "plots" / f"{slot + 1:02d}_{device}_{direction}_{target}.png", dpi=160)
        plt.close(fig)
        made += 1

        axis = axes_all[slot // 2][slot % 2]
        draw(axis, t, window, [
            ("silicon (transistor)", SILICON, 2.6, data[f"silicon_{coeff}"]),
            ("HSPICE native IBIS", NATIVE, 1.6, data[f"native_{coeff}"]),
            ("pybis gate-state", MODEL, 1.6, data[f"model_{coeff}"]),
        ], t_rev, coeff.replace("k", "K"))
        axis.set_title(f"{device} {direction.replace('_', '-')} {target}%\n{headline}", fontsize=9.5)
        axis.set_xlabel("Time (ns)")
        if slot == 0:
            axis.legend(fontsize=8.5, loc="best")

    fig_all.suptitle(
        "Ku/Kd during an interrupted pulse: silicon vs pybis vs HSPICE's IBIS engine\n"
        "(the coefficient shown is the device that was on, was partly turned off, and must return)",
        fontsize=11.5)
    fig_all.tight_layout(rect=(0, 0, 1, 0.93))
    fig_all.savefig(OUT / "plots" / "00_summary_four_cases.png", dpi=160)
    plt.close(fig_all)

    print(f"figures: {made + 1}")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
