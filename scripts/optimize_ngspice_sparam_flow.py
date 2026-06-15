from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_sparam_conversion_quality_study import (  # noqa: E402
    ensure_skrf,
    group_delay,
    max_singular_from_mats,
    rel,
    safe_id,
    through_pairs,
    touchstone_files,
    touchstone_port_count,
    z0_summary,
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float | object, digits: int = 4) -> str:
    try:
        val = float(value)  # type: ignore[arg-type]
    except Exception:
        return ""
    if not math.isfinite(val):
        return ""
    return f"{val:.{digits}g}"


def pair_label(i: int, j: int) -> str:
    return f"S{i + 1}{j + 1}"


def robust_delay(freqs: np.ndarray, response: np.ndarray) -> float:
    mag = np.abs(response)
    if len(freqs) < 3 or not np.any(np.isfinite(mag)):
        return float("nan")
    peak = float(np.nanmax(mag))
    if peak <= 0:
        return float("nan")
    mask = mag > max(1e-4, 0.10 * peak)
    if np.count_nonzero(mask) < 8:
        mask = mag > max(1e-5, 0.01 * peak)
    if np.count_nonzero(mask) < 3:
        return float("nan")
    gd = group_delay(freqs, response)
    gd = gd[mask]
    gd = gd[np.isfinite(gd)]
    return float(np.nanmedian(gd)) if len(gd) else float("nan")


def through_path_rows(freqs: np.ndarray, s: np.ndarray, nports: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for i, j in through_pairs(nports):
        response = s[:, i, j]
        mag = np.abs(response)
        peak = float(np.nanmax(mag)) if len(mag) else float("nan")
        low_mag = float(mag[0]) if len(mag) else float("nan")
        high_mag = float(mag[-1]) if len(mag) else float("nan")
        delay_s = robust_delay(freqs, response)
        rows.append(
            {
                "pair": pair_label(i, j),
                "to_port": i + 1,
                "from_port": j + 1,
                "peak_mag_db": 20 * math.log10(max(peak, 1e-30)),
                "low_freq_mag_db": 20 * math.log10(max(low_mag, 1e-30)),
                "high_freq_mag_db": 20 * math.log10(max(high_mag, 1e-30)),
                "delay_ns": delay_s * 1e9 if math.isfinite(delay_s) else float("nan"),
                "delay_s": delay_s,
            }
        )
    return rows


def choose_dominant_path(rows: list[dict[str, object]]) -> dict[str, object] | None:
    valid = [row for row in rows if math.isfinite(float(row.get("peak_mag_db", float("nan"))))]
    if not valid:
        return None
    return sorted(valid, key=lambda row: float(row["peak_mag_db"]), reverse=True)[0]


def delay_spread_ns(rows: list[dict[str, object]]) -> float:
    delays = [float(row["delay_ns"]) for row in rows if math.isfinite(float(row.get("delay_ns", float("nan"))))]
    if len(delays) < 2:
        return float("nan")
    return float(max(delays) - min(delays))


def recommended_route(row: dict[str, object], args: argparse.Namespace) -> tuple[str, str]:
    if row.get("status") != "ok":
        return "unsupported", str(row.get("status", "unsupported"))
    if row.get("sampled_is_passive") is False and float(row.get("sampled_max_sv", 0.0)) > args.max_touchstone_sv:
        return "touchstone_quality_first", "sampled Touchstone is non-passive beyond tolerance"
    delay_ns = float(row.get("dominant_delay_ns") or 0.0)
    cycles = float(row.get("delay_fmax_cycles") or 0.0)
    if delay_ns >= args.long_delay_ns and cycles >= args.long_delay_cycles:
        return "delay_aware_required", "long propagation delay creates too many phase wraps for direct vector-fit export"
    if cycles >= args.long_delay_cycles * 4:
        return "delay_aware_required", "very high delay-bandwidth product"
    return "direct_vector_fit", "short/low-complexity enough for direct vector-fit candidate search"


def analyze_touchstone(path: Path, args: argparse.Namespace) -> dict[str, object]:
    skrf, _ = ensure_skrf(args.skrf_target)
    row: dict[str, object] = {
        "channel_id": safe_id(path),
        "path": str(path.resolve()),
        "relative_path": rel(path),
        "ports_from_suffix": touchstone_port_count(path) or "",
        "bytes": path.stat().st_size,
    }
    try:
        nw = skrf.Network(str(path.resolve()))
        freqs = np.asarray(nw.frequency.f, dtype=float)
        if not len(freqs):
            row.update({"status": "no_frequency_data", "recommended_flow": "unsupported"})
            return row
        nports = int(nw.nports)
        supported = nports in (2, 4)
        row.update(
            {
                "status": "ok" if supported else "unsupported_v1",
                "supported_v1": supported,
                "ports": nports,
                "points": len(freqs),
                "f_min_hz": float(freqs[0]),
                "f_max_hz": float(freqs[-1]),
                "z0_summary": z0_summary(nw),
            }
        )
        if not supported:
            row["recommended_flow"] = "unsupported"
            return row
        s = np.asarray(nw.s, dtype=complex)
        sample_sv, sample_idx = max_singular_from_mats(s)
        row["sampled_max_sv"] = sample_sv
        row["sampled_max_sv_freq_hz"] = float(freqs[sample_idx])
        row["sampled_is_passive"] = bool(nw.is_passive())
        paths = through_path_rows(freqs, s, nports)
        dominant = choose_dominant_path(paths)
        if dominant:
            delay_ns = float(dominant.get("delay_ns", float("nan")))
            row["dominant_path"] = dominant["pair"]
            row["dominant_peak_mag_db"] = dominant["peak_mag_db"]
            row["dominant_low_freq_mag_db"] = dominant["low_freq_mag_db"]
            row["dominant_high_freq_mag_db"] = dominant["high_freq_mag_db"]
            row["dominant_delay_ns"] = delay_ns
            row["delay_fmax_cycles"] = delay_ns * 1e-9 * float(freqs[-1]) if math.isfinite(delay_ns) else float("nan")
            row["through_delay_spread_ns"] = delay_spread_ns(paths)
        row["through_paths_json"] = "; ".join(
            f"{path_row['pair']} peak={fmt(path_row['peak_mag_db'])}dB delay={fmt(path_row['delay_ns'])}ns"
            for path_row in paths
        )
        flow, reason = recommended_route(row, args)
        row["recommended_flow"] = flow
        row["route_reason"] = reason
        delay_ns = float(row.get("dominant_delay_ns") or 0.0)
        if flow == "direct_vector_fit":
            row["recommended_smoke_stop_ns"] = args.direct_stop_ns
            row["recommended_audit_stop_ns"] = args.direct_stop_ns
            row["recommended_candidates"] = args.direct_candidates
            row["ngspice_action"] = "run direct vector-fit candidate search, ngspice smoke, then HSPICE audit"
        elif flow == "delay_aware_required":
            row["recommended_smoke_stop_ns"] = max(args.direct_stop_ns, math.ceil(delay_ns + args.stop_margin_ns))
            row["recommended_audit_stop_ns"] = max(args.direct_stop_ns, math.ceil(delay_ns + args.stop_margin_ns))
            row["recommended_candidates"] = "none_as_final"
            row["ngspice_action"] = "skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit"
        else:
            row["recommended_smoke_stop_ns"] = ""
            row["recommended_audit_stop_ns"] = ""
            row["recommended_candidates"] = ""
            row["ngspice_action"] = "fix input data or add support before ngspice conversion"
    except Exception as exc:
        row.update({"status": "parse_error", "error": str(exc), "recommended_flow": "unsupported", "route_reason": "parse error"})
    return row


def collect_inputs(args: argparse.Namespace) -> list[Path]:
    seen: set[Path] = set()
    paths: list[Path] = []
    for item in args.touchstone or []:
        resolved = item.resolve()
        if resolved not in seen:
            seen.add(resolved)
            paths.append(resolved)
    for root in args.touchstone_dir or []:
        for path in touchstone_files(root.resolve()):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                paths.append(resolved)
    return paths


def write_report(path: Path, rows: list[dict[str, object]], args: argparse.Namespace) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        flow = str(row.get("recommended_flow", ""))
        counts[flow] = counts.get(flow, 0) + 1
    lines = [
        "# Optimized ngspice S-parameter Flow",
        "",
        "## Routing Rules",
        "",
        f"- Direct vector-fit route when dominant delay < `{args.long_delay_ns}` ns or delay-bandwidth product < `{args.long_delay_cycles}` cycles.",
        f"- Delay-aware route when both thresholds are exceeded.",
        f"- Direct-route transient stop stays at `{args.direct_stop_ns}` ns.",
        f"- Delay-aware transient stop is `dominant_delay_ns + {args.stop_margin_ns}` ns, minimum `{args.direct_stop_ns}` ns.",
        "",
        "## Summary",
        "",
    ]
    for flow, count in sorted(counts.items()):
        lines.append(f"- `{flow}`: {count}")
    lines.extend(
        [
            "",
            "## Channels",
            "",
            "| channel | ports | dominant path | delay (ns) | cycles at fmax | route | action |",
            "|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in rows[:200]:
        lines.append(
            f"| `{row.get('channel_id', '')}` | {row.get('ports', '')} | `{row.get('dominant_path', '')}` | "
            f"{fmt(row.get('dominant_delay_ns', ''))} | {fmt(row.get('delay_fmax_cycles', ''))} | "
            f"`{row.get('recommended_flow', '')}` | {row.get('ngspice_action', row.get('route_reason', ''))} |"
        )
    if len(rows) > 200:
        lines.append(f"| ... | | | | | | {len(rows) - 200} more channels in CSV |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_route_manifests(out_dir: Path, rows: list[dict[str, object]]) -> None:
    for flow in sorted({str(row.get("recommended_flow", "")) for row in rows if row.get("recommended_flow")}):
        flow_rows = [row for row in rows if row.get("recommended_flow") == flow]
        write_csv(out_dir / f"manifest_{flow}.csv", flow_rows)


def write_commands(out_dir: Path, args: argparse.Namespace) -> None:
    direct_manifest = out_dir / "manifest_direct_vector_fit.csv"
    delay_manifest = out_dir / "manifest_delay_aware_required.csv"
    lines = [
        "# Suggested commands from optimize_ngspice_sparam_flow.py",
        "",
        "$target = Join-Path $env:TEMP 'ibis_skrf_target'",
        "",
    ]
    if direct_manifest.exists():
        lines.extend(
            [
                "# Direct-route channels: run normal vector-fit/ngspice/HSPICE audit.",
                "py -3.14 scripts/run_sparam_conversion_quality_study.py run "
                f"--skrf-target $target --manifest {direct_manifest} "
                f"--study-dir {out_dir / 'direct_vector_fit_study'} "
                f"--candidates {args.direct_candidates} "
                f"--smoke-stop-ns {args.direct_stop_ns} --audit-stop-ns {args.direct_stop_ns}",
                "",
            ]
        )
    if delay_manifest.exists():
        lines.extend(
            [
                "# Delay-aware channels: do not accept direct vector-fit export as final.",
                "# Use the per-channel recommended_audit_stop_ns from manifest_delay_aware_required.csv",
                "# with run_native_hspice_sparam_audit.py and the delay-aware prototype until a delayed macromodel exporter is implemented.",
                "",
            ]
        )
    (out_dir / "suggested_commands.ps1").write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight S-parameter channels and choose the optimized ngspice conversion route.")
    parser.add_argument("--touchstone", type=Path, action="append")
    parser.add_argument("--touchstone-dir", type=Path, action="append")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--skrf-target", type=Path, default=None)
    parser.add_argument("--long-delay-ns", type=float, default=2.0)
    parser.add_argument("--long-delay-cycles", type=float, default=40.0)
    parser.add_argument("--max-touchstone-sv", type=float, default=1.05)
    parser.add_argument("--direct-stop-ns", type=float, default=12.0)
    parser.add_argument("--stop-margin-ns", type=float, default=20.0)
    parser.add_argument("--direct-candidates", default="auto_fit,vector_1r1c,vector_2r2c,vector_3r3c,vector_4r4c,vector_5r5c,vector_6r6c,vector_8r8c")
    args = parser.parse_args()

    paths = collect_inputs(args)
    if not paths:
        raise SystemExit("No Touchstone files found. Pass --touchstone or --touchstone-dir.")
    rows = []
    for idx, path in enumerate(paths, start=1):
        print(f"[{idx}/{len(paths)}] {path}")
        rows.append(analyze_touchstone(path, args))
    out_csv = args.out_dir.resolve() / "ngspice_flow_preflight.csv"
    write_csv(out_csv, rows)
    write_route_manifests(args.out_dir.resolve(), rows)
    write_report(args.out_dir.resolve() / "README.md", rows, args)
    write_commands(args.out_dir.resolve(), args)
    print(out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
