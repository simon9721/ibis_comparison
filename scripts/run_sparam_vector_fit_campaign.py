from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import warnings

import matplotlib

matplotlib.use("Agg")
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_sparam_conversion_quality_study import (  # noqa: E402
    DEFAULT_HSPICE,
    DEFAULT_NGSPICE,
    ROOT as TRUST_ROOT,
    StudyError,
    annotate_smoke_confidence,
    audit_cases,
    classify_hspice_row,
    classify_hspice_row_view,
    compare_hspice_ngspice,
    describe_candidate,
    dominant_path_info,
    ensure_skrf,
    fitted_s_matrices,
    fmt,
    inventory_paths,
    max_singular_from_mats,
    near_pass,
    passivity_bands,
    plot_frequency_fit,
    plot_singular,
    plot_transient_overlay,
    read_csv,
    rel,
    run_hspice_case,
    run_ngspice_cases,
    safe_id,
    sha256_file,
    smoke_cases,
    smoke_gate_failures,
    smoke_gate_warnings,
    source_family,
    touchstone_port_count,
    write_csv,
    z0_summary,
)


DEFAULT_STUDY_DIR = ROOT / "results" / "sparam_vector_fit_campaign_v1_2026-06-12"
DEFAULT_REDUCED_BASELINE = ROOT / "results" / "sparam_rx_trust_v2_2026-06-11" / "ranking.csv"
PREPROCESS_MODES = ("raw", "dc_hold", "freq_trim_0p9", "freq_trim_0p75")
TRUST_RANK = {"PASS": 0, "WARN": 1, "FAIL": 2, "ERROR": 3}


@dataclass(frozen=True)
class VFCandidateSpec:
    name: str
    kind: str
    n_poles_real: int | None = None
    n_poles_cmplx: int | None = None
    init_pole_spacing: str = ""
    target_error: float | None = None
    model_order_max: int | None = None


def candidate_specs(profile: str = "full", selected: str | None = None) -> list[VFCandidateSpec]:
    auto = [
        VFCandidateSpec("auto_fit_default", "auto", target_error=0.01, model_order_max=100),
        VFCandidateSpec("auto_fit_tight", "auto", target_error=0.005, model_order_max=80),
        VFCandidateSpec("auto_fit_very_tight", "auto", target_error=0.001, model_order_max=100),
    ]
    orders = [1, 2, 3, 4, 5, 6, 8, 10, 12]
    if profile == "pilot":
        auto = auto[:2]
        orders = [3, 5, 8]
    fixed = [
        VFCandidateSpec(f"vector_{order}r{order}c", "fixed", order, order, spacing)
        for order in orders
        for spacing in ("lin", "log")
    ]
    specs = auto + fixed
    if not selected:
        return specs
    requested = {item.strip() for item in selected.split(",") if item.strip()}
    out = []
    for spec in specs:
        aliases = {spec.name}
        if spec.kind == "fixed":
            aliases.add(f"{spec.name}_{spec.init_pole_spacing}")
        if aliases & requested:
            out.append(spec)
    unknown = requested - {alias for spec in specs for alias in ({spec.name, f"{spec.name}_{spec.init_pole_spacing}"} if spec.kind == "fixed" else {spec.name})}
    if unknown:
        raise StudyError(f"Unknown vector-fit candidates: {', '.join(sorted(unknown))}")
    return out


def candidate_id(preprocess: str, spec: VFCandidateSpec, enforced: bool = False) -> str:
    parts = [preprocess, spec.name]
    if spec.kind == "fixed":
        parts.append(spec.init_pole_spacing)
    if enforced:
        parts.append("enforced")
    return "_".join(parts)


def preprocessing_modes(args: argparse.Namespace) -> list[str]:
    if args.preprocess:
        modes = []
        for item in args.preprocess:
            modes.extend(part.strip() for part in item.split(",") if part.strip())
    else:
        modes = list(PREPROCESS_MODES)
    unknown = sorted(set(modes) - set(PREPROCESS_MODES))
    if unknown:
        raise StudyError(f"Unknown preprocessing modes: {', '.join(unknown)}")
    return modes


def make_network(skrf, base_nw, freqs: np.ndarray, s: np.ndarray, z0: np.ndarray, name: str):
    frequency = skrf.Frequency.from_f(freqs, unit="hz")
    return skrf.Network(frequency=frequency, s=s, z0=z0, name=name)


def preprocess_network(skrf, nw, mode: str):
    freqs = np.asarray(nw.frequency.f, dtype=float)
    s = np.asarray(nw.s, dtype=complex)
    z0 = np.asarray(nw.z0)
    if mode == "raw":
        return nw, {"fit_f_min_hz": float(freqs[0]), "fit_f_max_hz": float(freqs[-1]), "fit_points": int(len(freqs)), "preprocess_notes": ""}
    if mode == "dc_hold":
        if freqs[0] <= 0.0:
            return nw, {"fit_f_min_hz": float(freqs[0]), "fit_f_max_hz": float(freqs[-1]), "fit_points": int(len(freqs)), "preprocess_notes": "already_has_dc"}
        out_freqs = np.concatenate([[0.0], freqs])
        out_s = np.concatenate([s[:1], s], axis=0)
        out_z0 = np.concatenate([z0[:1], z0], axis=0)
        out = make_network(skrf, nw, out_freqs, out_s, out_z0, f"{nw.name}_dc_hold")
        return out, {
            "fit_f_min_hz": 0.0,
            "fit_f_max_hz": float(out_freqs[-1]),
            "fit_points": int(len(out_freqs)),
            "preprocess_notes": f"prepended_dc_from_{freqs[0]:.12g}_hz",
        }
    trim_fracs = {"freq_trim_0p9": 0.9, "freq_trim_0p75": 0.75}
    if mode in trim_fracs:
        keep = max(2, int(math.floor(len(freqs) * trim_fracs[mode])))
        keep = min(keep, len(freqs))
        out_freqs = freqs[:keep]
        out = make_network(skrf, nw, out_freqs, s[:keep], z0[:keep], f"{nw.name}_{mode}")
        return out, {
            "fit_f_min_hz": float(out_freqs[0]),
            "fit_f_max_hz": float(out_freqs[-1]),
            "fit_points": int(len(out_freqs)),
            "preprocess_notes": f"trimmed_high_freq_to_{trim_fracs[mode]:.2f}_points",
        }
    raise StudyError(f"Unhandled preprocessing mode: {mode}")


def load_reduced_baseline(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows = read_csv(path)
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        key = str(row.get("relative_path") or row.get("channel_path") or "")
        if key:
            out[key.replace("\\", "/")] = row
    return out


def baseline_for(row: dict[str, object], baseline: dict[str, dict[str, str]]) -> dict[str, str]:
    for key in (str(row.get("relative_path", "")), str(row.get("channel_path", ""))):
        key = key.replace("\\", "/")
        if key in baseline:
            return baseline[key]
    return {}


def inventory_command(args: argparse.Namespace) -> int:
    skrf, _ = ensure_skrf(args.skrf_target)
    rows: list[dict[str, object]] = []
    for source, path in inventory_paths(args):
        ports_suffix = touchstone_port_count(path)
        row: dict[str, object] = {
            "channel_id": safe_id(path),
            "source": source,
            "source_family": source_family(source, path),
            "path": str(path),
            "relative_path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "ports_from_suffix": ports_suffix or "",
        }
        try:
            nw = skrf.Network(str(path))
            freqs = np.asarray(nw.frequency.f, dtype=float)
            supported = bool(nw.nports in (2, 4) and len(freqs))
            row.update(
                {
                    "status": "ok" if supported else "unsupported_v1",
                    "supported_v1": supported,
                    "ports": int(nw.nports),
                    "points": int(len(freqs)),
                    "f_min_hz": float(freqs[0]) if len(freqs) else "",
                    "f_max_hz": float(freqs[-1]) if len(freqs) else "",
                    "z0_summary": z0_summary(nw),
                }
            )
            row.update(dominant_path_info(nw))
        except Exception as exc:
            row.update(
                {
                    "status": "parse_error",
                    "supported_v1": False,
                    "ports": ports_suffix or "",
                    "points": "",
                    "f_min_hz": "",
                    "f_max_hz": "",
                    "z0_summary": "",
                    "error": str(exc),
                    "dominant_path": "",
                    "dominant_output_port": "",
                    "dominant_input_port": "",
                    "dominant_peak_mag_db": "",
                    "max_reflection_mag_db": "",
                }
            )
        rows.append(row)

    counts = Counter(str(row.get("sha256", "")) for row in rows)
    for row in rows:
        digest = str(row.get("sha256", ""))
        row["duplicate_count"] = counts[digest]
        row["duplicate_group"] = digest[:12] if counts[digest] > 1 else ""
    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_family[str(row.get("source_family", "unknown"))].append(row)
    for family_rows in by_family.values():
        for idx, row in enumerate(sorted(family_rows, key=lambda item: str(item.get("channel_id", ""))), start=1):
            row["validation_split"] = "holdout" if idx % 5 == 0 else "calibration"

    args.study_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.study_dir / "manifest.csv", rows)
    print(f"Inventoried {len(rows)} Touchstone files; {sum(bool(row.get('supported_v1')) for row in rows)} supported.")
    return 0


def load_manifest(args: argparse.Namespace) -> list[dict[str, str]]:
    manifest = args.study_dir / "manifest.csv"
    if not manifest.exists():
        inventory_command(args)
    return read_csv(manifest)


def selected_channels(rows: list[dict[str, str]], args: argparse.Namespace) -> list[dict[str, str]]:
    supported = [row for row in rows if str(row.get("supported_v1", "")).lower() == "true" or row.get("supported_v1") is True]
    if args.channel_id:
        wanted = {item.strip() for value in args.channel_id for item in value.split(",") if item.strip()}
        supported = [row for row in supported if row.get("channel_id") in wanted or Path(row.get("path", "")).stem in wanted]
    if args.source_family:
        wanted = {item.strip() for value in args.source_family for item in value.split(",") if item.strip()}
        supported = [row for row in supported if row.get("source_family") in wanted]
    if args.max_channels:
        supported = supported[: args.max_channels]
    return supported


def campaign_math_failures(row: dict[str, object], args: argparse.Namespace) -> list[str]:
    failures: list[str] = []
    def number(key: str, default: float = float("nan")) -> float:
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
    try:
        if int(number("points", 0.0)) < args.min_frequency_points:
            failures.append("too_few_frequency_points")
        if int(number("fit_points", 0.0)) < args.min_frequency_points:
            failures.append("too_few_fit_points")
        if number("fit_f_min_hz", float("inf")) > args.max_low_freq_start_hz:
            failures.append("low_frequency_coverage")
        if not (row.get("is_passive") is True or str(row.get("is_passive")) == "True"):
            failures.append("non_passive_fit")
        if number("max_sv_high", float("inf")) > args.max_sv_high_threshold:
            failures.append("dense_singular_value")
        if number("fit_complex_rms", float("inf")) > args.rms_threshold:
            failures.append("complex_rms_error")
        if number("fit_mag_db_max_above_m40", float("inf")) > args.mag_db_max_threshold:
            failures.append("magnitude_db_error")
        gd = number("fit_group_delay_rms_ps", 0.0)
        if math.isfinite(gd) and gd > args.group_delay_rms_ps_threshold:
            failures.append("group_delay_error")
    except Exception as exc:
        failures.append(f"metric_parse_error:{exc}")
    return sorted(set(failures))


def campaign_warnings(row: dict[str, object], args: argparse.Namespace) -> list[str]:
    warnings_out: list[str] = []
    if str(row.get("preprocessing_mode")) == "dc_hold" and float(row.get("original_f_min_hz") or 0.0) > 0.0:
        warnings_out.append("dc_extrapolated_from_first_point")
    if str(row.get("preprocessing_mode", "")).startswith("freq_trim"):
        warnings_out.append("high_frequency_trimmed_for_fit")
    try:
        if float(row.get("max_sv_high") or 0.0) > args.passivity_warn_sv:
            warnings_out.append("passivity_margin_low")
    except Exception:
        warnings_out.append("passivity_margin_parse")
    return sorted(set(warnings_out))


def quality_score(row: dict[str, object]) -> float:
    def val(key: str, default: float = 0.0) -> float:
        try:
            value = row.get(key, default)
            if value in ("", None):
                return default
            out = float(value)
            return out if math.isfinite(out) else default
        except Exception:
            return default

    return (
        val("fit_complex_rms", 1e6)
        + 0.5 * val("rx_fit_complex_rms", 1e6)
        + 0.25 * val("reflection_fit_complex_rms", 1e6)
        + 1e-5 * val("fit_group_delay_rms_ps", 0.0)
        + 1e-4 * val("model_order", 999.0)
        + 1e-3 * len(str(row.get("math_warn_reasons", "")).split(";"))
    )


def classify_row(row: dict[str, object], args: argparse.Namespace) -> None:
    failures = campaign_math_failures(row, args)
    warnings_out = campaign_warnings(row, args)
    row["math_fail_reasons"] = ";".join(failures)
    row["math_warn_reasons"] = ";".join(warnings_out)
    if failures:
        row["fit_trust_class"] = "FAIL"
    elif warnings_out:
        row["fit_trust_class"] = "WARN"
    else:
        row["fit_trust_class"] = "PASS"
    row["independent_score"] = quality_score(row)


def fit_one_candidate(
    args: argparse.Namespace,
    skrf,
    eval_nw,
    fit_nw,
    channel_base: dict[str, object],
    preprocess: str,
    preprocess_info: dict[str, object],
    spec: VFCandidateSpec,
    channel_dir: Path,
) -> tuple[dict[str, object], object | None]:
    _, VectorFitting = ensure_skrf(args.skrf_target)
    cid = candidate_id(preprocess, spec)
    row: dict[str, object] = {
        **channel_base,
        **preprocess_info,
        "candidate_id": cid,
        "candidate": spec.name,
        "candidate_family": "full_vector_fit",
        "preprocessing_mode": preprocess,
        "fit_source": "vector_fit_frequency_domain",
        "use_scope": "general_multiport",
        "view_role": "full_model",
        "passivity_enforced": False,
        "init_pole_spacing": spec.init_pole_spacing,
        "n_poles_real": spec.n_poles_real or "",
        "n_poles_cmplx": spec.n_poles_cmplx or "",
        "auto_target_error": spec.target_error or "",
        "auto_model_order_max": spec.model_order_max or "",
        "fit_constant": True,
        "fit_proportional": False,
        "enforce_dc": True,
        "export_status": "",
        "fit_status": "",
    }
    start = time.perf_counter()
    try:
        vf = VectorFitting(fit_nw)
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            if spec.kind == "auto":
                vf.auto_fit(
                    target_error=float(spec.target_error or 0.01),
                    model_order_max=int(spec.model_order_max or 100),
                    parameter_type="s",
                    enforce_dc=True,
                )
            else:
                vf.vector_fit(
                    n_poles_real=int(spec.n_poles_real or 0),
                    n_poles_cmplx=int(spec.n_poles_cmplx or 0),
                    init_pole_spacing=spec.init_pole_spacing,
                    parameter_type="s",
                    fit_constant=True,
                    fit_proportional=False,
                    enforce_dc=True,
                )
        row["fit_warning_messages"] = "; ".join(str(record.message) for record in records)
        row.update(describe_candidate(eval_nw, vf, args.high_fmax, args.dense_samples))
        sp_path = channel_dir / "models" / cid / f"{channel_base['channel_id']}_{cid}.sp"
        sp_path.parent.mkdir(parents=True, exist_ok=True)
        vf.write_spice_subcircuit_s(str(sp_path), fitted_model_name="s_equivalent")
        row["spice_file"] = rel(sp_path)
        row["export_status"] = "ok"
        row["fit_status"] = "ok"
        row["fit_time_s"] = time.perf_counter() - start
        classify_row(row, args)
        return row, vf
    except Exception as exc:
        row["fit_time_s"] = time.perf_counter() - start
        row["fit_status"] = "error"
        row["fit_error"] = str(exc)
        row["fit_trust_class"] = "FAIL"
        row["math_fail_reasons"] = "fit_error"
        row["math_warn_reasons"] = ""
        row["independent_score"] = 1e9
        return row, None


def enforce_candidate(
    args: argparse.Namespace,
    eval_nw,
    base_row: dict[str, object],
    vf,
    channel_dir: Path,
) -> tuple[dict[str, object], object | None]:
    row = dict(base_row)
    row["candidate_id"] = f"{base_row['candidate_id']}_enforced"
    row["candidate_family"] = "full_vector_fit_enforced"
    row["passivity_enforced"] = True
    start = time.perf_counter()
    try:
        vf.passivity_enforce(n_samples=args.enforce_samples, f_max=args.high_fmax, preserve_dc=True)
        row.update(describe_candidate(eval_nw, vf, args.high_fmax, args.dense_samples))
        sp_path = channel_dir / "models" / str(row["candidate_id"]) / f"{base_row['channel_id']}_{row['candidate_id']}.sp"
        sp_path.parent.mkdir(parents=True, exist_ok=True)
        vf.write_spice_subcircuit_s(str(sp_path), fitted_model_name="s_equivalent")
        row["spice_file"] = rel(sp_path)
        row["export_status"] = "ok"
        row["fit_status"] = "ok"
        row["enforcement_time_s"] = time.perf_counter() - start
        classify_row(row, args)
        return row, vf
    except Exception as exc:
        row["fit_status"] = "error"
        row["fit_error"] = f"passivity_enforce:{exc}"
        row["math_fail_reasons"] = "passivity_enforce_error"
        row["fit_trust_class"] = "FAIL"
        row["independent_score"] = 1e9
        return row, None


def select_best(rows: list[dict[str, object]]) -> dict[str, object] | None:
    eligible = [row for row in rows if row.get("fit_trust_class") in ("PASS", "WARN") and row.get("spice_file")]
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda row: (
            TRUST_RANK.get(str(row.get("fit_trust_class", "FAIL")), 9),
            len([item for item in str(row.get("math_warn_reasons", "")).split(";") if item]),
            float(row.get("independent_score") or 1e9),
            int(float(row.get("model_order") or 999)),
        ),
    )[0]


def fit_command(args: argparse.Namespace) -> int:
    skrf, _ = ensure_skrf(args.skrf_target)
    manifest = selected_channels(load_manifest(args), args)
    specs = candidate_specs(args.candidate_profile, args.candidates)
    modes = preprocessing_modes(args)
    baseline = load_reduced_baseline(args.reduced_baseline)
    args.study_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.study_dir / "vf_candidates.csv",
        [
            {
                "candidate": spec.name,
                "kind": spec.kind,
                "n_poles_real": spec.n_poles_real or "",
                "n_poles_cmplx": spec.n_poles_cmplx or "",
                "init_pole_spacing": spec.init_pole_spacing,
                "target_error": spec.target_error or "",
                "model_order_max": spec.model_order_max or "",
            }
            for spec in specs
        ],
    )

    all_rows: list[dict[str, object]] = []
    ranking: list[dict[str, object]] = []
    for idx, manifest_row in enumerate(manifest, start=1):
        channel_id = manifest_row["channel_id"]
        print(f"[{idx}/{len(manifest)}] vector-fit {channel_id}")
        channel_path = Path(manifest_row["path"]).resolve()
        channel_dir = args.study_dir / "channels" / channel_id
        channel_dir.mkdir(parents=True, exist_ok=True)
        eval_nw = skrf.Network(str(channel_path))
        freqs = np.asarray(eval_nw.frequency.f, dtype=float)
        sample_sv, sample_idx = max_singular_from_mats(np.asarray(eval_nw.s))
        base: dict[str, object] = {
            "channel_id": channel_id,
            "source": manifest_row.get("source", ""),
            "source_family": manifest_row.get("source_family", ""),
            "validation_split": manifest_row.get("validation_split", ""),
            "channel_path": rel(channel_path),
            "relative_path": manifest_row.get("relative_path", rel(channel_path)),
            "ports": int(eval_nw.nports),
            "points": int(len(freqs)),
            "original_f_min_hz": float(freqs[0]),
            "original_f_max_hz": float(freqs[-1]),
            "high_fmax_hz": args.high_fmax,
            "sampled_max_sv": sample_sv,
            "sampled_max_sv_freq_hz": float(freqs[sample_idx]),
            "sampled_is_passive": bool(eval_nw.is_passive()),
        }
        reduced = baseline_for(base, baseline)
        if reduced:
            base.update(
                {
                    "reduced_baseline_candidate": reduced.get("rx_selected_candidate") or reduced.get("selected_candidate", ""),
                    "reduced_baseline_rx_ready_status": reduced.get("rx_ready_status", ""),
                    "reduced_baseline_rx_voltage_shape_class": reduced.get("rx_voltage_shape_class", ""),
                    "reduced_baseline_rx_timing_class": reduced.get("rx_timing_class", ""),
                }
            )
        channel_rows: list[dict[str, object]] = []
        vf_by_id: dict[str, object] = {}
        for mode in modes:
            fit_nw, prep_info = preprocess_network(skrf, eval_nw, mode)
            for spec in specs:
                row, vf = fit_one_candidate(args, skrf, eval_nw, fit_nw, base, mode, prep_info, spec, channel_dir)
                channel_rows.append(row)
                all_rows.append(row)
                if vf is not None:
                    vf_by_id[str(row["candidate_id"])] = vf
                if vf is not None and not args.skip_passivity_enforcement and near_pass(row):
                    enforced_row, enforced_vf = enforce_candidate(args, eval_nw, row, vf, channel_dir)
                    channel_rows.append(enforced_row)
                    all_rows.append(enforced_row)
                    if enforced_vf is not None:
                        vf_by_id[str(enforced_row["candidate_id"])] = enforced_vf
        selected = select_best(channel_rows)
        if selected is None:
            ranking.append(
                {
                    **base,
                    "selected_candidate_id": "",
                    "selected_candidate": "",
                    "fit_trust_class": "FAIL",
                    "independent_trust_class": "FAIL",
                    "full_model_ready_status": "FAIL",
                    "reason": "no_vector_candidate_passed_fit_gates",
                }
            )
            continue
        selected_copy = args.study_dir / "selected_vector_models" / f"{channel_id}.sp"
        selected_source = ROOT / str(selected["spice_file"])
        selected_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(selected_source, selected_copy)
        selected_vf = vf_by_id.get(str(selected["candidate_id"]))
        if selected_vf is not None:
            plot_frequency_fit(eval_nw, selected_vf, args.study_dir / "plots" / "frequency_fit" / f"{channel_id}_{selected['candidate_id']}.png", f"{channel_id}: {selected['candidate_id']}")
            plot_singular(selected_vf, args.high_fmax, args.study_dir / "plots" / "passivity" / f"{channel_id}_{selected['candidate_id']}.png", f"{channel_id}: selected vector fit passivity")
        ranking.append(
            {
                **base,
                "selected_candidate_id": selected.get("candidate_id", ""),
                "selected_candidate": selected.get("candidate", ""),
                "selected_preprocessing_mode": selected.get("preprocessing_mode", ""),
                "selected_init_pole_spacing": selected.get("init_pole_spacing", ""),
                "selected_passivity_enforced": selected.get("passivity_enforced", ""),
                "selected_spice_file": selected.get("spice_file", ""),
                "selected_model_copy": rel(selected_copy),
                "selected_model_order": selected.get("model_order", ""),
                "selected_fit_complex_rms": selected.get("fit_complex_rms", ""),
                "selected_rx_fit_complex_rms": selected.get("rx_fit_complex_rms", ""),
                "selected_reflection_fit_complex_rms": selected.get("reflection_fit_complex_rms", ""),
                "selected_max_sv_high": selected.get("max_sv_high", ""),
                "fit_trust_class": selected.get("fit_trust_class", ""),
                "math_fail_reasons": selected.get("math_fail_reasons", ""),
                "math_warn_reasons": selected.get("math_warn_reasons", ""),
                "independent_score": selected.get("independent_score", ""),
                "independent_trust_class": selected.get("fit_trust_class", ""),
                "full_model_ready_status": "FULL_MODEL_READY" if selected.get("fit_trust_class") == "PASS" else str(selected.get("fit_trust_class", "FAIL")),
                "reason": "selected_by_vector_fit_independent_score",
            }
        )

    write_csv(args.study_dir / "vf_metrics.csv", all_rows)
    write_csv(args.study_dir / "vf_ranking.csv", ranking)
    report_command(args)
    print(f"Wrote vector-fit campaign outputs under {args.study_dir}")
    return 0


def smoke_ngspice_command(args: argparse.Namespace) -> int:
    ranking_path = args.study_dir / "vf_ranking.csv"
    if not ranking_path.exists():
        raise StudyError(f"Missing {ranking_path}; run fit first.")
    ranking = read_csv(ranking_path)
    selected = [row for row in ranking if row.get("selected_model_copy")]
    if args.max_channels:
        selected = selected[: args.max_channels]
    rows: list[dict[str, object]] = []
    cases = smoke_cases(args.smoke_stop_ns)
    for idx, row in enumerate(selected, start=1):
        channel_id = row["channel_id"]
        print(f"[{idx}/{len(selected)}] ngspice smoke {channel_id}")
        model = ROOT / row["selected_model_copy"]
        out_dir = args.study_dir / "channels" / channel_id / "vf_ngspice_smoke" / row["selected_candidate_id"]
        smoke_rows = run_ngspice_cases(args.ngspice, model, int(row["ports"]), out_dir, cases, args.sim_timeout)
        for smoke in smoke_rows:
            annotate_smoke_confidence(smoke, args)
            smoke.update(
                {
                    "channel_id": channel_id,
                    "candidate_id": row.get("selected_candidate_id", ""),
                    "candidate": row.get("selected_candidate", ""),
                    "preprocessing_mode": row.get("selected_preprocessing_mode", ""),
                    "passivity_enforced": row.get("selected_passivity_enforced", ""),
                }
            )
            rows.append(smoke)
    write_csv(args.study_dir / "vf_ngspice_smoke.csv", rows)
    update_ranking_with_smoke(args, ranking, rows)
    report_command(args)
    return 0


def update_ranking_with_smoke(args: argparse.Namespace, ranking: list[dict[str, str]], smoke_rows: list[dict[str, object]]) -> None:
    by_channel: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in smoke_rows:
        by_channel[str(row.get("channel_id", ""))].append(row)
    updated: list[dict[str, object]] = []
    for row in ranking:
        out: dict[str, object] = dict(row)
        rows = by_channel.get(row.get("channel_id", ""), [])
        failures: list[str] = []
        warnings_out: list[str] = []
        for smoke in rows:
            failures.extend(smoke_gate_failures(smoke, args))
            warnings_out.extend(smoke_gate_warnings(smoke, args))
        failures = sorted(set(failures))
        warnings_out = sorted(set(warnings_out))
        out["ngspice_smoke_cases"] = len(rows)
        out["ngspice_smoke_fail_reasons"] = ";".join(failures)
        out["ngspice_smoke_warn_reasons"] = ";".join(warnings_out)
        if row.get("fit_trust_class") == "FAIL" or failures:
            out["independent_trust_class"] = "FAIL"
            out["full_model_ready_status"] = "FAIL"
        elif row.get("fit_trust_class") == "WARN" or warnings_out:
            out["independent_trust_class"] = "WARN"
            out["full_model_ready_status"] = "WARN"
        else:
            out["independent_trust_class"] = "PASS"
            out["full_model_ready_status"] = "FULL_MODEL_READY"
        updated.append(out)
    write_csv(args.study_dir / "vf_ranking.csv", updated)


def audit_hspice_command(args: argparse.Namespace) -> int:
    ranking_path = args.study_dir / "vf_ranking.csv"
    if not ranking_path.exists():
        raise StudyError(f"Missing {ranking_path}; run fit first.")
    ranking = [row for row in read_csv(ranking_path) if row.get("selected_model_copy")]
    if args.channel_id:
        wanted = {item.strip() for value in args.channel_id for item in value.split(",") if item.strip()}
        ranking = [row for row in ranking if row.get("channel_id") in wanted or Path(row.get("channel_path", "")).stem in wanted]
    if args.max_channels:
        ranking = ranking[: args.max_channels]
    existing: list[dict[str, object]] = []
    corr_path = args.study_dir / "vf_hspice_correlation.csv"
    done: set[tuple[str, str]] = set()
    if args.resume and corr_path.exists():
        existing = list(read_csv(corr_path))
        done = {(str(row.get("channel_id", "")), str(row.get("case", ""))) for row in existing}
    corr_rows: list[dict[str, object]] = list(existing)
    for idx, row in enumerate(ranking, start=1):
        channel_id = row["channel_id"]
        print(f"[{idx}/{len(ranking)}] HSPICE audit {channel_id}")
        touchstone = ROOT / row["channel_path"]
        model = ROOT / row["selected_model_copy"]
        nports = int(row["ports"])
        out_dir = args.study_dir / "channels" / channel_id / "vf_hspice_audit" / row["selected_candidate_id"]
        for case in audit_cases(args.audit_stop_ns):
            if (channel_id, case.name) in done:
                continue
            hrow = run_hspice_case(args.hspice, touchstone, nports, out_dir, case, args.sim_timeout)
            ng_rows = run_ngspice_cases(args.ngspice, model, nports, out_dir / "ngspice", [case], args.sim_timeout)
            ngrow = ng_rows[0] if ng_rows else {}
            h_tr0 = ROOT / str(hrow.get("hspice_tr0", ""))
            n_raw = ROOT / str(ngrow.get("raw", ""))
            comp = compare_hspice_ngspice(h_tr0, n_raw, nports)
            comp.update(
                {
                    "channel_id": channel_id,
                    "candidate_id": row.get("selected_candidate_id", ""),
                    "candidate": row.get("selected_candidate", ""),
                    "preprocessing_mode": row.get("selected_preprocessing_mode", ""),
                    "passivity_enforced": row.get("selected_passivity_enforced", ""),
                    "source_family": row.get("source_family", ""),
                    "validation_split": row.get("validation_split", ""),
                    "independent_trust_class": row.get("independent_trust_class", row.get("fit_trust_class", "")),
                    "case": case.name,
                    "edge_ps": case.edge_ps,
                    "amplitude_v": case.amplitude_v,
                    "hspice_tr0": hrow.get("hspice_tr0", ""),
                    "hspice_lis": hrow.get("hspice_lis", ""),
                    "ngspice_raw": ngrow.get("raw", ""),
                    "ngspice_log": ngrow.get("log", ""),
                }
            )
            klass, reason = classify_hspice_row(comp, args)
            comp["hspice_audit_class"] = klass
            comp["hspice_audit_reason"] = reason
            rx_class, rx_reason = classify_hspice_row_view(comp, args, "rx")
            refl_class, refl_reason = classify_hspice_row_view(comp, args, "reflection")
            comp["rx_hspice_audit_class"] = rx_class
            comp["rx_hspice_audit_reason"] = rx_reason
            comp["reflection_hspice_audit_class"] = refl_class
            comp["reflection_hspice_audit_reason"] = refl_reason
            if h_tr0.exists() and n_raw.exists():
                plot_path = args.study_dir / "plots" / "hspice_overlays" / f"{channel_id}_{row['selected_candidate_id']}_{case.name}.png"
                try:
                    plot_transient_overlay(h_tr0, n_raw, nports, plot_path, f"{channel_id}: {case.name} vector-fit audit")
                    comp["overlay_plot"] = rel(plot_path)
                except Exception as exc:
                    comp["overlay_error"] = str(exc)
            corr_rows.append(comp)
            write_csv(corr_path, corr_rows)
    write_csv(corr_path, corr_rows)
    write_calibration_summary(args.study_dir, read_csv(ranking_path), corr_rows)
    report_command(args)
    return 0


def write_calibration_summary(study_dir: Path, ranking: list[dict[str, str]], corr: list[dict[str, object]]) -> None:
    rank_by_channel = {row.get("channel_id", ""): row for row in ranking}
    rows: list[dict[str, object]] = []
    for split in ("all", "calibration", "holdout"):
        for klass in ("PASS", "WARN", "FAIL"):
            subset = []
            for row in corr:
                info = rank_by_channel.get(str(row.get("channel_id", "")), {})
                if split != "all" and info.get("validation_split") != split:
                    continue
                if info.get("independent_trust_class", info.get("fit_trust_class", "FAIL")) == klass:
                    subset.append(row)
            total = len(subset)
            hpass = sum(1 for row in subset if row.get("hspice_audit_class") == "PASS")
            hwarn = sum(1 for row in subset if row.get("hspice_audit_class") == "WARN")
            hfail = sum(1 for row in subset if row.get("hspice_audit_class") == "FAIL")
            herr = sum(1 for row in subset if row.get("hspice_audit_class") == "ERROR")
            rows.append(
                {
                    "validation_split": split,
                    "independent_class": klass,
                    "hspice_pass": hpass,
                    "hspice_warn": hwarn,
                    "hspice_fail": hfail,
                    "hspice_error": herr,
                    "total": total,
                    "false_pass_rate": "" if klass != "PASS" or total == 0 else (hfail + hwarn + herr) / total,
                }
            )
    write_csv(study_dir / "vf_calibration_summary.csv", rows)


def count_by(rows: list[dict[str, object] | dict[str, str]], key: str) -> Counter:
    return Counter(str(row.get(key, "") or "") for row in rows)


def report_command(args: argparse.Namespace) -> int:
    study_dir = args.study_dir
    metrics = read_csv(study_dir / "vf_metrics.csv") if (study_dir / "vf_metrics.csv").exists() else []
    ranking = read_csv(study_dir / "vf_ranking.csv") if (study_dir / "vf_ranking.csv").exists() else []
    smoke = read_csv(study_dir / "vf_ngspice_smoke.csv") if (study_dir / "vf_ngspice_smoke.csv").exists() else []
    corr = read_csv(study_dir / "vf_hspice_correlation.csv") if (study_dir / "vf_hspice_correlation.csv").exists() else []
    if corr and ranking:
        write_calibration_summary(study_dir, ranking, corr)
    calibration = read_csv(study_dir / "vf_calibration_summary.csv") if (study_dir / "vf_calibration_summary.csv").exists() else []

    lines: list[str] = [
        "# scikit-rf Vector Fitting Campaign",
        "",
        f"Study folder: `{rel(study_dir)}`",
        "",
        "## Summary",
        "",
        f"- Candidate rows: `{len(metrics)}`",
        f"- Ranked channels: `{len(ranking)}`",
        f"- ngspice smoke rows: `{len(smoke)}`",
        f"- HSPICE audit rows: `{len(corr)}`",
        "- HSPICE is audit-only; vector-fit selection is based on independent fit/smoke metrics.",
        "",
        "## Selected Candidate Classes",
        "",
    ]
    for klass, count in count_by(ranking, "independent_trust_class").most_common():
        lines.append(f"- `{klass or 'unclassified'}`: `{count}`")
    lines.extend(["", "## Candidate Outcomes", ""])
    for candidate, count in count_by(metrics, "candidate").most_common():
        passes = sum(1 for row in metrics if row.get("candidate") == candidate and row.get("fit_trust_class") == "PASS")
        warns = sum(1 for row in metrics if row.get("candidate") == candidate and row.get("fit_trust_class") == "WARN")
        fails = sum(1 for row in metrics if row.get("candidate") == candidate and row.get("fit_trust_class") == "FAIL")
        selected = sum(1 for row in ranking if row.get("selected_candidate") == candidate)
        lines.append(f"- `{candidate}`: `{count}` rows, P/W/F `{passes}/{warns}/{fails}`, selected `{selected}`")
    lines.extend(["", "## Preprocessing Outcomes", ""])
    for mode, count in count_by(metrics, "preprocessing_mode").most_common():
        selected = sum(1 for row in ranking if row.get("selected_preprocessing_mode") == mode)
        passes = sum(1 for row in metrics if row.get("preprocessing_mode") == mode and row.get("fit_trust_class") == "PASS")
        warns = sum(1 for row in metrics if row.get("preprocessing_mode") == mode and row.get("fit_trust_class") == "WARN")
        fails = sum(1 for row in metrics if row.get("preprocessing_mode") == mode and row.get("fit_trust_class") == "FAIL")
        lines.append(f"- `{mode}`: `{count}` candidate rows, P/W/F `{passes}/{warns}/{fails}`, selected `{selected}`")
    lines.extend(["", "## Passivity Enforcement", ""])
    for value, count in count_by(metrics, "passivity_enforced").most_common():
        selected = sum(1 for row in ranking if str(row.get("selected_passivity_enforced", "")) == value)
        passes = sum(1 for row in metrics if str(row.get("passivity_enforced", "")) == value and row.get("fit_trust_class") == "PASS")
        warns = sum(1 for row in metrics if str(row.get("passivity_enforced", "")) == value and row.get("fit_trust_class") == "WARN")
        fails = sum(1 for row in metrics if str(row.get("passivity_enforced", "")) == value and row.get("fit_trust_class") == "FAIL")
        lines.append(f"- `{value}`: `{count}` candidate rows, P/W/F `{passes}/{warns}/{fails}`, selected `{selected}`")
    lines.extend(["", "## Best Settings Observed", ""])
    selected_counter = Counter(
        (
            row.get("selected_candidate", ""),
            row.get("selected_preprocessing_mode", ""),
            row.get("selected_init_pole_spacing", ""),
            str(row.get("selected_passivity_enforced", "")),
        )
        for row in ranking
        if row.get("selected_candidate")
    )
    if selected_counter:
        for (candidate, preprocess, spacing, enforced), count in selected_counter.most_common(10):
            lines.append(f"- `{candidate}` preprocess `{preprocess}`, spacing `{spacing}`, enforced `{enforced}`: selected `{count}`")
    else:
        lines.append("- No vector-fit candidate was selected.")
    lines.extend(["", "## Reduced Baseline Context", ""])
    baseline_rows = [row for row in ranking if row.get("reduced_baseline_candidate")]
    if baseline_rows:
        for status, count in Counter(row.get("reduced_baseline_rx_ready_status", "") for row in baseline_rows).most_common():
            lines.append(f"- reduced baseline RX status `{status or 'unknown'}`: `{count}` channels")
    else:
        lines.append("- No reduced baseline match found for these channel paths.")
    lines.extend(["", "## HSPICE Calibration", ""])
    if calibration:
        for row in calibration:
            lines.append(
                f"- split `{row.get('validation_split')}`, independent `{row.get('independent_class')}`: "
                f"HSPICE P/W/F/E `{row.get('hspice_pass')}/{row.get('hspice_warn')}/{row.get('hspice_fail')}/{row.get('hspice_error')}`, "
                f"total `{row.get('total')}`, false-pass `{row.get('false_pass_rate')}`"
            )
    else:
        lines.append("- No HSPICE audit data yet.")
    lines.extend(["", "## Audit Outcomes By Edge", ""])
    if corr:
        for edge, count in Counter(str(row.get("edge_ps", "")) for row in corr).most_common():
            subset = [row for row in corr if str(row.get("edge_ps", "")) == edge]
            outcomes = Counter(str(row.get("hspice_audit_class", "")) for row in subset)
            lines.append(
                f"- edge `{edge} ps`: total `{count}`, HSPICE P/W/F/E "
                f"`{outcomes.get('PASS', 0)}/{outcomes.get('WARN', 0)}/{outcomes.get('FAIL', 0)}/{outcomes.get('ERROR', 0)}`"
            )
    else:
        lines.append("- No HSPICE audit data yet.")
    lines.extend(["", "## Selected Models", ""])
    for row in ranking[:100]:
        lines.append(
            f"- `{row.get('channel_id')}`: `{row.get('selected_candidate_id')}` "
            f"({row.get('independent_trust_class', row.get('fit_trust_class'))}), "
            f"preprocess `{row.get('selected_preprocessing_mode')}`, "
            f"order `{row.get('selected_model_order')}`, "
            f"model `{row.get('selected_model_copy')}`"
        )
    if len(ranking) > 100:
        lines.append(f"- ... {len(ranking) - 100} more")
    lines.extend(
        [
            "",
            "## Interpretation Checklist",
            "",
            "- `FULL_MODEL_READY` requires a selected vector-fit model with independent PASS after smoke checks.",
            "- `dc_hold` indicates the fit used a synthetic DC point copied from the first measured frequency.",
            "- `freq_trim_0p9` and `freq_trim_0p75` fit on trimmed high-frequency data but are scored on the original grid.",
            "- Reduced-model columns, when present, are baseline context only and do not affect vector-fit selection.",
            "",
            "## Reproduction Commands",
            "",
            "Pilot command used for this folder:",
            "",
            "```powershell",
            "py -3.14 scripts/run_sparam_vector_fit_campaign.py fit `",
            "  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12 `",
            '  --skrf-target "$env:TEMP\\ibis_skrf_target" `',
            "  --no-skrf-tests `",
            "  --no-repo-local `",
            "  --extra-touchstone-dir results/converted_sp_comparison_2026-06-12/inputs `",
            "  --candidates vector_3r3c_lin `",
            "  --preprocess raw,dc_hold `",
            "  --dense-samples 101 `",
            "  --skip-passivity-enforcement",
            "```",
            "",
            "Full campaign template:",
            "",
            "```powershell",
            "py -3.14 scripts/run_sparam_vector_fit_campaign.py fit `",
            "  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12 `",
            '  --skrf-target "$env:TEMP\\ibis_skrf_target" `',
            "  --skrf-tests-dir results/sparam_conversion_quality_2026-06-08/inputs/skrf_tests `",
            "  --extra-touchstone-dir hspice/sparam `",
            "  --candidate-profile full `",
            "  --preprocess raw,dc_hold,freq_trim_0p9,freq_trim_0p75 `",
            "  --dense-samples 501",
            "```",
            "",
            "After fitting, run:",
            "",
            "```powershell",
            "py -3.14 scripts/run_sparam_vector_fit_campaign.py smoke-ngspice `",
            "  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12",
            "",
            "py -3.14 scripts/run_sparam_vector_fit_campaign.py audit-hspice `",
            "  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12 `",
            "  --max-channels 20 `",
            "  --resume",
            "```",
            "",
            "## Key Files",
            "",
            "- `manifest.csv`",
            "- `vf_candidates.csv`",
            "- `vf_metrics.csv`",
            "- `vf_ranking.csv`",
            "- `vf_ngspice_smoke.csv`",
            "- `vf_hspice_correlation.csv`",
            "- `vf_calibration_summary.csv`",
            "- `selected_vector_models/`",
            "- `plots/frequency_fit/`",
            "- `plots/passivity/`",
            "- `plots/hspice_overlays/`",
        ]
    )
    study_dir.mkdir(parents=True, exist_ok=True)
    (study_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {study_dir / 'README.md'}")
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY_DIR)
    parser.add_argument("--skrf-target", type=Path, default=None)


def add_inventory_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--skrf-tests-dir", type=Path, default=None)
    parser.add_argument("--extra-touchstone-dir", type=Path, action="append")
    parser.add_argument("--no-skrf-tests", action="store_true")
    parser.add_argument("--no-repo-local", action="store_true")


def add_fit_args(parser: argparse.ArgumentParser) -> None:
    add_inventory_args(parser)
    parser.add_argument("--candidate-profile", choices=("full", "pilot"), default="full")
    parser.add_argument("--candidates", default=None)
    parser.add_argument("--preprocess", action="append", help="Comma-separated preprocessing modes: raw,dc_hold,freq_trim_0p9,freq_trim_0p75")
    parser.add_argument("--max-channels", type=int, default=0)
    parser.add_argument("--channel-id", action="append")
    parser.add_argument("--source-family", action="append")
    parser.add_argument("--dense-samples", type=int, default=1001)
    parser.add_argument("--high-fmax", type=float, default=400e9)
    parser.add_argument("--rms-threshold", type=float, default=0.02)
    parser.add_argument("--mag-db-max-threshold", type=float, default=1.0)
    parser.add_argument("--group-delay-rms-ps-threshold", type=float, default=2.0)
    parser.add_argument("--max-low-freq-start-hz", type=float, default=5e9)
    parser.add_argument("--min-frequency-points", type=int, default=8)
    parser.add_argument("--max-sv-high-threshold", type=float, default=1.05)
    parser.add_argument("--passivity-warn-sv", type=float, default=1.0)
    parser.add_argument("--enforce-samples", type=int, default=2000)
    parser.add_argument("--skip-passivity-enforcement", action="store_true")
    parser.add_argument("--reduced-baseline", type=Path, default=DEFAULT_REDUCED_BASELINE)


def add_smoke_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ngspice", type=Path, default=Path(os.environ.get("NGSPICE_EXE", DEFAULT_NGSPICE)))
    parser.add_argument("--max-channels", type=int, default=0)
    parser.add_argument("--sim-timeout", type=int, default=180)
    parser.add_argument("--smoke-stop-ns", type=float, default=12.0)
    parser.add_argument("--pre-response-fail-v", type=float, default=0.05)
    parser.add_argument("--settling-fail-v", type=float, default=0.08)
    parser.add_argument("--overshoot-fail-pct", type=float, default=65.0)
    parser.add_argument("--overshoot-warn-pct", type=float, default=20.0)
    parser.add_argument("--pre-response-warn-pct", type=float, default=5.0)
    parser.add_argument("--settling-warn-pct", type=float, default=5.0)
    parser.add_argument("--min-smoke-swing-v", type=float, default=0.02)
    parser.add_argument("--min-delay-confidence-swing-v", type=float, default=0.02)


def add_audit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ngspice", type=Path, default=Path(os.environ.get("NGSPICE_EXE", DEFAULT_NGSPICE)))
    parser.add_argument("--hspice", type=Path, default=Path(os.environ.get("HSPICE_EXE", DEFAULT_HSPICE)))
    parser.add_argument("--max-channels", type=int, default=0)
    parser.add_argument("--channel-id", action="append")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--sim-timeout", type=int, default=240)
    parser.add_argument("--audit-stop-ns", type=float, default=35.0)
    parser.add_argument("--hspice-rx-active-rmse-pass-v", type=float, default=0.02)
    parser.add_argument("--hspice-rx-active-maxabs-pass-v", type=float, default=0.075)
    parser.add_argument("--hspice-tx-active-rmse-pass-v", type=float, default=0.05)
    parser.add_argument("--hspice-delay-pass-ps", type=float, default=25.0)
    parser.add_argument("--hspice-min-delay-confidence-swing-v", type=float, default=0.02)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dedicated scikit-rf vector fitting campaign.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inventory = sub.add_parser("inventory")
    add_common_args(p_inventory)
    add_inventory_args(p_inventory)
    p_inventory.set_defaults(func=inventory_command)

    p_fit = sub.add_parser("fit")
    add_common_args(p_fit)
    add_fit_args(p_fit)
    p_fit.set_defaults(func=fit_command)

    p_smoke = sub.add_parser("smoke-ngspice")
    add_common_args(p_smoke)
    add_smoke_args(p_smoke)
    p_smoke.set_defaults(func=smoke_ngspice_command)

    p_audit = sub.add_parser("audit-hspice")
    add_common_args(p_audit)
    add_audit_args(p_audit)
    p_audit.set_defaults(func=audit_hspice_command)

    p_report = sub.add_parser("report")
    add_common_args(p_report)
    p_report.set_defaults(func=report_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.study_dir = args.study_dir.resolve()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
