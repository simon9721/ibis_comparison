from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


SOURCE_DIR = ROOT / "results" / "three_buffer_common_pulse_sweep_edge50ps_2026-07-30"
OUT_DIR = ROOT / "results" / "three_buffer_gup_gdn_waveforms_2026-08-04"

CASES = (
    ("edge_50ps_long_control", "Complete transition (10 ns high)"),
    ("short_high_1ns", "Interrupted transition (1 ns high)"),
    ("short_low_1ns", "Interrupted transition (1 ns low)"),
)

BLACK = "#111111"
STATE_COLOR = "#0072B2"
MAPPED_COLOR = "#CC3311"
TARGET_COLOR = "#8A8F98"
EDGE_COLOR = "#7A7A7A"
GRID_COLOR = "#D9DEE5"


@dataclass(frozen=True)
class Device:
    device_id: str
    label: str
    supply_v: float


DEVICES = (
    Device("io_buf", "io_buf", 3.3),
    Device("inv_chain", "inv_chain", 1.8),
    Device("ex2", "ex2", 3.3),
)


def read_waveform(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"No rows in {path}")
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def crossings(time_ns: np.ndarray, values: np.ndarray, threshold: float) -> list[float]:
    signed = values - threshold
    result: list[float] = []
    indexes = np.flatnonzero(signed[:-1] * signed[1:] < 0)
    for index in indexes:
        fraction = -signed[index] / (signed[index + 1] - signed[index])
        result.append(float(time_ns[index] + fraction * (time_ns[index + 1] - time_ns[index])))
    return result


def plot_line(ax: plt.Axes, x: np.ndarray, y: np.ndarray, color: str, width: float, zorder: int) -> None:
    ax.plot(x, y, color=color, lw=width, solid_capstyle="round", zorder=zorder)


def write_source(
    device: Device,
    case_id: str,
    data: dict[str, np.ndarray],
    relative_time: np.ndarray,
    active: np.ndarray,
) -> None:
    output = OUT_DIR / "source_data" / f"{device.device_id}_{case_id}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    keys = [
        "input_v",
        "hspice_ibis_ku",
        "hspice_ibis_kd",
        "gate_state_gup",
        "gate_state_gdn",
        "gate_state_guptarget",
        "gate_state_gdntarget",
        "gate_state_ku",
        "gate_state_kd",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_ns", "relative_time_ns", *keys])
        writer.writeheader()
        for index in np.flatnonzero(active):
            writer.writerow(
                {
                    "time_ns": f"{data['time_ns'][index]:.12g}",
                    "relative_time_ns": f"{relative_time[index]:.12g}",
                    **{key: f"{data[key][index]:.12g}" for key in keys},
                }
            )


def plot_device(device: Device) -> Path:
    fig, axes = plt.subplots(2, len(CASES), figsize=(21.0, 8.6))
    fig.subplots_adjust(left=0.055, right=0.985, bottom=0.13, top=0.75, wspace=0.18, hspace=0.24)

    for column, (case_id, case_label) in enumerate(CASES):
        path = SOURCE_DIR / "runs" / device.device_id / "waveform_data" / f"{case_id}.csv"
        data = read_waveform(path)
        edge_times = crossings(data["time_ns"], data["input_v"], 0.5 * device.supply_v)
        if len(edge_times) < 2:
            raise RuntimeError(f"Expected two command edges in {path}")
        first_edge, reverse_edge = edge_times[:2]
        relative_time = data["time_ns"] - first_edge
        reverse_relative = reverse_edge - first_edge
        x_min, x_max = -0.75, reverse_relative + 2.0
        active = (relative_time >= x_min) & (relative_time <= x_max)
        x = relative_time[active]

        for row, coefficient in enumerate(("ku", "kd")):
            ax = axes[row, column]
            state = data[f"gate_state_g{'up' if coefficient == 'ku' else 'dn'}"][active]
            target = data[f"gate_state_g{'up' if coefficient == 'ku' else 'dn'}target"][active]
            mapped = data[f"gate_state_{coefficient}"][active]
            native = data[f"hspice_ibis_{coefficient}"][active]

            plot_line(ax, x, native, BLACK, 4.4, 2)
            plot_line(ax, x, target, TARGET_COLOR, 1.6, 1)
            plot_line(ax, x, state, STATE_COLOR, 2.5, 4)
            plot_line(ax, x, mapped, MAPPED_COLOR, 2.0, 3)

            edge_labels = ("fall", "rise") if "short_low" in case_id else ("rise", "fall")
            for edge, label in zip((0.0, reverse_relative), edge_labels):
                ax.axvline(edge, color=EDGE_COLOR, lw=1.1, ls="--", zorder=0)
                ax.text(edge, 1.19, label, color="#555555", fontsize=9, ha="center", va="bottom")
            ax.axhline(0.0, color="#A7ADB5", lw=0.8)
            ax.axhline(1.0, color="#A7ADB5", lw=0.8, ls=":")
            ax.set_xlim(x_min, x_max)
            visible = np.concatenate((native, state, target, mapped))
            lower = min(-0.15, float(np.nanmin(visible)) - 0.08)
            upper = max(1.15, float(np.nanmax(visible)) + 0.08)
            ax.set_ylim(lower, upper)
            ax.grid(True, color=GRID_COLOR, lw=0.75)
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=10)

        axes[0, column].set_title(case_label, fontsize=14, fontweight="bold", pad=12)
        axes[1, column].set_xlabel("Time from first input edge (ns)", fontsize=11)
        write_source(device, case_id, data, relative_time, active)

    axes[0, 0].set_ylabel("Pullup: GUP and Ku", fontsize=11)
    axes[1, 0].set_ylabel("Pulldown: GDN and Kd", fontsize=11)
    fig.suptitle(
        f"{device.label}: direct gate-state waveforms and mapped coefficients",
        fontsize=20,
        fontweight="bold",
        y=0.975,
    )
    fig.text(
        0.5,
        0.92,
        "50 ps input edges | 50 ohm || 2 pF load | full two-state gate model",
        fontsize=11,
        color="#444444",
        ha="center",
    )
    handles = (
        Line2D([0], [0], color=BLACK, lw=4.4, label="HSPICE native-IBIS Ku/Kd"),
        Line2D([0], [0], color=STATE_COLOR, lw=2.5, label="continuous state GUP/GDN"),
        Line2D([0], [0], color=MAPPED_COLOR, lw=2.0, label="mapped Ku(GUP)/Kd(GDN)"),
        Line2D([0], [0], color=TARGET_COLOR, lw=1.6, label="state target"),
    )
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.875), ncol=4, frameon=False)
    fig.text(
        0.5,
        0.045,
        "GUP/GDN are bounded hidden memory states. The coefficient maps and rate residual can extend Ku/Kd outside 0..1.",
        ha="center",
        fontsize=10,
        color="#555555",
    )
    output = OUT_DIR / "plots" / f"{device.device_id}_gup_gdn_waveforms.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)
    return output


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [plot_device(device) for device in DEVICES]
    lines = [
        "# Three-Buffer Direct GUP/GDN Waveforms",
        "",
        "Generated from cached common-pulse waveform CSVs. No simulations were rerun.",
        "",
        "## Figures",
        "",
        *[f"- `{path.relative_to(OUT_DIR).as_posix()}`" for path in outputs],
        "",
        "Blue is the continuous hidden state, red is the resulting mapped coefficient, black is HSPICE native IBIS, and gray is the delayed command target.",
        "The source data for every panel is under `source_data/`.",
        "",
        f"Source study: `{SOURCE_DIR.relative_to(ROOT).as_posix()}`.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="ascii")
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
