from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from spice_tool_paths import default_ngspice  # noqa: E402
from run_io_buf_coeff_state_retrigger import (  # noqa: E402
    SweepCase,
    active_mask,
    build_cases,
    build_pwl_points,
    c_load_line,
    ensure_dir,
    find_signal,
    fmt_num,
    interp_to,
    make_hspice_deck,
    maxabs,
    percent_reduction,
    pwl_text,
    read_csv,
    rmse,
    run_process,
    spice_time_ns,
    status_for,
    to_ns,
    write_csv,
    write_text,
)


OUT_DIR = ROOT / "results" / "io_buf_shortpulse_hybrid_retrigger_2026-06-21"
COMMON_DIR = OUT_DIR / "common"
CASES_DIR = OUT_DIR / "cases"
DEMO_DIR = OUT_DIR / "interrupted_switching_demo"
FIGURES_DIR = DEMO_DIR / "figures"
DEFAULT_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
DEFAULT_NGSPICE = default_ngspice(console=True)

REQUIRED_CASE_IDS = [
    "edge_1ps_base_50r_2pf",
    "short_pulse_500ps_high",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
]
CONTROL_CASE = "edge_1ps_base_50r_2pf"
DEMO_CASE = "short_pulse_1ns_high"

COLORS = {
    "hspice": "#1f77b4",
    "legacy": "#ff7f0e",
    "coeff_state": "#2ca02c",
    "hybrid": "#9467bd",
    "input": "#222222",
    "target": "#7f7f7f",
}


@dataclass(frozen=True)
class Variant:
    variant_id: str
    label: str
    subcircuit_type: str
    save_diagnostics: bool = False
    is_hybrid: bool = False


VARIANTS = [
    Variant("legacy", "legacy pybis", "InputDriven"),
    Variant("coeff_state", "CoeffState pybis", "InputDrivenCoeffState", save_diagnostics=True),
    Variant(
        "hybrid_branch",
        "ShortPulseHybrid branch",
        "InputDrivenShortPulseHybrid",
        save_diagnostics=True,
        is_hybrid=True,
    ),
    Variant(
        "hybrid_main_slope",
        "ShortPulseHybrid main-slope",
        "InputDrivenShortPulseHybridMainSlope",
        save_diagnostics=True,
        is_hybrid=True,
    ),
    Variant(
        "hybrid_constrained",
        "ShortPulseHybrid constrained",
        "InputDrivenShortPulseHybridConstrained",
        save_diagnostics=True,
        is_hybrid=True,
    ),
]


def case_by_id(case_id: str) -> SweepCase:
    cases = {case.case_id: case for case in build_cases()}
    return cases[case_id]


def selected_cases(case_ids: list[str], all_cases: bool) -> list[SweepCase]:
    available = {case.case_id: case for case in build_cases()}
    if all_cases:
        return [available[case_id] for case_id in available]
    ids = case_ids or REQUIRED_CASE_IDS
    missing = [case_id for case_id in ids if case_id not in available]
    if missing:
        raise SystemExit(f"Unknown case(s): {', '.join(missing)}")
    return [available[case_id] for case_id in ids]


def make_ngspice_deck(case: SweepCase, variant: Variant) -> str:
    extra = ""
    if variant.save_diagnostics:
        extra = (
            " V(xdrv.kutarget) V(xdrv.kdtarget)"
            " V(xdrv.kuleg) V(xdrv.kdleg)"
            " V(xdrv.kucor) V(xdrv.kdcor)"
            " V(xdrv.hshort) V(xdrv.highage)"
        )
    return f"""* io_buf {variant.label}/ngspice switching coefficient extraction
* Sweep case: {case.case_id}
* {case.description}
.title io_buf ngspice {variant.label} Ku/Kd extraction {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{pwl_text(case)}

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 {fmt_num(case.r_load_ohm)}
{c_load_line("pad", case.c_load_pf).rstrip()}

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){extra}
.tran 0.001n {spice_time_ns(case.stop_ns)}
.end
"""


def prepare_common(ibis_path: Path) -> dict[str, Path]:
    ensure_dir(COMMON_DIR)
    common_ibis = COMMON_DIR / "io_buf.ibs"
    shutil.copy2(ibis_path, common_ibis)
    paths: dict[str, Path] = {}
    for variant in VARIANTS:
        output_path = COMMON_DIR / variant.variant_id / "driver_OutputInput_Typical.sub"
        convert_ibis_to_pybis(
            ibis_path=common_ibis,
            output_path=output_path,
            component_name="MCM Driver 1",
            model_name="driver",
            io_type="Output",
            subcircuit_type=variant.subcircuit_type,
            corner="Typical",
        )
        paths[variant.variant_id] = output_path
    return paths


def run_hspice_case(case: SweepCase, ibis_path: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], Path, int]:
    h_dir = CASES_DIR / case.case_id / "hspice_native_ibis"
    ensure_dir(h_dir)
    shutil.copy2(ibis_path, h_dir / "io_buf.ibs")
    stem = f"{case.case_id}_hspice_native_ibis"
    deck = h_dir / f"{stem}.sp"
    write_text(deck, make_hspice_deck(case))
    rc = run_process(["hspice", "-i", deck.name, "-o", stem], h_dir, h_dir / "hspice_stdout.log", timeout_s=timeout_s)
    if rc != 0:
        raise RuntimeError(f"HSPICE return code {rc}")
    return parse_hspice_tr0(h_dir / f"{stem}.tr0"), deck, rc


def run_ngspice_variant(
    case: SweepCase,
    variant: Variant,
    model_path: Path,
    ngspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], Path, Path, int]:
    n_dir = CASES_DIR / case.case_id / f"ngspice_{variant.variant_id}"
    ensure_dir(n_dir)
    shutil.copy2(model_path, n_dir / "driver_OutputInput_Typical.sub")
    stem = f"{case.case_id}_ngspice_{variant.variant_id}"
    deck = n_dir / f"{stem}.sp"
    raw = n_dir / f"{stem}.raw"
    write_text(deck, make_ngspice_deck(case, variant))
    rc = run_process([str(ngspice), "-b", "-r", raw.name, deck.name], n_dir, n_dir / "ngspice_stdout.log", timeout_s=timeout_s)
    if rc != 0:
        raise RuntimeError(f"ngspice {variant.variant_id} return code {rc}")
    return parse_ngspice_raw(raw), deck, raw, rc


def command_times(case: SweepCase) -> tuple[float, float]:
    edge = case.edge_ns
    if case.pattern == "short_pulse":
        return 5.0 + 0.5 * edge, 5.0 + case.high_time_ns + 0.5 * edge
    return 5.0 + 0.5 * edge, 15.0 + 0.5 * edge


def coefficient_jump(t_ns: np.ndarray, values: np.ndarray, center_ns: float) -> float:
    mask = (t_ns >= center_ns - 0.02) & (t_ns <= center_ns + 0.02)
    if np.count_nonzero(mask) < 2:
        return 0.0
    return float(np.max(np.abs(np.diff(values[mask]))))


def score_variant(
    case: SweepCase,
    variant: Variant,
    h_data: dict[str, np.ndarray],
    n_data: dict[str, np.ndarray],
    hspice_deck: Path,
    ngspice_deck: Path,
    raw_path: Path,
) -> dict[str, object]:
    h_t = to_ns(find_signal(h_data, "time"))
    n_t = to_ns(find_signal(n_data, "time"))
    mask = active_mask(h_t, case)
    _, fall_ns = command_times(case)

    h_pad = find_signal(h_data, "v(pad_ibis)")
    h_ku = find_signal(h_data, "v(ku)")
    h_kd = find_signal(h_data, "v(kd)")
    n_pad = interp_to(n_t, find_signal(n_data, "v(pad)"), h_t)
    n_ku = interp_to(n_t, find_signal(n_data, "v(xdrv.ku)", "v(xdrv:ku)"), h_t)
    n_kd = interp_to(n_t, find_signal(n_data, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)

    pad_rmse = rmse(h_pad[mask], n_pad[mask])
    ku_rmse = rmse(h_ku[mask], n_ku[mask])
    kd_rmse = rmse(h_kd[mask], n_kd[mask])
    row: dict[str, object] = {
        "case_id": case.case_id,
        "description": case.description,
        "pattern": case.pattern,
        "pulse_high_ns": case.high_time_ns if case.pattern == "short_pulse" else "",
        "variant": variant.variant_id,
        "variant_label": variant.label,
        "is_hybrid": variant.is_hybrid,
        "edge_ns": case.edge_ns,
        "r_load_ohm": case.r_load_ohm,
        "c_load_pf": case.c_load_pf,
        "hspice_deck": str(hspice_deck.relative_to(ROOT)),
        "ngspice_deck": str(ngspice_deck.relative_to(ROOT)),
        "ngspice_raw": str(raw_path.relative_to(ROOT)),
        "pad_active_rmse_v": pad_rmse,
        "pad_active_max_v": maxabs(h_pad[mask], n_pad[mask]),
        "ku_active_rmse": ku_rmse,
        "ku_active_max": maxabs(h_ku[mask], n_ku[mask]),
        "kd_active_rmse": kd_rmse,
        "kd_active_max": maxabs(h_kd[mask], n_kd[mask]),
        "ku_peak": float(np.max(n_ku[mask])),
        "kd_min": float(np.min(n_kd[mask])),
        "ku_min": float(np.min(n_ku[mask])),
        "kd_max": float(np.max(n_kd[mask])),
        "coeff_range_ok": bool(
            np.min(n_ku[mask]) >= -0.2
            and np.max(n_ku[mask]) <= 1.2
            and np.min(n_kd[mask]) >= -0.2
            and np.max(n_kd[mask]) <= 1.2
        ),
        "ku_jump_at_retrigger": coefficient_jump(h_t, n_ku, fall_ns),
        "kd_jump_at_retrigger": coefficient_jump(h_t, n_kd, fall_ns),
        "status": status_for(pad_rmse, ku_rmse, kd_rmse),
    }
    if variant.save_diagnostics:
        for name in ["kutarget", "kdtarget", "kuleg", "kdleg", "kucor", "kdcor", "hshort", "highage"]:
            try:
                sig = interp_to(n_t, find_signal(n_data, f"v(xdrv.{name})", f"v(xdrv:{name})"), h_t)
                row[f"{name}_min"] = float(np.min(sig[mask]))
                row[f"{name}_max"] = float(np.max(sig[mask]))
            except KeyError:
                row[f"{name}_min"] = ""
                row[f"{name}_max"] = ""
    return row


def run_case(case: SweepCase, ngspice: Path, ibis_path: Path, model_paths: dict[str, Path], timeout_s: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    h_data, h_deck, _ = run_hspice_case(case, ibis_path, timeout_s)
    for variant in VARIANTS:
        n_data, n_deck, raw, _ = run_ngspice_variant(case, variant, model_paths[variant.variant_id], ngspice, timeout_s)
        rows.append(score_variant(case, variant, h_data, n_data, h_deck, n_deck, raw))
    return rows


def choose_best_hybrid(rows: list[dict[str, object]]) -> tuple[str, list[dict[str, object]]]:
    hybrid_ids = [variant.variant_id for variant in VARIANTS if variant.is_hybrid]
    legacy_by_case = {(r["case_id"], r["variant"]): r for r in rows}
    summary: list[dict[str, object]] = []
    best_variant = hybrid_ids[0]
    best_score = float("inf")
    for variant_id in hybrid_ids:
        short_rows = [
            r for r in rows if r.get("variant") == variant_id and str(r.get("case_id", "")).startswith("short_pulse")
        ]
        control = next((r for r in rows if r.get("variant") == variant_id and r.get("case_id") == CONTROL_CASE), None)
        legacy_control = legacy_by_case.get((CONTROL_CASE, "legacy"))
        if not short_rows or control is None or legacy_control is None:
            continue
        pad_mv = np.array([float(r["pad_active_rmse_v"]) * 1e3 for r in short_rows], dtype=float)
        ku = np.array([float(r["ku_active_rmse"]) for r in short_rows], dtype=float)
        kd = np.array([float(r["kd_active_rmse"]) for r in short_rows], dtype=float)
        control_pad_delta_mv = (float(control["pad_active_rmse_v"]) - float(legacy_control["pad_active_rmse_v"])) * 1e3
        control_coeff_delta = max(float(control["ku_active_rmse"]), float(control["kd_active_rmse"])) - max(
            float(legacy_control["ku_active_rmse"]),
            float(legacy_control["kd_active_rmse"]),
        )
        control_pass = control_pad_delta_mv <= 5.0 and control_coeff_delta <= 0.02
        score = float(np.nanmean(pad_mv) / 100.0 + np.nanmean(ku) + np.nanmean(kd))
        if not control_pass:
            score += 100.0
        item = {
            "variant": variant_id,
            "mean_short_pad_rmse_mv": float(np.nanmean(pad_mv)),
            "mean_short_ku_rmse": float(np.nanmean(ku)),
            "mean_short_kd_rmse": float(np.nanmean(kd)),
            "control_pad_delta_mv": control_pad_delta_mv,
            "control_coeff_delta": control_coeff_delta,
            "control_pass": control_pass,
            "selection_score": score,
            "selected": False,
        }
        summary.append(item)
        if score < best_score:
            best_score = score
            best_variant = variant_id
    for item in summary:
        item["selected"] = item["variant"] == best_variant
    return best_variant, summary


def write_wide_metrics(rows: list[dict[str, object]]) -> None:
    by_case: dict[str, dict[str, object]] = {}
    for row in rows:
        case_id = str(row["case_id"])
        variant = str(row["variant"])
        out = by_case.setdefault(
            case_id,
            {
                "case_id": case_id,
                "description": row.get("description", ""),
                "pattern": row.get("pattern", ""),
                "pulse_high_ns": row.get("pulse_high_ns", ""),
            },
        )
        for key in [
            "pad_active_rmse_v",
            "pad_active_max_v",
            "ku_active_rmse",
            "kd_active_rmse",
            "ku_peak",
            "kd_min",
            "coeff_range_ok",
            "ku_jump_at_retrigger",
            "kd_jump_at_retrigger",
            "status",
        ]:
            out[f"{variant}_{key}"] = row.get(key, "")
    ordered = [by_case[case_id] for case_id in REQUIRED_CASE_IDS if case_id in by_case]
    write_csv(OUT_DIR / "metrics_by_case.csv", ordered)


def input_waveform(case: SweepCase, t_ns: np.ndarray) -> np.ndarray:
    points = build_pwl_points(case)
    xp = np.asarray([p[0] for p in points], dtype=float)
    yp = np.asarray([p[1] for p in points], dtype=float)
    return np.interp(t_ns, xp, yp)


def read_waveforms(case_id: str, hybrid_variant: str) -> dict[str, np.ndarray]:
    case_dir = CASES_DIR / case_id
    h_path = case_dir / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0"
    paths = {
        "legacy": case_dir / "ngspice_legacy" / f"{case_id}_ngspice_legacy.raw",
        "coeff_state": case_dir / "ngspice_coeff_state" / f"{case_id}_ngspice_coeff_state.raw",
        "hybrid": case_dir / f"ngspice_{hybrid_variant}" / f"{case_id}_ngspice_{hybrid_variant}.raw",
    }
    h = parse_hspice_tr0(h_path)
    t = to_ns(find_signal(h, "time"))
    out = {
        "time_ns": t,
        "hspice_pad": find_signal(h, "v(pad_ibis)"),
        "hspice_ku": find_signal(h, "v(ku)"),
        "hspice_kd": find_signal(h, "v(kd)"),
    }
    for key, path in paths.items():
        data = parse_ngspice_raw(path)
        nt = to_ns(find_signal(data, "time"))
        out[f"{key}_pad"] = interp_to(nt, find_signal(data, "v(pad)"), t)
        out[f"{key}_ku"] = interp_to(nt, find_signal(data, "v(xdrv.ku)", "v(xdrv:ku)"), t)
        out[f"{key}_kd"] = interp_to(nt, find_signal(data, "v(xdrv.kd)", "v(xdrv:kd)"), t)
        for diag in ["kutarget", "kdtarget", "kuleg", "kdleg", "kucor", "kdcor", "hshort", "highage"]:
            try:
                out[f"{key}_{diag}"] = interp_to(nt, find_signal(data, f"v(xdrv.{diag})", f"v(xdrv:{diag})"), t)
            except KeyError:
                pass
    return out


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def mark_commands(ax, case: SweepCase) -> None:
    rise_ns, fall_ns = command_times(case)
    ax.axvline(rise_ns, color="0.25", lw=1.0, ls=":", alpha=0.85)
    ax.axvline(fall_ns, color="0.25", lw=1.0, ls=":", alpha=0.85)
    ax.axvspan(rise_ns, fall_ns, color="#f2c94c", alpha=0.12, lw=0)


def plot_case_figures(case_id: str, hybrid_variant: str) -> None:
    ensure_dir(FIGURES_DIR)
    case = case_by_id(case_id)
    data = read_waveforms(case_id, hybrid_variant)
    t = data["time_ns"]
    x0, x1 = command_times(case)
    xlim = (x0 - 0.65, min(case.stop_ns, x1 + 5.0))

    fig, axes = plt.subplots(2, 1, figsize=(10.8, 6.6), sharex=True, height_ratios=[0.72, 1.35])
    for ax in axes:
        mark_commands(ax, case)
    axes[0].plot(t, input_waveform(case, t), color=COLORS["input"], lw=2.2, label="input command")
    style(axes[0], "Input (V)")
    axes[0].legend(loc="upper right")
    axes[1].plot(t, data["hspice_pad"], color=COLORS["hspice"], lw=2.2, label="HSPICE native IBIS")
    axes[1].plot(t, data["legacy_pad"], color=COLORS["legacy"], lw=1.9, label="legacy pybis")
    axes[1].plot(t, data["coeff_state_pad"], color=COLORS["coeff_state"], lw=1.9, label="CoeffState pybis")
    axes[1].plot(t, data["hybrid_pad"], color=COLORS["hybrid"], lw=2.0, label="ShortPulseHybrid")
    style(axes[1], "Pad (V)")
    axes[1].set_xlabel("Time (ns)")
    axes[1].legend(loc="best", ncol=2)
    axes[1].set_xlim(*xlim)
    fig.suptitle(f"{case_id}: input and pad overlay")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / f"{case_id}_01_input_pad_overlay.png", dpi=180)
    plt.close(fig)

    for coeff in ["ku", "kd"]:
        fig, ax = plt.subplots(figsize=(10.8, 4.3))
        mark_commands(ax, case)
        ax.plot(t, data[f"hspice_{coeff}"], color=COLORS["hspice"], lw=2.3, label=f"HSPICE {coeff.upper()}")
        ax.plot(t, data[f"legacy_{coeff}"], color=COLORS["legacy"], lw=2.0, label=f"legacy {coeff.upper()}")
        ax.plot(t, data[f"coeff_state_{coeff}"], color=COLORS["coeff_state"], lw=2.0, label=f"CoeffState {coeff.upper()}")
        ax.plot(t, data[f"hybrid_{coeff}"], color=COLORS["hybrid"], lw=2.1, label=f"ShortPulseHybrid {coeff.upper()}")
        ax.set_ylim(-0.12, 1.16)
        ax.set_xlim(*xlim)
        style(ax, coeff.upper())
        ax.set_xlabel("Time (ns)")
        ax.legend(loc="best", ncol=2)
        fig.suptitle(f"{case_id}: {coeff.upper()} only")
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        fig.savefig(FIGURES_DIR / f"{case_id}_02_{coeff}_only.png", dpi=180)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.8, 4.7))
    mark_commands(ax, case)
    ax.plot(t, data["hspice_pad"], color=COLORS["hspice"], lw=2.3, label="HSPICE native IBIS")
    ax.plot(t, data["legacy_pad"], color=COLORS["legacy"], lw=1.8, label="legacy pybis")
    ax.plot(t, data["hybrid_pad"], color=COLORS["hybrid"], lw=2.1, label="ShortPulseHybrid")
    mask = (t >= xlim[0]) & (t <= xlim[1])
    ax.fill_between(t[mask], data["hspice_pad"][mask], data["legacy_pad"][mask], color=COLORS["legacy"], alpha=0.15, label="legacy mismatch area")
    ax.fill_between(t[mask], data["hspice_pad"][mask], data["hybrid_pad"][mask], color=COLORS["hybrid"], alpha=0.16, label="hybrid mismatch area")
    style(ax, "Pad (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_xlim(*xlim)
    ax.legend(loc="best", ncol=2)
    fig.suptitle(f"{case_id}: pad consequence")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIGURES_DIR / f"{case_id}_03_pad_consequence.png", dpi=180)
    plt.close(fig)


def plot_control_vs_interrupted(hybrid_variant: str) -> None:
    control = read_waveforms(CONTROL_CASE, hybrid_variant)
    short = read_waveforms(DEMO_CASE, hybrid_variant)
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.4), sharex=False)
    for ax, case_id, data, coeff in [
        (axes[0, 0], CONTROL_CASE, control, "pad"),
        (axes[0, 1], DEMO_CASE, short, "pad"),
        (axes[1, 0], CONTROL_CASE, control, "ku"),
        (axes[1, 1], DEMO_CASE, short, "ku"),
    ]:
        case = case_by_id(case_id)
        mark_commands(ax, case)
        t = data["time_ns"]
        ax.plot(t, data[f"hspice_{coeff}"], color=COLORS["hspice"], lw=2.1, label="HSPICE")
        ax.plot(t, data[f"legacy_{coeff}"], color=COLORS["legacy"], lw=1.8, label="legacy")
        ax.plot(t, data[f"coeff_state_{coeff}"], color=COLORS["coeff_state"], lw=1.8, label="CoeffState")
        ax.plot(t, data[f"hybrid_{coeff}"], color=COLORS["hybrid"], lw=2.0, label="Hybrid")
        x0, x1 = command_times(case)
        ax.set_xlim(x0 - 0.65, min(case.stop_ns, x1 + 5.0))
        style(ax, "Pad (V)" if coeff == "pad" else "Ku")
        ax.set_title(case_id)
    axes[1, 0].set_xlabel("Time (ns)")
    axes[1, 1].set_xlabel("Time (ns)")
    axes[0, 1].legend(loc="best", ncol=2)
    fig.suptitle("Control long pulse vs interrupted short pulse")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / "control_vs_interrupted.png", dpi=180)
    plt.close(fig)


def plot_summary_bars(rows: list[dict[str, object]], hybrid_variant: str) -> None:
    short_ids = ["short_pulse_500ps_high", "short_pulse_1ns_high", "short_pulse_2ns_high"]
    metrics = [
        ("pad_active_rmse_v", "Pad RMSE (mV)", 1e3),
        ("ku_active_rmse", "Ku RMSE", 1.0),
        ("kd_active_rmse", "Kd RMSE", 1.0),
        ("ku_peak", "Ku peak", 1.0),
        ("kd_min", "Kd minimum", 1.0),
    ]
    variants = [("legacy", "legacy", COLORS["legacy"]), ("coeff_state", "CoeffState", COLORS["coeff_state"]), (hybrid_variant, "Hybrid", COLORS["hybrid"])]
    row_lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    fig, axes = plt.subplots(len(metrics), 1, figsize=(11.5, 12.6), sharex=True)
    x = np.arange(len(short_ids))
    width = 0.24
    for ax, (metric, ylabel, scale) in zip(axes, metrics):
        for offset, (variant, label, color) in zip([-width, 0.0, width], variants):
            values = [float(row_lookup[(case_id, variant)][metric]) * scale for case_id in short_ids]
            ax.bar(x + offset, values, width=width, color=color, alpha=0.88, label=label)
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", alpha=0.28)
    axes[0].legend(loc="best", ncol=3)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(["500 ps", "1 ns", "2 ns"])
    axes[-1].set_xlabel("Short high-pulse width")
    fig.suptitle("Short-pulse summary: lower RMSE is better; Ku peak/Kd minimum show coefficient behavior")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(FIGURES_DIR / "short_pulse_summary_bars.png", dpi=180)
    plt.close(fig)


def write_demo_metrics(rows: list[dict[str, object]], hybrid_variant: str) -> None:
    selected = [
        r
        for r in rows
        if r.get("case_id") in {"short_pulse_500ps_high", "short_pulse_1ns_high", "short_pulse_2ns_high"}
        and r.get("variant") in {"legacy", "coeff_state", hybrid_variant}
    ]
    write_csv(DEMO_DIR / "demo_metrics.csv", selected)


def write_readme(rows: list[dict[str, object]], selection_rows: list[dict[str, object]], hybrid_variant: str) -> None:
    lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    control_legacy = lookup[(CONTROL_CASE, "legacy")]
    control_hybrid = lookup[(CONTROL_CASE, hybrid_variant)]
    control_pad_delta_mv = (float(control_hybrid["pad_active_rmse_v"]) - float(control_legacy["pad_active_rmse_v"])) * 1e3
    control_coeff_delta = max(float(control_hybrid["ku_active_rmse"]), float(control_hybrid["kd_active_rmse"])) - max(
        float(control_legacy["ku_active_rmse"]), float(control_legacy["kd_active_rmse"])
    )

    one_ns = {
        key: lookup[(DEMO_CASE, key)]
        for key in ["legacy", "coeff_state", hybrid_variant]
    }
    h_data = parse_hspice_tr0(CASES_DIR / DEMO_CASE / "hspice_native_ibis" / f"{DEMO_CASE}_hspice_native_ibis.tr0")
    h_t = to_ns(find_signal(h_data, "time"))
    mask = active_mask(h_t, case_by_id(DEMO_CASE))
    h_ku_peak = float(np.max(find_signal(h_data, "v(ku)")[mask]))
    h_pad_peak = float(np.max(find_signal(h_data, "v(pad_ibis)")[mask]))
    demo_waves = read_waveforms(DEMO_CASE, hybrid_variant)
    legacy_pad_peak = float(demo_waves["legacy_pad"][mask].max())
    coeff_pad_peak = float(demo_waves["coeff_state_pad"][mask].max())
    hybrid_pad_peak = float(demo_waves["hybrid_pad"][mask].max())

    short_rows = [r for r in rows if str(r.get("case_id", "")).startswith("short_pulse") and r.get("variant") == hybrid_variant]
    legacy_short = {r["case_id"]: r for r in rows if str(r.get("case_id", "")).startswith("short_pulse") and r.get("variant") == "legacy"}
    improved = []
    for row in short_rows:
        legacy = legacy_short[row["case_id"]]
        coeff_range_ok = row["coeff_range_ok"] is True or str(row["coeff_range_ok"]).lower() == "true"
        improved.append(
            float(row["pad_active_rmse_v"]) < float(legacy["pad_active_rmse_v"])
            and float(row["ku_active_rmse"]) < float(legacy["ku_active_rmse"])
            and float(row["kd_active_rmse"]) < float(legacy["kd_active_rmse"])
            and coeff_range_ok
        )

    lines = [
        "# io_buf Short-Pulse Hybrid Retrigger Study",
        "",
        "This study keeps legacy `InputDriven` as the default and tests an opt-in `InputDrivenShortPulseHybrid` mode only on interrupted high pulses.",
        "",
        "## Headline",
        "",
        f"- Selected hybrid candidate: `{hybrid_variant}`.",
        f"- Long-pulse control pad RMSE delta versus legacy: `{control_pad_delta_mv:.3f} mV`.",
        f"- Long-pulse control max Ku/Kd RMSE delta versus legacy: `{control_coeff_delta:.5f}`.",
        f"- Short-pulse coefficient-first improvements versus legacy: `{sum(improved)}` / `{len(improved)}`.",
        "- Legacy pybis generation remains unchanged; hybrid circuitry is only present when `--subcircuit-type InputDrivenShortPulseHybrid*` is requested.",
        "",
        "## short_pulse_1ns_high Specific Numbers",
        "",
        f"- HSPICE Ku peak: `{h_ku_peak:.4f}`",
        f"- legacy Ku peak: `{float(one_ns['legacy']['ku_peak']):.4f}`",
        f"- CoeffState Ku peak: `{float(one_ns['coeff_state']['ku_peak']):.4f}`",
        f"- ShortPulseHybrid Ku peak: `{float(one_ns[hybrid_variant]['ku_peak']):.4f}`",
        f"- HSPICE pad peak: `{h_pad_peak:.4f} V`",
        f"- legacy pad peak: `{legacy_pad_peak:.4f} V`",
        f"- CoeffState pad peak: `{coeff_pad_peak:.4f} V`",
        f"- ShortPulseHybrid pad peak: `{hybrid_pad_peak:.4f} V`",
        "",
        "## Short-Pulse Metric Table",
        "",
        "| Case | Flow | Pad RMSE mV | Ku RMSE | Kd RMSE | Ku peak | Kd minimum |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for case_id in ["short_pulse_500ps_high", "short_pulse_1ns_high", "short_pulse_2ns_high"]:
        for variant_id, flow_name in [
            ("legacy", "legacy pybis"),
            ("coeff_state", "CoeffState"),
            (hybrid_variant, "ShortPulseHybrid"),
        ]:
            row = lookup[(case_id, variant_id)]
            lines.append(
                f"| {case_id} | {flow_name} | {float(row['pad_active_rmse_v']) * 1e3:.3f} | "
                f"{float(row['ku_active_rmse']):.4f} | {float(row['kd_active_rmse']):.4f} | "
                f"{float(row['ku_peak']):.4f} | {float(row['kd_min']):.4f} |"
            )
    lines.extend(
        [
            "",
            "## Candidate Selection",
            "",
            "| Candidate | Mean short pad RMSE mV | Mean short Ku RMSE | Mean short Kd RMSE | Control pad delta mV | Control coeff delta | Selected |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in selection_rows:
        lines.append(
            "| {variant} | {mean_short_pad_rmse_mv:.3f} | {mean_short_ku_rmse:.4f} | {mean_short_kd_rmse:.4f} | "
            "{control_pad_delta_mv:.3f} | {control_coeff_delta:.5f} | {selected} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "- `figures/*_input_pad_overlay.png`: input plus pad overlay for each short pulse.",
            "- `figures/*_ku_only.png`: Ku plotted separately, with distinct colors for HSPICE, legacy, CoeffState, and hybrid.",
            "- `figures/*_kd_only.png`: Kd plotted separately.",
            "- `figures/*_pad_consequence.png`: pad mismatch area for legacy and hybrid.",
            "- `figures/control_vs_interrupted.png`: long-pulse control versus interrupted 1 ns pulse.",
            "- `figures/short_pulse_summary_bars.png`: pad RMSE, Ku RMSE, Kd RMSE, Ku peak, and Kd minimum.",
            "",
            "## Interpretation",
            "",
            "This is still experimental. A useful result requires coefficient correctness, not just a nicer pad waveform.",
            "The hybrid is only a candidate for broader validation if it preserves the long-pulse control and improves pad, Ku, and Kd on the short-pulse cases.",
            "",
        ]
    )
    write_text(DEMO_DIR / "README.md", "\n".join(lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# io_buf Short-Pulse Hybrid Retrigger Study",
                "",
                f"Canonical demo: `interrupted_switching_demo/README.md`",
                f"Selected hybrid candidate: `{hybrid_variant}`",
                "",
                "Primary CSVs:",
                "",
                "- `candidate_metrics.csv`",
                "- `metrics_by_case.csv`",
                "- `hybrid_selection.csv`",
                "- `interrupted_switching_demo/demo_metrics.csv`",
                "",
            ]
        ),
    )


def generate_report(rows: list[dict[str, object]]) -> str:
    best_hybrid, selection = choose_best_hybrid(rows)
    write_csv(OUT_DIR / "hybrid_selection.csv", selection)
    write_wide_metrics(rows)
    write_demo_metrics(rows, best_hybrid)
    for case_id in ["short_pulse_500ps_high", "short_pulse_1ns_high", "short_pulse_2ns_high"]:
        plot_case_figures(case_id, best_hybrid)
    plot_control_vs_interrupted(best_hybrid)
    plot_summary_bars(rows, best_hybrid)
    write_readme(rows, selection, best_hybrid)
    return best_hybrid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Short-pulse-only pybis hybrid retrigger study.")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--ibis", type=Path, default=DEFAULT_IBIS)
    parser.add_argument("--case", action="append", default=[], help="Run only this case_id. May be repeated.")
    parser.add_argument("--all-cases", action="store_true", help="Run all cases from the coefficient-state sweep.")
    parser.add_argument("--resume", action="store_true", help="Skip completed case/variant rows.")
    parser.add_argument("--summarize-only", action="store_true", help="Regenerate plots/report from candidate_metrics.csv.")
    parser.add_argument("--timeout-s", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in [OUT_DIR, COMMON_DIR, CASES_DIR, DEMO_DIR, FIGURES_DIR]:
        ensure_dir(path)

    if args.summarize_only:
        rows = read_csv(OUT_DIR / "candidate_metrics.csv")
        best = generate_report(rows)
        print(f"OUT_DIR={OUT_DIR}")
        print(f"SELECTED_HYBRID={best}")
        return 0

    model_paths = prepare_common(args.ibis)
    cases = selected_cases(args.case, args.all_cases)
    existing_rows = read_csv(OUT_DIR / "candidate_metrics.csv") if args.resume else []
    done = {(str(r.get("case_id")), str(r.get("variant"))) for r in existing_rows}
    rows = list(existing_rows)

    for idx, case in enumerate(cases, start=1):
        case_done = all((case.case_id, variant.variant_id) in done for variant in VARIANTS)
        if args.resume and case_done:
            print(f"[{idx}/{len(cases)}] {case.case_id} (resume skip)", flush=True)
            continue
        print(f"[{idx}/{len(cases)}] {case.case_id}", flush=True)
        rows = [r for r in rows if str(r.get("case_id")) != case.case_id]
        try:
            rows.extend(run_case(case, args.ngspice, args.ibis, model_paths, args.timeout_s))
        except Exception as exc:
            rows.append({"case_id": case.case_id, "variant": "case_error", "status": "failed", "error": str(exc)})
        ordered_case_ids = [c.case_id for c in selected_cases([], args.all_cases)]
        order = {(case_id, variant.variant_id): (i, j) for i, case_id in enumerate(ordered_case_ids) for j, variant in enumerate(VARIANTS)}
        rows.sort(key=lambda r: order.get((str(r.get("case_id")), str(r.get("variant"))), (9999, 9999)))
        write_csv(OUT_DIR / "candidate_metrics.csv", rows)

    ok_rows = [r for r in rows if r.get("variant") != "case_error"]
    best = generate_report(ok_rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"DEMO={DEMO_DIR / 'README.md'}")
    print(f"SELECTED_HYBRID={best}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
