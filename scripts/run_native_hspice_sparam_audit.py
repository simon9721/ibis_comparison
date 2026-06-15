from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_hspice_tr0  # noqa: E402
from run_sparam_conversion_quality_study import (  # noqa: E402
    DEFAULT_HSPICE,
    SmokeCase,
    edge_crossings,
    rel,
    run_hspice_case,
    waveform_levels,
)


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


def hspice_metrics(tr0: Path, nports: int, amplitude_v: float) -> dict[str, object]:
    data = parse_hspice_tr0(tr0)
    tx_sig = "v(p1)"
    rx_sig = "v(p2)" if nports == 2 else "v(p3)"
    tx_low, tx_active, tx_threshold, tx_active_high = waveform_levels(data["time"], data[tx_sig])
    rx_low, rx_active, rx_threshold, rx_active_high = waveform_levels(data["time"], data[rx_sig])
    out: dict[str, object] = {
        "points": len(data["time"]),
        "stop_ns": float(data["time"][-1] * 1e9),
        "tx_min_v": float(np.nanmin(data[tx_sig])),
        "tx_max_v": float(np.nanmax(data[tx_sig])),
        "rx_min_v": float(np.nanmin(data[rx_sig])),
        "rx_max_v": float(np.nanmax(data[rx_sig])),
        "tx_low_v": tx_low,
        "tx_active_v": tx_active,
        "tx_threshold_v": tx_threshold,
        "rx_low_v": rx_low,
        "rx_active_v": rx_active,
        "rx_threshold_v": rx_threshold,
    }
    tx_rise, tx_fall = edge_crossings(data["time"], data[tx_sig], tx_threshold, tx_active_high)
    rx_rise, rx_fall = edge_crossings(data["time"], data[rx_sig], rx_threshold, rx_active_high)
    out["tx_rise50_ns"] = "" if tx_rise is None else tx_rise * 1e9
    out["rx_rise50_ns"] = "" if rx_rise is None else rx_rise * 1e9
    out["tx_fall50_ns"] = "" if tx_fall is None else tx_fall * 1e9
    out["rx_fall50_ns"] = "" if rx_fall is None else rx_fall * 1e9
    if tx_rise is not None and rx_rise is not None:
        out["rx_minus_tx_rise50_ps"] = (rx_rise - tx_rise) * 1e12
    if tx_fall is not None and rx_fall is not None:
        out["rx_minus_tx_fall50_ps"] = (rx_fall - tx_fall) * 1e12
    return out


def make_cases(stop_ns: float) -> list[SmokeCase]:
    return [
        SmokeCase("audit_amp1p5_edge5_r50", 50.0, 5.0, 1.5, stop_ns=stop_ns),
        SmokeCase("audit_amp1p5_edge50_r50", 50.0, 50.0, 1.5, stop_ns=stop_ns),
        SmokeCase("audit_amp1p5_edge500_r50", 50.0, 500.0, 1.5, stop_ns=stop_ns),
    ]


def lis_notes(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, object] = {}
    delay_match = re.search(r"delay estimation at S\[[^\]]+\]\[[^\]]+\]:\s*([0-9.eE+-]+)\s*sec", text)
    rms_match = re.search(r"Rational fitting RMS error\s*=\s*([0-9.eE+-]+)", text)
    pole_match = re.search(r"Rational fitting pole count\s*=\s*([0-9.eE+-]+)", text)
    passive = re.search(r"Rational model is passive|S[- ]?Parameters file is passive|S parameters are passive", text, re.IGNORECASE)
    if delay_match:
        out["lis_delay_estimate_s"] = float(delay_match.group(1))
    if rms_match:
        out["lis_rational_rms_error"] = float(rms_match.group(1))
    if pole_match:
        out["lis_rational_pole_count"] = int(float(pole_match.group(1)))
    out["lis_mentions_passive"] = bool(passive)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run native HSPICE S-element transient audit on one Touchstone file.")
    parser.add_argument("--touchstone", type=Path, required=True)
    parser.add_argument("--ports", type=int, default=4)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--hspice", type=Path, default=DEFAULT_HSPICE)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--stop-ns", type=float, default=12.0)
    parser.add_argument("--reuse-existing", action="store_true", help="Parse existing .tr0/.lis files instead of rerunning HSPICE when they are present.")
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for case in make_cases(args.stop_ns):
        prefix = args.out_dir.resolve() / f"{case.name}_hspice"
        if args.reuse_existing and prefix.with_suffix(".tr0").exists():
            row = {
                "case": case.name,
                "hspice_return_code": "reused",
                "hspice_tr0": rel(prefix.with_suffix(".tr0")),
                "hspice_lis": rel(prefix.with_suffix(".lis")),
            }
        else:
            row = run_hspice_case(args.hspice.resolve(), args.touchstone.resolve(), args.ports, args.out_dir.resolve(), case, args.timeout)
        tr0 = ROOT / str(row.get("hspice_tr0", ""))
        lis = ROOT / str(row.get("hspice_lis", ""))
        if tr0.exists():
            row.update(hspice_metrics(tr0, args.ports, case.amplitude_v))
        row.update(lis_notes(lis))
        rows.append(row)

    out_csv = args.out_dir.resolve() / "native_hspice_audit.csv"
    write_csv(out_csv, rows)
    print(out_csv)
    for row in rows:
        print(
            row["case"],
            "rc=",
            row.get("hspice_return_code"),
            "tr0=",
            bool((ROOT / str(row.get("hspice_tr0", ""))).exists()),
            "rise_delay_ps=",
            row.get("rx_minus_tx_rise50_ps", ""),
            "fit_rms=",
            row.get("lis_rational_rms_error", ""),
            "poles=",
            row.get("lis_rational_pole_count", ""),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
