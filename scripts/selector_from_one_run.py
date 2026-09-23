#!/usr/bin/env python3
"""Can a better selector be built from the same one stressed run?

Step 8 picks (K, shape) by the alignment of the pad's falling leg at the calibration width -
one number out of a whole measured waveform. Its grid holds builds at 1.2-4.2 % on nine
buffers and the timing finds them on two, so the selector, not the model, is what is losing
those points.

Everything a user has is the IBIS file and that one stressed pad run, so a selector may use
any feature of that single waveform - but nothing from the other widths, which are the score.
Three candidates, all read off the calibration-width run that every build already made:

    timing    |lag| of the falling leg            (what step 8 uses)
    rms       rms difference over the pulse window, the whole shape
    rms+peak  the same rms, with builds whose calibration-width peak is off by more than
              2 % dropped first (the calibration should have matched it; when it cannot,
              the build is straining)

Scored by what each selection then costs on the five stressed widths. No new simulation.

Output: results/selector_from_one_run_2026-09-23/

    py -3.14 scripts/selector_from_one_run.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import spicelab as sl  # noqa: E402
import stage_count_from_file as sc  # noqa: E402

OUT = ROOT / "results" / "selector_from_one_run_2026-09-23"


def builds(dev: str):
    """Every step-8 / step-6 build of this buffer: (K, shape, folder, worst peak, lag, peaks)."""
    out = []
    for step in ("step8", "step6"):
        d = sc.OUT / step / sc.dcc_name(step, dev)
        for p in sorted(d.glob("ibis_prior_K*/sweep.csv")):
            r = list(csv.DictReader(p.open()))[-1]
            m = re.search(r"_prior([0-9.]+)_([0-9.]+)", p.parent.name)
            if not m:
                continue
            pk = [float(v) for k, v in r.items() if k.startswith("pk_d")]
            lag = [float(v) for k, v in r.items() if k.startswith("lag_d")]
            key = (int(r["K"]), float(m.group(1)), float(m.group(2)))
            if any(b["key"] == key for b in out):
                continue                                  # step 6 built the universal corner too
            out.append(dict(key=key, dir=p.parent, worst=max(map(abs, pk)), peaks=pk,
                            lag=lag[-1], peak_calib=pk[-1]))
    return out


def pad_rms(dev: str, folder: Path) -> float:
    """rms between the model's pad and the transistor's, over the calibration-width pulse only."""
    cs = gp.cases(dev)
    depth, w, dref = cs[-1]                                # the calibration width is the deepest case
    raw = folder / f"d{depth}" / "run.raw"
    # the matrix buffers keep the transistor run in the case folder; the variants one level in
    ref = dref / "run.tr0" if dev in gp.MATRIX_SET else dref / "transistor" / "run.tr0"
    if not raw.exists() or not ref.exists():
        return float("nan")
    r = sl.parse_ngspice_raw(raw)
    t, pad = sl.time_ns(r), sl.trace(r, "out")
    tt, tp = gp.tr0_pad(ref)
    rev = gp.RISE_NS + w
    g = np.arange(rev - 0.3, rev + 1.5, 0.002)             # the pulse and its return
    return float(np.sqrt(np.mean((np.interp(g, t, pad) - np.interp(g, tt, tp)) ** 2)) * 1e3)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, picks = [], []
    for dev in sc.BUFFERS:
        gp.VARIANT_NAME = dev
        bs = builds(dev)
        if not bs:
            continue
        for b in bs:
            b["rms"] = pad_rms(dev, b["dir"])
            rows.append(dict(buffer=dev, K=b["key"][0], vt=b["key"][1], alpha=b["key"][2],
                             worst_peak_pct=round(b["worst"], 1), lag_calib_ps=round(b["lag"]),
                             peak_at_calib_pct=round(b["peak_calib"], 1),
                             pad_rms_at_calib_mV=round(b["rms"], 1) if b["rms"] == b["rms"] else ""))
        ok = [b for b in bs if b["rms"] == b["rms"]]
        if not ok:
            continue
        by_timing = min(ok, key=lambda b: abs(b["lag"]))
        by_rms = min(ok, key=lambda b: b["rms"])
        strict = [b for b in ok if abs(b["peak_calib"]) <= 2.0] or ok
        by_rms_peak = min(strict, key=lambda b: b["rms"])
        best = min(ok, key=lambda b: b["worst"])
        picks.append(dict(buffer=dev,
                          timing=f"K{by_timing['key'][0]} {by_timing['key'][1]:g}/{by_timing['key'][2]:g}",
                          timing_pct=round(by_timing["worst"], 1),
                          rms=f"K{by_rms['key'][0]} {by_rms['key'][1]:g}/{by_rms['key'][2]:g}",
                          rms_pct=round(by_rms["worst"], 1),
                          rms_peak=f"K{by_rms_peak['key'][0]} {by_rms_peak['key'][1]:g}/{by_rms_peak['key'][2]:g}",
                          rms_peak_pct=round(by_rms_peak["worst"], 1),
                          best_possible_pct=round(best["worst"], 1),
                          best=f"K{best['key'][0]} {best['key'][1]:g}/{best['key'][2]:g}"))
    for name, rs in (("selector_builds.csv", rows), ("selector_picks.csv", picks)):
        with (OUT / name).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rs[0]))
            w.writeheader()
            w.writerows(rs)
    print(f"  {'buffer':13s} {'by timing':>20s} {'by pad rms':>20s} {'rms, peak within 2 %':>26s} {'best in grid':>18s}")
    for o in picks:
        print(f"  {o['buffer']:13s} {o['timing']:>11s} {o['timing_pct']:6.1f} % "
              f"{o['rms']:>11s} {o['rms_pct']:6.1f} % {o['rms_peak']:>17s} {o['rms_peak_pct']:6.1f} % "
              f"{o['best']:>11s} {o['best_possible_pct']:5.1f} %")
    for k, label in (("timing_pct", "timing"), ("rms_pct", "pad rms"), ("rms_peak_pct", "rms + peak gate"),
                     ("best_possible_pct", "best in grid")):
        v = [o[k] for o in picks]
        print(f"  {label:16s} within 10 %: {sum(1 for x in v if x <= 10)} of {len(v)}   "
              f"mean {sum(v) / len(v):.1f} %   worst {max(v):.1f} %")
    print(f"  wrote {OUT / 'selector_picks.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
