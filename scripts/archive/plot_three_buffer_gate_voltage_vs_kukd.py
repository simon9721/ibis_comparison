from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "results" / "three_buffer_common_pulse_sweep_edge50ps_2026-07-30"
OUT_DIR = ROOT / "results" / "three_buffer_gate_voltage_vs_kukd_2026-07-31"

CASES = (
    ("edge_50ps_long_control", "Complete transition (10 ns high)"),
    ("short_high_1ns", "Interrupted transition (1 ns high)"),
)

BLACK = "#111111"
KU_COLOR = "#0072B2"
KD_COLOR = "#D55E00"
EDGE_COLOR = "#7A7A7A"
GRID_COLOR = "#D9DEE5"


@dataclass(frozen=True)
class Device:
    device_id: str
    label: str
    supply_v: float
    gate_nodes: str
    separate_gates: bool


DEVICES = (
    Device("io_buf", "io_buf", 3.3, "PMOS: xdut.n2; NMOS: xdut.n3", True),
    Device("inv_chain", "inv_chain", 1.8, "shared output-stage gate: xdut.vout7", False),
    Device("ex2", "ex2", 3.3, "shared output-stage gate: xdut.n4", False),
)


def read_waveform(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"No waveform rows in {path}")
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def threshold_crossings(time_ns: np.ndarray, values: np.ndarray, threshold: float) -> list[float]:
    crossings: list[float] = []
    signed = values - threshold
    for index in np.flatnonzero((signed[:-1] <= 0) & (signed[1:] > 0)):
        fraction = -signed[index] / (signed[index + 1] - signed[index])
        crossings.append(float(time_ns[index] + fraction * (time_ns[index + 1] - time_ns[index])))
    for index in np.flatnonzero((signed[:-1] >= 0) & (signed[1:] < 0)):
        fraction = -signed[index] / (signed[index + 1] - signed[index])
        crossings.append(float(time_ns[index] + fraction * (time_ns[index + 1] - time_ns[index])))
    return sorted(crossings)


def gate_proxies(device: Device, data: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    control_1 = data["transistor_control_1_v"] / device.supply_v
    ku_proxy = 1.0 - control_1
    if device.separate_gates:
        kd_proxy = data["transistor_control_2_v"] / device.supply_v
    else:
        kd_proxy = control_1
    return ku_proxy, kd_proxy


def marker_stride(size: int) -> int:
    return max(1, size // 32)


def plot_pair(
    ax: plt.Axes,
    time_relative_ns: np.ndarray,
    ibis: np.ndarray,
    proxy: np.ndarray,
    color: str,
) -> None:
    # The colored trace is drawn inside a wider black trace. Both remain visible
    # even when the proxy and native-IBIS coefficient coincide closely.
    ax.plot(time_relative_ns, ibis, color=BLACK, lw=4.6, solid_capstyle="round", zorder=2)
    ax.plot(
        time_relative_ns,
        proxy,
        color=color,
        lw=2.1,
        marker="o",
        markersize=3.8,
        markeredgecolor="white",
        markeredgewidth=0.55,
        markevery=marker_stride(time_relative_ns.size),
        solid_capstyle="round",
        zorder=3,
    )


def add_edge_markers(ax: plt.Axes, reverse_relative_ns: float) -> None:
    for edge, label in ((0.0, "rise"), (reverse_relative_ns, "fall")):
        ax.axvline(edge, color=EDGE_COLOR, lw=1.2, ls="--", zorder=1)
        ax.text(
            edge,
            1.115,
            label,
            color="#555555",
            fontsize=9,
            ha="center",
            va="bottom",
            clip_on=False,
        )


def write_source_data(
    device: Device,
    case_id: str,
    case_label: str,
    data: dict[str, np.ndarray],
    relative_time_ns: np.ndarray,
    ku_proxy: np.ndarray,
    kd_proxy: np.ndarray,
    active: np.ndarray,
) -> None:
    path = OUT_DIR / "source_data" / f"{device.device_id}_{case_id}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "device",
        "case_id",
        "case_label",
        "time_ns",
        "relative_time_ns",
        "input_v",
        "pmos_or_shared_gate_v",
        "nmos_gate_v",
        "hspice_native_ibis_ku",
        "hspice_native_ibis_kd",
        "transistor_gate_ku_proxy",
        "transistor_gate_kd_proxy",
    ]
    control_2 = data.get("transistor_control_2_v", data["transistor_control_1_v"])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in np.flatnonzero(active):
            writer.writerow(
                {
                    "device": device.device_id,
                    "case_id": case_id,
                    "case_label": case_label,
                    "time_ns": f"{data['time_ns'][index]:.12g}",
                    "relative_time_ns": f"{relative_time_ns[index]:.12g}",
                    "input_v": f"{data['input_v'][index]:.12g}",
                    "pmos_or_shared_gate_v": f"{data['transistor_control_1_v'][index]:.12g}",
                    "nmos_gate_v": f"{control_2[index]:.12g}",
                    "hspice_native_ibis_ku": f"{data['hspice_ibis_ku'][index]:.12g}",
                    "hspice_native_ibis_kd": f"{data['hspice_ibis_kd'][index]:.12g}",
                    "transistor_gate_ku_proxy": f"{ku_proxy[index]:.12g}",
                    "transistor_gate_kd_proxy": f"{kd_proxy[index]:.12g}",
                }
            )


def plot_device(device: Device) -> tuple[Path, list[dict[str, object]]]:
    fig, axes = plt.subplots(2, 2, figsize=(16.0, 9.2), constrained_layout=False)
    fig.subplots_adjust(left=0.075, right=0.925, bottom=0.14, top=0.76, wspace=0.25, hspace=0.22)
    metrics: list[dict[str, object]] = []

    for column, (case_id, case_label) in enumerate(CASES):
        path = SOURCE_DIR / "runs" / device.device_id / "waveform_data" / f"{case_id}.csv"
        data = read_waveform(path)
        ku_proxy, kd_proxy = gate_proxies(device, data)
        time_ns = data["time_ns"]
        edges = threshold_crossings(time_ns, data["input_v"], 0.5 * device.supply_v)
        if len(edges) < 2:
            raise RuntimeError(f"Expected rise and fall crossings in {path}; found {edges}")
        first_edge, reverse_edge = edges[:2]
        relative_time_ns = time_ns - first_edge
        reverse_relative_ns = reverse_edge - first_edge
        x_min = -0.75
        x_max = reverse_relative_ns + 2.0
        active = (relative_time_ns >= x_min) & (relative_time_ns <= x_max)

        ax_ku = axes[0, column]
        ax_kd = axes[1, column]
        plot_pair(
            ax_ku,
            relative_time_ns[active],
            data["hspice_ibis_ku"][active],
            ku_proxy[active],
            KU_COLOR,
        )
        plot_pair(
            ax_kd,
            relative_time_ns[active],
            data["hspice_ibis_kd"][active],
            kd_proxy[active],
            KD_COLOR,
        )

        for ax in (ax_ku, ax_kd):
            add_edge_markers(ax, reverse_relative_ns)
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(-0.18, 1.18)
            ax.axhline(0.0, color="#A7ADB5", lw=0.8)
            ax.axhline(1.0, color="#A7ADB5", lw=0.8, ls=":")
            ax.grid(True, color=GRID_COLOR, linewidth=0.75)
            ax.tick_params(labelsize=10)
            ax.spines[["top", "right"]].set_visible(False)

        ax_ku.set_title(case_label, fontsize=14, fontweight="bold", pad=12)
        ax_kd.set_xlabel("Time from input rising edge (ns)", fontsize=11)

        ku_secondary = ax_ku.secondary_yaxis(
            "right",
            functions=(
                lambda normalized: device.supply_v * (1.0 - normalized),
                lambda voltage: 1.0 - voltage / device.supply_v,
            ),
        )
        ku_secondary.set_ylabel("PMOS/shared gate (V)", color=KU_COLOR, fontsize=10)
        ku_secondary.tick_params(axis="y", colors=KU_COLOR, labelsize=9)

        kd_secondary = ax_kd.secondary_yaxis(
            "right",
            functions=(
                lambda normalized: device.supply_v * normalized,
                lambda voltage: voltage / device.supply_v,
            ),
        )
        kd_secondary.set_ylabel("NMOS/shared gate (V)", color=KD_COLOR, fontsize=10)
        kd_secondary.tick_params(axis="y", colors=KD_COLOR, labelsize=9)

        write_source_data(
            device,
            case_id,
            case_label,
            data,
            relative_time_ns,
            ku_proxy,
            kd_proxy,
            active,
        )

        metrics.extend(
            (
                {
                    "device": device.device_id,
                    "case_id": case_id,
                    "quantity": "Ku",
                    "proxy_rmse": float(
                        np.sqrt(np.mean((data["hspice_ibis_ku"][active] - ku_proxy[active]) ** 2))
                    ),
                    "gate_node": device.gate_nodes,
                },
                {
                    "device": device.device_id,
                    "case_id": case_id,
                    "quantity": "Kd",
                    "proxy_rmse": float(
                        np.sqrt(np.mean((data["hspice_ibis_kd"][active] - kd_proxy[active]) ** 2))
                    ),
                    "gate_node": device.gate_nodes,
                },
            )
        )

    axes[0, 0].set_ylabel("Pullup strength: Ku / gate proxy", fontsize=11)
    axes[1, 0].set_ylabel("Pulldown strength: Kd / gate proxy", fontsize=11)

    fig.suptitle(
        f"{device.label}: final-stage gate voltage vs. native-IBIS Ku/Kd",
        fontsize=20,
        fontweight="bold",
        y=0.975,
    )
    fig.text(
        0.5,
        0.925,
        "50 ps input edges | 50 ohm || 2 pF load | HSPICE cached transistor and native-IBIS results",
        ha="center",
        va="center",
        fontsize=11,
        color="#444444",
    )
    handles = (
        Line2D([0], [0], color=BLACK, lw=4.6, label="HSPICE native-IBIS coefficient"),
        Line2D([0], [0], color=KU_COLOR, lw=2.1, marker="o", label="PMOS gate-voltage Ku proxy"),
        Line2D([0], [0], color=KD_COLOR, lw=2.1, marker="o", label="NMOS gate-voltage Kd proxy"),
        Line2D([0], [0], color=EDGE_COLOR, lw=1.2, ls="--", label="input edge"),
    )
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.885), ncol=4, frameon=False)
    fig.text(
        0.5,
        0.055,
        f"Gate probes: {device.gate_nodes}.  "
        "Ku proxy = 1 - V(PMOS/shared gate)/VDD; Kd proxy = V(NMOS/shared gate)/VDD.",
        ha="center",
        va="center",
        fontsize=10,
        color="#444444",
    )
    fig.text(
        0.5,
        0.025,
        "Colored curves are timing/strength proxies from physical gate voltage; they are not transistor-level Ku/Kd extractions.",
        ha="center",
        va="center",
        fontsize=9.5,
        color="#666666",
    )

    output = OUT_DIR / "plots" / f"{device.device_id}_gate_voltage_vs_kukd.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)
    return output, metrics


def write_metrics(rows: list[dict[str, object]]) -> None:
    path = OUT_DIR / "proxy_metrics_active_window.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_readme(outputs: list[Path]) -> None:
    lines = [
        "# Three-Buffer Gate Voltage vs. Ku/Kd Figures",
        "",
        "Presentation-ready figures generated from cached data only. No simulations were rerun.",
        "",
        "## Figures",
        "",
    ]
    lines.extend(f"- `{path.relative_to(OUT_DIR).as_posix()}`" for path in outputs)
    lines.extend(
        (
            "",
            "Each figure compares the normal 10 ns high control with the same 1 ns short-high pulse.",
            "The stimulus uses 50 ps rise/fall time and a 50 ohm || 2 pF load.",
            "",
            "## Meaning",
            "",
            "- Black: HSPICE native-IBIS runtime `Ku` or `Kd`.",
            "- Blue: physical PMOS/shared-gate voltage represented as `1 - Vgate/VDD`.",
            "- Orange: physical NMOS/shared-gate voltage represented as `Vgate/VDD`.",
            "- The colored curves are gate-voltage proxies. They preserve physical gate timing but are not exact transistor `Ku/Kd` extractions.",
            "- The secondary right axes convert the normalized proxy back into actual gate volts.",
            "",
            "## Gate Probes",
            "",
            "- `io_buf`: PMOS `v(xdut.n2)` and NMOS `v(xdut.n3)`.",
            "- `inv_chain`: shared final-stage control `v(xdut.vout7)`.",
            "- `ex2`: shared output-stage control `v(xdut.n4)`.",
            "",
            "## Numeric Data",
            "",
            "- `source_data/*.csv`: exact active-window data plotted in each column.",
            "- `proxy_metrics_active_window.csv`: proxy RMSE over the displayed windows.",
            "",
            f"Source study: `{SOURCE_DIR.relative_to(ROOT).as_posix()}`.",
        )
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    metric_rows: list[dict[str, object]] = []
    for device in DEVICES:
        output, rows = plot_device(device)
        outputs.append(output)
        metric_rows.extend(rows)
    write_metrics(metric_rows)
    write_readme(outputs)
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
