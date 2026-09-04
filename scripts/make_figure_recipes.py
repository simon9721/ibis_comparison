#!/usr/bin/env python3
"""Emit figure-editor recipes for every per-case waveform CSV under a results tree.

Study runners already write aligned per-case CSVs. `tools/figure_editor` can open
any of them, restyle interactively, and render headlessly to PNG/SVG/PDF from a
saved JSON recipe. The missing piece was the recipe: without one, restyling a
generated figure meant editing the plotting script and re-running the sweep.

This closes that gap retroactively and for every future run. It walks a results
tree, and for each waveform CSV writes one recipe per field present (pad, Ku, Kd),
already carrying the study palette and draw order. Anyone can then open a recipe,
change colours or limits for a slide, and export vector -- with no simulation and
no script edit.

Recipes are cheap, deterministic text and reference the CSV by relative path, so
regenerating them is always safe.

    py -3.14 scripts/make_figure_recipes.py                          # default tree
    py -3.14 scripts/make_figure_recipes.py --root results/foo --render svg
    py -3.14 scripts/make_figure_recipes.py --glob 'waveforms/*.csv'

Then either:

    scripts\\launch_figure_editor.cmd <recipe>.json
    py -3.14 tools/figure_editor/figure_editor.py <recipe>.json --render out.svg
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import figures as figmod  # noqa: E402
from figure_editor import figure_document as fd  # noqa: E402

DEFAULT_ROOT = ROOT / "results" / "variant_stress_cases_2026-09-04"
FIELDS = ("pad", "ku", "kd")


def fields_present(csv_path: Path) -> list[str]:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle))
    return [f for f in FIELDS
            if any(c.endswith(f"_{f}") for c in header)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                    help="results tree to walk")
    ap.add_argument("--glob", default="**/waveforms.csv",
                    help="pattern for per-case CSVs (default **/waveforms.csv)")
    ap.add_argument("--render", choices=["svg", "png", "pdf"],
                    help="also render each recipe headlessly")
    ap.add_argument("--force", action="store_true",
                    help="overwrite recipes that already exist")
    args = ap.parse_args()

    root = args.root if args.root.is_absolute() else ROOT / args.root
    if not root.exists():
        print(f"no such tree: {root}")
        return 1

    written = rendered = skipped = 0
    for csv_path in sorted(root.glob(args.glob)):
        try:
            present = fields_present(csv_path)
        except (OSError, StopIteration):
            continue
        for field in present:
            out = csv_path.parent / f"{field}.recipe.json"
            if out.exists() and not args.force:
                skipped += 1
            else:
                try:
                    recipe = figmod.recipe_for_case(csv_path, field)
                except ValueError:
                    continue
                recipe.save(out)
                written += 1
            if args.render:
                recipe = fd.FigureRecipe.load(out)
                fd.render_recipe(recipe, out.with_suffix("").with_suffix(f".{args.render}"))
                rendered += 1

    print(f"recipes written {written}, skipped {skipped} (already present)"
          + (f", rendered {rendered}" if args.render else ""))
    if written or skipped:
        print(f"\nopen one with:\n  scripts\\launch_figure_editor.cmd "
              f"{root.relative_to(ROOT)}\\...\\pad.recipe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
