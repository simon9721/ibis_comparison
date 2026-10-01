# -*- coding: utf-8 -*-
"""Does the stage law reproduce the alpha-power-law paper's own delay formula?

Sakurai & Newton 1990, eq. (5):

    t_pHL = (1/2 - (1 - nu_T)/(1 + alpha)) * t_T  +  C_L V_DD / (2 I_D0)

for an inverter discharged by one device under a linear input ramp of duration t_T, with
the opposing device neglected. In stage-law terms nu_T = vt, alpha = p and
C_L V_DD / I_D0 = 1/s, so the formula predicts the 50 %-to-50 % delay of one stage of (19).

Two columns: the opposing device switched off (the paper's assumption) and both devices
present (the stage law as used). The formula is stated to hold while the input ramp is
shorter than about three output transition times; the last row is outside that.

    py -3.14 results/stage_law_doc_2026-10-01/check_delay_formula.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import current_limited_stage_model as cl      # noqa: E402

S, VT, XLIN, P = 2.19, 0.30, 0.45, 1.0        # /ns; alpha = p = 1


def main():
    t = np.arange(-0.5, 6.0, cl.DT)
    print(f"s = {S}/ns, vt = {VT}, x_lin = {XLIN}, p = alpha = {P:g}")
    print(f"{'t_T (ns)':>9}{'eq. (5)':>9}{'one device':>12}{'both devices':>14}")
    worst = 0.0
    for tT in (0.05, 0.2, 0.4, 0.8, 1.5):
        u = np.clip(t / tT, 0, 1)
        formula = (0.5 - (1 - VT) / (1 + P)) * tT + 1.0 / (2 * S)
        one = cl.simulate(u, S, 1e-9, VT, XLIN, P)
        two = cl.simulate(u, S, S, VT, XLIN, P)
        d = lambda v: float(np.interp(0.5, v, t)) - tT / 2      # noqa: E731
        print(f"{tT:>9.2f}{formula:>9.3f}{d(one):>12.3f}{d(two):>14.3f}")
        if tT <= 0.8:
            worst = max(worst, abs(d(one) - formula), abs(d(two) - formula))
    print(f"\nworst |difference| for t_T <= 0.8 ns: {worst * 1e3:.1f} ps")
    return worst


if __name__ == "__main__":
    main()
