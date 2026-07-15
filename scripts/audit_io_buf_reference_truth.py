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
CASES_DIR = RESULT_ROOT / "cases"
OUT_DIR = RESULT_ROOT / "reference_truth_audit"
FLOW_ORDER = [
    "hspice_native_ibis",
    "hspice_transistor_sp",
    "ngspice_legacy",
    "ngspice_value_match_v2",
    "ngspice_two_state_directional_residual",
    "ngspice_two_state_directional_residual_recover_mean",
    "ngspice_two_state_directional_residual_recover_fast",
]
DISPLAY = {
    "hspice_native_ibis": "HSPICE native IBIS",
    "hspice_transistor_sp": "HSPICE transistor io_buf.sp",
    "ngspice_legacy": "ngspice legacy pybis",
    "ngspice_value_match_v2": "ngspice value-match v2",
    "ngspice_two_state_directional_residual": "ngspice directional residual",
    "ngspice_two_state_directional_residual_recover_mean": "ngspice mean recover",
    "ngspice_two_state_directional_residual_recover_fast": "ngspice fast recover",
}
COLORS = {
    "hspice_native_ibis": "#1f77b4",
    "hspice_transistor_sp": "#6f2dbd",
    "ngspice_legacy": "#ff7f0e",
    "ngspice_value_match_v2": "#8c564b",
    "ngspice_two_state_directional_residual": "#d62728",
    "ngspice_two_state_directional_residual_recover_mean": "#2ca02c",
    "ngspice_two_state_directional_residual_recover_fast": "#9467bd",
}


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


def get_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    lower = {key.lower(): key for key in data}
    for name in names:
        key = lower.get(name.lower())
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(names)


def load_flow(case_id: str, flow: str) -> dict[str, np.ndarray] | None:
    flow_dir = CASES_DIR / case_id / flow
    if flow == "hspice_native_ibis":
        path = flow_dir / f"{case_id}_hspice_native_ibis.tr0"
        return parse_hspice_tr0(path) if path.exists() else None
    if flow == "hspice_transistor_sp":
        path = flow_dir / f"{case_id}_hspice_transistor_sp.tr0"
        return parse_hspice_tr0(path) if path.exists() else None
    path = flow_dir / f"{case_id}_{flow}.raw"
    return parse_ngspice_raw(path) if path.exists() else None


def pad_signal(data: dict[str, np.ndarray], flow: str) -> np.ndarray:
    if flow == "hspice_native_ibis":
        return get_signal(data, "v(pad_ibis)")
    if flow == "hspice_transistor_sp":
        return get_signal(data, "v(pad_sp)")
    return get_signal(data, "v(pad)")


def coeff_signal(data: dict[str, np.ndarray], coeff: str) -> np.ndarray | None:
    names = [f"v({coeff})", f"v(xdrv.{coeff})", f"v(xdrv:{coeff})"]
    try:
        return get_signal(data, *names)
    except KeyError:
        return None


def interp_to(t_src: np.ndarray, y_src: np.ndarray, t_ref: np.ndarray) -> np.ndarray:
    return np.interp(t_ref, t_src, y_src)


def active_mask(case: base.StudyCase, t: np.ndarray) -> np.ndarray:
    mask = np.zeros_like(t, dtype=bool)
    for start, end in base.transition_windows(case):
        mask |= (t >= start) & (t <= end)
    return mask


def metric_against(case: base.StudyCase, ref_data: dict[str, np.ndarray], ref_flow: str, dut_data: dict[str, np.ndarray], dut_flow: str) -> dict[str, float]:
    tr = t_ns(ref_data)
    yr = pad_signal(ref_data, ref_flow)
    td = t_ns(dut_data)
    yd = pad_signal(dut_data, dut_flow)
    mask = active_mask(case, tr) & np.isfinite(yr)
    if int(np.sum(mask)) < 2:
        mask = np.isfinite(yr)
    yi = interp_to(td, yd, tr)
    err = yi[mask] - yr[mask]
    return {
        "rmse_v": float(np.sqrt(np.mean(err * err))),
        "max_abs_v": float(np.max(np.abs(err))),
        "mean_err_v": float(np.mean(err)),
        "n": int(np.sum(mask)),
    }


def waveform_extrema(case: base.StudyCase, data: dict[str, np.ndarray], flow: str) -> dict[str, float]:
    t = t_ns(data)
    y = pad_signal(data, flow)
    rise_ns, reverse_ns = base.command_times(case)
    end_ns = max(end for _, end in base.transition_windows(case))
    mask = (t >= max(0.0, rise_ns - 0.5)) & (t <= end_ns) & np.isfinite(y)
    if int(np.sum(mask)) < 2:
        mask = np.isfinite(y)
    tt = t[mask]
    yy = y[mask]
    imax = int(np.nanargmax(yy))
    imin = int(np.nanargmin(yy))
    return {
        "pad_peak_v": float(yy[imax]),
        "pad_peak_time_ns": float(tt[imax]),
        "pad_peak_from_reverse_ns": float(tt[imax] - reverse_ns),
        "pad_min_v": float(yy[imin]),
        "pad_min_time_ns": float(tt[imin]),
        "pad_span_v": float(np.nanmax(yy) - np.nanmin(yy)),
    }


def build_pad_rescore_rows(cases: list[base.StudyCase]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    ranking: list[dict[str, object]] = []
    for case in cases:
        loaded = {flow: load_flow(case.case_id, flow) for flow in FLOW_ORDER}
        native = loaded.get("hspice_native_ibis")
        transistor = loaded.get("hspice_transistor_sp")
        if native is None or transistor is None:
            continue
        native_vs_trans = metric_against(case, native, "hspice_native_ibis", transistor, "hspice_transistor_sp")
        for flow in FLOW_ORDER:
            data = loaded.get(flow)
            if data is None:
                continue
            vs_native = metric_against(case, native, "hspice_native_ibis", data, flow)
            vs_trans = metric_against(case, transistor, "hspice_transistor_sp", data, flow)
            ext = waveform_extrema(case, data, flow)
            rows.append(
                {
                    "case_id": case.case_id,
                    "flow": flow,
                    "vs_native_rmse_mV": vs_native["rmse_v"] * 1e3,
                    "vs_native_max_mV": vs_native["max_abs_v"] * 1e3,
                    "vs_transistor_rmse_mV": vs_trans["rmse_v"] * 1e3,
                    "vs_transistor_max_mV": vs_trans["max_abs_v"] * 1e3,
                    "native_vs_transistor_rmse_mV": native_vs_trans["rmse_v"] * 1e3,
                    **ext,
                }
            )
        for reference, key in [("native_ibis", "vs_native_rmse_mV"), ("transistor_sp", "vs_transistor_rmse_mV")]:
            candidates = [row for row in rows if row["case_id"] == case.case_id and str(row["flow"]).startswith("ngspice")]
            candidates.sort(key=lambda row: float(row[key]))
            if candidates:
                ranking.append(
                    {
                        "case_id": case.case_id,
                        "reference": reference,
                        "best_ngspice_flow": candidates[0]["flow"],
                        "best_ngspice_rmse_mV": candidates[0][key],
                        "native_vs_transistor_rmse_mV": native_vs_trans["rmse_v"] * 1e3,
                    }
                )
    return rows, ranking


def build_short_high_timing_rows(cases: list[base.StudyCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in cases:
        if case.pattern != "short_high":
            continue
        for flow in FLOW_ORDER:
            data = load_flow(case.case_id, flow)
            if data is None:
                continue
            ext = waveform_extrema(case, data, flow)
            row: dict[str, object] = {
                "case_id": case.case_id,
                "flow": flow,
                "pulse_width_ns": case.pulse_width_ns,
                **ext,
            }
            ku = coeff_signal(data, "ku")
            kd = coeff_signal(data, "kd")
            if ku is not None:
                row["ku_peak"] = float(np.nanmax(ku))
                row["ku_min"] = float(np.nanmin(ku))
            if kd is not None:
                row["kd_peak"] = float(np.nanmax(kd))
                row["kd_min"] = float(np.nanmin(kd))
            rows.append(row)
    return rows


def build_double_toggle_rows() -> list[dict[str, object]]:
    case = next(case for case in base.build_cases(include_low=True) if case.case_id == "double_toggle_1ps")
    rows: list[dict[str, object]] = []
    for flow in FLOW_ORDER:
        data = load_flow(case.case_id, flow)
        if data is None:
            continue
        ext = waveform_extrema(case, data, flow)
        row: dict[str, object] = {"case_id": case.case_id, "flow": flow, **ext}
        ku = coeff_signal(data, "ku")
        kd = coeff_signal(data, "kd")
        if ku is not None:
            t = t_ns(data)
            imax = int(np.nanargmax(ku))
            row["ku_peak"] = float(ku[imax])
            row["ku_peak_time_ns"] = float(t[imax])
        if kd is not None:
            t = t_ns(data)
            imin = int(np.nanargmin(kd))
            row["kd_min"] = float(kd[imin])
            row["kd_min_time_ns"] = float(t[imin])
        rows.append(row)
    return rows


def plot_reference_overlays(cases: list[base.StudyCase]) -> None:
    plot_cases = [
        "edge_1ps_base_50r_2pf",
        "short_pulse_500ps_high",
        "short_pulse_1ns_high",
        "short_pulse_2ns_high",
        "short_pulse_2ns_low",
        "double_toggle_1ps",
    ]
    case_map = {case.case_id: case for case in cases}
    out = OUT_DIR / "plots"
    ensure_dir(out)
    for case_id in plot_cases:
        case = case_map.get(case_id)
        if case is None:
            continue
        fig, axes = plt.subplots(2, 1, figsize=(10.5, 6.2), sharex=True, constrained_layout=True)
        t_min = 4.5
        t_max = min(case.stop_ns, max(end for _, end in base.transition_windows(case)) + 0.3)
        plotted = False
        for flow in FLOW_ORDER:
            data = load_flow(case.case_id, flow)
            if data is None:
                continue
            t = t_ns(data)
            y = pad_signal(data, flow)
            mask = (t >= t_min) & (t <= t_max)
            axes[0].plot(t[mask], y[mask], lw=1.9, color=COLORS.get(flow), label=DISPLAY.get(flow, flow))
            plotted = True
        if not plotted:
            plt.close(fig)
            continue
        t_axis = np.linspace(t_min, t_max, 2000)
        axes[1].plot(t_axis, base.input_waveform(case, t_axis), color="#222222", lw=1.5, label="input")
        axes[0].set_title(f"{case_id}: pad reference overlay", loc="left", fontweight="bold")
        axes[0].set_ylabel("Pad voltage (V)")
        axes[0].grid(True, color="#d8dde6")
        axes[0].legend(loc="best", frameon=False, fontsize=8)
        axes[1].set_ylabel("Input (V)")
        axes[1].set_xlabel("Time (ns)")
        axes[1].grid(True, color="#d8dde6")
        axes[1].legend(loc="best", frameon=False)
        fig.savefig(out / f"{case_id}_pad_reference_overlay.png", dpi=180)
        plt.close(fig)


def plot_double_toggle_commitment() -> None:
    case = next(case for case in base.build_cases(include_low=True) if case.case_id == "double_toggle_1ps")
    out = OUT_DIR / "plots"
    ensure_dir(out)
    fig, axes = plt.subplots(3, 1, figsize=(10.8, 8.0), sharex=True, constrained_layout=True)
    t_min, t_max = 4.9, 10.5
    t_axis = np.linspace(t_min, t_max, 3000)
    axes[0].plot(t_axis, base.input_waveform(case, t_axis), color="#222222", lw=1.5, label="input")
    for flow in ["hspice_native_ibis", "hspice_transistor_sp", "ngspice_legacy", "ngspice_two_state_directional_residual"]:
        data = load_flow(case.case_id, flow)
        if data is None:
            continue
        t = t_ns(data)
        y = pad_signal(data, flow)
        mask = (t >= t_min) & (t <= t_max)
        axes[1].plot(t[mask], y[mask], color=COLORS.get(flow), lw=1.9, label=DISPLAY.get(flow, flow))
    native = load_flow(case.case_id, "hspice_native_ibis")
    if native is not None:
        t = t_ns(native)
        mask = (t >= t_min) & (t <= t_max)
        axes[2].plot(t[mask], get_signal(native, "v(ku)")[mask], color="#1f77b4", lw=1.9, label="HSPICE native Ku")
        axes[2].plot(t[mask], get_signal(native, "v(kd)")[mask], color="#d62728", lw=1.9, label="HSPICE native Kd")
    axes[0].set_title("double_toggle_1ps: full-table commitment audit", loc="left", fontweight="bold")
    axes[0].set_ylabel("Input (V)")
    axes[1].set_ylabel("Pad voltage (V)")
    axes[2].set_ylabel("Native IBIS coeff")
    axes[2].set_xlabel("Time (ns)")
    for ax in axes:
        ax.grid(True, color="#d8dde6")
        ax.legend(loc="best", frameon=False, fontsize=8)
    fig.savefig(out / "double_toggle_full_table_commitment.png", dpi=180)
    plt.close(fig)


def write_readme(
    pad_rows: list[dict[str, object]],
    ranking_rows: list[dict[str, object]],
    short_high_rows: list[dict[str, object]],
    double_rows: list[dict[str, object]],
) -> None:
    def lookup(case_id: str, flow: str, key: str) -> float:
        for row in pad_rows:
            if row["case_id"] == case_id and row["flow"] == flow:
                return float(row[key])
        return float("nan")

    def short_lookup(case_id: str, flow: str, key: str) -> float:
        for row in short_high_rows:
            if row["case_id"] == case_id and row["flow"] == flow:
                return float(row[key])
        return float("nan")

    best_trans = {row["case_id"]: row for row in ranking_rows if row["reference"] == "transistor_sp"}
    double_native = next((row for row in double_rows if row["flow"] == "hspice_native_ibis"), {})
    native_500 = short_lookup("short_pulse_500ps_high", "hspice_native_ibis", "ku_peak")
    native_1ns = short_lookup("short_pulse_1ns_high", "hspice_native_ibis", "ku_peak")
    native_2ns = short_lookup("short_pulse_2ns_high", "hspice_native_ibis", "ku_peak")
    lines = [
        "# io_buf Reference Truth Audit",
        "",
        "This audit checks whether conclusions change when pad-level scoring uses HSPICE transistor `io_buf.sp` instead of HSPICE native IBIS. It uses existing cached waveforms only; no new simulations are run.",
        "",
        "## Headline Finding",
        "",
        f"- HSPICE native IBIS and HSPICE transistor disagree strongly on the long-pulse pad: `{lookup('edge_1ps_base_50r_2pf', 'hspice_transistor_sp', 'vs_native_rmse_mV'):.1f} mV` RMSE.",
        f"- On `short_pulse_1ns_high`, native-vs-transistor pad disagreement is `{lookup('short_pulse_1ns_high', 'hspice_transistor_sp', 'vs_native_rmse_mV'):.1f} mV`, while directional-residual vs native is `{lookup('short_pulse_1ns_high', 'ngspice_two_state_directional_residual', 'vs_native_rmse_mV'):.1f} mV` and vs transistor is `{lookup('short_pulse_1ns_high', 'ngspice_two_state_directional_residual', 'vs_transistor_rmse_mV'):.1f} mV`.",
        f"- On short-high cases, the best transistor-pad ngspice flow is often not the best native-IBIS flow, so pad-level conclusions are reference-dependent.",
        f"- Pure short-high native-IBIS Ku is partial, not full-table replay: Ku peaks are `{native_500:.4f}`, `{native_1ns:.4f}`, `{native_2ns:.4f}` for 0.5/1/2 ns high pulses.",
        f"- The existing `double_toggle_1ps` case is not a pure 1 ps glitch because it ends with a sustained final high. Native Ku peak `{float(double_native.get('ku_peak', float('nan'))):.4f}` is therefore not enough to prove full-table commitment from the first glitch.",
        "- Coefficient RMSE still has value for matching HSPICE native IBIS, but it should no longer be treated as transistor-level truth without qualification.",
        "",
        "## Best ngspice Pad Match by Reference",
        "",
        "| Case | Reference | Best ngspice flow | RMSE mV | Native-vs-transistor RMSE mV |",
        "|---|---|---|---:|---:|",
    ]
    for row in ranking_rows:
        lines.append(
            "| {case} | {ref} | {flow} | {rmse:.3f} | {nvt:.3f} |".format(
                case=row["case_id"],
                ref=row["reference"],
                flow=row["best_ngspice_flow"],
                rmse=float(row["best_ngspice_rmse_mV"]),
                nvt=float(row["native_vs_transistor_rmse_mV"]),
            )
        )
    lines.extend(
        [
            "",
            "## Short-High Pad Timing",
            "",
            "| Case | Flow | Pad peak V | Peak time ns | Peak from reverse ns | Ku peak | Kd min |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in short_high_rows:
        if row["flow"] not in ["hspice_native_ibis", "hspice_transistor_sp", "ngspice_two_state_directional_residual", "ngspice_two_state_directional_residual_recover_mean"]:
            continue
        lines.append(
            "| {case} | {flow} | {peak:.4f} | {ptime:.4f} | {prel:.4f} | {ku} | {kd} |".format(
                case=row["case_id"],
                flow=row["flow"],
                peak=float(row["pad_peak_v"]),
                ptime=float(row["pad_peak_time_ns"]),
                prel=float(row["pad_peak_from_reverse_ns"]),
                ku=f"{float(row['ku_peak']):.4f}" if "ku_peak" in row else "",
                kd=f"{float(row['kd_min']):.4f}" if "kd_min" in row else "",
            )
        )
    lines.extend(
        [
            "",
            "## Double-Toggle Commitment Check",
            "",
            "| Flow | Pad peak V | Pad peak time ns | Ku peak | Ku peak time ns | Kd min |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in double_rows:
        lines.append(
            "| {flow} | {pad:.4f} | {ptime:.4f} | {ku} | {kut} | {kd} |".format(
                flow=row["flow"],
                pad=float(row["pad_peak_v"]),
                ptime=float(row["pad_peak_time_ns"]),
                ku=f"{float(row['ku_peak']):.4f}" if "ku_peak" in row else "",
                kut=f"{float(row['ku_peak_time_ns']):.4f}" if "ku_peak_time_ns" in row else "",
                kd=f"{float(row['kd_min']):.4f}" if "kd_min" in row else "",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The previous no-false-pass discipline was still correct, but the reference hierarchy needs to be explicit: native IBIS is the coefficient reference, while transistor `io_buf.sp` is the pad-level physics reference.",
            "- The short-high pad errors are already comparable to, or smaller than, native-vs-transistor disagreement in some cases. Past that point, coefficient matching may be matching HSPICE IBIS playback internals rather than silicon behavior.",
            "- The double-toggle result does not prove full-table commitment by itself because the final input state is sustained high. A separate pure-glitch test would be needed to test scheduler commitment directly.",
            "- The short-high native-IBIS coefficient peaks are partial, so HSPICE native IBIS is not simply replaying a full Ku table for every short pulse. The remaining reference concern is narrower: the Kd recovery/hold behavior may still be native-IBIS playback policy rather than transistor-level behavior.",
            "",
            "Files:",
            "",
            "- `pad_rescore_vs_references.csv`",
            "- `pad_ranking_by_reference.csv`",
            "- `short_high_pad_timing.csv`",
            "- `double_toggle_commitment.csv`",
            "- `plots/*_pad_reference_overlay.png`",
            "- `plots/double_toggle_full_table_commitment.png`",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ensure_dir(OUT_DIR)
    cases = base.build_cases(include_low=True)
    pad_rows, ranking_rows = build_pad_rescore_rows(cases)
    short_high_rows = build_short_high_timing_rows(cases)
    double_rows = build_double_toggle_rows()
    write_csv(OUT_DIR / "pad_rescore_vs_references.csv", pad_rows)
    write_csv(OUT_DIR / "pad_ranking_by_reference.csv", ranking_rows)
    write_csv(OUT_DIR / "short_high_pad_timing.csv", short_high_rows)
    write_csv(OUT_DIR / "double_toggle_commitment.csv", double_rows)
    plot_reference_overlays(cases)
    plot_double_toggle_commitment()
    write_readme(pad_rows, ranking_rows, short_high_rows, double_rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
