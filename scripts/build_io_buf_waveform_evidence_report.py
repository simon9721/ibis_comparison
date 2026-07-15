from __future__ import annotations

import math
import sys
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
import run_io_buf_value_matched_replay_v2 as base  # noqa: E402


RESULT_ROOT = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
CASES_DIR = RESULT_ROOT / "cases"
OUT_DIR = RESULT_ROOT / "waveform_evidence_report"
PLOTS_DIR = OUT_DIR / "plots"
DATA_DIR = OUT_DIR / "data"

CASE_IDS = [
    "edge_1ps_base_50r_2pf",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
    "short_pulse_1ns_low",
]

PANEL_FLOWS = [
    "hspice_native_ibis",
    "ngspice_legacy",
    "ngspice_value_match_v2",
    "ngspice_two_state_directional_residual",
    "ngspice_two_state_directional_residual_recover_mean",
]
PAD_EXTRA_FLOWS = ["hspice_transistor_sp"]

EVOLUTION_FLOWS = [
    "ngspice_legacy",
    "ngspice_value_match_v2",
    "ngspice_two_state_identity",
    "ngspice_two_state_pwl",
    "ngspice_two_state_directional",
    "ngspice_two_state_directional_residual",
    "ngspice_two_state_directional_residual_recover_mean",
]

FLOW_LABELS = {
    "hspice_native_ibis": "HSPICE native IBIS",
    "hspice_transistor_sp": "HSPICE transistor io_buf.sp",
    "ngspice_legacy": "legacy pybis",
    "ngspice_value_match_v2": "value-match v2",
    "ngspice_two_state_identity": "two-state identity",
    "ngspice_two_state_pwl": "two-state PWL",
    "ngspice_two_state_directional": "two-state directional",
    "ngspice_two_state_directional_residual": "directional + residual",
    "ngspice_two_state_directional_residual_recover_mean": "recover mean",
}

FLOW_COLORS = {
    "hspice_native_ibis": "#000000",
    "hspice_transistor_sp": "#8a8a8a",
    "ngspice_legacy": "#e68613",
    "ngspice_value_match_v2": "#7b2cbf",
    "ngspice_two_state_identity": "#1b9e77",
    "ngspice_two_state_pwl": "#66a61e",
    "ngspice_two_state_directional": "#1f77b4",
    "ngspice_two_state_directional_residual": "#d62728",
    "ngspice_two_state_directional_residual_recover_mean": "#2ca02c",
}

FLOW_WIDTHS = {
    "hspice_native_ibis": 3.1,
    "hspice_transistor_sp": 3.0,
}

FLOW_MARKERS = {
    "hspice_native_ibis": None,
    "hspice_transistor_sp": None,
    "ngspice_legacy": "o",
    "ngspice_value_match_v2": "s",
    "ngspice_two_state_identity": "P",
    "ngspice_two_state_pwl": "X",
    "ngspice_two_state_directional": "D",
    "ngspice_two_state_directional_residual": "^",
    "ngspice_two_state_directional_residual_recover_mean": "v",
}

FLOW_MARK_START = {
    "ngspice_legacy": 8,
    "ngspice_value_match_v2": 20,
    "ngspice_two_state_identity": 32,
    "ngspice_two_state_pwl": 44,
    "ngspice_two_state_directional": 56,
    "ngspice_two_state_directional_residual": 68,
    "ngspice_two_state_directional_residual_recover_mean": 80,
}

SHORT_PULSE_FLOWS = [
    "hspice_native_ibis",
    "ngspice_value_match_v2",
    "ngspice_two_state_directional_residual",
    "ngspice_two_state_directional_residual_recover_mean",
]

PAIR_MODEL = "ngspice_two_state_directional_residual"


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


def get_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray | None:
    lower = {key.lower(): key for key in data}
    for name in names:
        key = lower.get(name.lower())
        if key is not None:
            return np.asarray(data[key], dtype=float)
    return None


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


def pad_signal(data: dict[str, np.ndarray], flow: str) -> np.ndarray | None:
    if flow == "hspice_native_ibis":
        return get_signal(data, "v(pad_ibis)")
    if flow == "hspice_transistor_sp":
        return get_signal(data, "v(pad_sp)")
    return get_signal(data, "v(pad)")


def coeff_signal(data: dict[str, np.ndarray], coeff: str) -> np.ndarray | None:
    return get_signal(data, f"v({coeff})", f"v(xdrv.{coeff})", f"v(xdrv:{coeff})")


def relevant_edges(case: base.StudyCase) -> list[tuple[float, str]]:
    edge = 0.5 * case.edge_ns
    if case.pattern == "rise_fall":
        return [(5.0 + edge, "rise"), (15.0 + edge, "fall")]
    if case.pattern == "short_high":
        return [(5.0 + edge, "rise"), (5.0 + case.pulse_width_ns + edge, "reverse/fall")]
    if case.pattern == "short_low":
        return [(10.0 + edge, "fall"), (10.0 + case.pulse_width_ns + edge, "reverse/rise")]
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
    elif direction == "fall":
        idx = np.where((d[:-1] >= 0.0) & (d[1:] < 0.0))[0]
    else:
        raise ValueError(direction)
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
    if kd is None:
        return None
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


def zoom_window(case: base.StudyCase, native: dict[str, np.ndarray] | None) -> tuple[float, float]:
    edges = relevant_edges(case)
    start_ns = max(0.0, edges[0][0] - 1.0)
    end_candidates = [end for _, end in base.transition_windows(case)]
    if native is not None:
        hold = native_kd_hold_region(case, native)
        if hold is not None:
            end_candidates.append(hold[1])
    end_ns = min(case.stop_ns, max(end_candidates) + 2.0)
    return start_ns, end_ns


def shade_hold_region(ax: plt.Axes, hold: tuple[float, float] | None) -> None:
    if hold is None:
        return
    ax.axvspan(hold[0], hold[1], color="#f2c14e", alpha=0.18, lw=0)


def mark_edges(ax: plt.Axes, case: base.StudyCase) -> None:
    ymin, ymax = ax.get_ylim()
    y_text = ymax - 0.08 * (ymax - ymin)
    for x, label in relevant_edges(case):
        ax.axvline(x, color="#444444", ls="--", lw=1.1, alpha=0.8)
        ax.text(x, y_text, f" {label}", rotation=90, va="top", ha="left", fontsize=8, color="#333333")


def plot_wave(ax: plt.Axes, data: dict[str, np.ndarray], y: np.ndarray, flow: str, label: str | None = None) -> None:
    marker = FLOW_MARKERS.get(flow)
    line, = ax.plot(
        t_ns(data),
        y,
        color=FLOW_COLORS[flow],
        lw=FLOW_WIDTHS.get(flow, 1.9),
        alpha=0.96,
        marker=marker,
        markevery=(FLOW_MARK_START.get(flow, 0), 150) if marker else None,
        markersize=4.2 if marker else 0,
        markerfacecolor="white" if marker else None,
        markeredgecolor=FLOW_COLORS[flow] if marker else None,
        markeredgewidth=1.25 if marker else 0,
        zorder=2 if flow.startswith("hspice") else 3,
        label=label if label is not None else FLOW_LABELS[flow],
    )
    if flow.startswith("ngspice"):
        line.set_path_effects([path_effects.Stroke(linewidth=line.get_linewidth() + 1.5, foreground="white"), path_effects.Normal()])


def style_axes(axes: list[plt.Axes] | np.ndarray, case: base.StudyCase, x0: float, x1: float, hold: tuple[float, float] | None = None) -> None:
    for ax in np.asarray(axes).ravel():
        shade_hold_region(ax, hold)
        ax.grid(True, alpha=0.24)
        ax.set_xlim(x0, x1)
        mark_edges(ax, case)


def add_figure_legend(
    fig: plt.Figure,
    axes: list[plt.Axes] | np.ndarray,
    ncol: int = 3,
    bbox_y: float = 0.985,
) -> None:
    legend_items: dict[str, object] = {}
    for ax in np.asarray(axes).ravel():
        handles, labels = ax.get_legend_handles_labels()
        for handle, label in zip(handles, labels):
            legend_items.setdefault(label, handle)
    fig.legend(
        list(legend_items.values()),
        list(legend_items.keys()),
        loc="upper center",
        ncol=ncol,
        frameon=True,
        fontsize=9,
        bbox_to_anchor=(0.5, bbox_y),
    )


def case_caption(case_id: str) -> list[str]:
    captions = {
        "edge_1ps_base_50r_2pf": [
            "Normal long-pulse control: legacy pybis should stay closest to native-IBIS Ku/Kd.",
            "Use the Ku/Kd panels to verify that experimental models do not earn credit from pad-only agreement.",
            "The pad panel includes transistor io_buf.sp only as a pad-level reference; it has no Ku/Kd coefficients.",
            "The wide native-vs-transistor pad difference is a setup/reference warning, not a pybis coefficient result.",
            "This is the preservation check: any short-pulse fix that breaks this case cannot become default.",
        ],
        "short_pulse_1ns_high": [
            "The shaded band is the native-IBIS Kd hold/recovery region after the reverse falling edge.",
            "Legacy pybis overdrives Ku toward a full pulse; value-match/two-state methods keep Ku partial.",
            "Kd is the hard problem: several methods improve pad shape while still missing native-IBIS Kd recovery.",
            "The transistor pad returns much sooner than the shaded native-IBIS Kd hold, so the hold is a playback target.",
            "This is the clearest evidence that pad improvement and coefficient correctness must be judged separately.",
        ],
        "short_pulse_2ns_high": [
            "The shaded native-IBIS Kd hold is even later here, while the transistor pad still returns quickly.",
            "Two-state directional models make Ku more partial than legacy, but Kd recovery remains model-dependent.",
            "Recover-mean improves native-IBIS Kd timing for this width more than for 1 ns, showing width sensitivity.",
            "The pad panel shows that transistor and native IBIS disagree in amplitude as well as timing.",
            "This case argues against a single fixed Kd recovery delay as a production solution.",
        ],
        "short_pulse_1ns_low": [
            "This mirrored direction behaves differently: short-low is generally easier for the two-state model.",
            "Watch Kd first: directional/residual variants track the native coefficient much better than short-high.",
            "Ku still matters because it carries the pullup-side recovery during the low pulse interruption.",
            "The transistor pad remains a pad-only reference and should not be read as a coefficient truth source.",
            "The contrast with short-high points to directional recovery logic, not static map fitting, as the remaining gap.",
        ],
    }
    return captions[case_id]


def evolution_caption() -> list[str]:
    return [
        "Each small panel compares one model generation against the same native-IBIS Kd reference.",
        "Legacy and value-match show why table replay/retiming alone is not enough for Kd.",
        "Identity/PWL/two-state variants improve hidden-state structure but still miss recovery behavior.",
        "Directional residual restores undershoot better, while recover-mean moves the Kd return earlier.",
        "The progression shows the real lever: Kd onset/recovery policy, not only Ku amplitude or pad shape.",
    ]


def plot_case(case: base.StudyCase) -> Path:
    loaded = {flow: load_flow(case.case_id, flow) for flow in PANEL_FLOWS + PAD_EXTRA_FLOWS}
    native = loaded["hspice_native_ibis"]
    if native is None:
        raise FileNotFoundError(case.case_id)
    hold = native_kd_hold_region(case, native)
    x0, x1 = zoom_window(case, native)

    fig, axes = plt.subplots(3, 1, figsize=(12.5, 9.0), sharex=True)
    for ax in axes:
        shade_hold_region(ax, hold)
        ax.grid(True, alpha=0.24)

    for flow in PANEL_FLOWS:
        data = loaded.get(flow)
        if data is None:
            continue
        ku = coeff_signal(data, "ku")
        kd = coeff_signal(data, "kd")
        pad = pad_signal(data, flow)
        if ku is not None:
            plot_wave(axes[0], data, ku, flow)
        if kd is not None:
            plot_wave(axes[1], data, kd, flow)
        if pad is not None:
            plot_wave(axes[2], data, pad, flow)

    trans = loaded.get("hspice_transistor_sp")
    if trans is not None:
        pad = pad_signal(trans, "hspice_transistor_sp")
        if pad is not None:
            plot_wave(axes[2], trans, pad, "hspice_transistor_sp")

    axes[0].set_ylabel("Ku")
    axes[1].set_ylabel("Kd")
    axes[2].set_ylabel("Pad voltage (V)")
    axes[2].set_xlabel("Time (ns)")
    axes[1].axhline(0.0, color="#555555", lw=1.1, alpha=0.8)
    axes[2].axhline(0.0, color="#999999", lw=0.8, alpha=0.5)
    for ax in axes:
        ax.set_xlim(x0, x1)
        mark_edges(ax, case)
    if hold is not None:
        axes[0].text(hold[0], axes[0].get_ylim()[1], " native-IBIS Kd hold region", va="top", ha="left", fontsize=9, color="#8a6d1d")

    handles, labels = axes[2].get_legend_handles_labels()
    # Preserve one legend with every visible flow, using the first handle seen for each label.
    legend_items: dict[str, object] = {}
    for ax in axes:
        h, l = ax.get_legend_handles_labels()
        for handle, label in zip(h, l):
            legend_items.setdefault(label, handle)
    fig.legend(
        list(legend_items.values()),
        list(legend_items.keys()),
        loc="upper center",
        ncol=3,
        frameon=True,
        fontsize=9,
        bbox_to_anchor=(0.5, 0.985),
    )
    fig.suptitle(f"{case.case_id}: cached waveform evidence", y=0.999, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.935))

    out = PLOTS_DIR / f"{case.case_id}_waveform_evidence.png"
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out


def plot_short_pulse_without_legacy(case: base.StudyCase) -> Path:
    loaded = {flow: load_flow(case.case_id, flow) for flow in SHORT_PULSE_FLOWS}
    native = loaded["hspice_native_ibis"]
    if native is None:
        raise FileNotFoundError(case.case_id)
    hold = native_kd_hold_region(case, native)
    x0, x1 = zoom_window(case, native)

    fig, axes = plt.subplots(3, 1, figsize=(13.5, 9.5), sharex=True)
    for flow in SHORT_PULSE_FLOWS:
        data = loaded.get(flow)
        if data is None:
            continue
        for ax, signal in zip(
            axes,
            (coeff_signal(data, "ku"), coeff_signal(data, "kd"), pad_signal(data, flow)),
        ):
            if signal is not None:
                plot_wave(ax, data, signal, flow)

    style_axes(axes, case, x0, x1, hold)
    axes[0].set_ylabel("Ku")
    axes[1].set_ylabel("Kd")
    axes[2].set_ylabel("Pad voltage (V)")
    axes[2].set_xlabel("Time (ns)")
    axes[1].axhline(0.0, color="#555555", lw=1.0, alpha=0.75)
    axes[2].axhline(0.0, color="#888888", lw=0.8, alpha=0.5)
    add_figure_legend(fig, axes, ncol=2)
    fig.suptitle(f"{case.case_id}: new methods vs native IBIS (legacy omitted)", y=0.999, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.925))

    out_dir = PLOTS_DIR / "short_pulse_no_legacy"
    ensure_dir(out_dir)
    out = out_dir / f"{case.case_id}_new_methods_vs_native.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def plot_directional_residual_vs_native(case: base.StudyCase) -> Path:
    native = load_flow(case.case_id, "hspice_native_ibis")
    model = load_flow(case.case_id, PAIR_MODEL)
    if native is None or model is None:
        raise FileNotFoundError(case.case_id)
    hold = native_kd_hold_region(case, native)
    x0, x1 = zoom_window(case, native)

    fig, axes = plt.subplots(3, 1, figsize=(13.5, 9.5), sharex=True)
    for flow, data in (("hspice_native_ibis", native), (PAIR_MODEL, model)):
        for ax, signal in zip(
            axes,
            (coeff_signal(data, "ku"), coeff_signal(data, "kd"), pad_signal(data, flow)),
        ):
            if signal is not None:
                plot_wave(ax, data, signal, flow)

    style_axes(axes, case, x0, x1, hold)
    axes[0].set_ylabel("Ku")
    axes[1].set_ylabel("Kd")
    axes[2].set_ylabel("Pad voltage (V)")
    axes[2].set_xlabel("Time (ns)")
    axes[1].axhline(0.0, color="#555555", lw=1.0, alpha=0.75)
    add_figure_legend(fig, axes, ncol=2)
    fig.suptitle(f"{case.case_id}: directional + residual vs HSPICE native IBIS", y=0.999, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.925))

    out_dir = PLOTS_DIR / "directional_residual_vs_native_ibis"
    ensure_dir(out_dir)
    out = out_dir / f"{case.case_id}_directional_residual_vs_native_ibis.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def plot_directional_residual_vs_transistor(case: base.StudyCase) -> Path:
    native = load_flow(case.case_id, "hspice_native_ibis")
    transistor = load_flow(case.case_id, "hspice_transistor_sp")
    model = load_flow(case.case_id, PAIR_MODEL)
    if native is None or transistor is None or model is None:
        raise FileNotFoundError(case.case_id)
    x0, x1 = zoom_window(case, native)
    transistor_pad = pad_signal(transistor, "hspice_transistor_sp")
    model_pad = pad_signal(model, PAIR_MODEL)
    if transistor_pad is None or model_pad is None:
        raise KeyError(f"pad missing for {case.case_id}")

    fig, ax = plt.subplots(1, 1, figsize=(13.5, 5.4))
    plot_wave(ax, transistor, transistor_pad, "hspice_transistor_sp")
    plot_wave(ax, model, model_pad, PAIR_MODEL)
    style_axes([ax], case, x0, x1)
    ax.axhline(0.0, color="#888888", lw=0.8, alpha=0.5)
    ax.set_ylabel("Pad voltage (V)")
    ax.set_xlabel("Time (ns)")
    add_figure_legend(fig, [ax], ncol=2, bbox_y=0.91)
    fig.suptitle(f"{case.case_id}: directional + residual vs HSPICE transistor io_buf.sp", y=0.995, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.82))

    out_dir = PLOTS_DIR / "directional_residual_vs_hspice_sp"
    ensure_dir(out_dir)
    out = out_dir / f"{case.case_id}_directional_residual_vs_hspice_sp.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def interp_on_grid(data: dict[str, np.ndarray], y: np.ndarray | None, grid: np.ndarray) -> np.ndarray:
    if y is None:
        return np.full_like(grid, np.nan, dtype=float)
    t = t_ns(data)
    mask = np.isfinite(t) & np.isfinite(y)
    if int(np.sum(mask)) < 2:
        return np.full_like(grid, np.nan, dtype=float)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(y[mask], dtype=float)
    order = np.argsort(tt)
    tt = tt[order]
    yy = yy[order]
    return np.interp(grid, tt, yy, left=np.nan, right=np.nan)


def export_raw_flow(case: base.StudyCase, flow: str, data: dict[str, np.ndarray]) -> Path:
    out = DATA_DIR / "raw" / case.case_id / f"{flow}_signals.csv"
    t = t_ns(data)
    ku = coeff_signal(data, "ku")
    kd = coeff_signal(data, "kd")
    pad = pad_signal(data, flow)
    input_v = base.input_waveform(case, t)
    rows: list[dict[str, object]] = []
    n = len(t)
    for i in range(n):
        row: dict[str, object] = {
            "time_ns": float(t[i]),
            "input_v": float(input_v[i]) if i < len(input_v) else "",
        }
        if ku is not None and i < len(ku):
            row["ku"] = float(ku[i])
        if kd is not None and i < len(kd):
            row["kd"] = float(kd[i])
        if pad is not None and i < len(pad):
            row["pad_v"] = float(pad[i])
        rows.append(row)
    write_csv(out, rows)
    return out


def export_case_numeric(case: base.StudyCase) -> tuple[Path, list[Path], Path]:
    flows = PANEL_FLOWS + PAD_EXTRA_FLOWS
    loaded = {flow: load_flow(case.case_id, flow) for flow in flows}
    native = loaded["hspice_native_ibis"]
    if native is None:
        raise FileNotFoundError(case.case_id)
    hold = native_kd_hold_region(case, native)
    x0, x1 = zoom_window(case, native)
    step_ns = 0.001
    grid = np.arange(x0, x1 + 0.5 * step_ns, step_ns)

    columns: dict[str, np.ndarray] = {
        "time_ns": grid,
        "input_v": base.input_waveform(case, grid),
    }
    for edge_i, (edge_time, _) in enumerate(relevant_edges(case), start=1):
        columns[f"edge_{edge_i}_time_ns"] = np.full_like(grid, edge_time, dtype=float)
    if hold is not None:
        columns["native_kd_hold_start_ns"] = np.full_like(grid, hold[0], dtype=float)
        columns["native_kd_hold_end_ns"] = np.full_like(grid, hold[1], dtype=float)
        columns["in_native_kd_hold_region"] = ((grid >= hold[0]) & (grid <= hold[1])).astype(float)
    else:
        columns["native_kd_hold_start_ns"] = np.full_like(grid, np.nan, dtype=float)
        columns["native_kd_hold_end_ns"] = np.full_like(grid, np.nan, dtype=float)
        columns["in_native_kd_hold_region"] = np.zeros_like(grid, dtype=float)

    raw_paths: list[Path] = []
    for flow, data in loaded.items():
        if data is None:
            continue
        raw_paths.append(export_raw_flow(case, flow, data))
        ku = coeff_signal(data, "ku")
        kd = coeff_signal(data, "kd")
        pad = pad_signal(data, flow)
        if flow != "hspice_transistor_sp":
            columns[f"{flow}__ku"] = interp_on_grid(data, ku, grid)
            columns[f"{flow}__kd"] = interp_on_grid(data, kd, grid)
        columns[f"{flow}__pad_v"] = interp_on_grid(data, pad, grid)

    rows: list[dict[str, object]] = []
    keys = list(columns.keys())
    for i in range(len(grid)):
        rows.append({key: float(columns[key][i]) for key in keys})
    aligned_path = DATA_DIR / f"{case.case_id}_aligned_1ps.csv"
    write_csv(aligned_path, rows)

    meta_rows: list[dict[str, object]] = []
    for flow in flows:
        data = loaded.get(flow)
        meta_rows.append(
            {
                "case_id": case.case_id,
                "flow": flow,
                "label": FLOW_LABELS[flow],
                "color": FLOW_COLORS[flow],
                "included_in_ku_kd_panels": flow != "hspice_transistor_sp",
                "included_in_pad_panel": True,
                "data_available": data is not None,
            }
        )
    meta_rows.extend(
        {
            "case_id": case.case_id,
            "flow": f"edge_{i}",
            "label": label,
            "color": "#444444",
            "included_in_ku_kd_panels": True,
            "included_in_pad_panel": True,
            "data_available": True,
            "time_ns": edge_time,
        }
        for i, (edge_time, label) in enumerate(relevant_edges(case), start=1)
    )
    if hold is not None:
        meta_rows.append(
            {
                "case_id": case.case_id,
                "flow": "native_kd_hold_region",
                "label": "native-IBIS Kd hold region",
                "color": "#f2c14e",
                "included_in_ku_kd_panels": True,
                "included_in_pad_panel": True,
                "data_available": True,
                "start_ns": hold[0],
                "end_ns": hold[1],
            }
        )
    meta_path = DATA_DIR / f"{case.case_id}_metadata.csv"
    write_csv(meta_path, meta_rows)
    return aligned_path, raw_paths, meta_path


def export_evolution_numeric(case: base.StudyCase) -> tuple[Path, list[Path], Path]:
    flows = ["hspice_native_ibis"] + EVOLUTION_FLOWS
    loaded = {flow: load_flow(case.case_id, flow) for flow in flows}
    native = loaded["hspice_native_ibis"]
    if native is None:
        raise FileNotFoundError(case.case_id)
    hold = native_kd_hold_region(case, native)
    x0, x1 = zoom_window(case, native)
    step_ns = 0.001
    grid = np.arange(x0, x1 + 0.5 * step_ns, step_ns)
    columns: dict[str, np.ndarray] = {
        "time_ns": grid,
        "input_v": base.input_waveform(case, grid),
    }
    if hold is not None:
        columns["native_kd_hold_start_ns"] = np.full_like(grid, hold[0], dtype=float)
        columns["native_kd_hold_end_ns"] = np.full_like(grid, hold[1], dtype=float)
        columns["in_native_kd_hold_region"] = ((grid >= hold[0]) & (grid <= hold[1])).astype(float)
    raw_paths: list[Path] = []
    for flow, data in loaded.items():
        if data is None:
            continue
        raw_paths.append(export_raw_flow(case, flow, data))
        columns[f"{flow}__kd"] = interp_on_grid(data, coeff_signal(data, "kd"), grid)
    rows = [{key: float(columns[key][i]) for key in columns} for i in range(len(grid))]
    aligned_path = DATA_DIR / "short_pulse_1ns_high_kd_evolution_aligned_1ps.csv"
    write_csv(aligned_path, rows)
    meta_rows = [
        {
            "case_id": case.case_id,
            "flow": flow,
            "label": FLOW_LABELS[flow],
            "color": FLOW_COLORS[flow],
            "data_available": loaded.get(flow) is not None,
            "panel_order": i,
        }
        for i, flow in enumerate(flows)
    ]
    meta_path = DATA_DIR / "short_pulse_1ns_high_kd_evolution_metadata.csv"
    write_csv(meta_path, meta_rows)
    return aligned_path, raw_paths, meta_path


def plot_evolution(case: base.StudyCase) -> Path:
    native = load_flow(case.case_id, "hspice_native_ibis")
    if native is None:
        raise FileNotFoundError(case.case_id)
    hold = native_kd_hold_region(case, native)
    x0, x1 = zoom_window(case, native)
    native_kd = coeff_signal(native, "kd")
    if native_kd is None:
        raise KeyError("native Kd missing")

    fig, axes = plt.subplots(len(EVOLUTION_FLOWS), 1, figsize=(12.0, 12.2), sharex=True)
    for ax, flow in zip(axes, EVOLUTION_FLOWS):
        data = load_flow(case.case_id, flow)
        shade_hold_region(ax, hold)
        ax.plot(t_ns(native), native_kd, color=FLOW_COLORS["hspice_native_ibis"], lw=2.2, label="native IBIS")
        if data is not None:
            kd = coeff_signal(data, "kd")
            if kd is not None:
                ax.plot(t_ns(data), kd, color=FLOW_COLORS[flow], lw=1.9, label=FLOW_LABELS[flow])
        ax.axhline(0.0, color="#555555", lw=0.8, alpha=0.7)
        mark_edges(ax, case)
        ax.set_xlim(x0, x1)
        ax.set_ylabel("Kd")
        ax.grid(True, alpha=0.22)
        ax.legend(loc="upper right", fontsize=8)
    axes[-1].set_xlabel("Time (ns)")
    fig.suptitle("short_pulse_1ns_high: Kd evolution by model generation", fontsize=15, y=0.998)
    fig.tight_layout(rect=(0, 0, 1, 0.978))
    out = PLOTS_DIR / "short_pulse_1ns_high_kd_evolution.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def make_contact_sheet(paths: list[Path]) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(18.0, 13.5))
    for ax, path in zip(axes.ravel(), paths):
        img = mpimg.imread(path)
        ax.imshow(img)
        ax.set_title(path.stem.replace("_waveform_evidence", ""), fontsize=14)
        ax.axis("off")
    for ax in axes.ravel()[len(paths) :]:
        ax.axis("off")
    fig.suptitle("io_buf waveform evidence: cached HSPICE/ngspice overlays", fontsize=18)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    out = PLOTS_DIR / "waveform_evidence_contact_sheet.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def make_group_contact_sheet(paths: list[Path], output_name: str, title: str) -> Path:
    cols = 2
    rows = int(math.ceil(len(paths) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(18.0, 6.8 * rows), squeeze=False)
    for ax, path in zip(axes.ravel(), paths):
        ax.imshow(mpimg.imread(path))
        ax.set_title(path.stem, fontsize=12)
        ax.axis("off")
    for ax in axes.ravel()[len(paths) :]:
        ax.axis("off")
    fig.suptitle(title, fontsize=18)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    out = PLOTS_DIR / output_name
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def write_report(
    case_paths: list[Path],
    contact: Path,
    evolution: Path,
    data_paths: list[Path],
    short_paths: list[Path],
    short_contact: Path,
    native_pair_paths: list[Path],
    native_pair_contact: Path,
    transistor_pair_paths: list[Path],
    transistor_pair_contact: Path,
) -> None:
    lines = [
        "# io_buf Waveform Evidence Report",
        "",
        "Cached data only. No HSPICE or ngspice simulations were rerun for this deliverable.",
        "",
        "Color key is fixed across all figures: HSPICE native IBIS is thick black, HSPICE transistor `io_buf.sp` is thick gray on pad panels only, legacy pybis is orange, value-match v2 is purple, directional+residual is red, and recover-mean is green.",
        "Sparse, staggered markers identify ngspice traces even where curves overlap; the continuous line color remains the primary flow key.",
        "",
        "## Figures And Captions",
        "",
    ]
    for path in case_paths:
        case_id = path.name.replace("_waveform_evidence.png", "")
        lines.append(f"### `{path.relative_to(OUT_DIR)}`")
        for item in case_caption(case_id):
            lines.append(f"- {item}")
        lines.append("")
    lines.append(f"### `{contact.relative_to(OUT_DIR)}`")
    for item in [
        "The contact sheet is a navigation aid for all four required waveform evidence cases.",
        "Read rows from top to bottom inside each case: Ku, Kd, then pad voltage.",
        "Use color consistency to track how each model behaves across directions and pulse widths.",
        "Short-high shaded regions identify the native-IBIS Kd hold region visually.",
        "For detailed inspection, open the individual full-size PNGs rather than this compressed sheet.",
    ]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append(f"### `{evolution.relative_to(OUT_DIR)}`")
    for item in evolution_caption():
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Cleaner Comparison Sets")
    lines.append("")
    lines.append("### Short pulses without legacy pybis")
    lines.append("")
    lines.append("These figures remove the grossly incorrect legacy replay so differences among the newer methods and native IBIS remain visible.")
    for path in short_paths:
        lines.append(f"- `{path.relative_to(OUT_DIR)}`")
    lines.append(f"- `{short_contact.relative_to(OUT_DIR)}`")
    lines.append("")
    lines.append("### Directional + residual vs HSPICE native IBIS")
    lines.append("")
    lines.append("These pairwise figures show Ku, Kd, and pad together. Native IBIS is the only HSPICE reference that exposes Ku/Kd.")
    for path in native_pair_paths:
        lines.append(f"- `{path.relative_to(OUT_DIR)}`")
    lines.append(f"- `{native_pair_contact.relative_to(OUT_DIR)}`")
    lines.append("")
    lines.append("### Directional + residual vs HSPICE transistor io_buf.sp")
    lines.append("")
    lines.append("These pairwise figures compare pad voltage only because the transistor-level deck does not expose IBIS Ku/Kd coefficients.")
    for path in transistor_pair_paths:
        lines.append(f"- `{path.relative_to(OUT_DIR)}`")
    lines.append(f"- `{transistor_pair_contact.relative_to(OUT_DIR)}`")
    lines.append("")
    lines.append("## Numeric Data")
    lines.append("")
    lines.append("- `data/<case>_aligned_1ps.csv`: one shared 1 ps time axis matching the plotted zoom window, with `Ku`, `Kd`, and pad columns by flow.")
    lines.append("- `data/<case>_metadata.csv`: edge times, shaded native-Kd hold interval, labels, and colors used in the figures.")
    lines.append("- `data/raw/<case>/<flow>_signals.csv`: original cached time samples for the plotted signals before interpolation.")
    lines.append("- `data/short_pulse_1ns_high_kd_evolution_aligned_1ps.csv`: numeric source for the Kd evolution figure.")
    lines.append("")
    for path in data_paths:
        lines.append(f"- `{path.relative_to(OUT_DIR)}`")
    lines.append("")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="ascii")


def main() -> None:
    ensure_dir(PLOTS_DIR)
    ensure_dir(DATA_DIR)
    case_map = {case.case_id: case for case in base.build_cases(include_low=True)}
    case_paths = [plot_case(case_map[case_id]) for case_id in CASE_IDS]
    contact = make_contact_sheet(case_paths)
    evolution = plot_evolution(case_map["short_pulse_1ns_high"])
    short_case_ids = [case_id for case_id in CASE_IDS if case_map[case_id].pattern.startswith("short_")]
    short_paths = [plot_short_pulse_without_legacy(case_map[case_id]) for case_id in short_case_ids]
    short_contact = make_group_contact_sheet(
        short_paths,
        "short_pulse_no_legacy_contact_sheet.png",
        "Short-pulse model development: native IBIS and new methods only",
    )
    native_pair_paths = [plot_directional_residual_vs_native(case_map[case_id]) for case_id in CASE_IDS]
    native_pair_contact = make_group_contact_sheet(
        native_pair_paths,
        "directional_residual_vs_native_ibis_contact_sheet.png",
        "Directional + residual vs HSPICE native IBIS",
    )
    transistor_pair_paths = [plot_directional_residual_vs_transistor(case_map[case_id]) for case_id in CASE_IDS]
    transistor_pair_contact = make_group_contact_sheet(
        transistor_pair_paths,
        "directional_residual_vs_hspice_sp_contact_sheet.png",
        "Directional + residual vs HSPICE transistor io_buf.sp",
    )
    data_paths: list[Path] = []
    for case_id in CASE_IDS:
        aligned, _, meta = export_case_numeric(case_map[case_id])
        data_paths.extend([aligned, meta])
    evo_aligned, _, evo_meta = export_evolution_numeric(case_map["short_pulse_1ns_high"])
    data_paths.extend([evo_aligned, evo_meta])
    write_report(
        case_paths,
        contact,
        evolution,
        data_paths,
        short_paths,
        short_contact,
        native_pair_paths,
        native_pair_contact,
        transistor_pair_paths,
        transistor_pair_contact,
    )
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
