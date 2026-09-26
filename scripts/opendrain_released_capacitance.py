#!/usr/bin/env python3
"""The open-drain part's own pad capacitance versus bias, released and driven.

The open-drain file declares C_comp 5.0 pF. Two solves of the same die disagree: the
single-fixture loop value is 3.0 pF and the two-fixture push-pull solve gives 1.75 pF. The
"released state is 0.25 pF" figure that has been quoted for this part is io_buf's number, from
a routine explicitly limited to io_buf; no released-state measurement of THIS part exists.

Method, identical to the io_buf measurement so the numbers are comparable:

    I_total(V) = I_conduction(V) + C(V) dV/dt
    a DC sweep is the conduction term with dV/dt exactly zero
    C(V) = [I_ramp(V) - I_dc(V)] / slope

No output-enable pin is needed. This output stage is NMOS-only to ground, so holding the input
at the level that leaves the pull-down off IS the released state. Both input levels are swept
rather than assumed, and the released one is identified by its conduction current.

    py -3.14 scripts/opendrain_released_capacitance.py
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
OUT = ROOT / "results" / "opendrain_ccomp_2026-09-17"
SUP, RAMP_NS, SETTLE_NS = 3.3, 2.0, 20.0
NL = "\n"


def deck(v_in: float, analysis: str) -> str:
    if analysis == "dc":
        drive = "Vpad pad 0 DC 0"
        run_line = f".dc Vpad 0 {SUP} {SUP / 400:.6f}" + NL + ".probe dc I(Vpad)"
    else:
        drive = f"Vpad pad 0 PWL(0n 0  {SETTLE_NS}n 0  {SETTLE_NS + RAMP_NS}n {SUP})"
        run_line = (".probe tran V(pad) I(Vpad)" + NL
                    + f".tran {RAMP_NS / 4000:.6f}n {SETTLE_NS + RAMP_NS}n")
    return ("* open-drain pad capacitance" + NL
            + ".title open-drain pad capacitance" + NL
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


def run(v_in: float, analysis: str, tag: str):
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=True)
    for f in ("buffer.sp", "hspice.mod"):
        if not (d / f).exists():
            shutil.copy2(SRC / f, d / f)
    (d / "run.sp").write_text(deck(v_in, analysis), encoding="utf-8")
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
    w = (t > SETTLE_NS + 0.02 * RAMP_NS) & (t < SETTLE_NS + 0.98 * RAMP_NS)
    return v[w], cur[w]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    grid = np.linspace(0.05 * SUP, 0.85 * SUP, 200)
    slope = SUP / (RAMP_NS * 1e-9)
    print(f"open-drain pad capacitance, supply {SUP} V, ramp {SUP} V in {RAMP_NS} ns\n")
    print(f"{'input':>7}{'DC current at mid-rail':>26}{'C at mid-rail':>16}{'C min':>10}{'C max':>10}  state")
    for v_in in (0.0, SUP):
        tag = f"in{v_in:g}".replace(".", "p")
        v_d, i_d = run(v_in, "dc", tag + "_dc")
        v_r, i_r = run(v_in, "ramp", tag + "_ramp")
        i_dc_mid = float(np.interp(SUP / 2, v_d, i_d))
        c = (np.interp(grid, v_r, i_r) - np.interp(grid, v_d, i_d)) / slope
        c_mid = float(np.interp(SUP / 2, grid, c))
        state = "RELEASED (pull-down off)" if abs(i_dc_mid) < 1e-5 else "driven (pull-down on)"
        print(f"{v_in:>7.1f}{i_dc_mid * 1e3:>23.4f} mA{c_mid * 1e12:>13.3f} pF"
              f"{c.min() * 1e12:>9.3f}{c.max() * 1e12:>9.3f}  {state}")
        np.savetxt(OUT / f"cv_{tag}.csv", np.c_[grid, c * 1e12], delimiter=",",
                   header="pad_v,C_pF", comments="")
    print(f"\ndeclared in the open-drain file: 5.0 pF")
    print(f"single-fixture loop solve: 3.0 pF     two-fixture push-pull solve: 1.75 pF")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
