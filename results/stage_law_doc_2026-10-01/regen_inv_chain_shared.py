# -*- coding: utf-8 -*-
"""Regenerate inv_chain's identical-stage table with the CURRENT integrator, one optimiser
start per process.

`results/current_limited_stages_2026-09-10/inv_chain_chain_shared_K.csv` was written on
09-09 23:39; `scripts/current_limited_stage_model.py` was last changed on 09-10 12:30, when
explicit Euler was replaced by Heun because Euler biased inv_chain's fast stages (see the
`simulate` docstring). So that CSV is Euler-era and no longer reproduces
(`results/device_taper_2026-09-28/FINDINGS.md` 6b).

`cl.fit_chain_shared` runs three Nelder-Mead starts in sequence and keeps the best. This
runs ONE start (same cost, same bounds, same budget) so the three can run in parallel:

    py -3.14 regen_inv_chain_shared.py fit 5 8.0      # K = 5, start s0 = 8  -> fit_K5_s8.json
    py -3.14 regen_inv_chain_shared.py collect        # best start per K -> the CSV

The result is what `cl.fit_chain_shared` returns, by construction: best over the same starts.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np                              # noqa: E402
import current_limited_stage_model as cl        # noqa: E402
import predriver_stage_probe as psp             # noqa: E402

HERE = Path(__file__).resolve().parent
DEV, GATE, STARTS = "inv_chain", "v(xdut.vout7)", (2.0, 8.0, 30.0)


def one_start(K: int, s0: float):
    grid, runs = cl.load(DEV)
    u, v = runs["full"][psp.STAGES[DEV][0]], runs["full"][GATE]

    def cost(z):
        s_up, s_dn, vt, x_lin = np.exp(z[0]), np.exp(z[1]), z[2], z[3]
        if not (0.0 <= vt <= 0.7 and 0.02 <= x_lin <= 1.5):
            return 9.0
        return float(np.sqrt(np.mean((cl.simulate_chain(u, [(s_up, s_dn, vt, x_lin, 1.0)] * K) - v) ** 2)))

    z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4]),
                          step=[0.7, 0.7, 0.15, 0.15], maxiter=800)
    out = dict(K=K, s0=s0, rms=c, s_up=float(np.exp(z[0])), s_dn=float(np.exp(z[1])),
               vt=float(z[2]), x_lin=float(z[3]))
    (HERE / f"fit_K{K}_s{s0:g}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(out)


def collect():
    grid, runs = cl.load(DEV)
    u_name = psp.STAGES[DEV][0]
    widths = sorted(k for k in runs if k != "full")
    rows = []
    for K in (3, 5, 7, 9):
        fits = [json.loads(p.read_text()) for p in sorted(HERE.glob(f"fit_K{K}_s*.json"))]
        if len(fits) < len(STARTS):
            print(f"K={K}: only {len(fits)} of {len(STARTS)} starts present - skipped")
            continue
        # cl.fit_chain_shared keeps the FIRST start that is strictly best, in STARTS order
        best = min(sorted(fits, key=lambda f: STARTS.index(f["s0"])), key=lambda f: f["rms"])
        prm = [(best["s_up"], best["s_dn"], best["vt"], best["x_lin"], 1.0)] * K
        print(f"K={K}: full-swing rms {best['rms']:.4f}  s_up {best['s_up']:.3f} s_dn {best['s_dn']:.3f} "
              f"vt {best['vt']:.3f} x_lin {best['x_lin']:.3f}  (start s0={best['s0']:g})")
        m = grid >= 5.0
        for W in widths:
            meas = runs[W][GATE]
            pred = cl.simulate_chain(runs[W][u_name], prm)
            lin = cl.linear_pred(grid, runs["full"][GATE], W / 1e3)
            rms = float(np.sqrt(np.mean((pred[m] - meas[m]) ** 2)))
            print(f"    {W:>5}  meas {meas.max():.3f}  pred {pred.max():.3f}  lin {lin.max():.3f}  rms {rms:.4f}")
            rows.append(dict(device=DEV, K=K, width_ps=W, meas_max=round(float(meas.max()), 3),
                             pred_max=round(float(pred.max()), 3), lin_max=round(float(lin.max()), 3),
                             rms=round(rms, 4), full_rms=round(best["rms"], 4)))
    with (HERE / "inv_chain_chain_shared_K_regenerated.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote inv_chain_chain_shared_K_regenerated.csv")


if __name__ == "__main__":
    if sys.argv[1] == "fit":
        one_start(int(sys.argv[2]), float(sys.argv[3]))
    else:
        collect()
