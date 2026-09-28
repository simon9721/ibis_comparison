# -*- coding: utf-8 -*-
"""Assemble the findings tables from the two result CSVs, and check the implied boundary.

The fit is never told the supply or V_th. If a form is physically right, the boundary
it implies at full gate drive should land near the device's own - and should be LARGER
on the 3.3 V part (ex2) than on the 1.8 V part (inv_chain).
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

D = Path(r"C:\Users\sh3qm\code\ibis_comparison\results\device_taper_2026-09-28")
rows = list(csv.DictReader(open(D / "results.csv"))) + list(csv.DictReader(open(D / "results_vsat.csv")))

ORDER = ["linear_const", "parab_const", "linear_ov", "parab_ov", "parab_vsat"]
NAME = {"linear_const": "min(1, d/x_lin)   fixed edge  [TODAY]",
        "parab_const":  "q(2-q), d/x_lin   fixed edge",
        "linear_ov":    "min(1, d/ov)      moving edge",
        "parab_ov":     "q(2-q), d/ov      LONG-CHANNEL",
        "parab_vsat":   "q(2-q), d/ov^(p/2)  VELOCITY-SAT"}

by = defaultdict(dict)
for r in rows:
    by[(r["device"], r["kind"])][int(r["width_ps"])] = r

for dev in ("ex2", "inv_chain"):
    ws = sorted({int(r["width_ps"]) for r in rows if r["device"] == dev})
    print(f"\n=== {dev} ===")
    print(f"  {'form':<38}{'n':>2}{'fullrms':>9}" + "".join(f"{w:>8}" for w in ws)
          + f"{'mean|e|':>9}{'wavrms':>8}{'vt':>7}{'edge@1':>8}")
    meas = [float(by[(dev, 'linear_const')][w]["meas_max"]) for w in ws]
    print(f"  {'measured':<38}{'':>2}{'':>9}" + "".join(f"{m:>8.3f}" for m in meas))
    for k in ORDER:
        d = by[(dev, k)]
        if not d:
            continue
        r0 = d[ws[0]]
        n, fr, vt = int(r0["n_params"]), float(r0["full_rms"]), float(r0["vt"])
        preds = [float(d[w]["pred_max"]) for w in ws]
        errs = [p - m for p, m in zip(preds, meas)]
        mae = sum(abs(e) for e in errs) / len(errs)
        wav = sum(float(d[w]["rms"]) for w in ws) / len(ws)
        if k.endswith("_const"):
            edge = float(r0["x_lin"])
        elif k.endswith("_ov"):
            edge = 1.0 - vt
        else:
            edge = (1.0 - vt) ** 0.5
        print(f"  {NAME[k]:<38}{n:>2}{fr:>9.4f}" + "".join(f"{p:>8.3f}" for p in preds)
              + f"{mae:>9.3f}{wav:>8.4f}{vt:>7.3f}{edge:>8.3f}")
    print(f"  {'errors, TODAY':<38}" + " " * 11 + "".join(
        f"{p-m:>+8.3f}" for p, m in zip([float(by[(dev, 'linear_const')][w]['pred_max']) for w in ws], meas)))
    print(f"  {'errors, VELOCITY-SAT':<38}" + " " * 11 + "".join(
        f"{p-m:>+8.3f}" for p, m in zip([float(by[(dev, 'parab_vsat')][w]['pred_max']) for w in ws], meas)))

print("\n=== the boundary each form implies at FULL drive, vs the real device ===")
print("  (check_xlin.py: 1.8 V parts 0.77 NMOS / 0.80 PMOS; 3.3 V parts 0.88 / 0.89)")
phys = {"ex2": (3.3, 0.88, 0.89), "inv_chain": (1.8, 0.77, 0.80)}
print(f"  {'buffer':<12}{'supply':>7}{'today':>8}{'long-chan':>11}{'vel-sat':>9}{'real device':>14}")
for dev in ("ex2", "inv_chain"):
    v, lo, hi = phys[dev]
    lc = 1.0 - float(by[(dev, "parab_ov")][sorted({int(r['width_ps']) for r in rows if r['device']==dev})[0]]["vt"])
    vs = (1.0 - float(by[(dev, "parab_vsat")][sorted({int(r['width_ps']) for r in rows if r['device']==dev})[0]]["vt"])) ** 0.5
    print(f"  {dev:<12}{v:>6.1f}V{0.45:>8.3f}{lc:>11.3f}{vs:>9.3f}{f'{lo:.2f}-{hi:.2f}':>14}")
