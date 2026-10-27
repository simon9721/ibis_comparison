#!/usr/bin/env python3
"""The two simplest reversal rules, run on ex2 and inv_chain at the paper's five stressed widths.

Question: when a short pulse reverses, what happens if the model simply re-enters the opposite
coefficient table (a) at the same elapsed time (time matching) or (b) where that table holds the
present coefficient value (value matching)? Both exist as pybis gate modes and were run in the
2026-08-20 stress matrix on three buffers, but the matrix scored a whole-record pad rms, which a
model that produces no pulse at all wins; and time matching had no number because it never
simulated. This re-runs both on the two base buffers the paper follows, at the widths of Table X,
and scores them as the paper does: the peak error of the pad pulse against the transistor, (28),
and the pad rms over the pulse and its return, the window of (29).

Methods (pybis gate modes, scripts/run_stress_method_matrix.py METHODS):
    time_match    InputDrivenTimeMatchedReplayFull    re-enter the opposite table at the same elapsed offset
    coeff_match   InputDrivenValueMatchedReplayV2Hybrid  re-enter where the opposite table holds the present Ku/Kd,
                                                      gated to the reversal

Each case is run through scripts/archive/compare_silicon_anchored_shortpulse.py (one ngspice run
of the model, the transistor and native references from HSPICE, the transistor's Ku/Kd from its
two fixture runs). The HSPICE fixture runs are the matrix's, copied into this folder. The
coefficient step each rule demands at the reversal comes from
scripts/archive/analyse_reversal_discontinuity.py (run here on the compressed matrix raws).

Output: results/reversal_rules_ex2_inv_chain_2026-10-27/{scores.csv, FINDINGS.md, <method>/...}

    py -3.14 scripts/reversal_rules_ex2_inv_chain.py --run     # launch the twenty cases (minutes)
    py -3.14 scripts/reversal_rules_ex2_inv_chain.py           # score what is there
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "reversal_rules_ex2_inv_chain_2026-10-27"
COMPARE = ROOT / "scripts" / "archive" / "compare_silicon_anchored_shortpulse.py"
METHODS = {"time_match": "InputDrivenTimeMatchedReplayFull", "coeff_match": "InputDrivenValueMatchedReplayV2Hybrid"}
WIDTHS = {"ex2": (809.6, 830.1, 857.6, 895.3, 974.7), "inv_chain": (103.5, 106.3, 110.8, 119.0, 135.0)}
EDGE_NS = 5.0


def run() -> None:
    for key, mode in METHODS.items():
        for dev, widths in WIDTHS.items():
            cmd = [sys.executable, str(COMPARE), "--out", str(OUT / key), "--device", dev, "--direction", "short_high",
                   "--ngspice-timeout", "240"]
            for w in widths:
                cmd += ["--width-ps", f"{w:.1f}"]
            print(f"-- {key} {dev}", flush=True)
            subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, PYBIS_GATE_MODE=mode))


def score() -> list[dict]:
    rows = []
    for key in METHODS:
        status = {}
        cases = OUT / key / "cases.csv"
        if cases.exists():
            for r in csv.DictReader(cases.open()):
                status[(r["device"], float(r["pulse_width_ps"]))] = r["status"]
        for dev, widths in WIDTHS.items():
            for w in widths:
                tag = f"{dev}_short_high_w{int(round(round(w, 1)))}ps"
                f = OUT / key / "waveforms" / f"{tag}.csv"
                row = dict(method=key, device=dev, width_ps=w, status=status.get((dev, w), "missing"))
                if f.exists():
                    rec = list(csv.DictReader(f.open()))
                    t = np.array([float(r["time_ns"]) for r in rec])
                    col = lambda k: np.array([float(r[k]) for r in rec])  # noqa: E731
                    tf = EDGE_NS + w / 1000.0
                    win = (t >= tf - 0.3) & (t <= tf + 2.6)                 # the peak, as _peak_err of the deck figures
                    wr = (t >= tf - 0.3) & (t <= tf + 1.5)                  # the window of (29)
                    tr, nat, mo = col("silicon_pad"), col("hspice_pad"), col("pybis_pad")
                    pk = tr[win].max()
                    row.update(transistor_peak_V=round(pk, 3),
                               native_peak_err_pct=round(100 * (nat[win].max() - pk) / pk, 1),
                               model_peak_err_pct=round(100 * (mo[win].max() - pk) / pk, 1),
                               model_ku_max=round(col("pybis_ku")[win].max(), 3),
                               native_rms_mV=round(1e3 * np.sqrt(np.mean((nat[wr] - tr[wr]) ** 2)), 1),
                               model_rms_mV=round(1e3 * np.sqrt(np.mean((mo[wr] - tr[wr]) ** 2)), 1))
                rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.run:
        run()
    rows = score()
    keys = ["method", "device", "width_ps", "status", "transistor_peak_V", "native_peak_err_pct", "model_peak_err_pct",
            "model_ku_max", "native_rms_mV", "model_rms_mV"]
    with (OUT / "scores.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        wr.writerows(rows)
    for r in rows:
        print("  ".join(f"{k}={r.get(k, '')}" for k in keys))
    # the failure reason of every case that did not simulate
    for key in METHODS:
        for log in sorted((OUT / key / "ngspice_runs").glob("**/ngspice_stdout.log")):
            txt = log.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"Timestep too small; time = ([0-9.e+-]+), timestep = ([0-9.e+-]+): trouble with node \"([^\"]+)\"", txt)
            if m:
                print(f"{key} {log.parts[-3]}: timestep collapse at {float(m.group(1)) * 1e9:.3f} ns, node {m.group(3)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
