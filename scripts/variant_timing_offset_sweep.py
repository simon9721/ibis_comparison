#!/usr/bin/env python3
"""What device property sets the sign and size of pybis's timing offset?

The offset is a per-device, per-direction constant: -56 to +72 ps across three
buffers, flipping sign both between devices and between directions on the same
device. Three devices give six data points, which is enough to see that it is
device-dependent and not enough to say what it depends on.

The variants built for items 1 and 2 each change **one known property**, so they
turn the question into a controlled experiment:

    inv_chain  base8     reference
               stage4    predriver depth halved, output stage identical
               skewp     output PMOS halved -> deliberate rise/fall asymmetry
               weak      both output devices halved
    ex2        base      reference
               slowpre   predriver halved
               skewp     output PMOS halved
               weak      both output devices halved
               nomiller  n4->out coupling removed

Crucially this runs at **full swing**, not on stressed cases. The timing
decomposition showed 77-103% of the offset is already present at near-full swing
on five of six device/direction combinations, so stress is not needed to see it --
and full swing costs one simulation per build instead of a bisection search for
each depth target.

    py -3.14 scripts/variant_timing_offset_sweep.py
"""
from __future__ import annotations

import csv
import os
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

OUT = ROOT / "results" / "variant_timing_offset_2026-09-03"
R_LOAD, C_LOAD_PF = 50.0, 2.0
RISE_NS, FALL_NS, STOP_NS = 5.0, 15.0, 22.0

INV = ROOT / "results" / "inv_chain_variants_2026-09-02"
EX2 = ROOT / "results" / "ex2_variants_2026-09-03"

# key, family, supply, ibis, inputs dir, model, component, what changed
VARIANTS = [
    ("inv base8",  "inv_chain", 1.8, INV/"base8/selection/tr1ps/invchain_base8_tr1ps.ibs",
     INV/"base8/inputs",  "driver2", "invchain", "reference"),
    ("inv stage4", "inv_chain", 1.8, INV/"stage4/selection/tr1ps/invchain_stage4_tr1ps.ibs",
     INV/"stage4/inputs", "driver2", "invchain", "predriver depth halved"),
    ("inv skewp",  "inv_chain", 1.8, INV/"skewp/selection/tr1ps/invchain_skewp_tr1ps.ibs",
     INV/"skewp/inputs",  "driver2", "invchain", "output PMOS halved"),
    ("inv weak",   "inv_chain", 1.8, INV/"weak/selection/tr1ps/invchain_weak_tr1ps.ibs",
     INV/"weak/inputs",   "driver2", "invchain", "both output devices halved"),
    ("ex2 base",     "ex2", 3.3, EX2/"base/selection/tr1ps/ex2_base_tr1ps.ibs",
     EX2/"base/inputs",     "driver", "MCM Driver 1", "reference"),
    ("ex2 slowpre",  "ex2", 3.3, EX2/"slowpre/selection/tr1ps/ex2_slowpre_tr1ps.ibs",
     EX2/"slowpre/inputs",  "driver", "MCM Driver 1", "predriver halved"),
    ("ex2 skewp",    "ex2", 3.3, EX2/"skewp/selection/tr1ps/ex2_skewp_tr1ps.ibs",
     EX2/"skewp/inputs",    "driver", "MCM Driver 1", "output PMOS halved"),
    ("ex2 weak",     "ex2", 3.3, EX2/"weak/selection/tr1ps/ex2_weak_tr1ps.ibs",
     EX2/"weak/inputs",     "driver", "MCM Driver 1", "both output devices halved"),
    ("ex2 nomiller", "ex2", 3.3, EX2/"nomiller/selection/tr1ps/ex2_nomiller_tr1ps.ibs",
     EX2/"nomiller/inputs", "driver", "MCM Driver 1", "n4->out coupling removed"),
]


def pwl(sup):
    return sl.pulse(0.0, sup, [RISE_NS, FALL_NS], stop_ns=STOP_NS)


def transistor(d: Path, family: str, inputs: Path, sup: float):
    d.mkdir(parents=True, exist_ok=True)
    for n in os.listdir(inputs):
        shutil.copy2(inputs / n, d / n)
    if family == "inv_chain":
        sub = next(p.name for p in inputs.glob("*_subckt_typ.sp"))
        body = (f".OPTIONS METHOD=GEAR GSHUNT=1E-12\n"
                f".PARAM vccr_typ=1.300V\n.PARAM vccq_typ=1.800V\n"
                f".PARAM vssq=0.000V\n.PARAM vss=0.000V\n"
                f".include '{sub}'\nVdd vccq 0 DC {sup}\n"
                f"XDUT in_dig pad vccq 0 invchain")
    else:
        body = (".include 'hspice.mod'\n.subckt EX2B in out vdd gnd\n"
                ".include 'buffer.sp'\n.ends EX2B\n"
                f"Vdd vdd 0 DC {sup}\nXDUT in_dig pad vdd 0 EX2B")
    (d / "run.sp").write_text(f"""* variant transistor
.title variant transistor
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {pwl(sup)}
{body}
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad)
.tran 0.002n {STOP_NS}n
.end
""", encoding="utf-8")
    tr0 = sl.hspice(d, timeout_s=900)
    if tr0 is None:
        return None
    r = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(r), sl.signal(r, "v(pad)")


def native(d: Path, ibis: Path, model: str, sup: float):
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ibis, d / "input.ibs")
    (d / "run.sp").write_text(f"""* variant native IBIS
.title variant native
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {pwl(sup)}
VPU pu_ref 0 DC {sup}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {sup}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='input.ibs' model='{model}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad)
.tran 0.002n {STOP_NS}n
.end
""", encoding="utf-8")
    tr0 = sl.hspice(d, timeout_s=900)
    if tr0 is None:
        return None
    r = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(r), sl.signal(r, "v(pad)")


def pybis(d: Path, ibis: Path, model: str, component: str, sup: float):
    d.mkdir(parents=True, exist_ok=True)
    try:
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)),
                            model_name=model, component_name=component)
        subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical",
                                        str(d / "driver.sub"))
    except Exception as exc:                       # noqa: BLE001
        print(f"    pybis generation failed: {exc}")
        return None
    text = (d / "driver.sub").read_text(errors="ignore")
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    nd = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
    nodes = [nd.get(p.upper(), p) for p in pins]
    en = 0.0 if re.search(r"NENABLE\s+0\s+V\s*=\s*\(\s*V\(EN[^)]*\)\s*<", text) else sup
    (d / "run.sp").write_text(f"""* variant pybis
.options reltol=1e-4 abstol=1e-10 vntol=1e-7
.include driver.sub
Vdd VCC 0 DC {sup}
Vin IN 0 {pwl(sup)}
Ven EN 0 DC {en:g}
X1 {' '.join(nodes)} {m.group(1)}
Rload OUT 0 {R_LOAD}
Cload OUT 0 {C_LOAD_PF}p
.tran 0.001n {STOP_NS}n
.save V(OUT)
.end
""", encoding="utf-8")
    raw = sl.ngspice(d, timeout_s=900)
    if raw is None:
        return None
    r = sl.parse_ngspice_raw(raw)
    return sl.time_ns(r), sl.trace(r, "out")


def cross(t, v, level, rising, after):
    for i in range(1, len(v)):
        if t[i] < after:
            continue
        if (rising and v[i - 1] < level <= v[i]) or (not rising and v[i - 1] > level >= v[i]):
            return float(t[i - 1] + (level - v[i - 1]) * (t[i] - t[i - 1]) / (v[i] - v[i - 1]))
    return float("nan")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{'variant':<14}{'what changed':<30}"
          f"{'pyb rise':>10}{'pyb fall':>10}{'nat rise':>10}{'nat fall':>10}")
    rows = []
    for key, fam, sup, ibis, inputs, model, comp, changed in VARIANTS:
        if not ibis.exists():
            print(f"{key:<14}{changed:<30}  model missing")
            continue
        d = OUT / key.replace(" ", "_")
        tr = transistor(d / "transistor", fam, inputs, sup)
        if tr is None:
            print(f"{key:<14}{changed:<30}  transistor failed")
            continue
        half = 0.5 * (np.nanmax(tr[1]) + np.nanmin(tr[1]))
        txr = cross(tr[0], tr[1], half, True, RISE_NS - 0.5)
        txf = cross(tr[0], tr[1], half, False, FALL_NS - 0.5)
        out = {}
        for name, got in (("native", native(d / "native", ibis, model, sup)),
                          ("pybis", pybis(d / "pybis", ibis, model, comp, sup))):
            if got is None:
                out[name] = (np.nan, np.nan)
                continue
            out[name] = ((cross(got[0], got[1], half, True, RISE_NS - 0.5) - txr) * 1e3,
                         (cross(got[0], got[1], half, False, FALL_NS - 0.5) - txf) * 1e3)
        pr, pf = out["pybis"]
        nr, nf = out["native"]
        print(f"{key:<14}{changed:<30}{pr:>9.1f}p{pf:>9.1f}p{nr:>9.1f}p{nf:>9.1f}p")
        rows.append({"variant": key, "changed": changed,
                     "pybis_rise_ps": round(pr, 2), "pybis_fall_ps": round(pf, 2),
                     "native_rise_ps": round(nr, 2), "native_fall_ps": round(nf, 2)})

    if rows:
        with (OUT / "variant_timing_offset.csv").open("w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        labels = [r["variant"] for r in rows]
        x = np.arange(len(labels))
        fig, ax = plt.subplots(figsize=(12.5, 6.0))
        ax.bar(x - 0.2, [r["pybis_rise_ps"] for r in rows], 0.4, label="pybis rise", color="#C02626")
        ax.bar(x + 0.2, [r["pybis_fall_ps"] for r in rows], 0.4, label="pybis fall", color="#E08A8A")
        ax.plot(x, [r["native_rise_ps"] for r in rows], "o--", color="#2B6CA3", label="native rise")
        ax.plot(x, [r["native_fall_ps"] for r in rows], "s--", color="#7FB3D5", label="native fall")
        ax.axhline(0, color="#111", lw=1.5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right")
        ax.set_ylabel("offset vs transistor (ps)", fontsize=11)
        ax.set_title("Timing offset at full swing across buffer variants", fontsize=13,
                     fontweight="bold")
        ax.grid(alpha=0.3, axis="y")
        ax.legend(fontsize=10)
        fig.tight_layout()
        fig.savefig(OUT / "variant_timing_offset.png", dpi=170)
        plt.close(fig)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
