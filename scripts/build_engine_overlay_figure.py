#!/usr/bin/env python3
"""The same pybis model in both engines, pad against pad.

`pybis_engine_model_decoupling_2026-09-03/FINDINGS.md` reports the 2x2 as three
crossing times and no picture. The crossings say the engines agree to half a
picosecond; this draws the two pad voltages so that can be seen rather than
taken on trust.

**Which model.** The translated subcircuit is `driver2_OutputInput_Typical` from
pybis2spice v1.2 -- the **stock Output model**, not gate_state and not cmd_clean.
Its body has no GUPCMD anywhere in it. So this figure answers "does the engine
change the answer", not "does the engine change *our* command-layer builds".

The ngspice half already exists and is not re-run:
`pybis_lag_converged_2026-09-03/pybis_0.2ps/` -- base8 at 1.8 V into 50 ohm + 2 pF,
0.2 ps step at reltol 1e-5, which is the converged setting the lag study settled
on. This adds the HSPICE half of the identical model, from the translation in
`pybis_engine_model_decoupling_2026-09-03/base8_driver_hspice.sub`, on the same
stimulus and the same load.

The translation used to have a caveat that mattered here: HSPICE's `PWL(1)`
extrapolates past a table's ends using the end slope where ngspice's `pwl()` holds
the end value, so a control node that ran off its table diverged. On base8 it put
the pad at -4394 V from 0.84 ns to 5.10 ns, straight through the rising edge --
not "early in the record" as first recorded. `pybis_subckt_to_hspice.py` now adds
a flat guard segment at each end of every table, which reproduces ngspice's
clamping, and the whole record agrees.

    py -3.14 scripts/build_engine_overlay_figure.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402

R = ROOT / "results"
NG_RUN = R / "pybis_lag_converged_2026-09-03" / "pybis_0.2ps"
NG_SUB = NG_RUN / "driver.sub"
OUT = R / "engine_overlay_2026-09-04"
FIGS = R / "meeting_deck_2026-09-04" / "figures"

# Read off pybis_0.2ps/run.sp so the two decks cannot drift apart.
SUPPLY, R_LOAD, C_LOAD_PF = 1.8, 50.0, 2.0
RISE_NS, FALL_NS, EDGE_NS, STOP_NS = 5.0, 15.0, 0.001, 22.0
SUBCKT = "driver2_OutputInput_Typical"

C_NG, C_HS = "#C05621", "#2B6CA3"

plt.rcParams.update({"font.size": 14, "axes.titlesize": 15, "axes.labelsize": 14,
                     "xtick.labelsize": 12, "ytick.labelsize": 12,
                     "legend.fontsize": 12})
FIGSIZE = (12.2, 5.4)


def hspice_run() -> tuple[np.ndarray, np.ndarray]:
    """The translated model in HSPICE, on the ngspice run's stimulus and load.

    Plain options, and Gear. The tight `accurate relv=1e-4 reli=1e-4` set the
    native deck uses collapses the timestep here: the translated PWL(1) tables
    extrapolate off their ends on an idle node, and chasing that transient to
    1e-4 never converges. Gear damps it and the edges -- the only part this
    figure claims anything about -- come out clean.
    """
    d = OUT / "hspice"
    d.mkdir(parents=True, exist_ok=True)
    # Translated here rather than reusing the stored .sub, so the figure is
    # reproducible from the same ngspice subcircuit the ngspice half ran.
    subprocess.run([sys.executable, str(ROOT / "scripts" / "pybis_subckt_to_hspice.py"),
                    str(NG_SUB), str(d / "driver_hspice.sub")], check=True)
    deck = f"""* base8 pybis model, translated, in HSPICE
.title pybis model in hspice
.option post=2 probe ingold=2 method=gear delmax=0.002n
.temp 27
.include 'driver_hspice.sub'
Vdd VCC 0 DC {SUPPLY}
Vin IN 0 PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  """ \
        f"""{FALL_NS}n {SUPPLY}  {FALL_NS + EDGE_NS}n 0  {STOP_NS}n 0)
Ven EN 0 DC {SUPPLY}
X1 OUT IN EN VCC 0 {SUBCKT}
Rload OUT 0 {R_LOAD}
Cload OUT 0 {C_LOAD_PF}p
.probe tran V(OUT)
.tran 0.0005n {STOP_NS}n
.end
"""
    sp = d / "run.sp"
    tr0 = d / "run.tr0"
    if not (tr0.exists() and sp.exists()
            and sp.read_text(encoding="utf-8") == deck):
        sp.write_text(deck, encoding="utf-8")
        if sl.hspice(d, timeout_s=900) is None:
            raise RuntimeError("hspice run failed -- see run.lis")
    raw = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(raw), sl.trace(raw, "out")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not (NG_RUN / "run.raw").exists():
        print(f"missing {NG_RUN / 'run.raw'}")
        return 1
    ng = sl.parse_ngspice_raw(NG_RUN / "run.raw")
    t_ng, v_ng = sl.time_ns(ng), sl.trace(ng, "out")
    t_hs, v_hs = hspice_run()

    grid = np.arange(0.05, STOP_NS - 0.05, 0.002)
    a = np.interp(grid, t_ng, v_ng)
    b = np.interp(grid, t_hs, v_hs)
    edges = ((grid > RISE_NS - 0.2) & (grid < RISE_NS + 3.0)) | \
            ((grid > FALL_NS - 0.2) & (grid < FALL_NS + 3.0))
    print(f"  whole record  max|diff| {np.abs(a - b).max() * 1e3:8.2f} mV")
    print(f"  edge windows  max|diff| {np.abs(a - b)[edges].max() * 1e3:8.2f} mV, "
          f"rms {np.sqrt(np.mean((a - b)[edges] ** 2)) * 1e3:.3f} mV")
    for lab, lo in (("rising", RISE_NS), ("falling", FALL_NS)):
        half = SUPPLY / 2.0
        x = sl.cross(t_ng, v_ng, half, rising=(lab == "rising"), after=lo - 0.2)
        y = sl.cross(t_hs, v_hs, half, rising=(lab == "rising"), after=lo - 0.2)
        print(f"  {lab:<8} 50% crossing  ngspice {x:.4f} ns   HSPICE {y:.4f} ns   "
              f"engine {(y - x) * 1e3:+.1f} ps")

    fig, ax = plt.subplots(1, 2, figsize=FIGSIZE, sharey=True)
    for a_, (lo, hi), title in ((ax[0], (RISE_NS - 0.2, RISE_NS + 2.8), "Rising edge"),
                                (ax[1], (FALL_NS - 0.2, FALL_NS + 2.8), "Falling edge")):
        a_.plot(t_ng, v_ng, color=C_NG, lw=4.0, label="pybis model in ngspice")
        a_.plot(t_hs, v_hs, color=C_HS, lw=2.0, ls="--",
                label="pybis model in HSPICE")
        a_.set_xlim(lo, hi)
        a_.set_title(title, loc="left", fontweight="bold")
        a_.set_xlabel("Time (ns)")
        a_.grid(alpha=0.3)
    ax[0].set_ylabel("Pad (V)")
    ax[0].legend(loc="lower right")
    fig.suptitle("inv_chain base8 | 50 ohm + 2 pF | the same pybis model in "
                 "both engines", fontsize=16, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "engine_overlay.png", dpi=200)
    plt.close(fig)
    print("  engine_overlay.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
