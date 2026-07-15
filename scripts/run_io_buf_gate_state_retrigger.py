from __future__ import annotations

import argparse
import csv
import shutil
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


OUT_DIR = ROOT / "results" / "io_buf_gate_state_retrigger_2026-06-22"
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
    "short_hybrid": "#9467bd",
    "gate_hybrid": "#d62728",
    "gate_full": "#8c564b",
    "input": "#222222",
    "target": "#7f7f7f",
    "state": "#17becf",
}


@dataclass(frozen=True)
class Variant:
    variant_id: str
    label: str
    subcircuit_type: str
    save_diagnostics: bool = False
    include_main_plots: bool = True


VARIANTS = [
    Variant("legacy", "legacy pybis", "InputDriven"),
    Variant("short_hybrid", "ShortPulseHybrid", "InputDrivenShortPulseHybrid", save_diagnostics=True),
    Variant("gate_hybrid", "GateStateHybrid", "InputDrivenGateStateHybrid", save_diagnostics=True),
    Variant("gate_full", "GateStateFull diagnostic", "InputDrivenGateStateFull", save_diagnostics=True, include_main_plots=False),
]


def case_by_id(case_id: str) -> SweepCase:
    return {case.case_id: case for case in build_cases()}[case_id]


def selected_cases(case_ids: list[str]) -> list[SweepCase]:
    available = {case.case_id: case for case in build_cases()}
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
            " V(xdrv.hinterrupt) V(xdrv.highage)"
            " V(xdrv.koverlap)"
        )
        extra += (
            " V(xdrv.kucor) V(xdrv.kdcor) V(xdrv.hshort)"
            " V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget)"
            " V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kugateraw) V(xdrv.kdgateraw)"
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


def run_hspice_case(case: SweepCase, ibis_path: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], Path]:
    h_dir = CASES_DIR / case.case_id / "hspice_native_ibis"
    ensure_dir(h_dir)
    shutil.copy2(ibis_path, h_dir / "io_buf.ibs")
    stem = f"{case.case_id}_hspice_native_ibis"
    deck = h_dir / f"{stem}.sp"
    write_text(deck, make_hspice_deck(case))
    rc = run_process(["hspice", "-i", deck.name, "-o", stem], h_dir, h_dir / "hspice_stdout.log", timeout_s=timeout_s)
    if rc != 0:
        raise RuntimeError(f"HSPICE return code {rc}")
    return parse_hspice_tr0(h_dir / f"{stem}.tr0"), deck


def run_ngspice_variant(
    case: SweepCase,
    variant: Variant,
    model_path: Path,
    ngspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], Path, Path]:
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
    return parse_ngspice_raw(raw), deck, raw


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


def overlap_energy(t_ns: np.ndarray, ku: np.ndarray, kd: np.ndarray, mask: np.ndarray) -> float:
    if np.count_nonzero(mask) < 2:
        return 0.0
    return float(np.trapezoid(np.maximum(ku[mask], 0.0) * np.maximum(kd[mask], 0.0), t_ns[mask]))


def optional_signal(data: dict[str, np.ndarray], t_src_ns: np.ndarray, t_dst_ns: np.ndarray, *names: str) -> np.ndarray | None:
    try:
        return interp_to(t_src_ns, find_signal(data, *names), t_dst_ns)
    except KeyError:
        return None


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
        "overlap_energy_ns": overlap_energy(h_t, n_ku, n_kd, mask),
        "status": status_for(pad_rmse, ku_rmse, kd_rmse),
    }
    for name in [
        "kutarget",
        "kdtarget",
        "kuleg",
        "kdleg",
        "kucor",
        "kdcor",
        "hshort",
        "hinterrupt",
        "highage",
        "gup",
        "gdn",
        "guptarget",
        "gdntarget",
        "kugate",
        "kdgate",
        "kugateraw",
        "kdgateraw",
        "koverlap",
    ]:
        sig = optional_signal(n_data, n_t, h_t, f"v(xdrv.{name})", f"v(xdrv:{name})")
        if sig is None:
            row[f"{name}_min"] = ""
            row[f"{name}_max"] = ""
        else:
            row[f"{name}_min"] = float(np.min(sig[mask]))
            row[f"{name}_max"] = float(np.max(sig[mask]))
    return row


def run_case(case: SweepCase, ngspice: Path, ibis_path: Path, model_paths: dict[str, Path], timeout_s: int) -> list[dict[str, object]]:
    h_data, h_deck = run_hspice_case(case, ibis_path, timeout_s)
    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        n_data, n_deck, raw = run_ngspice_variant(case, variant, model_paths[variant.variant_id], ngspice, timeout_s)
        rows.append(score_variant(case, variant, h_data, n_data, h_deck, n_deck, raw))
    return rows


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
            "ku_active_rmse",
            "kd_active_rmse",
            "ku_peak",
            "kd_min",
            "overlap_energy_ns",
            "coeff_range_ok",
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


def read_waveforms(case_id: str) -> dict[str, np.ndarray]:
    case_dir = CASES_DIR / case_id
    h_path = case_dir / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0"
    h = parse_hspice_tr0(h_path)
    t = to_ns(find_signal(h, "time"))
    out = {
        "time_ns": t,
        "hspice_pad": find_signal(h, "v(pad_ibis)"),
        "hspice_ku": find_signal(h, "v(ku)"),
        "hspice_kd": find_signal(h, "v(kd)"),
    }
    for variant in VARIANTS:
        path = case_dir / f"ngspice_{variant.variant_id}" / f"{case_id}_ngspice_{variant.variant_id}.raw"
        data = parse_ngspice_raw(path)
        nt = to_ns(find_signal(data, "time"))
        out[f"{variant.variant_id}_pad"] = interp_to(nt, find_signal(data, "v(pad)"), t)
        out[f"{variant.variant_id}_ku"] = interp_to(nt, find_signal(data, "v(xdrv.ku)", "v(xdrv:ku)"), t)
        out[f"{variant.variant_id}_kd"] = interp_to(nt, find_signal(data, "v(xdrv.kd)", "v(xdrv:kd)"), t)
        for name in [
            "kutarget",
            "kdtarget",
            "kuleg",
            "kdleg",
            "hinterrupt",
            "highage",
            "gup",
            "gdn",
            "guptarget",
            "gdntarget",
            "kugate",
            "kdgate",
            "koverlap",
        ]:
            sig = optional_signal(data, nt, t, f"v(xdrv.{name})", f"v(xdrv:{name})")
            if sig is not None:
                out[f"{variant.variant_id}_{name}"] = sig
    return out


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def mark_commands(ax, case: SweepCase) -> None:
    rise_ns, fall_ns = command_times(case)
    ax.axvline(rise_ns, color="0.25", lw=1.0, ls=":", alpha=0.85)
    ax.axvline(fall_ns, color="0.25", lw=1.0, ls=":", alpha=0.85)
    ax.axvspan(rise_ns, fall_ns, color="#f2c94c", alpha=0.12, lw=0)


def plot_main_case(case_id: str) -> None:
    ensure_dir(FIGURES_DIR)
    case = case_by_id(case_id)
    data = read_waveforms(case_id)
    t = data["time_ns"]
    x0, x1 = command_times(case)
    xlim = (x0 - 0.65, min(case.stop_ns, x1 + 5.0))
    flows = [
        ("hspice", "HSPICE native IBIS"),
        ("legacy", "legacy pybis"),
        ("short_hybrid", "ShortPulseHybrid"),
        ("gate_hybrid", "GateStateHybrid"),
    ]

    fig, axes = plt.subplots(2, 1, figsize=(10.8, 6.6), sharex=True, height_ratios=[0.72, 1.35])
    for ax in axes:
        mark_commands(ax, case)
    axes[0].plot(t, input_waveform(case, t), color=COLORS["input"], lw=2.2, label="input command")
    style(axes[0], "Input (V)")
    axes[0].legend(loc="upper right")
    for key, label in flows:
        axes[1].plot(t, data[f"{key}_pad"], color=COLORS[key], lw=2.0, label=label)
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
        for key, label in flows:
            ax.plot(t, data[f"{key}_{coeff}"], color=COLORS[key], lw=2.0, label=f"{label} {coeff.upper()}")
        ax.set_ylim(-0.12, 1.16)
        ax.set_xlim(*xlim)
        style(ax, coeff.upper())
        ax.set_xlabel("Time (ns)")
        ax.legend(loc="best", ncol=2)
        fig.suptitle(f"{case_id}: {coeff.upper()} only")
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        fig.savefig(FIGURES_DIR / f"{case_id}_02_{coeff}_only.png", dpi=180)
        plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(10.8, 6.8), sharex=True)
    for ax in axes:
        mark_commands(ax, case)
    axes[0].plot(t, data["gate_hybrid_gup"], color=COLORS["gate_hybrid"], lw=2.0, label="GUP")
    axes[0].plot(t, data["gate_hybrid_gdn"], color=COLORS["state"], lw=2.0, label="GDN")
    axes[0].plot(t, data["gate_hybrid_hinterrupt"], color=COLORS["target"], lw=1.7, label="HINTERRUPT")
    axes[0].set_ylim(-0.1, 1.12)
    style(axes[0], "Gate states")
    axes[0].legend(loc="best", ncol=3)
    axes[1].plot(t, data["gate_hybrid_kugate"], color=COLORS["gate_hybrid"], lw=2.0, label="KUGATE")
    axes[1].plot(t, data["gate_hybrid_kdgate"], color=COLORS["state"], lw=2.0, label="KDGATE")
    axes[1].plot(t, data["gate_hybrid_kutarget"], color="#aa4499", lw=1.5, label="KUTARGET")
    axes[1].plot(t, data["gate_hybrid_kdtarget"], color="#44aa99", lw=1.5, label="KDTARGET")
    axes[1].set_ylim(-0.12, 1.16)
    style(axes[1], "Gate coefficients")
    axes[1].legend(loc="best", ncol=2)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_xlim(*xlim)
    fig.suptitle(f"{case_id}: GateStateHybrid diagnostics")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / f"{case_id}_03_gate_state_diagnostics.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.8, 4.7))
    mark_commands(ax, case)
    ax.plot(t, data["hspice_pad"], color=COLORS["hspice"], lw=2.3, label="HSPICE native IBIS")
    ax.plot(t, data["short_hybrid_pad"], color=COLORS["short_hybrid"], lw=1.9, label="ShortPulseHybrid")
    ax.plot(t, data["gate_hybrid_pad"], color=COLORS["gate_hybrid"], lw=2.1, label="GateStateHybrid")
    mask = (t >= xlim[0]) & (t <= xlim[1])
    ax.fill_between(t[mask], data["hspice_pad"][mask], data["short_hybrid_pad"][mask], color=COLORS["short_hybrid"], alpha=0.14, label="short-hybrid mismatch")
    ax.fill_between(t[mask], data["hspice_pad"][mask], data["gate_hybrid_pad"][mask], color=COLORS["gate_hybrid"], alpha=0.14, label="gate-state mismatch")
    style(ax, "Pad (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_xlim(*xlim)
    ax.legend(loc="best", ncol=2)
    fig.suptitle(f"{case_id}: pad consequence")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIGURES_DIR / f"{case_id}_04_pad_consequence.png", dpi=180)
    plt.close(fig)


def plot_control_vs_interrupted() -> None:
    control = read_waveforms(CONTROL_CASE)
    short = read_waveforms(DEMO_CASE)
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
        for key, label in [
            ("hspice", "HSPICE"),
            ("legacy", "legacy"),
            ("short_hybrid", "ShortHybrid"),
            ("gate_hybrid", "GateState"),
        ]:
            ax.plot(t, data[f"{key}_{coeff}"], color=COLORS[key], lw=1.9, label=label)
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


def plot_summary_bars(rows: list[dict[str, object]]) -> None:
    short_ids = ["short_pulse_500ps_high", "short_pulse_1ns_high", "short_pulse_2ns_high"]
    metrics = [
        ("pad_active_rmse_v", "Pad RMSE (mV)", 1e3),
        ("ku_active_rmse", "Ku RMSE", 1.0),
        ("kd_active_rmse", "Kd RMSE", 1.0),
        ("ku_peak", "Ku peak", 1.0),
        ("kd_min", "Kd minimum", 1.0),
        ("overlap_energy_ns", "Ku*Kd overlap (ns)", 1.0),
    ]
    variants = [
        ("legacy", "legacy", COLORS["legacy"]),
        ("short_hybrid", "ShortHybrid", COLORS["short_hybrid"]),
        ("gate_hybrid", "GateState", COLORS["gate_hybrid"]),
    ]
    row_lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    fig, axes = plt.subplots(len(metrics), 1, figsize=(11.5, 14.0), sharex=True)
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
    fig.suptitle("Gate-state short-pulse summary")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(FIGURES_DIR / "short_pulse_summary_bars.png", dpi=180)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]]) -> None:
    lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    control_legacy = lookup[(CONTROL_CASE, "legacy")]
    control_gate = lookup[(CONTROL_CASE, "gate_hybrid")]
    control_pad_delta_mv = (float(control_gate["pad_active_rmse_v"]) - float(control_legacy["pad_active_rmse_v"])) * 1e3
    control_coeff_delta = max(float(control_gate["ku_active_rmse"]), float(control_gate["kd_active_rmse"])) - max(
        float(control_legacy["ku_active_rmse"]),
        float(control_legacy["kd_active_rmse"]),
    )

    one_ns = {key: lookup[(DEMO_CASE, key)] for key in ["legacy", "short_hybrid", "gate_hybrid", "gate_full"]}
    h_data = parse_hspice_tr0(CASES_DIR / DEMO_CASE / "hspice_native_ibis" / f"{DEMO_CASE}_hspice_native_ibis.tr0")
    h_t = to_ns(find_signal(h_data, "time"))
    mask = active_mask(h_t, case_by_id(DEMO_CASE))
    h_ku_peak = float(np.max(find_signal(h_data, "v(ku)")[mask]))
    h_pad_peak = float(np.max(find_signal(h_data, "v(pad_ibis)")[mask]))
    waves = read_waveforms(DEMO_CASE)

    short_ids = ["short_pulse_500ps_high", "short_pulse_1ns_high", "short_pulse_2ns_high"]
    gate_better_legacy = 0
    gate_better_short = 0
    for case_id in short_ids:
        gate = lookup[(case_id, "gate_hybrid")]
        legacy = lookup[(case_id, "legacy")]
        short = lookup[(case_id, "short_hybrid")]
        if (
            float(gate["pad_active_rmse_v"]) < float(legacy["pad_active_rmse_v"])
            and float(gate["ku_active_rmse"]) < float(legacy["ku_active_rmse"])
            and float(gate["kd_active_rmse"]) < float(legacy["kd_active_rmse"])
        ):
            gate_better_legacy += 1
        if (
            float(gate["pad_active_rmse_v"]) < float(short["pad_active_rmse_v"])
            and float(gate["ku_active_rmse"]) < float(short["ku_active_rmse"])
            and float(gate["kd_active_rmse"]) < float(short["kd_active_rmse"])
        ):
            gate_better_short += 1

    lines = [
        "# io_buf Gate-State pybis Retrigger Study",
        "",
        "This study tests an opt-in transistor-like `InputDrivenGateStateHybrid` mode against HSPICE native IBIS, legacy pybis, and the current short-pulse hybrid.",
        "",
        "## Headline",
        "",
        f"- Long-pulse control pad RMSE delta versus legacy: `{control_pad_delta_mv:.3f} mV`.",
        f"- Long-pulse control max Ku/Kd RMSE delta versus legacy: `{control_coeff_delta:.5f}`.",
        f"- GateStateHybrid coefficient-first improvements versus legacy: `{gate_better_legacy}` / `3` short-pulse cases.",
        f"- GateStateHybrid coefficient-first improvements versus ShortPulseHybrid: `{gate_better_short}` / `3` short-pulse cases.",
        "- `InputDrivenGateStateFull` is diagnostic only and is not considered for default behavior.",
        "",
        "## short_pulse_1ns_high Specific Numbers",
        "",
        f"- HSPICE Ku peak: `{h_ku_peak:.4f}`",
        f"- legacy Ku peak: `{float(one_ns['legacy']['ku_peak']):.4f}`",
        f"- ShortPulseHybrid Ku peak: `{float(one_ns['short_hybrid']['ku_peak']):.4f}`",
        f"- GateStateHybrid Ku peak: `{float(one_ns['gate_hybrid']['ku_peak']):.4f}`",
        f"- GateStateFull Ku peak: `{float(one_ns['gate_full']['ku_peak']):.4f}`",
        f"- HSPICE pad peak: `{h_pad_peak:.4f} V`",
        f"- legacy pad peak: `{float(waves['legacy_pad'][mask].max()):.4f} V`",
        f"- ShortPulseHybrid pad peak: `{float(waves['short_hybrid_pad'][mask].max()):.4f} V`",
        f"- GateStateHybrid pad peak: `{float(waves['gate_hybrid_pad'][mask].max()):.4f} V`",
        "",
        "## Short-Pulse Metric Table",
        "",
        "| Case | Flow | Pad RMSE mV | Ku RMSE | Kd RMSE | Ku peak | Kd minimum | Overlap ns |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case_id in short_ids:
        for variant_id, flow_name in [
            ("legacy", "legacy pybis"),
            ("short_hybrid", "ShortPulseHybrid"),
            ("gate_hybrid", "GateStateHybrid"),
            ("gate_full", "GateStateFull"),
        ]:
            row = lookup[(case_id, variant_id)]
            lines.append(
                f"| {case_id} | {flow_name} | {float(row['pad_active_rmse_v']) * 1e3:.3f} | "
                f"{float(row['ku_active_rmse']):.4f} | {float(row['kd_active_rmse']):.4f} | "
                f"{float(row['ku_peak']):.4f} | {float(row['kd_min']):.4f} | {float(row['overlap_energy_ns']):.4f} |"
            )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "- `figures/*_01_input_pad_overlay.png`: input plus pad overlay.",
            "- `figures/*_02_ku_only.png`: Ku-only comparison.",
            "- `figures/*_02_kd_only.png`: Kd-only comparison.",
            "- `figures/*_03_gate_state_diagnostics.png`: GUP/GDN, KUGATE/KDGATE, and targets.",
            "- `figures/*_04_pad_consequence.png`: mismatch area for ShortPulseHybrid versus GateStateHybrid.",
            "- `figures/control_vs_interrupted.png`: long-pulse preservation check.",
            "- `figures/short_pulse_summary_bars.png`: metrics and overlap energy.",
            "",
            "## Interpretation",
            "",
            "A real improvement requires better coefficient agreement, not just lower pad RMSE.",
            "The gate-state model remains experimental unless it preserves the long-pulse control and beats the current ShortPulseHybrid on Ku, Kd, and pad metrics.",
            "",
        ]
    )
    write_text(DEMO_DIR / "README.md", "\n".join(lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# io_buf Gate-State pybis Retrigger Study",
                "",
                "Canonical demo: `interrupted_switching_demo/README.md`",
                "",
                "Primary CSVs:",
                "",
                "- `candidate_metrics.csv`",
                "- `metrics_by_case.csv`",
                "- `interrupted_switching_demo/demo_metrics.csv`",
                "",
            ]
        ),
    )


def write_demo_metrics(rows: list[dict[str, object]]) -> None:
    selected = [
        r
        for r in rows
        if r.get("case_id") in {"short_pulse_500ps_high", "short_pulse_1ns_high", "short_pulse_2ns_high"}
    ]
    write_csv(DEMO_DIR / "demo_metrics.csv", selected)


def generate_report(rows: list[dict[str, object]]) -> None:
    write_wide_metrics(rows)
    write_demo_metrics(rows)
    for case_id in ["short_pulse_500ps_high", "short_pulse_1ns_high", "short_pulse_2ns_high"]:
        plot_main_case(case_id)
    plot_control_vs_interrupted()
    plot_summary_bars(rows)
    write_readme(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gate-state pybis retrigger study.")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--ibis", type=Path, default=DEFAULT_IBIS)
    parser.add_argument("--case", action="append", default=[], help="Run only this case_id. May be repeated.")
    parser.add_argument("--resume", action="store_true", help="Skip completed case/variant rows.")
    parser.add_argument("--summarize-only", action="store_true", help="Regenerate plots/report from candidate_metrics.csv.")
    parser.add_argument("--timeout-s", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in [OUT_DIR, COMMON_DIR, CASES_DIR, DEMO_DIR, FIGURES_DIR]:
        ensure_dir(path)

    if args.summarize_only:
        rows = [r for r in read_csv(OUT_DIR / "candidate_metrics.csv") if r.get("variant") != "case_error"]
        generate_report(rows)
        print(f"OUT_DIR={OUT_DIR}")
        print(f"DEMO={DEMO_DIR / 'README.md'}")
        return 0

    model_paths = prepare_common(args.ibis)
    cases = selected_cases(args.case)
    existing_rows = read_csv(OUT_DIR / "candidate_metrics.csv") if args.resume else []
    done = {(str(r.get("case_id")), str(r.get("variant"))) for r in existing_rows}
    rows = list(existing_rows)
    case_order = [case.case_id for case in selected_cases([])]
    order = {(case_id, variant.variant_id): (i, j) for i, case_id in enumerate(case_order) for j, variant in enumerate(VARIANTS)}

    for idx, case in enumerate(cases, start=1):
        if args.resume and all((case.case_id, variant.variant_id) in done for variant in VARIANTS):
            print(f"[{idx}/{len(cases)}] {case.case_id} (resume skip)", flush=True)
            continue
        print(f"[{idx}/{len(cases)}] {case.case_id}", flush=True)
        rows = [r for r in rows if str(r.get("case_id")) != case.case_id]
        try:
            rows.extend(run_case(case, args.ngspice, args.ibis, model_paths, args.timeout_s))
        except Exception as exc:
            rows.append({"case_id": case.case_id, "variant": "case_error", "status": "failed", "error": str(exc)})
        rows.sort(key=lambda r: order.get((str(r.get("case_id")), str(r.get("variant"))), (9999, 9999)))
        write_csv(OUT_DIR / "candidate_metrics.csv", rows)

    ok_rows = [r for r in rows if r.get("variant") != "case_error"]
    generate_report(ok_rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"DEMO={DEMO_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
