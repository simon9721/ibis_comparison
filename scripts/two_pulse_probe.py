#!/usr/bin/env python3
"""Two identical stressed pulses: does the second one carry the first one's error?

Same benches as the pulse train (`pulse_train_accumulation.py`), same three builds
(transistor, native HSPICE IBIS, ours = cmd_clean), two pulses of the same width W with
a gap G between the first falling edge and the second rising edge:

    settled    G = 6 ns, the pad and every internal node have returned to rest
    unsettled  G = W, 50 % duty, the second pulse lands on the tail of the first

Per pulse: model pad-peak time minus the transistor's, and the best-fit lag.

    py -3.14 scripts/two_pulse_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pulse_train_accumulation as pt  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

OUT = ROOT / "results" / "two_pulse_2026-09-11"
FIG = ROOT / "results" / "meeting_deck_2026-09-11" / "figures" / "two_pulses.png"
C_SI, C_NAT, C_CLEAN = "#111111", "#2B6CA3", "#2E8B57"
CASES = [("io_buf", 1.792), ("ex2", 0.858)]
GAPS = [("settled", 6.0), ("unsettled", None)]   # None -> gap = W (50 % duty)


def make_edges(W, G):
    return [5.0, 5.0 + W, 5.0 + W + G, 5.0 + 2 * W + G]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pt.OUT = OUT
    hspice = Path(default_hspice())
    fig, axes = plt.subplots(2, 2, figsize=(17, 8.6))
    for c, (dev, W) in enumerate(CASES):
        ibis, sup, _ = pt.DEV[dev]
        device = next(x for x in base.DEVICES if x.device_id == dev)
        for r, (tag, G) in enumerate(GAPS):
            G = W if G is None else G
            edges = make_edges(W, G)
            stop = edges[-1] + 8.0
            pt.edges = lambda width, n, e=edges: e
            pt.stop_ns = lambda width, n, s=stop: s
            print(f"  {dev} {tag}: W {W*1e3:.0f} ps, gap {G*1e3:.0f} ps ...")
            t_si, si = pt.transistor(dev, device, W, 2, tag, hspice)
            t_n, nat = pt.native(dev, ibis, sup, W, 2, tag, hspice)
            t_o, our = pt.ours(dev, ibis, sup, W, 2, tag)
            a = axes[r, c]
            x0, x1 = 4.5, edges[-1] + 3.0
            for t, y, col, lw, ls, lab in ((t_si, si, C_SI, 3.0, "-", "transistor"), (t_n, nat, C_NAT, 1.6, "-", "native HSPICE IBIS"),
                                            (t_o, our, C_CLEAN, 1.9, "--", "ours (cmd_clean)")):
                m = (t > x0) & (t < x1)
                a.plot(t[m], y[m], color=col, lw=lw, ls=ls, label=lab)
            for e in edges:
                a.axvline(e, color="#888", ls="--", lw=0.9)
            # per-pulse numbers
            lines = []
            for k, (lo, hi) in enumerate(((edges[0], edges[1] + G), (edges[2], edges[3] + 3.0)), 1):
                g = np.arange(lo, hi, 0.002)
                asi = np.interp(g, t_si, si)
                ia = int(np.argmax(asi))
                parts = []
                for name, t, y in (("native", t_n, nat), ("ours", t_o, our)):
                    b = np.interp(g, t, y)
                    ib = int(np.argmax(b))
                    parts.append(f"{name} peak {(g[ib]-g[ia])*1e3:+.0f} ps / {(b[ib]-asi[ia])*1e3:+.0f} mV")
                lines.append(f"pulse {k}: " + ", ".join(parts))
            a.set_title(f"{dev}, two {W*1e3:.0f} ps pulses, gap {G*1e3:.0f} ps ({tag})\n" + "\n".join(lines), fontsize=9.5, fontweight="bold")
            a.grid(alpha=0.3)
            a.set_xlabel("time (ns)")
            if c == 0:
                a.set_ylabel("pad (V)")
            if r == 0 and c == 0:
                a.legend(fontsize=8, loc="upper right")
            print("     " + " | ".join(lines))
    fig.suptitle("Two identical stressed pulses: the second pulse's error against the first (peak-time shift and peak error vs the transistor)",
                 fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG, dpi=170)
    print("  wrote", FIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
