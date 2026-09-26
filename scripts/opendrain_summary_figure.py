#!/usr/bin/env python3
"""Open-drain, three buffers, four builds: the low-excursion error against depth.

    py -3.14 scripts/opendrain_summary_figure.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R = ROOT / "results"
CHAIN = {
    "base": R / "opendrain_chain_2026-09-10/base_c3_calib680_odprior/cases.csv",
    "od_weak": R / "opendrain_chain_2026-09-10/od_weak_c3_calib680_odprior_K3/cases.csv",
    "od_slowpre": R / "opendrain_chain_2026-09-10/od_slowpre_c3_calib800_odprior_K3/cases.csv",
}
CALIB = {"base": 46.7, "od_weak": 61.2, "od_slowpre": 70.1}


def rows(p):
    with p.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if float(r["width_ns"]) < 5.0]


def main() -> int:
    fig, axes = plt.subplots(2, 3, figsize=(18, 9))
    for j, v in enumerate(CHAIN):
        rs = rows(CHAIN[v])
        d = [float(r["depth_pct"]) for r in rs]
        a = axes[0, j]
        a.plot(d, [float(r["native_low_err_mV"]) for r in rs], "-", color="#2B6CA3", lw=1.8, marker="s", label="native HSPICE IBIS")
        a.plot(d, [float(r["legacy_low_err_mV"]) for r in rs], "-", color="#C05621", lw=1.8, marker="o", label="ours, legacy Kd control (before)")
        a.plot(d, [float(r["gatestate_low_err_mV"]) for r in rs], "-", color="#7F8C8D", lw=1.8, marker="^", label="ours, open-drain gate-state build (converter, no silicon)")
        a.plot(d, [float(r["chain_low_err_mV"]) for r in rs], "-", color="#2E7D4F", lw=2.4, marker="D", label="ours, chain on the pull-down gate (3 pF, NMOS map, one pad point)")
        a.axhline(0, color="k", lw=0.8)
        a.axvline(CALIB[v], color="#2E7D4F", ls=":", lw=1.0)
        a.set_title(f"{v}: model low minus transistor low", fontsize=12, fontweight="bold")
        a.set_xlabel("depth (% of the settled low excursion the transistor reached)")
        a.set_ylabel("mV  (negative = pulls too far)")
        a.invert_xaxis()
        a.grid(alpha=0.3)
        if j == 0:
            a.legend(fontsize=8, loc="lower left")
        b = axes[1, j]
        b.plot(d, [float(r["si_kd_at_min"]) for r in rs], "-", color="#111111", lw=3.0, marker="o", label="transistor")
        b.plot(d, [float(r["gatestate_kd_at_min"]) for r in rs], "-", color="#7F8C8D", lw=1.8, marker="^", label="gate-state build")
        b.plot(d, [float(r["chain_kd_at_min"]) for r in rs], "-", color="#2E7D4F", lw=2.4, marker="D", label="chain")
        b.set_title("Kd at the transistor's pad minimum", fontsize=12, fontweight="bold")
        b.set_xlabel("depth (%)")
        b.set_ylabel("Kd")
        b.set_ylim(-0.05, 1.1)
        b.invert_xaxis()
        b.grid(alpha=0.3)
        if j == 0:
            b.legend(fontsize=8)
    fig.suptitle("Open-drain ex2, three variants: legacy → converter gate-state build → chain recipe, against transistor and native "
                 "(dotted line = the one calibration width)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    out = R / "opendrain_gatestate_2026-09-10/opendrain_summary.png"
    fig.savefig(out, dpi=150)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
