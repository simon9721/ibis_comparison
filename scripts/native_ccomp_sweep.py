#!/usr/bin/env python3
"""Does native IBIS's outward accumulation scale with C_comp too?

`ccomp_accumulation_2026-09-04` swept the explicit C_comp in the **pybis**
subcircuit and showed the outward accumulation follows it. That establishes
causation for our model only. For native IBIS all we had was the cross-device
correlation -- 0.468 pF gives +1 ps, 1.2 pF gives +67, 5.0 pF gives +93 -- which
is three points across three different buffers.

This is the same within-device control on the other implementation: edit the
`C_comp` line in a copy of the .ibs, hand it to HSPICE's B-element, and re-run.
Nothing else about the file changes, so if the accumulation moves, it moves for
the same reason it does in our model.

The two implementations use C_comp very differently -- native replays V-T tables
with C_comp for load adjustment, pybis back-solves Ku/Kd with the C_comp current
removed and adds the capacitor back explicitly -- so agreement here would say the
accumulation belongs to the IBIS *representation*, not to either implementation.

    py -3.14 scripts/native_ccomp_sweep.py
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
import spicelab as sl  # noqa: E402
from timing_shift_accumulation import ladder, swing  # noqa: E402

R = ROOT / "results"
SRC = R / "defect_b_full_swing_2026-09-03" / "native"
TRANSISTOR = R / "defect_b_full_swing_2026-09-03" / "transistor" / "run.tr0"
OUT = R / "native_ccomp_sweep_2026-09-04"

NOMINAL_PF = 1.2
SCALES = (1.0, 0.5, 0.25, 0.0)
RISE_NS, FALL_NS = 5.0, 15.0


def run_at(scale: float) -> tuple[np.ndarray, np.ndarray]:
    d = OUT / f"x{scale:g}".replace(".", "p")
    d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC / "run.sp", d / "run.sp")
    ibs = (SRC / "input.ibs").read_text(encoding="utf-8", errors="ignore")
    value = NOMINAL_PF * scale
    # Keep min/max in step with typ; the deck asks for typ, but a min/max above
    # typ would be an invalid file and ibischk-style readers can object.
    ibs, n = re.subn(r"^C_comp\s+\S+\s+\S+\s+\S+\s*$",
                     f"C_comp {value:.4f}pF {value:.4f}pF {value:.4f}pF",
                     ibs, count=1, flags=re.M)
    if n != 1:
        raise RuntimeError("could not find the C_comp line")
    (d / "input.ibs").write_text(ibs, encoding="utf-8")
    if not (d / "run.tr0").exists():
        if sl.hspice(d, timeout_s=900) is None:
            raise RuntimeError(f"native x{scale} failed -- see run.lis")
    raw = sl.parse_hspice_tr0(d / "run.tr0")
    return sl.time_ns(raw), sl.trace(raw, "pad")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tr = sl.parse_hspice_tr0(TRANSISTOR)
    grid = np.arange(4.5, 20.0, 0.002)
    ref = np.interp(grid, sl.time_ns(tr), sl.trace(tr, "pad"))

    print(f"  io_buf native IBIS, full swing. Nominal C_comp {NOMINAL_PF} pF.")
    print(f"    {'C_comp':>10}{'out: early':>12}{'late':>7}{'change':>9}")
    for scale in SCALES:
        t, y = run_at(scale)
        y = np.interp(grid, t, y)
        out = ladder(grid, ref, y, FALL_NS, -1, outward=False, strict=False)
        g = np.isfinite(out)
        if not g.any():
            print(f"    {NOMINAL_PF * scale:8.3f}pF   no usable crossings")
            continue
        print(f"    {NOMINAL_PF * scale:8.3f}pF{out[g][0]:>12.0f}"
              f"{out[g][-1]:>7.0f}{swing(out):>9.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
