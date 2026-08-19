#!/usr/bin/env python3
"""Merge isolated pad-match load workers into the canonical portability study."""

from __future__ import annotations

import csv
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "results" / "three_buffer_pad_matched_replay_load_portability_2026-08-04"
SOURCES = (
    DESTINATION,
    ROOT / "results" / "three_buffer_pad_matched_replay_load_inv_slow_work_2026-08-04",
    ROOT / "results" / "three_buffer_pad_matched_replay_load_inv_fast_work_2026-08-04",
    ROOT / "results" / "three_buffer_pad_matched_replay_load_ex2_slow_work_2026-08-04",
    ROOT / "results" / "three_buffer_pad_matched_replay_load_ex2_fast_work_2026-08-04",
)
TREE_NAMES = (
    "calibration", "generated_models", "hspice_references", "runs",
    "waveform_data", "plots",
)
CSV_KEYS = {
    "candidate_metrics.csv": ("device", "profile", "load_ohm", "load_pf", "case_id", "flow"),
    "run_manifest.csv": ("device", "profile", "load_ohm", "load_pf", "case_id", "flow"),
    "calibration_manifest.csv": ("device", "profile"),
    "reference_manifest.csv": ("device", "profile", "load_ohm", "load_pf", "case_id", "reference"),
    "figure_manifest.csv": ("device", "profile", "load", "case_id", "figure"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for source in SOURCES[1:]:
        if not source.exists():
            raise FileNotFoundError(source)
        for tree_name in TREE_NAMES:
            tree = source / tree_name
            if tree.exists():
                shutil.copytree(tree, DESTINATION / tree_name, dirs_exist_ok=True)

    for filename, key_fields in CSV_KEYS.items():
        merged: dict[tuple[str, ...], dict[str, str]] = {}
        for source in SOURCES:
            for row in read_csv(source / filename):
                key = tuple(row.get(field, "") for field in key_fields)
                merged[key] = row
        rows = sorted(
            merged.values(),
            key=lambda row: tuple(row.get(field, "") for field in key_fields),
        )
        write_csv(DESTINATION / filename, rows)
        print(f"{filename}: {len(rows)}")
    print(DESTINATION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
