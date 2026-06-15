from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import textwrap
from pathlib import Path

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


def read_csv(path: Path) -> list[dict[str, str]]:
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


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._") or "case"


def fnum(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "") or 0.0)
    except ValueError:
        return 0.0


def common_time_grid(th: np.ndarray, yh: np.ndarray, tn: np.ndarray, yn: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lo = max(float(th[0]), float(tn[0]))
    hi = min(float(th[-1]), float(tn[-1]))
    n = min(7000, max(500, min(len(th), len(tn))))
    grid = np.linspace(lo, hi, n)
    return grid, np.interp(grid, th, yh), np.interp(grid, tn, yn)


def choose_scale(yh: np.ndarray, yn: np.ndarray, signal_kind: str) -> tuple[float, str]:
    span = max(
        abs(float(np.nanmax(yh))),
        abs(float(np.nanmin(yh))),
        abs(float(np.nanmax(yn))),
        abs(float(np.nanmin(yn))),
    )
    if signal_kind == "rx" and span < 0.02:
        return 1000.0, "mV"
    return 1.0, "V"


def active_xlim(t_ns: np.ndarray, yh: np.ndarray, yn: np.ndarray, signal_kind: str) -> tuple[float, float]:
    if signal_kind == "tx":
        return float(t_ns[0]), float(t_ns[-1])
    baseline = float(np.nanmedian(yh[: max(10, min(len(yh), len(yh) // 20))]))
    span = max(float(np.nanmax(np.abs(yh - baseline))), float(np.nanmax(np.abs(yn - baseline))), 1e-15)
    active = np.where((np.abs(yh - baseline) > 0.04 * span) | (np.abs(yn - baseline) > 0.04 * span))[0]
    if active.size == 0:
        return float(t_ns[0]), float(t_ns[-1])
    lo = max(float(t_ns[0]), float(t_ns[max(0, int(active[0]) - 80)]) - 1.0)
    hi = min(float(t_ns[-1]), float(t_ns[min(len(t_ns) - 1, int(active[-1]) + 80)]) + 1.0)
    if hi - lo < 4.0:
        mid = 0.5 * (lo + hi)
        lo = max(float(t_ns[0]), mid - 2.0)
        hi = min(float(t_ns[-1]), mid + 2.0)
    return lo, hi


def axis_policy(yh_scaled: np.ndarray, yn_scaled: np.ndarray, unit: str) -> tuple[float, float, float]:
    values = np.concatenate([yh_scaled[np.isfinite(yh_scaled)], yn_scaled[np.isfinite(yn_scaled)]])
    if values.size == 0:
        return -1.0, 1.0, 1.0
    ymin = float(np.min(values))
    ymax = float(np.max(values))
    if unit == "mV":
        tick = 1.0
        pad = 0.20
        min_span = 4.0
    else:
        raw_span = max(abs(ymin), abs(ymax), ymax - ymin)
        if raw_span <= 1.2:
            tick = 0.2
            min_span = 1.0
        elif raw_span <= 3.0:
            tick = 0.5
            min_span = 2.0
        else:
            tick = 1.0
            min_span = 4.0
        pad = 0.05 * max(ymax - ymin, tick)
    lo = np.floor((ymin - pad) / tick) * tick
    hi = np.ceil((ymax + pad) / tick) * tick
    if hi <= lo:
        lo -= tick
        hi += tick
    if hi - lo < min_span:
        center = 0.5 * (hi + lo)
        lo = np.floor((center - min_span / 2.0) / tick) * tick
        hi = lo + min_span
    return float(lo), float(hi), float(tick)


def apply_y_axis_policy(ax, yh_scaled: np.ndarray, yn_scaled: np.ndarray, unit: str) -> None:
    lo, hi, tick = axis_policy(yh_scaled, yn_scaled, unit)
    ax.set_ylim(lo, hi)
    ax.yaxis.set_major_locator(MultipleLocator(tick))


def plot_one(row: dict[str, str], out_path: Path, signal_kind: str) -> None:
    h = parse_hspice_tr0(resolve_path(row["hspice_tr0"]))
    n = parse_ngspice_raw(resolve_path(row["ngspice_raw"]))
    nports = int(float(row.get("ports", "2") or 2))
    signal = "v(p1)" if signal_kind == "tx" else ("v(p2)" if nports == 2 else "v(p3)")
    th = np.asarray(h["time"], dtype=float)
    tn = np.asarray(n["time"], dtype=float)
    yh = np.asarray(h[signal], dtype=float)
    yn = np.asarray(n[signal], dtype=float)
    grid, hg, ng = common_time_grid(th, yh, tn, yn)
    grid_ns = grid * 1e9
    scale, unit = choose_scale(hg, ng, signal_kind)
    lo, hi = active_xlim(grid_ns, hg, ng, signal_kind)

    fig, ax = plt.subplots(figsize=(9.5, 4.9), facecolor="white")
    hg_scaled = hg * scale
    ng_scaled = ng * scale
    ax.plot(grid_ns, hg_scaled, color="#1f77b4", linewidth=2.0, label="HSPICE native S")
    ax.plot(grid_ns, ng_scaled, color="#ff7f0e", linestyle="--", linewidth=1.9, label="ngspice converted")
    ax.set_xlim(lo, hi)
    apply_y_axis_policy(ax, hg_scaled, ng_scaled, unit)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(f"{'RX' if signal_kind == 'rx' else 'TX'} voltage ({unit})")
    ax.grid(True, color="#d7dde6", linewidth=0.9)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="best", fontsize=9.5)
    shape = row.get("rx_shape_hspice_audit_class", "")
    timing = row.get("rx_timing_hspice_audit_class", "")
    independent = f"{row.get('rx_voltage_shape_class', '')}/{row.get('rx_timing_class', '')}"
    if signal_kind == "rx":
        rmse = 1000.0 * fnum(row, "rx_active_rmse_v")
        maxabs = 1000.0 * fnum(row, "rx_active_maxabs_v")
        metric_line = f"RX active RMSE {rmse:.3g} mV, max {maxabs:.3g} mV"
    else:
        rmse = 1000.0 * fnum(row, "tx_active_rmse_v")
        maxabs = 1000.0 * fnum(row, "tx_active_maxabs_v")
        metric_line = f"TX active RMSE {rmse:.3g} mV, max {maxabs:.3g} mV"
    title = f"{'RX side' if signal_kind == 'rx' else 'TX side'} | {row.get('channel_id', '')} | {row.get('case', '')}"
    wrapped_title = "\n".join(textwrap.wrap(title, width=88))
    ax.set_title(wrapped_title, loc="left", fontsize=10.2, weight="bold", pad=9)
    box_text = (
        f"Audit: {row.get('hspice_audit_class', '')}\n"
        f"Ind RX: {independent}\n"
        f"HSPICE RX: {shape}/{timing}\n"
        f"{metric_line}"
    )
    ax.text(
        0.012,
        0.972,
        box_text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.6,
        bbox={"boxstyle": "round,pad=0.28", "facecolor": "white", "edgecolor": "#b0bec5", "alpha": 0.92},
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def case_sort(row: dict[str, str]) -> tuple[str, str]:
    return row.get("channel_id", ""), row.get("case", "")


def build(args: argparse.Namespace) -> int:
    study_dir = args.study_dir.resolve()
    out_dir = args.out_dir.resolve()
    for child in ("good_cases", "bad_cases"):
        target = out_dir / child
        if target.exists():
            shutil.rmtree(target)
    corr = read_csv(study_dir / "hspice_correlation.csv")
    rows = [
        row for row in corr
        if row.get("correlation_status") == "ok"
        and row.get("hspice_audit_class") in {"PASS", "WARN", "FAIL"}
        and row.get("hspice_tr0")
        and row.get("ngspice_raw")
    ]
    if args.max_cases:
        good = [row for row in rows if row.get("hspice_audit_class") == "PASS"]
        bad = [row for row in rows if row.get("hspice_audit_class") != "PASS"]
        rows = sorted(good, key=case_sort)[: args.max_cases] + sorted(bad, key=case_sort)[: args.max_cases]

    index_rows: list[dict[str, object]] = []
    for idx, row in enumerate(sorted(rows, key=case_sort), start=1):
        bucket = "good_cases" if row.get("hspice_audit_class") == "PASS" else "bad_cases"
        stem = safe_name(f"{idx:03d}_{row.get('hspice_audit_class', '')}_{row.get('channel_id', '')}_{row.get('case', '')}")
        for signal_kind in ("rx", "tx"):
            signal_dir = out_dir / bucket / f"{signal_kind}_side"
            out_path = signal_dir / f"{stem}_{signal_kind}.png"
            plot_one(row, out_path, signal_kind)
            index_rows.append(
                {
                    "bucket": bucket,
                    "signal": signal_kind,
                    "channel_id": row.get("channel_id", ""),
                    "case": row.get("case", ""),
                    "selected_candidate_family": row.get("selected_candidate_family", ""),
                    "independent_rx_shape": row.get("rx_voltage_shape_class", ""),
                    "independent_rx_timing": row.get("rx_timing_class", ""),
                    "hspice_rx_shape": row.get("rx_shape_hspice_audit_class", ""),
                    "hspice_rx_timing": row.get("rx_timing_hspice_audit_class", ""),
                    "hspice_audit_class": row.get("hspice_audit_class", ""),
                    "rx_active_rmse_mv": 1000.0 * fnum(row, "rx_active_rmse_v"),
                    "rx_active_maxabs_mv": 1000.0 * fnum(row, "rx_active_maxabs_v"),
                    "tx_active_rmse_mv": 1000.0 * fnum(row, "tx_active_rmse_v"),
                    "tx_active_maxabs_mv": 1000.0 * fnum(row, "tx_active_maxabs_v"),
                    "figure": str(out_path.relative_to(out_dir)).replace("\\", "/"),
                }
            )

    write_csv(out_dir / "index.csv", index_rows)
    good_cases = len({(row["channel_id"], row["case"]) for row in index_rows if row["bucket"] == "good_cases"})
    bad_cases = len({(row["channel_id"], row["case"]) for row in index_rows if row["bucket"] == "bad_cases"})
    readme = [
        "# Simple Good/Bad HSPICE-ngspice Overlays",
        "",
        "Classification rule:",
        "",
        "- `good_cases`: overall HSPICE audit class is `PASS`.",
        "- `bad_cases`: overall HSPICE audit class is `WARN` or `FAIL`.",
        "- RX-shape-only status is still recorded in `index.csv`, but folder placement uses the stricter visual/pass-fail audit class.",
        "- Each case has one clean RX-side figure and one clean TX-side figure.",
        "",
        f"Source study: `{study_dir}`",
        f"Good cases: `{good_cases}`",
        f"Bad cases: `{bad_cases}`",
        "",
        "Folders:",
        "",
        "- `good_cases/rx_side/`",
        "- `good_cases/tx_side/`",
        "- `bad_cases/rx_side/`",
        "- `bad_cases/tx_side/`",
        "",
        "See `index.csv` for metrics and exact figure filenames.",
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")
    print(f"Wrote simple overlays under {out_dir}")
    print(f"Good cases: {good_cases}; bad cases: {bad_cases}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate simple one-panel good/bad RX and TX overlays.")
    p.add_argument("--study-dir", type=Path, default=ROOT / "results" / "sparam_rx_trust_v2_2026-06-11")
    p.add_argument("--out-dir", type=Path, default=ROOT / "results" / "simple_good_bad_overlays_2026-06-12")
    p.add_argument("--max-cases", type=int, default=0, help="Optional per-bucket limit for quick preview.")
    return p


def main() -> int:
    return build(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
