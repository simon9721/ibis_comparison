#!/usr/bin/env python3
"""Is the two-fixture Ku/Kd solve ill-conditioned on ex2? Measured: no.

Native IBIS run the way IBIS intends -- `ramp_rwf=2`, two V-T tables -- produces a
dead pad on ex2 (0.03 V where the transistor reaches 1.47 V) and no warning.
s2ibispy's own two-fixture solve on the same tables returns max|Ku| of 1.28-1.83
and rejects every edge-rate candidate. Both are the same computation, so the
natural suspicion was that the 2x2 system is ill-conditioned.

At each instant the output equation is

    I_pad = Ku*I_pu(V) + Kd*I_pd(V) + clamps(V) + C_comp*dV/dt

and recording the transition into two fixtures gives two equations in (Ku, Kd):

    M(t) = [[I_pu(V_A(t)), I_pd(V_A(t))],
            [I_pu(V_B(t)), I_pd(V_B(t))]]

**The suspicion is wrong.** cond(M) over the recorded transition:

    ex2_base    2.5 median, 3.1 max        inv_base8   5.2 median, 5.4 max
    ex2_weak    1.9 median, 2.2 max        io_buf      2.7 median, 3.1 max

No buffer has a single sample above 100. ex2 is conditioned *better* than
inv_chain, which does not fail. So neither ex2's dead native pad nor its
out-of-range Ku can be blamed on a near-singular solve, and the mechanism for both
is still open. Ruling this out matters because it was about to be written up as
the explanation.

Kept as a standing negative result: re-run it if new buffers start failing the
selector's max|Ku| gate, to confirm conditioning is still not the cause.

    py -3.14 scripts/two_fixture_conditioning.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "tools" / "pybis2spice", ROOT / "scripts",
           ROOT / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402

OUT = ROOT / "results" / "two_fixture_conditioning_2026-09-04"

BUFFERS = [
    ("ex2_base", ROOT / "results/ex2_variants_2026-09-03/base/selection/tr1ps/ex2_base_tr1ps.ibs",
     "driver", "MCM Driver 1", "#C02626"),
    ("ex2_weak", ROOT / "results/ex2_variants_2026-09-03/weak/selection/tr1ps/ex2_weak_tr1ps.ibs",
     "driver", "MCM Driver 1", "#E06A6A"),
    ("inv_base8",
     ROOT / "results/inv_chain_variants_2026-09-02/base8/selection/tr1ps/invchain_base8_tr1ps.ibs",
     "driver2", "invchain", "#1B6B4F"),
    ("io_buf", ROOT / "buffers" / "models" / "io_buf.ibs", "driver", "MCM Driver 1", "#2B6CA3"),
]


def curves(d):
    """I_pu(V_pad), I_pd(V_pad) as callables.

    The [Pullup] table's voltage axis is IBIS-native -- the voltage *across* the
    device, Vcc - V_pad -- while [Pulldown] is already referenced to the pad.
    Checked against the data: ex2's I_pu is ~0 at axis 0 (pad at the rail) and
    -36 mA at axis 3.3 (pad at ground).
    """
    vcc = float(np.asarray(d.v_range).ravel()[0])
    pu, pd = np.asarray(d.iv_pullup), np.asarray(d.iv_pulldown)
    return (lambda v: np.interp(vcc - v, pu[:, 0], pu[:, 1]),
            lambda v: np.interp(v, pd[:, 0], pd[:, 1]))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4))
    print(f"{'buffer':<12}{'fixtures':<14}{'median cond':>13}{'p90':>10}{'max':>12}"
          f"{'% of samples':>14}")
    print(f"{'':<12}{'':<14}{'':>13}{'':>10}{'':>12}{'cond > 100':>14}")
    for name, path, model, comp, colour in BUFFERS:
        if not path.exists():
            print(f"{name:<12}  missing {path.name}")
            continue
        d = pb.DataModel(pb.get_ibis_model_ecdtools(str(path)),
                         model_name=model, component_name=comp)
        if len(d.vt_rising) < 2:
            print(f"{name:<12}  only {len(d.vt_rising)} rising waveform(s)")
            continue
        i_pu, i_pd = curves(d)
        wa, wb = d.vt_rising[0], d.vt_rising[1]
        a, b = np.asarray(wa.data), np.asarray(wb.data)
        t = a[:, 0]
        va, vb = a[:, 1], np.interp(t, b[:, 0], b[:, 1])

        conds = np.empty(len(t))
        for i in range(len(t)):
            M = np.array([[i_pu(va[i]), i_pd(va[i])],
                          [i_pu(vb[i]), i_pd(vb[i])]], dtype=float)
            conds[i] = np.linalg.cond(M) if np.all(np.isfinite(M)) else np.inf
        finite = conds[np.isfinite(conds)]
        fa = float(np.asarray(wa.v_fix).ravel()[0])
        fb = float(np.asarray(wb.v_fix).ravel()[0])
        print(f"{name:<12}{f'{fa:g} / {fb:g} V':<14}{np.median(finite):>13.1f}"
              f"{np.percentile(finite, 90):>10.1f}{finite.max():>12.1f}"
              f"{100 * np.mean(finite > 100):>13.1f}%")

        tn = (t - t[0]) * 1e9
        axes[0].semilogy(tn, np.clip(conds, 1, 1e6), color=colour, lw=1.8, label=name)
        axes[1].plot(va, vb, color=colour, lw=1.8, label=name)

    axes[0].axhline(100, color="#111", ls="--", lw=1.2)
    axes[0].set_xlabel("time through the recorded transition (ns)")
    axes[0].set_ylabel("cond(M)  —  log scale")
    axes[0].set_title("Conditioning of the two-fixture Ku/Kd solve", fontweight="bold")
    axes[0].grid(alpha=0.3, which="both")
    axes[0].legend(fontsize=9)
    axes[1].set_xlabel("pad voltage, fixture A (V)")
    axes[1].set_ylabel("pad voltage, fixture B (V)")
    axes[1].set_title("Do the two fixtures separate the operating point?", fontweight="bold")
    axes[1].grid(alpha=0.3)
    axes[1].legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "two_fixture_conditioning.png", dpi=170)
    plt.close(fig)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
