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
for _p in (ROOT / "scripts", ROOT / "scripts" / "archive",
           ROOT / ".codex_deps" / "presentation" / "python"):
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
# The 0904 deck draws gate-state in purple and delay_cmd in green; matched
# here so the recap figure is the one the audience already saw.
GATE = "#7B2CBF"
DELAY = fg.METHOD_COLORS["delay_cmd"]
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

def timing_shift() -> None:
    """The other defect: our model crosses later than native under stress.

    Measured on this figure's own case at 50% of the transistor's excursion. The
    plan quotes "69-99 ps late, where native IBIS is 5-26 ps early"; that is not
    reproducible from the data on disk with this metric. What the stress matrix
    actually shows, over its five short-high cases per device:

        io_buf      native +11 .. +18 ps    ours +27 .. +34 ps
        inv_chain   native  -6 ..  -5 ps    ours  +8 .. +12 ps
        ex2         native -46 .. -37 ps    ours -42 .. -26 ps

    So on io_buf and inv_chain our model runs about 15 ps later than native; on
    ex2 both are early and ours is the closer of the two. The defect is real and
    device-dependent, but smaller and less one-sided than the plan states.
    """
    case = "io_buf_short_high_w2354ps.csv"
    src = MATRIX / "gate_state" / "waveforms" / case
    if not src.exists():
        print(f"  timing_shift: missing {case}")
        return
    d = read(src)
    t, si = d["time_ns"], d["silicon_pad"]
    base = float(np.median(si[t < 4.8]))
    lvl = base + 0.5 * (si.max() - base)
    marks = [("HSPICE transistor", si, SIL, 5.0, 0.30),
             ("HSPICE native IBIS", d["hspice_pad"], SIL, 2.2, 1.0),
             ("our IBIS model", d["pybis_pad"], GATE, 2.4, 1.0)]
    fig, ax = plt.subplots(figsize=(W, H))
    t_tx = sl.cross(t, si, lvl, after=4.9)
    for label, y, colour, lw, alpha in marks:
        ax.plot(t, y, color=colour, lw=lw, alpha=alpha, label=label)
        x = sl.cross(t, y, lvl, after=4.9)
        if np.isfinite(x):
            ax.plot([x], [lvl], "o", color=colour, ms=11, alpha=max(alpha, 0.6),
                    zorder=6)
    ax.axhline(lvl, color="#111", lw=1.2, ls=":")
    ax.text(t_tx - 0.02, lvl + 0.06, "50% of the transistor's excursion",
            fontsize=14, ha="right")
    for label, y, colour, _lw, _a in marks[1:]:
        x = sl.cross(t, y, lvl, after=4.9)
        if np.isfinite(x):
            ax.annotate(f"{(x - t_tx) * 1e3:+.0f} ps", xy=(x, lvl),
                        xytext=(x + 0.06, lvl - 0.22), fontsize=15, color=colour,
                        arrowprops=dict(arrowstyle="->", color=colour, lw=1.6))
    ax.set_xlim(t_tx - 0.55, t_tx + 0.75)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, "io_buf", "2354 ps pulse", "the rising 50% crossing")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=13)
    save(fig, OUT / "timing_shift.png")


def command_mechanism() -> None:
    """How delay_cmd works, shown on the command node itself.

    One line of the generated subcircuit separates the builds:

        gate_state   CGUPCMD GUPCMD 0 {gate_c} ic=0     a capacitor
                     RGUPCMD GUPCMD 0 1e15              across 1e15 ohm
                     BGUPCMDON I = -{gate_c}*V(PUONP)/edge_delay   packet per edge
        delay_cmd    BGUPCMD GUPCMD 0 V = V(PUCMDLVL)   driven by the level

    Measured on the tail after the reversal: gate_state sits at -0.144 and creeps
    back over ~3 ns; delay_cmd is at exactly 0.

    Only the command is plotted, not Ku or the pad. On this bench the stranded
    charge happens to be *negative*, and the command clamp min(max(x,0),1) removes
    it before it reaches the coefficient -- the two builds' pads agree to 5 mV
    here. The consequence is shown on the case where the charge is positive, in
    the pad figure beside it. Plotting a Ku panel here would have implied a
    difference that this bench does not show.
    """
    src = R / "command_mechanism_2026-09-04" / "command_mechanism.csv"
    if not src.exists():
        print("  command_mechanism: run scripts/probe_command_mechanism.py first")
        return
    d = read(src)
    rev = 5.0 + 2.354
    fig, ax = plt.subplots(figsize=(HW, HH))
    ax.axhline(0, color="#111", lw=1.4)
    ax.plot(d["time_ns"], d["gate_state_gupcmd"], color=GATE, lw=2.8,
            label="gate-state: a capacitor charged per edge")
    ax.plot(d["time_ns"], d["delay_cmd_gupcmd"], color=DELAY, lw=2.8,
            label="delay_cmd: driven by the input level")
    ax.axvline(rev, color=REV, ls="--", lw=1.6, label="reverse edge")
    # Annotations anchored inside the axes: at x=9.1 the longer one ran off the
    # right edge of the half-width box.
    ax.annotate("−0.144 left behind", xy=(9.2, -0.144), xytext=(8.4, -0.30),
                fontsize=14, color=GATE, ha="center",
                arrowprops=dict(arrowstyle="->", color=GATE, lw=1.6))
    ax.annotate("returns to exactly 0", xy=(9.2, 0.0), xytext=(8.6, 0.34),
                fontsize=14, color=DELAY, ha="center",
                arrowprops=dict(arrowstyle="->", color=DELAY, lw=1.6))
    ax.set_xlim(4.9, 12.0)
    ax.set_ylim(-0.42, 1.30)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("command (GUPCMD)")
    # Two parts, not three: a half-width box clips a longer title.
    title(ax, "io_buf 2354 ps pulse", "the command node")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=12)
    save(fig, OUT / "command_node.png")


def command_pad() -> None:
    """The pad consequence, half width, to sit beside the command node."""
    case = "io_buf_short_high_w2354ps.csv"
    gs = MATRIX / "gate_state" / "waveforms" / case
    dc = MATRIX / "delay_cmd" / "waveforms" / case
    if not (gs.exists() and dc.exists()):
        print(f"  command_pad: missing {case}")
        return
    a, b = read(gs), read(dc)
    fig, ax = plt.subplots(figsize=(HW, HH))
    ax.plot(a["time_ns"], a["silicon_pad"], color=SIL, lw=5.0, alpha=0.30,
            label="HSPICE transistor")
    ax.plot(a["time_ns"], a["hspice_pad"], color=SIL, lw=2.0,
            label="HSPICE native IBIS")
    ax.plot(a["time_ns"], a["pybis_pad"], color=GATE, lw=2.4,
            label="gate-state")
    ax.plot(b["time_ns"], b["pybis_pad"], color=DELAY, lw=2.4,
            label="delay_cmd")
    ax.axvline(7.354, color=REV, ls="--", lw=1.6, label="reverse edge")
    ax.set_xlim(7.3, 12.0)
    ax.set_ylim(-0.02, 0.20)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, "io_buf 2354 ps pulse", "pad voltage")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=12)
    save(fig, OUT / "command_pad.png")


def recap() -> None:
    """The issue recap: pad and coefficients on one truncated io_buf pulse.

    **Not** drawn from the native-anchored sweep, although the 0904 deck's recap
    figure is. That sweep picks the pulse width at which *native IBIS* reaches the
    target, so on its swing_50 case the transistor is 67.6% through its transition
    while native is only 50.3% through. Plotted on one time axis the transistor's
    edge then sits ~150 ps to the left, which reads as a propagation-delay error
    and is not one -- it is the two curves being at different points of the same
    transition. Measured at 50% of each curve's own peak the gap is still 76 ps to
    native and 130 ps to gate-state, far larger than anything else in the study.

    This uses a transistor-anchored case instead, where all three see the same
    pulse width. The peaks then agree to within 0.09 V and the crossings to tens of
    picoseconds -- native -7 ps, gate-state +46 ps -- which is the finding
    everywhere else. Resampling is not the difference: decimating a fine ngspice
    trace to an 88 ps grid moves its 50% crossing by under 1.5 ps.
    """
    case = "io_buf_short_high_w2354ps.csv"
    src = MATRIX / "gate_state" / "waveforms" / case
    if not src.exists():
        print(f"  recap: missing {case}")
        return
    d = read(src)
    rev = 5.0 + 2.354
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(d["time_ns"], d["silicon_pad"], color=SIL, lw=6.0, alpha=0.32,
            label="HSPICE transistor", zorder=2)
    ax.plot(d["time_ns"], d["hspice_pad"], color=SIL, lw=2.2,
            label="HSPICE native IBIS", zorder=4)
    ax.plot(d["time_ns"], d["pybis_pad"], color=GATE, lw=2.4,
            label="gate-state", zorder=3)
    ax.axvline(rev, color=REV, ls="--", lw=1.8, label="reverse edge")
    ax.set_xlim(5.4, 11.0)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, "io_buf", "2354 ps pulse", "pad voltage")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", ncol=2)
    save(fig, OUT / "recap_pad.png")

    fig, axes = plt.subplots(2, 1, figsize=(W, H), sharex=True)
    for axis, field, label in ((axes[0], "ku", "Ku"), (axes[1], "kd", "Kd")):
        axis.axhspan(-0.05, 1.05, color="#EAF1F7", zorder=0)
        axis.plot(d["time_ns"], d[f"silicon_{field}"], color=SIL, lw=6.0,
                  alpha=0.32, label="HSPICE transistor", zorder=2)
        axis.plot(d["time_ns"], d[f"hspice_{field}"], color=SIL, lw=2.2,
                  label="HSPICE native IBIS", zorder=4)
        axis.plot(d["time_ns"], d[f"pybis_{field}"], color=GATE, lw=2.4,
                  label="gate-state", zorder=3)
        axis.axvline(rev, color=REV, ls="--", lw=1.8)
        axis.set_ylabel(label)
        axis.grid(alpha=0.3)
    axes[0].set_xlim(5.4, 11.0)
    axes[0].set_ylim(-0.25, 1.25)
    axes[0].legend(loc="upper right", ncol=3, fontsize=13)
    title(axes[0], "io_buf", "2354 ps pulse", "Ku and Kd")
    axes[1].set_xlabel("Time (ns)")
    save(fig, OUT / "recap_kukd.png")


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


def fixture_kukd() -> None:
    """V-T and Ku under five different R/L/C characterisation fixtures.

    Re-solves from the runs test_kukd_fixture_variants.py already made, which are
    cached, so nothing is re-simulated. The study's own figure is four panels at
    13 x 12 in -- correct for print, far too tall for a slide -- so this redraws
    the two panels that carry the argument at slide size.
    """
    # Imported lazily and taken from the archived module itself: adding
    # tools/pybis2spice to this file's path made `pybis2spice` resolve to the
    # outer repo directory instead of the inner package.
    import test_kukd_fixture_variants as fx  # noqa: PLC0415
    import run_three_buffer_realistic_pulse_campaign as base  # noqa: PLC0415

    pb = fx.pb

    device = next(d for d in base.DEVICES if d.device_id == "io_buf")
    rows = {(r["device"], r["direction"], str(int(float(r["target_percent"])))): r
            for r in fx.read_csv(fx.SWEEP / "selection.csv")}
    chosen = rows.get(("io_buf", "short_high", "70"))
    if chosen is None:
        print("  fixture_kukd: no selection row")
        return
    width_ns = float(chosen["pulse_width_ps"]) / 1000.0
    case = base.PulseCase("short_high_swing70", 0.050, "short_high", width_ns,
                          22.0, "70% native swing")
    ibis_data = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                             model_name=device.model, component_name=device.component)
    root = fx.OUT / "hspice_fixtures" / "io_buf" / "short_high_swing70"

    got = []
    for variant, l_fix, c_fix in fx.VARIANTS:
        tag = f"l{l_fix * 1e9:g}n_c{c_fix * 1e12:g}p"
        try:
            runs = [fx.run_variant(device, case, v, l_fix, c_fix, root / tag / name,
                                   fx.default_hspice(), 300)
                    for v, name in ((0.0, "vfix_0"), (device.supply_v, "vfix_vcc"))]
        except Exception as exc:                       # noqa: BLE001
            print(f"  fixture_kukd: {variant} unavailable ({str(exc)[:40]})")
            continue
        got.append((variant, runs[0], fx.solve_from_measured(ibis_data, runs)))
    if len(got) < 2:
        print("  fixture_kukd: not enough fixtures solved yet")
        return

    lo, hi = 5.0 - 0.3, 5.0 + width_ns + 3.0
    fig, ax = plt.subplots(figsize=(HW, HH))
    for (variant, run, _sol), colour in zip(got, fx.COLOURS):
        ax.plot(run[0] * 1e9, run[1], color=colour, lw=2.4, label=variant)
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    # Short title: the half-width box clips a three-part one.
    title(ax, "io_buf 70% swing", "V-T on five fixtures")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=11)
    save(fig, OUT / "fixture_vt.png")

    fig, ax = plt.subplots(figsize=(HW, HH))
    ax.axhspan(-0.05, 1.05, color="#EAF1F7", zorder=0)
    for (variant, _run, sol), colour in zip(got, fx.COLOURS):
        ax.plot(sol[:, 0] * 1e9, sol[:, 1], color=colour, lw=2.4, label=variant)
    ax.set_xlim(lo, hi)
    ax.set_ylim(-0.35, 1.25)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Ku")
    title(ax, "io_buf 70% swing", "Ku on each fixture")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=11)
    save(fig, OUT / "fixture_ku.png")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (recap, clean_edge, stress_pair, timing_shift, offset_chain,
               command_mechanism, command_pad, offset_removed,
               variant_pair, fixture_kukd):
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
