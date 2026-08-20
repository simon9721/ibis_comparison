#!/usr/bin/env python3
"""Run every candidate model over the same 90%-50% loaded-swing stress cases.

The stress axis comes from `three_buffer_loaded_swing_stress_sweep_2026-08-14`,
which searched for the pulse width at which the *transistor* pad reaches each
fraction of its full swing before the reverse edge. Those widths are properties
of HSPICE references alone, so holding them fixed and varying only the model
makes the methods directly comparable -- an earlier attempt changed the width
selection and the model together and could attribute the difference to neither.

Each case is run through `compare_silicon_anchored_shortpulse`, which records
silicon, HSPICE native IBIS and the model on one grid. Silicon Ku/Kd come from
the two-fixture solve, so a method can be scored on the coefficients and not
only on the pad.

Methods are run in priority order and each is resumable, so an interrupted run
still leaves every completed method usable. HSPICE results are shared across
methods through the reference cache; only the ngspice model run repeats.

    python scripts/run_stress_method_matrix.py --out results/stress_matrix
    python scripts/run_stress_method_matrix.py --method delay_cmd --method legacy
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

STRESS_SELECTION = (
    ROOT / "results" / "three_buffer_loaded_swing_stress_sweep_2026-08-14" / "selection.csv"
)

# Ordered by what each one is expected to tell us, because a run that is cut
# short should still have answered the most important questions.
METHODS = (
    ("gate_state", "InputDrivenTwoStateGateDirectionalDualResidualFull",
     "current gate-state model, edge-integrating command plus restore patch"),
    ("delay_cmd", "InputDrivenTwoStateGateDelayCommandFull",
     "gate-state with the command as a transport-delayed copy of the input level"),
    ("predriver_cmd", "InputDrivenTwoStateGatePredriverCommandFull",
     "gate-state with the command delay carried by a state, so it can be interrupted"),
    ("legacy", "InputDriven",
     "pybis before any interruption handling; the reference point for all of it"),
    ("coeff_match", "InputDrivenValueMatchedReplayV2Hybrid",
     "resume the opposite curve where it holds the present coefficient value"),
    ("pad_match", "InputDrivenPadMatchedReplayV1",
     "resume where the recorded pad trajectory holds the present pad voltage"),
    ("pad_match_slew", "InputDrivenPadMatchedReplayV1SlewAware",
     "pad matching with dV/dt used to disambiguate the crossing"),
    ("hybrid", "InputDrivenTwoStateGateDirectionalDualResidualHybrid",
     "gate-state, handing off to matched replay in a window around the reversal"),
)


def stress_cases() -> list[tuple[str, str, list[tuple[int, float]]]]:
    """Returns (device, direction, [(target_percent, width_ps)]) from the sweep."""
    if not STRESS_SELECTION.exists():
        raise FileNotFoundError(STRESS_SELECTION)
    grouped: dict[tuple[str, str], list[tuple[int, float]]] = {}
    with STRESS_SELECTION.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row["device"], row["direction"])
            grouped.setdefault(key, []).append(
                (int(float(row["target_percent"])), float(row["pulse_width_ps"]))
            )
    return [(device, direction, sorted(widths, reverse=True))
            for (device, direction), widths in sorted(grouped.items())]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "stress_method_matrix")
    parser.add_argument("--method", action="append",
                        choices=[key for key, _, _ in METHODS],
                        help="restrict to these methods; default runs all, in priority order")
    parser.add_argument("--device", action="append")
    parser.add_argument("--ngspice-timeout", type=int, default=240)
    args = parser.parse_args()

    out_root = args.out if args.out.is_absolute() else ROOT / args.out
    selected = args.method or [key for key, _, _ in METHODS]
    cases = stress_cases()
    if args.device:
        cases = [c for c in cases if c[0] in set(args.device)]

    total = sum(len(widths) for _, _, widths in cases)
    print(f"{total} stress cases x {len(selected)} methods", flush=True)

    for key, mode, description in METHODS:
        if key not in selected:
            continue
        out = out_root / key
        print(f"\n{'=' * 70}\n{key}: {description}\n  mode {mode}\n  -> {out}\n{'=' * 70}",
              flush=True)
        env = dict(os.environ, PYBIS_GATE_MODE=mode)
        for device, direction, widths in cases:
            command = [
                sys.executable, str(ROOT / "scripts" / "compare_silicon_anchored_shortpulse.py"),
                "--out", str(out), "--device", device, "--direction", direction,
                "--ngspice-timeout", str(args.ngspice_timeout),
            ]
            for _, width_ps in widths:
                command += ["--width-ps", f"{width_ps:.1f}"]
            print(f"-- {key} {device} {direction} "
                  f"({', '.join(f'{p}%' for p, _ in widths)})", flush=True)
            result = subprocess.run(command, cwd=ROOT, env=env)
            if result.returncode != 0:
                # One buffer failing should not cost the rest of the matrix.
                print(f"   FAILED rc={result.returncode}", flush=True)
    print("\nmatrix complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
