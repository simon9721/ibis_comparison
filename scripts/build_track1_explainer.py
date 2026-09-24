#!/usr/bin/env python3
"""Build the track-1 explainer page from its template and the stored simulation runs.

The page is the visual companion to `docs/track1_recipe.md`; the two must agree, which
`scripts/check_recipe_agreement.py` verifies. The prose and the SVG structure are authored by
hand in the template; everything this script adds is geometry:

  * **conceptual curves** computed from the closed forms the argument uses, so the pictures are
    exact rather than sketched - the two degenerate models in the first figure really do compose
    to the same Ku(t), and the reversal dots really do sit on the trajectory;
  * **real traces** - pad and gate waveforms lifted out of the transistor .tr0 references and
    the ngspice .raw of the shipped model and of the build the recipe selected.

Both land as polyline point strings in one JS object, spliced into the template's
`/*__CURVES__*/` placeholder; four lines of script in the page assign them by id.

Extracting the real traces needs the stored runs, which are large and get cleaned. They are
therefore cached in `results/track1_summary_2026-09-23/explainer_traces.json`, and the page
rebuilds from that cache alone. Pass `--extract` to regenerate the cache from the runs.

Output: results/track1_summary_2026-09-23/track1_explainer.html

    python scripts/build_track1_explainer.py [--extract]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

OUT_DIR = ROOT / "results" / "track1_summary_2026-09-23"
TEMPLATE = ROOT / "docs" / "track1_explainer.template.html"
CACHE = OUT_DIR / "explainer_traces.json"
PAGE = OUT_DIR / "track1_explainer.html"

SC = ROOT / "results" / "stage_count_from_file_2026-09-21"
MX = ROOT / "results" / "stress_method_matrix_2026-08-20" / "pad_match" / "hspice_references"

# The build the recipe selected for each of the two buffers the page shows, and the shipped
# model generated at the same C_comp. Both are the folders WAVEFORMS.md indexes.
CASES = {
    "ex2": dict(
        sup=3.3, gate=None,
        ours=SC / "step6/ex2_c2.64/ibis_prior_K3_prior0.5_0.7_xlin0.45_calibpad810",
        ship=SC / "knee_models/ex2_c2.64/shipped",
        tran=MX / "ex2/transistor/r50_c2pf",
        widths={810: "short_high_w810ps_810ps", 975: "short_high_w975ps_975ps"}),
    "inv_chain": dict(
        sup=1.8, gate=104,
        ours=SC / "step8/inv_chain_c0.66/ibis_prior_K6_prior0.4_0.9_calibpad104",
        ship=SC / "knee_models/inv_chain_c0.66/shipped",
        tran=MX / "inv_chain/transistor/r50_c2pf",
        widths={104: "short_high_w104ps_104ps", 135: "short_high_w135ps_135ps"}),
}
N_SAMPLES = 130                      # points per trace after resampling onto a common grid


# --------------------------------------------------------------------------- #
# the real traces
# --------------------------------------------------------------------------- #

def extract_traces() -> dict:
    """Lift the pad and gate waveforms out of the stored runs. Needs the .raw files."""
    import gate_ramp_prototype as gp
    import gate_replay_prototype as gr
    import spicelab as sl

    def samp(t, y, t0, t1):
        g = np.linspace(t0, t1, N_SAMPLES)
        return [round(float(v), 4) for v in np.interp(g, t, y)], [round(float(v - t0), 4) for v in g]

    out = {}
    for dev, c in CASES.items():
        gp.VARIANT_NAME = dev
        out[dev] = dict(supply=c["sup"], widths={})
        for w_ps, folder in c["widths"].items():
            w = w_ps / 1000.0
            rev = gp.RISE_NS + w                       # where the input reverses
            t0, t1 = rev - 0.30, rev + 2.0
            tt, tp = gp.tr0_pad(c["tran"] / folder / "run.tr0")
            rs = sl.parse_ngspice_raw(c["ours"] / f"d{w_ps}" / "run.raw")
            rh = sl.parse_ngspice_raw(c["ship"] / f"d{w_ps}" / "run.raw")
            pad, tax = samp(tt, tp, t0, t1)
            rec = dict(t=tax, transistor=pad,
                       ours=samp(sl.time_ns(rs), sl.trace(rs, "out"), t0, t1)[0],
                       shipped=samp(sl.time_ns(rh), sl.trace(rh, "out"), t0, t1)[0],
                       reversal_at=round(rev - t0, 4))
            if c["gate"] == w_ps:
                tw, gw = gr.real_gate(dev, w_ps, gr.GATES[dev][0])
                rec["gate_transistor"] = samp(tw, gw, t0, t1)[0]
                rec["gate_ours"] = samp(sl.time_ns(rs), sl.trace(rs, "x1.gup"), t0, t1)[0]
                rec["gate_shipped"] = samp(sl.time_ns(rh), sl.trace(rh, "x1.gup"), t0, t1)[0]
            out[dev]["widths"][str(w_ps)] = rec
            print(f"  {dev} w={w_ps} ps: transistor peak {max(pad):.3f} V, "
                  f"ours {max(rec['ours']):.3f}, shipped {max(rec['shipped']):.3f}")
    return out


# --------------------------------------------------------------------------- #
# the geometry
# --------------------------------------------------------------------------- #

def curves(traces: dict) -> dict:
    """Every polyline the page draws, in its own SVG viewBox units."""
    out: dict[str, object] = {}

    def emit(name, xs, ys, box, xr, yr):
        x0, y0, w, h = box
        px = x0 + (np.asarray(xs, float) - xr[0]) / (xr[1] - xr[0]) * w
        py = y0 + h - (np.asarray(ys, float) - yr[0]) / (yr[1] - yr[0]) * h
        out[name] = " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(px, py))

    PLOT = (0, 0, 150, 92)               # the mini-plots of figures 1 and 2 share this rect

    # -- the degeneracy. Ku(t) = x^2 both ways: A is map g^2 through gate x, B is map g^6
    # through gate x^(1/3). At the reversal x = 0.5 both give Ku = 0.25, gates 0.50 and 0.79.
    x = np.linspace(0, 1, 90)
    emit("d1_gateA", x, x, PLOT, (0, 1), (0, 1.05))
    emit("d1_gateB", x, x ** (1 / 3), PLOT, (0, 1), (0, 1.05))
    emit("d1_mapA", x, x ** 2, PLOT, (0, 1), (0, 1.05))
    emit("d1_mapB", x, x ** 6, PLOT, (0, 1), (0, 1.05))
    emit("d1_ku", x, x ** 2, PLOT, (0, 1), (0, 1.05))

    # -- Ku against its own gate: a thin lens (measured) and an open loop (wrong C_comp)
    g = np.linspace(0, 1, 90)
    base = np.clip((g - 0.35) / 0.65, 0, 1) ** 0.8
    lens = np.sin(np.pi * np.clip((g - 0.35) / 0.65, 0, 1))
    emit("d2_tight_up", g, base - 0.045 * lens, PLOT, (0, 1), (0, 1.35))
    emit("d2_tight_dn", g, base + 0.045 * lens, PLOT, (0, 1), (0, 1.35))
    emit("d2_open_up", g, 1.24 * base - 0.30 * lens, PLOT, (0, 1), (0, 1.35))
    emit("d2_open_dn", g, 1.24 * base + 0.30 * lens, PLOT, (0, 1), (0, 1.35))

    # -- a current-limited stage's output: a ramp until x_lin from the rail, then a taper,
    # against the RC that reaches the same point at the same time. x_lin = 0.45 is the value
    # the real probed stages fitted (0.37-0.63).
    XLIN, T, t1 = 0.45, 3.2, 1.0
    t = np.linspace(0, T, 160)
    s = (1 - XLIN) / t1
    emit("d3_cl", t, np.where(t < t1, s * t, 1 - XLIN * np.exp(-(t - t1) * s / XLIN)),
         (0, 0, 300, 110), (0, T), (0, 1.08))
    emit("d3_rc", t, 1 - np.exp(-t / (t1 / np.log(1 / XLIN))), (0, 0, 300, 110), (0, T), (0, 1.08))

    # -- the calibration pins one point: candidates sharing a peak, fanning out elsewhere
    tt = np.linspace(0, 4.2, 150)
    tp = 1.35

    def bell(w):
        u = (tt - tp) / w
        return np.exp(-np.where(u < 0, u, u / 1.7) ** 2)

    for i, w in enumerate((0.34, 0.42, 0.50, 0.58, 0.66, 0.78)):
        emit(f"d8_c{i}", tt, 0.92 * bell(w), (0, 0, 300, 110), (0, 4.2), (0, 1.05))
    emit("d8_pick", tt, 0.92 * bell(0.50), (0, 0, 300, 110), (0, 4.2), (0, 1.05))

    # -- three regimes: the gate each buffer's predriver actually reaches (gate_physics 09-08)
    tg = np.linspace(0, 3.0, 130)
    GB = (0, 0, 140, 84)
    emit("d10_io", tg, np.where(tg < 1.0, 0.55 * tg, 0.55 * np.exp(-(tg - 1.0) / 0.55)), GB, (0, 3), (0, 1.12))
    emit("d10_inv", tg, np.where(tg < 0.35, 0.0, np.where(tg < 0.8, (tg - 0.35) / 0.45,
                                                          np.exp(-(tg - 0.8) / 0.42))), GB, (0, 3), (0, 1.12))
    emit("d10_ex2", tg, np.where(tg < 1.25, 0.70 * (tg / 1.25) ** 0.85,
                                 0.70 * np.exp(-(tg - 1.25) / 0.95)), GB, (0, 3), (0, 1.12))

    # -- the spine: one gate trajectory, whose interior only a truncation reaches
    tq = np.linspace(0, 1, 140)
    emit("d12_gate", tq, 1 - np.exp(-3.4 * tq), (0, 0, 360, 116), (0, 1), (0, 1.1))

    # -- the real runs
    PAD = (0, 0, 330, 150)
    for dev, w, vmax in (("ex2", "810", 1.65), ("ex2", "975", 1.65),
                         ("inv_chain", "104", 1.45), ("inv_chain", "135", 1.45)):
        d = traces[dev]["widths"][w]
        span = max(d["t"])
        for k in ("transistor", "ours", "shipped"):
            emit(f"p_{dev}_{w}_{k}", d["t"], d[k], PAD, (0, span), (-0.08, vmax))
        out[f"rev_{dev}_{w}"] = round(d["reversal_at"] / span * PAD[2], 1)
    d = traces["inv_chain"]["widths"]["104"]
    for k in ("gate_transistor", "gate_ours", "gate_shipped"):
        emit(f"g_inv_104_{k}", d["t"], d[k], (0, 0, 330, 120), (0, max(d["t"])), (-0.08, 1.15))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true",
                    help="re-read the stored runs and refresh the trace cache (needs the .raw files)")
    args = ap.parse_args()

    if args.extract:
        print("extracting real traces from the stored runs:")
        CACHE.write_text(json.dumps(extract_traces(), separators=(",", ":")), encoding="utf-8")
        print(f"  wrote {CACHE.relative_to(ROOT).as_posix()}")
    traces = json.loads(CACHE.read_text(encoding="utf-8"))

    cv = curves(traces)
    html = TEMPLATE.read_text(encoding="utf-8")
    if html.count("/*__CURVES__*/") != 1:
        raise SystemExit("template has no /*__CURVES__*/ placeholder")
    html = html.replace("/*__CURVES__*/",
                        "const CURVES = " + json.dumps(cv, separators=(",", ":")) + ";")

    # every polyline in the page must receive geometry: a blank figure is the failure mode
    import re
    ids = re.findall(r'<polyline id="([^"]+)"', html)
    alias = dict(re.findall(r"(\w+):\"(\w+)\"", html[html.index("var dup ="):][:220]))
    missing = [i for i in ids if i not in cv and i not in alias]
    if missing or len(ids) != len(set(ids)):
        raise SystemExit(f"polylines without geometry: {missing}; duplicate ids: "
                         f"{[i for i in ids if ids.count(i) > 1]}")

    PAGE.write_text(html, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT).as_posix()} "
          f"({PAGE.stat().st_size / 1024:.0f} kB, {len(ids)} polylines, {len(cv)} curves)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
