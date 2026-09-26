#!/usr/bin/env python3
"""Can the (map, gate) pair be recovered from the IBIS tables plus a physics prior?

The last round proved the output stage is a static Ku(g) map of one gate node,
and that the IBIS tables only pin Ku(t) at full swing — so any monotone
re-parametrisation of (map, gate) fits full swing, and only the right pair
reproduces stress. This tests a way to break the tie without silicon data:

1. **Prior**: a MOSFET-shaped map, Ku(g) = ((g - vt) / (1 - vt))^alpha for
   g > vt, else 0. Fit it to the three silicon maps (two-fixture Ku against the
   real gate at full swing). If one family with two numbers fits all three, the
   map can be assumed.
2. **Derived gate**: invert the prior on the shipped model's full-swing Ku(t):
   g_ibis(t) = vt + (1 - vt) * Ku(t)^(1/alpha). Compare with the real gate.
3. **Stressed gate by superposition**: g(t) = g_rise(t - t_on) + g_fall(t - t_off) - 1
   from the derived step responses. Compare with the real stressed gate and with
   the shipped model's GUP at the same widths.

Needs: predriver_stage_probe runs, full_swing_fixtures (silicon_map_replay
--source full), and the shipped builds under gate_cascade_prototype_2026-09-09.

    py -3.14 scripts/physics_map_gate_from_ibis.py
"""
from __future__ import annotations

import csv
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
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import silicon_map_replay as smr  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402

R = ROOT / "results"
G = R / "gate_cascade_prototype_2026-09-09"
OUT = R / "physics_map_gate_2026-09-10"
# (model dir, C_comp for the silicon solve, full-swing fixture dir)
DEV = {
    "ex2": ("ex2_c1.7", 1.75, smr.FSFIX / "ex2"),
    "inv_chain": ("inv_chain_c0.6", 0.6, smr.FSFIX / "inv_chain"),
    "io_buf": ("io_buf", None, R / "full_swing_silicon_kukd_2026-09-07"),
}
COL = {"ex2": "#B03060", "inv_chain": "#2E8B57", "io_buf": "#111111"}
GRIDG = np.linspace(0.0, 1.0, 1001)


def prior(g, vt, alpha):
    x = np.clip((g - vt) / (1.0 - vt), 0.0, 1.0)
    return x ** alpha


def prior3(g, vt, alpha, gs):
    """Threshold vt, power alpha, and saturation at gs < 1 (the real maps reach Ku = 1
    before the gate reaches its rail)."""
    x = np.clip((g - vt) / (gs - vt), 0.0, 1.0)
    return x ** alpha


def fit_prior3(g, ku):
    best = (9.0, None, None, None)
    for vt in np.arange(0.3, 0.61, 0.01):
        for gs in np.arange(0.80, 1.001, 0.01):
            if gs <= vt + 0.1:
                continue
            for al in np.arange(0.6, 2.01, 0.05):
                r = float(np.sqrt(np.mean((prior3(g, vt, al, gs) - ku) ** 2)))
                if r < best[0]:
                    best = (r, vt, al, gs)
    return best[1], best[2], best[3], best[0]


def invert(ku, vt, alpha):
    return vt + (1.0 - vt) * np.clip(ku, 0.0, 1.0) ** (1.0 / alpha)


def fit_prior(g, ku):
    """Grid search vt, alpha minimising rms over g in [vt, 1]; weights favour the working range."""
    best = (9.0, None, None)
    for vt in np.arange(0.0, 0.61, 0.01):
        for al in np.arange(0.6, 3.01, 0.02):
            e = prior(g, vt, al) - ku
            r = float(np.sqrt(np.mean(e ** 2)))
            if r < best[0]:
                best = (r, vt, al)
    return best[1], best[2], best[0]


def below_threshold(t, g, kun, vt, eps=0.02):
    """Below Ku ~ 0 the gate is invisible to the tables. Continue each edge with the slope it
    has just above threshold, so the derived step response reaches 0 instead of parking at vt."""
    g = np.where(kun <= 0.003, 0.0, g)  # where the tables show no Ku at all, the gate is "off" (0), not vt
    vis = g > vt + 0.03                 # "visible": the derived gate is clear of the threshold
    # rising edge: first visible sample after 4.9 ns
    for t0, t1, sign in ((4.9, 14.0, +1), (14.9, 21.5, -1)):
        win = (t >= t0) & (t <= t1)
        idx = np.where(win & (vis if sign > 0 else ~vis))[0]
        if not len(idx):
            continue
        i = idx[0]
        j = np.searchsorted(t, t[i] + 0.02)
        slope = (g[j] - g[i]) / max(t[j] - t[i], 1e-6) if sign > 0 else (g[i] - g[max(i - 5, 0)]) / max(t[i] - t[max(i - 5, 0)], 1e-6)
        if sign > 0:
            pre = win & (t < t[i])
            g[pre] = np.clip(vt + slope * (t[pre] - t[i]), 0.0, 1.0)
        else:
            post = win & (t >= t[i])
            g[post] = np.clip(vt + slope * (t[post] - t[i]), 0.0, 1.0)
    return g


def t_cross(t, y, level, t0=0.0):
    i = np.where((t >= t0) & (y >= level))[0]
    return float(t[i[0]]) if len(i) else float("nan")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    fig, axes = plt.subplots(3, 3, figsize=(17, 13))
    for col, (dev, (mdir, cc, fsfix)) in enumerate(DEV.items()):
        sup, ibis = gp.VARIANTS[dev]
        gp.VARIANT_NAME = dev
        model, comp = gp.ibis_names(ibis)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
        if cc:
            data.c_comp = [cc * 1e-12] * 3
        node_u, _ = gr.GATES[dev]
        # --- silicon map at full swing (rising branch) --------------------------
        lo, hi = smr.fixture(fsfix / "vfix_0/run.tr0"), smr.fixture(fsfix / "vfix_vcc/run.tr0")
        s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
        ts, ku_si = s[:, 0] * 1e9, s[:, 1]
        tg, g_real = gr.real_gate(dev, 0, node_u)
        ku_rise, ku_fall, _, _ = smr.silicon_maps(ts, ku_si, s[:, 2], tg, g_real, 5.0, 15.0)
        gg, kk = ku_rise
        m = (kk >= 0.10) & (gg <= 0.995)          # the working range: below Ku 0.1 the pad does not care
        vt, al, rms = fit_prior(gg[m], kk[m])
        lv = np.array([0.2, 0.4, 0.6, 0.8, 0.9])
        g_at, g_pr = np.interp(lv, kk[m], gg[m]), invert(lv, vt, al)
        print(f"\n=== {dev}: silicon Ku(g) at full swing fitted by ((g-vt)/(1-vt))^alpha: vt={vt:.2f} alpha={al:.2f} rms(Ku>=0.1)={rms:.3f}")
        print("    gate at Ku = 0.2/0.4/0.6/0.8/0.9   real: " + " ".join(f"{x:.2f}" for x in g_at)
              + "   prior: " + " ".join(f"{x:.2f}" for x in g_pr))
        vt3, al3, gs3, rms3 = fit_prior3(gg[m], kk[m])
        g_pr3 = np.interp(lv, prior3(GRIDG, vt3, al3, gs3), GRIDG)
        print(f"    3-parameter prior: vt={vt3:.2f} alpha={al3:.2f} gs={gs3:.2f} rms={rms3:.3f}   gate at those Ku: "
              + " ".join(f"{x:.2f}" for x in g_pr3))
        rows.append(dict(device=dev, prior3_vt=round(vt3, 2), prior3_alpha=round(al3, 2), prior3_gs=round(gs3, 2), prior3_rms=round(rms3, 3)))
        # --- derived gate from the shipped model's full-swing Ku(t) ------------
        ship = (G / mdir / "shipped/driver.sub").read_text(encoding="utf-8")
        full = gp.run_ours(G / mdir / "shipped/full", ship, sup, 10.0)
        tf = full["t"]
        kb = full["kugate_base"]                      # the gate part only: no residual transient
        k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
        kuf = np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0)
        g_ibis = invert(kuf, vt, al)
        g_ibis = below_threshold(tf, g_ibis, kuf, vt)
        grid = np.arange(4.8, 20.0, 0.002)
        gi, gr_ = np.interp(grid, tf, g_ibis), np.interp(grid, tg, g_real)
        # rise: real gate vs derived, t50 and 10-90 from the 5 ns edge
        def stats(y, t0):
            tt = grid - t0
            return (t_cross(tt, y, 0.5, 0.0) * 1e3, (t_cross(tt, y, 0.9, 0.0) - t_cross(tt, y, 0.1, 0.0)) * 1e3)
        r50, r1090 = stats(gr_, 5.0)
        i50, i1090 = stats(gi, 5.0)
        f_real = 1 - gr_
        f_ibis = 1 - gi
        fr50, fr1090 = stats(np.where(grid > 14.9, f_real, 0), 15.0)
        fi50, fi1090 = stats(np.where(grid > 14.9, f_ibis, 0), 15.0)
        win = (grid > 5.0) & (grid < 8.0)
        rms_gate = float(np.sqrt(np.mean((gi[win] - gr_[win]) ** 2)))
        print(f"    real gate:    rise t50 {r50:.0f} ps, 10-90 {r1090:.0f}; fall t50 {fr50:.0f}, 10-90 {fr1090:.0f}")
        print(f"    derived gate: rise t50 {i50:.0f} ps, 10-90 {i1090:.0f}; fall t50 {fi50:.0f}, 10-90 {fi1090:.0f}   rms(5-8 ns) {rms_gate:.3f}")
        r0 = lambda x: None if np.isnan(x) else round(x)   # noqa: E731
        rows.append(dict(device=dev, vt=round(vt, 2), alpha=round(al, 2), map_rms=round(rms, 3),
                         real_t50_rise=r0(r50), real_1090_rise=r0(r1090), derived_t50_rise=r0(i50), derived_1090_rise=r0(i1090),
                         real_t50_fall=r0(fr50), derived_t50_fall=r0(fi50), gate_rms_5_8ns=round(rms_gate, 3)))
        a = axes[0][col]
        a.plot(gg, kk, color=COL[dev], lw=2.5, label="silicon Ku(g), full swing")
        a.plot(gg, prior(gg, vt, al), color="#C05621", lw=1.8, ls="--", label=f"prior vt={vt:.2f}, alpha={al:.2f} (rms {rms:.3f})")
        a.set_title(f"{dev}: the map and its MOSFET-shaped fit", fontweight="bold")
        a.set_xlabel("gate, 0 = off, 1 = on")
        a.set_ylabel("Ku")
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
        b = axes[1][col]
        b.plot(grid - 5.0, gr_, color="#111111", lw=2.5, label="real gate (transistor node)")
        b.plot(grid - 5.0, gi, color=COL[dev], lw=1.8, ls="--", label="gate derived from IBIS Ku(t) through the prior")
        b.plot(grid - 5.0, np.interp(grid, tf, full["gup"]), color="#8A8A8A", lw=1.2, ls=":", label="shipped model GUP")
        b.set_xlim(-0.2, {"ex2": 3.0, "inv_chain": 0.6, "io_buf": 4.0}[dev])
        b.set_title(f"{dev}: full-swing rise, the gate the tables imply", fontweight="bold")
        b.set_xlabel("time from the input edge (ns)")
        b.set_ylabel("gate")
        b.grid(alpha=0.3)
        b.legend(fontsize=8)
        # --- stressed gate by superposition of the derived step responses --------
        tau = np.arange(-0.2, 9.0, 0.002)
        s_rise = np.interp(tau + 5.0, tf, g_ibis)
        s_fall = np.interp(tau + 15.0, tf, g_ibis)
        cs = gp.cases(dev)
        c = axes[2][col]
        print(f"    {'W ps':>6}{'real max':>9}{'superpos max':>13}{'shipped GUP max':>16}{'real t50':>9}{'superpos t50':>13}{'shipped t50':>12}"
              f" | {'Ku si max':>10}{'Ku prior(sup)':>14}{'Ku shipped':>11}")
        for k, (depth, w, d) in enumerate(cs):
            tw, gw = gr.real_gate(dev, depth, node_u)
            rev = 5.0 + w
            g2 = np.arange(4.8, rev + 3.0, 0.002)
            real = np.interp(g2, tw, gw)
            pred = np.interp(g2 - 5.0, tau, s_rise, left=0.0) + np.interp(g2 - rev, tau, s_fall, left=1.0) - 1.0
            shp = gp.run_ours(G / mdir / "shipped" / f"d{depth}", ship, sup, w)
            gs = np.interp(g2, shp["t"], shp["gup"])
            t50 = lambda y: (t_cross(g2, y, 0.5 * y.max(), 5.0) - 5.0) * 1e3
            # the transistor's own Ku in this stressed event (matrix fixtures), the shipped model's Ku, and the prior on the superposed gate
            fxd = smr.FIX / dev / f"short_high_w{depth}ps"
            ss = solve_silicon_kukd(data, smr.fixture(fxd / "vfix_0/run.tr0"), smr.fixture(fxd / "vfix_vcc/run.tr0"), sup, uniform_ps=5.0)
            tks, kks = ss[:, 0] * 1e9, ss[:, 1]
            mm = (tks > rev + 0.09) & (tks < rev + 2.5)
            ku_si_max = float(np.max(kks[mm])) if mm.any() else float("nan")
            ku_sup = prior(pred, vt, al)
            ku_shp = np.interp(g2, shp["t"], shp["ku"])
            m2 = g2 > rev + 0.09
            print(f"    {depth:>6}{real.max():>9.3f}{pred.max():>13.3f}{gs.max():>16.3f}{t50(real):>9.0f}{t50(pred):>13.0f}{t50(gs):>12.0f}"
                  f" | {ku_si_max:>10.3f}{ku_sup[m2].max():>14.3f}{ku_shp[m2].max():>11.3f}")
            rows.append(dict(device=dev, width_ps=depth, real_max=round(float(real.max()), 3), superpos_max=round(float(pred.max()), 3),
                             shipped_gup_max=round(float(gs.max()), 3), real_t50=r0(t50(real)), superpos_t50=r0(t50(pred)), shipped_t50=r0(t50(gs))))
            if k in (0, len(cs) // 2, len(cs) - 1):
                lw = 2.5 if k == len(cs) // 2 else 1.4
                c.plot(g2 - 5.0, real, color="#111111", lw=lw, label="real gate" if k == 0 else None)
                c.plot(g2 - 5.0, pred, color=COL[dev], lw=lw, ls="--", label="superposition of derived steps" if k == 0 else None)
                c.plot(g2 - 5.0, gs, color="#8A8A8A", lw=lw * 0.8, ls=":", label="shipped model GUP" if k == 0 else None)
        c.set_xlim(-0.2, {"ex2": 4.0, "inv_chain": 1.0, "io_buf": 5.5}[dev])
        c.set_title(f"{dev}: stressed gate, shallowest / middle / deepest width", fontweight="bold")
        c.set_xlabel("time from the input rising edge (ns)")
        c.set_ylabel("gate")
        c.grid(alpha=0.3)
        c.legend(fontsize=8)
    fig.suptitle("From the IBIS tables to the gate: a MOSFET-shaped map, the gate it implies, and superposition under stress",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "physics_map_gate.png", dpi=150)
    plt.close(fig)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with (OUT / "results.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=keys)
        wri.writeheader()
        wri.writerows(rows)
    print(f"\n  figure: {OUT / 'physics_map_gate.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
