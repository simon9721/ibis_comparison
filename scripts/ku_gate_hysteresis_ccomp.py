#!/usr/bin/env python3
"""Ku against the transistor's own gate voltage, and the C_comp that closes the loop.

Every base-buffer transistor run in the stress matrix recorded an internal
predriver node (io_buf n2, inv_chain vout7, ex2 n4). Plotting the two-fixture Ku
against that node over an event asks whether Ku is a static map of the gate --
the premise of the gate-state model.

The two-fixture solve subtracts C_comp*dV/dt before dividing by I_pu(V). A wrong
C_comp leaves displacement current booked as Ku, and dV/dt flips sign between
the rise and the fall, so the error opens a **loop** in Ku-vs-gate. Sweeping the
C_comp used in the solve and finding the value that minimises the loop measures
the device's capacitance with no C-V run. A real capacitance is width-independent;
the minimum has to be too, or the method is not measuring one.

Result 2026-09-08: ex2 minimises at 1.50-1.75 pF on all five widths against a
declared 5.0; inv_chain at 0.50-0.60 against 0.468; io_buf is too shallow to
decide (slow gate, small dV/dt) but agrees in direction with the direct C-V
extraction. See results/gate_physics_2026-09-08/FINDINGS.md.

    py -3.14 scripts/ku_gate_hysteresis_ccomp.py
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

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402

R = ROOT / "results"
MX = R / "stress_method_matrix_2026-08-20"
REF = MX / "pad_match" / "hspice_references"
FIX = MX / "delay_cmd" / "hspice_fixtures"
OUT = R / "gate_physics_2026-09-08"

BUFFERS = {
    "io_buf": (R / "io_buf_fast_edge_regen_2026-08-19/source/io_buf_fast_50ps.ibs", 3.3,
               "v(xdut.n2)", np.arange(0.2, 1.61, 0.1)),
    "inv_chain": (REF / "inv_chain/fast_5ps/r50_c2pf/short_high_w104ps_104ps/native/input.ibs", 1.8,
                  "v(xdut.vout7)", np.arange(0.1, 1.01, 0.1)),
    "ex2": (REF / "ex2/fast_5ps/r50_c2pf/short_high_w810ps_810ps/native/input.ibs", 3.3,
            "v(xdut.n4)", np.arange(1.0, 4.01, 0.25)),
}
COL = {"io_buf": "#111111", "inv_chain": "#2E8B57", "ex2": "#B03060"}


def ibis_names(ibis: Path) -> tuple[str, str]:
    t = ibis.read_text(errors="ignore")
    return (re.search(r"^\[Model\]\s+(\S+)", t, re.M).group(1),
            re.search(r"^\[Component\]\s+(.+?)\s*$", t, re.M).group(1))


def fixture(p: Path) -> np.ndarray:
    raw = sl.parse_hspice_tr0(p)
    t = np.asarray(raw["time"], float)
    v = np.asarray(raw[next(k for k in raw if "pad" in k)], float)
    return np.column_stack([t, v, v, v])


def event(ts, ku, t, vg, rev, tpk):
    """Ku and gate voltage over the event, split at the Ku peak."""
    g = np.arange(rev - 0.05, min(tpk + 2.5, 21.0), 0.002)
    kug, vgg = np.interp(g, ts, ku), np.interp(g, t, vg)
    ipk = int(np.argmax(kug))
    after = np.where(kug[ipk:] < 0.05)[0]
    iend = ipk + (after[0] if len(after) else len(kug) - ipk - 1)
    return kug[:iend + 1], vgg[:iend + 1], ipk


def hysteresis(kug, vgg, ipk) -> float:
    up_vg, up_ku, dn_vg, dn_ku = vgg[:ipk + 1], kug[:ipk + 1], vgg[ipk:], kug[ipk:]
    lo, hi = max(up_vg.min(), dn_vg.min()), min(up_vg.max(), dn_vg.max())
    if hi <= lo + 0.05:
        return float("nan")
    grid = np.linspace(lo, hi, 40)
    o1, o2 = np.argsort(up_vg), np.argsort(dn_vg)
    return float(np.mean(np.abs(np.interp(grid, up_vg[o1], up_ku[o1])
                                - np.interp(grid, dn_vg[o2], dn_ku[o2]))))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(17, 9.5))
    for col, (dev, (ibis, sup, node, ccs)) in enumerate(BUFFERS.items()):
        m, c = ibis_names(ibis)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=m, component_name=c)
        declared = float(data.c_comp[0]) * 1e12
        runs = sorted((REF / dev / "transistor" / "r50_c2pf").glob("short_high_w*ps_*"))
        print(f"=== {dev}  declared C_comp {declared:.3f} pF  gate {node}")
        print(f"    {'W ps':>6}{'argmin pF':>10}{'min loop':>9}{'loop@declared':>14}")
        mins = []
        for d in runs:
            W = int(re.search(r"_w(\d+)ps", d.name).group(1))
            fxd = FIX / dev / f"short_high_w{W}ps"
            if not (fxd / "vfix_0/run.tr0").exists():
                continue
            raw = sl.parse_hspice_tr0(d / "run.tr0")
            t, pad = sl.time_ns(raw), raw["v(pad_sp)"]
            rev, tpk = 5.0 + W / 1000, float(t[int(np.argmax(pad))])
            lo_f, hi_f = fixture(fxd / "vfix_0/run.tr0"), fixture(fxd / "vfix_vcc/run.tr0")
            loops = []
            for cc in ccs:
                data.c_comp = [cc * 1e-12] * 3
                s = solve_silicon_kukd(data, lo_f, hi_f, sup, uniform_ps=5.0)
                loops.append(hysteresis(*event(s[:, 0] * 1e9, s[:, 1], t, raw[node], rev, tpk)))
            loops = np.array(loops)
            i = int(np.nanargmin(loops))
            mins.append(ccs[i])
            data.c_comp = [declared * 1e-12] * 3
            s = solve_silicon_kukd(data, lo_f, hi_f, sup, uniform_ps=5.0)
            kug, vgg, ipk = event(s[:, 0] * 1e9, s[:, 1], t, raw[node], rev, tpk)
            ld = hysteresis(kug, vgg, ipk)
            print(f"    {W:>6}{ccs[i]:>10.2f}{loops[i]:>9.3f}{ld:>14.3f}")
            axes[0][col].plot(ccs, loops, marker="o", ms=4, lw=1.6, label=f"W {W} ps")
            if d == runs[len(runs) // 2]:
                # the Ku-vs-gate loop itself, at the declared value and at the minimum
                axes[1][col].plot(vgg, kug, color="#C05621", lw=2.0,
                                  label=f"declared {declared:.2f} pF (loop {ld:.2f})")
                data.c_comp = [ccs[i] * 1e-12] * 3
                s2 = solve_silicon_kukd(data, lo_f, hi_f, sup, uniform_ps=5.0)
                k2, v2, _ = event(s2[:, 0] * 1e9, s2[:, 1], t, raw[node], rev, tpk)
                axes[1][col].plot(v2, k2, color=COL[dev], lw=2.0, ls="--",
                                  label=f"{ccs[i]:.2f} pF (loop {loops[i]:.2f})")
                data.c_comp = [declared * 1e-12] * 3
        if mins:
            print(f"    -> argmin mean {np.mean(mins):.2f} pF, spread {min(mins):.2f}..{max(mins):.2f}")
        a = axes[0][col]
        a.axvline(declared, color="#8A8A8A", ls="--", lw=1.4, label="declared")
        a.set_title(f"{dev}: Ku-vs-gate loop against the C_comp used in the solve",
                    fontsize=11, fontweight="bold")
        a.set_xlabel("C_comp used (pF)")
        a.set_ylabel("loop (mean |Ku_up - Ku_down|)")
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
        b = axes[1][col]
        b.set_title(f"{dev}: Ku against {node}, middle width", fontsize=11, fontweight="bold")
        b.set_xlabel("gate voltage (V)")
        b.set_ylabel("Ku")
        b.grid(alpha=0.3)
        b.legend(fontsize=8)
    fig.suptitle("Is Ku a static map of the real gate? The C_comp that closes the loop",
                 fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "ku_gate_hysteresis_ccomp.png", dpi=170)
    plt.close(fig)
    print(f"\n  figure: {OUT / 'ku_gate_hysteresis_ccomp.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
