#!/usr/bin/env python3
"""The command layer as K identical current-limited stages, built in ngspice and scored on the pad.

The recipe from `current_limited_stages_2026-09-10` and `physics_map_gate_2026-09-10`:

  1. a target gate step response  (--source real: the transistor's own node;
                                    --source ibis: the tables' Ku(t) inverted through the map prior)
  2. K identical current-limited stages fitted to it at full swing (K from the
     rms plateau, or given)
  3. the chain replaces the T-line command + RC gate; GUP = its last stage,
     GDN = 1 - GUP (one inverter drives both halves on ex2 / inv_chain)
  4. maps on the last stage: --maps ibis   (re-derived from the shipped full-swing
                                            gate-part K(t) against the new gate)
                             --maps prior  (the MOSFET-shaped prior, vt / alpha)
                             --maps silicon(the transistor's Ku/Kd against its gate)

Scored on the matrix stressed widths (peak % and lag vs the transistor) and on
the full-swing pad. `--source real --maps silicon` is the truth-bounded build
(everything the model could know if it saw the transistor); `--source ibis
--maps prior` is the file-only recipe.

    py -3.14 scripts/gate_chain_prototype.py --variant ex2 --ccomp 1.7 --source real --maps silicon
    py -3.14 scripts/gate_chain_prototype.py --variant ex2 --ccomp 1.7 --source ibis --maps prior
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

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_cascade_prototype as gc  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import shared_gate_prototype as sg  # noqa: E402
import silicon_map_replay as smr  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402

R = ROOT / "results"
G = R / "gate_cascade_prototype_2026-09-09"
OUT = R / "gate_chain_prototype_2026-09-10"
LOOP_CC = {"ex2": 1.75, "inv_chain": 0.6, "io_buf": None}
FSFIX = {"ex2": smr.FSFIX / "ex2", "inv_chain": smr.FSFIX / "inv_chain", "io_buf": R / "full_swing_silicon_kukd_2026-09-07"}
DEADBAND = 0.005
PRIOR_FN = None          # set in main: g -> Ku on [0, 1]
XLIN_DN_RATIO = 1.0      # discharge-direction resistive fraction = x_lin * ratio


def stage_block(K, s_up, s_dn, vt, x_lin, p=1.0, pre="STG") -> str:
    """K identical current-limited stages from CHIN to <pre><K>; rates in 1/ns."""
    lines = [f"* --- current-limited command chain {pre}: K identical stages (fitted at full swing) ---"]
    for k in range(1, K + 1):
        u = "V(CHIN)" if k == 1 else f"V({pre}{k - 1})"
        v = f"V({pre}{k})"
        hu = f"pow(max(min(({u} - {vt:.6g}) / {1 - vt:.6g}, 1), 0), {p:g})"
        hd = f"pow(max(min((1 - {u} - {vt:.6g}) / {1 - vt:.6g}, 1), 0), {p:g})"
        ru = f"min(1, (1 - {v}) / {x_lin:.6g})"
        rd = f"min(1, {v} / {x_lin * XLIN_DN_RATIO:.6g})"
        lines.append(f"B{pre}{k} {pre}{k} 0 I = -{{gate_c}} * 1e9 * ({s_up:.6g} * {hu} * {ru} - {s_dn:.6g} * {hd} * {rd})")
        lines.append(f"C{pre}{k} {pre}{k} 0 {{gate_c}} ic=0")
        lines.append(f"R{pre}{k} {pre}{k} 0 1e12")
    if pre == "STG":
        lines.append(f"BGUP GUP 0 V = min(max(V(STG{K}), 0), 1)")
    else:
        lines.append(f"BGDN GDN 0 V = 1.0 - min(max(V({pre}{K}), 0), 1)")
    return "\n".join(lines)


def patch_chain(sub: str, K, prm, gdn=None, sup=3.3) -> str:
    """gdn = (K_d, prm_d): a second chain drives GDN (io_buf: two predriver paths); else GDN = 1 - GUP.

    The chain input is its own mid-supply comparator on IN. The sub's NINX uses
    (Vinh + Vinl) / 2 from the IBIS file, which for inv_chain is 1.4 V on a 1.8 V
    part (Vinh is declared 2.0 V), so NINX sees every 50 ps-edge pulse ~30 ps
    narrower than the transistor's first inverter does.
    """
    s_up, s_dn, vt, x_lin, p = prm
    chin = f"BCHIN CHIN 0 V = (V(IN,VSS) > {0.5 * sup:.4g}) ? 1.0 : 0.0\n"
    s = re.sub(r"^BGUP GUP 0 I = .*$", chin + stage_block(K, s_up, s_dn, vt, x_lin, p), sub, count=1, flags=re.M)
    s = re.sub(r"^CGUP GUP 0 .*\n", "", s, count=1, flags=re.M)
    s = re.sub(r"^RGUP GUP 0 .*\n", "", s, count=1, flags=re.M)
    tgt = "V(CHIN)" if K == 1 else f"V(STG{K - 1})"
    s = re.sub(r"^BGUPTARGET GUPTARGET 0 V = .*$", f"BGUPTARGET GUPTARGET 0 V = min(max({tgt}, 0), 1)", s, count=1, flags=re.M)
    if gdn is None:
        s = sg.patch_shared(s)
    else:
        Kd, pd = gdn
        s = re.sub(r"^BGDN GDN 0 I = .*$", stage_block(Kd, pd[0], pd[1], pd[2], pd[3], pd[4], pre="STGD"), s, count=1, flags=re.M)
        s = re.sub(r"^CGDN GDN 0 .*\n", "", s, count=1, flags=re.M)
        s = re.sub(r"^BGDNBASE GDNBASE 0 .*\n", "", s, count=1, flags=re.M)
        s = re.sub(r"^RGDN GDN GDNBASE .*\n", "", s, count=1, flags=re.M)
        tgd = "V(CHIN)" if Kd == 1 else f"V(STGD{Kd - 1})"
        s = re.sub(r"^BGDNTARGET GDNTARGET 0 V = .*$", f"BGDNTARGET GDNTARGET 0 V = 1.0 - min(max({tgd}, 0), 1)", s, count=1, flags=re.M)
    s = re.sub(r"^BKUGATE_BASE KUGATE_BASE 0 V = .*$",
               f"BKUGATE_BASE KUGATE_BASE 0 V = (V(GUPTARGET) >= V(GUP) - {DEADBAND}) ? V(KUGATE_ON) : V(KUGATE_OFF)", s, count=1, flags=re.M)
    s = re.sub(r"^BKDGATE_BASE KDGATE_BASE 0 V = .*$",
               f"BKDGATE_BASE KDGATE_BASE 0 V = (V(GDNTARGET) >= V(GDN) - {DEADBAND}) ? V(KDGATE_ON) : V(KDGATE_OFF)", s, count=1, flags=re.M)
    assert "BSTG1" in s and "BGUP GUP 0 V" in s
    return s


def target_gate(dev, source, full_ship, vt, al):
    """(t, g) full-swing gate step responses on the model's time base."""
    if source == "real":
        return gr.real_gate(dev, 0, gr.GATES[dev][0])
    tf, kb = full_ship["t"], full_ship["kugate_base"]
    k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
    kuf = np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0)
    g = pm.below_threshold(tf, pm.invert(kuf, vt, al), kuf, vt)
    return tf, g


def target_gdn_gate(dev, source, full_ship, vt, al):
    """The pull-down predriver's step response as a rising 0..1 trace (1 = pull-down off)."""
    if source == "real":
        return gr.real_gate(dev, 0, gr.GATES[dev][1])
    tf, kd = full_ship["t"], full_ship["kdgate_base"]
    d_on, d_off = float(np.interp(4.5, tf, kd)), float(np.interp(12.0, tf, kd))
    kdn = np.clip((d_on - kd) / (d_on - d_off), 0.0, 1.0)
    return tf, pm.below_threshold(tf, pm.invert(kdn, vt, al), kdn, vt)


def t_on():
    """The chain input switches at the mid-crossing of the input edge (50 ps on the matrix decks, 1 ps on variants)."""
    return 5.0 + gp.EDGE_PS.get(gp.VARIANT_NAME, 1.0) / 2000.0


def fit_chain_to(t, g, Ks, x_lin_fixed=None):
    """K identical stages on the DT grid, input = the digital step at the edge midpoints."""
    grid = np.arange(4.0, 21.0, cl.DT)
    u = ((grid >= t_on()) & (grid < t_on() + 10.0)).astype(float)
    v = np.interp(grid, t, g)
    fits = {}
    for K in Ks:
        c, prms = cl.fit_chain_shared(u, v, K, x_lin_fixed=x_lin_fixed)
        fits[K] = (c, prms[0])
        print(f"      K={K}: rms {c:.4f}  s_up {prms[0][0]:.2f} s_dn {prms[0][1]:.2f} vt {prms[0][2]:.2f} x_lin {prms[0][3]:.2f}")
    return fits, grid, u, v


def fit_chain_ku(full_ship, vt, al, Ks, which="ku", x_lin_fixed=None):
    """File-only route: fit K identical stages so that prior(chain output) reproduces the
    tables' full-swing gate-part Ku(t) (or, for the pull-down, the mirrored Kd(t)). No
    inversion of the prior where it is poorly conditioned; the sub-threshold part of the
    chain is constrained only by the identical-stage structure."""
    grid = np.arange(4.0, 21.0, cl.DT)
    u = ((grid >= t_on()) & (grid < t_on() + 10.0)).astype(float)
    tf = full_ship["t"]
    if which == "ku":
        kb = full_ship["kugate_base"]
        k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
        target = np.interp(grid, tf, np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0))
    else:
        kd = full_ship["kdgate_base"]
        d_on, d_off = float(np.interp(4.5, tf, kd)), float(np.interp(12.0, tf, kd))
        target = np.interp(grid, tf, np.clip((d_on - kd) / (d_on - d_off), 0.0, 1.0))
    fits = {}
    for K in Ks:
        best = (9.0, None)

        def unpack(z):
            return np.exp(z[0]), np.exp(z[1]), z[2], (x_lin_fixed if x_lin_fixed is not None else z[3])

        def cost(z):
            s_up, s_dn, vtt, x_lin = unpack(z)
            if not (0.0 <= vtt <= 0.7 and 0.02 <= x_lin <= 1.5):
                return 9.0
            g = cl.simulate_chain(u, [(s_up, s_dn, vtt, x_lin, 1.0)] * K)
            return float(np.sqrt(np.mean((PRIOR_FN(g) - target) ** 2)))

        n = 3 if x_lin_fixed is not None else 4
        for s0 in (2.0, 8.0, 30.0):
            z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4][:n]), step=[0.7, 0.7, 0.15, 0.15][:n], maxiter=800)
            if c < best[0]:
                s_up, s_dn, vtt, x_lin = unpack(z)
                best = (c, (float(s_up), float(s_dn), float(vtt), float(x_lin), 1.0))
        fits[K] = best
        print(f"      K={K}: Ku-domain rms {best[0]:.4f}  s_up {best[1][0]:.2f} s_dn {best[1][1]:.2f} vt {best[1][2]:.2f} x_lin {best[1][3]:.2f}")
    return fits


def pick_K(fits):
    """Smallest K on the rms plateau (within 5 % of the best)."""
    best = min(c for c, _ in fits.values())
    for K in sorted(fits):
        if fits[K][0] <= 1.05 * best + 1e-4:
            return K
    return max(fits)


def prior_maps(full_ship, vt, al):
    tf, kb = full_ship["t"], full_ship["kugate_base"]
    k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
    kd = full_ship["kdgate_base"]
    d_off, d_on = float(np.interp(12.0, tf, kd)), float(np.interp(4.5, tf, kd))
    grid = np.linspace(0.0, 1.0, 200)
    ku = k_rest + (k_on - k_rest) * PRIOR_FN(grid)
    kdm = d_off + (d_on - d_off) * PRIOR_FN(grid)
    return (grid, ku), (grid, ku), (grid, kdm), (grid, kdm)


def silicon_maps_for(dev, data, sup, cc):
    lo, hi = smr.fixture(FSFIX[dev] / "vfix_0/run.tr0"), smr.fixture(FSFIX[dev] / "vfix_vcc/run.tr0")
    if cc:
        data.c_comp = [cc * 1e-12] * 3
    s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
    tg, g = gr.real_gate(dev, 0, gr.GATES[dev][0])
    gd = None if gr.GATES[dev][1] is None else 1.0 - np.interp(tg, *gr.real_gate(dev, 0, gr.GATES[dev][1]))
    return smr.silicon_maps(s[:, 0] * 1e9, s[:, 1], s[:, 2], tg, g, 5.0, 15.0, gd)


def calibrate(prm, K, Wc, gmax):
    """One stressed observation: the gate maximum at width Wc (ps). Move the stage
    threshold (the drive law under a partial input, invisible at full swing) until
    the python chain reproduces it; if the threshold cannot reach it, scale both
    drives. The other full-swing numbers stay."""
    grid_c = np.arange(4.0, 5.0 + Wc / 1e3 + 3.0, cl.DT)
    u_c = ((grid_c >= t_on()) & (grid_c < t_on() + Wc / 1e3)).astype(float)

    def gate_max(vt_):
        return float(cl.simulate_chain(u_c, [(prm[0], prm[1], vt_, prm[3], prm[4])] * K).max())

    g_before = gate_max(prm[2])
    if gate_max(0.0) >= gmax >= gate_max(0.7):
        lo, hi = 0.0, 0.7
        for _ in range(24):
            mid = 0.5 * (lo + hi)
            if gate_max(mid) > gmax:
                lo = mid
            else:
                hi = mid
        vt_c = 0.5 * (lo + hi)
        out = (prm[0], prm[1], vt_c, prm[3], prm[4])
        print(f"    calibration: gate max at {Wc:g} ps = {g_before:.3f}; target {gmax:.3f} -> threshold vt {vt_c:.3f} (gives {gate_max(vt_c):.3f})")
        return out

    def gate_max_s(k):
        return float(cl.simulate_chain(u_c, [(prm[0] * k, prm[1] * k, prm[2], prm[3], prm[4])] * K).max())

    lo, hi = 0.3, 4.0
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        if gate_max_s(mid) < gmax:
            lo = mid
        else:
            hi = mid
    kc = 0.5 * (lo + hi)
    print(f"    calibration: gate max at {Wc:g} ps = {g_before:.3f}; target {gmax:.3f} out of the threshold's reach -> drive scale {kc:.3f} (gives {gate_max_s(kc):.3f})")
    return (prm[0] * kc, prm[1] * kc, prm[2], prm[3], prm[4])


def calibrate_pad(ship, K, prm, gdn, sup, maps, ref, w, workdir, label=""):
    """One stressed transistor run of the PAD (ref = (t_ns, v) at width w ns) is the
    target: bisect the stage threshold in ngspice until the model's peak matches;
    if the threshold cannot bracket it, scale both drives. Returns the new prm."""
    rise, fall, kd_on, kd_off = maps

    def build(prm_):
        return gc.patch_kd_maps(gc.patch_maps(patch_chain(ship, K, prm_, gdn, sup), rise, fall), kd_on, kd_off)

    def pad_err(prm_, i):
        r = gp.run_ours(workdir / f"it{i:02d}", build(prm_), sup, w)
        return gp.score(ref[0], ref[1], r["t"], r["pad"], w)[0]

    e0 = pad_err(prm, 0)
    e_lo = pad_err((prm[0], prm[1], 0.0, prm[3], prm[4]), 1)
    e_hi = pad_err((prm[0], prm[1], 0.7, prm[3], prm[4]), 2)
    print(f"    pad calibration {label}: peak error {e0:+.1f} % with vt {prm[2]:.3f}; vt 0 -> {e_lo:+.1f} %, vt 0.7 -> {e_hi:+.1f} %")
    it = 3
    if e_lo >= 0 >= e_hi:
        lo, hi = 0.0, 0.7
        for _ in range(7):
            mid = 0.5 * (lo + hi)
            if pad_err((prm[0], prm[1], mid, prm[3], prm[4]), it) > 0:
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
        if pad_err((prm[0] * mid, prm[1] * mid, prm[2], prm[3], prm[4]), it) < 0:
            lo = mid
        else:
            hi = mid
        it += 1
    kc = 0.5 * (lo + hi)
    print(f"    -> drive scale {kc:.3f}")
    return (prm[0] * kc, prm[1] * kc, prm[2], prm[3], prm[4])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="ex2")
    ap.add_argument("--ccomp", type=float, default=None)
    ap.add_argument("--source", choices=("real", "ibis"), default="real")
    ap.add_argument("--maps", choices=("ibis", "prior", "silicon"), default="silicon")
    ap.add_argument("--K", type=int, default=None, help="stage count; default: smallest K on the rms plateau over --Ks")
    ap.add_argument("--Ks", type=int, nargs="*", default=None)
    ap.add_argument("--fix-xlin", type=float, default=None, help="fix the resistive fraction of every stage (physics: ~0.45) so the fit has 3 numbers")
    ap.add_argument("--prior", type=float, nargs=2, default=None, metavar=("VT", "ALPHA"),
                    help="map prior; default: fitted to this device's silicon map (needs the fixtures)")
    ap.add_argument("--prior3", type=float, nargs=3, default=None, metavar=("VT", "ALPHA", "GS"),
                    help="three-parameter prior with saturation at GS (overrides --prior)")
    ap.add_argument("--calib", type=float, nargs=2, default=None, metavar=("W_PS", "GATE_MAX"),
                    help="one stressed characterisation point: adjust the stage threshold so the chain's gate maximum at W_PS is GATE_MAX")
    ap.add_argument("--calib-pad", type=int, default=None, metavar="DEPTH",
                    help="calibrate on the transistor PAD peak at this matrix depth (one stressed run, no gate probe): bisection on the stage threshold, then the drive")
    ap.add_argument("--depth-residual", action="store_true",
                    help="re-attach the depth-scaled pull-down residual (residual_depth_rule) to the chain build (io_buf)")
    args = ap.parse_args()
    dev = args.variant
    cc = args.ccomp if args.ccomp is not None else LOOP_CC[dev]
    sup, ibis = gp.VARIANTS[dev]
    gp.VARIANT_NAME = dev
    global PRIOR_FN
    matrix = dev in gp.MATRIX_SET
    mdir = G / (dev + (f"_c{cc:g}" if cc else ""))
    if not (mdir / "shipped/driver.sub").exists():
        # variants: generate the shipped model here (C_comp rewritten if asked)
        if cc:
            txt = re.sub(r"^C_comp\s+.*$", f"C_comp {cc:.4f}pF {cc:.4f}pF {cc:.4f}pF", ibis.read_text(errors="ignore"), count=1, flags=re.M)
            mdir.mkdir(parents=True, exist_ok=True)
            ibis = mdir / "input_ccomp.ibs"
            ibis.write_text(txt, encoding="utf-8")
        model, comp = gp.ibis_names(ibis)
        data0 = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
        from pybis2spice import subcircuit
        (mdir / "shipped").mkdir(parents=True, exist_ok=True)
        subcircuit.generate_spice_model("Output", gp.BUILD, data0, "Typical", str(mdir / "shipped/driver.sub"))
    ship = (mdir / "shipped/driver.sub").read_text(encoding="utf-8")
    full_ship = gp.run_ours(mdir / "shipped/full", ship, sup, 10.0)
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    cs = gp.cases(dev)
    refs = {d_: gp.tr0_pad(d / "run.tr0" if matrix else d / "transistor/run.tr0") for d_, _, d in cs}
    label = (f"{args.source}_{args.maps}" + (f"_K{args.K}" if args.K else "")
             + (f"_prior{args.prior[0]:g}_{args.prior[1]:g}" if args.prior else "")
             + (f"_prior3_{args.prior3[0]:g}_{args.prior3[1]:g}_{args.prior3[2]:g}" if args.prior3 else "")
             + (f"_xlin{args.fix_xlin:g}" if args.fix_xlin else "")
             + (f"_calib{args.calib[0]:g}" if args.calib else "") + (f"_calibpad{args.calib_pad}" if args.calib_pad else "")
             + ("_dres" if args.depth_residual else ""))
    tag = OUT / (dev + (f"_c{cc:g}" if cc else "")) / label
    tag.mkdir(parents=True, exist_ok=True)

    # --- the map prior (needed for --source ibis and --maps prior) -----------
    need_si = args.maps == "silicon" or args.source == "real" or not (args.prior or args.prior3)
    si = silicon_maps_for(dev, data, sup, cc) if need_si else None
    if args.prior3:
        vt, al, gs = args.prior3
        PRIOR_FN = lambda g: pm.prior3(g, vt, al, gs)   # noqa: E731
        pr_txt = f"prior3 vt={vt:.2f} alpha={al:.2f} gs={gs:.2f}"
    else:
        if args.prior:
            vt, al = args.prior
        else:
            gg, kk = si[0]
            m = (kk >= 0.10) & (gg <= 0.995)
            vt, al, _ = pm.fit_prior(gg[m], kk[m])
        PRIOR_FN = lambda g: pm.prior(g, vt, al)         # noqa: E731
        pr_txt = f"prior vt={vt:.2f} alpha={al:.2f}"
    print(f"\n  {dev}: chain prototype, source={args.source}, maps={args.maps}, {pr_txt}, C_comp {cc}")

    # --- target gate and the chain fit -----------------------------------------
    fam = "io_buf" if dev.startswith("io_buf") else ("inv" if dev.startswith("inv") else "ex2")
    Ks = args.Ks or ([args.K] if args.K else ({"ex2": [2, 3, 4], "inv": [5, 7, 9], "io_buf": [1, 2, 3]}[fam]))
    if args.source == "ibis":
        print("    chain fit in the Ku domain: prior(chain) vs the tables' full-swing Ku(t):")
        fits = fit_chain_ku(full_ship, vt, al, Ks, x_lin_fixed=args.fix_xlin)
    else:
        t_g, g = target_gate(dev, args.source, full_ship, vt, al)
        print("    chain fit to the real gate step responses:")
        fits, grid, u, v = fit_chain_to(t_g, g, Ks, x_lin_fixed=args.fix_xlin)
    K = args.K or pick_K(fits)
    c, prm = fits[K]
    print(f"    -> K = {K}: s_up {prm[0]:.3f} s_dn {prm[1]:.3f} vt {prm[2]:.3f} x_lin {prm[3]:.3f}  (full-swing rms {c:.4f})")
    if args.calib:
        prm = calibrate(prm, K, args.calib[0], args.calib[1])
    gdn = None
    if gr.GATES.get(dev, (None, None))[1] is not None:
        print("    pull-down chain fit (second predriver path):")
        if args.source == "ibis":
            fits_d = fit_chain_ku(full_ship, vt, al, Ks, which="kd", x_lin_fixed=args.fix_xlin)
        else:
            td, gd_ = target_gdn_gate(dev, args.source, full_ship, vt, al)
            fits_d, _, _, _ = fit_chain_to(td, gd_, Ks, x_lin_fixed=args.fix_xlin)
        Kd = args.K or pick_K(fits_d)
        cd, prm_d = fits_d[Kd]
        print(f"    -> K_d = {Kd}: s_up {prm_d[0]:.3f} s_dn {prm_d[1]:.3f} vt {prm_d[2]:.3f} x_lin {prm_d[3]:.3f}  (rms {cd:.4f})")
        gdn = (Kd, prm_d)
    # --- build ----------------------------------------------------------------
    text1 = patch_chain(ship, K, prm, gdn, sup)
    full_new = gp.run_ours(tag / "full_pass1", text1, sup, 10.0)
    if args.maps == "ibis":
        rise, fall = gc.derive_maps(full_new, full_ship)
        kd_on, kd_off = sg.derive_kd_maps(full_new, full_ship)
    elif args.maps == "prior":
        rise, fall, kd_on, kd_off = prior_maps(full_ship, vt, al)
    else:
        rise, fall, kd_on, kd_off = si
    text = gc.patch_kd_maps(gc.patch_maps(text1, rise, fall), kd_on, kd_off)
    if args.calib_pad:
        depth = args.calib_pad
        w = next(w_ for d_, w_, _ in cs if d_ == depth)
        prm = calibrate_pad(ship, K, prm, gdn, sup, (rise, fall, kd_on, kd_off), refs[depth], w, tag / "calib", f"d{depth}")
        text1 = patch_chain(ship, K, prm, gdn, sup)
        text = gc.patch_kd_maps(gc.patch_maps(text1, rise, fall), kd_on, kd_off)
    if args.depth_residual:
        import residual_depth_rule as rd
        f0 = gp.run_ours(tag / "full_noresidual", text, sup, 10.0)
        plateau = float(np.interp(14.5, f0["t"], f0["pad"]))
        text = rd.patch(text, rd.peak_hold_pad(plateau))
        print(f"    depth-scaled residual attached (model plateau {plateau:.4f} V)")
    (tag / "driver_chain.sub").write_text(text, encoding="utf-8")

    # --- score ----------------------------------------------------------------
    fs = gp.run_ours(tag / "full", text, sup, 10.0)
    if matrix:
        fraw = psp.parse_tr0(psp.OUT / dev / "full/run.tr0")
        tfull, pfull = np.asarray(fraw["time"], float) * 1e9, np.asarray(fraw["v(pad_sp)"], float)
    else:
        cand = sorted((cs[0][2].parent / "full_swing").glob("**/*.tr0"))
        if cand:
            tfull, pfull = gp.tr0_pad(cand[0])
        else:
            tfull, pfull = np.array([0.0, 22.0]), np.array([np.nan, np.nan])
    g2 = np.arange(4.5, 20.0, 0.005)
    rms_full = float(np.sqrt(np.mean((np.interp(g2, fs["t"], fs["pad"]) - np.interp(g2, tfull, pfull)) ** 2)))
    rms_ship = float(np.sqrt(np.mean((np.interp(g2, full_ship["t"], full_ship["pad"]) - np.interp(g2, tfull, pfull)) ** 2)))
    # the chain's gate vs the real gate at full swing
    if matrix:
        tr_, gr_ = gr.real_gate(dev, 0, gr.GATES[dev][0])
        gw = (g2 > 4.9) & (g2 < 9.0)
        gate_rms = float(np.sqrt(np.mean((np.interp(g2[gw], fs["t"], fs["gup"]) - np.interp(g2[gw], tr_, gr_)) ** 2)))
    else:
        gate_rms = float("nan")
    print(f"    full swing: pad rms vs transistor {rms_full*1e3:.1f} mV (shipped {rms_ship*1e3:.1f}); model gate vs real gate rms {gate_rms:.3f}")
    print(f"    {'build':<22} | " + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs) + " | " + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs) + " |  gate max: model / real")
    rows = []
    fig, axes = plt.subplots(2, len(cs), figsize=(4.0 * len(cs), 7.0), sharex="col")
    for name, txt, d0 in (("shipped", ship, mdir / "shipped"), (label, text, tag)):
        pks, lags, gm = [], [], []
        for col, (depth, w, d) in enumerate(cs):
            r = gp.run_ours(d0 / f"d{depth}", txt, sup, w)
            pk, lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
            pks.append(pk)
            lags.append(lag)
            rev = gp.RISE_NS + w
            gg = np.arange(rev - 0.5, rev + 3.0, 0.002)
            if matrix:
                tw, gw_ = gr.real_gate(dev, depth, gr.GATES[dev][0])
            else:
                tw, gw_ = gg, np.full(len(gg), np.nan)
            gm.append((float(np.interp(gg, r["t"], r["gup"]).max()), float(np.nanmax(np.interp(gg, tw, gw_)))))
            a, b = axes[0][col], axes[1][col]
            if name == "shipped":
                a.plot(gg - rev, np.interp(gg, tw, gw_), color="#111111", lw=3.0, label="transistor gate")
                a.plot(gg - rev, np.interp(gg, r["t"], r["gup"]), color="#8A8A8A", lw=1.2, ls=":", label="shipped GUP")
                b.plot(gg - rev, np.interp(gg, *refs[depth]), color="#111111", lw=3.0, label="transistor pad")
                b.plot(gg - rev, np.interp(gg, r["t"], r["pad"]), color="#8A8A8A", lw=1.2, ls=":", label=f"shipped ({pk:+.0f}%)")
            else:
                a.plot(gg - rev, np.interp(gg, r["t"], r["gup"]), color="#B03060", lw=2.0, ls="--", label=f"chain GUP, K={K}")
                a.plot(gg - rev, np.interp(gg, r["t"], r["ku"]), color="#C05621", lw=1.2, label="chain Ku")
                b.plot(gg - rev, np.interp(gg, r["t"], r["pad"]), color="#2E8B57", lw=2.0, ls="--", label=f"chain ({pk:+.0f}%)")
                a.set_title(f"W = {depth} ps", fontweight="bold")
                a.set_ylim(-0.2, 1.2)
                a.grid(alpha=0.3)
                b.grid(alpha=0.3)
                b.set_xlabel("time from the reversal (ns)")
                if col == 0:
                    a.legend(fontsize=7)
                    b.legend(fontsize=7)
                    a.set_ylabel("gate / Ku")
                    b.set_ylabel("pad (V)")
        rows.append(dict(build=name, K=K if name != "shipped" else "", full_pad_rms_mV=round((rms_ship if name == "shipped" else rms_full) * 1e3, 1),
                         **{f"pk_d{dp}": round(x, 1) for (dp, _, _), x in zip(cs, pks)},
                         **{f"lag_d{dp}": round(x, 1) for (dp, _, _), x in zip(cs, lags)},
                         **{f"gate_d{dp}": f"{m_[0]:.2f}/{m_[1]:.2f}" for (dp, _, _), m_ in zip(cs, gm)}))
        print(f"    {name:<22} | " + "".join(f"{x:>9.1f}" for x in pks) + " | " + "".join(f"{x:>9.0f}" for x in lags)
              + " |  " + " ".join(f"{m_[0]:.2f}/{m_[1]:.2f}" for m_ in gm))
    fig.suptitle(f"{dev}: command = {K} identical current-limited stages ({args.source} gate, {args.maps} maps)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(tag / "chain.png", dpi=150)
    plt.close(fig)
    with (tag / "sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(rows[-1].keys()))
        wri.writeheader()
        wri.writerows(rows)
    print(f"  figure: {tag / 'chain.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
