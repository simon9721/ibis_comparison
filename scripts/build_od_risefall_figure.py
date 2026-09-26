#!/usr/bin/env python3
"""Open-drain rise-then-fall figure (neutral: no annotations), drawn from the runs in
results/opendrain_risefall_2026-09-11 (input rests LOW, HIGH at 5 ns, LOW at 17 ns,
1 kOhm pull-up to VCC, 2 pF):

    transistor              HSPICE transistor bench
    native                  HSPICE native IBIS (ramp_rwf=2)
    gatestate_clamped_diag  our gate-state build with the I-V pwl() arguments clamped to
                            the table range (diagnostic; the converter's own build diverges
                            on this load, see the session notes of 2026-09-11)

The transistor Kd is solved from this bench (1 kOhm fixture, C_comp 3 pF) with the same
two-fixture identity used everywhere else, here with one fixture only. Where the
pull-down current at the pad voltage is small the quotient is ill-conditioned; the
figure masks |I_pd| below a threshold instead of drawing the blow-up.

    py -3.14 scripts/build_od_risefall_figure.py [--diag]
"""
from __future__ import annotations

import argparse
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
import build_od_slide_figures as bf  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import FixtureWaveform  # noqa: E402

O = ROOT / "results" / "opendrain_risefall_2026-09-11"
SUP, RPU, T_REL, T_PD = 3.3, 1000.0, 5.0, 17.0
PD_MIN = 1e-6   # A; below this the single-fixture Kd quotient is not meaningful


def transistor_kd(data, t_ns, pad, pd_min=PD_MIN):
    time = np.arange(t_ns[0], t_ns[-1], 0.005) * 1e-9
    v = np.interp(time * 1e9, t_ns, pad)
    wave = FixtureWaveform(np.column_stack([time, v, v, v]), [SUP] * 3, RPU)
    pu, pd, pc, gc, rf, cc, cf = pb.generating_current_data(data, time, 1, wave)
    num = gc + pc + rf - cc - cf
    ok = np.abs(pd) > pd_min
    kd = np.where(ok, num / np.where(ok, pd, 1.0), np.nan)
    return time * 1e9, kd, dict(pd=pd, num=num, gc=gc, pc=pc, rf=rf, cc=cc, cf=cf, v=v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diag", action="store_true", help="also write the Kd-solve diagnostic around the rise")
    ap.add_argument("--ccomp", default=None, help="use the runs made with this C_comp tag (e.g. 0p25) instead of the file's 5 pF")
    args = ap.parse_args()
    nat_dir = "native" if args.ccomp is None else f"native_ccomp{args.ccomp}"
    gs_dir = "gatestate_clamped_diag" if args.ccomp is None else f"gatestate_clamped_ccomp{args.ccomp}"
    tag = "" if args.ccomp is None else f"_ccomp{args.ccomp}"
    cc_txt = "C_comp as in the file (5 pF)" if args.ccomp is None else f"C_comp {args.ccomp.replace('p', '.')} pF (measured, NMOS off) in both IBIS models"

    raw = sl.parse_hspice_tr0(O / "transistor/run.tr0")
    t_si, si = sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float)
    raw = sl.parse_hspice_tr0(O / nat_dir / "run.tr0")
    t_n, nat, kd_n = sl.time_ns(raw), np.asarray(raw["v(pad)"], float), np.asarray(raw["v(kd)"], float)
    raw = sl.parse_ngspice_raw(O / gs_dir / "run.raw")
    t_o, our, kd_o = sl.time_ns(raw), sl.trace(raw, "out"), sl.signal(raw, "v(x1.kd)")
    data = bf.load_data(3.0)
    tk, kd_si, parts = transistor_kd(data, t_si, si)

    fig, ax = plt.subplots(2, 1, figsize=(15, 8.4), sharex=True)
    x0, x1 = 4.0, 21.0
    series = (
        (ax[0], [(t_si, si, bf.C_SI, 3.2, "-", "transistor (HSPICE)"),
                 (t_n, nat, bf.C_NAT, 1.7, "-", "native HSPICE IBIS"),
                 (t_o, our, bf.C_GS, 1.9, "--", "gate-state")], "pad (V)"),
        (ax[1], [(tk, kd_si, bf.C_SI, 3.2, "-", "transistor Kd"),
                 (t_n, kd_n, bf.C_NAT, 1.7, "-", "native Kd"),
                 (t_o, kd_o, bf.C_GS, 1.9, "--", "gate-state Kd")], "Kd (pull-down fraction on)"),
    )
    for a, ss, ylab in series:
        for t, y, col, lw, ls, lab in ss:
            m = (t > x0) & (t < x1)
            a.plot(t[m], y[m], color=col, lw=lw, ls=ls, label=lab)
        for e in (T_REL, T_PD):
            a.axvline(e, color="#888", ls="--", lw=1)
        a.grid(alpha=0.3)
        a.set_ylabel(ylab)
        a.legend(fontsize=8.5, loc="center right")
    ax[0].set_ylim(-0.2, 3.7)
    ax[1].set_ylim(-0.3, 1.45)
    ax[1].set_xlabel("time (ns)")
    ax[0].set_title("Open-drain ex2, full swing: input LOW at rest, HIGH at 5 ns, LOW at 17 ns; 1 kΩ pull-up to VCC, 2 pF. Dashed lines: input edges.\n" + cc_txt,
                    fontweight="bold", fontsize=11.5)
    fig.suptitle("Open-drain, rise then fall: pad and Kd, transistor vs native vs gate-state", fontsize=13, fontweight="bold")
    fig.tight_layout()
    for p in (O / f"od_risefall{tag}.png", bf.FIGS / f"od_risefall{tag}.png"):
        fig.savefig(p, dpi=160)
    plt.close(fig)
    print("wrote", O / f"od_risefall{tag}.png")

    if args.diag:
        m = (tk > 4.5) & (tk < 9.0)
        fig, ax = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
        ax[0].plot(tk[m], parts["v"][m], color=bf.C_SI)
        ax[0].set_ylabel("pad (V)")
        ax[1].plot(tk[m], parts["pd"][m] * 1e3, label="I_pd(V_pad) from the [Pulldown] table (denominator)")
        ax[1].plot(tk[m], parts["num"][m] * 1e3, label="numerator (fixture − clamps − C_comp)")
        ax[1].plot(tk[m], parts["rf"][m] * 1e3, label="fixture current (3.3 − V)/1 kΩ", ls=":")
        ax[1].plot(tk[m], -parts["cc"][m] * 1e3, label="−C_comp dV/dt", ls="--")
        ax[1].axhline(PD_MIN * 1e3, color="#888", lw=0.8)
        ax[1].axhline(-PD_MIN * 1e3, color="#888", lw=0.8)
        ax[1].set_ylabel("mA")
        ax[1].legend(fontsize=8)
        ax[2].plot(tk[m], kd_si[m], color=bf.C_SI)
        ax[2].set_ylim(-0.5, 1.5)
        ax[2].set_ylabel("Kd = num / I_pd")
        ax[2].set_xlabel("time (ns)")
        for a in ax:
            a.grid(alpha=0.3)
        fig.suptitle("Transistor Kd solve on the 1 kΩ bench, around the rise", fontweight="bold")
        fig.tight_layout()
        fig.savefig(O / "kd_solve_diag.png", dpi=150)
        print("wrote", O / "kd_solve_diag.png")
        # where does I_pd cross the threshold / zero?
        pd = parts["pd"]
        v = parts["v"]
        for tt in (5.0, 5.5, 5.8, 5.9, 6.0, 6.1, 6.2, 6.5, 7.0, 8.0):
            i = int(np.argmin(np.abs(tk - tt)))
            print(f"  t {tt:4.1f} ns  pad {v[i]:.3f} V  I_pd {pd[i]*1e3:+.4f} mA  num {parts['num'][i]*1e3:+.4f} mA  "
                  f"rf {parts['rf'][i]*1e3:+.4f}  -cc {-parts['cc'][i]*1e3:+.4f}  Kd {kd_si[i]:+.3f}")
        # table sample: I_pd vs V near 0
        vt = np.linspace(-0.2, 1.0, 13)
        wave = FixtureWaveform(np.column_stack([np.arange(13) * 1e-9, vt, vt, vt]), [SUP] * 3, RPU)
        _, pd_t, *_ = pb.generating_current_data(data, np.arange(13) * 1e-9, 1, wave)
        print("  [Pulldown] table I(V):", ", ".join(f"{a:.1f}V:{b*1e3:+.3f}mA" for a, b in zip(vt, pd_t)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
