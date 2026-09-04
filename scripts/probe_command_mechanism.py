#!/usr/bin/env python3
"""Probe the command node of both builds, so how delay_cmd works can be shown.

The difference between the two is one line of the generated subcircuit:

    gate_state   CGUPCMD GUPCMD 0 {gate_c} ic=0            a capacitor
                 RGUPCMD GUPCMD 0 1e15                     across 1e15 ohm
                 BGUPCMDON  I = -{gate_c}*V(PUONP)/edge_delay   a packet per edge
    delay_cmd    BGUPCMD GUPCMD 0 V = V(PUCMDLVL)          driven by the level

The first integrates a fixed packet of charge on every input edge and has no
resistive path to remove it, so a truncated pulse leaves some behind. The second
is a function of the present input level, so it returns to exactly zero.

That is the whole mechanism, and it is visible directly on the command node --
but nothing in the study had ever plotted the two side by side. This runs both
builds on one truncated io_buf pulse and saves the command, the gate state it
drives, Ku, and the pad, so the chain can be shown rather than asserted.

    py -3.14 scripts/probe_command_mechanism.py
"""
from __future__ import annotations

import csv
import re
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

IBIS = ROOT / "results" / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
OUT = ROOT / "results" / "command_mechanism_2026-09-04"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
RISE_NS, WIDTH_NS, STOP_NS = 5.0, 2.354, 22.0   # the case the offset slide uses

BUILDS = (("gate_state", "InputDrivenTwoStateGateDirectionalDualResidualFull"),
          ("delay_cmd", "InputDrivenTwoStateGateDelayCommandFull"))

# Command, the gate state it drives, the coefficient, and the pad.
PROBES = ("gupcmd", "gup", "ku", "kd")


def run(tag: str, subckt: str) -> dict[str, np.ndarray] | None:
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", subckt, data, "Typical",
                                    str(d / "driver.sub"))
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    hi = RISE_NS + WIDTH_NS
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + 0.001}n {SUPPLY}  "
           f"{hi}n {SUPPLY}  {hi + 0.001}n 0  {STOP_NS}n 0)")
    saves = " ".join(f"V(X1.{p})" for p in PROBES)
    deck = (dk.ngspice_header()
            + ".include driver.sub\n"
            + dk.supply("VCC", SUPPLY, name="Vdd")
            + f"Vin IN 0 {pwl}\n"
            + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
            + sub.instance("X1")
            + dk.load("OUT", R_LOAD, C_LOAD_PF)
            + f".tran 0.002n {STOP_NS}n\n.save V(OUT) {saves}\n.end\n")
    sp, raw = d / "run.sp", d / "run.raw"
    if not (raw.exists() and sp.exists() and sp.read_text(encoding="utf-8") == deck):
        sp.write_text(deck, encoding="utf-8")
        if sl.ngspice(d, timeout_s=900) is None:
            print(f"  {tag}: ngspice failed")
            return None
    r = sl.parse_ngspice_raw(raw)
    out = {"time_ns": sl.time_ns(r), "pad": sl.trace(r, "out")}
    for p in PROBES:
        try:
            out[p] = sl.signal(r, f"v(x1.{p})", f"x1.{p}")
        except Exception:                              # noqa: BLE001
            out[p] = np.full(len(out["time_ns"]), np.nan)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    got = {}
    for tag, subckt in BUILDS:
        r = run(tag, subckt)
        if r is None:
            return 1
        got[tag] = r
        print(f"  {tag}: {', '.join(k for k in r if np.any(np.isfinite(r[k])))}")

    grid = got["gate_state"]["time_ns"]
    cols = {"time_ns": grid}
    for tag in got:
        for k, v in got[tag].items():
            if k == "time_ns":
                continue
            cols[f"{tag}_{k}"] = np.interp(grid, got[tag]["time_ns"], v)
    path = OUT / "command_mechanism.csv"
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(list(cols))
        w.writerows(np.column_stack(list(cols.values())))
    print(f"\nwrote {path.relative_to(ROOT)}")

    rev = RISE_NS + WIDTH_NS
    tail = (grid > rev + 1.0) & (grid < rev + 1.7)
    for tag in got:
        c = cols[f"{tag}_gupcmd"][tail]
        print(f"  {tag:<12} command on the tail: {np.mean(c):+.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
