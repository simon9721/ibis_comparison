#!/usr/bin/env python3
"""The command as the measured step response itself — for a linear predriver (io_buf).

io_buf's predriver is linear from input to pad (`predriver_stages_2026-09-09`):
under any pulse its gate is the superposition of its own two full-swing step
responses, P(t) = S_rise(t − t_on) + S_fall(t − t_off) − 1, to within 0.035.
A fitted stage cannot draw its decelerating ramp; the step response can.

Built into the model: a 3 ps delayed copy of the digital input marks each
edge; a latch samples the edge time; the elapsed time since the last rising
and the last falling edge index two pwl tables (the step responses); GUP is
their sum minus one, clipped. The same for GDN from the NMOS-gate path.
Exact for one pulse; on a train it keeps only the last edge of each direction
(right when each response settles within one period).

    --source real   step responses from the probed transistor gates (n2, n3)
    --source ibis   from the tables' Ku(t)/Kd(t) inverted through the prior

    py -3.14 scripts/gate_step_prototype.py --source real --maps prior --depth-residual
"""
from __future__ import annotations

import argparse
import csv
import re
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
from pybis2spice import pybis2spice as pb  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_cascade_prototype as gc  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import gate_chain_prototype as gch  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402

R = ROOT / "results"
OUT = R / "gate_step_prototype_2026-09-10"
DEADBAND = 0.005


def step_tables(t, g, t_on=5.0, t_off=15.0, span=9.0, dt=0.02):
    """S_rise(tau), S_fall(tau) on a uniform tau grid from the full-swing trace (0 = rest, 1 = on)."""
    tau = np.arange(0.0, span, dt)
    return tau, np.clip(np.interp(tau + t_on, t, g), 0, 1), np.clip(np.interp(tau + t_off, t, g), 0, 1)


def pwl_expr(var, tau, y):
    pts = ", ".join(f"{a:.4g}, {b:.5g}" for a, b in zip(tau, y))
    return f"pwl({var}, {pts})"


def step_block(name, tau, s_rise, s_fall, invert_out=False):
    """Two-stopwatch step-response command producing node <name> (GUP or GDN)."""
    pre = "SR" if name == "GUP" else "SD"
    lines = [f"* --- step-response command for {name}: elapsed time since the last rise / fall edge indexes the measured step responses ---"]
    lines.append(f"B{pre}TR {pre}TR 0 V = time * 1e9 - V({pre}LR) + 0.028")
    lines.append(f"B{pre}TF {pre}TF 0 V = time * 1e9 - V({pre}LF) + 0.028")
    lines.append(f"B{pre}RISE {pre}RISE 0 V = (V({pre}LR) > 0.5) ? {pwl_expr(f'V({pre}TR)', tau, s_rise)} : 0.0")
    lines.append(f"B{pre}FALL {pre}FALL 0 V = (V({pre}LF) > 0.5) ? {pwl_expr(f'V({pre}TF)', tau, s_fall)} : 1.0")
    g = f"min(max(V({pre}RISE) + V({pre}FALL) - 1.0, 0), 1)"
    lines.append(f"B{name} {name} 0 V = {'1.0 - ' if invert_out else ''}{g}")
    return "\n".join(lines)


def latch_block() -> str:
    """Edge detector and the two time latches (shared by GUP and GDN)."""
    return "\n".join([
        # a 30 ps edge window (T-line delay) and a 2 ps tracking constant: the latch
        # follows time*1e9 for the whole window, so it holds t_edge + 30 ps - 2 ps
        # (subtracted in the stopwatch below). A 3 ps window with a 0.2 ps constant
        # was under-resolved by the integrator and latched 1.3 ns short.
        "TCHD CHIN 0 CHD 0 Z0=50 Td=30p",
        "RCHD CHD 0 50",
        "BEDGER EDGER 0 V = (V(CHIN) > 0.5 && V(CHD) < 0.5) ? 1.0 : 0.0",
        "BEDGEF EDGEF 0 V = (V(CHIN) < 0.5 && V(CHD) > 0.5) ? 1.0 : 0.0",
        "BSRLR SRLR 0 I = -1e-12 * ((V(EDGER) > 0.5) ? (time * 1e9 - V(SRLR)) / 2p : 0)",
        "CSRLR SRLR 0 1e-12 ic=0",
        "RSRLR SRLR 0 1e15",
        "BSRLF SRLF 0 I = -1e-12 * ((V(EDGEF) > 0.5) ? (time * 1e9 - V(SRLF)) / 2p : 0)",
        "CSRLF SRLF 0 1e-12 ic=0",
        "RSRLF SRLF 0 1e15",
        "BSDLR SDLR 0 V = V(SRLR)",
        "BSDLF SDLF 0 V = V(SRLF)",
    ])


def patch_step(sub: str, sup: float, tau, gu_r, gu_f, gd_r, gd_f) -> str:
    chin = f"BCHIN CHIN 0 V = (V(IN,VSS) > {0.5 * sup:.4g}) ? 1.0 : 0.0\n"
    block = chin + latch_block() + "\n" + step_block("GUP", tau, gu_r, gu_f) + "\n" + step_block("GDN", tau, gd_r, gd_f, invert_out=True)
    s = re.sub(r"^BGUP GUP 0 I = .*$", block, sub, count=1, flags=re.M)
    for pat in (r"^CGUP GUP 0 .*\n", r"^RGUP GUP 0 .*\n", r"^BGDN GDN 0 I = .*\n", r"^CGDN GDN 0 .*\n", r"^BGDNBASE GDNBASE 0 .*\n", r"^RGDN GDN GDNBASE .*\n"):
        s = re.sub(pat, "", s, count=1, flags=re.M)
    # direction selectors: the step response's own slope (rise table still rising -> ON map)
    s = re.sub(r"^BGUPTARGET GUPTARGET 0 V = .*$", "BGUPTARGET GUPTARGET 0 V = (V(EDGER) > 0.5 || V(CHIN) > 0.5) ? 1.0 : 0.0", s, count=1, flags=re.M)
    s = re.sub(r"^BGDNTARGET GDNTARGET 0 V = .*$", "BGDNTARGET GDNTARGET 0 V = (V(CHIN) > 0.5) ? 0.0 : 1.0", s, count=1, flags=re.M)
    s = re.sub(r"^BKUGATE_BASE KUGATE_BASE 0 V = .*$",
               f"BKUGATE_BASE KUGATE_BASE 0 V = (V(GUPTARGET) >= V(GUP) - {DEADBAND}) ? V(KUGATE_ON) : V(KUGATE_OFF)", s, count=1, flags=re.M)
    s = re.sub(r"^BKDGATE_BASE KDGATE_BASE 0 V = .*$",
               f"BKDGATE_BASE KDGATE_BASE 0 V = (V(GDNTARGET) >= V(GDN) - {DEADBAND}) ? V(KDGATE_ON) : V(KDGATE_OFF)", s, count=1, flags=re.M)
    assert "BSRRISE" in s and "BGDN GDN 0 V" in s
    return s


def ibis_steps(full_ship, vt, al, which):
    tf = full_ship["t"]
    if which == "ku":
        kb = full_ship["kugate_base"]
        k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
        kn = np.clip((kb - k_rest) / (k_on - k_rest), 0, 1)
    else:
        kd = full_ship["kdgate_base"]
        d_on, d_off = float(np.interp(4.5, tf, kd)), float(np.interp(12.0, tf, kd))
        kn = np.clip((d_on - kd) / (d_on - d_off), 0, 1)
    return tf, pm.below_threshold(tf, pm.invert(kn, vt, al), kn, vt)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="io_buf")
    ap.add_argument("--source", choices=("real", "ibis"), default="real")
    ap.add_argument("--maps", choices=("prior", "silicon"), default="prior")
    ap.add_argument("--prior", type=float, nargs=2, default=(0.50, 0.78))
    ap.add_argument("--depth-residual", action="store_true")
    ap.add_argument("--calib-pad", type=int, default=None, metavar="DEPTH",
                    help="one stressed pad run: bisect a time-scale on the rise step response (faster/slower ramp) until the peak matches")
    args = ap.parse_args()
    dev = args.variant
    sup, ibis = gp.VARIANTS[dev]
    gp.VARIANT_NAME = dev
    mdir = gch.G / dev
    ship = (mdir / "shipped/driver.sub").read_text(encoding="utf-8")
    full_ship = gp.run_ours(mdir / "shipped/full", ship, sup, 10.0)
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    cs = gp.cases(dev)
    refs = {d_: gp.tr0_pad(d / "run.tr0") for d_, _, d in cs}
    vt, al = args.prior
    gch.PRIOR_FN = lambda g: pm.prior(g, vt, al)
    label = f"{args.source}_{args.maps}" + ("_dres" if args.depth_residual else "") + (f"_calibpad{args.calib_pad}" if args.calib_pad else "")
    tag = OUT / dev / label
    tag.mkdir(parents=True, exist_ok=True)

    if args.source == "real":
        tu, gu = gr.real_gate(dev, 0, gr.GATES[dev][0])
        td, gd = gr.real_gate(dev, 0, gr.GATES[dev][1])
    else:
        tu, gu = ibis_steps(full_ship, vt, al, "ku")
        td, gd = ibis_steps(full_ship, vt, al, "kd")
    tau, gu_r, gu_f = step_tables(tu, gu)
    _, gd_r, gd_f = step_tables(td, gd)
    print(f"\n  {dev}: step-response command, source={args.source}, maps={args.maps}; S_rise 10-90 {1e3*(tau[gu_r>0.9][0]-tau[gu_r>0.1][0]):.0f} ps, S_fall 10-90 {1e3*(tau[gu_f<0.1][0]-tau[gu_f<0.9][0]):.0f} ps")
    if args.maps == "prior":
        rise, fall, kd_on, kd_off = gch.prior_maps(full_ship, vt, al)
    else:
        rise, fall, kd_on, kd_off = gch.silicon_maps_for(dev, data, sup, None)

    def build(k_rise):
        # k_rise > 1: the rise step response is played faster (tau / k), i.e. the ramp is steeper
        gu_r_k = np.interp(tau * k_rise, tau, gu_r)
        t1 = patch_step(ship, sup, tau, gu_r_k, gu_f, gd_r, gd_f)
        t2 = gc.patch_kd_maps(gc.patch_maps(t1, rise, fall), kd_on, kd_off)
        if args.depth_residual:
            import residual_depth_rule as rd
            f0 = gp.run_ours(tag / f"full_noresidual_k{k_rise:.4f}", t2, sup, 10.0)
            plateau = float(np.interp(14.5, f0["t"], f0["pad"]))
            t2 = rd.patch(t2, rd.peak_hold_pad(plateau))
        return t2

    k_rise = 1.0
    if args.calib_pad:
        depth = args.calib_pad
        w = next(w_ for d_, w_, _ in cs if d_ == depth)

        def pad_err(k, i):
            r = gp.run_ours(tag / "calib" / f"it{i:02d}", build(k), sup, w)
            return gp.score(*refs[depth], r["t"], r["pad"], w)[0]

        e0 = pad_err(1.0, 0)
        lo, hi = 0.8, 1.3
        e_lo, e_hi = pad_err(lo, 1), pad_err(hi, 2)
        print(f"    pad calibration at d{depth}: peak error {e0:+.1f} % at k=1; k={lo} -> {e_lo:+.1f} %, k={hi} -> {e_hi:+.1f} %")
        it = 3
        for _ in range(7):
            mid = 0.5 * (lo + hi)
            if pad_err(mid, it) < 0:
                lo = mid          # too low: play the rise faster
            else:
                hi = mid
            it += 1
        k_rise = 0.5 * (lo + hi)
        print(f"    -> rise time-scale k = {k_rise:.4f}")
    text = build(k_rise)
    (tag / "driver_step.sub").write_text(text, encoding="utf-8")
    fs = gp.run_ours(tag / "full", text, sup, 10.0)
    fraw = psp.parse_tr0(psp.OUT / dev / "full/run.tr0")
    tfull, pfull = np.asarray(fraw["time"], float) * 1e9, np.asarray(fraw["v(pad_sp)"], float)
    g2 = np.arange(4.5, 20.0, 0.005)
    rms_full = float(np.sqrt(np.mean((np.interp(g2, fs["t"], fs["pad"]) - np.interp(g2, tfull, pfull)) ** 2)))
    tr_, gr_ = gr.real_gate(dev, 0, gr.GATES[dev][0])
    gw = (g2 > 4.9) & (g2 < 9.0)
    gate_rms = float(np.sqrt(np.mean((np.interp(g2[gw], fs["t"], fs["gup"]) - np.interp(g2[gw], tr_, gr_)) ** 2)))
    print(f"    full swing: pad rms vs transistor {rms_full*1e3:.1f} mV; model gate vs real gate rms {gate_rms:.3f}")
    print(f"    {'build':<18} | " + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs) + " | " + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs) + " |  gate max: model / real")
    rows = []
    fig, axes = plt.subplots(2, len(cs), figsize=(4.0 * len(cs), 7.0), sharex="col")
    for name, txt, d0 in (("shipped", ship, mdir / "shipped"), (label, text, tag)):
        pks, lags, gm = [], [], []
        for col, (depth, w, d) in enumerate(cs):
            r = gp.run_ours(d0 / f"d{depth}", txt, sup, w)
            pk, lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
            pks.append(pk)
            lags.append(lag)
            rev = gp.RISE_NS + w
            gg = np.arange(rev - 0.5, rev + 3.0, 0.002)
            tw, gw_ = gr.real_gate(dev, depth, gr.GATES[dev][0])
            gm.append((float(np.interp(gg, r["t"], r["gup"]).max()), float(np.interp(gg, tw, gw_).max())))
            a, b = axes[0][col], axes[1][col]
            if name == "shipped":
                a.plot(gg - rev, np.interp(gg, tw, gw_), color="#111111", lw=3.0, label="transistor gate")
                a.plot(gg - rev, np.interp(gg, r["t"], r["gup"]), color="#8A8A8A", lw=1.2, ls=":", label="shipped GUP")
                b.plot(gg - rev, np.interp(gg, *refs[depth]), color="#111111", lw=3.0, label="transistor pad")
                b.plot(gg - rev, np.interp(gg, r["t"], r["pad"]), color="#8A8A8A", lw=1.2, ls=":", label=f"shipped ({pk:+.0f}%)")
            else:
                a.plot(gg - rev, np.interp(gg, r["t"], r["gup"]), color="#B03060", lw=2.0, ls="--", label="step-response GUP")
                a.plot(gg - rev, np.interp(gg, r["t"], r["ku"]), color="#C05621", lw=1.2, label="Ku")
                b.plot(gg - rev, np.interp(gg, r["t"], r["pad"]), color="#2E8B57", lw=2.0, ls="--", label=f"step response ({pk:+.0f}%)")
                a.set_title(f"W = {depth} ps", fontweight="bold")
                a.set_ylim(-0.2, 1.2)
                a.grid(alpha=0.3)
                b.grid(alpha=0.3)
                b.set_xlabel("time from the reversal (ns)")
                if col == 0:
                    a.legend(fontsize=7)
                    b.legend(fontsize=7)
                    a.set_ylabel("gate / Ku")
                    b.set_ylabel("pad (V)")
        rows.append(dict(build=name, **{f"pk_d{dp}": round(x, 1) for (dp, _, _), x in zip(cs, pks)},
                         **{f"lag_d{dp}": round(x, 1) for (dp, _, _), x in zip(cs, lags)}))
        print(f"    {name:<18} | " + "".join(f"{x:>9.1f}" for x in pks) + " | " + "".join(f"{x:>9.0f}" for x in lags)
              + " |  " + " ".join(f"{m_[0]:.2f}/{m_[1]:.2f}" for m_ in gm))
    fig.suptitle(f"{dev}: command = the measured step responses replayed ({args.source}, {args.maps} maps)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(tag / "step.png", dpi=150)
    plt.close(fig)
    with (tag / "sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(rows[-1].keys()))
        wri.writeheader()
        wri.writerows(rows)
    print(f"  figure: {tag / 'step.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
