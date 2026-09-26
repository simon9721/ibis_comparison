#!/usr/bin/env python3
"""Before and after, against both references, as shapes rather than numbers.

`residual_rescale_time_2026-09-04` reports the two derived corrections as
aggregate pedestal and RMSE. Those cannot show whether the *shape* survived --
and three earlier candidate fixes in this investigation improved the aggregates
while quietly destroying the Kd shape. So this draws it.

The window runs to +3 ns rather than +1, because the most informative event is
not the fall. After the pad collapses to zero at about +1.2 ns it comes back up
to a **secondary bump of ~52 mV at +1.8 ns** -- the pull-down finally being
commanded on, with Kd running 0 -> 1 straight through it. That bump is a clean,
well separated timing marker, and it is where the accumulating shift shows:

    transistor   1.905 -> 1.700 ns   as the pulse shortens (205 ps earlier)
    native       1.905 -> 1.848 ns   (68 ps, a third of it)
    ours         2.014 -> 2.014 ns   flat -- the command chain is fixed delays
                                     from the input edge, so it cannot move

    py -3.14 scripts/build_correction_shape_figures.py
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
import spicelab as sl  # noqa: E402
from pedestal_localization import read  # noqa: E402

R = ROOT / "results"
MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
RUNS = R / "residual_rescale_time_2026-09-04"
FIGS = R / "meeting_deck_2026-09-04" / "figures"

WIDTHS = (2354, 1989, 1792, 1505)
ALL_WIDTHS = (2354, 2226, 2090, 1989, 1853, 1792, 1666, 1634, 1505)
RISE_NS = 5.0
XLIM = (-0.35, 3.0)
C_SI, C_NAT, C_OLD, C_NEW = "#111111", "#2B6CA3", "#C05621", "#2E8B57"
SERIES = (("shipped", C_OLD, "ours, before", "-"),
          ("amp_puoff", C_NEW, "ours, corrected", "--"))


def ours(mode: str, width: int, node: str):
    raw = sl.parse_ngspice_raw(RUNS / mode / f"w{width}" / "run.raw")
    y = sl.trace(raw, "out") if node == "pad" else sl.signal(raw, f"v(x1.{node})")
    return sl.time_ns(raw) - (RISE_NS + width / 1000.0), y


def bump_time(t, y):
    """Peak of the secondary bump, searched well clear of the primary fall."""
    g = np.arange(1.3, 3.0, 0.001)
    v = np.interp(g, t, y)
    return float(g[int(np.argmax(v))]), float(v.max())


def peak_reached(t, y) -> float:
    return float(np.interp(np.arange(-0.3, 1.0, 0.001), t, y).max())


def shapes() -> None:
    rows = (("pad", "Pad (V)", (-0.05, 1.3)),
            ("ku", "Ku", (-0.10, 0.85)),
            ("kd", "Kd", (-0.35, 1.15)))
    fig, axes = plt.subplots(len(rows), len(WIDTHS),
                             figsize=(3.6 * len(WIDTHS), 3.2 * len(rows)),
                             sharex=True)
    for col, width in enumerate(WIDTHS):
        ref = read(MATRIX / f"io_buf_short_high_w{width}ps.csv")
        t = ref["time_ns"] - (RISE_NS + width / 1000.0)
        for row, (node, label, ylim) in enumerate(rows):
            a = axes[row][col]
            m = (t > XLIM[0]) & (t < XLIM[1])
            a.plot(t[m], ref[f"silicon_{node}"][m], color=C_SI, lw=3.2,
                   label="transistor", zorder=2)
            a.plot(t[m], ref[f"hspice_{node}"][m], color=C_NAT, lw=2.0,
                   label="native IBIS", zorder=3)
            for mode, colour, lab, style in SERIES:
                tt, y = ours(mode, width, node)
                mm = (tt > XLIM[0]) & (tt < XLIM[1])
                a.plot(tt[mm], y[mm], color=colour, lw=2.0, ls=style, label=lab,
                       zorder=4)
            a.axvline(0, color="#8A8A8A", ls="--", lw=1.3)
            a.axhline(0, color="#111", lw=0.8)
            a.set_ylim(*ylim)
            a.set_xlim(*XLIM)
            a.grid(alpha=0.3)
            if row == 0:
                a.set_title(f"{width} ps", fontsize=13, fontweight="bold")
            if row == len(rows) - 1:
                a.set_xlabel("Time from the reversal (ns)")
            if col == 0:
                a.set_ylabel(label, fontsize=13)
    axes[0][0].legend(fontsize=10, loc="upper right")
    fig.suptitle("io_buf short high | the two derived corrections, to +3 ns so "
                 "the pull-down turn-on is in view",
                 fontsize=16, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "correction_shapes.png", dpi=200)
    plt.close(fig)
    print("  correction_shapes.png")


def tail() -> None:
    fig, axes = plt.subplots(1, len(WIDTHS), figsize=(3.6 * len(WIDTHS), 3.8),
                             sharey=True)
    for a, width in zip(axes, WIDTHS):
        ref = read(MATRIX / f"io_buf_short_high_w{width}ps.csv")
        t = ref["time_ns"] - (RISE_NS + width / 1000.0)
        m = (t > 0.15) & (t < 3.0)
        a.plot(t[m], ref["silicon_pad"][m] * 1e3, color=C_SI, lw=3.2,
               label="transistor")
        a.plot(t[m], ref["hspice_pad"][m] * 1e3, color=C_NAT, lw=2.0,
               label="native IBIS")
        for mode, colour, lab, style in SERIES:
            tt, y = ours(mode, width, "pad")
            mm = (tt > 0.15) & (tt < 3.0)
            a.plot(tt[mm], y[mm] * 1e3, color=colour, lw=2.0, ls=style, label=lab)
        a.axhline(0, color="#111", lw=0.8)
        a.set_title(f"{width} ps", fontsize=13, fontweight="bold")
        a.set_xlabel("Time from the reversal (ns)")
        a.grid(alpha=0.3)
    axes[0].set_ylabel("Pad (mV)")
    axes[0].set_ylim(-20, 200)
    axes[0].legend(fontsize=10)
    fig.suptitle("The tail: the pedestal first, then the pull-down turn-on bump",
                 fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "correction_tail.png", dpi=200)
    plt.close(fig)
    print("  correction_tail.png")


def bump() -> None:
    """The bump on its own, and how its timing tracks the excursion reached."""
    fig, axes = plt.subplots(1, len(WIDTHS) + 1,
                             figsize=(3.5 * (len(WIDTHS) + 1), 4.2))
    for a, width in zip(axes, WIDTHS):
        ref = read(MATRIX / f"io_buf_short_high_w{width}ps.csv")
        t = ref["time_ns"] - (RISE_NS + width / 1000.0)
        m = (t > 1.2) & (t < 3.0)
        a.plot(t[m], ref["silicon_pad"][m] * 1e3, color=C_SI, lw=3.2,
               label="transistor")
        a.plot(t[m], ref["hspice_pad"][m] * 1e3, color=C_NAT, lw=2.0,
               label="native IBIS")
        for mode, colour, lab, style in SERIES:
            tt, y = ours(mode, width, "pad")
            mm = (tt > 1.2) & (tt < 3.0)
            a.plot(tt[mm], y[mm] * 1e3, color=colour, lw=2.0, ls=style, label=lab)
        # where the transistor put the bump in the least stressed case
        a.axvline(1.905, color="#8A8A8A", ls=":", lw=1.4)
        a.set_ylim(-3, 62)
        a.set_xlim(1.2, 3.0)
        a.set_title(f"{width} ps", fontsize=13, fontweight="bold")
        a.set_xlabel("Time from the reversal (ns)")
        a.grid(alpha=0.3)
    axes[0].set_ylabel("Pad (mV)")
    axes[0].legend(fontsize=9)

    a = axes[-1]
    for kind, key, colour, lab, mk in (
            ("ref", "silicon_pad", C_SI, "transistor", "o"),
            ("ref", "hspice_pad", C_NAT, "native IBIS", "s"),
            ("run", "shipped", C_OLD, "ours, before", "^"),
            ("run", "amp_puoff", C_NEW, "ours, corrected", "v")):
        xs, ys = [], []
        for w in ALL_WIDTHS:
            ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
            tr = ref["time_ns"] - (RISE_NS + w / 1000.0)
            xs.append(peak_reached(tr, ref["silicon_pad"]))
            if kind == "ref":
                ys.append(bump_time(tr, ref[key])[0])
            else:
                ys.append(bump_time(*ours(key, w, "pad"))[0])
        a.plot(xs, ys, marker=mk, color=colour, lw=2.0, ms=7, label=lab)
    a.set_xlabel("Peak the pad actually reached (V)")
    a.set_ylabel("Bump time from the reversal (ns)")
    a.set_title("Ours does not move", fontsize=12, fontweight="bold")
    a.grid(alpha=0.3)
    a.legend(fontsize=9)
    fig.suptitle("The pull-down turn-on bump: a clean marker for the "
                 "accumulating shift", fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "correction_bump.png", dpi=200)
    plt.close(fig)
    print("  correction_bump.png")


def main() -> int:
    shapes()
    tail()
    bump()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
