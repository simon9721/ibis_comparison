#!/usr/bin/env python3
"""What are the REAL saturation boundary and drive exponent of the predriver transistors?

`results/model_provenance_2026-09-25/check_xlin.py` compares our fitted x_lin against
`1 - VTH0/V_DD`. That is the long-channel Shockley value V_DSAT = V_GS - V_TH - i.e. a
PREDICTION of the same Level-1 model we are departing from, not a measurement. It is
also computed from `buffers/models/hspice.mod` for every buffer, but inv_chain does not
use that card: it runs on `HL18G-S3.7S.lib` at 180 nm drawn, whose VTH0 is 0.464/0.613
against hspice.mod's 0.363/0.407.

So the yardstick in `results/device_taper_2026-09-28/FINDINGS.md` section 3 is doubly
suspect. This replaces it with the devices' own numbers, read against the alpha-power-law
paper (Sakurai & Newton, IEEE JSSC 25(2) 584-594, 1990):

    V_TH, alpha   Appendix A: V_TH is chosen so that log I_sat against log(V_GS - V_TH) is a
                  straight line; alpha is its slope
    V_D0          the paper gives no procedure. Taken as the breakpoint that best fits its
                  piecewise model, I_D = I_D0 * min(1, V_DS/V_D0), to the full-drive output
                  curve - the "effective resistance" line of the paper's Fig. 4

(Until 2026-10-01 this script took V_TH at 2 % of peak current and V_D0 from the origin
tangent, and called both "Appendix A". The tangent reads 25-40 % lower than the fit.)

Both are dimensionless once divided by V_DD, and both are what the stage law's drain
factor is trying to be. `p` in h(u) IS alpha, so this measures that too.

    py -3.14 scripts/device_alpha_extract.py

Output: results/device_taper_2026-09-28/alpha_extract/
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import spice_decks as sd  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

N_OUTER = 21          # .dc vg 0 VDD VDD/20
OUT = ROOT / "results" / "device_taper_2026-09-28" / "alpha_extract"

MOD = ROOT / "buffers" / "models" / "hspice.mod"
HL18 = ROOT / "buffers" / "inv_chain" / "HL18G-S3.7S.lib"

# The devices the predrivers actually use, at the sizes they are actually drawn.
DEVICES = [
    # name                 buffer       card   model     W        L      VDD  type
    ("ex2 predriver NMOS", "ex2", "hspice.mod", "nfet", 1.62e-5, 6e-7, 3.3, "n"),
    ("ex2 predriver PMOS", "ex2", "hspice.mod", "pfet", 3.21e-5, 6e-7, 3.3, "p"),
    ("inv_chain NMOS", "inv_chain", "HL18G", "nch_tn", 1e-6, 180e-9, 1.8, "n"),
    ("inv_chain PMOS", "inv_chain", "HL18G", "pch_tn", 2e-6, 180e-9, 1.8, "p"),
]


def deck(card: str, model: str, w: float, l_: float, vdd: float, kind: str) -> str:
    """One device, gate and drain swept. PMOS is written with its own rails so that
    VGS and VDS come out positive and the two types are read the same way."""
    head = sd.hspice_header(f"alpha extraction {model}", options="post=2 probe accurate ingold=2")
    lib = (f".include '{MOD.as_posix()}'" if card == "hspice.mod"
           else f".lib '{HL18.as_posix()}' tt_tn")
    if kind == "n":
        dev = f"m1 d g 0 0 {model} w={w:g} l={l_:g}"
        src = "vd d 0 dc 0\nvg g 0 dc 0"
    else:
        # source at VDD, so |VGS| = vdd - vg_node and |VDS| = vdd - vd_node
        dev = f"m1 d g s s {model} w={w:g} l={l_:g}\nvs s 0 dc {vdd:g}"
        src = f"vd d 0 dc {vdd:g}\nvg g 0 dc {vdd:g}"
    return (f"{head}{lib}\n{dev}\n{src}\n"
            f".dc vd 0 {vdd:g} {vdd / 400:g} vg 0 {vdd:g} {vdd / 20:g}\n"
            f".print dc i(vd)\n.end\n")


def run(d: Path, text: str) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "run.sp").write_text(text, encoding="utf-8")
    subprocess.run([str(default_hspice()), "-i", "run.sp", "-o", "run"],
                   cwd=d, capture_output=True, timeout=900)
    sw = list(d.glob("run.sw0"))
    if not sw:
        raise RuntimeError(f"no .sw0 in {d}; see run.lis")
    return sw[0]


def parse_sw0(p: Path, n_outer: int):
    """-> [(v_outer, v_inner[], probe[]), ...], one entry per outer sweep value.

    POST=2 ASCII: 13-character fields, no delimiter, the same character stream
    `eye_diagram.parse_hspice_tr0` decodes for .tr0. Only the block layout differs
    (a nested .dc writes the outer value once, then the inner pairs, then a 1e30
    terminator), which is why the decode is repeated here instead of reused.
    """
    raw = p.read_text(errors="replace")
    j = raw.find("$&%#")
    if j < 0:
        raise ValueError(f"no $&%# marker in {p}")
    flat = re.sub(r"\s+", "", raw[j + 4:])
    vals = []
    for k in range(0, len(flat) - 12, 13):
        try:
            vals.append(float(flat[k:k + 13]))
        except ValueError:
            break
    v = np.array(vals)
    v = v[np.abs(v) < 1e29]                       # drop the per-block 1e30 terminators
    if v.size % n_outer:
        raise ValueError(f"{p}: {v.size} values do not split into {n_outer} blocks")
    return [(float(b[0]), b[1::2], b[2::2]) for b in v.reshape(n_outer, -1)]


def extract(blocks, vdd: float, kind: str, full: bool = False):
    """(V_D0, alpha, V_TH, vgs, isat, curves); with full=True also the origin-tangent V_D0.

    V_TH and alpha follow Appendix A of the paper (its first method): V_TH is the value
    that makes log I_sat against log(V_GS - V_TH) most nearly a straight line, and alpha is
    that line's slope. I_sat is read at |V_DS| = V_DD.

    V_D0 is NOT covered by Appendix A - the paper only says the four parameters are "easily
    obtained from the measured data". Here it is the breakpoint that best fits the paper's
    own piecewise model, I/I_D0 = min(1, V_DS/V_D0), to the output curve at full gate drive
    (least squares over 0..V_DD). That matches the paper's Fig. 4, where the triode line is
    an effective resistance lying under the measured curve. The origin-tangent intersection
    used until 2026-10-01 is steeper than that line and reads 25-40 % lower; it is still
    returned with full=True because the 09-28 findings quote it.

    For the PMOS the deck holds the source at V_DD and sweeps the node voltages, so
    |V_GS| = V_DD - v_gate and |V_DS| = V_DD - v_drain; both are flipped here so the two
    device types are read identically.
    """
    curves, vgs = [], []
    for v_out, v_in, probe in blocks:
        g = v_out if kind == "n" else vdd - v_out
        d = v_in if kind == "n" else vdd - v_in
        order = np.argsort(d)
        curves.append((d[order], np.abs(probe)[order]))
        vgs.append(g)
    order = np.argsort(vgs)
    vgs = np.array(vgs)[order]
    curves = [curves[i] for i in order]
    isat = np.array([y[-1] for _, y in curves])          # at |V_DS| = V_DD

    # Appendix A: the V_TH that linearises the log-log plot; alpha is the slope
    best = (-1.0, float("nan"), float("nan"))
    for vth in np.arange(0.05, 0.5 * vdd, 0.005):
        m = (vgs > vth + 0.15) & (isat > 0)
        if m.sum() < 6:
            continue
        lx, ly = np.log(vgs[m] - vth), np.log(isat[m])
        c = np.polyfit(lx, ly, 1)
        r2 = 1.0 - np.sum((ly - np.polyval(c, lx)) ** 2) / np.sum((ly - ly.mean()) ** 2)
        if r2 > best[0]:
            best = (r2, float(vth), float(c[0]))
    _, vth, alpha = best

    # V_D0: least-squares breakpoint of the paper's piecewise model at full gate drive
    x, y = curves[-1]
    yn = y / y[-1]
    cand = np.linspace(0.05, 1.0, 951) * vdd
    vd0 = float(cand[np.argmin([np.mean((np.minimum(1.0, x / v) - yn) ** 2) for v in cand])])

    if not full:
        return vd0, alpha, vth, vgs, isat, curves
    n0 = max(3, int(0.02 * len(x)))
    g0 = np.polyfit(x[:n0], y[:n0], 1)[0]
    vd0_tangent = float(y[-1] / g0) if g0 > 0 else float("nan")
    return vd0, alpha, vth, vgs, isat, curves, vd0_tangent


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"  HSPICE: {default_hspice()}\n")
    print(f"  {'device':<22}{'VDD':>5}{'L':>8}{'V_TH':>7}{'V_D0':>8}{'V_D0/VDD':>10}{'alpha':>8}")
    rows, fig = [], plt.figure(figsize=(11, 4.2))
    for name, buf, card, model, w, l_, vdd, kind in DEVICES:
        sw = run(OUT / model, deck(card, model, w, l_, vdd, kind))
        vd0, alpha, vth, vgs, isat, curves, vd0_tan = extract(parse_sw0(sw, N_OUTER), vdd, kind, full=True)
        print(f"  {name:<22}{vdd:>5.1f}{l_ * 1e9:>7.0f}n{vth:>7.3f}{vd0:>8.3f}{vd0 / vdd:>10.3f}{alpha:>8.2f}")
        rows.append((name, vdd, l_, vth, vd0, vd0 / vdd, alpha, vd0_tan / vdd))
        ax = fig.add_subplot(1, 2, 1)
        x, y = curves[-1]
        ax.plot(x / vdd, y * 1e3, label=f"{name}  V_D0/VDD={vd0 / vdd:.2f}")
        ax.axvline(vd0 / vdd, ls=":", lw=1, color=ax.lines[-1].get_color())
        ax2 = fig.add_subplot(1, 2, 2)
        ax2.loglog(np.maximum(vgs - vth, 1e-6), np.maximum(isat, 1e-12) * 1e3, "o-", ms=3, label=f"{name} a={alpha:.2f}")
    for ax, xl, yl, t in ((fig.axes[0], "|V_DS| / V_DD", "|I_D| (mA)", "output curve at full gate drive"),
                          (fig.axes[1], "gate overdrive (V)", "|I_sat| (mA)", "saturation current vs overdrive")):
        ax.set_xlabel(xl), ax.set_ylabel(yl), ax.set_title(t), ax.grid(alpha=0.3), ax.legend(fontsize=7)
    fig.suptitle("alpha-power-law parameters of the predriver devices as drawn",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "alpha_extract.png", dpi=150)

    print(f"\n  {'device':<22}{'measured V_D0/VDD':>19}{'Level-1 1-Vth/VDD':>20}{'x_lin today':>13}")
    for name, vdd, l_, vth, vd0, frac, alpha, tan in rows:
        print(f"  {name:<22}{frac:>19.3f}{1 - vth / vdd:>20.3f}{0.45:>13.2f}")
    (OUT / "results.csv").write_text(
        "device,vdd,L_m,vth_extracted,vd0,vd0_over_vdd,alpha,vd0_tangent_over_vdd\n"
        + "\n".join(f"{n},{v},{l_},{t:.4f},{d:.4f},{f:.4f},{a:.3f},{tn:.4f}" for n, v, l_, t, d, f, a, tn in rows) + "\n",
        encoding="utf-8")
    print(f"\n  wrote {OUT / 'results.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
