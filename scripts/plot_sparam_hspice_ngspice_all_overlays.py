from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
import re
import sys
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402


DEFAULT_STUDY_DIR = ROOT / "results" / "sparam_conversion_quality_2026-06-08"


def resolve_repo(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._") or "case"


def crossing(t: np.ndarray, y: np.ndarray, threshold: float, rise: bool, after: float) -> float | None:
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


def finite_values(*arrays: np.ndarray) -> np.ndarray:
    if not arrays:
        return np.array([0.0, 1.0])
    merged = np.concatenate([np.asarray(arr, dtype=float).reshape(-1) for arr in arrays])
    merged = merged[np.isfinite(merged)]
    return merged if merged.size else np.array([0.0, 1.0])


def signal_names(nports: int) -> tuple[str, str]:
    if nports == 4:
        return "v(p1)", "v(p3)"
    return "v(p1)", "v(p2)"


def setup_axis(ax: plt.Axes, title: str, xlim: tuple[float, float], ylim: tuple[float, float]) -> None:
    ax.set_title(title, loc="left", fontsize=10.5, fontweight="bold")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, which="major", color="#d7dde6", linewidth=0.8)
    ax.grid(True, which="minor", color="#eef1f5", linewidth=0.5)
    ax.minorticks_on()


def class_value(row: dict[str, str], key: str, fallback: str = "UNCLASSIFIED") -> str:
    value = row.get(key) or fallback
    return value.upper()


def class_color(value: str) -> str:
    value = value.upper()
    if value == "PASS":
        return "#167044"
    if value in ("FAIL", "NO_AUDIT"):
        return "#b02a2a"
    return "#5a5f69"


def wrapped(text: str, width: int = 70) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False)) if text else ""


def edge_margin_ns(case_name: str) -> float:
    match = re.search(r"edge(\d+)", case_name)
    edge_ps = float(match.group(1)) if match else 50.0
    return max(0.45, min(1.4, edge_ps * 0.003))


def edge_xlim(times_ns: list[float], fallback: tuple[float, float], margin: float) -> tuple[float, float]:
    vals = [value for value in times_ns if np.isfinite(value)]
    if not vals:
        return fallback
    return max(0.0, min(vals) - margin), max(vals) + margin


def plot_case(row: dict[str, str], out_png: Path) -> tuple[Path, plt.Figure]:
    nports = int(row.get("ports") or 2)
    tx_sig, rx_sig = signal_names(nports)
    h = parse_hspice_tr0(resolve_repo(row["hspice_tr0"]))
    n = parse_ngspice_raw(resolve_repo(row["ngspice_raw"]))

    ht = h["time"] * 1e9
    nt = n["time"] * 1e9
    htx, hrx = h[tx_sig], h[rx_sig]
    ntx, nrx = n[tx_sig], n[rx_sig]
    threshold = float(row.get("threshold_v") or 0.75)

    h_tx_r = crossing(h["time"], htx, threshold, True, 0.5e-9)
    h_rx_r = crossing(h["time"], hrx, threshold, True, 0.5e-9)
    n_tx_r = crossing(n["time"], ntx, threshold, True, 0.5e-9)
    n_rx_r = crossing(n["time"], nrx, threshold, True, 0.5e-9)
    h_tx_f = crossing(h["time"], htx, threshold, False, 8.5e-9)
    h_rx_f = crossing(h["time"], hrx, threshold, False, 8.5e-9)
    n_tx_f = crossing(n["time"], ntx, threshold, False, 8.5e-9)
    n_rx_f = crossing(n["time"], nrx, threshold, False, 8.5e-9)

    margin = edge_margin_ns(row["case"])
    rise_xlim = edge_xlim(
        [1e9 * t for t in (h_tx_r, h_rx_r, n_tx_r, n_rx_r) if t is not None],
        (0.8, 2.2),
        margin,
    )
    fall_xlim = edge_xlim(
        [1e9 * t for t in (h_tx_f, h_rx_f, n_tx_f, n_rx_f) if t is not None],
        (8.8, 10.4),
        margin,
    )
    full_xlim = (0.0, max(float(np.nanmax(ht)), float(np.nanmax(nt))))

    y_all = finite_values(htx, hrx, ntx, nrx)
    y_pad = max(0.05, 0.08 * (float(np.max(y_all)) - float(np.min(y_all)) or 1.0))
    ylim = float(np.min(y_all)) - y_pad, float(np.max(y_all)) + y_pad

    fig, axes = plt.subplots(2, 3, figsize=(15.5, 8.0), constrained_layout=True)
    metric_class = class_value(row, "metric_class")
    hspice_class = class_value(row, "hspice_case_class")
    edge_class = class_value(row, "edge_case_class", "UNCLASSIFIED")
    overall_class = class_value(row, "overall_case_class")
    fig.suptitle(
        f"{overall_class}: {row['channel_id']} | {row['case']} | Metric {metric_class} | Timing {hspice_class} | Edge {edge_class}",
        fontsize=14,
        fontweight="bold",
        color=class_color(overall_class),
    )
    panels = [
        ("Full Waveform", full_xlim, False),
        ("Rising Edge", rise_xlim, True),
        ("Falling Edge", fall_xlim, True),
    ]
    series = [
        ("Tx/Input Port", htx, ntx, tx_sig),
        ("Rx/Output Port", hrx, nrx, rx_sig),
    ]

    for r, (row_title, hy, ny, sig) in enumerate(series):
        for c, (panel_title, xlim, show_threshold) in enumerate(panels):
            ax = axes[r][c]
            ax.plot(ht, hy, color="#1f5a99", linewidth=1.9, label="HSPICE native S")
            ax.plot(nt, ny, color="#cf4337", linestyle="--", linewidth=1.7, label="ngspice converted")
            if show_threshold:
                ax.axhline(threshold, color="#555555", linestyle=":", linewidth=0.9, label=f"{threshold:.3g} V")
            setup_axis(ax, f"{row_title}: {panel_title}", xlim, ylim)
            if r == 0 and c == 0:
                ax.legend(loc="best", frameon=False, fontsize=9)

    metric_text = "\n".join(
        [
            f"Metric: {metric_class}",
            f"Timing audit: {hspice_class}",
            f"Edge audit: {edge_class}",
            f"Rx RMSE: {float(row.get('rx_rmse_v') or 0):.4g} V",
            f"Rx max abs: {float(row.get('rx_maxabs_v') or 0):.4g} V",
            f"Rise delay delta: {float(row.get('rx_minus_tx_rise50_ps_delta_ps') or 0):.4g} ps",
            f"Fall delay delta: {float(row.get('rx_minus_tx_fall50_ps_delta_ps') or 0):.4g} ps",
            wrapped(row.get("metric_reason", ""), 58),
            wrapped(row.get("hspice_case_reason", ""), 58),
            wrapped(row.get("edge_case_reason", ""), 58),
        ]
    )
    axes[1][0].text(
        0.02,
        0.04,
        metric_text,
        transform=axes[1][0].transAxes,
        fontsize=9,
        va="bottom",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cfd7e3", "alpha": 0.92},
    )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=170)
    return out_png, fig


def write_summary_page(pdf: PdfPages, rows: list[dict[str, str]]) -> None:
    metric_counts = Counter(class_value(row, "metric_class") for row in rows)
    hspice_counts = Counter(class_value(row, "hspice_case_class", "NO_AUDIT") for row in rows)
    edge_counts = Counter(class_value(row, "edge_case_class", "NO_AUDIT") for row in rows)
    overall_counts = Counter(class_value(row, "overall_case_class", "NO_AUDIT") for row in rows)
    lines = [
        "HSPICE vs ngspice Overlay Classification",
        "",
        "Case counts:",
        f"  Overall PASS: {overall_counts.get('PASS', 0)}",
        f"  Overall FAIL: {overall_counts.get('FAIL', 0)}",
        f"  Overall NO_AUDIT: {overall_counts.get('NO_AUDIT', 0)}",
        "",
        "Independent metric:",
        f"  PASS: {metric_counts.get('PASS', 0)}",
        f"  FAIL: {metric_counts.get('FAIL', 0)}",
        "",
        "HSPICE timing audit:",
        f"  PASS: {hspice_counts.get('PASS', 0)}",
        f"  FAIL: {hspice_counts.get('FAIL', 0)}",
        f"  NO_AUDIT: {hspice_counts.get('NO_AUDIT', 0)}",
        "",
        "HSPICE edge audit:",
        f"  PASS: {edge_counts.get('PASS', 0)}",
        f"  FAIL: {edge_counts.get('FAIL', 0)}",
        f"  NO_AUDIT: {edge_counts.get('NO_AUDIT', 0)}",
        "",
        "Per-case verdicts:",
    ]
    for row in rows:
        lines.append(
            f"  {class_value(row, 'overall_case_class', 'NO_AUDIT'):8s}  "
            f"{row.get('channel_id', '')} / {row.get('case', '')}  "
            f"(metric {class_value(row, 'metric_class')}, timing {class_value(row, 'hspice_case_class', 'NO_AUDIT')}, edge {class_value(row, 'edge_case_class', 'NO_AUDIT')})"
        )

    fig = plt.figure(figsize=(11, 8.5), constrained_layout=True)
    fig.text(
        0.055,
        0.95,
        "\n".join(lines),
        va="top",
        ha="left",
        family="monospace",
        fontsize=9.5,
    )
    pdf.savefig(fig)
    plt.close(fig)


def write_index(path: Path, plotted: list[dict[str, str]], skipped: list[dict[str, str]], pdf_path: Path) -> None:
    lines = [
        "# HSPICE vs ngspice Overlay Index",
        "",
        f"Multipage PDF: [{pdf_path.name}]({pdf_path.name})",
        "",
        "## Plotted Cases",
        "",
        "| Channel | Case | Candidate | Metric | Timing | Edge | Overall | Rx RMSE (V) | Rx Max Abs (V) | Rise Delay Delta (ps) | Fall Delay Delta (ps) | Figure |",
        "|---|---|---:|---|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in plotted:
        fig = Path(row["figure"])
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['channel_id']}`",
                    f"`{row['case']}`",
                    f"`{row.get('candidate', '')}`",
                    f"`{class_value(row, 'metric_class')}`",
                    f"`{class_value(row, 'hspice_case_class')}`",
                    f"`{class_value(row, 'edge_case_class')}`",
                    f"`{class_value(row, 'overall_case_class')}`",
                    f"{float(row.get('rx_rmse_v') or 0):.4g}",
                    f"{float(row.get('rx_maxabs_v') or 0):.4g}",
                    f"{float(row.get('rx_minus_tx_rise50_ps_delta_ps') or 0):.4g}",
                    f"{float(row.get('rx_minus_tx_fall50_ps_delta_ps') or 0):.4g}",
                    f"[{fig.name}]({fig.name})",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Skipped Cases", ""])
    if not skipped:
        lines.append("None.")
    else:
        lines.append("| Channel | Case | Candidate | Metric | Timing | Edge | Overall | Status | Note |")
        lines.append("|---|---|---:|---|---|---|---|---|---|")
        for row in skipped:
            note = row.get("skip_note") or row.get("correlation_status") or ""
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{row.get('channel_id', '')}`",
                        f"`{row.get('case', '')}`",
                        f"`{row.get('candidate', '')}`",
                        f"`{class_value(row, 'metric_class')}`",
                        f"`{class_value(row, 'hspice_case_class', 'NO_AUDIT')}`",
                        f"`{class_value(row, 'edge_case_class', 'NO_AUDIT')}`",
                        f"`{class_value(row, 'overall_case_class', 'NO_AUDIT')}`",
                        f"`{row.get('correlation_status', '')}`",
                        note.replace("|", "\\|"),
                    ]
                )
                + " |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate all HSPICE-vs-ngspice overlay figures for S-param study correlations.")
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY_DIR)
    parser.add_argument("--corr-csv", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    study_dir = args.study_dir.resolve()
    if args.corr_csv:
        corr_path = args.corr_csv.resolve()
    else:
        classified = study_dir / "hspice_correlation_classified.csv"
        corr_path = classified if classified.exists() else study_dir / "hspice_correlation.csv"
    out_dir = args.out_dir.resolve() if args.out_dir else study_dir / "plots" / "hspice_ngspice_overlays"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "all_hspice_ngspice_overlays.pdf"

    rows = list(csv.DictReader(corr_path.open(newline="", encoding="utf-8")))
    plotted: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    with PdfPages(pdf_path) as pdf:
        write_summary_page(pdf, rows)
        for row in rows:
            if row.get("correlation_status") != "ok":
                row["skip_note"] = "No complete HSPICE/ngspice raw pair for this audit case."
                skipped.append(row)
                continue
            h_path = resolve_repo(row.get("hspice_tr0", ""))
            n_path = resolve_repo(row.get("ngspice_raw", ""))
            if not h_path.exists() or not n_path.exists():
                row["skip_note"] = f"Missing file: hspice={h_path.exists()} ngspice={n_path.exists()}"
                skipped.append(row)
                continue
            out_png = out_dir / f"{safe_name(row['channel_id'])}__{safe_name(row['case'])}.png"
            try:
                _, fig = plot_case(row, out_png)
                pdf.savefig(fig)
                plt.close(fig)
                plotted.append({**row, "figure": rel(out_png)})
            except Exception as exc:
                row["skip_note"] = str(exc)
                skipped.append(row)

    write_index(out_dir / "README.md", plotted, skipped, pdf_path)
    write_rows = plotted + skipped
    with (out_dir / "overlay_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        fields: list[str] = []
        for row in write_rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(write_rows)

    print(f"Plotted {len(plotted)} cases")
    print(f"Skipped {len(skipped)} cases")
    print(out_dir / "README.md")
    print(pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
