#!/usr/bin/env python3
"""Build focused mid-transition evidence for pad-voltage-matched replay v2."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
for path in (LOCAL_DEPS, ROOT / "scripts"):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_STUDY = ROOT / "results" / "three_buffer_pad_matched_replay_v2_midtransition_2026-08-11"
DEFAULT_INV_CHAIN_CUSTOM_STUDY = ROOT / "results" / "three_buffer_pad_matched_replay_v2_inv_chain_custom_2026-08-11"
DEVICES = ("io_buf", "inv_chain", "ex2")
DIRECTIONS = ("short_high", "short_low")
PROFILES = ("slow_1ns", "fast_5ps")
WIDTHS = ("250ps", "500ps", "1ns", "2ns")

BLACK = "#111111"
GRAY = "#777777"
RED = "#CC3311"
BLUE = "#0072B2"
PURPLE = "#7B2CBF"
GRID = "#D9DEE5"


@dataclass
class Selection:
    device: str
    direction: str
    profile: str
    case_id: str
    width_ns: float
    first_edge_ns: float
    reverse_edge_ns: float
    native_ku_at_reverse: float
    native_kd_at_reverse: float
    native_ku_progress: float
    native_kd_progress: float
    native_progress: float
    map_triggered: bool
    mapping_ambiguous: bool
    event_start_span_ns: float
    waveform_path: Path
    source_study: Path
    metric: dict[str, str]
    legacy_metric: dict[str, str]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_wave(path: Path) -> dict[str, np.ndarray]:
    rows = read_rows(path)
    if not rows:
        raise RuntimeError(f"empty waveform: {path}")
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
        if row_value_is_numeric(rows[0].get(key, ""))
    }


def row_value_is_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def interp(data: dict[str, np.ndarray], key: str, time_ns: float) -> float:
    return float(np.interp(time_ns, data["time_ns"], data[key]))


def endpoint_states(long_wave: dict[str, np.ndarray]) -> tuple[float, float, float, float]:
    time_ns = long_wave["time_ns"]
    low_mask = (time_ns >= 1.0) & (time_ns <= 4.0)
    high_mask = (time_ns >= 10.0) & (time_ns <= 14.0)
    return (
        float(np.median(long_wave["hspice_native_ku"][low_mask])),
        float(np.median(long_wave["hspice_native_kd"][low_mask])),
        float(np.median(long_wave["hspice_native_ku"][high_mask])),
        float(np.median(long_wave["hspice_native_kd"][high_mask])),
    )


def normalized(value: float, start: float, end: float) -> float:
    scale = end - start
    return (value - start) / scale if abs(scale) > 1e-9 else float("nan")


def case_times(direction: str, width_ns: float) -> tuple[float, float]:
    edge_ns = 0.050
    if direction == "short_high":
        return 5.0 + 0.5 * edge_ns, 5.0 + width_ns + 0.5 * edge_ns
    return 10.0 + 0.5 * edge_ns, 10.0 + width_ns + 0.5 * edge_ns


def width_from_case_id(case_id: str) -> float:
    tag = case_id.rsplit("_", 1)[-1]
    if tag.endswith("ps"):
        return float(tag[:-2]) / 1000.0
    if tag.endswith("ns"):
        return float(tag[:-2])
    raise ValueError(f"cannot parse pulse width from {case_id}")


def choose_cases(
    study: Path,
    metrics: list[dict[str, str]],
    inv_chain_custom_study: Path | None,
) -> tuple[list[Selection], list[Selection]]:
    metric_indices = {study: {
        (row["device"], row["profile"], row["case_id"], row["flow"]): row
        for row in metrics
        if row.get("load_ohm") == "50.0" and row.get("load_pf") == "2.0"
    }}
    if inv_chain_custom_study and (inv_chain_custom_study / "candidate_metrics.csv").exists():
        custom_metrics = read_rows(inv_chain_custom_study / "candidate_metrics.csv")
        metric_indices[inv_chain_custom_study] = {
            (row["device"], row["profile"], row["case_id"], row["flow"]): row
            for row in custom_metrics
            if row.get("load_ohm") == "50.0" and row.get("load_pf") == "2.0"
        }
    selections: list[Selection] = []
    all_candidates: list[Selection] = []
    for device in DEVICES:
        candidates_by_direction: dict[str, list[Selection]] = {key: [] for key in DIRECTIONS}
        candidate_sources: list[tuple[Path, str, str, float]] = []
        if device == "inv_chain" and inv_chain_custom_study in metric_indices:
            custom_wave_dir = inv_chain_custom_study / "waveform_data" / device / "fast_5ps" / "r50_c2pf"
            for direction in DIRECTIONS:
                for wave_path in sorted(custom_wave_dir.glob(f"{direction}_custom_*.csv")):
                    candidate_sources.append((
                        inv_chain_custom_study,
                        "fast_5ps",
                        wave_path.stem,
                        width_from_case_id(wave_path.stem),
                    ))
        else:
            for profile in PROFILES:
                for direction in DIRECTIONS:
                    for width_tag in WIDTHS:
                        width_ns = {"250ps": 0.25, "500ps": 0.5, "1ns": 1.0, "2ns": 2.0}[width_tag]
                        candidate_sources.append((study, profile, f"{direction}_{width_tag}", width_ns))

        for source_study, profile, case_id, width_ns in candidate_sources:
            long_path = study / "waveform_data" / device / profile / "r50_c2pf" / "long_control.csv"
            long_wave = read_wave(long_path)
            ku_low, kd_low, ku_high, kd_high = endpoint_states(long_wave)
            direction = "short_high" if case_id.startswith("short_high") else "short_low"
            wave_path = source_study / "waveform_data" / device / profile / "r50_c2pf" / f"{case_id}.csv"
            wave = read_wave(wave_path)
            first_edge, reverse_edge = case_times(direction, width_ns)
            sample_time = reverse_edge - 0.002
            ku_reverse = interp(wave, "hspice_native_ku", sample_time)
            kd_reverse = interp(wave, "hspice_native_kd", sample_time)
            if direction == "short_high":
                ku_progress = normalized(ku_reverse, ku_low, ku_high)
                kd_progress = normalized(kd_reverse, kd_low, kd_high)
            else:
                ku_progress = normalized(ku_reverse, ku_high, ku_low)
                kd_progress = normalized(kd_reverse, kd_high, kd_low)
            progress = float(np.nanmean([ku_progress, kd_progress]))
            metric_index = metric_indices[source_study]
            metric = metric_index[(device, profile, case_id, "pad_voltage")]
            legacy = metric_index[(device, profile, case_id, "legacy")]
            selection = Selection(
                device=device,
                direction=direction,
                profile=profile,
                case_id=case_id,
                width_ns=width_ns,
                first_edge_ns=first_edge,
                reverse_edge_ns=reverse_edge,
                native_ku_at_reverse=ku_reverse,
                native_kd_at_reverse=kd_reverse,
                native_ku_progress=ku_progress,
                native_kd_progress=kd_progress,
                native_progress=progress,
                map_triggered=str(metric.get("pad_map_triggered", "")).lower() == "true",
                mapping_ambiguous=str(metric.get("mapping_ambiguous", "")).lower() == "true",
                event_start_span_ns=float(metric.get("event_start_span_ns") or 0.0),
                waveform_path=wave_path,
                source_study=source_study,
                metric=metric,
                legacy_metric=legacy,
            )
            candidates_by_direction[direction].append(selection)
            all_candidates.append(selection)
        for direction in DIRECTIONS:
            candidates = candidates_by_direction[direction]
            confirmed = [
                item for item in candidates
                if item.map_triggered and 0.10 <= item.native_progress <= 0.90
            ]
            pool = confirmed or [item for item in candidates if item.map_triggered] or candidates
            selections.append(min(pool, key=lambda item: abs(item.native_progress - 0.5)))
    return selections, all_candidates


def active_window(selection: Selection, wave: dict[str, np.ndarray]) -> np.ndarray:
    time_ns = wave["time_ns"]
    start = selection.first_edge_ns - 0.50
    search = time_ns >= selection.first_edge_ns
    active_end = selection.reverse_edge_ns + 0.75
    for key in (
        "input_v", "hspice_native_pad_v", "hspice_transistor_pad_v", "pad_voltage_pad_v",
        "hspice_native_ku", "hspice_native_kd", "pad_voltage_ku", "pad_voltage_kd",
    ):
        values = wave[key]
        tail = values[time_ns >= max(selection.reverse_edge_ns + 0.5, float(time_ns[-1]) - 2.0)]
        final = float(np.median(tail)) if tail.size else float(values[-1])
        scale = max(float(np.ptp(values[search])), 1.0)
        unsettled = search & (np.abs(values - final) > 0.01 * scale)
        if np.any(unsettled):
            active_end = max(active_end, float(time_ns[np.flatnonzero(unsettled)[-1]]) + 0.35)
    end = min(float(time_ns[-1]), selection.reverse_edge_ns + 5.0, active_end)
    return (wave["time_ns"] >= start) & (wave["time_ns"] <= end)


def style_axis(axis: plt.Axes) -> None:
    axis.grid(True, color=GRID, lw=0.8, alpha=0.7)
    axis.spines[["top", "right"]].set_visible(False)


def plot_case(selection: Selection, output: Path) -> None:
    wave = read_wave(selection.waveform_path)
    mask = active_window(selection, wave)
    t = wave["time_ns"][mask] - selection.first_edge_ns
    first = 0.0
    reverse = selection.reverse_edge_ns - selection.first_edge_ns
    fig, axes = plt.subplots(4, 1, figsize=(14.5, 11.5), sharex=True, constrained_layout=True)
    axes[0].plot(t, wave["input_v"][mask], color=BLUE, lw=2.0, label="input")
    axes[0].set_ylabel("input (V)")
    axes[1].plot(t, wave["hspice_native_pad_v"][mask], color=BLACK, lw=4.0, alpha=0.82, label="HSPICE native IBIS")
    axes[1].plot(t, wave["hspice_transistor_pad_v"][mask], color=GRAY, lw=3.0, alpha=0.82, label="HSPICE transistor")
    axes[1].plot(t, wave["pad_voltage_pad_v"][mask], color=RED, lw=2.1, label="pad-match v2")
    axes[1].set_ylabel("pad (V)")
    axes[2].plot(t, wave["hspice_native_ku"][mask], color=BLACK, lw=4.0, alpha=0.82, label="HSPICE native IBIS")
    axes[2].plot(t, wave["pad_voltage_ku"][mask], color=RED, lw=2.1, label="pad-match v2")
    axes[2].set_ylabel("Ku")
    axes[3].plot(t, wave["hspice_native_kd"][mask], color=BLACK, lw=4.0, alpha=0.82, label="HSPICE native IBIS")
    axes[3].plot(t, wave["pad_voltage_kd"][mask], color=RED, lw=2.1, label="pad-match v2")
    axes[3].axhline(0.0, color="#999999", lw=0.8)
    axes[3].set_ylabel("Kd")
    axes[3].set_xlabel("time from first stressed edge (ns)")
    for axis in axes:
        axis.axvline(first, color="#666666", lw=1.2, ls="--")
        axis.axvline(reverse, color=PURPLE, lw=1.4, ls="--")
        style_axis(axis)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.985, 0.985), ncol=3, frameon=True)
    direction_label = selection.direction.replace("_", "-")
    fig.suptitle(
        f"{selection.device} | {direction_label} stress | {selection.width_ns:g} ns pulse",
        fontsize=17,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_diagnostics(selections: list[Selection], output: Path) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(15.5, 10.5), sharex="col", constrained_layout=True)
    for column, selection in enumerate(selections):
        wave = read_wave(selection.waveform_path)
        mask = active_window(selection, wave)
        t = wave["time_ns"][mask] - selection.first_edge_ns
        reverse = selection.reverse_edge_ns - selection.first_edge_ns
        axes[0, column].plot(t, wave["pad_voltage_pad_v"][mask], color=RED, lw=2.0, label="pad")
        axes[0, column].plot(t, wave["pad_voltage_padsamp"][mask], color=BLUE, lw=1.8, label="latched pad sample")
        axes[0, column].set_ylabel("voltage (V)")
        axes[1, column].plot(t, wave["pad_voltage_padstart_latch"][mask], color=PURPLE, lw=2.0, label="inferred start")
        axes[1, column].plot(t, wave["pad_voltage_padarg"][mask], color=RED, lw=1.8, label="replay argument")
        axes[1, column].set_ylabel("table time (ns)")
        axes[2, column].plot(t, wave["pad_voltage_padmapactive"][mask], color="#009E73", lw=2.0, label="pad map active")
        axes[2, column].plot(t, wave["pad_voltage_padmatch_ambiguous"][mask], color="#E69F00", lw=1.8, label="ambiguous")
        axes[2, column].set_ylabel("flag")
        axes[2, column].set_xlabel("time from first stressed edge (ns)")
        for row in range(3):
            axes[row, column].axvline(0.0, color="#666666", lw=1.1, ls="--")
            axes[row, column].axvline(reverse, color=PURPLE, lw=1.3, ls="--")
            style_axis(axes[row, column])
        axes[0, column].set_title(selection.direction.replace("_", "-"))
    for row in range(3):
        handles, labels = axes[row, 0].get_legend_handles_labels()
        axes[row, 0].legend(handles, labels, loc="best", fontsize=9)
    fig.suptitle(f"{selections[0].device} | pad-match v2 diagnostics", fontsize=17)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_contact_sheet(selections: list[Selection], output: Path) -> None:
    by_key = {(item.device, item.direction): item for item in selections}
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    for row, device in enumerate(DEVICES):
        for column, direction in enumerate(DIRECTIONS):
            selection = by_key[(device, direction)]
            wave = read_wave(selection.waveform_path)
            mask = active_window(selection, wave)
            t = wave["time_ns"][mask] - selection.first_edge_ns
            axis = axes[row, column]
            axis.plot(t, wave["hspice_native_pad_v"][mask], color=BLACK, lw=4.0, alpha=0.82, label="HSPICE native IBIS")
            axis.plot(t, wave["hspice_transistor_pad_v"][mask], color=GRAY, lw=2.7, alpha=0.82, label="HSPICE transistor")
            axis.plot(t, wave["pad_voltage_pad_v"][mask], color=RED, lw=2.0, label="pad-match v2")
            axis.axvline(0.0, color="#666666", lw=1.0, ls="--")
            axis.axvline(selection.reverse_edge_ns - selection.first_edge_ns, color=PURPLE, lw=1.2, ls="--")
            axis.set_title(f"{device} | {direction.replace('_', '-')} | {selection.width_ns:g} ns pulse")
            axis.set_ylabel("pad (V)")
            axis.set_xlabel("time from first stressed edge (ns)")
            style_axis(axis)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.suptitle("Pad-voltage-matched replay v2 | mid-transition stress", fontsize=18, y=0.985)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=3, frameon=True)
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.06, top=0.90, hspace=0.42, wspace=0.12)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def focused_wave_rows(selection: Selection) -> list[dict[str, object]]:
    wave = read_wave(selection.waveform_path)
    mask = active_window(selection, wave)
    keys = (
        "time_ns", "input_v", "hspice_native_pad_v", "hspice_native_ku", "hspice_native_kd",
        "hspice_transistor_pad_v", "legacy_pad_v", "legacy_ku", "legacy_kd",
        "pad_voltage_pad_v", "pad_voltage_ku", "pad_voltage_kd", "pad_voltage_padsamp",
        "pad_voltage_padstart_latch", "pad_voltage_padarg", "pad_voltage_padmapactive",
        "pad_voltage_padmatch_ambiguous",
    )
    indices = np.flatnonzero(mask)
    return [
        {key: float(wave[key][index]) for key in keys}
        for index in indices
    ]


def metric_value(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return float("nan")


def write_report(
    study: Path,
    selections: list[Selection],
    all_candidates: list[Selection],
    output: Path,
) -> None:
    rows: list[dict[str, object]] = []
    for selection in selections:
        rows.append({
            "device": selection.device,
            "direction": selection.direction,
            "profile": selection.profile,
            "case_id": selection.case_id,
            "pulse_width_ns": selection.width_ns,
            "native_progress_at_reverse": selection.native_progress,
            "native_ku_at_reverse": selection.native_ku_at_reverse,
            "native_kd_at_reverse": selection.native_kd_at_reverse,
            "native_ku_progress_at_reverse": selection.native_ku_progress,
            "native_kd_progress_at_reverse": selection.native_kd_progress,
            "pad_map_triggered": selection.map_triggered,
            "mapping_ambiguous": selection.mapping_ambiguous,
            "event_start_span_ns": selection.event_start_span_ns,
            "v2_classification": selection.metric.get("classification", ""),
            "v2_pad_rmse_mv": metric_value(selection.metric, "pad_rmse_mv"),
            "v2_ku_rmse": metric_value(selection.metric, "ku_rmse"),
            "v2_kd_rmse": metric_value(selection.metric, "kd_rmse"),
            "legacy_pad_rmse_mv": metric_value(selection.legacy_metric, "pad_rmse_mv"),
            "legacy_ku_rmse": metric_value(selection.legacy_metric, "ku_rmse"),
            "legacy_kd_rmse": metric_value(selection.legacy_metric, "kd_rmse"),
            "source_study": str(selection.source_study.relative_to(ROOT)),
        })
    write_rows(output / "selected_midtransition_metrics.csv", rows)
    selected_keys = {(item.device, item.direction, item.profile, item.case_id) for item in selections}
    write_rows(output / "candidate_midtransition_progress.csv", [{
        "device": item.device,
        "direction": item.direction,
        "profile": item.profile,
        "case_id": item.case_id,
        "pulse_width_ns": item.width_ns,
        "native_ku_at_reverse": item.native_ku_at_reverse,
        "native_kd_at_reverse": item.native_kd_at_reverse,
        "native_ku_progress_at_reverse": item.native_ku_progress,
        "native_kd_progress_at_reverse": item.native_kd_progress,
        "native_composite_progress_at_reverse": item.native_progress,
        "pad_map_triggered": item.map_triggered,
        "mapping_ambiguous": item.mapping_ambiguous,
        "selected": (item.device, item.direction, item.profile, item.case_id) in selected_keys,
        "source_study": str(item.source_study.relative_to(ROOT)),
    } for item in all_candidates])
    all_metric_improvements = sum(
        float(row["v2_pad_rmse_mv"]) < float(row["legacy_pad_rmse_mv"])
        and float(row["v2_ku_rmse"]) < float(row["legacy_ku_rmse"])
        and float(row["v2_kd_rmse"]) < float(row["legacy_kd_rmse"])
        for row in rows
    )
    short_high_rows = [row for row in rows if row["direction"] == "short_high"]
    short_low_rows = [row for row in rows if row["direction"] == "short_low"]
    short_high_pad_improvements = sum(
        float(row["v2_pad_rmse_mv"]) < float(row["legacy_pad_rmse_mv"])
        for row in short_high_rows
    )
    short_low_pad_regressions = sum(
        float(row["v2_pad_rmse_mv"]) > float(row["legacy_pad_rmse_mv"])
        for row in short_low_rows
    )
    ambiguous_count = sum(bool(row["mapping_ambiguous"]) for row in rows)
    for selection in selections:
        device_dir = output / selection.device
        suffix = "short_high" if selection.direction == "short_high" else "short_low"
        figure_number = "01" if selection.direction == "short_high" else "02"
        plot_case(selection, device_dir / f"{figure_number}_{suffix}_pad_match_v2.png")
        write_rows(device_dir / f"{suffix}_waveforms.csv", focused_wave_rows(selection))
    for device in DEVICES:
        device_selections = [item for item in selections if item.device == device]
        plot_diagnostics(device_selections, output / device / "03_trigger_diagnostics.png")
    plot_contact_sheet(selections, output / "00_all_buffers_pad_contact_sheet.png")

    lines = [
        "# Three-Buffer Pad-Matched Replay V2: Mid-Transition Evidence",
        "",
        "This focused package combines the completed three-buffer v2 study with a custom-width inv_chain sweep. The report builder itself runs no simulations.",
        "",
        "## Headline Result",
        "",
        f"- Confirmed pad-match activation: `{sum(bool(row['pad_map_triggered']) for row in rows)}/{len(rows)}` selected reversals.",
        f"- Pad, Ku, and Kd all improve together: `{all_metric_improvements}/{len(rows)}` cases.",
        f"- Short-high pad RMSE improves versus legacy: `{short_high_pad_improvements}/{len(short_high_rows)}` buffers, but coefficient agreement does not improve consistently.",
        f"- Short-low pad RMSE regresses versus legacy: `{short_low_pad_regressions}/{len(short_low_rows)}` buffers.",
        f"- Pad inverse mapping is explicitly ambiguous in `{ambiguous_count}/{len(rows)}` selected cases.",
        "- Conclusion: pad voltage alone is not a sufficient hidden state for reliable reverse-edge replay across these three buffers.",
        "",
        "## Common Bench",
        "",
        "- Input transition: `50 ps` rise and fall for every selected case.",
        "- Load: `50 ohm || 2 pF` directly at the output pad.",
        "- Supplies: io_buf `3.3 V`, inv_chain `1.8 V`, ex2 `3.3 V`.",
        "- References: HSPICE native IBIS supplies pad plus Ku/Kd; HSPICE transistor SPICE supplies pad only.",
        "- Candidate: ngspice `InputDrivenPadMatchedReplayV2`; `slow_1ns` and `fast_5ps` identify the IBIS source profile, not the 50 ps input edge.",
        "",
        "## Selection Rule",
        "",
        "- Compute native-IBIS Ku/Kd transition progress immediately before the reverse edge.",
        "- Require pad-match v2 to trigger and prefer progress in the 10%-90% interval.",
        "- Select the case closest to 50% composite Ku/Kd progress for each buffer and direction.",
        "- Composite progress confirms an unsettled transition; the Ku and Kd progress columns in the CSV retain directional asymmetry rather than hiding it.",
        "",
        "## Selected Cases",
        "",
        "| Buffer | Direction | Profile | Width | Native progress | Trigger | Ambiguous | V2 class | Pad RMSE mV | Ku RMSE | Kd RMSE |",
        "|---|---|---|---:|---:|---|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['device']} | {row['direction']} | {row['profile']} | {float(row['pulse_width_ns']):g} ns | "
            f"{float(row['native_progress_at_reverse']):.3f} | {row['pad_map_triggered']} | {row['mapping_ambiguous']} | "
            f"{row['v2_classification']} | {float(row['v2_pad_rmse_mv']):.3f} | "
            f"{float(row['v2_ku_rmse']):.4f} | {float(row['v2_kd_rmse']):.4f} |"
        )
    lines.extend([
        "",
        "## Figures",
        "",
        "- `00_all_buffers_pad_contact_sheet.png`: pad-level overview for all six selected reversals.",
        "- `<buffer>/01_short_high_pad_match_v2.png`: input, pad, Ku, and Kd for fall-after-rise.",
        "- `<buffer>/01_short_low_pad_match_v2.png`: input, pad, Ku, and Kd for rise-after-fall.",
        "- `<buffer>/03_trigger_diagnostics.png`: sampled pad voltage, inferred table start, replay argument, and active/ambiguity flags.",
        "- `<buffer>/*_waveforms.csv`: numeric data behind each focused figure.",
        "- `candidate_midtransition_progress.csv`: native Ku/Kd progress for every pulse considered by the selector.",
        "",
        "## Interpretation",
        "",
        "The figures must be read coefficient-first: a visually improved pad is not sufficient when either Ku or Kd disagrees with native IBIS. `PAD_MAPPING_AMBIGUOUS` is retained as an experimental result, not hidden.",
    ])
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--inv-chain-custom-study", type=Path, default=DEFAULT_INV_CHAIN_CUSTOM_STUDY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    study = args.study_dir.resolve()
    output = (args.output_dir or (study / "focused_midtransition_evidence")).resolve()
    metrics = read_rows(study / "candidate_metrics.csv")
    custom_study = args.inv_chain_custom_study.resolve() if args.inv_chain_custom_study else None
    selections, all_candidates = choose_cases(study, metrics, custom_study)
    write_report(study, selections, all_candidates, output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
