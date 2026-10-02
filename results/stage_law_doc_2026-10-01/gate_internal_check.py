# -*- coding: utf-8 -*-
"""Is the file-only model's INTERNAL gate close to the transistor's real gate?

The file-only model is judged at the pad. Its internal gate G_UP is never compared with
anything, and a wrong gate paired with a wrong map can still give the right pad. This
compares the two directly on the buffers whose gate was probed:

    model   v(x1.gup) of the selected file-only build (selector_from_one_run), in ngspice
    real    the probed predriver output (ex2 n4, inv_chain vout7), normalised rest -> settled
            (predriver_stages_2026-09-09, via current_limited_stage_model.load)

at full swing and at the five stressed widths.

    py -3.14 results/stage_law_doc_2026-10-01/gate_internal_check.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / ".codex_deps" / "presentation" / "python", ROOT / "tools" / "pybis2spice", ROOT / "scripts"):
    sys.path.insert(0, str(p))

import matplotlib                                   # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
import gate_ramp_prototype  # noqa: E402,F401  (first: binds pybis2spice before the deck modules add tools/ to the path)
import build_0924_deck_figures as b24               # noqa: E402
import current_limited_stage_model as cl            # noqa: E402
import spicelab as sl                               # noqa: E402

HERE = Path(__file__).resolve().parent
GATE = {"ex2": "v(xdut.n4)", "inv_chain": "v(xdut.vout7)"}


def model_gate(folder, which):
    raw = sl.parse_ngspice_raw(folder / which / "run.raw")
    return sl.time_ns(raw), sl.signal(raw, "v(x1.gup)"), sl.signal(raw, "v(x1.ku)")


def main():
    fig, axes = plt.subplots(2, 4, figsize=(11, 5.2))
    for r, dev in enumerate(("ex2", "inv_chain")):
        folder = b24._pick_build(dev)
        grid, runs = cl.load(dev)
        widths = sorted(k for k in runs if k != "full")
        print(f"\n=== {dev}: selected file-only build {folder.name}")
        print(f"  {'case':>8}{'real peak':>11}{'model peak':>12}{'diff':>8}{'rms':>8}{'lag (ps)':>10}")
        cases = [("full", "full")] + [(W, f"d{W}") for W in widths]
        for j, (key, which) in enumerate(cases):
            t, g, _ku = model_gate(folder, which)
            real = runs[key][GATE[dev]]
            mod = np.interp(grid, t, g)
            win = (grid >= 4.9) & (grid <= (9.0 if key == "full" else 5.0 + (key / 1e3) + 2.5))
            rms = float(np.sqrt(np.mean((mod[win] - real[win]) ** 2)))
            # lag: shift of the model that best overlays the real gate
            lags = np.arange(-0.4, 0.4001, 0.002)
            errs = [np.mean((np.interp(grid[win] + L, grid, mod) - real[win]) ** 2) for L in lags]
            lag = float(lags[int(np.argmin(errs))]) * 1e3
            pk_r, pk_m = float(real[win].max()), float(mod[win].max())
            print(f"  {str(key):>8}{pk_r:>11.3f}{pk_m:>12.3f}{pk_m - pk_r:>+8.3f}{rms:>8.3f}{lag:>+10.0f}")
            if j in (0, 1, 3, 5):
                a = axes[r][(0, 1, 3, 5).index(j)]
                a.plot(grid - 5.0, real, color="#111111", lw=2.4, label="real gate (probed)")
                a.plot(grid - 5.0, mod, color="#0E9F9A", lw=1.6, label="model gate $G_{UP}$")
                xmax = {"ex2": 4.0, "inv_chain": 1.0}[dev]
                a.set_xlim(-0.05 * xmax, xmax); a.set_ylim(-0.1, 1.15)
                a.set_title(f"{dev}, {'full transition' if key == 'full' else str(key) + ' ps'}", fontsize=9)
                a.set_xlabel("time from the input edge (ns)", fontsize=8)
                if j == 0:
                    a.set_ylabel("gate, normalised"); a.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "gate_internal_check.png", dpi=160)
    print(f"\nfigure: {HERE / 'gate_internal_check.png'}")


if __name__ == "__main__":
    main()
