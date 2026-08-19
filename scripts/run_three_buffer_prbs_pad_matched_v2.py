#!/usr/bin/env python3
"""Run pad-voltage-matched replay v2 on per-buffer stressed PRBS7 streams."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
import shutil
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

import run_three_buffer_pad_matched_replay as pad
import run_three_buffer_prbs_phase1 as phase


DEFAULT_OUT = ROOT / "results" / "three_buffer_prbs_pad_matched_v2_true_output_2026-08-11"
MODEL_STUDY = ROOT / "results" / "three_buffer_pad_matched_replay_v2_midtransition_2026-08-11"
BASELINE_PRBS = ROOT / "results" / "three_buffer_prbs_phase1_2026-07-31"
DEFAULT_SELECTION_CSV = (
    ROOT / "results" / "three_buffer_output_level_reversal_screen_2026-08-11" / "selected_ui.csv"
)
PARTIAL_LOW = 0.05
PARTIAL_HIGH = 0.95
FLOW_MODES = {
    "legacy": "InputDriven",
    "pad_match_v2": "InputDrivenPadMatchedReplayV2",
}
PAD_V2_DIAGNOSTICS = (
    "kuleg", "kdleg", "padsamp", "padstart_latch", "padstartspan",
    "padmatch_ambiguous", "pmt0", "pmelapsed", "padarg", "padmapactive",
    "hfall_after_rise", "hrise_after_fall", "hreverse_edge", "pmsample",
    "pmlatchpulse", "kutarget", "kdtarget", "coeff_jump_ku", "coeff_jump_kd",
)

BLACK = "#111111"
GRAY = "#777777"
RED = "#CC3311"
BLUE = "#0072B2"
PURPLE = "#7B2CBF"
ORANGE = "#E69F00"
GREEN = "#009E73"
GRID = "#D9DEE5"


def ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    ensure(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_selections(path: Path) -> dict[str, dict[str, object]]:
    selected_rows = read_csv(path)
    screening_path = path.parent / "screening_metrics.csv"
    screening_rows = read_csv(screening_path)
    result: dict[str, dict[str, object]] = {}
    for row in selected_rows:
        device = row["device"]
        ui_ns = float(row["selected_ui_ns"])
        native = next(
            item for item in screening_rows
            if item["device"] == device
            and item["reference"] == "hspice_native_ibis"
            and abs(float(item["width_ns"]) - ui_ns) < 1e-12
        )
        result[device] = {
            "ui_ns": ui_ns,
            "stress_direction": row["stress_direction"],
            "loaded_low_v": float(native["loaded_low_v"]),
            "loaded_high_v": float(native["loaded_high_v"]),
            "selection_gate": row["selection_gate"],
        }
    return result


def save_wave(path: Path, data: dict[str, np.ndarray]) -> None:
    ensure(path.parent)
    names = list(data)
    np.savetxt(
        path,
        np.column_stack([data[name] for name in names]),
        delimiter=",",
        header=",".join(names),
        comments="",
        fmt="%.10g",
    )


def style_axis(axis: plt.Axes) -> None:
    axis.grid(True, color=GRID, lw=0.8, alpha=0.75)
    axis.spines[["top", "right"]].set_visible(False)


def interp(wave: dict[str, np.ndarray], time_ns: np.ndarray, key: str) -> np.ndarray:
    return np.interp(time_ns, wave["time_ns"], wave[key])


def candidate_model(device: phase.base.Device, flow: str, out: Path, ngspice: Path) -> Path:
    source = (
        MODEL_STUDY
        / "generated_models"
        / device.device_id
        / "fast_5ps"
        / ("pad_voltage" if flow == "pad_match_v2" else "legacy")
        / f"{device.subckt}.sub"
    )
    if source.exists():
        return source

    pad.OUT = out
    pad.FLOWS = pad.V2_FLOWS
    pad.PAD_FLOWS = tuple(item.flow_id for item in pad.FLOWS if item.pad_reference)
    profile = phase.base.Profile("fast_5ps", "fast-edge IBIS", device.fast_ibis)
    legacy = pad.prepare_legacy(device, profile)
    reference, _ = pad.build_pad_reference(device, profile, legacy, ngspice, 120, True)
    return pad.prepare_models(device, profile, reference)[
        "pad_voltage" if flow == "pad_match_v2" else "legacy"
    ]


def ngspice_deck(
    device: phase.base.Device,
    case: phase.PrbsCase,
    flow: str,
    solver_profile: str,
) -> str:
    diagnostics = ""
    if flow == "pad_match_v2":
        diagnostics = "".join(f" V(xdrv.{name})" for name in PAD_V2_DIAGNOSTICS)
    signals = f"V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){diagnostics}"
    return f"""* Three-buffer stressed PRBS7 pad-match v2
.title {device.device_id} PRBS7 UI={phase.base.fmt(case.ui_ns)}ns {flow}
.temp 27
.options {phase.SOLVER_PROFILES[solver_profile]}

{phase.prbs_pwl(device, case)}

Ven en_sig 0 DC {phase.base.fmt(device.enable_v)}
Vdd vdd 0 DC {phase.base.fmt(device.supply_v)}
.include '{device.subckt}.sub'
XDRV pad in_dig en_sig vdd 0 {device.subckt}
Rload pad 0 {phase.base.fmt(phase.LOAD_OHM)}
Cload pad 0 {phase.base.fmt(phase.LOAD_PF)}p

.save {signals}
.tran {phase.base.fmt(phase.TRAN_STEP_NS)}n {phase.base.fmt(phase.candidate_stop_ns(case))}n
.control
set filetype=binary
run
linearize
write run.raw {signals}
quit
.endc
.end
"""


def run_ngspice(
    out: Path,
    device: phase.base.Device,
    case: phase.PrbsCase,
    flow: str,
    model: Path,
    ngspice: Path,
    timeout_s: int,
    solver_profile: str,
    resume: bool,
) -> tuple[dict[str, np.ndarray] | None, dict[str, object]]:
    run_dir = out / "runs" / device.device_id / case.case_id / flow / solver_profile
    ensure(run_dir)
    local_model = run_dir / f"{device.subckt}.sub"
    shutil.copy2(model, local_model)
    deck_text = ngspice_deck(device, case, flow, solver_profile)
    deck = run_dir / "run.sp"
    raw = run_dir / "run.raw"
    log = run_dir / "run.log"
    signature_file = run_dir / "run_signature.txt"
    signature = hashlib.sha256(deck_text.encode("ascii") + local_model.read_bytes()).hexdigest()
    complete = False
    if resume and raw.exists() and signature_file.exists():
        if signature_file.read_text(encoding="ascii").strip() == signature:
            try:
                existing = pad.parse_ng(raw)
                complete = existing["time_ns"][-1] >= 0.995 * phase.candidate_stop_ns(case)
            except Exception:
                complete = False
    if resume and not complete and log.exists() and signature_file.exists():
        prior = log.read_text(encoding="utf-8", errors="replace")
        if signature_file.read_text(encoding="ascii").strip() == signature and "TIMEOUT after" in prior:
            return None, {
                "device": device.device_id,
                "case_id": case.case_id,
                "ui_ps": case.ui_ns * 1000.0,
                "flow": flow,
                "status": "NUMERIC_FAIL",
                "source": "existing_timeout",
                "return_code": 124,
                "log": str(log.relative_to(ROOT)),
            }
    source = "existing_raw" if complete else "run"
    if not complete:
        deck.write_text(deck_text, encoding="ascii")
        if raw.exists():
            raw.unlink()
        rc = phase.base.run_process([str(ngspice), "-b", deck.name], run_dir, log, timeout_s)
        signature_file.write_text(signature + "\n", encoding="ascii")
        if rc != 0 or not raw.exists():
            return None, {
                "device": device.device_id,
                "case_id": case.case_id,
                "ui_ps": case.ui_ns * 1000.0,
                "flow": flow,
                "status": "NUMERIC_FAIL",
                "return_code": rc,
                "source": source,
                "raw": "",
                "log": str(log.relative_to(ROOT)),
            }
    parsed = pad.parse_ng(raw)
    return parsed, {
        "device": device.device_id,
        "case_id": case.case_id,
        "ui_ps": case.ui_ns * 1000.0,
        "flow": flow,
        "status": "COMPLETED",
        "return_code": 0,
        "source": source,
        "raw": str(raw.relative_to(ROOT)),
        "log": str(log.relative_to(ROOT)),
    }


def align(
    device: phase.base.Device,
    case: phase.PrbsCase,
    transistor: dict[str, np.ndarray],
    native: dict[str, np.ndarray],
    candidates: dict[str, dict[str, np.ndarray] | None],
) -> dict[str, np.ndarray]:
    start = max(0.0, case.analysis_start_ns - 2.0 * case.ui_ns)
    stop = phase.candidate_stop_ns(case)
    time_ns = np.arange(start, stop + 0.5 * phase.TRAN_STEP_NS, phase.TRAN_STEP_NS)
    result = {
        "time_ns": time_ns,
        "input_v": phase.input_waveform(device, case, time_ns),
        "hspice_transistor_pad_v": interp(transistor, time_ns, "pad_v"),
        "hspice_native_ibis_pad_v": interp(native, time_ns, "pad_v"),
        "hspice_native_ibis_ku": interp(native, time_ns, "ku"),
        "hspice_native_ibis_kd": interp(native, time_ns, "kd"),
    }
    for flow, wave in candidates.items():
        if wave is None:
            continue
        for key, values in wave.items():
            if key == "time_ns" or values is None:
                continue
            result[f"{flow}_{key}"] = np.interp(time_ns, wave["time_ns"], values)
    return result


def transition_events(
    device: phase.base.Device,
    case: phase.PrbsCase,
    data: dict[str, np.ndarray],
    selection: dict[str, object],
) -> list[dict[str, object]]:
    bits = phase.analysis_bits()
    starts = phase.bit_starts(case)
    low_v = float(selection["loaded_low_v"])
    high_v = float(selection["loaded_high_v"])
    swing_v = max(high_v - low_v, 1e-12)
    rows: list[dict[str, object]] = []
    for index in range(1, len(bits)):
        previous = bits[index - 1]
        current = bits[index]
        if current == previous:
            continue
        crossing = float(starts[index] + 0.5 * case.edge_ns)
        sample_time = crossing - phase.TRAN_STEP_NS
        ku = float(np.interp(sample_time, data["time_ns"], data["hspice_native_ibis_ku"]))
        kd = float(np.interp(sample_time, data["time_ns"], data["hspice_native_ibis_kd"]))
        if previous:
            ku_progress = ku
            kd_progress = 1.0 - kd
            direction = "fall_after_rise"
        else:
            ku_progress = 1.0 - ku
            kd_progress = kd
            direction = "rise_after_fall"
        composite = 0.5 * (ku_progress + kd_progress)
        coefficient_midstate = 0.10 <= composite <= 0.90
        isolated_reversal = index >= 2 and bits[index - 2] == current
        prior_crossing = float(starts[index - 1] + 0.5 * case.edge_ns)
        next_crossing = float(data["time_ns"][-1])
        for future in range(index + 1, len(bits)):
            if bits[future] != bits[future - 1]:
                next_crossing = float(starts[future] + 0.5 * case.edge_ns)
                break
        recovery_gap_ui = (next_crossing - crossing) / case.ui_ns
        clean_recovery = recovery_gap_ui >= 1.5
        response_stop = min(next_crossing, crossing + max(4.0 * case.ui_ns, 1.0))
        response_mask = (
            (data["time_ns"] >= prior_crossing)
            & (data["time_ns"] <= response_stop)
        )
        response_time = data["time_ns"][response_mask]
        native_pad = data["hspice_native_ibis_pad_v"][response_mask]
        pad_at_reverse = float(np.interp(crossing, data["time_ns"], data["hspice_native_ibis_pad_v"]))
        if previous:
            extreme_index = int(np.argmax(native_pad))
            output_extreme = float(native_pad[extreme_index])
            output_excursion = (output_extreme - low_v) / swing_v
            pad_progress_at_reverse = (pad_at_reverse - low_v) / swing_v
        else:
            extreme_index = int(np.argmin(native_pad))
            output_extreme = float(native_pad[extreme_index])
            output_excursion = (high_v - output_extreme) / swing_v
            pad_progress_at_reverse = (high_v - pad_at_reverse) / swing_v
        output_turn_time = float(response_time[extreme_index])
        probe_delta = min(0.02, 0.15 * case.ui_ns)
        before = float(np.interp(
            output_turn_time - probe_delta,
            data["time_ns"],
            data["hspice_native_ibis_pad_v"],
        ))
        after = float(np.interp(
            output_turn_time + probe_delta,
            data["time_ns"],
            data["hspice_native_ibis_pad_v"],
        ))
        if previous:
            output_reversed = before < output_extreme - 1e-5 and after < output_extreme - 1e-5
        else:
            output_reversed = before > output_extreme + 1e-5 and after > output_extreme + 1e-5
        stressed = bool(
            isolated_reversal
            and clean_recovery
            and PARTIAL_LOW <= output_excursion <= PARTIAL_HIGH
            and output_turn_time >= crossing
            and output_reversed
        )
        event_mask = (
            (data["time_ns"] >= crossing)
            & (data["time_ns"] <= response_stop)
        )
        active = bool(
            "pad_match_v2_padmapactive" in data
            and np.any(data["pad_match_v2_padmapactive"][event_mask] > 0.5)
        )
        ambiguous = bool(
            "pad_match_v2_padmatch_ambiguous" in data
            and np.any(data["pad_match_v2_padmatch_ambiguous"][event_mask] > 0.5)
        )
        row: dict[str, object] = {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000.0,
            "bit_index": index,
            "edge_time_ns": crossing,
            "direction": direction,
            "previous_bit": previous,
            "current_bit": current,
            "native_ku_before_edge": ku,
            "native_kd_before_edge": kd,
            "native_ku_progress": ku_progress,
            "native_kd_progress": kd_progress,
            "native_composite_progress": composite,
            "coefficient_midstate": coefficient_midstate,
            "isolated_reversal_pattern": isolated_reversal,
            "clean_recovery_pattern": clean_recovery,
            "recovery_gap_ui": recovery_gap_ui,
            "native_loaded_low_v": low_v,
            "native_loaded_high_v": high_v,
            "native_pad_at_reverse_v": pad_at_reverse,
            "native_pad_progress_at_reverse": pad_progress_at_reverse,
            "native_output_extreme_v": output_extreme,
            "native_output_excursion_fraction": output_excursion,
            "native_output_turn_time_ns": output_turn_time,
            "native_output_direction_reversed": output_reversed,
            "midtransition_stress": stressed,
            "true_output_reversal": stressed,
            "pad_v2_active": active,
            "pad_v2_ambiguous": ambiguous,
        }
        for signal in ("pad_v", "ku", "kd"):
            native_key = f"hspice_native_ibis_{signal}"
            candidate_key = f"pad_match_v2_{signal}"
            if candidate_key in data:
                error = data[candidate_key][event_mask] - data[native_key][event_mask]
                row[f"v2_{signal}_event_rmse"] = float(np.sqrt(np.mean(error * error)))
                row[f"v2_{signal}_event_max_error"] = float(np.max(np.abs(error)))
        rows.append(row)
    return rows


def metrics(
    device: phase.base.Device,
    case: phase.PrbsCase,
    data: dict[str, np.ndarray],
    events: list[dict[str, object]],
) -> list[dict[str, object]]:
    mask = phase.analysis_mask(case, data["time_ns"])
    stressed = [row for row in events if bool(row["midtransition_stress"])]
    result: list[dict[str, object]] = []
    for flow in ("legacy", "pad_match_v2"):
        if f"{flow}_pad_v" not in data:
            continue
        row: dict[str, object] = {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000.0,
            "data_rate_gbps": 1.0 / case.ui_ns,
            "flow": flow,
            "transition_count": len(events),
            "midtransition_count": len(stressed),
            "midtransition_fraction": len(stressed) / len(events) if events else 0.0,
        }
        for signal in ("pad_v", "ku", "kd"):
            reference = data[f"hspice_native_ibis_{signal}"][mask]
            candidate = data[f"{flow}_{signal}"][mask]
            row[f"{signal}_rmse"] = float(np.sqrt(np.mean((candidate - reference) ** 2)))
            row[f"{signal}_max_error"] = float(np.max(np.abs(candidate - reference)))
        eye = phase.optimize_eye(case, data["time_ns"], data[f"{flow}_pad_v"])
        row.update({f"eye_{key}": value for key, value in eye.items()})
        if flow == "pad_match_v2":
            row["active_event_count"] = sum(bool(item["pad_v2_active"]) for item in events)
            row["ambiguous_event_count"] = sum(bool(item["pad_v2_ambiguous"]) for item in events)
            row["stressed_active_count"] = sum(
                bool(item["midtransition_stress"]) and bool(item["pad_v2_active"])
                for item in events
            )
        result.append(row)
    transistor_eye = phase.optimize_eye(case, data["time_ns"], data["hspice_transistor_pad_v"])
    native_eye = phase.optimize_eye(case, data["time_ns"], data["hspice_native_ibis_pad_v"])
    result.extend([
        {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000.0,
            "data_rate_gbps": 1.0 / case.ui_ns,
            "flow": "hspice_native_ibis",
            **{f"eye_{key}": value for key, value in native_eye.items()},
        },
        {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000.0,
            "data_rate_gbps": 1.0 / case.ui_ns,
            "flow": "hspice_transistor",
            "pad_v_rmse": float(np.sqrt(np.mean(
                (data["hspice_transistor_pad_v"][mask] - data["hspice_native_ibis_pad_v"][mask]) ** 2
            ))),
            **{f"eye_{key}": value for key, value in transistor_eye.items()},
        },
    ])
    return result


def plot_sequence(
    device: phase.base.Device,
    case: phase.PrbsCase,
    data: dict[str, np.ndarray],
    events: list[dict[str, object]],
    output: Path,
) -> None:
    candidate_flow = "pad_match_v2" if "pad_match_v2_pad_v" in data else "legacy"
    candidate_label = "pad-match v2" if candidate_flow == "pad_match_v2" else "legacy pybis (V2 timed out)"
    stressed = [row for row in events if bool(row["midtransition_stress"])]
    center = float(stressed[0]["edge_time_ns"]) if stressed else case.analysis_start_ns + 5 * case.ui_ns
    start = max(case.analysis_start_ns, center - 3.0 * case.ui_ns)
    stop = min(case.analysis_end_ns, start + 12.0 * case.ui_ns)
    mask = (data["time_ns"] >= start) & (data["time_ns"] <= stop)
    t = (data["time_ns"][mask] - start) / case.ui_ns
    fig, axes = plt.subplots(4, 1, figsize=(15.5, 10.5), sharex=True, constrained_layout=True)
    axes[0].plot(t, data["input_v"][mask], color=BLUE, lw=1.8)
    axes[0].set_ylabel("input (V)")
    axes[1].plot(t, data["hspice_native_ibis_pad_v"][mask], color=BLACK, lw=3.6, alpha=0.84, label="HSPICE native IBIS")
    axes[1].plot(t, data["hspice_transistor_pad_v"][mask], color=GRAY, lw=2.8, alpha=0.84, label="HSPICE transistor")
    axes[1].plot(t, data[f"{candidate_flow}_pad_v"][mask], color=RED, lw=2.0, label=candidate_label)
    axes[1].set_ylabel("pad (V)")
    for axis, signal in ((axes[2], "ku"), (axes[3], "kd")):
        axis.plot(t, data[f"hspice_native_ibis_{signal}"][mask], color=BLACK, lw=3.6, alpha=0.84, label="HSPICE native IBIS")
        axis.plot(t, data[f"{candidate_flow}_{signal}"][mask], color=RED, lw=2.0, label=candidate_label)
        axis.set_ylabel(signal.capitalize())
    axes[3].axhline(0.0, color="#999999", lw=0.8)
    axes[3].set_xlabel("bit position (UI)")
    for event in events:
        edge = float(event["edge_time_ns"])
        if not (start <= edge <= stop):
            continue
        x = (edge - start) / case.ui_ns
        for axis in axes:
            axis.axvline(x, color="#999999", lw=0.65, alpha=0.65)
            if bool(event["midtransition_stress"]):
                axis.axvspan(x - 0.04, x + 0.04, color=ORANGE, alpha=0.20)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.985, 0.985), ncol=3, frameon=True)
    fig.suptitle(f"{device.device_id} | stressed PRBS7 | {case.ui_ns * 1000:.0f} ps UI", fontsize=17)
    for axis in axes:
        style_axis(axis)
    ensure(output.parent)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_event_zoom(
    device: phase.base.Device,
    case: phase.PrbsCase,
    data: dict[str, np.ndarray],
    events: list[dict[str, object]],
    output: Path,
) -> None:
    candidate_flow = "pad_match_v2" if "pad_match_v2_pad_v" in data else "legacy"
    candidate_label = "pad-match v2" if candidate_flow == "pad_match_v2" else "legacy pybis (V2 timed out)"
    stressed = [row for row in events if bool(row["midtransition_stress"])]
    selected = min(
        stressed or events,
        key=lambda row: abs(float(row["native_output_excursion_fraction"]) - 0.5),
    )
    edge = float(selected["edge_time_ns"])
    start = edge - 1.25 * case.ui_ns
    stop = edge + 3.0 * case.ui_ns
    mask = (data["time_ns"] >= start) & (data["time_ns"] <= stop)
    t = (data["time_ns"][mask] - edge) / case.ui_ns
    fig, axes = plt.subplots(5, 1, figsize=(14.5, 11.5), sharex=True, constrained_layout=True)
    axes[0].plot(t, data["input_v"][mask], color=BLUE, lw=1.9)
    axes[0].set_ylabel("input (V)")
    axes[1].plot(t, data["hspice_native_ibis_pad_v"][mask], color=BLACK, lw=3.6, alpha=0.84, label="HSPICE native IBIS")
    axes[1].plot(t, data["hspice_transistor_pad_v"][mask], color=GRAY, lw=2.8, alpha=0.84, label="HSPICE transistor")
    axes[1].plot(t, data[f"{candidate_flow}_pad_v"][mask], color=RED, lw=2.0, label=candidate_label)
    axes[1].set_ylabel("pad (V)")
    for axis, signal in ((axes[2], "ku"), (axes[3], "kd")):
        axis.plot(t, data[f"hspice_native_ibis_{signal}"][mask], color=BLACK, lw=3.6, alpha=0.84)
        axis.plot(t, data[f"{candidate_flow}_{signal}"][mask], color=RED, lw=2.0)
        axis.set_ylabel(signal.capitalize())
    axes[3].axhline(0.0, color="#999999", lw=0.8)
    if "pad_match_v2_padmapactive" in data:
        axes[4].plot(t, data["pad_match_v2_padmapactive"][mask], color=GREEN, lw=2.0, label="pad-map active")
    if "pad_match_v2_padmatch_ambiguous" in data:
        axes[4].plot(t, data["pad_match_v2_padmatch_ambiguous"][mask], color=ORANGE, lw=1.8, label="mapping ambiguous")
    axes[4].set_ylabel("flag")
    axes[4].set_xlabel("time from selected reverse edge (UI)")
    turn_ui = (float(selected["native_output_turn_time_ns"]) - edge) / case.ui_ns
    for axis in axes:
        axis.axvline(0.0, color=PURPLE, lw=1.4, ls="--")
        axis.axvline(turn_ui, color=ORANGE, lw=1.4, ls=":")
        style_axis(axis)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.985, 0.985), ncol=3, frameon=True)
    fig.suptitle(
        f"{device.device_id} | true output reversal | native excursion "
        f"{100.0 * float(selected['native_output_excursion_fraction']):.1f}%",
        fontsize=17,
    )
    ensure(output.parent)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_diagnostics(
    device: phase.base.Device,
    case: phase.PrbsCase,
    data: dict[str, np.ndarray],
    events: list[dict[str, object]],
    output: Path,
) -> None:
    stressed = [row for row in events if bool(row["midtransition_stress"])]
    selected = min(
        stressed or events,
        key=lambda row: abs(float(row["native_output_excursion_fraction"]) - 0.5),
    )
    edge = float(selected["edge_time_ns"])
    start = edge - 0.75 * case.ui_ns
    stop = edge + 3.0 * case.ui_ns
    mask = (data["time_ns"] >= start) & (data["time_ns"] <= stop)
    t = (data["time_ns"][mask] - edge) / case.ui_ns
    fig, axes = plt.subplots(3, 1, figsize=(14.0, 8.8), sharex=True, constrained_layout=True)
    axes[0].plot(t, data["pad_match_v2_pad_v"][mask], color=RED, lw=2.0, label="pad")
    axes[0].plot(t, data["pad_match_v2_padsamp"][mask], color=BLUE, lw=1.8, label="latched pad sample")
    axes[0].set_ylabel("voltage (V)")
    axes[1].plot(t, data["pad_match_v2_padstart_latch"][mask], color=PURPLE, lw=2.0, label="inferred start")
    axes[1].plot(t, data["pad_match_v2_padarg"][mask], color=RED, lw=1.8, label="replay argument")
    axes[1].set_ylabel("table time (ns)")
    axes[2].plot(t, data["pad_match_v2_padmapactive"][mask], color=GREEN, lw=2.0, label="pad-map active")
    axes[2].plot(t, data["pad_match_v2_padmatch_ambiguous"][mask], color=ORANGE, lw=1.8, label="mapping ambiguous")
    axes[2].set_ylabel("flag")
    axes[2].set_xlabel("time from selected reverse edge (UI)")
    for axis in axes:
        axis.axvline(0.0, color=PURPLE, lw=1.3, ls="--")
        axis.legend(loc="best", fontsize=9)
        style_axis(axis)
    fig.suptitle(f"{device.device_id} | pad-match v2 replay diagnostics", fontsize=17)
    ensure(output.parent)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_eyes(
    device: phase.base.Device,
    case: phase.PrbsCase,
    data: dict[str, np.ndarray],
    output: Path,
) -> None:
    relative = np.linspace(-0.5 * case.ui_ns, 1.5 * case.ui_ns, 401)
    starts = phase.bit_starts(case)
    flows = [
        ("hspice_native_ibis_pad_v", BLACK, "HSPICE native IBIS"),
        ("hspice_transistor_pad_v", GRAY, "HSPICE transistor"),
    ]
    if "pad_match_v2_pad_v" in data:
        flows.append(("pad_match_v2_pad_v", RED, "pad-match v2"))
    else:
        flows.append(("legacy_pad_v", RED, "legacy pybis (V2 timed out)"))
    fig, axes = plt.subplots(1, len(flows), figsize=(16.0, 5.0), sharex=True, sharey=True, constrained_layout=True)
    for axis, (key, color, label) in zip(axes, flows):
        for start in starts:
            values = np.interp(start + relative, data["time_ns"], data[key])
            axis.plot(relative / case.ui_ns, values, color=color, lw=0.85, alpha=0.35)
        axis.set_title(label)
        axis.set_xlabel("time from bit boundary (UI)")
        style_axis(axis)
    axes[0].set_ylabel("pad (V)")
    fig.suptitle(f"{device.device_id} | PRBS7 pad eyes | {case.ui_ns * 1000:.0f} ps UI", fontsize=17)
    ensure(output.parent)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def contact_sheet(paths: list[Path], output: Path) -> None:
    if not paths:
        return
    images = [plt.imread(path) for path in paths]
    fig, axes = plt.subplots(len(images), 1, figsize=(16.0, 8.2 * len(images)), constrained_layout=True)
    for axis, image in zip(np.atleast_1d(axes), images):
        axis.imshow(image)
        axis.axis("off")
    ensure(output.parent)
    fig.savefig(output, dpi=130)
    plt.close(fig)


def activation_audit(event_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for device in ("io_buf", "inv_chain", "ex2"):
        events = [row for row in event_rows if row["device"] == device]
        native_mid = [row for row in events if bool(row["midtransition_stress"])]
        active = [row for row in events if bool(row["pad_v2_active"])]
        true_active = [
            row for row in events
            if bool(row["midtransition_stress"]) and bool(row["pad_v2_active"])
        ]
        missed = [
            row for row in events
            if bool(row["midtransition_stress"]) and not bool(row["pad_v2_active"])
        ]
        false_active = [
            row for row in events
            if not bool(row["midtransition_stress"]) and bool(row["pad_v2_active"])
        ]
        rows.append({
            "device": device,
            "reversal_count": len(events),
            "native_midtransition_count": len(native_mid),
            "v2_active_count": len(active),
            "true_active_count": len(true_active),
            "missed_midtransition_count": len(missed),
            "false_active_count": len(false_active),
            "ambiguous_count": sum(bool(row["pad_v2_ambiguous"]) for row in events),
        })
    return rows


def build_readme(
    out: Path,
    metric_rows: list[dict[str, object]],
    event_rows: list[dict[str, object]],
    run_rows: list[dict[str, object]],
) -> None:
    audit_rows = activation_audit(event_rows)
    lines = [
        "# Three-Buffer Stressed PRBS7: Pad-Matched Replay V2",
        "",
        "## Fixed Bench",
        "",
        "- Fast-edge IBIS profile for all three buffers.",
        "- Deterministic PRBS7 (`x^7 + x^6 + 1`), 31 analyzed bits containing every three-bit history.",
        "- Input rise/fall: `50 ps`; direct load: `50 ohm || 2 pF`.",
        "- Per-buffer UI is selected by an HSPICE output screen, not by Ku/Kd alone.",
        "- A true output reversal is an isolated one-bit pulse whose native pad turns around after 5%-95% of loaded swing without completing the original full swing.",
        "- HSPICE native IBIS provides pad and Ku/Kd; HSPICE transistor SPICE provides pad only.",
        "- ngspice flows: unchanged legacy pybis and `InputDrivenPadMatchedReplayV2`.",
        "",
        "## Selected Data Rates",
        "",
        "| Buffer | UI | Data rate | Native transitions | True output reversals | V2 active | Ambiguous |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for device in ("io_buf", "inv_chain", "ex2"):
        row = next(
            item for item in metric_rows
            if item["device"] == device and item["flow"] in {"pad_match_v2", "legacy"}
        )
        v2_row = next(
            (item for item in metric_rows if item["device"] == device and item["flow"] == "pad_match_v2"),
            None,
        )
        lines.append(
            f"| {device} | {float(row['ui_ps']):.0f} ps | {float(row['data_rate_gbps']):.3f} Gb/s | "
            f"{int(row['transition_count'])} | {int(row['midtransition_count'])} "
            f"({100.0 * float(row['midtransition_fraction']):.1f}%) | "
            f"{int(v2_row['active_event_count']) if v2_row else 'n/a'} | "
            f"{int(v2_row['ambiguous_event_count']) if v2_row else 'n/a'} |"
        )
    lines.extend([
        "",
        "## Trigger Audit",
        "",
        "A correct PRBS retrigger detector must activate on true native output reversals and return to legacy replay afterward.",
        "",
        "| Buffer | True output reversals | Correct activations | Missed reversals | False activations | Ambiguous |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in audit_rows:
        lines.append(
            f"| {row['device']} | {row['native_midtransition_count']} | {row['true_active_count']} | "
            f"{row['missed_midtransition_count']} | {row['false_active_count']} | {row['ambiguous_count']} |"
        )
    lines.extend([
        "",
        "## Correlation",
        "",
        "| Buffer | Flow | Pad RMSE | Ku RMSE | Kd RMSE | Eye height |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for row in metric_rows:
        if row["flow"] not in {"legacy", "pad_match_v2"}:
            continue
        lines.append(
            f"| {row['device']} | {row['flow']} | {1000.0 * float(row['pad_v_rmse']):.2f} mV | "
            f"{float(row['ku_rmse']):.4f} | {float(row['kd_rmse']):.4f} | "
            f"{float(row['eye_eye_height_v']):.4f} V |"
        )
    for device in ("io_buf", "inv_chain", "ex2"):
        if not any(row["device"] == device and row["flow"] == "pad_match_v2" for row in metric_rows):
            status = next(
                (row["status"] for row in run_rows if row["device"] == device and row["flow"] == "pad_match_v2"),
                "NOT_RUN",
            )
            lines.append(f"| {device} | pad_match_v2 | {status} | n/a | n/a | n/a |")
    better = 0
    for device in ("io_buf", "inv_chain", "ex2"):
        legacy = next(row for row in metric_rows if row["device"] == device and row["flow"] == "legacy")
        v2 = next(
            (row for row in metric_rows if row["device"] == device and row["flow"] == "pad_match_v2"),
            None,
        )
        if v2 is None:
            continue
        if all(float(v2[f"{key}_rmse"]) < float(legacy[f"{key}_rmse"]) for key in ("pad_v", "ku", "kd")):
            better += 1
    lines.extend([
        "",
        "## Headline Finding",
        "",
        f"- Pad, Ku, and Kd all improve together versus legacy in `{better}/3` stressed PRBS cases.",
        f"- Total true native output-reversal events: `{sum(bool(row['midtransition_stress']) for row in event_rows)}`.",
        f"- Pad-V2 mapping ambiguities: `{sum(bool(row['pad_v2_ambiguous']) for row in event_rows)}` transition events.",
        f"- Pad-V2 numeric failures: `{sum(row.get('flow') == 'pad_match_v2' and row.get('status') != 'COMPLETED' for row in run_rows)}`.",
        "- Trigger correctness is reported separately as correct, missed, and false activations; a sequence-level pass requires zero misses and zero false activations.",
        "- Persistent activation or a bounded timeout is an algorithm-state/numerical failure even when one isolated event looks reasonable.",
        "- Read the coefficient panels with the pad panel: an open eye or lower pad error is not sufficient when Ku/Kd diverge.",
        "",
        "## Figures And Data",
        "",
        "- `00_three_buffer_prbs_contact_sheet.png`: sequence-level overview for all buffers.",
        "- `figures/<buffer>/01_prbs_sequence.png`: input, pad, Ku, and Kd; orange bands mark true native output reversals.",
        "- `figures/<buffer>/02_midtransition_event.png`: the true output reversal closest to 50% excursion.",
        "- `figures/<buffer>/03_pad_match_diagnostics.png`: sampled pad, inferred replay start, replay timer, active and ambiguity flags.",
        "- `figures/<buffer>/04_pad_eyes.png`: clean native-IBIS, transistor, and pad-V2 eyes.",
        "- `waveforms/<buffer>.csv`: numeric data behind the figures.",
        "- `stress_events.csv`: every PRBS reversal and its native Ku/Kd progress.",
        "- `activation_audit.csv`: correct, missed, and false V2 activations by buffer.",
        "- `metrics.csv`: sequence RMSE and eye metrics.",
        "- `run_manifest.csv`: simulator status plus cache/run provenance.",
        "",
        f"Completed simulator flows: `{sum(row.get('status') == 'COMPLETED' for row in run_rows)}/{len(run_rows)}`.",
    ])
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    out = args.study_dir.resolve()
    ensure(out)
    phase.OUT_DIR = out
    pad.OUT = out
    run_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    sequence_paths: list[Path] = []
    selections = load_selections(args.selection_csv.resolve())

    for device in phase.base.DEVICES:
        selection = selections[device.device_id]
        ui_ns = float(selection["ui_ns"])
        case = phase.make_case(ui_ns)
        profile = phase.fast_profile(device)
        print(f"[{device.device_id}] UI={ui_ns * 1000:.0f} ps", flush=True)
        transistor_raw, transistor_row = phase.run_hspice_transistor(device, case, args.hspice, args.timeout_s)
        native_raw, native_row = phase.run_hspice_native(device, case, profile, args.hspice, args.timeout_s)
        run_rows.extend((transistor_row, native_row))
        transistor = phase.base.transistor_waveform(device, transistor_raw)
        native = phase.base.native_waveform(native_raw)
        candidates: dict[str, dict[str, np.ndarray] | None] = {}
        for flow in ("legacy", "pad_match_v2"):
            model = candidate_model(device, flow, out, args.ngspice)
            wave, row = run_ngspice(
                out,
                device,
                case,
                flow,
                model,
                args.ngspice,
                args.timeout_s,
                args.solver_profile,
                args.resume,
            )
            run_rows.append(row)
            candidates[flow] = wave
        if candidates["legacy"] is None:
            write_csv(out / "run_manifest.csv", run_rows)
            continue
        data = align(device, case, transistor, native, candidates)
        events = transition_events(device, case, data, selection)
        event_rows.extend(events)
        metric_rows.extend(metrics(device, case, data, events))
        save_wave(out / "waveforms" / f"{device.device_id}.csv", data)
        figure_dir = out / "figures" / device.device_id
        sequence = figure_dir / "01_prbs_sequence.png"
        plot_sequence(device, case, data, events, sequence)
        plot_event_zoom(device, case, data, events, figure_dir / "02_midtransition_event.png")
        if candidates["pad_match_v2"] is not None:
            plot_diagnostics(device, case, data, events, figure_dir / "03_pad_match_diagnostics.png")
        plot_eyes(device, case, data, figure_dir / "04_pad_eyes.png")
        sequence_paths.append(sequence)
        write_csv(out / "run_manifest.csv", run_rows)
        write_csv(out / "stress_events.csv", event_rows)
        write_csv(out / "metrics.csv", metric_rows)

    contact_sheet(sequence_paths, out / "00_three_buffer_prbs_contact_sheet.png")
    write_csv(out / "run_manifest.csv", run_rows)
    write_csv(out / "stress_events.csv", event_rows)
    write_csv(out / "metrics.csv", metric_rows)
    write_csv(out / "activation_audit.csv", activation_audit(event_rows))
    build_readme(out, metric_rows, event_rows, run_rows)
    print(out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--selection-csv", type=Path, default=DEFAULT_SELECTION_CSV)
    parser.add_argument("--hspice", type=Path, default=phase.base.DEFAULT_HSPICE)
    parser.add_argument("--ngspice", type=Path, default=phase.base.DEFAULT_NGSPICE)
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument(
        "--solver-profile",
        choices=sorted(phase.SOLVER_PROFILES),
        default="gear_relaxed",
    )
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    run(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
