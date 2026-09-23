#!/usr/bin/env python3
"""Can the chain's gate be made to fall faster without spoiling the full swing?

inv_chain's modelled gate reaches the right height, peaks ~45 ps late and stays up 10-20 ps
too long; that surplus charge is its 26 % pad overshoot
(`results/inv_chain_single_curve_2026-09-22/`). The stage law has one knob for the discharge
direction: `--dn-ratio R` sets the discharge x_lin to `x_lin * R`, so a smaller R saturates the
pull-down current nearer the rail and should sharpen the tail. s_dn and x_lin are refitted at
each R against the same full-swing Ku(t), so a ratio that helps the stressed fall without
raising the full-swing rms is a real gain, not a trade.

R = 1 is the build step 7 made. For each R: the five stressed peaks, the gate pulse's area
against the transistor's, and the full-swing pad rms.

Output: results/inv_chain_fall_rate_2026-09-22/

    py -3.14 scripts/inv_chain_fall_rate.py [--ratios 0.3 0.5 1 2]
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

import numpy as np  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import stage_count_from_file as sc  # noqa: E402
from gate_pulse_shape import shape  # noqa: E402

OUT = ROOT / "results" / "inv_chain_fall_rate_2026-09-22"
DEV, K, CC, PRIOR, CALIB = "inv_chain", 7, 0.6, (0.49, 0.6), 104


def build(ratio: float) -> dict:
    gp, gch, _ = sc._modules()
    gch.OUT = OUT
    gch.G = sc.MEAS_MODELS                      # today's converter, measured C_comp
    sys.argv = ["gate_chain_prototype", "--variant", DEV, "--source", "ibis", "--maps", "prior",
                "--K", str(K), "--calib-pad", str(CALIB), "--ccomp", f"{CC:g}",
                "--prior", f"{PRIOR[0]:g}", f"{PRIOR[1]:g}"] + \
               ([] if ratio == 1.0 else ["--dn-ratio", f"{ratio:g}"])
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        gch.main()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"dn{ratio:g}.log").write_text(log.getvalue(), encoding="utf-8")

    suffix = "" if ratio == 1.0 else f"_dn{ratio:g}"
    tag = next(iter(sorted((OUT / f"{DEV}_c{CC:g}").glob(f"ibis_prior_K{K}_*{suffix}"))), None)
    if tag is None or not (tag / "sweep.csv").exists():
        return dict(dn_ratio=ratio, note="build produced no sweep.csv")
    row = list(csv.DictReader((tag / "sweep.csv").open()))[-1]
    pk = [float(v) for k, v in row.items() if k.startswith("pk_d")]
    lag = [float(v) for k, v in row.items() if k.startswith("lag_d")]

    gp.VARIANT_NAME = DEV
    sup, _ = gp.VARIANTS[DEV]
    text = (tag / "driver_chain.sub").read_text(encoding="utf-8")
    areas = []
    for depth, w, _d in gp.cases(DEV):
        r = gp.run_ours(tag / f"d{depth}", text, sup, w)
        rev = gp.RISE_NS + w
        g = np.arange(rev - 0.5, rev + 3.0, 0.002)
        tw, gw = gr.real_gate(DEV, depth, gr.GATES[DEV][0])
        m, s = shape(g, np.interp(g, r["t"], r["gup"])), shape(g, np.interp(g, tw, gw))
        areas.append(100 * (m[3] / s[3] - 1))
    return dict(dn_ratio=ratio, worst_peak_pct=f"{max(map(abs, pk)):.1f}",
                peaks_pct=" / ".join(f"{x:+.1f}" for x in pk),
                lag_ps=" / ".join(f"{x:.0f}" for x in lag),
                gate_area_excess_pct=" / ".join(f"{x:+.0f}" for x in areas),
                full_pad_rms_mV=row["full_pad_rms_mV"], build=tag.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratios", type=float, nargs="+", default=[0.3, 0.5, 1.0, 2.0])
    args = ap.parse_args()
    rows = [build(r) for r in args.ratios]
    for r in rows:
        print(f"  dn-ratio {r['dn_ratio']:>4}: worst {r.get('worst_peak_pct', '-'):>5} %  "
              f"peaks {r.get('peaks_pct', '-')}  gate area {r.get('gate_area_excess_pct', '-')}  "
              f"full {r.get('full_pad_rms_mV', '-')} mV", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "fall_rate.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(max(rows, key=len)))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT / 'fall_rate.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
