#!/usr/bin/env python3
"""Would a faster final stage narrow inv_chain's gate pulse?

inv_chain's modelled gate reaches the right height and stays up 10-20 ps too long; the surplus
charge is its 26 % pad overshoot, and the one discharge knob the stage law has (`--dn-ratio`)
only buys 2-6 points (`results/inv_chain_fall_rate_2026-09-22/`). The suspicion is that the
chain needs a final stage that is not identical to the others - it is the one that drives the
output gate and sets its fall.

This is the cheap version of that test: take the built model and multiply **only the last
stage's** discharge rate s_dn, with no refitting, then measure the gate pulse and the pad. A
scale that narrows the gate and lowers the pad says the degree of freedom is the right one and
a fitted version is worth writing; it is not itself a model, because nothing re-establishes
the full swing - which is reported alongside so the cost is visible.

Output: results/inv_chain_last_stage_2026-09-22/

    py -3.14 scripts/inv_chain_last_stage_probe.py [--scales 1 1.5 2 3]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import spicelab as sl  # noqa: E402
import stage_count_from_file as sc  # noqa: E402
from gate_pulse_shape import shape  # noqa: E402

OUT = ROOT / "results" / "inv_chain_last_stage_2026-09-22"
DEV, K = "inv_chain", 7
SRC = None      # the step-7 build (measured C_comp, family shape, today's converter)


def scale_last_stage(text: str, scale: float) -> str:
    """Multiply the last pull-up-chain stage's discharge rate s_dn by `scale`.

    The stage's current source reads
        BSTG<k> STG<k> 0 I = -{gate_c} * 1e9 * (<s_up> * <hu> * <ru> - <s_dn> * <hd> * <rd>)
    so s_dn is the coefficient right after the minus sign in the bracket.
    """
    pat = re.compile(rf"^(BSTG{K} STG{K} 0 I = .*?\) - )([0-9.eE+-]+)( \* max)", re.M)
    m = pat.search(text)
    if not m:
        raise RuntimeError(f"no BSTG{K} line to scale")
    return pat.sub(lambda mm: mm.group(1) + f"{float(mm.group(2)) * scale:.6g}" + mm.group(3), text, count=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scales", type=float, nargs="+", default=[1.0, 1.5, 2.0, 3.0])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tag = sc.build_dir("step2f", DEV, K, None)
    base = (tag / "driver_chain.sub").read_text(encoding="utf-8")
    gp.VARIANT_NAME = DEV
    sup, _ = gp.VARIANTS[DEV]
    cs = gp.cases(DEV)
    refs = {d_: gp.tr0_pad(d / "run.tr0") for d_, _, d in cs}

    # the transistor's own full swing, for the cost side of the trade. inv_chain is one of the
    # matrix buffers, whose full-swing reference lives with the predriver probe runs, not with
    # the stressed cases (gate_chain_prototype does the same).
    import predriver_stage_probe as psp
    fraw = psp.parse_tr0(psp.OUT / DEV / "full/run.tr0")
    tfull = np.asarray(fraw["time"], float) * 1e9
    pfull = np.asarray(fraw["v(pad_sp)"], float)
    grid = np.arange(4.5, 20.0, 0.005)

    rows = []
    for sc_ in args.scales:
        text = scale_last_stage(base, sc_) if sc_ != 1.0 else base
        d0 = OUT / f"s{sc_:g}"
        pks, areas = [], []
        for depth, w, _d in cs:
            r = gp.run_ours(d0 / f"d{depth}", text, sup, w)
            pk, _lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
            pks.append(pk)
            rev = gp.RISE_NS + w
            g = np.arange(rev - 0.5, rev + 3.0, 0.002)
            tw, gw = gr.real_gate(DEV, depth, gr.GATES[DEV][0])
            m, s_ = shape(g, np.interp(g, r["t"], r["gup"])), shape(g, np.interp(g, tw, gw))
            areas.append(100 * (m[3] / s_[3] - 1))
        rf = gp.run_ours(d0 / "full", text, sup, 10.0)
        rms = 1e3 * float(np.sqrt(np.mean((np.interp(grid, rf["t"], rf["pad"]) - np.interp(grid, tfull, pfull)) ** 2)))
        rows.append(dict(s_dn_scale=sc_, worst_peak_pct=round(max(map(abs, pks)), 1),
                         peaks_pct=" / ".join(f"{x:+.1f}" for x in pks),
                         gate_area_excess_pct=" / ".join(f"{x:+.0f}" for x in areas),
                         full_pad_rms_mV=round(rms, 1)))
        print(f"  last-stage s_dn x{sc_:<4g} worst {rows[-1]['worst_peak_pct']:5.1f} %  "
              f"peaks {rows[-1]['peaks_pct']}  gate area {rows[-1]['gate_area_excess_pct']}  "
              f"full {rows[-1]['full_pad_rms_mV']} mV", flush=True)
    with (OUT / "last_stage.csv").open("w", newline="") as fh:
        w_ = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w_.writeheader()
        w_.writerows(rows)
    print(f"wrote {OUT / 'last_stage.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
