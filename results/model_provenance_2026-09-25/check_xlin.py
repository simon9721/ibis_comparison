# -*- coding: utf-8 -*-
"""Does our fitted x_lin match the saturation/triode boundary, or is it an effective
parameter absorbing the real I-V?

    x_lin_longchannel = (V_DD - V_th) / V_DD = 1 - V_th/V_DD

CORRECTION, 2026-09-28. Two things were wrong with using that as the yardstick, and
both inflated it:

 1. It is a long-channel PREDICTION, not a measurement - the Shockley V_DSAT = V_GS - V_TH,
    which is exactly what the alpha-power law says fails for short-channel devices.
    Measured on the devices as drawn (scripts/device_alpha_extract.py, HSPICE,
    Sakurai-Newton Appendix A), V_D0/V_DD is:

        ex2 NMOS  0.6um  0.347      ex2 PMOS  0.6um  0.420
        inv NMOS  180nm  0.232      inv PMOS  180nm  0.400

    against the 0.66-0.89 predicted below. So x_lin = 0.45 is CLOSE to the device and
    the prediction was not: the number was right and its stated justification was wrong.
    The same runs measure alpha at 1.11-1.39, which supports p = 1 over p = 2.

 2. VTH0 below is from buffers/models/hspice.mod and was applied to every buffer, but
    inv_chain runs on buffers/inv_chain/HL18G-S3.7S.lib (models nch_tn/pch_tn, 180 nm
    drawn), whose VTH0 is 0.464/0.613. The "1.8 V" row was never inv_chain's device.

Both rows are printed below so the size of the error is visible. Prefer the measured
numbers for any new claim.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/sh3qm/code/ibis_comparison")
sys.path.insert(0, str(ROOT / "scripts"))
import stage_count_from_file as sc          # noqa: E402
import gate_ramp_prototype as gp            # noqa: E402

VTH_N, VTH_P = 0.3627858, 0.4064886          # VTH0 from buffers/models/hspice.mod  (ex2, io_buf)
HL_N, HL_P = 0.46435, 0.61250                # VTH0 from buffers/inv_chain/HL18G-S3.7S.lib (inv_*)

# measured, not predicted - scripts/device_alpha_extract.py
MEASURED = {"ex2 (3.3 V, 0.6 um)": (0.347, 0.420), "inv_chain (1.8 V, 180 nm)": (0.232, 0.400)}

print("long-channel PREDICTION, x_lin = 1 - V_th/V_DD  (full gate drive):")
print(f"   ex2 / io_buf   V_DD 3.3 V :  NMOS {1 - VTH_N / 3.3:.2f}   PMOS {1 - VTH_P / 3.3:.2f}   (hspice.mod)")
print(f"   inv_chain      V_DD 1.8 V :  NMOS {1 - HL_N / 1.8:.2f}   PMOS {1 - HL_P / 1.8:.2f}   (HL18G)")
print("   [the old version printed 0.77/0.80 for the 1.8 V row, using hspice.mod's VTH0,")
print("    which is not the card inv_chain uses]")
print("\nMEASURED V_D0/V_DD on the devices as drawn (Sakurai-Newton Appendix A):")
for k, (n, p_) in MEASURED.items():
    print(f"   {k:<26} NMOS {n:.3f}   PMOS {p_:.3f}")
print("   -> the real boundary is 0.23-0.42, so x_lin = 0.45 is close to it and the")
print("      long-channel prediction above is the thing that is wrong.")

print("\nwhat the fit actually lands on (est_knee, pull-up), per buffer:")
d = sc.OUT / "step1"
for f in sorted(d.glob("est_knee__*__pull-up.csv")):
    dev = f.name.split("__")[1]
    rows = {int(r["K"]): r for r in csv.DictReader(f.open())}
    best = min(rows.values(), key=lambda r: float(r["rms"]))
    vdd = gp.VARIANTS[dev][0] if dev in gp.VARIANTS else None
    print(f"   {dev:14s} V_DD {vdd}   K={best['K']:>2s}   vt={float(best['vt']):.3f}   "
          f"x_lin={float(best['x_lin']):.3f}")
