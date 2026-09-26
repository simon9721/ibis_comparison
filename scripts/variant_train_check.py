#!/usr/bin/env python3
"""Validation: the nine variants on a stressed pulse train (8 pulses, 50 % duty, at each
variant's 50 %-depth width, 1 ps input edges like their stress cases).

Transistor: the variant's depth50 transistor deck with the train PWL substituted.
Models: track 1 (file chain + prior map + pad point) and track 2 (+ measured map), the
builds already made by gate_chain_prototype.py / variant_silicon_maps.py.
Scoring as in track2_train_check.py (windows shifted by the transistor's own delay).

    py -3.14 scripts/variant_train_check.py [--only ex2_base ...]
"""
from __future__ import annotations

import argparse
import re
import shutil
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
from track2_train_check import per_pulse  # noqa: E402

R = ROOT / "results"
CH = R / "gate_chain_prototype_2026-09-10"
OUT = R / "variant_train_check_2026-09-14"
N = 8
VARIANTS = ["ex2_base", "ex2_weak", "ex2_nomiller", "ex2_skewp", "ex2_slowpre", "inv_base8", "inv_weak", "inv_skewp", "inv_stage4"]


PATTERNS = [
    ("track 1", "ibis_prior_K*_calibpad50", "#C05621", "-"),
    ("track 2", "ibis_silicon_K*_calibpad50", "#2E7D4F", "--"),
    ("real stage", "real_silicon_K*_calibpad50", "#2B5C8A", "-."),
    ("real stage, sqrt", "real_silicon_K*_calibpad50_p0.5", "#7B3F9E", ":"),
    ("real stage, joint", "real_silicon_K*_calibpad50_joint*", "#B03060", "-."),
    # one row per tail ratio: builds() takes hits[0], so a single "_dn*" row would score only
    # the lexically first ratio (dn1.5) and silently ignore dn2 and dn3
    ("joint + tail 1.5", "real_silicon_K*_calibpad50_joint*_dn1.5", "#8A6D3B", "--"),
    ("joint + tail 2", "real_silicon_K*_calibpad50_joint*_dn2", "#6D8A3B", "--"),
    ("joint + tail 3", "real_silicon_K*_calibpad50_joint*_dn3", "#3B6D8A", "--"),
]


def builds(v):
    """[(label, driver.sub, colour, linestyle)] for the builds that exist for this variant."""
    d = next(p for p in CH.glob(f"{v}_c*") if p.is_dir())
    out = []
    for label, pat, col, ls in PATTERNS:
        suffix = pat.split("*")[-1]
        hits = sorted(h for h in d.glob(pat) if (h / "driver_chain.sub").exists() and h.name.endswith(suffix))
        if "_dn" not in pat:
            # a trailing "*" makes endswith("") vacuous, so the plain joint pattern would also
            # swallow the tail-ratio builds; keep each row to the builds it names
            hits = [h for h in hits if "_dn" not in h.name]
        if hits:
            out.append((label, hits[0] / "driver_chain.sub", col, ls))
    return out


def transistor_train(v, sup, width, src_case: Path):
    d = OUT / v / "transistor_train"
    d.mkdir(parents=True, exist_ok=True)
    src = src_case / "transistor"
    for f in src.iterdir():
        if f.is_file() and not f.name.startswith("run."):
            shutil.copy2(f, d / f.name)
    deck = (src / "run.sp").read_text(encoding="utf-8", errors="replace")
    pwl = sl.pulse(0.0, sup, pt.edges(width, N), edge_ps=1.0, stop_ns=pt.stop_ns(width, N))
    deck = re.sub(r"Vin in_dig 0 PWL\(.*?\)", f"Vin in_dig 0 {pwl}", deck, flags=re.S)
    deck = re.sub(r"^\.tran .*$", f".tran 0.002n {pt.stop_ns(width, N):g}n", deck, flags=re.M)
    (d / "run.sp").write_text(deck, encoding="utf-8")
    if not (d / "run.tr0").exists():
        if base.run_process([str(default_hspice()), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 1800) != 0:
            raise RuntimeError(f"hspice failed: {d}")
    raw = sl.parse_hspice_tr0(d / "run.tr0")
    key = next(k for k in raw if "pad" in k)
    return sl.time_ns(raw), np.asarray(raw[key], float)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=VARIANTS)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    fig, axes = plt.subplots(len(args.only), 1, figsize=(16, 3.2 * len(args.only)))
    axes = np.atleast_1d(axes)
    print(f"{'variant':<13}{'W ps':>6} | per build: pulse 1 / settled (%)")
    for a, v in zip(axes, args.only):
        sup, _ = gp.VARIANTS[v]
        gp.VARIANT_NAME = v
        cs = gp.cases(v)
        depth, width, case = [c for c in cs if c[0] == 50][0]
        t_si, si = transistor_train(v, sup, width, case)
        a.plot(t_si, si, color="#111", lw=2.4, label="transistor")
        res = []
        for label, sub, col, ls in builds(v):
            d = OUT / v / sub.parent.name
            t_m, m = tc.run_train(d, sub.read_text(encoding="utf-8"), sup, width, N)
            pp = per_pulse(t_si, si, t_m, m, width, N)
            p1 = 100 * pp[0][1] / 1e3 / pp[0][2]
            settled = 100 * float(np.mean([r[1] for r in pp[3:]])) / 1e3 / float(np.mean([r[2] for r in pp[3:]]))
            res.append((label, p1, settled))
            a.plot(t_m, m, color=col, lw=1.4, ls=ls, label=f"{label} ({settled:+.0f} % settled)")
        print(f"{v:<13}{width*1e3:>6.0f} | " + " | ".join(f"{lab}: {p1:+.1f} / {se:+.1f}" for lab, p1, se in res))
        rows.append((v, width, *[x for r in res for x in r]))
        a.set_xlim(4.5, 5 + 16 * width + 1.5)
        a.set_title(f"{v}, 8 x {width*1e3:.0f} ps at 50 % duty", fontweight="bold", fontsize=10)
        a.grid(alpha=0.3)
        a.legend(fontsize=7, loc="upper right")
        a.set_ylabel("pad (V)")
    axes[-1].set_xlabel("time (ns)")
    fig.tight_layout()
    fig.savefig(OUT / "variant_trains.png", dpi=130)
    with (OUT / "summary.csv").open("w", encoding="utf-8") as fh:
        fh.write("variant,width_ns,build,pulse1_pct,settled_pct,(repeated per build)\n")
        for r in rows:
            fh.write(",".join(str(x) for x in r) + "\n")
    print("wrote", OUT / "summary.csv", OUT / "variant_trains.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
