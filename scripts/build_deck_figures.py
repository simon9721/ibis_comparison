#!/usr/bin/env python3
"""Slide figures for the meeting deck: simulation waveforms only.

Two rules, both from comparing the deck against an earlier one that read better:

**Only simulation results.** No bar charts, no scatter plots, no schematics. A
number is explained by listing it on the slide, not by drawing it as a bar. An
earlier draft turned the error budget, the C_comp sweep and the max|Ku| table into
charts; they looked tidy and told the reader less than the plain numbers would
have.

**Drawn at the size they are placed.** The study's print figures are 11-13 in wide
and up to 13 in tall with ~10 pt labels; dropped into a slide box their axis text
measured 3.9-5.6 pt. These are drawn at the slide box size with 14-17 pt fonts, so
the scale factor is 1.0 and the text is the size it claims.

Layout follows the earlier deck: pad voltage and the coefficients side by side for
the same case, a bold pipe-separated title carrying device, pulse and quantity,
the transistor as a thick pale trace with native IBIS drawn over it, and the
reversal marked with a dashed line.

Nothing is re-simulated -- every panel is rebuilt from raw output or CSVs already
on disk.

    py -3.14 scripts/build_deck_figures.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
import figures as fg  # noqa: E402

OUT = ROOT / "results" / "meeting_deck_2026-09-04" / "figures"
R = ROOT / "results"
MATRIX = R / "stress_method_matrix_2026-08-20"

W, H = 12.2, 5.2          # full-width slide box
HW, HH = 6.0, 4.9         # half-width box, for side-by-side pairs
DPI = 200
plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 17, "axes.labelsize": 16,
    "xtick.labelsize": 14, "ytick.labelsize": 14, "legend.fontsize": 13,
    "axes.linewidth": 1.2, "lines.linewidth": 2.4, "grid.alpha": 0.3,
})

SIL, NAT = fg.SILICON, fg.NATIVE
GATE, DELAY = fg.METHOD_COLORS["gate_state"], fg.METHOD_COLORS["delay_cmd"]
REV = "#8A8A8A"


def read(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open()))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(f"  {path.name}")


def title(ax, *parts: str) -> None:
    """Bold, pipe-separated: device | pulse | build | quantity."""
    ax.set_title("  |  ".join(parts), fontweight="bold")


# --------------------------------------------------------------------------- #

def clean_edge() -> None:
    """Full swing: the transistor, native IBIS and our model all agree."""
    d = R / "defect_b_full_swing_2026-09-03"
    tx = sl.parse_hspice_tr0(d / "transistor" / "run.tr0")
    nat = sl.parse_hspice_tr0(d / "native" / "run.tr0")
    py = sl.parse_ngspice_raw(d / "pybis_plain" / "run.raw")
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(sl.time_ns(tx), sl.signal(tx, "v(pad)"), color=SIL, lw=5.0,
            alpha=0.30, label="HSPICE transistor", zorder=2)
    ax.plot(sl.time_ns(nat), sl.signal(nat, "v(pad)"), color=SIL, lw=2.2,
            label="HSPICE native IBIS", zorder=4)
    ax.plot(sl.time_ns(py), sl.trace(py, "out"), color=GATE, lw=2.2,
            label="our IBIS model", zorder=3)
    ax.set_xlim(14.95, 15.9)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, "io_buf", "full swing", "pad voltage")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right")
    save(fig, OUT / "clean_edge.png")


def _pair(d, t_rev, xlim, name, *, dev, pulse, pad_keys, k_keys):
    """A pad figure and a Ku/Kd figure, sized to sit side by side on one slide."""
    fig, ax = plt.subplots(figsize=(HW, HH))
    for key, colour, lw, alpha, label, z in pad_keys:
        if key in d:
            ax.plot(d["time_ns"], d[key], color=colour, lw=lw, alpha=alpha,
                    label=label, zorder=z)
    ax.axvline(t_rev, color=REV, ls="--", lw=1.6, label="reverse edge")
    ax.set_xlim(*xlim)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, dev, pulse, "pad voltage")
    ax.grid(alpha=0.3)
    # Upper left: the event is on the right of these windows, so a legend
    # at upper right sat straight on the curves.
    ax.legend(loc="upper left", fontsize=12)
    save(fig, OUT / f"{name}_pad.png")

    fig, axes = plt.subplots(2, 1, figsize=(HW, HH), sharex=True)
    for axis, field, label in ((axes[0], "ku", "Ku"), (axes[1], "kd", "Kd")):
        axis.axhspan(-0.05, 1.05, color="#EAF1F7", zorder=0)
        for key, colour, lw, alpha, lab, z in k_keys:
            col = f"{key}_{field}"
            if col in d:
                axis.plot(d["time_ns"], d[col], color=colour, lw=lw, alpha=alpha,
                          label=lab, zorder=z)
        axis.axvline(t_rev, color=REV, ls="--", lw=1.6)
        axis.set_ylabel(label)
        axis.grid(alpha=0.3)
    axes[0].set_xlim(*xlim)
    axes[0].legend(loc="upper left", fontsize=11, ncol=2)
    title(axes[0], dev, pulse, "Ku and Kd")
    axes[1].set_xlabel("Time (ns)")
    save(fig, OUT / f"{name}_kukd.png")


def stress_pair() -> None:
    """io_buf under a truncated pulse: the defect, in pad and in coefficients."""
    src = R / "_baseline_edgecmd" / "waveforms" / "io_buf_short_high_depth86.csv"
    if not src.exists():
        print("  stress_pair: missing case CSV")
        return
    d = read(src)
    _pair(d, 6.214, (4.9, 9.0), "stress", dev="io_buf", pulse="1214 ps pulse",
          pad_keys=[("silicon_pad", SIL, 5.0, 0.30, "HSPICE transistor", 2),
                    ("hspice_pad", SIL, 2.0, 1.0, "HSPICE native IBIS", 4),
                    ("pybis_pad", GATE, 2.2, 1.0, "our IBIS model", 3)],
          k_keys=[("silicon", SIL, 5.0, 0.30, "HSPICE transistor", 2),
                  ("hspice", SIL, 2.0, 1.0, "HSPICE native IBIS", 4),
                  ("pybis", GATE, 2.2, 1.0, "our IBIS model", 3)])


def offset_chain() -> None:
    """The command capacitor, and the pad it drives."""
    src = R / "settled_offset_diagnosis_2026-08-27" / "08_comprehensive_offset_chain.csv"
    if not src.exists():
        print("  offset_chain: missing CSV")
        return
    d = read(src)
    fig, axes = plt.subplots(2, 1, figsize=(W, H), sharex=True)
    axes[0].plot(d["time_ns"], d["gupcmd"], color=GATE, lw=2.8,
                 label="GUPCMD, the command capacitor")
    axes[0].axhline(0, color="#111", lw=1.4)
    # Zoomed to the residue. On a 0-to-1 scale the commanded pulse dominates and
    # the charge left behind -- the point of the slide -- is invisible.
    axes[0].set_ylim(-0.006, 0.05)
    axes[0].text(0.015, 0.84, "commanded pulse reaches 1.0, off scale",
                 transform=axes[0].transAxes, ha="left", fontsize=14, color="#555")
    axes[0].set_ylabel("GUPCMD")
    title(axes[0], "io_buf", "truncated pulse", "command capacitor, then the pad")
    axes[1].plot(d["time_ns"], d["transistor_pad_v"], color=SIL, lw=5.0,
                 alpha=0.30, label="HSPICE transistor")
    axes[1].plot(d["time_ns"], d["native_pad_v"], color=SIL, lw=2.0,
                 label="HSPICE native IBIS")
    axes[1].plot(d["time_ns"], d["model_pad_v"], color=GATE, lw=2.4,
                 label="gate-state, as shipped")
    axes[1].set_ylabel("Pad (V)")
    axes[1].set_xlabel("Time (ns)")
    for a in axes:
        a.grid(alpha=0.3)
        a.legend(loc="upper right", fontsize=13)
    save(fig, OUT / "offset_chain.png")


def offset_removed() -> None:
    """The stranded-charge pedestal, and delay_cmd removing it."""
    case = "io_buf_short_high_w2354ps.csv"
    gs = MATRIX / "gate_state" / "waveforms" / case
    dc = MATRIX / "delay_cmd" / "waveforms" / case
    if not (gs.exists() and dc.exists()):
        print(f"  offset_removed: missing {case}")
        return
    a, b = read(gs), read(dc)
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(a["time_ns"], a["silicon_pad"], color=SIL, lw=5.0, alpha=0.30,
            label="HSPICE transistor", zorder=2)
    ax.plot(a["time_ns"], a["hspice_pad"], color=SIL, lw=2.0,
            label="HSPICE native IBIS", zorder=4)
    ax.plot(a["time_ns"], a["pybis_pad"], color=GATE, lw=2.4,
            label="gate-state, as shipped", zorder=3)
    ax.plot(b["time_ns"], b["pybis_pad"], color=DELAY, lw=2.4,
            label="gate-state + delay_cmd", zorder=3)
    ax.axvline(7.354, color=REV, ls="--", lw=1.6, label="reverse edge")
    ax.set_xlim(7.2, 12.5)
    ax.set_ylim(-0.02, 0.26)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, "io_buf", "2354 ps pulse", "pad voltage after the reversal")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right")
    save(fig, OUT / "offset_removed.png")


def variant_pair() -> None:
    """A new buffer variant under the same stress: pad and coefficients."""
    src = None
    for cand in sorted((R / "variant_stress_cases_2026-09-04").rglob("waveforms.csv")):
        if cand.parent.name.startswith("depth50"):
            src = cand
            break
    if src is None:
        print("  variant_pair: no depth50 case yet")
        return
    d = read(src)
    variant = src.parent.parent.name
    width_ps = int(src.parent.name.split("_w")[1].replace("ps", ""))
    t_rev = 5.0 + width_ps / 1000.0
    _pair(d, t_rev, (4.94, 5.55), "variant", dev=variant,
          pulse=f"{width_ps} ps pulse",
          pad_keys=[("silicon_pad", SIL, 5.0, 0.30, "HSPICE transistor", 2),
                    ("native_pad", SIL, 2.0, 1.0, "HSPICE native IBIS", 4),
                    ("gate_state_pad", GATE, 2.2, 1.0, "gate-state", 3),
                    ("delay_cmd_pad", DELAY, 2.2, 1.0, "delay_cmd", 3)],
          k_keys=[("silicon", SIL, 5.0, 0.30, "HSPICE transistor", 2),
                  ("native", SIL, 2.0, 1.0, "HSPICE native IBIS", 4),
                  ("gate_state", GATE, 2.2, 1.0, "gate-state", 3),
                  ("delay_cmd", DELAY, 2.2, 1.0, "delay_cmd", 3)])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (clean_edge, stress_pair, offset_chain, offset_removed, variant_pair):
        try:
            fn()
        except Exception as exc:                       # noqa: BLE001
            print(f"  {fn.__name__} failed: {exc}")
    # An error-budget bar, a max|Ku| scatter and a C_comp bar used to live here.
    # They are numbers, and numbers get listed on the slide instead.
    for stale in ("error_budget.png", "ku_cap.png", "ccomp.png",
                  "shift_vs_depth.png"):
        p = OUT / stale
        if p.exists():
            p.unlink()
            print(f"  removed {stale}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
