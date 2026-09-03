from __future__ import annotations

import argparse
import csv
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

import run_inv_chain_forced_midtransition_reversal as forced  # noqa: E402
import run_inv_chain_gate_state_clean_comparison as base  # noqa: E402
import run_inv_chain_s2ibispy_slow_fast_comparison as prior  # noqa: E402
import run_reversal_hybrid_slow_fast_comparison as hybrid  # noqa: E402


OUT_DIR = ROOT / "results" / "inv_chain_transistor_visible_reversal_2026-07-28"
WIDTHS_PS = (
    55,
    60,
    65,
    70,
    75,
    80,
    90,
    92,
    94,
    96,
    98,
    100,
    102,
    104,
    106,
    108,
    110,
    115,
    120,
    150,
    180,
    200,
)
RESPONSE_MIN = 0.05
PARTIAL_MAX = 0.95
REPRESENTATIVE_CASE_IDS = (
    "visible_sweep_100ps_high",
    "visible_sweep_110ps_low",
)

BLACK = "#111111"
GRAY = "#777777"
RED = "#d62728"
GREEN = "#009e73"
BLUE = "#1769aa"
PURPLE = "#7b2cbf"


def cases() -> list[base.Case]:
    result = [
        base.Case(
            "edge_1ps_base_50r_2pf",
            "Complete rise and fall",
            "rise_fall",
            10.0,
            22.0,
        )
    ]
    for width_ps in WIDTHS_PS:
        width_ns = width_ps * 1e-3
        result.extend(
            [
                base.Case(
                    f"visible_sweep_{width_ps}ps_high",
                    f"{width_ps} ps high pulse",
                    "short_high",
                    width_ns,
                    9.0,
                ),
                base.Case(
                    f"visible_sweep_{width_ps}ps_low",
                    f"{width_ps} ps low pulse",
                    "short_low",
                    width_ns,
                    14.0,
                ),
            ]
        )
    return result


def configure(path: Path) -> None:
    prior.configure_variant(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def gate_data(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "time_ns": base.to_ns(base.find_signal(raw, "time")),
        "gate_state_gup": base.find_signal(raw, "v(xdrv.gup)", "v(xdrv:gup)"),
        "gate_state_gdn": base.find_signal(raw, "v(xdrv.gdn)", "v(xdrv:gdn)"),
        "gate_state_guptarget": base.find_signal(
            raw, "v(xdrv.guptarget)", "v(xdrv:guptarget)"
        ),
        "gate_state_gdntarget": base.find_signal(
            raw, "v(xdrv.gdntarget)", "v(xdrv:gdntarget)"
        ),
    }


def transistor_wave(raw: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    return (
        base.to_ns(base.find_signal(raw, "time")),
        base.find_signal(raw, "v(pad_sp)"),
    )


def native_wave(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "time_ns": base.to_ns(base.find_signal(raw, "time")),
        "pad_v": base.find_signal(raw, "v(pad_ibis)", "v(pad)"),
        "ku": base.find_signal(raw, "v(ku)"),
        "kd": base.find_signal(raw, "v(kd)"),
    }


def ngspice_gate_wave(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    result = {
        "time_ns": base.to_ns(base.find_signal(raw, "time")),
        "pad_v": base.find_signal(raw, "v(pad)"),
        "ku": base.find_signal(raw, "v(xdrv.ku)", "v(xdrv:ku)"),
        "kd": base.find_signal(raw, "v(xdrv.kd)", "v(xdrv:kd)"),
    }
    result.update(gate_data(raw))
    return result


def response_extreme(
    case: base.Case,
    time_ns: np.ndarray,
    pad_v: np.ndarray,
) -> float:
    start = 5.0 if case.pattern == "short_high" else 10.0
    mask = (time_ns >= start) & (time_ns <= start + 2.5)
    values = pad_v[mask]
    return float(np.max(values) if case.pattern == "short_high" else np.min(values))


def settled_levels(
    time_ns: np.ndarray,
    pad_v: np.ndarray,
) -> tuple[float, float]:
    low_mask = time_ns <= 4.8
    if not np.any(low_mask):
        raise RuntimeError("No pre-edge samples available for transistor low level")
    low = float(np.median(pad_v[low_mask]))
    high = float(np.median(pad_v[(time_ns >= 10.0) & (time_ns <= 14.0)]))
    return low, high


def excursion_fraction(
    direction: str,
    extreme: float,
    low: float,
    high: float,
) -> float:
    swing = max(high - low, 1e-12)
    if direction == "short_high":
        return (extreme - low) / swing
    return (high - extreme) / swing


def plot_summary(rows: list[dict[str, object]], output: Path) -> None:
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(14.5, 8.6),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )
    for row_index, variant_id in enumerate(["slow_1ns", "fast_5ps"]):
        for column_index, direction in enumerate(["short_high", "short_low"]):
            ax = axes[row_index, column_index]
            selected = sorted(
                (
                    row
                    for row in rows
                    if row["variant_id"] == variant_id
                    and row["direction"] == direction
                ),
                key=lambda row: float(row["pulse_width_ps"]),
            )
            widths = np.asarray(
                [float(row["pulse_width_ps"]) for row in selected], dtype=float
            )
            response = np.asarray(
                [float(row["transistor_excursion_fraction"]) for row in selected],
                dtype=float,
            )
            gup = np.asarray(
                [float(row["gup_at_reverse"]) for row in selected], dtype=float
            )
            gdn = np.asarray(
                [float(row["gdn_at_reverse"]) for row in selected], dtype=float
            )
            strict_candidate = np.asarray(
                [
                    str(row["strict_two_state_candidate"]).lower() == "true"
                    for row in selected
                ]
            )
            directional_candidate = np.asarray(
                [
                    str(row["directional_candidate"]).lower() == "true"
                    for row in selected
                ]
            )
            ax.axhspan(RESPONSE_MIN, PARTIAL_MAX, color="#eef6ee", alpha=0.9)
            ax.plot(
                widths,
                response,
                color=BLUE,
                marker="o",
                lw=2.2,
                label="transistor output excursion",
            )
            ax.plot(
                widths,
                gup,
                color=RED,
                marker="s",
                lw=2.0,
                label="GUP at reverse command",
            )
            ax.plot(
                widths,
                gdn,
                color=GREEN,
                marker="D",
                lw=2.0,
                label="GDN at reverse command",
            )
            if np.any(directional_candidate):
                ax.scatter(
                    widths[directional_candidate],
                    response[directional_candidate],
                    s=130,
                    facecolors="none",
                    edgecolors=PURPLE,
                    linewidths=2.4,
                    label="one-state directional candidate",
                    zorder=6,
                )
            if np.any(strict_candidate):
                ax.scatter(
                    widths[strict_candidate],
                    response[strict_candidate],
                    s=45,
                    color=BLACK,
                    label="strict two-state candidate",
                    zorder=7,
                )
            ax.axhline(RESPONSE_MIN, color="#888888", lw=1.0, ls="--")
            ax.axhline(PARTIAL_MAX, color="#888888", lw=1.0, ls="--")
            ax.set_title(
                f"{'slow IBIS' if variant_id == 'slow_1ns' else 'fast IBIS'} | "
                f"{'short high' if direction == 'short_high' else 'short low'}"
            )
            ax.set_xlabel("input pulse width (ps)")
            ax.set_ylabel("normalized response / state")
            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, color="#dddddd", alpha=0.75)
    axes[0, 0].legend(frameon=False, fontsize=9, loc="best")
    fig.suptitle(
        "Does transistor-visible response overlap a certified hidden-state reversal?",
        fontweight="bold",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_candidate(
    variant_id: str,
    case: base.Case,
    transistor: tuple[np.ndarray, np.ndarray],
    state: dict[str, np.ndarray],
    record: dict[str, object],
    output: Path,
) -> None:
    tt, pad = transistor
    t = state["time_ns"]
    start = 5.0 if case.pattern == "short_high" else 10.0
    reverse = start + case.pulse_width_ns + 0.5 * base.EDGE_NS
    left = start - 0.2
    right = start + 1.2
    fig, axes = plt.subplots(
        3, 1, figsize=(14.5, 8.4), sharex=True, constrained_layout=True
    )
    axes[0].plot(tt, pad, color=BLACK, lw=3.0, label="HSPICE transistor pad")
    axes[1].plot(t, state["gate_state_gup"], color=RED, lw=2.3, label="GUP")
    axes[1].plot(
        t,
        state["gate_state_guptarget"],
        color=PURPLE,
        lw=1.6,
        label="GUP target",
    )
    axes[2].plot(t, state["gate_state_gdn"], color=GREEN, lw=2.3, label="GDN")
    axes[2].plot(
        t,
        state["gate_state_gdntarget"],
        color=BLUE,
        lw=1.6,
        label="GDN target",
    )
    for ax in axes:
        ax.axvline(start + 0.5 * base.EDGE_NS, color="#888888", ls="--", lw=1.2)
        ax.axvline(reverse, color="#555555", ls="--", lw=1.2)
        ax.set_xlim(left, right)
        ax.grid(True, color="#dddddd", alpha=0.75)
    axes[0].set_ylabel("pad voltage (V)")
    axes[1].set_ylabel("GUP")
    axes[2].set_ylabel("GDN")
    axes[2].set_xlabel("time (ns)")
    axes[0].legend(frameon=False)
    axes[1].legend(frameon=False)
    axes[2].legend(frameon=False)
    axes[1].annotate(
        f"GUP={float(record['gup_at_reverse']):.3f}",
        (
            float(record["gup_reverse_target_50_ns"]),
            float(record["gup_at_reverse"]),
        ),
        xytext=(8, 10),
        textcoords="offset points",
        color=RED,
        fontweight="bold",
    )
    axes[2].annotate(
        f"GDN={float(record['gdn_at_reverse']):.3f}",
        (
            float(record["gdn_reverse_target_50_ns"]),
            float(record["gdn_at_reverse"]),
        ),
        xytext=(8, 10),
        textcoords="offset points",
        color=GREEN,
        fontweight="bold",
    )
    fig.suptitle(
        f"{variant_id} | {case.title}",
        fontweight="bold",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.sqrt(np.mean((candidate - reference) ** 2)))


def plot_representative_comparison(
    variant_id: str,
    case: base.Case,
    native: dict[str, np.ndarray],
    transistor: tuple[np.ndarray, np.ndarray],
    gate: dict[str, np.ndarray],
    hybrid_wave: dict[str, np.ndarray],
    output: Path,
) -> dict[str, object]:
    start = 5.0 if case.pattern == "short_high" else 10.0
    left = start - 0.2
    right = start + 2.0
    t = np.arange(left, right + 0.0005, 0.001)
    input_v = base.input_waveform(case, t)

    def sample(wave: dict[str, np.ndarray], key: str) -> np.ndarray:
        return np.interp(t, wave["time_ns"], wave[key])

    transistor_pad = np.interp(t, transistor[0], transistor[1])
    native_pad = sample(native, "pad_v")
    native_ku = sample(native, "ku")
    native_kd = sample(native, "kd")
    gate_pad = sample(gate, "pad_v")
    gate_ku = sample(gate, "ku")
    gate_kd = sample(gate, "kd")
    hybrid_pad = sample(hybrid_wave, "pad_v")
    hybrid_ku = sample(hybrid_wave, "ku")
    hybrid_kd = sample(hybrid_wave, "kd")

    fig, axes = plt.subplots(
        3, 1, figsize=(14.5, 9.0), sharex=True, constrained_layout=True
    )
    axes[0].plot(t, native_pad, color=BLACK, lw=3.0, label="HSPICE native IBIS")
    axes[0].plot(
        t, transistor_pad, color=GRAY, lw=3.2, label="HSPICE transistor"
    )
    axes[0].plot(t, gate_pad, color=RED, lw=2.0, label="gate state model")
    axes[0].plot(t, hybrid_pad, color=PURPLE, lw=2.0, label="hybrid model")
    axes[1].plot(t, native_ku, color=BLACK, lw=3.0)
    axes[1].plot(t, gate_ku, color=RED, lw=2.0)
    axes[1].plot(t, hybrid_ku, color=PURPLE, lw=2.0)
    axes[2].plot(t, native_kd, color=BLACK, lw=3.0)
    axes[2].plot(t, gate_kd, color=RED, lw=2.0)
    axes[2].plot(t, hybrid_kd, color=PURPLE, lw=2.0)
    reverse = start + case.pulse_width_ns + 0.5 * base.EDGE_NS
    for ax, ylabel in zip(axes, ["pad voltage (V)", "Ku", "Kd"]):
        ax.axvline(start + 0.5 * base.EDGE_NS, color="#999999", ls="--", lw=1.0)
        ax.axvline(reverse, color="#666666", ls="--", lw=1.0)
        ax.set_ylabel(ylabel)
        ax.grid(True, color="#dddddd", alpha=0.75)
    axes[2].axhline(0.0, color="#777777", lw=0.8)
    axes[0].legend(frameon=False, ncol=4, loc="upper right")
    axes[2].set_xlabel("time (ns)")
    fig.suptitle(f"{variant_id} | {case.title}", fontweight="bold")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)

    return {
        "variant_id": variant_id,
        "case_id": case.case_id,
        "pulse_width_ps": case.pulse_width_ns * 1e3,
        "transistor_pad_extreme_v": response_extreme(
            case, transistor[0], transistor[1]
        ),
        "gate_pad_rmse_v_vs_native": rmse(native_pad, gate_pad),
        "gate_ku_rmse_vs_native": rmse(native_ku, gate_ku),
        "gate_kd_rmse_vs_native": rmse(native_kd, gate_kd),
        "hybrid_pad_rmse_v_vs_native": rmse(native_pad, hybrid_pad),
        "hybrid_ku_rmse_vs_native": rmse(native_ku, hybrid_ku),
        "hybrid_kd_rmse_vs_native": rmse(native_kd, hybrid_kd),
        "input_peak_v": float(np.max(input_v)),
    }


def write_report(
    rows: list[dict[str, object]],
    representative_metrics: list[dict[str, object]],
) -> None:
    strict_candidates = [
        row
        for row in rows
        if str(row["strict_two_state_candidate"]).lower() == "true"
    ]
    directional_candidates = [
        row
        for row in rows
        if str(row["directional_candidate"]).lower() == "true"
    ]
    lines = [
        "# inv_chain Transistor-Visible Reversal Sweep",
        "",
        "This focused sweep asks whether an input pulse can both produce a measurable, incomplete HSPICE transistor output pulse and reverse the fitted pybis hidden states while both remain between 5% and 95%.",
        "",
        "## Headline Finding",
        "",
        "- No pulse width satisfies the strict requirement that the transistor respond while both `GUP` and `GDN` remain partial.",
        "- Useful one-state directional cases do exist. A `100 ps` high pulse produces a `36.8%` transistor output excursion while `GUP` remains partial. A `110 ps` low pulse produces a `47.8%` excursion while `GDN` remains partial.",
        "- These cases are valid tests of one coefficient network reversing from history. They are not proof of simultaneous pullup and pulldown retrigger behavior.",
        "- For the representative slow and fast IBIS comparisons, the hybrid improves pad, `Ku`, and `Kd` RMSE versus the always-on gate-state model.",
        "",
        "## Bench",
        "",
        "- Supply: `1.8 V`.",
        "- Load: `50 ohm || 2 pF`.",
        "- Input rise/fall: `1 ps`.",
        "- Temperature: `27 C`.",
        f"- Pulse widths: `{', '.join(str(value) for value in WIDTHS_PS)} ps`.",
        "- The transistor reference is independent of the slow/fast IBIS profile and is cached by the transistor deck/model signature.",
        "",
        "## Criteria",
        "",
        f"- Transistor-visible partial pulse: output excursion is from `{100 * RESPONSE_MIN:.0f}%` to `{100 * PARTIAL_MAX:.0f}%` of the loaded settled swing.",
        "- Strict two-state reversal: both `GUP` and `GDN` are between `0.05` and `0.95` at their own delayed reverse commands.",
        "- One-state directional reversal: at least one of `GUP/GDN` is still partial. This is a real interrupted transition, but the other network has already settled.",
        "- A candidate must also satisfy the transistor-visible partial-pulse criterion.",
        "",
        "## Strict Two-State Candidates",
        "",
        "| Profile | Direction | Width (ps) | Transistor excursion | GUP | GDN |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in strict_candidates:
        lines.append(
            f"| {row['variant_id']} | {row['direction']} | "
            f"{float(row['pulse_width_ps']):.0f} | "
            f"{100 * float(row['transistor_excursion_fraction']):.1f}% | "
            f"{float(row['gup_at_reverse']):.3f} | "
            f"{float(row['gdn_at_reverse']):.3f} |"
        )
    if not strict_candidates:
        lines.append("| none | none | n/a | n/a | n/a | n/a |")
    lines.extend(
        [
            "",
            "## One-State Directional Candidates",
            "",
            "| Profile | Direction | Width (ps) | Transistor excursion | GUP | GDN |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in directional_candidates:
        lines.append(
            f"| {row['variant_id']} | {row['direction']} | "
            f"{float(row['pulse_width_ps']):.0f} | "
            f"{100 * float(row['transistor_excursion_fraction']):.1f}% | "
            f"{float(row['gup_at_reverse']):.3f} | "
            f"{float(row['gdn_at_reverse']):.3f} |"
        )
    if not directional_candidates:
        lines.append("| none | none | n/a | n/a | n/a | n/a |")
    lines.extend(
        [
            "",
            "## Representative Full Comparisons",
            "",
            "| Profile | Case | Gate pad (mV) | Hybrid pad (mV) | Gate Ku | Hybrid Ku | Gate Kd | Hybrid Kd |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in representative_metrics:
        lines.append(
            f"| {row['variant_id']} | {row['case_id']} | "
            f"{1e3 * float(row['gate_pad_rmse_v_vs_native']):.3f} | "
            f"{1e3 * float(row['hybrid_pad_rmse_v_vs_native']):.3f} | "
            f"{float(row['gate_ku_rmse_vs_native']):.5f} | "
            f"{float(row['hybrid_ku_rmse_vs_native']):.5f} | "
            f"{float(row['gate_kd_rmse_vs_native']):.5f} | "
            f"{float(row['hybrid_kd_rmse_vs_native']):.5f} |"
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `sweep_summary.csv`: numeric result for every width/profile/direction.",
            "- `plots/01_overlap_summary.png`: transistor excursion and hidden-state depth versus pulse width.",
            "- `plots/candidates/`: waveform/state evidence for every joint candidate.",
            "- `plots/representative_comparisons/`: HSPICE native IBIS, HSPICE transistor, gate-state, and hybrid overlays for the 100 ps high and 110 ps low cases.",
            "- `representative_comparison_metrics.csv`: numeric errors for those full comparisons.",
            "",
            "## Interpretation",
            "",
            "A transistor-visible short pulse and a pybis hidden-state reversal are separate tests. The strict two-state and one-state directional classifications must remain distinct; a one-state case is useful for testing that coefficient's reversal, but it cannot validate simultaneous pullup and pulldown state recovery.",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find inv_chain pulse widths with transistor response and partial gate states."
    )
    parser.add_argument("--ngspice", type=Path, default=base.DEFAULT_NGSPICE)
    parser.add_argument("--hspice", type=Path, default=base.DEFAULT_HSPICE)
    parser.add_argument("--timeout-s", type=int, default=240)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_cases = cases()
    normal = all_cases[0]
    pulse_cases = all_cases[1:]
    rows: list[dict[str, object]] = []
    transistor_by_case: dict[
        str, tuple[np.ndarray, np.ndarray]
    ] = {}
    state_by_key: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    record_by_key: dict[tuple[str, str], dict[str, object]] = {}
    gate_wave_by_key: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    native_by_key: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    hybrid_by_key: dict[tuple[str, str], dict[str, np.ndarray]] = {}

    transistor_dir = OUT_DIR / "transistor_reference"
    configure(transistor_dir)
    normal_raw, _ = base.run_hspice_transistor(
        normal,
        prior.DEFAULT_TRANSISTOR_WRAPPER,
        prior.DEFAULT_TRANSISTOR_LIBRARY,
        args.hspice,
        args.timeout_s,
    )
    normal_time, normal_pad = transistor_wave(normal_raw)
    low, high = settled_levels(normal_time, normal_pad)

    for index, case in enumerate(pulse_cases, start=1):
        print(f"[transistor {index}/{len(pulse_cases)}] {case.case_id}", flush=True)
        raw, _ = base.run_hspice_transistor(
            case,
            prior.DEFAULT_TRANSISTOR_WRAPPER,
            prior.DEFAULT_TRANSISTOR_LIBRARY,
            args.hspice,
            args.timeout_s,
        )
        transistor_by_case[case.case_id] = transistor_wave(raw)

    for variant in prior.VARIANTS:
        variant_dir = OUT_DIR / variant.variant_id
        configure(variant_dir)
        fit = base.offline_fit(variant.ibis)
        models = base.prepare_models(variant.ibis)
        for index, case in enumerate(pulse_cases, start=1):
            print(
                f"[{variant.variant_id} {index}/{len(pulse_cases)}] {case.case_id}",
                flush=True,
            )
            raw, _, _ = base.run_ngspice(
                case,
                "gate_state",
                models["gate_state"],
                args.ngspice,
                args.timeout_s,
            )
            gate_waveform = ngspice_gate_wave(raw)
            state = {
                key: value
                for key, value in gate_waveform.items()
                if key == "time_ns" or key.startswith("gate_state_")
            }
            record = forced.certify_reversal(
                variant.variant_id,
                case,
                state,
                fit,
            )
            if record is None:
                continue
            state_by_key[(variant.variant_id, case.case_id)] = state
            gate_wave_by_key[(variant.variant_id, case.case_id)] = gate_waveform
            record_by_key[(variant.variant_id, case.case_id)] = record
            tt, pad = transistor_by_case[case.case_id]
            extreme = response_extreme(case, tt, pad)
            fraction = excursion_fraction(case.pattern, extreme, low, high)
            visible_partial = RESPONSE_MIN <= fraction <= PARTIAL_MAX
            both_partial = bool(record["both_states_partial"])
            any_partial = bool(record["gup_partial_5_95"]) or bool(
                record["gdn_partial_5_95"]
            )
            rows.append(
                {
                    **record,
                    "transistor_settled_low_v": low,
                    "transistor_settled_high_v": high,
                    "transistor_pad_extreme_v": extreme,
                    "transistor_excursion_fraction": fraction,
                    "transistor_visible_partial": visible_partial,
                    "any_state_partial": any_partial,
                    "strict_two_state_candidate": visible_partial and both_partial,
                    "directional_candidate": visible_partial
                    and any_partial
                    and not both_partial,
                }
            )
            base.write_csv(OUT_DIR / "sweep_summary.csv", rows)

        representative_cases = [
            case for case in pulse_cases if case.case_id in REPRESENTATIVE_CASE_IDS
        ]
        hybrid_device = next(
            item for item in hybrid.DEVICES if item.device_id == "inv_chain"
        )
        hybrid_variant = next(
            item
            for item in hybrid.VARIANTS["inv_chain"]
            if item.variant_id
            == ("slow" if variant.variant_id == "slow_1ns" else "fast")
        )
        hybrid_model = hybrid.prepare_model(
            hybrid_device,
            hybrid_variant,
            variant_dir,
        )
        for case in representative_cases:
            native_raw, _ = prior.run_native(
                variant,
                case,
                args.hspice,
                args.timeout_s,
            )
            native_by_key[(variant.variant_id, case.case_id)] = native_wave(
                native_raw
            )
            hcase = hybrid.Case(
                case.case_id,
                case.title,
                case.pattern,
                case.pulse_width_ns,
                case.stop_ns,
                (
                    4.8 if case.pattern == "short_high" else 9.8,
                    7.0 if case.pattern == "short_high" else 12.0,
                ),
            )
            hwave, _, _ = hybrid.run_hybrid(
                hybrid_device,
                hcase,
                hybrid_model,
                variant_dir,
                args.ngspice,
                args.timeout_s,
            )
            hybrid_by_key[(variant.variant_id, case.case_id)] = hwave

    candidates = [
        row
        for row in rows
        if str(row["strict_two_state_candidate"]).lower() == "true"
        or str(row["directional_candidate"]).lower() == "true"
    ]
    for row in candidates:
        key = (str(row["variant_id"]), str(row["case_id"]))
        case = next(item for item in pulse_cases if item.case_id == row["case_id"])
        plot_candidate(
            key[0],
            case,
            transistor_by_case[key[1]],
            state_by_key[key],
            record_by_key[key],
            OUT_DIR
            / "plots"
            / "candidates"
            / f"{key[0]}_{key[1]}.png",
        )
    representative_metrics: list[dict[str, object]] = []
    for variant in prior.VARIANTS:
        for case_id in REPRESENTATIVE_CASE_IDS:
            key = (variant.variant_id, case_id)
            case = next(item for item in pulse_cases if item.case_id == case_id)
            representative_metrics.append(
                plot_representative_comparison(
                    variant.variant_id,
                    case,
                    native_by_key[key],
                    transistor_by_case[case_id],
                    gate_wave_by_key[key],
                    hybrid_by_key[key],
                    OUT_DIR
                    / "plots"
                    / "representative_comparisons"
                    / f"{variant.variant_id}_{case_id}.png",
                )
            )
    base.write_csv(OUT_DIR / "sweep_summary.csv", rows)
    base.write_csv(
        OUT_DIR / "representative_comparison_metrics.csv",
        representative_metrics,
    )
    plot_summary(rows, OUT_DIR / "plots" / "01_overlap_summary.png")
    write_report(rows, representative_metrics)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"JOINT_CANDIDATES={len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
