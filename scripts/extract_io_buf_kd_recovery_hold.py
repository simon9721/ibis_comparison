from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0  # noqa: E402
import run_io_buf_value_matched_replay_v2 as base  # noqa: E402


RESULT_ROOT = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
OUT_DIR = RESULT_ROOT / "kd_recovery_diagnostics" / "hold_time"
SHORT_HIGH_CASES = [
    "short_pulse_500ps_high",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
]
COMPARE_FLOWS = [
    "hspice_native_ibis",
    "ngspice_two_state_directional_residual",
    "ngspice_two_state_directional_residual_recover_mean",
    "ngspice_two_state_directional_residual_recover_fast",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def t_ns(data: dict[str, np.ndarray]) -> np.ndarray:
    t = np.asarray(data["time"], dtype=float)
    return t * 1e9 if np.nanmax(t) < 1e-3 else t


def sig(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    lower = {key.lower(): key for key in data}
    for name in names:
        key = lower.get(name.lower())
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(names)


def crossing_time(t: np.ndarray, y: np.ndarray, level: float, start_ns: float) -> float:
    mask = (t >= start_ns) & np.isfinite(y)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(y[mask], dtype=float)
    if len(tt) < 2:
        return float("nan")
    d = yy - level
    idx = np.where((d[:-1] < 0.0) & (d[1:] >= 0.0))[0]
    if len(idx) == 0:
        return float("nan")
    i = int(idx[0])
    if yy[i + 1] == yy[i]:
        return float(tt[i])
    return float(tt[i] + (level - yy[i]) * (tt[i + 1] - tt[i]) / (yy[i + 1] - yy[i]))


def recovery_markers(t: np.ndarray, kd: np.ndarray, reverse_ns: float, active_end_ns: float) -> dict[str, float]:
    mask = (t >= reverse_ns) & (t <= active_end_ns) & np.isfinite(kd)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(kd[mask], dtype=float)
    if len(tt) < 8:
        return {
            "kd_min": float("nan"),
            "kd_min_time_ns": float("nan"),
            "kd_final": float("nan"),
            "recovery_10_ns": float("nan"),
            "recovery_50_ns": float("nan"),
            "recovery_90_ns": float("nan"),
            "main_slope_tau_10_90_ns": float("nan"),
        }

    min_idx = int(np.nanargmin(yy))
    kd_min = float(yy[min_idx])
    kd_min_time = float(tt[min_idx])
    tail_start = active_end_ns - max(0.3, 0.15 * (active_end_ns - kd_min_time))
    tail = yy[tt >= tail_start]
    kd_final = float(np.median(tail)) if len(tail) else float(yy[-1])
    span = kd_final - kd_min
    if span <= 1e-4:
        return {
            "kd_min": kd_min,
            "kd_min_time_ns": kd_min_time,
            "kd_final": kd_final,
            "recovery_10_ns": float("nan"),
            "recovery_50_ns": float("nan"),
            "recovery_90_ns": float("nan"),
            "main_slope_tau_10_90_ns": float("nan"),
        }

    t10 = crossing_time(tt, yy, kd_min + 0.10 * span, kd_min_time)
    t50 = crossing_time(tt, yy, kd_min + 0.50 * span, kd_min_time)
    t90 = crossing_time(tt, yy, kd_min + 0.90 * span, kd_min_time)
    tau = (t90 - t10) / math.log(9.0) if math.isfinite(t10) and math.isfinite(t90) and t90 > t10 else float("nan")
    return {
        "kd_min": kd_min,
        "kd_min_time_ns": kd_min_time,
        "kd_final": kd_final,
        "recovery_10_ns": t10,
        "recovery_50_ns": t50,
        "recovery_90_ns": t90,
        "main_slope_tau_10_90_ns": tau,
    }


def fit_hold_law(rows: list[dict[str, object]], prefix: str = "hspice") -> dict[str, object]:
    x = np.asarray([float(row["pulse_width_ns"]) for row in rows], dtype=float)
    y = np.asarray([float(row[f"{prefix}_t_hold_50_ns"]) for row in rows], dtype=float)
    good = np.isfinite(x) & np.isfinite(y)
    x = x[good]
    y = y[good]
    if len(y) < 2:
        return {
            "source": prefix,
            "h1_constant_ns": float("nan"),
            "h1_spread_fraction": float("nan"),
            "h1_residual_rms_ns": float("nan"),
            "h2_intercept_ns": float("nan"),
            "h2_slope_ns_per_ns": float("nan"),
            "h2_residual_rms_ns": float("nan"),
            "h2_improvement_ratio": float("nan"),
            "verdict": "INSUFFICIENT_DATA",
        }
    h1 = float(np.mean(y))
    h1_resid = y - h1
    h1_rms = float(np.sqrt(np.mean(h1_resid * h1_resid)))
    h1_spread = float((np.max(y) - np.min(y)) / h1) if h1 else float("nan")
    if len(y) >= 3:
        a_mat = np.vstack([x, np.ones_like(x)]).T
        slope, intercept = np.linalg.lstsq(a_mat, y, rcond=None)[0]
        pred = intercept + slope * x
        h2_rms = float(np.sqrt(np.mean((y - pred) ** 2)))
    else:
        intercept = float("nan")
        slope = float("nan")
        h2_rms = float("nan")
    ratio = h2_rms / h1_rms if h1_rms > 0 and math.isfinite(h2_rms) else float("nan")
    if math.isfinite(h1_spread) and h1_spread < 0.10:
        verdict = "CONSTANT_HOLD_SUFFICIENT"
    elif math.isfinite(ratio) and ratio < 0.5 and abs(float(slope)) > 0.05:
        verdict = "HOLD_PLUS_WIDTH_DRIFT_PREFERRED"
    else:
        verdict = "NO_SIMPLE_HOLD_LAW"
    return {
        "source": prefix,
        "h1_constant_ns": h1,
        "h1_spread_fraction": h1_spread,
        "h1_residual_rms_ns": h1_rms,
        "h2_intercept_ns": float(intercept),
        "h2_slope_ns_per_ns": float(slope),
        "h2_residual_rms_ns": h2_rms,
        "h2_improvement_ratio": ratio,
        "verdict": verdict,
    }


def build_hspice_hold_rows() -> list[dict[str, object]]:
    cases = {case.case_id: case for case in base.build_cases(include_low=True)}
    rows: list[dict[str, object]] = []
    for case_id in SHORT_HIGH_CASES:
        case = cases[case_id]
        rise_ns, reverse_ns = base.command_times(case)
        active_end_ns = max(end for _, end in base.transition_windows(case))
        path = RESULT_ROOT / "cases" / case_id / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0"
        data = parse_hspice_tr0(path)
        t = t_ns(data)
        kd = sig(data, "v(kd)")
        markers = recovery_markers(t, kd, reverse_ns, active_end_ns)
        row: dict[str, object] = {
            "case_id": case_id,
            "pulse_width_ns": case.pulse_width_ns,
            "rising_edge_ns": rise_ns,
            "reverse_edge_ns": reverse_ns,
            "active_end_ns": active_end_ns,
            "hspice_kd_min": markers["kd_min"],
            "hspice_kd_min_time_ns": markers["kd_min_time_ns"],
            "hspice_kd_final": markers["kd_final"],
            "hspice_recovery_10_ns": markers["recovery_10_ns"],
            "hspice_recovery_50_ns": markers["recovery_50_ns"],
            "hspice_recovery_90_ns": markers["recovery_90_ns"],
            "hspice_t_hold_10_ns": markers["recovery_10_ns"] - reverse_ns,
            "hspice_t_hold_50_ns": markers["recovery_50_ns"] - reverse_ns,
            "hspice_t_hold_90_ns": markers["recovery_90_ns"] - reverse_ns,
            "hspice_recovery_50_from_rising_ns": markers["recovery_50_ns"] - rise_ns,
            "hspice_min_to_10_delay_ns": markers["recovery_10_ns"] - markers["kd_min_time_ns"],
            "hspice_main_slope_tau_10_90_ns": markers["main_slope_tau_10_90_ns"],
        }
        rows.append(row)
    return rows


def build_candidate_comparison_rows(hspice_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    hspice_by_case = {str(row["case_id"]): row for row in hspice_rows}
    timing_rows = read_csv(RESULT_ROOT / "kd_recovery_diagnostics" / "recovery_timing_summary.csv")
    rows: list[dict[str, object]] = []
    for row in timing_rows:
        case_id = row.get("case_id", "")
        flow = row.get("flow", "")
        if case_id not in SHORT_HIGH_CASES or flow not in COMPARE_FLOWS:
            continue
        reference = hspice_by_case[case_id]
        reverse_ns = float(row["input_fall_ns"])
        recover50 = float(row["kd_recover_50_ns"])
        model_hold = recover50 - reverse_ns
        hspice_hold = float(reference["hspice_t_hold_50_ns"])
        rows.append(
            {
                "case_id": case_id,
                "flow": flow,
                "pulse_width_ns": float(reference["pulse_width_ns"]),
                "reverse_edge_ns": reverse_ns,
                "kd_recover_50_ns": recover50,
                "t_hold_50_ns": model_hold,
                "hspice_t_hold_50_ns": hspice_hold,
                "t_hold_error_ps": (model_hold - hspice_hold) * 1e3,
                "kd_recover_lag_vs_hspice_ps": row.get("kd_recover_lag_vs_hspice_ps", ""),
                "pdonp_recover_max": row.get("pdonp_recover_max", ""),
            }
        )
    return rows


def plot_hspice_hold(rows: list[dict[str, object]], fit: dict[str, object]) -> None:
    pulse = np.asarray([float(row["pulse_width_ns"]) for row in rows], dtype=float)
    hold50 = np.asarray([float(row["hspice_t_hold_50_ns"]) for row in rows], dtype=float)
    hold10 = np.asarray([float(row["hspice_t_hold_10_ns"]) for row in rows], dtype=float)
    hold90 = np.asarray([float(row["hspice_t_hold_90_ns"]) for row in rows], dtype=float)
    tau = np.asarray([float(row["hspice_main_slope_tau_10_90_ns"]) for row in rows], dtype=float)
    labels = [str(row["case_id"]).replace("short_pulse_", "").replace("_high", "") for row in rows]

    xline = np.linspace(float(np.min(pulse)), float(np.max(pulse)), 100)
    h1 = float(fit["h1_constant_ns"])
    h2 = float(fit["h2_intercept_ns"]) + float(fit["h2_slope_ns_per_ns"]) * xline

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    axes[0].fill_between(pulse, hold10, hold90, color="#aec7e8", alpha=0.35, label="HSPICE 10%-90% recovery window")
    axes[0].plot(pulse, hold50, marker="o", lw=2.2, color="#1f77b4", label="HSPICE T_hold at Kd 50%")
    axes[0].plot(xline, np.full_like(xline, h1), color="#ff7f0e", lw=1.8, label=f"H1 constant {h1:.3f} ns")
    axes[0].plot(xline, h2, color="#2ca02c", lw=1.8, label=f"H2 {float(fit['h2_intercept_ns']):.3f}+{float(fit['h2_slope_ns_per_ns']):.3f}*pw")
    for x, y, label in zip(pulse, hold50, labels):
        axes[0].annotate(label, (x, y), textcoords="offset points", xytext=(6, 6))
    axes[0].set_xlabel("Short-high pulse width (ns)")
    axes[0].set_ylabel("T_hold from reverse edge (ns)")
    axes[0].set_title("HSPICE Kd recovery hold law", loc="left", fontweight="bold")
    axes[0].grid(True, color="#d8dde6")
    axes[0].legend(loc="best", frameon=False)

    axes[1].plot(pulse, tau, marker="s", lw=2.2, color="#9467bd", label="10%-90% main-slope tau")
    for x, y, label in zip(pulse, tau, labels):
        axes[1].annotate(label, (x, y), textcoords="offset points", xytext=(6, 6))
    axes[1].set_xlabel("Short-high pulse width (ns)")
    axes[1].set_ylabel("Kd recovery slope tau (ns)")
    axes[1].set_title("Recovery rate stays nearly fixed", loc="left", fontweight="bold")
    axes[1].grid(True, color="#d8dde6")
    axes[1].legend(loc="best", frameon=False)
    fig.savefig(OUT_DIR / "hspice_kd_hold_time_fit.png", dpi=180)
    plt.close(fig)


def plot_candidate_comparison(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    flow_labels = {
        "hspice_native_ibis": "HSPICE",
        "ngspice_two_state_directional_residual": "residual",
        "ngspice_two_state_directional_residual_recover_mean": "mean recover",
        "ngspice_two_state_directional_residual_recover_fast": "fast recover",
    }
    colors = {
        "hspice_native_ibis": "#1f77b4",
        "ngspice_two_state_directional_residual": "#d62728",
        "ngspice_two_state_directional_residual_recover_mean": "#2ca02c",
        "ngspice_two_state_directional_residual_recover_fast": "#9467bd",
    }
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    for flow in COMPARE_FLOWS:
        sub = [row for row in rows if row["flow"] == flow]
        if not sub:
            continue
        sub.sort(key=lambda row: float(row["pulse_width_ns"]))
        x = [float(row["pulse_width_ns"]) for row in sub]
        y = [float(row["t_hold_50_ns"]) for row in sub]
        err = [float(row["t_hold_error_ps"]) for row in sub]
        axes[0].plot(x, y, marker="o", lw=2.0, color=colors.get(flow), label=flow_labels.get(flow, flow))
        if flow != "hspice_native_ibis":
            axes[1].plot(x, err, marker="o", lw=2.0, color=colors.get(flow), label=flow_labels.get(flow, flow))
    axes[0].set_xlabel("Short-high pulse width (ns)")
    axes[0].set_ylabel("Kd recover-50 hold from reverse edge (ns)")
    axes[0].set_title("Candidate hold timing versus HSPICE", loc="left", fontweight="bold")
    axes[0].grid(True, color="#d8dde6")
    axes[0].legend(loc="best", frameon=False)
    axes[1].axhline(0.0, color="#333333", lw=1.0)
    axes[1].set_xlabel("Short-high pulse width (ns)")
    axes[1].set_ylabel("Hold-time error versus HSPICE (ps)")
    axes[1].set_title("Fixed candidates straddle the HSPICE law", loc="left", fontweight="bold")
    axes[1].grid(True, color="#d8dde6")
    axes[1].legend(loc="best", frameon=False)
    fig.savefig(OUT_DIR / "candidate_hold_time_comparison.png", dpi=180)
    plt.close(fig)


def write_readme(
    hspice_rows: list[dict[str, object]],
    fit: dict[str, object],
    comparison_rows: list[dict[str, object]],
) -> None:
    tau_values = [float(row["hspice_main_slope_tau_10_90_ns"]) for row in hspice_rows]
    tau_spread = max(tau_values) / min(tau_values) if len(tau_values) >= 2 else float("nan")
    h1 = float(fit["h1_constant_ns"])
    h1_spread = 100.0 * float(fit["h1_spread_fraction"])
    h1_rms_ps = 1e3 * float(fit["h1_residual_rms_ns"])
    h2_intercept = float(fit["h2_intercept_ns"])
    h2_slope = float(fit["h2_slope_ns_per_ns"])
    h2_rms_ps = 1e3 * float(fit["h2_residual_rms_ns"])
    lines = [
        "# Kd Recovery Hold-Time Diagnostic",
        "",
        "This diagnostic measures the HSPICE short-high Kd recovery hold time after the input reverse edge. It uses cached HSPICE native-IBIS data only; no simulations are run here.",
        "",
        "## Headline Finding",
        "",
        f"- HSPICE `T_hold50 = Kd_recover50 - reverse_edge` is not perfectly constant: constant-hold spread is `{h1_spread:.1f}%` with RMS residual `{h1_rms_ps:.1f} ps`.",
        f"- A linear hold law fits these three widths much better: `T_hold50 = {h2_intercept:.4f} + {h2_slope:.4f} * pulse_width` ns, RMS residual `{h2_rms_ps:.1f} ps`.",
        f"- The Kd 10%-90% recovery-rate tau remains nearly constant, spread `{tau_spread:.3f}x`, so the next model should change release/hold timing first, not the ramp tau.",
        f"- Verdict: `{fit['verdict']}`.",
        "",
        "## HSPICE Hold Measurements",
        "",
        "| Case | Pulse ns | Reverse ns | Kd min ns | Recover10 ns | Recover50 ns | Recover90 ns | T_hold50 ns | Tau10-90 ns |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in hspice_rows:
        lines.append(
            "| {case} | {pw:.3f} | {rev:.4f} | {tmin:.4f} | {t10:.4f} | {t50:.4f} | {t90:.4f} | {hold:.4f} | {tau:.4f} |".format(
                case=row["case_id"],
                pw=float(row["pulse_width_ns"]),
                rev=float(row["reverse_edge_ns"]),
                tmin=float(row["hspice_kd_min_time_ns"]),
                t10=float(row["hspice_recovery_10_ns"]),
                t50=float(row["hspice_recovery_50_ns"]),
                t90=float(row["hspice_recovery_90_ns"]),
                hold=float(row["hspice_t_hold_50_ns"]),
                tau=float(row["hspice_main_slope_tau_10_90_ns"]),
            )
        )
    lines.extend(
        [
            "",
            "## Candidate Hold Comparison",
            "",
            "| Case | Flow | T_hold50 ns | Error vs HSPICE ps | Recovery pulse max |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in comparison_rows:
        lines.append(
            "| {case} | {flow} | {hold:.4f} | {err:.1f} | {pulse} |".format(
                case=row["case_id"],
                flow=row["flow"],
                hold=float(row["t_hold_50_ns"]),
                err=float(row["t_hold_error_ps"]),
                pulse=row.get("pdonp_recover_max", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The existing mean/fast recovery candidates are fixed shifts, so they cross HSPICE at one pulse width and miss at the others.",
            "- The measured HSPICE law is better represented as `reverse_edge + hold(pulse_width)` followed by a nearly fixed fast recovery ramp.",
            "- A next candidate should implement this only on the short-high interrupted-turn-off path. Short-low behavior is already the healthier quadrant and should be used as a leakage/regression check.",
            "",
            "Figures:",
            "",
            "- `hspice_kd_hold_time_fit.png`",
            "- `candidate_hold_time_comparison.png`",
            "",
            "CSVs:",
            "",
            "- `hspice_kd_hold_time.csv`",
            "- `candidate_hold_time_comparison.csv`",
            "- `hold_law_fit_summary.csv`",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ensure_dir(OUT_DIR)
    hspice_rows = build_hspice_hold_rows()
    hold_fit = fit_hold_law(hspice_rows)
    comparison_rows = build_candidate_comparison_rows(hspice_rows)
    write_csv(OUT_DIR / "hspice_kd_hold_time.csv", hspice_rows)
    write_csv(OUT_DIR / "candidate_hold_time_comparison.csv", comparison_rows)
    write_csv(OUT_DIR / "hold_law_fit_summary.csv", [hold_fit])
    plot_hspice_hold(hspice_rows, hold_fit)
    plot_candidate_comparison(comparison_rows)
    write_readme(hspice_rows, hold_fit, comparison_rows)

    print(f"H1 constant hold = {float(hold_fit['h1_constant_ns']):.4f} ns")
    print(
        "H2 hold law = "
        f"{float(hold_fit['h2_intercept_ns']):.4f} + "
        f"{float(hold_fit['h2_slope_ns_per_ns']):.4f} * pulse_width ns"
    )
    print(f"VERDICT={hold_fit['verdict']}")
    print(f"OUT_DIR={OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
