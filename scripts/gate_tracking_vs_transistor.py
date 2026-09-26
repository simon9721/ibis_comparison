#!/usr/bin/env python3
"""Does the corrected model's internal gate follow the transistor's real gate?

The prototypes reproduce the stressed pad on twelve buffers. That could be a
good curve fit or the right physics. The matrix transistor runs recorded the
real predriver gate (ex2 `n4`, inv_chain `vout7`, io_buf `n2`), so the question
is answerable: normalise the real gate to its own full-swing excursion and
overlay the model's command/gate nodes under stress.

For ex2 the cascade's last stage (`PUP5`) is the model's predriver and `GUP`
its gate; for inv_chain the hybrid stage (`PUCMDLVL`) and `GUP`. If the
model's node tracks the transistor's in time and in how far it gets, the
structure is physical. If it tracks only at full swing, it is a fit.

    py -3.14 scripts/gate_tracking_vs_transistor.py --variant ex2 --build cascade5
    py -3.14 scripts/gate_tracking_vs_transistor.py --variant inv_chain --build hybrid50ps
"""
from __future__ import annotations

import argparse
import re
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
import spicelab as sl  # noqa: E402

R = ROOT / "results"
MX = R / "stress_method_matrix_2026-08-20/pad_match/hspice_references"
G = R / "gate_cascade_prototype_2026-09-09"
GATE = {"ex2": ("v(xdut.n4)", "pup5", True), "inv_chain": ("v(xdut.vout7)", "pucmdlvl", True),
        "io_buf": ("v(xdut.n2)", "guptarget", True)}
RISE_NS = 5.0


def norm(v, lo, hi, invert):
    x = (v - lo) / (hi - lo)
    return 1.0 - x if invert else x


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="ex2")
    ap.add_argument("--build", default="cascade5")
    args = ap.parse_args()
    node, cmd, invert = GATE[args.variant]
    runs = sorted((MX / args.variant / "transistor/r50_c2pf").glob("short_high_w*ps_*"))
    OUT = G / args.variant
    fig, axes = plt.subplots(2, len(runs), figsize=(4.0 * len(runs), 7.5), sharex="col")
    print(f"  {args.variant} / {args.build}: real gate {node} vs model {cmd} and GUP, normalised to full-swing excursion")
    print(f"    {'W ps':>6}{'real max':>9}{'model cmd max':>14}{'GUP max':>9}{'t50 real':>9}{'t50 cmd':>9}{'t50 GUP':>9}{'corr(cmd,real)':>15}")
    # full-swing excursion of the real gate: from the widest run's own extremes is
    # biased; use the model's shipped full swing for the model, and for the real
    # node the extremes over the widest stressed run (it saturates there on
    # inv_chain; on ex2 it reaches ~70 % -- reported as is).
    for col, d in enumerate(runs):
        W = int(re.search(r"_w(\d+)ps", d.name).group(1))
        rev = RISE_NS + W / 1000.0
        tr = sl.parse_hspice_tr0(d / "run.tr0")
        t = sl.time_ns(tr)
        g = np.asarray(tr[node], float)
        rest = float(np.median(g[(t > 4.0) & (t < 4.9)]))
        # the gate's fully-on level: its extreme on the FULL-SWING control run,
        # so "1" means "as far as the real gate ever goes", not this run's own max
        fs = sl.parse_hspice_tr0(R / "three_buffer_loaded_swing_stress_sweep_2026-08-14/hspice_references"
                                 / args.variant / "transistor/r50_c2pf/long_control/run.tr0")
        gfs = np.asarray(fs[node], float)
        ext = float(gfs.min() if invert else gfs.max())
        real = (rest - g) / (rest - ext) if invert else (g - rest) / (ext - rest)
        # model
        mdl = sl.parse_ngspice_raw(OUT / args.build / f"d{W}" / "run.raw")
        tm = sl.time_ns(mdl)
        c = np.full(len(tm), np.nan)
        for cand in (cmd, "pucmdlvl", "pup6", "pup5"):
            try:
                c = sl.signal(mdl, f"v(x1.{cand})")
                cmd = cand
                break
            except Exception:                           # noqa: BLE001
                continue
        gup = sl.signal(mdl, "v(x1.gup)")
        grid = np.arange(rev - 0.5, rev + 2.5, 0.002)
        rr = np.interp(grid, t, real)
        cc = np.interp(grid, tm, c)
        gg = np.interp(grid, tm, gup)

        def t50(y):
            i = np.where(y > 0.5 * np.nanmax(y))[0]
            return float(grid[i[0]] - rev) * 1e3 if len(i) else float("nan")
        ok = ~np.isnan(cc)
        corr = float(np.corrcoef(cc[ok], rr[ok])[0, 1]) if ok.sum() > 10 else float("nan")
        print(f"    {W:>6}{rr.max():>9.3f}{np.nanmax(cc):>14.3f}{gg.max():>9.3f}{t50(rr):>9.0f}{t50(cc):>9.0f}{t50(gg):>9.0f}{corr:>15.3f}")
        a = axes[0][col]
        a.plot(grid - rev, rr, color="#111111", lw=3.0, label=f"transistor {node.split('.')[-1][:-1]}, normalised")
        a.plot(grid - rev, cc, color="#2E8B57", lw=2.0, ls="--", label=f"model {cmd}")
        a.plot(grid - rev, gg, color="#C05621", lw=1.6, ls=":", label="model GUP")
        a.axvline(0, color="#8A8A8A", ls="--", lw=1.2)
        a.set_ylim(-0.1, 1.15)
        a.set_title(f"W = {W} ps", fontweight="bold")
        a.grid(alpha=0.3)
        if col == 0:
            a.set_ylabel("gate, 0 = off, 1 = full-swing on")
            a.legend(fontsize=8)
        b = axes[1][col]
        pad = np.asarray(tr["v(pad_sp)"], float)
        b.plot(grid - rev, np.interp(grid, t, pad), color="#111111", lw=3.0, label="transistor pad")
        b.plot(grid - rev, np.interp(grid, tm, sl.trace(mdl, "out")), color="#2E8B57", lw=2.0, ls="--", label=f"ours, {args.build}")
        b.axvline(0, color="#8A8A8A", ls="--", lw=1.2)
        b.set_xlabel("time from the reversal (ns)")
        b.grid(alpha=0.3)
        if col == 0:
            b.set_ylabel("pad (V)")
            b.legend(fontsize=8)
    fig.suptitle(f"{args.variant}: does the model's gate follow the transistor's real gate under stress?  ({args.build})",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / f"gate_tracking_{args.build}.png", dpi=160)
    plt.close(fig)
    print(f"  figure: {OUT / f'gate_tracking_{args.build}.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
