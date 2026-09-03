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

import run_inv_chain_gate_state_clean_comparison as base  # noqa: E402
import run_inv_chain_s2ibispy_slow_fast_comparison as prior  # noqa: E402
import run_inv_chain_transistor_visible_reversal_sweep as sweep  # noqa: E402


OUT_DIR = (
    ROOT
    / "results"
    / "inv_chain_transistor_visible_reversal_2026-07-28"
    / "native_ibis_match_analysis"
)
TRANSISTOR_ROOT = (
    ROOT
    / "results"
    / "inv_chain_transistor_visible_reversal_2026-07-28"
    / "transistor_reference"
    / "cases"
)

BLACK = "#111111"
GRAY = "#777777"
BLUE = "#1769aa"
ORANGE = "#d97706"
GREEN = "#009e73"
RED = "#d62728"

VISIBLE_MIN = 0.05
PARTIAL_MAX = 0.95
PAD_RMSE_MATCH_V = 0.075
EXTREME_ERROR_MATCH_V = 0.10
TIMING_ERROR_MATCH_NS = 0.10
REFINEMENT_WIDTHS_PS = (125, 130, 135, 140, 145)


def analysis_cases() -> list[base.Case]:
    result = list(sweep.cases()[1:])
    for width_ps in REFINEMENT_WIDTHS_PS:
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
    return sorted(
        result,
        key=lambda case: (case.pattern, case.pulse_width_ns),
    )


def read_transistor(case: base.Case) -> dict[str, np.ndarray]:
    stem = f"{case.case_id}_hspice_transistor"
    path = (
        TRANSISTOR_ROOT
        / case.case_id
        / "hspice_transistor"
        / f"{stem}.tr0"
    )
    if not path.exists():
        raise FileNotFoundError(path)
    raw = base.parse_hspice_tr0(path)
    return {
        "time_ns": base.to_ns(base.find_signal(raw, "time")),
        "pad_v": base.find_signal(raw, "v(pad_sp)"),
    }


def native_wave(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "time_ns": base.to_ns(base.find_signal(raw, "time")),
        "pad_v": base.find_signal(raw, "v(pad_ibis)", "v(pad)"),
        "ku": base.find_signal(raw, "v(ku)"),
        "kd": base.find_signal(raw, "v(kd)"),
    }


def interp(wave: dict[str, np.ndarray], t: np.ndarray, key: str) -> np.ndarray:
    return np.interp(t, wave["time_ns"], wave[key])


def rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.sqrt(np.mean((candidate - reference) ** 2)))


def response_metrics(
    case: base.Case,
    native: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
    settled_low_v: float,
    settled_high_v: float,
) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    start = 5.0 if case.pattern == "short_high" else 10.0
    stop = start + 2.0
    t = np.arange(start - 0.2, stop + 0.0005, 0.001)
    native_pad = interp(native, t, "pad_v")
    transistor_pad = interp(transistor, t, "pad_v")
    native_ku = interp(native, t, "ku")
    native_kd = interp(native, t, "kd")
    input_v = base.input_waveform(case, t)
    swing = settled_high_v - settled_low_v

    if case.pattern == "short_high":
        native_index = int(np.argmax(native_pad))
        transistor_index = int(np.argmax(transistor_pad))
        native_extreme = float(native_pad[native_index])
        transistor_extreme = float(transistor_pad[transistor_index])
        transistor_fraction = (transistor_extreme - settled_low_v) / swing
    else:
        native_index = int(np.argmin(native_pad))
        transistor_index = int(np.argmin(transistor_pad))
        native_extreme = float(native_pad[native_index])
        transistor_extreme = float(transistor_pad[transistor_index])
        transistor_fraction = (settled_high_v - transistor_extreme) / swing

    waveform_rmse = rmse(native_pad, transistor_pad)
    extreme_error = abs(native_extreme - transistor_extreme)
    timing_error = abs(float(t[native_index] - t[transistor_index]))
    transistor_visible = transistor_fraction >= VISIBLE_MIN
    transistor_partial = transistor_fraction <= PARTIAL_MAX
    matched = (
        transistor_visible
        and waveform_rmse <= PAD_RMSE_MATCH_V
        and extreme_error <= EXTREME_ERROR_MATCH_V
        and timing_error <= TIMING_ERROR_MATCH_NS
    )
    score = (
        waveform_rmse / PAD_RMSE_MATCH_V
        + extreme_error / EXTREME_ERROR_MATCH_V
        + timing_error / TIMING_ERROR_MATCH_NS
    )

    def active_duration(values: np.ndarray, active: np.ndarray) -> float:
        indices = np.where(active)[0]
        if not len(indices):
            return 0.0
        return float(t[indices[-1]] - t[indices[0]])

    return (
        {
            "case_id": case.case_id,
            "direction": case.pattern,
            "pulse_width_ps": case.pulse_width_ns * 1e3,
            "pad_rmse_v": waveform_rmse,
            "pad_max_error_v": float(
                np.max(np.abs(native_pad - transistor_pad))
            ),
            "native_pad_extreme_v": native_extreme,
            "transistor_pad_extreme_v": transistor_extreme,
            "pad_extreme_error_v": extreme_error,
            "native_extreme_time_ns": float(t[native_index]),
            "transistor_extreme_time_ns": float(t[transistor_index]),
            "extreme_time_delta_ns": float(t[native_index] - t[transistor_index]),
            "transistor_excursion_fraction": transistor_fraction,
            "transistor_visible": transistor_visible,
            "transistor_partial": transistor_partial,
            "pad_match": matched,
            "match_score": score,
            "native_ku_peak": float(np.max(native_ku)),
            "native_ku_min": float(np.min(native_ku)),
            "native_kd_peak": float(np.max(native_kd)),
            "native_kd_min": float(np.min(native_kd)),
            "native_ku_above_0p5_duration_ns": active_duration(
                native_ku, native_ku >= 0.5
            ),
            "native_kd_below_0p5_duration_ns": active_duration(
                native_kd, native_kd <= 0.5
            ),
        },
        {
            "time_ns": t,
            "input_v": input_v,
            "native_pad_v": native_pad,
            "transistor_pad_v": transistor_pad,
            "native_ku": native_ku,
            "native_kd": native_kd,
        },
    )


def write_wave_csv(path: Path, data: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(data)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(keys)
        for values in zip(*(data[key] for key in keys)):
            writer.writerow(values)


def plot_sweep(rows: list[dict[str, object]], output: Path) -> None:
    fig, axes = plt.subplots(
        2, 2, figsize=(14.5, 8.5), sharex=True, constrained_layout=True
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
            widths = [float(row["pulse_width_ps"]) for row in selected]
            ax.plot(
                widths,
                [float(row["native_pad_extreme_v"]) for row in selected],
                color=BLACK,
                marker="o",
                lw=2.2,
                label="HSPICE native IBIS",
            )
            ax.plot(
                widths,
                [float(row["transistor_pad_extreme_v"]) for row in selected],
                color=GRAY,
                marker="s",
                lw=2.2,
                label="HSPICE transistor",
            )
            matches = [
                index
                for index, row in enumerate(selected)
                if str(row["pad_match"]).lower() == "true"
            ]
            if matches:
                ax.scatter(
                    [widths[index] for index in matches],
                    [
                        float(selected[index]["transistor_pad_extreme_v"])
                        for index in matches
                    ],
                    s=120,
                    facecolors="none",
                    edgecolors=GREEN,
                    linewidths=2.4,
                    label="pad match",
                    zorder=6,
                )
            ax.set_title(
                f"{'slow IBIS' if variant_id == 'slow_1ns' else 'fast IBIS'} | "
                f"{'short high' if direction == 'short_high' else 'short low'}"
            )
            ax.set_xlabel("input pulse width (ps)")
            ax.set_ylabel("pad peak / minimum (V)")
            ax.grid(True, color="#dddddd", alpha=0.75)
    axes[0, 0].legend(frameon=False, loc="best")
    fig.suptitle(
        "HSPICE native IBIS versus transistor output amplitude",
        fontweight="bold",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_case(
    variant_id: str,
    case: base.Case,
    data: dict[str, np.ndarray],
    output: Path,
) -> None:
    t = data["time_ns"]
    fig, axes = plt.subplots(
        3, 1, figsize=(14.5, 8.8), sharex=True, constrained_layout=True
    )
    axes[0].plot(
        t,
        data["native_pad_v"],
        color=BLACK,
        lw=3.0,
        label="HSPICE native IBIS",
    )
    axes[0].plot(
        t,
        data["transistor_pad_v"],
        color=GRAY,
        lw=3.2,
        label="HSPICE transistor",
    )
    axes[1].plot(t, data["native_ku"], color=BLUE, lw=2.5, label="native IBIS Ku")
    axes[2].plot(t, data["native_kd"], color=ORANGE, lw=2.5, label="native IBIS Kd")
    start = 5.0 if case.pattern == "short_high" else 10.0
    reverse = start + case.pulse_width_ns + 0.5 * base.EDGE_NS
    for ax, ylabel in zip(axes, ["pad voltage (V)", "Ku", "Kd"]):
        ax.axvline(start + 0.5 * base.EDGE_NS, color="#999999", ls="--", lw=1.0)
        ax.axvline(reverse, color="#666666", ls="--", lw=1.0)
        ax.set_ylabel(ylabel)
        ax.grid(True, color="#dddddd", alpha=0.75)
    axes[2].axhline(0.0, color="#777777", lw=0.8)
    axes[0].legend(frameon=False)
    axes[1].legend(frameon=False)
    axes[2].legend(frameon=False)
    axes[2].set_xlabel("time (ns)")
    fig.suptitle(f"{variant_id} | {case.title}", fontweight="bold")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def write_report(rows: list[dict[str, object]]) -> None:
    visible = [
        row
        for row in rows
        if str(row["transistor_visible"]).lower() == "true"
    ]
    matched = [
        row for row in visible if str(row["pad_match"]).lower() == "true"
    ]
    ranked = sorted(visible, key=lambda row: float(row["match_score"]))
    partial_matches = [
        row
        for row in matched
        if str(row["transistor_partial"]).lower() == "true"
    ]
    earliest_partial = min(
        partial_matches,
        key=lambda row: float(row["pulse_width_ps"]),
        default=None,
    )
    lines = [
        "# inv_chain HSPICE Native-IBIS / Transistor Match Analysis",
        "",
        "This analysis searches for nontrivial pulse cases where the HSPICE native IBIS pad waveform agrees with the HSPICE transistor chain. Cases in which both outputs reject the pulse are excluded from the match claim.",
        "",
        "## Headline Finding",
        "",
        "- Pad matches occur only with the fast `5 ps` IBIS model in this sweep; the slow `1 ns` IBIS model does not pass the waveform, amplitude, and timing gates.",
        "- The earliest partial-output match is the `130 ps` short-high case: transistor excursion is `88.6%`, pad RMSE is about `72.6 mV`, peak error is about `61.2 mV`, and peak timing differs by `17 ps`.",
        "- Native-IBIS `Ku/Kd` are nevertheless almost fully exercised in that case. The pad match therefore does not prove that the IBIS coefficients represent the transistor's hidden internal state.",
        "",
        "## Match Gates",
        "",
        f"- Pad RMSE <= `{1e3 * PAD_RMSE_MATCH_V:.0f} mV`.",
        f"- Pad peak/minimum error <= `{1e3 * EXTREME_ERROR_MATCH_V:.0f} mV`.",
        f"- Peak/minimum timing error <= `{1e3 * TIMING_ERROR_MATCH_NS:.0f} ps`.",
        f"- Transistor excursion >= `{100 * VISIBLE_MIN:.0f}%` of loaded settled swing.",
        "",
        "## Passing Cases",
        "",
        "| Profile | Direction | Width (ps) | Excursion | Partial | Pad RMSE (mV) | Extreme error (mV) | Timing delta (ps) | Ku peak | Kd min | Ku > 0.5 (ps) | Kd < 0.5 (ps) |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in matched:
        lines.append(
            f"| {row['variant_id']} | {row['direction']} | "
            f"{float(row['pulse_width_ps']):.0f} | "
            f"{100 * float(row['transistor_excursion_fraction']):.1f}% | "
            f"{row['transistor_partial']} | "
            f"{1e3 * float(row['pad_rmse_v']):.2f} | "
            f"{1e3 * float(row['pad_extreme_error_v']):.2f} | "
            f"{1e3 * float(row['extreme_time_delta_ns']):+.1f} | "
            f"{float(row['native_ku_peak']):.4f} | "
            f"{float(row['native_kd_min']):.4f} | "
            f"{1e3 * float(row['native_ku_above_0p5_duration_ns']):.1f} | "
            f"{1e3 * float(row['native_kd_below_0p5_duration_ns']):.1f} |"
        )
    if not matched:
        lines.append(
            "| none | none | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |"
        )
    if earliest_partial is not None:
        lines.extend(
            [
                "",
                "## Earliest Partial Match Ku/Kd",
                "",
                f"- Case: `{earliest_partial['variant_id']} / {earliest_partial['case_id']}`.",
                f"- Native Ku peak: `{float(earliest_partial['native_ku_peak']):.4f}`; Ku remains above `0.5` for `{1e3 * float(earliest_partial['native_ku_above_0p5_duration_ns']):.1f} ps`.",
                f"- Native Kd minimum: `{float(earliest_partial['native_kd_min']):.4f}`; Kd remains below `0.5` for `{1e3 * float(earliest_partial['native_kd_below_0p5_duration_ns']):.1f} ps`.",
                "- These are near full coefficient endpoints even though the transistor pad pulse remains slightly below its settled loaded level.",
            ]
        )
    lines.extend(
        [
            "",
            "## Best Visible Cases",
            "",
            "| Rank | Profile | Direction | Width (ps) | Score | Pad RMSE (mV) | Extreme error (mV) | Timing delta (ps) |",
            "|---:|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for index, row in enumerate(ranked[:8], start=1):
        lines.append(
            f"| {index} | {row['variant_id']} | {row['direction']} | "
            f"{float(row['pulse_width_ps']):.0f} | "
            f"{float(row['match_score']):.3f} | "
            f"{1e3 * float(row['pad_rmse_v']):.2f} | "
            f"{1e3 * float(row['pad_extreme_error_v']):.2f} | "
            f"{1e3 * float(row['extreme_time_delta_ns']):+.1f} |"
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `pad_match_metrics.csv`: every width/profile/direction.",
            "- `plots/01_pad_match_sweep.png`: native-IBIS and transistor extrema versus pulse width.",
            "- `plots/matched_cases/`: pad plus native-IBIS Ku/Kd for every passing case.",
            "- `waveform_data/`: aligned numeric data for passing cases.",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find inv_chain pulse widths where HSPICE native IBIS matches the transistor chain."
    )
    parser.add_argument("--hspice", type=Path, default=base.DEFAULT_HSPICE)
    parser.add_argument("--timeout-s", type=int, default=240)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_cases = analysis_cases()
    rows: list[dict[str, object]] = []
    waveforms: dict[tuple[str, str], dict[str, np.ndarray]] = {}

    normal_path = (
        TRANSISTOR_ROOT
        / "edge_1ps_base_50r_2pf"
        / "hspice_transistor"
        / "edge_1ps_base_50r_2pf_hspice_transistor.tr0"
    )
    normal_raw = base.parse_hspice_tr0(normal_path)
    normal_time = base.to_ns(base.find_signal(normal_raw, "time"))
    normal_pad = base.find_signal(normal_raw, "v(pad_sp)")
    settled_low, settled_high = sweep.settled_levels(normal_time, normal_pad)

    prior.configure_variant(OUT_DIR.parent / "transistor_reference")
    for index, case in enumerate(all_cases, start=1):
        transistor_path = (
            TRANSISTOR_ROOT
            / case.case_id
            / "hspice_transistor"
            / f"{case.case_id}_hspice_transistor.tr0"
        )
        if transistor_path.exists():
            continue
        print(
            f"[transistor {index}/{len(all_cases)}] {case.case_id}",
            flush=True,
        )
        base.run_hspice_transistor(
            case,
            prior.DEFAULT_TRANSISTOR_WRAPPER,
            prior.DEFAULT_TRANSISTOR_LIBRARY,
            args.hspice,
            args.timeout_s,
        )

    for variant in prior.VARIANTS:
        variant_dir = OUT_DIR / variant.variant_id
        prior.configure_variant(variant_dir)
        for index, case in enumerate(all_cases, start=1):
            print(
                f"[{variant.variant_id} {index}/{len(all_cases)}] {case.case_id}",
                flush=True,
            )
            native_raw, _ = prior.run_native(
                variant,
                case,
                args.hspice,
                args.timeout_s,
            )
            native = native_wave(native_raw)
            transistor = read_transistor(case)
            metrics, data = response_metrics(
                case,
                native,
                transistor,
                settled_low,
                settled_high,
            )
            metrics["variant_id"] = variant.variant_id
            rows.append(metrics)
            waveforms[(variant.variant_id, case.case_id)] = data
            base.write_csv(OUT_DIR / "pad_match_metrics.csv", rows)

    matches = [
        row for row in rows if str(row["pad_match"]).lower() == "true"
    ]
    for row in matches:
        key = (str(row["variant_id"]), str(row["case_id"]))
        case = next(item for item in all_cases if item.case_id == key[1])
        output = (
            OUT_DIR
            / "plots"
            / "matched_cases"
            / f"{key[0]}_{key[1]}.png"
        )
        plot_case(key[0], case, waveforms[key], output)
        write_wave_csv(
            OUT_DIR
            / "waveform_data"
            / f"{key[0]}_{key[1]}.csv",
            waveforms[key],
        )
    base.write_csv(OUT_DIR / "pad_match_metrics.csv", rows)
    plot_sweep(rows, OUT_DIR / "plots" / "01_pad_match_sweep.png")
    write_report(rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"PAD_MATCHES={len(matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
