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
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
if str(PYBIS_ROOT) not in sys.path:
    sys.path.insert(0, str(PYBIS_ROOT))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
import run_io_buf_two_state_gate_model as gate_study  # noqa: E402
import run_io_buf_value_matched_replay_v2 as base  # noqa: E402


RESULT_ROOT = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
CASES_DIR = RESULT_ROOT / "cases"
OUT_DIR = RESULT_ROOT / "presentation_evidence_figures"
DEFAULT_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"


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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


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


def load_flow(case_id: str, flow: str) -> dict[str, np.ndarray]:
    flow_dir = CASES_DIR / case_id / flow
    if flow == "hspice_native_ibis":
        return parse_hspice_tr0(flow_dir / f"{case_id}_hspice_native_ibis.tr0")
    if flow == "hspice_transistor_sp":
        return parse_hspice_tr0(flow_dir / f"{case_id}_hspice_transistor_sp.tr0")
    return parse_ngspice_raw(flow_dir / f"{case_id}_{flow}.raw")


def pad_signal(data: dict[str, np.ndarray], flow: str) -> np.ndarray:
    if flow == "hspice_native_ibis":
        return get_signal(data, "v(pad_ibis)")
    if flow == "hspice_transistor_sp":
        return get_signal(data, "v(pad_sp)")
    return get_signal(data, "v(pad)")


def coeff_signal(data: dict[str, np.ndarray], coeff: str) -> np.ndarray:
    return get_signal(data, f"v({coeff})", f"v(xdrv.{coeff})", f"v(xdrv:{coeff})")


def interp_to(t_src: np.ndarray, y_src: np.ndarray, t_ref: np.ndarray) -> np.ndarray:
    mask = np.isfinite(t_src) & np.isfinite(y_src)
    if int(np.sum(mask)) < 2:
        return np.full_like(t_ref, np.nan, dtype=float)
    tt = np.asarray(t_src[mask], dtype=float)
    yy = np.asarray(y_src[mask], dtype=float)
    order = np.argsort(tt)
    return np.interp(t_ref, tt[order], yy[order], left=np.nan, right=np.nan)


def rmse_on_window(t_ref: np.ndarray, y_ref: np.ndarray, t_dut: np.ndarray, y_dut: np.ndarray, x0: float, x1: float) -> float:
    mask = (t_ref >= x0) & (t_ref <= x1) & np.isfinite(y_ref)
    yi = interp_to(t_dut, y_dut, t_ref)
    mask &= np.isfinite(yi)
    if int(np.sum(mask)) < 2:
        return float("nan")
    err = yi[mask] - y_ref[mask]
    return float(np.sqrt(np.mean(err * err)))


def relevant_edges(case: base.StudyCase) -> list[tuple[float, str]]:
    e = 0.5 * case.edge_ns
    if case.pattern == "short_high":
        return [(5.0 + e, "rise"), (5.0 + case.pulse_width_ns + e, "reverse")]
    if case.pattern == "short_low":
        return [(10.0 + e, "fall"), (10.0 + case.pulse_width_ns + e, "reverse")]
    if case.pattern == "rise_fall":
        return [(5.0 + e, "rise"), (15.0 + e, "fall")]
    raise ValueError(case.pattern)


def crossing_time(t: np.ndarray, y: np.ndarray, level: float, start_ns: float, direction: str) -> float:
    mask = (t >= start_ns) & np.isfinite(y)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(y[mask], dtype=float)
    if len(tt) < 2:
        return float("nan")
    d = yy - level
    if direction == "rise":
        idx = np.where((d[:-1] <= 0.0) & (d[1:] > 0.0))[0]
    else:
        idx = np.where((d[:-1] >= 0.0) & (d[1:] < 0.0))[0]
    if len(idx) == 0:
        return float("nan")
    i = int(idx[0])
    if yy[i + 1] == yy[i]:
        return float(tt[i])
    return float(tt[i] + (level - yy[i]) * (tt[i + 1] - tt[i]) / (yy[i + 1] - yy[i]))


def tail_median(t: np.ndarray, y: np.ndarray, start_ns: float, end_ns: float) -> float:
    mask = (t >= start_ns) & (t <= end_ns) & np.isfinite(y)
    vals = y[mask]
    return float(np.median(vals)) if len(vals) else float("nan")


def native_kd_hold_region(case: base.StudyCase, native: dict[str, np.ndarray]) -> tuple[float, float] | None:
    if case.pattern != "short_high":
        return None
    reverse_ns = relevant_edges(case)[1][0]
    active_end_ns = max(end for _, end in base.transition_windows(case))
    t = t_ns(native)
    kd = coeff_signal(native, "kd")
    mask = (t >= reverse_ns) & (t <= active_end_ns) & np.isfinite(kd)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(kd[mask], dtype=float)
    if len(tt) < 8:
        return None
    i_min = int(np.nanargmin(yy))
    kd_min = float(yy[i_min])
    kd_min_time = float(tt[i_min])
    kd_final = tail_median(tt, yy, max(kd_min_time, active_end_ns - 0.5), active_end_ns)
    span = kd_final - kd_min
    if span <= 1e-4:
        return None
    kd50 = crossing_time(tt, yy, kd_min + 0.5 * span, kd_min_time, "rise")
    if not math.isfinite(kd50):
        return None
    return reverse_ns, kd50


def active_zoom(case: base.StudyCase, native: dict[str, np.ndarray] | None = None) -> tuple[float, float]:
    edges = relevant_edges(case)
    x0 = max(0.0, edges[0][0] - 1.0)
    end_candidates = [end for _, end in base.transition_windows(case)]
    if native is not None:
        hold = native_kd_hold_region(case, native)
        if hold is not None:
            end_candidates.append(hold[1])
    return x0, min(case.stop_ns, max(end_candidates) + 2.0)


def mark_edges(ax: plt.Axes, case: base.StudyCase) -> None:
    for x, _ in relevant_edges(case):
        ax.axvline(x, color="#444444", lw=1.1, ls="--", alpha=0.8)


def reconstruction_gate_figure() -> None:
    kr, kf, fit = gate_study.load_io_buf_k_tables(DEFAULT_IBIS)
    _, data = gate_study.reconstruction_rows_and_data(kr, kf, fit)
    fit_row = read_csv(RESULT_ROOT / "gate_fit_summary.csv")[0]
    metrics = {(row["candidate"], row["table"]): row for row in read_csv(RESULT_ROOT / "normal_k_reconstruction.csv")}

    cols = [
        ("pwl", "single map", "pwl_reconstruction_rmse_max", "pwl_reconstruction_max_error_max", "pwl_table_gate"),
        ("directional", "+ directional maps", "directional_reconstruction_rmse_max", "directional_reconstruction_max_error_max", "directional_table_gate"),
        ("directional_residual", "+ rate residual", "directional_residual_reconstruction_rmse_max", "directional_residual_reconstruction_max_error_max", "directional_residual_table_gate"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13.6, 7.6), sharex="row", sharey="row")
    rows_out: list[dict[str, object]] = []
    for col_idx, (candidate, title, rmse_key, max_key, gate_key) in enumerate(cols):
        gate = fit_row[gate_key]
        gate_color = "#138a36" if gate == "PASS" else "#b00020"
        worst_rmse = float(fit_row[rmse_key])
        worst_max = float(fit_row[max_key])

        for row_idx, coeff in enumerate(["ku", "kd"]):
            ax = axes[row_idx, col_idx]
            tr = data["tr"]
            tf = data["tf"]
            ax.plot(tr, data[f"{coeff}_rise_orig"], color="#000000", lw=2.7, label="IBIS table")
            ax.plot(tf, data[f"{coeff}_fall_orig"], color="#000000", lw=2.7, ls="--")
            ax.plot(tr, data[f"{coeff}_rise_{candidate}"], color="#d62728", lw=2.0, label="model")
            ax.plot(tf, data[f"{coeff}_fall_{candidate}"], color="#d62728", lw=2.0, ls="--")
            ax.grid(True, alpha=0.25)
            ax.set_xlim(0.0, max(float(np.nanmax(tr)), float(np.nanmax(tf))))
            if row_idx == 0:
                ax.set_title(title, fontsize=13, fontweight="bold")
                ax.text(
                    0.03,
                    0.94,
                    f"worst max error = {worst_max:.6f}\n{gate}",
                    transform=ax.transAxes,
                    va="top",
                    ha="left",
                    fontsize=10,
                    color=gate_color,
                    bbox=dict(facecolor="white", edgecolor=gate_color, alpha=0.88, boxstyle="round,pad=0.28"),
                )
            if col_idx == 0:
                ax.set_ylabel("Ku" if coeff == "ku" else "Kd")
            if row_idx == 1:
                ax.set_xlabel("IBIS table time (ns)")
            if coeff == "kd":
                ax.axhline(0.0, color="#666666", lw=1.0, alpha=0.8)
                y_orig = data["kd_fall_orig"]
                neg = y_orig < -0.005
                if np.any(neg):
                    x_start = float(np.min(tf[neg]))
                    x_stop = float(np.max(tf[neg]))
                    ax.axvspan(x_start, x_stop, color="#f2c14e", alpha=0.18, lw=0)
                    ax.annotate(
                        "Kd undershoot",
                        xy=(x_start, -0.055),
                        xytext=(x_start + 0.75, -0.16),
                        arrowprops=dict(arrowstyle="->", color="#8a6d1d", lw=1.2),
                        fontsize=9,
                        color="#8a6d1d",
                    )
            for table in [f"{coeff}_rise", f"{coeff}_fall"]:
                m = metrics[(candidate, table)]
                rows_out.append(
                    {
                        "figure_panel": f"{coeff}_{candidate}",
                        "candidate": candidate,
                        "column_title": title,
                        "table": table,
                        "rmse": m["rmse"],
                        "max_error": m["max_error"],
                        "worst_candidate_rmse": worst_rmse,
                        "worst_candidate_max_error": worst_max,
                        "gate": gate,
                    }
                )

    # Add a compact style key without turning the image into an RMSE table.
    axes[0, 0].plot([], [], color="#000000", lw=2.7, label="IBIS table")
    axes[0, 0].plot([], [], color="#d62728", lw=2.0, label="model")
    axes[0, 0].plot([], [], color="#555555", lw=2.0, ls="-", label="rising/on")
    axes[0, 0].plot([], [], color="#555555", lw=2.0, ls="--", label="falling/off")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    unique: dict[str, object] = {}
    for h, label in zip(handles, labels):
        unique.setdefault(label, h)
    fig.suptitle("Offline Ku/Kd reconstruction gate: model structure progression", fontsize=16, y=0.985)
    fig.legend(list(unique.values()), list(unique.keys()), loc="upper center", ncol=4, fontsize=10, frameon=True, bbox_to_anchor=(0.5, 0.94))
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(OUT_DIR / "reconstruction_gate_evidence.png", dpi=170)
    plt.close(fig)
    write_csv(OUT_DIR / "reconstruction_gate_panel_errors.csv", rows_out)


def quadrant_figure() -> None:
    case_map = {case.case_id: case for case in base.build_cases(include_low=True)}
    low = case_map["short_pulse_1ns_low"]
    high = case_map["short_pulse_1ns_high"]

    data = {
        low.case_id: {
            "case": low,
            "native": load_flow(low.case_id, "hspice_native_ibis"),
            "transistor": load_flow(low.case_id, "hspice_transistor_sp"),
            "model": load_flow(low.case_id, "ngspice_two_state_directional_residual"),
            "title": "short-low \u2713",
        },
        high.case_id: {
            "case": high,
            "native": load_flow(high.case_id, "hspice_native_ibis"),
            "transistor": load_flow(high.case_id, "hspice_transistor_sp"),
            "model": load_flow(high.case_id, "ngspice_two_state_directional_residual"),
            "title": "short-high \u2717",
        },
    }

    fig, axes = plt.subplots(3, 2, figsize=(13.8, 10.0), sharex="col")
    case_order = [low.case_id, high.case_id]
    metrics_by_case: dict[str, dict[str, float]] = {}
    rows = []
    for case_id in case_order:
        item = data[case_id]
        case = item["case"]
        native = item["native"]
        model = item["model"]
        x0, x1 = active_zoom(case, native)
        t_native = t_ns(native)
        t_model = t_ns(model)
        pad_rmse = rmse_on_window(
            t_native,
            pad_signal(native, "hspice_native_ibis"),
            t_model,
            pad_signal(model, "ngspice_two_state_directional_residual"),
            x0,
            x1,
        )
        kd_rmse = rmse_on_window(
            t_native,
            coeff_signal(native, "kd"),
            t_model,
            coeff_signal(model, "kd"),
            x0,
            x1,
        )
        ku_rmse = rmse_on_window(
            t_native,
            coeff_signal(native, "ku"),
            t_model,
            coeff_signal(model, "ku"),
            x0,
            x1,
        )
        metrics_by_case[case_id] = {"pad_rmse_v": pad_rmse, "ku_rmse": ku_rmse, "kd_rmse": kd_rmse}
        rows.extend(
            [
                {
                    "figure_panel": f"{case_id}_pad",
                    "case_id": case_id,
                    "variable": "pad_v",
                    "reference_flow": "hspice_native_ibis",
                    "dut_flow": "ngspice_two_state_directional_residual",
                    "rmse": pad_rmse,
                    "display_value": pad_rmse * 1e3,
                    "display_units": "mV",
                    "window_start_ns": x0,
                    "window_stop_ns": x1,
                },
                {
                    "figure_panel": f"{case_id}_ku",
                    "case_id": case_id,
                    "variable": "ku",
                    "reference_flow": "hspice_native_ibis",
                    "dut_flow": "ngspice_two_state_directional_residual",
                    "rmse": ku_rmse,
                    "display_value": ku_rmse,
                    "display_units": "unitless",
                    "window_start_ns": x0,
                    "window_stop_ns": x1,
                },
                {
                    "figure_panel": f"{case_id}_kd",
                    "case_id": case_id,
                    "variable": "kd",
                    "reference_flow": "hspice_native_ibis",
                    "dut_flow": "ngspice_two_state_directional_residual",
                    "rmse": kd_rmse,
                    "display_value": kd_rmse,
                    "display_units": "unitless",
                    "window_start_ns": x0,
                    "window_stop_ns": x1,
                },
            ]
        )

    for col_idx, case_id in enumerate(case_order):
        item = data[case_id]
        case = item["case"]
        native = item["native"]
        transistor = item["transistor"]
        model = item["model"]
        x0, x1 = active_zoom(case, native)
        hold = native_kd_hold_region(case, native)

        pad_ax = axes[0, col_idx]
        ku_ax = axes[1, col_idx]
        kd_ax = axes[2, col_idx]
        for ax in [pad_ax, ku_ax, kd_ax]:
            ax.set_xlim(x0, x1)
            ax.grid(True, alpha=0.25)
            mark_edges(ax, case)

        pad_ax.plot(t_ns(native), pad_signal(native, "hspice_native_ibis"), color="#000000", lw=3.0, label="HSPICE native IBIS")
        pad_ax.plot(t_ns(transistor), pad_signal(transistor, "hspice_transistor_sp"), color="#8a8a8a", lw=3.0, label="HSPICE transistor io_buf.sp")
        pad_ax.plot(t_ns(model), pad_signal(model, "ngspice_two_state_directional_residual"), color="#d62728", lw=2.2, label="directional+residual")
        pad_ax.set_title(item["title"], fontsize=14, fontweight="bold")
        pad_ax.set_ylabel("Pad voltage (V)")

        ku_ax.plot(t_ns(native), coeff_signal(native, "ku"), color="#000000", lw=3.0, label="native IBIS Ku")
        ku_ax.plot(t_ns(model), coeff_signal(model, "ku"), color="#d62728", lw=2.2, label="directional+residual Ku")
        ku_ax.axhline(0.0, color="#555555", lw=1.0, alpha=0.8)
        ku_ax.set_ylabel("Ku")

        if hold is not None:
            kd_ax.axvspan(hold[0], hold[1], color="#f2c14e", alpha=0.22, lw=0)
        kd_ax.plot(t_ns(native), coeff_signal(native, "kd"), color="#000000", lw=3.0, label="native IBIS Kd")
        kd_ax.plot(t_ns(model), coeff_signal(model, "kd"), color="#d62728", lw=2.2, label="directional+residual Kd")
        kd_ax.axhline(0.0, color="#555555", lw=1.0, alpha=0.8)
        kd_ax.set_ylabel("Kd")
        kd_ax.set_xlabel("Time (ns)")
        if hold is not None:
            kd_ax.text(hold[0] + 0.08, 0.16, "native-IBIS Kd hold", fontsize=10, color="#8a6d1d", ha="left", va="bottom")

    handles, labels = [], []
    for axis in axes.ravel():
        h, l = axis.get_legend_handles_labels()
        handles.extend(h)
        labels.extend(l)
    unique: dict[str, object] = {}
    for h, label in zip(handles, labels):
        unique.setdefault(label, h)
    fig.suptitle("Pad and coefficient checks are separate: short-low passes, short-high Kd remains open", fontsize=16, y=0.988)
    fig.legend(list(unique.values()), list(unique.keys()), loc="upper center", ncol=4, fontsize=10, frameon=True, bbox_to_anchor=(0.5, 0.945))
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(OUT_DIR / "three_quadrants_one_open.png", dpi=170)
    plt.close(fig)

    write_csv(OUT_DIR / "three_quadrants_metrics.csv", rows)


def main() -> None:
    ensure_dir(OUT_DIR)
    reconstruction_gate_figure()
    quadrant_figure()
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
