#!/usr/bin/env python3
"""What the Ku-domain fit (26) sees: the residual landscape and the search path, on ex2.

Same problem as gate_chain_prototype.fit_chain_ku for ex2 (K = 3, map shape (0.57, 0.64),
x_lin = 0.45, p = 1, C_comp 1.7 pF target cached in shape_from_file/target_ex2.npz):

  landscape.npz   rms over a grid of (s_up, v_t) at the fitted s_dn, and of (s_up, s_dn) at
                  the fitted v_t
  paths.npz       every evaluation of the three Nelder-Mead runs (starts 2, 8, 30 per ns,
                  800 iterations), so the search can be drawn

    py -3.14 results/stage_law_doc_2026-10-01/fit_search.py
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import current_limited_stage_model as cl  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "fit_search"
K, X_LIN, P = 3, 0.45, 1.0
VT_MAP, A_MAP = 0.57, 0.64
FIT = (2.19028, 2.12377, 0.52764)          # step-1 result, as_track1 pass (stage_count_from_file)


def target():
    d = np.load(HERE / "shape_from_file" / "target_ex2.npz")
    return d["u"], d["target"]


def prior(g):
    return np.clip((g - VT_MAP) / (1.0 - VT_MAP), 0.0, 1.0) ** A_MAP


def rms(s_up, s_dn, vt, u, tgt):
    if not (0.0 <= vt <= 0.7):
        return 9.0
    g = cl.simulate_chain(u, [(s_up, s_dn, vt, X_LIN, P)] * K)
    return float(np.sqrt(np.mean((prior(g) - tgt) ** 2)))


def _row(args):
    kind, a, bs = args
    u, tgt = target()
    if kind == "vt":          # a = s_up, bs = v_t values, s_dn fixed
        return [rms(a, FIT[1], b, u, tgt) for b in bs]
    return [rms(a, b, FIT[2], u, tgt) for b in bs]     # a = s_up, bs = s_dn values, v_t fixed


def _search(s0):
    """One Nelder-Mead run as fit_chain_ku does it, logging every evaluation."""
    u, tgt = target()
    log = []

    def cost(z):
        c = rms(float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), u, tgt)
        log.append((float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), c))
        return c

    z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4]), step=[0.7, 0.7, 0.15], maxiter=800)
    return s0, np.array(log), (float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), float(c))


def main() -> int:
    OUT.mkdir(exist_ok=True)
    s_up = np.exp(np.linspace(np.log(0.5), np.log(12.0), 41))
    vt = np.linspace(0.0, 0.7, 36)
    s_dn = np.exp(np.linspace(np.log(0.5), np.log(12.0), 41))
    with ProcessPoolExecutor(max_workers=6) as ex:
        paths = list(ex.map(_search, (2.0, 8.0, 30.0)))
        z_vt = np.array(list(ex.map(_row, [("vt", a, vt) for a in s_up])))
        z_dn = np.array(list(ex.map(_row, [("dn", a, s_dn) for a in s_up])))
    np.savez(OUT / "landscape.npz", s_up=s_up, vt=vt, s_dn=s_dn, rms_sup_vt=z_vt, rms_sup_sdn=z_dn,
             fit=np.array(FIT), fit_rms=rms(*FIT, *target()))
    np.savez(OUT / "paths.npz", starts=np.array([p[0] for p in paths]),
             **{f"log_{int(p[0])}": p[1] for p in paths},
             **{f"end_{int(p[0])}": np.array(p[2]) for p in paths})
    for s0, log, end in paths:
        print(f"start {s0:g}/ns: {len(log)} evaluations -> s_up {end[0]:.3f} s_dn {end[1]:.3f} vt {end[2]:.3f} rms {end[3]:.4f}")
    print(f"landscape: {z_vt.shape} + {z_dn.shape}, min {z_vt.min():.4f} / {z_dn.min():.4f}; fit rms {rms(*FIT, *target()):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
