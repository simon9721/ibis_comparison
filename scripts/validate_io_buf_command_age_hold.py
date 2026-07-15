from __future__ import annotations

import argparse
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
from spice_tool_paths import default_hspice  # noqa: E402
import run_io_buf_value_matched_replay_v2 as base  # noqa: E402
import run_io_buf_two_state_gate_model as two_state  # noqa: E402


RESULT_ROOT = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
OUT_DIR = RESULT_ROOT / "kd_recovery_diagnostics" / "command_age_hold"
DEFAULT_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
TRAINING_CASE_IDS = [
    "short_pulse_500ps_high",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
]
HELDOUT_CASE = base.StudyCase(
    "short_pulse_1p5ns_high",
    "Held-out 1.5 ns high pulse before output settles, 1 ps edges, 50 ohm + 2 pF",
    0.001,
    13.5,
    50.0,
    2.0,
    3.3,
    "short_high",
    1.5,
)
TOL_PS = 30.0


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


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


def recovery_markers(case: base.StudyCase, data: dict[str, np.ndarray]) -> dict[str, float]:
    rise_ns, reverse_ns = base.command_times(case)
    active_end_ns = max(end for _, end in base.transition_windows(case))
    t = t_ns(data)
    kd = sig(data, "v(kd)")
    mask = (t >= reverse_ns) & (t <= active_end_ns) & np.isfinite(kd)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(kd[mask], dtype=float)
    if len(tt) < 8:
        raise RuntimeError(f"Not enough Kd points for {case.case_id}")
    min_idx = int(np.nanargmin(yy))
    kd_min = float(yy[min_idx])
    kd_min_time = float(tt[min_idx])
    tail_start = active_end_ns - max(0.3, 0.15 * (active_end_ns - kd_min_time))
    tail = yy[tt >= tail_start]
    kd_final = float(np.median(tail)) if len(tail) else float(yy[-1])
    span = kd_final - kd_min
    if span <= 1e-4:
        raise RuntimeError(f"Kd recovery span is too small for {case.case_id}: {span}")
    t10 = crossing_time(tt, yy, kd_min + 0.10 * span, kd_min_time)
    t50 = crossing_time(tt, yy, kd_min + 0.50 * span, kd_min_time)
    t90 = crossing_time(tt, yy, kd_min + 0.90 * span, kd_min_time)
    tau = (t90 - t10) / math.log(9.0) if math.isfinite(t10) and math.isfinite(t90) and t90 > t10 else float("nan")
    return {
        "rising_edge_ns": rise_ns,
        "reverse_edge_ns": reverse_ns,
        "active_end_ns": active_end_ns,
        "command_age_ns": reverse_ns - rise_ns,
        "kd_min": kd_min,
        "kd_min_time_ns": kd_min_time,
        "kd_final": kd_final,
        "recovery_10_ns": t10,
        "recovery_50_ns": t50,
        "recovery_90_ns": t90,
        "t_hold_10_ns": t10 - reverse_ns,
        "t_hold_50_ns": t50 - reverse_ns,
        "t_hold_90_ns": t90 - reverse_ns,
        "main_slope_tau_10_90_ns": tau,
    }


def run_or_restore_heldout_hspice(ibis: Path, hspice: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    two_state.configure_base_globals()
    data, _deck, cache_row = base.run_hspice_native(HELDOUT_CASE, ibis, hspice, timeout_s)
    return data, cache_row


def load_training_case(case: base.StudyCase) -> dict[str, np.ndarray]:
    path = RESULT_ROOT / "cases" / case.case_id / "hspice_native_ibis" / f"{case.case_id}_hspice_native_ibis.tr0"
    if not path.exists():
        raise FileNotFoundError(path)
    return parse_hspice_tr0(path)


def build_rows(heldout_data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    cases_by_id = {case.case_id: case for case in base.build_cases(include_low=True)}
    rows: list[dict[str, object]] = []
    for case_id in TRAINING_CASE_IDS:
        case = cases_by_id[case_id]
        markers = recovery_markers(case, load_training_case(case))
        rows.append(
            {
                "case_id": case.case_id,
                "role": "train",
                "pulse_width_ns": case.pulse_width_ns,
                **markers,
            }
        )
    rows.append(
        {
            "case_id": HELDOUT_CASE.case_id,
            "role": "heldout",
            "pulse_width_ns": HELDOUT_CASE.pulse_width_ns,
            **recovery_markers(HELDOUT_CASE, heldout_data),
        }
    )
    return rows


def fit_training(rows: list[dict[str, object]]) -> dict[str, object]:
    train = [row for row in rows if row["role"] == "train"]
    x = np.asarray([float(row["command_age_ns"]) for row in train], dtype=float)
    y = np.asarray([float(row["t_hold_50_ns"]) for row in train], dtype=float)
    a_mat = np.vstack([x, np.ones_like(x)]).T
    slope, intercept = np.linalg.lstsq(a_mat, y, rcond=None)[0]
    pred = intercept + slope * x
    train_rms = float(np.sqrt(np.mean((y - pred) ** 2)))
    heldout = next(row for row in rows if row["role"] == "heldout")
    heldout_age = float(heldout["command_age_ns"])
    heldout_pred = float(intercept + slope * heldout_age)
    heldout_meas = float(heldout["t_hold_50_ns"])
    heldout_error_ps = (heldout_pred - heldout_meas) * 1e3
    verdict = "PASS" if abs(heldout_error_ps) <= TOL_PS else "FAIL"
    return {
        "fit_intercept_ns": float(intercept),
        "fit_slope_ns_per_ns": float(slope),
        "train_rms_ns": train_rms,
        "train_rms_ps": train_rms * 1e3,
        "heldout_case_id": heldout["case_id"],
        "heldout_command_age_ns": heldout_age,
        "heldout_predicted_t_hold_50_ns": heldout_pred,
        "heldout_measured_t_hold_50_ns": heldout_meas,
        "heldout_error_ps": heldout_error_ps,
        "tolerance_ps": TOL_PS,
        "verdict": verdict,
    }


def plot_validation(rows: list[dict[str, object]], fit: dict[str, object]) -> None:
    train = [row for row in rows if row["role"] == "train"]
    heldout = next(row for row in rows if row["role"] == "heldout")
    x_train = np.asarray([float(row["command_age_ns"]) for row in train], dtype=float)
    y_train = np.asarray([float(row["t_hold_50_ns"]) for row in train], dtype=float)
    x_held = float(heldout["command_age_ns"])
    y_held = float(heldout["t_hold_50_ns"])
    pred_held = float(fit["heldout_predicted_t_hold_50_ns"])
    tau_x = [float(row["command_age_ns"]) for row in rows]
    tau_y = [float(row["main_slope_tau_10_90_ns"]) for row in rows]

    x_line = np.linspace(min(tau_x) - 0.05, max(tau_x) + 0.05, 120)
    y_line = float(fit["fit_intercept_ns"]) + float(fit["fit_slope_ns_per_ns"]) * x_line

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    axes[0].plot(x_line, y_line, color="#2ca02c", lw=2.0, label=f"fit on 0.5/1/2 ns, RMS {float(fit['train_rms_ps']):.1f} ps")
    axes[0].scatter(x_train, y_train, s=72, color="#1f77b4", label="training HSPICE")
    axes[0].scatter([x_held], [y_held], s=90, color="#d62728", label="held-out HSPICE 1.5 ns")
    axes[0].scatter([x_held], [pred_held], s=90, marker="x", color="#111111", label="held-out prediction")
    axes[0].plot([x_held, x_held], [pred_held, y_held], color="#d62728", lw=1.4, ls=":")
    for row in rows:
        axes[0].annotate(
            str(row["case_id"]).replace("short_pulse_", "").replace("_high", ""),
            (float(row["command_age_ns"]), float(row["t_hold_50_ns"])),
            textcoords="offset points",
            xytext=(6, 6),
        )
    axes[0].set_xlabel("Command age at reverse edge (ns)")
    axes[0].set_ylabel("HSPICE T_hold50 (ns)")
    axes[0].set_title(f"Held-out command-age validation: {fit['verdict']}", loc="left", fontweight="bold")
    axes[0].grid(True, color="#d8dde6")
    axes[0].legend(loc="best", frameon=False)

    axes[1].plot(tau_x, tau_y, marker="s", lw=2.0, color="#9467bd", label="10%-90% main-slope tau")
    for row in rows:
        axes[1].annotate(
            str(row["case_id"]).replace("short_pulse_", "").replace("_high", ""),
            (float(row["command_age_ns"]), float(row["main_slope_tau_10_90_ns"])),
            textcoords="offset points",
            xytext=(6, 6),
        )
    axes[1].set_xlabel("Command age at reverse edge (ns)")
    axes[1].set_ylabel("Kd recovery slope tau (ns)")
    axes[1].set_title("Recovery rate check", loc="left", fontweight="bold")
    axes[1].grid(True, color="#d8dde6")
    axes[1].legend(loc="best", frameon=False)
    fig.savefig(OUT_DIR / "command_age_hold_heldout_validation.png", dpi=180)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]], fit: dict[str, object], cache_row: dict[str, object]) -> None:
    lines = [
        "# Command-Age Kd Hold Held-Out Validation",
        "",
        "This diagnostic tests whether the short-high Kd recovery hold law is real or just a two-parameter line through three points. It trains on the existing 0.5 ns, 1 ns, and 2 ns high-pulse cases, then predicts a held-out 1.5 ns high-pulse HSPICE reference.",
        "",
        "## Headline Finding",
        "",
        f"- Training law: `T_hold50 = {float(fit['fit_intercept_ns']):.4f} + {float(fit['fit_slope_ns_per_ns']):.4f} * command_age` ns.",
        f"- Training RMS: `{float(fit['train_rms_ps']):.1f} ps`.",
        f"- Held-out 1.5 ns predicted T_hold50: `{float(fit['heldout_predicted_t_hold_50_ns']):.4f} ns`.",
        f"- Held-out 1.5 ns measured T_hold50: `{float(fit['heldout_measured_t_hold_50_ns']):.4f} ns`.",
        f"- Held-out error: `{float(fit['heldout_error_ps']):+.1f} ps` with tolerance `+/-{float(fit['tolerance_ps']):.0f} ps`.",
        f"- Verdict: `{fit['verdict']}`.",
        f"- Held-out HSPICE reference source: `{cache_row.get('source', 'n/a')}`.",
        "",
        "## Measurements",
        "",
        "| Case | Role | Age ns | T_hold50 ns | Kd min ns | Tau10-90 ns |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {case} | {role} | {age:.4f} | {hold:.4f} | {tmin:.4f} | {tau:.4f} |".format(
                case=row["case_id"],
                role=row["role"],
                age=float(row["command_age_ns"]),
                hold=float(row["t_hold_50_ns"]),
                tmin=float(row["kd_min_time_ns"]),
                tau=float(row["main_slope_tau_10_90_ns"]),
            )
        )
    lines.extend(
        [
            "",
            "## Implementation Spec If Verdict Passes",
            "",
            "- Add an opt-in mode named `InputDrivenTwoStateGateDirectionalResidualCommandAgeHold`.",
            "- Keep directional maps, Kd residual, and normal long-pulse behavior unchanged.",
            "- On the rising input edge, launch an NMOS-off command-age clock independent of the delayed `GDN` node.",
            "- On a falling reverse edge during short-high interrupted turn-off, latch `AGE = t_reverse - t_turn_off_command`.",
            "- Compute `T_hold = A + B * clamp(AGE, 0.5 ns, 2.0 ns)` using the validated constants above.",
            "- Release Kd recovery at `reverse_edge + T_hold`, then use the existing fixed fast recovery shape/rate.",
            "- The new path must fire only for short-high interrupted turn-off. Long-pulse, short-low, and unrelated cases must remain unchanged to three significant figures versus directional-residual.",
            "",
            "## Interpretation Rule",
            "",
            "- If the held-out test passes, command-age is a causally usable latch variable and the next candidate is worth implementing.",
            "- If the held-out test fails, stop adding hold-law variants and report the ceiling: the two-state model captures directionality, residual undershoot, and fixed recovery rate, but interrupted-turn-off recovery needs command-phase information not exposed by IBIS.",
            "",
            "Files:",
            "",
            "- `command_age_hold_training_and_heldout.csv`",
            "- `command_age_hold_validation_summary.csv`",
            "- `command_age_hold_heldout_validation.png`",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate command-age Kd hold law on a held-out 1.5 ns HSPICE case.")
    parser.add_argument("--ibis", type=Path, default=DEFAULT_IBIS)
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--timeout-s", type=int, default=240)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dir(OUT_DIR)
    heldout_data, cache_row = run_or_restore_heldout_hspice(args.ibis, args.hspice, args.timeout_s)
    rows = build_rows(heldout_data)
    fit = fit_training(rows)
    write_csv(OUT_DIR / "command_age_hold_training_and_heldout.csv", rows)
    write_csv(OUT_DIR / "command_age_hold_validation_summary.csv", [fit])
    write_csv(OUT_DIR / "heldout_hspice_cache_manifest.csv", [cache_row])
    plot_validation(rows, fit)
    write_readme(rows, fit, cache_row)
    print(f"LAW=T_hold50={float(fit['fit_intercept_ns']):.4f}+{float(fit['fit_slope_ns_per_ns']):.4f}*age ns")
    print(f"HELDOUT_ERROR_PS={float(fit['heldout_error_ps']):+.1f}")
    print(f"VERDICT={fit['verdict']}")
    print(f"HELDOUT_HSPICE_SOURCE={cache_row.get('source', 'n/a')}")
    print(f"OUT_DIR={OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
