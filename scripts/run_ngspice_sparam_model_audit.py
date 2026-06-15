from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_sparam_conversion_quality_study import (  # noqa: E402
    DEFAULT_NGSPICE,
    SmokeCase,
    rel,
    run_ngspice_cases,
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_cases(stop_ns: float) -> list[SmokeCase]:
    return [
        SmokeCase("audit_amp1p5_edge5_r50", 50.0, 5.0, 1.5, stop_ns=stop_ns),
        SmokeCase("audit_amp1p5_edge50_r50", 50.0, 50.0, 1.5, stop_ns=stop_ns),
        SmokeCase("audit_amp1p5_edge500_r50", 50.0, 500.0, 1.5, stop_ns=stop_ns),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ngspice transient audit cases on an exported S-parameter SPICE model.")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--ports", type=int, default=4)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--stop-ns", type=float, default=35.0)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    rows = run_ngspice_cases(args.ngspice.resolve(), args.model.resolve(), args.ports, args.out_dir.resolve(), make_cases(args.stop_ns), args.timeout)
    for row in rows:
        row["model"] = rel(args.model)
    out_csv = args.out_dir.resolve() / "ngspice_model_audit.csv"
    write_csv(out_csv, rows)
    print(out_csv)
    for row in rows:
        print(row["case"], "rc=", row.get("return_code"), "finite=", row.get("finite_reasonable"), "rxmax=", row.get("v(p3)_max_v"), "trouble=", row.get("last_trouble", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
