#!/usr/bin/env python3
"""Can C_comp be recovered from the IBIS file alone, from the Ku overshoot?

Ku is the fraction of the pull-up's own I-V curve the buffer is using, so it cannot exceed 1.
`solve_k_params_output` subtracts the C_comp displacement current before solving, and a larger
C_comp books more of the pad current as device current: the overshoot GROWS with C_comp (at
C_comp = 0 the peak Ku is exactly 1). The file therefore gives an upper bound, not a point
estimate - and it needs nothing but the file: no probed gate, no transistor netlist.

This sweeps C_comp per buffer, records max Ku on the rising solve and max Kd on the falling
one, and reports the largest C_comp whose peak is still within a tolerance of 1, against the
value declared in the file and the loop-measured value the track-1 builds use
(gate_physics_2026-09-08).

Output: results/ccomp_from_file_2026-09-22/ (csv, figure, its FINDINGS.md is written by hand).

    py -3.14 scripts/ccomp_from_file.py
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
import gate_ramp_prototype as gp  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from stage_count_from_file import BUFFERS  # noqa: E402  (the loop-measured C_comp per buffer)

OUT = ROOT / "results" / "ccomp_from_file_2026-09-22"
GRID = np.concatenate([np.arange(0.0, 2.0, 0.005), np.arange(2.0, 12.001, 0.02)])   # pF


def peak(data, cc_pf: float) -> tuple[float, float]:
    """(max Ku on the rising solve, max Kd on the falling solve) at this C_comp."""
    data.c_comp = [cc_pf * 1e-12] * 3
    ku = pb.solve_k_params_output(data, corner=1, waveform_type="Rising")[:, 1]
    kd = pb.solve_k_params_output(data, corner=1, waveform_type="Falling")[:, 2]
    return float(np.nanmax(ku)), float(np.nanmax(kd))


def largest_within(cc: np.ndarray, y: np.ndarray, level: float) -> float:
    """The largest C_comp whose peak coefficient is still <= level, interpolated.

    The overshoot grows with C_comp (the solve subtracts the displacement current, so a larger
    C_comp books more current as device current), so this is the upper bound the file puts on
    C_comp at that tolerance - not a point where the overshoot vanishes."""
    ok = np.where(y <= level)[0]
    if not len(ok):
        return float("nan")
    j = int(ok[-1])                      # the last C_comp still within tolerance
    if j == len(cc) - 1:
        return float(cc[j])              # the sweep never leaves the tolerance
    return float(np.interp(level, [y[j], y[j + 1]], [cc[j], cc[j + 1]]))


TOLS = (0.01, 0.02, 0.05, 0.10)


def knee(cc: np.ndarray, y: np.ndarray) -> float:
    """Where the overshoot starts: the rising branch extrapolated back to 1, as a threshold
    voltage is extracted. No tolerance to choose."""
    m = (y >= 1.05) & (y <= 1.35)
    if m.sum() < 5:
        return float("nan")
    a, b = np.polyfit(cc[m], y[m], 1)
    return float((1.0 - b) / a)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows, curves = [], {}
    for dev, (sup, ibis) in gp.VARIANTS.items():
        model, comp = gp.ibis_names(ibis)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
        declared = float(np.asarray(data.c_comp).ravel()[0]) * 1e12
        loop = BUFFERS[dev]["cc"]
        ku = np.array([peak(data, c)[0] for c in GRID])
        kd = np.array([peak(data, c)[1] for c in GRID])
        curves[dev] = (ku, kd, declared, loop)
        at = lambda y, c: float(np.interp(c, GRID, y)) if c else float("nan")  # noqa: E731
        r = dict(buffer=dev, declared_pF=round(declared, 3), loop_pF=loop if loop else "",
                 max_ku_at_0=round(ku[0], 3), max_ku_at_declared=round(at(ku, declared), 3),
                 max_ku_at_loop=round(at(ku, loop), 3) if loop else "",
                 max_kd_at_declared=round(at(kd, declared), 3),
                 max_kd_at_loop=round(at(kd, loop), 3) if loop else "")
        r["knee_ku_pF"] = round(knee(GRID, ku), 2)
        r["knee_kd_pF"] = round(knee(GRID, kd), 2)
        # the tighter of the two is the binding constraint; on these 12 buffers that is always Ku
        r["knee_pF"] = round(min(r["knee_ku_pF"], r["knee_kd_pF"]), 2)
        for tol in TOLS:
            r[f"ku_bound_{tol:g}_pF"] = round(largest_within(GRID, ku, 1 + tol), 2)
            r[f"kd_bound_{tol:g}_pF"] = round(largest_within(GRID, kd, 1 + tol), 2)
        rows.append(r)
        print(f"  {dev:13s} declared {declared:5.2f}  loop {str(loop):>4s}  "
              f"bound from Ku at 1 %/2 %/5 %: " + " ".join(f"{r[f'ku_bound_{t:g}_pF']:5.2f}" for t in TOLS[:3])
              + f"   knee Ku/Kd {r['knee_ku_pF']:.2f}/{r['knee_kd_pF']:.2f}"
              + f"   max Ku {at(ku, declared):.2f} at declared", flush=True)
    with (OUT / "ccomp_from_file.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with (OUT / "ccomp_curves.csv").open("w", newline="") as fh:       # the sweep itself, for re-use
        w = csv.writer(fh)
        w.writerow(["buffer", "c_comp_pF", "max_ku", "max_kd"])
        for dev, (ku, kd, _d, _l) in curves.items():
            w.writerows([[dev, f"{c:g}", f"{a:.4f}", f"{b:.4f}"] for c, a, b in zip(GRID, ku, kd)])

    fig, axes = plt.subplots(3, 4, figsize=(16.5, 9.5), sharey=True)
    for ax, (dev, (ku, kd, declared, loop)) in zip(axes.ravel(), curves.items()):
        ax.plot(GRID, ku, color="#C0392B", lw=1.8, label="max Ku (rising solve)")
        ax.plot(GRID, kd, color="#2E86C1", lw=1.8, label="max Kd (falling solve)")
        ax.axhline(1.0, color="#555555", ls="--", lw=1.1)
        ax.axvline(declared, color="#E67E22", lw=1.4, label=f"declared {declared:.2f} pF")
        if loop:
            ax.axvline(loop, color="#27AE60", lw=1.4, ls=":", label=f"loop-measured {loop} pF")
        ax.set_xlim(0, min(GRID[-1], max(declared, loop or 0) * 1.6 + 0.6))
        ax.set_ylim(0.7, 2.0)
        ax.set_title(dev, fontweight="bold", fontsize=11)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7.5, loc="upper right")
    for ax in axes[-1]:
        ax.set_xlabel("C_comp (pF)")
    for ax in axes[:, 0]:
        ax.set_ylabel("peak solved coefficient")
    fig.suptitle("C_comp from the file alone: above the knee, the solved Ku exceeds 1 - which is impossible",
                 fontweight="bold", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT / "ccomp_from_file.png", dpi=160)
    plt.close(fig)
    print(f"wrote {OUT / 'ccomp_from_file.csv'} and ccomp_from_file.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
