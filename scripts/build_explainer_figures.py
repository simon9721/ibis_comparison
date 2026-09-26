#!/usr/bin/env python3
"""Figures that show how the recipe is built and how each number is measured, for the
walkthrough page. All real simulation data; nothing here is a sketch.

    obs1_reach.png          the output gate node falls short as the pulse shortens; GUP does not
    obs2_rates.png          per-stage slope, and the level at which the next stage starts
    obs3_superposition.png  step-up response + step-down response - 1, against the measured node
    obs4_replay.png         what is played into GUP (the measured gate node), and the pad it gives
    stage_knobs.png         what each of the four stage numbers does under one short pulse
    stage_degeneracy.png    three thresholds that match at full swing and differ under stress
    track1_how.png          fitting the four stage numbers to the file's own Ku(t)
    calib_how.png           the one stressed pad run setting the stage threshold
    valve_measured.png      how the Ku map is measured: two fixtures -> Ku(t) -> Ku(gate)
    valve_effect.png        what the measured map changes on the stressed pad
    train_overlay_<dev>.png eight pulses overlaid: the first against a settled one

    py -3.14 scripts/build_explainer_figures.py
"""
from __future__ import annotations

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
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import gate_chain_prototype as gch  # noqa: E402
import silicon_map_replay as smr  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402
import pulse_train_accumulation as pt  # noqa: E402

R = ROOT / "results"
TR = R / "track2_train_check_2026-09-13"
CH = R / "gate_chain_prototype_2026-09-10"
GC = R / "gate_cascade_prototype_2026-09-09" / "ex2_c1.7"
OUT = TR / "figs"
C_SI, C_OLD, C_T1, C_T2, C_REAL = "#111111", "#8A8A8A", "#C05621", "#2E7D4F", "#2B5C8A"
GATE = "v(xdut.n4)"           # ex2: the gate node of the output transistors
EX2_FIT = dict(s_up=2.19028, s_dn=2.12377, vt_fit=0.528, x_lin=0.45, K=3)
EX2_PRIOR = (0.57, 0.64)      # the assumed Ku map: threshold, exponent
STRESS_PCT = {   # transistor pad excursion as a percent of its own full swing, measured 2026-09-17
    "ex2": {975: 91, 895: 81, 858: 71, 830: 60, 810: 50},
    "inv_chain": {135: 90, 119: 81, 111: 71, 106: 60, 104: 49},
    "io_buf": {2354: 80, 2090: 71, 1853: 60, 1666: 50, 1505: 37},
}


def stress_txt(dev, w_ps, fmt=" ({} % of full swing)"):
    pct = STRESS_PCT.get(dev, {}).get(int(round(w_ps)))
    return "" if pct is None else fmt.format(pct)


T_ON = 5.0 + 0.050 / 2        # the model's comparator switches at the middle of the 50 ps edge


def ng(p: Path, node="out"):
    raw = sl.parse_ngspice_raw(p / "run.raw")
    return sl.time_ns(raw), (sl.trace(raw, "out") if node == "out" else sl.signal(raw, node))


def ex2_probe(W=None):
    """(t, normalised gate node) for the full-swing run, or for a stressed width."""
    full = psp.parse_tr0(psp.OUT / "ex2/full/run.tr0")
    tf, vf = sl.time_ns(full), psp.signals(full, psp.STAGES["ex2"])
    if W is None:
        return tf, psp.normalise(tf, vf[GATE], tf, vf[GATE])[0], tf, vf
    raw = psp.parse_tr0(psp.OUT / f"ex2/w{W}/run.tr0")
    t, v = sl.time_ns(raw), psp.signals(raw, psp.STAGES["ex2"])
    return t, psp.normalise(tf, vf[GATE], t, v[GATE])[0], tf, vf


def obs1():
    fig, a = plt.subplots(figsize=(11, 4.6))
    grid = np.arange(4.8, 9.0, 0.002)
    for W, sh in ((975, 0.5), (810, 1.0)):
        t, g, _, _ = ex2_probe(W)
        y = np.interp(grid, t, g)
        a.plot(grid - 5, y, color=(0, 0, 0, sh), lw=3.0,
               label=f"gate node n4, {W} ps pulse: reaches {y.max():.2f}")
        tm, gup = ng(GC / "shipped" / f"d{W}", "v(x1.gup)")
        ym = np.interp(grid, tm, gup)
        a.plot(grid - 5, ym, color=C_OLD, lw=2.0, ls=":" if W == 975 else "--",
               label=f"shipped model GUP, {W} ps pulse: reaches {ym.max():.2f}")
    a.set_ylim(-0.1, 1.15)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("0 = rest, 1 = fully on")
    a.grid(alpha=0.3)
    a.legend(fontsize=8.5, loc="upper right")
    a.set_title("ex2 — observation 1: the gate node loses reach with the pulse width; GUP barely does",
                fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "obs1_reach.png", dpi=160)
    plt.close(fig)


def obs2():
    _, _, tf, vf = ex2_probe()
    grid = np.arange(4.8, 8.0, 0.002)
    cmap = plt.get_cmap("viridis")
    gs = {}
    fig, a = plt.subplots(figsize=(11, 4.6))
    for i, n in enumerate(psp.STAGES["ex2"][1:4]):
        g, _, _ = psp.normalise(tf, vf[n], tf, vf[n])
        y = np.interp(grid, tf, g)
        gs[n] = y
        a.plot(grid - 5, y, color=cmap((i + 1) / 4), lw=2.2, label=n.replace("v(xdut.", "").rstrip(")"))
    for prev, cur in (("v(xdut.n2)", "v(xdut.n3)"), ("v(xdut.n3)", "v(xdut.n4)")):
        i0 = int(np.argmax(gs[cur] > 0.10))
        t0, lvl = grid[i0] - 5, gs[prev][i0]
        a.plot([t0, t0], [0, lvl], color="#B03060", lw=1, ls=":")
        a.plot(t0, lvl, "o", color="#B03060", ms=6)
        a.text(t0 + 0.03, lvl + 0.04, f"{cur[7:9]} starts moving when {prev[7:9]} passes {lvl:.2f}",
               fontsize=9, color="#B03060")
    y = gs["v(xdut.n3)"]
    i1, i2 = int(np.argmax(y > 0.3)), int(np.argmax(y > 0.7))
    a.annotate(f"n3 charges at {0.4 / (grid[i2] - grid[i1]):.2f} of its swing per ns",
               xy=(grid[i2] - 5, 0.7), xytext=(grid[i2] - 5 + 0.5, 0.42), fontsize=9, color="#444",
               arrowprops=dict(arrowstyle="->", color="#444"))
    a.set_ylim(-0.1, 1.15)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("0 = rest, 1 = fully on")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="lower right")
    a.set_title("ex2 — observation 2: each stage has its own charge rate, and starts at a threshold",
                fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "obs2_rates.png", dpi=160)
    plt.close(fig)


def obs3(W=858):
    """The linear (superposition) prediction, drawn as the sum it actually is."""
    t, g, tf, vf = ex2_probe(W)
    g_full, _, _ = psp.normalise(tf, vf[GATE], tf, vf[GATE])
    tau, gr_, gf_ = psp.step_responses(tf, g_full)
    grid = np.arange(4.8, 9.0, 0.002)
    w = W / 1e3
    up = np.interp(grid - psp.RISE_NS, tau, gr_, left=0.0, right=gr_[-1])
    dn = np.interp(grid - psp.RISE_NS - w, tau, gf_, left=1.0, right=gf_[-1])
    lin = up + dn - 1.0
    meas = np.interp(grid, t, g)
    fig, a = plt.subplots(figsize=(12, 4.8))
    x = grid - 5
    a.plot(x, up, color="#2E8B57", lw=2.0, ls=":", label="A: the stage's step-up response, from the rising edge (0 → 1)")
    a.plot(x, dn, color="#5B2A86", lw=2.0, ls=":", label="B: the stage's step-down response, from the falling edge (1 → 0)")
    a.plot(x, lin, color="#2B6CA3", lw=2.4, ls="--", label="A + B − 1: what a linear stage would do")
    a.plot(x, meas, color=C_SI, lw=3.0, label=f"measured gate node n4, {W} ps pulse")
    a.axvline(w, color="#8A8A8A", ls="--", lw=1)
    il = int(np.argmin(abs(x - 2.55)))
    a.text(2.6, up[il] - 0.07, "A", color="#2E8B57", fontsize=13, fontweight="bold")
    a.text(2.6, dn[il] + 0.02, "B", color="#5B2A86", fontsize=13, fontweight="bold")
    xa = 1.75
    ia = int(np.argmin(abs(x - xa)))
    a.annotate("", xy=(xa, lin[ia]), xytext=(xa, meas[ia]), arrowprops=dict(arrowstyle="<->", color="#B03060", lw=1.6))
    a.text(xa + 0.07, 0.5 * (lin[ia] + meas[ia]) - 0.03, "the real stage delivers less\nand returns sooner",
           fontsize=9.5, color="#B03060")
    a.set_ylim(-0.15, 1.25)
    a.set_xlim(-0.3, 3.2)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("0 = rest, 1 = fully on")
    a.grid(alpha=0.3)
    a.legend(fontsize=8.5, loc="upper right")
    a.set_title("ex2 — observation 3: a linear stage would answer a pulse with A + B − 1. This one does not",
                fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "obs3_superposition.png", dpi=160)
    plt.close(fig)


def obs4(W=858):
    """What 'replaying the real gate' means: the measured n4, normalised, driven into GUP."""
    full = psp.parse_tr0(psp.OUT / "ex2/full/run.tr0")
    tf, vf = sl.time_ns(full), psp.signals(full, psp.STAGES["ex2"])
    raw = psp.parse_tr0(psp.OUT / f"ex2/w{W}/run.tr0")
    t, v = sl.time_ns(raw), psp.signals(raw, psp.STAGES["ex2"])
    g, rest, high = psp.normalise(tf, vf[GATE], t, v[GATE])
    fig, ax = plt.subplots(1, 3, figsize=(17.5, 4.5))
    grid = np.arange(4.6, 9.0, 0.002)
    a = ax[0]
    a.plot(grid - 5, np.interp(grid, t, v[GATE]), color=C_SI, lw=3.0)
    a.axhline(rest, color="#B03060", lw=1, ls=":")
    a.axhline(high, color="#B03060", lw=1, ls=":")
    a.text(-0.32, rest - 0.24, f"rest, {rest:.2f} V: pull-up off", fontsize=9.5, color="#B03060", bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
    a.text(-0.32, high + 0.10, f"fully on, {high:.2f} V", fontsize=9.5, color="#B03060", bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("n4 (V)")
    a.set_ylim(-0.15, 3.6)
    a.grid(alpha=0.3)
    a.set_title("a. ex2: the gate node n4 in volts, as measured.\nIt is an inverting node, so it falls to turn the pull-up on",
                fontweight="bold", fontsize=10.5)
    a = ax[1]
    a.plot(grid - 5, np.interp(grid, t, g), color=C_REAL, lw=3.0)
    a.axhline(0, color="#B03060", lw=1, ls=":")
    a.axhline(1, color="#B03060", lw=1, ls=":")
    a.text(-0.32, 0.05, "0 = pull-up off", fontsize=9.5, color="#B03060", bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
    a.text(-0.32, 1.03, "1 = fully on", fontsize=9.5, color="#B03060", bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("driven into GUP (0 … 1)")
    a.set_ylim(-0.12, 1.15)
    a.grid(alpha=0.3)
    a.set_title(f"b. the same trace rescaled: ({rest:.2f} V − n4) / {rest:.2f} V.\n"
                "Every other figure on this page plots nodes this way",
                fontweight="bold", fontsize=10.5)
    gp.VARIANT_NAME = "ex2"
    cs = gp.cases("ex2")
    d_si = [c for c in cs if c[0] == W][0][2]
    t_si, si = gp.tr0_pad(d_si / "run.tr0")
    rev = 5 + W / 1e3
    g2 = np.arange(rev - 0.6, rev + 2.6, 0.002)
    a = ax[2]
    a.plot(g2 - rev, np.interp(g2, t_si, si), color=C_SI, lw=3.0, label="transistor pad")
    ts, vs = ng(GC / "shipped" / f"d{W}")
    a.plot(g2 - rev, np.interp(g2, ts, vs), color=C_OLD, lw=2.0, ls=":", label="shipped model (its own GUP)")
    tr_, vr_ = ng(GC / "gate_replay" / f"d{W}")
    a.plot(g2 - rev, np.interp(g2, tr_, vr_), color=C_REAL, lw=2.2, ls="--", label="same model, GUP = the measured n4")
    a.set_xlabel("time from the reversal (ns)")
    a.set_ylabel("pad (V)")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="upper right")
    a.set_title("c. ex2: the pad that results when panel b is played\ninto GUP. The output stage was never the problem",
                fontweight="bold", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(OUT / "obs4_replay.png", dpi=160)
    plt.close(fig)


def chain_levels(vt, width_ns, K=3):
    grid = np.arange(4.0, 21.0, cl.DT)
    u = ((grid >= T_ON) & (grid < T_ON + width_ns)).astype(float)
    prm = (EX2_FIT["s_up"], EX2_FIT["s_dn"], vt, EX2_FIT["x_lin"], 1.0)
    out, x = [], u
    for _ in range(K):
        x = cl.simulate(x, *prm)
        out.append(x)
    return grid, u, out


def last_stage(prm, width_ns, K=3, grid=None):
    grid = np.arange(4.0, 21.0, cl.DT) if grid is None else grid
    u = ((grid >= T_ON) & (grid < T_ON + width_ns)).astype(float)
    x = u
    for _ in range(K):
        x = cl.simulate(x, prm[0], prm[1], prm[2], prm[3], 1.0)
    return grid, x


def stage_knobs(W_PS=858):
    """What each of the four numbers does to the last stage, under one short pulse."""
    base = [EX2_FIT["s_up"], EX2_FIT["s_dn"], EX2_FIT["vt_fit"], EX2_FIT["x_lin"]]
    sweeps = [(0, "s_up", "charge rate", [1.4, base[0], 3.4], "how fast a stage rises"),
              (1, "s_dn", "discharge rate", [1.3, base[1], 3.4], "how fast it falls back"),
              (2, "vt", "threshold", [0.25, base[2], 0.68], "the level the previous stage must pass"),
              (3, "x_lin", "resistive fraction", [0.12, base[3], 0.95], "where it stops being constant-current")]
    width = W_PS / 1e3
    fig, ax = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
    cols = ["#2B6CA3", "#111111", "#B03060"]
    for a, (idx, sym, name, vals, what) in zip(ax, sweeps):
        for val, c in zip(vals, cols):
            prm = list(base)
            prm[idx] = val
            grid, x = last_stage(prm, width)
            fitted = abs(val - base[idx]) < 1e-9
            a.plot(grid - 5, x, color=c, lw=2.8 if fitted else 2.0,
                   label=f"{sym} = {val:g}{' (fitted)' if fitted else ''},  peak {x.max():.2f}")
        a.axvspan(0.0, width, color="#000000", alpha=0.06)
        a.set_xlim(-0.2, 3.5)
        a.set_ylim(-0.05, 1.45)      # headroom so the legend never covers a peak
        a.grid(alpha=0.3)
        a.set_xlabel("time from the input rising edge (ns)")
        a.set_title(name + ",  " + sym + "\n" + what, fontweight="bold", fontsize=11)
        a.legend(fontsize=9, loc="upper right", framealpha=0.95)
    ax[0].set_ylabel("last stage output, 0 … 1")
    fig.suptitle(f"ex2: what each of the four numbers does under one {W_PS} ps input pulse{stress_txt('ex2', W_PS)}, shaded. "
                 "Three stages in the chain; only the last one is drawn", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "stage_knobs.png", dpi=160)
    plt.close(fig)


def fit_how():
    """What fitting means: trial stage numbers against the measured full-swing gate node."""
    t, g, _, _ = ex2_probe()
    grid = np.arange(4.0, 21.0, cl.DT)
    u = ((grid >= T_ON) & (grid < T_ON + 10.0)).astype(float)
    v = np.interp(grid, t, g)
    cost, prms = cl.fit_chain_shared(u, v, EX2_FIT["K"], p=1.0)
    b = prms[0]
    print(f"      fit to the measured ex2 gate node: rms {cost:.4f}  "
          f"s_up {b[0]:.2f} s_dn {b[1]:.2f} vt {b[2]:.2f} x_lin {b[3]:.2f}")
    trials = [(0.9, 0.9, 0.15, 0.20, "too slow"),
              (5.0, 5.0, 0.62, 0.85, "too fast"),
              # the fitted rise exactly, half the discharge rate: separable only on the falling edge
              (b[0], b[1] * 0.5, b[2], b[3], "the fitted rise, half the discharge rate")]
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.7), sharey=True)
    x = grid - 5
    for a in ax:
        a.plot(x, v, color=C_SI, lw=3.4, label="measured gate node n4 at full swing (the target)")
    for (s_up, s_dn, vt, x_lin, name), c in zip(trials, ["#8A8A8A", "#B03060", "#2B6CA3"]):
        y = cl.simulate_chain(u, [(s_up, s_dn, vt, x_lin, 1.0)] * EX2_FIT["K"])
        r = float(np.sqrt(np.mean((y - v) ** 2)))
        for a in ax:
            a.plot(x, y, color=c, lw=1.8, ls="--", label=f"trial, {name}:  rms {r:.3f}")
    yb = cl.simulate_chain(u, [tuple(b)] * EX2_FIT["K"])
    for a in ax:
        a.plot(x, yb, color=C_T1, lw=2.8,
               label=f"best fit:  rms {cost:.3f}   s_up {b[0]:.2f}, s_dn {b[1]:.2f}, vt {b[2]:.2f}, x_lin {b[3]:.2f}")
    ax[0].set_xlim(-0.3, 4.0)
    ax[1].set_xlim(9.7, 14.0)
    ax[0].set_ylim(-0.05, 1.18)
    ax[0].set_title("a. the rising edge", fontweight="bold", fontsize=11)
    ax[1].set_title("b. the falling edge, 10 ns later", fontweight="bold", fontsize=11)
    ax[0].set_ylabel("gate node, or last stage of the chain, 0 … 1")
    handles, labels = ax[0].get_legend_handles_labels()
    ax[0].legend(handles[:5], labels[:5], fontsize=8.8, loc="lower right", framealpha=0.95)
    for a in ax:
        a.grid(alpha=0.3)
        a.set_xlabel("time from the input rising edge (ns)")
    fig.suptitle("ex2: the fit varies the four numbers until the three-stage chain lands on one measured recording",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "fit_how.png", dpi=160)
    plt.close(fig)


def stage_degeneracy(W_PS=858):
    """Why the threshold cannot come from a full-swing recording: three thresholds, each with
    the other three numbers refitted, give back the same full-swing curve and very different
    short-pulse peaks."""
    gp.VARIANT_NAME = "ex2"
    base = [EX2_FIT["s_up"], EX2_FIT["s_dn"], EX2_FIT["vt_fit"], EX2_FIT["x_lin"]]
    K = EX2_FIT["K"]
    grid, v_full = last_stage(base, 10.0, K)
    width = W_PS / 1e3
    rows = []
    for vt in (0.25, EX2_FIT["vt_fit"], 0.68):
        rms, prm = gch.refit_with_vt(grid, v_full, K, vt, 1.0)
        p4 = list(prm[:4])
        _, f = last_stage(p4, 10.0, K)
        _, s = last_stage(p4, width, K)
        rows.append((vt, p4, rms, f, s))
        print(f"      vt {vt:.3f} -> s_up {p4[0]:.2f} s_dn {p4[1]:.2f} x_lin {p4[3]:.2f}"
              f"   full-swing rms {rms:.4f}   t50 {grid[int(np.argmax(f >= 0.5))] - 5:.3f} ns   {W_PS} ps peak {s.max():.3f}")
    peaks = [r[4].max() for r in rows]
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.7), sharey=True)
    cols = ["#2B6CA3", "#111111", "#B03060"]
    for (vt, p4, rms, f, s), c in zip(rows, cols):
        base_lab = f"vt = {vt:.2f}  with  s_up = {p4[0]:.2f}, s_dn = {p4[1]:.2f}, x_lin = {p4[3]:.2f}"
        ax[0].plot(grid - 5, f, color=c, lw=3.4 if c == cols[0] else 2.0,
                   label=base_lab + f"   (rms {rms:.3f})")
        ax[1].plot(grid - 5, s, color=c, lw=2.4, label=f"vt = {vt:.2f}   peak {s.max():.2f}")
    ax[0].set_title("a. a long input pulse: three thresholds, each with the other\n"
                    "three numbers refitted. The three are then nearly indistinguishable",
                    fontweight="bold", fontsize=11)
    ax[1].set_title(f"b. the same three settings under a {W_PS} ps pulse:\n"
                    f"the last stage peaks at {peaks[0]:.2f}, {peaks[1]:.2f} and {peaks[2]:.2f}",
                    fontweight="bold", fontsize=11)
    ax[1].axvspan(0.0, width, color="#000000", alpha=0.06)
    for a in ax:
        a.set_xlim(-0.2, 3.5)
        a.set_ylim(-0.05, 1.32)
        a.grid(alpha=0.3)
        a.set_xlabel("time from the input rising edge (ns)")
        a.legend(fontsize=8.5, loc="upper right", framealpha=0.95)
    ax[0].set_ylabel("last stage output, 0 … 1")
    fig.suptitle("ex2: why the threshold needs a stressed measurement of its own",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "stage_degeneracy.png", dpi=160)
    plt.close(fig)


def track1_how():
    raw = sl.parse_ngspice_raw(GC / "shipped/full/run.raw")
    tf = sl.time_ns(raw)
    kb = sl.signal(raw, "v(x1.kugate_base)")
    k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
    target = np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0)
    grid, u, levels = chain_levels(EX2_FIT["vt_fit"], 10.0)
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))
    a = ax[0]
    a.plot(tf - 5, target, color=C_SI, lw=3.0, label="Ku(t) at full swing, from the file's\nV-T tables (0 = off, 1 = fully on)")
    a.plot(grid - 5, pm.prior(levels[-1], *EX2_PRIOR), color=C_T1, lw=2.0, ls="--",
           label="the fitted stages, read through\nthe assumed Ku map")
    a.set_xlim(-0.3, 4.0)
    a.set_title("a. the four numbers are fitted to this", fontweight="bold", fontsize=11)
    a.set_ylabel("Ku, 0 … 1")
    a = ax[1]
    a.plot(grid - 5, u, color="#5B2A86", lw=2.4, label="comparator output (0 / 1)")
    for i, lv in enumerate(levels):
        a.plot(grid - 5, lv, lw=2.0, color=plt.get_cmap("viridis")((i + 1) / 4), label=f"stage {i + 1}")
    a.set_xlim(-0.3, 4.0)
    a.set_title("b. the stages that do it, at full swing", fontweight="bold", fontsize=11)
    a.set_ylabel("stage output, 0 … 1")
    grid2, u2, levels2 = chain_levels(EX2_FIT["vt_fit"], 0.858)
    a = ax[2]
    a.plot(grid2 - 5, u2, color="#5B2A86", lw=2.4, label="comparator output (0 / 1)")
    for i, lv in enumerate(levels2):
        a.plot(grid2 - 5, lv, lw=2.0, color=plt.get_cmap("viridis")((i + 1) / 4),
               label=f"stage {i + 1}: peak {lv.max():.2f}")
    a.axvline(0.858, color="#8A8A8A", ls="--", lw=1)
    a.set_xlim(-0.3, 4.0)
    a.set_title("c. same four numbers, 858 ps pulse (71 % of full swing), nothing refitted", fontweight="bold", fontsize=11)
    a.set_ylabel("stage output, 0 … 1")
    for a in ax:
        a.set_ylim(-0.1, 1.15)
        a.grid(alpha=0.3)
        a.set_xlabel("time from the input rising edge (ns)")
        a.legend(fontsize=8, loc="lower right")
    fig.suptitle("ex2: fitting the four stage numbers to the file's own Ku(t)", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "track1_how.png", dpi=160)
    plt.close(fig)


def calib_how():
    gp.VARIANT_NAME = "ex2"
    cs = gp.cases("ex2")
    d_si = [c for c in cs if c[0] == 810][0][2]
    t_si, si = gp.tr0_pad(d_si / "run.tr0")
    base = CH / "ex2_c1.7/ibis_silicon_K3_xlin0.45_calibpad810"
    rev = 5 + 0.810
    grid = np.arange(rev - 0.6, rev + 2.6, 0.002)
    ref = np.interp(grid, t_si, si)
    pk_ref = ref.max()
    fig, a = plt.subplots(figsize=(12, 4.8))
    a.plot(grid - rev, ref, color=C_SI, lw=3.2,
           label=f"the one stressed transistor run (810 ps): peak {pk_ref:.2f} V")
    for it, vt, col, ls in (("it01", 0.00, "#B03060", ":"), ("it02", 0.70, "#5B2A86", "-."), (None, 0.47, C_T2, "--")):
        p = (base / "d810") if it is None else (base / "calib" / it)
        t, v = ng(p)
        y = np.interp(grid, t, v)
        err = 100 * (y.max() - pk_ref) / pk_ref
        a.plot(grid - rev, y, color=col, lw=2.0, ls=ls,
               label=f"stage threshold {vt:.2f}: peak {y.max():.2f} V ({err:+.0f} %)")
        a.plot((grid - rev)[int(np.argmax(y))], y.max(), "o", color=col, ms=5)
    a.plot((grid - rev)[int(np.argmax(ref))], pk_ref, "o", color=C_SI, ms=6)
    a.set_xlabel("time from the reversal (ns)")
    a.set_ylabel("pad (V)")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="upper right")
    a.set_title("ex2, 810 ps pulse (50 % of full swing) — the calibration: vary the stage threshold until the model's pad peak matches this one run",
                fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "calib_how.png", dpi=160)
    plt.close(fig)


def valve_measured():
    """How the Ku map is measured: two fixture runs, a two-unknown solve, then Ku against the gate."""
    sup, ibis = gp.VARIANTS["ex2"]
    gp.VARIANT_NAME = "ex2"
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    data.c_comp = [1.7e-12] * 3
    lo = smr.fixture(smr.FSFIX / "ex2/vfix_0/run.tr0")
    hi = smr.fixture(smr.FSFIX / "ex2/vfix_vcc/run.tr0")
    s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
    ts, ku, kd = s[:, 0] * 1e9, s[:, 1], s[:, 2]
    tg, g = gr.real_gate("ex2", 0, GATE)
    maps = smr.silicon_maps(ts, ku, kd, tg, g, 5.0, 15.0, None)
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))
    a = ax[0]
    a.plot(lo[:, 0] * 1e9 - 5, lo[:, 1], color="#2B6CA3", lw=2.2, label="pad into 50 Ω to 0 V")
    a.plot(hi[:, 0] * 1e9 - 5, hi[:, 1], color="#B03060", lw=2.2, label="pad into 50 Ω to VCC")
    a.set_xlim(-0.3, 4.0)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("pad (V)")
    a.set_title("a. two full-swing runs of the transistor,\ninto two different loads", fontweight="bold", fontsize=11)
    a.legend(fontsize=9, loc="center right")
    a = ax[1]
    m = (ts > 4.7) & (ts < 9.0)
    a.plot(ts[m] - 5, ku[m], color=C_T2, lw=2.4, label="Ku(t), solved from the two runs")
    a.plot(tg - 5, g, color=C_SI, lw=2.2, ls="--", label="the gate node n4 at the same instants")
    a.set_xlim(-0.3, 4.0)
    a.set_ylim(-0.1, 1.3)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("0 … 1")
    a.set_title("b. at each instant the two loads give two\nequations: solve for Ku and Kd", fontweight="bold", fontsize=11)
    a.legend(fontsize=9, loc="lower right")
    a = ax[2]
    a.plot(maps[0][0], maps[0][1], color=C_T2, lw=2.6, label="measured: Ku plotted against n4")
    a.plot(maps[1][0], maps[1][1], color=C_T2, lw=1.4, ls=":", label="the same on the falling edge")
    gg = np.linspace(0, 1, 200)
    a.plot(gg, pm.prior(gg, *EX2_PRIOR), color=C_T1, lw=2.0, ls="--", label="assumed (track 1): threshold + power law")
    a.set_xlabel("gate node n4, normalised 0 … 1")
    a.set_ylabel("Ku")
    a.set_ylim(-0.15, 1.3)
    a.set_title("c. the Ku map: one curve, because Ku depends\non the gate alone", fontweight="bold", fontsize=11)
    a.legend(fontsize=8.5, loc="upper left")
    for a in ax:
        a.grid(alpha=0.3)
    fig.suptitle("ex2: how the Ku map is measured", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "valve_measured.png", dpi=160)
    plt.close(fig)


def valve_effect(W=858):
    gp.VARIANT_NAME = "ex2"
    cs = gp.cases("ex2")
    d_si = [c for c in cs if c[0] == W][0][2]
    t_si, si = gp.tr0_pad(d_si / "run.tr0")
    rev = 5 + W / 1e3
    grid = np.arange(rev - 0.6, rev + 2.6, 0.002)
    fig, a = plt.subplots(figsize=(11, 4.4))
    a.plot(grid - rev, np.interp(grid, t_si, si), color=C_SI, lw=3.2, label="transistor")
    for d, lab, col, ls in ((CH / "ex2_c1.7/ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810/d858", "track 1: assumed Ku map", C_T1, "-"),
                            (CH / "ex2_c1.7/ibis_silicon_K3_xlin0.45_calibpad810/d858", "track 2: measured Ku map", C_T2, "--")):
        t, v = ng(d)
        a.plot(grid - rev, np.interp(grid, t, v), color=col, lw=2.0, ls=ls, label=lab)
    a.set_xlabel("time from the reversal (ns)")
    a.set_ylabel("pad (V)")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="upper right")
    a.set_title("ex2, 858 ps pulse (71 % of full swing) — same stages, same threshold search, same pad equation: only the Ku map changed",
                fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "valve_effect.png", dpi=160)
    plt.close(fig)


TRAINS = {
    "ex2": [("ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810", "stages from the file + pad point", C_T1, "-"),
            ("ibis_silicon_K3_xlin0.45_calibpad810", "+ measured Ku map", C_T2, "--"),
            ("real_silicon_K3_calibpad810", "stages fitted to the measured gate node", C_REAL, "-.")],
    "inv_chain": [("ibis_silicon_K7_calibpad104", "stages from the file + pad point", C_T1, "-"),
                  ("real_silicon_K7_calibpad104", "stages fitted to the measured gate node", C_REAL, "-.")],
    "io_buf": [("real_prior_calibpad1505", "replay, most recent edge only", C_T1, "-"),
               ("real_prior_calibpad1505_slots3", "replay, last three pulses summed", C_T2, "--")],
}


def train_overlay(dev):
    _, sup, W = pt.DEV[dev]
    raw = sl.parse_hspice_tr0(TR / dev / "transistor_edge50/run.tr0")
    t_si, si = sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float)
    g0 = np.arange(5.0, 5.0 + 4 * W, 0.002)
    a0 = np.interp(g0, t_si, si)
    i0 = int(np.argmax(a0 > 0.3 * a0.max()))
    m0 = (g0 >= g0[i0]) & (g0 <= g0[i0] + 1.5 * W)
    d0 = max(0.0, float(g0[m0][int(np.argmax(a0[m0]))]) - 5.0 - W)
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.4), sharey=True)
    for col, (k, name) in enumerate(((0, "first pulse"), (7, "eighth pulse, settled"))):
        a = ax[col]
        lo = 5.0 + 2 * W * k + d0
        grid = np.arange(lo, lo + 2 * W, 0.002)
        ref = np.interp(grid, t_si, si)
        a.plot((grid - lo) * 1e3, ref, color=C_SI, lw=3.2, label=f"transistor (peak {ref.max():.2f} V)")
        for sub, lab, c, ls in TRAINS[dev]:
            t, v = ng(TR / dev / sub)
            y = np.interp(grid, t, v)
            a.plot((grid - lo) * 1e3, y, color=c, lw=2.0, ls=ls, label=f"{lab} ({y.max():.2f} V)")
        a.set_title(name, fontweight="bold")
        a.set_xlabel("time within the pulse (ps)")
        a.grid(alpha=0.3)
        a.legend(fontsize=8, loc="upper right")
    ax[0].set_ylabel("pad (V)")
    fig.suptitle(f"{dev}: eight {W * 1e3:.0f} ps pulses{stress_txt(dev, W * 1e3)} back to back, the first and the eighth on the same axes",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / f"train_overlay_{dev}.png", dpi=160)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    obs1()
    obs2()
    obs3()
    obs4()
    stage_knobs()
    fit_how()
    stage_degeneracy()
    track1_how()
    calib_how()
    valve_measured()
    valve_effect()
    for dev in TRAINS:
        train_overlay(dev)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
