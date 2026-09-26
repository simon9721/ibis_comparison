#!/usr/bin/env python3
"""The open-drain ex2 under stress: does it follow the push-pull buffers or not?

Every stressed buffer so far is push-pull. The open-drain has no pullup: it can
only pull the pad low, and releases it to a 50 ohm termination to VCC. Its IBIS
has one waveform per edge (there is no 0 V fixture a released pad can rise into),
so native runs the single-waveform path and the coefficient solve has one unknown,
Kd, from one fixture -- which is the bench itself. That makes the transistor's Kd
directly measurable from the bench run:

    Kd(t) = (I_gc + I_pc + I_fixture - C_comp dV/dt) / I_pd(V)

The stressed event is a short LOW input pulse: the buffer pulls the pad down for
W and releases it before it settles. Depth is the low excursion reached as a
fraction of the settled low level from a 10 ns control.

Three builds see the same bench (50 ohm to VCC, 2 pF): transistor (HSPICE, n4
probed), native (HSPICE), ours (`InputDrivenTwoStateGateDelayCommandFull`, ngspice).

    py -3.14 scripts/opendrain_stress_cases.py
"""
from __future__ import annotations

import csv
import re
import shutil
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
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from extract_silicon_kukd import FixtureWaveform  # noqa: E402
from pedestal_localization import best_lag  # noqa: E402

import argparse  # noqa: E402

R = ROOT / "results"
# Defaults are the base open-drain; the od_weak / od_slowpre variants pass their
# own IBIS (the selector's probe output) and inputs dir. Same bench, same widths.
_ap = argparse.ArgumentParser()
_ap.add_argument("--ibis", type=Path, default=R / "ex2_variants_2026-09-03/opendrain/ibis/ex2_opendrain.ibs")
_ap.add_argument("--inputs", type=Path, default=R / "ex2_variants_2026-09-03/opendrain/inputs")
_ap.add_argument("--out", type=Path, default=R / "opendrain_stress_2026-09-08")
# The first width is the 10 ns control; the rest straddle the pull-down onset,
# which sits at ~0.65 ns on the base OD and od_weak and ~0.8 ns on od_slowpre
# (its predriver is slower). Pass --widths to move the grid for a new variant.
_ap.add_argument("--widths", type=float, nargs="+",
                 default=[10.0, 0.75, 0.72, 0.70, 0.68, 0.66, 0.64, 0.62])
_ARGS = _ap.parse_args()
IBIS, OUT = _ARGS.ibis, _ARGS.out


class _Var:  # keeps the `VAR / "inputs"` spelling used below
    inputs = _ARGS.inputs

    def __truediv__(self, name):
        assert name == "inputs"
        return self.inputs


VAR = _Var()
SUP, R_PU, C_LOAD_PF = 3.3, 50.0, 2.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
STOP = 22.0
WIDTHS = tuple(_ARGS.widths)


def pwl(width: float) -> str:
    # rest high, pull low at 5 ns for `width`, release
    return sl.pulse(0.0, SUP, [5.0, 5.0 + width], start_high=True, stop_ns=STOP)


def run_hspice(d: Path, deck: str, hspice: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "run.sp").write_text(deck, encoding="utf-8")
    tr0, lis = d / "run.tr0", d / "run.lis"
    ok = tr0.exists() and lis.exists() and "job concluded" in lis.read_text(errors="replace").lower()
    if not ok:
        rc = base.run_process([str(hspice), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 1800)
        if rc != 0 or not tr0.exists():
            raise RuntimeError(f"hspice failed: {d}")
    return tr0


def transistor(width: float, hspice: Path):
    d = OUT / f"w{width*1e3:.0f}ps" / "transistor"
    d.mkdir(parents=True, exist_ok=True)
    for f in (VAR / "inputs").iterdir():
        shutil.copy2(f, d / f.name)
    deck = f"""* ex2 open-drain transistor, pull-up bench, W={width} ns
.title od transistor
.option post=2 probe accurate ingold=2
.temp 27
Vdd vdd 0 DC {SUP}
Vin in_dig 0 {pwl(width)}
.include 'hspice.mod'
.subckt ex2_buffer in out vdd gnd
.include 'buffer.sp'
.ends ex2_buffer
XREF in_dig pad_sp vdd 0 ex2_buffer
Rpu pad_sp vdd {R_PU}
Cload pad_sp 0 {C_LOAD_PF}p
.probe tran V(in_dig) V(pad_sp) V(xref.n4)
.tran 0.002n {STOP}n
.end
"""
    raw = sl.parse_hspice_tr0(run_hspice(d, deck, hspice))
    return sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float), np.asarray(raw["v(xref.n4)"], float)


def native(width: float, hspice: Path):
    d = OUT / f"w{width*1e3:.0f}ps" / "native"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(IBIS, d / "input.ibs")
    deck = f"""* ex2 open-drain native IBIS, pull-up bench
.title od native
.option post=2 probe accurate ingold=2
.temp 27
Vdd vdd 0 DC {SUP}
Vin in_dig 0 {pwl(width)}
VPU pu_ref 0 DC {SUP}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUP}
VGC gc_ref 0 DC 0
* Open-drain: the B-element still takes the standard output-buffer node order
* (buffer=2); pu_ref is simply unused by a pulldown-only model.
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='input.ibs' model='driver' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pd=kd
Rpu pad vdd {R_PU}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad) V(kd)
.tran 0.002n {STOP}n
.end
"""
    raw = sl.parse_hspice_tr0(run_hspice(d, deck, hspice))
    kd = np.asarray(raw["v(kd)"], float) if "v(kd)" in raw else np.full(len(raw["time"]), np.nan)
    return sl.time_ns(raw), np.asarray(raw["v(pad)"], float), kd


def ours(width: float, data):
    d = OUT / f"w{width*1e3:.0f}ps" / "ours"
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "driver.sub").exists():
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical", str(d / "driver.sub"))
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    (d / "run.sp").write_text(
        dk.ngspice_header() + ".include driver.sub\n" + dk.supply("VCC", SUP, name="Vdd")
        + f"Vin IN 0 {pwl(width)}\n" + dk.supply("EN", sub.enable_level(SUP), name="Ven")
        + sub.instance("X1") + f"Rpu OUT VCC {R_PU}\nCload OUT 0 {C_LOAD_PF}p\n"
        + f".tran 0.002n {STOP}n\n.save V(OUT) V(X1.kd)\n.end\n", encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1800) is None:
            raise RuntimeError(f"ngspice failed: {d}")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    try:
        kd = sl.signal(raw, "v(x1.kd)")
    except Exception:                                   # noqa: BLE001
        kd = np.full(len(sl.time_ns(raw)), np.nan)
    return sl.time_ns(raw), sl.trace(raw, "out"), kd


def transistor_kd(data, t_ns, pad):
    """Single-fixture Kd from the bench run itself (the bench is the OD fixture)."""
    time = np.arange(t_ns[0], t_ns[-1], 0.005) * 1e-9
    v = np.interp(time * 1e9, t_ns, pad)
    wave = FixtureWaveform(np.column_stack([time, v, v, v]), [SUP] * 3, R_PU)
    pu, pd, pc, gc, rf, cc, cf = pb.generating_current_data(data, time, 1, wave)
    num = gc + pc + rf - cc - cf
    kd = np.where(np.abs(pd) > 1e-6, num / np.where(np.abs(pd) > 1e-6, pd, 1.0), np.nan)
    return time * 1e9, kd


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    hspice = Path(default_hspice())
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)), model_name="driver",
                        component_name="MCM Driver 1")
    rows = []
    settled_low = None
    fig, axes = plt.subplots(2, 4, figsize=(20, 9))
    for i, W in enumerate(WIDTHS):
        print(f"  W = {W} ns ...")
        t_si, si, n4 = transistor(W, hspice)
        t_n, nat, nat_kd = native(W, hspice)
        t_o, our, our_kd = ours(W, data)
        tk, si_kd = transistor_kd(data, t_si, si)
        g = np.arange(4.5, min(5.0 + 2 * W + 3.0, STOP - 0.1), 0.002)
        a_si, a_n, a_o = np.interp(g, t_si, si), np.interp(g, t_n, nat), np.interp(g, t_o, our)
        imin = int(np.argmin(a_si))
        if W == WIDTHS[0]:
            settled_low = float(np.interp(14.5, t_si, si))
        depth = (SUP - a_si[imin]) / (SUP - settled_low) if settled_low is not None else np.nan
        lo, hi = 5.0, min(5.0 + 2 * W + 2.0, STOP - 0.1)
        lag_n, res_n = best_lag(g, a_si, a_n, lo, hi, max_lag_ns=0.5)
        lag_o, res_o = best_lag(g, a_si, a_o, lo, hi, max_lag_ns=0.5)
        tmin = g[imin]
        kd_si_min_t = float(np.interp(tmin, tk, np.nan_to_num(si_kd)))
        rows.append(dict(width_ns=W, depth_pct=round(100 * depth, 1), si_low_V=round(a_si[imin], 4),
                         t_min_after_rev_ps=round((tmin - (5.0 + W)) * 1e3, 1),
                         nat_low_err_mV=round((a_n.min() - a_si[imin]) * 1e3, 1),
                         our_low_err_mV=round((a_o.min() - a_si[imin]) * 1e3, 1),
                         nat_lag_ps=round(lag_n, 1), nat_res=round(res_n, 3),
                         our_lag_ps=round(lag_o, 1), our_res=round(res_o, 3),
                         si_kd_at_min=round(kd_si_min_t, 3),
                         nat_kd_at_min=round(float(np.interp(tmin, t_n, np.nan_to_num(nat_kd))), 3),
                         our_kd_at_min=round(float(np.interp(tmin, t_o, np.nan_to_num(our_kd))), 3),
                         n4_at_min=round(float(np.interp(tmin, t_si, n4)), 3),
                         n4_excursion=round(float(n4.max() - n4.min()), 3)))
        print(f"    depth {100*depth:5.1f}%  low {a_si[imin]:.3f} V  our low err {rows[-1]['our_low_err_mV']:+.0f} mV"
              f"  nat {rows[-1]['nat_low_err_mV']:+.0f}  lag ours {lag_o:+.0f} nat {lag_n:+.0f}"
              f"  Kd@min si {kd_si_min_t:.2f} ours {rows[-1]['our_kd_at_min']:.2f} nat {rows[-1]['nat_kd_at_min']:.2f}")
        a = axes.ravel()[i]
        m = (g > 4.8) & (g < min(5.0 + W + 2.5, STOP - 0.1))
        a.plot(g[m] - 5.0, a_si[m], color="#111111", lw=3.0, label="transistor")
        a.plot(g[m] - 5.0, a_n[m], color="#2B6CA3", lw=1.8, label="native")
        a.plot(g[m] - 5.0, a_o[m], color="#C05621", lw=1.8, ls="--", label="ours")
        a.set_title(f"W = {W*1e3:.0f} ps, depth {100*depth:.0f}%", fontsize=11, fontweight="bold")
        a.set_xlabel("time from pull-down (ns)")
        a.grid(alpha=0.3)
        if i == 0:
            a.legend(fontsize=8)
            a.set_ylabel("pad (V)")
    fig.suptitle("Open-drain ex2 under stress: short low pulses into a 50 ohm pull-up", fontsize=15,
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "opendrain_stress.png", dpi=160)
    plt.close(fig)
    with (OUT / "cases.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {OUT / 'cases.csv'} and {OUT / 'opendrain_stress.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
