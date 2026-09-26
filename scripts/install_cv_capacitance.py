#!/usr/bin/env python3
"""Replace the fixed C_comp with the netlist's measured C(V), and re-measure.

The chain so far:

* the model falls progressively behind the transistor on the way out of an event
  (`timing_shift_accumulation_2026-09-04`);
* that accumulation is caused by the explicit C_comp, in both IBIS
  implementations (`ccomp_accumulation_2026-09-04`, `native_ccomp_sweep_2026-09-04`);
* but the golden-waveform test says the declared value is *right* for
  reconstructing the model's own V-T tables (`golden_waveform_test_2026-09-03`);
* and the netlist's real pad capacitance is neither constant nor that size --
  0.25 pF in high-Z, 0.40-0.54 pF with the pull-down on, 0.37-1.12 pF with the
  pull-up on, against a declared 1.2 pF (`pad_capacitance_2026-09-04`).

That points at the capacitor being the wrong *shape* rather than the wrong
*size*. This tests it.

**Both places have to change together.** pybis back-solves Ku/Kd from the V-T
tables with the C_comp displacement current subtracted out
(`generating_current_data`: `i_c_comp = c_comp * dvt/dt`) and then puts an
explicit capacitor back in the netlist. Changing only the netlist would leave Ku
carrying a constant-C_comp subtraction it no longer matches -- which is the
mistake the earlier "remove C_comp" experiment made. So the solve is patched to
use C(V) as well.

**Two variants, to separate shape from size:**

* `cv` -- the measured C(V) as it stands. Changes both.
* `cv_scaled` -- the same curve rescaled so its mean equals the declared 1.2 pF.
  Same size, different shape. This is the one that tests the hypothesis.

    py -3.14 scripts/install_cv_capacitance.py
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
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
from timing_shift_accumulation import ladder, swing  # noqa: E402

R = ROOT / "results"
CV = R / "pad_capacitance_2026-09-04" / "io_buf"
BENCH = R / "defect_b_full_swing_2026-09-03" / "pybis_plain"
TRANSISTOR = R / "defect_b_full_swing_2026-09-03" / "transistor" / "run.tr0"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
OUT = R / "cv_capacitance_2026-09-04"

MODEL, COMPONENT = "driver", "MCM Driver 1"
DECLARED_F = 1.2e-12
FALL_NS = 15.0

_ORIGINAL = pb.generating_current_data


def measured_cv() -> tuple[np.ndarray, np.ndarray]:
    """The mean of the two driven states.

    Through a transition both devices are partly on, so neither single-state
    curve is the right one to stand for the whole event; their mean is the
    defensible one-curve summary. The high-Z curve is the pure junction
    capacitance with no channel and is the wrong thing to install for a driven
    buffer.
    """
    lo = np.loadtxt(CV / "cv_inlo.csv", delimiter=",", skiprows=1)
    hi = np.loadtxt(CV / "cv_inhi.csv", delimiter=",", skiprows=1)
    v = lo[:, 0]
    return v, 0.5 * (lo[:, 1] + np.interp(v, hi[:, 0], hi[:, 1]))


def patch_solver(v: np.ndarray, c: np.ndarray) -> None:
    """Make the Ku/Kd solve subtract C(V) dV/dt instead of C_comp dV/dt."""
    def wrapper(ibis_data, time, corner=1, waveform_obj=None):
        out = list(_ORIGINAL(ibis_data, time, corner, waveform_obj))
        vt = np.interp(time, waveform_obj.data[:, 0], waveform_obj.data[:, corner])
        out[5] = np.interp(vt, v, c) * pb.differentiate(vt, time)
        return tuple(out)
    pb.generating_current_data = wrapper


def build(tag: str, v: np.ndarray, c: np.ndarray) -> Path:
    """Generate the subcircuit with C(V) in the solve and in the netlist."""
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=True)
    patch_solver(v, c)
    try:
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                            model_name=MODEL, component_name=COMPONENT)
        subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical",
                                        str(d / "driver.sub"))
    finally:
        pb.generating_current_data = _ORIGINAL

    # Swap the fixed capacitor for a behavioural one. ngspice takes
    # `Cxxx n+ n- C='expr'` for a voltage-dependent capacitance.
    # ngspice's pwl() takes a flat comma-separated x0, y0, x1, y1, ... list --
    # the same shape the generated I-V tables already use. Grouping the pairs
    # with spaces is a syntax error.
    table = ", ".join(f"{vv:.6g}, {cc:.6e}" for vv, cc in zip(v, c))
    sub = (d / "driver.sub").read_text(encoding="utf-8")
    sub, n = re.subn(r"^C2 DIE VSS \{C_comp\}\s*$",
                     f"C2 DIE VSS C='pwl(V(DIE,VSS), {table})'",
                     sub, count=1, flags=re.M)
    if n != 1:
        raise RuntimeError(f"{tag}: could not find the C_comp capacitor line")
    (d / "driver.sub").write_text(sub, encoding="utf-8")
    shutil.copyfile(BENCH / "run.sp", d / "run.sp")
    return d


def measure(d: Path, ref: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1800) is None:
            raise RuntimeError(f"{d.name} failed -- see ngspice.log")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    y = np.interp(grid, sl.time_ns(raw), sl.trace(raw, "out"))
    return ladder(grid, ref, y, FALL_NS, -1, outward=False, strict=False)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    v, c = measured_cv()
    print(f"  measured C(V): {c.min()*1e12:.2f} .. {c.max()*1e12:.2f} pF, "
          f"mean {c.mean()*1e12:.2f} pF   (declared {DECLARED_F*1e12:.2f} pF)")

    tr = sl.parse_hspice_tr0(TRANSISTOR)
    grid = np.arange(4.5, 20.0, 0.002)
    ref = np.interp(grid, sl.time_ns(tr), sl.trace(tr, "pad"))

    variants = [("cv", v, c),
                ("cv_scaled", v, c * (DECLARED_F / c.mean()))]
    print(f"\n    {'variant':<12}{'mean C':>9}{'out: early':>12}{'late':>7}"
          f"{'change':>9}")
    print(f"    {'constant (nominal)':<12}{DECLARED_F*1e12:8.2f}p"
          f"{'+22':>12}{'+91':>7}{'+69':>9}   [from ccomp_accumulation]")
    for tag, vv, cc in variants:
        lad = measure(build(tag, vv, cc), ref, grid)
        g = np.isfinite(lad)
        if not g.any():
            print(f"    {tag:<12}   no usable crossings")
            continue
        print(f"    {tag:<12}{cc.mean()*1e12:8.2f}p{lad[g][0]:>12.0f}"
              f"{lad[g][-1]:>7.0f}{swing(lad):>9.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
