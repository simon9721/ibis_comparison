#!/usr/bin/env python3
"""Does model accuracy depend on the input edge rate?

The three matrix buffers run at 50 ps input edges, the nine variants at 1 ps. Every comparison
is internally consistent (both sides use that buffer's edge) and stress levels are matched by
measured pad reach, so the pooled numbers are legitimate. What was never tested is whether the
ACCURACY itself depends on the edge rate, because no buffer had been run at both.

This takes one existing model per family, unchanged, and runs it and its transistor at 1 ps and
at 50 ps over the same widths. If peak error against achieved stress is the same at both edges,
the 1 ps choice costs nothing.

    py -3.14 scripts/edge_rate_check.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

OUT = ROOT / "results" / "edge_rate_check_2026-09-17"
CH = ROOT / "results" / "gate_chain_prototype_2026-09-10"
BUILDS = {
    "inv_base8": CH / "inv_base8_c0.6/real_silicon_K7_calibpad50/driver_chain.sub",
    "ex2_base": CH / "ex2_base_c1.7/real_silicon_K3_calibpad50/driver_chain.sub",
}


def transistor_at_edge(v, case: Path, sup: float, w: float, edge_ps: float, tag: str):
    """Re-run this case's transistor deck with a different input edge. Same 50 % width."""
    d = OUT / v / tag
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "run.tr0").exists():
        src = case / "transistor"
        for f in src.iterdir():
            if f.is_file() and not f.name.startswith("run."):
                shutil.copy2(f, d / f.name)
        e = edge_ps / 1000.0
        t_f = 5.0 + w
        pwl = (f"PWL(0n 0  5n 0  {5.0 + e:.6g}n {sup:g}  {t_f:.6g}n {sup:g}  "
               f"{t_f + e:.6g}n 0  22n 0)")
        deck = (src / "run.sp").read_text(encoding="utf-8", errors="replace")
        deck = re.sub(r"Vin in_dig 0 PWL\(.*?\)", f"Vin in_dig 0 {pwl}", deck, flags=re.S)
        (d / "run.sp").write_text(deck, encoding="utf-8")
        rc = base.run_process([str(default_hspice()), "-i", "run.sp", "-o", "run"],
                              d, d / "hspice_stdout.log", 1800)
        if rc != 0 or not (d / "run.tr0").exists():
            raise RuntimeError(f"hspice failed: {d}")
    return gp.tr0_pad(d / "run.tr0")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for v, sub_path in BUILDS.items():
        if not sub_path.exists():
            print(f"\n{v}: no build at {sub_path}"); continue
        sup, _ = gp.VARIANTS[v]
        gp.VARIANT_NAME = v
        sub = sub_path.read_text(encoding="utf-8")
        fs = sorted((ROOT / "results/variant_stress_cases_2026-09-04" / v).glob("full_swing/**/*.tr0"))
        tf, pf = gp.tr0_pad(fs[0])
        rest = float(np.interp(4.5, tf, pf))
        full = float(pf.max() if abs(pf.max() - rest) > abs(pf.min() - rest) else pf.min())
        print(f"\n=== {v}: full-swing excursion {full - rest:+.4f} V, build {sub_path.parent.name}")
        print(f"    {'width':>7} | {'1 ps: stress':>13}{'peak err':>10}{'lag':>6} | "
              f"{'50 ps: stress':>14}{'peak err':>10}{'lag':>6} | {'d(err)':>8}")
        for depth, w, case in gp.cases(v):
            row = {}
            for edge, tag in ((1.0, "e1"), (50.0, "e50")):
                gp.EDGE_PS[v] = edge
                t_si, si = (gp.tr0_pad(case / "transistor/run.tr0") if edge == 1.0
                            else transistor_at_edge(v, case, sup, w, edge, f"d{depth}_e50"))
                m = t_si > 5.0
                pk = float(si[m].max() if (full - rest) > 0 else si[m].min())
                stress = 100.0 * (pk - rest) / (full - rest)
                r = gp.run_ours(OUT / v / f"d{depth}_{tag}_model", sub, sup, w)
                err, lag, _, _ = gp.score(t_si, si, r["t"], r["pad"], w)
                row[edge] = (stress, err, lag)
            s1, e1, l1 = row[1.0]
            s5, e5, l5 = row[50.0]
            print(f"    {w*1e3:>6.0f}p | {s1:>12.1f}%{e1:>9.1f}%{l1:>6.0f} | "
                  f"{s5:>13.1f}%{e5:>9.1f}%{l5:>6.0f} | {e5-e1:>+7.1f}")
        gp.EDGE_PS.pop(v, None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
