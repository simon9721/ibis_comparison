#!/usr/bin/env python3
"""Four small figures, all real simulation data, one per thing a model has to be able to do
(the bridge between the probed waveforms and the bucket model on the walkthrough page):

  req1_caught_midleg.png   ex2's last runner at 70 % stress vs the old model's knob (GUP)
  req2_rates_handoff.png   ex2 at full swing: each runner's slope, and where the next one starts
  req3_fair_share.png      ex2's last runner under a short pulse vs the sum of its own step responses
  req4_pad_is_fine.png     the old model with the real last runner played into it: pad follows

    py -3.14 scripts/build_requirement_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import spicelab as sl  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402

R = ROOT / "results"
OUT = R / "track2_train_check_2026-09-13" / "figs"
G = R / "gate_cascade_prototype_2026-09-09" / "ex2_c1.7"
C_SI, C_OLD, C_NEW, C_LIN = "#111111", "#8A8A8A", "#2E7D4F", "#2B6CA3"
W = 858


def load_ex2():
    nodes = psp.STAGES["ex2"]
    full = psp.parse_tr0(psp.OUT / "ex2/full/run.tr0")
    tf, vf = sl.time_ns(full), psp.signals(full, nodes)
    st = psp.parse_tr0(psp.OUT / f"ex2/w{W}/run.tr0")
    ts, vs = sl.time_ns(st), psp.signals(st, nodes)
    return nodes, tf, vf, ts, vs


def req1(nodes, tf, vf, ts, vs):
    g, rest, high = psp.normalise(tf, vf["v(xdut.n4)"], ts, vs["v(xdut.n4)"])
    raw = sl.parse_ngspice_raw(G / "shipped" / f"d{W}" / "run.raw")
    tm, gup = sl.time_ns(raw), sl.signal(raw, "v(x1.gup)")
    fig, a = plt.subplots(figsize=(9, 4.4))
    grid = np.arange(4.8, 8.5, 0.002)
    a.plot(grid - 5, np.interp(grid, ts, g), color=C_SI, lw=3.0, label="real last runner (ex2, n4), 70 % stress")
    a.plot(grid - 5, np.interp(grid, tm, gup), color=C_OLD, lw=2.0, ls=":", label="old model's knob (GUP): wait, then full move")
    a.axvline(W / 1e3, color="#8A8A8A", ls="--", lw=1)
    a.text(W / 1e3 + 0.05, 1.05, "go taken back", fontsize=9, color="#555")
    a.set_ylim(-0.1, 1.15)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("0 = rest, 1 = fully on")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="upper right")
    a.set_title("1. A runner can be caught mid-leg; a wait cannot", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "req1_caught_midleg.png", dpi=160)
    plt.close(fig)


def req2(nodes, tf, vf):
    fig, a = plt.subplots(figsize=(9, 4.4))
    grid = np.arange(4.8, 8.0, 0.002)
    cmap = plt.get_cmap("viridis")
    gs = {}
    for i, n in enumerate(nodes[1:4]):
        g, _, _ = psp.normalise(tf, vf[n], tf, vf[n])
        y = np.interp(grid, tf, g)
        gs[n] = y
        a.plot(grid - 5, y, color=cmap((i + 1) / 4), lw=2.2, label=n.replace("v(xdut.", "").rstrip(")"))
    # where does each runner start (10 % of its swing), and how full is the previous one then?
    for prev, cur in (("v(xdut.n2)", "v(xdut.n3)"), ("v(xdut.n3)", "v(xdut.n4)")):
        i0 = int(np.argmax(gs[cur] > 0.10))
        t0 = grid[i0] - 5
        lvl = gs[prev][i0]
        a.plot([t0, t0], [0, lvl], color="#B03060", lw=1, ls=":")
        a.plot(t0, lvl, "o", color="#B03060", ms=6)
        a.text(t0 + 0.03, lvl + 0.04, f"{cur[7:9]} starts when {prev[7:9]} is at {lvl:.2f}", fontsize=9, color="#B03060")
    # slope of n3 through its middle
    y = gs["v(xdut.n3)"]
    i1, i2 = int(np.argmax(y > 0.3)), int(np.argmax(y > 0.7))
    slope = 0.4 / (grid[i2] - grid[i1])
    a.annotate(f"n3 fills at {slope:.2f} of its swing per ns", xy=(grid[i2] - 5, 0.7), xytext=(grid[i2] - 5 + 0.5, 0.45), fontsize=9, color="#444",
               arrowprops=dict(arrowstyle="->", color="#444"))
    a.set_ylim(-0.1, 1.15)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("0 = rest, 1 = fully on")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="lower right")
    a.set_title("2. Each runner fills at its own rate, and starts when the previous one reaches a level", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "req2_rates_handoff.png", dpi=160)
    plt.close(fig)


def req3(nodes, tf, vf, ts, vs):
    n = "v(xdut.n4)"
    g_full, rest, high = psp.normalise(tf, vf[n], tf, vf[n])
    tau, gr, gf = psp.step_responses(tf, g_full)
    g, _, _ = psp.normalise(tf, vf[n], ts, vs[n])
    grid = np.arange(4.8, 8.5, 0.002)
    p1, p2 = psp.lti_predictions(grid, tau, gr, gf, W / 1e3)
    fig, a = plt.subplots(figsize=(9, 4.4))
    a.plot(grid - 5, np.interp(grid, ts, g), color=C_SI, lw=3.0, label="real last runner under the short pulse")
    a.plot(grid - 5, p2, color=C_LIN, lw=2.0, ls="--", label="its fair share: rise curve + fall curve, added up")
    a.axvline(W / 1e3, color="#8A8A8A", ls="--", lw=1)
    a.set_ylim(-0.1, 1.15)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("0 = rest, 1 = fully on")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="upper right")
    a.set_title("3. A short push gets less than its fair share, and returns sooner", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "req3_fair_share.png", dpi=160)
    plt.close(fig)


def req4():
    gp.VARIANT_NAME = "ex2"
    cs = gp.cases("ex2")
    d_si = [c for c in cs if c[0] == W][0][2]
    t_si, si = gp.tr0_pad(d_si / "run.tr0")
    rs = sl.parse_ngspice_raw(G / "shipped" / f"d{W}" / "run.raw")
    rr = sl.parse_ngspice_raw(G / "gate_replay" / f"d{W}" / "run.raw")
    fig, a = plt.subplots(figsize=(9, 4.4))
    rev = 5 + W / 1e3
    grid = np.arange(rev - 0.5, rev + 3.0, 0.002)
    a.plot(grid - rev, np.interp(grid, t_si, si), color=C_SI, lw=3.0, label="transistor pad")
    a.plot(grid - rev, np.interp(grid, sl.time_ns(rs), sl.trace(rs, "out")), color=C_OLD, lw=2.0, ls=":", label="old model, its own knob")
    a.plot(grid - rev, np.interp(grid, sl.time_ns(rr), sl.trace(rr, "out")), color=C_NEW, lw=2.2, ls="--", label="old model, real last runner played into its knob")
    a.set_xlabel("time from the reversal (ns)")
    a.set_ylabel("pad (V)")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="upper right")
    a.set_title("4. The output pin was never the problem: give it the real runner and it follows", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "req4_pad_is_fine.png", dpi=160)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    nodes, tf, vf, ts, vs = load_ex2()
    req1(nodes, tf, vf, ts, vs)
    req2(nodes, tf, vf)
    req3(nodes, tf, vf, ts, vs)
    req4()
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
