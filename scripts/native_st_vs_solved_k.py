#!/usr/bin/env python3
"""Is native's St_pu(t) the same curve as the offline two-fixture solve?

This is the question `native_vs_solved_ku.py` posed and never answered. It
separates the two remaining explanations for why native's Ku sits +15 ps from the
transistor under stress while ours sits +80:

* if native's St_pu(t) **equals** the offline solve on a clean full swing, then
  the stored trajectory is identical and every difference under stress is in how
  each model is *entered and driven*;
* if they **differ even at full swing**, the difference is in the solve or in the
  replay itself, and the stress case is a red herring.

`solve_k_params_output` returns [time, k_u, k_d] with **time in seconds** while
every waveform in this study is in ns -- the unit trap that produced a saturated
square wave the first time this solve was used.

The B-element run already exists (results/native_vs_solved_ku_2026-09-04), driven
at full swing into the same 50 ohm + 2 pF bench with `xv_pu=ku` / `xv_pd=kd`
exposing St_pu and St_pd as nodes.

    py -3.14 scripts/native_st_vs_solved_k.py
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

R = ROOT / "results"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
NATIVE = R / "native_vs_solved_ku_2026-09-04" / "run.tr0"
OUT = R / "native_st_vs_solved_2026-09-07"

MODEL, COMPONENT = "driver", "MCM Driver 1"
RISE_NS, FALL_NS = 5.0, 15.0
C_NAT, C_SOLVE = "#2B6CA3", "#B03060"


def solved(kind: str):
    """[time_ns, Ku, Kd] from the two recorded fixtures."""
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    k = pb.solve_k_params_output(data, corner=1, waveform_type=kind)
    return k[:, 0] * 1e9, k[:, 1], k[:, 2]   # seconds -> ns


def lag_ps(grid, ref, y, max_ps=400):
    """Shift y that best aligns it to ref, plus the residual after aligning."""
    step = grid[1] - grid[0]
    n = int((max_ps * 1e-3) / step)
    span = float(ref.max() - ref.min())
    best = (0, 1e9)
    for s in range(-n, n + 1):
        shifted = np.interp(grid, grid + s * step, y)
        err = float(np.sqrt(np.mean((shifted - ref) ** 2)))
        if err < best[1]:
            best = (s, err)
    return -best[0] * step * 1e3, best[1] / span


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tr = sl.parse_hspice_tr0(NATIVE)
    tn = sl.time_ns(tr)
    nat = {"ku": sl.trace(tr, "ku"), "kd": sl.trace(tr, "kd"),
           "pad": sl.trace(tr, "pad")}

    print("  Native St_pu / St_pd against the offline two-fixture solve,")
    print("  full swing, io_buf.  Time is measured from each edge.\n")
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    verdict = []
    for col, (kind, edge) in enumerate((("Rising", RISE_NS), ("Falling", FALL_NS))):
        ts, ku, kd = solved(kind)
        span = min(float(ts.max()), 6.0)
        g = np.arange(0.0, span, 0.002)
        for row, (name, sv) in enumerate((("ku", ku), ("kd", kd))):
            a = axes[row][col]
            s = np.interp(g, ts, sv)
            n = np.interp(g, tn - edge, nat[name])
            lag, res = lag_ps(g, s, n)
            mx = float(np.abs(n - s).max())
            rms = float(np.sqrt(np.mean((n - s) ** 2)))
            verdict.append((kind, name, lag, res, mx, rms))
            print(f"    {kind:<8} {name}: max|diff| {mx:.4f}   rms {rms:.4f}   "
                  f"best lag {lag:+.0f} ps (residual {res:.3f})")
            a.plot(g, s, color=C_SOLVE, lw=3.0, label="offline two-fixture solve")
            a.plot(g, n, color=C_NAT, lw=1.8, ls="--", label="native St (HSPICE)")
            a.set_title(f"{kind} edge, {name.upper()}", fontweight="bold")
            a.set_xlabel("Time from the edge (ns)")
            a.set_ylabel(name.upper())
            a.grid(alpha=0.3)
            a.legend(fontsize=9)
    fig.suptitle("Native's stored trajectory against the offline solve, full swing",
                 fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "native_st_vs_solved.png", dpi=200)
    plt.close(fig)

    # max|diff| is dominated by the time offset, so it is the residual *after*
    # alignment that says whether the shape is the same curve.
    worst_res = max(v[3] for v in verdict)
    lags = [v[2] for v in verdict]
    print(f"\n  Worst residual after alignment: {worst_res:.4f} of span")
    print(f"  Lags: {min(lags):+.0f} to {max(lags):+.0f} ps")
    if worst_res < 0.02:
        print("  -> SAME CURVE, offset in time. Native replays the offline solve.")
    else:
        print("  -> different shape, not merely offset.")
    print(f"  figure: {OUT / 'native_st_vs_solved.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
