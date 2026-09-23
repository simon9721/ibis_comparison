#!/usr/bin/env python3
"""Would one short-LOW characterisation point fix io_buf's pull-down?

`results/io_buf_pulldown_depth_2026-09-22` found io_buf's pull-down direction 16-21 points
shallow under stress while its full swing is right to 0.4 %. The pull-down chain's own numbers
say why: it discharges at 1.62/ns against the pull-up chain's 4.08, so on a 200 ps pulse the
gate can only travel about a third of the way. Its threshold is also railed at the fit's upper
bound (0.699999 of 0.7), which is a sign the full-swing fit wanted something it could not have.

The recipe calibrates the pull-up chain on one stressed pad run and leaves the pull-down with
no calibration at all. So: sweep the pull-down chain's discharge rate, and ask whether any one
value matches the transistor at every width - which is what "one characterisation point fixes
it" means - or whether the depths cross, which would make it structural.

Output: results/io_buf_pulldown_calib_2026-09-23/

    py -3.14 scripts/io_buf_pulldown_calib.py [--scales 1 1.5 2 3 4]
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
import gate_ramp_prototype as gp  # noqa: E402
import stage_count_from_file as sc  # noqa: E402
from io_buf_pulldown_depth import cases, short_low  # noqa: E402

OUT = ROOT / "results" / "io_buf_pulldown_calib_2026-09-23"
DEV, K, KD = "io_buf", 1, 3


def scale_pulldown_sdn(text: str, scale: float) -> str:
    """Multiply every pull-down chain stage's discharge rate (the coefficient after the minus
    sign in each BSTGD line) by `scale`. That is the rate at which the chain drives GDN up."""
    pat = re.compile(r"^(BSTGD\d+ STGD\d+ 0 I = .*?\) - )([0-9.eE+-]+)( \* max)", re.M)
    n = len(pat.findall(text))
    if not n:
        raise RuntimeError("no BSTGD lines to scale")
    return pat.sub(lambda m: m.group(1) + f"{float(m.group(2)) * scale:.6g}" + m.group(3), text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scales", type=float, nargs="+", default=[1.0, 1.5, 2.0, 3.0, 4.0])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    gp.VARIANT_NAME = DEV
    sup, _ = gp.VARIANTS[DEV]
    base = (sc.build_dir("step2f", DEV, K, KD) / "driver_chain.sub").read_text(encoding="utf-8")
    cs = cases()
    print(f"  widths: {[w for w, _ in cs]} ps; transistor depths: {[round(p, 1) for _, p in cs]} %")
    rows = []
    for s in args.scales:
        text = scale_pulldown_sdn(base, s) if s != 1.0 else base
        t0, pad0 = short_low(OUT / f"s{s:g}" / "full_swing", text, sup, 10.0)
        rest = float(np.median(pad0[t0 < gp.RISE_NS - 0.2]))
        low = float(np.min(pad0))
        errs = []
        for w, real_pct in cs:
            t, pad = short_low(OUT / f"s{s:g}" / f"w{w}", text, sup, w / 1000.0)
            ours = float(np.min(pad[(t > gp.RISE_NS) & (t < gp.RISE_NS + 3.0)]))
            our_pct = 100.0 * (rest - ours) / (rest - low)
            errs.append(our_pct - real_pct)
            rows.append(dict(sdn_scale=s, width_ps=w, our_depth_pct=round(our_pct, 1),
                             transistor_depth_pct=round(real_pct, 1), err_points=round(our_pct - real_pct, 1),
                             full_swing_V=round(rest - low, 4)))
        print(f"  pull-down s_dn x{s:<4g} depth error by width: "
              + " / ".join(f"{e:+5.1f}" for e in errs)
              + f"   (spread {max(errs) - min(errs):4.1f} points, full swing {rest - low:.3f} V)", flush=True)
    with (OUT / "pulldown_calib.csv").open("w", newline="") as fh:
        w_ = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w_.writeheader()
        w_.writerows(rows)
    print(f"wrote {OUT / 'pulldown_calib.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
