# -*- coding: utf-8 -*-
"""Does the probe's linear_const baseline reproduce cl.fit_chain_shared?

ex2 K=3 reproduced the committed CSV exactly (0.756 vs 0.755 at the deepest width).
inv_chain K=7 did not: 0.701 against the CSV's 0.672, at identical full-swing rms
0.0032. Either the probe's harness differs, or the inv_chain fit sits on the
pulse-swallowing cliff where a 1e-16 integrator difference amplifies.

Run cl's OWN fitter now and see which number it produces today.
"""
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\sh3qm\code\ibis_comparison")
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np                              # noqa: E402
import current_limited_stage_model as cl        # noqa: E402
import predriver_stage_probe as psp             # noqa: E402
import device_taper_probe as dt                 # noqa: E402

for dev, K, gate in (("ex2", 3, "v(xdut.n4)"), ("inv_chain", 7, "v(xdut.vout7)")):
    grid, runs = cl.load(dev)
    full = runs["full"]
    u_name = psp.STAGES[dev][0]
    widths = sorted(k for k in runs if k != "full")

    c_cl, prms_cl = cl.fit_chain_shared(full[u_name], full[gate], K)
    c_dt, prms_dt = dt.fit_shared(full[u_name], full[gate], K, "linear_const")

    print(f"\n=== {dev}, K={K} ===")
    print(f"  cl.fit_chain_shared   rms {c_cl:.5f}  "
          f"s_up {prms_cl[0][0]:.3f} s_dn {prms_cl[0][1]:.3f} vt {prms_cl[0][2]:.3f} x_lin {prms_cl[0][3]:.3f}")
    print(f"  probe linear_const    rms {c_dt:.5f}  "
          f"s_up {prms_dt[0][0]:.3f} s_dn {prms_dt[0][1]:.3f} vt {prms_dt[0][2]:.3f} x_lin {prms_dt[0][3]:.3f}")

    print(f"  {'W':>6}{'measured':>10}{'cl':>9}{'probe':>9}{'committed CSV':>15}")
    csv = {("ex2", 810): 0.755, ("ex2", 830): 0.782, ("ex2", 858): 0.813,
           ("ex2", 895): 0.847, ("ex2", 975): 0.898,
           ("inv_chain", 104): 0.672, ("inv_chain", 106): 0.820, ("inv_chain", 111): 0.909,
           ("inv_chain", 119): 0.960, ("inv_chain", 135): 0.987}
    for W in widths:
        a = cl.simulate_chain(runs[W][u_name], prms_cl).max()
        b = dt.simulate_chain(runs[W][u_name], prms_dt, "linear_const").max()
        print(f"  {W:>6}{runs[W][gate].max():>10.3f}{a:>9.3f}{b:>9.3f}"
              f"{csv.get((dev, W), float('nan')):>15.3f}")

    # same parameters through both integrators - isolates fitter from integrator
    same = max(float(np.abs(cl.simulate_chain(runs[W][u_name], prms_cl)
                            - dt.simulate_chain(runs[W][u_name], prms_cl, "linear_const")).max())
               for W in widths)
    print(f"  same params, both integrators: max diff {same:.2e}")
