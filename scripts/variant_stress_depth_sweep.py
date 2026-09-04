#!/usr/bin/env python3
"""Does the timing offset stay flat with stress depth on the variants?

The variant sweep measured the offset at full swing only, and concluded that
75-95% of it is inherited from native IBIS while pybis's own term is a small,
stable 3-11 ps. Carrying that to stressed pulses rests on the depth
decomposition, which showed 77-103% of the offset is already present at near-full
swing -- but that was measured on the three base buffers and merely *assumed* for
the variants.

This tests the assumption directly.

**No bisection.** Bisection exists to hit a specific depth (43%, 86%) so that
devices can be compared at matched stress. The question here is narrower -- is the
offset flat in depth? -- and that needs several *different* depths per variant,
not particular ones. So the pulse width is swept and the resulting depth is
measured rather than targeted, which costs one run per point instead of a search.

For each variant and width: transistor, native IBIS and pybis, all into the same
load. Timing is taken at **50% of each trace's own excursion**, not at 50% of the
transistor's. That matters here: under stress the models can reach a very
different peak than the transistor -- pybis takes inv_chain to 1.43 V where the
transistor only reaches 0.81 -- so a level fixed to the transistor's excursion is
crossed early simply because the model is heading somewhere higher. Scoring each
trace against its own excursion separates the timing question from the amplitude
question, which is measured alongside it. At full swing the two conventions
coincide, which is why this only surfaced on the stressed sweep.

    py -3.14 scripts/variant_stress_depth_sweep.py
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

import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402

OUT = ROOT / "results" / "variant_stress_depth_2026-09-03"
R_LOAD, C_LOAD_PF = 50.0, 2.0
RISE_NS, STOP_NS = 5.0, 22.0

INV = ROOT / "results" / "inv_chain_variants_2026-09-02"
EX2 = ROOT / "results" / "ex2_variants_2026-09-03"

# Widths chosen to straddle the partial-excursion regime for each family: the
# stress matrix used 104-135 ps for inv_chain and 810-975 ps for ex2, widened
# here because the variants are deliberately faster or slower than their base.
VARIANTS = [
    ("inv_base8",  "inv_chain", 1.8, INV/"base8/selection/tr1ps/invchain_base8_tr1ps.ibs",
     INV/"base8/inputs",  "driver2", "invchain",     [0.104, 0.118, 0.135, 0.170]),
    ("inv_stage4", "inv_chain", 1.8, INV/"stage4/selection/tr1ps/invchain_stage4_tr1ps.ibs",
     INV/"stage4/inputs", "driver2", "invchain",     [0.104, 0.118, 0.135, 0.170]),
    ("inv_skewp",  "inv_chain", 1.8, INV/"skewp/selection/tr1ps/invchain_skewp_tr1ps.ibs",
     INV/"skewp/inputs",  "driver2", "invchain",     [0.115, 0.132, 0.150, 0.190]),
    ("inv_weak",   "inv_chain", 1.8, INV/"weak/selection/tr1ps/invchain_weak_tr1ps.ibs",
     INV/"weak/inputs",   "driver2", "invchain",     [0.120, 0.140, 0.160, 0.200]),
    ("ex2_base",     "ex2", 3.3, EX2/"base/selection/tr1ps/ex2_base_tr1ps.ibs",
     EX2/"base/inputs",     "driver", "MCM Driver 1", [0.70, 0.82, 0.90, 1.05]),
    ("ex2_slowpre",  "ex2", 3.3, EX2/"slowpre/selection/tr1ps/ex2_slowpre_tr1ps.ibs",
     EX2/"slowpre/inputs",  "driver", "MCM Driver 1", [0.95, 1.15, 1.35, 1.65]),
    ("ex2_skewp",    "ex2", 3.3, EX2/"skewp/selection/tr1ps/ex2_skewp_tr1ps.ibs",
     EX2/"skewp/inputs",    "driver", "MCM Driver 1", [0.75, 0.90, 1.05, 1.25]),
    ("ex2_weak",     "ex2", 3.3, EX2/"weak/selection/tr1ps/ex2_weak_tr1ps.ibs",
     EX2/"weak/inputs",     "driver", "MCM Driver 1", [0.80, 0.95, 1.10, 1.30]),
    ("ex2_nomiller", "ex2", 3.3, EX2/"nomiller/selection/tr1ps/ex2_nomiller_tr1ps.ibs",
     EX2/"nomiller/inputs", "driver", "MCM Driver 1", [0.70, 0.82, 0.90, 1.05]),
]


def short_high_pwl(sup: float, width_ns: float) -> str:
    """A single short pulse: rest low, rise at RISE_NS, fall width_ns later."""
    return sl.pulse(0.0, sup, [RISE_NS, RISE_NS + width_ns], stop_ns=STOP_NS)


def _cached_hspice(d: Path, deck: str):
    """Run `deck` in `d`, reusing the existing .tr0 when the deck is unchanged.

    Same contract as the transistor cache: the result is a function of the deck
    text alone, so re-running the sweep to fix one build must not re-simulate the
    others."""
    sp, tr0 = d / "run.sp", d / "run.tr0"
    if tr0.exists() and sp.exists() and sp.read_text(encoding="utf-8") == deck:
        return tr0
    sp.write_text(deck, encoding="utf-8")
    return sl.hspice(d, timeout_s=900)


def transistor_deck(family: str, inputs: Path, sup: float, width: float,
                    d: Path) -> str:
    """Deck text for the transistor run, and the inputs copied in beside it.

    Split out from transistor() so the fixture-loaded variants used for the
    silicon Ku/Kd solve can reuse exactly this netlist and stimulus, changing only
    the load. Any drift between the two would put the coefficients and the pad
    voltage on different circuits.
    """
    d.mkdir(parents=True, exist_ok=True)
    for n in os.listdir(inputs):
        shutil.copy2(inputs / n, d / n)
    if family == "inv_chain":
        sub = next(p.name for p in inputs.glob("*_subckt_typ.sp"))
        body = (".OPTIONS METHOD=GEAR GSHUNT=1E-12\n"
                ".PARAM vccr_typ=1.300V\n.PARAM vccq_typ=1.800V\n"
                ".PARAM vssq=0.000V\n.PARAM vss=0.000V\n"
                f".include '{sub}'\nVdd vccq 0 DC {sup}\n"
                "XDUT in_dig pad vccq 0 invchain")
    else:
        body = (".include 'hspice.mod'\n.subckt EX2B in out vdd gnd\n"
                ".include 'buffer.sp'\n.ends EX2B\n"
                f"Vdd vdd 0 DC {sup}\nXDUT in_dig pad vdd 0 EX2B")
    deck = f"""* variant stressed transistor
.title stressed transistor
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {short_high_pwl(sup, width)}
{body}
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad)
.tran 0.002n {STOP_NS}n
.end
"""
    return deck


def transistor(d: Path, family: str, inputs: Path, sup: float, width: float):
    # The transistor result depends only on the netlist, the pulse width and the
    # load -- never on which pybis build is being compared against it. So an
    # existing run with a byte-identical deck is reused. Restarting this sweep to
    # change the model build should not re-simulate the silicon.
    deck = transistor_deck(family, inputs, sup, width, d)
    tr0 = _cached_hspice(d, deck)
    if tr0 is None:
        return None
    r = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(r), sl.signal(r, "v(pad)")


def native(d: Path, ibis: Path, model: str, sup: float, width: float, mode: int = 2):
    """Native IBIS. `mode` is HSPICE's ramp_rwf/ramp_fwf: 2 = use two waveform
    tables (the documented default, the two-fixture solve IBIS intends), 1 = use
    only the first table.

    Both are run because they disagree badly on ex2: the default silently produces
    a dead pad (0.03 V on a pulse the transistor takes to 1.47 V) while mode 1
    tracks the transistor. Reporting only one of them would either slander native
    or hide a real failure of its two-fixture solve."""
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ibis, d / "input.ibs")
    rwf = fwf = mode
    deck = (f"""* variant stressed native
.title stressed native rwf{mode}
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {short_high_pwl(sup, width)}
VPU pu_ref 0 DC {sup}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {sup}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='input.ibs' model='{model}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf={rwf} ramp_fwf={fwf}
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad)
.tran 0.002n {STOP_NS}n
.end
""")
    tr0 = _cached_hspice(d, deck)
    if tr0 is None:
        return None
    r = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(r), sl.signal(r, "v(pad)")


def pybis_run(d: Path, ibis: Path, model: str, comp: str, sup: float, width: float,
              subckt_type: str):
    d.mkdir(parents=True, exist_ok=True)
    try:
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)),
                            model_name=model, component_name=comp)
        subcircuit.generate_spice_model("Output", subckt_type, data, "Typical",
                                        str(d / "driver.sub"))
    except Exception:                              # noqa: BLE001
        return None
    text = (d / "driver.sub").read_text(errors="ignore")
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    nd = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
    nodes = [nd.get(p.upper(), p) for p in pins]
    en = 0.0 if re.search(r"NENABLE\s+0\s+V\s*=\s*\(\s*V\(EN[^)]*\)\s*<", text) else sup
    deck = f"""* variant stressed pybis
.options reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC {sup}
Vin IN 0 {short_high_pwl(sup, width)}
Ven EN 0 DC {en:g}
X1 {' '.join(nodes)} {m.group(1)}
Rload OUT 0 {R_LOAD}
Cload OUT 0 {C_LOAD_PF}p
.tran 0.002n {STOP_NS}n
.save V(OUT)
.end
"""
    # Subcircuit generation is cheap; the ngspice solve is not. Reuse an existing
    # result whenever the deck is byte-identical, so fixing the native build does
    # not re-simulate every pybis case.
    sp, prev = d / "run.sp", d / "run.raw"
    if prev.exists() and sp.exists() and sp.read_text(encoding="utf-8") == deck:
        raw = prev
    else:
        sp.write_text(deck, encoding="utf-8")
        raw = sl.ngspice(d, timeout_s=900)
    if raw is None:
        return None
    r = sl.parse_ngspice_raw(raw)
    return sl.time_ns(r), sl.trace(r, "out")


def cross(t, v, level, after):
    for i in range(1, len(v)):
        if t[i] < after:
            continue
        if v[i - 1] < level <= v[i]:
            return float(t[i - 1] + (level - v[i - 1]) * (t[i] - t[i - 1]) / (v[i] - v[i - 1]))
    return float("nan")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    out_csv = OUT / "variant_stress_depth.csv"
    rows = []
    print(f"{"variant":<14}{"width":>8}{"tx exc":>9}{"nat2":>8}{"nat1":>9}"
          f"{"gate exc":>9}{"dcmd exc":>9}"
          f"{'nat2-tx':>8}{'nat1-tx':>10}{'gate-tx':>10}{'dcmd-tx':>10}", flush=True)
    for key, fam, sup, ibis, inputs, model, comp, widths in VARIANTS:
        if not ibis.exists():
            print(f"{key:<14}  model missing", flush=True)
            continue
        full = None
        for w in widths:
            d = OUT / key / f"w{int(round(w*1000))}ps"
            tr = transistor(d / "transistor", fam, inputs, sup, w)
            if tr is None:
                print(f"{key:<14}{w*1000:>7.0f}p  transistor failed", flush=True)
                continue
            t, si = tr
            base = float(np.median(si[t < RISE_NS - 0.5]))
            exc = float(si.max() - base)
            full = exc if full is None else max(full, exc)
            if exc < 0.02:
                print(f"{key:<14}{w*1000:>7.0f}p{exc:>9.3f}   no excursion -- skipped",
                      flush=True)
                continue
            txc = cross(t, si, base + 0.5 * exc, RISE_NS - 0.5)
            res, peak = {}, {}
            builds = (
                ("native", native(d / "native", ibis, model, sup, w, 2)),
                ("native1", native(d / "native_rwf1", ibis, model, sup, w, 1)),
                # The study's own naming calls plain "InputDriven" the *legacy*
                # build. It has no command layer, which is the machinery that
                # exists to handle a truncated pulse, so it is the wrong thing to
                # measure under stress. These are the two the stress matrix uses.
                ("gate_state", pybis_run(d / "gate_state", ibis, model, comp, sup, w,
                                         "InputDrivenTwoStateGateDirectionalDualResidualFull")),
                ("delay_cmd", pybis_run(d / "delay_cmd", ibis, model, comp, sup, w,
                                        "InputDrivenTwoStateGateDelayCommandFull")),
            )
            for nm, got in builds:
                if got is None:
                    res[nm] = peak[nm] = np.nan
                    continue
                gt, gv = got
                gb = float(np.median(gv[gt < RISE_NS - 0.5]))
                ge = float(gv.max() - gb)
                peak[nm] = ge
                # Each trace is scored against its OWN 50% level, not the
                # transistor's. Under stress the models can reach a very different
                # peak -- pybis takes inv_chain to 1.43 V where the transistor only
                # reaches 0.81 -- so a level fixed to the transistor's excursion is
                # crossed early merely because the model is heading higher, which
                # reports an amplitude error as a timing one. At full swing the two
                # conventions coincide, which is why this only bit on the stressed
                # sweep.
                res[nm] = (cross(gt, gv, gb + 0.5 * ge, RISE_NS - 0.5) - txc) * 1e3
            print(f"{key:<14}{w*1000:>7.0f}p{exc:>9.3f}"
                  f"{peak['native']:>8.3f}{peak['native1']:>9.3f}"
                  f"{peak['gate_state']:>9.3f}{peak['delay_cmd']:>9.3f}"
                  f"{res['native']:>8.1f}p{res['native1']:>9.1f}p"
                  f"{res['gate_state']:>9.1f}p{res['delay_cmd']:>9.1f}p",
                  flush=True)
            rows.append({"variant": key, "width_ps": round(w * 1000, 1),
                         "tx_excursion_v": round(exc, 4),
                         "native_excursion_v": round(peak["native"], 4),
                         "native_rwf1_excursion_v": round(peak["native1"], 4),
                         "gate_state_excursion_v": round(peak["gate_state"], 4),
                         "delay_cmd_excursion_v": round(peak["delay_cmd"], 4),
                         "native_vs_tx_ps": round(res["native"], 2),
                         "native_rwf1_vs_tx_ps": round(res["native1"], 2),
                         "gate_state_vs_tx_ps": round(res["gate_state"], 2),
                         "delay_cmd_vs_tx_ps": round(res["delay_cmd"], 2)})
            with out_csv.open("w", newline="", encoding="utf-8") as h:
                w2 = csv.DictWriter(h, fieldnames=list(rows[0]))
                w2.writeheader()
                w2.writerows(rows)
    print(f"\nwrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
