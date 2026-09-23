#!/usr/bin/env python3
"""Figures for the 2026-09-22/23 results: track 1 end to end, and what is left.

Five figures, all from tables and runs already on disk - nothing is re-simulated:

    endtoend.png        worst stressed peak per buffer: shipped / track-1 / file-only
    ccomp.png           C_comp: declared, the file's knee estimate, the loop measurement
    inv_chain_gate.png  inv_chain at 106 ps: the gate pulse and the pad, model vs transistor
    io_buf_pulldown.png io_buf's short-LOW depth against the transistor, and the Kd spread
    last_stage.png      what a faster final stage does to inv_chain

Output: results/track1_summary_2026-09-23/

    py -3.14 scripts/build_0923_figures.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import gate_ramp_prototype as gp  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import stage_count_from_file as sc  # noqa: E402

R = ROOT / "results"
OUT = R / "track1_summary_2026-09-23"
SC = sc.OUT
SHIPPED, TRACK1, FILEONLY = "#8A8A8A", "#2E86C1", "#C0392B"
BODY = {"font.size": 12, "axes.titlesize": 13, "axes.labelsize": 12, "xtick.labelsize": 10.5,
        "ytick.labelsize": 10.5, "legend.fontsize": 10.5, "axes.linewidth": 1.1}


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=180)
    plt.close(fig)
    print(f"  {name}")


def rows(path: Path):
    return list(csv.DictReader(path.open())) if path.exists() else []


def worst(sweep: Path, which="chain"):
    """(worst peak %, per-width peaks) of the shipped row or the chain row of a sweep.csv."""
    rr = rows(sweep)
    if not rr:
        return None, []
    r = rr[0] if which == "shipped" else rr[-1]
    pk = [float(v) for k, v in r.items() if k.startswith("pk_d")]
    return (max(map(abs, pk)) if pk else None), pk


def fig_endtoend():
    """Per buffer: the shipped model, the track-1 build, and the file-only build."""
    # the final recipe: (K, shape) chosen on the whole pad waveform of the one stressed run
    sel = {r["buffer"]: r for r in rows(R / "selector_from_one_run_2026-09-23" / "selector_picks.csv")}
    e2e = {r["buffer"]: r for r in rows(SC / "step6_endtoend.csv")}
    split = {r["buffer"]: r for r in rows(SC / "step4_split.csv")}
    devs, ship, tr1, fo = [], [], [], []
    for dev, b in sc.BUFFERS.items():
        tag = sc.build_dir("step2f", dev, b["k_net"][0], b["k_net"][1])
        if tag is None or dev not in sel:
            continue
        devs.append(dev)
        ship.append(worst(tag / "sweep.csv", "shipped")[0] or np.nan)
        tr1.append(float(split[dev]["step2_worst_peak_pct"]) if dev in split else np.nan)
        fo.append(float(sel[dev]["rms_pct"]))
    x = np.arange(len(devs))
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(figsize=(12.5, 4.8))
        ax.bar(x - 0.27, ship, 0.26, color=SHIPPED, label="shipped IBIS model")
        ax.bar(x, tr1, 0.26, color=TRACK1, label="track 1 (measured C_comp, family shape, netlist K)")
        ax.bar(x + 0.27, fo, 0.26, color=FILEONLY, label="file only (C_comp from the file; K and shape from one pad run)")
        ax.axhline(10, color="#555555", ls="--", lw=1.1)
        ax.text(-0.45, 11, "±10 %", fontsize=10, color="#555555")
        ax.set_xticks(x, devs, rotation=28, ha="right")
        ax.set_ylabel("worst stressed peak error (%)")
        ax.set_ylim(0, np.nanmax(ship) * 1.28)          # room for the legend above the tallest bar
        ax.set_title("A model built from the IBIS file alone, against one built from probed silicon",
                     fontweight="bold")
        ax.legend(loc="upper center", ncol=3, frameon=False)
        ax.grid(axis="y", alpha=0.3)
        save(fig, "endtoend.png")


def fig_ccomp():
    cc = rows(R / "ccomp_from_file_2026-09-22" / "ccomp_from_file.csv")
    devs = [r["buffer"] for r in cc]
    dec = [float(r["declared_pF"]) for r in cc]
    knee = [float(r["knee_pF"]) for r in cc]
    loop = [float(r["loop_pF"]) if r["loop_pF"] else np.nan for r in cc]
    x = np.arange(len(devs))
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(figsize=(12.5, 4.4))
        ax.bar(x - 0.27, dec, 0.26, color="#E67E22", label="declared in the IBIS file")
        ax.bar(x, knee, 0.26, color=FILEONLY, label="from the file's Ku overshoot (the knee)")
        ax.bar(x + 0.27, loop, 0.26, color="#27AE60", label="loop-measured (needs the probed gate)")
        ax.set_xticks(x, devs, rotation=28, ha="right")
        ax.set_ylabel("C_comp (pF)")
        ax.set_title("C_comp without probing: the file rejects its own declared value on the ex2 family",
                     fontweight="bold")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        save(fig, "ccomp.png")


def fig_inv_chain_gate(depth=106):
    """inv_chain at its worst width: the gate pulse, then the pad."""
    dev, K = "inv_chain", 7
    tag = sc.build_dir("step2f", dev, K, None)
    if tag is None:
        print("  (no inv_chain step-7 build)")
        return
    gp.VARIANT_NAME = dev
    sup, _ = gp.VARIANTS[dev]
    text = (tag / "driver_chain.sub").read_text(encoding="utf-8")
    case = next((c for c in gp.cases(dev) if c[0] == depth), None)
    if case is None:
        print(f"  (no {depth} ps case)")
        return
    _d, w, dref = case
    r = gp.run_ours(tag / f"d{depth}", text, sup, w)
    tt, pt_ = gp.tr0_pad(dref / "run.tr0")
    tw, gw = gr.real_gate(dev, depth, gr.GATES[dev][0])
    rev = gp.RISE_NS + w
    g = np.arange(rev - 0.15, rev + 0.6, 0.002)      # the pulse, not the quiet either side of it
    with plt.rc_context(BODY):
        fig, (a, b) = plt.subplots(2, 1, figsize=(8.6, 7.0), sharex=True)
        a.plot((g - rev) * 1e3, np.interp(g, tw, gw), color="#111111", lw=2.6, label="transistor gate")
        a.plot((g - rev) * 1e3, np.interp(g, r["t"], r["gup"]), color=FILEONLY, lw=2.2, ls="--",
               label="our chain's gate")
        a.set_ylabel("gate (0-1)")
        a.set_title(f"{dev} at {depth} ps: the right height, 45 ps late, 16 ps too wide", fontweight="bold")
        a.legend()
        a.grid(alpha=0.3)
        b.plot((g - rev) * 1e3, np.interp(g, tt, pt_), color="#111111", lw=2.6, label="transistor pad")
        b.plot((g - rev) * 1e3, np.interp(g, r["t"], r["pad"]), color=FILEONLY, lw=2.2, ls="--",
               label="our pad (+26 %)")
        b.set_ylabel("pad (V)")
        b.set_xlabel("time from the reversal (ps)")
        b.legend()
        b.grid(alpha=0.3)
        save(fig, "inv_chain_gate.png")


def fig_io_buf_pulldown():
    rr = rows(R / "io_buf_pulldown_depth_2026-09-22" / "pulldown_depth.csv")
    if not rr:
        print("  (no io_buf pull-down table)")
        return
    kd3 = [r for r in rr if r["Kd"] == "3"]
    w = [int(r["width_ps"]) for r in kd3]
    ours = [float(r["our_depth_pct"]) for r in kd3]
    real = [float(r["transistor_depth_pct"]) for r in kd3]
    spread = []
    for ww in w:
        v = [float(r["our_min_V"]) for r in rr if int(r["width_ps"]) == ww]
        spread.append(1e3 * (max(v) - min(v)))
    with plt.rc_context(BODY):
        fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.4), gridspec_kw={"width_ratios": [1.5, 1]})
        a.plot(w, real, "-o", color="#111111", lw=2.4, label="transistor")
        a.plot(w, ours, "--s", color=FILEONLY, lw=2.2, label="our model")
        a.set_xlabel("short-LOW pulse width (ps)")
        a.set_ylabel("depth reached (% of full swing)")
        a.set_title("io_buf's pull-down direction: 16-21 points shallow", fontweight="bold")
        a.legend()
        a.grid(alpha=0.3)
        b.bar(range(len(w)), spread, color=TRACK1)
        b.set_xticks(range(len(w)), [str(x) for x in w], rotation=30)
        b.set_xlabel("width (ps)")
        b.set_ylabel("spread across Kd = 2...5 (mV)")
        b.set_title("the pull-down chain depth\nis unidentifiable", fontweight="bold")
        b.grid(axis="y", alpha=0.3)
        save(fig, "io_buf_pulldown.png")


def fig_last_stage():
    rr = rows(R / "inv_chain_last_stage_2026-09-22" / "last_stage.csv")
    if not rr:
        print("  (no last-stage table)")
        return
    sc_ = [float(r["s_dn_scale"]) for r in rr]
    pk = [float(r["worst_peak_pct"]) for r in rr]
    fs = [float(r["full_pad_rms_mV"]) for r in rr]
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(figsize=(7.6, 4.6))
        ax.plot(sc_, pk, "-o", color=FILEONLY, lw=2.2, label="worst stressed peak (%)")
        ax.plot(sc_, fs, "--s", color=TRACK1, lw=2.0, label="full-swing pad rms (mV)")
        ax.axhline(10, color="#555555", ls=":", lw=1.1)
        ax.set_xlabel("final stage's discharge rate, relative to the others")
        ax.set_title("inv_chain: a faster final stage improves both", fontweight="bold")
        ax.legend()
        ax.grid(alpha=0.3)
        save(fig, "last_stage.png")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (fig_endtoend, fig_ccomp, fig_inv_chain_gate, fig_io_buf_pulldown, fig_last_stage):
        try:
            f()
        except Exception as exc:                      # one bad figure must not cost the set
            print(f"  FAILED {f.__name__}: {exc!r}")
    print(f"wrote into {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
