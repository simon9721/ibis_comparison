# -*- coding: utf-8 -*-
"""Does our fitted x_lin match the textbook saturation/triode boundary, or is it an
effective parameter absorbing the real I-V?

Textbook (long channel, full gate drive): the conducting device stays saturated while its
headroom exceeds its overdrive, so the resistive zone occupies a fraction

    x_lin_book = (V_DD - V_th) / V_DD = 1 - V_th/V_DD

of the swing. Compare against what we actually fit.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/sh3qm/code/ibis_comparison")
sys.path.insert(0, str(ROOT / "scripts"))
import stage_count_from_file as sc          # noqa: E402
import gate_ramp_prototype as gp            # noqa: E402

VTH_N, VTH_P = 0.3627858, 0.4064886          # VTH0 from buffers/models/hspice.mod

print("textbook expectation, x_lin = 1 - V_th/V_DD  (full gate drive):")
for vdd in (1.8, 3.3):
    print(f"   V_DD {vdd} V :  NMOS {1 - VTH_N / vdd:.2f}   PMOS {1 - VTH_P / vdd:.2f}")

print("\nwhat the fit actually lands on (est_knee, pull-up), per buffer:")
d = sc.OUT / "step1"
for f in sorted(d.glob("est_knee__*__pull-up.csv")):
    dev = f.name.split("__")[1]
    rows = {int(r["K"]): r for r in csv.DictReader(f.open())}
    best = min(rows.values(), key=lambda r: float(r["rms"]))
    vdd = gp.VARIANTS[dev][0] if dev in gp.VARIANTS else None
    print(f"   {dev:14s} V_DD {vdd}   K={best['K']:>2s}   vt={float(best['vt']):.3f}   "
          f"x_lin={float(best['x_lin']):.3f}")
