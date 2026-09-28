#!/usr/bin/env python3
"""Does the device taper survive the Ku-domain fit - the one track 1 actually uses?

`results/device_taper_2026-09-28` compared seven drain factors on the GATE-domain bench:
stages fitted against the probed transistor gate. That needs the transistor. Track 1 fits
in the **Ku domain**: it drives K identical stages from a comparator, reads the last stage
through an assumed map, and compares the result against the file's own full-swing Ku(t)
(`gate_chain_prototype.fit_chain_ku`). Nothing about the gate is observable.

Two questions the gate-domain bench could not answer:

  1. Does the Sakurai-Newton boundary `x0 * D^(p/2)` fit Ku(t) as well as today's
     `min(1, d/x_lin)`?
  2. Is `x0` BETTER DETERMINED here than `x_lin` is? `docs/stage_law_walkthrough.md` 5 says a
     free `x_lin` lands anywhere in 0.02-1.50 in this domain. If a drive-tied boundary is
     pinned down where a constant is not, that is the argument for adopting it - and the
     measured V_D0/V_DD (0.23-0.42, `device_alpha_extract.py`) says where it should land.

The target is `v(x1.kugate_base)` from a full-swing ngspice run of the SHIPPED pybis2spice
subcircuit: the gate-driven part of Ku, direction-selected, residual excluded, normalised
rest->on. Identical to what `fit_chain_ku` uses, so the baseline row reproduces the recipe.

    py -3.14 scripts/device_taper_ku.py --dev ex2
    py -3.14 scripts/device_taper_ku.py                # both

Output: results/device_taper_2026-09-28/ku_domain/
"""
from __future__ import annotations

import argparse
import csv
import re
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

import current_limited_stage_model as cl  # noqa: E402
import device_taper_probe as dt  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402

OUT = ROOT / "results" / "device_taper_2026-09-28" / "ku_domain"

# the existing track-1 build of each buffer (stage_count_from_file.BUFFERS), so the
# baseline row is the shipped configuration rather than something new
BUFFERS = {
    "ex2":       dict(cc=1.7, prior=(0.57, 0.64), K=3),
    "inv_chain": dict(cc=0.6, prior=(0.49, 0.60), K=7),
}
KINDS = ("linear_const", "parab_const", "linear_snx0", "parab_snx0", "parab_vsat")


def shipped_ku(dev: str, cc: float):
    """Build the shipped subcircuit with C_comp rewritten, run it full swing, return
    (grid, normalised Ku target). Mirrors gate_chain_prototype's own setup."""
    from pybis2spice import pybis2spice as pb
    from pybis2spice import subcircuit

    gp.VARIANT_NAME = dev
    sup, ibis = gp.VARIANTS[dev]
    d = OUT / dev
    d.mkdir(parents=True, exist_ok=True)
    sub = d / "shipped" / "driver.sub"
    if not sub.exists():
        txt = re.sub(r"^C_comp\s+.*$", f"C_comp {cc:.4f}pF {cc:.4f}pF {cc:.4f}pF",
                     ibis.read_text(errors="ignore"), count=1, flags=re.M)
        ibis2 = d / "input_ccomp.ibs"
        ibis2.write_text(txt, encoding="utf-8")
        model, comp = gp.ibis_names(ibis2)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis2)),
                            model_name=model, component_name=comp)
        sub.parent.mkdir(parents=True, exist_ok=True)
        subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(sub))
    full = gp.run_ours(d / "shipped" / "full", sub.read_text(encoding="utf-8"), sup, 10.0)

    grid = np.arange(4.0, 21.0, cl.DT)
    tf, kb = full["t"], full["kugate_base"]
    k_rest = float(np.interp(4.5, tf, kb))
    k_on = float(np.interp(12.0, tf, kb))
    target = np.interp(grid, tf, np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0))
    t_on = 5.0 + gp.EDGE_PS.get(dev, 1.0) / 2000.0
    u = ((grid >= t_on) & (grid < t_on + 10.0)).astype(float)
    return grid, u, target


def fit_ku(u, target, prior_fn, K, kind, p=1.0, fix_xlin=None):
    """Same cost and optimiser budget as gate_chain_prototype.fit_chain_ku, with the
    drain factor switched: rms( map(chain(u)) - Ku_file )."""
    n = 3 if fix_xlin is not None else dt.NP_[kind]
    best = (9.0, None)

    def unpack(z):
        x_lin = fix_xlin if fix_xlin is not None else (float(z[3]) if n == 4 else float("nan"))
        return float(np.exp(z[0])), float(np.exp(z[1])), float(z[2]), x_lin

    def cost(z):
        s_up, s_dn, vt, x_lin = unpack(z)
        if not 0.0 <= vt <= 0.7:
            return 9.0
        if n == 4 and not 0.02 <= x_lin <= 1.5:
            return 9.0
        g = dt.simulate_chain(u, [(s_up, s_dn, vt, x_lin, p)] * K, kind)
        return float(np.sqrt(np.mean((prior_fn(g) - target) ** 2)))

    for s0 in (2.0, 8.0, 30.0):
        z, c = cl.nelder_mead(cost, np.array([np.log(s0), np.log(s0), 0.4, 0.4][:n]),
                              step=[0.7, 0.7, 0.15, 0.15][:n], maxiter=800)
        if c < best[0]:
            best = (c, unpack(z))
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", nargs="*", default=list(BUFFERS))
    ap.add_argument("--kinds", nargs="*", default=list(KINDS))
    ap.add_argument("--fix-xlin", type=float, default=None,
                    help="hold the boundary constant, as the shipped build does")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tag = "_pin" if a.fix_xlin is not None else ""
    rows = []
    for dev in a.dev:
        cfg = BUFFERS[dev]
        vt_m, al = cfg["prior"]
        prior_fn = lambda g: pm.prior(g, vt_m, al)      # noqa: E731
        grid, u, target = shipped_ku(dev, cfg["cc"])
        K = cfg["K"]
        print(f"\n=== {dev}: K = {K}, map prior vt={vt_m} alpha={al}, C_comp {cfg['cc']} pF")
        print(f"    target = kugate_base from the shipped model's full-swing run, "
              f"{len(grid)} points at {cl.DT * 1000:g} ps")
        print(f"    {'drain factor':<46}{'n':>2}{'Ku rms':>9}{'s_up':>8}{'s_dn':>8}{'vt':>7}"
              f"{'x_lin/x0':>10}")
        fig, ax = plt.subplots(figsize=(9, 4.2))
        ax.plot(grid - 5.0, target, color="#111111", lw=3, alpha=0.35, label="file Ku(t)")
        for kind in a.kinds:
            c, (s_up, s_dn, vt, x_lin) = fit_ku(u, target, prior_fn, K, kind,
                                                fix_xlin=a.fix_xlin)
            npar = 3 if a.fix_xlin is not None else dt.NP_[kind]
            xl = f"{x_lin:.3f}" + ("*" if a.fix_xlin is not None else "") if npar == 3 and a.fix_xlin is not None else (f"{x_lin:.3f}" if dt.NP_[kind] == 4 else "   --")
            print(f"    {dt.LABEL[kind]:<46}{npar:>2}{c:>9.4f}{s_up:>8.2f}{s_dn:>8.2f}"
                  f"{vt:>7.3f}{xl:>10}")
            g = dt.simulate_chain(u, [(s_up, s_dn, vt, x_lin, 1.0)] * K, kind)
            ax.plot(grid - 5.0, prior_fn(g), lw=1.4, label=f"{kind} ({dt.NP_[kind]}p) rms {c:.4f}")
            rows.append(dict(device=dev, K=K, kind=kind, n_params=dt.NP_[kind],
                             ku_rms=round(c, 5), s_up=round(s_up, 4), s_dn=round(s_dn, 4),
                             vt=round(vt, 4),
                             x_lin=(round(x_lin, 4) if dt.NP_[kind] == 4 else None)))
        ax.set_xlim(-0.2, 8), ax.set_ylim(-0.05, 1.1), ax.grid(alpha=0.3)
        ax.set_xlabel("time from the input edge (ns)"), ax.set_ylabel("Ku, normalised rest to on")
        ax.set_title(f"{dev}: drain factors fitted in the Ku domain (file only)", fontweight="bold")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(OUT / f"{dev}_ku_domain{tag}.png", dpi=150)
        plt.close(fig)
    with (OUT / f"results{tag}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {OUT / 'results.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
