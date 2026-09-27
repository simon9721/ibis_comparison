#!/usr/bin/env python3
"""C_comp per variant by the Ku-vs-gate loop method, now that every variant has a probed gate.

Same measurement as `ku_gate_hysteresis_ccomp.py` on the base buffers: the
two-fixture Ku plotted against the real gate opens a loop when the C_comp used
in the solve is wrong; the loop-minimising value is the device's C_comp. Uses
the variant's deepest stressed case (fixture_0 / fixture_vcc from the stress
cases, the gate from `variant_gate_probe.py`).

    py -3.14 scripts/variant_ccomp_loop.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import silicon_map_replay as smr  # noqa: E402
import ku_gate_hysteresis_ccomp as kh  # noqa: E402

PROBE = ROOT / "results/variant_gate_probe_2026-09-10"


def main() -> int:
    info = json.loads((PROBE / "gate_max.json").read_text())
    out = {}
    print(f"    {'variant':<13}{'declared pF':>12}{'loop@declared':>14}{'argmin pF':>10}{'min loop':>9}")
    for v in info:
        sup, ibis = gp.VARIANTS[v]
        model, comp = gp.ibis_names(ibis)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
        declared = float(data.c_comp[0]) * 1e12
        depth, w, d = gp.cases(v)[-1]
        lo, hi = smr.fixture(d / "fixture_0/run.tr0"), smr.fixture(d / "fixture_vcc/run.tr0")
        raw = psp.parse_tr0(PROBE / v / f"w{depth}" / "run.tr0")
        t = np.asarray(raw["time"], float) * 1e9
        vg = np.asarray(raw[info[v]["node"]], float)
        pad = np.asarray(raw["v(pad)"], float)
        rev, tpk = 5.0 + w, float(t[int(np.argmax(pad))])
        ccs = np.arange(0.5, 6.01, 0.25) if v.startswith("ex2") else np.arange(0.1, 1.51, 0.1)
        loops = []
        for cc in ccs:
            data.c_comp = [cc * 1e-12] * 3
            s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
            loops.append(kh.hysteresis(*kh.event(s[:, 0] * 1e9, s[:, 1], t, vg, rev, tpk)))
        loops = np.array(loops)
        i = int(np.nanargmin(loops))
        data.c_comp = [declared * 1e-12] * 3
        s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
        ld = kh.hysteresis(*kh.event(s[:, 0] * 1e9, s[:, 1], t, vg, rev, tpk))
        out[v] = dict(declared_pF=round(declared, 3), loop_declared=round(float(ld), 3), argmin_pF=round(float(ccs[i]), 3), min_loop=round(float(loops[i]), 3))
        print(f"    {v:<13}{declared:>12.2f}{ld:>14.3f}{ccs[i]:>10.2f}{loops[i]:>9.3f}")
    (PROBE / "ccomp_loop.json").write_text(json.dumps(out, indent=2))
    print(f"  wrote {PROBE / 'ccomp_loop.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
