#!/usr/bin/env python3
"""Does the timing shift accumulate *within* one event, or is it a fixed offset?

Every timing number in this study so far is **one crossing per case**, almost
always the 50% point. That cannot distinguish a model which is uniformly N ps
late from one which starts aligned and falls progressively further behind as the
transition proceeds. Those are different defects with different causes.

Method: crossing times at 10%, 15% ... 90% of the **transistor's own** excursion,
model minus transistor, taken separately on the way *into* the event and on the
way *out* of it. A fixed offset gives a flat ladder; accumulation gives a sloped
one.

"Into" and "out" rather than "rising" and "falling", because the two directions
are mirror images: a `short_high` pulse goes up into the event and comes back
down, a `short_low` pulse dips down into it and comes back up. The interesting
side turned out to be the way *out*, on both.

Three devices, both directions, plus an unstressed full-swing control wherever
one exists on disk. The control is what separates "our model does this" from
"IBIS does this": if native drifts by the same amount on a clean transition, the
accumulation is not ours.

    py -3.14 scripts/timing_shift_accumulation.py
"""
from __future__ import annotations

import csv
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
MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
GATE = R / "stress_method_matrix_2026-08-20" / "gate_state" / "waveforms"
OUT = R / "timing_shift_accumulation_2026-09-04"
FIGS = R / "meeting_deck_2026-09-04" / "figures"

# The campaign puts a short_high event at 5 ns and a short_low one at 10 ns.
EVENT_NS = {"short_high": 5.0, "short_low": 10.0}

# Unstressed benches: transistor / native / pybis, same 5 ns rise, 15 ns fall.
# ex2 has none -- the only ex2 full-swing bench on disk is the open-drain
# variant, which is a different buffer, so ex2 is reported stressed-only.
CONTROLS = {
    "io_buf": (R / "defect_b_full_swing_2026-09-03" / "transistor" / "run.tr0",
               R / "defect_b_full_swing_2026-09-03" / "native" / "run.tr0",
               R / "defect_b_full_swing_2026-09-03" / "pybis_plain" / "run.raw"),
    "inv_chain": (R / "inv_chain_variants_full_swing_2026-09-03" / "base8"
                  / "transistor" / "run.tr0",
                  R / "inv_chain_variants_full_swing_2026-09-03" / "base8"
                  / "native_ibis" / "run.tr0",
                  R / "inv_chain_variants_full_swing_2026-09-03" / "base8"
                  / "pybis" / "run.raw"),
}

# ex2's control was built later, by scripts/ex2_full_swing_control.py, and is
# already resampled onto one grid -- so it arrives as a CSV rather than a trio of
# raw simulator outputs.
CONTROL_CSV = {"ex2": R / "ex2_full_swing_control_2026-09-04" / "full_swing.csv"}

C_NAT, C_ORIG, C_CLEAN = "#2B6CA3", "#C05621", "#2E8B57"
FRACS = np.arange(0.10, 0.91, 0.05)

plt.rcParams.update({"font.size": 12, "axes.titlesize": 13, "axes.labelsize": 12,
                     "xtick.labelsize": 10, "ytick.labelsize": 10,
                     "legend.fontsize": 10})


def read(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open()))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def event_geometry(t: np.ndarray, ref: np.ndarray, start: float, sign: int):
    """(quiet level before the event, the excursion's extremum, its time)."""
    base = float(np.median(ref[(t > start - 0.6) & (t < start - 0.1)]))
    w = (t >= start) & (t <= start + 5.0)
    idx = np.argmax(ref[w] * sign)
    return base, float(ref[w][idx]), float(t[w][idx])


def excursion(t: np.ndarray, y: np.ndarray, start: float, sign: int) -> float:
    """How far this trace actually travels during the event."""
    base, peak, _ = event_geometry(t, y, start, sign)
    return abs(peak - base)


def ladder(t: np.ndarray, ref: np.ndarray, y: np.ndarray, start: float,
           sign: int, outward: bool, strict: bool = True) -> np.ndarray:
    """Crossing-time difference at each fraction of the reference's excursion.

    `outward=False` is the way into the event, `True` the way back out. Both
    curves are asked for the same absolute voltage, so each number is a
    horizontal distance between the two traces -- which is what a timing shift
    means.
    """
    base, peak, t_peak = event_geometry(t, ref, start, sign)
    y_reach = excursion(t, y, start, sign)
    out, times, rtimes = [], [], []
    for f in FRACS:
        level = base + f * (peak - base)
        rising = (sign > 0) != outward      # into: follows sign; out: opposite
        after = t_peak if outward else start - 0.2
        a = sl.cross(t, ref, level, rising=rising, after=after)
        b = sl.cross(t, y, level, rising=rising, after=after)
        ok = np.isfinite(a) and np.isfinite(b)
        # A level the model never reaches has no crossing to compare, and
        # cross() will happily return one from a later ripple -- which is how
        # io_buf short_low produced "shifts" of 1500 ps.
        if ok:
            ok = abs(level - base) <= y_reach
        # Anything outside the event window is a different event.
        if ok:
            ok = (a - start) < 4.0 and (b - start) < 4.0
        out.append((b - a) * 1e3 if ok else np.nan)
        times.append(b if ok else np.nan)
        rtimes.append(a if ok else np.nan)
    # The way out is travelled from the extremum back to the base, so the ladder
    # is visited 90% first and 10% last. Reverse it so index order is time order
    # on both sides and "first/last/change" mean the same thing throughout.
    arr, tt, rt = np.array(out), np.array(times), np.array(rtimes)
    if outward:
        arr, tt, rt = arr[::-1], tt[::-1], rt[::-1]
    # The ladder assumes the model crosses each level once, in order. A ringing
    # recovery crosses several times and `cross` returns the first, so the
    # crossing sequence jumps around and the differences stop being delays --
    # this is how io_buf short_low produced "shifts" of over a nanosecond.
    # Reject the whole ladder rather than report part of it.
    g = np.isfinite(tt)
    if g.sum() > 1 and np.any(np.diff(tt[g]) < -0.020):
        return np.full(len(arr), np.nan)
    # A shift longer than the reference's own transition is not a shift: the two
    # curves are no longer the same feature seen at two times. io_buf short_low
    # reports ~900 ps against a transition an order of magnitude shorter, because
    # the model over-dips so far that its recovery is a different shape.
    # The *reference's* own span, not the model's -- using the model's lets a
    # badly stretched model licence its own error.
    rg = np.isfinite(rt)
    span = float(rt[rg][-1] - rt[rg][0]) if rg.sum() > 1 else 0.0
    # `strict=False` for a caller that has already established the pairing is
    # sound -- the C_comp sweep deliberately changes the edge rate, so a shift
    # larger than the reference's own edge is the expected result there rather
    # than a sign of mismatched features.
    if strict and g.sum() > 1 and np.nanmax(np.abs(arr)) > max(span, 0.05) * 1e3:
        return np.full(len(arr), np.nan)
    return arr


def swing(sh: np.ndarray) -> float:
    """Change across the ladder in time order, ps. NaN if under two points."""
    good = np.isfinite(sh)
    if good.sum() < 2:
        return float("nan")
    v = sh[good]
    return float(v[-1] - v[0])


def both_ladders(t, ref, y, start, sign, is_ctrl, fall_ns=15.0):
    """(into, out) ladders for one case.

    On a stressed pulse the way out is the return leg of the same event, so it is
    the same ladder walked backwards. On the unstressed control there is no
    return leg -- the pad settles and comes back down ten nanoseconds later as a
    transition of its own -- so the way out is that second edge, measured as its
    own approach. Both give "the pad coming back down", which is what the
    stressed cases' outward leg is, and that is what makes the two comparable.
    """
    into = ladder(t, ref, y, start, sign, outward=False)
    if is_ctrl:
        return into, ladder(t, ref, y, fall_ns, -sign, outward=False)
    return into, ladder(t, ref, y, start, sign, outward=True)


def comparable(t, ref, y, start, sign, tol=0.30) -> bool:
    """Do the two traces travel far enough alike for a horizontal gap to mean
    anything? If the model's excursion differs by more than `tol`, the curves do
    not overlap in amplitude and a crossing-time difference is not a timing
    measurement. `native_stress_law` hit exactly this on io_buf short_low.
    """
    a, b = excursion(t, ref, start, sign), excursion(t, y, start, sign)
    return a > 1e-6 and abs(b - a) / a <= tol


def control_case(device: str) -> dict[str, np.ndarray] | None:
    csv_path = CONTROL_CSV.get(device)
    if csv_path is not None and csv_path.exists():
        d = read(csv_path)
        d["original_pad"] = None
        # That bench is a 6 ns pulse from 5 ns, so its falling edge is at 11 ns.
        # The other two controls are 5/15 ns runs. Hardcoding 15 here measured
        # ex2's settled tail as if it were a transition and produced -830 ps.
        d["fall_ns"] = np.array([11.0])
        return d
    paths = CONTROLS.get(device)
    if paths is None or not all(p.exists() for p in paths):
        return None
    tr, nat, pyb = paths
    a, b = sl.parse_hspice_tr0(tr), sl.parse_hspice_tr0(nat)
    c = sl.parse_ngspice_raw(pyb)
    grid = np.arange(4.5, 20.0, 0.002)
    return {"time_ns": grid,
            "silicon_pad": np.interp(grid, sl.time_ns(a), sl.trace(a, "pad")),
            "hspice_pad": np.interp(grid, sl.time_ns(b), sl.trace(b, "pad")),
            "pybis_pad": np.interp(grid, sl.time_ns(c), sl.trace(c, "out")),
            "original_pad": None, "fall_ns": np.array([15.0])}


def collect(device: str, direction: str):
    """Every stressed case for one device/direction, widest (least stressed) first."""
    cases = []
    for path in sorted(MATRIX.glob(f"{device}_{direction}_w*ps.csv"),
                       key=lambda p: -int(p.stem.split("_w")[1].replace("ps", ""))):
        width = int(path.stem.split("_w")[1].replace("ps", ""))
        d = read(path)
        gs = GATE / path.name
        d["original_pad"] = read(gs)["pybis_pad"] if gs.exists() else None
        cases.append((f"{width} ps", d, EVENT_NS[direction], False))
    return cases


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    print("  shift vs the transistor across the ladder, ps, in time order.")
    print("  'into' = base to the excursion's extremum, 'out' = back again.\n")
    header = (f"    {'device / direction':<26}{'case':<12}{'build':<11}"
              f"{'into: first':>12}{'last':>7}{'change':>8}"
              f"{'  |  out: first':>16}{'last':>7}{'change':>8}")
    for device in ("io_buf", "inv_chain", "ex2"):
        for direction in ("short_high", "short_low"):
            sign = 1 if direction == "short_high" else -1
            cases = collect(device, direction)
            ctrl = control_case(device) if direction == "short_high" else None
            if ctrl is not None:
                cases.append(("full swing", ctrl, 5.0, True))
            if not cases:
                continue
            print(header)
            for label, d, start, is_ctrl in cases:
                t, ref = d["time_ns"], d["silicon_pad"]
                for name, key in (("native", "hspice_pad"),
                                  ("original", "original_pad"),
                                  ("cmd_clean", "pybis_pad")):
                    y = d.get(key)
                    if y is None:
                        continue
                    if not comparable(t, ref, y, start, sign):
                        print(f"    {device + ' ' + direction:<26}{label:<12}"
                              f"{name:<11}  excursion differs by >30%, "
                              f"not a timing comparison")
                        continue
                    fall = float(d.get("fall_ns", [15.0])[0])
                    a, b = both_ladders(t, ref, y, start, sign, is_ctrl, fall)
                    if not np.isfinite(b).any():
                        print(f"    {device + ' ' + direction:<26}{label:<12}"
                              f"{name:<11}  outward leg is not monotonic "
                              f"(ringing), not a timing comparison")
                        continue
                    ga, gb = np.isfinite(a), np.isfinite(b)
                    fa = f"{a[ga][0]:+.0f}" if ga.any() else "-"
                    la = f"{a[ga][-1]:+.0f}" if ga.any() else "-"
                    fb = f"{b[gb][0]:+.0f}" if gb.any() else "-"
                    lb = f"{b[gb][-1]:+.0f}" if gb.any() else "-"
                    print(f"    {device + ' ' + direction:<26}{label:<12}"
                          f"{name:<11}{fa:>12}{la:>7}{swing(a):>+8.0f}"
                          f"{fb:>16}{lb:>7}{swing(b):>+8.0f}")
                    rows.append({"device": device, "direction": direction,
                                 "case": label, "build": name,
                                 "into_change_ps": round(swing(a), 1),
                                 "out_change_ps": round(swing(b), 1),
                                 "out_first_ps": round(float(b[gb][0]), 1) if gb.any() else "",
                                 "out_last_ps": round(float(b[gb][-1]), 1) if gb.any() else ""})
            print()

    path = OUT / "ladder_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path.relative_to(ROOT)}")

    # One panel per device/direction, the outward ladder only -- that is where
    # the accumulation lives and a six-panel figure of both sides is unreadable.
    combos = [(dev, dr) for dev in ("io_buf", "inv_chain", "ex2")
              for dr in ("short_high", "short_low")]
    fig, axes = plt.subplots(2, 3, figsize=(13.2, 7.4))
    for ax, (device, direction) in zip(axes.ravel(), combos):
        sign = 1 if direction == "short_high" else -1
        cases = collect(device, direction)
        ctrl = control_case(device) if direction == "short_high" else None
        for label, d, start, is_ctrl in cases:
            t, ref = d["time_ns"], d["silicon_pad"]
            for name, key, colour in (("native", "hspice_pad", C_NAT),
                                      ("cmd_clean", "pybis_pad", C_CLEAN)):
                y = d.get(key)
                if y is None:
                    continue
                lad = both_ladders(t, ref, y, start, sign, False)[1]
                ax.plot(np.linspace(0, 100, len(lad)), lad,
                        color=colour, lw=1.2, alpha=0.45)
        if ctrl is not None:
            for name, key, colour in (("native", "hspice_pad", C_NAT),
                                      ("cmd_clean", "pybis_pad", C_CLEAN)):
                lad = both_ladders(ctrl["time_ns"], ctrl["silicon_pad"],
                                   ctrl[key], 5.0, 1, True,
                                   float(ctrl.get("fall_ns", [15.0])[0]))[1]
                ax.plot(np.linspace(0, 100, len(lad)), lad,
                        color=colour, lw=3.0, label=f"{name}, full swing")
        ax.axhline(0, color="#111", lw=1.0)
        ax.set_title(f"{device} {direction}", fontsize=12, fontweight="bold")
        ax.set_xlabel("position through the leg  (early → late)")
        ax.grid(alpha=0.3)
        if ctrl is not None:
            ax.legend(loc="best", fontsize=9)
    axes[0][0].set_ylabel("model − transistor (ps)")
    axes[1][0].set_ylabel("model − transistor (ps)")
    fig.suptitle("The way out of the event: thin = stressed cases, "
                 "thick = unstressed control", fontsize=15, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "timing_shift_ladder.png", dpi=200)
    plt.close(fig)
    print("  timing_shift_ladder.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
