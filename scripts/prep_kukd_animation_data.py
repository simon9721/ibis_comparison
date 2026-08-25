#!/usr/bin/env python3
"""Dump real numbers for the Ku/Kd extraction animation.

The animation should show the actual solve, not a sketch of it, so this pulls
the two fixture waveforms that were already simulated, runs the same 2x2 solve
the study uses, and records one representative instant in full detail.

Every number the animation shows has to be traceable on screen, so the dump
carries more than the solve itself: the pullup and pulldown I-V curves the two
multipliers are read off, and the term-by-term breakdown of each right-hand
side. Otherwise a viewer sees four decimals appear with no origin.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / ".codex_deps" / "presentation" / "python", ROOT, ROOT / "scripts",
          ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(q))

import numpy as np
from pybis2spice import pybis2spice
from eye_diagram import parse_hspice_tr0
import run_three_buffer_realistic_pulse_campaign as base
from extract_silicon_kukd import FixtureWaveform, R_FIXTURE, CORNER

CASE = ROOT / "results" / "stress_method_matrix_2026-08-20" / "hybrid" / "hspice_fixtures" / "inv_chain" / "short_high_w135ps"
OUT = ROOT / "results" / "kukd_animation" / "data.json"


def pad_of(run_dir):
    raw = parse_hspice_tr0(run_dir / "run.tr0")
    t = np.asarray(raw["time"], dtype=float)
    pad = np.asarray(raw[next(k for k in raw if "pad_sp" in k)], dtype=float)
    return t, pad


def iv_curves(ibis, vcc, n=240):
    """The pullup and pulldown tables as the solve sees them, versus pad voltage.

    Same call the per-timestep lookup makes, just swept over the rail instead of
    over a waveform, so the curve drawn is the curve read from.
    """
    v = np.linspace(0.0, vcc, n)
    pullup_ref = pybis2spice.get_reference(ibis.pullup_ref, ibis.v_range, CORNER)
    pulldown_ref = pybis2spice.get_reference(ibis.pulldown_ref, 0, CORNER)
    pu = pybis2spice.get_current_data_from_iv_data(
        v, ibis.iv_pullup, pullup_ref, CORNER, iv_data_adjust=ibis.iv_pwr_clamp)
    pd = pybis2spice.get_current_data_from_iv_data(
        v, ibis.iv_pulldown, pulldown_ref, CORNER, iv_data_adjust=ibis.iv_gnd_clamp)
    return v, pu, pd


def main():
    device = next(d for d in base.DEVICES if d.device_id == "inv_chain")
    ibis = pybis2spice.DataModel(
        pybis2spice.get_ibis_model_ecdtools(str(device.fast_ibis)),
        model_name=device.model, component_name=device.component)

    t_lo, pad_lo = pad_of(CASE / "vfix_0")
    t_hi, pad_hi = pad_of(CASE / "vfix_vcc")
    low = np.column_stack([t_lo, pad_lo, pad_lo, pad_lo])
    high = np.column_stack([t_hi, pad_hi, pad_hi, pad_hi])

    time = np.unique(np.sort(np.concatenate([t_lo, t_hi])))
    wl = FixtureWaveform(low, [0.0, 0.0, 0.0], R_FIXTURE)
    wh = FixtureWaveform(high, [device.supply_v] * 3, R_FIXTURE)
    pu1, pd1, pc1, gc1, rf1, cc1, cf1 = pybis2spice.generating_current_data(ibis, time, CORNER, wl)
    pu2, pd2, pc2, gc2, rf2, cc2, cf2 = pybis2spice.generating_current_data(ibis, time, CORNER, wh)
    i1 = gc1 + pc1 + rf1 - cc1 - cf1
    i2 = gc2 + pc2 + rf2 - cc2 - cf2

    ku = np.full(len(time), np.nan)
    kd = np.full(len(time), np.nan)
    for n in range(len(time)):
        m = np.array([[pu1[n], pd1[n]], [pu2[n], pd2[n]]])
        if abs(np.linalg.det(m)) > 1e-18:
            ku[n], kd[n] = np.linalg.solve(m, np.array([i1[n], i2[n]]))

    t_ns = time * 1e9
    # A representative instant: the moment the pullup is about half on, so both
    # devices carry real current and neither term dominates the solve.
    window = (t_ns > 5.05) & (t_ns < 5.60) & np.isfinite(ku)
    cand = np.where(window)[0]
    idx = int(cand[int(np.argmin(np.abs(ku[cand] - 0.5)))])

    def dec(a, n=420):
        keep = (t_ns >= 4.85) & (t_ns <= 5.85)
        arr = np.asarray(a)[keep]
        step = max(1, len(arr) // n)
        return [float(x) for x in arr[::step]]

    v_iv, pu_iv, pd_iv = iv_curves(ibis, device.supply_v)

    snap = {
        "t_ns": float(t_ns[idx]),
        "v_lo": float(np.interp(time[idx], t_lo, pad_lo)),
        "v_hi": float(np.interp(time[idx], t_hi, pad_hi)),
        "pu_lo": float(pu1[idx]), "pd_lo": float(pd1[idx]), "rhs_lo": float(i1[idx]),
        "pu_hi": float(pu2[idx]), "pd_hi": float(pd2[idx]), "rhs_hi": float(i2[idx]),
        # The right-hand side is not measured directly -- it is everything in the
        # pad current that is already known, so the animation has to be able to
        # show it being assembled term by term.
        "terms_lo": {"rfix": float(rf1[idx]), "pwr_clamp": float(pc1[idx]),
                     "gnd_clamp": float(gc1[idx]), "c_comp": float(cc1[idx]),
                     "c_fixture": float(cf1[idx])},
        "terms_hi": {"rfix": float(rf2[idx]), "pwr_clamp": float(pc2[idx]),
                     "gnd_clamp": float(gc2[idx]), "c_comp": float(cc2[idx]),
                     "c_fixture": float(cf2[idx])},
        "ku": float(ku[idx]), "kd": float(kd[idx]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "device": "inv_chain", "vcc": device.supply_v, "r_fixture": R_FIXTURE,
        "c_comp": float(ibis.c_comp[CORNER - 1]),
        "t": dec(t_ns), "pad_lo": dec(np.interp(time, t_lo, pad_lo)),
        "pad_hi": dec(np.interp(time, t_hi, pad_hi)),
        "ku": dec(ku), "kd": dec(kd),
        "iv": {"v": [float(x) for x in v_iv],
               "pu": [float(x) for x in pu_iv],
               "pd": [float(x) for x in pd_iv]},
        "snapshot": snap,
    }, indent=1), encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))
    print("snapshot at t = %.4f ns" % snap["t_ns"])
    for k, v in snap.items():
        if isinstance(v, dict):
            print("   %-8s %s" % (k, " ".join("%s=%.6g" % kv for kv in v.items())))
        else:
            print("   %-8s %s" % (k, ("%.6g" % v)))


if __name__ == "__main__":
    raise SystemExit(main())
