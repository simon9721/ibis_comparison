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

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
import run_io_buf_value_matched_replay_v2 as base  # noqa: E402


RESULT_ROOT = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
OUT_DIR = RESULT_ROOT / "kd_recovery_diagnostics" / "effective_tau"
SHORT_HIGH_CASES = [
    "short_pulse_500ps_high",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
]
MODEL_DEPTH_FLOWS = [
    "ngspice_two_state_directional_residual",
    "ngspice_two_state_directional_residual_recover_mean",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


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


def interp_at(t: np.ndarray, y: np.ndarray, x: float) -> float:
    return float(np.interp(x, t, y))


def crossing_time(t: np.ndarray, y: np.ndarray, level: float, start_ns: float, direction: str) -> float:
    mask = (t >= start_ns) & np.isfinite(y)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(y[mask], dtype=float)
    if len(tt) < 2:
        return float("nan")
    delta = yy - level
    if direction == "rising":
        idx = np.where((delta[:-1] < 0.0) & (delta[1:] >= 0.0))[0]
    else:
        idx = np.where((delta[:-1] > 0.0) & (delta[1:] <= 0.0))[0]
    if len(idx) == 0:
        return float("nan")
    i = int(idx[0])
    if yy[i + 1] == yy[i]:
        return float(tt[i])
    return float(tt[i] + (level - yy[i]) * (tt[i + 1] - tt[i]) / (yy[i + 1] - yy[i]))


def fit_hspice_recovery_tau(
    t: np.ndarray,
    kd: np.ndarray,
    reverse_ns: float,
    active_end_ns: float,
) -> dict[str, float]:
    """
    Fit HSPICE Kd recovery from its post-reverse minimum to settled high.

    For short-high pulses, Kd is still near 1 at the input falling edge. The
    delayed rising-edge response then turns Kd off, and only after that does Kd
    recover. Therefore the physically meaningful recovery fit starts at Kd_min,
    not at the input reverse edge.
    """
    def result(
        *,
        tau_ns: float = float("nan"),
        main_slope_tau_10_90_ns: float = float("nan"),
        recovery_10_ns: float = float("nan"),
        recovery_50_ns: float = float("nan"),
        recovery_90_ns: float = float("nan"),
        delay_min_to_10_ns: float = float("nan"),
        fit_start_ns: float = float("nan"),
        fit_end_ns: float = float("nan"),
        kd_start: float = float("nan"),
        kd_final: float = float("nan"),
        n_fit: int = 0,
        fit_rmse: float = float("nan"),
        fit_r2: float = float("nan"),
    ) -> dict[str, float]:
        return {
            "tau_ns": tau_ns,
            "main_slope_tau_10_90_ns": main_slope_tau_10_90_ns,
            "recovery_10_ns": recovery_10_ns,
            "recovery_50_ns": recovery_50_ns,
            "recovery_90_ns": recovery_90_ns,
            "delay_min_to_10_ns": delay_min_to_10_ns,
            "fit_start_ns": fit_start_ns,
            "fit_end_ns": fit_end_ns,
            "kd_start": kd_start,
            "kd_final": kd_final,
            "n_fit": n_fit,
            "fit_rmse": fit_rmse,
            "fit_r2": fit_r2,
        }

    mask = (t >= reverse_ns) & (t <= active_end_ns) & np.isfinite(kd)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(kd[mask], dtype=float)
    if len(tt) < 8:
        return result()

    min_idx = int(np.nanargmin(yy))
    fit_start_ns = float(tt[min_idx])
    kd_start = float(yy[min_idx])
    tail_start = active_end_ns - max(0.3, 0.15 * (active_end_ns - fit_start_ns))
    tail = yy[tt >= tail_start]
    kd_final = float(np.median(tail)) if len(tail) else float(yy[-1])
    span = kd_final - kd_start
    if span <= 1e-4:
        return result(fit_start_ns=fit_start_ns, fit_end_ns=active_end_ns, kd_start=kd_start, kd_final=kd_final)

    after = tt >= fit_start_ns
    x_all = tt[after] - fit_start_ns
    y_all = yy[after]
    frac_remaining = (kd_final - y_all) / span
    good = (frac_remaining > 0.03) & (frac_remaining < 0.95) & np.isfinite(frac_remaining)
    if int(np.sum(good)) < 4:
        return result(
            fit_start_ns=fit_start_ns,
            fit_end_ns=active_end_ns,
            kd_start=kd_start,
            kd_final=kd_final,
            n_fit=int(np.sum(good)),
        )

    x = x_all[good]
    z = np.log(frac_remaining[good])
    # Force the exponential to start at kd_start when x=0. This avoids hiding
    # onset/shape error in an arbitrary intercept.
    slope = float(np.dot(x, z) / np.dot(x, x))
    tau = -1.0 / slope if slope < 0 else float("nan")
    fit_y = kd_final - span * np.exp(-x / tau) if math.isfinite(tau) else np.full_like(x, np.nan)
    residual = y_all[good] - fit_y
    fit_rmse = float(np.sqrt(np.mean(residual * residual)))
    denom = float(np.sum((y_all[good] - np.mean(y_all[good])) ** 2))
    fit_r2 = 1.0 - float(np.sum(residual * residual)) / denom if denom > 0 else float("nan")
    level_10 = kd_start + 0.10 * span
    level_50 = kd_start + 0.50 * span
    level_90 = kd_start + 0.90 * span
    t10 = crossing_time(tt, yy, level_10, fit_start_ns, "rising")
    t50 = crossing_time(tt, yy, level_50, fit_start_ns, "rising")
    t90 = crossing_time(tt, yy, level_90, fit_start_ns, "rising")
    main_slope_tau = (t90 - t10) / math.log(9.0) if math.isfinite(t10) and math.isfinite(t90) and t90 > t10 else float("nan")
    apparent_delay_to_10 = t10 - fit_start_ns if math.isfinite(t10) else float("nan")
    return result(
        tau_ns=float(tau),
        main_slope_tau_10_90_ns=float(main_slope_tau),
        recovery_10_ns=t10,
        recovery_50_ns=t50,
        recovery_90_ns=t90,
        delay_min_to_10_ns=float(apparent_delay_to_10),
        fit_start_ns=fit_start_ns,
        fit_end_ns=active_end_ns,
        kd_start=kd_start,
        kd_final=kd_final,
        n_fit=int(np.sum(good)),
        fit_rmse=fit_rmse,
        fit_r2=fit_r2,
    )


def model_depth_metrics(case_id: str, reverse_ns: float, fit_start_ns: float, active_end_ns: float) -> dict[str, object]:
    row: dict[str, object] = {}
    case_dir = RESULT_ROOT / "cases" / case_id
    for flow in MODEL_DEPTH_FLOWS:
        raw = case_dir / flow / f"{case_id}_{flow}.raw"
        key = flow.removeprefix("ngspice_")
        if not raw.exists():
            continue
        try:
            data = parse_ngspice_raw(raw)
            rt = t_ns(data)
            gdn = sig(data, "v(xdrv.gdn)", "v(xdrv:gdn)")
            gdntarget = sig(data, "v(xdrv.gdntarget)", "v(xdrv:gdntarget)")
            local = (rt >= reverse_ns) & (rt <= active_end_ns)
            pre_fit = (rt >= reverse_ns) & (rt <= fit_start_ns)
            row[f"{key}_gdn_at_input_reverse"] = interp_at(rt, gdn, reverse_ns)
            row[f"{key}_gdn_at_hspice_kd_min_time"] = interp_at(rt, gdn, fit_start_ns)
            row[f"{key}_gdn_min_reverse_to_active_end"] = float(np.nanmin(gdn[local])) if np.any(local) else float("nan")
            row[f"{key}_gdn_min_reverse_to_hspice_kd_min"] = float(np.nanmin(gdn[pre_fit])) if np.any(pre_fit) else float("nan")
            row[f"{key}_gdntarget_at_input_reverse"] = interp_at(rt, gdntarget, reverse_ns)
            row[f"{key}_gdntarget_at_hspice_kd_min_time"] = interp_at(rt, gdntarget, fit_start_ns)
        except Exception as exc:
            row[f"{key}_depth_error"] = repr(exc)
    return row


def build_rows() -> list[dict[str, object]]:
    cases = {case.case_id: case for case in base.build_cases(include_low=True)}
    rows: list[dict[str, object]] = []
    for case_id in SHORT_HIGH_CASES:
        case = cases[case_id]
        _, reverse_ns = base.command_times(case)
        active_end_ns = max(end for _, end in base.transition_windows(case))
        h_path = RESULT_ROOT / "cases" / case_id / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0"
        h = parse_hspice_tr0(h_path)
        ht = t_ns(h)
        hkd = sig(h, "v(kd)")
        fit = fit_hspice_recovery_tau(ht, hkd, reverse_ns, active_end_ns)
        row: dict[str, object] = {
            "case_id": case_id,
            "pulse_width_ns": case.pulse_width_ns,
            "reverse_edge_ns": reverse_ns,
            "active_end_ns": active_end_ns,
            "hspice_kd_at_input_reverse": interp_at(ht, hkd, reverse_ns),
            "hspice_kd_min": fit["kd_start"],
            "hspice_kd_min_time_ns": fit["fit_start_ns"],
            "hspice_kd_final": fit["kd_final"],
            "hspice_kd_off_depth": fit["kd_final"] - fit["kd_start"],
            "hspice_effective_tau_ns": fit["tau_ns"],
            "hspice_main_slope_tau_10_90_ns": fit["main_slope_tau_10_90_ns"],
            "hspice_recovery_10_ns": fit["recovery_10_ns"],
            "hspice_recovery_50_ns": fit["recovery_50_ns"],
            "hspice_recovery_90_ns": fit["recovery_90_ns"],
            "hspice_delay_min_to_10_ns": fit["delay_min_to_10_ns"],
            "hspice_tau_fit_n": fit["n_fit"],
            "hspice_tau_fit_rmse": fit["fit_rmse"],
            "hspice_tau_fit_r2": fit["fit_r2"],
        }
        row.update(model_depth_metrics(case_id, reverse_ns, fit["fit_start_ns"], active_end_ns))
        rows.append(row)
    return rows


def plot_rows(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    pulse = np.asarray([float(row["pulse_width_ns"]) for row in rows], dtype=float)
    tau = np.asarray([float(row["hspice_effective_tau_ns"]) for row in rows], dtype=float)
    main_tau = np.asarray([float(row["hspice_main_slope_tau_10_90_ns"]) for row in rows], dtype=float)
    depth = np.asarray([float(row["hspice_kd_off_depth"]) for row in rows], dtype=float)
    kd_min = np.asarray([float(row["hspice_kd_min"]) for row in rows], dtype=float)
    labels = [str(row["case_id"]).replace("short_pulse_", "").replace("_high", "") for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    axes[0].plot(pulse, tau, marker="o", lw=2.0, color="#1f77b4", label="apparent min-to-final tau")
    axes[0].plot(pulse, main_tau, marker="s", lw=2.0, color="#2ca02c", label="10%-90% main-slope tau")
    for x, y, label in zip(pulse, tau, labels):
        axes[0].annotate(label, (x, y), textcoords="offset points", xytext=(6, 6))
    axes[0].set_xlabel("Short-high pulse width (ns)")
    axes[0].set_ylabel("HSPICE Kd recovery tau metric (ns)")
    axes[0].set_title("Recovery tau versus pulse width", loc="left", fontweight="bold")
    axes[0].grid(True, color="#d8dde6")
    axes[0].legend(loc="best", frameon=False)

    axes[1].plot(depth, tau, marker="o", lw=2.0, color="#d62728", label="apparent min-to-final tau")
    axes[1].plot(depth, main_tau, marker="s", lw=2.0, color="#9467bd", label="10%-90% main-slope tau")
    for x, y, label, kmin in zip(depth, tau, labels, kd_min):
        axes[1].annotate(f"{label}\nKd_min={kmin:.3f}", (x, y), textcoords="offset points", xytext=(6, 6))
    axes[1].set_xlabel("HSPICE Kd off-depth (Kd_final - Kd_min)")
    axes[1].set_ylabel("HSPICE Kd recovery tau metric (ns)")
    axes[1].set_title("Recovery tau versus interruption depth", loc="left", fontweight="bold")
    axes[1].grid(True, color="#d8dde6")
    axes[1].legend(loc="best", frameon=False)
    fig.savefig(OUT_DIR / "hspice_effective_tau_vs_depth.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(len(rows), 1, figsize=(10.8, 8.0), sharex=False, constrained_layout=True)
    if len(rows) == 1:
        axes = [axes]
    for ax, row in zip(axes, rows):
        case_id = str(row["case_id"])
        h_path = RESULT_ROOT / "cases" / case_id / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0"
        h = parse_hspice_tr0(h_path)
        ht = t_ns(h)
        hkd = sig(h, "v(kd)")
        reverse = float(row["reverse_edge_ns"])
        start = float(row["hspice_kd_min_time_ns"])
        end = float(row["active_end_ns"])
        tau_value = float(row["hspice_effective_tau_ns"])
        kd_start = float(row["hspice_kd_min"])
        kd_final = float(row["hspice_kd_final"])
        model = kd_final - (kd_final - kd_start) * np.exp(-(ht - start) / tau_value)
        model[ht < start] = np.nan
        ax.plot(ht, hkd, color="#1f77b4", lw=2.0, label="HSPICE Kd")
        ax.plot(ht, model, color="#d62728", lw=1.5, label=f"apparent fit tau={tau_value:.3f} ns")
        ax.axvline(reverse, color="#333333", lw=1.0, ls=":", label="input reverse")
        ax.axvline(start, color="#ff7f0e", lw=1.0, ls=":", label="Kd min / fit start")
        for marker_key, color, label in [
            ("hspice_recovery_10_ns", "#2ca02c", "10%"),
            ("hspice_recovery_50_ns", "#9467bd", "50%"),
            ("hspice_recovery_90_ns", "#8c564b", "90%"),
        ]:
            marker_t = float(row[marker_key])
            if math.isfinite(marker_t):
                ax.axvline(marker_t, color=color, lw=0.9, ls="--", label=label)
        ax.set_xlim(max(0, reverse - 0.4), end + 0.3)
        ax.set_ylabel("Kd")
        ax.set_title(case_id, loc="left", fontweight="bold")
        ax.grid(True, color="#d8dde6")
        ax.legend(loc="best", frameon=False, ncol=4)
    axes[-1].set_xlabel("Time (ns)")
    fig.savefig(OUT_DIR / "hspice_kd_recovery_tau_fits.png", dpi=180)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]]) -> None:
    finite_taus = [float(row["hspice_effective_tau_ns"]) for row in rows if math.isfinite(float(row["hspice_effective_tau_ns"]))]
    finite_main = [float(row["hspice_main_slope_tau_10_90_ns"]) for row in rows if math.isfinite(float(row["hspice_main_slope_tau_10_90_ns"]))]
    spread = max(finite_taus) / min(finite_taus) if len(finite_taus) >= 2 else float("nan")
    main_spread = max(finite_main) / min(finite_main) if len(finite_main) >= 2 else float("nan")
    verdict = "NONLINEAR_OR_MULTI_STAGE_RECOVERY" if math.isfinite(spread) and spread >= 1.25 else "APPROX_LINEAR_APPARENT_RECOVERY"
    lines = [
        "# Effective Kd Recovery Tau Diagnostic",
        "",
        "This diagnostic fits the HSPICE native-IBIS Kd recovery after the post-reverse Kd minimum, not directly from the input reverse edge. That matters because in short-high pulses Kd is still near its on-state at the input falling edge; the delayed rising-edge response turns Kd off first, then Kd recovers.",
        "",
        f"- Apparent min-to-final tau spread: `{spread:.3f}x`",
        f"- Main-slope 10%-90% tau spread: `{main_spread:.3f}x`",
        f"- Verdict: `{verdict}`",
        "- The apparent exponential fit is intentionally reported with RMSE/R2. Poor R2 means the recovery is not a clean one-pole exponential; use the tau as a diagnostic, not as a direct parameter table.",
        "",
        "| Case | Pulse ns | HSPICE Kd min | Kd off-depth | Apparent tau ns | 10-90 tau ns | Min-to-10 delay ns | Fit RMSE | Fit R2 | Residual GDN at input reverse | Residual GDN min |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {case} | {pulse:.3f} | {kdmin:.4f} | {depth:.4f} | {tau:.4f} | {main_tau:.4f} | {delay10:.4f} | {rmse:.5f} | {r2:.4f} | {grev:.4f} | {gmin:.4f} |".format(
                case=row["case_id"],
                pulse=float(row["pulse_width_ns"]),
                kdmin=float(row["hspice_kd_min"]),
                depth=float(row["hspice_kd_off_depth"]),
                tau=float(row["hspice_effective_tau_ns"]),
                main_tau=float(row["hspice_main_slope_tau_10_90_ns"]),
                delay10=float(row["hspice_delay_min_to_10_ns"]),
                rmse=float(row["hspice_tau_fit_rmse"]),
                r2=float(row["hspice_tau_fit_r2"]),
                grev=float(row.get("two_state_directional_residual_gdn_at_input_reverse", float("nan"))),
                gmin=float(row.get("two_state_directional_residual_gdn_min_reverse_to_active_end", float("nan"))),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- If the apparent HSPICE tau changes strongly with pulse width or Kd off-depth, the NMOS re-turn-on is not well represented by one constant recovery law.",
            "- If the 10%-90% tau is steadier than the apparent tau, then much of the width-dependence is delayed/flat early recovery rather than the main slope itself.",
            "- `Residual GDN at input reverse` is included as a sanity check. In this delayed-gate model it stays near 1 at the input reverse edge, so it is not a useful interruption-depth variable by itself.",
            "- `HSPICE Kd min` / `Kd off-depth` is the better observable depth proxy because it comes from the golden coefficient waveform.",
            "",
            "Figures:",
            "",
            "- `hspice_effective_tau_vs_depth.png`",
            "- `hspice_kd_recovery_tau_fits.png`",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ensure_dir(OUT_DIR)
    rows = build_rows()
    write_csv(OUT_DIR / "hspice_effective_kd_recovery_tau.csv", rows)
    plot_rows(rows)
    write_readme(rows)
    for row in rows:
        print(
            f"{row['case_id']}: apparent_tau={float(row['hspice_effective_tau_ns']):.4f} ns, "
            f"main_tau_10_90={float(row['hspice_main_slope_tau_10_90_ns']):.4f} ns, "
            f"Kd_min={float(row['hspice_kd_min']):.4f}, depth={float(row['hspice_kd_off_depth']):.4f}, "
            f"fit_rmse={float(row['hspice_tau_fit_rmse']):.5f}"
        )
    print(f"OUT_DIR={OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
