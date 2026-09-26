#!/usr/bin/env python3
"""Is the stress pedestal the fitted command delays?

`pedestal_localization.py` showed the pedestal is already present in Ku and Kd at
the same size as in the pad, so it is made upstream of the output stage. And on
io_buf, native's Ku tracks the transistor's own Ku to +1..+19 ps while ours is
+64..+111 ps late -- so it is our coefficient timing that is wrong, not native's.

What generates our coefficient timing is the command layer, and it is built from
**two delayed copies of the input** combined with a gate:

    TPDCMDA NINX 0 PDCMDA 0 Td=0.850179n      the shorter delay
    TPDCMDB NINX 0 PDCMDB 0 Td=1.831336n      the longer one
    BPDCMDLVL = (V(PDCMDA) > 0.5) || (V(PDCMDB) > 0.5)

The gap between the two copies is what sets when the command turns on and off.
Fitted per device:

    io_buf      PU 0.925 ns   PD 0.981 ns      pulses 1.505 - 2.354 ns
    ex2         PU 0.333      PD 0.275         pulses 0.688 - 0.975
    inv_chain   PU 0.021      PD 0.035         pulses 0.104 - 0.135

On io_buf the gap is **half the entire stressed pulse**. When the pulse is that
short the two delayed copies straddle the next input edge, and the gate sees a
combination it never sees on a long pulse -- which is exactly the shape of a
defect that is absent at full swing and present under stress.

This tests it the only way that settles it: scale every fitted delay and see
whether the pedestal follows. Measured as the lag of our pad against native's
over the outward leg, on io_buf's own stressed case.

    py -3.14 scripts/delay_pedestal_test.py
"""
from __future__ import annotations

import csv
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
REFCASE = (R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
           / "io_buf_short_high_w1792ps.csv")
OUT = R / "delay_pedestal_2026-09-04"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
RISE_NS, FALL_NS, EDGE_NS, STOP_NS = 5.000, 6.790, 0.050, 22.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"

# The four fitted delays in io_buf's model, in ns. Everything else on a Td= line
# (the 10 ps edge_delay transmission lines) is left alone.
FITTED = (0.992580638109, 0.0676997420246, 1.83133633792, 0.850179083174)
# The gate-state lag time constants, inline in the BGUP/BGDN current expressions
# rather than on a Td= line: GUP rise/fall then GDN rise/fall.
TAUS = ("1.12696960112n", "0.11221276864n", "0.27130163155n", "0.244985656311n")
SCALES = (1.0, 0.5, 0.25, 0.05)


def build(scale: float, mode: str = "delay") -> Path:
    d = OUT / mode / f"x{scale:g}".replace(".", "p")
    d.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                    str(d / "driver.sub"))
    text = (d / "driver.sub").read_text(encoding="utf-8")
    hits = 0
    if mode == "delay":
        for value in FITTED:
            # A transmission line needs a positive delay, so a small floor
            # replaces what would otherwise be Td=0.
            new = max(value * scale, 1e-4)
            text, n = re.subn(rf"Td={re.escape(f'{value:.12g}')}n",
                              f"Td={new:.12g}n", text)
            hits += n
    else:
        for token in TAUS:
            new = max(float(token.rstrip("n")) * scale, 1e-5)
            text, n = re.subn(re.escape(token), f"{new:.12g}n", text)
            hits += min(n, 1)
    if hits < 4:
        raise RuntimeError(f"{mode} scale {scale}: patched only {hits} of 4")
    (d / "driver.sub").write_text(text, encoding="utf-8")

    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  "
           f"{FALL_NS}n {SUPPLY}  {FALL_NS + EDGE_NS}n 0  {STOP_NS}n 0)")
    deck = (dk.ngspice_header()
            + ".include driver.sub\n"
            + dk.supply("VCC", SUPPLY, name="Vdd")
            + f"Vin IN 0 {pwl}\n"
            + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
            + sub.instance("X1")
            + dk.load("OUT", R_LOAD, C_LOAD_PF)
            + f".tran 0.002n {STOP_NS}n\n.save V(OUT)\n.end\n")
    (d / "run.sp").write_text(deck, encoding="utf-8")
    return d


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ref = read(REFCASE)
    t_ref = ref["time_ns"]
    lo, hi = outward_window(t_ref, ref["silicon_pad"], RISE_NS)
    grid = np.arange(lo, hi, 0.002)
    native = np.interp(grid, t_ref, ref["hspice_pad"])
    silicon = np.interp(grid, t_ref, ref["silicon_pad"])

    print("  io_buf short high 1792 ps. Lag of our pad over the outward leg, ps")
    print("  (+ = ours later). The pedestal is our pad against native's.\n")
    for mode, label in (("delay", "command transport delays"),
                        ("tau", "gate-state time constants")):
        print(f"\n  Scaling the {label}:")
        print(f"    {'scale':<14}{'vs native':>12}{'vs transistor':>15}")
        for scale in SCALES:
            d = build(scale, mode)
            if not (d / "run.raw").exists():
                if sl.ngspice(d, timeout_s=1200) is None:
                    print(f"    x{scale:<13g} run failed -- see ngspice.log")
                    continue
            raw = sl.parse_ngspice_raw(d / "run.raw")
            ours = np.interp(grid, sl.time_ns(raw), sl.trace(raw, "out"))
            a, _ = best_lag(grid, native, ours, lo, hi)
            b, _ = best_lag(grid, silicon, ours, lo, hi)
            print(f"    x{scale:<13g}{a:>12.0f}{b:>15.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
