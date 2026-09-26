#!/usr/bin/env python3
"""Scale the pull-up off-delay: every stress level, and the unstressed control.

`ku_overshoot_test.py` found the pedestal by looking at the Ku *shape* rather than
a fitted lag. Our Ku climbs past the reversal to 0.680 where native turns around
at 0.508, and shortening `pu_off` alone brings the peak down (0.680 -> 0.544) and
speeds the decay (345 -> 285 ps). On the pad at 1792 ps the pedestal against
native falls monotonically:

    shipped      85 ps      pu_off x0.25    19 ps
    pu_off x0.5  42         pu_off x0        0

with alignment residuals of 0.00-0.04 throughout, so the shape is kept rather than
traded away. The earlier sweep concluded "not the delays" because it scaled all
four together -- and `pu_on` pushes the other way (shortening it takes the Ku peak
from 0.680 up to 0.954), so the two cancelled into a non-monotonic mess.

Two things decide whether this is a fix rather than a fluke:

* does it hold across the **whole stress family**, or only at 1792 ps;
* does it damage the **unstressed** case, where the shipped model is already
  within 2-4 ps of native.

    py -3.14 scripts/pu_off_sweep.py
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
OUT = R / "pu_off_sweep_2026-09-04"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
RISE_NS, EDGE_NS, STOP_NS = 5.000, 0.050, 22.0
PU_OFF = 0.0676997420246

WIDTHS = (2354, 2226, 2090, 1989, 1853, 1792, 1666, 1634, 1505)
SCALES = (1.0, 0.5, 0.25, 0.0)


def build(scale: float, width_ps: int | None) -> Path:
    """width_ps None means the unstressed control: a 10 ns pulse."""
    tag = f"x{scale:g}".replace(".", "p")
    case = "full" if width_ps is None else f"w{width_ps}"
    d = OUT / tag / case
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "driver.sub").exists():
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                            model_name=MODEL, component_name=COMPONENT)
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                        str(d / "driver.sub"))
        text = (d / "driver.sub").read_text(encoding="utf-8")
        text, n = re.subn(rf"Td={re.escape(f'{PU_OFF:.12g}')}n",
                          f"Td={max(PU_OFF * scale, 1e-4):.12g}n", text)
        if n == 0:
            raise RuntimeError("pu_off not found")
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


def pad_of(d: Path):
    raw = sl.parse_ngspice_raw(d / "run.raw")
    return sl.time_ns(raw), sl.trace(raw, "out")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    print("  Pedestal: our pad against native's, over the outward leg, ps.")
    print("  Residual after alignment in brackets -- a rising residual means the")
    print("  shape is being traded for the number.\n")
    print(f"    {'width':<9}" + "".join(f"{f'pu_off x{s:g}':>16}" for s in SCALES))
    rmse_rows = []
    for width in WIDTHS:
        ref = read(MATRIX / f"io_buf_short_high_w{width}ps.csv")
        t_ref = ref["time_ns"]
        lo, hi = outward_window(t_ref, ref["silicon_pad"], RISE_NS)
        g = np.arange(lo, hi, 0.002)
        nat = np.interp(g, t_ref, ref["hspice_pad"])
        si = np.interp(g, t_ref, ref["silicon_pad"])
        cells, rmses = [], []
        for scale in SCALES:
            t, y = pad_of(build(scale, width))
            pad = np.interp(g, t, y)
            lag, res = best_lag(g, nat, pad, lo, hi)
            cells.append(f"{lag:+6.0f}({res:4.2f})")
            rmses.append(float(np.sqrt(np.mean((pad - si) ** 2))) * 1e3)
        print(f"    {width:<9}" + "".join(f"{c:>16}" for c in cells))
        rmse_rows.append((width, rmses))

    print("\n  Pad RMSE against the transistor over the same window, mV:")
    print(f"    {'width':<9}" + "".join(f"{f'x{s:g}':>10}" for s in SCALES))
    for width, rmses in rmse_rows:
        print(f"    {width:<9}" + "".join(f"{v:>10.1f}" for v in rmses))
    means = np.mean([r for _, r in rmse_rows], axis=0)
    print(f"    {'mean':<9}" + "".join(f"{v:>10.1f}" for v in means))

    print("\n  The unstressed control -- 10 ns pulse, these must not move:")
    print(f"    {'scale':<9}{'rise 50% (ns)':>16}{'fall 50% (ns)':>16}"
          f"{'peak (V)':>11}")
    for scale in SCALES:
        t, y = pad_of(build(scale, None))
        base = float(np.median(y[t < 4.8]))
        half = 0.5 * (float(np.max(y)) + base)
        a = sl.cross(t, y, half, rising=True, after=4.9)
        b = sl.cross(t, y, half, rising=False, after=15.0)
        print(f"    x{scale:<8g}{a:>16.4f}{b:>16.4f}{float(np.max(y)):>11.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
