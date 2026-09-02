#!/usr/bin/env python3
"""Choose sim_time and tr/tf for a buffer by measuring it, not by inheriting them.

Two recipe parameters control what ends up in a generated IBIS file, and both
have been carried forward unexamined across every buffer in this study:

    sim_time   the characterization capture window
    tr = tf    the characterization input edge

They are coupled, because the V-T table is 1000 uniformly spaced points across
sim_time (1000 is the IBIS >= 4.0 ceiling), so:

    V-T sampling = sim_time / 1000

sim_time must be long enough to capture the buffer settling, and short enough
that 1000 points resolve the edge. Today all three buffers sit at 6-8 ns, which
nobody chose -- and inv_chain settles in 0.33 ns, so 94% of its V-T resolution
is spent on flat waveform. Shortening its window to 1 ns takes the edge from
3.3 samples to 20, with the same 1000 points.

This measures both instead. Pass 1 converts once with a generous window and a
safe edge, purely to observe the buffer: the generated V-T tables report when it
settles and how wide its output edge is. Pass 2 sets sim_time from that
measurement and sweeps tr downward, keeping the fastest edge that passes every
gate:

    exit code 0            the conversion did not lose a SPICE job
    ibischk clean          the file is valid IBIS
    max|Ku|, max|Kd|       the coefficient extraction is not corrupted
    edge samples >= 5      the V-T grid actually resolves the transition

The last gate is the one that catches io_buf's failure mode directly rather
than waiting to observe its symptoms: at 6 ps sampling a 5 ps edge lands inside
a single sample, C_comp*dV/dt reads ~660 mA against a 23 mA fixture current, and
the endpoints, onset delays and gate-state maps are all corrupted downstream.

    py -3.14 scripts/select_s2ibispy_parameters.py --buffer inv_chain
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python",
          ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(q))

import numpy as np  # noqa: E402

from spice_tool_paths import default_hspice  # noqa: E402

S2I_SRC = Path(r"C:\Users\sh3qm\code\s2ibispy\src")
S2I_DEPS = ROOT / ".codex_deps" / "s2ibispy" / "python"
IBISCHK = Path(r"C:\Users\sh3qm\code\s2ibispy\resources\ibischk\ibischk7.exe")

CONVERT_TIMEOUT_S = 1200
COEFF_LIMIT = 1.25          # max |Ku| or |Kd| before the extraction is corrupt
MIN_EDGE_SAMPLES = 5.0      # V-T points across the 20-80% output transition
SETTLE_TOL = 0.005          # fraction of the excursion counted as settled
SETTLE_MARGIN = 2.0         # sim_time = margin * settling time
PROBE_TR_S = 2.0e-10        # safe edge for the observation pass
SWEEP_TR_S = [2.0e-10, 1.0e-10, 5.0e-11, 2.0e-11, 1.0e-11, 5.0e-12, 1.0e-12]

_SUFFIX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3}


@dataclass
class Buffer:
    """Everything needed to convert and then grade one buffer."""
    name: str
    base_config: Path
    inputs_dir: Path
    ibis_model: str
    ibis_component: str


BUFFERS = {
    "inv_chain": Buffer(
        "inv_chain",
        ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27" / "configs"
        / "inv_chain_fast_5ps.yaml",
        ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27" / "inputs",
        "driver2", "invchain",
    ),
}


def _num(token: str) -> float:
    token = token.strip()
    if token and token[-1] in _SUFFIX:
        return float(token[:-1]) * _SUFFIX[token[-1]]
    return float(token)


def read_vt_tables(ibis_path: Path) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Every [Rising Waveform] / [Falling Waveform] block, as (label, t, v)."""
    tables: list[tuple[str, list[float], list[float]]] = []
    current: tuple[str, list[float], list[float]] | None = None
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
    """Last instant the waveform is still more than `tol` of its excursion away
    from where it ends. Zero if it never moves."""
    excursion = float(v.max() - v.min())
    if excursion <= 0:
        return 0.0
    far = np.where(np.abs(v - v[-1]) > tol * excursion)[0]
    return float(t[far[-1]]) if len(far) else 0.0


def edge_width(t: np.ndarray, v: np.ndarray) -> float:
    """20% to 80% transition time, measured on whichever direction it runs."""
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
    """What the generated tables say about the buffer itself."""
    tables = read_vt_tables(ibis_path)
    if not tables:
        raise RuntimeError(f"no V-T tables in {ibis_path}")
    settle = max(settling_time(t, v) for _, t, v in tables)
    widths = [w for w in (edge_width(t, v) for _, t, v in tables) if np.isfinite(w)]
    span = float(max(t[-1] for _, t, _ in tables))
    points = max(len(t) for _, t, _ in tables)
    return {
        "settle_s": settle,
        "edge_width_s": min(widths) if widths else float("nan"),
        "window_s": span,
        "points": points,
        "sampling_s": span / points if points else float("nan"),
        "window_used_pct": 100.0 * settle / span if span else float("nan"),
    }


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
            if tr_s is not None:
                lines.append(raw.split("typ:")[0] + f"typ: {tr_s:.6e}")
                continue
            lines.append(raw)
            continue
        if in_tr_tf and not stripped.startswith(("typ:", "min:", "max:")):
            in_tr_tf = False
        lines.append(raw)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def convert(buffer: Buffer, config: Path, out_dir: Path) -> tuple[int, float]:
    """Run s2ibispy from the inputs directory. Returns (exit code, seconds).

    PYTHONPATH needs both the tool source and the vendored dependencies, and the
    working directory must be `inputs/` because the generated HSPICE decks
    reference the transistor library by bare filename. Both failure modes are
    confusing, so they are handled here rather than left to the caller.
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
                cwd=str(buffer.inputs_dir), env=env, stdout=log,
                stderr=subprocess.STDOUT, timeout=CONVERT_TIMEOUT_S)
            code = done.returncode
        except subprocess.TimeoutExpired:
            log.write(f"\ns2ibispy exceeded {CONVERT_TIMEOUT_S} s\n")
            code = 124
    return code, time.time() - started


def extraction_quality(buffer: Buffer, ibis_path: Path) -> dict[str, float]:
    """Can pybis consume the file? Independent of whether HSPICE can."""
    from pybis2spice import pybis2spice as pb
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis_path)),
                        model_name=buffer.ibis_model,
                        component_name=buffer.ibis_component)
    rising = pb.solve_k_params_output(data, corner=1, waveform_type="Rising")
    falling = pb.solve_k_params_output(data, corner=1, waveform_type="Falling")
    ku = np.concatenate([rising[:, 1], falling[:, 1]])
    kd = np.concatenate([rising[:, 2], falling[:, 2]])
    return {"max_abs_ku": float(np.nanmax(np.abs(ku))),
            "max_abs_kd": float(np.nanmax(np.abs(kd)))}


def grade(buffer: Buffer, ibis_path: Path, code: int,
          observed: dict[str, float]) -> dict[str, object]:
    """Every gate, and why a candidate was rejected."""
    result: dict[str, object] = {"exit_code": code}
    reasons: list[str] = []
    if code != 0 or not ibis_path.exists():
        reasons.append(f"conversion exit {code}")
        result["reject"] = "; ".join(reasons)
        return result

    fresh = observe(ibis_path)
    samples = (fresh["edge_width_s"] / fresh["sampling_s"]
               if fresh["sampling_s"] > 0 else float("nan"))
    result.update({k: fresh[k] for k in
                   ("edge_width_s", "sampling_s", "window_s")})
    result["edge_samples"] = samples

    try:
        result.update(extraction_quality(buffer, ibis_path))
    except Exception as error:
        reasons.append(f"extraction failed: {type(error).__name__}")
        result["reject"] = "; ".join(reasons)
        return result

    if np.isfinite(samples) and samples < MIN_EDGE_SAMPLES:
        reasons.append(f"edge spans {samples:.1f} V-T samples (< {MIN_EDGE_SAMPLES})")
    for key, label in (("max_abs_ku", "max|Ku|"), ("max_abs_kd", "max|Kd|")):
        if result.get(key, 0.0) > COEFF_LIMIT:
            reasons.append(f"{label} = {result[key]:.3f} (> {COEFF_LIMIT})")
    result["reject"] = "; ".join(reasons)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buffer", default="inv_chain", choices=sorted(BUFFERS))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--skip-probe", action="store_true",
                        help="reuse the probe conversion from a previous run")
    args = parser.parse_args()

    buffer = BUFFERS[args.buffer]
    out = args.out or (ROOT / "results" /
                       f"s2ibispy_parameter_selection_{buffer.name}_2026-09-02")
    out.mkdir(parents=True, exist_ok=True)

    # --- Pass 1: observe the buffer -------------------------------------------
    probe_dir = out / "probe"
    probe_ibis = probe_dir / f"{buffer.name}_probe.ibs"
    if not (args.skip_probe and probe_ibis.exists()):
        config = probe_dir / f"{buffer.name}_probe.yaml"
        probe_dir.mkdir(parents=True, exist_ok=True)
        write_config(buffer.base_config, config, tr_s=PROBE_TR_S,
                     file_name=probe_ibis.name,
                     note="Observation pass for parameter selection; "
                          "inherited sim_time, safe 200 ps edge.")
        print(f"probe: converting {buffer.name} at tr = {PROBE_TR_S * 1e12:.0f} ps "
              f"with the inherited window ...", flush=True)
        code, wall = convert(buffer, config, probe_dir)
        if code != 0 or not probe_ibis.exists():
            print(f"probe failed (exit {code}); see {probe_dir / 'convert.log'}")
            return 1
        print(f"   done in {wall:.0f} s")

    seen = observe(probe_ibis)
    settle_ns = seen["settle_s"] * 1e9
    chosen_sim = max(SETTLE_MARGIN * seen["settle_s"], 10 * seen["edge_width_s"])
    print(f"\nobserved from the probe model")
    print(f"   settles by            {settle_ns:8.3f} ns")
    print(f"   output edge 20-80%    {seen['edge_width_s'] * 1e12:8.1f} ps")
    print(f"   inherited window      {seen['window_s'] * 1e9:8.3f} ns"
          f"   ({seen['window_used_pct']:.0f}% used, "
          f"{seen['sampling_s'] * 1e12:.2f} ps sampling)")
    print(f"   chosen sim_time       {chosen_sim * 1e9:8.3f} ns"
          f"   ({chosen_sim / seen['points'] * 1e12:.2f} ps sampling)")

    # --- Pass 2: sweep the edge under the chosen window ------------------------
    print(f"\nsweeping tr under sim_time = {chosen_sim * 1e9:.3f} ns")
    print(f"{'tr':>8}{'rc':>4}{'edge pts':>10}{'max|Ku|':>10}{'max|Kd|':>10}"
          f"{'s':>6}   verdict")
    rows: list[dict[str, object]] = []
    accepted: dict[str, object] | None = None
    for tr_s in SWEEP_TR_S:
        tag = f"tr{tr_s * 1e12:g}ps"
        case_dir = out / tag
        ibis = case_dir / f"{buffer.name}_{tag}.ibs"
        config = case_dir / f"{buffer.name}_{tag}.yaml"
        case_dir.mkdir(parents=True, exist_ok=True)
        write_config(buffer.base_config, config, tr_s=tr_s, sim_time_s=chosen_sim,
                     file_name=ibis.name,
                     note=f"Parameter selection; sim_time={chosen_sim:.3e}, "
                          f"tr=tf={tr_s:.3e}.")
        code, wall = convert(buffer, config, case_dir)
        row = {"buffer": buffer.name, "tr_s": tr_s, "sim_time_s": chosen_sim,
               "convert_s": round(wall, 1)}
        row.update(grade(buffer, ibis, code, seen))
        rows.append(row)
        verdict = "accept" if not row.get("reject") else f"reject: {row['reject']}"
        print(f"{tag:>8}{code:4d}{row.get('edge_samples', float('nan')):10.1f}"
              f"{row.get('max_abs_ku', float('nan')):10.3f}"
              f"{row.get('max_abs_kd', float('nan')):10.3f}{wall:6.0f}   {verdict}",
              flush=True)
        if not row.get("reject") and accepted is None:
            accepted = row      # first acceptance is the slowest; keep sweeping

    survivors = [r for r in rows if not r.get("reject")]
    best = min(survivors, key=lambda r: r["tr_s"]) if survivors else None

    summary = out / "selection.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({k for r in rows for k in r})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    decision = {
        "buffer": buffer.name,
        "observed": {k: seen[k] for k in seen},
        "chosen_sim_time_s": chosen_sim,
        "chosen_tr_s": best["tr_s"] if best else None,
        "gates": {"max_abs_coefficient": COEFF_LIMIT,
                  "min_edge_samples": MIN_EDGE_SAMPLES},
        "rejected": [{"tr_s": r["tr_s"], "reason": r["reject"]}
                     for r in rows if r.get("reject")],
    }
    (out / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")

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
    print(f"wrote {(out / 'decision.json').resolve()}")
    return 0 if best else 1


if __name__ == "__main__":
    raise SystemExit(main())
