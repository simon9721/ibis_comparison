#!/usr/bin/env python3
"""One clear figure: the lag and the gap between native IBIS and pybis.

Both read the same base8 IBIS file into the same 50 ohm + 2 pF load. The top
panel overlays the rising edge -- the horizontal offset between the two 50%
crossings is the *lag*. The bottom panel is pybis minus native across the whole
edge -- its size is the *gap* (the RMSE is the area under it). Converged ngspice
so the difference shown is the model, not the solver.

    py -3.14 scripts/plot_native_vs_pybis_lag_gap.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python",
           ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402

IBIS = (ROOT / "results" / "inv_chain_variants_2026-09-02" / "base8" /
        "selection" / "tr1ps" / "invchain_base8_tr1ps.ibs")
OUT = ROOT / "results" / "pybis_lag_localization_2026-09-03"
SUP, RL, CL = 1.8, 50.0, 2.0
NATIVE, PYBIS = "#2B6CA3", "#C02626"


def _pwl():
    return sl.pulse(0.0, SUP, [5.0, 15.0], stop_ns=22.0)


def native(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(IBIS, d / IBIS.name)
    (d / "run.sp").write_text(f"""* native
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {_pwl()}
VPU pu_ref 0 DC {SUP}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUP}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='{IBIS.name}' model='driver2' buffer=2 typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
Rload pad 0 {RL}
Cload pad 0 {CL}p
.probe tran V(pad)
.tran 0.0005n 22n
.end""", encoding="utf-8")
    tr0 = sl.hspice(d)
    r = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(r), sl.signal(r, "v(pad)")


def pybis(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name="driver2", component_name="invchain")
    subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical", str(d / "driver.sub"))
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", (d / "driver.sub").read_text(), re.M | re.I)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    nd = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
    nodes = [nd.get(p.upper(), p) for p in pins]
    (d / "run.sp").write_text(f"""* pybis converged
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC {SUP}
Vin IN 0 {_pwl()}
Ven EN 0 DC {SUP}
X1 {' '.join(nodes)} {m.group(1)}
Rload OUT 0 {RL}
Cload OUT 0 {CL}p
.tran 0.0005n 22n
.save V(OUT)
.end""", encoding="utf-8")
    r = sl.parse_ngspice_raw(sl.ngspice(d))
    return sl.time_ns(r), sl.trace(r, "out")


def cross(t, y, lvl, rising, after):
    for i in range(1, len(y)):
        if t[i] < after:
            continue
        if (rising and y[i - 1] < lvl <= y[i]) or (not rising and y[i - 1] > lvl >= y[i]):
            return t[i - 1] + (lvl - y[i - 1]) * (t[i] - t[i - 1]) / (y[i] - y[i - 1])
    return float("nan")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tn, yn = native(OUT / "native")
    tp, yp = pybis(OUT / "pybis")
    grid = np.linspace(4.9, 6.4, 30000)
    a = np.interp(grid, tp, yp)   # pybis
    b = np.interp(grid, tn, yn)   # native
    half = 0.9
    cn = cross(grid, b, half, True, 5.0)
    cp = cross(grid, a, half, True, 5.0)
    lag = (cp - cn) * 1e3
    rmse = np.sqrt(np.trapezoid((a - b) ** 2, grid) / (grid[-1] - grid[0])) * 1e3

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(11.5, 8.4), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1.4]})
    ax0.plot(grid, b, color=NATIVE, lw=2.6, label="native IBIS (HSPICE B-element)")
    ax0.plot(grid, a, color=PYBIS, lw=2.2, ls=(0, (5, 2.2)), label="pybis (ngspice subcircuit)")
    ax0.axhline(half, color="#8A8A8A", lw=1.0, ls=":")
    ax0.annotate("", xy=(cp, half), xytext=(cn, half),
                 arrowprops=dict(arrowstyle="<->", color="#111", lw=1.6))
    ax0.text((cn + cp) / 2, half + 0.06, f"lag {lag:.1f} ps", ha="center",
             fontsize=12, fontweight="bold")
    # Zoom inset: at full scale the curves sit 4.9 ps apart on a 1500 ps axis
    # (0.33% of the width), so the separation the bottom panel reports as 93 mV
    # is invisible. The inset opens the steepest part of the edge, where that
    # 93 mV is simply the lag times the 18.5 mV/ps slew.
    axz = ax0.inset_axes([0.58, 0.13, 0.40, 0.46])
    axz.plot(grid, b, color=NATIVE, lw=2.4)
    axz.plot(grid, a, color=PYBIS, lw=2.0, ls=(0, (4, 1.8)))
    imx = int(np.argmax(np.abs(a - b)))
    axz.set_xlim(grid[imx] - 0.018, grid[imx] + 0.022)
    lo = min(a[imx], b[imx]); hi = max(a[imx], b[imx])
    axz.set_ylim(lo - 0.32, hi + 0.34)
    axz.grid(alpha=0.30, color="#C9D3DE", lw=0.7)
    axz.tick_params(labelsize=8.5)
    axz.set_title("zoom: steepest part of the edge", fontsize=9.5, pad=4)
    imax = imx
    axz.annotate("", xy=(grid[imax], a[imax]), xytext=(grid[imax], b[imax]),
                 arrowprops=dict(arrowstyle="<->", color="#111", lw=1.4))
    axz.text(grid[imax] + 0.0015, (a[imax] + b[imax]) / 2, "93 mV",
             fontsize=9.5, fontweight="bold", va="center")
    ax0.indicate_inset_zoom(axz, edgecolor="#555")

    ax0.set_ylabel("Pad (V)", fontsize=12)
    ax0.set_title("base8  |  50 Ω + 2 pF  |  native IBIS vs pybis, rising edge  (converged)",
                  fontsize=14.5, fontweight="bold", pad=10)
    ax0.legend(fontsize=11.5, loc="upper left", framealpha=0.95)

    ax1.fill_between(grid, 0, (a - b) * 1e3, color=PYBIS, alpha=0.30)
    ax1.plot(grid, (a - b) * 1e3, color=PYBIS, lw=1.6)
    ax1.axhline(0, color="#5A5A5A", lw=1.0)
    ax1.text(0.015, 0.86, f"gap: RMSE {rmse:.1f} mV, worst {np.max(np.abs(a-b))*1e3:.0f} mV",
             transform=ax1.transAxes, fontsize=11.5, fontweight="bold")
    ax1.set_ylabel("pybis − native (mV)", fontsize=11.5)
    ax1.set_xlabel("Time (ns)", fontsize=12)
    for ax in (ax0, ax1):
        ax.set_xlim(4.9, 6.4)
        ax.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        ax.tick_params(labelsize=11)
        for s in ax.spines.values():
            s.set_color("#3A4753")
    fig.tight_layout()
    fig.savefig(OUT / "native_vs_pybis_lag_and_gap.png", dpi=175)
    plt.close(fig)
    print(f"lag {lag:.1f} ps, gap RMSE {rmse:.1f} mV")
    print(f"wrote {OUT / 'native_vs_pybis_lag_and_gap.png'}")


if __name__ == "__main__":
    main()
