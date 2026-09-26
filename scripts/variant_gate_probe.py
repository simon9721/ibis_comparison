#!/usr/bin/env python3
"""The one-point calibration run for every variant: probe the output gate.

Re-runs each variant's full-swing transistor deck and its deepest stressed deck
with the last predriver node probed (ex2 family: n4; inv family: the highest
internal VOUTn), normalises the gate to 0 = rest / 1 = full-swing high, and
records the gate maximum at that width. That number is the `--calib W GMAX`
input of the chain prototype. Writes results/variant_gate_probe_2026-09-10/gate_max.json.

    py -3.14 scripts/variant_gate_probe.py --variants ex2_base ex2_weak ...
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402

VAR = ROOT / "results/variant_stress_cases_2026-09-04"
OUT = ROOT / "results/variant_gate_probe_2026-09-10"


def gate_node(src: Path, variant: str) -> str:
    if variant.startswith("ex2"):
        return "v(xdut.n4)"
    sub = next(src.glob("invchain_*_subckt_typ.sp"))
    ns = sorted({int(m) for m in re.findall(r"VOUT(\d+)", sub.read_text(errors="ignore"))})
    return f"v(xdut.vout{ns[-2]})"          # the highest VOUTn is the pad; the one below drives it


def run(src: Path, dst: Path, node: str, hspice: Path, full: bool) -> Path:
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file() and not f.name.startswith("run."):
            shutil.copy2(f, dst / f.name)
    deck = (src / "run.sp").read_text(errors="replace")
    deck = re.sub(r"^\.probe tran .*$", f".probe tran V(IN_DIG) {node.upper()} V(PAD)", deck, flags=re.M)
    if full:
        # keep the stressed deck's edge, move the falling edge to 15 ns
        deck = re.sub(r"Vin in_dig 0 PWL\(0n 0  5n 0  (\S+) (\S+)  \S+ \S+  \S+ 0  22n 0\)",
                      lambda m: f"Vin in_dig 0 PWL(0n 0  5n 0  {m.group(1)} {m.group(2)}  15n {m.group(2)}  15.001n 0  22n 0)", deck)
        assert "15n" in deck, "full-swing edit failed"
    return psp.run_hspice(dst, deck, hspice)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="*", default=[v for v in gp.VARIANTS if v not in gp.MATRIX_SET and v != "io_buf"])
    args = ap.parse_args()
    hspice = Path(default_hspice())
    OUT.mkdir(parents=True, exist_ok=True)
    res_path = OUT / "gate_max.json"
    res = json.loads(res_path.read_text()) if res_path.exists() else {}
    for v in args.variants:
        cases = gp.cases(v)
        depth, w, d = cases[-1]                       # the deepest width
        src = d / "transistor"
        node = gate_node(src, v)
        tr_full = run(src, OUT / v / "full", node, hspice, full=True)
        tr_w = run(src, OUT / v / f"w{depth}", node, hspice, full=False)
        rf = psp.parse_tr0(tr_full)
        tf, gf = np.asarray(rf["time"], float) * 1e9, np.asarray(rf[node], float)
        rest, high = float(np.interp(4.5, tf, gf)), float(np.interp(14.5, tf, gf))
        rw = psp.parse_tr0(tr_w)
        tw, gw = np.asarray(rw["time"], float) * 1e9, np.asarray(rw[node], float)
        gn = (gw - rest) / (high - rest)
        m = (tw > 5.0) & (tw < 5.0 + w + 3.0)
        gmax = float(gn[m].max())
        # the full-swing gate's own timing, for the record
        gfn = (gf - rest) / (high - rest)
        t50 = float(tf[(tf > 5.0) & (gfn > 0.5)][0] - 5.0) * 1e3
        res[v] = dict(node=node, width_ps=int(round(w * 1e3)), depth=depth, gate_max=round(gmax, 4),
                      full_t50_ps=round(t50), rest_v=round(rest, 4), high_v=round(high, 4))
        print(f"  {v:<13} {node:<16} W {w*1e3:>6.0f} ps  gate max {gmax:.3f}   (full-swing t50 {t50:.0f} ps)")
        res_path.write_text(json.dumps(res, indent=2))
    print(f"  wrote {res_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
