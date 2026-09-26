#!/usr/bin/env python3
"""Is Kd, like Ku, a static map of the SAME gate node?

ex2's output stage is one inverter: n4 drives the five pull-up PFETs and the
five pull-down NFETs. inv_chain's is the same (vout7 drives inv8's P and N).
So on those two, physics says Ku(t) = f_u(g(t)) and Kd(t) = f_d(g(t)) with one
and the same g. Our model gives the pull-down its own gate node (GDN) with its
own command timing. This checks the transistor side of that claim: the Kd-vs-
gate loop at the C_comp that closed the Ku loop (ex2 1.75 pF, inv_chain 0.6,
io_buf declared). io_buf has two separate predriver gates (n2 for the PFETs,
n3 for the NFETs), so there Kd is plotted against n3.

    py -3.14 scripts/kd_gate_hysteresis.py
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
import ku_gate_hysteresis_ccomp as kh  # noqa: E402

OUT = ROOT / "results/gate_physics_2026-09-08"
STAGES = ROOT / "results/predriver_stages_2026-09-09"
CC = {"io_buf": None, "inv_chain": 0.6, "ex2": 1.75}      # None = declared
KD_NODE = {"io_buf": "v(xdut.n3)", "inv_chain": "v(xdut.vout7)", "ex2": "v(xdut.n4)"}


def main() -> int:
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    for col, (dev, (ibis, sup, node, _)) in enumerate(kh.BUFFERS.items()):
        m, c = kh.ibis_names(ibis)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=m, component_name=c)
        cc = CC[dev] or float(data.c_comp[0]) * 1e12
        data.c_comp = [cc * 1e-12] * 3
        runs = sorted((kh.REF / dev / "transistor" / "r50_c2pf").glob("short_high_w*ps_*"))
        print(f"=== {dev}  C_comp used {cc:.2f} pF   Ku vs {node}, Kd vs {KD_NODE[dev]}")
        print(f"    {'W ps':>6}{'Ku loop':>9}{'Kd loop':>9}{'Ku max':>8}{'Kd min':>8}")
        for d in runs:
            W = int(re.search(r"_w(\d+)ps", d.name).group(1))
            fxd = kh.FIX / dev / f"short_high_w{W}ps"
            if not (fxd / "vfix_0/run.tr0").exists():
                continue
            raw = sl.parse_hspice_tr0(d / "run.tr0")
            t, pad = sl.time_ns(raw), raw["v(pad_sp)"]
            rev, tpk = 5.0 + W / 1000, float(t[int(np.argmax(pad))])
            s = solve_silicon_kukd(data, kh.fixture(fxd / "vfix_0/run.tr0"), kh.fixture(fxd / "vfix_vcc/run.tr0"),
                                   sup, uniform_ps=5.0)
            ts = s[:, 0] * 1e9
            kug, vgg, ipk = kh.event(ts, s[:, 1], t, raw[node], rev, tpk)
            lu = kh.hysteresis(kug, vgg, ipk)
            # Kd: the same event window, but Kd dips; use 1-Kd so the peak logic applies
            gate_kd = raw[KD_NODE[dev]] if KD_NODE[dev] in raw else None
            if gate_kd is None:
                # io_buf n3 was not recorded in the matrix runs: take it from the stage probe run
                sp = STAGES / dev / f"w{W}" / "run.tr0"
                if sp.exists():
                    r2 = sl.parse_hspice_tr0(sp)
                    gate_kd = np.interp(t, sl.time_ns(r2), np.asarray(r2[KD_NODE[dev]], float))
            if gate_kd is None:
                print(f"    {W:>6}{lu:>9.3f}{'n/a':>9}")
                continue
            kdg, vdg, ipk_d = kh.event(ts, 1.0 - s[:, 2], t, gate_kd, rev, tpk)
            ld = kh.hysteresis(kdg, vdg, ipk_d)
            print(f"    {W:>6}{lu:>9.3f}{ld:>9.3f}{kug.max():>8.3f}{1 - kdg.max():>8.3f}")
            if d == runs[len(runs) // 2]:
                axes[0][col].plot(vgg, kug, color="#B03060", lw=2.0, label=f"Ku, loop {lu:.2f}")
                axes[1][col].plot(vdg, 1.0 - kdg, color="#2B6CA3", lw=2.0, label=f"Kd, loop {ld:.2f}")
        axes[0][col].set_title(f"{dev}: Ku against {node}  (C_comp {cc:.2f} pF)", fontsize=11, fontweight="bold")
        axes[1][col].set_title(f"{dev}: Kd against {KD_NODE[dev]}", fontsize=11, fontweight="bold")
        for a in (axes[0][col], axes[1][col]):
            a.set_xlabel("gate voltage (V)")
            a.grid(alpha=0.3)
            a.legend(fontsize=9)
        axes[0][col].set_ylabel("Ku")
        axes[1][col].set_ylabel("Kd")
    fig.suptitle("Ku and Kd against the transistor's real gate, middle width: are both static maps of one node?",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "kd_gate_hysteresis.png", dpi=170)
    plt.close(fig)
    print(f"\n  figure: {OUT / 'kd_gate_hysteresis.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
