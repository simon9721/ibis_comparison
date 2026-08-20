from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np


@dataclass
class SeriesStyle:
    column: str
    label: str
    color: str = "#1769aa"
    linewidth: float = 2.0
    linestyle: str = "-"
    marker: str = ""
    markersize: float = 4.0
    alpha: float = 1.0
    zorder: float = 2.0
    visible: bool = True


@dataclass
class FigureStyle:
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    title_size: float = 16.0
    label_size: float = 12.0
    tick_size: float = 10.0
    legend_size: float = 10.0
    legend_location: str = "best"
    legend_columns: int = 1
    show_legend: bool = True
    show_grid: bool = True
    grid_alpha: float = 0.45
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None
    width_in: float = 11.0
    height_in: float = 6.5
    dpi: int = 160
    background: str = "#ffffff"
    transparent: bool = False
    font_family: str = "DejaVu Sans"
    x_scale: str = "linear"
    y_scale: str = "linear"


@dataclass
class FigureRecipe:
    csv_path: str = ""
    x_column: str = ""
    series: list[SeriesStyle] = field(default_factory=list)
    figure: FigureStyle = field(default_factory=FigureStyle)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        csv_path = Path(self.csv_path)
        if csv_path.is_absolute():
            try:
                payload["csv_path"] = os.path.relpath(csv_path, path.parent)
            except (ValueError, OSError):
                payload["csv_path"] = str(csv_path)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "FigureRecipe":
        payload = json.loads(path.read_text(encoding="utf-8"))
        csv_path = Path(payload.get("csv_path", ""))
        if csv_path and not csv_path.is_absolute():
            csv_path = (path.parent / csv_path).resolve()
        return cls(
            csv_path=str(csv_path),
            x_column=payload.get("x_column", ""),
            series=[SeriesStyle(**item) for item in payload.get("series", [])],
            figure=FigureStyle(**payload.get("figure", {})),
        )


def read_numeric_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No data rows in {path}")
    result: dict[str, np.ndarray] = {}
    for column in rows[0]:
        values: list[float] = []
        numeric = True
        for row in rows:
            text = (row.get(column) or "").strip()
            if not text:
                values.append(float("nan"))
                continue
            try:
                values.append(float(text))
            except ValueError:
                numeric = False
                break
        if numeric:
            result[column] = np.asarray(values, dtype=float)
    if not result:
        raise ValueError(f"No numeric columns in {path}")
    return result


def default_x_column(columns: list[str]) -> str:
    priorities = ("time_ns", "time_s", "time", "frequency_hz", "frequency")
    lookup = {column.lower(): column for column in columns}
    for name in priorities:
        if name in lookup:
            return lookup[name]
    return columns[0]


def default_colors() -> list[str]:
    return [
        "#111111",
        "#1769aa",
        "#d62728",
        "#7b2cbf",
        "#008b6e",
        "#d97706",
        "#17becf",
        "#e377c2",
        "#8c564b",
        "#7f7f7f",
    ]


def recipe_for_csv(path: Path) -> FigureRecipe:
    data = read_numeric_csv(path)
    columns = list(data)
    x_column = default_x_column(columns)
    colors = default_colors()
    # Large study CSVs often contain dozens of diagnostic nodes. Start with a
    # readable subset; every remaining numeric column is available in the GUI.
    series = [
        SeriesStyle(column=column, label=column, color=colors[index % len(colors)])
        for index, column in enumerate(
            [column for column in columns if column != x_column][:8]
        )
    ]
    return FigureRecipe(
        csv_path=str(path.resolve()),
        x_column=x_column,
        series=series,
        figure=FigureStyle(xlabel=x_column),
    )


def build_figure(
    recipe: FigureRecipe,
    *,
    backend: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    if backend:
        matplotlib.use(backend, force=True)
    data = read_numeric_csv(Path(recipe.csv_path))
    if recipe.x_column not in data:
        raise KeyError(f"X column {recipe.x_column!r} is not in {recipe.csv_path}")
    style = recipe.figure
    fig, ax = plt.subplots(figsize=(style.width_in, style.height_in))
    fig.patch.set_facecolor(style.background)
    ax.set_facecolor(style.background)
    x = data[recipe.x_column]
    for item in recipe.series:
        if not item.visible or item.column not in data:
            continue
        valid = np.isfinite(x) & np.isfinite(data[item.column])
        ax.plot(
            x[valid],
            data[item.column][valid],
            label=item.label,
            color=item.color,
            linewidth=item.linewidth,
            linestyle=item.linestyle,
            marker=item.marker or None,
            markersize=item.markersize,
            alpha=item.alpha,
            zorder=item.zorder,
        )
    ax.set_title(style.title, fontsize=style.title_size, fontfamily=style.font_family)
    ax.set_xlabel(style.xlabel, fontsize=style.label_size, fontfamily=style.font_family)
    ax.set_ylabel(style.ylabel, fontsize=style.label_size, fontfamily=style.font_family)
    ax.set_xscale(style.x_scale)
    ax.set_yscale(style.y_scale)
    ax.tick_params(labelsize=style.tick_size)
    for tick in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        tick.set_fontfamily(style.font_family)
    ax.grid(style.show_grid, alpha=style.grid_alpha)
    if style.x_min is not None or style.x_max is not None:
        ax.set_xlim(left=style.x_min, right=style.x_max)
    if style.y_min is not None or style.y_max is not None:
        ax.set_ylim(bottom=style.y_min, top=style.y_max)
    if style.show_legend and any(item.visible for item in recipe.series):
        ax.legend(
            loc=style.legend_location,
            fontsize=style.legend_size,
            frameon=False,
            ncol=style.legend_columns,
            prop={"family": style.font_family, "size": style.legend_size},
        )
    fig.tight_layout()
    return fig, ax


def render_recipe(recipe: FigureRecipe, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, _ = build_figure(recipe, backend="Agg")
    figure.savefig(
        output,
        dpi=recipe.figure.dpi,
        facecolor=recipe.figure.background,
        transparent=recipe.figure.transparent,
    )
    plt.close(figure)
    return output


def update_dataclass(instance: Any, values: dict[str, Any]) -> None:
    for key, value in values.items():
        if hasattr(instance, key):
            setattr(instance, key, value)
