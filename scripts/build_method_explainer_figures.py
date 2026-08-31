#!/usr/bin/env python3
"""Four figures answering two questions with pictures instead of prose.

What the transistor-derived Ku/Kd bought us -- three things, one figure each:

  q2_01  a grading target that is not native IBIS's opinion. On inv_chain
         short-high the transistor produces no pulse at all and native IBIS
         produces 0.93 V, so a recovery law fitted to native IBIS would be
         fitted to an artifact.

  q2_02  proof that io_buf's 1.76 ns pullup-off-to-pulldown-on gap is real
         device behaviour and not a fitting bug. Silicon's own Kd does not move
         until 2.05 ns after the edge. This is what reversed the recommendation
         on delay_cmd: reproducing the gap is correct, and the shipped model
         fills it with a driver that is not there.

  q2_03  where the defect actually lives. The model's Ku bump after a reversal
         looks 2.2x too tall against silicon, but subtracting the stranded-charge
         pedestal leaves it within 4%. The reversal law was right; the command
         layer was wrong. Without silicon Ku/Kd we would have gone hunting in
         the wrong place.

How the level-driven command works, against the one it replaces:

  q3_01  the same case through both command layers, one row per stage, from the
         input level down to the pad.

    py -3.14 scripts/build_method_explainer_figures.py
"""
from __future__ import annotations

import argparse
import csv
import glob
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / ".codex_deps" / "presentation" / "python", ROOT / "scripts"):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
SWEEP = ROOT / "results" / "three_buffer_native_anchored_stress_sweep_2026-08-19"
SILICON_DIR = ROOT / "results" / "silicon_kukd_conditioning_2026-08-27" / "waveforms"
RECOVERY = ROOT / "results" / "silicon_kukd_recovery_uniform_2026-08-27" / "waveforms"
PROBE = ROOT / "results" / "settled_offset_diagnosis_2026-08-27" / "command_probe"
OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27" / "explainers"

SILICON = "#111111"
NATIVE = "#2B6CA3"
SHIPPED = "#C05621"
LEVEL = "#1B6B4F"
GREY = "#8A8A8A"
DPI = 170

# io_buf typical corner, from the fit.
PU_OFF_DELAY, PD_ON_DELAY = 0.0677, 1.8313


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) if x not in ("", "nan") else np.nan for x in r]
                       for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(rows[0])}


def style(axis, ylabel=None, title=None):
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=11)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")
    if ylabel:
        axis.set_ylabel(ylabel, fontsize=12)
    if title:
        axis.set_title(title, fontsize=15, fontweight="bold", pad=10)


def grading_target(path: Path) -> str:
    """inv_chain short-high: the transistor produces nothing, native IBIS a pulse."""
    d = load(SWEEP / "figures" / "inv_chain" / "short_high" / "swing_50" / "waveforms.csv")
    t = d["time_ns"]
    fig, axis = plt.subplots(figsize=(12.4, 5.6))
    axis.plot(t, d["hspice_transistor_pad_v"], color=SILICON, lw=3.4,
              label="HSPICE transistor")
    axis.plot(t, d["hspice_native_pad_v"], color=NATIVE, lw=2.4,
              label="HSPICE native IBIS")
    axis.set_xlim(4.8, 8.0)
    axis.set_xlabel("Time (ns)", fontsize=12)
    style(axis, "Pad (V)", "inv_chain  |  short high  |  50% target")
    axis.legend(fontsize=12, loc="upper right", framealpha=0.95)
    axis.axhline(0.0, color=GREY, lw=1.0)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    m = (t > 4.5) & (t < 9.0)
    return (f"transistor peak {np.nanmax(d['hspice_transistor_pad_v'][m]):.4f} V, "
            f"native IBIS {np.nanmax(d['hspice_native_pad_v'][m]):.4f} V")


def dead_zone_is_real(path: Path) -> str:
    """Silicon's own coefficients show the gap between the two devices."""
    d = load(SILICON_DIR / "io_buf_full_transition.csv")
    t = d["time_ns"]
    edge = 15.0
    fig, axis = plt.subplots(figsize=(12.4, 6.0))
    axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
    axis.plot(t, d["silicon_ku"], color="#B4680A", lw=3.0, label="silicon Ku  (pullup)")
    axis.plot(t, d["silicon_kd"], color=NATIVE, lw=3.0, label="silicon Kd  (pulldown)")
    axis.axvspan(edge + PU_OFF_DELAY, edge + PD_ON_DELAY, color="#D9534F",
                 alpha=0.13, lw=0, zorder=1,
                 label=f"neither device on  ({PD_ON_DELAY - PU_OFF_DELAY:.2f} ns)")
    axis.axvline(edge, color=GREY, ls="--", lw=1.6)
    axis.set_xlim(14.8, 18.4)
    axis.set_ylim(-0.2, 1.2)
    axis.set_xlabel("Time (ns)", fontsize=12)
    style(axis, "coefficient",
          "io_buf  |  full transition  |  falling edge  |  Ku and Kd from silicon")
    axis.legend(fontsize=11.5, loc="center right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)

    def crossing(y, level):
        for i in range(1, len(y)):
            if y[i - 1] < level <= y[i]:
                return float(t[i])
        return float("nan")
    return (f"silicon Kd reaches 50% at {crossing(d['silicon_kd'], 0.5) - edge:.2f} ns "
            f"after the edge; the fit says pd_on_delay = {PD_ON_DELAY:.4f} ns")


def bump_on_pedestal(path: Path) -> str:
    """The model's reversal bump is right; it is sitting on stranded charge."""
    d = load(RECOVERY / "io_buf_short_high_70.csv")
    t = d["time_ns"]
    t_rev = 7.2095
    tail = (t >= t_rev + 2.8) & (t <= t_rev + 4.0)
    pedestal = float(np.nanmean(d["model_ku"][tail]))

    fig, axes = plt.subplots(2, 1, figsize=(12.4, 8.0), sharex=True)
    for axis in axes:
        axis.axvline(t_rev, color=GREY, ls="--", lw=1.6)
        axis.set_xlim(t_rev + 0.3, t_rev + 4.2)
        # The whole event lives under Ku = 0.15; the default range buries it.
        axis.set_ylim(-0.09, 0.15)
        style(axis)
    axes[0].plot(t, d["silicon_ku"], color=SILICON, lw=3.0, label="silicon")
    axes[0].plot(t, d["native_ku"], color=NATIVE, lw=2.2, label="native IBIS")
    axes[0].plot(t, d["model_ku"], color=SHIPPED, lw=2.4, label="gate-state, as shipped")
    axes[0].axhline(pedestal, color=SHIPPED, ls=":", lw=1.8)
    axes[0].set_ylabel("Ku", fontsize=13)
    style(axes[0], "Ku", "io_buf  |  short high  |  70% target  |  Ku after the reversal")
    axes[0].legend(fontsize=11.5, loc="upper right", framealpha=0.95)

    axes[1].plot(t, d["silicon_ku"], color=SILICON, lw=3.0, label="silicon")
    axes[1].plot(t, d["model_ku"] - pedestal, color=SHIPPED, lw=2.4,
                 label="gate-state, with the pedestal subtracted")
    axes[1].axhline(0.0, color=GREY, lw=1.0)
    axes[1].set_ylabel("Ku", fontsize=13)
    axes[1].set_xlabel("Time (ns)", fontsize=12)
    axes[1].legend(fontsize=11.5, loc="upper right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)

    window = (t >= t_rev + 1.0) & (t <= t_rev + 3.0)
    sil_peak = float(np.nanmax(d["silicon_ku"][window]))
    mod_peak = float(np.nanmax(d["model_ku"][window]))
    return (f"model peak {mod_peak:.4f} - pedestal {pedestal:.4f} = "
            f"{mod_peak - pedestal:.4f}, against silicon {sil_peak:.4f}")


def delay_cmd_chain(path: Path) -> str:
    """The same case through both command layers, stage by stage."""
    width_ps, target = 1792, 60
    t_rev = 5.0 + width_ps / 1000.0
    shipped = load(PROBE / f"swing_{target}_w{width_ps}ps.csv")

    hits = glob.glob(str(MATRIX / "delay_cmd" / "ngspice_runs" / "io_buf" / "*" / "*" /
                         "cases" / f"short_high_w{width_ps}ps_*" /
                         "ngspice_gate_state" / "run.raw"))
    raw = parse_ngspice_raw(Path(hits[0]))
    keys = {k.lower(): k for k in raw}
    tl = np.asarray(raw[keys["time"]]) * 1e9

    def node(name):
        return np.asarray(raw[keys[f"v(xdrv.{name})"]])

    panels = [
        ("input level\nNINX", None, node("ninx"), (-0.1, 1.15)),
        ("command\nGUPCMD", shipped["gupcmd"], node("gupcmd"), (-0.1, 1.15)),
        ("after the clamp\nGUPTARGET", shipped["guptarget"], node("guptarget"), (-0.1, 1.15)),
        ("Ku", shipped["ku"], node("ku"), (-0.1, 0.8)),
        ("Pad (V)", shipped["pad"], np.asarray(raw[keys["v(pad)"]]), (-0.08, 1.0)),
    ]

    fig, axes = plt.subplots(len(panels), 1, figsize=(12.6, 13.0), sharex=True)
    for axis, (label, old, new, ylim) in zip(axes, panels):
        if old is None:
            # The input is the same stimulus in both builds, so it gets one
            # neutral trace rather than a colour that implies one of them.
            axis.plot(tl, new, color=SILICON, lw=2.4, label="the input, common to both")
            axis.legend(fontsize=11.5, loc="upper right", framealpha=0.95)
            axis.set_ylim(*ylim)
            axis.set_xlim(4.7, 11.5)
            axis.axvline(5.0, color=GREY, ls=":", lw=1.5)
            axis.axvline(t_rev, color=GREY, ls="--", lw=1.7)
            style(axis, label)
            continue
        axis.plot(shipped["time_ns"], old, color=SHIPPED, lw=2.6,
                  label="edge-integrating command (shipped)")
        axis.plot(tl, new, color=LEVEL, lw=2.2, ls=(0, (5, 2.2)),
                  label="level command (delay_cmd)")
        axis.axvline(5.0, color=GREY, ls=":", lw=1.5)
        axis.axvline(t_rev, color=GREY, ls="--", lw=1.7)
        axis.set_ylim(*ylim)
        axis.set_xlim(4.7, 11.5)
        style(axis, label)
    axes[0].set_title(f"io_buf  |  short high  |  {width_ps} ps  |  "
                      "the command layer, stage by stage",
                      fontsize=15, fontweight="bold", pad=11)
    axes[1].legend(fontsize=11.5, loc="upper right", framealpha=0.95)
    axes[-1].set_xlabel("Time (ns)", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)

    hold = (shipped["time_ns"] >= t_rev + 1.0) & (shipped["time_ns"] <= t_rev + 1.7)
    hold_l = (tl >= t_rev + 1.0) & (tl <= t_rev + 1.7)
    return (f"settled GUPCMD -- shipped {shipped['gupcmd'][hold].mean():+.5f}, "
            f"level {node('gupcmd')[hold_l].mean():+.5f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("q2_01_grading_target.png", grading_target,
         "why silicon Ku/Kd is the right target"),
        ("q2_02_dead_zone_is_real.png", dead_zone_is_real,
         "why the 1.76 ns gap is device behaviour"),
        ("q2_03_bump_on_a_pedestal.png", bump_on_pedestal,
         "where the defect actually lives"),
        ("q3_01_command_layer_stages.png", delay_cmd_chain,
         "how the level command differs"),
    ]
    for name, builder, headline in jobs:
        print(f"{name:<34}{headline}")
        print(f"{'':<34}{builder(out / name)}")
    print(f"\nwrote {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
