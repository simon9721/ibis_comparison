from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

import run_three_buffer_realistic_pulse_campaign as base


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "three_buffer_common_pulse_sweep_2026-07-30"
EDGE_NS = 0.100
PULSE_WIDTHS_NS = (0.250, 0.500, 1.000, 2.000)
PROFILE_ID = "fast_5ps"


def profile_for(device: base.Device) -> base.Profile:
    return next(profile for profile in base.profiles(device) if profile.profile_id == PROFILE_ID)


def cases() -> list[base.PulseCase]:
    result = [
        base.PulseCase(
            case_id=f"{base.edge_tag(EDGE_NS)}_long_control",
            edge_ns=EDGE_NS,
            pattern="rise_fall",
            pulse_width_ns=10.0,
            stop_ns=22.0,
            target_label="long control",
        )
    ]
    for direction in ("short_high", "short_low"):
        for width_ns in PULSE_WIDTHS_NS:
            result.append(
                base.PulseCase(
                    case_id=f"{direction}_{base.width_tag(width_ns)}",
                    edge_ns=EDGE_NS,
                    pattern=direction,
                    pulse_width_ns=width_ns,
                    stop_ns=22.0,
                    target_label=direction.replace("_", " "),
                )
            )
    return result


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    base.write_csv(path, rows)


def read_waveform(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def waveform_path(device: base.Device, case: base.PulseCase) -> Path:
    return (
        OUT_DIR
        / "runs"
        / device.device_id
        / "waveform_data"
        / f"{case.case_id}.csv"
    )


def plot_path(device: base.Device, case: base.PulseCase) -> Path:
    return (
        OUT_DIR
        / "plots"
        / "cases"
        / device.device_id
        / f"{case.case_id}.png"
    )


def plot_common_inputs() -> None:
    colors = ("#1769aa", "#008b6e", "#d97706", "#7b2cbf")
    fig, axes = base.plt.subplots(2, 1, figsize=(13.0, 7.5), constrained_layout=True)
    representative = base.DEVICES[0]
    for ax, direction in zip(axes, ("short_high", "short_low")):
        for color, width_ns in zip(colors, PULSE_WIDTHS_NS):
            case = next(
                case
                for case in cases()
                if case.pattern == direction and case.pulse_width_ns == width_ns
            )
            start = 4.5 if direction == "short_high" else 9.5
            stop = 8.0 if direction == "short_high" else 13.0
            time_ns = np.linspace(start, stop, 3501)
            values = base.input_waveform(representative, case, time_ns) / representative.supply_v
            ax.plot(time_ns, values, color=color, lw=2.2, label=f"{base.fmt(width_ns * 1000)} ps")
        ax.set_title(direction.replace("_", " "), loc="left", fontweight="bold")
        ax.set_ylabel("Input / VDD")
        ax.set_ylim(-0.08, 1.08)
        ax.grid(True, color=base.GRID)
    axes[0].legend(title="Common pulse width", frameon=False, ncol=4)
    axes[1].set_xlabel("Time (ns)")
    fig.suptitle(
        f"Common stimulus grid | {base.fmt(EDGE_NS * 1000)} ps rise/fall time",
        fontweight="bold",
    )
    output = OUT_DIR / "plots" / "00_common_input_stimuli.png"
    base.ensure_dir(output.parent)
    fig.savefig(output, dpi=180)
    base.plt.close(fig)


def native_range_rows(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "device": row["device"],
            "case_id": row["case_id"],
            "direction": (
                "long_control"
                if row["case_id"] == "edge_100ps_long_control"
                else str(row["case_id"]).rsplit("_", 1)[0]
            ),
            "pulse_width_ps": row["pulse_width_ps"],
            "ku_min": row["native_ku_min"],
            "ku_max": row["native_ku_max"],
            "kd_min": row["native_kd_min"],
            "kd_max": row["native_kd_max"],
            "outside_nominal_coefficient_range": row["native_reference_extended_range"],
        }
        for row in metrics
        if row["flow"] == "hspice_transistor"
    ]


def summary_rows(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for device in base.DEVICES:
        for flow in ("hspice_transistor", "gate_state", "hybrid"):
            selected = [
                row
                for row in metrics
                if row["device"] == device.device_id and row["flow"] == flow
            ]
            completed = [
                row
                for row in selected
                if row.get("pad_rmse_v") not in {"", None}
                and np.isfinite(float(row["pad_rmse_v"]))
            ]
            result.append(
                {
                    "device": device.device_id,
                    "flow": flow,
                    "cases": len(selected),
                    "completed": len(completed),
                    "numeric_failures": sum(row["status"] == "NUMERIC_FAIL" for row in selected),
                    "median_pad_rmse_mv": (
                        float(np.median([float(row["pad_rmse_v"]) for row in completed])) * 1000
                        if completed
                        else float("nan")
                    ),
                    "median_ku_rmse": (
                        float(
                            np.median(
                                [
                                    float(row["ku_rmse"])
                                    for row in completed
                                    if row.get("ku_rmse") not in {"", None}
                                ]
                            )
                        )
                        if flow != "hspice_transistor" and completed
                        else ""
                    ),
                    "median_kd_rmse": (
                        float(
                            np.median(
                                [
                                    float(row["kd_rmse"])
                                    for row in completed
                                    if row.get("kd_rmse") not in {"", None}
                                ]
                            )
                        )
                        if flow != "hspice_transistor" and completed
                        else ""
                    ),
                }
            )
    return result


def response_vs_width_rows() -> list[dict[str, object]]:
    pad_keys = {
        "hspice_transistor": "hspice_transistor_pad_v",
        "hspice_native_ibis": "hspice_ibis_pad_v",
        "gate_state": "gate_state_pad_v",
        "hybrid": "hybrid_pad_v",
    }
    rows: list[dict[str, object]] = []
    for device in base.DEVICES:
        long_data = read_waveform(
            waveform_path(
                device,
                next(case for case in cases() if case.pattern == "rise_fall"),
            )
        )
        levels: dict[str, tuple[float, float, float]] = {}
        time_ns = long_data["time_ns"]
        low_mask = (time_ns >= 4.0) & (time_ns <= 4.8)
        high_mask = (time_ns >= 11.5) & (time_ns <= 14.5)
        for flow, key in pad_keys.items():
            if key not in long_data:
                continue
            low = float(np.median(long_data[key][low_mask]))
            high = float(np.median(long_data[key][high_mask]))
            levels[flow] = (low, high, high - low)

        for case in cases():
            if case.pattern not in {"short_high", "short_low"}:
                continue
            data = read_waveform(waveform_path(device, case))
            time_ns = data["time_ns"]
            event_start = 4.8 if case.pattern == "short_high" else 9.8
            event_mask = time_ns >= event_start
            for flow, key in pad_keys.items():
                if key not in data or flow not in levels:
                    continue
                low, high, swing = levels[flow]
                peak = float(np.max(data[key][event_mask]))
                minimum = float(np.min(data[key][event_mask]))
                excursion = peak - low if case.pattern == "short_high" else high - minimum
                rows.append(
                    {
                        "device": device.device_id,
                        "direction": case.pattern,
                        "pulse_width_ps": case.pulse_width_ns * 1000,
                        "flow": flow,
                        "normal_low_v": low,
                        "normal_high_v": high,
                        "normal_swing_v": swing,
                        "response_peak_v": peak,
                        "response_min_v": minimum,
                        "response_excursion_v": excursion,
                        "response_fraction_of_own_long_swing": (
                            excursion / swing if abs(swing) > 1e-12 else float("nan")
                        ),
                    }
                )
            native_mask = event_mask
            rows.append(
                {
                    "device": device.device_id,
                    "direction": case.pattern,
                    "pulse_width_ps": case.pulse_width_ns * 1000,
                    "flow": "hspice_native_coefficients",
                    "native_ku_min": float(np.min(data["hspice_ibis_ku"][native_mask])),
                    "native_ku_max": float(np.max(data["hspice_ibis_ku"][native_mask])),
                    "native_kd_min": float(np.min(data["hspice_ibis_kd"][native_mask])),
                    "native_kd_max": float(np.max(data["hspice_ibis_kd"][native_mask])),
                }
            )
    return rows


def plot_response_vs_width(rows: list[dict[str, object]]) -> None:
    colors = {"io_buf": "#1769aa", "inv_chain": "#008b6e", "ex2": "#d97706"}
    fig, axes = base.plt.subplots(2, 2, figsize=(14.0, 9.0), sharex=True, constrained_layout=True)
    for row_index, flow in enumerate(("hspice_transistor", "hspice_native_ibis")):
        for column, direction in enumerate(("short_high", "short_low")):
            ax = axes[row_index, column]
            for device in base.DEVICES:
                selected = sorted(
                    (
                        row
                        for row in rows
                        if row["flow"] == flow
                        and row["direction"] == direction
                        and row["device"] == device.device_id
                    ),
                    key=lambda row: float(row["pulse_width_ps"]),
                )
                ax.plot(
                    [float(row["pulse_width_ps"]) for row in selected],
                    [float(row["response_fraction_of_own_long_swing"]) for row in selected],
                    marker="o",
                    lw=2.2,
                    color=colors[device.device_id],
                    label=device.label,
                )
            ax.axhline(1.0, color="#888888", lw=1.0, ls=":")
            ax.set_title(
                f"{'HSPICE transistor' if flow == 'hspice_transistor' else 'HSPICE native IBIS'} | "
                f"{direction.replace('_', ' ')}",
                loc="left",
                fontweight="bold",
            )
            ax.set_ylabel("Pad excursion / own long-pulse swing")
            ax.grid(True, color=base.GRID)
            if row_index == 1:
                ax.set_xlabel("Common pulse width (ps)")
    axes[0, 0].legend(frameon=False)
    output = OUT_DIR / "plots" / "04_response_vs_common_pulse_width.png"
    fig.savefig(output, dpi=180)
    base.plt.close(fig)


def plot_native_coefficients_vs_width(rows: list[dict[str, object]]) -> None:
    colors = {"io_buf": "#1769aa", "inv_chain": "#008b6e", "ex2": "#d97706"}
    fig, axes = base.plt.subplots(2, 2, figsize=(14.0, 9.0), sharex=True, constrained_layout=True)
    definitions = (
        ("short_high", "native_ku_max", "Short high | Ku maximum"),
        ("short_high", "native_kd_min", "Short high | Kd minimum"),
        ("short_low", "native_ku_min", "Short low | Ku minimum"),
        ("short_low", "native_kd_max", "Short low | Kd maximum"),
    )
    coefficient_rows = [row for row in rows if row["flow"] == "hspice_native_coefficients"]
    for ax, (direction, key, title) in zip(axes.reshape(-1), definitions):
        for device in base.DEVICES:
            selected = sorted(
                (
                    row
                    for row in coefficient_rows
                    if row["direction"] == direction and row["device"] == device.device_id
                ),
                key=lambda row: float(row["pulse_width_ps"]),
            )
            ax.plot(
                [float(row["pulse_width_ps"]) for row in selected],
                [float(row[key]) for row in selected],
                marker="o",
                lw=2.2,
                color=colors[device.device_id],
                label=device.label,
            )
        ax.axhline(0.0, color="#999999", lw=0.8)
        ax.axhline(1.0, color="#999999", lw=0.8, ls=":")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_ylabel(key.replace("native_", "").replace("_", " "))
        ax.set_xlabel("Common pulse width (ps)")
        ax.grid(True, color=base.GRID)
    axes[0, 0].legend(frameon=False)
    output = OUT_DIR / "plots" / "05_native_kukd_vs_common_pulse_width.png"
    fig.savefig(output, dpi=180)
    base.plt.close(fig)


def transistor_gate_proxies(
    device: base.Device,
    data: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    control_1 = data["transistor_control_1_v"] / device.supply_v
    ku_proxy = 1.0 - control_1
    if device.device_id == "io_buf":
        kd_proxy = data["transistor_control_2_v"] / device.supply_v
    else:
        kd_proxy = control_1
    return ku_proxy, kd_proxy


def plot_transistor_gate_proxies() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for device_index, device in enumerate(base.DEVICES, start=1):
        device_paths: list[Path] = []
        for case in cases():
            data = read_waveform(waveform_path(device, case))
            ku_proxy, kd_proxy = transistor_gate_proxies(device, data)
            time_ns = data["time_ns"]
            output = (
                OUT_DIR
                / "plots"
                / "transistor_gate_proxy"
                / device.device_id
                / f"{case.case_id}.png"
            )
            base.ensure_dir(output.parent)
            fig, axes = base.plt.subplots(2, 1, figsize=(13.5, 7.8), sharex=True, constrained_layout=True)
            axes[0].plot(
                time_ns,
                data["hspice_ibis_ku"],
                color=base.BLACK,
                lw=3.0,
                label="HSPICE native IBIS Ku",
            )
            axes[0].plot(
                time_ns,
                ku_proxy,
                color=base.GREEN,
                lw=2.2,
                label="Transistor gate-voltage Ku proxy",
            )
            axes[1].plot(
                time_ns,
                data["hspice_ibis_kd"],
                color=base.BLACK,
                lw=3.0,
                label="HSPICE native IBIS Kd",
            )
            axes[1].plot(
                time_ns,
                kd_proxy,
                color=base.ORANGE,
                lw=2.2,
                label="Transistor gate-voltage Kd proxy",
            )
            for ax in axes:
                for edge in base.command_edges(device, case):
                    ax.axvline(edge, color=base.EDGE_COLOR, ls="--", lw=1.0)
                ax.grid(True, color=base.GRID)
                ax.legend(frameon=False, loc="best")
            axes[0].set_ylabel("Ku / proxy")
            axes[1].set_ylabel("Kd / proxy")
            axes[1].set_xlabel("Time (ns)")
            fig.suptitle(
                f"{device.label} | {case.target_label} | "
                f"{base.fmt(EDGE_NS * 1000)} ps edge, "
                f"{base.fmt(case.pulse_width_ns * 1000)} ps pulse",
                fontweight="bold",
            )
            fig.savefig(output, dpi=180)
            base.plt.close(fig)
            device_paths.append(output)
            rows.append(
                {
                    "device": device.device_id,
                    "case_id": case.case_id,
                    "direction": case.pattern,
                    "pulse_width_ps": case.pulse_width_ns * 1000,
                    "ku_proxy_rmse_vs_native_ibis": base.rmse(data["hspice_ibis_ku"], ku_proxy),
                    "kd_proxy_rmse_vs_native_ibis": base.rmse(data["hspice_ibis_kd"], kd_proxy),
                    "ku_proxy_min": float(np.min(ku_proxy)),
                    "ku_proxy_max": float(np.max(ku_proxy)),
                    "kd_proxy_min": float(np.min(kd_proxy)),
                    "kd_proxy_max": float(np.max(kd_proxy)),
                    "figure": str(output.relative_to(ROOT)),
                }
            )
        base.contact_sheet(
            device_paths,
            OUT_DIR / "plots" / f"0{device_index + 5}_{device.device_id}_gate_proxy_overview.png",
            columns=2,
        )
    return rows


def edge_slew_comparison() -> list[dict[str, object]]:
    reference_dir = ROOT / "results" / "three_buffer_common_pulse_sweep_2026-07-30"
    reference_path = reference_dir / "response_vs_common_pulse_width.csv"
    current_path = OUT_DIR / "response_vs_common_pulse_width.csv"
    if abs(EDGE_NS - 0.050) > 1e-12 or not reference_path.exists():
        return []
    reference_rows = base.read_csv(reference_path)
    current_rows = base.read_csv(current_path)
    rows: list[dict[str, object]] = []
    for current in current_rows:
        if current["flow"] == "hspice_native_coefficients":
            continue
        reference = next(
            row
            for row in reference_rows
            if row["device"] == current["device"]
            and row["direction"] == current["direction"]
            and row["pulse_width_ps"] == current["pulse_width_ps"]
            and row["flow"] == current["flow"]
        )
        fraction_50 = float(current["response_fraction_of_own_long_swing"])
        fraction_100 = float(reference["response_fraction_of_own_long_swing"])
        rows.append(
            {
                "device": current["device"],
                "direction": current["direction"],
                "pulse_width_ps": current["pulse_width_ps"],
                "flow": current["flow"],
                "response_fraction_edge_50ps": fraction_50,
                "response_fraction_edge_100ps": fraction_100,
                "delta_50ps_minus_100ps": fraction_50 - fraction_100,
            }
        )
    write_csv(OUT_DIR / "edge_50ps_vs_100ps_response.csv", rows)

    colors = {"io_buf": "#1769aa", "inv_chain": "#008b6e", "ex2": "#d97706"}
    fig, axes = base.plt.subplots(2, 2, figsize=(14.0, 9.0), sharex=True, constrained_layout=True)
    for row_index, flow in enumerate(("hspice_transistor", "hspice_native_ibis")):
        for column, direction in enumerate(("short_high", "short_low")):
            ax = axes[row_index, column]
            for device in base.DEVICES:
                selected = sorted(
                    (
                        row
                        for row in rows
                        if row["flow"] == flow
                        and row["direction"] == direction
                        and row["device"] == device.device_id
                    ),
                    key=lambda row: float(row["pulse_width_ps"]),
                )
                widths = [float(row["pulse_width_ps"]) for row in selected]
                ax.plot(
                    widths,
                    [float(row["response_fraction_edge_50ps"]) for row in selected],
                    color=colors[device.device_id],
                    lw=2.3,
                    marker="o",
                    label=f"{device.label} | 50 ps edge",
                )
                ax.plot(
                    widths,
                    [float(row["response_fraction_edge_100ps"]) for row in selected],
                    color=colors[device.device_id],
                    lw=1.7,
                    marker="x",
                    ls="--",
                    label=f"{device.label} | 100 ps edge",
                )
            ax.axhline(1.0, color="#888888", lw=1.0, ls=":")
            ax.set_title(
                f"{'HSPICE transistor' if flow == 'hspice_transistor' else 'HSPICE native IBIS'} | "
                f"{direction.replace('_', ' ')}",
                loc="left",
                fontweight="bold",
            )
            ax.set_ylabel("Pad excursion / own long-pulse swing")
            ax.grid(True, color=base.GRID)
            if row_index == 1:
                ax.set_xlabel("Common pulse width (ps)")
    axes[0, 0].legend(frameon=False, ncol=2, fontsize=9)
    output = OUT_DIR / "plots" / "09_edge_50ps_vs_100ps_response.png"
    fig.savefig(output, dpi=180)
    base.plt.close(fig)
    return rows


def write_readme(metrics: list[dict[str, object]], run_rows: list[dict[str, object]]) -> None:
    failures = [row for row in run_rows if row.get("status") == "NUMERIC_FAIL"]
    response_rows = base.read_csv(OUT_DIR / "response_vs_common_pulse_width.csv")
    proxy_rows = base.read_csv(OUT_DIR / "transistor_gate_proxy_metrics.csv")

    def median(values: list[float]) -> float:
        return float(np.median(np.asarray(values, dtype=float)))

    proxy_summary = {
        device.device_id: (
            median(
                [
                    float(row["ku_proxy_rmse_vs_native_ibis"])
                    for row in proxy_rows
                    if row["device"] == device.device_id
                ]
            ),
            median(
                [
                    float(row["kd_proxy_rmse_vs_native_ibis"])
                    for row in proxy_rows
                    if row["device"] == device.device_id
                ]
            ),
        )
        for device in base.DEVICES
    }
    edge_comparison_rows = base.read_csv(OUT_DIR / "edge_50ps_vs_100ps_response.csv")
    slew_lines: list[str] = []
    if edge_comparison_rows:
        transistor_worst = max(
            (
                row
                for row in edge_comparison_rows
                if row["flow"] == "hspice_transistor"
            ),
            key=lambda row: abs(float(row["delta_50ps_minus_100ps"])),
        )
        native_worst = max(
            (
                row
                for row in edge_comparison_rows
                if row["flow"] == "hspice_native_ibis"
            ),
            key=lambda row: abs(float(row["delta_50ps_minus_100ps"])),
        )
        slew_lines = [
            "## 50 ps Versus 100 ps Input Slew",
            "",
            "The transistor responses are nearly unchanged, confirming that both edges primarily "
            "measure buffer pulse filtering. The largest transistor response-fraction change is "
            f"`{100 * abs(float(transistor_worst['delta_50ps_minus_100ps'])):.1f}` percentage points "
            f"for `{transistor_worst['device']} / {transistor_worst['direction']} / "
            f"{float(transistor_worst['pulse_width_ps']):.0f} ps`.",
            "",
            "Native IBIS is more slew-sensitive. Its largest change is "
            f"`{100 * abs(float(native_worst['delta_50ps_minus_100ps'])):.1f}` percentage points "
            f"for `{native_worst['device']} / {native_worst['direction']} / "
            f"{float(native_worst['pulse_width_ps']):.0f} ps`. This is model behavior rather than "
            "a corresponding transistor-level change.",
            "",
        ]

    def response(
        device: str,
        direction: str,
        width_ps: float,
        flow: str,
    ) -> float:
        row = next(
            row
            for row in response_rows
            if row["device"] == device
            and row["direction"] == direction
            and abs(float(row["pulse_width_ps"]) - width_ps) < 1e-9
            and row["flow"] == flow
        )
        return float(row["response_fraction_of_own_long_swing"])

    lines = [
        "# Three-Buffer Common-Pulse Sweep",
        "",
        "This study uses one common stimulus grid for `io_buf`, `inv_chain`, and `ex2`.",
        "The pulse widths were chosen directly and do not use the adaptive pulse-selection result.",
        "",
        "## Fixed Setup",
        "",
        "- Fast-edge IBIS files only.",
        f"- Runtime rise/fall time: `{base.fmt(EDGE_NS * 1000)} ps` for every device and case.",
        "- Full-swing pulse widths: `250 ps`, `500 ps`, `1 ns`, and `2 ns`.",
        "- Both short-high and short-low directions.",
        "- Normal long-pulse control.",
        "- Load: `50 ohm || 2 pF`.",
        "- HSPICE transistor and native-IBIS references.",
        "- ngspice gate-state and hybrid candidates.",
        "- Transistor controls shown as `1 - V(gate)/VDD` for rising-command polarity.",
        "",
        "## Start Here",
        "",
        "- `plots/00_common_input_stimuli.png`: exact common input grid.",
        "- `plots/01_io_buf_overview.png`: all `io_buf` cases.",
        "- `plots/02_inv_chain_overview.png`: all `inv_chain` cases.",
        "- `plots/03_ex2_overview.png`: all `ex2` cases.",
        "- `plots/04_response_vs_common_pulse_width.png`: pad response trends.",
        "- `plots/05_native_kukd_vs_common_pulse_width.png`: native coefficient trends.",
        "- `plots/06_io_buf_gate_proxy_overview.png`: `io_buf` physical-gate coefficient proxy.",
        "- `plots/07_inv_chain_gate_proxy_overview.png`: `inv_chain` physical-gate coefficient proxy.",
        "- `plots/08_ex2_gate_proxy_overview.png`: `ex2` physical-gate coefficient proxy.",
        "- `plots/09_edge_50ps_vs_100ps_response.png`: input-slew sensitivity, when available.",
        "- `plots/by_pulse_width/`: direct three-buffer comparisons at each common width.",
        "",
        "## Data",
        "",
        "- `metrics.csv`: candidate errors and validity flags.",
        "- `summary_by_device.csv`: compact device/flow summary.",
        "- `native_ibis_coefficient_ranges.csv`: native HSPICE `Ku/Kd` extrema.",
        "- `response_vs_common_pulse_width.csv`: pad and coefficient trends versus width.",
        "- `transistor_gate_proxy_metrics.csv`: linear physical-gate proxy errors versus native Ku/Kd.",
        "- `edge_50ps_vs_100ps_response.csv`: direct slew sensitivity, when available.",
        "- `run_manifest.csv`: cache/run status and raw-result paths.",
        "- `runs/<device>/waveform_data/`: exact data behind every figure.",
        "",
        "## Headline Findings",
        "",
        "- `inv_chain` is effectively too fast for this pulse grid to create partial output behavior. "
        f"At 250 ps, transistor short-high/short-low responses are "
        f"`{100 * response('inv_chain', 'short_high', 250, 'hspice_transistor'):.1f}%` / "
        f"`{100 * response('inv_chain', 'short_low', 250, 'hspice_transistor'):.1f}%` of full swing.",
        "- `ex2` has a clear threshold between 500 ps and 1 ns. For short-high, the transistor "
        f"moves only `{100 * response('ex2', 'short_high', 500, 'hspice_transistor'):.1f}%` at 500 ps "
        f"but `{100 * response('ex2', 'short_high', 1000, 'hspice_transistor'):.1f}%` at 1 ns.",
        "- Native IBIS overpredicts sub-nanosecond `ex2` response. At 500 ps it predicts "
        f"`{100 * response('ex2', 'short_high', 500, 'hspice_native_ibis'):.1f}%` short-high and "
        f"`{100 * response('ex2', 'short_low', 500, 'hspice_native_ibis'):.1f}%` short-low, versus "
        f"transistor `{100 * response('ex2', 'short_high', 500, 'hspice_transistor'):.1f}%` and "
        f"`{100 * response('ex2', 'short_low', 500, 'hspice_transistor'):.1f}%`.",
        "- `io_buf` is strongly direction-asymmetric. At 250 ps, transistor short-high movement is "
        f"`{100 * response('io_buf', 'short_high', 250, 'hspice_transistor'):.1f}%`, while short-low "
        f"movement is `{100 * response('io_buf', 'short_low', 250, 'hspice_transistor'):.1f}%`.",
        "- Native IBIS underpredicts the fast `io_buf` short-low response: at 250 ps the native result "
        f"is `{100 * response('io_buf', 'short_low', 250, 'hspice_native_ibis'):.1f}%` versus "
        f"transistor `{100 * response('io_buf', 'short_low', 250, 'hspice_transistor'):.1f}%`.",
        "- All simulator runs completed, but completion is not validity. `io_buf` candidates retain "
        "coefficient discontinuity/envelope failures; `ex2` is strongest at 1-2 ns; and the hybrid "
        "often remains inactive for `inv_chain` because its final-stage transition has already settled.",
        "",
        "## Interpretation",
        "",
        "Using identical stimuli reveals the buffers' effective pulse filtering directly: "
        "`inv_chain` is fastest, `ex2` is intermediate, and `io_buf` has separate fast and slow "
        "directions. A common pulse cannot guarantee a mid-transition reversal in every buffer; "
        "that is a measured device result, not a defect in this study.",
        "",
        *slew_lines,
        "## Transistor Gate-Voltage Proxy",
        "",
        "The proxy uses the measured final-stage gate voltage to preserve physical timing:",
        "",
        "- `Ku_proxy = 1 - V(PMOS_gate)/VDD`.",
        "- `Kd_proxy = V(NMOS_gate)/VDD`.",
        "- For shared-gate output stages, both proxies come from the same gate voltage.",
        "",
        "This is a diagnostic proxy, not a true IBIS coefficient extraction. Gate voltage does "
        "not include transistor threshold, nonlinear transconductance, drain-voltage dependence, "
        "or parallel-device current sharing. Exact effective Ku/Kd requires probing pullup and "
        "pulldown currents separately and normalizing them against the corresponding static IBIS "
        "I-V tables at the instantaneous pad voltage.",
        "",
        "Measured median proxy RMSE (`Ku`, `Kd`):",
        "",
        f"- `io_buf`: `{proxy_summary['io_buf'][0]:.4f}`, `{proxy_summary['io_buf'][1]:.4f}`.",
        f"- `inv_chain`: `{proxy_summary['inv_chain'][0]:.4f}`, `{proxy_summary['inv_chain'][1]:.4f}`.",
        f"- `ex2`: `{proxy_summary['ex2'][0]:.4f}`, `{proxy_summary['ex2'][1]:.4f}`.",
        "",
        "The simple proxy is therefore genuinely informative for `inv_chain`, but not accurate "
        "enough to replace Ku/Kd for `io_buf` or `ex2`.",
        "",
        f"Numerical failures: `{len(failures)}`.",
    ]
    if failures:
        lines.extend(["", "## Numerical Failures", ""])
        for row in failures:
            lines.append(f"- `{row['device']} / {row['case_id']} / {row['flow']}`")
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="ascii")


def generate_reports() -> None:
    plot_common_inputs()
    response_rows = response_vs_width_rows()
    write_csv(OUT_DIR / "response_vs_common_pulse_width.csv", response_rows)
    plot_response_vs_width(response_rows)
    plot_native_coefficients_vs_width(response_rows)
    write_csv(OUT_DIR / "transistor_gate_proxy_metrics.csv", plot_transistor_gate_proxies())
    edge_slew_comparison()
    all_cases = cases()
    by_width: dict[tuple[str, float], list[Path]] = {}
    for device_index, device in enumerate(base.DEVICES, start=1):
        profile = profile_for(device)
        device_plots: list[Path] = []
        for case in all_cases:
            source = waveform_path(device, case)
            if not source.exists():
                continue
            data = read_waveform(source)
            output = plot_path(device, case)
            base.plot_case(
                device,
                profile,
                case,
                data,
                output,
                invert_transistor_controls=True,
            )
            device_plots.append(output)
            base.save_editable_recipes(device, profile, case, source)
            if case.pattern in {"short_high", "short_low"}:
                by_width.setdefault((case.pattern, case.pulse_width_ns), []).append(output)
        base.contact_sheet(
            device_plots,
            OUT_DIR / "plots" / f"0{device_index}_{device.device_id}_overview.png",
            columns=2,
        )

    for (direction, width_ns), paths in by_width.items():
        base.contact_sheet(
            paths,
            OUT_DIR
            / "plots"
            / "by_pulse_width"
            / f"{direction}_{base.width_tag(width_ns)}_three_buffers.png",
            columns=3,
        )

    metrics = [{key: value for key, value in row.items()} for row in base.read_csv(OUT_DIR / "metrics.csv")]
    run_rows = [{key: value for key, value in row.items()} for row in base.read_csv(OUT_DIR / "run_manifest.csv")]
    write_readme(metrics, run_rows)


def run(args: argparse.Namespace) -> None:
    all_metrics: list[dict[str, object]] = []
    run_manifest: list[dict[str, object]] = []
    all_cases = cases()

    for device in base.DEVICES:
        profile = profile_for(device)
        common_dir = OUT_DIR / "models" / device.device_id
        models = base.prepare_ngspice_models(device, profile, common_dir)
        for case_index, case in enumerate(all_cases, start=1):
            print(f"[{device.device_id} {case_index}/{len(all_cases)}] {case.case_id}", flush=True)
            transistor_raw, transistor_row = base.run_transistor(
                device,
                case,
                OUT_DIR / "runs",
                args.hspice,
                args.timeout_s,
            )
            native_raw, native_row = base.run_native_ibis(
                device,
                profile,
                case,
                OUT_DIR / "runs",
                args.hspice,
                args.timeout_s,
            )
            run_manifest.extend([transistor_row, native_row])

            transistor = base.transistor_waveform(device, transistor_raw)
            native = base.native_waveform(native_raw)
            flow_waves: dict[str, dict[str, np.ndarray] | None] = {}
            candidate_rows: list[dict[str, object]] = []
            for flow, mode in (("gate_state", base.FULL_MODE), ("hybrid", base.HYBRID_MODE)):
                raw, row = base.run_ngspice(
                    device,
                    profile,
                    case,
                    flow,
                    mode,
                    models[flow],
                    OUT_DIR / "runs",
                    args.ngspice,
                    args.timeout_s,
                )
                candidate_rows.append(row)
                run_manifest.append(row)
                flow_waves[flow] = base.ngspice_waveform(raw) if raw is not None else None

            data = base.aligned_data(device, case, transistor, native, flow_waves)
            wave_path = waveform_path(device, case)
            base.save_waveform(wave_path, data)
            all_metrics.extend(
                base.comparison_metrics(device, profile, case, data, candidate_rows)
            )
            write_csv(OUT_DIR / "metrics.csv", all_metrics)
            write_csv(OUT_DIR / "run_manifest.csv", run_manifest)

    write_csv(OUT_DIR / "summary_by_device.csv", summary_rows(all_metrics))
    write_csv(OUT_DIR / "native_ibis_coefficient_ranges.csv", native_range_rows(all_metrics))
    generate_reports()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Common-edge/common-pulse three-buffer study.")
    parser.add_argument("--hspice", type=Path, default=base.DEFAULT_HSPICE)
    parser.add_argument("--ngspice", type=Path, default=base.DEFAULT_NGSPICE)
    parser.add_argument("--timeout-s", type=int, default=180)
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--edge-ps", type=float, default=100.0)
    parser.add_argument("--study-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    global EDGE_NS, OUT_DIR
    args = parse_args()
    EDGE_NS = args.edge_ps * 1e-3
    if args.study_dir is not None:
        OUT_DIR = args.study_dir if args.study_dir.is_absolute() else ROOT / args.study_dir
    elif abs(args.edge_ps - 100.0) > 1e-9:
        OUT_DIR = (
            ROOT
            / "results"
            / f"three_buffer_common_pulse_sweep_edge{base.fmt(args.edge_ps)}ps_2026-07-30"
        )
    base.ensure_dir(OUT_DIR)
    if args.report_only:
        generate_reports()
        return 0
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
