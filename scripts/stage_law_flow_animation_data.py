#!/usr/bin/env python3
"""Collect the data behind the stage-law flow animation (scripts/stage_law_flow_animation.py).

Everything the animation draws is a stored result of the project; this script gathers it into
one file so that the manim scene needs no simulator and no project imports:

    the problem        ex2's full transition and its 810 ps pulse, transistor against native IBIS
                       (build_0917_deck_figures / the stress matrix)
    one stage          the step response of (19) for a few rates and thresholds
    the target         ex2's IBIS tables and V-T waveforms, the converter's solved Ku/Kd, the
                       shipped model's full-swing Ku, the normalised target (25)
    the fit            the file's Ku(t) against the chain + map for the fitted and for varied
                       numbers; the residual landscape and the three search paths (fit_search.py)
    the ambiguity      two maps, same full swing, opposite 810 ps answers (shape_from_file)
    the measurement    ex2's nine candidates before and after calibration, the bisection
                       iterations (calib_iterations.py), the selected model at five widths
    the result         worst stressed peak error on the twelve buffers, proposed and native

Output: results/stage_law_flow_animation_2026-10-15/data/flow_data.npz

    py -3.14 scripts/stage_law_flow_animation_data.py
"""
from __future__ import annotations

import json
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
import predriver_stage_probe as psp  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402

OUT = ROOT / "results" / "stage_law_flow_animation_2026-10-15" / "data"
DOC = ROOT / "results" / "stage_law_doc_2026-10-01"


def thin(t, *ys, n=400, lo=None, hi=None):
    """Resample onto n points of [lo, hi] (the animation needs no more)."""
    t = np.asarray(t, float)
    lo = t[0] if lo is None else lo
    hi = t[-1] if hi is None else hi
    g = np.linspace(lo, hi, n)
    return (g,) + tuple(np.interp(g, t, np.asarray(y, float)) for y in ys)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    d = {}
    gp.VARIANT_NAME = "ex2"

    # ---- the problem
    full = psp.parse_tr0(cl.ST / "ex2" / "full" / "run.tr0")
    tf = np.asarray(full["time"], float) * 1e9 - 5.0
    sig = psp.signals(full, ["v(in_dig)", "v(pad_sp)"])
    d["p_t"], d["p_in"], d["p_pad"] = thin(tf, sig["v(in_dig)"], sig["v(pad_sp)"], lo=-0.5, hi=6.0)
    t_si, si, _ = f17.transistor_pad("ex2", 810)
    t_si = t_si - 5.0
    nat = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / "ex2_short_high_w810ps.csv")
    d["s_t"], d["s_si"] = thin(t_si, si, lo=-0.5, hi=3.0)
    _, d["s_nat"] = thin(nat["time_ns"] - 5.0, nat["hspice_pad"], lo=-0.5, hi=3.0)
    d["s_nat_err"] = b24._peak_err(nat["time_ns"] - 5.0, nat["hspice_pad"], t_si, si, 0.81)[0]
    d["s_peak"] = float(si[(t_si >= 0.51) & (t_si <= 3.4)].max())

    # ---- one stage: step responses
    ts = np.arange(-0.1, 2.0, cl.DT)
    step = (ts >= 0).astype(float)
    d["st_t"] = ts
    d["st_u"] = step
    for s_up in (1.0, 2.0, 4.0):
        d[f"st_sup{s_up:g}"] = cl.simulate(step, s_up, s_up, 0.3, 0.45, 1.0)
    for vt in (0.1, 0.5):
        d[f"st_vt{vt:g}"] = cl.simulate(step, 2.0, 2.0, vt, 0.45, 1.0)

    # ---- the target (ex2, measured C_comp 1.7 pF: the fit example of the document)
    base = ROOT / "results" / "gate_cascade_prototype_2026-09-09" / "ex2_c1.7"
    ib = base / "input_ccomp.ibs"
    m, c = gp.ibis_names(ib)
    dm = pb.DataModel(pb.get_ibis_model_ecdtools(str(ib)), model_name=m, component_name=c)
    vdd = float(dm.v_range[0])
    v = np.linspace(-0.5, vdd + 1.0, 200)
    d["iv_v"] = v
    d["iv_pu"] = -np.interp(vdd - v, dm.iv_pullup[:, 0], dm.iv_pullup[:, 1]) * 1e3
    d["iv_pd"] = np.interp(v, dm.iv_pulldown[:, 0], dm.iv_pulldown[:, 1]) * 1e3
    for i, wf in enumerate(dm.vt_rising):
        d[f"vt_t"], d[f"vt_r{i}"] = thin(wf.data[:, 0] * 1e9, wf.data[:, 1], lo=0, hi=8)
    for i, wf in enumerate(dm.vt_falling):
        _, d[f"vt_f{i}"] = thin(wf.data[:, 0] * 1e9, wf.data[:, 1], lo=0, hi=8)
    kr = pb.solve_k_params_output(dm, 1, "Rising")
    d["k_tau"], d["k_ku"], d["k_kd"] = thin(kr[:, 0] * 1e9, kr[:, 1], kr[:, 2], lo=0, hi=8)
    grid, u, target, t_on = figs.shipped_target("ex2", base / "shipped" / "full" / "run.raw")
    raw = sl.parse_ngspice_raw(base / "shipped" / "full" / "run.raw")
    tfull = sl.time_ns(raw)
    d["m_t"], d["m_ku"], d["m_kd"] = thin(tfull - 5.0, sl.signal(raw, "v(x1.kugate_base)"),
                                          sl.signal(raw, "v(x1.kdgate_base)"), lo=-1, hi=16)
    d["g_t"] = grid - t_on
    d["g_u"] = u
    d["g_target"] = target

    # ---- the fit: the chain + map for the fitted numbers, and for the knobs
    p = figs.EX2
    vt_m, a_m = p["shape"]
    d["fit_prm"] = np.array([p["s_up"], p["s_dn"], p["vt_fit"]])
    d["map_vt_a"] = np.array([vt_m, a_m])

    def model(s_up, s_dn, vt, K=3):
        nodes = figs.chain_stages(u, s_up, s_dn, vt, 0.45, K)
        return nodes, figs.prior(nodes[-1], vt_m, a_m)

    nodes, ku = model(p["s_up"], p["s_dn"], p["vt_fit"])
    d["fit_nodes"] = np.array(nodes)
    d["fit_ku"] = ku
    d["fit_rms"] = float(np.sqrt(np.mean((ku - target) ** 2)))
    knobs = {"s_up": [(1.1, p["s_dn"], p["vt_fit"]), (4.4, p["s_dn"], p["vt_fit"])],
             "s_dn": [(p["s_up"], 1.06, p["vt_fit"]), (p["s_up"], 4.2, p["vt_fit"])],
             "vt": [(p["s_up"], p["s_dn"], 0.30), (p["s_up"], p["s_dn"], 0.65)]}
    for name, vals in knobs.items():
        for j, prm in enumerate(vals):
            _, y = model(*prm)
            d[f"knob_{name}_{j}"] = y
            d[f"knob_{name}_{j}_rms"] = float(np.sqrt(np.mean((y - target) ** 2)))
            d[f"knob_{name}_{j}_prm"] = np.array(prm)
    _, y0 = model(8.0, 8.0, 0.4)
    d["guess_ku"], d["guess_rms"] = y0, float(np.sqrt(np.mean((y0 - target) ** 2)))
    # one stage against three
    r1 = {int(r["K"]): r for r in __import__("csv").DictReader(
        (ROOT / "results/stage_count_from_file_2026-09-21/step1/as_track1__ex2__pull-up.csv").open())}[1]
    _, y1 = model(float(r1["s_up"]), float(r1["s_dn"]), float(r1["vt"]), K=1)
    d["k1_ku"], d["k1_rms"] = y1, float(r1["rms"])
    # the landscape and the paths
    L = np.load(DOC / "fit_search" / "landscape.npz")
    P = np.load(DOC / "fit_search" / "paths.npz")
    for k in L.files:
        d[f"land_{k}"] = L[k]
    for s0 in (2, 8, 30):
        lg = P[f"log_{s0}"]
        best = np.minimum.accumulate(lg[:, 3])
        idx = [0] + [i for i in range(1, len(lg)) if best[i] < best[i - 1]]
        d[f"path_{s0}"] = lg[idx]
        d[f"end_{s0}"] = P[f"end_{s0}"]

    # ---- the ambiguity: two maps fitted to the same file, driven by the 810 ps pulse
    u810 = ((grid >= t_on) & (grid < t_on + 0.81)).astype(float)
    for tag, (vm, am) in (("late", (0.6, 0.6)), ("early", (0.4, 0.6))):
        r = json.loads((DOC / "shape_from_file" / f"shape_ex2_{vm}_{am}.json").read_text())
        g = figs.chain_stages(u, r["s_up"], r["s_dn"], r["vt"], 0.45, 3)[-1]
        g810 = figs.chain_stages(u810, r["s_up"], r["s_dn"], r["vt"], 0.45, 3)[-1]
        gg = np.linspace(0, 1, 200)
        d[f"amb_{tag}_map"] = figs.prior(gg, vm, am)
        d[f"amb_{tag}_gate"] = g
        d[f"amb_{tag}_ku"] = figs.prior(g, vm, am)
        d[f"amb_{tag}_ku810"] = figs.prior(g810, vm, am)
        d[f"amb_{tag}_vt"] = r["vt"]
        d[f"amb_{tag}_rms"] = r["rms"]
    d["amb_g"] = np.linspace(0, 1, 200)

    # ---- the measurement: nine candidates before/after calibration, the bisection, five widths
    names, pre, post = [], [], []
    for (k, sh), folder in b24.CAND.items():
        z = np.load(DOC / "before_calibration" / f"K{k}_{sh}.npz")
        tt, y = thin(z["t"], z["pad"], lo=0.2, hi=3.0)
        t1, _ku, pad = b24._cand(folder, "d810")
        _, y1 = thin(t1, pad, lo=0.2, hi=3.0)
        names.append(f"K{k} {sh.replace('_', '/')}")
        pre.append(y)
        post.append(y1)
    d["c_t"], d["c_names"], d["c_pre"], d["c_post"] = tt, np.array(names), np.array(pre), np.array(post)
    d["c_pick"] = names.index(f"K{b24.PICK[0]} {b24.PICK[1].replace('_', '/')}")
    cz = np.load(DOC / "calib_iterations" / "ex2.npz", allow_pickle=True)
    its = [i for i, n in enumerate(cz["names"]) if str(n).startswith("it")]
    d["b_vt"] = cz["vt"][its]
    d["b_err"] = cz["err"][its]
    d["b_t"], *pads = thin(cz["t"] - 5.0, *[cz["pads"][i] for i in its], lo=0.2, hi=3.0)
    d["b_pads"] = np.array(pads)
    dense = [i for i, n in enumerate(cz["names"]) if not str(n).startswith("it")]
    order = np.argsort(cz["vt"])
    d["b_curve_vt"], d["b_curve_err"] = cz["vt"][order], cz["err"][order]
    sel = {r["buffer"]: r for r in __import__("csv").DictReader(
        (ROOT / "results/selector_from_one_run_2026-09-23/selector_builds.csv").open())}
    rows = list(__import__("csv").DictReader((ROOT / "results/selector_from_one_run_2026-09-23/selector_builds.csv").open()))
    rms29 = []
    for n in names:
        k = int(n[1]); vm, am = n.split()[1].split("/")
        r = next(r for r in rows if r["buffer"] == "ex2" and int(r["K"]) == k and r["vt"] == vm and r["alpha"] == am)
        rms29.append(float(r["pad_rms_at_calib_mV"]))
    d["c_rms29"] = np.array(rms29)
    folder = b24.CAND[b24.PICK]
    wt, wsi, wmo = [], [], []
    for wp in b24.DEV["ex2"][3]:
        ts_, s_, _ = f17.transistor_pad("ex2", wp)
        tq, sq = thin(ts_ - 5.0, s_, lo=0.2, hi=3.0)
        t1, _ku, pad = b24._cand(folder, f"d{wp}")
        _, mq = thin(t1, pad, lo=0.2, hi=3.0)
        wsi.append(sq); wmo.append(mq)
    d["w_widths"] = np.array(b24.DEV["ex2"][3])
    d["w_t"], d["w_si"], d["w_mo"] = tq, np.array(wsi), np.array(wmo)

    # ---- the result on twelve buffers
    devs, natv, t1v, dead = figs.fig_pad_summary()
    d["r_devs"], d["r_native"], d["r_proposed"], d["r_dead"] = (np.array(devs), np.array(natv, float),
                                                               np.array(t1v, float), np.array(dead))
    np.savez(OUT / "flow_data.npz", **d)
    print(f"wrote {OUT / 'flow_data.npz'}: {len(d)} arrays; fit rms {d['fit_rms']:.4f}, native {d['s_nat_err']:+.0f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
