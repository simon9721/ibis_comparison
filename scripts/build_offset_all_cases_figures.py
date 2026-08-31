#!/usr/bin/env python3
"""Figure 13, repeated for every stress case that has both builds.

One figure per case: the full response above, the post-reversal tail below, with
the transistor, native IBIS, the shipped gate-state model and the level-driven
command on the same axes. The restore-term probe only exists for the five
io_buf short-high targets, so it appears on those and is absent elsewhere.

The reversal is located from the data rather than assumed, because short-high
and short-low start their edges at different times: the first sample where the
transistor pad leaves its initial level by 5% of the record's full range is the
edge, and the reversal is one pulse width later.

The tail measurement is the mean absolute gap to the transistor between the
reversal + 1.0 ns and + 1.7 ns. On io_buf that window sits after the pad has
discharged and before the pulldown finally engages at + 1.83 ns, so it reads the
stranded-charge pedestal and nothing else.

    py -3.14 scripts/build_offset_all_cases_figures.py
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
FIX = ROOT / "results" / "settled_offset_diagnosis_2026-08-27" / "fix_probe"
OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27" / "all_cases"

SILICON = "#111111"
NATIVE = "#2B6CA3"
SHIPPED = "#C05621"
RESTORE = "#7B2CBF"
LEVEL = "#1B6B4F"
DPI = 160

DEVICE_ORDER = {"io_buf": 0, "inv_chain": 1, "ex2": 2}
DIR_ORDER = {"short_high": 0, "short_low": 1}


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) if x not in ("", "nan") else np.nan for x in r]
                       for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(rows[0])}


def reversal_ns(time_ns: np.ndarray, pad: np.ndarray, width_ns: float) -> float:
    """Edge detected from the transistor pad, plus one pulse width."""
    finite = np.isfinite(pad)
    t, y = time_ns[finite], pad[finite]
    span = float(np.nanmax(y) - np.nanmin(y))
    if span <= 0:
        return float(t[0]) + width_ns
    moved = np.where(np.abs(y - y[0]) > 0.05 * span)[0]
    edge = float(t[moved[0]]) if len(moved) else float(t[0])
    return edge + width_ns


def restore_probe(device: str, direction: str, width_ps: int):
    """The restore-term run, which exists only for io_buf short-high."""
    if device != "io_buf" or direction != "short_high":
        return None
    hits = list(FIX.glob(f"gate_and_tau_swing*_w{width_ps}ps.csv"))
    return load(hits[0]) if hits else None


def figure(path: Path, title: str, series, t_rev: float, window) -> dict[str, float]:
    fig, axes = plt.subplots(2, 1, figsize=(12.4, 8.2))
    lo, hi = t_rev + 1.0, t_rev + 1.7
    gaps: dict[str, float] = {}

    # Measured on an interpolated grid, not on native samples: the comparison
    # records are coarse in flat stretches -- up to 1.1 ns between points -- so a
    # 700 ps window can contain no samples at all and average over nothing.
    silicon_t, silicon_y = series[0][3], series[0][4]
    pedestal_grid = np.linspace(lo, hi, 400)
    worst_grid = np.linspace(t_rev + 0.2, t_rev + window, 1200)
    for label, colour, lw, t, pad in series:
        axes[0].plot(t, pad, color=colour, lw=lw, label=label)
        axes[1].plot(t, pad * 1e3, color=colour, lw=lw)
        for suffix, grid, reduce in (("", pedestal_grid, np.nanmean),
                                     ("|worst", worst_grid, np.nanmax)):
            here = np.interp(grid, t, pad)
            there = np.interp(grid, silicon_t, silicon_y)
            gaps[label + suffix] = float(reduce(np.abs(here - there))) * 1e3

    zoom = (t_rev + 0.4, t_rev + window)
    stack = []
    for _, _, _, t, pad in series:
        m = (t >= zoom[0]) & (t <= zoom[1])
        if m.any():
            stack.append(pad[m] * 1e3)
    if stack:
        flat = np.concatenate(stack)
        pad_mv = max(8.0, 0.08 * (np.nanmax(flat) - np.nanmin(flat)))
        axes[1].set_ylim(np.nanmin(flat) - pad_mv, np.nanmax(flat) + pad_mv)

    axes[0].set_xlim(t_rev - 0.25, t_rev + window)
    axes[0].set_ylabel("Pad (V)", fontsize=12)
    axes[0].set_title(title, fontsize=14.5, fontweight="bold", pad=10)
    axes[0].legend(fontsize=10, loc="upper right", framealpha=0.95)

    axes[1].set_xlim(*zoom)
    axes[1].set_ylabel("Pad (mV)", fontsize=12)
    axes[1].set_xlabel("Time (ns)", fontsize=12)
    axes[1].axvspan(lo, hi, color="#8A8A8A", alpha=0.10, lw=0)

    for axis in axes:
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.6)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=10.5)
        for spine in axis.spines.values():
            spine.set_color("#3A4753")

    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    shipped_dir = MATRIX / "hybrid" / "waveforms"
    level_dir = MATRIX / "delay_cmd" / "waveforms"
    names = sorted(p.name for p in shipped_dir.glob("*.csv")
                   if (level_dir / p.name).exists())

    def sort_key(name: str):
        m = re.match(r"(\w+?)_(short_high|short_low)_w(\d+)ps\.csv", name)
        return (DEVICE_ORDER.get(m.group(1), 9), DIR_ORDER[m.group(2)], -int(m.group(3)))

    names.sort(key=sort_key)
    rows: list[dict[str, object]] = []
    print(f"{'':<30}{'pedestal, mean |gap| mV':^36}  | {'worst |gap| mV':^26}")
    print(f"{'case':<30}{'shipped':>9}{'restore':>9}{'delay_cmd':>10}{'native':>8}"
          f"  | {'shipped':>8}{'delay_cmd':>10}{'native':>8}")

    for index, name in enumerate(names, start=1):
        m = re.match(r"(\w+?)_(short_high|short_low)_w(\d+)ps\.csv", name)
        device, direction, width_ps = m.group(1), m.group(2), int(m.group(3))
        shipped = load(shipped_dir / name)
        level = load(level_dir / name)
        width_ns = width_ps / 1000.0
        t_rev = reversal_ns(shipped["time_ns"], shipped["silicon_pad"], width_ns)
        # inv_chain settles in well under a nanosecond; io_buf needs four.
        window = 4.5 if device == "io_buf" else (2.5 if device == "ex2" else 1.6)

        series = [
            ("HSPICE transistor", SILICON, 3.4, shipped["time_ns"], shipped["silicon_pad"]),
            ("HSPICE native IBIS", NATIVE, 2.0, shipped["time_ns"], shipped["hspice_pad"]),
            ("gate-state, as shipped", SHIPPED, 2.2, shipped["time_ns"], shipped["pybis_pad"]),
        ]
        probe = restore_probe(device, direction, width_ps)
        if probe is not None:
            series.append(("gate-state + restore fix", RESTORE, 2.0,
                           probe["time_ns"], probe["pad"]))
        series.append(("gate-state + delay_cmd", LEVEL, 2.6,
                       level["time_ns"], level["pybis_pad"]))

        title = (f"{device}  |  {direction.replace('_', ' ')}  |  {width_ps} ps")
        stem = f"{index:02d}_{device}_{direction}_w{width_ps}ps.png"
        gaps = figure(out / stem, title, series, t_rev, window)

        def g(key):
            return gaps.get(key, float("nan"))
        print(f"{device + ' ' + direction + ' ' + str(width_ps) + 'ps':<30}"
              f"{g('gate-state, as shipped'):9.1f}{g('gate-state + restore fix'):9.1f}"
              f"{g('gate-state + delay_cmd'):10.1f}{g('HSPICE native IBIS'):8.1f}"
              f"  | {g('gate-state, as shipped|worst'):8.1f}"
              f"{g('gate-state + delay_cmd|worst'):10.1f}"
              f"{g('HSPICE native IBIS|worst'):8.1f}")
        rows.append({
            "figure": stem, "device": device, "direction": direction,
            "pulse_width_ps": width_ps, "reversal_ns": round(t_rev, 4),
            "native_gap_mv": round(g("HSPICE native IBIS"), 3),
            "shipped_gap_mv": round(g("gate-state, as shipped"), 3),
            "restore_gap_mv": round(g("gate-state + restore fix"), 3),
            "delay_cmd_gap_mv": round(g("gate-state + delay_cmd"), 3),
            "native_worst_mv": round(g("HSPICE native IBIS|worst"), 3),
            "shipped_worst_mv": round(g("gate-state, as shipped|worst"), 3),
            "restore_worst_mv": round(g("gate-state + restore fix|worst"), 3),
            "delay_cmd_worst_mv": round(g("gate-state + delay_cmd|worst"), 3),
        })

    summary = out / "tail_gap.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} cases")
    for metric, title in (("gap", "pedestal window, mean |gap|"),
                          ("worst", "whole tail, worst |gap|")):
        print(f"\n  {title}")
        for key, label in ((f"native_{metric}_mv", "native IBIS"),
                           (f"shipped_{metric}_mv", "shipped gate-state"),
                           (f"delay_cmd_{metric}_mv", "delay_cmd")):
            values = np.array([r[key] for r in rows], dtype=float)
            values = values[np.isfinite(values)]
            print(f"    {label:<22} mean {values.mean():6.1f} mV"
                  f"   worst {values.max():6.1f} mV")
        better = sum(1 for r in rows
                     if r[f"delay_cmd_{metric}_mv"] < r[f"shipped_{metric}_mv"])
        print(f"    delay_cmd closer on {better} of {len(rows)} cases")
    print(f"\nwrote {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
