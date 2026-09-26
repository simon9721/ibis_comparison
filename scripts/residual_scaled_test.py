#!/usr/bin/env python3
"""Scale the falling residual by how far the transition actually got.

Decomposing Ku into its two parts across a reversal (`ku_decompose_2026-09-04`)
localises the pedestal exactly:

    t-rev      Ku    gate part   residual
     -100    0.433     0.436      0.000
       -4    0.476     0.479     -0.001
      +69    0.680     0.513     +0.173     <- the whole excursion is here
     +199    0.250     0.241     -0.001

The gate part is smooth through the reversal. The **residual** is zero all through
the transition and then fires +0.173 -- a quarter of the total Ku -- in about
70 ps.

It is not misfiring. Its own table says so:

    KURES_F at HNX =  0.0    0.006   0.012   0.018   0.024   0.030
                    -0.056  -0.102  -0.092  +0.088  +0.158  +0.183

The falling residual really does rise to +0.18 early in a fall. It has to: it
corrects the gate map's lag at the start of a fall **from fully on**, where the
true Ku is 1.0 and the map has not caught up.

On a truncated pulse we are falling from **0.48**, not 1.0 -- and the correction
is applied at full size regardless. That is the defect: a correction measured for
a complete transition, applied unscaled to a partial one.

The fix follows directly and needs no latch: scale the falling residual by the
gate state, which *is* how far the transition got. On a complete fall GUP is 1.0
at the start and the correction is unchanged; on a truncated one GUP is 0.48 and
the correction is halved, which is what it should be.

    KURES_F  ->  KURES_F * min(max(V(GUP), 0), 1)
    KDRES_F  ->  KDRES_F * min(max(V(GDN), 0), 1)

    py -3.14 scripts/residual_scaled_test.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
from pedestal_localization import best_lag, outward_window, read  # noqa: E402

R = ROOT / "results"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
TRANSISTOR_FULL = R / "defect_b_full_swing_2026-09-03" / "transistor" / "run.tr0"
OUT = R / "residual_scaled_2026-09-04"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
RISE_NS, EDGE_NS, STOP_NS = 5.000, 0.050, 22.0
WIDTHS = (2354, 2226, 2090, 1989, 1853, 1792, 1666, 1634, 1505)

# Scale the residual of the device that is turning **off**, by how far on it
# actually was. The device turning **on** starts from fully off whether the pulse
# was truncated or not, so its residual is already right and must be left alone.
#
# On the falling branch the pull-up turns off (scale KURES_F by GUP) and the
# pull-down turns on (leave KDRES_F). On the rising branch it is the other way
# round, so KDRES_R is the one to scale.
#
# Scaling KDRES_F instead -- the first thing tried -- multiplies by a GDN that is
# ~0 at the reversal and so deletes the pull-down residual outright. The aggregate
# RMSE still improved, but the Kd *shape* lost the negative excursion that both
# the transistor and native have after the reversal. A number can hide that; the
# shape cannot.
# Both falling-branch residuals scale with **GUP**, not with each device's own
# gate. The falling residual corrects a reversal out of a pull-up-on state, and
# how big that correction should be is set by how far the pull-up actually got --
# which is GUP. The pull-down's own gate is ~0 at the reversal and says nothing
# about the size of the transition being corrected.
#
# Measured at 1792 ps: ours -0.171 against the transistor's -0.085 at +96 ps, a
# factor of 2.0, and GUP at the reversal is 0.498. That is the factor.
SELECTORS = {
    "KURES_TABLE": ("V(KURES_F)", "GUPHOLD"),
    "KDRES_TABLE": ("V(KDRES_F)", "GUPHOLD"),
}

# Scaling by the *instantaneous* GUP gets the peak of Kd's negative excursion
# exactly right (-0.081 against the transistor's -0.085 at +96 ps) and then kills
# the tail (-0.009 against -0.058 at +204 ps), because GUP itself is decaying
# through the fall. What the residual needs is how far the pull-up got **at the
# reversal**, held.
#
# A peak-hold gives that without latching an edge pulse -- which this project has
# already found does not work, since the pulses are a couple of timesteps wide and
# the latch charges partway. This tracks GUP upward almost instantly and leaks
# down over 5 ns, so it reads the reversal value throughout the fall and forgets
# it before the next event.
PEAK_HOLD = """BGUPHOLD GUPHOLD 0 I = -1e-12 * ((V(GUP) > V(GUPHOLD)) ? (V(GUP) - V(GUPHOLD)) / 1p : (V(GUP) - V(GUPHOLD)) / 5n)
CGUPHOLD GUPHOLD 0 1e-12 ic=0
RGUPHOLD GUPHOLD 0 1e12
"""


def build(tag: str, scaled: bool, width_ps: int | None) -> Path:
    d = OUT / tag / (f"w{width_ps}" if width_ps else "full")
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "driver.sub").exists():
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                            model_name=MODEL, component_name=COMPONENT)
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                        str(d / "driver.sub"))
        if scaled:
            text = (d / "driver.sub").read_text(encoding="utf-8")
            for node, (target, gate) in SELECTORS.items():
                # Wrap just that one V(...) reference wherever it sits in the
                # selector line: KURES_F is the else-branch, KDRES_R the then.
                pat = rf"^(B\S+ {node} 0 V = .*?){re.escape(target)}"
                new = rf"\1({target} * min(max(V({gate}), 0), 1))"
                text, n = re.subn(pat, new, text, count=1, flags=re.M)
                if n != 1:
                    raise RuntimeError(f"{node}: selector not found")
            # Insert the peak-hold just before the line that first uses it.
            anchor = "BKURES_TABLE"
            i = text.index(anchor)
            text = text[:i] + PEAK_HOLD + text[i:]
            (d / "driver.sub").write_text(text, encoding="utf-8")
    fall = RISE_NS + (10.0 if width_ps is None else width_ps / 1000.0)
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  "
           f"{fall}n {SUPPLY}  {fall + EDGE_NS}n 0  {STOP_NS}n 0)")
    (d / "run.sp").write_text(
        dk.ngspice_header()
        + ".include driver.sub\n"
        + dk.supply("VCC", SUPPLY, name="Vdd")
        + f"Vin IN 0 {pwl}\n"
        + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
        + sub.instance("X1")
        + dk.load("OUT", R_LOAD, C_LOAD_PF)
        + f".tran 0.002n {STOP_NS}n\n.save V(OUT) V(X1.ku) V(X1.kd)\n.end\n",
        encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1200) is None:
            raise RuntimeError(f"{d} failed")
    return d


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("  Pedestal against native over the outward leg, ps, residual in "
          "brackets;\n  and pad RMSE against the transistor, mV.\n")
    print(f"    {'width':<9}{'shipped':>18}{'residual scaled':>18}"
          f"{'RMSE ship':>11}{'RMSE scaled':>13}")
    ped_a, ped_b, rm_a, rm_b = [], [], [], []
    for width in WIDTHS:
        ref = read(MATRIX / f"io_buf_short_high_w{width}ps.csv")
        t_ref = ref["time_ns"]
        lo, hi = outward_window(t_ref, ref["silicon_pad"], RISE_NS)
        g = np.arange(lo, hi, 0.002)
        nat = np.interp(g, t_ref, ref["hspice_pad"])
        si = np.interp(g, t_ref, ref["silicon_pad"])
        cells = []
        for tag, scaled in (("shipped", False), ("scaled", True)):
            d = build(tag, scaled, width)
            raw = sl.parse_ngspice_raw(d / "run.raw")
            pad = np.interp(g, sl.time_ns(raw), sl.trace(raw, "out"))
            lag, res = best_lag(g, nat, pad, lo, hi)
            rmse = float(np.sqrt(np.mean((pad - si) ** 2))) * 1e3
            cells.append((lag, res, rmse))
        (la, ra, ma), (lb, rb, mb) = cells
        ped_a.append(la); ped_b.append(lb); rm_a.append(ma); rm_b.append(mb)
        print(f"    {width:<9}{f'{la:+.0f}({ra:.2f})':>18}"
              f"{f'{lb:+.0f}({rb:.2f})':>18}{ma:>11.1f}{mb:>13.1f}")
    print(f"    {'mean':<9}{np.mean(np.abs(ped_a)):>18.0f}"
          f"{np.mean(np.abs(ped_b)):>18.0f}{np.mean(rm_a):>11.1f}"
          f"{np.mean(rm_b):>13.1f}")

    print("\n  The unstressed control, against the transistor:")
    tr = sl.parse_hspice_tr0(TRANSISTOR_FULL)
    gg = np.arange(4.5, 21.5, 0.002)
    si = np.interp(gg, sl.time_ns(tr), sl.trace(tr, "pad"))
    base = float(np.median(si[gg < 4.8]))
    half = 0.5 * (float(si.max()) + base)
    si_r = sl.cross(gg, si, half, rising=True, after=4.9)
    si_f = sl.cross(gg, si, half, rising=False, after=15.0)
    print(f"    {'build':<18}{'peak err (mV)':>15}{'rise err (ps)':>15}"
          f"{'fall err (ps)':>15}{'RMSE (mV)':>12}")
    for tag, scaled in (("shipped", False), ("residual scaled", True)):
        d = build("shipped" if not scaled else "scaled", scaled, None)
        raw = sl.parse_ngspice_raw(d / "run.raw")
        y = np.interp(gg, sl.time_ns(raw), sl.trace(raw, "out"))
        r = sl.cross(gg, y, half, rising=True, after=4.9)
        f = sl.cross(gg, y, half, rising=False, after=15.0)
        print(f"    {tag:<18}{(y.max()-si.max())*1e3:>15.1f}"
              f"{(r-si_r)*1e3:>15.1f}{(f-si_f)*1e3:>15.1f}"
              f"{float(np.sqrt(np.mean((y-si)**2)))*1e3:>12.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
