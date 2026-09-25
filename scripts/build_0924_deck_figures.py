#!/usr/bin/env python3
"""Figures for the 2026-09-24 deck, which tells the story in the order the evidence came in.

The 09-18 deck already carries the probing schematics and a four-panel walk at one stress
level. What it does not carry is the same walk *across* stress levels, which is what makes the
argument: the real gate changes shape as the pulse shortens, and GUP does not.

    map_from_probe        how Ku(gate) is built: pair Ku(t) from the file with the probed
                          gate at each instant, and read off the curve
    works_levels_<dev>    the pad at five stress levels - transistor, native HSPICE IBIS,
                          our gate-state model, and the same model driven by the real gate
    gate_shape_<dev>      the gate itself at those five levels: the real one against GUP
    ku_consequence_<dev>  what that shape difference does to Ku and to the pad

Nothing is re-simulated; every trace is read from runs already on disk (the probed gates from
`predriver_stages_2026-09-09`, the replays from `gate_cascade_prototype_2026-09-09`, native and
transistor from the 08-20 stress matrix).

Output: results/meeting_deck_2026-09-24/figures/

    py -3.14 scripts/build_0924_deck_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import build_0917_deck_figures as f17  # noqa: E402
import build_0918_deck_figures as f18  # noqa: E402
import spicelab as sl  # noqa: E402

OUT = ROOT / "results" / "meeting_deck_2026-09-24" / "figures"
OURS, REAL, SIL, NAT = f18.OURS, f18.REAL, f17.SIL, f17.NAT
BODY = f18.BODY

# (cascade folder, probed node, its name, the five widths deepest-last, pad y-limit)
DEV = {
    "ex2": ("ex2_c1.7", "v(xdut.n4)", "n4", [810, 830, 858, 895, 975], 1.75, 2.2),
    "inv_chain": ("inv_chain_c0.6", "v(xdut.vout7)", "vout7", [104, 106, 111, 119, 135], 1.45, 0.45),
}
DEPTH_PCT = {810: 50, 830: 60, 858: 70, 895: 80, 975: 90,
             104: 50, 106: 60, 111: 70, 119: 80, 135: 90}


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=f17.DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {name}.png")


def _run(dev, depth, build):
    """(t from the input edge, GUP, Ku, pad) of one stored ngspice run."""
    folder = DEV[dev][0]
    raw = sl.parse_ngspice_raw(f17.CASC / folder / build / f"d{depth}" / "run.raw")
    t = sl.time_ns(raw) - 5.0
    return t, sl.signal(raw, "v(x1.gup)"), sl.signal(raw, "v(x1.ku)"), sl.trace(raw, "out")


def _peak_err(t, y, t_si, si, w):
    """Peak error against the transistor, over the pulse and its return."""
    win = lambda tt: (tt >= w - 0.3) & (tt <= w + 2.6)   # noqa: E731
    pk = float(si[win(t_si)].max())
    return 100.0 * (float(y[win(t)].max()) - pk) / pk, pk


# --------------------------------------------------------------------------- #
# 1. how the map is measured
# --------------------------------------------------------------------------- #

def map_from_probe(dev: str = "ex2") -> None:
    """Pair Ku(t) with the probed gate at each instant; the pairing IS the curve."""
    folder, node, gname, widths, _ylim, span = DEV[dev]
    tf, gfull, _ts, _gs = f17._norm_pair(dev, widths[0], node)
    d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / f"{dev}_short_high_w{widths[2]}ps.csv")

    # Ku(t) on the FULL transition - a stressed run turns round, and its pairing would fold the
    # map back on itself instead of tracing it
    raw = sl.parse_ngspice_raw(f17.CASC / folder / "shipped" / "full" / "run.raw")
    t_m, ku_m = sl.time_ns(raw) - 5.0, sl.signal(raw, "v(x1.ku)")
    # stop where the gate FIRST settles: its global argmax is 10 ns into the run and would
    # squash the transition into the left edge
    g_end = float(tf[np.argmax(np.asarray(gfull) >= 0.995)]) + 0.25
    tfull = np.linspace(0.2, g_end, 400)
    ku_t = np.interp(tfull, t_m, ku_m)
    g_t = np.interp(tfull, tf, gfull)
    marks = [0.95, 1.10, 1.22, 1.35, 1.55]
    cols = ["#26326B", "#6A3D9A", "#B03060", "#D9642B", "#E8A33D"]

    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, 2, figsize=(11.4, 4.2))
        a = ax[0]
        a.plot(tfull, ku_t, color="#111111", lw=2.8, label="Ku(t), from the IBIS file")
        a.plot(tfull, g_t, color=REAL, lw=2.8, label=f"the probed gate {gname}(t)")
        for m, c in zip(marks, cols):
            ku_i, g_i = float(np.interp(m, tfull, ku_t)), float(np.interp(m, tfull, g_t))
            a.plot([m, m], [g_i, ku_i], color=c, lw=1.4, ls=":")
            a.plot(m, ku_i, "o", color=c, ms=8, zorder=5)
            a.plot(m, g_i, "s", color=c, ms=8, zorder=5)
        a.set_title("1  full swing: at each instant, read off both", fontweight="bold")
        a.set_xlabel("time from the input edge (ns)")
        a.set_ylabel("0 to 1")
        a.legend(loc="upper left", framealpha=0.95)
        a.grid(alpha=0.3)
        a.set_xlim(0.2, g_end)

        b = ax[1]
        order = np.argsort(g_t)
        b.plot(g_t[order], ku_t[order], color=REAL, lw=3.0)
        for m, c in zip(marks, cols):
            b.plot(float(np.interp(m, tfull, g_t)), float(np.interp(m, tfull, ku_t)),
                   "o", color=c, ms=9, zorder=5)
        b.set_title("2  the pairing is the curve:  Ku as a function of the gate", fontweight="bold")
        b.set_xlabel(f"gate {gname}, 0 to 1")
        b.set_ylabel("Ku")
        b.grid(alpha=0.3)
        b.set_xlim(-0.03, 1.03)
        fig.suptitle(f"{dev}  |  measuring the map: one probe, one full transition",
                     fontsize=15, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        save(fig, f"map_from_probe_{dev}")


# --------------------------------------------------------------------------- #
# 2. does the measured map work?
# --------------------------------------------------------------------------- #

def works_levels(dev: str) -> None:
    """The pad at five stress levels: transistor, native, our gate-state model, real-gate map."""
    folder, node, gname, widths, ylim, span = DEV[dev]
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, len(widths), figsize=(3.05 * len(widths), 4.3), sharey=True)
        handles = None
        for a, w_ps in zip(ax, widths):
            w = w_ps / 1000.0
            d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / f"{dev}_short_high_w{w_ps}ps.csv")
            x = d["time_ns"] - 5.0
            t_si, si, _rev = f17.transistor_pad(dev, w_ps)
            t_si = t_si - 5.0
            a.plot(t_si, si, color=SIL, lw=3.4, label="transistor (truth)", zorder=4)
            e_nat, _ = _peak_err(x, d["hspice_pad"], t_si, si, w)
            a.plot(x, d["hspice_pad"], color=NAT, lw=2.0, ls=(0, (1, 1.6)), label="native IBIS")
            errs = [(NAT, f"native IBIS  {e_nat:+.0f} %")]
            # short names in the panel, full names in the one legend below: the panel is
            # 3 inches wide and the full names ran off its right-hand edge
            for build, col, lab, short in (
                    ("shipped", OURS, "our gate-state model", "gate-state"),
                    ("gate_replay_silicon_full", REAL, "real gate + measured map", "real gate + map")):
                t, _g, _k, pad = _run(dev, w_ps, build)
                e, _ = _peak_err(t, pad, t_si, si, w)
                a.plot(t, pad, color=col, lw=2.4, ls="--" if build == "shipped" else "-", label=lab)
                errs.append((col, f"{short}  {e:+.0f} %"))
            # the error labels sit under the curves: the overshoot is the point of the panel
            # and a legend box over it hides exactly what the slide is for
            for i, (col, txt) in enumerate(errs):
                a.text(0.04, 0.97 - 0.085 * i, txt, transform=a.transAxes, color=col,
                       fontsize=9, fontweight="bold", va="top")
            a.set_title(f"{DEPTH_PCT[w_ps]} % stress   ({w_ps} ps)", fontweight="bold", fontsize=12)
            a.set_xlim(w - (0.35 if span > 1 else 0.20), w + span)
            a.set_ylim(-0.12, ylim * 1.30)   # headroom so the error labels clear the curves
            a.grid(alpha=0.3)
            a.set_xlabel("time (ns)")
            handles = a.get_legend_handles_labels()
        ax[0].set_ylabel("pad (V)")
        fig.legend(*handles, loc="lower center", ncol=4, fontsize=11, frameon=False,
                   bbox_to_anchor=(0.5, -0.02))
        fig.suptitle(f"{dev}  |  the measured map holds at every stress level",
                     fontsize=15, fontweight="bold")
        fig.tight_layout(rect=(0, 0.06, 1, 0.9))
        save(fig, f"works_levels_{dev}")


# --------------------------------------------------------------------------- #
# 3. why: the real gate changes shape, GUP does not
# --------------------------------------------------------------------------- #

def gate_shape(dev: str) -> None:
    """The probed gate against our GUP, at each stress level, on one normalised axis."""
    folder, node, gname, widths, _ylim, span = DEV[dev]
    tf, gfull, _t, _g = f17._norm_pair(dev, widths[0], node)
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, len(widths), figsize=(3.05 * len(widths), 3.9), sharey=True)
        for a, w_ps in zip(ax, widths):
            w = w_ps / 1000.0
            _tf, _gf, ts, greal = f17._norm_pair(dev, w_ps, node)
            t, gup, _k, _p = _run(dev, w_ps, "shipped")
            a.plot(tf, gfull, color="#B9B9B9", lw=3.2, label="full swing", zorder=1)
            a.plot(ts, greal, color=SIL, lw=3.0, label=f"real gate {gname}", zorder=3)
            a.plot(t, gup, color=OURS, lw=2.4, ls="--", label="our GUP", zorder=2)
            gm, um = float(np.nanmax(greal)), float(np.nanmax(gup))
            a.plot(ts[np.nanargmax(greal)], gm, "o", color=SIL, ms=7, zorder=5)
            a.plot(t[np.nanargmax(gup)], um, "o", color=OURS, ms=7, zorder=5)
            a.annotate(f"{gm:.2f}", (ts[np.nanargmax(greal)], gm), textcoords="offset points",
                       xytext=(-6, 6), ha="right", color=SIL, fontsize=11, fontweight="bold")
            a.annotate(f"{um:.2f}", (t[np.nanargmax(gup)], um), textcoords="offset points",
                       xytext=(8, -4), ha="left", color=OURS, fontsize=11, fontweight="bold")
            a.set_title(f"{DEPTH_PCT[w_ps]} % stress   ({w_ps} ps)", fontweight="bold", fontsize=12)
            a.set_xlim(w - 0.55, w + max(span, 0.9))
            a.set_ylim(-0.08, 1.24)
            a.grid(alpha=0.3)
            a.set_xlabel("time (ns)")
            handles = a.get_legend_handles_labels()
        ax[0].set_ylabel("gate, 0 to 1")
        fig.legend(*handles, loc="lower center", ncol=3, fontsize=11, frameon=False,
                   bbox_to_anchor=(0.5, -0.02))
        fig.suptitle(f"{dev}  |  the real gate changes shape with the pulse; GUP keeps one shape",
                     fontsize=15, fontweight="bold")
        fig.tight_layout(rect=(0, 0.06, 1, 0.9))
        save(fig, f"gate_shape_{dev}")


def ku_consequence(dev: str) -> None:
    """The shape difference, carried through the map into Ku and then into the pad."""
    folder, node, gname, widths, ylim, span = DEV[dev]
    show = [widths[0], widths[2], widths[-1]]          # deepest, middle, mildest
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(2, len(show), figsize=(3.5 * len(show), 5.6), sharex="col")
        for j, w_ps in enumerate(show):
            w = w_ps / 1000.0
            d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / f"{dev}_short_high_w{w_ps}ps.csv")
            xk, kk = d["time_ns"] - 5.0, d["silicon_ku"].copy()
            for edge in (0.0, w):      # the two-fixture solve is differentiation noise here
                kk[(xk > edge - 0.02) & (xk < edge + 0.09)] = np.nan
            t_si, si, _r = f17.transistor_pad(dev, w_ps)
            t_si = t_si - 5.0
            a, b = ax[0][j], ax[1][j]
            a.plot(xk, kk, color=SIL, lw=3.0, label="transistor (truth)")
            b.plot(t_si, si, color=SIL, lw=3.4, label="transistor (truth)")
            errs = []
            for build, col, lab in (("shipped", OURS, "our GUP + IBIS map"),
                                    ("gate_replay_silicon_full", REAL, "real gate + measured map")):
                t, _g, ku, pad = _run(dev, w_ps, build)
                a.plot(t, ku, color=col, lw=2.2, ls="--" if build == "shipped" else "-", label=lab)
                e, _ = _peak_err(t, pad, t_si, si, w)
                b.plot(t, pad, color=col, lw=2.4, ls="--" if build == "shipped" else "-", label=lab)
                errs.append((col, f"{e:+.0f} %"))
            # the whole point of the bottom row is the purple overshoot, and a legend box in
            # the upper right of the panel is drawn directly over it
            for i, (col, txt) in enumerate(errs):
                b.text(0.03, 0.96 - 0.10 * i, txt, transform=b.transAxes, color=col,
                       fontsize=12, fontweight="bold", va="top")
            a.set_title(f"{DEPTH_PCT[w_ps]} % stress", fontweight="bold")
            for c in (a, b):
                c.set_xlim(w - 0.35, w + span)
                c.grid(alpha=0.3)
            a.set_ylim(-0.45, 1.35)
            b.set_ylim(-0.12, ylim * 1.15)
            b.set_xlabel("time (ns)")
            handles = a.get_legend_handles_labels()
        ax[0][0].set_ylabel("Ku")
        ax[1][0].set_ylabel("pad (V)")
        fig.legend(*handles, loc="lower center", ncol=3, fontsize=11.5, frameon=False,
                   bbox_to_anchor=(0.5, -0.015))
        fig.suptitle(f"{dev}  |  the same map, two gates: the error is the gate's shape",
                     fontsize=15, fontweight="bold")
        fig.tight_layout(rect=(0, 0.045, 1, 0.93))
        save(fig, f"ku_consequence_{dev}")


def stage_law() -> None:
    """The four numbers as geometry: a threshold on the input, a slope, and a taper."""
    XLIN, VT = 0.45, 0.45
    t = np.linspace(0, 4.6, 500)
    u = np.clip((t - 0.35) / 0.30, 0, 1)                    # the stage's input, rising
    h = np.clip((u - VT) / (1 - VT), 0, 1)                  # drive: nothing until u passes vt
    v = np.zeros_like(t)
    for i in range(1, len(t)):
        up = 0.72 * h[i] * min(1.0, (1 - v[i - 1]) / XLIN)
        v[i] = min(1.0, v[i - 1] + up * (t[i] - t[i - 1]))
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, 2, figsize=(12.6, 3.8))
        a = ax[0]
        a.plot(t, u, color="#666666", lw=3.4)
        a.axhline(VT, color=OURS, lw=1.8, ls="--")
        a.annotate("vt  —  the stage does nothing\nuntil its input passes this",
                   (2.30, VT), textcoords="offset points", xytext=(-30, -44), color=OURS,
                   fontsize=12, fontweight="bold",
                   arrowprops=dict(arrowstyle="->", color=OURS, lw=1.5))
        a.set_title("its input", fontweight="bold", fontsize=13)
        a.set_ylim(-0.06, 1.22)
        a.set_xlabel("time")
        a.set_ylabel("0 to 1")
        a.grid(alpha=0.3)

        b = ax[1]
        i0, i1 = int(np.argmax(v > 0.02)), int(np.argmax(v > 1 - XLIN))
        b.plot(t[i0:i1 + 1], v[i0:i1 + 1], color=REAL, lw=7.0, alpha=0.4, zorder=1)
        b.plot(t, v, color=SIL, lw=3.4, zorder=2)
        b.axhline(1 - XLIN, color="#999999", lw=1.5, ls=":")
        b.annotate("s_up  —  constant current,\nso the gate travels on a\nstraight ramp",
                   (t[(i0 + i1) // 2], v[(i0 + i1) // 2]), textcoords="offset points",
                   xytext=(-66, 52), color=REAL, fontsize=12, fontweight="bold",
                   arrowprops=dict(arrowstyle="->", color=REAL, lw=1.5))
        b.annotate("x_lin  —  within this much of\nthe rail the current tapers off",
                   (2.60, 0.90), textcoords="offset points", xytext=(-40, -80),
                   color="#4A4A4A", fontsize=12, fontweight="bold",
                   arrowprops=dict(arrowstyle="->", color="#4A4A4A", lw=1.5))
        b.set_title("the gate it produces", fontweight="bold", fontsize=13)
        b.set_ylim(-0.06, 1.22)
        b.set_xlabel("time")
        b.grid(alpha=0.3)
        fig.suptitle("one stage  —  s_dn is the same picture on the way back",
                     fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.88))
        save(fig, "stage_law")


def main() -> int:
    print("figures for the 09-24 deck:")
    map_from_probe("ex2")
    sampling_grid("ex2")
    stage_nonlinear("ex2")
    stage_law()
    model_blocks()
    k_choice()
    calib_select()
    knobs()
    fit_search()
    bisection()
    solve_ku()
    prior_shape()
    map_summary()
    what_we_have()
    coverage()
    four_numbers()
    ccomp_reject()
    pick_rank()
    for dev in DEV:
        works_levels(dev)
        gate_shape(dev)
        ku_consequence(dev)
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}")
    return 0




# --------------------------------------------------------------------------- #
# the method half: what the file gives, what one stressed run adds, and the law
# --------------------------------------------------------------------------- #

def sampling_grid(dev: str = "ex2") -> None:
    """Every stressed width stops the gate at a different point of the same trajectory."""
    folder, node, gname, widths, _ylim, _span = DEV[dev]
    tf, gfull, _t, _g = f17._norm_pair(dev, widths[0], node)
    cols = ["#8B1A3A", "#B03060", "#C2683B", "#D99A2B", "#4C8C3F"]
    with plt.rc_context(BODY):
        fig, a = plt.subplots(figsize=(11.6, 4.6))
        a.plot(tf, gfull, color="#B9B9B9", lw=5.0, label="the gate on a full transition", zorder=1)
        for k, (w_ps, c) in enumerate(zip(widths, cols)):
            ts, greal = f17._norm_pair(dev, w_ps, node)[2:]
            a.plot(ts, greal, color=c, lw=2.3, zorder=2)
            i = int(np.nanargmax(greal))
            a.plot(ts[i], greal[i], "o", color=c, ms=10, zorder=5)
            # the peaks crowd together, so label on the falling branch - but each curve has
            # to be cut at a different height or the five labels land on the same spot
            tail = np.asarray(greal)[i:]
            lvl = 0.62 - 0.11 * k
            j = i + int(np.argmax(tail <= lvl)) if np.any(tail <= lvl) else len(greal) - 1
            a.annotate(f"{DEPTH_PCT[w_ps]} %", (ts[j], greal[j]), textcoords="offset points",
                       xytext=(7, 1), color=c, fontsize=12.5, fontweight="bold")
        a.set_xlim(0.3, 2.6)
        a.set_ylim(-0.05, 1.18)
        a.set_xlabel("time from the input edge (ns)")
        a.set_ylabel(f"gate {gname}, 0 to 1")
        a.grid(alpha=0.3)
        a.legend(loc="upper left", fontsize=11)
        a.set_title(f"{dev}  |  each stressed width stops the clock at a different point "
                    "of the same path", fontsize=14, fontweight="bold")
        fig.tight_layout()
        save(fig, f"sampling_grid_{dev}")


def stage_nonlinear(dev: str = "ex2", depth: int | None = None) -> None:
    """Measured stage response against linear superposition, down the chain.

    The superposition itself comes from predriver_stage_probe, which owns it - this only
    re-plots one width across the chain so it fits a slide.
    """
    import predriver_stage_probe as psp
    depth = depth or DEV[dev][3][0]
    nodes = psp.NODES[dev][1:] if hasattr(psp, "NODES") else \
        ["v(xdut.n2)", "v(xdut.n3)", "v(xdut.n4)", "v(pad_sp)"]
    labels = ["stage 1  (n2)", "stage 2  (n3)", "output gate  (n4)", "the pad"]
    full = psp.parse_tr0(psp.OUT / dev / "full" / "run.tr0")
    sh = psp.parse_tr0(psp.OUT / dev / f"w{depth}" / "run.tr0")
    tf = np.asarray(full["time"], float) * 1e9
    ts = np.asarray(sh["time"], float) * 1e9
    vf, vs = psp.signals(full, nodes), psp.signals(sh, nodes)
    grid = np.arange(4.6, 9.4, 0.002)
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, len(nodes), figsize=(3.1 * len(nodes), 3.9), sharey=True)
        for a, n, lab in zip(ax, nodes, labels):
            g_full, _, _ = psp.normalise(tf, vf[n], tf, vf[n])
            g_short, _, _ = psp.normalise(tf, vf[n], ts, vs[n])
            tau, gr, gf = psp.step_responses(tf, g_full)
            p1, _p2 = psp.lti_predictions(grid, tau, gr, gf, depth / 1000.0)
            a.plot(grid - 5.0, p1, color="#C2683B", lw=2.2, ls=(0, (1.5, 1.6)),
                   label="if the stage were linear")
            a.plot(ts - 5.0, g_short, color=SIL, lw=3.0, label="measured")
            m, pl = float(np.nanmax(g_short)), float(np.nanmax(p1))
            a.annotate(f"{m:.2f}", (ts[np.nanargmax(g_short)] - 5.0, m), fontsize=11,
                       fontweight="bold", color=SIL, textcoords="offset points", xytext=(-4, 7),
                       ha="right")
            a.annotate(f"{pl:.2f}", (grid[np.nanargmax(p1)] - 5.0, pl), fontsize=11,
                       fontweight="bold", color="#C2683B", textcoords="offset points",
                       xytext=(6, 4), ha="left")
            a.set_title(lab, fontweight="bold", fontsize=12)
            a.set_xlim(-0.3, 3.0)
            a.set_ylim(-0.08, 1.25)
            a.grid(alpha=0.3)
            a.set_xlabel("time (ns)")
            handles = a.get_legend_handles_labels()
        ax[0].set_ylabel("0 = rest, 1 = full swing")
        fig.legend(*handles, loc="lower center", ncol=2, fontsize=11, frameon=False,
                   bbox_to_anchor=(0.5, -0.02))
        fig.suptitle(f"{dev}  |  {depth} ps pulse: every stage under-reaches what a linear "
                     "filter would do, and the gap compounds",
                     fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0.06, 1, 0.9))
        save(fig, f"stage_nonlinear_{dev}")


# --------------------------------------------------------------------------- #
# the method, step by step: what is fitted, what cannot be, and how one run decides
# --------------------------------------------------------------------------- #
SC = ROOT / "results" / "stage_count_from_file_2026-09-21"
CAND = {                      # (K, shape) -> the build folder, for ex2's nine candidates
    (k, sh): (SC / ("step6" if sh == "0.5_0.7" else "step8") / "ex2_c2.64" /
              f"ibis_prior_K{k}_prior{sh}_xlin0.45_calibpad810")
    for k in (3, 4, 5) for sh in ("0.5_0.7", "0.4_0.6", "0.4_0.9")
}
SHIPPED_FULL = SC / "knee_models" / "ex2_c2.64" / "shipped" / "full" / "run.raw"
KCOL = {3: "#B03060", 4: "#D9842B", 5: "#2E7D6E"}
PICK = (3, "0.5_0.7")


def _cand(folder, which):
    raw = sl.parse_ngspice_raw(folder / which / "run.raw")
    t = sl.time_ns(raw) - 5.0
    return t, sl.signal(raw, "v(x1.ku)"), sl.trace(raw, "out")


def model_blocks() -> None:
    """The architecture, with what is known before any measurement marked."""
    with plt.rc_context(BODY):
        fig, a = plt.subplots(figsize=(12.4, 3.5))
        a.set_xlim(0, 124)
        a.set_ylim(0, 34)
        a.axis("off")
        def box(x, w, label, sub, fc, ec):
            a.add_patch(plt.Rectangle((x, 16), w, 10, facecolor=fc, edgecolor=ec, lw=2.0))
            a.text(x + w / 2, 21.4, label, ha="center", va="center", fontsize=13, fontweight="bold")
            if sub:
                a.text(x + w / 2, 12.6, sub, ha="center", va="top", fontsize=10.5, color=ec)
        def arrow(x0, x1, lab=""):
            a.annotate("", (x1, 21), (x0, 21), arrowprops=dict(arrowstyle="-|>", lw=1.8, color="#555555"))
            if lab:
                a.text((x0 + x1) / 2, 27.5, lab, ha="center", fontsize=11.5, fontweight="bold")
        a.text(2, 21, "input", fontsize=13, fontweight="bold", va="center")
        arrow(11, 17)
        for i, x in enumerate((17, 28, 39)):
            box(x, 9, str(i + 1), "", "#EFEFEF", "#666666")
        a.text(51.5, 21, "\u2026", ha="center", va="center", fontsize=15)
        box(55, 9, "K", "", "#EFEFEF", "#666666")
        a.text(38, 8.5, "K identical current-limited stages", ha="center", fontsize=11.5,
               color="#666666", fontweight="bold")
        arrow(64, 72, "gate g")
        box(72, 16, "the map", "", "#EFEFEF", REAL)
        arrow(88, 96, "Ku")
        box(96, 18, "I-V tables", "", "#EFEFEF", "#666666")
        arrow(114, 121)
        a.text(122, 21, "pad", fontsize=13, fontweight="bold", va="center")
        # one label under both: two centred captions ran into each other
        a.plot([72, 72, 114, 114], [14.5, 12.5, 12.5, 14.5], color="#999999", lw=1.4)
        a.text(93, 8.5, "both straight from the file, unchanged", ha="center", fontsize=11.5,
               color="#666666", fontweight="bold")
        fig.tight_layout()
        save(fig, "model_blocks")


def k_choice(dev: str = "ex2") -> None:
    """What the file sees (a plateau in the fit) against what a stressed pulse sees."""
    import csv as _csv
    rms = None
    with (SC / "step1_summary.csv").open(encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            if r["pass_"] == "est_knee" and r["buffer"] == "ex2" and r["chain"] == "pull-up":
                rms = [float(x) for x in r["rms_by_K"].split()]
    Ks = np.arange(1, len(rms) + 1)
    best = min(rms)
    band = [k for k, v in zip(Ks, rms) if v <= 1.25 * best][:3]
    t_si, si, _r = f17.transistor_pad("ex2", 810)
    t_si, w = t_si - 5.0, 0.810
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.3))
        a = ax[0]
        a.axhspan(0, 1.25 * best, color=REAL, alpha=0.10)
        a.axhline(1.25 * best, color=REAL, lw=1.5, ls="--")
        a.plot(Ks, rms, "o-", color=SIL, lw=2.6, ms=8, zorder=3)
        for k in band:
            a.plot(k, rms[k - 1], "o", color=REAL, ms=14, zorder=4)
        a.annotate("within 25 % of the best fit:\nthe file cannot separate these",
                   (band[1], rms[band[1] - 1]), textcoords="offset points", xytext=(28, 54),
                   fontsize=11.5, fontweight="bold", color=REAL,
                   arrowprops=dict(arrowstyle="->", color=REAL, lw=1.5))
        a.set_xticks(Ks)
        a.set_xlabel("number of stages, K")
        a.set_ylabel("fit error against the file's Ku(t)")
        a.set_ylim(0, max(rms) * 1.12)
        a.set_title("what the file sees \u2014 a plateau", fontsize=13, fontweight="bold")
        a.grid(alpha=0.3)

        b = ax[1]
        b.plot(t_si, si, color=SIL, lw=4.0, label="transistor (truth)", zorder=4)
        for k in band:
            t, _ku, pad = _cand(CAND[(int(k), "0.5_0.7")], "d810")
            e, _ = _peak_err(t, pad, t_si, si, w)
            b.plot(t, pad, color=KCOL[int(k)], lw=2.4, label=f"K = {k}   peak {e:+.0f} %")
        b.set_xlim(w - 0.35, w + 2.0)
        b.set_ylim(-0.12, 1.5)
        b.set_title("what one stressed pulse sees \u2014 three different buffers",
                    fontsize=13, fontweight="bold")
        b.set_xlabel("time (ns)")
        b.set_ylabel("pad (V)")
        b.grid(alpha=0.3)
        b.legend(loc="upper right", fontsize=10.5)
        fig.suptitle("ex2  |  the file narrows K to a band of three and cannot choose inside it",
                     fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.91))
        save(fig, "k_choice")


def calib_select(dev: str = "ex2") -> None:
    """After calibration every candidate hits the measured peak; the tail is what separates them."""
    t_si, si, _r = f17.transistor_pad("ex2", 810)
    t_si, w = t_si - 5.0, 0.810
    grid = np.arange(w - 0.1, w + 1.5, 0.004)
    ref = np.interp(grid, t_si, si)
    rows = []
    with plt.rc_context(BODY):
        fig, a = plt.subplots(figsize=(11.6, 4.5))
        a.plot(t_si, si, color=SIL, lw=4.4, label="transistor (truth)", zorder=5)
        for (k, sh), d in CAND.items():
            t, _ku, pad = _cand(d, "d810")
            rms = 1e3 * float(np.sqrt(np.mean((np.interp(grid, t, pad) - ref) ** 2)))
            rows.append(((k, sh), rms))
            is_pick = (k, sh) == PICK
            a.plot(t, pad, color=REAL if is_pick else "#9AA5A8",
                   lw=3.0 if is_pick else 1.5, alpha=1.0 if is_pick else 0.8,
                   zorder=4 if is_pick else 2,
                   label="the one it picks  (K3, 0.5/0.7)" if is_pick else None)
        a.plot([], [], color="#9AA5A8", lw=1.5, label="the other eight candidates")
        pk = float(si[(t_si >= w - 0.3) & (t_si <= w + 2.6)].max())
        a.annotate("every candidate reaches the measured peak height:\nthe calibration put it "
                   "there",
                   (1.45, pk), textcoords="offset points", xytext=(-238, 44), fontsize=11.5,
                   fontweight="bold", color="#444444",
                   arrowprops=dict(arrowstyle="->", color="#444444", lw=1.4))
        a.annotate("they separate here", (2.05, 0.26), textcoords="offset points",
                   xytext=(30, 40), fontsize=11.5, fontweight="bold", color=REAL,
                   arrowprops=dict(arrowstyle="->", color=REAL, lw=1.4))
        a.set_xlim(w - 0.3, w + 2.1)
        a.set_ylim(-0.12, 1.25)
        a.set_xlabel("time from the input edge (ns)")
        a.set_ylabel("pad (V)")
        a.grid(alpha=0.3)
        a.legend(loc="upper right", fontsize=11)
        a.set_title("ex2  |  the calibration spends the peak, so the rest of the waveform "
                    "is what chooses", fontsize=14, fontweight="bold")
        fig.tight_layout()
        save(fig, "calib_select")
    best = min(rows, key=lambda r: r[1])
    print("    waveform rms at the calibration width (mV): "
          + ", ".join(f"K{k} {sh} {v:.0f}" for (k, sh), v in sorted(rows, key=lambda r: r[1])[:4]))
    print(f"    best = K{best[0][0]} {best[0][1]}; the recipe picks K{PICK[0]} {PICK[1]}")


# --------------------------------------------------------------------------- #
# from the 09-17 method film's exported arrays - see its README
# --------------------------------------------------------------------------- #
NPZ = ROOT / "results" / "method_animations_2026-09-17" / "method_data.npz"
_FILM = None


def film():
    global _FILM
    if _FILM is None:
        _FILM = np.load(NPZ, allow_pickle=True)
    return _FILM




def knobs() -> None:
    """What each of the four numbers does, swept one at a time, on a truncated pulse.

    On a rising full-swing transition s_dn does nothing visible - it is the discharge rate - so
    the sweep is drawn on the 810 ps pulse, where every one of the four acts. Simulated with
    `current_limited_stage_model`, the module that owns the stage law, from the fitted values
    the 09-17 film exported.
    """
    import current_limited_stage_model as cl
    d = film()
    base = {n: float(v) for n, v in zip(d["knob_names"], d["knob_base"])}
    K, W = 3, 0.810
    grid = np.arange(0.0, 4.2, cl.DT)
    u = ((grid >= 0.30) & (grid < 0.30 + W)).astype(float)
    cols = ["#C9D7E4", "#8FAEC8", "#5C87AD", "#2C5C88", "#123853"]
    TEXT = {
        "s_up": ("s_up", "how hard a stage charges",
                 "a faster gate gets further before the pulse ends"),
        "s_dn": ("s_dn", "how hard it discharges",
                 "sets how quickly the gate lets go again"),
        "vt": ("vt", "the input it needs before it reacts",
               "a later hand-off, so less of the pulse survives"),
        "x_lin": ("x_lin", "how near the rail it tapers",
                  "changes the shape of the approach, not the timing"),
    }
    with plt.rc_context(BODY):
        fig, axs = plt.subplots(2, 2, figsize=(13.4, 5.9), sharex=True, sharey=True)
        for a, name in zip(axs.ravel(), ["s_up", "s_dn", "vt", "x_lin"]):
            vals = d[f"knob_{name}_v"]
            for v, c in zip(vals, cols):
                prm = dict(base)
                prm[name] = float(v)
                g = cl.simulate_chain(u, [(prm["s_up"], prm["s_dn"], prm["vt"],
                                           prm["x_lin"], 1.0)] * K)
                a.plot(grid, g, color=c, lw=2.2)
            g0 = cl.simulate_chain(u, [(base["s_up"], base["s_dn"], base["vt"],
                                        base["x_lin"], 1.0)] * K)
            a.plot(grid, g0, color=SIL, lw=3.6, zorder=5)
            sym, what, effect = TEXT[name]
            a.set_title(f"{sym}   \u2014   {what}", fontsize=13, fontweight="bold")
            a.text(0.035, 0.94, f"swept {vals[0]:.2g} \u2192 {vals[-1]:.2g}",
                   transform=a.transAxes, fontsize=11.5, color="#123853",
                   fontweight="bold", va="top")
            a.text(0.035, 0.82, effect, transform=a.transAxes, fontsize=11,
                   color="#555555", va="top")
            a.set_xlim(0.15, 3.1)
            a.set_ylim(-0.04, 1.16)
            a.grid(alpha=0.3)
        for a in axs[1]:
            a.set_xlabel("time from the input edge (ns)")
        for a in axs[:, 0]:
            a.set_ylabel("the gate, 0 to 1")
        axs[0][0].plot([], [], color=SIL, lw=3.6, label="the value the fit chose")
        axs[0][0].legend(loc="lower right", fontsize=10.5)
        fig.suptitle("ex2  |  the four numbers, each swept on its own, on the 810 ps pulse",
                     fontsize=14.5, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        save(fig, "knobs")


def fit_search() -> None:
    """The four numbers searched until the chain reproduces the file's Ku(t)."""
    d = film()
    t, tgt, cur, rms = d["fit_t"], d["fit_target"], d["fit_curves"], d["fit_rms"]
    keep = [0, 3, 7, 12, 20, len(rms) - 1]
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.2),
                              gridspec_kw={"width_ratios": [1.85, 1]})
        a = ax[0]
        a.plot(t, tgt, color=SIL, lw=4.6, label="the file's Ku(t) \u2014 the target", zorder=5)
        for rank, i in enumerate(keep):
            sh = 0.18 + 0.72 * rank / (len(keep) - 1)
            a.plot(t, cur[i], color=(0.12, 0.31, 0.48, sh), lw=2.0,
                   label="the chain, as the search improves it" if rank == 0 else None)
        a.plot(t, cur[-1], color=REAL, lw=2.8, label="where it lands", zorder=4)
        a.set_xlim(-0.25, 3.0)     # the rise; fit_t runs -0.4 to 13 ns, input on at 0
        a.set_ylim(-0.08, 1.18)
        a.set_xlabel("time (ns)")
        a.set_ylabel("Ku")
        a.grid(alpha=0.3)
        a.legend(loc="lower right", fontsize=10.5)
        a.set_title("the chain is moved until it lands on the file", fontsize=13, fontweight="bold")

        b = ax[1]
        b.plot(np.arange(1, len(rms) + 1), rms, "o-", color=SIL, lw=2.2, ms=5)
        b.plot(len(rms), rms[-1], "o", color=REAL, ms=11, zorder=5)
        b.set_yscale("log")
        b.set_xlabel("trial")
        b.set_ylabel("error against the file")
        b.grid(alpha=0.3, which="both")
        b.set_title(f"{rms[0]:.3f}  \u2192  {rms[-1]:.4f}", fontsize=13, fontweight="bold")
        p0, p1 = d["fit_params"][0], d["fit_params"][-1]
        # the trail is flat and low across most of the panel; the clear space is top right
        b.text(0.97, 0.72, f"s_up {p1[0]:.2f}   s_dn {p1[1]:.2f}\nvt {p1[2]:.2f}   x_lin {p1[3]:.2f}",
               transform=b.transAxes, fontsize=11, fontweight="bold", color=REAL,
               ha="right", va="top")
        fig.suptitle("ex2  |  step 2: the four numbers are fitted to the file, and cost no "
                     "measurement", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.9))
        save(fig, "fit_search")


def bisection() -> None:
    """The one stressed pad run placing the threshold: every iteration the search wrote."""
    d = film()
    t, tgt, cur, vt = d["bis_t"], d["bis_target"], d["bis_curves"], d["bis_vt"]
    w = float(d["bis_width_ps"][0]) / 1000.0
    order = np.argsort(np.abs(vt - vt[-1]))[::-1]
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.2),
                              gridspec_kw={"width_ratios": [1.85, 1]})
        a = ax[0]
        a.plot(t, tgt, color=SIL, lw=4.6, label="the measured pad \u2014 the target", zorder=5)
        for rank, i in enumerate(order):
            sh = 0.16 + 0.70 * rank / (len(order) - 1)
            a.plot(t, cur[i], color=(0.48, 0.17, 0.38, sh), lw=1.8,
                   label="each bisection step" if rank == 0 else None)
        a.plot(t, cur[-1], color=REAL, lw=2.8, label=f"where it stops (vt {vt[-1]:.3f})", zorder=4)
        a.set_xlim(-0.25, 2.4)     # bis_t is already measured from the input edge
        a.set_xlabel("time (ns)")
        a.set_ylabel("pad (V)")
        a.grid(alpha=0.3)
        a.legend(loc="upper right", fontsize=10.5)
        a.set_title("one measured pulse moves one number", fontsize=13, fontweight="bold")

        b = ax[1]
        b.plot(np.arange(1, len(vt) + 1), vt, "o-", color=SIL, lw=2.2, ms=7)
        b.plot(len(vt), vt[-1], "o", color=REAL, ms=12, zorder=5)
        b.axhline(vt[-1], color=REAL, lw=1.4, ls="--")
        b.annotate(f"vt = {vt[-1]:.3f}", (len(vt), vt[-1]), textcoords="offset points",
                   xytext=(-92, 16), fontsize=12, fontweight="bold", color=REAL)
        for i in (1, 2):      # steps 2 and 3 probe the ends of the bracket, hence the spikes
            b.annotate("bracket\nend", (i + 1, vt[i]), textcoords="offset points",
                       xytext=(6, 12 if vt[i] < 0.35 else -30), fontsize=10.5,
                       color="#777777", fontweight="bold")
        b.set_xlabel("bisection step")
        b.set_ylabel("the threshold vt")
        b.set_ylim(-0.08, 0.80)
        b.grid(alpha=0.3)
        b.set_title("bracket 0 \u2026 0.7, then halve", fontsize=13, fontweight="bold")
        fig.suptitle("ex2  |  step 4: the stressed run sets the amplitude, by moving vt alone",
                     fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.9))
        save(fig, "bisection")


def solve_ku() -> None:
    """Where Ku(t) comes from: two loads at one instant give two equations, two unknowns."""
    d = film()
    v, iv_v, iv_pu, iv_pd = d["slv_v"], d["slv_iv_v"], d["slv_iv_pu"], d["slv_iv_pd"]
    ans, tns, vcc = d["slv_ans"], float(d["slv_t_ns"][0]), float(d["slv_vcc"][0])
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.2))
        a = ax[0]
        a.plot(iv_v, iv_pu * 1e3, color="#B03060", lw=3.0, label="pull-up, fully on")
        a.plot(iv_v, iv_pd * 1e3, color="#2E7D6E", lw=3.0, label="pull-down, fully on")
        # name the curves on the curves: a legend box in this panel sits over the
        # pull-down branch for most of its travel
        for arr, col, lab, xl, dy in ((iv_pd, "#2E7D6E", "pull-down, fully on", 1.75, 9),
                                      (iv_pu, "#B03060", "pull-up, fully on", 1.05, -20)):
            a.annotate(lab, (xl, float(np.interp(xl, iv_v, arr * 1e3))),
                       textcoords="offset points", xytext=(0, dy), ha="center",
                       fontsize=11.5, fontweight="bold", color=col)
        for x, lab in zip(v, ("load 1", "load 2")):
            a.axvline(x, color="#888888", lw=1.4, ls="--")
            ha, off = ("left", 7) if lab.endswith("1") else ("right", -7)
            a.annotate(f"{lab}\n{x:.2f} V", (x, -18.0), textcoords="offset points",
                       xytext=(off, 0), ha=ha, va="top", fontsize=11, fontweight="bold",
                       color="#555555")
        a.set_xlabel("pad voltage (V)")
        a.set_ylabel("current (mA)")
        a.grid(alpha=0.3)
        a.margins(y=0.14)
        a.set_title(f"the file's I-V curves, read at one instant (t = {tns:.2f} ns)",
                    fontsize=13, fontweight="bold")

        b = ax[1]
        b.axis("off")
        b.text(0.0, 0.94, "the same instant, recorded into two different loads:", fontsize=12.5,
               fontweight="bold")
        b.text(0.02, 0.78, "load 1:   Ku\u00b7I_pu(V\u2081)  +  Kd\u00b7I_pd(V\u2081)  =  "
                           "the current it took", fontsize=12, family="monospace")
        b.text(0.02, 0.66, "load 2:   Ku\u00b7I_pu(V\u2082)  +  Kd\u00b7I_pd(V\u2082)  =  "
                           "the current it took", fontsize=12, family="monospace")
        b.text(0.0, 0.46, "Two equations, two unknowns \u2014 so one instant of two recordings\n"
                          "gives Ku and Kd outright. No fitting.", fontsize=12.5)
        b.text(0.0, 0.20, f"here:   Ku = {ans[0]:.3f}     Kd = {ans[1]:.3f}", fontsize=15,
               fontweight="bold", color=REAL, family="monospace")
        b.text(0.0, 0.05, "Repeat at every instant and the result is Ku(t) \u2014 what the "
                          "file gives us.", fontsize=12)
        fig.suptitle(f"where Ku(t) comes from  |  ex2, supply {vcc:.1f} V",
                     fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.9))
        save(fig, "solve_ku")


def prior_shape() -> None:
    """The measured map against the analytic shape track 1 has to assume in its place."""
    d = film()
    g, meas, prior = d["cmp_g"], d["cmp_meas"], d["cmp_prior"]
    with plt.rc_context(BODY):
        fig, a = plt.subplots(figsize=(8.6, 4.4))
        a.plot(g, meas, color=REAL, lw=4.0, label="measured on the transistor")
        a.plot(g, prior, color=OURS, lw=2.8, ls="--",
               label="the analytic shape track 1 assumes")
        a.set_xlabel("gate, 0 to 1")
        a.set_ylabel("Ku")
        a.set_xlim(-0.02, 1.02)
        a.grid(alpha=0.3)
        a.legend(loc="upper left", fontsize=11)
        a.set_title("with no probe, the map's shape has to be assumed \u2014 so it is one of the "
                    "things the\nstressed run chooses", fontsize=13, fontweight="bold")
        fig.tight_layout()
        save(fig, "prior_shape")


def map_summary() -> None:
    """Peak error against stress depth: native, our gate-state model, the measured map."""
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, 2, figsize=(11.4, 4.2), sharey=True)
        for a, dev in zip(ax, ("ex2", "inv_chain")):
            _f, node, _g, widths, _y, _s = DEV[dev]
            xs = [DEPTH_PCT[w] for w in widths]
            series = {"native IBIS": ([], NAT, ":"), "our gate-state model": ([], OURS, "--"),
                      "real gate + measured map": ([], REAL, "-")}
            for w_ps in widths:
                w = w_ps / 1000.0
                d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / f"{dev}_short_high_w{w_ps}ps.csv")
                t_si, si, _r = f17.transistor_pad(dev, w_ps)
                t_si = t_si - 5.0
                series["native IBIS"][0].append(
                    _peak_err(d["time_ns"] - 5.0, d["hspice_pad"], t_si, si, w)[0])
                for build, key in (("shipped", "our gate-state model"),
                                   ("gate_replay_silicon_full", "real gate + measured map")):
                    t, _g2, _k, pad = _run(dev, w_ps, build)
                    series[key][0].append(_peak_err(t, pad, t_si, si, w)[0])
            a.axhspan(-10, 10, color=REAL, alpha=0.10)
            a.axhline(0, color="#999999", lw=1.2)
            for lab, (ys, c, ls) in series.items():
                a.plot(xs, ys, ls, color=c, lw=2.6, marker="o", ms=7, label=lab)
            a.set_title(dev, fontsize=13, fontweight="bold")
            a.set_xlabel("stress depth (% of the settled swing)")
            a.set_xticks(xs)
            a.grid(alpha=0.3)
        ax[0].set_ylabel("peak error against the transistor (%)")
        ax[0].legend(loc="upper right", fontsize=10.5)
        ax[0].text(52, 4, "\u00b110 %", fontsize=11, color=REAL, fontweight="bold")
        fig.suptitle("given the right gate, the measured map holds across the whole stress axis",
                     fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.9))
        save(fig, "map_summary")


def what_we_have() -> None:
    """What a probe gives us, against what the published file gives a customer."""
    with plt.rc_context(BODY):
        fig, a = plt.subplots(figsize=(11.0, 4.3))
        a.set_xlim(0, 100)
        a.set_ylim(-7, 54)
        a.axis("off")
        rows = [("the output stage's I-V curves", True, True),
                ("one full transition, Ku(t)", True, True),
                ("the map from gate to Ku", True, False),
                ("the gate's own trajectory", True, False)]
        for col, (x, head, c) in enumerate(((6, "us, on our own test chips", REAL),
                                            (54, "a customer, with the published file", OURS))):
            a.add_patch(plt.Rectangle((x - 2, 4), 42, 44, facecolor="#F4F6F5",
                                      edgecolor=c, lw=2.2))
            a.text(x + 19, 43, head, ha="center", fontsize=13, fontweight="bold", color=c)
            for i, (lab, mine, theirs) in enumerate(rows):
                y = 35 - i * 7.2
                ok = mine if col == 0 else theirs
                a.text(x + 1, y, "\u2713" if ok else "\u2717", fontsize=15,
                       fontweight="bold", color=c if ok else "#BBBBBB")
                a.text(x + 6, y, lab, fontsize=12,
                       color="#222222" if ok else "#AAAAAA", va="center_baseline")
        a.annotate("", (52, 26), (48, 26),
                   arrowprops=dict(arrowstyle="-|>", lw=2.0, color="#555555"))
        a.text(50, -2, "the whole question is this gap", ha="center", fontsize=12.5,
               fontweight="bold", color="#555555")
        fig.tight_layout()
        save(fig, "what_we_have")


def coverage() -> None:
    """Which part of the stress axis this has actually been tested on."""
    rows = [("how short the pulse is", ["90 %", "80 %", "70 %", "60 %", "50 %"], "below 50 %"),
            ("direction", ["short HIGH"], "short LOW, on 11 of 12 buffers"),
            ("how many pulses", ["one"], "trains"),
            ("what the pin drives", ["50 \u03a9 \u2016 2 pF"], "any other load"),
            ("conditions", ["Typical"], "Min / Max, supply, temperature")]
    with plt.rc_context(BODY):
        fig, a = plt.subplots(figsize=(11.6, 4.2))
        a.set_xlim(0, 100)
        a.set_ylim(0, len(rows) * 10 + 8)
        a.axis("off")
        a.text(1, len(rows) * 10 + 2, "tested", fontsize=12.5, fontweight="bold", color=REAL)
        a.text(56, len(rows) * 10 + 2, "not tested", fontsize=12.5, fontweight="bold", color="#B0563C")
        for i, (name, done, gap) in enumerate(rows):
            y = (len(rows) - 1 - i) * 10 + 2
            a.text(1, y + 6.4, name, fontsize=12, fontweight="bold", color="#333333")
            for j, lab in enumerate(done):
                a.add_patch(plt.Rectangle((1 + j * 10.6, y), 9.6, 5.2, facecolor=REAL,
                                          alpha=0.22, edgecolor=REAL, lw=1.5))
                a.text(1 + j * 10.6 + 4.8, y + 2.6, lab, ha="center", va="center", fontsize=11)
            a.add_patch(plt.Rectangle((56, y), 42, 5.2, facecolor="#B0563C", alpha=0.10,
                                      edgecolor="#B0563C", lw=1.5, linestyle="--"))
            a.text(57.5, y + 2.6, gap, va="center", fontsize=11, color="#8A3F2A")
        fig.suptitle("what this has been tested on", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        save(fig, "coverage")


def four_numbers() -> None:
    """The stage law dissected: every term coloured, every symbol defined."""
    C = {"s": "#1F6F8B", "h": "#8E44AD", "x": "#B0563C", "v": "#444444"}

    def run(ax, fig, x, y, parts, size):
        """Draw coloured segments left to right, advancing by what each one measured."""
        for txt, col in parts:
            t = ax.text(x, y, txt, fontsize=size, family="monospace", color=col,
                        fontweight="bold" if col != C["v"] else "normal", va="center")
            fig.canvas.draw()
            x += t.get_window_extent().width / fig.get_size_inches()[0] / fig.dpi * 100
        return x

    with plt.rc_context(BODY):
        fig = plt.figure(figsize=(12.6, 5.5))
        a = fig.add_axes([0, 0.52, 1, 0.46])
        a.axis("off")
        a.set_xlim(0, 100)
        a.set_ylim(0, 30)
        a.text(50, 27, "one stage, as the physics on the last slide requires it",
               ha="center", fontsize=13, fontweight="bold", color="#333333")
        run(a, fig, 3.5, 16, [
            ("dv/dt  =  ", C["v"]), ("s_up", C["s"]), ("\u00b7h(u)\u00b7", C["h"]),
            ("min(1, (1\u2212v)/", C["v"]), ("x_lin", C["x"]), (")", C["v"]),
            ("   \u2212   ", C["v"]), ("s_dn", C["s"]), ("\u00b7h(1\u2212u)\u00b7", C["h"]),
            ("min(1, v/", C["v"]), ("x_lin", C["x"]), (")", C["v"])], 15)
        x = run(a, fig, 3.5, 5, [
            ("with   h(u) = clip((u \u2212 ", C["v"]), ("vt", C["h"]),
            (")/(1 \u2212 ", C["v"]), ("vt", C["h"]), ("), 0, 1)", C["v"])], 14)
        a.text(x + 6, 5, "u = the stage's input,   v = its output", fontsize=13,
               family="monospace", color="#888888", va="center")

        b = fig.add_axes([0.03, 0.02, 0.94, 0.46])
        b.axis("off")
        b.set_xlim(0, 100)
        b.set_ylim(0, 100)
        cols = [2, 13, 40, 72]
        for cx, h in zip(cols, ["", "is", "what it decides", "where its value comes from"]):
            b.text(cx, 92, h, fontsize=11.5, fontweight="bold", color="#777777")
        rows = [
            ("s_up", C["s"], "the charging current",
             "where the gate is when the pulse ends", "fitted to the file's Ku(t)"),
            ("s_dn", C["s"], "the discharging current",
             "how quickly the gate lets go again", "fitted to the file's Ku(t)"),
            ("vt", C["h"], "the input it needs to react",
             "how much of a pulse survives each hop", "fitted, then re-set by the run"),
            ("x_lin", C["x"], "where saturation ends",
             "the shape of the approach to the rail", "fitted (pinned 0.45 on most)"),
        ]
        for i, (sym, col, is_, dec, src) in enumerate(rows):
            y = 76 - i * 19
            b.plot([0.2, 1.1], [y + 2, y + 2], color=col, lw=5, solid_capstyle="butt")
            b.text(cols[0], y, sym, fontsize=14, family="monospace", fontweight="bold", color=col)
            b.text(cols[1], y, is_, fontsize=12.5, color="#222222")
            b.text(cols[2], y, dec, fontsize=12.5, color="#222222")
            b.text(cols[3], y, src, fontsize=12.5, color="#222222")
        save(fig, "four_numbers")


def ccomp_reject() -> None:
    """Why the file rejects its own declared C_comp: Ku cannot exceed 1."""
    import csv as _csv
    cc, ku = [], []
    with (ROOT / "results/ccomp_from_file_2026-09-22/ccomp_curves.csv").open(encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            if r["buffer"] == "ex2":
                cc.append(float(r["c_comp_pF"])); ku.append(float(r["max_ku"]))
    cc, ku = np.array(cc), np.array(ku)
    knee, decl, loop = 2.64, 5.0, 1.70
    with plt.rc_context(BODY):
        fig, a = plt.subplots(figsize=(10.8, 4.6))
        a.plot(cc, ku, color=SIL, lw=3.6, zorder=3)
        a.axhline(1.0, color="#B0563C", lw=2.2, ls="--", zorder=2)
        a.text(3.25, 1.004, "Ku = 1: the device conducting everything it has",
               fontsize=11.5, color="#B0563C", fontweight="bold", va="bottom")
        # annotations above their own points, staggered so none overlaps another or the curve
        for x, lab, col, off, ha in (
                (loop, f"loop-measured {loop} pF", REAL, (-14, 112), "right"),
                (knee, f"the knee {knee} pF", "#1F6F8B", (14, 44), "left"),
                (decl, f"declared in the file {decl} pF", "#B0563C", (-12, 26), "right")):
            y = float(np.interp(x, cc, ku))
            a.plot(x, y, "o", color=col, ms=11, zorder=5)
            a.annotate(f"{lab}\nsolve returns Ku = {y:.2f}", (x, y), textcoords="offset points",
                       xytext=off, ha=ha, fontsize=11.5, fontweight="bold", color=col,
                       arrowprops=dict(arrowstyle="->", color=col, lw=1.4))
        a.set_xlim(0, 5.7)
        a.set_ylim(0.985, 1.42)
        a.set_xlabel("C_comp assumed when solving the file (pF)")
        a.set_ylabel("peak Ku the solve returns")
        a.grid(alpha=0.3)
        a.set_title("ex2  |  the bigger the C_comp you assume, the more current the solve "
                    "credits to the device", fontsize=13.5, fontweight="bold")
        fig.tight_layout()
        save(fig, "ccomp_reject")


def pick_rank() -> None:
    """How the choice is made: the nine candidates ranked by waveform error."""
    t_si, si, _r = f17.transistor_pad("ex2", 810)
    t_si, w = t_si - 5.0, 0.810
    grid = np.arange(w - 0.1, w + 1.5, 0.004)
    ref = np.interp(grid, t_si, si)
    rows = []
    for (k, sh), d in CAND.items():
        t, _ku, pad = _cand(d, "d810")
        rms = 1e3 * float(np.sqrt(np.mean((np.interp(grid, t, pad) - ref) ** 2)))
        pk, _ = _peak_err(t, pad, t_si, si, w)
        rows.append((f"K{k}  {sh.replace('_', '/')}", rms, pk, (k, sh) == PICK))
    rows.sort(key=lambda r: r[1])
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(1, 2, figsize=(12.4, 4.6), sharey=True)
        y = np.arange(len(rows))[::-1]
        a = ax[0]
        a.barh(y, [r[1] for r in rows],
               color=[REAL if r[3] else "#AAB4B7" for r in rows], height=0.62)
        for yy, r in zip(y, rows):
            a.text(r[1] + 4, yy, f"{r[1]:.0f}", va="center", fontsize=11.5,
                   fontweight="bold", color=REAL if r[3] else "#555555")
        a.set_yticks(y, [r[0] for r in rows], fontsize=11.5)
        a.set_xlabel("error over the whole measured waveform (mV rms)")
        a.set_title("ranked on the waveform \u2014 what the recipe uses",
                    fontsize=13, fontweight="bold")
        a.set_xlim(0, max(r[1] for r in rows) * 1.18)
        a.grid(alpha=0.3, axis="x")
        a.annotate("the one it picks", (rows[0][1], y[0]), textcoords="offset points",
                   xytext=(70, 30), fontsize=12, fontweight="bold", color=REAL,
                   arrowprops=dict(arrowstyle="->", color=REAL, lw=1.5))

        b = ax[1]
        b.barh(y, [abs(r[2]) for r in rows],
               color=[REAL if r[3] else "#AAB4B7" for r in rows], height=0.62)
        for yy, r in zip(y, rows):
            b.text(abs(r[2]) + 0.12, yy, f"{r[2]:+.1f} %", va="center", fontsize=11.5,
                   color=REAL if r[3] else "#555555")
        b.set_xlabel("error at the peak only (%)")
        b.set_title("ranked on the peak \u2014 no order at all", fontsize=13, fontweight="bold")
        b.set_xlim(0, max(abs(r[2]) for r in rows) * 1.35)
        b.grid(alpha=0.3, axis="x")
        fig.suptitle("ex2  |  the same nine candidates, scored two ways",
                     fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        save(fig, "pick_rank")


if __name__ == "__main__":
    raise SystemExit(main())
