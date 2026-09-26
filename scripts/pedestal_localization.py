#!/usr/bin/env python3
"""Where does the stress pedestal enter -- the coefficients, or the output stage?

`timing_shift_accumulation_2026-09-04` split the timing shift in two. The
accumulating part is C_comp and is shared with native IBIS. What is left is a
**constant pedestal that appears only under stress and is ours alone**: our pad
runs +83..+99 ps later than native's on io_buf, and 12..41 ps *earlier* on
inv_chain and ex2, where at full swing the two agree to 2-4 ps.

Nothing explains it. This localises it, the same way the full-swing lag was
localised: the pad is built as

    pad  <-  Ku(t) x I_pu(V) + Kd(t) x I_pd(V) + clamps + C_comp dV/dt

so if the pedestal is already present in Ku(t) it is made upstream -- in the
command layer, the gate state, or the table replay. If Ku(t) agrees and only the
pad differs, it is made in the output stage.

No new simulation. The stress matrix already carries all three coefficient sets
next to all three pads: `silicon_*` from the two-fixture solve on the transistor
(ground truth), `hspice_*` from native's `xv_pu`/`xv_pd`, and `pybis_*` from ours.

Measure: the lag that best aligns one trace to another over the outward leg, by
RMS. Reported with the residual after alignment, because a lag only describes the
difference if the shapes match once shifted -- a large residual means the traces
differ in shape and the number is not a delay.

    py -3.14 scripts/pedestal_localization.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

R = ROOT / "results"
MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
FINE = R / "settled_offset_diagnosis_2026-08-27" / "09_comprehensive_offset_fix_comparison.csv"

EVENT_NS = {"short_high": 5.0, "short_low": 10.0}
CASES = (("io_buf", "short_high"), ("inv_chain", "short_high"),
         ("ex2", "short_high"))


def read(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open()))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def best_lag(t, ref, y, lo, hi, max_lag_ns=0.30):
    """(lag ps, residual rms after aligning) for `y` against `ref` over [lo, hi].

    Positive lag means `y` happens later. Both traces are put on a fine uniform
    grid first: the matrix files are on ngspice's adaptive steps, ~33 ps apart in
    this window, and shifting on that grid quantises the answer.
    """
    grid = np.arange(lo, hi, 0.002)
    a = np.interp(grid, t, ref)
    b = np.interp(grid, t, y)
    span = np.ptp(a)
    if span < 1e-9:
        return float("nan"), float("nan")
    lags = np.arange(-max_lag_ns, max_lag_ns + 1e-9, 0.001)
    best, best_err = np.nan, np.inf
    for lag in lags:
        err = np.sqrt(np.mean((np.interp(grid - lag, grid, b) - a) ** 2))
        if err < best_err:
            best_err, best = err, lag
    # Sign: shifting b by `lag` samples it at grid-lag, which moves it later. If
    # b is genuinely D late, the best shift is -D. Negate so the number reads as
    # "how much later b is", which is what every other measurement here reports.
    return -best * 1e3, best_err / span


def outward_window(t, pad, start):
    """From the pad's own peak to 1.5 ns past it -- the leg the pedestal is on."""
    w = (t >= start) & (t <= start + 5.0)
    i = int(np.argmax(pad[w]))
    t_peak = float(t[w][i])
    return t_peak, min(t_peak + 1.5, float(t[-1]) - 0.05)


def main() -> int:
    print("  Lag of ours against native over the outward leg, ps "
          "(+ = ours later),")
    print("  with the residual after alignment as a fraction of the trace's own "
          "span.\n")
    print(f"    {'case':<26}" + "".join(f"{h:>15}" for h in
          ("Ku vs nat", "Kd vs nat", "pad vs nat",
           "Ku vs Si", "nat Ku vs Si")))

    # The fine-grained case first: a 5 ps uniform grid, and it carries native's
    # coefficients too. Everything else is on the matrix's adaptive steps.
    if FINE.exists():
        d = read(FINE)
        t = d["time_ns"]
        t_peak, hi = outward_window(t, d["transistor_pad_v"], 5.0)
        row = []
        for ours, theirs in (("original_ku", "native_ku"),
                             ("original_kd", "native_kd"),
                             ("original_pad_v", "native_pad_v"),
                             ("original_ku", "transistor_ku"),
                             ("native_ku", "transistor_ku")):
            lag, res = best_lag(t, d[theirs], d[ours], t_peak, hi)
            row.append(f"{lag:+6.0f}({res:4.2f})")
        print(f"    {'io_buf 1792 [5ps grid]':<26}" + "".join(f"{x:>15}" for x in row))

    for device, direction in CASES:
        start = EVENT_NS[direction]
        for path in sorted(MATRIX.glob(f"{device}_{direction}_w*ps.csv"),
                           key=lambda p: -int(p.stem.split("_w")[1].rstrip("ps"))):
            width = path.stem.split("_w")[1]
            d = read(path)
            t = d["time_ns"]
            t_peak, hi = outward_window(t, d["silicon_pad"], start)
            row = []
            for ours, theirs in (("pybis_ku", "hspice_ku"),
                                 ("pybis_kd", "hspice_kd"),
                                 ("pybis_pad", "hspice_pad"),
                                 ("pybis_ku", "silicon_ku"),
                                 ("hspice_ku", "silicon_ku")):
                lag, res = best_lag(t, d[theirs], d[ours], t_peak, hi)
                row.append(f"{lag:+6.0f}({res:4.2f})")
            print(f"    {device + ' ' + width:<26}" + "".join(f"{x:>15}" for x in row))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
