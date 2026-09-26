#!/usr/bin/env python3
"""Track 1 vs track 2 on a stressed pulse train: do the builds that are right on one
pulse stay right when pulses arrive before the buffer has recovered?

Bench: 8 pulses at 50 % duty at the matrix's deepest width, 50 Ohm || 2 pF, and the
SAME 50 ps input edges the single-pulse matrix and the calibration used (the 2026-09-08
train reference used 1 ps edges, which on inv_chain's 1.4 V threshold changes the
effective width by 28 ps; the transistor is re-run here with 50 ps edges).

Scoring: per pulse, the transistor's peak and the model's peak inside a window that is
shifted by the buffer's own input-to-pad delay (measured on the transistor's first
pulse), so a pad response that lands after the input period (inv_chain: ~250 ps delay
on a 222 ps period) is still scored against its own pulse.

    py -3.14 scripts/track2_train_check.py
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
import gate_ramp_prototype as gp  # noqa: E402
import gate_chain_train_calib as tc  # noqa: E402
import pulse_train_accumulation as pt  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

R = ROOT / "results"
CH = R / "gate_chain_prototype_2026-09-10"
ST = R / "gate_step_prototype_2026-09-10"
OUT = R / "track2_train_check_2026-09-13"
EDGE_PS = 50.0

BUILDS = [
    ("ex2", "track 1: file chain + prior map + pad point", CH / "ex2_c1.7/ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810/driver_chain.sub"),
    ("ex2", "track 2: file chain + measured map + pad point", CH / "ex2_c1.7/ibis_silicon_K3_xlin0.45_calibpad810/driver_chain.sub"),
    ("inv_chain", "track 1: file chain + prior map + pad point", CH / "inv_chain_c0.6/ibis_prior_K7_prior0.49_0.6_calibpad104/driver_chain.sub"),
    ("inv_chain", "track 2: file chain + measured map + pad point", CH / "inv_chain_c0.6/ibis_silicon_K7_calibpad104/driver_chain.sub"),
    ("inv_chain", "track 2, square-law stage (p = 2)", CH / "inv_chain_c0.6/ibis_silicon_K7_calibpad104_p2/driver_chain.sub"),
    ("inv_chain", "track 2, chain fitted to the real gate (truth-bounded)", CH / "inv_chain_c0.6/real_silicon_K7/driver_chain.sub"),
    ("inv_chain", "track 2, chain fitted to the real gate, gate-calibrated", CH / "inv_chain_c0.6/real_silicon_K7_calib104/driver_chain.sub"),
    ("inv_chain", "plain law, fitted to the real gate + pad point", CH / "inv_chain_c0.6/real_silicon_K7_calibpad104/driver_chain.sub"),
    ("inv_chain", "square-root law, fitted to the real gate", CH / "inv_chain_c0.6/real_silicon_K7_p0.5/driver_chain.sub"),
    ("inv_chain", "square-root law, fitted to the real gate + pad point", CH / "inv_chain_c0.6/real_silicon_K7_calibpad104_p0.5/driver_chain.sub"),
    ("inv_chain", "square-root law, from the tables + pad point", CH / "inv_chain_c0.6/ibis_silicon_K7_calibpad104_p0.5/driver_chain.sub"),
    ("inv_chain", "square-root law, tables + tail pinned at 0.41 + pad point", CH / "inv_chain_c0.6/ibis_silicon_K7_xlin0.41_calibpad104_p0.5/driver_chain.sub"),
    ("ex2", "track 2, square-law stage (p = 2)", CH / "ex2_c1.7/ibis_silicon_K3_calibpad810_p2/driver_chain.sub"),
    ("ex2", "chain fitted to the real last stage + pad point", CH / "ex2_c1.7/real_silicon_K3_calibpad810/driver_chain.sub"),
    ("ex2", "chain fitted to the real last stage, joint with the stressed gate, + pad point", CH / "ex2_c1.7/real_silicon_K3_calibpad810_joint810/driver_chain.sub"),
    # 2026-09-17: the measured map with its ends anchored (settled level +19.0 -> +2.2 mV on
    # ex2, +13.6 -> -1.2 on inv_chain). Trains were never run on these, so the walkthrough
    # could not carry an honest row for them.
    ("ex2", "real last stage + pad point, map ends anchored", CH / "ex2_c1.7/real_silicon_K3_calibpad810_anch/driver_chain.sub"),
    ("ex2", "real last stage + pad point, pull-down end only", CH / "ex2_c1.7/real_silicon_K3_calibpad810_anchoff/driver_chain.sub"),
    ("inv_chain", "real last stage + pad point, map ends anchored", CH / "inv_chain_c0.6/real_silicon_K7_calibpad104_anch/driver_chain.sub"),
    ("inv_chain", "real last stage + pad point, pull-down end only", CH / "inv_chain_c0.6/real_silicon_K7_calibpad104_anchoff/driver_chain.sub"),
    ("io_buf", "track 1: file step response + pad point", ST / "io_buf/ibis_prior_calibpad1505/driver_step.sub"),
    ("io_buf", "track 2: measured step response + pad point", ST / "io_buf/real_prior_calibpad1505/driver_step.sub"),
    ("io_buf", "track 2, 3-slot: last 3 edges superposed", ST / "io_buf/real_prior_calibpad1505_slots3/driver_step.sub"),
]
COLORS = {"track 1": ("#C05621", "-"), "track 2": ("#2E7D4F", "--"), "track 2, 3": ("#2B6CA3", "-.")}


def transistor_train(dev, sup, width, n):
    """Transistor train with 50 ps edges (the 2026-09-08 reference used 1 ps)."""
    d = OUT / dev / "transistor_edge50"
    d.mkdir(parents=True, exist_ok=True)
    src = tc.TRAIN_REF / dev / "stressed/transistor"
    for f in src.iterdir():
        if f.is_file() and not f.name.startswith("run."):
            (d / f.name).write_bytes(f.read_bytes())
    deck = (src / "run.sp").read_text(encoding="utf-8", errors="replace")
    pwl = sl.pulse(0.0, sup, pt.edges(width, n), edge_ps=EDGE_PS, stop_ns=pt.stop_ns(width, n))
    deck = re.sub(r"Vin in_dig 0 PWL\(.*?\)", f"Vin in_dig 0 {pwl}", deck, flags=re.S)
    (d / "run.sp").write_text(deck, encoding="utf-8")
    if not (d / "run.tr0").exists():
        rc = base.run_process([str(default_hspice()), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 1800)
        if rc != 0:
            raise RuntimeError(f"hspice failed: {d}")
    raw = sl.parse_hspice_tr0(d / "run.tr0")
    return sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float)


def per_pulse(t_si, si, t_m, m, width, n):
    """(peak shift ps, peak error mV, transistor peak V) per pulse, windows shifted by the
    transistor's own delay so that pulse k's pad response is scored against pulse k."""
    g0 = np.arange(5.0, 5.0 + 4 * width, 0.002)
    a0 = np.interp(g0, t_si, si)
    # the FIRST pulse's peak (pulse 2 is taller, so a plain argmax would pick it): the first
    # sample above 30 % of the train's maximum, then the maximum within the next 1.5 W
    i0 = int(np.argmax(a0 > 0.3 * a0.max()))
    m0 = (g0 >= g0[i0]) & (g0 <= g0[i0] + 1.5 * width)
    t_pk1 = float(g0[m0][int(np.argmax(a0[m0]))])
    # window k = [peak_k - W, peak_k + W): centred on where pulse k's pad peak is expected, so
    # it never reaches into the next pulse's rising flank
    d0 = max(0.0, t_pk1 - 5.0 - width)
    rows = []
    for k in range(n):
        lo, hi = 5.0 + 2 * width * k + d0, 5.0 + 2 * width * (k + 1) + d0
        g = np.arange(lo, hi, 0.002)
        a, b = np.interp(g, t_si, si), np.interp(g, t_m, m)
        ia, ib = int(np.argmax(a)), int(np.argmax(b))
        rows.append(((g[ib] - g[ia]) * 1e3, (b[ib] - a[ia]) * 1e3, a[ia]))
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    n = pt.N_PULSES
    print(f"{'buffer':<10} {'build':<48} {'W ps':>6} | {'pulse 1':>8} {'settled':>8} {'shift':>6}   (peak error vs the transistor; settled = pulses 4-8; shift = peak time, ps)")
    rows = []
    fig, axes = plt.subplots(3, 1, figsize=(16, 10))
    axmap = {"ex2": axes[0], "inv_chain": axes[1], "io_buf": axes[2]}
    done = set()
    for dev, label, sub in BUILDS:
        if not sub.exists():
            print(f"{dev:<10} {label:<48}   (no build yet: {sub.parent.name})")
            continue
        _, sup, width = pt.DEV[dev]
        gp.VARIANT_NAME = dev
        gp.EDGE_PS[dev] = EDGE_PS
        t_si, si = transistor_train(dev, sup, width, n)
        d = OUT / dev / sub.parent.name
        t_m, m = tc.run_train(d, sub.read_text(encoding="utf-8"), sup, width, n)
        pp = per_pulse(t_si, si, t_m, m, width, n)
        p1 = 100 * pp[0][1] / 1e3 / pp[0][2]
        settled = 100 * float(np.mean([r[1] for r in pp[3:]])) / 1e3 / float(np.mean([r[2] for r in pp[3:]]))
        shift = float(np.mean([r[0] for r in pp[3:]]))
        print(f"{dev:<10} {label:<48} {width*1e3:>6.0f} | {p1:>+7.1f}% {settled:>+7.1f}% {shift:>+5.0f}")
        rows.append((dev, label, width, p1, settled, shift))
        a = axmap[dev]
        if dev not in done:
            a.plot(t_si, si, color="#111", lw=2.6, label="transistor (50 ps edges)")
            a.set_title(f"{dev}, 8 pulses of {width*1e3:.0f} ps at 50 % duty", fontweight="bold")
            a.set_xlim(4.5, 5 + 16 * width + 2)
            a.grid(alpha=0.3)
            a.set_ylabel("pad (V)")
            done.add(dev)
        col, ls = COLORS["track 2, 3"] if (label.startswith("track 2, 3") or "square" in label or "truth" in label or "gate-calibrated" in label or "root" in label or "real last stage" in label or "plain law" in label) else COLORS[label[:7]]
        a.plot(t_m, m, color=col, lw=1.5, ls=ls, label=label)
    for a in axes:
        a.legend(fontsize=8, loc="upper right")
    axes[-1].set_xlabel("time (ns)")
    fig.tight_layout()
    fig.savefig(OUT / "trains.png", dpi=140)
    with (OUT / "summary.csv").open("w", encoding="utf-8") as fh:
        fh.write("device,build,width_ns,pulse1_pk_pct,settled_pk_pct,settled_peak_shift_ps\n")
        for r in rows:
            fh.write(",".join(str(x) for x in r) + "\n")
    print("wrote", OUT / "summary.csv", OUT / "trains.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
