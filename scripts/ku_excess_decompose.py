#!/usr/bin/env python3
"""Where does our excess Ku live -- the gate map, or the residual?

Scored against the transistor over +90..+400 ps from the reversal (the window
where the two-fixture solve is trustworthy; nearer the reversal it goes
ill-conditioned and reads 0.99 at 1792 ps, which the device does not do):

    Ku rms vs transistor        native 0.0167   shipped 0.1358   corrected 0.0903
    Ku ratio to transistor      native 1.07     shipped 1.93     corrected 1.59
    Kd rms vs transistor        native 0.0107   shipped 0.0411   corrected 0.0148

So Kd is essentially solved and **Ku is not** -- still 1.6x the transistor after
the residual scaling. Since the correction already halves the residual, a 1.6x
leftover implies the **gate part** over-predicts on its own.

Ku is built as:

    KUGATE_BASE = pwl(GUP, ...) selected on whether GUP is rising or falling
    KURES_TABLE = pwl(HNX, ...) the residual
    Ku          = KUGATE_BASE + KURES_TABLE

This probes all three plus GUP and HNX, so the excess can be attributed.

    py -3.14 scripts/ku_excess_decompose.py
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
OUT = R / "ku_excess_decompose_2026-09-07"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
RISE_NS, EDGE_NS, STOP_NS = 5.000, 0.050, 22.0
WIDTHS = (2354, 1989, 1792, 1505)
PROBES = ("ku", "kd", "gup", "gdn", "hnx", "kugate_base", "kures_table",
          "kdgate_base", "kdres_table")

# Same peak-hold patch as residual_rescale_time, so "corrected" here is the same
# build that produced the numbers above.
PEAK_HOLD = (
    "BGUPHOLD GUPHOLD 0 I = -1e-12 * ((V(GUP) > V(GUPHOLD)) ? "
    "(V(GUP) - V(GUPHOLD)) / 1p : (V(GUP) - V(GUPHOLD)) / 5n)\n"
    "CGUPHOLD GUPHOLD 0 1e-12 ic=0\n"
    "RGUPHOLD GUPHOLD 0 1e12\n"
    "BFRAC FRAC 0 V = min(max(V(GUPHOLD), 0.05), 1.0)\n"
)
PU_OFF = 0.0676997420246
PU_OFF_SCALE = 0.70


def patch(text: str, mode: str) -> str:
    if mode == "shipped":
        return text
    anchor = "BKURES_TABLE"
    text = text[:text.index(anchor)] + PEAK_HOLD + text[text.index(anchor):]
    for node, target in (("KURES_TABLE", "V(KURES_F)"),
                         ("KDRES_TABLE", "V(KDRES_F)")):
        pat = rf"^(B\S+ {node} 0 V = .*?){re.escape(target)}"
        text, n = re.subn(pat, rf"\1({target} * V(FRAC))", text, count=1, flags=re.M)
        if n != 1:
            raise RuntimeError(f"{node}: selector not found")
    text, n = re.subn(rf"Td={re.escape(f'{PU_OFF:.12g}')}n",
                      f"Td={PU_OFF * PU_OFF_SCALE:.12g}n", text)
    if n == 0:
        raise RuntimeError("pu_off not found")
    return text


def build(mode: str, width_ps: int) -> Path:
    d = OUT / mode / f"w{width_ps}"
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "driver.sub").exists():
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                            model_name=MODEL, component_name=COMPONENT)
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                        str(d / "driver.sub"))
        (d / "driver.sub").write_text(
            patch((d / "driver.sub").read_text(encoding="utf-8"), mode),
            encoding="utf-8")
    fall = RISE_NS + width_ps / 1000.0
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  "
           f"{fall}n {SUPPLY}  {fall + EDGE_NS}n 0  {STOP_NS}n 0)")
    saves = " ".join(f"V(X1.{p})" for p in PROBES)
    (d / "run.sp").write_text(
        dk.ngspice_header() + ".include driver.sub\n"
        + dk.supply("VCC", SUPPLY, name="Vdd")
        + f"Vin IN 0 {pwl}\n"
        + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
        + sub.instance("X1") + dk.load("OUT", R_LOAD, C_LOAD_PF)
        + f".tran 0.002n {STOP_NS}n\n.save V(OUT) {saves}\n.end\n",
        encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1200) is None:
            raise RuntimeError(f"{d} failed -- see ngspice.log")
    return d


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    g = np.arange(0.090, 0.400, 0.002)
    print("  Our Ku split into its two parts, against the transistor and native.")
    print("  Window +90..+400 ps from the reversal.\n")
    print(f"    {'width':<7}{'mode':<11}{'transistor':>11}{'native':>9}"
          f"{'our Ku':>9}{'gate part':>11}{'residual':>10}"
          f"{'gate/si':>9}{'total/si':>10}")
    fig, axes = plt.subplots(1, len(WIDTHS), figsize=(4.0 * len(WIDTHS), 4.2),
                             sharey=True)
    for a, w in zip(axes, WIDTHS):
        ref = read(MATRIX / f"io_buf_short_high_w{w}ps.csv")
        t = ref["time_ns"] - (RISE_NS + w / 1000.0)
        si = np.interp(g, t, ref["silicon_ku"])
        nat = np.interp(g, t, ref["hspice_ku"])
        for mode in ("shipped", "amp_puoff"):
            raw = sl.parse_ngspice_raw(build(mode, w) / "run.raw")
            tt = sl.time_ns(raw) - (RISE_NS + w / 1000.0)
            def s(node):
                return np.interp(g, tt, sl.signal(raw, f"v(x1.{node})"))
            ku, gate, res = s("ku"), s("kugate_base"), s("kures_table")
            ok = np.abs(si) > 0.03
            print(f"    {w:<7}{mode:<11}{si.mean():>11.4f}{nat.mean():>9.4f}"
                  f"{ku.mean():>9.4f}{gate.mean():>11.4f}{res.mean():>10.4f}"
                  f"{np.median(gate[ok]/si[ok]):>9.2f}"
                  f"{np.median(ku[ok]/si[ok]):>10.2f}")
            if mode == "amp_puoff":
                m = (tt > -0.35) & (tt < 0.8)
                a.plot(tt[m], sl.signal(raw, "v(x1.kugate_base)")[m],
                       color="#7A3E9D", lw=2.0, label="our gate part")
                a.plot(tt[m], sl.signal(raw, "v(x1.kures_table)")[m],
                       color="#C05621", lw=2.0, ls=":", label="our residual")
                a.plot(tt[m], sl.signal(raw, "v(x1.ku)")[m],
                       color="#2E8B57", lw=2.2, ls="--", label="our Ku (sum)")
        m2 = (t > -0.35) & (t < 0.8)
        a.plot(t[m2], ref["silicon_ku"][m2], color="#111111", lw=3.0,
               label="transistor", zorder=1)
        a.plot(t[m2], ref["hspice_ku"][m2], color="#2B6CA3", lw=1.8,
               label="native", zorder=2)
        a.axvline(0, color="#8A8A8A", ls="--", lw=1.2)
        a.axhline(0, color="#111", lw=0.8)
        a.set_ylim(-0.2, 1.0)
        a.set_xlim(-0.35, 0.8)
        a.set_title(f"{w} ps", fontsize=13, fontweight="bold")
        a.set_xlabel("Time from the reversal (ns)")
        a.grid(alpha=0.3)
    axes[0].set_ylabel("Ku")
    axes[0].legend(fontsize=9)
    fig.suptitle("Our Ku split into gate part and residual, corrected build",
                 fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "ku_excess_decompose.png", dpi=200)
    plt.close(fig)
    print(f"\n  figure: {OUT / 'ku_excess_decompose.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
