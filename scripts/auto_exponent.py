#!/usr/bin/env python3
"""Item 2: pick the stage drive-law exponent automatically, from the data the recipe already
has (the full-swing runs and the ONE stressed pad point), without knowing the family.

For each candidate exponent the chain is fitted to the real last-stage step, calibrated on
the pad point, and scored on what the recipe can see:

    score = |peak error on the calibration pulse, %|  +  |best-fit lag on it, ps| / 10
          + full-swing pad rms vs the transistor, mV / 5

(the matrix's other widths and the trains are NOT used: they are the test). The build with
the smaller score is kept. Reads the sweep.csv the chain script writes.

    py -3.14 scripts/auto_exponent.py --dev ex2 --ccomp 1.7 --K 3 --calib-pad 810
    py -3.14 scripts/auto_exponent.py --dev inv_chain --ccomp 0.6 --K 7 --calib-pad 104
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CH = ROOT / "results" / "gate_chain_prototype_2026-09-10"


def build_dir(dev, cc, K, depth, p):
    d = CH / (dev + (f"_c{cc:g}" if cc else ""))
    return d / (f"real_silicon_K{K}_calibpad{depth}" + (f"_p{p:g}" if p != 1.0 else ""))


def run_build(dev, cc, K, depth, p):
    d = build_dir(dev, cc, K, depth, p)
    if not (d / "sweep.csv").exists():
        cmd = [sys.executable, str(ROOT / "scripts/gate_chain_prototype.py"), "--variant", dev, "--source", "real", "--maps", "silicon",
               "--K", str(K), "--calib-pad", str(depth), "--p", str(p)] + (["--ccomp", str(cc)] if cc else [])
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rows = list(csv.DictReader((d / "sweep.csv").open(encoding="utf-8")))
    row = [r for r in rows if r["build"] != "shipped"][-1]
    return d, row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--ccomp", type=float, default=None)
    ap.add_argument("--K", type=int, required=True)
    ap.add_argument("--calib-pad", type=int, required=True)
    ap.add_argument("--exponents", type=float, nargs="*", default=[1.0, 0.5])
    args = ap.parse_args()
    best = None
    print(f"{args.dev}: exponent selection on the calibration pulse (d{args.calib_pad}) and full swing only")
    print(f"  {'p':>4} {'peak %':>8} {'lag ps':>7} {'fs rms mV':>10} {'score':>7}   (other widths, for information only)")
    for p in args.exponents:
        d, row = run_build(args.dev, args.ccomp, args.K, args.calib_pad, p)
        pk = float(row[f"pk_d{args.calib_pad}"])
        lag = float(row[f"lag_d{args.calib_pad}"])
        fs = float(row["full_pad_rms_mV"])
        score = abs(pk) + abs(lag) / 10.0 + fs / 5.0
        others = ", ".join(f"{k[3:]}: {float(v):+.0f}" for k, v in row.items() if k.startswith("pk_d") and k != f"pk_d{args.calib_pad}")
        print(f"  {p:>4g} {pk:>+8.1f} {lag:>+7.0f} {fs:>10.1f} {score:>7.1f}   ({others})")
        if best is None or score < best[0]:
            best = (score, p, d)
    print(f"  -> exponent {best[1]:g}  ({best[2].name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
