from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_three_buffer_prbs_phase1 as phase  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402


BASELINE_DIR = ROOT / "results" / "three_buffer_prbs_phase1_2026-07-31"
OUT_DIR = ROOT / "results" / "three_buffer_prbs_hybrid_v2_2026-07-31"
MODE = phase.HYBRID_V2_MODE
FLOW = "ngspice_hybrid_v2"
PURPLE = "#7b2cbf"
BLUE = "#1769aa"
BLACK = "#111111"
GRAY = "#737373"
GREEN = "#008b6e"
GRID = "#d9dde3"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    base.write_csv(path, rows)


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="ascii")


def prepare_model(device: base.Device) -> Path:
    output = OUT_DIR / "models" / device.device_id / f"{device.subckt}.sub"
    base.convert_ibis_to_pybis(
        ibis_path=device.fast_ibis,
        output_path=output,
        component_name=device.component,
        model_name=device.model,
        io_type="Output",
        subcircuit_type=MODE,
        corner="Typical",
    )
    return output


def baseline_waveform(device: base.Device, case: phase.PrbsCase) -> dict[str, np.ndarray]:
    path = BASELINE_DIR / "waveforms" / device.device_id / f"{case.case_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"missing cached Phase 1 waveform: {path}")
    return phase.load_waveform(path)


def merge_v2(
    baseline: dict[str, np.ndarray],
    raw: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    wave = base.ngspice_waveform(raw)
    result = {name: np.asarray(values) for name, values in baseline.items()}
    time_ns = result["time_ns"]
    for name, values in wave.items():
        if name in {"time_ns", "input_v"}:
            continue
        result[f"{FLOW}_{name}"] = np.interp(time_ns, wave["time_ns"], values)
    return result


def save_waveform(path: Path, data: dict[str, np.ndarray]) -> None:
    ensure_dir(path.parent)
    names = list(data)
    np.savetxt(
        path,
        np.column_stack([data[name] for name in names]),
        delimiter=",",
        header=",".join(names),
        comments="",
        fmt="%.10g",
    )


def rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.sqrt(np.mean((candidate - reference) ** 2)))


def active_intervals(case: phase.PrbsCase, data: dict[str, np.ndarray]) -> list[tuple[int, int]]:
    key = f"{FLOW}_hhybridv2active"
    if key not in data:
        return []
    active = (data[key] > 0.5) & phase.analysis_mask(case, data["time_ns"])
    edges = np.diff(active.astype(np.int8), prepend=0, append=0)
    starts = np.flatnonzero(edges == 1)
    stops = np.flatnonzero(edges == -1) - 1
    return list(zip(starts.tolist(), stops.tolist()))


def event_rows(
    device: base.Device,
    case: phase.PrbsCase,
    data: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    time_ns = data["time_ns"]
    for event_index, (start, stop) in enumerate(active_intervals(case, data), start=1):
        section = slice(start, stop + 1)
        fall = np.any(data.get(f"{FLOW}_hfall_after_rise", np.zeros_like(time_ns))[section] > 0.5)
        rise = np.any(data.get(f"{FLOW}_hrise_after_fall", np.zeros_like(time_ns))[section] > 0.5)
        kind = "BOTH" if fall and rise else "FALL_AFTER_RISE" if fall else "RISE_AFTER_FALL" if rise else "UNCLASSIFIED"
        row: dict[str, object] = {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000.0,
            "event_index": event_index,
            "event_kind": kind,
            "start_ns": float(time_ns[start]),
            "stop_ns": float(time_ns[stop]),
            "duration_ns": float(time_ns[stop] - time_ns[start]),
            "duration_ui": float((time_ns[stop] - time_ns[start]) / case.ui_ns),
        }
        for output, key in (
            ("ku_sample", f"{FLOW}_v2kusamp"),
            ("kd_sample", f"{FLOW}_v2kdsamp"),
            ("ku_start_error", f"{FLOW}_v2starterrku"),
            ("kd_start_error", f"{FLOW}_v2starterrkd"),
            ("gup", f"{FLOW}_gup"),
            ("gdn", f"{FLOW}_gdn"),
        ):
            row[output] = float(data[key][start]) if key in data else float("nan")
        for output, candidate, reference in (
            ("max_pad_error_v", f"{FLOW}_pad_v", "hspice_native_ibis_pad_v"),
            ("max_ku_error", f"{FLOW}_ku", "hspice_native_ibis_ku"),
            ("max_kd_error", f"{FLOW}_kd", "hspice_native_ibis_kd"),
        ):
            row[output] = float(np.max(np.abs(data[candidate][section] - data[reference][section])))
        rows.append(row)
    return rows


def case_metrics(
    device: base.Device,
    case: phase.PrbsCase,
    data: dict[str, np.ndarray],
    status: str,
) -> dict[str, object]:
    row: dict[str, object] = {
        "device": device.device_id,
        "case_id": case.case_id,
        "ui_ps": case.ui_ns * 1000.0,
        "flow": FLOW,
        "status": status,
    }
    key = f"{FLOW}_pad_v"
    if key not in data:
        return row
    mask = phase.analysis_mask(case, data["time_ns"])
    active_key = f"{FLOW}_hhybridv2active"
    active = data[active_key][mask] > 0.5 if active_key in data else np.zeros(np.count_nonzero(mask), dtype=bool)
    metrics = {}
    for signal in ("pad_v", "ku", "kd"):
        reference = data[f"hspice_native_ibis_{signal}"][mask]
        candidate = data[f"{FLOW}_{signal}"][mask]
        metrics[f"{signal}_rmse_vs_native"] = rmse(reference, candidate)
        metrics[f"{signal}_max_error_vs_native"] = float(np.max(np.abs(candidate - reference)))
    ku = data[f"{FLOW}_ku"][mask]
    kd = data[f"{FLOW}_kd"][mask]
    intervals = active_intervals(case, data)
    handoff_indices = [start for start, _ in intervals]

    def at_handoffs(key: str) -> np.ndarray:
        if key not in data or not handoff_indices:
            return np.array([], dtype=float)
        return np.asarray(data[key])[handoff_indices]

    def handoff_jumps(signal: str) -> np.ndarray:
        values = np.asarray(data[f"{FLOW}_{signal}"])
        jumps = [abs(float(values[start]) - float(values[start - 1])) for start in handoff_indices if start > 0]
        return np.asarray(jumps, dtype=float)

    ku_handoff_jumps = handoff_jumps("ku")
    kd_handoff_jumps = handoff_jumps("kd")
    ku_start_errors = at_handoffs(f"{FLOW}_v2starterrku")
    kd_start_errors = at_handoffs(f"{FLOW}_v2starterrkd")
    eye = phase.optimize_eye(case, data["time_ns"], data[f"{FLOW}_pad_v"])
    row.update(metrics)
    row.update(
        {
            "eye_height_v": eye["eye_height_v"],
            "eye_width_ns": eye["eye_width_ns"],
            "best_delay_ns": eye["best_delay_ns"],
            "hybrid_active_fraction": float(np.mean(active)),
            "hybrid_activation_count": len(intervals),
            "ku_min": float(np.min(ku)),
            "ku_max": float(np.max(ku)),
            "kd_min": float(np.min(kd)),
            "kd_max": float(np.max(kd)),
            "max_ku_step": float(np.max(ku_handoff_jumps)) if ku_handoff_jumps.size else 0.0,
            "max_kd_step": float(np.max(kd_handoff_jumps)) if kd_handoff_jumps.size else 0.0,
            "max_start_error_ku": float(np.max(ku_start_errors)) if ku_start_errors.size else 0.0,
            "max_start_error_kd": float(np.max(kd_start_errors)) if kd_start_errors.size else 0.0,
            "coefficient_range_ok": bool(np.min(ku) >= -0.2 and np.max(ku) <= 1.2 and np.min(kd) >= -0.2 and np.max(kd) <= 1.2),
        }
    )
    old_available = f"ngspice_hybrid_pad_v" in data
    if old_available:
        improvements = []
        for signal in ("pad_v", "ku", "kd"):
            reference = data[f"hspice_native_ibis_{signal}"][mask]
            old = rmse(reference, data[f"ngspice_hybrid_{signal}"][mask])
            new = float(row[f"{signal}_rmse_vs_native"])
            row[f"old_hybrid_{signal}_rmse_vs_native"] = old
            row[f"v2_improvement_{signal}_percent"] = 100.0 * (old - new) / max(old, 1e-15)
            improvements.append(new < old)
        row["comparison_class"] = "IMPROVES_PAD_KU_KD" if all(improvements) else "MIXED" if any(improvements) else "WORSE_ALL"
    else:
        row["comparison_class"] = "NO_OLD_HYBRID_RESULT"
    if not intervals:
        row["validation_class"] = "NO_TRIGGER_CONTROL"
    elif not row["coefficient_range_ok"]:
        row["validation_class"] = "INVALID_COEFFICIENT_RANGE"
    elif float(row["max_ku_step"]) > 0.02 or float(row["max_kd_step"]) > 0.02:
        row["validation_class"] = "HANDOFF_DISCONTINUITY"
    elif row["comparison_class"] != "IMPROVES_PAD_KU_KD":
        row["validation_class"] = "NO_CONSISTENT_IMPROVEMENT"
    else:
        row["validation_class"] = "CANDIDATE_PASS"
    return row


def style(axis: plt.Axes) -> None:
    axis.grid(True, color=GRID, linewidth=0.7, alpha=0.75)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)


def plot_case(device: base.Device, case: phase.PrbsCase, data: dict[str, np.ndarray]) -> Path:
    output = OUT_DIR / "plots" / "cases" / device.device_id / case.case_id / "01_hybrid_v2_evidence.png"
    ensure_dir(output.parent)
    start = case.analysis_start_ns
    stop = start + 32.0 * case.ui_ns
    mask = (data["time_ns"] >= start) & (data["time_ns"] <= stop)
    x = (data["time_ns"][mask] - start) / case.ui_ns
    figure, axes = plt.subplots(5, 1, figsize=(16, 13), sharex=True)
    axes[0].plot(x, data["input_v"][mask], color=GREEN, linewidth=1.5)
    axes[0].set_ylabel("Input (V)")
    pad_flows = [
        ("hspice_transistor_pad_v", GRAY, "HSPICE transistor", 2.5),
        ("hspice_native_ibis_pad_v", BLACK, "HSPICE native IBIS", 3.1),
        ("ngspice_hybrid_pad_v", BLUE, "old hybrid", 1.7),
        (f"{FLOW}_pad_v", PURPLE, "Hybrid V2", 2.1),
    ]
    for key, color, label, linewidth in pad_flows:
        if key in data:
            axes[1].plot(x, data[key][mask], color=color, label=label, linewidth=linewidth)
    axes[1].set_ylabel("Pad (V)")
    for axis, signal in ((axes[2], "ku"), (axes[3], "kd")):
        for key, color, label, linewidth in (
            (f"hspice_native_ibis_{signal}", BLACK, "HSPICE native IBIS", 3.1),
            (f"ngspice_hybrid_{signal}", BLUE, "old hybrid", 1.7),
            (f"{FLOW}_{signal}", PURPLE, "Hybrid V2", 2.1),
        ):
            if key in data:
                axis.plot(x, data[key][mask], color=color, label=label, linewidth=linewidth)
        axis.set_ylabel(signal.capitalize())
    axes[3].axhline(0.0, color="#999999", linewidth=0.8)
    active_key = f"{FLOW}_hhybridv2active"
    if active_key in data:
        axes[4].plot(x, data[active_key][mask], color=PURPLE, linewidth=2.0, label="V2 active")
    for key, color, label in (
        (f"{FLOW}_v2kuprogress", "#d97706", "Ku progress"),
        (f"{FLOW}_v2kdprogress", "#008b6e", "Kd progress"),
    ):
        if key in data:
            axes[4].plot(x, data[key][mask], color=color, linewidth=1.4, label=label)
    axes[4].set_ylabel("Event state")
    axes[4].set_xlabel("Bit position in analyzed PRBS window (UI)")
    for start_index, stop_index in active_intervals(case, data):
        left = (data["time_ns"][start_index] - start) / case.ui_ns
        right = (data["time_ns"][stop_index] - start) / case.ui_ns
        for axis in axes[1:]:
            axis.axvspan(left, right, color=PURPLE, alpha=0.08, linewidth=0)
    for axis in axes:
        style(axis)
    handles, labels = axes[1].get_legend_handles_labels()
    figure.suptitle(f"{device.label}: Hybrid V2, UI = {case.ui_ns * 1000:.0f} ps", fontsize=17, y=0.985)
    figure.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.962))
    figure.subplots_adjust(top=0.925, bottom=0.065, hspace=0.10)
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_summary(rows: list[dict[str, object]]) -> None:
    completed = [row for row in rows if row.get("status") == "COMPLETED"]
    if not completed:
        return
    ensure_dir(OUT_DIR / "plots")
    figure, axes = plt.subplots(3, 3, figsize=(17, 12), constrained_layout=True)
    for row_index, device in enumerate(base.DEVICES):
        selected = sorted(
            [row for row in completed if row["device"] == device.device_id],
            key=lambda row: float(row["ui_ps"]),
        )
        x = [float(row["ui_ps"]) for row in selected]
        for column, (field, ylabel) in enumerate(
            (
                ("pad_v_rmse_vs_native", "Pad RMSE (mV)"),
                ("ku_rmse_vs_native", "Ku RMSE"),
                ("kd_rmse_vs_native", "Kd RMSE"),
            )
        ):
            axis = axes[row_index, column]
            scale = 1000.0 if column == 0 else 1.0
            axis.plot(x, [scale * float(row[field]) for row in selected], color=PURPLE, marker="o", linewidth=2.2, label="Hybrid V2")
            old_field = f"old_hybrid_{'pad_v' if column == 0 else 'ku' if column == 1 else 'kd'}_rmse_vs_native"
            old_rows = [row for row in selected if old_field in row]
            if old_rows:
                axis.plot(
                    [float(row["ui_ps"]) for row in old_rows],
                    [scale * float(row[old_field]) for row in old_rows],
                    color=BLUE,
                    marker="s",
                    linewidth=1.8,
                    label="old hybrid",
                )
            axis.set_xscale("log")
            axis.set_xticks([250, 500, 1000, 2000], ["250", "500", "1000", "2000"])
            axis.set_title(f"{device.label}: {ylabel}")
            axis.set_xlabel("UI (ps)")
            axis.set_ylabel(ylabel)
            axis.legend(frameon=False)
            style(axis)
    figure.suptitle("Hybrid V2 correlation versus old hybrid", fontsize=18)
    figure.savefig(OUT_DIR / "plots" / "00_hybrid_v2_metric_summary.png", dpi=180)
    plt.close(figure)


def write_readme(rows: list[dict[str, object]], events: list[dict[str, object]]) -> None:
    completed = [row for row in rows if row.get("status") == "COMPLETED"]
    all_better = [row for row in completed if row.get("comparison_class") == "IMPROVES_PAD_KU_KD"]
    mixed = [row for row in completed if row.get("comparison_class") == "MIXED"]
    candidate_passes = [row for row in completed if row.get("validation_class") == "CANDIDATE_PASS"]
    triggered = [row for row in completed if int(row.get("hybrid_activation_count", 0)) > 0]
    invalid_range = [row for row in completed if row.get("validation_class") == "INVALID_COEFFICIENT_RANGE"]
    discontinuous = [row for row in completed if row.get("validation_class") == "HANDOFF_DISCONTINUITY"]
    failures = [row for row in rows if row.get("status") != "COMPLETED"]
    lines = [
        "# Three-Buffer PRBS Hybrid V2",
        "",
        "Hybrid V2 keeps legacy Ku(t)/Kd(t) during normal operation. At an interrupted reversal it freezes the continuously tracked directional gate-map coefficients in capacitor-backed sample/hold nodes, then advances independent normalized legacy Ku(t) and Kd(t) transition shapes from those anchors.",
        "",
        "## Headline Finding",
        "",
        "- The exact sampled-start proposal is **not viable in its current form**.",
        "- A relative RMSE improvement is not a pass: the handoff must also be continuous, coefficients must remain physical, and the output eye must remain usable.",
        "- The main failure is coordinate mismatch at handoff: the directional gate-map value can be far from the currently visible legacy coefficient at the same reversal. Freezing that value preserves the mismatch rather than fixing it.",
        "- Independent normalized Ku/Kd progress preserves the table's relative transition shape, but it cannot repair a wrong starting anchor.",
        "",
        "## Execution",
        "",
        f"- Completed ngspice cases: `{len(completed)}/{len(rows)}`.",
        "- HSPICE simulations run by this study: `0`. All references come from the cached Phase 1 numeric waveforms.",
        f"- Cases improving pad, Ku, and Kd together versus the old hybrid: `{len(all_better)}`.",
        f"- Cases passing all Hybrid V2 validity gates: `{len(candidate_passes)}`.",
        f"- Completed cases with an actual Hybrid V2 trigger: `{len(triggered)}`.",
        f"- Triggered cases with invalid coefficient range: `{len(invalid_range)}`.",
        f"- Triggered cases with a handoff jump above 0.02 but otherwise valid range: `{len(discontinuous)}`.",
        f"- Mixed cases: `{len(mixed)}`.",
        f"- Numeric failures: `{len(failures)}`.",
        f"- Captured Hybrid V2 replay events: `{len(events)}`.",
        "",
        "## Interpretation",
        "",
        "A useful result must improve coefficients as well as pad voltage. `comparison_class` is relative to the old hybrid; `validation_class` is the actual safety result. Large event-start error or handoff jump means the gate-map initialization is discontinuous. A long active fraction means the replay has become a sustained alternate mode rather than a brief retrigger correction.",
        "",
        "## Runtime Sequence",
        "",
        "1. Legacy Ku(t)/Kd(t) drive the output while hidden GUP/GDN states track every command.",
        "2. A detected reversal opens a 20 ps sample window and freezes Ku(GUP)/Kd(GDN).",
        "3. After 25 ps, separate normalized Ku(t) and Kd(t) progress coordinates advance from the frozen anchors toward the new endpoints.",
        "4. Outside that replay interval, control returns to legacy Ku(t)/Kd(t).",
        "",
        "## Files",
        "",
        "- `metrics.csv`: pad/Ku/Kd errors, eye metrics, active fraction, coefficient steps, and old-hybrid deltas.",
        "- `hybrid_v2_events.csv`: every replay event with direction, duration, sampled coefficients, and event-window errors.",
        "- `waveforms/`: complete aligned numeric data, including V2 samples, progress, replay, and active state.",
        "- `plots/00_hybrid_v2_metric_summary.png`: matrix-level comparison.",
        "- `plots/cases/`: one detailed evidence figure per case.",
        "- `../three_buffer_prbs_hybrid_v2_continuous_anchor_2026-07-31/`: archived moving-anchor approximation; retained as diagnostic evidence only.",
    ]
    if failures:
        lines.extend(["", "## Failures", ""])
        for row in failures:
            lines.append(f"- `{row['device']} / {row['case_id']}`: `{row['status']}`")
    write_text(OUT_DIR / "README.md", "\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> None:
    global OUT_DIR
    phase.OUT_DIR = OUT_DIR
    selected_devices = [device for device in base.DEVICES if device.device_id in args.devices]
    selected_cases = phase.cases(tuple(args.uis_ns))
    metric_rows: list[dict[str, object]] = []
    event_data: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []
    total = len(selected_devices) * len(selected_cases)
    index = 0
    for device in selected_devices:
        model = prepare_model(device)
        for case in selected_cases:
            index += 1
            print(f"[{index}/{total}] {device.device_id} | UI {case.ui_ns * 1000:.0f} ps", flush=True)
            baseline = baseline_waveform(device, case)
            raw, run_row = phase.run_ngspice(
                device,
                case,
                FLOW,
                MODE,
                model,
                args.ngspice,
                args.timeout_s,
                args.retry_failures,
                args.solver_profile,
            )
            manifest.append(run_row)
            if raw is None:
                stale_waveform = OUT_DIR / "waveforms" / device.device_id / f"{case.case_id}.csv"
                stale_plot = OUT_DIR / "plots" / "cases" / device.device_id / case.case_id / "01_hybrid_v2_evidence.png"
                for stale_path in (stale_waveform, stale_plot):
                    if stale_path.exists():
                        stale_path.unlink()
                metric_rows.append(
                    {
                        "device": device.device_id,
                        "case_id": case.case_id,
                        "ui_ps": case.ui_ns * 1000.0,
                        "flow": FLOW,
                        "status": run_row["status"],
                    }
                )
                continue
            data = merge_v2(baseline, raw)
            save_waveform(OUT_DIR / "waveforms" / device.device_id / f"{case.case_id}.csv", data)
            metric_rows.append(case_metrics(device, case, data, str(run_row["status"])))
            event_data.extend(event_rows(device, case, data))
            plot_case(device, case, data)
            print("  waveform, metrics, events, and plot written", flush=True)
    write_csv(OUT_DIR / "run_manifest.csv", manifest)
    write_csv(OUT_DIR / "metrics.csv", metric_rows)
    write_csv(OUT_DIR / "hybrid_v2_events.csv", event_data)
    plot_summary(metric_rows)
    write_readme(metric_rows, event_data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PRBS comparison for state-initialized Hybrid V2.")
    parser.add_argument("--ngspice", type=Path, default=base.DEFAULT_NGSPICE)
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument("--devices", nargs="+", choices=[device.device_id for device in base.DEVICES], default=[device.device_id for device in base.DEVICES])
    parser.add_argument("--uis-ns", nargs="+", type=float, default=list(phase.UI_VALUES_NS))
    parser.add_argument("--solver-profile", choices=sorted(phase.SOLVER_PROFILES), default="trap_relaxed")
    parser.add_argument("--retry-failures", action="store_true")
    parser.add_argument("--study-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    global OUT_DIR
    args = parse_args()
    if args.study_dir is not None:
        OUT_DIR = args.study_dir if args.study_dir.is_absolute() else ROOT / args.study_dir
    ensure_dir(OUT_DIR)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
