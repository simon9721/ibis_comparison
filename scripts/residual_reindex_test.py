#!/usr/bin/env python3
"""Change only the residual table's index, from the stopwatch to the gate state.

Our Ku is built from two pieces added together:

    KUGATE_BASE = pwl(V(GUP), ...)        indexed by the GATE STATE
    KURES_TABLE = pwl(V(HNX), ...)        indexed by HNX, time since the input edge
    Ku = KUGATE_BASE + KURES_TABLE

The first already carries a partial transition correctly -- GUP is continuous, so
a truncated pulse leaves it at 0.54 rather than 1.0 and the map reads the right
value. The second is a correction table read off a **stopwatch that resets to zero
at every input edge**, so it applies the correction for a transition that began
from fully settled even when it did not.

`v_indexed_prototype_2026-09-04` showed that entering the reverse trajectory where
the coefficient already is takes Kd from +191 ps to +1 ps against the transistor.
This tests whether the residual's index is where that belongs, by changing **only**
that and nothing else.

The re-index needs no latch and no per-edge reset. On a complete transition the
model's own gate state traces out GUP(HNX); inverting it gives an
equivalent-elapsed-time as a static function of the gate state:

    HNX_eff = pwl(V(GUP), <inverse of the recorded GUP(HNX)>)

On a complete transition that reproduces HNX exactly, so the unstressed cases
cannot regress by construction. On a truncated one it enters partway.

Step 1 runs the unmodified model at full swing to record GUP(HNX) and GDN(HNX).
Step 2 patches the four residual tables. Step 3 measures, stressed and unstressed.

    py -3.14 scripts/residual_reindex_test.py
"""
from __future__ import annotations

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
from pedestal_localization import best_lag, outward_window, read  # noqa: E402

R = ROOT / "results"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
STRESSED = (R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
            / "io_buf_short_high_w1792ps.csv")
OUT = R / "residual_reindex_2026-09-04"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
EDGE_NS, STOP_NS = 0.050, 22.0
PROBES = ("gup", "gdn", "hnx", "ku", "kd")

# (label, rise time, fall time). The stressed case is the deck the whole study
# uses; the full swing is the no-regression control.
CASES = {"stressed": (5.000, 6.790), "full_swing": (5.000, 15.000)}


def make_deck(sub: dk.PybisSubckt, rise: float, fall: float) -> str:
    pwl = (f"PWL(0n 0  {rise}n 0  {rise + EDGE_NS}n {SUPPLY}  "
           f"{fall}n {SUPPLY}  {fall + EDGE_NS}n 0  {STOP_NS}n 0)")
    saves = " ".join(f"V(X1.{p})" for p in PROBES)
    return (dk.ngspice_header()
            + ".include driver.sub\n"
            + dk.supply("VCC", SUPPLY, name="Vdd")
            + f"Vin IN 0 {pwl}\n"
            + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
            + sub.instance("X1")
            + dk.load("OUT", R_LOAD, C_LOAD_PF)
            + f".tran 0.002n {STOP_NS}n\n.save V(OUT) {saves}\n.end\n")


def generate(tag: str) -> Path:
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                    str(d / "driver.sub"))
    return d


def run(d: Path, case: str) -> dict[str, np.ndarray]:
    rise, fall = CASES[case]
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    run_dir = d / case
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "driver.sub").write_bytes((d / "driver.sub").read_bytes())
    (run_dir / "run.sp").write_text(make_deck(sub, rise, fall), encoding="utf-8")
    if not (run_dir / "run.raw").exists():
        if sl.ngspice(run_dir, timeout_s=1200) is None:
            raise RuntimeError(f"{d.name}/{case} failed -- see ngspice.log")
    raw = sl.parse_ngspice_raw(run_dir / "run.raw")
    out = {"time_ns": sl.time_ns(raw), "pad": sl.trace(raw, "out")}
    for p in PROBES:
        out[p] = sl.signal(raw, f"v(x1.{p})", f"x1.{p}")
    return out


def inverse_table(gate: np.ndarray, hnx: np.ndarray, window) -> tuple[np.ndarray, np.ndarray]:
    """gate value -> equivalent elapsed time, over one complete transition.

    `hnx` is the model's own stopwatch, so pairing it with the gate state during a
    complete transition and inverting gives exactly the identity on that
    transition -- which is what makes the unstressed case safe.
    """
    g, h = gate[window], hnx[window]
    order = np.argsort(g)
    g, h = g[order], h[order]
    uniq, idx = np.unique(np.round(g, 4), return_inverse=True)
    hh = np.bincount(idx, h) / np.bincount(idx)
    # Decimate onto a uniform gate grid. The raw pairing runs to thousands of
    # points, which would put a multi-thousand-term pwl on one netlist line for
    # no accuracy that matters.
    grid = np.linspace(uniq.min(), uniq.max(), 200)
    return grid, np.interp(grid, uniq, hh)


def as_pwl(node: str, xs: np.ndarray, ys: np.ndarray, cap: float) -> str:
    pairs = ", ".join(f"{x:.6g}, {y:.6g}" for x, y in zip(xs, ys))
    return f"min(max(pwl(V({node}), {pairs}), 0), {cap})"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # --- step 1: the unmodified model, and its own complete-transition gate path
    base = generate("baseline")
    full = run(base, "full_swing")
    t, hnx = full["time_ns"], full["hnx"]
    rise, fall = CASES["full_swing"]
    # Windows over each complete transition, from the edge until the stopwatch
    # resets at the next one.
    w_rise = (t > rise) & (t < fall - 0.05)
    w_fall = (t > fall) & (t < STOP_NS - 0.05)
    tables = {
        "KURES_R": ("GUP",) + inverse_table(full["gup"], hnx, w_rise),
        "KURES_F": ("GUP",) + inverse_table(full["gup"], hnx, w_fall),
        "KDRES_R": ("GDN",) + inverse_table(full["gdn"], hnx, w_rise),
        "KDRES_F": ("GDN",) + inverse_table(full["gdn"], hnx, w_fall),
    }
    for name, (node, xs, _) in tables.items():
        print(f"  {name}: indexed on {node}, {len(xs)} points, "
              f"{xs.min():.3f}..{xs.max():.3f}")

    # --- step 2: patch only the residual tables' index
    fixed = generate("reindexed")
    text = (fixed / "driver.sub").read_text(encoding="utf-8")
    patched = 0
    for name, (node, xs, ys) in tables.items():
        # Each residual line reads  pwl(min(max(V(HNX), 0), <cap>), <table>)
        # Match on the node name, not the element name: the pulldown residuals
        # are elements BKDRESR / BKDRESF driving nodes KDRES_R / KDRES_F, so the
        # element name is not the node name with a prefix.
        pattern = rf"^(B\S+ {name} 0 V = pwl\()min\(max\(V\(HNX\), 0\), ([0-9.e+]+)\)"
        m = re.search(pattern, text, flags=re.M)
        if m is None:
            print(f"  {name}: could not find its HNX index")
            continue
        cap = float(m.group(2))
        text = re.sub(pattern, lambda mm: mm.group(1) + as_pwl(node, xs, ys, cap),
                      text, count=1, flags=re.M)
        patched += 1
    if patched != 4:
        print(f"  patched {patched} of 4 residual tables -- stopping")
        return 1
    (fixed / "driver.sub").write_text(text, encoding="utf-8")
    print(f"  patched {patched} residual tables\n")

    # --- step 3: measure
    ref = read(STRESSED)
    t_ref = ref["time_ns"]
    lo, hi = outward_window(t_ref, ref["silicon_pad"], 5.0)
    grid = np.arange(lo, hi, 0.002)
    truth = {k: np.interp(grid, t_ref, ref[f"silicon_{k}"]) for k in ("ku", "kd")}
    truth["pad"] = np.interp(grid, t_ref, ref["silicon_pad"])
    nat_pad = np.interp(grid, t_ref, ref["hspice_pad"])

    print("  Lag against the transistor over the outward leg, ps "
          "(+ = later). Stressed case:\n")
    print(f"    {'build':<22}{'Ku':>10}{'Kd':>10}{'pad':>10}{'pad vs native':>16}")
    for tag, label in (("baseline", "shipped"), ("reindexed", "re-indexed")):
        d = run(OUT / tag, "stressed")
        vals = []
        for key in ("ku", "kd", "pad"):
            y = np.interp(grid, d["time_ns"], d[key])
            vals.append(best_lag(grid, truth[key], y, lo, hi)[0])
        pad = np.interp(grid, d["time_ns"], d["pad"])
        ped = best_lag(grid, nat_pad, pad, lo, hi)[0]
        print(f"    {label:<22}{vals[0]:>10.0f}{vals[1]:>10.0f}"
              f"{vals[2]:>10.0f}{ped:>16.0f}")
    print(f"    {'native, two tables':<22}{'+15':>10}{'+67':>10}"
          f"{'':>10}{'0':>16}   [reference]")

    # --- the no-regression check
    print("\n  Full swing, the unstressed control -- these must not move:")
    print(f"    {'build':<22}{'rise 50% (ns)':>16}{'fall 50% (ns)':>16}")
    for tag, label in (("baseline", "shipped"), ("reindexed", "re-indexed")):
        d = run(OUT / tag, "full_swing")
        tt, pad = d["time_ns"], d["pad"]
        half = 0.5 * (float(np.max(pad)) + float(np.median(pad[tt < 4.8])))
        a = sl.cross(tt, pad, half, rising=True, after=4.9)
        b = sl.cross(tt, pad, half, rising=False, after=15.0)
        print(f"    {label:<22}{a:>16.4f}{b:>16.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
