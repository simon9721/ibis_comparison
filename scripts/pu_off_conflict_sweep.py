#!/usr/bin/env python3
"""Is `pu_off` genuinely undecidable, or was three points just too few?

`pu_off_scale_2026-09-07` claimed the parameter cannot be derived because it sets
two things at once -- when the gate decays, and the phase between the gate and the
residual spike -- and they want opposite values. That was argued from three
points (0.70 / 0.29 / 0.25) plus a mechanism read off the netlist. Three points
cannot rule out an interior optimum that satisfies both.

This sweeps it properly. Two objectives, each measured against its own reference:

* **coefficient**  Ku rms against the transistor over +90..+400 ps from the
  reversal, three widths. That window is grid-converged (spread 0.0012 against
  0.0304 nearer the reversal, `silicon_kukd_conditioning_2026-09-07`), so the
  reference is sound there.
* **amplitude**    the full-swing reversal overshoot above the trace's own
  settled plateau. The transistor's is +64.9 mV, native's +83.8.

If both objectives are monotone in `pu_off` and pull in opposite directions,
there is no value that satisfies both and the claim stands. If either turns over,
it falls.

    py -3.14 scripts/pu_off_conflict_sweep.py
"""
from __future__ import annotations

import re
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
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
from pedestal_localization import read  # noqa: E402

R = ROOT / "results"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
OUT = R / "pu_off_conflict_2026-09-07"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
RISE_NS, EDGE_NS, STOP_NS = 5.000, 0.050, 22.0
WIDTHS = (2354, 1792, 1505)
SCALES = (0.10, 0.20, 0.25, 0.29, 0.40, 0.50, 0.60, 0.70, 0.85, 1.00)
PU_OFF = 0.0676997420246

PEAK_HOLD = (
    "BGUPHOLD GUPHOLD 0 I = -1e-12 * ((V(GUP) > V(GUPHOLD)) ? "
    "(V(GUP) - V(GUPHOLD)) / 1p : (V(GUP) - V(GUPHOLD)) / 5n)\n"
    "CGUPHOLD GUPHOLD 0 1e-12 ic=0\n"
    "RGUPHOLD GUPHOLD 0 1e12\n"
    "BFRAC FRAC 0 V = min(max(V(GUPHOLD), 0.05), 1.0)\n"
)


def patch(text: str, scale: float) -> str:
    anchor = "BKURES_TABLE"
    text = text[:text.index(anchor)] + PEAK_HOLD + text[text.index(anchor):]
    for node, target in (("KURES_TABLE", "V(KURES_F)"),
                         ("KDRES_TABLE", "V(KDRES_F)")):
        pat = rf"^(B\S+ {node} 0 V = .*?){re.escape(target)}"
        text, n = re.subn(pat, rf"\1({target} * V(FRAC))", text, count=1, flags=re.M)
        if n != 1:
            raise RuntimeError(f"{node}: selector not found")
    text, n = re.subn(rf"Td={re.escape(f'{PU_OFF:.12g}')}n",
                      f"Td={PU_OFF * scale:.12g}n", text)
    if n == 0:
        raise RuntimeError("pu_off not found")
    return text


def build(scale: float, width_ps: int | None) -> Path:
    d = OUT / f"s{scale:.2f}" / (f"w{width_ps}" if width_ps else "full")
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "driver.sub").exists():
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                            model_name=MODEL, component_name=COMPONENT)
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                        str(d / "driver.sub"))
        (d / "driver.sub").write_text(
            patch((d / "driver.sub").read_text(encoding="utf-8"), scale),
            encoding="utf-8")
    fall = RISE_NS + (10.0 if width_ps is None else width_ps / 1000.0)
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  "
           f"{fall}n {SUPPLY}  {fall + EDGE_NS}n 0  {STOP_NS}n 0)")
    (d / "run.sp").write_text(
        dk.ngspice_header() + ".include driver.sub\n"
        + dk.supply("VCC", SUPPLY, name="Vdd")
        + f"Vin IN 0 {pwl}\n"
        + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
        + sub.instance("X1") + dk.load("OUT", R_LOAD, C_LOAD_PF)
        + f".tran 0.002n {STOP_NS}n\n.save V(OUT) V(X1.ku) V(X1.kd)\n.end\n",
        encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1200) is None:
            raise RuntimeError(f"{d} failed -- see ngspice.log")
    return d


def overshoot(t, y) -> float:
    """Local max in 15.00-15.30 ns above the settled plateau at 14.5 ns, mV."""
    g = np.arange(15.00, 15.30, 0.001)
    return (float(np.interp(g, t, y).max()) - float(np.interp(14.5, t, y))) * 1e3


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    win = np.arange(0.090, 0.400, 0.002)
    print("  Two objectives against pu_off scale. Reference: the transistor's")
    print("  full-swing reversal overshoot is +64.9 mV, native's +83.8.\n")
    print(f"    {'scale':>7}{'pu_off ps':>11}{'Ku rms':>10}{'Ku ratio':>10}"
          f"{'overshoot mV':>15}")
    rows = []
    for sc in SCALES:
        rs, qs = [], []
        for w in WIDTHS:
            ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
            t = ref["time_ns"] - (RISE_NS + w / 1000.0)
            si = np.interp(win, t, ref["silicon_ku"])
            raw = sl.parse_ngspice_raw(build(sc, w) / "run.raw")
            ku = np.interp(win, sl.time_ns(raw) - (RISE_NS + w / 1000.0),
                           sl.signal(raw, "v(x1.ku)"))
            ok = np.abs(si) > 0.03
            rs.append(float(np.sqrt(np.mean((ku - si) ** 2))))
            qs.append(float(np.median(ku[ok] / si[ok])))
        raw = sl.parse_ngspice_raw(build(sc, None) / "run.raw")
        ov = overshoot(sl.time_ns(raw), sl.trace(raw, "out"))
        rows.append((sc, np.mean(rs), np.mean(qs), ov))
        print(f"    {sc:>7.2f}{PU_OFF * sc * 1e3:>11.1f}{np.mean(rs):>10.4f}"
              f"{np.mean(qs):>10.2f}{ov:>15.1f}")

    sc = np.array([r[0] for r in rows])
    rms = np.array([r[1] for r in rows])
    ov = np.array([r[3] for r in rows])
    print(f"\n    Ku rms monotone increasing in scale: "
          f"{bool(np.all(np.diff(rms) > 0))}")
    print(f"    overshoot monotone increasing in scale: "
          f"{bool(np.all(np.diff(ov) > -0.5))}")
    print(f"    best scale for Ku:        {sc[int(np.argmin(rms))]:.2f}")
    print(f"    scale matching the transistor's +64.9 mV overshoot: "
          f"{float(np.interp(64.9, ov, sc)):.2f}")

    # Each objective as distance from its own target, so the conflict is visible:
    # the Ku error is smallest at a LOW scale, the overshoot error at a HIGH one.
    ku_err = np.abs(rms - 0.0167)          # native's Ku rms is the bar
    ov_err = np.abs(ov - 64.9)             # the transistor's overshoot, mV
    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    ax1.plot(sc, ku_err / ku_err.max(), marker="o", color="#2E8B57", lw=2.4,
             label="coefficient error  |Ku rms - native's|   (best at scale 0.10)")
    ax1.plot(sc, ov_err / ov_err.max(), marker="s", color="#C05621", lw=2.4,
             label="amplitude error  |overshoot - transistor's 64.9 mV|   (best at scale 0.86)")
    ax1.axvline(0.10, color="#2E8B57", ls=":", lw=1.4)
    ax1.axvline(0.86, color="#C05621", ls=":", lw=1.4)
    ax1.set_xlabel("pu_off scale")
    ax1.set_ylabel("error, normalised to its own worst value")
    ax1.set_ylim(-0.02, 1.05)
    ax1.grid(alpha=0.3)
    ax1.legend(fontsize=9, loc="upper center")
    ax1.set_title("One parameter, two errors that fall in opposite directions -- no scale satisfies both",
                  fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "pu_off_conflict.png", dpi=200)
    plt.close(fig)
    print(f"\n  figure: {OUT / 'pu_off_conflict.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
