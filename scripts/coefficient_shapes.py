#!/usr/bin/env python3
"""Look at the Ku/Kd shapes, across stress, against the transistor.

Every measurement in the pedestal investigation so far has been a *number* -- a
best-fit lag, sometimes with a residual to say whether the lag meant anything.
That has been enough to eliminate causes but not to find one, and a lag by
construction cannot see a change of shape.

So this draws them. Three sources on one axis, for every io_buf short_high width
plus the unstressed control:

    silicon_*   the transistor, through the two-fixture solve -- ground truth
    hspice_*    native IBIS's own St_pu / St_pd
    pybis_*     ours

Time is plotted relative to each case's own reversal, so the widths overlay and
the question "what changes as the pulse gets shorter" is answerable by eye.

    py -3.14 scripts/coefficient_shapes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pedestal_localization import read  # noqa: E402

R = ROOT / "results"
MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
FIGS = R / "meeting_deck_2026-09-04" / "figures"

C_SI, C_NAT, C_US = "#111111", "#2B6CA3", "#C05621"
RISE_NS = 5.0


def cases(device: str, direction: str):
    for path in sorted(MATRIX.glob(f"{device}_{direction}_w*ps.csv"),
                       key=lambda p: -int(p.stem.split("_w")[1].rstrip("ps"))):
        width = int(path.stem.split("_w")[1].rstrip("ps"))
        yield width, read(path)


def main() -> int:
    picked = [(w, d) for w, d in cases("io_buf", "short_high")
              if w in (2354, 1989, 1792, 1505)]
    fig, axes = plt.subplots(2, len(picked), figsize=(3.5 * len(picked), 7.0),
                             sharex=True, sharey="row")
    for col, (width, d) in enumerate(picked):
        rev = RISE_NS + width / 1000.0
        t = d["time_ns"] - rev
        w = (t > -1.2) & (t < 1.6)
        for row, key in enumerate(("ku", "kd")):
            a = axes[row][col]
            a.plot(t[w], d[f"silicon_{key}"][w], color=C_SI, lw=3.2,
                   label="transistor")
            a.plot(t[w], d[f"hspice_{key}"][w], color=C_NAT, lw=2.0,
                   label="native")
            a.plot(t[w], d[f"pybis_{key}"][w], color=C_US, lw=2.0, label="ours")
            a.axvline(0, color="#8A8A8A", ls="--", lw=1.4)
            a.axhline(0, color="#111", lw=0.8)
            a.grid(alpha=0.3)
            if row == 0:
                a.set_title(f"{width} ps", fontsize=12, fontweight="bold")
            else:
                a.set_xlabel("Time from the reversal (ns)")
    axes[0][0].set_ylabel("Ku")
    axes[1][0].set_ylabel("Kd")
    axes[0][0].legend(fontsize=10)
    fig.suptitle("io_buf short high | the coefficient shapes as the pulse is cut "
                 "shorter", fontsize=15, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "coefficient_shapes.png", dpi=200)
    plt.close(fig)
    print("  coefficient_shapes.png")

    # Numbers that describe the shape rather than a delay: what each coefficient
    # peaks at, and where, relative to the reversal.
    print("\n  Peak value and its time relative to the reversal:")
    print(f"    {'width':<9}{'':<6}" + "".join(f"{h:>22}" for h in
          ("transistor", "native", "ours")))
    for width, d in cases("io_buf", "short_high"):
        rev = RISE_NS + width / 1000.0
        t = d["time_ns"] - rev
        w = (t > -1.5) & (t < 2.0)
        for key in ("ku", "kd"):
            cells = []
            for src in ("silicon", "hspice", "pybis"):
                y = d[f"{src}_{key}"][w]
                i = int(np.argmax(y))
                cells.append(f"{y[i]:+.3f} at {t[w][i]:+.3f} ns")
            print(f"    {width:<9}{key:<6}" + "".join(f"{c:>22}" for c in cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
