#!/usr/bin/env python3
"""The open-drain part's pad capacitance in its DRIVEN state, by ramp-rate convergence.

The released state measured cleanly at 0.234 pF (opendrain_released_capacitance.py). The driven
state did not, and the reason is numerical: with the pull-down on, conduction at mid-rail is
44 mA while the displacement current at a 2 ns ramp is only C dV/dt ~ 0.8 mA, so C is a small
difference of large numbers.

A faster ramp raises the displacement term proportionally without changing conduction. This
sweeps the ramp duration and looks for a value that stops moving. The RELEASED state is measured
at every ramp rate as a control: it is known to be 0.234 pF, so any rate where the control drifts
is a rate where the method has broken down.

    py -3.14 scripts/opendrain_driven_capacitance.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

SRC = ROOT / "results" / "ex2_variants_2026-09-03" / "opendrain" / "inputs"
OUT = ROOT / "results" / "opendrain_ccomp_2026-09-17" / "driven"
SUP, SETTLE_NS = 3.3, 20.0
RAMPS = [2.0, 0.5, 0.2, 0.05, 0.02, 0.01]
NL = "\n"


def deck(v_in: float, analysis: str, ramp_ns: float) -> str:
    if analysis == "dc":
        drive = "Vpad pad 0 DC 0"
        run_line = f".dc Vpad 0 {SUP} {SUP / 400:.6f}" + NL + ".probe dc I(Vpad)"
    else:
        drive = f"Vpad pad 0 PWL(0n 0  {SETTLE_NS}n 0  {SETTLE_NS + ramp_ns}n {SUP})"
        run_line = (".probe tran V(pad) I(Vpad)" + NL
                    + f".tran {ramp_ns / 4000:.7f}n {SETTLE_NS + ramp_ns}n")
    return ("* open-drain driven-state pad capacitance" + NL
            + ".title od driven capacitance" + NL
            + ".option post=2 probe ingold=2" + NL
            + ".temp 27" + NL
            + f"Vdd vdd 0 DC {SUP}" + NL
            + f"Vin in_dig 0 DC {v_in}" + NL
            + ".include 'hspice.mod'" + NL
            + ".subckt od_buffer in out vdd gnd" + NL
            + ".include 'buffer.sp'" + NL
            + ".ends od_buffer" + NL
            + "XBUF in_dig pad vdd 0 od_buffer" + NL
            + drive + NL + run_line + NL + ".end" + NL)


def run(v_in: float, analysis: str, ramp_ns: float, tag: str):
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=True)
    for f in ("buffer.sp", "hspice.mod"):
        if not (d / f).exists():
            shutil.copy2(SRC / f, d / f)
    (d / "run.sp").write_text(deck(v_in, analysis, ramp_ns), encoding="utf-8")
    res = d / ("run.sw0" if analysis == "dc" else "run.tr0")
    if not res.exists():
        sl.hspice(d, timeout_s=1800, hspice_path=default_hspice())
        if not res.exists():
            raise RuntimeError(f"{tag} failed, see {d / 'run.lis'}")
    if analysis == "dc":
        patched = d / "run_as_tr0.tr0"
        patched.write_bytes(res.read_bytes().replace(b"VOLTS", b"TIME ", 1))
        raw = sl.parse_hspice_tr0(patched)
        return sl.time_ns(raw) / 1e9, -sl.signal(raw, "i(vpad)", "i1(vpad)")
    raw = sl.parse_hspice_tr0(res)
    cur = -sl.signal(raw, "i(vpad)", "i1(vpad)")
    t, v = sl.time_ns(raw), sl.trace(raw, "pad")
    w = (t > SETTLE_NS + 0.02 * ramp_ns) & (t < SETTLE_NS + 0.98 * ramp_ns)
    return v[w], cur[w]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    grid = np.linspace(0.05 * SUP, 0.85 * SUP, 200)
    print("open-drain pad capacitance versus ramp rate. Released is the control: it should stay 0.234 pF.\n")
    print(f"{'ramp':>7}{'dV/dt':>12}{'displacement':>14} | {'RELEASED C':>12}{'drift':>8} | "
          f"{'DRIVEN C':>11}{'conduction':>12}")
    base_rel = None
    for r in RAMPS:
        slope = SUP / (r * 1e-9)
        row = {}
        for v_in, key in ((SUP, "rel"), (0.0, "drv")):
            tg = f"{key}_r{r:g}".replace(".", "p")
            v_d, i_d = run(v_in, "dc", r, tg + "_dc")
            v_r, i_r = run(v_in, "ramp", r, tg + "_ramp")
            c = (np.interp(grid, v_r, i_r) - np.interp(grid, v_d, i_d)) / slope
            row[key] = (float(np.interp(SUP / 2, grid, c)),
                        float(np.interp(SUP / 2, v_d, i_d)))
        c_rel, _ = row["rel"]
        c_drv, i_drv = row["drv"]
        if base_rel is None:
            base_rel = c_rel
        disp = 0.234e-12 * slope
        print(f"{r:>6.2f}n{slope/1e9:>10.2f} V/ns{disp*1e3:>11.2f} mA | "
              f"{c_rel*1e12:>10.3f} pF{(c_rel-base_rel)*1e12:>+7.3f} | "
              f"{c_drv*1e12:>9.3f} pF{i_drv*1e3:>9.1f} mA")
    print(f"\nreleased state, measured earlier at 2 ns: 0.234 pF")
    print(f"declared 5.0 pF   loop solve 3.0 pF   push-pull solve 1.75 pF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
