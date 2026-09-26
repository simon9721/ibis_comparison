#!/usr/bin/env python3
"""Open-drain: the transistor's own Kd against its own gate, and the prior that fits it.

The chain recipe on the open-drain ex2 (`opendrain_chain_build.py`) reproduced
the calibration point but not the depth law: the pad's cliff between 620 and
750 ps is much sharper on the transistor than on any chain. The gate-state
bench already recorded n4 and Kd at the pad minimum for every width, and those
pairs say the NMOS turns on far below the ex2 pull-up prior's threshold of
0.52. This measures the map properly: single-fixture Kd(t) solved from the
bench run (C_comp as given) against the normalised n4, full swing and every
stressed width on one axis, and a three-parameter prior fitted to it.

    py -3.14 scripts/opendrain_silicon_map.py --variant base --ccomp 3.0
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import FixtureWaveform  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402
import opendrain_chain_build as ocb  # noqa: E402

R = ROOT / "results"
OUT = R / "opendrain_silicon_map_2026-09-10"


def kd_solve(data, t_ns, pad):
    time = np.arange(t_ns[0], t_ns[-1], 0.005) * 1e-9
    v = np.interp(time * 1e9, t_ns, pad)
    wave = FixtureWaveform(np.column_stack([time, v, v, v]), [ocb.SUP] * 3, ocb.R_PU)
    pu, pd, pc, gc, rf, cc, cf = pb.generating_current_data(data, time, 1, wave)
    num = gc + pc + rf - cc - cf
    kd = np.where(np.abs(pd) > 1e-6, num / np.where(np.abs(pd) > 1e-6, pd, 1.0), np.nan)
    return time * 1e9, kd


def fit_prior3_wide(g, kd):
    """Grid search with the threshold allowed down to 0 (the pull-up prior's grid starts at 0.3)."""
    best = (9.0, None, None, None)
    for vt in np.arange(0.0, 0.61, 0.01):
        for gs in np.arange(0.70, 1.001, 0.01):
            if gs <= vt + 0.1:
                continue
            for al in np.arange(0.6, 2.01, 0.05):
                r = float(np.sqrt(np.mean((pm.prior3(g, vt, al, gs) - kd) ** 2)))
                if r < best[0]:
                    best = (r, vt, al, gs)
    return best[1], best[2], best[3], best[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(ocb.VARIANTS), default="base")
    ap.add_argument("--ccomp", type=float, default=3.0, help="C_comp (pF) used in the single-fixture solve; the loop closes at 3.0 on the base OD")
    args = ap.parse_args()
    ibis, _, widths, _ = ocb.VARIANTS[args.variant]
    txt = re.sub(r"^C_comp\s+.*$", f"C_comp {args.ccomp:.4f}pF {args.ccomp:.4f}pF {args.ccomp:.4f}pF", ibis.read_text(errors="ignore"), count=1, flags=re.M)
    OUT.mkdir(parents=True, exist_ok=True)
    ib = OUT / f"{args.variant}_c{args.ccomp:g}.ibs"
    ib.write_text(txt, encoding="utf-8")
    import gate_ramp_prototype as gp
    model, comp = gp.ibis_names(ib)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ib)), model_name=model, component_name=comp)

    # n4 normalisation from the full-swing run: rest (input high, pad released) -> 0, settled low -> 1
    raw10 = sl.parse_hspice_tr0(ocb.GATESTATE / args.variant / ocb.wdir(10.0) / "transistor" / "run.tr0")
    t10, n4_10 = sl.time_ns(raw10), np.asarray(raw10["v(xref.n4)"], float)
    n_rest, n_on = float(np.interp(4.5, t10, n4_10)), float(np.interp(12.0, t10, n4_10))
    print(f"  {args.variant}: n4 rest {n_rest:.3f} V, settled on {n_on:.3f} V (C_comp {args.ccomp} pF in the solve)")

    fig, ax = plt.subplots(1, 2, figsize=(14, 6))
    allg, allk = [], []
    cmap = plt.get_cmap("viridis")
    for i, W in enumerate(widths):
        raw = sl.parse_hspice_tr0(ocb.GATESTATE / args.variant / ocb.wdir(W) / "transistor" / "run.tr0")
        t, pad, n4 = sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float), np.asarray(raw["v(xref.n4)"], float)
        tk, kd = kd_solve(data, t, pad)
        g = np.interp(tk, t, (n4 - n_rest) / (n_on - n_rest))
        # the pull-down leg only, 90 ps after each input edge (the two-fixture rule; here the pad is
        # single-fixture so the solve is cleaner, but the input edge itself still spikes)
        lo, hi = 5.09, min(5.0 + W + 2.5, ocb.STOP - 0.2)
        m = (tk > lo) & (tk < hi) & np.isfinite(kd)
        if W >= 5.0:
            m &= (tk < 5.0 + W - 0.05)
        c = cmap(i / max(1, len(widths) - 1))
        ax[0].plot(g[m], kd[m], color=c, lw=1.2, label=f"W {W * 1e3:.0f} ps")
        allg.append(g[m])
        allk.append(kd[m])
    g_all, k_all = np.concatenate(allg), np.concatenate(allk)
    keep = (g_all >= 0) & (g_all <= 1.05) & (k_all > -0.2) & (k_all < 1.3)
    vt, al, gs, rms = fit_prior3_wide(g_all[keep], np.clip(k_all[keep], 0, 1))
    fam = pm.prior3(np.linspace(0, 1, 200), *ocb.FAMILY_PRIOR["ex2"])
    grid = np.linspace(0, 1, 200)
    ax[0].plot(grid, pm.prior3(grid, vt, al, gs), color="#C0392B", lw=2.5, ls="--", label=f"fit: vt {vt:.2f} α {al:.2f} gs {gs:.2f} (rms {rms:.3f})")
    ax[0].plot(grid, fam, color="#7F8C8D", lw=2.0, ls=":", label="ex2 pull-up prior (0.52 / 1.10 / 0.91)")
    ax[0].set_xlabel("n4, normalised (0 = released, 1 = settled on)")
    ax[0].set_ylabel("transistor Kd (single-fixture solve)")
    ax[0].set_title(f"open-drain {args.variant}: Kd against its own gate, all widths")
    ax[0].set_ylim(-0.1, 1.2)
    ax[0].grid(alpha=0.3)
    ax[0].legend(fontsize=7)
    # right: the per-width pairs at the pad minimum (the bench's own numbers)
    import csv
    with (ocb.GATESTATE / args.variant / "cases.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    gm = [(float(r["n4_at_min"]) - n_rest) / (n_on - n_rest) for r in rows]
    km = [float(r["si_kd_at_min"]) for r in rows]
    ax[1].plot(gm, km, "ko", ms=7, label="at the pad minimum, each width")
    ax[1].plot(grid, pm.prior3(grid, vt, al, gs), color="#C0392B", lw=2.5, ls="--", label="fit")
    ax[1].plot(grid, fam, color="#7F8C8D", lw=2.0, ls=":", label="ex2 pull-up prior")
    ax[1].set_xlabel("n4 at the pad minimum, normalised")
    ax[1].set_ylabel("Kd at the pad minimum")
    ax[1].set_title("the same map, one point per width")
    ax[1].grid(alpha=0.3)
    ax[1].legend(fontsize=8)
    fig.suptitle("The open-drain NMOS map is not the pull-up map: it turns on much earlier in its gate swing", fontsize=13, fontweight="bold")
    fig.tight_layout()
    p = OUT / f"{args.variant}_c{args.ccomp:g}_silicon_kd_map.png"
    fig.savefig(p, dpi=150)
    print(f"  prior3 fit to the silicon Kd map: vt {vt:.2f} alpha {al:.2f} gs {gs:.2f} rms {rms:.3f}")
    print(f"  wrote {p}")
    (OUT / f"{args.variant}_c{args.ccomp:g}_prior3.txt").write_text(f"{vt:.3f} {al:.3f} {gs:.3f} rms {rms:.4f}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
