#!/usr/bin/env python3
"""Real gate in, and the Ku/Kd maps taken from the transistor instead of the IBIS tables.

`gate_replay_prototype.py` feeds the model the transistor's real gate and keeps
the maps the shipped model implies: Ku(g) is "the IBIS Ku(t) at the moment the
real full-swing gate passed g". On inv_chain that under-drives the stressed pad
by up to 54 %, although Ku is a single-valued function of the gate within every
stressed event (loop <= 0.1). So either the map's shape is wrong, or the output
stage is not a static map. This decides it.

The map is now the transistor's own two-fixture Ku(t)/Kd(t) plotted against its
own gate, either

    --source full     at full swing (two new fixture runs, rise 5 ns, fall 15 ns)
    --source stress   inside the middle stressed event (the matrix fixture runs)

and the stressed widths are replayed as before. If the silicon map reproduces
the stressed pad, the output stage IS a static map of the gate and the IBIS
tables place Ku wrongly against the gate for a fast gate. The map values are
printed side by side so the difference can be read directly.

    py -3.14 scripts/silicon_map_replay.py --variant inv_chain --ccomp 0.6 --source full
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from extract_silicon_kukd import run_fixture, solve_silicon_kukd  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_cascade_prototype as gc  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402

R = ROOT / "results"
G = R / "gate_cascade_prototype_2026-09-09"
FIX = R / "stress_method_matrix_2026-08-20/delay_cmd/hspice_fixtures"
FSFIX = R / "full_swing_fixtures_2026-09-09"
LOOP_CC = {"ex2": 1.75, "inv_chain": 0.6, "io_buf": None}
GRID = np.linspace(0.0, 1.0, 200)


def fixture(p: Path) -> np.ndarray:
    raw = psp.parse_tr0(p)
    t = np.asarray(raw["time"], float)
    v = np.asarray(raw[next(k for k in raw if "pad" in k)], float)
    return np.column_stack([t, v, v, v])


def branch(g, k, mask):
    x, y = g[mask], k[mask]
    o = np.argsort(x)
    x, y = x[o], y[o]
    ux, idx = np.unique(np.round(x, 5), return_inverse=True)
    uy = np.bincount(idx, y) / np.bincount(idx)
    return GRID, np.interp(GRID, ux, uy)


def silicon_maps(ts, ku, kd, tg, g, t_on, t_off, gd=None):
    """(ku_rise, ku_fall, kd_on, kd_off) against the gate; kd against gd = 1-g by default."""
    gg = np.interp(ts, tg, g)
    gdd = 1.0 - gg if gd is None else np.interp(ts, tg, gd)
    win = (ts >= t_on - 0.05) & (ts <= t_off + 3.0)
    ipk = int(np.argmax(np.where(win, gg, -9)))
    up = (ts >= t_on - 0.05) & (ts <= ts[ipk])
    dn = (ts >= ts[ipk]) & (ts <= t_off + 3.0)
    ku_rise, ku_fall = branch(gg, ku, up), branch(gg, ku, dn)
    # pull-down: GDN falls on the input rise (KDGATE_OFF), rises on the input fall (KDGATE_ON)
    ipk_d = int(np.argmin(np.where(win, gdd, 9)))
    kd_off = branch(gdd, kd, (ts >= t_on - 0.05) & (ts <= ts[ipk_d]))
    kd_on = branch(gdd, kd, (ts >= ts[ipk_d]) & (ts <= t_off + 3.0))
    return ku_rise, ku_fall, kd_on, kd_off


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="inv_chain")
    ap.add_argument("--ccomp", type=float, default=None, help="C_comp (pF) for both the model and the silicon solve; default: loop value")
    ap.add_argument("--source", choices=("full", "stress"), default="full")
    args = ap.parse_args()
    dev = args.variant
    cc = args.ccomp if args.ccomp is not None else LOOP_CC[dev]
    sup, ibis = gp.VARIANTS[dev]
    gp.VARIANT_NAME = dev
    OUT = G / (dev + (f"_c{cc:g}" if cc else ""))
    assert (OUT / "shipped/driver.sub").exists(), f"run gate_replay_prototype.py --variant {dev}" + (f" --ccomp {cc}" if cc else "") + " first"
    ship = (OUT / "shipped/driver.sub").read_text(encoding="utf-8")
    tag = OUT / f"gate_replay_silicon_{args.source}"
    tag.mkdir(parents=True, exist_ok=True)
    node_u, node_d = gr.GATES[dev]
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    if cc:
        data.c_comp = [cc * 1e-12] * 3
    cs = gp.cases(dev)
    refs = {d_: gp.tr0_pad(d / "run.tr0") for d_, _, d in cs}
    hspice = Path(default_hspice())

    # --- the silicon coefficients and the real gate for the map source --------
    if args.source == "full":
        device = next(x for x in base.DEVICES if x.device_id == dev)
        case = base.PulseCase("e50p_long_control", 0.050, "rise_fall", 10.0, 22.0)
        lo = run_fixture(device, case, 0.0, FSFIX / dev / "vfix_0", hspice, 1800)
        hi = run_fixture(device, case, sup, FSFIX / dev / "vfix_vcc", hspice, 1800)
        tg, g = gr.real_gate(dev, 0, node_u)
        gd = None if node_d is None else 1.0 - gr.real_gate(dev, 0, node_d)[1]
        t_on, t_off = 5.0, 15.0
    else:
        depth, w, _ = cs[len(cs) // 2]
        fxd = FIX / dev / f"short_high_w{depth}ps"
        lo, hi = fixture(fxd / "vfix_0/run.tr0"), fixture(fxd / "vfix_vcc/run.tr0")
        tg, g = gr.real_gate(dev, depth, node_u)
        gd = None if node_d is None else 1.0 - gr.real_gate(dev, depth, node_d)[1]
        t_on, t_off = 5.0, 5.0 + w
    s = solve_silicon_kukd(data, lo, hi, sup, uniform_ps=5.0)
    ts, ku, kd = s[:, 0] * 1e9, s[:, 1], s[:, 2]
    ku_rise, ku_fall, kd_on, kd_off = silicon_maps(ts, ku, kd, tg, g, t_on, t_off, gd)

    # --- the IBIS-implied maps, for comparison ---------------------------------
    full_ship = gp.run_ours(OUT / "shipped/full", ship, sup, 10.0)
    replay_full = OUT / "gate_replay/full_pass1"
    text_ibis = (OUT / "gate_replay/driver_replay_full.sub").read_text(encoding="utf-8")
    full_new = gp.run_ours(replay_full, gr.patch_replay(ship, *gr.real_gate(dev, 0, node_u),
                                                       *((None, None) if node_d is None else (gr.real_gate(dev, 0, node_d)[0], 1.0 - gr.real_gate(dev, 0, node_d)[1]))), sup, 10.0)
    ib_rise, ib_fall = gc.derive_maps(full_new, full_ship)
    print(f"\n  {dev}: Ku map against the real gate, C_comp {cc} pF, silicon source = {args.source}")
    print(f"    {'g':>6}{'IBIS rise':>11}{'Si rise':>9}{'IBIS fall':>11}{'Si fall':>9}")
    for gv in (0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        print(f"    {gv:>6.1f}{np.interp(gv, *ib_rise):>11.3f}{np.interp(gv, *ku_rise):>9.3f}"
              f"{np.interp(gv, *ib_fall):>11.3f}{np.interp(gv, *ku_fall):>9.3f}")

    # --- build with the silicon maps and score -------------------------------
    text_full = gc.patch_kd_maps(gc.patch_maps(text_ibis, ku_rise, ku_fall), kd_on, kd_off)
    (tag / "driver_silicon_full.sub").write_text(text_full, encoding="utf-8")
    fs = gp.run_ours(tag / "full", text_full, sup, 10.0)
    # full-swing pad against the transistor's full-swing pad (the stage-probe run)
    fraw = psp.parse_tr0(psp.OUT / dev / "full/run.tr0")
    tfull, pfull = np.asarray(fraw["time"], float) * 1e9, np.asarray(fraw["v(pad_sp)"], float)
    grid = np.arange(4.5, 20.0, 0.005)
    rms_full = float(np.sqrt(np.mean((np.interp(grid, fs["t"], fs["pad"]) - np.interp(grid, tfull, pfull)) ** 2)))
    fs_ib = gp.run_ours(OUT / "gate_replay/full", text_ibis, sup, 10.0)
    rms_full_ib = float(np.sqrt(np.mean((np.interp(grid, fs_ib["t"], fs_ib["pad"]) - np.interp(grid, tfull, pfull)) ** 2)))
    print(f"\n    full-swing pad rms vs transistor: IBIS maps {rms_full_ib*1e3:.1f} mV, silicon maps {rms_full*1e3:.1f} mV")
    print(f"    {'build':<24} | " + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs) + " | " + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs))
    rows = []
    fig, axes = plt.subplots(2, len(cs), figsize=(4.0 * len(cs), 7.0), sharex="col")
    for label in ("gate_replay", f"gate_replay_silicon_{args.source}"):
        pks, lags = [], []
        for col, (depth, w, d) in enumerate(cs):
            tw, gw = gr.real_gate(dev, depth, node_u)
            twd, gwd = (None, None) if node_d is None else (gr.real_gate(dev, depth, node_d)[0], 1.0 - gr.real_gate(dev, depth, node_d)[1])
            base_text = gr.patch_replay(ship, tw, gw, twd, gwd)
            if label == "gate_replay":
                text = gc.patch_kd_maps(gc.patch_maps(base_text, ib_rise, ib_fall), *gr.sg.derive_kd_maps(full_new, full_ship))
                r = gp.run_ours(OUT / "gate_replay" / f"d{depth}", text, sup, w)
            else:
                text = gc.patch_kd_maps(gc.patch_maps(base_text, ku_rise, ku_fall), kd_on, kd_off)
                r = gp.run_ours(tag / f"d{depth}", text, sup, w)
            pk, lag, _, _ = gp.score(*refs[depth], r["t"], r["pad"], w)
            pks.append(pk)
            lags.append(lag)
            rev = gp.RISE_NS + w
            gg = np.arange(rev - 0.3, rev + 1.5, 0.002)
            a, b = axes[0][col], axes[1][col]
            if label == "gate_replay":
                a.plot(gg - rev, np.interp(gg, tw, gw), color="#111111", lw=3.0, label="real gate (replayed)")
                a.plot(gg - rev, np.interp(gg, r["t"], r["ku"]), color="#C05621", lw=1.4, ls=":", label="Ku, IBIS-implied map")
                b.plot(gg - rev, np.interp(gg, *refs[depth]), color="#111111", lw=3.0, label="transistor pad")
                b.plot(gg - rev, np.interp(gg, r["t"], r["pad"]), color="#C05621", lw=1.4, ls=":", label=f"IBIS map ({pk:+.0f}%)")
            else:
                a.plot(gg - rev, np.interp(gg, r["t"], r["ku"]), color="#B03060", lw=1.8, label="Ku, silicon map")
                a.plot(gg - rev, np.interp(gg, r["t"], r["kd"]), color="#2B6CA3", lw=1.2, label="Kd, silicon map")
                b.plot(gg - rev, np.interp(gg, r["t"], r["pad"]), color="#2E8B57", lw=2.0, ls="--", label=f"silicon map ({pk:+.0f}%)")
                a.set_title(f"W = {depth} ps", fontweight="bold")
                a.set_ylim(-0.2, 1.2)
                a.grid(alpha=0.3)
                b.grid(alpha=0.3)
                b.set_xlabel("time from the reversal (ns)")
                if col == 0:
                    a.legend(fontsize=7)
                    b.legend(fontsize=7)
                    a.set_ylabel("gate / coefficients")
                    b.set_ylabel("pad (V)")
        rows.append(dict(build=label, **{f"pk_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, pks)},
                         **{f"lag_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, lags)}))
        print(f"    {label:<24} | " + "".join(f"{v:>9.1f}" for v in pks) + " | " + "".join(f"{v:>9.0f}" for v in lags))
    fig.suptitle(f"{dev}: real gate replayed, Ku/Kd maps from the transistor ({args.source}) vs implied by the IBIS tables",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(tag / "silicon_map_replay.png", dpi=150)
    plt.close(fig)
    # the maps themselves
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    ax[0].plot(*ib_rise, color="#C05621", ls=":", lw=2, label="IBIS-implied, gate rising")
    ax[0].plot(*ib_fall, color="#C05621", lw=2, label="IBIS-implied, gate falling")
    ax[0].plot(*ku_rise, color="#B03060", ls=":", lw=2, label=f"silicon ({args.source}), gate rising")
    ax[0].plot(*ku_fall, color="#B03060", lw=2, label=f"silicon ({args.source}), gate falling")
    ax[0].set_xlabel("gate, 0 = off, 1 = fully on")
    ax[0].set_ylabel("Ku")
    ax[0].set_title(f"{dev}: the Ku map", fontweight="bold")
    ax[0].grid(alpha=0.3)
    ax[0].legend(fontsize=8)
    ax[1].plot(*kd_off, color="#2B6CA3", ls=":", lw=2, label="silicon, GDN falling (pull-down turning off)")
    ax[1].plot(*kd_on, color="#2B6CA3", lw=2, label="silicon, GDN rising")
    ax[1].set_xlabel("GDN, 0 = off, 1 = fully on")
    ax[1].set_ylabel("Kd")
    ax[1].set_title(f"{dev}: the Kd map", fontweight="bold")
    ax[1].grid(alpha=0.3)
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(tag / "maps.png", dpi=150)
    plt.close(fig)
    with (tag / "sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wri.writeheader()
        wri.writerows(rows)
    print(f"  figures: {tag / 'silicon_map_replay.png'}, {tag / 'maps.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
