#!/usr/bin/env python3
"""Does delay_cmd fix the timing shift, or only the offset?

The offset defect was traced to `GUPCMD`: an open-loop integrator with no DC path,
so a truncated pulse strands charge. `delay_cmd` is level-driven -- the command is
a function of the current input level rather than accumulated edge history -- so it
returns to exactly zero and strands nothing, and it removes the offset
(63.9 -> 3.7 mV at reversal).

The timing shift ("defect B") was separately shown to be **stress-specific**: the
gate-state build is ~9 ps from native on a clean full-swing edge but ~75-125 ps
under stress. Truncation is the same trigger as the offset, so the two defects may
be one mechanism -- and if they are, delay_cmd should already fix the timing too.

Nobody has checked. delay_cmd's *amplitude* was measured (RMSE 108.6 -> 92.2 mV,
best in the study); its *timing* never was. This measures it.

Method note: these stressed events are partial excursions, so a fixed 50%-of-rail
threshold is not a safe reference -- on some cases it is never crossed. Timing is
taken at 50% of *each case's transistor excursion*, applied identically to every
build, so the comparison does not depend on how far the pulse happened to get.

    py -3.14 scripts/delay_cmd_timing_test.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
BUILDS = ("gate_state", "delay_cmd")


def load(path: Path):
    rows = list(csv.DictReader(path.open()))
    col = lambda k: np.array([float(r[k]) for r in rows])  # noqa: E731
    return col("time_ns"), col("silicon_pad"), col("pybis_pad")


def cross(t, v, level, rising, after):
    for i in range(1, len(v)):
        if t[i] < after:
            continue
        if (rising and v[i - 1] < level <= v[i]) or (not rising and v[i - 1] > level >= v[i]):
            return float(t[i - 1] + (level - v[i - 1]) * (t[i] - t[i - 1]) / (v[i] - v[i - 1]))
    return float("nan")


def event_timing(t, si, other, direction):
    """Crossing time of `other` and of the transistor, at 50% of the transistor's
    own excursion for this case. Returns (t_transistor, t_other)."""
    if direction == "short_high":
        base = float(np.median(si[t < t[0] + 0.2 * (t[-1] - t[0])]))
        level = base + 0.5 * (si.max() - base)
        after = t[0] + 0.2 * (t[-1] - t[0])
        return cross(t, si, level, True, after), cross(t, other, level, True, after)
    plateau = float(np.median(si[(t > 9.0) & (t < 10.2)]))
    win_lo = 10.2
    depth = plateau - si[(t > win_lo) & (t < 12.5)].min()
    level = plateau - 0.5 * depth
    return cross(t, si, level, False, win_lo), cross(t, other, level, False, win_lo)


def main() -> int:
    per_build: dict[str, list] = {b: [] for b in BUILDS}
    names = {}
    for b in BUILDS:
        folder = MATRIX / b / "waveforms"
        if not folder.exists():
            print(f"missing {folder}")
            return 1
        for f in sorted(folder.glob("io_buf_*.csv")):
            names.setdefault(f.name, set()).add(b)

    shared = sorted(n for n, bs in names.items() if bs == set(BUILDS))
    print(f"{len(shared)} io_buf cases present in both builds\n")
    print(f"{'case':<32}{'gate_state':>12}{'delay_cmd':>12}   improvement")
    rows = []
    for name in shared:
        direction = "short_" + name.split("_short_")[1].split("_")[0]
        shifts = {}
        for b in BUILDS:
            t, si, py = load(MATRIX / b / "waveforms" / name)
            tx, mo = event_timing(t, si, py, direction)
            shifts[b] = (mo - tx) * 1e3 if np.isfinite(tx) and np.isfinite(mo) else float("nan")
        g, d = shifts["gate_state"], shifts["delay_cmd"]
        if not (np.isfinite(g) and np.isfinite(d)):
            continue
        better = abs(d) < abs(g)
        rows.append((name, g, d))
        print(f"{name.replace('.csv',''):<32}{g:>11.1f}p{d:>11.1f}p   "
              f"{'better' if better else 'worse':>7}  ({abs(g)-abs(d):+.1f} ps)")

    if rows:
        g = np.array([r[1] for r in rows])
        d = np.array([r[2] for r in rows])
        print(f"\n{'':<32}{'gate_state':>12}{'delay_cmd':>12}")
        print(f"{'mean |shift|':<32}{np.mean(np.abs(g)):>11.1f}p{np.mean(np.abs(d)):>11.1f}p")
        print(f"{'max  |shift|':<32}{np.max(np.abs(g)):>11.1f}p{np.max(np.abs(d)):>11.1f}p")
        print(f"{'mean signed shift':<32}{np.mean(g):>11.1f}p{np.mean(d):>11.1f}p")
        print(f"\ndelay_cmd better on {int(np.sum(np.abs(d) < np.abs(g)))}/{len(rows)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
