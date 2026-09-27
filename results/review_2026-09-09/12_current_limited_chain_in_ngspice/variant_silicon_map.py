#!/usr/bin/env python3
"""A variant's own Ku-vs-gate map from its stressed fixture runs and the probed gate.

The variant stress cases carry two-fixture transistor runs per depth
(fixture_0 / fixture_vcc); `variant_gate_probe.py` added the gate node at the
deepest depth. Solve Ku/Kd there, plot against the normalised gate, fit the
three-parameter prior. Answers "is inv_stage4's map the family map?".

    py -3.14 scripts/variant_silicon_map.py --variant inv_stage4 --ccomp 0.6
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import silicon_map_replay as smr  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402

PROBE = ROOT / "results/variant_gate_probe_2026-09-10"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="inv_stage4")
    ap.add_argument("--ccomp", type=float, default=None)
    args = ap.parse_args()
    v = args.variant
    sup, ibis = gp.VARIANTS[v]
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    if args.ccomp:
        data.c_comp = [args.ccomp * 1e-12] * 3
    info = json.loads((PROBE / "gate_max.json").read_text())[v]
    depth, w, d = gp.cases(v)[-1]
    lo, hi = smr.fixture(d / "fixture_0/run.tr0"), smr.fixture(d / "fixture_vcc/run.tr0")
    s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
    raw = psp.parse_tr0(PROBE / v / f"w{depth}" / "run.tr0")
    t = np.asarray(raw["time"], float) * 1e9
    g = (np.asarray(raw[info["node"]], float) - info["rest_v"]) / (info["high_v"] - info["rest_v"])
    ku_rise, ku_fall, kd_on, kd_off = smr.silicon_maps(s[:, 0] * 1e9, s[:, 1], s[:, 2], t, g, 5.0, 5.0 + w)
    gg, kk = ku_rise
    m = (kk >= 0.10) & (gg <= min(0.995, float(g.max()) - 0.01))
    vt, al, gs, rms = pm.fit_prior3(gg[m], kk[m])
    print(f"  {v}: gate {info['node']} at W {info['width_ps']} ps reaches {info['gate_max']:.3f}; own prior3 vt={vt:.2f} alpha={al:.2f} gs={gs:.2f} rms={rms:.3f}")
    for gv in (0.5, 0.6, 0.7, 0.8, 0.88):
        print(f"    g={gv:.2f}: silicon Ku {np.interp(gv, gg, kk):.3f}   family prior3 {pm.prior3(gv, 0.42, 1.15, 0.87):.3f}   own prior3 {pm.prior3(gv, vt, al, gs):.3f}")
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(gg, kk, color="#2E8B57", lw=2.2, label=f"silicon Ku(g), stressed event W={info['width_ps']} ps")
    ax.plot(gg, pm.prior3(gg, 0.42, 1.15, 0.87), color="#C05621", ls="--", lw=1.8, label="inv family prior3 (0.42, 1.15, 0.87)")
    ax.plot(gg, pm.prior3(gg, vt, al, gs), color="#B03060", ls=":", lw=2.0, label=f"own prior3 ({vt:.2f}, {al:.2f}, {gs:.2f})")
    ax.axvline(info["gate_max"], color="#8A8A8A", ls="--", lw=1.0)
    ax.set_xlabel("gate, 0 = off, 1 = full-swing on")
    ax.set_ylabel("Ku")
    ax.set_title(f"{v}: the map is not the family map?", fontweight="bold")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = PROBE / v / "silicon_map.png"
    fig.savefig(out, dpi=150)
    print(f"  figure: {out}")
    (PROBE / v / "own_prior3.json").write_text(json.dumps(dict(vt=vt, alpha=al, gs=gs, rms=rms)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
