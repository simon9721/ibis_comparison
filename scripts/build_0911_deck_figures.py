#!/usr/bin/env python3
"""Figures for the 2026-09-11 deck update: the cmd_clean command (slide 7) and the variant
stress results (slide 9). Nothing here re-simulates; every figure is drawn from existing runs.

    results/meeting_deck_2026-09-11/figures/
      cmd_clean_command.png        io_buf 1792 ps: input, the command node, the gate, original vs cmd_clean
      variants_same_stress.png     one family per panel: the transistor's pad on every variant at 50 % depth
      variants_model_vs_si.png     one panel per variant at 50 % depth: transistor, ours, native
      variants_peak_law.png        peak excess against depth, ours and native, one panel per family
      variants_what_changed.png    what was changed in the silicon against how much the error moved
      variants_entry.png           the mechanism: how far 'on' each model is when the transistor's pad peaks
      variants_two_regimes.png     where each buffer's event sits: io_buf alone in the residual corner

    py -3.14 scripts/build_0911_deck_figures.py
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

R = ROOT / "results"
OUT = R / "meeting_deck_2026-09-11" / "figures"
CROSS = R / "cross_device_stress_2026-09-08"
VAR = R / "variant_stress_cases_2026-09-04"
CMD = R / "command_mechanism_2026-09-04" / "command_mechanism.csv"

# last week's palette
C_SI, C_NAT, C_ORIG, C_FIX, C_CLEAN = "#111111", "#2B6CA3", "#C05621", "#7A3E9D", "#2E8B57"
FAMILY = {"inv": "#2E8B57", "ex2": "#B03060", "io_": "#111111"}
DESC = {
    "inv_base8": "base8: 8 stages, x2 taper", "inv_stage4": "stage4: 4 stages, same output",
    "inv_skewp": "skewp: PMOS half width (Wp = Wn)", "inv_weak": "weak: half drive at every stage",
    "inv_chain": "inv_chain (shipped)",
    "ex2_base": "base: as shipped", "ex2_slowpre": "slowpre: predriver half width",
    "ex2_skewp": "skewp: output PMOS half width", "ex2_weak": "weak: output stage half width",
    "ex2_nomiller": "nomiller: gate-drain caps removed", "ex2": "ex2 (shipped)", "io_buf": "io_buf",
}
CHANGE = {  # what the variant touches: the predriver (timing) or the output stage (drive)
    "inv_base8": "reference", "inv_stage4": "predriver", "inv_skewp": "output stage", "inv_weak": "both",
    "ex2_base": "reference", "ex2_slowpre": "predriver", "ex2_skewp": "output stage",
    "ex2_weak": "output stage", "ex2_nomiller": "output stage",
}
MARK = {"inv_base8": "o", "inv_stage4": "s", "inv_skewp": "^", "inv_weak": "v", "inv_chain": "D",
        "ex2_base": "o", "ex2_slowpre": "s", "ex2_skewp": "^", "ex2_weak": "v", "ex2_nomiller": "P",
        "ex2": "D", "io_buf": "*"}
EX2 = ["ex2_base", "ex2_slowpre", "ex2_skewp", "ex2_weak", "ex2_nomiller"]
INV = ["inv_base8", "inv_stage4", "inv_skewp", "inv_weak"]


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=170)
    plt.close(fig)
    print("  wrote", OUT / name)


# ----------------------------------------------------------------------------------------- #
# slide 7: the command
# ----------------------------------------------------------------------------------------- #
def cmd_clean_command():
    rows = list(csv.DictReader(open(CMD)))
    t = np.array([f(r["time_ns"]) for r in rows])
    g = lambda k: np.array([f(r[k]) for r in rows])  # noqa: E731
    rise, fall, edge, sup = 5.000, 6.790, 0.050, 3.3
    tin = np.array([0, rise, rise + edge, fall, fall + edge, 14])
    vin = np.array([0, 0, sup, sup, 0, 0])
    fig, ax = plt.subplots(3, 1, figsize=(13, 8.2), sharex=True)
    for a in ax:
        for x, lab in ((rise, "rising edge"), (fall, "falling edge")):
            a.axvline(x, color="#888", ls="--", lw=1.0)
        a.grid(alpha=0.3)
    ax[0].plot(tin, vin, color="#444", lw=2.2)
    ax[0].set_ylabel("Input (V)")
    ax[0].set_title("1. Input stimulus  (io_buf, short high, 1792 ps)", loc="left", fontweight="bold")
    ax[0].text(rise + 0.03, sup * 0.85, "rising edge", color="#666", fontsize=9)
    ax[0].text(fall + 0.03, sup * 0.85, "falling edge", color="#666", fontsize=9)
    ax[1].plot(t, g("gate_state_gupcmd"), color=C_ORIG, lw=2.2, label="original: GUPCMD is a capacitor charged by an edge packet")
    ax[1].plot(t, g("delay_cmd_gupcmd"), color=C_CLEAN, lw=2.2, label="cmd_clean: GUPCMD is the input level, delayed")
    ax[1].axhline(0, color="#111", lw=0.8)
    ax[1].set_ylabel("Command (GUPCMD)")
    ax[1].set_title("2. The command node: where the fix lives", loc="left", fontweight="bold")
    ax[1].legend(fontsize=9, loc="upper right")
    y0 = g("gate_state_gupcmd")
    m = (t > 8.0) & (t < 8.5)
    ax[1].annotate(f"stranded at {np.mean(y0[m]):+.2f} after the pulse,\nleaks away over ~4 ns",
                   xy=(8.2, np.mean(y0[m])), xytext=(8.6, 0.45), fontsize=9, color=C_ORIG,
                   arrowprops=dict(arrowstyle="->", color=C_ORIG))
    ax[1].annotate("exactly 0 or 1 by construction", xy=(9.5, 0.0), xytext=(9.6, 0.25), fontsize=9, color=C_CLEAN,
                   arrowprops=dict(arrowstyle="->", color=C_CLEAN))
    ax[2].plot(t, g("gate_state_gup"), color=C_ORIG, lw=2.2, label="original")
    ax[2].plot(t, g("delay_cmd_gup"), color=C_CLEAN, lw=2.2, label="cmd_clean")
    ax[2].axhline(0, color="#111", lw=0.8)
    ax[2].set_ylabel("Gate state (GUP)")
    ax[2].set_title("3. The pull-up gate state follows its command: the stranded offset becomes a stranded gate", loc="left", fontweight="bold")
    ax[2].legend(fontsize=9, loc="upper right")
    ax[2].set_xlabel("Time (ns)")
    ax[2].set_xlim(4.5, 12.0)
    fig.suptitle("cmd_clean: the command is a delayed copy of the input level, not a charge that has to be cleaned up", fontsize=13, fontweight="bold")
    save(fig, "cmd_clean_command.png")


# ----------------------------------------------------------------------------------------- #
# slide 9: the variants
# ----------------------------------------------------------------------------------------- #
def load_cross():
    cases = {(c["variant"], int(c["depth"])): c for c in csv.DictReader(open(CROSS / "cases.csv"))}
    met = defaultdict(dict)
    for r in csv.DictReader(open(CROSS / "metrics.csv")):
        met[(r["variant"], int(r["depth"]))][r["model"]] = r
    return cases, met


def series(cases, met, v, model, key):
    ks = sorted([k for k in cases if k[0] == v], key=lambda k: k[1])
    xs, ys = [], []
    for k in ks:
        row = met[k].get(model)
        if row is None or int(row["valid"]) != 1:
            continue
        xs.append(k[1])
        ys.append(f(row[key]))
    return np.array(xs, float), np.array(ys, float)


def case_dir(variant, depth):
    d = sorted(VAR.glob(f"{variant}/depth{depth}_w*ps"), key=lambda p: p.stat().st_mtime)
    return d[-1] if d else None


def full_swing_v(variant):
    """Each variant's settled full-swing excursion, from the case table (excursion / achieved depth)."""
    vals = []
    for r in csv.DictReader(open(VAR / "cases.csv")):
        if r["variant"] == variant:
            vals.append(f(r["tx_excursion_v"]) / (f(r["depth_achieved_pct"]) / 100.0))
    return float(np.median(vals))


def waveforms(variant, depth):
    d = case_dir(variant, depth)
    w = float(d.name.split("_w")[1].rstrip("ps")) / 1e3
    rows = list(csv.DictReader(open(d / "waveforms.csv")))
    t = np.array([f(r["time_ns"]) for r in rows])
    g = lambda k: np.array([f(r[k]) for r in rows])  # noqa: E731
    return dict(t=t, rev=5.0 + w, w=w, si=g("silicon_pad"), ours=g("delay_cmd_pad"), nat=g("native_pad"),
                si_ku=g("silicon_ku"), ours_ku=g("delay_cmd_ku"), nat_ku=g("native_ku"))


MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"


def matrix_waveforms(name, width_ps):
    rows = list(csv.DictReader(open(MATRIX / f"{name}_short_high_w{width_ps}ps.csv")))
    t = np.array([f(r["time_ns"]) for r in rows])
    g = lambda k: np.array([f(r[k]) for r in rows])  # noqa: E731
    return dict(t=t, rev=5.0 + width_ps / 1e3, w=width_ps / 1e3, si=g("silicon_pad"), ours=g("pybis_pad"), nat=g("hspice_pad"),
                si_ku=g("silicon_ku"), ours_ku=g("pybis_ku"), nat_ku=g("hspice_ku"))


def _pad_panel(a, wv, fs, xlim, nat_ok, label_first=False):
    x = wv["t"] - wv["rev"]
    m = (x > xlim[0]) & (x < xlim[1])
    a.plot(x[m], wv["si"][m] / fs, color=C_SI, lw=3.0, label="transistor")
    if nat_ok:
        a.plot(x[m], wv["nat"][m] / fs, color=C_NAT, lw=1.6, label="native HSPICE IBIS")
    else:
        a.plot(x[m], wv["nat"][m] / fs, color=C_NAT, lw=1.6, ls=":", label="native HSPICE IBIS (dead: its 2-waveform solver fails on this file)")
    a.plot(x[m], wv["ours"][m] / fs, color=C_CLEAN, lw=1.9, ls="--", label="ours (cmd_clean)")
    a.axvline(0, color="#888", ls="--", lw=1)
    a.grid(alpha=0.3)
    if label_first:
        a.legend(fontsize=8)


def variants_depth_waves():
    """Slide 13: the error growing as the pulse shortens, on real pads."""
    cases, met = load_cross()
    fig, axes = plt.subplots(2, 5, figsize=(19, 7.4))
    for r, v in enumerate(("ex2_base", "inv_base8")):
        fs = full_swing_v(v)
        for c, depth in enumerate((90, 80, 70, 60, 50)):
            a = axes[r, c]
            wv = waveforms(v, depth)
            nat_ok = met[(v, depth)]["native"]["valid"] == "1"
            _pad_panel(a, wv, fs, (-0.4, 2.2) if v == "ex2_base" else (-0.15, 0.75), nat_ok, label_first=(r == 0 and c == 0))
            e = f(met[(v, depth)]["delay_cmd"]["pad_peak_err_pct"])
            en = f(met[(v, depth)]["native"]["pad_peak_err_pct"]) if nat_ok else None
            a.set_title(f"{DESC[v].split(':')[0]}  {depth} % depth, pulse {wv['w'] * 1e3:.0f} ps\nours {e:+.0f} %" + (f", native {en:+.0f} %" if en is not None else ", native dead (dotted)"),
                        fontsize=9.5, fontweight="bold")
            if c == 0:
                a.set_ylabel("pad / full swing")
            if r == 1:
                a.set_xlabel("time from reversal (ns)")
    fig.suptitle("The same buffer, five pulse widths: the shorter the pulse, the more the models overshoot the transistor (the transistor's own peak falls, the models' barely does)",
                 fontsize=12.5, fontweight="bold")
    save(fig, "variants_depth_waves.png")


def variants_change_waves():
    """Slide 14: what changed in the silicon, on real pads at the same depth."""
    cases, met = load_cross()
    trio = (("ex2_base", "ex2_slowpre", "ex2_weak"), ("inv_base8", "inv_stage4", "inv_weak"))
    fig, axes = plt.subplots(2, 3, figsize=(17, 8))
    for r, vs in enumerate(trio):
        for c, v in enumerate(vs):
            a = axes[r, c]
            fs = full_swing_v(v)
            wv = waveforms(v, 50)
            nat_ok = met[(v, 50)]["native"]["valid"] == "1"
            _pad_panel(a, wv, fs, (-0.4, 2.2) if v.startswith("ex2") else (-0.15, 0.75), nat_ok, label_first=(r == 0 and c == 0))
            e = f(met[(v, 50)]["delay_cmd"]["pad_peak_err_pct"])
            en = f(met[(v, 50)]["native"]["pad_peak_err_pct"]) if nat_ok else None
            a.set_title(f"{DESC[v]}\n50 % depth, pulse {wv['w'] * 1e3:.0f} ps: ours {e:+.0f} %" + (f", native {en:+.0f} %" if en is not None else ", native dead (dotted)"),
                        fontsize=10, fontweight="bold")
            if c == 0:
                a.set_ylabel("pad / full swing")
            if r == 1:
                a.set_xlabel("time from reversal (ns)")
    fig.suptitle("Same depth, different silicon. ex2: halving the output stage changes nothing (+71 → +66 %), halving the predriver takes a third off (+45 %).\n"
                 "inv: halving the stage count and halving the drive both take a third to a half off; on a 100 ps pulse the output stage's own speed limits the pad too.",
                 fontsize=12, fontweight="bold")
    save(fig, "variants_change_waves.png")


def variants_mechanism_waves():
    """Slide 15: Ku(t) on real traces: ours is fully on when the transistor's pad peaks."""
    cases, met = load_cross()
    vs = ("ex2_base", "ex2_slowpre", "inv_base8")
    fig, axes = plt.subplots(2, 3, figsize=(17, 8), sharex="col")
    for c, v in enumerate(vs):
        wv = waveforms(v, 50)
        fs = full_swing_v(v)
        x = wv["t"] - wv["rev"]
        xlim = (-0.4, 2.0) if v.startswith("ex2") else (-0.15, 0.7)
        m = (x > xlim[0]) & (x < xlim[1])
        nat_ok = met[(v, 50)]["native"]["valid"] == "1"
        # transistor pad peak instant
        ipk = int(np.argmax(np.where(m & (x > 0), wv["si"], -np.inf)))
        tpk = x[ipk]
        a = axes[0, c]
        a.plot(x[m], wv["si_ku"][m], color=C_SI, lw=3.0, label="transistor Ku")
        a.plot(x[m], wv["nat_ku"][m], color=C_NAT, lw=1.6, ls="-" if nat_ok else ":", label="native Ku" if nat_ok else "native Ku (dead)")
        a.plot(x[m], wv["ours_ku"][m], color=C_CLEAN, lw=1.9, ls="--", label="ours Ku")
        a.axvline(0, color="#888", ls="--", lw=1)
        a.axvline(tpk, color="#B03060", lw=1.2)
        ku_si, ku_o = float(wv["si_ku"][ipk]), float(wv["ours_ku"][ipk])
        a.annotate(f"transistor Ku {ku_si:.2f}", (tpk, ku_si), textcoords="offset points", xytext=(10, -14), fontsize=9, color=C_SI)
        a.annotate(f"ours Ku {ku_o:.2f}", (tpk, ku_o), textcoords="offset points", xytext=(10, 6), fontsize=9, color=C_CLEAN)
        a.set_ylim(-0.15, 1.3)
        a.set_title(f"{DESC[v]}, 50 % depth\nred line = when the transistor's pad peaks", fontsize=10, fontweight="bold")
        a.grid(alpha=0.3)
        if c == 0:
            a.legend(fontsize=8, loc="upper left")
            a.set_ylabel("Ku (pull-up fraction on)")
        b = axes[1, c]
        _pad_panel(b, wv, fs, xlim, nat_ok, label_first=(c == 0))
        b.axvline(tpk, color="#B03060", lw=1.2)
        b.set_xlabel("time from reversal (ns)")
        if c == 0:
            b.set_ylabel("pad / full swing")
    fig.suptitle("The mechanism on real traces: when the transistor's pad peaks its pull-up is only 20 to 40 % on; the model's pull-up is still fully on, so its pad keeps rising",
                 fontsize=12, fontweight="bold")
    save(fig, "variants_mechanism_waves.png")


def variants_regime_waves():
    """Slide 16: io_buf against ex2 on the same instrument: the gate at the reversal."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 8), sharex="col")
    for c, (name, wps, fs, xlim, note) in enumerate((
            ("io_buf", 1792, 1.5233, (-1.9, 1.6), "pad peaks 100 ps after the reversal, gate caught while still opening"),
            ("ex2", 858, 1.5451, (-0.9, 1.6), "pad peaks 700 ps after the reversal, after the predriver has closed the gate again"))):
        wv = matrix_waveforms(name, wps)
        x = wv["t"] - wv["rev"]
        m = (x > xlim[0]) & (x < xlim[1])
        ipk = int(np.argmax(np.where(m & (x > 0.05), wv["si"], -np.inf)))
        tpk = x[ipk]
        a = axes[0, c]
        a.plot(x[m], wv["si_ku"][m], color=C_SI, lw=3.0, label="transistor Ku")
        a.plot(x[m], wv["nat_ku"][m], color=C_NAT, lw=1.6, label="native Ku")
        a.plot(x[m], wv["ours_ku"][m], color=C_CLEAN, lw=1.9, ls="--", label="ours Ku (cmd_clean)")
        a.axvline(0, color="#888", ls="--", lw=1.2)
        a.axvline(tpk, color="#B03060", lw=1.2)
        if c == 0:
            # io_buf: the solve is unusable within ~90 ps of the reversal, so read the gate just before it
            i0 = int(np.argmin(np.abs(x + 0.06)))
            a.annotate(f"just before the reversal: Ku {wv['si_ku'][i0]:.2f} and still rising,\nboth models on the same curve",
                       (x[i0], wv["si_ku"][i0]), textcoords="offset points", xytext=(-260, 40), fontsize=9.5,
                       arrowprops=dict(arrowstyle="->", color="#444"))
        else:
            ku_si, ku_o = float(wv["si_ku"][ipk]), float(wv["ours_ku"][ipk])
            a.annotate(f"at the transistor's pad peak:\ntransistor Ku {ku_si:.2f} and falling, ours {ku_o:.2f}", (tpk, max(ku_si, ku_o)),
                       textcoords="offset points", xytext=(30, 30), fontsize=9.5, arrowprops=dict(arrowstyle="->", color="#444"))
        a.set_ylim(-0.3, 1.4)
        a.set_title(f"{name}, short high, {wps} ps pulse\n{note}", fontsize=10.5, fontweight="bold")
        a.grid(alpha=0.3)
        if c == 0:
            a.legend(fontsize=8, loc="upper right")
            a.set_ylabel("Ku (pull-up fraction on)")
        b = axes[1, c]
        b.plot(x[m], wv["si"][m] / fs, color=C_SI, lw=3.0, label="transistor")
        b.plot(x[m], wv["nat"][m] / fs, color=C_NAT, lw=1.6, label="native HSPICE IBIS")
        b.plot(x[m], wv["ours"][m] / fs, color=C_CLEAN, lw=1.9, ls="--", label="ours (cmd_clean)")
        b.axvline(0, color="#888", ls="--", lw=1.2)
        b.axvline(tpk, color="#B03060", lw=1.2)
        b.grid(alpha=0.3)
        b.set_xlabel("time from the input reversal (ns)")
        if c == 0:
            b.set_ylabel("pad / full swing")
            b.legend(fontsize=8)
    fig.suptitle("Two regimes (dashed = input reversal, red = transistor's pad peak).  io_buf: a slow gate, caught while still opening; both models follow, the error is the residual afterwards.\n"
                 "ex2: the pad peaks 700 ps later, when the transistor's predriver has already closed the gate again, while the models' gate is still fully on.",
                 fontsize=11, fontweight="bold")
    save(fig, "variants_regime_waves.png")


def main() -> int:
    cmd_clean_command()
    variants_same_stress()
    variants_model_vs_si()
    variants_depth_waves()
    variants_change_waves()
    variants_mechanism_waves()
    variants_regime_waves()
    variants_peak_law()
    variants_what_changed()
    variants_entry()
    variants_two_regimes()
    return 0


def variants_same_stress(depth=50):
    fig, ax = plt.subplots(1, 2, figsize=(15, 5.6))
    for a, fam, vs in ((ax[0], "ex2", EX2), (ax[1], "inv", INV)):
        cm = plt.get_cmap("viridis")
        for i, v in enumerate(vs):
            wv = waveforms(v, depth)
            fs = full_swing_v(v)
            x = wv["t"] - wv["rev"]
            m = (x > -0.6) & (x < 2.2 if fam == "ex2" else x < 0.8)
            a.plot(x[m], wv["si"][m] / fs, color=cm(i / max(1, len(vs) - 1)), lw=2.4,
                   label=f"{DESC[v]}  (pulse {wv['w'] * 1e3:.0f} ps)")
        a.axhline(0.5, color="#999", ls=":", lw=1)
        a.axvline(0, color="#888", ls="--", lw=1)
        a.set_title(f"{fam} family, transistor only, every variant at {depth} % depth", fontweight="bold")
        a.set_xlabel("time from the input reversal (ns)")
        a.set_ylabel("pad, as a fraction of that variant's full swing")
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.suptitle("Same stress, different silicon: the pulse width that reaches 50 % is set by the predriver, the shape after the reversal is the family's",
                 fontsize=12.5, fontweight="bold")
    save(fig, "variants_same_stress.png")


def variants_model_vs_si(depth=50):
    cases, met = load_cross()
    vs = EX2 + INV
    fig, axes = plt.subplots(2, 5, figsize=(19, 7.6))
    for i, v in enumerate(vs):
        a = axes.ravel()[i if i < 5 else i + 1] if False else axes.ravel()[i]
        wv = waveforms(v, depth)
        fs = full_swing_v(v)
        x = wv["t"] - wv["rev"]
        m = (x > -0.5) & (x < (2.2 if v.startswith("ex2") else 0.8))
        a.plot(x[m], wv["si"][m] / fs, color=C_SI, lw=3.0, label="transistor")
        nat_ok = met.get((v, depth), {}).get("native", {}).get("valid") == "1"
        a.plot(x[m], wv["nat"][m] / fs, color=C_NAT, lw=1.6, ls="-" if nat_ok else ":",
               label="native HSPICE IBIS" if nat_ok else "native HSPICE IBIS (dead: solver fails on this file)")
        a.plot(x[m], wv["ours"][m] / fs, color=C_CLEAN, lw=1.8, ls="--", label="ours (cmd_clean)")
        e = f(met[(v, depth)]["delay_cmd"]["pad_peak_err_pct"])
        en = f(met[(v, depth)]["native"]["pad_peak_err_pct"]) if nat_ok else None
        a.set_title(f"{DESC[v]}\nours {e:+.0f} %" + (f", native {en:+.0f} %" if en is not None else ", native dead (dotted)"), fontsize=9.5, fontweight="bold")
        a.axvline(0, color="#888", ls="--", lw=1)
        a.grid(alpha=0.3)
        if i == 0:
            a.legend(fontsize=8)
            a.set_ylabel("pad / full swing")
        if i >= 5:
            a.set_xlabel("time from reversal (ns)")
    axes.ravel()[-1].axis("off")
    fig.suptitle(f"Every variant at {depth} % depth: our cmd_clean model peaks 34 to 71 % too high on all nine; native fails the same way where its solver runs, dotted where it does not",
                 fontsize=12.5, fontweight="bold")
    save(fig, "variants_model_vs_si.png")


def variants_peak_law():
    cases, met = load_cross()
    fig, ax = plt.subplots(1, 2, figsize=(15, 6))
    for a, fam, vs in ((ax[0], "ex2", EX2 + ["ex2"]), (ax[1], "inv", INV + ["inv_chain"])):
        for v in vs:
            x, y = series(cases, met, v, "delay_cmd", "pad_peak_err_pct")
            a.plot(x, y, marker=MARK[v], color=FAMILY[fam], lw=2.0 if v in ("ex2_base", "inv_base8") else 1.4,
                   ms=7, alpha=0.95 if v in ("ex2_base", "inv_base8") else 0.75, label=f"ours: {DESC[v]}")
            xn, yn = series(cases, met, v, "native", "pad_peak_err_pct")
            if len(xn) >= 3:
                a.plot(xn, yn, marker=MARK[v], color=C_NAT, lw=1.2, ls=":", ms=5, label=f"native: {DESC[v]}")
        a.axhline(0, color="#111", lw=0.8)
        a.invert_xaxis()
        a.set_xlabel("depth (% of the full swing the transistor reached before the reversal)")
        a.set_ylabel("model pad peak minus transistor's (%)")
        a.set_title(f"{fam} family: one law, one slope per variant", fontweight="bold")
        a.grid(alpha=0.3)
        a.legend(fontsize=7.5, ncol=1)
    fig.suptitle("The stressed error grows with depth on every push-pull variant; native (dotted) tracks ours within a few percent where it survives",
                 fontsize=12.5, fontweight="bold")
    save(fig, "variants_peak_law.png")


def variants_what_changed():
    cases, met = load_cross()
    vs = EX2 + INV
    at50 = []
    slopes = []
    for v in vs:
        x, y = series(cases, met, v, "delay_cmd", "pad_peak_err_pct")
        at50.append(float(np.interp(50, x, y)))
        m = (x >= 50) & (x <= 90)
        slopes.append(-10 * np.polyfit(x[m], y[m], 1)[0])  # % per 10 % of depth lost
    col = {"reference": "#555555", "predriver": "#B03060", "output stage": "#2B6CA3", "both": "#8A6FB0"}
    fig, ax = plt.subplots(1, 1, figsize=(15, 6))
    xs = np.arange(len(vs))
    bars = ax.bar(xs, at50, color=[col[CHANGE[v]] for v in vs], edgecolor="white")
    for b, s, v in zip(bars, slopes, vs):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.2, f"{s:.1f} %/10 %", ha="center", fontsize=9, color="#333")
    ax.set_xticks(xs)
    short = {"ex2_base": "base\nas shipped", "ex2_slowpre": "slowpre\npredriver\nhalf width", "ex2_skewp": "skewp\noutput PMOS\nhalf width",
             "ex2_weak": "weak\noutput stage\nhalf width", "ex2_nomiller": "nomiller\ngate-drain\ncaps removed", "inv_base8": "base8\n8 stages",
             "inv_stage4": "stage4\n4 stages\nsame output", "inv_skewp": "skewp\nPMOS\nhalf width", "inv_weak": "weak\nhalf drive\nevery stage"}
    ax.set_xticklabels([short[v] for v in vs], fontsize=9)
    ax.set_ylabel("our pad peak excess at 50 % depth (%)")
    ax.axvline(4.5, color="#999", lw=1)
    ax.text(2, 78, "ex2 family (3.3 V, 3-stage predriver)", ha="center", fontsize=10, color="#666")
    ax.text(7, 78, "inv family (1.8 V, 8-stage predriver)", ha="center", fontsize=10, color="#666")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=col[k], label=k) for k in ("reference", "predriver", "output stage", "both")],
              title="what the variant changes", fontsize=9, loc="upper right")
    ax.set_ylim(0, 85)
    ax.grid(alpha=0.3, axis="y")
    ax.set_title("What was changed in the silicon, against how much the model's error moved (label: slope, % per 10 % of depth)",
                 fontweight="bold")
    fig.text(0.5, 0.012, "ex2: halving the output stage (weak, skewp) or removing the gate-drain caps barely moves the error; slowing the predriver (slowpre) cuts it by a third.\n"
             "inv: every change cuts it by a third to a half, the stage count (stage4) and the output devices alike, because on a 100 ps pulse the output stage's own speed also limits what the pad can follow.",
             ha="center", fontsize=9.5, color="#333")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT / "variants_what_changed.png", dpi=170)
    plt.close(fig)
    print("  wrote", OUT / "variants_what_changed.png")


def variants_entry():
    cases, met = load_cross()
    vs = EX2 + INV + ["io_buf"]
    fig, ax = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw=dict(width_ratios=[1.1, 1]))
    # left: Ku at the transistor's pad peak, transistor vs ours, at 50 % depth
    a = ax[0]
    si, ours, labels = [], [], []
    for v in vs:
        ks = [k for k in cases if k[0] == v and k[1] == 50] or [min((k for k in cases if k[0] == v), key=lambda k: abs(k[1] - 50))]
        k = ks[0]
        si.append(f(cases[k]["si_ku_at_tpk"]))
        ours.append(f(met[k]["delay_cmd"]["ku_at_tpk"]))
        labels.append(DESC[v].split(":")[0] if v != "io_buf" else "io_buf")
    xs = np.arange(len(vs))
    a.bar(xs - 0.2, si, 0.4, color=C_SI, label="transistor's Ku when its pad peaks")
    a.bar(xs + 0.2, ours, 0.4, color=C_ORIG, label="our Ku at that same instant")
    a.set_xticks(xs)
    a.set_xticklabels(labels, fontsize=9, rotation=20)
    a.set_ylabel("Ku (pull-up fraction on)")
    a.set_title("At ~50 % depth: the transistor's pull-up is 20 to 40 % on when its output turns; ours is fully on", fontweight="bold", fontsize=10.5)
    a.axvline(4.5, color="#999", lw=1)
    a.axvline(8.5, color="#999", lw=1)
    a.grid(alpha=0.3, axis="y")
    a.legend(fontsize=9)
    # right: entry excess vs peak excess, every case
    a = ax[1]
    allx, ally = [], []
    for v in vs + ["ex2", "inv_chain"]:
        _, y = series(cases, met, v, "delay_cmd", "pad_peak_err_pct")
        _, x = series(cases, met, v, "delay_cmd", "ku_entry_excess")
        a.scatter(x, y, marker=MARK[v], color=FAMILY[v[:3]], s=60 if v != "io_buf" else 150, label=v, edgecolor="white", lw=0.5)
        allx += list(x)
        ally += list(y)
    allx, ally = np.array(allx), np.array(ally)
    ok = ~np.isnan(allx) & ~np.isnan(ally)
    r = np.corrcoef(allx[ok], ally[ok])[0, 1]
    c = np.polyfit(allx[ok], ally[ok], 1)
    xx = np.linspace(-0.2, 1.1, 50)
    a.plot(xx, np.polyval(c, xx), color="#8A8A8A", lw=1.5, ls="--")
    a.axhline(0, color="#111", lw=0.8)
    a.axvline(0, color="#111", lw=0.8)
    a.set_xlabel("Ku entry excess: our Ku minus the transistor's, at the transistor's pad peak")
    a.set_ylabel("pad peak excess (%)")
    a.set_title(f"One mechanism on twelve buffers: r = {r:.2f} over {ok.sum()} cases", fontweight="bold", fontsize=10.5)
    a.grid(alpha=0.3)
    a.legend(fontsize=7, ncol=2)
    fig.suptitle("The deeper result: the model enters the reversal fully on because its command is a delay, and the peak error is that entry excess",
                 fontsize=12.5, fontweight="bold")
    save(fig, "variants_entry.png")


def variants_two_regimes():
    cases, met = load_cross()
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    offs = {"ex2_base": (8, -16), "ex2_nomiller": (8, 4), "ex2": (8, 6), "inv_chain": (8, 10), "inv_weak": (8, 0),
            "inv_skewp": (8, -9), "inv_base8": (8, -18), "inv_stage4": (8, -4), "ex2_skewp": (-70, -14), "ex2_weak": (8, -12),
            "ex2_slowpre": (8, 4), "io_buf": (-44, 12)}
    for v in EX2 + INV + ["ex2", "inv_chain", "io_buf"]:
        ks = sorted([k for k in cases if k[0] == v], key=lambda k: k[1])
        k = ks[0]
        x, y = f(cases[k]["tau_rise"]), f(cases[k]["tpk_after_rev_ps"])
        ax.scatter(x, y, marker=MARK[v], color=FAMILY[v[:3]], s=90 if v != "io_buf" else 220, edgecolor="white", lw=0.6)
        ax.annotate(v, (x, y), textcoords="offset points", xytext=offs.get(v, (6, 4)), fontsize=9)
    ax.set_xscale("log")
    ax.set_xlabel("our model's gate rise time constant, tau_rise (ps, log)")
    ax.set_ylabel("transistor pad peak after the input reversal (ps)")
    ax.set_title("Where each buffer's event sits: io_buf alone has a gate slower than its pulse, so it is caught part way\n"
                 "(the other eleven enter the reversal fully on, which is the regime the model fails in)", fontweight="bold", fontsize=11)
    ax.grid(alpha=0.3, which="both")
    save(fig, "variants_two_regimes.png")


if __name__ == "__main__":
    raise SystemExit(main())
