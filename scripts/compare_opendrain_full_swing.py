#!/usr/bin/env python3
"""Open-drain ex2: transistor vs native IBIS vs pybis, on a pull-up load.

Item 2 of `0902_plan.md`, completed. The open-drain model is valid now that the
s2ibispy clamp double-count is fixed (commit c780715 upstream), so the
comparison item 2 exists for can finally run.

An open-drain has no pullup: it drives the pad low and releases it high. So the
bench is not the push-pull 50 ohm-to-ground bench -- the pad would never rise.
It is a pull-up termination, 50 ohm to VCC with a small load cap, which is how
open-drain nets are actually built. All three builds see the identical load.

    transistor    HSPICE on the open-drain netlist (pullup removed) -- truth
    native IBIS   HSPICE reading the generated .ibs
    pybis         ngspice on the InputDriven subcircuit from the same .ibs

Input pulses low at 5 ns and 15 ns (the buffer pulling the pad down); between,
the pad is released and the 50 ohm pullup restores it to VCC.

    py -3.14 scripts/compare_opendrain_full_swing.py
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python",
          ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

VAR = ROOT / "results" / "ex2_variants_2026-09-03" / "opendrain"
IBIS = VAR / "ibis" / "ex2_opendrain.ibs"
OUT = ROOT / "results" / "ex2_opendrain_full_swing_2026-09-03"
NGSPICE = ROOT / ".codex_deps" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY_V = 3.3
R_PULLUP, C_LOAD_PF = 50.0, 2.0   # pull-up termination: 50 ohm to VCC, 2 pF
LOW_NS, HIGH_NS, STOP_NS = 5.0, 15.0, 22.0   # pad driven low between these
HSPICE_TIMEOUT_S, NGSPICE_TIMEOUT_S = 600, 600

TRANSISTOR, NATIVE, PYBIS = "#111111", "#2B6CA3", "#C02626"
DPI = 175


def pwl() -> str:
    """Input starts low, releases high at 5 ns, drives low again at 15 ns.

    Starting low matters: the InputDriven model initializes with the pulldown on
    (output low) and only establishes state on the first detected edge, so a
    stimulus that started high would leave t < 5 ns in the wrong state for pybis
    while the transistor sat released-high. Starting low aligns the initial
    condition across all three builds, and each edge is then measured cleanly:
    a release (low->high) at 5 ns and a drive (high->low) at 15 ns."""
    return (f"PWL(0n 0  {LOW_NS}n 0  {LOW_NS + 0.001}n {SUPPLY_V}  "
            f"{HIGH_NS}n {SUPPLY_V}  {HIGH_NS + 0.001}n 0  {STOP_NS}n 0)")


def run(cmd: list[str], cwd: Path, log: str, timeout: int) -> int:
    with (cwd / log).open("w", encoding="utf-8") as handle:
        try:
            return subprocess.run(cmd, cwd=str(cwd), stdout=handle,
                                  stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            handle.write(f"\ntimed out after {timeout} s\n")
            return 124


def transistor(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in os.listdir(VAR / "inputs"):
        shutil.copy2(VAR / "inputs" / name, out_dir / name)
    deck = f"""* ex2 open-drain transistor, pull-up load
.title ex2 open-drain transistor
.option post=2 probe accurate ingold=2
.temp 27
Vdd vdd 0 DC {SUPPLY_V}
Vin in_dig 0 {pwl()}
.include 'hspice.mod'
.subckt ex2_buffer in out vdd gnd
.include 'buffer.sp'
.ends ex2_buffer
XREF in_dig pad_sp vdd 0 ex2_buffer
Rpu pad_sp vdd {R_PULLUP}
Cload pad_sp 0 {C_LOAD_PF}p
.probe tran V(in_dig) V(pad_sp)
.tran 0.001n {STOP_NS}n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    run([str(default_hspice()), "-i", "run.sp", "-o", "run"], out_dir, "hspice.log",
        HSPICE_TIMEOUT_S)
    tr0 = out_dir / "run.tr0"
    if not tr0.exists():
        return None
    raw = parse_hspice_tr0(tr0)
    k = {x.lower(): x for x in raw}
    return (np.asarray(raw[k["time"]]) * 1e9,
            np.asarray(raw[next(k[x] for x in k if "pad" in x)]))


def native_ibis(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(IBIS, out_dir / IBIS.name)
    # Open-drain: no pullup reference needed, but the B-element still takes the
    # standard node order; pu_ref simply goes unused by a pulldown-only model.
    deck = f"""* ex2 open-drain native IBIS, pull-up load
.title ex2 open-drain native IBIS
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {pwl()}
VPU pu_ref 0 DC {SUPPLY_V}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUPPLY_V}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='{IBIS.name}' model='{MODEL}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2
Rpu pad_ibis od_rail {R_PULLUP}
Vodrail od_rail 0 DC {SUPPLY_V}
Cload pad_ibis 0 {C_LOAD_PF}p
.probe tran V(in_dig) V(pad_ibis)
.tran 0.001n {STOP_NS}n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    run([str(default_hspice()), "-i", "run.sp", "-o", "run"], out_dir, "hspice.log",
        HSPICE_TIMEOUT_S)
    tr0 = out_dir / "run.tr0"
    if not tr0.exists():
        return None
    raw = parse_hspice_tr0(tr0)
    k = {x.lower(): x for x in raw}
    return (np.asarray(raw[k["time"]]) * 1e9,
            np.asarray(raw[next(k[x] for x in k if "pad" in x)]))


def pybis(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    from pybis2spice import pybis2spice as pb, subcircuit
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    sub = out_dir / "driver.sub"
    subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical", str(sub))
    if not sub.exists():
        return None
    text = sub.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    name = match.group(1)
    pins = [p for p in match.group(2).split("params:")[0].split() if "=" not in p]
    node_for = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0", "GND": "0"}
    nodes = [node_for.get(p.upper(), p) for p in pins]
    deck = f"""* ex2 open-drain pybis, pull-up load
.include driver.sub
Vdd VCC 0 DC {SUPPLY_V}
Vin IN 0 {pwl()}
Ven EN 0 DC 0   $ active-low enable: EN low enables the open-drain
X1 {' '.join(nodes)} {name}
Rpu OUT VCC {R_PULLUP}
Cload OUT 0 {C_LOAD_PF}p
.tran 0.001n {STOP_NS}n
.save V(OUT) V(IN)
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    code = run([str(NGSPICE), "-b", "-r", "run.raw", "run.sp"], out_dir, "ngspice.log",
               NGSPICE_TIMEOUT_S)
    raw_path = out_dir / "run.raw"
    if code != 0 or not raw_path.exists():
        return None
    raw = parse_ngspice_raw(raw_path)
    k = {x.lower(): x for x in raw}
    return (np.asarray(raw[k["time"]]) * 1e9,
            np.asarray(raw[next(k[x] for x in k if "out" in x)]))


def crossing(t, y, level, rising, after):
    for i in range(1, len(y)):
        if t[i] < after:
            continue
        if (rising and y[i - 1] < level <= y[i]) or (not rising and y[i - 1] > level >= y[i]):
            return float(t[i - 1] + (level - y[i - 1]) * (t[i] - t[i - 1]) / (y[i] - y[i - 1]))
    return float("nan")


def score(model, ref):
    tm, pm = model
    tr, pr = ref
    lo, hi = max(tm[0], tr[0]), min(tm[-1], tr[-1])
    grid = np.linspace(lo, hi, 40000)
    a, b = np.interp(grid, tm, pm), np.interp(grid, tr, pr)
    half = 0.5 * (np.nanmax(b) + np.nanmin(b))
    return {
        "rmse_mv": float(np.sqrt(np.trapezoid((a - b) ** 2, grid) / (grid[-1] - grid[0]))) * 1e3,
        "worst_mv": float(np.nanmax(np.abs(a - b))) * 1e3,
        "release_shift_ps": (crossing(grid, a, half, True, LOW_NS - 0.5)
                             - crossing(grid, b, half, True, LOW_NS - 0.5)) * 1e3,
        "drive_shift_ps": (crossing(grid, a, half, False, HIGH_NS - 0.5)
                           - crossing(grid, b, half, False, HIGH_NS - 0.5)) * 1e3,
    }


def figure(path, traces):
    fig, axes = plt.subplots(2, 1, figsize=(12.6, 8.2))
    for axis, span, title in ((axes[0], (LOW_NS - 0.3, LOW_NS + 3.0), "buffer releases, pull-up restores high"),
                              (axes[1], (HIGH_NS - 0.3, HIGH_NS + 3.0), "buffer drives the pad low")):
        for label, colour, w, data in (("HSPICE transistor", TRANSISTOR, 3.4, traces.get("transistor")),
                                       ("HSPICE native IBIS", NATIVE, 2.2, traces.get("native")),
                                       ("ngspice pybis", PYBIS, 2.0, traces.get("pybis"))):
            if data is None:
                continue
            axis.plot(data[0], data[1], color=colour, lw=w, label=label,
                      ls="-" if "transistor" in label else (0, (5, 2.2)))
        axis.set_xlim(*span)
        axis.set_ylabel("Pad (V)", fontsize=12)
        axis.set_title(f"ex2 open-drain  |  {title}", fontsize=13.5, fontweight="bold", pad=8)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=11)
        for s in axis.spines.values():
            s.set_color("#3A4753")
    axes[0].legend(fontsize=11, loc="upper right", framealpha=0.95)
    axes[1].set_xlabel("Time (ns)", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = (args.out if args.out.is_absolute() else ROOT / args.out).resolve()
    (out / "plots").mkdir(parents=True, exist_ok=True)

    traces = {"transistor": transistor(out / "transistor"),
              "native": native_ibis(out / "native_ibis"),
              "pybis": pybis(out / "pybis")}
    if traces["transistor"] is None:
        print("transistor run failed")
        return 1

    print(f"{'build':<16}{'RMSE mV':>9}{'worst mV':>10}{'release ps':>12}{'drive ps':>11}")
    rows = []
    for label, key in (("native IBIS", "native"), ("pybis", "pybis")):
        if traces[key] is None:
            print(f"{label:<16}   run failed")
            continue
        m = score(traces[key], traces["transistor"])
        print(f"{label:<16}{m['rmse_mv']:9.2f}{m['worst_mv']:10.1f}"
              f"{m['release_shift_ps']:12.1f}{m['drive_shift_ps']:11.1f}")
        rows.append({"build": key, **{k: round(v, 4) for k, v in m.items()}})
    figure(out / "plots" / "ex2_opendrain_full_swing.png", traces)

    with (out / "opendrain_comparison.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["build", "rmse_mv", "worst_mv",
                                          "release_shift_ps", "drive_shift_ps"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
