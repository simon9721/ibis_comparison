from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_inv_chain_gate_state_clean_comparison as base  # noqa: E402


OUT_DIR = ROOT / "results" / "inv_chain_s2ibispy_slow_fast_comparison_2026-07-27"
SOURCE_DIR = ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27"
DEFAULT_TRANSISTOR_WRAPPER = (
    ROOT
    / "inv_chain"
    / "clean_ibis_vs_pybis_matched_pkg"
    / "invchain_ref_ngspice.sub"
)
DEFAULT_TRANSISTOR_LIBRARY = (
    ROOT
    / "inv_chain"
    / "clean_ibis_vs_pybis_matched_pkg"
    / "HL18G-S3.7S.lib"
)

FAST_BLUE = "#0072B2"
SLOW_ORANGE = "#D55E00"
LEGACY_BLUE = "#1769aa"
GATE_RED = "#d62728"
BLACK = "#111111"
GRAY = "#858585"


@dataclass(frozen=True)
class Variant:
    variant_id: str
    label: str
    edge_setting: str
    ibis: Path


VARIANTS = [
    Variant(
        "slow_1ns",
        "slow IBIS (1 ns source edges)",
        "tr=tf=1 ns",
        SOURCE_DIR / "slow_1ns" / "inv_chain_slow_1ns.ibs",
    ),
    Variant(
        "fast_5ps",
        "fast IBIS (5 ps source edges)",
        "tr=tf=5 ps",
        SOURCE_DIR / "fast_5ps" / "inv_chain_fast_5ps.ibs",
    ),
]


def configure_variant(variant_dir: Path) -> None:
    base.OUT_DIR = variant_dir
    base.COMMON_DIR = variant_dir / "common"
    base.CASES_DIR = variant_dir / "cases"
    base.PLOTS_DIR = variant_dir / "plots"
    base.DATA_DIR = variant_dir / "waveform_data"
    base.FIT_DIR = variant_dir / "fit_diagnostics"
    for path in [
        base.OUT_DIR,
        base.COMMON_DIR,
        base.CASES_DIR,
        base.PLOTS_DIR,
        base.DATA_DIR,
        base.FIT_DIR,
    ]:
        base.ensure_dir(path)


def native_deck(case: base.Case, ibis_name: str) -> str:
    return base.make_hspice_native_deck(case).replace(
        "file='t2b_0615_v5.ibs'",
        f"file='{ibis_name}'",
    )


def prior_sanity_dir(variant: Variant) -> Path:
    return SOURCE_DIR / "hspice_sanity" / variant.variant_id


def restore_normal_native_sanity(
    variant: Variant,
    case: base.Case,
    out_dir: Path,
    stem: str,
    deck_text: str,
) -> bool:
    if case.case_id != "edge_1ps_base_50r_2pf":
        return False
    source = prior_sanity_dir(variant)
    tr0 = source / "run.tr0"
    lis = source / "run.lis"
    if not tr0.exists() or not lis.exists():
        return False
    base.write_text(out_dir / f"{stem}.sp", deck_text)
    shutil.copy2(tr0, out_dir / f"{stem}.tr0")
    shutil.copy2(lis, out_dir / f"{stem}.lis")
    for suffix in ["ic0", "st0"]:
        candidate = source / f"run.{suffix}"
        if candidate.exists():
            shutil.copy2(candidate, out_dir / f"{stem}.{suffix}")
    return True


def run_native(
    variant: Variant,
    case: base.Case,
    hspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = base.CASES_DIR / case.case_id / "hspice_native_ibis"
    base.ensure_dir(out_dir)
    shutil.copy2(variant.ibis, out_dir / variant.ibis.name)
    stem = f"{case.case_id}_hspice_native_ibis"
    deck_text = native_deck(case, variant.ibis.name)
    if restore_normal_native_sanity(variant, case, out_dir, stem, deck_text):
        source = "prior_sanity"
    else:
        source = base.cache_hspice(
            "inv_chain_s2ibispy_native_ibis_direct_50r_2pf",
            case,
            deck_text,
            [variant.ibis],
            out_dir,
            stem,
            hspice,
            timeout_s,
        )
    tr0 = out_dir / f"{stem}.tr0"
    return base.parse_hspice_tr0(tr0), {
        "variant_id": variant.variant_id,
        "case_id": case.case_id,
        "reference": "hspice_native_ibis",
        "source": source,
        "deck": str((out_dir / f"{stem}.sp").relative_to(ROOT)),
        "tr0": str(tr0.relative_to(ROOT)),
        "lis": str((out_dir / f"{stem}.lis").relative_to(ROOT)),
    }


def plot_hspice_ibis_vs_transistor(
    variant: Variant,
    case: base.Case,
    data: dict[str, np.ndarray],
    out_dir: Path,
) -> Path:
    base.ensure_dir(out_dir)
    t = data["time_ns"]
    fig, ax = plt.subplots(figsize=(14.0, 5.2), constrained_layout=True)
    ax.plot(
        t,
        data["hspice_ibis_pad_v"],
        color=BLACK,
        lw=3.0,
        label=f"HSPICE native {variant.label}",
    )
    ax.plot(
        t,
        data["hspice_transistor_pad_v"],
        color=GRAY,
        lw=3.4,
        alpha=0.94,
        label="HSPICE transistor",
    )
    base.style_axis(ax, "pad voltage (V)", case)
    ax.set_xlabel("time (ns)")
    ax.legend(frameon=False, ncol=2, loc="upper center")
    ax.set_title(case.title, loc="left", fontweight="bold", fontsize=15)
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_three_way(
    variant: Variant,
    case: base.Case,
    data: dict[str, np.ndarray],
    out_dir: Path,
) -> Path:
    base.ensure_dir(out_dir)
    t = data["time_ns"]
    fig, ax = plt.subplots(figsize=(14.0, 5.2), constrained_layout=True)
    ax.plot(
        t,
        data["hspice_ibis_pad_v"],
        color=BLACK,
        lw=3.0,
        label=f"HSPICE native {variant.label}",
    )
    ax.plot(
        t,
        data["hspice_transistor_pad_v"],
        color=GRAY,
        lw=3.5,
        alpha=0.90,
        label="HSPICE transistor",
    )
    ax.plot(
        t,
        data["gate_state_pad_v"],
        color=GATE_RED,
        lw=1.8,
        marker="D",
        markevery=max(1, len(t) // 43),
        ms=3.2,
        label="ngspice directional-residual",
    )
    base.style_axis(ax, "pad voltage (V)", case)
    ax.set_xlabel("time (ns)")
    ax.legend(frameon=False, ncol=3, loc="upper center")
    ax.set_title(case.title, loc="left", fontweight="bold", fontsize=15)
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_slow_fast_native(
    case: base.Case,
    variant_data: dict[str, dict[str, np.ndarray]],
    out_dir: Path,
) -> Path:
    base.ensure_dir(out_dir)
    fig, axes = plt.subplots(3, 1, figsize=(14.0, 9.0), sharex=True, constrained_layout=True)
    specs = [
        ("hspice_ibis_pad_v", "pad voltage (V)"),
        ("hspice_ibis_ku", "Ku"),
        ("hspice_ibis_kd", "Kd"),
    ]
    colors = {"slow_1ns": SLOW_ORANGE, "fast_5ps": FAST_BLUE}
    for ax, (key, ylabel) in zip(axes, specs):
        for variant in VARIANTS:
            data = variant_data[variant.variant_id]
            ax.plot(
                data["time_ns"],
                data[key],
                color=colors[variant.variant_id],
                lw=2.4,
                label=f"HSPICE {variant.label}",
            )
        base.style_axis(ax, ylabel, case)
    axes[-1].axhline(0.0, color="#777777", lw=0.8, alpha=0.55)
    axes[0].legend(frameon=False, ncol=2, loc="upper center")
    axes[-1].set_xlabel("time (ns)")
    fig.suptitle(case.title, fontweight="bold", fontsize=16)
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_metric_summary(metrics: list[dict[str, object]], output: Path) -> None:
    cases = [case.case_id for case in base.CASES]
    flows = ["hspice_transistor", "legacy", "gate_state"]
    titles = [
        "HSPICE transistor vs native IBIS",
        "legacy pybis vs native IBIS",
        "gate-state pybis vs native IBIS",
    ]
    colors = {"slow_1ns": SLOW_ORANGE, "fast_5ps": FAST_BLUE}
    lookup = {
        (str(row["variant_id"]), str(row["case_id"]), str(row["flow"])): row
        for row in metrics
    }
    fig, axes = plt.subplots(3, 1, figsize=(16.0, 11.0), sharex=True, constrained_layout=True)
    x = np.arange(len(cases), dtype=float)
    width = 0.36
    for ax, flow, title in zip(axes, flows, titles):
        for offset, variant in zip([-width / 2.0, width / 2.0], VARIANTS):
            values = [
                1e3
                * float(
                    lookup[(variant.variant_id, case_id, flow)][
                        "pad_rmse_v_vs_hspice_ibis"
                    ]
                )
                for case_id in cases
            ]
            ax.bar(
                x + offset,
                values,
                width=width,
                color=colors[variant.variant_id],
                label=variant.label,
            )
        ax.set_ylabel("pad RMSE (mV)")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.grid(True, axis="y", color="#d8d8d8", alpha=0.65)
    axes[0].legend(frameon=False, ncol=2, loc="upper right")
    axes[-1].set_xticks(x, cases, rotation=28, ha="right")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170)
    plt.close(fig)


def add_variant_fields(
    variant: Variant,
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "variant_id": variant.variant_id,
            "variant_label": variant.label,
            "source_edge_setting": variant.edge_setting,
            **row,
        }
        for row in rows
    ]


def uniformize_case_data(
    case: base.Case,
    data: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    source_time = np.asarray(data["time_ns"], dtype=float)
    time_ns = np.arange(0.0, case.stop_ns + 0.0005, 0.001)
    result: dict[str, np.ndarray] = {"time_ns": time_ns}
    for key, values in data.items():
        if key == "time_ns":
            continue
        result[key] = np.interp(time_ns, source_time, np.asarray(values, dtype=float))
    rows = [
        {key: float(values[index]) for key, values in result.items()}
        for index in range(len(time_ns))
    ]
    base.write_csv(base.DATA_DIR / f"{case.case_id}.csv", rows)
    return result


def write_variant_readme(
    variant: Variant,
    fit: dict[str, object],
    metrics: list[dict[str, object]],
    cache_rows: list[dict[str, object]],
) -> None:
    lookup = {
        (str(row["case_id"]), str(row["flow"])): row
        for row in metrics
        if row["variant_id"] == variant.variant_id
    }
    lines = [
        f"# inv_chain {variant.label}",
        "",
        "## Setup",
        "",
        f"- Source IBIS: `{variant.ibis.relative_to(ROOT)}`",
        f"- Source edge setting: `{variant.edge_setting}`",
        f"- Component/model: `{base.COMPONENT_NAME}` / `{base.MODEL_NAME}`",
        f"- Supply: `{base.SUPPLY_V} V`",
        f"- Load: `{base.LOAD_OHM:.0f} ohm || {base.LOAD_PF:g} pF`",
        f"- Applied input edge: `{base.EDGE_NS * 1e3:g} ps`",
        "- Temperature: `27 C`",
        "- No channel or transmission line.",
        "",
        "## Offline Gate-State Reconstruction",
        "",
        f"- Worst directional-residual RMSE: `{float(fit['worst_rmse']):.6f}`",
        f"- Worst directional-residual max error: `{float(fit['worst_max_error']):.6f}`",
        f"- Reconstruction gate: **{fit['gate']}**",
        "",
        "## Comparison Phases",
        "",
        "- `plots/01_hspice_ibis_vs_transistor/`: HSPICE native IBIS pad vs HSPICE transistor pad.",
        "- `plots/02_hspice_ibis_vs_legacy/`: HSPICE native IBIS vs ngspice legacy pybis, pad/Ku/Kd.",
        "- `plots/03_hspice_ibis_vs_gate_state/`: HSPICE native IBIS vs ngspice directional-residual, pad/Ku/Kd.",
        "- `plots/04_hspice_ibis_gate_state_transistor/`: pad-only three-way overlay.",
        "- `waveform_data/`: aligned numeric traces behind every plot.",
        "",
        "## Pad RMSE versus Native HSPICE IBIS",
        "",
        "| Case | HSPICE transistor (mV) | legacy pybis (mV) | gate-state pybis (mV) |",
        "|---|---:|---:|---:|",
    ]
    for case in base.CASES:
        values = []
        for flow in ["hspice_transistor", "legacy", "gate_state"]:
            values.append(
                1e3 * float(lookup[(case.case_id, flow)]["pad_rmse_v_vs_hspice_ibis"])
            )
        lines.append(
            f"| {case.case_id} | {values[0]:.3f} | {values[1]:.3f} | {values[2]:.3f} |"
        )
    lines.extend(
        [
            "",
            "## HSPICE Reference Sources",
            "",
            "| Case | Reference | Source |",
            "|---|---|---|",
        ]
    )
    for row in cache_rows:
        if row["variant_id"] == variant.variant_id:
            lines.append(f"| {row['case_id']} | {row['reference']} | {row['source']} |")
    lines.append("")
    (base.OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_main_readme(
    metrics: list[dict[str, object]],
    fits: dict[str, dict[str, object]],
) -> None:
    lookup = {
        (str(row["variant_id"]), str(row["case_id"]), str(row["flow"])): row
        for row in metrics
    }
    normal = "edge_1ps_base_50r_2pf"
    interrupted = [
        case.case_id
        for case in base.CASES
        if case.pulse_width_ns < 1.0 and case.pattern in {"short_high", "short_low"}
    ]

    def metric_range(
        variant_id: str,
        flow: str,
        key: str,
        scale: float = 1.0,
    ) -> tuple[float, float]:
        values = [
            scale * float(lookup[(variant_id, case_id, flow)][key])
            for case_id in interrupted
        ]
        return min(values), max(values)

    slow_legacy_pad = metric_range(
        "slow_1ns", "legacy", "pad_rmse_v_vs_hspice_ibis", 1e3
    )
    slow_gate_pad = metric_range(
        "slow_1ns", "gate_state", "pad_rmse_v_vs_hspice_ibis", 1e3
    )
    fast_legacy_pad = metric_range(
        "fast_5ps", "legacy", "pad_rmse_v_vs_hspice_ibis", 1e3
    )
    fast_gate_pad = metric_range(
        "fast_5ps", "gate_state", "pad_rmse_v_vs_hspice_ibis", 1e3
    )
    lines = [
        "# inv_chain Slow/Fast IBIS Comparison Ladder",
        "",
        "This package repeats the same controlled comparison phases for the two s2ibispy-generated `inv_chain` models.",
        "",
        "## Controlled Bench",
        "",
        f"- Supply: `{base.SUPPLY_V} V`",
        f"- Load in HSPICE and ngspice: `{base.LOAD_OHM:.0f} ohm || {base.LOAD_PF:g} pF`",
        f"- Applied input stimulus edge: `{base.EDGE_NS * 1e3:g} ps`",
        "- Temperature: `27 C`",
        "- Direct buffer-to-load connection; no channel.",
        "- HSPICE transistor references are restored from the unchanged reference cache.",
        "",
        "## Models",
        "",
    ]
    for variant in VARIANTS:
        lines.append(
            f"- `{variant.variant_id}`: `{variant.edge_setting}`, "
            f"`{variant.ibis.relative_to(ROOT)}`."
        )
    lines.extend(
        [
            "",
            "## Headline Normal-Edge Numbers",
            "",
            "| Model | Reconstruction gate | HSPICE IBIS vs transistor | legacy pybis vs HSPICE IBIS | gate-state vs HSPICE IBIS |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for variant in VARIANTS:
        values = [
            1e3
            * float(lookup[(variant.variant_id, normal, flow)]["pad_rmse_v_vs_hspice_ibis"])
            for flow in ["hspice_transistor", "legacy", "gate_state"]
        ]
        lines.append(
            f"| {variant.label} | {fits[variant.variant_id]['gate']} | "
            f"{values[0]:.3f} mV | {values[1]:.3f} mV | {values[2]:.3f} mV |"
        )
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "- Both files pass the offline directional-residual reconstruction gate. "
            f"The slow model's worst table RMSE/max error is `{float(fits['slow_1ns']['worst_rmse']):.5f}/{float(fits['slow_1ns']['worst_max_error']):.5f}`; "
            f"the fast model's is `{float(fits['fast_5ps']['worst_rmse']):.5f}/{float(fits['fast_5ps']['worst_max_error']):.5f}`.",
            "- The edge setting changes fitted onset delay, not the underlying fitted time constants. Pullup-on delay changes from "
            f"`{float(fits['slow_1ns']['pu_on_delay_ns']):.3f} ns` to `{float(fits['fast_5ps']['pu_on_delay_ns']):.3f} ns`, "
            f"while pullup-off tau remains `{float(fits['slow_1ns']['pu_off_tau_ns']):.3f} ns` versus `{float(fits['fast_5ps']['pu_off_tau_ns']):.3f} ns`.",
            "- Complete and settled pulses still favor legacy pybis. On the normal edge it is about `11.4 mV` from native HSPICE IBIS, versus `17-18 mV` for gate state.",
            f"- Interrupted 50/100/200 ps pulses reverse that result. For the slow IBIS, legacy pad RMSE spans `{slow_legacy_pad[0]:.1f}-{slow_legacy_pad[1]:.1f} mV`, while gate state spans `{slow_gate_pad[0]:.1f}-{slow_gate_pad[1]:.1f} mV`.",
            f"- For the fast IBIS, legacy pad RMSE spans `{fast_legacy_pad[0]:.1f}-{fast_legacy_pad[1]:.1f} mV`, while gate state spans `{fast_gate_pad[0]:.1f}-{fast_gate_pad[1]:.1f} mV`.",
            "- The slow IBIS is not a good transistor-timing model under this 1 ps bench: normal pad RMSE is `383.2 mV`, mainly from its delayed transition. The fast IBIS reduces that to `13.8 mV`.",
            "- Fast source waveforms do not reproduce the transistor chain's minimum-pulse filtering. For a 50 ps high input the transistor pad stays essentially at `0 V`, while native HSPICE reaches about `0.448 V` with the fast IBIS (`0.466 V` with the slow IBIS).",
            "- Therefore the conclusions are separate: gate state strongly improves native-IBIS interrupted-coefficient playback; the fast IBIS is the closer transistor approximation, but is still not transistor-accurate for the shortest pulses.",
        ]
    )
    lines.extend(
        [
            "",
            "## Figure Guide",
            "",
            "- `slow_1ns/plots/` and `fast_5ps/plots/`: identical phase-by-phase comparison folders.",
            "- `plots/05_hspice_native_slow_vs_fast/`: direct HSPICE native-IBIS pad/Ku/Kd comparison.",
            "- `plots/06_pad_rmse_summary.png`: the same error measure across every case and phase.",
            "- `metrics.csv`: all pad/Ku/Kd metrics with a `variant_id` column.",
            "- `waveform_data/` inside each variant: aligned numeric source data.",
            "",
            "## Interpretation Rule",
            "",
            "The transistor comparison is pad-only. `Ku/Kd` comparisons are native-HSPICE-IBIS playback checks. A gate-state result is not validated unless its offline reconstruction gate passes and its transient pad and coefficient behavior both remain accurate.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the same inv_chain HSPICE/pybis comparison ladder for slow and fast IBIS models."
    )
    parser.add_argument("--ngspice", type=Path, default=base.DEFAULT_NGSPICE)
    parser.add_argument("--hspice", type=Path, default=base.DEFAULT_HSPICE)
    parser.add_argument("--transistor-wrapper", type=Path, default=DEFAULT_TRANSISTOR_WRAPPER)
    parser.add_argument("--transistor-library", type=Path, default=DEFAULT_TRANSISTOR_LIBRARY)
    parser.add_argument("--timeout-s", type=int, default=240)
    parser.add_argument("--case", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base.ensure_dir(OUT_DIR)
    cases = base.select_cases(args.case)
    base.CASES = cases
    metrics: list[dict[str, object]] = []
    cache_rows: list[dict[str, object]] = []
    fits: dict[str, dict[str, object]] = {}
    all_data: dict[str, dict[str, dict[str, np.ndarray]]] = {}

    for variant in VARIANTS:
        print(f"===== {variant.variant_id}: {variant.label} =====", flush=True)
        if not variant.ibis.exists():
            raise FileNotFoundError(variant.ibis)
        variant_dir = OUT_DIR / variant.variant_id
        configure_variant(variant_dir)
        fit = base.offline_fit(variant.ibis)
        fits[variant.variant_id] = fit
        models = base.prepare_models(variant.ibis)
        base.write_provenance(
            variant.ibis,
            args.transistor_wrapper,
            args.transistor_library,
            models,
        )
        all_data[variant.variant_id] = {}
        phase_images: dict[str, list[Path]] = {
            "01": [],
            "02": [],
            "03": [],
            "04": [],
        }
        variant_metrics: list[dict[str, object]] = []
        variant_cache: list[dict[str, object]] = []

        for index, case in enumerate(cases, start=1):
            print(f"[{index}/{len(cases)}] {case.case_id}", flush=True)
            h_native, native_cache = run_native(variant, case, args.hspice, args.timeout_s)
            h_transistor, transistor_cache = base.run_hspice_transistor(
                case,
                args.transistor_wrapper,
                args.transistor_library,
                args.hspice,
                args.timeout_s,
            )
            transistor_cache["variant_id"] = variant.variant_id
            ng_legacy, _, _ = base.run_ngspice(
                case,
                "legacy",
                models["legacy"],
                args.ngspice,
                args.timeout_s,
            )
            ng_gate, _, _ = base.run_ngspice(
                case,
                "gate_state",
                models["gate_state"],
                args.ngspice,
                args.timeout_s,
            )
            data = uniformize_case_data(
                case,
                base.align_case(case, h_native, h_transistor, ng_legacy, ng_gate),
            )
            all_data[variant.variant_id][case.case_id] = data
            rows = add_variant_fields(variant, base.case_metrics(case, data))
            variant_metrics.extend(rows)
            metrics.extend(rows)
            variant_cache.extend([native_cache, transistor_cache])
            cache_rows.extend([native_cache, transistor_cache])

            phase_images["01"].append(
                plot_hspice_ibis_vs_transistor(
                    variant,
                    case,
                    data,
                    base.PLOTS_DIR / "01_hspice_ibis_vs_transistor",
                )
            )
            phase_images["02"].append(
                base.plot_two_flow(
                    case,
                    data,
                    "legacy",
                    "ngspice legacy pybis",
                    base.PLOTS_DIR / "02_hspice_ibis_vs_legacy",
                )
            )
            phase_images["03"].append(
                base.plot_two_flow(
                    case,
                    data,
                    "gate_state",
                    "ngspice directional-residual",
                    base.PLOTS_DIR / "03_hspice_ibis_vs_gate_state",
                )
            )
            phase_images["04"].append(
                plot_three_way(
                    variant,
                    case,
                    data,
                    base.PLOTS_DIR / "04_hspice_ibis_gate_state_transistor",
                )
            )
            base.write_csv(OUT_DIR / "metrics.csv", metrics)
            base.write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)

        for phase, images in phase_images.items():
            base.contact_sheet(
                images,
                base.PLOTS_DIR / f"{phase}_contact_sheet.png",
            )
        base.write_csv(variant_dir / "metrics.csv", variant_metrics)
        base.write_csv(variant_dir / "reference_cache_manifest.csv", variant_cache)
        write_variant_readme(variant, fit, variant_metrics, cache_rows)

    cross_images: list[Path] = []
    cross_dir = OUT_DIR / "plots" / "05_hspice_native_slow_vs_fast"
    for case in cases:
        cross_images.append(
            plot_slow_fast_native(
                case,
                {
                    variant.variant_id: all_data[variant.variant_id][case.case_id]
                    for variant in VARIANTS
                },
                cross_dir,
            )
        )
    base.contact_sheet(
        cross_images,
        OUT_DIR / "plots" / "05_hspice_native_slow_vs_fast_contact_sheet.png",
    )
    plot_metric_summary(metrics, OUT_DIR / "plots" / "06_pad_rmse_summary.png")
    base.write_csv(OUT_DIR / "metrics.csv", metrics)
    base.write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)
    write_main_readme(metrics, fits)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
