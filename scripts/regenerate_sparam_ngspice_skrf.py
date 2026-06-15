from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import warnings
from pathlib import Path

import numpy as np
import skrf
from skrf.vectorFitting import VectorFitting


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_S2P = ROOT / "hspice" / "sparam" / "Clarity_example.S2P"
DEFAULT_OUT = ROOT / "hspice" / "sparam_ngspice" / "regenerated_skrf"


def max_singular_from_mats(mats: np.ndarray) -> dict[str, float]:
    singular = np.linalg.svd(mats, compute_uv=False)
    max_by_freq = singular[:, 0]
    idx = int(np.argmax(max_by_freq))
    return {
        "max_singular": float(max_by_freq[idx]),
        "index": idx,
    }


def fitted_s_matrices(vf: VectorFitting, freqs: np.ndarray) -> np.ndarray:
    nports = vf.network.nports
    mats = np.empty((len(freqs), nports, nports), dtype=complex)
    for i in range(nports):
        for j in range(nports):
            mats[:, i, j] = vf.get_model_response(i, j, freqs=freqs)
    return mats


def dense_singular_stats(vf: VectorFitting, f_stop: float, n: int) -> dict[str, float]:
    freqs = np.linspace(0.0, f_stop, n)
    stats = max_singular_from_mats(fitted_s_matrices(vf, freqs))
    stats["freq_hz"] = float(freqs[stats.pop("index")])
    stats["f_stop_hz"] = float(f_stop)
    stats["samples"] = n
    return stats


def passivity_bands(vf: VectorFitting) -> list[list[float]]:
    bands = vf.passivity_test()
    return np.asarray(bands, dtype=float).reshape((-1, 2)).tolist() if np.size(bands) else []


def describe_fit(vf: VectorFitting, fmax: float, dense_high_fmax: float) -> dict[str, object]:
    passive = vf.is_passive()
    bands = passivity_bands(vf)
    return {
        "rms_error": float(vf.get_rms_error()),
        "pole_count_array": int(len(vf.poles)),
        "model_order": int(VectorFitting.get_model_order(vf.poles)),
        "is_passive": bool(passive),
        "passivity_violation_bands_hz": bands,
        "dense_to_input_fmax": dense_singular_stats(vf, fmax, 1001),
        "dense_to_high_fmax": dense_singular_stats(vf, dense_high_fmax, 2001),
    }


def write_model(vf: VectorFitting, path: Path, name: str) -> None:
    vf.write_spice_subcircuit_s(str(path), fitted_model_name=name)


def fit_variant(name: str, nw: skrf.Network) -> tuple[VectorFitting, list[str]]:
    vf = VectorFitting(nw)
    caught: list[str] = []
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        if name == "auto_default":
            vf.auto_fit()
        elif name == "vector_3r3c":
            vf.vector_fit(n_poles_real=3, n_poles_cmplx=3)
        elif name == "vector_2r2c":
            vf.vector_fit()
        else:
            raise ValueError(f"unknown fit variant: {name}")
    caught.extend(str(record.message) for record in records)
    return vf, caught


def run(args: argparse.Namespace) -> int:
    s2p = args.s2p.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    nw = skrf.Network(str(s2p))
    sample_stats = max_singular_from_mats(nw.s)
    sample_freqs = nw.frequency.f
    fmax = float(sample_freqs[-1])
    sample_stats["freq_hz"] = float(sample_freqs[sample_stats.pop("index")])

    summary: dict[str, object] = {
        "scikit_rf_version": skrf.__version__,
        "input_s2p": str(s2p),
        "ports": int(nw.nports),
        "points": int(len(sample_freqs)),
        "frequency_min_hz": float(sample_freqs[0]),
        "frequency_max_hz": fmax,
        "network_is_passive_at_samples": bool(nw.is_passive()),
        "network_sample_singular": sample_stats,
        "dense_high_fmax_hz": float(args.high_fmax),
        "enforce_fmax_hz": float(args.enforce_fmax),
        "variants": {},
    }

    for variant in args.variants:
        vf, fit_warnings = fit_variant(variant, nw)
        variant_dir = out_dir / variant
        variant_dir.mkdir(parents=True, exist_ok=True)

        unforced_sp = variant_dir / f"Clarity_example_{variant}_unforced.sp"
        write_model(vf, unforced_sp, "s_equivalent")

        variant_summary: dict[str, object] = {
            "fit_warnings": fit_warnings,
            "unforced_spice": str(unforced_sp),
            "unforced": describe_fit(vf, fmax, args.high_fmax),
        }

        for label, enforce_fmax in (
            ("passive_input_band", fmax),
            ("passive_high_band", args.enforce_fmax),
        ):
            vf_enforced = copy.deepcopy(vf)
            enforce_warnings: list[str] = []
            with warnings.catch_warnings(record=True) as records:
                warnings.simplefilter("always")
                vf_enforced.passivity_enforce(
                    n_samples=args.enforce_samples,
                    f_max=enforce_fmax,
                    preserve_dc=True,
                )
            enforce_warnings.extend(str(record.message) for record in records)
            sp_path = variant_dir / f"Clarity_example_{variant}_{label}.sp"
            write_model(vf_enforced, sp_path, "s_equivalent")
            variant_summary[label] = {
                "enforce_fmax_hz": float(enforce_fmax),
                "enforce_samples": int(args.enforce_samples),
                "enforce_warnings": enforce_warnings,
                "spice": str(sp_path),
                "fit": describe_fit(vf_enforced, fmax, args.high_fmax),
            }

        summary["variants"][variant] = variant_summary

    summary_json = out_dir / "summary.json"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    summary_csv = out_dir / "summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "variant",
                "stage",
                "rms_error",
                "model_order",
                "is_passive",
                "violation_bands",
                "max_sv_input_band",
                "max_sv_input_band_freq_hz",
                "max_sv_high_band",
                "max_sv_high_band_freq_hz",
                "spice_file",
            ]
        )
        variants = summary["variants"]
        assert isinstance(variants, dict)
        for variant, data_obj in variants.items():
            data = data_obj
            assert isinstance(data, dict)
            rows = [("unforced", data["unforced"], data["unforced_spice"])]
            rows.extend(
                (stage, data[stage]["fit"], data[stage]["spice"])
                for stage in ("passive_input_band", "passive_high_band")
            )
            for stage, fit_obj, sp_path in rows:
                fit = fit_obj
                assert isinstance(fit, dict)
                input_stats = fit["dense_to_input_fmax"]
                high_stats = fit["dense_to_high_fmax"]
                assert isinstance(input_stats, dict)
                assert isinstance(high_stats, dict)
                writer.writerow(
                    [
                        variant,
                        stage,
                        fit["rms_error"],
                        fit["model_order"],
                        fit["is_passive"],
                        json.dumps(fit["passivity_violation_bands_hz"]),
                        input_stats["max_singular"],
                        input_stats["freq_hz"],
                        high_stats["max_singular"],
                        high_stats["freq_hz"],
                        sp_path,
                    ]
                )

    print(f"Loaded {s2p}")
    print(f"scikit-rf {skrf.__version__}")
    print(f"Network sample passive: {summary['network_is_passive_at_samples']}")
    print(
        "Network sampled max singular "
        f"{summary['network_sample_singular']['max_singular']:.9g} "
        f"at {summary['network_sample_singular']['freq_hz']:.9g} Hz"
    )
    print(f"Wrote {summary_json}")
    print(f"Wrote {summary_csv}")
    return 0


def positive_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("expected a positive finite float")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate scikit-rf S-parameter vector-fit SPICE models and check passivity."
    )
    parser.add_argument("--s2p", type=Path, default=DEFAULT_S2P)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--variant",
        dest="variants",
        action="append",
        choices=("auto_default", "vector_3r3c", "vector_2r2c"),
        help="Fit variant to run. Repeat to run multiple. Defaults to auto_default and vector_3r3c.",
    )
    parser.add_argument("--high-fmax", type=positive_float, default=400e9)
    parser.add_argument("--enforce-fmax", type=positive_float, default=400e9)
    parser.add_argument("--enforce-samples", type=int, default=2000)
    args = parser.parse_args()
    if args.variants is None:
        args.variants = ["auto_default", "vector_3r3c"]
    if args.enforce_samples <= 0:
        parser.error("--enforce-samples must be positive")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
