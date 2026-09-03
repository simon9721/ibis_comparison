#!/usr/bin/env python3
"""Where does the pybis lag come from -- edge detection, or the output stage?

Across five silicons pybis (ngspice on the InputDriven subcircuit) runs 7-9 ps
later than native IBIS (HSPICE reading the same .ibs) and sits at ~3x its pad
RMSE against the transistor. Both read the identical IBIS file, so the difference
is how each turns the tables into a waveform:

    native IBIS   HSPICE's B-element replays the recorded V-T behaviour
    pybis         replays the recorded Ku(t)/Kd(t), indexed by elapsed time
                  since an edge it detects with a 1.4 V comparator and a 10 ps
                  transport line

This forks the lag into two candidates:

    command layer   pybis's Ku edge is itself late -> the edge detector /
                    comparator / transport delay is the cause
    output stage    pybis's Ku aligns with native's, but the pad still lags ->
                    the I-V drive or C_comp handling is the cause

Both native IBIS and pybis expose Ku/Kd (native via xv_pu=ku, pybis as an
internal node), so this probes Ku on both sides and compares its 50% crossing to
the pad's. Whichever layer already carries the 7-9 ps is the culprit.

    py -3.14 scripts/localize_pybis_lag.py
"""
from __future__ import annotations

import argparse
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

import spicelab as sl  # the item-5 module  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402

BASE = ROOT / "results" / "inv_chain_variants_2026-09-02" / "base8"
IBIS = BASE / "selection" / "tr1ps" / "invchain_base8_tr1ps.ibs"
OUT = ROOT / "results" / "pybis_lag_localization_2026-09-03"

MODEL, COMPONENT = "driver2", "invchain"
SUPPLY_V, R_LOAD, C_LOAD_PF = 1.8, 50.0, 2.0
RISE_NS, FALL_NS, STOP_NS = 5.0, 15.0, 22.0


def _pwl() -> str:
    return sl.pulse(0.0, SUPPLY_V, [RISE_NS, FALL_NS], stop_ns=STOP_NS)


def native(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(IBIS, out_dir / IBIS.name)
    deck = f"""* base8 native IBIS with Ku/Kd probed
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
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad) V(ku) V(kd)
.tran 0.001n {STOP_NS}n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    tr0 = sl.hspice(out_dir)
    if tr0 is None:
        return None
    raw = sl.parse_hspice_tr0(tr0)
    return {"t": sl.time_ns(raw), "pad": sl.signal(raw, "v(pad)"),
            "ku": sl.signal(raw, "v(ku)"), "kd": sl.signal(raw, "v(kd)")}


def pybis(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical",
                                    str(out_dir / "driver.sub"))
    import re
    text = (out_dir / "driver.sub").read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    name = m.group(1)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    node = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0", "GND": "0"}
    nodes = [node.get(p.upper(), p) for p in pins]
    deck = f"""* base8 pybis with Ku/Kd probed
.include driver.sub
Vdd VCC 0 DC {SUPPLY_V}
Vin IN 0 {_pwl()}
Ven EN 0 DC {SUPPLY_V}
X1 {' '.join(nodes)} {name}
Rload OUT 0 {R_LOAD}
Cload OUT 0 {C_LOAD_PF}p
.tran 0.001n {STOP_NS}n
.save V(OUT) V(X1.Ku) V(X1.Kd) V(X1.NINX) V(X1.N6)
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    raw_path = sl.ngspice(out_dir)
    if raw_path is None:
        return None
    raw = sl.parse_ngspice_raw(raw_path)
    got = {"t": sl.time_ns(raw), "pad": sl.trace(raw, "out")}
    for label, needle in (("ku", "ku"), ("kd", "kd"), ("ninx", "ninx"), ("n6", "n6")):
        try:
            got[label] = sl.trace(raw, needle)
        except KeyError:
            pass
    return got


def cross(t, y, level, rising, after):
    for i in range(1, len(y)):
        if t[i] < after:
            continue
        if (rising and y[i - 1] < level <= y[i]) or (not rising and y[i - 1] > level >= y[i]):
            return float(t[i - 1] + (level - y[i - 1]) * (t[i] - t[i - 1]) / (y[i] - y[i - 1]))
    return float("nan")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = (args.out if args.out.is_absolute() else ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    nat = native(out / "native")
    pyb = pybis(out / "pybis")
    if nat is None or pyb is None:
        print(f"run failed: native={nat is not None} pybis={pyb is not None}")
        return 1

    print("50% crossings on the rising edge (input steps at 5.000 ns)\n")
    print(f"{'signal':<10}{'native ns':>12}{'pybis ns':>12}{'pybis-native ps':>17}")
    rows = []
    for sig, rising in (("ku", True), ("pad", True)):
        if sig not in nat or sig not in pyb:
            continue
        level = 0.5 if sig == "ku" else 0.5 * SUPPLY_V
        cn = cross(nat["t"], nat[sig], level, rising, RISE_NS - 0.3)
        cp = cross(pyb["t"], pyb[sig], level, rising, RISE_NS - 0.3)
        print(f"{sig:<10}{cn:12.4f}{cp:12.4f}{(cp - cn) * 1e3:17.1f}")
        rows.append((sig, cn, cp))

    # When does pybis first believe an edge happened?
    if "ninx" in pyb:
        edge = cross(pyb["t"], pyb["ninx"], 0.5, True, RISE_NS - 0.3)
        print(f"\npybis NINX (input comparator fires) at {edge:.4f} ns "
              f"({(edge - RISE_NS) * 1e3:+.1f} ps vs the 5.000 ns input step)")

    fig, axes = plt.subplots(2, 1, figsize=(12.0, 8.0), sharex=True)
    axes[0].plot(nat["t"], nat["ku"], color="#2B6CA3", lw=2.4, label="native IBIS Ku")
    if "ku" in pyb:
        axes[0].plot(pyb["t"], pyb["ku"], color="#C02626", lw=2.0, ls=(0, (5, 2.2)),
                     label="pybis Ku")
    axes[0].set_ylabel("Ku", fontsize=12)
    axes[0].set_title("base8  |  where the pybis lag enters  |  rising edge",
                      fontsize=14, fontweight="bold", pad=9)
    axes[0].legend(fontsize=11, loc="lower right", framealpha=0.95)
    axes[1].plot(nat["t"], nat["pad"], color="#2B6CA3", lw=2.4, label="native IBIS pad")
    axes[1].plot(pyb["t"], pyb["pad"], color="#C02626", lw=2.0, ls=(0, (5, 2.2)),
                 label="pybis pad")
    axes[1].set_ylabel("Pad (V)", fontsize=12)
    axes[1].set_xlabel("Time (ns)", fontsize=12)
    axes[1].legend(fontsize=11, loc="lower right", framealpha=0.95)
    for axis in axes:
        axis.set_xlim(RISE_NS - 0.1, RISE_NS + 0.6)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=11)
        for s in axis.spines.values():
            s.set_color("#3A4753")
    fig.tight_layout()
    fig.savefig(out / "lag_localization.png", dpi=175)
    plt.close(fig)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
