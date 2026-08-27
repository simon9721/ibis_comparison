#!/usr/bin/env python3
"""The shipped builds, not the mechanism: gate-state against every Vc-matching.

Figure 18 shows the two *mechanisms* agree to 0.08 mV once everything else is
stripped away. This shows what the actual implementations do on a real case,
which is a different and less flattering picture: the production models carry
residual corrections, arming and sampling machinery, and read Ku from different
places, so they do not produce the same waveform.

io_buf short_high at 2226 ps is the only width where all five builds converge,
so the comparison is made there rather than on the deck's 1634 ps case, which
pure gate-state and two of the Vc builds do not solve.

    py -3.14 scripts/build_implementation_comparison_figure.py
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
OUT = ROOT / "results" / "ibis_intro_figures_2026-08-25" / "figures_methods"

STEM = "io_buf_short_high_w2226ps.csv"
EDGE_NS, WIDTH_NS = 5.0, 2.2259
WINDOW = (4.6, 9.4)

TRANSISTOR = "#808080"
# Reference first, then the shipped Vc build, then each correction in the order
# it was applied, so the figure reads as the sequence of fixes.
BUILDS = [
    ("gate_state", "gate-state (pure build)", "#1B6B4F", 2.6),
    ("gate_match", "Vc-matching, as shipped", "#D97706", 2.2),
    ("gate_match_hybrid", "Vc-matching, gated to the reversal", "#C02626", 2.2),
    ("gate_match_equiv", "Vc-matching, same map and residual", "#7B2CBF", 2.2),
]
DPI = 180


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def style(axis, title=None):
    axis.grid(alpha=0.3, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=12)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")
    if title:
        axis.set_title(title, fontsize=18, fontweight="bold", pad=12)


# Each Vc build against the gate-state built on the *same* command layer. Pairing
# the delay_cmd build against the edge-integrating gate-state would charge it for
# a command change it did not make.
CONVERGENCE = [
    ("gate_match", "gate_state", "as shipped", "#D97706"),
    ("gate_match_hybrid", "gate_state", "gated to the reversal", "#C02626"),
    ("gate_match_equiv", "gate_state", "same map and residual", "#7B2CBF"),
    ("gate_match_equiv_delaycmd", "delay_cmd",
     "delay command, sample fixed", "#1B6B4F"),
]


def convergence_figure(out):
    """Absolute waveforms for the closest pair, and every build's gap below it."""
    pairs = [(a, b, lab, c) for a, b, lab, c in CONVERGENCE
             if (MATRIX / a / "waveforms" / STEM).exists()
             and (MATRIX / b / "waveforms" / STEM).exists()]
    if not pairs:
        return {}
    t_rev = EDGE_NS + WIDTH_NS
    fig, axes = plt.subplots(2, 1, figsize=(14.2, 9.0))

    best_a, best_b, best_lab, best_c = pairs[-1]
    a, b = (load(MATRIX / best_a / "waveforms" / STEM),
            load(MATRIX / best_b / "waveforms" / STEM))
    axes[0].plot(b["time_ns"], b["silicon_pad"], color=TRANSISTOR, lw=5.4,
                 label="HSPICE transistor", zorder=2)
    axes[0].plot(b["time_ns"], b["pybis_pad"], color="#1B6B4F", lw=3.0,
                 label="gate-state (integrated gate)", zorder=3)
    axes[0].plot(a["time_ns"], a["pybis_pad"], color="#C02626", lw=2.0,
                 ls=(0, (5, 2.4)), label="Vc-matching (replayed gate)", zorder=4)
    axes[0].axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1)
    axes[0].set_xlim(*WINDOW)
    axes[0].set_ylabel("Pad voltage (V)", fontsize=13)
    style(axes[0], f"io_buf  |  {WIDTH_NS * 1000:.0f} ps pulse  |  "
                   "replayed gate against integrated gate")
    axes[0].legend(fontsize=12, loc="upper left", framealpha=0.94)

    worst = {}
    for key, ref, label, colour in pairs:
        d = load(MATRIX / key / "waveforms" / STEM)
        r = load(MATRIX / ref / "waveforms" / STEM)
        t = d["time_ns"]
        m = (t >= WINDOW[0]) & (t <= WINDOW[1])
        gap = np.abs(d["pybis_pad"][m] - np.interp(t[m], r["time_ns"], r["pybis_pad"]))
        worst[label] = float(np.max(gap)) * 1000.0
        axes[1].semilogy(t[m], np.maximum(gap * 1000.0, 1e-3), color=colour, lw=2.2,
                         label=f"{label}   worst {worst[label]:.0f} mV")
    axes[1].axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1)
    axes[1].set_xlim(*WINDOW)
    axes[1].set_ylim(1e-2, 2e3)
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    axes[1].set_ylabel("|Vc-matching - gate-state|  (mV)", fontsize=13)
    style(axes[1])
    axes[1].legend(fontsize=11.5, loc="upper left", framealpha=0.94)
    fig.tight_layout()
    fig.savefig(out / "20_convergence.png", dpi=DPI)
    plt.close(fig)
    return worst


# The pair after every bookkeeping difference is removed: same command layer,
# same map, same residual, sample settling inside its pulse. All that separates
# them now is how the gate value is obtained.
FINAL_PAIR = ("gate_match_equiv_delaycmd", "delay_cmd")


def final_pair_figure(out):
    """Pad, Ku and Kd for the corrected pair, on one set of axes each."""
    a_key, b_key = FINAL_PAIR
    if not all((MATRIX / k / "waveforms" / STEM).exists() for k in FINAL_PAIR):
        return {}
    a, b = (load(MATRIX / a_key / "waveforms" / STEM),
            load(MATRIX / b_key / "waveforms" / STEM))
    t_rev = EDGE_NS + WIDTH_NS
    integ, replay = "#1B6B4F", "#C02626"

    fig, axes = plt.subplots(3, 1, figsize=(14.2, 11.4), sharex=True)
    axes[0].plot(b["time_ns"], b["silicon_pad"], color=TRANSISTOR, lw=5.4,
                 label="HSPICE transistor", zorder=2)
    axes[0].plot(b["time_ns"], b["pybis_pad"], color=integ, lw=3.2,
                 label="gate-state   gate by integration", zorder=3)
    axes[0].plot(a["time_ns"], a["pybis_pad"], color=replay, lw=2.0, ls=(0, (5, 2.4)),
                 label="Vc-matching   gate by replay", zorder=4)
    axes[0].set_ylabel("Pad voltage (V)", fontsize=13)
    style(axes[0], f"io_buf  |  {WIDTH_NS * 1000:.0f} ps pulse  |  "
                   "pad voltage and Ku/Kd")
    axes[0].legend(fontsize=12, loc="upper left", framealpha=0.94)

    worst = {}
    for axis, coeff in zip(axes[1:], ("ku", "kd")):
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        axis.plot(b["time_ns"], b[f"pybis_{coeff}"], color=integ, lw=3.2,
                  label="gate-state", zorder=3)
        axis.plot(a["time_ns"], a[f"pybis_{coeff}"], color=replay, lw=2.0,
                  ls=(0, (5, 2.4)), label="Vc-matching", zorder=4)
        axis.set_ylabel(coeff.replace("k", "K"), fontsize=15)
        axis.set_ylim(-0.25, 1.3)
        style(axis)
        axis.legend(fontsize=12, loc="upper right", framealpha=0.94)

    for axis in axes:
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1)
        axis.set_xlim(*WINDOW)
    axes[2].set_xlabel("Time (ns)", fontsize=13)
    fig.tight_layout()
    fig.savefig(out / "23_final_pair.png", dpi=DPI)
    plt.close(fig)

    t = a["time_ns"]
    m = (t >= WINDOW[0]) & (t <= WINDOW[1])
    for name, col in (("pad", "pybis_pad"), ("Ku", "pybis_ku"), ("Kd", "pybis_kd")):
        worst[name] = float(np.max(np.abs(a[col][m] -
                                          np.interp(t[m], b["time_ns"], b[col]))))
    return worst


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    have = [(k, lab, c, lw) for k, lab, c, lw in BUILDS
            if (MATRIX / k / "waveforms" / STEM).exists()]
    missing = [k for k, *_ in BUILDS if (MATRIX / k / "waveforms" / STEM).exists() is False]
    if missing:
        print("missing:", missing)
    base = load(MATRIX / have[0][0] / "waveforms" / STEM)
    t_rev = EDGE_NS + WIDTH_NS
    title = f"io_buf  |  {WIDTH_NS * 1000:.0f} ps pulse  |  shipped implementations"

    fig, axis = plt.subplots(figsize=(14.2, 6.0))
    axis.plot(base["time_ns"], base["silicon_pad"], color=TRANSISTOR, lw=5.4,
              label="HSPICE transistor", zorder=2)
    for key, label, colour, lw in have:
        d = load(MATRIX / key / "waveforms" / STEM)
        axis.plot(d["time_ns"], d["pybis_pad"], color=colour, lw=lw, label=label, zorder=4)
    axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1, label="reverse edge")
    axis.set_xlim(*WINDOW)
    axis.set_xlabel("Time (ns)", fontsize=13)
    axis.set_ylabel("Pad voltage (V)", fontsize=13)
    style(axis, f"{title}  |  pad voltage")
    axis.legend(fontsize=11.5, loc="upper left", framealpha=0.94)
    fig.tight_layout()
    fig.savefig(out / "19_implementations_pad.png", dpi=DPI)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(14.2, 8.4), sharex=True)
    for axis, coeff in zip(axes, ("ku", "kd")):
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        axis.plot(base["time_ns"], base[f"silicon_{coeff}"], color=TRANSISTOR, lw=5.4,
                  label="HSPICE transistor", zorder=2)
        for key, label, colour, lw in have:
            d = load(MATRIX / key / "waveforms" / STEM)
            axis.plot(d["time_ns"], d[f"pybis_{coeff}"], color=colour, lw=lw,
                      label=label, zorder=4)
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8, zorder=1)
        axis.set_ylabel(coeff.replace("k", "K"), fontsize=15)
        axis.set_ylim(-0.25, 1.3)
        style(axis)
    axes[0].set_title(f"{title}  |  Ku and Kd", fontsize=18, fontweight="bold", pad=12)
    axes[0].legend(fontsize=11.5, loc="upper right", framealpha=0.94, ncol=2)
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    axes[0].set_xlim(*WINDOW)
    fig.tight_layout()
    fig.savefig(out / "19_implementations_kukd.png", dpi=DPI)
    plt.close(fig)

    ref = load(MATRIX / "gate_state" / "waveforms" / STEM)
    t = ref["time_ns"]
    m = (t >= WINDOW[0]) & (t <= WINDOW[1])
    print(f"io_buf 2226 ps, each build against the pure gate-state build\n")
    print(f"{'build':38s} {'worst dPad':>12s} {'worst dKu':>11s}")
    for key, label, _c, _lw in have:
        if key == "gate_state":
            continue
        d = load(MATRIX / key / "waveforms" / STEM)
        dp = np.max(np.abs(ref["pybis_pad"][m] -
                           np.interp(t[m], d["time_ns"], d["pybis_pad"]))) * 1000
        dk = np.max(np.abs(ref["pybis_ku"][m] -
                           np.interp(t[m], d["time_ns"], d["pybis_ku"])))
        print(f"{label:38s} {dp:9.1f} mV {dk:11.3f}")
    worst = convergence_figure(out)
    if worst:
        print("\neach build against the gate-state on its own command layer")
        for label, value in worst.items():
            print(f"   {label:32s} {value:8.1f} mV")
    final = final_pair_figure(out)
    if final:
        print("\nfinal pair, worst separation across the window")
        for name, value in final.items():
            unit = " V" if name == "pad" else ""
            print(f"   {name:4s} {value:.3e}{unit}")
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
