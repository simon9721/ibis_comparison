from __future__ import annotations

import csv
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_reversal_hybrid_slow_fast_comparison as base  # noqa: E402
from pybis2spice import pybis2spice, subcircuit  # noqa: E402


OUT_DIR = ROOT / "results" / "io_buf_inv_chain_dual_residual_hybrid_comparison_2026-07-27"
KD_ONLY_DIR = ROOT / "results" / "io_buf_inv_chain_reversal_hybrid_comparison_2026-07-27"
DUAL_MODE = "InputDrivenTwoStateGateDirectionalDualResidualHybrid"
DUAL_LABEL = "ngspice dual Ku/Kd-residual hybrid"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def numeric_csv(path: Path) -> dict[str, np.ndarray]:
    rows = read_csv(path)
    if not rows:
        raise ValueError(f"No rows in {path}")
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
        if all(row.get(key, "") not in {"", None} for row in rows)
    }


def metric_number(row: dict[str, str], key: str) -> float | None:
    try:
        value = float(row.get(key, ""))
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def direct_comparison_rows() -> list[dict[str, object]]:
    old_rows = {
        (row["device"], row["ibis_variant"], row["case_id"]): row
        for row in read_csv(KD_ONLY_DIR / "metrics.csv")
        if row.get("flow") == "hybrid"
    }
    new_rows = {
        (row["device"], row["ibis_variant"], row["case_id"]): row
        for row in read_csv(OUT_DIR / "metrics.csv")
        if row.get("flow") == "hybrid"
    }
    result: list[dict[str, object]] = []
    for key in sorted(new_rows):
        device, variant, case_id = key
        old = old_rows.get(key, {})
        new = new_rows[key]
        row: dict[str, object] = {
            "device": device,
            "ibis_variant": variant,
            "case_id": case_id,
            "kd_only_status": old.get("status", "MISSING"),
            "dual_status": new.get("status", ""),
        }
        for metric in ["pad_rmse_v", "ku_rmse", "kd_rmse"]:
            old_value = metric_number(old, metric)
            new_value = metric_number(new, metric)
            row[f"kd_only_{metric}"] = "" if old_value is None else old_value
            row[f"dual_{metric}"] = "" if new_value is None else new_value
            row[f"dual_reduction_pct_{metric}"] = (
                ""
                if old_value in {None, 0.0} or new_value is None
                else 100.0 * (1.0 - new_value / old_value)
            )
        for metric in [
            "hybrid_active_duration_ns",
            "max_takeover_ku_step",
            "max_takeover_kd_step",
            "max_handoff_ku_step",
            "max_handoff_kd_step",
        ]:
            row[f"kd_only_{metric}"] = old.get(metric, "")
            row[f"dual_{metric}"] = new.get(metric, "")
        for metric in ["ku_min", "ku_max", "kd_min", "kd_max", "coefficient_range_ok"]:
            row[f"kd_only_{metric}"] = old.get(metric, "")
            row[f"dual_{metric}"] = new.get(metric, "")
        result.append(row)
    return result


def waveform_path(root: Path, device: str, variant: str, case_id: str) -> Path:
    return root / device / variant / "waveform_data" / f"{case_id}.csv"


def refresh_residual_waveform_columns() -> None:
    names = ["kures", "kures_table", "guprate", "kdres", "kdres_table", "gdnrate"]
    for device in base.DEVICES:
        for variant in base.VARIANTS[device.device_id]:
            for case in device.cases:
                waveform = waveform_path(
                    OUT_DIR,
                    device.device_id,
                    variant.variant_id,
                    case.case_id,
                )
                raw = (
                    OUT_DIR
                    / device.device_id
                    / variant.variant_id
                    / "cases"
                    / case.case_id
                    / "ngspice_reversal_hybrid"
                    / "run.raw"
                )
                if not waveform.exists() or not raw.exists():
                    continue
                data = numeric_csv(waveform)
                if all(f"hybrid_{name}" in data for name in names):
                    continue
                simulation = base.ngspice_waveform(raw)
                for name in names:
                    if name in simulation:
                        data[f"hybrid_{name}"] = np.interp(
                            data["time_ns"],
                            simulation["time_ns"],
                            simulation[name],
                        )
                base.save_numeric(waveform, data)


def augment_metrics() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [dict(row) for row in read_csv(OUT_DIR / "metrics.csv")]
    for row in rows:
        if row.get("flow") != "hybrid" or row.get("status") == "NUMERIC_FAIL":
            continue
        path = waveform_path(
            OUT_DIR,
            str(row["device"]),
            str(row["ibis_variant"]),
            str(row["case_id"]),
        )
        if not path.exists():
            continue
        data = numeric_csv(path)
        if "hybrid_ku" not in data or "hybrid_kd" not in data:
            continue
        ku = data["hybrid_ku"]
        kd = data["hybrid_kd"]
        row["ku_min"] = float(np.min(ku))
        row["ku_max"] = float(np.max(ku))
        row["kd_min"] = float(np.min(kd))
        row["kd_max"] = float(np.max(kd))
        range_ok = (
            float(np.min(ku)) >= -0.2
            and float(np.max(ku)) <= 1.2
            and float(np.min(kd)) >= -0.2
            and float(np.max(kd)) <= 1.2
        )
        row["coefficient_range_ok"] = range_ok
        if not range_ok:
            row["status"] = "NONPHYSICAL_COEFFICIENT_RANGE"
    base.write_csv(OUT_DIR / "metrics.csv", rows)
    base.write_csv(OUT_DIR / "comparison_summary.csv", base.comparison_summary(rows))
    base.OUT_DIR = OUT_DIR
    base.readme(rows)
    readme_path = OUT_DIR / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")
    readme_text = readme_text.replace(
        "`GUP/GDN`, direction-specific coefficient maps, and the Kd residual run continuously",
        "`GUP/GDN`, direction-specific coefficient maps, and independent Ku/Kd residuals run continuously",
    )
    readme_path.write_text(readme_text, encoding="utf-8")
    return rows


def write_failure_diagnostics(metrics: list[dict[str, object]], timeout_s: int = 60) -> None:
    existing = {
        (row.get("device", ""), row.get("ibis_variant", ""), row.get("case_id", "")): row
        for row in read_csv(OUT_DIR / "numeric_failure_diagnostics.csv")
    }
    rows: list[dict[str, object]] = []
    for metric in metrics:
        if metric.get("flow") != "hybrid" or metric.get("status") != "NUMERIC_FAIL":
            continue
        log_value = str(metric.get("log", ""))
        log = Path(log_value)
        if not log.is_absolute():
            log = ROOT / log
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        references = [
            float(value)
            for value in re.findall(r"Reference value\s*:\s*([0-9.eE+-]+)", text)
        ]
        raw = log.parent / "run.raw"
        key = (
            str(metric.get("device", "")),
            str(metric.get("ibis_variant", "")),
            str(metric.get("case_id", "")),
        )
        prior = existing.get(key, {})
        raw_size = (
            raw.stat().st_size
            if raw.exists()
            else int(prior.get("partial_raw_bytes_before_cleanup", 0) or 0)
        )
        row = {
            "device": metric.get("device", ""),
            "ibis_variant": metric.get("ibis_variant", ""),
            "case_id": metric.get("case_id", ""),
            "failure_class": "TIMEOUT_TINY_TIMESTEP_STALL",
            "timeout_s": timeout_s,
            "last_reference_s": references[-1] if references else "",
            "last_reference_ns": references[-1] * 1e9 if references else "",
            "log_path": str(log.relative_to(ROOT)) if log.exists() else log_value,
            "log_bytes": log.stat().st_size if log.exists() else 0,
            "partial_raw_path": str(raw.relative_to(ROOT)),
            "partial_raw_bytes_before_cleanup": raw_size,
            "partial_raw_removed": str(prior.get("partial_raw_removed", "")).lower() == "true",
        }
        if raw.exists():
            resolved = raw.resolve()
            if OUT_DIR.resolve() not in resolved.parents or resolved.name != "run.raw":
                raise RuntimeError(f"Refusing to remove unexpected partial raw path: {resolved}")
            raw.unlink()
            row["partial_raw_removed"] = True
        rows.append(row)
    base.write_csv(OUT_DIR / "numeric_failure_diagnostics.csv", rows)


def write_residual_fit_summary() -> None:
    rows: list[dict[str, object]] = []
    for device in base.DEVICES:
        for variant in base.VARIANTS[device.device_id]:
            model = (
                OUT_DIR
                / device.device_id
                / variant.variant_id
                / "common"
                / "reversal_hybrid"
                / f"{device.subckt}.sub"
            )
            text = model.read_text(encoding="utf-8", errors="replace")
            match = re.search(
                r"Ku/Kd rate gain=([0-9.eE+-]+)/([0-9.eE+-]+) ns",
                text,
            )
            parsed = pybis2spice.get_ibis_model_ecdtools(str(variant.ibis))
            data_model = pybis2spice.DataModel(
                parsed,
                model_name=device.model,
                component_name=device.component,
            )
            corner = subcircuit.convert_corner_str_to_index("Typical") + 1
            kr = pybis2spice.compress_param(
                pybis2spice.solve_k_params_output(
                    data_model,
                    corner=corner,
                    waveform_type="Rising",
                ),
                threshold=1e-3,
            )
            kf = pybis2spice.compress_param(
                pybis2spice.solve_k_params_output(
                    data_model,
                    corner=corner,
                    waveform_type="Falling",
                ),
                threshold=1e-3,
            )
            fit = subcircuit.two_state_directional_gate_fit(kr, kf)
            tr = np.asarray(kr[:, subcircuit._TIME], dtype=float) * 1e9
            tf = np.asarray(kf[:, subcircuit._TIME], dtype=float) * 1e9
            gup_rise = subcircuit.gate_response(
                tr, fit["pu_on_delay"], fit["pu_on_tau"], 0.0, 1.0
            )
            gup_fall = subcircuit.gate_response(
                tf, fit["pu_off_delay"], fit["pu_off_tau"], 1.0, 0.0
            )
            gdn_rise = subcircuit.gate_response(
                tr, fit["pd_off_delay"], fit["pd_off_tau"], 1.0, 0.0
            )
            gdn_fall = subcircuit.gate_response(
                tf, fit["pd_on_delay"], fit["pd_on_tau"], 0.0, 1.0
            )
            ku_rise_base = np.interp(gup_rise, fit["ku_on_map_x"], fit["ku_on_map_y"])
            ku_fall_base = np.interp(gup_fall, fit["ku_off_map_x"], fit["ku_off_map_y"])
            kd_rise_base = np.interp(gdn_rise, fit["kd_off_map_x"], fit["kd_off_map_y"])
            kd_fall_base = np.interp(gdn_fall, fit["kd_on_map_x"], fit["kd_on_map_y"])
            ku_rise_dual = (
                ku_rise_base
                + np.asarray(fit["ku_rise_residual"], dtype=float)
                + float(fit["ku_rate_gain_ns"])
                * subcircuit.gate_state_rate(
                    tr, fit["pu_on_delay"], fit["pu_on_tau"], 0.0, 1.0
                )
            )
            ku_fall_dual = (
                ku_fall_base
                + np.asarray(fit["ku_fall_residual"], dtype=float)
                + float(fit["ku_rate_gain_ns"])
                * subcircuit.gate_state_rate(
                    tf, fit["pu_off_delay"], fit["pu_off_tau"], 1.0, 0.0
                )
            )
            kd_rise_residual = (
                kd_rise_base
                + np.asarray(fit["kd_rise_residual"], dtype=float)
                + float(fit["kd_rate_gain_ns"])
                * subcircuit.gate_state_rate(
                    tr, fit["pd_off_delay"], fit["pd_off_tau"], 1.0, 0.0
                )
            )
            kd_fall_residual = (
                kd_fall_base
                + np.asarray(fit["kd_fall_residual"], dtype=float)
                + float(fit["kd_rate_gain_ns"])
                * subcircuit.gate_state_rate(
                    tf, fit["pd_on_delay"], fit["pd_on_tau"], 0.0, 1.0
                )
            )
            originals = [
                np.asarray(kr[:, subcircuit._KU], dtype=float),
                np.asarray(kf[:, subcircuit._KU], dtype=float),
                np.asarray(kr[:, subcircuit._KD], dtype=float),
                np.asarray(kf[:, subcircuit._KD], dtype=float),
            ]
            kd_only_reconstructed = [
                ku_rise_base,
                ku_fall_base,
                kd_rise_residual,
                kd_fall_residual,
            ]
            dual_reconstructed = [
                ku_rise_dual,
                ku_fall_dual,
                kd_rise_residual,
                kd_fall_residual,
            ]
            kd_only_rmse = [
                float(np.sqrt(np.mean((dut - ref) ** 2)))
                for ref, dut in zip(originals, kd_only_reconstructed)
            ]
            kd_only_max = [
                float(np.max(np.abs(dut - ref)))
                for ref, dut in zip(originals, kd_only_reconstructed)
            ]
            dual_rmse = [
                float(np.sqrt(np.mean((dut - ref) ** 2)))
                for ref, dut in zip(originals, dual_reconstructed)
            ]
            dual_max = [
                float(np.max(np.abs(dut - ref)))
                for ref, dut in zip(originals, dual_reconstructed)
            ]
            kures_max = 0.0
            kdres_max = 0.0
            for case in device.cases:
                waveform = waveform_path(
                    OUT_DIR,
                    device.device_id,
                    variant.variant_id,
                    case.case_id,
                )
                if not waveform.exists():
                    continue
                data = numeric_csv(waveform)
                if "hybrid_kures" in data:
                    kures_max = max(kures_max, float(np.max(np.abs(data["hybrid_kures"]))))
                if "hybrid_kdres" in data:
                    kdres_max = max(kdres_max, float(np.max(np.abs(data["hybrid_kdres"]))))
            rows.append(
                {
                    "device": device.device_id,
                    "ibis_variant": variant.variant_id,
                    "edge_setting": variant.edge_setting,
                    "ku_rate_gain_ns": float(match.group(1)) if match else "",
                    "kd_rate_gain_ns": float(match.group(2)) if match else "",
                    "max_abs_runtime_ku_residual": kures_max,
                    "max_abs_runtime_kd_residual": kdres_max,
                    "kd_only_offline_worst_rmse": max(kd_only_rmse),
                    "kd_only_offline_worst_max_error": max(kd_only_max),
                    "dual_offline_worst_rmse": max(dual_rmse),
                    "dual_offline_worst_max_error": max(dual_max),
                    "dual_offline_gate": (
                        "PASS"
                        if max(dual_rmse) <= 0.02 and max(dual_max) <= 0.08
                        else "FAIL"
                    ),
                    "generated_model": str(model.relative_to(ROOT)),
                    "sha256": base.sha256(model),
                }
            )
    base.write_csv(OUT_DIR / "residual_fit_summary.csv", rows)


def style_axis(ax: plt.Axes, device: base.Device, case: base.Case, ylabel: str) -> None:
    base.style_axis(ax, device, case, ylabel)


def plot_direct_comparison(
    device: base.Device,
    variant: base.ModelVariant,
    case: base.Case,
    old: dict[str, np.ndarray],
    new: dict[str, np.ndarray],
    output: Path,
) -> Path:
    base.ensure_dir(output.parent)
    t = new["time_ns"]
    old_t = old["time_ns"]
    fig, axes = plt.subplots(3, 1, figsize=(14.5, 9.3), sharex=True, constrained_layout=True)
    for ax, (suffix, ylabel) in zip(
        axes,
        [("pad_v", "pad voltage (V)"), ("ku", "Ku"), ("kd", "Kd")],
    ):
        ax.plot(t, new[f"hspice_ibis_{suffix}"], color=base.BLACK, lw=3.0, label="HSPICE IBIS")
        if suffix == "pad_v":
            ax.plot(
                t,
                new["hspice_transistor_pad_v"],
                color=base.GRAY,
                lw=3.0,
                alpha=0.8,
                label="transistor",
            )
        ax.plot(
            old_t,
            old[f"hybrid_{suffix}"],
            color=base.BLUE,
            lw=1.8,
            marker="o",
            markevery=max(1, len(old_t) // 55),
            ms=2.8,
            label="Kd-only",
        )
        ax.plot(
            t,
            new[f"hybrid_{suffix}"],
            color=base.RED,
            lw=1.9,
            marker="D",
            markevery=max(1, len(t) // 55),
            ms=2.8,
            label="dual residual",
        )
        style_axis(ax, device, case, ylabel)
    axes[2].axhline(0, color="#777777", lw=0.8, alpha=0.6)
    axes[0].legend(frameon=False, ncol=4, loc="upper center")
    axes[-1].set_xlabel("time (ns)")
    fig.suptitle(
        f"{device.label} | {variant.label} | {case.title}",
        fontsize=16,
        fontweight="bold",
    )
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return output


def plot_residual_diagnostics(
    device: base.Device,
    variant: base.ModelVariant,
    case: base.Case,
    data: dict[str, np.ndarray],
    output: Path,
) -> Path:
    base.ensure_dir(output.parent)
    t = data["time_ns"]
    fig, axes = plt.subplots(4, 1, figsize=(14.5, 10.5), sharex=True, constrained_layout=True)
    axes[0].plot(t, data["input_v"], color=base.BLACK, lw=2.0, label="input")
    axes[0].plot(
        t,
        data.get("hybrid_hhybridactive", np.zeros_like(t)) * device.supply_v,
        color=base.PURPLE,
        lw=1.8,
        label="hybrid active (scaled)",
    )
    axes[1].plot(t, data.get("hybrid_gup", np.zeros_like(t)), color=base.ORANGE, lw=2.0, label="GUP")
    axes[1].plot(t, data.get("hybrid_gdn", np.zeros_like(t)), color=base.GREEN, lw=2.0, label="GDN")
    axes[2].plot(t, data.get("hybrid_kures_table", np.zeros_like(t)), color="#e76f51", lw=1.5, label="Ku table residual")
    axes[2].plot(t, data.get("hybrid_kures", np.zeros_like(t)), color=base.RED, lw=2.0, label="Ku total residual")
    axes[3].plot(t, data.get("hybrid_kdres_table", np.zeros_like(t)), color="#2a9d8f", lw=1.5, label="Kd table residual")
    axes[3].plot(t, data.get("hybrid_kdres", np.zeros_like(t)), color=base.GREEN, lw=2.0, label="Kd total residual")
    for ax, ylabel in zip(axes, ["command", "hidden state", "Ku residual", "Kd residual"]):
        style_axis(ax, device, case, ylabel)
        ax.legend(frameon=False, ncol=3, loc="upper center")
    axes[-1].set_xlabel("time (ns)")
    fig.suptitle(
        f"{device.label} | {variant.label} | {case.title} | dual residual diagnostics",
        fontsize=16,
        fontweight="bold",
    )
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return output


def make_extra_plots() -> None:
    for device in base.DEVICES:
        for variant in base.VARIANTS[device.device_id]:
            direct_images: list[Path] = []
            residual_images: list[Path] = []
            for case in device.cases:
                old_path = waveform_path(KD_ONLY_DIR, device.device_id, variant.variant_id, case.case_id)
                new_path = waveform_path(OUT_DIR, device.device_id, variant.variant_id, case.case_id)
                if not old_path.exists() or not new_path.exists():
                    continue
                old = numeric_csv(old_path)
                new = numeric_csv(new_path)
                if "hybrid_pad_v" not in old or "hybrid_pad_v" not in new:
                    continue
                plots = OUT_DIR / device.device_id / variant.variant_id / "plots"
                direct_images.append(
                    plot_direct_comparison(
                        device,
                        variant,
                        case,
                        old,
                        new,
                        plots / "07_kd_only_vs_dual_residual" / f"{case.case_id}.png",
                    )
                )
                residual_images.append(
                    plot_residual_diagnostics(
                        device,
                        variant,
                        case,
                        new,
                        plots / "08_dual_residual_diagnostics" / f"{case.case_id}.png",
                    )
                )
            if direct_images:
                base.contact_sheet(
                    direct_images,
                    OUT_DIR
                    / device.device_id
                    / variant.variant_id
                    / "plots"
                    / "07_kd_only_vs_dual_residual_contact_sheet.png",
                )
            if residual_images:
                base.contact_sheet(
                    residual_images,
                    OUT_DIR
                    / device.device_id
                    / variant.variant_id
                    / "plots"
                    / "08_dual_residual_diagnostics_contact_sheet.png",
                )


def append_findings(rows: list[dict[str, object]]) -> None:
    path = OUT_DIR / "README.md"
    text = path.read_text(encoding="utf-8")
    fit_rows = read_csv(OUT_DIR / "residual_fit_summary.csv")
    fit_passes = sum(row.get("dual_offline_gate") == "PASS" for row in fit_rows)
    fast_io_fit = next(
        (
            row
            for row in fit_rows
            if row.get("device") == "io_buf" and row.get("ibis_variant") == "fast"
        ),
        {},
    )
    comparable = [
        row
        for row in rows
        if all(
            isinstance(row.get(f"{prefix}_{metric}"), float)
            for prefix in ["kd_only", "dual"]
            for metric in ["pad_rmse_v", "ku_rmse", "kd_rmse"]
        )
    ]
    meaningful_ku_better = [
        row for row in rows
        if isinstance(row.get("dual_reduction_pct_ku_rmse"), float)
        and float(row["dual_reduction_pct_ku_rmse"]) > 1.0
    ]
    meaningful_ku_worse = [
        row for row in rows
        if isinstance(row.get("dual_reduction_pct_ku_rmse"), float)
        and float(row["dual_reduction_pct_ku_rmse"]) < -1.0
    ]
    meaningful_pad_better = [
        row for row in rows
        if isinstance(row.get("dual_reduction_pct_pad_rmse_v"), float)
        and float(row["dual_reduction_pct_pad_rmse_v"]) > 1.0
    ]
    meaningful_pad_worse = [
        row for row in rows
        if isinstance(row.get("dual_reduction_pct_pad_rmse_v"), float)
        and float(row["dual_reduction_pct_pad_rmse_v"]) < -1.0
    ]
    meaningful_all = [
        row for row in rows
        if all(
            isinstance(row.get(f"dual_reduction_pct_{metric}"), float)
            and float(row[f"dual_reduction_pct_{metric}"]) > 1.0
            for metric in ["pad_rmse_v", "ku_rmse", "kd_rmse"]
        )
    ]
    strong_all = [
        row for row in rows
        if all(
            isinstance(row.get(f"dual_reduction_pct_{metric}"), float)
            and float(row[f"dual_reduction_pct_{metric}"]) > 5.0
            for metric in ["pad_rmse_v", "ku_rmse", "kd_rmse"]
        )
    ]
    status_counts = Counter(str(row.get("dual_status", "")) for row in rows)
    lines = [
        "",
        "## Dual-Residual Extension",
        "",
        "- The previous hybrid corrected only `Kd`; this candidate independently adds `Ku` rise/fall table residuals and a `dGUP/dt` residual while retaining the established `Kd` residual.",
        f"- Comparable completed A/B cases: `{len(comparable)}`.",
        f"- Using a 1% material-change threshold, Ku improves in `{len(meaningful_ku_better)}/{len(comparable)}` cases and worsens in `{len(meaningful_ku_worse)}/{len(comparable)}`.",
        f"- Pad improves in `{len(meaningful_pad_better)}/{len(comparable)}` cases and worsens in `{len(meaningful_pad_worse)}/{len(comparable)}`.",
        f"- Only `{len(meaningful_all)}/{len(comparable)}` cases improve pad, Ku, and Kd together by more than 1%; `{len(strong_all)}` improve all three by more than 5%.",
        "- The dual residual is **not preferred over the Kd-only hybrid**. It regresses the previously continuous slow-`io_buf` 2 ns-low result, and three fast-`io_buf` cases violate the allowed coefficient range.",
        "- `inv_chain` remains strong, but the new Ku term mostly makes small changes: all 12 activated cases retain their continuous-improvement status, with individual A/B changes generally only a few percent.",
        "- Slow `io_buf` 2 ns-low regresses from pad/Ku RMSE `11.244 mV / 0.01235` to `13.295 mV / 0.01541`. Fast `io_buf` 1 ns-high improves Ku RMSE from `0.35595` to `0.14276`, but worsens pad/Kd to `540.949 mV / 0.32682` and violates coefficient bounds.",
        f"- Offline complete-edge reconstruction passes for `{fit_passes}/{len(fit_rows)}` device/IBIS variants. Fast `io_buf` improves offline worst RMSE from `{fast_io_fit.get('kd_only_offline_worst_rmse', 'n/a')}` to `{fast_io_fit.get('dual_offline_worst_rmse', 'n/a')}`.",
        f"- That offline pass does not transfer to interrupted runtime: fast `io_buf` reaches Ku/Kd residual magnitudes `{fast_io_fit.get('max_abs_runtime_ku_residual', 'n/a')}` / `{fast_io_fit.get('max_abs_runtime_kd_residual', 'n/a')}`. The complete-edge residual is still elapsed-time-indexed and is not a valid general correction at an arbitrary hidden state.",
        f"- Dual-candidate status counts: `{dict(status_counts)}`.",
        "- HSPICE references were reused from cache; this extension ran only the new ngspice candidate.",
        "",
        "Additional evidence:",
        "",
        "- `dual_vs_kd_only_summary.csv`: direct numeric A/B comparison.",
        "- `residual_fit_summary.csv`: independently fitted Ku/Kd rate gains and observed residual magnitudes.",
        "- `plots/07_kd_only_vs_dual_residual`: native IBIS, transistor pad, Kd-only hybrid, and dual-residual hybrid.",
        "- `plots/08_dual_residual_diagnostics`: `GUP/GDN` plus separate Ku/Kd residual contributions.",
    ]
    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    base.OUT_DIR = OUT_DIR
    base.HYBRID_SUBCIRCUIT_TYPE = DUAL_MODE
    base.HYBRID_DISPLAY_LABEL = DUAL_LABEL
    postprocess_only = "--postprocess-only" in sys.argv
    if postprocess_only:
        sys.argv.remove("--postprocess-only")
        result = 0
    else:
        result = base.main()
    refresh_residual_waveform_columns()
    metrics = augment_metrics()
    rows = direct_comparison_rows()
    base.write_csv(OUT_DIR / "dual_vs_kd_only_summary.csv", rows)
    write_failure_diagnostics(metrics)
    write_residual_fit_summary()
    source_verification = KD_ONLY_DIR / "legacy_unchanged_verification.csv"
    if source_verification.exists():
        shutil.copy2(source_verification, OUT_DIR / "legacy_unchanged_verification.csv")
    make_extra_plots()
    append_findings(rows)
    print(f"DUAL_SUMMARY={OUT_DIR / 'dual_vs_kd_only_summary.csv'}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
