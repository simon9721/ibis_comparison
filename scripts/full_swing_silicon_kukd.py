#!/usr/bin/env python3
"""Solve the transistor's Ku/Kd at full swing -- the reference that never existed.

Two open items in `pu_off_scale_2026-09-07` both close on this one run:

* every full-swing comparison there leans on native, because the stress matrix
  carries `silicon_ku`/`silicon_kd` for stressed cases only;
* the reversal overshoot is an objective the sweep trades against, and nobody has
  checked whether the **transistor's own coefficient** overshoots at the start of
  a fall. If it does not, "preserve the overshoot" is the wrong objective and the
  `pu_off` conflict may dissolve rather than needing an architectural fix.

Two HSPICE runs of the transistor into the IBIS fixtures (50 ohm to 0 V and to
VCC) on the canonical `long_control` case -- rise at 5 ns, fall at 15 ns, the same
stimulus as `defect_b_full_swing_2026-09-03`.

Solved at five grids, because `silicon_kukd_conditioning_2026-09-07` showed the
excursion near a reversal is set by the `C_comp dV/dt` finite difference and does
not converge. Any claim made here has to survive that check or be dropped.

    py -3.14 scripts/full_swing_silicon_kukd.py
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
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from extract_silicon_kukd import run_fixture, solve_silicon_kukd  # noqa: E402

R = ROOT / "results"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
NATIVE = R / "native_vs_solved_ku_2026-09-04" / "run.tr0"
SWEEP = R / "pu_off_conflict_2026-09-07"
OUT = R / "full_swing_silicon_kukd_2026-09-07"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY = 3.3
RISE_NS, FALL_NS = 5.0, 15.0
GRIDS = (None, 1.0, 2.0, 5.0, 10.0)
C_SI, C_NAT, C_SOLVE = "#111111", "#2B6CA3", "#B03060"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    device = next(d for d in base.DEVICES if d.device_id == "io_buf")
    # The campaign's own full-swing control: 10 ns high, 22 ns stop, 50 ps edges.
    case = base.PulseCase("e50p_long_control", 0.050, "rise_fall", 10.0, 22.0)
    hspice = Path(default_hspice())

    runs = {}
    for tag, v_fix in (("vfix_0", 0.0), ("vfix_vcc", SUPPLY)):
        print(f"  running transistor into {tag} ...")
        runs[tag] = run_fixture(device, case, v_fix, OUT / tag, hspice, 1800)
        print(f"    {len(runs[tag])} samples, "
              f"pad {runs[tag][:, 1].min():.3f}..{runs[tag][:, 1].max():.3f} V")

    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)

    print("\n  Transistor Ku at the FALLING edge, by grid. The question is whether"
          "\n  it overshoots above its pre-reversal value the way native's does"
          "\n  (native peaks 1.1943 at +83 ps; the offline table solve does too).\n")
    print(f"    {'grid':>8}{'Ku before':>12}{'Ku peak':>10}{'t peak ps':>11}"
          f"{'overshoot':>11}{'cond max':>10}")
    sols = {}
    for ups in GRIDS:
        sol = solve_silicon_kukd(data, runs["vfix_0"], runs["vfix_vcc"], SUPPLY,
                                 uniform_ps=ups)
        t = sol[:, 0] * 1e9 - FALL_NS
        sols[ups] = (t, sol[:, 1], sol[:, 2], sol[:, 3])
        before = float(np.median(sol[(t > -0.30) & (t < -0.05), 1]))
        m = (t > -0.02) & (t < 0.30)
        i = int(np.nanargmax(np.where(m, sol[:, 1], -9e9)))
        cmax = float(np.nanmax(sol[m, 3]))
        print(f"    {'union' if ups is None else f'{ups:g} ps':>8}{before:>12.4f}"
              f"{sol[i, 1]:>10.4f}{t[i]*1e3:>11.0f}"
              f"{sol[i, 1]-before:>11.4f}{cmax:>10.1f}")

    print("\n  Convergence check: spread across the 1/2/5/10 ps solves, by slice.")
    print(f"    {'window ps':>12}{'Ku spread':>12}{'Kd spread':>12}")
    for lo in (0, 50, 90, 150, 250):
        gg = np.arange(lo / 1000, (lo + 50) / 1000, 0.002)
        ku = np.array([np.interp(gg, sols[u][0], sols[u][1]) for u in GRIDS[1:]])
        kd = np.array([np.interp(gg, sols[u][0], sols[u][2]) for u in GRIDS[1:]])
        print(f"    {f'{lo}..{lo+50}':>12}{ku.std(axis=0).mean():>12.4f}"
              f"{kd.std(axis=0).mean():>12.4f}")

    tn = sl.parse_hspice_tr0(NATIVE)
    tnat = sl.time_ns(tn) - FALL_NS
    print("\n  Against native and our builds, on the 5 ps solve:")
    print(f"    {'t-fall ps':>10}{'transistor':>12}{'native':>9}"
          f"{'ours x0.70':>12}{'ours x0.10':>12}")
    ours = {}
    for tag in ("s0.70", "s0.10"):
        raw = sl.parse_ngspice_raw(SWEEP / tag / "full" / "run.raw")
        ours[tag] = (sl.time_ns(raw) - FALL_NS, sl.signal(raw, "v(x1.ku)"))
    t5, ku5 = sols[5.0][0], sols[5.0][1]
    for p in (-0.050, 0.000, 0.030, 0.070, 0.090, 0.150, 0.250, 0.400):
        print(f"    {p*1e3:>10.0f}{float(np.interp(p, t5, ku5)):>12.4f}"
              f"{float(np.interp(p, tnat, sl.trace(tn, 'ku'))):>9.4f}"
              + "".join(f"{float(np.interp(p, *ours[t])):>12.4f}"
                        for t in ("s0.70", "s0.10")))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    a = axes[0]
    for ups, style in zip(GRIDS, ("-", "-", "-", "-", "-")):
        t, ku, _, _ = sols[ups]
        m = (t > -0.35) & (t < 0.8)
        a.plot(t[m], ku[m], lw=2.0, ls=style,
               label=f"transistor, {'union' if ups is None else f'{ups:g} ps'}")
    a.axvline(0, color="#8A8A8A", ls="--", lw=1.2)
    a.set_title("Transistor Ku at the falling edge, by grid",
                fontsize=13, fontweight="bold")
    a.set_xlabel("Time from the falling edge (ns)")
    a.set_ylabel("Ku")
    a.grid(alpha=0.3)
    a.legend(fontsize=9)

    b = axes[1]
    t, ku, _, _ = sols[5.0]
    m = (t > -0.35) & (t < 0.8)
    b.plot(t[m], ku[m], color=C_SI, lw=3.0, label="transistor (5 ps solve)")
    mn = (tnat > -0.35) & (tnat < 0.8)
    b.plot(tnat[mn], sl.trace(tn, "ku")[mn], color=C_NAT, lw=2.0,
           label="native St_pu")
    for tag, colour, lab in (("s0.70", "#C05621", "ours, pu_off x0.70"),
                             ("s0.10", "#2E8B57", "ours, pu_off x0.10")):
        tt, y = ours[tag]
        mm = (tt > -0.35) & (tt < 0.8)
        b.plot(tt[mm], y[mm], color=colour, lw=2.0, ls="--", label=lab)
    b.axvline(0, color="#8A8A8A", ls="--", lw=1.2)
    b.axhline(1.0, color="#999", lw=0.8)
    b.set_title("Full swing: does the transistor's Ku overshoot?",
                fontsize=13, fontweight="bold")
    b.set_xlabel("Time from the falling edge (ns)")
    b.grid(alpha=0.3)
    b.legend(fontsize=9)
    fig.suptitle("The transistor's own coefficients at full swing",
                 fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "full_swing_silicon_kukd.png", dpi=200)
    plt.close(fig)
    print(f"\n  figure: {OUT / 'full_swing_silicon_kukd.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
