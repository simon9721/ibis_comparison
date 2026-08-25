#!/usr/bin/env python3
"""Intro-slide figures: what Ku/Kd are, and where the short pulse breaks them.

Four figures telling one story on one buffer, so the audience tracks the same
two traces throughout:

    1  full swing, pad voltage      HSPICE native IBIS vs our ngspice model
    2  full swing, Ku and Kd        the same agreement, in the coefficients
    3  short pulse, pad voltage     where it stops agreeing
    4  short pulse, Ku and Kd       why: the legacy model restarts the opposite
                                    table from its beginning at the reverse edge

The model is `pybis2spice` in its shipped `InputDriven` mode -- the converter
before any interruption handling. Slides call it "ngspice" because on an intro
slide the tool matters and the mode does not.

Both traces come from the same joint record the rest of the study uses, so the
grid is identical for both and no resampling favours either one.

    py -3.14 scripts/build_ibis_intro_figures.py --device io_buf
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
sys.path.insert(0, str(ROOT / "scripts"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

FULL = ROOT / "results" / "ibis_intro_figures_2026-08-25" / "waveforms"
SHORT = ROOT / "results" / "stress_method_matrix_2026-08-20" / "legacy" / "waveforms"
OUT = ROOT / "results" / "ibis_intro_figures_2026-08-25" / "figures"

# Black for the reference and one strong blue for us. Deliberately none of the
# method colours from the 2026-08-20 flat set (purple gate-state, red
# pad-matched, grey transistor): these slides run before any method is named.
NATIVE = "#000000"
NGSPICE = "#1F6FB2"

DPI = 180
WIDE = (14.2, 6.0)
STACK = (14.2, 8.4)

# device -> (full-swing width ps, short-pulse width ps, full window, short window)
CASES = {
    # Short pulse is the 50% target, the earliest reversal in the stress set:
    # the reference peaks at 0.45 V there and the legacy model at 1.09 V, so the
    # failure is a doubled pulse rather than a modest overshoot. Later reversals
    # show the same defect shrinking smoothly to +219 mV at 90%.
    "io_buf": (10000.0, 1505.0, (4.0, 18.0), (4.9, 7.6)),
    "inv_chain": (3000.0, 135.0, (4.9, 8.9), (5.05, 5.75)),
    "ex2": (6000.0, 975.0, (4.6, 12.0), (4.8, 7.6)),
}
EDGE_NS = 5.0


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def style(axis, title=None, subtitle=None):
    axis.grid(alpha=0.3, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=12)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")
    if title:
        axis.set_title(title, fontsize=18, fontweight="bold", pad=34 if subtitle else 12)
    if subtitle:
        axis.text(0.5, 1.015, subtitle, transform=axis.transAxes, ha="center",
                  va="bottom", fontsize=12.5, color="#57646F")


def worst_gap(t, a, b, window, exclude=(), guard=0.15):
    """Largest separation between the two traces inside the plotted window.

    Quoted on the agreement figures so "they match" is a number rather than an
    impression formed at projector distance.

    `exclude` drops a guard band around the input edges. At the switching
    instant both traces carry a transient of a few samples that is an artefact
    of reading a coefficient while the buffer is between states, not a
    difference between the models -- on io_buf it alone sets the worst Ku gap at
    0.29 against 0.14 through the whole transition. The figures still draw it;
    only the quoted number excludes it, and the caption says so.
    """
    m = (t >= window[0]) & (t <= window[1])
    for edge in exclude:
        m &= np.abs(t - edge) > guard
    return float(np.max(np.abs(a[m] - b[m]))) if m.any() else float("nan")


def pad_figure(path, d, window, title, subtitle=None, t_rev=None):
    t = d["time_ns"]
    fig, axis = plt.subplots(figsize=WIDE)
    axis.plot(t, d["hspice_pad"], color=NATIVE, lw=4.2,
              label="HSPICE  (native IBIS model)", zorder=3)
    axis.plot(t, d["pybis_pad"], color=NGSPICE, lw=2.4, ls=(0, (5, 2.4)),
              label="ngspice  (our IBIS model)", zorder=4)
    if t_rev is not None:
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1,
                     label="reverse edge")
    axis.set_xlim(*window)
    axis.set_xlabel("Time (ns)", fontsize=13)
    axis.set_ylabel("Pad voltage (V)", fontsize=13)
    style(axis, title, subtitle)
    axis.legend(fontsize=12.5, loc="best", framealpha=0.92)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def kukd_figure(path, d, window, title, subtitle=None, t_rev=None, notes=None):
    t = d["time_ns"]
    fig, axes = plt.subplots(2, 1, figsize=STACK, sharex=True)
    for axis, coeff in zip(axes, ("ku", "kd")):
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        axis.plot(t, d[f"hspice_{coeff}"], color=NATIVE, lw=4.2,
                  label="HSPICE  (native IBIS model)", zorder=3)
        axis.plot(t, d[f"pybis_{coeff}"], color=NGSPICE, lw=2.4, ls=(0, (5, 2.4)),
                  label="ngspice  (our IBIS model)", zorder=4)
        if t_rev is not None:
            axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1)
        axis.set_ylabel(coeff.replace("k", "K"), fontsize=15)
        axis.set_ylim(-0.25, 1.3)
        style(axis)
    axes[0].set_title(title, fontsize=18, fontweight="bold",
                      pad=34 if subtitle else 12)
    if subtitle:
        axes[0].text(0.5, 1.015, subtitle, transform=axes[0].transAxes, ha="center",
                     va="bottom", fontsize=12.5, color="#57646F")
    axes[0].legend(fontsize=12.5, loc="center right", framealpha=0.92)
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    axes[0].set_xlim(*window)
    if notes:
        for axis, (x, y, text) in notes:
            axes[axis].annotate(text, xy=(x, y), fontsize=12.5, color="#AE4E19",
                                fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", default="io_buf", choices=sorted(CASES))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    full_w, short_w, full_win, short_win = CASES[args.device]
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    full_path = FULL / f"{args.device}_short_high_w{int(round(full_w))}ps.csv"
    short_path = SHORT / f"{args.device}_short_high_w{int(round(short_w))}ps.csv"
    for path in (full_path, short_path):
        if not path.exists():
            print(f"missing {path.relative_to(ROOT)}")
            return 1

    full = load(full_path)
    short = load(short_path)
    t_rev = EDGE_NS + short_w / 1000.0

    edges = (EDGE_NS, EDGE_NS + full_w / 1000.0)
    gap_pad = worst_gap(full["time_ns"], full["hspice_pad"], full["pybis_pad"], full_win)
    gap_ku = worst_gap(full["time_ns"], full["hspice_ku"], full["pybis_ku"], full_win, edges)
    gap_kd = worst_gap(full["time_ns"], full["hspice_kd"], full["pybis_kd"], full_win, edges)

    pad_figure(out / "1_full_swing_pad.png", full, full_win,
               "A full transition: our model reproduces the IBIS reference",
               f"worst separation {gap_pad * 1000:.0f} mV")
    kukd_figure(out / "2_full_swing_kukd.png", full, full_win,
                "The same agreement, in the coefficients themselves",
                f"worst separation  Ku {gap_ku:.2f}   Kd {gap_kd:.2f}"
                "   (away from the switching instants)")
    pad_figure(out / "3_short_pulse_pad.png", short, short_win,
               "Interrupt the transition and the agreement goes",
               f"pulse reversed after {short_w:.0f} ps", t_rev=t_rev)
    kukd_figure(out / "4_short_pulse_kukd.png", short, short_win,
                "Why: the reverse edge resets the model's clock to zero",
                "the falling table starts at Ku = 1, so Ku is driven there - "
                "it was only 0.30",
                t_rev=t_rev)

    print(f"{args.device}: full swing w{full_w:.0f}ps, short pulse w{short_w:.0f}ps")
    print(f"  full-swing worst separation: pad {gap_pad * 1000:.1f} mV, "
          f"Ku {gap_ku:.3f}, Kd {gap_kd:.3f}")
    for name in sorted(p.name for p in out.glob("*.png")):
        print("  " + name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
