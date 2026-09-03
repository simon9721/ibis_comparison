"""Generate Ku/Kd review plots for the normal and stressed pybis cases.

The accepted review RAW for ngspice pybis did not save the internal Ku/Kd
nodes, so this script reruns only the two ngspice pybis decks with those nodes
enabled.  Xyce already saved Ku/Kd/NX in the review CSVs.
"""

from __future__ import annotations

import csv
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from eye_diagram import load_waveform, resolve_signal_key, sanitize_waveform


ROOT = Path(__file__).resolve().parent.parent
NGSPICE = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")
REVIEW_DIR = ROOT / "results" / "transient_review_plots_2026-05-13"
NORMAL_DIR = REVIEW_DIR / "normal_prbs_channel"
STRESSED_DIR = REVIEW_DIR / "stressed_edge50_prbs80_channel"


@dataclass(frozen=True)
class Flow:
    label: str
    path: Path
    fmt: str
    n10b_signal: str
    ku_signal: str
    kd_signal: str
    pad_signal: str
    tx_signal: str
    nx_signal: str
    input_signal: str


@dataclass(frozen=True)
class CaseConfig:
    name: str
    title: str
    out_dir: Path
    full_window_ns: tuple[float, float]
    zoom_window_ns: tuple[float, float]
    marker_ns: float | None
    marker_label: str
    min_t_end_ns: float
    ngspice_source_deck: Path
    ngspice_review_deck: Path
    ngspice_review_raw: Path
    xyce_csv: Path
    include_replacements: dict[str, Path]


def posix(path: Path) -> str:
    return path.resolve().as_posix()


def replace_include(text: str, include_target: str, absolute_path: Path) -> str:
    pattern = re.compile(rf"(?im)^(\.include\s+)['\"]?{re.escape(include_target)}['\"]?\s*$")
    replacement = rf"\1'{posix(absolute_path)}'"
    text, count = pattern.subn(replacement, text)
    if count != 1:
        raise RuntimeError(f"Expected one include for {include_target!r}, replaced {count}")
    return text


def add_kukd_save(text: str) -> str:
    save_line = ".save V(in_dig) V(pad) V(tx_out) V(n10b) V(xdrv.ku) V(xdrv.kd) V(xdrv.nx)"
    text, count = re.subn(r"(?im)^\.save\s+.*$", save_line, text, count=1)
    if count != 1:
        raise RuntimeError("Expected one .save line")
    return text


def prepare_ngspice_deck(case: CaseConfig) -> None:
    text = case.ngspice_source_deck.read_text(encoding="utf-8")
    for include_target, absolute_path in case.include_replacements.items():
        text = replace_include(text, include_target, absolute_path)
    text = add_kukd_save(text)
    if case.name == "normal_prbs_channel":
        text, count = re.subn(r"(?im)^\.tran\s+10p\s+1000n\s*$", ".tran 10p 80n", text)
        if count != 1:
            raise RuntimeError("Expected one normal-case .tran line for the Ku/Kd diagnostic window")
    case.ngspice_review_deck.parent.mkdir(parents=True, exist_ok=True)
    case.ngspice_review_deck.write_text(text, encoding="ascii")


def ngspice_raw_has_kukd(case: CaseConfig) -> bool:
    path = case.ngspice_review_raw
    if not path.exists():
        return False
    try:
        data = load_waveform(path, fmt="ngspice")
        resolve_signal_key(data, "v(xdrv.ku)")
        resolve_signal_key(data, "v(xdrv.kd)")
        if float(data["time"][-1] * 1e9) < case.min_t_end_ns:
            return False
        return True
    except Exception:
        return False


def run_ngspice_if_needed(case: CaseConfig) -> None:
    if ngspice_raw_has_kukd(case):
        return
    if not NGSPICE.exists():
        raise FileNotFoundError(NGSPICE)
    prepare_ngspice_deck(case)
    case.ngspice_review_raw.unlink(missing_ok=True)
    log_path = case.ngspice_review_raw.with_suffix(".log")
    try:
        proc = subprocess.run(
            [str(NGSPICE), "-b", "-r", case.ngspice_review_raw.name, case.ngspice_review_deck.name],
            cwd=case.ngspice_review_deck.parent,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(
            "COMMAND: "
            + " ".join(
                [str(NGSPICE), "-b", "-r", case.ngspice_review_raw.name, case.ngspice_review_deck.name]
            )
            + "\n\nRETURN_CODE: TIMEOUT\n\n"
            + f"STDOUT:\n{exc.stdout or ''}\n\nSTDERR:\n{exc.stderr or ''}",
            encoding="utf-8",
        )
        case.ngspice_review_raw.unlink(missing_ok=True)
        raise RuntimeError(f"ngspice timed out for {case.name}; see {log_path}") from exc
    log_path.write_text(
        "COMMAND: "
        + " ".join([str(NGSPICE), "-b", "-r", case.ngspice_review_raw.name, case.ngspice_review_deck.name])
        + "\n\n"
        + f"RETURN_CODE: {proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}",
        encoding="utf-8",
    )
    if proc.returncode != 0 or not case.ngspice_review_raw.exists():
        raise RuntimeError(f"ngspice failed for {case.name}; see {log_path}")


def load_flow(flow: Flow) -> dict[str, np.ndarray]:
    data = load_waveform(flow.path, fmt=flow.fmt)
    out: dict[str, np.ndarray] = {}
    time = data["time"]
    for name, requested in [
        ("n10b", flow.n10b_signal),
        ("ku", flow.ku_signal),
        ("kd", flow.kd_signal),
        ("pad", flow.pad_signal),
        ("tx", flow.tx_signal),
        ("nx", flow.nx_signal),
        ("in", flow.input_signal),
    ]:
        key = resolve_signal_key(data, requested)
        t, y = sanitize_waveform(time, data[key])
        if "time" not in out:
            out["time"] = t
        out[name] = y
    out["rx"] = out["n10b"]
    return out


def clip(t_ns: np.ndarray, y: np.ndarray, window: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    mask = (t_ns >= window[0]) & (t_ns <= window[1])
    return t_ns[mask], y[mask]


def envelope_decimate(t: np.ndarray, y: np.ndarray, max_points: int = 7000) -> tuple[np.ndarray, np.ndarray]:
    if len(t) <= max_points:
        return t, y
    bins = max(2, max_points // 2)
    edges = np.linspace(0, len(t), bins + 1, dtype=int)
    keep: list[int] = [0, len(t) - 1]
    for start, end in zip(edges[:-1], edges[1:]):
        if end <= start:
            continue
        seg = y[start:end]
        keep.append(start + int(np.argmin(seg)))
        keep.append(start + int(np.argmax(seg)))
    idx = np.array(sorted(set(keep)), dtype=int)
    return t[idx], y[idx]


def add_marker(ax: plt.Axes, marker_ns: float | None, label: str) -> None:
    if marker_ns is None:
        return
    xmin, xmax = ax.get_xlim()
    if xmin <= marker_ns <= xmax:
        ax.axvline(marker_ns, color="0.2", linestyle=":", linewidth=1.0)
        ax.text(
            marker_ns,
            0.98,
            label,
            transform=ax.get_xaxis_transform(),
            rotation=90,
            va="top",
            ha="right",
            fontsize=8,
        )


def style_axis(ax: plt.Axes, xlabel: bool = False) -> None:
    ax.grid(True, alpha=0.25)
    if xlabel:
        ax.set_xlabel("Time (ns)")


def plot_individual(case: CaseConfig, flow: Flow, data: dict[str, np.ndarray], out_path: Path) -> None:
    t_ns = data["time"] * 1e9
    windows = [case.full_window_ns, case.zoom_window_ns]
    window_names = ["full transient", "diagnostic zoom"]

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 7.8), sharex=False)
    for col, (window, name) in enumerate(zip(windows, window_names)):
        ax_v = axes[0, col]
        ax_k = axes[1, col]
        tx, vx = clip(t_ns, data["n10b"], window)
        tx, vx = envelope_decimate(tx, vx)
        ax_v.plot(tx, vx, color="#1f77b4", linewidth=1.25, label="V(n10b)")
        ax_v.set_title(f"{flow.label} - {name}")
        ax_v.set_ylabel("V(n10b) (V)")
        ax_v.legend(loc="best", fontsize=8)
        ax_v.set_xlim(*window)
        style_axis(ax_v)
        add_marker(ax_v, case.marker_ns, case.marker_label)

        for y, color, label in [
            (data["ku"], "#0072B2", "Ku"),
            (data["kd"], "#D55E00", "Kd"),
        ]:
            tk, yk = clip(t_ns, y, window)
            tk, yk = envelope_decimate(tk, yk)
            ax_k.plot(tk, yk, color=color, linewidth=1.35, label=label)
        ax_k.set_ylabel("Coefficient")
        ax_k.set_xlim(*window)
        ax_k.legend(loc="best", fontsize=8)
        style_axis(ax_k, xlabel=True)
        add_marker(ax_k, case.marker_ns, case.marker_label)

    fig.suptitle(f"{case.title}: pybis Ku/Kd Diagnostic", fontsize=14)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_overlay(
    case: CaseConfig,
    ng_data: dict[str, np.ndarray],
    xy_data: dict[str, np.ndarray],
    out_path: Path,
) -> None:
    windows = [case.full_window_ns, case.zoom_window_ns]
    window_names = ["full transient", "diagnostic zoom"]
    series = [
        ("n10b", "V(n10b) (V)", "V(n10b)"),
        ("ku", "Ku", "Ku"),
        ("kd", "Kd", "Kd"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(13.5, 10.2), sharex=False)
    for col, (window, name) in enumerate(zip(windows, window_names)):
        for row, (key, ylabel, title) in enumerate(series):
            ax = axes[row, col]
            for data, color, label, linestyle in [
                (ng_data, "#0072B2", "ngspice pybis", "-"),
                (xy_data, "#D55E00", "Xyce pybis", "--"),
            ]:
                t_ns = data["time"] * 1e9
                tx, yx = clip(t_ns, data[key], window)
                tx, yx = envelope_decimate(tx, yx)
                ax.plot(tx, yx, color=color, linestyle=linestyle, linewidth=1.25, label=label)
            ax.set_xlim(*window)
            ax.set_ylabel(ylabel)
            if row == 0:
                ax.set_title(f"{title} - {name}")
            if row == 2:
                style_axis(ax, xlabel=True)
            else:
                style_axis(ax)
            ax.legend(loc="best", fontsize=8)
            add_marker(ax, case.marker_ns, case.marker_label)
    fig.suptitle(f"{case.title}: ngspice vs Xyce pybis Ku/Kd", fontsize=14)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def summarize(case: CaseConfig, label: str, data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    rows = []
    t_ns = data["time"] * 1e9
    for name, window in [("full", case.full_window_ns), ("zoom", case.zoom_window_ns)]:
        row: dict[str, object] = {
            "case": case.name,
            "flow": label,
            "window": name,
            "t_start_ns": window[0],
            "t_end_ns": window[1],
        }
        mask = (t_ns >= window[0]) & (t_ns <= window[1])
        for key in ["n10b", "ku", "kd"]:
            y = data[key][mask]
            row[f"{key}_min"] = float(np.min(y))
            row[f"{key}_max"] = float(np.max(y))
            row[f"{key}_mean"] = float(np.mean(y))
        rows.append(row)
    return rows


def write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_signals(path: Path, fmt: str, signals: dict[str, str]) -> dict[str, np.ndarray]:
    data = load_waveform(path, fmt=fmt)
    out: dict[str, np.ndarray] = {}
    for name, requested in signals.items():
        key = resolve_signal_key(data, requested)
        t, y = sanitize_waveform(data["time"], data[key])
        out["time"] = t
        out[name] = y
    return out


def value_at_ns(data: dict[str, np.ndarray], key: str, t_ns: float) -> float:
    return float(np.interp(t_ns, data["time"] * 1e9, data[key]))


def extrema_in_window(
    data: dict[str, np.ndarray],
    key: str,
    window_ns: tuple[float, float],
    mode: str,
) -> tuple[float, float]:
    t_ns = data["time"] * 1e9
    mask = (t_ns >= window_ns[0]) & (t_ns <= window_ns[1])
    if not np.any(mask):
        return math.nan, math.nan
    tw = t_ns[mask]
    yw = data[key][mask]
    idx = int(np.argmax(yw) if mode == "max" else np.argmin(yw))
    return float(tw[idx]), float(yw[idx])


def first_crossing_ns(
    data: dict[str, np.ndarray],
    key: str,
    window_ns: tuple[float, float],
    level: float,
    direction: str,
) -> float:
    t_ns = data["time"] * 1e9
    mask = (t_ns >= window_ns[0]) & (t_ns <= window_ns[1])
    tw = t_ns[mask]
    yw = data[key][mask]
    if direction == "rise":
        idx = np.where(yw >= level)[0]
    else:
        idx = np.where(yw <= level)[0]
    if len(idx) == 0:
        return math.nan
    return float(tw[int(idx[0])])


def crossing_time_ns(
    data: dict[str, np.ndarray],
    key: str,
    window_ns: tuple[float, float],
    level: float,
    direction: str,
) -> float:
    t_ns = data["time"] * 1e9
    mask = (t_ns >= window_ns[0]) & (t_ns <= window_ns[1])
    tw = t_ns[mask]
    yw = data[key][mask]
    if len(tw) < 2:
        return math.nan
    if direction == "rise":
        idx = np.where((yw[:-1] < level) & (yw[1:] >= level))[0]
    else:
        idx = np.where((yw[:-1] > level) & (yw[1:] <= level))[0]
    if len(idx) == 0:
        return math.nan
    i = int(idx[0])
    if yw[i + 1] == yw[i]:
        return float(tw[i])
    frac = (level - yw[i]) / (yw[i + 1] - yw[i])
    return float(tw[i] + frac * (tw[i + 1] - tw[i]))


def sustained_crossing_time_ns(
    data: dict[str, np.ndarray],
    key: str,
    window_ns: tuple[float, float],
    level: float,
    direction: str,
    min_duration_ns: float = 0.10,
) -> float:
    t_ns = data["time"] * 1e9
    mask = (t_ns >= window_ns[0]) & (t_ns <= window_ns[1])
    tw = t_ns[mask]
    yw = data[key][mask]
    if len(tw) < 2:
        return math.nan
    if direction == "rise":
        idx = np.where((yw[:-1] < level) & (yw[1:] >= level))[0]
        good = yw >= level
    else:
        idx = np.where((yw[:-1] > level) & (yw[1:] <= level))[0]
        good = yw <= level
    for raw_i in idx:
        i = int(raw_i)
        if yw[i + 1] == yw[i]:
            cross_t = float(tw[i])
        else:
            frac = (level - yw[i]) / (yw[i + 1] - yw[i])
            cross_t = float(tw[i] + frac * (tw[i + 1] - tw[i]))
        end_t = cross_t + min_duration_ns
        j_end = int(np.searchsorted(tw, end_t, side="left"))
        if j_end >= len(tw):
            return cross_t
        if np.all(good[i + 1 : j_end + 1]):
            return cross_t
    return math.nan


def input_transition_edges(
    data: dict[str, np.ndarray],
    window_ns: tuple[float, float],
    level: float = 1.65,
    min_separation_ns: float = 0.2,
) -> list[dict[str, object]]:
    t_ns = data["time"] * 1e9
    y = data["in"]
    rows: list[dict[str, object]] = []
    idx = np.where(
        ((y[:-1] < level) & (y[1:] >= level))
        | ((y[:-1] > level) & (y[1:] <= level))
    )[0]
    for i in idx:
        if y[i + 1] == y[i]:
            continue
        tc = float(t_ns[i] + (level - y[i]) * (t_ns[i + 1] - t_ns[i]) / (y[i + 1] - y[i]))
        if tc < window_ns[0] or tc > window_ns[1]:
            continue
        if rows and abs(tc - float(rows[-1]["input_50pct_ns"])) < min_separation_ns:
            continue
        rows.append(
            {
                "edge": f"E{len(rows) + 1}",
                "direction": "rise" if y[i + 1] > y[i] else "fall",
                "input_50pct_ns": tc,
            }
        )
    return rows


def plot_normal_source_edge_history(
    case: CaseConfig,
    ng_data: dict[str, np.ndarray],
    xy_data: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    if case.name != "normal_prbs_channel":
        return []

    ref_ng = load_signals(
        ROOT / "ngspice_refspice" / "tb_refspice_prbs7_new50ohm_batch.raw",
        "ngspice",
        {"in": "v(in_dig)", "pad": "v(pad_ref)", "tx": "v(tx_out)", "rx": "v(n10b)"},
    )
    ref_xy = load_signals(
        ROOT / "xyce_refspice" / "tb_refspice_prbs7_new50ohm_xyce.cir.csv",
        "xyce",
        {"in": "v(in_dig)", "pad": "v(pad_ref)", "tx": "v(tx_out)", "rx": "v(n10b)"},
    )

    edge_rows: list[dict[str, object]] = []
    edge_specs = input_transition_edges(xy_data, (33.0, 76.0))
    for i, spec in enumerate(edge_specs):
        input_t = float(spec["input_50pct_ns"])
        next_input_t = (
            float(edge_specs[i + 1]["input_50pct_ns"])
            if i + 1 < len(edge_specs)
            else input_t + 8.0
        )
        direction = str(spec["direction"])
        coeff_key = "ku" if direction == "rise" else "kd"
        tx_mode = "max" if direction == "rise" else "min"
        coeff_window = (input_t - 0.05, min(input_t + 8.0, next_input_t - 0.02))
        resp_window = (input_t, min(input_t + 8.0, next_input_t - 0.02))
        if coeff_window[1] <= coeff_window[0]:
            coeff_window = (input_t - 0.05, input_t + 8.0)
            resp_window = (input_t, input_t + 8.0)

        coeff_xy_t = sustained_crossing_time_ns(xy_data, coeff_key, coeff_window, 0.9, "rise")
        coeff_ng_t = sustained_crossing_time_ns(ng_data, coeff_key, coeff_window, 0.9, "rise")
        py_xy_t, py_xy_v = extrema_in_window(xy_data, "tx", resp_window, tx_mode)
        py_ng_t, py_ng_v = extrema_in_window(ng_data, "tx", resp_window, tx_mode)
        ref_xy_t, ref_xy_v = extrema_in_window(ref_xy, "tx", resp_window, tx_mode)
        ref_ng_t, ref_ng_v = extrema_in_window(ref_ng, "tx", resp_window, tx_mode)
        edge_rows.append(
            {
                "edge": spec["edge"],
                "direction": direction,
                "input_50pct_ns": input_t,
                "expected_source_coefficient": coeff_key,
                "xyce_coeff_cross_0p9_ns": coeff_xy_t,
                "ngspice_coeff_cross_0p9_ns": coeff_ng_t,
                "xyce_pybis_tx_extreme_ns": py_xy_t,
                "xyce_pybis_tx_extreme_v": py_xy_v,
                "ngspice_pybis_tx_extreme_ns": py_ng_t,
                "ngspice_pybis_tx_extreme_v": py_ng_v,
                "xyce_refspice_tx_extreme_ns": ref_xy_t,
                "xyce_refspice_tx_extreme_v": ref_xy_v,
                "ngspice_refspice_tx_extreme_ns": ref_ng_t,
                "ngspice_refspice_tx_extreme_v": ref_ng_v,
            }
        )

    map_window = (33.0, 77.0)
    colors = ["#0072B2", "#CC3311", "#009E73", "#7A3E9D"]
    fig, axes = plt.subplots(
        4,
        1,
        figsize=(14.0, 10.2),
        sharex=True,
        gridspec_kw={"height_ratios": [0.75, 1.0, 1.05, 1.05]},
    )

    ax = axes[0]
    t_ns = xy_data["time"] * 1e9
    tx, yx = clip(t_ns, xy_data["in"], map_window)
    tx, yx = envelope_decimate(tx, yx)
    ax.plot(tx, yx, color="0.25", linewidth=1.35, label="input")
    ax.set_ylabel("Input (V)")
    ax.set_ylim(-0.2, 3.5)
    ax.set_title("Normal source-side edge response map: input edge -> pybis Ku/Kd -> pybis/refspice tx_out")
    ax.legend(loc="upper right", fontsize=8)

    ax = axes[1]
    for data, suffix, style, alpha in [
        (xy_data, "Xyce", "-", 0.95),
        (ng_data, "ngspice", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        for key, color, label in [
            ("ku", "#0072B2", "Ku"),
            ("kd", "#D55E00", "Kd"),
        ]:
            tx, yx = clip(t_ns, data[key], map_window)
            tx, yx = envelope_decimate(tx, yx)
            ax.plot(tx, yx, color=color, linestyle=style, linewidth=1.65, alpha=alpha, label=f"{label} {suffix}")
    ax.set_ylabel("Ku/Kd")
    ax.set_ylim(-0.12, 1.12)
    ax.legend(loc="upper right", fontsize=8, ncol=4)

    ax = axes[2]
    for data, suffix, style, alpha in [
        (xy_data, "Xyce pybis", "-", 0.95),
        (ng_data, "ngspice pybis", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["tx"], map_window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(tx, yx, color="#7A3E9D", linestyle=style, linewidth=1.8, alpha=alpha, label=f"tx_out {suffix}")
    ax.set_ylabel("pybis tx_out (V)")
    ax.set_ylim(-0.25, 1.85)
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    ax = axes[3]
    for data, suffix, style, alpha in [
        (ref_xy, "Xyce refspice", "-", 0.95),
        (ref_ng, "ngspice refspice", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["tx"], map_window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(tx, yx, color="0.25", linestyle=style, linewidth=1.8, alpha=alpha, label=f"tx_out {suffix}")
    ax.set_ylabel("refspice tx_out (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_ylim(-0.25, 1.85)
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    for ax in axes:
        ax.set_xlim(*map_window)
        ax.grid(True, alpha=0.25)
        for row, color in zip(edge_rows, colors):
            input_t = float(row["input_50pct_ns"])
            coeff_t = float(row["xyce_coeff_cross_0p9_ns"])
            py_t = float(row["xyce_pybis_tx_extreme_ns"])
            ref_t = float(row["xyce_refspice_tx_extreme_ns"])
            ax.axvline(input_t, color=color, linestyle=":", linewidth=1.0, alpha=0.95)
            if not math.isnan(coeff_t):
                ax.axvline(coeff_t, color=color, linestyle="-.", linewidth=0.9, alpha=0.75)
            if ax is axes[2] and not math.isnan(py_t):
                ax.axvline(py_t, color=color, linestyle="--", linewidth=0.95, alpha=0.85)
            if ax is axes[3] and not math.isnan(ref_t):
                ax.axvline(ref_t, color=color, linestyle="--", linewidth=0.95, alpha=0.85)

    for row, color in zip(edge_rows, colors):
        input_t = float(row["input_50pct_ns"])
        coeff_t = float(row["xyce_coeff_cross_0p9_ns"])
        py_t = float(row["xyce_pybis_tx_extreme_ns"])
        ref_t = float(row["xyce_refspice_tx_extreme_ns"])
        coeff = str(row["expected_source_coefficient"]).upper()
        axes[0].text(input_t, 0.94, f"{row['edge']} input\n{input_t:.2f} ns", transform=axes[0].get_xaxis_transform(), rotation=90, va="top", ha="right", fontsize=8, color=color)
        if not math.isnan(coeff_t):
            axes[1].text(coeff_t, 0.94, f"{row['edge']} {coeff}\n{coeff_t:.2f} ns", transform=axes[1].get_xaxis_transform(), rotation=90, va="top", ha="right", fontsize=8, color=color)
        axes[2].text(py_t, 0.94, f"{row['edge']} pybis\n{py_t:.2f} ns", transform=axes[2].get_xaxis_transform(), rotation=90, va="top", ha="right", fontsize=8, color=color)
        axes[3].text(ref_t, 0.94, f"{row['edge']} ref\n{ref_t:.2f} ns", transform=axes[3].get_xaxis_transform(), rotation=90, va="top", ha="right", fontsize=8, color=color)

    axes[2].annotate(
        "normal pybis source response stays in the same voltage range as refspice",
        xy=(edge_rows[1]["xyce_pybis_tx_extreme_ns"], edge_rows[1]["xyce_pybis_tx_extreme_v"]),
        xytext=(52.0, 1.62),
        arrowprops={"arrowstyle": "->", "color": "0.2", "lw": 1.1},
        fontsize=9,
        color="0.15",
    )
    fig.tight_layout()
    fig.savefig(case.out_dir / "15_normal_source_edge_response_map.png", dpi=190)
    plt.close(fig)
    write_metrics(case.out_dir / "normal_source_edge_response_map_metrics.csv", edge_rows)
    return edge_rows


def plot_spike_leadin_history(case: CaseConfig, ng_data: dict[str, np.ndarray], xy_data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    if case.name != "stressed_edge50_prbs80_channel":
        return []

    ref_ng = load_signals(
        ROOT
        / "results"
        / "stressed_edge50_corrected_crossflow_2026-05-12_clean"
        / "runs"
        / "ui2_len30cm_loss5_coarse10"
        / "ngspice_refspice"
        / "ui2_len30cm_loss5_coarse10_ngspice_refspice.raw",
        "ngspice",
        {"in": "v(in_dig)", "pad": "v(pad_ref)", "tx": "v(tx_out)", "rx": "v(n10b)"},
    )
    ref_xy = load_signals(
        ROOT
        / "results"
        / "stressed_edge50_corrected_crossflow_2026-05-12_clean"
        / "runs"
        / "ui2_len30cm_loss5_coarse10"
        / "xyce_refspice"
        / "ui2_len30cm_loss5_coarse10_xyce_refspice.cir.csv",
        "xyce",
        {"in": "v(in_dig)", "pad": "v(pad_ref)", "tx": "v(tx_out)", "rx": "v(n10b)"},
    )

    window = (53.6, 58.9)
    markers = [
        (54.2, "fall cmd"),
        (54.24, "pybis pad launch"),
        (56.2, "rise cmd"),
        (56.69, "rx spike"),
    ]

    fig, axes = plt.subplots(5, 1, figsize=(13.5, 12.0), sharex=True)
    ax = axes[0]
    for data, color, label, style in [
        (ng_data, "#0072B2", "ngspice pybis pad", "-"),
        (xy_data, "#D55E00", "Xyce pybis pad", "--"),
        (ref_ng, "0.25", "ngspice refspice pad", "-."),
        (ref_xy, "0.55", "Xyce refspice pad", ":"),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["pad"], window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(tx, yx, color=color, linestyle=style, linewidth=1.1, label=label)
    t_ns = ng_data["time"] * 1e9
    tx, yx = clip(t_ns, ng_data["in"], window)
    tx, yx = envelope_decimate(tx, yx)
    ax.plot(tx, yx, color="0.75", linewidth=0.9, alpha=0.8, label="input")
    ax.set_ylabel("Pad / input (V)")
    ax.set_title("Stressed pybis spike lead-in: transmitter launch precedes receiver spike")
    ax.legend(loc="best", fontsize=8, ncol=3)

    ax = axes[1]
    for data, color, label, style in [
        (ng_data, "#0072B2", "ngspice pybis rx", "-"),
        (xy_data, "#D55E00", "Xyce pybis rx", "--"),
        (ref_ng, "0.25", "ngspice refspice rx", "-."),
        (ref_xy, "0.55", "Xyce refspice rx", ":"),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["rx"], window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(tx, yx, color=color, linestyle=style, linewidth=1.1, label=label)
    ax.set_ylabel("V(n10b) (V)")
    ax.legend(loc="best", fontsize=8, ncol=2)

    for ax, key, ylabel in [
        (axes[2], "ku", "Ku"),
        (axes[3], "kd", "Kd"),
        (axes[4], "nx", "NX (ns table time)"),
    ]:
        for data, color, label, style in [
            (ng_data, "#0072B2", "ngspice pybis", "-"),
            (xy_data, "#D55E00", "Xyce pybis", "--"),
        ]:
            t_ns = data["time"] * 1e9
            tx, yx = clip(t_ns, data[key], window)
            tx, yx = envelope_decimate(tx, yx)
            ax.plot(tx, yx, color=color, linestyle=style, linewidth=1.15, label=label)
        ax.set_ylabel(ylabel)
        ax.legend(loc="best", fontsize=8)

    for ax in axes:
        ax.set_xlim(*window)
        ax.grid(True, alpha=0.25)
        for marker_t, label in markers:
            ax.axvline(marker_t, color="0.2", linestyle=":", linewidth=0.9)
            ax.text(
                marker_t,
                0.98,
                label,
                transform=ax.get_xaxis_transform(),
                rotation=90,
                va="top",
                ha="right",
                fontsize=8,
            )
    axes[-1].set_xlabel("Time (ns)")
    fig.tight_layout()
    fig.savefig(case.out_dir / "15_stressed_spike_leadin_kukd_history.png", dpi=180)
    plt.close(fig)

    chain_window = (53.85, 57.05)
    event_times = {
        "input fall 50%": 54.10,
        "Ku/Kd switch": 54.20,
        "pad launch peak": 54.24,
        "rx spike": 56.69,
    }
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(14.0, 8.2),
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.25]},
    )

    ax = axes[0]
    for data, label_suffix, style, alpha in [
        (xy_data, "Xyce", "-", 0.95),
        (ng_data, "ngspice", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["ku"], chain_window)
        ax.plot(
            tx,
            yx,
            color="#0072B2",
            linestyle=style,
            linewidth=2.0,
            alpha=alpha,
            label=f"Ku {label_suffix}",
        )
        tx, yx = clip(t_ns, data["kd"], chain_window)
        ax.plot(
            tx,
            yx,
            color="#D55E00",
            linestyle=style,
            linewidth=2.0,
            alpha=alpha,
            label=f"Kd {label_suffix}",
        )
    ax.axvspan(54.10, 54.30, color="#FFD166", alpha=0.22, label="source window")
    ax.set_ylabel("Pybis coefficient")
    ax.set_ylim(-0.12, 1.12)
    ax.set_title("Stressed pybis spike chain: coefficient event launches pad pulse, channel delays it to receiver")
    ax.legend(loc="upper right", fontsize=8, ncol=3)
    ax.grid(True, alpha=0.25)

    ax = axes[1]
    waveform_specs = [
        (xy_data, "pad", "#CC3311", "-", 2.0, "pybis pad Xyce"),
        (ng_data, "pad", "#CC3311", ":", 1.8, "pybis pad ngspice"),
        (xy_data, "rx", "#7A3E9D", "-", 2.0, "pybis receiver Xyce"),
        (ng_data, "rx", "#7A3E9D", ":", 1.8, "pybis receiver ngspice"),
        (ref_xy, "pad", "0.45", "--", 1.2, "refspice pad Xyce"),
        (ref_xy, "rx", "0.2", "--", 1.2, "refspice receiver Xyce"),
    ]
    for data, key, color, style, width, label in waveform_specs:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data[key], chain_window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(tx, yx, color=color, linestyle=style, linewidth=width, label=label)
    t_ns = xy_data["time"] * 1e9
    tx, yx = clip(t_ns, xy_data["in"], chain_window)
    tx, yx = envelope_decimate(tx, yx / 3.3)
    ax.plot(tx, yx, color="0.65", linewidth=1.0, alpha=0.75, label="input scaled to 0-1")
    ax.axvspan(54.10, 54.30, color="#FFD166", alpha=0.22)
    ax.set_ylabel("Transient voltage (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_xlim(*chain_window)
    ax.set_ylim(-0.45, 2.35)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=8, ncol=3)

    for ax in axes:
        for label, marker_t in event_times.items():
            ax.axvline(marker_t, color="0.18", linestyle=":", linewidth=1.0)
            ax.text(
                marker_t,
                0.97,
                f"{marker_t:.2f} ns\n{label}",
                transform=ax.get_xaxis_transform(),
                rotation=90,
                va="top",
                ha="right",
                fontsize=8,
                color="0.15",
            )

    pad_peak_t = 54.24
    rx_peak_t = 56.69
    pad_peak_v = value_at_ns(xy_data, "pad", pad_peak_t)
    rx_peak_v = value_at_ns(xy_data, "rx", rx_peak_t)
    axes[1].annotate(
        "~2.45 ns channel delay",
        xy=(rx_peak_t, rx_peak_v),
        xytext=(54.95, 2.12),
        arrowprops={"arrowstyle": "->", "color": "0.2", "lw": 1.2},
        fontsize=9,
        color="0.15",
    )
    axes[1].annotate(
        "large pybis pad launch",
        xy=(pad_peak_t, pad_peak_v),
        xytext=(54.38, 2.23),
        arrowprops={"arrowstyle": "->", "color": "#CC3311", "lw": 1.2},
        fontsize=9,
        color="#8B1A0E",
    )
    axes[0].annotate(
        "Ku high / Kd off\nright after falling edge",
        xy=(54.22, value_at_ns(xy_data, "ku", 54.22)),
        xytext=(54.42, 0.72),
        arrowprops={"arrowstyle": "->", "color": "0.2", "lw": 1.1},
        fontsize=9,
        color="0.15",
    )
    fig.tight_layout()
    fig.savefig(case.out_dir / "16_stressed_spike_chain_kukd_top_transient_bottom.png", dpi=190)
    plt.close(fig)

    simple_window = (53.95, 54.85)
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(12.5, 6.8),
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.15]},
    )
    ax = axes[0]
    for data, suffix, style, alpha in [
        (xy_data, "Xyce", "-", 0.95),
        (ng_data, "ngspice", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["ku"], simple_window)
        ax.plot(tx, yx, color="#0072B2", linestyle=style, linewidth=2.1, alpha=alpha, label=f"Ku {suffix}")
        tx, yx = clip(t_ns, data["kd"], simple_window)
        ax.plot(tx, yx, color="#D55E00", linestyle=style, linewidth=2.1, alpha=alpha, label=f"Kd {suffix}")
    ax.set_ylabel("Coefficient")
    ax.set_ylim(-0.12, 1.12)
    ax.set_title("Stressed pybis source event: Ku/Kd switch vs tx_out before channel")
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.25)

    ax = axes[1]
    for data, suffix, style, alpha in [
        (xy_data, "Xyce", "-", 0.95),
        (ng_data, "ngspice", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["tx"], simple_window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(tx, yx, color="#7A3E9D", linestyle=style, linewidth=2.1, alpha=alpha, label=f"tx_out {suffix}")
    ax.set_ylabel("tx_out (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_ylim(-0.25, 2.35)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    for ax in axes:
        ax.set_xlim(*simple_window)
        for label, marker_t in [
            ("input fall 50%", 54.10),
            ("Ku/Kd switch", 54.20),
            ("tx peak", 54.24),
        ]:
            ax.axvline(marker_t, color="0.2", linestyle=":", linewidth=1.0)
            ax.text(
                marker_t,
                0.97,
                f"{marker_t:.2f} ns\n{label}",
                transform=ax.get_xaxis_transform(),
                rotation=90,
                va="top",
                ha="right",
                fontsize=8,
                color="0.15",
            )
    fig.tight_layout()
    fig.savefig(case.out_dir / "17_stressed_pybis_tx_vs_kukd_no_channel.png", dpi=190)
    plt.close(fig)

    context_window = (51.7, 56.6)
    context_markers = [
        ("previous input rise", 52.10),
        ("source spike fall", 54.10),
        ("Ku/Kd switch", 54.20),
        ("tx peak", 54.24),
        ("next input rise", 56.10),
    ]
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(13.5, 7.2),
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.2]},
    )

    ax = axes[0]
    for data, suffix, style, alpha in [
        (xy_data, "Xyce", "-", 0.95),
        (ng_data, "ngspice", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        for key, color, label in [
            ("ku", "#0072B2", "Ku"),
            ("kd", "#D55E00", "Kd"),
        ]:
            tx, yx = clip(t_ns, data[key], context_window)
            ax.plot(
                tx,
                yx,
                color=color,
                linestyle=style,
                linewidth=1.9,
                alpha=alpha,
                label=f"{label} {suffix}",
            )
    ax.axvspan(54.10, 54.30, color="#FFD166", alpha=0.22, label="problem source window")
    ax.set_ylabel("Coefficient")
    ax.set_ylim(-0.12, 1.12)
    ax.set_title("Stressed pybis source context: one bit before and after the large tx_out pulse")
    ax.legend(loc="upper right", fontsize=8, ncol=3)
    ax.grid(True, alpha=0.25)

    ax = axes[1]
    for data, suffix, style, alpha in [
        (xy_data, "Xyce", "-", 0.95),
        (ng_data, "ngspice", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["tx"], context_window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(
            tx,
            yx,
            color="#7A3E9D",
            linestyle=style,
            linewidth=2.0,
            alpha=alpha,
            label=f"tx_out {suffix}",
        )
    for data, suffix, style, alpha in [
        (ref_xy, "Xyce refspice", "--", 0.9),
        (ref_ng, "ngspice refspice", "-.", 0.82),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["tx"], context_window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(
            tx,
            yx,
            color="0.25",
            linestyle=style,
            linewidth=1.45,
            alpha=alpha,
            label=f"tx_out {suffix}",
        )
    t_ns = xy_data["time"] * 1e9
    tx, yx = clip(t_ns, xy_data["in"], context_window)
    tx, yx = envelope_decimate(tx, yx / 3.3)
    ax.plot(tx, yx, color="0.45", linewidth=1.15, alpha=0.82, label="input scaled to 0-1")
    ax.axvspan(54.10, 54.30, color="#FFD166", alpha=0.22)
    ax.set_ylabel("tx_out (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_xlim(*context_window)
    ax.set_ylim(-0.45, 2.35)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=8, ncol=3)

    for ax in axes:
        for label, marker_t in context_markers:
            ax.axvline(marker_t, color="0.2", linestyle=":", linewidth=0.9)
            ax.text(
                marker_t,
                0.97,
                f"{marker_t:.2f} ns\n{label}",
                transform=ax.get_xaxis_transform(),
                rotation=90,
                va="top",
                ha="right",
                fontsize=8,
                color="0.15",
            )
    axes[1].annotate(
        "large source pulse occurs on the falling edge,\nbetween two rising-edge intervals",
        xy=(54.24, value_at_ns(xy_data, "tx", 54.24)),
        xytext=(54.75, 1.86),
        arrowprops={"arrowstyle": "->", "color": "0.2", "lw": 1.1},
        fontsize=9,
        color="0.15",
    )
    fig.tight_layout()
    fig.savefig(case.out_dir / "18_stressed_pybis_tx_kukd_source_context.png", dpi=190)
    plt.close(fig)

    edge_specs = [
        {
            "edge": "E1",
            "label": "previous rise",
            "direction": "rise",
            "color": "#0072B2",
            "edge_window": (51.95, 52.25),
            "resp_window": (52.0, 53.05),
            "coeff_key": "kd",
            "coeff_level": 0.9,
            "coeff_direction": "rise",
            "tx_mode": "min",
        },
        {
            "edge": "E2",
            "label": "problem fall",
            "direction": "fall",
            "color": "#CC3311",
            "edge_window": (53.95, 54.25),
            "resp_window": (54.0, 55.35),
            "coeff_key": "ku",
            "coeff_level": 0.9,
            "coeff_direction": "rise",
            "tx_mode": "max",
        },
        {
            "edge": "E3",
            "label": "next rise",
            "direction": "rise",
            "color": "#009E73",
            "edge_window": (55.95, 56.25),
            "resp_window": (56.0, 56.65),
            "coeff_key": "kd",
            "coeff_level": 0.9,
            "coeff_direction": "rise",
            "tx_mode": "min",
        },
    ]

    edge_rows: list[dict[str, object]] = []
    for spec in edge_specs:
        input_t = crossing_time_ns(
            xy_data,
            "in",
            spec["edge_window"],
            1.65,
            spec["direction"],
        )
        coeff_xy_t = crossing_time_ns(
            xy_data,
            spec["coeff_key"],
            spec["edge_window"],
            spec["coeff_level"],
            spec["coeff_direction"],
        )
        coeff_ng_t = crossing_time_ns(
            ng_data,
            spec["coeff_key"],
            spec["edge_window"],
            spec["coeff_level"],
            spec["coeff_direction"],
        )
        py_xy_t, py_xy_v = extrema_in_window(xy_data, "tx", spec["resp_window"], spec["tx_mode"])
        py_ng_t, py_ng_v = extrema_in_window(ng_data, "tx", spec["resp_window"], spec["tx_mode"])
        ref_xy_t, ref_xy_v = extrema_in_window(ref_xy, "tx", spec["resp_window"], spec["tx_mode"])
        ref_ng_t, ref_ng_v = extrema_in_window(ref_ng, "tx", spec["resp_window"], spec["tx_mode"])
        edge_rows.append(
            {
                "edge": spec["edge"],
                "label": spec["label"],
                "direction": spec["direction"],
                "input_50pct_ns": input_t,
                "coefficient_signal": spec["coeff_key"],
                "xyce_coeff_cross_ns": coeff_xy_t,
                "ngspice_coeff_cross_ns": coeff_ng_t,
                "xyce_pybis_tx_extreme_ns": py_xy_t,
                "xyce_pybis_tx_extreme_v": py_xy_v,
                "ngspice_pybis_tx_extreme_ns": py_ng_t,
                "ngspice_pybis_tx_extreme_v": py_ng_v,
                "xyce_refspice_tx_extreme_ns": ref_xy_t,
                "xyce_refspice_tx_extreme_v": ref_xy_v,
                "ngspice_refspice_tx_extreme_ns": ref_ng_t,
                "ngspice_refspice_tx_extreme_v": ref_ng_v,
            }
        )

    map_window = (51.75, 56.75)
    fig, axes = plt.subplots(
        4,
        1,
        figsize=(14.0, 10.4),
        sharex=True,
        gridspec_kw={"height_ratios": [0.75, 1.0, 1.05, 1.05]},
    )

    ax = axes[0]
    t_ns = xy_data["time"] * 1e9
    tx, yx = clip(t_ns, xy_data["in"], map_window)
    tx, yx = envelope_decimate(tx, yx)
    ax.plot(tx, yx, color="0.25", linewidth=1.35, label="input")
    ax.set_ylabel("Input (V)")
    ax.set_ylim(-0.2, 3.5)
    ax.set_title("Source-side edge response map: input edge -> pybis Ku/Kd -> pybis/refspice tx_out")
    ax.legend(loc="upper right", fontsize=8)

    ax = axes[1]
    for data, suffix, style, alpha in [
        (xy_data, "Xyce", "-", 0.95),
        (ng_data, "ngspice", ":", 0.85),
    ]:
        t_ns = data["time"] * 1e9
        for key, color, label in [
            ("ku", "#0072B2", "Ku"),
            ("kd", "#D55E00", "Kd"),
        ]:
            tx, yx = clip(t_ns, data[key], map_window)
            ax.plot(tx, yx, color=color, linestyle=style, linewidth=1.7, alpha=alpha, label=f"{label} {suffix}")
    ax.set_ylabel("Ku/Kd")
    ax.set_ylim(-0.12, 1.12)
    ax.legend(loc="upper right", fontsize=8, ncol=4)

    ax = axes[2]
    for data, suffix, style, alpha in [
        (xy_data, "Xyce pybis", "-", 0.95),
        (ng_data, "ngspice pybis", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["tx"], map_window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(tx, yx, color="#7A3E9D", linestyle=style, linewidth=1.8, alpha=alpha, label=f"tx_out {suffix}")
    ax.set_ylabel("pybis tx_out (V)")
    ax.set_ylim(-0.45, 2.35)
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    ax = axes[3]
    for data, suffix, style, alpha in [
        (ref_xy, "Xyce refspice", "-", 0.95),
        (ref_ng, "ngspice refspice", ":", 0.9),
    ]:
        t_ns = data["time"] * 1e9
        tx, yx = clip(t_ns, data["tx"], map_window)
        tx, yx = envelope_decimate(tx, yx)
        ax.plot(tx, yx, color="0.25", linestyle=style, linewidth=1.8, alpha=alpha, label=f"tx_out {suffix}")
    ax.set_ylabel("refspice tx_out (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_ylim(-0.65, 1.75)
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    for ax in axes:
        ax.set_xlim(*map_window)
        ax.grid(True, alpha=0.25)
        for row, spec in zip(edge_rows, edge_specs):
            color = spec["color"]
            input_t = row["input_50pct_ns"]
            coeff_t = row["xyce_coeff_cross_ns"]
            py_t = row["xyce_pybis_tx_extreme_ns"]
            ref_t = row["xyce_refspice_tx_extreme_ns"]
            ax.axvline(input_t, color=color, linestyle=":", linewidth=1.0, alpha=0.95)
            ax.axvline(coeff_t, color=color, linestyle="-.", linewidth=0.9, alpha=0.75)
            if ax is axes[2]:
                ax.axvline(py_t, color=color, linestyle="--", linewidth=0.95, alpha=0.85)
            if ax is axes[3]:
                ax.axvline(ref_t, color=color, linestyle="--", linewidth=0.95, alpha=0.85)

    for row, spec in zip(edge_rows, edge_specs):
        color = spec["color"]
        input_t = row["input_50pct_ns"]
        coeff_t = row["xyce_coeff_cross_ns"]
        py_t = row["xyce_pybis_tx_extreme_ns"]
        ref_t = row["xyce_refspice_tx_extreme_ns"]
        axes[0].text(input_t, 0.94, f"{spec['edge']} input\n{input_t:.2f} ns", transform=axes[0].get_xaxis_transform(), rotation=90, va="top", ha="right", fontsize=8, color=color)
        axes[1].text(coeff_t, 0.94, f"{spec['edge']} {spec['coeff_key'].upper()}\n{coeff_t:.2f} ns", transform=axes[1].get_xaxis_transform(), rotation=90, va="top", ha="right", fontsize=8, color=color)
        axes[2].text(py_t, 0.94, f"{spec['edge']} pybis\n{py_t:.2f} ns", transform=axes[2].get_xaxis_transform(), rotation=90, va="top", ha="right", fontsize=8, color=color)
        axes[3].text(ref_t, 0.94, f"{spec['edge']} ref\n{ref_t:.2f} ns", transform=axes[3].get_xaxis_transform(), rotation=90, va="top", ha="right", fontsize=8, color=color)

    axes[2].annotate(
        "problem edge: pybis source pulse is much larger",
        xy=(edge_rows[1]["xyce_pybis_tx_extreme_ns"], edge_rows[1]["xyce_pybis_tx_extreme_v"]),
        xytext=(54.55, 2.08),
        arrowprops={"arrowstyle": "->", "color": "#CC3311", "lw": 1.1},
        fontsize=9,
        color="#8B1A0E",
    )
    axes[3].annotate(
        "same input edge in refspice",
        xy=(edge_rows[1]["xyce_refspice_tx_extreme_ns"], edge_rows[1]["xyce_refspice_tx_extreme_v"]),
        xytext=(54.55, 1.35),
        arrowprops={"arrowstyle": "->", "color": "0.25", "lw": 1.1},
        fontsize=9,
        color="0.2",
    )
    fig.tight_layout()
    fig.savefig(case.out_dir / "19_stressed_source_edge_response_map.png", dpi=190)
    plt.close(fig)
    write_metrics(case.out_dir / "source_edge_response_map_metrics.csv", edge_rows)

    rows: list[dict[str, object]] = []
    for flow, data, ref_data in [
        ("ngspice_pybis", ng_data, ref_ng),
        ("xyce_pybis", xy_data, ref_xy),
    ]:
        pad_peak_ns, pad_peak_v = extrema_in_window(data, "pad", (53.8, 55.2), "max")
        rx_peak_ns, rx_peak_v = extrema_in_window(data, "rx", (55.5, 58.8), "max")
        ref_pad_peak_ns, ref_pad_peak_v = extrema_in_window(ref_data, "pad", (53.8, 55.2), "max")
        ref_rx_peak_ns, ref_rx_peak_v = extrema_in_window(ref_data, "rx", (55.5, 58.8), "max")
        rows.append(
            {
                "case": case.name,
                "flow": flow,
                "pybis_pad_peak_ns": pad_peak_ns,
                "pybis_pad_peak_v": pad_peak_v,
                "refspice_pad_peak_ns": ref_pad_peak_ns,
                "refspice_pad_peak_v": ref_pad_peak_v,
                "pybis_rx_peak_ns": rx_peak_ns,
                "pybis_rx_peak_v": rx_peak_v,
                "refspice_rx_peak_ns": ref_rx_peak_ns,
                "refspice_rx_peak_v": ref_rx_peak_v,
                "pad_peak_to_rx_peak_ns": rx_peak_ns - pad_peak_ns,
                "ku_at_rx_peak": value_at_ns(data, "ku", rx_peak_ns),
                "kd_at_rx_peak": value_at_ns(data, "kd", rx_peak_ns),
                "nx_at_rx_peak": value_at_ns(data, "nx", rx_peak_ns),
                "ku_cross_0p1_after_rise_ns": first_crossing_ns(data, "ku", (56.2, 62.5), 0.1, "rise"),
                "kd_cross_0p9_after_rise_ns": first_crossing_ns(data, "kd", (56.2, 62.5), 0.9, "fall"),
            }
        )

    write_metrics(case.out_dir / "spike_leadin_metrics.csv", rows)
    return rows


def copy_if_different(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and src.read_bytes() == dst.read_bytes():
        return
    shutil.copy2(src, dst)


def build_cases() -> list[CaseConfig]:
    normal_sources = NORMAL_DIR / "kukd_sources"
    stressed_sources = STRESSED_DIR / "kukd_sources"
    return [
        CaseConfig(
            name="normal_prbs_channel",
            title="Normal PRBS7 + accepted 50 ohm RLGC channel",
            out_dir=NORMAL_DIR,
            full_window_ns=(0.0, 75.0),
            zoom_window_ns=(50.0, 70.0),
            marker_ns=None,
            marker_label="",
            min_t_end_ns=79.0,
            ngspice_source_deck=ROOT
            / "results"
            / "prbs_rlgc_clean_2026-05-10"
            / "ngspice"
            / "tb_clean_prbs_rlgc_ngspice.sp",
            ngspice_review_deck=normal_sources / "normal_ngspice_pybis_kukd.sp",
            ngspice_review_raw=normal_sources / "normal_ngspice_pybis_kukd.raw",
            xyce_csv=ROOT
            / "results"
            / "prbs_rlgc_clean_2026-05-10"
            / "xyce"
            / "tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir.csv",
            include_replacements={
                "prbs7_vstim.inc": ROOT / "ngspice_pybis" / "prbs7_vstim.inc",
                "driver_OutputInput_Typical.sub": ROOT
                / "results"
                / "ngspice_kukd_ab_context38_2026-05-11"
                / "driver_OutputInput_Typical_pre_kukd_3e0bf44.sub",
                "../new 50ohm channel/channel_ngspice.sp": ROOT
                / "new 50ohm channel"
                / "channel_ngspice.sp",
            },
        ),
        CaseConfig(
            name="stressed_edge50_prbs80_channel",
            title="Stressed edge50 PRBS80 + 30 cm loss x5 coarse10 RLGC channel",
            out_dir=STRESSED_DIR,
            full_window_ns=(0.0, 160.0),
            zoom_window_ns=(55.5, 58.8),
            marker_ns=56.69,
            marker_label="spike peak",
            min_t_end_ns=159.0,
            ngspice_source_deck=ROOT
            / "results"
            / "stressed_edge50_corrected_crossflow_2026-05-12_clean"
            / "runs"
            / "ui2_len30cm_loss5_coarse10"
            / "ngspice_pybis_edge50_corrected"
            / "ui2_len30cm_loss5_coarse10_ngspice_pybis_edge50_corrected.sp",
            ngspice_review_deck=stressed_sources / "stressed_ngspice_pybis_edge50_kukd.sp",
            ngspice_review_raw=stressed_sources / "stressed_ngspice_pybis_edge50_kukd.raw",
            xyce_csv=ROOT
            / "results"
            / "stressed_edge50_corrected_crossflow_2026-05-12_clean"
            / "runs"
            / "ui2_len30cm_loss5_coarse10"
            / "xyce_pybis_edge50"
            / "ui2_len30cm_loss5_coarse10_xyce_pybis_edge50.cir.csv",
            include_replacements={
                "../../../models/driver_OutputInput_Typical_relaxed92_edge50_tailflat4p2_ngspice_syntax.sub": ROOT
                / "results"
                / "stressed_edge50_corrected_crossflow_2026-05-12_clean"
                / "models"
                / "driver_OutputInput_Typical_relaxed92_edge50_tailflat4p2_ngspice_syntax.sub",
            },
        ),
    ]


def main() -> int:
    all_rows: list[dict[str, object]] = []
    all_normal_rows: list[dict[str, object]] = []
    for case in build_cases():
        run_ngspice_if_needed(case)
        case_rows: list[dict[str, object]] = []
        ng_flow = Flow(
            label="ngspice pybis",
            path=case.ngspice_review_raw,
            fmt="ngspice",
            n10b_signal="v(n10b)",
            ku_signal="v(xdrv.ku)",
            kd_signal="v(xdrv.kd)",
            pad_signal="v(pad)",
            tx_signal="v(tx_out)",
            nx_signal="v(xdrv.nx)",
            input_signal="v(in_dig)",
        )
        xy_flow = Flow(
            label="Xyce pybis",
            path=case.xyce_csv,
            fmt="xyce",
            n10b_signal="v(n10b)",
            ku_signal="v(xdrv:ku)",
            kd_signal="v(xdrv:kd)",
            pad_signal="v(pad)",
            tx_signal="v(tx_out)",
            nx_signal="v(xdrv:nx)",
            input_signal="v(in_dig)",
        )
        ng_data = load_flow(ng_flow)
        xy_data = load_flow(xy_flow)
        plot_individual(case, ng_flow, ng_data, case.out_dir / "12_ngspice_pybis_kukd.png")
        plot_individual(case, xy_flow, xy_data, case.out_dir / "13_xyce_pybis_kukd.png")
        plot_overlay(case, ng_data, xy_data, case.out_dir / "14_ngspice_xyce_pybis_kukd_overlay.png")
        normal_rows = plot_normal_source_edge_history(case, ng_data, xy_data)
        all_normal_rows.extend(normal_rows)
        spike_rows = plot_spike_leadin_history(case, ng_data, xy_data)
        case_rows.extend(summarize(case, "ngspice_pybis", ng_data))
        case_rows.extend(summarize(case, "xyce_pybis", xy_data))
        all_rows.extend(case_rows)
        write_metrics(case.out_dir / "kukd_metrics.csv", case_rows)
        copy_if_different(case.ngspice_review_raw.with_suffix(".log"), case.out_dir / "kukd_sources" / case.ngspice_review_raw.with_suffix(".log").name)

    write_metrics(REVIEW_DIR / "kukd_metrics.csv", all_rows)
    for row in all_rows:
        if row["window"] == "zoom":
            print(
                f"{row['case']} {row['flow']}: "
                f"Ku {row['ku_min']:.4g}..{row['ku_max']:.4g}, "
                f"Kd {row['kd_min']:.4g}..{row['kd_max']:.4g}"
            )
    if spike_rows:
        for row in spike_rows:
            print(
                f"{row['flow']} spike lead-in: pad peak {row['pybis_pad_peak_v']:.4g}V "
                f"at {row['pybis_pad_peak_ns']:.3f}ns -> rx peak {row['pybis_rx_peak_v']:.4g}V "
                f"at {row['pybis_rx_peak_ns']:.3f}ns; "
                f"Ku/Kd at rx peak {row['ku_at_rx_peak']:.4g}/{row['kd_at_rx_peak']:.4g}"
            )
    if all_normal_rows:
        for row in all_normal_rows:
            print(
                f"normal {row['edge']} {row['direction']}: input {row['input_50pct_ns']:.3f}ns, "
                f"{str(row['expected_source_coefficient']).upper()} Xyce/ngspice "
                f"{row['xyce_coeff_cross_0p9_ns']:.3f}/{row['ngspice_coeff_cross_0p9_ns']:.3f}ns, "
                f"pybis tx Xyce/ngspice {row['xyce_pybis_tx_extreme_v']:.4g}/"
                f"{row['ngspice_pybis_tx_extreme_v']:.4g}V"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
