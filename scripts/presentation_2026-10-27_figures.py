#!/usr/bin/env python3
"""Figures for the 2026-10-27 presentation of the stage-law paper (1027_presentation_materials.md).

Every curve is a stored run; nothing is simulated. One palette throughout: transistor black,
HSPICE native IBIS blue dashed, the stage-law model teal, the value-matched replay orange, the
file's own tables grey. Titles carry the pulse width and its depth in percent of the settled swing.

    challenge_<dev>.png        transistor against native at 50, 70, 90 % (stress matrix waveforms)
    value_match_<dev>_<w>ps.png
                               transistor, native and the value-matched replay at 50, 70 and 90 %, with
                               the instant the value is matched marked (reversal_rules_ex2_inv_chain)
    time_match_<dev>.png       the file's rising and falling K_u / K_d tables on one clock and the
                               step time matching demands at the reversal
    kstage_blocks.png          the signal path of Fig. 6 without equation numbers
    map_derivation.png         the map from the alpha-power law, four lines, Times-like face
    maps_and_shapes.png        the maps measured on the probed gates of ex2 and inv_chain, and the
                               three candidate shapes over them
    knob_sup.png, knob_sdn.png, knob_vt.png, knob_fit.png
                               one fitted number at a time (the four panels of Fig. 12 as four
                               figures; the curves are recomputed here exactly as fig_fit_knobs
                               does, because that function draws one four-panel figure)
    band_K.png                 residual of the fit against K with the band rule, ex2 and inv_chain
    fullswing_<dev>.png        the model's full-swing pad against the transistor's, the 50 % level and crossings
    result_<dev>_<w>ps.png     transistor, native and the model, one figure per buffer and width
    result_table.csv/.md       peak error and lag per width, model and native

    py -3.14 scripts/presentation_2026-10-27_figures.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import gate_ramp_prototype as gp  # noqa: E402,F401  (import order: binds pybis2spice before the deck modules)
import build_0917_deck_figures as f17  # noqa: E402
import build_0924_deck_figures as b24  # noqa: E402
import build_stage_law_doc_figures as figs  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402

OUT = ROOT / "results" / "presentation_2026-10-27"
MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
RULES = ROOT / "results" / "reversal_rules_ex2_inv_chain_2026-10-27"
DOC = ROOT / "results" / "stage_law_doc_2026-10-01"
TR, NATIVE, MODEL, VALUE, FILE, RED = "#111111", "#2B6CA3", "#0E9F9A", "#C9862B", "#8A9499", "#B0563C"
WIDTHS = {"ex2": [810, 830, 858, 895, 975], "inv_chain": [104, 106, 111, 119, 135]}
DEPTH = {"ex2": {810: 50, 830: 60, 858: 70, 895: 80, 975: 90}, "inv_chain": {104: 50, 106: 60, 111: 70, 119: 80, 135: 90}}
RC = {"font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11, "legend.fontsize": 9.5, "axes.spines.top": False,
      "axes.spines.right": False, "font.family": "DejaVu Sans"}
NAT_LS = (0, (2, 1.2))


def title(dev, w):
    return f"{dev}, {w} ps pulse ({DEPTH[dev][w]} % of the settled swing)"


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ", name)


def matrix_wave(dev, w):
    rows = list(csv.DictReader((MATRIX / f"{dev}_short_high_w{w}ps.csv").open()))
    col = lambda k: np.array([float(r[k]) for r in rows])  # noqa: E731
    return col("time_ns") - 5.0, col("silicon_pad"), col("hspice_pad")


def xlim(dev, w):
    return (w / 1000 - (0.35 if dev == "ex2" else 0.21), w / 1000 + (2.2 if dev == "ex2" else 0.45))


def peak_err(t, y, t_ref, y_ref, w_ns):
    win = lambda tt: (tt >= w_ns - 0.3) & (tt <= w_ns + 2.6)  # noqa: E731
    pk = float(y_ref[win(t_ref)].max())
    return 100.0 * (float(y[win(t)].max()) - pk) / pk


# ------------------------------------------------------------------ 1. the challenge
def challenge():
    for dev in ("ex2", "inv_chain"):
        swing = figs.settled_swing(dev)
        with plt.rc_context(RC):
            fig, ax = plt.subplots(1, 3, figsize=(12, 3.6), gridspec_kw={"wspace": 0.3})
            for a, w in zip(ax, (WIDTHS[dev][0], WIDTHS[dev][2], WIDTHS[dev][4])):
                t, si, nat = matrix_wave(dev, w)
                a.plot(t, si, color=TR, lw=2.6, label="transistor level")
                a.plot(t, nat, color=NATIVE, lw=2.0, ls=NAT_LS, label="HSPICE native IBIS")
                a.set_xlim(*xlim(dev, w)); a.set_ylim(-0.1, swing * 1.05)
                a.set_title(f"{dev}, {w} ps pulse ({DEPTH[dev][w]} % of swing)", fontsize=11)
                a.set_xlabel("time from the input edge (ns)")
                a.grid(alpha=0.25, lw=0.5)
            ax[0].set_ylabel("pad voltage (V)")
            ax[0].legend(frameon=False, loc="upper right")
            save(fig, f"challenge_{dev}.png")


# ------------------------------------------------------------------ 2. previous methods
def value_match():
    for dev in ("ex2", "inv_chain"):
        for w in (WIDTHS[dev][0], WIDTHS[dev][2], WIDTHS[dev][4]):
            rows = list(csv.DictReader((RULES / "coeff_match" / "waveforms" / f"{dev}_short_high_w{w}ps.csv").open()))
            col = lambda k: np.array([float(r[k]) for r in rows])  # noqa: E731
            t = col("time_ns") - 5.0
            si, nat, mo = col("silicon_pad"), col("hspice_pad"), col("pybis_pad")
            ku_si, ku_nat, ku_mo = col("silicon_ku"), col("hspice_ku"), col("pybis_ku")
            swing = figs.settled_swing(dev)
            wn = w / 1000.0
            with plt.rc_context(RC):
                fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"wspace": 0.3})
                a = ax[0]
                a.plot(t, si, color=TR, lw=2.6, label="transistor level")
                a.plot(t, nat, color=NATIVE, lw=2.0, ls=NAT_LS, label=f"native IBIS ({peak_err(t, nat, t, si, wn):+.0f} % peak)")
                a.plot(t, mo, color=VALUE, lw=2.2, label=f"value-matched replay ({peak_err(t, mo, t, si, wn):+.0f} % peak)")
                a.axvline(wn, color=VALUE, lw=1, ls=":")
                a.set_xlim(*xlim(dev, w)); a.set_ylim(-0.1, swing * 1.05)
                a.set_title(title(dev, w) + ": the pad", fontsize=11); a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("pad voltage (V)")
                a.legend(frameon=False, loc="upper right"); a.grid(alpha=0.25, lw=0.5)
                b = ax[1]
                b.plot(t, ku_si, color=TR, lw=2.2, label="solved from the transistor")
                b.plot(t, ku_nat, color=NATIVE, lw=1.8, ls=NAT_LS, label="native IBIS")
                b.plot(t, ku_mo, color=VALUE, lw=2.0, label="value-matched replay")
                b.axvline(wn, color=VALUE, lw=1, ls=":")
                k_at = float(np.interp(wn, t, ku_mo))
                device = next(d for d in base.DEVICES if d.device_id == dev)
                dm = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)), model_name=device.model, component_name=device.component)
                kr = pb.solve_k_params_output(dm, 1, "Rising")
                tr_ = kr[:, 0] * 1e9
                m = tr_ >= wn
                b.plot(tr_[m], kr[m, 1], color=VALUE, lw=1.6, ls=(0, (3, 2)), label="the rising table it was on, unfinished")
                b.plot([wn], [k_at], "o", color=VALUE, ms=8, zorder=6, label="reversal: value matched here")
                b.set_xlim(a.get_xlim()); b.set_ylim(-0.3, 1.35)
                b.set_title(title(dev, w) + ": $K_u$", fontsize=11); b.set_xlabel("time from the input edge (ns)"); b.set_ylabel("$K_u$")
                b.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=8.5); b.grid(alpha=0.25, lw=0.5)
                save(fig, f"value_match_{dev}_{w}ps.png")


def time_match():
    for dev_id in ("ex2", "inv_chain"):
        w = WIDTHS[dev_id][0]
        device = next(d for d in base.DEVICES if d.device_id == dev_id)
        dm = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)), model_name=device.model, component_name=device.component)
        kr = pb.solve_k_params_output(dm, 1, "Rising")
        kf = pb.solve_k_params_output(dm, 1, "Falling")
        tr, tf = kr[:, 0] * 1e9, kf[:, 0] * 1e9
        wn = w / 1000.0
        span = 3.0 if dev_id == "ex2" else 0.8
        with plt.rc_context(RC):
            fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"wspace": 0.3})
            for a, (name, cr, cf) in zip(ax, (("$K_u$", kr[:, 1], kf[:, 1]), ("$K_d$", kr[:, 2], kf[:, 2]))):
                vr, vf = float(np.interp(wn, tr, cr)), float(np.interp(wn, tf, cf))
                a.plot(tr, cr, color=MODEL, lw=2.2, label=f"{name} table of the rising edge (the file)")
                a.plot(tf, cf, color=RED, lw=2.2, ls="--", label=f"{name} table of the falling edge (the file)")
                a.annotate("", (wn, vf), (wn, vr), arrowprops=dict(arrowstyle="-|>", color=VALUE, lw=2.4, mutation_scale=16))
                a.plot([wn], [vr], "o", color=MODEL, ms=7); a.plot([wn], [vf], "o", color=RED, ms=7)
                a.text(wn + 0.04 * span, (vr + vf) / 2, f"reversal at {w} ps:\nthe clock stays, {name} jumps\nfrom {vr:.2f} to {vf:.2f}",
                       color=VALUE, fontsize=9.5, va="center")
                a.set_xlim(0, span); a.set_ylim(-0.15, 1.45)
                a.set_xlabel("time since the input edge, the table's own clock (ns)"); a.set_ylabel(name)
                a.set_title(f"{title(dev_id, w)}: {name}", fontsize=11)
                a.legend(frameon=False, loc="upper right", fontsize=8.5); a.grid(alpha=0.25, lw=0.5)
            save(fig, f"time_match_{dev_id}.png")


# ------------------------------------------------------------------ 3. the K-stage model
def kstage_blocks():
    saved = figs.OUT
    figs.OUT = OUT
    try:
        figs.fig_blocks(eq_numbers=False, name="kstage_blocks")
    finally:
        figs.OUT = saved


# ------------------------------------------------------------------ 4. the map
def map_derivation():
    lines = [
        (r"$\alpha$-power law, saturation current at gate drive $V_{GS}$:",
         r"$I'_{D0} = I_{D0}\,D^{\alpha},\qquad D = \dfrac{V_{GS} - V_{TH}}{V_{DD} - V_{TH}}$"),
        (r"the conducting fraction is the current at the present drive over the current at full drive:",
         r"$K_u \triangleq \dfrac{I(V_{GS})}{I(V_{DD})} = D^{\alpha}$"),
        (r"with the gate normalized, $g = V_{GS}/V_{DD}$, and $v_{t,map} = V_{TH}/V_{DD}$:",
         r"$D = \dfrac{g - v_{t,map}}{1 - v_{t,map}}$"),
        (r"the map, with $a$ the effective exponent of the output device and the clip for cutoff:",
         r"$M(g) = \mathrm{clip}\!\left(\dfrac{g - v_{t,map}}{1 - v_{t,map}},\,0,\,1\right)^{a},\qquad K_u = M(G_{UP})$"),
    ]
    with plt.rc_context({"font.family": "STIXGeneral", "mathtext.fontset": "stix"}):      # the paper's Times-like face
        fig = plt.figure(figsize=(10, 4.6))
        fig.patch.set_facecolor("white")
        y = 0.93
        for text, eq in lines:
            fig.text(0.03, y, text, fontsize=14, color="#222222", va="top")
            fig.text(0.10, y - 0.085, eq, fontsize=17, va="top")
            y -= 0.235
        save(fig, "map_derivation.png")


def measured_maps():
    out = {}
    for dev in ("ex2", "inv_chain"):
        folder, node, _g, widths, _y, _s = b24.DEV[dev]
        tf_, gfull, _ts, _gs = f17._norm_pair(dev, widths[0], node)
        raw = sl.parse_ngspice_raw(f17.CASC / folder / "shipped" / "full" / "run.raw")
        t_m, ku_m = sl.time_ns(raw) - 5.0, sl.signal(raw, "v(x1.ku)")
        g_end = float(tf_[np.argmax(np.asarray(gfull) >= 0.995)]) + 0.25
        tt = np.linspace(0.05, g_end, 600)
        g_t, ku_t = np.interp(tt, tf_, gfull), np.interp(tt, t_m, ku_m)
        order = np.argsort(g_t)
        out[dev] = (g_t[order], ku_t[order])
    return out


def maps_and_shapes():
    gg = np.linspace(0, 1, 400)
    measured = measured_maps()
    fitted = {"ex2": (0.57, 0.64), "inv_chain": (0.49, 0.60)}
    cols = {"ex2": TR, "inv_chain": "#666666"}
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"wspace": 0.28})
        a = ax[0]
        for dev in ("ex2", "inv_chain"):
            g, k = measured[dev]
            a.plot(g, k, color=cols[dev], lw=2.2, label=f"{dev} measured, formula fit ({fitted[dev][0]:.2f}, {fitted[dev][1]:.2f})")
        a.set_title("the map measured where the gate can be probed"); a.set_xlabel("gate $g$ (normalized)"); a.set_ylabel("$K_u$")
        a.set_xlim(0, 1.02); a.set_ylim(-0.1, 1.2); a.legend(frameon=False, loc="upper left", fontsize=9); a.grid(alpha=0.25, lw=0.5)
        b = ax[1]
        for dev, shade in (("ex2", "#BBBBBB"), ("inv_chain", "#D8D8D8")):
            g, k = measured[dev]
            b.plot(g, k, color=shade, lw=2.2, label=f"{dev} measured")
        for (v, a_), col, ls in zip(figs.SHAPES, (MODEL, NATIVE, RED), ("-", "--", "-.")):
            b.plot(gg, figs.prior(gg, v, a_), color=col, lw=2.2, ls=ls, label=f"candidate ({v:.2f}, {a_:.2f})")
        b.set_title("the three candidate shapes the method offers"); b.set_xlabel("gate $g$ (normalized)"); b.set_ylabel("$M(g)$")
        b.set_xlim(0, 1.02); b.set_ylim(-0.1, 1.2); b.legend(frameon=False, loc="upper left", fontsize=9, title="$(v_{t,map},\\ a)$"); b.grid(alpha=0.25, lw=0.5)
        save(fig, "maps_and_shapes.png")


# ------------------------------------------------------------------ 5. the fit
def knobs():
    """The four panels of fig_fit_knobs as four figures: the same chain, target and values."""
    d = np.load(DOC / "shape_fileonly" / "target_ex2.npz")
    u, target = d["u"], d["target"]
    t = np.arange(4.0, 21.0, cl.DT) - 5.025
    p = figs.EX2
    su, sd, vt0 = round(p["s_up"], 2), round(p["s_dn"], 2), round(p["vt_fit"], 2)

    def ku(s_up, s_dn, vt):
        return figs.prior(figs.chain_stages(u, s_up, s_dn, vt, p["x_lin"], 3)[-1], *p["shape"])

    def rms(y):
        return float(np.sqrt(np.mean((y - target) ** 2)))

    shades = ("#9CC8C6", MODEL, "#0B5F5C")
    panels = (("knob_sup.png", "$s_{up}$", (round(su / 2, 2), su, round(su * 2, 2)), (0, 3.0), lambda v: (v, sd, vt0), "$s_{{up}}$ = {v:g}/ns"),
              ("knob_sdn.png", "$s_{dn}$", (round(sd / 2, 2), sd, round(sd * 2, 2)), (10.0, 13.0), lambda v: (su, v, vt0), "$s_{{dn}}$ = {v:g}/ns"),
              ("knob_vt.png", "$v_t$", (0.30, 0.50, vt0), (0, 3.0), lambda v: (su, sd, v), "$v_t$ = {v:g}"))
    with plt.rc_context(RC):
        for name, ttl, vals, xr, prm, lab in panels:
            fig, a = plt.subplots(figsize=(6.4, 4.0))
            a.plot(t, target, color=TR, lw=3.2, alpha=0.35, label="the file's $K_u(t)$")
            for v, c in zip(vals, shades):
                a.plot(t, ku(*prm(v)), color=c, lw=2.0, label=lab.format(v=v))
            a.set_xlim(*xr); a.set_ylim(-0.05, 1.12); a.set_title(ttl, fontsize=13)
            a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("$K_u$")
            a.legend(frameon=False, loc="center right" if name != "knob_sdn.png" else "center left"); a.grid(alpha=0.25, lw=0.5)
            save(fig, name)
        fig, a = plt.subplots(figsize=(6.4, 4.0))
        a.plot(t, target, color=TR, lw=3.2, alpha=0.35, label="the file's $K_u(t)$")
        steps = ((8.0, 8.0, 0.40, "first guess"), (su, 8.0, 0.40, "$s_{up}$ adjusted"), (su, sd, 0.40, "$s_{dn}$ adjusted"),
                 (su, sd, vt0, "$v_t$ adjusted: the fit"))
        for (s_up, s_dn, vt, lab), c in zip(steps, ("#BBBBBB", "#888888", "#4FB3AF", RED)):
            y = ku(s_up, s_dn, vt)
            a.plot(t, y, color=c, lw=2.2 if lab.endswith("fit") else 1.6, label=f"{lab}  (rms {rms(y):.3f})")
        a.set_xlim(0, 3.0); a.set_ylim(-0.05, 1.12); a.set_title("a fit, one number at a time", fontsize=13)
        a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("$K_u$")
        a.legend(frameon=False, loc="center right"); a.grid(alpha=0.25, lw=0.5)
        save(fig, "knob_fit.png")


def band_K():
    rows = {r["buffer"]: [float(x) for x in r["rms_by_K"].split()]
            for r in csv.DictReader((ROOT / "results/stage_count_from_file_2026-09-21/step1_summary.csv").open())
            if r["pass_"] == "est_knee" and r["chain"] == "pull-up" and r["buffer"] in ("ex2", "inv_chain")}
    knet = {"ex2": 3, "inv_chain": 7}
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"wspace": 0.3})
        for a, dev in zip(ax, ("ex2", "inv_chain")):
            r = rows[dev]
            K = np.arange(1, len(r) + 1)
            thr = 1.25 * min(r)
            band = [k for k in K if r[k - 1] <= thr][:3]
            a.plot(K, r, "o-", color=MODEL, lw=2, ms=6, label="residual of the fit to the file's $K_u(t)$")
            a.axhline(thr, color=VALUE, lw=1.4, ls="--", label=f"1.25 × best = {thr:.4f}")
            a.plot(band, [r[k - 1] for k in band], "o", color=VALUE, ms=12, mfc="none", mew=2.2, label=f"band kept: K = {', '.join(map(str, band))}")
            a.plot([knet[dev]], [r[knet[dev] - 1]], "s", color=TR, ms=9, mfc="none", mew=2, label=f"netlist count K = {knet[dev]}")
            a.set_yscale("log"); a.set_xticks(K); a.set_xlabel("stage count $K$"); a.set_ylabel("residual (rms)")
            a.set_title(f"{dev}: the file does not pick one K"); a.legend(frameon=False, fontsize=9); a.grid(alpha=0.25, lw=0.5, which="both")
        save(fig, "band_K.png")


# ------------------------------------------------------------------ 6. verification: full swing
def t50(t, y):
    lo, hi = float(y[0]), float(y[-1])
    yy = (y - lo) / (hi - lo)
    i = int(np.argmax(yy >= 0.5))
    return float(np.interp(0.5, yy[i - 1:i + 1], t[i - 1:i + 1]))


def fullswing_delay():
    out = []
    for dev in ("ex2", "inv_chain"):
        full = psp.parse_tr0(cl.ST / dev / "full" / "run.tr0")
        ts, vs = np.asarray(full["time"], float) * 1e9 - 5.0, np.asarray(full["v(pad_sp)"], float)
        tm, _ku, vm = b24._cand(figs.pick_build(dev), "full")
        span = 4.0 if dev == "ex2" else 1.0
        ms, mm = (ts > -0.2) & (ts < span), (tm > -0.2) & (tm < span)
        d_si, d_mo = t50(ts[ms], vs[ms]), t50(tm[mm], vm[mm])
        out.append((dev, d_si, d_mo))
        with plt.rc_context(RC):
            fig, a = plt.subplots(figsize=(6.4, 4.0))
            a.plot(ts, vs, color=TR, lw=2.6, label=f"transistor level, 50 % at {d_si * 1000:.0f} ps")
            a.plot(tm, vm, color=MODEL, lw=2.0, label=f"stage-law model, 50 % at {d_mo * 1000:.0f} ps")
            a.axvline(d_si, color=TR, lw=1.2, ls="--"); a.axvline(d_mo, color=MODEL, lw=1.2, ls="--")
            half = 0.5 * (float(vs[ms][0]) + float(vs[ms][-1]))
            a.axhline(half, color=FILE, lw=1.2, ls="--")
            a.text(-0.15, half + 0.02, "50 % of the swing", color="#555555", fontsize=9, va="bottom")
            a.set_xlim(-0.2, span); a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("pad voltage (V)")
            a.set_title(f"{dev}: complete transition into 50 Ω ∥ 2 pF"); a.legend(frameon=False, loc="center right"); a.grid(alpha=0.25, lw=0.5)
            save(fig, f"fullswing_{dev}.png")
    return out


# ------------------------------------------------------------------ 7. the result
def result():
    table = []
    for dev in ("ex2", "inv_chain"):
        folder = figs.pick_build(dev)
        sweep = list(csv.DictReader((folder / "sweep.csv").open()))[-1]
        swing = figs.settled_swing(dev)
        with plt.rc_context(RC):
            for w in WIDTHS[dev]:
                t_si, si, nat = matrix_wave(dev, w)
                tm, _ku, pm = b24._cand(folder, f"d{w}")
                e_nat, e_mo = peak_err(t_si, nat, t_si, si, w / 1000), float(sweep[f"pk_d{w}"])
                table.append(dict(buffer=dev, width_ps=w, depth_pct=DEPTH[dev][w], transistor_peak_V=round(float(si[(t_si > 0) & (t_si < w / 1000 + 2.6)].max()), 3),
                                  model_peak_err_pct=e_mo, model_lag_ps=float(sweep[f"lag_d{w}"]), native_peak_err_pct=round(e_nat, 1)))
                fig, a = plt.subplots(figsize=(6.4, 4.0))
                a.plot(t_si, si, color=TR, lw=2.6, label="transistor level", zorder=3)
                a.plot(t_si, nat, color=NATIVE, lw=2.0, ls=NAT_LS, label=f"HSPICE native IBIS ({e_nat:+.0f} % peak)", zorder=2)
                a.plot(tm, pm, color=MODEL, lw=2.2, ls="--", label=f"stage-law model ({e_mo:+.1f} % peak)", zorder=4)
                a.set_xlim(*xlim(dev, w)); a.set_ylim(-0.1, swing * 1.05)
                a.set_title(title(dev, w), fontsize=12)
                a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("pad voltage (V)")
                a.legend(frameon=False, loc="upper right"); a.grid(alpha=0.25, lw=0.5)
                save(fig, f"result_{dev}_{w}ps.png")
    with (OUT / "result_table.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys()))
        w.writeheader(); w.writerows(table)
    md = ["| buffer | pulse width | depth | transistor peak | model peak error | model lag | native IBIS peak error |", "|---|---:|---:|---:|---:|---:|---:|"]
    for r in table:
        md.append(f"| {r['buffer']} | {r['width_ps']} ps | {r['depth_pct']} % | {r['transistor_peak_V']:.2f} V | {r['model_peak_err_pct']:+.1f} % | {r['model_lag_ps']:+.0f} ps | {r['native_peak_err_pct']:+.0f} % |")
    (OUT / "result_table.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("   result_table.csv/.md")
    return table


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in ("fit_knobs.png", "fullswing_delay.png"):
        (OUT / stale).unlink(missing_ok=True)
    challenge(); value_match(); time_match(); kstage_blocks(); map_derivation(); maps_and_shapes(); knobs(); band_K()
    for dev, a, b in fullswing_delay():
        print(f"   full-swing 50 % crossing {dev}: transistor {a * 1000:.0f} ps, model {b * 1000:.0f} ps")
    result()
    return 0


if __name__ == "__main__":
    sys.exit(main())
