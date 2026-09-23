#!/usr/bin/env python3
"""Where do today's models stand on a stressed pulse train?

Everything in the 09-21/22 track-1 work is single-pulse. The train results on record
(`gate_chain_train_calib_2026-09-10`, `track2_train_check_2026-09-13`) were built before the
converter clamped the input threshold, so their inverter-chain numbers carry the 1.4 V
threshold that masks inv_chain's error threefold.

This reruns the train on the models today's work produced, with no refitting and no HSPICE
(the transistor train references at 50 ps edges are cached from 09-13):

    shipped     the converter's own model, as the bar
    track-1     step 7's build: measured C_comp, family shape, netlist K
    file-only   step 6's build at the K its timing selector chose, knee C_comp, universal shape

Scored per pulse against the transistor train: the first pulse, and the settled ones.

Output: results/train_check_today_2026-09-23/

    py -3.14 scripts/train_check_today.py [--buffers ex2 inv_chain io_buf] [--n 8]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import gate_chain_train_calib as tc  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import pulse_train_accumulation as pt  # noqa: E402
import stage_count_from_file as sc  # noqa: E402

OUT = ROOT / "results" / "train_check_today_2026-09-23"


def models(dev: str):
    """(label, driver text) for the shipped model and today's two builds."""
    b = sc.BUFFERS[dev]
    out = []
    ship = sc.MEAS_MODELS / sc.dcc_name("step2f", dev) / "shipped" / "driver.sub"
    if ship.exists():
        out.append(("shipped", ship.read_text(encoding="utf-8"), ""))
    t7 = sc.build_dir("step2f", dev, b["k_net"][0], b["k_net"][1])
    if t7 is not None:
        out.append(("track-1", (t7 / "driver_chain.sub").read_text(encoding="utf-8"), f"K={b['k_net'][0]}"))
    kd = sc.plateau_band(dev, "pull-down")[0] if b["k_net"][1] is not None else None
    sel = None
    p = sc.OUT / "step6_endtoend.csv"
    if p.exists():
        for r in csv.DictReader(p.open()):
            if r["buffer"] == dev:
                sel = int(r["K_selected"])
    if sel is not None:
        t6 = sc.build_dir("step6", dev, sel, kd)
        if t6 is not None:
            out.append(("file-only", (t6 / "driver_chain.sub").read_text(encoding="utf-8"), f"K={sel}"))
    # the final recipe: K and shape chosen on the whole pad waveform of the one stressed run
    p8 = ROOT / "results" / "selector_from_one_run_2026-09-23" / "selector_picks.csv"
    if p8.exists():
        for r in csv.DictReader(p8.open()):
            if r["buffer"] != dev:
                continue
            kk, sh = r["rms"].split(" ")
            r = dict(r, K_selected=kk[1:], shape_selected=sh)
            vt, al = (float(x) for x in sh.split("/"))
            t8 = (sc.build_dir("step8", dev, int(r["K_selected"]), kd, (vt, al))
                  or sc.build_dir("step6", dev, int(r["K_selected"]), kd))
            if t8 is not None:
                out.append(("file+shape", (t8 / "driver_chain.sub").read_text(encoding="utf-8"),
                            f"K={r['K_selected']} {r['shape_selected']}"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffers", nargs="+", default=["ex2", "inv_chain", "io_buf"])
    ap.add_argument("--n", type=int, default=8)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for dev in args.buffers:
        gp.VARIANT_NAME = dev
        sup, _ibis = gp.VARIANTS[dev]
        width = pt.DEV[dev][2]
        t_si, si = tc.transistor_train_edge50(dev, sup, width, args.n)
        print(f"\n{dev}: train W {width * 1e3:.0f} ps x {args.n}", flush=True)
        for label, text, note in models(dev):
            t_m, m = tc.run_train(OUT / dev / label.replace("/", "_"), text, sup, width, args.n)
            if len(t_m) < 100 or float(t_m.max()) < 0.9 * pt.stop_ns(width, args.n):
                # ngspice gave up (io_buf stalls on some builds: "Reference value ..." then nothing).
                # Scoring the empty trace would read as -100 %, which is not a model error.
                rows.append(dict(buffer=dev, model=label, note=note, first_pulse_err_pct="",
                                 first_pulse_lag_ps="", settled_err_pct="", settled_lag_ps="",
                                 transistor_peak_V="", per_pulse_err_pct="ngspice did not converge"))
                print(f"  {label:10s} {note:6s} ngspice did not converge "
                      f"({len(t_m)} points, {float(t_m.max()):.1f} of {pt.stop_ns(width, args.n):.1f} ns)", flush=True)
                continue
            # settled_error returns percentages: (settled %, settled shift ps, pulse-1 %, pulse-1 shift ps)
            settled_pct, settled_lag, first_pct, first_lag = tc.settled_error(t_si, si, t_m, m, width, args.n)
            per = tc.per_pulse_aligned(t_si, si, t_m, m, width, args.n)
            rows.append(dict(buffer=dev, model=label, note=note,
                             first_pulse_err_pct=round(first_pct, 1), first_pulse_lag_ps=round(first_lag),
                             settled_err_pct=round(settled_pct, 1), settled_lag_ps=round(settled_lag),
                             transistor_peak_V=round(per[0][2], 3) if per else "",
                             per_pulse_err_pct=" / ".join(f"{100 * r[1] / 1e3 / r[2]:+.1f}" for r in per)))
            print(f"  {label:10s} {note:6s} pulse 1 {first_pct:+6.1f} % / {first_lag:+4.0f} ps   "
                  f"settled {settled_pct:+6.1f} % / {settled_lag:+4.0f} ps   "
                  f"per pulse {rows[-1]['per_pulse_err_pct']}", flush=True)
    with (OUT / "train_check.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT / 'train_check.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
