#!/usr/bin/env python3
"""Figures for Simon's 2026-09-18 deck, `0918_Simon_IBIS.pptx`, from the comments on it.

    slide 3          recap_pad.png                 io_buf 1792 ps: transistor, native, gate_state_fixed
    slide 4          ex2_stress_levels.png         ex2 at 90 / 80 / 70 / 60 / 50 % depth, main bench
    slide 5          inv_chain_stress_levels.png   inv_chain, the same
    slides 10/13/16  four_panel_{io_buf,ex2,inv_chain}.png  real gate / GUP / Ku / pad
    slides 11/14/17  real_gate_{io_buf,ex2,inv_chain}.png   the same four panels, GUP = the real gate

gate_state_fixed is the build the 09-04 deck called cmd_clean and the code calls delay_cmd
(InputDrivenTwoStateGateDelayCommandFull). Everything is at the file's declared C_comp, like
the recap and variant slides. Slides 10-17 are at 70 % stress, the width of the stage walks
on slides 9 / 12 / 15: io_buf 2090 ps, ex2 858 ps, inv_chain 111 ps. Nothing is re-simulated.

    py -3.14 scripts/build_0918_deck_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import build_cmd_clean_slides as cc  # noqa: E402  the recap figure's data and geometry
import build_0911_deck_figures as f11  # noqa: E402  the variant cases
import build_0917_deck_figures as f17  # noqa: E402  probes, replays, transistor pads
import spicelab as sl  # noqa: E402

R = ROOT / "results"
OUT = R / "meeting_deck_2026-09-18" / "figures"
NAME = "gate_state_fixed"
OURS = f17.GATE       # purple: our model, as in every deck
REAL = f17.REPLAY     # teal: the transistor's gate put into our model
SIL = f17.SIL
BODY = {"font.size": 13, "axes.titlesize": 13, "axes.labelsize": 13, "xtick.labelsize": 11.5,
        "ytick.labelsize": 11.5, "legend.fontsize": 11, "axes.linewidth": 1.2}

# 70 % stress, as on the stage-walk slides. Declared C_comp: the folders without a _c suffix.
SPECS = {
    "io_buf": ("io_buf", 2090, "v(xdut.n2)", "n2, the PMOS gate", (-0.2, 5.5)),
    "ex2": ("ex2", 858, "v(xdut.n4)", "n4", (-0.1, 3.0)),
    "inv_chain": ("inv_chain", 111, "v(xdut.vout7)", "vout7", (-0.03, 0.6)),
}


def save(fig, name: str, rect=None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=rect) if rect else fig.tight_layout()
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print(f"  {name}")


# ----------------------------------------------------------------------------- slide 3
def recap_pad() -> None:
    """The 09-04 pad figure with three curves kept. Same size and the same axis ranges as the
    picture it replaces, so the arrows and boxes drawn over it on the slide stay on target."""
    c, m = cc.read(cc.CHAIN), cc.read(cc.MATRIX)
    rc = {"font.size": 14, "axes.titlesize": 15, "axes.labelsize": 14,
          "xtick.labelsize": 12, "ytick.labelsize": 12, "legend.fontsize": 12}
    with plt.rc_context(rc):
        # the y range the original had with all five curves on it
        f0, a0 = plt.subplots(figsize=cc.FIGSIZE_ONE)
        for k in ("transistor_pad_v", "native_pad_v", "original_pad_v", "fix_pad_v"):
            a0.plot(c["time_ns"], c[k])
        a0.plot(m["time_ns"], m["pybis_pad"])
        a0.axhline(0)
        a0.set_xlim(4.6, 14.6)
        ylim = a0.get_ylim()
        plt.close(f0)

        fig, a = plt.subplots(figsize=cc.FIGSIZE_ONE)
        a.plot(c["time_ns"], c["transistor_pad_v"], color=cc.C_SIL, lw=3.4, label="HSPICE transistor")
        a.plot(c["time_ns"], c["native_pad_v"], color=cc.C_NAT, lw=2.7, label="HSPICE native IBIS")
        a.plot(m["time_ns"], m["pybis_pad"], color=cc.C_CLEAN, lw=2.4, label=NAME)
        for x in (cc.RISE_NS, cc.REV):
            a.axvline(x, color=cc.C_MARK, ls="--", lw=1.25, zorder=0)
        a.axhline(0, color="#111", lw=1.0)
        a.set_xlim(4.6, 14.6)
        a.set_ylim(*ylim)
        a.set_xlabel("Time (ns)")
        a.set_ylabel("Pad (V)")
        a.grid(alpha=0.3)
        a.legend(loc="upper right")
        fig.suptitle(f"{cc.CASE} | pad voltage", fontsize=16, fontweight="bold")
        fig.tight_layout()
        OUT.mkdir(parents=True, exist_ok=True)
        fig.savefig(OUT / "recap_pad.png", dpi=200)
        plt.close(fig)
    print("  recap_pad.png")


# ----------------------------------------------------------------------------- slides 4, 5
def stress_levels(dev: str, name: str, xlim, ticks) -> None:
    """One buffer at five depths, in the style of the 09-11 variant figure, from the main bench
    (3.3 V, 50 ohm || 2 pF, 50 ps edges) that slides 9-17 use. The variant bench has 1 ps
    edges; native HSPICE dies on ex2 there, and its 70 % case reads +27 % where this reads
    +22 %. Errors are pad-peak, in the same window as the other slides."""
    import csv
    rows = [r for r in csv.DictReader(open(f17.MATRIX / "per_case.csv"))
            if r["device"] == dev and r["direction"] == "short_high"]
    widths = {int(r["target_percent"]): round(float(r["pulse_width_ps"])) for r in rows}
    with plt.rc_context(BODY | {"axes.titlesize": 12, "font.size": 12}):
        fig, axes = plt.subplots(1, 5, figsize=(12.6, 5.0), sharey=True)
        handles = None
        for a, depth in zip(axes, (90, 80, 70, 60, 50)):
            w = widths[depth]
            d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / f"{dev}_short_high_w{w}ps.csv")
            t, rev = d["time_ns"], 5.0 + w / 1000.0
            x = t - rev
            win = (x > -0.3) & (x < 2.6)
            pk = float(d["silicon_pad"][win].max())
            e = 100.0 * (float(d["pybis_pad"][win].max()) - pk) / pk
            en = 100.0 * (float(d["hspice_pad"][win].max()) - pk) / pk
            nat_ok = float(d["hspice_pad"][win].max()) > 0.3 * pk
            mm = (x > xlim[0]) & (x < xlim[1])
            h1, = a.plot(x[mm], d["silicon_pad"][mm], color=f11.C_SI, lw=3.0, label="transistor")
            h2, = a.plot(x[mm], d["hspice_pad"][mm], color=f11.C_NAT, lw=1.7, ls="-" if nat_ok else ":",
                         label="native HSPICE IBIS")
            h3, = a.plot(x[mm], d["pybis_pad"][mm], color=f11.C_CLEAN, lw=2.0, ls="--", label=f"ours ({NAME})")
            handles = handles or [h1, h2, h3]
            a.axvline(0, color="#888", ls="--", lw=1)
            nat = f"native {en:+.0f} %" if nat_ok else "native dead"
            a.set_title(f"{depth} % depth, {w} ps\nours {e:+.0f} %\n{nat}", fontweight="bold", fontsize=11.5)
            a.set_xticks(ticks)
            a.set_xlabel("time from reversal (ns)")
            a.set_xlim(*xlim)
            a.grid(alpha=0.3)
            print(f"      {dev} {depth} %: {w} ps, ours {e:+.1f} %, {nat}")
        axes[0].set_ylabel("pad (V)")
        fig.legend(handles, [h.get_label() for h in handles], loc="lower center", ncol=3, frameon=False)
        save(fig, name, rect=(0, 0.07, 1, 1))


# ----------------------------------------------------------------------------- slides 10-17
def _turn(t, g, lo, hi):
    sel = (t >= lo) & (t <= hi)
    return float(t[sel][np.argmax(g[sel])])


def four_panel(dev: str, replay: bool) -> None:
    """Real gate / GUP / Ku / pad on one time axis. replay: our GUP replaced by the real gate
    (io_buf: both gates, n2 for GUP and n3 for GDN)."""
    folder, depth, node, gname, xlim = SPECS[dev]
    w = depth / 1000.0
    _tf, gfull, ts, greal = f17._norm_pair(dev, depth, node)
    tf = _tf
    raw = sl.parse_ngspice_raw(f17.CASC / folder / ("gate_replay" if replay else "shipped") / f"d{depth}" / "run.raw")
    tm = sl.time_ns(raw) - 5.0
    gup, ku, pad = sl.signal(raw, "v(x1.gup)"), sl.signal(raw, "v(x1.ku)"), sl.trace(raw, "out")
    t_si, si, rev = f17.transistor_pad(dev, depth)
    t_si = t_si - 5.0
    d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / f"{dev}_short_high_w{depth}ps.csv")
    xk, kk = d["time_ns"] - 5.0, d["silicon_ku"].copy()
    for edge in (0.0, w):   # the two-fixture solve is differentiation noise here
        kk[(xk > edge - 0.02) & (xk < edge + 0.09)] = np.nan
    win = lambda t: (t >= w - 0.3) & (t <= w + 2.6)   # noqa: E731
    peak = float(si[win(t_si)].max())
    err = 100.0 * (float(pad[win(tm)].max()) - peak) / peak
    col = REAL if replay else OURS
    who = ("real gates as GUP / GDN" if dev == "io_buf" else "real gate as GUP") if replay else NAME
    base_err = None
    if replay:
        rb = sl.parse_ngspice_raw(f17.CASC / folder / "shipped" / f"d{depth}" / "run.raw")
        tb, pb = sl.time_ns(rb) - 5.0, sl.trace(rb, "out")
        base_err = 100.0 * (float(pb[win(tb)].max()) - peak) / peak

    with plt.rc_context(BODY):
        fig, ax = plt.subplots(4, 1, figsize=(12.2, 6.7), sharex=True)
        ax[0].plot(tf, gfull, color=SIL, lw=4.0, alpha=0.30, label="full swing")
        ax[0].plot(ts, greal, color="#111111", lw=2.4, label=f"{depth} ps pulse")
        ax[1].plot(tm, gup, color=col, lw=2.4)
        ax[2].plot(xk, kk, color=SIL, lw=4.0, alpha=0.30, label="transistor")
        ax[2].plot(tm, ku, color=col, lw=2.2, label=who)
        ax[3].plot(t_si, si, color=SIL, lw=5.0, alpha=0.30, label="HSPICE transistor")
        if replay:   # the unmodified model, for comparison with the real-gate run
            ax[3].plot(tb, pb, color=OURS, lw=2.0, label=f"{NAME}   {base_err:+.1f} %")
        lab = f"{who}   {err:+.1f} %"
        ax[3].plot(tm, pad, color=col, lw=2.4, label=lab)
        heads = [f"1  transistor: real gate {gname}",
                 "2  our model: GUP = the real gate, replayed" if replay else "2  our model: GUP",
                 "3  Ku", "4  pad"]
        ylab = ["gate, 0 to 1", "GUP", "Ku", "pad (V)"]
        for a, h, yl in zip(ax, heads, ylab):
            a.axvline(w, color=f17.REV, ls="--", lw=1.4)
            a.grid(alpha=0.3)
            a.set_ylabel(yl)
            a.text(0.005, 0.93, h, transform=a.transAxes, va="top", fontsize=12.5, fontweight="bold",
                   bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
        for a in ax[:2]:
            a.set_ylim(-0.15, 1.2)
        kv = np.concatenate([kk[np.isfinite(kk)], ku[(tm >= xlim[0]) & (tm <= xlim[1])]])
        ax[2].set_ylim(min(-0.15, float(kv.min()) - 0.05), max(1.2, float(kv.max()) + 0.08))
        ax[2].set_yticks([0.0, 0.5, 1.0])
        t_real = _turn(ts, greal, 0.0, w + 3.0)
        t_gup = _turn(tm, gup, 0.0, w + 3.0)
        for a in ax:
            a.axvline(t_real, color="#111111", ls=":", lw=1.3)
            if not replay:
                a.axvline(t_gup, color=col, ls=":", lw=1.3)
        if not replay:
            ax[1].annotate(f"turns round {1000 * (t_gup - t_real):.0f} ps after the real gate",
                           xy=(t_gup, float(gup.max())), xytext=(0.985, 0.62), textcoords="axes fraction",
                           ha="right", color=col, fontsize=12, arrowprops={"arrowstyle": "->", "color": col, "lw": 1.2})
        ax[0].legend(loc="center right", fontsize=10.5, ncol=2)
        ax[2].legend(loc="upper right", fontsize=10.5, ncol=2)
        ax[3].legend(loc="upper right", fontsize=11)
        ax[3].set_xlim(*xlim)
        ax[3].set_xlabel("Time from the input edge (ns)")
        tail = f":  {err:+.1f} %   ({NAME}: {base_err:+.1f} %)" if replay else ""
        fig.suptitle(f"{dev}  |  {depth} ps pulse, 70 % stress  |  {who}{tail}", fontweight="bold", fontsize=15)
        save(fig, f"{'real_gate' if replay else 'four_panel'}_{dev}.png")
    print(f"      {dev}: pad {err:+.1f} %" + (f" (was {base_err:+.1f} %)" if replay else "")
          + f", real gate turns at {t_real:.3f} ns" + ("" if replay else f", GUP at {t_gup:.3f} ns"))


# ------------------------------------------------------ after slide 17: inv_chain explained
MEAS = f17.MEAS       # green: Ku curves measured on the transistor, and the build using them
TRIAL = f17.TRIAL     # amber: a prototype / track 1
NPZ = R / "method_animations_2026-09-17" / "method_data.npz"


def _peak_err(t, v, t_si, si, rev):
    win = lambda x: (x >= rev - 0.3) & (x <= rev + 2.6)   # noqa: E731
    pk = float(si[win(t_si)].max())
    return 100.0 * (float(v[win(t)].max()) - pk) / pk


def inv_why_111() -> None:
    """Why the real gate makes inv_chain worse, at slide 17's width (111 ps). Both runs carry the
    same real gate; one turns it into Ku with curves from the file, the other with curves measured
    on the transistor. At C_comp 0.6 pF, the loop-measured value: the transistor's Ku solve needs
    the right C_comp, and the declared-value replay collapses ngspice's timestep (09-18)."""
    base = f17.CASC / "inv_chain_c0.6"

    def cross(t, y, lvl, lo, hi, down):
        m = (t >= lo) & (t <= hi)
        idx = np.where(y[m] <= lvl)[0] if down else np.where(y[m] >= lvl)[0]
        return float(t[m][idx[0]])

    # full swing: input rises at 0 and falls at 10 ns (from the input's rising edge)
    panels = (("full", "full swing, rising edge", "uses ku_rise", (0.22, 0.52), False),
              ("full", "full swing, falling edge", "uses ku_fall", (10.22, 10.52), True),
              ("d111", "111 ps pulse", "ku_rise, then ku_fall", (0.22, 0.52), None))
    with plt.rc_context(BODY):
        fig, axes = plt.subplots(1, 3, figsize=(12.2, 5.0), sharey=True)
        for ax, (sub, name, uses, xl, down) in zip(axes, panels):
            f = sl.parse_ngspice_raw(base / "gate_replay" / sub / "run.raw")
            m = sl.parse_ngspice_raw(base / "gate_replay_silicon_full" / sub / "run.raw")
            tf, tm = sl.time_ns(f) - 5.0, sl.time_ns(m) - 5.0
            kf, km = sl.signal(f, "v(x1.ku)"), sl.signal(m, "v(x1.ku)")
            ax.plot(tf, sl.signal(f, "v(x1.gup)"), color="#111111", lw=2.6, label="the real gate (same in both runs)")
            ax.plot(tm, km, color=MEAS, lw=2.6, label="Ku, curves measured on the transistor")
            ax.plot(tf, kf, color=REAL, lw=2.6, label="Ku, curves built from the IBIS file")
            ax.set_xlim(*xl)
            ax.set_ylim(-0.12, 1.45)
            ax.set_xlabel("Time from the input edge (ns)")
            ax.grid(alpha=0.3)
            ax.set_title(f"{name}\n{uses}", fontweight="bold", fontsize=13)
            if down is not None:
                lo = xl[0]
                dt = 1000 * (cross(tf, kf, 0.5, lo, xl[1], down) - cross(tm, km, 0.5, lo, xl[1], down))
                word = "late" if dt > 0 else "early"
                ax.text(xl[1] - 0.005, 0.5 if not down else 0.62, f"file's Ku {abs(dt):.0f} ps {word}",
                        ha="right", fontsize=12.5, color=REAL)
                print(f"      {name}: file's Ku {dt:+.1f} ps against the transistor's at Ku = 0.5")
            else:
                on, used = sl.signal(f, "v(x1.kugate_on)"), sl.signal(f, "v(x1.kugate_base)")
                i = int(np.argmax((tf > 0.3) & (np.abs(on - used) > 0.05)))
                tj = float(tf[i])
                g_at = float(np.interp(tj, tf, sl.signal(f, "v(x1.gup)")))
                vals = {tag: tuple(float(np.interp(tj, t, sl.signal(r, f"v(x1.{k})"))) for k in ("kugate_on", "kugate_off"))
                        for tag, r, t in (("file", f, tf), ("transistor", m, tm))}
                ax.axvline(tj, color=f17.REV, ls="--", lw=1.5)
                ax.text(tj + 0.006, 1.42, f"switch at gate {g_at:.2f}", fontsize=12, va="top")
                ax.text(0.515, 0.92, f"transistor" + chr(10) + f"{vals['transistor'][0]:.2f} -> {vals['transistor'][1]:.2f}",
                        ha="right", va="top", fontsize=12.5, color=MEAS, fontweight="bold")
                ax.text(0.515, 0.58, f"file" + chr(10) + f"{vals['file'][0]:.2f} -> {vals['file'][1]:.2f}",
                        ha="right", va="top", fontsize=12.5, color=REAL, fontweight="bold")
                print(f"      switch at {tj:.3f} ns, gate {g_at:.2f}; file {vals['file']}, transistor {vals['transistor']}; "
                      f"Ku peaks {km.max():.2f} / {kf.max():.2f}")
        axes[0].set_ylabel("gate, and Ku")
        h, lab = axes[0].get_legend_handles_labels()
        fig.legend(h, lab, loc="lower center", ncol=3, frameon=False, fontsize=11.5)
        save(fig, "inv_why_111.png", rect=(0, 0.07, 1, 1))


def inv_fixed_111() -> None:
    """The same real gate, Ku curves from the file against Ku curves from the transistor. C_comp
    0.6 pF, as inv_why_111."""
    base = f17.CASC / "inv_chain_c0.6"
    t_si, si, rev = f17.transistor_pad("inv_chain", 111)
    with plt.rc_context(BODY):
        fig, ax = plt.subplots(figsize=(12.2, 5.0))
        ax.plot(t_si, si, color=SIL, lw=5.0, alpha=0.30, label="HSPICE transistor", zorder=2)
        for label, sub, col in (("real gate, Ku curves from the IBIS file", "gate_replay", REAL),
                                ("real gate, Ku curves measured on the transistor", "gate_replay_silicon_full", MEAS)):
            t, v = f17.raw_pad(base / sub / "d111" / "run.raw")
            e = _peak_err(t, v, t_si, si, rev)
            ax.plot(t, v, color=col, lw=2.4, label=f"{label}   {e:+.1f} %", zorder=3)
            print(f"      inv_chain 111 ps: {label:48s} {e:+.1f} %")
        ax.axvline(rev, color=f17.REV, ls="--", lw=1.5, label="reverse edge")
        ax.set_xlim(5.05, 5.65)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Pad voltage (V)")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper left", fontsize=12)
        ax.set_title("inv_chain  |  111 ps pulse, 70 % stress  |  C_comp 0.6 pF  |  pad voltage", fontweight="bold", fontsize=14)
        save(fig, "inv_fixed_111.png")


def three_handoffs() -> None:
    """All three buffers on one time scale. Top: the full-swing falling edge, where ku_fall is
    built - how fast each gate moves, and how far the file's Ku is off the transistor's. Bottom:
    the 70 % short pulse around the ku_rise -> ku_fall switch. Each at its measured C_comp
    (ex2 1.7, inv_chain 0.6); io_buf at the declared value, and it has no transistor-curve run."""
    cols = (("ex2", "ex2_c1.7", 858, "C_comp 1.7 pF"), ("inv_chain", "inv_chain_c0.6", 111, "C_comp 0.6 pF"),
            ("io_buf", "io_buf", 2090, "declared C_comp"))
    span = 0.40                        # the same 400 ps window in every panel

    def cross(t, y, lvl, lo, hi, down):
        m = (t >= lo) & (t <= hi)
        idx = np.where(y[m] <= lvl)[0] if down else np.where(y[m] >= lvl)[0]
        return float(t[m][idx[0]]) if len(idx) else float("nan")

    def load(fo, sub, run):
        p = f17.CASC / fo / sub / run / "run.raw"
        if not p.is_file():
            return None
        r = sl.parse_ngspice_raw(p)
        return dict(t=sl.time_ns(r), g=sl.signal(r, "v(x1.gup)"), ku=sl.signal(r, "v(x1.ku)"),
                    on=sl.signal(r, "v(x1.kugate_on)"), base=sl.signal(r, "v(x1.kugate_base)"),
                    off=sl.signal(r, "v(x1.kugate_off)"))

    with plt.rc_context(BODY | {"axes.titlesize": 12.5}):
        fig, axes = plt.subplots(2, 3, figsize=(12.2, 6.1), sharey=True)
        for c, (dev, fo, w, cc_) in enumerate(cols):
            # --- top: full-swing falling edge (input falls at 15 ns)
            f_, m_ = load(fo, "gate_replay", "full"), load(fo, "gate_replay_silicon_full", "full")
            t50 = cross(f_["t"], f_["g"], 0.5, 15.0, 18.0, True)
            t90, t10 = cross(f_["t"], f_["g"], 0.9, 15.0, 18.0, True), cross(f_["t"], f_["g"], 0.1, 15.0, 18.0, True)
            a = axes[0][c]
            x0 = t50 - span / 2
            a.plot((f_["t"] - x0) * 1e3, f_["g"], color="#111111", lw=2.6, label="the real gate")
            if m_ is not None:
                a.plot((m_["t"] - x0) * 1e3, m_["ku"], color=MEAS, lw=2.4, label="Ku, transistor's curves")
            a.plot((f_["t"] - x0) * 1e3, f_["ku"], color=REAL, lw=2.4, label="Ku, file's curves")
            note = f"gate falls 90->10 %\nin {1000 * (t10 - t90):.0f} ps"
            if m_ is not None:
                off = 1000 * (cross(f_["t"], f_["ku"], 0.5, 15.0, 18.0, True) - cross(m_["t"], m_["ku"], 0.5, 15.0, 18.0, True))
                note += f"\nfile's Ku {abs(off):.0f} ps {'early' if off < 0 else 'late'}"
            else:
                note += "\n(no transistor-curve run)"
            ny = 0.95                                     # top right: clear of every curve, short lines
            a.text(0.97, ny, note, transform=a.transAxes, ha="right", va="top", fontsize=11.5,
                   bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
            a.set_title(f"{dev}  |  full swing, falling edge", fontweight="bold")
            a.set_xlabel("Time (ps)")
            # --- bottom: the short pulse around the switch
            f_, m_ = load(fo, "gate_replay", f"d{w}"), load(fo, "gate_replay_silicon_full", f"d{w}")
            i = int(np.argmax((f_["t"] > 5.05) & (np.abs(f_["base"] - f_["on"]) > 0.02)))
            tsw = float(f_["t"][i])
            b = axes[1][c]
            x0 = tsw - 0.15
            b.plot((f_["t"] - x0) * 1e3, f_["g"], color="#111111", lw=2.6)
            if m_ is not None:
                b.plot((m_["t"] - x0) * 1e3, m_["ku"], color=MEAS, lw=2.4)
            b.plot((f_["t"] - x0) * 1e3, f_["ku"], color=REAL, lw=2.4)
            b.axvline(150, color=f17.REV, ls="--", lw=1.4)
            b.text(0.97, ny,
                   f"gate {f_['g'][i]:.2f}:\nKu {f_['on'][i]:.2f} -> {f_['off'][i]:.2f}",
                   transform=b.transAxes, ha="right", va="top", fontsize=11.5, color=REAL, fontweight="bold",
                   bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
            b.set_title(f"{dev}  |  {w} ps pulse: the handoff", fontweight="bold")
            b.set_xlabel("Time (ps)")
            print(f"      {dev}: {note.replace(chr(10), '; ')}; switch g {f_['g'][i]:.2f}, file Ku {f_['on'][i]:.2f} -> {f_['off'][i]:.2f}")
            for ax in (a, b):
                ax.set_xlim(0, span * 1e3)
                ax.set_ylim(-0.12, 1.25)
                ax.grid(alpha=0.3)
        axes[0][0].set_ylabel("gate, and Ku")
        axes[1][0].set_ylabel("gate, and Ku")
        h, lab = axes[0][0].get_legend_handles_labels()
        fig.legend(h, lab, loc="lower center", ncol=3, frameon=False, fontsize=11.5)
        save(fig, "three_handoffs.png", rect=(0, 0.05, 1, 1))


def vinh_inv() -> None:
    """Backup: why our model beats native on inv_chain. The IBIS file's Vinh 2.0 V on a 1.8 V
    part puts our input comparator at 1.4 V; with 50 ps edges that trims the pulse the model
    sees. Both builds at C_comp 0.6 pF, the only folder with the clamped-threshold build."""
    w, edge, v = 0.1108, 0.05, 1.8
    with plt.rc_context(BODY):
        fig, (a, b) = plt.subplots(1, 2, figsize=(12.2, 4.9), gridspec_kw={"width_ratios": [1, 1.6]})
        tt = np.array([-0.05, 0.0, edge, w, w + edge, 0.25])
        vv = np.array([0, 0, v, v, 0, 0])
        a.plot(tt * 1e3, vv, color="#111111", lw=2.6, label="input, 111 ps pulse")
        for th, col, lab in ((1.4, OURS, "switches at 1.4 V (Vinh 2.0 V in the file)"), (0.9, TRIAL, "switches at 0.9 V (mid-supply)")):
            t_on, t_off = edge * th / v, w + edge * (v - th) / v
            a.axhline(th, color=col, ls="--", lw=1.4)
            a.plot([t_on * 1e3, t_off * 1e3], [th, th], color=col, lw=5, alpha=0.55, solid_capstyle="butt",
                   label=f"{lab}: sees {1e3 * (t_off - t_on):.0f} ps")
        a.set_xlim(-30, 200)
        a.set_ylim(-0.1, 2.75)
        a.set_yticks([0, 0.5, 1.0, 1.5])
        a.set_xlabel("Time from the input edge (ps)")
        a.set_ylabel("input (V)")
        a.grid(alpha=0.3)
        a.legend(loc="upper right", fontsize=10)
        a.set_title("the pulse the model sees", fontweight="bold", fontsize=14)
        t_si, si, rev = f17.transistor_pad("inv_chain", 111)
        d = f17.read(f17.MATRIX / "delay_cmd" / "waveforms" / "inv_chain_short_high_w111ps.csv")
        b.plot(t_si, si, color=SIL, lw=5.0, alpha=0.30, label="HSPICE transistor")
        en = _peak_err(d["time_ns"], d["hspice_pad"], t_si, si, rev)
        b.plot(d["time_ns"], d["hspice_pad"], color=f17.NAT, lw=2.0, label=f"HSPICE native IBIS   {en:+.1f} %")
        for sub, col, lab in (("shipped", OURS, "ours, 1.4 V"), ("shipped_thr0.9", TRIAL, "ours, 0.9 V")):
            t, vp = f17.raw_pad(f17.CASC / "inv_chain_c0.6" / sub / "d111" / "run.raw")
            e = _peak_err(t, vp, t_si, si, rev)
            b.plot(t, vp, color=col, lw=2.4, label=f"{lab}   {e:+.1f} %")
            print(f"      vinh: {lab} {e:+.1f} %, native {en:+.1f} %")
        b.axvline(rev, color=f17.REV, ls="--", lw=1.4)
        b.set_xlim(5.05, 5.65)
        b.set_xlabel("Time (ns)")
        b.set_ylabel("Pad voltage (V)")
        b.grid(alpha=0.3)
        b.legend(loc="upper right", fontsize=11)
        b.set_title("inv_chain  |  111 ps  |  pad voltage", fontweight="bold", fontsize=14)
        save(fig, "vinh_inv.png")


def slew_0918() -> None:
    """The 09-17 slowed-gate figure with this deck's name for our model. Same runs, same
    folder (declared C_comp); only the label and the output folder differ."""
    old = f17.OUT
    f17.OUT = OUT
    try:
        f17.pad_overlay("slew_ex2", "ex2", 810, "810 ps pulse",
                        [(NAME, f17.CASC / "ex2" / "shipped" / "d810" / "run.raw", OURS),
                         ("gate slowed to 500 ps", f17.CASC / "ex2" / "slew500ps" / "d810" / "run.raw", TRIAL)],
                        (5.3, 8.4))
    finally:
        f17.OUT = old


# --------------------------------------------------------- how to reproduce: the method (ex2)
def track1_file_fit():
    """The file-only track-1 fit, reproduced from the build it produced
    (gate_chain_prototype_2026-09-10/ex2_c1.7/ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810).
    No internal node: three identical stages drive the MOSFET-shaped curve (vt 0.57, alpha 0.64),
    and the stage numbers are fitted so the model's Ku matches the file's own full-swing Ku(t),
    both edges (gate_chain_prototype.fit_chain_ku). The fitted numbers are read from the build's
    first calibration iterate (calib/it00): s_up 2.19028, s_dn 2.12377, vt 0.527643, x_lin fixed
    0.45. Returns (t from the input edge, file's Ku, model's Ku, stage output g, rms)."""
    import current_limited_stage_model as cl
    import physics_map_gate_from_ibis as pm
    import re
    it00 = (R / "gate_chain_prototype_2026-09-10" / "ex2_c1.7" / "ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810"
            / "calib" / "it00" / "driver.sub").read_text(encoding="utf-8")
    line = next(ln for ln in it00.splitlines() if ln.startswith("BSTG1 "))
    s_up, vt = (float(x) for x in re.search(r"\(([\d.]+) \* pow\(max\(min\(\(V\(CHIN\) - ([\d.]+)\)", line).groups())
    s_dn = float(re.search(r"- ([\d.]+) \* pow\(max\(min\(\(1 - V\(CHIN\)", line).group(1))
    x_lin = float(re.search(r"\(1 - V\(STG1\)\) / ([\d.]+)\)", line).group(1))
    raw = sl.parse_ngspice_raw(f17.CASC / "ex2_c1.7" / "shipped" / "full" / "run.raw")
    tf, kb = sl.time_ns(raw), sl.signal(raw, "v(x1.kugate_base)")
    k_rest, k_on = float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb))
    grid = np.arange(4.0, 21.0, cl.DT)
    target = np.interp(grid, tf, np.clip((kb - k_rest) / (k_on - k_rest), 0.0, 1.0))
    t_on = 5.0 + 0.050 / 2
    u = ((grid >= t_on) & (grid < t_on + 10.0)).astype(float)
    g = cl.simulate_chain(u, [(s_up, s_dn, vt, x_lin, 1.0)] * 3)
    ku = pm.prior(g, 0.57, 0.64)
    rms = float(np.sqrt(np.mean((ku - target) ** 2)))
    print(f"      file-only fit: s_up {s_up:.3f} s_dn {s_dn:.3f} vt {vt:.3f} x_lin {x_lin:.2f}; Ku-domain rms {rms:.4f}")
    return grid - 5.0, target, ku, g, rms


def method_track1() -> None:
    """Track 1, file only: the stages fitted so the model's Ku matches the file's full-swing Ku(t)
    (left, no internal node); the stage threshold placed by one stressed pad run, bisected at
    810 ps (right, the same build's calibration iterates)."""
    D = np.load(NPZ)
    t, target, ku, g, rms = track1_file_fit()
    with plt.rc_context(BODY):
        fig, (a, b) = plt.subplots(1, 2, figsize=(12.2, 4.9))
        m = (t >= -0.4) & (t <= 13.0)
        a.plot(t[m], target[m], color=SIL, lw=5.0, alpha=0.40, label="the file's Ku(t), 10 ns pulse")
        a.plot(t[m], ku[m], color=TRIAL, lw=2.4, label=f"model's Ku: 3 stages -> MOSFET curve   rms {rms:.3f}")
        a.plot(t[m], g[m], color=TRIAL, lw=1.2, ls=":", label="the stages' output (the model's gate)")
        a.set_xlim(-0.4, 13.0)
        a.set_ylim(-0.08, 1.12)
        a.set_xlabel("Time from the input edge (ns)")
        a.set_ylabel("Ku, and gate (0 to 1)")
        a.grid(alpha=0.3)
        a.legend(loc="center right", fontsize=10.5)
        a.set_title("1. fit the stages to the file's Ku, full swing", fontweight="bold", fontsize=13.5)
        t, tgt = D["bis_t"], D["bis_target"]
        b.plot(t, tgt, color=SIL, lw=5.0, alpha=0.35, label=f"transistor pad, 810 ps   peak {tgt.max():.3f} V")
        for k, (vt, c) in enumerate(zip(D["bis_vt"], D["bis_curves"])):
            last = k == len(D["bis_vt"]) - 1
            b.plot(t, c, color=TRIAL, lw=2.4 if last else 1.0, alpha=1.0 if last else 0.35,
                   label=f"stage threshold vt = {vt:.3f}   peak {c.max():.3f} V" if last else ("other vt tried" if k == 0 else None))
        b.set_xlim(-0.2, 2.2)
        b.set_xlabel("Time from the reversal (ns)")
        b.set_ylabel("Pad voltage (V)")
        b.grid(alpha=0.3)
        b.legend(loc="upper right", fontsize=10.5)
        b.set_title("2. place the threshold with one short pulse", fontweight="bold", fontsize=13.5)
        fig.suptitle("ex2  |  track 1, from the IBIS file only: rebuild how the gate moves", fontweight="bold", fontsize=15)
        save(fig, "method_track1.png")
    print(f"      bisection vt {np.round(D['bis_vt'], 3)}")


def method_result() -> None:
    """Both tracks, on the pulse the threshold was placed at (810 ps) and one it never saw.
    Track 1 = ibis_prior_K3_..._calibpad810 (file-fitted stages, MOSFET-shaped curve); tracks
    1 + 2 = ibis_silicon_K3_xlin0.45_calibpad810 (the same file-fitted stages, the measured Ku
    curve) - the 09-13 study's track 2. The animation's green was real_silicon_K3_calibpad810,
    whose stages were fitted to the probed gate; that is not track 1 + track 2 and is not used."""
    D = np.load(NPZ)
    t12 = R / "gate_chain_prototype_2026-09-10" / "ex2_c1.7" / "ibis_silicon_K3_xlin0.45_calibpad810"
    with plt.rc_context(BODY):
        fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.3), sharey=True)
        builds = (("ship", OURS, "our model (gate_state_fixed)", "-", "ours"),
                  ("t1", TRIAL, "track 1: stages from the file + MOSFET-shaped Ku curve", "--", "track 1"),
                  ("t12", MEAS, "tracks 1 + 2: the same stages + the measured Ku curve", "-", "tracks 1 + 2"))
        handles = []
        for ax, w, note in ((axes[0], 810, "threshold placed here"), (axes[1], 895, "never seen")):
            t, si = D[f"rw_t_{w}"], D[f"rw_si_{w}"]
            pk = float(si.max())
            h, = ax.plot(t, si, color=SIL, lw=5.0, alpha=0.35, label="HSPICE transistor")
            hs = [h]
            for k, (key, col, lab, ls, short) in enumerate(builds):
                if key == "t12":
                    tr, vr = f17.raw_pad(t12 / f"d{w}" / "run.raw")
                    v = np.interp(t, tr - 5.0 - w / 1000.0, vr)
                else:
                    v = D[f"rw_{key}_{w}"]
                h, = ax.plot(t, v, color=col, lw=2.4, ls=ls, label=lab)
                hs.append(h)
                ax.text(0.97, 0.93 - 0.085 * k, f"{short}  {100 * (v.max() - pk) / pk:+.1f} %", transform=ax.transAxes,
                        ha="right", va="top", fontsize=13, color=col, fontweight="bold")
            handles = handles or hs
            ax.axvline(0, color=f17.REV, ls="--", lw=1.4)
            ax.set_xlim(-0.3, 2.6)
            ax.set_xlabel("Time from the reversal (ns)")
            ax.grid(alpha=0.3)
            ax.set_title(f"ex2  |  {w} ps pulse  |  {note}", fontweight="bold", fontsize=14)
        axes[0].set_ylabel("Pad voltage (V)")
        fig.legend(handles, [h.get_label() for h in handles], loc="lower center", ncol=2, frameon=False, fontsize=11.5)
        save(fig, "method_result.png", rect=(0, 0.12, 1, 1))


# ----------------------------------------------------------------------------- slides 6-8
# Gate-level schematics from the netlists the probes ran (predriver_stages_2026-09-09):
# ex2 buffer.sp, inv_chain invchain_ref_ngspice.sub, io_buf io_buf.sp. Every node the probe
# recorded is dotted and named as on the waveform slides; the node that drives the output
# transistors is orange. W in um.
HI = "#C05621"
INK = "#1F1F1F"
SIZE = "#6B6B6B"
LW = 1.8


def _line(ax, *pts, c=INK, lw=LW):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=c, lw=lw, solid_capstyle="round", zorder=2)


def _inv(ax, x, y, s=0.62, label=None):
    """Inverter: input pin (x, y); returns the output pin."""
    from matplotlib.patches import Circle, Polygon
    tip = x + 0.87 * s
    ax.add_patch(Polygon([(x, y - s / 2), (x, y + s / 2), (tip, y)], closed=True,
                         fc="white", ec=INK, lw=LW, zorder=3))
    ax.add_patch(Circle((tip + 0.06, y), 0.06, fc="white", ec=INK, lw=LW, zorder=3))
    if label:
        ax.text(x + 0.4 * s, y - s / 2 - 0.12, label, ha="center", va="top", fontsize=10.5, color=SIZE)
    return tip + 0.12, y


def _nand(ax, x, y, s=0.72, label=None):
    """Two-input NAND: inputs (x, y +- s/4); returns the output pin."""
    from matplotlib.patches import Circle, PathPatch
    from matplotlib.path import Path as MPath
    h = s / 2
    body = MPath([(x, y - h), (x + 0.45 * s, y - h), (x + 0.95 * s, y - h), (x + 0.95 * s, y),
                  (x + 0.95 * s, y + h), (x + 0.45 * s, y + h), (x, y + h), (x, y - h)],
                 [1, 2, 3, 3, 3, 3, 2, 79])
    ax.add_patch(PathPatch(body, fc="white", ec=INK, lw=LW, zorder=3))
    ax.add_patch(Circle((x + 0.95 * s + 0.06, y), 0.06, fc="white", ec=INK, lw=LW, zorder=3))
    if label:
        ax.text(x + 0.45 * s, y - h - 0.12, label, ha="center", va="top", fontsize=10.5, color=SIZE)
    return x + 0.95 * s + 0.12, y


def _node(ax, x, y, name, gate=False, dy=0.16, ha="center"):
    c = HI if gate else INK
    ax.plot([x], [y], "o", color=c, ms=7.5 if gate else 6, zorder=5)
    ax.text(x, y + dy, name, ha=ha, va="bottom", fontsize=13.5 if gate else 13, color=c,
            fontweight="bold")


def _mos(ax, x, y, pmos):
    """MOSFET, gate on the left at (x - 0.26, y); returns (top terminal, bottom terminal)."""
    from matplotlib.patches import Circle
    _line(ax, (x, y - 0.3), (x, y + 0.3), lw=2.4)                    # channel
    _line(ax, (x - 0.12, y - 0.24), (x - 0.12, y + 0.24))            # gate plate
    if pmos:
        ax.add_patch(Circle((x - 0.19, y), 0.06, fc="white", ec=INK, lw=LW, zorder=3))
    _line(ax, (x, y + 0.24), (x + 0.3, y + 0.24), (x + 0.3, y + 0.45))
    _line(ax, (x, y - 0.24), (x + 0.3, y - 0.24), (x + 0.3, y - 0.45))
    return (x + 0.3, y + 0.45), (x + 0.3, y - 0.45)


def _gnd(ax, x, y):
    _line(ax, (x, y), (x, y - 0.12))
    for k, w in enumerate((0.18, 0.12, 0.06)):
        _line(ax, (x - w, y - 0.12 - 0.07 * k), (x + w, y - 0.12 - 0.07 * k))


def _vdd(ax, x, y, v):
    _line(ax, (x - 0.18, y), (x + 0.18, y))
    ax.text(x, y + 0.08, f"VDD {v}", ha="center", va="bottom", fontsize=11.5)


def _output_stage(ax, x, y_p, y_n, v, sizes, shared_gate=None):
    """PMOS over NMOS at x; pad node between them, load to the right. Returns the gate pins."""
    (pt, pb), (nt, nb) = _mos(ax, x, y_p, pmos=True), _mos(ax, x, y_n, pmos=False)
    _line(ax, pt, (pt[0], pt[1] + 0.25))
    _vdd(ax, pt[0], pt[1] + 0.25, v)
    _line(ax, nb, (nb[0], nb[1] - 0.15))
    _gnd(ax, nb[0], nb[1] - 0.15)
    y_pad = (y_p + y_n) / 2
    _line(ax, pb, nt)
    xl = x + 1.25
    _line(ax, (pb[0], y_pad), (xl + 0.55, y_pad))
    _node(ax, pb[0] + 0.45, y_pad, "pad")
    # load: 50 ohm and 2 pF to ground
    zz = [(xl, y_pad)] + [(xl + (0.1 if k % 2 else -0.1), y_pad - 0.15 - 0.09 * k) for k in range(6)] + [(xl, y_pad - 0.8)]
    _line(ax, *zz)
    _gnd(ax, xl, y_pad - 0.8)
    xc = xl + 0.55
    _line(ax, (xc, y_pad), (xc, y_pad - 0.36))
    _line(ax, (xc - 0.17, y_pad - 0.36), (xc + 0.17, y_pad - 0.36), lw=2.4)
    _line(ax, (xc - 0.17, y_pad - 0.46), (xc + 0.17, y_pad - 0.46), lw=2.4)
    _line(ax, (xc, y_pad - 0.46), (xc, y_pad - 0.8))
    _gnd(ax, xc, y_pad - 0.8)
    ax.text(xl + 0.28, y_pad - 1.2, "50 Ω ∥ 2 pF", ha="center", va="top", fontsize=11.5)
    ax.text(x + 0.05, y_n - 1.0, sizes, ha="center", va="top", fontsize=10.5, color=SIZE)
    return (x - 0.25, y_p), (x - 0.12, y_n)


def _canvas(w=14.0, h=5.6):
    fig, ax = plt.subplots(figsize=(12.2, 12.2 * h / w))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def schematic_ex2() -> None:
    fig, ax = _canvas()
    y = 2.9
    ax.text(0.2, y + 0.16, "in", ha="left", va="bottom", fontsize=13, fontweight="bold")
    ax.plot([0.45], [y], "o", color=INK, ms=6, zorder=5)
    x = 0.45
    for k, (name, lab) in enumerate((("n2", "3.6 / 1.8"), ("n3", "14.1 / 7.2"), ("n4", "2×32.1 / 2×16.2"))):
        _line(ax, (x, y), (x + 0.5, y))
        ox, _ = _inv(ax, x + 0.5, y, label=lab)
        x = ox + 0.9
        _line(ax, (ox, y), (x, y), c=HI if name == "n4" else INK, lw=2.6 if name == "n4" else LW)
        _node(ax, ox + 0.45, y, name, gate=(name == "n4"))
    xo = x + 1.3
    g_p, g_n = _output_stage(ax, xo, y + 0.75, y - 0.75, "3.3 V", "output stage\n5×42.2 / 5×21.2, L 0.9")
    _line(ax, (x, y), (x + 0.5, y), (x + 0.5, g_p[1]), g_p, c=HI, lw=2.6)
    _line(ax, (x + 0.5, y), (x + 0.5, g_n[1]), g_n, c=HI, lw=2.6)
    ax.text(0.2, 0.25, "W in µm, PMOS / NMOS; L = 0.6 µm unless noted.   ● probed node     "
            "orange: the one node that drives both output transistors", fontsize=11, color=SIZE)
    ax.set_title("ex2  |  layout-extracted output buffer: three inverters and the output stage  |  3.3 V",
                 fontweight="bold", fontsize=14.5)
    save(fig, "schematic_ex2.png")


def schematic_inv_chain() -> None:
    fig, ax = _canvas()
    y = 2.9
    ax.text(0.1, y + 0.16, "in", ha="left", va="bottom", fontsize=13, fontweight="bold")
    ax.plot([0.3], [y], "o", color=INK, ms=6, zorder=5)
    x = 0.3
    for k in range(1, 8):
        _line(ax, (x, y), (x + 0.2, y))
        ox, _ = _inv(ax, x + 0.2, y, s=0.5, label=f"×{2 ** (k - 1)}")
        x = ox + 0.62
        gate = k == 7
        _line(ax, (ox, y), (x, y), c=HI if gate else INK, lw=2.6 if gate else LW)
        _node(ax, ox + 0.31, y, f"vout{k}", gate=gate)
    xo = x + 1.1
    g_p, g_n = _output_stage(ax, xo, y + 0.75, y - 0.75, "1.8 V", "output stage, inverter 8\n×128")
    _line(ax, (x, y), (x + 0.5, y), (x + 0.5, g_p[1]), g_p, c=HI, lw=2.6)
    _line(ax, (x + 0.5, y), (x + 0.5, g_n[1]), g_n, c=HI, lw=2.6)
    ax.text(0.2, 0.25, "every inverter 2 / 1 µm, L 0.18 µm, repeated ×m: m doubles stage to stage.   "
            "● probed node     orange: drives both output transistors", fontsize=11, color=SIZE)
    ax.set_title("inv_chain  |  eight inverters, ×2 taper, the eighth is the output stage  |  1.8 V",
                 fontweight="bold", fontsize=14.5)
    save(fig, "schematic_inv_chain.png")


def schematic_io_buf() -> None:
    fig, ax = _canvas()
    y_up, y_dn = 4.0, 1.9
    xin = 0.45
    ax.text(0.2, (y_up + y_dn) / 2 + 0.16, "in", ha="left", va="bottom", fontsize=13, fontweight="bold")
    ax.plot([xin], [(y_up + y_dn) / 2], "o", color=INK, ms=6, zorder=5)
    _line(ax, (xin, (y_up + y_dn) / 2), (xin + 0.35, (y_up + y_dn) / 2))
    xs = xin + 0.35
    s = 0.72
    # pull-up path: in -> NAND(in, oe) -> n2 -> PMOS
    _line(ax, (xs, (y_up + y_dn) / 2), (xs, y_up - s / 4), (xs + 3.1, y_up - s / 4))
    _line(ax, (xs + 2.7, y_up + s / 4), (xs + 3.1, y_up + s / 4))
    ax.text(xs + 2.65, y_up + s / 4, "oe = 1", ha="right", va="center", fontsize=11, color=SIZE)
    o2, _ = _nand(ax, xs + 3.1, y_up, s=s, label="NAND: P 2×64.2 / N 7.2 series")
    # pull-down path: in -> INV -> n1 -> NAND(n1, oe) -> nand_n3 -> INV -> n3 -> NMOS
    _line(ax, (xs, (y_up + y_dn) / 2), (xs, y_dn), (xs + 0.25, y_dn))
    o1, _ = _inv(ax, xs + 0.25, y_dn, label="3.6 / 1.8")
    _line(ax, (o1[0] if isinstance(o1, tuple) else o1, y_dn), (o1 + 0.9, y_dn))
    _node(ax, o1 + 0.45, y_dn, "n1")
    _line(ax, (o1 + 0.9, y_dn), (o1 + 0.9, y_dn + s / 4), (o1 + 1.2, y_dn + s / 4))
    _line(ax, (o1 + 0.85, y_dn - s / 4), (o1 + 1.2, y_dn - s / 4))
    ax.text(o1 + 0.8, y_dn - s / 4, "oe = 1", ha="right", va="center", fontsize=11, color=SIZE)
    o3, _ = _nand(ax, o1 + 1.2, y_dn, s=s, label="NAND: 2×64.2 / 7.2")
    _line(ax, (o3, y_dn), (o3 + 1.1, y_dn))
    _node(ax, o3 + 0.5, y_dn, "nand_n3")
    o4, _ = _inv(ax, o3 + 1.1, y_dn, label="32.1 / 7.2")
    xo = 11.0
    _line(ax, (o2, y_up), (xo - 0.25, y_up), c=HI, lw=2.6)
    _node(ax, o2 + 1.7, y_up, "n2  (PMOS gate)", gate=True)
    _line(ax, (o4, y_dn), (xo - 0.12, y_dn), c=HI, lw=2.6)
    _node(ax, o4 + 1.7, y_dn, "n3  (NMOS gate)", gate=True)
    _output_stage(ax, xo, y_up, y_dn, "3.3 V", "")
    ax.text(xo + 0.05, y_dn - 1.0, "output stage\n5×42.2 / 5×21.2, L 0.9",
            ha="center", va="top", fontsize=10.5, color=SIZE)
    ax.text(0.8, y_up + 0.95, "pull-up path", fontsize=13, fontweight="bold")
    ax.text(0.8, y_dn - 1.0, "pull-down path", fontsize=13, fontweight="bold")
    ax.text(0.2, 0.2, "W in µm, PMOS / NMOS; L = 0.6 µm unless noted.   ● probed node     "
            "orange: two separate gates, one per output transistor", fontsize=11, color=SIZE)
    ax.set_title("io_buf  |  two predriver paths, one per output transistor  |  3.3 V",
                 fontweight="bold", fontsize=14.5)
    save(fig, "schematic_io_buf.png")


# ------------------------------------------------ full-swing stage walks (to sit by slides 9/12/15)
import predriver_stage_probe as psp  # noqa: E402

FULL_RUNS = {"ex2": ("full_w3000ps", 3.0, 6.0), "inv_chain": ("full_w1000ps", 1.0, 1.8),
             "io_buf": ("full", 10.0, 15.5)}     # run, pulse width (ns), plot window (ns)


def full_walk(dev: str) -> None:
    """Every probed node on a full-swing pulse, in the format of Simon's 70 % stage walks on
    slides 9 / 12 / 15 (9 x 5 in, 160 dpi, viridis in signal order, input and pad thick). Each
    node is normalised to its own full swing from the 10 ns run, as there."""
    sub, w, xmax = FULL_RUNS[dev]
    nodes = psp.STAGES[dev]
    full = psp.parse_tr0(psp.OUT / dev / "full" / "run.tr0")
    tf, vf = sl.time_ns(full), psp.signals(full, nodes)
    raw = psp.parse_tr0(psp.OUT / dev / sub / "run.tr0")
    t, v = sl.time_ns(raw), psp.signals(raw, nodes)
    grid = np.arange(psp.RISE_NS - 0.2, psp.RISE_NS + xmax + 0.2, 0.002)
    cmap = plt.get_cmap("viridis")
    # matplotlib's own defaults, as Simon's 70 % figures use (the 09-17 module sets larger ones)
    keys = ("font.size", "axes.titlesize", "axes.labelsize", "xtick.labelsize", "ytick.labelsize",
            "legend.fontsize", "axes.linewidth", "lines.linewidth", "grid.alpha")
    ctx = plt.rc_context({k: matplotlib.rcParamsDefault[k] for k in keys})
    ctx.__enter__()
    fig, a = plt.subplots(figsize=(9, 5))
    for i, n in enumerate(nodes):
        g, _, _ = psp.normalise(tf, vf[n], t, v[n])
        name = n.replace("v(xdut.", "").replace("v(", "").rstrip(")")
        name = {"pad_sp": "pad", "in_dig": "input"}.get(name, name)
        a.plot(grid - psp.RISE_NS, np.interp(grid, t, g), color=cmap(i / max(1, len(nodes) - 1)),
               lw=2.4 if i in (0, len(nodes) - 1) else 1.6, label=name)
    a.axvline(w, color="#8A8A8A", ls="--", lw=1.0)
    a.set_xlim(-0.2, xmax)
    a.set_ylim(-0.2, 1.15)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("each node, 0 = rest, 1 = its full swing")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="center right")
    a.set_title(f"{dev}, full swing ({w:g} ns pulse)", fontweight="bold", fontsize=13)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"full_walk_{dev}.png", dpi=160)
    plt.close(fig)
    ctx.__exit__(None, None, None)
    print(f"  full_walk_{dev}.png")


def how_mapping_works() -> None:
    """How a gate-state model turns Ku into a function of the gate, for our GUP and for the real
    gate. ex2, C_comp 1.7 pF (measured; at the declared 5 pF the file's Ku overshoots to 1.23).
    Column 1: the full-swing rising edge - the file's Ku(t) and the gate, paired instant by
    instant (coloured markers). Column 2: the resulting curves ku_rise / ku_fall, read from the
    netlist the run used; the markers land on ku_rise. Column 3: the 858 ps pulse - the gate that
    drives the model, and the curve's output Ku = curve(gate) (KUGATE_BASE; the model adds a
    time-indexed residual, <= 0.09 here), with the transistor's Ku for reference."""
    from matplotlib.patches import ConnectionPatch
    base = f17.CASC / "ex2_c1.7"
    rows = (("A", "gate_state_fixed: our gate GUP (a fixed delay, then an RC ramp)", "shipped",
             "shipped/driver.sub", OURS, "our GUP"),
            ("B", "real gate: the transistor's own gate node n4, replayed", "gate_replay",
             "gate_replay/driver_replay_full.sub", REAL, "real gate n4"))
    ship_full = sl.parse_ngspice_raw(base / "shipped" / "full" / "run.raw")
    tfu, kfile = sl.time_ns(ship_full) - 5.0, sl.signal(ship_full, "v(x1.kugate_base)")
    # the transistor's Ku at 858 ps, solved from the matrix fixture runs at THIS C_comp (1.7 pF);
    # the matrix CSV's silicon_ku is solved at the declared 5 pF and peaks early and high
    import gate_ramp_prototype as gp
    import silicon_map_replay as smr
    from pybis2spice import pybis2spice as pb
    from extract_silicon_kukd import solve_silicon_kukd
    gp.VARIANT_NAME = "ex2"
    sup, ibis = gp.VARIANTS["ex2"]
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    data.c_comp = [1.7e-12] * 3
    fx = smr.FIX / "ex2" / "short_high_w858ps"
    sol = solve_silicon_kukd(data, smr.fixture(fx / "vfix_0/run.tr0"), smr.fixture(fx / "vfix_vcc/run.tr0"), sup, uniform_ps=5.0)
    xk, kk = sol[:, 0] * 1e9 - 5.0, sol[:, 1].copy()
    for edge in (0.0, 0.858):
        kk[(xk > edge - 0.02) & (xk < edge + 0.09)] = np.nan
    marks = (0.1, 0.4, 0.7, 0.95)                      # pair at the instants the file's Ku reaches these
    mcol = plt.get_cmap("plasma")(np.linspace(0.05, 0.8, len(marks)))
    rise = (tfu > 0.0) & (tfu < 3.0)
    t_mark = [float(tfu[rise][np.argmax(kfile[rise] >= m)]) for m in marks]
    curves = {}
    with plt.rc_context(BODY | {"axes.titlesize": 12.5, "legend.fontsize": 10.5}):
        fig, axes = plt.subplots(2, 3, figsize=(12.2, 7.0), gridspec_kw={"width_ratios": [1.15, 0.85, 1.25]})
        for r, (tag, what, sub, subck, col, gname) in enumerate(rows):
            if sub == "shipped":
                g_full = sl.signal(ship_full, "v(x1.gup)")
                tg = tfu
            else:
                rp = sl.parse_ngspice_raw(base / "gate_replay" / "full_pass1" / "run.raw")
                tg, g_full = sl.time_ns(rp) - 5.0, sl.signal(rp, "v(x1.gup)")
            on, off = f17._pwl_table(base / subck, "KUGATE_ON"), f17._pwl_table(base / subck, "KUGATE_OFF")
            curves[tag] = on
            # --- column 1: build
            a = axes[r][0]
            a.plot(tfu, kfile, color="#333333", lw=2.4, label="Ku(t) from the IBIS file")
            a.plot(tg, g_full, color=col, lw=2.4, label=f"{gname}(t)")
            for tm, c in zip(t_mark, mcol):
                gk, kv = float(np.interp(tm, tg, g_full)), float(np.interp(tm, tfu, kfile))
                a.plot([tm, tm], [min(gk, kv), max(gk, kv)], color=c, lw=1.2, ls=":")
                a.plot([tm], [kv], "o", color=c, ms=7, zorder=5)
                a.plot([tm], [gk], "s", color=c, ms=7, zorder=5)
            a.set_xlim(-0.1, 2.2)
            a.set_ylim(-0.08, 1.12)
            a.set_xlabel("Time from the input edge (ns)")
            a.set_ylabel(f"{tag}", rotation=0, fontsize=20, fontweight="bold", labelpad=18, va="center")
            a.grid(alpha=0.3)
            from matplotlib.lines import Line2D
            h, lab = a.get_legend_handles_labels()
            h.append(Line2D([], [], color="#777777", ls=":", marker="o", ms=6))
            lab.append("● ■ one instant")
            lab[0] = "Ku(t), IBIS file"
            a.legend(h, lab, loc="upper left", fontsize=9.5)
            a.set_title("1. full swing: pair Ku and the gate\nat each instant", fontweight="bold")
            # --- column 2: the curve
            b = axes[r][1]
            other = curves.get("A") if tag == "B" else None
            if other is not None:
                b.plot(other[:, 0], other[:, 1], color=OURS, lw=1.4, alpha=0.35, label="row A's ku_rise")
            b.plot(on[:, 0], on[:, 1], color=col, lw=2.6, label="ku_rise(g)")
            b.plot(off[:, 0], off[:, 1], color=col, lw=1.8, ls="--", label="ku_fall(g)")
            for tm, c in zip(t_mark, mcol):
                gk, kv = float(np.interp(tm, tg, g_full)), float(np.interp(tm, tfu, kfile))
                b.plot([gk], [kv], "o", color=c, ms=8, zorder=5, mec="white", mew=0.8)
            b.set_xlim(0, 1.02)
            b.set_ylim(-0.08, 1.12)
            b.set_xlabel(f"gate ({gname}), 0 to 1")
            b.set_ylabel("Ku")
            b.grid(alpha=0.3)
            b.legend(loc="upper left", fontsize=10)
            b.set_title("2. the curve: Ku as a\nfunction of the gate", fontweight="bold")
            # --- column 3: use it on the short pulse
            c3 = axes[r][2]
            rs = sl.parse_ngspice_raw(base / sub / "d858" / "run.raw")
            ts = sl.time_ns(rs) - 5.0
            gs_, kb = sl.signal(rs, "v(x1.gup)"), sl.signal(rs, "v(x1.kugate_base)")
            c3.plot(xk, kk, color=SIL, lw=5.0, alpha=0.35, label="transistor's Ku")
            c3.plot(ts, gs_, color=col, lw=1.8, ls="--", label=f"{gname}(t), drives it")
            c3.plot(ts, kb, color=col, lw=2.6, label="Ku = curve(gate)")
            c3.axvline(0.858, color=f17.REV, ls="--", lw=1.3)
            on_s, used = sl.signal(rs, "v(x1.kugate_on)"), kb
            i = int(np.argmax((ts > 0.9) & (np.abs(on_s - used) > 0.02)))
            c3.axvline(float(ts[i]), color=col, ls=":", lw=1.3)
            c3.text(float(ts[i]) + 0.03, 1.1, "switch to ku_fall", color=col, fontsize=10, va="center")
            t_si, si, rev = f17.transistor_pad("ex2", 858)
            tp, vp = f17.raw_pad(base / sub / "d858" / "run.raw")
            win = lambda x: (x >= rev - 0.3) & (x <= rev + 2.6)   # noqa: E731
            e = 100 * (float(vp[win(tp)].max()) - float(si[win(t_si)].max())) / float(si[win(t_si)].max())
            c3.set_xlim(0.4, 2.6)
            c3.set_ylim(-0.12, 2.25)
            c3.set_yticks([0.0, 0.5, 1.0])
            c3.set_xlabel("Time from the input edge (ns)")
            c3.grid(alpha=0.3)
            c3.legend(loc="upper left", fontsize=9.5)
            c3.set_title(f"3. 858 ps pulse: read Ku off the\ncurve at each instant (pad {e:+.1f} %)", fontweight="bold")
            print(f"      {tag}: pad {e:+.1f} %, switch at {ts[i]:.3f} ns (gate {gs_[i]:.2f})")
        fig.suptitle("ex2  |  the same Ku(t) from the file, paired with two different gates  |  C_comp 1.7 pF",
                     fontweight="bold", fontsize=14.5)
        # layout first; row titles and arrows are placed afterwards so they do not enter it
        fig.tight_layout(rect=(0.03, 0, 1, 0.95), h_pad=4.5, w_pad=3.5)
        for r, (tag, what, *_rest) in enumerate(rows):
            col = rows[r][4]
            top = axes[r][0].get_position().y1
            fig.text(0.035, top + 0.075, what, fontsize=13.5, fontweight="bold", color=col)
            for src, dst in ((axes[r][0], axes[r][1]), (axes[r][1], axes[r][2])):
                p0, p1 = src.get_position(), dst.get_position()
                cp = ConnectionPatch(xyA=(p0.x1 + 0.004, (p0.y0 + p0.y1) / 2), coordsA=fig.transFigure,
                                     xyB=(p1.x0 - 0.045, (p1.y0 + p1.y1) / 2), coordsB=fig.transFigure,
                                     arrowstyle="-|>", mutation_scale=16, lw=2.0, color="#555555")
                fig.add_artist(cp)
        fig.savefig(OUT / "how_mapping_works.png", dpi=200)
        plt.close(fig)
    print("  how_mapping_works.png")


def full_walks() -> None:
    for dev in ("io_buf", "ex2", "inv_chain"):
        full_walk(dev)


def iobuf_paths() -> None:
    """io_buf's two predriver paths as separate figures, full swing and 70 % stress (2090 ps),
    in the same format; each node keeps the colour it has in the combined figure."""
    dev = "io_buf"
    allnodes = psp.STAGES[dev]            # input, n1, nand_n3, n3, n2, pad
    paths = {"pull-up": ["v(in_dig)", "v(xdut.n2)", "v(pad_sp)"],
             "pull-down": ["v(in_dig)", "v(xdut.n1)", "v(xdut.nand_n3)", "v(xdut.n3)", "v(pad_sp)"]}
    cases = (("full", 10.0, 15.5, "full swing (10 ns pulse)", "full"), ("w2090", 2.09, 5.5, "70 % stress", "70"))
    keys = ("font.size", "axes.titlesize", "axes.labelsize", "xtick.labelsize", "ytick.labelsize",
            "legend.fontsize", "axes.linewidth", "lines.linewidth", "grid.alpha")
    full = psp.parse_tr0(psp.OUT / dev / "full" / "run.tr0")
    tf, vf = sl.time_ns(full), psp.signals(full, allnodes)
    cmap = plt.get_cmap("viridis")
    with plt.rc_context({k: matplotlib.rcParamsDefault[k] for k in keys}):
        for sub, w, xmax, what, tag in cases:
            raw = psp.parse_tr0(psp.OUT / dev / sub / "run.tr0")
            t, v = sl.time_ns(raw), psp.signals(raw, allnodes)
            grid = np.arange(psp.RISE_NS - 0.2, psp.RISE_NS + xmax + 0.2, 0.002)
            for pname, nodes in paths.items():
                fig, a = plt.subplots(figsize=(9, 5))
                for n in nodes:
                    i = allnodes.index(n)
                    g, _, _ = psp.normalise(tf, vf[n], t, v[n])
                    name = n.replace("v(xdut.", "").replace("v(", "").rstrip(")")
                    name = {"pad_sp": "pad", "in_dig": "input", "n2": "n2 (PMOS gate)",
                            "n3": "n3 (NMOS gate)"}.get(name, name)
                    a.plot(grid - psp.RISE_NS, np.interp(grid, t, g), color=cmap(i / (len(allnodes) - 1)),
                           lw=2.4 if n in ("v(in_dig)", "v(pad_sp)") else 1.6, label=name)
                a.axvline(w, color="#8A8A8A", ls="--", lw=1.0)
                a.set_xlim(-0.2, xmax)
                a.set_ylim(-0.2, 1.15)
                a.set_xlabel("time from the input rising edge (ns)")
                a.set_ylabel("each node, 0 = rest, 1 = its full swing")
                a.grid(alpha=0.3)
                a.legend(fontsize=9, loc="center right")
                if pname == "pull-down":
                    a.text(0.99, 0.02, "n3 at 1 = the pull-down is off", transform=a.transAxes,
                           ha="right", va="bottom", fontsize=9, color="#555555")
                a.set_title(f"io_buf {pname} path, {what}", fontweight="bold", fontsize=13)
                fig.tight_layout()
                name = f"iobuf_{pname.replace('-', '')}_{tag}.png"
                fig.savefig(OUT / name, dpi=160)
                plt.close(fig)
                print(f"  {name}")


def main() -> int:
    print("building 0918 deck figures")
    jobs = [recap_pad, schematic_io_buf, schematic_ex2, schematic_inv_chain, full_walks, iobuf_paths,
            how_mapping_works, inv_why_111, three_handoffs, inv_fixed_111, vinh_inv, slew_0918, method_track1, method_result,
            lambda: stress_levels("ex2", "ex2_stress_levels.png", (-0.4, 2.2), [0, 1, 2]),
            lambda: stress_levels("inv_chain", "inv_chain_stress_levels.png", (-0.1, 0.6), [0, 0.2, 0.4])]
    for dev in SPECS:
        jobs.append(lambda dev=dev: four_panel(dev, replay=False))
        jobs.append(lambda dev=dev: four_panel(dev, replay=True))
    for fn in jobs:
        try:
            fn()
        except Exception as exc:  # one bad path must not cost the whole set
            print(f"  FAILED: {exc!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
