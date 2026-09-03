#!/usr/bin/env python3
"""Is native IBIS's stressed-case behaviour predictable? Test the law out of sample.

On io_buf short_high, native IBIS under-swings the transistor by 60-124 mV and the
error tracks how complete the transition was, with r = +0.94. That is one device
and one direction -- enough to notice a pattern, not enough to call it a law.

This tests it on every device and direction available in the width-sweep family
(io_buf, ex2, inv_chain; short_high and short_low). If native's error is a
function of completion fraction across all of them, its stressed behaviour is
predictable and can be corrected for rather than merely noted. If the slope or
sign changes per device, it is not a law and the io_buf result was a coincidence.

Completion fraction is measured per device from its own largest observed
excursion, so no external full-swing assumption is imported.

    py -3.14 scripts/native_stress_law.py
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SRC = ROOT / "results" / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
OUT = ROOT / "results" / "native_stress_law_2026-09-03"
NAT, PYB = "#2B6CA3", "#C02626"


def excursion(t, v, direction):
    """Signed excursion of the event from the settled level before it."""
    base = float(np.median(v[t < t[0] + 0.25 * (t[-1] - t[0])]))
    ext = float(v.max() if direction == "short_high" else v.min())
    return abs(ext - base)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for f in sorted(SRC.glob("*.csv")):
        stem = f.stem
        device = stem.split("_short")[0]
        direction = "short_" + stem.split("_short_")[1].split("_")[0]
        rows = list(csv.DictReader(f.open()))
        col = lambda k: np.array([float(r[k]) for r in rows])  # noqa: E731
        t = col("time_ns")
        groups[(device, direction)].append(
            (excursion(t, col("silicon_pad"), direction),
             excursion(t, col("hspice_pad"), direction),
             excursion(t, col("pybis_pad"), direction)))

    print(f"{'device / direction':<26}{'n':>3}{'slope':>9}{'intercept':>11}"
          f"{'r':>8}{'err at frac=1':>15}")
    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    summary = []
    for (dev, dirn), vals in sorted(groups.items()):
        si = np.array([v[0] for v in vals])
        hs = np.array([v[1] for v in vals])
        py = np.array([v[2] for v in vals])
        full = si.max()                       # this device's own largest excursion
        frac = si / full
        err = (hs - si) * 1e3
        if len(frac) < 3 or np.ptp(frac) < 0.05:
            print(f"{dev+' '+dirn:<26}{len(frac):>3}   (too few / too narrow a span)")
            continue
        m, b = np.polyfit(frac, err, 1)
        r = float(np.corrcoef(frac, err)[0, 1])
        print(f"{dev+' '+dirn:<26}{len(frac):>3}{m:>9.0f}{b:>11.0f}{r:>8.3f}{m+b:>14.0f}m")
        summary.append((dev, dirn, m, b, r))
        ax.plot(frac, err, "o", ms=7, label=f"{dev} {dirn}  (r={r:+.2f})")
        xs = np.linspace(frac.min(), frac.max(), 20)
        ax.plot(xs, m * xs + b, "-", lw=1.4, alpha=0.65)

    ax.axhline(0, color="#111", lw=1.6)
    ax.set_xlabel("completion fraction  (transistor excursion / that device's full excursion)",
                  fontsize=11)
    ax.set_ylabel("native IBIS peak error vs transistor (mV)", fontsize=11)
    ax.set_title("Does native's stressed error follow one law across devices?",
                 fontsize=13.5, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "native_stress_law.png", dpi=170)
    plt.close(fig)

    print()
    if summary:
        slopes = [s[2] for s in summary]
        signs = {np.sign(s[3]) for s in summary}
        print(f"slopes range {min(slopes):.0f} to {max(slopes):.0f} mV per unit fraction")
        print(f"intercept signs: {'all negative (under-swing everywhere)' if signs == {-1.0} else signs}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
