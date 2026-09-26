#!/usr/bin/env python3
"""Slide figures for the 2026-09-17 deck: inside the buffer, and the open question.

Conventions inherited from build_deck_figures.py, which the 0904 README sets out:

* **Simulation figures only.** No bar charts, no scatter plots, no schematics. A number is
  explained by listing it on the slide.
* **Drawn at the size they are placed**, so axis text is the size it claims. The study's
  figures are 17-20 in wide; dropped into a 12 in slide box their labels come out at 5-7 pt.
  Everything here is drawn at 12.2 x 5.2 (full width) or 6.0 x 4.9 (half) with 14-17 pt fonts.
* Pad and coefficients side by side for the same case; bold pipe-separated titles
  (device | pulse | quantity); the transistor as a thick pale trace with the models drawn
  over it; the reversal marked with a dashed line.
* The shipped model keeps the purple the audience already knows from the 0904 and 0911
  decks. The real gate replayed into the model is teal, the one colour not yet spoken for.

Nothing is re-simulated - every panel is rebuilt from raw output already on disk.

    py -3.14 scripts/build_0917_deck_figures.py
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
import gate_ramp_prototype as gp  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402

R = ROOT / "results"
OUT = R / "meeting_deck_2026-09-17" / "figures"
MATRIX = R / "stress_method_matrix_2026-08-20"
CASC = R / "gate_cascade_prototype_2026-09-09"
NPZ = R / "method_animations_2026-09-17" / "method_data.npz"

W, H = 12.2, 5.2
HW, HH = 6.0, 4.9
DPI = 200
plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 17, "axes.labelsize": 16,
    "xtick.labelsize": 14, "ytick.labelsize": 14, "legend.fontsize": 13,
    "axes.linewidth": 1.2, "lines.linewidth": 2.4, "grid.alpha": 0.3,
})

SIL, NAT = fg.SILICON, fg.NATIVE
GATE = "#7B2CBF"      # the shipped gate-state build, as in the 0904/0911 decks
REPLAY = "#0E9F9F"    # the transistor's own gate node, replayed into the model
TRIAL = "#D97706"     # a prototype under test (cascade, slowed gate)
REV = "#8A8A8A"


def read(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open()))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=DPI)
    plt.close(fig)
    print(f"  {name}.png")


def title(ax, *parts: str) -> None:
    ax.set_title("  |  ".join(parts), fontweight="bold")


def raw_pad(path: Path):
    """(t_ns, pad) from an ngspice run, or None if the run is not on disk."""
    if not path.is_file():
        print(f"    (missing {path.relative_to(ROOT)})")
        return None
    raw = sl.parse_ngspice_raw(path)
    return sl.time_ns(raw), sl.trace(raw, "out")


def transistor_pad(dev: str, depth: int):
    """The HSPICE transistor reference at one stressed width, and its reversal time."""
    gp.VARIANT_NAME = dev
    for d, w, case in gp.cases(dev):
        if d == depth:
            tr0 = case / "run.tr0"
            if not tr0.is_file():            # the 09-04 variant cases keep it one level down
                tr0 = case / "transistor" / "run.tr0"
            t, v = gp.tr0_pad(tr0)
            return t, v, 5.0 + w
    raise SystemExit(f"no transistor case for {dev} at {depth} ps")


# --------------------------------------------------------------------------- recap
def _pair(d, t_rev, xlim, name, *, dev, pulse, pad_keys, k_keys):
    """A pad figure and a Ku/Kd figure, sized to sit side by side on one slide."""
    fig, ax = plt.subplots(figsize=(HW, HH))
    for key, colour, lw, alpha, label, z in pad_keys:
        if key in d:
            ax.plot(d["time_ns"], d[key], color=colour, lw=lw, alpha=alpha, label=label, zorder=z)
    ax.axvline(t_rev, color=REV, ls="--", lw=1.6, label="reverse edge")
    ax.set_xlim(*xlim)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, dev, pulse, "pad voltage")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=12)
    save(fig, f"{name}_pad")

    fig, axes = plt.subplots(2, 1, figsize=(HW, HH), sharex=True)
    for axis, field, label in ((axes[0], "ku", "Ku"), (axes[1], "kd", "Kd")):
        axis.axhspan(-0.05, 1.05, color="#EAF1F7", zorder=0)
        for key, colour, lw, alpha, lab, z in k_keys:
            col = f"{key}_{field}"
            if col in d:
                axis.plot(d["time_ns"], d[col], color=colour, lw=lw, alpha=alpha, label=lab, zorder=z)
        axis.axvline(t_rev, color=REV, ls="--", lw=1.6)
        axis.set_ylabel(label)
        axis.grid(alpha=0.3)
    axes[0].set_xlim(*xlim)
    axes[0].legend(loc="upper left", fontsize=11, ncol=2)
    title(axes[0], dev, pulse, "Ku and Kd")
    axes[1].set_xlabel("Time (ns)")
    save(fig, f"{name}_kukd")


def recap() -> None:
    """ex2 at 810 ps: the defect, in pad and in coefficients. Same case as the film."""
    src = MATRIX / "delay_cmd" / "waveforms" / "ex2_short_high_w810ps.csv"
    if not src.exists():
        print("  recap: missing case CSV")
        return
    d = read(src)
    _pair(d, 5.81, (5.3, 8.4), "recap", dev="ex2", pulse="810 ps pulse",
          pad_keys=[("silicon_pad", SIL, 5.0, 0.30, "HSPICE transistor", 2),
                    ("hspice_pad", SIL, 2.0, 1.0, "HSPICE native IBIS", 4),
                    ("pybis_pad", GATE, 2.2, 1.0, "our gate-state model", 3)],
          k_keys=[("silicon", SIL, 5.0, 0.30, "HSPICE transistor", 2),
                  ("hspice", SIL, 2.0, 1.0, "HSPICE native IBIS", 4),
                  ("pybis", GATE, 2.2, 1.0, "our gate-state model", 3)])


# --------------------------------------------------------------------------- the map
def ku_vs_gate() -> None:
    """Ku against the real gate node: one curve, the output stage has no memory of its own."""
    if not NPZ.is_file():
        print("  ku_vs_gate: missing npz")
        return
    D = np.load(NPZ)
    g, ku = D["map_gate"], D["map_ku"]
    fig, axes = plt.subplots(1, 2, figsize=(W, H))
    axes[0].plot(D["map_t"], ku, color=REPLAY, lw=2.6)
    axes[0].set_xlabel("Time (ns)")
    axes[0].set_ylabel("Ku, solved from two fixtures")
    title(axes[0], "ex2", "full swing", "Ku against time")
    axes[0].grid(alpha=0.3)
    axes[1].plot(g, ku, color=REPLAY, lw=2.6)
    axes[1].set_xlabel("gate node n4, 0 = rest, 1 = fully on")
    axes[1].set_ylabel("Ku")
    title(axes[1], "ex2", "the same points", "Ku against the gate")
    axes[1].grid(alpha=0.3)
    for ax in axes:
        ax.set_ylim(-0.15, 1.15)
    save(fig, "ku_vs_gate")


# --------------------------------------------------------------------------- the shipped gate
def gate_vs_real_three() -> None:
    """The shipped model's own gate node against the transistor's, all three buffers.

    Deepest stressed width each. The shipped gate is a fixed delay into a fixed ramp; the
    real one is the probed predriver node. This is the figure the whole deck turns on.
    """
    specs = (("ex2", "ex2_c1.7", 810, "v(xdut.n4)", "n4"),
             ("inv_chain", "inv_chain_c0.6", 104, "v(xdut.vout7)", "vout7"),
             ("io_buf", "io_buf", 1505, "v(xdut.n2)", "n2"))
    fig, axes = plt.subplots(1, 3, figsize=(W, H))
    for ax, (dev, var, depth, node, short) in zip(axes, specs):
        full_p = psp.OUT / dev / "full" / "run.tr0"
        short_p = psp.OUT / dev / f"w{depth}" / "run.tr0"
        ship_p = CASC / var / "shipped" / f"d{depth}" / "run.raw"
        if not (full_p.is_file() and short_p.is_file()):
            print(f"    gate_vs_real: no probe runs for {dev}")
            ax.set_visible(False)
            continue
        full = psp.parse_tr0(full_p)
        tf = np.asarray(full["time"], float) * 1e9
        vf = psp.signals(full, [node])
        sh = psp.parse_tr0(short_p)
        ts = np.asarray(sh["time"], float) * 1e9
        vs = psp.signals(sh, [node])
        g_full, _, _ = psp.normalise(tf, vf[node], tf, vf[node])
        g_short, _, _ = psp.normalise(tf, vf[node], ts, vs[node])
        rev = 5.0 + depth / 1000.0
        ax.plot(tf - 5.0, g_full, color=SIL, lw=4.0, alpha=0.30, label="real gate, full swing")
        ax.plot(ts - 5.0, g_short, color=SIL, lw=2.6, label=f"real gate, {depth} ps")
        peak_real = float(np.interp(np.linspace(0, rev - 5.0 + 3.0, 2000), ts - 5.0, g_short).max())
        note = f"real gate stops at {peak_real:.2f}"
        if ship_p.is_file():
            raw = sl.parse_ngspice_raw(ship_p)
            tm, gm = sl.time_ns(raw), sl.signal(raw, "v(x1.gup)")
            ax.plot(tm - 5.0, gm, color=GATE, lw=2.4, label=f"shipped GUP, {depth} ps")
            peak_ship = float(gm[(tm >= 5.0) & (tm <= rev + 3.0)].max())
            note += f"\nshipped GUP reaches {peak_ship:.2f}"
        else:
            print(f"    gate_vs_real: no shipped run for {dev}")
        ax.axvline(rev - 5.0, color=REV, ls="--", lw=1.6)
        xmax = {"ex2": 3.2, "inv_chain": 0.6, "io_buf": 5.5}[dev]
        ax.set_xlim(-0.1, xmax)
        ax.set_ylim(-0.08, 1.12)
        ax.set_xlabel("Time from the input edge (ns)")
        ax.set_ylabel("gate, 0 to 1")
        title(ax, dev, f"{depth} ps", short)
        ax.text(0.98, 0.04, note, transform=ax.transAxes, ha="right", va="bottom",
                fontsize=13, bbox=dict(facecolor="white", edgecolor="#cccccc"))
        ax.grid(alpha=0.3)
        ax.legend(loc="upper left", fontsize=10.5)
    save(fig, "gate_vs_real_three")


# --------------------------------------------------------------------------- pad overlays
def pad_overlay(name: str, dev: str, depth: int, pulse: str, builds, xlim, decorate=None) -> None:
    """Transistor (pale), then each build over it, one stressed width."""
    t_si, si, rev = transistor_pad(dev, depth)
    peak = float(si[(t_si >= rev - 0.3) & (t_si <= rev + 2.6)].max())
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(t_si, si, color=SIL, lw=5.0, alpha=0.30, label="HSPICE transistor", zorder=2)
    lines = []
    for label, path, colour in builds:
        got = raw_pad(path)
        if got is None:
            continue
        t, v = got
        err = 100.0 * (float(v[(t >= rev - 0.3) & (t <= rev + 2.6)].max()) - peak) / peak
        ax.plot(t, v, color=colour, lw=2.4, label=f"{label}   {err:+.1f} %", zorder=3)
        lines.append((label, err))
    ax.axvline(rev, color=REV, ls="--", lw=1.6, label="reverse edge")
    ax.set_xlim(*xlim)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, dev, pulse, "pad voltage")
    ax.grid(alpha=0.3)
    if decorate is not None:
        decorate(ax, rev)
    ax.legend(loc="upper right", fontsize=13)
    save(fig, name)
    for label, err in lines:
        print(f"      {label:32s} {err:+6.1f} %")


def replay_ex2() -> None:
    pad_overlay("replay_ex2", "ex2", 810, "810 ps pulse",
                [("shipped gate-state", CASC / "ex2_c1.7" / "shipped" / "d810" / "run.raw", GATE),
                 ("real gate put in, file's curve", CASC / "ex2_c1.7" / "gate_replay" / "d810" / "run.raw", REPLAY)],
                (5.3, 8.4))


def replay_iobuf() -> None:
    pad_overlay("replay_iobuf", "io_buf", 2090, "2090 ps pulse",
                [("shipped gate-state", CASC / "io_buf" / "shipped" / "d2090" / "run.raw", GATE),
                 ("real gates put in", CASC / "io_buf" / "gate_replay" / "d2090" / "run.raw", REPLAY)],
                (6.6, 10.5))


def cascade_ex2() -> None:
    pad_overlay("cascade_ex2", "ex2", 810, "810 ps pulse",
                [("shipped gate-state", CASC / "ex2_c1.7" / "shipped" / "d810" / "run.raw", GATE),
                 ("RC cascade, N = 5", CASC / "ex2" / "cascade5" / "d810" / "run.raw", TRIAL)],
                (5.3, 8.4))


def slew_ex2() -> None:
    pad_overlay("slew_ex2", "ex2", 810, "810 ps pulse",
                [("shipped gate-state", CASC / "ex2" / "shipped" / "d810" / "run.raw", GATE),
                 ("gate slowed to 500 ps", CASC / "ex2" / "slew500ps" / "d810" / "run.raw", TRIAL)],
                (5.3, 8.4))


# ------------------------------------------------------- reversal-entry rules
def reversal_rules() -> None:
    """io_buf at 1634 ps: the reversal-entry rules that ran on this case, on one pad axis.
    t-matching and value-matching only ever ran on io_buf, so io_buf is the buffer; 1634 ps
    is the shallowest width all of them solved. delay_cmd is the shipped gate-state build."""
    case = "io_buf_short_high_w1634ps.csv"
    # The gated builds (time_match_hybrid, coeff_match), as the 08-25 figures used: the
    # ungated ...ReplayFull builders replace the whole waveform path and come up on the
    # wrong rail before the pulse, which is a defect of that build, not of the rule.
    runs = [("legacy", "legacy: replay from the edge", "#2E86C1", 2.0),
            ("coeff_match", "Ku/Kd value-matching", "#C0392B", 2.0),
            ("time_match_hybrid", "t-matching", TRIAL, 2.0)]
    # gate-matching is left out: it leaves the transistor 0.7 ns before the reversal, so it
    # says nothing about entering one. The shipped build is left out: this slide is the
    # rules that failed.
    fig, ax = plt.subplots(figsize=(W, H))
    first = True
    for key, label, colour, lw in runs:
        src = MATRIX / key / "waveforms" / case
        if not src.exists():
            print(f"    (missing {src.relative_to(ROOT)})")
            continue
        d = read(src)
        if first:  # the transistor and native columns are identical in every file
            ax.plot(d["time_ns"], d["silicon_pad"], color=SIL, lw=5.0, alpha=0.30,
                    label="HSPICE transistor", zorder=2)
            ax.plot(d["time_ns"], d["hspice_pad"], color=NAT, lw=2.4,
                    label="HSPICE native IBIS", zorder=3)
            first = False
        ax.plot(d["time_ns"], d["pybis_pad"], color=colour, lw=lw, label=label, zorder=4)
    ax.axvline(5.0 + 1.634, color=REV, ls="--", lw=1.6, label="reverse edge")
    ax.set_xlim(4.8, 9.2)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Pad voltage (V)")
    title(ax, "io_buf", "1634 ps pulse", "the reversal-entry rules, pad voltage")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=12, ncol=2)
    save(fig, "reversal_rules")


def _pwl_table(subckt: Path, source: str) -> np.ndarray:
    """A Ku/Kd table out of a generated subcircuit, as (t, value) rows.
    Same parse as scripts/archive/build_value_match_misalignment_demo.py."""
    import re
    text = subckt.read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"^B\S*\s+{re.escape(source)}\s+0\s+V\s*=\s*pwl\(", text, re.MULTILINE)
    if not m:
        raise ValueError(f"source {source} not found in {subckt}")
    line = text[m.start(): text.find("\n", m.start())]
    payload = line.split("),", 2)[2].split("),", 1)[1].rsplit(")", 1)[0]
    nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", payload)]
    arr = np.asarray(nums, dtype=float).reshape(-1, 2)
    return arr[np.argsort(arr[:, 0])]


def value_match_split() -> None:
    """One coherent state, two falling-table times: why value-matching cannot enter a reversal.
    Numbers from the 06-25 demo's CSV; the tables from the subcircuit that demo parsed."""
    demo = R / "io_buf_value_match_misalignment_demo_2026-06-25"
    sub = (R / "io_buf_value_matched_replay_redo_2026-06-25" / "debug_timeout" / "stop_7p25ns"
           / "driver_OutputInput_Typical.sub")
    if not sub.exists():
        print(f"    (missing {sub.relative_to(ROOT)})")
        return
    s = read(demo / "value_match_misalignment_summary.csv")
    ku, kd = s["pre_ku"][0], s["pre_kd"][0]
    tku, tkd, tmid = s["pre_tf_ku"][0], s["pre_tf_kd"][0], s["pre_tf_start"][0]
    tables = {"Ku": _pwl_table(sub, "HKUF0"), "Kd": _pwl_table(sub, "HKDF0")}
    fig, axes = plt.subplots(1, 2, figsize=(W, H - 0.3), sharey=True)
    for ax, (name, val, tf, colour) in zip(axes, (("Ku", ku, tku, "#0072B2"), ("Kd", kd, tkd, "#D55E00"))):
        tab = tables[name]
        ax.axvspan(tku, tkd, color="#FFF4D6", zorder=0)
        ax.plot(tab[:, 0], tab[:, 1], color=colour, lw=2.6, label=f"{name} falling table", zorder=3)
        ax.axhline(val, color=colour, ls=":", lw=1.6, zorder=2)
        ax.axvline(tf, color=colour, ls="--", lw=1.8, zorder=2)
        ax.axvline(tmid, color="#6F2DBD", ls="-.", lw=1.6, zorder=2, label=f"forced midpoint {tmid:.3f} ns")
        ax.plot([tf], [val], "o", color=colour, ms=10, zorder=5)
        ax.annotate(f"{name} = {val:.3f} now\nsits at {tf:.3f} ns", xy=(tf, val),
                    xytext=(tf + (0.55 if name == "Ku" else -1.55), 0.62), fontsize=14, color=colour,
                    arrowprops={"arrowstyle": "->", "color": colour, "lw": 1.4})
        ax.set_xlim(0, 4.2)
        ax.set_ylim(-0.12, 1.08)
        ax.set_xlabel("Falling-table time (ns)")
        ax.grid(alpha=0.3)
        ax.legend(loc="center right", fontsize=12)
        title(ax, "io_buf", "2 ns pulse", f"{name} falling table")
    axes[0].set_ylabel("coefficient")
    save(fig, "value_match_split")


# ------------------------------------------------- one buffer at a time (the 25-slide reflow)
MEAS = "#2E8B57"      # a map measured on the transistor, and the build that uses it

GATE_SPECS = {"ex2": ("ex2_c1.7", 810, "v(xdut.n4)", "n4", 3.2),
              "inv_chain": ("inv_chain_c0.6", 104, "v(xdut.vout7)", "vout7", 0.6),
              "io_buf": ("io_buf", 2090, "v(xdut.n2)", "n2", 5.5)}


def gate_vs_real(dev: str) -> None:
    """The transistor's gate node against the shipped model's GUP, one buffer, one width.
    io_buf is at 2090 ps, not its deepest width: that is where its gate replay ran."""
    var, depth, node, short, xmax = GATE_SPECS[dev]
    full = psp.parse_tr0(psp.OUT / dev / "full" / "run.tr0")
    sh = psp.parse_tr0(psp.OUT / dev / f"w{depth}" / "run.tr0")
    tf = np.asarray(full["time"], float) * 1e9
    ts = np.asarray(sh["time"], float) * 1e9
    vf, vs = psp.signals(full, [node]), psp.signals(sh, [node])
    g_full, _, _ = psp.normalise(tf, vf[node], tf, vf[node])
    g_short, _, _ = psp.normalise(tf, vf[node], ts, vs[node])
    rev = 5.0 + depth / 1000.0
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(tf - 5.0, g_full, color=SIL, lw=5.0, alpha=0.30, label="real gate, full swing")
    ax.plot(ts - 5.0, g_short, color="#111111", lw=2.8, label=f"real gate, {depth} ps pulse")
    sel = (ts >= 5.0) & (ts <= rev + 3.0)
    pr = float(g_short[sel].max())
    raw = sl.parse_ngspice_raw(CASC / var / "shipped" / f"d{depth}" / "run.raw")
    tm, gm = sl.time_ns(raw), sl.signal(raw, "v(x1.gup)")
    pm = float(gm[(tm >= 5.0) & (tm <= rev + 3.0)].max())
    ax.plot(tm - 5.0, gm, color=GATE, lw=2.6, label=f"our gate (GUP), {depth} ps pulse")
    ax.axvline(rev - 5.0, color=REV, ls="--", lw=1.6, label="reverse edge")
    ax.axhline(pr, color="#111111", ls=":", lw=1.2)
    ax.axhline(pm, color=GATE, ls=":", lw=1.2)
    ax.text(xmax * 0.985, pr, f"real gate reaches {pr:.2f} ", ha="right", va="bottom" if pr >= pm else "top", fontsize=14)
    ax.text(xmax * 0.985, pm, f"our gate reaches {pm:.2f} ", ha="right", va="bottom" if pm > pr else "top",
            fontsize=14, color=GATE)
    ax.set_xlim(-0.05 * xmax, xmax)
    ax.set_ylim(-0.08, 1.12)
    ax.set_xlabel("Time from the input edge (ns)")
    ax.set_ylabel(f"gate {short}, 0 = rest, 1 = fully on")
    title(ax, dev, f"{depth} ps pulse", "the real gate against ours")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left" if dev == "io_buf" else "center right", fontsize=12.5)
    save(fig, f"gate_vs_real_{dev}")
    print(f"      {dev}: real {pr:.2f}, ours {pm:.2f}")


def gate_vs_real_all() -> None:
    for dev in GATE_SPECS:
        gate_vs_real(dev)


def static_map_ex2() -> None:
    """Ku against time, the gate against time, then one against the other: time drops out."""
    D = np.load(NPZ)
    t, g, ku = D["map_t"], D["map_gate"], D["map_ku"]
    fig, axes = plt.subplots(1, 3, figsize=(W, H - 0.2))
    axes[0].plot(t, ku, color=REPLAY, lw=2.6)
    axes[0].set_xlabel("Time (ns)"); axes[0].set_ylabel("Ku")
    axes[0].set_title("a. Ku, solved from two fixtures", fontweight="bold", fontsize=15)
    axes[1].plot(t, g, color="#111111", lw=2.6)
    axes[1].set_xlabel("Time (ns)"); axes[1].set_ylabel("gate n4, 0 to 1")
    axes[1].set_title("b. the gate, probed", fontweight="bold", fontsize=15)
    axes[2].plot(g, ku, color=REPLAY, lw=2.6)
    axes[2].set_xlabel("gate n4, 0 to 1"); axes[2].set_ylabel("Ku")
    axes[2].set_title("c. Ku against the gate", fontweight="bold", fontsize=15)
    for ax in axes:
        ax.set_ylim(-0.15, 1.15); ax.grid(alpha=0.3)
    fig.suptitle("ex2  |  full swing", fontweight="bold", fontsize=17)
    save(fig, "static_map_ex2")


def replay_inv() -> None:
    base = CASC / "inv_chain_c0.6"
    pad_overlay("replay_inv", "inv_chain", 104, "104 ps pulse",
                [("shipped gate-state", base / "shipped" / "d104" / "run.raw", GATE),
                 ("real gate, file's curve", base / "gate_replay" / "d104" / "run.raw", REPLAY),
                 ("real gate, measured curve", base / "gate_replay_silicon_full" / "d104" / "run.raw", MEAS)],
                (5.0, 5.9))


def inv_map() -> None:
    """The two Ku-against-gate maps the inv_chain replays used, gate rising. Read out of the
    subcircuits those runs were built from, so the figure is the maps that produced the pads."""
    base = CASC / "inv_chain_c0.6"
    f_map = _pwl_table(base / "gate_replay" / "driver_replay_full.sub", "KUGATE_ON")
    m_map = _pwl_table(base / "gate_replay_silicon_full" / "driver_silicon_full.sub", "KUGATE_ON")
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(f_map[:, 0], f_map[:, 1], color=REPLAY, lw=2.8, label="implied by the IBIS file")
    ax.plot(m_map[:, 0], m_map[:, 1], color=MEAS, lw=2.8, label="measured on the transistor")
    g0 = 0.7
    kf, km = float(np.interp(g0, f_map[:, 0], f_map[:, 1])), float(np.interp(g0, m_map[:, 0], m_map[:, 1]))
    ax.axvline(g0, color=REV, ls="--", lw=1.4)
    ax.plot([g0, g0], [kf, km], "o", color="#111111", ms=8, zorder=5)
    ax.annotate(f"gate 70 % on:\nfile says Ku = {kf:.2f}\ntransistor says {km:.2f}", xy=(g0, (kf + km) / 2),
                xytext=(0.12, 0.62), fontsize=15, arrowprops={"arrowstyle": "->", "lw": 1.4})
    ax.set_xlim(0, 1); ax.set_ylim(-0.12, 1.1)
    ax.set_xlabel("gate vout7, 0 = off, 1 = fully on"); ax.set_ylabel("Ku")
    title(ax, "inv_chain", "gate rising", "how much pull-up for how much gate")
    ax.grid(alpha=0.3); ax.legend(loc="lower right", fontsize=14)
    save(fig, "inv_map")
    print(f"      at g = 0.7: file {kf:.2f}, measured {km:.2f}")


# ------------------------------------------------------------ second reflow (09-18 feedback)
HILITE = "#C05621"    # the gate node, the same orange as its box on the schematic slide
PADCOL = "#B8860B"


def _norm_pair(dev: str, depth: int, node: str):
    """(t_full, g_full, t_short, g_short), time from the input edge, node on its own 0-1 swing."""
    full = psp.parse_tr0(psp.OUT / dev / "full" / "run.tr0")
    sh = psp.parse_tr0(psp.OUT / dev / f"w{depth}" / "run.tr0")
    tf = np.asarray(full["time"], float) * 1e9
    ts = np.asarray(sh["time"], float) * 1e9
    vf, vs = psp.signals(full, [node]), psp.signals(sh, [node])
    g_full, _, _ = psp.normalise(tf, vf[node], tf, vf[node])
    g_short, _, _ = psp.normalise(tf, vf[node], ts, vs[node])
    return tf - 5.0, g_full, ts - 5.0, g_short


WALKS = {
    "ex2": (810, 4.0, [("", ["v(in_dig)", "v(xdut.n2)", "v(xdut.n3)", "v(xdut.n4)", "v(pad_sp)"], "v(xdut.n4)",
                        "n4 - the gate of the output stage")]),
    "inv_chain": (104, 0.8, [("", ["v(in_dig)"] + [f"v(xdut.vout{k})" for k in range(1, 8)] + ["v(pad_sp)"],
                              "v(xdut.vout7)", "vout7 - the gate of the output stage")]),
    "io_buf": (2090, 5.5, [("pull-up path", ["v(in_dig)", "v(xdut.n2)", "v(pad_sp)"], "v(xdut.n2)",
                            "n2 - PMOS gate (pull-up)"),
                           ("pull-down path", ["v(in_dig)", "v(xdut.n1)", "v(xdut.nand_n3)", "v(xdut.n3)", "v(pad_sp)"],
                            "v(xdut.n3)", "n3 - NMOS gate (pull-down); 1 = off")]),
}


def walk(dev: str) -> None:
    """The pulse down the chain, the gate node drawn in the schematic's orange. io_buf has two
    predriver paths and gets one panel each."""
    depth, xmax, paths = WALKS[dev]
    fig, axes = plt.subplots(len(paths), 1, figsize=(W, 4.9 if len(paths) == 1 else 5.9), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, (pname, nodes, gate, gate_label) in zip(axes, paths):
        mids = [n for n in nodes if n not in ("v(in_dig)", "v(pad_sp)", gate)]
        shades = plt.cm.Blues(np.linspace(0.45, 0.85, max(len(mids), 1)))
        for n in nodes:
            _, _, t, g = _norm_pair(dev, depth, n)
            short = n.split(".")[-1].rstrip(")")
            if n == "v(in_dig)":
                ax.plot(t, g, color="#222222", lw=2.2, label="input")
            elif n == "v(pad_sp)":
                ax.plot(t, g, color=PADCOL, lw=3.2, label="pad", zorder=6)
            elif n == gate:
                ax.plot(t, g, color=HILITE, lw=3.2, label=gate_label, zorder=5)
            else:
                ax.plot(t, g, color=shades[mids.index(n)], lw=1.8, label=short)
        ax.axvline(depth / 1000.0, color=REV, ls="--", lw=1.6)
        ax.set_ylim(-0.2, 1.15)
        ax.set_ylabel("0 = rest, 1 = full swing", fontsize=13)
        ax.grid(alpha=0.3)
        ax.legend(loc="center left", bbox_to_anchor=(1.005, 0.5), fontsize=11.5, frameon=False)
        if pname:
            ax.set_title(pname, loc="left", fontsize=15, fontweight="bold")
    if dev == "io_buf":
        _, _, t, g = _norm_pair(dev, depth, "v(pad_sp)")
        sel = (t > 3.2) & (t < 5.0)
        tb = float(t[sel][g[sel].argmax()])
        axes[0].annotate("the bump: the pull-down" + chr(10) + "turns back on", xy=(tb, float(g[sel].max())),
                         xytext=(tb - 0.55, 0.55), fontsize=13, arrowprops={"arrowstyle": "->", "lw": 1.3})
        print(f"      io_buf bump at {tb:.2f} ns after the input edge, {tb - depth / 1000:.2f} after the reversal")
    axes[0].set_xlim(-0.05 * xmax, xmax)
    axes[-1].set_xlabel("Time from the input edge (ns)")
    if len(paths) == 1:
        title(axes[0], dev, f"{depth} ps pulse", "every node, input to pad")
    else:
        fig.suptitle(f"{dev}  |  {depth} ps pulse  |  every node, input to pad", fontweight="bold", fontsize=17)
    save(fig, f"walk_{dev}")


def walks() -> None:
    for dev in WALKS:
        walk(dev)


def _turn(t, g, depth):
    sel = (t >= 0.0) & (t <= depth / 1000.0 + 3.0)
    return float(t[sel][g[sel].argmax()])


def _gate_and_k(ax_g, ax_k, dev, var, depth, node, model_sig, k_sig, k_col, k_name, xmax, flip=False):
    tf, g_full, ts, g_short = _norm_pair(dev, depth, node)
    raw = sl.parse_ngspice_raw(CASC / var / "shipped" / f"d{depth}" / "run.raw")
    tm = sl.time_ns(raw) - 5.0
    gm, km = sl.signal(raw, model_sig), sl.signal(raw, k_sig)
    if flip:   # the probe's 0 is "at rest"; the model's node may call rest 1
        g_full, g_short = 1.0 - g_full, 1.0 - g_short
    ax_g.plot(tf, g_full, color=SIL, lw=4.5, alpha=0.30, label="real gate, full swing")
    ax_g.plot(ts, g_short, color="#111111", lw=2.6, label="real gate")
    ax_g.plot(tm, gm, color=GATE, lw=2.4, label="our gate")
    ax_g.axvline(depth / 1000.0, color=REV, ls="--", lw=1.6, label="reverse edge")
    src = MATRIX / "delay_cmd" / "waveforms" / f"{dev}_short_high_w{depth}ps.csv"
    if src.exists():
        d = read(src)
        x, k = d["time_ns"] - 5.0, d[f"silicon_{k_col}"].copy()
        for edge in (0.0, depth / 1000.0):
            k[(x > edge - 0.02) & (x < edge + 0.09)] = np.nan
        ax_k.plot(x, k, color=SIL, lw=4.5, alpha=0.30,
                  label=f"{k_name}, transistor")
    else:
        print(f"      (no transistor {k_name} for {dev} at {depth} ps)")
    ax_k.plot(tm, km, color=GATE, lw=2.4, label=f"{k_name}, our model")
    ax_k.axvline(depth / 1000.0, color=REV, ls="--", lw=1.6)
    for ax in (ax_g, ax_k):
        ax.set_xlim(-0.05 * xmax, xmax)
        ax.set_ylim(-0.15, 1.25)
        ax.grid(alpha=0.3)
    ax_g.set_ylabel("gate, 0 to 1", fontsize=14)
    ax_k.set_ylabel(k_name, fontsize=14)
    return tm, gm, ts, g_short


def gate_step(dev: str) -> None:
    """Step 2: the real gate against ours (top), and what the pad actually sees, Ku (bottom)."""
    var, depth, node, short, xmax = GATE_SPECS[dev]
    if dev != "io_buf":
        fig, (a, b) = plt.subplots(2, 1, figsize=(W, 5.7), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
        tm, gm, ts, gs = _gate_and_k(a, b, dev, var, depth, node, "v(x1.gup)", "v(x1.ku)", "ku", "Ku", xmax)
        t_real, t_ours = _turn(ts, gs, depth), _turn(tm, gm, depth)
        for ax in (a, b):
            ax.axvline(t_real, color="#111111", ls=":", lw=1.3)
            ax.axvline(t_ours, color=GATE, ls=":", lw=1.3)
        a.annotate(f"ours turns round\n{1000 * (t_ours - t_real):.0f} ps late", xy=(t_ours, float(gm.max())),
                   xytext=(t_ours + 0.12 * xmax, 0.35), fontsize=14, color=GATE,
                   arrowprops={"arrowstyle": "->", "color": GATE, "lw": 1.3})
        a.legend(loc="upper right", fontsize=11.5, ncol=2)
        b.legend(loc="upper right", fontsize=11.5)
        b.set_xlabel("Time from the input edge (ns)")
        title(a, dev, f"{depth} ps pulse", f"the gate {short}, and the Ku it produces")
        print(f"      {dev}: real turns {t_real:.3f}, ours {t_ours:.3f}, late {1000 * (t_ours - t_real):.0f} ps")
    else:
        fig, axes = plt.subplots(2, 2, figsize=(W, 5.7), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
        raw = sl.parse_ngspice_raw(CASC / var / "shipped" / f"d{depth}" / "run.raw")
        gdn_rest = float(sl.signal(raw, "v(x1.gdn)")[0])
        flip = gdn_rest > 0.5
        print(f"      io_buf: model GDN at rest = {gdn_rest:.2f}; probe n3 {'flipped to match' if flip else 'as it is'}")
        _gate_and_k(axes[0][0], axes[1][0], dev, var, depth, "v(xdut.n2)", "v(x1.gup)", "v(x1.ku)", "ku", "Ku", xmax)
        _gate_and_k(axes[0][1], axes[1][1], dev, var, depth, "v(xdut.n3)", "v(x1.gdn)", "v(x1.kd)", "kd", "Kd", xmax, flip=flip)
        axes[0][0].set_title("pull-up: PMOS gate n2, and Ku", fontweight="bold", fontsize=15)
        axes[0][1].set_title("pull-down: NMOS gate n3 (1 = on), and Kd", fontweight="bold", fontsize=15)
        axes[0][0].legend(loc="upper left", fontsize=10.5)
        axes[1][0].legend(loc="upper left", fontsize=10.5)
        axes[1][1].legend(loc="lower right", fontsize=10.5)
        for ax in axes[1]:
            ax.set_xlabel("Time from the input edge (ns)")
        fig.suptitle(f"io_buf  |  {depth} ps pulse", fontweight="bold", fontsize=17)
    save(fig, f"gate_step_{dev}")


def gate_steps() -> None:
    for dev in GATE_SPECS:
        gate_step(dev)


def inv_why() -> None:
    """Why inv_chain's real gate made it worse, in time. Both runs carry the same real gate.
    The model keeps one Ku curve for a rising gate and one for a falling gate. From the file
    the two disagree; on the transistor they are nearly one. A full swing only ever uses one
    at a time; a short pulse has to jump between them at the top."""
    base = CASC / "inv_chain_c0.6"
    fig, axes = plt.subplots(1, 2, figsize=(W, H), sharey=True)
    for ax, sub, name in ((axes[0], "full", "full swing"), (axes[1], "d104", "104 ps pulse")):
        f = sl.parse_ngspice_raw(base / "gate_replay" / sub / "run.raw")
        m = sl.parse_ngspice_raw(base / "gate_replay_silicon_full" / sub / "run.raw")
        tf, tm = sl.time_ns(f) - 5.0, sl.time_ns(m) - 5.0
        kf, km = sl.signal(f, "v(x1.ku)"), sl.signal(m, "v(x1.ku)")
        ax.plot(tf, sl.signal(f, "v(x1.gup)"), color="#111111", lw=2.6, label="the real gate (same in both runs)")
        ax.plot(tm, km, color=MEAS, lw=2.6, label="Ku, curves measured on the transistor")
        ax.plot(tf, kf, color=REPLAY, lw=2.6, label="Ku, curves from the file")
        ax.set_xlim(0.22, 0.52)
        ax.set_ylim(-0.12, 1.3)
        ax.set_xlabel("Time from the input edge (ns)")
        ax.grid(alpha=0.3)
        ax.set_title("inv_chain  |  " + name, fontweight="bold", fontsize=15)
        if sub == "full":
            up = lambda t, k: float(np.interp(0.5, k[(t > 0.2) & (t < 0.5)], t[(t > 0.2) & (t < 0.5)]))
            ax.text(0.515, 0.45, "only the rising-gate curve" + chr(10) + "is ever used: both agree",
                    ha="right", fontsize=13)
            print(f"      full swing: the two Ku agree to {1000 * (up(tf, kf) - up(tm, km)):.0f} ps at Ku = 0.5")
        else:
            on, base_ = sl.signal(f, "v(x1.kugate_on)"), sl.signal(f, "v(x1.kugate_base)")
            i = int(np.argmax((tf > 0.3) & (np.abs(on - base_) > 0.05)))
            ts_ = float(tf[i])
            vals = {}
            for tag, r, t in (("file", f, tf), ("transistor", m, tm)):
                vals[tag] = tuple(float(np.interp(ts_, t, sl.signal(r, f"v(x1.{k})"))) for k in ("kugate_on", "kugate_off"))
            g_at = float(np.interp(ts_, tf, sl.signal(f, "v(x1.gup)")))
            ax.axvline(ts_, color=REV, ls="--", lw=1.6)
            ax.text(ts_ + 0.006, 1.24, f"the model jumps to its" + chr(10) + f"falling-gate curve (gate" + chr(10) + f"at {g_at:.2f}, still rising)",
                    fontsize=12.5, va="top")
            ax.text(0.515, 0.62, f"transistor: Ku {vals['transistor'][0]:.2f} -> {vals['transistor'][1]:.2f}",
                    ha="right", fontsize=13, color=MEAS)
            ax.text(0.515, 0.50, f"file: Ku {vals['file'][0]:.2f} -> {vals['file'][1]:.2f}",
                    ha="right", fontsize=13, color=REPLAY)
            print(f"      jump at {ts_:.3f} ns, gate {g_at:.2f}: file {vals['file']}, transistor {vals['transistor']}")
            print(f"      Ku peaks {km.max():.2f} (transistor's curves), {kf.max():.2f} (file's)")
    axes[0].set_ylabel("gate, and Ku")
    axes[0].legend(loc="upper left", fontsize=11.5)
    save(fig, "inv_why")


def replay_inv_split() -> None:
    base = CASC / "inv_chain_c0.6"
    pad_overlay("replay_inv_fail", "inv_chain", 104, "104 ps pulse",
                [("our model", base / "shipped" / "d104" / "run.raw", GATE),
                 ("real gate put in", base / "gate_replay" / "d104" / "run.raw", REPLAY)], (5.2, 5.6))
    pad_overlay("replay_inv_fixed", "inv_chain", 104, "104 ps pulse",
                [("real gate, Ku curve from the file", base / "gate_replay" / "d104" / "run.raw", REPLAY),
                 ("real gate, Ku curve from the transistor", base / "gate_replay_silicon_full" / "d104" / "run.raw", MEAS)],
                (5.2, 5.6))


def replay_iobuf_marked() -> None:
    def mark(ax, rev):
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle((rev + 1.3, -0.03), 1.6, 0.13, fill=False, ec=HILITE, lw=2.0, zorder=7))
        ax.text(rev + 2.1, 0.13, "the bump: next slide", ha="center", va="bottom", fontsize=13, color=HILITE)
    pad_overlay("replay_iobuf", "io_buf", 2090, "2090 ps pulse",
                [("our model", CASC / "io_buf" / "shipped" / "d2090" / "run.raw", GATE),
                 ("real gates put in", CASC / "io_buf" / "gate_replay" / "d2090" / "run.raw", REPLAY)],
                (6.6, 10.5), decorate=mark)


def iobuf_bump() -> None:
    """The bump at five pulse widths, from the reversal: the transistor's moves, ours does not."""
    widths = [2354, 2090, 1853, 1666, 1505]
    cols = plt.cm.viridis(np.linspace(0.05, 0.92, len(widths)))
    fig, axes = plt.subplots(1, 2, figsize=(W, H), sharey=True)
    out = {0: [], 1: []}
    for w, c in zip(widths, cols):
        t, v, rev = transistor_pad("io_buf", w)
        got = raw_pad(CASC / "io_buf" / "shipped" / f"d{w}" / "run.raw")
        for k, (tt, vv) in enumerate(((t, v), got)):
            x = tt - rev
            sel = (x > 1.3) & (x < 2.8)
            tb = float(x[sel][vv[sel].argmax()])
            out[k].append(tb)
            axes[k].plot(x, vv, color=c, lw=2.2, label=f"{w} ps pulse: +{tb:.2f} ns")
    for ax, name in zip(axes, ("the transistor", "our model")):
        ax.set_xlim(0.8, 3.3)
        ax.set_ylim(-0.005, 0.08)
        ax.set_xlabel("Time after the reversal (ns)")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right", fontsize=11.5)
    axes[0].set_ylabel("Pad voltage (V)")
    axes[0].set_title(f"the transistor: moves {1000 * (max(out[0]) - min(out[0])):.0f} ps", fontweight="bold", fontsize=16)
    axes[1].set_title(f"our model: moves {1000 * (max(out[1]) - min(out[1])):.0f} ps", fontweight="bold", fontsize=16)
    fig.suptitle("io_buf  |  five pulse widths  |  the bump, timed from the reversal", fontweight="bold", fontsize=16)
    save(fig, "iobuf_bump")
    print(f"      transistor {out[0]}, ours {out[1]}")


# ------------------------------------------- tried after looking inside (09-08 -> 09-10)
CC = R / "ex2_ccomp_correction_2026-09-08"


def _pad_panel(ax, dev, depth, builds, xlim, head, legend="upper right"):
    """The transistor pale, each build over it, on one axis. colour None: scored, not drawn."""
    t_si, si, rev = transistor_pad(dev, depth)
    win = lambda t: (t >= rev - 0.3) & (t <= rev + 2.6)   # noqa: E731
    peak = float(si[win(t_si)].max())
    ax.plot(t_si, si, color=SIL, lw=5.0, alpha=0.30, label="HSPICE transistor", zorder=2)
    for label, path, colour in builds:
        got = raw_pad(path)
        if got is None:
            continue
        t, v = got
        err = 100.0 * (float(v[win(t)].max()) - peak) / peak
        if colour is not None:
            ax.plot(t, v, color=colour, lw=2.4, label=f"{label}   {err:+.1f} %", zorder=3)
        print(f"      {dev} {depth}: {label:36s} {err:+6.1f} %")
    ax.axvline(rev, color=REV, ls="--", lw=1.6, label="reverse edge")
    ax.set_xlim(*xlim)
    ax.set_xlabel("Time (ns)")
    ax.grid(alpha=0.3)
    ax.set_title(head, fontweight="bold", fontsize=15)
    ax.legend(loc=legend, fontsize=11.5)


def ccomp_ex2() -> None:
    """The measured C_comp put into our model: 858 ps, the width the study ran."""
    pad_overlay("ccomp_ex2", "ex2", 858, "858 ps pulse",
                [("our model, C_comp 5.0 pF (declared)", CC / "c5.0" / "w858" / "ours" / "run.raw", GATE),
                 ("our model, C_comp 1.7 pF (measured)", CC / "c1.7" / "w858" / "ours" / "run.raw", TRIAL)],
                (5.3, 8.4))


def cascade_pair() -> None:
    """The RC cascade: right on ex2, dead on an inverter chain. Built at the declared C_comp,
    so our model is drawn from the same folder."""
    ex2_ship = CASC / "ex2" / "shipped" / "d810" / "run.raw"
    if not ex2_ship.is_file():
        ex2_ship = CASC / "ex2_c1.7" / "shipped" / "d810" / "run.raw"
    fig, axes = plt.subplots(1, 2, figsize=(W, H))
    _pad_panel(axes[0], "ex2", 810,
               [("our model, same folder", ex2_ship, None),
                ("RC cascade, 5 stages", CASC / "ex2" / "cascade5" / "d810" / "run.raw", TRIAL)],
               (5.3, 8.0), "ex2  |  810 ps: looks right")
    _pad_panel(axes[1], "inv_base8", 50,
               [("our model, same folder", CASC / "inv_base8" / "shipped" / "d50" / "run.raw", None),
                ("RC cascade, 4 stages", CASC / "inv_base8" / "cascade4" / "d50" / "run.raw", TRIAL),
                ("delay + one 60 ps stage", CASC / "inv_base8" / "hybrid60ps" / "d50" / "run.raw", None)],
               (5.05, 5.75), "inv_base8  |  102 ps: nothing gets through")
    axes[0].set_ylabel("Pad voltage (V)")
    save(fig, "cascade_pair")


def superpose_ex2() -> None:
    """Derive ex2's gate from the file through the MOSFET-shaped curve (left, full swing),
    then predict the 810 ps pulse as the rising step plus the falling step (right).
    Same computation as physics_map_gate_from_ibis.py, from the runs it used."""
    import physics_map_gate_from_ibis as pm
    vt, al = 0.57, 0.64            # ex2's fit, physics_map_gate_2026-09-10/results.csv
    raw = sl.parse_ngspice_raw(CASC / "ex2_c1.7" / "shipped" / "full" / "run.raw")
    tf, kb = sl.time_ns(raw), sl.signal(raw, "v(x1.kugate_base)")
    k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
    kuf = np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0)
    g_file = pm.below_threshold(tf, pm.invert(kuf, vt, al), kuf, vt)
    tau = np.arange(-0.2, 9.0, 0.002)
    s_rise, s_fall = np.interp(tau + 5.0, tf, g_file), np.interp(tau + 15.0, tf, g_file)
    tfu, gfu, ts, gs = _norm_pair("ex2", 810, "v(xdut.n4)")
    w = 0.810
    x = np.arange(-0.2, w + 3.0, 0.002)
    pred = np.interp(x, tau, s_rise, left=0.0) + np.interp(x - w, tau, s_fall, left=1.0) - 1.0
    real = np.interp(x, ts, gs)
    fig, axes = plt.subplots(1, 2, figsize=(W, H), sharey=True)
    a, b = axes
    a.plot(tfu, gfu, color="#111111", lw=2.6, label="real gate n4")
    a.plot(tau, s_rise, color=TRIAL, lw=2.6, ls="--", label="gate derived from the file")
    a.set_xlim(-0.1, 2.6)
    a.set_title("ex2  |  full swing: the step", fontweight="bold", fontsize=15)
    b.plot(x, real, color="#111111", lw=2.6, label="real gate n4")
    b.plot(x, pred, color=TRIAL, lw=2.6, ls="--", label="rising + falling step")
    b.axvline(w, color=REV, ls="--", lw=1.6, label="reverse edge")
    b.set_xlim(-0.1, 3.0)
    b.set_title("ex2  |  810 ps pulse: superposed", fontweight="bold", fontsize=15)
    pr, pp = float(real.max()), float(pred.max())
    b.axhline(pr, color="#111111", ls=":", lw=1.2)
    b.axhline(pp, color=TRIAL, ls=":", lw=1.2)
    b.text(2.95, pp, f"superposition says {pp:.2f} ", ha="right", va="bottom", fontsize=14, color=TRIAL)
    b.text(2.95, pr, f"real gate stops at {pr:.2f} ", ha="right", va="bottom", fontsize=14)
    for ax in axes:
        ax.axhspan(-0.08, vt, color="#EDEDED", zorder=0)
        ax.set_ylim(-0.08, 1.12)
        ax.set_xlabel("Time from the input edge (ns)")
        ax.grid(alpha=0.3)
    a.text(2.55, 0.02, "below threshold the file shows" + chr(10) + "nothing: dashed = straight continuation",
           ha="right", va="bottom", fontsize=12, color="#555555")
    a.legend(loc="upper left", fontsize=12)
    b.legend(loc="upper left", fontsize=11)
    a.set_ylabel("gate, 0 = rest, 1 = fully on")
    save(fig, "superpose_ex2")
    t50 = lambda t, g: float(t[np.argmax(g >= 0.5)])  # noqa: E731
    print(f"      full-swing t50: real {1000 * t50(tfu, gfu):.0f} ps, from the file {1000 * t50(tau, s_rise):.0f} ps")
    print(f"      810 ps: real gate max {pr:.3f}, superposition {pp:.3f}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("building 0917 deck figures")
    for fn in (recap, ku_vs_gate, gate_vs_real_three, replay_ex2,
               cascade_ex2, slew_ex2, reversal_rules, value_match_split,
               gate_vs_real_all, static_map_ex2, replay_inv, inv_map,
               walks, gate_steps, inv_why, replay_inv_split, replay_iobuf_marked, iobuf_bump,
               ccomp_ex2, cascade_pair, superpose_ex2):
        try:
            fn()
        except Exception as exc:  # one bad path must not cost the whole set
            print(f"  FAILED {fn.__name__}: {exc!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
