from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from run_sparam_conversion_quality_study import (  # noqa: E402
    common_grid_error,
    common_grid_error_active,
    edge_crossings,
    rel,
    waveform_levels,
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


def case_from_hspice(path: Path) -> str | None:
    match = re.fullmatch(r"(.+)_hspice\.tr0", path.name)
    return match.group(1) if match else None


def minmax(y: np.ndarray) -> tuple[float, float]:
    return float(np.nanmin(y)), float(np.nanmax(y))


def timing_fields(prefix: str, t: np.ndarray, tx: np.ndarray, rx: np.ndarray, tx_threshold: float, rx_threshold: float, tx_active_high: bool, rx_active_high: bool) -> dict[str, object]:
    tx_rise, tx_fall = edge_crossings(t, tx, tx_threshold, tx_active_high)
    rx_rise, rx_fall = edge_crossings(t, rx, rx_threshold, rx_active_high)
    row: dict[str, object] = {
        f"{prefix}_tx_rise50_ns": "" if tx_rise is None else tx_rise * 1e9,
        f"{prefix}_rx_rise50_ns": "" if rx_rise is None else rx_rise * 1e9,
        f"{prefix}_tx_fall50_ns": "" if tx_fall is None else tx_fall * 1e9,
        f"{prefix}_rx_fall50_ns": "" if rx_fall is None else rx_fall * 1e9,
    }
    if tx_rise is not None and rx_rise is not None:
        row[f"{prefix}_rx_minus_tx_rise50_ps"] = (rx_rise - tx_rise) * 1e12
    if tx_fall is not None and rx_fall is not None:
        row[f"{prefix}_rx_minus_tx_fall50_ps"] = (rx_fall - tx_fall) * 1e12
    return row


def classify(row: dict[str, object], rx_rmse_v: float, rx_maxabs_v: float, delay_ps: float, tx_rmse_v: float) -> tuple[str, str]:
    reasons: list[str] = []
    try:
        if float(row["rx_active_rmse_v"]) > rx_rmse_v:
            reasons.append("rx_active_rmse")
        if float(row["rx_active_maxabs_v"]) > rx_maxabs_v:
            reasons.append("rx_active_maxabs")
        rise_delta = row.get("rx_rise50_delta_ps", "")
        fall_delta = row.get("rx_fall50_delta_ps", "")
        if rise_delta == "":
            reasons.append("missing_rx_rise_delta")
        elif abs(float(rise_delta)) > delay_ps:
            reasons.append("rx_rise_delta")
        if fall_delta == "":
            reasons.append("missing_rx_fall_delta")
        elif abs(float(fall_delta)) > delay_ps:
            reasons.append("rx_fall_delta")
        if float(row["tx_active_rmse_v"]) > tx_rmse_v:
            reasons.append("tx_backdrive_or_input_mismatch")
    except Exception as exc:
        return "FAIL", f"metric_parse_error:{exc}"
    return ("PASS", "thresholds passed") if not reasons else ("FAIL", ";".join(reasons))


def plot_case(h: dict[str, np.ndarray], n: dict[str, np.ndarray], nports: int, path: Path, title: str, label_dut: str, row: dict[str, object]) -> None:
    rx_sig = "v(p2)" if nports == 2 else "v(p3)"
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 6.8), sharex=True, constrained_layout=True)
    for ax, sig, label, threshold_key in (
        (axes[0], "v(p1)", "Tx / input port", "hspice_tx_threshold_v"),
        (axes[1], rx_sig, "Rx / output port", "hspice_rx_threshold_v"),
    ):
        ax.plot(h["time"] * 1e9, h[sig], label="HSPICE native S", linewidth=1.9)
        ax.plot(n["time"] * 1e9, n[sig], "--", label=label_dut, linewidth=1.55)
        threshold = row.get(threshold_key, "")
        if threshold != "":
            ax.axhline(float(threshold), color="#555555", linestyle=":", linewidth=1)
        ax.set_title(label, loc="left", fontweight="bold")
        ax.set_ylabel("Voltage (V)")
        ax.grid(True, color="#d7dde6")
        ax.legend(frameon=False, loc="best")
    axes[1].set_xlabel("Time (ns)")
    fig.suptitle(title, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def compare_case(case: str, h_tr0: Path, n_raw: Path, nports: int, out_dir: Path, label_dut: str, args: argparse.Namespace) -> dict[str, object]:
    h = parse_hspice_tr0(h_tr0)
    n = parse_ngspice_raw(n_raw)
    tx_sig = "v(p1)"
    rx_sig = "v(p2)" if nports == 2 else "v(p3)"

    h_tx_low, h_tx_active, h_tx_threshold, h_tx_active_high = waveform_levels(h["time"], h[tx_sig])
    h_rx_low, h_rx_active, h_rx_threshold, h_rx_active_high = waveform_levels(h["time"], h[rx_sig])
    h_tx_min, h_tx_max = minmax(h[tx_sig])
    h_rx_min, h_rx_max = minmax(h[rx_sig])
    n_tx_min, n_tx_max = minmax(n[tx_sig])
    n_rx_min, n_rx_max = minmax(n[rx_sig])

    tx_rmse, tx_maxabs = common_grid_error(h["time"], h[tx_sig], n["time"], n[tx_sig])
    rx_rmse, rx_maxabs = common_grid_error(h["time"], h[rx_sig], n["time"], n[rx_sig])
    tx_active_rmse, tx_active_maxabs = common_grid_error_active(h["time"], h[tx_sig], n["time"], n[tx_sig], h_tx_low, h_tx_active)
    rx_active_rmse, rx_active_maxabs = common_grid_error_active(h["time"], h[rx_sig], n["time"], n[rx_sig], h_rx_low, h_rx_active)

    row: dict[str, object] = {
        "case": case,
        "hspice_tr0": rel(h_tr0),
        "ngspice_raw": rel(n_raw),
        "hspice_stop_ns": float(h["time"][-1] * 1e9),
        "ngspice_stop_ns": float(n["time"][-1] * 1e9),
        "hspice_tx_min_v": h_tx_min,
        "hspice_tx_max_v": h_tx_max,
        "ngspice_tx_min_v": n_tx_min,
        "ngspice_tx_max_v": n_tx_max,
        "hspice_rx_min_v": h_rx_min,
        "hspice_rx_max_v": h_rx_max,
        "ngspice_rx_min_v": n_rx_min,
        "ngspice_rx_max_v": n_rx_max,
        "hspice_tx_low_v": h_tx_low,
        "hspice_tx_active_v": h_tx_active,
        "hspice_tx_threshold_v": h_tx_threshold,
        "hspice_rx_low_v": h_rx_low,
        "hspice_rx_active_v": h_rx_active,
        "hspice_rx_threshold_v": h_rx_threshold,
        "tx_rmse_v": tx_rmse,
        "tx_maxabs_v": tx_maxabs,
        "tx_active_rmse_v": tx_active_rmse,
        "tx_active_maxabs_v": tx_active_maxabs,
        "rx_rmse_v": rx_rmse,
        "rx_maxabs_v": rx_maxabs,
        "rx_active_rmse_v": rx_active_rmse,
        "rx_active_maxabs_v": rx_active_maxabs,
        "ngspice_input_backdrive_flag": bool(n_tx_min < -0.25 or n_tx_max < 0.5 * h_tx_max),
    }
    row.update(timing_fields("hspice", h["time"], h[tx_sig], h[rx_sig], h_tx_threshold, h_rx_threshold, h_tx_active_high, h_rx_active_high))
    row.update(timing_fields("ngspice", n["time"], n[tx_sig], n[rx_sig], h_tx_threshold, h_rx_threshold, h_tx_active_high, h_rx_active_high))
    for key in ("tx_rise50_ns", "rx_rise50_ns", "tx_fall50_ns", "rx_fall50_ns"):
        hk = f"hspice_{key}"
        nk = f"ngspice_{key}"
        if row.get(hk, "") != "" and row.get(nk, "") != "":
            row[f"{key.replace('_ns', '')}_delta_ps"] = (float(row[nk]) - float(row[hk])) * 1e3
    for key in ("rx_minus_tx_rise50_ps", "rx_minus_tx_fall50_ps"):
        hk = f"hspice_{key}"
        nk = f"ngspice_{key}"
        if row.get(hk, "") != "" and row.get(nk, "") != "":
            row[f"{key}_delta_ps"] = float(row[nk]) - float(row[hk])
    row["case_class"], row["case_reason"] = classify(row, args.rx_active_rmse_pass_v, args.rx_active_maxabs_pass_v, args.delay_pass_ps, args.tx_active_rmse_pass_v)

    plot_path = out_dir / f"{case}_hspice_vs_ngspice.png"
    row["plot"] = rel(plot_path)
    plot_case(h, n, nports, plot_path, f"{case}: {row['case_class']}", label_dut, row)
    return row


def write_report(out_dir: Path, rows: list[dict[str, object]], args: argparse.Namespace) -> None:
    passed = [row for row in rows if row.get("case_class") == "PASS"]
    failed = [row for row in rows if row.get("case_class") != "PASS"]
    lines = [
        "# S-parameter Transient Audit Comparison",
        "",
        f"- HSPICE dir: `{rel(args.hspice_dir.resolve())}`",
        f"- ngspice dir: `{rel(args.ngspice_dir.resolve())}`",
        f"- Cases compared: {len(rows)}",
        f"- PASS: {len(passed)}",
        f"- FAIL: {len(failed)}",
        "",
        "## Thresholds",
        "",
        f"- RX active RMSE pass: `{args.rx_active_rmse_pass_v} V`",
        f"- RX active maxabs pass: `{args.rx_active_maxabs_pass_v} V`",
        f"- Incremental delay delta pass: `{args.delay_pass_ps} ps`",
        f"- TX active RMSE pass: `{args.tx_active_rmse_pass_v} V`",
        "",
        "## Cases",
        "",
        "| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | plot |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        rise = row.get("rx_rise50_delta_ps", "")
        fall = row.get("rx_fall50_delta_ps", "")
        rise_text = "" if rise == "" else f"{float(rise):.4g}"
        fall_text = "" if fall == "" else f"{float(fall):.4g}"
        lines.append(
            f"| `{row['case']}` | `{row['case_class']}` | "
            f"{float(row['rx_active_rmse_v']):.4g} | {float(row['rx_active_maxabs_v']):.4g} | "
            f"{rise_text} | {fall_text} | `{row['plot']}` |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare native HSPICE S-element transients against ngspice converted-model transients.")
    parser.add_argument("--hspice-dir", type=Path, required=True)
    parser.add_argument("--ngspice-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--ports", type=int, default=4)
    parser.add_argument("--label-dut", default="ngspice converted")
    parser.add_argument("--rx-active-rmse-pass-v", type=float, default=0.02)
    parser.add_argument("--rx-active-maxabs-pass-v", type=float, default=0.075)
    parser.add_argument("--tx-active-rmse-pass-v", type=float, default=0.05)
    parser.add_argument("--delay-pass-ps", type=float, default=25.0)
    args = parser.parse_args()

    h_cases = {
        case: path
        for path in args.hspice_dir.resolve().glob("*_hspice.tr0")
        for case in [case_from_hspice(path)]
        if case
    }
    rows: list[dict[str, object]] = []
    for case, h_tr0 in sorted(h_cases.items()):
        n_raw = args.ngspice_dir.resolve() / f"{case}.raw"
        if not n_raw.exists():
            rows.append({"case": case, "case_class": "FAIL", "case_reason": "missing_ngspice_raw", "hspice_tr0": rel(h_tr0), "ngspice_raw": rel(n_raw)})
            continue
        rows.append(compare_case(case, h_tr0, n_raw, args.ports, args.out_dir.resolve(), args.label_dut, args))

    out_csv = args.out_dir.resolve() / "comparison.csv"
    write_csv(out_csv, rows)
    write_report(args.out_dir.resolve(), rows, args)
    print(out_csv)
    for row in rows:
        print(row["case"], row["case_class"], row.get("case_reason", ""), "rx_active_rmse=", row.get("rx_active_rmse_v", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
