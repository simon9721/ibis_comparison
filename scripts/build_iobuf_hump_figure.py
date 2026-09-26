#!/usr/bin/env python3
"""io_buf's pull-down release hump: the transistor's walks earlier under stress, the model's does not.

Left panel the transistor, right panel the step-replay model with a 3-stage current-limited
pull-down chain, five pulse widths each, plotted from the input reversal so the two panels are
directly comparable. Reads existing runs only; nothing is simulated.

    py -3.14 scripts/build_iobuf_hump_figure.py
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
import gate_ramp_prototype as gp  # noqa: E402

BUILD = ROOT / "results/gate_step_prototype_2026-09-10/io_buf/real_prior_slots3_gdnchain3_k1.0559"
OUT = ROOT / "results/track2_train_check_2026-09-13/figs"


def hump(t, v, rev):
    g = np.arange(rev + 0.9, rev + 3.2, 0.002)
    y = np.interp(g, t, v)
    i = int(np.argmax(y))
    return float(g[i] - rev), float(y[i])


def main() -> int:
    gp.VARIANT_NAME = "io_buf"
    cs = gp.cases("io_buf")
    cmap = plt.get_cmap("viridis")
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.7), sharey=True)
    for k, (depth, w, case) in enumerate(cs):
        col = cmap(k / max(1, len(cs) - 1))
        rev = gp.RISE_NS + w
        g = np.arange(rev + 0.8, rev + 3.3, 0.002)
        t_si, si = gp.tr0_pad(case / "run.tr0")
        ts, _ = hump(t_si, si, rev)
        ax[0].plot(g - rev, np.interp(g, t_si, si), color=col, lw=2.2,
                   label=f"{depth} ps input: hump at {ts:.3f} ns")
        raw = sl.parse_ngspice_raw(BUILD / f"d{depth}" / "run.raw")
        tm, vm = sl.time_ns(raw), np.asarray(raw["v(out)"], float)
        tmo, _ = hump(tm, vm, rev)
        ax[1].plot(g - rev, np.interp(g, tm, vm), color=col, lw=2.2,
                   label=f"{depth} ps input: hump at {tmo:.3f} ns")
    for a, ttl in zip(ax, ("a. transistor: the hump walks 202 ps earlier as the pulse shortens",
                           "b. model: the hump sits at 2.06 ns whatever the pulse does")):
        a.set_xlim(0.8, 3.3)
        a.set_ylim(-0.005, 0.075)
        a.grid(alpha=0.3)
        a.set_xlabel("time from the input reversal (ns)")
        a.legend(fontsize=9, loc="upper right", framealpha=0.95)
        a.set_title(ttl, fontweight="bold", fontsize=11)
    ax[0].set_ylabel("pad (V)")
    fig.suptitle("io_buf: the pull-down path releasing. Same five pulses in both panels, plotted from the input reversal",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "iobuf_hump.png", dpi=160)
    plt.close(fig)
    print("wrote", OUT / "iobuf_hump.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
