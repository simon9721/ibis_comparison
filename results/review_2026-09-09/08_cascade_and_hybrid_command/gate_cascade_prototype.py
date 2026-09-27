#!/usr/bin/env python3
"""Prototype v2: the command delay as an analog RC cascade, not a transmission line.

`gate_ramp_prototype.py` slowed the gate ramp and re-derived the map so full
swing was preserved. Result: the fall entered partway (dual map, k >= 4) and
timing improved -- inv_base8 lag 67 -> 55 ps, ex2 124 -> 17 ps at 90 % -- but the
stressed **peak** barely moved on ex2 (70.9 -> 66.9 %). The traces say why: our
pad is already 46 % above the transistor's at +600 ps, *before* our off-command
arrives at rev + pu_off. The transistor's rise bends the moment the input
reverses, because its predriver is a chain of analog stages; ours cannot, because
the command is a T-line delay that blocks the reversal until pu_off.

So v2 replaces the pull-up command path

    TPUCMDA/TPUCMDB (T-lines, Td = pu_on / pu_off)  ->  AND  ->  GUPTARGET (0/1)

with an N-stage RC cascade driven by the input:

    NINX -> P1 -> P2 -> ... -> PN = GUPTARGET   (continuous, 0..1)

each stage first-order with tau_up on the way up and tau_dn on the way down,
calibrated so the cascade's 50 % crossings land at pu_on and pu_off exactly as
before (for N identical stages the step response is Erlang-N; the 50 % point is
at x_N tau, x_1 = 0.693, x_2 = 1.678, x_3 = 2.674, x_4 = 3.672). The gate RC and
the map follow as shipped, but the maps are re-derived from the new full-swing
GUP(t) against the shipped gate-part Ku(t), so **full swing is preserved by
construction**. Under truncation the reversal now bleeds through the cascade
immediately and the gate never reaches 1.

Pull-down path left as shipped (short-high only; the pull-down is off during
the event).

    py -3.14 scripts/gate_cascade_prototype.py --variant ex2_base --stages 1 2 3 4
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402

R = ROOT / "results"
X50 = {1: 0.6931, 2: 1.6783, 3: 2.6741, 4: 3.6721, 5: 4.6709, 6: 5.6700}


def delays(sub: str) -> tuple[float, float]:
    on = float(re.search(r"^TPUCMDA .*?Td=([0-9.e+-]+)n", sub, re.M).group(1))
    off = float(re.search(r"^TPUCMDB .*?Td=([0-9.e+-]+)n", sub, re.M).group(1))
    return on, off


def pd_delays(sub: str) -> tuple[float, float]:
    """(pd_off after the input rise, pd_on after the input fall)."""
    off = float(re.search(r"^TPDCMDA .*?Td=([0-9.e+-]+)n", sub, re.M).group(1))
    on = float(re.search(r"^TPDCMDB .*?Td=([0-9.e+-]+)n", sub, re.M).group(1))
    return off, on


def pd_cascade_block(n: int, tau_up: float, tau_dn: float) -> str:
    """Input rising -> Q rises with tau_up (pull-down turns OFF after pd_off);
    input falling -> Q falls with tau_dn (pull-down turns ON after pd_on).
    PDCMDLVL = 1 - Q_N, so GDNCMD = Q_N, continuous."""
    lines = []
    src = "NINX"
    for i in range(1, n + 1):
        node = f"PDN{i}"
        lines.append(f"BPDN{i} {node} 0 I = -{{gate_c}} * (V({src}) - V({node})) / "
                     f"((V({src}) > V({node})) ? {tau_up:.12g}n : {tau_dn:.12g}n)")
        lines.append(f"CPDN{i} {node} 0 {{gate_c}} ic=0")
        lines.append(f"RPDN{i} {node} 0 1e12")
        src = node
    lines.append(f"BPDCMDLVL PDCMDLVL 0 V = 1.0 - min(max(V({src}), 0), 1)")
    return "\n".join(lines) + "\n"


def patch_pd_cascade(sub: str, n: int) -> str:
    off, on = pd_delays(sub)
    tau_up, tau_dn = off / X50[n], on / X50[n]
    s = re.sub(r"^TPDCMDA .*\n^RPDCMDA .*\n^TPDCMDB .*\n^RPDCMDB .*\n^BPDCMDLVL .*\n",
               pd_cascade_block(n, tau_up, tau_dn), sub, count=1, flags=re.M)
    if "BPDN1" not in s:
        raise RuntimeError("pull-down command block not found")
    return s


def cascade_block(n: int, tau_up: float, tau_dn: float) -> str:
    lines = []
    src = "NINX"
    for i in range(1, n + 1):
        node = f"PUP{i}"
        lines.append(f"BPUP{i} {node} 0 I = -{{gate_c}} * (V({src}) - V({node})) / "
                     f"((V({src}) > V({node})) ? {tau_up:.12g}n : {tau_dn:.12g}n)")
        lines.append(f"CPUP{i} {node} 0 {{gate_c}} ic=0")
        lines.append(f"RPUP{i} {node} 0 1e12")
        src = node
    lines.append(f"BPUCMDLVL PUCMDLVL 0 V = min(max(V({src}), 0), 1)")
    return "\n".join(lines) + "\n"


def patch_cascade(sub: str, n: int) -> str:
    on, off = delays(sub)
    tau_up, tau_dn = on / X50[n], off / X50[n]
    # drop the two T-lines, their terminations and the AND
    s = re.sub(r"^TPUCMDA .*\n^RPUCMDA .*\n^TPUCMDB .*\n^RPUCMDB .*\n^BPUCMDLVL .*\n",
               cascade_block(n, tau_up, tau_dn), sub, count=1, flags=re.M)
    if "BPUP1" not in s:
        raise RuntimeError("pull-up command block not found")
    return s


def patch_hybrid(sub: str, tau_ns: float) -> str:
    """Delay line kept, one analog stage after it.

    For a regenerative inverter chain (inv_chain) the command really is a delay:
    a 100 ps pulse propagates intact, which a pure RC cascade cannot do. What is
    analog there is only the last stage. So: keep TPUCMDA/TPUCMDB and the AND,
    shorten both delays by 0.693*tau so the 50 % points stay put, and feed the
    AND's output through one RC of time constant tau. A pulse shorter than a few
    tau is truncated by that stage alone.
    """
    shift = 0.6931 * tau_ns

    def shorten(m):
        return f"{m.group(1)}{max(float(m.group(2)) - shift, 0.001):.12g}n"
    s = re.sub(r"^(TPUCMDA .*?Td=)([0-9.e+-]+)n", shorten, sub, count=1, flags=re.M)
    s = re.sub(r"^(TPUCMDB .*?Td=)([0-9.e+-]+)n", shorten, s, count=1, flags=re.M)
    s = re.sub(r"^BPUCMDLVL PUCMDLVL 0 V = (.*)$",
               lambda m: ("BPUCMDRAW PUCMDRAW 0 V = " + m.group(1) + "\n"
                          f"BPUCMDLVL PUCMDLVL 0 I = -{{gate_c}} * (V(PUCMDRAW) - V(PUCMDLVL)) / {tau_ns:.12g}n\n"
                          "CPUCMDLVL PUCMDLVL 0 {gate_c} ic=0\nRPUCMDLVL PUCMDLVL 0 1e12"),
               s, count=1, flags=re.M)
    if "BPUCMDRAW" not in s:
        raise RuntimeError("pull-up command AND not found")
    return s


def patch_slew(sub: str, swing_ps: float) -> str:
    """Delay line kept, one SLEW-LIMITED stage after it.

    inv_chain's last predriver stage is a linear ramp, not an RC: on the matrix
    transistor runs its slope at 25 % of the swing equals its slope at 75 %
    (ratio 0.91-1.04; an RC gives ~3), a straight line fits to 0.01-0.02 V where
    an exponential misses by 0.13-0.15, and the peak dV/dt is ~32 V/ns at every
    width -- a full 1.8 V swing in ~56 ps. So the stage integrates at a fixed
    rate: I = c * clamp((target - x) / tau_small, -SR, +SR) with SR = 1/swing.
    A linear ramp crosses 50 % at swing/2, so both T-line delays are shortened
    by that to hold the full-swing 50 % points.
    """
    swing = swing_ps / 1e3
    sr = 1.0 / swing            # per ns, for a 0..1 node
    shift = 0.5 * swing

    def shorten(m):
        return f"{m.group(1)}{max(float(m.group(2)) - shift, 0.001):.12g}n"
    s = re.sub(r"^(TPUCMDA .*?Td=)([0-9.e+-]+)n", shorten, sub, count=1, flags=re.M)
    s = re.sub(r"^(TPUCMDB .*?Td=)([0-9.e+-]+)n", shorten, s, count=1, flags=re.M)
    s = re.sub(r"^BPUCMDLVL PUCMDLVL 0 V = (.*)$",
               lambda m: ("BPUCMDRAW PUCMDRAW 0 V = " + m.group(1) + "\n"
                          f"BPUCMDLVL PUCMDLVL 0 I = -{{gate_c}} * max(min((V(PUCMDRAW) - V(PUCMDLVL)) / 0.002n, {sr:.6g}e9), -{sr:.6g}e9)\n"
                          "CPUCMDLVL PUCMDLVL 0 {gate_c} ic=0\nRPUCMDLVL PUCMDLVL 0 1e12"),
               s, count=1, flags=re.M)
    if "BPUCMDRAW" not in s:
        raise RuntimeError("pull-up command AND not found")
    return s


def derive_maps(full_new: dict, full_ship: dict, gate: str = "gup", base: str = "kugate_base"):
    """Rise and fall maps: shipped gate-part K(t) against the NEW gate(t).

    Resampled onto a uniform 200-point grid in g, which keeps the pwl abscissa
    strictly monotonic and the netlist line short. For the pull-down, `gate` is
    GDN and its "rise" is the pull-down turning on (input falling edge).
    """
    t, gup = full_new["t"], full_new[gate]
    gb = np.interp(t, full_ship["t"], full_ship[base])
    ipk = int(np.argmax(gup))
    grid = np.linspace(0.0, 1.0, 200)

    def branch(mask):
        x, y = gup[mask], gb[mask]
        o = np.argsort(x)
        x, y = x[o], y[o]
        ux, idx = np.unique(np.round(x, 5), return_inverse=True)
        uy = np.bincount(idx, y) / np.bincount(idx)
        return grid, np.interp(grid, ux, uy)

    rise = branch((t >= gp.RISE_NS - 0.05) & (t <= t[ipk]))
    fall = branch(t >= t[ipk])
    return rise, fall


def patch_maps(sub: str, rise, fall) -> str:
    s = re.sub(r"^BKUGATE_ON KUGATE_ON 0 V = .*$", gp.as_pwl("BKUGATE_ON KUGATE_ON 0 V =", *rise), sub, count=1, flags=re.M)
    s = re.sub(r"^BKUGATE_OFF KUGATE_OFF 0 V = .*$", gp.as_pwl("BKUGATE_OFF KUGATE_OFF 0 V =", *fall), s, count=1, flags=re.M)
    return s


def as_pwl_gdn(prefix: str, xs, ys) -> str:
    pairs = ", ".join(f"{x:.6g}, {y:.6g}" for x, y in zip(xs, ys))
    return f"{prefix} pwl(min(max(V(GDN), 0), 1), {pairs})"


def patch_kd_maps(sub: str, rise, fall) -> str:
    s = re.sub(r"^BKDGATE_ON KDGATE_ON 0 V = .*$", as_pwl_gdn("BKDGATE_ON KDGATE_ON 0 V =", *rise), sub, count=1, flags=re.M)
    s = re.sub(r"^BKDGATE_OFF KDGATE_OFF 0 V = .*$", as_pwl_gdn("BKDGATE_OFF KDGATE_OFF 0 V =", *fall), s, count=1, flags=re.M)
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="ex2_base")
    ap.add_argument("--stages", type=int, nargs="*", default=[1, 2, 3, 4])
    ap.add_argument("--pd", action="store_true", help="also cascade the pull-down command and re-derive the Kd maps")
    ap.add_argument("--hybrid", type=float, nargs="*", default=[],
                    help="delay line kept + one analog stage after it; values are its tau in ps")
    ap.add_argument("--slew", type=float, nargs="*", default=[],
                    help="delay line kept + one slew-limited stage; values are the full-swing time in ps")
    ap.add_argument("--ccomp", type=float, default=None,
                    help="rewrite the IBIS C_comp (pF) before building, e.g. 1.7 on ex2")
    args = ap.parse_args()
    sup, ibis = gp.VARIANTS[args.variant]
    gp.VARIANT_NAME = args.variant
    OUT = R / "gate_cascade_prototype_2026-09-09" / (args.variant + ("_pd" if args.pd else "") + (f"_c{args.ccomp:g}" if args.ccomp else ""))
    if args.ccomp:
        OUT.mkdir(parents=True, exist_ok=True)
        txt = re.sub(r"^C_comp\s+.*$", f"C_comp {args.ccomp:.4f}pF {args.ccomp:.4f}pF {args.ccomp:.4f}pF",
                     ibis.read_text(errors="ignore"), count=1, flags=re.M)
        ibis = OUT / "input_ccomp.ibs"
        ibis.write_text(txt, encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    ship_dir = OUT / "shipped"
    ship_dir.mkdir(parents=True, exist_ok=True)
    if not (ship_dir / "driver.sub").exists():
        subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(ship_dir / "driver.sub"))
    ship = (ship_dir / "driver.sub").read_text(encoding="utf-8")
    on, off = delays(ship)
    print(f"  {args.variant}: pu_on {on*1e3:.0f} ps, pu_off {off*1e3:.0f} ps")

    full_ship = gp.run_ours(ship_dir / "full", ship, sup, 10.0)
    cs = gp.cases(args.variant)
    refs = {d_: gp.tr0_pad(d / "run.tr0" if args.variant in gp.MATRIX_SET else d / "transistor/run.tr0") for d_, _, d in cs}
    nats = {d_: gp.native_pad(args.variant, d_, d) for d_, _, d in cs}

    rows = []
    print(f"\n    {'build':<10}{'FS Ku rms':>10} | " + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs)
          + " | " + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs))
    for name, text in (("shipped", ship), ("native", None)):
        pks, lags = [], []
        for depth, w, d in cs:
            if text is None:
                pk, lag, _, _ = gp.score(*refs[depth], *nats[depth], w)
            else:
                r = gp.run_ours(ship_dir / f"d{depth}", ship, sup, w)
                pk, lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
            pks.append(pk)
            lags.append(lag)
        rows.append(dict(build=name, fs_ku_rms=0.0, **{f"pk_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, pks)},
                         **{f"lag_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, lags)}))
        print(f"    {name:<10}{'-':>10} | " + "".join(f"{v:>9.1f}" for v in pks) + " | " + "".join(f"{v:>9.0f}" for v in lags))

    builds = [(f"cascade{n}", n, None) for n in args.stages] + \
             [(f"hybrid{tau:g}ps", None, tau / 1e3) for tau in args.hybrid] + \
             [(f"slew{sw:g}ps", None, -sw) for sw in args.slew]      # negative = slew swing in ps
    for label, n, tau in builds:
        if tau is not None and tau < 0:
            text1 = patch_slew(ship, -tau)
        elif tau is not None:
            text1 = patch_hybrid(ship, tau)
        else:
            text1 = patch_cascade(ship, n)
            if args.pd:
                text1 = patch_pd_cascade(text1, n)
        tag = OUT / label
        # pass 1: new GUP(t) (and GDN(t)) at full swing (maps do not affect the gates)
        full_new = gp.run_ours(tag / "full_pass1", text1, sup, 10.0)
        rise, fall = derive_maps(full_new, full_ship)
        text2 = patch_maps(text1, rise, fall)
        if args.pd:
            # GDN's "rise" is the pull-down turning on: derive over the falling-input
            # half by using the GDN maximum as the split, exactly as for GUP.
            kd_rise, kd_fall = derive_maps(full_new, full_ship, gate="gdn", base="kdgate_base")
            text2 = patch_kd_maps(text2, kd_rise, kd_fall)
        (tag / "driver_cascade.sub").parent.mkdir(parents=True, exist_ok=True)
        (tag / "driver_cascade.sub").write_text(text2, encoding="utf-8")
        fs = gp.run_ours(tag / "full", text2, sup, 10.0)
        tf = full_ship["t"]
        m = (tf > gp.RISE_NS - 0.5) & (tf < 17.0)
        ku_rms = float(np.sqrt(np.mean((np.interp(tf[m], fs["t"], fs["ku"]) - full_ship["ku"][m]) ** 2)))
        pks, lags = [], []
        for depth, w, d in cs:
            r = gp.run_ours(tag / f"d{depth}", text2, sup, w)
            pk, lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
            pks.append(pk)
            lags.append(lag)
        rows.append(dict(build=label, fs_ku_rms=round(ku_rms, 4),
                         **{f"pk_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, pks)},
                         **{f"lag_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, lags)}))
        print(f"    {label:<10}{ku_rms:>10.4f} | " + "".join(f"{v:>9.1f}" for v in pks)
              + " | " + "".join(f"{v:>9.0f}" for v in lags))

    with (OUT / "sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wri.writeheader()
        wri.writerows(rows)
    print(f"\n  wrote {OUT / 'sweep.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
