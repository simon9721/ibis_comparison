from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from run_io_buf_coeff_state_retrigger import build_cases, build_pwl_points  # noqa: E402


STUDY_DIR = ROOT / "results" / "io_buf_coeff_state_retrigger_2026-06-20"
OUT_DIR = STUDY_DIR / "interrupted_switching_demo"
PLOTS_DIR = OUT_DIR / "figures"
CONTROL_CASE = "edge_1ps_base_50r_2pf"
INTERRUPTED_CASE = "short_pulse_1ns_high"


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    available = ", ".join(sorted(data.keys()))
    raise KeyError(f"Missing signal {names}; available: {available}")


def to_ns(t_s: np.ndarray) -> np.ndarray:
    return np.asarray(t_s, dtype=float) * 1e9


def interp_to(t_src_ns: np.ndarray, y_src: np.ndarray, t_dst_ns: np.ndarray) -> np.ndarray:
    return np.interp(t_dst_ns, t_src_ns, y_src)


def read_case(case_id: str) -> dict[str, np.ndarray]:
    case_dir = STUDY_DIR / "cases" / case_id
    h_path = case_dir / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0"
    legacy_path = case_dir / "ngspice_legacy" / f"{case_id}_ngspice_legacy.raw"
    coeff_path = case_dir / "ngspice_coeff_state" / f"{case_id}_ngspice_coeff_state.raw"

    h = parse_hspice_tr0(h_path)
    legacy = parse_ngspice_raw(legacy_path)
    coeff = parse_ngspice_raw(coeff_path)

    t = to_ns(find_signal(h, "time"))
    legacy_t = to_ns(find_signal(legacy, "time"))
    coeff_t = to_ns(find_signal(coeff, "time"))

    return {
        "time_ns": t,
        "hspice_pad_v": find_signal(h, "v(pad_ibis)"),
        "hspice_ku": find_signal(h, "v(ku)"),
        "hspice_kd": find_signal(h, "v(kd)"),
        "legacy_pad_v": interp_to(legacy_t, find_signal(legacy, "v(pad)"), t),
        "legacy_ku": interp_to(legacy_t, find_signal(legacy, "v(xdrv.ku)", "v(xdrv:ku)"), t),
        "legacy_kd": interp_to(legacy_t, find_signal(legacy, "v(xdrv.kd)", "v(xdrv:kd)"), t),
        "coeff_pad_v": interp_to(coeff_t, find_signal(coeff, "v(pad)"), t),
        "coeff_ku": interp_to(coeff_t, find_signal(coeff, "v(xdrv.ku)", "v(xdrv:ku)"), t),
        "coeff_kd": interp_to(coeff_t, find_signal(coeff, "v(xdrv.kd)", "v(xdrv:kd)"), t),
        "coeff_kutarget": interp_to(coeff_t, find_signal(coeff, "v(xdrv.kutarget)", "v(xdrv:kutarget)"), t),
        "coeff_kdtarget": interp_to(coeff_t, find_signal(coeff, "v(xdrv.kdtarget)", "v(xdrv:kdtarget)"), t),
    }


def case_by_id(case_id: str):
    return {case.case_id: case for case in build_cases()}[case_id]


def input_waveform(case_id: str, t: np.ndarray) -> np.ndarray:
    points = build_pwl_points(case_by_id(case_id))
    xp = np.asarray([p[0] for p in points], dtype=float)
    yp = np.asarray([p[1] for p in points], dtype=float)
    return np.interp(t, xp, yp)


def command_times(case_id: str) -> tuple[float, float]:
    case = case_by_id(case_id)
    edge = case.edge_ns
    if case.pattern == "short_pulse":
        return 5.0 + 0.5 * edge, 5.0 + case.high_time_ns + 0.5 * edge
    return 5.0 + 0.5 * edge, 15.0 + 0.5 * edge


def active_mask(t: np.ndarray, start: float, stop: float) -> np.ndarray:
    return (t >= start) & (t <= stop)


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def peak_value(t: np.ndarray, y: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    idx = int(np.argmax(y[mask]))
    tt = t[mask]
    yy = y[mask]
    return float(yy[idx]), float(tt[idx])


def min_value(t: np.ndarray, y: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    idx = int(np.argmin(y[mask]))
    tt = t[mask]
    yy = y[mask]
    return float(yy[idx]), float(tt[idx])


def settled_high_reference(control: dict[str, np.ndarray]) -> float:
    t = control["time_ns"]
    y = control["hspice_pad_v"]
    mask = (t >= 11.0) & (t <= 14.0)
    return float(np.median(y[mask]))


def metrics(control: dict[str, np.ndarray], short: dict[str, np.ndarray]) -> dict[str, float]:
    t = short["time_ns"]
    rise_50, fall_50 = command_times(INTERRUPTED_CASE)
    mask = active_mask(t, rise_50 - 0.5, fall_50 + 4.5)

    h_pad_pk, h_pad_pk_t = peak_value(t, short["hspice_pad_v"], mask)
    l_pad_pk, l_pad_pk_t = peak_value(t, short["legacy_pad_v"], mask)
    c_pad_pk, c_pad_pk_t = peak_value(t, short["coeff_pad_v"], mask)
    h_ku_pk, h_ku_pk_t = peak_value(t, short["hspice_ku"], mask)
    l_ku_pk, l_ku_pk_t = peak_value(t, short["legacy_ku"], mask)
    c_ku_pk, c_ku_pk_t = peak_value(t, short["coeff_ku"], mask)
    h_kd_min, h_kd_min_t = min_value(t, short["hspice_kd"], mask)
    l_kd_min, l_kd_min_t = min_value(t, short["legacy_kd"], mask)
    c_kd_min, c_kd_min_t = min_value(t, short["coeff_kd"], mask)

    return {
        "settled_high_v": settled_high_reference(control),
        "rise_command_50_ns": rise_50,
        "fall_command_50_ns": fall_50,
        "hspice_pad_at_reverse_v": float(np.interp(fall_50, t, short["hspice_pad_v"])),
        "legacy_pad_at_reverse_v": float(np.interp(fall_50, t, short["legacy_pad_v"])),
        "coeff_pad_at_reverse_v": float(np.interp(fall_50, t, short["coeff_pad_v"])),
        "hspice_pad_peak_v": h_pad_pk,
        "legacy_pad_peak_v": l_pad_pk,
        "coeff_pad_peak_v": c_pad_pk,
        "hspice_pad_peak_time_ns": h_pad_pk_t,
        "legacy_pad_peak_time_ns": l_pad_pk_t,
        "coeff_pad_peak_time_ns": c_pad_pk_t,
        "hspice_ku_peak": h_ku_pk,
        "legacy_ku_peak": l_ku_pk,
        "coeff_ku_peak": c_ku_pk,
        "hspice_ku_peak_time_ns": h_ku_pk_t,
        "legacy_ku_peak_time_ns": l_ku_pk_t,
        "coeff_ku_peak_time_ns": c_ku_pk_t,
        "hspice_kd_min": h_kd_min,
        "legacy_kd_min": l_kd_min,
        "coeff_kd_min": c_kd_min,
        "hspice_kd_min_time_ns": h_kd_min_t,
        "legacy_kd_min_time_ns": l_kd_min_t,
        "coeff_kd_min_time_ns": c_kd_min_t,
        "legacy_pad_rmse_v": rmse(short["legacy_pad_v"][mask], short["hspice_pad_v"][mask]),
        "coeff_pad_rmse_v": rmse(short["coeff_pad_v"][mask], short["hspice_pad_v"][mask]),
        "legacy_ku_rmse": rmse(short["legacy_ku"][mask], short["hspice_ku"][mask]),
        "coeff_ku_rmse": rmse(short["coeff_ku"][mask], short["hspice_ku"][mask]),
        "legacy_kd_rmse": rmse(short["legacy_kd"][mask], short["hspice_kd"][mask]),
        "coeff_kd_rmse": rmse(short["coeff_kd"][mask], short["hspice_kd"][mask]),
    }


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def mark_commands(axes, rise_50: float, fall_50: float) -> None:
    for ax in np.ravel(axes):
        ax.axvline(rise_50, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvline(fall_50, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvspan(rise_50, fall_50, color="#f2c94c", alpha=0.14, lw=0)


def plot_interrupted_timeline(short: dict[str, np.ndarray], values: dict[str, float]) -> None:
    t = short["time_ns"]
    vin = input_waveform(INTERRUPTED_CASE, t)
    rise_50 = values["rise_command_50_ns"]
    fall_50 = values["fall_command_50_ns"]

    fig, axes = plt.subplots(4, 1, figsize=(11.2, 10.2), sharex=True, height_ratios=[0.75, 1.05, 1.2, 1.0])
    mark_commands(axes, rise_50, fall_50)

    axes[0].plot(t, vin, color="black", lw=2.0)
    axes[0].set_ylim(-0.25, 3.55)
    style(axes[0], "Input (V)")
    axes[0].annotate("rise command", xy=(rise_50, 3.05), xytext=(rise_50 - 0.45, 2.25), arrowprops={"arrowstyle": "->", "lw": 1.1})
    axes[0].annotate("reverse before settle", xy=(fall_50, 3.05), xytext=(fall_50 + 0.25, 2.25), arrowprops={"arrowstyle": "->", "lw": 1.1})

    axes[1].plot(t, short["hspice_pad_v"], lw=2.2, label="HSPICE native IBIS")
    axes[1].plot(t, short["legacy_pad_v"], lw=1.9, ls="--", label="legacy pybis")
    axes[1].plot(t, short["coeff_pad_v"], lw=2.0, ls="-.", label="CoeffState pybis")
    axes[1].axhline(values["settled_high_v"], color="0.25", lw=1.0, ls=":", alpha=0.75, label="settled high")
    style(axes[1], "Pad (V)")
    axes[1].legend(loc="upper right", ncol=2)
    axes[1].annotate(
        f"At reverse: HSPICE pad {values['hspice_pad_at_reverse_v']:.2f} V\nsettled high {values['settled_high_v']:.2f} V",
        xy=(fall_50, values["hspice_pad_at_reverse_v"]),
        xytext=(fall_50 + 0.45, 0.55),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )

    axes[2].plot(t, short["hspice_ku"], color="#1f77b4", lw=2.1, label="HSPICE Ku")
    axes[2].plot(t, short["legacy_ku"], color="#1f77b4", lw=1.7, ls="--", label="legacy Ku")
    axes[2].plot(t, short["coeff_ku"], color="#1f77b4", lw=1.9, ls="-.", label="CoeffState Ku")
    axes[2].plot(t, short["hspice_kd"], color="#d62728", lw=2.1, label="HSPICE Kd")
    axes[2].plot(t, short["legacy_kd"], color="#d62728", lw=1.7, ls="--", label="legacy Kd")
    axes[2].plot(t, short["coeff_kd"], color="#d62728", lw=1.9, ls="-.", label="CoeffState Kd")
    axes[2].set_ylim(-0.12, 1.12)
    style(axes[2], "Ku / Kd")
    axes[2].legend(loc="center right", ncol=3)
    axes[2].annotate(
        f"legacy Ku peak {values['legacy_ku_peak']:.2f}\nCoeffState Ku peak {values['coeff_ku_peak']:.2f}\nHSPICE Ku peak {values['hspice_ku_peak']:.2f}",
        xy=(values["coeff_ku_peak_time_ns"], values["coeff_ku_peak"]),
        xytext=(fall_50 + 1.0, 0.34),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )

    axes[3].plot(t, short["coeff_kutarget"], lw=2.0, label="CoeffState KUTARGET")
    axes[3].plot(t, short["coeff_ku"], lw=1.7, ls="--", label="CoeffState Ku")
    axes[3].plot(t, short["coeff_kdtarget"], lw=2.0, label="CoeffState KDTARGET")
    axes[3].plot(t, short["coeff_kd"], lw=1.7, ls="--", label="CoeffState Kd")
    axes[3].set_ylim(-0.08, 1.08)
    style(axes[3], "Targets / states")
    axes[3].legend(loc="center right", ncol=2)
    axes[3].set_xlabel("Time (ns)")

    axes[3].set_xlim(rise_50 - 0.65, fall_50 + 5.0)
    fig.suptitle("InputDrivenCoeffState interrupted switching demo: short_pulse_1ns_high")
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(PLOTS_DIR / "01_interrupted_event_timeline.png", dpi=180)
    plt.close(fig)


def plot_ku_kd_focus(short: dict[str, np.ndarray], values: dict[str, float]) -> None:
    t = short["time_ns"]
    rise_50 = values["rise_command_50_ns"]
    fall_50 = values["fall_command_50_ns"]

    fig, axes = plt.subplots(2, 1, figsize=(11.0, 6.7), sharex=True)
    mark_commands(axes, rise_50, fall_50)

    axes[0].plot(t, short["hspice_ku"], lw=2.3, label="HSPICE Ku")
    axes[0].plot(t, short["legacy_ku"], lw=2.0, ls="--", label="legacy pybis Ku")
    axes[0].plot(t, short["coeff_ku"], lw=2.0, ls="-.", label="CoeffState Ku")
    axes[0].set_ylim(-0.08, 1.08)
    style(axes[0], "Ku")
    axes[0].legend(loc="upper right")
    axes[0].annotate(
        "legacy still plays a near-full transition",
        xy=(values["legacy_ku_peak_time_ns"], values["legacy_ku_peak"]),
        xytext=(fall_50 + 0.25, 0.82),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[0].annotate(
        "CoeffState keeps Ku partial,\nbut still higher than HSPICE",
        xy=(values["coeff_ku_peak_time_ns"], values["coeff_ku_peak"]),
        xytext=(fall_50 + 0.55, 0.38),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )

    axes[1].plot(t, short["hspice_kd"], lw=2.3, label="HSPICE Kd")
    axes[1].plot(t, short["legacy_kd"], lw=2.0, ls="--", label="legacy pybis Kd")
    axes[1].plot(t, short["coeff_kd"], lw=2.0, ls="-.", label="CoeffState Kd")
    axes[1].set_ylim(-0.12, 1.08)
    style(axes[1], "Kd")
    axes[1].legend(loc="lower right")
    axes[1].annotate(
        "CoeffState Kd recovers continuously,\nbut misses HSPICE's brief negative dip",
        xy=(values["coeff_kd_min_time_ns"], values["coeff_kd_min"]),
        xytext=(fall_50 + 1.15, 0.42),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_xlim(rise_50 - 0.2, fall_50 + 4.4)
    fig.suptitle("Ku/Kd behavior during interrupted pulse")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(PLOTS_DIR / "02_ku_kd_state_difference.png", dpi=180)
    plt.close(fig)


def plot_pad_consequence(short: dict[str, np.ndarray], values: dict[str, float]) -> None:
    t = short["time_ns"]
    rise_50 = values["rise_command_50_ns"]
    fall_50 = values["fall_command_50_ns"]
    mask = active_mask(t, rise_50 - 0.1, fall_50 + 4.2)

    fig, ax = plt.subplots(figsize=(11.0, 5.3))
    mark_commands([ax], rise_50, fall_50)
    ax.plot(t, short["hspice_pad_v"], lw=2.4, label="HSPICE native IBIS")
    ax.plot(t, short["legacy_pad_v"], lw=2.1, ls="--", label="legacy pybis")
    ax.plot(t, short["coeff_pad_v"], lw=2.1, ls="-.", label="CoeffState pybis")
    ax.fill_between(t[mask], short["hspice_pad_v"][mask], short["legacy_pad_v"][mask], color="#eb5757", alpha=0.13, label="legacy mismatch")
    ax.fill_between(t[mask], short["hspice_pad_v"][mask], short["coeff_pad_v"][mask], color="#2f80ed", alpha=0.13, label="CoeffState mismatch")
    style(ax, "Pad voltage (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_xlim(rise_50 - 0.2, fall_50 + 4.4)
    ax.set_ylim(-0.12, 1.65)
    ax.legend(loc="upper right")
    ax.annotate(
        f"HSPICE partial pulse\npeak {values['hspice_pad_peak_v']:.2f} V",
        xy=(values["hspice_pad_peak_time_ns"], values["hspice_pad_peak_v"]),
        xytext=(rise_50 + 0.25, 0.56),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.annotate(
        f"legacy near-full pulse\npeak {values['legacy_pad_peak_v']:.2f} V",
        xy=(values["legacy_pad_peak_time_ns"], values["legacy_pad_peak_v"]),
        xytext=(fall_50 + 0.55, 1.18),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.annotate(
        f"CoeffState reduced pulse\npeak {values['coeff_pad_peak_v']:.2f} V",
        xy=(values["coeff_pad_peak_time_ns"], values["coeff_pad_peak_v"]),
        xytext=(fall_50 + 1.15, 0.28),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.set_title("Pad consequence: coefficient-state improves the failure, but does not match HSPICE yet")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "03_pad_consequence.png", dpi=180)
    plt.close(fig)


def plot_control_vs_interrupted(control: dict[str, np.ndarray], short: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 7.4), sharex="col")

    ct = control["time_ns"]
    st = short["time_ns"]
    control_vin = input_waveform(CONTROL_CASE, ct) / 3.3
    short_vin = input_waveform(INTERRUPTED_CASE, st) / 3.3
    rise_50, fall_50 = command_times(INTERRUPTED_CASE)

    axes[0, 0].plot(ct, control_vin, color="black", lw=1.4, label="input / 3.3")
    axes[0, 0].plot(ct, control["hspice_pad_v"], lw=2.0, label="HSPICE pad")
    axes[0, 0].plot(ct, control["legacy_pad_v"], lw=1.7, ls="--", label="legacy pad")
    axes[0, 0].plot(ct, control["coeff_pad_v"], lw=1.8, ls="-.", label="CoeffState pad")
    axes[0, 0].set_title("Control: complete full toggle")
    style(axes[0, 0], "Pad / input")
    axes[0, 0].legend(loc="upper right")
    axes[0, 0].set_xlim(4.7, 18.7)

    axes[1, 0].plot(ct, control["hspice_ku"], lw=2.0, label="HSPICE Ku")
    axes[1, 0].plot(ct, control["legacy_ku"], lw=1.7, ls="--", label="legacy Ku")
    axes[1, 0].plot(ct, control["coeff_ku"], lw=1.8, ls="-.", label="CoeffState Ku")
    axes[1, 0].plot(ct, control["hspice_kd"], lw=2.0, label="HSPICE Kd")
    axes[1, 0].plot(ct, control["legacy_kd"], lw=1.7, ls="--", label="legacy Kd")
    axes[1, 0].plot(ct, control["coeff_kd"], lw=1.8, ls="-.", label="CoeffState Kd")
    style(axes[1, 0], "Coeff")
    axes[1, 0].set_ylim(-0.12, 1.12)
    axes[1, 0].set_xlabel("Time (ns)")
    axes[1, 0].legend(loc="center right", ncol=3)

    axes[0, 1].plot(st, short_vin, color="black", lw=1.4, label="input / 3.3")
    axes[0, 1].plot(st, short["hspice_pad_v"], lw=2.0, label="HSPICE pad")
    axes[0, 1].plot(st, short["legacy_pad_v"], lw=1.7, ls="--", label="legacy pad")
    axes[0, 1].plot(st, short["coeff_pad_v"], lw=1.8, ls="-.", label="CoeffState pad")
    axes[0, 1].set_title("Interrupted: reverse before settling")
    style(axes[0, 1], "Pad / input")
    axes[0, 1].legend(loc="upper right")
    axes[0, 1].set_xlim(rise_50 - 0.3, fall_50 + 4.5)

    axes[1, 1].plot(st, short["hspice_ku"], lw=2.0, label="HSPICE Ku")
    axes[1, 1].plot(st, short["legacy_ku"], lw=1.7, ls="--", label="legacy Ku")
    axes[1, 1].plot(st, short["coeff_ku"], lw=1.8, ls="-.", label="CoeffState Ku")
    axes[1, 1].plot(st, short["hspice_kd"], lw=2.0, label="HSPICE Kd")
    axes[1, 1].plot(st, short["legacy_kd"], lw=1.7, ls="--", label="legacy Kd")
    axes[1, 1].plot(st, short["coeff_kd"], lw=1.8, ls="-.", label="CoeffState Kd")
    style(axes[1, 1], "Coeff")
    axes[1, 1].set_ylim(-0.12, 1.12)
    axes[1, 1].set_xlabel("Time (ns)")
    axes[1, 1].legend(loc="center right", ncol=3)

    for ax in axes[:, 1]:
        ax.axvline(rise_50, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvline(fall_50, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvspan(rise_50, fall_50, color="#f2c94c", alpha=0.14, lw=0)

    fig.suptitle("Control vs interrupted switching: branch-state algorithm improves interruption but regresses complete edges")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(PLOTS_DIR / "04_control_vs_interrupted.png", dpi=180)
    plt.close(fig)


def plot_short_pulse_summary() -> None:
    metrics_path = STUDY_DIR / "legacy_vs_coeff_state_summary.csv"
    rows = []
    with metrics_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["kind"] == "short_pulse":
                rows.append(row)
    if not rows:
        return

    labels = [row["case_id"].replace("short_pulse_", "").replace("_high", "") for row in rows]
    x = np.arange(len(rows))
    legacy_pad = np.array([float(row["legacy_pad_rmse_mv"]) for row in rows])
    coeff_pad = np.array([float(row["coeff_pad_rmse_mv"]) for row in rows])
    legacy_coeff = np.array([float(row["legacy_coeff_rmse"]) for row in rows])
    coeff_coeff = np.array([float(row["coeff_coeff_rmse"]) for row in rows])

    fig, axes = plt.subplots(2, 1, figsize=(9.5, 6.8), sharex=True)
    width = 0.34
    axes[0].bar(x - width / 2, legacy_pad, width=width, label="legacy pybis")
    axes[0].bar(x + width / 2, coeff_pad, width=width, label="CoeffState pybis")
    axes[0].set_ylabel("Pad RMSE (mV)")
    axes[0].grid(True, axis="y", alpha=0.28)
    axes[0].legend(loc="upper right")

    axes[1].bar(x - width / 2, legacy_coeff, width=width, label="legacy pybis")
    axes[1].bar(x + width / 2, coeff_coeff, width=width, label="CoeffState pybis")
    axes[1].set_ylabel("Max Ku/Kd RMSE")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].grid(True, axis="y", alpha=0.28)
    axes[1].legend(loc="upper right")
    axes[1].set_xlabel("Interrupted high-pulse width")
    fig.suptitle("Short-pulse improvement is real, but coefficient error remains significant")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(PLOTS_DIR / "05_short_pulse_summary.png", dpi=180)
    plt.close(fig)


def write_csv(path: Path, row: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def write_readme(values: dict[str, float]) -> None:
    lines = [
        "# Coefficient-State Interrupted Switching Demo",
        "",
        f"This demo uses `{INTERRUPTED_CASE}` to inspect the experimental `InputDrivenCoeffState` algorithm against HSPICE native IBIS and legacy pybis.",
        "",
        "The input rises at about 5 ns and falls again at about 6 ns, before the normal output transition settles.",
        "",
        "## Figures",
        "",
        "- `figures/01_interrupted_event_timeline.png`: input, pad, Ku/Kd, and CoeffState target/state diagnostics.",
        "- `figures/02_ku_kd_state_difference.png`: focused Ku/Kd comparison for the interrupted event.",
        "- `figures/03_pad_consequence.png`: how the coefficient behavior maps into pad waveform error.",
        "- `figures/04_control_vs_interrupted.png`: normal full-toggle control versus interrupted switching.",
        "- `figures/05_short_pulse_summary.png`: all short-pulse widths from the coefficient-state sweep.",
        "",
        "## Key Numbers",
        "",
        f"- Settled high from the normal full-toggle bench: `{values['settled_high_v']:.3f} V`.",
        f"- At the reverse command, HSPICE pad is only `{values['hspice_pad_at_reverse_v']:.3f} V`, so the output is not settled.",
        f"- HSPICE Ku peak: `{values['hspice_ku_peak']:.3f}`.",
        f"- Legacy pybis Ku peak: `{values['legacy_ku_peak']:.3f}`.",
        f"- CoeffState Ku peak: `{values['coeff_ku_peak']:.3f}`.",
        f"- HSPICE pad peak: `{values['hspice_pad_peak_v']:.3f} V`.",
        f"- Legacy pybis pad peak: `{values['legacy_pad_peak_v']:.3f} V`.",
        f"- CoeffState pad peak: `{values['coeff_pad_peak_v']:.3f} V`.",
        f"- Legacy pad RMSE: `{values['legacy_pad_rmse_v'] * 1e3:.1f} mV`.",
        f"- CoeffState pad RMSE: `{values['coeff_pad_rmse_v'] * 1e3:.1f} mV`.",
        f"- Legacy max Ku/Kd RMSE: `{max(values['legacy_ku_rmse'], values['legacy_kd_rmse']):.3f}`.",
        f"- CoeffState max Ku/Kd RMSE: `{max(values['coeff_ku_rmse'], values['coeff_kd_rmse']):.3f}`.",
        "",
        "## Interpretation",
        "",
        "The new algorithm fixes the worst legacy failure mode: Ku no longer plays a full transition after a very short pulse. The pad pulse is much smaller and closer to HSPICE.",
        "",
        "However, it is still not correct enough to become the default. In this 1 ns case, CoeffState Ku is still higher than HSPICE, and Kd recovers smoothly instead of reproducing HSPICE's sharper dip/recovery shape.",
        "",
        "The control-vs-interrupted figure also shows the tradeoff: the branch-state model helps interrupted pulses, but the full-toggle case regresses compared with legacy pybis. The next algorithm should therefore be hybrid or event-aware: keep legacy behavior for complete edges, and use coefficient-state correction only when a retrigger is detected before the previous transition settles.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> int:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    control = read_case(CONTROL_CASE)
    short = read_case(INTERRUPTED_CASE)
    values = metrics(control, short)

    plot_interrupted_timeline(short, values)
    plot_ku_kd_focus(short, values)
    plot_pad_consequence(short, values)
    plot_control_vs_interrupted(control, short)
    plot_short_pulse_summary()
    write_csv(OUT_DIR / "demo_metrics.csv", values)
    write_readme(values)

    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"FIGURES={PLOTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
