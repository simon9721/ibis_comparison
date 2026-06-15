from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

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


EDGES = (5, 50, 500)
SIGNALS = (("v(p1)", "Tx / input port"), ("v(p3)", "Rx / output port"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def channel_key(name: str) -> str:
    return re.sub(r"_(5F3N|8F)_t$", "_t", name)


def select_rows(rows: list[dict[str, str]], include_duplicates: bool) -> list[dict[str, str]]:
    if include_duplicates:
        return sorted(rows, key=lambda row: row.get("channel_name", ""))

    by_key: dict[str, dict[str, str]] = {}
    for row in rows:
        name = row.get("channel_name", "")
        key = channel_key(name)
        saved = by_key.get(key)
        if saved is None or ("5F3N" in name and "5F3N" not in saved.get("channel_name", "")):
            by_key[key] = row
    return sorted(by_key.values(), key=lambda row: row.get("channel_name", ""))


def case_name(edge_ps: int) -> str:
    return f"audit_amp1p5_edge{edge_ps}_r50"


def accepted_paths(row: dict[str, str], edge_ps: int) -> tuple[Path, Path]:
    out_dir = Path(row["out_dir"])
    label = row.get("accepted_label") or trim_label(float(row.get("accepted_trim_ps", "0")))
    case = case_name(edge_ps)
    hspice = out_dir / "hspice_native" / f"{case}_hspice.tr0"
    ngspice = out_dir / "trim_sweep" / label / "ngspice" / f"{case}.raw"
    return hspice, ngspice


def trim_label(trim_ps: float) -> str:
    if trim_ps < 0:
        return f"trim_m{abs(trim_ps):.0f}ps"
    if trim_ps > 0:
        return f"trim_p{trim_ps:.0f}ps"
    return "trim_p0ps"


def load_comparison_rows(row: dict[str, str]) -> dict[str, dict[str, str]]:
    out_dir = Path(row["out_dir"])
    label = row.get("accepted_label") or trim_label(float(row.get("accepted_trim_ps", "0")))
    csv_path = out_dir / "trim_sweep" / label / "comparison" / "comparison.csv"
    return {item["case"]: item for item in read_csv(csv_path)}


def plot_signal(ax, h: dict[str, np.ndarray], n: dict[str, np.ndarray], sig: str, title: str, threshold: str = "") -> None:
    ax.plot(h["time"] * 1e9, h[sig], color="#1f77b4", linewidth=1.7, label="HSPICE native S")
    ax.plot(n["time"] * 1e9, n[sig], color="#ff7f0e", linewidth=1.5, linestyle="--", label="ngspice optimized")
    if threshold:
        try:
            ax.axhline(float(threshold), color="#555555", linestyle=":", linewidth=0.9)
        except ValueError:
            pass
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold")
    ax.set_ylabel("V")
    ax.grid(True, color="#d7dde6", linewidth=0.8)
    ax.set_xlim(0, max(float(h["time"][-1]), float(n["time"][-1])) * 1e9)


def plot_channel(row: dict[str, str], out_dir: Path, pdf: PdfPages | None) -> Path:
    name = row["channel_name"]
    compare = load_comparison_rows(row)
    fig, axes = plt.subplots(len(EDGES), len(SIGNALS), figsize=(15.5, 10.5), sharex=True, constrained_layout=True)
    fig.suptitle(
        f"{name}: HSPICE native S vs ngspice optimized, accepted trim {row.get('accepted_trim_ps', '')} ps",
        fontsize=15,
        fontweight="bold",
    )

    for r_idx, edge in enumerate(EDGES):
        h_path, n_path = accepted_paths(row, edge)
        h = parse_hspice_tr0(h_path)
        n = parse_ngspice_raw(n_path)
        metrics = compare[case_name(edge)]
        for c_idx, (sig, label) in enumerate(SIGNALS):
            threshold_key = "hspice_tx_threshold_v" if sig == "v(p1)" else "hspice_rx_threshold_v"
            title = f"{edge} ps edge - {label}"
            if sig == "v(p3)":
                title += (
                    f" | RMSE {float(metrics['rx_active_rmse_v']) * 1e3:.2f} mV"
                    f", rise {float(metrics['rx_rise50_delta_ps']):.1f} ps"
                    f", fall {float(metrics['rx_fall50_delta_ps']):.1f} ps"
                )
            plot_signal(axes[r_idx, c_idx], h, n, sig, title, metrics.get(threshold_key, ""))

    for ax in axes[-1, :]:
        ax.set_xlabel("Time (ns)")
    axes[0, 1].legend(loc="upper right", frameon=False)

    path = out_dir / f"{name}_accepted_overlay.png"
    fig.savefig(path, dpi=170)
    if pdf is not None:
        pdf.savefig(fig)
    plt.close(fig)
    return path


def plot_overview(rows: list[dict[str, str]], out_dir: Path, suffix: str) -> Path:
    fig, axes = plt.subplots(len(rows), len(EDGES), figsize=(17.5, max(12.0, 2.0 * len(rows))), sharex=False, constrained_layout=True)
    if len(rows) == 1:
        axes = np.asarray([axes])
    fig.suptitle("Cisco strong-S31 accepted RX overlays: HSPICE native S vs ngspice optimized", fontsize=16, fontweight="bold")

    for r_idx, row in enumerate(rows):
        compare = load_comparison_rows(row)
        for c_idx, edge in enumerate(EDGES):
            ax = axes[r_idx, c_idx]
            h_path, n_path = accepted_paths(row, edge)
            h = parse_hspice_tr0(h_path)
            n = parse_ngspice_raw(n_path)
            metrics = compare[case_name(edge)]
            plot_signal(
                ax,
                h,
                n,
                "v(p3)",
                (
                    f"{row['channel_name']} - {edge} ps | "
                    f"RMSE {float(metrics['rx_active_rmse_v']) * 1e3:.1f} mV, "
                    f"rise {float(metrics['rx_rise50_delta_ps']):.1f} ps, "
                    f"fall {float(metrics['rx_fall50_delta_ps']):.1f} ps"
                ),
                metrics.get("hspice_rx_threshold_v", ""),
            )
            if r_idx != len(rows) - 1:
                ax.set_xlabel("")
    for ax in axes[-1, :]:
        ax.set_xlabel("Time (ns)")
    axes[0, 0].legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=8)

    path = out_dir / f"accepted_rx_overlay_overview_{suffix}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def write_report(out_dir: Path, rows: list[dict[str, str]], channel_plots: list[Path], overview: Path, pdf_path: Path, suffix: str) -> None:
    lines = [
        "# Cisco Accepted Overlay Plots",
        "",
        "These plots use each channel's accepted trim from the current batch summary.",
        "",
        f"- Channels plotted: `{len(rows)}`",
        f"- Overview PNG: `{overview.name}`",
        f"- Detailed PDF: `{pdf_path.name}`",
        "",
        "| channel | trim (ps) | max RX RMSE (V) | max RX maxabs (V) | max rise delta (ps) | max fall delta (ps) | plot |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    by_name = {path.stem.replace("_accepted_overlay", ""): path.name for path in channel_plots}
    for row in rows:
        lines.append(
            f"| `{row['channel_name']}` | {row.get('accepted_trim_ps', '')} | "
            f"{row.get('accepted_max_rx_active_rmse_v', '')} | {row.get('accepted_max_rx_active_maxabs_v', '')} | "
            f"{row.get('accepted_max_rx_rise50_delta_ps', '')} | {row.get('accepted_max_rx_fall50_delta_ps', '')} | "
            f"`{by_name.get(row['channel_name'], '')}` |"
        )
    (out_dir / f"README_{suffix}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create clear accepted HSPICE-vs-ngspice overlays for the Cisco batch.")
    parser.add_argument("--summary", type=Path, default=ROOT / "results" / "sparam_cisco_delay_parallel_batch_2026-06-08" / "batch_summary.csv")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "sparam_cisco_delay_parallel_batch_2026-06-08" / "clear_overlays")
    parser.add_argument("--include-duplicates", action="store_true", help="Include byte-identical 8F duplicate rows instead of plotting one representative per channel pair.")
    args = parser.parse_args()

    rows = [row for row in read_csv(args.summary.resolve()) if row.get("status") == "pass"]
    rows = select_rows(rows, args.include_duplicates)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    suffix = "all" if args.include_duplicates else "unique"
    pdf_path = args.out_dir / f"accepted_overlays_{suffix}.pdf"
    channel_plots: list[Path] = []
    with PdfPages(pdf_path) as pdf:
        for row in rows:
            channel_plots.append(plot_channel(row, args.out_dir, pdf))
    overview = plot_overview(rows, args.out_dir, suffix)
    write_report(args.out_dir, rows, channel_plots, overview, pdf_path, suffix)

    print(f"Wrote {overview}")
    print(f"Wrote {pdf_path}")
    print(f"Wrote {len(channel_plots)} per-channel PNGs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
