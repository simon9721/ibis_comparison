#!/usr/bin/env python3
"""One gate for both halves: the pull-down follows the pull-up's gate node.

ex2's and inv_chain's output stage is a single inverter -- one predriver node
drives the P and the N side. Our model gives the pull-down its own gate (GDN,
from its own delay lines and its own RC), so when the pull-up gate is made to
track the real gate under stress, the pull-down is still on its own clock.

This takes an existing build (shipped, or any cascade/hybrid/slew build) and
ties the pull-down to the same node:

    GDN       = 1 - GUP            (was: its own RC from PDCMDLVL)
    GDNTARGET = 1 - GUPTARGET

then re-derives the two Kd maps from the shipped full-swing gate-part Kd(t)
against the new GDN(t), so full swing is preserved by construction (same
discipline as the cascade prototype). Scored on the matrix stressed widths.

    py -3.14 scripts/shared_gate_prototype.py --variant ex2 --base shipped hybrid300ps slew700ps cascade5
    py -3.14 scripts/shared_gate_prototype.py --variant inv_chain --base shipped slew56ps hybrid40ps
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_cascade_prototype as gc  # noqa: E402

R = ROOT / "results"
G = R / "gate_cascade_prototype_2026-09-09"


def patch_shared(sub: str) -> str:
    s = re.sub(r"^BGDN GDN 0 I = .*$", "BGDN GDN 0 V = 1.0 - V(GUP)", sub, count=1, flags=re.M)
    s = re.sub(r"^CGDN GDN 0 .*\n", "", s, count=1, flags=re.M)
    s = re.sub(r"^BGDNBASE GDNBASE 0 .*\n", "", s, count=1, flags=re.M)
    s = re.sub(r"^RGDN GDN GDNBASE .*\n", "", s, count=1, flags=re.M)
    s = re.sub(r"^BGDNTARGET GDNTARGET 0 V = .*$", "BGDNTARGET GDNTARGET 0 V = 1.0 - V(GUPTARGET)", s, count=1, flags=re.M)
    assert "BGDN GDN 0 V = 1.0 - V(GUP)" in s and "1.0 - V(GUPTARGET)" in s
    return s


def derive_kd_maps(full_new: dict, full_ship: dict):
    """KDGATE_OFF (GDN falling, input rise) and KDGATE_ON (GDN rising) against the new GDN(t).

    Split at the GDN minimum of the full-swing run; both branches resampled on a
    uniform 200-point grid so the pwl abscissa stays monotonic.
    """
    t, gdn = full_new["t"], full_new["gdn"]
    kb = np.interp(t, full_ship["t"], full_ship["kdgate_base"])
    win = (t >= gp.RISE_NS - 0.05) & (t <= 20.0)
    imin = int(np.argmin(np.where(win, gdn, 9.0)))
    grid = np.linspace(0.0, 1.0, 200)

    def branch(mask):
        x, y = gdn[mask], kb[mask]
        o = np.argsort(x)
        x, y = x[o], y[o]
        ux, idx = np.unique(np.round(x, 5), return_inverse=True)
        uy = np.bincount(idx, y) / np.bincount(idx)
        return grid, np.interp(grid, ux, uy)

    off = branch((t >= gp.RISE_NS - 0.05) & (t <= t[imin]))
    on = branch((t >= t[imin]) & (t <= 20.0))
    return on, off


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="ex2")
    ap.add_argument("--base", nargs="*", default=["shipped"])
    args = ap.parse_args()
    sup, ibis = gp.VARIANTS[args.variant]
    gp.VARIANT_NAME = args.variant
    OUT = G / args.variant
    ship = (OUT / "shipped/driver.sub").read_text(encoding="utf-8")
    full_ship = gp.run_ours(OUT / "shipped/full", ship, sup, 10.0)
    cs = gp.cases(args.variant)
    refs = {d_: gp.tr0_pad(d / "run.tr0" if args.variant in gp.MATRIX_SET else d / "transistor/run.tr0") for d_, _, d in cs}
    rows = []
    print(f"\n  {args.variant}: pull-down tied to the pull-up gate (GDN = 1 - GUP), Kd maps re-derived")
    print(f"    {'build':<22}{'FS Ku rms':>10}{'FS Kd rms':>10} | " + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs)
          + " | " + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs))
    for b in args.base:
        src = OUT / b / ("driver.sub" if b == "shipped" else "driver_cascade.sub")
        text0 = src.read_text(encoding="utf-8")
        for label, text in ((b, text0), (b + "_shared", None)):
            tag = OUT / label
            if text is None:
                text1 = patch_shared(text0)
                full_new = gp.run_ours(tag / "full_pass1", text1, sup, 10.0)
                on, off = derive_kd_maps(full_new, full_ship)
                text = gc.patch_kd_maps(text1, on, off)
                tag.mkdir(parents=True, exist_ok=True)
                (tag / "driver_cascade.sub").write_text(text, encoding="utf-8")
            fs = gp.run_ours(tag / "full", text, sup, 10.0)
            tf = full_ship["t"]
            m = (tf > gp.RISE_NS - 0.5) & (tf < 17.0)
            ku_rms = float(np.sqrt(np.mean((np.interp(tf[m], fs["t"], fs["ku"]) - full_ship["ku"][m]) ** 2)))
            kd_rms = float(np.sqrt(np.mean((np.interp(tf[m], fs["t"], fs["kd"]) - full_ship["kd"][m]) ** 2)))
            pks, lags = [], []
            for depth, w, d in cs:
                r = gp.run_ours(tag / f"d{depth}", text, sup, w)
                pk, lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
                pks.append(pk)
                lags.append(lag)
            rows.append(dict(build=label, fs_ku_rms=round(ku_rms, 4), fs_kd_rms=round(kd_rms, 4),
                             **{f"pk_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, pks)},
                             **{f"lag_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, lags)}))
            print(f"    {label:<22}{ku_rms:>10.4f}{kd_rms:>10.4f} | " + "".join(f"{v:>9.1f}" for v in pks)
                  + " | " + "".join(f"{v:>9.0f}" for v in lags))
    with (OUT / "shared_gate_sweep.csv").open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        if fh.tell() == 0:
            w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {OUT / 'shared_gate_sweep.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
