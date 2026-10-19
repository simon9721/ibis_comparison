#!/usr/bin/env python3
"""The native element's own coefficients through one complete transition of ex2.

For Fig. 8(b) of the paper: HSPICE's B-element with ramp_rwf=2 ramp_fwf=2 (the two-waveform
mode), driven by a 10 ns pulse into the test load (50 ohm and 2 pF), with its pull-up and
pull-down scaling coefficients probed through xv_pu / xv_pd (PrimeSim HSPICE User Guide: Signal
Integrity, T-2022.06, ch. 8). The file is the one the probed-map setting uses
(results/gate_cascade_prototype_2026-09-09/ex2_c1.7/input_ccomp.ibs, C_comp 1.7 pF), so the
coefficients can be laid over the converter's two-fixture solution of the same file.

Output: native_full_swing/ex2_c1.7.npz (t_ns, pad, ku, kd) and the HSPICE run next to it.

    py -3.14 results/stage_law_doc_2026-10-01/native_full_swing.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
import spicelab as sl  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "native_full_swing"
IBS = ROOT / "results" / "gate_cascade_prototype_2026-09-09" / "ex2_c1.7" / "input_ccomp.ibs"
SUP = 3.3
DECK = f"""* native element, complete transition, coefficients probed
.title native full swing ex2 (C_comp 1.7 pF)
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5n 0  5.05n {SUP}  15n {SUP}  15.05n 0  22n 0)
VPU pu_ref 0 DC {SUP}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUP}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='input.ibs' model='driver' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd
Rload pad 0 50.0
Cload pad 0 2.0p
.probe tran V(pad) V(ku) V(kd)
.tran 0.002n 22.0n
.end
"""


def main() -> int:
    d = OUT / "ex2_c1.7"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(IBS, d / "input.ibs")
    (d / "run.sp").write_text(DECK, encoding="utf-8")
    rc = base.run_process([str(default_hspice()), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 600)
    if rc != 0 or not (d / "run.tr0").exists():
        raise SystemExit(f"hspice failed (rc {rc})")
    raw = sl.parse_hspice_tr0(d / "run.tr0")
    t = sl.time_ns(raw)
    pad, ku, kd = (np.asarray(raw[k], float) for k in ("v(pad)", "v(ku)", "v(kd)"))
    np.savez(OUT / "ex2_c1.7.npz", t_ns=t, pad=pad, ku=ku, kd=kd)
    m = (t > 5) & (t < 16)
    print(f"pad {pad[m].min():.3f}..{pad[m].max():.3f} V, Ku {ku[m].min():.3f}..{ku[m].max():.3f}, "
          f"Kd {kd[m].min():.3f}..{kd[m].max():.3f} -> {OUT / 'ex2_c1.7.npz'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
