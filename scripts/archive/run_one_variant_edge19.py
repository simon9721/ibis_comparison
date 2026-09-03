from __future__ import annotations

import csv
from pathlib import Path

import sweep_xyce_pybis_context_variants as s


def pick_10to11_rise(summary_path: Path):
    if not summary_path.exists():
        return None
    with summary_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row.get("direction") == "rise" and "10->11" in row.get("contexts", ""):
            return row
    return None


def main() -> int:
    s.base.configure_suite(["--suite", "coarse10_context"])
    result = s.run_variant(
        s.Variant(
            "edge19_flat4p2",
            "driver_OutputInput_Typical_xyce_relaxed92_edge19_tailflat4p2.sub",
            "Ku/Kd polarity selector test",
        ),
        timeout_s=300.0,
    )
    print("run_result:", result)

    out_dir = s.OUT_DIR
    edge15 = pick_10to11_rise(out_dir / "edge15_flat4p2_summary.csv")
    edge19 = pick_10to11_rise(out_dir / "edge19_flat4p2_summary.csv")

    print("edge15_10to11_rise:", edge15)
    print("edge19_10to11_rise:", edge19)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
