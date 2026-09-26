#!/usr/bin/env python3
"""The unstressed ex2 bench that the accumulation study was missing.

`timing_shift_accumulation_2026-09-04` measures how far the model drifts from the
transistor on the way out of an event, and uses an unstressed full-swing run as
the control that separates "our model does this" from "IBIS does this". io_buf and
inv_chain had one on disk; **ex2 did not** -- the only ex2 full-swing bench was the
open-drain variant, which is a different buffer.

So ex2's accumulation (+54..+103 ps) could not be attributed. This builds the
missing control: transistor, native IBIS and pybis on ex2 base, full swing, using
the campaign's own deck builders so the bench is identical to the stressed cases
apart from the pulse being long enough to settle.

    py -3.14 scripts/ex2_full_swing_control.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
import spicelab as sl  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402

OUT = ROOT / "results" / "ex2_full_swing_control_2026-09-04"

# Long enough that the pad settles at both ends. ex2's stressed cases are
# 688-975 ps, so 6 ns is many times the transition and unambiguously unstressed.
EDGE_NS, WIDTH_NS, STOP_NS = 0.050, 6.0, 16.0
DEVICE_ID = "ex2"


def main() -> int:
    device = next(d for d in base.DEVICES if d.device_id == DEVICE_ID)
    case = base.PulseCase(f"full_swing_{WIDTH_NS * 1000:.0f}ps", EDGE_NS,
                          "short_high", WIDTH_NS, STOP_NS, "full swing")
    profile = base.Profile("fast", "fast edge", device.fast_ibis)
    OUT.mkdir(parents=True, exist_ok=True)
    hspice, ngspice = default_hspice(), default_ngspice(console=True)

    print(f"  {device.device_id}: full swing, {WIDTH_NS * 1000:.0f} ps pulse")
    tr, _ = base.run_transistor(device, case, OUT, hspice, 900)
    print("    transistor ok")
    nat, _ = base.run_native_ibis(device, profile, case, OUT, hspice, 900)
    print("    native ok")

    # pybis: generate the stock InputDriven subcircuit, then run it through the
    # campaign's ngspice path so the deck matches the stressed cases exactly.
    from pybis2spice import pybis2spice as pb, subcircuit
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                        model_name=device.model, component_name=device.component)
    model = OUT / f"{device.subckt}.sub"
    subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical",
                                    str(model))
    pyb, _ = base.run_ngspice(device, profile, case, "plain", "typ", model, OUT,
                              ngspice, 900)
    if pyb is None:
        print("    pybis run failed")
        return 1
    print("    pybis ok")

    def pad(d):
        for k in d:
            if "pad" in k.lower() or k.lower() in ("out", "v(out)"):
                return np.asarray(d[k], dtype=float)
        raise KeyError(f"no pad in {list(d)}")

    grid = np.arange(4.5, STOP_NS - 0.1, 0.002)
    cols = {}
    for name, d in (("silicon", tr), ("native", nat), ("pybis", pyb)):
        t = np.asarray(d[next(k for k in d if k.lower().startswith("time"))],
                       dtype=float)
        t = t * 1e9 if t.max() < 1e-3 else t
        cols[name] = np.interp(grid, t, pad(d))

    import csv
    path = OUT / "full_swing.csv"
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["time_ns", "silicon_pad", "hspice_pad", "pybis_pad"])
        w.writerows(np.column_stack([grid, cols["silicon"], cols["native"],
                                     cols["pybis"]]))
    print(f"  wrote {path.relative_to(ROOT)}")
    for name in ("silicon", "native", "pybis"):
        y = cols[name]
        print(f"    {name:<10} pad {y.min():+.3f} .. {y.max():+.3f} V")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
