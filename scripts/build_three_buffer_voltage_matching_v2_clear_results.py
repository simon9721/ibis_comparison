#!/usr/bin/env python3
"""Build a clear HSPICE/legacy/Voltage-Matching-V2 three-buffer comparison."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
for path in (LOCAL_DEPS, ROOT, ROOT / "scripts", ROOT / "tools" / "pybis2spice"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from eye_diagram import parse_hspice_tr0
from spice_tool_paths import default_ngspice
import run_three_buffer_pad_matched_replay as pad
import run_three_buffer_realistic_pulse_campaign as base


SOURCE_STUDY = ROOT / "results" / "three_buffer_single_true_output_reversal_2026-08-11"
LEGACY_STUDY = ROOT / "results" / "three_buffer_pad_matched_replay_v2_midtransition_2026-08-11"
DEFAULT_OUT = ROOT / "results" / "three_buffer_voltage_matching_v2_clear_results_2026-08-14"

PROFILE_ID = "fast_5ps"
LOAD_TAG = "r50_c2pf"
EDGE_NS = 0.050
LOAD_DESCRIPTION = "50 ohm || 2 pF"

BLACK = "#111111"
ORANGE = "#E69F00"
BLUE = "#0072B2"
INPUT = "#6B7280"
EDGE = "#666666"
GRID = "#D7DCE2"

FLOW_STYLES = {
    "hspice": {
        "label": "HSPICE native IBIS",
        "color": BLACK,
        "linewidth": 3.4,
        "linestyle": "-",
        "marker": None,
        "zorder": 2,
    },
    "legacy": {
        "label": "legacy pybis",
        "color": ORANGE,
        "linewidth": 2.3,
        "linestyle": "--",
        "marker": "o",
        "zorder": 3,
    },
    "v2": {
        "label": "Voltage-Matching V2",
        "color": BLUE,
        "linewidth": 2.0,
        "linestyle": "-",
        "marker": "D",
        "zorder": 4,
    },
}

DEVICE_LABELS = {
    "io_buf": "io_buf",
    "inv_chain": "inv_chain",
    "ex2": "ex2",
}


def ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    ensure(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_waveforms(path: Path, data: dict[str, np.ndarray]) -> None:
    fields = list(data)
    ensure(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(zip(*(data[field] for field in fields)))


def profile_for(device: base.Device) -> base.Profile:
    return base.Profile(PROFILE_ID, "fast-edge IBIS", device.fast_ibis)


def control_case() -> base.PulseCase:
    return base.PulseCase("long_control", EDGE_NS, "rise_fall", 10.0, 22.0, "full swing")


def selected_cases() -> dict[tuple[str, str], base.PulseCase]:
    rows = read_csv(SOURCE_STUDY / "selection.csv")
    cases: dict[tuple[str, str], base.PulseCase] = {}
    for row in rows:
        device_id = row["device"]
        direction = row["direction"]
        width_ns = float(row["pulse_width_ps"]) / 1000.0
        case_root = SOURCE_STUDY / "runs" / device_id / PROFILE_ID / LOAD_TAG
        matches = sorted(case_root.glob(f"{direction}_mid50_*/voltage_matching/run.raw"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one selected V2 raw for {device_id}/{direction}; got {matches}")
        case_id = matches[0].parents[1].name
        cases[(device_id, direction)] = base.PulseCase(
            case_id,
            EDGE_NS,
            direction,
            width_ns,
            22.0,
            f"true output-level {direction.replace('_', ' ')} reversal",
        )
    return cases


def source_paths(device: base.Device, case: base.PulseCase) -> tuple[Path, Path]:
    native = (
        SOURCE_STUDY
        / "hspice_references"
        / device.device_id
        / PROFILE_ID
        / LOAD_TAG
        / case.case_id
        / "native"
        / "run.tr0"
    )
    v2 = (
        SOURCE_STUDY
        / "runs"
        / device.device_id
        / PROFILE_ID
        / LOAD_TAG
        / case.case_id
        / "voltage_matching"
        / "run.raw"
    )
    if not native.exists() or not v2.exists():
        raise FileNotFoundError(f"Missing cached source for {device.device_id}/{case.case_id}")
    return native, v2


def existing_control_legacy(device: base.Device) -> Path:
    path = (
        LEGACY_STUDY
        / "runs"
        / device.device_id
        / PROFILE_ID
        / LOAD_TAG
        / "long_control"
        / "legacy"
        / "run.raw"
    )
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def legacy_model(device: base.Device) -> Path:
    path = (
        LEGACY_STUDY
        / "generated_models"
        / device.device_id
        / PROFILE_ID
        / "legacy"
        / f"{device.subckt}.sub"
    )
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def load_native(path: Path) -> dict[str, np.ndarray]:
    return base.native_waveform(parse_hspice_tr0(path))


def load_v2(path: Path) -> dict[str, np.ndarray]:
    return pad.parse_ng(path)


def load_legacy_control(device: base.Device) -> dict[str, np.ndarray]:
    return pad.parse_ng(existing_control_legacy(device))


def run_legacy_selected(
    out: Path,
    device: base.Device,
    case: base.PulseCase,
    ngspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    profile = profile_for(device)
    raw, row = base.run_ngspice(
        device,
        profile,
        case,
        "legacy",
        "InputDriven",
        legacy_model(device),
        out / "legacy_runs",
        ngspice,
        timeout_s,
    )
    if raw is None:
        raise RuntimeError(f"Legacy ngspice failed for {device.device_id}/{case.case_id}: {row}")
    return base.ngspice_waveform(raw), row


def align(
    native: dict[str, np.ndarray],
    legacy: dict[str, np.ndarray],
    v2: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    time_ns = np.asarray(native["time_ns"], dtype=float)
    result: dict[str, np.ndarray] = {
        "time_ns": time_ns,
        "input_v": np.asarray(native["input_v"], dtype=float),
    }
    for flow, wave in (("hspice", native), ("legacy", legacy), ("v2", v2)):
        for signal in ("pad_v", "ku", "kd"):
            result[f"{flow}_{signal}"] = np.interp(
                time_ns,
                np.asarray(wave["time_ns"], dtype=float),
                np.asarray(wave[signal], dtype=float),
            )
    for diagnostic in ("padsamp", "pmsample", "pmlatchpulse", "padmapactive", "padarg"):
        values = v2.get(diagnostic)
        if values is not None:
            result[f"v2_{diagnostic}"] = np.interp(
                time_ns,
                np.asarray(v2["time_ns"], dtype=float),
                np.asarray(values, dtype=float),
            )
    return result


def active_window(case: base.PulseCase, device: base.Device) -> tuple[float, float]:
    edges = base.command_edges(device, case)
    if case.pattern == "rise_fall":
        return edges[0] - 0.75, edges[-1] + 4.5
    return edges[-2] - 0.75, edges[-1] + 5.0


def active_mask(case: base.PulseCase, device: base.Device, time_ns: np.ndarray) -> np.ndarray:
    start, stop = active_window(case, device)
    return (time_ns >= start) & (time_ns <= stop)


def rmse(reference: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(reference[mask] - candidate[mask]))))


def metric_rows(
    device: base.Device,
    case_role: str,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    mask = active_mask(case, device, data["time_ns"])
    rows: list[dict[str, object]] = []
    for flow in ("legacy", "v2"):
        row: dict[str, object] = {
            "device": device.device_id,
            "case_role": case_role,
            "case_id": case.case_id,
            "pulse_width_ps": "" if case_role == "full_swing" else 1000.0 * case.pulse_width_ns,
            "flow": "legacy_pybis" if flow == "legacy" else "voltage_matching_v2",
        }
        for signal in ("pad_v", "ku", "kd"):
            scale = 1000.0 if signal == "pad_v" else 1.0
            suffix = "pad_rmse_mv" if signal == "pad_v" else f"{signal}_rmse"
            max_suffix = "pad_max_error_mv" if signal == "pad_v" else f"{signal}_max_error"
            difference = data[f"{flow}_{signal}"] - data[f"hspice_{signal}"]
            row[suffix] = scale * rmse(data[f"hspice_{signal}"], data[f"{flow}_{signal}"], mask)
            row[max_suffix] = scale * float(np.max(np.abs(difference[mask])))
        rows.append(row)
    return rows


def comparison_rows(
    device: base.Device,
    case_role: str,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
) -> dict[str, object]:
    mask = active_mask(case, device, data["time_ns"])
    row: dict[str, object] = {
        "device": device.device_id,
        "case_role": case_role,
        "case_id": case.case_id,
        "pulse_width_ps": "" if case_role == "full_swing" else 1000.0 * case.pulse_width_ns,
    }
    for signal in ("pad_v", "ku", "kd"):
        scale = 1000.0 if signal == "pad_v" else 1.0
        units = "mv" if signal == "pad_v" else ""
        suffix = f"_{units}" if units else ""
        legacy_error = rmse(data[f"hspice_{signal}"], data[f"legacy_{signal}"], mask)
        v2_error = rmse(data[f"hspice_{signal}"], data[f"v2_{signal}"], mask)
        row[f"v2_vs_legacy_{signal}_rmse{suffix}"] = scale * rmse(
            data[f"legacy_{signal}"], data[f"v2_{signal}"], mask
        )
        row[f"legacy_vs_hspice_{signal}_rmse{suffix}"] = scale * legacy_error
        row[f"v2_vs_hspice_{signal}_rmse{suffix}"] = scale * v2_error
        row[f"v2_improvement_vs_legacy_{signal}_percent"] = (
            100.0 * (legacy_error - v2_error) / legacy_error
            if legacy_error > 1e-15 else 0.0
        )
    if case_role == "full_swing":
        row["result"] = "FULL_SWING_EQUIVALENCE_CHECK"
    else:
        improvements = [
            float(row[f"v2_improvement_vs_legacy_{signal}_percent"])
            for signal in ("pad_v", "ku", "kd")
        ]
        if all(value > 0.0 for value in improvements):
            row["result"] = "V2_IMPROVES_PAD_KU_KD"
        elif improvements[0] > 0.0:
            row["result"] = "PAD_IMPROVES_WITH_COEFFICIENT_TRADEOFF"
        else:
            row["result"] = "V2_NOT_BETTER_OVERALL"
    return row


def sample_time(data: dict[str, np.ndarray], reverse_ns: float) -> float | None:
    pulse = data.get("v2_pmsample")
    if pulse is None or not np.any(np.isfinite(pulse)):
        return None
    mask = data["time_ns"] >= reverse_ns - 0.01
    if not np.any(mask):
        return None
    indexes = np.flatnonzero(mask)
    local = pulse[indexes]
    peak = float(np.nanmax(local))
    if peak <= 0.05:
        return None
    hits = indexes[local >= 0.5 * peak]
    return None if len(hits) == 0 else float(data["time_ns"][hits[0]])


def plot_trace(ax: plt.Axes, time_ns: np.ndarray, values: np.ndarray, flow: str, markevery: int) -> None:
    style = FLOW_STYLES[flow]
    ax.plot(
        time_ns,
        values,
        label=style["label"],
        color=style["color"],
        linewidth=style["linewidth"],
        linestyle=style["linestyle"],
        marker=style["marker"],
        markevery=markevery if style["marker"] else None,
        markersize=3.8,
        markerfacecolor="white",
        markeredgewidth=1.2,
        zorder=style["zorder"],
    )


def plot_case(
    out: Path,
    device: base.Device,
    case_role: str,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
) -> Path:
    start_ns, stop_ns = active_window(case, device)
    mask = (data["time_ns"] >= start_ns) & (data["time_ns"] <= stop_ns)
    time_ns = data["time_ns"][mask]
    stride = max(1, len(time_ns) // 55)
    edges = base.command_edges(device, case)

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(15.0, 10.8),
        sharex=True,
        gridspec_kw={"height_ratios": [0.65, 1.35, 1.0, 1.0]},
    )
    axes[0].plot(time_ns, data["input_v"][mask], color=INPUT, linewidth=2.2)
    axes[0].set_ylabel("Input\n(V)")

    for axis, signal, ylabel in (
        (axes[1], "pad_v", "Pad voltage\n(V)"),
        (axes[2], "ku", "Ku"),
        (axes[3], "kd", "Kd"),
    ):
        for flow in ("hspice", "legacy", "v2"):
            plot_trace(axis, time_ns, data[f"{flow}_{signal}"][mask], flow, stride)
        axis.set_ylabel(ylabel)
    axes[2].axhline(0.0, color="#A7ADB5", linewidth=0.9)
    axes[3].axhline(0.0, color="#A7ADB5", linewidth=0.9)

    if case.pattern == "rise_fall":
        shown_edges = edges
        edge_labels = ("rising command", "falling command")
    else:
        shown_edges = edges[-2:]
        edge_labels = ("first edge", "reverse edge")
    close_edges = len(shown_edges) == 2 and abs(shown_edges[1] - shown_edges[0]) < 0.5
    for edge_index, (edge_ns, edge_label) in enumerate(zip(shown_edges, edge_labels)):
        for axis in axes:
            axis.axvline(edge_ns, color=EDGE, linestyle="--", linewidth=1.15, zorder=1)
        axes[0].text(
            edge_ns,
            1.02,
            edge_label,
            transform=axes[0].get_xaxis_transform(),
            ha=("right" if edge_index == 0 else "left") if close_edges else "center",
            va="bottom",
            fontsize=9,
            color="#4B5563",
        )

    if case.pattern != "rise_fall":
        reverse_ns = edges[-1]
        sampled_at = sample_time(data, reverse_ns)
        if sampled_at is not None and start_ns <= sampled_at <= stop_ns:
            for axis in axes:
                axis.axvline(sampled_at, color=BLUE, linestyle=":", linewidth=1.45, zorder=1)
            sampled_v = float(np.interp(sampled_at, data["time_ns"], data["v2_pad_v"]))
            axes[1].scatter(
                [sampled_at],
                [sampled_v],
                marker="X",
                s=74,
                color=BLUE,
                edgecolor="white",
                linewidth=0.9,
                zorder=6,
                label="V2 sample",
            )

    for axis in axes:
        axis.set_xlim(start_ns, stop_ns)
        axis.grid(True, color=GRID, linewidth=0.75, alpha=0.75)
        axis.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("Time (ns)")

    if case_role == "full_swing":
        detail = "full-swing control"
    else:
        direction = "short-high" if case.pattern == "short_high" else "short-low"
        detail = f"{direction} midpoint reversal, {1000.0 * case.pulse_width_ns:.1f} ps pulse"
    fig.suptitle(
        f"{DEVICE_LABELS[device.device_id]} | {detail}",
        fontsize=17,
        fontweight="bold",
        y=0.992,
    )
    fig.text(0.5, 0.962, f"50 ps command edges | {LOAD_DESCRIPTION}", ha="center", fontsize=10.5, color="#4B5563")

    handles, labels = axes[1].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(
        by_label.values(),
        by_label.keys(),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.943),
        ncol=4,
        frameon=False,
        fontsize=10.5,
    )
    fig.tight_layout(rect=(0.045, 0.04, 0.99, 0.915), h_pad=0.48)

    direction_folder = {
        "full_swing": "full_swing",
        "short_high": "interrupted_short_high",
        "short_low": "interrupted_short_low",
    }[case_role]
    path = out / "figures" / direction_folder / f"{device.device_id}.png"
    ensure(path.parent)
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    return path


def contact_sheet(paths: list[Path], output: Path, title: str, columns: int = 3) -> None:
    rows = int(np.ceil(len(paths) / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(7.7 * columns, 5.7 * rows), squeeze=False)
    for axis, path in zip(axes.ravel(), paths):
        axis.imshow(plt.imread(path))
        axis.axis("off")
    for axis in axes.ravel()[len(paths):]:
        axis.axis("off")
    fig.suptitle(title, fontsize=22, fontweight="bold", y=0.995)
    fig.tight_layout(rect=(0.005, 0.005, 0.995, 0.975), pad=0.5)
    ensure(output.parent)
    fig.savefig(output, dpi=115, facecolor="white")
    plt.close(fig)


def write_readme(
    out: Path,
    metrics: list[dict[str, object]],
    comparisons: list[dict[str, object]],
) -> None:
    def row(device: str, role: str, flow: str) -> dict[str, object]:
        return next(
            item for item in metrics
            if item["device"] == device and item["case_role"] == role and item["flow"] == flow
        )

    def comparison(device: str, role: str) -> dict[str, object]:
        return next(
            item for item in comparisons
            if item["device"] == device and item["case_role"] == role
        )

    lines = [
        "# Voltage-Matching V2: Clear Three-Buffer Results",
        "",
        "This package compares exactly three simulator/model flows under the same `50 ohm || 2 pF` load and `50 ps` command edges:",
        "",
        "- HSPICE native IBIS: coefficient and pad reference.",
        "- ngspice legacy pybis: ordinary elapsed-time Ku/Kd replay.",
        "- ngspice Voltage-Matching V2: pad-voltage snapshot mapped to a shared opposite-table Ku/Kd start time.",
        "",
        "HSPICE data are read from the existing cache. Only the six exact-width legacy ngspice reversal cases are simulated for this package.",
        "",
        "## Full-Swing Control",
        "",
        "The full-swing cases establish the non-interrupted baseline. They directly measure how much the V2 replay transaction changes an otherwise settled rise/fall sequence.",
        "",
        "| Buffer | Legacy pad RMSE (mV) | V2 pad RMSE (mV) | Legacy Ku/Kd RMSE | V2 Ku/Kd RMSE |",
        "|---|---:|---:|---:|---:|",
    ]
    for device in DEVICE_LABELS:
        legacy = row(device, "full_swing", "legacy_pybis")
        v2 = row(device, "full_swing", "voltage_matching_v2")
        lines.append(
            f"| {device} | {legacy['pad_rmse_mv']:.3f} | {v2['pad_rmse_mv']:.3f} | "
            f"{max(legacy['ku_rmse'], legacy['kd_rmse']):.5f} | "
            f"{max(v2['ku_rmse'], v2['kd_rmse']):.5f} |"
        )

    lines.extend([
        "",
        "Direct V2-versus-legacy full-swing difference:",
        "",
        "| Buffer | Pad RMSE (mV) | Ku RMSE | Kd RMSE |",
        "|---|---:|---:|---:|",
    ])
    for device in DEVICE_LABELS:
        item = comparison(device, "full_swing")
        lines.append(
            f"| {device} | {item['v2_vs_legacy_pad_v_rmse_mv']:.3f} | "
            f"{item['v2_vs_legacy_ku_rmse']:.5f} | {item['v2_vs_legacy_kd_rmse']:.5f} |"
        )

    lines.extend([
        "",
        "## Interrupted Cases",
        "",
        "These are true output-level midpoint reversals selected separately for each buffer. V2 is judged from pad, Ku, and Kd together; a pad-only improvement is not a coefficient-correct result.",
        "",
        "| Buffer | Direction | Pulse (ps) | Flow | Pad RMSE (mV) | Ku RMSE | Kd RMSE |",
        "|---|---|---:|---|---:|---:|---:|",
    ])
    for device in DEVICE_LABELS:
        for role in ("short_high", "short_low"):
            for flow in ("legacy_pybis", "voltage_matching_v2"):
                item = row(device, role, flow)
                lines.append(
                    f"| {device} | {role.replace('_', '-')} | {float(item['pulse_width_ps']):.1f} | "
                    f"{flow} | {item['pad_rmse_mv']:.3f} | {item['ku_rmse']:.5f} | {item['kd_rmse']:.5f} |"
                )

    lines.extend([
        "",
        "## Finding",
        "",
        "- Full swing: V2 is nearly identical to legacy for `inv_chain` and `ex2`; `io_buf` shows a larger Ku difference around the settled reverse edge.",
        "- `io_buf` short-low: V2 improves pad, Ku, and Kd together. This is the clearest positive case.",
        "- `inv_chain` and `ex2` short-high: V2 improves all three metrics, but only modestly and the absolute disagreement remains large.",
        "- `io_buf` short-high: pad and Ku improve, but Kd worsens. This is not coefficient-correct overall.",
        "- `inv_chain` and `ex2` short-low: Kd improves while pad and/or Ku become worse. The single sampled pad voltage does not identify a universally correct opposite-table state.",
        "",
        "Overall: Voltage-Matching V2 is a useful directional baseline, not a general interrupted-transition solution.",
    ])

    lines.extend([
        "",
        "## How To Read The Figures",
        "",
        "- Thick black is HSPICE native IBIS; orange circles are legacy pybis; blue diamonds are Voltage-Matching V2.",
        "- Dashed gray lines are the first and reverse input commands.",
        "- The blue dotted line and X marker identify the V2 voltage-sampling event when available.",
        "- Full-swing control is shown first, followed by short-high and short-low midpoint reversals.",
        "",
        "## Files",
        "",
        "- `01_full_swing_contact_sheet.png`",
        "- `02_interrupted_short_high_contact_sheet.png`",
        "- `03_interrupted_short_low_contact_sheet.png`",
        "- `04_all_results_contact_sheet.png`",
        "- `figures/`: one full-resolution PNG per buffer and case role.",
        "- `waveforms/`: aligned numerical data behind every figure.",
        "- `metrics.csv`: active-window errors against HSPICE native IBIS.",
        "- `v2_vs_legacy_summary.csv`: direct full-swing equivalence and interrupted-case improvement/tradeoff classification.",
        "- `source_manifest.csv`: exact cached/rerun provenance.",
    ])
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    parser.add_argument("--timeout-s", type=int, default=300)
    args = parser.parse_args()

    out = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out = out.resolve()
    ensure(out)

    cases = selected_cases()
    metrics: list[dict[str, object]] = []
    comparisons: list[dict[str, object]] = []
    sources: list[dict[str, object]] = []
    figures: dict[str, list[Path]] = {"full_swing": [], "short_high": [], "short_low": []}

    for device in base.DEVICES:
        profile = profile_for(device)
        for role in ("full_swing", "short_high", "short_low"):
            case = control_case() if role == "full_swing" else cases[(device.device_id, role)]
            native_path, v2_path = source_paths(device, case)
            native = load_native(native_path)
            v2 = load_v2(v2_path)
            if role == "full_swing":
                legacy_path = existing_control_legacy(device)
                legacy = load_legacy_control(device)
                legacy_source = "existing_raw"
            else:
                legacy, legacy_row = run_legacy_selected(out, device, case, args.ngspice, args.timeout_s)
                legacy_path = ROOT / str(legacy_row["raw"])
                legacy_source = str(legacy_row["source"])

            data = align(native, legacy, v2)
            write_waveforms(out / "waveforms" / role / f"{device.device_id}.csv", data)
            metrics.extend(metric_rows(device, role, case, data))
            comparisons.append(comparison_rows(device, role, case, data))
            figures[role].append(plot_case(out, device, role, case, data))
            sources.extend([
                {
                    "device": device.device_id,
                    "case_role": role,
                    "case_id": case.case_id,
                    "flow": "hspice_native_ibis",
                    "source": "cached_existing_tr0",
                    "path": str(native_path.relative_to(ROOT)),
                },
                {
                    "device": device.device_id,
                    "case_role": role,
                    "case_id": case.case_id,
                    "flow": "legacy_pybis",
                    "source": legacy_source,
                    "path": str(legacy_path.relative_to(ROOT)),
                },
                {
                    "device": device.device_id,
                    "case_role": role,
                    "case_id": case.case_id,
                    "flow": "voltage_matching_v2",
                    "source": "cached_existing_raw",
                    "path": str(v2_path.relative_to(ROOT)),
                },
            ])
            print(f"[{device.device_id}] {role}: complete", flush=True)

    write_csv(out / "metrics.csv", metrics)
    write_csv(out / "v2_vs_legacy_summary.csv", comparisons)
    write_csv(out / "source_manifest.csv", sources)
    contact_sheet(figures["full_swing"], out / "01_full_swing_contact_sheet.png", "Full-Swing Control")
    contact_sheet(
        figures["short_high"],
        out / "02_interrupted_short_high_contact_sheet.png",
        "Interrupted Short-High Midpoint Reversal",
    )
    contact_sheet(
        figures["short_low"],
        out / "03_interrupted_short_low_contact_sheet.png",
        "Interrupted Short-Low Midpoint Reversal",
    )
    contact_sheet(
        figures["full_swing"] + figures["short_high"] + figures["short_low"],
        out / "04_all_results_contact_sheet.png",
        "Voltage-Matching V2: HSPICE vs Legacy vs V2",
        columns=3,
    )
    write_readme(out, metrics, comparisons)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
