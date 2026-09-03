from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_io_buf_switching_coeff_sweep import (  # noqa: E402
    SweepCase,
    build_cases,
    build_pwl_points,
    transition_windows,
)


STUDY_DIR = ROOT / "results" / "io_buf_switching_coeff_sweep_2026-06-19"
OUT_DIR = STUDY_DIR / "mismatch_analysis"
PLOTS_DIR = OUT_DIR / "plots"
CASES_TO_ANALYZE = [
    "edge_5ps_50r_2pf",
    "edge_50ps_50r_2pf",
    "edge_500ps_50r_2pf",
    "edge_2ns_50r_2pf",
    "short_pulse_2ns_high",
]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_waveform(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        values: dict[str, list[float]] = {field: [] for field in fields}
        for row in reader:
            for field in fields:
                values[field].append(float(row[field]))
    return {field: np.asarray(vals, dtype=float) for field, vals in values.items()}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def crossing_time(t: np.ndarray, y: np.ndarray, threshold: float, direction: str, x0: float, x1: float) -> float:
    mask = (t >= x0) & (t <= x1)
    tt = t[mask]
    yy = y[mask]
    if len(tt) < 2:
        return float("nan")
    if direction == "rise":
        before = yy < threshold
        after = yy >= threshold
    elif direction == "fall":
        before = yy > threshold
        after = yy <= threshold
    else:
        raise ValueError(direction)
    idxs = np.flatnonzero(before[:-1] & after[1:]) + 1
    if len(idxs) == 0:
        return float("nan")
    idx = int(idxs[0])
    t0, t1 = float(tt[idx - 1]), float(tt[idx])
    y0, y1 = float(yy[idx - 1]), float(yy[idx])
    if abs(y1 - y0) < 1e-15:
        return t1
    frac = (threshold - y0) / (y1 - y0)
    return t0 + frac * (t1 - t0)


def signal_extrema(t: np.ndarray, y: np.ndarray, x0: float, x1: float) -> tuple[float, float, float, float]:
    mask = (t >= x0) & (t <= x1)
    tt = t[mask]
    yy = y[mask]
    if len(tt) == 0:
        return (float("nan"), float("nan"), float("nan"), float("nan"))
    i_min = int(np.argmin(yy))
    i_max = int(np.argmax(yy))
    return float(np.min(yy)), float(tt[i_min]), float(np.max(yy)), float(tt[i_max])


def fmt(value: object, digits: int = 3) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(x):
        return ""
    return f"{x:.{digits}f}"


def pwl_transitions(case: SweepCase) -> list[dict[str, object]]:
    points = build_pwl_points(case)
    windows = transition_windows(case)
    rows: list[dict[str, object]] = []
    wi = 0
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if abs(v1 - v0) <= 1e-9:
            continue
        x0, x1 = windows[wi]
        wi += 1
        rows.append(
            {
                "event_index": wi,
                "input_direction": "rise" if v1 > v0 else "fall",
                "input_start_ns": t0,
                "input_end_ns": t1,
                "input_50_ns": 0.5 * (t0 + t1),
                "window_start_ns": x0,
                "window_end_ns": x1,
            }
        )
    return rows


def analyze_case(case: SweepCase, metric_row: dict[str, str]) -> tuple[list[dict[str, object]], dict[str, object]]:
    data = read_waveform(STUDY_DIR / "cases" / case.case_id / "aligned_waveforms.csv")
    t = data["time_ns"]
    h_pad = data["hspice_pad_v"]
    n_pad = data["ngspice_pybis_pad_v_interp"]
    h_ku = data["hspice_ku"]
    n_ku = data["ngspice_pybis_ku_interp"]
    h_kd = data["hspice_kd"]
    n_kd = data["ngspice_pybis_kd_interp"]

    event_rows: list[dict[str, object]] = []
    for event in pwl_transitions(case):
        x0 = float(event["window_start_ns"])
        x1 = float(event["window_end_ns"])
        search0 = float(event["input_start_ns"])
        input_dir = str(event["input_direction"])
        if input_dir == "rise":
            coeff_specs = [("kd", "fall", h_kd, n_kd), ("ku", "rise", h_ku, n_ku)]
            pad_dir = "rise"
        else:
            coeff_specs = [("ku", "fall", h_ku, n_ku), ("kd", "rise", h_kd, n_kd)]
            pad_dir = "fall"

        pad_min, pad_min_t, pad_max, pad_max_t = signal_extrema(t, h_pad, x0, x1)
        pad_threshold = pad_min + 0.5 * (pad_max - pad_min)
        h_pad_50 = crossing_time(t, h_pad, pad_threshold, pad_dir, search0, x1)
        n_pad_50 = crossing_time(t, n_pad, pad_threshold, pad_dir, search0, x1)
        n_pad_min, n_pad_min_t, n_pad_max, n_pad_max_t = signal_extrema(t, n_pad, x0, x1)

        base = {
            "case_id": case.case_id,
            "event_index": event["event_index"],
            "input_direction": input_dir,
            "input_50_ns": event["input_50_ns"],
            "window_start_ns": x0,
            "window_end_ns": x1,
            "pad_hspice_50_ns": h_pad_50,
            "pad_ngspice_50_ns": n_pad_50,
            "pad_ng_minus_h_ps": (n_pad_50 - h_pad_50) * 1000.0 if math.isfinite(n_pad_50) and math.isfinite(h_pad_50) else float("nan"),
            "pad_hspice_peak_v": pad_max if pad_dir == "rise" else pad_min,
            "pad_ngspice_peak_v": n_pad_max if pad_dir == "rise" else n_pad_min,
            "pad_peak_delta_v": (n_pad_max - pad_max) if pad_dir == "rise" else (n_pad_min - pad_min),
        }
        for coeff_name, coeff_dir, h_sig, n_sig in coeff_specs:
            coeff_row = dict(base)
            coeff_row["coefficient"] = coeff_name
            coeff_row["coefficient_direction"] = coeff_dir
            for level in (0.1, 0.5, 0.9):
                h_t = crossing_time(t, h_sig, level, coeff_dir, search0, x1)
                n_t = crossing_time(t, n_sig, level, coeff_dir, search0, x1)
                coeff_row[f"hspice_{int(level * 100)}pct_ns"] = h_t
                coeff_row[f"ngspice_{int(level * 100)}pct_ns"] = n_t
                coeff_row[f"ng_minus_h_{int(level * 100)}pct_ps"] = (n_t - h_t) * 1000.0 if math.isfinite(h_t) and math.isfinite(n_t) else float("nan")
            h_min, h_min_t, h_max, h_max_t = signal_extrema(t, h_sig, x0, x1)
            n_min, n_min_t, n_max, n_max_t = signal_extrema(t, n_sig, x0, x1)
            coeff_row.update(
                {
                    "hspice_min": h_min,
                    "hspice_max": h_max,
                    "ngspice_min": n_min,
                    "ngspice_max": n_max,
                    "peak_delta": (n_max - h_max) if coeff_dir == "rise" else (n_min - h_min),
                    "active_coeff_abs_error_mean": float(np.mean(np.abs(n_sig[(t >= x0) & (t <= x1)] - h_sig[(t >= x0) & (t <= x1)]))),
                    "active_coeff_abs_error_max": float(np.max(np.abs(n_sig[(t >= x0) & (t <= x1)] - h_sig[(t >= x0) & (t <= x1)]))),
                }
            )
            event_rows.append(coeff_row)

    summary = {
        "case_id": case.case_id,
        "description": case.description,
        "quality_status": metric_row.get("quality_status", ""),
        "pad_rmse_mv": float(metric_row["pad_active_rmse_v"]) * 1000.0,
        "ku_rmse": float(metric_row["ku_active_rmse"]),
        "kd_rmse": float(metric_row["kd_active_rmse"]),
        "max_abs_coeff_error": max(float(row["active_coeff_abs_error_max"]) for row in event_rows),
        "max_abs_50pct_coeff_timing_delta_ps": max(
            abs(float(row["ng_minus_h_50pct_ps"]))
            for row in event_rows
            if math.isfinite(float(row["ng_minus_h_50pct_ps"]))
        ),
        "max_abs_pad_50pct_delta_ps": max(
            abs(float(row["pad_ng_minus_h_ps"]))
            for row in event_rows
            if math.isfinite(float(row["pad_ng_minus_h_ps"]))
        ),
    }
    return event_rows, summary


def plot_case_diagnostic(case: SweepCase) -> None:
    data = read_waveform(STUDY_DIR / "cases" / case.case_id / "aligned_waveforms.csv")
    t = data["time_ns"]
    h_pad = data["hspice_pad_v"]
    n_pad = data["ngspice_pybis_pad_v_interp"]
    h_ku = data["hspice_ku"]
    n_ku = data["ngspice_pybis_ku_interp"]
    h_kd = data["hspice_kd"]
    n_kd = data["ngspice_pybis_kd_interp"]

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(11, 8.2), sharex=True)
    axes[0].plot(t, h_pad, lw=2.0, label="HSPICE pad")
    axes[0].plot(t, n_pad, lw=1.7, ls="--", label="ngspice pybis pad")
    axes[0].set_ylabel("Pad (V)")
    axes[0].grid(True, alpha=0.28)
    axes[0].legend(loc="best")

    axes[1].plot(t, h_ku, lw=2.0, label="HSPICE Ku")
    axes[1].plot(t, n_ku, lw=1.7, ls="--", label="ngspice Ku")
    axes[1].plot(t, h_kd, lw=2.0, label="HSPICE Kd")
    axes[1].plot(t, n_kd, lw=1.7, ls="--", label="ngspice Kd")
    axes[1].set_ylabel("Coeff")
    axes[1].set_ylim(-0.12, 1.12)
    axes[1].grid(True, alpha=0.28)
    axes[1].legend(loc="best", ncol=2)

    axes[2].plot(t, n_ku - h_ku, lw=1.8, label="ngspice Ku - HSPICE Ku")
    axes[2].plot(t, n_kd - h_kd, lw=1.8, label="ngspice Kd - HSPICE Kd")
    axes[2].axhline(0.0, color="black", lw=0.8)
    axes[2].set_ylabel("Coeff error")
    axes[2].set_xlabel("Time (ns)")
    axes[2].grid(True, alpha=0.28)
    axes[2].legend(loc="best")

    for event in pwl_transitions(case):
        for ax in axes:
            ax.axvline(float(event["input_50_ns"]), color="0.25", lw=1.0, ls=":", alpha=0.8)
    fig.suptitle(f"{case.case_id}: coefficient mismatch diagnostic")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(PLOTS_DIR / f"{case.case_id}_diagnostic.png", dpi=180)
    plt.close(fig)


def mechanism_text(case_id: str) -> str:
    if case_id == "edge_5ps_50r_2pf":
        return "Small but visible coefficient timing skew. The pad waveform is still close; coefficient RMSE crosses the GOOD threshold first."
    if case_id == "edge_50ps_50r_2pf":
        return "Moderate slow-edge skew. Ku/Kd still follow the same general shape, but the pad and coefficient transitions no longer line up at the few-ps level."
    if case_id == "edge_500ps_50r_2pf":
        return "The input ramp is slow enough that HSPICE and pybis make different switching-decision timing choices. Coefficient turn-off/turn-on timing diverges by hundreds of ps."
    if case_id == "edge_2ns_50r_2pf":
        return "Very slow input ramp. HSPICE switches the output much earlier on the rising edge and later on the falling edge; pybis lags/advances differently, creating large pad error."
    if case_id == "short_pulse_2ns_high":
        return "Interrupted transition. HSPICE never lets Ku reach a full pull-up state before reversal, while pybis drives Ku close to full on, causing a much larger pad pulse."
    return ""


def write_report(summaries: list[dict[str, object]], events: list[dict[str, object]]) -> None:
    lines = [
        "# io_buf Switching Coefficient Mismatch Analysis",
        "",
        "This report focuses on the WARN/CHECK cases from the switching-coefficient sweep.",
        "The goal is to separate simple waveform error from the underlying Ku/Kd state behavior.",
        "",
        "## Key Takeaway",
        "",
        "The largest mismatch is not load-dependent. It appears when the input stimulus makes the IBIS switching state ambiguous: slow input ramps and interrupted transitions.",
        "",
        "## Case Summary",
        "",
        "| Case | Status | Pad RMSE (mV) | Ku RMSE | Kd RMSE | Max coeff err | Max coeff 50% delta (ps) | Max pad 50% delta (ps) | Mechanism |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            "| {case} | {status} | {pad} | {ku} | {kd} | {cerr} | {ct} | {pt} | {mech} |".format(
                case=row["case_id"],
                status=row["quality_status"],
                pad=fmt(row["pad_rmse_mv"], 1),
                ku=fmt(row["ku_rmse"], 4),
                kd=fmt(row["kd_rmse"], 4),
                cerr=fmt(row["max_abs_coeff_error"], 3),
                ct=fmt(row["max_abs_50pct_coeff_timing_delta_ps"], 1),
                pt=fmt(row["max_abs_pad_50pct_delta_ps"], 1),
                mech=mechanism_text(str(row["case_id"])),
            )
        )

    lines.extend(
        [
            "",
            "## Event-Level 50% Timing",
            "",
            "Positive timing delta means ngspice/pybis crosses later than HSPICE. Negative means ngspice/pybis crosses earlier.",
            "",
            "| Case | Event | Input | Coeff | Coeff dir | Coeff 50% delta (ps) | Pad 50% delta (ps) | Peak delta |",
            "|---|---:|---|---|---|---:|---:|---:|",
        ]
    )
    for row in events:
        lines.append(
            "| {case} | {ev} | {inp} | {coeff} | {cdir} | {ct} | {pt} | {peak} |".format(
                case=row["case_id"],
                ev=row["event_index"],
                inp=row["input_direction"],
                coeff=row["coefficient"],
                cdir=row["coefficient_direction"],
                ct=fmt(row["ng_minus_h_50pct_ps"], 1),
                pt=fmt(row["pad_ng_minus_h_ps"], 1),
                peak=fmt(row["peak_delta"], 3),
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "For normal fast toggles, HSPICE and pybis generate nearly identical Ku/Kd trajectories. The mismatch grows when the input ramp itself is slow because the two implementations do not make the same switching-state timing decision.",
            "",
            "For the short-pulse case, the issue is not just a timing offset. The transition is interrupted before the pad settles. HSPICE keeps the pull-up coefficient partial, while pybis allows the pull-up coefficient to reach near full strength before recovery. That creates a much larger output pulse in ngspice/pybis.",
            "",
            "## Diagnostic Plots",
            "",
        ]
    )
    for row in summaries:
        case_id = row["case_id"]
        lines.append(f"- `plots/{case_id}_diagnostic.png`")

    (OUT_DIR / "SWITCHING_COEFF_MISMATCH_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    case_map = {case.case_id: case for case in build_cases()}
    metrics = {row["case_id"]: row for row in read_csv_rows(STUDY_DIR / "metrics_by_case.csv")}

    all_events: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for case_id in CASES_TO_ANALYZE:
        case = case_map[case_id]
        events, summary = analyze_case(case, metrics[case_id])
        all_events.extend(events)
        summaries.append(summary)
        plot_case_diagnostic(case)

    write_csv(OUT_DIR / "mismatch_case_summary.csv", summaries)
    write_csv(OUT_DIR / "mismatch_event_timing.csv", all_events)
    write_report(summaries, all_events)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"REPORT={OUT_DIR / 'SWITCHING_COEFF_MISMATCH_ANALYSIS.md'}")
    print(f"SUMMARY={OUT_DIR / 'mismatch_case_summary.csv'}")
    print(f"EVENTS={OUT_DIR / 'mismatch_event_timing.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
