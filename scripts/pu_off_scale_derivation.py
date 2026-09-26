#!/usr/bin/env python3
"""Re-derive PU_OFF_SCALE, which `residual_rescale_time_2026-09-04` got wrong.

That study set `pu_off` equal to the transistor's observed pull-up turn-around
(48 ps), reasoning that our fitted 68 ps put ours at 69-77 so 68 x 0.70 = 48
would land on it. It then dismissed x0.25 -- which scored far better -- as
"compensating rather than fixing".

That derivation double-counts the input edge ramp. Measured on the corrected
build (`ku_excess_decompose_2026-09-07`):

    pu_off 67.7 ps  ->  gate turns around at 96-98 ps
    pu_off 47.4 ps  ->  gate turns around at 75-78 ps

A 20.3 ps change in `pu_off` moves the turn-around by 20 ps -- 1:1 -- on a
constant offset of ~28.5 ps. That offset is the deck's own falling edge: the
input takes 50 ps to cross, so the command sees it at +25 ps, and the T-line
adds a few more.

So the turn-around is `pu_off + 28.5`, and landing it on the transistor's 47-51 ps
needs `pu_off ~ 19.5 ps`, i.e. a scale of **0.29** -- not 0.70. x0.25 gives 45 ps,
within 3 ps of the transistor. It was the measured answer all along.

This tests 0.70 against 0.29 and 0.25 on turn-around, Ku ratio, Kd, the stress
pedestal and the unstressed control.

    py -3.14 scripts/pu_off_scale_derivation.py
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
OUT = R / "pu_off_scale_2026-09-07"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
RISE_NS, EDGE_NS, STOP_NS = 5.000, 0.050, 22.0
WIDTHS = (2354, 2226, 2090, 1989, 1853, 1792, 1666, 1634, 1505)
PROBES = ("ku", "kd", "gup", "kugate_base", "kures_table")

PU_OFF = 0.0676997420246
SCALES = {"x0.70 (old)": 0.70, "x0.29 (derived)": 0.29, "x0.25": 0.25}

PEAK_HOLD = (
    "BGUPHOLD GUPHOLD 0 I = -1e-12 * ((V(GUP) > V(GUPHOLD)) ? "
    "(V(GUP) - V(GUPHOLD)) / 1p : (V(GUP) - V(GUPHOLD)) / 5n)\n"
    "CGUPHOLD GUPHOLD 0 1e-12 ic=0\n"
    "RGUPHOLD GUPHOLD 0 1e12\n"
    "BFRAC FRAC 0 V = min(max(V(GUPHOLD), 0.05), 1.0)\n"
)


def patch(text: str, scale: float) -> str:
    anchor = "BKURES_TABLE"
    text = text[:text.index(anchor)] + PEAK_HOLD + text[text.index(anchor):]
    for node, target in (("KURES_TABLE", "V(KURES_F)"),
                         ("KDRES_TABLE", "V(KDRES_F)")):
        pat = rf"^(B\S+ {node} 0 V = .*?){re.escape(target)}"
        text, n = re.subn(pat, rf"\1({target} * V(FRAC))", text, count=1, flags=re.M)
        if n != 1:
            raise RuntimeError(f"{node}: selector not found")
    text, n = re.subn(rf"Td={re.escape(f'{PU_OFF:.12g}')}n",
                      f"Td={PU_OFF * scale:.12g}n", text)
    if n == 0:
        raise RuntimeError("pu_off not found")
    return text


def build(tag: str, scale: float, width_ps: int | None) -> Path:
    d = OUT / tag.replace(" ", "_").replace("(", "").replace(")", "") / \
        (f"w{width_ps}" if width_ps else "full")
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "driver.sub").exists():
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                            model_name=MODEL, component_name=COMPONENT)
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                        str(d / "driver.sub"))
        (d / "driver.sub").write_text(
            patch((d / "driver.sub").read_text(encoding="utf-8"), scale),
            encoding="utf-8")
    fall = RISE_NS + (10.0 if width_ps is None else width_ps / 1000.0)
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  "
           f"{fall}n {SUPPLY}  {fall + EDGE_NS}n 0  {STOP_NS}n 0)")
    saves = " ".join(f"V(X1.{p})" for p in PROBES)
    (d / "run.sp").write_text(
        dk.ngspice_header() + ".include driver.sub\n"
        + dk.supply("VCC", SUPPLY, name="Vdd")
        + f"Vin IN 0 {pwl}\n"
        + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
        + sub.instance("X1") + dk.load("OUT", R_LOAD, C_LOAD_PF)
        + f".tran 0.002n {STOP_NS}n\n.save V(OUT) {saves}\n.end\n",
        encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1200) is None:
            raise RuntimeError(f"{d} failed -- see ngspice.log")
    return d


def turn(t, y, lo=-0.02, hi=0.30):
    g = np.arange(lo, hi, 0.001)
    v = np.interp(g, t, y)
    return float(g[int(np.argmax(v))]) * 1e3


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    win = np.arange(0.090, 0.400, 0.002)

    print("  Pull-up turn-around, ps after the reversal. Reference: the")
    print("  transistor at 47-51 ps, native at 48-49.\n")
    print(f"    {'width':<8}{'transistor':>12}{'native':>9}"
          + "".join(f"{k:>18}" for k in SCALES))
    for w in WIDTHS:
        ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
        t = ref["time_ns"] - (RISE_NS + w / 1000.0)
        cells = []
        for tag, sc in SCALES.items():
            raw = sl.parse_ngspice_raw(build(tag, sc, w) / "run.raw")
            tt = sl.time_ns(raw) - (RISE_NS + w / 1000.0)
            cells.append(turn(tt, sl.signal(raw, "v(x1.kugate_base)")))
        print(f"    {w:<8}{turn(t, ref['silicon_ku']):>12.0f}"
              f"{turn(t, ref['hspice_ku']):>9.0f}"
              + "".join(f"{c:>18.0f}" for c in cells))

    print("\n  Ku ratio to the transistor over +90..+400 ps (native is 1.07),")
    print("  and Ku / Kd rms against the transistor.\n")
    print(f"    {'width':<8}" + "".join(f"{k:>18}" for k in SCALES))
    agg = {k: {"q": [], "ru": [], "rd": []} for k in SCALES}
    for w in WIDTHS:
        ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
        t = ref["time_ns"] - (RISE_NS + w / 1000.0)
        si_u = np.interp(win, t, ref["silicon_ku"])
        si_d = np.interp(win, t, ref["silicon_kd"])
        ok = np.abs(si_u) > 0.03
        cells = []
        for tag, sc in SCALES.items():
            raw = sl.parse_ngspice_raw(build(tag, sc, w) / "run.raw")
            tt = sl.time_ns(raw) - (RISE_NS + w / 1000.0)
            ku = np.interp(win, tt, sl.signal(raw, "v(x1.ku)"))
            kd = np.interp(win, tt, sl.signal(raw, "v(x1.kd)"))
            q = float(np.median(ku[ok] / si_u[ok]))
            agg[tag]["q"].append(q)
            agg[tag]["ru"].append(float(np.sqrt(np.mean((ku - si_u) ** 2))))
            agg[tag]["rd"].append(float(np.sqrt(np.mean((kd - si_d) ** 2))))
            cells.append(q)
        print(f"    {w:<8}" + "".join(f"{c:>18.2f}" for c in cells))
    print(f"    {'mean q':<8}" + "".join(f"{np.mean(agg[k]['q']):>18.2f}" for k in SCALES))
    print(f"    {'Ku rms':<8}" + "".join(f"{np.mean(agg[k]['ru']):>18.4f}" for k in SCALES)
          + "     (native 0.0167)")
    print(f"    {'Kd rms':<8}" + "".join(f"{np.mean(agg[k]['rd']):>18.4f}" for k in SCALES)
          + "     (native 0.0107)")

    print("\n  Stress pedestal against native, ps, and pad RMSE vs the transistor, mV.\n")
    print(f"    {'width':<8}" + "".join(f"{k:>18}" for k in SCALES))
    ped = {k: [] for k in SCALES}
    rms = {k: [] for k in SCALES}
    for w in WIDTHS:
        ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
        t_ref = ref["time_ns"]
        lo, hi = outward_window(t_ref, ref["silicon_pad"], RISE_NS)
        g = np.arange(lo, hi, 0.002)
        nat = np.interp(g, t_ref, ref["hspice_pad"])
        si = np.interp(g, t_ref, ref["silicon_pad"])
        cells = []
        for tag, sc in SCALES.items():
            raw = sl.parse_ngspice_raw(build(tag, sc, w) / "run.raw")
            pad = np.interp(g, sl.time_ns(raw), sl.trace(raw, "out"))
            lag, res = best_lag(g, nat, pad, lo, hi)
            ped[tag].append(abs(lag))
            rms[tag].append(float(np.sqrt(np.mean((pad - si) ** 2))) * 1e3)
            cells.append(f"{lag:+.0f}({res:.2f})")
        print(f"    {w:<8}" + "".join(f"{c:>18}" for c in cells))
    print(f"    {'mean ped':<8}" + "".join(f"{np.mean(ped[k]):>18.0f}" for k in SCALES))
    print(f"    {'mean RMSE':<8}" + "".join(f"{np.mean(rms[k]):>18.1f}" for k in SCALES))

    print("\n  The unstressed control, against the transistor:")
    tr = sl.parse_hspice_tr0(TRANSISTOR_FULL)
    gg = np.arange(4.5, 21.5, 0.002)
    si = np.interp(gg, sl.time_ns(tr), sl.trace(tr, "pad"))
    half = 0.5 * (float(si.max()) + float(np.median(si[gg < 4.8])))
    si_r = sl.cross(gg, si, half, rising=True, after=4.9)
    si_f = sl.cross(gg, si, half, rising=False, after=15.0)
    print(f"    {'scale':<18}{'peak err (mV)':>15}{'rise err (ps)':>15}"
          f"{'fall err (ps)':>15}{'RMSE (mV)':>12}")
    for tag, sc in SCALES.items():
        raw = sl.parse_ngspice_raw(build(tag, sc, None) / "run.raw")
        y = np.interp(gg, sl.time_ns(raw), sl.trace(raw, "out"))
        r = sl.cross(gg, y, half, rising=True, after=4.9)
        f = sl.cross(gg, y, half, rising=False, after=15.0)
        print(f"    {tag:<18}{(y.max()-si.max())*1e3:>15.1f}{(r-si_r)*1e3:>15.1f}"
              f"{(f-si_f)*1e3:>15.1f}"
              f"{float(np.sqrt(np.mean((y-si)**2)))*1e3:>12.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
