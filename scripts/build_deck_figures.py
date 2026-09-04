#!/usr/bin/env python3
"""Slide-sized versions of the deck figures, with text that survives projection.

The study's figures are drawn for print: 11-13 inches wide, often 7-13 inches
tall, with ~10 pt labels. Dropping one into a slide box shrinks everything with
it. Measured on the first draft of the deck, every figure's axis text landed
between **3.9 and 5.6 pt** -- technically present, unreadable from a seat.

The fix is not to enlarge the box, which cannot work for a figure taller than the
slide. It is to redraw at the size it will actually occupy, with fonts chosen for
that size: one or two panels, 12.2 x 5.2 inches, 16-20 pt. Placed at 12.2 inches
wide the scale factor is 1.0, so a 17 pt label is 17 pt on the slide.

Nothing is re-simulated. Every panel is rebuilt from raw output or CSVs already on
disk, so this is cheap to re-run when results change.

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

# One slide box. Figures are drawn at exactly the size they are placed at, so
# point sizes here are point sizes on the slide.
W, H = 12.2, 5.2
DPI = 200
plt.rcParams.update({
    "font.size": 16, "axes.titlesize": 19, "axes.labelsize": 17,
    "xtick.labelsize": 15, "ytick.labelsize": 15, "legend.fontsize": 15,
    "axes.linewidth": 1.2, "lines.linewidth": 2.6, "grid.alpha": 0.3,
})

SIL, NAT = fg.SILICON, fg.NATIVE
GATE, DELAY = fg.METHOD_COLORS["gate_state"], fg.METHOD_COLORS["delay_cmd"]


def read(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open()))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def finish(fig, ax, path: Path, legend_ncol=3):
    for a in np.atleast_1d(ax).ravel():
        a.grid(alpha=0.3)
    np.atleast_1d(ax).ravel()[0].legend(ncol=legend_ncol, framealpha=0.95)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(f"  {path.name}")


# --------------------------------------------------------------------------- #

def clean_edge() -> None:
    """io_buf full swing, falling edge. Re-plotted from the defect_b run dirs."""
    d = R / "defect_b_full_swing_2026-09-03"
    tx = sl.parse_hspice_tr0(d / "transistor" / "run.tr0")
    nat = sl.parse_hspice_tr0(d / "native" / "run.tr0")
    py = sl.parse_ngspice_raw(d / "pybis_plain" / "run.raw")
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(sl.time_ns(tx), sl.signal(tx, "v(pad)"), color=SIL, lw=3.4,
            label="HSPICE transistor", zorder=5)
    ax.plot(sl.time_ns(nat), sl.signal(nat, "v(pad)"), color=NAT, lw=2.6,
            ls="--", label="native IBIS", zorder=4)
    ax.plot(sl.time_ns(py), sl.trace(py, "out"), color=GATE, lw=2.4,
            ls="--", label="pybis", zorder=3)
    ax.set_xlim(14.95, 15.9)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    ax.set_title("io_buf  ·  full swing  ·  50 ohm and 2 pF  ·  falling edge")
    finish(fig, ax, OUT / "clean_edge.png")


def offset_removed() -> None:
    """The settled pedestal, shipped gate-state vs delay_cmd, on one io_buf case."""
    # Chosen by measuring the pedestal on every case present in both builds: this
    # is where the defect is largest, so the figure shows the thing it claims to.
    # gate-state 97.9 mV against silicon's 2.1 mV; delay_cmd 5.2 mV.
    case = "io_buf_short_high_w2354ps.csv"
    gs = MATRIX / "gate_state" / "waveforms" / case
    dc = MATRIX / "delay_cmd" / "waveforms" / case
    if not (gs.exists() and dc.exists()):
        print(f"  offset_removed: missing {case}")
        return
    a, b = read(gs), read(dc)
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(a["time_ns"], a["silicon_pad"], color=SIL, lw=3.4,
            label="HSPICE transistor", zorder=5)
    ax.plot(a["time_ns"], a["hspice_pad"], color=NAT, lw=2.4, ls="--",
            label="native IBIS", zorder=4)
    ax.plot(a["time_ns"], a["pybis_pad"], color=GATE, lw=2.6,
            label="gate-state (as shipped)", zorder=3)
    ax.plot(b["time_ns"], b["pybis_pad"], color=DELAY, lw=2.6,
            label="gate-state + delay_cmd", zorder=3)
    ax.set_xlim(7.2, 12.5)
    ax.set_ylim(-0.02, 0.26)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    ax.set_title("io_buf  ·  2354 ps pulse  ·  after the reversal")
    finish(fig, ax, OUT / "offset_removed.png", legend_ncol=2)


def shift_vs_depth() -> None:
    """pybis minus transistor against depth, over the nine buffer variants.

    An earlier version drew this from results/_baseline_edgecmd/, which was wrong
    twice over. It merged short_high and short_low onto one line per device, and
    that set has only two or three depths per device and direction. Split by
    direction it shows the shift essentially *flat* with depth, and on io_buf
    short-high growing toward full swing -- the opposite of the slide's claim.

    The claim is supported by the variant sweep, which controlled depth properly
    across nine buffers and four widths each, and where the shift grows
    monotonically as the pulse is truncated on 9 of 9.

    The x axis is depth relative to the widest pulse tested, not to a settled full
    swing: that sweep predates the settled-reference correction, so the widest
    stressed width is itself ~3-9% short of settled. It is a relative trend, and
    labelled as one.
    """
    src = R / "variant_stress_depth_2026-09-03" / "variant_stress_depth.csv"
    if not src.exists():
        print("  shift_vs_depth: missing variant sweep CSV")
        return
    rows = list(csv.DictReader(src.open()))
    by: dict[str, list[tuple[float, float]]] = {}
    for r in rows:
        by.setdefault(r["variant"], []).append(
            (float(r["tx_excursion_v"]), float(r["gate_state_vs_tx_ps"])))
    fig, ax = plt.subplots(figsize=(W, H))
    fam = {"inv": "#1B6B4F", "ex2": "#2B6CA3"}
    for variant, vals in sorted(by.items()):
        full = max(v[0] for v in vals)
        # Below 30% the models make a transition several times larger than the
        # transistor, so no crossing metric separates timing from amplitude.
        # Those points are excluded here for the same reason the written summary
        # excludes them, rather than being drawn and then caveated.
        pts = sorted(((100.0 * v[0] / full, v[1]) for v in vals
                      if 100.0 * v[0] / full >= 30.0))
        if len(pts) < 2:
            continue
        colour = fam["inv"] if variant.startswith("inv") else fam["ex2"]
        # No per-line labels: nine of them collided in the middle of the plot, and
        # the message is the family trend, which the two colours already carry.
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=colour,
                ms=8, lw=2.0, alpha=0.8)
    ax.axhline(0, color="#111", lw=1.6)
    ax.plot([], [], "o-", color=fam["inv"], label="inv_chain variants")
    ax.plot([], [], "o-", color=fam["ex2"], label="ex2 variants")
    ax.set_xlabel("excursion reached, % of the widest pulse tested")
    ax.set_ylabel("pybis − transistor (ps)")
    ax.set_title("nine buffer variants  ·  four pulse widths each  ·  depths below 30% omitted")
    ax.set_xlim(28, 106)
    finish(fig, ax, OUT / "shift_vs_depth.png", legend_ncol=2)


def error_budget() -> None:
    """The clean-edge error budget as a bar, not a table.

    The point is the *proportion* -- that the format costs far more than our
    command layer -- and a proportion is read from a length faster than from three
    numbers in a column.
    """
    labels = ["native IBIS", "pybis stock", "pybis gate-state"]
    vals = [34.6, 38.4, 43.5]
    cols = [NAT, "#8A8A8A", GATE]
    fig, ax = plt.subplots(figsize=(W, 4.9))
    bars = ax.barh(labels[::-1], vals[::-1], color=cols[::-1], height=0.55)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 0.7, b.get_y() + b.get_height() / 2, f"+{v:.1f} ps",
                va="center", fontsize=18)
    ax.axvline(34.6, color="#111", ls="--", lw=2.0)
    # In the white gap between two bars, not above the top one -- at y=2.45 this
    # sat outside the axes and printed straight through the title.
    ax.text(34.6 - 1.0, 1.5, "what the IBIS format itself costs",
            ha="right", va="center", fontsize=17, color="#111",
            bbox=dict(facecolor="white", edgecolor="none", pad=3))
    ax.set_xlim(0, 52)
    ax.set_xlabel("falling 50% crossing, later than the transistor (ps)")
    ax.set_title("io_buf  ·  full swing  ·  falling edge")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "error_budget.png", dpi=DPI)
    plt.close(fig)
    print("  error_budget.png")


def ku_cap() -> None:
    """max|Ku| against output edge rate, with the cap that rejects most of them."""
    # Label offsets are set per point, not uniformly: base (200 ps) and nomiller
    # (208 ps) sit almost on top of each other, and a shared offset put their two
    # labels in the same place.
    data = [("slowpre\npredriver halved", 328, 1.047, (-14, 16), "right"),
            ("nomiller\nMiller caps out", 208, 1.299, (16, 6), "left"),
            ("base\ncontrol", 200, 1.283, (-16, -34), "right"),
            ("skewp\nPMOS halved", 160, 1.589, (18, -4), "left"),
            ("weak\nboth halved", 152, 1.779, (18, 4), "left")]
    fig, ax = plt.subplots(figsize=(W, 4.9))
    ax.plot([d[1] for d in data], [d[2] for d in data], "o", ms=17,
            color=GATE, zorder=5)
    for name, x, y, off, ha in data:
        ax.annotate(name, (x, y), textcoords="offset points", xytext=off,
                    ha=ha, va="center", fontsize=16)
    ax.axhline(1.25, color="#C02626", ls="--", lw=2.4, zorder=3)
    ax.text(355, 1.30, "the 1.25 cap — rejects four of these five",
            color="#C02626", fontsize=17, va="bottom", ha="right")
    ax.set_xlabel("output edge rate (ps)  —  faster to the left")
    ax.set_ylabel("max |Ku|")
    ax.set_ylim(0.92, 2.02)
    ax.set_xlim(120, 380)
    ax.set_title("ex2 variants  ·  all seven characterisation edge rates")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "ku_cap.png", dpi=DPI)
    plt.close(fig)
    print("  ku_cap.png")


def offset_chain() -> None:
    """Where the offset comes from: the command capacitor, then the pad.

    The print version stacks five panels (GUPCMD, GUPTARGET, GUP, Ku, pad) at
    12 x 13 inches. At slide size that is 3.9 pt text. Two panels carry the
    argument -- the charge that is stranded, and what the load sees -- so the
    other three are dropped rather than shrunk into illegibility.
    """
    src = R / "settled_offset_diagnosis_2026-08-27" / "08_comprehensive_offset_chain.csv"
    if not src.exists():
        print("  offset_chain: missing CSV")
        return
    d = read(src)
    fig, axes = plt.subplots(2, 1, figsize=(W, H), sharex=True)
    axes[0].plot(d["time_ns"], d["gupcmd"], color=GATE, lw=3.0,
                 label="GUPCMD — the command capacitor")
    axes[0].axhline(0, color="#111", lw=1.4)
    # Zoomed to the residue. On a 0-to-1 scale the commanded pulse dominates and
    # the charge left behind -- the entire point of the slide -- is invisible.
    axes[0].set_ylim(-0.006, 0.05)
    # Left side: at the right it sat underneath the legend.
    axes[0].text(0.015, 0.86, "commanded pulse reaches 1.0, off scale",
                 transform=axes[0].transAxes, ha="left", fontsize=15, color="#555")
    axes[0].set_ylabel("GUPCMD")
    axes[0].set_title("io_buf  ·  truncated pulse  ·  command capacitor, then the pad")
    axes[1].plot(d["time_ns"], d["transistor_pad_v"], color=SIL, lw=3.4,
                 label="HSPICE transistor")
    axes[1].plot(d["time_ns"], d["native_pad_v"], color=NAT, lw=2.4, ls="--",
                 label="native IBIS")
    axes[1].plot(d["time_ns"], d["model_pad_v"], color=GATE, lw=2.6,
                 label="gate-state (as shipped)")
    axes[1].set_ylabel("Pad (V)")
    axes[1].set_xlabel("Time (ns)")
    for a in axes:
        a.grid(alpha=0.3)
        a.legend(ncol=3, framealpha=0.95)
    fig.tight_layout()
    fig.savefig(OUT / "offset_chain.png", dpi=DPI)
    plt.close(fig)
    print("  offset_chain.png")


def ccomp() -> None:
    """C_comp nominal vs zero, across the load sweep."""
    rows = list(csv.DictReader((R / "pybis_ccomp_converged_2026-09-03"
                                / "ccomp_validation.csv").open()))
    labels, nom, zero = [], [], []
    for r in rows:
        try:
            z = float(r["pybis_noccomp_shift_ps"])
            n = float(r["pybis_ccomp_shift_ps"])
        except ValueError:
            continue
        if not (np.isfinite(z) and np.isfinite(n)):
            continue
        labels.append(r["load"])
        nom.append(n)
        zero.append(z)
    if not labels:
        print("  ccomp: no finite rows")
        return
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(W, H))
    ax.bar(x - 0.2, nom, 0.4, color=DELAY, label="C_comp at nominal")
    ax.bar(x + 0.2, zero, 0.4, color=GATE, label="C_comp set to zero")
    ax.axhline(0, color="#111", lw=1.4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("50% crossing shift vs transistor (ps)")
    ax.set_title("50% crossing shift vs the transistor, across the load sweep")
    finish(fig, ax, OUT / "ccomp.png", legend_ncol=2)


def variant_kukd() -> None:
    """Ku and Kd for one stressed variant case, at slide size."""
    src = next((R / "variant_stress_cases_2026-09-04").rglob("waveforms.csv"), None)
    if src is None:
        print("  variant_kukd: no case CSV yet")
        return
    d = read(src)
    fig, axes = plt.subplots(2, 1, figsize=(W, H), sharex=True)
    for ax, field, label in ((axes[0], "ku", "Ku"), (axes[1], "kd", "Kd")):
        for source, (colour, _lw, z) in fg.ORDER.items():
            col = f"{source}_{field}"
            if col not in d:
                continue
            ax.plot(d["time_ns"], d[col], color=colour, lw=2.6,
                    label=source.replace("_", " "), zorder=z)
        ax.set_ylabel(label)
        ax.grid(alpha=0.3)
    edge = 5.0
    axes[0].set_xlim(edge - 0.06, edge + 0.55)
    # Above the axes, not inside: at ncol=5 the box covered the Ku plateau.
    axes[0].legend(ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.02),
                   framealpha=0.95, fontsize=14)
    axes[0].set_title("")
    axes[1].set_xlabel("Time (ns)")
    fig.tight_layout()
    fig.savefig(OUT / "variant_kukd.png", dpi=DPI)
    plt.close(fig)
    print("  variant_kukd.png")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (error_budget, clean_edge, offset_chain, offset_removed,
               shift_vs_depth, ccomp, ku_cap, variant_kukd):
        try:
            fn()
        except Exception as exc:                       # noqa: BLE001
            print(f"  {fn.__name__} failed: {exc}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
