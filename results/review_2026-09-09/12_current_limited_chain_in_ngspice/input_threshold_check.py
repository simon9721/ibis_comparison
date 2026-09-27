#!/usr/bin/env python3
"""What the IBIS input threshold does to a stressed pulse on inv_chain.

The inv_chain IBIS file declares Vinl 0.8 V / Vinh 2.0 V on a 1.8 V part, so
the converter's digital input (NINX) switches at 1.4 V: with 50 ps input edges
every pulse reaches the command layer ~29 ps narrower than the transistor's
first inverter (threshold ~0.9 V) sees it. This re-scores the shipped model
with the threshold moved to mid-supply, nothing else changed.

    py -3.14 scripts/input_threshold_check.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import gate_ramp_prototype as gp  # noqa: E402

G = ROOT / "results/gate_cascade_prototype_2026-09-09"


def main() -> int:
    for dev, mdir, thr in (("inv_chain", "inv_chain_c0.6", 0.9), ("ex2", "ex2_c1.7", 1.65)):
        sup, _ = gp.VARIANTS[dev]
        gp.VARIANT_NAME = dev
        ship = (G / mdir / "shipped/driver.sub").read_text(encoding="utf-8")
        old = re.search(r"input_threshold=([\d.]+)", ship).group(1)
        mod = ship.replace(f"input_threshold={old}", f"input_threshold={thr}", 1)
        cs = gp.cases(dev)
        refs = {d_: gp.tr0_pad(d / "run.tr0") for d_, _, d in cs}
        print(f"\n  {dev}: shipped model, input threshold {old} V (from Vinh/Vinl) vs {thr} V (mid-supply)")
        print(f"    {'threshold':<12} | " + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs) + " | " + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs))
        for name, txt, d0 in ((old, ship, G / mdir / "shipped"), (str(thr), mod, G / mdir / f"shipped_thr{thr:g}")):
            pks, lags = [], []
            for depth, w, d in cs:
                r = gp.run_ours(d0 / f"d{depth}", txt, sup, w)
                pk, lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
                pks.append(pk)
                lags.append(lag)
            print(f"    {name:<12} | " + "".join(f"{x:>9.1f}" for x in pks) + " | " + "".join(f"{x:>9.0f}" for x in lags))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
