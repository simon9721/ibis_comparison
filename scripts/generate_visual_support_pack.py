from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
import shutil
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fnum(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "") or 0.0)
    except ValueError:
        return 0.0


def rel(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_artifact(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def case_sort_key(row: dict[str, str]) -> tuple[int, str, str]:
    case = row.get("case", "")
    edge_rank = 0
    if "edge50" in case:
        edge_rank = 0
    elif "edge5" in case:
        edge_rank = 1
    elif "edge500" in case:
        edge_rank = 2
    split_rank = 0 if row.get("validation_split") == "holdout" else 1
    return (split_rank, f"{edge_rank}", row.get("channel_id", ""))


def one_per_channel(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in sorted(rows, key=case_sort_key):
        channel = row.get("channel_id", "")
        overlay = resolve_artifact(row.get("overlay_plot", ""))
        if not channel or channel in seen or not overlay.exists():
            continue
        out.append(row)
        seen.add(channel)
        if len(out) >= limit:
            break
    return out


def status_label(row: dict[str, str]) -> str:
    if row.get("rx_voltage_shape_class") == "PASS" and row.get("rx_timing_class") == "WARN":
        return "RX_SHAPE_READY_TIMING_WARN"
    if row.get("rx_trust_class") == "PASS":
        return "RX_READY"
    return row.get("rx_ready_status") or row.get("rx_trust_class") or "UNKNOWN"


def short_channel(channel_id: str) -> str:
    if len(channel_id) <= 34:
        return channel_id
    return channel_id[:31] + "..."


def caption_for(row: dict[str, str], prefix: str = "") -> str:
    rmse_mv = 1000.0 * fnum(row, "rx_active_rmse_v")
    max_mv = 1000.0 * fnum(row, "rx_active_maxabs_v")
    lines = [
        prefix or status_label(row),
        f"{short_channel(row.get('channel_id', ''))} | {row.get('case', '')}",
        f"Independent RX shape/timing: {row.get('rx_voltage_shape_class', '')}/{row.get('rx_timing_class', '')}",
        f"HSPICE RX shape/timing: {row.get('rx_shape_hspice_audit_class', '')}/{row.get('rx_timing_hspice_audit_class', '')}",
        f"RX active RMSE {rmse_mv:.3g} mV, max {max_mv:.3g} mV",
    ]
    return "\n".join(lines)


def save_current_figure(fig: plt.Figure, path: Path, pdf: PdfPages | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    if pdf is not None:
        pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def plot_headline(
    out_dir: Path,
    ranking: list[dict[str, str]],
    corr: list[dict[str, str]],
    view_cal: list[dict[str, str]],
    pdf: PdfPages | None,
) -> Path:
    views = [
        ("RX shape", "rx_voltage_shape_class"),
        ("RX timing", "rx_timing_class"),
        ("RX combined", "rx_trust_class"),
        ("Reflection", "reflection_trust_class"),
        ("Full model", "full_model_trust_class"),
    ]
    counts = []
    for _, key in views:
        counter = Counter(row.get(key, "FAIL") or "FAIL" for row in ranking)
        counts.append([counter.get("PASS", 0), counter.get("WARN", 0), counter.get("FAIL", 0)])

    shape_pass = [
        row for row in view_cal
        if row.get("view") == "rx_voltage_shape"
        and row.get("validation_split") == "all"
        and row.get("independent_class") == "PASS"
    ]
    timing_pass = [
        row for row in view_cal
        if row.get("view") == "rx_timing"
        and row.get("validation_split") == "all"
        and row.get("independent_class") == "PASS"
    ]
    shape_total = int(float(shape_pass[0].get("total", "0") or 0)) if shape_pass else 0
    shape_hspice_pass = int(float(shape_pass[0].get("hspice_pass", "0") or 0)) if shape_pass else 0
    shape_false = shape_pass[0].get("false_pass_rate", "n/a") if shape_pass else "n/a"
    timing_total = int(float(timing_pass[0].get("total", "0") or 0)) if timing_pass else 0
    timing_hspice_warn = int(float(timing_pass[0].get("hspice_warn", "0") or 0)) if timing_pass else 0

    fig = plt.figure(figsize=(13.5, 7.2), facecolor="white")
    grid = fig.add_gridspec(2, 2, height_ratios=[3, 2], width_ratios=[2.2, 1.3], hspace=0.35, wspace=0.25)
    ax = fig.add_subplot(grid[:, 0])
    x = range(len(views))
    bottoms = [0] * len(views)
    colors = {"PASS": "#2e7d32", "WARN": "#f9a825", "FAIL": "#c62828"}
    for idx, klass in enumerate(("PASS", "WARN", "FAIL")):
        values = [row[idx] for row in counts]
        ax.bar(x, values, bottom=bottoms, label=klass, color=colors[klass], width=0.62)
        for pos, value, bottom in zip(x, values, bottoms):
            if value > 0:
                ax.text(pos, bottom + value / 2, str(value), ha="center", va="center", fontsize=11, color="white", weight="bold")
        bottoms = [b + v for b, v in zip(bottoms, values)]
    ax.set_xticks(list(x), [name for name, _ in views], rotation=20, ha="right")
    ax.set_ylabel("Channels")
    ax.set_title("Independent Readiness Split: Shape Is Improving, Full Model Is Not Ready", fontsize=14, weight="bold")
    ax.legend(loc="upper right")
    ax.grid(axis="y", color="#d8dee9", linewidth=0.8)
    ax.set_axisbelow(True)

    ax_text = fig.add_subplot(grid[0, 1])
    ax_text.axis("off")
    bullets = [
        f"RX shape independent PASS: {shape_hspice_pass}/{shape_total} HSPICE PASS",
        f"RX shape false-pass rate: {shape_false}",
        f"RX timing independent PASS: {timing_total} audited rows; {timing_hspice_warn} HSPICE WARN",
        "Combined RX_READY remains 0 by design",
        "Reflection and full-model claims remain blocked",
    ]
    ax_text.text(
        0.0,
        1.0,
        "Tomorrow's headline",
        fontsize=14,
        weight="bold",
        va="top",
    )
    ax_text.text(
        0.0,
        0.84,
        "\n".join(f"- {item}" for item in bullets),
        fontsize=11.5,
        va="top",
        linespacing=1.45,
    )

    ax_table = fig.add_subplot(grid[1, 1])
    ax_table.axis("off")
    audit_counter = Counter(row.get("hspice_audit_class", "ERROR") or "ERROR" for row in corr)
    table_rows = [
        ["HSPICE audit rows", len(corr)],
        ["Valid correlations", sum(1 for row in corr if row.get("correlation_status") == "ok")],
        ["Audit PASS / WARN / FAIL / ERROR", f"{audit_counter['PASS']} / {audit_counter['WARN']} / {audit_counter['FAIL']} / {audit_counter['ERROR']}"],
        ["Selected channels", sum(1 for row in ranking if row.get("status") == "selected")],
        ["Failed channels", sum(1 for row in ranking if row.get("status") != "selected")],
    ]
    table = ax_table.table(cellText=table_rows, colLabels=["Metric", "Value"], loc="center", cellLoc="left", colLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(10.5)
    table.scale(1.0, 1.55)
    for (row_idx, _), cell in table.get_celld().items():
        if row_idx == 0:
            cell.set_facecolor("#263238")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#f7f9fb" if row_idx % 2 else "white")

    path = out_dir / "01_headline_readiness.png"
    save_current_figure(fig, path, pdf)
    return path


def plot_view_calibration(out_dir: Path, view_cal: list[dict[str, str]], pdf: PdfPages | None) -> Path:
    views = ["rx_voltage_shape", "rx_timing", "rx", "reflection", "full_model"]
    pass_rows = {
        row.get("view", ""): row
        for row in view_cal
        if row.get("validation_split") == "all" and row.get("independent_class") == "PASS"
    }
    totals = [int(float(pass_rows.get(view, {}).get("total", "0") or 0)) for view in views]
    hpass = [int(float(pass_rows.get(view, {}).get("hspice_pass", "0") or 0)) for view in views]
    hwarn = [int(float(pass_rows.get(view, {}).get("hspice_warn", "0") or 0)) for view in views]
    hfail = [int(float(pass_rows.get(view, {}).get("hspice_fail", "0") or 0)) for view in views]

    fig, ax = plt.subplots(figsize=(12, 5.8), facecolor="white")
    x = range(len(views))
    bottom = [0] * len(views)
    for values, label, color in [
        (hpass, "HSPICE PASS", "#2e7d32"),
        (hwarn, "HSPICE WARN", "#f9a825"),
        (hfail, "HSPICE FAIL", "#c62828"),
    ]:
        ax.bar(x, values, bottom=bottom, label=label, color=color, width=0.58)
        bottom = [b + v for b, v in zip(bottom, values)]
    for i, total in enumerate(totals):
        ax.text(i, max(total, 0) + 0.3, f"n={total}", ha="center", fontsize=10)
    ax.set_xticks(list(x), [view.replace("_", " ") for view in views], rotation=18, ha="right")
    ax.set_ylabel("Rows with independent PASS")
    ax.set_title("Does Independent PASS Predict HSPICE?", fontsize=14, weight="bold")
    ax.legend()
    ax.grid(axis="y", color="#d8dee9", linewidth=0.8)
    ax.set_axisbelow(True)
    path = out_dir / "02_independent_pass_vs_hspice.png"
    save_current_figure(fig, path, pdf)
    return path


def plot_montage(
    rows: list[dict[str, str]],
    out_dir: Path,
    filename: str,
    title: str,
    prefix: str,
    pdf: PdfPages | None,
    cols: int = 2,
) -> Path | None:
    if not rows:
        return None
    rows = rows[:6]
    img_rows = (len(rows) + cols - 1) // cols
    fig, axes = plt.subplots(img_rows, cols, figsize=(15, 5.15 * img_rows), facecolor="white")
    if not isinstance(axes, (list, tuple)):
        axes_list = list(axes.flat) if hasattr(axes, "flat") else [axes]
    else:
        axes_list = list(axes)
    if hasattr(axes, "flat"):
        axes_list = list(axes.flat)
    fig.suptitle(title, fontsize=16, weight="bold", y=0.995)
    for ax, row in zip(axes_list, rows):
        overlay = resolve_artifact(row.get("overlay_plot", ""))
        image = mpimg.imread(overlay)
        ax.imshow(image)
        ax.axis("off")
        ax.set_title(caption_for(row, prefix=prefix), fontsize=9.2, loc="left")
    for ax in axes_list[len(rows):]:
        ax.axis("off")
    fig.subplots_adjust(top=0.94, hspace=0.38, wspace=0.18)
    path = out_dir / filename
    save_current_figure(fig, path, pdf)
    return path


def load_rx_waveforms(row: dict[str, str]) -> tuple[object, object, str]:
    h_path = resolve_artifact(row.get("hspice_tr0", ""))
    n_path = resolve_artifact(row.get("ngspice_raw", ""))
    nports = int(float(row.get("ports", "2") or 2))
    rx_sig = "v(p2)" if nports == 2 else "v(p3)"
    return parse_hspice_tr0(h_path), parse_ngspice_raw(n_path), rx_sig


def rx_zoom_limits(t_ns, yh, yn) -> tuple[float, float]:
    import numpy as np

    y = np.asarray(yh)
    t = np.asarray(t_ns)
    if len(t) == 0:
        return 0.0, 35.0
    baseline = float(np.nanmedian(y[: max(5, min(len(y), len(y) // 20))]))
    span = max(float(np.nanmax(np.abs(y - baseline))), float(np.nanmax(np.abs(np.asarray(yn) - baseline))), 1e-15)
    active = np.where(np.abs(y - baseline) > 0.08 * span)[0]
    if active.size == 0:
        return float(t[0]), float(t[-1])
    lo = max(float(t[0]), float(t[max(0, active[0] - 20)]) - 1.0)
    hi = min(float(t[-1]), float(t[min(len(t) - 1, active[-1] + 20)]) + 1.0)
    if hi - lo < 4.0:
        mid = 0.5 * (hi + lo)
        lo = max(float(t[0]), mid - 2.0)
        hi = min(float(t[-1]), mid + 2.0)
    return lo, hi


def plot_rx_zoom_grid(
    rows: list[dict[str, str]],
    out_dir: Path,
    filename: str,
    title: str,
    pdf: PdfPages | None,
    limit: int = 4,
) -> Path | None:
    import numpy as np

    rows = rows[:limit]
    if not rows:
        return None
    cols = 2
    img_rows = (len(rows) + cols - 1) // cols
    fig, axes = plt.subplots(img_rows, cols, figsize=(13.5, 4.4 * img_rows), facecolor="white")
    axes_list = list(axes.flat) if hasattr(axes, "flat") else [axes]
    fig.suptitle(title, fontsize=15, weight="bold", y=0.995)
    for ax, row in zip(axes_list, rows):
        try:
            h, n, rx_sig = load_rx_waveforms(row)
        except Exception as exc:
            ax.axis("off")
            ax.text(0.05, 0.5, f"Could not load waveform:\n{exc}", transform=ax.transAxes)
            continue
        th = h["time"] * 1e9
        tn = n["time"] * 1e9
        yh = h[rx_sig]
        yn = n[rx_sig]
        scale = 1000.0 if max(abs(float(np.nanmax(yh))), abs(float(np.nanmin(yh))), abs(float(np.nanmax(yn))), abs(float(np.nanmin(yn)))) < 0.02 else 1.0
        ylabel = "RX voltage (mV)" if scale == 1000.0 else "RX voltage (V)"
        lo, hi = rx_zoom_limits(th, yh, np.interp(th, tn, yn))
        ax.plot(th, yh * scale, label="HSPICE native S", linewidth=2.0, color="#1f77b4")
        ax.plot(tn, yn * scale, "--", label="ngspice converted", linewidth=1.8, color="#ff7f0e")
        ax.set_xlim(lo, hi)
        ax.grid(True, color="#d7dde6")
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Time (ns)")
        ax.set_title(
            f"{short_channel(row.get('channel_id', ''))} | {row.get('case', '')}\n"
            f"Independent {row.get('rx_voltage_shape_class', '')}/{row.get('rx_timing_class', '')}; "
            f"HSPICE {row.get('rx_shape_hspice_audit_class', '')}/{row.get('rx_timing_hspice_audit_class', '')}; "
            f"RMSE {1000 * fnum(row, 'rx_active_rmse_v'):.3g} mV",
            fontsize=9.5,
            loc="left",
        )
        ax.legend(frameon=False, fontsize=8.5)
    for ax in axes_list[len(rows):]:
        ax.axis("off")
    fig.subplots_adjust(top=0.88, hspace=0.55, wspace=0.22)
    path = out_dir / filename
    save_current_figure(fig, path, pdf)
    return path


def plot_rx_error_scatter(out_dir: Path, corr: list[dict[str, str]], pdf: PdfPages | None) -> Path:
    rows = [row for row in corr if row.get("correlation_status") == "ok"]
    colors = {"PASS": "#2e7d32", "WARN": "#f9a825", "FAIL": "#c62828"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), facecolor="white")
    for ax, zoom in ((axes[0], False), (axes[1], True)):
        for klass in ("PASS", "WARN", "FAIL"):
            xs = [1000.0 * fnum(row, "rx_active_rmse_v") for row in rows if row.get("rx_voltage_shape_class") == klass]
            ys = [1000.0 * fnum(row, "rx_active_maxabs_v") for row in rows if row.get("rx_voltage_shape_class") == klass]
            if xs:
                ax.scatter(xs, ys, s=52, alpha=0.78, label=f"Independent RX shape {klass}", color=colors[klass], edgecolors="white", linewidths=0.5)
        ax.axvline(20.0, color="#546e7a", linestyle="--", linewidth=1.2, label="RMSE pass limit 20 mV")
        ax.axhline(75.0, color="#78909c", linestyle=":", linewidth=1.2, label="Max error pass limit 75 mV")
        ax.set_xlabel("HSPICE audit RX active RMSE (mV)")
        ax.set_ylabel("HSPICE audit RX active max error (mV)")
        ax.grid(True, color="#d7dde6")
        ax.set_axisbelow(True)
        if zoom:
            ax.set_xlim(-0.01, 0.08)
            ax.set_ylim(-0.03, 0.55)
            ax.set_title("Zoom: RX-shape PASS cluster", fontsize=12, weight="bold")
        else:
            ax.set_title("Full audit error space", fontsize=12, weight="bold")
    axes[0].legend(fontsize=8.5, loc="upper left")
    fig.suptitle("RX Shape Class vs HSPICE Error: PASS Rows Stay Inside Limits", fontsize=14, weight="bold")
    fig.subplots_adjust(top=0.84, wspace=0.28)
    path = out_dir / "09_rx_shape_error_scatter.png"
    save_current_figure(fig, path, pdf)
    return path


def plot_io_buf_montage(io_dir: Path, out_dir: Path, pdf: PdfPages | None) -> Path | None:
    if not io_dir.exists():
        return None
    images = [
        ("Old IBIS, ngspice pybis vs refspice", io_dir / "01_ngspice_old_slow_io_buf_pybis_vs_refspice.png"),
        ("Old IBIS, HSPICE IBIS vs SPICE", io_dir / "02_hspice_old_slow_io_buf_ibis_vs_spice.png"),
        ("New IBIS, ngspice pybis vs refspice", io_dir / "03_ngspice_new_fast_io_buf_pybis_vs_refspice.png"),
        ("New IBIS, HSPICE IBIS vs SPICE", io_dir / "04_hspice_new_fast_io_buf_ibis_vs_spice.png"),
        ("New IBIS, all four curves", io_dir / "05_new_io_buf_all_four_ngspice_hspice_overlay.png"),
        ("pybis ngspice vs HSPICE IBIS", io_dir / "06_new_io_buf_ngspice_pybis_vs_hspice_ibis.png"),
    ]
    images = [(label, path) for label, path in images if path.exists()]
    if not images:
        return None
    fig, axes = plt.subplots(3, 2, figsize=(15, 16), facecolor="white")
    fig.suptitle("IO Buffer IBIS Edge-Rate Study: Old Slow IBIS vs New Fast IBIS", fontsize=16, weight="bold", y=0.995)
    for ax, (label, path) in zip(axes.flat, images):
        ax.imshow(mpimg.imread(path))
        ax.axis("off")
        ax.set_title(label, fontsize=10.5, loc="left")
    for ax in list(axes.flat)[len(images):]:
        ax.axis("off")
    path = out_dir / "00_io_buf_edge_rate_study.png"
    save_current_figure(fig, path, pdf)
    return path


def copy_examples(rows_by_group: dict[str, list[dict[str, str]]], out_dir: Path) -> list[dict[str, object]]:
    examples_dir = out_dir / "example_overlays"
    examples_dir.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict[str, object]] = []
    for group, rows in rows_by_group.items():
        group_dir = examples_dir / group
        group_dir.mkdir(parents=True, exist_ok=True)
        for row in rows:
            source = resolve_artifact(row.get("overlay_plot", ""))
            if not source.exists():
                continue
            dest_name = f"{row.get('channel_id', 'channel')}_{row.get('case', 'case')}.png"
            dest = group_dir / dest_name
            shutil.copy2(source, dest)
            rows_out.append({
                "group": group,
                "channel_id": row.get("channel_id", ""),
                "case": row.get("case", ""),
                "validation_split": row.get("validation_split", ""),
                "selected_candidate_family": row.get("selected_candidate_family", ""),
                "display_status": status_label(row),
                "independent_rx_shape": row.get("rx_voltage_shape_class", ""),
                "independent_rx_timing": row.get("rx_timing_class", ""),
                "hspice_rx_shape": row.get("rx_shape_hspice_audit_class", ""),
                "hspice_rx_timing": row.get("rx_timing_hspice_audit_class", ""),
                "hspice_audit_class": row.get("hspice_audit_class", ""),
                "rx_active_rmse_mv": 1000.0 * fnum(row, "rx_active_rmse_v"),
                "rx_active_maxabs_mv": 1000.0 * fnum(row, "rx_active_maxabs_v"),
                "copied_overlay": rel(dest, out_dir),
            })
    write_csv(out_dir / "visual_case_examples.csv", rows_out)
    return rows_out


def write_readme(
    out_dir: Path,
    study_dir: Path,
    io_dir: Path,
    figure_paths: list[Path],
    case_rows: list[dict[str, object]],
    ranking: list[dict[str, str]],
    corr: list[dict[str, str]],
    view_cal: list[dict[str, str]],
) -> None:
    def link(path: Path) -> str:
        return rel(path, out_dir)

    shape_pass = next(
        (
            row for row in view_cal
            if row.get("view") == "rx_voltage_shape"
            and row.get("validation_split") == "all"
            and row.get("independent_class") == "PASS"
        ),
        {},
    )
    holdout_shape = next(
        (
            row for row in view_cal
            if row.get("view") == "rx_voltage_shape"
            and row.get("validation_split") == "holdout"
            and row.get("independent_class") == "PASS"
        ),
        {},
    )
    timing_pass = next(
        (
            row for row in view_cal
            if row.get("view") == "rx_timing"
            and row.get("validation_split") == "all"
            and row.get("independent_class") == "PASS"
        ),
        {},
    )
    family_counter = Counter(row.get("selected_candidate_family", "") for row in corr)
    h_counter = Counter(row.get("hspice_audit_class", "") for row in corr)
    scoped_shape_ready = sum(
        1
        for row in ranking
        if row.get("rx_voltage_shape_class") == "PASS" and row.get("rx_timing_class") == "WARN"
    )
    lines = [
        "# Visual Support Pack",
        "",
        "This folder is a presentation-oriented summary of the latest ngspice/HSPICE S-parameter trust work plus the earlier IO buffer IBIS edge-rate study.",
        "",
        "## Headline",
        "",
        f"- Canonical S-parameter study: `{rel(study_dir, ROOT)}`",
        f"- IO buffer edge-rate study: `{rel(io_dir, ROOT)}`",
        f"- Selected S-parameter channels: `{sum(1 for row in ranking if row.get('status') == 'selected')}`",
        f"- HSPICE audit rows: `{len(corr)}`; valid waveform correlations: `{sum(1 for row in corr if row.get('correlation_status') == 'ok')}`",
        f"- HSPICE audit PASS/WARN/FAIL/ERROR: `{h_counter['PASS']}/{h_counter['WARN']}/{h_counter['FAIL']}/{h_counter['ERROR']}`",
        f"- RX voltage-shape independent PASS vs HSPICE PASS: `{shape_pass.get('hspice_pass', '0')}/{shape_pass.get('total', '0')}`",
        f"- Holdout RX voltage-shape PASS vs HSPICE PASS: `{holdout_shape.get('hspice_pass', '0')}/{holdout_shape.get('total', '0')}`",
        f"- RX timing independent PASS produced HSPICE WARN in `{timing_pass.get('hspice_warn', '0')}` of `{timing_pass.get('total', '0')}` audited rows",
        f"- Scoped shape-only status `RX_SHAPE_READY_TIMING_WARN`: `{scoped_shape_ready}` channels",
        "- Combined `RX_READY` remains `0`; full-model ready remains `0`.",
        "",
        "## Figures",
        "",
    ]
    for path in figure_paths:
        lines.append(f"- [{path.name}]({link(path)})")
    lines.extend([
        "",
        "## How To Read This",
        "",
        "- `RX_SHAPE_READY_TIMING_WARN` means the independent flow predicts RX waveform shape well, but threshold timing is not certified.",
        "- Reduced `.s4p` models are scoped to matched-50-ohm RX-through behavior; they are not full 4-port replacements.",
        "- HSPICE audit rows marked `ERROR` are missing native HSPICE `.tr0` data, not ngspice waveform mismatches.",
        "",
        "## Candidate Family Audit Rows",
        "",
    ])
    for family, count in sorted(family_counter.items()):
        lines.append(f"- `{family or 'unknown'}`: `{count}` audited rows")
    lines.extend([
        "",
        "## Example Overlay Index",
        "",
        "See `visual_case_examples.csv` for the exact channel/case list and copied overlay paths.",
        "",
    ])
    for row in case_rows[:30]:
        lines.append(
            f"- `{row['group']}`: `{row['channel_id']}` `{row['case']}` "
            f"status `{row['display_status']}`, HSPICE RX shape/timing "
            f"`{row['hspice_rx_shape']}/{row['hspice_rx_timing']}`, overlay `{row['copied_overlay']}`"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_visual_pack(args: argparse.Namespace) -> int:
    study_dir = args.study_dir.resolve()
    io_dir = args.io_dir.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ranking = read_csv(study_dir / "ranking.csv")
    corr = read_csv(study_dir / "hspice_correlation.csv")
    view_cal = read_csv(study_dir / "view_calibration_summary.csv")

    ok_corr = [row for row in corr if row.get("correlation_status") == "ok" and row.get("overlay_plot")]
    rx_shape_pass_rows = one_per_channel(
        [
            row for row in ok_corr
            if row.get("rx_voltage_shape_class") == "PASS"
            and row.get("rx_shape_hspice_audit_class") == "PASS"
        ],
        6,
    )
    delayeq_rows = one_per_channel(
        [
            row for row in ok_corr
            if row.get("selected_candidate_family") == "reduced_4p_rx_delayeq_rc_ring"
            and row.get("rx_shape_hspice_audit_class") == "PASS"
        ],
        6,
    )
    clarity_rows = one_per_channel(
        [
            row for row in ok_corr
            if row.get("channel_id", "").startswith("Clarity_example")
            and row.get("rx_shape_hspice_audit_class") == "FAIL"
        ],
        2,
    )
    reflection_gap_rows = one_per_channel(
        [
            row for row in ok_corr
            if row.get("reflection_trust_class") == "FAIL"
            and row.get("reflection_hspice_audit_class") == "PASS"
        ],
        4,
    )
    rows_by_group = {
        "rx_shape_pass": rx_shape_pass_rows,
        "delayeq_rx_shape_pass": delayeq_rows,
        "clarity_fast_edge_fail": clarity_rows,
        "reflection_metric_gap": reflection_gap_rows,
    }
    case_rows = copy_examples(rows_by_group, out_dir)

    figure_paths: list[Path] = []
    with PdfPages(out_dir / "visual_support_pack.pdf") as pdf:
        io_fig = plot_io_buf_montage(io_dir, out_dir, pdf)
        if io_fig is not None:
            figure_paths.append(io_fig)
        figure_paths.append(plot_headline(out_dir, ranking, corr, view_cal, pdf))
        figure_paths.append(plot_view_calibration(out_dir, view_cal, pdf))
        for maybe_path in [
            plot_montage(
                rx_shape_pass_rows,
                out_dir,
                "03_rx_shape_pass_hspice_confirmed.png",
                "RX Shape PASS Cases: Independent Metric Confirmed By HSPICE",
                "RX_SHAPE_READY_TIMING_WARN",
                pdf,
            ),
            plot_montage(
                delayeq_rows,
                out_dir,
                "04_delayeq_reduced_4p_examples.png",
                "Delay-Equalized Reduced .s4p: Shape Tracks HSPICE, Timing Still WARN",
                "Delay-equalized .s4p RX shape OK",
                pdf,
            ),
            plot_montage(
                clarity_rows,
                out_dir,
                "05_clarity_fast_edge_mismatch.png",
                "Clarity .s2p: Fast-Edge Voltage Shape Still Fails",
                "Known mismatch / not ready",
                pdf,
            ),
            plot_montage(
                reflection_gap_rows,
                out_dir,
                "06_reflection_metric_gap_examples.png",
                "Reflection Gap: TX Observable Can Pass While S11-Based Claim Fails",
                "Reflection metric gap",
                pdf,
            ),
            plot_rx_zoom_grid(
                rx_shape_pass_rows,
                out_dir,
                "07_rx_shape_pass_rx_zoom.png",
                "RX-Only Zoom: Shape-PASS / Timing-WARN Cases Stay Within Millivolt-Level Error",
                pdf,
            ),
            plot_rx_zoom_grid(
                delayeq_rows,
                out_dir,
                "08_delayeq_rx_zoom.png",
                "RX-Only Zoom: Delay-Equalized Reduced .s4p Has Low Voltage Error, Timing WARN",
                pdf,
            ),
        ]:
            if maybe_path is not None:
                figure_paths.append(maybe_path)
        figure_paths.append(plot_rx_error_scatter(out_dir, corr, pdf))

    write_readme(out_dir, study_dir, io_dir, figure_paths, case_rows, ranking, corr, view_cal)
    print(f"Wrote visual support pack under {out_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate presentation visuals for S-parameter and IO-buffer studies.")
    parser.add_argument("--study-dir", type=Path, default=ROOT / "results" / "sparam_rx_trust_v2_2026-06-11")
    parser.add_argument("--io-dir", type=Path, default=ROOT / "results" / "io_buf_old_new_four_overlays_2026-06-05")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "visual_support_pack_2026-06-12")
    return parser


def main() -> int:
    return build_visual_pack(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
