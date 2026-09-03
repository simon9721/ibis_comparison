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

from run_io_buf_switching_coeff_sweep import build_cases, build_pwl_points  # noqa: E402


STUDY_DIR = ROOT / "results" / "io_buf_switching_coeff_sweep_2026-06-19"
OUT_DIR = STUDY_DIR / "interrupted_switching_demo"
PLOTS_DIR = OUT_DIR / "figures"
CONTROL_CASE = "edge_1ps_base_50r_2pf"
INTERRUPTED_CASE = "short_pulse_2ns_high"


def read_waveform(case_id: str) -> dict[str, np.ndarray]:
    path = STUDY_DIR / "cases" / case_id / "aligned_waveforms.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows: dict[str, list[float]] = {field: [] for field in fields}
        for row in reader:
            for field in fields:
                rows[field].append(float(row[field]))
    return {field: np.asarray(values, dtype=float) for field, values in rows.items()}


def interp(t: np.ndarray, y: np.ndarray, x: float) -> float:
    return float(np.interp(x, t, y))


def input_waveform(case_id: str, t: np.ndarray) -> np.ndarray:
    case = {case.case_id: case for case in build_cases()}[case_id]
    points = build_pwl_points(case)
    xp = np.asarray([p[0] for p in points], dtype=float)
    yp = np.asarray([p[1] for p in points], dtype=float)
    return np.interp(t, xp, yp)


def settled_high_reference(control: dict[str, np.ndarray]) -> float:
    t = control["time_ns"]
    y = control["hspice_pad_v"]
    mask = (t >= 11.0) & (t <= 14.0)
    return float(np.median(y[mask]))


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def mark_commands(axes, rise_50: float = 5.0005, fall_50: float = 7.0005) -> None:
    for ax in np.ravel(axes):
        ax.axvline(rise_50, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvline(fall_50, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvspan(rise_50, fall_50, color="#f2c94c", alpha=0.14, lw=0)


def plot_interrupted_timeline(short: dict[str, np.ndarray], high_ref: float, metrics: dict[str, float]) -> None:
    t = short["time_ns"]
    vin = input_waveform(INTERRUPTED_CASE, t)
    h_pad = short["hspice_pad_v"]
    n_pad = short["ngspice_pybis_pad_v_interp"]
    h_ku = short["hspice_ku"]
    n_ku = short["ngspice_pybis_ku_interp"]
    h_kd = short["hspice_kd"]
    n_kd = short["ngspice_pybis_kd_interp"]

    fig, axes = plt.subplots(3, 1, figsize=(11, 8.2), sharex=True, height_ratios=[0.8, 1.15, 1.25])
    mark_commands(axes)

    axes[0].plot(t, vin, color="black", lw=2.0)
    axes[0].set_ylim(-0.25, 3.55)
    style(axes[0], "Input (V)")
    axes[0].annotate("rise command", xy=(5.0005, 3.05), xytext=(4.75, 2.35), arrowprops={"arrowstyle": "->", "lw": 1.1})
    axes[0].annotate("reverse command before output settles", xy=(7.0005, 3.05), xytext=(7.35, 2.2), arrowprops={"arrowstyle": "->", "lw": 1.1})

    axes[1].plot(t, h_pad, lw=2.2, label="HSPICE native IBIS")
    axes[1].plot(t, n_pad, lw=2.0, ls="--", label="ngspice pybis")
    axes[1].axhline(high_ref, color="0.25", lw=1.1, ls="--", alpha=0.75, label="settled high from full toggle")
    style(axes[1], "Pad (V)")
    axes[1].legend(loc="lower right")
    axes[1].annotate(
        f"At reverse command,\npad is only {metrics['pad_at_reverse_hspice_v']:.2f} V\nvs settled high {high_ref:.2f} V",
        xy=(7.0005, metrics["pad_at_reverse_hspice_v"]),
        xytext=(7.55, 0.42),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[1].annotate(
        f"pybis pad peak {metrics['ngspice_pad_peak_v']:.2f} V\nHSPICE peak {metrics['hspice_pad_peak_v']:.2f} V",
        xy=(7.45, metrics["ngspice_pad_peak_v"]),
        xytext=(8.15, 1.2),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )

    axes[2].plot(t, h_ku, lw=2.0, label="HSPICE Ku")
    axes[2].plot(t, n_ku, lw=2.0, ls="--", label="pybis Ku")
    axes[2].plot(t, h_kd, lw=2.0, label="HSPICE Kd")
    axes[2].plot(t, n_kd, lw=2.0, ls="--", label="pybis Kd")
    axes[2].set_ylim(-0.12, 1.12)
    style(axes[2], "Coeff")
    axes[2].set_xlabel("Time (ns)")
    axes[2].legend(loc="center right", ncol=2)
    axes[2].annotate(
        "same initial Kd turn-off",
        xy=(6.65, 0.5),
        xytext=(5.15, 0.42),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
    )
    axes[2].annotate(
        "Ku histories split\nafter reverse command",
        xy=(7.28, metrics["hspice_ku_peak"]),
        xytext=(8.1, 0.32),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )

    axes[2].set_xlim(4.6, 10.4)
    fig.suptitle("Interrupted switching demo: second command arrives before previous output settles")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(PLOTS_DIR / "01_interrupted_event_timeline.png", dpi=180)
    plt.close(fig)


def plot_ku_state_difference(short: dict[str, np.ndarray], metrics: dict[str, float]) -> None:
    t = short["time_ns"]
    h_ku = short["hspice_ku"]
    n_ku = short["ngspice_pybis_ku_interp"]
    h_kd = short["hspice_kd"]
    n_kd = short["ngspice_pybis_kd_interp"]

    fig, axes = plt.subplots(2, 1, figsize=(10.8, 6.6), sharex=True)
    mark_commands(axes)
    axes[0].plot(t, h_ku, lw=2.4, label="HSPICE Ku")
    axes[0].plot(t, n_ku, lw=2.2, ls="--", label="pybis Ku")
    axes[0].axhline(metrics["hspice_ku_peak"], color="C0", lw=1.0, ls=":")
    axes[0].axhline(metrics["ngspice_ku_peak"], color="C1", lw=1.0, ls=":")
    style(axes[0], "Ku")
    axes[0].set_ylim(-0.08, 1.08)
    axes[0].legend(loc="upper right")
    axes[0].annotate(
        f"HSPICE Ku stays partial\npeak {metrics['hspice_ku_peak']:.2f}",
        xy=(metrics["hspice_ku_peak_time_ns"], metrics["hspice_ku_peak"]),
        xytext=(7.9, 0.48),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[0].annotate(
        f"pybis Ku reaches near full on\npeak {metrics['ngspice_ku_peak']:.2f}",
        xy=(metrics["ngspice_ku_peak_time_ns"], metrics["ngspice_ku_peak"]),
        xytext=(7.72, 0.82),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )

    axes[1].plot(t, h_kd, lw=2.4, label="HSPICE Kd")
    axes[1].plot(t, n_kd, lw=2.2, ls="--", label="pybis Kd")
    style(axes[1], "Kd")
    axes[1].set_ylim(-0.1, 1.08)
    axes[1].legend(loc="lower right")
    axes[1].annotate(
        f"Kd recovery: pybis about {metrics['kd_recovery_delta_ps']:.0f} ps later",
        xy=(9.5, 0.5),
        xytext=(7.9, 0.22),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_xlim(6.0, 10.4)
    fig.suptitle("Coefficient-state difference after interrupted switching")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(PLOTS_DIR / "02_ku_kd_state_difference.png", dpi=180)
    plt.close(fig)


def plot_pad_consequence(short: dict[str, np.ndarray], metrics: dict[str, float], high_ref: float) -> None:
    t = short["time_ns"]
    h_pad = short["hspice_pad_v"]
    n_pad = short["ngspice_pybis_pad_v_interp"]
    mask = (t >= 5.6) & (t <= 10.6)

    fig, ax = plt.subplots(figsize=(10.8, 5.3))
    mark_commands([ax])
    ax.plot(t, h_pad, lw=2.4, label="HSPICE native IBIS")
    ax.plot(t, n_pad, lw=2.2, ls="--", label="ngspice pybis")
    ax.fill_between(t[mask], h_pad[mask], n_pad[mask], color="#eb5757", alpha=0.18, label="waveform mismatch area")
    ax.axhline(high_ref, color="0.25", lw=1.0, ls="--", alpha=0.75, label="settled high from full toggle")
    style(ax, "Pad voltage (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_xlim(5.5, 10.5)
    ax.set_ylim(-0.08, 1.65)
    ax.legend(loc="upper right")
    ax.annotate(
        f"HSPICE partial pulse\npeak {metrics['hspice_pad_peak_v']:.2f} V",
        xy=(metrics["hspice_pad_peak_time_ns"], metrics["hspice_pad_peak_v"]),
        xytext=(6.1, 0.95),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.annotate(
        f"pybis near-full pulse\npeak {metrics['ngspice_pad_peak_v']:.2f} V",
        xy=(metrics["ngspice_pad_peak_time_ns"], metrics["ngspice_pad_peak_v"]),
        xytext=(8.2, 1.27),
        arrowprops={"arrowstyle": "->", "lw": 1.1},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.75", "alpha": 0.92},
    )
    ax.set_title("Pad consequence: partial HSPICE state vs near-full pybis pull-up")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "03_pad_consequence.png", dpi=180)
    plt.close(fig)


def plot_control_vs_interrupted(control: dict[str, np.ndarray], short: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.2, 7.2), sharex="col")

    ct = control["time_ns"]
    st = short["time_ns"]
    control_vin = input_waveform(CONTROL_CASE, ct)
    short_vin = input_waveform(INTERRUPTED_CASE, st)

    axes[0, 0].plot(ct, control_vin / 3.3, color="black", lw=1.6, label="input / 3.3")
    axes[0, 0].plot(ct, control["hspice_pad_v"], lw=2.0, label="HSPICE pad")
    axes[0, 0].plot(ct, control["ngspice_pybis_pad_v_interp"], lw=1.8, ls="--", label="pybis pad")
    axes[0, 0].set_title("Control: complete full toggle")
    style(axes[0, 0], "Pad / input")
    axes[0, 0].legend(loc="upper right")
    axes[0, 0].set_xlim(4.7, 18.5)

    axes[1, 0].plot(ct, control["hspice_ku"], lw=2.0, label="HSPICE Ku")
    axes[1, 0].plot(ct, control["ngspice_pybis_ku_interp"], lw=1.8, ls="--", label="pybis Ku")
    axes[1, 0].plot(ct, control["hspice_kd"], lw=2.0, label="HSPICE Kd")
    axes[1, 0].plot(ct, control["ngspice_pybis_kd_interp"], lw=1.8, ls="--", label="pybis Kd")
    style(axes[1, 0], "Coeff")
    axes[1, 0].set_ylim(-0.1, 1.1)
    axes[1, 0].set_xlabel("Time (ns)")
    axes[1, 0].legend(loc="center right", ncol=2)

    axes[0, 1].plot(st, short_vin / 3.3, color="black", lw=1.6, label="input / 3.3")
    axes[0, 1].plot(st, short["hspice_pad_v"], lw=2.0, label="HSPICE pad")
    axes[0, 1].plot(st, short["ngspice_pybis_pad_v_interp"], lw=1.8, ls="--", label="pybis pad")
    axes[0, 1].set_title("Interrupted: command reverses before settling")
    style(axes[0, 1], "Pad / input")
    axes[0, 1].legend(loc="upper right")
    axes[0, 1].set_xlim(4.7, 10.6)

    axes[1, 1].plot(st, short["hspice_ku"], lw=2.0, label="HSPICE Ku")
    axes[1, 1].plot(st, short["ngspice_pybis_ku_interp"], lw=1.8, ls="--", label="pybis Ku")
    axes[1, 1].plot(st, short["hspice_kd"], lw=2.0, label="HSPICE Kd")
    axes[1, 1].plot(st, short["ngspice_pybis_kd_interp"], lw=1.8, ls="--", label="pybis Kd")
    style(axes[1, 1], "Coeff")
    axes[1, 1].set_ylim(-0.1, 1.1)
    axes[1, 1].set_xlabel("Time (ns)")
    axes[1, 1].legend(loc="center right", ncol=2)

    for ax in axes[:, 1]:
        ax.axvline(5.0005, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvline(7.0005, color="0.2", lw=1.0, ls=":", alpha=0.85)
        ax.axvspan(5.0005, 7.0005, color="#f2c94c", alpha=0.14, lw=0)

    fig.suptitle("Control vs interrupted switching: same IBIS, different event history")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(PLOTS_DIR / "04_control_vs_interrupted.png", dpi=180)
    plt.close(fig)


def metrics(control: dict[str, np.ndarray], short: dict[str, np.ndarray]) -> dict[str, float]:
    t = short["time_ns"]
    h_pad = short["hspice_pad_v"]
    n_pad = short["ngspice_pybis_pad_v_interp"]
    h_ku = short["hspice_ku"]
    n_ku = short["ngspice_pybis_ku_interp"]
    h_kd = short["hspice_kd"]
    n_kd = short["ngspice_pybis_kd_interp"]

    mask = (t >= 5.0) & (t <= 10.2)
    h_ku_local = h_ku[mask]
    n_ku_local = n_ku[mask]
    h_kd_local = h_kd[mask]
    n_kd_local = n_kd[mask]
    t_local = t[mask]
    h_pad_local = h_pad[mask]
    n_pad_local = n_pad[mask]
    h_ku_i = int(np.argmax(h_ku_local))
    n_ku_i = int(np.argmax(n_ku_local))
    h_pad_i = int(np.argmax(h_pad_local))
    n_pad_i = int(np.argmax(n_pad_local))

    # From mismatch_event_timing.csv: event 2 Kd 50% recovery delta.
    event_path = STUDY_DIR / "mismatch_analysis" / "mismatch_event_timing.csv"
    kd_recovery_delta = float("nan")
    if event_path.exists():
        with event_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if (
                    row["case_id"] == INTERRUPTED_CASE
                    and row["event_index"] == "2"
                    and row["coefficient"] == "kd"
                ):
                    kd_recovery_delta = float(row["ng_minus_h_50pct_ps"])
                    break

    return {
        "settled_high_v": settled_high_reference(control),
        "pad_at_reverse_hspice_v": interp(t, h_pad, 7.0005),
        "pad_at_reverse_ngspice_v": interp(t, n_pad, 7.0005),
        "hspice_pad_peak_v": float(h_pad_local[h_pad_i]),
        "hspice_pad_peak_time_ns": float(t_local[h_pad_i]),
        "ngspice_pad_peak_v": float(n_pad_local[n_pad_i]),
        "ngspice_pad_peak_time_ns": float(t_local[n_pad_i]),
        "hspice_ku_peak": float(h_ku_local[h_ku_i]),
        "hspice_ku_peak_time_ns": float(t_local[h_ku_i]),
        "ngspice_ku_peak": float(n_ku_local[n_ku_i]),
        "ngspice_ku_peak_time_ns": float(t_local[n_ku_i]),
        "hspice_kd_min": float(np.min(h_kd_local)),
        "ngspice_kd_min": float(np.min(n_kd_local)),
        "kd_recovery_delta_ps": kd_recovery_delta,
    }


def write_csv(path: Path, row: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def write_readme(values: dict[str, float]) -> None:
    lines = [
        "# Interrupted Switching Demo",
        "",
        "This demo shows why the `short_pulse_2ns_high` case mismatches between HSPICE native IBIS and ngspice pybis.",
        "",
        "The second input command arrives before the first output transition settles. That makes the switching coefficient history matter.",
        "",
        "## Figures",
        "",
        "- `figures/01_interrupted_event_timeline.png`: input command, pad voltage, and Ku/Kd coefficients on the same time axis.",
        "- `figures/02_ku_kd_state_difference.png`: focused view of the coefficient-state split.",
        "- `figures/03_pad_consequence.png`: output waveform consequence of the coefficient split.",
        "- `figures/04_control_vs_interrupted.png`: normal full-toggle control vs interrupted switching.",
        "",
        "## Key Numbers",
        "",
        f"- Settled high from the normal full-toggle bench: `{values['settled_high_v']:.3f} V`.",
        f"- At the reverse command, HSPICE pad is only `{values['pad_at_reverse_hspice_v']:.3f} V`, so the previous transition is not settled.",
        f"- HSPICE Ku peak during interrupted pulse: `{values['hspice_ku_peak']:.3f}`.",
        f"- pybis Ku peak during interrupted pulse: `{values['ngspice_ku_peak']:.3f}`.",
        f"- HSPICE pad peak: `{values['hspice_pad_peak_v']:.3f} V`.",
        f"- pybis pad peak: `{values['ngspice_pad_peak_v']:.3f} V`.",
        f"- Kd recovery 50 percent timing: pybis is about `{values['kd_recovery_delta_ps']:.0f} ps` later than HSPICE.",
        "",
        "## Interpretation",
        "",
        "HSPICE does not let the pull-up coefficient complete a normal full transition after the input reverses. Ku remains partial, and the pad produces a partial pulse.",
        "",
        "pybis allows Ku to reach near full strength before recovering. That creates a much larger output pulse. This is a state/history mismatch, not just a small timing offset.",
        "",
        "So the risk condition is: a new switching event arrives before the previous output transition has settled. In that case, coefficient history and native IBIS state-machine behavior become important.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> int:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    control = read_waveform(CONTROL_CASE)
    short = read_waveform(INTERRUPTED_CASE)
    values = metrics(control, short)
    high_ref = values["settled_high_v"]

    plot_interrupted_timeline(short, high_ref, values)
    plot_ku_state_difference(short, values)
    plot_pad_consequence(short, values, high_ref)
    plot_control_vs_interrupted(control, short)
    write_csv(OUT_DIR / "demo_metrics.csv", values)
    write_readme(values)

    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"FIGURES={PLOTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
