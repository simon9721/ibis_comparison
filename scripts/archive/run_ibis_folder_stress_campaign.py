#!/usr/bin/env python3
"""Run model-adaptive interrupted-transition stress cases over an IBIS corpus."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import re
import shutil
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
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


DEFAULT_FULL_STUDY = ROOT / "results" / "external_ibis_full_swing_adaptive_v2_2026-08-07"
DEFAULT_STUDY = ROOT / "results" / "external_ibis_adaptive_stress_2026-08-11"
DIRECTIONS = ("short_high", "short_low")


def unique_ready(candidates: list[Candidate]) -> list[Candidate]:
    ready = [candidate for candidate in candidates if candidate.applicability == "READY_PUSH_PULL"]
    canonical_by_hash: dict[str, str] = {}
    for candidate in ready:
        canonical_by_hash.setdefault(candidate.sha256, candidate.file_name)
    return [candidate for candidate in ready if candidate.file_name == canonical_by_hash[candidate.sha256]]


def interp_at(h: dict[str, np.ndarray], key: str, time_s: float) -> float:
    return float(np.interp(time_s, h["time"], h[key]))


def select_reverse_width(candidate: Candidate, h: dict[str, np.ndarray], direction: str) -> dict[str, float | str]:
    edge_s = candidate.input_edge_ns * 1e-9
    if direction == "short_high":
        transition_start_s = candidate.rise_edge_ns * 1e-9
        search_start_s = transition_start_s + edge_s
        search_stop_s = (candidate.fall_edge_ns - 0.5) * 1e-9
        endpoint_s = search_stop_s
        fallback_ns = max(0.1, 0.5 * candidate.rise_settle_ns)
    else:
        transition_start_s = candidate.fall_edge_ns * 1e-9
        search_start_s = transition_start_s + edge_s
        search_stop_s = (candidate.stop_ns - 0.5) * 1e-9
        endpoint_s = search_stop_s
        fallback_ns = max(0.1, 0.5 * candidate.fall_settle_ns)

    initial_s = max(0.0, transition_start_s - 0.1e-9)
    initial = np.asarray([interp_at(h, "ku", initial_s), interp_at(h, "kd", initial_s)])
    final = np.asarray([interp_at(h, "ku", endpoint_s), interp_at(h, "kd", endpoint_s)])
    usable = np.abs(final - initial) >= 0.05
    if not np.any(usable) or search_stop_s <= search_start_s:
        width_ns = fallback_ns
        reverse_s = transition_start_s + width_ns * 1e-9
        source = "fixture_settle_fallback"
    else:
        dense_t = np.linspace(search_start_s, search_stop_s, 20001)
        traces = np.column_stack([
            np.interp(dense_t, h["time"], h["ku"]),
            np.interp(dense_t, h["time"], h["kd"]),
        ])
        normalized = (traces[:, usable] - initial[usable]) / (final[usable] - initial[usable])
        progress = np.mean(np.clip(normalized, 0.0, 1.0), axis=1)
        progress_envelope = np.maximum.accumulate(progress)
        hit = np.flatnonzero(progress_envelope >= 0.5)
        index = int(hit[0]) if len(hit) else int(np.argmin(np.abs(progress_envelope - 0.5)))
        reverse_s = float(dense_t[index])
        width_ns = max(0.1, (reverse_s - transition_start_s) * 1e9)
        source = "cached_hspice_composite_k_50pct"

    ku_reverse = interp_at(h, "ku", reverse_s)
    kd_reverse = interp_at(h, "kd", reverse_s)
    components = []
    for value, start, end, valid in zip((ku_reverse, kd_reverse), initial, final, usable):
        if valid:
            components.append(float(np.clip((value - start) / (end - start), 0.0, 1.0)))
    composite = float(np.mean(components)) if components else math.nan
    return {
        "direction": direction,
        "selection_source": source,
        "pulse_width_ns": width_ns,
        "reverse_time_ns": reverse_s * 1e9,
        "hspice_ku_at_reverse": ku_reverse,
        "hspice_kd_at_reverse": kd_reverse,
        "hspice_composite_progress": composite,
        "hspice_ku_initial": float(initial[0]),
        "hspice_kd_initial": float(initial[1]),
        "hspice_ku_settled": float(final[0]),
        "hspice_kd_settled": float(final[1]),
    }


def bench_times(candidate: Candidate, direction: str, width_ns: float) -> dict[str, float]:
    rise = candidate.rise_edge_ns
    edge = candidate.input_edge_ns
    if direction == "short_high":
        transition_edge = rise
        reverse = rise + width_ns
        stop = reverse + edge + max(10.0, 1.25 * candidate.fall_settle_ns + 1.0)
    else:
        # Start high at the DC operating point. Replaying a many-nanosecond
        # rising table only to precondition the falling test adds no evidence
        # and can dominate ngspice runtime for slow vendor models.
        transition_edge = rise
        reverse = transition_edge + width_ns
        stop = reverse + edge + max(10.0, 1.25 * candidate.rise_settle_ns + 1.0)
    return {
        "rise_ns": rise,
        "fall_ns": candidate.fall_edge_ns,
        "transition_edge_ns": transition_edge,
        "reverse_ns": reverse,
        "stop_ns": stop,
        "save_start_ns": max(0.0, transition_edge - 1.0),
    }


def stimulus_pwl(candidate: Candidate, direction: str, times: dict[str, float]) -> str:
    vcc = candidate.vcc
    rise = times["rise_ns"]
    edge = candidate.input_edge_ns
    reverse = times["reverse_ns"]
    if direction == "short_high":
        points = [(0, 0), (rise, 0), (rise + edge, vcc), (reverse, vcc), (reverse + edge, 0)]
    else:
        fall = times["transition_edge_ns"]
        points = [
            (0, vcc),
            (fall, vcc),
            (fall + edge, 0),
            (reverse, 0),
            (reverse + edge, vcc),
        ]
    return " ".join(f"{time_ns:.12g}n {value:.12g}" for time_ns, value in points)


def hspice_nodes(candidate: Candidate) -> tuple[str, str, str]:
    model_type = candidate.model_type.lower()
    enable_v = 0.0 if "active-low" in candidate.enable.lower() else candidate.vcc
    if model_type == "output":
        return "pu_ref pd_ref pad_h in_dig pc_ref gc_ref", "", ""
    if model_type == "3-state":
        return "pu_ref pd_ref pad_h in_dig en_sig pc_ref gc_ref", f"Ven en_sig 0 DC {enable_v:.12g}", ""
    if model_type == "i/o":
        return (
            "pu_ref pd_ref pad_h in_dig en_sig dig_q pc_ref gc_ref",
            f"Ven en_sig 0 DC {enable_v:.12g}",
            "Rdig dig_q 0 1k",
        )
    raise ValueError(f"unsupported HSPICE stress model type: {candidate.model_type}")


def make_hspice_deck(candidate: Candidate, direction: str, times: dict[str, float]) -> str:
    nodes, enable_source, digital_load = hspice_nodes(candidate)
    return f"""* Model-adaptive interrupted-transition stress reference
.title {candidate.file_name} / {candidate.model} / {direction}
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL({stimulus_pwl(candidate, direction, times)})
{enable_source}
VPU pu_ref 0 DC {candidate.pullup_ref:.12g}
VPD pd_ref 0 DC {candidate.pulldown_ref:.12g}
VPC pc_ref 0 DC {candidate.power_clamp_ref:.12g}
VGC gc_ref 0 DC {candidate.gnd_clamp_ref:.12g}

BIBIS {nodes}
+ file='{candidate.declared_file_name}'
+ model='{candidate.model}'
+ typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
+ xv_pu=ku xv_pd=kd

{digital_load}
Rload pad_h 0 50
Cload pad_h 0 2p
.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran 0.001n {times['stop_ns']:.12g}n {times['save_start_ns']:.12g}n
.end
"""


def make_ngspice_deck(candidate: Candidate, direction: str, times: dict[str, float], subckt: str) -> str:
    enable_v = 0.0 if "active-low" in candidate.enable.lower() else candidate.vcc
    return f"""* Model-adaptive interrupted-transition legacy-pybis stress case
.title {candidate.file_name} / {candidate.model} / {direction}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL({stimulus_pwl(candidate, direction, times)})
Ven en_sig 0 DC {enable_v:.12g}
Vdd vdd 0 DC {candidate.vcc:.12g}
.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 {subckt}
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n {times['stop_ns']:.12g}n {times['save_start_ns']:.12g}n
.end
"""


def initialize_legacy_high(subckt_text: str, until_ns: float) -> str:
    """Force the copied legacy model's DC state high before a short-low test."""

    replacements = {
        "B28": "1",
        "B29": "0",
    }
    output: list[str] = []
    replaced: set[str] = set()
    for line in subckt_text.splitlines():
        match = re.match(r"^(B2[89]\s+\S+\s+\S+\s+V\s*=\s*)(.+)$", line, flags=re.IGNORECASE)
        if match:
            element = line.split(None, 1)[0].upper()
            if element in replacements:
                original = match.group(2)
                forced = replacements[element]
                line = f"{match.group(1)}(time < {until_ns:.12g}n) ? {forced} : ({original})"
                replaced.add(element)
        output.append(line)
    if replaced != set(replacements):
        missing = ", ".join(sorted(set(replacements) - replaced))
        raise ValueError(f"legacy high-state initialization could not patch {missing}")
    return "\n".join(output) + "\n"


def raw_reaches(path: Path, stop_ns: float) -> bool:
    if not path.exists():
        return False
    try:
        data = parse_ngspice_raw(path)
        return len(data["time"]) > 2 and float(data["time"][-1]) >= 0.999 * stop_ns * 1e-9
    except Exception:
        return False


def compare_stress(candidate: Candidate, h: dict[str, np.ndarray], n: dict[str, np.ndarray], times: dict[str, float]) -> dict[str, object]:
    start_s = times["save_start_ns"] * 1e-9
    stop_s = times["stop_ns"] * 1e-9
    eval_t = np.linspace(start_s, stop_s, 30001)
    h_eval = {key: np.interp(eval_t, h["time"], value) for key, value in h.items() if key != "time"}
    n_eval = {key: np.interp(eval_t, n["time"], value) for key, value in n.items() if key != "time"}
    errors = {key: float(np.sqrt(np.mean(np.square(h_eval[key] - n_eval[key])))) for key in ("pad", "ku", "kd")}
    pad_fraction = errors["pad"] / max(candidate.vcc, 1e-6)
    if pad_fraction <= 0.02 and errors["ku"] <= 0.05 and errors["kd"] <= 0.05:
        stress_class = "GOOD"
    elif pad_fraction <= 0.05 and errors["ku"] <= 0.10 and errors["kd"] <= 0.10:
        stress_class = "WARN"
    else:
        stress_class = "CHECK"
    reverse_s = times["reverse_ns"] * 1e-9
    return {
        "stress_class": stress_class,
        "pad_rmse_mv": errors["pad"] * 1e3,
        "pad_rmse_pct_vcc": pad_fraction * 100.0,
        "ku_rmse": errors["ku"],
        "kd_rmse": errors["kd"],
        "hspice_pad_min_v": float(np.min(h_eval["pad"])),
        "hspice_pad_max_v": float(np.max(h_eval["pad"])),
        "ngspice_pad_min_v": float(np.min(n_eval["pad"])),
        "ngspice_pad_max_v": float(np.max(n_eval["pad"])),
        "hspice_ku_at_reverse_run": interp_at(h, "ku", reverse_s),
        "hspice_kd_at_reverse_run": interp_at(h, "kd", reverse_s),
        "ngspice_ku_at_reverse_run": interp_at(n, "ku", reverse_s),
        "ngspice_kd_at_reverse_run": interp_at(n, "kd", reverse_s),
    }


def plot_case(candidate: Candidate, direction: str, h: dict[str, np.ndarray], n: dict[str, np.ndarray], times: dict[str, float], output: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True, constrained_layout=True)
    ht, nt = h["time"] * 1e9, n["time"] * 1e9
    labels = (("pad", "pad (V)"), ("ku", "Ku"), ("kd", "Kd"))
    ng_colors = ("#0072B2", "#D55E00", "#009E73")
    for ax, (key, ylabel), ng_color in zip(axes, labels, ng_colors):
        ax.plot(ht, h[key], color="black", lw=2.7, label="HSPICE native IBIS")
        ax.plot(nt, n[key], color=ng_color, lw=1.8, label="ngspice legacy pybis")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
        ax.axvline(times["transition_edge_ns"], color="#777777", ls="--", lw=1.0)
        ax.axvline(times["reverse_ns"], color="#7B3294", ls="--", lw=1.2)
    input_ax = axes[0].twinx()
    input_ax.plot(ht, h["input"], color="#999999", lw=1.0, alpha=0.6)
    input_ax.set_ylabel("input (V)", color="#777777")
    axes[0].legend(loc="best")
    axes[2].axhline(0, color="#999999", lw=0.8)
    axes[2].set_xlabel("time (ns)")
    axes[2].legend(loc="best")
    axes[0].set_xlim(times["save_start_ns"], times["stop_ns"])
    fig.suptitle(f"{candidate.file_name} | {candidate.model} | {direction} | {times['reverse_ns'] - times['transition_edge_ns']:.3f} ns pulse")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170)
    plt.close(fig)


def run_case(
    candidate: Candidate,
    direction: str,
    selection: dict[str, float | str],
    study: Path,
    full_study: Path,
    hspice: Path,
    ngspice: Path,
    timeout_s: float,
    resume: bool,
) -> dict[str, object]:
    times = bench_times(candidate, direction, float(selection["pulse_width_ns"]))
    case_dir = study / "cases" / candidate.case_id / direction
    h_dir = case_dir / "hspice_native_ibis"
    n_dir = case_dir / "ngspice_legacy_pybis"
    h_dir.mkdir(parents=True, exist_ok=True)
    n_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate.source_path, h_dir / candidate.declared_file_name)
    h_deck = h_dir / "run.sp"
    h_deck_text = make_hspice_deck(candidate, direction, times)
    h_deck_changed = not h_deck.exists() or h_deck.read_text(encoding="ascii", errors="replace") != h_deck_text
    h_deck.write_text(h_deck_text, encoding="ascii")
    h_tr0 = h_dir / "run.tr0"
    row: dict[str, object] = {
        "file": candidate.file_name,
        "model": candidate.model,
        "model_type": candidate.model_type,
        "vcc_v": candidate.vcc,
        "case_id": candidate.case_id,
        **selection,
        **times,
        "status": "PENDING",
        "hspice_tr0": str(h_tr0.relative_to(ROOT)),
        "ngspice_raw": "",
        "plot": "",
    }
    if not (resume and not h_deck_changed and h_tr0.exists()):
        for stale in (h_tr0, h_dir / "run.lis"):
            if stale.exists():
                stale.unlink()
        rc, runtime, _ = run_process(
            [str(hspice), "-i", h_deck.name, "-o", "run"],
            h_dir,
            h_dir / "stdout.log",
            timeout_s,
            completion_file=h_dir / "run.lis",
            completion_text="job concluded",
        )
        row["hspice_runtime_s"] = runtime
        if rc is None or rc != 0 or not h_tr0.exists():
            row.update(status="HSPICE_FAIL", error="native IBIS stress run failed")
            return row
    else:
        row["hspice_runtime_s"] = 0.0

    full_sub = full_study / "cases" / candidate.case_id / "ngspice_legacy_pybis" / "legacy.sub"
    if not full_sub.exists():
        row.update(status="PYBIS_UNAVAILABLE", error="full-transition legacy pybis conversion is unavailable")
        return row
    subckt_text = full_sub.read_text(encoding="utf-8", errors="replace")
    if direction == "short_low":
        try:
            # Keep the DC override through the input slew and the generated
            # model's 10 ps edge detector. Releasing at the edge itself leaves
            # a brief branch-selection gap and creates an artificial Kd spike.
            release_ns = times["transition_edge_ns"] + candidate.input_edge_ns + 0.02
            subckt_text = initialize_legacy_high(subckt_text, release_ns)
        except ValueError as exc:
            row.update(status="PYBIS_UNAVAILABLE", error=str(exc))
            return row
    local_sub = n_dir / "legacy.sub"
    local_sub_text = subckt_text.encode("ascii", errors="replace").decode("ascii")
    subckt_changed = not local_sub.exists() or local_sub.read_text(encoding="ascii", errors="replace") != local_sub_text
    local_sub.write_text(local_sub_text, encoding="ascii")
    shutil.copy2(candidate.source_path, n_dir / candidate.declared_file_name)
    (n_dir / ".spiceinit").write_text("set filetype=binary\n", encoding="ascii")
    match = re.search(r"(?im)^\s*\.subckt\s+(\S+)", subckt_text)
    if not match:
        row.update(status="PYBIS_UNAVAILABLE", error="legacy subcircuit declaration not found")
        return row
    n_deck = n_dir / "run.sp"
    n_deck_text = make_ngspice_deck(candidate, direction, times, match.group(1))
    n_deck_changed = not n_deck.exists() or n_deck.read_text(encoding="ascii", errors="replace") != n_deck_text
    n_deck.write_text(n_deck_text, encoding="ascii")
    n_raw = n_dir / "run.raw"
    row["ngspice_raw"] = str(n_raw.relative_to(ROOT))
    if not (resume and not subckt_changed and not n_deck_changed and raw_reaches(n_raw, times["stop_ns"])):
        if n_raw.exists():
            n_raw.unlink()
        rc, runtime, _ = run_process(
            [str(ngspice), "-b", "-r", n_raw.name, n_deck.name],
            n_dir,
            n_dir / "stdout.log",
            timeout_s,
        )
        row["ngspice_runtime_s"] = runtime
        if rc is None:
            row.update(status="NGSPICE_TIMEOUT", error="legacy pybis stress run timed out")
            return row
        if rc != 0 or not raw_reaches(n_raw, times["stop_ns"]):
            row.update(status="NGSPICE_FAIL", error=f"legacy pybis stress return code {rc}")
            return row
    else:
        row["ngspice_runtime_s"] = 0.0

    try:
        h = extract_hspice(parse_hspice_tr0(h_tr0))
        n = extract_ngspice(parse_ngspice_raw(n_raw))
        row.update(compare_stress(candidate, h, n, times))
        plot_path = study / "plots" / candidate.case_id / f"{direction}.png"
        plot_case(candidate, direction, h, n, times, plot_path)
        row["plot"] = str(plot_path.relative_to(ROOT))
        row.update(status="COMPLETED", error="")
    except Exception as exc:
        row.update(status="ANALYSIS_FAIL", error=f"{type(exc).__name__}: {exc}")
    return row


def plot_summary(study: Path, rows: list[dict[str, object]]) -> None:
    completed = [row for row in rows if row.get("status") == "COMPLETED"]
    colors = {"GOOD": "#009E73", "WARN": "#E69F00", "CHECK": "#D55E00"}
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)
    for ax, direction in zip(axes, DIRECTIONS):
        direction_rows = [row for row in completed if row.get("direction") == direction]
        labels = ["GOOD", "WARN", "CHECK"]
        counts = [sum(row.get("stress_class") == label for row in direction_rows) for label in labels]
        bars = ax.bar(labels, counts, color=[colors[label] for label in labels])
        ax.bar_label(bars, padding=3)
        ax.set_title(direction.replace("_", " "))
        ax.set_ylabel("model count")
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Interrupted-transition stress outcomes")
    output = study / "plots" / "summary_outcomes.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 8), constrained_layout=True)
    markers = {"short_high": "o", "short_low": "s"}
    for direction in DIRECTIONS:
        direction_rows = [row for row in completed if row.get("direction") == direction]
        ax.scatter(
            [float(row["pulse_width_ns"]) for row in direction_rows],
            [max(float(row["ku_rmse"]), float(row["kd_rmse"]), 1e-4) for row in direction_rows],
            marker=markers[direction],
            s=55,
            alpha=0.75,
            label=direction.replace("_", " "),
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("selected mid-transition pulse width (ns)")
    ax.set_ylabel("max(Ku RMSE, Kd RMSE)")
    ax.set_title("Legacy pybis coefficient error under adaptive reversal")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend()
    fig.savefig(study / "plots" / "summary_error_vs_pulse_width.png", dpi=180)
    plt.close(fig)


def write_report(study: Path, selected: list[Candidate], rows: list[dict[str, object]]) -> None:
    completed = [row for row in rows if row.get("status") == "COMPLETED"]

    def values(direction: str, key: str) -> list[float]:
        result: list[float] = []
        for row in completed:
            if row.get("direction") != direction:
                continue
            try:
                result.append(float(row[key]))
            except (KeyError, TypeError, ValueError):
                pass
        return result

    def percentile(data: list[float], fraction: float) -> float:
        return float(np.percentile(np.asarray(data, dtype=float), 100.0 * fraction))

    total_good = sum(row.get("stress_class") == "GOOD" for row in completed)
    total_warn = sum(row.get("stress_class") == "WARN" for row in completed)
    total_check = sum(row.get("stress_class") == "CHECK" for row in completed)
    reverse_ku_delta = max(
        abs(float(row["hspice_ku_at_reverse_run"]) - float(row["hspice_ku_at_reverse"]))
        for row in completed
    )
    reverse_kd_delta = max(
        abs(float(row["hspice_kd_at_reverse_run"]) - float(row["hspice_kd_at_reverse"]))
        for row in completed
    )
    lines = [
        "# External IBIS Adaptive Stress Campaign",
        "",
        "This study reverses each input while its preceding native-IBIS Ku/Kd transition is near 50% composite progress.",
        "",
        "## Bench",
        "",
        "- Typical corner, model-derived supply/reference voltages, and `50 ohm || 2 pF` load.",
        "- Input rise/fall time remains 50 ps; only pulse timing changes by model and direction.",
        "- `short_high`: falling edge arrives during the preceding rising output transition.",
        "- `short_low`: the input starts high at the DC operating point; a rising edge then arrives during the preceding falling output transition.",
        "- The copied pybis short-low model is held at settled `Ku=1, Kd=0` only through the first falling-edge detector interval; the override is released before the measured reverse edge.",
        "- Stress width is selected from the cached full-transition HSPICE Ku/Kd trajectory; HSPICE is used only to design and validate the stress bench, not to alter pybis.",
        "",
        "## Stress Selection",
        "",
        "Each coefficient is normalized from its initial value to its settled value. The selection signal is",
        "`progress = 0.5 * (normalized_Ku + normalized_Kd)`; the input reverses at the first monotonic-envelope crossing of `progress=0.5`.",
        "This does not require both coefficients to equal 0.5. A break-before-make interval can have one path already off while the other has not yet turned on.",
        f"The stress reruns reproduce the cached coefficient state at reversal within `{reverse_ku_delta:.4f}` Ku and `{reverse_kd_delta:.4f}` Kd in the worst case.",
        "",
        "## Classification",
        "",
        "- `GOOD`: pad RMSE <= 2% of VCC and both coefficient RMSE values <= 0.05.",
        "- `WARN`: pad RMSE <= 5% of VCC and both coefficient RMSE values <= 0.10.",
        "- `CHECK`: any completed comparison outside those limits. It is evidence of disagreement, not a simulator execution failure.",
        "",
        "## Results",
        "",
        f"- Unique applicable models: `{len(selected)}`; requested direction cases: `{2 * len(selected)}`.",
        f"- Completed HSPICE/ngspice comparisons: `{len(completed)}`.",
        f"- Overall: GOOD `{total_good}` ({100.0 * total_good / max(len(completed), 1):.1f}%), WARN `{total_warn}` ({100.0 * total_warn / max(len(completed), 1):.1f}%), CHECK `{total_check}` ({100.0 * total_check / max(len(completed), 1):.1f}%).",
    ]
    for direction in DIRECTIONS:
        direction_rows = [row for row in rows if row.get("direction") == direction]
        lines.append(f"- `{direction}`: " + ", ".join(
            f"{label} `{sum(row.get('status') == 'COMPLETED' and row.get('stress_class') == label for row in direction_rows)}`"
            for label in ("GOOD", "WARN", "CHECK")
        ))
        widths = values(direction, "pulse_width_ns")
        pad = values(direction, "pad_rmse_mv")
        ku = values(direction, "ku_rmse")
        kd = values(direction, "kd_rmse")
        lines.append(
            f"  Selected width range `{min(widths):.3f}..{max(widths):.3f} ns` (median `{percentile(widths, 0.5):.3f} ns`); "
            f"median pad/Ku/Kd RMSE `{percentile(pad, 0.5):.1f} mV / {percentile(ku, 0.5):.3f} / {percentile(kd, 0.5):.3f}`."
        )
    lines.extend([
        "",
        "## Headline Findings",
        "",
        f"- Legacy table replay is generally not reliable for a measured mid-transition reversal: `{total_check}/{len(completed)}` completed cases require CHECK.",
        "- Failure is not universal. The inverter-derived `inv_t2b`, `invchain_test_0615_v5`, and `t2b_0616` models are GOOD in both directions at about 0.30-0.33 ns.",
        "- `io_buf` and its related variants are CHECK in both directions; their post-reversal coefficient histories visibly diverge even though the state at the reverse edge initially agrees.",
        "- Pulse width alone is not a quality predictor. Similar-width models can be GOOD or CHECK because the opposite-table restart shape and Ku/Kd staging differ by model.",
        "- The narrow coefficient jump at the reverse edge in CHECK plots is the legacy restart behavior under test, not the short-low DC initialization.",
    ])
    failures = [row for row in rows if row.get("status") != "COMPLETED"]
    lines.extend(["", "## Incomplete Cases", ""])
    if failures:
        for row in failures:
            lines.append(f"- `{row.get('file')} / {row.get('model')} / {row.get('direction')}`: `{row.get('status')}` - {row.get('error', '')}")
    else:
        lines.append("None.")
    lines.extend([
        "",
        "## Case Table",
        "",
        "| File | Model | Direction | Width ns | Progress | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |",
        "|---|---|---|---:|---:|---|---|---:|---:|---:|",
    ])
    for row in rows:
        def fmt(key: str, digits: int) -> str:
            try:
                return f"{float(row[key]):.{digits}f}"
            except (KeyError, TypeError, ValueError):
                return "n/a"
        lines.append(
            f"| {row.get('file')} | {row.get('model')} | {row.get('direction')} | {fmt('pulse_width_ns', 3)} | "
            f"{fmt('hspice_composite_progress', 3)} | {row.get('status')} | {row.get('stress_class', '')} | "
            f"{fmt('pad_rmse_mv', 3)} | {fmt('ku_rmse', 4)} | {fmt('kd_rmse', 4)} |"
        )
    lines.extend([
        "",
        "## Files",
        "",
        "- `stress_selection.csv`: selected per-model pulse widths and HSPICE state at reversal.",
        "- `metrics.csv`: simulator status and pad/Ku/Kd comparison metrics.",
        "- `cases/<model>/<direction>/`: exact decks, copied IBIS/model, raw output, and logs.",
        "- `plots/<model>/<direction>.png`: pad, Ku, and Kd overlays.",
        "- `plots/summary_outcomes.png` and `summary_error_vs_pulse_width.png`: campaign summaries.",
    ])
    (study / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--full-study", type=Path, default=DEFAULT_FULL_STUDY)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--select-regex")
    parser.add_argument("--max-models", type=int)
    parser.add_argument("--timeout-s", type=float, default=300.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    args = parser.parse_args()

    study = args.study_dir.resolve()
    full_study = args.full_study.resolve()
    study.mkdir(parents=True, exist_ok=True)
    candidates, _ = inventory(args.source_dir.resolve())
    selected = unique_ready(candidates)
    if args.select_regex:
        pattern = re.compile(args.select_regex, re.IGNORECASE)
        selected = [candidate for candidate in selected if pattern.search(f"{candidate.file_name}/{candidate.model}")]
    if args.max_models is not None:
        selected = selected[: args.max_models]

    if args.report_only:
        rows = read_csv(study / "metrics.csv")
        plot_summary(study, rows)
        write_report(study, selected, rows)
        print(f"Regenerated {study}")
        return 0

    selections: list[dict[str, object]] = []
    selection_by_case: dict[tuple[str, str], dict[str, object]] = {}
    for candidate in selected:
        full_hspice = full_study / "cases" / candidate.case_id / "hspice_native_ibis" / "run.tr0"
        if not full_hspice.exists():
            continue
        h = extract_hspice(parse_hspice_tr0(full_hspice))
        for direction in DIRECTIONS:
            selection = {
                "file": candidate.file_name,
                "model": candidate.model,
                "case_id": candidate.case_id,
                **select_reverse_width(candidate, h, direction),
            }
            selections.append(selection)
            selection_by_case[(candidate.case_id, direction)] = selection
    write_csv(study / "stress_selection.csv", selections)

    rows: list[dict[str, object]] = []
    total = len(selected) * len(DIRECTIONS)
    index = 0
    for candidate in selected:
        for direction in DIRECTIONS:
            index += 1
            print(f"[{index}/{total}] {candidate.file_name} / {candidate.model} / {direction}", flush=True)
            selection = selection_by_case.get((candidate.case_id, direction))
            if selection is None:
                row = {
                    "file": candidate.file_name,
                    "model": candidate.model,
                    "direction": direction,
                    "status": "SELECTION_UNAVAILABLE",
                    "error": "cached full-transition HSPICE reference is unavailable",
                }
            else:
                row = run_case(candidate, direction, selection, study, full_study, args.hspice, args.ngspice, args.timeout_s, args.resume)
            rows.append(row)
            write_csv(study / "metrics.csv", rows)
            print(f"  {row['status']} {row.get('stress_class', '')} {row.get('error', '')}", flush=True)
    plot_summary(study, rows)
    write_report(study, selected, rows)
    print(f"Wrote {study}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
