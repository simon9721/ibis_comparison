#!/usr/bin/env python3
"""Does the outward timing accumulation scale with C_comp, within one device?

`timing_shift_accumulation_2026-09-04` found that the model falls progressively
further behind the transistor on the way *out* of an event, that native IBIS does
the same by the same amount, and that the size of it tracks the buffer's declared
C_comp across three devices:

    inv_chain  0.468 pF  ->   +1 ps
    io_buf     1.2   pF  ->  +67 ps
    ex2        5.0   pF  ->  +54..+103 ps (stressed only)

Three points, and the devices differ in supply, edge rate and drive as well as in
C_comp, so that is a correlation and not a mechanism. This is the within-device
control it needs: hold the buffer fixed and change only the explicit C_comp in the
generated subcircuit.

Both directions, because they fail differently:

* **io_buf**, which accumulates +67 ps, scaled *down*. If C_comp is the cause the
  accumulation should shrink toward zero.
* **base8**, which accumulates +2 ps, scaled *up* to io_buf's and ex2's declared
  values. If C_comp is the cause the accumulation should appear.

A one-directional test would not distinguish "C_comp causes it" from "C_comp
happens to be large on the devices that have it".

Everything is compared against that device's own HSPICE transistor run, which is
untouched -- only the model changes.

    py -3.14 scripts/ccomp_accumulation_test.py
"""
from __future__ import annotations

import re
import shutil
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
from timing_shift_accumulation import FRACS, ladder, swing  # noqa: E402

R = ROOT / "results"
OUT = R / "ccomp_accumulation_2026-09-04"
FIGS = R / "meeting_deck_2026-09-04" / "figures"

# device -> (pybis run dir to clone, transistor .tr0, nominal C_comp F, scales)
BENCH = {
    "io_buf": (R / "defect_b_full_swing_2026-09-03" / "pybis_plain",
               R / "defect_b_full_swing_2026-09-03" / "transistor" / "run.tr0",
               1.2e-12, (1.0, 0.5, 0.25, 0.0)),
    # base8's nominal is 0.468 pF; 2.56x reaches io_buf's 1.2 pF and 10.7x ex2's
    # 5.0 pF, so the scales land on the other two devices' declared values.
    "base8": (R / "inv_chain_variants_full_swing_2026-09-03" / "base8" / "pybis",
              R / "inv_chain_variants_full_swing_2026-09-03" / "base8"
              / "transistor" / "run.tr0",
              4.68e-13, (1.0, 2.56, 10.7)),
}

RISE_NS, FALL_NS = 5.0, 15.0


def run_at(device: str, scale: float) -> tuple[np.ndarray, np.ndarray]:
    """The device's pybis model with C_comp scaled, on its own bench."""
    src, _, nominal, _ = BENCH[device]
    d = OUT / device / f"x{scale:g}".replace(".", "p")
    d.mkdir(parents=True, exist_ok=True)
    for name in ("run.sp", "driver.sub"):
        shutil.copyfile(src / name, d / name)
    sub = (d / "driver.sub").read_text(encoding="utf-8")
    # Rewrite the one parameter. C2 reads {C_comp}, so nothing else has to move.
    sub, n = re.subn(r"^\.param C_comp = \S+$",
                     f".param C_comp = {nominal * scale:.6e}", sub,
                     count=1, flags=re.M)
    if n != 1:
        raise RuntimeError(f"{device}: could not find the C_comp parameter")
    (d / "driver.sub").write_text(sub, encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=900) is None:
            raise RuntimeError(f"{device} x{scale} failed -- see ngspice.log")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    return sl.time_ns(raw), sl.trace(raw, "out")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for device, (_, tr_path, nominal, scales) in BENCH.items():
        tr = sl.parse_hspice_tr0(tr_path)
        grid = np.arange(4.5, 20.0, 0.002)
        ref = np.interp(grid, sl.time_ns(tr), sl.trace(tr, "pad"))
        print(f"\n  {device}: nominal C_comp {nominal * 1e12:.3f} pF")
        print(f"    {'C_comp':>10}{'into: change':>14}{'out: first':>12}"
              f"{'last':>7}{'out: change':>13}")
        rows = []
        for scale in scales:
            t, y = run_at(device, scale)
            y = np.interp(grid, t, y)
            into = ladder(grid, ref, y, RISE_NS, 1, outward=False, strict=False)
            # The way out of a full swing is the falling edge ten nanoseconds
            # later, measured as its own approach -- same convention as the
            # control in timing_shift_accumulation.
            out = ladder(grid, ref, y, FALL_NS, -1, outward=False, strict=False)
            g = np.isfinite(out)
            first = float(out[g][0]) if g.any() else np.nan
            last = float(out[g][-1]) if g.any() else np.nan
            print(f"    {nominal * scale * 1e12:8.3f}pF{swing(into):>14.0f}"
                  f"{first:>12.0f}{last:>7.0f}{swing(out):>13.0f}")
            rows.append((nominal * scale * 1e12, out, swing(out)))
        results[device] = rows

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    for ax, (device, rows) in zip(axes, results.items()):
        shades = plt.cm.viridis(np.linspace(0.15, 0.85, len(rows)))
        for (cc, out, _), colour in zip(rows, shades):
            ax.plot(np.linspace(0, 100, len(out)), out, "o-", color=colour,
                    lw=2.0, ms=4, label=f"{cc:.2f} pF")
        ax.axhline(0, color="#111", lw=1.0)
        ax.set_title(f"{device}, full swing", fontsize=13, fontweight="bold")
        ax.set_xlabel("position through the leg  (early → late)")
        ax.grid(alpha=0.3)
        ax.legend(title="explicit C_comp", fontsize=10)
    axes[0].set_ylabel("model − transistor (ps), coming out")
    fig.suptitle("Does the outward accumulation scale with C_comp?",
                 fontsize=15, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "ccomp_accumulation.png", dpi=200)
    plt.close(fig)
    print("\n  ccomp_accumulation.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
