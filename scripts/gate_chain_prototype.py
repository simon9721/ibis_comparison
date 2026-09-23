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
LAST_SDN = None          # scale on the FINAL stage's discharge rate (None = identical stages)
FIT_LAST_SDN = False     # fit that scale in the Ku-domain fit
XLIN_DN_RATIO = 1.0      # discharge-direction resistive fraction = x_lin * ratio


def stage_block(K, s_up, s_dn, vt, x_lin, p=1.0, pre="STG", last_sdn=None) -> str:
    """K current-limited stages from CHIN to <pre><K>; rates in 1/ns.

    `last_sdn` scales the final stage's discharge rate only: that stage drives the output gate
    and sets how fast it comes back, which the identical-stage fit cannot get right on a fast
    chain (inv_chain, 2026-09-22). None = every stage identical, as before."""
    head = "K identical stages (fitted at full swing)" if not last_sdn else \
        f"K stages, the last discharging {last_sdn:g}x faster (fitted at full swing)"
    lines = [f"* --- current-limited command chain {pre}: {head} ---"]
    for k in range(1, K + 1):
        u = "V(CHIN)" if k == 1 else f"V({pre}{k - 1})"
        v = f"V({pre}{k})"
        xu = f"max(min(({u} - {vt:.6g}) / {1 - vt:.6g}, 1), 0)"
        xd = f"max(min((1 - {u} - {vt:.6g}) / {1 - vt:.6g}, 1), 0)"
        if p == 1.0:
            hu, hd = xu, xd
        else:
            # p < 1 has an infinite slope at 0 (ngspice: "0, -0.5 out of range for pwr");
            # shift by 1e-3 so the slope is finite and the law still starts at exactly 0
            eps = 1e-6
            hu = f"(pow({xu} + {eps:g}, {p:g}) - {eps ** p:.6g})"
            hd = f"(pow({xd} + {eps:g}, {p:g}) - {eps ** p:.6g})"
        ru = f"min(1, (1 - {v}) / {x_lin:.6g})"
        rd = f"min(1, {v} / {x_lin * XLIN_DN_RATIO:.6g})"
        sd = s_dn * (last_sdn if (last_sdn and k == K) else 1.0)
        lines.append(f"B{pre}{k} {pre}{k} 0 I = -{{gate_c}} * 1e9 * ({s_up:.6g} * {hu} * {ru} - {sd:.6g} * {hd} * {rd})")
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
    s = re.sub(r"^BGUP GUP 0 I = .*$", chin + stage_block(K, s_up, s_dn, vt, x_lin, p, last_sdn=LAST_SDN), sub, count=1, flags=re.M)
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
        c, prms = cl.fit_chain_shared(u, v, K, p=P_LAW, x_lin_fixed=x_lin_fixed)
        fits[K] = (c, prms[0])
        print(f"      K={K}: rms {c:.4f}  s_up {prms[0][0]:.2f} s_dn {prms[0][1]:.2f} vt {prms[0][2]:.2f} x_lin {prms[0][3]:.2f}")
    return fits, grid, u, v


P_LAW = 1.0   # drive power law h(x) = clip((x - vt)/(1 - vt))**P_LAW; 2 = MOSFET-like square law (recovery_law_probe.py)


def chain_prms(s_up, s_dn, vt, x_lin, p, K, last_sdn=None):
    """The per-stage parameters the emitter would write: identical stages, except that the
    final one's discharge rate is scaled when `last_sdn` is set."""
    r = last_sdn if last_sdn is not None else LAST_SDN
    prms = [(s_up, s_dn, vt, x_lin, p)] * K
    if r:
        prms = prms[:-1] + [(s_up, s_dn * r, vt, x_lin, p)]
    return prms


def fit_chain_ku(full_ship, vt, al, Ks, which="ku", x_lin_fixed=None):
    """File-only route: fit K identical stages so that prior(chain output) reproduces the
    tables' full-swing gate-part Ku(t) (or, for the pull-down, the mirrored Kd(t)). No
    inversion of the prior where it is poorly conditioned; the sub-threshold part of the
    chain is constrained only by the identical-stage structure."""
    grid = np.arange(4.0, 21.0, cl.DT)
    u = ((grid >= t_on()) & (grid < t_on() + 10.0)).astype(float)
    tf = full_ship["t"]
    # `model(g)` is what the built model would show for the chain output g (the
    # pull-up sense, 1 = input high): Ku = prior(g); for the pull-down branch
    # Kd = prior(GDN) with GDN = 1 - g. Fitting Kd through its own map matters on
    # an open-drain, where Ku is a mirrored placeholder: the Ku-domain target is
    # zero wherever g < vt, which is exactly where Kd turns on, so a Ku-domain
    # fit leaves the pull-down onset unconstrained (measured 250 ps early on the
    # open-drain ex2, 2026-09-10).
    if which == "ku":
        kb = full_ship["kugate_base"]
        k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
        target = np.interp(grid, tf, np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0))
        model = PRIOR_FN
    elif which == "kd_map":
        kd = full_ship["kdgate_base"]
        d_on, d_off = float(np.interp(4.5, tf, kd)), float(np.interp(12.0, tf, kd))
        target = np.interp(grid, tf, np.clip((kd - d_off) / (d_on - d_off), 0.0, 1.0))
        model = lambda g: PRIOR_FN(1.0 - g)  # noqa: E731
    else:
        kd = full_ship["kdgate_base"]
        d_on, d_off = float(np.interp(4.5, tf, kd)), float(np.interp(12.0, tf, kd))
        target = np.interp(grid, tf, np.clip((d_on - kd) / (d_on - d_off), 0.0, 1.0))
        model = PRIOR_FN
    fits = {}
    for K in Ks:
        best = (9.0, None)

        def unpack(z):
            return np.exp(z[0]), np.exp(z[1]), z[2], (x_lin_fixed if x_lin_fixed is not None else z[3])

        def cost(z, last_sdn=None):
            s_up, s_dn, vtt, x_lin = unpack(z)
            if not (0.0 <= vtt <= 0.7 and 0.02 <= x_lin <= 1.5):
                return 9.0
            g = cl.simulate_chain(u, chain_prms(s_up, s_dn, vtt, x_lin, P_LAW, K, last_sdn))
            return float(np.sqrt(np.mean((model(g) - target) ** 2)))

        n = 3 if x_lin_fixed is not None else 4
        for s0 in (2.0, 8.0, 30.0):
            z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4][:n]), step=[0.7, 0.7, 0.15, 0.15][:n], maxiter=800)
            if c < best[0]:
                s_up, s_dn, vtt, x_lin = unpack(z)
                best = (c, (float(s_up), float(s_dn), float(vtt), float(x_lin), P_LAW))
        if FIT_LAST_SDN and best[1] is not None:
            # one more number: how much faster the final stage discharges. Refit the shared four
            # at each candidate, so the scale cannot simply absorb a worse shared fit.
            global LAST_SDN
            keep, best_r = LAST_SDN, (best[0], 1.0, best[1])
            for r in (1.25, 1.5, 2.0, 3.0, 4.0, 6.0):
                LAST_SDN = r
                for s0 in (2.0, 8.0, 30.0):
                    z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4][:n]),
                                          step=[0.7, 0.7, 0.15, 0.15][:n], maxiter=800)
                    if c < best_r[0]:
                        su, sd, vtt, xl = unpack(z)
                        best_r = (c, r, (float(su), float(sd), float(vtt), float(xl), P_LAW))
            LAST_SDN = keep if best_r[1] == 1.0 else best_r[1]
            best = (best_r[0], best_r[2])
            print(f"      K={K}: final-stage discharge x{best_r[1]:g} (Ku-domain rms {best_r[0]:.4f})")
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


def anchor_maps(maps):
    """Force each measured map to the physics at its two ends: exactly 0 where the branch is
    off and 1 where it is fully on.

    The two-fixture solve leaves a small residual there. Measured 2026-09-17: at 12 ns, with
    the input high and the pull-down fully off, the solved Kd map returns -0.0144 on ex2 and
    -0.0166 on inv_chain instead of 0, so the pull-down branch SOURCES current at the settled
    point; Ku reads 1.0029 instead of 1. The settled level reads both ends directly, which is
    the whole of the +20 mV / +14 mV full-swing offset (every prior-map build lands within
    3 mV). A conducting fraction cannot be negative, and the pull-up table was confirmed to
    reproduce the transistor's DC operating point to 0.03 %, so both ends are known exactly;
    only the interior shape is measured. The interior is left untouched."""
    out = []
    for xs, ys in maps:
        y = np.asarray(ys, float)
        lo, hi = float(y[0]), float(y[-1])
        out.append((xs, np.clip((y - lo) / (hi - lo), 0.0, 1.0) if hi - lo > 1e-9 else y))
    return tuple(out)


def anchor_maps_off(maps):
    """Gentler anchor: clip only the pull-down maps at zero, so a branch that is fully off
    cannot source current, and leave the pull-up maps exactly as solved.

    Measured 2026-09-17: the full rescale fixes the settled level on both buffers but costs
    ex2's stressed peaks (-2.0/-3.1/-3.8/-3.8/+0.9 becomes -8.8/-10.1/-9.6/-8.5/-2.2, and it
    reproduces at a second calibration width, with the plain build losing its threshold bracket
    too, so it is not a calibration artifact). ex2's stressed peak is built while the gate is
    still below turn-on, which is the region where the solved Ku goes slightly negative; that
    region is what the rescale clips away. inv_chain never reads there. This variant keeps it."""
    rise, fall, kd_on, kd_off = maps

    def clip(m):
        return m[0], np.clip(np.asarray(m[1], float), 0.0, None)

    return rise, fall, clip(kd_on), clip(kd_off)


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
        return float(cl.simulate_chain(u_c, chain_prms(prm[0], prm[1], vt_, prm[3], prm[4], K)).max())

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
        return float(cl.simulate_chain(u_c, chain_prms(prm[0] * k, prm[1] * k, prm[2], prm[3], prm[4], K)).max())

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


def fall50(t, v, w):
    """Time (ns) at which the stressed pad falls back through half its peak, after the peak."""
    rev = gp.RISE_NS + w
    g = np.arange(rev - 0.1, rev + 3.0, 0.001)
    a = np.interp(g, t, v)
    ia = int(np.argmax(a))
    below = np.where(a[ia:] < 0.5 * a[ia])[0]
    return float(g[ia + below[0]]) if len(below) else float("nan")


def calibrate_fall(ship, K, prm, gdn, sup, maps, ref, w, workdir, label=""):
    """Second number from the same stressed pad run: its return time. Bisect a scale on the
    stage discharge rate s_dn until the model's pad falls through half-peak at the same time
    as the transistor's (the real-stage fit gets the peak right but returns too slowly under
    stress: the stage drains a partial level faster than the chain's law, 2026-09-14)."""
    rise, fall, kd_on, kd_off = maps
    t_ref = fall50(ref[0], ref[1], w)

    def err(k, i):
        prm_ = (prm[0], prm[1] * k, prm[2], prm[3], prm[4])
        text = gc.patch_kd_maps(gc.patch_maps(patch_chain(ship, K, prm_, gdn, sup), rise, fall), kd_on, kd_off)
        r = gp.run_ours(workdir / f"fall{i:02d}", text, sup, w)
        return (fall50(r["t"], r["pad"], w) - t_ref) * 1e3, gp.score(ref[0], ref[1], r["t"], r["pad"], w)[0]

    e0, p0 = err(1.0, 0)
    print(f"    fall calibration {label}: return time {e0:+.0f} ps vs transistor with s_dn {prm[1]:.3f} (peak {p0:+.1f} %)")
    lo, hi = 0.4, 3.0
    it = 1
    for _ in range(7):
        mid = 0.5 * (lo + hi)
        e, _ = err(mid, it)
        if e > 0:      # model returns late: drain faster
            lo = mid
        else:
            hi = mid
        it += 1
    k = 0.5 * (lo + hi)
    e, pk = err(k, it)
    print(f"    -> s_dn scale {k:.3f}: return time {e:+.0f} ps, peak {pk:+.1f} %")
    return (prm[0], prm[1] * k, prm[2], prm[3], prm[4])


def fit_chain_joint(dev, node, t_g, g, W_ps, K, p, x_lin_fixed=None, w_stress=1.0):
    """K identical stages fitted to the full-swing step AND the probed stressed gate at
    W_ps (joint_fit_probe.py: the full-swing step alone leaves the threshold and rates
    under-determined, and the chain returns 50-60 ps late under stress; one stressed gate
    in the fit closes that to ~20 ps while keeping the train widening)."""
    grid = np.arange(4.0, 21.0, cl.DT)
    u_f = ((grid >= t_on()) & (grid < t_on() + 10.0)).astype(float)
    v_f = np.interp(grid, t_g, g)
    ts, gs = gr.real_gate(dev, W_ps, node)
    u_s = ((grid >= t_on()) & (grid < t_on() + W_ps / 1e3)).astype(float)
    v_s = np.interp(grid, ts, gs)
    mf = ((grid > 4.6) & (grid < 9.0)) | ((grid > 14.6) & (grid < 19.0))
    ms = (grid > 4.6) & (grid < 9.0)
    best = (9.0, None)

    def unpack(z):
        return float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), (x_lin_fixed if x_lin_fixed is not None else float(z[3]))

    def cost(z):
        s_up, s_dn, vt, x_lin = unpack(z)
        if not (0.0 <= vt <= 0.7 and 0.02 <= x_lin <= 1.5):
            return 9.0
        prms = [(s_up, s_dn, vt, x_lin, p)] * K
        c = float(np.mean((cl.simulate_chain(u_f, prms)[mf] - v_f[mf]) ** 2))
        c += w_stress * float(np.mean((cl.simulate_chain(u_s, prms)[ms] - v_s[ms]) ** 2))
        return float(np.sqrt(c))

    n = 3 if x_lin_fixed is not None else 4
    for s0 in (2.0, 8.0, 30.0):
        z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4][:n]), step=[0.7, 0.7, 0.15, 0.15][:n], maxiter=800)
        if c < best[0]:
            s_up, s_dn, vt, x_lin = unpack(z)
            best = (c, (s_up, s_dn, vt, x_lin, p))
    return best


def refit_with_vt(t_g, g, K, vt_fixed, p):
    """K identical stages fitted to the full-swing gate step with the threshold held: the
    other three numbers (s_up, s_dn, x_lin) re-adjust so full swing stays reproduced."""
    grid = np.arange(4.0, 21.0, cl.DT)
    u = ((grid >= t_on()) & (grid < t_on() + 10.0)).astype(float)
    v = np.interp(grid, t_g, g)
    best = (9.0, None)

    def cost(z):
        s_up, s_dn, x_lin = np.exp(z[0]), np.exp(z[1]), z[2]
        if not (0.02 <= x_lin <= 1.5):
            return 9.0
        return float(np.sqrt(np.mean((cl.simulate_chain(u, [(s_up, s_dn, vt_fixed, x_lin, p)] * K) - v) ** 2)))

    for s0 in (2.0, 8.0, 30.0):
        z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4]), step=[0.7, 0.7, 0.15], maxiter=600)
        if c < best[0]:
            best = (c, (float(np.exp(z[0])), float(np.exp(z[1])), float(vt_fixed), float(z[2]), p))
    return best


def calibrate_timing(ship, K, prm, gdn, sup, maps, ref, w, workdir, t_g, g, label=""):
    """The stressed pad's return time sets the threshold: for each candidate vt the chain is
    refitted at full swing (full swing preserved), built, run on the calibration pulse, and
    its half-peak return time compared with the transistor's; bisection on vt. The peak is
    then set by the usual pad calibration (drive scale). Motivation: joint_fit_probe.py,
    where adding one stressed gate to the fit moved vt 0.28 -> 0.34 and closed the return
    from +55 ps to +16 ps while keeping the train widening (ex2, 2026-09-14)."""
    rise, fall, kd_on, kd_off = maps
    t_ref = fall50(ref[0], ref[1], w)
    cache = {}

    def err(vt, i):
        c, prm_ = refit_with_vt(t_g, g, K, vt, prm[4])
        text = gc.patch_kd_maps(gc.patch_maps(patch_chain(ship, K, prm_, gdn, sup), rise, fall), kd_on, kd_off)
        r = gp.run_ours(workdir / f"vt{i:02d}", text, sup, w)
        e = (fall50(r["t"], r["pad"], w) - t_ref) * 1e3
        cache[vt] = prm_
        return e

    e0 = err(prm[2], 0)
    print(f"    timing calibration {label}: return time {e0:+.0f} ps vs transistor with vt {prm[2]:.3f}")
    lo, hi = max(0.05, prm[2] - 0.2), min(0.65, prm[2] + 0.25)
    e_lo, e_hi = err(lo, 1), err(hi, 2)
    print(f"      vt {lo:.2f} -> {e_lo:+.0f} ps, vt {hi:.2f} -> {e_hi:+.0f} ps")
    if not ((e_lo > 0) != (e_hi > 0)):
        print("      no bracket: threshold left as fitted")
        return prm
    it = 3
    for _ in range(6):
        mid = 0.5 * (lo + hi)
        e = err(mid, it)
        if (e > 0) == (e_lo > 0):
            lo, e_lo = mid, e
        else:
            hi, e_hi = mid, e
        it += 1
    vt = lo if abs(e_lo) < abs(e_hi) else hi
    prm_ = cache[vt]
    print(f"    -> vt {vt:.3f}: s_up {prm_[0]:.3f} s_dn {prm_[1]:.3f} x_lin {prm_[3]:.3f}, return time {min(e_lo, e_hi, key=abs):+.0f} ps")
    return prm_


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="ex2")
    ap.add_argument("--ccomp", type=float, default=None)
    ap.add_argument("--source", choices=("real", "ibis"), default="real")
    ap.add_argument("--maps", choices=("ibis", "prior", "silicon"), default="silicon")
    ap.add_argument("--K", type=int, default=None, help="stage count; default: smallest K on the rms plateau over --Ks")
    ap.add_argument("--p", type=float, default=1.0, help="drive power law exponent of every stage (1 = linear above threshold, 2 = square law)")
    ap.add_argument("--anchor-maps", action="store_true",
                    help="with --maps silicon: rescale each measured map so it is exactly 0 at the off end and 1 at "
                         "the on end. Removes the solve residual that the settled level reads directly (see anchor_maps)")
    ap.add_argument("--anchor-mode", choices=("ends", "off"), default="ends",
                    help="with --anchor-maps: 'ends' rescales every map to exactly 0..1; 'off' clips only the pull-down "
                         "maps at zero and leaves the pull-up map's sub-threshold region as solved")
    ap.add_argument("--last-sdn", type=float, default=None, metavar="R",
                    help="the FINAL stage discharges R times faster than the others (default: identical)")
    ap.add_argument("--fit-last-sdn", action="store_true",
                    help="fit that scale in the Ku-domain fit instead of fixing it")
    ap.add_argument("--dn-ratio", type=float, default=1.0, metavar="R",
                    help="fifth stage number: the discharge-direction resistive fraction is x_lin * R (1 = symmetric). "
                         "R > 1 makes a stage go resistive earlier on the way down, so it drains more slowly at the end "
                         "and keeps residual charge between pulses (train recovery) without changing the rise")
    ap.add_argument("--joint-stress", type=int, default=None, metavar="W_PS", help="with --source real: also fit the chain to the probed stressed gate at this width (needs predriver_stages_2026-09-09/<dev>/w<W>)")
    ap.add_argument("--calib-timing", action="store_true", help="with --calib-pad and --source real: set the threshold from the stressed pad's return time (refitting at full swing), then the peak")
    ap.add_argument("--calib-fall", action="store_true", help="with --calib-pad: also match the stressed pad's return time by scaling the stage discharge rate")
    ap.add_argument("--fit-through", choices=("prior", "silicon"), default="prior",
                    help="for --source ibis: invert the tables' Ku(t) through the map prior (default) or through the measured rise map")
    ap.add_argument("--Ks", type=int, nargs="*", default=None)
    ap.add_argument("--Kd", type=int, default=None,
                    help="stage count of the second (pull-down) predriver chain, io_buf; default: as --K / the plateau pick")
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
    global P_LAW, XLIN_DN_RATIO, LAST_SDN, FIT_LAST_SDN
    LAST_SDN, FIT_LAST_SDN = args.last_sdn, args.fit_last_sdn
    P_LAW = args.p
    XLIN_DN_RATIO = args.dn_ratio      # the ngspice emitter (stage_block) reads this module global
    cl.XLIN_DN_RATIO = args.dn_ratio   # the python fit must use the same law it is emitting
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
    label = (f"{args.source}_{args.maps}" + (f"_K{args.K}" if args.K else "") + (f"_Kd{args.Kd}" if args.Kd else "")
             + (f"_prior{args.prior[0]:g}_{args.prior[1]:g}" if args.prior else "")
             + (f"_prior3_{args.prior3[0]:g}_{args.prior3[1]:g}_{args.prior3[2]:g}" if args.prior3 else "")
             + (f"_xlin{args.fix_xlin:g}" if args.fix_xlin else "")
             + (f"_calib{args.calib[0]:g}" if args.calib else "") + (f"_calibpad{args.calib_pad}" if args.calib_pad else "") + ("_fall" if args.calib_fall else "") + ("_timing" if args.calib_timing else "") + (f"_joint{args.joint_stress}" if args.joint_stress else "") + (f"_p{args.p:g}" if args.p != 1.0 else "") + (f"_dn{args.dn_ratio:g}" if args.dn_ratio != 1.0 else "") + ("_lastfit" if args.fit_last_sdn else (f"_last{args.last_sdn:g}" if args.last_sdn else "")) + (("_anchoff" if args.anchor_mode == "off" else "_anch") if args.anchor_maps else "") + ("_fitsi" if args.fit_through == "silicon" else "")
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
    if args.fit_through == "silicon":
        # invert the tables through the MEASURED rise map itself (normalised rest..on), not
        # through its MOSFET-shaped approximation: the low-gate part of the map decides
        # where the chain fit puts its draining tail (recovery_law_probe.py, 2026-09-14)
        gg, kk = si[0]
        kn = (kk - float(kk[0])) / (float(kk[-1]) - float(kk[0]))
        PRIOR_FN = lambda g: np.interp(g, gg, kn)        # noqa: E731
        pr_txt += ", fit through the measured map"
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
        if args.joint_stress:
            print(f"    joint fit: full-swing step + the probed stressed gate at {args.joint_stress} ps")
            for K_ in Ks:
                c_, prm_ = fit_chain_joint(dev, gr.GATES[dev][0], t_g, g, args.joint_stress, K_, P_LAW, x_lin_fixed=args.fix_xlin)
                fits[K_] = (c_, prm_)
                print(f"      K={K_}: joint rms {c_:.4f}  s_up {prm_[0]:.2f} s_dn {prm_[1]:.2f} vt {prm_[2]:.2f} x_lin {prm_[3]:.2f}")
    K = args.K or pick_K(fits)
    c, prm = fits[K]
    print(f"    -> K = {K}: s_up {prm[0]:.3f} s_dn {prm[1]:.3f} vt {prm[2]:.3f} x_lin {prm[3]:.3f}  (full-swing rms {c:.4f})")
    if args.calib:
        prm = calibrate(prm, K, args.calib[0], args.calib[1])
    gdn = None
    if gr.GATES.get(dev, (None, None))[1] is not None:
        print("    pull-down chain fit (second predriver path):")
        Ks_d = [args.Kd] if args.Kd else Ks
        if args.source == "ibis":
            fits_d = fit_chain_ku(full_ship, vt, al, Ks_d, which="kd", x_lin_fixed=args.fix_xlin)
        else:
            td, gd_ = target_gdn_gate(dev, args.source, full_ship, vt, al)
            fits_d, _, _, _ = fit_chain_to(td, gd_, Ks_d, x_lin_fixed=args.fix_xlin)
        Kd = args.Kd or args.K or pick_K(fits_d)
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
        if args.anchor_maps:
            # at settle the model selects KDGATE_ON (GDNTARGET == GDN), so the residual the
            # settled level reads is kd_on at GDN 0, not kd_off
            before = (float(rise[1][-1]), float(kd_on[1][0]))
            if args.anchor_mode == "off":
                rise, fall, kd_on, kd_off = anchor_maps_off((rise, fall, kd_on, kd_off))
                print(f"    pull-down maps clipped at zero: Kd at the off end {before[1]:+.4f} -> "
                      f"{float(kd_on[1][0]):.4f}; Ku left as solved (on end {before[0]:.4f})")
            else:
                rise, fall, kd_on, kd_off = anchor_maps((rise, fall, kd_on, kd_off))
                print(f"    maps anchored to their ends: Ku at the on end {before[0]:.4f} -> 1.0000, "
                      f"Kd at the off end {before[1]:+.4f} -> 0.0000")
    text = gc.patch_kd_maps(gc.patch_maps(text1, rise, fall), kd_on, kd_off)
    if args.calib_pad:
        depth = args.calib_pad
        w = next(w_ for d_, w_, _ in cs if d_ == depth)
        if args.calib_timing:
            assert args.source == "real", "--calib-timing refits against the real gate step"
            prm = calibrate_timing(ship, K, prm, gdn, sup, (rise, fall, kd_on, kd_off), refs[depth], w, tag / "calib_t", t_g, g, f"d{depth}")
        prm = calibrate_pad(ship, K, prm, gdn, sup, (rise, fall, kd_on, kd_off), refs[depth], w, tag / "calib", f"d{depth}")
        if args.calib_fall:
            prm = calibrate_fall(ship, K, prm, gdn, sup, (rise, fall, kd_on, kd_off), refs[depth], w, tag / "calib", f"d{depth}")
            prm = calibrate_pad(ship, K, prm, gdn, sup, (rise, fall, kd_on, kd_off), refs[depth], w, tag / "calib2", f"d{depth} (after the fall)")
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
