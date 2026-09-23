#!/usr/bin/env python3
"""Can the one stressed pad run choose the Ku-vs-gate shape, not just the stage threshold?

Track 1 uses one universal curve shape (vt 0.5, alpha 0.7) for every buffer. That costs
inv_base8 and inv_skewp 3-4 points against their measured family shape (step 4b vs step 2).
The shape cannot come from the full swing - any monotone re-pairing of (map, gate) reproduces
it (predriver_stages_2026-09-09) - but the stressed run is a second observation, and it is
already on hand: today it only places the stage threshold.

This asks whether it *could* also choose the shape: build each buffer across a grid of
(vt, alpha), each one pad-calibrated as usual, and see whether the stressed error has a
minimum, where it sits, and whether that is near the measured family shape.

If the minimum is sharp and lands near the family shape, the shape is recoverable from what
track 1 already measures. If the surface is flat, the universal shape is as good as anything
the file plus one run can know, and 3-4 points is the price of not probing.

Output: results/shape_from_stressed_run_2026-09-22/

    py -3.14 scripts/shape_from_stressed_run.py [--buffers inv_base8 inv_skewp]
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import stage_count_from_file as sc  # noqa: E402

OUT = ROOT / "results" / "shape_from_stressed_run_2026-09-22"
GRID = [(0.40, 0.60), (0.40, 0.90), (0.50, 0.70), (0.55, 0.70), (0.60, 0.70), (0.50, 1.00)]
# the measured family shapes, for reference: ex2 (0.57, 0.64), inv_chain (0.49, 0.60),
# io_buf (0.50, 0.78); the 7-stage inverter variants use the 3-parameter prior (0.42, 1.15, 0.87)


def build(dev: str, vt: float, al: float) -> dict:
    gp, gch, _ = sc._modules()
    gch.OUT = OUT
    gch.G = sc.MEAS_MODELS                       # today's converter, measured C_comp
    b = sc.BUFFERS[dev]
    argv = ["gate_chain_prototype", "--variant", dev, "--source", "ibis", "--maps", "prior",
            "--K", str(b["k_net"][0]), "--calib-pad", str(b["calib"]),
            "--prior", f"{vt:g}", f"{al:g}"]
    if b["cc"]:
        argv += ["--ccomp", f"{b['cc']:g}"]
    if b["xlin"] is not None:
        argv += ["--fix-xlin", f"{b['xlin']:g}"]
    if b["k_net"][1] is not None:
        argv += ["--Kd", str(b["k_net"][1])]
    sys.argv = argv
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        gch.main()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{dev}_vt{vt:g}_al{al:g}.log").write_text(log.getvalue(), encoding="utf-8")
    dcc = dev + (f"_c{b['cc']:g}" if b["cc"] else "")
    for tag in sorted((OUT / dcc).glob(f"ibis_prior_K{b['k_net'][0]}_prior{vt:g}_{al:g}*")):
        if (tag / "sweep.csv").exists():
            r = list(csv.DictReader((tag / "sweep.csv").open()))[-1]
            pk = [float(v) for k, v in r.items() if k.startswith("pk_d")]
            lag = [float(v) for k, v in r.items() if k.startswith("lag_d")]
            return dict(buffer=dev, vt=vt, alpha=al, worst_peak_pct=round(max(map(abs, pk)), 1),
                        peaks_pct=" / ".join(f"{x:+.1f}" for x in pk),
                        lag_calib_ps=round(lag[-1]), full_pad_rms_mV=r["full_pad_rms_mV"])
    return dict(buffer=dev, vt=vt, alpha=al, worst_peak_pct="", peaks_pct="build failed")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffers", nargs="+", default=["inv_base8", "inv_skewp"])
    args = ap.parse_args()
    rows = []
    for dev in args.buffers:
        print(f"{dev}: {len(GRID)} shapes", flush=True)
        for vt, al in GRID:
            rows.append(build(dev, vt, al))
            r = rows[-1]
            print(f"  vt {vt:g} alpha {al:g}: worst {r['worst_peak_pct']} %  {r['peaks_pct']}  "
                  f"lag {r.get('lag_calib_ps', '-')} ps  full {r.get('full_pad_rms_mV', '-')} mV", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "shape_grid.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(max(rows, key=len)))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT / 'shape_grid.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
