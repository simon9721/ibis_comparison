from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import warnings
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from bbs_extract import run_extraction as run_bbs_extraction  # noqa: E402
from hspice_reference_cache import cache_dir, reference_signature, restore as restore_hspice_cache, save as save_hspice_cache  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


DEFAULT_STUDY_DIR = ROOT / "results" / "sparam_conversion_quality_2026-06-08"
DEFAULT_NGSPICE = default_ngspice(console=True)
DEFAULT_HSPICE = default_hspice()
DEFAULT_BBS = Path(r"C:\Cadence\Sigrity2024.1\tools\bin\BroadbandSPICE.exe")
TOUCHSTONE_RE = re.compile(r"\.[sS](\d+)[pP]$")
DERIVED_TOUCHSTONE_NAMES = {"ch_model_fit.s2p"}
BBS_PRESET_CONFIGS: dict[str, dict[str, object]] = {
    "clean": {},
    "reciprocity": {"reciprocity_enforcement": {"type": "Average"}},
    "lowfreq": {"low_frequency_extrapolation": {"sampling_points": 14}},
    "smoothing": {"sparameter_smoothing": {"matrix": "All", "fitting": "mean", "window_width": 2}},
    "causality": {"causality_enforcement": {"matrix": "All"}},
    "recip_lowfreq": {
        "reciprocity_enforcement": {"type": "Average"},
        "low_frequency_extrapolation": {"sampling_points": 14},
    },
    "smooth_lowfreq": {
        "sparameter_smoothing": {"matrix": "All", "fitting": "mean", "window_width": 2},
        "low_frequency_extrapolation": {"sampling_points": 14},
    },
}
TRUST_CLASS_RANK = {"PASS": 0, "WARN": 1, "FAIL": 2}
REDUCED_CANDIDATES = {
    "reduced_s2p_delay_rc",
    "reduced_s2p_delay_rc_ring",
    "reduced_s2p_delay_rc_ring_reflect",
    "reduced_s2p_rx_delay_rc_ring",
    "reduced_s2p_rx_delayeq_rc_ring",
    "reduced_s2p_reflection",
    "reduced_s2p_reflection_s11_rc",
    "reduced_4p_dominant_delay_rc",
    "reduced_4p_dominant_delay_rc_reflect",
    "reduced_4p_rx_dominant_delay_rc",
    "reduced_4p_rx_delayeq_rc_ring",
    "reduced_4p_reflection",
    "reduced_4p_reflection_s11_rc",
}
ANALYSIS_ONLY_CANDIDATES = {"linear_reconstructed_rx"}
NAMED_NON_VECTOR_CANDIDATES = REDUCED_CANDIDATES | ANALYSIS_ONLY_CANDIDATES
REDUCED_EDGE_PS = (5, 50, 500)


_SKRF = None
_VF = None


class StudyError(RuntimeError):
    pass


def ensure_skrf(target: Path | None = None):
    global _SKRF, _VF
    if _SKRF is not None and _VF is not None:
        return _SKRF, _VF

    candidates: list[Path] = []
    if target is not None:
        candidates.append(target)
    env_target = os.environ.get("SKRF_TARGET")
    if env_target:
        candidates.append(Path(env_target))
    candidates.append(Path(os.environ.get("TEMP", "")) / "ibis_skrf_target")

    for candidate in candidates:
        if candidate and candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))

    try:
        import skrf  # type: ignore
        try:
            from skrf.vectorFitting import VectorFitting  # type: ignore
        except ImportError:
            from skrf.vectorfitting import VectorFitting  # type: ignore
    except ImportError as exc:
        raise StudyError(
            "scikit-rf is required. Install it into a temp target with:\n"
            "  $target = Join-Path $env:TEMP 'ibis_skrf_target'\n"
            "  py -3.14 -m pip install --target $target scikit-rf\n"
            "or pass --skrf-target <path>."
        ) from exc

    _SKRF = skrf
    _VF = VectorFitting
    return _SKRF, _VF


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def fmt(value: float) -> str:
    return f"{value:.12g}"


def safe_id(path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem).strip("._") or "channel"
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:8]
    return f"{stem}_{digest}"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def touchstone_port_count(path: Path) -> int | None:
    match = TOUCHSTONE_RE.search(path.name)
    return int(match.group(1)) if match else None


def touchstone_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and TOUCHSTONE_RE.search(path.name)
        and "__MACOSX" not in path.parts
        and not path.name.startswith("._")
    )


def fetch_skrf_tests(args: argparse.Namespace) -> int:
    study_dir = args.study_dir.resolve()
    dest = args.dest.resolve() if args.dest else (study_dir / "inputs" / "skrf_tests")
    cache_dir = study_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest.mkdir(parents=True, exist_ok=True)

    ref = args.github_ref
    archive = cache_dir / f"scikit-rf-{re.sub(r'[^A-Za-z0-9_.-]+', '_', ref)}.zip"
    url = f"https://github.com/scikit-rf/scikit-rf/archive/{ref}.zip"

    if args.force or not archive.exists():
        print(f"Downloading {url}")
        with urllib.request.urlopen(url, timeout=120) as response:
            archive.write_bytes(response.read())
    else:
        print(f"Using cached {archive}")

    extracted: list[dict[str, object]] = []
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            name = member.filename.replace("\\", "/")
            if member.is_dir() or "/skrf/tests/" not in name or not TOUCHSTONE_RE.search(name):
                continue
            rel_part = name.split("/skrf/tests/", 1)[1]
            if not rel_part or rel_part.startswith("../") or "/../" in rel_part:
                continue
            out_path = dest / rel_part
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, out_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(
                {
                    "source": name,
                    "path": rel(out_path),
                    "bytes": out_path.stat().st_size,
                    "ports_from_suffix": touchstone_port_count(out_path),
                }
            )

    write_csv(study_dir / "skrf_fetch_manifest.csv", extracted)
    print(f"Extracted {len(extracted)} Touchstone files to {dest}")
    print(f"Wrote {study_dir / 'skrf_fetch_manifest.csv'}")
    return 0


def z0_summary(nw) -> str:
    try:
        z = np.asarray(nw.z0)
        if z.size == 0:
            return ""
        flat = z.reshape(-1)
        vals: list[str] = []
        for value in flat[: min(8, flat.size)]:
            if abs(np.imag(value)) < 1e-9:
                vals.append(f"{float(np.real(value)):.6g}")
            else:
                vals.append(f"{value.real:.6g}{value.imag:+.6g}j")
        suffix = "" if flat.size <= 8 else "..."
        return ";".join(vals) + suffix
    except Exception:
        return ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dominant_path_info(nw) -> dict[str, object]:
    s = np.asarray(nw.s, dtype=complex)
    nports = int(nw.nports)
    best_pair: tuple[int, int] | None = None
    best_mag = -float("inf")
    for out_idx in range(nports):
        for in_idx in range(nports):
            if out_idx == in_idx:
                continue
            peak = float(np.nanmax(np.abs(s[:, out_idx, in_idx])))
            if peak > best_mag:
                best_mag = peak
                best_pair = (out_idx, in_idx)
    refl = [float(np.nanmax(np.abs(s[:, idx, idx]))) for idx in range(nports)]
    out: dict[str, object] = {
        "dominant_path": "",
        "dominant_output_port": "",
        "dominant_input_port": "",
        "dominant_peak_mag_db": "",
        "max_reflection_mag_db": 20 * math.log10(max(max(refl), 1e-30)) if refl else "",
    }
    if best_pair is not None:
        out_idx, in_idx = best_pair
        out.update(
            {
                "dominant_path": f"S{out_idx + 1}{in_idx + 1}",
                "dominant_output_port": out_idx + 1,
                "dominant_input_port": in_idx + 1,
                "dominant_peak_mag_db": 20 * math.log10(max(best_mag, 1e-30)),
            }
        )
    return out


def source_family(source: str, path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if "cisco_backplane_channel_data" in parts:
        return "cisco"
    if "molex" in name:
        return "molex"
    if source == "skrf_tests":
        return "skrf_tests"
    if source == "extra":
        return "extra"
    return "repo_local"


def inventory_paths(args: argparse.Namespace) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    if not args.no_skrf_tests:
        skrf_tests_dir = args.skrf_tests_dir.resolve() if args.skrf_tests_dir else args.study_dir.resolve() / "inputs" / "skrf_tests"
        roots.append(("skrf_tests", skrf_tests_dir))
    if not args.no_repo_local:
        roots.append(("repo_local", ROOT / "hspice" / "sparam"))
    for extra in args.extra_touchstone_dir or []:
        roots.append(("extra", extra.resolve()))

    seen: set[Path] = set()
    files: list[tuple[str, Path]] = []
    for source, root in roots:
        for path in touchstone_files(root):
            if source == "repo_local" and path.name.lower() in DERIVED_TOUCHSTONE_NAMES:
                continue
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append((source, resolved))
    return files


def inventory(args: argparse.Namespace) -> int:
    skrf, _ = ensure_skrf(args.skrf_target)
    study_dir = args.study_dir.resolve()
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
            "status": "",
        }
        try:
            nw = skrf.Network(str(path))
            freqs = np.asarray(nw.frequency.f, dtype=float)
            has_frequency_data = bool(len(freqs))
            supported = bool(nw.nports in (2, 4) and has_frequency_data)
            row.update(
                {
                    "ports": int(nw.nports),
                    "points": int(len(freqs)),
                    "f_min_hz": float(freqs[0]) if has_frequency_data else "",
                    "f_max_hz": float(freqs[-1]) if has_frequency_data else "",
                    "z0_summary": z0_summary(nw),
                    "supported_v1": supported,
                    "status": "ok" if supported else ("no_frequency_data" if not has_frequency_data else "unsupported_v1"),
                }
            )
            row.update(dominant_path_info(nw))
        except Exception as exc:
            row.update(
                {
                    "ports": ports_suffix or "",
                    "points": "",
                    "f_min_hz": "",
                    "f_max_hz": "",
                    "z0_summary": "",
                    "supported_v1": False,
                    "status": "parse_error",
                    "error": str(exc),
                    "dominant_path": "",
                    "dominant_output_port": "",
                    "dominant_input_port": "",
                    "dominant_peak_mag_db": "",
                    "max_reflection_mag_db": "",
                }
            )
        rows.append(row)

    hash_counts: dict[str, int] = {}
    for row in rows:
        digest = str(row.get("sha256", ""))
        hash_counts[digest] = hash_counts.get(digest, 0) + 1
    for row in rows:
        digest = str(row.get("sha256", ""))
        count = hash_counts.get(digest, 0)
        row["duplicate_count"] = count
        row["duplicate_group"] = digest[:12] if count > 1 else ""
    by_family: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_family.setdefault(str(row.get("source_family", "unknown")), []).append(row)
    for family_rows in by_family.values():
        for idx, row in enumerate(sorted(family_rows, key=lambda item: str(item.get("channel_id", ""))), start=1):
            row["validation_split"] = "holdout" if idx % 5 == 0 else "calibration"

    manifest = args.manifest.resolve() if args.manifest else study_dir / "manifest.csv"
    write_csv(manifest, rows)
    supported = sum(str(row.get("supported_v1")) == "True" or row.get("supported_v1") is True for row in rows)
    print(f"Inventoried {len(rows)} Touchstone files; {supported} supported for v1.")
    print(f"Wrote {manifest}")
    return 0


def max_singular_from_mats(mats: np.ndarray) -> tuple[float, int]:
    singular = np.linalg.svd(mats, compute_uv=False)
    max_by_freq = singular[:, 0]
    idx = int(np.argmax(max_by_freq))
    return float(max_by_freq[idx]), idx


def fitted_s_matrices(vf, freqs: np.ndarray) -> np.ndarray:
    nports = vf.network.nports
    mats = np.empty((len(freqs), nports, nports), dtype=complex)
    for i in range(nports):
        for j in range(nports):
            mats[:, i, j] = vf.get_model_response(i, j, freqs=freqs)
    return mats


def passivity_bands(vf) -> list[list[float]]:
    try:
        bands = vf.passivity_test()
        return np.asarray(bands, dtype=float).reshape((-1, 2)).tolist() if np.size(bands) else []
    except Exception:
        return [[float("nan"), float("nan")]]


def through_pairs(nports: int) -> list[tuple[int, int]]:
    if nports == 2:
        return [(1, 0), (0, 1)]
    if nports == 4:
        return [(2, 0), (3, 1), (0, 2), (1, 3)]
    return []


def dominant_rx_path(nports: int) -> tuple[int, int]:
    if nports == 2:
        return 1, 0
    if nports == 4:
        return 2, 0
    return 0, 0


def input_reflection_path(nports: int) -> tuple[int, int]:
    return 0, 0


def prefixed_metrics(prefix: str, metrics: dict[str, float]) -> dict[str, float]:
    return {f"{prefix}_{key}": value for key, value in metrics.items()}


def reduced_candidate_profile(name: str, nports: int) -> dict[str, object]:
    if name == "linear_reconstructed_rx":
        return {
            "view_role": "analysis_only",
            "use_scope": "analysis_only_linear_reconstruction",
            "include_ring": True,
            "include_reflection": False,
        }
    include_ring = "_ring" in name or name == "reduced_s2p_reflection"
    include_reflection = name.endswith("_reflect") or name.endswith("_reflection") or name.endswith("_s11_rc") or name in {
        "reduced_s2p_reflection",
        "reduced_4p_reflection",
    }
    delay_equalized = "_delayeq_" in name
    if name in {"reduced_s2p_reflection", "reduced_4p_reflection", "reduced_s2p_reflection_s11_rc", "reduced_4p_reflection_s11_rc"}:
        view_role = "reflection"
    elif include_reflection:
        view_role = "combined"
    else:
        view_role = "rx_through"
    if view_role == "reflection":
        use_scope = "matched_50ohm_reflection"
    elif view_role == "rx_through":
        use_scope = "matched_50ohm_rx_through"
    elif nports == 2:
        use_scope = "matched_50ohm_transient"
    else:
        use_scope = "matched_50ohm_reduced_4p"
    return {
        "view_role": view_role,
        "use_scope": use_scope,
        "include_ring": include_ring,
        "include_reflection": include_reflection,
        "delay_equalized": delay_equalized,
    }


def group_delay(freqs: np.ndarray, response: np.ndarray) -> np.ndarray:
    if len(freqs) < 3:
        return np.array([], dtype=float)
    omega = 2 * np.pi * freqs
    phase = np.unwrap(np.angle(response))
    return -np.gradient(phase, omega)


def frequency_metrics(nw, fitted: np.ndarray) -> dict[str, float]:
    original = np.asarray(nw.s, dtype=complex)
    diff = fitted - original
    abs_diff = np.abs(diff)
    row: dict[str, float] = {
        "fit_complex_rms": float(np.sqrt(np.mean(abs_diff**2))),
        "fit_complex_max": float(np.max(abs_diff)),
    }

    mag = np.abs(original)
    fit_mag = np.abs(fitted)
    mask = mag > 1e-2
    if np.any(mask):
        mag_err_db = 20 * np.log10(np.maximum(fit_mag[mask], 1e-30)) - 20 * np.log10(np.maximum(mag[mask], 1e-30))
        phase_err = np.rad2deg(np.angle(fitted[mask] * np.conj(original[mask])))
        row["fit_mag_db_rms_above_m40"] = float(np.sqrt(np.mean(mag_err_db**2)))
        row["fit_mag_db_max_above_m40"] = float(np.max(np.abs(mag_err_db)))
        row["fit_phase_deg_rms_above_m40"] = float(np.sqrt(np.mean(phase_err**2)))
        row["fit_phase_deg_max_above_m40"] = float(np.max(np.abs(phase_err)))
    else:
        row["fit_mag_db_rms_above_m40"] = float("nan")
        row["fit_mag_db_max_above_m40"] = float("nan")
        row["fit_phase_deg_rms_above_m40"] = float("nan")
        row["fit_phase_deg_max_above_m40"] = float("nan")

    gd_errs: list[float] = []
    freqs = np.asarray(nw.frequency.f, dtype=float)
    for i, j in through_pairs(nw.nports):
        path_mask = np.abs(original[:, i, j]) > 1e-2
        if np.count_nonzero(path_mask) < 3:
            continue
        gd_orig = group_delay(freqs[path_mask], original[:, i, j][path_mask])
        gd_fit = group_delay(freqs[path_mask], fitted[:, i, j][path_mask])
        if len(gd_orig) and len(gd_fit):
            gd_errs.extend(np.abs(gd_fit - gd_orig).tolist())
    row["fit_group_delay_rms_ps"] = float(np.sqrt(np.mean(np.asarray(gd_errs) ** 2)) * 1e12) if gd_errs else float("nan")
    row["fit_group_delay_max_ps"] = float(np.max(gd_errs) * 1e12) if gd_errs else float("nan")
    return row


def candidate_specs(selected: str | None = None) -> list[tuple[str, int | None]]:
    specs: list[tuple[str, int | None]] = [("auto_fit", None)]
    specs.extend((f"vector_{n}r{n}c", n) for n in (1, 2, 3, 4, 5, 6, 8))
    specs.extend((name, None) for name in sorted(REDUCED_CANDIDATES))
    if not selected:
        return specs
    filtered: list[tuple[str, int | None]] = []
    for item in [part.strip() for part in selected.split(",") if part.strip()]:
        if item == "auto_fit":
            filtered.append((item, None))
            continue
        if item in NAMED_NON_VECTOR_CANDIDATES:
            filtered.append((item, None))
            continue
        match = re.fullmatch(r"vector_(\d+)r\1c", item)
        if not match:
            raise StudyError(f"Unknown candidate name: {item}")
        filtered.append((item, int(match.group(1))))
    return filtered


def candidate_specs_for_channel(args: argparse.Namespace, nports: int) -> list[tuple[str, int | None]]:
    if getattr(args, "enable_bbs", False) and not args.candidates and not args.fast_calibration_profile:
        if nports == 4:
            return candidate_specs("reduced_4p_rx_dominant_delay_rc,reduced_4p_rx_delayeq_rc_ring,reduced_4p_reflection_s11_rc")
        if nports == 2:
            return candidate_specs("vector_3r3c,reduced_s2p_rx_delayeq_rc_ring,reduced_s2p_reflection_s11_rc")
    if not args.fast_calibration_profile:
        return candidate_specs(args.candidates)
    if args.candidates:
        return candidate_specs(args.candidates)
    if nports == 4:
        return candidate_specs("reduced_4p_rx_dominant_delay_rc,reduced_4p_rx_delayeq_rc_ring,reduced_4p_reflection_s11_rc")
    if nports == 2:
        return candidate_specs("vector_3r3c,vector_5r5c,reduced_s2p_rx_delay_rc_ring,reduced_s2p_rx_delayeq_rc_ring,reduced_s2p_reflection_s11_rc")
    return candidate_specs(args.candidates)


def fit_candidate(nw, spec: tuple[str, int | None]):
    _, VectorFitting = ensure_skrf()
    name, n = spec
    vf = VectorFitting(nw)
    caught: list[str] = []
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        if name == "auto_fit":
            vf.auto_fit()
        else:
            assert n is not None
            vf.vector_fit(n_poles_real=n, n_poles_cmplx=n)
    caught.extend(str(record.message) for record in records)
    return vf, caught


def describe_candidate(nw, vf, high_fmax: float, dense_samples: int) -> dict[str, object]:
    _, VectorFitting = ensure_skrf()
    freqs = np.asarray(nw.frequency.f, dtype=float)
    fitted_at_samples = fitted_s_matrices(vf, freqs)
    metrics: dict[str, object] = frequency_metrics(nw, fitted_at_samples)
    rx_out, rx_in = dominant_rx_path(nw.nports)
    refl_out, refl_in = input_reflection_path(nw.nports)
    metrics.update(
        prefixed_metrics(
            "rx",
            one_path_frequency_metrics(freqs, np.asarray(nw.s[:, rx_out, rx_in], dtype=complex), fitted_at_samples[:, rx_out, rx_in]),
        )
    )
    metrics.update(
        prefixed_metrics(
            "reflection",
            one_path_frequency_metrics(freqs, np.asarray(nw.s[:, refl_out, refl_in], dtype=complex), fitted_at_samples[:, refl_out, refl_in]),
        )
    )
    metrics["model_order"] = int(VectorFitting.get_model_order(vf.poles))
    metrics["pole_count_array"] = int(len(vf.poles))
    try:
        metrics["is_passive"] = bool(vf.is_passive())
    except Exception as exc:
        metrics["is_passive"] = False
        metrics["passivity_error"] = str(exc)
    metrics["passivity_violation_bands_hz"] = json.dumps(passivity_bands(vf))

    input_sv, input_idx = max_singular_from_mats(fitted_at_samples)
    metrics["max_sv_input_samples"] = input_sv
    metrics["max_sv_input_samples_freq_hz"] = float(freqs[input_idx])

    dense_freqs = np.linspace(0.0, high_fmax, dense_samples)
    dense_mats = fitted_s_matrices(vf, dense_freqs)
    high_sv, high_idx = max_singular_from_mats(dense_mats)
    last_sv = float(np.linalg.svd(dense_mats[-1], compute_uv=False)[0])
    metrics["max_sv_high"] = high_sv
    metrics["max_sv_high_freq_hz"] = float(dense_freqs[high_idx])
    metrics["sv_at_high_fmax"] = last_sv
    return metrics


def write_spice_model(vf, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    vf.write_spice_subcircuit_s(str(path), fitted_model_name="s_equivalent")


def source_voltage(t: np.ndarray, edge_ps: float, amplitude_v: float = 1.5) -> np.ndarray:
    edge = edge_ps * 1e-12
    stop = max(float(t[-1]) + 1e-9, 1.0)
    xp = np.array([0.0, 1.0e-9, 1.0e-9 + edge, 9.0e-9, 9.0e-9 + edge, stop], dtype=float)
    yp = np.array([0.0, 0.0, amplitude_v, amplitude_v, 0.0, 0.0], dtype=float)
    return np.interp(t, xp, yp)


def lowpass(t: np.ndarray, x: np.ndarray, tau_s: float) -> np.ndarray:
    tau_s = max(float(tau_s), 1e-15)
    y = np.empty_like(x)
    y[0] = x[0]
    for idx in range(1, len(x)):
        alpha = math.exp(-float(t[idx] - t[idx - 1]) / tau_s)
        y[idx] = x[idx] + (y[idx - 1] - x[idx]) * alpha
    return y


def interp_transfer(freqs: np.ndarray, response: np.ndarray, query_hz: np.ndarray) -> np.ndarray:
    freqs = np.asarray(freqs, dtype=float)
    response = np.asarray(response, dtype=complex)
    order = np.argsort(freqs)
    freqs = freqs[order]
    response = response[order]
    if len(freqs) == 0:
        return np.zeros_like(query_hz, dtype=complex)
    if freqs[0] > 0:
        freqs = np.concatenate([[0.0], freqs])
        response = np.concatenate([[response[0]], response])
    real = np.interp(query_hz, freqs, response.real, left=float(response.real[0]), right=0.0)
    imag = np.interp(query_hz, freqs, response.imag, left=float(response.imag[0]), right=0.0)
    out = real + 1j * imag
    fmax = float(freqs[-1])
    if fmax > 0:
        taper_start = 0.85 * fmax
        taper = np.ones_like(query_hz, dtype=float)
        in_taper = (query_hz > taper_start) & (query_hz < fmax)
        taper[in_taper] = 0.5 * (1.0 + np.cos(np.pi * (query_hz[in_taper] - taper_start) / max(fmax - taper_start, 1.0)))
        taper[query_hz >= fmax] = 0.0
        out *= taper
    return out


def synthetic_transfer_waveform(
    nw,
    out_idx: int,
    in_idx: int,
    t: np.ndarray,
    edge_ps: float,
    incident_scale: float = 0.5,
) -> np.ndarray:
    dt = float(t[1] - t[0])
    n_base = len(t)
    n_fft = 1 << int(math.ceil(math.log2(max(8, 2 * n_base))))
    t_fft = np.arange(n_fft, dtype=float) * dt
    x = incident_scale * source_voltage(t_fft, edge_ps)
    bins = np.fft.rfftfreq(n_fft, dt)
    freqs = np.asarray(nw.frequency.f, dtype=float)
    response = np.asarray(nw.s[:, out_idx, in_idx], dtype=complex)
    h = interp_transfer(freqs, response, bins)
    y = np.fft.irfft(np.fft.rfft(x) * h, n_fft)
    return y[:n_base]


def model_waveform_reduced(
    t: np.ndarray,
    edge_ps: float,
    delay_s: float,
    taus_s: np.ndarray,
    gains: np.ndarray,
    tail_fast_s: np.ndarray | None = None,
    tail_slow_s: np.ndarray | None = None,
    tail_gains: np.ndarray | None = None,
    incident_scale: float = 0.5,
) -> np.ndarray:
    line = incident_scale * source_voltage(t - delay_s, edge_ps)
    y = np.zeros_like(line)
    for tau_s, gain in zip(taus_s, gains):
        y += float(gain) * lowpass(t, line, float(tau_s))
    if tail_fast_s is not None and tail_slow_s is not None and tail_gains is not None:
        for fast_s, slow_s, gain in zip(tail_fast_s, tail_slow_s, tail_gains):
            y += float(gain) * (lowpass(t, line, float(fast_s)) - lowpass(t, line, float(slow_s)))
    return y


def ring_basis_waveform(t: np.ndarray, edge_ps: float, delay_s: float, fast_s: float, slow_s: float) -> np.ndarray:
    x = 0.5 * source_voltage(t - delay_s, edge_ps)
    return lowpass(t, x, fast_s) - lowpass(t, x, slow_s)


def reduced_s21_waveform(t: np.ndarray, edge_ps: float, fit: dict[str, object]) -> np.ndarray:
    y = model_waveform_reduced(
        t,
        edge_ps,
        float(fit["delay_s"]),
        np.asarray(fit["taus_s"], dtype=float),
        np.asarray(fit["gains"], dtype=float),
        np.asarray(fit.get("tail_fast_s", []), dtype=float),
        np.asarray(fit.get("tail_slow_s", []), dtype=float),
        np.asarray(fit.get("tail_gains", []), dtype=float),
    )
    for delay_s, fast_s, slow_s, gain in zip(
        np.asarray(fit.get("ring_delay_s", []), dtype=float),
        np.asarray(fit.get("ring_fast_s", []), dtype=float),
        np.asarray(fit.get("ring_slow_s", []), dtype=float),
        np.asarray(fit.get("ring_gains", []), dtype=float),
    ):
        y += float(gain) * ring_basis_waveform(t, edge_ps, float(delay_s), float(fast_s), float(slow_s))
    return y


def crossing_for_fit(t: np.ndarray, y: np.ndarray, threshold: float, rise: bool, after: float) -> float | None:
    if rise:
        idxs = np.where((y[:-1] < threshold) & (y[1:] >= threshold))[0]
    else:
        idxs = np.where((y[:-1] >= threshold) & (y[1:] < threshold))[0]
    idxs = [idx for idx in idxs if t[idx] >= after]
    if not idxs:
        return None
    idx = idxs[0]
    if y[idx + 1] == y[idx]:
        return float(t[idx])
    return float(t[idx] + (threshold - y[idx]) * (t[idx + 1] - t[idx]) / (y[idx + 1] - y[idx]))


def reduced_active_error(ref: np.ndarray, pred: np.ndarray) -> tuple[float, float]:
    high = float(np.nanpercentile(ref, 95.0))
    low = float(np.nanpercentile(ref, 5.0))
    swing = max(abs(high - low), 1e-12)
    mask = (np.abs(ref - low) >= 0.02 * swing) | (np.abs(pred - low) >= 0.02 * swing)
    if not np.any(mask):
        return float("nan"), float("nan")
    diff = pred[mask] - ref[mask]
    return float(np.sqrt(np.mean(diff**2))), float(np.max(np.abs(diff)))


def reduced_fit_refs(nw, out_idx: int, in_idx: int, stop_ns: float, step_ps: float) -> dict[int, dict[str, np.ndarray]]:
    dt = step_ps * 1e-12
    t = np.arange(0.0, stop_ns * 1e-9 + 0.5 * dt, dt)
    refs: dict[int, dict[str, np.ndarray]] = {}
    for edge in REDUCED_EDGE_PS:
        rx = synthetic_transfer_waveform(nw, out_idx, in_idx, t, edge)
        pin = 0.5 * source_voltage(t, edge)
        low, active, threshold, active_high = waveform_levels(t, rx)
        tx_low, tx_active, tx_threshold, tx_active_high = waveform_levels(t, pin)
        rx_first, rx_second = edge_crossings(t, rx, threshold, active_high)
        tx_first, tx_second = edge_crossings(t, pin, tx_threshold, tx_active_high)
        refs[edge] = {
            "time": t,
            "v_p2": rx,
            "v_p1": pin,
            "rx_low": low,
            "rx_active": active,
            "threshold": threshold,
            "rx_active_high": active_high,
            "rise": rx_first,
            "fall": rx_second,
            "tx_rise": tx_first,
            "tx_fall": tx_second,
        }
    return refs


def estimate_delay_from_refs(refs: dict[int, dict[str, np.ndarray]]) -> float:
    delays: list[float] = []
    for ref in refs.values():
        for tx_key, rx_key in (("tx_rise", "rise"), ("tx_fall", "fall")):
            tx = ref.get(tx_key)
            rx = ref.get(rx_key)
            if tx is not None and rx is not None:
                delays.append((float(rx) - float(tx)) * 1e9)
    if delays:
        return max(0.0, float(np.nanmedian(delays)))
    return 0.0


def estimate_impulse_delay_from_refs(refs: dict[int, dict[str, np.ndarray]]) -> float:
    delays: list[float] = []
    for ref in refs.values():
        t = np.asarray(ref["time"], dtype=float)
        if len(t) < 3:
            continue
        rx = np.asarray(ref["v_p2"], dtype=float)
        tx = np.asarray(ref["v_p1"], dtype=float)
        dt = float(np.nanmedian(np.diff(t)))
        if not math.isfinite(dt) or dt <= 0:
            continue
        rx_slope = np.gradient(rx, dt)
        tx_slope = np.gradient(tx, dt)
        rx_idx = int(np.nanargmax(np.abs(rx_slope)))
        tx_idx = int(np.nanargmax(np.abs(tx_slope)))
        delay = float(t[rx_idx] - t[tx_idx]) * 1e9
        if math.isfinite(delay) and delay >= 0.0:
            delays.append(delay)
    return float(np.nanmedian(delays)) if delays else float("nan")


def estimate_group_delay_ns(nw, out_idx: int, in_idx: int) -> float:
    freqs = np.asarray(nw.frequency.f, dtype=float)
    response = np.asarray(nw.s[:, out_idx, in_idx], dtype=complex)
    mask = np.abs(response) > 1e-2
    if np.count_nonzero(mask) < 3:
        return float("nan")
    gd = group_delay(freqs[mask], response[mask])
    gd = gd[np.isfinite(gd) & (gd >= 0.0)]
    return float(np.nanmedian(gd) * 1e9) if len(gd) else float("nan")


def estimate_reduced_delay(
    nw,
    out_idx: int,
    in_idx: int,
    refs: dict[int, dict[str, np.ndarray]],
    delay_equalized: bool,
) -> dict[str, object]:
    step_ns = estimate_delay_from_refs(refs)
    impulse_ns = estimate_impulse_delay_from_refs(refs)
    group_ns = estimate_group_delay_ns(nw, out_idx, in_idx)
    sources = [("step_threshold", step_ns)]
    if math.isfinite(impulse_ns):
        sources.append(("impulse_peak", impulse_ns))
    if math.isfinite(group_ns):
        sources.append(("group_delay_median", group_ns))
    if delay_equalized:
        finite = [value for _, value in sources if math.isfinite(float(value)) and float(value) >= 0.0]
        delay_ns = max(0.0, float(np.nanmedian(finite))) if finite else 0.0
        source = "median_step_impulse_group_delay"
    else:
        delay_ns = max(0.0, float(step_ns)) if math.isfinite(float(step_ns)) else 0.0
        source = "step_threshold"
    return {
        "delay_ns": delay_ns,
        "delay_estimator_source": source,
        "delay_step_threshold_ns": float(step_ns) if math.isfinite(float(step_ns)) else "",
        "delay_impulse_peak_ns": float(impulse_ns) if math.isfinite(float(impulse_ns)) else "",
        "delay_group_delay_median_ns": float(group_ns) if math.isfinite(float(group_ns)) else "",
        "delay_candidate_sources": ";".join(f"{name}:{value:.12g}" for name, value in sources if math.isfinite(float(value))),
    }


def delay_removed_group_delay_metrics(nw, out_idx: int, in_idx: int, delay_ns: float) -> dict[str, object]:
    freqs = np.asarray(nw.frequency.f, dtype=float)
    response = np.asarray(nw.s[:, out_idx, in_idx], dtype=complex)
    mask = np.abs(response) > 1e-2
    if np.count_nonzero(mask) < 3:
        return {
            "rx_group_delay_rms_ps": float("nan"),
            "rx_group_delay_std_ps": float("nan"),
            "rx_delayeq_group_delay_rms_ps": float("nan"),
            "rx_delayeq_group_delay_std_ps": float("nan"),
        }
    gd_ps = group_delay(freqs[mask], response[mask]) * 1e12
    gd_ps = gd_ps[np.isfinite(gd_ps)]
    if not len(gd_ps):
        return {
            "rx_group_delay_rms_ps": float("nan"),
            "rx_group_delay_std_ps": float("nan"),
            "rx_delayeq_group_delay_rms_ps": float("nan"),
            "rx_delayeq_group_delay_std_ps": float("nan"),
        }
    residual = gd_ps - float(delay_ns) * 1000.0
    return {
        "rx_group_delay_rms_ps": float(np.sqrt(np.mean(gd_ps**2))),
        "rx_group_delay_std_ps": float(np.std(gd_ps)),
        "rx_delayeq_group_delay_rms_ps": float(np.sqrt(np.mean(residual**2))),
        "rx_delayeq_group_delay_std_ps": float(np.std(residual)),
    }


def parse_float_values(text: str) -> list[float]:
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def parse_tau_pairs(text: str) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        fast, slow = item.split(":", 1)
        out.append((float(fast), float(slow)))
    return out


def fit_reduced_basis(
    refs: dict[int, dict[str, np.ndarray]],
    delay_ns: float,
    tau_ns: list[float],
    tail_pairs_ns: list[tuple[float, float]],
    gain_bound: float,
    reg: float,
) -> dict[str, object]:
    from scipy.optimize import lsq_linear

    matrix_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    delay_s = delay_ns * 1e-9
    for edge, ref in refs.items():
        t = ref["time"]
        line = 0.5 * source_voltage(t - delay_s, edge)
        cols = [lowpass(t, line, tau * 1e-9) for tau in tau_ns]
        for fast_ns, slow_ns in tail_pairs_ns:
            cols.append(lowpass(t, line, fast_ns * 1e-9) - lowpass(t, line, slow_ns * 1e-9))
        basis = np.column_stack(cols)
        low = float(ref["rx_low"])
        swing = max(abs(float(ref["rx_active"]) - low), 1e-12)
        mask = np.abs(ref["v_p2"] - low) >= 0.01 * swing
        matrix_rows.append(basis[mask])
        target_rows.append(ref["v_p2"][mask])
    matrix = np.vstack(matrix_rows)
    target = np.concatenate(target_rows)
    if reg > 0:
        matrix = np.vstack([matrix, reg * np.eye(matrix.shape[1])])
        target = np.concatenate([target, np.zeros(matrix.shape[1])])
    result = lsq_linear(matrix, target, bounds=(-gain_bound, gain_bound), lsmr_tol="auto", max_iter=500)
    coeff = result.x
    n_tau = len(tau_ns)
    tail_coeff = coeff[n_tau:]
    tail_fast_ns = np.asarray([pair[0] for pair in tail_pairs_ns], dtype=float)
    tail_slow_ns = np.asarray([pair[1] for pair in tail_pairs_ns], dtype=float)
    fit = {
        "delay_s": delay_s,
        "delay_ns": delay_ns,
        "taus_s": np.asarray(tau_ns, dtype=float) * 1e-9,
        "taus_ns": np.asarray(tau_ns, dtype=float),
        "gains": coeff[:n_tau],
        "tail_fast_s": tail_fast_ns * 1e-9,
        "tail_fast_ns": tail_fast_ns,
        "tail_slow_s": tail_slow_ns * 1e-9,
        "tail_slow_ns": tail_slow_ns,
        "tail_gains": tail_coeff,
        "dc_gain_to_load": float(np.sum(coeff[:n_tau])),
        "objective": float(result.cost),
    }
    for edge, ref in refs.items():
        pred = reduced_s21_waveform(ref["time"], edge, fit)
        rmse, maxabs = reduced_active_error(ref["v_p2"], pred)
        fit[f"edge{edge}_fit_rx_active_rmse_v"] = rmse
        fit[f"edge{edge}_fit_rx_active_maxabs_v"] = maxabs
    return fit


def fit_ring_basis(
    refs: dict[int, dict[str, np.ndarray]],
    fit: dict[str, object],
    delay_ns: list[float],
    tau_pairs_ns: list[tuple[float, float]],
    gain_bound: float,
    reg: float,
) -> dict[str, object]:
    if not delay_ns or not tau_pairs_ns:
        return {
            "ring_delay_s": np.asarray([], dtype=float),
            "ring_delay_ns": np.asarray([], dtype=float),
            "ring_fast_s": np.asarray([], dtype=float),
            "ring_fast_ns": np.asarray([], dtype=float),
            "ring_slow_s": np.asarray([], dtype=float),
            "ring_slow_ns": np.asarray([], dtype=float),
            "ring_gains": np.asarray([], dtype=float),
            "ring_fit_cost": 0.0,
        }
    from scipy.optimize import lsq_linear

    specs = [(delay, fast, slow) for delay in delay_ns for fast, slow in tau_pairs_ns if slow > fast]
    matrix_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    for edge, ref in refs.items():
        t = ref["time"]
        base = reduced_s21_waveform(t, edge, fit)
        residual = ref["v_p2"] - base
        cols = [ring_basis_waveform(t, edge, delay * 1e-9, fast * 1e-9, slow * 1e-9) for delay, fast, slow in specs]
        basis = np.column_stack(cols)
        low = float(ref["rx_low"])
        swing = max(abs(float(ref["rx_active"]) - low), 1e-12)
        mask = (np.abs(ref["v_p2"] - low) >= 0.01 * swing) | (np.abs(residual) >= max(0.005, 0.10 * float(np.nanmax(np.abs(residual)))))
        matrix_rows.append(basis[mask])
        target_rows.append(residual[mask])
    matrix = np.vstack(matrix_rows)
    target = np.concatenate(target_rows)
    if reg > 0:
        matrix = np.vstack([matrix, reg * np.eye(matrix.shape[1])])
        target = np.concatenate([target, np.zeros(matrix.shape[1])])
    result = lsq_linear(matrix, target, bounds=(-gain_bound, gain_bound), lsmr_tol="auto", max_iter=500)
    coeff = result.x
    return {
        "ring_delay_s": np.asarray([item[0] for item in specs], dtype=float) * 1e-9,
        "ring_delay_ns": np.asarray([item[0] for item in specs], dtype=float),
        "ring_fast_s": np.asarray([item[1] for item in specs], dtype=float) * 1e-9,
        "ring_fast_ns": np.asarray([item[1] for item in specs], dtype=float),
        "ring_slow_s": np.asarray([item[2] for item in specs], dtype=float) * 1e-9,
        "ring_slow_ns": np.asarray([item[2] for item in specs], dtype=float),
        "ring_gains": coeff,
        "ring_fit_cost": float(result.cost),
    }


def fit_reflection_basis(refs: dict[int, dict[str, np.ndarray]], tau_ns: list[float], tail_pairs_ns: list[tuple[float, float]], gain_bound: float, reg: float) -> dict[str, object]:
    from scipy.optimize import lsq_linear

    matrix_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    for edge, ref in refs.items():
        t = ref["time"]
        pin = 0.5 * source_voltage(t, edge)
        cols = [lowpass(t, pin, tau * 1e-9) for tau in tau_ns]
        for fast_ns, slow_ns in tail_pairs_ns:
            cols.append(lowpass(t, pin, fast_ns * 1e-9) - lowpass(t, pin, slow_ns * 1e-9))
        basis = np.column_stack(cols)
        target = ref.get("v_p1_target")
        if target is None:
            continue
        residual = np.asarray(target, dtype=float) - pin
        mask = np.abs(pin) >= 0.01 * max(float(np.nanmax(np.abs(pin))), 1e-12)
        matrix_rows.append(basis[mask])
        target_rows.append(residual[mask])
    if not matrix_rows:
        return {
            "tx_taus_s": np.asarray([], dtype=float),
            "tx_taus_ns": np.asarray([], dtype=float),
            "tx_gains": np.asarray([], dtype=float),
            "tx_tail_fast_s": np.asarray([], dtype=float),
            "tx_tail_fast_ns": np.asarray([], dtype=float),
            "tx_tail_slow_s": np.asarray([], dtype=float),
            "tx_tail_slow_ns": np.asarray([], dtype=float),
            "tx_tail_gains": np.asarray([], dtype=float),
            "tx_fit_cost": 0.0,
        }
    matrix = np.vstack(matrix_rows)
    target = np.concatenate(target_rows)
    if reg > 0:
        matrix = np.vstack([matrix, reg * np.eye(matrix.shape[1])])
        target = np.concatenate([target, np.zeros(matrix.shape[1])])
    result = lsq_linear(matrix, target, bounds=(-gain_bound, gain_bound), lsmr_tol="auto", max_iter=500)
    coeff = result.x
    n_tau = len(tau_ns)
    tail_fast_ns = np.asarray([pair[0] for pair in tail_pairs_ns], dtype=float)
    tail_slow_ns = np.asarray([pair[1] for pair in tail_pairs_ns], dtype=float)
    return {
        "tx_taus_s": np.asarray(tau_ns, dtype=float) * 1e-9,
        "tx_taus_ns": np.asarray(tau_ns, dtype=float),
        "tx_gains": coeff[:n_tau],
        "tx_tail_fast_s": tail_fast_ns * 1e-9,
        "tx_tail_fast_ns": tail_fast_ns,
        "tx_tail_slow_s": tail_slow_ns * 1e-9,
        "tx_tail_slow_ns": tail_slow_ns,
        "tx_tail_gains": coeff[n_tau:],
        "tx_fit_cost": float(result.cost),
    }


def reflection_model_lines(fit: dict[str, object], r_stage: float = 1000.0) -> list[str]:
    lines = ["* Touchstone-derived input reflection correction.", "Rtxsum txsum 0 1"]
    for idx, (tau_ns, gain) in enumerate(zip(np.asarray(fit.get("tx_taus_ns", []), dtype=float), np.asarray(fit.get("tx_gains", []), dtype=float)), start=1):
        cap_f = (float(tau_ns) * 1e-9) / r_stage
        lines.extend([f"Etxsrc{idx} txsrc{idx} 0 pin 0 1", f"Rtx{idx} txsrc{idx} tx{idx} {r_stage:.12g}", f"Ctx{idx} tx{idx} 0 {cap_f:.12g}", f"Gtx{idx} 0 txsum tx{idx} 0 {float(gain):.12g}"])
    for idx, (fast_ns, slow_ns, gain) in enumerate(zip(np.asarray(fit.get("tx_tail_fast_ns", []), dtype=float), np.asarray(fit.get("tx_tail_slow_ns", []), dtype=float), np.asarray(fit.get("tx_tail_gains", []), dtype=float)), start=1):
        fast_cap_f = (float(fast_ns) * 1e-9) / r_stage
        slow_cap_f = (float(slow_ns) * 1e-9) / r_stage
        lines.extend(
            [
                f"Etxtailfsrc{idx} txtailfsrc{idx} 0 pin 0 1",
                f"Rtxtailf{idx} txtailfsrc{idx} txtailf{idx} {r_stage:.12g}",
                f"Ctx_tailf{idx} txtailf{idx} 0 {fast_cap_f:.12g}",
                f"Gtxtailf{idx} 0 txsum txtailf{idx} 0 {float(gain):.12g}",
                f"Etxtailssrc{idx} txtailssrc{idx} 0 pin 0 1",
                f"Rtxtails{idx} txtailssrc{idx} txtails{idx} {r_stage:.12g}",
                f"Ctx_tails{idx} txtails{idx} 0 {slow_cap_f:.12g}",
                f"Gtxtails{idx} 0 txsum txtails{idx} 0 {-float(gain):.12g}",
            ]
        )
    lines.extend(["Etxport p1 pin txsum 0 1", "Rpin_leak pin 0 1e12"])
    return lines


def tx_reflection_waveform(t: np.ndarray, edge_ps: float, fit: dict[str, object]) -> np.ndarray:
    pin = 0.5 * source_voltage(t, edge_ps)
    y = pin.copy()
    for tau_s, gain in zip(np.asarray(fit.get("tx_taus_s", []), dtype=float), np.asarray(fit.get("tx_gains", []), dtype=float)):
        y += float(gain) * lowpass(t, pin, float(tau_s))
    for fast_s, slow_s, gain in zip(
        np.asarray(fit.get("tx_tail_fast_s", []), dtype=float),
        np.asarray(fit.get("tx_tail_slow_s", []), dtype=float),
        np.asarray(fit.get("tx_tail_gains", []), dtype=float),
    ):
        y += float(gain) * (lowpass(t, pin, float(fast_s)) - lowpass(t, pin, float(slow_s)))
    return y


def write_reduced_spice_model(path: Path, fit: dict[str, object], nports: int, output_port: int, r_stage: float = 1000.0) -> None:
    delay_ns = float(fit["delay_ns"])
    taus_ns = np.asarray(fit["taus_ns"], dtype=float)
    gains = np.asarray(fit["gains"], dtype=float)
    tail_fast_ns = np.asarray(fit.get("tail_fast_ns", []), dtype=float)
    tail_slow_ns = np.asarray(fit.get("tail_slow_ns", []), dtype=float)
    tail_gains = np.asarray(fit.get("tail_gains", []), dtype=float)
    ring_delay_ns = np.asarray(fit.get("ring_delay_ns", []), dtype=float)
    ring_fast_ns = np.asarray(fit.get("ring_fast_ns", []), dtype=float)
    ring_slow_ns = np.asarray(fit.get("ring_slow_ns", []), dtype=float)
    ring_gains = np.asarray(fit.get("ring_gains", []), dtype=float)
    has_tx_correction = bool(len(np.asarray(fit.get("tx_gains", []), dtype=float)) or len(np.asarray(fit.get("tx_tail_gains", []), dtype=float)))
    input_node = "pin" if has_tx_correction else "p1"
    if nports == 2:
        subckt = ".subckt s_equivalent p1 p2"
        output_node = "p2"
        leak_lines: list[str] = []
    elif nports == 4:
        subckt = ".subckt s_equivalent p1 p2 p3 p4"
        output_node = f"p{output_port}"
        leak_lines = [f"Rleak_p{idx} p{idx} 0 1e12" for idx in (2, 3, 4) if idx != output_port]
    else:
        raise ValueError(nports)

    lines = [
        "* Touchstone-only reduced S-parameter macromodel",
        "* Scope: matched 50 ohm transient channel qualification, not arbitrary termination replacement.",
        subckt,
    ]
    if has_tx_correction:
        lines.extend(reflection_model_lines(fit, r_stage=r_stage))
    lines.extend(
        [
            f"Tdelay {input_node} 0 ndelay 0 Z0=50 TD={delay_ns:.12g}n",
            "Rdelay_term ndelay 0 50",
            *leak_lines,
            "Rsum sum 0 1",
        ]
    )
    for idx, (tau_ns, gain) in enumerate(zip(taus_ns, gains), start=1):
        cap_f = (float(tau_ns) * 1e-9) / r_stage
        lines.extend(
            [
                f"Ebrsrc{idx} brsrc{idx} 0 ndelay 0 1",
                f"Rbr{idx} brsrc{idx} br{idx} {r_stage:.12g}",
                f"Cbr{idx} br{idx} 0 {cap_f:.12g}",
                f"Gsum{idx} 0 sum br{idx} 0 {float(gain):.12g}",
            ]
        )
    for idx, (fast_ns, slow_ns, gain) in enumerate(zip(tail_fast_ns, tail_slow_ns, tail_gains), start=1):
        fast_cap_f = (float(fast_ns) * 1e-9) / r_stage
        slow_cap_f = (float(slow_ns) * 1e-9) / r_stage
        lines.extend(
            [
                f"Etailfsrc{idx} tailfsrc{idx} 0 ndelay 0 1",
                f"Rtailf{idx} tailfsrc{idx} tailf{idx} {r_stage:.12g}",
                f"Ctailf{idx} tailf{idx} 0 {fast_cap_f:.12g}",
                f"Gtailf{idx} 0 sum tailf{idx} 0 {float(gain):.12g}",
                f"Etailssrc{idx} tailssrc{idx} 0 ndelay 0 1",
                f"Rtails{idx} tailssrc{idx} tails{idx} {r_stage:.12g}",
                f"Ctails{idx} tails{idx} 0 {slow_cap_f:.12g}",
                f"Gtails{idx} 0 sum tails{idx} 0 {-float(gain):.12g}",
            ]
        )
    for idx, (delay_ns_i, fast_ns, slow_ns, gain) in enumerate(zip(ring_delay_ns, ring_fast_ns, ring_slow_ns, ring_gains), start=1):
        fast_cap_f = (float(fast_ns) * 1e-9) / r_stage
        slow_cap_f = (float(slow_ns) * 1e-9) / r_stage
        base = f"ringbase{idx}"
        if abs(float(delay_ns_i)) > 1e-15:
            lines.extend(
                [
                    f"Tringdelay{idx} {input_node} 0 {base} 0 Z0=1e12 TD={float(delay_ns_i):.12g}n",
                    f"Rringdelay_term{idx} {base} 0 1e12",
                ]
            )
        else:
            lines.append(f"Eringbase{idx} {base} 0 {input_node} 0 1")
        lines.extend(
            [
                f"Eringfsrc{idx} ringfsrc{idx} 0 {base} 0 1",
                f"Rringf{idx} ringfsrc{idx} ringf{idx} {r_stage:.12g}",
                f"Cringf{idx} ringf{idx} 0 {fast_cap_f:.12g}",
                f"Gringf{idx} 0 sum ringf{idx} 0 {float(gain):.12g}",
                f"Eringssrc{idx} ringssrc{idx} 0 {base} 0 1",
                f"Rrings{idx} ringssrc{idx} rings{idx} {r_stage:.12g}",
                f"Crings{idx} rings{idx} 0 {slow_cap_f:.12g}",
                f"Grings{idx} 0 sum rings{idx} 0 {-float(gain):.12g}",
            ]
        )
    lines.extend([f"Eout outdrv 0 sum 0 2", f"Rout outdrv {output_node} 50", ".ends s_equivalent", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="ascii")


def reduced_transfer_response(freqs: np.ndarray, fit: dict[str, object]) -> np.ndarray:
    omega = 2.0 * np.pi * np.asarray(freqs, dtype=float)
    jw = 1j * omega
    delay = np.exp(-jw * float(fit.get("delay_s", 0.0)))
    response = np.zeros_like(jw, dtype=complex)
    for tau_s, gain in zip(np.asarray(fit.get("taus_s", []), dtype=float), np.asarray(fit.get("gains", []), dtype=float)):
        response += float(gain) / (1.0 + jw * float(tau_s))
    for fast_s, slow_s, gain in zip(
        np.asarray(fit.get("tail_fast_s", []), dtype=float),
        np.asarray(fit.get("tail_slow_s", []), dtype=float),
        np.asarray(fit.get("tail_gains", []), dtype=float),
    ):
        response += float(gain) * (1.0 / (1.0 + jw * float(fast_s)) - 1.0 / (1.0 + jw * float(slow_s)))
    response *= delay
    for delay_s, fast_s, slow_s, gain in zip(
        np.asarray(fit.get("ring_delay_s", []), dtype=float),
        np.asarray(fit.get("ring_fast_s", []), dtype=float),
        np.asarray(fit.get("ring_slow_s", []), dtype=float),
        np.asarray(fit.get("ring_gains", []), dtype=float),
    ):
        response += (
            float(gain)
            * np.exp(-jw * float(delay_s))
            * (1.0 / (1.0 + jw * float(fast_s)) - 1.0 / (1.0 + jw * float(slow_s)))
        )
    return response


def reflection_transfer_response(freqs: np.ndarray, fit: dict[str, object]) -> np.ndarray:
    omega = 2.0 * np.pi * np.asarray(freqs, dtype=float)
    jw = 1j * omega
    response = np.zeros_like(jw, dtype=complex)
    for tau_s, gain in zip(np.asarray(fit.get("tx_taus_s", []), dtype=float), np.asarray(fit.get("tx_gains", []), dtype=float)):
        response += float(gain) / (1.0 + jw * float(tau_s))
    for fast_s, slow_s, gain in zip(
        np.asarray(fit.get("tx_tail_fast_s", []), dtype=float),
        np.asarray(fit.get("tx_tail_slow_s", []), dtype=float),
        np.asarray(fit.get("tx_tail_gains", []), dtype=float),
    ):
        response += float(gain) * (1.0 / (1.0 + jw * float(fast_s)) - 1.0 / (1.0 + jw * float(slow_s)))
    return response


def one_path_frequency_metrics(freqs: np.ndarray, original: np.ndarray, fitted: np.ndarray) -> dict[str, float]:
    diff = fitted - original
    row: dict[str, float] = {
        "fit_complex_rms": float(np.sqrt(np.mean(np.abs(diff) ** 2))),
        "fit_complex_max": float(np.max(np.abs(diff))),
    }
    mask = np.abs(original) > 1e-2
    if np.any(mask):
        mag_err_db = 20 * np.log10(np.maximum(np.abs(fitted[mask]), 1e-30)) - 20 * np.log10(np.maximum(np.abs(original[mask]), 1e-30))
        phase_err = np.rad2deg(np.angle(fitted[mask] * np.conj(original[mask])))
        row["fit_mag_db_rms_above_m40"] = float(np.sqrt(np.mean(mag_err_db**2)))
        row["fit_mag_db_max_above_m40"] = float(np.max(np.abs(mag_err_db)))
        row["fit_phase_deg_rms_above_m40"] = float(np.sqrt(np.mean(phase_err**2)))
        row["fit_phase_deg_max_above_m40"] = float(np.max(np.abs(phase_err)))
    else:
        row["fit_mag_db_rms_above_m40"] = float("nan")
        row["fit_mag_db_max_above_m40"] = float("nan")
        row["fit_phase_deg_rms_above_m40"] = float("nan")
        row["fit_phase_deg_max_above_m40"] = float("nan")
    gd_mask = np.abs(original) > 1e-2
    gd_orig = group_delay(freqs[gd_mask], original[gd_mask]) if np.count_nonzero(gd_mask) >= 3 else np.array([], dtype=float)
    gd_fit = group_delay(freqs[gd_mask], fitted[gd_mask]) if np.count_nonzero(gd_mask) >= 3 else np.array([], dtype=float)
    if len(gd_orig) and len(gd_fit):
        gd_err = np.abs(gd_fit - gd_orig)
        row["fit_group_delay_rms_ps"] = float(np.sqrt(np.mean(gd_err**2)) * 1e12)
        row["fit_group_delay_max_ps"] = float(np.max(gd_err) * 1e12)
    else:
        row["fit_group_delay_rms_ps"] = float("nan")
        row["fit_group_delay_max_ps"] = float("nan")
    return row


def reduced_candidate_metrics(nw, fit: dict[str, object], out_idx: int, in_idx: int, high_fmax: float, dense_samples: int) -> dict[str, object]:
    freqs = np.asarray(nw.frequency.f, dtype=float)
    original = np.asarray(nw.s[:, out_idx, in_idx], dtype=complex)
    fitted = reduced_transfer_response(freqs, fit)
    metrics: dict[str, object] = one_path_frequency_metrics(freqs, original, fitted)
    metrics["model_order"] = int(
        len(np.asarray(fit.get("gains", [])))
        + len(np.asarray(fit.get("tail_gains", [])))
        + len(np.asarray(fit.get("ring_gains", [])))
        + len(np.asarray(fit.get("tx_gains", [])))
        + len(np.asarray(fit.get("tx_tail_gains", [])))
        + 1
    )
    metrics["pole_count_array"] = int(metrics["model_order"])
    metrics["is_passive"] = True
    metrics["passivity_violation_bands_hz"] = json.dumps([])
    input_abs = np.abs(fitted)
    sample_idx = int(np.nanargmax(input_abs)) if len(input_abs) else 0
    metrics["max_sv_input_samples"] = float(input_abs[sample_idx]) if len(input_abs) else float("nan")
    metrics["max_sv_input_samples_freq_hz"] = float(freqs[sample_idx]) if len(freqs) else float("nan")
    dense_freqs = np.linspace(0.0, high_fmax, dense_samples)
    dense_response = reduced_transfer_response(dense_freqs, fit)
    dense_abs = np.abs(dense_response)
    dense_idx = int(np.nanargmax(dense_abs)) if len(dense_abs) else 0
    metrics["max_sv_high"] = float(dense_abs[dense_idx]) if len(dense_abs) else float("nan")
    metrics["max_sv_high_freq_hz"] = float(dense_freqs[dense_idx]) if len(dense_freqs) else float("nan")
    metrics["sv_at_high_fmax"] = float(dense_abs[-1]) if len(dense_abs) else float("nan")
    return metrics


def plot_reduced_step_fit(refs: dict[int, dict[str, np.ndarray]], fit: dict[str, object], path: Path, title: str) -> None:
    fig, axes = plt.subplots(len(refs), 2, figsize=(13, max(5, 2.7 * len(refs))), sharex=True, constrained_layout=True)
    axes_arr = np.asarray(axes).reshape(len(refs), 2)
    for row_idx, edge in enumerate(sorted(refs)):
        ref = refs[edge]
        t = ref["time"]
        rx_pred = reduced_s21_waveform(t, edge, fit)
        tx_pred = tx_reflection_waveform(t, edge, fit)
        axes_arr[row_idx, 0].plot(t * 1e9, ref.get("v_p1_target", ref["v_p1"]), label="Touchstone-derived target", linewidth=1.7)
        axes_arr[row_idx, 0].plot(t * 1e9, tx_pred, "--", label="TX/reflection fit", linewidth=1.35)
        axes_arr[row_idx, 0].set_title(f"{edge} ps TX", loc="left")
        axes_arr[row_idx, 1].plot(t * 1e9, ref["v_p2"], label="Touchstone-derived target", linewidth=1.7)
        axes_arr[row_idx, 1].plot(t * 1e9, rx_pred, "--", label="RX reduced fit", linewidth=1.35)
        axes_arr[row_idx, 1].set_title(f"{edge} ps RX", loc="left")
        for ax in axes_arr[row_idx]:
            ax.set_ylabel("Voltage (V)")
            ax.grid(True, color="#d7dde6")
    axes_arr[0, 0].legend(frameon=False)
    axes_arr[0, 1].legend(frameon=False)
    axes_arr[-1, 0].set_xlabel("Time (ns)")
    axes_arr[-1, 1].set_xlabel("Time (ns)")
    fig.suptitle(title, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def build_reduced_candidate(
    args: argparse.Namespace,
    nw,
    name: str,
    base: dict[str, object],
    channel_id: str,
    model_dir: Path,
    plot_dir: Path,
    high_fmax: float,
) -> dict[str, object]:
    nports = int(nw.nports)
    if name.startswith("reduced_s2p") and nports != 2:
        return {**base, "candidate": name, "candidate_family": name, "fit_source": "touchstone_time_domain", "math_pass": False, "math_fail_reasons": "candidate_requires_s2p"}
    if name.startswith("reduced_4p") and nports != 4:
        return {**base, "candidate": name, "candidate_family": name, "fit_source": "touchstone_time_domain", "math_pass": False, "math_fail_reasons": "candidate_requires_s4p"}

    profile = reduced_candidate_profile(name, nports)
    out_idx, in_idx = dominant_rx_path(nports)
    output_port = out_idx + 1
    use_scope = str(profile["use_scope"])
    refs = reduced_fit_refs(nw, out_idx, in_idx, args.reduced_fit_stop_ns, args.reduced_fit_step_ps)
    if bool(profile["include_reflection"]):
        for edge, ref in refs.items():
            t = ref["time"]
            ref["v_p1_target"] = 0.5 * source_voltage(t, edge) + synthetic_transfer_waveform(nw, in_idx, in_idx, t, edge)
    delay_info = estimate_reduced_delay(nw, out_idx, in_idx, refs, bool(profile["delay_equalized"]))
    delay_ns = float(delay_info["delay_ns"])
    fit = fit_reduced_basis(
        refs,
        delay_ns,
        parse_float_values(args.reduced_rc_taus_ns),
        parse_tau_pairs(args.reduced_tail_pairs_ns),
        args.reduced_gain_bound,
        args.reduced_fit_reg,
    )
    if bool(profile["include_ring"]):
        fit.update(
            fit_ring_basis(
                refs,
                fit,
                parse_float_values(args.reduced_ring_delays_ns),
                parse_tau_pairs(args.reduced_ring_tau_pairs_ns),
                args.reduced_gain_bound,
                args.reduced_fit_reg,
            )
        )
    else:
        fit.update(fit_ring_basis(refs, fit, [], [], args.reduced_gain_bound, args.reduced_fit_reg))
    if bool(profile["include_reflection"]):
        fit.update(
            fit_reflection_basis(
                refs,
                parse_float_values(args.reduced_reflect_taus_ns),
                parse_tau_pairs(args.reduced_reflect_tail_pairs_ns),
                args.reduced_gain_bound,
                args.reduced_fit_reg,
            )
        )
    else:
        fit.update(fit_reflection_basis({}, [], [], args.reduced_gain_bound, args.reduced_fit_reg))

    sp_path = model_dir / name / f"{channel_id}_{name}.sp"
    write_reduced_spice_model(sp_path, fit, nports, output_port)
    plot_reduced_step_fit(refs, fit, plot_dir / f"{name}_touchstone_step_fit.png", f"{channel_id}: {name} Touchstone-derived step fit")

    row: dict[str, object] = {
        **base,
        "candidate": name,
        "candidate_family": name,
        "stage": "touchstone_time_fit",
        "fit_source": "touchstone_time_domain",
        "use_scope": use_scope,
        "view_role": profile["view_role"],
        "dominant_path": f"S{out_idx + 1}{in_idx + 1}",
        "delay_estimate_ns": float(delay_ns),
        "delay_equalized": bool(profile["delay_equalized"]),
        "delay_estimator_source": delay_info.get("delay_estimator_source", ""),
        "delay_step_threshold_ns": delay_info.get("delay_step_threshold_ns", ""),
        "delay_impulse_peak_ns": delay_info.get("delay_impulse_peak_ns", ""),
        "delay_group_delay_median_ns": delay_info.get("delay_group_delay_median_ns", ""),
        "delay_candidate_sources": delay_info.get("delay_candidate_sources", ""),
        "basis_order": int(len(np.asarray(fit.get("gains", []))) + len(np.asarray(fit.get("tail_gains", [])))),
        "ring_basis_count": int(len(np.asarray(fit.get("ring_gains", [])))),
        "reflection_basis_count": int(len(np.asarray(fit.get("tx_gains", []))) + len(np.asarray(fit.get("tx_tail_gains", [])))),
        "dc_gain_to_load": fit.get("dc_gain_to_load", ""),
        "reduced_fit_objective": fit.get("objective", ""),
        "spice_file": rel(sp_path),
        "fit_warnings": "",
    }
    for key, value in fit.items():
        if key.startswith("edge") and isinstance(value, (float, int, np.floating)):
            row[key] = float(value)
    row.update(reduced_candidate_metrics(nw, fit, out_idx, in_idx, high_fmax, args.dense_samples))
    row.update(delay_removed_group_delay_metrics(nw, out_idx, in_idx, delay_ns))
    for key in (
        "fit_complex_rms",
        "fit_complex_max",
        "fit_mag_db_rms_above_m40",
        "fit_mag_db_max_above_m40",
        "fit_phase_deg_rms_above_m40",
        "fit_phase_deg_max_above_m40",
        "fit_group_delay_rms_ps",
        "fit_group_delay_max_ps",
    ):
        if key in row:
            row[f"rx_{key}"] = row[key]
    freqs = np.asarray(nw.frequency.f, dtype=float)
    refl_out, refl_in = input_reflection_path(nports)
    if bool(profile["include_reflection"]):
        reflection_fit = reflection_transfer_response(freqs, fit)
    else:
        reflection_fit = np.zeros_like(freqs, dtype=complex)
    row.update(
        prefixed_metrics(
            "reflection",
            one_path_frequency_metrics(freqs, np.asarray(nw.s[:, refl_out, refl_in], dtype=complex), reflection_fit),
        )
    )
    failures = math_gate_failures(
        row,
        args.rms_threshold,
        args.mag_db_max_threshold,
        args.group_delay_rms_ps_threshold,
        args.max_low_freq_start_hz,
        args.min_frequency_points,
        args.max_sv_high_threshold,
    )
    row["math_pass"] = not failures
    row["math_fail_reasons"] = ";".join(failures)
    return row


def build_analysis_only_candidate(name: str, base: dict[str, object]) -> dict[str, object]:
    profile = reduced_candidate_profile(name, int(base.get("ports") or 0))
    return {
        **base,
        "candidate": name,
        "candidate_family": name,
        "stage": "analysis_only",
        "fit_source": "touchstone_time_domain",
        "use_scope": profile["use_scope"],
        "view_role": profile["view_role"],
        "math_pass": False,
        "math_fail_reasons": "analysis_only_not_ngspice_model",
        "trust_class": "FAIL",
        "trust_fail_reasons": "analysis_only_not_ngspice_model",
        "rx_trust_class": "FAIL",
        "rx_fail_reasons": "analysis_only_not_ngspice_model",
        "reflection_trust_class": "FAIL",
        "reflection_fail_reasons": "analysis_only_not_ngspice_model",
        "full_model_trust_class": "FAIL",
        "full_model_fail_reasons": "analysis_only_not_ngspice_model",
    }


class SmokeCase:
    def __init__(self, name: str, rsrc_ohm: float | None, edge_ps: float, amplitude_v: float, stop_ns: float = 12.0):
        self.name = name
        self.rsrc_ohm = rsrc_ohm
        self.edge_ps = edge_ps
        self.amplitude_v = amplitude_v
        self.stop_ns = stop_ns


def smoke_cases(stop_ns: float = 12.0) -> list[SmokeCase]:
    cases: list[SmokeCase] = []
    for rsrc in (None, 50.0):
        for edge in (5.0, 50.0, 500.0):
            label = "ideal" if rsrc is None else "r50"
            cases.append(SmokeCase(f"amp1p5_edge{int(edge)}_{label}", rsrc, edge, 1.5, stop_ns=stop_ns))
    for amp in (0.05, 0.1, 0.5):
        cases.append(SmokeCase(f"amp{str(amp).replace('.', 'p')}_edge5_ideal", None, 5.0, amp, stop_ns=stop_ns))
        cases.append(SmokeCase(f"amp{str(amp).replace('.', 'p')}_edge5_r50", 50.0, 5.0, amp, stop_ns=stop_ns))
    return cases


def audit_cases(stop_ns: float = 12.0) -> list[SmokeCase]:
    return [
        SmokeCase("audit_amp1p5_edge5_r50", 50.0, 5.0, 1.5, stop_ns=stop_ns),
        SmokeCase("audit_amp1p5_edge50_r50", 50.0, 50.0, 1.5, stop_ns=stop_ns),
        SmokeCase("audit_amp1p5_edge500_r50", 50.0, 500.0, 1.5, stop_ns=stop_ns),
    ]


def selected_audit_cases(args: argparse.Namespace) -> list[SmokeCase]:
    cases = audit_cases(args.audit_stop_ns)
    max_cases = int(getattr(args, "max_audit_cases", 0) or 0)
    return cases[:max_cases] if max_cases > 0 else cases


def source_lines(case: SmokeCase, drive_node: str = "p1") -> tuple[list[str], str]:
    edge = case.edge_ps * 1e-12
    amp = case.amplitude_v
    if case.rsrc_ohm is None:
        return (
            [f"Vin  {drive_node}  0  PWL(0 0 1n 0 {fmt(1e-9 + edge)} {fmt(amp)} 9n {fmt(amp)} {fmt(9e-9 + edge)} 0)"],
            "ideal",
        )
    return (
        [
            f"Vin   src  0  PWL(0 0 1n 0 {fmt(1e-9 + edge)} {fmt(amp)} 9n {fmt(amp)} {fmt(9e-9 + edge)} 0)",
            f"Rsrc  src  {drive_node}  {fmt(case.rsrc_ohm)}",
        ],
        "src",
    )


def write_ngspice_deck(deck: Path, model_spice: Path, nports: int, case: SmokeCase) -> None:
    src, src_node = source_lines(case, "p1")
    stop = case.stop_ns * 1e-9
    include = str(model_spice.resolve()).replace("\\", "/")
    if nports == 2:
        channel = ["Xchannel  p1  p2  s_equivalent", "Rterm  p2  0  50"]
        save = ".save V(p1) V(p2)" + (" V(src)" if src_node == "src" else "")
    elif nports == 4:
        channel = [
            "Xchannel  p1  p2  p3  p4  s_equivalent",
            "Rnear_neg  p2  0  50",
            "Rterm_pos  p3  0  50",
            "Rterm_neg  p4  0  50",
        ]
        save = ".save V(p1) V(p2) V(p3) V(p4)" + (" V(src)" if src_node == "src" else "")
    else:
        raise ValueError(nports)
    text = "\n".join(
        [
            f"* ngspice channel smoke: {case.name}",
            ".temp 27",
            ".options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12",
            *src,
            f".include '{include}'",
            *channel,
            save,
            f".tran 10p {fmt(stop)}",
            ".end",
            "",
        ]
    )
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(text, encoding="ascii")


def parse_minmax(data: dict[str, np.ndarray], signal: str) -> tuple[float, float, bool]:
    values = data[signal]
    return float(np.nanmin(values)), float(np.nanmax(values)), bool(np.all(np.isfinite(values)))


def crossing_time(t: np.ndarray, y: np.ndarray, threshold: float, rise: bool, after: float) -> float | None:
    if rise:
        idxs = np.where((y[:-1] < threshold) & (y[1:] >= threshold))[0]
    else:
        idxs = np.where((y[:-1] >= threshold) & (y[1:] < threshold))[0]
    idxs = [idx for idx in idxs if t[idx] >= after]
    if not idxs:
        return None
    i = idxs[0]
    if y[i + 1] == y[i]:
        return float(t[i])
    return float(t[i] + (threshold - y[i]) * (t[i + 1] - t[i]) / (y[i + 1] - y[i]))


def waveform_levels(t: np.ndarray, y: np.ndarray) -> tuple[float, float, float, bool]:
    finite = np.isfinite(t) & np.isfinite(y)
    if not np.any(finite):
        return float("nan"), float("nan"), float("nan"), True
    tf = t[finite]
    yf = y[finite]
    initial_stop = min(0.9e-9, max(float(tf[-1]) * 0.1, float(tf[0])))
    initial = yf[tf <= initial_stop]
    low = float(np.nanmedian(initial)) if len(initial) >= 3 else float(np.nanpercentile(yf, 5.0))
    upper_cut = float(np.nanpercentile(yf, 90.0))
    lower_cut = float(np.nanpercentile(yf, 10.0))
    upper = yf[yf >= upper_cut]
    lower = yf[yf <= lower_cut]
    upper_level = float(np.nanmedian(upper)) if len(upper) else float(np.nanmax(yf))
    lower_level = float(np.nanmedian(lower)) if len(lower) else float(np.nanmin(yf))
    if abs(upper_level - low) >= abs(lower_level - low):
        active = upper_level
    else:
        active = lower_level
    threshold = 0.5 * (low + active)
    return low, active, threshold, active >= low


def edge_crossings(t: np.ndarray, y: np.ndarray, threshold: float, active_high: bool) -> tuple[float | None, float | None]:
    first_edge_is_rising = active_high
    rise = crossing_time(t, y, threshold, first_edge_is_rising, 0.5e-9)
    fall = crossing_time(t, y, threshold, not first_edge_is_rising, 8.5e-9)
    return rise, fall


def threshold_crossing_count(t: np.ndarray, y: np.ndarray, threshold: float, lo: float, hi: float) -> int:
    mask = (t[:-1] >= lo) & (t[:-1] <= hi)
    if not np.any(mask):
        return 0
    y0 = y[:-1][mask]
    y1 = y[1:][mask]
    return int(np.sum(((y0 < threshold) & (y1 >= threshold)) | ((y0 >= threshold) & (y1 < threshold))))


def smoke_waveform_sanity(t: np.ndarray, y: np.ndarray, low: float, active: float, threshold: float) -> dict[str, object]:
    swing = max(abs(active - low), 1e-12)
    high = max(low, active)
    low_level = min(low, active)
    pre_mask = t <= 0.9e-9
    settle_start = max(0.0, min(float(t[-1]) - 0.5e-9, 10.0e-9))
    settle_mask = t >= settle_start
    out: dict[str, object] = {
        "pre_response_abs_v": float(np.nanmax(np.abs(y[pre_mask] - low))) if np.any(pre_mask) else float("nan"),
        "overshoot_v": max(0.0, float(np.nanmax(y) - high)),
        "undershoot_v": max(0.0, float(low_level - np.nanmin(y))),
        "settling_abs_v": abs(float(np.nanmedian(y[settle_mask])) - low) if np.any(settle_mask) else float("nan"),
        "rise_threshold_crossing_count": threshold_crossing_count(t, y, threshold, 0.5e-9, 2.5e-9),
        "fall_threshold_crossing_count": threshold_crossing_count(t, y, threshold, 8.5e-9, min(float(t[-1]), 10.8e-9)),
    }
    out["swing_v"] = float(swing)
    out["ringing_threshold_ambiguous"] = bool(
        int(out["rise_threshold_crossing_count"]) > 1 or int(out["fall_threshold_crossing_count"]) > 1
    )
    out["overshoot_pct_swing"] = 100.0 * float(out["overshoot_v"]) / swing
    out["undershoot_pct_swing"] = 100.0 * float(out["undershoot_v"]) / swing
    out["settling_pct_swing"] = 100.0 * float(out["settling_abs_v"]) / swing
    out["pre_response_pct_swing"] = 100.0 * float(out["pre_response_abs_v"]) / swing
    return out


def smoke_delay_confidence(row: dict[str, object], args: argparse.Namespace) -> tuple[str, str]:
    reasons: list[str] = []
    for prefix in ("tx", "rx"):
        try:
            swing = float(row.get(f"{prefix}_swing_v", 0.0) or 0.0)
            if swing < args.min_delay_confidence_swing_v:
                reasons.append(f"{prefix}_low_swing")
        except Exception:
            reasons.append(f"{prefix}_swing_parse")
        if str(row.get(f"{prefix}_ringing_threshold_ambiguous", "")).lower() == "true":
            reasons.append(f"{prefix}_threshold_ambiguous")
        if row.get(f"{prefix}_rise50_ns", "") == "" or row.get(f"{prefix}_fall50_ns", "") == "":
            reasons.append(f"{prefix}_missing_50pct_crossing")
    if reasons:
        return "low", ";".join(sorted(set(reasons)))
    return "high", ""


def annotate_smoke_confidence(row: dict[str, object], args: argparse.Namespace) -> None:
    shape_terms: list[float] = []
    for prefix in ("tx", "rx"):
        for key in ("pre_response_abs_v", "settling_abs_v", "overshoot_v", "undershoot_v"):
            value = row.get(f"{prefix}_{key}", "")
            try:
                if value != "" and math.isfinite(float(value)):
                    shape_terms.append(abs(float(value)))
            except Exception:
                continue
    row["voltage_shape_score_v"] = max(shape_terms) if shape_terms else float("nan")
    confidence, reasons = smoke_delay_confidence(row, args)
    row["threshold_delay_confidence"] = confidence
    row["threshold_delay_confidence_reasons"] = reasons


def transient_metrics_from_raw(raw: Path, nports: int, case: SmokeCase, return_code: int, log: Path) -> dict[str, object]:
    row: dict[str, object] = {
        "return_code": return_code,
        "raw": rel(raw),
        "log": rel(log),
    }
    tx_sig = "v(p1)"
    rx_sig = "v(p2)" if nports == 2 else "v(p3)"
    try:
        data = parse_ngspice_raw(raw)
        t = data["time"]
        row["points"] = len(t)
        row["stop_ns"] = float(t[-1] * 1e9)
        for signal in (tx_sig, rx_sig):
            vmin, vmax, finite = parse_minmax(data, signal)
            row[f"{signal}_min_v"] = vmin
            row[f"{signal}_max_v"] = vmax
            row[f"{signal}_finite"] = finite
        tx_low, tx_active, tx_threshold, tx_active_high = waveform_levels(t, data[tx_sig])
        rx_low, rx_active, rx_threshold, rx_active_high = waveform_levels(t, data[rx_sig])
        row["tx_low_v"] = tx_low
        row["tx_active_v"] = tx_active
        row["tx_threshold_v"] = tx_threshold
        row["rx_low_v"] = rx_low
        row["rx_active_v"] = rx_active
        row["rx_threshold_v"] = rx_threshold
        tx_rise, tx_fall = edge_crossings(t, data[tx_sig], tx_threshold, tx_active_high)
        rx_rise, rx_fall = edge_crossings(t, data[rx_sig], rx_threshold, rx_active_high)
        row["tx_rise50_ns"] = "" if tx_rise is None else tx_rise * 1e9
        row["rx_rise50_ns"] = "" if rx_rise is None else rx_rise * 1e9
        row["tx_fall50_ns"] = "" if tx_fall is None else tx_fall * 1e9
        row["rx_fall50_ns"] = "" if rx_fall is None else rx_fall * 1e9
        if tx_rise is not None and rx_rise is not None:
            row["rx_minus_tx_rise50_ps"] = (rx_rise - tx_rise) * 1e12
        if tx_fall is not None and rx_fall is not None:
            row["rx_minus_tx_fall50_ps"] = (rx_fall - tx_fall) * 1e12
        for prefix, sig, low, active, threshold in (
            ("tx", tx_sig, tx_low, tx_active, tx_threshold),
            ("rx", rx_sig, rx_low, rx_active, rx_threshold),
        ):
            sanity = smoke_waveform_sanity(t, data[sig], low, active, threshold)
            for key, value in sanity.items():
                row[f"{prefix}_{key}"] = value
        row["finite_reasonable"] = (
            return_code == 0
            and float(row["stop_ns"]) >= case.stop_ns * 0.999
            and all(abs(float(row[f"{signal}_min_v"])) < 10 and abs(float(row[f"{signal}_max_v"])) < 10 for signal in (tx_sig, rx_sig))
        )
    except Exception as exc:
        row["parse_error"] = str(exc)
        row["finite_reasonable"] = False
    if log.exists():
        text = log.read_text(encoding="utf-8", errors="replace")
        trouble = ""
        for line in text.splitlines():
            if "Timestep too small" in line or "trouble with node" in line or "Error" in line:
                trouble = line
        row["last_trouble"] = trouble
    return row


def run_ngspice_cases(ngspice: Path, model_spice: Path, nports: int, out_dir: Path, cases: list[SmokeCase], timeout: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in cases:
        deck = out_dir / f"{case.name}.sp"
        raw = deck.with_suffix(".raw")
        log = deck.with_suffix(".log")
        write_ngspice_deck(deck, model_spice, nports, case)
        try:
            completed = subprocess.run(
                [str(ngspice), "-b", "-o", log.name, "-r", raw.name, deck.name],
                cwd=out_dir,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            row = transient_metrics_from_raw(raw, nports, case, completed.returncode, log)
        except Exception as exc:
            row = {"return_code": -999, "raw": rel(raw), "log": rel(log), "finite_reasonable": False, "run_error": str(exc)}
        row.update({"case": case.name, "rsrc_ohm": "ideal" if case.rsrc_ohm is None else case.rsrc_ohm, "edge_ps": case.edge_ps, "amplitude_v": case.amplitude_v})
        rows.append(row)
    return rows


def smoke_gate_failures(row: dict[str, object], args: argparse.Namespace) -> list[str]:
    failures: list[str] = []
    if not bool(row.get("finite_reasonable")):
        failures.append("ngspice_nonfinite_or_unreasonable")
    for prefix in ("tx", "rx"):
        pre = row.get(f"{prefix}_pre_response_abs_v", "")
        settle = row.get(f"{prefix}_settling_abs_v", "")
        over = row.get(f"{prefix}_overshoot_pct_swing", "")
        under = row.get(f"{prefix}_undershoot_pct_swing", "")
        try:
            low = float(row.get(f"{prefix}_low_v", 0.0))
            active = float(row.get(f"{prefix}_active_v", 0.0))
            swing = abs(active - low)
            if pre != "" and math.isfinite(float(pre)) and float(pre) > args.pre_response_fail_v:
                failures.append(f"{prefix}_pre_response")
            if settle != "" and math.isfinite(float(settle)) and float(settle) > args.settling_fail_v:
                failures.append(f"{prefix}_settling")
            if swing >= args.min_smoke_swing_v and over != "" and math.isfinite(float(over)) and float(over) > args.overshoot_fail_pct:
                failures.append(f"{prefix}_overshoot")
            if swing >= args.min_smoke_swing_v and under != "" and math.isfinite(float(under)) and float(under) > args.overshoot_fail_pct:
                failures.append(f"{prefix}_undershoot")
        except Exception:
            failures.append(f"{prefix}_smoke_metric_parse")
    return failures


def smoke_gate_warnings(row: dict[str, object], args: argparse.Namespace) -> list[str]:
    warnings_out: list[str] = []
    for prefix in ("tx", "rx"):
        if str(row.get(f"{prefix}_ringing_threshold_ambiguous")).lower() == "true":
            warnings_out.append(f"{prefix}_edge_ringing_threshold_ambiguous")
        try:
            low = float(row.get(f"{prefix}_low_v", 0.0))
            active = float(row.get(f"{prefix}_active_v", 0.0))
            swing = abs(active - low)
            if swing < args.min_smoke_swing_v:
                warnings_out.append(f"{prefix}_low_swing_metric_floor")
            pre_pct = row.get(f"{prefix}_pre_response_pct_swing", "")
            if pre_pct != "" and math.isfinite(float(pre_pct)) and float(pre_pct) > args.pre_response_warn_pct:
                warnings_out.append(f"{prefix}_pre_response_margin")
            settle_pct = row.get(f"{prefix}_settling_pct_swing", "")
            if settle_pct != "" and math.isfinite(float(settle_pct)) and float(settle_pct) > args.settling_warn_pct:
                warnings_out.append(f"{prefix}_settling_margin")
            over_pct = row.get(f"{prefix}_overshoot_pct_swing", "")
            if swing >= args.min_smoke_swing_v and over_pct != "" and math.isfinite(float(over_pct)) and float(over_pct) > args.overshoot_warn_pct:
                warnings_out.append(f"{prefix}_overshoot_margin")
            under_pct = row.get(f"{prefix}_undershoot_pct_swing", "")
            if swing >= args.min_smoke_swing_v and under_pct != "" and math.isfinite(float(under_pct)) and float(under_pct) > args.overshoot_warn_pct:
                warnings_out.append(f"{prefix}_undershoot_margin")
        except Exception:
            warnings_out.append(f"{prefix}_smoke_warning_parse")
    if str(row.get("threshold_delay_confidence", "")) == "low":
        warnings_out.append("threshold_delay_confidence_low")
        try:
            shape_score = float(row.get("voltage_shape_score_v", float("nan")))
            if math.isfinite(shape_score) and shape_score <= max(args.pre_response_fail_v, args.settling_fail_v):
                warnings_out.append("voltage_shape_ok_threshold_delay_low")
        except Exception:
            warnings_out.append("threshold_delay_confidence_parse")
    return warnings_out


def smoke_prefix_shape_score(row: dict[str, object], prefix: str) -> float:
    values: list[float] = []
    for key in ("pre_response_abs_v", "settling_abs_v", "overshoot_v", "undershoot_v"):
        value = row.get(f"{prefix}_{key}", "")
        try:
            if value != "" and math.isfinite(float(value)):
                values.append(abs(float(value)))
        except Exception:
            continue
    return max(values) if values else float("nan")


def smoke_prefix_gate_failures(row: dict[str, object], args: argparse.Namespace, prefix: str) -> list[str]:
    failures: list[str] = []
    if not bool(row.get("finite_reasonable")):
        failures.append("ngspice_nonfinite_or_unreasonable")
    pre = row.get(f"{prefix}_pre_response_abs_v", "")
    settle = row.get(f"{prefix}_settling_abs_v", "")
    over = row.get(f"{prefix}_overshoot_pct_swing", "")
    under = row.get(f"{prefix}_undershoot_pct_swing", "")
    try:
        low = float(row.get(f"{prefix}_low_v", 0.0))
        active = float(row.get(f"{prefix}_active_v", 0.0))
        swing = abs(active - low)
        if pre != "" and math.isfinite(float(pre)) and float(pre) > args.pre_response_fail_v:
            failures.append(f"{prefix}_pre_response")
        if settle != "" and math.isfinite(float(settle)) and float(settle) > args.settling_fail_v:
            failures.append(f"{prefix}_settling")
        if swing >= args.min_smoke_swing_v and over != "" and math.isfinite(float(over)) and float(over) > args.overshoot_fail_pct:
            failures.append(f"{prefix}_overshoot")
        if swing >= args.min_smoke_swing_v and under != "" and math.isfinite(float(under)) and float(under) > args.overshoot_fail_pct:
            failures.append(f"{prefix}_undershoot")
    except Exception:
        failures.append(f"{prefix}_smoke_metric_parse")
    return failures


def smoke_prefix_gate_warnings(row: dict[str, object], args: argparse.Namespace, prefix: str) -> list[str]:
    warnings_out: list[str] = []
    if str(row.get(f"{prefix}_ringing_threshold_ambiguous")).lower() == "true":
        warnings_out.append(f"{prefix}_edge_ringing_threshold_ambiguous")
    try:
        low = float(row.get(f"{prefix}_low_v", 0.0))
        active = float(row.get(f"{prefix}_active_v", 0.0))
        swing = abs(active - low)
        if swing < args.min_smoke_swing_v:
            warnings_out.append(f"{prefix}_low_swing_metric_floor")
        pre_pct = row.get(f"{prefix}_pre_response_pct_swing", "")
        if pre_pct != "" and math.isfinite(float(pre_pct)) and float(pre_pct) > args.pre_response_warn_pct:
            warnings_out.append(f"{prefix}_pre_response_margin")
        settle_pct = row.get(f"{prefix}_settling_pct_swing", "")
        if settle_pct != "" and math.isfinite(float(settle_pct)) and float(settle_pct) > args.settling_warn_pct:
            warnings_out.append(f"{prefix}_settling_margin")
        over_pct = row.get(f"{prefix}_overshoot_pct_swing", "")
        if swing >= args.min_smoke_swing_v and over_pct != "" and math.isfinite(float(over_pct)) and float(over_pct) > args.overshoot_warn_pct:
            warnings_out.append(f"{prefix}_overshoot_margin")
        under_pct = row.get(f"{prefix}_undershoot_pct_swing", "")
        if swing >= args.min_smoke_swing_v and under_pct != "" and math.isfinite(float(under_pct)) and float(under_pct) > args.overshoot_warn_pct:
            warnings_out.append(f"{prefix}_undershoot_margin")
    except Exception:
        warnings_out.append(f"{prefix}_smoke_warning_parse")
    delay_reasons = [item for item in str(row.get("threshold_delay_confidence_reasons", "") or "").split(";") if item]
    if str(row.get("threshold_delay_confidence", "")) == "low" and any(item.startswith(f"{prefix}_") for item in delay_reasons):
        warnings_out.append(f"{prefix}_threshold_delay_confidence_low")
        try:
            shape_score = smoke_prefix_shape_score(row, prefix)
            if math.isfinite(shape_score) and shape_score <= max(args.pre_response_fail_v, args.settling_fail_v):
                warnings_out.append(f"{prefix}_voltage_shape_ok_threshold_delay_low")
        except Exception:
            warnings_out.append(f"{prefix}_threshold_delay_confidence_parse")
    return warnings_out


def write_hspice_deck(deck: Path, touchstone: Path, nports: int, case: SmokeCase) -> None:
    src, _ = source_lines(case, "p1")
    stop = case.stop_ns * 1e-9
    deck.parent.mkdir(parents=True, exist_ok=True)
    local_touchstone = deck.parent / f"input_channel.s{nports}p"
    if touchstone.resolve() != local_touchstone.resolve():
        shutil.copy2(touchstone, local_touchstone)
    tstone = local_touchstone.name
    if nports == 2:
        channel = ["Schannel  p1  p2  0  MNAME=ch_model", "Rterm  p2  0  50"]
        probes = ".probe tran V(p1) V(p2) V(src)"
    elif nports == 4:
        channel = [
            "Schannel  p1  p2  p3  p4  0  MNAME=ch_model",
            "Rnear_neg  p2  0  50",
            "Rterm_pos  p3  0  50",
            "Rterm_neg  p4  0  50",
        ]
        probes = ".probe tran V(p1) V(p2) V(p3) V(p4) V(src)"
    else:
        raise ValueError(nports)
    text = "\n".join(
        [
            f"* HSPICE native S-parameter audit: {case.name}",
            ".option post=2 probe accurate",
            ".temp 27",
            *src,
            *channel,
            ".MODEL ch_model S",
            f"+ TSTONEFILE='{tstone}'",
            "+ Z0=50",
            "+ RATIONAL_FUNC=1",
            "+ INTERPOLATION=HYBRID",
            "+ LOWPASS=1",
            "+ HIGHPASS=3",
            "+ PASSIVE=1",
            probes,
            f".tran 10p {fmt(stop)}",
            ".end",
            "",
        ]
    )
    deck.write_text(text, encoding="ascii")


def run_hspice_case(hspice: Path, touchstone: Path, nports: int, out_dir: Path, case: SmokeCase, timeout: int) -> dict[str, object]:
    deck = out_dir / f"{case.name}_hspice.sp"
    prefix = out_dir / f"{case.name}_hspice"
    write_hspice_deck(deck, touchstone, nports, case)
    deck_text = deck.read_text(encoding="ascii")
    signature_id, signature = reference_signature(
        deck_text,
        [touchstone],
        {
            "family": "sparam_native_s",
            "case": case.name,
            "nports": nports,
        },
    )
    h_cache = cache_dir("sparam_native_s", f"{safe_id(touchstone)}_{case.name}", signature_id)
    if restore_hspice_cache(h_cache, out_dir, prefix.name, deck_text):
        return {
            "case": case.name,
            "hspice_return_code": 0,
            "hspice_reference": "cache",
            "hspice_tr0": rel(prefix.with_suffix(".tr0")),
            "hspice_lis": rel(prefix.with_suffix(".lis")),
        }
    if prefix.with_suffix(".tr0").exists():
        save_hspice_cache(h_cache, out_dir, prefix.name, deck_text, signature)
        return {
            "case": case.name,
            "hspice_return_code": 0,
            "hspice_reference": "existing",
            "hspice_tr0": rel(prefix.with_suffix(".tr0")),
            "hspice_lis": rel(prefix.with_suffix(".lis")),
        }
    try:
        completed = subprocess.run(
            [str(hspice), "-i", deck.name, "-o", prefix.name],
            cwd=out_dir,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        rc = completed.returncode
    except Exception as exc:
        return {"case": case.name, "hspice_return_code": -999, "hspice_error": str(exc), "hspice_tr0": rel(prefix.with_suffix(".tr0"))}
    if rc == 0:
        save_hspice_cache(h_cache, out_dir, prefix.name, deck_text, signature)
    return {
        "case": case.name,
        "hspice_return_code": rc,
        "hspice_reference": "run",
        "hspice_tr0": rel(prefix.with_suffix(".tr0")),
        "hspice_lis": rel(prefix.with_suffix(".lis")),
    }


def common_grid_error(t_ref: np.ndarray, y_ref: np.ndarray, t_dut: np.ndarray, y_dut: np.ndarray) -> tuple[float, float]:
    start = max(float(t_ref[0]), float(t_dut[0]))
    stop = min(float(t_ref[-1]), float(t_dut[-1]))
    if stop <= start:
        return float("nan"), float("nan")
    n = min(5000, max(100, min(len(t_ref), len(t_dut))))
    grid = np.linspace(start, stop, n)
    ref_i = np.interp(grid, t_ref, y_ref)
    dut_i = np.interp(grid, t_dut, y_dut)
    diff = dut_i - ref_i
    return float(np.sqrt(np.mean(diff**2))), float(np.max(np.abs(diff)))


def common_grid_error_active(
    t_ref: np.ndarray,
    y_ref: np.ndarray,
    t_dut: np.ndarray,
    y_dut: np.ndarray,
    low: float,
    active: float,
) -> tuple[float, float]:
    start = max(float(t_ref[0]), float(t_dut[0]))
    stop = min(float(t_ref[-1]), float(t_dut[-1]))
    if stop <= start:
        return float("nan"), float("nan")
    n = min(5000, max(100, min(len(t_ref), len(t_dut))))
    grid = np.linspace(start, stop, n)
    ref_i = np.interp(grid, t_ref, y_ref)
    dut_i = np.interp(grid, t_dut, y_dut)
    swing = max(abs(active - low), 1e-12)
    mask = (np.abs(ref_i - low) >= 0.02 * swing) | (np.abs(dut_i - low) >= 0.02 * swing)
    if not np.any(mask):
        return float("nan"), float("nan")
    diff = dut_i[mask] - ref_i[mask]
    return float(np.sqrt(np.mean(diff**2))), float(np.max(np.abs(diff)))


def median_window(t: np.ndarray, y: np.ndarray, lo: float, hi: float) -> float:
    mask = (t >= lo) & (t <= hi)
    if not np.any(mask):
        return float(np.nanmedian(y))
    return float(np.nanmedian(y[mask]))


def compare_hspice_ngspice(h_tr0: Path, n_raw: Path, nports: int) -> dict[str, object]:
    row: dict[str, object] = {}
    try:
        h = parse_hspice_tr0(h_tr0)
        n = parse_ngspice_raw(n_raw)
        tx_sig = "v(p1)"
        rx_sig = "v(p2)" if nports == 2 else "v(p3)"
        for label, sig in (("tx", tx_sig), ("rx", rx_sig)):
            rmse, maxabs = common_grid_error(h["time"], h[sig], n["time"], n[sig])
            row[f"{label}_rmse_v"] = rmse
            row[f"{label}_maxabs_v"] = maxabs
        h_tx_low, h_tx_active, h_tx_threshold, h_tx_active_high = waveform_levels(h["time"], h[tx_sig])
        h_rx_low, h_rx_active, h_rx_threshold, h_rx_active_high = waveform_levels(h["time"], h[rx_sig])
        n_tx_low, n_tx_active, n_tx_threshold, n_tx_active_high = waveform_levels(n["time"], n[tx_sig])
        n_rx_low, n_rx_active, n_rx_threshold, n_rx_active_high = waveform_levels(n["time"], n[rx_sig])
        row["hspice_tx_low_v"] = h_tx_low
        row["hspice_tx_active_v"] = h_tx_active
        row["hspice_tx_threshold_v"] = h_tx_threshold
        row["hspice_rx_low_v"] = h_rx_low
        row["hspice_rx_active_v"] = h_rx_active
        row["hspice_rx_threshold_v"] = h_rx_threshold
        row["ngspice_tx_low_v"] = n_tx_low
        row["ngspice_tx_active_v"] = n_tx_active
        row["ngspice_tx_threshold_v"] = n_tx_threshold
        row["ngspice_rx_low_v"] = n_rx_low
        row["ngspice_rx_active_v"] = n_rx_active
        row["ngspice_rx_threshold_v"] = n_rx_threshold
        row["hspice_tx_swing_v"] = abs(h_tx_active - h_tx_low)
        row["hspice_rx_swing_v"] = abs(h_rx_active - h_rx_low)
        row["ngspice_tx_swing_v"] = abs(n_tx_active - n_tx_low)
        row["ngspice_rx_swing_v"] = abs(n_rx_active - n_rx_low)
        row["threshold_v"] = h_rx_threshold
        tx_active_rmse, tx_active_maxabs = common_grid_error_active(h["time"], h[tx_sig], n["time"], n[tx_sig], h_tx_low, h_tx_active)
        rx_active_rmse, rx_active_maxabs = common_grid_error_active(h["time"], h[rx_sig], n["time"], n[rx_sig], h_rx_low, h_rx_active)
        row["tx_active_rmse_v"] = tx_active_rmse
        row["tx_active_maxabs_v"] = tx_active_maxabs
        row["rx_active_rmse_v"] = rx_active_rmse
        row["rx_active_maxabs_v"] = rx_active_maxabs
        for prefix, data in (("hspice", h), ("ngspice", n)):
            t = data["time"]
            tx = data[tx_sig]
            rx = data[rx_sig]
            tx_rise, tx_fall = edge_crossings(t, tx, h_tx_threshold, h_tx_active_high)
            rx_rise, rx_fall = edge_crossings(t, rx, h_rx_threshold, h_rx_active_high)
            row[f"{prefix}_tx_rise_threshold_crossing_count"] = threshold_crossing_count(t, tx, h_tx_threshold, 0.5e-9, 2.5e-9)
            row[f"{prefix}_tx_fall_threshold_crossing_count"] = threshold_crossing_count(t, tx, h_tx_threshold, 8.5e-9, min(float(t[-1]), 10.8e-9))
            row[f"{prefix}_rx_rise_threshold_crossing_count"] = threshold_crossing_count(t, rx, h_rx_threshold, 0.5e-9, 2.5e-9)
            row[f"{prefix}_rx_fall_threshold_crossing_count"] = threshold_crossing_count(t, rx, h_rx_threshold, 8.5e-9, min(float(t[-1]), 10.8e-9))
            row[f"{prefix}_tx_rise50_ns"] = "" if tx_rise is None else tx_rise * 1e9
            row[f"{prefix}_rx_rise50_ns"] = "" if rx_rise is None else rx_rise * 1e9
            row[f"{prefix}_tx_fall50_ns"] = "" if tx_fall is None else tx_fall * 1e9
            row[f"{prefix}_rx_fall50_ns"] = "" if rx_fall is None else rx_fall * 1e9
            if tx_rise is not None and rx_rise is not None:
                row[f"{prefix}_rx_minus_tx_rise50_ps"] = (rx_rise - tx_rise) * 1e12
            if tx_fall is not None and rx_fall is not None:
                row[f"{prefix}_rx_minus_tx_fall50_ps"] = (rx_fall - tx_fall) * 1e12
        for key in ("rx_minus_tx_rise50_ps", "rx_minus_tx_fall50_ps"):
            hk = f"hspice_{key}"
            nk = f"ngspice_{key}"
            if hk in row and nk in row:
                row[f"{key}_delta_ps"] = float(row[nk]) - float(row[hk])
        row["correlation_status"] = "ok"
    except Exception as exc:
        row["correlation_status"] = "parse_error"
        row["correlation_error"] = str(exc)
    return row


def audit_delay_confidence(row: dict[str, object], args: argparse.Namespace) -> tuple[str, str]:
    threshold = float(getattr(args, "hspice_min_delay_confidence_swing_v", getattr(args, "min_delay_confidence_swing_v", 0.02)))
    reasons: list[str] = []
    for sim in ("hspice", "ngspice"):
        for prefix in ("tx", "rx"):
            try:
                swing = float(row.get(f"{sim}_{prefix}_swing_v", 0.0) or 0.0)
                if swing < threshold:
                    reasons.append(f"{sim}_{prefix}_low_swing")
            except Exception:
                reasons.append(f"{sim}_{prefix}_swing_parse")
            for edge in ("rise", "fall"):
                count = row.get(f"{sim}_{prefix}_{edge}_threshold_crossing_count", "")
                try:
                    if count != "" and int(count) > 1:
                        reasons.append(f"{sim}_{prefix}_{edge}_threshold_ambiguous")
                except Exception:
                    reasons.append(f"{sim}_{prefix}_{edge}_threshold_parse")
            if row.get(f"{sim}_{prefix}_rise50_ns", "") == "" or row.get(f"{sim}_{prefix}_fall50_ns", "") == "":
                reasons.append(f"{sim}_{prefix}_missing_50pct_crossing")
    if reasons:
        return "low", ";".join(sorted(set(reasons)))
    return "high", ""


def classify_hspice_row(row: dict[str, object], args: argparse.Namespace) -> tuple[str, str]:
    if row.get("correlation_status") != "ok":
        return "ERROR", str(row.get("correlation_error") or row.get("correlation_status") or "correlation_error")
    failures: list[str] = []
    delay_failures: list[str] = []
    try:
        if float(row.get("rx_active_rmse_v", float("inf"))) > args.hspice_rx_active_rmse_pass_v:
            failures.append("rx_active_rmse")
        if float(row.get("rx_active_maxabs_v", float("inf"))) > args.hspice_rx_active_maxabs_pass_v:
            failures.append("rx_active_maxabs")
        if float(row.get("tx_active_rmse_v", 0.0)) > args.hspice_tx_active_rmse_pass_v:
            failures.append("tx_active_rmse")
        delay_confidence, delay_reasons = audit_delay_confidence(row, args)
        row["hspice_threshold_delay_confidence"] = delay_confidence
        row["hspice_threshold_delay_confidence_reasons"] = delay_reasons
        for key in ("rx_minus_tx_rise50_ps_delta_ps", "rx_minus_tx_fall50_ps_delta_ps"):
            value = row.get(key, "")
            if delay_confidence == "high" and value != "" and abs(float(value)) > args.hspice_delay_pass_ps:
                delay_failures.append(key.replace("_ps_delta_ps", ""))
    except Exception as exc:
        return "ERROR", f"metric_parse_error:{exc}"
    if failures or delay_failures:
        return "FAIL", ";".join(failures + delay_failures)
    if row.get("hspice_threshold_delay_confidence") == "low":
        return "WARN", "voltage_pass_threshold_delay_confidence_low"
    return "PASS", "thresholds passed"


def classify_hspice_rx_shape(row: dict[str, object], args: argparse.Namespace) -> tuple[str, str]:
    try:
        failures: list[str] = []
        if float(row.get("rx_active_rmse_v", float("inf"))) > args.hspice_rx_active_rmse_pass_v:
            failures.append("rx_active_rmse")
        if float(row.get("rx_active_maxabs_v", float("inf"))) > args.hspice_rx_active_maxabs_pass_v:
            failures.append("rx_active_maxabs")
    except Exception as exc:
        return "ERROR", f"metric_parse_error:{exc}"
    if failures:
        return "FAIL", ";".join(failures)
    return "PASS", "rx shape thresholds passed"


def classify_hspice_rx_timing(row: dict[str, object], args: argparse.Namespace) -> tuple[str, str]:
    try:
        delay_confidence, delay_reasons = audit_delay_confidence(row, args)
        row["hspice_threshold_delay_confidence"] = delay_confidence
        row["hspice_threshold_delay_confidence_reasons"] = delay_reasons
        failures: list[str] = []
        for key in ("rx_minus_tx_rise50_ps_delta_ps", "rx_minus_tx_fall50_ps_delta_ps"):
            value = row.get(key, "")
            if delay_confidence == "high" and value != "" and abs(float(value)) > args.hspice_delay_pass_ps:
                failures.append(key.replace("_ps_delta_ps", ""))
    except Exception as exc:
        return "ERROR", f"metric_parse_error:{exc}"
    if failures:
        return "FAIL", ";".join(failures)
    if delay_confidence == "low":
        return "WARN", "rx_timing_threshold_confidence_low"
    return "PASS", "rx timing thresholds passed"


def classify_hspice_row_view(row: dict[str, object], args: argparse.Namespace, view: str) -> tuple[str, str]:
    if row.get("correlation_status") != "ok":
        return "ERROR", str(row.get("correlation_error") or row.get("correlation_status") or "correlation_error")
    try:
        delay_confidence, delay_reasons = audit_delay_confidence(row, args)
        row["hspice_threshold_delay_confidence"] = delay_confidence
        row["hspice_threshold_delay_confidence_reasons"] = delay_reasons
        if view == "rx":
            shape_class, shape_reason = classify_hspice_rx_shape(row, args)
            timing_class, timing_reason = classify_hspice_rx_timing(row, args)
            row["rx_shape_hspice_audit_class"] = shape_class
            row["rx_shape_hspice_audit_reason"] = shape_reason
            row["rx_timing_hspice_audit_class"] = timing_class
            row["rx_timing_hspice_audit_reason"] = timing_reason
            if shape_class == "ERROR" or timing_class == "ERROR":
                return "ERROR", ";".join(reason for klass, reason in ((shape_class, shape_reason), (timing_class, timing_reason)) if klass == "ERROR")
            if shape_class == "FAIL" or timing_class == "FAIL":
                return "FAIL", ";".join(reason for klass, reason in ((shape_class, shape_reason), (timing_class, timing_reason)) if klass == "FAIL")
            if shape_class == "WARN" or timing_class == "WARN":
                return "WARN", ";".join(reason for klass, reason in ((shape_class, shape_reason), (timing_class, timing_reason)) if klass == "WARN")
            return "PASS", "rx shape and timing thresholds passed"
        if view == "reflection":
            failures = []
            if float(row.get("tx_active_rmse_v", float("inf"))) > args.hspice_tx_active_rmse_pass_v:
                failures.append("tx_active_rmse")
            if failures:
                return "FAIL", ";".join(failures)
            return "PASS", "reflection/TX thresholds passed"
    except Exception as exc:
        return "ERROR", f"metric_parse_error:{exc}"
    return classify_hspice_row(row, args)


def calibration_summary_rows(ranking: list[dict[str, str]], corr: list[dict[str, object]]) -> list[dict[str, object]]:
    independent_by_channel = {}
    for row in ranking:
        independent_by_channel[row.get("channel_id", "")] = {
            "class": row.get("independent_trust_class", "FAIL") or "FAIL",
            "validation_split": row.get("validation_split", "") or "unsplit",
            "source_family": row.get("source_family", "") or "unknown",
        }
    cells: dict[tuple[str, str, str], int] = {}
    for row in corr:
        info = independent_by_channel.get(
            str(row.get("channel_id", "")),
            {"class": "FAIL", "validation_split": str(row.get("validation_split", "") or "unsplit")},
        )
        independent = str(info.get("class", "FAIL") or "FAIL")
        split = str(row.get("validation_split", "") or info.get("validation_split", "") or "unsplit")
        audited = str(row.get("hspice_audit_class", "ERROR") or "ERROR")
        cells[("all", independent, audited)] = cells.get(("all", independent, audited), 0) + 1
        cells[(split, independent, audited)] = cells.get((split, independent, audited), 0) + 1

    rows: list[dict[str, object]] = []
    splits = ["all"] + sorted({split for split, _, _ in cells if split != "all"})
    for split in splits:
        for independent in ("PASS", "WARN", "FAIL"):
            total = sum(count for (scope, klass, _), count in cells.items() if scope == split and klass == independent)
            pass_count = cells.get((split, independent, "PASS"), 0)
            warn_count = cells.get((split, independent, "WARN"), 0)
            fail_count = cells.get((split, independent, "FAIL"), 0)
            error_count = cells.get((split, independent, "ERROR"), 0)
            rows.append(
                {
                    "validation_split": split,
                    "independent_class": independent,
                    "hspice_pass": pass_count,
                    "hspice_warn": warn_count,
                    "hspice_fail": fail_count,
                    "hspice_error": error_count,
                    "total": total,
                    "false_pass_rate": (warn_count + fail_count + error_count) / total if independent == "PASS" and total else "",
                }
            )
    return rows


def view_calibration_summary_rows(ranking: list[dict[str, str]], corr: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    view_defs = [
        ("rx_voltage_shape", "rx_voltage_shape_class", "rx_shape_hspice_audit_class"),
        ("rx_timing", "rx_timing_class", "rx_timing_hspice_audit_class"),
        ("rx", "rx_trust_class", "rx_hspice_audit_class"),
        ("reflection", "reflection_trust_class", "reflection_hspice_audit_class"),
        ("full_model", "full_model_trust_class", "full_model_hspice_audit_class"),
    ]
    for view, independent_key, audit_key in view_defs:
        independent_by_channel = {
            str(row.get("channel_id", "")): {
                "class": row.get(independent_key, "FAIL") or "FAIL",
                "validation_split": row.get("validation_split", "") or "unsplit",
            }
            for row in ranking
        }
        cells: dict[tuple[str, str, str], int] = {}
        for row in corr:
            info = independent_by_channel.get(
                str(row.get("channel_id", "")),
                {"class": "FAIL", "validation_split": str(row.get("validation_split", "") or "unsplit")},
            )
            independent = str(info.get("class", "FAIL") or "FAIL")
            split = str(row.get("validation_split", "") or info.get("validation_split", "") or "unsplit")
            audited = str(row.get(audit_key, row.get("hspice_audit_class", "ERROR")) or "ERROR")
            cells[("all", independent, audited)] = cells.get(("all", independent, audited), 0) + 1
            cells[(split, independent, audited)] = cells.get((split, independent, audited), 0) + 1
        splits = ["all"] + sorted({split for split, _, _ in cells if split != "all"})
        for split in splits:
            for independent in ("PASS", "WARN", "FAIL"):
                total = sum(count for (scope, klass, _), count in cells.items() if scope == split and klass == independent)
                pass_count = cells.get((split, independent, "PASS"), 0)
                warn_count = cells.get((split, independent, "WARN"), 0)
                fail_count = cells.get((split, independent, "FAIL"), 0)
                error_count = cells.get((split, independent, "ERROR"), 0)
                rows.append(
                    {
                        "view": view,
                        "validation_split": split,
                        "independent_class": independent,
                        "hspice_pass": pass_count,
                        "hspice_warn": warn_count,
                        "hspice_fail": fail_count,
                        "hspice_error": error_count,
                        "total": total,
                        "false_pass_rate": (warn_count + fail_count + error_count) / total if independent == "PASS" and total else "",
                    }
                )
    return rows


def view_trust_summary_rows(ranking: list[dict[str, object]], corr: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    view_defs = [
        ("rx_voltage_shape", "rx_voltage_shape_class", "rx_ready_status", "rx_selected_candidate", "rx_shape_hspice_audit_class"),
        ("rx_timing", "rx_timing_class", "rx_ready_status", "rx_selected_candidate", "rx_timing_hspice_audit_class"),
        ("rx", "rx_trust_class", "rx_ready_status", "rx_selected_candidate", "rx_hspice_audit_class"),
        ("reflection", "reflection_trust_class", "reflection_ready_status", "reflection_selected_candidate", "reflection_hspice_audit_class"),
        ("full_model", "full_model_trust_class", "full_model_ready_status", "full_selected_candidate", "full_model_hspice_audit_class"),
    ]
    for view, class_key, ready_key, selected_key, audit_key in view_defs:
        all_rows = list(ranking)
        selected_rows = [row for row in ranking if row.get("status") == "selected"]
        audit_rows = [row for row in corr if row.get(audit_key) or row.get("hspice_audit_class")]
        rows.append(
            {
                "view": view,
                "ready": sum(1 for row in all_rows if str(row.get(class_key, "")) == "PASS"),
                "warn": sum(1 for row in all_rows if str(row.get(class_key, "")) == "WARN"),
                "fail": sum(1 for row in all_rows if str(row.get(class_key, "")) == "FAIL"),
                "selected_models": sum(1 for row in selected_rows if row.get(selected_key)),
                "ready_label_count": sum(1 for row in all_rows if str(row.get(ready_key, "")).endswith("_READY")),
                "hspice_pass": sum(1 for row in audit_rows if str(row.get(audit_key, row.get("hspice_audit_class", ""))) == "PASS"),
                "hspice_warn": sum(1 for row in audit_rows if str(row.get(audit_key, row.get("hspice_audit_class", ""))) == "WARN"),
                "hspice_fail": sum(1 for row in audit_rows if str(row.get(audit_key, row.get("hspice_audit_class", ""))) == "FAIL"),
                "hspice_error": sum(1 for row in audit_rows if str(row.get(audit_key, row.get("hspice_audit_class", ""))) == "ERROR"),
            }
        )
    return rows


def candidate_family_summary_rows(metrics: list[dict[str, object]], ranking: list[dict[str, object]], corr: list[dict[str, object]]) -> list[dict[str, object]]:
    selected_family_by_channel = {
        str(row.get("channel_id", "")): str(row.get("selected_candidate_family", "") or "none")
        for row in ranking
    }
    rows: list[dict[str, object]] = []
    families = sorted(
        {
            str(row.get("candidate_family", "") or "unknown")
            for row in metrics
        }
        | {
            str(row.get("selected_candidate_family", "") or "none")
            for row in ranking
            if row.get("status") == "selected"
        }
    )
    for family in families:
        metric_rows = [row for row in metrics if str(row.get("candidate_family", "") or "unknown") == family]
        selected = [row for row in ranking if str(row.get("selected_candidate_family", "") or "none") == family and row.get("status") == "selected"]
        audit_rows = [row for row in corr if selected_family_by_channel.get(str(row.get("channel_id", "")), "none") == family]
        rows.append(
            {
                "candidate_family": family,
                "candidate_rows": len(metric_rows),
                "candidate_pass": sum(1 for row in metric_rows if row.get("trust_class") == "PASS"),
                "candidate_warn": sum(1 for row in metric_rows if row.get("trust_class") == "WARN"),
                "candidate_fail": sum(1 for row in metric_rows if row.get("trust_class") == "FAIL"),
                "selected_channels": len(selected),
                "selected_pass": sum(1 for row in selected if row.get("independent_trust_class") == "PASS"),
                "selected_warn": sum(1 for row in selected if row.get("independent_trust_class") == "WARN"),
                "selected_fail": sum(1 for row in selected if row.get("independent_trust_class") == "FAIL"),
                "hspice_pass": sum(1 for row in audit_rows if row.get("hspice_audit_class") == "PASS"),
                "hspice_warn": sum(1 for row in audit_rows if row.get("hspice_audit_class") == "WARN"),
                "hspice_fail": sum(1 for row in audit_rows if row.get("hspice_audit_class") == "FAIL"),
                "hspice_error": sum(1 for row in audit_rows if row.get("hspice_audit_class") == "ERROR"),
            }
        )
    return rows


def source_family_summary_rows(ranking: list[dict[str, object]], corr: list[dict[str, object]]) -> list[dict[str, object]]:
    source_by_channel = {
        str(row.get("channel_id", "")): str(row.get("source_family", "") or "unknown")
        for row in ranking
    }
    rows: list[dict[str, object]] = []
    families = sorted(set(source_by_channel.values()))
    for family in families:
        selected = [row for row in ranking if str(row.get("source_family", "") or "unknown") == family and row.get("status") == "selected"]
        failed = [row for row in ranking if str(row.get("source_family", "") or "unknown") == family and row.get("status") != "selected"]
        audit_rows = [row for row in corr if source_by_channel.get(str(row.get("channel_id", "")), "unknown") == family]
        rows.append(
            {
                "source_family": family,
                "selected_channels": len(selected),
                "failed_channels": len(failed),
                "independent_pass": sum(1 for row in selected if row.get("independent_trust_class") == "PASS"),
                "independent_warn": sum(1 for row in selected if row.get("independent_trust_class") == "WARN"),
                "independent_fail": sum(1 for row in selected if row.get("independent_trust_class") == "FAIL"),
                "hspice_pass": sum(1 for row in audit_rows if row.get("hspice_audit_class") == "PASS"),
                "hspice_warn": sum(1 for row in audit_rows if row.get("hspice_audit_class") == "WARN"),
                "hspice_fail": sum(1 for row in audit_rows if row.get("hspice_audit_class") == "FAIL"),
                "hspice_error": sum(1 for row in audit_rows if row.get("hspice_audit_class") == "ERROR"),
            }
        )
    return rows


def warning_audit_summary_rows(ranking: list[dict[str, object]], corr: list[dict[str, object]]) -> list[dict[str, object]]:
    warnings_by_channel: dict[str, list[str]] = {}
    for row in ranking:
        if row.get("status") != "selected":
            continue
        channel_id = str(row.get("channel_id", ""))
        reasons = [item for item in str(row.get("independent_warn_reasons", "") or "").split(";") if item]
        warnings_by_channel[channel_id] = reasons or ["NO_WARNING"]
    rows_by_warning: dict[str, dict[str, object]] = {}
    for channel_id, warnings_list in warnings_by_channel.items():
        for warning in warnings_list:
            rows_by_warning.setdefault(
                warning,
                {
                    "warning_reason": warning,
                    "selected_channels": 0,
                    "audit_rows": 0,
                    "hspice_pass": 0,
                    "hspice_warn": 0,
                    "hspice_fail": 0,
                    "hspice_error": 0,
                },
            )
            rows_by_warning[warning]["selected_channels"] = int(rows_by_warning[warning]["selected_channels"]) + 1
    for row in corr:
        channel_id = str(row.get("channel_id", ""))
        for warning in warnings_by_channel.get(channel_id, ["NO_WARNING"]):
            out = rows_by_warning.setdefault(
                warning,
                {
                    "warning_reason": warning,
                    "selected_channels": 0,
                    "audit_rows": 0,
                    "hspice_pass": 0,
                    "hspice_warn": 0,
                    "hspice_fail": 0,
                    "hspice_error": 0,
                },
            )
            out["audit_rows"] = int(out["audit_rows"]) + 1
            klass = str(row.get("hspice_audit_class", "ERROR") or "ERROR").lower()
            key = f"hspice_{klass if klass in ('pass', 'warn', 'fail', 'error') else 'error'}"
            out[key] = int(out[key]) + 1
    return sorted(rows_by_warning.values(), key=lambda row: (str(row["warning_reason"]) == "NO_WARNING", str(row["warning_reason"])))


def write_derived_summary_csvs(study_dir: Path, metrics: list[dict[str, object]], ranking: list[dict[str, object]], corr: list[dict[str, object]]) -> None:
    write_csv(study_dir / "candidate_family_summary.csv", candidate_family_summary_rows(metrics, ranking, corr))
    write_csv(study_dir / "source_family_summary.csv", source_family_summary_rows(ranking, corr))
    write_csv(study_dir / "warning_audit_summary.csv", warning_audit_summary_rows(ranking, corr))
    write_csv(study_dir / "view_trust_summary.csv", view_trust_summary_rows(ranking, corr))
    if corr:
        write_csv(study_dir / "view_calibration_summary.csv", view_calibration_summary_rows(ranking, corr))


def plot_frequency_fit(nw, vf, path: Path, title: str) -> None:
    freqs = np.asarray(nw.frequency.f, dtype=float)
    fitted = fitted_s_matrices(vf, freqs)
    nports = nw.nports
    pairs = [(i, j) for i in range(nports) for j in range(nports)]
    if nports == 4:
        pairs = [(0, 0), (2, 0), (1, 1), (3, 1), (2, 2), (3, 3)]
    cols = 2
    rows = math.ceil(len(pairs) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(11, max(4, 2.5 * rows)), constrained_layout=True)
    axes_arr = np.asarray(axes).reshape(-1)
    for ax, (i, j) in zip(axes_arr, pairs):
        ax.plot(freqs * 1e-9, 20 * np.log10(np.maximum(np.abs(nw.s[:, i, j]), 1e-30)), label="Touchstone", linewidth=1.6)
        ax.plot(freqs * 1e-9, 20 * np.log10(np.maximum(np.abs(fitted[:, i, j]), 1e-30)), "--", label="fit", linewidth=1.4)
        ax.set_title(f"S{i + 1}{j + 1}", loc="left")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Magnitude (dB)")
        ax.grid(True, color="#d7dde6")
    for ax in axes_arr[len(pairs) :]:
        ax.axis("off")
    axes_arr[0].legend(frameon=False)
    fig.suptitle(title, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_singular(vf, high_fmax: float, path: Path, title: str) -> None:
    freqs = np.linspace(0, high_fmax, 1001)
    mats = fitted_s_matrices(vf, freqs)
    sv = np.linalg.svd(mats, compute_uv=False)[:, 0]
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    ax.plot(freqs * 1e-9, sv, linewidth=1.8)
    ax.axhline(1.0, color="#555555", linestyle=":", linewidth=1)
    ax.axhline(1.05, color="#c43c2f", linestyle="--", linewidth=1)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Max singular value")
    ax.grid(True, color="#d7dde6")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_transient_overlay(h_tr0: Path, n_raw: Path, nports: int, path: Path, title: str) -> None:
    h = parse_hspice_tr0(h_tr0)
    n = parse_ngspice_raw(n_raw)
    rx_sig = "v(p2)" if nports == 2 else "v(p3)"
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, constrained_layout=True)
    for ax, sig, label in ((axes[0], "v(p1)", "Tx/Input Port"), (axes[1], rx_sig, "Rx/Output Port")):
        ax.plot(h["time"] * 1e9, h[sig], label="HSPICE native S", linewidth=1.8)
        ax.plot(n["time"] * 1e9, n[sig], "--", label="ngspice converted", linewidth=1.6)
        ax.set_title(label, loc="left", fontweight="bold")
        ax.set_ylabel("Voltage (V)")
        ax.grid(True, color="#d7dde6")
        ax.legend(frameon=False)
    axes[1].set_xlabel("Time (ns)")
    fig.suptitle(title, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def voltage_axis_limits(values: list[np.ndarray], min_tick_v: float = 0.001) -> tuple[float, float, float]:
    chunks = [np.asarray(v, dtype=float)[np.isfinite(v)] for v in values if len(v)]
    if not chunks:
        return -min_tick_v, min_tick_v, min_tick_v
    finite_values = np.concatenate(chunks)
    if finite_values.size == 0:
        return -min_tick_v, min_tick_v, min_tick_v
    vmin = float(np.nanmin(finite_values))
    vmax = float(np.nanmax(finite_values))
    span = max(vmax - vmin, min_tick_v)
    padding = max(0.08 * span, min_tick_v)
    lo = math.floor((vmin - padding) / min_tick_v) * min_tick_v
    hi = math.ceil((vmax + padding) / min_tick_v) * min_tick_v
    tick = max(min_tick_v, math.ceil(((hi - lo) / 8.0) / min_tick_v) * min_tick_v)
    return lo, hi, tick


def plot_transient_side_overlay(
    h_tr0: Path,
    n_raw: Path,
    nports: int,
    path: Path,
    title: str,
    side: str,
    dut_label: str = "ngspice converted",
) -> None:
    h = parse_hspice_tr0(h_tr0)
    n = parse_ngspice_raw(n_raw)
    if side == "rx":
        sig = "v(p2)" if nports == 2 else "v(p3)"
        side_title = "RX / Output Port"
    elif side == "tx":
        sig = "v(p1)"
        side_title = "TX / Input Port"
    else:
        raise ValueError(side)
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    ax.plot(h["time"] * 1e9, h[sig], label="HSPICE native S", linewidth=1.9)
    ax.plot(n["time"] * 1e9, n[sig], "--", label=dut_label, linewidth=1.6)
    lo, hi, tick = voltage_axis_limits([h[sig], n[sig]], 0.001)
    ax.set_ylim(lo, hi)
    ax.yaxis.set_major_locator(MultipleLocator(tick))
    ax.set_title(f"{title} - {side_title}", loc="left", fontweight="bold")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, color="#d7dde6")
    ax.legend(frameon=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def write_audit_overlay_pdfs(study_dir: Path, corr: list[dict[str, object]]) -> None:
    from matplotlib.backends.backend_pdf import PdfPages

    out_dir = study_dir / "audit_overlay_groups"
    out_dir.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, object]] = []
    groups: dict[str, list[dict[str, object]]] = {}
    for row in corr:
        plot_text = str(row.get("overlay_plot", "") or "")
        if not plot_text:
            continue
        plot_path = Path(plot_text)
        if not plot_path.is_absolute():
            plot_path = ROOT / plot_path
        if not plot_path.exists():
            continue
        klass = str(row.get("hspice_audit_class", "ERROR") or "ERROR")
        groups.setdefault(klass, []).append(row)
        index_rows.append(
            {
                "hspice_audit_class": klass,
                "channel_id": row.get("channel_id", ""),
                "case": row.get("case", ""),
                "overlay_plot": rel(plot_path),
                "hspice_audit_reason": row.get("hspice_audit_reason", ""),
            }
        )
    for klass, rows in groups.items():
        pdf_path = out_dir / f"hspice_ngspice_overlays_{klass.lower()}.pdf"
        with PdfPages(pdf_path) as pdf:
            for row in rows:
                plot_path = Path(str(row.get("overlay_plot", "")))
                if not plot_path.is_absolute():
                    plot_path = ROOT / plot_path
                try:
                    img = plt.imread(plot_path)
                except Exception:
                    continue
                fig, ax = plt.subplots(figsize=(11, 8.5), constrained_layout=True)
                ax.imshow(img)
                ax.axis("off")
                ax.set_title(
                    f"{row.get('channel_id', '')} | {row.get('case', '')} | {klass}: {row.get('hspice_audit_reason', '')}",
                    loc="left",
                    fontsize=10,
                )
                pdf.savefig(fig)
                plt.close(fig)
    write_csv(study_dir / "audit_overlay_index.csv", index_rows)


def candidate_passes_math(
    row: dict[str, object],
    rms_threshold: float,
    mag_db_max_threshold: float,
    group_delay_rms_ps_threshold: float,
    max_low_freq_start_hz: float,
    min_frequency_points: int,
    max_sv_high_threshold: float,
) -> bool:
    return not math_gate_failures(
        row,
        rms_threshold,
        mag_db_max_threshold,
        group_delay_rms_ps_threshold,
        max_low_freq_start_hz,
        min_frequency_points,
        max_sv_high_threshold,
    )


def math_gate_failures(
    row: dict[str, object],
    rms_threshold: float,
    mag_db_max_threshold: float,
    group_delay_rms_ps_threshold: float,
    max_low_freq_start_hz: float,
    min_frequency_points: int,
    max_sv_high_threshold: float,
) -> list[str]:
    failures: list[str] = []
    try:
        if int(row.get("points") or 0) < min_frequency_points:
            failures.append("too_few_frequency_points")
        if float(row.get("f_min_hz") or float("inf")) > max_low_freq_start_hz:
            failures.append("low_frequency_coverage")
        if not (str(row.get("is_passive")) == "True" or row.get("is_passive") is True):
            failures.append("non_passive_fit")
        if float(row["max_sv_high"]) > max_sv_high_threshold:
            failures.append("dense_singular_value")
        if float(row["fit_complex_rms"]) > rms_threshold:
            failures.append("complex_rms_error")
        if float(row["fit_mag_db_max_above_m40"]) > mag_db_max_threshold:
            failures.append("magnitude_db_error")

        group_delay = float(row.get("fit_group_delay_rms_ps") or 0.0)
        if math.isfinite(group_delay) and group_delay > group_delay_rms_ps_threshold:
            failures.append("group_delay_error")
    except Exception:
        failures.append("metric_parse_error")
    return failures


def near_pass(row: dict[str, object]) -> bool:
    try:
        return float(row["max_sv_high"]) <= 1.2 or float(row["max_sv_input_samples"]) <= 1.05
    except Exception:
        return False


def finite_metric(row: dict[str, object], key: str, default: float = float("nan")) -> float:
    try:
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def quality_score(row: dict[str, object]) -> float:
    rms = float(row.get("fit_complex_rms") or 1e9)
    gd = row.get("fit_group_delay_rms_ps")
    gd_val = 0.0 if gd in ("", None) or not math.isfinite(float(gd)) else float(gd) * 1e-5
    shape = row.get("max_voltage_shape_score_v")
    shape_val = 0.0 if shape in ("", None) or not math.isfinite(float(shape)) else float(shape) * 0.1
    delay_low = float(row.get("threshold_delay_confidence_low_cases") or 0.0) * 1e-3
    return rms + gd_val + shape_val + delay_low + float(row.get("model_order") or 999) * 1e-4


def view_quality_score(row: dict[str, object], view: str) -> float:
    if view == "rx":
        rms = finite_metric(row, "rx_fit_complex_rms", finite_metric(row, "fit_complex_rms", 1e9))
        gd = finite_metric(row, "rx_fit_group_delay_rms_ps", finite_metric(row, "fit_group_delay_rms_ps", 0.0))
        shape = finite_metric(row, "max_rx_voltage_shape_score_v", finite_metric(row, "max_voltage_shape_score_v", 0.0))
        delay_low = finite_metric(row, "rx_threshold_delay_confidence_low_cases", 0.0) * 1e-3
        return rms + (0.0 if not math.isfinite(gd) else gd * 1e-5) + (0.0 if not math.isfinite(shape) else shape * 0.1) + delay_low + finite_metric(row, "model_order", 999.0) * 1e-4
    if view == "reflection":
        rms = finite_metric(row, "reflection_fit_complex_rms", 1e9)
        shape = finite_metric(row, "max_tx_voltage_shape_score_v", finite_metric(row, "max_voltage_shape_score_v", 0.0))
        delay_low = finite_metric(row, "tx_threshold_delay_confidence_low_cases", 0.0) * 1e-3
        return rms + (0.0 if not math.isfinite(shape) else shape * 0.1) + delay_low + finite_metric(row, "model_order", 999.0) * 1e-4
    return quality_score(row)


def warning_count(row: dict[str, object]) -> int:
    return len([item for item in str(row.get("trust_warn_reasons", "") or "").split(";") if item])


def view_warning_count(row: dict[str, object], view: str) -> int:
    key = {
        "rx": "rx_warn_reasons",
        "reflection": "reflection_warn_reasons",
        "full_model": "full_model_warn_reasons",
    }.get(view, "trust_warn_reasons")
    return len([item for item in str(row.get(key, "") or "").split(";") if item])


def view_math_gate_failures(row: dict[str, object], args: argparse.Namespace, view: str) -> list[str]:
    failures: list[str] = []
    if str(row.get("view_role", "")) == "analysis_only":
        return ["analysis_only_not_ngspice_model"]
    try:
        if int(row.get("points") or 0) < args.min_frequency_points:
            failures.append("too_few_frequency_points")
        if float(row.get("f_min_hz") or float("inf")) > args.max_low_freq_start_hz:
            failures.append("low_frequency_coverage")
        if finite_metric(row, "max_sv_high", float("inf")) > args.max_sv_high_threshold:
            failures.append("dense_singular_value")
    except Exception:
        failures.append("metric_parse_error")

    if view == "rx":
        if str(row.get("view_role", "")) == "reflection":
            failures.append("candidate_not_rx_view")
        rms = finite_metric(row, "rx_fit_complex_rms", finite_metric(row, "fit_complex_rms", float("inf")))
        mag = finite_metric(row, "rx_fit_mag_db_max_above_m40", finite_metric(row, "fit_mag_db_max_above_m40", 0.0))
        gd = finite_metric(row, "rx_fit_group_delay_rms_ps", finite_metric(row, "fit_group_delay_rms_ps", 0.0))
    elif view == "reflection":
        rms = finite_metric(row, "reflection_fit_complex_rms", float("inf"))
        mag = finite_metric(row, "reflection_fit_mag_db_max_above_m40", 0.0)
        gd = finite_metric(row, "reflection_fit_group_delay_rms_ps", 0.0)
    else:
        failures.extend([item for item in str(row.get("math_fail_reasons", "") or "").split(";") if item])
        if str(row.get("use_scope", "")) != "general_multiport":
            failures = [item for item in failures if item not in {"complex_rms_error", "magnitude_db_error", "group_delay_error"}]
        return sorted(set(failures))

    if math.isfinite(rms) and rms > args.rms_threshold:
        failures.append(f"{view}_complex_rms_error")
    if math.isfinite(mag) and mag > args.mag_db_max_threshold:
        failures.append(f"{view}_magnitude_db_error")
    if math.isfinite(gd) and gd > args.group_delay_rms_ps_threshold:
        failures.append(f"{view}_group_delay_error")
    return sorted(set(failures))


def view_candidate_warning_reasons(row: dict[str, object], smoke_rows: list[dict[str, object]], args: argparse.Namespace, view: str) -> list[str]:
    warnings_out: list[str] = []
    try:
        max_sv = finite_metric(row, "max_sv_high", float("nan"))
        if math.isfinite(max_sv) and max_sv > args.passivity_warn_sv:
            warnings_out.append("passivity_margin_low")
    except Exception:
        warnings_out.append("passivity_margin_parse")
    if view == "rx":
        for smoke in smoke_rows:
            warnings_out.extend(smoke_prefix_gate_warnings(smoke, args, "rx"))
        return sorted(set(warnings_out))
    if view == "reflection":
        if str(row.get("view_role", "")) == "rx_through":
            warnings_out.append("reflection_unmodeled_small_s11")
        for smoke in smoke_rows:
            warnings_out.extend(smoke_prefix_gate_warnings(smoke, args, "tx"))
        return sorted(set(warnings_out))
    if str(row.get("use_scope", "")) != "general_multiport":
        warnings_out.append("not_general_multiport_model")
    if int(row.get("ports") or 0) == 4 and str(row.get("candidate_family", "")).startswith("reduced"):
        warnings_out.append("reduced_4p_not_full_matrix")
    for smoke in smoke_rows:
        warnings_out.extend(smoke_gate_warnings(smoke, args))
    return sorted(set(warnings_out))


def rx_voltage_shape_math_failures(row: dict[str, object], args: argparse.Namespace) -> list[str]:
    failures = view_math_gate_failures(row, args, "rx")
    return [item for item in failures if item != "rx_group_delay_error"]


def classify_rx_voltage_shape(row: dict[str, object], smoke_rows: list[dict[str, object]], args: argparse.Namespace) -> tuple[str, str, str]:
    failures = rx_voltage_shape_math_failures(row, args)
    for smoke in smoke_rows:
        failures.extend(smoke_prefix_gate_failures(smoke, args, "rx"))
    failures = sorted(set(failures))
    if failures:
        return "FAIL", ";".join(failures), ""

    warnings_out: list[str] = []
    try:
        max_sv = finite_metric(row, "max_sv_high", float("nan"))
        if math.isfinite(max_sv) and max_sv > args.passivity_warn_sv:
            warnings_out.append("passivity_margin_low")
    except Exception:
        warnings_out.append("passivity_margin_parse")
    timing_warning_prefixes = (
        "rx_low_swing",
        "rx_threshold",
        "rx_voltage_shape_ok_threshold",
        "rx_edge_ringing_threshold",
    )
    for smoke in smoke_rows:
        for warning in smoke_prefix_gate_warnings(smoke, args, "rx"):
            if not warning.startswith(timing_warning_prefixes):
                warnings_out.append(warning)
    warnings_out = sorted(set(warnings_out))
    if warnings_out:
        return "WARN", "", ";".join(warnings_out)
    return "PASS", "", ""


def classify_rx_timing(row: dict[str, object], smoke_rows: list[dict[str, object]], args: argparse.Namespace) -> tuple[str, str, str]:
    failures: list[str] = []
    if str(row.get("view_role", "")) == "reflection":
        failures.append("candidate_not_rx_view")
    gd = finite_metric(row, "rx_fit_group_delay_rms_ps", finite_metric(row, "fit_group_delay_rms_ps", float("nan")))
    if math.isfinite(gd) and gd > args.group_delay_rms_ps_threshold:
        failures.append("rx_group_delay_error")
    if finite_metric(row, "max_sv_high", float("inf")) > args.max_sv_high_threshold:
        failures.append("dense_singular_value")
    failures = sorted(set(failures))
    if failures:
        return "FAIL", ";".join(failures), ""

    warnings_out: list[str] = []
    if not math.isfinite(gd):
        warnings_out.append("rx_group_delay_metric_missing")
    for smoke in smoke_rows:
        for warning in smoke_prefix_gate_warnings(smoke, args, "rx"):
            if (
                "threshold_delay_confidence" in warning
                or "low_swing" in warning
                or "threshold_ambiguous" in warning
                or "edge_ringing_threshold" in warning
            ):
                warnings_out.append(warning)
    warnings_out = sorted(set(warnings_out))
    if warnings_out:
        return "WARN", "", ";".join(warnings_out)
    return "PASS", "", ""


def combine_rx_classes(
    voltage_class: str,
    voltage_failures: str,
    voltage_warnings: str,
    timing_class: str,
    timing_failures: str,
    timing_warnings: str,
) -> tuple[str, str, str]:
    if voltage_class == "FAIL" or timing_class == "FAIL":
        failures = ";".join(item for item in (voltage_failures, timing_failures) if item)
        return "FAIL", failures, ""
    warnings_out = ";".join(item for item in (voltage_warnings, timing_warnings) if item)
    if voltage_class == "WARN" or timing_class == "WARN":
        return "WARN", "", warnings_out
    return "PASS", "", ""


def rx_ready_status_from_classes(voltage_class: object, timing_class: object, rx_class: object) -> str:
    if rx_class == "PASS" and voltage_class == "PASS" and timing_class == "PASS":
        return "RX_READY"
    if rx_class == "FAIL" or voltage_class == "FAIL" or timing_class == "FAIL":
        return "FAIL"
    if voltage_class == "PASS" and timing_class == "WARN":
        return "RX_VOLTAGE_OK_TIMING_AMBIGUOUS"
    if voltage_class == "WARN" and timing_class == "PASS":
        return "RX_WARN_VOLTAGE_MARGIN"
    return "WARN"


def append_reason(existing: object, reason: str) -> str:
    reasons = [item for item in str(existing or "").split(";") if item]
    reasons.append(reason)
    return ";".join(sorted(set(reasons)))


def apply_combined_candidate_gates(rows: list[dict[str, object]], args: argparse.Namespace) -> None:
    rx_pass = [
        row
        for row in rows
        if row.get("rx_trust_class") == "PASS"
        and str(row.get("view_role", "")) == "rx_through"
    ]
    reflection_pass = [
        row
        for row in rows
        if row.get("reflection_trust_class") == "PASS"
        and str(row.get("view_role", "")) == "reflection"
    ]
    best_rx_shape = min(
        (finite_metric(row, "max_rx_voltage_shape_score_v", finite_metric(row, "rx_independent_score", float("inf"))) for row in rx_pass),
        default=float("inf"),
    )
    for row in rows:
        if str(row.get("view_role", "")) != "combined":
            continue
        reasons: list[str] = []
        if not rx_pass:
            reasons.append("combined_requires_individual_rx_pass")
        if not reflection_pass:
            reasons.append("combined_requires_individual_reflection_pass")
        combined_shape = finite_metric(row, "max_rx_voltage_shape_score_v", finite_metric(row, "rx_independent_score", float("inf")))
        if math.isfinite(best_rx_shape) and math.isfinite(combined_shape):
            if combined_shape - best_rx_shape > args.combined_rx_shape_degradation_v:
                reasons.append("combined_rx_shape_degradation")
        if not reasons:
            row["combined_candidate_allowed"] = True
            row["combined_gate_reasons"] = ""
            continue
        reason_text = ";".join(sorted(set(reasons)))
        row["combined_candidate_allowed"] = False
        row["combined_gate_reasons"] = reason_text
        for prefix in ("rx", "reflection", "full_model"):
            row[f"{prefix}_trust_class"] = "FAIL"
            row[f"{prefix}_fail_reasons"] = append_reason(row.get(f"{prefix}_fail_reasons", ""), reason_text)
            row[f"{prefix}_warn_reasons"] = ""
        row["trust_class"] = "FAIL"
        row["trust_fail_reasons"] = append_reason(row.get("trust_fail_reasons", ""), reason_text)
        row["trust_warn_reasons"] = ""
        row["rx_ready_status_candidate"] = "FAIL"


def classify_view_candidate(row: dict[str, object], smoke_rows: list[dict[str, object]], args: argparse.Namespace, view: str) -> tuple[str, str, str]:
    if view == "rx":
        voltage_class, voltage_failures, voltage_warnings = classify_rx_voltage_shape(row, smoke_rows, args)
        timing_class, timing_failures, timing_warnings = classify_rx_timing(row, smoke_rows, args)
        return combine_rx_classes(voltage_class, voltage_failures, voltage_warnings, timing_class, timing_failures, timing_warnings)
    failures = view_math_gate_failures(row, args, view)
    if view == "reflection":
        for smoke in smoke_rows:
            failures.extend(smoke_prefix_gate_failures(smoke, args, "tx"))
    else:
        for smoke in smoke_rows:
            failures.extend(smoke_gate_failures(smoke, args))
    failures = sorted(set(failures))
    if failures:
        return "FAIL", ";".join(failures), ""
    warnings_out = view_candidate_warning_reasons(row, smoke_rows, args, view)
    if view == "full_model" and str(row.get("use_scope", "")) != "general_multiport":
        return "WARN", "", ";".join(warnings_out)
    if warnings_out:
        return "WARN", "", ";".join(warnings_out)
    return "PASS", "", ""


def candidate_warning_reasons(row: dict[str, object], smoke_rows: list[dict[str, object]], args: argparse.Namespace) -> list[str]:
    warnings_out: list[str] = []
    try:
        max_sv = float(row.get("max_sv_high") or float("nan"))
        if math.isfinite(max_sv) and max_sv > args.passivity_warn_sv:
            warnings_out.append("passivity_margin_low")
    except Exception:
        warnings_out.append("passivity_margin_parse")
    if int(row.get("ports") or 0) == 4 and str(row.get("candidate_family", "")).startswith("reduced"):
        warnings_out.append("reduced_4p_not_full_matrix")
    for smoke in smoke_rows:
        warnings_out.extend(smoke_gate_warnings(smoke, args))
    return sorted(set(warnings_out))


def classify_candidate(row: dict[str, object], smoke_rows: list[dict[str, object]], args: argparse.Namespace) -> tuple[str, str, str]:
    failures = list(filter(None, str(row.get("math_fail_reasons", "")).split(";")))
    for smoke in smoke_rows:
        failures.extend(smoke_gate_failures(smoke, args))
    failures = sorted(set(failures))
    if failures:
        return "FAIL", ";".join(failures), ""
    warnings_out = candidate_warning_reasons(row, smoke_rows, args)
    if warnings_out:
        return "WARN", "", ";".join(warnings_out)
    return "PASS", "", ""


def select_candidate(rows: list[dict[str, object]]) -> dict[str, object] | None:
    eligible = [row for row in rows if row.get("trust_class") in ("PASS", "WARN")]
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda row: (TRUST_CLASS_RANK[str(row["trust_class"])], warning_count(row), quality_score(row), int(row["model_order"])),
    )[0]


def select_candidate_for_view(rows: list[dict[str, object]], view: str, pass_only: bool = False) -> dict[str, object] | None:
    class_key = {
        "rx": "rx_trust_class",
        "reflection": "reflection_trust_class",
        "full_model": "full_model_trust_class",
    }[view]
    allowed = ("PASS",) if pass_only else ("PASS", "WARN")
    eligible = [row for row in rows if row.get(class_key) in allowed]
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda row: (
            TRUST_CLASS_RANK[str(row[class_key])],
            view_warning_count(row, view),
            view_quality_score(row, view),
            int(float(row.get("model_order") or 999)),
        ),
    )[0]


def best_candidate_attempt_for_view(rows: list[dict[str, object]], view: str) -> dict[str, object] | None:
    if not rows:
        return None
    class_key = {
        "rx": "rx_trust_class",
        "reflection": "reflection_trust_class",
        "full_model": "full_model_trust_class",
    }[view]
    return sorted(
        rows,
        key=lambda row: (
            TRUST_CLASS_RANK.get(str(row.get(class_key, "FAIL")), 3),
            view_warning_count(row, view),
            view_quality_score(row, view),
            int(float(row.get("model_order") or 999)),
        ),
    )[0]


def trust_ready_label(klass: object, ready_name: str) -> str:
    if klass == "PASS":
        return ready_name
    if klass == "WARN":
        return "WARN"
    return "FAIL"


def copy_selected_model(source_text: object, destination: Path) -> str:
    if not source_text:
        return ""
    source = Path(str(source_text))
    if not source.is_absolute():
        source = ROOT / source
    if not source.exists():
        return ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return rel(destination)


def csv_tokens(value: object, default: tuple[str, ...]) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return list(default)
    return [item.strip() for item in text.split(",") if item.strip()]


def bbs_preset_tokens(value: object) -> list[str]:
    presets = csv_tokens(value, ("clean",))
    unknown = [preset for preset in presets if preset not in BBS_PRESET_CONFIGS]
    if unknown:
        raise StudyError(f"Unknown BBS preset(s): {', '.join(unknown)}. Known presets: {', '.join(sorted(BBS_PRESET_CONFIGS))}")
    return presets


def write_bbs_preset_config(study_dir: Path, preset: str) -> tuple[Path, dict[str, object]]:
    if preset not in BBS_PRESET_CONFIGS:
        raise StudyError(f"Unknown BBS preset: {preset}")
    config = BBS_PRESET_CONFIGS[preset]
    config_dir = study_dir / "inputs" / "bbs_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / f"{preset}.json"
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path, config


def find_subckt_name(spice_file: Path) -> str:
    pattern = re.compile(r"^\s*\.subckt\s+(\S+)", re.IGNORECASE)
    for line in spice_file.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1)
    raise StudyError(f"No .subckt found in BBS SPICE file: {spice_file}")


def write_bbs_ngspice_wrapper(wrapper: Path, bbs_spice: Path, nports: int) -> str:
    subckt = find_subckt_name(bbs_spice)
    include = str(bbs_spice.resolve()).replace("\\", "/")
    if nports == 2:
        pins = "p1 p2"
        xline = f"Xbbs p1 p2 0 {subckt}"
    elif nports == 4:
        pins = "p1 p2 p3 p4"
        xline = f"Xbbs p1 p2 p3 p4 0 {subckt}"
    else:
        raise ValueError(nports)
    text = "\n".join(
        [
            "* ngspice wrapper for BroadbandSPICE General SPICE output",
            f".include '{include}'",
            f".subckt s_equivalent {pins}",
            xline,
            ".ends s_equivalent",
            "",
        ]
    )
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(text, encoding="ascii")
    return subckt


def count_bbs_model_order(spice_file: Path) -> int:
    try:
        text = spice_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 999
    cap_states = sum(1 for line in text.splitlines() if re.match(r"^\s*C\S+", line, re.IGNORECASE))
    laplace_terms = sum(1 for line in text.splitlines() if "LAPLACE" in line.upper())
    controlled_terms = sum(1 for line in text.splitlines() if re.match(r"^\s*[GFEH]\S+", line, re.IGNORECASE))
    return max(1, cap_states + laplace_terms, controlled_terms)


def interpolate_s_matrices(src_freqs: np.ndarray, src_s: np.ndarray, target_freqs: np.ndarray) -> np.ndarray:
    if len(src_freqs) == len(target_freqs) and np.allclose(src_freqs, target_freqs):
        return np.asarray(src_s, dtype=complex)
    out = np.empty((len(target_freqs), src_s.shape[1], src_s.shape[2]), dtype=complex)
    for i in range(src_s.shape[1]):
        for j in range(src_s.shape[2]):
            path = np.asarray(src_s[:, i, j], dtype=complex)
            out[:, i, j] = np.interp(target_freqs, src_freqs, path.real) + 1j * np.interp(target_freqs, src_freqs, path.imag)
    return out


def bbs_fitted_metrics(nw, fitted_touchstone: Path | None, high_fmax: float, dense_samples: int) -> dict[str, object]:
    if fitted_touchstone is None or not fitted_touchstone.exists():
        return {
            "fit_complex_rms": float("inf"),
            "fit_complex_max": float("inf"),
            "max_sv_input_samples": float("inf"),
            "max_sv_high": float("inf"),
            "math_fail_reasons_extra": "bbs_fitted_touchstone_missing",
        }
    skrf, _ = ensure_skrf()
    fitted = skrf.Network(str(fitted_touchstone))
    if fitted.nports != nw.nports:
        return {
            "fit_complex_rms": float("inf"),
            "fit_complex_max": float("inf"),
            "max_sv_input_samples": float("inf"),
            "max_sv_high": float("inf"),
            "math_fail_reasons_extra": "bbs_fitted_touchstone_port_mismatch",
        }
    freqs = np.asarray(nw.frequency.f, dtype=float)
    fitted_freqs = np.asarray(fitted.frequency.f, dtype=float)
    fitted_at_samples = interpolate_s_matrices(fitted_freqs, np.asarray(fitted.s), freqs)
    row = frequency_metrics(nw, fitted_at_samples)
    rx_out, rx_in = dominant_rx_path(nw.nports)
    refl_out, refl_in = input_reflection_path(nw.nports)
    row.update(
        prefixed_metrics(
            "rx",
            one_path_frequency_metrics(freqs, np.asarray(nw.s[:, rx_out, rx_in], dtype=complex), fitted_at_samples[:, rx_out, rx_in]),
        )
    )
    row.update(
        prefixed_metrics(
            "reflection",
            one_path_frequency_metrics(freqs, np.asarray(nw.s[:, refl_out, refl_in], dtype=complex), fitted_at_samples[:, refl_out, refl_in]),
        )
    )
    sample_sv, sample_idx = max_singular_from_mats(fitted_at_samples)
    row["max_sv_input_samples"] = sample_sv
    row["max_sv_input_sample_freq_hz"] = float(freqs[sample_idx])
    dense_freqs = np.linspace(float(freqs[0]), min(high_fmax, float(freqs[-1])), max(2, min(dense_samples, len(freqs) * 4)))
    dense_mats = interpolate_s_matrices(fitted_freqs, np.asarray(fitted.s), dense_freqs)
    dense_sv, dense_idx = max_singular_from_mats(dense_mats)
    row["max_sv_high"] = dense_sv
    row["max_sv_high_freq_hz"] = float(dense_freqs[dense_idx])
    row["sampled_is_passive"] = bool(sample_sv <= 1.0 + 1e-9)
    row["is_passive"] = bool(dense_sv <= 1.0 + 1e-9)
    row["math_fail_reasons_extra"] = ""
    return row


def bbs_mode_candidate(mode: str, circuit_type: str, preset: str) -> str:
    return f"bbs_{mode}_{circuit_type}_{preset}"


def build_bbs_candidate_rows(
    args: argparse.Namespace,
    channel_path: Path,
    nports: int,
    base: dict[str, object],
    nw,
    high_fmax: float,
    channel_id: str,
    channel_dir: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if not getattr(args, "enable_bbs", False):
        return [], []
    modes = csv_tokens(getattr(args, "bbs_modes", ""), ("passivity2",))
    circuit_types = csv_tokens(getattr(args, "bbs_circuit_types", ""), ("hspice", "gspice"))
    presets = bbs_preset_tokens(getattr(args, "bbs_preset_grid", "clean"))
    preset_configs = {
        preset: write_bbs_preset_config(args.study_dir.resolve(), preset)
        for preset in presets
    }
    candidate_rows: list[dict[str, object]] = []
    extraction_rows: list[dict[str, object]] = []
    for preset in presets:
        config_path, config_data = preset_configs[preset]
        config_arg = None if preset == "clean" else config_path
        config_json = json.dumps(config_data, sort_keys=True)
        for mode in modes:
            for circuit_type in circuit_types:
                candidate = bbs_mode_candidate(mode, circuit_type, preset)
                work_dir = channel_dir / "bbs" / preset / mode / circuit_type
                work_dir.mkdir(parents=True, exist_ok=True)
                local_touchstone = work_dir / channel_path.name
                shutil.copy2(channel_path, local_touchstone)
                manifest_path = work_dir / "bbs_manifest.csv"
                started = time.perf_counter()
                try:
                    rows = run_bbs_extraction(
                        local_touchstone,
                        mode=mode,
                        circuit_type=circuit_type,
                        max_iter=args.bbs_max_iter,
                        error=args.bbs_error,
                        config=config_arg,
                        exe=args.bbs_exe,
                        manifest=manifest_path,
                        timeout=args.bbs_timeout,
                    )
                    bbs_raw = rows[0] if rows else {"success": False, "return_code": -999, "stderr": "no BBS result row"}
                except Exception as exc:
                    bbs_raw = {
                        "input": str(local_touchstone),
                        "mode": mode,
                        "circuit_type": circuit_type,
                        "return_code": -999,
                        "success": False,
                        "result_dir": str(work_dir),
                        "circuit_file": "",
                        "fitted_touchstone": "",
                        "error_order_file": "",
                        "generated_files": "",
                        "stderr": str(exc),
                        "elapsed_s": time.perf_counter() - started,
                    }
                circuit_file = Path(str(bbs_raw.get("circuit_file", ""))) if bbs_raw.get("circuit_file") else None
                fitted_touchstone = Path(str(bbs_raw.get("fitted_touchstone", ""))) if bbs_raw.get("fitted_touchstone") else None
                error_order_file = Path(str(bbs_raw.get("error_order_file", ""))) if bbs_raw.get("error_order_file") else None
                selected_copy = ""
                if circuit_file and circuit_file.exists():
                    selected_copy = copy_selected_model(circuit_file, args.study_dir.resolve() / "selected_models" / "bbs" / channel_id / candidate / circuit_file.name)
                bbs_row: dict[str, object] = {
                    **base,
                    "candidate": candidate,
                    "bbs_mode": mode,
                    "bbs_circuit_type": circuit_type,
                    "bbs_preset": preset,
                    "bbs_config_file": rel(config_path),
                    "bbs_config_json": config_json,
                    "bbs_status": "ok" if bbs_raw.get("success") else "failed",
                    "bbs_return_code": bbs_raw.get("return_code", ""),
                    "bbs_timed_out": bbs_raw.get("timed_out", ""),
                    "bbs_elapsed_s": bbs_raw.get("elapsed_s", ""),
                    "bbs_exe": bbs_raw.get("exe", str(args.bbs_exe)),
                    "bbs_input_copy": rel(local_touchstone),
                    "bbs_manifest": rel(manifest_path) if manifest_path.exists() else "",
                    "bbs_result_dir": rel(Path(str(bbs_raw.get("result_dir", work_dir)))),
                    "bbs_circuit_file": rel(circuit_file) if circuit_file and circuit_file.exists() else "",
                    "bbs_selected_model_copy": selected_copy,
                    "bbs_fitted_touchstone": rel(fitted_touchstone) if fitted_touchstone and fitted_touchstone.exists() else "",
                    "bbs_error_order_file": rel(error_order_file) if error_order_file and error_order_file.exists() else "",
                    "bbs_generated_files": ";".join(rel(Path(p)) for p in str(bbs_raw.get("generated_files", "")).split(";") if p),
                    "bbs_stdout_tail": bbs_raw.get("stdout", ""),
                    "bbs_stderr_tail": bbs_raw.get("stderr", ""),
                }
                extraction_rows.append(bbs_row)
                if circuit_type != "gspice" or not circuit_file or not circuit_file.exists():
                    continue
                wrapper = channel_dir / "models" / candidate / f"{channel_id}_{candidate}_ngspice_wrapper.sp"
                try:
                    subckt_name = write_bbs_ngspice_wrapper(wrapper, circuit_file, nports)
                    bbs_row["bbs_subckt_name"] = subckt_name
                    bbs_row["ngspice_model_spice"] = rel(wrapper)
                    metrics = bbs_fitted_metrics(nw, fitted_touchstone, high_fmax, args.dense_samples)
                    model_order = count_bbs_model_order(circuit_file)
                    row = {
                        **base,
                        "candidate": candidate,
                        "candidate_family": "bbs_full_model",
                        "stage": "raw",
                        "fit_source": "broadband_spice",
                        "use_scope": "general_multiport",
                        "view_role": "full_model",
                        "bbs_mode": mode,
                        "bbs_circuit_type": circuit_type,
                        "bbs_preset": preset,
                        "bbs_config_file": rel(config_path),
                        "bbs_config_json": config_json,
                        "bbs_subckt_name": subckt_name,
                        "bbs_circuit_file": rel(circuit_file),
                        "bbs_selected_model_copy": selected_copy,
                        "bbs_fitted_touchstone": rel(fitted_touchstone) if fitted_touchstone and fitted_touchstone.exists() else "",
                        "bbs_error_order_file": rel(error_order_file) if error_order_file and error_order_file.exists() else "",
                        "spice_file": rel(wrapper),
                        "model_order": model_order,
                        "fit_warnings": "",
                    }
                    row.update(metrics)
                    row["math_pass"] = candidate_passes_math(
                        row,
                        args.rms_threshold,
                        args.mag_db_max_threshold,
                        args.group_delay_rms_ps_threshold,
                        args.max_low_freq_start_hz,
                        args.min_frequency_points,
                        args.max_sv_high_threshold,
                    ) and not row.get("math_fail_reasons_extra")
                    failures = math_gate_failures(
                        row,
                        args.rms_threshold,
                        args.mag_db_max_threshold,
                        args.group_delay_rms_ps_threshold,
                        args.max_low_freq_start_hz,
                        args.min_frequency_points,
                        args.max_sv_high_threshold,
                    )
                    if row.get("math_fail_reasons_extra"):
                        failures.append(str(row["math_fail_reasons_extra"]))
                    row["math_fail_reasons"] = ";".join(sorted(set(failures)))
                except Exception as exc:
                    row = {
                        **base,
                        "candidate": candidate,
                        "candidate_family": "bbs_full_model",
                        "stage": "raw",
                        "fit_source": "broadband_spice",
                        "use_scope": "general_multiport",
                        "view_role": "full_model",
                        "bbs_mode": mode,
                        "bbs_circuit_type": circuit_type,
                        "bbs_preset": preset,
                        "bbs_config_file": rel(config_path),
                        "bbs_config_json": config_json,
                        "bbs_circuit_file": rel(circuit_file),
                        "math_pass": False,
                        "math_fail_reasons": "bbs_wrapper_error",
                        "fit_error": str(exc),
                        "spice_file": "",
                        "model_order": 999,
                        "fit_complex_rms": float("inf"),
                        "max_sv_high": float("inf"),
                    }
                candidate_rows.append(row)
    return candidate_rows, extraction_rows


def run_channel(args: argparse.Namespace, manifest_row: dict[str, str], all_metrics: list[dict[str, object]], smoke_rows_all: list[dict[str, object]], ranking_rows: list[dict[str, object]], corr_rows: list[dict[str, object]], bbs_candidate_rows: list[dict[str, object]] | None = None) -> None:
    skrf, _ = ensure_skrf(args.skrf_target)
    channel_path = Path(manifest_row["path"]).resolve()
    channel_id = manifest_row["channel_id"]
    nports = int(manifest_row["ports"])
    channel_dir = args.study_dir.resolve() / "channels" / channel_id
    model_dir = channel_dir / "models"
    plot_dir = channel_dir / "plots"
    nw = skrf.Network(str(channel_path))
    freqs = np.asarray(nw.frequency.f, dtype=float)
    high_fmax = args.high_fmax or min(400e9, max(40 * float(freqs[-1]), 2 / (args.min_edge_ps * 1e-12)))

    sample_sv, sample_idx = max_singular_from_mats(np.asarray(nw.s))
    base = {
        "channel_id": channel_id,
        "source": manifest_row.get("source", ""),
        "source_family": manifest_row.get("source_family", ""),
        "validation_split": manifest_row.get("validation_split", ""),
        "channel_path": rel(channel_path),
        "relative_path": manifest_row.get("relative_path", rel(channel_path)),
        "ports": nports,
        "points": len(freqs),
        "f_min_hz": float(freqs[0]),
        "f_max_hz": float(freqs[-1]),
        "inventory_dominant_path": manifest_row.get("dominant_path", ""),
        "max_low_freq_start_hz": args.max_low_freq_start_hz,
        "low_freq_coverage_ok": bool(float(freqs[0]) <= args.max_low_freq_start_hz),
        "low_freq_coverage_ratio": float(freqs[0]) / args.max_low_freq_start_hz if args.max_low_freq_start_hz else float("inf"),
        "min_frequency_points": args.min_frequency_points,
        "frequency_point_count_ok": bool(len(freqs) >= args.min_frequency_points),
        "high_fmax_hz": high_fmax,
        "sampled_max_sv": sample_sv,
        "sampled_max_sv_freq_hz": float(freqs[sample_idx]),
        "sampled_is_passive": bool(nw.is_passive()),
        "qualification_profile": "fast_calibration" if args.fast_calibration_profile else "full",
        "combined_rx_shape_degradation_v": args.combined_rx_shape_degradation_v,
    }

    candidate_rows: list[dict[str, object]] = []
    fitted_by_name: dict[str, object] = {}
    for spec in candidate_specs_for_channel(args, nports):
        name = spec[0]
        try:
            if name in ANALYSIS_ONLY_CANDIDATES:
                candidate_rows.append(build_analysis_only_candidate(name, base))
                continue
            if name in REDUCED_CANDIDATES:
                candidate_rows.append(build_reduced_candidate(args, nw, name, base, channel_id, model_dir, plot_dir, high_fmax))
                continue
            vf, fit_warnings = fit_candidate(nw, spec)
            row = {
                **base,
                "candidate": name,
                "candidate_family": "full_vector_fit",
                "stage": "raw",
                "fit_source": "vector_fit_frequency_domain",
                "use_scope": "general_multiport",
                "view_role": "full_model",
                "fit_warnings": " | ".join(fit_warnings),
            }
            row.update(describe_candidate(nw, vf, high_fmax, args.dense_samples))
            sp_path = model_dir / name / f"{channel_id}_{name}.sp"
            write_spice_model(vf, sp_path)
            row["spice_file"] = rel(sp_path)
            row["math_pass"] = candidate_passes_math(
                row,
                args.rms_threshold,
                args.mag_db_max_threshold,
                args.group_delay_rms_ps_threshold,
                args.max_low_freq_start_hz,
                args.min_frequency_points,
                args.max_sv_high_threshold,
            )
            row["math_fail_reasons"] = ";".join(
                math_gate_failures(
                    row,
                    args.rms_threshold,
                    args.mag_db_max_threshold,
                    args.group_delay_rms_ps_threshold,
                    args.max_low_freq_start_hz,
                    args.min_frequency_points,
                    args.max_sv_high_threshold,
                )
            )
            candidate_rows.append(row)
            fitted_by_name[name] = vf

            if not args.skip_passivity_enforcement and not row["math_pass"] and near_pass(row):
                with warnings.catch_warnings(record=True) as records:
                    warnings.simplefilter("always")
                    vf.passivity_enforce(n_samples=args.enforce_samples, f_max=high_fmax, preserve_dc=True)
                enforced = {
                    **base,
                    "candidate": f"{name}_enforced",
                    "candidate_family": "full_vector_fit_enforced",
                    "stage": "passivity_enforced",
                    "fit_source": "vector_fit_frequency_domain",
                    "use_scope": "general_multiport",
                    "view_role": "full_model",
                    "fit_warnings": " | ".join(str(r.message) for r in records),
                }
                enforced.update(describe_candidate(nw, vf, high_fmax, args.dense_samples))
                enf_path = model_dir / f"{name}_enforced" / f"{channel_id}_{name}_enforced.sp"
                write_spice_model(vf, enf_path)
                enforced["spice_file"] = rel(enf_path)
                enforced["math_pass"] = candidate_passes_math(
                    enforced,
                    args.rms_threshold,
                    args.mag_db_max_threshold,
                    args.group_delay_rms_ps_threshold,
                    args.max_low_freq_start_hz,
                    args.min_frequency_points,
                    args.max_sv_high_threshold,
                )
                enforced["math_fail_reasons"] = ";".join(
                    math_gate_failures(
                        enforced,
                        args.rms_threshold,
                        args.mag_db_max_threshold,
                        args.group_delay_rms_ps_threshold,
                        args.max_low_freq_start_hz,
                        args.min_frequency_points,
                        args.max_sv_high_threshold,
                    )
                )
                candidate_rows.append(enforced)
                fitted_by_name[f"{name}_enforced"] = vf
        except Exception as exc:
            family = name if name in NAMED_NON_VECTOR_CANDIDATES else "full_vector_fit"
            candidate_rows.append({**base, "candidate": name, "candidate_family": family, "stage": "raw", "math_pass": False, "math_fail_reasons": "fit_error", "fit_error": str(exc)})

    bbs_rows, bbs_extractions = build_bbs_candidate_rows(args, channel_path, nports, base, nw, high_fmax, channel_id, channel_dir)
    candidate_rows.extend(bbs_rows)
    if bbs_candidate_rows is not None:
        bbs_candidate_rows.extend(bbs_extractions)

    bbs_smoke_top_n = int(getattr(args, "bbs_smoke_top_n", 4) or 0)
    bbs_smoke_candidates: set[str] = set()
    bbs_candidate_metric_rows = [
        row
        for row in candidate_rows
        if str(row.get("candidate_family", "")).startswith("bbs_")
        and row.get("spice_file")
    ]
    if bbs_candidate_metric_rows and bbs_smoke_top_n > 0:
        bbs_smoke_candidates = {
            str(row.get("candidate", ""))
            for row in sorted(
                bbs_candidate_metric_rows,
                key=lambda item: (
                    0 if bool(item.get("math_pass")) else 1,
                    len([part for part in str(item.get("math_fail_reasons", "") or "").split(";") if part]),
                    quality_score(item),
                    finite_metric(item, "model_order", 999.0),
                ),
            )[:bbs_smoke_top_n]
        }
    else:
        bbs_smoke_candidates = {str(row.get("candidate", "")) for row in bbs_candidate_metric_rows}

    for row in candidate_rows:
        row_smoke_rows: list[dict[str, object]] = []
        view_math_ok = any(
            not view_math_gate_failures(row, args, view)
            for view in ("rx", "reflection", "full_model")
        ) or not rx_voltage_shape_math_failures(row, args)
        spice_text = str(row.get("spice_file", "") or "")
        family = str(row.get("candidate_family", "") or "")
        is_bbs = family.startswith("bbs_")
        bbs_not_smoked = (
            is_bbs
            and bool(spice_text)
            and not args.skip_ngspice
            and str(row.get("candidate", "")) not in bbs_smoke_candidates
        )
        should_run_ngspice = (
            bool(spice_text)
            and not args.skip_ngspice
            and (bool(row.get("math_pass")) or view_math_ok or is_bbs)
            and not bbs_not_smoked
        )
        if should_run_ngspice:
            smoke_dir = channel_dir / "ngspice_smoke" / str(row["candidate"])
            case_stop_ns = max(args.smoke_stop_ns, float(row.get("delay_estimate_ns") or 0.0) + 12.0)
            smoke_rows = run_ngspice_cases(args.ngspice.resolve(), ROOT / str(row["spice_file"]), nports, smoke_dir, smoke_cases(case_stop_ns), args.sim_timeout)
            for smoke in smoke_rows:
                annotate_smoke_confidence(smoke, args)
                smoke_rows_all.append({**base, "candidate": row["candidate"], "candidate_family": row.get("candidate_family", ""), **smoke})
            row_smoke_rows = smoke_rows
            row["ngspice_pass"] = all(not smoke_gate_failures(smoke, args) for smoke in smoke_rows)
            row["ngspice_cases"] = len(smoke_rows)
            row["ngspice_cases_passed"] = sum(not smoke_gate_failures(smoke, args) for smoke in smoke_rows)
            shape_scores = [
                float(smoke.get("voltage_shape_score_v"))
                for smoke in smoke_rows
                if smoke.get("voltage_shape_score_v") not in ("", None)
                and math.isfinite(float(smoke.get("voltage_shape_score_v")))
            ]
            row["max_voltage_shape_score_v"] = max(shape_scores) if shape_scores else ""
            rx_shape_scores = [
                smoke_prefix_shape_score(smoke, "rx")
                for smoke in smoke_rows
                if math.isfinite(smoke_prefix_shape_score(smoke, "rx"))
            ]
            tx_shape_scores = [
                smoke_prefix_shape_score(smoke, "tx")
                for smoke in smoke_rows
                if math.isfinite(smoke_prefix_shape_score(smoke, "tx"))
            ]
            row["max_rx_voltage_shape_score_v"] = max(rx_shape_scores) if rx_shape_scores else ""
            row["max_tx_voltage_shape_score_v"] = max(tx_shape_scores) if tx_shape_scores else ""
            row["threshold_delay_confidence_low_cases"] = sum(1 for smoke in smoke_rows if smoke.get("threshold_delay_confidence") == "low")
            row["rx_threshold_delay_confidence_low_cases"] = sum(
                1
                for smoke in smoke_rows
                if smoke.get("threshold_delay_confidence") == "low"
                and any(item.startswith("rx_") for item in str(smoke.get("threshold_delay_confidence_reasons", "") or "").split(";"))
            )
            row["tx_threshold_delay_confidence_low_cases"] = sum(
                1
                for smoke in smoke_rows
                if smoke.get("threshold_delay_confidence") == "low"
                and any(item.startswith("tx_") for item in str(smoke.get("threshold_delay_confidence_reasons", "") or "").split(";"))
            )
            row["threshold_delay_confidence_low_reasons"] = ";".join(
                sorted(
                    {
                        item
                        for smoke in smoke_rows
                        for item in str(smoke.get("threshold_delay_confidence_reasons", "") or "").split(";")
                        if item
                    }
                )
            )
        else:
            row["ngspice_pass"] = False if not row.get("math_pass") else "skipped"
        if bbs_not_smoked:
            row["ngspice_pass"] = "skipped_bbs_not_top_n"
            row["math_fail_reasons"] = append_reason(row.get("math_fail_reasons", ""), "bbs_smoke_not_in_top_n")
            row["ngspice_fail_reasons"] = "bbs_smoke_not_in_top_n"
        else:
            row["ngspice_fail_reasons"] = "" if row_smoke_rows else ("ngspice_skipped" if row.get("math_pass") else "")
        trust_class, trust_failures, trust_warnings = classify_candidate(row, row_smoke_rows, args)
        row["trust_class"] = trust_class
        row["trust_fail_reasons"] = trust_failures
        row["trust_warn_reasons"] = trust_warnings
        rx_voltage_class, rx_voltage_failures, rx_voltage_warnings = classify_rx_voltage_shape(row, row_smoke_rows, args)
        row["rx_voltage_shape_class"] = rx_voltage_class
        row["rx_voltage_shape_fail_reasons"] = rx_voltage_failures
        row["rx_voltage_shape_warn_reasons"] = rx_voltage_warnings
        rx_timing_class, rx_timing_failures, rx_timing_warnings = classify_rx_timing(row, row_smoke_rows, args)
        row["rx_timing_class"] = rx_timing_class
        row["rx_timing_fail_reasons"] = rx_timing_failures
        row["rx_timing_warn_reasons"] = rx_timing_warnings
        rx_class, rx_failures, rx_warnings = combine_rx_classes(
            rx_voltage_class,
            rx_voltage_failures,
            rx_voltage_warnings,
            rx_timing_class,
            rx_timing_failures,
            rx_timing_warnings,
        )
        row["rx_trust_class"] = rx_class
        row["rx_fail_reasons"] = rx_failures
        row["rx_warn_reasons"] = rx_warnings
        row["rx_ready_status_candidate"] = rx_ready_status_from_classes(rx_voltage_class, rx_timing_class, rx_class)
        reflection_class, reflection_failures, reflection_warnings = classify_view_candidate(row, row_smoke_rows, args, "reflection")
        row["reflection_trust_class"] = reflection_class
        row["reflection_fail_reasons"] = reflection_failures
        row["reflection_warn_reasons"] = reflection_warnings
        full_class, full_failures, full_warnings = classify_view_candidate(row, row_smoke_rows, args, "full_model")
        row["full_model_trust_class"] = full_class
        row["full_model_fail_reasons"] = full_failures
        row["full_model_warn_reasons"] = full_warnings
        row["independent_score"] = quality_score(row)
        row["rx_independent_score"] = view_quality_score(row, "rx")
        row["reflection_independent_score"] = view_quality_score(row, "reflection")
        row["full_model_independent_score"] = view_quality_score(row, "full_model")

    apply_combined_candidate_gates(candidate_rows, args)

    selected = select_candidate(candidate_rows)
    rx_selected = select_candidate_for_view(candidate_rows, "rx")
    reflection_selected = select_candidate_for_view(candidate_rows, "reflection")
    full_best = select_candidate_for_view(candidate_rows, "full_model")
    full_selected = full_best if full_best is not None and full_best.get("full_model_trust_class") == "PASS" else None
    rx_attempt = rx_selected or best_candidate_attempt_for_view(candidate_rows, "rx")
    reflection_attempt = reflection_selected or best_candidate_attempt_for_view(candidate_rows, "reflection")
    full_attempt = full_best or best_candidate_attempt_for_view(candidate_rows, "full_model")
    for row in candidate_rows:
        row["selected"] = bool(selected and row["candidate"] == selected["candidate"])
        row["rx_selected"] = bool(rx_selected and row["candidate"] == rx_selected["candidate"])
        row["reflection_selected"] = bool(reflection_selected and row["candidate"] == reflection_selected["candidate"])
        row["full_model_selected"] = bool(full_selected and row["candidate"] == full_selected["candidate"])
        all_metrics.append(row)

    primary_selected = full_selected or rx_selected or selected
    if primary_selected is None:
        ranking_rows.append(
            {
                **base,
                "selected_candidate": "",
                "status": "no_candidate_passed",
                "independent_trust_class": "FAIL",
                "rx_trust_class": "FAIL",
                "rx_voltage_shape_class": "FAIL",
                "rx_timing_class": "FAIL",
                "reflection_trust_class": "FAIL",
                "full_model_trust_class": "FAIL",
                "rx_ready_status": "FAIL",
                "reflection_ready_status": "FAIL",
                "full_model_ready_status": "FAIL",
                "reason": "no candidate passed independent qualification gates",
            }
        )
        return

    selected = primary_selected
    selected_source = ROOT / str(selected["spice_file"])
    selected_channel_copy = channel_dir / "selected_model.sp"
    selected_study_copy = args.study_dir.resolve() / "selected_models" / f"{channel_id}.sp"
    selected_channel_copy.parent.mkdir(parents=True, exist_ok=True)
    selected_study_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(selected_source, selected_channel_copy)
    shutil.copy2(selected_source, selected_study_copy)
    rx_model_copy = ""
    rx_channel_model_copy = ""
    if rx_selected is not None:
        rx_model_copy = copy_selected_model(rx_selected.get("spice_file", ""), args.study_dir.resolve() / "selected_models" / "rx" / f"{channel_id}.sp")
        rx_channel_model_copy = copy_selected_model(rx_selected.get("spice_file", ""), channel_dir / "selected_rx_model.sp")
    reflection_model_copy = ""
    reflection_channel_model_copy = ""
    if reflection_selected is not None:
        reflection_model_copy = copy_selected_model(reflection_selected.get("spice_file", ""), args.study_dir.resolve() / "selected_models" / "reflection" / f"{channel_id}.sp")
        reflection_channel_model_copy = copy_selected_model(reflection_selected.get("spice_file", ""), channel_dir / "selected_reflection_model.sp")
    full_model_copy = ""
    full_channel_model_copy = ""
    if full_selected is not None:
        full_model_copy = copy_selected_model(full_selected.get("spice_file", ""), args.study_dir.resolve() / "selected_models" / "full" / f"{channel_id}.sp")
        full_channel_model_copy = copy_selected_model(full_selected.get("spice_file", ""), channel_dir / "selected_full_model.sp")

    ranking_rows.append(
        {
            **base,
            "selected_candidate": selected["candidate"],
            "selected_candidate_family": selected.get("candidate_family", ""),
            "selected_fit_source": selected.get("fit_source", ""),
            "selected_use_scope": selected.get("use_scope", ""),
            "selected_dominant_path": selected.get("dominant_path", ""),
            "selected_delay_estimate_ns": selected.get("delay_estimate_ns", ""),
            "selected_delay_equalized": selected.get("delay_equalized", ""),
            "selected_delay_estimator_source": selected.get("delay_estimator_source", ""),
            "selected_delay_step_threshold_ns": selected.get("delay_step_threshold_ns", ""),
            "selected_delay_impulse_peak_ns": selected.get("delay_impulse_peak_ns", ""),
            "selected_delay_group_delay_median_ns": selected.get("delay_group_delay_median_ns", ""),
            "selected_basis_order": selected.get("basis_order", ""),
            "selected_ring_basis_count": selected.get("ring_basis_count", ""),
            "selected_reflection_basis_count": selected.get("reflection_basis_count", ""),
            "selected_spice_file": selected["spice_file"],
            "selected_model_copy": rel(selected_study_copy),
            "selected_channel_model_copy": rel(selected_channel_copy),
            "selected_model_order": selected["model_order"],
            "selected_fit_complex_rms": selected["fit_complex_rms"],
            "selected_max_sv_high": selected["max_sv_high"],
            "independent_score": selected.get("independent_score", ""),
            "independent_trust_class": selected.get("trust_class", ""),
            "independent_fail_reasons": selected.get("trust_fail_reasons", ""),
            "independent_warn_reasons": selected.get("trust_warn_reasons", ""),
            "rx_selected_candidate": "" if rx_selected is None else rx_selected.get("candidate", ""),
            "rx_selected_candidate_family": "" if rx_selected is None else rx_selected.get("candidate_family", ""),
            "rx_selected_use_scope": "" if rx_selected is None else rx_selected.get("use_scope", ""),
            "rx_selected_dominant_path": "" if rx_selected is None else rx_selected.get("dominant_path", ""),
            "rx_selected_spice_file": "" if rx_selected is None else rx_selected.get("spice_file", ""),
            "rx_selected_model_copy": rx_model_copy,
            "rx_selected_channel_model_copy": rx_channel_model_copy,
            "rx_best_attempt_candidate": "" if rx_attempt is None else rx_attempt.get("candidate", ""),
            "rx_trust_class": "FAIL" if rx_attempt is None else rx_attempt.get("rx_trust_class", ""),
            "rx_voltage_shape_class": "FAIL" if rx_attempt is None else rx_attempt.get("rx_voltage_shape_class", ""),
            "rx_voltage_shape_fail_reasons": "no_rx_candidate" if rx_attempt is None else rx_attempt.get("rx_voltage_shape_fail_reasons", ""),
            "rx_voltage_shape_warn_reasons": "" if rx_attempt is None else rx_attempt.get("rx_voltage_shape_warn_reasons", ""),
            "rx_timing_class": "FAIL" if rx_attempt is None else rx_attempt.get("rx_timing_class", ""),
            "rx_timing_fail_reasons": "no_rx_candidate" if rx_attempt is None else rx_attempt.get("rx_timing_fail_reasons", ""),
            "rx_timing_warn_reasons": "" if rx_attempt is None else rx_attempt.get("rx_timing_warn_reasons", ""),
            "rx_fail_reasons": "no_rx_candidate" if rx_attempt is None else rx_attempt.get("rx_fail_reasons", ""),
            "rx_warn_reasons": "" if rx_attempt is None else rx_attempt.get("rx_warn_reasons", ""),
            "rx_independent_score": "" if rx_attempt is None else rx_attempt.get("rx_independent_score", ""),
            "rx_ready_status": "FAIL" if rx_attempt is None else rx_attempt.get("rx_ready_status_candidate", rx_ready_status_from_classes(rx_attempt.get("rx_voltage_shape_class"), rx_attempt.get("rx_timing_class"), rx_attempt.get("rx_trust_class"))),
            "reflection_selected_candidate": "" if reflection_selected is None else reflection_selected.get("candidate", ""),
            "reflection_selected_candidate_family": "" if reflection_selected is None else reflection_selected.get("candidate_family", ""),
            "reflection_selected_use_scope": "" if reflection_selected is None else reflection_selected.get("use_scope", ""),
            "reflection_selected_spice_file": "" if reflection_selected is None else reflection_selected.get("spice_file", ""),
            "reflection_selected_model_copy": reflection_model_copy,
            "reflection_selected_channel_model_copy": reflection_channel_model_copy,
            "reflection_best_attempt_candidate": "" if reflection_attempt is None else reflection_attempt.get("candidate", ""),
            "reflection_trust_class": "FAIL" if reflection_attempt is None else reflection_attempt.get("reflection_trust_class", ""),
            "reflection_fail_reasons": "no_reflection_candidate" if reflection_attempt is None else reflection_attempt.get("reflection_fail_reasons", ""),
            "reflection_warn_reasons": "" if reflection_attempt is None else reflection_attempt.get("reflection_warn_reasons", ""),
            "reflection_independent_score": "" if reflection_attempt is None else reflection_attempt.get("reflection_independent_score", ""),
            "reflection_ready_status": trust_ready_label(None if reflection_attempt is None else reflection_attempt.get("reflection_trust_class"), "REFLECTION_READY"),
            "full_selected_candidate": "" if full_selected is None else full_selected.get("candidate", ""),
            "full_selected_candidate_family": "" if full_selected is None else full_selected.get("candidate_family", ""),
            "full_selected_use_scope": "" if full_selected is None else full_selected.get("use_scope", ""),
            "full_selected_spice_file": "" if full_selected is None else full_selected.get("spice_file", ""),
            "full_selected_model_copy": full_model_copy,
            "full_selected_channel_model_copy": full_channel_model_copy,
            "full_model_best_candidate": "" if full_best is None else full_best.get("candidate", ""),
            "full_model_best_candidate_family": "" if full_best is None else full_best.get("candidate_family", ""),
            "full_model_best_use_scope": "" if full_best is None else full_best.get("use_scope", ""),
            "full_model_trust_class": "FAIL" if full_attempt is None else full_attempt.get("full_model_trust_class", ""),
            "full_model_fail_reasons": "no_full_model_candidate" if full_attempt is None else full_attempt.get("full_model_fail_reasons", ""),
            "full_model_warn_reasons": "" if full_attempt is None else full_attempt.get("full_model_warn_reasons", ""),
            "full_model_independent_score": "" if full_attempt is None else full_attempt.get("full_model_independent_score", ""),
            "full_model_ready_status": trust_ready_label(None if full_attempt is None else full_attempt.get("full_model_trust_class"), "FULL_MODEL_READY"),
            "status": "selected",
            "reason": "full model selected if independently PASS, otherwise scoped RX model selected for backward-compatible primary output",
        }
    )

    selected_vf = fitted_by_name.get(str(selected["candidate"]))
    if selected_vf is not None:
        plot_frequency_fit(nw, selected_vf, plot_dir / "frequency_fit.png", f"{channel_id}: selected fit")
        plot_singular(selected_vf, high_fmax, plot_dir / "max_singular_value.png", f"{channel_id}: selected fit passivity")

    if not args.skip_hspice:
        audit_dir = channel_dir / "hspice_audit"
        audit_touchstone = audit_dir / f"channel.s{nports}p"
        audit_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(channel_path, audit_touchstone)
        for case in selected_audit_cases(args):
            h_row = run_hspice_case(args.hspice.resolve(), audit_touchstone, nports, audit_dir, case, args.sim_timeout)
            ng_dir = audit_dir / "ngspice"
            ng_rows = run_ngspice_cases(args.ngspice.resolve(), ROOT / str(selected["spice_file"]), nports, ng_dir, [case], args.sim_timeout)
            ng_row = ng_rows[0] if ng_rows else {}
            corr = {
                **base,
                "candidate": selected["candidate"],
                "selected_candidate": selected["candidate"],
                "selected_candidate_family": selected.get("candidate_family", ""),
                "selected_fit_source": selected.get("fit_source", ""),
                "selected_use_scope": selected.get("use_scope", ""),
                "independent_trust_class": selected.get("trust_class", ""),
                "independent_warn_reasons": selected.get("trust_warn_reasons", ""),
                "rx_selected_candidate": "" if rx_selected is None else rx_selected.get("candidate", ""),
                "rx_trust_class": "FAIL" if rx_attempt is None else rx_attempt.get("rx_trust_class", ""),
                "rx_voltage_shape_class": "FAIL" if rx_attempt is None else rx_attempt.get("rx_voltage_shape_class", ""),
                "rx_voltage_shape_warn_reasons": "" if rx_attempt is None else rx_attempt.get("rx_voltage_shape_warn_reasons", ""),
                "rx_timing_class": "FAIL" if rx_attempt is None else rx_attempt.get("rx_timing_class", ""),
                "rx_timing_warn_reasons": "" if rx_attempt is None else rx_attempt.get("rx_timing_warn_reasons", ""),
                "rx_warn_reasons": "" if rx_attempt is None else rx_attempt.get("rx_warn_reasons", ""),
                "rx_ready_status": "FAIL" if rx_attempt is None else rx_attempt.get("rx_ready_status_candidate", ""),
                "reflection_selected_candidate": "" if reflection_selected is None else reflection_selected.get("candidate", ""),
                "reflection_trust_class": "FAIL" if reflection_selected is None else reflection_selected.get("reflection_trust_class", ""),
                "reflection_warn_reasons": "" if reflection_selected is None else reflection_selected.get("reflection_warn_reasons", ""),
                "full_selected_candidate": "" if full_selected is None else full_selected.get("candidate", ""),
                "full_model_trust_class": "FAIL" if full_best is None else full_best.get("full_model_trust_class", ""),
                "full_model_warn_reasons": "" if full_best is None else full_best.get("full_model_warn_reasons", ""),
                "case": case.name,
                **h_row,
                "ngspice_raw": ng_row.get("raw", ""),
                "ngspice_log": ng_row.get("log", ""),
                "ngspice_return_code": ng_row.get("return_code", ""),
            }
            h_tr0 = Path(str(h_row.get("hspice_tr0", "")))
            if not h_tr0.is_absolute():
                h_tr0 = ROOT / h_tr0
            n_raw = Path(str(ng_row.get("raw", "")))
            if not n_raw.is_absolute():
                n_raw = ROOT / n_raw
            if h_tr0.exists() and n_raw.exists():
                corr.update(compare_hspice_ngspice(h_tr0, n_raw, nports))
                try:
                    overlay = plot_dir / f"{case.name}_hspice_vs_ngspice.png"
                    plot_transient_overlay(h_tr0, n_raw, nports, overlay, f"{channel_id}: {case.name}")
                    corr["overlay_plot"] = rel(overlay)
                except Exception as exc:
                    corr["plot_error"] = str(exc)
            else:
                corr["correlation_status"] = "missing_raw"
            h_class, h_reason = classify_hspice_row(corr, args)
            corr["hspice_audit_class"] = h_class
            corr["hspice_audit_reason"] = h_reason
            rx_h_class, rx_h_reason = classify_hspice_row_view(corr, args, "rx")
            corr["rx_hspice_audit_class"] = rx_h_class
            corr["rx_hspice_audit_reason"] = rx_h_reason
            reflection_h_class, reflection_h_reason = classify_hspice_row_view(corr, args, "reflection")
            corr["reflection_hspice_audit_class"] = reflection_h_class
            corr["reflection_hspice_audit_reason"] = reflection_h_reason
            corr["full_model_hspice_audit_class"] = h_class
            corr["full_model_hspice_audit_reason"] = h_reason
            corr_rows.append(corr)


def write_study_outputs(
    study_dir: Path,
    all_metrics: list[dict[str, object]],
    smoke_rows: list[dict[str, object]],
    ranking_rows: list[dict[str, object]],
    corr_rows: list[dict[str, object]],
    bbs_candidate_rows: list[dict[str, object]] | None = None,
) -> None:
    write_csv(study_dir / "metrics.csv", all_metrics)
    write_csv(study_dir / "ngspice_smoke.csv", smoke_rows)
    write_csv(study_dir / "ranking.csv", ranking_rows)
    write_csv(study_dir / "hspice_correlation.csv", corr_rows)
    if bbs_candidate_rows is not None:
        write_csv(study_dir / "bbs_candidates.csv", bbs_candidate_rows)
        write_csv(study_dir / "bbs_ranking.csv", bbs_ranking_rows(all_metrics, bbs_candidate_rows))
    bbs_rows = bbs_metric_rows(all_metrics)
    if bbs_rows:
        write_csv(study_dir / "bbs_metrics.csv", bbs_rows)
    bbs_smoke_rows = [row for row in smoke_rows if str(row.get("candidate_family", "")).startswith("bbs_")]
    if bbs_smoke_rows:
        write_csv(study_dir / "bbs_ngspice_smoke.csv", bbs_smoke_rows)
    if corr_rows:
        write_csv(study_dir / "calibration_summary.csv", calibration_summary_rows(ranking_rows, corr_rows))
        write_audit_overlay_pdfs(study_dir, corr_rows)
    write_derived_summary_csvs(study_dir, all_metrics, ranking_rows, corr_rows)
    write_report(study_dir, all_metrics, ranking_rows, corr_rows)


def run_study(args: argparse.Namespace) -> int:
    ensure_skrf(args.skrf_target)
    study_dir = args.study_dir.resolve()
    manifest = args.manifest.resolve() if args.manifest else study_dir / "manifest.csv"
    if not manifest.exists():
        inventory_args = argparse.Namespace(**vars(args))
        inventory_args.manifest = manifest
        inventory(inventory_args)

    rows = read_csv(manifest)
    supported = [row for row in rows if str(row.get("supported_v1")).lower() == "true" and row.get("status") == "ok"]
    metrics_path = study_dir / "metrics.csv"
    smoke_path = study_dir / "ngspice_smoke.csv"
    ranking_path = study_dir / "ranking.csv"
    corr_path = study_dir / "hspice_correlation.csv"
    bbs_path = study_dir / "bbs_candidates.csv"
    all_metrics: list[dict[str, object]] = [dict(row) for row in read_csv(metrics_path)] if args.resume and metrics_path.exists() else []
    smoke_rows: list[dict[str, object]] = [dict(row) for row in read_csv(smoke_path)] if args.resume and smoke_path.exists() else []
    ranking_rows: list[dict[str, object]] = [dict(row) for row in read_csv(ranking_path)] if args.resume and ranking_path.exists() else []
    corr_rows: list[dict[str, object]] = [dict(row) for row in read_csv(corr_path)] if args.resume and corr_path.exists() else []
    bbs_candidate_rows: list[dict[str, object]] = [dict(row) for row in read_csv(bbs_path)] if args.resume and bbs_path.exists() else []
    if args.resume:
        completed = {str(row.get("channel_id", "")) for row in ranking_rows if row.get("channel_id")}
        supported = [row for row in supported if str(row.get("channel_id", "")) not in completed]
    if args.max_channels:
        supported = supported[: args.max_channels]

    for idx, row in enumerate(supported, start=1):
        print(f"[{idx}/{len(supported)}] {row['channel_id']} ({row['relative_path']})")
        run_channel(args, row, all_metrics, smoke_rows, ranking_rows, corr_rows, bbs_candidate_rows)
        write_study_outputs(study_dir, all_metrics, smoke_rows, ranking_rows, corr_rows, bbs_candidate_rows)

    write_study_outputs(study_dir, all_metrics, smoke_rows, ranking_rows, corr_rows, bbs_candidate_rows)
    print(f"Wrote study outputs under {study_dir}")
    return 0


def qualify_study(args: argparse.Namespace) -> int:
    args.skip_hspice = True
    return run_study(args)


def bbs_metric_rows(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in metrics if str(row.get("candidate_family", "")).startswith("bbs_")]


def bbs_ngspice_rank(row: dict[str, object]) -> int:
    status = str(row.get("ngspice_pass", ""))
    if status == "True" or row.get("ngspice_pass") is True:
        return 0
    if status == "False" or row.get("ngspice_pass") is False:
        return 1
    return 2


def bbs_ranking_rows(metrics: list[dict[str, object]], bbs_candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    metric_by_channel: dict[str, list[dict[str, object]]] = {}
    extraction_by_channel: dict[str, list[dict[str, object]]] = {}
    for row in bbs_metric_rows(metrics):
        metric_by_channel.setdefault(str(row.get("channel_id", "")), []).append(row)
    for row in bbs_candidates:
        extraction_by_channel.setdefault(str(row.get("channel_id", "")), []).append(row)

    rows: list[dict[str, object]] = []
    for channel_id in sorted(set(metric_by_channel) | set(extraction_by_channel)):
        metrics_for_channel = metric_by_channel.get(channel_id, [])
        extractions = extraction_by_channel.get(channel_id, [])
        if metrics_for_channel:
            best = sorted(
                metrics_for_channel,
                key=lambda row: (
                    TRUST_CLASS_RANK.get(str(row.get("trust_class", "FAIL")), 3),
                    bbs_ngspice_rank(row),
                    warning_count(row),
                    quality_score(row),
                    int(float(row.get("model_order") or 999)),
                ),
            )[0]
            rows.append(
                {
                    "channel_id": channel_id,
                    "channel_path": best.get("channel_path", ""),
                    "ports": best.get("ports", ""),
                    "best_bbs_candidate": best.get("candidate", ""),
                    "best_bbs_mode": best.get("bbs_mode", ""),
                    "best_bbs_preset": best.get("bbs_preset", ""),
                    "best_bbs_trust_class": best.get("trust_class", ""),
                    "best_bbs_rx_trust_class": best.get("rx_trust_class", ""),
                    "best_bbs_reflection_trust_class": best.get("reflection_trust_class", ""),
                    "best_bbs_full_model_trust_class": best.get("full_model_trust_class", ""),
                    "best_bbs_independent_score": best.get("independent_score", ""),
                    "best_bbs_fit_complex_rms": best.get("fit_complex_rms", ""),
                    "best_bbs_mag_db_max_above_m40": best.get("fit_mag_db_max_above_m40", ""),
                    "best_bbs_group_delay_rms_ps": best.get("fit_group_delay_rms_ps", ""),
                    "best_bbs_max_sv_high": best.get("max_sv_high", ""),
                    "best_bbs_ngspice_pass": best.get("ngspice_pass", ""),
                    "best_bbs_ngspice_cases_passed": best.get("ngspice_cases_passed", ""),
                    "best_bbs_spice_file": best.get("spice_file", ""),
                    "best_bbs_circuit_file": best.get("bbs_circuit_file", ""),
                    "best_bbs_fitted_touchstone": best.get("bbs_fitted_touchstone", ""),
                    "status": "best_bbs_metric_candidate",
                    "extraction_rows": len(extractions),
                    "successful_extractions": sum(1 for row in extractions if row.get("bbs_status") == "ok"),
                    "timeout_extractions": sum(1 for row in extractions if str(row.get("bbs_timed_out", "")).lower() == "true"),
                }
            )
            continue
        rows.append(
            {
                "channel_id": channel_id,
                "channel_path": extractions[0].get("channel_path", "") if extractions else "",
                "ports": extractions[0].get("ports", "") if extractions else "",
                "best_bbs_candidate": "",
                "best_bbs_trust_class": "FAIL",
                "best_bbs_rx_trust_class": "FAIL",
                "best_bbs_reflection_trust_class": "FAIL",
                "best_bbs_full_model_trust_class": "FAIL",
                "status": "no_successful_bbs_gspice_model",
                "extraction_rows": len(extractions),
                "successful_extractions": sum(1 for row in extractions if row.get("bbs_status") == "ok"),
                "timeout_extractions": sum(1 for row in extractions if str(row.get("bbs_timed_out", "")).lower() == "true"),
                "failed_candidates": ";".join(str(row.get("candidate", "")) for row in extractions if row.get("bbs_status") != "ok"),
            }
        )
    return rows


def resolve_artifact_path(text: object) -> Path | None:
    value = str(text or "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def copy_artifact(src_text: object, dest: Path) -> str:
    src = resolve_artifact_path(src_text)
    if not src or not src.exists() or not src.is_file():
        return ""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return rel(dest)


def write_bbs_audit_share_pack(study_dir: Path, bbs_corr_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not bbs_corr_rows:
        return []
    out_root = study_dir / "bbs_audit_share_pack"
    index_rows: list[dict[str, object]] = []
    for row in bbs_corr_rows:
        channel_id = str(row.get("channel_id", "") or "channel")
        candidate = str(row.get("candidate", "") or "candidate")
        case = str(row.get("case", "") or "case")
        case_dir = out_root / channel_id / candidate / case
        copied: dict[str, str] = {}
        copied["rx_overlay"] = copy_artifact(row.get("rx_overlay_plot", ""), case_dir / "rx_overlay.png")
        copied["tx_overlay"] = copy_artifact(row.get("tx_overlay_plot", ""), case_dir / "tx_overlay.png")
        copied["two_panel_overlay"] = copy_artifact(row.get("overlay_plot", ""), case_dir / "overlay_two_panel.png")
        copied["bbs_gspice_model"] = copy_artifact(row.get("bbs_circuit_file", ""), case_dir / "bbs_gspice_model.txt")
        copied["ngspice_wrapper"] = copy_artifact(row.get("ngspice_model_spice", ""), case_dir / "ngspice_wrapper.sp")
        copied["hspice_tr0"] = copy_artifact(row.get("hspice_tr0", ""), case_dir / "hspice.tr0")
        copied["hspice_lis"] = copy_artifact(row.get("hspice_lis", ""), case_dir / "hspice.lis")
        copied["ngspice_raw"] = copy_artifact(row.get("ngspice_raw", ""), case_dir / "ngspice.raw")
        copied["ngspice_log"] = copy_artifact(row.get("ngspice_log", ""), case_dir / "ngspice.log")

        h_tr0 = resolve_artifact_path(row.get("hspice_tr0", ""))
        if h_tr0:
            copied["hspice_deck"] = copy_artifact(h_tr0.with_suffix(".sp"), case_dir / "hspice_native_s_element.sp")
            touchstone = h_tr0.parent / f"channel.s{row.get('ports', '')}p"
            copied["audit_touchstone"] = copy_artifact(touchstone, case_dir / touchstone.name)
        n_raw = resolve_artifact_path(row.get("ngspice_raw", ""))
        if n_raw:
            copied["ngspice_deck"] = copy_artifact(n_raw.with_suffix(".sp"), case_dir / "ngspice_bbs_model.sp")

        readme = [
            f"# {channel_id} - {candidate} - {case}",
            "",
            "## Classification",
            "",
            f"- HSPICE audit: `{row.get('hspice_audit_class', '')}`",
            f"- RX audit: `{row.get('rx_hspice_audit_class', '')}`",
            f"- Reflection/TX audit: `{row.get('reflection_hspice_audit_class', '')}`",
            f"- BBS preset: `{row.get('bbs_preset', '')}`",
            "",
            "## Metrics",
            "",
            f"- RX active RMSE: `{row.get('rx_active_rmse_v', '')}` V",
            f"- RX active max error: `{row.get('rx_active_maxabs_v', '')}` V",
            f"- TX active RMSE: `{row.get('tx_active_rmse_v', '')}` V",
            f"- TX active max error: `{row.get('tx_active_maxabs_v', '')}` V",
            f"- RX-minus-TX rise 50% delay delta: `{row.get('rx_minus_tx_rise50_ps_delta_ps', '')}` ps",
            "",
            "## Files",
            "",
        ]
        for key in sorted(copied):
            if copied[key]:
                readme.append(f"- `{key}`: `{copied[key]}`")
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
        index_rows.append(
            {
                "channel_id": channel_id,
                "candidate": candidate,
                "case": case,
                "hspice_audit_class": row.get("hspice_audit_class", ""),
                "rx_hspice_audit_class": row.get("rx_hspice_audit_class", ""),
                "reflection_hspice_audit_class": row.get("reflection_hspice_audit_class", ""),
                "rx_active_rmse_v": row.get("rx_active_rmse_v", ""),
                "tx_active_rmse_v": row.get("tx_active_rmse_v", ""),
                "share_dir": rel(case_dir),
                **{f"{key}_copy": value for key, value in copied.items() if value},
            }
        )
    write_csv(study_dir / "bbs_audit_share_pack_index.csv", index_rows)
    return index_rows


def csv_filter_values(values: list[str] | None) -> set[str]:
    out: set[str] = set()
    for value in values or []:
        out.update(part.strip() for part in str(value).split(",") if part.strip())
    return out


def row_matches_values(row: dict[str, object], field: str, values: set[str]) -> bool:
    if not values:
        return True
    return str(row.get(field, "")) in values


def filter_audit_selected_rows(rows: list[dict[str, object]], args: argparse.Namespace) -> list[dict[str, object]]:
    channel_ids = csv_filter_values(args.channel_id)
    selected_families = csv_filter_values(args.selected_family)
    source_families = csv_filter_values(args.source_family)
    validation_splits = csv_filter_values(args.validation_split)
    rx_voltage_shape_classes = csv_filter_values(args.rx_voltage_shape_class)
    rx_timing_classes = csv_filter_values(args.rx_timing_class)
    rx_ready_statuses = csv_filter_values(args.rx_ready_status)
    reflection_classes = csv_filter_values(args.reflection_trust_class)
    full_model_classes = csv_filter_values(args.full_model_trust_class)
    filtered = []
    for row in rows:
        if not row_matches_values(row, "channel_id", channel_ids):
            continue
        if not row_matches_values(row, "selected_candidate_family", selected_families):
            continue
        if not row_matches_values(row, "source_family", source_families):
            continue
        if not row_matches_values(row, "validation_split", validation_splits):
            continue
        if not row_matches_values(row, "rx_voltage_shape_class", rx_voltage_shape_classes):
            continue
        if not row_matches_values(row, "rx_timing_class", rx_timing_classes):
            continue
        if not row_matches_values(row, "rx_ready_status", rx_ready_statuses):
            continue
        if not row_matches_values(row, "reflection_trust_class", reflection_classes):
            continue
        if not row_matches_values(row, "full_model_trust_class", full_model_classes):
            continue
        filtered.append(row)
    return filtered


def audit_row_is_retryable_error(row: dict[str, object]) -> bool:
    return (
        str(row.get("hspice_audit_class", "")) == "ERROR"
        or str(row.get("correlation_status", "")) in {"missing_raw", "compare_failed"}
        or bool(str(row.get("hspice_error", "")).strip())
    )


def audit_bbs_hspice(args: argparse.Namespace, study_dir: Path) -> None:
    bbs_path = study_dir / "bbs_candidates.csv"
    if not bbs_path.exists():
        return
    top_n = int(getattr(args, "bbs_audit_top_n", 2) or 2)
    selected_pairs: set[tuple[str, str]] = set()
    metrics_path = study_dir / "metrics.csv"
    if metrics_path.exists():
        metrics_by_channel: dict[str, list[dict[str, object]]] = {}
        for metric in bbs_metric_rows([dict(row) for row in read_csv(metrics_path)]):
            metrics_by_channel.setdefault(str(metric.get("channel_id", "")), []).append(metric)
        for channel_id, channel_metrics in metrics_by_channel.items():
            for metric in sorted(
                channel_metrics,
                key=lambda row: (
                    TRUST_CLASS_RANK.get(str(row.get("trust_class", "FAIL")), 3),
                    bbs_ngspice_rank(row),
                    warning_count(row),
                    quality_score(row),
                    int(float(row.get("model_order") or 999)),
                ),
            )[:top_n]:
                selected_pairs.add((channel_id, str(metric.get("candidate", ""))))
    rows = [
        row
        for row in read_csv(bbs_path)
        if row.get("bbs_circuit_type") == "gspice"
        and row.get("bbs_status") == "ok"
        and row.get("bbs_circuit_file")
        and (not selected_pairs or (str(row.get("channel_id", "")), str(row.get("candidate", ""))) in selected_pairs)
    ]
    if not rows:
        return
    if args.max_channels:
        seen: set[str] = set()
        limited: list[dict[str, str]] = []
        for row in rows:
            channel_id = str(row.get("channel_id", ""))
            if channel_id not in seen and len(seen) >= args.max_channels:
                continue
            seen.add(channel_id)
            limited.append(row)
        rows = limited

    corr_path = study_dir / "bbs_hspice_correlation.csv"
    corr_rows: list[dict[str, object]] = [dict(row) for row in read_csv(corr_path)] if args.resume and corr_path.exists() else []
    completed_cases = {
        (str(row.get("channel_id", "")), str(row.get("candidate", "")), str(row.get("case", "")))
        for row in corr_rows
        if row.get("channel_id") and row.get("candidate") and row.get("case")
    }
    for idx, row in enumerate(rows, start=1):
        channel_id = row["channel_id"]
        candidate = row["candidate"]
        channel_path = Path(row["channel_path"])
        if not channel_path.is_absolute():
            channel_path = ROOT / channel_path
        nports = int(row["ports"])
        model_path = Path(row.get("ngspice_model_spice") or "")
        if not model_path.is_absolute():
            model_path = ROOT / model_path
        if not model_path.exists():
            # Backfill from the normal metrics table when bbs_candidates.csv came
            # from an older qualify run.
            metrics = [
                metric
                for metric in read_csv(study_dir / "metrics.csv")
                if metric.get("channel_id") == channel_id and metric.get("candidate") == candidate
            ]
            if metrics:
                model_path = Path(metrics[0].get("spice_file", ""))
                if not model_path.is_absolute():
                    model_path = ROOT / model_path
        if not model_path.exists():
            continue
        audit_dir = study_dir / "channels" / channel_id / "bbs_hspice_audit" / candidate
        audit_touchstone = audit_dir / f"channel.s{nports}p"
        audit_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(channel_path, audit_touchstone)
        print(f"[BBS {idx}/{len(rows)}] HSPICE audit {channel_id} {candidate}")
        for case in selected_audit_cases(args):
            if args.resume and (channel_id, candidate, case.name) in completed_cases:
                continue
            h_row = run_hspice_case(args.hspice.resolve(), audit_touchstone, nports, audit_dir, case, args.sim_timeout)
            ng_dir = audit_dir / "ngspice"
            ng_rows = run_ngspice_cases(args.ngspice.resolve(), model_path, nports, ng_dir, [case], args.sim_timeout)
            ng_row = ng_rows[0] if ng_rows else {}
            corr: dict[str, object] = {
                "channel_id": channel_id,
                "source": row.get("source", ""),
                "source_family": row.get("source_family", ""),
                "validation_split": row.get("validation_split", ""),
                "channel_path": row.get("channel_path", ""),
                "ports": nports,
                "candidate": candidate,
                "candidate_family": "bbs_full_model",
                "bbs_mode": row.get("bbs_mode", ""),
                "bbs_preset": row.get("bbs_preset", ""),
                "bbs_config_file": row.get("bbs_config_file", ""),
                "bbs_circuit_file": row.get("bbs_circuit_file", ""),
                "ngspice_model_spice": rel(model_path),
                "case": case.name,
                **h_row,
                "ngspice_raw": ng_row.get("raw", ""),
                "ngspice_log": ng_row.get("log", ""),
                "ngspice_return_code": ng_row.get("return_code", ""),
            }
            h_tr0 = Path(str(h_row.get("hspice_tr0", "")))
            if not h_tr0.is_absolute():
                h_tr0 = ROOT / h_tr0
            n_raw = Path(str(ng_row.get("raw", "")))
            if not n_raw.is_absolute():
                n_raw = ROOT / n_raw
            if h_tr0.exists() and n_raw.exists():
                corr.update(compare_hspice_ngspice(h_tr0, n_raw, nports))
                try:
                    overlay = study_dir / "plots" / "bbs_overlays" / channel_id / f"{candidate}_{case.name}.png"
                    plot_transient_overlay(h_tr0, n_raw, nports, overlay, f"{channel_id}: {candidate} {case.name}")
                    corr["overlay_plot"] = rel(overlay)
                    rx_overlay = study_dir / "plots" / "bbs_overlays" / channel_id / "rx" / f"{candidate}_{case.name}_rx.png"
                    tx_overlay = study_dir / "plots" / "bbs_overlays" / channel_id / "tx" / f"{candidate}_{case.name}_tx.png"
                    plot_transient_side_overlay(h_tr0, n_raw, nports, rx_overlay, f"{channel_id}: {candidate} {case.name}", "rx", "ngspice BBS")
                    plot_transient_side_overlay(h_tr0, n_raw, nports, tx_overlay, f"{channel_id}: {candidate} {case.name}", "tx", "ngspice BBS")
                    corr["rx_overlay_plot"] = rel(rx_overlay)
                    corr["tx_overlay_plot"] = rel(tx_overlay)
                except Exception as exc:
                    corr["plot_error"] = str(exc)
            else:
                corr["correlation_status"] = "missing_raw"
            h_class, h_reason = classify_hspice_row(corr, args)
            corr["hspice_audit_class"] = h_class
            corr["hspice_audit_reason"] = h_reason
            rx_h_class, rx_h_reason = classify_hspice_row_view(corr, args, "rx")
            corr["rx_hspice_audit_class"] = rx_h_class
            corr["rx_hspice_audit_reason"] = rx_h_reason
            reflection_h_class, reflection_h_reason = classify_hspice_row_view(corr, args, "reflection")
            corr["reflection_hspice_audit_class"] = reflection_h_class
            corr["reflection_hspice_audit_reason"] = reflection_h_reason
            corr["full_model_hspice_audit_class"] = h_class
            corr["full_model_hspice_audit_reason"] = h_reason
            corr_rows.append(corr)
            completed_cases.add((channel_id, candidate, case.name))
            write_csv(corr_path, corr_rows)
    write_csv(corr_path, corr_rows)


def audit_hspice(args: argparse.Namespace) -> int:
    ensure_skrf(args.skrf_target)
    study_dir = args.study_dir.resolve()
    ranking_path = args.ranking.resolve() if args.ranking else study_dir / "ranking.csv"
    if not ranking_path.exists():
        raise StudyError(f"Missing ranking file: {ranking_path}. Run qualify first.")
    ranking = read_csv(ranking_path)
    selected = [row for row in ranking if row.get("status") == "selected" and row.get("selected_candidate")]
    selected = filter_audit_selected_rows(selected, args)
    if args.max_channels:
        selected = selected[: args.max_channels]

    corr_path = study_dir / "hspice_correlation.csv"
    corr_rows: list[dict[str, object]] = [dict(row) for row in read_csv(corr_path)] if args.resume and corr_path.exists() else []
    if args.resume and args.retry_errors:
        selected_channel_ids = {str(row.get("channel_id", "")) for row in selected}
        corr_rows = [
            row for row in corr_rows
            if str(row.get("channel_id", "")) not in selected_channel_ids or not audit_row_is_retryable_error(row)
        ]
    completed_cases = {
        (str(row.get("channel_id", "")), str(row.get("case", "")))
        for row in corr_rows
        if row.get("channel_id") and row.get("case")
    }
    for idx, row in enumerate(selected, start=1):
        channel_id = row["channel_id"]
        channel_path = Path(row["channel_path"]).resolve() if Path(row["channel_path"]).is_absolute() else ROOT / row["channel_path"]
        nports = int(row["ports"])
        model_path_text = row.get("selected_model_copy") or row.get("selected_spice_file") or ""
        selected_model = Path(model_path_text).resolve() if Path(model_path_text).is_absolute() else ROOT / model_path_text
        channel_dir = study_dir / "channels" / channel_id
        audit_dir = channel_dir / "hspice_audit"
        audit_touchstone = audit_dir / f"channel.s{nports}p"
        audit_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(channel_path, audit_touchstone)
        print(f"[{idx}/{len(selected)}] HSPICE audit {channel_id}")
        for case in selected_audit_cases(args):
            if args.resume and (channel_id, case.name) in completed_cases:
                continue
            h_row = run_hspice_case(args.hspice.resolve(), audit_touchstone, nports, audit_dir, case, args.sim_timeout)
            ng_dir = audit_dir / "ngspice"
            ng_rows = run_ngspice_cases(args.ngspice.resolve(), selected_model, nports, ng_dir, [case], args.sim_timeout)
            ng_row = ng_rows[0] if ng_rows else {}
            corr: dict[str, object] = {
                "channel_id": channel_id,
                "source": row.get("source", ""),
                "source_family": row.get("source_family", ""),
                "validation_split": row.get("validation_split", ""),
                "channel_path": row.get("channel_path", ""),
                "ports": nports,
                "selected_candidate": row.get("selected_candidate", ""),
                "selected_candidate_family": row.get("selected_candidate_family", ""),
                "selected_fit_source": row.get("selected_fit_source", ""),
                "selected_use_scope": row.get("selected_use_scope", ""),
                "independent_trust_class": row.get("independent_trust_class", ""),
                "independent_warn_reasons": row.get("independent_warn_reasons", ""),
                "rx_selected_candidate": row.get("rx_selected_candidate", ""),
                "rx_trust_class": row.get("rx_trust_class", ""),
                "rx_voltage_shape_class": row.get("rx_voltage_shape_class", ""),
                "rx_voltage_shape_warn_reasons": row.get("rx_voltage_shape_warn_reasons", ""),
                "rx_timing_class": row.get("rx_timing_class", ""),
                "rx_timing_warn_reasons": row.get("rx_timing_warn_reasons", ""),
                "rx_ready_status": row.get("rx_ready_status", ""),
                "rx_warn_reasons": row.get("rx_warn_reasons", ""),
                "reflection_selected_candidate": row.get("reflection_selected_candidate", ""),
                "reflection_trust_class": row.get("reflection_trust_class", ""),
                "reflection_warn_reasons": row.get("reflection_warn_reasons", ""),
                "full_selected_candidate": row.get("full_selected_candidate", ""),
                "full_model_trust_class": row.get("full_model_trust_class", ""),
                "full_model_warn_reasons": row.get("full_model_warn_reasons", ""),
                "case": case.name,
                **h_row,
                "ngspice_raw": ng_row.get("raw", ""),
                "ngspice_log": ng_row.get("log", ""),
                "ngspice_return_code": ng_row.get("return_code", ""),
            }
            h_tr0 = Path(str(h_row.get("hspice_tr0", "")))
            if not h_tr0.is_absolute():
                h_tr0 = ROOT / h_tr0
            n_raw = Path(str(ng_row.get("raw", "")))
            if not n_raw.is_absolute():
                n_raw = ROOT / n_raw
            if h_tr0.exists() and n_raw.exists():
                corr.update(compare_hspice_ngspice(h_tr0, n_raw, nports))
                try:
                    overlay = channel_dir / "plots" / f"{case.name}_hspice_vs_ngspice.png"
                    plot_transient_overlay(h_tr0, n_raw, nports, overlay, f"{channel_id}: {case.name}")
                    corr["overlay_plot"] = rel(overlay)
                except Exception as exc:
                    corr["plot_error"] = str(exc)
            else:
                corr["correlation_status"] = "missing_raw"
            h_class, h_reason = classify_hspice_row(corr, args)
            corr["hspice_audit_class"] = h_class
            corr["hspice_audit_reason"] = h_reason
            rx_h_class, rx_h_reason = classify_hspice_row_view(corr, args, "rx")
            corr["rx_hspice_audit_class"] = rx_h_class
            corr["rx_hspice_audit_reason"] = rx_h_reason
            reflection_h_class, reflection_h_reason = classify_hspice_row_view(corr, args, "reflection")
            corr["reflection_hspice_audit_class"] = reflection_h_class
            corr["reflection_hspice_audit_reason"] = reflection_h_reason
            corr["full_model_hspice_audit_class"] = h_class
            corr["full_model_hspice_audit_reason"] = h_reason
            corr_rows.append(corr)
            completed_cases.add((channel_id, case.name))
        metrics = read_csv(study_dir / "metrics.csv") if (study_dir / "metrics.csv").exists() else []
        write_csv(corr_path, corr_rows)
        write_csv(study_dir / "calibration_summary.csv", calibration_summary_rows(ranking, corr_rows))
        write_audit_overlay_pdfs(study_dir, corr_rows)
        write_derived_summary_csvs(study_dir, metrics, ranking, corr_rows)
        write_report(study_dir, metrics, ranking, corr_rows)

    write_csv(corr_path, corr_rows)
    calibration = calibration_summary_rows(ranking, corr_rows)
    write_csv(study_dir / "calibration_summary.csv", calibration)
    write_audit_overlay_pdfs(study_dir, corr_rows)
    metrics = read_csv(study_dir / "metrics.csv") if (study_dir / "metrics.csv").exists() else []
    write_derived_summary_csvs(study_dir, metrics, ranking, corr_rows)
    audit_bbs_hspice(args, study_dir)
    write_report_from_files(study_dir)
    print(f"Wrote {corr_path}")
    print(f"Wrote {study_dir / 'calibration_summary.csv'}")
    return 0


def report_command(args: argparse.Namespace) -> int:
    return write_report_from_files(args.study_dir.resolve())


def write_report(study_dir: Path, metrics: list[dict[str, object]], ranking: list[dict[str, object]], corr: list[dict[str, object]]) -> None:
    selected = [row for row in ranking if row.get("status") == "selected"]
    failed = [row for row in ranking if row.get("status") != "selected"]
    ok_corr = [row for row in corr if row.get("correlation_status") == "ok"]
    trust_counts = {
        klass: sum(1 for row in selected if row.get("independent_trust_class") == klass)
        for klass in ("PASS", "WARN", "FAIL")
    }
    view_counts = {
        "rx": {klass: sum(1 for row in ranking if row.get("rx_trust_class") == klass) for klass in ("PASS", "WARN", "FAIL")},
        "rx_voltage_shape": {klass: sum(1 for row in ranking if row.get("rx_voltage_shape_class") == klass) for klass in ("PASS", "WARN", "FAIL")},
        "rx_timing": {klass: sum(1 for row in ranking if row.get("rx_timing_class") == klass) for klass in ("PASS", "WARN", "FAIL")},
        "reflection": {klass: sum(1 for row in ranking if row.get("reflection_trust_class") == klass) for klass in ("PASS", "WARN", "FAIL")},
        "full_model": {klass: sum(1 for row in ranking if row.get("full_model_trust_class") == klass) for klass in ("PASS", "WARN", "FAIL")},
    }
    family_counts: dict[str, dict[str, int]] = {}
    for row in metrics:
        family = str(row.get("candidate_family", "") or "unknown")
        klass = str(row.get("trust_class", "") or "UNCLASSIFIED")
        family_counts.setdefault(family, {})
        family_counts[family][klass] = family_counts[family].get(klass, 0) + 1
    source_counts: dict[str, dict[str, int]] = {}
    split_counts: dict[str, dict[str, int]] = {}
    for row in selected:
        source = str(row.get("source_family", "") or "unknown")
        split = str(row.get("validation_split", "") or "unsplit")
        klass = str(row.get("independent_trust_class", "") or "FAIL")
        source_counts.setdefault(source, {})
        source_counts[source][klass] = source_counts[source].get(klass, 0) + 1
        split_counts.setdefault(split, {})
        split_counts[split][klass] = split_counts[split].get(klass, 0) + 1
    calibration_path = study_dir / "calibration_summary.csv"
    calibration_rows = read_csv(calibration_path) if calibration_path.exists() else []
    family_summary_path = study_dir / "candidate_family_summary.csv"
    family_summary_rows = read_csv(family_summary_path) if family_summary_path.exists() else []
    warning_summary_path = study_dir / "warning_audit_summary.csv"
    warning_summary_rows = read_csv(warning_summary_path) if warning_summary_path.exists() else []
    view_summary_path = study_dir / "view_trust_summary.csv"
    view_summary_rows = read_csv(view_summary_path) if view_summary_path.exists() else []
    view_calibration_path = study_dir / "view_calibration_summary.csv"
    view_calibration_rows = read_csv(view_calibration_path) if view_calibration_path.exists() else []
    bbs_candidates_path = study_dir / "bbs_candidates.csv"
    bbs_candidates_rows = read_csv(bbs_candidates_path) if bbs_candidates_path.exists() else []
    bbs_smoke_path = study_dir / "bbs_ngspice_smoke.csv"
    bbs_smoke_rows = read_csv(bbs_smoke_path) if bbs_smoke_path.exists() else []
    bbs_corr_path = study_dir / "bbs_hspice_correlation.csv"
    bbs_corr_rows = read_csv(bbs_corr_path) if bbs_corr_path.exists() else []
    bbs_metric_rows = [row for row in metrics if str(row.get("candidate_family", "")).startswith("bbs_")]
    bbs_ranking_path = study_dir / "bbs_ranking.csv"
    bbs_ranking = read_csv(bbs_ranking_path) if bbs_ranking_path.exists() else bbs_ranking_rows(metrics, bbs_candidates_rows)
    bbs_share_rows = write_bbs_audit_share_pack(study_dir, [dict(row) for row in bbs_corr_rows]) if bbs_corr_rows else []
    lines = [
        "# ngspice S-parameter Trust Workflow",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        f"- Candidate metric rows: {len(metrics)}",
        f"- Selected channels: {len(selected)}",
        f"- Independent PASS/WARN/FAIL: {trust_counts['PASS']} / {trust_counts['WARN']} / {trust_counts['FAIL']}",
        f"- RX-through PASS/WARN/FAIL: {view_counts['rx']['PASS']} / {view_counts['rx']['WARN']} / {view_counts['rx']['FAIL']}",
        f"- RX voltage-shape PASS/WARN/FAIL: {view_counts['rx_voltage_shape']['PASS']} / {view_counts['rx_voltage_shape']['WARN']} / {view_counts['rx_voltage_shape']['FAIL']}",
        f"- RX timing PASS/WARN/FAIL: {view_counts['rx_timing']['PASS']} / {view_counts['rx_timing']['WARN']} / {view_counts['rx_timing']['FAIL']}",
        f"- Reflection PASS/WARN/FAIL: {view_counts['reflection']['PASS']} / {view_counts['reflection']['WARN']} / {view_counts['reflection']['FAIL']}",
        f"- Full-model PASS/WARN/FAIL: {view_counts['full_model']['PASS']} / {view_counts['full_model']['WARN']} / {view_counts['full_model']['FAIL']}",
        f"- Failed channels: {len(failed)}",
        f"- HSPICE correlation rows: {len(corr)}",
        f"- Successful HSPICE correlations: {len(ok_corr)}",
        f"- BBS extraction rows: {len(bbs_candidates_rows)}",
        f"- BBS candidate metric rows: {len(bbs_metric_rows)}",
        f"- BBS ngspice smoke rows: {len(bbs_smoke_rows)}",
        f"- BBS HSPICE audit rows: {len(bbs_corr_rows)}",
        "- HSPICE is optional audit data only; it is not used by `qualify` model selection.",
        "",
        "## Key Files",
        "",
        "- `manifest.csv`: Touchstone inventory",
        "- `metrics.csv`: HSPICE-independent fit/passivity metrics",
        "- `ngspice_smoke.csv`: ngspice transient smoke metrics",
        "- `ranking.csv`: selected model per channel",
        "- `selected_models/`: stable copies of selected ngspice-ready models",
        "- `selected_models/rx/`: scoped RX-through selected models when available",
        "- `selected_models/reflection/`: scoped reflection selected models when available",
        "- `selected_models/full/`: full multiport selected models when independently PASS",
        "- `hspice_correlation.csv`: optional HSPICE native S-element audit metrics",
        "- `calibration_summary.csv`: optional independent-trust vs HSPICE-audit confusion matrix",
        "- `view_trust_summary.csv`: RX/reflection/full readiness counts",
        "- `view_calibration_summary.csv`: optional view-level false-PASS calibration",
        "- `candidate_family_summary.csv`: candidate-family selection and audit outcomes",
        "- `warning_audit_summary.csv`: warning reason vs HSPICE audit outcomes",
        "- `audit_overlay_groups/`: optional grouped HSPICE-vs-ngspice overlay PDFs",
        "- `bbs_candidates.csv`: BroadbandSPICE extraction outputs",
        "- `bbs_ngspice_smoke.csv`: ngspice smoke metrics for BBS General SPICE models",
        "- `bbs_hspice_correlation.csv`: optional BBS HSPICE native S-element audit",
        "- `bbs_audit_share_pack/`: per-plotted-case BBS models, testbenches, outputs, and RX/TX plots",
        "- `bbs_audit_share_pack_index.csv`: index of the BBS share-pack files",
        "- `selected_models/bbs/`: archived BBS HSPICE and General SPICE netlists",
        "- `plots/bbs_overlays/`: BBS HSPICE-vs-ngspice overlays",
        "",
        "## Candidate Families",
        "",
    ]
    for family in sorted(family_counts):
        counts = family_counts[family]
        lines.append(
            f"- `{family}`: PASS `{counts.get('PASS', 0)}`, WARN `{counts.get('WARN', 0)}`, "
            f"FAIL `{counts.get('FAIL', 0)}`, unclassified `{counts.get('UNCLASSIFIED', 0)}`"
        )
    lines.extend(
        [
            "",
            "## Source Families",
            "",
        ]
    )
    for source in sorted(source_counts):
        counts = source_counts[source]
        lines.append(f"- `{source}`: PASS `{counts.get('PASS', 0)}`, WARN `{counts.get('WARN', 0)}`, FAIL `{counts.get('FAIL', 0)}`")
    if split_counts:
        lines.extend(["", "## Calibration Split", ""])
        for split in sorted(split_counts):
            counts = split_counts[split]
            lines.append(f"- `{split}`: PASS `{counts.get('PASS', 0)}`, WARN `{counts.get('WARN', 0)}`, FAIL `{counts.get('FAIL', 0)}`")
    if bbs_candidates_rows or bbs_metric_rows:
        bbs_extract_ok = sum(1 for row in bbs_candidates_rows if row.get("bbs_status") == "ok")
        bbs_gspice_ok = sum(1 for row in bbs_candidates_rows if row.get("bbs_status") == "ok" and row.get("bbs_circuit_type") == "gspice")
        bbs_hspice_ok = sum(1 for row in bbs_candidates_rows if row.get("bbs_status") == "ok" and row.get("bbs_circuit_type") == "hspice")
        bbs_class_counts = {
            klass: sum(1 for row in bbs_metric_rows if row.get("trust_class") == klass)
            for klass in ("PASS", "WARN", "FAIL")
        }
        bbs_audit_counts = {
            klass: sum(1 for row in bbs_corr_rows if row.get("hspice_audit_class") == klass)
            for klass in ("PASS", "WARN", "FAIL", "ERROR")
        }
        bbs_timeout_count = sum(1 for row in bbs_candidates_rows if str(row.get("bbs_timed_out", "")).lower() == "true")
        preset_counts: dict[str, dict[str, int]] = {}
        for row in bbs_candidates_rows:
            preset = str(row.get("bbs_preset", "") or "unknown")
            status = "ok" if row.get("bbs_status") == "ok" else "failed"
            preset_counts.setdefault(preset, {"ok": 0, "failed": 0, "timeout": 0})
            preset_counts[preset][status] += 1
            if str(row.get("bbs_timed_out", "")).lower() == "true":
                preset_counts[preset]["timeout"] += 1
        lines.extend(
            [
                "",
                "## Broadband SPICE Integration",
                "",
                f"- BBS extraction success: `{bbs_extract_ok}/{len(bbs_candidates_rows)}` rows",
                f"- BBS extraction timeouts: `{bbs_timeout_count}`",
                f"- BBS HSPICE-compatible outputs: `{bbs_hspice_ok}`",
                f"- BBS General SPICE outputs: `{bbs_gspice_ok}`",
                f"- BBS independent PASS/WARN/FAIL: `{bbs_class_counts['PASS']}/{bbs_class_counts['WARN']}/{bbs_class_counts['FAIL']}`",
                f"- BBS HSPICE audit P/W/F/E: `{bbs_audit_counts['PASS']}/{bbs_audit_counts['WARN']}/{bbs_audit_counts['FAIL']}/{bbs_audit_counts['ERROR']}`",
                f"- BBS audit share-pack cases: `{len(bbs_share_rows)}`",
                "- BBS remains a full-model candidate family; HSPICE audit results are reported separately and do not affect `qualify` ranking.",
            ]
        )
        if preset_counts:
            lines.extend(["", "### BBS Preset Extraction Summary", ""])
            for preset in sorted(preset_counts):
                counts = preset_counts[preset]
                lines.append(f"- `{preset}`: ok `{counts['ok']}`, failed `{counts['failed']}`, timeout `{counts['timeout']}`")
        if bbs_ranking:
            lines.extend(["", "### Best BBS Candidate Per Channel", ""])
            for row in bbs_ranking[:30]:
                lines.append(
                    f"- `{row.get('channel_id', '')}`: `{row.get('best_bbs_candidate', '') or 'none'}` "
                    f"({row.get('status', '')}), mode `{row.get('best_bbs_mode', '')}`, preset `{row.get('best_bbs_preset', '')}`, "
                    f"independent `{row.get('best_bbs_trust_class', '')}`, RX `{row.get('best_bbs_rx_trust_class', '')}`, "
                    f"reflection `{row.get('best_bbs_reflection_trust_class', '')}`, full `{row.get('best_bbs_full_model_trust_class', '')}`, "
                    f"ngspice pass `{row.get('best_bbs_ngspice_pass', '')}`, extractions `{row.get('successful_extractions', 0)}/{row.get('extraction_rows', 0)}`"
                )
        lines.extend(["", "### BBS Candidate Metric Rows", ""])
        for row in bbs_metric_rows[:20]:
            lines.append(
                f"- `{row.get('channel_id', '')}` `{row.get('candidate', '')}`: independent `{row.get('trust_class', '')}`, "
                f"RX `{row.get('rx_trust_class', '')}`, reflection `{row.get('reflection_trust_class', '')}`, "
                f"full `{row.get('full_model_trust_class', '')}`, wrapper `{row.get('spice_file', '')}`"
            )
        if bbs_corr_rows:
            lines.extend(["", "### BBS HSPICE Audit Overlays", ""])
            for row in bbs_corr_rows[:30]:
                lines.append(
                    f"- `{row.get('channel_id', '')}` `{row.get('candidate', '')}` `{row.get('case', '')}`: "
                    f"HSPICE audit `{row.get('hspice_audit_class', '')}`, RX `{row.get('rx_hspice_audit_class', '')}`, "
                    f"reflection `{row.get('reflection_hspice_audit_class', '')}`, "
                    f"RX active RMSE `{row.get('rx_active_rmse_v', '')}` V, TX active RMSE `{row.get('tx_active_rmse_v', '')}` V, "
                    f"rise delay delta `{row.get('rx_minus_tx_rise50_ps_delta_ps', '')}` ps, "
                    f"RX plot `{row.get('rx_overlay_plot', '')}`, TX plot `{row.get('tx_overlay_plot', '')}`"
                )
    if view_summary_rows:
        lines.extend(["", "## Path-Level Readiness", ""])
        lines.append(
            f"- `rx_voltage_shape`: pass `{view_counts['rx_voltage_shape']['PASS']}`, warn `{view_counts['rx_voltage_shape']['WARN']}`, fail `{view_counts['rx_voltage_shape']['FAIL']}`"
        )
        lines.append(
            f"- `rx_timing`: pass `{view_counts['rx_timing']['PASS']}`, warn `{view_counts['rx_timing']['WARN']}`, fail `{view_counts['rx_timing']['FAIL']}`"
        )
        for row in view_summary_rows:
            lines.append(
                f"- `{row.get('view', '')}`: ready `{row.get('ready', 0)}`, warn `{row.get('warn', 0)}`, fail `{row.get('fail', 0)}`, "
                f"selected models `{row.get('selected_models', 0)}`, HSPICE P/W/F/E "
                f"`{row.get('hspice_pass', 0)}/{row.get('hspice_warn', 0)}/{row.get('hspice_fail', 0)}/{row.get('hspice_error', 0)}`"
            )
    if calibration_rows:
        lines.extend(["", "## False-PASS Headline", ""])
        for row in calibration_rows:
            if row.get("independent_class") != "PASS":
                continue
            false_pass = row.get("false_pass_rate", "")
            false_text = "n/a" if false_pass == "" else f"{float(false_pass):.4g}"
            lines.append(
                f"- Split `{row.get('validation_split', 'all')}`: independent PASS total `{row.get('total', 0)}`, "
                f"HSPICE pass `{row.get('hspice_pass', 0)}`, warn `{row.get('hspice_warn', 0)}`, "
                f"fail `{row.get('hspice_fail', 0)}`, error `{row.get('hspice_error', 0)}`, false-PASS `{false_text}`"
            )
    if view_calibration_rows:
        lines.extend(["", "## View False-PASS Headline", ""])
        for row in view_calibration_rows:
            if row.get("independent_class") != "PASS":
                continue
            false_pass = row.get("false_pass_rate", "")
            false_text = "n/a" if false_pass == "" else f"{float(false_pass):.4g}"
            lines.append(
                f"- View `{row.get('view', '')}`, split `{row.get('validation_split', 'all')}`: independent PASS total `{row.get('total', 0)}`, "
                f"HSPICE pass `{row.get('hspice_pass', 0)}`, warn `{row.get('hspice_warn', 0)}`, "
                f"fail `{row.get('hspice_fail', 0)}`, error `{row.get('hspice_error', 0)}`, false-PASS `{false_text}`"
            )
    if family_summary_rows:
        lines.extend(["", "## Family Audit Outcomes", ""])
        for row in family_summary_rows[:20]:
            lines.append(
                f"- `{row.get('candidate_family', '')}`: selected `{row.get('selected_channels', 0)}`, "
                f"independent P/W/F `{row.get('selected_pass', 0)}/{row.get('selected_warn', 0)}/{row.get('selected_fail', 0)}`, "
                f"HSPICE P/W/F/E `{row.get('hspice_pass', 0)}/{row.get('hspice_warn', 0)}/{row.get('hspice_fail', 0)}/{row.get('hspice_error', 0)}`"
            )
    if warning_summary_rows:
        lines.extend(["", "## Warning Audit Outcomes", ""])
        for row in warning_summary_rows[:20]:
            lines.append(
                f"- `{row.get('warning_reason', '')}`: channels `{row.get('selected_channels', 0)}`, audit rows `{row.get('audit_rows', 0)}`, "
                f"HSPICE P/W/F/E `{row.get('hspice_pass', 0)}/{row.get('hspice_warn', 0)}/{row.get('hspice_fail', 0)}/{row.get('hspice_error', 0)}`"
            )
    lines.extend(
        [
            "",
        "## Selected Models",
        "",
        ]
    )
    for row in selected[:40]:
        lines.append(
            f"- `{row['channel_id']}`: `{row['selected_candidate']}` "
            f"({row.get('independent_trust_class', '')}, scope `{row.get('selected_use_scope', '')}`), "
            f"RX `{row.get('rx_ready_status', row.get('rx_trust_class', ''))}`, "
            f"RX-shape `{row.get('rx_voltage_shape_class', '')}`, RX-timing `{row.get('rx_timing_class', '')}`, "
            f"reflection `{row.get('reflection_ready_status', row.get('reflection_trust_class', ''))}`, "
            f"full `{row.get('full_model_ready_status', row.get('full_model_trust_class', ''))}`, "
            f"order `{row['selected_model_order']}`, RMS `{float(row['selected_fit_complex_rms']):.4g}`, "
            f"max SV `{float(row['selected_max_sv_high']):.4g}`, model `{row.get('selected_model_copy', '')}`"
        )
    if len(selected) > 40:
        lines.append(f"- ... {len(selected) - 40} more")
    if failed:
        lines.extend(["", "## Failed Channels", ""])
        for row in failed[:40]:
            lines.append(f"- `{row['channel_id']}`: {row.get('reason', row.get('status', 'failed'))}")
    if calibration_rows:
        lines.extend(["", "## HSPICE Calibration", ""])
        for row in calibration_rows:
            false_pass = row.get("false_pass_rate", "")
            suffix = "" if false_pass == "" else f", false-pass rate `{float(false_pass):.4g}`"
            lines.append(
                f"- Split `{row.get('validation_split', 'all')}`, independent `{row['independent_class']}`: HSPICE pass `{row['hspice_pass']}`, "
                f"warn `{row.get('hspice_warn', 0)}`, fail `{row['hspice_fail']}`, error `{row['hspice_error']}`, total `{row['total']}`{suffix}"
            )
    study_dir.mkdir(parents=True, exist_ok=True)
    (study_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report_from_files(study_dir: Path) -> int:
    metrics = read_csv(study_dir / "metrics.csv") if (study_dir / "metrics.csv").exists() else []
    ranking = read_csv(study_dir / "ranking.csv") if (study_dir / "ranking.csv").exists() else []
    corr = read_csv(study_dir / "hspice_correlation.csv") if (study_dir / "hspice_correlation.csv").exists() else []
    bbs_candidates = read_csv(study_dir / "bbs_candidates.csv") if (study_dir / "bbs_candidates.csv").exists() else []
    bbs_rows = bbs_metric_rows([dict(row) for row in metrics])
    if bbs_rows:
        write_csv(study_dir / "bbs_metrics.csv", bbs_rows)
    if bbs_candidates:
        write_csv(study_dir / "bbs_ranking.csv", bbs_ranking_rows([dict(row) for row in metrics], [dict(row) for row in bbs_candidates]))
    if corr and not (study_dir / "calibration_summary.csv").exists():
        write_csv(study_dir / "calibration_summary.csv", calibration_summary_rows(ranking, corr))
    if corr:
        write_audit_overlay_pdfs(study_dir, corr)
    write_derived_summary_csvs(study_dir, metrics, ranking, corr)
    write_report(study_dir, metrics, ranking, corr)
    print(f"Wrote {study_dir / 'README.md'}")
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY_DIR)
    parser.add_argument("--skrf-target", type=Path, default=None)


def add_inventory_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--skrf-tests-dir", type=Path, default=None)
    parser.add_argument("--extra-touchstone-dir", type=Path, action="append")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--no-skrf-tests", action="store_true")
    parser.add_argument("--no-repo-local", action="store_true")


def add_qualification_args(parser: argparse.ArgumentParser) -> None:
    add_inventory_args(parser)
    parser.add_argument("--ngspice", type=Path, default=Path(os.environ.get("NGSPICE_EXE", DEFAULT_NGSPICE)))
    parser.add_argument("--skip-ngspice", action="store_true")
    parser.add_argument("--enable-bbs", action="store_true", help="Generate BroadbandSPICE HSPICE/GSPICE models as first-class candidate artifacts.")
    parser.add_argument("--bbs-exe", type=Path, default=Path(os.environ.get("BBS_EXE", DEFAULT_BBS)))
    parser.add_argument("--bbs-modes", default="passivity2", help="Comma-separated BBS extraction modes, e.g. passivity2,precision.")
    parser.add_argument("--bbs-circuit-types", default="hspice,gspice", help="Comma-separated BBS output types, e.g. hspice,gspice.")
    parser.add_argument("--bbs-preset-grid", default="clean", help="Comma-separated BBS tuning presets, e.g. clean,reciprocity,lowfreq,smoothing.")
    parser.add_argument("--bbs-max-iter", type=int, default=200)
    parser.add_argument("--bbs-error", type=float, default=0.02)
    parser.add_argument("--bbs-config", type=Path, default=None, help="Optional BBS tuning config JSON. Omit for clean extraction.")
    parser.add_argument("--bbs-timeout", type=int, default=600, help="BroadbandSPICE extraction timeout per channel/mode/circuit-type.")
    parser.add_argument("--bbs-smoke-top-n", type=int, default=4, help="Run ngspice smoke only for the top N BBS GSPICE candidates per channel. Use 0 for all.")
    parser.add_argument("--max-channels", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="Skip channels already present in ranking.csv and append to existing CSV outputs.")
    parser.add_argument("--fast-calibration-profile", action="store_true", help="Use a faster global profile: reduced candidates for .s4p and a small vector/reduced set for .s2p.")
    parser.add_argument("--candidates", default=None, help="Comma-separated candidate names to run, e.g. vector_3r3c,reduced_s2p_rx_delayeq_rc_ring,reduced_4p_reflection_s11_rc.")
    parser.add_argument("--dense-samples", type=int, default=1001)
    parser.add_argument("--high-fmax", type=float, default=400e9)
    parser.add_argument("--min-edge-ps", type=float, default=5.0)
    parser.add_argument("--rms-threshold", type=float, default=0.02)
    parser.add_argument("--mag-db-max-threshold", type=float, default=1.0)
    parser.add_argument("--group-delay-rms-ps-threshold", type=float, default=2.0)
    parser.add_argument("--max-low-freq-start-hz", type=float, default=5e9)
    parser.add_argument("--min-frequency-points", type=int, default=8)
    parser.add_argument("--max-sv-high-threshold", type=float, default=1.05)
    parser.add_argument("--passivity-warn-sv", type=float, default=1.0)
    parser.add_argument("--pre-response-fail-v", type=float, default=0.05)
    parser.add_argument("--settling-fail-v", type=float, default=0.08)
    parser.add_argument("--overshoot-fail-pct", type=float, default=65.0)
    parser.add_argument("--overshoot-warn-pct", type=float, default=20.0)
    parser.add_argument("--pre-response-warn-pct", type=float, default=5.0)
    parser.add_argument("--settling-warn-pct", type=float, default=5.0)
    parser.add_argument("--min-smoke-swing-v", type=float, default=0.02)
    parser.add_argument("--min-delay-confidence-swing-v", type=float, default=0.02)
    parser.add_argument("--enforce-samples", type=int, default=2000)
    parser.add_argument("--skip-passivity-enforcement", action="store_true")
    parser.add_argument("--sim-timeout", type=int, default=180)
    parser.add_argument("--smoke-stop-ns", type=float, default=12.0)
    parser.add_argument("--audit-stop-ns", type=float, default=12.0)
    parser.add_argument("--reduced-fit-stop-ns", type=float, default=35.0)
    parser.add_argument("--reduced-fit-step-ps", type=float, default=10.0)
    parser.add_argument("--reduced-rc-taus-ns", default="0.03,0.08,0.2,0.7,2.5,8.0")
    parser.add_argument("--reduced-tail-pairs-ns", default="0.05:2.0,0.2:8.0")
    parser.add_argument("--reduced-ring-delays-ns", default="0,0.04,0.08,0.14,0.22")
    parser.add_argument("--reduced-ring-tau-pairs-ns", default="0.005:0.03,0.015:0.10,0.05:0.35")
    parser.add_argument("--reduced-reflect-taus-ns", default="0.01,0.03,0.08,0.2,0.7")
    parser.add_argument("--reduced-reflect-tail-pairs-ns", default="0.02:0.4,0.08:2.0")
    parser.add_argument("--reduced-fit-reg", type=float, default=0.01)
    parser.add_argument("--reduced-gain-bound", type=float, default=5.0)
    parser.add_argument("--combined-rx-shape-degradation-v", type=float, default=0.002, help="Maximum allowed RX shape-score degradation for combined RX+reflection reduced candidates.")


def add_hspice_audit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ranking", type=Path, default=None)
    parser.add_argument("--ngspice", type=Path, default=Path(os.environ.get("NGSPICE_EXE", DEFAULT_NGSPICE)))
    parser.add_argument("--hspice", type=Path, default=Path(os.environ.get("HSPICE_EXE", DEFAULT_HSPICE)))
    parser.add_argument("--max-channels", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="Skip channel/case audit rows already present in hspice_correlation.csv.")
    parser.add_argument("--retry-errors", action="store_true", help="With --resume, drop previous ERROR/missing_raw rows and rerun those channel/case audits.")
    parser.add_argument("--channel-id", action="append", help="Audit only these channel IDs. May be repeated or comma-separated.")
    parser.add_argument("--selected-family", action="append", help="Audit only selected candidate families. May be repeated or comma-separated.")
    parser.add_argument("--source-family", action="append", help="Audit only source families. May be repeated or comma-separated.")
    parser.add_argument("--validation-split", action="append", help="Audit only validation splits, e.g. calibration or holdout.")
    parser.add_argument("--rx-voltage-shape-class", action="append", help="Audit only rows with this independent RX voltage-shape class.")
    parser.add_argument("--rx-timing-class", action="append", help="Audit only rows with this independent RX timing class.")
    parser.add_argument("--rx-ready-status", action="append", help="Audit only rows with this independent RX readiness status.")
    parser.add_argument("--reflection-trust-class", action="append", help="Audit only rows with this independent reflection class.")
    parser.add_argument("--full-model-trust-class", action="append", help="Audit only rows with this independent full-model class.")
    parser.add_argument("--sim-timeout", type=int, default=180)
    parser.add_argument("--audit-stop-ns", type=float, default=12.0)
    parser.add_argument("--max-audit-cases", type=int, default=0, help="Limit audit cases per model; 0 runs all cases.")
    parser.add_argument("--bbs-audit-top-n", type=int, default=2, help="Audit the top N BBS GSPICE candidates per channel.")
    parser.add_argument("--hspice-rx-active-rmse-pass-v", type=float, default=0.02)
    parser.add_argument("--hspice-rx-active-maxabs-pass-v", type=float, default=0.075)
    parser.add_argument("--hspice-tx-active-rmse-pass-v", type=float, default=0.05)
    parser.add_argument("--hspice-delay-pass-ps", type=float, default=25.0)
    parser.add_argument("--hspice-min-delay-confidence-swing-v", type=float, default=0.02)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch S-parameter conversion quality study.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch-skrf-tests", help="Download scikit-rf master archive and extract skrf/tests Touchstone files.")
    add_common_args(p_fetch)
    p_fetch.add_argument("--github-ref", default="master")
    p_fetch.add_argument("--dest", type=Path, default=None)
    p_fetch.add_argument("--force", action="store_true")
    p_fetch.set_defaults(func=fetch_skrf_tests)

    p_inv = sub.add_parser("inventory", help="Inventory Touchstone files.")
    add_common_args(p_inv)
    add_inventory_args(p_inv)
    p_inv.set_defaults(func=inventory)

    p_qualify = sub.add_parser("qualify", help="Select ngspice-ready models using HSPICE-independent metrics only.")
    add_common_args(p_qualify)
    add_qualification_args(p_qualify)
    p_qualify.set_defaults(func=qualify_study)

    p_audit = sub.add_parser("audit-hspice", help="Optional development audit of selected models against HSPICE native S-elements.")
    add_common_args(p_audit)
    add_hspice_audit_args(p_audit)
    p_audit.set_defaults(func=audit_hspice)

    p_report = sub.add_parser("report", help="Regenerate README and calibration summary from existing CSV outputs.")
    add_common_args(p_report)
    p_report.set_defaults(func=report_command)

    p_run = sub.add_parser("run", help="Backward-compatible combined qualification command; use qualify + audit-hspice for the split workflow.")
    add_common_args(p_run)
    add_qualification_args(p_run)
    p_run.add_argument("--hspice", type=Path, default=Path(os.environ.get("HSPICE_EXE", DEFAULT_HSPICE)))
    p_run.add_argument("--skip-hspice", action="store_true")
    p_run.add_argument("--hspice-rx-active-rmse-pass-v", type=float, default=0.02)
    p_run.add_argument("--hspice-rx-active-maxabs-pass-v", type=float, default=0.075)
    p_run.add_argument("--hspice-tx-active-rmse-pass-v", type=float, default=0.05)
    p_run.add_argument("--hspice-delay-pass-ps", type=float, default=25.0)
    p_run.add_argument("--hspice-min-delay-confidence-swing-v", type=float, default=0.02)
    p_run.add_argument("--max-audit-cases", type=int, default=0, help="Limit audit cases per model; 0 runs all cases.")
    p_run.set_defaults(func=run_study)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
