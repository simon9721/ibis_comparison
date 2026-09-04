#!/usr/bin/env python3
"""Overlay every variant in a family at the same depth target.

The per-case figures show one variant at a time, which answers "does this buffer
behave" but not "does the family behave the same way". Holding the depth fixed and
overlaying the family answers the second: at 50% of its own settled swing, does
every inv_chain variant show the same error, or does the error track a device
parameter?

Depth is the right axis to hold, not pulse width. Each variant reaches 50% at a
different width -- inv_base8 at 102 ps, inv_stage4 at 83 ps, inv_weak at 114 ps --
because they are deliberately faster or slower. Overlaying at equal width would
compare different amounts of stress.

Time is plotted relative to each case's own reverse edge, since the widths differ.

    py -3.14 scripts/overlay_variant_family.py                  # all depths
    py -3.14 scripts/overlay_variant_family.py --depth 50 --family inv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

CASES = ROOT / "results" / "variant_stress_cases_2026-09-04"
OUT = ROOT / "results" / "variant_family_overlay_2026-09-04"

# One colour per variant within a family, stable across depths so a reader can
# follow the same buffer from slide to slide.
COLOURS = ["#C02626", "#2B6CA3", "#1B6B4F", "#7B2CBF", "#D97706"]


def read(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open()))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def collect(family: str, depth: int) -> list[tuple[str, float, dict]]:
    out = []
    for variant_dir in sorted(CASES.iterdir()):
        if not variant_dir.is_dir() or not variant_dir.name.startswith(family):
            continue
        # Pick the most recent match, not the first alphabetically. Earlier
        # target sets left directories behind -- inv_stage4 has both
        # depth50_w104ps (superseded) and depth50_w83ps (current), and sorted()
        # puts w104 first because "1" < "8". That silently overlaid a case from a
        # different depth definition, showing stage4 peaking at 1.11 V where its
        # actual 50% case reaches 0.73.
        matches = [c for c in variant_dir.glob(f"depth{depth}_w*ps")
                   if (c / "waveforms.csv").exists()]
        if not matches:
            continue
        case = max(matches, key=lambda c: c.stat().st_mtime)
        width = int(case.name.split("_w")[1].replace("ps", ""))
        out.append((variant_dir.name, 5.0 + width / 1000.0, read(case / "waveforms.csv")))
    return out


def draw(family: str, depth: int, series: list[tuple[str, float, dict]]) -> None:
    if len(series) < 2:
        print(f"  {family} depth{depth}: only {len(series)} variant(s), skipped")
        return
    fields = [("silicon_pad", "HSPICE transistor"),
              ("gate_state_pad", "gate-state"),
              ("delay_cmd_pad", "delay_cmd")]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.6), sharey=True)
    for axis, (col, label) in zip(axes, fields):
        for (variant, rev, d), colour in zip(series, COLOURS):
            if col not in d:
                continue
            axis.plot((d["time_ns"] - rev) * 1e3, d[col], color=colour, lw=2.2,
                      label=variant)
        axis.axvline(0.0, color="#8A8A8A", ls="--", lw=1.6)
        axis.set_title(label, fontsize=15, fontweight="bold")
        axis.set_xlabel("Time from the reverse edge (ps)")
        axis.set_xlim(-260, 420)
        axis.grid(alpha=0.3)
    axes[0].set_ylabel("Pad voltage (V)")
    axes[0].legend(fontsize=11, loc="upper left")
    fig.suptitle(f"{family} family  |  every variant at {depth}% of its own "
                 f"settled swing", fontsize=16, fontweight="bold")
    fig.tight_layout()
    path = OUT / f"{family}_depth{depth}_pad.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.6), sharey=True)
    for axis, field in zip(axes, ("ku", "kd")):
        for (variant, rev, d), colour in zip(series, COLOURS):
            a, b = f"silicon_{field}", f"gate_state_{field}"
            if a in d:
                axis.plot((d["time_ns"] - rev) * 1e3, d[a], color=colour, lw=3.4,
                          alpha=0.35, label=f"{variant} transistor")
            if b in d:
                axis.plot((d["time_ns"] - rev) * 1e3, d[b], color=colour, lw=1.8,
                          label=f"{variant} gate-state")
        axis.axvline(0.0, color="#8A8A8A", ls="--", lw=1.6)
        axis.axhspan(-0.05, 1.05, color="#EAF1F7", zorder=0)
        axis.set_title(field.capitalize(), fontsize=15, fontweight="bold")
        axis.set_xlabel("Time from the reverse edge (ps)")
        axis.set_xlim(-260, 420)
        axis.grid(alpha=0.3)
    axes[0].set_ylabel("coefficient")
    axes[0].legend(fontsize=9, ncol=2, loc="upper left")
    fig.suptitle(f"{family} family  |  coefficients at {depth}% of own swing",
                 fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / f"{family}_depth{depth}_kukd.png", dpi=200)
    plt.close(fig)
    print(f"  {family} depth{depth}: {len(series)} variants "
          f"({', '.join(v for v, _, _ in series)})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family", action="append", choices=["inv", "ex2"])
    ap.add_argument("--depth", action="append", type=int)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    families = args.family or ["inv", "ex2"]
    depths = args.depth or [90, 80, 70, 60, 50]
    for family in families:
        for depth in depths:
            draw(family, depth, collect(family, depth))
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
