#!/usr/bin/env python3
"""Figures for the two-tracks walkthrough page, all from existing runs (nothing re-simulated).

    trains_ex2.png / trains_inv_chain.png / trains_io_buf.png
        one buffer per figure: transistor vs the builds that matter for the story
    ex2_family_50.png
        the five ex2 variants at 50 % stress: transistor, track 1, track 2
    inv_widths.png
        inv_chain on the train: input, stage 4, stage 7 and pad, pulse 1 next to pulse 8

    py -3.14 scripts/build_two_tracks_figures.py
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
TR = R / "track2_train_check_2026-09-13"
CH = R / "gate_chain_prototype_2026-09-10"
FIGS = TR / "figs"
C_SI, C_T1, C_T2, C_T3 = "#111111", "#C05621", "#2E7D4F", "#2B6CA3"
W = {"ex2": 0.858, "inv_chain": 0.111, "io_buf": 1.792}


def ng(d):
    raw = sl.parse_ngspice_raw(d / "run.raw")
    return sl.time_ns(raw), sl.trace(raw, "out")


def hs(d, key="v(pad_sp)"):
    raw = sl.parse_hspice_tr0(d / "run.tr0")
    return sl.time_ns(raw), np.asarray(raw[key], float)


def train_fig(dev, builds, title):
    t_si, si = hs(TR / dev / "transistor_edge50")
    fig, a = plt.subplots(figsize=(15, 4.6))
    a.plot(t_si, si, color=C_SI, lw=3.0, label="transistor (HSPICE)")
    for sub, label, col, ls in builds:
        t, v = ng(TR / dev / sub)
        a.plot(t, v, color=col, lw=1.8, ls=ls, label=label)
    a.set_xlim(4.5, 5 + 16 * W[dev] + 2)
    a.grid(alpha=0.3)
    a.set_xlabel("time (ns)")
    a.set_ylabel("pad (V)")
    a.legend(fontsize=9, loc="upper right")
    a.set_title(title, fontweight="bold", fontsize=11.5)
    fig.tight_layout()
    fig.savefig(FIGS / f"trains_{dev}.png", dpi=150)
    plt.close(fig)


def ex2_family():
    variants = ["ex2_base", "ex2_weak", "ex2_nomiller", "ex2_skewp", "ex2_slowpre"]
    fig, axes = plt.subplots(1, 5, figsize=(20, 4.4), sharey=False)
    for a, v in zip(axes, variants):
        cs = gp.cases(v)
        depth, w, d_si = [c for c in cs if c[0] == 50][0]
        t_si, si = hs(d_si / "transistor", "v(pad)")
        base_dir = CH / f"{v}_c1.7"
        t1 = ng(base_dir / "ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad50" / "d50")
        t2 = ng(base_dir / "ibis_silicon_K3_xlin0.45_calibpad50" / "d50")
        rev = 5.0 + w
        for t, y, col, lw, ls, lab in ((t_si, si, C_SI, 3.0, "-", "transistor"), (t1[0], t1[1], C_T1, 1.7, "-", "track 1: file + one pad point"),
                                      (t2[0], t2[1], C_T2, 1.9, "--", "track 2: + measured valve curve")):
            m = (t > rev - 0.5) & (t < rev + 3.0)
            a.plot(t[m] - rev, y[m], color=col, lw=lw, ls=ls, label=lab)
        a.set_title(f"{v}, 50 % stress ({w*1e3:.0f} ps)", fontweight="bold")
        a.set_xlabel("time from the reversal (ns)")
        a.grid(alpha=0.3)
    axes[0].set_ylabel("pad (V)")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGS / "ex2_family_50.png", dpi=150)
    plt.close(fig)


def inv_widths():
    nodes = psp.STAGES["inv_chain"]
    d = TR / "inv_chain/transistor_edge50_probed"
    raw = psp.parse_tr0(d / "run.tr0")
    t = sl.time_ns(raw)
    sig = psp.signals(raw, nodes)
    full = psp.parse_tr0(psp.OUT / "inv_chain/full/run.tr0")
    tf = sl.time_ns(full)
    vf = psp.signals(full, nodes)
    show = [("v(in_dig)", "input"), ("v(xdut.vout4)", "runner 4"), ("v(xdut.vout7)", "runner 7 (the last one)"), ("v(pad_sp)", "output pin")]
    fig, axes = plt.subplots(len(show), 2, figsize=(13, 9), sharey="row")
    w = W["inv_chain"]
    for r, (nd, lab) in enumerate(show):
        g, rest, high = psp.normalise(tf, vf[nd], t, sig[nd])
        # each runner's own delay: its first 50 % crossing after the first input edge
        gd = np.arange(5.0, 5.0 + 1.0, 0.0005)
        yd = np.interp(gd, t, g)
        delay = float(gd[np.argmax(yd > 0.5)] - 5.0)
        windows = ((5.0 + delay - 0.08, 5.0 + delay + 2 * w + 0.02, "pulse 1"),
                   (5.0 + 14 * w + delay - 0.08, 5.0 + 14 * w + delay + 2 * w + 0.02, "pulse 8 (settled)"))
        for c, (lo, hi, wl) in enumerate(windows):
            a = axes[r, c]
            m = (t > lo) & (t < hi)
            a.plot(t[m] - lo - 0.08, g[m], color=C_SI, lw=2.4)
            a.axhline(0.5, color="#888", ls=":", lw=1)
            y = np.interp(np.arange(lo, hi, 0.0005), t, g)
            gg = np.arange(lo, hi, 0.0005)
            up = np.where((y[1:] > 0.5) & (y[:-1] <= 0.5))[0]
            dn = np.where((y[1:] <= 0.5) & (y[:-1] > 0.5))[0]
            if len(up) and len(dn[dn > up[0]]):
                r0, f0 = gg[up[0]], gg[dn[dn > up[0]][0]]
                a.axvspan(r0 - lo - 0.08, f0 - lo - 0.08, color="#2B6CA3", alpha=0.12)
                a.text(0.98, 0.85, f"{(f0 - r0) * 1e3:.0f} ps above 50 %", transform=a.transAxes, ha="right", fontsize=10)
            a.set_ylim(-0.15, 1.2)
            a.grid(alpha=0.3)
            if r == 0:
                a.set_title(wl, fontweight="bold")
            if c == 0:
                a.set_ylabel(lab + "\n0 = rest, 1 = full", fontsize=9)
            if r == len(show) - 1:
                a.set_xlabel("time from this runner's own start (ns)")
    fig.suptitle("inv_chain transistor on the train: the same runner, on the first pulse and on a settled pulse", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIGS / "inv_widths.png", dpi=150)
    plt.close(fig)


def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    train_fig("ex2", [("ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810", "track 1: file + one pad point", C_T1, "-"),
                      ("ibis_silicon_K3_xlin0.45_calibpad810", "track 2: + measured valve curve", C_T2, "--")],
              "ex2, eight 858 ps pulses back to back")
    train_fig("inv_chain", [("ibis_silicon_K7_calibpad104", "runners fitted from the IBIS file + one pad point", C_T1, "-"),
                            ("real_silicon_K7", "runners fitted to the real chip's last runner", C_T2, "--")],
              "inv_chain, eight 111 ps pulses back to back")
    train_fig("io_buf", [("real_prior_calibpad1505", "model remembering only the latest pulse", C_T1, "-"),
                         ("real_prior_calibpad1505_slots3", "model remembering the last three pulses", C_T2, "--")],
              "io_buf, eight 1792 ps pulses back to back")
    ex2_family()
    inv_widths()
    print("wrote", FIGS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
