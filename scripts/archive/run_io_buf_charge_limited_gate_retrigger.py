import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import run_io_buf_directional_gate_state_retrigger as base


ROOT = base.ROOT
BASE_BUILD_PWL_POINTS = base.build_pwl_points
BASE_SCORE_VARIANT = base.score_variant
BASE_READ_WAVEFORMS = base.read_waveforms
OUT_DIR = ROOT / "results" / "io_buf_charge_limited_gate_retrigger_2026-06-22"
COMMON_DIR = OUT_DIR / "common"
CASES_DIR = OUT_DIR / "cases"
DEMO_DIR = OUT_DIR / "interrupted_switching_demo"
FIGURES_DIR = DEMO_DIR / "figures"

REQUIRED_CASE_IDS = [
    "edge_1ps_base_50r_2pf",
    "short_pulse_500ps_high",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
    "short_pulse_500ps_low",
    "short_pulse_1ns_low",
    "short_pulse_2ns_low",
    "double_toggle_1ps",
]
CONTROL_CASE = "edge_1ps_base_50r_2pf"
DEMO_CASE = "short_pulse_1ns_high"

COLORS = {
    "hspice": "#1f77b4",
    "legacy": "#ff7f0e",
    "short_hybrid": "#9467bd",
    "gate_hybrid": "#d62728",
    "dir_hybrid": "#2ca02c",
    "charge_hybrid": "#6f2dbd",
    "charge_fast": "#17becf",
    "charge_full": "#8c564b",
    "input": "#222222",
    "target": "#7f7f7f",
    "state": "#bcbd22",
}

VARIANTS = [
    base.Variant("legacy", "legacy pybis", "InputDriven"),
    base.Variant("short_hybrid", "ShortPulseHybrid", "InputDrivenShortPulseHybrid", save_diagnostics=True),
    base.Variant("gate_hybrid", "GateStateHybrid", "InputDrivenGateStateHybrid", save_diagnostics=True),
    base.Variant(
        "dir_hybrid",
        "DirectionalGateStateHybrid",
        "InputDrivenDirectionalGateStateHybrid",
        save_diagnostics=True,
    ),
    base.Variant(
        "charge_hybrid",
        "ChargeLimitedGateHybrid",
        "InputDrivenChargeLimitedGateHybrid",
        save_diagnostics=True,
    ),
    base.Variant(
        "charge_fast",
        "ChargeLimitedGateFastRecover",
        "InputDrivenChargeLimitedGateFastRecover",
        save_diagnostics=True,
    ),
    base.Variant(
        "charge_full",
        "ChargeLimitedGateFull diagnostic",
        "InputDrivenChargeLimitedGateFull",
        save_diagnostics=True,
        include_main_plots=False,
    ),
]


def install_globals() -> None:
    base.OUT_DIR = OUT_DIR
    base.COMMON_DIR = COMMON_DIR
    base.CASES_DIR = CASES_DIR
    base.DEMO_DIR = DEMO_DIR
    base.FIGURES_DIR = FIGURES_DIR
    base.REQUIRED_CASE_IDS = REQUIRED_CASE_IDS
    base.CONTROL_CASE = CONTROL_CASE
    base.DEMO_CASE = DEMO_CASE
    base.COLORS = COLORS
    base.VARIANTS = VARIANTS
    base.build_cases = build_cases
    base.build_pwl_points = build_pwl_points
    base.make_ngspice_deck = make_ngspice_deck
    base.score_variant = score_variant
    base.read_waveforms = read_waveforms
    base.plot_main_case = plot_main_case
    base.plot_high_low_comparison = plot_high_low_comparison
    base.plot_summary_bars = plot_summary_bars
    base.write_readme = write_readme
    base.generate_report = generate_report


def build_cases() -> list[base.StudyCase]:
    return [
        base.StudyCase(
            "edge_1ps_base_50r_2pf",
            "Baseline 1 ps rise/fall, 50 ohm + 2 pF",
            0.001,
            25.0,
            50.0,
            2.0,
            3.3,
            "rise_fall",
        ),
        base.StudyCase(
            "short_pulse_500ps_high",
            "500 ps high pulse with 1 ps edges, 50 ohm + 2 pF",
            0.001,
            12.5,
            50.0,
            2.0,
            3.3,
            "short_high",
            0.5,
        ),
        base.StudyCase(
            "short_pulse_1ns_high",
            "1 ns high pulse with 1 ps edges, 50 ohm + 2 pF",
            0.001,
            13.0,
            50.0,
            2.0,
            3.3,
            "short_high",
            1.0,
        ),
        base.StudyCase(
            "short_pulse_2ns_high",
            "2 ns high pulse with 1 ps edges, 50 ohm + 2 pF",
            0.001,
            14.0,
            50.0,
            2.0,
            3.3,
            "short_high",
            2.0,
        ),
        base.StudyCase(
            "short_pulse_500ps_low",
            "500 ps low pulse after settled high, 50 ohm + 2 pF",
            0.001,
            16.0,
            50.0,
            2.0,
            3.3,
            "short_low",
            0.5,
        ),
        base.StudyCase(
            "short_pulse_1ns_low",
            "1 ns low pulse after settled high, 50 ohm + 2 pF",
            0.001,
            16.5,
            50.0,
            2.0,
            3.3,
            "short_low",
            1.0,
        ),
        base.StudyCase(
            "short_pulse_2ns_low",
            "2 ns low pulse after settled high, 50 ohm + 2 pF",
            0.001,
            17.5,
            50.0,
            2.0,
            3.3,
            "short_low",
            2.0,
        ),
        base.StudyCase(
            "double_toggle_1ps",
            "Two interrupted high pulses with 1 ps edges, 50 ohm + 2 pF",
            0.001,
            16.0,
            50.0,
            2.0,
            3.3,
            "double_toggle",
            0.6,
        ),
    ]


def build_pwl_points(case: base.StudyCase) -> list[tuple[float, float]]:
    if case.pattern != "double_toggle":
        return BASE_BUILD_PWL_POINTS(case)
    e = case.edge_ns
    hv = case.high_v
    return [
        (0.0, 0.0),
        (5.0, 0.0),
        (5.0 + e, hv),
        (5.0 + case.pulse_width_ns, hv),
        (5.0 + case.pulse_width_ns + e, 0.0),
        (7.2, 0.0),
        (7.2 + e, hv),
        (7.2 + case.pulse_width_ns, hv),
        (7.2 + case.pulse_width_ns + e, 0.0),
        (case.stop_ns, 0.0),
    ]


def make_ngspice_deck(case: base.StudyCase, variant: base.Variant) -> str:
    extra = ""
    if variant.save_diagnostics:
        extra = (
            " V(xdrv.kutarget) V(xdrv.kdtarget)"
            " V(xdrv.kuleg) V(xdrv.kdleg)"
            " V(xdrv.hinterrupt) V(xdrv.hshort)"
            " V(xdrv.highage) V(xdrv.lowage)"
            " V(xdrv.koverlap)"
            " V(xdrv.gup) V(xdrv.gdn) V(xdrv.kugate) V(xdrv.kdgate)"
            " V(xdrv.ku_on) V(xdrv.ku_off) V(xdrv.kd_off) V(xdrv.kd_on)"
            " V(xdrv.kudir) V(xdrv.kddir)"
            " V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)"
            " V(xdrv.hdiractive) V(xdrv.halign) V(xdrv.haligned)"
            " V(xdrv.qpu) V(xdrv.qpd)"
            " V(xdrv.qputarget) V(xdrv.qpdtarget)"
            " V(xdrv.kuchg) V(xdrv.kdchg)"
            " V(xdrv.hchgactive) V(xdrv.had_rise) V(xdrv.had_fall)"
            " V(xdrv.hchgunsettled)"
        )
    return f"""* io_buf {variant.label}/ngspice charge-limited Ku/Kd extraction
* Sweep case: {case.case_id}
* {case.description}
.title io_buf ngspice {variant.label} Ku/Kd extraction {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{base.pwl_text(case)}

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 {base.fmt_num(case.r_load_ohm)}
{base.c_load_line("pad", case.c_load_pf).rstrip()}

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){extra}
.tran 0.001n {base.spice_time_ns(case.stop_ns)}
.end
"""


def time_of_extreme(t: np.ndarray, y: np.ndarray, mask: np.ndarray, kind: str) -> float:
    if np.count_nonzero(mask) == 0:
        return float("nan")
    idxs = np.where(mask)[0]
    local = y[mask]
    idx = int(np.argmax(local) if kind == "max" else np.argmin(local))
    return float(t[idxs[idx]])


def time_of_worst_error(t: np.ndarray, ref: np.ndarray, cand: np.ndarray, mask: np.ndarray) -> float:
    if np.count_nonzero(mask) == 0:
        return float("nan")
    idxs = np.where(mask)[0]
    idx = int(np.argmax(np.abs(ref[mask] - cand[mask])))
    return float(t[idxs[idx]])


def active_interval(t: np.ndarray, y: np.ndarray, mask: np.ndarray, threshold: float = 0.5) -> tuple[float, float, int]:
    active = mask & (y > threshold)
    count = int(np.count_nonzero(active))
    if count == 0:
        return float("nan"), float("nan"), 0
    return float(t[active][0]), float(t[active][-1]), count


def score_variant(
    case: base.StudyCase,
    variant: base.Variant,
    h_data: dict[str, np.ndarray],
    n_data: dict[str, np.ndarray],
    hspice_deck: Path,
    ngspice_deck: Path,
    raw_path: Path,
) -> dict[str, object]:
    row = BASE_SCORE_VARIANT(case, variant, h_data, n_data, hspice_deck, ngspice_deck, raw_path)
    if row.get("status") == "failed":
        return row

    h_t = base.to_ns(base.find_signal(h_data, "time"))
    n_t = base.to_ns(base.find_signal(n_data, "time"))
    mask = base.active_mask(h_t, case)
    h_pad = base.find_signal(h_data, "v(pad_ibis)")
    h_ku = base.find_signal(h_data, "v(ku)")
    h_kd = base.find_signal(h_data, "v(kd)")
    n_pad = base.interp_to(n_t, base.find_signal(n_data, "v(pad)"), h_t)
    n_ku = base.interp_to(n_t, base.find_signal(n_data, "v(xdrv.ku)", "v(xdrv:ku)"), h_t)
    n_kd = base.interp_to(n_t, base.find_signal(n_data, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)

    row.update(
        {
            "ku_peak_time_ns": time_of_extreme(h_t, n_ku, mask, "max"),
            "ku_min_time_ns": time_of_extreme(h_t, n_ku, mask, "min"),
            "kd_min_time_ns": time_of_extreme(h_t, n_kd, mask, "min"),
            "kd_max_time_ns": time_of_extreme(h_t, n_kd, mask, "max"),
            "pad_peak_v": float(np.max(n_pad[mask])) if np.count_nonzero(mask) else "",
            "pad_min_v": float(np.min(n_pad[mask])) if np.count_nonzero(mask) else "",
            "pad_peak_time_ns": time_of_extreme(h_t, n_pad, mask, "max"),
            "pad_min_time_ns": time_of_extreme(h_t, n_pad, mask, "min"),
            "pad_worst_error_time_ns": time_of_worst_error(h_t, h_pad, n_pad, mask),
            "ku_worst_error_time_ns": time_of_worst_error(h_t, h_ku, n_ku, mask),
            "kd_worst_error_time_ns": time_of_worst_error(h_t, h_kd, n_kd, mask),
            "hspice_pad_peak_v": float(np.max(h_pad[mask])) if np.count_nonzero(mask) else "",
            "hspice_pad_min_v": float(np.min(h_pad[mask])) if np.count_nonzero(mask) else "",
        }
    )

    for name in [
        "qpu",
        "qpd",
        "qputarget",
        "qpdtarget",
        "kuchg",
        "kdchg",
        "hchgactive",
        "had_rise",
        "had_fall",
        "hchgunsettled",
        "hfall_after_rise",
        "hrise_after_fall",
        "koverlap",
    ]:
        sig = base.optional_signal(n_data, n_t, h_t, f"v(xdrv.{name})", f"v(xdrv:{name})")
        if sig is None:
            row[f"{name}_min"] = ""
            row[f"{name}_max"] = ""
            continue
        row[f"{name}_min"] = float(np.min(sig[mask])) if np.count_nonzero(mask) else ""
        row[f"{name}_max"] = float(np.max(sig[mask])) if np.count_nonzero(mask) else ""
        if name in {"qpu", "qpd"}:
            row[f"{name}_overcancel"] = bool(np.min(sig[mask]) < -0.02 or np.max(sig[mask]) > 1.02)
        if name in {"hchgactive", "hfall_after_rise", "hrise_after_fall"}:
            start, end, count = active_interval(h_t, sig, mask)
            row[f"{name}_active_start_ns"] = start
            row[f"{name}_active_end_ns"] = end
            row[f"{name}_active_count"] = count
    return row


def read_waveforms(case_id: str) -> dict[str, np.ndarray]:
    data = BASE_READ_WAVEFORMS(case_id)
    t = data["time_ns"]
    case_dir = CASES_DIR / case_id
    for variant in VARIANTS:
        path = case_dir / f"ngspice_{variant.variant_id}" / f"{case_id}_ngspice_{variant.variant_id}.raw"
        if not path.exists():
            continue
        raw = base.parse_ngspice_raw(path)
        nt = base.to_ns(base.find_signal(raw, "time"))
        for name in [
            "qpu",
            "qpd",
            "qputarget",
            "qpdtarget",
            "kuchg",
            "kdchg",
            "hchgactive",
            "had_rise",
            "had_fall",
            "hchgunsettled",
            "hfall_after_rise",
            "hrise_after_fall",
            "koverlap",
            "kutarget",
            "kdtarget",
            "kuleg",
            "kdleg",
        ]:
            sig = base.optional_signal(raw, nt, t, f"v(xdrv.{name})", f"v(xdrv:{name})")
            if sig is not None:
                data[f"{variant.variant_id}_{name}"] = sig
    return data


def flows(include_full: bool = False) -> list[tuple[str, str]]:
    base_flows = [
        ("hspice", "HSPICE native IBIS"),
        ("legacy", "legacy pybis"),
        ("short_hybrid", "ShortPulseHybrid"),
        ("gate_hybrid", "GateStateHybrid"),
        ("dir_hybrid", "DirectionalGateStateHybrid"),
        ("charge_hybrid", "ChargeLimitedGateHybrid"),
        ("charge_fast", "ChargeLimitedGateFastRecover"),
    ]
    if include_full:
        base_flows.append(("charge_full", "ChargeLimitedGateFull"))
    return base_flows


def plot_main_case(case_id: str) -> None:
    base.ensure_dir(FIGURES_DIR)
    case = base.case_by_id(case_id)
    data = read_waveforms(case_id)
    t = data["time_ns"]
    x0, x1 = base.command_times(case)
    xlim = (max(0.0, x0 - 0.75), min(case.stop_ns, x1 + 5.0))

    fig, axes = plt.subplots(2, 1, figsize=(11.4, 6.8), sharex=True, height_ratios=[0.72, 1.35])
    for ax in axes:
        base.mark_commands(ax, case)
    axes[0].plot(t, base.input_waveform(case, t), color=COLORS["input"], lw=2.2, label="input command")
    base.style(axes[0], "Input (V)")
    axes[0].legend(loc="upper right")
    for key, label in flows():
        axes[1].plot(t, data[f"{key}_pad"], color=COLORS[key], lw=1.8, label=label)
    base.style(axes[1], "Pad (V)")
    axes[1].set_xlabel("Time (ns)")
    axes[1].legend(loc="best", ncol=2)
    axes[1].set_xlim(*xlim)
    fig.suptitle(f"{case_id}: input and pad overlay")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / f"{case_id}_01_input_pad_overlay.png", dpi=180)
    plt.close(fig)

    for coeff in ["ku", "kd"]:
        fig, ax = plt.subplots(figsize=(11.4, 4.5))
        base.mark_commands(ax, case)
        for key, label in flows():
            ax.plot(t, data[f"{key}_{coeff}"], color=COLORS[key], lw=1.9, label=f"{label} {coeff.upper()}")
        ax.set_ylim(-0.14, 1.18)
        ax.set_xlim(*xlim)
        base.style(ax, coeff.upper())
        ax.set_xlabel("Time (ns)")
        ax.legend(loc="best", ncol=2)
        fig.suptitle(f"{case_id}: {coeff.upper()} only")
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        fig.savefig(FIGURES_DIR / f"{case_id}_02_{coeff}_only.png", dpi=180)
        plt.close(fig)

    for variant in ["charge_hybrid", "charge_fast", "charge_full"]:
        if f"{variant}_qpu" not in data:
            continue
        fig, axes = plt.subplots(3, 1, figsize=(11.4, 9.1), sharex=True)
        for ax in axes:
            base.mark_commands(ax, case)
        axes[0].plot(t, data[f"{variant}_qpu"], color="#6f2dbd", lw=2.0, label="QPU")
        axes[0].plot(t, data[f"{variant}_qpd"], color="#17becf", lw=2.0, label="QPD")
        axes[0].plot(t, data[f"{variant}_qputarget"], color="#b38add", lw=1.6, label="QPUTARGET")
        axes[0].plot(t, data[f"{variant}_qpdtarget"], color="#9edae5", lw=1.6, label="QPDTARGET")
        axes[0].set_ylim(-0.1, 1.12)
        base.style(axes[0], "Charge state")
        axes[0].legend(loc="best", ncol=4)
        axes[1].plot(t, data[f"{variant}_kuchg"], color="#6f2dbd", lw=2.0, label="KUCHG")
        axes[1].plot(t, data[f"{variant}_kdchg"], color="#17becf", lw=2.0, label="KDCHG")
        axes[1].plot(t, data[f"{variant}_kuleg"], color=COLORS["legacy"], lw=1.4, label="KULEG")
        axes[1].plot(t, data[f"{variant}_kdleg"], color="#ffbb78", lw=1.4, label="KDLEG")
        axes[1].set_ylim(-0.14, 1.18)
        base.style(axes[1], "Coeff candidates")
        axes[1].legend(loc="best", ncol=4)
        axes[2].plot(t, data[f"{variant}_hchgactive"], color="#6f2dbd", lw=2.0, label="HCHGACTIVE")
        axes[2].plot(t, data[f"{variant}_hfall_after_rise"], color="#d62728", lw=1.7, label="HFALL_AFTER_RISE")
        axes[2].plot(t, data[f"{variant}_hrise_after_fall"], color="#2ca02c", lw=1.7, label="HRISE_AFTER_FALL")
        if f"{variant}_hchgunsettled" in data:
            axes[2].plot(t, data[f"{variant}_hchgunsettled"], color="#7f7f7f", lw=1.4, label="HCHGUNSETTLED")
        axes[2].set_ylim(-0.1, 1.12)
        base.style(axes[2], "Detect/latch")
        axes[2].legend(loc="best", ncol=4)
        axes[2].set_xlabel("Time (ns)")
        axes[2].set_xlim(*xlim)
        fig.suptitle(f"{case_id}: {variant} charge-state diagnostics")
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(FIGURES_DIR / f"{case_id}_03_{variant}_charge_diagnostics.png", dpi=180)
        plt.close(fig)


def plot_high_low_comparison() -> None:
    high = read_waveforms("short_pulse_1ns_high")
    low = read_waveforms("short_pulse_1ns_low")
    fig, axes = plt.subplots(2, 2, figsize=(12.2, 7.6), sharex=False)
    for ax, case_id, data, coeff in [
        (axes[0, 0], "short_pulse_1ns_high", high, "ku"),
        (axes[0, 1], "short_pulse_1ns_low", low, "ku"),
        (axes[1, 0], "short_pulse_1ns_high", high, "kd"),
        (axes[1, 1], "short_pulse_1ns_low", low, "kd"),
    ]:
        case = base.case_by_id(case_id)
        base.mark_commands(ax, case)
        t = data["time_ns"]
        for key, label in [
            ("hspice", "HSPICE"),
            ("legacy", "legacy"),
            ("dir_hybrid", "Directional"),
            ("charge_hybrid", "ChargeLimited"),
            ("charge_fast", "FastRecover"),
        ]:
            ax.plot(t, data[f"{key}_{coeff}"], color=COLORS[key], lw=1.8, label=label)
        x0, x1 = base.command_times(case)
        ax.set_xlim(max(0.0, x0 - 0.75), min(case.stop_ns, x1 + 5.0))
        base.style(ax, coeff.upper())
        ax.set_title(case_id)
    axes[1, 0].set_xlabel("Time (ns)")
    axes[1, 1].set_xlabel("Time (ns)")
    axes[0, 1].legend(loc="best", ncol=2)
    fig.suptitle("Charge-limited check: short high pulse vs mirrored short low pulse")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / "high_vs_low_pulse_comparison.png", dpi=180)
    plt.close(fig)


def plot_summary_bars(rows: list[dict[str, object]]) -> None:
    short_ids = [case_id for case_id in REQUIRED_CASE_IDS if case_id.startswith("short_")]
    metrics = [
        ("pad_active_rmse_v", "Pad RMSE (mV)", 1e3),
        ("ku_active_rmse", "Ku RMSE", 1.0),
        ("kd_active_rmse", "Kd RMSE", 1.0),
        ("ku_peak", "Ku peak", 1.0),
        ("kd_min", "Kd minimum", 1.0),
        ("kd_recovery_delta_ns", "Kd recovery delta (ns)", 1.0),
        ("overlap_energy_ns", "Ku*Kd overlap (ns)", 1.0),
    ]
    variants = [
        ("legacy", "legacy", COLORS["legacy"]),
        ("gate_hybrid", "GateState", COLORS["gate_hybrid"]),
        ("dir_hybrid", "Directional", COLORS["dir_hybrid"]),
        ("charge_hybrid", "ChargeLimited", COLORS["charge_hybrid"]),
        ("charge_fast", "FastRecover", COLORS["charge_fast"]),
    ]
    row_lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    fig, axes = plt.subplots(len(metrics), 1, figsize=(14.2, 16.5), sharex=True)
    x = np.arange(len(short_ids))
    width = 0.16
    offsets = np.linspace(-2, 2, len(variants)) * width
    for ax, (metric, ylabel, scale) in zip(axes, metrics):
        for offset, (variant, label, color) in zip(offsets, variants):
            values = []
            for case_id in short_ids:
                value = row_lookup.get((case_id, variant), {}).get(metric, "")
                try:
                    values.append(float(value) * scale)
                except (TypeError, ValueError):
                    values.append(np.nan)
            ax.bar(x + offset, values, width=width, color=color, alpha=0.88, label=label)
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", alpha=0.28)
    axes[0].legend(loc="best", ncol=5)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(["500ps high", "1ns high", "2ns high", "500ps low", "1ns low", "2ns low"], rotation=25, ha="right")
    axes[-1].set_xlabel("Interrupted pulse case")
    fig.suptitle("Charge-limited interrupted-pulse summary")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(FIGURES_DIR / "short_pulse_summary_bars.png", dpi=180)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]]) -> None:
    lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    control_legacy = lookup.get((CONTROL_CASE, "legacy"), {})
    control_charge = lookup.get((CONTROL_CASE, "charge_hybrid"), {})
    control_pad_delta_mv = (
        (float(control_charge["pad_active_rmse_v"]) - float(control_legacy["pad_active_rmse_v"])) * 1e3
        if control_legacy and control_charge
        else float("nan")
    )
    control_coeff_delta = (
        max(float(control_charge["ku_active_rmse"]), float(control_charge["kd_active_rmse"]))
        - max(float(control_legacy["ku_active_rmse"]), float(control_legacy["kd_active_rmse"]))
        if control_legacy and control_charge
        else float("nan")
    )

    short_ids = [case_id for case_id in REQUIRED_CASE_IDS if case_id.startswith("short_")]
    improved_vs_legacy = 0
    improved_vs_dir = 0
    no_overcancel = 0
    low_detector = 0
    for case_id in short_ids:
        charge = lookup.get((case_id, "charge_hybrid"), {})
        legacy = lookup.get((case_id, "legacy"), {})
        directional = lookup.get((case_id, "dir_hybrid"), {})
        if not charge or not legacy:
            continue
        if (
            float(charge["pad_active_rmse_v"]) < float(legacy["pad_active_rmse_v"])
            and float(charge["ku_active_rmse"]) < float(legacy["ku_active_rmse"])
            and float(charge["kd_active_rmse"]) < float(legacy["kd_active_rmse"])
        ):
            improved_vs_legacy += 1
        if directional and float(charge["kd_active_rmse"]) < float(directional["kd_active_rmse"]):
            improved_vs_dir += 1
        qpu_ok = str(charge.get("qpu_overcancel", "")) in {"False", "false", "0", ""}
        qpd_ok = str(charge.get("qpd_overcancel", "")) in {"False", "false", "0", ""}
        if qpu_ok and qpd_ok:
            no_overcancel += 1
        if case_id.endswith("_low") and float(charge.get("hrise_after_fall_active_count", 0) or 0) > 0:
            low_detector += 1

    h_data = base.parse_hspice_tr0(CASES_DIR / DEMO_CASE / "hspice_native_ibis" / f"{DEMO_CASE}_hspice_native_ibis.tr0")
    h_t = base.to_ns(base.find_signal(h_data, "time"))
    h_mask = base.active_mask(h_t, base.case_by_id(DEMO_CASE))
    h_ku_peak = float(np.max(base.find_signal(h_data, "v(ku)")[h_mask]))
    h_pad_peak = float(np.max(base.find_signal(h_data, "v(pad_ibis)")[h_mask]))

    def row_num(case_id: str, variant: str, key: str) -> float:
        return float(lookup[(case_id, variant)][key])

    lines = [
        "# io_buf Charge-Limited Gate-State pybis Retrigger Study",
        "",
        "This study tests `InputDrivenChargeLimitedGateHybrid`, which replaces additive directional event taps with bounded pullup/pulldown charge states `QPU` and `QPD`.",
        "",
        "## Headline",
        "",
        f"- Long-pulse control pad RMSE delta versus legacy: `{control_pad_delta_mv:.3f} mV`.",
        f"- Long-pulse control max Ku/Kd RMSE delta versus legacy: `{control_coeff_delta:.5f}`.",
        f"- ChargeLimitedHybrid coefficient-first improvements versus legacy: `{improved_vs_legacy}` / `{len(short_ids)}` interrupted cases.",
        f"- ChargeLimitedHybrid Kd RMSE improvements versus DirectionalHybrid: `{improved_vs_dir}` / `{len(short_ids)}` interrupted cases.",
        f"- Charge-state over-cancel checks passed: `{no_overcancel}` / `{len(short_ids)}` interrupted cases.",
        f"- Short-low `HRISE_AFTER_FALL` activations: `{low_detector}` / `3` mirrored low-pulse cases.",
        "- Primary `ChargeLimitedHybrid` uses the charge path for fall-after-rise short-high pulses only; `HRISE_AFTER_FALL` is reported as a diagnostic because enabling it in the primary hybrid regressed the long-pulse control.",
        "- `ChargeLimitedFastRecover` keeps the mirrored-low path active as an experimental comparison; `ChargeLimitedFull` shows the bounded charge model itself can improve Kd, but with pad/Ku tradeoffs.",
        "- `double_toggle_1ps` remains a stress failure for primary `ChargeLimitedHybrid`; this mode is not default-ready.",
        "- `InputDrivenChargeLimitedGateFull` is diagnostic only and is not considered for default behavior.",
        "- HSPICE is used only for validation; all charge-limited timing comes from IBIS/pybis coefficient tables.",
        "",
        "## short_pulse_1ns_high Specific Numbers",
        "",
        f"- HSPICE Ku peak: `{h_ku_peak:.4f}`",
        f"- legacy Ku peak: `{row_num(DEMO_CASE, 'legacy', 'ku_peak'):.4f}`",
        f"- GateStateHybrid Ku peak: `{row_num(DEMO_CASE, 'gate_hybrid', 'ku_peak'):.4f}`",
        f"- DirectionalHybrid Ku peak: `{row_num(DEMO_CASE, 'dir_hybrid', 'ku_peak'):.4f}`",
        f"- ChargeLimitedHybrid Ku peak: `{row_num(DEMO_CASE, 'charge_hybrid', 'ku_peak'):.4f}`",
        f"- ChargeLimitedFastRecover Ku peak: `{row_num(DEMO_CASE, 'charge_fast', 'ku_peak'):.4f}`",
        f"- HSPICE pad peak: `{h_pad_peak:.4f} V`",
        f"- legacy pad peak: `{row_num(DEMO_CASE, 'legacy', 'pad_peak_v'):.4f} V`",
        f"- GateStateHybrid pad peak: `{row_num(DEMO_CASE, 'gate_hybrid', 'pad_peak_v'):.4f} V`",
        f"- DirectionalHybrid pad peak: `{row_num(DEMO_CASE, 'dir_hybrid', 'pad_peak_v'):.4f} V`",
        f"- ChargeLimitedHybrid pad peak: `{row_num(DEMO_CASE, 'charge_hybrid', 'pad_peak_v'):.4f} V`",
        "",
        "## How To Read The Figures",
        "",
        "- `*_01_input_pad_overlay.png`: input command and pad waveform, HSPICE vs each ngspice pybis mode.",
        "- `*_02_ku_only.png`: Ku coefficient overlay only.",
        "- `*_02_kd_only.png`: Kd coefficient overlay only.",
        "- `*_03_charge_hybrid_charge_diagnostics.png`: QPU/QPD states, charge-mapped coefficients, and detector/latch activity.",
        "- `high_vs_low_pulse_comparison.png`: mirrored 1 ns short-high vs short-low behavior.",
        "- `short_pulse_summary_bars.png`: summary metrics beyond RMSE, including peaks, recovery, and overlap.",
        "",
        "## Output Files",
        "",
        "- `candidate_metrics.csv`: detailed per-case/per-variant metrics.",
        "- `metrics_by_case.csv`: compact case comparison.",
        "- `interrupted_switching_demo/demo_metrics.csv`: short-pulse-focused metrics.",
        "",
    ]
    base.write_text(OUT_DIR / "README.md", "\n".join(lines))
    base.write_text(DEMO_DIR / "README.md", "\n".join(lines))


def generate_report(rows: list[dict[str, object]]) -> None:
    base.write_wide_metrics(rows)
    base.write_demo_metrics(rows)
    available_cases = sorted({str(r.get("case_id")) for r in rows if r.get("variant") != "case_error"})
    for case_id in available_cases:
        if case_id == CONTROL_CASE:
            continue
        try:
            plot_main_case(case_id)
        except FileNotFoundError:
            continue
    if {"short_pulse_1ns_high", "short_pulse_1ns_low"}.issubset(set(available_cases)):
        plot_high_low_comparison()
    plot_summary_bars(rows)
    if CONTROL_CASE in available_cases and DEMO_CASE in available_cases:
        write_readme(rows)
    else:
        lines = [
            "# io_buf Charge-Limited Gate-State pybis Retrigger Study",
            "",
            "Partial run. Complete the required cases to generate the full findings README.",
            "",
            f"Available cases: `{', '.join(available_cases)}`",
            "",
        ]
        base.write_text(OUT_DIR / "README.md", "\n".join(lines))
        base.write_text(DEMO_DIR / "README.md", "\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Charge-limited gate-state pybis retrigger study.")
    parser.add_argument("--ngspice", type=Path, default=base.DEFAULT_NGSPICE)
    parser.add_argument("--ibis", type=Path, default=base.DEFAULT_IBIS)
    parser.add_argument("--case", action="append", default=[], help="Run only this case_id. May be repeated.")
    parser.add_argument("--resume", action="store_true", help="Skip completed case/variant rows.")
    parser.add_argument("--summarize-only", action="store_true", help="Regenerate plots/report from candidate_metrics.csv.")
    parser.add_argument("--timeout-s", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    install_globals()
    args = parse_args()
    for path in [OUT_DIR, COMMON_DIR, CASES_DIR, DEMO_DIR, FIGURES_DIR]:
        base.ensure_dir(path)

    if args.summarize_only:
        rows = [r for r in base.read_csv(OUT_DIR / "candidate_metrics.csv") if r.get("variant") != "case_error"]
        base.generate_report(rows)
        print(f"OUT_DIR={OUT_DIR}")
        print(f"DEMO={DEMO_DIR / 'README.md'}")
        return 0

    model_paths = base.prepare_common(args.ibis)
    cases = base.selected_cases(args.case)
    existing_rows = base.read_csv(OUT_DIR / "candidate_metrics.csv") if args.resume else []
    done = {(str(r.get("case_id")), str(r.get("variant"))) for r in existing_rows}
    rows = list(existing_rows)
    case_order = [case.case_id for case in base.selected_cases([])]
    order = {(case_id, variant.variant_id): (i, j) for i, case_id in enumerate(case_order) for j, variant in enumerate(VARIANTS)}

    for idx, case in enumerate(cases, start=1):
        if args.resume and all((case.case_id, variant.variant_id) in done for variant in VARIANTS):
            print(f"[{idx}/{len(cases)}] {case.case_id} (resume skip)", flush=True)
            continue
        print(f"[{idx}/{len(cases)}] {case.case_id}", flush=True)
        rows = [r for r in rows if str(r.get("case_id")) != case.case_id]
        try:
            rows.extend(base.run_case(case, args.ngspice, args.ibis, model_paths, args.timeout_s))
        except Exception as exc:
            rows.append({"case_id": case.case_id, "variant": "case_error", "status": "failed", "error": str(exc)})
        rows.sort(key=lambda r: order.get((str(r.get("case_id")), str(r.get("variant"))), (9999, 9999)))
        base.write_csv(OUT_DIR / "candidate_metrics.csv", rows)

    ok_rows = [r for r in rows if r.get("variant") != "case_error"]
    base.generate_report(ok_rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"DEMO={DEMO_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
