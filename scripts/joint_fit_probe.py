#!/usr/bin/env python3
"""Why is the real-stage chain late on ex2-type chips, and can one set of four bucket
numbers reproduce the full-swing step, the stressed gate (peak AND return) and the train?

Python chain only (current_limited_stage_model.simulate). Targets, all from the probed
transistor:
    full-swing step of the last stage           predriver_stages_2026-09-09/<dev>/full
    stressed last-stage pulses at the 5 widths  predriver_stages_2026-09-09/<dev>/w*
    the last stage on the 8-pulse train         track2_train_check_2026-09-13/<dev>/transistor_edge50_probed

Fits compared (K identical stages, plain law):
    full     fitted to the full-swing step only (= --source real)
    joint    fitted to the full-swing step + the stressed gate at the deepest width
    joint2   fitted to the full-swing step + the stressed gate at the deepest and the mildest width

    py -3.14 scripts/joint_fit_probe.py --dev ex2 --K 3
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
import current_limited_stage_model as cl  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import pulse_train_accumulation as pt  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

R = ROOT / "results"
TR = R / "track2_train_check_2026-09-13"
GATE = {"ex2": "v(xdut.n4)", "inv_chain": "v(xdut.vout7)"}
EDGE = {"ex2": 0.050, "inv_chain": 0.050}


def probed_train(dev, sup, width, n):
    """The transistor train with every stage probed (50 ps edges), cached."""
    d = TR / dev / "transistor_edge50_probed"
    d.mkdir(parents=True, exist_ok=True)
    src = TR / dev / "transistor_edge50"
    if not (d / "run.tr0").exists():
        for f in src.iterdir():
            if f.is_file() and not f.name.startswith("run."):
                shutil.copy2(f, d / f.name)
        deck = (src / "run.sp").read_text(encoding="utf-8", errors="replace")
        deck = re.sub(r"^\.probe tran .*$", ".probe tran " + " ".join(nd.upper() for nd in psp.STAGES[dev]), deck, flags=re.M)
        (d / "run.sp").write_text(deck, encoding="utf-8")
        if base.run_process([str(default_hspice()), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 1800) != 0:
            raise RuntimeError(f"hspice failed: {d}")
    raw = psp.parse_tr0(d / "run.tr0")
    return sl.time_ns(raw), psp.signals(raw, psp.STAGES[dev])


def widths(grid, y):
    up = np.where((y[1:] > 0.5) & (y[:-1] <= 0.5))[0]
    dn = np.where((y[1:] <= 0.5) & (y[:-1] > 0.5))[0]
    out = []
    for r in up:
        f = dn[dn > r]
        if len(f):
            out.append((grid[f[0]] - grid[r]) * 1e3)
    return out


def step_input(grid, edges):
    u = np.zeros_like(grid)
    for k in range(0, len(edges), 2):
        u[(grid >= edges[k]) & (grid < edges[k + 1])] = 1.0
    return u


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="ex2")
    ap.add_argument("--K", type=int, default=3)
    ap.add_argument("--p", type=float, default=1.0)
    args = ap.parse_args()
    dev, K = args.dev, args.K
    node = GATE[dev]
    grid, runs = cl.load(dev)                      # normalised nodes on a 2 ps grid, 4..21 ns
    Ws = sorted(k for k in runs if k != "full")
    half = EDGE[dev] / 2
    # inputs as the ngspice chain sees them: a 0/1 step at the edge midpoints
    u_full = step_input(grid, [5.0 + half, 15.0 + half])
    g_full = runs["full"][node]
    u_w = {W: step_input(grid, [5.0 + half, 5.0 + W / 1e3 + half]) for W in Ws}
    g_w = {W: runs[W][node] for W in Ws}
    # train
    _, sup, wt = pt.DEV[dev]
    n = pt.N_PULSES
    t_tr, sig = probed_train(dev, sup, wt, n)
    full = psp.parse_tr0(psp.OUT / dev / "full/run.tr0")
    tf = sl.time_ns(full)
    g_tr_real, _, _ = psp.normalise(tf, psp.signals(full, psp.STAGES[dev])[node], t_tr, sig[node])
    grid_tr = np.arange(4.0, pt.stop_ns(wt, n), cl.DT)
    u_tr = step_input(grid_tr, [e + half for e in pt.edges(wt, n)])
    g_tr = np.interp(grid_tr, t_tr, g_tr_real)
    w_real = widths(grid_tr, g_tr)
    print(f"{dev}: transistor last stage on the train: pulse-1 width {w_real[0]:.0f} ps, settled {w_real[-1]:.0f} ps")

    def sim(prm, u):
        x = u
        for _ in range(K):
            x = cl.simulate(x, *prm)
        return x

    def unpack(z):
        return float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), float(z[3]), args.p

    def cost_factory(ws, w_stress):
        mf = ((grid > 4.6) & (grid < 8.0)) | ((grid > 14.6) & (grid < 18.0))
        ms = (grid > 4.6) & (grid < 9.0)

        def cost(z):
            s_up, s_dn, vt, x_lin, p = unpack(z)
            if not (0.0 <= vt <= 0.7 and 0.02 <= x_lin <= 1.5):
                return 9.0
            prm = (s_up, s_dn, vt, x_lin, p)
            c = float(np.mean((sim(prm, u_full)[mf] - g_full[mf]) ** 2))
            for W in ws:
                c += w_stress * float(np.mean((sim(prm, u_w[W])[ms] - g_w[W][ms]) ** 2))
            return float(np.sqrt(c))
        return cost

    def fit(ws, w_stress=1.0):
        best = (9.0, None)
        cost = cost_factory(ws, w_stress)
        for s0 in (1.0, 3.0, 10.0, 30.0):
            z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4]), step=[0.7, 0.7, 0.15, 0.15], maxiter=800)
            if c < best[0]:
                best = (c, unpack(z))
        return best

    def report(label, prm):
        # stressed gate: peak and half-peak return time per width
        parts = []
        for W in Ws:
            g = sim(prm, u_w[W])
            m = (grid > 5.0) & (grid < 9.0)
            gm, gr = g[m], g_w[W][m]
            im, ir = int(np.argmax(gm)), int(np.argmax(gr))
            tm = grid[m][im + int(np.argmax(gm[im:] < 0.5 * gm[im]))]
            tr = grid[m][ir + int(np.argmax(gr[ir:] < 0.5 * gr[ir]))]
            parts.append(f"{W}: pk {gm.max() - gr.max():+.2f} ret {(tm - tr) * 1e3:+4.0f}ps")
        ws_ = widths(grid_tr, sim(prm, u_tr))
        mm = (grid_tr > 5 + 2 * wt * 4.4) & (grid_tr < 5 + 2 * wt * 5.0)
        val = float(sim(prm, u_tr)[mm].min())
        print(f"{label:<8} s_up {prm[0]:5.2f} s_dn {prm[1]:5.2f} vt {prm[2]:.2f} x_lin {prm[3]:.2f} | " + "  ".join(parts)
              + f" | train widths p1 {ws_[0] if ws_ else float('nan'):.0f} settled {ws_[-1] if len(ws_) >= n else float('nan'):.0f} ps (real {w_real[0]:.0f} / {w_real[-1]:.0f}), valley {val:.2f}")

    print("stressed gate per width: model peak minus real peak (0..1 scale), and half-peak return time minus real (ps)")
    c, prm = fit([])
    report("full", prm)
    c, prm = fit([Ws[0]])
    report("joint", prm)
    c, prm = fit([Ws[0], Ws[-1]])
    report("joint2", prm)
    c, prm = fit(list(Ws), 0.5)
    report("jointAll", prm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
