#!/usr/bin/env python3
"""Drive the model's gate with the transistor's REAL gate: is the output stage right?

Every remaining stressed-pad error is one of two things: the model's gate
trajectory is not the real one (a predriver problem), or the model's output
stage does not turn a correct gate into the correct pad (a Ku/Kd-map, C_comp or
I-V problem). This separates them without a fit. The model's GUP is replaced by
the transistor's own normalised gate node, replayed as a PWL source:

    ex2        GUP = norm(n4),     GDN = 1 - GUP      (one inverter drives both)
    inv_chain  GUP = norm(vout7),  GDN = 1 - GUP
    io_buf     GUP = norm(n2),     GDN = norm(n3)     (two predriver paths)

The rise/fall branch selectors (GUPTARGET, GDNTARGET) become the same trace led
by 4 ps, so "target >= gate" still means "rising". The Ku and Kd maps are then
re-derived from the shipped full-swing gate-part K(t) against the real full-
swing gate, so full swing is preserved by construction, and the stressed widths
are scored as in the cascade prototype.

If the pad now matches the transistor, everything left in our stressed error is
the predriver, and the whole problem reduces to producing g(t). If it does not,
the output-stage representation is wrong even with a perfect gate, and by how
much.

Needs the stage-probe runs (`predriver_stage_probe.py`) for the real gates.

    py -3.14 scripts/gate_replay_prototype.py --variant ex2
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

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_cascade_prototype as gc  # noqa: E402
import shared_gate_prototype as sg  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402

R = ROOT / "results"
G = R / "gate_cascade_prototype_2026-09-09"
ST = R / "predriver_stages_2026-09-09"
GATES = {"ex2": ("v(xdut.n4)", None), "inv_chain": ("v(xdut.vout7)", None),
         "io_buf": ("v(xdut.n2)", "v(xdut.n3)")}
LEAD_NS = 0.02        # direction selector looks 20 ps ahead; a 4 ps lead flipped on plateau noise and stalled ngspice on io_buf
DEADBAND = 0.005
SMOOTH_NS = 0.003


def real_gate(dev: str, W: int, node: str):
    """(t, g) with g normalised: 0 = rest, 1 = the node's full-swing extreme."""
    full = psp.parse_tr0(ST / dev / "full" / "run.tr0")
    tf, vf = sl.time_ns(full), psp.signals(full, psp.STAGES[dev])[node]
    rest = float(np.interp(4.5, tf, vf))      # HSPICE writes adaptive points only; plateaus are sparse
    high = float(np.interp(14.5, tf, vf))
    if W == 0:
        t, v = tf, vf
    else:
        raw = psp.parse_tr0(ST / dev / f"w{W}" / "run.tr0")
        t, v = sl.time_ns(raw), psp.signals(raw, psp.STAGES[dev])[node]
    return t, (v - rest) / (high - rest)


def pwl_source(name: str, node: str, t, g, lead_ns: float = 0.0) -> str:
    """A V-source PWL with 2 ps points where the trace moves and coarse points elsewhere."""
    tt = np.arange(0.0, 22.0, 0.002)
    gg = np.interp(tt + lead_ns, t, g)
    keep = np.zeros(len(tt), bool)
    keep[0] = keep[-1] = True
    d = np.abs(np.diff(gg))
    keep[1:] |= d > 1e-3
    keep[:-1] |= d > 1e-3
    keep |= (np.arange(len(tt)) % 25) == 0
    pts = " ".join(f"{a:.4f}n {b:.6f}" for a, b in zip(tt[keep], gg[keep]))
    return f"{name} {node} 0 PWL({pts})"


def patch_replay(sub: str, t, g, t_d=None, g_d=None, keep_gdn: bool = False) -> str:
    """Replace GUP (and GDN) dynamics by the replayed real gate; keep_gdn leaves the model's own GDN."""
    src = pwl_source("VGUPSRC", "GUPSRC", t, g) + "\n" + pwl_source("VGUPLEAD", "GUPLEAD", t, g, LEAD_NS)
    # the replayed gate goes through a 3 ps RC so GUP is smooth between the PWL
    # knots (a piecewise-linear gate straight into the comparators stalled ngspice
    # on io_buf's d1853 case); CGUP / RGUP stay
    s = re.sub(r"^BGUP GUP 0 I = .*$",
               src + f"\nBGUP GUP 0 I = -{{gate_c}} * (min(max(V(GUPSRC), 0), 1) - V(GUP)) / {SMOOTH_NS}n",
               sub, count=1, flags=re.M)
    s = re.sub(r"^BGUPTARGET GUPTARGET 0 V = .*$", "BGUPTARGET GUPTARGET 0 V = min(max(V(GUPLEAD), 0), 1)", s, count=1, flags=re.M)
    if keep_gdn:
        pass
    elif t_d is None:
        s = sg.patch_shared(s)
    else:
        srcd = pwl_source("VGDNSRC", "GDNSRC", t_d, g_d) + "\n" + pwl_source("VGDNLEAD", "GDNLEAD", t_d, g_d, LEAD_NS)
        s = re.sub(r"^BGDN GDN 0 I = .*$",
                   srcd + f"\nBGDN GDN 0 I = -{{gate_c}} * (min(max(V(GDNSRC), 0), 1) - V(GDN)) / {SMOOTH_NS}n",
                   s, count=1, flags=re.M)
        s = re.sub(r"^BGDNTARGET GDNTARGET 0 V = .*$", "BGDNTARGET GDNTARGET 0 V = min(max(V(GDNLEAD), 0), 1)", s, count=1, flags=re.M)
    # rising/falling map selection with a deadband, so plateau wiggles do not flip it
    s = re.sub(r"^BKUGATE_BASE KUGATE_BASE 0 V = .*$",
               f"BKUGATE_BASE KUGATE_BASE 0 V = (V(GUPTARGET) >= V(GUP) - {DEADBAND}) ? V(KUGATE_ON) : V(KUGATE_OFF)", s, count=1, flags=re.M)
    s = re.sub(r"^BKDGATE_BASE KDGATE_BASE 0 V = .*$",
               f"BKDGATE_BASE KDGATE_BASE 0 V = (V(GDNTARGET) >= V(GDN) - {DEADBAND}) ? V(KDGATE_ON) : V(KDGATE_OFF)", s, count=1, flags=re.M)
    assert "VGUPSRC" in s and "GUPLEAD" in s and f"V(GUP) - {DEADBAND}" in s
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="ex2")
    ap.add_argument("--ccomp", type=float, default=None, help="rewrite the IBIS C_comp (pF) before building the shipped model")
    ap.add_argument("--gup-only", action="store_true", help="replay the pull-up gate only; the model keeps its own GDN")
    ap.add_argument("--skip", type=int, nargs="*", default=[], help="widths (ps) to skip, e.g. one that stalls ngspice")
    args = ap.parse_args()
    dev = args.variant
    sup, ibis = gp.VARIANTS[dev]
    gp.VARIANT_NAME = dev
    OUT = G / (dev + (f"_c{args.ccomp:g}" if args.ccomp else ""))
    tag = OUT / ("gate_replay_guponly" if args.gup_only else "gate_replay")
    KEEP = args.gup_only
    tag.mkdir(parents=True, exist_ok=True)
    if not (OUT / "shipped/driver.sub").exists():
        if args.ccomp:
            txt = re.sub(r"^C_comp\s+.*$", f"C_comp {args.ccomp:.4f}pF {args.ccomp:.4f}pF {args.ccomp:.4f}pF",
                         ibis.read_text(errors="ignore"), count=1, flags=re.M)
            ibis = OUT / "input_ccomp.ibs"
            ibis.write_text(txt, encoding="utf-8")
        model, comp = gp.ibis_names(ibis)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
        (OUT / "shipped").mkdir(parents=True, exist_ok=True)
        subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(OUT / "shipped/driver.sub"))
    ship = (OUT / "shipped/driver.sub").read_text(encoding="utf-8")
    full_ship = gp.run_ours(OUT / "shipped/full", ship, sup, 10.0)
    node_u, node_d = GATES[dev]
    cs = gp.cases(dev)
    refs = {d_: gp.tr0_pad(d / "run.tr0") for d_, _, d in cs}

    # full swing: the real full-swing gate in, maps re-derived
    tu, gu = real_gate(dev, 0, node_u)
    td, gd = (None, None) if node_d is None else real_gate(dev, 0, node_d)
    if gd is not None:
        gd = 1.0 - gd            # GDN convention: 1 = pull-down on, and n3 rests high... see below
    text1 = patch_replay(ship, tu, gu, td, gd, keep_gdn=KEEP)
    full_new = gp.run_ours(tag / "full_pass1", text1, sup, 10.0)
    rise, fall = gc.derive_maps(full_new, full_ship)
    on, off = sg.derive_kd_maps(full_new, full_ship)
    text_full = gc.patch_kd_maps(gc.patch_maps(text1, rise, fall), on, off)
    (tag / "driver_replay_full.sub").write_text(text_full, encoding="utf-8")
    fs = gp.run_ours(tag / "full", text_full, sup, 10.0)
    tf = full_ship["t"]
    m = (tf > gp.RISE_NS - 0.5) & (tf < 17.0)
    ku_rms = float(np.sqrt(np.mean((np.interp(tf[m], fs["t"], fs["ku"]) - full_ship["ku"][m]) ** 2)))
    kd_rms = float(np.sqrt(np.mean((np.interp(tf[m], fs["t"], fs["kd"]) - full_ship["kd"][m]) ** 2)))
    print(f"\n  {dev}: model driven by the transistor's real gate ({node_u}" + (f", {node_d}" if node_d else "") + ")")
    print(f"    full swing: Ku rms {ku_rms:.4f}, Kd rms {kd_rms:.4f} vs shipped")
    print(f"    {'build':<14} | " + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs) + " | " + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs))
    rows = []
    for label in ("shipped", "gate_replay"):
        pks, lags = [], []
        fig, axes = plt.subplots(2, len(cs), figsize=(4.0 * len(cs), 7.0), sharex="col")
        for col, (depth, w, d) in enumerate(cs):
            if depth in args.skip and label != "shipped":
                pks.append(float("nan"))
                lags.append(float("nan"))
                continue
            if label == "shipped":
                r = gp.run_ours(OUT / "shipped" / f"d{depth}", ship, sup, w)
            else:
                tw, gw = real_gate(dev, depth, node_u)
                twd, gwd = (None, None) if node_d is None else real_gate(dev, depth, node_d)
                if gwd is not None:
                    gwd = 1.0 - gwd
                text = gc.patch_kd_maps(gc.patch_maps(patch_replay(ship, tw, gw, twd, gwd, keep_gdn=KEEP), rise, fall), on, off)
                r = gp.run_ours(tag / f"d{depth}", text, sup, w)
            pk, lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
            pks.append(pk)
            lags.append(lag)
            if label == "gate_replay":
                rev = gp.RISE_NS + w
                grid = np.arange(rev - 0.5, rev + 2.5, 0.002)
                tr_t, tr_pad = refs[depth]
                a = axes[0][col]
                a.plot(grid - rev, np.interp(grid, tw, gw), color="#111111", lw=3.0, label="transistor gate (replayed into the model)")
                a.plot(grid - rev, np.interp(grid, r["t"], r["gup"]), color="#2E8B57", lw=1.6, ls="--", label="model GUP")
                a.plot(grid - rev, np.interp(grid, r["t"], r["ku"]), color="#B03060", lw=1.4, label="model Ku")
                a.plot(grid - rev, np.interp(grid, r["t"], r["kd"]), color="#2B6CA3", lw=1.4, label="model Kd")
                a.set_ylim(-0.2, 1.2)
                a.set_title(f"W = {depth} ps", fontweight="bold")
                a.grid(alpha=0.3)
                if col == 0:
                    a.legend(fontsize=7)
                    a.set_ylabel("gate / coefficients")
                b = axes[1][col]
                b.plot(grid - rev, np.interp(grid, tr_t, tr_pad), color="#111111", lw=3.0, label="transistor pad")
                b.plot(grid - rev, np.interp(grid, r["t"], r["pad"]), color="#2E8B57", lw=2.0, ls="--", label=f"ours, real gate replayed ({pk:+.0f}%)")
                rs = gp.run_ours(OUT / "shipped" / f"d{depth}", ship, sup, w)
                b.plot(grid - rev, np.interp(grid, rs["t"], rs["pad"]), color="#C05621", lw=1.4, ls=":", label="ours, shipped")
                b.set_xlabel("time from the reversal (ns)")
                b.grid(alpha=0.3)
                if col == 0:
                    b.legend(fontsize=7)
                    b.set_ylabel("pad (V)")
        if label == "gate_replay":
            fig.suptitle(f"{dev}: the model's output stage fed with the transistor's real gate", fontsize=14, fontweight="bold")
            fig.tight_layout()
            fig.savefig(tag / "gate_replay.png", dpi=150)
        plt.close(fig)
        rows.append(dict(build=label, **{f"pk_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, pks)},
                         **{f"lag_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, lags)}))
        print(f"    {label:<14} | " + "".join(f"{v:>9.1f}" for v in pks) + " | " + "".join(f"{v:>9.0f}" for v in lags))
    with (tag / "sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wri.writeheader()
        wri.writerows(rows)
    print(f"  figure: {tag / 'gate_replay.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
