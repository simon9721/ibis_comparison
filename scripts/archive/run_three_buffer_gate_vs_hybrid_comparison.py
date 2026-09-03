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


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
for path in [SCRIPTS, PYBIS_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_ngspice_raw  # noqa: E402
import run_ex2_slow_fast_gate_state_comparison as ex2  # noqa: E402
import run_inv_chain_forced_midtransition_reversal as inv_forced  # noqa: E402
import run_inv_chain_gate_state_clean_comparison as inv_base  # noqa: E402
import run_inv_chain_s2ibispy_slow_fast_comparison as inv_profiles  # noqa: E402
from spice_tool_paths import default_ngspice  # noqa: E402


OUT_DIR = ROOT / "results" / "three_buffer_gate_vs_hybrid_2026-07-28"
IO_SOURCE = (
    ROOT / "results" / "io_buf_inv_chain_reversal_hybrid_comparison_2026-07-27"
)
INV_SOURCE = (
    ROOT / "results" / "inv_chain_forced_midtransition_reversal_2026-07-28"
)
EX2_SOURCE = (
    ROOT / "results" / "ex2_slow_fast_gate_state_comparison_2026-07-28"
)

HYBRID_MODE = "InputDrivenTwoStateGateDirectionalResidualHybrid"

BLACK = "#111111"
GRAY = "#858585"
RED = "#d62728"
PURPLE = "#7b2cbf"
EDGE = "#777777"
GRID = "#dddddd"


@dataclass(frozen=True)
class ComparisonCase:
    device: str
    profile: str
    profile_label: str
    case_id: str
    title: str
    pattern: str
    pulse_width_ns: float
    source_csv: Path
    full_prefix: str


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_waveform(path: Path) -> dict[str, np.ndarray]:
    rows = read_csv(path)
    if not rows:
        raise FileNotFoundError(path)
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def save_waveform(path: Path, data: dict[str, np.ndarray]) -> None:
    write_csv(
        path,
        [
            {key: float(values[index]) for key, values in data.items()}
            for index in range(len(data["time_ns"]))
        ],
    )


def optional_signal(
    raw: dict[str, np.ndarray],
    *names: str,
) -> np.ndarray | None:
    normalized = {
        key.lower().replace(":", "."): key
        for key in raw
    }
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(raw[key], dtype=float)
    return None


def raw_time_ns(raw: dict[str, np.ndarray]) -> np.ndarray:
    values = optional_signal(raw, "time")
    if values is None:
        raise KeyError("ngspice raw has no time vector")
    return values * 1e9


def add_hybrid(
    data: dict[str, np.ndarray],
    raw: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    result = dict(data)
    source_time = raw_time_ns(raw)
    target_time = data["time_ns"]
    required = {
        "hybrid_pad_v": ("v(pad)",),
        "hybrid_ku": ("v(xdrv.ku)", "v(xdrv:ku)"),
        "hybrid_kd": ("v(xdrv.kd)", "v(xdrv:kd)"),
    }
    optional = {
        "hybrid_gup": ("v(xdrv.gup)", "v(xdrv:gup)"),
        "hybrid_gdn": ("v(xdrv.gdn)", "v(xdrv:gdn)"),
        "hybrid_hhybridactive": (
            "v(xdrv.hhybridactive)",
            "v(xdrv:hhybridactive)",
        ),
    }
    for key, names in required.items():
        values = optional_signal(raw, *names)
        if values is None:
            raise KeyError(f"missing required hybrid signal {names}")
        result[key] = np.interp(target_time, source_time, values)
    for key, names in optional.items():
        values = optional_signal(raw, *names)
        if values is not None:
            result[key] = np.interp(target_time, source_time, values)
    return result


def case_edges(case: ComparisonCase) -> list[float]:
    start = 5.0005 if case.pattern == "short_high" else 10.0005
    return [start, start + case.pulse_width_ns]


def active_mask(case: ComparisonCase, time_ns: np.ndarray) -> np.ndarray:
    start, reverse = case_edges(case)
    return (time_ns >= start - 1.0) & (time_ns <= reverse + 4.0)


def rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.sqrt(np.mean((candidate - reference) ** 2)))


def metrics(
    case: ComparisonCase,
    data: dict[str, np.ndarray],
    hybrid_status: str,
) -> list[dict[str, object]]:
    mask = active_mask(case, data["time_ns"])
    rows: list[dict[str, object]] = []
    for flow in ["full_gate", "hybrid"]:
        prefix = case.full_prefix if flow == "full_gate" else "hybrid"
        if f"{prefix}_pad_v" not in data:
            rows.append(
                {
                    "device": case.device,
                    "profile": case.profile,
                    "case_id": case.case_id,
                    "flow": flow,
                    "status": hybrid_status if flow == "hybrid" else "UNAVAILABLE",
                }
            )
            continue
        row: dict[str, object] = {
            "device": case.device,
            "profile": case.profile,
            "case_id": case.case_id,
            "flow": flow,
            "status": "COMPLETED",
        }
        for suffix in ["pad_v", "ku", "kd"]:
            reference = data[f"hspice_ibis_{suffix}"][mask]
            candidate = data[f"{prefix}_{suffix}"][mask]
            row[f"{suffix}_rmse"] = rmse(reference, candidate)
            row[f"{suffix}_max_error"] = float(
                np.max(np.abs(candidate - reference))
            )
        rows.append(row)
    return rows


def plot_case(
    case: ComparisonCase,
    data: dict[str, np.ndarray],
    hybrid_status: str,
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    time_ns = data["time_ns"]
    mask = active_mask(case, time_ns)
    x0 = float(np.min(time_ns[mask]))
    x1 = float(np.max(time_ns[mask]))
    fig, axes = plt.subplots(
        3,
        1,
        figsize=(14.5, 9.0),
        sharex=True,
        constrained_layout=True,
    )
    panels = [
        ("pad_v", "pad voltage (V)"),
        ("ku", "Ku"),
        ("kd", "Kd"),
    ]
    for ax, (suffix, ylabel) in zip(axes, panels):
        ax.plot(
            time_ns,
            data[f"hspice_ibis_{suffix}"],
            color=BLACK,
            lw=3.2,
            label="HSPICE native IBIS",
            zorder=5,
        )
        if suffix == "pad_v":
            ax.plot(
                time_ns,
                data["hspice_transistor_pad_v"],
                color=GRAY,
                lw=3.2,
                label="HSPICE transistor",
                zorder=2,
            )
        full_key = f"{case.full_prefix}_{suffix}"
        if full_key in data:
            ax.plot(
                time_ns,
                data[full_key],
                color=RED,
                lw=2.0,
                marker="o",
                markevery=max(1, len(time_ns) // 60),
                ms=3.0,
                label="gate state model",
                zorder=4,
            )
        hybrid_key = f"hybrid_{suffix}"
        if hybrid_key in data:
            ax.plot(
                time_ns,
                data[hybrid_key],
                color=PURPLE,
                lw=2.0,
                marker="D",
                markevery=max(1, len(time_ns) // 52),
                ms=3.0,
                label="hybrid model",
                zorder=3,
            )
        for edge in case_edges(case):
            ax.axvline(edge, color=EDGE, lw=1.1, ls="--", alpha=0.8)
        ax.set_ylabel(ylabel)
        ax.set_xlim(x0, x1)
        ax.grid(True, color=GRID, alpha=0.75)
    axes[2].axhline(0.0, color="#777777", lw=0.8)
    if "hybrid_pad_v" not in data:
        axes[0].text(
            0.98,
            0.08,
            f"hybrid unavailable: {hybrid_status}",
            transform=axes[0].transAxes,
            ha="right",
            va="bottom",
            color=PURPLE,
            fontsize=10,
        )
    handles: list[object] = []
    labels: list[str] = []
    for ax in axes:
        for handle, label in zip(*ax.get_legend_handles_labels()):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    axes[0].legend(handles, labels, frameon=False, ncol=4, loc="upper center")
    axes[2].set_xlabel("time (ns)")
    fig.suptitle(
        f"{case.device} | {case.profile_label} | {case.title}",
        fontweight="bold",
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def contact_sheet(paths: list[Path], output: Path) -> None:
    if not paths:
        return
    images = [plt.imread(path) for path in paths]
    columns = 2
    rows = (len(images) + columns - 1) // columns
    fig, axes = plt.subplots(
        rows,
        columns,
        figsize=(16.0, 5.4 * rows),
        constrained_layout=True,
    )
    flat = np.atleast_1d(axes).ravel()
    for ax, image in zip(flat, images):
        ax.imshow(image)
        ax.axis("off")
    for ax in flat[len(images) :]:
        ax.axis("off")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=125)
    plt.close(fig)


def io_cases() -> list[ComparisonCase]:
    cases: list[ComparisonCase] = []
    specs = [
        ("short_pulse_1ns_high", "1 ns high pulse", "short_high", 1.0),
        ("short_pulse_2ns_high", "2 ns high pulse", "short_high", 2.0),
        ("short_pulse_1ns_low", "1 ns low pulse", "short_low", 1.0),
        ("short_pulse_2ns_low", "2 ns low pulse", "short_low", 2.0),
    ]
    for profile, label in [("slow", "slow IBIS"), ("fast", "fast IBIS")]:
        for case_id, title, pattern, width in specs:
            cases.append(
                ComparisonCase(
                    "io_buf",
                    profile,
                    label,
                    case_id,
                    title,
                    pattern,
                    width,
                    IO_SOURCE
                    / "io_buf"
                    / profile
                    / "waveform_data"
                    / f"{case_id}.csv",
                    "full_gate",
                )
            )
    return cases


def inv_cases() -> list[ComparisonCase]:
    result: list[ComparisonCase] = []
    selected = [case for case in inv_forced.CASES if case.pattern != "rise_fall"]
    for variant in inv_profiles.VARIANTS:
        for case in selected:
            result.append(
                ComparisonCase(
                    "inv_chain",
                    variant.variant_id,
                    (
                        "slow IBIS"
                        if variant.variant_id == "slow_1ns"
                        else "fast IBIS"
                    ),
                    case.case_id,
                    case.title,
                    case.pattern,
                    case.pulse_width_ns,
                    INV_SOURCE
                    / variant.variant_id
                    / "waveform_data"
                    / f"{case.case_id}.csv",
                    "gate_state",
                )
            )
    return result


def ex2_cases() -> list[ComparisonCase]:
    result: list[ComparisonCase] = []
    selected_ids = {
        "short_pulse_50ps_high",
        "short_pulse_500ps_high",
        "short_pulse_1ns_high",
        "short_pulse_50ps_low",
        "short_pulse_500ps_low",
        "short_pulse_1ns_low",
    }
    for profile in ["slow_1ns", "fast_5ps"]:
        for case in ex2.CASES:
            if case.case_id not in selected_ids:
                continue
            result.append(
                ComparisonCase(
                    "ex2",
                    profile,
                    "slow IBIS" if profile == "slow_1ns" else "fast IBIS",
                    case.case_id,
                    case.title,
                    case.pattern,
                    case.pulse_width_ns,
                    EX2_SOURCE
                    / profile
                    / "waveform_data"
                    / f"{case.case_id}.csv",
                    "gate_full" if profile == "slow_1ns" else "gate_stable",
                )
            )
    return result


def prepare_inv_hybrid(
    profile: str,
    output: Path,
) -> tuple[Path, Path]:
    variant = next(
        item for item in inv_profiles.VARIANTS if item.variant_id == profile
    )
    common = output / "common"
    common.mkdir(parents=True, exist_ok=True)
    ibis_copy = common / variant.ibis.name
    shutil.copy2(variant.ibis, ibis_copy)
    model = common / "hybrid" / "driver2_OutputInput_Typical.sub"
    convert_ibis_to_pybis(
        ibis_path=ibis_copy,
        output_path=model,
        component_name=inv_base.COMPONENT_NAME,
        model_name=inv_base.MODEL_NAME,
        io_type="Output",
        subcircuit_type=HYBRID_MODE,
        corner="Typical",
    )
    return variant.ibis, model


def run_inv_hybrid(
    case: ComparisonCase,
    model: Path,
    ngspice: Path,
    timeout_s: int,
    resume: bool,
) -> dict[str, np.ndarray]:
    profile_dir = OUT_DIR / case.device / case.profile
    inv_forced.configure_variant(profile_dir)
    case_object = next(
        item for item in inv_forced.CASES if item.case_id == case.case_id
    )
    raw_path = (
        profile_dir
        / "cases"
        / case.case_id
        / "ngspice_reversal_hybrid"
        / f"{case.case_id}_ngspice_reversal_hybrid.raw"
    )
    if resume and raw_path.exists():
        return parse_ngspice_raw(raw_path)
    raw, _, _ = inv_base.run_ngspice(
        case_object,
        "reversal_hybrid",
        model,
        ngspice,
        timeout_s,
    )
    return raw


def prepare_ex2_hybrid(profile: str, output: Path) -> Path:
    ibis = ex2.PROFILES[profile]
    common = output / "common"
    common.mkdir(parents=True, exist_ok=True)
    ibis_copy = common / "ex2.ibs"
    shutil.copy2(ibis, ibis_copy)
    model = common / "hybrid" / "driver_OutputInput_Typical.sub"
    convert_ibis_to_pybis(
        ibis_path=ibis_copy,
        output_path=model,
        component_name=ex2.COMPONENT_NAME,
        model_name=ex2.MODEL_NAME,
        io_type="Output",
        subcircuit_type=HYBRID_MODE,
        corner="Typical",
    )
    return model


def run_ex2_hybrid(
    case: ComparisonCase,
    model: Path,
    ngspice: Path,
    timeout_s: int,
    resume: bool,
) -> dict[str, np.ndarray]:
    profile_dir = OUT_DIR / case.device / case.profile
    ex2.configure_clean(profile_dir)
    case_object = next(item for item in ex2.CASES if item.case_id == case.case_id)
    raw_path = (
        profile_dir
        / "cases"
        / case.case_id
        / "ngspice_hybrid"
        / f"{case.case_id}_ngspice_hybrid.raw"
    )
    if resume and raw_path.exists():
        return parse_ngspice_raw(raw_path)
    return ex2.run_ngspice(
        case_object,
        "hybrid",
        model,
        ngspice,
        timeout_s,
    )


def comparison_rows(metrics_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    lookup = {
        (
            str(row["device"]),
            str(row["profile"]),
            str(row["case_id"]),
            str(row["flow"]),
        ): row
        for row in metrics_rows
    }
    result: list[dict[str, object]] = []
    keys = sorted({key[:3] for key in lookup})
    for device, profile, case_id in keys:
        full = lookup.get((device, profile, case_id, "full_gate"), {})
        hybrid = lookup.get((device, profile, case_id, "hybrid"), {})
        row: dict[str, object] = {
            "device": device,
            "profile": profile,
            "case_id": case_id,
            "hybrid_status": hybrid.get("status", ""),
        }
        for suffix in ["pad_v", "ku", "kd"]:
            full_value = full.get(f"{suffix}_rmse", "")
            hybrid_value = hybrid.get(f"{suffix}_rmse", "")
            row[f"full_gate_{suffix}_rmse"] = full_value
            row[f"hybrid_{suffix}_rmse"] = hybrid_value
            if full_value != "" and hybrid_value != "":
                row[f"hybrid_minus_full_{suffix}_rmse"] = (
                    float(hybrid_value) - float(full_value)
                )
            else:
                row[f"hybrid_minus_full_{suffix}_rmse"] = ""
        result.append(row)
    return result


def write_report(
    cases: list[ComparisonCase],
    metrics_rows: list[dict[str, object]],
    failures: list[dict[str, object]],
) -> None:
    comparisons = comparison_rows(metrics_rows)
    completed = [
        row for row in comparisons if row["hybrid_status"] == "COMPLETED"
    ]
    all_three_better = 0
    for row in completed:
        deltas = [
            row[f"hybrid_minus_full_{suffix}_rmse"]
            for suffix in ["pad_v", "ku", "kd"]
        ]
        if all(value != "" and float(value) < 0 for value in deltas):
            all_three_better += 1
    lines = [
        "# Three-Buffer Full Gate-State vs Reversal Hybrid",
        "",
        "Presentation figures intentionally omit legacy pybis. The comparison is HSPICE native IBIS versus the always-active full gate-state model and the legacy-normal/gate-on-reversal hybrid. HSPICE transistor output is included on pad panels only.",
        "",
        "## Scope",
        "",
        f"- Cases plotted: `{len(cases)}` across `io_buf`, `inv_chain`, and `ex2`, slow and fast IBIS.",
        f"- Completed hybrid cases: `{len(completed)}/{len(cases)}`.",
        f"- Hybrid improves pad, Ku, and Kd RMSE together versus full gate-state in `{all_three_better}/{len(completed)}` completed cases.",
        "- HSPICE was not rerun. Existing aligned HSPICE/full-gate data were reused; only missing hybrid ngspice cases were simulated.",
        "- The hybrid still contains legacy replay internally for settled operation, but no standalone legacy waveform is plotted.",
        "",
        "## Important Limits",
        "",
        "- `inv_chain` uses the newly certified forced-reversal widths.",
        "- `io_buf` uses the established 1 ns and 2 ns interrupted cases. Its pullup and pulldown delays are so asymmetric that both hidden states cannot generally be partial at the same delayed reverse instant.",
        "- `ex2` uses 50 ps, 500 ps, and 1 ns interrupted cases. The full gate-state reconstruction gate remains failed, so these are diagnostic comparisons.",
        "- Prior normal-control hybrid runs were numerically stiff because hidden states are tracked continuously. This package does not promote the hybrid as production-ready.",
        "",
        "## Figures",
        "",
        "- `<device>/<profile>/plots/`: one three-panel pad/Ku/Kd figure per case.",
        "- `<device>/<profile>/contact_sheet.png`: profile-level overview.",
        "- Black: HSPICE native IBIS; gray: HSPICE transistor pad; red: gate state model; purple: hybrid model.",
        "",
        "## Numeric Outputs",
        "",
        "- `metrics.csv`: independent full-gate and hybrid errors versus native IBIS.",
        "- `comparison_summary.csv`: direct hybrid-minus-full RMSE deltas.",
        "- `<device>/<profile>/waveform_data/*.csv`: exact plotted data.",
        "- `hybrid_failures.csv`: any ngspice hybrid failures and preserved log paths.",
    ]
    if failures:
        lines.extend(["", "## Hybrid Failures", ""])
        for row in failures:
            lines.append(
                f"- `{row['device']}/{row['profile']}/{row['case_id']}`: "
                f"{row['error']}"
            )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare full gate-state and reversal hybrid without legacy plots."
    )
    parser.add_argument(
        "--ngspice",
        type=Path,
        default=default_ngspice(console=True),
    )
    parser.add_argument("--timeout-s", type=int, default=120)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = io_cases() + inv_cases() + ex2_cases()
    metrics_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    images: dict[tuple[str, str], list[Path]] = {}
    inv_models: dict[str, Path] = {}
    ex2_models: dict[str, Path] = {}

    for index, case in enumerate(cases, start=1):
        print(
            f"[{index}/{len(cases)}] "
            f"{case.device}/{case.profile}/{case.case_id}",
            flush=True,
        )
        data = read_waveform(case.source_csv)
        hybrid_status = "COMPLETED" if "hybrid_pad_v" in data else "UNAVAILABLE"
        if case.device == "inv_chain" and not args.report_only:
            if case.profile not in inv_models:
                _, inv_models[case.profile] = prepare_inv_hybrid(
                    case.profile,
                    OUT_DIR / case.device / case.profile,
                )
            try:
                raw = run_inv_hybrid(
                    case,
                    inv_models[case.profile],
                    args.ngspice,
                    args.timeout_s,
                    args.resume,
                )
                data = add_hybrid(data, raw)
                hybrid_status = "COMPLETED"
            except Exception as exc:
                hybrid_status = "NUMERIC_FAIL"
                failures.append(
                    {
                        "device": case.device,
                        "profile": case.profile,
                        "case_id": case.case_id,
                        "error": str(exc),
                    }
                )
        elif case.device == "ex2" and not args.report_only:
            if case.profile not in ex2_models:
                ex2_models[case.profile] = prepare_ex2_hybrid(
                    case.profile,
                    OUT_DIR / case.device / case.profile,
                )
            try:
                raw = run_ex2_hybrid(
                    case,
                    ex2_models[case.profile],
                    args.ngspice,
                    args.timeout_s,
                    args.resume,
                )
                data = add_hybrid(data, raw)
                hybrid_status = "COMPLETED"
            except Exception as exc:
                hybrid_status = "NUMERIC_FAIL"
                failures.append(
                    {
                        "device": case.device,
                        "profile": case.profile,
                        "case_id": case.case_id,
                        "error": str(exc),
                    }
                )
        elif args.report_only:
            saved = (
                OUT_DIR
                / case.device
                / case.profile
                / "waveform_data"
                / f"{case.case_id}.csv"
            )
            if saved.exists():
                data = read_waveform(saved)
                hybrid_status = (
                    "COMPLETED" if "hybrid_pad_v" in data else "UNAVAILABLE"
                )
        if case.device == "io_buf" and hybrid_status != "COMPLETED":
            failures.append(
                {
                    "device": case.device,
                    "profile": case.profile,
                    "case_id": case.case_id,
                    "error": "prior hybrid ngspice run did not complete",
                }
            )

        waveform = (
            OUT_DIR
            / case.device
            / case.profile
            / "waveform_data"
            / f"{case.case_id}.csv"
        )
        save_waveform(waveform, data)
        metrics_rows.extend(metrics(case, data, hybrid_status))
        image = plot_case(
            case,
            data,
            hybrid_status,
            OUT_DIR
            / case.device
            / case.profile
            / "plots"
            / f"{case.case_id}.png",
        )
        images.setdefault((case.device, case.profile), []).append(image)
        write_csv(OUT_DIR / "metrics.csv", metrics_rows)
        write_csv(OUT_DIR / "hybrid_failures.csv", failures)

    for key, paths in images.items():
        contact_sheet(
            paths,
            OUT_DIR / key[0] / key[1] / "contact_sheet.png",
        )
    write_csv(OUT_DIR / "metrics.csv", metrics_rows)
    write_csv(OUT_DIR / "comparison_summary.csv", comparison_rows(metrics_rows))
    write_csv(OUT_DIR / "hybrid_failures.csv", failures)
    write_report(cases, metrics_rows, failures)
    print(f"OUT_DIR={OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
