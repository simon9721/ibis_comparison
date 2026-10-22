#!/usr/bin/env python3
"""Collect the data behind the stage-law model animation (scripts/stage_law_model_animation.py).

The animation explains the model itself (one stage, its law, the chain, the map, the pad) on the
test buffer ex2. Everything it draws is a stored result of the project, gathered here into one
file so that the manim scene needs no simulator and no project imports. Where the scene shows a
model curve, this script evaluates the model's own equations (current_limited_stage_model.simulate,
build_stage_law_doc_figures.chain_stages / prior) on the stored parameters, as the previous data
script did for the step responses. Numbers quoted in the storyboard are checked against what the
stored results say (soft checks, listed at the end of the run).

Arrays written, by part, with their source:

    part 1  what the file knows
      p1_t, p1_in, p1_gate, p1_pad          ex2 complete transition: input pin, probed gate (n4) and
                                            pad, normalised (predriver_stages_2026-09-09/ex2/full/run.tr0
                                            via current_limited_stage_model.ST, predriver_stage_probe.normalise)
      p1s_t, p1s_in, p1s_gate, p1s_pad      the same for the 810 ps pulse (.../ex2/w810/run.tr0)
      p1_gate_peak                          peak of the probed gate under the pulse (0.76)
      p1_pad_t, p1_pad_si, p1_pad_nat       pad in volts: transistor (build_0917_deck_figures.transistor_pad)
                                            and HSPICE native IBIS (stress_method_matrix_2026-08-20/delay_cmd/
                                            waveforms/ex2_short_high_w810ps.csv)
      p1_nat_err, p1_pad_peak, p1_swing     native peak error (build_0924_deck_figures._peak_err), the
                                            transistor's pulse peak (V), the settled swing (V)
    part 2  one stage and its law (illustrative values v_t = 0.3, x_lin = 0.45, s_up = s_dn = 2/ns)
      b_t, b_u, b_v                         one stage driven by a 0.4 ns input ramp up, a hold, a ramp down
                                            (cl.simulate on cl.DT)
      b_h_u, b_h_1u, b_r_up, b_r_dn         the four factors of (19) along that run
      b_up, b_dn                            the charging and discharging terms along that run (1/ns)
      b_events                              [t tap opens, t input fully on, t taper begins, t drain opens,
                                            t drain taper begins] (ns)
      hr_x, hr_h, hr_r                      the gate factor h and the drain factor r against their argument
      sr_t, sr_u, sr_v, sr_knee, sr_tau     one stage's step response, the ramp/exponential knee, x_lin/s_up
      dev_x, dev_y, dev_D, dev_knee,        inv_chain NMOS output-current family from HSPICE, five gate drives,
      dev_level, dev_alpha, dev_x0, dev_vth with the alpha-power knee of each (device_taper_2026-09-28/
                                            alpha_extract/nch_tn/run.sw0 via device_alpha_extract.parse_sw0/extract)
      dev_ll_x, dev_ll_y                    saturation current against gate drive (log-log data of the same device)
      dev_names, dev_alphas                 alpha of the four predriver devices (alpha_extract/results.csv)
      kn_t, kn_step, kn_sup1/2/4            step response as s_up is changed
      kn_ramp, kn_vt0.1/0.3/0.5             response to a 0.5 ns input ramp as v_t is changed
      kn_fall, kn_sdn1/2/4                  the falling edge as s_dn is changed
    part 3  the chain (ex2, file-only setting, selected candidate: build_stage_law_doc_figures.EX2)
      ch_prm                                [s_up, s_dn, v_t (after calibration), x_lin, K]
      ch_t, ch_u_full, ch_v_full (3, n)     complete transition: the three stage nodes (chain_stages)
      ch_handover, ch_t_rail                [t v1 crosses v_t, t v2 crosses v_t], t the gate reaches 0.99
      ch_u_810, ch_v_810 (3, n)             the 810 ps pulse
      ch_peak_810, ch_tpeak_810             peak and time of peak of each node under the pulse
      ch_real_t, ch_real_g, ch_real_peak    the probed gate of ex2 at 810 ps (f17._norm_pair)
      ch_lead_ps, ch_return_ps              model gate minus probed gate: t at half peak on the rise (lead,
                                            positive = model earlier) and on the return
    part 4  the map
      mp_t, mp_g, mp_ku                     ex2 complete transition: probed gate (f17._norm_pair, ex2_c1.7)
                                            and the file's K_u (gate_cascade_prototype_2026-09-09/ex2_c1.7/
                                            shipped/full/run.raw, v(x1.ku)), as fig_map
      mp_marks                              the five instants marked (ns)
      mp_curve_g, mp_curve_ku               the measured map (the pairs sorted by gate)
      mp_gg, mp_fit, mp_fit_prm             the formula fitted to it, (0.57, 0.64)
      mp_shapes, mp_cand (3, n)             the three candidate shapes (build_stage_law_doc_figures.SHAPES)
      mp_hyst                               [io_buf lo, io_buf hi, inv_chain lo, inv_chain hi, ex2 at 1.7 pF]
                                            rising-against-falling branch difference (gate_physics_2026-09-08/FINDINGS.md)
      gk_t, gk_u, gk_target                 the file's own K_u(t) target and chain input
                                            (stage_law_doc_2026-10-01/shape_fileonly/target_ex2.npz)
      gk_g_fit, gk_ku_fit, gk_rms_fit       the fitted chain (v_t = 0.700) and its K_u through the map (0.5, 0.7)
      gk_g_cal, gk_ku_cal, gk_rms_cal       the same chain after calibration (v_t = 0.632)
      gk_g_cut, gk_ku_cut                   the calibrated chain under the 810 ps pulse
      gk_marks_full, gk_marks_cut           the six instants marked in each row (fig_gate_to_ku)
    part 5  from K_u to the pad
      iv_v, iv_pu, iv_pd, iv_vdd            the pull-up and pull-down I-V tables of the file-only IBIS file
                                            (stage_count_from_file_2026-09-21/knee_models/ex2_c2.64/input_ccomp.ibs)
      cc_declared, cc_estimated             C_comp of the shipped ex2 file (5.0 pF) and of the file-only file (2.64 pF)
      pd_t, pd_si, pd_nat, pd_mo, pd_ku     pad at 810 ps: transistor, native, the selected model and its K_u
                                            (b24._cand(b24.CAND[b24.PICK], "d810"))
      pd_err_nat, pd_err_mo                 peak errors (b24._peak_err)
    part 6  what the file fixes
      ft_prm, ft_rms, ft_vt_bound           the fit (fit_search_fileonly/paths.npz end_2, landscape.npz vt_bound)
      ft_steps (4, n), ft_steps_prm, ft_steps_rms   a fit one number at a time from (8, 8, 0.4) (fig_fit_knobs d)
      ft_land_s_up, ft_land_vt, ft_land_rms the residual landscape over (s_up, v_t)
      am_g, am_late_map, am_early_map       two assumed maps (0.6, 0.6) and (0.4, 0.6)
      am_late_ku, am_early_ku, am_*_rms     each with the stage law fitted through it (shape_fileonly/*.json)
      am_late_ku810, am_early_ku810         the two under the 810 ps pulse
      am_late_vt, am_early_vt
      rms_by_K                              fit residual against stage count (stage_count_from_file step1_summary.csv,
                                            est_knee, ex2, pull-up)
      c_t, c_names, c_pre, c_post, c_pick   the nine candidates before (stage_law_doc/before_calibration) and after
                                            calibration (step6/step8 builds), the selected one
      c_rms                                 waveform rms at the calibration width (selector_builds.csv)
      bi_names, bi_vt, bi_err, bi_t, bi_pads   the bisection iterations on the selected candidate (calib_iterations/ex2.npz)
      w_widths, w_t, w_si, w_mo             the selected model at the five widths against the transistor
    part 7  closing card
      cl_worst                              worst peak error of the selected model over the five widths (8.3 %)

Output: results/stage_law_model_animation_2026-10-22/data/model_data.npz

    py -3.14 scripts/stage_law_model_animation_data.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import gate_ramp_prototype as gp  # noqa: E402  (before the deck modules: pybis2spice resolution)
import build_0917_deck_figures as f17  # noqa: E402
import build_0924_deck_figures as b24  # noqa: E402
import build_stage_law_doc_figures as figs  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402
import device_alpha_extract as dae  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402

OUT = ROOT / "results" / "stage_law_model_animation_2026-10-22" / "data"
DOC = ROOT / "results" / "stage_law_doc_2026-10-01"
SC = ROOT / "results" / "stage_count_from_file_2026-09-21"

CHECKS: list[str] = []


def check(name: str, value: float, expected: float, tol: float) -> None:
    """Soft check of a storyboard number against the stored result; mismatches are listed at the end."""
    ok = abs(float(value) - expected) <= tol
    CHECKS.append(f"  {'ok      ' if ok else 'MISMATCH'} {name}: stored {float(value):.4g}, storyboard {expected:g}")


def thin(t, *ys, n=400, lo=None, hi=None):
    """Resample onto n points of [lo, hi] (the animation needs no more)."""
    t = np.asarray(t, float)
    lo = t[0] if lo is None else lo
    hi = t[-1] if hi is None else hi
    g = np.linspace(lo, hi, n)
    return (g,) + tuple(np.interp(g, t, np.asarray(y, float)) for y in ys)


def first_t(t, cond):
    i = np.argmax(cond)
    return float(t[i]) if cond[i] else float("nan")


def half_cross(t, y, rising=True):
    """Time at which y first crosses half its peak, on the rise or (after the peak) on the return."""
    pk = float(y.max())
    ip = int(np.argmax(y))
    if rising:
        return first_t(t, y >= 0.5 * pk)
    tail, yt = t[ip:], y[ip:]
    return first_t(tail, yt <= 0.5 * pk)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    d = {}
    gp.VARIANT_NAME = "ex2"
    p = figs.EX2

    # ------------------------------------------------------------ part 1: what the file knows
    sig = ["v(in_dig)", "v(xdut.n4)", "v(pad_sp)"]
    full = psp.parse_tr0(cl.ST / "ex2" / "full" / "run.tr0")
    tf, sf = np.asarray(full["time"], float) * 1e9, psp.signals(full, sig)
    st = psp.parse_tr0(cl.ST / "ex2" / "w810" / "run.tr0")
    ts, ss = np.asarray(st["time"], float) * 1e9, psp.signals(st, sig)
    g_full, g_rest, g_high = psp.normalise(tf, sf["v(xdut.n4)"], tf, sf["v(xdut.n4)"])
    g_st = (ss["v(xdut.n4)"] - g_rest) / (g_high - g_rest)
    p_full, p_rest, p_high = psp.normalise(tf, sf["v(pad_sp)"], tf, sf["v(pad_sp)"])
    p_st = (ss["v(pad_sp)"] - p_rest) / (p_high - p_rest)
    sup = float(sf["v(in_dig)"].max())
    d["p1_t"], d["p1_in"], d["p1_gate"], d["p1_pad"] = thin(tf - 5.0, sf["v(in_dig)"] / sup, g_full, p_full, lo=-0.5, hi=4.0)
    d["p1s_t"], d["p1s_in"], d["p1s_gate"], d["p1s_pad"] = thin(ts - 5.0, ss["v(in_dig)"] / sup, g_st, p_st, lo=-0.5, hi=3.0)
    win = (ts - 5.0 > 0) & (ts - 5.0 < 3.0)
    d["p1_gate_peak"] = float(g_st[win].max())
    check("part 1 probed gate peak at 810 ps", d["p1_gate_peak"], 0.76, 0.01)
    t_si, si, _ = f17.transistor_pad("ex2", 810)
    t_si = t_si - 5.0
    nat = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / "ex2_short_high_w810ps.csv")
    t_nat, pad_nat = nat["time_ns"] - 5.0, nat["hspice_pad"]
    d["p1_pad_t"], d["p1_pad_si"] = thin(t_si, si, lo=-0.5, hi=3.0)
    _, d["p1_pad_nat"] = thin(t_nat, pad_nat, lo=-0.5, hi=3.0)
    e_nat, pk = b24._peak_err(t_nat, pad_nat, t_si, si, 0.81)
    d["p1_nat_err"], d["p1_pad_peak"], d["p1_swing"] = float(e_nat), float(pk), float(p_high - p_rest)
    check("part 1 native peak error (%)", e_nat, 71, 1.0)
    check("part 1 measured pulse peak (V)", pk, 0.77, 0.01)

    # ------------------------------------------------------------ part 2: one stage (illustrative values)
    VT, XL, S = 0.3, 0.45, 2.0
    t2 = np.arange(-0.2, 3.4, cl.DT)
    u2 = np.where(t2 < 1.8, np.clip(t2 / 0.4, 0.0, 1.0), np.clip(1.0 - (t2 - 1.8) / 0.4, 0.0, 1.0))
    v2 = cl.simulate(u2, S, S, VT, XL, 1.0)
    h_u, h_1u = cl.h(u2, VT, 1.0), cl.h(1.0 - u2, VT, 1.0)
    r_up, r_dn = np.minimum(1.0, (1.0 - v2) / XL), np.minimum(1.0, v2 / XL)
    d["b_t"], d["b_u"], d["b_v"] = t2, u2, v2
    d["b_h_u"], d["b_h_1u"], d["b_r_up"], d["b_r_dn"] = h_u, h_1u, r_up, r_dn
    d["b_up"], d["b_dn"] = S * h_u * r_up, S * h_1u * r_dn
    t_tap = first_t(t2, h_u > 0)
    t_on = first_t(t2, u2 >= 1.0)
    t_taper = first_t(t2, v2 > 1.0 - XL)
    t_drain = first_t(t2, (t2 > 1.0) & (h_1u > 0))
    t_taper_dn = first_t(t2, (t2 > t_drain) & (v2 < XL))
    d["b_events"] = np.array([t_tap, t_on, t_taper, t_drain, t_taper_dn])
    d["b_prm"] = np.array([VT, XL, S])
    xx = np.linspace(0, 1, 200)
    d["hr_x"], d["hr_h"], d["hr_r"] = xx, cl.h(xx, VT, 1.0), np.minimum(1.0, xx / XL)
    # one stage's step response: ramp of slope s_up, then exponential with tau = x_lin / s_up
    tsr = np.arange(-0.1, 2.0, cl.DT)
    step = (tsr >= 0).astype(float)
    d["sr_t"], d["sr_u"], d["sr_v"] = tsr, step, cl.simulate(step, S, S, VT, XL, 1.0)
    d["sr_knee"] = np.array([(1.0 - XL) / S, 1.0 - XL])
    d["sr_tau"] = XL / S
    # the device behind the law: inv_chain NMOS output curves (HSPICE) and the alpha-power knee
    vdd = 1.8
    blocks = dae.parse_sw0(figs.DT / "alpha_extract" / "nch_tn" / "run.sw0", dae.N_OUTER)
    vd0, alpha, vth, vgs, isat, curves = dae.extract(blocks, vdd, "n")
    x_full, y_full = curves[-1]
    fam_x = np.linspace(0, 1, 200)
    ys, Ds, knees, levels = [], [], [], []
    for j in (8, 11, 14, 17, 20):
        xj, yj = curves[j]
        ys.append(np.interp(fam_x, xj / vdd, yj / y_full[-1]))
        D = (vgs[j] - vth) / (vdd - vth)
        Ds.append(D)
        knees.append((vd0 / vdd) * D ** (alpha / 2))
        levels.append(D ** alpha)
    d["dev_x"], d["dev_y"], d["dev_D"], d["dev_knee"], d["dev_level"] = fam_x, np.array(ys), np.array(Ds), np.array(knees), np.array(levels)
    d["dev_alpha"], d["dev_x0"], d["dev_vth"] = float(alpha), float(vd0 / vdd), float(vth)
    m = vgs > vth + 0.05
    d["dev_ll_x"], d["dev_ll_y"] = (vgs[m] - vth) / (vdd - vth), isat[m] / isat[-1]
    rows = list(csv.DictReader((figs.DT / "alpha_extract" / "results.csv").open()))
    d["dev_names"] = np.array([r["device"] for r in rows])
    d["dev_alphas"] = np.array([float(r["alpha"]) for r in rows])
    check("part 2 inv_chain NMOS alpha", alpha, 1.28, 0.02)
    check("part 2 smallest device alpha (storyboard says 1.0-1.4)", d["dev_alphas"].min(), 1.0, 0.1)
    check("part 2 largest device alpha (storyboard says 1.0-1.4)", d["dev_alphas"].max(), 1.4, 0.1)
    # the three knobs
    tk = np.arange(-0.1, 2.0, cl.DT)
    stepk = (tk >= 0).astype(float)
    d["kn_t"], d["kn_step"] = tk, stepk
    for s in (1.0, 2.0, 4.0):
        d[f"kn_sup{s:g}"] = cl.simulate(stepk, s, s, VT, XL, 1.0)
    ramp = np.clip(tk / 0.5, 0.0, 1.0)
    d["kn_ramp"] = ramp
    for vt in (0.1, 0.3, 0.5):
        d[f"kn_vt{vt:g}"] = cl.simulate(ramp, S, S, vt, XL, 1.0)
    fall = (tk < 0).astype(float)
    d["kn_fall"] = fall
    for s in (1.0, 2.0, 4.0):
        d[f"kn_sdn{s:g}"] = cl.simulate(fall, S, s, VT, XL, 1.0, v0=1.0)

    # ------------------------------------------------------------ part 3: the chain (ex2, selected file-only model)
    d["ch_prm"] = np.array([p["s_up"], p["s_dn"], p["vt_cal"], p["x_lin"], p["K"]])
    t3 = np.arange(-0.3, 4.2, cl.DT)
    u_full3 = (t3 >= 0).astype(float)
    u_810 = ((t3 >= 0) & (t3 < 0.81)).astype(float)
    v_full = figs.chain_stages(u_full3, p["s_up"], p["s_dn"], p["vt_cal"], p["x_lin"], p["K"])
    v_810 = figs.chain_stages(u_810, p["s_up"], p["s_dn"], p["vt_cal"], p["x_lin"], p["K"])
    d["ch_t"], d["ch_u_full"], d["ch_v_full"] = t3, u_full3, np.array(v_full)
    d["ch_u_810"], d["ch_v_810"] = u_810, np.array(v_810)
    h1, h2 = first_t(t3, v_full[0] >= p["vt_cal"]), first_t(t3, v_full[1] >= p["vt_cal"])
    d["ch_handover"] = np.array([h1, h2])
    d["ch_t_rail"] = first_t(t3, v_full[2] >= 0.99)
    d["ch_peak_810"] = np.array([v.max() for v in v_810])
    d["ch_tpeak_810"] = np.array([t3[int(np.argmax(v))] for v in v_810])
    check("part 3 handover 1 (ns)", h1, 0.29, 0.02)
    check("part 3 handover 2 (ns)", h2, 0.73, 0.03)
    check("part 3 gate reaches 0.99 (ns, 'near 2')", d["ch_t_rail"], 2.0, 0.25)
    check("part 3 v2 peak under 810 ps", d["ch_peak_810"][1], 0.88, 0.02)
    check("part 3 gate peak under 810 ps", d["ch_peak_810"][2], 0.71, 0.02)
    tfr, gfr, tsr_, gsr = f17._norm_pair("ex2", 810, "v(xdut.n4)")
    d["ch_real_t"], d["ch_real_g"] = thin(tsr_, gsr, lo=-0.3, hi=4.2)
    wr = (tsr_ > 0) & (tsr_ < 3.0)
    d["ch_real_peak"] = float(gsr[wr].max())
    mg = v_810[2]
    tr, gr = d["ch_real_t"], d["ch_real_g"]
    d["ch_lead_ps"] = 1e3 * (half_cross(tr, gr, True) - half_cross(t3, mg, True))
    d["ch_return_ps"] = 1e3 * (half_cross(tr, gr, False) - half_cross(t3, mg, False))
    check("part 3 model gate leads the probed gate (ps)", d["ch_lead_ps"], 60, 15)

    # ------------------------------------------------------------ part 4: the map
    folder, node, _gname, widths, _y, _s = b24.DEV["ex2"]
    tfm, gfull_m, _tsm, _gsm = f17._norm_pair("ex2", widths[0], node)
    raw = sl.parse_ngspice_raw(f17.CASC / folder / "shipped" / "full" / "run.raw")
    t_m, ku_m = sl.time_ns(raw) - 5.0, sl.signal(raw, "v(x1.ku)")
    g_end = float(tfm[np.argmax(np.asarray(gfull_m) >= 0.995)]) + 0.25
    tt = np.linspace(0.2, g_end, 400)
    ku_t, g_t = np.interp(tt, t_m, ku_m), np.interp(tt, tfm, gfull_m)
    d["mp_t"], d["mp_g"], d["mp_ku"] = tt, g_t, ku_t
    d["mp_marks"] = np.array([0.95, 1.10, 1.22, 1.35, 1.55])
    order = np.argsort(g_t)
    d["mp_curve_g"], d["mp_curve_ku"] = g_t[order], ku_t[order]
    gg = np.linspace(0, 1, 400)
    d["mp_gg"], d["mp_fit"], d["mp_fit_prm"] = gg, figs.prior(gg, 0.57, 0.64), np.array([0.57, 0.64])
    d["mp_shapes"] = np.array(figs.SHAPES)
    d["mp_cand"] = np.array([figs.prior(gg, v, a) for v, a in figs.SHAPES])
    txt = (ROOT / "results" / "gate_physics_2026-09-08" / "FINDINGS.md").read_text(encoding="utf-8")
    hio = re.search(r"\| io_buf \| n2 \| ([0-9.]+)–([0-9.]+) \|", txt)
    hinv = re.search(r"\| inv_chain \| vout7 \| ([0-9.]+)–([0-9.]+) \|", txt)
    hex2 = re.search(r"At 1\.7 pF the loop is ([0-9.]+)", txt)
    assert hio and hinv and hex2, "hysteresis numbers not found in gate_physics FINDINGS.md"
    d["mp_hyst"] = np.array([float(hio.group(1)), float(hio.group(2)), float(hinv.group(1)), float(hinv.group(2)), float(hex2.group(1))])
    check("part 4 map hysteresis, low end", d["mp_hyst"].min(), 0.07, 0.005)
    check("part 4 map hysteresis, high end", d["mp_hyst"].max(), 0.11, 0.005)
    # the two relations in series, against the file's own Ku(t)
    z = np.load(DOC / "shape_fileonly" / "target_ex2.npz")
    grid, u_full, target, t_on4 = z["grid"], z["u"], z["target"], float(z["t_on"])
    t4 = grid - t_on4
    vtm, am = p["shape"]
    g_fit = figs.chain_stages(u_full, p["s_up"], p["s_dn"], p["vt_fit"], p["x_lin"], p["K"])[-1]
    g_cal = figs.chain_stages(u_full, p["s_up"], p["s_dn"], p["vt_cal"], p["x_lin"], p["K"])[-1]
    u_cut = ((t4 >= 0) & (t4 < 0.81)).astype(float)
    g_cut = figs.chain_stages(u_cut, p["s_up"], p["s_dn"], p["vt_cal"], p["x_lin"], p["K"])[-1]
    ku_fit, ku_cal, ku_cut = figs.prior(g_fit, vtm, am), figs.prior(g_cal, vtm, am), figs.prior(g_cut, vtm, am)
    d["gk_rms_fit"] = float(np.sqrt(np.mean((ku_fit - target) ** 2)))
    d["gk_rms_cal"] = float(np.sqrt(np.mean((ku_cal - target) ** 2)))
    (d["gk_t"], d["gk_u"], d["gk_target"], d["gk_g_fit"], d["gk_ku_fit"], d["gk_g_cal"], d["gk_ku_cal"],
     d["gk_g_cut"], d["gk_ku_cut"]) = thin(t4, u_full, target, g_fit, ku_fit, g_cal, ku_cal, g_cut, ku_cut, n=600, lo=-0.3, hi=4.6)
    d["gk_marks_full"] = np.array([0.85, 1.12, 1.22, 1.36, 1.6, 2.2])
    d["gk_marks_cut"] = np.array([0.95, 1.12, 1.25, 1.37, 1.5, 1.62])
    d["gk_gate_peak_cut"], d["gk_ku_peak_cut"] = float(g_cut.max()), float(ku_cut.max())
    check("part 4 fit rms (v_t 0.700)", d["gk_rms_fit"], 0.023, 0.001)
    check("part 4 gate turns back at (810 ps, calibrated)", g_cut.max(), 0.71, 0.02)
    check("part 4 Ku peak (810 ps, calibrated)", ku_cut.max(), 0.54, 0.02)

    # ------------------------------------------------------------ part 5: from Ku to the pad
    ib = SC / "knee_models" / "ex2_c2.64" / "input_ccomp.ibs"
    mname, cname = gp.ibis_names(ib)
    dm = pb.DataModel(pb.get_ibis_model_ecdtools(str(ib)), model_name=mname, component_name=cname)
    vdd5 = float(dm.v_range[0])
    v = np.linspace(-0.5, vdd5 + 1.0, 200)
    d["iv_v"], d["iv_vdd"] = v, vdd5
    d["iv_pu"] = -np.interp(vdd5 - v, dm.iv_pullup[:, 0], dm.iv_pullup[:, 1]) * 1e3
    d["iv_pd"] = np.interp(v, dm.iv_pulldown[:, 0], dm.iv_pulldown[:, 1]) * 1e3
    d["cc_estimated"] = float(dm.c_comp[0]) * 1e12
    ib0 = gp.VARIANTS["ex2"][1]
    m0, c0 = gp.ibis_names(ib0)
    dm0 = pb.DataModel(pb.get_ibis_model_ecdtools(str(ib0)), model_name=m0, component_name=c0)
    d["cc_declared"] = float(dm0.c_comp[0]) * 1e12
    check("part 5 C_comp declared (pF)", d["cc_declared"], 5.0, 0.05)
    check("part 5 C_comp estimated (pF)", d["cc_estimated"], 2.64, 0.01)
    t1, ku1, pad1 = b24._cand(b24.CAND[b24.PICK], "d810")
    d["pd_t"], d["pd_si"] = thin(t_si, si, lo=-0.5, hi=3.0)
    _, d["pd_nat"] = thin(t_nat, pad_nat, lo=-0.5, hi=3.0)
    _, d["pd_mo"], d["pd_ku"] = thin(t1, pad1, ku1, lo=-0.5, hi=3.0)
    d["pd_err_nat"] = float(e_nat)
    d["pd_err_mo"] = float(b24._peak_err(t1, pad1, t_si, si, 0.81)[0])
    check("part 5 model peak error (%)", d["pd_err_mo"], -2, 1.0)

    # ------------------------------------------------------------ part 6: what the file fixes
    P = np.load(DOC / "fit_search_fileonly" / "paths.npz")
    L = np.load(DOC / "fit_search_fileonly" / "landscape.npz")
    end = P["end_2"]
    d["ft_prm"], d["ft_rms"], d["ft_vt_bound"] = end[:3], float(end[3]), float(L["vt_bound"])
    d["ft_land_s_up"], d["ft_land_vt"], d["ft_land_rms"] = L["s_up"], L["vt"], L["rms_sup_vt"]
    check("part 6 fitted s_up", end[0], 2.552, 0.002)
    check("part 6 fitted s_dn", end[1], 2.694, 0.002)
    check("part 6 fitted v_t", end[2], 0.700, 0.001)
    check("part 6 fit rms", end[3], 0.023, 0.001)
    assert abs(end[0] - p["s_up"]) < 1e-3 and abs(end[1] - p["s_dn"]) < 1e-3, "paths.npz end_2 differs from EX2"
    su, sd, vt0 = round(p["s_up"], 2), round(p["s_dn"], 2), round(p["vt_fit"], 2)
    steps = ((8.0, 8.0, 0.40), (su, 8.0, 0.40), (su, sd, 0.40), (su, sd, vt0))
    ys, rr = [], []
    for s_up, s_dn, vt in steps:
        y = figs.prior(figs.chain_stages(u_full, s_up, s_dn, vt, 0.45, 3)[-1], vtm, am)
        ys.append(np.interp(d["gk_t"], t4, y))
        rr.append(float(np.sqrt(np.mean((y - target) ** 2))))
    d["ft_steps"], d["ft_steps_prm"], d["ft_steps_rms"] = np.array(ys), np.array(steps), np.array(rr)
    # the ambiguity: two maps fitted to the same file, driven by the 810 ps pulse (as fig_ambiguity)
    for tag, (vm, a_) in (("late", (0.6, 0.6)), ("early", (0.4, 0.6))):
        r = json.loads((DOC / "shape_fileonly" / f"shape_ex2_{vm:g}_{a_:g}.json").read_text())
        g = figs.chain_stages(u_full, r["s_up"], r["s_dn"], r["vt"], 0.45, 3)[-1]
        g810 = figs.chain_stages(u_cut, r["s_up"], r["s_dn"], r["vt"], 0.45, 3)[-1]
        d[f"am_{tag}_map"] = figs.prior(gg, vm, a_)
        _, d[f"am_{tag}_ku"], d[f"am_{tag}_ku810"] = thin(t4, figs.prior(g, vm, a_), figs.prior(g810, vm, a_), n=600, lo=-0.3, hi=4.6)
        d[f"am_{tag}_vt"], d[f"am_{tag}_rms"] = float(r["vt"]), float(r["rms"])
        d[f"am_{tag}_peak810"] = float(figs.prior(g810, vm, a_).max())
        d[f"am_{tag}_shape"] = np.array([vm, a_])
    d["am_g"] = gg
    check("part 6 late map rms", d["am_late_rms"], 0.0241, 0.0002)
    check("part 6 early map rms", d["am_early_rms"], 0.0233, 0.0002)
    check("part 6 late map Ku peak at 810 ps", d["am_late_peak810"], 0.26, 0.02)
    check("part 6 early map Ku peak at 810 ps", d["am_early_peak810"], 0.0, 0.01)
    step1 = next(r for r in csv.DictReader((SC / "step1_summary.csv").open())
                 if r["pass_"] == "est_knee" and r["buffer"] == "ex2" and r["chain"] == "pull-up")
    d["rms_by_K"] = np.array([float(x) for x in step1["rms_by_K"].split()])
    check("part 6 K=3 residual", d["rms_by_K"][2], 0.0233, 0.0002)
    check("part 6 K=4 residual", d["rms_by_K"][3], 0.0231, 0.0002)
    check("part 6 K=5 residual", d["rms_by_K"][4], 0.0220, 0.0002)
    # the nine candidates before and after calibration, the bisection, the five widths
    names, pre, post = [], [], []
    for (k, sh), folder in b24.CAND.items():
        zz = np.load(DOC / "before_calibration" / f"K{k}_{sh}.npz")
        tt9, y = thin(zz["t"], zz["pad"], lo=0.2, hi=3.0)
        tp, _ku, pad = b24._cand(folder, "d810")
        _, y1 = thin(tp, pad, lo=0.2, hi=3.0)
        names.append(f"K{k} {sh.replace('_', '/')}")
        pre.append(y)
        post.append(y1)
    d["c_t"], d["c_names"], d["c_pre"], d["c_post"] = tt9, np.array(names), np.array(pre), np.array(post)
    d["c_pick"] = names.index(f"K{b24.PICK[0]} {b24.PICK[1].replace('_', '/')}")
    check("part 6 lowest candidate peak before calibration (V)", d["c_pre"].max(axis=1).min(), 0.01, 0.01)
    check("part 6 highest candidate peak before calibration (V)", d["c_pre"].max(axis=1).max(), 1.28, 0.01)
    cz = np.load(DOC / "calib_iterations" / "ex2.npz", allow_pickle=True)
    its = [i for i, n in enumerate(cz["names"]) if str(n).startswith("it")]
    d["bi_names"] = np.array([str(cz["names"][i]) for i in its])
    d["bi_vt"], d["bi_err"] = cz["vt"][its], cz["err"][its]
    d["bi_t"], *pads = thin(cz["t"] - 5.0, *[cz["pads"][i] for i in its], lo=0.2, hi=3.0)
    d["bi_pads"] = np.array(pads)
    rows = list(csv.DictReader((ROOT / "results/selector_from_one_run_2026-09-23/selector_builds.csv").open()))
    rms9, worst9 = [], []
    for n in names:
        k = int(n[1]); vm, a_ = n.split()[1].split("/")
        r = next(r for r in rows if r["buffer"] == "ex2" and int(r["K"]) == k and r["vt"] == vm and r["alpha"] == a_)
        rms9.append(float(r["pad_rms_at_calib_mV"]))
        worst9.append(float(r["worst_peak_pct"]))
    d["c_rms"], d["c_worst"] = np.array(rms9), np.array(worst9)
    d["cl_worst"] = float(worst9[d["c_pick"]])
    check("part 7 worst peak error of the selected model (%)", d["cl_worst"], 8.3, 0.05)
    assert int(np.argmin(rms9)) == d["c_pick"], "the waveform rms does not select the PICK candidate"
    folder = b24.CAND[b24.PICK]
    wsi, wmo = [], []
    for wp in b24.DEV["ex2"][3]:
        ts_, s_, _ = f17.transistor_pad("ex2", wp)
        tq, sq = thin(ts_ - 5.0, s_, lo=0.2, hi=3.0)
        tp, _ku, pad = b24._cand(folder, f"d{wp}")
        _, mq = thin(tp, pad, lo=0.2, hi=3.0)
        wsi.append(sq); wmo.append(mq)
    d["w_widths"] = np.array(b24.DEV["ex2"][3])
    d["w_t"], d["w_si"], d["w_mo"] = tq, np.array(wsi), np.array(wmo)

    np.savez(OUT / "model_data.npz", **d)
    print(f"wrote {OUT / 'model_data.npz'}: {len(d)} arrays")
    print("storyboard numbers against the stored results:")
    print("\n".join(CHECKS))
    print(f"  chain handovers {d['ch_handover'][0]:.3f}, {d['ch_handover'][1]:.3f} ns; gate at 0.99: {d['ch_t_rail']:.2f} ns; "
          f"810 ps peaks {d['ch_peak_810'].round(3)} at {d['ch_tpeak_810'].round(2)} ns; probed gate peak {d['ch_real_peak']:.3f}; "
          f"lead {d['ch_lead_ps']:.0f} ps, return {d['ch_return_ps']:.0f} ps")
    print(f"  rms vs file: fitted chain {d['gk_rms_fit']:.4f}, calibrated chain {d['gk_rms_cal']:.4f}; "
          f"fit steps rms {d['ft_steps_rms'].round(3)}; bucket events {d['b_events'].round(3)}")
    print(f"  bisection: " + ", ".join(f"{n} vt {v:.3f} err {e:+.0f}%" for n, v, e in zip(d["bi_names"], d["bi_vt"], d["bi_err"])))
    print(f"  device alphas: " + ", ".join(f"{n} {a:.2f}" for n, a in zip(d['dev_names'], d['dev_alphas'])) + f"; nch_tn x0 {d['dev_x0']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
