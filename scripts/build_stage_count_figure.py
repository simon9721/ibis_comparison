#!/usr/bin/env python3
"""Why the model carries every predriver stage, not just the last one.

K identical current-limited stages are fitted to ex2's measured full-swing gate node for
K = 1, 2, 3, then each is asked to predict the same node under a short pulse. The point is
that full swing does not choose K: two stages fit it nearly as well as three and then predict
the stressed gate completely wrongly. Reads existing probe runs; nothing is simulated.

    py -3.14 scripts/build_stage_count_figure.py
"""
from __future__ import annotations

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
import current_limited_stage_model as cl  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402

OUT = ROOT / "results" / "track2_train_check_2026-09-13" / "figs"
GATE, DEV, W_PS, STRESS = "v(xdut.n4)", "ex2", 858, 71
T_ON = 5.0 + 0.050 / 2
COLS = {1: "#B03060", 2: "#C08A21", 3: "#2B6CA3"}


def probe(sub):
    raw = psp.parse_tr0(psp.OUT / DEV / sub / "run.tr0")
    return np.asarray(raw["time"], float) * 1e9, psp.signals(raw, psp.STAGES[DEV])


def main() -> int:
    tf, vf = probe("full")
    g_full, _, _ = psp.normalise(tf, vf[GATE], tf, vf[GATE])
    ts, vs = probe(f"w{W_PS}")
    g_str, _, _ = psp.normalise(tf, vf[GATE], ts, vs[GATE])

    grid = np.arange(4.0, 21.0, cl.DT)
    u_full = ((grid >= T_ON) & (grid < T_ON + 10.0)).astype(float)
    u_str = ((grid >= T_ON) & (grid < T_ON + W_PS / 1e3)).astype(float)
    v_full = np.interp(grid, tf, g_full)
    meas_str = np.interp(grid, ts, g_str)

    fig, ax = plt.subplots(1, 2, figsize=(15, 4.7), sharey=True)
    ax[0].plot(grid - 5, v_full, color="#111111", lw=3.4, label="measured gate node n4")
    ax[1].plot(grid - 5, meas_str, color="#111111", lw=3.4,
               label=f"measured gate node n4: peak {meas_str.max():.2f}")
    for K in (1, 2, 3):
        rms, prms = cl.fit_chain_shared(u_full, v_full, K, p=1.0)
        pred_full = cl.simulate_chain(u_full, prms)
        pred_str = cl.simulate_chain(u_str, prms)
        print(f"  K={K}: full-swing rms {rms:.4f}   stressed peak {pred_str.max():.3f} "
              f"(measured {meas_str.max():.3f})")
        ax[0].plot(grid - 5, pred_full, color=COLS[K], lw=1.9, ls="--",
                   label=f"K = {K} stages: full-swing rms {rms:.4f}")
        ax[1].plot(grid - 5, pred_str, color=COLS[K], lw=1.9, ls="--",
                   label=f"K = {K} stages: peak {pred_str.max():.2f}")
    ax[0].set_xlim(-0.3, 4.0)
    ax[1].set_xlim(-0.3, 4.0)
    ax[0].set_ylim(-0.08, 1.16)
    ax[0].set_title("a. fitted to the full-swing gate: all three land on it",
                    fontweight="bold", fontsize=11)
    ax[1].set_title(f"b. the same three, asked for a {W_PS} ps pulse ({STRESS} % of full swing)",
                    fontweight="bold", fontsize=11)
    ax[0].set_ylabel("gate node n4, 0 = rest, 1 = fully on")
    for a in ax:
        a.grid(alpha=0.3)
        a.set_xlabel("time from the input rising edge (ns)")
        a.legend(fontsize=9, loc="upper right", framealpha=0.95)
    fig.suptitle("ex2: full swing cannot choose the stage count. The model needs one stage per real predriver stage",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "stage_count.png", dpi=160)
    plt.close(fig)
    print("wrote", OUT / "stage_count.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
