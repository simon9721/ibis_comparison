import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import run_io_buf_charge_limited_gate_retrigger as charge


base = charge.base
ROOT = charge.ROOT
OUT_DIR = ROOT / "results" / "io_buf_value_matched_replay_2026-06-23"
COMMON_DIR = OUT_DIR / "common"
CASES_DIR = OUT_DIR / "cases"
DEMO_DIR = OUT_DIR / "interrupted_switching_demo"
FIGURES_DIR = DEMO_DIR / "figures"

REQUIRED_CASE_IDS = charge.REQUIRED_CASE_IDS
CONTROL_CASE = charge.CONTROL_CASE
DEMO_CASE = charge.DEMO_CASE

COLORS = {
    "hspice": "#1f77b4",
    "legacy": "#ff7f0e",
    "gate_hybrid": "#d62728",
    "charge_hybrid": "#6f2dbd",
    "vm_hybrid": "#2ca02c",
    "vm_full": "#17becf",
    "vm_ku": "#bcbd22",
    "vm_kd": "#8c564b",
    "input": "#222222",
    "diag": "#7f7f7f",
}

VARIANTS = [
    base.Variant("legacy", "legacy pybis", "InputDriven"),
    base.Variant("gate_hybrid", "GateStateHybrid", "InputDrivenGateStateHybrid", save_diagnostics=True),
    base.Variant(
        "charge_hybrid",
        "ChargeLimitedGateHybrid",
        "InputDrivenChargeLimitedGateHybrid",
        save_diagnostics=True,
    ),
    base.Variant(
        "vm_hybrid",
        "ValueMatchedReplayHybrid",
        "InputDrivenValueMatchedReplayHybrid",
        save_diagnostics=True,
    ),
    base.Variant(
        "vm_full",
        "ValueMatchedReplayFull diagnostic",
        "InputDrivenValueMatchedReplayFull",
        save_diagnostics=True,
        include_main_plots=False,
    ),
    base.Variant(
        "vm_ku",
        "ValueMatchedReplayKuOnly diagnostic",
        "InputDrivenValueMatchedReplayKuOnly",
        save_diagnostics=True,
        include_main_plots=False,
    ),
    base.Variant(
        "vm_kd",
        "ValueMatchedReplayKdOnly diagnostic",
        "InputDrivenValueMatchedReplayKdOnly",
        save_diagnostics=True,
        include_main_plots=False,
    ),
]

DIAGNOSTIC_TIMEOUT_S = {
    "vm_full": 30,
}


def install_globals() -> None:
    for module in [charge, base]:
        module.OUT_DIR = OUT_DIR
        module.COMMON_DIR = COMMON_DIR
        module.CASES_DIR = CASES_DIR
        module.DEMO_DIR = DEMO_DIR
        module.FIGURES_DIR = FIGURES_DIR
        module.REQUIRED_CASE_IDS = REQUIRED_CASE_IDS
        module.CONTROL_CASE = CONTROL_CASE
        module.DEMO_CASE = DEMO_CASE
        module.COLORS = COLORS
        module.VARIANTS = VARIANTS
    base.build_cases = charge.build_cases
    base.build_pwl_points = charge.build_pwl_points
    base.make_ngspice_deck = make_ngspice_deck
    base.score_variant = score_variant
    base.read_waveforms = read_waveforms
    base.plot_main_case = plot_main_case
    base.plot_high_low_comparison = plot_high_low_comparison
    base.plot_summary_bars = plot_summary_bars
    base.write_readme = write_readme
    base.generate_report = generate_report
    base.run_case = run_case


def cleanup_failed_raw(case: base.StudyCase, variant: base.Variant) -> None:
    raw = (
        CASES_DIR
        / case.case_id
        / f"ngspice_{variant.variant_id}"
        / f"{case.case_id}_ngspice_{variant.variant_id}.raw"
    )
    if raw.exists():
        raw.unlink()


def run_case(
    case: base.StudyCase,
    ngspice: Path,
    ibis_path: Path,
    model_paths: dict[str, Path],
    timeout_s: int,
) -> list[dict[str, object]]:
    h_data, h_deck = base.run_hspice_case(case, ibis_path, timeout_s)
    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        variant_timeout = min(timeout_s, DIAGNOSTIC_TIMEOUT_S.get(variant.variant_id, timeout_s))
        try:
            n_data, n_deck, raw = base.run_ngspice_variant(
                case,
                variant,
                model_paths[variant.variant_id],
                ngspice,
                variant_timeout,
            )
            rows.append(score_variant(case, variant, h_data, n_data, h_deck, n_deck, raw))
        except Exception as exc:
            cleanup_failed_raw(case, variant)
            rows.append(
                {
                    "case_id": case.case_id,
                    "description": case.description,
                    "pattern": case.pattern,
                    "pulse_width_ns": case.pulse_width_ns if case.pattern.startswith("short_") else "",
                    "variant": variant.variant_id,
                    "variant_label": variant.label,
                    "status": "failed",
                    "error": str(exc),
                    "hspice_deck": str(h_deck.relative_to(ROOT)),
                }
            )
    return rows


def make_ngspice_deck(case: base.StudyCase, variant: base.Variant) -> str:
    extra = ""
    if variant.save_diagnostics:
        extra = (
            " V(xdrv.kutarget) V(xdrv.kdtarget)"
            " V(xdrv.kuleg) V(xdrv.kdleg)"
            " V(xdrv.kusamp) V(xdrv.kdsamp)"
            " V(xdrv.tr_ku) V(xdrv.tr_kd) V(xdrv.tf_ku) V(xdrv.tf_kd)"
            " V(xdrv.tr_start) V(xdrv.tf_start) V(xdrv.vmstart) V(xdrv.vmarg)"
            " V(xdrv.match_err_ku) V(xdrv.match_err_kd)"
            " V(xdrv.start_disagree) V(xdrv.match_ambiguous) V(xdrv.hvmatch)"
            " V(xdrv.kumatch) V(xdrv.kdmatch)"
            " V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)"
            " V(xdrv.qpu) V(xdrv.qpd) V(xdrv.kuchg) V(xdrv.kdchg)"
        )
    return f"""* io_buf {variant.label}/ngspice value-matched replay extraction
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


def optional(data: dict[str, np.ndarray], nt: np.ndarray, t: np.ndarray, name: str) -> np.ndarray | None:
    return base.optional_signal(data, nt, t, f"v(xdrv.{name})", f"v(xdrv:{name})")


def active_interval(t: np.ndarray, y: np.ndarray, mask: np.ndarray, threshold: float = 0.5) -> tuple[float, float, int]:
    active = mask & (y > threshold)
    if np.count_nonzero(active) == 0:
        return float("nan"), float("nan"), 0
    return float(t[active][0]), float(t[active][-1]), int(np.count_nonzero(active))


def score_variant(
    case: base.StudyCase,
    variant: base.Variant,
    h_data: dict[str, np.ndarray],
    n_data: dict[str, np.ndarray],
    hspice_deck: Path,
    ngspice_deck: Path,
    raw_path: Path,
) -> dict[str, object]:
    row = charge.BASE_SCORE_VARIANT(case, variant, h_data, n_data, hspice_deck, ngspice_deck, raw_path)
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
            "pad_peak_v": float(np.max(n_pad[mask])) if np.count_nonzero(mask) else "",
            "pad_min_v": float(np.min(n_pad[mask])) if np.count_nonzero(mask) else "",
            "hspice_pad_peak_v": float(np.max(h_pad[mask])) if np.count_nonzero(mask) else "",
            "hspice_pad_min_v": float(np.min(h_pad[mask])) if np.count_nonzero(mask) else "",
            "ku_min": float(np.min(n_ku[mask])) if np.count_nonzero(mask) else "",
            "kd_max": float(np.max(n_kd[mask])) if np.count_nonzero(mask) else "",
            "pad_worst_error_time_ns": charge.time_of_worst_error(h_t, h_pad, n_pad, mask),
            "ku_worst_error_time_ns": charge.time_of_worst_error(h_t, h_ku, n_ku, mask),
            "kd_worst_error_time_ns": charge.time_of_worst_error(h_t, h_kd, n_kd, mask),
        }
    )
    for name in [
        "kusamp",
        "kdsamp",
        "tr_ku",
        "tr_kd",
        "tf_ku",
        "tf_kd",
        "tr_start",
        "tf_start",
        "vmstart",
        "vmarg",
        "match_err_ku",
        "match_err_kd",
        "start_disagree",
        "match_ambiguous",
        "hvmatch",
        "kumatch",
        "kdmatch",
        "qpu",
        "qpd",
        "kuchg",
        "kdchg",
    ]:
        sig = optional(n_data, n_t, h_t, name)
        if sig is None:
            row[f"{name}_min"] = ""
            row[f"{name}_max"] = ""
            continue
        row[f"{name}_min"] = float(np.min(sig[mask])) if np.count_nonzero(mask) else ""
        row[f"{name}_max"] = float(np.max(sig[mask])) if np.count_nonzero(mask) else ""
        if name in {"hvmatch", "match_ambiguous"}:
            start, end, count = active_interval(h_t, sig, mask)
            row[f"{name}_active_start_ns"] = start
            row[f"{name}_active_end_ns"] = end
            row[f"{name}_active_count"] = count
    return row


def read_waveforms(case_id: str) -> dict[str, np.ndarray]:
    data = charge.BASE_READ_WAVEFORMS(case_id)
    t = data["time_ns"]
    case_dir = CASES_DIR / case_id
    for variant in VARIANTS:
        path = case_dir / f"ngspice_{variant.variant_id}" / f"{case_id}_ngspice_{variant.variant_id}.raw"
        if not path.exists():
            continue
        raw = base.parse_ngspice_raw(path)
        nt = base.to_ns(base.find_signal(raw, "time"))
        for name in [
            "kutarget",
            "kdtarget",
            "kuleg",
            "kdleg",
            "kusamp",
            "kdsamp",
            "tr_ku",
            "tr_kd",
            "tf_ku",
            "tf_kd",
            "tr_start",
            "tf_start",
            "vmstart",
            "vmarg",
            "match_err_ku",
            "match_err_kd",
            "start_disagree",
            "match_ambiguous",
            "hvmatch",
            "kumatch",
            "kdmatch",
            "qpu",
            "qpd",
            "kuchg",
            "kdchg",
        ]:
            sig = optional(raw, nt, t, name)
            if sig is not None:
                data[f"{variant.variant_id}_{name}"] = sig
    return data


def main_flows() -> list[tuple[str, str]]:
    return [
        ("hspice", "HSPICE native IBIS"),
        ("legacy", "legacy pybis"),
        ("gate_hybrid", "GateStateHybrid"),
        ("charge_hybrid", "ChargeLimitedHybrid"),
        ("vm_hybrid", "ValueMatchedHybrid"),
        ("vm_full", "ValueMatchedFull"),
    ]


def mark(ax, case: base.StudyCase) -> None:
    base.mark_commands(ax, case)


def plot_main_case(case_id: str) -> None:
    base.ensure_dir(FIGURES_DIR)
    case = base.case_by_id(case_id)
    data = read_waveforms(case_id)
    t = data["time_ns"]
    x0, x1 = base.command_times(case)
    xlim = (max(0.0, x0 - 0.75), min(case.stop_ns, x1 + 5.0))

    fig, axes = plt.subplots(2, 1, figsize=(11.4, 6.8), sharex=True, height_ratios=[0.72, 1.35])
    for ax in axes:
        mark(ax, case)
    axes[0].plot(t, base.input_waveform(case, t), color=COLORS["input"], lw=2.2, label="input")
    base.style(axes[0], "Input (V)")
    axes[0].legend(loc="upper right")
    for key, label in main_flows():
        if f"{key}_pad" in data:
            axes[1].plot(t, data[f"{key}_pad"], color=COLORS[key], lw=1.8, label=label)
    base.style(axes[1], "Pad (V)")
    axes[1].set_xlim(*xlim)
    axes[1].set_xlabel("Time (ns)")
    axes[1].legend(loc="best", ncol=2)
    fig.suptitle(f"{case_id}: input and pad overlay")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / f"{case_id}_01_input_pad_overlay.png", dpi=180)
    plt.close(fig)

    for coeff in ["ku", "kd"]:
        fig, ax = plt.subplots(figsize=(11.4, 4.5))
        mark(ax, case)
        for key, label in main_flows():
            if f"{key}_{coeff}" in data:
                ax.plot(t, data[f"{key}_{coeff}"], color=COLORS[key], lw=1.8, label=f"{label} {coeff.upper()}")
        ax.set_ylim(-0.14, 1.18)
        ax.set_xlim(*xlim)
        base.style(ax, coeff.upper())
        ax.set_xlabel("Time (ns)")
        ax.legend(loc="best", ncol=2)
        fig.suptitle(f"{case_id}: {coeff.upper()} only")
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        fig.savefig(FIGURES_DIR / f"{case_id}_02_{coeff}_only.png", dpi=180)
        plt.close(fig)

    for variant in ["vm_hybrid", "vm_full", "vm_ku", "vm_kd"]:
        if f"{variant}_vmstart" not in data:
            continue
        fig, axes = plt.subplots(3, 1, figsize=(11.4, 9.2), sharex=True)
        for ax in axes:
            mark(ax, case)
        axes[0].plot(t, data[f"{variant}_kusamp"], color="#2ca02c", lw=1.8, label="KUSAMP")
        axes[0].plot(t, data[f"{variant}_kdsamp"], color="#17becf", lw=1.8, label="KDSAMP")
        axes[0].plot(t, data[f"{variant}_kumatch"], color="#98df8a", lw=1.4, label="KUMATCH")
        axes[0].plot(t, data[f"{variant}_kdmatch"], color="#9edae5", lw=1.4, label="KDMATCH")
        axes[0].set_ylim(-0.14, 1.18)
        base.style(axes[0], "Coeff value")
        axes[0].legend(loc="best", ncol=4)
        axes[1].plot(t, data[f"{variant}_tr_ku"], color="#2ca02c", lw=1.5, label="TR_KU")
        axes[1].plot(t, data[f"{variant}_tr_kd"], color="#17becf", lw=1.5, label="TR_KD")
        axes[1].plot(t, data[f"{variant}_tf_ku"], color="#d62728", lw=1.5, label="TF_KU")
        axes[1].plot(t, data[f"{variant}_tf_kd"], color="#9467bd", lw=1.5, label="TF_KD")
        axes[1].plot(t, data[f"{variant}_vmstart"], color=COLORS[variant], lw=2.0, label="VMSTART")
        base.style(axes[1], "Replay start (ns)")
        axes[1].legend(loc="best", ncol=5)
        axes[2].plot(t, data[f"{variant}_hvmatch"], color=COLORS[variant], lw=2.0, label="HVMATCH")
        axes[2].plot(t, data[f"{variant}_start_disagree"], color="#7f7f7f", lw=1.5, label="START_DISAGREE ns")
        axes[2].plot(t, data[f"{variant}_match_ambiguous"], color="#bcbd22", lw=1.5, label="MATCH_AMBIGUOUS")
        axes[2].plot(t, data[f"{variant}_match_err_ku"], color="#2ca02c", lw=1.2, label="MATCH_ERR_KU")
        axes[2].plot(t, data[f"{variant}_match_err_kd"], color="#17becf", lw=1.2, label="MATCH_ERR_KD")
        base.style(axes[2], "Active / errors")
        axes[2].legend(loc="best", ncol=3)
        axes[2].set_xlabel("Time (ns)")
        axes[2].set_xlim(*xlim)
        fig.suptitle(f"{case_id}: {variant} value-match diagnostics")
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(FIGURES_DIR / f"{case_id}_03_{variant}_value_match_diagnostics.png", dpi=180)
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
        mark(ax, case)
        t = data["time_ns"]
        for key, label in [
            ("hspice", "HSPICE"),
            ("legacy", "legacy"),
            ("charge_hybrid", "ChargeLimited"),
            ("vm_hybrid", "ValueMatched"),
            ("vm_full", "VM Full"),
        ]:
            if f"{key}_{coeff}" in data:
                ax.plot(t, data[f"{key}_{coeff}"], color=COLORS[key], lw=1.8, label=label)
        x0, x1 = base.command_times(case)
        ax.set_xlim(max(0.0, x0 - 0.75), min(case.stop_ns, x1 + 5.0))
        base.style(ax, coeff.upper())
        ax.set_title(case_id)
    axes[1, 0].set_xlabel("Time (ns)")
    axes[1, 1].set_xlabel("Time (ns)")
    axes[0, 1].legend(loc="best", ncol=2)
    fig.suptitle("Value-matched replay: short high vs mirrored short low")
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
        ("start_disagree_max", "Start disagree max (ns)", 1.0),
        ("match_ambiguous_active_count", "Ambiguous samples", 1.0),
    ]
    variants = [
        ("legacy", "legacy", COLORS["legacy"]),
        ("charge_hybrid", "ChargeLimited", COLORS["charge_hybrid"]),
        ("vm_hybrid", "VM Hybrid", COLORS["vm_hybrid"]),
        ("vm_full", "VM Full", COLORS["vm_full"]),
    ]
    row_lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    fig, axes = plt.subplots(len(metrics), 1, figsize=(14.2, 16.5), sharex=True)
    x = np.arange(len(short_ids))
    width = 0.19
    offsets = np.linspace(-1.5, 1.5, len(variants)) * width
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
    axes[0].legend(loc="best", ncol=4)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(["500ps high", "1ns high", "2ns high", "500ps low", "1ns low", "2ns low"], rotation=25, ha="right")
    axes[-1].set_xlabel("Interrupted pulse case")
    fig.suptitle("Value-matched replay interrupted-pulse summary")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(FIGURES_DIR / "short_pulse_summary_bars.png", dpi=180)
    plt.close(fig)


def write_wide_metrics(rows: list[dict[str, object]]) -> None:
    by_case: dict[str, dict[str, object]] = {}
    keys = [
        "pad_active_rmse_v",
        "ku_active_rmse",
        "kd_active_rmse",
        "ku_peak",
        "kd_min",
        "vmstart_max",
        "start_disagree_max",
        "match_ambiguous_active_count",
        "hvmatch_active_count",
        "status",
    ]
    for row in rows:
        case_id = str(row["case_id"])
        variant = str(row["variant"])
        out = by_case.setdefault(
            case_id,
            {
                "case_id": case_id,
                "description": row.get("description", ""),
                "pattern": row.get("pattern", ""),
                "pulse_width_ns": row.get("pulse_width_ns", ""),
            },
        )
        for key in keys:
            out[f"{variant}_{key}"] = row.get(key, "")
    ordered = [by_case[case_id] for case_id in REQUIRED_CASE_IDS if case_id in by_case]
    base.write_csv(OUT_DIR / "metrics_by_case.csv", ordered)


def write_demo_metrics(rows: list[dict[str, object]]) -> None:
    base.write_csv(DEMO_DIR / "demo_metrics.csv", [r for r in rows if str(r.get("case_id", "")).startswith("short_")])


def write_readme(rows: list[dict[str, object]]) -> None:
    lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}

    def safe_float(value: object) -> float:
        try:
            if value == "":
                return float("nan")
            return float(value)
        except (TypeError, ValueError):
            return float("nan")

    def fmt_num(value: float, fmt: str) -> str:
        return "n/a" if not np.isfinite(value) else format(value, fmt)

    def row_num(case_id: str, variant: str, key: str) -> float:
        return safe_float(lookup.get((case_id, variant), {}).get(key, ""))

    control_legacy = lookup.get((CONTROL_CASE, "legacy"), {})
    control_vm = lookup.get((CONTROL_CASE, "vm_hybrid"), {})
    control_pad_delta_mv = (row_num(CONTROL_CASE, "vm_hybrid", "pad_active_rmse_v") - row_num(CONTROL_CASE, "legacy", "pad_active_rmse_v")) * 1e3
    control_vm_coeff = max(row_num(CONTROL_CASE, "vm_hybrid", "ku_active_rmse"), row_num(CONTROL_CASE, "vm_hybrid", "kd_active_rmse"))
    control_legacy_coeff = max(row_num(CONTROL_CASE, "legacy", "ku_active_rmse"), row_num(CONTROL_CASE, "legacy", "kd_active_rmse"))
    control_coeff_delta = control_vm_coeff - control_legacy_coeff
    short_ids = [case_id for case_id in REQUIRED_CASE_IDS if case_id.startswith("short_")]
    improved_vs_legacy = 0
    ambiguous = 0
    for case_id in short_ids:
        vm = lookup.get((case_id, "vm_hybrid"), {})
        legacy = lookup.get((case_id, "legacy"), {})
        if not vm or not legacy:
            continue
        vm_pad = safe_float(vm.get("pad_active_rmse_v", ""))
        vm_ku = safe_float(vm.get("ku_active_rmse", ""))
        vm_kd = safe_float(vm.get("kd_active_rmse", ""))
        legacy_pad = safe_float(legacy.get("pad_active_rmse_v", ""))
        legacy_ku = safe_float(legacy.get("ku_active_rmse", ""))
        legacy_kd = safe_float(legacy.get("kd_active_rmse", ""))
        if (
            np.isfinite(vm_pad)
            and np.isfinite(vm_ku)
            and np.isfinite(vm_kd)
            and vm_pad < legacy_pad
            and vm_ku < legacy_ku
            and vm_kd < legacy_kd
        ):
            improved_vs_legacy += 1
        if safe_float(vm.get("match_ambiguous_active_count", 0)) > 0:
            ambiguous += 1

    def status_counts(variant: str) -> str:
        counts: dict[str, int] = {}
        for row in rows:
            if str(row.get("variant", "")) != variant:
                continue
            status = str(row.get("status", "") or "blank")
            counts[status] = counts.get(status, 0) + 1
        order = ["GOOD", "CHECK", "WARN", "failed", "blank"]
        parts = [f"{key}={counts[key]}" for key in order if key in counts]
        parts.extend(f"{key}={value}" for key, value in sorted(counts.items()) if key not in order)
        return ", ".join(parts) if parts else "no rows"

    control_vm_status = str(control_vm.get("status", "missing") if control_vm else "missing")
    control_vm_error = str(control_vm.get("error", "") if control_vm else "")

    h_data = base.parse_hspice_tr0(CASES_DIR / DEMO_CASE / "hspice_native_ibis" / f"{DEMO_CASE}_hspice_native_ibis.tr0")
    h_t = base.to_ns(base.find_signal(h_data, "time"))
    h_mask = base.active_mask(h_t, base.case_by_id(DEMO_CASE))
    h_ku_peak = float(np.max(base.find_signal(h_data, "v(ku)")[h_mask]))
    h_kd_min = float(np.min(base.find_signal(h_data, "v(kd)")[h_mask]))
    h_pad_peak = float(np.max(base.find_signal(h_data, "v(pad_ibis)")[h_mask]))

    lines = [
        "# io_buf Value-Matched Replay Baseline",
        "",
        "This study tests whether interrupted transitions can be improved by sampling current `Ku/Kd`, mapping those values onto the opposite IBIS coefficient table, and replaying from the inferred table time.",
        "",
        "## Headline",
        "",
        f"- Long-pulse control pad RMSE delta versus legacy: `{fmt_num(control_pad_delta_mv, '.3f')} mV`.",
        f"- Long-pulse control max Ku/Kd RMSE delta versus legacy: `{fmt_num(control_coeff_delta, '.5f')}`.",
        f"- ValueMatchedHybrid coefficient-first improvements versus legacy: `{improved_vs_legacy}` / `{len(short_ids)}` interrupted cases.",
        f"- ValueMatchedHybrid table-retiming ambiguity observed in `{ambiguous}` / `{len(short_ids)}` interrupted cases.",
        f"- ValueMatchedHybrid status across required cases: `{status_counts('vm_hybrid')}`.",
        f"- ValueMatchedFull diagnostic status across required cases: `{status_counts('vm_full')}`.",
        f"- Long-pulse control ValueMatchedHybrid status: `{control_vm_status}`{(' (' + control_vm_error + ')') if control_vm_error else ''}.",
        "- `ValueMatchedReplayFull`, `KuOnly`, and `KdOnly` are diagnostic-only variants.",
        "- HSPICE is validation only; inverse maps and weights come only from IBIS/pybis coefficient tables.",
        "",
        "## Current Interpretation",
        "",
        "- The baseline is implemented and produces the right diagnostic visibility, but value-matched table retiming is not sufficient as a replacement candidate.",
        "- The most important short-high demo still replays almost full `Ku`, so it fails for the same physical reason as legacy pybis.",
        "- Several low-pulse and long-control value-matched variants hit ngspice timeout/stiffness, so the method is not robust enough without additional hidden-state constraints.",
        "- Charge-limited gate-state remains the better current direction for short-high behavior because it limits the available pullup charge instead of just retiming table playback.",
        "",
        "## short_pulse_1ns_high Specific Numbers",
        "",
        f"- HSPICE Ku peak: `{h_ku_peak:.4f}`",
        f"- legacy Ku peak: `{fmt_num(row_num(DEMO_CASE, 'legacy', 'ku_peak'), '.4f')}`",
        f"- ChargeLimitedHybrid Ku peak: `{fmt_num(row_num(DEMO_CASE, 'charge_hybrid', 'ku_peak'), '.4f')}`",
        f"- ValueMatchedHybrid Ku peak: `{fmt_num(row_num(DEMO_CASE, 'vm_hybrid', 'ku_peak'), '.4f')}`",
        f"- HSPICE Kd min: `{h_kd_min:.4f}`",
        f"- legacy Kd min: `{fmt_num(row_num(DEMO_CASE, 'legacy', 'kd_min'), '.4f')}`",
        f"- ValueMatchedHybrid Kd min: `{fmt_num(row_num(DEMO_CASE, 'vm_hybrid', 'kd_min'), '.4f')}`",
        f"- HSPICE pad peak: `{h_pad_peak:.4f} V`",
        f"- legacy pad peak: `{fmt_num(row_num(DEMO_CASE, 'legacy', 'pad_peak_v'), '.4f')} V`",
        f"- ChargeLimitedHybrid pad peak: `{fmt_num(row_num(DEMO_CASE, 'charge_hybrid', 'pad_peak_v'), '.4f')} V`",
        f"- ValueMatchedHybrid pad peak: `{fmt_num(row_num(DEMO_CASE, 'vm_hybrid', 'pad_peak_v'), '.4f')} V`",
        "",
        "## How To Read The Figures",
        "",
        "- `*_01_input_pad_overlay.png`: input command and pad waveform.",
        "- `*_02_ku_only.png` / `*_02_kd_only.png`: coefficient overlays.",
        "- `*_03_vm_*_value_match_diagnostics.png`: sampled values, inferred table times, match errors, and ambiguity.",
        "- `high_vs_low_pulse_comparison.png`: mirrored 1 ns short-high and short-low comparison.",
        "- `short_pulse_summary_bars.png`: RMSE, peak, and ambiguity summary.",
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
    write_wide_metrics(rows)
    write_demo_metrics(rows)
    available_cases = sorted({str(r.get("case_id")) for r in rows if r.get("variant") != "case_error"})
    for case_id in available_cases:
        if case_id == CONTROL_CASE:
            continue
        try:
            plot_main_case(case_id)
        except (FileNotFoundError, KeyError):
            continue
    if {"short_pulse_1ns_high", "short_pulse_1ns_low"}.issubset(set(available_cases)):
        plot_high_low_comparison()
    plot_summary_bars(rows)
    if CONTROL_CASE in available_cases and DEMO_CASE in available_cases:
        write_readme(rows)
    else:
        text = "# io_buf Value-Matched Replay Baseline\n\nPartial run. Complete the required cases for the full report.\n"
        base.write_text(OUT_DIR / "README.md", text)
        base.write_text(DEMO_DIR / "README.md", text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Value-matched pybis replay baseline study.")
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
        generate_report(rows)
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
    generate_report(ok_rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"DEMO={DEMO_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
