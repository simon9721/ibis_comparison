from __future__ import annotations

import argparse
import csv
from pathlib import Path
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


DEFAULT_STUDY = ROOT / "results" / "sparam_vector_fit_campaign_v1_2026-06-12_expanded_pilot"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def resolve_path(text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


def display_path(path: Path) -> str:
    full = path if path.is_absolute() else ROOT / path
    try:
        return str(full.relative_to(ROOT))
    except ValueError:
        return str(full)


def safe_id(text: object) -> str:
    out = []
    for ch in str(text):
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or "case"


def as_float(row: dict[str, str], key: str) -> float | None:
    text = row.get(key, "")
    if text == "":
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not np.isfinite(value):
        return None
    return value


def nice_step(span: float) -> float:
    if span <= 0:
        return 0.001
    raw = span / 8.0
    exponent = np.floor(np.log10(raw))
    base = raw / (10**exponent)
    if base <= 1.0:
        nice = 1.0
    elif base <= 2.0:
        nice = 2.0
    elif base <= 5.0:
        nice = 5.0
    else:
        nice = 10.0
    return max(0.001, float(nice * (10**exponent)))


def voltage_scale(values: np.ndarray) -> tuple[float, str, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 1.0, "V", 0.05
    max_abs = float(np.max(np.abs(finite)))
    if max_abs < 0.05:
        # Low-swing channel outputs are otherwise visually indistinguishable
        # from zero on a volt-scale plot. Keep a 1 mV minimum span so tiny
        # numerical noise is not exaggerated into a full-screen waveform.
        return 1e3, "mV", 1.0
    return 1.0, "V", 0.05


def nice_ylim(values: np.ndarray, min_span: float) -> tuple[float, float, np.ndarray]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return -0.5 * min_span, 0.5 * min_span, np.linspace(-0.5 * min_span, 0.5 * min_span, 5)
    low = float(np.min(finite))
    high = float(np.max(finite))
    span = max(high - low, 0.001)
    # Avoid visually exaggerating tiny differences. The plot should show the
    # signal scale, not a residual-sized y-axis.
    min_span = max(min_span, 0.08 * max(abs(low), abs(high), 1.0 if min_span >= 0.05 else 0.0))
    span = max(span, min_span)
    center = 0.5 * (low + high)
    low = center - 0.55 * span
    high = center + 0.55 * span
    step = nice_step(high - low)
    low_tick = np.floor(low / step) * step
    high_tick = np.ceil(high / step) * step
    ticks = np.arange(low_tick, high_tick + 0.5 * step, step)
    return float(low_tick), float(high_tick), ticks


def plot_side(
    h: dict[str, np.ndarray],
    n: dict[str, np.ndarray],
    signal: str,
    out_path: Path,
    title: str,
    metric_label: str,
) -> None:
    h_time = h["time"] * 1e9
    n_time = n["time"] * 1e9
    raw_values = np.concatenate([h[signal], n[signal]])
    scale, unit, min_span = voltage_scale(raw_values)
    h_y = h[signal] * scale
    n_y = n[signal] * scale

    y_low, y_high, y_ticks = nice_ylim(np.concatenate([h_y, n_y]), min_span)

    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    ax.plot(h_time, h_y, label="HSPICE native S-parameter", linewidth=2.0, color="#1f5a99")
    ax.plot(n_time, n_y, label="ngspice vector-fit .sp", linewidth=1.8, linestyle="--", color="#c23b2a")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(f"Voltage ({unit})")
    ax.set_ylim(y_low, y_high)
    ax.set_yticks(y_ticks)
    ax.grid(True, color="#d7dde6", linewidth=0.8)
    ax.legend(frameon=False, loc="best")
    ax.text(
        0.99,
        0.03,
        metric_label,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9.5,
        bbox={"facecolor": "white", "edgecolor": "#cfd6df", "alpha": 0.9, "boxstyle": "round,pad=0.28"},
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def build_metric_label(row: dict[str, str], side: str) -> str:
    prefix = "rx" if side == "rx" else "tx"
    rmse = as_float(row, f"{prefix}_active_rmse_v")
    maxabs = as_float(row, f"{prefix}_active_maxabs_v")
    cls = row.get("hspice_audit_class", "") if side == "rx" else row.get("reflection_hspice_audit_class", "")
    parts = []
    if cls:
        parts.append(f"audit: {cls}")
    if rmse is not None:
        parts.append(f"active RMSE: {rmse * 1e3:.2f} mV")
    if maxabs is not None:
        parts.append(f"max error: {maxabs * 1e3:.2f} mV")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one-side-per-figure vector-fit HSPICE/ngspice overlays.")
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--correlation-csv", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    study_dir = args.study_dir
    corr_csv = args.correlation_csv or (study_dir / "vf_hspice_correlation.csv")
    if not corr_csv.is_absolute():
        corr_csv = ROOT / corr_csv
    corr_rows = read_csv(corr_csv)
    manifest = {row["channel_id"]: row for row in read_csv(study_dir / "manifest.csv") if row.get("channel_id")}
    out_dir = args.out_dir or (study_dir / "plots" / "side_overlays")
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    index_rows: list[dict[str, object]] = []
    for row in corr_rows:
        if row.get("correlation_status") != "ok":
            continue
        h_path = resolve_path(row.get("hspice_tr0", ""))
        n_path = resolve_path(row.get("ngspice_raw", ""))
        if not h_path.exists() or not n_path.exists():
            continue

        h = parse_hspice_tr0(h_path)
        n = parse_ngspice_raw(n_path)
        ports = int(float(manifest.get(row.get("channel_id", ""), {}).get("ports", "2") or "2"))
        signals = {"tx": "v(p1)", "rx": "v(p2)" if ports == 2 else "v(p3)"}

        for side, signal in signals.items():
            if signal not in h or signal not in n:
                continue
            edge = row.get("edge_ps", "")
            channel_id = row.get("channel_id", "")
            candidate = row.get("candidate_id", "")
            case = row.get("case", "")
            side_label = "RX side" if side == "rx" else "TX side"
            title = f"{channel_id} | {side_label} | {candidate} | {edge} ps edge"
            filename = f"{safe_id(channel_id)}_{safe_id(candidate)}_{safe_id(case)}_{side}.png"
            out_path = out_dir / side / filename
            plot_side(h, n, signal, out_path, title, build_metric_label(row, side))
            index_rows.append(
                {
                    "channel_id": channel_id,
                    "candidate_id": candidate,
                    "case": case,
                    "edge_ps": edge,
                    "side": side,
                    "signal": signal,
                    "hspice_audit_class": row.get("hspice_audit_class", ""),
                    "rx_shape_hspice_audit_class": row.get("rx_shape_hspice_audit_class", ""),
                    "rx_timing_hspice_audit_class": row.get("rx_timing_hspice_audit_class", ""),
                    "reflection_hspice_audit_class": row.get("reflection_hspice_audit_class", ""),
                    "active_rmse_v": row.get(f"{side}_active_rmse_v", ""),
                    "active_maxabs_v": row.get(f"{side}_active_maxabs_v", ""),
                    "plot": display_path(out_path),
                }
            )

    write_csv(out_dir / "index.csv", index_rows)
    rx_count = sum(1 for row in index_rows if row["side"] == "rx")
    tx_count = sum(1 for row in index_rows if row["side"] == "tx")
    readme = [
        "# Vector-Fit Side Overlays",
        "",
        f"Study folder: `{display_path(study_dir)}`",
        f"Correlation CSV: `{display_path(corr_csv)}`",
        "",
        f"- RX-side figures: `{rx_count}`",
        f"- TX-side figures: `{tx_count}`",
        f"- Total figures: `{len(index_rows)}`",
        "",
        "Each figure compares HSPICE native S-parameter simulation against ngspice running the exported vector-fit `.sp` model.",
        "",
        "The y-axis uses the signal scale instead of a tight residual scale, so small millivolt-level errors do not look artificially huge.",
        "",
        "## Files",
        "",
        "- `rx/`",
        "- `tx/`",
        "- `index.csv`",
        "- `testbenches/`",
        "",
        "`testbenches/` may contain copied vector-fit `.sp` models, HSPICE decks, ngspice decks, and Touchstone inputs used to produce the figures.",
    ]
    (out_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"Wrote {len(index_rows)} side overlay figures to {out_dir}")
    print(f"RX: {rx_count}, TX: {tx_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
