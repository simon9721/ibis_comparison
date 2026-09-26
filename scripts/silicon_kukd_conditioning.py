#!/usr/bin/env python3
"""Is the transistor's stressed Ku near a reversal an artifact? Prove it or drop it.

`pu_off_scale_2026-09-07` claimed the transistor's stressed Ku peak (1.2892 at
+49 ps on io_buf 1792 ps, from a pull-up that entered the fall at 0.48) is a
solve artifact and cannot anchor a delay. That claim was made on plausibility --
"a pull-up that entered at 0.48 does not reach 1.29" -- not on a measurement.

It also sits against a standing negative result: `two_fixture_conditioning.py`
found io_buf's *characterisation tables* well conditioned (2.7 median, 3.1 max).
But that is a different solve. The stressed silicon coefficients come from two
transistor runs under the stressed stimulus, and conditioning there depends on
those trajectories, not on the recorded tables.

`solve_silicon_kukd` already returns cond(M) in column 3, and its own comment
names the mechanism: the two fixtures stop giving independent information
whenever both devices are nearly off. This reads it out at the reversal.

The test is falsifiable in both directions:

* cond spikes where Ku spikes  -> artifact confirmed, the claim stands;
* cond stays low               -> the Ku excursion is real and the claim is wrong.

    py -3.14 scripts/silicon_kukd_conditioning.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402

R = ROOT / "results"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
FIX = (R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "hspice_fixtures"
       / "io_buf")
OUT = R / "silicon_kukd_conditioning_2026-09-07"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, RISE_NS = 3.3, 5.0
WIDTHS = (2354, 1989, 1792, 1505)


def fixture(width: int, tag: str) -> np.ndarray:
    raw = sl.parse_hspice_tr0(FIX / f"short_high_w{width}ps" / tag / "run.tr0")
    t = np.asarray(raw["time"], float)
    v = np.asarray(raw["v(pad_sp)"], float)
    return np.column_stack([t, v, v, v])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)

    print("  Transistor Ku/Kd and the conditioning of the 2x2 solve that made")
    print("  them, around the reversal. cond(M) is column 3 of the solver.\n")
    fig, axes = plt.subplots(2, len(WIDTHS), figsize=(4.0 * len(WIDTHS), 7.0),
                             sharex=True)
    for col, w in enumerate(WIDTHS):
        sol = solve_silicon_kukd(data, fixture(w, "vfix_0"),
                                 fixture(w, "vfix_vcc"), SUPPLY)
        t = sol[:, 0] * 1e9 - (RISE_NS + w / 1000.0)
        ku, kd, cond = sol[:, 1], sol[:, 2], sol[:, 3]
        base = float(np.median(cond[(t > 0.150) & (t < 0.400)]))
        print(f"    --- {w} ps   (cond median over +150..+400 ps = {base:.1f})")
        print(f"    {'t-rev ps':>9}{'Ku':>10}{'Kd':>10}{'cond(M)':>12}"
              f"{'x baseline':>12}")
        for p in (-0.050, 0.000, 0.030, 0.050, 0.070, 0.090, 0.150, 0.250, 0.400):
            i = int(np.argmin(np.abs(t - p)))
            print(f"    {t[i]*1e3:>9.0f}{ku[i]:>10.4f}{kd[i]:>10.4f}"
                  f"{cond[i]:>12.1f}{cond[i]/base:>12.1f}")
        peak = int(np.argmax(np.where((t > -0.02) & (t < 0.30), ku, -9e9)))
        print(f"    Ku peaks {ku[peak]:.4f} at {t[peak]*1e3:+.0f} ps, "
              f"cond there {cond[peak]:.1f} = {cond[peak]/base:.1f}x baseline\n")

        a = axes[0][col]
        m = (t > -0.35) & (t < 0.8)
        a.plot(t[m], ku[m], color="#111111", lw=2.4, label="transistor Ku")
        a.plot(t[m], kd[m], color="#B03060", lw=1.8, label="transistor Kd")
        a.axvline(0, color="#8A8A8A", ls="--", lw=1.2)
        a.axhline(0, color="#111", lw=0.8)
        a.set_ylim(-1.2, 1.5)
        a.set_title(f"{w} ps", fontsize=13, fontweight="bold")
        a.grid(alpha=0.3)
        if col == 0:
            a.set_ylabel("solved coefficient")
            a.legend(fontsize=9)
        b = axes[1][col]
        b.plot(t[m], cond[m], color="#C05621", lw=2.2)
        b.set_ylim(0, 5)
        b.axvline(0, color="#8A8A8A", ls="--", lw=1.2)
        b.axhline(base, color="#2B6CA3", ls=":", lw=1.6,
                  label=f"baseline {base:.0f}")
        b.axvspan(-0.02, 0.090, color="#C05621", alpha=0.12)
        b.grid(alpha=0.3)
        b.set_xlabel("Time from the reversal (ns)")
        if col == 0:
            b.set_ylabel("cond(M)  (1 = perfect; >100 would be ill-conditioned)")
            b.legend(fontsize=9)
    fig.suptitle("The transistor's stressed coefficients and the conditioning "
                 "of the solve behind them", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "silicon_kukd_conditioning.png", dpi=200)
    plt.close(fig)
    print(f"  figure: {OUT / 'silicon_kukd_conditioning.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
