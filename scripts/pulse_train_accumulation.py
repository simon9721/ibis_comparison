#!/usr/bin/env python3
"""Does the timing error accumulate over a train of stressed pulses?

Every stressed case so far is one pulse from a settled state. If the defect is
state carry-over -- each event starting from where the previous one left the
device -- then a train of pulses at 50% duty, where the pad never settles, should
show the error growing (or not) pulse by pulse. One pulse cannot show that.

Three base buffers, transistor / native / ours, at one stressed width each and a
full-swing control train. Per pulse k: the pad peak time of each model minus the
transistor's, and the best-fit lag of each model onto the transistor over that
pulse's own window. Plotted against k.

    py -3.14 scripts/pulse_train_accumulation.py
"""
from __future__ import annotations

import csv
import re
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
from pedestal_localization import best_lag  # noqa: E402

R = ROOT / "results"
REF = R / "stress_method_matrix_2026-08-20/pad_match/hspice_references"
OUT = R / "pulse_train_2026-09-08"
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
N_PULSES = 8
R_LOAD, C_LOAD_PF = 50.0, 2.0

# (ibis, supply, stressed width ns). Widths are the ~57-71% depth cases.
DEV = {
    "io_buf": (R / "io_buf_fast_edge_regen_2026-08-19/source/io_buf_fast_50ps.ibs", 3.3, 1.792),
    "inv_chain": (REF / "inv_chain/fast_5ps/r50_c2pf/short_high_w104ps_104ps/native/input.ibs", 1.8, 0.111),
    "ex2": (REF / "ex2/fast_5ps/r50_c2pf/short_high_w810ps_810ps/native/input.ibs", 3.3, 0.858),
}
COL = {"native": "#2B6CA3", "ours": "#C05621"}


def ibis_names(ibis: Path) -> tuple[str, str]:
    t = ibis.read_text(errors="ignore")
    return (re.search(r"^\[Model\]\s+(\S+)", t, re.M).group(1),
            re.search(r"^\[Component\]\s+(.+?)\s*$", t, re.M).group(1))


def edges(width: float, n: int) -> list[float]:
    """50% duty train: high for `width`, low for `width`, n times, from 5 ns."""
    out, t = [], 5.0
    for _ in range(n):
        out += [t, t + width]
        t += 2 * width
    return out


def stop_ns(width: float, n: int) -> float:
    return 5.0 + 2 * width * n + 6.0


def run_hspice(d: Path, deck: str, hspice: Path, timeout=1800) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "run.sp").write_text(deck, encoding="utf-8")
    tr0, lis = d / "run.tr0", d / "run.lis"
    ok = tr0.exists() and lis.exists() and "job concluded" in lis.read_text(errors="replace").lower()
    if not ok:
        rc = base.run_process([str(hspice), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", timeout)
        if rc != 0 or not tr0.exists():
            raise RuntimeError(f"hspice failed: {d}")
    return tr0


def transistor(dev, device, width, n, tag, hspice):
    d = OUT / dev / tag / "transistor"
    d.mkdir(parents=True, exist_ok=True)
    base.copy_transistor_inputs(device, d)
    case = base.PulseCase(f"train_{tag}", 0.001, "short_high", width, stop_ns(width, n))
    deck = base.transistor_deck(device, case)
    pwl = sl.pulse(0.0, device.supply_v, edges(width, n), stop_ns=stop_ns(width, n))
    deck = re.sub(r"Vin in_dig 0 PWL\(.*?\)", f"Vin in_dig 0 {pwl}", deck, flags=re.S)
    deck = deck.replace(f".tran {base.fmt(base.TRAN_STEP_NS)}n", ".tran 0.002n")
    raw = sl.parse_hspice_tr0(run_hspice(d, deck, hspice))
    return sl.time_ns(raw), np.asarray(raw["v(pad_sp)"], float)


def native(dev, ibis, sup, width, n, tag, hspice):
    d = OUT / dev / tag / "native"
    d.mkdir(parents=True, exist_ok=True)
    (d / "input.ibs").write_bytes(ibis.read_bytes())
    model, _ = ibis_names(ibis)
    pwl = sl.pulse(0.0, sup, edges(width, n), stop_ns=stop_ns(width, n))
    # The B-element node list follows the model type: a plain Output model takes
    # six nodes with buffer=2; an I/O model (io_buf's OutputInput) takes the
    # eight-node form with enable and digital-out. Getting this wrong is HSPICE's
    # "difficulty in reading input" on the BIBIS line.
    mtype = re.search(r"^Model_type\s+(\S+)", ibis.read_text(errors="ignore"), re.M).group(1).lower()
    if mtype == "output":
        belem = ("BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref\n"
                 f"+ file='input.ibs' model='{model}' buffer=2 typ=typ power=off interpol=1\n")
        extra = ""
    else:
        belem = ("BIBIS pu_ref pd_ref pad in_dig en_sig dig_q pc_ref gc_ref\n"
                 f"+ file='input.ibs' model='{model}' typ=typ power=off interpol=1\n")
        extra = f"Ven en_sig 0 DC {sup}\nRdig dig_q 0 1k\n"
    deck = f"""* {dev} native IBIS, pulse train {tag}
.title native train
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {pwl}
{extra}VPU pu_ref 0 DC {sup}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {sup}
VGC gc_ref 0 DC 0
{belem}+ ramp_rwf=2 ramp_fwf=2
Rload pad 0 {R_LOAD}
Cload pad 0 {C_LOAD_PF}p
.probe tran V(pad)
.tran 0.002n {stop_ns(width, n)}n
.end
"""
    raw = sl.parse_hspice_tr0(run_hspice(d, deck, hspice))
    return sl.time_ns(raw), np.asarray(raw["v(pad)"], float)


SUB_OVERRIDE: dict[str, Path] = {}     # dev -> a corrected driver.sub to train instead of the shipped one


def ours(dev, ibis, sup, width, n, tag):
    d = OUT / dev / tag / ("ours_" + SUB_OVERRIDE[dev].parent.name if dev in SUB_OVERRIDE else "ours")
    d.mkdir(parents=True, exist_ok=True)
    if dev in SUB_OVERRIDE:
        (d / "driver.sub").write_bytes(SUB_OVERRIDE[dev].read_bytes())
    if not (d / "driver.sub").exists():
        model, comp = ibis_names(ibis)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical", str(d / "driver.sub"))
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = sl.pulse(0.0, sup, edges(width, n), stop_ns=stop_ns(width, n))
    (d / "run.sp").write_text(
        dk.ngspice_header() + ".include driver.sub\n" + dk.supply("VCC", sup, name="Vdd")
        + f"Vin IN 0 {pwl}\n" + dk.supply("EN", sub.enable_level(sup), name="Ven")
        + sub.instance("X1") + dk.load("OUT", R_LOAD, C_LOAD_PF)
        + f".tran 0.002n {stop_ns(width, n)}n\n.save V(OUT)\n.end\n", encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1800) is None:
            raise RuntimeError(f"ngspice failed: {d}")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    return sl.time_ns(raw), sl.trace(raw, "out")


def per_pulse(t_si, si, t_m, m, width, n):
    """(peak shift ps, lag ps, peak error mV) per pulse."""
    rows = []
    for k in range(n):
        lo, hi = 5.0 + 2 * width * k, 5.0 + 2 * width * (k + 1)
        g = np.arange(lo, hi, 0.002)
        a, b = np.interp(g, t_si, si), np.interp(g, t_m, m)
        ia, ib = int(np.argmax(a)), int(np.argmax(b))
        lag, _ = best_lag(g, a, b, lo, hi, max_lag_ns=min(0.4, width))
        rows.append(((g[ib] - g[ia]) * 1e3, lag, (b[ib] - a[ia]) * 1e3, a[ia]))
    return rows


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", nargs="*", default=[], help="dev=path/to/driver.sub overrides for 'ours'")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    for item in args.sub:
        dev, path = item.split("=", 1)
        SUB_OVERRIDE[dev] = Path(path)
    global OUT
    if args.tag:
        OUT = OUT.parent / (OUT.name + "_" + args.tag)
    OUT.mkdir(parents=True, exist_ok=True)
    hspice = Path(default_hspice())
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    table = []
    for col, (dev, (ibis, sup, w_stress)) in enumerate(DEV.items()):
        device = next(x for x in base.DEVICES if x.device_id == dev)
        for row, (tag, width) in enumerate((("stressed", w_stress), ("control", 5.0))):
            print(f"  {dev} {tag} W={width} ns, {N_PULSES} pulses ...")
            t_si, si = transistor(dev, device, width, N_PULSES, tag, hspice)
            t_n, nat = native(dev, ibis, sup, width, N_PULSES, tag, hspice)
            t_o, our = ours(dev, ibis, sup, width, N_PULSES, tag)
            res = {"native": per_pulse(t_si, si, t_n, nat, width, N_PULSES),
                   "ours": per_pulse(t_si, si, t_o, our, width, N_PULSES)}
            a = axes[row][col]
            for name, rows in res.items():
                ks = np.arange(1, N_PULSES + 1)
                a.plot(ks, [r[1] for r in rows], marker="o", color=COL[name], lw=2.0, label=f"{name}: lag")
                a.plot(ks, [r[0] for r in rows], marker="s", ls="--", color=COL[name], lw=1.4,
                       label=f"{name}: peak shift")
                for k, r in enumerate(rows, 1):
                    table.append(dict(device=dev, case=tag, width_ns=width, pulse=k, model=name,
                                      peak_shift_ps=round(r[0], 1), lag_ps=round(r[1], 1),
                                      peak_err_mV=round(r[2], 1), si_peak_V=round(r[3], 4)))
            a.axhline(0, color="#111", lw=0.8)
            a.set_title(f"{dev} {tag}, W = {width*1e3:.0f} ps, 50% duty", fontsize=11, fontweight="bold")
            a.set_xlabel("pulse index")
            a.set_ylabel("model minus transistor (ps)")
            a.grid(alpha=0.3)
            if col == 0:
                a.legend(fontsize=8)
            si_pk = [r[3] for r in res["ours"]]
            print(f"    transistor pad peaks: " + " ".join(f"{v:.3f}" for v in si_pk))
            for name, rows in res.items():
                print(f"    {name:<7} lag ps: " + " ".join(f"{r[1]:+5.0f}" for r in rows)
                      + f"   | peak err mV: " + " ".join(f"{r[2]:+5.0f}" for r in rows))
    fig.suptitle("Does the timing error accumulate over a pulse train?", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "pulse_train.png", dpi=170)
    plt.close(fig)
    with (OUT / "per_pulse.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    print(f"\n  figure: {OUT / 'pulse_train.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
