#!/usr/bin/env python3
"""Animated walkthroughs of how track 1 and track 2 actually work, from real runs.

    fit_search.gif      the four stage numbers being searched until the chain lands on one
                        full-swing recording (the Nelder-Mead trial sequence, logged live)
    bisection.gif       the one stressed pad run placing the stage threshold, replayed from
                        the ten iteration directories the calibration actually wrote
    map_build.gif       two fixture runs becoming the Ku map: a cursor sweeps time, and each
                        instant drops a point onto the gate-versus-Ku plane

Everything drawn is measured or computed from runs already on disk; nothing is illustrated.

    py -3.14 scripts/build_method_animations.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402
import spicelab as sl  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import silicon_map_replay as smr  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402

OUT = ROOT / "results" / "method_animations_2026-09-17"
CH = ROOT / "results" / "gate_chain_prototype_2026-09-10"
CAL = CH / "ex2_c1.7/ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810/calib"
GATE, K, T_ON = "v(xdut.n4)", 3, 5.0 + 0.050 / 2
C_SI, C_M, C_DIM = "#111111", "#C05621", "#B9B3A9"
DPI, FPS = 100, 6


def save(anim, name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    anim.save(p, writer=PillowWriter(fps=FPS), dpi=DPI)
    print("  wrote " + str(p) + "  (%.2f MB)" % (p.stat().st_size / 1e6))


# --------------------------------------------------------------------------- 1
def fit_search():
    """Log every trial the search makes, then animate the best-so-far converging."""
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
    idx = np.unique(np.linspace(0, len(seq) - 1, min(45, len(seq))).astype(int))
    seq = [seq[i] for i in idx] + [seq[-1]] * 6
    print("    fit: %d trials, %d improving frames, final rms %.4f" % (len(trials), len(idx), seq[-1][0]))

    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    x = grid - 5
    ax.plot(x, v, color=C_SI, lw=3.4, label="measured gate node n4, full swing (the target)")
    ln = ax.plot([], [], color=C_M, lw=2.4, label="the four-number chain, this trial")[0]
    txt = ax.text(0.985, 0.06, "", transform=ax.transAxes, ha="right", fontsize=10.5,
                  family="monospace", bbox=dict(facecolor="white", edgecolor="#cccccc"))
    ax.set_xlim(-0.3, 4.0)
    ax.set_ylim(-0.08, 1.16)
    ax.grid(alpha=0.3)
    ax.set_xlabel("time from the input rising edge (ns)")
    ax.set_ylabel("gate node, 0 = rest, 1 = fully on")
    ax.legend(loc="lower right", fontsize=9.5)
    ax.set_title("Track 1, step 1: search the four numbers until the chain lands on one recording",
                 fontweight="bold", fontsize=11.5)

    def frame(i):
        r, prm, y = seq[i]
        ln.set_data(x, y)
        txt.set_text("s_up %5.2f   s_dn %5.2f\nvt   %5.2f   x_lin %5.2f\nrms  %.4f"
                     % (prm[0], prm[1], prm[2], prm[3], r))
        return ln, txt

    save(FuncAnimation(fig, frame, frames=len(seq), blit=False), "fit_search.gif")
    plt.close(fig)


# --------------------------------------------------------------------------- 2
def bisection():
    """Replay the ten iterations the threshold calibration actually wrote."""
    gp.VARIANT_NAME = "ex2"
    depth, w, case = [c for c in gp.cases("ex2") if c[0] == 810][0]
    t_si, si = gp.tr0_pad(case / "run.tr0")
    frames = []
    for d in sorted(CAL.glob("it*")):
        txt = (d / "driver.sub").read_text(encoding="utf-8")
        m = re.search(r"V\(CHIN\) - ([0-9.]+)", txt)
        raw = sl.parse_ngspice_raw(d / "run.raw")
        frames.append((float(m.group(1)), sl.time_ns(raw), sl.trace(raw, "out")))
    rev = 5.0 + w
    g = np.arange(rev - 0.7, rev + 2.6, 0.002)
    a = np.interp(g, t_si, si)
    tgt = float(a.max())
    print("    bisection: %d iterations, target peak %.4f V" % (len(frames), tgt))

    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    x = g - rev
    for _, tm, vm in frames:
        ax.plot(x, np.interp(g, tm, vm), color=C_DIM, lw=1.0, zorder=1)
    ax.plot(x, a, color=C_SI, lw=3.4, zorder=3,
            label="transistor, one 810 ps run: peak %.3f V" % tgt)
    ln = ax.plot([], [], color=C_M, lw=2.6, zorder=4, label="model at the threshold being tried")[0]
    txt = ax.text(0.985, 0.94, "", transform=ax.transAxes, ha="right", va="top", fontsize=10.5,
                  family="monospace", bbox=dict(facecolor="white", edgecolor="#cccccc"))
    ax.set_xlim(-0.7, 2.6)
    ax.set_ylim(-0.12, 1.55)
    ax.grid(alpha=0.3)
    ax.set_xlabel("time from the input reversal (ns)")
    ax.set_ylabel("pad (V)")
    ax.legend(loc="lower right", fontsize=9.5)
    ax.set_title("Track 1, step 2: one stressed run places the threshold, by bisection",
                 fontweight="bold", fontsize=11.5)
    order = list(range(len(frames))) + [len(frames) - 1] * 6

    def frame(i):
        vt, tm, vm = frames[order[i]]
        y = np.interp(g, tm, vm)
        ln.set_data(x, y)
        err = 100.0 * (y.max() - tgt) / tgt
        txt.set_text("iteration %2d\nthreshold %.3f\npeak error %+5.1f %%" % (order[i], vt, err))
        return ln, txt

    save(FuncAnimation(fig, frame, frames=len(order), blit=False), "bisection.gif")
    plt.close(fig)


# --------------------------------------------------------------------------- 3
def map_build():
    """Two fixture runs -> Ku(t) -> the same points replotted against the gate node."""
    sup, ibis = gp.VARIANTS["ex2"]
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    data.c_comp = [1.7e-12] * 3
    lo = smr.fixture(smr.FSFIX / "ex2/vfix_0/run.tr0")
    hi = smr.fixture(smr.FSFIX / "ex2/vfix_vcc/run.tr0")
    s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
    ts, ku = s[:, 0] * 1e9, s[:, 1]
    tg, gg = gr.real_gate("ex2", 0, GATE)
    gate = np.interp(ts, tg, gg)
    m = (ts >= 4.9) & (ts <= 7.6)
    ts, ku, gate = ts[m], ku[m], gate[m]
    step = max(1, len(ts) // 70)
    idx = list(range(0, len(ts), step)) + [len(ts) - 1] * 6
    print("    map: %d solved instants, %d frames" % (len(ts), len(idx)))

    fig, ax = plt.subplots(1, 3, figsize=(13.8, 4.2))
    ax[0].plot(np.asarray(lo[:, 0], float) * 1e9, lo[:, 1], color="#2B6CA3", lw=2.0,
               label="50 ohm to 0 V")
    ax[0].plot(np.asarray(hi[:, 0], float) * 1e9, hi[:, 1], color="#B03060", lw=2.0,
               label="50 ohm to VCC")
    ax[0].set_xlim(4.9, 7.6)
    ax[0].set_xlabel("time (ns)")
    ax[0].set_ylabel("pad (V)")
    ax[0].set_title("a. two fixture runs", fontweight="bold", fontsize=11)
    ax[0].legend(fontsize=9)
    ax[0].grid(alpha=0.3)

    ax[1].plot(ts, ku, color=C_DIM, lw=1.4)
    ax[1].set_xlim(4.9, 7.6)
    ax[1].set_ylim(-0.15, 1.15)
    ax[1].set_xlabel("time (ns)")
    ax[1].set_ylabel("Ku solved at this instant")
    ax[1].set_title("b. solve the two for Ku(t)", fontweight="bold", fontsize=11)
    ax[1].grid(alpha=0.3)

    ax[2].set_xlim(-0.05, 1.05)
    ax[2].set_ylim(-0.15, 1.15)
    ax[2].set_xlabel("gate node n4, 0 = rest, 1 = fully on")
    ax[2].set_ylabel("Ku")
    ax[2].set_title("c. plot Ku against the gate, and it is a map", fontweight="bold", fontsize=11)
    ax[2].grid(alpha=0.3)

    cur = [ax[0].axvline(ts[0], color=C_M, lw=1.6), ax[1].axvline(ts[0], color=C_M, lw=1.6)]
    dot = ax[1].plot([], [], "o", color=C_M, ms=7)[0]
    trail = ax[2].plot([], [], "-", color="#2B6CA3", lw=2.2)[0]
    head = ax[2].plot([], [], "o", color=C_M, ms=8)[0]
    fig.suptitle("Track 2: two extra full-swing runs turn into the Ku map",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()

    def frame(i):
        j = idx[i]
        for c in cur:
            c.set_xdata([ts[j], ts[j]])
        dot.set_data([ts[j]], [ku[j]])
        trail.set_data(gate[:j + 1], ku[:j + 1])
        head.set_data([gate[j]], [ku[j]])
        return (cur[0], cur[1], dot, trail, head)

    save(FuncAnimation(fig, frame, frames=len(idx), blit=False), "map_build.gif")
    plt.close(fig)


if __name__ == "__main__":
    print("building method animations")
    fit_search()
    bisection()
    map_build()
