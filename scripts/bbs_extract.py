#!/usr/bin/env python3
"""CLI/helper for Cadence Sigrity Broadband SPICE Touchstone extraction.

The wrapper runs BroadbandSPICE in batch mode around a generated Sigrity Python
script. It intentionally keeps tuning off by default so a clean run matches a
fresh GUI extraction unless a JSON tuning config is explicitly supplied.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any


MODE_MAP = {
    "passivity": "Passivity mode",
    "passivity2": "Passivity mode II",
    "passivity3": "Passivity mode III",
    "passivity4": "Passivity mode IV",
    "precision": "Precision mode",
}
CIRCUIT_MAP = {
    "hspice": "HSPICE Compatible",
    "gspice": "General SPICE Compatible",
    "spectre": "Spectre Compatible",
}
MATRIX_MAP = {
    "All": "All matrix entries",
    "Diagonal": "Diagonal matrix entries",
    "Upper": "Upper matrix entries",
    "Lower": "Lower matrix entries",
}
SMOOTH_FIT_MAP = {"mean": 0, "2nd": 1, "4th": 2}
RECIP_TYPES = {
    "Average",
    "Keep upper triangular matrix",
    "Keep lower triangular matrix",
}
EXE_CANDIDATES = [
    r"C:\Cadence\Sigrity2024.1\tools\bin\BroadbandSPICE.exe",
    r"C:\Cadence\Sigrity2023.1\tools\bin\BroadbandSPICE.exe",
    r"C:\Program Files\Cadence\Sigrity2024.1\tools\bin\BroadbandSPICE.exe",
    r"C:\Program Files\Cadence\Sigrity2023.1\tools\bin\BroadbandSPICE.exe",
]
TOUCHSTONE_GLOB = "*.s*p"

INIT_CONFIG: dict[str, Any] = {
    "_comment": "Delete any section to disable it. Values shown are defaults.",
    "reciprocity_enforcement": {
        "_comment": "Recover S_ij = S_ji symmetry.",
        "type": "Average",
    },
    "sparameter_smoothing": {
        "_comment": "matrix: All|Diagonal|Upper|Lower; fitting: mean|2nd|4th.",
        "matrix": "All",
        "fitting": "mean",
        "window_width": 2,
    },
    "low_frequency_extrapolation": {
        "_comment": "Extrapolate toward DC using the lowest N sampling points.",
        "sampling_points": 14,
    },
    "abandon_lower_frequency": {
        "_comment": "Discard data below this many MHz before extrapolation.",
        "below_mhz": 1.0,
    },
    "specify_dc_values": {
        "_comment": "Provide DC values from a separate Touchstone file.",
        "touchstone_file": "",
    },
    "interpolation": {
        "_comment": "Add sampling points adaptively.",
        "max_amplitude_change": 0.10,
        "max_phase_change": 45.0,
    },
    "causality_enforcement": {
        "_comment": "matrix: All|Diagonal|Upper|Lower.",
        "matrix": "All",
    },
}

_SCRIPT_HEAD = """\
import sigrity

bbsprj = sigrity.get_bbsproject()
bbsprj.load_sparameter_file(r'{spar_file}')

opt = bbsprj.BbsOptionSettings
opt.set_extraction_mode('{mode}')
opt.set_bbs_circuit_type('{ctype}')
opt.set_bbs_circuit_file(r'{circuit_file}')
opt.set_max_iterations({max_iter})
opt.set_highlight_errors({err})
{freq_line}
"""

_SCRIPT_TAIL = """\
ext = bbsprj.BbsExtractionManager
ext.start_original_sparameter_spice_circuit_extraction()

sigrity.exit(False)
"""


def parse_freq(text: str) -> tuple[float, str]:
    s = text.strip().replace(" ", "")
    for unit in ("GHz", "MHz", "KHz", "Hz"):
        if s.lower().endswith(unit.lower()):
            return float(s[: -len(unit)]), unit
    raise argparse.ArgumentTypeError(
        f"frequency {text!r} must end in Hz/KHz/MHz/GHz, e.g. 1.8GHz"
    )


def find_exe(override: str | Path | None = None) -> str:
    if override:
        p = Path(override)
        if not p.exists():
            raise FileNotFoundError(f"BroadbandSPICE executable does not exist: {p}")
        return str(p)
    for cand in EXE_CANDIDATES:
        if Path(cand).exists():
            return cand
    raise FileNotFoundError(
        "Could not auto-detect BroadbandSPICE.exe. Pass --exe C:\\path\\to\\BroadbandSPICE.exe"
    )


def collect_inputs(target: str | Path) -> list[Path]:
    p = Path(target).resolve()
    if p.is_dir():
        files = sorted(p.glob(TOUCHSTONE_GLOB))
        if not files:
            raise FileNotFoundError(f"no Touchstone files ({TOUCHSTONE_GLOB}) in {p}")
        return files
    if p.is_file():
        return [p]
    raise FileNotFoundError(f"not found: {p}")


def _matrix(scope: str, section: str) -> str:
    if scope not in MATRIX_MAP:
        raise ValueError(f"{section}.matrix must be one of {list(MATRIX_MAP)}; got {scope!r}")
    return MATRIX_MAP[scope]


def _clean_config(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _clean_config(v) for k, v in value.items() if not k.startswith("_comment")}
    return value


def load_config(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"--config not found: {p}")
    return _clean_config(json.loads(p.read_text(encoding="utf-8")))


def build_tuning_lines(cfg: dict[str, Any]) -> str:
    lines: list[str] = []
    if "reciprocity_enforcement" in cfg:
        t = cfg["reciprocity_enforcement"].get("type", "Average")
        if t not in RECIP_TYPES:
            raise ValueError(f"reciprocity_enforcement.type must be one of {sorted(RECIP_TYPES)}")
        lines += ["opt.enable_reciprocity_enforcement(True)", f"opt.set_reciprocity_enforcement_type('{t}')"]

    if "sparameter_smoothing" in cfg:
        s = cfg["sparameter_smoothing"]
        mat = _matrix(s.get("matrix", "All"), "sparameter_smoothing")
        fit = s.get("fitting", "mean")
        if fit not in SMOOTH_FIT_MAP:
            raise ValueError(f"sparameter_smoothing.fitting must be one of {list(SMOOTH_FIT_MAP)}")
        width = int(s.get("window_width", 2))
        lines += [
            "opt.enable_sparameter_smoothing_matrix(True)",
            f"opt.set_sparameter_smoothing_matrix_type('{mat}')",
            f"opt.set_sparameter_smoothing_fitting_type({SMOOTH_FIT_MAP[fit]})",
            f"opt.set_sparameter_smoothing_window_width({width})",
        ]

    if "low_frequency_extrapolation" in cfg:
        n = int(cfg["low_frequency_extrapolation"].get("sampling_points", 14))
        lines += ["opt.enable_low_frequency_extrapolation(True)", f"opt.set_low_frequency_extrapolation_sampling_points({n})"]

    if "abandon_lower_frequency" in cfg:
        mhz = float(cfg["abandon_lower_frequency"].get("below_mhz", 1.0))
        lines += ["opt.enable_abandon_sparameter_lower_frequency(True)", f"opt.set_abandon_sparameter_lower_frequency({mhz})"]

    if "specify_dc_values" in cfg:
        path = cfg["specify_dc_values"].get("touchstone_file", "").strip()
        if not path:
            raise ValueError("specify_dc_values.touchstone_file is required when that section is present")
        lines += [f"opt.set_dc_values_touchstone_file(r'{path.replace(chr(92), '/')}')"]

    if "interpolation" in cfg:
        i = cfg["interpolation"]
        amp = float(i.get("max_amplitude_change", 0.10))
        ph = float(i.get("max_phase_change", 45.0))
        lines += [
            "opt.enable_add_sampling_points_adaptively(True)",
            f"opt.set_max_amplitude_change({amp})",
            f"opt.set_max_phase_change({ph})",
        ]

    if "causality_enforcement" in cfg:
        mat = _matrix(cfg["causality_enforcement"].get("matrix", "All"), "causality_enforcement")
        lines += ["opt.enable_causality_enforcement(True)", f"opt.set_causality_enforcement_type('{mat}')"]
    return ("\n".join(lines) + "\n") if lines else ""


def build_script(
    spar_path: Path,
    circuit_file: Path,
    mode: str,
    circuit_type: str,
    max_iter: int,
    error: float,
    freq: tuple[float, str] | None,
    tuning_lines: str,
) -> str:
    if freq:
        value, unit = freq
        freq_line = f"opt.set_reduce_upper_frequency({{'MaxFreq': {value}, 'Unit': '{unit}'}})"
    else:
        freq_line = "# (no upper-frequency reduction; full file bandwidth)"
    return _SCRIPT_HEAD.format(
        spar_file=str(spar_path).replace("\\", "/"),
        circuit_file=str(circuit_file).replace("\\", "/"),
        mode=MODE_MAP[mode],
        ctype=CIRCUIT_MAP[circuit_type],
        max_iter=max_iter,
        err=error,
        freq_line=freq_line,
    ) + tuning_lines + _SCRIPT_TAIL


def expected_circuit_files(result_dir: Path, stem: str, requested_circuit_file: Path, circuit_type: str) -> list[Path]:
    candidates = {
        "hspice": [requested_circuit_file],
        "gspice": [result_dir / f"{stem}_GSPICE.txt", requested_circuit_file],
        "spectre": [
            result_dir / f"{stem}_SPECTRE.txt",
            result_dir / f"{stem}_Spectre.txt",
            result_dir / f"{stem}_spectre.txt",
            requested_circuit_file,
        ],
    }[circuit_type]
    seen: set[str] = set()
    out: list[Path] = []
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            out.append(path)
            seen.add(key)
    return out


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
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


def extract_one(
    exe: str,
    spar_path: Path,
    mode: str,
    circuit_type: str,
    max_iter: int,
    error: float,
    freq: tuple[float, str] | None = None,
    tuning_lines: str = "",
    keep_script: bool = False,
    timeout: int | None = None,
) -> dict[str, Any]:
    result_dir = spar_path.parent / f"BBSResult_{spar_path.stem}"
    result_dir.mkdir(exist_ok=True)
    requested_circuit = result_dir / f"{spar_path.stem}_BBSckt.txt"
    script = build_script(spar_path, requested_circuit, mode, circuit_type, max_iter, error, freq, tuning_lines)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(script)
        script_path = Path(tf.name)

    started = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            [exe, "-b", "-NoUI", "-py", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = -998
        stdout = (exc.stdout or "").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or "").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stderr = (stderr + f"\nBroadbandSPICE extraction timed out after {timeout} s").strip()
    finally:
        if not keep_script:
            try:
                script_path.unlink()
            except OSError:
                pass
    elapsed_s = max(0.0, time.perf_counter() - started)
    outputs = [p for p in expected_circuit_files(result_dir, spar_path.stem, requested_circuit, circuit_type) if p.exists()]
    generated = sorted(p for p in result_dir.glob("*") if p.is_file())
    fitted = next((p for p in generated if p.name.lower().endswith(f"_fitted.s{touchstone_port_count(spar_path) or ''}p")), None)
    if fitted is None:
        fitted = next((p for p in generated if "_fitted." in p.name.lower()), None)
    error_order = result_dir / "Error_Order.txt"
    return {
        "input": str(spar_path),
        "stem": spar_path.stem,
        "mode": mode,
        "mode_label": MODE_MAP[mode],
        "circuit_type": circuit_type,
        "circuit_type_label": CIRCUIT_MAP[circuit_type],
        "max_iter": max_iter,
        "error": error,
        "exe": exe,
        "return_code": return_code,
        "success": bool(outputs) and not timed_out,
        "timed_out": timed_out,
        "result_dir": str(result_dir),
        "circuit_file": str(outputs[0]) if outputs else "",
        "fitted_touchstone": str(fitted) if fitted else "",
        "error_order_file": str(error_order) if error_order.exists() else "",
        "generated_files": ";".join(str(p) for p in generated),
        "stdout": stdout.strip()[-4000:],
        "stderr": stderr.strip()[-4000:],
        "script_file": str(script_path) if keep_script else "",
        "elapsed_s": elapsed_s,
    }


def touchstone_port_count(path: Path) -> int | None:
    suffix = path.suffix.lower()
    if suffix.startswith(".s") and suffix.endswith("p"):
        try:
            return int(suffix[2:-1])
        except ValueError:
            return None
    return None


def run_extraction(
    target: str | Path,
    mode: str = "passivity",
    circuit_type: str = "hspice",
    max_iter: int = 200,
    error: float = 0.02,
    freq: tuple[float, str] | None = None,
    config: str | Path | None = None,
    exe: str | Path | None = None,
    manifest: str | Path | None = None,
    keep_script: bool = False,
    timeout: int | None = None,
) -> list[dict[str, Any]]:
    resolved_exe = find_exe(exe)
    tuning_lines = build_tuning_lines(load_config(config)) if config else ""
    rows = [
        extract_one(resolved_exe, path, mode, circuit_type, max_iter, error, freq, tuning_lines, keep_script, timeout)
        for path in collect_inputs(target)
    ]
    if manifest:
        write_manifest(Path(manifest), rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract SPICE subcircuits from S-parameter files via Broadband SPICE.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="a Touchstone file, or a folder of them")
    parser.add_argument("--mode", choices=MODE_MAP, default="passivity")
    parser.add_argument("--circuit-type", choices=CIRCUIT_MAP, default="hspice")
    parser.add_argument("--max-iter", type=int, default=200)
    parser.add_argument("--freq", type=parse_freq, default=None, metavar="N{Hz|KHz|MHz|GHz}")
    parser.add_argument("--error", type=float, default=0.02)
    parser.add_argument("--config", default=None)
    parser.add_argument("--init-config", metavar="PATH", default=None)
    parser.add_argument("--manifest", type=Path, default=None, help="write machine-readable extraction manifest CSV")
    parser.add_argument("--exe", default=None)
    parser.add_argument("--keep-script", action="store_true")
    parser.add_argument("--timeout", type=int, default=None, help="BroadbandSPICE extraction timeout in seconds")
    args = parser.parse_args()

    if args.init_config:
        out = Path(args.init_config)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(INIT_CONFIG, indent=2), encoding="utf-8")
        print(f"[ok] wrote starter config: {out}")
        return 0
    if not args.input:
        parser.error("input is required unless using --init-config")

    try:
        rows = run_extraction(
            args.input,
            mode=args.mode,
            circuit_type=args.circuit_type,
            max_iter=args.max_iter,
            error=args.error,
            freq=args.freq,
            config=args.config,
            exe=args.exe,
            manifest=args.manifest,
            keep_script=args.keep_script,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    print(f"[bbs] {sum(bool(row['success']) for row in rows)}/{len(rows)} succeeded")
    for row in rows:
        label = "ok" if row["success"] else "FAIL"
        print(f"[{label}] {Path(str(row['input'])).name} {row['mode']} {row['circuit_type']} -> {row['circuit_file']}")
    return 0 if all(bool(row["success"]) for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
