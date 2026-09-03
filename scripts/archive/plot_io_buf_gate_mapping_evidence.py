from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_io_buf_two_state_gate_model as study  # noqa: E402


OUTPUT_DIR = (
    ROOT
    / "results"
    / "io_buf_two_state_gate_model_2026-06-30"
    / "gate_mapping_evidence"
)

BLACK = "#111111"
RED = "#d62728"
BLUE = "#1f77b4"
ORANGE = "#e67e22"
PURPLE = "#6f42a1"
GRAY = "#777777"
GRID = "#d9dde3"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_time_reconstruction(data: dict[str, np.ndarray], output: Path) -> None:
    specs = [
        ("tr", "gup_rise", "ku_rise", "Pullup ON: Ku_rise(t)", "GUP"),
        ("tf", "gup_fall", "ku_fall", "Pullup OFF: Ku_fall(t)", "GUP"),
        ("tr", "gdn_rise", "kd_rise", "Pulldown OFF: Kd_fall(t)", "GDN"),
        ("tf", "gdn_fall", "kd_fall", "Pulldown ON: Kd_rise(t)", "GDN"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14.0, 8.8), constrained_layout=True)
    for ax, (time_key, state_key, prefix, title, state_name) in zip(axes.flat, specs):
        time_ns = data[time_key]
        original = data[f"{prefix}_orig"]
        core = data[f"{prefix}_directional"]
        final = data[f"{prefix}_directional_residual"]
        state = data[state_key]
        marker_step = max(1, len(time_ns) // 28)

        ax.plot(time_ns, original, color=BLACK, lw=3.2, label="original IBIS-derived K(t)", zorder=2)
        if prefix.startswith("kd"):
            ax.plot(
                time_ns,
                core,
                color=ORANGE,
                lw=1.8,
                ls="--",
                label="core directional Kd(GDN)",
                zorder=3,
            )
            model_label = "final Kd(GDN) + residual"
        else:
            model_label = "new directional Ku(GUP)"
        ax.plot(
            time_ns,
            final,
            color=RED,
            lw=1.7,
            marker="o",
            ms=3.0,
            markevery=marker_step,
            markerfacecolor="white",
            markeredgewidth=0.9,
            label=model_label,
            zorder=4,
        )
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Original coefficient-table time (ns)")
        ax.set_ylabel(prefix[:2].capitalize())
        ax.grid(True, color=GRID, alpha=0.85)
        ax.axhline(0.0, color="#9aa0a6", lw=0.8)

        state_ax = ax.twinx()
        state_ax.plot(time_ns, state, color=PURPLE, lw=1.2, alpha=0.38, label=state_name)
        state_ax.set_ylabel(state_name, color=PURPLE)
        state_ax.set_ylim(-0.05, 1.05)
        state_ax.tick_params(axis="y", colors=PURPLE)

        left_lines, left_labels = ax.get_legend_handles_labels()
        state_lines, state_labels = state_ax.get_legend_handles_labels()
        ax.legend(left_lines + state_lines, left_labels + state_labels, loc="best", frameon=True, fontsize=8.8)

    fig.suptitle(
        "io_buf: original Ku(t)/Kd(t) tables vs gate-state reconstruction",
        fontsize=16,
        fontweight="bold",
    )
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_transfer_maps(
    data: dict[str, np.ndarray], dfit: dict[str, object], output: Path
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.8), constrained_layout=True)

    ax = axes[0]
    ax.scatter(
        data["gup_rise"],
        data["ku_rise_orig"],
        s=14,
        color=BLACK,
        alpha=0.40,
        label="original Ku_rise samples paired with GUP",
    )
    ax.scatter(
        data["gup_fall"],
        data["ku_fall_orig"],
        s=17,
        marker="x",
        color=GRAY,
        alpha=0.55,
        label="original Ku_fall samples paired with GUP",
    )
    ax.plot(dfit["ku_on_map_x"], dfit["ku_on_map_y"], color=RED, lw=2.5, label="fitted Ku_on(GUP)")
    ax.plot(dfit["ku_off_map_x"], dfit["ku_off_map_y"], color=BLUE, lw=2.5, label="fitted Ku_off(GUP)")
    ax.set_title("Pullup directional transfer maps", loc="left", fontweight="bold")
    ax.set_xlabel("Hidden gate state GUP")
    ax.set_ylabel("Effective pullup coefficient Ku")
    ax.set_xlim(-0.02, 1.02)
    ax.grid(True, color=GRID, alpha=0.85)
    ax.legend(frameon=True, fontsize=9)
    ax = axes[1]
    ax.scatter(
        data["gdn_rise"],
        data["kd_rise_orig"],
        s=14,
        color=BLACK,
        alpha=0.40,
        label="original Kd_fall samples paired with GDN",
    )
    ax.scatter(
        data["gdn_fall"],
        data["kd_fall_orig"],
        s=17,
        marker="x",
        color=GRAY,
        alpha=0.55,
        label="original Kd_rise samples paired with GDN",
    )
    ax.plot(dfit["kd_off_map_x"], dfit["kd_off_map_y"], color=ORANGE, lw=2.5, label="fitted Kd_off(GDN)")
    ax.plot(dfit["kd_on_map_x"], dfit["kd_on_map_y"], color=BLUE, lw=2.5, label="fitted Kd_on(GDN)")
    ax.set_title("Pulldown directional transfer maps", loc="left", fontweight="bold")
    ax.set_xlabel("Hidden gate state GDN")
    ax.set_ylabel("Core effective pulldown coefficient Kd")
    ax.set_xlim(-0.02, 1.02)
    ax.grid(True, color=GRID, alpha=0.85)
    ax.legend(frameon=True, fontsize=9)
    ax.text(
        0.98,
        0.03,
        "Core Kd(GDN) maps shown here; final Kd also adds the dynamic residual.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.8,
        color=GRAY,
        bbox={"facecolor": "white", "edgecolor": "#c8ccd2", "alpha": 0.9},
    )

    fig.suptitle(
        "io_buf: how original table samples become Ku(GUP) and Kd(GDN) PWL maps",
        fontsize=16,
        fontweight="bold",
    )
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_numeric_rows(data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    specs = [
        ("pu_on", "tr", "gup_rise", "ku_rise"),
        ("pu_off", "tf", "gup_fall", "ku_fall"),
        ("pd_off", "tr", "gdn_rise", "kd_rise"),
        ("pd_on", "tf", "gdn_fall", "kd_fall"),
    ]
    rows: list[dict[str, object]] = []
    for process, time_key, state_key, prefix in specs:
        original = data[f"{prefix}_orig"]
        core = data[f"{prefix}_directional"]
        final = data[f"{prefix}_directional_residual"]
        for index, time_ns in enumerate(data[time_key]):
            rows.append(
                {
                    "process": process,
                    "table_time_ns": float(time_ns),
                    "gate_state": float(data[state_key][index]),
                    "original_coefficient": float(original[index]),
                    "core_directional_map_coefficient": float(core[index]),
                    "final_residual_corrected_coefficient": float(final[index]),
                    "core_minus_original": float(core[index] - original[index]),
                    "final_minus_original": float(final[index] - original[index]),
                }
            )
    return rows


def build_map_rows(dfit: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    specs = [
        ("ku_on", "GUP", "Ku", "ku_on_map_x", "ku_on_map_y"),
        ("ku_off", "GUP", "Ku", "ku_off_map_x", "ku_off_map_y"),
        ("kd_off", "GDN", "Kd", "kd_off_map_x", "kd_off_map_y"),
        ("kd_on", "GDN", "Kd", "kd_on_map_x", "kd_on_map_y"),
    ]
    for mapping, state_name, coefficient_name, x_key, y_key in specs:
        for state, coefficient in zip(dfit[x_key], dfit[y_key]):
            rows.append(
                {
                    "mapping": mapping,
                    "state_name": state_name,
                    "coefficient_name": coefficient_name,
                    "gate_state": float(state),
                    "mapped_coefficient": float(coefficient),
                }
            )
    return rows


def write_readme(output_dir: Path) -> None:
    text = """# io_buf Gate-State Mapping Evidence

Cached/table-derived evidence only; no HSPICE or ngspice simulation was run.

Files:

- `01_original_tables_vs_gate_mapped_time.png`: original complete-edge Ku(t)/Kd(t) tables versus coefficients reconstructed from GUP(t)/GDN(t). Purple traces show the hidden state. For Kd, both the core directional map and final residual-corrected coefficient are shown.
- `02_directional_gate_transfer_maps.png`: the actual directional PWL maps. Black/gray points are original table samples paired with reconstructed gate state; colored curves are the fitted maps written to SPICE.
- `gate_mapping_time_data.csv`: numerical time, gate state, original coefficient, core mapped coefficient, and residual-corrected coefficient.
- `gate_transfer_map_points.csv`: exact PWL state/coefficient points for the four directional maps.

Interpretation:

1. Delay and tau reconstruct continuous GUP/GDN trajectories from complete-edge tables.
2. Original coefficient samples are paired with those state values.
3. Separate on/off maps are required because the same state can imply different coefficient strength by direction.
4. Ku uses the directional map directly. The best current Kd adds a dynamic residual to the core Kd(GDN) map.
"""
    (output_dir / "README.md").write_text(text, encoding="ascii")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ibis_path = study.DEFAULT_IBIS
    kr, kf, fit = study.load_io_buf_k_tables(ibis_path)
    _, data = study.reconstruction_rows_and_data(kr, kf, fit)
    dfit = study.subcircuit.two_state_directional_gate_fit(kr, kf)

    plot_time_reconstruction(
        data, OUTPUT_DIR / "01_original_tables_vs_gate_mapped_time.png"
    )
    plot_transfer_maps(
        data, dfit, OUTPUT_DIR / "02_directional_gate_transfer_maps.png"
    )
    write_csv(OUTPUT_DIR / "gate_mapping_time_data.csv", build_numeric_rows(data))
    write_csv(OUTPUT_DIR / "gate_transfer_map_points.csv", build_map_rows(dfit))
    write_readme(OUTPUT_DIR)
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
