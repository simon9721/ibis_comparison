#!/usr/bin/env python3
"""Does io_buf's pull-down chain depth show up on a short-LOW pulse?

Step 2 swept io_buf's pull-down chain over Kd = 2...5 and found the scores identical to 0.1 %
and 1 ps - but every case there was a short-HIGH pulse, whose falling leg barely exercises the
pull-down path. This drives the same builds with short-LOW pulses (the input dips and the pad
is pulled down and released) at the five widths the 08-14 loaded-swing sweep selected, where
transistor references already exist.

Two questions, in order:

1. do the four builds differ from each other at all? If not, Kd is unidentifiable from the pad
   and the answer is that it does not matter;
2. if they do, which Kd matches the transistor?

Output: results/io_buf_pulldown_depth_2026-09-22/

    py -3.14 scripts/io_buf_pulldown_depth.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import stage_count_from_file as sc  # noqa: E402

OUT = ROOT / "results" / "io_buf_pulldown_depth_2026-09-22"
REF = ROOT / "results" / "three_buffer_loaded_swing_stress_sweep_2026-08-14" / \
    "hspice_references" / "io_buf" / "transistor" / "r50_c2pf"
DEV, K, KDS = "io_buf", 1, (2, 3, 4, 5)


def short_low(d: Path, sub_text: str, sup: float, width_ns: float):
    """One short-LOW run: the input sits high, dips for `width_ns`, and returns."""
    d.mkdir(parents=True, exist_ok=True)
    sub_path = d / "driver.sub"
    if not sub_path.exists() or sub_path.read_text(encoding="utf-8", errors="replace") != sub_text:
        sub_path.write_text(sub_text, encoding="utf-8")
    sub = dk.PybisSubckt.parse(sub_path)
    pwl = sl.pulse(sup, 0.0, [gp.RISE_NS, gp.RISE_NS + width_ns],
                   edge_ps=gp.EDGE_PS.get(DEV, 1.0), stop_ns=gp.STOP_NS)
    saves = " ".join(f"V(X1.{p})" for p in gp.PROBES)
    deck = (dk.ngspice_header() + ".include driver.sub\n" + dk.supply("VCC", sup, name="Vdd")
            + f"Vin IN 0 {pwl}\n" + dk.supply("EN", sub.enable_level(sup), name="Ven")
            + sub.instance("X1") + dk.load("OUT", gp.R_LOAD, gp.C_LOAD_PF)
            + f".tran 0.002n {gp.STOP_NS}n\n.save V(OUT) {saves}\n.end\n")
    prev, stamp = d / "run.sp", d / "driver.sub.used"
    fresh = (prev.exists() and prev.read_text(encoding="utf-8") == deck and (d / "run.raw").exists()
             and stamp.exists() and stamp.read_text(encoding="utf-8") == sub_text)
    if not fresh:
        prev.write_text(deck, encoding="utf-8")
        stamp.write_text(sub_text, encoding="utf-8")
        if sl.ngspice(d, timeout_s=1800) is None:
            raise RuntimeError(f"ngspice failed: {d}")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    return sl.time_ns(raw), sl.trace(raw, "out")


SELECTION = ROOT / "results" / "three_buffer_loaded_swing_stress_sweep_2026-08-14" / "selection.csv"


def cases():
    """(width ps, the depth the transistor reached, as % of its own full swing).

    Measured from the 08-14 sweep's waveforms with the same rule used on ours - the extremum
    against the long-control swing - rather than read from its selection table, so both sides
    are derived the same way. (They agree to ~2 points either way.)"""
    tc, pc = gp.tr0_pad(REF / "long_control" / "run.tr0")
    rest = float(np.median(pc[(tc > 8.0) & (tc < 9.9)]))     # settled high, before the dip at 10 ns
    low = float(np.min(pc))
    out = {}
    for d in sorted(REF.glob("short_low_swing*")):
        t, pad = gp.tr0_pad(d / "run.tr0")
        m = float(np.min(pad[(t > 10.0) & (t < 13.0)]))
        w = int(d.name.split("_")[-1].removesuffix("ps"))
        out[w] = 100.0 * (rest - m) / (rest - low)           # the later search wins on a tie
    return sorted(out.items())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    gp.VARIANT_NAME = DEV
    sup, _ibis = gp.VARIANTS[DEV]
    cs = cases()
    print(f"  short-low widths with a transistor reference: {[w for w, _ in cs]} ps")
    rows = []
    # our own full swing in this direction: a long low pulse, the 100 % the depths refer to
    tag0 = sc.build_dir("step2", DEV, K, KDS[0])
    t0, pad0 = short_low(OUT / "full_swing", (tag0 / "driver_chain.sub").read_text(encoding="utf-8"), sup, 10.0)
    rest = float(np.median(pad0[t0 < gp.RISE_NS - 0.2]))
    low = float(np.min(pad0))
    print(f"  our full swing in this direction: {rest:.3f} V rest -> {low:.3f} V ({rest - low:.3f} V)")
    for kd in KDS:
        tag = sc.build_dir("step2", DEV, K, kd)
        if tag is None:
            print(f"  Kd={kd}: no step-2 build, skipped", flush=True)
            continue
        text = (tag / "driver_chain.sub").read_text(encoding="utf-8")
        for w, real_pct in cs:
            t, pad = short_low(OUT / f"Kd{kd}" / f"w{w}", text, sup, w / 1000.0)
            ours = float(np.min(pad[(t > gp.RISE_NS) & (t < gp.RISE_NS + 3.0)]))
            our_pct = 100.0 * (rest - ours) / (rest - low)
            rows.append(dict(Kd=kd, width_ps=w, our_min_V=round(ours, 4), our_depth_pct=round(our_pct, 1),
                             transistor_depth_pct=round(real_pct, 1),
                             depth_err_points=round(our_pct - real_pct, 1)))
            print(f"    Kd={kd} w={w:>4} ps: our depth {our_pct:5.1f} %, transistor {real_pct:5.1f} % "
                  f"({our_pct - real_pct:+.1f} points)", flush=True)
    with (OUT / "pulldown_depth.csv").open("w", newline="") as fh:
        w_ = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w_.writeheader()
        w_.writerows(rows)
    spread = {}
    for w, _ in cs:
        v = [r["our_min_V"] for r in rows if r["width_ps"] == w]
        if v:
            spread[w] = max(v) - min(v)
    print("\n  spread across Kd = 2...5 at each width (V): "
          + ", ".join(f"{w}: {s:.4f}" for w, s in spread.items()))
    print(f"  wrote {OUT / 'pulldown_depth.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
