#!/usr/bin/env python3
"""Does pybis's explicit C_comp help or hurt against the transistor, across loads?

The lag localization showed pybis's explicit C_comp adds ~10 ps that native IBIS
does not, and that removing it matches native on one load (50 ohm + 2 pF). But
`solve_k_params_output` extracts Ku with the C_comp current subtracted
(`i1 = ... - i_c_comp`), so Ku is C_comp-free and adding an explicit C_comp back
is, in principle, the correct reconstruction. Theory and the one-load result
disagree, so this decides it empirically over the load space that C_comp
actually governs.

Four builds at each load, all measured against the transistor (ground truth):

    transistor              HSPICE on the base8 netlist
    native IBIS             HSPICE reading the .ibs
    pybis  (C_comp nominal) ngspice, the shipped output stage
    pybis  (C_comp = 0)     ngspice, explicit C_comp removed

C_comp matters most under a light load (little external C to swamp the die cap)
and least under a heavy one, so the loads span that: from 50 ohm with no extra
cap to a high-impedance, cap-dominated termination. If removing C_comp moves
pybis toward the transistor at every load, it is a genuine fix; if it helps at
some loads and hurts at others, the explicit C_comp is doing something real and
the fix has to be more careful than deletion.

    py -3.14 scripts/validate_pybis_ccomp.py
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python",
           ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402

VARIANT = ROOT / "results" / "inv_chain_variants_2026-09-02" / "base8"
IBIS = VARIANT / "selection" / "tr1ps" / "invchain_base8_tr1ps.ibs"
NETLIST_INPUTS = VARIANT / "inputs"
OUT = ROOT / "results" / "pybis_ccomp_validation_2026-09-03"

MODEL, COMPONENT = "driver2", "invchain"
SUPPLY_V = 1.8
C_COMP_PF = 0.468
RISE_NS, FALL_NS, STOP_NS = 5.0, 15.0, 22.0

SUPPLY_BLOCK = """.PARAM  vccr_typ  = 1.300V
.PARAM  vccq_typ  = 1.800V
.PARAM  vssq      = 0.000V
.PARAM  vss       = 0.000V"""

# label, R_load ohm, C_load pF. Light (cap-lean) to heavy (cap-dominated).
LOADS = [
    ("50R_0pF", 50.0, 0.0),
    ("50R_2pF", 50.0, 2.0),
    ("50R_10pF", 50.0, 10.0),
    ("500R_2pF", 500.0, 2.0),
    ("1k_5pF", 1000.0, 5.0),
]


def _pwl() -> str:
    return sl.pulse(0.0, SUPPLY_V, [RISE_NS, FALL_NS], stop_ns=STOP_NS)


def transistor(out_dir: Path, r_load: float, c_load: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("HL18G-S3.7S.lib", "invchain_base8_subckt_typ.sp"):
        shutil.copy2(NETLIST_INPUTS / name, out_dir / name)
    deck = f"""* base8 transistor
.title base8 transistor
.OPTIONS METHOD=GEAR GSHUNT=1E-12
.option post=2 probe accurate ingold=2
.temp 27
{SUPPLY_BLOCK}
.include 'invchain_base8_subckt_typ.sp'
Vdd vccq 0 DC {SUPPLY_V}
Vin in_dig 0 {_pwl()}
XDUT in_dig pad vccq 0 invchain
Rload pad 0 {r_load}
Cload pad 0 {c_load}p
.probe tran V(pad)
.tran 0.001n {STOP_NS}n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    tr0 = sl.hspice(out_dir)
    return (sl.time_ns(r := sl.parse_hspice_tr0(tr0)), sl.signal(r, "v(pad)")) if tr0 else None


def native(out_dir: Path, r_load: float, c_load: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(IBIS, out_dir / IBIS.name)
    deck = f"""* base8 native IBIS
.title base8 native ibis
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {_pwl()}
VPU pu_ref 0 DC {SUPPLY_V}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUPPLY_V}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='{IBIS.name}' model='{MODEL}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2
Rload pad 0 {r_load}
Cload pad 0 {c_load}p
.probe tran V(pad)
.tran 0.001n {STOP_NS}n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    tr0 = sl.hspice(out_dir)
    return (sl.time_ns(r := sl.parse_hspice_tr0(tr0)), sl.signal(r, "v(pad)")) if tr0 else None


def pybis(out_dir: Path, r_load: float, c_load: float, c_comp_pf: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical",
                                    str(out_dir / "driver.sub"))
    text = (out_dir / "driver.sub").read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    node = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
    nodes = [node.get(p.upper(), p) for p in pins]
    deck = f"""* base8 pybis, C_comp override
.include driver.sub
Vdd VCC 0 DC {SUPPLY_V}
Vin IN 0 {_pwl()}
Ven EN 0 DC {SUPPLY_V}
X1 {' '.join(nodes)} {m.group(1)} C_comp={c_comp_pf * 1e-12:.6e}
Rload OUT 0 {r_load}
Cload OUT 0 {c_load}p
.tran 0.001n {STOP_NS}n
.save V(OUT)
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    raw = sl.ngspice(out_dir)
    return (sl.time_ns(r := sl.parse_ngspice_raw(raw)), sl.trace(r, "out")) if raw else None


def score(model, ref, window):
    tm, pm = model
    tr, pr = ref
    grid = np.linspace(*window, 40000)
    a, b = np.interp(grid, tm, pm), np.interp(grid, tr, pr)
    rmse = float(np.sqrt(np.trapezoid((a - b) ** 2, grid) / (grid[-1] - grid[0]))) * 1e3
    half = 0.5 * (np.nanmax(b) + np.nanmin(b))

    def cross(t, y, rising, after):
        for i in range(1, len(y)):
            if t[i] < after:
                continue
            if (rising and y[i - 1] < half <= y[i]) or (not rising and y[i - 1] > half >= y[i]):
                return t[i - 1] + (half - y[i - 1]) * (t[i] - t[i - 1]) / (y[i] - y[i - 1])
        return float("nan")

    shift = (cross(grid, a, True, RISE_NS - 0.3) - cross(grid, b, True, RISE_NS - 0.3)) * 1e3
    return rmse, shift


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = (args.out if args.out.is_absolute() else ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    window = (RISE_NS - 0.3, RISE_NS + 4.0)

    print(f"{'load':<10}{'native RMSE':>12}{'pyb Ccomp':>11}{'pyb noCcomp':>13}"
          f"  | {'native ps':>10}{'pyb Cc ps':>10}{'pyb no ps':>10}")
    rows = []
    for label, r_load, c_load in LOADS:
        case = out / label
        tr = transistor(case / "transistor", r_load, c_load)
        if tr is None:
            print(f"{label:<10}  transistor failed")
            continue
        nat = native(case / "native", r_load, c_load)
        pyc = pybis(case / "pybis_ccomp", r_load, c_load, C_COMP_PF)
        pyn = pybis(case / "pybis_noccomp", r_load, c_load, 0.0)
        r_nat, s_nat = score(nat, tr, window) if nat else (np.nan, np.nan)
        r_pyc, s_pyc = score(pyc, tr, window) if pyc else (np.nan, np.nan)
        r_pyn, s_pyn = score(pyn, tr, window) if pyn else (np.nan, np.nan)
        print(f"{label:<10}{r_nat:12.2f}{r_pyc:11.2f}{r_pyn:13.2f}"
              f"  | {s_nat:10.1f}{s_pyc:10.1f}{s_pyn:10.1f}")
        rows.append({"load": label, "r_load": r_load, "c_load_pf": c_load,
                     "native_rmse_mv": round(r_nat, 3), "pybis_ccomp_rmse_mv": round(r_pyc, 3),
                     "pybis_noccomp_rmse_mv": round(r_pyn, 3),
                     "native_shift_ps": round(s_nat, 2), "pybis_ccomp_shift_ps": round(s_pyc, 2),
                     "pybis_noccomp_shift_ps": round(s_pyn, 2)})

    if not rows:
        print("nothing ran")
        return 1
    import csv
    with (out / "ccomp_validation.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    labels = [r["load"] for r in rows]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(11.5, 6.0))
    ax.bar(x - 0.25, [r["native_rmse_mv"] for r in rows], 0.25, label="native IBIS", color="#2B6CA3")
    ax.bar(x, [r["pybis_ccomp_rmse_mv"] for r in rows], 0.25, label="pybis (C_comp)", color="#C02626")
    ax.bar(x + 0.25, [r["pybis_noccomp_rmse_mv"] for r in rows], 0.25,
           label="pybis (C_comp=0)", color="#1B6B4F")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("pad RMSE vs transistor (mV)", fontsize=12)
    ax.set_title("pybis C_comp against the transistor, across loads",
                 fontsize=15, fontweight="bold", pad=11)
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out / "ccomp_validation.png", dpi=175)
    plt.close(fig)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
