#!/usr/bin/env python3
"""Score every method in the stress matrix against silicon, per stress level.

Reads whatever `run_stress_method_matrix.py` has produced so far -- methods run
in priority order and each is resumable, so a partial matrix is normal and is
reported as such rather than being treated as an error.

Errors are time-weighted, since HSPICE's adaptive grid oversamples transitions
by roughly ten to one and a sample mean would report the transition almost
exclusively. HSPICE native IBIS is scored the same way in every table: it has
exactly the information the models have, so it is the honest bar for them.

Writes summary.csv and per_case.csv, and prints the tables.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402

from run_stress_method_matrix import METHODS, case_tag, stress_cases  # noqa: E402


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


def score(path: Path, source: str) -> dict[str, float]:
    d = load(path)
    t = d["time_ns"]
    return {
        "pad_mv": time_rmse(d[f"{source}_pad"], d["silicon_pad"], t) * 1000.0,
        "ku": time_rmse(d[f"{source}_ku"], d["silicon_ku"], t),
        "kd": time_rmse(d[f"{source}_kd"], d["silicon_kd"], t),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path,
                        default=ROOT / "results" / "stress_method_matrix_2026-08-20")
    parser.add_argument("--metric", choices=("pad_mv", "ku", "kd"), default="pad_mv")
    args = parser.parse_args()

    root = args.matrix if args.matrix.is_absolute() else ROOT / args.matrix
    available = [(key, label) for key, _, label in METHODS if (root / key / "waveforms").exists()]
    if not available:
        print(f"no method output under {root}")
        return 1

    per_case: list[dict[str, object]] = []
    for device, direction, widths in stress_cases():
        for target, width_ps in widths:
            tag = case_tag(device, direction, width_ps)
            row: dict[str, object] = {
                "device": device, "direction": direction, "target_percent": target,
                "pulse_width_ps": round(width_ps, 1),
            }
            native_done = False
            for key, _ in available:
                path = root / key / "waveforms" / f"{tag}.csv"
                if not path.exists():
                    continue
                values = score(path, "pybis")
                for metric, value in values.items():
                    row[f"{key}_{metric}"] = round(value, 4)
                if not native_done:
                    # Identical across methods -- same engine, same stimulus --
                    # so take it from whichever method ran first.
                    for metric, value in score(path, "hspice").items():
                        row[f"native_{metric}"] = round(value, 4)
                    native_done = True
            if native_done:
                per_case.append(row)

    if not per_case:
        print("no completed cases yet")
        return 1

    metric = args.metric
    unit = "mV" if metric == "pad_mv" else ""
    columns = ["native"] + [key for key, _ in available]
    width = max(11, max(len(c) for c in columns) + 1)

    print(f"{metric} error against silicon{(' (' + unit + ')') if unit else ''}, time-weighted")
    print(f"{len(per_case)} of 30 stress cases complete\n")

    header = f"{'case':30s}"
    for column in columns:
        header += f"{column:>{width}s}"
    print(header)

    last = None
    for row in per_case:
        group = (row["device"], row["direction"])
        if last is not None and group != last:
            print()
        last = group
        name = f"{row['device']} {row['direction'].replace('short_', '')} {row['target_percent']}%"
        line = f"{name:30s}"
        for column in columns:
            value = row.get(f"{column}_{metric}")
            line += f"{value:>{width}.1f}" if isinstance(value, float) and metric == "pad_mv" \
                else (f"{value:>{width}.3f}" if isinstance(value, float) else f"{'-':>{width}s}")
        print(line)

    print("\n" + "=" * (30 + width * len(columns)))
    # A method that fails to converge on a case contributes nothing to its own
    # mean, so comparing per-method means silently rewards failing on the hard
    # ones. The like-for-like row averages only over cases every method solved.
    common = [r for r in per_case
              if all(isinstance(r.get(f"{c}_{metric}"), float)
                     and np.isfinite(r[f"{c}_{metric}"]) for c in columns)]
    summary: list[dict[str, object]] = []
    for label, subset in [("all cases (own coverage)", per_case),
                          (f"cases all methods solved ({len(common)})", common)] + [
        (f"{device}", [r for r in per_case if r["device"] == device])
        for device in sorted({str(r["device"]) for r in per_case})
    ]:
        if not subset:
            continue
        line = f"{label:30s}"
        entry: dict[str, object] = {"group": label, "cases": len(subset)}
        for column in columns:
            values = [r[f"{column}_{metric}"] for r in subset
                      if isinstance(r.get(f"{column}_{metric}"), float)
                      and np.isfinite(r[f"{column}_{metric}"])]
            if values:
                mean = float(np.mean(values))
                entry[column] = round(mean, 4)
                line += f"{mean:>{width}.1f}" if metric == "pad_mv" else f"{mean:>{width}.3f}"
            else:
                line += f"{'-':>{width}s}"
        summary.append(entry)
        print(line)

    out_per_case = root / "per_case.csv"
    fields: list[str] = []
    for row in per_case:
        for key in row:
            if key not in fields:
                fields.append(key)
    with out_per_case.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(per_case)

    out_summary = root / "summary.csv"
    with out_summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    print(f"\nwrote {out_per_case.relative_to(ROOT)}")
    print(f"wrote {out_summary.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
