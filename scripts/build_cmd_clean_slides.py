#!/usr/bin/env python3
"""Two figures: last week's pages redrawn with cmd_clean added as a third curve.

Last week's deck compared **original** against **fix** — the retuned restore term
— on io_buf, short high, 1792 ps. These are the same two figures, same case, same
wording and same colours, with **cmd_clean** (the build the code calls
`delay_cmd`) drawn alongside so all three can be read at once:

    results/settled_offset_diagnosis_2026-08-27/
        12_gup_ku_fix_comparison.png       ->  cmd_clean_gate_and_ku.png
        11_pad_voltage_fix_comparison.png  ->  cmd_clean_pad.png

Last week's palette is kept exactly, so a curve that was purple last week is
purple again: transistor #111111, native #2B6CA3, original #C05621, fix #7A3E9D.
cmd_clean takes #2E8B57, the one colour in that palette not already spoken for.

The pad figure is one panel, not two. Last week's carried a post-reversal tail
zoom underneath; this is the full view only.

Sources, all one bench -- nothing here re-simulates what already exists:

  * `settled_offset_diagnosis_2026-08-27/09_comprehensive_offset_fix_comparison.csv`
    is what last week's pages were drawn from. It carries the input, every
    internal node of both the original and the fix, and the transistor and native
    references.
  * `stress_method_matrix_2026-08-20/delay_cmd/waveforms/io_buf_short_high_w1792ps.csv`
    carries cmd_clean's Ku, Kd and pad. Its transistor and native columns are
    identical to the comprehensive CSV's to the last decimal, which is how we know
    the two files are the same bench and can be combined.

cmd_clean's *internal* nodes (GUPCMD, GUP) are in neither file, so one ngspice run
regenerates them -- with the stimulus read back off the comprehensive CSV: a 50 ps
edge rising at 5.000 ns and falling at 6.790 ns. Getting that wrong is not
cosmetic; a 1 ps edge moves the pad by up to 77 mV.

    py -3.14 scripts/build_cmd_clean_slides.py
"""
from __future__ import annotations

import csv
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

R = ROOT / "results"
DIAG = R / "settled_offset_diagnosis_2026-08-27"
CHAIN = DIAG / "09_comprehensive_offset_fix_comparison.csv"
FIX_PROBE = DIAG / "fix_probe"
MATRIX_DIR = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
MATRIX = MATRIX_DIR / "io_buf_short_high_w1792ps.csv"

# The same pad figure at every stress level, from files already on disk.
#
#   original   fix_probe/as_shipped_swing{S}_w{W}ps.csv     column `pad`
#   fix_old    fix_probe/gate_and_tau_swing{S}_w{W}ps.csv   column `pad`
#   the rest   stress_method_matrix/delay_cmd/.../w{W}ps.csv
#              columns silicon_pad, hspice_pad, pybis_pad
#
# At 1792 all four are bit-identical to the comprehensive CSV page 7 is drawn
# from -- max|diff| 0.000 mV on every one of them -- which is how we know the two
# trees are the same bench and the other levels can be assembled the same way.
#
# 90% (2484 ps) is absent on purpose. delay_cmd never produced a result there:
# per_case.csv leaves delay_cmd_pad_mv blank for that row. The cause is known --
# the dead zone after the reversal collapses the timestep to ~1 fs and the run
# hits the 240 s wall. reltol=1e-3 completes it but moves the pad by up to 30 mV,
# which is the size of the differences being compared, so a forced run would not
# be evidence.
LEVELS = ((50, 1634), (60, 1792), (70, 1989), (80, 2226))
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
OUT = R / "cmd_clean_slides_2026-09-04"
FIGS = R / "meeting_deck_2026-09-04" / "figures"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY, R_LOAD, C_LOAD_PF = 3.3, 50.0, 2.0
# Read off the comprehensive CSV: 50 ps edges, rise at 5.000, fall at 6.790.
RISE_NS, FALL_NS, EDGE_NS, STOP_NS = 5.000, 6.790, 0.050, 22.0
REV = FALL_NS
CASE = "io_buf | short high | 1792 ps"
CMD_CLEAN = "InputDrivenTwoStateGateDelayCommandFull"
PROBES = ("gupcmd", "gdncmd", "guptarget", "gdntarget", "gup", "gdn", "ku", "kd")

# Last week's colours, unchanged, so a curve keeps the colour the audience
# already associates with it. cmd_clean takes the one that was spare.
C_SIL, C_NAT = "#111111", "#2B6CA3"
C_ORIG, C_FIX, C_CLEAN = "#C05621", "#7A3E9D", "#2E8B57"
C_MARK = "#777777"

# Two panels need more height than one; the deck gives both slides the same tall
# picture box and letterboxes whichever way each figure falls.
FIGSIZE_PAIR = (12.2, 6.2)
FIGSIZE_ONE = (12.2, 5.4)
GK_WINDOW = (7.0, 11.2)

plt.rcParams.update({"font.size": 14, "axes.titlesize": 15, "axes.labelsize": 14,
                     "xtick.labelsize": 12, "ytick.labelsize": 12,
                     "legend.fontsize": 12})


def read(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open()))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def cmd_clean_nodes() -> dict[str, np.ndarray]:
    """One ngspice run for cmd_clean's internal nodes, on the matching stimulus."""
    d = OUT / "cmd_clean"
    d.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", CMD_CLEAN, data, "Typical",
                                    str(d / "driver.sub"))
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {SUPPLY}  "
           f"{FALL_NS}n {SUPPLY}  {FALL_NS + EDGE_NS}n 0  {STOP_NS}n 0)")
    saves = " ".join(f"V(X1.{p})" for p in PROBES)
    deck = (dk.ngspice_header()
            + ".include driver.sub\n"
            + dk.supply("VCC", SUPPLY, name="Vdd")
            + f"Vin IN 0 {pwl}\n"
            + dk.supply("EN", sub.enable_level(SUPPLY), name="Ven")
            + sub.instance("X1")
            + dk.load("OUT", R_LOAD, C_LOAD_PF)
            + f".tran 0.002n {STOP_NS}n\n.save V(OUT) {saves}\n.end\n")
    sp, raw = d / "run.sp", d / "run.raw"
    if not (raw.exists() and sp.exists() and sp.read_text(encoding="utf-8") == deck):
        sp.write_text(deck, encoding="utf-8")
        if sl.ngspice(d, timeout_s=900) is None:
            raise RuntimeError("cmd_clean run failed")
    r = sl.parse_ngspice_raw(raw)
    out = {"time_ns": sl.time_ns(r), "pad": sl.trace(r, "out")}
    for p in PROBES:
        try:
            out[p] = sl.signal(r, f"v(x1.{p})", f"x1.{p}")
        except Exception:                              # noqa: BLE001
            out[p] = np.full(len(out["time_ns"]), np.nan)
    return out


def save(fig, name: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    # tight_layout, but not a tight bbox: the bbox would trim to the ink and
    # change the aspect the deck is expecting.
    fig.tight_layout()
    fig.savefig(FIGS / name, dpi=200)
    plt.close(fig)
    print(f"  {name}")


_TRAPZ = getattr(np, "trapezoid", None) or np.trapz


def tail_mean(t: np.ndarray, y: np.ndarray, rev: float | None = None,
              lo: float = 1.0, hi: float = 1.7) -> float:
    """Level over the window the offset is read in: 1.0-1.7 ns after the reversal.

    Late enough that the transition itself is over, early enough to be before the
    restore gate has taken any of the stranded charge back off.

    Time-weighted, not a plain mean of the samples. These files are on different
    grids -- the diagnosis CSVs are a uniform 5 ps, the stress matrix is ngspice's
    own adaptive steps and puts only 21 points in this window against 140 -- so an
    unweighted mean of the matrix samples is biased toward wherever the solver
    happened to cluster them. On io_buf 1792 that alone was worth 0.8 mV on the
    transistor reference, which is the same size as the differences being read.
    """
    rev = REV if rev is None else rev
    a, b = rev + lo, rev + hi
    w = (t >= a) & (t <= b)
    ts = np.concatenate(([a], t[w], [b]))
    ys = np.concatenate(([np.interp(a, t, y)], y[w], [np.interp(b, t, y)]))
    return float(_TRAPZ(ys, ts) / (b - a))


def gate_and_ku(c: dict, k: dict) -> None:
    """Last week's 12_gup_ku_fix_comparison, with cmd_clean added."""
    lo, hi = GK_WINDOW
    # Slice to the window before plotting. set_xlim alone leaves the y autoscale
    # on the whole 0-22 ns run, which includes the full 0-to-1 excursion, so the
    # residues being compared here get squashed into the bottom tenth of the axis.
    cw = (c["time_ns"] >= lo) & (c["time_ns"] <= hi)
    kw = (k["time_ns"] >= lo) & (k["time_ns"] <= hi)
    fig, ax = plt.subplots(2, 1, figsize=FIGSIZE_PAIR, sharex=True)
    panels = ((ax[0], "Pullup gate state", "GUP",
               c["original_gup"], c["fix_gup"], k["gup"]),
              (ax[1], "Pullup coefficient", "Ku",
               c["original_ku"], c["fix_ku"], k["ku"]))
    for a, title, ylab, orig, fix, clean in panels:
        a.plot(c["time_ns"][cw], orig[cw], color=C_ORIG, lw=2.4, label="original")
        a.plot(c["time_ns"][cw], fix[cw], color=C_FIX, lw=2.4, label="fix_old")
        a.plot(k["time_ns"][kw], clean[kw], color=C_CLEAN, lw=2.4,
               label="cmd_clean")
        a.axhline(0, color="#111", lw=1.0)
        a.set_ylabel(ylab)
        a.set_title(title, loc="left", fontweight="bold")
        a.set_xlim(lo, hi)
        a.grid(alpha=0.3)
        a.legend(loc="upper right")
    ax[1].set_xlabel("Time (ns)")
    fig.suptitle(f"{CASE} | GUP and Ku: original vs fix_old vs cmd_clean",
                 fontsize=16, fontweight="bold")
    save(fig, "cmd_clean_gate_and_ku.png")


def pad(c: dict, m: dict) -> None:
    """Last week's 11_pad_voltage_fix_comparison, with cmd_clean added.

    One panel: the full view. Last week's had a tail zoom under it.
    """
    fig, a = plt.subplots(figsize=FIGSIZE_ONE)
    a.plot(c["time_ns"], c["transistor_pad_v"], color=C_SIL, lw=3.4,
           label="HSPICE transistor")
    a.plot(c["time_ns"], c["native_pad_v"], color=C_NAT, lw=2.7,
           label="HSPICE native IBIS")
    a.plot(c["time_ns"], c["original_pad_v"], color=C_ORIG, lw=2.4,
           label="original")
    a.plot(c["time_ns"], c["fix_pad_v"], color=C_FIX, lw=2.4, label="fix_old")
    a.plot(m["time_ns"], m["pybis_pad"], color=C_CLEAN, lw=2.4, label="cmd_clean")
    for x in (RISE_NS, REV):
        a.axvline(x, color=C_MARK, ls="--", lw=1.25, zorder=0)
    a.axhline(0, color="#111", lw=1.0)
    a.set_xlim(4.6, 14.6)
    a.set_xlabel("Time (ns)")
    a.set_ylabel("Pad (V)")
    a.grid(alpha=0.3)
    a.legend(ncol=2, loc="upper right")
    fig.suptitle(f"{CASE} | pad voltage: original vs fix_old vs cmd_clean",
                 fontsize=16, fontweight="bold")
    save(fig, "cmd_clean_pad.png")


def pad_at_level(target: int, width_ps: int) -> bool:
    """Page 7's figure at one stress level. Returns False if a source is missing."""
    src = {"orig": FIX_PROBE / f"as_shipped_swing{target}_w{width_ps}ps.csv",
           "fix": FIX_PROBE / f"gate_and_tau_swing{target}_w{width_ps}ps.csv",
           "mat": MATRIX_DIR / f"io_buf_short_high_w{width_ps}ps.csv"}
    absent = [k for k, v in src.items() if not v.exists()]
    if absent:
        print(f"  swing{target}: missing {', '.join(src[k].name for k in absent)}")
        return False
    o, f, m = (read(src[k]) for k in ("orig", "fix", "mat"))
    rev = 5.0 + width_ps / 1000.0
    # The reference curves run 0-22 ns, but original and fix_old were only saved
    # from half a nanosecond before the reversal. Every level therefore gets the
    # same relative window, which is also what makes the four comparable.
    lo, hi = rev - 0.45, rev + 7.80
    fig, a = plt.subplots(figsize=FIGSIZE_ONE)
    a.plot(m["time_ns"], m["silicon_pad"], color=C_SIL, lw=3.4,
           label="HSPICE transistor")
    a.plot(m["time_ns"], m["hspice_pad"], color=C_NAT, lw=2.7,
           label="HSPICE native IBIS")
    a.plot(o["time_ns"], o["pad"], color=C_ORIG, lw=2.4, label="original")
    a.plot(f["time_ns"], f["pad"], color=C_FIX, lw=2.4, label="fix_old")
    a.plot(m["time_ns"], m["pybis_pad"], color=C_CLEAN, lw=2.4, label="cmd_clean")
    a.axvline(rev, color=C_MARK, ls="--", lw=1.25, zorder=0)
    a.axhline(0, color="#111", lw=1.0)
    a.set_xlim(lo, hi)
    a.set_xlabel("Time (ns)")
    a.set_ylabel("Pad (V)")
    a.grid(alpha=0.3)
    a.legend(ncol=2, loc="upper right")
    fig.suptitle(f"io_buf | short high | {width_ps} ps ({target}% swing) | "
                 f"pad voltage: original vs fix_old vs cmd_clean",
                 fontsize=16, fontweight="bold")
    save(fig, f"cmd_clean_pad_swing{target}.png")

    mv = lambda d, col: tail_mean(d["time_ns"], d[col], rev) * 1e3  # noqa: E731
    ref = mv(m, "silicon_pad")
    lv = {"original": mv(o, "pad"), "fix_old": mv(f, "pad"),
          "cmd_clean": mv(m, "pybis_pad"), "native": mv(m, "hspice_pad")}
    # The target is the transistor's own level, not zero -- a build that lands
    # below the transistor is not "better than perfect".
    print(f"    level mV   transistor {ref:5.2f}   "
          + "   ".join(f"{k} {v:6.2f}" for k, v in lv.items()))
    print(f"    error mV   {'':16}"
          + "   ".join(f"{k} {abs(v - ref):6.2f}" for k, v in lv.items()))
    return True


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = [p for p in (CHAIN, MATRIX) if not p.exists()]
    if missing:
        print("missing: " + ", ".join(str(p) for p in missing))
        return 1
    c, m = read(CHAIN), read(MATRIX)
    k = cmd_clean_nodes()

    # The regenerated run must agree with the matrix result it stands in for.
    g = np.arange(5.0, 12.0, 0.005)
    a = np.interp(g, m["time_ns"], m["pybis_pad"])
    b = np.interp(g, k["time_ns"], k["pad"])
    print(f"  regenerated cmd_clean vs the matrix: max|diff| "
          f"{np.abs(a - b).max() * 1e3:.2f} mV, rms "
          f"{np.sqrt(np.mean((a - b) ** 2)) * 1e3:.2f} mV")

    gate_and_ku(c, k)
    pad(c, m)

    print("\n  the same pad figure at each stress level:")
    for target, width_ps in LEVELS:
        pad_at_level(target, width_ps)

    # Retired: an earlier draft built four figures here, before the set was cut
    # to these two. Deleted rather than left behind, so nothing stale gets reused.
    for stale in ("cmd_clean_0_command_node.png", "cmd_clean_1_command.png",
                  "cmd_clean_2_gate_and_ku.png", "cmd_clean_3_pad.png"):
        p = FIGS / stale
        if p.exists():
            p.unlink()
            print(f"  removed {stale}")

    print("\n  tail, 1.0-1.7 ns after the reversal:")
    for lab, t, y in (("GUPCMD original ", c["time_ns"], c["original_gupcmd"]),
                      ("GUPCMD fix_old  ", c["time_ns"], c["fix_gupcmd"]),
                      ("GUPCMD cmd_clean", k["time_ns"], k["gupcmd"])):
        print(f"    {lab} {tail_mean(t, y):+.5f}")
    for lab, t, y in (("transistor", c["time_ns"], c["transistor_pad_v"]),
                      ("native", c["time_ns"], c["native_pad_v"]),
                      ("original", c["time_ns"], c["original_pad_v"]),
                      ("fix_old", c["time_ns"], c["fix_pad_v"]),
                      ("cmd_clean", m["time_ns"], m["pybis_pad"])):
        print(f"    pad {lab:<11} {tail_mean(t, y) * 1e3:7.2f} mV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
