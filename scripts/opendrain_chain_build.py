#!/usr/bin/env python3
"""Open-drain: the current-limited-chain recipe on the pull-down gate.

The converter now builds the gate-state model for `Model_type Open_drain`
(`subcircuit.open_drain_tables_as_push_pull`): one predriver, one device, the
pull-down gate GDN with its Kd map. That build rests in the right state and
tracks depth partly, but like every gate-state build it drives the gate from a
delay plus an RC, so under a short LOW pulse the pull-down is still far more
"on" than the transistor's (`opendrain_gatestate_2026-09-10`).

This applies the push-pull recipe of `build_chain_model.py` to the open-drain:

    1. the converter's open-drain gate-state model
    2. its full-swing gate-part Kd(t)
    3. K identical current-limited stages fitted so that Kd = PRIOR(1 - chain)
       reproduces it (Kd domain: a Ku-domain fit through the mirrored placeholder
       leaves the pull-down onset unconstrained and lands 250 ps early). The
       prior is the NMOS map measured in `opendrain_silicon_map.py` (threshold
       ~0.2 of the gate swing, not the pull-up's 0.52); K on the 5 % plateau or
       --K; x_lin 0.45; C_comp from the loop (3.0 pF), not the declared 5.0
    4. one stressed transistor PAD run on the open-drain bench (50 ohm to VCC,
       2 pF, short LOW pulse): bisect the stage threshold until the model's low
       excursion matches, else scale the drive
    5. score every width of the open-drain matrix against the transistor and
       native, next to the legacy build and the plain gate-state build

    py -3.14 scripts/opendrain_chain_build.py --variant base --ccomp 3.0 --prior3 0.20 1.30 0.88 --calib-width 0.68 --tag _odprior
    py -3.14 scripts/opendrain_chain_build.py --variant od_weak --ccomp 3.0 --prior3 0.23 1.15 0.92 --K 3 --calib-width 0.68 --tag _odprior_K3
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit, chain_command as cc  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_chain_prototype as gch  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402

R = ROOT / "results"
GATESTATE = R / "opendrain_gatestate_2026-09-10"
OUT = R / "opendrain_chain_2026-09-10"
SUP, R_PU, C_LOAD_PF, STOP = 3.3, 50.0, 2.0, 22.0
FAMILY_PRIOR = {"ex2": (0.52, 1.10, 0.91)}
VARIANTS = {
    "base": (R / "ex2_variants_2026-09-03/opendrain/ibis/ex2_opendrain.ibs",
             R / "ex2_variants_2026-09-03/opendrain/inputs",
             [10.0, 0.75, 0.72, 0.70, 0.68, 0.66, 0.64, 0.62], R / "opendrain_stress_2026-09-08"),
    "od_weak": (R / "s2ibispy_parameter_selection_ex2_od_weak_2026-09-02/probe/ex2_od_weak_probe.ibs",
                R / "ex2_variants_2026-09-03/od_weak/inputs",
                [10.0, 0.75, 0.72, 0.70, 0.68, 0.66, 0.64, 0.62], R / "opendrain_stress_od_weak_2026-09-08"),
    "od_slowpre": (R / "s2ibispy_parameter_selection_ex2_od_slowpre_2026-09-02/probe/ex2_od_slowpre_probe.ibs",
                   R / "ex2_variants_2026-09-03/od_slowpre/inputs",
                   [10.0, 1.0, 0.94, 0.88, 0.84, 0.80, 0.77, 0.75], R / "opendrain_stress_od_slowpre_2026-09-08"),
}


def wdir(width: float) -> str:
    return f"w{width * 1e3:.0f}ps"


def low_pulse(width: float) -> str:
    return sl.pulse(0.0, SUP, [5.0, 5.0 + width], start_high=True, stop_ns=STOP)


def run_od(d: Path, sub_text: str, width: float):
    """The open-drain bench in ngspice for one driver text. Cached on the text."""
    d.mkdir(parents=True, exist_ok=True)
    (d / "driver.sub").write_text(sub_text, encoding="utf-8")
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    deck = (dk.ngspice_header() + ".include driver.sub\n" + dk.supply("VCC", SUP, name="Vdd")
            + f"Vin IN 0 {low_pulse(width)}\n" + dk.supply("EN", sub.enable_level(SUP), name="Ven")
            + sub.instance("X1") + f"Rpu OUT VCC {R_PU}\nCload OUT 0 {C_LOAD_PF}p\n"
            + f".tran 0.002n {STOP}n\n.save V(OUT) V(X1.kd) V(X1.gdn)\n.end\n")
    stamp = d / "driver.sub.used"
    fresh = (d / "run.raw").exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == sub_text
    if not fresh:
        (d / "run.sp").write_text(deck, encoding="utf-8")
        stamp.write_text(sub_text, encoding="utf-8")
        if sl.ngspice(d, timeout_s=1800) is None:
            raise RuntimeError(f"ngspice failed: {d}")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    return sl.time_ns(raw), sl.trace(raw, "out")


def transistor_pad(variant: str, width: float):
    tr0 = GATESTATE / variant / wdir(width) / "transistor" / "run.tr0"
    raw = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float)


def excursion_error(t_si, si, t_m, m, width, settled_low):
    """Model low excursion minus the transistor's, as % of the transistor's excursion at this width,
    and the model's low-excursion error in mV (the bench's number)."""
    g = np.arange(4.5, min(5.0 + 2 * width + 3.0, STOP - 0.1), 0.002)
    a, b = np.interp(g, t_si, si), np.interp(g, t_m, m)
    exc_si, exc_m = SUP - a.min(), SUP - b.min()
    return 100.0 * (exc_m - exc_si) / exc_si, (b.min() - a.min()) * 1e3, (SUP - a.min()) / (SUP - settled_low)


def calibrate_od(ship, K, prm, maps_args, variant, width, workdir):
    """Bisection on the stage threshold against the transistor's low excursion at `width`."""
    t_si, si = transistor_pad(variant, width)
    t10, s10 = transistor_pad(variant, 10.0)
    settled = float(np.interp(14.5, t10, s10))

    def build(prm_):
        return cc.patch_prior_maps(cc.patch_chain(ship, K, prm_, SUP), *maps_args)

    def err(prm_, i):
        t_m, m = run_od(workdir / f"it{i:02d}", build(prm_), width)
        return excursion_error(t_si, si, t_m, m, width, settled)[0]

    # The stage rate is h(x) = ((x - vt) / (1 - vt))^p, so the excursion is not
    # monotone in vt over [0, 0.7]: lowering vt below the fitted value slows the
    # stages (the normalisation grows) as much as it opens them earlier. Bracket
    # from the fitted threshold toward the side the sign asks for; the push-pull
    # recipe bracketed [0, 0.7] and happened to be monotone there.
    e0 = err(prm, 0)
    vt0 = prm[2]
    if e0 > 0:
        e_hi = err((prm[0], prm[1], 0.7, prm[3], prm[4]), 1)
        lo, hi, e_lo = vt0, 0.7, e0
    else:
        e_lo = err((prm[0], prm[1], 0.0, prm[3], prm[4]), 1)
        lo, hi, e_hi = 0.0, vt0, e0
    print(f"    calibration at W = {width * 1e3:.0f} ps: excursion error {e0:+.1f} % with vt {vt0:.3f}; bracket vt {lo:.3f} -> {e_lo:+.1f} %, vt {hi:.3f} -> {e_hi:+.1f} %")
    it = 2
    if e_lo >= 0 >= e_hi:
        for _ in range(7):
            mid = 0.5 * (lo + hi)
            if err((prm[0], prm[1], mid, prm[3], prm[4]), it) > 0:
                lo = mid
            else:
                hi = mid
            it += 1
        prm = (prm[0], prm[1], 0.5 * (lo + hi), prm[3], prm[4])
        print(f"    -> threshold vt {prm[2]:.3f}")
        return prm
    lo, hi = 0.5, 2.0
    for _ in range(7):
        mid = 0.5 * (lo + hi)
        if err((prm[0] * mid, prm[1] * mid, prm[2], prm[3], prm[4]), it) < 0:
            lo = mid
        else:
            hi = mid
        it += 1
    kc = 0.5 * (lo + hi)
    print(f"    -> drive scale {kc:.3f}")
    return (prm[0] * kc, prm[1] * kc, prm[2], prm[3], prm[4])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS), default="base")
    ap.add_argument("--ccomp", type=float, default=None, help="override C_comp (pF); default: the file's declared value")
    ap.add_argument("--K", type=int, default=None)
    ap.add_argument("--Ks", type=int, nargs="*", default=[2, 3, 4])
    ap.add_argument("--fix-xlin", type=float, default=0.45)
    ap.add_argument("--prior3", type=float, nargs=3, default=None)
    ap.add_argument("--calib-width", type=float, default=None, help="pulse width (ns) of the one stressed transistor run; default: none")
    ap.add_argument("--fit", choices=("kd_map", "ku"), default="kd_map",
                    help="fit the chain so that Kd = prior(1 - g) reproduces the tables' Kd(t) (default), or the mirrored Ku(t)")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    ibis, inputs, widths, legacy_dir = VARIANTS[args.variant]
    tag = (args.variant + (f"_c{args.ccomp:g}" if args.ccomp else "") + (f"_calib{args.calib_width * 1e3:.0f}" if args.calib_width else "")
           + ("" if args.fit == "kd_map" else f"_{args.fit}") + args.tag)
    out = OUT / tag
    work = out / "build"
    work.mkdir(parents=True, exist_ok=True)
    if args.ccomp:
        txt = re.sub(r"^C_comp\s+.*$", f"C_comp {args.ccomp:.4f}pF {args.ccomp:.4f}pF {args.ccomp:.4f}pF",
                     ibis.read_text(errors="ignore"), count=1, flags=re.M)
        ibis_used = work / "input_ccomp.ibs"
        ibis_used.write_text(txt, encoding="utf-8")
    else:
        ibis_used = ibis
    model, comp = gp.ibis_names(ibis_used)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis_used)), model_name=model, component_name=comp)
    subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(work / "driver_shipped.sub"))
    ship = (work / "driver_shipped.sub").read_text(encoding="utf-8")
    assert "Open-drain: pull-down gate GDN" in ship, "converter did not take the open-drain gate-state path"
    gp.VARIANT_NAME = "__od__"
    gp.EDGE_PS["__od__"] = 1.0
    full_ship = gp.run_ours(work / "full", ship, SUP, 10.0)

    vt, al, gs = args.prior3 or FAMILY_PRIOR["ex2"]
    gch.PRIOR_FN = lambda g: pm.prior3(g, vt, al, gs)
    Ks = [args.K] if args.K else args.Ks
    print(f"  {args.variant}: prior3 vt={vt} alpha={al} gs={gs}; chain fit in the {'Kd' if args.fit == 'kd_map' else '(mirrored) Ku'} domain:")
    fits = gch.fit_chain_ku(full_ship, vt, al, Ks, which=args.fit, x_lin_fixed=args.fix_xlin)
    K = args.K or gch.pick_K(fits)
    c, prm = fits[K]
    print(f"  -> K = {K}: s_up {prm[0]:.3f} s_dn {prm[1]:.3f} vt {prm[2]:.3f} x_lin {prm[3]:.3f} (full-swing rms {c:.4f})")
    tf, kb, kd = full_ship["t"], full_ship["kugate_base"], full_ship["kdgate_base"]
    maps_args = (float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb)),
                 float(np.interp(4.5, tf, kd)), float(np.interp(12.0, tf, kd)), gch.PRIOR_FN)
    if args.calib_width:
        prm = calibrate_od(ship, K, prm, maps_args, args.variant, args.calib_width, work / "calib")
    text = cc.patch_prior_maps(cc.patch_chain(ship, K, prm, SUP), *maps_args)
    (out / "driver_chain.sub").write_text(text, encoding="utf-8")

    # score every width: chain vs transistor and native; legacy and gate-state numbers from their case files
    def cases(p):
        with p.open(encoding="utf-8") as fh:
            return {float(r["width_ns"]): r for r in csv.DictReader(fh)}
    legacy = cases(legacy_dir / "cases.csv")
    gstate = cases(GATESTATE / args.variant / "cases.csv")
    t10, s10 = transistor_pad(args.variant, 10.0)
    settled = float(np.interp(14.5, t10, s10))
    rows = []
    print(f"\n  {'W (ps)':>7} {'depth %':>8} | {'legacy mV':>10} {'gate-state':>10} {'chain':>8} | {'native':>8} | {'Kd@min si':>9} {'chain':>6} | excursion % chain")
    for W in widths:
        t_si, si = transistor_pad(args.variant, W)
        t_m, m = run_od(out / wdir(W), text, W)
        pct, mv, depth = excursion_error(t_si, si, t_m, m, W, settled)
        raw = sl.parse_ngspice_raw(out / wdir(W) / "run.raw")
        kd_m = sl.signal(raw, "v(x1.kd)")
        g = np.arange(4.5, min(5.0 + 2 * W + 3.0, STOP - 0.1), 0.002)
        tmin = g[int(np.argmin(np.interp(g, t_si, si)))]
        kd_at_min = float(np.interp(tmin, t_m, kd_m))
        lg, gs_ = legacy[W], gstate[W]
        rows.append(dict(width_ns=W, depth_pct=round(100 * depth, 1), legacy_low_err_mV=float(lg["our_low_err_mV"]),
                         gatestate_low_err_mV=float(gs_["our_low_err_mV"]), chain_low_err_mV=round(mv, 1),
                         native_low_err_mV=float(gs_["nat_low_err_mV"]), si_kd_at_min=float(gs_["si_kd_at_min"]),
                         gatestate_kd_at_min=float(gs_["our_kd_at_min"]), chain_kd_at_min=round(kd_at_min, 3),
                         chain_excursion_err_pct=round(pct, 1)))
        print(f"  {W * 1e3:7.0f} {100 * depth:8.1f} | {float(lg['our_low_err_mV']):10.0f} {float(gs_['our_low_err_mV']):10.0f} {mv:8.0f} | {float(gs_['nat_low_err_mV']):8.0f} | {float(gs_['si_kd_at_min']):9.2f} {kd_at_min:6.2f} | {pct:+.1f}")
    with (out / "cases.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (out / "params.txt").write_text(f"K={K} s_up={prm[0]:.6g} s_dn={prm[1]:.6g} vt={prm[2]:.6g} x_lin={prm[3]:.6g} prior3={vt},{al},{gs} ccomp={args.ccomp} calib_width={args.calib_width}\n", encoding="utf-8")

    # figure: pad per width, four traces
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 4, figsize=(20, 9))
    for i, W in enumerate(widths):
        a = axes.ravel()[i]
        t_si, si = transistor_pad(args.variant, W)
        nat = sl.parse_hspice_tr0(GATESTATE / args.variant / wdir(W) / "native" / "run.tr0")
        t_n, vn = sl.time_ns(nat), np.asarray(nat["v(pad)"], float)
        gsr = sl.parse_ngspice_raw(GATESTATE / args.variant / wdir(W) / "ours" / "run.raw")
        t_g, vg = sl.time_ns(gsr), sl.trace(gsr, "out")
        t_m, m = run_od(out / wdir(W), text, W)
        g = np.arange(4.8, min(5.0 + W + 2.5, STOP - 0.1), 0.002)
        a.plot(g - 5.0, np.interp(g, t_si, si), color="#111111", lw=3.0, label="transistor")
        a.plot(g - 5.0, np.interp(g, t_n, vn), color="#2B6CA3", lw=1.6, label="native HSPICE IBIS")
        a.plot(g - 5.0, np.interp(g, t_g, vg), color="#999999", lw=1.4, ls=":", label="ours, gate-state (no chain)")
        a.plot(g - 5.0, np.interp(g, t_m, m), color="#2E7D4F", lw=2.0, ls="--", label=f"ours, chain K={K}")
        a.set_title(f"W = {W * 1e3:.0f} ps, depth {rows[i]['depth_pct']:.0f} %", fontsize=11, fontweight="bold")
        a.set_xlabel("time from pull-down (ns)")
        a.grid(alpha=0.3)
        if i == 0:
            a.legend(fontsize=8)
            a.set_ylabel("pad (V)")
    fig.suptitle(f"Open-drain {args.variant}: short low pulses into 50 ohm to VCC, chain command on the pull-down gate ({tag})",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "opendrain_chain.png", dpi=160)
    plt.close(fig)
    print(f"\n  wrote {out / 'cases.csv'}, {out / 'opendrain_chain.png'}, {out / 'driver_chain.sub'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
