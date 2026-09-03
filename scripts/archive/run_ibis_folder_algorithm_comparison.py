#!/usr/bin/env python3
"""Compare experimental pybis algorithms on model-adaptive IBIS stress cases."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import re
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
for path in (LOCAL_DEPS, ROOT / "scripts"):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from convert_ibis_to_pybis import convert  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from run_ibis_folder_full_swing_campaign import (  # noqa: E402
    Candidate,
    DEFAULT_SOURCE,
    extract_hspice,
    extract_ngspice,
    inventory,
    read_csv,
    run_process,
    write_csv,
)
from run_ibis_folder_stress_campaign import unique_ready  # noqa: E402
from spice_tool_paths import default_ngspice  # noqa: E402


DEFAULT_FULL_STUDY = ROOT / "results" / "external_ibis_full_swing_adaptive_v2_2026-08-07"
DEFAULT_STRESS_STUDY = ROOT / "results" / "external_ibis_adaptive_stress_2026-08-11"
DEFAULT_STUDY = ROOT / "results" / "external_ibis_algorithm_comparison_2026-08-11"

ALGORITHMS = {
    "value_match_v2": {
        "mode": "InputDrivenValueMatchedReplayV2Hybrid",
        "label": "value-matched replay v2",
        "color": "#CC79A7",
    },
    "gate_state_full": {
        "mode": "InputDrivenTwoStateGateDirectionalResidualFull",
        "label": "gate-state full",
        "color": "#D55E00",
    },
    "gate_state_hybrid": {
        "mode": "InputDrivenTwoStateGateDirectionalResidualHybrid",
        "label": "gate-state hybrid",
        "color": "#009E73",
    },
}

FLOW_STYLE = {
    "legacy": {"label": "legacy pybis", "color": "#0072B2"},
    **{key: {"label": value["label"], "color": value["color"]} for key, value in ALGORITHMS.items()},
}


def safe_float(value: object, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def unlink_with_retry(path: Path, attempts: int = 20, delay_s: float = 0.1) -> bool:
    """Remove a simulator output after Windows releases any closing file handle."""
    for _ in range(attempts):
        try:
            path.unlink(missing_ok=True)
            return True
        except PermissionError:
            time.sleep(delay_s)
    return False


def read_rows(path: Path) -> list[dict[str, str]]:
    return read_csv(path) if path.exists() else []


def row_index(rows: list[dict[str, str]], *keys: str) -> dict[tuple[str, ...], dict[str, str]]:
    return {tuple(str(row.get(key, "")) for key in keys): row for row in rows}


def subckt_name(path: Path) -> str:
    match = re.search(r"(?im)^\s*\.subckt\s+(\S+)", path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        raise RuntimeError("generated model has no .subckt declaration")
    return match.group(1)


def algorithm_times(candidate: Candidate, direction: str, stress_row: dict[str, str]) -> dict[str, float]:
    width = safe_float(stress_row.get("pulse_width_ns"))
    h_transition = safe_float(stress_row.get("transition_edge_ns"), candidate.rise_edge_ns)
    h_stop = safe_float(stress_row.get("stop_ns"), h_transition + 10.0)
    relative_stop = max(2.0, h_stop - h_transition)
    if direction == "short_high":
        transition = candidate.rise_edge_ns
    else:
        # Experimental models begin low internally. Give them the same complete
        # rising transition used by the full-swing campaign before launching the
        # interrupted falling transition.
        transition = candidate.fall_edge_ns
    reverse = transition + width
    return {
        "width_ns": width,
        "transition_ns": transition,
        "reverse_ns": reverse,
        "stop_ns": transition + relative_stop,
        "save_start_ns": max(0.0, transition - 1.0),
        "reference_transition_ns": h_transition,
    }


def stimulus_pwl(candidate: Candidate, direction: str, times: dict[str, float]) -> str:
    edge = candidate.input_edge_ns
    transition = times["transition_ns"]
    reverse = times["reverse_ns"]
    if direction == "short_high":
        points = [(0.0, 0.0), (transition, 0.0), (transition + edge, candidate.vcc), (reverse, candidate.vcc), (reverse + edge, 0.0)]
    else:
        rise = candidate.rise_edge_ns
        points = [
            (0.0, 0.0),
            (rise, 0.0),
            (rise + edge, candidate.vcc),
            (transition, candidate.vcc),
            (transition + edge, 0.0),
            (reverse, 0.0),
            (reverse + edge, candidate.vcc),
        ]
    return " ".join(f"{time_ns:.12g}n {value:.12g}" for time_ns, value in points)


def ngspice_deck(candidate: Candidate, direction: str, times: dict[str, float], name: str) -> str:
    enable_v = 0.0 if "active-low" in candidate.enable.lower() else candidate.vcc
    return f"""* Experimental pybis model-adaptive interrupted-transition comparison
.title {candidate.file_name} / {candidate.model} / {direction}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL({stimulus_pwl(candidate, direction, times)})
Ven en_sig 0 DC {enable_v:.12g}
Vdd vdd 0 DC {candidate.vcc:.12g}
.include 'algorithm.sub'
XDRV pad_n in_dig en_sig vdd 0 {name}
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n {times['stop_ns']:.12g}n {times['save_start_ns']:.12g}n
.end
"""


def raw_reaches(path: Path, stop_ns: float) -> bool:
    if not path.exists():
        return False
    try:
        data = parse_ngspice_raw(path)
        return len(data["time"]) > 2 and float(data["time"][-1]) >= 0.999 * stop_ns * 1e-9
    except Exception:
        return False


def classify(candidate: Candidate, h: dict[str, np.ndarray], n: dict[str, np.ndarray], h_transition_ns: float, n_transition_ns: float) -> dict[str, object]:
    h_rel = h["time"] - h_transition_ns * 1e-9
    n_rel = n["time"] - n_transition_ns * 1e-9
    start = max(float(h_rel[0]), float(n_rel[0]), -1e-9)
    stop = min(float(h_rel[-1]), float(n_rel[-1]))
    if stop <= start:
        raise RuntimeError("reference and algorithm waveforms have no aligned overlap")
    eval_t = np.linspace(start, stop, 30001)
    errors: dict[str, float] = {}
    for key in ("pad", "ku", "kd"):
        hv = np.interp(eval_t, h_rel, h[key])
        nv = np.interp(eval_t, n_rel, n[key])
        errors[key] = float(np.sqrt(np.mean(np.square(hv - nv))))
    pad_fraction = errors["pad"] / max(candidate.vcc, 1e-6)
    if pad_fraction <= 0.02 and errors["ku"] <= 0.05 and errors["kd"] <= 0.05:
        result_class = "GOOD"
    elif pad_fraction <= 0.05 and errors["ku"] <= 0.10 and errors["kd"] <= 0.10:
        result_class = "WARN"
    else:
        result_class = "CHECK"
    return {
        "comparison_class": result_class,
        "pad_rmse_mv": 1e3 * errors["pad"],
        "pad_rmse_pct_vcc": 100.0 * pad_fraction,
        "ku_rmse": errors["ku"],
        "kd_rmse": errors["kd"],
    }


def run_algorithm(
    candidate: Candidate,
    direction: str,
    algorithm: str,
    model_path: Path,
    stress_row: dict[str, str],
    h: dict[str, np.ndarray],
    study: Path,
    ngspice: Path,
    timeout_s: float,
    resume: bool,
) -> tuple[dict[str, object], dict[str, np.ndarray] | None, dict[str, float]]:
    times = algorithm_times(candidate, direction, stress_row)
    run_dir = study / "cases" / candidate.case_id / direction / algorithm
    run_dir.mkdir(parents=True, exist_ok=True)
    local_model = run_dir / "algorithm.sub"
    shutil.copy2(model_path, local_model)
    shutil.copy2(candidate.source_path, run_dir / candidate.declared_file_name)
    (run_dir / ".spiceinit").write_text("set filetype=binary\n", encoding="ascii")
    name = subckt_name(local_model)
    deck = run_dir / "run.sp"
    deck_text = ngspice_deck(candidate, direction, times, name)
    deck_changed = not deck.exists() or deck.read_text(encoding="ascii", errors="replace") != deck_text
    deck.write_text(deck_text, encoding="ascii")
    raw = run_dir / "run.raw"
    row: dict[str, object] = {
        "file": candidate.file_name,
        "model": candidate.model,
        "case_id": candidate.case_id,
        "direction": direction,
        "algorithm": algorithm,
        "subcircuit_type": ALGORITHMS[algorithm]["mode"],
        "pulse_width_ns": times["width_ns"],
        "status": "PENDING",
        "deck": str(deck.relative_to(ROOT)),
        "raw": str(raw.relative_to(ROOT)),
        "model_subcircuit": str(model_path.relative_to(ROOT)),
    }
    if not (resume and not deck_changed and raw_reaches(raw, times["stop_ns"])):
        if raw.exists() and not unlink_with_retry(raw):
            row.update(status="STALE_RAW_LOCK", error="existing raw file is still locked by ngspice")
            return row, None, times
        rc, runtime, _ = run_process(
            [str(ngspice), "-b", "-r", raw.name, deck.name],
            run_dir,
            run_dir / "stdout.log",
            timeout_s,
        )
        row["runtime_s"] = runtime
        if rc is None:
            row.update(status="NGSPICE_TIMEOUT", error="ngspice timeout")
            return row, None, times
        if rc != 0 or not raw.exists():
            row.update(status="NGSPICE_FAIL", error=f"ngspice return code {rc}")
            return row, None, times
    else:
        row["runtime_s"] = 0.0
    try:
        n = extract_ngspice(parse_ngspice_raw(raw))
        row.update(classify(candidate, h, n, times["reference_transition_ns"], times["transition_ns"]))
        row.update(status="COMPLETED", error="")
        return row, n, times
    except Exception as exc:
        row.update(status="ANALYSIS_FAIL", error=f"{type(exc).__name__}: {exc}")
        return row, None, times


def plot_algorithms(
    candidate: Candidate,
    direction: str,
    h: dict[str, np.ndarray],
    h_transition_ns: float,
    flows: dict[str, tuple[dict[str, np.ndarray], float]],
    width_ns: float,
    output: Path,
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True, constrained_layout=True)
    h_t = h["time"] * 1e9 - h_transition_ns
    for ax, key, label in zip(axes, ("pad", "ku", "kd"), ("pad (V)", "Ku", "Kd")):
        ax.plot(h_t, h[key], color="black", lw=4.0, alpha=0.72, zorder=1, label="HSPICE native IBIS")
        for index, (flow, (data, transition_ns)) in enumerate(flows.items()):
            style = FLOW_STYLE[flow]
            ax.plot(
                data["time"] * 1e9 - transition_ns,
                data[key],
                color=style["color"],
                lw=1.8,
                alpha=0.95,
                zorder=3 + index,
                label=style["label"],
            )
        ax.axvline(0.0, color="#777777", ls="--", lw=1.0)
        ax.axvline(width_ns, color="#7B3294", ls="--", lw=1.2)
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.24)
    axes[2].axhline(0.0, color="#999999", lw=0.8)
    axes[2].set_xlabel("time from first stressed edge (ns)")
    axes[0].legend(loc="best", ncol=2)
    axes[0].set_xlim(max(-1.0, float(h_t[0])), float(h_t[-1]))
    fig.suptitle(f"{candidate.file_name} | {candidate.model} | {direction} | {width_ns:.3f} ns")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def make_full_swing_figure(candidate: Candidate, full_row: dict[str, str] | None, full_study: Path, output: Path) -> None:
    source = full_study / "plots" / f"{candidate.case_id}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copy2(source, output)
        return
    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    ax.axis("off")
    status = full_row.get("status", "UNAVAILABLE") if full_row else "UNAVAILABLE"
    error = full_row.get("error", "full-swing result unavailable") if full_row else "full-swing result unavailable"
    ax.text(0.5, 0.58, f"{candidate.file_name} / {candidate.model}", ha="center", fontsize=18)
    ax.text(0.5, 0.42, f"Full-swing overlay unavailable: {status}", ha="center", fontsize=14)
    ax.text(0.5, 0.30, error, ha="center", fontsize=10, wrap=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def write_model_readme(
    candidate: Candidate,
    folder: Path,
    full_row: dict[str, str] | None,
    stress_rows: dict[str, dict[str, str]],
    algorithm_rows: list[dict[str, object]],
) -> None:
    lines = [
        f"# {candidate.file_name} / {candidate.model}",
        "",
        f"- Component: `{candidate.component}`",
        f"- Model type: `{candidate.model_type}`",
        f"- Supply: `{candidate.vcc:g} V`",
        f"- Full-swing legacy status/class: `{(full_row or {}).get('status', 'UNAVAILABLE')}` / `{(full_row or {}).get('comparison_class', '')}`",
        "",
        "## Figures",
        "",
        "- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.",
        "- `01_short_high_algorithms.png`: fall-after-rise stress comparison.",
        "- `02_short_low_algorithms.png`: rise-after-fall stress comparison.",
        "",
        "## Stress Status",
        "",
        "| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for direction in ("short_high", "short_low"):
        legacy = stress_rows.get(direction, {})
        lines.append(
            f"| {direction} | legacy | {legacy.get('status', 'UNAVAILABLE')} | {legacy.get('stress_class', '')} | "
            f"{legacy.get('pad_rmse_mv', '')} | {legacy.get('ku_rmse', '')} | {legacy.get('kd_rmse', '')} |"
        )
        for row in [item for item in algorithm_rows if item.get("direction") == direction]:
            lines.append(
                f"| {direction} | {row.get('algorithm')} | {row.get('status')} | {row.get('comparison_class', '')} | "
                f"{row.get('pad_rmse_mv', '')} | {row.get('ku_rmse', '')} | {row.get('kd_rmse', '')} |"
            )
    (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_inventory(
    study: Path,
    selected: list[Candidate],
    full_index: dict[tuple[str, str], dict[str, str]],
    stress_index: dict[tuple[str, str, str], dict[str, str]],
    algorithm_rows: list[dict[str, object]],
) -> None:
    algorithm_index = {(str(row.get("file")), str(row.get("model")), str(row.get("direction")), str(row.get("algorithm"))): row for row in algorithm_rows}
    rows: list[dict[str, object]] = []
    for candidate in selected:
        full = full_index.get((candidate.file_name, candidate.model), {})
        row: dict[str, object] = {
            "source_path": str(candidate.source_path),
            "file": candidate.file_name,
            "component": candidate.component,
            "model": candidate.model,
            "model_type": candidate.model_type,
            "enable": candidate.enable,
            "vcc_v": candidate.vcc,
            "sha256": candidate.sha256,
            "full_swing_status": full.get("status", "UNAVAILABLE"),
            "full_swing_class": full.get("comparison_class", ""),
        }
        for direction in ("short_high", "short_low"):
            legacy = stress_index.get((candidate.file_name, candidate.model, direction), {})
            row[f"legacy_{direction}_status"] = legacy.get("status", "UNAVAILABLE")
            row[f"legacy_{direction}_class"] = legacy.get("stress_class", "")
            row[f"{direction}_pulse_width_ns"] = legacy.get("pulse_width_ns", "")
            for algorithm in ALGORITHMS:
                result = algorithm_index.get((candidate.file_name, candidate.model, direction, algorithm), {})
                row[f"{algorithm}_{direction}_status"] = result.get("status", "NOT_RUN")
                row[f"{algorithm}_{direction}_class"] = result.get("comparison_class", "")
        row["figure_folder"] = str((study / "figures" / candidate.case_id).relative_to(ROOT))
        rows.append(row)
    write_csv(study / "simulated_ibis_models.csv", rows)

    by_file: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_file.setdefault(str(row["file"]), []).append(row)
    lines = [
        "# Simulated IBIS Files And Models",
        "",
        f"- Unique IBIS files: `{len(by_file)}`",
        f"- Unique applicable models: `{len(rows)}`",
        "- Exact duplicate files are suppressed by SHA-256, matching the full-swing and stress campaigns.",
        "",
        "| IBIS file | Component | Model | Type | VCC | Full swing | Legacy high/low | Value-match high/low | Gate full high/low | Gate hybrid high/low |",
        "|---|---|---|---|---:|---|---|---|---|---|",
    ]
    for row in rows:
        def pair(prefix: str) -> str:
            return f"{row.get(prefix + '_short_high_status', '')}/{row.get(prefix + '_short_low_status', '')}"
        lines.append(
            f"| {row['file']} | {row['component']} | {row['model']} | {row['model_type']} | {safe_float(row['vcc_v']):g} | "
            f"{row['full_swing_status']} | {pair('legacy')} | {pair('value_match_v2')} | {pair('gate_state_full')} | {pair('gate_state_hybrid')} |"
        )
    (study / "SIMULATED_IBIS_MODELS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_summary(study: Path, rows: list[dict[str, object]]) -> None:
    completed = [row for row in rows if row.get("status") == "COMPLETED"]
    if not completed:
        return
    labels = list(ALGORITHMS)
    classes = ("GOOD", "WARN", "CHECK")
    colors = {"GOOD": "#009E73", "WARN": "#E69F00", "CHECK": "#D55E00"}
    x = np.arange(len(labels))
    bottom = np.zeros(len(labels))
    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
    for result_class in classes:
        counts = np.array([sum(row.get("algorithm") == algorithm and row.get("comparison_class") == result_class for row in completed) for algorithm in labels])
        ax.bar(x, counts, bottom=bottom, color=colors[result_class], label=result_class)
        bottom += counts
    ax.set_xticks(x, [ALGORITHMS[key]["label"] for key in labels], rotation=12, ha="right")
    ax.set_ylabel("completed stress cases")
    ax.set_title("Experimental pybis algorithm outcomes")
    ax.legend()
    ax.grid(axis="y", alpha=0.24)
    output = study / "figures" / "00_algorithm_outcomes.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def write_comparison_summaries(
    study: Path,
    rows: list[dict[str, object]],
    stress_index: dict[tuple[str, str, str], dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    availability: list[dict[str, object]] = []
    versus_legacy: list[dict[str, object]] = []
    class_rank = {"CHECK": 0, "WARN": 1, "GOOD": 2}
    for algorithm in ALGORITHMS:
        for direction in ("short_high", "short_low"):
            subset = [
                row for row in rows
                if row.get("algorithm") == algorithm and row.get("direction") == direction
            ]
            availability.append({
                "algorithm": algorithm,
                "direction": direction,
                "total": len(subset),
                "completed": sum(row.get("status") == "COMPLETED" for row in subset),
                "good": sum(row.get("comparison_class") == "GOOD" for row in subset),
                "warn": sum(row.get("comparison_class") == "WARN" for row in subset),
                "check": sum(row.get("comparison_class") == "CHECK" for row in subset),
                "conversion_fail": sum(row.get("status") == "CONVERSION_FAIL" for row in subset),
                "ngspice_timeout": sum(row.get("status") == "NGSPICE_TIMEOUT" for row in subset),
                "ngspice_fail": sum(row.get("status") == "NGSPICE_FAIL" for row in subset),
            })
            deltas: list[int] = []
            for row in subset:
                legacy = stress_index.get(
                    (str(row.get("file")), str(row.get("model")), direction),
                    {},
                )
                algorithm_class = str(row.get("comparison_class", ""))
                legacy_class = str(legacy.get("stress_class", ""))
                if (
                    row.get("status") == "COMPLETED"
                    and legacy.get("status") == "COMPLETED"
                    and algorithm_class in class_rank
                    and legacy_class in class_rank
                ):
                    deltas.append(class_rank[algorithm_class] - class_rank[legacy_class])
            versus_legacy.append({
                "algorithm": algorithm,
                "direction": direction,
                "paired_completed_cases": len(deltas),
                "improved_class": sum(delta > 0 for delta in deltas),
                "same_class": sum(delta == 0 for delta in deltas),
                "worse_class": sum(delta < 0 for delta in deltas),
            })
    write_csv(study / "algorithm_summary.csv", availability)
    write_csv(study / "algorithm_vs_legacy.csv", versus_legacy)
    return availability, versus_legacy


def write_report(
    study: Path,
    selected: list[Candidate],
    rows: list[dict[str, object]],
    stress_index: dict[tuple[str, str, str], dict[str, str]],
) -> None:
    availability, versus_legacy = write_comparison_summaries(study, rows, stress_index)
    combined = []
    for algorithm in ALGORITHMS:
        values = [row for row in versus_legacy if row["algorithm"] == algorithm]
        combined.append({
            "algorithm": algorithm,
            "paired": sum(int(row["paired_completed_cases"]) for row in values),
            "improved": sum(int(row["improved_class"]) for row in values),
            "same": sum(int(row["same_class"]) for row in values),
            "worse": sum(int(row["worse_class"]) for row in values),
        })
    lines = [
        "# External IBIS Algorithm Comparison",
        "",
        "This package places the full-swing result and all interrupted-transition algorithm figures together for each IBIS model.",
        "",
        "## Headline Findings",
        "",
        "- No experimental algorithm is a universal winner across all models and both reversal directions.",
    ]
    for row in combined:
        lines.append(
            f"- `{row['algorithm']}` versus legacy on `{row['paired']}` paired completed cases: "
            f"class improved/same/worse `{row['improved']}`/`{row['same']}`/`{row['worse']}`."
        )
    lines.extend([
        "- Gate-state full produces the most class improvements; gate-state hybrid has the fewest class regressions. Value matching is usually unchanged from legacy.",
        "- Timeout rows are numerical-availability findings, not waveform CHECK classifications; no missing curve is counted as a fit failure.",
        "",
        "## Algorithms",
        "",
        "- `legacy`: existing InputDriven table replay baseline.",
        "- `value_match_v2`: corrected value-matched opposite-table replay.",
        "- `gate_state_full`: directional+rate-residual gate-state model used for all transitions.",
        "- `gate_state_hybrid`: legacy normal behavior with directional+rate-residual gate-state handling during interruption.",
        "",
        "## Coverage",
        "",
        f"- Applicable models: `{len(selected)}`.",
    ])
    for algorithm in ALGORITHMS:
        algorithm_rows = [row for row in availability if row.get("algorithm") == algorithm]
        lines.append(
            f"- `{algorithm}`: completed `{sum(int(row['completed']) for row in algorithm_rows)}` / "
            f"`{sum(int(row['total']) for row in algorithm_rows)}`; GOOD/WARN/CHECK "
            f"`{sum(int(row['good']) for row in algorithm_rows)}`/"
            f"`{sum(int(row['warn']) for row in algorithm_rows)}`/"
            f"`{sum(int(row['check']) for row in algorithm_rows)}`."
        )
    failures = [row for row in rows if row.get("status") != "COMPLETED"]
    lines.extend([
        "",
        "## Files",
        "",
        "- `simulated_ibis_models.csv` and `SIMULATED_IBIS_MODELS.md`: exact file/model inventory and status.",
        "- `algorithm_metrics.csv`: per-algorithm stress metrics.",
        "- `algorithm_summary.csv`: completion and class counts by algorithm/direction.",
        "- `algorithm_vs_legacy.csv`: paired class improvement/same/regression counts.",
        "- `figures/<case>/00_full_swing.png`: full-swing baseline.",
        "- `figures/<case>/01_short_high_algorithms.png`: fall-after-rise algorithms.",
        "- `figures/<case>/02_short_low_algorithms.png`: rise-after-fall algorithms.",
        "- `cases/<case>/<direction>/<algorithm>/`: generated subcircuit, deck, raw, and log.",
        "",
        "## Explicit Failures",
        "",
    ])
    if failures:
        for row in failures:
            lines.append(
                f"- `{row.get('file')} / {row.get('model')} / {row.get('direction')} / {row.get('algorithm')}`: "
                f"`{row.get('status')}` - {row.get('error', '')}"
            )
    else:
        lines.append("None.")
    (study / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--full-study", type=Path, default=DEFAULT_FULL_STUDY)
    parser.add_argument("--stress-study", type=Path, default=DEFAULT_STRESS_STUDY)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--algorithms", default=",".join(ALGORITHMS))
    parser.add_argument("--select-regex")
    parser.add_argument("--max-models", type=int)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    args = parser.parse_args()

    study = args.study_dir.resolve()
    full_study = args.full_study.resolve()
    stress_study = args.stress_study.resolve()
    study.mkdir(parents=True, exist_ok=True)
    candidates, _ = inventory(args.source_dir.resolve())
    selected = unique_ready(candidates)
    if args.select_regex:
        pattern = re.compile(args.select_regex, re.IGNORECASE)
        selected = [candidate for candidate in selected if pattern.search(f"{candidate.file_name}/{candidate.model}")]
    if args.max_models is not None:
        selected = selected[: args.max_models]
    requested = [item.strip() for item in args.algorithms.split(",") if item.strip()]
    unknown = [item for item in requested if item not in ALGORITHMS]
    if unknown:
        raise SystemExit(f"unknown algorithms: {', '.join(unknown)}")

    full_rows = read_rows(full_study / "metrics.csv")
    stress_rows = read_rows(stress_study / "metrics.csv")
    full_index = row_index(full_rows, "file", "model")
    stress_index = row_index(stress_rows, "file", "model", "direction")
    existing_rows = read_rows(study / "algorithm_metrics.csv") if args.resume or args.report_only else []
    result_rows: list[dict[str, object]] = [dict(row) for row in existing_rows]
    result_index = {(str(row.get("file")), str(row.get("model")), str(row.get("direction")), str(row.get("algorithm"))): index for index, row in enumerate(result_rows)}

    if not args.report_only:
        total = len(selected)
        for candidate_number, candidate in enumerate(selected, start=1):
            print(f"[{candidate_number}/{total}] {candidate.file_name} / {candidate.model}", flush=True)
            figure_dir = study / "figures" / candidate.case_id
            full_row = full_index.get((candidate.file_name, candidate.model))
            make_full_swing_figure(candidate, full_row, full_study, figure_dir / "00_full_swing.png")

            converted: dict[str, Path] = {}
            conversion_errors: dict[str, str] = {}
            for algorithm in requested:
                model_dir = study / "models" / candidate.case_id / algorithm
                model_dir.mkdir(parents=True, exist_ok=True)
                model_path = model_dir / "algorithm.sub"
                try:
                    if not (args.resume and model_path.exists()):
                        started = time.perf_counter()
                        convert(
                            candidate.source_path,
                            model_path,
                            candidate.component,
                            candidate.model,
                            "Output",
                            ALGORITHMS[algorithm]["mode"],
                            "Typical",
                        )
                        (model_dir / "conversion_runtime.txt").write_text(f"{time.perf_counter() - started:.6f}\n", encoding="ascii")
                    converted[algorithm] = model_path
                except Exception as exc:
                    conversion_errors[algorithm] = f"{type(exc).__name__}: {exc}"
                    (model_dir / "conversion_error.txt").write_text(conversion_errors[algorithm] + "\n", encoding="utf-8")

            candidate_results: list[dict[str, object]] = []
            candidate_stress: dict[str, dict[str, str]] = {}
            for direction_index, direction in enumerate(("short_high", "short_low"), start=1):
                stress_row = stress_index.get((candidate.file_name, candidate.model, direction))
                if stress_row is None:
                    continue
                candidate_stress[direction] = stress_row
                h_path_text = stress_row.get("hspice_tr0", "")
                h_path = ROOT / h_path_text if h_path_text else Path()
                if not h_path.exists():
                    continue
                h = extract_hspice(parse_hspice_tr0(h_path))
                h_transition = safe_float(stress_row.get("transition_edge_ns"), candidate.rise_edge_ns)
                width = safe_float(stress_row.get("pulse_width_ns"))
                flows: dict[str, tuple[dict[str, np.ndarray], float]] = {}
                legacy_raw_text = stress_row.get("ngspice_raw", "")
                legacy_raw = ROOT / legacy_raw_text if legacy_raw_text else Path()
                if legacy_raw.exists():
                    try:
                        flows["legacy"] = (extract_ngspice(parse_ngspice_raw(legacy_raw)), h_transition)
                    except Exception:
                        pass
                for algorithm in requested:
                    key = (candidate.file_name, candidate.model, direction, algorithm)
                    existing_row = result_rows[result_index[key]] if args.resume and key in result_index else None
                    existing_status = str(existing_row.get("status", "")) if existing_row else ""
                    terminal_statuses = {
                        "CONVERSION_FAIL",
                        "NGSPICE_TIMEOUT",
                        "NGSPICE_FAIL",
                        "ANALYSIS_FAIL",
                        "STALE_RAW_LOCK",
                    }
                    if existing_row is not None and existing_status in terminal_statuses:
                        row = existing_row
                        n = None
                        times = algorithm_times(candidate, direction, stress_row)
                    elif algorithm in conversion_errors:
                        row = {
                            "file": candidate.file_name,
                            "model": candidate.model,
                            "case_id": candidate.case_id,
                            "direction": direction,
                            "algorithm": algorithm,
                            "subcircuit_type": ALGORITHMS[algorithm]["mode"],
                            "pulse_width_ns": width,
                            "status": "CONVERSION_FAIL",
                            "error": conversion_errors[algorithm],
                        }
                        n = None
                        times = algorithm_times(candidate, direction, stress_row)
                    else:
                        row, n, times = run_algorithm(
                            candidate,
                            direction,
                            algorithm,
                            converted[algorithm],
                            stress_row,
                            h,
                            study,
                            args.ngspice,
                            args.timeout_s,
                            args.resume,
                        )
                    if key in result_index:
                        result_rows[result_index[key]] = row
                    else:
                        result_index[key] = len(result_rows)
                        result_rows.append(row)
                    candidate_results.append(row)
                    write_csv(study / "algorithm_metrics.csv", result_rows)
                    if n is not None:
                        flows[algorithm] = (n, times["transition_ns"])
                    print(f"  {direction} / {algorithm}: {row.get('status')} {row.get('comparison_class', '')}", flush=True)
                plot_algorithms(
                    candidate,
                    direction,
                    h,
                    h_transition,
                    flows,
                    width,
                    figure_dir / f"{direction_index:02d}_{direction}_algorithms.png",
                )
            write_model_readme(candidate, figure_dir, full_row, candidate_stress, candidate_results)
            write_inventory(study, selected, full_index, stress_index, result_rows)
            plot_summary(study, result_rows)
            write_report(study, selected, result_rows, stress_index)
    else:
        write_inventory(study, selected, full_index, stress_index, result_rows)
        plot_summary(study, result_rows)
        write_report(study, selected, result_rows, stress_index)

    print(f"Wrote {study}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
