#!/usr/bin/env python3
"""The transistor's internal stages probed, one figure per buffer, same size and layout for
the full-swing and the stressed case so the two can be read against each other.

    --full        a long-enough input pulse (ex2 3 ns, inv_chain 1 ns, io_buf 10 ns): every
                  stage completes its leg on both edges
    (default)     the short pulse whose pad reaches --target of full swing (0.70)

Reads the probe runs of `predriver_stage_probe.py` (and `build_full_swing_probes.py` for the
shorter full-swing pulses); nothing is re-simulated. Every node is normalised to its own full
swing, 0 = rest, 1 = fully on, and `pad_sp` / `in_dig` are labelled `pad` / `input`.

    py -3.14 scripts/build_stage_walk_figures.py [--full] [--target 0.70]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import spicelab as sl  # noqa: E402
from predriver_stage_probe import STAGES, OUT, XMAX_NS, RISE_NS, parse_tr0, signals, normalise  # noqa: E402

FIGS = ROOT / "results" / "meeting_deck_2026-09-11" / "figures"
PRETTY = {"pad_sp": "pad", "in_dig": "input"}
FULL_W_PS = {"ex2": 3000, "inv_chain": 1000, "io_buf": None}   # None: the 10 ns `full` run
FIGSIZE = (14, 4.6)


def label(node: str) -> str:
    n = node.replace("v(xdut.", "").replace("v(", "").rstrip(")")
    return PRETTY.get(n, n)


def load(dev: str, sub: str):
    raw = parse_tr0(OUT / dev / sub / "run.tr0")
    return sl.time_ns(raw), signals(raw, STAGES[dev])


def pick_width(dev: str, target: float, t_full, v_full):
    """The probed width whose pad excursion is closest to `target` of its full swing."""
    pad = STAGES[dev][-1]
    best = None
    for d in sorted((OUT / dev).glob("w*")):
        if not d.name[1:].isdigit():
            continue
        W = int(d.name[1:])
        t, v = load(dev, d.name)
        g, _, _ = normalise(t_full, v_full[pad], t, v[pad])
        depth = float(g[(t > RISE_NS) & (t < RISE_NS + 8)].max())
        if best is None or abs(depth - target) < abs(best[1] - target):
            best = (W, depth)
    return best


def draw(dev, nodes, t_full, v_full, t, v, width_ns, xmax, title, out):
    grid = np.arange(RISE_NS - 0.2, RISE_NS + xmax + 0.2, 0.002)
    cmap = plt.get_cmap("viridis")
    fig, a = plt.subplots(figsize=FIGSIZE)
    for i, n in enumerate(nodes):
        g, _, _ = normalise(t_full, v_full[n], t, v[n])
        a.plot(grid - RISE_NS, np.interp(grid, t, g), color=cmap(i / max(1, len(nodes) - 1)),
               lw=2.4 if i in (0, len(nodes) - 1) else 1.6, label=label(n))
    a.axvline(width_ns, color="#8A8A8A", ls="--", lw=1.0)
    a.set_xlim(-0.2, xmax)
    a.set_ylim(-0.2, 1.15)
    a.set_xlabel("time from the input rising edge (ns)")
    a.set_ylabel("each node, 0 = rest, 1 = its full swing")
    a.grid(alpha=0.3)
    a.legend(fontsize=9, loc="center right")
    a.set_title(title, fontweight="bold", fontsize=13)
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print("  wrote", out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=float, default=0.70)
    ap.add_argument("--dev", nargs="*", default=list(STAGES))
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    FIGS.mkdir(parents=True, exist_ok=True)
    for dev in args.dev:
        nodes = STAGES[dev]
        t_full, v_full = load(dev, "full")        # the 0/1 levels always come from this run
        if args.full:
            wps = FULL_W_PS[dev]
            sub = "full" if wps is None else f"full_w{wps}ps"
            w = 10.0 if wps is None else wps / 1e3
            t, v = load(dev, sub)
            draw(dev, nodes, t_full, v_full, t, v, w, w + XMAX_NS[dev],
                 f"{dev}, full swing: a {w:g} ns input pulse (dashed line: the input goes back down)",
                 FIGS / f"stage_walk_{dev}_full.png")
        else:
            W, depth = pick_width(dev, args.target, t_full, v_full)
            t, v = load(dev, f"w{W}")
            draw(dev, nodes, t_full, v_full, t, v, W / 1e3, XMAX_NS[dev],
                 f"{dev}, short pulse: {W} ps in, and the pad only reaches {round(depth * 100)} % (dashed line: the input goes back down)",
                 FIGS / f"stage_walk_{dev}_{round(args.target * 100)}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
