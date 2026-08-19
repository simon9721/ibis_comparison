from __future__ import annotations

import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0  # noqa: E402


OLD_STUDY = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
CORRECT_STUDY = (
    ROOT / "results" / "io_buf_correct_hspice_reference_waveforms_2026-07-23"
)
OUT = (
    ROOT
    / "results"
    / "ibis_kukd_handwritten_notes_deck"
    / "hspice_slow_fast_transistor_comparison"
    / "short_pulse_cases"
)
PLOTS = OUT / "plots"

SLOW_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
FAST_IBIS = (
    ROOT
    / "results"
    / "io_buf_fast_edge_retest_2026-06-05"
    / "source"
    / "io_buf.ibs"
)
TRANSISTOR = ROOT / "models" / "io_buf.sp"
TRANSISTOR_MODEL = ROOT.parent / "s2ibispy" / "tests" / "hspice.mod"

FLOWS = ["old_slow_ibis", "fast_5ps_ibis", "source_transistor"]
LABELS = {
    "old_slow_ibis": "HSPICE IBIS: old slow-characterized file",
    "fast_5ps_ibis": "HSPICE IBIS: regenerated 5 ps file",
    "source_transistor": "HSPICE transistor: io_buf.sp",
}
COLORS = {
    "old_slow_ibis": "#E67E22",
    "fast_5ps_ibis": "#008F83",
    "source_transistor": "#151515",
}
WIDTHS = {
    "old_slow_ibis": 3.5,
    "fast_5ps_ibis": 6.0,
    "source_transistor": 3.0,
}


@dataclass(frozen=True)
class Case:
    case_id: str
    label: str
    pulse_kind: str
    first_edge_ns: float
    reverse_edge_ns: float
    xlim: tuple[float, float]
    ylim: tuple[float, float]
    metric_window: tuple[float, float]


CASES = [
    Case(
        "short_pulse_1ns_high",
        "1 ns high pulse",
        "high",
        5.0,
        6.0,
        (4.5, 12.5),
        (-0.06, 0.13),
        (4.5, 12.5),
    ),
    Case(
        "short_pulse_2ns_high",
        "2 ns high pulse",
        "high",
        5.0,
        7.0,
        (4.5, 13.5),
        (-0.08, 1.08),
        (4.5, 13.5),
    ),
    Case(
        "short_pulse_1ns_low",
        "1 ns low pulse after settled high",
        "low",
        10.0,
        11.0,
        (9.0, 17.5),
        (-0.08, 1.68),
        (9.0, 17.5),
    ),
    Case(
        "short_pulse_2ns_low",
        "2 ns low pulse after settled high",
        "low",
        10.0,
        12.0,
        (9.0, 18.0),
        (-0.08, 1.68),
        (9.0, 18.0),
    ),
]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def paths_for(case: Case) -> dict[str, dict[str, Path]]:
    old_dir = OLD_STUDY / "cases" / case.case_id / "hspice_native_ibis"
    correct_case = CORRECT_STUDY / "cases" / case.case_id
    old_stem = f"{case.case_id}_hspice_native_ibis"
    return {
        "old_slow_ibis": {
            "deck": old_dir / f"{old_stem}.sp",
            "tr0": old_dir / f"{old_stem}.tr0",
            "lis": old_dir / f"{old_stem}.lis",
        },
        "fast_5ps_ibis": {
            "deck": correct_case / "hspice_native_fast_ibis" / "run.sp",
            "tr0": correct_case / "hspice_native_fast_ibis" / "run.tr0",
            "lis": correct_case / "hspice_native_fast_ibis" / "run.lis",
        },
        "source_transistor": {
            "deck": correct_case / "hspice_transistor_original" / "run.sp",
            "tr0": correct_case / "hspice_transistor_original" / "run.tr0",
            "lis": correct_case / "hspice_transistor_original" / "run.lis",
        },
    }


def load_case(case: Case) -> dict[str, dict[str, np.ndarray]]:
    result: dict[str, dict[str, np.ndarray]] = {}
    for flow, artifacts in paths_for(case).items():
        parsed = parse_hspice_tr0(artifacts["tr0"])
        pad_key = "v(pad_ibis)" if "v(pad_ibis)" in parsed else "v(pad)"
        result[flow] = {
            "time_ns": np.asarray(parsed["time"], dtype=float) * 1e9,
            "input_v": np.asarray(parsed["v(in_dig)"], dtype=float),
            "pad_v": np.asarray(parsed[pad_key], dtype=float),
        }
    return result


def interp(
    waveform: dict[str, np.ndarray],
    grid_ns: np.ndarray,
    signal: str = "pad_v",
) -> np.ndarray:
    return np.interp(grid_ns, waveform["time_ns"], waveform[signal])


def style_axis(ax: plt.Axes) -> None:
    ax.grid(True, color="#D7D7D7", linewidth=0.8, alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=12)


def plot_case(case: Case, waveforms: dict[str, dict[str, np.ndarray]]) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=180)
    ax.axvspan(
        case.first_edge_ns,
        case.reverse_edge_ns,
        color="#E6E6E6",
        alpha=0.65,
        zorder=0,
    )
    for flow in FLOWS:
        wave = waveforms[flow]
        ax.plot(
            wave["time_ns"],
            wave["pad_v"],
            color=COLORS[flow],
            linewidth=WIDTHS[flow],
            label=LABELS[flow],
            zorder=4 if flow == "source_transistor" else 3,
        )
    for edge, text in [
        (case.first_edge_ns, "first edge"),
        (case.reverse_edge_ns, "reverse edge"),
    ]:
        ax.axvline(edge, color="#777777", linewidth=1.5, linestyle="--", zorder=2)
        ax.text(
            edge,
            case.ylim[1] - 0.04 * (case.ylim[1] - case.ylim[0]),
            text,
            rotation=90,
            ha="right",
            va="top",
            fontsize=10,
            color="#555555",
        )
    pulse_text = "input high" if case.pulse_kind == "high" else "input low"
    ax.text(
        0.5 * (case.first_edge_ns + case.reverse_edge_ns),
        case.ylim[0] + 0.04 * (case.ylim[1] - case.ylim[0]),
        pulse_text,
        ha="center",
        va="bottom",
        fontsize=11,
        color="#555555",
    )
    ax.set_xlim(*case.xlim)
    ax.set_ylim(*case.ylim)
    ax.set_xlabel("time (ns)", fontsize=14)
    ax.set_ylabel("pad voltage (V)", fontsize=14)
    ax.set_title(
        f"{case.label}: same HSPICE bench, three source models",
        fontsize=18,
        fontweight="bold",
        loc="left",
    )
    style_axis(ax)
    ax.legend(
        loc="upper right",
        frameon=True,
        fontsize=11,
    )
    fig.tight_layout()
    index = CASES.index(case) + 1
    fig.savefig(
        PLOTS / f"{index:02d}_{case.case_id}_pad_overlay.png",
        bbox_inches="tight",
    )
    plt.close(fig)


def crossing_time(
    time_ns: np.ndarray,
    values: np.ndarray,
    level: float,
    start_ns: float,
    rising: bool,
) -> float:
    mask = time_ns >= start_ns
    t = time_ns[mask]
    y = values[mask]
    if rising:
        indices = np.where((y[:-1] < level) & (y[1:] >= level))[0]
    else:
        indices = np.where((y[:-1] > level) & (y[1:] <= level))[0]
    if indices.size == 0:
        return float("nan")
    index = int(indices[0])
    y0 = y[index]
    y1 = y[index + 1]
    if y1 == y0:
        return float(t[index])
    return float(t[index] + (level - y0) * (t[index + 1] - t[index]) / (y1 - y0))


def calculate_metrics(
    case: Case,
    waveforms: dict[str, dict[str, np.ndarray]],
) -> list[dict[str, float | str]]:
    grid_ns = np.arange(case.metric_window[0], case.metric_window[1] + 0.0005, 0.001)
    aligned = {flow: interp(waveforms[flow], grid_ns) for flow in FLOWS}
    reference = aligned["source_transistor"]
    rows: list[dict[str, float | str]] = []
    for flow in FLOWS:
        values = aligned[flow]
        peak_index = int(np.argmax(values))
        min_index = int(np.argmin(values))
        rmse_mv = 1000.0 * float(np.sqrt(np.mean((values - reference) ** 2)))
        max_error_mv = 1000.0 * float(np.max(np.abs(values - reference)))
        recovery_t50_ns = float("nan")
        recovery_delay_ns = float("nan")
        if case.pulse_kind == "low":
            raw = waveforms[flow]
            pre_mask = (raw["time_ns"] >= case.first_edge_ns - 1.0) & (
                raw["time_ns"] <= case.first_edge_ns - 0.2
            )
            recovery_mask = (raw["time_ns"] >= case.first_edge_ns) & (
                raw["time_ns"] <= case.metric_window[1]
            )
            high_value = float(np.median(raw["pad_v"][pre_mask]))
            minimum = float(np.min(raw["pad_v"][recovery_mask]))
            level = 0.5 * (high_value + minimum)
            recovery_t50_ns = crossing_time(
                raw["time_ns"],
                raw["pad_v"],
                level,
                case.reverse_edge_ns,
                True,
            )
            recovery_delay_ns = recovery_t50_ns - case.reverse_edge_ns
        rows.append(
            {
                "case_id": case.case_id,
                "case_label": case.label,
                "flow": flow,
                "flow_label": LABELS[flow],
                "rmse_vs_transistor_mv": rmse_mv,
                "max_error_vs_transistor_mv": max_error_mv,
                "pad_peak_v": float(values[peak_index]),
                "pad_peak_time_ns": float(grid_ns[peak_index]),
                "pad_min_v": float(values[min_index]),
                "pad_min_time_ns": float(grid_ns[min_index]),
                "recovery_t50_ns": recovery_t50_ns,
                "recovery_delay_from_reverse_ns": recovery_delay_ns,
            }
        )
    return rows


def plot_rmse_summary(metric_rows: list[dict[str, float | str]]) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=180)
    x = np.arange(len(CASES))
    width = 0.34
    for index, flow in enumerate(["old_slow_ibis", "fast_5ps_ibis"]):
        values = [
            float(
                next(
                    row["rmse_vs_transistor_mv"]
                    for row in metric_rows
                    if row["case_id"] == case.case_id and row["flow"] == flow
                )
            )
            for case in CASES
        ]
        bars = ax.bar(
            x + (index - 0.5) * width,
            values,
            width,
            color=COLORS[flow],
            label=LABELS[flow],
        )
        for bar, value in zip(bars, values, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 8,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
                color=COLORS[flow],
            )
    ax.set_xticks(
        x,
        ["1 ns high", "2 ns high", "1 ns low", "2 ns low"],
        fontsize=13,
    )
    ax.set_ylabel("pad RMSE versus source transistor (mV)", fontsize=14)
    ax.set_title(
        "Fast-edge regeneration does not solve every interrupted transition",
        fontsize=18,
        fontweight="bold",
        loc="left",
    )
    style_axis(ax)
    ax.legend(loc="upper left", frameon=True, fontsize=11)
    fig.tight_layout()
    fig.savefig(PLOTS / "05_short_pulse_rmse_summary.png", bbox_inches="tight")
    plt.close(fig)


def plot_low_recovery(metric_rows: list[dict[str, float | str]]) -> None:
    low_cases = ["short_pulse_1ns_low", "short_pulse_2ns_low"]
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=180)
    x = np.arange(len(low_cases))
    width = 0.25
    all_values: list[float] = []
    for index, flow in enumerate(FLOWS):
        values = [
            float(
                next(
                    row["recovery_delay_from_reverse_ns"]
                    for row in metric_rows
                    if row["case_id"] == case_id and row["flow"] == flow
                )
            )
            for case_id in low_cases
        ]
        all_values.extend(values)
        bars = ax.bar(
            x + (index - 1) * width,
            values,
            width,
            color=COLORS[flow],
            label=LABELS[flow],
        )
        for bar, value_ns in zip(bars, values, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value_ns + 0.04,
                f"{value_ns:.3f}",
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
                color=COLORS[flow],
            )
    ax.set_xticks(x, ["1 ns low", "2 ns low"], fontsize=13)
    ax.set_ylabel("pad 50% recovery delay after reverse edge (ns)", fontsize=14)
    ax.set_title(
        "Short-low recovery: regenerated IBIS returns too early",
        fontsize=18,
        fontweight="bold",
        loc="left",
    )
    ax.set_ylim(0, max(all_values) * 1.25)
    style_axis(ax)
    ax.legend(loc="upper left", frameon=True, fontsize=10)
    fig.tight_layout()
    fig.savefig(PLOTS / "06_short_low_recovery_timing.png", bbox_inches="tight")
    plt.close(fig)


def write_aligned_waveforms(
    all_waveforms: dict[str, dict[str, dict[str, np.ndarray]]]
) -> None:
    fields = [
        "case_id",
        "time_ns",
        "input_v",
        "old_slow_ibis_pad_v",
        "fast_5ps_ibis_pad_v",
        "source_transistor_pad_v",
    ]
    with (OUT / "aligned_short_pulse_waveforms.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in CASES:
            waveforms = all_waveforms[case.case_id]
            stop_ns = min(
                case.metric_window[1],
                *(float(waveforms[flow]["time_ns"][-1]) for flow in FLOWS),
            )
            grid_ns = np.arange(case.metric_window[0], stop_ns + 0.0005, 0.001)
            aligned_pad = {
                flow: interp(waveforms[flow], grid_ns) for flow in FLOWS
            }
            aligned_input = interp(
                waveforms["source_transistor"], grid_ns, "input_v"
            )
            for index, time_ns in enumerate(grid_ns):
                writer.writerow(
                    {
                        "case_id": case.case_id,
                        "time_ns": float(time_ns),
                        "input_v": float(aligned_input[index]),
                        "old_slow_ibis_pad_v": float(
                            aligned_pad["old_slow_ibis"][index]
                        ),
                        "fast_5ps_ibis_pad_v": float(
                            aligned_pad["fast_5ps_ibis"][index]
                        ),
                        "source_transistor_pad_v": float(
                            aligned_pad["source_transistor"][index]
                        ),
                    }
                )


def write_metric_csv(metric_rows: list[dict[str, float | str]]) -> None:
    fields = list(metric_rows[0])
    with (OUT / "short_pulse_metrics.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(metric_rows)


def write_reference_manifest() -> None:
    with (CORRECT_STUDY / "reference_cache_manifest.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        correct_sources = {
            (row["case_id"], row["flow"]): row["source"]
            for row in csv.DictReader(handle)
        }
    fields = [
        "case_id",
        "flow",
        "source",
        "deck",
        "deck_sha256",
        "tr0",
        "tr0_sha256",
        "lis",
    ]
    with (OUT / "reference_manifest.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in CASES:
            for flow, artifacts in paths_for(case).items():
                writer.writerow(
                    {
                        "case_id": case.case_id,
                        "flow": flow,
                        "source": (
                            "preexisting_cache"
                            if flow == "old_slow_ibis"
                            else correct_sources[
                                (
                                    case.case_id,
                                    (
                                        "hspice_native_fast_ibis"
                                        if flow == "fast_5ps_ibis"
                                        else "hspice_transistor_original"
                                    ),
                                )
                            ]
                        ),
                        "deck": artifacts["deck"],
                        "deck_sha256": sha256(artifacts["deck"]),
                        "tr0": artifacts["tr0"],
                        "tr0_sha256": sha256(artifacts["tr0"]),
                        "lis": artifacts["lis"],
                    }
                )


def value(
    metric_rows: list[dict[str, float | str]],
    case_id: str,
    flow: str,
    field: str,
) -> float:
    return float(
        next(
            row[field]
            for row in metric_rows
            if row["case_id"] == case_id and row["flow"] == flow
        )
    )


def write_readme(metric_rows: list[dict[str, float | str]]) -> None:
    lines = [
        "# HSPICE short-pulse comparison: slow IBIS, fast IBIS, transistor",
        "",
        "Existing HSPICE references were restored from cache. For the newly added",
        "`short_pulse_2ns_low` case, the regenerated-IBIS and original-transistor",
        "references were simulated once; the old slow-IBIS result was reused.",
        "",
        "## Common bench",
        "",
        "- All three candidates run in HSPICE.",
        "- Ideal `3.3 V` supply and enable.",
        "- Runtime command rise/fall time: `1 ps`.",
        "- Direct output load: `50 ohm` to ground in parallel with `2 pF` external capacitance.",
        "- Both IBIS files contain typical `C_comp = 1.2 pF`.",
        "- Temperature: `27 C`.",
        "- No channel or transmission line.",
        "",
        "## Cases",
        "",
        "- `short_pulse_1ns_high`: high command from `5 ns` to `6 ns`.",
        "- `short_pulse_2ns_high`: high command from `5 ns` to `7 ns`.",
        "- `short_pulse_1ns_low`: settled high, then low command from `10 ns` to `11 ns`.",
        "- `short_pulse_2ns_low`: settled high, then low command from `10 ns` to `12 ns`.",
        "",
        "## Pad results",
        "",
        "| Case | Flow | RMSE vs transistor | Peak | Minimum | Recovery delay after reverse |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for case in CASES:
        for flow in FLOWS:
            rmse = value(metric_rows, case.case_id, flow, "rmse_vs_transistor_mv")
            peak = value(metric_rows, case.case_id, flow, "pad_peak_v")
            minimum = value(metric_rows, case.case_id, flow, "pad_min_v")
            recovery = value(
                metric_rows,
                case.case_id,
                flow,
                "recovery_delay_from_reverse_ns",
            )
            recovery_text = "n/a" if np.isnan(recovery) else f"{recovery:.3f} ns"
            lines.append(
                f"| {case.label} | {LABELS[flow]} | {rmse:.1f} mV | "
                f"{peak:.4f} V | {minimum:.4f} V | {recovery_text} |"
            )
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "- The regenerated 5 ps IBIS is the correct complete-edge source-correlation pair, but that does not guarantee transistor-equivalent interrupted switching.",
            "- For the `1 ns high` pulse, all outputs are small. The transistor peaks earlier and higher than either IBIS result, so small absolute voltage error is not proof of matching internal history.",
            "- For the `2 ns high` pulse, regenerated IBIS is closer to the transistor than the old IBIS in both peak amplitude and overall waveform.",
            "- For the `1 ns low` pulse, regenerated IBIS recovers far too early. The old slow IBIS happens to be closer in recovery timing, but this comes from its stored complete-edge delay and should not be interpreted as a generally correct short-pulse model.",
            "- For the `2 ns low` pulse, regenerated IBIS remains early while the old slow IBIS becomes late relative to the transistor. Neither fixed complete-edge replay captures the width-dependent recovery law.",
            "- Slow versus fast IBIS still have identical static drive strength; these differences are entirely dynamic.",
            "",
            "## Figures",
            "",
            "- `plots/01_short_pulse_1ns_high_pad_overlay.png`",
            "- `plots/02_short_pulse_2ns_high_pad_overlay.png`",
            "- `plots/03_short_pulse_1ns_low_pad_overlay.png`",
            "- `plots/04_short_pulse_2ns_low_pad_overlay.png`",
            "- `plots/05_short_pulse_rmse_summary.png`",
            "- `plots/06_short_low_recovery_timing.png`",
            "- `plots/contact_sheet.png`",
            "",
            "## Numeric data",
            "",
            "- `short_pulse_metrics.csv`",
            "- `aligned_short_pulse_waveforms.csv`",
            "- `reference_manifest.csv`",
            "",
            "## Model sources",
            "",
            f"- Old IBIS: `{SLOW_IBIS}` (`{sha256(SLOW_IBIS)}`).",
            f"- Regenerated IBIS: `{FAST_IBIS}` (`{sha256(FAST_IBIS)}`).",
            f"- Transistor: `{TRANSISTOR}` with `{TRANSISTOR_MODEL}`.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_contact_sheet() -> None:
    names = [
        "01_short_pulse_1ns_high_pad_overlay.png",
        "02_short_pulse_2ns_high_pad_overlay.png",
        "03_short_pulse_1ns_low_pad_overlay.png",
        "04_short_pulse_2ns_low_pad_overlay.png",
        "05_short_pulse_rmse_summary.png",
        "06_short_low_recovery_timing.png",
    ]
    fig, axes = plt.subplots(3, 2, figsize=(16, 13.5), dpi=140)
    for ax in axes.flat:
        ax.axis("off")
    for ax, name in zip(axes.flat, names):
        image = plt.imread(PLOTS / name)
        ax.imshow(image)
        ax.set_title(name.removesuffix(".png"), fontsize=12, loc="left")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(PLOTS / "contact_sheet.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    all_waveforms: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    metric_rows: list[dict[str, float | str]] = []
    for case in CASES:
        waveforms = load_case(case)
        all_waveforms[case.case_id] = waveforms
        plot_case(case, waveforms)
        metric_rows.extend(calculate_metrics(case, waveforms))
    plot_rmse_summary(metric_rows)
    plot_low_recovery(metric_rows)
    write_metric_csv(metric_rows)
    write_aligned_waveforms(all_waveforms)
    write_reference_manifest()
    write_readme(metric_rows)
    make_contact_sheet()
    print(OUT)


if __name__ == "__main__":
    main()
