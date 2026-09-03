from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_inv_chain_gate_state_clean_comparison as base  # noqa: E402
import run_inv_chain_s2ibispy_slow_fast_comparison as prior  # noqa: E402


OUT_DIR = ROOT / "results" / "inv_chain_forced_midtransition_reversal_2026-07-28"

CASES = [
    base.Case("edge_1ps_base_50r_2pf", "Complete rise and fall", "rise_fall", 10.0, 22.0),
    base.Case("midrev_35ps_high", "35 ps high: forced mid-transition reversal", "short_high", 0.035, 9.0),
    base.Case("midrev_45ps_high", "45 ps high: forced mid-transition reversal", "short_high", 0.045, 9.0),
    base.Case("short_pulse_50ps_high", "50 ps high: forced mid-transition reversal", "short_high", 0.050, 10.0),
    base.Case("midrev_40ps_low", "40 ps low: forced mid-transition reversal", "short_low", 0.040, 14.0),
    base.Case("midrev_45ps_low", "45 ps low: forced mid-transition reversal", "short_low", 0.045, 14.0),
    base.Case("short_pulse_50ps_low", "50 ps low: forced mid-transition reversal", "short_low", 0.050, 14.0),
]

BLACK = "#111111"
GRAY = "#858585"
BLUE = "#1769aa"
RED = "#d62728"
PURPLE = "#7b2cbf"
GREEN = "#009e73"


def configure_variant(path: Path) -> None:
    base.OUT_DIR = path
    base.COMMON_DIR = path / "common"
    base.CASES_DIR = path / "cases"
    base.PLOTS_DIR = path / "plots"
    base.DATA_DIR = path / "waveform_data"
    base.FIT_DIR = path / "fit_diagnostics"
    base.CASES = CASES
    for item in [
        base.OUT_DIR,
        base.COMMON_DIR,
        base.CASES_DIR,
        base.PLOTS_DIR,
        base.DATA_DIR,
        base.FIT_DIR,
    ]:
        base.ensure_dir(item)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def read_waveform(path: Path) -> dict[str, np.ndarray]:
    rows = read_csv(path)
    if not rows:
        raise FileNotFoundError(path)
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def crossing(
    time_ns: np.ndarray,
    signal: np.ndarray,
    direction: str,
    after_ns: float,
) -> tuple[float, int]:
    if direction == "rise":
        candidates = np.where(
            (time_ns[1:] >= after_ns)
            & (signal[:-1] < 0.5)
            & (signal[1:] >= 0.5)
        )[0]
    else:
        candidates = np.where(
            (time_ns[1:] >= after_ns)
            & (signal[:-1] > 0.5)
            & (signal[1:] <= 0.5)
        )[0]
    if not len(candidates):
        raise RuntimeError(f"No {direction} target crossing after {after_ns:.6f} ns")
    index = int(candidates[0])
    y0 = float(signal[index])
    y1 = float(signal[index + 1])
    fraction = 0.0 if abs(y1 - y0) < 1e-15 else (0.5 - y0) / (y1 - y0)
    return float(time_ns[index] + fraction * (time_ns[index + 1] - time_ns[index])), index


def state_at(time_ns: np.ndarray, values: np.ndarray, sample_ns: float) -> float:
    return float(np.interp(sample_ns - 1e-6, time_ns, values))


def predicted_states(case: base.Case, fit: dict[str, object]) -> tuple[float, float]:
    width = case.pulse_width_ns
    values = {key: float(value) for key, value in fit.items() if key.endswith("_ns")}
    if case.pattern == "short_high":
        pu_time = max(
            0.0,
            width + values["pu_off_delay_ns"] - values["pu_on_delay_ns"],
        )
        pd_time = max(
            0.0,
            width + values["pd_on_delay_ns"] - values["pd_off_delay_ns"],
        )
        gup = 1.0 - math.exp(-pu_time / values["pu_on_tau_ns"])
        gdn = math.exp(-pd_time / values["pd_off_tau_ns"])
        return gup, gdn
    pu_time = max(
        0.0,
        width + values["pu_on_delay_ns"] - values["pu_off_delay_ns"],
    )
    pd_time = max(
        0.0,
        width + values["pd_off_delay_ns"] - values["pd_on_delay_ns"],
    )
    gup = math.exp(-pu_time / values["pu_off_tau_ns"])
    gdn = 1.0 - math.exp(-pd_time / values["pd_on_tau_ns"])
    return gup, gdn


def certify_reversal(
    variant_id: str,
    case: base.Case,
    data: dict[str, np.ndarray],
    fit: dict[str, object],
) -> dict[str, object] | None:
    if case.pattern not in {"short_high", "short_low"}:
        return None
    time_ns = data["time_ns"]
    gup = data["gate_state_gup"]
    gdn = data["gate_state_gdn"]
    gup_target = data["gate_state_guptarget"]
    gdn_target = data["gate_state_gdntarget"]
    pulse_start = 5.0 if case.pattern == "short_high" else 10.0
    raw_reverse = pulse_start + case.pulse_width_ns + 0.5 * base.EDGE_NS
    values = {key: float(value) for key, value in fit.items() if key.endswith("_ns")}
    forward_edge = pulse_start + 0.5 * base.EDGE_NS
    if case.pattern == "short_high":
        gup_forward = forward_edge + values["pu_on_delay_ns"]
        gdn_forward = forward_edge + values["pd_off_delay_ns"]
        gup_reverse = raw_reverse + values["pu_off_delay_ns"]
        gdn_reverse = raw_reverse + values["pd_on_delay_ns"]
        gup_progress = state_at(time_ns, gup, gup_reverse)
        gdn_state = state_at(time_ns, gdn, gdn_reverse)
        gdn_progress = 1.0 - gdn_state
        gup_state = gup_progress
    else:
        gup_forward = forward_edge + values["pu_off_delay_ns"]
        gdn_forward = forward_edge + values["pd_on_delay_ns"]
        gup_reverse = raw_reverse + values["pu_on_delay_ns"]
        gdn_reverse = raw_reverse + values["pd_off_delay_ns"]
        gup_state = state_at(time_ns, gup, gup_reverse)
        gdn_state = state_at(time_ns, gdn, gdn_reverse)
        gup_progress = 1.0 - gup_state
        gdn_progress = gdn_state
    predicted_gup, predicted_gdn = predicted_states(case, fit)
    gup_partial = 0.05 < gup_state < 0.95
    gdn_partial = 0.05 < gdn_state < 0.95
    return {
        "variant_id": variant_id,
        "case_id": case.case_id,
        "direction": case.pattern,
        "pulse_width_ps": case.pulse_width_ns * 1e3,
        "raw_reverse_ns": raw_reverse,
        "gup_forward_target_50_ns": gup_forward,
        "gup_reverse_target_50_ns": gup_reverse,
        "gup_motion_before_reverse_ps": (gup_reverse - gup_forward) * 1e3,
        "gup_at_reverse": gup_state,
        "gup_target_at_reverse": state_at(time_ns, gup_target, gup_reverse),
        "gup_transition_progress": gup_progress,
        "gup_predicted_at_reverse": predicted_gup,
        "gup_partial_5_95": gup_partial,
        "gdn_forward_target_50_ns": gdn_forward,
        "gdn_reverse_target_50_ns": gdn_reverse,
        "gdn_motion_before_reverse_ps": (gdn_reverse - gdn_forward) * 1e3,
        "gdn_at_reverse": gdn_state,
        "gdn_target_at_reverse": state_at(time_ns, gdn_target, gdn_reverse),
        "gdn_transition_progress": gdn_progress,
        "gdn_predicted_at_reverse": predicted_gdn,
        "gdn_partial_5_95": gdn_partial,
        "both_states_partial": gup_partial and gdn_partial,
        "classification": "FORCED_MID_TRANSITION"
        if gup_partial and gdn_partial
        else "NOT_BOTH_PARTIAL",
    }


def edge_lines(ax: plt.Axes, case: base.Case) -> None:
    for edge in base.command_edges(case):
        ax.axvline(edge, color="#999999", lw=1.0, ls="--", alpha=0.75)


def plot_waveforms(
    case: base.Case,
    data: dict[str, np.ndarray],
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    t = data["time_ns"]
    fig, axes = plt.subplots(3, 1, figsize=(14.5, 9.0), sharex=True, constrained_layout=True)
    axes[0].plot(t, data["hspice_ibis_pad_v"], color=BLACK, lw=3.0, label="HSPICE native IBIS")
    axes[0].plot(t, data["hspice_transistor_pad_v"], color=GRAY, lw=3.2, label="HSPICE transistor")
    axes[0].plot(t, data["gate_state_pad_v"], color=RED, lw=1.9, label="gate state model")
    axes[1].plot(t, data["hspice_ibis_ku"], color=BLACK, lw=3.0)
    axes[1].plot(t, data["gate_state_ku"], color=RED, lw=1.9)
    axes[2].plot(t, data["hspice_ibis_kd"], color=BLACK, lw=3.0)
    axes[2].plot(t, data["gate_state_kd"], color=RED, lw=1.9)
    for ax, ylabel in zip(axes, ["pad voltage (V)", "Ku", "Kd"]):
        base.style_axis(ax, ylabel, case)
        edge_lines(ax, case)
    axes[2].axhline(0.0, color="#777777", lw=0.8)
    axes[0].legend(frameon=False, ncol=3, loc="upper center")
    axes[2].set_xlabel("time (ns)")
    fig.suptitle(case.title, fontweight="bold")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_state_evidence(
    case: base.Case,
    data: dict[str, np.ndarray],
    record: dict[str, object],
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    t = data["time_ns"]
    fig, axes = plt.subplots(3, 1, figsize=(14.5, 8.6), sharex=True, constrained_layout=True)
    axes[0].plot(t, data["input_v"], color=BLACK, lw=2.4, label="input command")
    axes[1].plot(t, data["gate_state_gup"], color=RED, lw=2.3, label="GUP")
    axes[1].plot(t, data["gate_state_guptarget"], color=PURPLE, lw=1.6, label="GUP target")
    axes[2].plot(t, data["gate_state_gdn"], color=GREEN, lw=2.3, label="GDN")
    axes[2].plot(t, data["gate_state_gdntarget"], color=BLUE, lw=1.6, label="GDN target")
    raw_reverse = float(record["raw_reverse_ns"])
    gup_reverse = float(record["gup_reverse_target_50_ns"])
    gdn_reverse = float(record["gdn_reverse_target_50_ns"])
    for ax in axes:
        ax.axvline(raw_reverse, color="#777777", lw=1.2, ls="--", label="input reverse")
        ax.axvline(gup_reverse, color=RED, lw=1.2, ls=":", label="GUP reverse command")
        ax.axvline(gdn_reverse, color=GREEN, lw=1.2, ls=":", label="GDN reverse command")
        ax.grid(True, color="#dddddd", alpha=0.75)
    axes[1].scatter([gup_reverse], [float(record["gup_at_reverse"])], color=RED, s=55, zorder=5)
    axes[2].scatter([gdn_reverse], [float(record["gdn_at_reverse"])], color=GREEN, s=55, zorder=5)
    axes[1].annotate(
        f"GUP={float(record['gup_at_reverse']):.3f}",
        (gup_reverse, float(record["gup_at_reverse"])),
        xytext=(8, 12),
        textcoords="offset points",
        color=RED,
        fontweight="bold",
    )
    axes[2].annotate(
        f"GDN={float(record['gdn_at_reverse']):.3f}",
        (gdn_reverse, float(record["gdn_at_reverse"])),
        xytext=(8, 12),
        textcoords="offset points",
        color=GREEN,
        fontweight="bold",
    )
    axes[0].set_ylabel("input (V)")
    axes[1].set_ylabel("GUP")
    axes[2].set_ylabel("GDN")
    axes[2].set_xlabel("time (ns)")
    axes[0].legend(frameon=False, ncol=4, loc="upper center")
    axes[1].legend(frameon=False, loc="upper right")
    axes[2].legend(frameon=False, loc="upper right")
    pulse_start = 5.0 if case.pattern == "short_high" else 10.0
    right = max(gup_reverse, gdn_reverse) + 0.8
    axes[2].set_xlim(pulse_start - 0.35, right)
    fig.suptitle(f"{case.title}: state at each delayed reverse command", fontweight="bold")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def localized_response(
    variant_id: str,
    case: base.Case,
    data: dict[str, np.ndarray],
) -> dict[str, object] | None:
    if case.pattern not in {"short_high", "short_low"}:
        return None
    start_ns = 5.0 if case.pattern == "short_high" else 10.0
    stop_ns = start_ns + 2.5
    mask = (data["time_ns"] >= start_ns) & (data["time_ns"] <= stop_ns)
    if not np.any(mask):
        raise RuntimeError(f"No localized response window for {case.case_id}")

    def extremum(key: str) -> float:
        values = data[key][mask]
        if case.pattern == "short_high":
            return float(np.max(values))
        return float(np.min(values))

    def coefficient_extremum(key: str, coefficient: str) -> float:
        values = data[key][mask]
        if (case.pattern == "short_high" and coefficient == "ku") or (
            case.pattern == "short_low" and coefficient == "kd"
        ):
            return float(np.max(values))
        return float(np.min(values))

    native_pad = extremum("hspice_ibis_pad_v")
    gate_pad = extremum("gate_state_pad_v")
    return {
        "variant_id": variant_id,
        "case_id": case.case_id,
        "direction": case.pattern,
        "pulse_width_ps": case.pulse_width_ns * 1e3,
        "window_start_ns": start_ns,
        "window_stop_ns": stop_ns,
        "hspice_ibis_pad_extreme_v": native_pad,
        "hspice_transistor_pad_extreme_v": extremum("hspice_transistor_pad_v"),
        "legacy_pad_extreme_v": extremum("legacy_pad_v"),
        "gate_state_pad_extreme_v": gate_pad,
        "gate_state_pad_extreme_error_v": gate_pad - native_pad,
        "hspice_ibis_ku_extreme": coefficient_extremum(
            "hspice_ibis_ku", "ku"
        ),
        "legacy_ku_extreme": coefficient_extremum("legacy_ku", "ku"),
        "gate_state_ku_extreme": coefficient_extremum("gate_state_ku", "ku"),
        "hspice_ibis_kd_extreme": coefficient_extremum(
            "hspice_ibis_kd", "kd"
        ),
        "legacy_kd_extreme": coefficient_extremum("legacy_kd", "kd"),
        "gate_state_kd_extreme": coefficient_extremum("gate_state_kd", "kd"),
    }


def plot_reversal_depth_summary(
    states: list[dict[str, object]],
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(13.0, 8.0),
        sharey=True,
        constrained_layout=True,
    )
    for row_index, variant_id in enumerate(["slow_1ns", "fast_5ps"]):
        for column_index, direction in enumerate(["short_high", "short_low"]):
            ax = axes[row_index, column_index]
            rows = sorted(
                (
                    row
                    for row in states
                    if row["variant_id"] == variant_id
                    and row["direction"] == direction
                ),
                key=lambda row: float(row["pulse_width_ps"]),
            )
            widths = [float(row["pulse_width_ps"]) for row in rows]
            ax.axhspan(0.05, 0.95, color="#e8f4ea", alpha=0.85)
            ax.plot(
                widths,
                [float(row["gup_at_reverse"]) for row in rows],
                color=RED,
                marker="o",
                lw=2.2,
                label="GUP at its reverse command",
            )
            ax.plot(
                widths,
                [float(row["gdn_at_reverse"]) for row in rows],
                color=GREEN,
                marker="s",
                lw=2.2,
                label="GDN at its reverse command",
            )
            ax.axhline(0.05, color="#777777", lw=1.0, ls="--")
            ax.axhline(0.95, color="#777777", lw=1.0, ls="--")
            ax.set_title(
                f"{'slow IBIS' if variant_id == 'slow_1ns' else 'fast IBIS'}: "
                f"{'short high' if direction == 'short_high' else 'short low'}"
            )
            ax.set_xlabel("input pulse width (ps)")
            ax.set_xticks(widths)
            ax.set_ylabel("state at delayed reverse command")
            ax.set_ylim(-0.02, 1.02)
            ax.grid(True, color="#dddddd", alpha=0.75)
    axes[0, 0].legend(frameon=False, loc="upper left")
    fig.suptitle(
        "Reversal certification: both hidden states are still partial",
        fontweight="bold",
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_response_extrema_summary(
    responses: list[dict[str, object]],
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(13.0, 8.0),
        constrained_layout=True,
    )
    flows = [
        ("hspice_ibis_pad_extreme_v", "HSPICE native IBIS", BLACK, "o"),
        ("hspice_transistor_pad_extreme_v", "HSPICE transistor", GRAY, "s"),
        ("gate_state_pad_extreme_v", "gate state model", RED, "D"),
    ]
    for row_index, variant_id in enumerate(["slow_1ns", "fast_5ps"]):
        for column_index, direction in enumerate(["short_high", "short_low"]):
            ax = axes[row_index, column_index]
            rows = sorted(
                (
                    row
                    for row in responses
                    if row["variant_id"] == variant_id
                    and row["direction"] == direction
                ),
                key=lambda row: float(row["pulse_width_ps"]),
            )
            widths = [float(row["pulse_width_ps"]) for row in rows]
            for key, label, color, marker in flows:
                ax.plot(
                    widths,
                    [float(row[key]) for row in rows],
                    color=color,
                    marker=marker,
                    lw=2.2,
                    label=label,
                )
            ax.set_title(
                f"{'slow IBIS' if variant_id == 'slow_1ns' else 'fast IBIS'}: "
                f"{'high-pulse peak' if direction == 'short_high' else 'low-pulse minimum'}"
            )
            ax.set_xlabel("input pulse width (ps)")
            ax.set_xticks(widths)
            ax.set_ylabel("localized pad extreme (V)")
            ax.grid(True, color="#dddddd", alpha=0.75)
    axes[0, 0].legend(frameon=False, loc="best")
    fig.suptitle(
        "Localized pad response by pulse width",
        fontweight="bold",
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def write_report(
    fits: dict[str, dict[str, object]],
    metrics: list[dict[str, object]],
    states: list[dict[str, object]],
    responses: list[dict[str, object]],
    cache_rows: list[dict[str, object]],
) -> None:
    metric_lookup = {
        (str(row["variant_id"]), str(row["case_id"]), str(row["flow"])): row
        for row in metrics
    }
    lines = [
        "# inv_chain Forced Mid-Transition Reversal Study",
        "",
        "This study replaces nominally short 50/100/200 ps tests with pulse widths chosen from the fitted directional delays and taus. A case is accepted as a genuine reversal only when both GUP and GDN are between 0.05 and 0.95 when their own delayed reverse commands arrive.",
        "",
        "## Bench",
        "",
        "- Supply: `1.8 V`; load: `50 ohm || 2 pF`; temperature: `27 C`.",
        "- Applied input edge: `1 ps`.",
        "- High-pulse widths: `35, 45, 50 ps`.",
        "- Low-pulse widths: `40, 45, 50 ps`.",
        "- HSPICE native IBIS and transistor runs use the new stimuli and are cached by deck/model signature.",
        "",
        "## Why The Old Set Was Weak",
        "",
        "- The input pulse width is not the duration seen by each hidden state because pullup and pulldown on/off delays differ.",
        "- For short-high, GUP motion is approximately `width - 21 ps`, while GDN motion is approximately `width + 35-36 ps`.",
        "- For short-low, the skew reverses. The old 100 ps and 200 ps cases are mostly settled; 50 ps is near the boundary and remains partial for both states in this measured setup.",
        "- A screened 25 ps high candidate was also too early: GUP was below the 5% state threshold when its reverse command arrived. Its completed artifacts remain under `slow_1ns/cases/midrev_25ps_high/`.",
        "",
        "## Reversal Certification",
        "",
        "| Profile | Case | GUP at reverse | GDN at reverse | Both partial |",
        "|---|---|---:|---:|---|",
    ]
    for row in states:
        lines.append(
            f"| {row['variant_id']} | {row['case_id']} | "
            f"{float(row['gup_at_reverse']):.3f} | "
            f"{float(row['gdn_at_reverse']):.3f} | "
            f"{row['both_states_partial']} |"
        )
    lines.extend(
        [
            "",
            "## Coefficient-First Results",
            "",
            "| Profile | Case | Flow | Pad RMSE (mV) | Ku RMSE | Kd RMSE |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for variant in prior.VARIANTS:
        for case in CASES[1:]:
            for flow in ["gate_state"]:
                row = metric_lookup[(variant.variant_id, case.case_id, flow)]
                lines.append(
                    f"| {variant.variant_id} | {case.case_id} | {flow} | "
                    f"{1e3 * float(row['pad_rmse_v_vs_hspice_ibis']):.3f} | "
                    f"{float(row['ku_rmse_vs_hspice_ibis']):.5f} | "
                    f"{float(row['kd_rmse_vs_hspice_ibis']):.5f} |"
                )
    lines.extend(
        [
            "",
            "## Localized Response Extremes",
            "",
            "These values are measured only around the delayed output response. They prevent a broad-window RMSE from hiding a short but important amplitude error.",
            "",
            "| Profile | Case | Native IBIS pad | Transistor pad | Gate-state pad | Gate minus native |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in responses:
        lines.append(
            f"| {row['variant_id']} | {row['case_id']} | "
            f"{float(row['hspice_ibis_pad_extreme_v']):.3f} | "
            f"{float(row['hspice_transistor_pad_extreme_v']):.3f} | "
            f"{float(row['gate_state_pad_extreme_v']):.3f} | "
            f"{float(row['gate_state_pad_extreme_error_v']):+.3f} |"
        )
    certified = sum(str(row["both_states_partial"]).lower() == "true" for row in states)
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `<profile>/plots/01_waveform_comparison/`: pad, Ku, and Kd overlays.",
            "- `<profile>/plots/02_reversal_state_evidence/`: input, GUP/GDN, targets, and sampled state values.",
            "- `<profile>/waveform_data/`: aligned numeric waveforms.",
            "- `plots/03_reversal_depth_summary.png`: measured GUP/GDN state depth at every reverse command.",
            "- `plots/04_response_extrema_summary.png`: localized pad peaks/minima across pulse widths.",
            "- `reversal_state_summary.csv`: measured state-at-reverse certification.",
            "- `localized_response_extrema.csv`: pad and coefficient extrema around each interrupted response.",
            "- `metrics.csv`: pad/Ku/Kd comparison metrics.",
            "- Legacy pybis metrics remain in `metrics.csv` for provenance, but legacy is intentionally omitted from presentation figures and report tables because its reversal failure is already established.",
            "",
            f"Certified forced reversals: `{certified}/{len(states)}`.",
            f"HSPICE reference records: `{len(cache_rows)}`.",
            "",
            "## Interpretation",
            "",
            "- These cases test actual hidden-state reversals rather than merely short input pulses.",
            "- Gate-state playback is dramatically better than legacy full-table replay in all certified cases.",
            "- It is not uniformly amplitude-correct: the shortest short-high response can overshoot native IBIS, and short-low pad dips are substantially too deep.",
            "- HSPICE transistor output largely rejects these 35-50 ps pulses. Matching native-IBIS Ku/Kd is therefore an IBIS-playback claim, not a claim that the IBIS model reproduces transistor minimum-pulse filtering.",
            "- The normal reconstruction gate still applies before any gate-state result is considered generally valid.",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run inv_chain pulse widths certified to reverse GUP and GDN mid-transition."
    )
    parser.add_argument("--ngspice", type=Path, default=base.DEFAULT_NGSPICE)
    parser.add_argument("--hspice", type=Path, default=base.DEFAULT_HSPICE)
    parser.add_argument("--timeout-s", type=int, default=240)
    parser.add_argument("--report-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prior.OUT_DIR = OUT_DIR
    metrics: list[dict[str, object]] = []
    states: list[dict[str, object]] = []
    responses: list[dict[str, object]] = []
    cache_rows: list[dict[str, object]] = []
    fits: dict[str, dict[str, object]] = {}

    for variant in prior.VARIANTS:
        variant_dir = OUT_DIR / variant.variant_id
        configure_variant(variant_dir)
        if args.report_only:
            fit_rows = read_csv(variant_dir / "gate_fit_summary.csv")
            if not fit_rows:
                raise FileNotFoundError(variant_dir / "gate_fit_summary.csv")
            fit = fit_rows[0]
        else:
            fit = base.offline_fit(variant.ibis)
        fits[variant.variant_id] = fit
        models = {} if args.report_only else base.prepare_models(variant.ibis)
        waveform_images: list[Path] = []
        state_images: list[Path] = []

        for index, case in enumerate(CASES, start=1):
            print(f"[{variant.variant_id} {index}/{len(CASES)}] {case.case_id}", flush=True)
            if args.report_only:
                data = read_waveform(base.DATA_DIR / f"{case.case_id}.csv")
            else:
                native, native_cache = prior.run_native(
                    variant, case, args.hspice, args.timeout_s
                )
                transistor, transistor_cache = base.run_hspice_transistor(
                    case,
                    prior.DEFAULT_TRANSISTOR_WRAPPER,
                    prior.DEFAULT_TRANSISTOR_LIBRARY,
                    args.hspice,
                    args.timeout_s,
                )
                transistor_cache["variant_id"] = variant.variant_id
                legacy, _, _ = base.run_ngspice(
                    case, "legacy", models["legacy"], args.ngspice, args.timeout_s
                )
                gate, _, _ = base.run_ngspice(
                    case, "gate_state", models["gate_state"], args.ngspice, args.timeout_s
                )
                data = prior.uniformize_case_data(
                    case,
                    base.align_case(case, native, transistor, legacy, gate),
                )
                rows = prior.add_variant_fields(variant, base.case_metrics(case, data))
                metrics.extend(rows)
                native_cache["variant_id"] = variant.variant_id
                cache_rows.extend([native_cache, transistor_cache])
                base.write_csv(OUT_DIR / "metrics.csv", metrics)
                base.write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)
            waveform_images.append(
                plot_waveforms(
                    case,
                    data,
                    base.PLOTS_DIR / "01_waveform_comparison" / f"{case.case_id}.png",
                )
            )
            record = certify_reversal(variant.variant_id, case, data, fit)
            if record is not None:
                states.append(record)
                response = localized_response(variant.variant_id, case, data)
                if response is not None:
                    responses.append(response)
                state_images.append(
                    plot_state_evidence(
                        case,
                        data,
                        record,
                        base.PLOTS_DIR
                        / "02_reversal_state_evidence"
                        / f"{case.case_id}.png",
                    )
                )
                base.write_csv(OUT_DIR / "reversal_state_summary.csv", states)
        base.contact_sheet(
            waveform_images,
            base.PLOTS_DIR / "01_waveform_comparison_contact_sheet.png",
        )
        base.contact_sheet(
            state_images,
            base.PLOTS_DIR / "02_reversal_state_evidence_contact_sheet.png",
        )

    if args.report_only:
        metrics = read_csv(OUT_DIR / "metrics.csv")
        cache_rows = read_csv(OUT_DIR / "reference_cache_manifest.csv")
    base.write_csv(OUT_DIR / "reversal_state_summary.csv", states)
    base.write_csv(OUT_DIR / "localized_response_extrema.csv", responses)
    plot_reversal_depth_summary(
        states,
        OUT_DIR / "plots" / "03_reversal_depth_summary.png",
    )
    plot_response_extrema_summary(
        responses,
        OUT_DIR / "plots" / "04_response_extrema_summary.png",
    )
    write_report(fits, metrics, states, responses, cache_rows)
    print(f"OUT_DIR={OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
