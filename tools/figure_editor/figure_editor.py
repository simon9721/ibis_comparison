from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.figure_editor.figure_document import (  # type: ignore
        FigureRecipe,
        SeriesStyle,
        build_figure,
        default_colors,
        read_numeric_csv,
        recipe_for_csv,
        render_recipe,
    )
else:
    from .figure_document import (
        FigureRecipe,
        SeriesStyle,
        build_figure,
        default_colors,
        read_numeric_csv,
        recipe_for_csv,
        render_recipe,
    )


def optional_float(text: str) -> float | None:
    value = text.strip()
    return None if value == "" else float(value)


def launch_gui(initial: Path | None = None) -> None:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, messagebox, ttk

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

    class FigureEditor:
        def __init__(self, root: tk.Tk) -> None:
            self.root = root
            self.root.title("Data Figure Editor")
            self.root.geometry("1500x900")
            self.recipe = FigureRecipe()
            self.data: dict[str, object] = {}
            self.figure = None
            self.canvas = None
            self.toolbar = None
            self.selected_series_index: int | None = None
            self._build()
            if initial:
                self.open_path(initial)

        def _build(self) -> None:
            shell = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
            shell.pack(fill=tk.BOTH, expand=True)
            controls = ttk.Frame(shell, width=430, padding=8)
            preview = ttk.Frame(shell, padding=4)
            shell.add(controls, weight=0)
            shell.add(preview, weight=1)
            self.preview = preview

            top = ttk.Frame(controls)
            top.pack(fill=tk.X, pady=(0, 6))
            ttk.Button(top, text="Open CSV", command=self.open_csv).pack(side=tk.LEFT)
            ttk.Button(top, text="Load Recipe", command=self.load_recipe).pack(side=tk.LEFT, padx=4)
            ttk.Button(top, text="Save Recipe", command=self.save_recipe).pack(side=tk.LEFT)
            ttk.Button(top, text="Export", command=self.export).pack(side=tk.RIGHT)

            self.path_var = tk.StringVar(value="No data loaded")
            ttk.Label(controls, textvariable=self.path_var, wraplength=410).pack(fill=tk.X, pady=(0, 6))

            notebook = ttk.Notebook(controls)
            notebook.pack(fill=tk.BOTH, expand=True)
            data_tab = ttk.Frame(notebook, padding=8)
            series_tab = ttk.Frame(notebook, padding=8)
            figure_tab = ttk.Frame(notebook, padding=8)
            notebook.add(data_tab, text="Data")
            notebook.add(series_tab, text="Series")
            notebook.add(figure_tab, text="Figure")

            ttk.Label(data_tab, text="X column").pack(anchor=tk.W)
            self.x_var = tk.StringVar()
            self.x_combo = ttk.Combobox(data_tab, textvariable=self.x_var, state="readonly")
            self.x_combo.pack(fill=tk.X, pady=(0, 8))
            self.x_combo.bind("<<ComboboxSelected>>", lambda _event: self.apply())

            ttk.Label(data_tab, text="Available numeric columns").pack(anchor=tk.W)
            self.available = tk.Listbox(data_tab, selectmode=tk.EXTENDED, height=12)
            self.available.pack(fill=tk.BOTH, expand=True)
            ttk.Button(data_tab, text="Add selected traces", command=self.add_selected).pack(fill=tk.X, pady=5)

            ttk.Label(data_tab, text="Plotted traces").pack(anchor=tk.W)
            self.tree = ttk.Treeview(data_tab, columns=("label", "color", "visible"), show="headings", height=10)
            self.tree.heading("label", text="Label")
            self.tree.heading("color", text="Color")
            self.tree.heading("visible", text="Visible")
            self.tree.column("label", width=220)
            self.tree.column("color", width=75)
            self.tree.column("visible", width=55)
            self.tree.pack(fill=tk.BOTH, expand=True)
            self.tree.bind("<<TreeviewSelect>>", self.select_series)
            order = ttk.Frame(data_tab)
            order.pack(fill=tk.X, pady=5)
            ttk.Button(order, text="Up", command=lambda: self.move_series(-1)).pack(side=tk.LEFT)
            ttk.Button(order, text="Down", command=lambda: self.move_series(1)).pack(side=tk.LEFT, padx=4)
            ttk.Button(order, text="Remove", command=self.remove_series).pack(side=tk.RIGHT)

            self.series_vars: dict[str, tk.Variable] = {
                "label": tk.StringVar(),
                "color": tk.StringVar(value="#1769aa"),
                "linewidth": tk.StringVar(value="2.0"),
                "linestyle": tk.StringVar(value="-"),
                "marker": tk.StringVar(value=""),
                "markersize": tk.StringVar(value="4.0"),
                "alpha": tk.StringVar(value="1.0"),
                "zorder": tk.StringVar(value="2.0"),
                "visible": tk.BooleanVar(value=True),
            }
            self._entry(series_tab, "Display label", self.series_vars["label"])
            color_row = ttk.Frame(series_tab)
            color_row.pack(fill=tk.X, pady=3)
            ttk.Label(color_row, text="Color", width=17).pack(side=tk.LEFT)
            ttk.Entry(color_row, textvariable=self.series_vars["color"]).pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(color_row, text="Choose", command=self.choose_color).pack(side=tk.RIGHT, padx=(4, 0))
            self._entry(series_tab, "Line width", self.series_vars["linewidth"])
            self._combo(series_tab, "Line style", self.series_vars["linestyle"], ["-", "--", "-.", ":", ""])
            self._combo(series_tab, "Marker", self.series_vars["marker"], ["", "o", "s", "^", "D", "x", "+", "."])
            self._entry(series_tab, "Marker size", self.series_vars["markersize"])
            self._entry(series_tab, "Alpha", self.series_vars["alpha"])
            self._entry(series_tab, "Layer (z-order)", self.series_vars["zorder"])
            ttk.Checkbutton(series_tab, text="Visible", variable=self.series_vars["visible"]).pack(anchor=tk.W, pady=5)
            ttk.Button(series_tab, text="Apply trace style", command=self.apply_series).pack(fill=tk.X, pady=8)

            self.figure_vars: dict[str, tk.Variable] = {
                "title": tk.StringVar(),
                "xlabel": tk.StringVar(),
                "ylabel": tk.StringVar(),
                "title_size": tk.StringVar(value="16"),
                "label_size": tk.StringVar(value="12"),
                "tick_size": tk.StringVar(value="10"),
                "legend_size": tk.StringVar(value="10"),
                "legend_location": tk.StringVar(value="best"),
                "legend_columns": tk.StringVar(value="1"),
                "show_legend": tk.BooleanVar(value=True),
                "show_grid": tk.BooleanVar(value=True),
                "grid_alpha": tk.StringVar(value="0.45"),
                "x_min": tk.StringVar(),
                "x_max": tk.StringVar(),
                "y_min": tk.StringVar(),
                "y_max": tk.StringVar(),
                "width_in": tk.StringVar(value="11"),
                "height_in": tk.StringVar(value="6.5"),
                "dpi": tk.StringVar(value="160"),
                "background": tk.StringVar(value="#ffffff"),
                "transparent": tk.BooleanVar(value=False),
                "font_family": tk.StringVar(value="DejaVu Sans"),
                "x_scale": tk.StringVar(value="linear"),
                "y_scale": tk.StringVar(value="linear"),
            }
            for key, label in [("title", "Title"), ("xlabel", "X label"), ("ylabel", "Y label")]:
                self._entry(figure_tab, label, self.figure_vars[key])
            for key, label in [
                ("title_size", "Title font"),
                ("label_size", "Axis-label font"),
                ("tick_size", "Tick font"),
                ("legend_size", "Legend font"),
            ]:
                self._entry(figure_tab, label, self.figure_vars[key])
            self._combo(
                figure_tab,
                "Legend position",
                self.figure_vars["legend_location"],
                ["best", "upper right", "upper left", "lower right", "lower left", "center right", "center left"],
            )
            self._entry(figure_tab, "Legend columns", self.figure_vars["legend_columns"])
            self._entry(figure_tab, "Font family", self.figure_vars["font_family"])
            self._combo(figure_tab, "X scale", self.figure_vars["x_scale"], ["linear", "log", "symlog"])
            self._combo(figure_tab, "Y scale", self.figure_vars["y_scale"], ["linear", "log", "symlog"])
            flags = ttk.Frame(figure_tab)
            flags.pack(fill=tk.X, pady=4)
            ttk.Checkbutton(flags, text="Legend", variable=self.figure_vars["show_legend"]).pack(side=tk.LEFT)
            ttk.Checkbutton(flags, text="Grid", variable=self.figure_vars["show_grid"]).pack(side=tk.LEFT, padx=12)
            ttk.Checkbutton(flags, text="Transparent", variable=self.figure_vars["transparent"]).pack(side=tk.LEFT)
            self._entry(figure_tab, "Grid alpha", self.figure_vars["grid_alpha"])
            limits = ttk.LabelFrame(figure_tab, text="Axis limits (blank = auto)", padding=5)
            limits.pack(fill=tk.X, pady=5)
            for key, label in [("x_min", "X min"), ("x_max", "X max"), ("y_min", "Y min"), ("y_max", "Y max")]:
                self._entry(limits, label, self.figure_vars[key])
            size = ttk.LabelFrame(figure_tab, text="Canvas and export", padding=5)
            size.pack(fill=tk.X, pady=5)
            for key, label in [("width_in", "Width (in)"), ("height_in", "Height (in)"), ("dpi", "DPI"), ("background", "Background")]:
                self._entry(size, label, self.figure_vars[key])
            ttk.Button(figure_tab, text="Apply figure settings", command=self.apply_figure).pack(fill=tk.X, pady=8)

        @staticmethod
        def _entry(parent: ttk.Frame, label: str, variable: tk.Variable) -> None:
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=17).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=variable).pack(side=tk.LEFT, fill=tk.X, expand=True)

        @staticmethod
        def _combo(parent: ttk.Frame, label: str, variable: tk.Variable, values: list[str]) -> None:
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=17).pack(side=tk.LEFT)
            ttk.Combobox(row, textvariable=variable, values=values, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)

        def open_path(self, path: Path) -> None:
            try:
                if path.suffix.lower() == ".json":
                    self.recipe = FigureRecipe.load(path)
                else:
                    self.recipe = recipe_for_csv(path)
                self.data = read_numeric_csv(Path(self.recipe.csv_path))
                self.refresh_controls()
                self.apply()
            except Exception as exc:
                messagebox.showerror("Open failed", str(exc))

        def open_csv(self) -> None:
            value = filedialog.askopenfilename(filetypes=[("CSV data", "*.csv"), ("All files", "*.*")])
            if value:
                self.open_path(Path(value))

        def load_recipe(self) -> None:
            value = filedialog.askopenfilename(filetypes=[("Figure recipe", "*.json")])
            if value:
                self.open_path(Path(value))

        def save_recipe(self) -> None:
            self.sync_recipe()
            value = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Figure recipe", "*.json")])
            if value:
                self.recipe.save(Path(value))

        def export(self) -> None:
            self.sync_recipe()
            value = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG image", "*.png"), ("SVG vector", "*.svg"), ("PDF document", "*.pdf")],
            )
            if value:
                try:
                    render_recipe(self.recipe, Path(value))
                except Exception as exc:
                    messagebox.showerror("Export failed", str(exc))

        def refresh_controls(self) -> None:
            self.path_var.set(self.recipe.csv_path)
            columns = list(self.data)
            self.x_combo["values"] = columns
            self.x_var.set(self.recipe.x_column)
            self.available.delete(0, tk.END)
            for column in columns:
                if column != self.recipe.x_column:
                    self.available.insert(tk.END, column)
            self.refresh_tree()
            for key, variable in self.figure_vars.items():
                value = getattr(self.recipe.figure, key)
                variable.set("" if value is None else value)

        def refresh_tree(self) -> None:
            for item in self.tree.get_children():
                self.tree.delete(item)
            for index, item in enumerate(self.recipe.series):
                self.tree.insert("", tk.END, iid=str(index), values=(item.label, item.color, "yes" if item.visible else "no"))

        def add_selected(self) -> None:
            colors = default_colors()
            existing = {item.column for item in self.recipe.series}
            for list_index in self.available.curselection():
                column = self.available.get(list_index)
                if column not in existing:
                    self.recipe.series.append(
                        SeriesStyle(
                            column=column,
                            label=column,
                            color=colors[len(self.recipe.series) % len(colors)],
                        )
                    )
            self.refresh_tree()
            self.apply()

        def select_series(self, _event: object = None) -> None:
            selected = self.tree.selection()
            if not selected:
                return
            index = int(selected[0])
            self.selected_series_index = index
            item = self.recipe.series[index]
            for key, variable in self.series_vars.items():
                variable.set(getattr(item, key))

        def apply_series(self) -> None:
            if self.selected_series_index is None:
                return
            try:
                item = self.recipe.series[self.selected_series_index]
                item.label = str(self.series_vars["label"].get())
                item.color = str(self.series_vars["color"].get())
                item.linewidth = float(self.series_vars["linewidth"].get())
                item.linestyle = str(self.series_vars["linestyle"].get())
                item.marker = str(self.series_vars["marker"].get())
                item.markersize = float(self.series_vars["markersize"].get())
                item.alpha = float(self.series_vars["alpha"].get())
                item.zorder = float(self.series_vars["zorder"].get())
                item.visible = bool(self.series_vars["visible"].get())
                self.refresh_tree()
                self.apply()
            except Exception as exc:
                messagebox.showerror("Invalid trace style", str(exc))

        def choose_color(self) -> None:
            result = colorchooser.askcolor(color=str(self.series_vars["color"].get()))
            if result[1]:
                self.series_vars["color"].set(result[1])

        def move_series(self, delta: int) -> None:
            if self.selected_series_index is None:
                return
            old = self.selected_series_index
            new = max(0, min(len(self.recipe.series) - 1, old + delta))
            if old == new:
                return
            item = self.recipe.series.pop(old)
            self.recipe.series.insert(new, item)
            self.selected_series_index = new
            self.refresh_tree()
            self.tree.selection_set(str(new))
            self.apply()

        def remove_series(self) -> None:
            if self.selected_series_index is None:
                return
            self.recipe.series.pop(self.selected_series_index)
            self.selected_series_index = None
            self.refresh_tree()
            self.apply()

        def apply_figure(self) -> None:
            try:
                self.collect_figure_values()
                self.apply()
            except Exception as exc:
                messagebox.showerror("Invalid figure setting", str(exc))

        def sync_recipe(self) -> None:
            self.recipe.x_column = self.x_var.get()
            self.collect_figure_values()

        def collect_figure_values(self) -> None:
            style = self.recipe.figure
            style.title = str(self.figure_vars["title"].get())
            style.xlabel = str(self.figure_vars["xlabel"].get())
            style.ylabel = str(self.figure_vars["ylabel"].get())
            for key in ["title_size", "label_size", "tick_size", "legend_size", "grid_alpha", "width_in", "height_in"]:
                setattr(style, key, float(self.figure_vars[key].get()))
            for key in ["x_min", "x_max", "y_min", "y_max"]:
                setattr(style, key, optional_float(str(self.figure_vars[key].get())))
            style.dpi = int(float(self.figure_vars["dpi"].get()))
            style.legend_columns = int(float(self.figure_vars["legend_columns"].get()))
            style.legend_location = str(self.figure_vars["legend_location"].get())
            style.show_legend = bool(self.figure_vars["show_legend"].get())
            style.show_grid = bool(self.figure_vars["show_grid"].get())
            style.background = str(self.figure_vars["background"].get())
            style.transparent = bool(self.figure_vars["transparent"].get())
            style.font_family = str(self.figure_vars["font_family"].get())
            style.x_scale = str(self.figure_vars["x_scale"].get())
            style.y_scale = str(self.figure_vars["y_scale"].get())

        def apply(self) -> None:
            if not self.recipe.csv_path:
                return
            self.recipe.x_column = self.x_var.get() or self.recipe.x_column
            if self.canvas:
                self.canvas.get_tk_widget().destroy()
            if self.toolbar:
                self.toolbar.destroy()
            if self.figure:
                import matplotlib.pyplot as plt
                plt.close(self.figure)
            self.figure, _ = build_figure(self.recipe)
            self.canvas = FigureCanvasTkAgg(self.figure, master=self.preview)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.preview, pack_toolbar=False)
            self.toolbar.update()
            self.toolbar.pack(fill=tk.X)

    root = tk.Tk()
    FigureEditor(root)
    root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edit data-backed Matplotlib figures.")
    parser.add_argument("input", nargs="?", type=Path, help="CSV data or JSON recipe")
    parser.add_argument("--render", type=Path, help="Headless export path; input must be a recipe")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.render:
        if not args.input or args.input.suffix.lower() != ".json":
            raise SystemExit("--render requires a JSON recipe input")
        render_recipe(FigureRecipe.load(args.input), args.render)
        return 0
    launch_gui(args.input)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
