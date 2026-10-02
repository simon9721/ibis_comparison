# -*- coding: utf-8 -*-
"""Quick look: can the map shape be chosen from the IBIS file?

For each of several shapes (v_t,map, a) the stage law is fitted through that shape to the
file's full-swing K_u(t) (the fit of eq. 26, x_lin = 0.45). If the residual has a clear
minimum near the shape measured with a probe, the file carries information about the map;
if it is flat, it does not, and the shape has to come from the stressed run.

    py -3.14 shape_from_file.py target ex2            # cache the file's K_u(t) once
    py -3.14 shape_from_file.py fit ex2 0.5 0.7       # one shape -> shape_ex2_0.5_0.7.json
    py -3.14 shape_from_file.py collect
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(p))
HERE = Path(__file__).resolve().parent / "shape_from_file"
HERE.mkdir(exist_ok=True)

MEASURED = {"ex2": (0.57, 0.64), "inv_chain": (0.49, 0.60)}       # fitted to the probed map
SELECTED = {"ex2": (0.5, 0.7), "inv_chain": (0.4, 0.9)}           # chosen by the stressed run


def main():
    cmd = sys.argv[1]
    if cmd == "target":
        import device_taper_ku as dku
        dev = sys.argv[2]
        grid, u, target = dku.shipped_ku(dev, dku.BUFFERS[dev]["cc"])
        np.savez(HERE / f"target_{dev}.npz", u=u, target=target)
        print("cached", dev)
    elif cmd == "fit":
        import device_taper_ku as dku
        import physics_map_gate_from_ibis as pm
        dev, vt, a = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
        d = np.load(HERE / f"target_{dev}.npz")
        c, (s_up, s_dn, v, _) = dku.fit_ku(d["u"], d["target"], lambda g: pm.prior(g, vt, a),
                                           dku.BUFFERS[dev]["K"], "linear_const", fix_xlin=0.45)
        out = dict(dev=dev, vt_map=vt, a=a, rms=c, s_up=s_up, s_dn=s_dn, vt=v)
        (HERE / f"shape_{dev}_{vt:g}_{a:g}.json").write_text(json.dumps(out), encoding="utf-8")
        print(out)
    else:
        for dev in ("ex2", "inv_chain"):
            rows = sorted((json.loads(p.read_text()) for p in HERE.glob(f"shape_{dev}_*.json")),
                          key=lambda r: r["rms"])
            print(f"\n{dev}: measured map {MEASURED[dev]}, selected by the stressed run {SELECTED[dev]}")
            print(f"  {'v_t,map':>8}{'a':>6}{'Ku rms':>9}{'s_up':>8}{'vt':>7}")
            for r in rows:
                print(f"  {r['vt_map']:>8.2f}{r['a']:>6.2f}{r['rms']:>9.4f}{r['s_up']:>8.2f}{r['vt']:>7.3f}")
            print(f"  spread: best {rows[0]['rms']:.4f}, worst {rows[-1]['rms']:.4f} "
                  f"({rows[-1]['rms'] / rows[0]['rms']:.2f}x)")


if __name__ == "__main__":
    main()
