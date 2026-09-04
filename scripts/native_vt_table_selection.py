#!/usr/bin/env python3
"""How much V-T data is native IBIS actually using, and does it matter?

HSPICE's B-element does not simply play back a V-T table. `ramp_rwf` / `ramp_fwf`
choose how *much* waveform data it uses (PrimeSim Continuum Elements, ch 4):

    0 = use [Ramp] data
    1 = use one waveform  (the first of that kind in the file)
    2 = use two waveforms (the first two)   -- the documented default

Thirty-two scripts in this study pass `ramp_rwf=2 ramp_fwf=2`. That is the default
and the two-fixture solve IBIS intends, so it is defensible -- but it is not
neutral, and on ex2 it fails outright: native's pad never leaves 0.03 V on a
1.05 ns pulse the transistor takes to 1.47 V, while `=1` tracks the transistor to
within 0.03 V. HSPICE warns about neither. That retracts "native does not respond
on ex2" as a claim about IBIS.

io_buf is the study's primary buffer and native is the bar every pybis number is
quoted against, so the same question has to be settled there rather than assumed.
This runs io_buf native both ways -- full swing and truncated -- against the
transistor, and reports excursion and 50% crossing for each.

One caveat when reading the `=1` column: it plays the *first* table, and the order
differs per buffer (inv_chain 1.8/0.0; io_buf and ex2 0.0/3.3). These benches load
the pad with 50 ohm to ground, so on io_buf `=1` is the load-matched waveform --
a best case, not a fair general model.

    py -3.14 scripts/native_vt_table_selection.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402

IBIS = ROOT / "results" / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
NETLIST = ROOT / "buffers" / "models" / "io_buf.sp"
MODCARD = ROOT / "buffers" / "models" / "hspice.mod"
OUT = ROOT / "results" / "native_vt_table_selection_2026-09-03"

MODEL = "driver"
SUPPLY_V, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
RISE_NS, STOP_NS = 5.0, 22.0

# Full swing (10 ns high, fully settled) plus three truncated pulses.
# io_buf has a ~1.9 ns input-to-pad delay, so sub-ns pulses die before the pad
# moves at all. These widths are the band the study's own io_buf depth cases
# use (short_high_depth43 = 973 ps, depth86 = 1214 ps): partial excursions.
CASES = [("full_swing", 10.0), ("w1300ps", 1.300), ("w1150ps", 1.150),
         ("w1000ps", 1.000), ("w900ps", 0.900)]


def _pwl(width_ns: float) -> str:
    hi = RISE_NS + width_ns
    return (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + 0.001}n {SUPPLY_V}  "
            f"{hi}n {SUPPLY_V}  {hi + 0.001}n 0  {STOP_NS}n 0)")


def _run(d: Path, deck: str):
    """Run a deck, reusing the .tr0 when the deck text is unchanged."""
    d.mkdir(parents=True, exist_ok=True)
    sp, tr0 = d / "run.sp", d / "run.tr0"
    if tr0.exists() and sp.exists() and sp.read_text(encoding="utf-8") == deck:
        r = sl.parse_hspice_tr0(tr0)
        return sl.time_ns(r), sl.signal(r, "v(pad)")
    sp.write_text(deck, encoding="utf-8")
    out = sl.hspice(d, timeout_s=900)
    if out is None:
        return None
    r = sl.parse_hspice_tr0(out)
    return sl.time_ns(r), sl.signal(r, "v(pad)")


def transistor(d: Path, width: float):
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(NETLIST, d / "io_buf.sp")
    shutil.copy2(MODCARD, d / "hspice.mod")
    return _run(d, f"""* io_buf transistor
.title io_buf transistor
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {_pwl(width)}
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
""")


def native(d: Path, width: float, idx: int):
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(IBIS, d / "input.ibs")
    return _run(d, f"""* io_buf native IBIS, ramp_rwf={idx}
.title io_buf native ibis rwf{idx}
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {_pwl(width)}
Ven en_sig 0 DC {SUPPLY_V}
VPU pu_ref 0 DC {SUPPLY_V}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUPPLY_V}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig en_sig dig_q pc_ref gc_ref
+ file='input.ibs' model='{MODEL}' typ=typ power=off interpol=1
+ ramp_rwf={idx} ramp_fwf={idx}
Rdig dig_q 0 1k
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad)
.tran 0.002n {STOP_NS}n
.end
""")


def cross(t, v, level, after):
    for i in range(1, len(v)):
        if t[i] >= after and v[i - 1] < level <= v[i]:
            return float(t[i - 1] + (level - v[i - 1]) * (t[i] - t[i - 1]) / (v[i] - v[i - 1]))
    return float("nan")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{'case':<12}{'build':<14}{'excursion V':>13}{'vs tx':>9}{'t50 ns':>9}{'vs tx':>10}")
    rows = []
    for name, width in CASES:
        base = np.nan
        tx = transistor(OUT / name / "transistor", width)
        if tx is None:
            print(f"{name:<12}transistor     FAILED")
            continue
        t, v = tx
        base = float(np.interp(RISE_NS - 0.2, t, v))
        m = (t > RISE_NS - 0.1) & (t < RISE_NS + max(width, 1.0) + 3.0)
        tx_exc = float(v[m].max() - base)
        tx_t50 = cross(t, v, base + 0.5 * tx_exc, RISE_NS - 0.1)
        print(f"{name:<12}{'transistor':<14}{tx_exc:>13.4f}{'--':>9}{tx_t50:>9.4f}{'--':>10}")
        for idx in (1, 2):
            r = native(OUT / name / f"native_rwf{idx}", width, idx)
            if r is None:
                print(f"{name:<12}{'native rwf'+str(idx):<14}   FAILED")
                continue
            tn, vn = r
            nb = float(np.interp(RISE_NS - 0.2, tn, vn))
            mn = (tn > RISE_NS - 0.1) & (tn < RISE_NS + max(width, 1.0) + 3.0)
            exc = float(vn[mn].max() - nb)
            # timed at 50% of the *transistor's* excursion, so the two builds are
            # measured against one common level rather than each against itself
            t50 = cross(tn, vn, nb + 0.5 * tx_exc, RISE_NS - 0.1)
            dt = (t50 - tx_t50) * 1e3 if np.isfinite(t50) and np.isfinite(tx_t50) else np.nan
            tag = "  <- single, load-matched waveform" if idx == 1 else ""
            print(f"{name:<12}{'native rwf'+str(idx):<14}{exc:>13.4f}"
                  f"{exc - tx_exc:>+9.4f}{t50:>9.4f}{dt:>+9.1f}p{tag}")
            rows.append((name, idx, exc, exc - tx_exc, dt))
        print()

    if rows:
        print("summary -- |excursion error| and |timing error|, averaged over cases")
        for idx in (1, 2):
            sub = [r for r in rows if r[1] == idx]
            if not sub:
                continue
            de = np.mean([abs(r[3]) for r in sub])
            dts = [abs(r[4]) for r in sub if np.isfinite(r[4])]
            print(f"  ramp_rwf={idx}: excursion {de:.4f} V"
                  + (f", timing {np.mean(dts):.1f} ps" if dts else ", timing n/a"))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
