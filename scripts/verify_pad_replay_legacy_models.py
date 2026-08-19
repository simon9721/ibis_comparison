#!/usr/bin/env python3
"""Verify generated legacy pybis models against a known hash manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, required=True)
    parser.add_argument("--baseline-manifest", type=Path, required=True)
    args = parser.parse_args()

    study_dir = args.study_dir.resolve()
    baseline_manifest = args.baseline_manifest.resolve()
    with baseline_manifest.open(newline="", encoding="utf-8-sig") as handle:
        expected_rows = list(csv.DictReader(handle))

    rows: list[dict[str, str]] = []
    all_identical = True
    for expected in expected_rows:
        device = expected["device"]
        profile = expected["profile"]
        model_dir = study_dir / "generated_models" / device / profile / "legacy"
        candidates = sorted(model_dir.glob("*.sub"))
        if len(candidates) != 1:
            rows.append(
                {
                    "device": device,
                    "profile": profile,
                    "result": "MISSING" if not candidates else "MULTIPLE_MODELS",
                    "sha256": "",
                    "expected_sha256": expected["sha256"],
                    "model_path": str(model_dir),
                }
            )
            all_identical = False
            continue

        model = candidates[0]
        actual_hash = sha256(model)
        identical = actual_hash == expected["sha256"]
        rows.append(
            {
                "device": device,
                "profile": profile,
                "result": "IDENTICAL" if identical else "DIFFERENT",
                "sha256": actual_hash,
                "expected_sha256": expected["sha256"],
                "model_path": str(model.relative_to(study_dir)),
            }
        )
        all_identical &= identical

    output = study_dir / "verification" / "legacy_model_hash_check.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "device",
        "profile",
        "result",
        "sha256",
        "expected_sha256",
        "model_path",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(f"{row['device']}/{row['profile']}: {row['result']}")
    print(f"Wrote {output}")
    return 0 if all_identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
