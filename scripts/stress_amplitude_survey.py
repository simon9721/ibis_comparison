#!/usr/bin/env python3
"""Amplitude survey of stressed cases: transistor vs native IBIS vs pybis.

Pure analysis -- every waveform already exists on disk, nothing is re-simulated.

Two things this fixes over the first pass:

* **Direction-aware excursion.** `short_high` starts low and makes a brief
  excursion up; `short_low` rises to a plateau and then makes a brief dip back
  down. Measuring `min()` over the whole trace, as I did first, returns the
  initial rest level for `short_low` rather than the dip, which is why those
  families looked like they had no dynamic range.
* **The depth-target family.** Defect B was quoted on depth-target cases, and
  only the width-sweep family had been measured. Both are covered here.

The excursion is measured identically for all three builds, so the comparison
does not depend on what `depth_target` is a fraction of.

    py -3.14 scripts/stress_amplitude_survey.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

FAMILIES = {
    "width-sweep": ROOT / "results" / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms",
    "depth-target": ROOT / "results" / "_baseline_edgecmd" / "waveforms",
}


def excursion(t: np.ndarray, v: np.ndarray, direction: str) -> float:
    """Magnitude of the stressed event, measured from the level it departs from.

    short_high: rest low -> brief rise. The reference is the pre-event rest level
    and the event is the maximum.

    short_low: rest low -> full rise to a plateau -> brief dip -> recover. The
    reference is the plateau (taken as the settled final level) and the event is
    the minimum *after* the pad has first reached that plateau, so the initial
    rest level is not mistaken for the dip.
    """
    if direction == "short_high":
        base = float(np.median(v[t < t[0] + 0.2 * (t[-1] - t[0])]))
        return float(v.max() - base)
    settled = float(np.median(v[t > t[0] + 0.9 * (t[-1] - t[0])]))
    reached = np.where(v > 0.9 * settled)[0]
    if reached.size == 0:
        return float("nan")
    after = v[reached[0]:]
    return float(settled - after.min())


def rows_for(folder: Path):
    out = []
    for f in sorted(folder.glob("*.csv")):
        if "_short_" not in f.stem:
            continue
        device = f.stem.split("_short")[0]
        direction = "short_" + f.stem.split("_short_")[1].split("_")[0]
        r = list(csv.DictReader(f.open()))
        col = lambda k: np.array([float(x[k]) for x in r])  # noqa: E731
        t = col("time_ns")
        out.append((device, direction, f.stem,
                    excursion(t, col("silicon_pad"), direction),
                    excursion(t, col("hspice_pad"), direction),
                    excursion(t, col("pybis_pad"), direction)))
    return out


def main() -> int:
    grand = {"native": 0, "pybis": 0}
    for fam, folder in FAMILIES.items():
        if not folder.exists():
            print(f"\n### {fam}: {folder} missing")
            continue
        print(f"\n{'='*84}\n### {fam}   ({folder.relative_to(ROOT)})\n{'='*84}")
        data = rows_for(folder)
        by = {}
        for d, dirn, stem, si, hs, py in data:
            by.setdefault((d, dirn), []).append((stem, si, hs, py))
        for (dev, dirn), items in sorted(by.items()):
            print(f"\n{dev} {dirn}")
            print(f"  {'case':<34}{'tx':>8}{'native':>8}{'pybis':>8} |"
                  f"{'nat err':>9}{'pyb err':>9}  winner")
            nb = pb = 0
            for stem, si, hs, py in items:
                if not np.isfinite(si):
                    continue
                en, ep = (hs - si) * 1e3, (py - si) * 1e3
                w = "pybis" if abs(ep) < abs(en) else "native"
                nb += w == "native"
                pb += w == "pybis"
                short = stem.replace(f"{dev}_{dirn}_", "")
                print(f"  {short:<34}{si:>8.3f}{hs:>8.3f}{py:>8.3f} |"
                      f"{en:>8.0f}m{ep:>8.0f}m  {w}")
            grand["native"] += nb
            grand["pybis"] += pb
            if nb + pb:
                print(f"  -> pybis closer on {pb}/{nb+pb}")
    tot = grand["native"] + grand["pybis"]
    print(f"\n{'='*84}\nOVERALL: pybis closer on {grand['pybis']}/{tot}, "
          f"native closer on {grand['native']}/{tot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
