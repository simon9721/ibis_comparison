#!/usr/bin/env python3
"""The fit (26) seen in the file-only setting, for the paper's explanatory figures (v7).

The paper's earlier versions explained the fit with a map measured on ex2's probed gate and the
netlist's C_comp, a setting the method never uses. This recomputes what those figures show in the
setting the procedure actually builds, ex2 at the C_comp estimated from the file (2.64 pF) with the
selected map shape (0.5, 0.7) and K = 3, and inv_chain at 0.66 pF with (0.4, 0.6) and K = 7 (the
candidate selected with x_lin = 0.45 on every buffer, stage_law_model_checks_2026-10-22):

    fit_search_fileonly/landscape.npz   rms of (26) over (s_up, v_t) at the fitted s_dn and over
                                        (s_up, s_dn) at the fitted v_t; v_t extended to 0.95 so the
                                        optimum beyond the 0.7 bound of the method is visible
    fit_search_fileonly/paths.npz       every evaluation of the three Nelder-Mead runs (starts 2, 8,
                                        30 per ns) with the method's bound, and one run with the
                                        bound at 0.95
    shape_fileonly/target_<dev>.npz     the chain input u(t) and the normalized target (25)
    shape_fileonly/shape_<dev>_<vt>_<a>.json   the fit through each of six map shapes

    py -3.14 results/stage_law_doc_2026-10-01/fileonly_fit_data.py
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import current_limited_stage_model as cl  # noqa: E402

HERE = Path(__file__).resolve().parent
SC = ROOT / "results" / "stage_count_from_file_2026-09-21"
OUT_SEARCH = HERE / "fit_search_fileonly"
OUT_SHAPE = HERE / "shape_fileonly"
X_LIN, P = 0.45, 1.0
SETTING = {"ex2": dict(cc=2.64, K=3, shape=(0.5, 0.7)), "inv_chain": dict(cc=0.66, K=7, shape=(0.4, 0.6))}
SHAPES = [(0.3, 0.6), (0.4, 0.6), (0.4, 0.9), (0.5, 0.7), (0.6, 0.6), (0.6, 0.9)]


def prior(g, vt, a):
    return np.clip((g - vt) / (1.0 - vt), 0.0, 1.0) ** a


def target(dev):
    z = np.load(OUT_SHAPE / f"target_{dev}.npz")
    return z["u"], z["target"]


def make_targets():
    import build_stage_law_doc_figures as figs
    OUT_SHAPE.mkdir(exist_ok=True)
    for dev, s in SETTING.items():
        raw = SC / "knee_models" / f"{dev}_c{s['cc']:g}" / "shipped" / "full" / "run.raw"
        grid, u, tgt, t_on = figs.shipped_target(dev, raw)
        np.savez(OUT_SHAPE / f"target_{dev}.npz", grid=grid, u=u, target=tgt, t_on=t_on)
        print(f"target {dev}: {len(grid)} samples, edge at {t_on:.3f} ns")


def rms(s_up, s_dn, vt, u, tgt, K, shape, vt_max=0.7):
    if not (0.0 <= vt <= vt_max):
        return 9.0
    g = cl.simulate_chain(u, [(s_up, s_dn, vt, X_LIN, P)] * K)
    return float(np.sqrt(np.mean((prior(g, *shape) - tgt) ** 2)))


def _row(args):
    kind, a, bs, fit = args
    u, tgt = target("ex2")
    s = SETTING["ex2"]
    if kind == "vt":
        return [rms(a, fit[1], b, u, tgt, s["K"], s["shape"], vt_max=1.0) for b in bs]
    return [rms(a, b, fit[2], u, tgt, s["K"], s["shape"]) for b in bs]


def _search(args):
    """One Nelder-Mead run as fit_chain_ku does it, logging every evaluation."""
    s0, vt_max = args
    u, tgt = target("ex2")
    s = SETTING["ex2"]
    log = []

    def cost(z):
        c = rms(float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), u, tgt, s["K"], s["shape"], vt_max)
        log.append((float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), c))
        return c

    z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4]), step=[0.7, 0.7, 0.15], maxiter=800)
    return s0, vt_max, np.array(log), (float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), float(c))


def _shape(args):
    dev, vt_m, a_m = args
    u, tgt = target(dev)
    K = SETTING[dev]["K"]
    best = (9.0, None)
    for s0 in (2.0, 8.0, 30.0):
        z, c = cl.nelder_mead(lambda z: rms(float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), u, tgt, K, (vt_m, a_m)),
                              np.array([np.log(s0), np.log(s0), 0.4]), step=[0.7, 0.7, 0.15], maxiter=800)
        if c < best[0]:
            best = (c, (float(np.exp(z[0])), float(np.exp(z[1])), float(z[2])))
    out = dict(dev=dev, K=K, cc=SETTING[dev]["cc"], vt_map=vt_m, a=a_m, rms=best[0], s_up=best[1][0], s_dn=best[1][1], vt=best[1][2])
    (OUT_SHAPE / f"shape_{dev}_{vt_m:g}_{a_m:g}.json").write_text(json.dumps(out), encoding="utf-8")
    return out


def main() -> int:
    make_targets()
    OUT_SEARCH.mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=6) as ex:
        shapes = list(ex.map(_shape, [(dev, vt, a) for dev in SETTING for vt, a in SHAPES]))
        paths = list(ex.map(_search, [(2.0, 0.7), (8.0, 0.7), (30.0, 0.7), (2.0, 0.95)]))
        fit = min((p for p in paths if p[1] == 0.7), key=lambda p: p[3][3])[3]
        s_up = np.exp(np.linspace(np.log(0.5), np.log(12.0), 41))
        vt = np.linspace(0.0, 0.95, 39)
        s_dn = np.exp(np.linspace(np.log(0.5), np.log(12.0), 41))
        z_vt = np.array(list(ex.map(_row, [("vt", a, vt, fit) for a in s_up])))
        z_dn = np.array(list(ex.map(_row, [("dn", a, s_dn, fit) for a in s_up])))
    u, tgt = target("ex2")
    s = SETTING["ex2"]
    np.savez(OUT_SEARCH / "landscape.npz", s_up=s_up, vt=vt, s_dn=s_dn, rms_sup_vt=z_vt, rms_sup_sdn=z_dn,
             fit=np.array(fit[:3]), fit_rms=fit[3], vt_bound=0.7)
    np.savez(OUT_SEARCH / "paths.npz", starts=np.array([p[0] for p in paths if p[1] == 0.7]),
             **{f"log_{int(p[0])}": p[2] for p in paths if p[1] == 0.7},
             **{f"end_{int(p[0])}": np.array(p[3]) for p in paths if p[1] == 0.7},
             log_free=[p for p in paths if p[1] == 0.95][0][2], end_free=np.array([p for p in paths if p[1] == 0.95][0][3]))
    for s0, vmax, log, end in paths:
        print(f"start {s0:g}/ns, v_t <= {vmax}: {len(log)} evaluations -> s_up {end[0]:.3f} s_dn {end[1]:.3f} vt {end[2]:.3f} rms {end[3]:.4f}")
    print(f"landscape: {z_vt.shape} + {z_dn.shape}, min {z_vt.min():.4f} / {z_dn.min():.4f}")
    for r in sorted(shapes, key=lambda r: (r["dev"], r["rms"])):
        print(f"  {r['dev']:9s} K={r['K']} shape ({r['vt_map']:.1f}, {r['a']:.1f}): rms {r['rms']:.4f}  s_up {r['s_up']:.2f} s_dn {r['s_dn']:.2f} vt {r['vt']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
