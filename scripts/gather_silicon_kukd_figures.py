#!/usr/bin/env python3
"""Collect one representative set of transistor-derived Ku/Kd figures.

These figures were spread over four result directories built on different
days, two of which predate both the io_buf model-card correction and the
uniform-grid solve. This copies the current, correct ones into a single
numbered folder and writes an index naming the source of each, so there is one
place to look and no ambiguity about which version a figure is.

Nothing is regenerated. Sources are the authoritative copies; this only
gathers.

    py -3.14 scripts/gather_silicon_kukd_figures.py
"""
from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FULL = ROOT / "results" / "full_swing_kukd_comparison_2026-08-27"
GRID = ROOT / "results" / "silicon_kukd_conditioning_2026-08-27"
MID = ROOT / "results" / "silicon_kukd_recovery_uniform_2026-08-27"
OUT = ROOT / "results" / "silicon_kukd_figures_2026-08-27"

# order, source, new name, what it is for
PLAN = [
    (FULL / "01_io_buf_full_swing_kukd.png", "01_validation_io_buf_full_swing.png",
     "Validation. io_buf clean full transition, silicon vs HSPICE native IBIS vs "
     "pybis. Three independent routes to the same coefficients."),
    (FULL / "02_inv_chain_full_swing_kukd.png", "02_validation_inv_chain_full_swing.png",
     "Validation, second buffer. Same comparison on inv_chain."),
    (GRID / "01_io_buf_full_transition.png", "03_grid_artifact_io_buf_full_swing.png",
     "Why the earlier figures spiked. Union of the two fixture grids on the left, "
     "one uniform 5 ps grid on the right. Not a conditioning failure -- cond never "
     "exceeds 5.5."),
    (GRID / "03_io_buf_short_high_70pct.png", "04_grid_artifact_io_buf_short_high_70.png",
     "The same artifact and the same fix on a reversal case."),
    (MID / "plots" / "io_buf_short_high_70.png", "05_reversal_io_buf_short_high_70.png",
     "Mid-reversal. io_buf short high 70%, silicon vs native IBIS vs gate-state."),
    (MID / "plots" / "io_buf_short_low_70.png", "06_reversal_io_buf_short_low_70.png",
     "Mid-reversal, opposite direction. The case where native IBIS departs from "
     "silicon most sharply."),
    (MID / "plots" / "inv_chain_short_high_50.png", "07_reversal_inv_chain_short_high_50.png",
     "Mid-reversal. inv_chain short high 50%, where silicon produces no pulse at all."),
    (MID / "plots" / "ex2_short_low_70.png", "08_reversal_ex2_short_low_70.png",
     "Mid-reversal. ex2 short low 70%, the third buffer."),
]

# Written by build_kukd_edge_closeups.py straight into this folder, continuing
# the numbering. Listed here so the index describes the whole set.
CLOSEUPS = [
    ("09_edge_io_buf_rising.png",
     "Close-up. io_buf rising edge, Ku and Kd, cropped to the transition."),
    ("10_edge_io_buf_falling.png",
     "Close-up. io_buf falling edge. Silicon leads both models by 35-54 ps."),
    ("11_edge_inv_chain_rising.png",
     "Close-up. inv_chain rising edge -- a 16 ps transition, where pybis fires "
     "270 ps early."),
    ("12_edge_inv_chain_falling.png",
     "Close-up. inv_chain falling edge."),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    index = ["# Transistor-derived Ku/Kd — representative set",
             "",
             "Gathered by `scripts/gather_silicon_kukd_figures.py`. Every figure below is",
             "the current version: io_buf runs use the stock `models/hspice.mod` card, and",
             "the two-fixture solve runs on a uniform 5 ps grid.",
             "",
             "Superseded and kept only for history:",
             "",
             "- `results/silicon_kukd_recovery_2026-08-19/` — union grid, and io_buf on the",
             "  RDSW-zeroed card that makes the device 8-16% too strong",
             "- `results/silicon_vs_pybis_kukd_figures_2026-08-19/` — same caveats",
             "",
             "| # | figure | what it shows | source |",
             "|---|---|---|---|"]
    copied = 0
    for n, (src, name, caption) in enumerate(PLAN, start=1):
        if not src.exists():
            print(f"missing  {src}")
            index.append(f"| {n} | _(missing)_ | {caption} | `{src.relative_to(ROOT)}` |")
            continue
        shutil.copy2(src, out / name)
        copied += 1
        index.append(f"| {n} | `{name}` | {caption} | `{src.relative_to(ROOT)}` |")

    for n, (name, caption) in enumerate(CLOSEUPS, start=len(PLAN) + 1):
        exists = (out / name).exists()
        index.append(f"| {n} | `{name}`{'' if exists else ' _(not built)_'} | {caption} "
                     f"| `scripts/build_kukd_edge_closeups.py` |")

    summary = MID / "recovery_vs_silicon.csv"
    if summary.exists():
        shutil.copy2(summary, out / "recovery_vs_silicon.csv")
        rows = list(csv.DictReader(summary.open(encoding="utf-8")))
        index += ["", "## Model and native IBIS against silicon, post-reversal Ku",
                  "", "Time-weighted RMSE. From `recovery_vs_silicon.csv` in this folder.",
                  "", "| buffer | direction | target | gate-state | native IBIS |",
                  "|---|---|---:|---:|---:|"]
        for r in rows:
            index.append(f"| {r['device']} | {r['direction'].replace('_', ' ')} | "
                         f"{r['target_percent']}% | {float(r['model_vs_silicon_ku_post']):.4f} | "
                         f"{float(r['native_vs_silicon_ku_post']):.4f} |")

    (out / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"gathered {copied}/{len(PLAN)} figures")
    print(out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
