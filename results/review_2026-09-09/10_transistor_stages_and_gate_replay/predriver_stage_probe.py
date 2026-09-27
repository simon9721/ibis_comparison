#!/usr/bin/env python3
"""Where, inside the transistor buffer, does a short pulse stop being a pulse?

The matrix runs only recorded the last predriver node. This re-runs the same
transistor decks (same stimulus, same load, hspice.mod) with EVERY internal
stage probed, at full swing and at the five stressed widths, and asks two
questions of each stage:

1. **Stage by stage**: how far does each node get, and when, as the pulse walks
   down the chain? The stage that first fails to complete is where the stressed
   behaviour is born.

2. **Is the stage linear?** A linear time-invariant stage answers a pulse with
   the superposition of its own two full-swing step responses:

       P(t) = g_rise(t - t_on) + g_fall(t - t_off) - 1

   where g_rise / g_fall are the node's normalised responses to the full-swing
   rising and falling input edges (measured in the full-swing run). Comparing
   P(t) with the measured pulse response tests linearity with no model in the
   loop. Where it holds, the right command structure is *the measured step
   response itself*, and any linear filter (delay + RC, cascade) can only
   approximate that. Where it fails, the failure's sign says what nonlinearity
   is present (a slew-limited stage under-reaches; a regenerative one overshoots
   the linear prediction).

    py -3.14 scripts/predriver_stage_probe.py            # all three devices
    py -3.14 scripts/predriver_stage_probe.py --dev ex2
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
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
import spicelab as sl  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402

R = ROOT / "results"
REF = R / "stress_method_matrix_2026-08-20/pad_match/hspice_references"
OUT = R / "predriver_stages_2026-09-09"
RISE_NS = 5.0
FALL_FULL_NS = 15.0
XMAX_NS = {"ex2": 4.0, "inv_chain": 1.0, "io_buf": 5.5}     # plot window after the input edge

# stage nodes in signal order, input first, pad last
STAGES = {
    "ex2": ["v(in_dig)", "v(xdut.n2)", "v(xdut.n3)", "v(xdut.n4)", "v(pad_sp)"],
    "inv_chain": ["v(in_dig)"] + [f"v(xdut.vout{k})" for k in range(1, 8)] + ["v(pad_sp)"],
    # io_buf: two predriver paths. Pull-up: in -> n2 (NOR-like, PMOS gate).
    # Pull-down: in -> n1 -> nand_n3 -> n3 (NMOS gate).
    "io_buf": ["v(in_dig)", "v(xdut.n1)", "v(xdut.nand_n3)", "v(xdut.n3)", "v(xdut.n2)", "v(pad_sp)"],
}


def run_hspice(d: Path, deck: str, hspice: Path, timeout=1800) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "run.sp").write_text(deck, encoding="utf-8")
    tr0, lis = d / "run.tr0", d / "run.lis"
    ok = tr0.exists() and lis.exists() and "job concluded" in lis.read_text(errors="replace").lower()
    if not ok:
        rc = base.run_process([str(hspice), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", timeout)
        if rc != 0 or not tr0.exists():
            raise RuntimeError(f"hspice failed: {d}")
    return tr0


def make_deck(src: Path, nodes: list[str], full: bool) -> str:
    deck = src.read_text(encoding="utf-8", errors="replace")
    deck = re.sub(r"^\.probe tran .*$", ".probe tran " + " ".join(n.upper() for n in nodes), deck, flags=re.M)
    if full:
        # keep the 50 ps rising edge at 5 ns, move the falling edge to 15 ns
        deck = re.sub(r"(\+ 5\.05n (\S+)\n)\+ \S+n \S+\n\+ \S+n 0\n",
                      lambda m: f"{m.group(1)}+ 15n {m.group(2)}\n+ 15.05n 0\n", deck, count=1)
        assert "+ 15n " in deck, "full-swing PWL edit failed"
    return deck


def stage_runs(dev: str, hspice: Path):
    """{'full': (t, {node: v}), W: (t, {node: v})} -- runs and parses everything."""
    nodes = STAGES[dev]
    srcs = sorted((REF / dev / "transistor/r50_c2pf").glob("short_high_w*ps_*"))
    out = {}
    for k, src in enumerate([srcs[0]] + srcs):
        full = k == 0
        W = 0 if full else int(re.search(r"_w(\d+)ps", src.name).group(1))
        d = OUT / dev / ("full" if full else f"w{W}")
        d.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file() and not f.name.startswith("run."):
                shutil.copy2(f, d / f.name)
        raw = parse_tr0(run_hspice(d, make_deck(src / "run.sp", nodes, full), hspice))
        t = sl.time_ns(raw)
        out["full" if full else W] = (t, signals(raw, nodes))
    return out


def parse_tr0(path: Path) -> dict:
    """HSPICE POST=2 ASCII tr0 with the header line-wrap handled.

    spicelab's parser splits the name block on whitespace, so a name that wraps
    across the 80-column header (`v(xdut.v` / `out2`) becomes two signals and
    every column after it is misaligned. Fragments that do not start a new
    `v(` / `i(` name are glued back onto the previous one.
    """
    raw = path.read_text(errors="replace")
    ti, ei = raw.find("TIME"), raw.find("$&%#")
    toks = [x for x in raw[ti + 4:ei].split() if x]
    names = []
    for x in toks:
        if x.lower().startswith(("v(", "i(")):
            names.append(x)
        else:
            names[-1] = names[-1] + x
    names = ["time"] + [n.lower() + (")" if "(" in n and not n.endswith(")") else "") for n in names]
    flat = re.sub(r"\s+", "", raw[ei + 4:])
    w = 13
    vals = []
    for i in range(0, len(flat) - w + 1, w):
        try:
            vals.append(float(flat[i:i + w]))
        except ValueError:
            break
    v = np.asarray(vals, float)
    n = len(names)
    v = v[: (len(v) // n) * n].reshape(-1, n)
    return {k: v[:, j] for j, k in enumerate(names)}


def signals(raw, nodes: list[str]) -> dict:
    missing = [n for n in nodes if n not in raw]
    assert not missing, (missing, list(raw))
    return {n: np.asarray(raw[n], float) for n in nodes}


def normalise(t_full, v_full, t, v):
    # HSPICE writes its adaptive time points only (~130 per run): plateaus can
    # have no sample for nanoseconds, so read the settled levels by interpolation
    rest = float(np.interp(4.5, t_full, v_full))
    high = float(np.interp(14.5, t_full, v_full))
    return (v - rest) / (high - rest), rest, high


def step_responses(t_full, g_full):
    """g_rise(tau) from the 5 ns edge, g_fall(tau) from the 15 ns edge (tau in ns)."""
    tau = np.arange(-0.2, 9.0, 0.002)
    return tau, np.interp(tau + RISE_NS, t_full, g_full), np.interp(tau + FALL_FULL_NS, t_full, g_full)


def lti_predictions(grid, tau, gr, gf, W_ns):
    """grid is absolute time in ns. P1 uses the rise response twice; P2 rise + fall."""
    a = np.interp(grid - RISE_NS, tau, gr, left=0.0, right=gr[-1])
    b1 = np.interp(grid - RISE_NS - W_ns, tau, gr, left=0.0, right=gr[-1])
    b2 = np.interp(grid - RISE_NS - W_ns, tau, gf, left=1.0, right=gf[-1])
    return a - b1, a + b2 - 1.0


def t_cross(grid, y, level, t0):
    i = np.where((grid >= t0) & (y >= level))[0]
    return float(grid[i[0]] - t0) * 1e3 if len(i) else float("nan")


def analyse(dev: str, runs: dict, rows: list):
    nodes = STAGES[dev]
    t_full, v_full = runs["full"]
    widths = sorted(k for k in runs if k != "full")
    # --- full-swing step responses per stage -------------------------------
    print(f"\n=== {dev}: full-swing step responses per stage (normalised to each node's own swing)")
    print(f"    {'node':<16}{'t50 rise':>9}{'10-90 rise':>11}{'t50 fall':>9}{'10-90 fall':>11}   (ps from the input edge)")
    steps = {}
    for n in nodes:
        g, rest, high = normalise(t_full, v_full[n], t_full, v_full[n])
        tau, gr, gf = step_responses(t_full, g)
        steps[n] = (tau, gr, gf, rest, high)
        r50 = t_cross(tau, gr, 0.5, 0.0)
        r10, r90 = t_cross(tau, gr, 0.1, 0.0), t_cross(tau, gr, 0.9, 0.0)
        f50 = t_cross(tau, 1 - gf, 0.5, 0.0)
        f10, f90 = t_cross(tau, 1 - gf, 0.1, 0.0), t_cross(tau, 1 - gf, 0.9, 0.0)
        print(f"    {n:<16}{r50:>9.0f}{r90 - r10:>11.0f}{f50:>9.0f}{f90 - f10:>11.0f}")
        rows.append(dict(device=dev, node=n, width_ps=0, kind="step", rest_v=round(rest, 4), high_v=round(high, 4),
                         t50_rise_ps=round(r50), rise_10_90_ps=round(r90 - r10), t50_fall_ps=round(f50),
                         fall_10_90_ps=round(f90 - f10)))
    # --- stressed pulses: measured vs LTI superposition ----------------------
    print(f"\n    stressed pulses: measured node vs the linear prediction P2 = g_rise(t) + g_fall(t-W) - 1")
    print(f"    {'node':<16}{'W ps':>6}{'meas max':>9}{'P2 max':>8}{'P1 max':>8}{'t50 meas':>9}{'t50 P2':>8}{'rms(m-P2)':>10}{'sign':>6}")
    nrow, ncol = len(nodes) - 1, len(widths)
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.0 * ncol, 2.6 * nrow), sharex=True, squeeze=False)
    for j, W in enumerate(widths):
        t, v = runs[W]
        Wn = W / 1e3
        rev = RISE_NS + Wn
        grid = np.arange(RISE_NS - 0.2, rev + 3.0, 0.002)
        for i, n in enumerate(nodes[1:]):
            tau, gr, gf, rest, high = steps[n]
            g = (np.interp(grid, t, v[n]) - rest) / (high - rest)
            p1, p2 = lti_predictions(grid, tau, gr, gf, Wn)
            m = grid >= RISE_NS
            rms = float(np.sqrt(np.mean((g[m] - p2[m]) ** 2)))
            sign = "under" if g.max() < p2.max() - 0.02 else ("over" if g.max() > p2.max() + 0.02 else "=")
            print(f"    {n:<16}{W:>6}{g.max():>9.3f}{p2.max():>8.3f}{p1.max():>8.3f}"
                  f"{t_cross(grid, g, 0.5 * g.max(), RISE_NS):>9.0f}{t_cross(grid, p2, 0.5 * p2.max(), RISE_NS):>8.0f}{rms:>10.3f}{sign:>6}")
            rows.append(dict(device=dev, node=n, width_ps=W, kind="pulse", meas_max=round(float(g.max()), 4),
                             p2_max=round(float(p2.max()), 4), p1_max=round(float(p1.max()), 4),
                             t50_meas_ps=round(t_cross(grid, g, 0.5 * g.max(), RISE_NS)),
                             t50_p2_ps=round(t_cross(grid, p2, 0.5 * p2.max(), RISE_NS)), rms_p2=round(rms, 4)))
            a = axes[i][j]
            a.plot(grid - RISE_NS, g, color="#111111", lw=2.4, label="measured")
            a.plot(grid - RISE_NS, p2, color="#2E8B57", lw=1.8, ls="--", label="linear: rise + fall steps")
            a.plot(grid - RISE_NS, p1, color="#C05621", lw=1.2, ls=":", label="linear: rise step twice")
            a.axvline(Wn, color="#8A8A8A", ls="--", lw=1.0)
            a.set_ylim(-0.15, 1.2)
            a.set_xlim(-0.2, XMAX_NS[dev])
            a.grid(alpha=0.3)
            if i == 0:
                a.set_title(f"W = {W} ps", fontweight="bold")
            if j == 0:
                a.set_ylabel(n.replace("v(xdut.", "").replace("v(", "").rstrip(")") + "\n0 = rest, 1 = full swing", fontsize=9)
            if i == 0 and j == 0:
                a.legend(fontsize=7, loc="upper right")
            if i == nrow - 1:
                a.set_xlabel("time from the input rising edge (ns)")
    fig.suptitle(f"{dev}: every stage under a short pulse -- measured vs the linear (superposition) prediction",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(OUT / dev / "stages_vs_linear.png", dpi=150)
    plt.close(fig)
    # --- one figure: the pulse walking down the chain, all stages on one axis per width
    fig, axes = plt.subplots(1, ncol, figsize=(4.2 * ncol, 4.2), sharey=True)
    cmap = plt.get_cmap("viridis")
    for j, W in enumerate(widths):
        t, v = runs[W]
        rev = RISE_NS + W / 1e3
        grid = np.arange(RISE_NS - 0.2, rev + 3.0, 0.002)
        a = axes[j]
        for i, n in enumerate(nodes):
            tau, gr, gf, rest, high = steps[n]
            g = (np.interp(grid, t, v[n]) - rest) / (high - rest)
            a.plot(grid - RISE_NS, g, color=cmap(i / max(1, len(nodes) - 1)), lw=2.0 if i in (0, len(nodes) - 1) else 1.4,
                   label=n.replace("v(xdut.", "").replace("v(", "").rstrip(")"))
        a.axvline(W / 1e3, color="#8A8A8A", ls="--", lw=1.0)
        a.set_xlim(-0.2, XMAX_NS[dev])
        a.set_title(f"W = {W} ps", fontweight="bold")
        a.set_xlabel("time from the input rising edge (ns)")
        a.grid(alpha=0.3)
        if j == 0:
            a.set_ylabel("each node, 0 = rest, 1 = its full swing")
            a.legend(fontsize=7)
    fig.suptitle(f"{dev}: the pulse walking down the chain (input first, pad last)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / dev / "pulse_down_the_chain.png", dpi=150)
    plt.close(fig)
    print(f"    figures: {OUT / dev / 'stages_vs_linear.png'}, {OUT / dev / 'pulse_down_the_chain.png'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", nargs="*", default=list(STAGES))
    args = ap.parse_args()
    hspice = default_hspice()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for dev in args.dev:
        analyse(dev, stage_runs(dev, hspice), rows)
    with (OUT / "stages.csv").open("a", newline="", encoding="utf-8") as fh:
        keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("device", "node", "width_ps", "kind"), k))
        w = csv.DictWriter(fh, fieldnames=keys)
        if fh.tell() == 0:
            w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {OUT / 'stages.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
