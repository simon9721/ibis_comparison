#!/usr/bin/env python3
"""Transistor against native IBIS against pybis, on four different silicons.

Item 1 of `0902_plan.md`. The study's conclusions rest on three buffers. These
are four variants of one of them, each changing a single property, and the
question is whether the models track silicon as the silicon changes.

Three runs per variant, identical stimulus and load in all three:

    transistor    HSPICE on the variant netlist -- ground truth
    native IBIS   HSPICE reading the generated .ibs -- the bar
    pybis         ngspice on the subcircuit pybis builds from the same .ibs

The IBIS model used is the one `select_s2ibispy_parameters.py` chose for that
variant, so each buffer is characterized on parameters measured from itself
rather than inherited.

Full swing only. A clean transition is the precondition for anything else
meaning much, and interrupted pulses are deliberately out of scope here.

Bench: 1 ps input edges at 5 ns and 15 ns, 50 ohm in parallel with 2 pF, 22 ns.
The same bench the July sanity checks used, so numbers are comparable to them.

    py -3.14 scripts/compare_variants_full_swing.py
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

VARIANTS_DIR = ROOT / "results" / "inv_chain_variants_2026-09-02"
OUT = ROOT / "results" / "inv_chain_variants_full_swing_2026-09-03"
NGSPICE = ROOT / ".codex_deps" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

VARIANTS = ["base8", "stage4", "skewp", "weak"]
SUPPLY_V = 1.8
R_LOAD, C_LOAD_PF = 50.0, 2.0
EDGE_PS = 1.0
RISE_NS, FALL_NS, STOP_NS = 5.0, 15.0, 22.0
HSPICE_TIMEOUT_S, NGSPICE_TIMEOUT_S = 600, 600

TRANSISTOR = "#111111"
NATIVE = "#2B6CA3"
PYBIS = "#C02626"
DPI = 175

# From invchain_top.sp. The corner subckt files reference these by name, so the
# deck has to define them even though only the typical corner is simulated.
SUPPLY_PARAMS = """.PARAM  vccr_typ  = 1.300V
.PARAM  vccr_min  = 1.250V
.PARAM  vccr_max  = 1.350V
.PARAM  vccq_typ  = 1.800V
.PARAM  vccq_min  = 1.700V
.PARAM  vccq_max  = 1.900V
.PARAM  gnd       = 0.000V
.PARAM  vssq      = 0.000V
.PARAM  vss       = 0.000V"""


def pwl(supply: float) -> str:
    edge = EDGE_PS / 1000.0
    return (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + edge}n {supply}  "
            f"{FALL_NS}n {supply}  {FALL_NS + edge}n 0  {STOP_NS}n 0)")


def run(command: list[str], cwd: Path, log_name: str, timeout: int) -> int:
    with (cwd / log_name).open("w", encoding="utf-8") as log:
        try:
            done = subprocess.run(command, cwd=str(cwd), stdout=log,
                                  stderr=subprocess.STDOUT, timeout=timeout)
            return done.returncode
        except subprocess.TimeoutExpired:
            log.write(f"\ntimed out after {timeout} s\n")
            return 124


def transistor_pad(variant: str, out_dir: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """HSPICE on the variant netlist. Ground truth for that silicon."""
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = VARIANTS_DIR / variant / "inputs"
    for name in os.listdir(inputs):
        shutil.copy2(inputs / name, out_dir / name)
    deck = f"""* {variant} transistor reference
.title {variant} transistor
.OPTIONS LIST NODE POST
.OPTIONS METHOD=GEAR
.OPTIONS GSHUNT=1E-12
.option post=2 probe accurate ingold=2
.temp 27

{SUPPLY_PARAMS}

.include 'invchain_{variant}_subckt_typ.sp'

Vdd vccq 0 DC {SUPPLY_V}
Vin in_dig 0 {pwl(SUPPLY_V)}
XDUT in_dig pad_sp vccq 0 invchain
Rload pad_sp 0 {R_LOAD}
Cload pad_sp 0 {C_LOAD_PF}p

.probe tran V(in_dig) V(pad_sp)
.tran 0.001n {STOP_NS}n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    run([str(default_hspice()), "-i", "run.sp", "-o", "run"], out_dir,
        "hspice.log", HSPICE_TIMEOUT_S)
    tr0 = out_dir / "run.tr0"
    if not tr0.exists():
        return None
    raw = parse_hspice_tr0(tr0)
    keys = {k.lower(): k for k in raw}
    t = np.asarray(raw[keys["time"]], dtype=float) * 1e9
    pad = np.asarray(raw[next(keys[k] for k in keys if "pad" in k)], dtype=float)
    return t, pad


def native_ibis_pad(ibis: Path, model: str, out_dir: Path
                    ) -> tuple[np.ndarray, np.ndarray] | None:
    """HSPICE reading the generated IBIS file directly."""
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ibis, out_dir / ibis.name)
    deck = f"""* {ibis.stem} native IBIS
.title {ibis.stem} native IBIS
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 {pwl(SUPPLY_V)}
VPU pu_ref 0 DC {SUPPLY_V}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUPPLY_V}
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='{ibis.name}' model='{model}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2

Rload pad_ibis 0 {R_LOAD}
Cload pad_ibis 0 {C_LOAD_PF}p

.probe tran V(in_dig) V(pad_ibis)
.tran 0.001n {STOP_NS}n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    run([str(default_hspice()), "-i", "run.sp", "-o", "run"], out_dir,
        "hspice.log", HSPICE_TIMEOUT_S)
    tr0 = out_dir / "run.tr0"
    if not tr0.exists():
        return None
    raw = parse_hspice_tr0(tr0)
    keys = {k.lower(): k for k in raw}
    t = np.asarray(raw[keys["time"]], dtype=float) * 1e9
    pad = np.asarray(raw[next(keys[k] for k in keys if "pad" in k)], dtype=float)
    return t, pad


def pybis_pad(ibis: Path, model: str, component: str, out_dir: Path
              ) -> tuple[np.ndarray, np.ndarray] | None:
    """ngspice on the subcircuit pybis builds from the same IBIS file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    from pybis2spice import pybis2spice as pb, subcircuit
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)),
                        model_name=model, component_name=component)
    sub = out_dir / "driver.sub"
    subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical", str(sub))
    if not sub.exists():
        return None

    text = sub.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    if not match:
        return None
    name = match.group(1)
    pins = [p for p in match.group(2).split("params:")[0].split() if "=" not in p]
    # Bind by pin name and tie the ground pin to node 0; leaving VSS as a named
    # node floats it and ngspice refuses the circuit.
    node_for = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC",
                "VSS": "0", "GND": "0"}
    nodes = [node_for.get(p.upper(), p) for p in pins]

    deck = f"""* {ibis.stem} pybis subcircuit
.include driver.sub
Vdd VCC 0 DC {SUPPLY_V}
Vin IN 0 {pwl(SUPPLY_V)}
Ven EN 0 DC {SUPPLY_V}
X1 {' '.join(nodes)} {name}
Rload OUT 0 {R_LOAD}
Cload OUT 0 {C_LOAD_PF}p
.tran 0.001n {STOP_NS}n
.save V(OUT) V(IN)
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    code = run([str(NGSPICE), "-b", "-r", "run.raw", "run.sp"], out_dir,
               "ngspice.log", NGSPICE_TIMEOUT_S)
    raw_path = out_dir / "run.raw"
    if code != 0 or not raw_path.exists():
        return None
    raw = parse_ngspice_raw(raw_path)
    keys = {k.lower(): k for k in raw}
    t = np.asarray(raw[keys["time"]], dtype=float) * 1e9
    pad = np.asarray(raw[next(keys[k] for k in keys if "out" in k)], dtype=float)
    return t, pad


def crossing(t: np.ndarray, y: np.ndarray, level: float, rising: bool,
             after: float) -> float:
    for i in range(1, len(y)):
        if t[i] < after:
            continue
        if (rising and y[i - 1] < level <= y[i]) or \
           (not rising and y[i - 1] > level >= y[i]):
            return float(t[i - 1] + (level - y[i - 1]) * (t[i] - t[i - 1])
                         / (y[i] - y[i - 1]))
    return float("nan")


def score(model, reference) -> dict[str, float]:
    """Time-weighted RMSE and edge timing against the transistor."""
    t_m, pad_m = model
    t_r, pad_r = reference
    lo, hi = max(t_m[0], t_r[0]), min(t_m[-1], t_r[-1])
    grid = np.linspace(lo, hi, 40000)
    a = np.interp(grid, t_m, pad_m)
    b = np.interp(grid, t_r, pad_r)
    half = 0.5 * (np.nanmax(b) + np.nanmin(b))
    return {
        "rmse_mv": float(np.sqrt(np.trapezoid((a - b) ** 2, grid)
                                 / (grid[-1] - grid[0]))) * 1e3,
        "worst_mv": float(np.nanmax(np.abs(a - b))) * 1e3,
        "rise_shift_ps": (crossing(grid, a, half, True, RISE_NS - 0.5)
                          - crossing(grid, b, half, True, RISE_NS - 0.5)) * 1e3,
        "fall_shift_ps": (crossing(grid, a, half, False, FALL_NS - 0.5)
                          - crossing(grid, b, half, False, FALL_NS - 0.5)) * 1e3,
    }


def figure(path: Path, variant: str, traces: dict, window: tuple[float, float]) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12.6, 8.2))
    for axis, span, title in ((axes[0], (RISE_NS - 0.2, RISE_NS + 1.4), "rising edge"),
                              (axes[1], (FALL_NS - 0.2, FALL_NS + 1.4), "falling edge")):
        for label, colour, width, data in (
                ("HSPICE transistor", TRANSISTOR, 3.4, traces.get("transistor")),
                ("HSPICE native IBIS", NATIVE, 2.2, traces.get("native")),
                ("ngspice pybis", PYBIS, 2.0, traces.get("pybis"))):
            if data is None:
                continue
            axis.plot(data[0], data[1], color=colour, lw=width, label=label,
                      ls="-" if label.endswith("transistor") else (0, (5, 2.2)))
        axis.set_xlim(*span)
        axis.set_ylabel("Pad (V)", fontsize=12)
        axis.set_title(f"{variant}  |  {title}", fontsize=13.5, fontweight="bold",
                       pad=8)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=11)
        for spine in axis.spines.values():
            spine.set_color("#3A4753")
    axes[0].legend(fontsize=11, loc="lower right", framealpha=0.95)
    axes[1].set_xlabel("Time (ns)", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--variant", action="append", choices=VARIANTS)
    args = parser.parse_args()
    out = (args.out if args.out.is_absolute() else ROOT / args.out).resolve()
    (out / "plots").mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    print(f"{'variant':<9}{'build':<14}{'RMSE mV':>9}{'worst mV':>10}"
          f"{'rise ps':>9}{'fall ps':>9}")
    for variant in (args.variant or VARIANTS):
        ibis = (VARIANTS_DIR / variant / "selection" / "tr1ps" /
                f"invchain_{variant}_tr1ps.ibs")
        if not ibis.exists():
            print(f"{variant:<9}  no selected model at {ibis}")
            continue
        case = out / variant
        started = time.time()
        traces = {
            "transistor": transistor_pad(variant, case / "transistor"),
            "native": native_ibis_pad(ibis, "driver2", case / "native_ibis"),
            "pybis": pybis_pad(ibis, "driver2", "invchain", case / "pybis"),
        }
        if traces["transistor"] is None:
            print(f"{variant:<9}  transistor run failed")
            continue
        row: dict[str, object] = {"variant": variant,
                                  "seconds": round(time.time() - started, 1)}
        for label, key in (("native IBIS", "native"), ("pybis", "pybis")):
            if traces[key] is None:
                print(f"{variant:<9}{label:<14}   run failed")
                continue
            m = score(traces[key], traces["transistor"])
            print(f"{variant:<9}{label:<14}{m['rmse_mv']:9.2f}{m['worst_mv']:10.1f}"
                  f"{m['rise_shift_ps']:9.1f}{m['fall_shift_ps']:9.1f}")
            row.update({f"{key}_{k}": round(v, 4) for k, v in m.items()})
        rows.append(row)
        figure(out / "plots" / f"{variant}_full_swing.png", variant, traces,
               (RISE_NS - 0.2, FALL_NS + 1.4))

    if not rows:
        print("nothing ran")
        return 1
    summary = out / "full_swing_comparison.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({k for r in rows for k in r})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
