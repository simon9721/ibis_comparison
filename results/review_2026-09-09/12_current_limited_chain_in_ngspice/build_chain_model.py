#!/usr/bin/env python3
"""The recipe as one command: IBIS file in, current-limited-chain driver.sub out.

    1. generate the converter's model (input threshold clamped to the supply)
    2. run it once at full swing to read its gate-part Ku(t) / Kd(t)
    3. fit K identical current-limited stages so that PRIOR(chain) reproduces
       that Ku(t) (K = smallest on the rms plateau, or --K)
    4. optional one stressed observation (--calib W_PS GATE_MAX) to place the
       drive law under a partial input
    5. write the model: chain -> GUP, GDN = 1 - GUP, prior maps on the last stage

    py -3.14 scripts/build_chain_model.py --ibis path.ibs --supply 3.3 --family ex2 --out driver_chain.sub
    py -3.14 scripts/build_chain_model.py --ibis path.ibs --supply 1.8 --family inv --calib 104 0.879 --out driver_chain.sub
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from pybis2spice import pybis2spice as pb, subcircuit, chain_command as cc  # noqa: E402
import gate_ramp_prototype as gp  # noqa: E402
import gate_cascade_prototype as gc  # noqa: E402
import gate_chain_prototype as gch  # noqa: E402
import physics_map_gate_from_ibis as pm  # noqa: E402

# family priors (three-parameter map, fitted to the base buffers' silicon maps 2026-09-10)
FAMILY_PRIOR = {"ex2": (0.52, 1.10, 0.91), "inv": (0.42, 1.15, 0.87), "io_buf": (0.51, 0.75, 1.00)}
FAMILY_KS = {"ex2": [2, 3, 4], "inv": [5, 7, 9], "io_buf": [1, 2, 3]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ibis", required=True, type=Path)
    ap.add_argument("--supply", type=float, required=True)
    ap.add_argument("--family", choices=list(FAMILY_PRIOR), default="ex2")
    ap.add_argument("--prior3", type=float, nargs=3, default=None)
    ap.add_argument("--ccomp", type=float, default=None, help="override C_comp (pF) in the IBIS before building")
    ap.add_argument("--K", type=int, default=None)
    ap.add_argument("--fix-xlin", type=float, default=0.45)
    ap.add_argument("--calib", type=float, nargs=2, default=None, metavar=("W_PS", "GATE_MAX"))
    ap.add_argument("--calib-pad", nargs=2, default=None, metavar=("PAD_CSV", "W_PS"),
                    help="one stressed transistor PAD run: CSV with time_ns,pad_v columns (or two columns), pulse width in ps; the model's threshold is bisected in ngspice to match its peak")
    ap.add_argument("--edge-ps", type=float, default=50.0, help="input edge the model will be driven with (sets the fit's step time)")
    ap.add_argument("--work", type=Path, default=ROOT / "results" / "build_chain_model")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    work = args.work / args.ibis.stem
    work.mkdir(parents=True, exist_ok=True)
    ibis = args.ibis
    if args.ccomp:
        txt = re.sub(r"^C_comp\s+.*$", f"C_comp {args.ccomp:.4f}pF {args.ccomp:.4f}pF {args.ccomp:.4f}pF",
                     ibis.read_text(errors="ignore"), count=1, flags=re.M)
        ibis = work / "input_ccomp.ibs"
        ibis.write_text(txt, encoding="utf-8")
    model, comp = gp.ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(work / "driver_shipped.sub"))
    ship = (work / "driver_shipped.sub").read_text(encoding="utf-8")
    gp.VARIANT_NAME = "__build__"
    gp.EDGE_PS["__build__"] = args.edge_ps
    full_ship = gp.run_ours(work / "full", ship, args.supply, 10.0)

    vt, al, gs = args.prior3 or FAMILY_PRIOR[args.family]
    gch.PRIOR_FN = lambda g: pm.prior3(g, vt, al, gs)
    Ks = [args.K] if args.K else FAMILY_KS[args.family]
    print(f"  {args.ibis.name}: prior3 vt={vt} alpha={al} gs={gs}; chain fit in the Ku domain:")
    fits = gch.fit_chain_ku(full_ship, vt, al, Ks, x_lin_fixed=args.fix_xlin)
    K = args.K or gch.pick_K(fits)
    c, prm = fits[K]
    print(f"  -> K = {K}: s_up {prm[0]:.3f} s_dn {prm[1]:.3f} vt {prm[2]:.3f} x_lin {prm[3]:.3f} (full-swing rms {c:.4f})")
    if args.calib:
        prm = gch.calibrate(prm, K, args.calib[0], args.calib[1])
    rise, fall, kd_on, kd_off = gch.prior_maps(full_ship, vt, al)
    if args.calib_pad:
        import numpy as np
        arr = np.loadtxt(args.calib_pad[0], delimiter=",", skiprows=1) if "," in Path(args.calib_pad[0]).read_text()[:200] else np.loadtxt(args.calib_pad[0])
        ref = (np.asarray(arr[:, 0], float), np.asarray(arr[:, 1], float))
        if ref[0].max() < 1e-6:                     # seconds -> ns
            ref = (ref[0] * 1e9, ref[1])
        w = float(args.calib_pad[1]) / 1e3
        prm = gch.calibrate_pad(ship, K, prm, None, args.supply, (rise, fall, kd_on, kd_off), ref, w, work / "calib_pad", f"W={args.calib_pad[1]} ps")
    # the converter-side module does the text work (chain + prior maps)
    import numpy as np
    text = cc.patch_chain(ship, K, prm, args.supply)
    tf, kb, kd = full_ship["t"], full_ship["kugate_base"], full_ship["kdgate_base"]
    text = cc.patch_prior_maps(text, float(np.interp(4.5, tf, kb)), float(np.interp(12.0, tf, kb)),
                               float(np.interp(4.5, tf, kd)), float(np.interp(12.0, tf, kd)), gch.PRIOR_FN)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
