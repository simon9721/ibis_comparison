#!/usr/bin/env python3
"""Build a cached-data audit of Ku/Kd excursions versus bounded gate states."""

from __future__ import annotations

import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

import matplotlib.pyplot as plt
import numpy as np


SOURCE_DIR = ROOT / "results" / "three_buffer_gup_gdn_waveforms_2026-08-04" / "source_data"
OUT_DIR = ROOT / "results" / "three_buffer_kukd_excursion_analysis_2026-08-04"

DEVICES = ("io_buf", "inv_chain", "ex2")
LABELS = {"io_buf": "io_buf", "inv_chain": "inv_chain", "ex2": "ex2"}


def read_numeric_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        name: np.asarray([float(row[name]) for row in rows], dtype=float)
        for name in rows[0]
    }


def finite_range(values: np.ndarray) -> tuple[float, float]:
    values = values[np.isfinite(values)]
    return float(np.min(values)), float(np.max(values))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plot_dir = OUT_DIR / "plots"
    plot_dir.mkdir(exist_ok=True)

    summaries: list[dict[str, object]] = []
    fig, axes = plt.subplots(2, 3, figsize=(18, 8.6), sharex="col")

    for column, device in enumerate(DEVICES):
        data = read_numeric_csv(SOURCE_DIR / f"{device}_edge_50ps_long_control.csv")
        t = data["relative_time_ns"]
        # Keep both the rising and falling transitions of the 10 ns control pulse.
        window = (t >= -0.25) & (t <= 14.0)
        t = t[window]

        ax_coeff = axes[0, column]
        ax_state = axes[1, column]
        ax_coeff.axhspan(0.0, 1.0, color="#e8f5e9", alpha=0.55, zorder=0)
        ax_state.axhspan(0.0, 1.0, color="#e8f5e9", alpha=0.55, zorder=0)
        for axis in (ax_coeff, ax_state):
            axis.axvline(0.0, color="#777777", linewidth=1.0, linestyle=":")
            axis.axvline(10.05, color="#777777", linewidth=1.0, linestyle=":")

        coeff_traces = (
            ("native Ku", "hspice_ibis_ku", "#111111", 2.5),
            ("native Kd", "hspice_ibis_kd", "#666666", 2.5),
            ("gate-model Ku", "gate_state_ku", "#d62728", 1.8),
            ("gate-model Kd", "gate_state_kd", "#9467bd", 1.8),
        )
        for label, key, color, width in coeff_traces:
            values = data[key][window]
            ax_coeff.plot(t, values, color=color, linewidth=width, label=label)
            minimum, maximum = finite_range(values)
            summaries.append(
                {
                    "device": device,
                    "source": "hspice_native_ibis" if key.startswith("hspice") else "ngspice_gate_state",
                    "quantity": "Ku" if key.endswith("ku") else "Kd",
                    "minimum": minimum,
                    "maximum": maximum,
                    "below_zero": minimum < 0.0,
                    "above_one": maximum > 1.0,
                }
            )

        state_traces = (
            ("GUP", "gate_state_gup", "#0072b2"),
            ("GDN", "gate_state_gdn", "#e69f00"),
            ("GUP target", "gate_state_guptarget", "#56b4e9"),
            ("GDN target", "gate_state_gdntarget", "#009e73"),
        )
        for label, key, color in state_traces:
            values = data[key][window]
            style = "--" if "target" in label.lower() else "-"
            width = 1.25 if "target" in label.lower() else 2.2
            ax_state.plot(t, values, color=color, linewidth=width, linestyle=style, label=label)
            if "target" not in label.lower():
                minimum, maximum = finite_range(values)
                summaries.append(
                    {
                        "device": device,
                        "source": "ngspice_gate_state",
                        "quantity": label,
                        "minimum": minimum,
                        "maximum": maximum,
                        "below_zero": minimum < -1e-9,
                        "above_one": maximum > 1.0 + 1e-9,
                    }
                )

        ax_coeff.set_title(LABELS[device], fontsize=15, fontweight="bold")
        ax_coeff.set_ylabel("coefficient" if column == 0 else "")
        ax_state.set_ylabel("hidden state" if column == 0 else "")
        ax_state.set_xlabel("time from input edge (ns)")
        ax_coeff.grid(True, alpha=0.22)
        ax_state.grid(True, alpha=0.22)
        ax_state.set_ylim(-0.08, 1.08)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.96))
    handles, labels = axes[1, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.015))
    fig.suptitle("Coefficient excursions versus bounded hidden states", fontsize=18, fontweight="bold", y=0.995)
    fig.subplots_adjust(left=0.065, right=0.985, top=0.89, bottom=0.12, wspace=0.17, hspace=0.16)
    figure_path = plot_dir / "three_buffer_kukd_excursions_vs_gate_states.png"
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)

    csv_path = OUT_DIR / "coefficient_excursion_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    readme = OUT_DIR / "README.md"
    readme.write_text(
        """# Three-Buffer Ku/Kd Excursion Audit

This report uses cached long-transition waveforms only; no simulator was run.

## Finding

- `GUP/GDN` are capacitor-backed normalized hidden states and remain inside 0 to 1.
- `Ku/Kd` are effective multipliers applied to static IBIS pullup/pulldown I/V curves. They are not probabilities or physical gate voltages, so the IBIS decomposition does not require them to remain inside 0 to 1.
- The excursions are already present in the HSPICE native-IBIS coefficients. They are strongest for fast `io_buf`, moderate for `ex2`, and small for `inv_chain`.
- The coefficient extraction solves a two-fixture current-balance system. Fast `dV/dt`, `C_comp` subtraction, clamp current, and mismatch between dynamic transistor behavior and static I/V tables can require a coefficient below 0 or above 1.
- The gate-state model clamps the hidden state before applying its directional PWL map, but it intentionally does not clip the mapped coefficient. Its rate residual can also add a signed `dG/dt` correction. Clipping would erase the native negative Kd excursion that the reconstruction gate was designed to preserve.

## Files

- `plots/three_buffer_kukd_excursions_vs_gate_states.png`
- `coefficient_excursion_summary.csv`

The plotted traces are copied from `results/three_buffer_gup_gdn_waveforms_2026-08-04/source_data`.
""",
        encoding="utf-8",
    )

    print(figure_path)
    print(csv_path)


if __name__ == "__main__":
    main()
