#!/usr/bin/env python3
"""Is the stress pedestal the difference between one V-T trajectory and two?

What is established about the pedestal (`pedestal_localization.py`,
`delay_pedestal_test.py`):

* it is already present in Ku and Kd at the same size as in the pad, so it is
  made upstream of the output stage;
* on io_buf, native's Ku tracks the **transistor's own** Ku to +1..+19 ps while
  ours is +64..+111 ps late -- our coefficient timing is the wrong one;
* it is **not** the fitted command transport delays: scaled to 5% of nominal,
  61 ps of the 85 survives, and the response is non-monotonic;
* it is **not** the gate-state time constants: scaled to 5%, 95 ps survives.

Every timing parameter in the command layer has been ruled out. What is left is
structural. Our Ku(t) is a **single fixed trajectory** played out by a scalar gate
state, so the only thing the model knows at a reversal is "how far along" it is.
HSPICE's B-element with `ramp_rwf=2` instead **interpolates between two recorded
V-T waveforms using the actual pad voltage**, so it can represent a pad caught at
an intermediate voltage.

That difference should vanish at full swing -- the pad is settled at the reversal,
so there is nothing intermediate to represent -- and appear under stress. Which is
exactly the pedestal's signature.

The test: run native with `ramp_rwf=1`, which forces it onto a single waveform
like ours. If the pedestal is the one-trajectory limitation, native should acquire
one too.

    py -3.14 scripts/native_waveform_count_test.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pedestal_localization import best_lag, outward_window, read  # noqa: E402

R = ROOT / "results"
IBS = R / "defect_b_full_swing_2026-09-03" / "native" / "input.ibs"
REFCASE = (R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
           / "io_buf_short_high_w1792ps.csv")
OUT = R / "native_waveform_count_2026-09-04"

SUPPLY = 3.3
RISE_NS, FALL_NS, EDGE_NS, STOP_NS = 5.000, 6.790, 0.050, 22.0
NL = "\n"


def deck(count: int) -> str:
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  "
           f"{FALL_NS}n {SUPPLY}  {FALL_NS + EDGE_NS}n 0  {STOP_NS}n 0)")
    return (f"* io_buf native IBIS, stressed, ramp_rwf={count}" + NL
            + ".title native waveform count" + NL
            + ".option post=2 probe accurate ingold=2" + NL
            + ".temp 27" + NL
            + f"Vin in_dig 0 {pwl}" + NL
            + f"Ven en_sig 0 DC {SUPPLY}" + NL
            + f"VPU pu_ref 0 DC {SUPPLY}" + NL
            + "VPD pd_ref 0 DC 0" + NL
            + f"VPC pc_ref 0 DC {SUPPLY}" + NL
            + "VGC gc_ref 0 DC 0" + NL
            + "BIBIS pu_ref pd_ref pad in_dig en_sig dig_q pc_ref gc_ref" + NL
            + "+ file='input.ibs' model='driver' typ=typ power=off interpol=1" + NL
            + f"+ ramp_rwf={count}" + NL
            + f"+ ramp_fwf={count}" + NL
            + "+ xv_pu=ku" + NL
            + "+ xv_pd=kd" + NL
            + "Rdig dig_q 0 1k" + NL
            + "Rload pad 0 50.0" + NL
            + "Cload pad 0 2.0p" + NL
            + ".probe tran V(pad) V(ku) V(kd)" + NL
            + f".tran 0.002n {STOP_NS}n" + NL
            + ".end" + NL)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ref = read(REFCASE)
    t_ref = ref["time_ns"]
    lo, hi = outward_window(t_ref, ref["silicon_pad"], RISE_NS)
    grid = np.arange(lo, hi, 0.002)
    silicon_pad = np.interp(grid, t_ref, ref["silicon_pad"])
    silicon_ku = np.interp(grid, t_ref, ref["silicon_ku"])
    ours_pad = np.interp(grid, t_ref, ref["pybis_pad"])
    ours_ku = np.interp(grid, t_ref, ref["pybis_ku"])

    print("  io_buf short high 1792 ps. Lag over the outward leg vs the "
          "transistor, ps")
    print("  (+ = later than the transistor).\n")
    print(f"    {'build':<28}{'Ku':>10}{'pad':>10}")
    a, _ = best_lag(grid, silicon_ku, ours_ku, lo, hi)
    b, _ = best_lag(grid, silicon_pad, ours_pad, lo, hi)
    print(f"    {'ours (one trajectory)':<28}{a:>10.0f}{b:>10.0f}")

    for count in (2, 1):
        d = OUT / f"rwf{count}"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(IBS, d / "input.ibs")
        (d / "run.sp").write_text(deck(count), encoding="utf-8")
        if not (d / "run.tr0").exists():
            if sl.hspice(d, timeout_s=900) is None:
                print(f"    native ramp_rwf={count}: run failed")
                continue
        raw = sl.parse_hspice_tr0(d / "run.tr0")
        t = sl.time_ns(raw)
        pad = np.interp(grid, t, sl.trace(raw, "pad"))
        ku = np.interp(grid, t, sl.signal(raw, "v(ku)"))
        a, _ = best_lag(grid, silicon_ku, ku, lo, hi)
        b, _ = best_lag(grid, silicon_pad, pad, lo, hi)
        label = ("native, two waveforms" if count == 2
                 else "native, ONE waveform")
        print(f"    {label:<28}{a:>10.0f}{b:>10.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
