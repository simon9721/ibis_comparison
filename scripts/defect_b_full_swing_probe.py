#!/usr/bin/env python3
"""Defect B: is the io_buf falling-edge lateness stress-specific, or always there?

Defect B is the gate-state model's falling 50% crossing running 69-99 ps late
against the HSPICE transistor on io_buf's five stress targets (truncated pulses at
90/80/70/60/50% width), where native IBIS on the same cases is 5-26 ps *early*.
Nothing has been tried on it.

The golden-waveform test narrowed it but could not settle it: that test runs the
plain InputDriven build on full swing against the model's own V-T tables, and
showed the shared I-V + Ku(t) + C_comp reconstruction replays a full-swing edge to
within 8 ps. So the error is not in that layer. It leaves three candidates -- the
gate-state command layer, the stress condition itself, or the bench.

This splits them with one measurement. Run io_buf **full swing** -- no truncation,
no reversal -- and measure the falling 50% crossing of each build against the
transistor:

  * If the gate-state build is ~70-100 ps late here too, defect B is **not**
    stress-specific. It is the command layer's fitted delays, which for io_buf are
    nanosecond-scale (pd_on 1.83 ns, pd_off 0.85 ns) -- a few percent of error in
    the falling-edge fit is ~90 ps, exactly defect B's size.
  * If it is ~0 here, defect B is genuinely a stress-condition effect, and the
    command layer only misbehaves once a pulse is truncated.

Plain InputDriven and native IBIS are run alongside as controls, so the
command layer's contribution is isolated from the reconstruction's.

    py -3.14 scripts/defect_b_full_swing_probe.py
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402

IBIS = ROOT / "results" / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
NETLIST = ROOT / "buffers" / "models" / "io_buf.sp"
MODCARD = ROOT / "buffers" / "models" / "hspice.mod"
OUT = ROOT / "results" / "defect_b_full_swing_2026-09-03"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY_V, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
RISE_NS, FALL_NS, STOP_NS = 5.0, 15.0, 22.0   # full swing: 10 ns high, fully settled


def _pwl() -> str:
    return sl.pulse(0.0, SUPPLY_V, [RISE_NS, FALL_NS], stop_ns=STOP_NS)


def transistor(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(NETLIST, d / "io_buf.sp")
    shutil.copy2(MODCARD, d / "hspice.mod")
    (d / "run.sp").write_text(f"""* io_buf transistor, full swing
.title io_buf transistor
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {_pwl()}
.include 'hspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF
Vdd_src vdd_src 0 DC {SUPPLY_V}
Rvdd vdd_src vdd 1
Cdec vdd 0 10p
Voe oe 0 DC {SUPPLY_V}
XDUT in_dig oe pad in_sense vdd 0 SPICE_BUF
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


def native(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(IBIS, d / "input.ibs")
    (d / "run.sp").write_text(f"""* io_buf native IBIS, full swing
.title io_buf native ibis
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {_pwl()}
Ven en_sig 0 DC {SUPPLY_V}
VPU pu_ref 0 DC {SUPPLY_V}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUPPLY_V}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig en_sig dig_q pc_ref gc_ref
+ file='input.ibs' model='{MODEL}' typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2
Rdig dig_q 0 1k
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


def pybis(d: Path, subckt_type: str):
    d.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    try:
        subcircuit.generate_spice_model("Output", subckt_type, data, "Typical",
                                        str(d / "driver.sub"))
    except Exception as exc:                       # noqa: BLE001
        print(f"   {subckt_type}: generation failed -- {exc}")
        return None
    if not (d / "driver.sub").exists():
        return None
    text = (d / "driver.sub").read_text(errors="ignore")
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    nd = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
    nodes = [nd.get(p.upper(), p) for p in pins]
    en = 0.0 if re.search(r"NENABLE\s+0\s+V\s*=\s*\(\s*V\(EN[^)]*\)\s*<", text) else SUPPLY_V
    (d / "run.sp").write_text(f"""* io_buf pybis {subckt_type}, full swing
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC {SUPPLY_V}
Vin IN 0 {_pwl()}
Ven EN 0 DC {en:g}
X1 {' '.join(nodes)} {m.group(1)}
Rload OUT 0 {R_LOAD}
Cload OUT 0 {C_LOAD_PF}p
.tran 0.0005n {STOP_NS}n
.save V(OUT)
.end
""", encoding="utf-8")
    raw = sl.ngspice(d, timeout_s=900)
    if raw is None:
        return None
    r = sl.parse_ngspice_raw(raw)
    return sl.time_ns(r), sl.trace(r, "out")


def cross(t, y, level, rising, after):
    for i in range(1, len(y)):
        if t[i] < after:
            continue
        if (rising and y[i - 1] < level <= y[i]) or (not rising and y[i - 1] > level >= y[i]):
            return float(t[i - 1] + (level - y[i - 1]) * (t[i] - t[i - 1]) / (y[i] - y[i - 1]))
    return float("nan")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {
        "transistor": transistor(OUT / "transistor"),
        "native IBIS": native(OUT / "native"),
        "pybis InputDriven": pybis(OUT / "pybis_plain", "InputDriven"),
        "pybis gate-state": pybis(OUT / "pybis_gate_state", "InputDrivenGateStateHybrid"),
    }
    tr = runs["transistor"]
    if tr is None:
        print("transistor run failed -- cannot measure")
        return 1
    half = 0.5 * (np.nanmax(tr[1]) + np.nanmin(tr[1]))
    tx_r = cross(tr[0], tr[1], half, True, RISE_NS - 0.5)
    tx_f = cross(tr[0], tr[1], half, False, FALL_NS - 0.5)
    print(f"\ntransistor 50%: rise {tx_r:.4f} ns, fall {tx_f:.4f} ns  (level {half:.3f} V)\n")
    print(f"{'build':<20}{'rise vs tx ps':>15}{'fall vs tx ps':>15}")
    for name, got in runs.items():
        if got is None or name == "transistor":
            if got is None:
                print(f"{name:<20}   run failed")
            continue
        r = (cross(got[0], got[1], half, True, RISE_NS - 0.5) - tx_r) * 1e3
        f = (cross(got[0], got[1], half, False, FALL_NS - 0.5) - tx_f) * 1e3
        print(f"{name:<20}{r:15.1f}{f:15.1f}")

    fig, ax = plt.subplots(2, 1, figsize=(12, 7.5))
    for axis, (lo, hi), ttl in ((ax[0], (RISE_NS - 0.2, RISE_NS + 2.0), "rising"),
                                (ax[1], (FALL_NS - 0.2, FALL_NS + 2.0), "falling")):
        for name, got in runs.items():
            if got is None:
                continue
            style = dict(color="#111111", lw=3.0) if name == "transistor" else {}
            axis.plot(got[0], got[1], label=name, ls="-" if name == "transistor" else (0, (5, 2.2)),
                      **style)
        axis.set_xlim(lo, hi)
        axis.set_title(f"io_buf full swing | {ttl} edge", fontsize=12, fontweight="bold")
        axis.set_ylabel("Pad (V)")
        axis.grid(alpha=0.3)
    ax[0].legend(fontsize=10)
    ax[1].set_xlabel("Time (ns)")
    fig.tight_layout()
    fig.savefig(OUT / "defect_b_full_swing.png", dpi=165)
    plt.close(fig)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
