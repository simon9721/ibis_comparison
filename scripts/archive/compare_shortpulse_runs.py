#!/usr/bin/env python3
"""Compare short-pulse runs against silicon, case by case.

`compare_silicon_anchored_shortpulse.py` writes one waveform CSV per case with
silicon, native IBIS and the model on a common grid. Comparing two such runs
tells you whether a model change helped, but only if the cases are matched by
what was actually simulated rather than by filename: runs that select widths
from the depth sweep are tagged by depth, runs given explicit widths are tagged
by width, and the same stimulus appears under both names.

Errors are time-weighted. HSPICE's adaptive grid puts roughly ten times more
samples inside a transition than outside it, so a plain mean over samples
reports the transition almost exclusively and inflates every number by about an
order of magnitude. Rankings survive that; absolute values do not.

Native IBIS is carried through every table as the reference point, since it is
the same information the model has and shows what the format can reach.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))

import numpy as np  # noqa: E402


def read_cases(run: Path) -> dict[tuple[str, str, int], str]:
    """Maps (device, direction, width_ps) to the tag its waveform file uses."""
    path = run / "cases.csv"
    if not path.exists():
        return {}
    out: dict[tuple[str, str, int], str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "OK":
                continue
            width = float(row["pulse_width_ps"])
            depth = float(row["depth_target"])
            direction = row["direction"]
            tag = (f"{direction}_w{int(round(width))}ps" if not np.isfinite(depth)
                   else f"{direction}_depth{int(round(depth * 100))}")
            out[(row["device"], direction, int(round(width)))] = f"{row['device']}_{tag}"
    return out


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def time_rmse(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    a, b, t = a[ok], b[ok], t[ok]
    if len(t) < 2 or t[-1] <= t[0]:
        return float("nan")
    return float(np.sqrt(np.trapezoid((a - b) ** 2, t) / (t[-1] - t[0])))


def errors(path: Path, source: str) -> dict[str, float]:
    d = load(path)
    t = d["time_ns"]
    return {
        "pad": time_rmse(d[f"{source}_pad"], d["silicon_pad"], t) * 1000.0,
        "ku": time_rmse(d[f"{source}_ku"], d["silicon_ku"], t),
        "kd": time_rmse(d[f"{source}_kd"], d["silicon_kd"], t),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path,
                        help="result directories; the first is the baseline")
    parser.add_argument("--label", action="append", default=None,
                        help="display name per run, in the same order")
    args = parser.parse_args()

    runs = [r if r.is_absolute() else (ROOT / r) for r in args.runs]
    labels = args.label or [r.name for r in runs]
    if len(labels) != len(runs):
        parser.error("--label must be given once per run")

    indexes = [read_cases(r) for r in runs]
    shared = set(indexes[0])
    for index in indexes[1:]:
        shared &= set(index)
    if not shared:
        print("no cases common to all runs")
        return 1

    width = max(8, max(len(l) for l in labels))
    print(f"pad error vs silicon, mV (time-weighted). {len(shared)} shared cases.")
    # Native IBIS is reported per run, not once. It is the same engine every
    # time, but it is scored against that run's silicon, so anything that moves
    # the reference -- a model card, a different stimulus -- moves it too.
    header = f"{'case':32s}"
    for label in labels:
        header += f" {'nat:' + label:>{width}s} {label:>{width}s}"
    print(header)

    totals = {label: [] for label in labels}
    natives = {label: [] for label in labels}
    per_device: dict[str, dict[str, list[float]]] = {}
    for key in sorted(shared):
        device, direction, width_ps = key
        paths = [r / "waveforms" / f"{index[key]}.csv" for r, index in zip(runs, indexes)]
        if not all(p.exists() for p in paths):
            continue
        line = f"{device + ' ' + direction + ' ' + str(width_ps) + 'ps':32s}"
        for path, label in zip(paths, labels):
            native = errors(path, "hspice")["pad"]
            value = errors(path, "pybis")["pad"]
            natives[label].append(native)
            totals[label].append(value)
            per_device.setdefault(device, {}).setdefault(label, []).append(value)
            line += f" {native:>{width}.1f} {value:>{width}.1f}"
        print(line)

    print()
    print(f"{'mean':32s}", end="")
    for label in labels:
        print(f" {np.mean(natives[label]):>{width}.1f} {np.mean(totals[label]):>{width}.1f}", end="")
    print()

    print("\nby buffer:")
    for device in sorted(per_device):
        print(f"  {device:12s}", end="")
        for label in labels:
            values = per_device[device][label]
            print(f" {label}={np.mean(values):6.1f}", end="")
        print()

    base = labels[0]
    print(f"\nagainst {base}:")
    for label in labels[1:]:
        deltas = [n - b for b, n in zip(totals[base], totals[label])]
        better = sum(1 for d in deltas if d < -0.5)
        worse = sum(1 for d in deltas if d > 0.5)
        print(f"  {label:24s} better {better:2d}  worse {worse:2d}  "
              f"flat {len(deltas) - better - worse:2d}  mean {np.mean(deltas):+.1f} mV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
