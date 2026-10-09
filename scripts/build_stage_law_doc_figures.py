#!/usr/bin/env python3
"""Figures for the stage-law derivation document (results/stage_law_doc_2026-10-01).

One function per figure, paper style (no slide headlines), every curve drawn from data
already in the repository:

    fig_device        HSPICE output curves of the predriver devices + the alpha-power fit
                      (results/device_taper_2026-09-28/alpha_extract, device_alpha_extract.py)
    fig_stage_law     the two factors of the stage law and one stage's step response
    fig_blocks        the signal path: comparator -> K stages -> map -> I-V tables -> pad
    fig_chain         one chain under a full transition and under a truncated pulse (ex2)
    fig_ku_fit        the Ku-domain fit against the file's own Ku(t) (device_taper_ku.py)
    fig_rms_vs_k      fit residual against stage count (stage_count_from_file step 1)
    fig_calibration   the one stressed run: what is measured, the vt bisection, the selection
    fig_gate_verify   stressed gate, measured vs stage law vs linear superposition
    fig_pad_waveforms transistor vs HSPICE native IBIS vs the proposed model, at the pad
    fig_pad_summary   worst stressed peak error on the twelve buffers

The data loaders are the 09-24 deck's (build_0924_deck_figures), reused rather than
re-derived; only the drawing is new.

    py -3.14 scripts/build_stage_law_doc_figures.py            # all
    py -3.14 scripts/build_stage_law_doc_figures.py fig_chain  # one
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import current_limited_stage_model as cl  # noqa: E402

OUT = ROOT / "results" / "stage_law_doc_2026-10-01" / "figures"
DT = ROOT / "results" / "device_taper_2026-09-28"
SC = ROOT / "results" / "stage_count_from_file_2026-09-21"

K_, TEAL, BLUE, RED, GREY, GREEN = "#111111", "#0E9F9A", "#2B6CA3", "#B0563C", "#8A9499", "#5B8C2A"
RC = {"font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 7.6,
      "xtick.labelsize": 8, "ytick.labelsize": 8, "lines.linewidth": 1.6,
      "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100}
W = 6.6          # text width, inches


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {name}.png")


def tag(ax, s, x=-0.02, y=1.06):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=9.5, fontweight="bold", va="bottom", ha="right")


def prior(g, vt, a, gs=1.0):
    return np.clip((np.asarray(g, float) - vt) / (gs - vt), 0.0, 1.0) ** a


# ------------------------------------------------------------------ 0. the problem
def fig_problem():
    """What goes wrong. (a) ex2's pad for a complete transition - the situation an IBIS file
    records. (b) The same buffer for an 810 ps input pulse: the transistor against HSPICE's
    native IBIS model of the same file."""
    import gate_ramp_prototype  # noqa: F401
    import build_0917_deck_figures as f17
    import build_0924_deck_figures as b24
    import predriver_stage_probe as psp
    full = psp.parse_tr0(cl.ST / "ex2" / "full" / "run.tr0")
    tf = np.asarray(full["time"], float) * 1e9 - 5.0
    sig = psp.signals(full, ["v(in_dig)", "v(pad_sp)"])
    t_si, si, _ = f17.transistor_pad("ex2", 810)
    t_si = t_si - 5.0
    d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / "ex2_short_high_w810ps.csv")
    x = d["time_ns"] - 5.0
    e_nat, _ = b24._peak_err(x, d["hspice_pad"], t_si, si, 0.81)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 2, figsize=(W, 2.5), gridspec_kw={"wspace": 0.28})
        a = ax[0]
        a.plot(tf, sig["v(in_dig)"], color=GREY, lw=1.0, label="input pin")
        a.plot(tf, sig["v(pad_sp)"], color=K_, lw=2.2, label="pad, transistor netlist")
        a.set_xlim(-0.5, 6); a.set_ylim(-0.3, 3.6)
        a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("voltage (V)")
        a.set_title("(a) a complete transition: what the file records", fontsize=8.5)
        a.legend(frameon=False, loc="lower right", fontsize=7)
        b = ax[1]
        b.plot(t_si, si, color=K_, lw=2.2, label="pad, transistor netlist")
        b.plot(x, d["hspice_pad"], color=BLUE, lw=1.6, ls=(0, (1.4, 1.4)), label=f"native IBIS model ({e_nat:+.0f} % on the peak)")
        b.annotate("", (0.81, -0.22), (0, -0.22), arrowprops=dict(arrowstyle="<|-|>", color="#555555", lw=1))
        b.text(0.4, -0.3, "810 ps input pulse", ha="center", va="top", fontsize=7)
        b.set_xlim(-0.5, 3.0); b.set_ylim(-0.5, 2.0)
        b.set_xlabel("time from the input edge (ns)")
        b.set_title("(b) a short pulse: the file's model fails", fontsize=8.5)
        b.legend(frameon=False, loc="upper left", fontsize=7)
        save(fig, "fig_problem")


# ------------------------------------------------------------------ 5c. the fit, seen as knobs
def fig_fit_knobs():
    """What each fitted number does to the model's K_u(t), against the file's curve (ex2,
    K = 3, map (0.57, 0.64), x_lin = 0.45), and how a fit progresses from a first guess."""
    sf = ROOT / "results" / "stage_law_doc_2026-10-01" / "shape_from_file"
    d = np.load(sf / "target_ex2.npz")
    u, target = d["u"], d["target"]
    t = np.arange(4.0, 21.0, cl.DT) - 5.025
    p = EX2
    base = (p["s_up"], p["s_dn"], p["vt_fit"], p["x_lin"])

    def ku(s_up, s_dn, vt, xl=0.45):
        return prior(chain_stages(u, s_up, s_dn, vt, xl, 3)[-1], *p["shape"])

    def rms(y):
        return float(np.sqrt(np.mean((y - target) ** 2)))

    with plt.rc_context(RC):
        fig, ax = plt.subplots(2, 2, figsize=(W, 4.6), gridspec_kw={"wspace": 0.22, "hspace": 0.55})
        panels = ((ax[0][0], "s_up", (1.1, 2.19, 4.4), (0, 3.0), "(a) $s_{up}$ sets the rising edge"),
                  (ax[0][1], "s_dn", (1.06, 2.12, 4.2), (10.0, 13.0), "(b) $s_{dn}$ sets the falling edge"),
                  (ax[1][0], "vt", (0.30, 0.528, 0.65), (0, 3.0), "(c) $v_t$ sets the delay between stages"))
        shades = ("#9CC8C6", TEAL, "#0B5F5C")
        for a, name, vals, xr, title in panels:
            a.plot(t, target, color=K_, lw=3.0, alpha=0.35, label="file $K_u(t)$")
            for v, c in zip(vals, shades):
                s_up, s_dn, vt = base[0], base[1], base[2]
                if name == "s_up":
                    s_up = v
                elif name == "s_dn":
                    s_dn = v
                else:
                    vt = v
                y = ku(s_up, s_dn, vt)
                lab = {"s_up": f"$s_{{up}}$ = {v:g}/ns", "s_dn": f"$s_{{dn}}$ = {v:g}/ns", "vt": f"$v_t$ = {v:g}"}[name]
                a.plot(t, y, color=c, lw=1.5, label=f"{lab}  (rms {rms(y):.3f})")
            a.set_xlim(*xr); a.set_ylim(-0.05, 1.12)
            a.set_title(title, fontsize=8.5)
            a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("$K_u$")
            a.legend(frameon=False, fontsize=6.4, loc="center right" if name != "s_dn" else "center left")
        a = ax[1][1]
        a.plot(t, target, color=K_, lw=3.0, alpha=0.35, label="file $K_u(t)$")
        steps = ((8.0, 8.0, 0.40, "first guess"), (2.19, 8.0, 0.40, "$s_{up}$ adjusted"), (2.19, 2.12, 0.40, "$s_{dn}$ adjusted"),
                 (2.19, 2.12, 0.528, "$v_t$ adjusted: the fit"))
        for (s_up, s_dn, vt, lab), c in zip(steps, ("#BBBBBB", "#888888", "#4FB3AF", RED)):
            y = ku(s_up, s_dn, vt)
            a.plot(t, y, color=c, lw=1.5 if lab.endswith("fit") else 1.2, label=f"{lab}  (rms {rms(y):.3f})")
        a.set_xlim(0, 3.0); a.set_ylim(-0.05, 1.12)
        a.set_title("(d) a fit, one number at a time", fontsize=8.5)
        a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("$K_u$")
        a.legend(frameon=False, fontsize=6.4, loc="center right")
        save(fig, "fig_fit_knobs")
    return {lab: rms(ku(s_up, s_dn, vt)) for s_up, s_dn, vt, lab in steps}


# ------------------------------------------------------------------ 1. the device
def fig_device():
    import device_alpha_extract as dae
    devs = [("ex2 NMOS (0.6 µm)", "nfet", 3.3, "n", BLUE, "-"),
            ("ex2 PMOS (0.6 µm)", "pfet", 3.3, "p", BLUE, "--"),
            ("inv_chain NMOS (180 nm)", "nch_tn", 1.8, "n", RED, "-"),
            ("inv_chain PMOS (180 nm)", "pch_tn", 1.8, "p", RED, "--")]
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 3, figsize=(W, 2.5), gridspec_kw={"wspace": 0.5})
        for name, model, vdd, kind, col, ls in devs:
            blocks = dae.parse_sw0(DT / "alpha_extract" / model / "run.sw0", dae.N_OUTER)
            vd0, alpha, vth, vgs, isat, curves = dae.extract(blocks, vdd, kind)
            x, y = curves[-1]
            ax[0].plot(x / vdd, y / y[-1], color=col, ls=ls, lw=1.5,
                       label=f"{name.split(' (')[0]}  {vd0 / vdd:.2f}")
            m = vgs > vth + 0.05
            ax[2].loglog((vgs[m] - vth) / (vdd - vth), isat[m] / isat[-1], color=col, ls=ls,
                         lw=1.5, label=f"{name.split(' (')[0]}: α = {alpha:.2f}")
            if model == "nch_tn":
                # panel b: the family at several drives, with the alpha-power knee of each
                for j in (8, 11, 14, 17, 20):
                    xx, yy = curves[j]
                    D = (vgs[j] - vth) / (vdd - vth)
                    ax[1].plot(xx / vdd, yy / y[-1], color=RED, lw=1.2)
                    knee = (vd0 / vdd) * D ** (alpha / 2)
                    ax[1].plot([0, knee, 1], [0, D ** alpha, D ** alpha], color=K_, lw=0.9,
                               ls=(0, (3, 2)))
                    ax[1].plot(knee, D ** alpha, "o", color=K_, ms=3)
                    ax[1].text(1.02, yy[-1] / y[-1], f"{D:.2f}", fontsize=6.5, va="center")
        ax[0].set_xlabel("$V_{DS}/V_{DD}$"); ax[0].set_ylabel("$I_D / I_{D0}$ at full gate drive")
        ax[0].legend(loc="lower right", frameon=False, fontsize=6.0, handlelength=1.4, borderaxespad=0.1,
                     title="$x_0 = V_{D0}/V_{DD}$", title_fontsize=6.4)
        ax[0].set_xlim(0, 1); ax[0].set_ylim(0, 1.08)
        ax[1].set_xlabel("$V_{DS}/V_{DD}$"); ax[1].set_ylabel("$I_D / I_{D0}$")
        ax[1].set_xlim(0, 1.2); ax[1].set_ylim(0, 1.42)
        ax[1].text(1.02, 1.1, "$D$ =", fontsize=6.5)
        ax[1].plot([], [], color=RED, lw=1.2, label="HSPICE (inv_chain NMOS)")
        ax[1].plot([], [], color=K_, lw=0.9, ls=(0, (3, 2)), label="α-power law, eq. (2)")
        ax[1].legend(loc="upper left", frameon=False, fontsize=6.0, handlelength=1.6)
        ax[2].set_xlabel("gate drive $D$"); ax[2].set_ylabel("$I'_{D0}/I_{D0}$")
        ax[2].legend(loc="lower right", frameon=False, fontsize=6.0, handlelength=1.4)
        ax[2].grid(alpha=0.25, which="both", lw=0.4)
        for a, s in zip(ax, "abc"):
            tag(a, f"({s})", x=0.0)
        save(fig, "fig_device")


# ------------------------------------------------------------------ 2. the stage law
def fig_stage_law():
    vt, x0 = 0.30, 0.45
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 3, figsize=(W, 2.4), gridspec_kw={"wspace": 0.45})
        x = np.linspace(0, 1, 400)
        for p, ls, lab in ((1.0, "-", "p = 1 (used)"), (1.3, "--", "p = 1.3"), (2.0, ":", "p = 2 (long channel)")):
            ax[0].plot(x, cl.h(x, vt, p), color=TEAL if p == 1 else GREY, ls=ls, label=lab)
        ax[0].axvline(vt, color=GREY, lw=0.6, ls=":")
        ax[0].text(vt + 0.02, 0.02, "$v_t$", fontsize=8)
        ax[0].set_xlabel("stage input $u$"); ax[0].set_ylabel("gate factor $h(u)$")
        ax[0].legend(frameon=False, loc="upper left", fontsize=6.8); ax[0].set_ylim(-0.03, 1.3)

        v = np.linspace(0, 1, 500)
        for g, c in ((1.0, K_), (0.6, "#555555"), (0.3, "#999999")):
            edge = x0 * g ** 0.5                                   # eq. (15), alpha = 1
            ax[1].plot(v, np.minimum(1, (1 - v) / edge), color=c, lw=1.2, ls="--",
                       label=f"eq. (15), g = {g:g}")
        ax[1].plot(v, np.minimum(1, (1 - v) / x0), color=TEAL, lw=2.0, label="$r(1-v)$, eq. (18)")
        ax[1].axvline(1 - x0, color=GREY, lw=0.6, ls=":")
        ax[1].text(1 - x0 - 0.02, 0.62, "$v = 1-x_{lin}$", fontsize=7.5, ha="right")
        ax[1].set_xlabel("stage output $v$"); ax[1].set_ylabel("drain factor (charging)")
        ax[1].legend(frameon=False, loc="lower left", fontsize=6.6); ax[1].set_ylim(-0.03, 1.3)

        s_up = 2.19
        t = np.arange(-0.2, 2.0, cl.DT)
        u = (t >= 0).astype(float)
        y = cl.simulate(u, s_up, s_up, vt, x0, 1.0)
        ax[2].plot(t, u, color=GREY, lw=1.0, label="input $u$")
        ax[2].plot(t, y, color=TEAL, lw=2.0, label="output $v$, eq. (19)")
        tk = (1 - x0) / s_up
        ax[2].plot([0, 1 / s_up], [0, 1], color=K_, lw=0.8, ls=(0, (3, 2)))
        ax[2].plot(tk, 1 - x0, "o", color=K_, ms=3.5)
        ax[2].annotate("ramp,\nslope $s_{up}$", (0.17, 0.25), fontsize=7.5)
        ax[2].annotate("exponential,\n$\\tau = x_{lin}/s_{up}$", (0.62, 0.68), fontsize=7.5)
        ax[2].set_xlabel("time (ns)"); ax[2].set_ylabel("normalised node")
        ax[2].set_xlim(-0.2, 1.8); ax[2].set_ylim(-0.03, 1.3)
        ax[2].legend(frameon=False, loc="upper right", fontsize=7)
        for a, s in zip(ax, "abc"):
            tag(a, f"({s})", x=0.0)
        save(fig, "fig_stage_law")


# ------------------------------------------------------------------ 3. the signal path
def fig_blocks():
    with plt.rc_context(RC):
        fig, a = plt.subplots(figsize=(W, 2.5))
        a.set_xlim(0, 100); a.set_ylim(0, 40); a.axis("off")

        def box(x, y, w, h, text, fc="#F1F3F4", ec="#555555", fs=7.6, bold=False):
            a.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8",
                                                fc=fc, ec=ec, lw=1.1))
            a.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
                   fontweight="bold" if bold else "normal")

        def arrow(x0, y0, x1, y1, text=None, dy=1.6):
            a.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color="#444444", lw=1.1))
            if text:
                a.text((x0 + x1) / 2, max(y0, y1) + dy, text, ha="center", va="bottom", fontsize=7.4)

        new, old = "#DDF1F0", "#F1F3F4"
        a.text(1.5, 26, "$V_{in}$", fontsize=8.5, va="center")
        arrow(5.2, 26, 8.5, 26)
        box(8.5, 21, 13.5, 10, "comparator\nat $V_{DD}/2$\n(20)", fc=new, ec=TEAL, fs=7.0)
        arrow(22, 26, 25, 26, "$u_1$")
        for i, lab in enumerate(("stage 1", "stage 2")):
            box(25 + 10.5 * i, 21, 8.5, 10, lab + "\n(19)", fc=new, ec=TEAL)
            arrow(33.5 + 10.5 * i, 26, 35.5 + 10.5 * i, 26)
        a.text(48.2, 26, "…", fontsize=11, ha="center", va="center")
        arrow(50, 26, 52, 26)
        box(52, 21, 8.5, 10, "stage $K$\n(19)", fc=new, ec=TEAL)
        arrow(60.5, 26, 66, 26, "$G_{UP}$")
        box(66, 21, 10, 10, "map $M$\n(22)", fc=new, ec=TEAL)
        arrow(76, 26, 81, 26, "$K_u$")
        box(81, 13, 12, 18, "I–V tables\n+ $C_{comp}$\n(24)", fc=old)
        arrow(93, 22, 98.5, 22)
        a.text(96, 24.2, "pad", fontsize=8.5, ha="center")
        # pull-down branch
        a.plot([63, 63], [26, 15], color="#444444", lw=1.1)
        arrow(63, 15, 66, 15)
        box(66, 10, 10, 10, "map $M_d$\n(22)", fc=new, ec=TEAL)
        a.text(60.4, 17.5, "$1-G_{UP}$", fontsize=7.2, ha="right")
        arrow(76, 15, 81, 15, "$K_d$")
        # braces
        a.plot([10, 76], [35.5, 35.5], color=TEAL, lw=1.2)
        a.text(43, 36.5, "added by the proposed method: fitted to the file, one stressed run to calibrate",
               ha="center", fontsize=7.6, color=TEAL)
        a.plot([81, 93], [9.5, 9.5], color="#666666", lw=1.2)
        a.text(87, 8.3, "from the IBIS file,\nunchanged", ha="center", va="top", fontsize=7.4, color="#555555")
        a.text(43, 4.2, "$K$ identical stages share $\\{s_{up}, s_{dn}, v_t, x_{lin}, p\\}$",
               ha="center", fontsize=7.6, color="#444444")
        save(fig, "fig_blocks")


# ------------------------------------------------------------------ 4. one chain, two inputs
EX2 = dict(s_up=2.1903, s_dn=2.1238, vt_fit=0.5276, vt_cal=0.487, x_lin=0.45, K=3, shape=(0.57, 0.64))


def chain_stages(u, s_up, s_dn, vt, x_lin, K):
    out, x = [], u
    for _ in range(K):
        x = cl.simulate(x, s_up, s_dn, vt, x_lin, 1.0)
        out.append(x)
    return out


def fig_chain():
    p = EX2
    t = np.arange(-0.3, 4.2, cl.DT)
    cases = (("full transition", (t >= 0).astype(float)),
             ("truncated pulse, 810 ps", ((t >= 0) & (t < 0.81)).astype(float)))
    cols = ("#9CC8C6", "#4FB3AF", TEAL)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(2, 2, figsize=(W, 3.5), sharex=True,
                               gridspec_kw={"hspace": 0.16, "wspace": 0.12, "height_ratios": [1.25, 1]})
        for j, (name, u) in enumerate(cases):
            st = chain_stages(u, p["s_up"], p["s_dn"], p["vt_cal"], p["x_lin"], p["K"])
            a = ax[0][j]
            a.plot(t, u, color=GREY, lw=1.0, label="$u_1$ (comparator)")
            for k, (v, c) in enumerate(zip(st, cols), 1):
                a.plot(t, v, color=c, lw=1.3 if k < 3 else 2.2,
                       label=f"$v_{k}$" + (" = $G_{UP}$" if k == 3 else ""))
            a.axhline(p["vt_cal"], color=K_, lw=0.6, ls=":")
            a.text(4.15, p["vt_cal"] + 0.02, "$v_t$", fontsize=7.5, ha="right")
            a.set_title(name, fontsize=9)
            a.set_ylim(-0.05, 1.12)
            b = ax[1][j]
            ku = prior(st[-1], *p["shape"])
            b.plot(t, ku, color=RED, lw=2.0, label="$K_u = M(G_{UP})$")
            b.set_ylim(-0.05, 1.12)
            b.set_xlabel("time from the input edge (ns)")
            b.annotate(f"peak $G_{{UP}}$ = {st[-1].max():.2f}\npeak $K_u$ = {ku.max():.2f}",
                       (0.97, 0.9), xycoords="axes fraction", ha="right", va="top", fontsize=7.6)
            if j:
                a.set_yticklabels([]); b.set_yticklabels([])
        ax[0][0].set_ylabel("stage nodes"); ax[1][0].set_ylabel("conducting fraction")
        ax[0][1].legend(*ax[0][0].get_legend_handles_labels(), frameon=False, loc="upper right", fontsize=7)
        ax[1][0].legend(frameon=False, loc="lower right")
        ax[0][0].set_xlim(-0.3, 4.2)
        tag(ax[0][0], "(a)", x=0.0); tag(ax[0][1], "(b)", x=0.0)
        save(fig, "fig_chain")


# ------------------------------------------------------------------ 4a. what the map is
SHAPES = ((0.50, 0.70), (0.40, 0.60), (0.40, 0.90))          # the three candidates of the method


def fig_map():
    """The map, measured where the gate can be probed (ex2), and the three shapes the method
    offers when it cannot. Left: at each instant of a full transition the probed gate and the
    file's K_u are read together. Middle: plotting one against the other gives the map, with
    the two-parameter formula fitted to it. Right: the candidate shapes."""
    import build_0917_deck_figures as f17
    import build_0924_deck_figures as b24
    import spicelab as sl
    folder, node, gname, widths, _y, _s = b24.DEV["ex2"]
    tf, gfull, _ts, _gs = f17._norm_pair("ex2", widths[0], node)
    raw = sl.parse_ngspice_raw(f17.CASC / folder / "shipped" / "full" / "run.raw")
    t_m, ku_m = sl.time_ns(raw) - 5.0, sl.signal(raw, "v(x1.ku)")
    g_end = float(tf[np.argmax(np.asarray(gfull) >= 0.995)]) + 0.25
    tt = np.linspace(0.2, g_end, 400)
    ku_t, g_t = np.interp(tt, t_m, ku_m), np.interp(tt, tf, gfull)
    marks = (0.95, 1.10, 1.22, 1.35, 1.55)
    cmap = plt.get_cmap("viridis")
    cols = [cmap(0.08 + 0.84 * i / 4) for i in range(5)]
    gg = np.linspace(0, 1, 400)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 3, figsize=(W, 2.55), gridspec_kw={"wspace": 0.36})
        a = ax[0]
        a.plot(tt, g_t, color=TEAL, lw=1.8, label="probed gate $g(t)$")
        a.plot(tt, ku_t, color=K_, lw=1.8, label="$K_u(t)$ of the file")
        for m, c in zip(marks, cols):
            ki, gi = float(np.interp(m, tt, ku_t)), float(np.interp(m, tt, g_t))
            a.plot([m, m], [gi, ki], color=c, lw=0.9, ls=":")
            a.plot(m, gi, "s", color=c, ms=4.5, mec="white", mew=0.5, zorder=5)
            a.plot(m, ki, "o", color=c, ms=4.5, mec="white", mew=0.5, zorder=5)
        a.set_xlim(0.2, g_end); a.set_ylim(-0.12, 1.3)
        a.set_xlabel("time (ns)"); a.set_ylabel("normalized")
        a.set_title("(a) with a probe", fontsize=8.3)
        a.legend(frameon=False, loc="upper left", fontsize=6.6)
        b = ax[1]
        order = np.argsort(g_t)
        b.plot(g_t[order], ku_t[order], color=K_, lw=1.8, label="measured map")
        b.plot(gg, prior(gg, 0.57, 0.64), color=RED, lw=1.4, ls="--", label="formula, (0.57, 0.64)")
        for m, c in zip(marks, cols):
            b.plot(float(np.interp(m, tt, g_t)), float(np.interp(m, tt, ku_t)), "o", color=c, ms=4.5,
                   mec="white", mew=0.5, zorder=5)
        b.set_xlim(-0.02, 1.02); b.set_ylim(-0.12, 1.3)
        b.set_xlabel("gate $g$"); b.set_ylabel("$K_u$")
        b.set_title("(b) the measured map", fontsize=8.3)
        b.legend(frameon=False, loc="upper left", fontsize=6.6)
        c = ax[2]
        c.plot(g_t[order], ku_t[order], color="#BBBBBB", lw=1.2, label="measured (ex2)")
        for (v, a_), col, ls in zip(SHAPES, (TEAL, BLUE, RED), ("-", "--", "-.")):
            c.plot(gg, prior(gg, v, a_), color=col, lw=1.5, ls=ls, label=f"({v:.2f}, {a_:.2f})")
        c.set_xlim(-0.02, 1.02); c.set_ylim(-0.12, 1.3)
        c.set_xlabel("gate $g$"); c.set_ylabel("$M(g)$")
        c.set_title("(c) candidate shapes", fontsize=8.3)
        c.legend(frameon=False, loc="upper left", fontsize=6.6, title="$(v_{t,map},\\ a)$", title_fontsize=6.6)
        save(fig, "fig_map")


# ------------------------------------------------------------------ 5b. the ambiguity
def fig_ambiguity():
    """Two different assumed maps, each with the stage law fitted through it to the same file
    K_u(t) (ex2, K = 3; results/stage_law_doc_2026-10-01/shape_from_file). The fitted gates
    differ, the full-swing K_u(t) does not - and under a short pulse the two models separate."""
    import json
    sf = ROOT / "results" / "stage_law_doc_2026-10-01" / "shape_from_file"
    d = np.load(sf / "target_ex2.npz")
    u_full, target = d["u"], d["target"]
    t = np.arange(4.0, 21.0, cl.DT) - 5.025
    u_cut = ((t >= 0) & (t < 0.81)).astype(float)
    cases = []
    for (v, a_), col, name in (((0.6, 0.6), BLUE, "late map"), ((0.4, 0.6), RED, "early map")):
        r = json.loads((sf / f"shape_ex2_{v:g}_{a_:g}.json").read_text())
        g_full = chain_stages(u_full, r["s_up"], r["s_dn"], r["vt"], 0.45, 3)[-1]
        g_cut = chain_stages(u_cut, r["s_up"], r["s_dn"], r["vt"], 0.45, 3)[-1]
        cases.append((v, a_, col, name, r, g_full, g_cut))
    gg = np.linspace(0, 1, 400)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(2, 2, figsize=(W, 4.4), gridspec_kw={"wspace": 0.26, "hspace": 0.5})
        for v, a_, col, name, r, g_full, g_cut in cases:
            lab = f"{name} ({v:g}, {a_:g})"
            ax[0][0].plot(gg, prior(gg, v, a_), color=col, lw=1.8, label=lab)
            ax[0][1].plot(t, g_full, color=col, lw=1.8, label=f"gate fitted through the {name}")
            ax[1][0].plot(t, prior(g_full, v, a_), color=col, lw=1.6, label=f"{name}, rms {r['rms']:.4f}")
            ku = prior(g_cut, v, a_)
            ax[1][1].plot(t, ku, color=col, lw=1.8, label=f"{name}: peak {ku.max():.2f}")
        ax[1][0].plot(t, target, color=K_, lw=3.2, alpha=0.35, zorder=1, label="file $K_u(t)$")
        ax[0][0].set_xlabel("gate $g$"); ax[0][0].set_ylabel("$M(g)$")
        ax[0][0].set_title("(a) two assumed maps", fontsize=8.5)
        ax[0][1].set_xlabel("time (ns)"); ax[0][1].set_ylabel("gate $g(t)$")
        ax[0][1].set_title("(b) the gate the fit produces for each", fontsize=8.5)
        ax[1][0].set_xlabel("time (ns)"); ax[1][0].set_ylabel("$K_u$")
        ax[1][0].set_title("(c) full transition: both match the file", fontsize=8.5)
        ax[1][1].set_xlabel("time (ns)"); ax[1][1].set_ylabel("$K_u$")
        ax[1][1].set_title("(d) 810 ps pulse: they separate", fontsize=8.5)
        for a in (ax[0][1], ax[1][0], ax[1][1]):
            a.set_xlim(0, 3.0); a.set_ylim(-0.05, 1.12)
        ax[0][0].set_ylim(-0.05, 1.12)
        ax[0][0].legend(frameon=False, loc="upper left", fontsize=6.8)
        ax[0][1].legend(frameon=False, loc="upper left", fontsize=6.4)
        ax[1][0].legend(frameon=False, loc="lower right", fontsize=6.8)
        ax[1][1].legend(frameon=False, loc="upper right", fontsize=6.8)
        save(fig, "fig_ambiguity")


# ------------------------------------------------------------------ 7b. the stressed run, used
def fig_stress_use():
    """How the one stressed measurement is used, on ex2's nine candidates (three stage counts
    x three map shapes, each fitted to the file). (a) the measurement. (b) the candidates as
    fitted to the file, before the measurement is used: re-run here from the stored
    pre-calibration subcircuits (calib/it00). (c) after the threshold of each is calibrated on
    the peak. (d) the selected candidate at all five widths."""
    import build_0917_deck_figures as f17
    import build_0924_deck_figures as b24
    import gate_ramp_prototype as gp
    gp.VARIANT_NAME = "ex2"
    w = 0.810
    t_si, si, _ = f17.transistor_pad("ex2", 810)
    t_si = t_si - 5.0
    peak = float(si[(t_si >= w - 0.3) & (t_si <= w + 2.6)].max())
    cache = ROOT / "results" / "stage_law_doc_2026-10-01" / "before_calibration"
    with plt.rc_context(RC):
        fig, ax = plt.subplots(2, 2, figsize=(W, 4.5), gridspec_kw={"wspace": 0.24, "hspace": 0.5})
        a = ax[0][0]
        a.plot(t_si, si, color=K_, lw=2.2)
        a.plot(t_si[int(np.argmax(si))], peak, "o", color=TEAL, ms=6, zorder=5)
        a.annotate(f"peak {peak:.2f} V", (1.62, peak + 0.03), fontsize=7.6, color=TEAL)
        a.annotate("", (w, -0.22), (0, -0.22), arrowprops=dict(arrowstyle="<|-|>", color="#555555", lw=1))
        a.text(w + 0.08, -0.22, "810 ps input pulse", va="center", fontsize=7)
        a.set_title("(a) the stressed measurement", fontsize=8.5)

        b, c = ax[0][1], ax[1][0]
        peaks0 = []
        for (k, sh), folder in b24.CAND.items():
            pick = (k, sh) == b24.PICK
            npz = cache / f"K{k}_{sh}.npz"
            if not npz.exists():
                cache.mkdir(parents=True, exist_ok=True)
                r = gp.run_ours(cache / f"K{k}_{sh}", (folder / "calib" / "it00" / "driver.sub").read_text(encoding="utf-8"),
                                3.3, w)
                np.savez(npz, t=np.asarray(r["t"]) - 5.0, pad=np.asarray(r["pad"]))
            z = np.load(npz)
            peaks0.append(float(z["pad"].max()))
            kw = dict(color=TEAL if pick else GREY, lw=1.9 if pick else 0.9, zorder=4 if pick else 2)
            b.plot(z["t"], z["pad"], **kw)
            t1, _ku, pad = b24._cand(folder, "d810")
            c.plot(t1, pad, label="selected candidate" if pick else None, **kw)
        for q in (b, c):
            q.plot(t_si, si, color=K_, lw=2.2, zorder=5, label="measurement" if q is c else None)
            q.axhline(peak, color=TEAL, lw=0.8, ls="--")
        b.set_title("(b) nine candidates, as fitted to the file", fontsize=8.5)
        b.text(0.03, 0.95, f"peaks {min(peaks0):.2f}–{max(peaks0):.2f} V", transform=b.transAxes, fontsize=7.2, va="top")
        c.axvspan(w - 0.3, w + 1.5, color="#EEF2F3", zorder=0)
        c.plot([], [], color=GREY, lw=0.9, label="other eight")
        c.set_title("(c) after calibrating $v_t$ on the peak", fontsize=8.5)
        c.legend(frameon=False, loc="upper right", fontsize=6.6)

        d = ax[1][1]
        folder = b24.CAND[b24.PICK]
        for i, wp in enumerate(b24.DEV["ex2"][3]):
            ts, s_, _ = f17.transistor_pad("ex2", wp)
            d.plot(ts - 5.0, s_, color=K_, lw=1.8, label="transistor" if i == 0 else None)
            t1, _ku, pad = b24._cand(folder, f"d{wp}")
            d.plot(t1, pad, color=TEAL, lw=1.2, ls="--", label="selected model" if i == 0 else None)
        d.set_title("(d) check: the selected model at five widths", fontsize=8.5)
        d.legend(frameon=False, loc="upper right", fontsize=6.6)
        for q in (a, b, c, d):
            q.set_xlim(0.2, 3.0); q.set_xlabel("time (ns)"); q.set_ylabel("pad voltage (V)")
        a.set_xlim(-0.2, 3.0)
        for q in (a, b, c):
            q.set_ylim(-0.4, max(1.5, max(peaks0) * 1.12))
        save(fig, "fig_stress_use")
    return min(peaks0), max(peaks0), peak


# ------------------------------------------------------------------ 4b. gate -> map -> Ku
def fig_gate_to_ku():
    """The whole construction on ex2 (K = 3): the stage law gives g(t); the map turns each
    value of g into a conducting fraction; the result is the model's K_u(t). The same sample
    instants are marked in all three panels. Top row: full transition, against the file's own
    K_u(t) - this comparison is the fit. Bottom row: an 810 ps pulse - the gate turns back and
    the map is only read over part of its range."""
    import device_taper_ku as dku
    p = EX2
    vtm, a_ = p["shape"]
    grid, u_full, target = dku.shipped_ku("ex2", dku.BUFFERS["ex2"]["cc"])
    t = grid - (5.0 + 0.025)                                  # input edge mid-point at t = 0
    g_full = chain_stages(u_full, p["s_up"], p["s_dn"], p["vt_fit"], p["x_lin"], p["K"])[-1]
    u_cut = ((t >= 0) & (t < 0.81)).astype(float)
    g_cut = chain_stages(u_cut, p["s_up"], p["s_dn"], p["vt_cal"], p["x_lin"], p["K"])[-1]
    gg = np.linspace(0, 1, 500)
    cmap = plt.get_cmap("viridis")

    def dots(ax, xs, ys, n):
        for i, (x, y) in enumerate(zip(xs, ys)):
            ax.plot(x, y, "o", ms=5.5, color=cmap(0.08 + 0.84 * i / max(1, n - 1)), mec="white", mew=0.7, zorder=6)

    with plt.rc_context(RC):
        fig, ax = plt.subplots(2, 3, figsize=(W, 4.7), gridspec_kw={"wspace": 0.42, "hspace": 0.55})
        rows = (("full transition", g_full, (0.85, 1.12, 1.22, 1.36, 1.6, 2.2), True),
                ("810 ps input pulse", g_cut, (0.95, 1.12, 1.25, 1.37, 1.5, 1.62), False))
        for r, (name, g, ts, full) in enumerate(rows):
            ku = prior(g, vtm, a_)
            gi = np.interp(ts, t, g)
            ki = prior(gi, vtm, a_)
            a, b, c = ax[r]
            # (1) the stage law's output: the gate
            a.plot(t, g, color=TEAL, lw=2.0)
            a.axhline(vtm, color=GREY, lw=0.7, ls=":")
            a.text(2.95, vtm + 0.03, "$v_{t,map}$", fontsize=7, ha="right", color="#555555")
            dots(a, ts, gi, len(ts))
            a.set_xlim(0, 3.0); a.set_ylim(-0.05, 1.12)
            a.set_xlabel("time (ns)"); a.set_ylabel("gate $g = G_{UP}$")
            a.set_title(("(a)" if full else "(d)") + f" stage law: $g(t)$, {name}", fontsize=8.2)
            # (2) the map, read at those gate values
            b.plot(gg, prior(gg, vtm, a_), color="#BBBBBB" if not full else RED, lw=1.3 if not full else 2.0)
            if not full:
                m = gg <= g.max()
                b.plot(gg[m], prior(gg[m], vtm, a_), color=RED, lw=2.4)
                b.axvline(g.max(), color=GREY, lw=0.7, ls=":")
                b.text(0.02, 0.86, f"gate turns back at {g.max():.2f};" + chr(10) + "above it the map is not read",
                       fontsize=6.2, color="#555555")
            b.axvline(vtm, color=GREY, lw=0.7, ls=":")
            dots(b, gi, ki, len(ts))
            b.set_xlim(0, 1.02); b.set_ylim(-0.05, 1.12)
            b.set_xlabel("gate $g$"); b.set_ylabel("$K_u = M(g)$")
            b.set_title(("(b)" if full else "(e)") + " the map $M(g)$", fontsize=8.2)
            # (3) the result
            if full:
                c.plot(t, target, color=K_, lw=2.6, label="IBIS file")
                rms = float(np.sqrt(np.mean((ku - target) ** 2)))
                c.plot(t, ku, color=RED, lw=1.7, label=f"model, rms {rms:.3f}")
            else:
                c.plot(t, prior(g_full, vtm, a_), color="#CCCCCC", lw=1.2, label="full transition")
                c.plot(t, ku, color=RED, lw=2.0, label=f"model, peak {ku.max():.2f}")
            dots(c, ts, ki, len(ts))
            c.set_xlim(0, 4.6); c.set_ylim(-0.05, 1.12)
            c.set_xlabel("time (ns)"); c.set_ylabel("$K_u$")
            c.set_title(("(c)" if full else "(f)") + " result: $K_u(t)$", fontsize=8.2)
            c.legend(frameon=False, loc="center right", fontsize=6.4, handlelength=1.3, borderaxespad=0.2)
        save(fig, "fig_gate_to_ku")



# ------------------------------------------------------------------ 5. the Ku-domain fit
def fig_ku_fit():
    import device_taper_ku as dku
    import device_taper_probe as dtp
    rows = {r["device"]: r for r in csv.DictReader((DT / "ku_domain" / "results_pin.csv").open())}
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 2, figsize=(W, 2.5), gridspec_kw={"wspace": 0.22})
        for a, dev, xmax in zip(ax, ("ex2", "inv_chain"), (3.0, 0.9)):
            cfg, r = dku.BUFFERS[dev], rows[dev]
            grid, u, target = dku.shipped_ku(dev, cfg["cc"])
            g = dtp.simulate_chain(u, [(float(r["s_up"]), float(r["s_dn"]), float(r["vt"]),
                                        0.45, 1.0)] * cfg["K"], "linear_const")
            model = prior(g, *cfg["prior"])
            tt = grid - 5.0
            a.plot(tt, target, color=K_, lw=2.6, label="file: $\\hat K_u^{file}(t)$")
            a.plot(tt, g, color=GREY, lw=1.1, ls="--", label="model gate $v_K(t)$ (not observable)")
            a.plot(tt, model, color=TEAL, lw=1.7, label="model: $M(v_K(t))$")
            a.set_xlim(-0.1 * xmax, xmax); a.set_ylim(-0.05, 1.1)
            a.set_xlabel("time from the input edge (ns)")
            a.set_title(f"{dev}, $K$ = {cfg['K']}: rms {float(r['ku_rms']):.4f}", fontsize=9)
            a.grid(alpha=0.25, lw=0.4)
        ax[0].set_ylabel("normalised")
        fig.legend(*ax[0].get_legend_handles_labels(), frameon=False, loc="lower center", ncol=3, fontsize=7.4,
                   bbox_to_anchor=(0.5, -0.12))
        tag(ax[0], "(a)", x=0.0); tag(ax[1], "(b)", x=0.0)
        save(fig, "fig_ku_fit")


# ------------------------------------------------------------------ 6. residual vs K
def band(v):
    best = min(v)
    return [k for k in range(1, len(v) + 1) if v[k - 1] <= 1.25 * best][:3]


def fig_rms_vs_k():
    rows = [r for r in csv.DictReader((SC / "step1_summary.csv").open()) if r["pass_"] == "as_track1"]
    show = {("ex2", "pull-up"): (BLUE, "ex2"), ("inv_chain", "pull-up"): (RED, "inv_chain"),
            ("io_buf", "pull-up"): (GREEN, "io_buf pull-up")}
    with plt.rc_context(RC):
        fig, a = plt.subplots(figsize=(W * 0.72, 2.7))
        ks = np.arange(1, 11)
        for r in rows:
            v = [float(x) for x in r["rms_by_K"].split()]
            key = (r["buffer"], r["chain"])
            if key not in show:
                a.semilogy(ks, v, color="#CCCCCC", lw=0.8, zorder=1)
                continue
            col, lab = show[key]
            a.semilogy(ks, v, color=col, lw=1.6, marker="o", ms=3, label=lab, zorder=3)
            b = band(v)
            a.semilogy(b, [v[k - 1] for k in b], color=col, lw=4.5, alpha=0.28, zorder=2,
                       solid_capstyle="round")
            kn = int(r["netlist_K"])
            a.plot(kn, v[kn - 1], "o", ms=9, mfc="none", mec=K_, mew=1.2, zorder=4)
        a.plot([], [], color="#CCCCCC", lw=0.8, label="the other ten chains")
        a.plot([], [], "o", ms=7, mfc="none", mec=K_, mew=1.2, ls="none", label="netlist stage count")
        a.plot([], [], color="#777777", lw=4.5, alpha=0.3, label="band of eq. (27)")
        a.set_xlabel("stage count $K$"); a.set_ylabel("$K_u$-domain rms of eq. (26)")
        a.set_xticks(ks); a.grid(alpha=0.25, which="both", lw=0.4)
        a.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.52, 1.0))
        save(fig, "fig_rms_vs_k")


# ------------------------------------------------------------------ 7. the one stressed run
def fig_calibration():
    import build_0917_deck_figures as f17
    import build_0924_deck_figures as b24
    t_si, si, _ = f17.transistor_pad("ex2", 810)
    t_si, w = t_si - 5.0, 0.810
    peak = float(si[(t_si >= w - 0.3) & (t_si <= w + 2.6)].max())
    d = b24.film()
    # bis_t is measured from the input's FALLING edge (export_method_animation_data: g - rev);
    # shift it so all three panels share the rising input edge as t = 0
    bt, bcur, bvt = d["bis_t"] + w, d["bis_curves"], d["bis_vt"]
    order = np.argsort(np.abs(bvt - bvt[-1]))[::-1]
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 3, figsize=(W, 2.45), gridspec_kw={"wspace": 0.1})
        a = ax[0]
        a.plot(t_si, si, color=K_, lw=2.2)
        a.plot(t_si[int(np.argmax(si))], peak, "o", color=TEAL, ms=6, zorder=5)
        a.axhline(peak, color=TEAL, lw=0.9, ls="--")
        a.annotate(f"peak {peak:.2f} V", (1.62, peak + 0.05), fontsize=7.6, color=TEAL)
        a.annotate("", (w, -0.2), (0, -0.2), arrowprops=dict(arrowstyle="<|-|>", color="#555555", lw=1))
        a.text(w + 0.08, -0.2, "810 ps input", ha="left", va="center", fontsize=7)
        a.set_xlim(-0.3, 3.0); a.set_ylim(-0.42, 1.5)
        a.set_xlabel("time (ns)"); a.set_ylabel("pad voltage (V)")
        a.set_title("(a) stressed measurement", fontsize=8.5)

        b = ax[1]
        for rank, i in enumerate(order):
            sh = 0.18 + 0.6 * rank / max(1, len(order) - 1)
            b.plot(bt, bcur[i], color=(0.17, 0.42, 0.64, sh), lw=1.1)
        b.plot(bt, bcur[order[-1]], color=TEAL, lw=2.0)
        b.axhline(peak, color=TEAL, lw=0.9, ls="--")
        b.annotate(f"$v_t$ = {bvt[order[0]]:.2f}", (bt[int(np.argmax(bcur[order[0]]))] + 0.1,
                                                   float(bcur[order[0]].max())), fontsize=7.5, color=BLUE)
        b.annotate(f"$v_t$ = {bvt[-1]:.3f}", (1.95, 0.42), fontsize=7.5, color=TEAL)
        b.set_xlim(-0.3, 3.0); b.set_ylim(-0.42, 1.5)
        b.set_xlabel("time (ns)")
        b.set_title("(b) calibration of $v_t$", fontsize=8.5)

        c = ax[2]
        c.axvspan(w - 0.3, w + 1.5, color="#EEF2F3", zorder=0)
        c.plot(t_si, si, color=K_, lw=2.4, zorder=5, label="transistor")
        for (k, sh), folder in b24.CAND.items():
            t, _ku, pad = b24._cand(folder, "d810")
            pick = (k, sh) == b24.PICK
            c.plot(t, pad, color=TEAL if pick else GREY, lw=1.9 if pick else 0.9,
                   zorder=4 if pick else 2, label="selected candidate" if pick else None)
        c.plot([], [], color=GREY, lw=0.9, label="other eight candidates")
        c.set_xlim(0.4, 2.9); c.set_ylim(-0.42, 1.5)
        c.set_xlabel("time (ns)")
        c.set_title("(c) selection by waveform", fontsize=8.5)
        c.legend(frameon=False, loc="upper right", fontsize=6.8)
        for a_ in ax[1:]:
            a_.set_yticklabels([])
        save(fig, "fig_calibration")


# ------------------------------------------------------------------ 8. gate-level verification
def fig_gate_verify():
    import device_taper_probe as dtp
    import predriver_stage_probe as psp
    rows = [r for r in csv.DictReader((DT / "results.csv").open()) if r["kind"] == "linear_const"]
    with plt.rc_context(RC):
        fig, ax = plt.subplots(2, 3, figsize=(W, 3.9), gridspec_kw={"hspace": 0.42, "wspace": 0.1})
        for i, dev in enumerate(("ex2", "inv_chain")):
            rr = [r for r in rows if r["device"] == dev]
            r0 = rr[0]
            K, gate = dtp.BUFFERS[dev]["K"], dtp.BUFFERS[dev]["gate"]
            prm = [(float(r0["s_up"]), float(r0["s_dn"]), float(r0["vt"]), float(r0["x_lin"]), 1.0)] * K
            grid, runs = cl.load(dev)
            u_name = psp.STAGES[dev][0]
            widths = sorted(k for k in runs if k != "full")
            for j, Wd in enumerate((widths[0], widths[2], widths[4])):
                a = ax[i][j]
                meas = runs[Wd][gate]
                pred = dtp.simulate_chain(runs[Wd][u_name], prm, "linear_const")
                lin = cl.linear_pred(grid, runs["full"][gate], Wd / 1e3)
                a.plot(grid - 5.0, meas, color=K_, lw=2.4, label="transistor gate (probed)")
                a.plot(grid - 5.0, pred, color=TEAL, lw=1.6, label="stage law ($K$ = 3 for ex2, 7 for inv_chain)")
                a.plot(grid - 5.0, lin, color=RED, lw=1.1, ls="--", label="linear superposition")
                a.set_xlim(-0.05 * psp.XMAX_NS[dev], psp.XMAX_NS[dev]); a.set_ylim(-0.08, 1.15)
                a.set_title(("(a) " if (i, j) == (0, 0) else "(b) " if (i, j) == (1, 0) else "") + f"{dev}, {Wd} ps", fontsize=9)
                a.text(0.97, 0.93, f"peak {meas.max():.3f}\nmodel {pred.max():.3f}\nlinear {lin.max():.3f}",
                       transform=a.transAxes, ha="right", va="top", fontsize=6.8)
                stored = float(next(r for r in rr if int(r["width_ps"]) == Wd)["pred_max"])
                assert abs(pred.max() - stored) < 0.004, (dev, Wd, pred.max(), stored)
                if j:
                    a.set_yticklabels([])
                if i:
                    a.set_xlabel("time from the input edge (ns)" if j == 1 else "")
            ax[i][0].set_ylabel("output gate, normalised")
        fig.legend(*ax[0][0].get_legend_handles_labels(), frameon=False, loc="lower center", ncol=3,
                   fontsize=7.4, bbox_to_anchor=(0.5, -0.045))
        save(fig, "fig_gate_verify")


# ------------------------------------------------------------------ 8b. the model's gate vs the real one
def fig_gate_internal():
    """The selected file-only model's internal gate G_UP against the probed transistor gate,
    which the method never sees (results/stage_law_doc_2026-10-01/gate_internal_check.py).
    Returns the peak table for the document."""
    import gate_ramp_prototype  # noqa: F401  (binds pybis2spice before the deck modules touch sys.path)
    import build_0924_deck_figures as b24
    import spicelab as sl
    gate = {"ex2": "v(xdut.n4)", "inv_chain": "v(xdut.vout7)"}
    rows = []
    with plt.rc_context(RC):
        fig, ax = plt.subplots(2, 3, figsize=(W, 3.8), gridspec_kw={"hspace": 0.5, "wspace": 0.1})
        for i, dev in enumerate(("ex2", "inv_chain")):
            folder = b24._pick_build(dev)
            grid, runs = cl.load(dev)
            widths = sorted(k for k in runs if k != "full")
            for j, (key, which) in enumerate([("full", "full"), (widths[0], f"d{widths[0]}"), (widths[-1], f"d{widths[-1]}")]):
                raw = sl.parse_ngspice_raw(folder / which / "run.raw")
                mod = np.interp(grid, sl.time_ns(raw), sl.signal(raw, "v(x1.gup)"))
                real = runs[key][gate[dev]]
                a = ax[i][j]
                a.plot(grid - 5.0, real, color=K_, lw=2.4, label="transistor gate (probed)")
                a.plot(grid - 5.0, mod, color=TEAL, lw=1.5, label="model gate $G_{UP}$ (file-only build)")
                xmax = {"ex2": 4.0, "inv_chain": 1.0}[dev]
                a.set_xlim(-0.05 * xmax, xmax); a.set_ylim(-0.1, 1.15)
                a.set_title(("(a) " if (i, j) == (0, 0) else "(b) " if (i, j) == (1, 0) else "")
                            + f"{dev}, {'full transition' if key == 'full' else str(key) + ' ps'}", fontsize=9)
                if j:
                    a.set_yticklabels([])
                if i:
                    a.set_xlabel("time from the input edge (ns)" if j == 1 else "")
            ax[i][0].set_ylabel("gate, normalised")
            for W_ in widths:
                raw = sl.parse_ngspice_raw(folder / f"d{W_}" / "run.raw")
                mod = np.interp(grid, sl.time_ns(raw), sl.signal(raw, "v(x1.gup)"))
                real = runs[W_][gate[dev]]
                win = (grid >= 4.9) & (grid <= 5.0 + W_ / 1e3 + 2.5)
                rows.append(dict(device=dev, width_ps=W_, real=float(real[win].max()), model=float(mod[win].max()),
                                 rms=float(np.sqrt(np.mean((mod[win] - real[win]) ** 2)))))
        fig.legend(*ax[0][0].get_legend_handles_labels(), frameon=False, loc="lower center", ncol=2,
                   fontsize=7.4, bbox_to_anchor=(0.5, -0.04))
        save(fig, "fig_gate_internal")
    return rows


# ------------------------------------------------------------------ 9, 10. the pad
def fig_pad_waveforms():
    import build_0917_deck_figures as f17
    import build_0924_deck_figures as b24
    import build_explainer_figures as bex
    devs = [("ex2", 810), ("inv_chain", 104), ("io_buf", 1505)]
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 3, figsize=(W, 2.5), gridspec_kw={"wspace": 0.3})
        for a, (dev, w_ps) in zip(ax, devs):
            w = w_ps / 1000.0
            span = b24.DEV[dev][5] if dev in b24.DEV else 3.4
            t_si, si, _ = f17.transistor_pad(dev, w_ps)
            t_si = t_si - 5.0
            d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / f"{dev}_short_high_w{w_ps}ps.csv")
            x = d["time_ns"] - 5.0
            a.plot(t_si, si, color=K_, lw=2.4, label="transistor-level reference", zorder=5)
            e_nat, _ = b24._peak_err(x, d["hspice_pad"], t_si, si, w)
            a.plot(x, d["hspice_pad"], color=BLUE, lw=1.6, ls=(0, (1.4, 1.4)), label="HSPICE native IBIS")
            t1 = b24._pick_build(dev)
            tt, _ku, pp = b24._cand(t1, f"d{w_ps}")
            e_t1, _ = b24._peak_err(tt, pp, t_si, si, w)
            a.plot(tt, pp, color=TEAL, lw=1.6, label="proposed (file + one stressed run)")
            top = max(float(np.nanmax(si)), float(np.nanmax(d["hspice_pad"])), float(np.nanmax(pp)))
            a.text(0.04, 0.97, f"native {e_nat:+.0f} %", transform=a.transAxes, color=BLUE, fontsize=7.6, va="top")
            a.text(0.04, 0.88, f"proposed {e_t1:+.0f} %", transform=a.transAxes, color=TEAL, fontsize=7.6, va="top")
            lead = 0.35 if span > 1 else 0.20
            a.set_xlim(w - lead, w + span); a.set_ylim(-0.08 * top, top * 1.42)
            a.set_xlabel("time (ns)")
            a.set_title(f"({'abc'[devs.index((dev, w_ps))]}) {dev}, {w_ps} ps", fontsize=8.5)
            a.grid(alpha=0.25, lw=0.4)
        ax[0].set_ylabel("pad voltage (V)")
        h, l = ax[0].get_legend_handles_labels()
        fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.17), fontsize=7.6)
        save(fig, "fig_pad_waveforms")


def fig_pad_summary():
    import build_0924_deck_figures as b24
    import stage_count_from_file as sc
    sel = b24._selector_picks()
    devs, nat, t1, dead = [], [], [], []
    for dev in sc.BUFFERS:
        n, alive = b24._native(dev)
        devs.append(dev)
        nat.append(n if (n is not None and alive) else np.nan)
        dead.append(not alive)
        t1.append(float(sel[dev]["rms_pct"]))
    x = np.arange(len(devs))
    with plt.rc_context(RC):
        fig, a = plt.subplots(figsize=(W, 2.7))
        a.bar(x - 0.19, nat, 0.36, color=BLUE, label="HSPICE native IBIS")
        a.bar(x + 0.19, t1, 0.36, color=TEAL, label="proposed (file + one stressed run)")
        top = np.nanmax(nat) * 1.22
        for i, isdead in enumerate(dead):
            if isdead:
                a.bar(i - 0.19, top * 0.93, 0.36, color="none", edgecolor="#AAAAAA", hatch="////", lw=0.8)
        for xi, v in zip(x, t1):
            a.text(xi + 0.19, v + 1.5, f"{v:.1f}", ha="center", fontsize=6.4, color=TEAL)
        a.axhline(10, color="#555555", ls="--", lw=0.8)
        a.text(len(devs) - 0.27, 10, "10 %", fontsize=7, color="#555555", ha="left", va="center")
        a.set_xticks(x, devs, rotation=30, ha="right")
        a.set_ylabel("worst stressed peak error (%)")
        a.set_ylim(0, top); a.set_xlim(-0.7, len(devs) - 0.3)
        h, l = a.get_legend_handles_labels()
        h.append(mpatches.Patch(facecolor="none", edgecolor="#AAAAAA", hatch="////"))
        l.append("native IBIS: no valid run")
        a.legend(h, l, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.16), fontsize=7.4)
        save(fig, "fig_pad_summary")
    return devs, nat, t1, dead


ALL = (fig_problem, fig_fit_knobs, fig_device, fig_stage_law, fig_blocks, fig_chain, fig_map, fig_gate_to_ku, fig_ku_fit,
       fig_ambiguity, fig_stress_use, fig_gate_internal, fig_rms_vs_k,
       fig_calibration, fig_gate_verify, fig_pad_waveforms, fig_pad_summary)

if __name__ == "__main__":
    want = sys.argv[1:]
    for f in ALL:
        if not want or f.__name__ in want:
            f()
