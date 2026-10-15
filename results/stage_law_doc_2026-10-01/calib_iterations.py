#!/usr/bin/env python3
"""How the threshold calibration (28) finds v_t, on ex2's selected candidate.

Re-runs the ten stored calibration iterations of the file-only ex2 build (K = 3, map shape
(0.5, 0.7), C_comp 2.64 pF: stage_count_from_file step 6, calib/it00..it09) and, for the
underlying curve, the same subcircuit at a dense set of thresholds. Each point is one ngspice
run of the complete model for the 810 ps pulse; the peak error is gate_ramp_prototype.score,
the one calibrate_pad bisects on.

Output: calib_iterations/ex2.npz  (vt, peak error, pad waveforms; the measured waveform)

    py -3.14 results/stage_law_doc_2026-10-01/calib_iterations.py
"""
from __future__ import annotations

import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(_p))
import gate_ramp_prototype as gp  # noqa: E402
import build_0917_deck_figures as f17  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "calib_iterations"
CAND = (ROOT / "results" / "stage_count_from_file_2026-09-21" / "step6" / "ex2_c2.64"
        / "ibis_prior_K3_prior0.5_0.7_xlin0.45_calibpad810")
W = 0.810
DENSE = [0.05, 0.15, 0.25, 0.30, 0.40, 0.45, 0.55, 0.60, 0.65]     # besides the iterates


def stage_vt(sub: str) -> float:
    m = re.search(r"^BSTG1 .*?V\(CHIN\) - ([0-9.eE+-]+)\)", sub, re.M)
    return float(m.group(1))


def with_vt(sub: str, vt: float) -> str:
    """The same subcircuit with every stage threshold replaced (identical stages)."""
    vt0 = stage_vt(sub)
    return sub.replace(f"- {vt0:.6g}) / {1 - vt0:.6g}", f"- {vt:.6g}) / {1 - vt:.6g}")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    gp.VARIANT_NAME = "ex2"
    t_si, si, _ = f17.transistor_pad("ex2", 810)
    its = sorted(CAND.glob("calib/it*/driver.sub"))
    subs = [(f"it{i:02d}", p.read_text(encoding="utf-8")) for i, p in enumerate(its)]
    base = subs[0][1]
    assert all(abs(stage_vt(with_vt(base, v)) - v) < 1e-6 for v in DENSE)
    subs += [(f"dense_{v:.2f}", with_vt(base, v)) for v in DENSE]

    def run(item):
        name, sub = item
        r = gp.run_ours(OUT / name, sub, 3.3, W)
        e = gp.score(t_si, si, r["t"], r["pad"], W)[0]
        return name, stage_vt(sub), e, np.asarray(r["t"]), np.asarray(r["pad"])

    with ThreadPoolExecutor(max_workers=4) as ex:        # ngspice is a subprocess; threads suffice
        res = list(ex.map(run, subs))
    t = res[0][3]
    np.savez(OUT / "ex2.npz", names=np.array([r[0] for r in res]), vt=np.array([r[1] for r in res]),
             err=np.array([r[2] for r in res]), t=t,
             pads=np.array([np.interp(t, r[3], r[4]) for r in res]), t_si=t_si, si=si)
    for r in res:
        print(f"{r[0]:12s} vt {r[1]:.4f}  peak error {r[2]:+7.2f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
