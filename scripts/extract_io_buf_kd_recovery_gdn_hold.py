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
OUT_DIR = RESULT_ROOT / "kd_recovery_diagnostics" / "gdn_hold_time"
SHORT_HIGH_CASES = [
    "short_pulse_500ps_high",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
]
GDN_ON = 1.0
GDN_FLOWS = [
    "ngspice_two_state_identity",
    "ngspice_two_state_pwl",
    "ngspice_two_state_directional",
    "ngspice_two_state_directional_residual",
    "ngspice_two_state_directional_residual_recover_mean",
    "ngspice_two_state_directional_residual_recover_fast",
]
PRIMARY_GDN_FLOW = "ngspice_two_state_directional_residual"


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


def hspice_recovery_markers(t: np.ndarray, kd: np.ndarray, reverse_ns: float, active_end_ns: float) -> dict[str, float]:
    mask = (t >= reverse_ns) & (t <= active_end_ns) & np.isfinite(kd)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(kd[mask], dtype=float)
    if len(tt) < 8:
        return {}
    min_idx = int(np.nanargmin(yy))
    kd_min = float(yy[min_idx])
    kd_min_time = float(tt[min_idx])
    tail_start = active_end_ns - max(0.3, 0.15 * (active_end_ns - kd_min_time))
    tail = yy[tt >= tail_start]
    kd_final = float(np.median(tail)) if len(tail) else float(yy[-1])
    span = kd_final - kd_min
    if span <= 1e-4:
        return {}
    t10 = crossing_time(tt, yy, kd_min + 0.10 * span, kd_min_time)
    t50 = crossing_time(tt, yy, kd_min + 0.50 * span, kd_min_time)
    t90 = crossing_time(tt, yy, kd_min + 0.90 * span, kd_min_time)
    tau = (t90 - t10) / math.log(9.0) if math.isfinite(t10) and math.isfinite(t90) and t90 > t10 else float("nan")
    return {
        "hspice_kd_min": kd_min,
        "hspice_kd_min_time_ns": kd_min_time,
        "hspice_kd_final": kd_final,
        "hspice_recovery_10_ns": t10,
        "hspice_recovery_50_ns": t50,
        "hspice_recovery_90_ns": t90,
        "hspice_t_hold_50_ns": t50 - reverse_ns,
        "hspice_main_slope_tau_10_90_ns": tau,
    }


def gdn_metrics(case_id: str, flow: str, reverse_ns: float, active_end_ns: float) -> dict[str, object]:
    raw = RESULT_ROOT / "cases" / case_id / flow / f"{case_id}_{flow}.raw"
    if not raw.exists():
        return {"gdn_error": "raw_missing"}
    try:
        data = parse_ngspice_raw(raw)
        t = t_ns(data)
        gdn = sig(data, "v(xdrv.gdn)", "v(xdrv:gdn)")
        gdntarget = sig(data, "v(xdrv.gdntarget)", "v(xdrv:gdntarget)")
        local = (t >= reverse_ns) & (t <= active_end_ns)
        return {
            "gdn_at_reverse": float(np.interp(reverse_ns, t, gdn)),
            "gdn_min_reverse_to_active_end": float(np.nanmin(gdn[local])) if np.any(local) else float("nan"),
            "gdn_target_at_reverse": float(np.interp(reverse_ns, t, gdntarget)),
            "gdn_target_min_reverse_to_active_end": float(np.nanmin(gdntarget[local])) if np.any(local) else float("nan"),
        }
    except Exception as exc:
        return {"gdn_error": repr(exc)}


def linfit(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    good = np.isfinite(x) & np.isfinite(y)
    x = x[good]
    y = y[good]
    if len(x) < 2:
        return {"slope": float("nan"), "intercept": float("nan"), "rms_ns": float("nan")}
    a = np.vstack([x, np.ones_like(x)]).T
    slope, intercept = np.linalg.lstsq(a, y, rcond=None)[0]
    pred = slope * x + intercept
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "rms_ns": float(np.sqrt(np.mean((y - pred) ** 2))),
    }


def origin_forced_depth_fit(gdn: np.ndarray, hold: np.ndarray) -> dict[str, float]:
    depth = GDN_ON - np.asarray(gdn, dtype=float)
    hold = np.asarray(hold, dtype=float)
    good = np.isfinite(depth) & np.isfinite(hold)
    depth = depth[good]
    hold = hold[good]
    if len(depth) < 2 or float(np.dot(depth, depth)) <= 0.0:
        return {"k_ns": float("nan"), "rms_ns": float("nan")}
    k = float(np.dot(depth, hold) / np.dot(depth, depth))
    pred = k * depth
    return {"k_ns": k, "rms_ns": float(np.sqrt(np.mean((hold - pred) ** 2)))}


def build_rows() -> list[dict[str, object]]:
    cases = {case.case_id: case for case in base.build_cases(include_low=True)}
    rows: list[dict[str, object]] = []
    for case_id in SHORT_HIGH_CASES:
        case = cases[case_id]
        rise_ns, reverse_ns = base.command_times(case)
        active_end_ns = max(end for _, end in base.transition_windows(case))
        h_path = RESULT_ROOT / "cases" / case_id / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0"
        h = parse_hspice_tr0(h_path)
        ht = t_ns(h)
        hkd = sig(h, "v(kd)")
        markers = hspice_recovery_markers(ht, hkd, reverse_ns, active_end_ns)
        for flow in GDN_FLOWS:
            row: dict[str, object] = {
                "case_id": case_id,
                "flow": flow,
                "pulse_width_ns": case.pulse_width_ns,
                "rising_edge_ns": rise_ns,
                "reverse_edge_ns": reverse_ns,
                "active_end_ns": active_end_ns,
            }
            row.update(markers)
            row.update(gdn_metrics(case_id, flow, reverse_ns, active_end_ns))
            rows.append(row)
    return rows


def fit_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    primary = [row for row in rows if row.get("flow") == PRIMARY_GDN_FLOW]
    pulse = np.asarray([float(row["pulse_width_ns"]) for row in primary], dtype=float)
    hold = np.asarray([float(row["hspice_t_hold_50_ns"]) for row in primary], dtype=float)
    pulse_fit = linfit(pulse, hold)
    summaries: list[dict[str, object]] = [
        {
            "predictor": "pulse_width_reference",
            "flow": "",
            "slope": pulse_fit["slope"],
            "intercept": pulse_fit["intercept"],
            "rms_ns": pulse_fit["rms_ns"],
            "rms_ps": pulse_fit["rms_ns"] * 1e3,
            "physical_limit_at_gdn_on_ns": "",
            "origin_forced_k_ns": "",
            "origin_forced_rms_ns": "",
            "verdict": "REFERENCE_CAUSAL_AGE_BUT_NOT_GATE_STATE",
        }
    ]
    for flow in GDN_FLOWS:
        sub = [row for row in rows if row.get("flow") == flow]
        gdn = np.asarray([float(row.get("gdn_at_reverse", float("nan"))) for row in sub], dtype=float)
        hold = np.asarray([float(row["hspice_t_hold_50_ns"]) for row in sub], dtype=float)
        gfit = linfit(gdn, hold)
        ofit = origin_forced_depth_fit(gdn, hold)
        limit = gfit["intercept"] + gfit["slope"] * GDN_ON if math.isfinite(gfit["intercept"]) else float("nan")
        distinct_gdn = len({round(float(x), 6) for x in gdn if math.isfinite(float(x))})
        if distinct_gdn < len(sub):
            verdict = "GDN_AT_REVERSE_COLLAPSES_WIDTHS"
        elif math.isfinite(limit) and abs(limit) > 0.15:
            verdict = "LINEAR_GDN_FAILS_ZERO_HOLD_LIMIT"
        elif math.isfinite(gfit["rms_ns"]) and gfit["rms_ns"] <= 1.5 * pulse_fit["rms_ns"]:
            verdict = "GDN_KEYING_COMPARABLE"
        else:
            verdict = "GDN_KEYING_WEAK"
        summaries.append(
            {
                "predictor": "gdn_at_reverse",
                "flow": flow,
                "slope": gfit["slope"],
                "intercept": gfit["intercept"],
                "rms_ns": gfit["rms_ns"],
                "rms_ps": gfit["rms_ns"] * 1e3,
                "physical_limit_at_gdn_on_ns": limit,
                "origin_forced_k_ns": ofit["k_ns"],
                "origin_forced_rms_ns": ofit["rms_ns"],
                "origin_forced_rms_ps": ofit["rms_ns"] * 1e3,
                "distinct_gdn_values": distinct_gdn,
                "verdict": verdict,
            }
        )
    return summaries


def plot_rows(rows: list[dict[str, object]], summaries: list[dict[str, object]]) -> None:
    primary = [row for row in rows if row.get("flow") == PRIMARY_GDN_FLOW]
    pulse = np.asarray([float(row["pulse_width_ns"]) for row in primary], dtype=float)
    hold = np.asarray([float(row["hspice_t_hold_50_ns"]) for row in primary], dtype=float)
    gdn = np.asarray([float(row["gdn_at_reverse"]) for row in primary], dtype=float)
    labels = [str(row["case_id"]).replace("short_pulse_", "").replace("_high", "") for row in primary]
    pulse_fit = next(row for row in summaries if row["predictor"] == "pulse_width_reference")
    gdn_fit = next(row for row in summaries if row.get("flow") == PRIMARY_GDN_FLOW)

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    xline = np.linspace(float(np.min(pulse)), float(np.max(pulse)), 100)
    axes[0].plot(pulse, hold, marker="o", lw=2.2, color="#1f77b4", label="HSPICE T_hold50")
    axes[0].plot(
        xline,
        float(pulse_fit["intercept"]) + float(pulse_fit["slope"]) * xline,
        color="#2ca02c",
        lw=1.8,
        label=f"pulse-width fit, RMS {float(pulse_fit['rms_ps']):.1f} ps",
    )
    for x, y, label in zip(pulse, hold, labels):
        axes[0].annotate(label, (x, y), textcoords="offset points", xytext=(6, 6))
    axes[0].set_xlabel("Pulse width / command age at reverse (ns)")
    axes[0].set_ylabel("HSPICE T_hold50 (ns)")
    axes[0].set_title("Age-keyed reference fit", loc="left", fontweight="bold")
    axes[0].grid(True, color="#d8dde6")
    axes[0].legend(loc="best", frameon=False)

    axes[1].scatter(gdn, hold, s=60, color="#d62728", label="GDN@reverse samples")
    finite = np.isfinite(gdn)
    if np.sum(finite) >= 2:
        gx = np.linspace(min(0.0, float(np.nanmin(gdn)) - 0.05), max(1.05, float(np.nanmax(gdn)) + 0.05), 100)
        axes[1].plot(
            gx,
            float(gdn_fit["intercept"]) + float(gdn_fit["slope"]) * gx,
            color="#9467bd",
            lw=1.8,
            label=f"GDN fit, RMS {float(gdn_fit['rms_ps']):.1f} ps",
        )
        k = float(gdn_fit.get("origin_forced_k_ns", float("nan")))
        if math.isfinite(k):
            axes[1].plot(gx, k * (GDN_ON - gx), color="#ff7f0e", lw=1.8, label="origin-forced depth fit")
    for x, y, label in zip(gdn, hold, labels):
        axes[1].annotate(label, (x, y), textcoords="offset points", xytext=(6, 6))
    axes[1].axvline(GDN_ON, color="#333333", lw=1.0, ls=":", label="GDN_ON")
    axes[1].set_xlabel(f"{PRIMARY_GDN_FLOW} GDN at reverse")
    axes[1].set_ylabel("HSPICE T_hold50 (ns)")
    axes[1].set_title("Current GDN state is not enough", loc="left", fontweight="bold")
    axes[1].grid(True, color="#d8dde6")
    axes[1].legend(loc="best", frameon=False)
    fig.savefig(OUT_DIR / "gdn_keyed_hold_fit.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    for flow in GDN_FLOWS:
        sub = [row for row in rows if row.get("flow") == flow]
        sub.sort(key=lambda row: float(row["pulse_width_ns"]))
        ax.plot(
            [float(row["pulse_width_ns"]) for row in sub],
            [float(row.get("gdn_at_reverse", float("nan"))) for row in sub],
            marker="o",
            lw=1.8,
            label=flow.replace("ngspice_two_state_", ""),
        )
    ax.set_xlabel("Short-high pulse width (ns)")
    ax.set_ylabel("GDN at reverse edge")
    ax.set_title("GDN at reverse collapses the two shortest widths", loc="left", fontweight="bold")
    ax.grid(True, color="#d8dde6")
    ax.legend(loc="best", frameon=False, fontsize=8)
    fig.savefig(OUT_DIR / "gdn_at_reverse_by_variant.png", dpi=180)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]], summaries: list[dict[str, object]]) -> None:
    pulse_fit = next(row for row in summaries if row["predictor"] == "pulse_width_reference")
    primary_fit = next(row for row in summaries if row.get("flow") == PRIMARY_GDN_FLOW)
    primary_rows = [row for row in rows if row.get("flow") == PRIMARY_GDN_FLOW]
    lines = [
        "# GDN-Keyed Kd Recovery Hold Diagnostic",
        "",
        "This diagnostic checks whether the short-high Kd hold law can be keyed to `GDN` at the reverse edge, which would be a causal gate-state variable. It uses cached HSPICE and ngspice raw data only.",
        "",
        "## Headline Finding",
        "",
        f"- Pulse-width/command-age fit remains strong: RMS `{float(pulse_fit['rms_ps']):.1f} ps`.",
        f"- Current `{PRIMARY_GDN_FLOW}` `GDN@reverse` fit is weaker: RMS `{float(primary_fit['rms_ps']):.1f} ps`.",
        f"- The current GDN state collapses 500 ps and 1 ns to essentially the same value, so it cannot distinguish their different HSPICE hold times.",
        f"- Linear GDN physical-limit check predicts hold `{float(primary_fit['physical_limit_at_gdn_on_ns']):.4f} ns` at `GDN_ON=1`, not `0 ns`; the origin-forced depth form has RMS `{float(primary_fit['origin_forced_rms_ps']):.1f} ps`.",
        f"- Verdict: `{primary_fit['verdict']}`. Do not implement the next candidate using the present `GDN@reverse` alone.",
        "",
        "## Primary Samples",
        "",
        "| Case | Pulse ns | HSPICE T_hold50 ns | GDN@reverse | GDN min after reverse | Main tau ns |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in primary_rows:
        lines.append(
            "| {case} | {pw:.3f} | {hold:.4f} | {gdn:.4f} | {gmin:.4f} | {tau:.4f} |".format(
                case=row["case_id"],
                pw=float(row["pulse_width_ns"]),
                hold=float(row["hspice_t_hold_50_ns"]),
                gdn=float(row["gdn_at_reverse"]),
                gmin=float(row["gdn_min_reverse_to_active_end"]),
                tau=float(row["hspice_main_slope_tau_10_90_ns"]),
            )
        )
    lines.extend(
        [
            "",
            "## Fit Summary",
            "",
            "| Predictor | Flow | Intercept | Slope | RMS ps | Limit at GDN_ON ns | Origin-forced RMS ps | Verdict |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in summaries:
        lines.append(
            "| {pred} | {flow} | {intercept} | {slope} | {rms} | {limit} | {origin} | {verdict} |".format(
                pred=row["predictor"],
                flow=row.get("flow", ""),
                intercept=f"{float(row['intercept']):.4f}" if row.get("intercept") != "" and math.isfinite(float(row["intercept"])) else "",
                slope=f"{float(row['slope']):.4f}" if row.get("slope") != "" and math.isfinite(float(row["slope"])) else "",
                rms=f"{float(row['rms_ps']):.1f}" if math.isfinite(float(row["rms_ps"])) else "",
                limit=f"{float(row['physical_limit_at_gdn_on_ns']):.4f}" if row.get("physical_limit_at_gdn_on_ns") not in ("", None) and math.isfinite(float(row["physical_limit_at_gdn_on_ns"])) else "",
                origin=f"{float(row['origin_forced_rms_ps']):.1f}" if row.get("origin_forced_rms_ps") not in ("", None) and math.isfinite(float(row["origin_forced_rms_ps"])) else "",
                verdict=row["verdict"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The GDN-keyed idea is physically attractive, but the current generated `GDN` state is delayed relative to the pending NMOS-off command.",
            "- At the reverse edge, 500 ps and 1 ns both report `GDN ~= 1`, even though HSPICE later shows different Kd recovery holds. That means `GDN@reverse` has not yet stored the relevant pending turn-off information.",
            "- The next candidate should use a causal variable that is actually available and discriminative at retrigger: latched command age / pending NMOS-off phase, or a redesigned gate state that moves when the pending off command is launched.",
            "- A literal pulse-width law is still not a production model claim. It is better described as command-age keyed at the reverse edge, and it needs a held-out pulse width before promotion.",
            "",
            "Figures:",
            "",
            "- `gdn_keyed_hold_fit.png`",
            "- `gdn_at_reverse_by_variant.png`",
            "",
            "CSVs:",
            "",
            "- `gdn_hold_samples.csv`",
            "- `gdn_hold_fit_summary.csv`",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ensure_dir(OUT_DIR)
    rows = build_rows()
    summaries = fit_summary(rows)
    write_csv(OUT_DIR / "gdn_hold_samples.csv", rows)
    write_csv(OUT_DIR / "gdn_hold_fit_summary.csv", summaries)
    plot_rows(rows, summaries)
    write_readme(rows, summaries)
    pulse_fit = next(row for row in summaries if row["predictor"] == "pulse_width_reference")
    primary_fit = next(row for row in summaries if row.get("flow") == PRIMARY_GDN_FLOW)
    print(f"Pulse-width RMS = {float(pulse_fit['rms_ps']):.1f} ps")
    print(f"Primary GDN RMS = {float(primary_fit['rms_ps']):.1f} ps")
    print(f"Primary GDN verdict = {primary_fit['verdict']}")
    print(f"OUT_DIR={OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
