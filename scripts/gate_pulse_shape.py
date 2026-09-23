#!/usr/bin/env python3
"""Is the chain's gate the same pulse as the transistor's, or just the same height?

inv_chain's gate reaches the right height at the width where its pad is 26 % high, so height
is not the story. This measures the whole pulse - height, when it peaks, its width at half
height, and its area above 0.1, which is the charge the output stage integrates - from the
step-7 builds' own runs, with no new simulation. ex2, where the recipe works, is measured the
same way for contrast.

Writes results/inv_chain_single_curve_2026-09-22/gate_shape.csv.

    py -3.14 scripts/gate_pulse_shape.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (REPO / "scripts", REPO / "tools" / "pybis2spice", REPO / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(p))
import csv  # noqa: E402
import numpy as np  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import stage_count_from_file as sc  # noqa: E402


def shape(t, y, lo=0.1):
    """(height, time of the peak, width at half height, area above lo) of one pulse."""
    i = int(np.argmax(y))
    h = float(y[i])
    half = 0.5 * h
    above = y >= half
    if not above.any():
        return h, float(t[i]), 0.0, 0.0
    j = np.where(above)[0]
    return h, float(t[i]), float(t[j[-1]] - t[j[0]]), float(np.trapezoid(np.clip(y - lo, 0, None), t))


OUT = REPO / "results" / "inv_chain_single_curve_2026-09-22"
ROWS = []


def run(dev, step, K):
    gp, gch, _ = sc._modules()
    gch.OUT, gch.G = sc.OUT / step, sc.PASSES[step]["models"]
    gp.VARIANT_NAME = dev
    sup, _ibis = gp.VARIANTS[dev]
    tag = sc.build_dir(step, dev, K, sc.BUFFERS[dev]["k_net"][1])
    text = (tag / "driver_chain.sub").read_text(encoding="utf-8")
    print(f"\n{dev} ({step}, K={K}) - gate pulse, model vs transistor")
    print(f"  {'W':>5} {'height':>13} {'peak at (ps)':>16} {'half-width (ps)':>17} {'area':>13}")
    for depth, w, _d in gp.cases(dev):
        r = gp.run_ours(tag / f"d{depth}", text, sup, w)
        rev = gp.RISE_NS + w
        g = np.arange(rev - 0.5, rev + 3.0, 0.002)
        tw, gw = gr.real_gate(dev, depth, gr.GATES[dev][0])
        m = shape(g, np.interp(g, r["t"], r["gup"]))
        s = shape(g, np.interp(g, tw, gw))
        print(f"  {depth:>5} {m[0]:6.2f}/{s[0]:5.2f} {1000*(m[1]-rev):8.0f}/{1000*(s[1]-rev):6.0f} "
              f"{1000*m[2]:8.0f}/{1000*s[2]:7.0f} {m[3]:7.3f}/{s[3]:5.3f}")
        ROWS.append(dict(buffer=dev, K=K, width_ps=depth,
                         height_model=round(m[0], 3), height_transistor=round(s[0], 3),
                         peak_ps_model=round(1000 * (m[1] - rev)), peak_ps_transistor=round(1000 * (s[1] - rev)),
                         halfwidth_ps_model=round(1000 * m[2]), halfwidth_ps_transistor=round(1000 * s[2]),
                         area_model=round(m[3], 4), area_transistor=round(s[3], 4),
                         area_excess_pct=round(100 * (m[3] / s[3] - 1), 1)))


if __name__ == "__main__":
    run("inv_chain", "step2f", 7)
    run("ex2", "step2f", 3)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "gate_shape.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0]))
        w.writeheader()
        w.writerows(ROWS)
    print(f"wrote {OUT / 'gate_shape.csv'}")
