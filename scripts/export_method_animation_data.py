#!/usr/bin/env python3
"""Export the data behind the method film to plain arrays.

The manim environment is a separate interpreter with none of this project's readers, so a
scene cannot open the simulation runs itself. This dumps everything an animation needs into a
single .npz of plain numpy arrays, from real runs only:

    stage_*      the predriver nodes on one full-swing run, each normalised to its own rest
                 and full-swing level, so the pulse can be watched moving down the chain
    fit_*        the Nelder-Mead trial sequence fitting four stage numbers to one full-swing
                 recording: the target, and the chain output at each improving trial
    bis_*        the ten iterations the threshold bisection actually wrote, with the threshold
                 recovered from each emitted netlist
    map_*        the two fixture runs, the Ku and Kd solved from them at each instant, and the
                 gate node at the same instants
    slv_*        ONE instant in full detail: both pad voltages, the I-V curves the two
                 multipliers are read off, the term-by-term right-hand sides, and the answer.
                 This is the beat that shows WHY two loads are enough to solve for two unknowns
    cmp_*        the measured Ku map against the analytic prior track 1 uses from the file
    pay_*        the payoff at the 810 ps stressed pulse: transistor, the file-only build, and
                 the build that uses the measured maps

Each block is independent: a failure prints and continues, so one bad path does not cost the
whole export. A missing key then fails loudly in the scene rather than silently drawing nothing.

    py -3.14 scripts/export_method_animation_data.py
"""
from __future__ import annotations

import csv
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_chain_prototype as gc  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import silicon_map_replay as smr  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import (  # noqa: E402
    solve_silicon_kukd, FixtureWaveform, R_FIXTURE, CORNER,
)

OUT = ROOT / "results" / "method_animations_2026-09-17"
CH = ROOT / "results" / "gate_chain_prototype_2026-09-10" / "ex2_c1.7"
CASC = ROOT / "results" / "gate_cascade_prototype_2026-09-09" / "ex2_c1.7"
DELAY = ROOT / "results" / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
CAL = CH / "ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810/calib"
GATE, K, T_ON = "v(xdut.n4)", 3, 5.0 + 0.050 / 2

# ex2's fitted prior, the one the file-only build is named after.
PRIOR_VT, PRIOR_ALPHA = 0.57, 0.64

# Filled by fit_data, reused by knob_data: the fitted stage numbers and the stimulus they
# were fitted against. Keeps the knob sweep on exactly the fit's own grid without refitting.
BEST = {}


def ex2_model():
    """The IBIS model as every solve here sees it, with C_comp at the measured 1.7 pF."""
    sup, ibis = gp.VARIANTS["ex2"]
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)),
                        model_name=model, component_name=comp)
    data.c_comp = [1.7e-12] * 3
    return sup, data


def fixtures():
    lo = smr.fixture(smr.FSFIX / "ex2/vfix_0/run.tr0")
    hi = smr.fixture(smr.FSFIX / "ex2/vfix_vcc/run.tr0")
    return lo, hi


# --------------------------------------------------------------------------- beat 2
def stage_data():
    """Every predriver node on the full-swing run, each normalised to its own levels.

    Normalising per node is the convention the rest of the study uses: it maps rest to 0 and
    the settled full-swing level to 1, so an inverting stage still reads as a rising edge and
    what the eye picks up is the DELAY accumulating down the chain.
    """
    full = psp.parse_tr0(psp.OUT / "ex2/full/run.tr0")
    tf = np.asarray(full["time"], float) * 1e9
    nodes = list(psp.STAGES["ex2"])
    vf = psp.signals(full, nodes)
    grid = np.arange(4.75, 8.51, 0.004)
    rows = []
    for n in nodes:
        g, _, _ = psp.normalise(tf, vf[n], tf, vf[n])
        rows.append(np.interp(grid, tf, g))
    print("    stages: %d nodes %s" % (len(nodes), nodes))
    # Unicode dtype, never object: np.load refuses a pickled array without allow_pickle,
    # so an object array here would crash the scene on first access.
    return dict(stage_t=grid - 5.0, stage_v=np.array(rows),
                stage_names=np.array(nodes))


# --------------------------------------------------------------------------- beat 3
def fit_data():
    full = psp.parse_tr0(psp.OUT / "ex2/full/run.tr0")
    tf = np.asarray(full["time"], float) * 1e9
    vf = psp.signals(full, psp.STAGES["ex2"])
    g_full, _, _ = psp.normalise(tf, vf[GATE], tf, vf[GATE])
    grid = np.arange(4.0, 21.0, cl.DT)
    u = ((grid >= T_ON) & (grid < T_ON + 10.0)).astype(float)
    v = np.interp(grid, tf, g_full)

    trials = []

    def cost(z):
        s_up, s_dn = float(np.exp(z[0])), float(np.exp(z[1]))
        vt, x_lin = float(z[2]), float(z[3])
        if not (0.0 <= vt <= 0.7 and 0.02 <= x_lin <= 1.5):
            return 9.0
        y = cl.simulate_chain(u, [(s_up, s_dn, vt, x_lin, 1.0)] * K)
        r = float(np.sqrt(np.mean((y - v) ** 2)))
        trials.append((r, (s_up, s_dn, vt, x_lin), y))
        return r

    cl.nelder_mead(cost, np.array([np.log(8.0), np.log(8.0), 0.40, 0.40]),
                   step=[0.7, 0.7, 0.15, 0.15], maxiter=400)

    best, seq = 9.0, []
    for r, prm, y in trials:
        if r < best:
            best = r
            seq.append((r, prm, y))
    keep = np.unique(np.linspace(0, len(seq) - 1, min(40, len(seq))).astype(int))
    seq = [seq[i] for i in keep]
    # BOTH edges. The cost above is the r.m.s. over the whole 4..21 ns grid with the input
    # high from 5.025 to 15.025, so the falling edge is in the residual too - it is what
    # constrains s_dn. Cropping this window to the rise misrepresents the fit as one-sided.
    m = (grid - 5 >= -0.4) & (grid - 5 <= 13.0)
    st = 2  # 2 ps native; 4 ps is ample for display and halves the array
    print("    fit: %d trials, %d improving frames kept, final rms %.4f, window %.1f..%.1f ns"
          % (len(trials), len(seq), seq[-1][0], (grid - 5)[m][0], (grid - 5)[m][-1]))
    BEST.update(prm=seq[-1][1], grid=grid, u=u, target=v)
    return dict(
        fit_t=(grid - 5)[m][::st],
        fit_target=v[m][::st],
        fit_curves=np.array([y[m][::st] for _, _, y in seq]),
        fit_rms=np.array([r for r, _, _ in seq]),
        fit_params=np.array([prm for _, prm, _ in seq]),
        fit_on_ns=np.array([0.0, 10.0]),  # input rises at 0, falls at +10 on this axis
    )


# --------------------------------------------------------------------------- "why four?"
def knob_data():
    """Each stage number swept alone, the other three held at their fitted values.

    This is the answer to "why four numbers": each one moves the stage output in a way the
    other three cannot reproduce, so none of them is redundant. s_up and s_dn set how hard
    the stage drives each way, vt where it starts responding at all, and x_lin how much of
    the swing is resistive rather than current-limited.
    """
    if "prm" not in BEST:
        print("    knobs: SKIPPED (fit_data did not run)")
        return {}
    base = [float(x) for x in BEST["prm"]]
    grid, u = BEST["grid"], BEST["u"]
    # Out to 13 ns so the falling edge finishes on screen. Cut at 11.5 the curves are still
    # descending through ~0.15, which undercuts the very point these panels make about s_dn.
    m = (grid - 5 >= -0.4) & (grid - 5 <= 13.0)
    st = 2
    names = ["s_up", "s_dn", "vt", "x_lin"]
    factors = [0.35, 0.60, 1.00, 1.70, 2.80]
    # vt gets an explicit ladder rather than the multiplicative factors: it is bounded near
    # 0.85, so the top two factors both clip there and two of the five curves come out
    # identical - fatal in a beat whose whole point is that each knob does something distinct.
    VT = [0.15, 0.30, None, 0.68, 0.82]
    out = {"knob_t": (grid - 5)[m][::st], "knob_names": np.array(names),
           "knob_base": np.array(base)}
    for i, nm in enumerate(names):
        vals, rows = [], []
        for j, f in enumerate(factors):
            p = list(base)
            if nm == "vt":
                p[i] = base[i] if VT[j] is None else float(VT[j])
            else:
                p[i] = float(base[i] * f)
            vals.append(p[i])
            rows.append(cl.simulate_chain(u, [(p[0], p[1], p[2], p[3], 1.0)] * K)[m][::st])
        out["knob_%s_v" % nm] = np.array(vals)
        out["knob_%s_y" % nm] = np.array(rows)
        print("    knob %-6s base %.3f -> %s" % (nm, base[i], " ".join("%.2f" % x for x in vals)))

    # WHY THE THRESHOLD NEEDS A STRESS RUN. vt swept on an 810 ps pulse, same ladder as
    # above. On the full swing every stage is driven all the way regardless of where it
    # starts responding, so the five vt curves nearly coincide and the fit cannot tell them
    # apart. On a pulse cut short the stages are caught mid-flight, and vt decides how far
    # the gate gets before turning round - the curves fan wide.
    u_short = ((grid >= T_ON) & (grid < T_ON + 0.810)).astype(float)
    ms = (grid - 5 >= -0.4) & (grid - 5 <= 3.0)
    rows_s = []
    for j in range(len(factors)):
        p = list(base)
        p[2] = base[2] if VT[j] is None else float(VT[j])
        rows_s.append(cl.simulate_chain(u_short, [(p[0], p[1], p[2], p[3], 1.0)] * K)[ms][::st])
    out["stress_t"] = (grid - 5)[ms][::st]
    out["stress_vt_y"] = np.array(rows_s)
    out["stress_vt_v"] = np.array(out["knob_vt_v"])
    full_y = np.array(out["knob_vt_y"])
    full_rms = float(np.sqrt(np.mean((full_y[0] - full_y[-1]) ** 2)))
    short_pk = np.array(rows_s).max(axis=1)
    print("    stress: vt %.2f..%.2f  full-swing rms between extremes %.3f  |  810 ps peaks %s"
          % (out["knob_vt_v"][0], out["knob_vt_v"][-1], full_rms,
             " ".join("%.2f" % x for x in short_pk)))
    return out


# --------------------------------------------------------------------------- beat 4
def bisection_data():
    gp.VARIANT_NAME = "ex2"
    depth, w, case = [c for c in gp.cases("ex2") if c[0] == 810][0]
    t_si, si = gp.tr0_pad(case / "run.tr0")
    rev = 5.0 + w
    g = np.arange(rev - 0.7, rev + 2.6, 0.002)
    vts, curves = [], []
    for d in sorted(CAL.glob("it*")):
        txt = (d / "driver.sub").read_text(encoding="utf-8")
        vts.append(float(re.search(r"V\(CHIN\) - ([0-9.]+)", txt).group(1)))
        raw = sl.parse_ngspice_raw(d / "run.raw")
        curves.append(np.interp(g, sl.time_ns(raw), sl.trace(raw, "out")))
    tgt = np.interp(g, t_si, si)
    print("    bisection: %d iterations, target peak %.4f V" % (len(vts), tgt.max()))
    return dict(bis_t=g - rev, bis_target=tgt, bis_curves=np.array(curves),
                bis_vt=np.array(vts), bis_width_ps=np.array([w * 1e3]))


# --------------------------------------------------------------------------- beats 5, 7
def map_data():
    sup, data = ex2_model()
    lo, hi = fixtures()
    s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
    ts, ku, kd = s[:, 0] * 1e9, s[:, 1], s[:, 2]
    tg, gg = gr.real_gate("ex2", 0, GATE)
    gate = np.interp(ts, tg, gg)
    m = (ts >= 4.9) & (ts <= 7.6)
    tl, vl = np.asarray(lo[:, 0], float) * 1e9, np.asarray(lo[:, 1], float)
    th, vh = np.asarray(hi[:, 0], float) * 1e9, np.asarray(hi[:, 1], float)
    ml, mh = (tl >= 4.9) & (tl <= 7.6), (th >= 4.9) & (th <= 7.6)
    print("    map: %d solved instants in the window" % int(m.sum()))
    return dict(map_t=ts[m], map_ku=ku[m], map_kd=kd[m], map_gate=gate[m],
                map_lo_t=tl[ml], map_lo_v=vl[ml], map_hi_t=th[mh], map_hi_v=vh[mh])


# --------------------------------------------------------------------------- beat 6
def iv_curves(ibis, vcc, n=240):
    """The pullup and pulldown tables as the solve sees them, versus pad voltage.

    Same call the per-instant lookup makes, just swept over the rail instead of over a
    waveform, so the curve drawn on screen is the curve being read from.
    """
    v = np.linspace(0.0, vcc, n)
    pu_ref = pb.get_reference(ibis.pullup_ref, ibis.v_range, CORNER)
    pd_ref = pb.get_reference(ibis.pulldown_ref, 0, CORNER)
    pu = pb.get_current_data_from_iv_data(v, ibis.iv_pullup, pu_ref, CORNER,
                                          iv_data_adjust=ibis.iv_pwr_clamp)
    pd = pb.get_current_data_from_iv_data(v, ibis.iv_pulldown, pd_ref, CORNER,
                                          iv_data_adjust=ibis.iv_gnd_clamp)
    return v, pu, pd


def solve_data():
    """One representative instant, in enough detail to show the 2x2 being formed.

    The instant is chosen where Ku is near 0.5, so both devices carry real current and
    neither row of the matrix is degenerate.
    """
    sup, data = ex2_model()
    lo, hi = fixtures()
    s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
    tsec, ku, kd, cond = s[:, 0], s[:, 1], s[:, 2], s[:, 3]
    t_ns = tsec * 1e9

    wl = FixtureWaveform(lo, [0.0, 0.0, 0.0], R_FIXTURE)
    wh = FixtureWaveform(hi, [sup] * 3, R_FIXTURE)
    pu1, pd1, pc1, gc1, rf1, cc1, cf1 = pb.generating_current_data(data, tsec, CORNER, wl)
    pu2, pd2, pc2, gc2, rf2, cc2, cf2 = pb.generating_current_data(data, tsec, CORNER, wh)
    i1 = gc1 + pc1 + rf1 - cc1 - cf1
    i2 = gc2 + pc2 + rf2 - cc2 - cf2

    win = (t_ns > 5.0) & (t_ns < 7.0) & np.isfinite(ku)
    cand = np.where(win)[0]
    idx = int(cand[int(np.argmin(np.abs(ku[cand] - 0.5)))])

    v_iv, pu_iv, pd_iv = iv_curves(data, sup)
    v_lo = float(np.interp(tsec[idx], np.asarray(lo[:, 0], float), np.asarray(lo[:, 1], float)))
    v_hi = float(np.interp(tsec[idx], np.asarray(hi[:, 0], float), np.asarray(hi[:, 1], float)))
    print("    solve: instant %.4f ns, V_lo %.3f V_hi %.3f, Ku %.3f Kd %.3f, cond %.1f"
          % (t_ns[idx], v_lo, v_hi, ku[idx], kd[idx], cond[idx]))
    return dict(
        slv_t_ns=np.array([t_ns[idx]]),
        slv_vcc=np.array([sup]),
        slv_v=np.array([v_lo, v_hi]),
        # row k of the 2x2: [pu, pd | rhs]
        slv_mat=np.array([[pu1[idx], pd1[idx]], [pu2[idx], pd2[idx]]]),
        slv_rhs=np.array([i1[idx], i2[idx]]),
        slv_terms=np.array([[rf1[idx], pc1[idx], gc1[idx], cc1[idx]],
                            [rf2[idx], pc2[idx], gc2[idx], cc2[idx]]]),
        slv_ans=np.array([ku[idx], kd[idx]]),
        slv_iv_v=v_iv, slv_iv_pu=pu_iv, slv_iv_pd=pd_iv,
    )


# --------------------------------------------------------------------------- beat 8
def compare_maps():
    """All FOUR measured maps, plus the analytic prior the file-only build uses for Ku.

    The solve yields Ku and Kd at every instant, and each is split at the gate extremum into
    an on-branch and an off-branch, so the model carries four maps, not one. Exporting only
    Ku-rise understates what the method actually builds.
    """
    sup, data = ex2_model()
    rise, fall, kd_on, kd_off = gc.silicon_maps_for("ex2", data, sup, 1.7e-12)
    g = np.asarray(rise[0], float)
    meas = np.asarray(rise[1], float)
    prior = pm.prior(g, PRIOR_VT, PRIOR_ALPHA)
    out = dict(cmp_g=g, cmp_meas=meas, cmp_prior=np.asarray(prior, float))
    for key, m in (("ku_rise", rise), ("ku_fall", fall), ("kd_on", kd_on), ("kd_off", kd_off)):
        out["map4_%s_g" % key] = np.asarray(m[0], float)
        out["map4_%s_v" % key] = np.asarray(m[1], float)
        print("    map4 %-8s grid %d, %.3f..%.3f"
              % (key, len(m[0]), float(np.min(m[1])), float(np.max(m[1]))))
    return out


# --------------------------------------------------------------------------- beat 9
def payoff_data():
    """The 810 ps stressed pulse: transistor, the shipped native model, and ours.

    The contrast that matters is against the SHIPPED model. Comparing the file-only build
    with the measured-map build at this width proves nothing, because both were calibrated
    on this very pulse's pad peak and so both land on it by construction.
    """
    gp.VARIANT_NAME = "ex2"
    depth, w, case = [c for c in gp.cases("ex2") if c[0] == 810][0]
    t_si, si = gp.tr0_pad(case / "run.tr0")
    rev = 5.0 + w
    g = np.arange(rev - 0.3, rev + 2.6, 0.002)
    out = dict(pay_t=g - rev, pay_si=np.interp(g, t_si, si))
    for key, p in (("pay_ship", CASC / "shipped" / "d810" / "run.raw"),
                   ("pay_file", CH / "ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810" / "d810" / "run.raw"),
                   ("pay_meas", CH / "real_silicon_K3_calibpad810" / "d810" / "run.raw")):
        if not p.is_file():
            print("    payoff: MISSING %s" % p)
            continue
        raw = sl.parse_ngspice_raw(p)
        out[key] = np.interp(g, sl.time_ns(raw), sl.trace(raw, "out"))
    # HSPICE's own native IBIS buffer at the same width, from the delay_cmd waveform set.
    # This is "the bar": the industry model, not ours. It fails the same way the shipped
    # pybis build does, which is the point - the failure is the approach, not a bug.
    pn = DELAY / "ex2_short_high_w810ps.csv"
    if pn.is_file():
        a = np.genfromtxt(pn, delimiter=",", names=True)
        out["pay_native"] = np.interp(g, np.asarray(a["time_ns"], float),
                                      np.asarray(a["hspice_pad"], float))
    tgt = out["pay_si"].max()
    for k in ("pay_native", "pay_ship", "pay_file", "pay_meas"):
        if k in out:
            print("    payoff: %-10s peak %+6.2f %%" % (k, 100 * (out[k].max() - tgt) / tgt))
    print("    payoff: transistor peak %.4f V" % tgt)
    return out


# --------------------------------------------------------------------------- the motivation
def why_data():
    """The shipped model on a full swing and on an 810 ps pulse, plus the gate behind it.

    The argument the film has to make is not "the file describes only half the buffer" - it is
    that the missing half only matters once a transition is interrupted. So: show the model
    landing on a full transition, then failing on a short one, then the gate that explains it.
    The real gate stops partway and turns round; the model's gate does not notice.
    """
    full = psp.parse_tr0(psp.OUT / "ex2/full/run.tr0")
    tf = np.asarray(full["time"], float) * 1e9
    vf = psp.signals(full, psp.STAGES["ex2"])
    g_full, _, _ = psp.normalise(tf, vf[GATE], tf, vf[GATE])

    sh = psp.parse_tr0(psp.OUT / "ex2/w810/run.tr0")
    tsh = np.asarray(sh["time"], float) * 1e9
    vsh = psp.signals(sh, [GATE])
    g_short, _, _ = psp.normalise(tf, vf[GATE], tsh, vsh[GATE])

    rf = sl.parse_ngspice_raw(CASC / "shipped" / "full" / "run.raw")
    rs = sl.parse_ngspice_raw(CASC / "shipped" / "d810" / "run.raw")

    # Out to 18 ns: the whole transition, rise AND fall, so the "it works" beat is framed
    # the same way as every stressed beat rather than showing only half a pulse.
    gp_ = np.arange(4.80, 18.001, 0.004)
    gg = np.arange(4.80, 8.001, 0.004)
    out = dict(
        why_pt=gp_ - 5.0,
        why_pad_si=np.interp(gp_, tf, np.asarray(vf["v(pad_sp)"], float)),
        why_pad_mo=np.interp(gp_, sl.time_ns(rf), sl.trace(rf, "out")),
        why_gt=gg - 5.0,
        why_g_si_full=np.interp(gg, tf, g_full),
        why_g_si_short=np.interp(gg, tsh, g_short),
        why_g_mo_full=np.interp(gg, sl.time_ns(rf), sl.signal(rf, "v(x1.gup)")),
        why_g_mo_short=np.interp(gg, sl.time_ns(rs), sl.signal(rs, "v(x1.gup)")),
    )
    print("    why: full-swing pad, transistor %.3f V, model %.3f V"
          % (out["why_pad_si"].max(), out["why_pad_mo"].max()))
    print("    why: gate max  transistor full %.3f short %.3f | model full %.3f short %.3f"
          % (out["why_g_si_full"].max(), out["why_g_si_short"].max(),
             out["why_g_mo_full"].max(), out["why_g_mo_short"].max()))
    return out


def clock_data():
    """The native model's Ku is a clock, not a state - measured across five pulse widths.

    This is why the hidden half has to be reconstructed at all. The native IBIS Ku replays
    the same schedule however short the pulse is, so an interrupted transition cannot be
    represented; the real gate, being a state, collapses instead.
    """
    widths = [975, 895, 858, 830, 810]
    grid = np.arange(5.80, 7.205, 0.004)
    sil, nat = [], []
    for w in widths:
        p = DELAY / ("ex2_short_high_w%dps.csv" % w)
        if not p.is_file():
            print("    clock: MISSING %s" % p)
            return {}
        a = np.genfromtxt(p, delimiter=",", names=True)
        t = np.asarray(a["time_ns"], float)
        sil.append(np.interp(grid, t, np.asarray(a["silicon_ku"], float)))
        nat.append(np.interp(grid, t, np.asarray(a["hspice_ku"], float)))
    sil, nat = np.array(sil), np.array(nat)
    print("    clock: silicon Ku peaks %s" % " ".join("%.3f" % x for x in sil.max(axis=1)))
    print("    clock: native  Ku peaks %s" % " ".join("%.3f" % x for x in nat.max(axis=1)))
    return dict(clock_t=grid, clock_w=np.array(widths, float), clock_sil=sil, clock_nat=nat)


# --------------------------------------------------------------------------- beat 8b
def map_gain():
    """What the measured map is worth, with everything else held fixed.

    This pair replays the SAME measured gate and differs in nothing but the Ku/Kd maps, so
    it isolates the map. The chain builds cannot: both are calibrated on the 810 ps pad peak
    and so land on it by construction, which makes that comparison circular.
    """
    p = CASC / "gate_replay_silicon_full" / "sweep.csv"
    if not p.is_file():
        print("    gain: MISSING %s" % p)
        return {}
    with open(p, newline="", encoding="utf-8") as fh:
        rows = {r["build"]: r for r in csv.DictReader(fh)}
    widths = [975, 895, 858, 830, 810]
    out = {"gain_w": np.array(widths, float)}
    for key, build in (("gain_ibis", "gate_replay"),
                       ("gain_meas", "gate_replay_silicon_full")):
        if build not in rows:
            print("    gain: no row for %s in %s" % (build, p.name))
            continue
        out[key] = np.array([float(rows[build]["pk_d%d" % w]) for w in widths])
        print("    gain %-10s %s" % (build, " ".join("%+5.1f" % x for x in out[key])))
    return out


# --------------------------------------------------------------------------- track 1's result
def t1_result():
    """Track 1 across all five widths, with the measured-map build beside it.

    At d810 both builds were calibrated, so that column proves nothing. The other four were
    not: there the file's Ku map costs 5-9 points against 2-4 for the measured one, while
    BOTH track the gate well. That is track 1's honest shortfall - the gate's motion is
    right, the gate-to-pad map is still the file's guess - and it is why track 2 exists.
    """
    widths = [975, 895, 858, 830, 810]
    out = {"t1_w": np.array(widths, float)}
    for key, rel in (("t1_file", "ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810"),
                     ("t1_meas", "real_silicon_K3_calibpad810")):
        p = CH / rel / "sweep.csv"
        if not p.is_file():
            print("    t1: MISSING %s" % p)
            continue
        with open(p, newline="", encoding="utf-8") as fh:
            rows = {r["build"]: r for r in csv.DictReader(fh)}
        r = rows.get(rel)
        if r is None:
            print("    t1: no row %s in %s" % (rel, p.name))
            continue
        out[key + "_pk"] = np.array([float(r["pk_d%d" % w]) for w in widths])
        out[key + "_gate"] = np.array([[float(x) for x in r["gate_d%d" % w].split("/")]
                                       for w in widths])
        print("    t1 %-8s pk   %s" % (key, " ".join("%+5.1f" % x for x in out[key + "_pk"])))
        print("    t1 %-8s gate %s" % (key, " ".join("%.2f/%.2f" % tuple(gg)
                                                       for gg in out[key + "_gate"])))
    return out


# --------------------------------------------------------------------------- result waveforms
def result_waves():
    """Pad waveforms at two widths, for a like-for-like comparison of track 1 alone against
    the full method, each over the transistor and the last gate-state.

    810 ps is where the threshold was placed, so track 1 looks right there by construction.
    895 ps was not calibrated, and is where its shortfall shows as a waveform rather than a
    number on a chart.
    """
    gp.VARIANT_NAME = "ex2"
    out = {}
    for depth, w, case in gp.cases("ex2"):
        if depth not in (810, 895):
            continue
        t_si, si = gp.tr0_pad(case / "run.tr0")
        rev = 5.0 + w
        g = np.arange(rev - 0.3, rev + 2.6, 0.002)
        out["rw_t_%d" % depth] = g - rev
        out["rw_si_%d" % depth] = np.interp(g, t_si, si)
        d = "d%d" % depth
        for key, p in (("ship", CASC / "shipped" / d / "run.raw"),
                       ("t1", CH / "ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810" / d / "run.raw"),
                       ("meas", CH / "real_silicon_K3_calibpad810" / d / "run.raw")):
            if not p.is_file():
                print("    rw: MISSING %s" % p)
                continue
            raw = sl.parse_ngspice_raw(p)
            out["rw_%s_%d" % (key, depth)] = np.interp(g, sl.time_ns(raw), sl.trace(raw, "out"))
        pk = out["rw_si_%d" % depth].max()
        print("    rw %d: transistor %.4f V | %s" % (depth, pk, "  ".join(
            "%s %+5.1f%%" % (k, 100 * (out["rw_%s_%d" % (k, depth)].max() - pk) / pk)
            for k in ("ship", "t1", "meas") if "rw_%s_%d" % (k, depth) in out)))
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print("exporting method animation data")
    d = {}
    for fn in (why_data, clock_data, stage_data, fit_data, knob_data, bisection_data,
               map_data, solve_data, compare_maps, map_gain, t1_result, result_waves,
               payoff_data):
        try:
            d.update(fn())
        except Exception:
            print("  FAILED: %s" % fn.__name__)
            traceback.print_exc()
    p = OUT / "method_data.npz"
    np.savez_compressed(p, **d)
    print("  wrote %s  (%.2f MB, %d arrays)" % (p, p.stat().st_size / 1e6, len(d)))
