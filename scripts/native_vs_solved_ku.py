#!/usr/bin/env python3
"""Is native's St_pu(t) the same curve as our solved Ku(t)?

The manual settles what `ramp_rwf` means. With **one** waveform there is one
linear equation and two unknowns, so HSPICE *assumes* the off-going device
switches linearly over `rwf_tune` x delta_T (0.25 by default). With **two**
waveforms the system is determined and St_pu, St_pd are genuinely solved -- the
same two-equation solve `solve_k_params_output` does offline.

So both we and native-with-two-tables have a properly solved coefficient. Yet
under stress native's Ku sits +15 ps from the transistor's and ours +80.

This asks the question that separates the two remaining explanations:

* if native's St_pu(t) **equals** our solved Ku(t) on a clean full swing, then the
  stored trajectory is right and the difference is entirely in how each one is
  *entered and driven* under stress -- our gate-state reconstruction;
* if they **differ even at full swing**, the difference is in the solve itself and
  the stress case is a red herring.

One HSPICE run: native at full swing with St_pu exposed.

    py -3.14 scripts/native_vs_solved_ku.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402

R = ROOT / "results"
IBS = R / "defect_b_full_swing_2026-09-03" / "native" / "input.ibs"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
OUT = R / "native_vs_solved_ku_2026-09-04"
FIGS = R / "meeting_deck_2026-09-04" / "figures"

MODEL, COMPONENT = "driver", "MCM Driver 1"
SUPPLY = 3.3
RISE_NS, FALL_NS, STOP_NS = 5.0, 15.0, 22.0
NL = "\n"


def deck() -> str:
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + 0.05}n {SUPPLY}  "
           f"{FALL_NS}n {SUPPLY}  {FALL_NS + 0.05}n 0  {STOP_NS}n 0)")
    return (f"* io_buf native IBIS, full swing, St_pu exposed" + NL
            + ".title native full swing with state" + NL
            + ".option post=2 probe accurate ingold=2" + NL
            + ".temp 27" + NL
            + f"Vin in_dig 0 {pwl}" + NL
            + f"Ven en_sig 0 DC {SUPPLY}" + NL
            + f"VPU pu_ref 0 DC {SUPPLY}" + NL
            + "VPD pd_ref 0 DC 0" + NL
            + f"VPC pc_ref 0 DC {SUPPLY}" + NL
            + "VGC gc_ref 0 DC 0" + NL
            + "BIBIS pu_ref pd_ref pad in_dig en_sig dig_q pc_ref gc_ref" + NL
            + "+ file='input.ibs' model='driver' typ=typ power=off interpol=1" + NL
            + "+ ramp_rwf=2" + NL
            + "+ ramp_fwf=2" + NL
            + "+ xv_pu=ku" + NL
            + "+ xv_pd=kd" + NL
            + "Rdig dig_q 0 1k" + NL
            + "Rload pad 0 50.0" + NL
            + "Cload pad 0 2.0p" + NL
            + ".probe tran V(pad) V(ku) V(kd)" + NL
            + f".tran 0.002n {STOP_NS}n" + NL
            + ".end" + NL)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(IBS, OUT / "input.ibs")
    (OUT / "run.sp").write_text(deck(), encoding="utf-8")
    if not (OUT / "run.tr0").exists():
        if sl.hspice(OUT, timeout_s=900) is None:
            print("  native run failed")
            return 1
    raw = sl.parse_hspice_tr0(OUT / "run.tr0")
    t = sl.time_ns(raw)
    nat_ku = sl.signal(raw, "v(ku)")
    nat_kd = sl.signal(raw, "v(kd)")

    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    kr = pb.solve_k_params_output(data, corner=1, waveform_type="Rising")
    kf = pb.solve_k_params_output(data, corner=1, waveform_type="Falling")
    # The solve's time column is in seconds; everything else here is in ns.
    tr_ns, tf_ns = kr[:, 0] * 1e9, kf[:, 0] * 1e9

    print("  io_buf full swing. Native's St_pu/St_pd against our solved "
          "Ku(t)/Kd(t),")
    print("  the solved curve replayed from each input edge.\n")
    for label, edge, ks, ts in (("rising", RISE_NS, kr, tr_ns),
                                ("falling", FALL_NS, kf, tf_ns)):
        w = (t > edge - 0.1) & (t < edge + float(ts[-1]))
        since = t[w] - edge
        for name, col, nat in (("Ku", 1, nat_ku), ("Kd", 2, nat_kd)):
            ours = np.interp(since, ts, ks[:, col])
            theirs = nat[w]
            rms = float(np.sqrt(np.mean((ours - theirs) ** 2)))
            worst = float(np.abs(ours - theirs).max())
            print(f"    {label:<8} {name}:  rms {rms:.4f}   worst {worst:.4f}"
                  f"   (over {float(ts[-1]):.2f} ns)")

    fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.6))
    for a, edge, ks, ts, title in ((ax[0], RISE_NS, kr, tr_ns, "Rising"),
                                   (ax[1], FALL_NS, kf, tf_ns, "Falling")):
        w = (t > edge - 0.1) & (t < edge + float(ts[-1]))
        since = t[w] - edge
        a.plot(since, nat_ku[w], color="#2B6CA3", lw=2.6, label="native St_pu")
        a.plot(since, np.interp(since, ts, ks[:, 1]), color="#C05621", lw=2.0,
               ls="--", label="our solved Ku(t)")
        a.plot(since, nat_kd[w], color="#2E8B57", lw=2.6, label="native St_pd")
        a.plot(since, np.interp(since, ts, ks[:, 2]), color="#7B2CBF", lw=2.0,
               ls="--", label="our solved Kd(t)")
        a.set_title(title, loc="left", fontweight="bold")
        a.set_xlabel("Time since the input edge (ns)")
        a.grid(alpha=0.3)
    ax[0].set_ylabel("coefficient")
    ax[0].legend(fontsize=10)
    fig.suptitle("io_buf | full swing | is native's state the same curve we "
                 "solve offline?", fontsize=15, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "native_vs_solved_ku.png", dpi=200)
    plt.close(fig)
    print("\n  native_vs_solved_ku.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
