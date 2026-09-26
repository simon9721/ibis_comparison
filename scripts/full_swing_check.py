#!/usr/bin/env python3
"""Item 5: how far is each build from the transistor at FULL swing, and where?

Overlays the 10 ns full-swing pad of the transistor, the shipped model and the chain builds
for ex2 and inv_chain, and reports per edge: 50 % crossing time error and the rms over the
edge window. All from existing runs (predriver_stages_2026-09-09/<dev>/full for the
transistor; <build>/full/run.raw for the models).

    py -3.14 scripts/full_swing_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import spicelab as sl  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402

R = ROOT / "results"
CH = R / "gate_chain_prototype_2026-09-10"
OUT = R / "track2_train_check_2026-09-13" / "figs"
BUILDS = {
    "ex2": [("shipped", CH / "ex2_c1.7/shipped/full"),
            ("file chain + measured map", CH / "ex2_c1.7/ibis_silicon_K3_xlin0.45_calibpad810/full"),
            ("real-stage chain", CH / "ex2_c1.7/real_silicon_K3_calibpad810/full")],
    "inv_chain": [("shipped", CH / "inv_chain_c0.6/shipped/full"),
                  ("file chain + measured map", CH / "inv_chain_c0.6/ibis_silicon_K7_calibpad104/full"),
                  ("real-stage chain, sqrt", CH / "inv_chain_c0.6/real_silicon_K7_calibpad104_p0.5/full")],
}
COLS = ["#888888", "#2E7D4F", "#2B5C8A"]


def cross(t, v, level, lo, hi, rising):
    g = np.arange(lo, hi, 0.001)
    y = np.interp(g, t, v)
    i = int(np.argmax(y > level)) if rising else int(np.argmax(y < level))
    return float(g[i])


def main() -> int:
    fig, axes = plt.subplots(2, 2, figsize=(16, 8))
    for r, dev in enumerate(BUILDS):
        raw = psp.parse_tr0(psp.OUT / dev / "full/run.tr0")
        t_si, si = sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float)
        rest, high = float(np.interp(4.5, t_si, si)), float(np.interp(14.5, t_si, si))
        mid = 0.5 * (rest + high)
        print(f"\n{dev}: full swing, transistor rest {rest:.3f} V high {high:.3f} V")
        print(f"  {'build':<28}{'rise 50 % err':>14}{'fall 50 % err':>14}{'rms rise win':>13}{'rms fall win':>13}{'high err':>10}")
        for c, (lo, hi, lab) in enumerate(((4.8, 7.5, "rising edge"), (14.8, 17.5, "falling edge"))):
            a = axes[r, c]
            m = (t_si > lo) & (t_si < hi)
            a.plot(t_si[m], si[m], color="#111", lw=2.8, label="transistor")
            a.set_title(f"{dev}, full swing, {lab}", fontweight="bold")
            a.grid(alpha=0.3)
            a.set_xlabel("time (ns)")
            a.set_ylabel("pad (V)")
        for (label, d), col in zip(BUILDS[dev], COLS):
            if not (d / "run.raw").exists():
                print(f"  {label:<28} (no run)")
                continue
            rw = sl.parse_ngspice_raw(d / "run.raw")
            t, v = sl.time_ns(rw), sl.trace(rw, "out")
            er = (cross(t, v, mid, 4.8, 8.0, True) - cross(t_si, si, mid, 4.8, 8.0, True)) * 1e3
            ef = (cross(t, v, mid, 14.8, 18.0, False) - cross(t_si, si, mid, 14.8, 18.0, False)) * 1e3
            g1, g2 = np.arange(4.8, 8.0, 0.002), np.arange(14.8, 18.0, 0.002)
            rr = np.sqrt(np.mean((np.interp(g1, t, v) - np.interp(g1, t_si, si)) ** 2)) * 1e3
            rf = np.sqrt(np.mean((np.interp(g2, t, v) - np.interp(g2, t_si, si)) ** 2)) * 1e3
            eh = (float(np.interp(14.5, t, v)) - high) * 1e3
            print(f"  {label:<28}{er:>+11.0f} ps{ef:>+11.0f} ps{rr:>10.1f} mV{rf:>10.1f} mV{eh:>+7.0f} mV")
            for c, (lo, hi) in enumerate(((4.8, 7.5), (14.8, 17.5))):
                m = (t > lo) & (t < hi)
                axes[r, c].plot(t[m], v[m], color=col, lw=1.5, ls="--" if "chain" in label else ":", label=label)
        axes[r, 0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "full_swing_check.png", dpi=140)
    print("\nwrote", OUT / "full_swing_check.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
