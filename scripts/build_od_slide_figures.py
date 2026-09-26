#!/usr/bin/env python3
"""Open-drain slides: full swing and stressed cases, transistor vs native vs our builds,
pad and Kd on the same axes. Drawn from existing runs:

    transistor, native   results/opendrain_gatestate_2026-09-10/base/w*/{transistor,native}
    ours, legacy build   results/opendrain_stress_2026-09-08/w*/ours          (before 2026-09-10)
    ours, gate-state     results/opendrain_gatestate_2026-09-10/base/w*/ours  (converter now)
    ours, chain          results/opendrain_chain_2026-09-10/base_c3_calib680_odprior/w*  (recipe)

    py -3.14 scripts/build_od_slide_figures.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import FixtureWaveform  # noqa: E402

R = ROOT / "results"
FIGS = R / "meeting_deck_2026-09-11" / "figures"
GS = R / "opendrain_gatestate_2026-09-10" / "base"
LEG = R / "opendrain_stress_2026-09-08"
CH = R / "opendrain_chain_2026-09-10" / "base_c3_calib680_odprior"
IBIS = R / "ex2_variants_2026-09-03/opendrain/ibis/ex2_opendrain.ibs"
SUP, R_PU = 3.3, 50.0
C_SI, C_NAT, C_LEG, C_GS, C_CH = "#111111", "#2B6CA3", "#C05621", "#7F8C8D", "#2E7D4F"


def wdir(w_ps):
    return f"w{w_ps}ps"


def transistor(w_ps):
    raw = sl.parse_hspice_tr0(GS / wdir(w_ps) / "transistor" / "run.tr0")
    return sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float)


def native(w_ps):
    raw = sl.parse_hspice_tr0(GS / wdir(w_ps) / "native" / "run.tr0")
    return sl.time_ns(raw), np.asarray(raw["v(pad)"], float), np.asarray(raw["v(kd)"], float)


def ngspice(d):
    raw = sl.parse_ngspice_raw(d / "run.raw")
    t = sl.time_ns(raw)
    try:
        kd = sl.signal(raw, "v(x1.kd)")
    except Exception:  # noqa: BLE001
        kd = np.full(len(t), np.nan)
    return t, sl.trace(raw, "out"), kd


def transistor_kd(data, t_ns, pad):
    time = np.arange(t_ns[0], t_ns[-1], 0.005) * 1e-9
    v = np.interp(time * 1e9, t_ns, pad)
    wave = FixtureWaveform(np.column_stack([time, v, v, v]), [SUP] * 3, R_PU)
    pu, pd, pc, gc, rf, cc, cf = pb.generating_current_data(data, time, 1, wave)
    num = gc + pc + rf - cc - cf
    return time * 1e9, np.where(np.abs(pd) > 1e-6, num / np.where(np.abs(pd) > 1e-6, pd, 1.0), np.nan)


def load_data(ccomp=3.0):
    txt = re.sub(r"^C_comp\s+.*$", f"C_comp {ccomp:.4f}pF {ccomp:.4f}pF {ccomp:.4f}pF", IBIS.read_text(errors="ignore"), count=1, flags=re.M)
    p = FIGS.parent / "od_ccomp3.ibs"
    p.write_text(txt, encoding="utf-8")
    return pb.DataModel(pb.get_ibis_model_ecdtools(str(p)), model_name="driver", component_name="MCM Driver 1")


def panel(ax_pad, ax_kd, w_ps, data, xlim, show_legend):
    t_si, si = transistor(w_ps)
    tk, kd_si = transistor_kd(data, t_si, si)
    t_n, nat, kd_n = native(w_ps)
    t_l, leg, kd_l = ngspice(LEG / wdir(w_ps) / "ours")
    t_g, gs, kd_g = ngspice(GS / wdir(w_ps) / "ours")
    t_c, ch, kd_c = ngspice(CH / wdir(w_ps))
    for a, series, ylab in ((ax_pad, ((t_si, si, C_SI, 3.0, "-", "transistor"), (t_n, nat, C_NAT, 1.6, "-", "native HSPICE IBIS"),
                                      (t_g, gs, C_GS, 1.6, "-", "ours, gate-state build (converter now)"),
                                      (t_c, ch, C_CH, 2.0, "--", "ours, chain + NMOS map + one pad point")), "pad (V)"),
                           (ax_kd, ((tk, kd_si, C_SI, 3.0, "-", "transistor Kd (solved, 3 pF)"), (t_n, kd_n, C_NAT, 1.6, "-", "native Kd"),
                                    (t_g, kd_g, C_GS, 1.6, "-", "gate-state Kd"), (t_c, kd_c, C_CH, 2.0, "--", "chain Kd")), "Kd (pull-down fraction on)")):
        for t, y, col, lw, ls, lab in series:
            m = (t > xlim[0]) & (t < xlim[1])
            a.plot(t[m] - 5.0, y[m], color=col, lw=lw, ls=ls, label=lab)
        a.axvline(0, color="#888", ls="--", lw=1)
        a.axvline(w_ps / 1e3, color="#888", ls="--", lw=1)
        a.grid(alpha=0.3)
        a.set_ylabel(ylab)
        if show_legend:
            a.legend(fontsize=7.5, loc="upper right" if a is ax_pad else "center right")
    ax_kd.set_ylim(-0.3, 1.4)
    ax_kd.set_xlabel("time from the pull-down edge (ns)")


def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    data = load_data(3.0)
    # 1. full swing
    fig, ax = plt.subplots(2, 1, figsize=(15, 8), sharex=True)
    panel(ax[0], ax[1], 10000, data, (4.5, 18.0), True)
    ax[0].set_title("Open-drain ex2, full swing: a 10 ns LOW input pulse into 50 Ω to VCC (2 pF). Dashed lines: input edges.", fontweight="bold")
    fig.suptitle("Open-drain at full swing: pad and Kd, transistor vs native vs our three builds", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "od_fullswing_10ns.png", dpi=160)
    plt.close(fig)
    # zoom of the two edges at full swing
    fig, axes = plt.subplots(2, 2, figsize=(16, 8), sharex="col")
    for c, (lo, hi, lab) in enumerate(((4.7, 7.5, "pull-down edge"), (14.7, 17.5, "release edge"))):
        panel(axes[0, c], axes[1, c], 10000, data, (lo, hi), c == 0)
        axes[0, c].set_title(f"full swing, {lab}", fontweight="bold")
    fig.suptitle("Open-drain full swing, the two edges zoomed: the legacy build rests in the wrong state and is ~120 ps late; the gate-state build fixes the rest state; the chain fixes the timing",
                 fontsize=11.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "od_fullswing_edges.png", dpi=160)
    plt.close(fig)
    # 2. stressed: four widths
    widths = (750, 700, 660, 620)
    fig, axes = plt.subplots(2, 4, figsize=(20, 8), sharex="col")
    for c, w in enumerate(widths):
        panel(axes[0, c], axes[1, c], w, data, (4.8, 5.0 + w / 1e3 + 2.4), c == 0)
        t_si, si = transistor(w)
        depth = (SUP - si[(t_si > 5) & (t_si < 9)].min()) / (SUP - 1.327) * 100
        axes[0, c].set_title(f"{w} ps LOW pulse, depth {depth:.0f} %", fontweight="bold")
        axes[1, c].set_ylim(-0.3, 1.4)
    fig.suptitle("Open-drain under stress: short LOW pulses. The transistor's Kd peak falls with depth (0.77 → 0.02); native stays at 1.0; the gate-state build follows partly; the chain follows to the calibration depth",
                 fontsize=11.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "od_stress.png", dpi=160)
    plt.close(fig)
    print("wrote", FIGS / "od_fullswing.png", FIGS / "od_fullswing_edges.png", FIGS / "od_stress.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
