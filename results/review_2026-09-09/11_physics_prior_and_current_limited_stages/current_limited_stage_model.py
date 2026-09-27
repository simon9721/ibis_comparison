#!/usr/bin/env python3
"""Does a current-limited stage, fitted at full swing only, predict the sub-linear stressed gate?

The superposition test showed ex2's and inv_chain's predriver stages under-reach
their linear prediction and return early (`predriver_stages_2026-09-09`). The
theory offered was: a CMOS inverter into a large load is a current source while
its input is at the rail (constant slew) and a resistor only near the destination
rail; with a partial input, its current follows the input non-linearly. This
tests that theory quantitatively, with no stressed data in the fit:

    dv/dt = s_up * h(u) * r(1 - v)  -  s_dn * h(1 - u) * r(v)
    h(x)  = clip((x - vt) / (1 - vt), 0, 1) ** p        drive vs input (threshold + power law)
    r(x)  = min(1, x / x_lin)                           current-limited, resistive near the rail

u, v are the stage's input and output nodes, each normalised 0 = rest, 1 = its
own full-swing high state (so every stage reads as non-inverting). The four
numbers (s_up, s_dn, vt, x_lin; p fitted from {1, 1.5, 2}) are fitted to the
full-swing run only. Then, for each stressed width, the stage is driven by its
measured stressed input and the prediction is compared with the measured output
and with the linear superposition prediction. Finally the whole chain is run
from the digital input alone.

    py -3.14 scripts/current_limited_stage_model.py --dev ex2 inv_chain
"""
from __future__ import annotations

import argparse
import csv
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
import predriver_stage_probe as psp  # noqa: E402

R = ROOT / "results"
ST = R / "predriver_stages_2026-09-09"
OUT = R / "current_limited_stages_2026-09-10"
DT = 0.002
XLIN_DN_RATIO = 1.0      # x_lin for the discharge direction = x_lin * ratio (1 = symmetric)
T_END = {"ex2": 21.0, "inv_chain": 21.0, "io_buf": 21.5}


def h(x, vt, p):
    return np.clip((x - vt) / (1.0 - vt), 0.0, 1.0) ** p


def simulate(u, s_up, s_dn, vt, x_lin, p, v0=0.0, n_sub=2):
    """Heun (RK2) with n_sub substeps per DT sample.

    Explicit Euler at DT = 2 ps was found to bias the fast inv_chain stages
    (tau ~ 20 ps): the python chain passed a 119 ps pulse that the same chain
    in ngspice swallowed. Heun with 1 ps substeps agrees with ngspice.
    """
    v = np.empty_like(u)
    x = v0
    hu = h(u, vt, p)
    hd = h(1.0 - u, vt, p)
    dt = DT / n_sub
    inv_xl = 1.0 / x_lin
    inv_xd = 1.0 / (x_lin * XLIN_DN_RATIO)

    def f(x_, i):
        up = s_up * hu[i] * min(1.0, (1.0 - x_) * inv_xl)
        dn = s_dn * hd[i] * min(1.0, x_ * inv_xd)
        return up - dn

    for i in range(len(u)):
        for _ in range(n_sub):
            k1 = f(x, i)
            k2 = f(x + dt * k1, i)
            x = x + 0.5 * dt * (k1 + k2)
            x = min(max(x, -0.05), 1.05)
        v[i] = x
    return v


def load(dev):
    runs = {}
    nodes = psp.STAGES[dev]
    full = psp.parse_tr0(ST / dev / "full/run.tr0")
    tf = np.asarray(full["time"], float) * 1e9
    sig = psp.signals(full, nodes)
    norm = {}
    for n in nodes:
        rest = float(np.interp(4.5, tf, sig[n]))
        high = float(np.interp(14.5, tf, sig[n]))
        norm[n] = (rest, high)
    grid = np.arange(4.0, T_END[dev], DT)
    runs["full"] = {n: np.interp(grid, tf, (sig[n] - norm[n][0]) / (norm[n][1] - norm[n][0])) for n in nodes}
    for d in sorted((ST / dev).glob("w*")):
        W = int(d.name[1:])
        raw = psp.parse_tr0(d / "run.tr0")
        t = np.asarray(raw["time"], float) * 1e9
        s = psp.signals(raw, nodes)
        runs[W] = {n: np.interp(grid, t, (s[n] - norm[n][0]) / (norm[n][1] - norm[n][0])) for n in nodes}
    return grid, runs


def nelder_mead(f, x0, step, xatol=1e-3, fatol=1e-5, maxiter=600):
    """Plain Nelder-Mead (no scipy on this interpreter)."""
    n = len(x0)
    pts = [np.array(x0, float)]
    for i in range(n):
        x = np.array(x0, float)
        x[i] += step[i]
        pts.append(x)
    vals = [f(x) for x in pts]
    for _ in range(maxiter):
        order = np.argsort(vals)
        pts = [pts[i] for i in order]
        vals = [vals[i] for i in order]
        if max(np.max(np.abs(p - pts[0])) for p in pts[1:]) < xatol and vals[-1] - vals[0] < fatol:
            break
        c = np.mean(pts[:-1], axis=0)
        xr = c + (c - pts[-1])
        fr = f(xr)
        if fr < vals[0]:
            xe = c + 2.0 * (c - pts[-1])
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c)
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, len(pts)):
                    pts[i] = pts[0] + 0.5 * (pts[i] - pts[0])
                    vals[i] = f(pts[i])
    i = int(np.argmin(vals))
    return pts[i], vals[i]


def fit_stage(u, v, p_set=(1.0, 1.5, 2.0)):
    """Nelder-Mead from a few starts over (log s_up, log s_dn, vt, x_lin), p from a small set."""
    best = (9.0, None)

    def cost(x, p):
        s_up, s_dn, vt, x_lin = np.exp(x[0]), np.exp(x[1]), x[2], x[3]
        if not (0.0 <= vt <= 0.7 and 0.02 <= x_lin <= 1.5):
            return 9.0
        pred = simulate(u, s_up, s_dn, vt, x_lin, p)
        return float(np.sqrt(np.mean((pred - v) ** 2)))

    for p in p_set:
        for s0 in (1.0, 4.0, 16.0):
            x0 = np.array([np.log(s0), np.log(s0), 0.3, 0.3])
            x, c = nelder_mead(lambda z: cost(z, p), x0, step=[0.7, 0.7, 0.15, 0.15])
            if c < best[0]:
                best = (c, (float(np.exp(x[0])), float(np.exp(x[1])), float(x[2]), float(x[3]), p))
    return best


def linear_pred(grid, v_full, W_ns):
    """Superposition of the node's own full-swing step responses (rise at 5 ns, fall at 15 ns)."""
    rise = np.where(grid < 14.9, v_full, 1.0)                                       # rise response, held after the plateau
    fall = np.interp(grid + (15.0 - 5.0 - W_ns), grid, v_full, left=1.0)             # fall response moved to t_off
    fall = np.where(grid < 5.0 + W_ns, 1.0, fall)
    return rise + fall - 1.0


def t50(grid, y, t0=5.0):
    m = grid >= t0
    yy = y[m]
    i = np.where(yy >= 0.5 * yy.max())[0]
    return float(grid[m][i[0]] - t0) * 1e3 if len(i) and yy.max() > 0.05 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", nargs="*", default=["ex2", "inv_chain"])
    ap.add_argument("--p", type=float, default=None, help="fix the drive power law (full swing cannot determine it); default: fit from {1, 1.5, 2}")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    r0 = lambda x: None if np.isnan(x) else round(x)   # noqa: E731
    for dev in args.dev:
        nodes = psp.STAGES[dev]
        grid, runs = load(dev)
        full = runs["full"]
        widths = sorted(k for k in runs if k != "full")
        params = {}
        print(f"\n=== {dev}: current-limited stage fits at full swing")
        print(f"    {'stage':<26}{'s_up 1/ns':>10}{'s_dn 1/ns':>10}{'vt':>6}{'x_lin':>7}{'p':>4}{'rms full':>9}")
        for k in range(1, len(nodes)):
            u_name, v_name = nodes[k - 1], nodes[k]
            c, prm = fit_stage(full[u_name], full[v_name], (args.p,) if args.p else (1.0, 1.5, 2.0))
            params[v_name] = prm
            print(f"    {u_name[2:-1]:>10} -> {v_name[2:-1]:<11}{prm[0]:>10.2f}{prm[1]:>10.2f}{prm[2]:>6.2f}{prm[3]:>7.2f}{prm[4]:>4.1f}{c:>9.3f}")
            rows.append(dict(device=dev, stage=v_name, s_up=round(prm[0], 3), s_dn=round(prm[1], 3), vt=round(prm[2], 3),
                             x_lin=round(prm[3], 3), p=prm[4], rms_full=round(c, 4)))
        # --- stressed: each stage from its measured input; and the whole chain from the digital input
        print(f"\n    stressed pulses -- measured vs current-limited (from measured input / from the chain) vs linear superposition")
        print(f"    {'stage':<12}{'W':>6}{'meas max':>9}{'CL max':>8}{'chain max':>10}{'lin max':>8}{'meas t50':>9}{'CL t50':>8}{'chain t50':>10}{'lin t50':>8}{'rms CL':>8}{'rms lin':>8}")
        nrow, ncol = len(nodes) - 1, len(widths)
        fig, axes = plt.subplots(nrow, ncol, figsize=(4.0 * ncol, 2.6 * nrow), sharex=True, squeeze=False)
        for j, W in enumerate(widths):
            Wn = W / 1e3
            chain_in = runs[W][nodes[0]]
            chain = chain_in
            for k in range(1, len(nodes)):
                u_name, v_name = nodes[k - 1], nodes[k]
                prm = params[v_name]
                meas = runs[W][v_name]
                cl = simulate(runs[W][u_name], *prm)
                chain = simulate(chain, *prm)
                lin = linear_pred(grid, full[v_name], Wn)
                m = grid >= 5.0
                rms_cl = float(np.sqrt(np.mean((cl[m] - meas[m]) ** 2)))
                rms_lin = float(np.sqrt(np.mean((lin[m] - meas[m]) ** 2)))
                print(f"    {v_name[2:-1]:<12}{W:>6}{meas.max():>9.3f}{cl.max():>8.3f}{chain.max():>10.3f}{lin.max():>8.3f}"
                      f"{t50(grid, meas):>9.0f}{t50(grid, cl):>8.0f}{t50(grid, chain):>10.0f}{t50(grid, lin):>8.0f}{rms_cl:>8.3f}{rms_lin:>8.3f}")
                rows.append(dict(device=dev, stage=v_name, width_ps=W, meas_max=round(float(meas.max()), 3), cl_max=round(float(cl.max()), 3),
                                 chain_max=round(float(chain.max()), 3), lin_max=round(float(lin.max()), 3),
                                 meas_t50=r0(t50(grid, meas)), cl_t50=r0(t50(grid, cl)), chain_t50=r0(t50(grid, chain)),
                                 lin_t50=r0(t50(grid, lin)), rms_cl=round(rms_cl, 4), rms_lin=round(rms_lin, 4)))
                a = axes[k - 1][j]
                a.plot(grid - 5.0, meas, color="#111111", lw=2.4, label="measured")
                a.plot(grid - 5.0, cl, color="#B03060", lw=1.8, label="current-limited stage, measured input")
                a.plot(grid - 5.0, chain, color="#C05621", lw=1.2, ls="-.", label="current-limited chain from the input pin")
                a.plot(grid - 5.0, lin, color="#2E8B57", lw=1.4, ls="--", label="linear superposition")
                a.axvline(Wn, color="#8A8A8A", ls="--", lw=1.0)
                a.set_xlim(-0.2, psp.XMAX_NS[dev])
                a.set_ylim(-0.15, 1.2)
                a.grid(alpha=0.3)
                if k == 1:
                    a.set_title(f"W = {W} ps", fontweight="bold")
                if j == 0:
                    a.set_ylabel(v_name[2:-1].replace("xdut.", "") + "\n0 = rest, 1 = full swing", fontsize=9)
                if k == 1 and j == 0:
                    a.legend(fontsize=7, loc="upper right")
                if k == nrow:
                    a.set_xlabel("time from the input rising edge (ns)")
        fig.suptitle(f"{dev}: stages under a short pulse -- a current-limited stage fitted at full swing only, vs linear superposition",
                     fontsize=13, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.98))
        fig.savefig(OUT / f"{dev}_current_limited_stages{args.tag}.png", dpi=150)
        plt.close(fig)
        print(f"    figure: {OUT / f'{dev}_current_limited_stages{args.tag}.png'}")
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with (OUT / f"results{args.tag}.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=keys)
        wri.writeheader()
        wri.writerows(rows)
    return 0


if __name__ == "__main__" and "--chain" not in sys.argv and "--shared" not in sys.argv:
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# How much of the chain must a model carry? Fit K current-limited stages from
# the input pin straight to the output gate, at full swing only, and predict
# the stressed gate. K = 1 is what a converter could build from one derived
# step response; the real chains are 3 (ex2) and 7 (inv_chain) stages.
# ---------------------------------------------------------------------------
def simulate_chain(u, prms):
    x = u
    for prm in prms:
        x = simulate(x, *prm)
    return x


def fit_chain(u, v, K, p=1.0, starts=None):
    best = (9.0, None)

    def unpack(z):
        out = []
        for k in range(K):
            s_up, s_dn, vt, x_lin = np.exp(z[4 * k]), np.exp(z[4 * k + 1]), z[4 * k + 2], z[4 * k + 3]
            if not (0.0 <= vt <= 0.7 and 0.02 <= x_lin <= 1.5):
                return None
            out.append((s_up, s_dn, vt, x_lin, p))
        return out

    def cost(z):
        prms = unpack(z)
        if prms is None:
            return 9.0
        return float(np.sqrt(np.mean((simulate_chain(u, prms) - v) ** 2)))

    for s0 in (starts or (2.0, 6.0, 20.0)):
        z0 = np.array([np.log(s0), np.log(s0), 0.4, 0.4] * K)
        z, c = nelder_mead(cost, z0, step=[0.7, 0.7, 0.15, 0.15] * K, maxiter=1500)
        if c < best[0]:
            best = (c, unpack(z))
    return best


def chain_study(dev, gate_node, Ks=(1, 2, 3)):
    grid, runs = load(dev)
    full = runs["full"]
    u_name = psp.STAGES[dev][0]
    widths = sorted(k for k in runs if k != "full")
    print(f"\n=== {dev}: K current-limited stages from {u_name[2:-1]} to {gate_node[2:-1]}, fitted at full swing only")
    fig, axes = plt.subplots(1, len(widths), figsize=(4.0 * len(widths), 3.6), sharey=True)
    out = []
    for K in Ks:
        c, prms = fit_chain(full[u_name], full[gate_node], K)
        print(f"    K={K}: full-swing rms {c:.4f}   " + "  ".join(f"[s_up {p[0]:.2f} s_dn {p[1]:.2f} vt {p[2]:.2f} x_lin {p[3]:.2f}]" for p in prms))
        print(f"    {'W':>6}{'meas max':>9}{'pred max':>9}{'lin max':>8}{'meas t50':>9}{'pred t50':>9}{'rms':>7}")
        for j, W in enumerate(widths):
            meas = runs[W][gate_node]
            pred = simulate_chain(runs[W][u_name], prms)
            lin = linear_pred(grid, full[gate_node], W / 1e3)
            m = grid >= 5.0
            rms = float(np.sqrt(np.mean((pred[m] - meas[m]) ** 2)))
            print(f"    {W:>6}{meas.max():>9.3f}{pred.max():>9.3f}{lin.max():>8.3f}{t50(grid, meas):>9.0f}{t50(grid, pred):>9.0f}{rms:>7.3f}")
            out.append(dict(device=dev, K=K, width_ps=W, meas_max=round(float(meas.max()), 3), pred_max=round(float(pred.max()), 3),
                            lin_max=round(float(lin.max()), 3), rms=round(rms, 4), full_rms=round(c, 4)))
            a = axes[j]
            if K == Ks[0]:
                a.plot(grid - 5.0, meas, color="#111111", lw=2.6, label="measured gate")
                a.plot(grid - 5.0, lin, color="#2E8B57", lw=1.3, ls="--", label="linear superposition")
            a.plot(grid - 5.0, pred, lw=1.6, ls=("-", "-.", ":")[Ks.index(K) % 3], color=("#B03060", "#C05621", "#2B6CA3")[Ks.index(K) % 3], label=f"K = {K} stages")
            a.set_xlim(-0.2, psp.XMAX_NS[dev])
            a.set_ylim(-0.1, 1.2)
            a.set_title(f"W = {W} ps", fontweight="bold")
            a.set_xlabel("time from the input rising edge (ns)")
            a.grid(alpha=0.3)
            if j == 0:
                a.set_ylabel(f"{gate_node[2:-1].replace('xdut.', '')}, 0 = rest, 1 = full swing")
                a.legend(fontsize=7)
    fig.suptitle(f"{dev}: the output gate under stress from K current-limited stages fitted at full swing only", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / f"{dev}_chain_K.png", dpi=150)
    plt.close(fig)
    with (OUT / f"{dev}_chain_K.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        wri.writeheader()
        wri.writerows(out)
    print(f"    figure: {OUT / f'{dev}_chain_K.png'}")


if __name__ == "__main__" and "--chain" in sys.argv and "--shared" not in sys.argv:
    OUT.mkdir(parents=True, exist_ok=True)
    for dev, node in (("ex2", "v(xdut.n4)"), ("inv_chain", "v(xdut.vout7)")):
        if dev in sys.argv or ("ex2" not in sys.argv and "inv_chain" not in sys.argv):
            chain_study(dev, node)


# ---------------------------------------------------------------------------
# The free K-stage fit is degenerate at full swing (any internal split of the
# delay fits) and the degenerate solutions predict stress wrongly. Real chains
# are tapered inverters of similar delay: constrain the K stages to SHARE their
# four numbers (a well-posed 4-parameter fit) and ask again.
# ---------------------------------------------------------------------------
def fit_chain_shared(u, v, K, p=1.0, x_lin_fixed=None):
    """K identical stages, 4 shared numbers (3 if x_lin is fixed by physics)."""
    best = (9.0, None)

    def unpack(z):
        x_lin = x_lin_fixed if x_lin_fixed is not None else z[3]
        return np.exp(z[0]), np.exp(z[1]), z[2], x_lin

    def cost(z):
        s_up, s_dn, vt, x_lin = unpack(z)
        if not (0.0 <= vt <= 0.7 and 0.02 <= x_lin <= 1.5):
            return 9.0
        return float(np.sqrt(np.mean((simulate_chain(u, [(s_up, s_dn, vt, x_lin, p)] * K) - v) ** 2)))

    n = 3 if x_lin_fixed is not None else 4
    for s0 in (2.0, 8.0, 30.0):
        z, c = nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4][:n]), step=[0.7, 0.7, 0.15, 0.15][:n], maxiter=800)
        if c < best[0]:
            s_up, s_dn, vt, x_lin = unpack(z)
            best = (c, [(float(s_up), float(s_dn), float(vt), float(x_lin), p)] * K)
    return best


def shared_study(dev, gate_node, Ks):
    grid, runs = load(dev)
    full = runs["full"]
    u_name = psp.STAGES[dev][0]
    widths = sorted(k for k in runs if k != "full")
    print(f"\n=== {dev}: K IDENTICAL current-limited stages (4 shared numbers) from {u_name[2:-1]} to {gate_node[2:-1]}, fitted at full swing only")
    out = []
    fig, axes = plt.subplots(1, len(widths), figsize=(4.0 * len(widths), 3.6), sharey=True)
    for K in Ks:
        c, prms = fit_chain_shared(full[u_name], full[gate_node], K)
        p0 = prms[0]
        print(f"    K={K}: full-swing rms {c:.4f}   s_up {p0[0]:.2f} s_dn {p0[1]:.2f} vt {p0[2]:.2f} x_lin {p0[3]:.2f}")
        print(f"    {'W':>6}{'meas max':>9}{'pred max':>9}{'lin max':>8}{'meas t50':>9}{'pred t50':>9}{'rms':>7}")
        for j, W in enumerate(widths):
            meas = runs[W][gate_node]
            pred = simulate_chain(runs[W][u_name], prms)
            lin = linear_pred(grid, full[gate_node], W / 1e3)
            m = grid >= 5.0
            rms = float(np.sqrt(np.mean((pred[m] - meas[m]) ** 2)))
            print(f"    {W:>6}{meas.max():>9.3f}{pred.max():>9.3f}{lin.max():>8.3f}{t50(grid, meas):>9.0f}{t50(grid, pred):>9.0f}{rms:>7.3f}")
            out.append(dict(device=dev, K=K, width_ps=W, meas_max=round(float(meas.max()), 3), pred_max=round(float(pred.max()), 3),
                            lin_max=round(float(lin.max()), 3), rms=round(rms, 4), full_rms=round(c, 4)))
            a = axes[j]
            if K == Ks[0]:
                a.plot(grid - 5.0, meas, color="#111111", lw=2.6, label="measured gate")
                a.plot(grid - 5.0, lin, color="#2E8B57", lw=1.3, ls="--", label="linear superposition")
            i = Ks.index(K) % 4
            a.plot(grid - 5.0, pred, lw=1.6, ls=("-", "-.", ":", "--")[i], color=("#B03060", "#C05621", "#2B6CA3", "#6A5ACD")[i], label=f"K = {K} identical stages")
            a.set_xlim(-0.2, psp.XMAX_NS[dev])
            a.set_ylim(-0.1, 1.2)
            a.set_title(f"W = {W} ps", fontweight="bold")
            a.set_xlabel("time from the input rising edge (ns)")
            a.grid(alpha=0.3)
            if j == 0:
                a.set_ylabel(f"{gate_node[2:-1].replace('xdut.', '')}, 0 = rest, 1 = full swing")
                a.legend(fontsize=7)
    fig.suptitle(f"{dev}: the output gate under stress from K identical current-limited stages (4 numbers) fitted at full swing only",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / f"{dev}_chain_shared_K.png", dpi=150)
    plt.close(fig)
    with (OUT / f"{dev}_chain_shared_K.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        wri.writeheader()
        wri.writerows(out)
    print(f"    figure: {OUT / f'{dev}_chain_shared_K.png'}")


if __name__ == "__main__" and "--shared" in sys.argv:
    OUT.mkdir(parents=True, exist_ok=True)
    if "ex2" in sys.argv or "inv_chain" not in sys.argv:
        shared_study("ex2", "v(xdut.n4)", (2, 3, 4))
    if "inv_chain" in sys.argv or "ex2" not in sys.argv:
        shared_study("inv_chain", "v(xdut.vout7)", (3, 5, 7, 9))
