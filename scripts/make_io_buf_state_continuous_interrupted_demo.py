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
from run_io_buf_state_continuous_retrigger import build_cases, build_pwl_points  # noqa: E402


STUDY_DIR = ROOT / "results" / "io_buf_state_continuous_retrigger_2026-06-20"
OUT_DIR = STUDY_DIR / "interrupted_switching_demo"
FIG_DIR = OUT_DIR / "figures"
PRIMARY_CASE = "short_pulse_1ns_high"
SECONDARY_CASE = "short_pulse_2ns_high"


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"Missing signal {names}; available: {sorted(data)}")


def to_ns(t_s: np.ndarray) -> np.ndarray:
    return np.asarray(t_s, dtype=float) * 1e9


def interp_to(t_src: np.ndarray, y_src: np.ndarray, t_dst: np.ndarray) -> np.ndarray:
    return np.interp(t_dst, t_src, y_src)


def load_case(case_id: str) -> dict[str, np.ndarray]:
    case_dir = STUDY_DIR / "cases" / case_id
    h = parse_hspice_tr0(case_dir / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0")
    legacy = parse_ngspice_raw(case_dir / "ngspice_legacy" / f"{case_id}_ngspice_legacy.raw")
    state = parse_ngspice_raw(case_dir / "ngspice_state_continuous" / f"{case_id}_ngspice_state_continuous.raw")

    ht = to_ns(find_signal(h, "time"))
    lt = to_ns(find_signal(legacy, "time"))
    st = to_ns(find_signal(state, "time"))

    return {
        "time_ns": ht,
        "input_v": find_signal(h, "v(in_dig)"),
        "h_pad": find_signal(h, "v(pad_ibis)"),
        "h_ku": find_signal(h, "v(ku)"),
        "h_kd": find_signal(h, "v(kd)"),
        "legacy_pad": interp_to(lt, find_signal(legacy, "v(pad)"), ht),
        "legacy_ku": interp_to(lt, find_signal(legacy, "v(xdrv.ku)", "v(xdrv:ku)"), ht),
        "legacy_kd": interp_to(lt, find_signal(legacy, "v(xdrv.kd)", "v(xdrv:kd)"), ht),
        "state_pad": interp_to(st, find_signal(state, "v(pad)"), ht),
        "state_ku": interp_to(st, find_signal(state, "v(xdrv.ku)", "v(xdrv:ku)"), ht),
        "state_kd": interp_to(st, find_signal(state, "v(xdrv.kd)", "v(xdrv:kd)"), ht),
        "state_pstate": interp_to(st, find_signal(state, "v(xdrv.pstate)", "v(xdrv:pstate)"), ht),
        "state_kutarget": interp_to(st, find_signal(state, "v(xdrv.kutarget)", "v(xdrv:kutarget)"), ht),
        "state_kdtarget": interp_to(st, find_signal(state, "v(xdrv.kdtarget)", "v(xdrv:kdtarget)"), ht),
    }


def case_meta(case_id: str):
    cases = {case.case_id: case for case in build_cases()}
    case = cases[case_id]
    points = build_pwl_points(case)
    transitions = []
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if abs(v1 - v0) > 1e-9:
            transitions.append((t0, t1, v0, v1))
    rise_t = transitions[0][0]
    fall_t = transitions[1][0]
    return case, rise_t, fall_t


def mask_between(t: np.ndarray, x0: float, x1: float) -> np.ndarray:
    return (t >= x0) & (t <= x1)


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def metrics(case_id: str, d: dict[str, np.ndarray]) -> dict[str, float]:
    _, rise_t, fall_t = case_meta(case_id)
    t = d["time_ns"]
    active = mask_between(t, rise_t - 0.25, fall_t + 3.0)
    reverse = float(fall_t)
    interrupted = mask_between(t, rise_t, fall_t + 3.0)
    return {
        "pad_at_reverse": float(np.interp(reverse, t, d["h_pad"])),
        "h_pad_peak": float(np.max(d["h_pad"][interrupted])),
        "legacy_pad_peak": float(np.max(d["legacy_pad"][interrupted])),
        "state_pad_peak": float(np.max(d["state_pad"][interrupted])),
        "h_ku_peak": float(np.max(d["h_ku"][interrupted])),
        "legacy_ku_peak": float(np.max(d["legacy_ku"][interrupted])),
        "state_ku_peak": float(np.max(d["state_ku"][interrupted])),
        "legacy_pad_rmse_mv": rmse(d["h_pad"][active], d["legacy_pad"][active]) * 1e3,
        "state_pad_rmse_mv": rmse(d["h_pad"][active], d["state_pad"][active]) * 1e3,
        "legacy_ku_rmse": rmse(d["h_ku"][active], d["legacy_ku"][active]),
        "state_ku_rmse": rmse(d["h_ku"][active], d["state_ku"][active]),
        "legacy_kd_rmse": rmse(d["h_kd"][active], d["legacy_kd"][active]),
        "state_kd_rmse": rmse(d["h_kd"][active], d["state_kd"][active]),
    }


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def mark_edges(axes, rise_t: float, fall_t: float) -> None:
    for ax in np.ravel(axes):
        ax.axvline(rise_t, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvline(fall_t, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvspan(rise_t, fall_t, color="#f2c94c", alpha=0.14, lw=0)


def plot_primary_timeline(case_id: str, d: dict[str, np.ndarray], m: dict[str, float]) -> None:
    _, rise_t, fall_t = case_meta(case_id)
    t = d["time_ns"]
    fig, axes = plt.subplots(4, 1, figsize=(11.2, 10.2), sharex=True, height_ratios=[0.7, 1.1, 1.15, 1.0])
    mark_edges(axes, rise_t, fall_t)

    axes[0].plot(t, d["input_v"], color="black", lw=2.0)
    axes[0].set_ylim(-0.25, 3.55)
    style(axes[0], "Input (V)")
    axes[0].annotate("rise", xy=(rise_t, 3.15), xytext=(rise_t - 0.45, 2.3), arrowprops={"arrowstyle": "->", "lw": 1.0})
    axes[0].annotate("reverse before settling", xy=(fall_t, 3.15), xytext=(fall_t + 0.25, 2.2), arrowprops={"arrowstyle": "->", "lw": 1.0})

    axes[1].plot(t, d["h_pad"], lw=2.2, label="HSPICE native IBIS")
    axes[1].plot(t, d["legacy_pad"], lw=1.9, ls="--", label="legacy pybis")
    axes[1].plot(t, d["state_pad"], lw=1.9, ls="-.", label="state-continuous pybis")
    style(axes[1], "Pad (V)")
    axes[1].legend(loc="upper right")
    axes[1].annotate(
        f"HSPICE partial pulse\npeak {m['h_pad_peak']:.2f} V",
        xy=(fall_t + 0.3, m["h_pad_peak"]),
        xytext=(fall_t + 1.1, 0.38),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[1].annotate(
        f"legacy pybis overdrives\npeak {m['legacy_pad_peak']:.2f} V",
        xy=(fall_t + 1.0, m["legacy_pad_peak"]),
        xytext=(fall_t + 1.55, 1.17),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[1].annotate(
        "state curve is small\nbecause drive is suppressed",
        xy=(fall_t + 0.55, max(m["state_pad_peak"], 0.02)),
        xytext=(fall_t + 2.15, 0.16),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )

    axes[2].plot(t, d["h_ku"], lw=2.0, color="#1f77b4", label="HSPICE Ku")
    axes[2].plot(t, d["h_kd"], lw=2.0, color="#d62728", label="HSPICE Kd")
    axes[2].plot(t, d["legacy_ku"], lw=1.7, ls="--", color="#1f77b4", label="legacy Ku")
    axes[2].plot(t, d["legacy_kd"], lw=1.7, ls="--", color="#d62728", label="legacy Kd")
    axes[2].plot(t, d["state_ku"], lw=1.7, ls="-.", color="#1f77b4", label="state Ku")
    axes[2].plot(t, d["state_kd"], lw=1.7, ls="-.", color="#d62728", label="state Kd")
    axes[2].set_ylim(-0.12, 1.15)
    style(axes[2], "Ku / Kd")
    axes[2].legend(loc="center right", ncol=3)

    axes[3].plot(t, d["state_pstate"], lw=2.0, label="PSTATE")
    axes[3].plot(t, d["state_kutarget"], lw=1.6, ls="--", label="KUTARGET")
    axes[3].plot(t, d["state_kdtarget"], lw=1.6, ls="--", label="KDTARGET")
    axes[3].set_ylim(-0.12, 1.15)
    style(axes[3], "State")
    axes[3].set_xlabel("Time (ns)")
    axes[3].legend(loc="best", ncol=3)

    axes[3].set_xlim(rise_t - 0.55, fall_t + 4.0)
    fig.suptitle(f"{case_id}: negative result - state-continuous suppresses drive instead of matching HSPICE coefficients")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG_DIR / "01_short_pulse_1ns_event_timeline.png", dpi=190)
    plt.close(fig)


def plot_ku_state(case_id: str, d: dict[str, np.ndarray], m: dict[str, float]) -> None:
    _, rise_t, fall_t = case_meta(case_id)
    t = d["time_ns"]
    fig, axes = plt.subplots(2, 1, figsize=(10.8, 6.8), sharex=True)
    mark_edges(axes, rise_t, fall_t)

    axes[0].plot(t, d["h_ku"], lw=2.3, label="HSPICE Ku")
    axes[0].plot(t, d["legacy_ku"], lw=2.0, ls="--", label="legacy pybis Ku")
    axes[0].plot(t, d["state_ku"], lw=2.0, ls="-.", label="state-continuous Ku")
    axes[0].set_ylim(-0.08, 1.12)
    style(axes[0], "Ku")
    axes[0].legend(loc="upper right")
    axes[0].annotate(
        f"legacy Ku peak {m['legacy_ku_peak']:.2f}",
        xy=(fall_t + 0.8, m["legacy_ku_peak"]),
        xytext=(fall_t + 1.35, 0.82),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[0].annotate(
        f"state Ku peak {m['state_ku_peak']:.2f}",
        xy=(fall_t + 0.25, m["state_ku_peak"]),
        xytext=(fall_t + 1.05, 0.32),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )

    axes[1].plot(t, d["h_kd"], lw=2.3, label="HSPICE Kd")
    axes[1].plot(t, d["legacy_kd"], lw=2.0, ls="--", label="legacy pybis Kd")
    axes[1].plot(t, d["state_kd"], lw=2.0, ls="-.", label="state-continuous Kd")
    axes[1].set_ylim(-0.12, 1.12)
    style(axes[1], "Kd")
    axes[1].legend(loc="lower right")
    axes[1].annotate(
        "wrong: state Kd stays on\nwhile HSPICE turns pulldown off",
        xy=(fall_t + 0.65, 1.0),
        xytext=(fall_t + 1.45, 0.56),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_xlim(rise_t - 0.25, fall_t + 3.8)
    fig.suptitle("Coefficient-state comparison: state-continuous is not matching HSPICE")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG_DIR / "02_short_pulse_1ns_ku_kd_state_difference.png", dpi=190)
    plt.close(fig)


def plot_pad_consequence(case_id: str, d: dict[str, np.ndarray], m: dict[str, float]) -> None:
    _, rise_t, fall_t = case_meta(case_id)
    t = d["time_ns"]
    fig, ax = plt.subplots(figsize=(10.8, 5.4))
    mark_edges([ax], rise_t, fall_t)
    ax.plot(t, d["h_pad"], lw=2.5, label="HSPICE native IBIS")
    ax.plot(t, d["legacy_pad"], lw=2.1, ls="--", label="legacy pybis")
    ax.plot(t, d["state_pad"], lw=2.1, ls="-.", label="state-continuous pybis")
    style(ax, "Pad voltage (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_xlim(rise_t - 0.35, fall_t + 4.0)
    ax.set_ylim(-0.08, 1.65)
    ax.legend(loc="upper right")
    ax.annotate(
        f"legacy RMSE {m['legacy_pad_rmse_mv']:.0f} mV",
        xy=(fall_t + 1.0, m["legacy_pad_peak"]),
        xytext=(fall_t + 1.65, 1.33),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.annotate(
        f"state pad RMSE {m['state_pad_rmse_mv']:.1f} mV\nbut coefficients are wrong",
        xy=(fall_t + 0.35, m["state_pad_peak"]),
        xytext=(fall_t + 1.25, 0.47),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.set_title("Pad-only metric false pass: state-continuous suppresses output by holding Kd on")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "03_short_pulse_1ns_pad_consequence.png", dpi=190)
    plt.close(fig)


def plot_2ns_limit(case_id: str, d: dict[str, np.ndarray], m: dict[str, float]) -> None:
    _, rise_t, fall_t = case_meta(case_id)
    t = d["time_ns"]
    fig, axes = plt.subplots(2, 1, figsize=(10.8, 7.0), sharex=True)
    mark_edges(axes, rise_t, fall_t)
    axes[0].plot(t, d["h_pad"], lw=2.4, label="HSPICE native IBIS")
    axes[0].plot(t, d["legacy_pad"], lw=2.0, ls="--", label="legacy pybis")
    axes[0].plot(t, d["state_pad"], lw=2.0, ls="-.", label="state-continuous pybis")
    style(axes[0], "Pad voltage (V)")
    axes[0].legend(loc="best")
    axes[0].set_title("2 ns short pulse: state-continuous still has wrong coefficient behavior")

    axes[1].plot(t, d["h_ku"], lw=2.2, color="#1f77b4", label="HSPICE Ku")
    axes[1].plot(t, d["legacy_ku"], lw=1.9, color="#1f77b4", ls="--", label="legacy Ku")
    axes[1].plot(t, d["state_ku"], lw=1.9, color="#1f77b4", ls="-.", label="state Ku")
    axes[1].plot(t, d["h_kd"], lw=2.2, color="#d62728", label="HSPICE Kd")
    axes[1].plot(t, d["legacy_kd"], lw=1.9, color="#d62728", ls="--", label="legacy Kd")
    axes[1].plot(t, d["state_kd"], lw=1.9, color="#d62728", ls="-.", label="state Kd")
    axes[1].set_ylim(-0.12, 1.15)
    style(axes[1], "Ku / Kd")
    axes[1].legend(loc="best", ncol=3)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_xlim(rise_t - 0.35, fall_t + 4.0)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "04_short_pulse_2ns_partial_improvement_limit.png", dpi=190)
    plt.close(fig)


def plot_summary(primary: dict[str, float], secondary: dict[str, float]) -> None:
    labels = ["1 ns short pulse", "2 ns short pulse"]
    legacy = [primary["legacy_pad_rmse_mv"], secondary["legacy_pad_rmse_mv"]]
    state = [primary["state_pad_rmse_mv"], secondary["state_pad_rmse_mv"]]
    legacy_kd = [primary["legacy_kd_rmse"], secondary["legacy_kd_rmse"]]
    state_kd = [primary["state_kd_rmse"], secondary["state_kd_rmse"]]
    x = np.arange(len(labels))
    width = 0.34
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.8))
    ax = axes[0]
    ax.bar(x - width / 2, legacy, width, label="legacy pybis")
    ax.bar(x + width / 2, state, width, label="state-continuous")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Pad RMSE vs HSPICE (mV)")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(loc="best")
    ax.set_title("Pad RMSE alone looks improved")
    for idx, (lval, sval) in enumerate(zip(legacy, state)):
        ax.text(idx - width / 2, lval + max(legacy) * 0.02, f"{lval:.0f}", ha="center", va="bottom")
        ax.text(idx + width / 2, sval + max(legacy) * 0.02, f"{sval:.0f}", ha="center", va="bottom")
    ax = axes[1]
    ax.bar(x - width / 2, legacy_kd, width, label="legacy pybis")
    ax.bar(x + width / 2, state_kd, width, label="state-continuous")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Kd RMSE vs HSPICE")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(loc="best")
    ax.set_title("Pulldown coefficient RMSE exposes the failure")
    for idx, (lval, sval) in enumerate(zip(legacy_kd, state_kd)):
        ymax = max(max(legacy_kd), max(state_kd))
        ax.text(idx - width / 2, lval + ymax * 0.02, f"{lval:.2f}", ha="center", va="bottom")
        ax.text(idx + width / 2, sval + ymax * 0.02, f"{sval:.2f}", ha="center", va="bottom")
    fig.suptitle("Interrupted-pulse result: the state-continuous algorithm is a false pass")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "05_short_pulse_rmse_summary.png", dpi=190)
    plt.close(fig)


def write_metrics_csv(rows: list[dict[str, object]]) -> None:
    path = OUT_DIR / "demo_metrics.csv"
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_readme(primary: dict[str, float], secondary: dict[str, float]) -> None:
    lines = [
        "# State-Continuous Interrupted Switching Demo - Negative Result",
        "",
        "This folder mirrors the older `io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo`, but adds the experimental state-continuous pybis curve.",
        "",
        "**Conclusion: the implemented state-continuous algorithm is not correct.** It can reduce pad-voltage RMSE in very short pulses, but it does that by suppressing the driver state rather than matching HSPICE `Ku/Kd` behavior.",
        "",
        "The clearest case is `short_pulse_1ns_high`: the falling command arrives before the pad has settled from the rising command.",
        "",
        "## Figures",
        "",
        "- `figures/01_short_pulse_1ns_event_timeline.png`: input command, pad waveform, Ku/Kd, and state diagnostics.",
        "- `figures/02_short_pulse_1ns_ku_kd_state_difference.png`: coefficient-state comparison.",
        "- `figures/03_short_pulse_1ns_pad_consequence.png`: waveform consequence of the coefficient behavior.",
        "- `figures/04_short_pulse_2ns_partial_improvement_limit.png`: the 2 ns case where improvement is only partial.",
        "- `figures/05_short_pulse_rmse_summary.png`: compact RMSE summary.",
        "",
        "## Key Numbers",
        "",
        "| Case | Legacy pad RMSE mV | State pad RMSE mV | Legacy Ku RMSE | State Ku RMSE | Legacy Kd RMSE | State Kd RMSE | HSPICE Ku peak | State Ku peak |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| short_pulse_1ns_high | {primary['legacy_pad_rmse_mv']:.1f} | {primary['state_pad_rmse_mv']:.1f} | {primary['legacy_ku_rmse']:.3f} | {primary['state_ku_rmse']:.3f} | {primary['legacy_kd_rmse']:.3f} | {primary['state_kd_rmse']:.3f} | {primary['h_ku_peak']:.3f} | {primary['state_ku_peak']:.3f} |",
        f"| short_pulse_2ns_high | {secondary['legacy_pad_rmse_mv']:.1f} | {secondary['state_pad_rmse_mv']:.1f} | {secondary['legacy_ku_rmse']:.3f} | {secondary['state_ku_rmse']:.3f} | {secondary['legacy_kd_rmse']:.3f} | {secondary['state_kd_rmse']:.3f} | {secondary['h_ku_peak']:.3f} | {secondary['state_ku_peak']:.3f} |",
        "",
        "## Interpretation",
        "",
        "Legacy pybis restarts the switching coefficient waveform on each input edge. In very short pulses, that can let Ku/Kd advance as if the previous transition were a clean full transition.",
        "",
        "The experimental state-continuous model used here is wrong because a single `PSTATE` is not a valid substitute for HSPICE's independent `Ku/Kd` event state. In the 1 ns case, HSPICE briefly turns the pulldown coefficient off and produces a small partial output pulse. The state-continuous model keeps `Kd` near 1 and `Ku` near 0, so the pad stays near 0 for the wrong reason.",
        "",
        "The apparent pad improvement is therefore a false pass. Coefficient agreement must be a hard gate for any retrigger algorithm, and this implementation fails that gate.",
        "",
        "## Root Cause",
        "",
        "- `PSTATE * rising_duration_ns` samples the rising table too early for short pulses, so `Ku` remains near zero.",
        "- `(1 - PSTATE) * falling_duration_ns` samples the falling table near its settled endpoint when `PSTATE` is still small, so `Kd` remains near one.",
        "- The algorithm treats IBIS waveform tables like normalized progress curves. They are not; they are event waveforms extracted under a fixture and HSPICE applies its own stateful switching logic.",
        "",
        "## Next Direction",
        "",
        "The next algorithm should fit or emulate HSPICE `Ku/Kd` trajectories directly. A candidate is a two-state coefficient ODE where each new edge changes the target and time constant from the current `Ku/Kd`, with coefficient continuity as the primary objective and pad waveform as a secondary check.",
        "",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    primary_data = load_case(PRIMARY_CASE)
    secondary_data = load_case(SECONDARY_CASE)
    primary_metrics = metrics(PRIMARY_CASE, primary_data)
    secondary_metrics = metrics(SECONDARY_CASE, secondary_data)

    plot_primary_timeline(PRIMARY_CASE, primary_data, primary_metrics)
    plot_ku_state(PRIMARY_CASE, primary_data, primary_metrics)
    plot_pad_consequence(PRIMARY_CASE, primary_data, primary_metrics)
    plot_2ns_limit(SECONDARY_CASE, secondary_data, secondary_metrics)
    plot_summary(primary_metrics, secondary_metrics)

    write_metrics_csv(
        [
            {"case_id": PRIMARY_CASE, **primary_metrics},
            {"case_id": SECONDARY_CASE, **secondary_metrics},
        ]
    )
    write_readme(primary_metrics, secondary_metrics)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
