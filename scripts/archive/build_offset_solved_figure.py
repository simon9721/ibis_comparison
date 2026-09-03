#!/usr/bin/env python3
"""Does the level-driven command actually remove the settled offset?

Four pad traces on the two io_buf short-high cases where the defect is visible
(the other three are the ones the clamp made look clean):

    HSPICE transistor      ground truth
    HSPICE native IBIS     the bar
    shipped gate-state     the defect -- edge-integrating command
    restore-term fix       cleanup started sooner and decayed faster
    delay_cmd              the structural repair -- command is a delayed level

The measurement is the pad plateau between reversal + 1.0 and + 1.7 ns, taken
before the pulldown bump so it reads the stranded-charge pedestal and nothing
else. Averaged over the four cases that ran:

    native IBIS          2.0 mV from the transistor
    shipped gate-state  28.6 mV
    restore-term fix    14.3 mV
    delay_cmd            2.2 mV

The cleanup halves the error; the level-driven command removes it. That is the
expected shape -- a restore term acts only after the charge is already stranded,
and it is gated off for 2.99 ns precisely so it cannot disturb a command still
in flight, so it cannot help during the window that matters.

    py -3.14 scripts/build_offset_solved_figure.py
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
FIX = ROOT / "results" / "settled_offset_diagnosis_2026-08-27" / "fix_probe"
OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27"

EDGE_NS = 5.0
# target percent -> pulse width ps. The two cases where the clamp does not hide
# the defect; 80 and 70 carry a negative command error the clamp erases.
CASES = [(60, 1792), (50, 1634)]

SILICON = "#111111"
NATIVE = "#2B6CA3"
SHIPPED = "#C05621"
RESTORE = "#7B2CBF"
LEVEL = "#1B6B4F"
DPI = 175


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) if x not in ("", "nan") else np.nan for x in r]
                       for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(rows[0])}


def traces(target: int, width: int):
    """(label, colour, time_ns, pad_v) for every build, on one case."""
    shipped = load(MATRIX / "hybrid" / "waveforms" / f"io_buf_short_high_w{width}ps.csv")
    level = load(MATRIX / "delay_cmd" / "waveforms" / f"io_buf_short_high_w{width}ps.csv")
    out = [
        ("HSPICE transistor", SILICON, 3.6, shipped["time_ns"], shipped["silicon_pad"]),
        ("HSPICE native IBIS", NATIVE, 2.0, shipped["time_ns"], shipped["hspice_pad"]),
        ("gate-state, as shipped", SHIPPED, 2.2, shipped["time_ns"], shipped["pybis_pad"]),
    ]
    probe = FIX / f"gate_and_tau_swing{target}_w{width}ps.csv"
    if probe.exists():
        fix = load(probe)
        out.append(("gate-state + restore fix", RESTORE, 2.0, fix["time_ns"], fix["pad"]))
    out.append(("gate-state + delay_cmd", LEVEL, 2.6, level["time_ns"], level["pybis_pad"]))
    return out


def style(axis):
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=11)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, len(CASES), figsize=(14.6, 9.0))
    summary: dict[str, list[float]] = {}

    for col, (target, width) in enumerate(CASES):
        t_rev = EDGE_NS + width / 1000.0
        rows = traces(target, width)
        for label, colour, lw, t, pad in rows:
            axes[0, col].plot(t, pad, color=colour, lw=lw, label=label)
            axes[1, col].plot(t, pad * 1e3, color=colour, lw=lw)
            lo, hi = t_rev + 1.0, t_rev + 1.7
            mask = (t >= lo) & (t <= hi)
            summary.setdefault(label, []).append(float(np.nanmean(pad[mask])) * 1e3)

        axes[0, col].set_xlim(t_rev - 0.15, t_rev + 4.5)
        axes[0, col].set_ylim(-0.06, 1.0)
        axes[0, col].set_ylabel("Pad (V)", fontsize=12)
        axes[0, col].set_title(f"io_buf  |  short high  |  {width} ps",
                               fontsize=14.5, fontweight="bold", pad=10)

        axes[1, col].set_xlim(t_rev + 0.5, t_rev + 4.5)
        axes[1, col].set_ylim(-12, 110)
        axes[1, col].set_ylabel("Pad (mV)", fontsize=12)
        axes[1, col].set_xlabel("Time (ns)", fontsize=12)
        axes[1, col].axhline(0.0, color="#5A5A5A", lw=1.0)
        # The window the plateau is measured over, before the pulldown bump.
        axes[1, col].axvspan(t_rev + 1.0, t_rev + 1.7, color="#8A8A8A", alpha=0.10, lw=0)

        for axis in (axes[0, col], axes[1, col]):
            axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.6)
            style(axis)

    axes[0, 0].legend(fontsize=10.5, loc="upper right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(out / "13_offset_removed_by_level_command.png", dpi=DPI)
    plt.close(fig)

    silicon = np.array(summary["HSPICE transistor"])
    print("pad plateau, reversal +1.0 to +1.7 ns, mean over the two cases\n")
    print(f"{'build':<26}{'plateau mV':>12}{'vs transistor':>15}")
    for label, values in summary.items():
        error = np.nanmean(np.abs(np.array(values) - silicon))
        gap = "" if label == "HSPICE transistor" else f"{error:14.1f} "
        print(f"{label:<26}{np.nanmean(values):12.1f}{gap:>15}")
    print(f"\nwrote {out.resolve()}\\13_offset_removed_by_level_command.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
