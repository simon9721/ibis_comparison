#!/usr/bin/env python3
"""Figure conventions for the study, and the bridge to the figure editor.

Two jobs, both about not restating things:

**One palette.** `SILICON`, `NATIVE` and `METHOD_COLORS` were defined in four
active scripts and six archived ones. They are imported here from the module that
owns them -- `scripts/archive/plot_stress_matrix_methods.py`, which set the
conventions the study's 496 per-case figures already follow -- and re-exported so
active code has an entry point that is not an archived path. The values are not
copied; there is still one definition.

**Editable figures without touching plotting code.** `tools/figure_editor` is a
CSV-backed editor: it stores every style choice in a JSON recipe next to the data,
reopens it in a GUI, and renders headlessly to PNG/SVG/PDF. Study runners already
write aligned per-case CSVs, so a recipe can be emitted for each one
automatically. That turns every generated figure into something restylable for a
slide -- and vector-exportable -- without editing or re-running a script.

`recipe_for_case` exists because the editor's own `recipe_for_csv` takes the first
few columns alphabetically, which on a per-case waveform CSV mixes Ku, Kd and pad
onto one axes. This selects one field, orders the sources the way the study plots
them, and applies the palette.

    from figures import ORDER, recipe_for_case, SILICON, NATIVE, METHOD_COLORS
"""
from __future__ import annotations

import csv as _csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "scripts" / "archive", ROOT / "tools",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import plot_stress_matrix_methods as _canon  # noqa: E402
from figure_editor import figure_document as fd  # noqa: E402

__all__ = [
    "SILICON", "NATIVE", "NATIVE1", "METHOD_COLORS", "ORDER",
    "FIELD_LABELS", "recipe_for_case", "case_title",
]

SILICON = _canon.SILICON
NATIVE = _canon.NATIVE
METHOD_COLORS = _canon.METHOD_COLORS
# The base matrix had no second native mode to draw; this is the only addition.
NATIVE1 = "#7FB3D5"

# Draw order and weight, silicon heaviest and on top. Keys are the source
# prefixes used in per-case waveform CSVs (`<source>_pad`, `<source>_ku`, ...).
ORDER: dict[str, tuple[str, float, int]] = {
    "silicon": (SILICON, 2.8, 6),
    "native": (NATIVE, 1.7, 5),
    "native_rwf1": (NATIVE1, 1.4, 4),
    "gate_state": (METHOD_COLORS.get("gate_state", "#C02626"), 1.4, 3),
    "delay_cmd": (METHOD_COLORS.get("delay_cmd", "#1B7F5A"), 1.4, 3),
    "legacy": (METHOD_COLORS.get("legacy", "#8A8A8A"), 1.3, 2),
}

FIELD_LABELS = {"pad": "Pad voltage (V)", "ku": "Ku", "kd": "Kd"}


def case_title(case_dir: Path, field: str) -> str:
    """`inv_base8 / depth90_w130ps` -> "inv_base8 · 90% of full swing · 130 ps".

    The number after `depth` is a percentage of the transistor's settled full
    swing, not a time -- an earlier version rendered it as "100 ns", which is both
    wrong and the exact confusion the depth/width distinction exists to avoid.
    """
    variant = case_dir.parent.name
    m = re.match(r"depth(\d+)_w(\d+)ps$", case_dir.name)
    if not m:
        return f"{variant} · {case_dir.name} — {FIELD_LABELS.get(field, field)}"
    return (f"{variant} · {m.group(1)}% of full swing · {m.group(2)} ps pulse"
            f" — {FIELD_LABELS.get(field, field)}")


def recipe_for_case(csv_path: Path, field: str, *, title: str | None = None,
                    x_column: str = "time_ns") -> fd.FigureRecipe:
    """A figure-editor recipe for one field of a per-case waveform CSV.

    `field` is "pad", "ku" or "kd". Only columns for that field are included, in
    the study's draw order, so the recipe opens as the figure a reader expects
    rather than every column at once. Columns absent from the CSV are skipped
    rather than erroring -- a build that failed to run is a normal outcome here.
    """
    csv_path = Path(csv_path)
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(_csv.reader(handle))
    series = []
    for source, (colour, lw, z) in ORDER.items():
        column = f"{source}_{field}"
        if column not in header:
            continue
        series.append(fd.SeriesStyle(
            column=column, label=source.replace("_", " "), color=colour,
            linewidth=lw, zorder=z))
    if not series:
        raise ValueError(f"{csv_path}: no '{field}' columns among {header}")
    style = fd.FigureStyle(
        title=title or case_title(csv_path.parent, field),
        xlabel="Time (ns)", ylabel=FIELD_LABELS.get(field, field),
        legend_columns=3, width_in=11.0, height_in=4.6 if field == "pad" else 4.0,
        dpi=160)
    return fd.FigureRecipe(csv_path=str(csv_path), x_column=x_column,
                           series=series, figure=style)
