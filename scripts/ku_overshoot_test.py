#!/usr/bin/env python3
"""Why does our Ku keep rising after the reversal, when native's turns around?

Looking at the coefficient *shapes* rather than a fitted lag
(`coefficient_shapes.png`) makes the pedestal visible as something specific:

    io_buf 1792 ps, Ku after the reversal      peak     at
        native                                 0.508    48 ps
        ours                                   0.669    77 ps

Before the reversal all three curves lie on each other. At the reversal native
turns around and ours **keeps climbing for another 29 ps and 0.16 higher**. That
overshoot is the pedestal's origin, and it is a shape fact no best-fit lag was
ever going to show.

The command layer gates the pull-up like this:

    TPUCMDA NINX 0 PUCMDA 0 Td=0.992581n     the on-delay
    TPUCMDB NINX 0 PUCMDB 0 Td=0.0677n       the off-delay
    BPUCMDLVL = (V(PUCMDA) > 0.5) && (V(PUCMDB) > 0.5)

With AND, PUCMDLVL **falls when the earlier copy falls** -- so the pull-up is told
to stop `pu_off_delay` = 68 ps after the input reverses. Our Ku peaks at 77 ps.
That is the hypothesis: the overshoot is the off-delay, and nothing else.

Earlier sweeps scaled all four delays together and measured the *pad* with a
best-fit lag, which mixed four effects and hid this. This sweeps them one at a
time and measures the Ku shape.

    py -3.14 scripts/ku_overshoot_test.py
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
CASE = (R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
        / "io_buf_short_high_w1792ps.csv")
OUT = R / "ku_overshoot_2026-09-04"
FIGS = R / "meeting_deck_2026-09-04" / "figures"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
RISE_NS, FALL_NS, EDGE_NS, STOP_NS = 5.000, 6.790, 0.050, 22.0
REV = 6.792
PROBES = ("gup", "gdn", "ku", "kd")

# name -> the exact Td value in the generated subcircuit, in ns.
DELAYS = {"pu_on": 0.992580638109, "pu_off": 0.0676997420246,
          "pd_on": 1.83133633792, "pd_off": 0.850179083174}


def build(tag: str, overrides: dict[str, float]) -> Path:
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                    str(d / "driver.sub"))
    text = (d / "driver.sub").read_text(encoding="utf-8")
    for name, new in overrides.items():
        old = DELAYS[name]
        text, n = re.subn(rf"Td={re.escape(f'{old:.12g}')}n",
                          f"Td={max(new, 1e-4):.12g}n", text)
        if n == 0:
            raise RuntimeError(f"{tag}: {name} not found")
    (d / "driver.sub").write_text(text, encoding="utf-8")

    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  "
           f"{FALL_NS}n {SUPPLY}  {FALL_NS + EDGE_NS}n 0  {STOP_NS}n 0)")
    saves = " ".join(f"V(X1.{p})" for p in PROBES)
    (d / "run.sp").write_text(
        dk.ngspice_header()
        + ".include driver.sub\n"
        + dk.supply("VCC", SUPPLY, name="Vdd")
        + f"Vin IN 0 {pwl}\n"
        + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
        + sub.instance("X1")
        + dk.load("OUT", R_LOAD, C_LOAD_PF)
        + f".tran 0.002n {STOP_NS}n\n.save V(OUT) {saves}\n.end\n",
        encoding="utf-8")
    return d


def measure(d: Path):
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1200) is None:
            raise RuntimeError(f"{d.name} failed")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    t = sl.time_ns(raw) - REV
    ku = sl.signal(raw, "v(x1.ku)")
    w = (t > -0.3) & (t < 0.8)
    i = int(np.argmax(ku[w]))
    # Where it has fallen back to a tenth of its peak: the decay, not just the
    # peak, since two curves can peak alike and separate afterwards.
    tail = ku[w][i:]
    j = np.argmax(tail < 0.1 * ku[w][i]) if (tail < 0.1 * ku[w][i]).any() else -1
    return (float(ku[w][i]), float(t[w][i]) * 1e3,
            float(t[w][i:][j]) * 1e3 if j >= 0 else float("nan"),
            t, ku)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ref = read(CASE)
    tr = ref["time_ns"] - REV
    w = (tr > -0.3) & (tr < 0.8)
    print("  io_buf 1792 ps, Ku after the reversal.")
    print(f"    {'build':<28}{'peak':>8}{'at (ps)':>10}{'down to 10% (ps)':>19}")
    for lab, key in (("native", "hspice_ku"), ("transistor (has a spike)", "silicon_ku")):
        y = ref[key][w]
        i = int(np.argmax(y))
        tail = y[i:]
        j = np.argmax(tail < 0.1 * y[i]) if (tail < 0.1 * y[i]).any() else -1
        down = tr[w][i:][j] * 1e3 if j >= 0 else float("nan")
        print(f"    {lab:<28}{y[i]:>8.3f}{tr[w][i]*1e3:>10.0f}{down:>19.0f}")

    runs = [("shipped", {})]
    for scale in (0.5, 0.25, 0.0):
        runs.append((f"pu_off x{scale:g}",
                     {"pu_off": DELAYS["pu_off"] * scale}))
    runs.append(("pu_on x0.25", {"pu_on": DELAYS["pu_on"] * 0.25}))
    runs.append(("pd_off x0.25", {"pd_off": DELAYS["pd_off"] * 0.25}))
    runs.append(("pd_on x0.25", {"pd_on": DELAYS["pd_on"] * 0.25}))

    curves = {}
    for tag, ov in runs:
        peak, at, down, t, ku = measure(build(tag.replace(" ", "_").replace(".", "p"), ov))
        curves[tag] = (t, ku)
        print(f"    {tag:<28}{peak:>8.3f}{at:>10.0f}{down:>19.0f}")

    fig, ax = plt.subplots(figsize=(12.2, 5.0))
    ax.plot(tr[w], ref["silicon_ku"][w], color="#111", lw=3.0,
            label="transistor (solve spikes at the reversal)")
    ax.plot(tr[w], ref["hspice_ku"][w], color="#2B6CA3", lw=2.6, label="native")
    shades = plt.cm.autumn(np.linspace(0.0, 0.7, len(curves)))
    for (tag, (t, ku)), colour in zip(curves.items(), shades):
        m = (t > -0.3) & (t < 0.8)
        ax.plot(t[m], ku[m], color=colour, lw=1.8, label=f"ours, {tag}")
    ax.axvline(0, color="#8A8A8A", ls="--", lw=1.4)
    ax.set_xlabel("Time from the reversal (ns)")
    ax.set_ylabel("Ku")
    ax.set_ylim(-0.1, 1.0)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, ncol=2)
    ax.set_title("io_buf 1792 ps | our Ku keeps climbing past the reversal — "
                 "which delay does it?", fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "ku_overshoot.png", dpi=200)
    plt.close(fig)
    print("\n  ku_overshoot.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
