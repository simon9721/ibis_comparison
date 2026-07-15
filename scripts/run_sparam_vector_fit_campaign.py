from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
from dataclasses import dataclass
import math
import multiprocessing as mp
import os
import queue
from pathlib import Path
import shutil
import subprocess
import sys
import time
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
DEFAULT_EDGE_QUALITY_PS = (5.0, 50.0, 500.0)
PREPROCESS_MODES = (
    "raw",
    "dc_hold",
    "freq_trim_0p95",
    "freq_trim_0p9",
    "freq_trim_0p75",
    "freq_trim_0p5",
    "linear_resample",
    "log_resample",
    "lowfreq_dense",
    "highfreq_dense",
    "hf_hold",
    "hf_rolloff_20db_dec",
    "hf_rolloff_40db_dec",
)
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
    fit_constant: bool = True
    fit_proportional: bool = False
    enforce_dc: bool = True
    n_poles_init_real: int | None = None
    n_poles_init_cmplx: int | None = None
    n_poles_add: int | None = None
    iters_start: int | None = None
    iters_inter: int | None = None
    iters_final: int | None = None
    alpha: float | None = None
    gamma: float | None = None
    nu_samples: float | None = None
    diagnostic_only: bool = False


def fixed_spec(
    n_real: int,
    n_cmplx: int,
    spacing: str,
    fit_constant: bool = True,
    enforce_dc: bool = True,
    fit_proportional: bool = False,
) -> VFCandidateSpec:
    name = f"vector_{n_real}r{n_cmplx}c"
    if not fit_constant:
        name += "_noconst"
    if not enforce_dc:
        name += "_nodc"
    if fit_proportional:
        name += "_propdiag"
    return VFCandidateSpec(
        name,
        "fixed",
        n_real,
        n_cmplx,
        spacing,
        fit_constant=fit_constant,
        fit_proportional=fit_proportional,
        enforce_dc=enforce_dc,
        diagnostic_only=fit_proportional,
    )


def auto_spec(
    name: str,
    target_error: float,
    model_order_max: int,
    n_poles_init_real: int | None = None,
    n_poles_init_cmplx: int | None = None,
    n_poles_add: int | None = None,
    iters_start: int | None = None,
    iters_inter: int | None = None,
    iters_final: int | None = None,
    alpha: float | None = None,
    gamma: float | None = None,
    nu_samples: float | None = None,
    enforce_dc: bool = True,
) -> VFCandidateSpec:
    return VFCandidateSpec(
        name,
        "auto",
        target_error=target_error,
        model_order_max=model_order_max,
        n_poles_init_real=n_poles_init_real,
        n_poles_init_cmplx=n_poles_init_cmplx,
        n_poles_add=n_poles_add,
        iters_start=iters_start,
        iters_inter=iters_inter,
        iters_final=iters_final,
        alpha=alpha,
        gamma=gamma,
        nu_samples=nu_samples,
        enforce_dc=enforce_dc,
    )


def candidate_specs(profile: str = "full", selected: str | None = None) -> list[VFCandidateSpec]:
    auto = [
        auto_spec("auto_fit_default", 0.01, 100),
        auto_spec("auto_fit_tight", 0.005, 80),
        auto_spec("auto_fit_very_tight", 0.001, 100),
    ]
    if profile == "pilot":
        auto = auto[:2]
        specs = auto + [fixed_spec(order, order, spacing) for order in (3, 5, 8) for spacing in ("lin", "log")]
    elif profile == "expanded":
        auto = auto + [
            auto_spec("auto_fit_low_order", 0.01, 40, 2, 2, 2, 2, 2, 3),
            auto_spec("auto_fit_high_order", 0.002, 120, 4, 4, 4, 3, 4, 6),
            auto_spec("auto_fit_slow_precise", 0.001, 160, 6, 6, 4, 4, 4, 8, 0.01, 0.01, 2.0),
            auto_spec("auto_fit_nodc", 0.005, 100, enforce_dc=False),
        ]
        fixed: list[VFCandidateSpec] = []
        fixed_orders = [(order, order) for order in (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20)]
        fixed_orders.extend([(0, 2), (0, 4), (1, 3), (2, 6), (4, 8), (6, 12)])
        for n_real, n_cmplx in fixed_orders:
            for spacing in ("lin", "log"):
                for fit_constant in (True, False):
                    for enforce_dc in (True, False):
                        fixed.append(fixed_spec(n_real, n_cmplx, spacing, fit_constant, enforce_dc))
        for order in (3, 5, 8):
            for spacing in ("lin", "log"):
                fixed.append(fixed_spec(order, order, spacing, fit_proportional=True))
        specs = auto + fixed
    else:
        orders = [1, 2, 3, 4, 5, 6, 8, 10, 12]
        fixed = [fixed_spec(order, order, spacing) for order in orders for spacing in ("lin", "log")]
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
    elif getattr(args, "phase_profile", "custom") == "phase0":
        modes = ["raw", "dc_hold"]
    elif getattr(args, "phase_profile", "custom") == "phase1":
        modes = list(PREPROCESS_MODES)
    elif getattr(args, "phase_profile", "custom") == "phase2":
        modes = ["raw", "dc_hold", "freq_trim_0p95", "freq_trim_0p9", "hf_hold", "hf_rolloff_20db_dec"]
    elif getattr(args, "phase_profile", "custom") == "phase3":
        modes = ["raw", "freq_trim_0p95", "freq_trim_0p9", "hf_hold", "hf_rolloff_20db_dec"]
    else:
        modes = list(PREPROCESS_MODES)
    unknown = sorted(set(modes) - set(PREPROCESS_MODES))
    if unknown:
        raise StudyError(f"Unknown preprocessing modes: {', '.join(unknown)}")
    return modes


def make_network(skrf, base_nw, freqs: np.ndarray, s: np.ndarray, z0: np.ndarray, name: str):
    frequency = skrf.Frequency.from_f(freqs, unit="hz")
    return skrf.Network(frequency=frequency, s=s, z0=z0, name=name)


def interp_complex(freqs: np.ndarray, values: np.ndarray, out_freqs: np.ndarray) -> np.ndarray:
    flat = values.reshape((values.shape[0], -1))
    out = np.empty((len(out_freqs), flat.shape[1]), dtype=complex)
    for idx in range(flat.shape[1]):
        out[:, idx] = np.interp(out_freqs, freqs, flat[:, idx].real) + 1j * np.interp(out_freqs, freqs, flat[:, idx].imag)
    return out.reshape((len(out_freqs),) + values.shape[1:])


def resample_z0(freqs: np.ndarray, z0: np.ndarray, out_freqs: np.ndarray) -> np.ndarray:
    z0_arr = np.asarray(z0, dtype=complex)
    if z0_arr.ndim == 0:
        return np.full((len(out_freqs), 1), z0_arr)
    if z0_arr.shape[0] != len(freqs):
        return np.repeat(z0_arr.reshape((1,) + z0_arr.shape), len(out_freqs), axis=0)
    return interp_complex(freqs, z0_arr, out_freqs)


def preprocess_network(skrf, nw, mode: str, args: argparse.Namespace | None = None):
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
    trim_fracs = {"freq_trim_0p95": 0.95, "freq_trim_0p9": 0.9, "freq_trim_0p75": 0.75, "freq_trim_0p5": 0.5}
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
    resample_points = max(8, int(getattr(args, "resample_points", 301) if args is not None else 301))
    if mode in {"linear_resample", "log_resample", "lowfreq_dense", "highfreq_dense"}:
        f_min = float(freqs[0])
        f_max = float(freqs[-1])
        if mode == "linear_resample":
            out_freqs = np.linspace(f_min, f_max, resample_points)
        elif mode == "log_resample":
            positive_min = float(freqs[0] if freqs[0] > 0.0 else freqs[np.nonzero(freqs > 0.0)[0][0]])
            out_freqs = np.geomspace(positive_min, f_max, resample_points)
            if freqs[0] <= 0.0:
                out_freqs = np.concatenate([[0.0], out_freqs])
        else:
            u = np.linspace(0.0, 1.0, resample_points)
            shaped = u**2 if mode == "lowfreq_dense" else 1.0 - (1.0 - u) ** 2
            out_freqs = f_min + (f_max - f_min) * shaped
        out_s = interp_complex(freqs, s, out_freqs)
        out_z0 = resample_z0(freqs, z0, out_freqs)
        out = make_network(skrf, nw, out_freqs, out_s, out_z0, f"{nw.name}_{mode}")
        return out, {
            "fit_f_min_hz": float(out_freqs[0]),
            "fit_f_max_hz": float(out_freqs[-1]),
            "fit_points": int(len(out_freqs)),
            "preprocess_notes": f"{mode}_{len(freqs)}_to_{len(out_freqs)}_points",
        }
    if mode in {"hf_hold", "hf_rolloff_20db_dec", "hf_rolloff_40db_dec"}:
        high_fmax = float(getattr(args, "high_fmax", freqs[-1]) if args is not None else freqs[-1])
        target = max(float(freqs[-1]), high_fmax)
        if target <= freqs[-1] * 1.001:
            out_freqs = freqs
            out_s = s
            out_z0 = z0
            note = f"{mode}_no_extension_needed"
        else:
            extra_points = max(4, int(getattr(args, "hf_extension_points", 25) if args is not None else 25))
            start = freqs[-1] * 1.001
            extra = np.geomspace(start, target, extra_points)
            if mode == "hf_hold":
                extra_s = np.repeat(s[-1:], len(extra), axis=0)
            else:
                db_per_dec = 20.0 if mode == "hf_rolloff_20db_dec" else 40.0
                scale = (extra / freqs[-1]) ** (-db_per_dec / 20.0)
                extra_s = s[-1:] * scale.reshape((-1, 1, 1))
            extra_z0 = np.repeat(z0[-1:], len(extra), axis=0)
            out_freqs = np.concatenate([freqs, extra])
            out_s = np.concatenate([s, extra_s], axis=0)
            out_z0 = np.concatenate([z0, extra_z0], axis=0)
            note = f"{mode}_extended_to_{target:.12g}_hz"
        out = make_network(skrf, nw, out_freqs, out_s, out_z0, f"{nw.name}_{mode}")
        return out, {
            "fit_f_min_hz": float(out_freqs[0]),
            "fit_f_max_hz": float(out_freqs[-1]),
            "fit_points": int(len(out_freqs)),
            "preprocess_notes": note,
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


def edge_quality_edges(args: argparse.Namespace) -> list[float]:
    return parse_csv_floats(getattr(args, "edge_quality_ps", ""), DEFAULT_EDGE_QUALITY_PS)


def edge_metric_key(edge_ps: float, suffix: str) -> str:
    if float(edge_ps).is_integer():
        label = str(int(edge_ps))
    else:
        label = f"{edge_ps:g}".replace(".", "p")
    return f"edge_{label}ps_{suffix}"


def edge_required_bandwidth_hz(edge_ps: float, args: argparse.Namespace) -> float:
    edge_s = max(float(edge_ps) * 1e-12, 1e-30)
    return float(getattr(args, "edge_bandwidth_factor", 0.35)) / edge_s


def edge_bandwidth_class(ratio: float, args: argparse.Namespace) -> str:
    if not math.isfinite(ratio) or ratio < 0.0:
        return "FAIL"
    if ratio >= float(getattr(args, "edge_bandwidth_pass_ratio", 1.0)):
        return "PASS"
    if ratio >= float(getattr(args, "edge_bandwidth_warn_ratio", 0.25)):
        return "WARN"
    return "FAIL"


def edge_bandwidth_metrics(row: dict[str, object], args: argparse.Namespace) -> dict[str, object]:
    out: dict[str, object] = {}
    try:
        fmax = float(row.get("original_f_max_hz") or 0.0)
    except Exception:
        fmax = 0.0
    warn_edges: list[str] = []
    fail_edges: list[str] = []
    worst_ratio = float("inf")
    worst_edge = ""
    for edge_ps in edge_quality_edges(args):
        required = edge_required_bandwidth_hz(edge_ps, args)
        ratio = fmax / required if required > 0.0 else float("nan")
        klass = edge_bandwidth_class(ratio, args)
        out[edge_metric_key(edge_ps, "required_hz")] = required
        out[edge_metric_key(edge_ps, "bandwidth_ratio")] = ratio
        out[edge_metric_key(edge_ps, "bandwidth_class")] = klass
        if math.isfinite(ratio) and ratio < worst_ratio:
            worst_ratio = ratio
            worst_edge = f"{edge_ps:g}"
        if klass == "WARN":
            warn_edges.append(f"{edge_ps:g}")
        elif klass == "FAIL":
            fail_edges.append(f"{edge_ps:g}")
    out["edge_bandwidth_worst_ratio"] = worst_ratio if math.isfinite(worst_ratio) else ""
    out["edge_bandwidth_worst_edge_ps"] = worst_edge
    out["edge_bandwidth_warn_edges_ps"] = ";".join(warn_edges)
    out["edge_bandwidth_fail_edges_ps"] = ";".join(fail_edges)
    return out


def row_float(row: dict[str, object] | dict[str, str], key: str, default: float = float("nan")) -> float:
    try:
        value = row.get(key, default)
        if value in ("", None):
            return default
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


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
        if number("rx_fit_complex_rms", float("inf")) > args.rms_threshold:
            failures.append("rx_complex_rms_error")
        if number("reflection_fit_complex_rms", float("inf")) > args.rms_threshold:
            failures.append("reflection_complex_rms_error")
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
    row.update(edge_bandwidth_metrics(row, args))
    failures = campaign_math_failures(row, args)
    warnings_out = campaign_warnings(row, args)
    if row.get("diagnostic_only") in (True, "True"):
        warnings_out.append("diagnostic_only_candidate")
    if row.get("edge_bandwidth_warn_edges_ps"):
        warnings_out.append("edge_bandwidth_insufficient")
    if row.get("edge_bandwidth_fail_edges_ps"):
        warnings_out.append("edge_bandwidth_severely_insufficient")
    impulse_ratio = row.get("impulse_pre_peak_energy_ratio", "")
    try:
        if impulse_ratio != "" and math.isfinite(float(impulse_ratio)) and float(impulse_ratio) > args.impulse_preresponse_warn_ratio:
            warnings_out.append("impulse_preresponse_energy")
    except Exception:
        warnings_out.append("impulse_metric_parse")
    row["math_fail_reasons"] = ";".join(failures)
    row["math_warn_reasons"] = ";".join(warnings_out)
    if failures:
        row["fit_trust_class"] = "FAIL"
    elif warnings_out:
        row["fit_trust_class"] = "WARN"
    else:
        row["fit_trust_class"] = "PASS"
    row["independent_score"] = quality_score(row)
    row["full_model_independent_class"] = row["fit_trust_class"]
    row["rx_shape_independent_class"] = "FAIL" if "rx_complex_rms_error" in failures or "dense_singular_value" in failures else row["fit_trust_class"]
    row["rx_timing_independent_class"] = "FAIL" if "group_delay_error" in failures or "rx_group_delay_error" in failures else row["fit_trust_class"]
    row["reflection_independent_class"] = "FAIL" if "reflection_complex_rms_error" in failures or "dense_singular_value" in failures else row["fit_trust_class"]


def impulse_sanity_metrics(eval_nw, vf, args: argparse.Namespace) -> dict[str, object]:
    out: dict[str, object] = {}
    try:
        path_info = dominant_path_info(eval_nw)
        rx_in = int(path_info.get("dominant_input_port") or 1) - 1
        rx_out = int(path_info.get("dominant_output_port") or (2 if eval_nw.nports == 2 else 3)) - 1
        fmax = min(float(args.high_fmax), max(float(eval_nw.frequency.f[-1]), 1.0))
        samples = max(256, int(getattr(args, "impulse_samples", 2048)))
        freqs = np.linspace(0.0, fmax, samples)
        response = np.asarray(vf.get_model_response(rx_out, rx_in, freqs), dtype=complex)
        if not np.all(np.isfinite(response)):
            out["impulse_status"] = "nonfinite"
            return out
        impulse = np.fft.irfft(response, n=2 * (len(freqs) - 1))
        mag = np.abs(impulse)
        total_energy = float(np.sum(mag**2))
        peak_idx = int(np.argmax(mag)) if mag.size else 0
        pre_stop = max(0, peak_idx - 2)
        pre_energy = float(np.sum(mag[:pre_stop] ** 2)) if total_energy > 0.0 else 0.0
        post_mag = mag[peak_idx + 1 :]
        peak = float(mag[peak_idx]) if mag.size else 0.0
        ring_count = int(np.count_nonzero(post_mag > 0.1 * peak)) if peak > 0.0 else 0
        dt = 1.0 / (2.0 * fmax) if fmax > 0.0 else float("nan")
        out.update(
            {
                "impulse_status": "ok",
                "impulse_samples": samples,
                "impulse_fmax_hz": fmax,
                "impulse_peak_time_ns": float(peak_idx * dt * 1e9) if math.isfinite(dt) else "",
                "impulse_pre_peak_energy_ratio": float(pre_energy / total_energy) if total_energy > 0.0 else 0.0,
                "impulse_post_peak_10pct_count": ring_count,
                "impulse_peak_abs": peak,
            }
        )
    except Exception as exc:
        out["impulse_status"] = "error"
        out["impulse_error"] = str(exc)
    return out


def write_candidate_plots(eval_nw, vf, args: argparse.Namespace, channel_dir: Path, row: dict[str, object]) -> None:
    if row.get("fit_status") != "ok":
        return
    if str(row.get("fit_trust_class", "")) not in {"PASS", "WARN"}:
        return
    plot_dir = channel_dir / "models" / str(row["candidate_id"])
    try:
        freq_path = plot_dir / "frequency_fit.png"
        plot_frequency_fit(eval_nw, vf, freq_path, f"{row['channel_id']}: {row['candidate_id']}")
        row["candidate_frequency_plot"] = rel(freq_path)
    except Exception as exc:
        row["candidate_frequency_plot_error"] = str(exc)
    try:
        singular_path = plot_dir / "passivity.png"
        plot_singular(vf, float(args.high_fmax), singular_path, f"{row['channel_id']}: {row['candidate_id']} passivity")
        row["candidate_passivity_plot"] = rel(singular_path)
    except Exception as exc:
        row["candidate_passivity_plot_error"] = str(exc)


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
        "diagnostic_only": spec.diagnostic_only,
        "passivity_enforced": False,
        "init_pole_spacing": spec.init_pole_spacing,
        "n_poles_real": spec.n_poles_real or "",
        "n_poles_cmplx": spec.n_poles_cmplx or "",
        "auto_target_error": spec.target_error or "",
        "auto_model_order_max": spec.model_order_max or "",
        "auto_n_poles_init_real": spec.n_poles_init_real or "",
        "auto_n_poles_init_cmplx": spec.n_poles_init_cmplx or "",
        "auto_n_poles_add": spec.n_poles_add or "",
        "auto_iters_start": spec.iters_start or "",
        "auto_iters_inter": spec.iters_inter or "",
        "auto_iters_final": spec.iters_final or "",
        "auto_alpha": spec.alpha or "",
        "auto_gamma": spec.gamma or "",
        "auto_nu_samples": spec.nu_samples or "",
        "fit_constant": spec.fit_constant,
        "fit_proportional": spec.fit_proportional,
        "enforce_dc": spec.enforce_dc,
        "export_status": "",
        "fit_status": "",
    }
    start = time.perf_counter()
    try:
        vf = VectorFitting(fit_nw)
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            if spec.kind == "auto":
                kwargs = {
                    "target_error": float(spec.target_error or 0.01),
                    "model_order_max": int(spec.model_order_max or 100),
                    "parameter_type": "s",
                    "enforce_dc": bool(spec.enforce_dc),
                }
                for key in ("n_poles_init_real", "n_poles_init_cmplx", "n_poles_add", "iters_start", "iters_inter", "iters_final"):
                    value = getattr(spec, key)
                    if value is not None:
                        kwargs[key] = int(value)
                for key in ("alpha", "gamma", "nu_samples"):
                    value = getattr(spec, key)
                    if value is not None:
                        kwargs[key] = float(value)
                vf.auto_fit(**kwargs)
            else:
                vf.vector_fit(
                    n_poles_real=int(spec.n_poles_real or 0),
                    n_poles_cmplx=int(spec.n_poles_cmplx or 0),
                    init_pole_spacing=spec.init_pole_spacing,
                    parameter_type="s",
                    fit_constant=bool(spec.fit_constant),
                    fit_proportional=bool(spec.fit_proportional),
                    enforce_dc=bool(spec.enforce_dc),
                )
        row["fit_warning_messages"] = "; ".join(str(record.message) for record in records)
        row.update(describe_candidate(eval_nw, vf, args.high_fmax, args.dense_samples))
        row.update(impulse_sanity_metrics(eval_nw, vf, args))
        sp_path = channel_dir / "models" / cid / f"{channel_base['channel_id']}_{cid}.sp"
        sp_path.parent.mkdir(parents=True, exist_ok=True)
        vf.write_spice_subcircuit_s(str(sp_path), fitted_model_name="s_equivalent")
        row["spice_file"] = rel(sp_path)
        row["export_status"] = "ok"
        row["fit_status"] = "ok"
        row["fit_time_s"] = time.perf_counter() - start
        classify_row(row, args)
        write_candidate_plots(eval_nw, vf, args, channel_dir, row)
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


def parse_csv_ints(text: str | None, default: tuple[int, ...]) -> list[int]:
    if not text:
        return list(default)
    return [int(item.strip()) for item in text.split(",") if item.strip()]


def parse_csv_tokens(text: str | None, default: tuple[str, ...]) -> list[str]:
    if not text:
        return list(default)
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_csv_floats(text: str | None, default: tuple[float, ...]) -> list[float]:
    if not text:
        return list(default)
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def parse_csv_bools(text: str | None, default: tuple[bool, ...]) -> list[bool]:
    tokens = parse_csv_tokens(text, tuple("true" if item else "false" for item in default))
    out = []
    for token in tokens:
        lowered = token.lower()
        if lowered in {"1", "true", "yes", "y"}:
            out.append(True)
        elif lowered in {"0", "false", "no", "n"}:
            out.append(False)
        else:
            raise StudyError(f"Invalid boolean token for passivity preserve-dc: {token}")
    return out


def passivity_fmax_value(mode: str, eval_nw, args: argparse.Namespace) -> float:
    original = float(eval_nw.frequency.f[-1])
    if mode == "original":
        return original
    if mode == "2x":
        return 2.0 * original
    if mode == "high":
        return float(args.high_fmax)
    try:
        return float(mode)
    except ValueError as exc:
        raise StudyError(f"Unknown passivity fmax mode: {mode}") from exc


def passivity_configs(args: argparse.Namespace, eval_nw, row: dict[str, object]) -> list[dict[str, object]]:
    strategy = getattr(args, "passivity_strategy", "near-pass")
    if strategy == "off" or getattr(args, "skip_passivity_enforcement", False):
        return []
    if strategy == "near-pass" and not near_pass(row):
        return []
    samples = parse_csv_ints(getattr(args, "enforce_samples_list", ""), (int(getattr(args, "enforce_samples", 2000)),))
    fmax_modes = parse_csv_tokens(getattr(args, "enforce_fmax_list", ""), ("high",))
    preserve = parse_csv_bools(getattr(args, "enforce_preserve_dc_list", ""), (True,))
    out = []
    for sample_count in samples:
        for fmax_mode in fmax_modes:
            for preserve_dc in preserve:
                out.append(
                    {
                        "n_samples": sample_count,
                        "f_max": passivity_fmax_value(fmax_mode, eval_nw, args),
                        "f_max_mode": fmax_mode,
                        "preserve_dc": preserve_dc,
                    }
                )
    return out


def enforce_candidate(
    args: argparse.Namespace,
    eval_nw,
    base_row: dict[str, object],
    vf,
    channel_dir: Path,
    config: dict[str, object] | None = None,
) -> tuple[dict[str, object], object | None]:
    config = config or {"n_samples": args.enforce_samples, "f_max": args.high_fmax, "f_max_mode": "high", "preserve_dc": True}
    row = dict(base_row)
    sample_count = int(config["n_samples"])
    fmax_mode = str(config.get("f_max_mode", "high")).replace(".", "p")
    preserve_dc = bool(config.get("preserve_dc", True))
    row["candidate_id"] = f"{base_row['candidate_id']}_enforced_s{sample_count}_{fmax_mode}_pdc{int(preserve_dc)}"
    row["candidate_family"] = "full_vector_fit_enforced"
    row["passivity_enforced"] = True
    row["passivity_enforce_samples"] = sample_count
    row["passivity_enforce_fmax_hz"] = float(config["f_max"])
    row["passivity_enforce_fmax_mode"] = config.get("f_max_mode", "high")
    row["passivity_enforce_preserve_dc"] = preserve_dc
    start = time.perf_counter()
    try:
        vf = copy.deepcopy(vf)
        vf.passivity_enforce(n_samples=sample_count, f_max=float(config["f_max"]), preserve_dc=preserve_dc)
        row.update(describe_candidate(eval_nw, vf, args.high_fmax, args.dense_samples))
        row.update(impulse_sanity_metrics(eval_nw, vf, args))
        try:
            row["enforcement_fit_complex_rms_delta"] = float(row.get("fit_complex_rms", 0.0)) - float(base_row.get("fit_complex_rms", 0.0))
            row["enforcement_rx_fit_complex_rms_delta"] = float(row.get("rx_fit_complex_rms", 0.0)) - float(base_row.get("rx_fit_complex_rms", 0.0))
            row["enforcement_max_sv_high_delta"] = float(row.get("max_sv_high", 0.0)) - float(base_row.get("max_sv_high", 0.0))
        except Exception:
            row["enforcement_delta_error"] = "parse_error"
        sp_path = channel_dir / "models" / str(row["candidate_id"]) / f"{base_row['channel_id']}_{row['candidate_id']}.sp"
        sp_path.parent.mkdir(parents=True, exist_ok=True)
        vf.write_spice_subcircuit_s(str(sp_path), fitted_model_name="s_equivalent")
        row["spice_file"] = rel(sp_path)
        row["export_status"] = "ok"
        row["fit_status"] = "ok"
        row["enforcement_time_s"] = time.perf_counter() - start
        classify_row(row, args)
        write_candidate_plots(eval_nw, vf, args, channel_dir, row)
        return row, vf
    except Exception as exc:
        row["fit_status"] = "error"
        row["fit_error"] = f"passivity_enforce:{exc}"
        row["math_fail_reasons"] = "passivity_enforce_error"
        row["fit_trust_class"] = "FAIL"
        row["independent_score"] = 1e9
        return row, None


def candidate_metadata(channel_base: dict[str, object], preprocess: str, spec: VFCandidateSpec) -> dict[str, object]:
    return {
        **channel_base,
        "candidate_id": candidate_id(preprocess, spec),
        "candidate": spec.name,
        "candidate_family": "full_vector_fit",
        "preprocessing_mode": preprocess,
        "fit_source": "vector_fit_frequency_domain",
        "use_scope": "general_multiport",
        "view_role": "full_model",
        "diagnostic_only": spec.diagnostic_only,
        "passivity_enforced": False,
        "init_pole_spacing": spec.init_pole_spacing,
        "n_poles_real": spec.n_poles_real or "",
        "n_poles_cmplx": spec.n_poles_cmplx or "",
        "auto_target_error": spec.target_error or "",
        "auto_model_order_max": spec.model_order_max or "",
        "auto_n_poles_init_real": spec.n_poles_init_real or "",
        "auto_n_poles_init_cmplx": spec.n_poles_init_cmplx or "",
        "auto_n_poles_add": spec.n_poles_add or "",
        "auto_iters_start": spec.iters_start or "",
        "auto_iters_inter": spec.iters_inter or "",
        "auto_iters_final": spec.iters_final or "",
        "auto_alpha": spec.alpha or "",
        "auto_gamma": spec.gamma or "",
        "auto_nu_samples": spec.nu_samples or "",
        "fit_constant": spec.fit_constant,
        "fit_proportional": spec.fit_proportional,
        "enforce_dc": spec.enforce_dc,
    }


def timeout_or_error_row(
    channel_base: dict[str, object],
    preprocess: str,
    spec: VFCandidateSpec,
    status: str,
    message: str,
    elapsed_s: float,
) -> dict[str, object]:
    row = candidate_metadata(channel_base, preprocess, spec)
    row.update(
        {
            "fit_status": status,
            "fit_error": message,
            "export_status": "",
            "fit_time_s": elapsed_s,
            "fit_trust_class": "FAIL",
            "full_model_independent_class": "FAIL",
            "rx_shape_independent_class": "FAIL",
            "rx_timing_independent_class": "FAIL",
            "reflection_independent_class": "FAIL",
            "math_fail_reasons": "candidate_timeout" if status == "timeout" else "candidate_error",
            "math_warn_reasons": "",
            "independent_score": 1e9,
        }
    )
    return row


def fit_candidate_bundle(
    args: argparse.Namespace,
    channel_path: Path,
    channel_base: dict[str, object],
    preprocess: str,
    spec: VFCandidateSpec,
    channel_dir: Path,
) -> list[dict[str, object]]:
    skrf, _ = ensure_skrf(args.skrf_target)
    eval_nw = skrf.Network(str(channel_path))
    fit_nw, preprocess_info = preprocess_network(skrf, eval_nw, preprocess, args)
    row, vf = fit_one_candidate(args, skrf, eval_nw, fit_nw, channel_base, preprocess, preprocess_info, spec, channel_dir)
    rows: list[dict[str, object]] = [row]
    if vf is not None:
        for config in passivity_configs(args, eval_nw, row):
            enforced_row, _ = enforce_candidate(args, eval_nw, row, vf, channel_dir, config)
            rows.append(enforced_row)
    return rows


def fit_bundle_worker(
    out_queue,
    args: argparse.Namespace,
    channel_path: str,
    channel_base: dict[str, object],
    preprocess: str,
    spec: VFCandidateSpec,
    channel_dir: str,
) -> None:
    try:
        rows = fit_candidate_bundle(args, Path(channel_path), channel_base, preprocess, spec, Path(channel_dir))
        out_queue.put({"status": "ok", "rows": rows})
    except Exception as exc:
        out_queue.put({"status": "error", "error": str(exc)})


def run_fit_candidate_bundle(
    args: argparse.Namespace,
    channel_path: Path,
    channel_base: dict[str, object],
    preprocess: str,
    spec: VFCandidateSpec,
    channel_dir: Path,
) -> list[dict[str, object]]:
    timeout_s = float(getattr(args, "candidate_timeout_s", 0.0) or 0.0)
    if timeout_s <= 0.0:
        start = time.perf_counter()
        try:
            return fit_candidate_bundle(args, channel_path, channel_base, preprocess, spec, channel_dir)
        except Exception as exc:
            return [timeout_or_error_row(channel_base, preprocess, spec, "error", str(exc), time.perf_counter() - start)]
    start = time.perf_counter()
    ctx = mp.get_context("spawn")
    out_queue = ctx.Queue()
    proc = ctx.Process(
        target=fit_bundle_worker,
        args=(out_queue, args, str(channel_path), channel_base, preprocess, spec, str(channel_dir)),
    )
    proc.start()
    proc.join(timeout_s)
    elapsed = time.perf_counter() - start
    if proc.is_alive():
        proc.terminate()
        proc.join(5.0)
        return [timeout_or_error_row(channel_base, preprocess, spec, "timeout", f"candidate exceeded {timeout_s:.3g}s", elapsed)]
    try:
        payload = out_queue.get_nowait()
    except queue.Empty:
        if proc.exitcode == 0:
            return [timeout_or_error_row(channel_base, preprocess, spec, "error", "worker returned no result", elapsed)]
        return [timeout_or_error_row(channel_base, preprocess, spec, "error", f"worker exit code {proc.exitcode}", elapsed)]
    if payload.get("status") == "ok":
        return list(payload.get("rows", []))
    return [timeout_or_error_row(channel_base, preprocess, spec, "error", str(payload.get("error", "worker error")), elapsed)]


def start_fit_candidate_process(
    ctx,
    args: argparse.Namespace,
    channel_path: Path,
    channel_base: dict[str, object],
    preprocess: str,
    spec: VFCandidateSpec,
    channel_dir: Path,
) -> dict[str, object]:
    out_queue = ctx.Queue()
    proc = ctx.Process(
        target=fit_bundle_worker,
        args=(out_queue, args, str(channel_path), channel_base, preprocess, spec, str(channel_dir)),
    )
    proc.start()
    return {
        "process": proc,
        "queue": out_queue,
        "start": time.perf_counter(),
        "channel_base": channel_base,
        "preprocess": preprocess,
        "spec": spec,
    }


def finish_fit_process(task: dict[str, object], timeout_s: float) -> list[dict[str, object]] | None:
    proc = task["process"]
    elapsed = time.perf_counter() - float(task["start"])
    channel_base = task["channel_base"]
    preprocess = str(task["preprocess"])
    spec = task["spec"]
    assert isinstance(channel_base, dict)
    assert isinstance(spec, VFCandidateSpec)
    if proc.is_alive():
        if timeout_s > 0.0 and elapsed > timeout_s:
            proc.terminate()
            proc.join(5.0)
            return [timeout_or_error_row(channel_base, preprocess, spec, "timeout", f"candidate exceeded {timeout_s:.3g}s", elapsed)]
        return None
    proc.join()
    out_queue = task["queue"]
    try:
        payload = out_queue.get_nowait()
    except queue.Empty:
        if proc.exitcode == 0:
            return [timeout_or_error_row(channel_base, preprocess, spec, "error", "worker returned no result", elapsed)]
        return [timeout_or_error_row(channel_base, preprocess, spec, "error", f"worker exit code {proc.exitcode}", elapsed)]
    if payload.get("status") == "ok":
        return list(payload.get("rows", []))
    return [timeout_or_error_row(channel_base, preprocess, spec, "error", str(payload.get("error", "worker error")), elapsed)]


def run_fit_tasks(
    args: argparse.Namespace,
    channel_path: Path,
    base: dict[str, object],
    channel_dir: Path,
    tasks: list[tuple[str, VFCandidateSpec]],
):
    workers = max(1, int(getattr(args, "workers", 1) or 1))
    timeout_s = float(getattr(args, "candidate_timeout_s", 0.0) or 0.0)
    if workers <= 1:
        for mode, spec in tasks:
            yield run_fit_candidate_bundle(args, channel_path, base, mode, spec, channel_dir)
        return
    ctx = mp.get_context("spawn")
    pending = list(tasks)
    active: list[dict[str, object]] = []
    while pending or active:
        while pending and len(active) < workers:
            mode, spec = pending.pop(0)
            active.append(start_fit_candidate_process(ctx, args, channel_path, base, mode, spec, channel_dir))
        completed: list[dict[str, object]] = []
        for task in active:
            rows = finish_fit_process(task, timeout_s)
            if rows is not None:
                completed.append(task)
                yield rows
        active = [task for task in active if task not in completed]
        if active and not completed:
            time.sleep(0.25)


def select_best(rows: list[dict[str, object]]) -> dict[str, object] | None:
    eligible = [
        row
        for row in rows
        if row.get("fit_trust_class") in ("PASS", "WARN")
        and row.get("spice_file")
        and row.get("diagnostic_only") not in (True, "True")
    ]
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
    if args.candidate_profile is None:
        args.candidate_profile = {
            "phase0": "pilot",
            "phase1": "expanded",
            "phase2": "full",
            "phase3": "full",
            "custom": "full",
        }.get(getattr(args, "phase_profile", "custom"), "full")
    specs = candidate_specs(args.candidate_profile, args.candidates)
    modes = preprocessing_modes(args)
    baseline = load_reduced_baseline(args.reduced_baseline)
    args.study_dir.mkdir(parents=True, exist_ok=True)
    candidate_grid = [
        {
            "candidate": spec.name,
            "candidate_id_example": candidate_id("<preprocess>", spec),
            "kind": spec.kind,
            "n_poles_real": spec.n_poles_real or "",
            "n_poles_cmplx": spec.n_poles_cmplx or "",
            "init_pole_spacing": spec.init_pole_spacing,
            "target_error": spec.target_error or "",
            "model_order_max": spec.model_order_max or "",
            "fit_constant": spec.fit_constant,
            "fit_proportional": spec.fit_proportional,
            "enforce_dc": spec.enforce_dc,
            "auto_n_poles_init_real": spec.n_poles_init_real or "",
            "auto_n_poles_init_cmplx": spec.n_poles_init_cmplx or "",
            "auto_n_poles_add": spec.n_poles_add or "",
            "auto_iters_start": spec.iters_start or "",
            "auto_iters_inter": spec.iters_inter or "",
            "auto_iters_final": spec.iters_final or "",
            "auto_alpha": spec.alpha or "",
            "auto_gamma": spec.gamma or "",
            "auto_nu_samples": spec.nu_samples or "",
            "diagnostic_only": spec.diagnostic_only,
        }
        for spec in specs
    ]
    write_csv(args.study_dir / "vf_candidate_grid.csv", candidate_grid)
    write_csv(args.study_dir / "vf_candidates.csv", candidate_grid)

    metrics_path = args.study_dir / "vf_metrics.csv"
    all_rows: list[dict[str, object]] = list(read_csv(metrics_path)) if args.resume and metrics_path.exists() else []
    done_base = {
        (str(row.get("channel_id", "")), str(row.get("candidate_id", "")))
        for row in all_rows
        if str(row.get("passivity_enforced", "")) not in {"True", "true", "1"}
    }
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
        base.update(edge_bandwidth_metrics(base, args))
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
        channel_rows: list[dict[str, object]] = [row for row in all_rows if str(row.get("channel_id", "")) == str(channel_id)]
        task_specs: list[tuple[str, VFCandidateSpec]] = []
        for mode in modes:
            for spec in specs:
                base_cid = candidate_id(mode, spec)
                if args.resume and (str(channel_id), base_cid) in done_base:
                    continue
                task_specs.append((mode, spec))
        for rows in run_fit_tasks(args, channel_path, base, channel_dir, task_specs):
            channel_rows.extend(rows)
            all_rows.extend(rows)
            for row in rows:
                base_cid = str(row.get("candidate_id", ""))
                if "_enforced_" in base_cid:
                    base_cid = base_cid.split("_enforced_", 1)[0]
                done_base.add((str(channel_id), base_cid))
            write_csv(metrics_path, all_rows)
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
            write_csv(args.study_dir / "vf_ranking.csv", ranking)
            continue
        selected_copy = args.study_dir / "selected_vector_models" / f"{channel_id}.sp"
        selected_source = ROOT / str(selected["spice_file"])
        selected_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(selected_source, selected_copy)
        if selected.get("candidate_frequency_plot"):
            freq_dest = args.study_dir / "plots" / "frequency_fit" / f"{channel_id}_{selected['candidate_id']}.png"
            freq_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / str(selected["candidate_frequency_plot"]), freq_dest)
        if selected.get("candidate_passivity_plot"):
            pass_dest = args.study_dir / "plots" / "passivity" / f"{channel_id}_{selected['candidate_id']}.png"
            pass_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / str(selected["candidate_passivity_plot"]), pass_dest)
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
                "selected_impulse_pre_peak_energy_ratio": selected.get("impulse_pre_peak_energy_ratio", ""),
                "selected_edge_bandwidth_worst_ratio": selected.get("edge_bandwidth_worst_ratio", ""),
                "selected_edge_bandwidth_worst_edge_ps": selected.get("edge_bandwidth_worst_edge_ps", ""),
                "selected_edge_bandwidth_warn_edges_ps": selected.get("edge_bandwidth_warn_edges_ps", ""),
                "selected_edge_bandwidth_fail_edges_ps": selected.get("edge_bandwidth_fail_edges_ps", ""),
                "fit_trust_class": selected.get("fit_trust_class", ""),
                "full_model_independent_class": selected.get("full_model_independent_class", selected.get("fit_trust_class", "")),
                "rx_shape_independent_class": selected.get("rx_shape_independent_class", ""),
                "rx_timing_independent_class": selected.get("rx_timing_independent_class", ""),
                "reflection_independent_class": selected.get("reflection_independent_class", ""),
                "math_fail_reasons": selected.get("math_fail_reasons", ""),
                "math_warn_reasons": selected.get("math_warn_reasons", ""),
                "independent_score": selected.get("independent_score", ""),
                "independent_trust_class": selected.get("fit_trust_class", ""),
                "full_model_ready_status": "FULL_MODEL_READY" if selected.get("fit_trust_class") == "PASS" else str(selected.get("fit_trust_class", "FAIL")),
                "reason": "selected_by_vector_fit_independent_score",
                **{
                    f"selected_{edge_metric_key(edge_ps, 'bandwidth_ratio')}": selected.get(edge_metric_key(edge_ps, "bandwidth_ratio"), "")
                    for edge_ps in edge_quality_edges(args)
                },
                **{
                    f"selected_{edge_metric_key(edge_ps, 'bandwidth_class')}": selected.get(edge_metric_key(edge_ps, "bandwidth_class"), "")
                    for edge_ps in edge_quality_edges(args)
                },
            }
        )
        write_csv(args.study_dir / "vf_ranking.csv", ranking)

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
        for key in ("full_model_independent_class", "rx_shape_independent_class", "rx_timing_independent_class", "reflection_independent_class"):
            if out["independent_trust_class"] != "PASS":
                out[key] = out["independent_trust_class"]
            elif not out.get(key):
                out[key] = "PASS"
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
    audit_rows_in: list[dict[str, str]] = list(ranking)
    if int(getattr(args, "audit_top_k", 1) or 1) > 1:
        metrics_by_channel: dict[str, list[dict[str, str]]] = defaultdict(list)
        for metric_row in read_csv(args.study_dir / "vf_metrics.csv"):
            if metric_row.get("spice_file") and metric_row.get("diagnostic_only") not in ("True", "true", "1"):
                metrics_by_channel[str(metric_row.get("channel_id", ""))].append(metric_row)
        for rank_row in ranking:
            channel_id = str(rank_row.get("channel_id", ""))
            selected_id = str(rank_row.get("selected_candidate_id", ""))
            candidates = sorted(
                metrics_by_channel.get(channel_id, []),
                key=lambda row: (
                    TRUST_RANK.get(str(row.get("fit_trust_class", "FAIL")), 9),
                    len([item for item in str(row.get("math_warn_reasons", "")).split(";") if item]),
                    float(row.get("independent_score") or 1e9),
                    int(float(row.get("model_order") or 999)),
                ),
            )
            added = 0
            for cand in candidates:
                cid = str(cand.get("candidate_id", ""))
                if not cid or cid == selected_id:
                    continue
                audit_row = dict(rank_row)
                audit_row.update(
                    {
                        "selected_candidate_id": cid,
                        "selected_candidate": cand.get("candidate", ""),
                        "selected_preprocessing_mode": cand.get("preprocessing_mode", ""),
                        "selected_init_pole_spacing": cand.get("init_pole_spacing", ""),
                        "selected_passivity_enforced": cand.get("passivity_enforced", ""),
                        "selected_spice_file": cand.get("spice_file", ""),
                        "selected_model_copy": cand.get("spice_file", ""),
                        "selected_model_order": cand.get("model_order", ""),
                        "fit_trust_class": cand.get("fit_trust_class", ""),
                        "independent_trust_class": cand.get("fit_trust_class", ""),
                        "full_model_ready_status": "FULL_MODEL_READY" if cand.get("fit_trust_class") == "PASS" else cand.get("fit_trust_class", "FAIL"),
                    }
                )
                audit_rows_in.append(audit_row)
                added += 1
                if added >= int(args.audit_top_k) - 1:
                    break
    existing: list[dict[str, object]] = []
    corr_path = args.study_dir / "vf_hspice_correlation.csv"
    done: set[tuple[str, str, str]] = set()
    if args.resume and corr_path.exists():
        existing = list(read_csv(corr_path))
        done = {(str(row.get("channel_id", "")), str(row.get("candidate_id", "")), str(row.get("case", ""))) for row in existing}
    corr_rows: list[dict[str, object]] = list(existing)
    for idx, row in enumerate(audit_rows_in, start=1):
        channel_id = row["channel_id"]
        print(f"[{idx}/{len(audit_rows_in)}] HSPICE audit {channel_id} {row.get('selected_candidate_id', '')}")
        touchstone = ROOT / row["channel_path"]
        model = ROOT / row["selected_model_copy"]
        nports = int(row["ports"])
        out_dir = args.study_dir / "channels" / channel_id / "vf_hspice_audit" / row["selected_candidate_id"]
        ngspice_dir = out_dir / "ngspice"
        local_model = ngspice_dir / "model.sp"
        ngspice_dir.mkdir(parents=True, exist_ok=True)
        if model.resolve() != local_model.resolve():
            shutil.copy2(model, local_model)
        for case in audit_cases(args.audit_stop_ns):
            if (channel_id, str(row.get("selected_candidate_id", "")), case.name) in done:
                continue
            hrow = run_hspice_case(args.hspice, touchstone, nports, out_dir, case, args.sim_timeout)
            ng_rows = run_ngspice_cases(args.ngspice, local_model, nports, ngspice_dir, [case], args.sim_timeout)
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
                    "ngspice_model_copy": rel(local_model),
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
    generate_post_audit_artifacts(args.study_dir)
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
                independent = row.get("independent_trust_class") or info.get("independent_trust_class", info.get("fit_trust_class", "FAIL"))
                if independent == klass:
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


def edge_class_for_channel(row: dict[str, object] | dict[str, str], edge_ps: float, args: argparse.Namespace) -> str:
    metrics = edge_bandwidth_metrics(dict(row), args)
    return str(metrics.get(edge_metric_key(edge_ps, "bandwidth_class"), "") or "unknown")


def edge_ratio_for_channel(row: dict[str, object] | dict[str, str], edge_ps: float, args: argparse.Namespace) -> float:
    metrics = edge_bandwidth_metrics(dict(row), args)
    return row_float(metrics, edge_metric_key(edge_ps, "bandwidth_ratio"))


def write_edge_bandwidth_summaries(
    study_dir: Path,
    ranking: list[dict[str, str]],
    corr: list[dict[str, object]],
    args: argparse.Namespace,
) -> None:
    edges = edge_quality_edges(args)
    selected_rows: list[dict[str, object]] = []
    selected_by_channel = {str(row.get("channel_id", "")): row for row in ranking}
    selected_candidate_by_channel = {str(row.get("channel_id", "")): str(row.get("selected_candidate_id", "")) for row in ranking}
    for row in ranking:
        out: dict[str, object] = {
            "channel_id": row.get("channel_id", ""),
            "selected_candidate_id": row.get("selected_candidate_id", ""),
            "ports": row.get("ports", ""),
            "points": row.get("points", ""),
            "original_f_max_hz": row.get("original_f_max_hz", ""),
            "independent_trust_class": row.get("independent_trust_class", row.get("fit_trust_class", "")),
        }
        metrics = edge_bandwidth_metrics(dict(row), args)
        for edge_ps in edges:
            out[edge_metric_key(edge_ps, "required_hz")] = metrics.get(edge_metric_key(edge_ps, "required_hz"), "")
            out[edge_metric_key(edge_ps, "bandwidth_ratio")] = metrics.get(edge_metric_key(edge_ps, "bandwidth_ratio"), "")
            out[edge_metric_key(edge_ps, "bandwidth_class")] = metrics.get(edge_metric_key(edge_ps, "bandwidth_class"), "")
            selected_corr = [
                item
                for item in corr
                if str(item.get("channel_id", "")) == str(row.get("channel_id", ""))
                and str(item.get("candidate_id", "")) == str(row.get("selected_candidate_id", ""))
                and str(item.get("edge_ps", "")) == f"{edge_ps:.1f}"
            ]
            if selected_corr:
                outcomes = Counter(str(item.get("hspice_audit_class", "")) for item in selected_corr)
                out[edge_metric_key(edge_ps, "selected_hspice_pass")] = outcomes.get("PASS", 0)
                out[edge_metric_key(edge_ps, "selected_hspice_warn")] = outcomes.get("WARN", 0)
                out[edge_metric_key(edge_ps, "selected_hspice_fail")] = outcomes.get("FAIL", 0)
                out[edge_metric_key(edge_ps, "selected_hspice_error")] = outcomes.get("ERROR", 0)
        selected_rows.append(out)
    write_csv(study_dir / "vf_selected_edge_readiness.csv", selected_rows)

    calib_rows: list[dict[str, object]] = []
    for edge_ps in edges:
        edge_corr = [row for row in corr if str(row.get("edge_ps", "")) == f"{edge_ps:.1f}"]
        for bandwidth_class in ("PASS", "WARN", "FAIL", "unknown"):
            subset = [
                row
                for row in edge_corr
                if edge_class_for_channel(selected_by_channel.get(str(row.get("channel_id", "")), {}), edge_ps, args) == bandwidth_class
            ]
            if not subset:
                continue
            outcomes = Counter(str(row.get("hspice_audit_class", "")) for row in subset)
            selected_subset = [
                row
                for row in subset
                if str(row.get("candidate_id", "")) == selected_candidate_by_channel.get(str(row.get("channel_id", "")), "")
            ]
            selected_outcomes = Counter(str(row.get("hspice_audit_class", "")) for row in selected_subset)
            calib_rows.append(
                {
                    "edge_ps": edge_ps,
                    "required_bandwidth_hz": edge_required_bandwidth_hz(edge_ps, args),
                    "bandwidth_class": bandwidth_class,
                    "hspice_pass": outcomes.get("PASS", 0),
                    "hspice_warn": outcomes.get("WARN", 0),
                    "hspice_fail": outcomes.get("FAIL", 0),
                    "hspice_error": outcomes.get("ERROR", 0),
                    "total": len(subset),
                    "selected_hspice_pass": selected_outcomes.get("PASS", 0),
                    "selected_hspice_warn": selected_outcomes.get("WARN", 0),
                    "selected_hspice_fail": selected_outcomes.get("FAIL", 0),
                    "selected_hspice_error": selected_outcomes.get("ERROR", 0),
                    "selected_total": len(selected_subset),
                }
            )
    write_csv(study_dir / "vf_edge_bandwidth_calibration.csv", calib_rows)

    adjusted_rows: list[dict[str, object]] = []
    annotated: list[dict[str, object]] = []
    for row in corr:
        channel = selected_by_channel.get(str(row.get("channel_id", "")), {})
        edge_ps = row_float(row, "edge_ps")
        bandwidth_class = edge_class_for_channel(channel, edge_ps, args) if math.isfinite(edge_ps) else "unknown"
        independent = str(row.get("independent_trust_class") or "FAIL")
        adjusted = independent
        if independent == "PASS" and bandwidth_class in {"WARN", "FAIL", "unknown"}:
            adjusted = "FAIL" if bandwidth_class == "FAIL" else "WARN"
        out = dict(row)
        out["edge_bandwidth_class"] = bandwidth_class
        out["edge_adjusted_independent_class"] = adjusted
        annotated.append(out)
    write_csv(study_dir / "vf_edge_adjusted_hspice_correlation.csv", annotated)

    for split in ("all", "calibration", "holdout"):
        for edge_token in ["all"] + [f"{edge:g}" for edge in edges]:
            for klass in ("PASS", "WARN", "FAIL"):
                subset = []
                for row in annotated:
                    if split != "all" and str(row.get("validation_split", "")) != split:
                        continue
                    if edge_token != "all" and str(row.get("edge_ps", "")) != f"{float(edge_token):.1f}":
                        continue
                    if str(row.get("edge_adjusted_independent_class", "")) == klass:
                        subset.append(row)
                if not subset:
                    continue
                outcomes = Counter(str(row.get("hspice_audit_class", "")) for row in subset)
                total = len(subset)
                adjusted_rows.append(
                    {
                        "validation_split": split,
                        "edge_ps": edge_token,
                        "edge_adjusted_independent_class": klass,
                        "hspice_pass": outcomes.get("PASS", 0),
                        "hspice_warn": outcomes.get("WARN", 0),
                        "hspice_fail": outcomes.get("FAIL", 0),
                        "hspice_error": outcomes.get("ERROR", 0),
                        "total": total,
                        "false_pass_rate": ""
                        if klass != "PASS"
                        else (outcomes.get("WARN", 0) + outcomes.get("FAIL", 0) + outcomes.get("ERROR", 0)) / total,
                    }
                )
    write_csv(study_dir / "vf_edge_adjusted_calibration_summary.csv", adjusted_rows)


def plot_edge_bandwidth_summaries(study_dir: Path, args: argparse.Namespace) -> None:
    out_dir = study_dir / "plots" / "edge_bandwidth"
    out_dir.mkdir(parents=True, exist_ok=True)
    calib_path = study_dir / "vf_edge_bandwidth_calibration.csv"
    if calib_path.exists():
        rows = read_csv(calib_path)
        if rows:
            labels = [f"{float(row.get('edge_ps') or 0):g} ps\n{row.get('bandwidth_class')}" for row in rows]
            pass_v = np.asarray([row_float(row, "hspice_pass", 0.0) for row in rows], dtype=float)
            warn_v = np.asarray([row_float(row, "hspice_warn", 0.0) for row in rows], dtype=float)
            fail_v = np.asarray([row_float(row, "hspice_fail", 0.0) for row in rows], dtype=float)
            err_v = np.asarray([row_float(row, "hspice_error", 0.0) for row in rows], dtype=float)
            x = np.arange(len(rows))
            fig, ax = plt.subplots(figsize=(max(7.0, 1.35 * len(rows)), 4.2))
            ax.bar(x, pass_v, label="HSPICE PASS", color="#2f8f46")
            ax.bar(x, warn_v, bottom=pass_v, label="HSPICE WARN", color="#d99a24")
            ax.bar(x, fail_v, bottom=pass_v + warn_v, label="HSPICE FAIL", color="#bf3b3b")
            ax.bar(x, err_v, bottom=pass_v + warn_v + fail_v, label="ERROR", color="#777777")
            ax.set_title("Edge Bandwidth Class vs HSPICE Audit")
            ax.set_ylabel("Audited cases")
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.grid(axis="y", alpha=0.25)
            ax.legend(loc="upper right", ncols=2, fontsize=8)
            fig.tight_layout()
            fig.savefig(out_dir / "edge_bandwidth_vs_hspice.png", dpi=180)
            plt.close(fig)

    selected_path = study_dir / "vf_selected_edge_readiness.csv"
    if selected_path.exists():
        rows = [row for row in read_csv(selected_path) if row.get("selected_candidate_id")]
        edges = edge_quality_edges(args)
        if rows and edges:
            x = np.arange(len(rows))
            width = min(0.24, 0.75 / max(len(edges), 1))
            fig, ax = plt.subplots(figsize=(max(9.0, 0.9 * len(rows)), 4.8))
            colors = ["#4c78a8", "#72b7b2", "#f58518", "#b279a2"]
            for idx, edge_ps in enumerate(edges):
                ratios = [row_float(row, edge_metric_key(edge_ps, "bandwidth_ratio"), float("nan")) for row in rows]
                ax.bar(x + (idx - (len(edges) - 1) / 2) * width, ratios, width=width, label=f"{edge_ps:g} ps", color=colors[idx % len(colors)])
            ax.axhline(float(getattr(args, "edge_bandwidth_pass_ratio", 1.0)), color="#2f8f46", linestyle="--", linewidth=1.1, label="PASS line")
            ax.axhline(float(getattr(args, "edge_bandwidth_warn_ratio", 0.25)), color="#d99a24", linestyle="--", linewidth=1.1, label="WARN line")
            ax.set_yscale("log")
            ax.set_ylabel("Touchstone fmax / required edge bandwidth")
            ax.set_title("Selected Model Edge Bandwidth Readiness")
            labels = [str(row.get("channel_id", "")).replace("_", "\n", 1) for row in rows]
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
            ax.grid(axis="y", which="both", alpha=0.25)
            ax.legend(loc="upper right", ncols=2, fontsize=8)
            fig.tight_layout()
            fig.savefig(out_dir / "selected_edge_bandwidth_ratios.png", dpi=180)
            plt.close(fig)


def generate_post_audit_artifacts(study_dir: Path) -> None:
    helpers = [
        [
            sys.executable,
            str(SCRIPT_DIR / "generate_vector_fit_side_overlays.py"),
            "--study-dir",
            str(study_dir),
            "--out-dir",
            str(study_dir / "plots" / "side_overlays"),
        ],
        [
            sys.executable,
            str(SCRIPT_DIR / "package_vector_fit_audit_share.py"),
            "--study-dir",
            str(study_dir),
        ],
    ]
    for cmd in helpers:
        script = Path(cmd[1])
        if not script.exists():
            print(f"[warn] post-audit helper missing: {script}")
            continue
        completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        if completed.returncode != 0:
            print(f"[warn] post-audit helper failed ({script.name}): {completed.stderr.strip()}")


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
    if ranking:
        write_edge_bandwidth_summaries(study_dir, ranking, corr, args)
        plot_edge_bandwidth_summaries(study_dir, args)
    calibration = read_csv(study_dir / "vf_calibration_summary.csv") if (study_dir / "vf_calibration_summary.csv").exists() else []
    edge_calibration = read_csv(study_dir / "vf_edge_bandwidth_calibration.csv") if (study_dir / "vf_edge_bandwidth_calibration.csv").exists() else []
    edge_adjusted_calibration = read_csv(study_dir / "vf_edge_adjusted_calibration_summary.csv") if (study_dir / "vf_edge_adjusted_calibration_summary.csv").exists() else []

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
    lines.extend(["", "## Independent View Classes", ""])
    for label, key in (
        ("full model", "full_model_independent_class"),
        ("RX shape", "rx_shape_independent_class"),
        ("RX timing", "rx_timing_independent_class"),
        ("reflection/TX", "reflection_independent_class"),
    ):
        counts = count_by(ranking, key)
        if counts:
            summary = ", ".join(f"{klass or 'unclassified'} `{count}`" for klass, count in counts.most_common())
            lines.append(f"- {label}: {summary}")
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
    lines.extend(["", "## Independent Edge Bandwidth Readiness", ""])
    if ranking:
        lines.append(
            f"- Edge bandwidth rule: required bandwidth = `{getattr(args, 'edge_bandwidth_factor', 0.35):g} / edge_time`; "
            f"PASS ratio >= `{getattr(args, 'edge_bandwidth_pass_ratio', 1.0):g}`, "
            f"WARN ratio >= `{getattr(args, 'edge_bandwidth_warn_ratio', 0.25):g}`."
        )
        for edge_ps in edge_quality_edges(args):
            counts = Counter(edge_class_for_channel(row, edge_ps, args) for row in ranking)
            required = edge_required_bandwidth_hz(edge_ps, args)
            summary = ", ".join(f"{klass} `{count}`" for klass, count in counts.most_common())
            lines.append(f"- `{edge_ps:g} ps` requires about `{required/1e9:.3g} GHz`: {summary}")
    else:
        lines.append("- No selected channels yet.")
    lines.extend(["", "## Edge Bandwidth Vs HSPICE Audit", ""])
    if edge_calibration:
        for row in edge_calibration:
            lines.append(
                f"- edge `{row.get('edge_ps')} ps`, bandwidth `{row.get('bandwidth_class')}`: "
                f"all audited HSPICE P/W/F/E `{row.get('hspice_pass')}/{row.get('hspice_warn')}/{row.get('hspice_fail')}/{row.get('hspice_error')}`, "
                f"selected-only P/W/F/E `{row.get('selected_hspice_pass')}/{row.get('selected_hspice_warn')}/{row.get('selected_hspice_fail')}/{row.get('selected_hspice_error')}`"
            )
    else:
        lines.append("- No HSPICE audit data yet.")
    lines.extend(["", "## Edge-Adjusted Independent Calibration", ""])
    if edge_adjusted_calibration:
        shown = [
            row
            for row in edge_adjusted_calibration
            if row.get("validation_split") == "all" and row.get("edge_adjusted_independent_class") == "PASS"
        ]
        if shown:
            for row in shown:
                lines.append(
                    f"- edge `{row.get('edge_ps')}`, adjusted independent PASS: "
                    f"HSPICE P/W/F/E `{row.get('hspice_pass')}/{row.get('hspice_warn')}/{row.get('hspice_fail')}/{row.get('hspice_error')}`, "
                    f"total `{row.get('total')}`, false-pass `{row.get('false_pass_rate')}`"
                )
        else:
            lines.append("- No edge-adjusted independent PASS rows.")
    else:
        lines.append("- No edge-adjusted calibration data yet.")
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
            "- `freq_trim_*`, resampling, and high-frequency extension modes fit modified data but are scored on the original grid.",
            "- `*_propdiag` candidates are diagnostic-only and cannot be selected as final deliverables.",
            "- `TIMEOUT` rows mean one candidate exceeded `--candidate-timeout-s`; the campaign continued.",
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
            "  --phase-profile phase1 `",
            "  --candidate-timeout-s 900 `",
            "  --passivity-strategy near-pass `",
            "  --enforce-samples-list 200,2000,20000 `",
            "  --enforce-fmax-list original,2x,high `",
            "  --enforce-preserve-dc-list true,false `",
            "  --dense-samples 501 `",
            "  --resume",
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
            "  --audit-top-k 3 `",
            "  --max-channels 20 `",
            "  --resume",
            "```",
            "",
            "## Key Files",
            "",
            "- `manifest.csv`",
            "- `vf_candidate_grid.csv`",
            "- `vf_candidates.csv`",
            "- `vf_metrics.csv`",
            "- `vf_ranking.csv`",
            "- `vf_ngspice_smoke.csv`",
            "- `vf_hspice_correlation.csv`",
            "- `vf_calibration_summary.csv`",
            "- `vf_selected_edge_readiness.csv`",
            "- `vf_edge_bandwidth_calibration.csv`",
            "- `vf_edge_adjusted_calibration_summary.csv`",
            "- `vf_edge_adjusted_hspice_correlation.csv`",
            "- `selected_vector_models/`",
            "- `plots/frequency_fit/`",
            "- `plots/passivity/`",
            "- `plots/edge_bandwidth/`",
            "- `plots/hspice_overlays/`",
            "- `plots/side_overlays/`",
            "- `share_pack/`",
        ]
    )
    study_dir.mkdir(parents=True, exist_ok=True)
    (study_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {study_dir / 'README.md'}")
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY_DIR)
    parser.add_argument("--skrf-target", type=Path, default=None)
    parser.add_argument("--edge-quality-ps", default=",".join(f"{edge:g}" for edge in DEFAULT_EDGE_QUALITY_PS))
    parser.add_argument("--edge-bandwidth-factor", type=float, default=0.35)
    parser.add_argument("--edge-bandwidth-pass-ratio", type=float, default=1.0)
    parser.add_argument("--edge-bandwidth-warn-ratio", type=float, default=0.25)


def add_inventory_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--skrf-tests-dir", type=Path, default=None)
    parser.add_argument("--extra-touchstone-dir", type=Path, action="append")
    parser.add_argument("--no-skrf-tests", action="store_true")
    parser.add_argument("--no-repo-local", action="store_true")


def add_fit_args(parser: argparse.ArgumentParser) -> None:
    add_inventory_args(parser)
    parser.add_argument("--candidate-profile", choices=("full", "pilot", "expanded"), default=None)
    parser.add_argument("--phase-profile", choices=("custom", "phase0", "phase1", "phase2", "phase3"), default="custom")
    parser.add_argument("--candidates", default=None)
    parser.add_argument("--preprocess", action="append", help=f"Comma-separated preprocessing modes: {','.join(PREPROCESS_MODES)}")
    parser.add_argument("--max-channels", type=int, default=0)
    parser.add_argument("--channel-id", action="append")
    parser.add_argument("--source-family", action="append")
    parser.add_argument("--resume", action="store_true", help="Reuse existing vf_metrics.csv rows and skip completed base candidates.")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--candidate-timeout-s", type=float, default=0.0)
    parser.add_argument("--dense-samples", type=int, default=1001)
    parser.add_argument("--high-fmax", type=float, default=400e9)
    parser.add_argument("--resample-points", type=int, default=301)
    parser.add_argument("--hf-extension-points", type=int, default=25)
    parser.add_argument("--impulse-samples", type=int, default=2048)
    parser.add_argument("--impulse-preresponse-warn-ratio", type=float, default=0.2)
    parser.add_argument("--rms-threshold", type=float, default=0.02)
    parser.add_argument("--mag-db-max-threshold", type=float, default=1.0)
    parser.add_argument("--group-delay-rms-ps-threshold", type=float, default=2.0)
    parser.add_argument("--max-low-freq-start-hz", type=float, default=5e9)
    parser.add_argument("--min-frequency-points", type=int, default=8)
    parser.add_argument("--max-sv-high-threshold", type=float, default=1.05)
    parser.add_argument("--passivity-warn-sv", type=float, default=1.0)
    parser.add_argument("--enforce-samples", type=int, default=2000)
    parser.add_argument("--passivity-strategy", choices=("near-pass", "all", "off"), default="near-pass")
    parser.add_argument("--enforce-samples-list", default="")
    parser.add_argument("--enforce-fmax-list", default="")
    parser.add_argument("--enforce-preserve-dc-list", default="")
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
    parser.add_argument("--audit-top-k", type=int, default=1, help="Audit selected model plus top K-1 additional candidates by independent score.")
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
