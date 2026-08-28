#!/usr/bin/env python3
"""What the transport-delay command buys, and what it costs.

`delay_cmd` is the "stop integrating a pulse" formulation: the command is a
delayed copy of the input *level*, so it is exactly 0 or 1 at the rails by
construction and cannot strand charge. It has the best pad RMSE in the study --
92.2 mV over 30 stress cases, the only method to beat native IBIS.

The cost is visible in the top two panels. io_buf turns its pullup *off*
0.068 ns after the input falls but does not turn its pulldown *on* for
1.831 ns. Two independently delayed levels therefore both read "off" for the
1.25 ns in between, and the pad is left with no driver at all -- both
coefficients go slightly negative and the node keeps only C_comp and the load.

The shipped edge-integrating command is drawn alongside. It has no dead zone,
because the pulldown command is a capacitor that was already charged; it pays
for that with the stranded charge instead.

    py -3.14 scripts/build_delay_cmd_dead_zone_figure.py
"""
from __future__ import annotations

import argparse
import csv
import glob
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / ".codex_deps" / "presentation" / "python", ROOT / "scripts"):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27"

WIDTH_PS = 1792
EDGE_NS = 5.0
# The two fitted delays that create the gap, from the io_buf typical corner.
PU_OFF_DELAY, PD_ON_DELAY = 0.0677, 1.8313

DELAY_C = "#1B4F8F"
SHIPPED_C = "#C05621"
SILICON_C = "#111111"
DEAD_C = "#D9534F"
DPI = 175


def raw(method: str):
    hits = glob.glob(str(MATRIX / method / "ngspice_runs" / "io_buf" / "*" / "*" /
                         "cases" / f"short_high_w{WIDTH_PS}ps_*" /
                         "ngspice_gate_state" / "run.raw"))
    if not hits:
        return None
    r = parse_ngspice_raw(Path(hits[0]))
    k = {x.lower(): x for x in r}
    d = {n[7:-1]: np.asarray(r[k[n]]) for n in k if n.startswith("v(xdrv.")}
    d["pad"] = np.asarray(r[k["v(pad)"]])
    d["rel_ns"] = np.asarray(r[k["time"]]) * 1e9 - (EDGE_NS + WIDTH_PS / 1000.0)
    return d


def silicon():
    path = MATRIX / "hybrid" / "waveforms" / f"io_buf_short_high_w{WIDTH_PS}ps.csv"
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) for x in r] for r in rows[1:]])
    d = {name: values[:, i] for i, name in enumerate(rows[0])}
    d["rel_ns"] = d["time_ns"] - (EDGE_NS + WIDTH_PS / 1000.0)
    return d


def dead_zone(d):
    """The span where neither coefficient is meaningfully on."""
    m = (d["rel_ns"] > 0) & (d["rel_ns"] < 3.0) & (d["ku"] < 0.02) & (d["kd"] < 0.02)
    if not m.any():
        return None
    return float(d["rel_ns"][m][0]), float(d["rel_ns"][m][-1])


def style(axis, label, ylim):
    axis.axhline(0.0, color="#5A5A5A", lw=1.1)
    axis.axvline(0.0, color="#8A8A8A", ls="--", lw=1.5)
    axis.set_ylim(*ylim)
    axis.set_xlim(-0.3, 4.5)
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=11.5)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")
    axis.set_ylabel(label, fontsize=13.5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    delay, shipped, sil = raw("delay_cmd"), raw("hybrid"), silicon()
    if delay is None or shipped is None:
        print("missing runs")
        return 1
    span = dead_zone(delay)

    panels = [("guptarget", "GUPTARGET\npullup command", (-0.05, 1.1)),
              ("gdntarget", "GDNTARGET\npulldown command", (-0.05, 1.1)),
              ("ku", "Ku", (-0.08, 0.35)),
              ("kd", "Kd", (-0.15, 1.1)),
              ("pad", "Pad voltage (V)", (-0.05, 1.0))]

    fig, axes = plt.subplots(len(panels), 1, figsize=(12.6, 14.0), sharex=True)
    for axis, (node, label, ylim) in zip(axes, panels):
        if span:
            axis.axvspan(*span, color=DEAD_C, alpha=0.14, lw=0, zorder=0)
        if node == "pad":
            axis.plot(sil["rel_ns"], sil["silicon_pad"], color=SILICON_C, lw=3.4,
                      label="HSPICE transistor", zorder=2)
        axis.plot(shipped["rel_ns"], shipped[node], color=SHIPPED_C, lw=2.6,
                  label="edge-integrating command (shipped)", zorder=3)
        axis.plot(delay["rel_ns"], delay[node], color=DELAY_C, lw=2.2,
                  ls=(0, (5, 2.2)), label="transport-delay command", zorder=4)
        style(axis, label, ylim)
    axes[0].legend(fontsize=11.5, loc="center right", framealpha=0.94)
    axes[4].legend(fontsize=11.5, loc="upper right", framealpha=0.94)
    axes[-1].set_xlabel("Time from the reversal (ns)", fontsize=13)
    fig.suptitle(f"io_buf  |  short high  |  {WIDTH_PS} ps  |  "
                 "the transport-delay command and its dead zone",
                 fontsize=17, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.978))
    fig.savefig(out / "05_delay_cmd_dead_zone.png", dpi=DPI)
    plt.close(fig)

    print(f"io_buf short high {WIDTH_PS} ps")
    print(f"  fitted delays: pu_off {PU_OFF_DELAY:.4f} ns, pd_on {PD_ON_DELAY:.4f} ns"
          f"  -> gap {PD_ON_DELAY - PU_OFF_DELAY:.3f} ns")
    if span:
        print(f"  measured dead zone: +{span[0]:.3f} to +{span[1]:.3f} ns "
              f"({span[1] - span[0]:.3f} ns wide)")
        m = (delay["rel_ns"] >= span[0]) & (delay["rel_ns"] <= span[1])
        print(f"    inside it: Ku {delay['ku'][m].min():+.4f} to {delay['ku'][m].max():+.4f},"
              f"  Kd {delay['kd'][m].min():+.4f} to {delay['kd'][m].max():+.4f}")
    for name, d in (("edge-integrating", shipped), ("transport-delay", delay)):
        hold = (d["rel_ns"] >= 2.60) & (d["rel_ns"] <= 2.95)
        print(f"  {name:<18} settled GUPTARGET {d['guptarget'][hold].mean():+.5f}")
    print(f"\nwrote {out.resolve()}\\05_delay_cmd_dead_zone.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
