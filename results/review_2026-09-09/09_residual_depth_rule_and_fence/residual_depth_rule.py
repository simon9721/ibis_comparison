#!/usr/bin/env python3
"""Scale the falling residual by the DEPTH the pad reached -- the 12/12 law -- instead of by GUP.

`cross_device_stress_2026-09-08` and the three open-drains found the same law on
every buffer: the transistor's falling residual (its Kd minimum after the reversal)
shrinks toward zero in proportion to how far the output got. Ours is a constant
calibrated on a complete transition. The io_buf correction (`FRAC`, a peak-hold
on GUP) scaled it by the *gate* state instead, and was measured 2.4x too steep.

This tests the law directly. Three builds per stressed case:

    shipped      the residual at full size
    frac_gup     scaled by GUP held at the reversal      (the io_buf correction)
    frac_depth   scaled by  pad peak / full-swing plateau (the measured law)

The plateau is the model's own settled full-swing level, so the scale is 1 at
full swing by construction. Scored against the transistor: pad peak error, lag,
and the Kd residual (rms and minimum) over the grid-converged window past the
pad peak. On io_buf the +1.8 ns bump amplitude is reported too, since the earlier
FRAC halved it by staying applied too long.

    py -3.14 scripts/residual_depth_rule.py --variant io_buf
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
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402

R = ROOT / "results"
MXF = R / "stress_method_matrix_2026-08-20/delay_cmd/hspice_fixtures/io_buf"

PEAK_HOLD_GUP = (
    "BGUPHOLD GUPHOLD 0 I = -1e-12 * ((V(GUP) > V(GUPHOLD)) ? "
    "(V(GUP) - V(GUPHOLD)) / 1p : (V(GUP) - V(GUPHOLD)) / 5n)\n"
    "CGUPHOLD GUPHOLD 0 1e-12 ic=0\nRGUPHOLD GUPHOLD 0 1e12\n"
    "BFRAC FRAC 0 V = min(max(V(GUPHOLD), 0.05), 1.0)\n")


def peak_hold_pad(plateau: float, fence_ns: float | None = None) -> str:
    # Fenced: the scale applies only while the stopwatch since the last input
    # edge is short -- i.e. during the truncated fall -- and is 1 afterwards, so
    # it cannot reach the pull-down turn-on at +1.8 ns.
    frac = f"min(max(V(PADHOLD) / {plateau:.6g}, 0.05), 1.0)"
    if fence_ns is not None:
        frac = f"(V(HNX) < {fence_ns:.4g}) ? {frac} : 1.0"
    return (
        "BPADHOLD PADHOLD 0 I = -1e-12 * ((V(OUT,VSS) > V(PADHOLD)) ? "
        "(V(OUT,VSS) - V(PADHOLD)) / 1p : (V(OUT,VSS) - V(PADHOLD)) / 5n)\n"
        "CPADHOLD PADHOLD 0 1e-12 ic=0\nRPADHOLD PADHOLD 0 1e12\n"
        f"BFRAC FRAC 0 V = {frac}\n")


def patch(text: str, hold_block: str) -> str:
    anchor = "BKURES_TABLE"
    text = text[:text.index(anchor)] + hold_block + text[text.index(anchor):]
    for node, target in (("KURES_TABLE", "V(KURES_F)"), ("KDRES_TABLE", "V(KDRES_F)")):
        pat = rf"^(B\S+ {node} 0 V = .*?){re.escape(target)}"
        text, n = re.subn(pat, rf"\1({target} * V(FRAC))", text, count=1, flags=re.M)
        if n != 1:
            raise RuntimeError(f"{node}: selector not found")
    return text


def fixture(p: Path) -> np.ndarray:
    raw = sl.parse_hspice_tr0(p)
    t = np.asarray(raw["time"], float)
    v = np.asarray(raw[next(k for k in raw if "pad" in k)], float)
    return np.column_stack([t, v, v, v])


def silicon_kd(variant: str, data, depth: int, d: Path, sup: float):
    if variant == "io_buf":
        lo, hi = fixture(MXF / f"short_high_w{depth}ps/vfix_0/run.tr0"), fixture(MXF / f"short_high_w{depth}ps/vfix_vcc/run.tr0")
    else:
        lo, hi = fixture(d / "fixture_0/run.tr0"), fixture(d / "fixture_vcc/run.tr0")
    s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
    return s[:, 0] * 1e9, s[:, 2]


def bump_mv(t, y, rev):
    g = np.arange(rev + 1.3, rev + 3.0, 0.001)
    v = np.interp(g, t, y)
    return float(v.max()) * 1e3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="io_buf")
    args = ap.parse_args()
    sup, ibis = gp.VARIANTS[args.variant]
    gp.VARIANT_NAME = args.variant
    OUT = R / "residual_depth_rule_2026-09-09" / args.variant
    OUT.mkdir(parents=True, exist_ok=True)
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    ship_dir = OUT / "shipped"
    ship_dir.mkdir(parents=True, exist_ok=True)
    if not (ship_dir / "driver.sub").exists():
        subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(ship_dir / "driver.sub"))
    ship = (ship_dir / "driver.sub").read_text(encoding="utf-8")

    full = gp.run_ours(ship_dir / "full", ship, sup, 10.0)
    plateau = float(np.interp(14.5, full["t"], full["pad"]))
    print(f"  {args.variant}: model full-swing plateau {plateau:.4f} V")
    builds = {"shipped": ship,
              "frac_gup": patch(ship, PEAK_HOLD_GUP),
              "frac_depth": patch(ship, peak_hold_pad(plateau)),
              "fenced_1.2": patch(ship, peak_hold_pad(plateau, 1.2)),
              "fenced_0.8": patch(ship, peak_hold_pad(plateau, 0.8))}

    cs = gp.cases(args.variant)
    rows = []
    hdr = f"    {'case':<7}{'build':<11}{'pk %':>7}{'lag ps':>8}{'Kd rms':>8}{'Kd min':>8}{'si Kdmin':>9}{'FRAC@rev':>9}"
    if args.variant == "io_buf":
        hdr += f"{'bump mV':>9}{'si bump':>9}"
    print(hdr)
    for depth, w, d in cs:
        t_si, si = gp.tr0_pad(d / "run.tr0" if args.variant == "io_buf" else d / "transistor/run.tr0")
        rev = gp.RISE_NS + w
        tpk = float(t_si[int(np.argmax(np.where((t_si > rev - 0.1) & (t_si < rev + 3.0), si, -9e9)))])
        ts, kd_si = silicon_kd(args.variant, data, depth, d, sup)
        win = np.arange(tpk + 0.05, tpk + 0.40, 0.002)
        sk = np.interp(win, ts, kd_si)
        for name, text in builds.items():
            r = gp.run_ours(OUT / name / f"d{depth}", text, sup, w)
            pk, lag, res, _ = gp.score(t_si, si, r["t"], r["pad"], w)
            mk = np.interp(win, r["t"], r["kd"])
            frac = float(np.interp(rev + 0.02, r["t"], r["kd"])) if name == "shipped" else np.nan
            row = dict(case=depth, build=name, pk_pct=round(pk, 1), lag_ps=round(lag, 1),
                       kd_rms=round(float(np.sqrt(np.mean((mk - sk) ** 2))), 4),
                       kd_min=round(float(mk.min()), 4), si_kd_min=round(float(sk.min()), 4))
            line = f"    {depth:<7}{name:<11}{pk:>7.1f}{lag:>8.0f}{row['kd_rms']:>8.4f}{row['kd_min']:>8.3f}{row['si_kd_min']:>9.3f}{'':>9}"
            if args.variant == "io_buf":
                row["bump_mV"] = round(bump_mv(r["t"], r["pad"], rev), 1)
                row["si_bump_mV"] = round(bump_mv(t_si, si, rev), 1)
                line += f"{row['bump_mV']:>9.1f}{row['si_bump_mV']:>9.1f}"
            rows.append(row)
            print(line)
    with (OUT / "results.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wri.writeheader()
        wri.writerows(rows)
    print(f"\n  wrote {OUT / 'results.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
