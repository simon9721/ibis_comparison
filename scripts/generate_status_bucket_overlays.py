from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from generate_simple_good_bad_overlays import (
    ROOT,
    case_sort,
    fnum,
    plot_one,
    read_csv,
    safe_name,
    write_csv,
)


BUCKET_DESCRIPTIONS = {
    "01_full_pass": "Overall HSPICE audit PASS: RX shape, RX timing, and TX/reflection checks pass.",
    "02_rx_shape_pass_timing_warn": "RX shape matches HSPICE, but timing is WARN/ambiguous. Useful RX-shape evidence, not timing-certified.",
    "03_rx_shape_pass_other_warn": "RX shape passes and timing is not the blocker, but another audit item prevents full PASS.",
    "04_rx_shape_fail": "RX voltage-shape mismatch against HSPICE.",
    "05_other_warn_or_fail": "Other WARN/FAIL cases that do not fit the main buckets.",
}


def status_bucket(row: dict[str, str]) -> str:
    if row.get("hspice_audit_class") == "PASS":
        return "01_full_pass"
    if row.get("rx_shape_hspice_audit_class") == "PASS" and row.get("rx_timing_hspice_audit_class") == "WARN":
        return "02_rx_shape_pass_timing_warn"
    if row.get("rx_shape_hspice_audit_class") == "PASS":
        return "03_rx_shape_pass_other_warn"
    if row.get("rx_shape_hspice_audit_class") == "FAIL":
        return "04_rx_shape_fail"
    return "05_other_warn_or_fail"


def build(args: argparse.Namespace) -> int:
    study_dir = args.study_dir.resolve()
    out_dir = args.out_dir.resolve()
    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corr = read_csv(study_dir / "hspice_correlation.csv")
    rows = [
        row for row in corr
        if row.get("correlation_status") == "ok"
        and row.get("hspice_tr0")
        and row.get("ngspice_raw")
        and row.get("hspice_audit_class") in {"PASS", "WARN", "FAIL"}
    ]
    if args.max_cases_per_bucket:
        selected = []
        for bucket in BUCKET_DESCRIPTIONS:
            selected.extend(
                sorted([row for row in rows if status_bucket(row) == bucket], key=case_sort)[: args.max_cases_per_bucket]
            )
        rows = selected

    index_rows: list[dict[str, object]] = []
    for idx, row in enumerate(sorted(rows, key=lambda r: (status_bucket(r), *case_sort(r))), start=1):
        bucket = status_bucket(row)
        stem = safe_name(f"{idx:03d}_{row.get('hspice_audit_class', '')}_{row.get('channel_id', '')}_{row.get('case', '')}")
        for signal_kind in ("rx", "tx"):
            out_path = out_dir / bucket / f"{signal_kind}_side" / f"{stem}_{signal_kind}.png"
            plot_one(row, out_path, signal_kind)
            index_rows.append(
                {
                    "bucket": bucket,
                    "bucket_description": BUCKET_DESCRIPTIONS[bucket],
                    "signal": signal_kind,
                    "channel_id": row.get("channel_id", ""),
                    "case": row.get("case", ""),
                    "selected_candidate_family": row.get("selected_candidate_family", ""),
                    "independent_rx_shape": row.get("rx_voltage_shape_class", ""),
                    "independent_rx_timing": row.get("rx_timing_class", ""),
                    "hspice_rx_shape": row.get("rx_shape_hspice_audit_class", ""),
                    "hspice_rx_timing": row.get("rx_timing_hspice_audit_class", ""),
                    "hspice_audit_class": row.get("hspice_audit_class", ""),
                    "hspice_audit_reason": row.get("hspice_audit_reason", ""),
                    "rx_active_rmse_mv": 1000.0 * fnum(row, "rx_active_rmse_v"),
                    "rx_active_maxabs_mv": 1000.0 * fnum(row, "rx_active_maxabs_v"),
                    "tx_active_rmse_mv": 1000.0 * fnum(row, "tx_active_rmse_v"),
                    "tx_active_maxabs_mv": 1000.0 * fnum(row, "tx_active_maxabs_v"),
                    "figure": str(out_path.relative_to(out_dir)).replace("\\", "/"),
                }
            )

    write_csv(out_dir / "index.csv", index_rows)
    case_counts = {}
    for bucket in BUCKET_DESCRIPTIONS:
        case_counts[bucket] = len(
            {
                (row["channel_id"], row["case"])
                for row in index_rows
                if row["bucket"] == bucket
            }
        )
    readme = [
        "# Status-Bucket HSPICE-ngspice Overlays",
        "",
        "This is the simpler plot set: one signal per figure, with separate RX-side and TX-side overlays.",
        "",
        "The cases are not split into simple good/bad because timing WARN is not automatically bad. Instead, folders describe what the audit actually says.",
        "",
        f"Source study: `{study_dir}`",
        "",
        "## Buckets",
        "",
    ]
    for bucket, desc in BUCKET_DESCRIPTIONS.items():
        readme.append(f"- `{bucket}`: `{case_counts[bucket]}` cases. {desc}")
    readme.extend(
        [
            "",
        "Each bucket contains:",
        "",
        "- `rx_side/`: one RX/output overlay per case",
        "- `tx_side/`: one TX/input overlay per case",
        "",
        "Plot scale policy:",
        "",
        "- Small RX waveforms are plotted in mV with 1 mV major y-axis increments and at least a 4 mV span.",
        "- Larger RX/TX waveforms are plotted in V with coarse rounded y-axis increments, usually 0.2 V.",
        "- This avoids making sub-mV differences look visually huge.",
        "",
        "See `index.csv` for metrics and exact figure filenames.",
        "",
    ]
    )
    (out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")

    print(f"Wrote status-bucket overlays under {out_dir}")
    for bucket, count in case_counts.items():
        print(f"{bucket}: {count}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate status-bucket one-panel RX/TX overlays.")
    p.add_argument("--study-dir", type=Path, default=ROOT / "results" / "sparam_rx_trust_v2_2026-06-11")
    p.add_argument("--out-dir", type=Path, default=ROOT / "results" / "status_bucket_overlays_2026-06-12")
    p.add_argument("--max-cases-per-bucket", type=int, default=0)
    p.add_argument("--clean", action="store_true", default=True)
    return p


def main() -> int:
    return build(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
