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
    "inv_chain": ("inv_chain_c0.6", "v(xdut.vout7)", "vout7", [104, 106, 111, 119, 135], 1.45, 0.85),
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
            errs = [(NAT, f"native IBIS {e_nat:+.0f} %")]
            for build, col, lab in (("shipped", OURS, "our gate-state model"),
                                    ("gate_replay_silicon_full", REAL, "real gate + measured map")):
                t, _g, _k, pad = _run(dev, w_ps, build)
                e, _ = _peak_err(t, pad, t_si, si, w)
                a.plot(t, pad, color=col, lw=2.4, ls="--" if build == "shipped" else "-", label=lab)
                errs.append((col, f"{lab} {e:+.0f} %"))
            # the error labels sit under the curves: the overshoot is the point of the panel
            # and a legend box over it hides exactly what the slide is for
            for i, (col, txt) in enumerate(errs):
                a.text(0.04, 0.97 - 0.085 * i, txt, transform=a.transAxes, color=col,
                       fontsize=9.5, fontweight="bold", va="top")
            a.set_title(f"{DEPTH_PCT[w_ps]} % stress   ({w_ps} ps)", fontweight="bold", fontsize=12)
            a.set_xlim(w - 0.35, w + span)
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
            a.plot(xk, kk, color=SIL, lw=3.0, label="transistor Ku")
            b.plot(t_si, si, color=SIL, lw=3.4, label="transistor pad")
            for build, col, lab in (("shipped", OURS, "our GUP + IBIS map"),
                                    ("gate_replay_silicon_full", REAL, "real gate + measured map")):
                t, _g, ku, pad = _run(dev, w_ps, build)
                a.plot(t, ku, color=col, lw=2.2, ls="--" if build == "shipped" else "-", label=lab)
                e, _ = _peak_err(t, pad, t_si, si, w)
                b.plot(t, pad, color=col, lw=2.4, ls="--" if build == "shipped" else "-",
                       label=f"{lab}  {e:+.0f} %")
            a.set_title(f"{DEPTH_PCT[w_ps]} % stress", fontweight="bold")
            for c in (a, b):
                c.set_xlim(w - 0.35, w + span)
                c.grid(alpha=0.3)
                c.legend(loc="upper right", fontsize=9, framealpha=0.95)
            a.set_ylim(-0.35, 1.45)
            b.set_ylim(-0.12, ylim)
            b.set_xlabel("time (ns)")
        ax[0][0].set_ylabel("Ku")
        ax[1][0].set_ylabel("pad (V)")
        fig.suptitle(f"{dev}  |  the same map, two gates: the error is the gate's shape",
                     fontsize=15, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.93))
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
        for w_ps, c in zip(widths, cols):
            ts, greal = f17._norm_pair(dev, w_ps, node)[2:]
            a.plot(ts, greal, color=c, lw=2.3, zorder=2)
            i = int(np.nanargmax(greal))
            a.plot(ts[i], greal[i], "o", color=c, ms=10, zorder=5)
            # the peaks crowd together; the falling branches are well separated, so label there
            tail = np.asarray(greal)[i:]
            j = i + int(np.argmax(tail <= 0.34)) if np.any(tail <= 0.34) else len(greal) - 1
            a.annotate(f"{DEPTH_PCT[w_ps]} %", (ts[j], greal[j]), textcoords="offset points",
                       xytext=(4, 4), color=c, fontsize=12, fontweight="bold")
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


if __name__ == "__main__":
    raise SystemExit(main())
