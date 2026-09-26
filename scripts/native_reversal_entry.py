#!/usr/bin/env python3
"""What does native do with its falling trajectory when the pulse is truncated?

`native_st_vs_solved_2026-09-07` settled that native's stored Ku(t)/Kd(t) is the
offline two-fixture solve, same shape to 0.4% of span. So native holds exactly one
falling trajectory, recorded from a **fully on** pull-up, indexed by time since
the edge -- the same thing we hold.

And the documented state mechanism (bracket V(out) between waveforms with
different initial voltages) is dormant here: io_buf's .ibs carries exactly one
pair per edge.

So native ought to have our defect. It does not -- its Ku sits +15 ps from the
transistor under stress where ours sits +80. This asks what it actually does with
the curve, by overlaying native's stressed Ku against its own full-swing falling
Ku, aligned at the reversal:

* **replays from the start** -> stressed Ku jumps to the full curve's 1.0 and
  follows it, and native has no state mechanism at all;
* **enters partway** -> stressed Ku picks the full curve up at the value it had
  reached, which is the entry condition working through some other route;
* **scales** -> stressed Ku is the full curve multiplied down.

    py -3.14 scripts/native_reversal_entry.py
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
FULL = R / "native_vs_solved_ku_2026-09-04" / "run.tr0"
RUNS = R / "residual_rescale_time_2026-09-04"
OUT = R / "native_reversal_entry_2026-09-07"

WIDTHS = (2354, 1989, 1792, 1505)
ALL_WIDTHS = (2354, 2226, 2090, 1989, 1853, 1792, 1666, 1634, 1505)
RISE_NS, FALL_NS = 5.0, 15.0
C_FULL, C_STRESS, C_SI, C_OURS = "#8A8A8A", "#2B6CA3", "#111111", "#C05621"


def full_falling():
    """Native's own falling Ku / Kd at full swing, timed from the falling edge."""
    tr = sl.parse_hspice_tr0(FULL)
    t = sl.time_ns(tr) - FALL_NS
    return t, sl.trace(tr, "ku"), sl.trace(tr, "kd")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tf, kuf, kdf = full_falling()
    g = np.arange(-0.05, 1.0, 0.002)
    ku_full = np.interp(g, tf, kuf)

    print("  Native's stressed Ku against its own full-swing falling Ku,")
    print("  both timed from the reversal.\n")
    print("  Ku at the reversal, and what the full curve says there:")
    print(f"    {'width':<8}{'native Ku at rev':>18}{'full-swing Ku at rev':>22}"
          f"{'ours Ku at rev':>17}")
    entries = []
    for w in ALL_WIDTHS:
        ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
        t = ref["time_ns"] - (RISE_NS + w / 1000.0)
        nat_at0 = float(np.interp(-0.004, t, ref["hspice_ku"]))
        raw = sl.parse_ngspice_raw(RUNS / "shipped" / f"w{w}" / "run.raw")
        our_at0 = float(np.interp(-0.004, sl.time_ns(raw) - (RISE_NS + w / 1000.0),
                                  sl.signal(raw, "v(x1.ku)")))
        entries.append((w, nat_at0, our_at0))
        print(f"    {w:<8}{nat_at0:>18.4f}{float(np.interp(0.0, g, ku_full)):>22.4f}"
              f"{our_at0:>17.4f}")

    print("\n  Does native's stressed fall follow the full-swing curve, or a")
    print("  scaled copy of it?  Ratio native_stressed / full_swing after the")
    print("  reversal, and the offset that would fit instead.\n")
    print(f"    {'width':<8}{'Ku(rev)':>9}" + "".join(f"{f'+{p}ps':>10}"
                                                      for p in (50, 100, 200, 300)))
    for w in ALL_WIDTHS:
        ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
        t = ref["time_ns"] - (RISE_NS + w / 1000.0)
        cells = []
        for p in (0.050, 0.100, 0.200, 0.300):
            nat = float(np.interp(p, t, ref["hspice_ku"]))
            fl = float(np.interp(p, g, ku_full))
            cells.append(nat / fl if abs(fl) > 0.02 else float("nan"))
        k0 = float(np.interp(-0.004, t, ref["hspice_ku"]))
        print(f"    {w:<8}{k0:>9.4f}" + "".join(f"{c:>10.3f}" for c in cells))

    fig, axes = plt.subplots(1, len(WIDTHS), figsize=(4.0 * len(WIDTHS), 4.2),
                             sharey=True)
    for a, w in zip(axes, WIDTHS):
        ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
        t = ref["time_ns"] - (RISE_NS + w / 1000.0)
        m = (t > -0.35) & (t < 1.0)
        a.plot(g, ku_full, color=C_FULL, lw=3.0,
               label="native, FULL-SWING falling Ku")
        a.plot(t[m], ref["hspice_ku"][m], color=C_STRESS, lw=2.2,
               label="native, stressed")
        a.plot(t[m], ref["silicon_ku"][m], color=C_SI, lw=1.6, label="transistor")
        raw = sl.parse_ngspice_raw(RUNS / "shipped" / f"w{w}" / "run.raw")
        tt = sl.time_ns(raw) - (RISE_NS + w / 1000.0)
        mm = (tt > -0.35) & (tt < 1.0)
        a.plot(tt[mm], sl.signal(raw, "v(x1.ku)")[mm], color=C_OURS, lw=1.8,
               label="ours")
        a.axvline(0, color="#8A8A8A", ls="--", lw=1.2)
        a.set_ylim(-0.15, 1.25)
        a.set_xlim(-0.35, 1.0)
        a.set_title(f"{w} ps", fontsize=13, fontweight="bold")
        a.set_xlabel("Time from the reversal (ns)")
        a.grid(alpha=0.3)
    axes[0].set_ylabel("Ku")
    axes[0].legend(fontsize=9)
    fig.suptitle("Does native replay its falling curve from the start, or enter "
                 "it partway?", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "native_reversal_entry.png", dpi=200)
    plt.close(fig)
    print(f"\n  figure: {OUT / 'native_reversal_entry.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
