#!/usr/bin/env python3
"""Check the stress-matrix waveforms for defects a mean error cannot show.

An RMSE ranks methods but hides shape. A model can win on error while producing
a trace no buffer would produce -- an extra dip, a response that starts before
the input edge, a peak in the wrong place -- and those are the failures that
matter when the model is driving a channel simulation rather than a scoreboard.

Three measures, all against silicon on the same grid:

  glitches   extra local extrema in the model's pad between the reverse edge and
             3 ns after it, beyond the number silicon shows. This is what caught
             the transport-delay command splitting one pulse into two.
  peak       how far the model's extreme pad excursion misses silicon's, in mV,
             signed so over-response is positive.
  early      how long before silicon the model first leaves its starting rail.
             Positive means the model moves first, which is unphysical.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402

from run_stress_method_matrix import METHODS, case_tag, stress_cases  # noqa: E402

# A wobble smaller than this is numerical, not a feature the eye would call a
# glitch; chosen well below the smallest real excursion in the matrix.
GLITCH_V = 0.02


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def extrema_count(t, y, lo, hi):
    """Counts local extrema whose swing either side exceeds GLITCH_V."""
    m = (t >= lo) & (t <= hi)
    y = y[m]
    if len(y) < 5:
        return 0
    d = np.diff(y)
    sign = np.sign(d)
    sign = sign[sign != 0]
    if len(sign) < 2:
        return 0
    turns = np.where(np.diff(sign) != 0)[0]
    count = 0
    for i in turns:
        left = y[: i + 1]
        right = y[i + 1:]
        if len(left) and len(right):
            if min(y[i] - left.min(), y[i] - right.min()) > GLITCH_V or \
               min(left.max() - y[i], right.max() - y[i]) > GLITCH_V:
                count += 1
    return count


def departs(t, y, rail, edge_ns):
    """First time after the input edge that the trace leaves its rail."""
    m = t >= edge_ns - 0.5
    tt, yy = t[m], y[m]
    idx = np.where(np.abs(yy - rail) > GLITCH_V)[0]
    return float(tt[idx[0]]) if len(idx) else float("nan")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path,
                        default=ROOT / "results" / "stress_method_matrix_2026-08-20")
    args = parser.parse_args()
    root = args.matrix if args.matrix.is_absolute() else ROOT / args.matrix
    available = [k for k, _, _ in METHODS if (root / k / "waveforms").exists()]

    totals: dict[str, dict[str, list]] = {k: {"glitch": [], "peak": [], "early": []}
                                          for k in available}
    for device, direction, widths in stress_cases():
        for _, width_ps in widths:
            tag = case_tag(device, direction, width_ps)
            edge_ns = 5.0 if direction == "short_high" else 10.0
            t_rev = edge_ns + width_ps / 1000.0
            for key in available:
                path = root / key / "waveforms" / f"{tag}.csv"
                if not path.exists():
                    continue
                d = load(path)
                t = d["time_ns"]
                sil, mod = d["silicon_pad"], d["pybis_pad"]
                rail = float(np.interp(edge_ns - 0.3, t, sil))
                high = direction == "short_high"
                sil_peak = float(sil.max() if high else sil.min())
                mod_peak = float(mod.max() if high else mod.min())
                over = (mod_peak - sil_peak) if high else (sil_peak - mod_peak)
                extra = (extrema_count(t, mod, t_rev, t_rev + 3.0)
                         - extrema_count(t, sil, t_rev, t_rev + 3.0))
                lead = departs(t, sil, rail, edge_ns) - departs(t, mod, rail, edge_ns)
                totals[key]["glitch"].append(max(0, extra))
                totals[key]["peak"].append(over * 1000.0)
                if np.isfinite(lead):
                    totals[key]["early"].append(lead * 1000.0)

    print("waveform shape against silicon, all stress cases")
    print("glitches = extra local extrema after the reversal, summed over cases")
    print("peak     = mean over-response at the pad extreme, mV (+ = overshoots)")
    print("early    = mean time the model moves before silicon does, ps (+ = too early)")
    print()
    print(f"{'method':18s} {'cases':>6s} {'glitches':>10s} {'peak mV':>10s} {'early ps':>10s}")
    for key in available:
        v = totals[key]
        if not v["peak"]:
            continue
        print(f"{key:18s} {len(v['peak']):6d} {sum(v['glitch']):10d} "
              f"{np.mean(v['peak']):10.1f} "
              f"{np.mean(v['early']) if v['early'] else float('nan'):10.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
