from __future__ import annotations

import argparse
import csv
import hashlib
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
if str(PYBIS_ROOT) not in sys.path:
    sys.path.insert(0, str(PYBIS_ROOT))

from pybis2spice import pybis2spice, subcircuit  # noqa: E402


OUT_DIR = (
    ROOT
    / "results"
    / "io_buf_inv_chain_ibis_waveform_failure_analysis_2026-07-28"
)
PLOTS_DIR = OUT_DIR / "plots"
DATA_DIR = OUT_DIR / "waveform_data"

BLACK = "#111111"
BLUE = "#0072B2"
ORANGE = "#D55E00"
GREEN = "#009E73"
RED = "#D62728"
PURPLE = "#7A3DB8"
GRAY = "#777777"


@dataclass(frozen=True)
class ModelCase:
    case_id: str
    label: str
    device: str
    edge_label: str
    ibis: Path
    component: str
    model: str
    transistor_sp: Path


CASES = [
    ModelCase(
        "io_buf_slow_1ns",
        "io_buf slow 1 ns",
        "io_buf",
        "1 ns",
        ROOT / "sim" / "hspice" / "sparam" / "io_buf.ibs",
        "MCM Driver 1",
        "driver",
        ROOT / "buffers" / "models" / "io_buf.sp",
    ),
    ModelCase(
        "io_buf_fast_5ps",
        "io_buf fast 5 ps",
        "io_buf",
        "5 ps",
        ROOT
        / "results"
        / "io_buf_fast_edge_retest_2026-06-05"
        / "source"
        / "io_buf.ibs",
        "MCM Driver 1",
        "driver",
        ROOT / "buffers" / "models" / "io_buf.sp",
    ),
    ModelCase(
        "inv_chain_slow_1ns",
        "inv_chain slow 1 ns",
        "inv_chain",
        "1 ns",
        ROOT
        / "results"
        / "inv_chain_s2ibispy_slow_fast_2026-07-27"
        / "slow_1ns"
        / "inv_chain_slow_1ns.ibs",
        "invchain",
        "driver2",
        ROOT / "buffers" / "inv_chain" / "invchain_subckt_typ.sp",
    ),
    ModelCase(
        "inv_chain_fast_5ps",
        "inv_chain fast 5 ps",
        "inv_chain",
        "5 ps",
        ROOT
        / "results"
        / "inv_chain_s2ibispy_slow_fast_2026-07-27"
        / "fast_5ps"
        / "inv_chain_fast_5ps.ibs",
        "invchain",
        "driver2",
        ROOT / "buffers" / "inv_chain" / "invchain_subckt_typ.sp",
    ),
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        path.write_text("", encoding="ascii")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def fmt(value: object, digits: int = 6) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "n/a"
    return f"{number:.{digits}g}"


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "figure.dpi": 120,
            "savefig.dpi": 180,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "lines.linewidth": 2.0,
        }
    )


def interpolation(time_s: np.ndarray, waveform: object, corner: int) -> np.ndarray:
    source = np.asarray(waveform.data, dtype=float)
    return np.interp(time_s, source[:, 0], source[:, corner])


def transition_markers(time_s: np.ndarray, values: np.ndarray) -> dict[str, float]:
    time_ns = np.asarray(time_s, dtype=float) * 1e9
    values = np.asarray(values, dtype=float)
    v0 = float(values[0])
    v1 = float(values[-1])
    span = v1 - v0
    result: dict[str, float] = {
        "initial_v": v0,
        "final_v": v1,
        "span_v": span,
    }
    if abs(span) < 1e-12:
        result.update({"t05_ns": math.nan, "t50_ns": math.nan, "t95_ns": math.nan})
        return result
    progress = (values - v0) / span
    for name, level in [("t05_ns", 0.05), ("t50_ns", 0.50), ("t95_ns", 0.95)]:
        indices = np.flatnonzero(progress >= level)
        result[name] = float(time_ns[indices[0]]) if len(indices) else math.nan
    threshold = max(1e-3, 0.01 * abs(span))
    indices = np.flatnonzero(np.abs(values - v0) >= threshold)
    result["first_motion_ns"] = float(time_ns[indices[0]]) if len(indices) else math.nan
    first_50ps = time_ns <= 0.05 + 1e-12
    result["boundary_excursion_50ps_v"] = (
        float(np.max(np.abs(values[first_50ps] - v0))) if np.any(first_50ps) else 0.0
    )
    return result


def expected_endpoint_error(kr: np.ndarray, kf: np.ndarray) -> dict[str, float]:
    expected = {
        "kr0_ku_error": abs(float(kr[0, 1]) - 0.0),
        "kr0_kd_error": abs(float(kr[0, 2]) - 1.0),
        "krend_ku_error": abs(float(kr[-1, 1]) - 1.0),
        "krend_kd_error": abs(float(kr[-1, 2]) - 0.0),
        "kf0_ku_error": abs(float(kf[0, 1]) - 1.0),
        "kf0_kd_error": abs(float(kf[0, 2]) - 0.0),
        "kfend_ku_error": abs(float(kf[-1, 1]) - 0.0),
        "kfend_kd_error": abs(float(kf[-1, 2]) - 1.0),
    }
    expected["max_endpoint_error"] = max(expected.values())
    return expected


def analyze_direction(
    data_model: object,
    direction: str,
    corner: int,
) -> dict[str, object]:
    waveforms = data_model.vt_rising if direction == "rising" else data_model.vt_falling
    waveform1 = waveforms[0]
    waveform2 = waveforms[1]
    time_s = np.unique(
        np.sort(
            np.concatenate(
                (
                    np.asarray(waveform1.data[:, 0], dtype=float),
                    np.asarray(waveform2.data[:, 0], dtype=float),
                )
            )
        )
    )
    v1 = interpolation(time_s, waveform1, corner)
    v2 = interpolation(time_s, waveform2, corner)
    currents1 = pybis2spice.generating_current_data(data_model, time_s, corner, waveform1)
    currents2 = pybis2spice.generating_current_data(data_model, time_s, corner, waveform2)
    i_pu1, i_pd1, i_pc1, i_gc1, i_rfix1, i_ccomp1, i_cfixture1 = currents1
    i_pu2, i_pd2, i_pc2, i_gc2, i_rfix2, i_ccomp2, i_cfixture2 = currents2
    b1 = i_gc1 + i_pc1 + i_rfix1 - i_ccomp1 - i_cfixture1
    b2 = i_gc2 + i_pc2 + i_rfix2 - i_ccomp2 - i_cfixture2

    ku = np.empty_like(time_s)
    kd = np.empty_like(time_s)
    cond = np.empty_like(time_s)
    determinant = np.empty_like(time_s)
    for index in range(len(time_s)):
        matrix = np.array(
            [
                [i_pu1[index], i_pd1[index]],
                [i_pu2[index], i_pd2[index]],
            ],
            dtype=float,
        )
        rhs = np.array([b1[index], b2[index]], dtype=float)
        solved = np.linalg.solve(matrix, rhs)
        ku[index] = solved[0]
        kd[index] = solved[1]
        cond[index] = np.linalg.cond(matrix)
        determinant[index] = np.linalg.det(matrix)

    k = np.column_stack((time_s, ku, kd))
    m1 = transition_markers(time_s, v1)
    m2 = transition_markers(time_s, v2)
    ccomp_to_rfixture = max(
        float(np.max(np.abs(i_ccomp1)))
        / max(float(np.max(np.abs(i_rfix1))), 1e-30),
        float(np.max(np.abs(i_ccomp2)))
        / max(float(np.max(np.abs(i_rfix2))), 1e-30),
    )
    peak_ccomp_index1 = int(np.argmax(np.abs(i_ccomp1)))
    peak_ccomp_index2 = int(np.argmax(np.abs(i_ccomp2)))
    return {
        "direction": direction,
        "waveform1": waveform1,
        "waveform2": waveform2,
        "time_s": time_s,
        "v1": v1,
        "v2": v2,
        "k": k,
        "cond": cond,
        "determinant": determinant,
        "i_rfix1": i_rfix1,
        "i_rfix2": i_rfix2,
        "i_ccomp1": i_ccomp1,
        "i_ccomp2": i_ccomp2,
        "markers1": m1,
        "markers2": m2,
        "fixture_t50_separation_ns": abs(m1["t50_ns"] - m2["t50_ns"]),
        "peak_ccomp_to_rfixture_ratio": ccomp_to_rfixture,
        "fixture1_peak_ccomp_time_ns": float(time_s[peak_ccomp_index1] * 1e9),
        "fixture2_peak_ccomp_time_ns": float(time_s[peak_ccomp_index2] * 1e9),
    }


def analyze_case(case: ModelCase) -> dict[str, object]:
    parsed = pybis2spice.get_ibis_model_ecdtools(str(case.ibis))
    data_model = pybis2spice.DataModel(
        parsed,
        model_name=case.model,
        component_name=case.component,
    )
    corner = subcircuit.convert_corner_str_to_index("Typical") + 1
    rising = analyze_direction(data_model, "rising", corner)
    falling = analyze_direction(data_model, "falling", corner)
    kr = np.asarray(rising["k"], dtype=float)
    kf = np.asarray(falling["k"], dtype=float)
    compressed_kr = pybis2spice.compress_param(kr, threshold=1e-3)
    compressed_kf = pybis2spice.compress_param(kf, threshold=1e-3)
    fit = subcircuit.gate_state_fit(compressed_kr, compressed_kf)
    endpoint = expected_endpoint_error(kr, kf)
    return {
        "case": case,
        "data_model": data_model,
        "rising": rising,
        "falling": falling,
        "kr": kr,
        "kf": kf,
        "fit": fit,
        "endpoint": endpoint,
    }


def fixture_label(waveform: object, corner: int, index: int) -> str:
    v_fix = float(waveform.v_fix[corner - 1])
    return f"fixture {index}: Vfix={v_fix:g} V, R={float(waveform.r_fix):g} ohm"


def save_raw_data(analysis: dict[str, object]) -> None:
    case = analysis["case"]
    assert isinstance(case, ModelCase)
    for direction in ["rising", "falling"]:
        result = analysis[direction]
        rows: list[dict[str, object]] = []
        time_s = np.asarray(result["time_s"], dtype=float)
        k = np.asarray(result["k"], dtype=float)
        for index, time_value in enumerate(time_s):
            rows.append(
                {
                    "time_s": time_value,
                    "time_ns": time_value * 1e9,
                    "fixture1_v": result["v1"][index],
                    "fixture2_v": result["v2"][index],
                    "ku": k[index, 1],
                    "kd": k[index, 2],
                    "solve_condition_number": result["cond"][index],
                    "solve_determinant": result["determinant"][index],
                    "fixture1_i_rfix_a": result["i_rfix1"][index],
                    "fixture2_i_rfix_a": result["i_rfix2"][index],
                    "fixture1_i_ccomp_a": result["i_ccomp1"][index],
                    "fixture2_i_ccomp_a": result["i_ccomp2"][index],
                }
            )
        write_csv(DATA_DIR / f"{case.case_id}_{direction}.csv", rows)


def summary_rows(
    analyses: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    waveform_rows: list[dict[str, object]] = []
    endpoint_rows: list[dict[str, object]] = []
    solve_rows: list[dict[str, object]] = []
    for analysis in analyses:
        case = analysis["case"]
        assert isinstance(case, ModelCase)
        for direction in ["rising", "falling"]:
            result = analysis[direction]
            for fixture_index in [1, 2]:
                markers = result[f"markers{fixture_index}"]
                waveform = result[f"waveform{fixture_index}"]
                waveform_rows.append(
                    {
                        "case_id": case.case_id,
                        "device": case.device,
                        "edge_setting": case.edge_label,
                        "direction": direction,
                        "fixture": fixture_index,
                        "v_fix_v": float(waveform.v_fix[0]),
                        "r_fix_ohm": float(waveform.r_fix),
                        **markers,
                    }
                )
            cond = np.asarray(result["cond"], dtype=float)
            determinant = np.asarray(result["determinant"], dtype=float)
            solve_rows.append(
                {
                    "case_id": case.case_id,
                    "direction": direction,
                    "condition_p50": float(np.percentile(cond, 50)),
                    "condition_p95": float(np.percentile(cond, 95)),
                    "condition_max": float(np.max(cond)),
                    "min_abs_determinant": float(np.min(np.abs(determinant))),
                    "fixture_t50_separation_ns": result["fixture_t50_separation_ns"],
                    "peak_ccomp_to_rfixture_ratio": result[
                        "peak_ccomp_to_rfixture_ratio"
                    ],
                    "fixture1_peak_ccomp_time_ns": result[
                        "fixture1_peak_ccomp_time_ns"
                    ],
                    "fixture2_peak_ccomp_time_ns": result[
                        "fixture2_peak_ccomp_time_ns"
                    ],
                    "solve_ill_conditioned_count_gt_1000": int(np.sum(cond > 1000.0)),
                }
            )
        kr = np.asarray(analysis["kr"], dtype=float)
        kf = np.asarray(analysis["kf"], dtype=float)
        fit = analysis["fit"]
        endpoint = analysis["endpoint"]
        endpoint_rows.append(
            {
                "case_id": case.case_id,
                "device": case.device,
                "edge_setting": case.edge_label,
                "kr_start_ku": kr[0, 1],
                "kr_start_kd": kr[0, 2],
                "kr_end_ku": kr[-1, 1],
                "kr_end_kd": kr[-1, 2],
                "kf_start_ku": kf[0, 1],
                "kf_start_kd": kf[0, 2],
                "kf_end_ku": kf[-1, 1],
                "kf_end_kd": kf[-1, 2],
                "max_endpoint_error": endpoint["max_endpoint_error"],
                "fitted_ku_off": fit["ku_off"],
                "fitted_ku_on": fit["ku_on"],
                "fitted_kd_off": fit["kd_off"],
                "fitted_kd_on": fit["kd_on"],
                "pu_on_delay_ns": fit["pu_on_delay"],
                "pu_off_delay_ns": fit["pu_off_delay"],
                "pd_on_delay_ns": fit["pd_on_delay"],
                "pd_off_delay_ns": fit["pd_off_delay"],
                "pu_on_tau_ns": fit["pu_on_tau"],
                "pu_off_tau_ns": fit["pu_off_tau"],
                "pd_on_tau_ns": fit["pd_on_tau"],
                "pd_off_tau_ns": fit["pd_off_tau"],
            }
        )
    return waveform_rows, endpoint_rows, solve_rows


def plot_raw_vt(analyses: list[dict[str, object]]) -> None:
    fig, axes = plt.subplots(4, 2, figsize=(13.5, 14.0), constrained_layout=True)
    for row, analysis in enumerate(analyses):
        case = analysis["case"]
        assert isinstance(case, ModelCase)
        for column, direction in enumerate(["rising", "falling"]):
            result = analysis[direction]
            ax = axes[row, column]
            t_ns = np.asarray(result["time_s"]) * 1e9
            ax.plot(
                t_ns,
                result["v1"],
                color=BLUE,
                label=fixture_label(result["waveform1"], 1, 1),
            )
            ax.plot(
                t_ns,
                result["v2"],
                color=ORANGE,
                label=fixture_label(result["waveform2"], 1, 2),
            )
            ax.set_title(f"{case.label}: {direction} V-T")
            ax.set_xlabel("IBIS waveform time (ns)")
            ax.set_ylabel("Fixture voltage (V)")
            ax.legend(loc="best")
    fig.suptitle(
        "Raw IBIS V-T waveforms: fixture synchronization and boundary behavior",
        fontsize=15,
        fontweight="bold",
    )
    fig.savefig(PLOTS_DIR / "01_raw_vt_waveforms.png")
    plt.close(fig)


def plot_boundary_zoom(analyses: list[dict[str, object]]) -> None:
    fig, axes = plt.subplots(4, 2, figsize=(14.0, 14.0), constrained_layout=True)
    for row, analysis in enumerate(analyses):
        case = analysis["case"]
        assert isinstance(case, ModelCase)
        rise = analysis["rising"]
        ax_v = axes[row, 0]
        t_ns = np.asarray(rise["time_s"]) * 1e9
        window = t_ns <= 0.10 + 1e-12
        ax_v.plot(
            t_ns[window],
            np.asarray(rise["v1"])[window] - float(rise["v1"][0]),
            color=BLUE,
            label="rising fixture 1",
        )
        ax_v.plot(
            t_ns[window],
            np.asarray(rise["v2"])[window] - float(rise["v2"][0]),
            color=ORANGE,
            label="rising fixture 2",
        )
        fall = analysis["falling"]
        tf_ns = np.asarray(fall["time_s"]) * 1e9
        fwindow = tf_ns <= 0.10 + 1e-12
        ax_v.plot(
            tf_ns[fwindow],
            np.asarray(fall["v1"])[fwindow] - float(fall["v1"][0]),
            color=GREEN,
            label="falling fixture 1",
        )
        ax_v.plot(
            tf_ns[fwindow],
            np.asarray(fall["v2"])[fwindow] - float(fall["v2"][0]),
            color=PURPLE,
            label="falling fixture 2",
        )
        ax_v.axhline(0.0, color=BLACK, lw=0.8)
        ax_v.set_title(f"{case.label}: first 100 ps voltage change")
        ax_v.set_xlabel("IBIS waveform time (ns)")
        ax_v.set_ylabel("V(t) - V(0) (V)")
        ax_v.legend(loc="best", ncols=2)

        ax_k = axes[row, 1]
        for result, direction, ku_color, kd_color in [
            (rise, "rise", BLUE, ORANGE),
            (fall, "fall", GREEN, PURPLE),
        ]:
            tk_ns = np.asarray(result["k"][:, 0]) * 1e9
            kwindow = tk_ns <= 0.10 + 1e-12
            ax_k.plot(
                tk_ns[kwindow],
                result["k"][kwindow, 1],
                color=ku_color,
                label=f"Ku {direction}",
            )
            ax_k.plot(
                tk_ns[kwindow],
                result["k"][kwindow, 2],
                color=kd_color,
                label=f"Kd {direction}",
            )
        ax_k.axhline(0.0, color=BLACK, lw=0.8)
        ax_k.axhline(1.0, color=GRAY, lw=0.8)
        ax_k.set_title(f"{case.label}: first 100 ps extracted K")
        ax_k.set_xlabel("IBIS waveform time (ns)")
        ax_k.set_ylabel("Coefficient")
        ax_k.legend(loc="best", ncols=2)
    fig.suptitle(
        "Table-boundary evidence: fast io_buf begins with an impulse, not a plateau",
        fontsize=15,
        fontweight="bold",
    )
    fig.savefig(PLOTS_DIR / "02_first_100ps_boundary_zoom.png")
    plt.close(fig)


def plot_k_tables(analyses: list[dict[str, object]]) -> None:
    fig, axes = plt.subplots(4, 2, figsize=(13.5, 14.0), constrained_layout=True)
    for row, analysis in enumerate(analyses):
        case = analysis["case"]
        assert isinstance(case, ModelCase)
        for column, direction in enumerate(["rising", "falling"]):
            result = analysis[direction]
            k = np.asarray(result["k"], dtype=float)
            ax = axes[row, column]
            ax.plot(k[:, 0] * 1e9, k[:, 1], color=BLUE, label="Ku")
            ax.plot(k[:, 0] * 1e9, k[:, 2], color=ORANGE, label="Kd")
            ax.axhline(0.0, color=BLACK, lw=0.8)
            ax.axhline(1.0, color=GRAY, lw=0.8)
            ax.scatter(
                [k[0, 0] * 1e9],
                [k[0, 1]],
                color=BLUE,
                edgecolor=BLACK,
                zorder=4,
            )
            ax.scatter(
                [k[0, 0] * 1e9],
                [k[0, 2]],
                color=ORANGE,
                edgecolor=BLACK,
                zorder=4,
            )
            ax.set_title(
                f"{case.label}: {direction} Ku/Kd\n"
                f"start=({k[0, 1]:.3f}, {k[0, 2]:.3f})"
            )
            ax.set_xlabel("IBIS waveform time (ns)")
            ax.set_ylabel("Coefficient")
            ax.legend(loc="best")
    fig.suptitle(
        "Extracted Ku/Kd from the two IBIS waveform fixtures",
        fontsize=15,
        fontweight="bold",
    )
    fig.savefig(PLOTS_DIR / "03_extracted_kukd_tables.png")
    plt.close(fig)


def plot_quality_summary(analyses: list[dict[str, object]]) -> None:
    labels = [analysis["case"].label for analysis in analyses]
    endpoint_error = [
        float(analysis["endpoint"]["max_endpoint_error"]) for analysis in analyses
    ]
    boundary_excursion = []
    t50_separation = []
    solve_condition = []
    ccomp_ratio = []
    for analysis in analyses:
        boundary_excursion.append(
            max(
                analysis[direction][f"markers{fixture}"][
                    "boundary_excursion_50ps_v"
                ]
                for direction in ["rising", "falling"]
                for fixture in [1, 2]
            )
        )
        t50_separation.append(
            max(
                float(analysis[direction]["fixture_t50_separation_ns"])
                for direction in ["rising", "falling"]
            )
        )
        solve_condition.append(
            max(
                float(np.max(analysis[direction]["cond"]))
                for direction in ["rising", "falling"]
            )
        )
        ccomp_ratio.append(
            max(
                float(analysis[direction]["peak_ccomp_to_rfixture_ratio"])
                for direction in ["rising", "falling"]
            )
        )
    colors = [ORANGE, RED, BLUE, GREEN]
    fig, axes = plt.subplots(2, 3, figsize=(16.0, 8.8), constrained_layout=True)
    metrics = [
        (
            boundary_excursion,
            "Largest voltage movement in first 50 ps",
            "Voltage excursion (V)",
        ),
        (
            endpoint_error,
            "Ku/Kd endpoint error",
            "Max absolute endpoint error",
        ),
        (
            t50_separation,
            "Separation between fixture t50 values",
            "Absolute t50 separation (ns)",
        ),
        (
            ccomp_ratio,
            "Ccomp-current sensitivity",
            "Peak |I_Ccomp| / peak |I_Rfixture|",
        ),
        (
            solve_condition,
            "Two-fixture solve condition number",
            "Maximum condition number",
        ),
    ]
    for ax, (values, title, ylabel) in zip(axes.flat, metrics):
        x = np.arange(len(labels))
        bars = ax.bar(x, values, color=colors)
        ax.set_xticks(x, labels, rotation=24, ha="right")
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                fmt(value, 4),
                ha="center",
                va="bottom",
                fontsize=8,
            )
    explanation = axes.flat[-1]
    explanation.axis("off")
    explanation.text(
        0.03,
        0.95,
        "How to read the evidence",
        va="top",
        fontsize=14,
        fontweight="bold",
    )
    explanation.text(
        0.03,
        0.82,
        "Fast io_buf-specific:\n"
        "1. Immediate V-T boundary impulse.\n"
        "2. Ccomp current dominates the earliest samples.\n"
        "3. Start coefficients are not settled endpoints.\n\n"
        "io_buf topology clue (slow and fast):\n"
        "4. Its two fixtures are strongly time-separated.\n\n"
        "All four 2x2 solves are well conditioned. The failure is a\n"
        "boundary/state-identification problem plus a model-order mismatch.",
        va="top",
        linespacing=1.35,
        fontsize=11,
    )
    fig.suptitle(
        "IBIS input-quality and extraction diagnostics",
        fontsize=15,
        fontweight="bold",
    )
    fig.savefig(PLOTS_DIR / "04_quality_metric_summary.png")
    plt.close(fig)


def plot_failure_chain(analyses: list[dict[str, object]]) -> None:
    fast = next(a for a in analyses if a["case"].case_id == "io_buf_fast_5ps")
    slow = next(a for a in analyses if a["case"].case_id == "io_buf_slow_1ns")
    inv = next(a for a in analyses if a["case"].case_id == "inv_chain_fast_5ps")
    fkr = np.asarray(fast["kr"])
    fkf = np.asarray(fast["kf"])
    fit = fast["fit"]
    fig, ax = plt.subplots(figsize=(15.5, 6.8), constrained_layout=True)
    ax.axis("off")
    boxes = [
        (
            0.02,
            "1. Raw fast io_buf V-T",
            "Immediate 6-20 ps feedthrough/ringing\n"
            f"first-50-ps excursion: "
            f"{max(fast[d][f'markers{i}']['boundary_excursion_50ps_v'] for d in ['rising','falling'] for i in [1,2]):.3f} V",
            RED,
        ),
        (
            0.265,
            "2. Extracted boundary K",
            f"rise t=0: Ku={fkr[0,1]:.3f}, Kd={fkr[0,2]:.3f}\n"
            f"fall t=0: Ku={fkf[0,1]:.3f}, Kd={fkf[0,2]:.3f}",
            ORANGE,
        ),
        (
            0.51,
            "3. Endpoint averaging",
            "gate_state_fit averages first and last samples\n"
            f"Ku off/on={fit['ku_off']:.3f}/{fit['ku_on']:.3f}\n"
            f"Kd off/on={fit['kd_off']:.3f}/{fit['kd_on']:.3f}",
            PURPLE,
        ),
        (
            0.755,
            "4. Wrong hidden-state model",
            "GUP/GDN no longer represent 0=off, 1=on.\n"
            "One first-order state also cannot reproduce\n"
            "the early feedthrough plus delayed main edge.",
            BLUE,
        ),
    ]
    for x, title, body, color in boxes:
        ax.add_patch(
            plt.Rectangle(
                (x, 0.28),
                0.215,
                0.48,
                transform=ax.transAxes,
                facecolor="white",
                edgecolor=color,
                linewidth=2.5,
            )
        )
        ax.text(
            x + 0.012,
            0.70,
            title,
            transform=ax.transAxes,
            fontsize=12,
            fontweight="bold",
            color=color,
            va="top",
        )
        ax.text(
            x + 0.012,
            0.62,
            body,
            transform=ax.transAxes,
            fontsize=10,
            va="top",
            linespacing=1.35,
        )
    for x in [0.235, 0.48, 0.725]:
        ax.annotate(
            "",
            xy=(x + 0.025, 0.52),
            xytext=(x, 0.52),
            xycoords=ax.transAxes,
            arrowprops={"arrowstyle": "->", "lw": 2.0, "color": BLACK},
        )
    ax.text(
        0.02,
        0.18,
        "Controls: "
        f"io_buf slow endpoint error={slow['endpoint']['max_endpoint_error']:.4f}; "
        f"inv_chain fast endpoint error={inv['endpoint']['max_endpoint_error']:.4f}. "
        f"Fast io_buf max solve condition={max(np.max(fast[d]['cond']) for d in ['rising','falling']):.2f}, "
        "so the 2x2 extraction is not singular.",
        transform=ax.transAxes,
        fontsize=11,
        bbox={"facecolor": "#F4F4F4", "edgecolor": "#BBBBBB", "pad": 8},
    )
    ax.set_title(
        "Why the current two-state gate model fails on fast io_buf",
        fontsize=16,
        fontweight="bold",
    )
    fig.savefig(PLOTS_DIR / "05_fast_io_buf_failure_chain.png")
    plt.close(fig)


def transistor_structure_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in [CASES[0], CASES[2]]:
        text = case.transistor_sp.read_text(encoding="utf-8", errors="ignore")
        mos_lines = [
            line.strip()
            for line in text.splitlines()
            if re.match(r"^\s*[mM]\w+", line)
        ]
        cap_lines = [
            line.strip()
            for line in text.splitlines()
            if re.match(r"^\s*[cC]\w+", line)
        ]
        output_mos = []
        for line in mos_lines:
            tokens = line.split()
            if len(tokens) < 4:
                continue
            drain = tokens[1].lower()
            source = tokens[3].lower()
            if drain in {"out", "vout8"} or source in {"out", "vout8"}:
                output_mos.append(line)
        gate_nodes: list[str] = []
        for line in output_mos:
            tokens = line.split()
            if len(tokens) >= 3:
                # MOS syntax: Mname drain gate source bulk model ...
                gate_nodes.append(tokens[2])
        rows.append(
            {
                "device": case.device,
                "transistor_source": str(case.transistor_sp.relative_to(ROOT)),
                "mos_count": len(mos_lines),
                "capacitor_count": len(cap_lines),
                "output_stage_mos_count": len(output_mos),
                "output_stage_gate_nodes": ";".join(sorted(set(gate_nodes))),
                "structure_interpretation": (
                    "separate pullup/pulldown control paths and tri-state logic"
                    if case.device == "io_buf"
                    else "tapered inverter chain with a shared final-stage gate node"
                ),
            }
        )
    return rows


def electrical_context_rows(analyses: list[dict[str, object]]) -> list[dict[str, object]]:
    by_device = {analysis["case"].device: analysis for analysis in analyses}
    io_model = by_device["io_buf"]["data_model"]
    inv_model = by_device["inv_chain"]["data_model"]
    rows: list[dict[str, object]] = [
        {
            "device": "io_buf",
            "vdd_v": 3.3,
            "settled_high_v_50ohm": 1.544661,
            "effective_pullup_r_ohm": 56.8196,
            "c_comp_pf": float(io_model.c_comp[0]) * 1e12,
            "output_pfet_effective_width_um": 5.0 * 42.15,
            "output_nfet_effective_width_um": 5.0 * 21.15,
            "output_length_um": 0.9,
            "source": (
                "results/io_buf_hspice_capacitance_driver_strength_2026-07-23/"
                "metrics.csv; models/io_buf.sp"
            ),
        },
        {
            "device": "inv_chain",
            "vdd_v": 1.8,
            "settled_high_v_50ohm": 1.4308080869565218,
            "effective_pullup_r_ohm": (
                (1.8 - 1.4308080869565218) / (1.4308080869565218 / 50.0)
            ),
            "c_comp_pf": float(inv_model.c_comp[0]) * 1e12,
            "output_pfet_effective_width_um": 2.0 * 128.0,
            "output_nfet_effective_width_um": 1.0 * 128.0,
            "output_length_um": 0.18,
            "source": (
                "results/inv_chain_s2ibispy_slow_fast_2026-07-27/"
                "hspice_sanity_metrics.csv; inv_chain/invchain_subckt_typ.sp"
            ),
        },
    ]
    return rows


def render_readme(
    analyses: list[dict[str, object]],
    waveform_rows: list[dict[str, object]],
    endpoint_rows: list[dict[str, object]],
    solve_rows: list[dict[str, object]],
    structure_rows: list[dict[str, object]],
    electrical_rows: list[dict[str, object]],
) -> None:
    by_case = {a["case"].case_id: a for a in analyses}
    fast = by_case["io_buf_fast_5ps"]
    slow = by_case["io_buf_slow_1ns"]
    inv_fast = by_case["inv_chain_fast_5ps"]
    fkr = np.asarray(fast["kr"])
    fkf = np.asarray(fast["kf"])
    fit = fast["fit"]
    max_fast_split = max(
        float(fast[d]["fixture_t50_separation_ns"]) for d in ["rising", "falling"]
    )
    max_inv_split = max(
        float(inv_fast[d]["fixture_t50_separation_ns"])
        for d in ["rising", "falling"]
    )
    max_fast_cond = max(
        float(np.max(fast[d]["cond"])) for d in ["rising", "falling"]
    )
    max_fast_ccomp = max(
        float(fast[d]["peak_ccomp_to_rfixture_ratio"])
        for d in ["rising", "falling"]
    )

    endpoint_table = [
        "| Model | rise start Ku/Kd | fall start Ku/Kd | max endpoint error | fitted off/on endpoints |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in endpoint_rows:
        endpoint_table.append(
            f"| {row['case_id']} | "
            f"{float(row['kr_start_ku']):.4f} / {float(row['kr_start_kd']):.4f} | "
            f"{float(row['kf_start_ku']):.4f} / {float(row['kf_start_kd']):.4f} | "
            f"{float(row['max_endpoint_error']):.4f} | "
            f"Ku {float(row['fitted_ku_off']):.3f}/{float(row['fitted_ku_on']):.3f}; "
            f"Kd {float(row['fitted_kd_off']):.3f}/{float(row['fitted_kd_on']):.3f} |"
        )

    structure_table = [
        "| Device | MOS | capacitors | output gate nodes | structural implication |",
        "|---|---:|---:|---|---|",
    ]
    for row in structure_rows:
        structure_table.append(
            f"| {row['device']} | {row['mos_count']} | {row['capacitor_count']} | "
            f"`{row['output_stage_gate_nodes']}` | {row['structure_interpretation']} |"
        )

    electrical_table = [
        "| Device | Vdd | settled high into 50 ohm | effective pullup R | Ccomp | output Wp/Wn, L |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in electrical_rows:
        electrical_table.append(
            f"| {row['device']} | {float(row['vdd_v']):.1f} V | "
            f"{float(row['settled_high_v_50ohm']):.4f} V | "
            f"{float(row['effective_pullup_r_ohm']):.2f} ohm | "
            f"{float(row['c_comp_pf']):.3f} pF | "
            f"{float(row['output_pfet_effective_width_um']):.2f}/"
            f"{float(row['output_nfet_effective_width_um']):.2f} um, "
            f"{float(row['output_length_um']):.2f} um |"
        )

    text = f"""# io_buf vs inv_chain: IBIS Waveform Failure Analysis

This report uses the existing IBIS files and pybis extraction code only. It runs
no HSPICE or ngspice simulations. Its purpose is to explain why the current
two-state gate model works for `inv_chain` but fails for the fast `io_buf` IBIS.

## Bottom Line

The fast `io_buf` failure is **not** caused by an ill-conditioned two-fixture
`Ku/Kd` linear solve. The maximum matrix condition number is only
`{max_fast_cond:.2f}`. The failure begins because the raw fast `io_buf` V-T
tables contain an immediate feedthrough/ringing event at the table boundary,
before a clean settled plateau exists.

That boundary event produces non-settled extracted coefficient samples:

- rising `t=0`: `Ku={fkr[0, 1]:.6f}`, `Kd={fkr[0, 2]:.6f}`
- falling `t=0`: `Ku={fkf[0, 1]:.6f}`, `Kd={fkf[0, 2]:.6f}`

The current `gate_state_fit()` then averages those first samples with the valid
opposite-table final samples. It therefore identifies:

- `Ku_off={fit['ku_off']:.6f}`, `Ku_on={fit['ku_on']:.6f}`
- `Kd_off={fit['kd_off']:.6f}`, `Kd_on={fit['kd_on']:.6f}`

Those values do not describe a normalized off/on hidden state. Once that
incorrect identification enters the GUP/GDN fit, the later residual branches
can improve an offline reconstruction numerically but cannot make the runtime
state physically meaningful.

## What the IBIS Waveforms Show

### inv_chain

The slow and fast `inv_chain` waveform fixtures both have a clean pre-edge
interval created by the eight-stage inverter chain. Their extracted coefficient
tables begin and end near the settled states:

- low: `Ku approximately 0`, `Kd approximately 1`
- high: `Ku approximately 1`, `Kd approximately 0`

The two fixtures also remain synchronized: the worst `t50` separation in the
fast model is only `{max_inv_split * 1e3:.1f} ps`. This supports a compact
single-progress-state interpretation.

### io_buf

The fast `io_buf` output begins moving within the first few picoseconds. The
first 50 ps contain a capacitive/feedthrough impulse; on the falling waveform,
the fixture voltage drops, rebounds, and only later enters its main transition.
The largest peak `|I_Ccomp| / |I_Rfixture|` ratio is `{max_fast_ccomp:.2f}`.
For both fast io_buf directions, the largest calculated `C_comp*dV/dt` term
occurs at `t=0`.

This follows directly from the extraction implementation. `differentiate()`
uses the forward interval `(V[1]-V[0])/(t[1]-t[0])`, and
`generating_current_data()` subtracts `C_comp*dV/dt` before solving Ku/Kd.
With no pre-edge sample, the first edge/feedthrough interval is assigned to the
first coefficient sample. That is acceptable for table replay, but it means
the first coefficient sample cannot also be assumed to be the settled endpoint.

The two io_buf fixtures also reach their main edges at very different times:
the worst `t50` separation is `{max_fast_split:.3f} ns`. This does not make the
2x2 solve singular, but it says the two loaded trajectories do not behave like
two synchronized observations of one simple hidden progress variable.
The slow io_buf separation is similarly large (`1.862 ns`), so fixture
desynchronization is a device/topology warning rather than the fast-model
failure by itself. The fast-model-specific evidence is the boundary impulse
and corrupted coefficient endpoints.

The slow `io_buf` model has the same asymmetric device, but its 1 ns excitation
suppresses the boundary impulse enough that the coefficient endpoints remain
valid. Its max endpoint error is only
`{float(slow['endpoint']['max_endpoint_error']):.4f}`.

## Why the Transistor Structures Differ

{chr(10).join(structure_table)}

`inv_chain` is an eight-stage regenerative inverter chain. The final PMOS and
NMOS share the same final internal gate node. A fast external edge is therefore
isolated and regenerated before reaching the output devices.

`io_buf` is a tri-state I/O buffer. Its output PMOS bank and NMOS bank use
different internal control nodes (`n2` and `n3`) and unequal logic paths. The
netlist also contains explicit parasitic capacitors around those internal/output
nodes. A 5 ps input can therefore produce:

1. direct capacitive/feedthrough motion,
2. separate pullup and pulldown predriver timing,
3. a later main output transition.

One first-order GUP and one first-order GDN can model the slow main behavior,
but not the boundary impulse plus the later multi-path transition as one state
trajectory.

### Electrical context

{chr(10).join(electrical_table)}

The output widths are similar in absolute size, but `io_buf` uses a much longer
output-device channel (`0.9 um` versus `0.18 um`) and is much weaker in the
shared 50 ohm check (`56.82 ohm` versus `12.90 ohm`). Its `C_comp` is also
larger (`1.2 pF` versus `0.468 pF`). These facts do not alone cause the fit
failure, but they make a fast boundary displacement current more important
relative to the conducting output network. The topology and waveform boundary
remain the decisive evidence.

## Exact Endpoint Evidence

{chr(10).join(endpoint_table)}

The damaging implementation assumption is visible in
`tools/pybis2spice/pybis2spice/subcircuit.py`:

```python
ku_off = mean(kr[0, Ku], kf[-1, Ku])
ku_on  = mean(kr[-1, Ku], kf[0, Ku])
kd_on  = mean(kr[0, Kd], kf[-1, Kd])
kd_off = mean(kr[-1, Kd], kf[0, Kd])
```

That is safe only when the first waveform sample is a settled endpoint. It is
true for both `inv_chain` IBIS files and the slow `io_buf` file; it is false for
the fast `io_buf` file.

## What Is Proven and What Is Inferred

**Proven from the cached data**

- The fast io_buf raw V-T tables contain strong first-sample/first-50-ps motion.
- Its extracted `Ku/Kd` starts are not settled endpoints.
- `gate_state_fit()` directly uses those starts to identify off/on values.
- The 2x2 extraction matrices are numerically well conditioned.
- The inv_chain tables have clean endpoints and synchronized fixture timing.
- The transistor netlists have fundamentally different output-control topology.

**Reasonable mechanism inference**

- io_buf's independent predriver paths and parasitic coupling explain why a
  very fast input creates an early feedthrough component that inv_chain's
  regenerative chain suppresses.
- The large fixture timing separation indicates load-dependent internal
  dynamics/Miller feedback that a two-state fit cannot uniquely identify from
  output V-T data alone.

Internal-node transistor transient probes would be needed to separate the exact
contributions of `n2`, `n3`, Ccomp, and each parasitic capacitor.

## Recommendation

Do **not** patch the fast io_buf result with more residual terms. The current
two-state method should reject this IBIS input using a waveform-quality gate:

- require a measurable settled pre-edge plateau,
- require coefficient endpoint consistency,
- report first-50-ps impulse magnitude,
- report fixture `t50` separation,
- confirm the 2x2 solve is conditioned.

For this file, retain legacy table replay. A principled future extension would
separate a quasi-static gate-state path from an explicit feedthrough/impulse
path, or regenerate the V-T tables with pre-trigger margin before the 5 ps
input edge. Merely changing endpoint averaging would remove one bug but would
not make the single-pole two-state model structurally adequate.

## Figures

- `plots/01_raw_vt_waveforms.png`
- `plots/02_first_100ps_boundary_zoom.png`
- `plots/03_extracted_kukd_tables.png`
- `plots/04_quality_metric_summary.png`
- `plots/05_fast_io_buf_failure_chain.png`

## Numeric Data

- `ibis_waveform_summary.csv`
- `k_endpoint_and_fit_summary.csv`
- `k_solve_diagnostics.csv`
- `transistor_structure_summary.csv`
- `electrical_context.csv`
- `source_manifest.csv`
- `waveform_data/<model>_<direction>.csv`

Every waveform-data CSV contains raw fixture voltages, extracted `Ku/Kd`,
condition number, determinant, fixture current, and Ccomp current on the common
time grid.
"""
    write_text(OUT_DIR / "README.md", text)


def main() -> None:
    global OUT_DIR, PLOTS_DIR, DATA_DIR
    parser = argparse.ArgumentParser(
        description="Analyze cached io_buf/inv_chain IBIS V-T and Ku/Kd extraction."
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    OUT_DIR = args.out_dir.resolve()
    PLOTS_DIR = OUT_DIR / "plots"
    DATA_DIR = OUT_DIR / "waveform_data"
    for path in [OUT_DIR, PLOTS_DIR, DATA_DIR]:
        ensure_dir(path)
    configure_plotting()

    missing = [case.ibis for case in CASES if not case.ibis.exists()]
    if missing:
        raise FileNotFoundError(f"Missing IBIS inputs: {missing}")

    analyses = [analyze_case(case) for case in CASES]
    for analysis in analyses:
        save_raw_data(analysis)

    waveform_rows, endpoint_rows, solve_rows = summary_rows(analyses)
    structure_rows = transistor_structure_rows()
    electrical_rows = electrical_context_rows(analyses)
    source_rows = [
        {
            "case_id": case.case_id,
            "ibis_path": str(case.ibis.relative_to(ROOT)),
            "ibis_sha256": sha256(case.ibis),
            "component": case.component,
            "model": case.model,
            "transistor_sp_path": str(case.transistor_sp.relative_to(ROOT)),
            "transistor_sp_sha256": sha256(case.transistor_sp),
        }
        for case in CASES
    ]
    write_csv(OUT_DIR / "ibis_waveform_summary.csv", waveform_rows)
    write_csv(OUT_DIR / "k_endpoint_and_fit_summary.csv", endpoint_rows)
    write_csv(OUT_DIR / "k_solve_diagnostics.csv", solve_rows)
    write_csv(OUT_DIR / "transistor_structure_summary.csv", structure_rows)
    write_csv(OUT_DIR / "electrical_context.csv", electrical_rows)
    write_csv(OUT_DIR / "source_manifest.csv", source_rows)

    plot_raw_vt(analyses)
    plot_boundary_zoom(analyses)
    plot_k_tables(analyses)
    plot_quality_summary(analyses)
    plot_failure_chain(analyses)
    render_readme(
        analyses,
        waveform_rows,
        endpoint_rows,
        solve_rows,
        structure_rows,
        electrical_rows,
    )
    print(f"Wrote cached-data analysis to {OUT_DIR}")


if __name__ == "__main__":
    main()
