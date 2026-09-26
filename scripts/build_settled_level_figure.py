#!/usr/bin/env python3
"""Where the full-swing settled level comes from: the measured map's end value.

Zooms the full-swing pad plateau for the transistor, the build using the measured
(silicon) Ku/Kd maps as solved, and the same build with the map ends anchored to 0 and 1
(`gate_chain_prototype.py --anchor-maps`). Reads existing runs only; nothing is simulated.

    py -3.14 scripts/build_settled_level_figure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import spicelab as sl  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402

R = ROOT / "results"
CH = R / "gate_chain_prototype_2026-09-10"
OUT = R / "track2_train_check_2026-09-13" / "figs"
C_SI, C_PLAIN, C_ANCH = "#111111", "#B03060", "#2B6CA3"

CASES = [("ex2", "ex2_c1.7/real_silicon_K3_calibpad810", "ex2_c1.7/real_silicon_K3_calibpad810_anch"),
         ("inv_chain", "inv_chain_c0.6/real_silicon_K7_calibpad104", "inv_chain_c0.6/real_silicon_K7_calibpad104_anch")]


def model(p: Path):
    raw = sl.parse_ngspice_raw(p / "full/run.raw")
    return sl.time_ns(raw), np.asarray(raw["v(out)"], float)


def main() -> int:
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.6))
    for a, (dev, plain, anch) in zip(ax, CASES):
        raw = psp.parse_tr0(psp.OUT / dev / "full/run.tr0")
        t_si, si = np.asarray(raw["time"], float) * 1e9, np.asarray(raw["v(pad_sp)"], float)
        hi = float(np.interp(12.0, t_si, si))
        a.plot(t_si, si, color=C_SI, lw=3.2, label=f"transistor, settles at {hi:.4f} V")
        for lbl, d, c, ls in (("measured map as solved", plain, C_PLAIN, "--"),
                              ("measured map, ends anchored", anch, C_ANCH, "-")):
            tm, vm = model(CH / d)
            v12 = float(np.interp(12.0, tm, vm))
            a.plot(tm, vm, color=c, lw=2.0, ls=ls, label=f"{lbl}: {1e3 * (v12 - hi):+.1f} mV")
        a.set_xlim(8.0, 15.0)
        a.set_ylim(hi - 0.035, hi + 0.035)
        a.grid(alpha=0.3)
        a.set_xlabel("time (ns)")
        a.set_ylabel("pad (V)")
        a.legend(fontsize=9.5, loc="lower left", framealpha=0.95)
        a.set_title(f"{dev}: the full-swing plateau, magnified", fontweight="bold", fontsize=11.5)
    fig.suptitle("The settled level is the measured map's end value, not the command layer: anchoring Ku to 1 and Kd to 0 at the ends closes it",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "settled_level.png", dpi=160)
    plt.close(fig)
    print("wrote", OUT / "settled_level.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
