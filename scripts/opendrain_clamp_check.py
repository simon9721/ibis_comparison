#!/usr/bin/env python3
"""Item 6 verification: regenerate the open-drain gate-state model with the converter (I-V
pwl arguments now clamped to the table range) and run the 1 kOhm rise-then-fall bench that
diverged on 2026-09-11. Also regenerates the push-pull ex2 model and diffs it against the
shipped build to show the only change is the clamp.

    py -3.14 scripts/opendrain_clamp_check.py
"""
from __future__ import annotations

import difflib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
import spice_decks as dk  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402

R = ROOT / "results"
O = R / "opendrain_risefall_2026-09-11"
OD_IBIS = R / "ex2_variants_2026-09-03/opendrain/ibis/ex2_opendrain.ibs"
SUP, RPU, CL, STOP, T_REL, T_PD = 3.3, 1000.0, 2.0, 26.0, 5.0, 17.0


def generate(ibis: Path, out: Path):
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    out.parent.mkdir(parents=True, exist_ok=True)
    subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(out))
    return out.read_text(encoding="utf-8")


def main() -> int:
    # 1. push-pull ex2: only the four pwl arguments should change
    ex2_ibis = gp.VARIANTS["ex2"][1]
    new = generate(ex2_ibis, O / "clamp_check" / "ex2_driver.sub")
    old = (R / "gate_cascade_prototype_2026-09-09/ex2_c1.7/shipped/driver.sub").read_text(encoding="utf-8")
    diff = [l for l in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0) if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    changed = [l[:60] for l in diff if l.startswith("+")]
    print(f"ex2 push-pull regenerated: {len(diff)//2} lines differ from the shipped build:")
    for l in changed:
        print("   ", l)
    # 2. open-drain on the 1 kOhm bench
    d = O / "gatestate_clamped_converter"
    d.mkdir(parents=True, exist_ok=True)
    sub_text = generate(OD_IBIS, d / "driver.sub")
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = sl.pulse(0.0, SUP, [T_REL, T_PD], start_high=False, stop_ns=STOP)
    deck = (dk.ngspice_header() + ".include driver.sub\n" + dk.supply("VCC", SUP, name="Vdd") + f"Vin IN 0 {pwl}\n"
            + dk.supply("EN", sub.enable_level(SUP), name="Ven") + sub.instance("X1")
            + f"Rpu OUT VCC {RPU}\nCload OUT 0 {CL}p\n.tran 0.002n {STOP}n\n.save V(OUT) V(X1.kd)\n.end\n")
    (d / "run.sp").write_text(deck, encoding="utf-8")
    if sl.ngspice(d, timeout_s=1800) is None:
        print("open-drain 1 kOhm bench: ngspice FAILED")
        return 1
    raw = sl.parse_ngspice_raw(d / "run.raw")
    t, v = sl.time_ns(raw), sl.trace(raw, "out")
    tr = sl.parse_hspice_tr0(O / "transistor/run.tr0")
    t_si, si = sl.time_ns(tr), np.asarray(tr["v(pad_sp)"], float)
    dg = sl.parse_ngspice_raw(O / "gatestate_clamped_diag/run.raw")
    t_d, v_d = sl.time_ns(dg), sl.trace(dg, "out")
    for name, tt, vv in (("transistor", t_si, si), ("converter, clamped (this build)", t, v), ("hand-clamped diagnostic (09-11)", t_d, v_d)):
        rest = float(np.interp(4.5, tt, vv))
        high = float(np.interp(16.99, tt, vv))
        g2 = np.arange(17, 22, 0.001)
        b = np.interp(g2, tt, vv)
        f50 = g2[int(np.argmax(b < 0.5 * (high + rest)))] - 17
        print(f"  {name:<34} rest {rest:.3f} V  high at 17 ns {high:.3f} V  fall 50 % {f50:.3f} ns  min {vv.min():+.2f} V")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
