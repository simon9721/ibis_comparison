#!/usr/bin/env python3
"""Two characterisation points: the single stressed pulse and a stressed train.

The one-point (pad-peak) calibration fixes the stage threshold and reproduces
the single-pulse regime, but the file-only chains were 9 % (ex2) / 23 %
(inv_chain) low on the settled pulses of a 50 % duty stressed train
(`NEXT_STEPS_FINDINGS.md` §12): a pulse that arrives before the stages have
returned to rest exercises the resistive fraction x_lin, which full swing does
not pin either. So: for each x_lin in a small set, refit the chain at full
swing, calibrate the threshold on the single pulse, run the train, and pick
the x_lin whose settled train peak matches. Then score all matrix widths.

    py -3.14 scripts/gate_chain_train_calib.py --variant ex2 --ccomp 1.7 --prior 0.57 0.64 --K 3
    py -3.14 scripts/gate_chain_train_calib.py --variant inv_chain --ccomp 0.6 --prior3 0.42 1.15 0.87 --K 7
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_cascade_prototype as gc  # noqa: E402
import gate_chain_prototype as gch  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402
import pulse_train_accumulation as pt  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402

R = ROOT / "results"
OUT = R / "gate_chain_train_calib_2026-09-10"
TRAIN_REF = R / "pulse_train_2026-09-08"


def run_train(d: Path, sub_text: str, sup: float, width: float, n: int):
    d.mkdir(parents=True, exist_ok=True)
    (d / "driver.sub").write_text(sub_text, encoding="utf-8")
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = sl.pulse(0.0, sup, pt.edges(width, n), edge_ps=gp.EDGE_PS.get(gp.VARIANT_NAME, 1.0), stop_ns=pt.stop_ns(width, n))
    deck = (dk.ngspice_header() + ".include driver.sub\n" + dk.supply("VCC", sup, name="Vdd")
            + f"Vin IN 0 {pwl}\n" + dk.supply("EN", sub.enable_level(sup), name="Ven")
            + sub.instance("X1") + dk.load("OUT", pt.R_LOAD, pt.C_LOAD_PF)
            + f".tran 0.002n {pt.stop_ns(width, n)}n\n.save V(OUT)\n.end\n")
    stamp = d / "driver.sub.used"
    fresh = (d / "run.raw").exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == sub_text
    if not fresh:
        (d / "run.sp").write_text(deck, encoding="utf-8")
        stamp.write_text(sub_text, encoding="utf-8")
        if sl.ngspice(d, timeout_s=1800) is None:
            raise RuntimeError(f"ngspice failed: {d}")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    return sl.time_ns(raw), sl.trace(raw, "out")


def per_pulse_aligned(t_si, si, t_m, m, width, n):
    """(peak shift ps, peak error mV, transistor peak V) per pulse, with the windows shifted by
    the transistor's own input-to-pad delay (its first pad peak), so a pad response that lands
    after the input period (inv_chain) is scored against its own pulse."""
    g0 = np.arange(5.0, 5.0 + 4 * width, 0.002)
    a0 = np.interp(g0, t_si, si)
    d0 = max(0.0, float(g0[int(np.argmax(a0))] - 5.0) - width / 2)
    rows = []
    for k in range(n):
        lo, hi = 5.0 + 2 * width * k + d0, 5.0 + 2 * width * (k + 1) + d0
        g = np.arange(lo, hi, 0.002)
        a, b = np.interp(g, t_si, si), np.interp(g, t_m, m)
        ia, ib = int(np.argmax(a)), int(np.argmax(b))
        rows.append(((g[ib] - g[ia]) * 1e3, (b[ib] - a[ia]) * 1e3, a[ia]))
    return rows


def settled_error(t_si, si, t_m, m, width, n):
    """settled peak error %, settled peak shift ps, pulse-1 peak error %, pulse-1 shift ps."""
    rows = per_pulse_aligned(t_si, si, t_m, m, width, n)
    # the last pulse's window runs past the end of the train, so its "peak" is the settle to the
    # rail: it scored +100 % on ex2 and +214 % on io_buf for the shipped model too (2026-09-23).
    # Averaging it moved the settled figure by 0.1-0.5 points in the runs checked; earlier
    # write-ups (09-10, 09-13) carry that.
    settled = rows[3:-1] if len(rows) > 4 else rows[3:]
    pk = float(np.mean([r[1] for r in settled]))          # mV
    ref = float(np.mean([r[2] for r in settled]))         # V
    shift = float(np.mean([r[0] for r in settled]))
    return 100.0 * pk / 1e3 / ref, shift, rows[0][1] / 1e3 / rows[0][2] * 100.0, rows[0][0]


def transistor_train_edge50(dev, sup, width, n):
    """The transistor train with the same 50 ps input edges as the matrix and the calibration
    (the 2026-09-08 reference used 1 ps edges, which on inv_chain's 1.4 V threshold changes the
    effective width by 28 ps). Cached under track2_train_check_2026-09-13/<dev>/transistor_edge50."""
    import re as _re
    import run_three_buffer_realistic_pulse_campaign as base
    from spice_tool_paths import default_hspice
    d = R / "track2_train_check_2026-09-13" / dev / "transistor_edge50"
    d.mkdir(parents=True, exist_ok=True)
    src = TRAIN_REF / dev / "stressed/transistor"
    for f in src.iterdir():
        if f.is_file() and not f.name.startswith("run."):
            (d / f.name).write_bytes(f.read_bytes())
    deck = (src / "run.sp").read_text(encoding="utf-8", errors="replace")
    pwl = sl.pulse(0.0, sup, pt.edges(width, n), edge_ps=50.0, stop_ns=pt.stop_ns(width, n))
    deck = _re.sub(r"Vin in_dig 0 PWL\(.*?\)", f"Vin in_dig 0 {pwl}", deck, flags=_re.S)
    (d / "run.sp").write_text(deck, encoding="utf-8")
    if not (d / "run.tr0").exists():
        if base.run_process([str(default_hspice()), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 1800) != 0:
            raise RuntimeError(f"hspice failed: {d}")
    raw = sl.parse_hspice_tr0(d / "run.tr0")
    return sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="ex2")
    ap.add_argument("--ccomp", type=float, default=None)
    ap.add_argument("--prior", type=float, nargs=2, default=None)
    ap.add_argument("--prior3", type=float, nargs=3, default=None)
    ap.add_argument("--K", type=int, required=True)
    ap.add_argument("--xlins", type=float, nargs="*", default=[0.25, 0.35, 0.45, 0.6, 0.8])
    ap.add_argument("--dn-ratios", type=float, nargs="*", default=[1.0], help="discharge-direction resistive fraction as a ratio of x_lin")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--sdn-scales", type=float, nargs="*", default=[1.0], help="scale the discharge rate s_dn after the full-swing fit (stage recovery between pulses)")
    args = ap.parse_args()
    dev = args.variant
    cc = args.ccomp
    sup, ibis = gp.VARIANTS[dev]
    gp.VARIANT_NAME = dev
    mdir = gch.G / (dev + (f"_c{cc:g}" if cc else ""))
    ship = (mdir / "shipped/driver.sub").read_text(encoding="utf-8")
    full_ship = gp.run_ours(mdir / "shipped/full", ship, sup, 10.0)
    if args.prior3:
        vt, al, gs = args.prior3
        gch.PRIOR_FN = lambda g: pm.prior3(g, vt, al, gs)
    else:
        vt, al = args.prior
        gch.PRIOR_FN = lambda g: pm.prior(g, vt, al)
    cs = gp.cases(dev)
    refs = {d_: gp.tr0_pad(d / "run.tr0") for d_, _, d in cs}
    depth, w_single, _ = cs[-1]
    width_train = pt.DEV[dev][2]
    gp.EDGE_PS[dev] = 50.0
    t_si, si = transistor_train_edge50(dev, sup, width_train, args.n)
    out = OUT / (dev + (f"_c{cc:g}" if cc else "") + "_edge50")
    out.mkdir(parents=True, exist_ok=True)
    rise, fall, kd_on, kd_off = gch.prior_maps(full_ship, vt, al)
    print(f"\n  {dev}: two-point calibration. single pulse d{depth} ({w_single*1e3:.0f} ps), train W {width_train*1e3:.0f} ps x {args.n}")
    print(f"    {'x_lin':>6}{'s_up':>7}{'s_dn':>7}{'vt (calib)':>11} | {'single pk%':>11}{'lag':>6} | {'train pulse1 %':>15}{'settled %':>10}{'settled lag':>12}")
    rows = []
    best = None
    for xl, ratio, sdn in [(x, r_, s_) for x in args.xlins for r_ in args.dn_ratios for s_ in args.sdn_scales]:
        cl.XLIN_DN_RATIO = ratio
        gch.XLIN_DN_RATIO = ratio
        fits = gch.fit_chain_ku(full_ship, vt, al, [args.K], x_lin_fixed=xl)
        c, prm = fits[args.K]
        prm = (prm[0], prm[1] * sdn, prm[2], prm[3], prm[4])
        tagx = f"xlin{xl:g}" + (f"_dn{ratio:g}" if ratio != 1.0 else "") + (f"_sdn{sdn:g}" if sdn != 1.0 else "")
        prm = gch.calibrate_pad(ship, args.K, prm, None, sup, (rise, fall, kd_on, kd_off), refs[depth], w_single, out / tagx / "calib", f"x_lin {xl:g} dn {ratio:g}")
        text = gc.patch_kd_maps(gc.patch_maps(gch.patch_chain(ship, args.K, prm, None, sup), rise, fall), kd_on, kd_off)
        r = gp.run_ours(out / tagx / f"d{depth}", text, sup, w_single)
        pk1, lag1, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w_single)
        t_m, m = run_train(out / tagx / "train", text, sup, width_train, args.n)
        se, slag, p1, p1lag = settled_error(t_si, si, t_m, m, width_train, args.n)
        print(f"    {xl:>6.2f}/{ratio:<4g}/{sdn:<4g}{prm[0]:>7.2f}{prm[1]:>7.2f}{prm[2]:>11.3f} | {pk1:>11.1f}{lag1:>6.0f} | {p1:>15.1f}{se:>10.1f}{slag:>12.0f}")
        rows.append(dict(x_lin=f"{xl}/{ratio}", s_up=round(prm[0], 3), s_dn=round(prm[1], 3), vt=round(prm[2], 3), single_pk=round(pk1, 1), single_lag=round(lag1),
                         train_pulse1_pk=round(p1, 1), train_settled_pk=round(se, 1), train_settled_lag=round(slag)))
        (out / tagx / "driver_chain.sub").write_text(text, encoding="utf-8")
        if best is None or abs(se) + abs(slag) / 20.0 < abs(best[0]) + abs(best[3]) / 20.0:
            best = (se, xl, text, slag, ratio, sdn)
    se, xl, text, slag, ratio, sdn = best
    cl.XLIN_DN_RATIO = ratio
    gch.XLIN_DN_RATIO = ratio
    print(f"\n    -> x_lin {xl:g} / dn {ratio:g} (settled train {se:+.1f} %, lag {slag:.0f} ps; score = |peak %| + |lag ps|/20). All matrix widths with that build:")
    print(f"    {'build':<14} | " + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs) + " | " + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs))
    tagb = f"xlin{xl:g}" + (f"_dn{ratio:g}" if ratio != 1.0 else "") + (f"_sdn{sdn:g}" if sdn != 1.0 else "")
    for name, txt, d0 in (("shipped", ship, mdir / "shipped"), (f"two-point x{xl:g}/{ratio:g}", text, out / tagb)):
        pks, lags = [], []
        for dp, w, _ in cs:
            r = gp.run_ours(d0 / f"d{dp}", txt, sup, w)
            pk, lag, _, _ = gp.score(*refs[dp], r["t"], r["pad"], w)
            pks.append(pk)
            lags.append(lag)
        print(f"    {name:<14} | " + "".join(f"{x:>9.1f}" for x in pks) + " | " + "".join(f"{x:>9.0f}" for x in lags))
        rows.append(dict(x_lin=name, **{f"pk_d{dp}": round(x, 1) for (dp, _, _), x in zip(cs, pks)}, **{f"lag_d{dp}": round(x) for (dp, _, _), x in zip(cs, lags)}))
    keys = []
    for r_ in rows:
        for k in r_:
            if k not in keys:
                keys.append(k)
    with (out / "sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=keys)
        wri.writeheader()
        wri.writerows(rows)
    print(f"  wrote {out / 'sweep.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
