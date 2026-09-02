#!/usr/bin/env python3
"""How much does the characterization edge rate change the generated IBIS model?

s2ibispy drives the transistor buffer with an input ramp of tr = tf and records
the response. That ramp is a free parameter of the conversion, and the July
comparison showed it is not a minor one: 1 ns characterization gave 379 mV pad
RMSE against the transistor, 5 ps gave 12.9 mV. Two points do not make a rule,
so this sweeps the whole range and looks for where it stops mattering.

The conversion itself is deterministic -- the same config run twice, and run
again five weeks after the archived original, produces byte-identical IBIS
(563940 bytes, 8424 lines, zero differing lines). So every difference measured
here is attributable to the edge rate and nothing else.

Each variant is scored on the same bench the July study used: an HSPICE native
IBIS instance, 1 ps input edges at 5 and 15 ns, a direct 50 ohm || 2 pF load,
no package and no channel, compared against the cached transistor run on the
identical bench.

    py -3.14 scripts/sweep_s2ibispy_edge_rate.py
    py -3.14 scripts/sweep_s2ibispy_edge_rate.py --skip-convert   # re-score only
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_hspice_tr0  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

STUDY = ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27"
BASE_CONFIG = STUDY / "configs" / "inv_chain_fast_5ps.yaml"
INPUTS = STUDY / "inputs"
TRANSISTOR = (ROOT / "results" / "inv_chain_gate_state_clean_comparison_2026-07-27" /
              "cases" / "edge_1ps_base_50r_2pf" / "hspice_transistor" /
              "edge_1ps_base_50r_2pf_hspice_transistor.tr0")
OUT = ROOT / "results" / "s2ibispy_edge_rate_sweep_2026-09-02"

S2I_SRC = Path(r"C:\Users\sh3qm\code\s2ibispy\src")
S2I_DEPS = ROOT / ".codex_deps" / "s2ibispy" / "python"
IBISCHK = Path(r"C:\Users\sh3qm\code\s2ibispy\resources\ibischk\ibischk7.exe")

# tr = tf, in seconds. Spans four decades, from far slower than the buffer's own
# edge to far faster.
EDGE_RATES_S = [1.0e-9, 5.0e-10, 2.0e-10, 1.0e-10, 5.0e-11, 2.0e-11, 5.0e-12, 1.0e-12]

CONVERT_TIMEOUT_S = 900
HSPICE_TIMEOUT_S = 600
DPI = 175


def tag_for(seconds: float) -> str:
    """A filename-safe label: 1ns, 200ps, 5ps, 1ps."""
    if seconds >= 1e-9:
        return f"{seconds * 1e9:g}ns"
    return f"{seconds * 1e12:g}ps"


def write_config(seconds: float, path: Path) -> None:
    """The base config with tr and tf overridden, and nothing else touched.

    Rewritten line by line rather than through a YAML round trip so the diff
    against the base config stays reviewable: only the two scalars and the
    output filename change.
    """
    tag = tag_for(seconds)
    lines, in_tr_or_tf = [], False
    for line in BASE_CONFIG.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("file_name:"):
            lines.append(f"file_name: inv_chain_{tag}.ibs")
            continue
        if stripped.startswith("notes:"):
            lines.append(f"notes: Edge-rate sweep; tr=tf={tag}. "
                         "All other settings match inv_chain_fast_5ps.")
            continue
        if stripped in ("tr:", "tf:"):
            in_tr_or_tf = True
            lines.append(line)
            continue
        if in_tr_or_tf and stripped.startswith("typ:"):
            lines.append(line.split("typ:")[0] + f"typ: {seconds:.6e}")
            in_tr_or_tf = False
            continue
        if in_tr_or_tf and not stripped.startswith(("typ:", "min:", "max:")):
            in_tr_or_tf = False
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def convert(seconds: float, out_dir: Path) -> tuple[int, float]:
    """Run s2ibispy for one edge rate. Returns (exit code, wall seconds).

    Run from the inputs directory so HSPICE can resolve the transistor library
    by its bare filename, exactly as the July reproduction recipe does.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    config = out_dir / f"inv_chain_{tag_for(seconds)}.yaml"
    write_config(seconds, config)

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(S2I_SRC), str(S2I_DEPS)])
    hspice_dir = str(default_hspice().parent)
    env["PATH"] = hspice_dir + os.pathsep + env.get("PATH", "")

    started = time.time()
    with (out_dir / "convert.log").open("w", encoding="utf-8") as log:
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "s2ibispy", str(config),
                 "--outdir", str(out_dir), "--spice-type", "hspice",
                 "--iterate", "0", "--cleanup", "0", "--ibischk", str(IBISCHK)],
                cwd=str(INPUTS), env=env, stdout=log, stderr=subprocess.STDOUT,
                timeout=CONVERT_TIMEOUT_S,
            )
            code = completed.returncode
        except subprocess.TimeoutExpired:
            log.write(f"\ns2ibispy timed out after {CONVERT_TIMEOUT_S} s\n")
            code = 124
    return code, time.time() - started


def bench(ibis: Path, out_dir: Path) -> Path | None:
    """The July sanity bench, pointed at one generated model."""
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ibis, out_dir / ibis.name)
    deck = f"""* inv_chain s2ibispy edge-rate sweep sanity check
.title inv_chain {ibis.stem} native IBIS
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 1.8
+ 15n 1.8
+ 15.001n 0
+ 22n 0 )

VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='{ibis.name}'
+ model='driver2'
+ buffer=2
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rload pad_ibis 0 50
Cload pad_ibis 0 2p

.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran 0.001n 22n
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    with (out_dir / "hspice.log").open("w", encoding="utf-8") as log:
        try:
            subprocess.run([str(default_hspice()), "-i", "run.sp", "-o", "run"],
                           cwd=str(out_dir), stdout=log, stderr=subprocess.STDOUT,
                           timeout=HSPICE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return None
    tr0 = out_dir / "run.tr0"
    return tr0 if tr0.exists() else None


def crossing(t: np.ndarray, y: np.ndarray, level: float, rising: bool) -> float:
    for i in range(1, len(y)):
        if (rising and y[i - 1] < level <= y[i]) or (not rising and y[i - 1] > level >= y[i]):
            return float(t[i - 1] + (level - y[i - 1]) * (t[i] - t[i - 1])
                         / (y[i] - y[i - 1]))
    return float("nan")


def score(tr0: Path, reference: tuple[np.ndarray, np.ndarray]) -> dict[str, float]:
    raw = parse_hspice_tr0(tr0)
    keys = {k.lower(): k for k in raw}
    t = np.asarray(raw[keys["time"]], dtype=float) * 1e9
    pad = np.asarray(raw[next(keys[k] for k in keys if "pad" in k)], dtype=float)
    t_ref, pad_ref = reference
    lo, hi = max(t[0], t_ref[0]), min(t[-1], t_ref[-1])
    grid = np.linspace(lo, hi, 20000)
    a = np.interp(grid, t, pad)
    b = np.interp(grid, t_ref, pad_ref)
    half = 0.5 * (np.nanmax(b) + np.nanmin(b))
    return {
        "pad_rmse_mv": float(np.sqrt(np.trapezoid((a - b) ** 2, grid)
                                     / (grid[-1] - grid[0]))) * 1e3,
        "pad_max_v": float(np.nanmax(a)),
        "rise_50_ns": crossing(grid, a, half, True),
        "fall_50_ns": crossing(grid, a, half, False),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--skip-convert", action="store_true",
                        help="reuse IBIS already generated by a previous run")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    (out / "plots").mkdir(parents=True, exist_ok=True)

    raw = parse_hspice_tr0(TRANSISTOR)
    keys = {k.lower(): k for k in raw}
    t_ref = np.asarray(raw[keys["time"]], dtype=float) * 1e9
    pad_ref = np.asarray(raw[next(keys[k] for k in keys if "pad" in k)], dtype=float)
    ref = (t_ref, pad_ref)
    half = 0.5 * (np.nanmax(pad_ref) + np.nanmin(pad_ref))
    ref_rise = crossing(t_ref, pad_ref, half, True)
    ref_fall = crossing(t_ref, pad_ref, half, False)
    print(f"transistor reference: rise 50% {ref_rise:.4f} ns, "
          f"fall 50% {ref_fall:.4f} ns, peak {np.nanmax(pad_ref):.4f} V\n")

    rows = []
    print(f"{'tr=tf':>8}{'convert':>10}{'rc':>4}{'pad RMSE':>11}"
          f"{'rise 50%':>11}{'fall 50%':>11}{'shift':>9}")
    print(f"{'':>8}{'s':>10}{'':>4}{'mV':>11}{'ns':>11}{'ns':>11}{'ps':>9}")
    for seconds in EDGE_RATES_S:
        tag = tag_for(seconds)
        case_dir = out / tag
        ibis = case_dir / f"inv_chain_{tag}.ibs"
        code, wall = (0, 0.0)
        if not args.skip_convert or not ibis.exists():
            code, wall = convert(seconds, case_dir)
        if code != 0 or not ibis.exists():
            print(f"{tag:>8}{wall:10.0f}{code:4d}   conversion failed")
            rows.append({"edge_tag": tag, "edge_s": seconds, "convert_rc": code,
                         "convert_s": round(wall, 1)})
            continue
        tr0 = bench(ibis, case_dir / "sanity")
        if tr0 is None:
            print(f"{tag:>8}{wall:10.0f}{code:4d}   bench failed")
            continue
        m = score(tr0, ref)
        shift = (m["rise_50_ns"] - ref_rise) * 1e3
        print(f"{tag:>8}{wall:10.0f}{code:4d}{m['pad_rmse_mv']:11.2f}"
              f"{m['rise_50_ns']:11.4f}{m['fall_50_ns']:11.4f}{shift:9.1f}")
        rows.append({"edge_tag": tag, "edge_s": seconds, "convert_rc": code,
                     "convert_s": round(wall, 1),
                     "pad_rmse_mv": round(m["pad_rmse_mv"], 4),
                     "pad_max_v": round(m["pad_max_v"], 5),
                     "rise_50_ns": round(m["rise_50_ns"], 5),
                     "fall_50_ns": round(m["fall_50_ns"], 5),
                     "rise_shift_ps": round(shift, 2)})

    summary = out / "edge_rate_sweep.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({k for r in rows for k in r})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    good = [r for r in rows if "pad_rmse_mv" in r]
    if good:
        edges = np.array([r["edge_s"] for r in good]) * 1e12
        rmse = np.array([r["pad_rmse_mv"] for r in good])
        shift = np.array([r["rise_shift_ps"] for r in good])
        fig, axes = plt.subplots(2, 1, figsize=(11.6, 8.0), sharex=True)
        for axis, y, label, colour in ((axes[0], rmse, "Pad RMSE vs transistor (mV)", "#C02626"),
                                       (axes[1], shift, "Rise 50% shift (ps)", "#2B6CA3")):
            axis.plot(edges, y, color=colour, lw=2.4, marker="o", ms=6)
            axis.set_xscale("log")
            axis.set_ylabel(label, fontsize=12)
            axis.grid(alpha=0.3, color="#C9D3DE", lw=0.8, which="both")
            axis.tick_params(labelsize=11)
            for spine in axis.spines.values():
                spine.set_color("#3A4753")
        axes[0].set_yscale("log")
        axes[0].set_title("inv_chain  |  generated IBIS accuracy against the "
                          "characterization edge rate",
                          fontsize=15, fontweight="bold", pad=11)
        axes[1].set_xlabel("s2ibispy characterization edge, tr = tf (ps)", fontsize=12)
        fig.tight_layout()
        fig.savefig(out / "plots" / "edge_rate_sweep.png", dpi=DPI)
        plt.close(fig)

    print(f"\nwrote {summary.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
