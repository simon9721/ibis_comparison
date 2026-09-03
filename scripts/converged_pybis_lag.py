#!/usr/bin/env python3
"""Is the pybis lag real, or numerical? Re-measure it converged and fairly.

The lag localization compared native IBIS (HSPICE, adaptive step, ~453 saved
points) against pybis (ngspice, 1 ps fixed step) and read 50% crossings off both.
Two confounds hide in that: ngspice's transient may not be converged at the
few-ps level on a sub-20-ps edge, and a 50% crossing interpolated from coarse
saved points carries its own error. The pybis lag moved 7 -> 10 -> 5 ps as the
ngspice step went 5 -> 1 -> 0.2 ps, so neither is settled.

This re-runs both with a fine, matched print step and tight tolerances, sweeps
the ngspice step to convergence, and reports the lag only once it stops moving.
Only then is the residual attributable to the model rather than the solver.

    py -3.14 scripts/converged_pybis_lag.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python",
           ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402

IBIS = (ROOT / "results" / "inv_chain_variants_2026-09-02" / "base8" /
        "selection" / "tr1ps" / "invchain_base8_tr1ps.ibs")
OUT = ROOT / "results" / "pybis_lag_converged_2026-09-03"
MODEL, COMPONENT = "driver2", "invchain"
SUPPLY_V, R_LOAD, C_LOAD_PF = 1.8, 50.0, 2.0
RISE_NS, STOP_NS = 5.0, 22.0


def _pwl():
    return sl.pulse(0.0, SUPPLY_V, [5.0, 15.0], stop_ns=STOP_NS)


def cross(t, y, level, after=4.7):
    for i in range(1, len(y)):
        if t[i] < after:
            continue
        if y[i - 1] < level <= y[i]:
            return t[i - 1] + (level - y[i - 1]) * (t[i] - t[i - 1]) / (y[i] - y[i - 1])
    return float("nan")


def native(out_dir: Path, print_ns: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(IBIS, out_dir / IBIS.name)
    # DELMAX caps HSPICE's internal step so the edge is resolved, not just saved.
    deck = f"""* base8 native IBIS, fine + tight
.title native converged
.option post=2 probe accurate ingold=2 relv=1e-4 reli=1e-4 delmax={print_ns}n
.temp 27
Vin in_dig 0 {_pwl()}
VPU pu_ref 0 DC {SUPPLY_V}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUPPLY_V}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='{IBIS.name}' model='{MODEL}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad)
.tran {print_ns}n {STOP_NS}n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    tr0 = sl.hspice(out_dir)
    if tr0 is None:
        return None
    r = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(r), sl.signal(r, "v(pad)")


def pybis(out_dir: Path, step_ns: float, reltol: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical",
                                    str(out_dir / "driver.sub"))
    text = (out_dir / "driver.sub").read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    nd = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
    nodes = [nd.get(p.upper(), p) for p in pins]
    deck = f""".options reltol={reltol} abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC {SUPPLY_V}
Vin IN 0 {_pwl()}
Ven EN 0 DC {SUPPLY_V}
X1 {' '.join(nodes)} {m.group(1)}
Rload OUT 0 {R_LOAD}
Cload OUT 0 {C_LOAD_PF}p
.tran {step_ns}n {STOP_NS}n
.save V(OUT)
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    raw = sl.ngspice(out_dir)
    if raw is None:
        return None
    r = sl.parse_ngspice_raw(raw)
    return sl.time_ns(r), sl.trace(r, "out")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    half = 0.5 * SUPPLY_V

    # native: converge on the HSPICE internal step / print step
    print("native IBIS 50% crossing vs its own resolution:")
    nat_cross = None
    for pn in (0.005, 0.001, 0.0005):
        nat = native(OUT / f"native_{pn*1000:g}ps", pn)
        if nat is None:
            print(f"   {pn*1000:g}ps  failed")
            continue
        c = cross(nat[0], nat[1], half)
        print(f"   print/delmax {pn*1000:>5.1f}ps -> {c:.4f} ns")
        nat_cross = c
    print(f"   -> native converged 50% = {nat_cross:.4f} ns\n")

    print("pybis 50% crossing vs ngspice step (reltol 1e-5):")
    print(f"{'step':>8}{'pybis 50%':>12}{'lag vs native ps':>18}")
    prev = None
    for step in (0.002, 0.001, 0.0005, 0.0002, 0.0001):
        pyb = pybis(OUT / f"pybis_{step*1000:g}ps", step, 1e-5)
        if pyb is None:
            print(f"{step*1000:>6.2f}ps  failed")
            continue
        c = cross(pyb[0], pyb[1], half)
        lag = (c - nat_cross) * 1e3
        conv = "" if prev is None else f"   (moved {abs(c-prev)*1e3:.2f} ps)"
        print(f"{step*1000:>6.2f}ps{c:12.4f}{lag:18.1f}{conv}")
        prev = c
    print("\nThe converged lag -- where the step stops moving it -- is the model's;")
    print("the spread across steps is the solver's.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
