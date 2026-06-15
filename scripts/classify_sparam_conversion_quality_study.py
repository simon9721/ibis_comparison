from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUDY_DIR = ROOT / "results" / "sparam_conversion_quality_2026-06-08"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


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


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        value = row.get(key, "")
        return default if value in ("", None) else float(value)
    except (TypeError, ValueError):
        return default


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    try:
        value = row.get(key, "")
        return default if value in ("", None) else int(float(value))
    except (TypeError, ValueError):
        return default


def metric_reasons(row: dict[str, str], max_low_freq_start_hz: float, min_frequency_points: int) -> list[str]:
    reasons: list[str] = []
    points = as_int(row, "points")
    f_min = as_float(row, "f_min_hz", float("inf"))
    if points < min_frequency_points:
        reasons.append(f"too_few_frequency_points:{points}<{min_frequency_points}")
    if f_min > max_low_freq_start_hz:
        reasons.append(f"low_frequency_coverage:{f_min:.6g}>{max_low_freq_start_hz:.6g}Hz")
    if row.get("status") != "selected":
        reasons.append(row.get("reason") or row.get("status") or "no_selected_model")
    return reasons


def classify_metric(row: dict[str, str], max_low_freq_start_hz: float, min_frequency_points: int) -> tuple[str, str]:
    reasons = metric_reasons(row, max_low_freq_start_hz, min_frequency_points)
    if reasons:
        return "FAIL", "; ".join(reasons)
    return "PASS", "updated independent metric gates passed"


def hspice_waveform_reasons(row: dict[str, str], rx_rmse_pass_v: float, delay_pass_ps: float) -> list[str]:
    if row.get("correlation_status") != "ok":
        return [row.get("correlation_status") or "missing_raw"]
    reasons: list[str] = []
    rx_rmse = as_float(row, "rx_rmse_v", float("inf"))
    rise_delta = abs(as_float(row, "rx_minus_tx_rise50_ps_delta_ps", float("inf")))
    fall_delta = abs(as_float(row, "rx_minus_tx_fall50_ps_delta_ps", float("inf")))
    if rx_rmse > rx_rmse_pass_v:
        reasons.append(f"rx_rmse:{rx_rmse:.6g}>{rx_rmse_pass_v:.6g}V")
    if rise_delta > delay_pass_ps:
        reasons.append(f"rise_delay_delta:{rise_delta:.6g}>{delay_pass_ps:.6g}ps")
    if fall_delta > delay_pass_ps:
        reasons.append(f"fall_delay_delta:{fall_delta:.6g}>{delay_pass_ps:.6g}ps")
    return reasons


def classify_hspice(row: dict[str, str], rx_rmse_pass_v: float, delay_pass_ps: float) -> tuple[str, str]:
    reasons = hspice_waveform_reasons(row, rx_rmse_pass_v, delay_pass_ps)
    if row.get("correlation_status") != "ok":
        return "NO_AUDIT", "; ".join(reasons)
    if reasons:
        return "FAIL", "; ".join(reasons)
    return "PASS", "HSPICE/ngspice waveform thresholds passed"


def edge_reasons(row: dict[str, str], rx_rmse_pass_v: float, rx_maxabs_pass_v: float, delay_pass_ps: float) -> list[str]:
    if row.get("correlation_status") != "ok":
        return [row.get("correlation_status") or "missing_raw"]
    reasons: list[str] = []
    rx_rmse = as_float(row, "rx_rmse_v", float("inf"))
    rx_maxabs = as_float(row, "rx_maxabs_v", float("inf"))
    rise_delta = abs(as_float(row, "rx_minus_tx_rise50_ps_delta_ps", float("inf")))
    fall_delta = abs(as_float(row, "rx_minus_tx_fall50_ps_delta_ps", float("inf")))
    if rx_rmse > rx_rmse_pass_v:
        reasons.append(f"edge_rx_rmse:{rx_rmse:.6g}>{rx_rmse_pass_v:.6g}V")
    if rx_maxabs > rx_maxabs_pass_v:
        reasons.append(f"edge_rx_maxabs:{rx_maxabs:.6g}>{rx_maxabs_pass_v:.6g}V")
    if rise_delta > delay_pass_ps:
        reasons.append(f"edge_rise_delay_delta:{rise_delta:.6g}>{delay_pass_ps:.6g}ps")
    if fall_delta > delay_pass_ps:
        reasons.append(f"edge_fall_delay_delta:{fall_delta:.6g}>{delay_pass_ps:.6g}ps")
    return reasons


def classify_edge(row: dict[str, str], rx_rmse_pass_v: float, rx_maxabs_pass_v: float, delay_pass_ps: float) -> tuple[str, str]:
    reasons = edge_reasons(row, rx_rmse_pass_v, rx_maxabs_pass_v, delay_pass_ps)
    if row.get("correlation_status") != "ok":
        return "NO_AUDIT", "; ".join(reasons)
    if reasons:
        return "FAIL", "; ".join(reasons)
    return "PASS", "strict edge/ringing thresholds passed"


def write_markdown(
    path: Path,
    channel_rows: list[dict[str, object]],
    corr_rows: list[dict[str, object]],
    max_low_freq_start_hz: float,
    min_frequency_points: int,
    rx_rmse_pass_v: float,
    delay_pass_ps: float,
    edge_rx_rmse_pass_v: float,
    edge_rx_maxabs_pass_v: float,
    edge_delay_pass_ps: float,
) -> None:
    metric_counts = Counter(str(row["metric_class"]) for row in channel_rows)
    hspice_counts = Counter(str(row["hspice_channel_class"]) for row in channel_rows)
    edge_counts = Counter(str(row["edge_channel_class"]) for row in channel_rows)
    overall_counts = Counter(str(row["overall_channel_class"]) for row in channel_rows)
    lines = [
        "# Reclassified S-parameter Quality Results",
        "",
        "## Updated Gates",
        "",
        f"- Low-frequency coverage: first Touchstone point must be <= `{max_low_freq_start_hz:.6g}` Hz",
        f"- Minimum frequency points: `{min_frequency_points}`",
        f"- HSPICE timing pass: Rx RMSE <= `{rx_rmse_pass_v:.6g}` V and abs 50% delay deltas <= `{delay_pass_ps:.6g}` ps",
        f"- HSPICE edge pass: Rx RMSE <= `{edge_rx_rmse_pass_v:.6g}` V, Rx max abs <= `{edge_rx_maxabs_pass_v:.6g}` V, and abs 50% delay deltas <= `{edge_delay_pass_ps:.6g}` ps",
        "",
        "## Summary",
        "",
        f"- Metric PASS channels: {metric_counts.get('PASS', 0)}",
        f"- Metric FAIL channels: {metric_counts.get('FAIL', 0)}",
        f"- HSPICE timing channel PASS: {hspice_counts.get('PASS', 0)}",
        f"- HSPICE timing channel FAIL: {hspice_counts.get('FAIL', 0)}",
        f"- HSPICE timing NO_AUDIT channels: {hspice_counts.get('NO_AUDIT', 0)}",
        f"- HSPICE edge channel PASS: {edge_counts.get('PASS', 0)}",
        f"- HSPICE edge channel FAIL: {edge_counts.get('FAIL', 0)}",
        f"- HSPICE edge NO_AUDIT channels: {edge_counts.get('NO_AUDIT', 0)}",
        f"- Overall channel PASS: {overall_counts.get('PASS', 0)}",
        f"- Overall channel FAIL: {overall_counts.get('FAIL', 0)}",
        f"- Overall channel NO_AUDIT: {overall_counts.get('NO_AUDIT', 0)}",
        "",
        "## Channel Classification",
        "",
        "| Channel | Selected Model | Metric | Timing | Edge | Overall | Reason |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in channel_rows:
        reason = str(row.get("overall_channel_reason") or row.get("metric_reason") or row.get("hspice_channel_reason") or "").replace("|", "\\|")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['channel_id']}`",
                    f"`{row.get('selected_candidate', '')}`",
                    f"`{row['metric_class']}`",
                    f"`{row['hspice_channel_class']}`",
                    f"`{row['edge_channel_class']}`",
                    f"`{row['overall_channel_class']}`",
                    reason,
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## HSPICE Audit Cases",
            "",
            "| Channel | Case | Candidate | Metric | Timing | Edge | Overall | Rx RMSE (V) | Rx Max Abs (V) | Rise Delta (ps) | Fall Delta (ps) |",
            "|---|---|---|---|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in corr_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.get('channel_id', '')}`",
                    f"`{row.get('case', '')}`",
                    f"`{row.get('candidate', '')}`",
                    f"`{row.get('metric_class', '')}`",
                    f"`{row.get('hspice_case_class', '')}`",
                    f"`{row.get('edge_case_class', '')}`",
                    f"`{row.get('overall_case_class', '')}`",
                    f"{as_float(row, 'rx_rmse_v'):.4g}" if row.get("rx_rmse_v") else "",
                    f"{as_float(row, 'rx_maxabs_v'):.4g}" if row.get("rx_maxabs_v") else "",
                    f"{as_float(row, 'rx_minus_tx_rise50_ps_delta_ps'):.4g}" if row.get("rx_minus_tx_rise50_ps_delta_ps") else "",
                    f"{as_float(row, 'rx_minus_tx_fall50_ps_delta_ps'):.4g}" if row.get("rx_minus_tx_fall50_ps_delta_ps") else "",
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def classify(args: argparse.Namespace) -> int:
    study_dir = args.study_dir.resolve()
    ranking = read_csv(study_dir / "ranking.csv")
    corr = read_csv(study_dir / "hspice_correlation.csv")

    metric_by_channel: dict[str, tuple[str, str]] = {}
    ranking_rows: list[dict[str, object]] = []
    for row in ranking:
        metric_class, metric_reason = classify_metric(row, args.max_low_freq_start_hz, args.min_frequency_points)
        metric_by_channel[row["channel_id"]] = (metric_class, metric_reason)
        ranking_rows.append(
            {
                **row,
                "metric_class": metric_class,
                "metric_reason": metric_reason,
                "max_low_freq_start_hz": args.max_low_freq_start_hz,
                "min_frequency_points": args.min_frequency_points,
            }
        )

    corr_rows: list[dict[str, object]] = []
    corr_by_channel: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in corr:
        metric_class, metric_reason = metric_by_channel.get(row["channel_id"], ("FAIL", "not present in ranking.csv"))
        hspice_class, hspice_reason = classify_hspice(row, args.hspice_rx_rmse_pass_v, args.hspice_delay_pass_ps)
        edge_class, edge_reason = classify_edge(
            row,
            args.edge_rx_rmse_pass_v,
            args.edge_rx_maxabs_pass_v,
            args.edge_delay_pass_ps,
        )
        if metric_class != "PASS":
            overall_class = "FAIL"
        elif hspice_class == "PASS" and edge_class == "PASS":
            overall_class = "PASS"
        elif hspice_class == "NO_AUDIT" or edge_class == "NO_AUDIT":
            overall_class = "NO_AUDIT"
        else:
            overall_class = "FAIL"
        out = {
            **row,
            "metric_class": metric_class,
            "metric_reason": metric_reason,
            "hspice_case_class": hspice_class,
            "hspice_case_reason": hspice_reason,
            "edge_case_class": edge_class,
            "edge_case_reason": edge_reason,
            "overall_case_class": overall_class,
            "hspice_rx_rmse_pass_v": args.hspice_rx_rmse_pass_v,
            "hspice_delay_pass_ps": args.hspice_delay_pass_ps,
            "edge_rx_rmse_pass_v": args.edge_rx_rmse_pass_v,
            "edge_rx_maxabs_pass_v": args.edge_rx_maxabs_pass_v,
            "edge_delay_pass_ps": args.edge_delay_pass_ps,
        }
        corr_rows.append(out)
        corr_by_channel[row["channel_id"]].append(out)

    channel_rows: list[dict[str, object]] = []
    for row in ranking_rows:
        channel_id = str(row["channel_id"])
        cases = corr_by_channel.get(channel_id, [])
        h_counts = Counter(str(case["hspice_case_class"]) for case in cases)
        e_counts = Counter(str(case["edge_case_class"]) for case in cases)
        if not cases or h_counts.get("NO_AUDIT", 0) == len(cases):
            hspice_channel_class = "NO_AUDIT"
            hspice_reason = "no complete HSPICE/ngspice audit waveform pair"
        elif h_counts.get("FAIL", 0) or h_counts.get("NO_AUDIT", 0):
            hspice_channel_class = "FAIL"
            hspice_reason = "one or more HSPICE audit cases failed or were missing"
        else:
            hspice_channel_class = "PASS"
            hspice_reason = "all HSPICE audit cases passed"
        if not cases or e_counts.get("NO_AUDIT", 0) == len(cases):
            edge_channel_class = "NO_AUDIT"
            edge_reason = "no complete HSPICE/ngspice audit waveform pair"
        elif e_counts.get("FAIL", 0) or e_counts.get("NO_AUDIT", 0):
            edge_channel_class = "FAIL"
            edge_reason = "one or more strict edge audit cases failed or were missing"
        else:
            edge_channel_class = "PASS"
            edge_reason = "all strict edge audit cases passed"
        if row["metric_class"] != "PASS":
            overall_channel_class = "FAIL"
            overall_channel_reason = row["metric_reason"]
        elif hspice_channel_class == "PASS" and edge_channel_class == "PASS":
            overall_channel_class = "PASS"
            overall_channel_reason = "metric, timing, and strict edge audit passed"
        elif hspice_channel_class == "NO_AUDIT" or edge_channel_class == "NO_AUDIT":
            overall_channel_class = "NO_AUDIT"
            overall_channel_reason = "no complete HSPICE/ngspice audit waveform pair"
        else:
            overall_channel_class = "FAIL"
            overall_channel_reason = hspice_reason if hspice_channel_class == "FAIL" else edge_reason
        channel_rows.append(
            {
                **row,
                "hspice_case_count": len(cases),
                "hspice_case_pass_count": h_counts.get("PASS", 0),
                "hspice_case_fail_count": h_counts.get("FAIL", 0),
                "hspice_case_no_audit_count": h_counts.get("NO_AUDIT", 0),
                "hspice_channel_class": hspice_channel_class,
                "hspice_channel_reason": hspice_reason,
                "edge_case_pass_count": e_counts.get("PASS", 0),
                "edge_case_fail_count": e_counts.get("FAIL", 0),
                "edge_case_no_audit_count": e_counts.get("NO_AUDIT", 0),
                "edge_channel_class": edge_channel_class,
                "edge_channel_reason": edge_reason,
                "overall_channel_class": overall_channel_class,
                "overall_channel_reason": overall_channel_reason,
            }
        )

    summary_rows: list[dict[str, object]] = []
    for key, value in Counter(str(row["metric_class"]) for row in channel_rows).items():
        summary_rows.append({"category": "metric_channel_class", "class": key, "count": value})
    for key, value in Counter(str(row["hspice_channel_class"]) for row in channel_rows).items():
        summary_rows.append({"category": "hspice_channel_class", "class": key, "count": value})
    for key, value in Counter(str(row["edge_channel_class"]) for row in channel_rows).items():
        summary_rows.append({"category": "edge_channel_class", "class": key, "count": value})
    for key, value in Counter(str(row["overall_channel_class"]) for row in channel_rows).items():
        summary_rows.append({"category": "overall_channel_class", "class": key, "count": value})
    for key, value in Counter(str(row["hspice_case_class"]) for row in corr_rows).items():
        summary_rows.append({"category": "hspice_case_class", "class": key, "count": value})
    for key, value in Counter(str(row["edge_case_class"]) for row in corr_rows).items():
        summary_rows.append({"category": "edge_case_class", "class": key, "count": value})

    write_csv(study_dir / "ranking_reclassified.csv", channel_rows)
    write_csv(study_dir / "hspice_correlation_classified.csv", corr_rows)
    write_csv(study_dir / "correlation_summary_by_channel_reclassified.csv", channel_rows)
    write_csv(study_dir / "classification_summary.csv", summary_rows)
    write_markdown(
        study_dir / "README_reclassified.md",
        channel_rows,
        corr_rows,
        args.max_low_freq_start_hz,
        args.min_frequency_points,
        args.hspice_rx_rmse_pass_v,
        args.hspice_delay_pass_ps,
        args.edge_rx_rmse_pass_v,
        args.edge_rx_maxabs_pass_v,
        args.edge_delay_pass_ps,
    )

    print(f"Wrote {study_dir / 'ranking_reclassified.csv'}")
    print(f"Wrote {study_dir / 'hspice_correlation_classified.csv'}")
    print(f"Wrote {study_dir / 'README_reclassified.md'}")
    for row in summary_rows:
        print(f"{row['category']} {row['class']}: {row['count']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Reclassify S-parameter study results with updated metric and HSPICE audit thresholds.")
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY_DIR)
    parser.add_argument("--max-low-freq-start-hz", type=float, default=5e9)
    parser.add_argument("--min-frequency-points", type=int, default=8)
    parser.add_argument("--hspice-rx-rmse-pass-v", type=float, default=0.10)
    parser.add_argument("--hspice-delay-pass-ps", type=float, default=25.0)
    parser.add_argument("--edge-rx-rmse-pass-v", type=float, default=0.02)
    parser.add_argument("--edge-rx-maxabs-pass-v", type=float, default=0.075)
    parser.add_argument("--edge-delay-pass-ps", type=float, default=5.0)
    args = parser.parse_args()
    return classify(args)


if __name__ == "__main__":
    raise SystemExit(main())
