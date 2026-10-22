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

    Added for the 2026-10-15 rewrite of Sections F onward (all from stored results):
    fig_workflow      the procedure as a flow (file / assumed / fitted / measured)
    fig_target        the fit's target: tables, V-T waveforms, solved Ku/Kd, normalised target (ex2)
    fig_fit_score     what the residual measures: the gap, for a poor trial and for the fit
    fig_fit_search    the residual landscape and the three Nelder-Mead runs (fit_search.py)
    fig_one_vs_chain  one stage against the three-stage chain; where the delay is spent
    fig_fit_all       the fit of the selected candidate on all twelve buffers (file-only settings)
    fig_calib_mech    the threshold calibration: peak error vs v_t, bisection, waveforms
                      (calib_iterations.py)

    Added for v6 (2026-10-19):
    fig_replay_fails  Fig. 1: the probed gate under a complete transition and an 810 ps pulse, the
                      transistor's own solved K_u against the native element's replayed one, the pad
    fig_stage         one predriver stage: the inverter, the load, I_P, I_N and the normalized u, v
    fig_native_fail   why native has no valid run on the variant files: the table lead-in at 2.7 ps
                      against 200 rows and the shipped 8 ps; native's K_u as generated and resampled
    fig_target        gains the two-fixture schematic and the native element's own coefficient
    fig_pad_summary   marks the native bars obtained with resampled tables

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
        b.set_title("(b) a short pulse: the native IBIS model fails", fontsize=8.5)
        b.legend(frameon=False, loc="upper left", fontsize=7)
        save(fig, "fig_problem")


# ------------------------------------------------------------------ 1. where the replay fails
def settled_swing(dev: str) -> float:
    """The pad excursion of the transistor's complete transition into the test load, in volts
    (predriver_stages_2026-09-09/<dev>/full: rest level before the edge, high level after it)."""
    import predriver_stage_probe as psp
    full = psp.parse_tr0(cl.ST / dev / "full" / "run.tr0")
    t, v = np.asarray(full["time"], float) * 1e9, np.asarray(full["v(pad_sp)"], float)
    _, rest, high = psp.normalise(t, v, t, v)
    return float(high - rest)


def pct_axis(ax, swing: float, label: bool = True):
    """A right-hand axis reading the pad voltage as a percentage of the settled swing."""
    sec = ax.secondary_yaxis("right", functions=(lambda v: 100.0 * v / swing, lambda p: p * swing / 100.0))
    sec.spines["right"].set_visible(True)
    sec.tick_params(labelsize=6.5, length=2)
    if label:
        sec.set_ylabel("% of settled swing", fontsize=7)
    return sec


def fig_replay_fails():
    """Fig. 1 of the paper, on ex2. (a) Complete transition: input, the probed gate of the output
    device (n4, normalized) and the pad; the gate reaches its rail. (b) An 810 ps pulse: the gate
    turns back partway. (c) K_u solved from the transistor's own two fixture runs against the native
    element's replayed coefficient. (d) The pad: transistor against native."""
    import gate_ramp_prototype  # noqa: F401
    import build_0917_deck_figures as f17
    import build_0924_deck_figures as b24
    import predriver_stage_probe as psp
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
    d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / "ex2_short_high_w810ps.csv")
    x = d["time_ns"] - 5.0
    t_si, si, _ = f17.transistor_pad("ex2", 810)
    t_si = t_si - 5.0
    e_nat, _ = b24._peak_err(x, d["hspice_pad"], t_si, si, 0.81)
    win = (ts - 5.0 > 0) & (ts - 5.0 < 3.0)
    g_peak = float(g_st[win].max())
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 4, figsize=(W, 2.5), gridspec_kw={"wspace": 0.5, "width_ratios": (1.08, 1, 1, 1)})
        for a, (t, u, g, p) in zip(ax[:2], ((tf, sf["v(in_dig)"], g_full, p_full), (ts, ss["v(in_dig)"], g_st, p_st))):
            a.plot(t - 5.0, u / sup, color=GREY, lw=1.0, label="input")
            a.plot(t - 5.0, g, color=TEAL, lw=1.9, label="gate (probed)")
            a.plot(t - 5.0, p, color=K_, lw=1.5, label="pad")
            a.set_ylim(-0.1, 1.15)
        ax[0].set_xlim(-0.5, 4.0); ax[1].set_xlim(-0.5, 3.0); ax[1].set_yticklabels([])
        ax[0].set_ylabel("normalized")
        ax[0].set_title("(a) complete transition:\ngate reaches its rail", fontsize=7.6)
        ax[1].set_title(f"(b) 810 ps pulse:\ngate turns back at {g_peak:.2f}", fontsize=7.6)
        ax[1].legend(*ax[0].get_legend_handles_labels(), frameon=False, fontsize=5.8, loc="upper right")
        ax[1].axhline(g_peak, color=TEAL, lw=0.6, ls=":")
        c = ax[2]
        c.plot(x, d["silicon_ku"], color=K_, lw=1.6, label="solved from\nthe transistor")
        c.plot(x, d["hspice_ku"], color=BLUE, lw=1.5, ls=(0, (1.4, 1.4)), label="native,\nreplayed")
        c.set_xlim(-0.5, 3.0); c.set_ylim(-0.15, 1.35)
        c.set_ylabel("$K_u$")
        c.set_title("(c) 810 ps pulse:\n$K_u$ solved and replayed", fontsize=7.6)
        c.legend(frameon=False, fontsize=5.6, loc="upper right")
        e = ax[3]
        e.plot(t_si, si, color=K_, lw=1.6, label="transistor")
        e.plot(x, d["hspice_pad"], color=BLUE, lw=1.5, ls=(0, (1.4, 1.4)), label=f"native\n({e_nat:+.0f} % peak)")
        e.set_xlim(-0.5, 3.0); e.set_ylim(-0.3, 1.7)
        e.set_ylabel("pad (V)")
        pct_axis(e, p_high - p_rest)
        e.set_title("(d) 810 ps pulse:\nthe pad", fontsize=7.6)
        e.legend(frameon=False, fontsize=5.6, loc="upper right")
        for a in ax:
            a.tick_params(labelsize=7)
            a.set_xlabel("time (ns)", fontsize=8)
        save(fig, "fig_replay_fails")
    return dict(gate_peak=g_peak, native_peak_err=e_nat, ku_si_peak=float(d["silicon_ku"][(x > 0) & (x < 3)].max()),
                ku_nat_peak=float(d["hspice_ku"][(x > 0) & (x < 3)].max()))


# ------------------------------------------------------------------ 2b. the stage law as a signal flow
def fig_stage_flow(vt: float = 0.3, x_lin: float = 0.45):
    """Equation (19) drawn as a signal flow: the charging path (gate factor, rate, drain factor),
    the discharging path, the node as an integrator, and the output fed back into the two drain
    factors and on to the next stage. Each factor block carries a thumbnail of its curve."""
    with plt.rc_context(RC):
        fig, a = plt.subplots(figsize=(3.3, 2.85))
        a.set_xlim(0, 100); a.set_ylim(-6, 76); a.axis("off")
        YT, YB, YM = 56, 20, 38                                   # the two paths and the node

        def hinge(x, y, w, h):                                    # h(.) : zero to v_t, then linear to one
            xs = [x + 1.5, x + 1.5 + (w - 3) * vt, x + w - 1.5]
            ys = [y + 1.5, y + 1.5, y + h - 1.5]
            a.plot(xs, ys, color=TEAL, lw=1.2)
            a.plot([xs[1], xs[1]], [y + 0.6, y + 2.4], color=K_, lw=0.6)

        def taper(x, y, w, h):                                    # r(.) : one, then down to zero within x_lin of the rail
            xs = [x + 1.5, x + 1.5 + (w - 3) * (1 - x_lin), x + w - 1.5]
            ys = [y + h - 1.5, y + h - 1.5, y + 1.5]
            a.plot(xs, ys, color=RED, lw=1.2)

        for y, lab_in, lab_h, lab_s, lab_r, lab_sign in ((YT, "$u$", "$h(u)$", "$s_{up}$", "$r(1-v)$", "+"),
                                                       (YB, "$1-u$", "$h(1-u)$", "$s_{dn}$", "$r(v)$", "−")):
            a.text(0.0, y, lab_in, fontsize=7.6, va="center", ha="left")
            darrow(a, 10.5, y, 14, y)
            dbox(a, 14, y - 6, 16, 12, "")
            hinge(14, y - 6, 16, 12)
            a.text(22, y + 7.0, lab_h, fontsize=7.2, ha="center", va="bottom")
            darrow(a, 30, y, 35.5, y)
            a.add_patch(mpatches.Circle((39, y), 3.5, fc="white", ec=K_, lw=0.9))
            a.text(39, y, "×", fontsize=8, ha="center", va="center")
            a.text(39, y + 5.0, lab_s, fontsize=7.4, ha="center", va="bottom")
            darrow(a, 42.5, y, 48, y)
            dbox(a, 48, y - 6, 16, 12, "")
            taper(48, y - 6, 16, 12)
            a.text(56, y + 7.0, lab_r, fontsize=7.2, ha="center", va="bottom")
            darrow(a, 64, y, 70, y)
            a.text(72.3, y + (2.6 if y == YT else -2.6), lab_sign, fontsize=9, ha="center", va="center")
        a.plot([70, 70], [YT, YB], color=K_, lw=0.9)
        a.add_patch(mpatches.Circle((70, YM), 2.2, fc="white", ec=K_, lw=0.9))
        a.text(70, YM, "Σ", fontsize=7, ha="center", va="center")
        darrow(a, 72.2, YM, 77, YM)
        dbox(a, 77, YM - 6, 13, 12, "$\\int dt$", fs=8)
        darrow(a, 90, YM, 99, YM)
        a.text(94.5, YM + 1.8, "$v$", fontsize=8.5, ha="center", va="bottom")
        a.text(99.5, YM - 3.6, "to the\nnext stage", fontsize=6.2, ha="right", va="top")
        a.plot([93, 93, 56, 56], [YM, YT + 13, YT + 13, YT + 6], color=K_, lw=0.7, ls="--")
        a.plot([93, 93, 56, 56], [YM, YB - 13, YB - 13, YB - 6], color=K_, lw=0.7, ls="--")
        a.text(75, YT + 13.6, "$v$ fed back", fontsize=6.4, ha="center", va="bottom")
        a.text(22, YT + 12.5, "charging term", fontsize=7, ha="center", va="bottom", color="#333333")
        a.text(22, YB - 12.5, "discharging term", fontsize=7, ha="center", va="top", color="#333333")
        a.text(50, -5.5, "$dv/dt = s_{up}\\,h(u)\\,r(1-v) - s_{dn}\\,h(1-u)\\,r(v)$   (19)", fontsize=7.6,
               ha="center", va="bottom")
        save(fig, "fig_stage_flow")


# ------------------------------------------------------------------ 1b. one stage, drawn
def fig_stage():
    """One predriver stage as Section II-A sees it: a CMOS inverter whose output node drives a
    lumped capacitance; the pull-up current I_P into the node and the pull-down current I_N out of
    it; the normalized input u and output v."""
    with plt.rc_context(RC):
        fig, a = plt.subplots(figsize=(3.3, 2.15))
        a.set_xlim(0, 100); a.set_ylim(0, 66); a.axis("off")
        lw = 1.2

        def mos(x, y, pmos):
            # channel at x, gate plate at x - 4, source/drain stubs to the right; y is the centre
            a.plot([x, x], [y - 7, y + 7], color=K_, lw=lw)
            a.plot([x - 4, x - 4], [y - 5, y + 5], color=K_, lw=lw)
            a.plot([x, x + 8], [y + 6, y + 6], color=K_, lw=lw)
            a.plot([x, x + 8], [y - 6, y - 6], color=K_, lw=lw)
            a.plot([x + 8, x + 8], [y + 6, y + 13], color=K_, lw=lw)
            a.plot([x + 8, x + 8], [y - 13, y - 6], color=K_, lw=lw)
            if pmos:
                a.add_patch(mpatches.Circle((x - 6, y), 1.6, fc="white", ec=K_, lw=lw))
                a.plot([x - 14, x - 8], [y, y], color=K_, lw=lw)
            else:
                a.plot([x - 14, x - 4], [y, y], color=K_, lw=lw)

        X, YP, YN = 38, 46, 20
        mos(X, YP, True); mos(X, YN, False)
        a.plot([X + 8, X + 8], [YP + 13, 62], color=K_, lw=lw)                  # PMOS source to V_DD
        a.plot([X + 2, X + 14], [62, 62], color=K_, lw=lw)
        a.text(X + 8, 64.5, "$V_{DD}$", ha="center", va="bottom", fontsize=8)
        a.plot([X + 8, X + 8], [4, YN - 13], color=K_, lw=lw)                   # NMOS source to ground
        a.plot([X + 2, X + 14], [4, 4], color=K_, lw=lw)
        a.plot([X + 8, X + 8], [YN + 13, YP - 13], color=K_, lw=lw)             # the output node
        a.plot([X - 14, X - 14], [YN, YP], color=K_, lw=lw)                     # the common gate
        a.plot([X - 30, X - 14], [33, 33], color=K_, lw=lw)
        a.text(X - 31, 33, "$V_{in}$", ha="right", va="center", fontsize=8.5)
        a.text(X - 25, 35.5, "$u = (V_{DD} - V_{in})/V_{DD}$", ha="center", va="bottom", fontsize=6.2, color="#444444")
        a.plot([X + 8, X + 40], [33, 33], color=K_, lw=lw)                      # to the load and the next stage
        a.plot(X + 8, 33, "o", ms=3, color=K_)
        a.text(X + 5.5, 35.5, "$V_o$", ha="right", va="bottom", fontsize=8.5)
        a.text(X + 25, 35.5, "$v = V_o/V_{DD}$", ha="center", va="bottom", fontsize=6.2, color="#444444")
        cx = X + 28                                                            # the lumped capacitance
        a.plot([cx, cx], [33, 24], color=K_, lw=lw)
        a.plot([cx - 4, cx + 4], [24, 24], color=K_, lw=lw)
        a.plot([cx - 4, cx + 4], [20.5, 20.5], color=K_, lw=lw)
        a.plot([cx, cx], [20.5, 4], color=K_, lw=lw)
        a.plot([X + 2, cx + 6], [4, 4], color=K_, lw=lw)
        a.text(cx + 5.5, 22.2, "$C$", ha="left", va="center", fontsize=8.5)
        a.annotate("", (X + 40 + 6, 33), (X + 40, 33), arrowprops=dict(arrowstyle="-|>", color=K_, lw=lw))
        a.text(X + 47, 33, "next\nstage", ha="left", va="center", fontsize=7)
        a.annotate("", (X + 8, YP - 10.5), (X + 8, YP - 6), arrowprops=dict(arrowstyle="-|>", color=TEAL, lw=1.6))
        a.text(X + 10, YP - 8, "$I_P$", color=TEAL, ha="left", va="center", fontsize=8.5)
        a.annotate("", (X + 8, YN + 6), (X + 8, YN + 10.5), arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.6))
        a.text(X + 10, YN + 8, "$I_N$", color=RED, ha="left", va="center", fontsize=8.5)
        a.text(2, 10, "(1): $C\\,dV_o/dt = I_P - I_N$", fontsize=7.0, va="center")
        save(fig, "fig_stage")


# ------------------------------------------------------------------ V-B. why native has no valid run
def fig_native_fail():
    """(a) The lead-in of the rising V-T table into the 0 V fixture: ex2_base as generated (2.7 ps),
    the same table resampled onto 200 rows, and the shipped ex2 table (8 ps), on a millivolt scale.
    (b) The native element's K_u under the 812 ps pulse, on the as-generated and on the resampled
    file, against the K_u solved from the transistor's own fixture runs."""
    import csv as _csv
    import native_revived_variants as nrv
    import spicelab as sl
    camp = ROOT / "results" / "variant_stress_cases_2026-09-04" / "ex2_base" / "depth50_w812ps"
    rev = ROOT / "results" / "native_revived_variants_2026-10-18" / "ex2_base" / "d50"
    ship = ROOT / "results" / "gate_cascade_prototype_2026-09-09" / "ex2_c1.7" / "input_ccomp.ibs"
    t_as, v_as = nrv.first_rising_table((camp / "native" / "input.ibs").read_text(errors="ignore"))
    t_rs, v_rs = nrv.first_rising_table((rev / "input.ibs").read_text(errors="ignore"))
    t_sh, v_sh = nrv.first_rising_table(ship.read_text(errors="ignore"))
    rows = list(_csv.DictReader((camp / "waveforms.csv").open()))
    t_w = np.array([float(r["time_ns"]) for r in rows]) - 5.0
    ku_si = np.array([float(r["silicon_ku"]) for r in rows])

    def ku_of(tr0):
        raw = sl.parse_hspice_tr0(tr0)
        return sl.time_ns(raw) - 5.0, np.asarray(raw["v(ku)"], float)

    t_dead, ku_dead = ku_of(camp / "native" / "run.tr0")
    t_live, ku_live = ku_of(rev / "run.tr0")
    step_as, step_rs = 1e12 * (t_as[1] - t_as[0]), 1e12 * (t_rs[1] - t_rs[0])
    cc_pf = float(_re.search(r"^C_comp\s+([0-9.]+)", (camp / "native" / "input.ibs").read_text(errors="ignore"), _re.M).group(1))

    lead = 0.30                                        # ns: the pre-edge part the probe implicated

    def ripple_mV(t, v):                               # rms about a 50 ps moving average, before the edge
        m = t < lead * 1e-9
        tt, vv = t[m], v[m]
        base = np.array([vv[np.abs(tt - x) <= 25e-12].mean() for x in tt])
        return 1e3 * float(np.std(vv - base))

    rip_as, rip_rs, rip_sh = ripple_mV(t_as, v_as), ripple_mV(t_rs, v_rs), ripple_mV(t_sh, v_sh)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(2, 1, figsize=(3.3, 3.9), gridspec_kw={"hspace": 0.62})
        a = ax[0]
        a.plot(t_as * 1e9, v_as * 1e3, color=TEAL, lw=0.9, label=f"as generated ({step_as:.1f} ps)")
        a.plot(t_rs * 1e9, v_rs * 1e3, color=ORANGE, lw=0.9, marker="o", ms=2.0, label=f"resampled, {len(t_rs)} rows ({step_rs:.0f} ps)")
        a.plot(t_sh * 1e9, v_sh * 1e3, color=GREY, lw=1.1, ls="--", label="shipped ex2 file (8 ps)")
        a.set_xlim(0, 0.6); a.set_ylim(-3, 6)
        a.set_xlabel("table time (ns)"); a.set_ylabel("pad voltage (mV)")
        a.set_title("(a) lead-in of the rising V–T table (0 V fixture)", fontsize=8)
        a.legend(frameon=False, fontsize=5.8, loc="upper left")
        b = ax[1]
        b.plot(t_w, ku_si, color=K_, lw=1.6, label="solved from the transistor")
        b.plot(t_dead, ku_dead, color=TEAL, lw=1.3, label="native, file as generated")
        b.plot(t_live, ku_live, color=BLUE, lw=1.4, ls=(0, (1.4, 1.4)), label=f"native, {len(t_rs)} rows")
        b.set_xlim(-0.3, 3.0); b.set_ylim(-0.1, 1.4)
        b.set_xlabel("time from the input edge (ns)"); b.set_ylabel("$K_u$")
        b.set_title("(b) ex2_base, 812 ps pulse", fontsize=8)
        b.legend(frameon=False, fontsize=6, loc="upper right")
        save(fig, "fig_native_fail")
    return dict(step_as=step_as, step_rs=step_rs, rows_rs=len(t_rs), ripple_as_mV=rip_as, ripple_rs_mV=rip_rs,
                ripple_sh_mV=rip_sh, cc_pf=cc_pf,
                ku_dead_max=float(ku_dead[(t_dead > 0) & (t_dead < 3)].max()),
                ku_live_max=float(ku_live[(t_live > 0) & (t_live < 3)].max()))


# ------------------------------------------------------------------ 5c. the fit, seen as knobs
def fig_fit_knobs():
    """What each fitted number does to the model's K_u(t), against the file's curve (ex2,
    K = 3, map (0.57, 0.64), x_lin = 0.45), and how a fit progresses from a first guess."""
    sf = ROOT / "results" / "stage_law_doc_2026-10-01" / "shape_fileonly"
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
        su, sd, vt0 = round(base[0], 2), round(base[1], 2), round(base[2], 2)
        panels = ((ax[0][0], "s_up", (round(su / 2, 2), su, round(su * 2, 2)), (0, 3.0), "(a) $s_{up}$ sets the rising edge"),
                  (ax[0][1], "s_dn", (round(sd / 2, 2), sd, round(sd * 2, 2)), (10.0, 13.0), "(b) $s_{dn}$ sets the falling edge"),
                  (ax[1][0], "vt", (0.30, 0.50, vt0), (0, 3.0), "(c) $v_t$ sets the delay between stages"))
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
        steps = ((8.0, 8.0, 0.40, "first guess"), (su, 8.0, 0.40, "$s_{up}$ adjusted"), (su, sd, 0.40, "$s_{dn}$ adjusted"),
                 (su, sd, vt0, "$v_t$ adjusted: the fit"))
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


# ------------------------------------------------------------------ plain block-diagram helpers
def dbox(a, x, y, w, h, text, fs=7.2, ls="-", lw=0.9):
    a.add_patch(mpatches.Rectangle((x, y), w, h, fc="white", ec=K_, lw=lw, ls=ls))
    a.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.2)


def darrow(a, x0, y0, x1, y1, text=None, above=True, fs=7.0, dy=1.3):
    a.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=K_, lw=0.9, shrinkA=0, shrinkB=0,
                                                      mutation_scale=8))
    if text:
        a.text((x0 + x1) / 2, (y0 + y1) / 2 + (dy if above else -dy), text, ha="center",
               va="bottom" if above else "top", fontsize=fs)


# ------------------------------------------------------------------ 3. the signal path
def fig_blocks():
    """(a) The buffer as an IBIS file describes it; (b) the model's signal path, aligned under it.
    Plain block diagram: rectangles, arrows, signal names and equation numbers."""
    with plt.rc_context(RC):
        fig, a = plt.subplots(figsize=(W, 3.75))
        a.set_xlim(0, 100); a.set_ylim(0, 67); a.axis("off")
        # (a) the buffer
        a.text(0.5, 65.5, "(a) the buffer", fontsize=8.5, va="center")
        a.text(1.0, 52, "input\npin", fontsize=7.2, va="center", ha="left")
        darrow(a, 7.0, 52, 10, 52)
        for i, x in enumerate((10, 20.5)):
            dbox(a, x, 47, 8.5, 10, f"inverter\n{i + 1}")
            darrow(a, x + 8.5, 52, x + 10.5, 52)
        a.text(33.2, 52, "…", fontsize=11, ha="center", va="center")
        darrow(a, 35, 52, 37, 52)
        dbox(a, 37, 47, 8.5, 10, "inverter\n$K$")
        darrow(a, 45.5, 52, 50, 52, "gate")
        dbox(a, 50, 44.5, 17, 15, "output stage:\npull-up device,\npull-down device", fs=6.8)
        darrow(a, 67, 52, 72, 52, "die")
        dbox(a, 72, 47, 8, 10, "$C_{comp}$")
        darrow(a, 80, 52, 83.5, 52)
        dbox(a, 83.5, 47, 9.5, 10, "package\n$R$, $L$, $C$")
        darrow(a, 93, 52, 98.5, 52)
        a.text(96, 54.2, "pad", fontsize=8, ha="center")
        a.plot([10, 45.5], [60.0, 60.0], color=K_, lw=0.7)
        a.plot([10, 10], [59, 60], color=K_, lw=0.7); a.plot([45.5, 45.5], [59, 60], color=K_, lw=0.7)
        a.text(27.7, 60.8, "predriver (not described in the file)", ha="center", fontsize=7, color=K_)
        a.plot([50, 93], [43.0, 43.0], color=K_, lw=0.7)
        a.plot([50, 50], [43, 44], color=K_, lw=0.7); a.plot([93, 93], [43, 44], color=K_, lw=0.7)
        a.text(71.5, 42.0, "described in the file: I–V tables, V–T waveforms of complete transitions, $C_{comp}$, package",
               ha="center", va="top", fontsize=7, color=K_)
        # (b) the model
        a.text(0.5, 36.5, "(b) the model", fontsize=8.5, va="center")
        a.text(1.5, 26, "$V_{in}$", fontsize=8, va="center")
        darrow(a, 5.2, 26, 8.5, 26)
        dbox(a, 8.5, 21, 13.5, 10, "comparator\n$V_{DD}/2$, (20)")
        darrow(a, 22, 26, 25, 26, "$u_1$")
        for i, lab in enumerate(("stage 1", "stage 2")):
            dbox(a, 25 + 10.5 * i, 21, 8.5, 10, lab + "\n(19)")
            darrow(a, 33.5 + 10.5 * i, 26, 35.5 + 10.5 * i, 26)
        a.text(48.2, 26, "…", fontsize=11, ha="center", va="center")
        darrow(a, 50, 26, 52, 26)
        dbox(a, 52, 21, 8.5, 10, "stage $K$\n(19)")
        darrow(a, 60.5, 26, 66, 26, "$G_{UP}$")
        dbox(a, 66, 21, 10, 10, "map $M$\n(22)")
        darrow(a, 76, 26, 81, 26, "$K_u$")
        dbox(a, 81, 13, 12, 18, "I–V tables,\n$C_{comp}$,\npackage (24)")
        darrow(a, 93, 22, 98.5, 22)
        a.text(96, 24.2, "pad", fontsize=8, ha="center")
        a.plot([63, 63], [26, 15], color=K_, lw=0.9)
        darrow(a, 63, 15, 66, 15)
        dbox(a, 66, 10, 10, 10, "map $M$\n(23)")
        a.text(60.4, 17.5, "$1-G_{UP}$", fontsize=7, ha="right")
        darrow(a, 76, 15, 81, 15, "$K_d$")
        a.plot([8.5, 76], [34.0, 34.0], color=K_, lw=0.7)
        a.plot([8.5, 8.5], [33, 34], color=K_, lw=0.7); a.plot([76, 76], [33, 34], color=K_, lw=0.7)
        a.text(42, 34.8, "proposed: (19)–(23), identified in Section IV", ha="center", fontsize=7, color=K_)
        a.plot([81, 93], [9.5, 9.5], color=K_, lw=0.7)
        a.plot([81, 81], [9.5, 10.5], color=K_, lw=0.7); a.plot([93, 93], [9.5, 10.5], color=K_, lw=0.7)
        a.text(87, 8.4, "from the file, unchanged", ha="center", va="top", fontsize=7, color=K_)
        a.text(42, 4.2, "the $K$ stages share one parameter set $\\{s_{up}, s_{dn}, v_t, x_{lin}, p\\}$",
               ha="center", fontsize=7, color=K_)
        save(fig, "fig_blocks")


# ------------------------------------------------------------------ 4. one chain, two inputs
# ex2 as the file-only procedure builds it: the selected candidate (K = 3, map (0.5, 0.7), C_comp
# estimated at 2.64 pF), its fit to the file and its threshold after calibration (ledger_ex2.csv)
EX2 = dict(s_up=2.5519, s_dn=2.6936, vt_fit=0.6999, vt_cal=0.6316, x_lin=0.45, K=3, shape=(0.5, 0.7), cc=2.64)


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
        ax[0][1].legend(*ax[0][0].get_legend_handles_labels(), frameon=False, loc="center right", fontsize=7,
                        bbox_to_anchor=(1.0, 0.36))
        ax[1][0].legend(frameon=False, loc="lower right")
        ax[0][0].set_xlim(-0.3, 4.2)
        tag(ax[0][0], "(a)", x=0.0); tag(ax[0][1], "(b)", x=0.0)
        save(fig, "fig_chain")
    st = chain_stages(cases[1][1], p["s_up"], p["s_dn"], p["vt_cal"], p["x_lin"], p["K"])
    return dict(gate_peak=float(st[-1].max()), ku_peak=float(prior(st[-1], *p["shape"]).max()),
                node_peaks=[float(v.max()) for v in st])


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
        b.plot(gg, prior(gg, 0.57, 0.64), color=RED, lw=1.4, ls="--", label="formula (22), fitted")
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
    K_u(t) (ex2, K = 3, file-only setting; results/stage_law_doc_2026-10-01/shape_fileonly). The fitted gates
    differ, the full-swing K_u(t) does not - and under a short pulse the two models separate."""
    import json
    sf = ROOT / "results" / "stage_law_doc_2026-10-01" / "shape_fileonly"
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
    return {name: dict(vt=r["vt"], rms=r["rms"], peak810=float(prior(g_cut, v, a_).max()))
            for v, a_, col, name, r, g_full, g_cut in cases}


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
        fig, ax = plt.subplots(2, 2, figsize=(W, 4.5), gridspec_kw={"wspace": 0.52, "hspace": 0.5})
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
        sw = settled_swing("ex2")
        for q in (a, b, c, d):
            pct_axis(q, sw, label=True)
        save(fig, "fig_stress_use")
    return min(peaks0), max(peaks0), peak


# ------------------------------------------------------------------ 4b. gate -> map -> Ku
def fig_gate_to_ku():
    """The whole construction on ex2 (K = 3): the stage law gives g(t); the map turns each
    value of g into a conducting fraction; the result is the model's K_u(t). The same sample
    instants are marked in all three panels. Top row: full transition, against the file's own
    K_u(t) - this comparison is the fit. Bottom row: an 810 ps pulse - the gate turns back and
    the map is only read over part of its range."""
    p = EX2
    vtm, a_ = p["shape"]
    z = np.load(DOCDIR / "shape_fileonly" / "target_ex2.npz")
    grid, u_full, target = z["grid"], z["u"], z["target"]
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
    return dict(gate_peak=float(g_cut.max()), ku_peak=float(prior(g_cut, vtm, a_).max()),
                rms=float(np.sqrt(np.mean((prior(g_full, vtm, a_) - target) ** 2))))



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
                   bbox_to_anchor=(0.5, -0.22))
        tag(ax[0], "(a)", x=0.0); tag(ax[1], "(b)", x=0.0)
        save(fig, "fig_ku_fit")


# ------------------------------------------------------------------ 6. residual vs K
def band(v):
    best = min(v)
    return [k for k in range(1, len(v) + 1) if v[k - 1] <= 1.25 * best][:3]


def fig_rms_vs_k():
    rows = [r for r in csv.DictReader((SC / "step1_summary.csv").open()) if r["pass_"] == "est_knee"]
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
        fig, ax = plt.subplots(1, 3, figsize=(W, 2.5), gridspec_kw={"wspace": 0.62})
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
            t1 = pick_build(dev)
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
            pct_axis(a, settled_swing(dev), label=True)
        ax[0].set_ylabel("pad voltage (V)")
        h, l = ax[0].get_legend_handles_labels()
        fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.17), fontsize=7.6)
        save(fig, "fig_pad_waveforms")


def fig_pad_summary(revived: dict | None = None):
    """Worst stressed peak error on the twelve buffers. `revived` maps a buffer on which native had
    no valid run as generated to its worst error with the V-T tables resampled (starred bars)."""
    import build_0924_deck_figures as b24
    import stage_count_from_file as sc
    revived = revived or {}
    devs, nat, t1, dead, star = [], [], [], [], []
    for dev in sc.BUFFERS:
        n, alive = b24._native(dev)
        devs.append(dev)
        if not alive and dev in revived:
            nat.append(revived[dev]); dead.append(False); star.append(True)
        else:
            nat.append(n if (n is not None and alive) else np.nan); dead.append(not alive); star.append(False)
        t1.append(selected(dev)[2])
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
        for xi, v, st in zip(x, nat, star):
            if not np.isnan(v):
                a.text(xi - 0.19, v + 1.5, f"{v:.0f}" + ("*" if st else ""), ha="center", fontsize=6.4, color=BLUE)
        a.axhline(10, color="#555555", ls="--", lw=0.8)
        a.text(len(devs) - 0.27, 10, "10 %", fontsize=7, color="#555555", ha="left", va="center")
        a.set_xticks(x, devs, rotation=30, ha="right")
        a.set_ylabel("worst stressed peak error (%)")
        a.set_ylim(0, top); a.set_xlim(-0.7, len(devs) - 0.3)
        h, l = a.get_legend_handles_labels()
        if any(dead):
            h.append(mpatches.Patch(facecolor="none", edgecolor="#AAAAAA", hatch="////"))
            l.append("native IBIS: no valid run")
        if any(star):
            l[0] = "HSPICE native IBIS (*: V–T tables resampled, see text)"
        a.legend(h, l, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.16), fontsize=7.4)
        save(fig, "fig_pad_summary")
    return devs, nat, t1, dead


# ================================================================== data helpers (new sections)
import re as _re

DOCDIR = ROOT / "results" / "stage_law_doc_2026-10-01"
DEVS = ("ex2", "ex2_base", "ex2_slowpre", "ex2_skewp", "ex2_weak", "ex2_nomiller",
        "inv_chain", "inv_base8", "inv_stage4", "inv_skewp", "inv_weak", "io_buf")
# One rule for x_lin. The selector study (selector_from_one_run_2026-09-23) had x_lin fitted on
# inv_chain (0.28) and io_buf (0.41) and fixed at 0.45 on the other ten. stage_law_model_checks
# (results/stage_law_model_checks_2026-10-22) rebuilt every candidate of those two with x_lin =
# 0.45 and selected by the same rule, the pad rms at the calibration width; those two picks
# replace the selector's, so that the document describes one method on all twelve buffers.
CHECKS = ROOT / "results" / "stage_law_model_checks_2026-10-22" / "checks.csv"


def uniform_picks() -> dict:
    """{buffer: checks.csv row} of the candidate selected among the uniform (x_lin = 0.45) builds
    of each buffer the checks rebuilt."""
    out = {}
    if not CHECKS.exists():
        return out
    for r in csv.DictReader(CHECKS.open(encoding="utf-8")):
        if r["check"] != "xlin_uniform":
            continue
        dev = r["dev"]
        if dev not in out or float(r["pad_rms_calib_mV"]) < float(out[dev]["pad_rms_calib_mV"]):
            out[dev] = r
    return out


def selected(dev: str):
    """(K, (vt_map, a), worst peak error % over the five widths) of the candidate selected on
    this buffer: the uniform build where the checks rebuilt it, else the selector's pick."""
    u = uniform_picks()
    if dev in u:
        r = u[dev]
        vt, a = (float(x) for x in r["shape"].split("/"))
        return int(r["K"]), (vt, a), float(r["worst_peak_pct"])
    import build_0924_deck_figures as b24
    p = b24._selector_picks()[dev]
    k_str, sh_str = p["rms"].split()
    vt, a = (float(x) for x in sh_str.split("/"))
    return int(k_str[1:]), (vt, a), float(p["rms_pct"])


def pick_build(dev: str) -> Path:
    """The build folder of the selected candidate (see selected())."""
    u = uniform_picks()
    if dev in u:
        return Path(u[dev]["folder"])
    import build_0924_deck_figures as b24
    return b24._pick_build(dev)


def sensitivity_rows() -> list:
    """The x_lin sensitivity rows of the checks (ex2 and inv_chain at 0.35 and 0.55)."""
    if not CHECKS.exists():
        return []
    return [r for r in csv.DictReader(CHECKS.open(encoding="utf-8")) if r["check"] == "xlin_sensitivity"]
_STG = _re.compile(r"^BSTG(\d+) .*?\(([0-9.eE+-]+) \* max\(min\(\(V\(\w+\) - ([0-9.eE+-]+)\) / [0-9.eE+-]+, 1\), 0\)"
                   r" \* min\(1, \(1 - V\(\w+\)\) / ([0-9.eE+-]+)\) - ([0-9.eE+-]+) \* max", _re.M)
ORANGE = "#C9862B"


def stage_params(sub_text):
    """(s_up, s_dn, vt, x_lin, p) of each stage of the pull-up chain, as gate_chain_prototype
    wrote them into the subcircuit (rates in 1/ns)."""
    rows = sorted((int(m.group(1)), float(m.group(2)), float(m.group(5)), float(m.group(3)), float(m.group(4)))
                  for m in _STG.finditer(sub_text))
    assert rows, "no BSTG lines"
    return [(su, sd, vt, xl, 1.0) for _, su, sd, vt, xl in rows]


def shipped_target(dev, raw_path):
    """The target of the fit (26) exactly as fit_chain_ku forms it: the shipped model's gate-driven
    Ku (v(x1.kugate_base)) through one full transition, normalised by (25) on the 2 ps fit grid,
    plus the chain input u(t) (a 10 ns pulse from the mid-point of the input edge)."""
    import gate_ramp_prototype as gp
    import spicelab as sl
    raw = sl.parse_ngspice_raw(Path(raw_path))
    tf, kb = sl.time_ns(raw), sl.signal(raw, "v(x1.kugate_base)")
    grid = np.arange(4.0, 21.0, cl.DT)
    t_on = 5.0 + gp.EDGE_PS.get(dev, 1.0) / 2000.0
    u = ((grid >= t_on) & (grid < t_on + 10.0)).astype(float)
    k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
    target = np.interp(grid, tf, np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0))
    return grid, u, target, t_on


def file_only_builds():
    """The candidate the file-only procedure selected on each of the twelve buffers
    (stage_count_from_file steps 6/8 at the knee C_comp, selector_from_one_run), with its stage
    numbers before calibration (= the fit (26)) and after, the fit's own target and residual.
    Also written to fit_all.csv for the document's table."""
    import gate_ramp_prototype as gp  # noqa: F401  (import order: before the deck modules)
    import stage_count_from_file as sc
    knet = {r["buffer"]: r["K_netlist"] for r in csv.DictReader((SC / "step8_picks.csv").open())}
    out = []
    for dev in DEVS:
        K, (vt_m, a_m), worst = selected(dev)             # the waveform-rms selector (29), as in the pad table
        bdir = pick_build(dev)
        pre = stage_params((bdir / "calib" / "it00" / "driver.sub").read_text(encoding="utf-8"))
        post = stage_params((bdir / "driver_chain.sub").read_text(encoding="utf-8"))
        assert len(pre) == K == len(post)
        raw = SC / "knee_models" / sc.dcc_name("step8", dev) / "shipped" / "full" / "run.raw"
        grid, u, target, t_on = shipped_target(dev, raw)
        g = cl.simulate_chain(u, pre)
        model = prior(g, vt_m, a_m)
        rms = float(np.sqrt(np.mean((model - target) ** 2)))
        out.append(dict(dev=dev, K=K, shape=(vt_m, a_m), cc=sc.est_cc(dev, "knee"), k_net=int(knet[dev]),
                        s_up=pre[0][0], s_dn=pre[0][1], vt_fit=pre[0][2], vt_cal=post[0][2], x_lin=pre[0][3],
                        rate_scale=post[0][0] / pre[0][0],
                        rms=rms, t=grid - t_on, target=target, model=model, gate=g,
                        worst=worst))
    with (DOCDIR / "fit_all.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["buffer", "C_comp_pF", "K_selected", "K_netlist", "vt_map", "a", "s_up", "s_dn", "vt_fit", "vt_calibrated",
                    "rate_scale_calibrated", "x_lin", "fit_rms", "worst_peak_pct"])
        for r in out:
            w.writerow([r["dev"], r["cc"], r["K"], r["k_net"], r["shape"][0], r["shape"][1], f"{r['s_up']:.4f}",
                        f"{r['s_dn']:.4f}", f"{r['vt_fit']:.4f}", f"{r['vt_cal']:.4f}", f"{r['rate_scale']:.3f}", r["x_lin"],
                        f"{r['rms']:.4f}", r["worst"]])
    return out


def ex2_ledger():
    """ex2 through the procedure with the file-only settings (C_comp 2.64 pF by the knee rule): the
    step-1 residual against K, the band, and for each of the nine candidates its fitted numbers,
    fit residual, pad peak before calibration, threshold after calibration, peak error and waveform
    rms at the calibration width, and the worst peak error over the five widths. ledger_ex2.csv."""
    import gate_ramp_prototype as gp
    import build_0917_deck_figures as f17
    import build_0924_deck_figures as b24
    import stage_count_from_file as sc
    gp.VARIANT_NAME = "ex2"
    w = 0.810
    t_si, si, _ = f17.transistor_pad("ex2", 810)
    t_si = t_si - 5.0
    peak = float(si[(t_si >= w - 0.3) & (t_si <= w + 2.6)].max())
    step1 = next(r for r in csv.DictReader((SC / "step1_summary.csv").open())
                 if r["pass_"] == "est_knee" and r["buffer"] == "ex2" and r["chain"] == "pull-up")
    rms_by_k = [float(x) for x in step1["rms_by_K"].split()]
    band = sc.plateau_band("ex2")
    selb = {(int(r["K"]), float(r["vt"]), float(r["alpha"])): r
            for r in csv.DictReader((ROOT / "results/selector_from_one_run_2026-09-23/selector_builds.csv").open())
            if r["buffer"] == "ex2"}
    grid, u, target, t_on = shipped_target("ex2", SC / "knee_models/ex2_c2.64/shipped/full/run.raw")
    rows = []
    for (k, sh), folder in b24.CAND.items():
        vt_m, a_m = (float(x) for x in sh.split("_"))
        pre = stage_params((folder / "calib" / "it00" / "driver.sub").read_text(encoding="utf-8"))
        post = stage_params((folder / "driver_chain.sub").read_text(encoding="utf-8"))
        model = prior(cl.simulate_chain(u, pre), vt_m, a_m)
        z = np.load(DOCDIR / "before_calibration" / f"K{k}_{sh}.npz")
        s = selb[(k, vt_m, a_m)]
        rows.append(dict(K=k, shape=(vt_m, a_m), s_up=pre[0][0], s_dn=pre[0][1], vt_fit=pre[0][2],
                         rms=float(np.sqrt(np.mean((model - target) ** 2))), peak0=float(z["pad"].max()),
                         vt_cal=post[0][2], peak_err=float(s["peak_at_calib_pct"]), pad_rms=float(s["pad_rms_at_calib_mV"]),
                         lag=float(s["lag_calib_ps"]), worst=float(s["worst_peak_pct"]), selected=(k, sh) == b24.PICK))
    with (DOCDIR / "ledger_ex2.csv").open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["K", "vt_map", "a", "s_up", "s_dn", "vt_fit", "fit_rms", "pad_peak_before_calibration_V",
                     "vt_calibrated", "peak_err_calib_pct", "pad_rms_calib_mV", "lag_calib_ps", "worst_peak_pct", "selected"])
        for r in rows:
            wr.writerow([r["K"], r["shape"][0], r["shape"][1], f"{r['s_up']:.4f}", f"{r['s_dn']:.4f}", f"{r['vt_fit']:.4f}",
                         f"{r['rms']:.4f}", f"{r['peak0']:.3f}", f"{r['vt_cal']:.4f}", r["peak_err"], r["pad_rms"], r["lag"],
                         r["worst"], int(r["selected"])])
    return dict(peak=peak, rms_by_k=rms_by_k, band=band, cands=rows, cc_declared=5.0, cc_knee=2.64)


# ------------------------------------------------------------------ F. the procedure as a flow
def fig_workflow():
    """The procedure as a plain flow chart: five steps, the two inputs that are not the file (the
    built-in constants and the one stressed measurement), and the model."""
    with plt.rc_context(RC):
        fig, a = plt.subplots(figsize=(W, 2.9))
        a.set_xlim(0, 100); a.set_ylim(0, 46); a.axis("off")
        fs = 6.3
        dbox(a, 1, 32, 23, 11, "IBIS file\nI–V tables, V–T waveforms,\n$C_{comp}$, package", ls="--", fs=fs)
        darrow(a, 24, 37.5, 27, 37.5)
        dbox(a, 27, 32, 23.5, 11, "step 0\nestimate $C_{comp}$; solve\n$K_u(t)$, $K_d(t)$; target (25)", fs=fs)
        darrow(a, 50.5, 37.5, 53.5, 37.5)
        dbox(a, 53.5, 32, 23.5, 11, "step 1\nfit $s_{up}$, $s_{dn}$, $v_t$ per\ncandidate, (26)", fs=fs)
        darrow(a, 77, 37.5, 80, 37.5)
        dbox(a, 80, 32, 19, 11, "step 2\nnine candidates:\nband (27) × 3 shapes", fs=fs)
        dbox(a, 53.5, 17, 23.5, 9.5, "built-in constants\n$x_{lin}$, $p$, three map\nshapes, band rule", ls="--", fs=fs)
        darrow(a, 65.25, 26.5, 65.25, 32)
        a.plot([89.5, 89.5], [32, 9.5], color=K_, lw=0.9)
        darrow(a, 89.5, 9.5, 77, 9.5)
        dbox(a, 53.5, 4, 23.5, 11, "step 3\ncalibrate $v_t$ of each\ncandidate on the peak, (28)", fs=fs)
        darrow(a, 53.5, 9.5, 50.5, 9.5)
        dbox(a, 27, 4, 23.5, 11, "step 4\nselect by the waveform\nover the pulse, (29)", fs=fs)
        darrow(a, 27, 9.5, 24, 9.5)
        dbox(a, 1, 4, 23, 11, "model\nsubcircuit, (19)–(24)", fs=fs)
        dbox(a, 1, 19, 23, 9.5, "one stressed pad\nwaveform (measured)", ls="--", fs=fs)
        a.plot([12.5, 12.5], [19, 15], color=K_, lw=0.9)
        a.plot([12.5, 38.75], [17, 17], color=K_, lw=0.9)
        darrow(a, 38.75, 17, 38.75, 15)
        a.plot([38.75, 60], [17, 17], color=K_, lw=0.9)
        darrow(a, 60, 17, 60, 15)
        save(fig, "fig_workflow")


# ------------------------------------------------------------------ I. the target
def fig_target():
    """Where the fit's target comes from: ex2's two-fixture V-T waveforms, the converter's solved
    Ku(t), Kd(t), the existing model's full-swing Ku against that solution, and the normalised
    target (25). Returns the alignment shift and the rms between solution and model."""
    import gate_ramp_prototype as gp
    from pybis2spice import pybis2spice as pb
    import spicelab as sl
    base = SC / "knee_models" / "ex2_c2.64"                 # the file at the C_comp estimated from the file
    ib = base / "input_ccomp.ibs"
    m, c = gp.ibis_names(ib)
    dm = pb.DataModel(pb.get_ibis_model_ecdtools(str(ib)), model_name=m, component_name=c)
    kr = pb.solve_k_params_output(dm, 1, "Rising")
    kf = pb.solve_k_params_output(dm, 1, "Falling")
    raw = sl.parse_ngspice_raw(base / "shipped" / "full" / "run.raw")
    tf = sl.time_ns(raw)
    kb = sl.signal(raw, "v(x1.kugate_base)")
    grid, u, target, t_on = shipped_target("ex2", base / "shipped" / "full" / "run.raw")

    def t50(t, y):
        y = (y - y[0]) / (y[-1] - y[0]) if abs(y[-1] - y[0]) > 0.5 else y
        i = int(np.argmax(y >= 0.5))
        return float(np.interp(0.5, y[i - 1:i + 1], t[i - 1:i + 1]))

    tau_r, ku_r, kd_r = kr[:, 0] * 1e9, kr[:, 1], kr[:, 2]
    tau_f, ku_f = kf[:, 0] * 1e9, kf[:, 1]
    sel_r = tf < 9.0
    shift_r = t50(tf[sel_r], kb[sel_r]) - t50(tau_r, ku_r)             # model time = table time + shift
    sel_f = tf > 9.0
    shift_f = t50(tf[sel_f], -kb[sel_f]) - t50(tau_f, -ku_f)
    ov = (tau_r + shift_r >= 4.0) & (tau_r + shift_r <= 12.5)
    rms_r = float(np.sqrt(np.mean((np.interp(tau_r[ov] + shift_r, tf, kb) - ku_r[ov]) ** 2)))
    # the C_comp estimate from the file (scripts/ccomp_from_file.py, results/ccomp_from_file_2026-09-22)
    CCF = ROOT / "results" / "ccomp_from_file_2026-09-22"
    cc_rows = [r for r in csv.DictReader((CCF / "ccomp_curves.csv").open()) if r["buffer"] == "ex2"]
    cc = np.array([float(r["c_comp_pF"]) for r in cc_rows])
    mk = np.array([float(r["max_ku"]) for r in cc_rows])
    info = next(r for r in csv.DictReader((CCF / "ccomp_from_file.csv").open()) if r["buffer"] == "ex2")
    cc_declared, cc_loop, cc_knee = float(info["declared_pF"]), float(info["loop_pF"]), float(info["knee_ku_pF"])
    ku_at_declared = float(np.interp(cc_declared, cc, mk))
    msk = (mk >= 1.05) & (mk <= 1.35)
    pa, pb = np.polyfit(cc[msk], mk[msk], 1)
    rfix_ohm = float(dm.vt_rising[0].r_fix)
    vfix_list = sorted({float(w.v_fix[0]) for w in dm.vt_rising})
    # the native element's own coefficient through the same transition (native_full_swing.py)
    nat = DOCDIR / "native_full_swing" / "ex2_c2.64.npz"
    nat_rms = float("nan")
    if nat.exists():
        z = np.load(nat)
        tn, kun = z["t_ns"], z["ku"]
        sel_n = tn < 9.0
        shift_n = t50(tn[sel_n], kun[sel_n]) - t50(tau_r, ku_r)
        nat_rms = float(np.sqrt(np.mean((np.interp(tau_r[ov] + shift_n, tn, kun) - ku_r[ov]) ** 2)))
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 3, figsize=(W, 2.6), gridspec_kw={"wspace": 0.4, "width_ratios": (0.8, 1.2, 0.8)})
        b = ax[0]
        for i, (wf, lab) in enumerate(zip(dm.vt_rising, ("rising, fixture 0 V", "rising, fixture 3.3 V"))):
            b.plot(wf.data[:, 0] * 1e9, wf.data[:, 1], color=(TEAL, "#0B5F5C")[i], lw=1.5, label=lab)
        for i, (wf, lab) in enumerate(zip(dm.vt_falling, ("falling, fixture 0 V", "falling, fixture 3.3 V"))):
            b.plot(wf.data[:, 0] * 1e9, wf.data[:, 1], color=(BLUE, "#143E63")[i], lw=1.5, ls="--", label=lab)
        b.set_xlim(0, 8); b.set_xlabel("table time (ns)"); b.set_ylabel("pad voltage (V)")
        b.set_title("(a) the file's V–T waveforms", fontsize=7.6)
        b.legend(frameon=False, fontsize=5.8, loc="center", bbox_to_anchor=(0.6, 0.62))
        # the fixture: buffer -> pad -> R_fix -> V_fix, drawn in an inset
        ins = b.inset_axes([0.3, 0.02, 0.68, 0.24])
        ins.set_xlim(0, 100); ins.set_ylim(0, 30); ins.axis("off")
        ins.add_patch(mpatches.Rectangle((2, 8), 22, 14, fc="#F1F3F4", ec="#555555", lw=0.8))
        ins.text(13, 15, "buffer", ha="center", va="center", fontsize=5.6)
        ins.plot([24, 40], [15, 15], color=K_, lw=0.8); ins.plot(40, 15, "o", ms=2, color=K_)
        ins.text(40, 20, "pad", ha="center", va="bottom", fontsize=5.6)
        zig = np.array([40, 44, 46, 50, 54, 58, 62, 64, 68])
        ins.plot(zig, [15, 15, 21, 9, 21, 9, 21, 15, 15], color=K_, lw=0.8)
        ins.text(54, 24, f"$R_{{fix}}$ {rfix_ohm:.0f} Ω", ha="center", va="bottom", fontsize=5.6)
        ins.plot([68, 80], [15, 15], color=K_, lw=0.8); ins.plot([80, 80], [10, 20], color=K_, lw=1.2)
        ins.text(83, 15, "$V_{fix}$: " + ", ".join(f"{v:g} V" for v in vfix_list), ha="left", va="center", fontsize=5.6)
        c = ax[1]
        c.plot(tau_r + shift_r - 5.0, ku_r, color="#9A9A9A", lw=3.2, label="$K_u$ solved from (a)")
        c.plot(tau_r + shift_r - 5.0, kd_r, color="#9A9A9A", lw=3.2, ls="--", label="$K_d$ solved from (a)")
        c.plot(tau_f + shift_f - 5.0, ku_f, color="#9A9A9A", lw=3.2)
        c.plot(tf - 5.0, kb, color=TEAL, lw=1.2, label="existing model, $K_u$")
        if nat.exists():
            c.plot(tn - 5.0, kun, color=BLUE, lw=1.1, ls=(0, (1.4, 1.4)), label="native element, $K_u$ (xv_pu)")
        c.plot(grid - 5.0, u, color="#BBBBBB", lw=1.0, label="chain input $u_1(t)$ (20)")
        c.plot(grid - 5.0, target, color=K_, lw=1.6, label="target $\\hat{K}_u(t)$ (25)")
        for x, lab in ((4.5 - 5.0, "$t_{rest}$"), (12.0 - 5.0, "$t_{on}$")):
            c.axvline(x, color=RED, lw=0.8, ls=":")
            c.text(x + 0.15, 0.86, lab, color=RED, fontsize=7)
        c.set_xlim(-1, 16); c.set_ylim(-0.12, 1.15); c.set_xlabel("time from the input edge (ns)"); c.set_ylabel("conducting fraction")
        c.set_title("(b) solution, existing model, target", fontsize=7.6)
        c.legend(frameon=False, fontsize=6.2, loc="center right")
        e = ax[2]
        e.plot(cc, mk, color=TEAL, lw=1.6, label="peak of solved $K_u$")
        xx = np.linspace(cc_knee, (1.38 - pb) / pa, 20)
        e.plot(xx, pa * xx + pb, color=K_, lw=0.8, ls="--", label="rising branch, extrapolated")
        e.axhline(1.0, color="#888888", lw=0.7)
        e.plot([cc_declared], [ku_at_declared], "o", color=RED, ms=4)
        e.text(cc_declared - 0.12, ku_at_declared + 0.012, f"declared\n{cc_declared:.1f} pF: {ku_at_declared:.2f}",
               ha="right", va="bottom", fontsize=6.4, color=RED)
        e.plot([cc_knee], [1.0], "o", color=K_, ms=4)
        e.text(cc_knee + 0.15, 0.99, f"estimate\n{cc_knee:.2f} pF", ha="left", va="top", fontsize=6.4)
        e.axvline(cc_loop, color=GREY, lw=0.8, ls=":")
        e.text(cc_loop + 0.1, 1.17, f"netlist\n{cc_loop:.2f} pF", ha="left", va="top", fontsize=6.4, color="#555555")
        e.set_xlim(0, 6); e.set_ylim(0.93, 1.36)
        e.set_xlabel("assumed $C_{comp}$ (pF)"); e.set_ylabel("peak of solved $K_u$")
        e.set_title("(c) $C_{comp}$ from the file", fontsize=7.6)
        e.legend(frameon=False, fontsize=6.0, loc="upper left")
        save(fig, "fig_target")
    return dict(shift_r=shift_r, shift_f=shift_f, rms_r=rms_r, n_iv=len(dm.iv_pullup), n_vt=len(dm.vt_rising[0].data),
                t_vt=float(dm.vt_rising[0].data[-1, 0] * 1e9), rfix=float(dm.vt_rising[0].r_fix),
                vfix=[float(w.v_fix[0]) for w in dm.vt_rising], ku_max=float(ku_r.max()), kd_max=float(kd_r.max()),
                cc_declared=cc_declared, cc_loop=cc_loop, cc_knee=cc_knee, ku_at_declared=ku_at_declared,
                nat_rms=nat_rms)


# ------------------------------------------------------------------ J. the residual, pictured
def fig_fit_score():
    """What the residual of (26) measures: the gap between the model's Ku(t) and the file's, for a
    poor trial and for the fit (ex2, K = 3, map (0.57, 0.64), x_lin = 0.45)."""
    d = np.load(DOCDIR / "shape_fileonly" / "target_ex2.npz")
    u, target = d["u"], d["target"]
    t = np.arange(4.0, 21.0, cl.DT) - 5.025
    p = EX2

    def ku(s_up, s_dn, vt):
        return prior(chain_stages(u, s_up, s_dn, vt, 0.45, 3)[-1], *p["shape"])

    trials = ((8.0, 8.0, 0.40, "a trial: $s_{up}$ = $s_{dn}$ = 8/ns, $v_t$ = 0.4"),
              (p["s_up"], p["s_dn"], p["vt_fit"], f"the fit: $s_{{up}}$ = {p['s_up']:.2f}/ns, $s_{{dn}}$ = {p['s_dn']:.2f}/ns, $v_t$ = {p['vt_fit']:.3f}"))
    out = {}
    with plt.rc_context(RC):
        fig = plt.figure(figsize=(W, 4.4))
        gs = fig.add_gridspec(2, 2, hspace=0.6, wspace=0.25)
        axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
        for a, (s_up, s_dn, vt, lab), tag_ in zip(axes[:2], trials, ("(a)", "(b)")):
            y = ku(s_up, s_dn, vt)
            r = float(np.sqrt(np.mean((y - target) ** 2)))
            out[lab] = r
            a.fill_between(t, target, y, color=RED, alpha=0.25, lw=0, label="the gap")
            a.plot(t, target, color=K_, lw=2.4, alpha=0.4, label="file $\\hat{K}_u(t)$")
            a.plot(t, y, color=TEAL, lw=1.6, label="model $M(v_K(t))$")
            a.set_xlim(-0.3, 3.0); a.set_ylim(-0.05, 1.12)
            a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("$K_u$")
            a.set_title(f"{tag_} {lab}\nresidual {r:.3f}", fontsize=8)
            a.legend(frameon=False, fontsize=6.6, loc="center right")
        c = axes[2]
        for (s_up, s_dn, vt, lab), col in zip(trials, (RED, TEAL)):
            y = ku(s_up, s_dn, vt)
            c.plot(t, y - target, color=col, lw=1.3, label=f"model − file, {lab.split(':')[0]} (rms {out[lab]:.3f})")
        c.axhline(0, color="#999999", lw=0.6)
        c.set_xlim(-1, 16); c.set_ylim(-1.05, 1.05)
        c.set_xlabel("time from the input edge (ns)"); c.set_ylabel("model − file")
        c.set_title("(c) the difference over the whole fit window (4–21 ns): the residual is its root-mean-square", fontsize=8)
        c.legend(frameon=False, fontsize=6.8, loc="upper right")
        save(fig, "fig_fit_score")
    return out


# ------------------------------------------------------------------ J. the search
def fig_fit_search():
    """The residual landscape of (26) on ex2 and the three Nelder-Mead runs, from fit_search.py."""
    L = np.load(DOCDIR / "fit_search_fileonly" / "landscape.npz")
    P = np.load(DOCDIR / "fit_search_fileonly" / "paths.npz")
    fit = L["fit"]
    cols = {2: TEAL, 8: ORANGE, 30: BLUE}
    out = {}
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 3, figsize=(W, 3.0), gridspec_kw={"wspace": 0.5, "width_ratios": (1.1, 1.1, 1)})
        levels = np.linspace(np.log10(0.02), np.log10(0.5), 15)
        a = ax[0]
        cf = a.contourf(L["s_up"], L["vt"], np.log10(L["rms_sup_vt"]).T, levels=levels, cmap="Greys_r", extend="both")
        a.set_xscale("log")
        b = ax[1]
        b.contourf(L["s_up"], L["s_dn"], np.log10(L["rms_sup_sdn"]).T, levels=levels, cmap="Greys_r", extend="both")
        b.set_xscale("log"); b.set_yscale("log")
        for s0 in (2, 8, 30):
            lg = P[f"log_{s0}"]
            best = np.minimum.accumulate(lg[:, 3])
            idx = [0] + [i for i in range(1, len(lg)) if best[i] < best[i - 1]]
            path = lg[idx]
            end = P[f"end_{s0}"]
            out[s0] = dict(n=len(lg), end=end)
            lab = f"start {s0}/ns → rms {end[3]:.3f}"
            a.plot(path[:, 0], path[:, 2], "-", color=cols[s0], lw=1.0)
            a.plot(path[0, 0], path[0, 2], "s", color=cols[s0], ms=4.5)
            a.plot(end[0], end[2], "*", color=cols[s0], ms=8, mec="white", mew=0.4)
            b.plot(path[:, 0], path[:, 1], "-", color=cols[s0], lw=1.0)
            b.plot(path[0, 0], path[0, 1], "s", color=cols[s0], ms=4.5)
            b.plot(end[0], end[1], "*", color=cols[s0], ms=8, mec="white", mew=0.4)
            ax[2].plot(np.arange(1, len(lg) + 1), best, color=cols[s0], lw=1.4, label=lab)
        a.plot(fit[0], fit[2], "o", color=RED, ms=4, mfc="none", mew=1.2)
        b.plot(fit[0], fit[1], "o", color=RED, ms=4, mfc="none", mew=1.2)
        if "vt_bound" in L.files:
            vb = float(L["vt_bound"])
            a.axhline(vb, color=RED, lw=0.7, ls="--")
            a.text(3.4, vb - 0.02, f"bound of the\nmethod, $v_t \\leq {vb:g}$", fontsize=5.6, color=RED, ha="left", va="top")
        if "end_free" in P.files:
            ef = P["end_free"]
            a.plot(ef[0], ef[2], "*", color=RED, ms=8, mfc="none", mew=0.8)
            a.annotate(f"no bound:\n$v_t$ = {ef[2]:.2f}, rms {ef[3]:.4f}", (ef[0], ef[2]), (0.52, 0.93), textcoords="axes fraction",
                       fontsize=5.6, color=RED, ha="left", va="top",
                       arrowprops=dict(arrowstyle="-", color=RED, lw=0.5, shrinkA=0, shrinkB=3))
            out["free"] = dict(end=ef)
        a.set_xlabel("$s_{up}$ (per ns, log scale)"); a.set_ylabel("$v_t$")
        a.set_title(f"(a) over ($s_{{up}}$, $v_t$), $s_{{dn}}$ = {fit[1]:.2f}/ns", fontsize=7.8)
        b.set_xlabel("$s_{up}$ (per ns, log scale)"); b.set_ylabel("$s_{dn}$ (per ns, log scale)")
        b.set_title(f"(b) over ($s_{{up}}$, $s_{{dn}}$), $v_t$ = {fit[2]:.3f}", fontsize=7.8)
        b.set_ylim(0.4, 14)
        if P["end_30"][1] > 14:
            b.text(0.03, 0.97, f"start 30/ns ends at\n$s_{{dn}}$ = {P['end_30'][1]:.0f}/ns (off scale)", transform=b.transAxes,
                   fontsize=5.6, color=BLUE, ha="left", va="top")
        cb = fig.colorbar(cf, ax=[a, b], orientation="horizontal", fraction=0.045, pad=0.3, aspect=45)
        cb.set_ticks(np.log10([0.02, 0.05, 0.1, 0.2, 0.5])); cb.set_ticklabels(["0.02", "0.05", "0.1", "0.2", "0.5"])
        cb.set_label("residual (rms)", fontsize=7); cb.ax.tick_params(labelsize=6.5)
        c = ax[2]
        c.set_yscale("log"); c.set_ylim(0.02, 1.6); c.set_xlim(0, 150)
        c.set_xlabel("evaluations of (26)"); c.set_ylabel("best residual so far")
        c.set_title("(c) the three runs", fontsize=8)
        c.legend(frameon=False, fontsize=6.3, loc="upper right", bbox_to_anchor=(1.02, 0.84))
        c.axhline(fit[3] if len(fit) > 3 else float(L["fit_rms"]), color=RED, lw=0.7, ls=":")
        save(fig, "fig_fit_search")
    return out


# ------------------------------------------------------------------ J. one stage against the chain
def fig_one_vs_chain():
    """Why a chain: the best single stage against the best three-stage chain on ex2's file curve
    (both from stage_count_from_file step 1, est_knee pass: the file-only setting), and where the chain
    spends the delay."""
    rows = {int(r["K"]): r for r in csv.DictReader((SC / "step1" / "est_knee__ex2__pull-up.csv").open())}
    d = np.load(DOCDIR / "shape_fileonly" / "target_ex2.npz")
    u, target = d["u"], d["target"]
    t = np.arange(4.0, 21.0, cl.DT) - 5.025
    vt_map, a_map = EX2["shape"]

    def crossing(y, level):
        i = int(np.argmax(y >= level))
        return float(np.interp(level, y[i - 1:i + 1], t[i - 1:i + 1]))

    nodes = {}
    for K in (1, 3):
        r = rows[K]
        nodes[K] = chain_stages(u, float(r["s_up"]), float(r["s_dn"]), float(r["vt"]), 0.45, K)
    vt3 = float(rows[3]["vt"])
    hand = [crossing(v, vt3) for v in nodes[3][:-1]] + [crossing(nodes[3][-1], vt_map)]
    file_start = crossing(target, 0.02)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 2, figsize=(W, 2.5), gridspec_kw={"wspace": 0.25})
        a = ax[0]
        a.plot(t, target, color=K_, lw=2.6, alpha=0.4, label="file $\\hat{K}_u(t)$")
        for K, col, ls in ((1, ORANGE, "-"), (3, TEAL, "-")):
            y = prior(nodes[K][-1], vt_map, a_map)
            a.plot(t, y, color=col, lw=1.6, ls=ls, label=f"$K$ = {K}: rms {float(rows[K]['rms']):.3f}")
        a.set_xlim(-0.3, 3.0); a.set_ylim(-0.05, 1.12)
        a.set_xlabel("time from the input edge (ns)"); a.set_ylabel("$K_u$")
        a.set_title("(a) one stage cannot be both late and steep", fontsize=8.5)
        a.legend(frameon=False, fontsize=6.8, loc="center right")
        b = ax[1]
        shades = ("#9CC8C6", "#4FB3AF", "#0B5F5C")
        for k, (v, col) in enumerate(zip(nodes[3], shades), 1):
            b.plot(t, v, color=col, lw=1.5, label=f"stage {k}" + (" = gate" if k == 3 else ""))
        b.axhline(vt3, color=GREY, lw=0.7, ls="--")
        b.text(-0.25, vt3 - 0.03, f"$v_t$ = {vt3:.2f}", ha="left", va="top", fontsize=6.6, color="#555555")
        b.axhline(vt_map, color=RED, lw=0.7, ls=":")
        b.text(2.95, vt_map + 0.02, f"$v_{{t,map}}$ = {vt_map}", ha="right", fontsize=6.6, color=RED)
        for k, x in enumerate(hand, 1):
            b.plot([x, x], [-0.05, (vt3 if k < 3 else vt_map)], color="#777777", lw=0.6)
            b.text(x, -0.1, f"{x:.2f}", ha="center", va="top", fontsize=6.4, color="#444444")
        b.set_xlim(-0.3, 3.0); b.set_ylim(-0.22, 1.12)
        b.set_xlabel("time from the input edge (ns)"); b.set_ylabel("stage output")
        b.set_title("(b) three stages: the delay is spent in handovers", fontsize=8.5)
        b.legend(frameon=False, fontsize=6.8, loc="lower right", bbox_to_anchor=(1.0, 0.1))
        save(fig, "fig_one_vs_chain")
    return dict(hand=hand, file_start=file_start, k1=rows[1], k3=rows[3])


# ------------------------------------------------------------------ J. the fit on all twelve
def fig_fit_all():
    """The fit (26) of the selected candidate on each of the twelve test buffers (file-only
    settings): the file's normalised Ku(t) and the model's, rising edge."""
    builds = file_only_builds()
    with plt.rc_context(RC):
        fig, axes = plt.subplots(3, 4, figsize=(W, 5.6), gridspec_kw={"wspace": 0.34, "hspace": 0.75})
        for a, r in zip(axes.ravel(), builds):
            a.plot(r["t"], r["target"], color=K_, lw=2.4, alpha=0.4, label="file $\\hat{K}_u(t)$")
            a.plot(r["t"], r["model"], color=TEAL, lw=1.4, label="model $M(G_{UP}(t))$")
            xmax = 3.2 if r["dev"].startswith("ex2") else (4.5 if r["dev"] == "io_buf" else 0.9)
            a.set_xlim(-0.1 * xmax, xmax); a.set_ylim(-0.05, 1.12)
            a.set_title(f"{r['dev']}\n$K$={r['K']} ({r['shape'][0]:g},{r['shape'][1]:g}) rms {r['rms']:.3f}", fontsize=6.8)
            a.tick_params(labelsize=6.5)
        fig.text(0.5, 0.045, "time from the input edge (ns)", ha="center", fontsize=8)
        for a in axes[:, 0]:
            a.set_ylabel("$K_u$", fontsize=7.5)
        fig.legend(*axes[0][0].get_legend_handles_labels(), frameon=False, loc="lower center", ncol=2, fontsize=7.4,
                   bbox_to_anchor=(0.5, -0.01))
        save(fig, "fig_fit_all")
    return builds


# ------------------------------------------------------------------ L. how the calibration finds vt
def fig_calib_mech():
    """The threshold calibration (28) on ex2's selected candidate: the peak error against v_t (dense
    sweep, from calib_iterations.py) with the ten bisection iterates, and the pad waveforms."""
    z = np.load(DOCDIR / "calib_iterations" / "ex2.npz", allow_pickle=True)
    names, vt, err, t, pads = [str(s) for s in z["names"]], z["vt"], z["err"], z["t"] - 5.0, z["pads"]
    t_si, si = z["t_si"] - 5.0, z["si"]
    its = [i for i, n in enumerate(names) if n.startswith("it")]
    order = np.argsort(vt)
    lo, hi, brackets = 0.0, 0.7, []
    for i in its[3:]:
        mid = 0.5 * (lo + hi)
        brackets.append((int(names[i][2:]), lo, hi, mid, err[i]))
        if err[i] > 0:
            lo = mid
        else:
            hi = mid
    vt_final = 0.5 * (lo + hi)
    w = 0.810
    peak = float(si[(t_si >= w - 0.3) & (t_si <= w + 2.6)].max())
    with plt.rc_context(RC):
        fig, ax = plt.subplots(1, 2, figsize=(W, 2.5), gridspec_kw={"wspace": 0.32})
        a = ax[0]
        a.plot(vt[order], err[order], "-", color=GREY, lw=1.1)
        a.axhline(0, color="#999999", lw=0.6)
        for i in its:
            n = int(names[i][2:])
            a.plot(vt[i], err[i], "o", color=TEAL if n >= 3 else ORANGE, ms=4.5, zorder=4)
            if n == 2:
                continue                                   # same point as iteration 0 (v_t = 0.7)
            dx, dy = {0: (6, 2), 5: (-8, 2), 7: (7, -9), 8: (-9, 1), 9: (8, -2)}.get(n, (0, 7 if err[i] >= 0 else -11))
            a.annotate("0, 2" if n == 0 else str(n), (vt[i], err[i]), (dx, dy), textcoords="offset points",
                       ha="center", fontsize=6.4, color="#333333")
        a.axvline(vt_final, color=RED, lw=0.8, ls=":")
        a.text(vt_final - 0.015, -85, f"$v_t$ = {vt_final:.3f}", ha="right", fontsize=6.8, color=RED)
        a.set_xlim(-0.03, 0.73); a.set_ylim(-105, 75)
        a.set_xlabel("stage threshold $v_t$"); a.set_ylabel("peak error (%)")
        a.set_title("(a) peak error against $v_t$; iterations numbered", fontsize=8.5)
        c = ax[1]
        c.plot(t_si, si, color=K_, lw=2.4, label="measured")
        c.axhline(peak, color=K_, lw=0.7, ls="--")
        for n, col in ((1, "#E0B09A"), (3, ORANGE), (5, "#4FB3AF"), (9, TEAL)):
            i = names.index(f"it{n:02d}")
            c.plot(t, pads[i], color=col, lw=1.2, label=f"iteration {n}: $v_t$ = {vt[i]:.2f} ({err[i]:+.0f} %)")
        c.set_xlim(0.2, 3.0); c.set_ylim(-0.4, 1.55)
        c.set_xlabel("time from the input edge (ns)"); c.set_ylabel("pad voltage (V)")
        c.set_title("(b) the pad waveform as $v_t$ is bisected", fontsize=8.5)
        pct_axis(c, settled_swing("ex2"))
        c.legend(frameon=False, fontsize=6.0, loc="upper left")
        save(fig, "fig_calib_mech")
    return dict(vt_final=vt_final, brackets=brackets, err0=float(err[its[0]]), vt0=float(vt[its[0]]),
                err_lo=float(err[its[1]]), err_hi=float(err[its[2]]), peak=peak, n_runs=len(its),
                emax=float(err[order].max()), vt_emax=float(vt[order][int(np.argmax(err[order]))]))


ALL = (fig_problem, fig_replay_fails, fig_stage, fig_stage_flow, fig_device, fig_stage_law, fig_blocks, fig_workflow, fig_chain,
       fig_map, fig_gate_to_ku, fig_target, fig_fit_score, fig_fit_knobs, fig_fit_search, fig_one_vs_chain,
       fig_ku_fit, fig_fit_all, fig_ambiguity, fig_rms_vs_k, fig_stress_use, fig_calib_mech, fig_gate_verify,
       fig_gate_internal, fig_pad_waveforms, fig_pad_summary, fig_native_fail, fig_calibration)

if __name__ == "__main__":
    want = sys.argv[1:]
    for f in ALL:
        if not want or f.__name__ in want:
            f()
