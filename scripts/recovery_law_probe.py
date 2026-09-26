#!/usr/bin/env python3
"""Which stage law reproduces the train widening? (inv_chain, python chain, no ngspice)

Measured on the transistor train (8 x 111 ps, 50 % duty, 50 ps edges): on pulse 1 each
stage narrows the pulse (input 111 ps -> vout7 90 ps); on the settled train each stage
widens it (~+6 ps per stage, vout7 133 ps) because 3-9 % of charge is left in every stage
between pulses. The fitted chain (x_lin 0.13, symmetric drain) narrows like pulse 1 and
never widens: its stages drain to exactly 0 in the gap.

Candidate laws, each refitted to the full-swing real gate (K = 7 identical stages), then
run on the train:

    dn_ratio  r  : discharge x_lin = r * x_lin (slower exponential tail on the drain side)
    p            : drive power law h(x) = clip((x - vt)/(1 - vt))**p (softer threshold)

    py -3.14 scripts/recovery_law_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402
import pulse_train_accumulation as pt  # noqa: E402

DEV, K, W, N = "inv_chain", 7, 0.111, 8
EDGE = 0.050
TRANS_P1 = [113, 111, 108, 104, 101, 94, 90]          # transistor, pulse 1 widths per stage (ps)
TRANS_SETTLED = [116, 117, 121, 122, 126, 128, 133]   # transistor, pulse 8
TRANS_VALLEY = [0.03, 0.01, 0.07, 0.02, 0.08, 0.03, 0.09]


def widths(grid, y):
    up = np.where((y[1:] > 0.5) & (y[:-1] <= 0.5))[0]
    dn = np.where((y[1:] <= 0.5) & (y[:-1] > 0.5))[0]
    ws = []
    for r in up:
        f = dn[dn > r]
        if len(f):
            ws.append((grid[f[0]] - grid[r]) * 1e3)
    return ws


def train_input(grid):
    pts_t, pts_v = [0.0], [0.0]
    for k, e in enumerate(pt.edges(W, N)):
        lvl = 1.0 if k % 2 == 0 else 0.0
        pts_t += [e, e + EDGE]
        pts_v += [1.0 - lvl, lvl]
    pts_t.append(grid[-1] + 1)
    pts_v.append(0.0)
    return np.interp(grid, pts_t, pts_v)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--step-input", action="store_true", help="drive the chain with the mid-supply comparator (0/1 step at the edge midpoints) as the ngspice chain does, instead of the 50 ps ramped input")
    args = ap.parse_args()
    global EDGE
    grid_full, runs = cl.load(DEV)
    u_full, v_full = runs["full"]["v(in_dig)"], runs["full"][f"v(xdut.vout{K})"]
    if args.step_input:
        u_full = (u_full > 0.5).astype(float)
        EDGE = 0.0001
    # fit on the two edges only (state carries: ~1 at the end of the first window, ~1 at the start of the second)
    m = ((grid_full > 4.6) & (grid_full < 6.6)) | ((grid_full > 14.6) & (grid_full < 16.6))
    u_fit, v_fit = u_full[m], v_full[m]
    grid_tr = np.arange(4.0, 5.0 + 2 * W * N + 1.5, cl.DT)
    u_tr = train_input(grid_tr)
    # single-pulse cliff: last-stage maximum for the five matrix widths (transistor: 1.00 0.99 0.97 0.94 0.88)
    def cliff(prms):
        out = []
        for wps in (135, 119, 111, 106, 104):
            g1 = np.arange(4.0, 8.0, cl.DT)
            u1 = ((g1 >= 5.0) & (g1 < 5.0 + wps / 1e3)).astype(float) if args.step_input else np.interp(g1, [0, 5.0, 5.0 + EDGE, 5.0 + wps / 1e3, 5.0 + wps / 1e3 + EDGE, 9.0], [0, 0, 1, 1, 0, 0])
            x = u1
            for prm in prms:
                x = cl.simulate(x, *prm)
            out.append(float(x.max()))
        return out
    print(f"transistor  p1 widths {TRANS_P1}  settled {TRANS_SETTLED}  valley {TRANS_VALLEY}; single-pulse gate max at 135/119/111/106/104 ps: 1.00 0.99 0.97 0.94 0.88")
    print(f"{'law':<22}{'fit rms':>8}{'s_up':>7}{'s_dn':>7}{'vt':>6}{'x_lin':>7} | p1 widths per stage -> settled widths | valley p4-5 | pad-equivalent gate width p1 / settled")
    for p, ratio in ((1.0, 1.0), (0.5, 1.0), (0.7, 1.0), (2.0, 1.0), (1.0, 3.0), (0.5, 3.0)):
        cl.XLIN_DN_RATIO = ratio
        rms, prms = cl.fit_chain_shared(u_fit, v_fit, K, p=p)
        s_up, s_dn, vt, x_lin, _ = prms[0]
        x = u_tr
        p1, st, val = [], [], []
        for prm in prms:
            x = cl.simulate(x, *prm)
            ws = widths(grid_tr, x)
            p1.append(ws[0] if ws else float("nan"))
            st.append(ws[-1] if len(ws) >= 8 else float("nan"))
            mm = (grid_tr > 5 + 2 * W * 4.4) & (grid_tr < 5 + 2 * W * 5.0)
            val.append(float(x[mm].min()))
        print(f"p={p:<4g} dn_ratio={ratio:<5g}{rms:>8.4f}{s_up:>7.2f}{s_dn:>7.2f}{vt:>6.2f}{x_lin:>7.3f} | "
              + " ".join(f"{a:4.0f}" for a in p1) + " -> " + " ".join(f"{a:4.0f}" for a in st)
              + " | " + " ".join(f"{a:4.2f}" for a in val) + f" | {p1[-1]:.0f} / {st[-1]:.0f} | cliff " + " ".join(f"{a:4.2f}" for a in cliff(prms)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
