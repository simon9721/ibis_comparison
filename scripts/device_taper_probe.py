#!/usr/bin/env python3
"""Can the device's own taper replace the indefensible x_lin = 0.45?

The stage law's drain factor is `min(1, dist/x_lin)`: a straight line into a
boundary held at a constant 0.45 of the swing. Both halves are unsourced
(`docs/stage_law_walkthrough.md` 4.4, tier 4), and the constant is the worse
offender - a real device's boundary is its overdrive, which MOVES with the input.

SPICE Level 1 (Leventhal & Green 3.8 p.89, eq. 3-24/3-25) gives instead

    I/I_sat = q(2 - q),   q = min(r, 1),   r = headroom / overdrive

which is a parabola into a boundary that tracks the gate. Substituting it costs
one parameter FEWER, because x_lin disappears into vt. This asks whether that
substitution is affordable.

Four drain factors, same integrator, same optimiser budget, fitted to full swing
only and then asked to predict the stressed gate (the section-8 bench):

    linear_const   min(1, dist/x_lin)          today's model            4 params
    parab_const    q(2-q), q = dist/x_lin      device curve, fixed edge 4 params
    linear_ov      min(1, dist/ov)             today's curve, moving edge 3 params
    parab_ov       q(2-q), q = dist/ov         the device form          3 params

`ov` is the driving device's normalised overdrive: u - vt when charging,
(1-u) - vt when discharging. The 2x2 separates the two changes - curve shape and
boundary - so a loss can be attributed.

    py -3.14 scripts/device_taper_probe.py --check       # integrator agrees with cl.simulate
    py -3.14 scripts/device_taper_probe.py --dev ex2
    py -3.14 scripts/device_taper_probe.py               # both buffers

Output: results/device_taper_2026-09-28/
"""
from __future__ import annotations

import argparse
import csv
import json
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

import current_limited_stage_model as cl  # noqa: E402  (owns the law, the fitter, the loader)
import predriver_stage_probe as psp  # noqa: E402

OUT = ROOT / "results" / "device_taper_2026-09-28"

# K is not under test here: take the count section 8 established for each buffer.
BUFFERS = {"ex2": dict(K=3, gate="v(xdut.n4)"), "inv_chain": dict(K=7, gate="v(xdut.vout7)")}

KINDS = ("linear_const", "parab_const", "linear_ov", "parab_ov", "parab_vsat")
NP_ = {"linear_const": 4, "parab_const": 4, "linear_ov": 3, "parab_ov": 3, "parab_vsat": 3}
LABEL = {
    "linear_const": "min(1, d/x_lin)      straight, fixed edge   [today]",
    "parab_const":  "q(2-q), q = d/x_lin  device curve, fixed edge",
    "linear_ov":    "min(1, d/ov)         straight, moving edge",
    "parab_ov":     "q(2-q), q = d/ov     DEVICE FORM, moving edge",
    "parab_vsat":   "q(2-q), q = d/ov^(p/2)  vsat edge, moves less",
}
EPS = 1e-9


def simulate(u, s_up, s_dn, vt, x_lin, p, kind, n_sub=2):
    """Heun (RK2), n_sub substeps per cl.DT - the same scheme and clipping as
    cl.simulate, with the drain factor switched. Everything the loop needs is
    precomputed as arrays so the inner steps are scalar arithmetic only."""
    hu = cl.h(u, vt, p)
    hd = cl.h(1.0 - u, vt, p)
    if kind.endswith("_ov"):
        nu = np.maximum(u - vt, EPS)                 # charging device's overdrive
        nd = np.maximum((1.0 - u) - vt, EPS)         # discharging device's overdrive
    elif kind.endswith("_vsat"):
        # Sakurai-Newton: V_DSAT ~ (V_GS - V_th)^(alpha/2), so the boundary moves with
        # the gate but MORE SLOWLY than the long-channel form. alpha is the same
        # exponent as p, so this costs no extra parameter. p=2 recovers the _ov case.
        nu = np.maximum(u - vt, EPS) ** (p / 2.0)
        nd = np.maximum((1.0 - u) - vt, EPS) ** (p / 2.0)
    else:
        nu = np.full_like(hu, x_lin)
        nd = np.full_like(hd, x_lin * cl.XLIN_DN_RATIO)
    parab = kind.startswith("parab")

    v = np.empty_like(u)
    x = 0.0
    dt = cl.DT / n_sub
    for i in range(len(u)):
        a, b, c, d = s_up * hu[i], s_dn * hd[i], nu[i], nd[i]
        for _ in range(n_sub):
            if parab:
                qu = (1.0 - x) / c
                if qu > 1.0:
                    qu = 1.0
                qd = x / d
                if qd > 1.0:
                    qd = 1.0
                k1 = a * qu * (2.0 - qu) - b * qd * (2.0 - qd)
                y = x + dt * k1
                qu = (1.0 - y) / c
                if qu > 1.0:
                    qu = 1.0
                qd = y / d
                if qd > 1.0:
                    qd = 1.0
                k2 = a * qu * (2.0 - qu) - b * qd * (2.0 - qd)
            else:
                ru = (1.0 - x) / c
                rd = x / d
                k1 = a * (ru if ru < 1.0 else 1.0) - b * (rd if rd < 1.0 else 1.0)
                y = x + dt * k1
                ru = (1.0 - y) / c
                rd = y / d
                k2 = a * (ru if ru < 1.0 else 1.0) - b * (rd if rd < 1.0 else 1.0)
            x = x + 0.5 * dt * (k1 + k2)
            if x < -0.05:
                x = -0.05
            elif x > 1.05:
                x = 1.05
        v[i] = x
    return v


def simulate_chain(u, prms, kind):
    x = u
    for prm in prms:
        x = simulate(x, *prm, kind)
    return x


def fit_shared(u, v, K, kind, p=1.0):
    """K identical stages sharing their numbers; x_lin only exists for the _const kinds.
    Same optimiser budget as cl.fit_chain_shared: 3 restarts, maxiter 800."""
    n = NP_[kind]
    best = (9.0, None)

    def unpack(z):
        s_up, s_dn, vt = float(np.exp(z[0])), float(np.exp(z[1])), float(z[2])
        x_lin = float(z[3]) if n == 4 else float("nan")
        return s_up, s_dn, vt, x_lin

    def cost(z):
        s_up, s_dn, vt, x_lin = unpack(z)
        if not 0.0 <= vt <= 0.7:
            return 9.0
        if n == 4 and not 0.02 <= x_lin <= 1.5:
            return 9.0
        pred = simulate_chain(u, [(s_up, s_dn, vt, x_lin, p)] * K, kind)
        return float(np.sqrt(np.mean((pred - v) ** 2)))

    for s0 in (2.0, 8.0, 30.0):
        z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4][:n]),
                              step=[0.7, 0.7, 0.15, 0.15][:n], maxiter=800)
        if c < best[0]:
            best = (c, unpack(z))
    s_up, s_dn, vt, x_lin = best[1]
    return best[0], [(s_up, s_dn, vt, x_lin, p)] * K


def check() -> int:
    """The new integrator must reproduce cl.simulate on the baseline kind, or the
    comparison is confounded by the integrator rather than by the drain factor."""
    rng = np.random.default_rng(0)
    grid = np.arange(4.0, 21.0, cl.DT)
    worst = 0.0
    for _ in range(6):
        u = np.clip(np.interp(grid, [4, 5, 5 + rng.uniform(0.1, 6), 21], [0, 0, 1, 1]), 0, 1)
        s_up, s_dn = rng.uniform(0.5, 20), rng.uniform(0.5, 20)
        vt, x_lin = rng.uniform(0.0, 0.6), rng.uniform(0.1, 1.0)
        a = cl.simulate(u, s_up, s_dn, vt, x_lin, 1.0)
        b = simulate(u, s_up, s_dn, vt, x_lin, 1.0, "linear_const")
        worst = max(worst, float(np.abs(a - b).max()))
    print(f"  max |new - cl.simulate| over 6 random cases: {worst:.3e}")
    print("  " + ("OK - same integrator" if worst < 1e-12 else "MISMATCH - do not trust the comparison"))
    return 0 if worst < 1e-12 else 1


def run(dev: str, rows: list, kinds=KINDS, tag: str = "") -> dict:
    cfg = BUFFERS[dev]
    K, gate = cfg["K"], cfg["gate"]
    grid, runs = cl.load(dev)
    full = runs["full"]
    u_name = psp.STAGES[dev][0]
    widths = sorted(k for k in runs if k != "full")
    meas = {W: runs[W][gate] for W in widths}

    print(f"\n=== {dev}: K = {K} identical stages, {u_name[2:-1]} -> {gate[2:-1]}, "
          f"fitted at FULL SWING only")
    print(f"    {'drain factor':<46}{'n':>2}{'full rms':>10}{'s_up':>8}{'s_dn':>8}{'vt':>7}{'x_lin':>7}")

    out, preds = {}, {}
    for kind in kinds:
        c, prms = fit_shared(full[u_name], full[gate], K, kind)
        s_up, s_dn, vt, x_lin = prms[0][:4]
        xl = f"{x_lin:.3f}" if NP_[kind] == 4 else "  --"
        print(f"    {LABEL[kind]:<46}{NP_[kind]:>2}{c:>10.4f}{s_up:>8.2f}{s_dn:>8.2f}{vt:>7.3f}{xl:>7}")
        preds[kind] = {W: simulate_chain(runs[W][u_name], prms, kind) for W in widths}
        out[kind] = dict(full_rms=c, s_up=s_up, s_dn=s_dn, vt=vt,
                         x_lin=(x_lin if NP_[kind] == 4 else None), n_params=NP_[kind])

    m = grid >= 5.0
    print(f"\n    stressed gate peak, fitted at full swing only (measured in brackets)")
    print(f"    {'drain factor':<46}" + "".join(f"{W:>9}" for W in widths) + f"{'mean|err|':>11}{'rms':>8}")
    print(f"    {'measured':<46}" + "".join(f"{meas[W].max():>9.3f}" for W in widths))
    for kind in kinds:
        errs = [float(preds[kind][W].max() - meas[W].max()) for W in widths]
        rms = float(np.mean([np.sqrt(np.mean((preds[kind][W][m] - meas[W][m]) ** 2)) for W in widths]))
        mae = float(np.mean(np.abs(errs)))
        print(f"    {LABEL[kind]:<46}" + "".join(f"{preds[kind][W].max():>9.3f}" for W in widths)
              + f"{mae:>11.3f}{rms:>8.4f}")
        out[kind].update(peak_err=errs, mean_abs_peak_err=mae, mean_rms=rms)
        for W in widths:
            rows.append(dict(device=dev, K=K, kind=kind, n_params=NP_[kind], width_ps=W,
                             full_rms=round(out[kind]["full_rms"], 5),
                             meas_max=round(float(meas[W].max()), 4),
                             pred_max=round(float(preds[kind][W].max()), 4),
                             rms=round(float(np.sqrt(np.mean((preds[kind][W][m] - meas[W][m]) ** 2))), 5),
                             s_up=round(out[kind]["s_up"], 4), s_dn=round(out[kind]["s_dn"], 4),
                             vt=round(out[kind]["vt"], 4),
                             x_lin=(round(out[kind]["x_lin"], 4) if out[kind]["x_lin"] else None)))

    fig, axes = plt.subplots(1, len(widths), figsize=(3.9 * len(widths), 3.7), sharey=True)
    col = {"linear_const": "#111111", "parab_const": "#C05621",
           "linear_ov": "#2B6CA3", "parab_ov": "#B03060", "parab_vsat": "#2E8B57"}
    for j, W in enumerate(widths):
        a = axes[j]
        a.plot(grid - 5.0, meas[W], color="#111111", lw=3.0, alpha=0.35, label="measured gate")
        for kind in kinds:
            a.plot(grid - 5.0, preds[kind][W], lw=1.5, color=col[kind],
                   ls=("-", "--", "-.", ":", (0, (3, 1, 1, 1)))[KINDS.index(kind)],
                   label=f"{kind} ({NP_[kind]}p)")
        a.set_xlim(-0.2, psp.XMAX_NS[dev])
        a.set_ylim(-0.1, 1.2)
        a.set_title(f"W = {W} ps", fontweight="bold")
        a.set_xlabel("time from the input rising edge (ns)")
        a.grid(alpha=0.3)
        if j == 0:
            a.set_ylabel(f"{gate[2:-1].replace('xdut.', '')}, 0 = rest, 1 = full swing")
            a.legend(fontsize=7)
    fig.suptitle(f"{dev}: four drain factors, each fitted at full swing only, predicting the stressed gate",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / f"{dev}_device_taper{tag}.png", dpi=150)
    plt.close(fig)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", nargs="*", default=list(BUFFERS))
    ap.add_argument("--kinds", nargs="*", default=None, help="subset of drain factors to fit")
    ap.add_argument("--tag", default="", help="suffix for the output files")
    ap.add_argument("--check", action="store_true", help="verify the integrator, then stop")
    a = ap.parse_args()
    if a.check:
        return check()
    OUT.mkdir(parents=True, exist_ok=True)
    print("  integrator check:")
    if check():
        return 1
    kinds = tuple(a.kinds) if a.kinds else KINDS
    rows, summary = [], {}
    for dev in a.dev:
        summary[dev] = run(dev, rows, kinds, a.tag)
    with (OUT / f"results{a.tag}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (OUT / f"summary{a.tag}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n  wrote {OUT / 'results.csv'} and summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
