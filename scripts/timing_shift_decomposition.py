#!/usr/bin/env python3
"""Where does pybis's timing shift come from, and does stress actually add to it?

"Defect B" was called stress-specific on the strength of the *native* comparison:
the gate-state build sits ~9 ps from native on a clean full-swing edge but ~75-125
ps from it under stress. Native has since been shown to be an unreliable yardstick
under stress -- on some cases it misses the event entirely, and its response is
device-dependent (tracking on io_buf, saturating on ex2 and inv_chain).

So the comparison has to be redone against the **transistor**, which is ground
truth and does not degrade. This measures pybis-minus-transistor across the depth
family, where `depth91` cases are essentially full-swing and the lower depths are
progressively more stressed. If the shift is roughly constant with depth, then
what full swing already carries is the whole of it and stress adds nothing; if it
grows as depth falls, stress genuinely contributes.

Timing is taken at 50% of each case's own transistor excursion, applied
identically to every build, since a fixed fraction of the rail is not crossed on
the shallower cases.

    py -3.14 scripts/timing_shift_decomposition.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SRC = ROOT / "results" / "_baseline_edgecmd" / "waveforms"
OUT = ROOT / "results" / "timing_shift_decomposition_2026-09-03"
COLOURS = {"io_buf": "#C02626", "ex2": "#2B6CA3", "inv_chain": "#1B6B4F"}


def cross(t, v, level, rising, after):
    for i in range(1, len(v)):
        if t[i] < after:
            continue
        if (rising and v[i - 1] < level <= v[i]) or (not rising and v[i - 1] > level >= v[i]):
            return float(t[i - 1] + (level - v[i - 1]) * (t[i] - t[i - 1]) / (v[i] - v[i - 1]))
    return float("nan")


def timing(t, si, other, direction):
    """(t_transistor, t_other) at 50% of the transistor's own excursion."""
    if direction == "short_high":
        base = float(np.median(si[t < t[0] + 0.2 * (t[-1] - t[0])]))
        level = base + 0.5 * (si.max() - base)
        after = t[0] + 0.2 * (t[-1] - t[0])
        return cross(t, si, level, True, after), cross(t, other, level, True, after)
    plateau = float(np.median(si[(t > 9.0) & (t < 10.2)]))
    window = (t > 10.2) & (t < 12.5)
    level = plateau - 0.5 * (plateau - si[window].min())
    return cross(t, si, level, False, 10.2), cross(t, other, level, False, 10.2)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in sorted(SRC.glob("*.csv")):
        device = f.stem.split("_short")[0]
        direction = "short_" + f.stem.split("_short_")[1].split("_")[0]
        depth = int(re.search(r"depth(\d+)", f.stem).group(1))
        r = list(csv.DictReader(f.open()))
        col = lambda k: np.array([float(x[k]) for x in r])  # noqa: E731
        t, si, hs, py = col("time_ns"), col("silicon_pad"), col("hspice_pad"), col("pybis_pad")
        tx, mp = timing(t, si, py, direction)
        _, mn = timing(t, si, hs, direction)
        if not np.isfinite(tx):
            continue
        rows.append((device, direction, depth,
                     (mp - tx) * 1e3 if np.isfinite(mp) else np.nan,
                     (mn - tx) * 1e3 if np.isfinite(mn) else np.nan))

    print(f"{'device':<11}{'direction':<12}{'depth':>6}"
          f"{'pybis vs tx':>13}{'native vs tx':>14}")
    for d, dirn, dep, ep, en in rows:
        print(f"{d:<11}{dirn:<12}{dep:>6}{ep:>12.1f}p{en:>13.1f}p")

    print(f"\n{'device':<11}{'shallowest':>12}{'deepest':>10}{'change':>10}   reading")
    for dev in ("io_buf", "ex2", "inv_chain"):
        sub = sorted([r for r in rows if r[0] == dev and np.isfinite(r[3])], key=lambda r: r[2])
        if len(sub) < 2:
            continue
        lo, hi = sub[0], sub[-1]
        change = hi[3] - lo[3]
        reading = ("flat -- stress adds nothing" if abs(change) < 8
                   else ("grows with depth" if change > 0 else "shrinks with depth"))
        print(f"{dev:<11}{lo[3]:>11.1f}p{hi[3]:>9.1f}p{change:>9.1f}p   {reading}")

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    for dev in ("io_buf", "ex2", "inv_chain"):
        for dirn, mk in (("short_high", "o"), ("short_low", "s")):
            sub = sorted([r for r in rows if r[0] == dev and r[1] == dirn
                          and np.isfinite(r[3])], key=lambda r: r[2])
            if not sub:
                continue
            ax.plot([r[2] for r in sub], [r[3] for r in sub], mk + "-",
                    color=COLOURS[dev], lw=2, ms=8,
                    label=f"{dev} {dirn}", alpha=0.9 if dirn == "short_high" else 0.55)
    ax.axhline(0, color="#111", lw=1.5)
    ax.set_xlabel("depth target (%)  —  right = closer to a full transition", fontsize=11)
    ax.set_ylabel("pybis − transistor, 50% of own excursion (ps)", fontsize=11)
    ax.set_title("Does the timing shift grow with stress? (measured against the transistor)",
                 fontsize=13, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "timing_shift_vs_depth.png", dpi=170)
    plt.close(fig)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
