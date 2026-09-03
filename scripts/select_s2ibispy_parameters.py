#!/usr/bin/env python3
"""Choose sim_time and tr/tf for a buffer by measuring it, not by inheriting them.

Point it at an s2ibispy recipe and it needs nothing else. The component name,
the driver model, the transistor netlist directory, the supply and the fixture
resistance are all read out of that recipe, so adding a buffer to the study
means writing its recipe -- which you have to do anyway -- and not registering
it here.

Two recipe parameters control what ends up in the generated IBIS file, and both
have been carried forward unexamined across every buffer in this study:

    sim_time   the characterization capture window
    tr = tf    the characterization input edge

They are coupled, because the V-T table is 1000 uniformly spaced points across
sim_time (1000 is the IBIS >= 4.0 ceiling), so:

    V-T sampling = sim_time / 1000

sim_time must be long enough to capture the buffer settling, and short enough
that 1000 points resolve the edge. Tuning tr alone leaves the resolution
wherever the inherited window happened to put it -- on inv_chain that was 6 ns
for a buffer that settles in 0.5 ns, spending 92% of the V-T points on flat
waveform.

Pass 1 converts once at a safe edge purely to observe the buffer: the generated
V-T tables report when it settles and how wide its output edge is. Pass 2 sets
sim_time from that measurement and sweeps tr downward, keeping the fastest edge
that passes every gate:

    exit code 0        the conversion did not lose a SPICE job, and ibischk
                       found no critical errors (the CLI returns 20 if it did)
    coefficients       max abs Ku and Kd within range, so the pybis extraction
                       is not corrupted
    edge samples       the V-T grid actually resolves the transition
    HSPICE runs        native IBIS simulates the model and produces a live pad
    ngspice runs       the pybis subcircuit converges rather than stalling

The last two matter because a model can pass every static check and still be
unusable. io_buf's 20 ps candidate had a clean table and then stalled ngspice
for 240 s on a study stimulus, which is what forced it to 50 ps.

    py -3.14 scripts/select_s2ibispy_parameters.py \\
        --config results/inv_chain_s2ibispy_slow_fast_2026-07-27/configs/inv_chain_fast_5ps.yaml
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python",
          ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "s2ibispy" / "python"):
    sys.path.insert(0, str(q))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from spice_tool_paths import default_hspice  # noqa: E402

S2I_SRC = Path(r"C:\Users\sh3qm\code\s2ibispy\src")
S2I_DEPS = ROOT / ".codex_deps" / "s2ibispy" / "python"
IBISCHK = Path(r"C:\Users\sh3qm\code\s2ibispy\resources\ibischk\ibischk7.exe")
NGSPICE = ROOT / ".codex_deps" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

CONVERT_TIMEOUT_S = 1200
HSPICE_TIMEOUT_S = 600
NGSPICE_TIMEOUT_S = 240     # io_buf's 20 ps candidate stalled for exactly this long
COEFF_LIMIT = 1.25
MIN_EDGE_SAMPLES = 5.0
SETTLE_TOL = 0.005
# sim_time = margin * settling. Only enough headroom to be sure the tail is
# captured; every nanosecond beyond that is spent on flat waveform at the
# cost of V-T resolution. A window that truncates the waveform moves the
# extraction endpoints, which the coefficient gate catches, so this can be
# tight rather than defensive. At 2.0 io_buf would have been handed a
# 10.4 ns window -- coarser sampling than the 6 ns it already had.
SETTLE_MARGIN = 1.25
PROBE_TR_S = 2.0e-10
SWEEP_TR_S = [2.0e-10, 1.0e-10, 5.0e-11, 2.0e-11, 1.0e-11, 5.0e-12, 1.0e-12]

# Model types that drive a pad. Anything else in the recipe is an input, a
# supply or a terminator and is not what we are characterizing.
DRIVER_TYPES = {"output", "i/o", "3-state", "open_drain", "open_sink",
                "open_source", "i/o_open_drain", "i/o_open_sink",
                "i/o_open_source", "output_ecl", "i/o_ecl"}

SUBCKT_RE = "^" + chr(92) + ".SUBCKT" + chr(92) + "s+(" + chr(92) + "S+)([^" + chr(92) + "n]*)"

_SUFFIX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3}


@dataclass
class Recipe:
    """Everything the selector needs, all of it read from the config."""
    path: Path
    name: str
    component: str
    model: str
    model_type: str
    inputs_dir: Path
    supply_v: float
    r_fixture: float
    sim_time_s: float

    @classmethod
    def load(cls, path: Path, inputs_dir: Path | None = None) -> "Recipe":
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        models = doc.get("models") or []
        drivers = [m for m in models
                   if str(m.get("type", "")).lower() in DRIVER_TYPES
                   and not m.get("nomodel")]
        if not drivers:
            raise SystemExit(
                f"{path.name}: no driving model found. Types present: "
                f"{sorted({str(m.get('type')) for m in models})}")
        driver = drivers[0]

        components = doc.get("components") or []
        if not components:
            raise SystemExit(f"{path.name}: no [Component] declared")
        component = str(components[0].get("component"))

        # The transistor netlist directory: HSPICE must run from here, because
        # the generated decks reference the device library by bare filename.
        resolved = inputs_dir
        if resolved is None:
            model_file = driver.get("modelFile")
            if not model_file:
                raise SystemExit(f"{path.name}: driver model has no modelFile; "
                                 "pass --inputs explicitly")
            resolved = Path(model_file).parent

        globals_ = doc.get("global_defaults") or {}
        supply = float((globals_.get("voltage_range") or {}).get("typ", 0.0))
        rising = driver.get("rising_waveforms") or [{}]
        r_fixture = float(rising[0].get("R_fixture", 50.0))
        return cls(path=path, name=path.stem, component=component,
                   model=str(driver.get("name")),
                   model_type=str(driver.get("type", "")),
                   inputs_dir=resolved, supply_v=supply, r_fixture=r_fixture,
                   sim_time_s=float(globals_.get("sim_time", 0.0)))


def _num(token: str) -> float:
    token = token.strip()
    if token and token[-1] in _SUFFIX:
        return float(token[:-1]) * _SUFFIX[token[-1]]
    return float(token)


def read_vt_tables(ibis_path: Path) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Every [Rising Waveform] / [Falling Waveform] block, as (label, t, v)."""
    tables: list[tuple[str, list[float], list[float]]] = []
    current = None
    for raw in ibis_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        low = line.lower()
        if low.startswith(("[rising waveform]", "[falling waveform]")):
            current = (low.strip("[]"), [], [])
            tables.append(current)
            continue
        if current is not None and line.startswith("["):
            current = None
            continue
        if current is None or not line or line.startswith("|"):
            continue
        if low.startswith(("r_fixture", "v_fixture", "c_fixture", "l_fixture")):
            continue
        parts = line.split()
        try:
            current[1].append(_num(parts[0]))
            current[2].append(float(parts[1]))
        except (ValueError, IndexError):
            continue
    return [(lab, np.asarray(t), np.asarray(v)) for lab, t, v in tables if len(t) > 2]


def settling_time(t: np.ndarray, v: np.ndarray, tol: float = SETTLE_TOL) -> float:
    """Last instant still more than `tol` of the excursion from where it ends."""
    excursion = float(v.max() - v.min())
    if excursion <= 0:
        return 0.0
    far = np.where(np.abs(v - v[-1]) > tol * excursion)[0]
    return float(t[far[-1]]) if len(far) else 0.0


def edge_width(t: np.ndarray, v: np.ndarray) -> float:
    """20% to 80% transition time, in whichever direction it runs."""
    start, end = float(v[0]), float(v[-1])
    if abs(end - start) < 1e-9:
        return float("nan")
    frac = (v - start) / (end - start)
    try:
        i20 = int(np.where(frac >= 0.2)[0][0])
        i80 = int(np.where(frac >= 0.8)[0][0])
    except IndexError:
        return float("nan")
    return abs(float(t[i80] - t[i20]))


def observe(ibis_path: Path) -> dict[str, float]:
    tables = read_vt_tables(ibis_path)
    if not tables:
        raise RuntimeError(f"no V-T tables in {ibis_path}")
    settle = max(settling_time(t, v) for _, t, v in tables)
    widths = [w for w in (edge_width(t, v) for _, t, v in tables) if np.isfinite(w)]
    span = float(max(t[-1] for _, t, _ in tables))
    points = max(len(t) for _, t, _ in tables)
    return {"settle_s": settle,
            "edge_width_s": min(widths) if widths else float("nan"),
            "window_s": span, "points": points,
            "sampling_s": span / points if points else float("nan"),
            "window_used_pct": 100.0 * settle / span if span else float("nan")}


def write_config(base: Path, dest: Path, *, tr_s: float | None = None,
                 sim_time_s: float | None = None, file_name: str | None = None,
                 note: str | None = None) -> None:
    """The base recipe with only the named scalars overridden.

    Rewritten line by line rather than through a YAML round trip, so a diff
    against the base config shows exactly what the selector changed.
    """
    in_tr_tf = False
    lines: list[str] = []
    for raw in base.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if file_name and stripped.startswith("file_name:"):
            lines.append(f"file_name: {file_name}")
            continue
        if note and stripped.startswith("notes:"):
            lines.append(f"notes: {note}")
            continue
        if sim_time_s is not None and stripped.startswith("sim_time:"):
            lines.append(raw.split("sim_time:")[0] + f"sim_time: {sim_time_s:.6e}")
            continue
        if stripped in ("tr:", "tf:"):
            in_tr_tf = True
            lines.append(raw)
            continue
        if in_tr_tf and stripped.startswith("typ:"):
            in_tr_tf = False
            lines.append(raw.split("typ:")[0] + f"typ: {tr_s:.6e}"
                         if tr_s is not None else raw)
            continue
        if in_tr_tf and not stripped.startswith(("typ:", "min:", "max:")):
            in_tr_tf = False
        lines.append(raw)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def convert(recipe: Recipe, config: Path, out_dir: Path) -> tuple[int, float]:
    """Run s2ibispy from the inputs directory. Returns (exit code, seconds).

    PYTHONPATH needs both the tool source and the vendored dependencies, and the
    working directory must be the inputs directory because the generated HSPICE
    decks reference the transistor library by bare filename. Both failure modes
    are confusing, so they are handled here rather than left to the caller.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(S2I_SRC), str(S2I_DEPS)])
    env["PATH"] = str(default_hspice().parent) + os.pathsep + env.get("PATH", "")
    started = time.time()
    with (out_dir / "convert.log").open("w", encoding="utf-8") as log:
        try:
            done = subprocess.run(
                [sys.executable, "-m", "s2ibispy", str(config), "--outdir", str(out_dir),
                 "--spice-type", "hspice", "--iterate", "0", "--cleanup", "0",
                 "--ibischk", str(IBISCHK)],
                cwd=str(recipe.inputs_dir), env=env, stdout=log,
                stderr=subprocess.STDOUT, timeout=CONVERT_TIMEOUT_S)
            code = done.returncode
        except subprocess.TimeoutExpired:
            log.write(f"\ns2ibispy exceeded {CONVERT_TIMEOUT_S} s\n")
            code = 124
    return code, time.time() - started


def coefficient_range(recipe: Recipe, ibis_path: Path) -> dict[str, float]:
    """Can pybis extract sane coefficients? Independent of whether it simulates."""
    from pybis2spice import pybis2spice as pb
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis_path)),
                        model_name=recipe.model, component_name=recipe.component)
    rising = pb.solve_k_params_output(data, corner=1, waveform_type="Rising")
    falling = pb.solve_k_params_output(data, corner=1, waveform_type="Falling")
    return {"max_abs_ku": float(np.nanmax(np.abs(
                np.concatenate([rising[:, 1], falling[:, 1]])))),
            "max_abs_kd": float(np.nanmax(np.abs(
                np.concatenate([rising[:, 2], falling[:, 2]]))))}


def hspice_converges(recipe: Recipe, ibis_path: Path, out_dir: Path) -> dict[str, object]:
    """Does HSPICE's native IBIS reader simulate this model and drive the pad?

    Deck built from the recipe, so it works for any buffer: supply and fixture
    resistance come from the config rather than being hard-coded.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    vcc = recipe.supply_v
    import shutil
    shutil.copy2(ibis_path, out_dir / ibis_path.name)

    # An I/O model takes two more nodes than an Output model -- an enable and a
    # digital-out -- and no `buffer=` selector. Wiring an I/O model the Output
    # way produces no .tr0 at all, with ibischk still reporting zero errors,
    # which reads as a broken model rather than a broken deck.
    if recipe.model_type.lower().startswith("i/o"):
        instance = f"""Ven en_sig 0 DC {vcc}
BIBIS pu_ref pd_ref pad_ibis in_dig en_sig dig_q pc_ref gc_ref
+ file='{ibis_path.name}' model='{recipe.model}' typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2
Rdig dig_q 0 1k"""
    else:
        instance = f"""BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='{ibis_path.name}' model='{recipe.model}' buffer=2 typ=typ power=off
+ interpol=1 ramp_rwf=2 ramp_fwf=2"""

    deck = f"""* convergence gate, HSPICE native IBIS
.title {ibis_path.stem}
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5n 0  5.001n {vcc}  15n {vcc}  15.001n 0  22n 0)
VPU pu_ref 0 DC {vcc}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {vcc}
VGC gc_ref 0 DC 0
{instance}
Rload pad_ibis 0 {recipe.r_fixture}
Cload pad_ibis 0 2p
.probe tran V(in_dig) V(pad_ibis)
.tran 0.001n 22n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    started = time.time()
    with (out_dir / "hspice.log").open("w", encoding="utf-8") as log:
        try:
            subprocess.run([str(default_hspice()), "-i", "run.sp", "-o", "run"],
                           cwd=str(out_dir), stdout=log, stderr=subprocess.STDOUT,
                           timeout=HSPICE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return {"hspice_ok": False, "hspice_s": time.time() - started,
                    "hspice_note": f"timed out after {HSPICE_TIMEOUT_S} s"}
    wall = time.time() - started
    tr0 = out_dir / "run.tr0"
    if not tr0.exists():
        return {"hspice_ok": False, "hspice_s": wall, "hspice_note": "no .tr0 written"}
    from eye_diagram import parse_hspice_tr0
    raw = parse_hspice_tr0(tr0)
    keys = {k.lower(): k for k in raw}
    pad = np.asarray(raw[next(keys[k] for k in keys if "pad" in k)], dtype=float)
    if not np.all(np.isfinite(pad)):
        return {"hspice_ok": False, "hspice_s": wall, "hspice_note": "non-finite pad"}
    swing = float(np.nanmax(pad) - np.nanmin(pad))
    if swing < 0.1 * max(vcc, 1e-9):
        return {"hspice_ok": False, "hspice_s": wall,
                "hspice_note": f"pad barely moves ({swing * 1e3:.1f} mV)"}
    return {"hspice_ok": True, "hspice_s": wall, "hspice_swing_v": round(swing, 4),
            "hspice_note": ""}


def ngspice_converges(recipe: Recipe, ibis_path: Path, out_dir: Path) -> dict[str, object]:
    """Does the pybis subcircuit converge, or does it stall the way io_buf did?"""
    out_dir.mkdir(parents=True, exist_ok=True)
    from pybis2spice import pybis2spice as pb, subcircuit
    try:
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis_path)),
                            model_name=recipe.model, component_name=recipe.component)
        sub_path = out_dir / "driver.sub"
        subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical",
                                        str(sub_path))
    except Exception as error:
        return {"ngspice_ok": False, "ngspice_s": 0.0,
                "ngspice_note": f"subcircuit generation failed: {type(error).__name__}"}
    if not sub_path.exists():
        return {"ngspice_ok": False, "ngspice_s": 0.0,
                "ngspice_note": "no subcircuit written"}

    text = sub_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(SUBCKT_RE, text, re.M | re.I)
    if not match:
        return {"ngspice_ok": False, "ngspice_s": 0.0,
                "ngspice_note": "no .SUBCKT line in the generated model"}
    name = match.group(1)
    tail = match.group(2).split("params:")[0]      # drop the parameter defaults
    pins = [p for p in tail.split() if "=" not in p]

    # Bind by pin name rather than position, and tie the ground pin to node 0.
    # Leaving VSS as a named node floats it and ngspice refuses the circuit.
    node_for = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC",
                "VSS": "0", "GND": "0"}
    nodes = [node_for.get(pin.upper(), pin) for pin in pins]
    unknown = [p for p in pins if p.upper() not in node_for]
    if unknown:
        return {"ngspice_ok": False, "ngspice_s": 0.0,
                "ngspice_note": f"unrecognised subckt pins {unknown}"}

    vcc = recipe.supply_v
    deck = f"""* convergence gate, ngspice pybis subcircuit
.include driver.sub
Vdd VCC 0 DC {vcc}
Vin IN 0 PWL(0n 0  5n 0  5.001n {vcc}  15n {vcc}  15.001n 0  22n 0)
Ven EN 0 DC {vcc}
X1 {' '.join(nodes)} {name}
Rload OUT 0 {recipe.r_fixture}
Cload OUT 0 2p
.tran 0.002n 22n
.save V(OUT) V(IN)
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    started = time.time()
    with (out_dir / "ngspice.log").open("w", encoding="utf-8") as log:
        try:
            done = subprocess.run([str(NGSPICE), "-b", "-r", "run.raw", "run.sp"],
                                  cwd=str(out_dir), stdout=log,
                                  stderr=subprocess.STDOUT, timeout=NGSPICE_TIMEOUT_S)
            code = done.returncode
        except subprocess.TimeoutExpired:
            return {"ngspice_ok": False, "ngspice_s": time.time() - started,
                    "ngspice_note": f"stalled, killed after {NGSPICE_TIMEOUT_S} s"}
    wall = time.time() - started
    raw_path = out_dir / "run.raw"
    if code != 0 or not raw_path.exists():
        return {"ngspice_ok": False, "ngspice_s": wall,
                "ngspice_note": f"ngspice exit {code}"}
    return {"ngspice_ok": True, "ngspice_s": wall, "ngspice_note": ""}


def grade(recipe: Recipe, ibis_path: Path, code: int, case_dir: Path,
          run_sim_gates: bool) -> dict[str, object]:
    """Every gate, and the reason a candidate was rejected."""
    result: dict[str, object] = {"exit_code": code}
    if code != 0 or not ibis_path.exists():
        result["reject"] = f"conversion exit {code}"
        return result

    fresh = observe(ibis_path)
    samples = (fresh["edge_width_s"] / fresh["sampling_s"]
               if fresh["sampling_s"] > 0 else float("nan"))
    result.update({k: fresh[k] for k in ("edge_width_s", "sampling_s", "window_s")})
    result["edge_samples"] = samples

    reasons: list[str] = []
    try:
        result.update(coefficient_range(recipe, ibis_path))
    except Exception as error:
        result["reject"] = f"extraction failed: {type(error).__name__}"
        return result

    if np.isfinite(samples) and samples < MIN_EDGE_SAMPLES:
        reasons.append(f"edge spans {samples:.1f} V-T samples (< {MIN_EDGE_SAMPLES})")
    for key, label in (("max_abs_ku", "max|Ku|"), ("max_abs_kd", "max|Kd|")):
        if result.get(key, 0.0) > COEFF_LIMIT:
            reasons.append(f"{label} = {result[key]:.3f} (> {COEFF_LIMIT})")

    if run_sim_gates:
        hs = hspice_converges(recipe, ibis_path, case_dir / "hspice_gate")
        result.update(hs)
        if not hs["hspice_ok"]:
            reasons.append(f"HSPICE: {hs['hspice_note']}")
        ng = ngspice_converges(recipe, ibis_path, case_dir / "ngspice_gate")
        result.update(ng)
        if not ng["ngspice_ok"]:
            reasons.append(f"ngspice: {ng['ngspice_note']}")

    result["reject"] = "; ".join(reasons)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True,
                        help="s2ibispy recipe (.yaml) for the buffer")
    parser.add_argument("--inputs", type=Path, default=None,
                        help="override the transistor netlist directory")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--skip-probe", action="store_true")
    parser.add_argument("--no-sim-gates", action="store_true",
                        help="skip the HSPICE and ngspice convergence gates")
    parser.add_argument("--settle-margin", type=float, default=SETTLE_MARGIN,
                        help="sim_time as a multiple of the measured settling")
    args = parser.parse_args()

    recipe = Recipe.load(args.config, args.inputs)
    out = args.out or (ROOT / "results" /
                       f"s2ibispy_parameter_selection_{recipe.name}_2026-09-02")
    out.mkdir(parents=True, exist_ok=True)

    print(f"recipe   {recipe.path.name}")
    print(f"  component {recipe.component}   model {recipe.model} "
          f"({recipe.model_type})")
    print(f"  inputs    {recipe.inputs_dir}")
    print(f"  supply    {recipe.supply_v} V   R_fixture {recipe.r_fixture} ohm")
    print(f"  inherited sim_time {recipe.sim_time_s * 1e9:.3f} ns\n")

    probe_dir = out / "probe"
    probe_ibis = probe_dir / f"{recipe.name}_probe.ibs"
    if not (args.skip_probe and probe_ibis.exists()):
        probe_dir.mkdir(parents=True, exist_ok=True)
        config = probe_dir / f"{recipe.name}_probe.yaml"
        write_config(recipe.path, config, tr_s=PROBE_TR_S, file_name=probe_ibis.name,
                     note="Observation pass for parameter selection.")
        print(f"probe: converting at tr = {PROBE_TR_S * 1e12:.0f} ps ...", flush=True)
        code, wall = convert(recipe, config, probe_dir)
        if code != 0 or not probe_ibis.exists():
            print(f"probe failed (exit {code}); see {probe_dir / 'convert.log'}")
            return 1
        print(f"   done in {wall:.0f} s")

    seen = observe(probe_ibis)
    chosen_sim = max(args.settle_margin * seen["settle_s"], 10 * seen["edge_width_s"])
    print("\nobserved from the probe model")
    print(f"   settles by            {seen['settle_s'] * 1e9:8.3f} ns")
    print(f"   output edge 20-80%    {seen['edge_width_s'] * 1e12:8.1f} ps")
    print(f"   inherited window      {seen['window_s'] * 1e9:8.3f} ns   "
          f"({seen['window_used_pct']:.0f}% used, "
          f"{seen['sampling_s'] * 1e12:.2f} ps sampling)")
    print(f"   chosen sim_time       {chosen_sim * 1e9:8.3f} ns   "
          f"({chosen_sim / seen['points'] * 1e12:.2f} ps sampling)")

    print(f"\nsweeping tr under sim_time = {chosen_sim * 1e9:.3f} ns")
    header = f"{'tr':>8}{'rc':>4}{'edge pts':>10}{'max|Ku|':>9}{'max|Kd|':>9}"
    if not args.no_sim_gates:
        header += f"{'hspice':>8}{'ngspice':>9}"
    print(header + "   verdict")

    rows: list[dict[str, object]] = []
    for tr_s in SWEEP_TR_S:
        tag = f"tr{tr_s * 1e12:g}ps"
        case_dir = out / tag
        case_dir.mkdir(parents=True, exist_ok=True)
        ibis = case_dir / f"{recipe.name}_{tag}.ibs"
        config = case_dir / f"{recipe.name}_{tag}.yaml"
        write_config(recipe.path, config, tr_s=tr_s, sim_time_s=chosen_sim,
                     file_name=ibis.name,
                     note=f"Parameter selection; sim_time={chosen_sim:.3e}, "
                          f"tr=tf={tr_s:.3e}.")
        code, wall = convert(recipe, config, case_dir)
        row = {"recipe": recipe.path.name, "component": recipe.component,
               "tr_s": tr_s, "sim_time_s": chosen_sim, "convert_s": round(wall, 1)}
        row.update(grade(recipe, ibis, code, case_dir, not args.no_sim_gates))
        rows.append(row)
        line = (f"{tag:>8}{code:4d}{row.get('edge_samples', float('nan')):10.1f}"
                f"{row.get('max_abs_ku', float('nan')):9.3f}"
                f"{row.get('max_abs_kd', float('nan')):9.3f}")
        if not args.no_sim_gates:
            line += (f"{'ok' if row.get('hspice_ok') else 'FAIL':>8}"
                     f"{'ok' if row.get('ngspice_ok') else 'FAIL':>9}")
        verdict = "accept" if not row.get("reject") else f"reject: {row['reject']}"
        print(f"{line}   {verdict}", flush=True)

    survivors = [r for r in rows if not r.get("reject")]
    best = min(survivors, key=lambda r: r["tr_s"]) if survivors else None

    summary = out / "selection.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({k for r in rows for k in r})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    (out / "decision.json").write_text(json.dumps({
        "recipe": str(recipe.path), "component": recipe.component,
        "model": recipe.model, "model_type": recipe.model_type,
        "observed": dict(seen), "chosen_sim_time_s": chosen_sim,
        "chosen_tr_s": best["tr_s"] if best else None,
        "gates": {"max_abs_coefficient": COEFF_LIMIT,
                  "min_edge_samples": MIN_EDGE_SAMPLES,
                  "hspice_convergence": not args.no_sim_gates,
                  "ngspice_convergence": not args.no_sim_gates,
                  "ngspice_timeout_s": NGSPICE_TIMEOUT_S},
        "rejected": [{"tr_s": r["tr_s"], "reason": r["reject"]}
                     for r in rows if r.get("reject")],
    }, indent=2), encoding="utf-8")

    print()
    if best:
        print(f"selected: sim_time = {chosen_sim * 1e9:.3f} ns, "
              f"tr = tf = {best['tr_s'] * 1e12:g} ps")
        print(f"          {best['edge_samples']:.1f} V-T samples across the edge, "
              f"max|Ku| {best['max_abs_ku']:.3f}")
        print(f"          expect about {0.7 * best['tr_s'] * 1e12:.1f} ps of "
              f"built-in lateness at this edge")
    else:
        print("no candidate passed every gate")
    print(f"\nwrote {summary.resolve()}")
    return 0 if best else 1


if __name__ == "__main__":
    raise SystemExit(main())
