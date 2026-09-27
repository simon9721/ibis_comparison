#!/usr/bin/env python3
"""ex2 with the C_comp the device actually has: does the stressed pad improve?

`gate_physics_2026-09-08` measured ex2's C_comp at 1.5-1.75 pF from the Ku-vs-gate
loop, against a declared 5.0. Both IBIS models simulate with the declared value
and every coefficient table was solved with it. This tests the correction the way
a user would apply it: edit the .ibs, rebuild, re-run.

Two stressed widths from the matrix (858, 975 ps) plus the 10 ns control,
transistor references already on disk. Native and ours are run at the declared
5.0 pF and at 1.7 pF; the transistor's Ku is re-solved at both so the coefficient
comparison is apples to apples.

    py -3.14 scripts/ex2_ccomp_correction_test.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402
from pedestal_localization import best_lag, outward_window  # noqa: E402

R = ROOT / "results"
MX = R / "stress_method_matrix_2026-08-20"
REF = MX / "pad_match" / "hspice_references" / "ex2"
FIX = MX / "delay_cmd" / "hspice_fixtures" / "ex2"
CTRL = R / "three_buffer_loaded_swing_stress_sweep_2026-08-14/hspice_references/ex2/transistor/r50_c2pf/long_control/run.tr0"
IBIS0 = REF / "fast_5ps/r50_c2pf/short_high_w810ps_810ps/native/input.ibs"
OUT = R / "ex2_ccomp_correction_2026-09-08"
SUP, R_LOAD, C_LOAD_PF, STOP = 3.3, 50.0, 2.0, 22.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
CCOMPS = (5.0, 1.7)
CASES = {"w858": 0.858, "w975": 0.975, "control": 10.0}


def ibis_with_ccomp(cc: float) -> Path:
    p = OUT / f"ex2_c{cc:.1f}.ibs"
    text = IBIS0.read_text(errors="ignore")
    text = re.sub(r"^C_comp\s+.*$", f"C_comp {cc:.4f}pF {cc:.4f}pF {cc:.4f}pF", text, count=1, flags=re.M)
    p.write_text(text, encoding="utf-8")
    return p


def pwl(width: float) -> str:
    return sl.pulse(0.0, SUP, [5.0, 5.0 + width], edge_ps=50.0, stop_ns=STOP)


def run_hspice(d: Path, deck: str, hspice: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "run.sp").write_text(deck, encoding="utf-8")
    tr0, lis = d / "run.tr0", d / "run.lis"
    ok = tr0.exists() and lis.exists() and "job concluded" in lis.read_text(errors="replace").lower()
    if not ok:
        rc = base.run_process([str(hspice), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 1800)
        if rc != 0 or not tr0.exists():
            raise RuntimeError(f"hspice failed: {d}")
    return tr0


def native(cc: float, tag: str, width: float, hspice: Path):
    d = OUT / f"c{cc:.1f}" / tag / "native"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ibis_with_ccomp(cc), d / "input.ibs")
    deck = f"""* ex2 native, C_comp {cc} pF
.title ex2 native
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {pwl(width)}
VPU pu_ref 0 DC {SUP}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUP}
VGC gc_ref 0 DC 0
* ex2 is a plain Output model: six-node B-element with buffer=2 (the matrix's own form)
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='input.ibs' model='driver' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad) V(ku) V(kd)
.tran 0.002n {STOP}n
.end
"""
    raw = sl.parse_hspice_tr0(run_hspice(d, deck, hspice))
    return sl.time_ns(raw), np.asarray(raw["v(pad)"], float), np.asarray(raw["v(ku)"], float)


def ours(cc: float, tag: str, width: float):
    d = OUT / f"c{cc:.1f}" / tag / "ours"
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "driver.sub").exists():
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis_with_ccomp(cc))),
                            model_name="driver", component_name="MCM Driver 1")
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical", str(d / "driver.sub"))
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    (d / "run.sp").write_text(
        dk.ngspice_header() + ".include driver.sub\n" + dk.supply("VCC", SUP, name="Vdd")
        + f"Vin IN 0 {pwl(width)}\n" + dk.supply("EN", sub.enable_level(SUP), name="Ven")
        + sub.instance("X1") + dk.load("OUT", R_LOAD, C_LOAD_PF)
        + f".tran 0.002n {STOP}n\n.save V(OUT) V(X1.ku) V(X1.kd)\n.end\n", encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1800) is None:
            raise RuntimeError(f"ngspice failed: {d}")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    return sl.time_ns(raw), sl.trace(raw, "out"), sl.signal(raw, "v(x1.ku)")


def fixture(p: Path) -> np.ndarray:
    raw = sl.parse_hspice_tr0(p)
    t = np.asarray(raw["time"], float)
    v = np.asarray(raw[next(k for k in raw if "pad" in k)], float)
    return np.column_stack([t, v, v, v])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    hspice = Path(default_hspice())
    print(f"  {'case':<8}{'C_comp':>7} | {'ours pk err mV':>15}{'ours lag ps':>12}{'ours RMSE mV':>13}"
          f" | {'nat pk err':>11}{'nat lag':>8}{'nat RMSE':>9} | {'Ku ratio ours/nat vs si':>24}")
    for tag, width in CASES.items():
        if tag == "control":
            tr = sl.parse_hspice_tr0(CTRL)
            t_si, si = sl.time_ns(tr), np.asarray(tr[next(k for k in tr if "pad" in k)], float)
            solve_ok = False
        else:
            wps = int(width * 1000)
            tr = sl.parse_hspice_tr0(REF / "transistor" / "r50_c2pf" / f"short_high_w{wps}ps_{wps}ps" / "run.tr0")
            t_si, si = sl.time_ns(tr), np.asarray(tr["v(pad_sp)"], float)
            lo_f, hi_f = fixture(FIX / f"short_high_w{wps}ps/vfix_0/run.tr0"), fixture(FIX / f"short_high_w{wps}ps/vfix_vcc/run.tr0")
            solve_ok = True
        rev = 5.0 + width
        tpk = float(t_si[int(np.argmax(si))])
        lo, hi = outward_window(t_si, si, 5.0)
        g = np.arange(lo, hi, 0.002)
        si_g = np.interp(g, t_si, si)
        for cc in CCOMPS:
            t_o, o, ku_o = ours(cc, tag, width)
            t_n, n, ku_n = native(cc, tag, width, hspice)
            o_g, n_g = np.interp(g, t_o, o), np.interp(g, t_n, n)
            lag_o, _ = best_lag(g, si_g, o_g, lo, hi)
            lag_n, _ = best_lag(g, si_g, n_g, lo, hi)
            cell = ""
            if solve_ok:
                data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis_with_ccomp(cc))),
                                    model_name="driver", component_name="MCM Driver 1")
                s = solve_silicon_kukd(data, lo_f, hi_f, SUP, uniform_ps=5.0)
                ts, ku_si = s[:, 0] * 1e9, s[:, 1]
                t_on = ts[np.where((ts > rev - 0.15) & (ku_si > 0.10))[0][0]]
                win = np.arange(t_on, tpk + 0.4, 0.002)
                su = np.interp(win, ts, ku_si)
                ok = su > 0.1
                qo = float(np.median(np.interp(win, t_o, ku_o)[ok] / su[ok]))
                qn = float(np.median(np.interp(win, t_n, ku_n)[ok] / su[ok]))
                cell = f"{qo:>11.2f} / {qn:<9.2f}"
            print(f"  {tag:<8}{cc:>7.1f} | {(o.max()-si.max())*1e3:>15.0f}{lag_o:>12.0f}"
                  f"{float(np.sqrt(np.mean((o_g-si_g)**2)))*1e3:>13.1f}"
                  f" | {(n.max()-si.max())*1e3:>11.0f}{lag_n:>8.0f}"
                  f"{float(np.sqrt(np.mean((n_g-si_g)**2)))*1e3:>9.1f} | {cell}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
