#!/usr/bin/env python3
"""Two figures: what the silicon extraction actually adds, and how the two
command layers differ mechanically.

An earlier version of this script drew three figures arguing for the silicon
Ku/Kd extraction. They were withdrawn because none of them needed it. The
native-IBIS-invents-a-pulse figure was a pad comparison, which requires no
coefficient extraction at all; the dead-zone figure repeated what the IBIS table
already says; and the bump-on-a-pedestal figure could have been drawn against
native IBIS Ku, whose bump peaks at 0.0469 against silicon's 0.0460.

So the question is answered by measurement instead. Silicon Ku/Kd and native
IBIS Ku/Kd are both available on all 17 recovery cases. Where they agree, the
extraction only confirmed what was already on hand; where they disagree over a
sustained stretch -- not merely at an edge, where silicon is known to be
unreliable -- it carries information nothing else does:

    io_buf short-high    slow-moving |dKu| = 0.0020   the offset cases
    io_buf short-low     slow-moving |dKu| = 0.2494   sustained 2.3 ns
    ex2    short-low     slow-moving |dKu| = 0.2023   sustained 0.6 ns

That is the honest split. On the cases this investigation was about, the
extraction added nothing. On short-low it disagrees with native IBIS by a
quarter of full scale for nanoseconds at a time, and that has not been used yet.

The command figure zooms to picosecond scale on the two instants where the
command changes, because that is where the mechanism is: the shipped block
integrates a 10 ps pulse and lands wherever the solver's timesteps put it, while
the level block steps to an exact rail.

    py -3.14 scripts/build_method_explainer_figures.py
"""
from __future__ import annotations

import argparse
import csv
import glob
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for q in (ROOT / ".codex_deps" / "presentation" / "python", ROOT / "scripts"):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
RECOVERY = ROOT / "results" / "silicon_kukd_recovery_uniform_2026-08-27" / "waveforms"
SCRATCH = Path(
    r"C:\Users\sh3qm\AppData\Local\Temp\claude"
    r"\c--Users-sh3qm-code-ibis-comparison\4830c25e-e99f-44a8-8aaf-2a359f268df1"
    r"\scratchpad\offset_fixes")
OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27" / "explainers"

SILICON = "#111111"
NATIVE = "#2B6CA3"
SHIPPED = "#C05621"
LEVEL = "#1B6B4F"
GREY = "#8A8A8A"
DPI = 170


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
        axis.set_ylabel(ylabel, fontsize=12.5)
    if title:
        axis.set_title(title, fontsize=14, fontweight="bold", pad=9)


def what_silicon_adds(path: Path) -> str:
    """Two cases side by side: one where the extraction was redundant, one not."""
    cases = [("io_buf_short_high_70", 7.2095, (6.9, 11.4),
              "io_buf  |  short high  |  70%"),
             ("io_buf_short_low_70", 10.242, (9.9, 14.4),
              "io_buf  |  short low  |  70%")]
    fig, axes = plt.subplots(2, 2, figsize=(14.6, 8.6))
    notes = []
    for col, (case, t_rev, window, title) in enumerate(cases):
        d = load(RECOVERY / f"{case}.csv")
        t = d["time_ns"]
        gap = d["silicon_ku"] - d["native_ku"]
        slew = np.abs(np.gradient(d["silicon_ku"], t))
        ok = np.isfinite(gap)
        quiet = ok & (slew < 0.5)
        notes.append(f"{case}: slow-moving |dKu| = {np.abs(gap[quiet]).mean():.4f}")

        top = axes[0, col]
        top.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        top.plot(t, d["silicon_ku"], color=SILICON, lw=3.0, label="silicon Ku")
        top.plot(t, d["native_ku"], color=NATIVE, lw=2.2, ls=(0, (5, 2.2)),
                 label="native IBIS Ku")
        top.set_ylim(-0.25, 1.15)
        style(top, "Ku", title)
        top.legend(fontsize=11, loc="upper right", framealpha=0.95)

        bottom = axes[1, col]
        bottom.fill_between(t, 0.0, gap, color=SHIPPED, alpha=0.30, lw=0)
        bottom.plot(t, gap, color=SHIPPED, lw=1.8)
        bottom.axhline(0.0, color=GREY, lw=1.0)
        bottom.set_ylim(-0.85, 0.55)
        style(bottom, "silicon Ku  -  native Ku")
        bottom.set_xlabel("Time (ns)", fontsize=12)

        for axis in (top, bottom):
            axis.axvline(t_rev, color=GREY, ls="--", lw=1.6)
            axis.set_xlim(*window)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return "   ".join(notes)


def how_the_command_differs(path: Path) -> str:
    """Picosecond zoom on the two instants where the command moves."""
    width_ps = 1792
    raw = parse_ngspice_raw(SCRATCH / "as_shipped_swing60" / "run.raw")
    keys = {k.lower(): k for k in raw}
    ts = np.asarray(raw[keys["time"]]) * 1e9
    shipped = np.asarray(raw[keys["v(xdrv.gupcmd)"]])

    hits = glob.glob(str(MATRIX / "delay_cmd" / "ngspice_runs" / "io_buf" / "*" / "*" /
                         "cases" / f"short_high_w{width_ps}ps_*" /
                         "ngspice_gate_state" / "run.raw"))
    raw_l = parse_ngspice_raw(Path(hits[0]))
    keys_l = {k.lower(): k for k in raw_l}
    tl = np.asarray(raw_l[keys_l["time"]]) * 1e9
    level = np.asarray(raw_l[keys_l["v(xdrv.gupcmd)"]])

    # The two instants the command moves: the input edge plus each fitted delay.
    rise_at = 5.0 + 0.9926
    fall_at = 5.0 + width_ps / 1000.0 + 0.0677
    panels = [("turn-on   target 1.000", rise_at, (0.90, 1.06)),
              ("turn-off   target 0.000", fall_at, (-0.02, 0.10))]

    fig, axes = plt.subplots(1, 3, figsize=(15.4, 5.6))
    for axis, (title, centre, ylim) in zip(axes[:2], panels):
        axis.plot(ts, shipped, color=SHIPPED, lw=2.6, marker="o", ms=3.4,
                  label="edge-integrating (shipped)")
        axis.plot(tl, level, color=LEVEL, lw=2.2, ls=(0, (4, 2)), marker="s", ms=3.0,
                  label="level command (delay_cmd)")
        axis.axhline(1.0 if centre == rise_at else 0.0, color=GREY, lw=1.2, ls=":")
        axis.set_xlim(centre - 0.030, centre + 0.045)
        axis.set_ylim(*ylim)
        style(axis, "GUPCMD", title)
        axis.set_xlabel("Time (ns)", fontsize=11.5)
    axes[0].legend(fontsize=10.5, loc="lower right", framealpha=0.95)

    axis = axes[2]
    axis.plot(ts, shipped, color=SHIPPED, lw=2.6)
    axis.plot(tl, level, color=LEVEL, lw=2.2, ls=(0, (4, 2)))
    axis.axhline(0.0, color=GREY, lw=1.2, ls=":")
    axis.set_xlim(6.7, 11.5)
    axis.set_ylim(-0.02, 0.10)
    style(axis, "GUPCMD", "what is left behind")
    axis.set_xlabel("Time (ns)", fontsize=11.5)

    fig.suptitle(f"io_buf  |  short high  |  {width_ps} ps  |  GUPCMD at the two "
                 "instants it moves, and what is left after",
                 fontsize=15, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=DPI)
    plt.close(fig)

    def at(t_arr, y, when):
        return float(np.interp(when, t_arr, y))
    return (f"after turn-on  shipped {at(ts, shipped, rise_at + 0.04):.5f}, "
            f"level {at(tl, level, rise_at + 0.04):.5f}   |   "
            f"after turn-off  shipped {at(ts, shipped, fall_at + 0.30):.5f}, "
            f"level {at(tl, level, fall_at + 0.30):.5f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    # The three withdrawn figures, removed so the folder does not carry an
    # argument the measurement does not support.
    for stale in ("q2_01_grading_target.png", "q2_02_dead_zone_is_real.png",
                  "q2_03_bump_on_a_pedestal.png", "q3_01_command_layer_stages.png"):
        (out / stale).unlink(missing_ok=True)

    jobs = [
        ("q2_what_silicon_kukd_adds.png", what_silicon_adds,
         "where the extraction is redundant, and where it is not"),
        ("q3_how_the_command_differs.png", how_the_command_differs,
         "integrate a pulse, or delay a level"),
    ]
    for name, builder, headline in jobs:
        print(f"{name:<36}{headline}")
        print(f"{'':<36}{builder(out / name)}")
    print(f"\nwrote {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
