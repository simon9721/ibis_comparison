#!/usr/bin/env python3
"""Assemble the 2026-09-08/09 findings into one reviewable package.

One folder per claim under results/review_2026-09-09/, each with the figure,
the CSV it was computed from, the FINDINGS.md and the script that produced it.
Two figures that did not exist yet are built here: the three-open-drain Kd law,
and the ex2 C_comp correction (the negative result).

    py -3.14 scripts/build_review_package.py
"""
from __future__ import annotations

import csv
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

R = ROOT / "results"
S = ROOT / "scripts"
OUT = R / "review_2026-09-09"


def copy(src: Path, dst_dir: Path, name: str | None = None) -> str:
    dst_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return f"(missing: {src.relative_to(ROOT)})"
    dst = dst_dir / (name or src.name)
    shutil.copy2(src, dst)
    return dst.name


# --------------------------------------------------------------------------- #
# New figure 1: the Kd law on three open-drains
# --------------------------------------------------------------------------- #

def fig_od_law(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    sets = (("base OD", R / "opendrain_stress_2026-09-08/cases.csv", "#111111", "o"),
            ("od_weak (pull-down 1/2 width)", R / "opendrain_stress_od_weak_2026-09-08/cases.csv", "#B03060", "s"),
            ("od_slowpre (predriver 1/2 width)", R / "opendrain_stress_od_slowpre_2026-09-08/cases.csv", "#2E8B57", "^"))
    fig, ax = plt.subplots(1, 3, figsize=(18, 5.4))
    for name, p, col, mk in sets:
        rows = [r for r in csv.DictReader(open(p)) if float(r["width_ns"]) < 5]
        d = np.array([float(r["depth_pct"]) for r in rows])
        si = np.array([float(r["si_kd_at_min"]) for r in rows])
        ou = np.array([float(r["our_kd_at_min"]) for r in rows])
        na = np.array([float(r["nat_kd_at_min"]) for r in rows])
        n4 = np.array([float(r["n4_at_min"]) for r in rows])
        ok = d > 5
        c = np.polyfit(d[ok] / 100, si[ok], 1)
        r2 = 1 - np.sum((si[ok] - np.polyval(c, d[ok] / 100)) ** 2) / np.sum((si[ok] - si[ok].mean()) ** 2)
        ax[0].plot(d, si, marker=mk, color=col, lw=2.2, ms=7,
                   label=f"{name}: transistor  Kd = {c[0]:.2f}·depth {c[1]:+.2f}  (R² {r2:.3f})")
        ax[0].plot(d, ou, marker=mk, color=col, lw=2.0, ls="--", ms=5, alpha=0.9)
        ax[1].plot(d, n4, marker=mk, color=col, lw=2.2, ms=7, label=name)
        err_o = np.array([float(r["our_low_err_mV"]) for r in rows])
        err_n = np.array([float(r["nat_low_err_mV"]) for r in rows])
        ax[2].plot(d, err_o, marker=mk, color=col, lw=2.2, ms=7, label=f"{name}: ours")
        ax[2].plot(d, err_n, marker=mk, color=col, lw=1.2, ls=":", ms=4, alpha=0.8, label=f"{name}: native")
    ax[0].axhline(1.0, color="#8A8A8A", lw=1.0, ls="--")
    ax[0].text(50, 0.93, "dashed = ours: Kd = 1.0 at every depth", fontsize=10, color="#333", ha="center")
    ax[0].set_xlabel("depth  (% of settled low excursion the transistor reached)")
    ax[0].set_ylabel("Kd at the pad minimum")
    ax[0].set_title("Transistor's Kd is linear in depth; ours is not\n(three open-drains)", fontweight="bold")
    ax[0].grid(alpha=0.3)
    ax[0].legend(fontsize=8, loc="lower left")
    ax[1].set_xlabel("depth (%)")
    ax[1].set_ylabel("real predriver gate n4 at the pad minimum (V)")
    ax[1].set_title("The real gate at the minimum tracks depth\n(corr 0.99 on all three)", fontweight="bold")
    ax[1].grid(alpha=0.3)
    ax[1].legend(fontsize=8)
    ax[2].axhline(0, color="#111", lw=0.8)
    ax[2].set_xlabel("depth (%)")
    ax[2].set_ylabel("model low  minus  transistor low  (mV)")
    ax[2].set_title("Both models pull all the way down at every width\n(od_weak native: positive = malfunction)", fontweight="bold")
    ax[2].grid(alpha=0.3)
    ax[2].legend(fontsize=7)
    for a in ax:
        a.invert_xaxis()
    fig.suptitle("Open-drain ex2, three variants: the stress law the IBIS models lack", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(dst / "od_three_variants_law.png", dpi=170)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# New figure 2: the C_comp correction, negative result
# --------------------------------------------------------------------------- #

def fig_ccomp_negative(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    # From results/ex2_ccomp_correction_2026-09-08.log (declared 5.0 vs measured 1.7 pF)
    cases = ("858 ps (71% depth)", "975 ps (91% depth)")
    ours_pk = {5.0: (244, 20), 1.7: (289, 52)}
    nat_pk = {5.0: (263, 18), 1.7: (342, 75)}
    ours_lag = {5.0: (236, 121), 1.7: (268, 149)}
    nat_lag = {5.0: (263, 141), 1.7: (300, 172)}
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(2)
    w = 0.18
    for i, (lab, d5, d17, col) in enumerate((("ours", ours_pk, None, "#C05621"), ("native", nat_pk, None, "#2B6CA3"))):
        ax[0].bar(x + (i - 0.5) * 2 * w - w / 2, d5[5.0], w, color=col, alpha=0.45, label=f"{lab}, declared 5.0 pF")
        ax[0].bar(x + (i - 0.5) * 2 * w + w / 2, d5[1.7], w, color=col, label=f"{lab}, measured 1.7 pF")
    for i, (lab, d, col) in enumerate((("ours", ours_lag, "#C05621"), ("native", nat_lag, "#2B6CA3"))):
        ax[1].bar(x + (i - 0.5) * 2 * w - w / 2, d[5.0], w, color=col, alpha=0.45, label=f"{lab}, declared 5.0 pF")
        ax[1].bar(x + (i - 0.5) * 2 * w + w / 2, d[1.7], w, color=col, label=f"{lab}, measured 1.7 pF")
    for a, ylab, title in ((ax[0], "stressed pad peak error (mV)", "Peak error gets WORSE with the true C_comp"),
                           (ax[1], "lag vs transistor (ps)", "Lag gets WORSE with the true C_comp")):
        a.set_xticks(x)
        a.set_xticklabels(cases)
        a.set_ylabel(ylab)
        a.set_title(title, fontweight="bold")
        a.grid(alpha=0.3, axis="y")
        a.legend(fontsize=8)
    fig.suptitle("ex2: the measured 1.7 pF is right about the device and wrong for the model —\n"
                 "the declared 5 pF was compensating a third of the gate-timing error (control unchanged at both)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(dst / "ex2_ccomp_correction_negative.png", dpi=170)
    plt.close(fig)



# --------------------------------------------------------------------------- #
# New figure 3: the two prototypes, shipped vs best build, per family
# --------------------------------------------------------------------------- #

def fig_prototypes(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    G = R / "gate_cascade_prototype_2026-09-09"
    panels = (("ex2_base", "cascade5", "RC cascade, N = 5"),
              ("ex2_weak", "cascade5", "RC cascade, N = 5"),
              ("ex2_skewp", "cascade6", "RC cascade, N = 6"),
              ("inv_base8", "hybrid60ps", "delay + one 60 ps stage"))
    fig, ax = plt.subplots(1, len(panels) + 1, figsize=(4.4 * (len(panels) + 1), 4.6))
    for a, (v, best, lab) in zip(ax, panels):
        rows = {r["build"]: r for r in csv.DictReader(open(G / v / "sweep.csv"))}
        keys = [k for k in rows["shipped"] if k.startswith("pk_")]
        d = np.array([float(k[4:]) for k in keys])
        for name, col, style, lw in (("shipped", "#C05621", "-", 2.4), (best, "#2E8B57", "--", 2.6), ("native", "#2B6CA3", ":", 1.6)):
            if name not in rows:
                continue
            y = np.array([float(rows[name][k]) for k in keys])
            if name == "native" and np.nanmin(y) < -50:
                continue          # native dead on the tr1ps variant files
            a.plot(d, y, color=col, ls=style, lw=lw, marker="o", ms=5, label=name if name != best else f"ours, {lab}")
        a.axhline(0, color="#111", lw=0.8)
        a.set_title(v, fontweight="bold")
        a.set_xlabel("depth (%)")
        a.invert_xaxis()
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    ax[0].set_ylabel("stressed pad peak, ours minus transistor (%)")
    # io_buf: gate-side fix on the lag
    a = ax[-1]
    rows = {r["mode"] + ("" if r["mode"] in ("shipped", "native") else f"_k{float(r['k']):g}"): r
            for r in csv.DictReader(open(R / "gate_ramp_prototype_2026-09-09/io_buf/sweep.csv"))}
    keys = [k for k in rows["shipped"] if k.startswith("lag_")]
    d = np.array([float(k[5:]) for k in keys])
    for name, col, style, lab in (("shipped", "#C05621", "-", "shipped"), ("single_k4", "#2E8B57", "--", "ours, slow gate x4, single map"), ("native", "#2B6CA3", ":", "native")):
        y = np.array([float(rows[name][k]) for k in keys])
        a.plot(d, y, color=col, ls=style, lw=2.4, marker="o", ms=5, label=lab)
    a.axhline(0, color="#111", lw=0.8)
    a.set_title("io_buf (pedestal, ps)", fontweight="bold")
    a.set_xlabel("pulse width (ps)")
    a.set_ylabel("lag vs transistor (ps)")
    a.grid(alpha=0.3)
    a.legend(fontsize=8)
    fig.suptitle("Two prototypes, full swing preserved by construction: what each family needs",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(dst / "prototypes_summary.png", dpi=170)
    plt.close(fig)

# --------------------------------------------------------------------------- #
# Package
# --------------------------------------------------------------------------- #

def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    d1 = OUT / "01_two_regimes_twelve_buffers"
    copy(R / "cross_device_stress_2026-09-08/cross_device_stress.png", d1)
    copy(R / "cross_device_stress_2026-09-08/cases.csv", d1)
    copy(R / "cross_device_stress_2026-09-08/metrics.csv", d1)
    copy(R / "cross_device_stress_2026-09-08/FINDINGS.md", d1)
    copy(S / "cross_device_stress_metrics.py", d1)
    copy(S / "build_cross_device_stress_figures.py", d1)

    d2 = OUT / "02_gate_physics_and_ccomp_loop"
    copy(R / "gate_physics_2026-09-08/ku_gate_hysteresis_ccomp.png", d2)
    copy(R / "gate_physics_2026-09-08/FINDINGS.md", d2)
    copy(S / "ku_gate_hysteresis_ccomp.py", d2)

    d3 = OUT / "03_ccomp_correction_negative_result"
    fig_ccomp_negative(d3)
    copy(R / "ex2_ccomp_correction_2026-09-08/FINDINGS.md", d3)
    copy(R / "ex2_ccomp_correction_2026-09-08.log", d3, "run.log")
    copy(S / "ex2_ccomp_correction_test.py", d3)

    d4 = OUT / "04_pulse_train_no_accumulation"
    copy(R / "pulse_train_2026-09-08/pulse_train.png", d4)
    copy(R / "pulse_train_2026-09-08/per_pulse.csv", d4)
    copy(R / "pulse_train_2026-09-08/FINDINGS.md", d4)
    copy(S / "pulse_train_accumulation.py", d4)

    d5 = OUT / "05_open_drain_three_variants"
    fig_od_law(d5)
    copy(R / "opendrain_stress_2026-09-08/opendrain_stress.png", d5, "sweep_base_od.png")
    copy(R / "opendrain_stress_od_weak_2026-09-08/opendrain_stress.png", d5, "sweep_od_weak.png")
    copy(R / "opendrain_stress_od_slowpre_2026-09-08/opendrain_stress.png", d5, "sweep_od_slowpre.png")
    copy(R / "opendrain_stress_2026-09-08/cases.csv", d5, "cases_base_od.csv")
    copy(R / "opendrain_stress_od_weak_2026-09-08/cases.csv", d5, "cases_od_weak.csv")
    copy(R / "opendrain_stress_od_slowpre_2026-09-08/cases.csv", d5, "cases_od_slowpre.csv")
    copy(R / "opendrain_stress_2026-09-08/FINDINGS.md", d5)
    copy(S / "opendrain_stress_cases.py", d5)

    d6 = OUT / "06_io_buf_background_0907"
    copy(R / "pu_off_conflict_2026-09-07/pu_off_conflict.png", d6)
    copy(R / "silicon_kukd_conditioning_2026-09-07/silicon_kukd_conditioning.png", d6)
    copy(R / "full_swing_silicon_kukd_2026-09-07/full_swing_silicon_kukd.png", d6)
    copy(R / "native_st_vs_solved_2026-09-07/native_st_vs_solved.png", d6)
    copy(R / "meeting_deck_2026-09-04/figures/correction_bump.png", d6)
    copy(R / "meeting_deck_2026-09-04/figures/correction_shapes.png", d6)
    copy(R / "pu_off_scale_2026-09-07/FINDINGS.md", d6, "FINDINGS_pu_off_scale.md")
    copy(R / "silicon_kukd_conditioning_2026-09-07/FINDINGS.md", d6, "FINDINGS_conditioning.md")
    copy(R / "full_swing_silicon_kukd_2026-09-07/FINDINGS.md", d6, "FINDINGS_full_swing.md")
    copy(R / "bump_marker_2026-09-07/FINDINGS.md", d6, "FINDINGS_bump_marker.md")

    d7 = OUT / "07_gate_ramp_prototype"
    copy(R / "gate_ramp_prototype_2026-09-09/FINDINGS.md", d7)
    for v in ("inv_base8", "ex2_base", "io_buf"):
        copy(R / f"gate_ramp_prototype_2026-09-09/{v}/sweep.csv", d7, f"sweep_{v}.csv")
    copy(S / "gate_ramp_prototype.py", d7)

    d8 = OUT / "08_cascade_and_hybrid_command"
    fig_prototypes(d8)
    copy(R / "gate_cascade_prototype_2026-09-09/FINDINGS.md", d8)
    for v in sorted(p.name for p in (R / "gate_cascade_prototype_2026-09-09").iterdir() if p.is_dir()):
        copy(R / f"gate_cascade_prototype_2026-09-09/{v}/sweep.csv", d8, f"sweep_{v}.csv")
    copy(S / "gate_cascade_prototype.py", d8)

    d9 = OUT / "09_residual_depth_rule_and_fence"
    copy(R / "residual_depth_rule_2026-09-09/FINDINGS.md", d9)
    for v in ("io_buf", "inv_base8", "ex2_base"):
        copy(R / f"residual_depth_rule_2026-09-09/{v}/results.csv", d9, f"results_{v}.csv")
    copy(S / "residual_depth_rule.py", d9)

    d10 = OUT / "10_transistor_stages_and_gate_replay"
    copy(R / "predriver_stages_2026-09-09/FINDINGS.md", d10)
    copy(R / "predriver_stages_2026-09-09/stages.csv", d10)
    for v in ("ex2", "inv_chain", "io_buf"):
        copy(R / f"predriver_stages_2026-09-09/{v}/stages_vs_linear.png", d10, f"stages_vs_linear_{v}.png")
        copy(R / f"predriver_stages_2026-09-09/{v}/pulse_down_the_chain.png", d10, f"pulse_down_the_chain_{v}.png")
    copy(R / "gate_physics_2026-09-08/kd_gate_hysteresis.png", d10)
    G = R / "gate_cascade_prototype_2026-09-09"
    copy(G / "ex2/shared_gate_sweep.csv", d10, "shared_gate_sweep_ex2.csv")
    copy(G / "inv_chain/shared_gate_sweep.csv", d10, "shared_gate_sweep_inv_chain.csv")
    copy(G / "ex2_c1.7/gate_replay/gate_replay.png", d10, "gate_replay_ex2_c1.7.png")
    copy(G / "ex2/gate_replay/gate_replay.png", d10, "gate_replay_ex2_c5.png")
    copy(G / "inv_chain_c0.6/gate_replay/gate_replay.png", d10, "gate_replay_inv_chain_ibis_maps.png")
    copy(G / "io_buf/gate_replay/gate_replay.png", d10, "gate_replay_io_buf.png")
    copy(G / "ex2_c1.7/gate_replay_silicon_full/silicon_map_replay.png", d10, "silicon_map_replay_ex2.png")
    copy(G / "ex2_c1.7/gate_replay_silicon_full/maps.png", d10, "maps_ex2.png")
    copy(G / "inv_chain_c0.6/gate_replay_silicon_full/silicon_map_replay.png", d10, "silicon_map_replay_inv_chain.png")
    copy(G / "inv_chain_c0.6/gate_replay_silicon_full/maps.png", d10, "maps_inv_chain.png")
    copy(G / "io_buf/gate_replay_silicon_full/silicon_map_replay.png", d10, "silicon_map_replay_io_buf.png")
    copy(G / "io_buf/gate_replay_silicon_full/maps.png", d10, "maps_io_buf.png")
    for v, tag in (("ex2_c1.7", "gate_replay_silicon_full"), ("inv_chain_c0.6", "gate_replay_silicon_full"),
                   ("inv_chain_c0.6", "gate_replay_silicon_stress"), ("io_buf", "gate_replay_silicon_full")):
        copy(G / v / tag / "sweep.csv", d10, f"sweep_{v}_{tag}.csv")
    for sc in ("predriver_stage_probe.py", "kd_gate_hysteresis.py", "shared_gate_prototype.py",
               "gate_replay_prototype.py", "silicon_map_replay.py"):
        copy(S / sc, d10)

    d11 = OUT / "11_physics_prior_and_current_limited_stages"
    copy(R / "physics_map_gate_2026-09-10/FINDINGS.md", d11, "FINDINGS_physics_map_gate.md")
    copy(R / "physics_map_gate_2026-09-10/physics_map_gate.png", d11)
    copy(R / "physics_map_gate_2026-09-10/results.csv", d11, "results_physics_map_gate.csv")
    copy(R / "current_limited_stages_2026-09-10/FINDINGS.md", d11, "FINDINGS_current_limited_stages.md")
    for v in ("ex2", "inv_chain"):
        copy(R / f"current_limited_stages_2026-09-10/{v}_current_limited_stages_p1.png", d11)
        copy(R / f"current_limited_stages_2026-09-10/{v}_chain_K.png", d11)
        copy(R / f"current_limited_stages_2026-09-10/{v}_chain_K.csv", d11)
        copy(R / f"current_limited_stages_2026-09-10/{v}_chain_shared_K.png", d11)
        copy(R / f"current_limited_stages_2026-09-10/{v}_chain_shared_K.csv", d11)
    copy(R / "current_limited_stages_2026-09-10/results_p1.csv", d11, "results_current_limited_stages_p1.csv")
    copy(S / "physics_map_gate_from_ibis.py", d11)
    copy(S / "current_limited_stage_model.py", d11)

    d12 = OUT / "12_current_limited_chain_in_ngspice"
    copy(R / "gate_chain_prototype_2026-09-10/FINDINGS.md", d12)
    GC = R / "gate_chain_prototype_2026-09-10"
    for v in sorted(p.name for p in GC.iterdir() if p.is_dir()):
        for b in sorted(p.name for p in (GC / v).iterdir() if p.is_dir()):
            copy(GC / v / b / "chain.png", d12, f"chain_{v}_{b}.png")
            copy(GC / v / b / "sweep.csv", d12, f"sweep_{v}_{b}.csv")
    copy(R / "input_threshold_check_2026-09-10.txt", d12)
    copy(R / "gate_chain_prototype_2026-09-10/NEXT_STEPS_FINDINGS.md", d12)
    copy(R / "pulse_train_2026-09-08_chain/pulse_train.png", d12, "pulse_train_ex2_chain.png")
    copy(R / "pulse_train_2026-09-08_chain/per_pulse.csv", d12, "pulse_train_ex2_chain_per_pulse.csv")
    copy(R / "physics_map_gate_2026-09-10/results.csv", d12, "prior3_fits.csv")
    copy(S / "gate_chain_prototype.py", d12)
    copy(S / "input_threshold_check.py", d12)
    copy(S / "build_chain_model.py", d12)
    copy(S / "variant_gate_probe.py", d12)
    copy(S / "variant_silicon_map.py", d12)
    copy(R / "variant_gate_probe_2026-09-10/gate_max.json", d12)
    copy(R / "variant_gate_probe_2026-09-10/ccomp_loop.json", d12)
    copy(S / "variant_ccomp_loop.py", d12)
    copy(S / "gate_chain_train_calib.py", d12)
    copy(ROOT / "tools/pybis2spice/pybis2spice/chain_command.py", d12)
    for v in ("ex2_c1.7", "inv_chain_c0.6"):
        copy(R / f"gate_chain_train_calib_2026-09-10/{v}/sweep.csv", d12, f"train_calib_sweep_{v}.csv")
    copy(S / "gate_step_prototype.py", d12)
    for b in sorted(p.name for p in (R / "gate_step_prototype_2026-09-10/io_buf").iterdir() if p.is_dir()) if (R / "gate_step_prototype_2026-09-10/io_buf").exists() else []:
        copy(R / "gate_step_prototype_2026-09-10/io_buf" / b / "step.png", d12, f"step_io_buf_{b}.png")
        copy(R / "gate_step_prototype_2026-09-10/io_buf" / b / "sweep.csv", d12, f"sweep_step_io_buf_{b}.csv")
    copy(R / "pulse_train_2026-09-08_chain_fileonly/pulse_train.png", d12, "pulse_train_fileonly.png")
    copy(R / "pulse_train_2026-09-08_chain_fileonly/per_pulse.csv", d12, "pulse_train_fileonly_per_pulse.csv")
    for v in ("inv_stage4", "inv_base8"):
        copy(R / f"variant_gate_probe_2026-09-10/{v}/silicon_map.png", d12, f"silicon_map_{v}.png")

    (OUT / "README.md").write_text(README, encoding="utf-8")
    print(f"  {OUT}")
    for d in sorted(OUT.iterdir()):
        if d.is_dir():
            print(f"    {d.name}/  " + ", ".join(p.name for p in sorted(d.iterdir())))
    return 0


README = r"""# Review package — stress investigation, 2026-09-07 → 09-09

Each folder is one claim. Inside: the figure that shows it, the CSV it was
computed from, the write-up (`FINDINGS.md`) with every number, and the script
that produced it (re-runnable with `py -3.14 <script>`). Reference throughout is
the **HSPICE transistor**; native IBIS is the bar; "ours" is the shipped
`InputDrivenTwoStateGateDelayCommandFull` build unless stated.

Read the folders in order; each builds on the last.

---

## 01 — Two stress regimes, twelve buffers  `01_two_regimes_twelve_buffers/`

**Claim.** Under stress, eleven buffers (four inv_chain variants + base, five ex2
variants + base) fail the same way: our model enters the reversal with the
pull-up fully on where the transistor is only part-way, so the stressed peak comes
out **+34…+71 % too tall at 50 % depth**. io_buf alone is in a different regime
(peak within ±3 %), because its gate is slow (τ 1.13 ns) and its pad peaks at the
reversal.

**Evidence.** `cross_device_stress.png` — panel 1: peak excess vs depth, all
twelve; panel 2: entry excess vs peak excess, **r = 0.889 over 68 cases,
0.86–0.98 inside every buffer**; panel 5: io_buf isolated by gate τ and event
timing. Native (dotted) fails identically where alive.
Numbers: `metrics.csv` (one row per case × model), `cases.csv` (per case).

**Also in the write-up.** The transistor's Kd residual shrinks toward zero with
stress on 12/12 buffers while ours is constant (panel 4). Native is dead on all
ex2 variants and inv_stage4 below 90 % (tr1ps IBIS files) — flagged
`native_valid = 0`, excluded. Pedestal sign vs the transistor is positive on
every case; the old "opposite sign on inv/ex2" was measured against native.

---

## 02 — Ku is a static map of the real gate; the loop measures C_comp  `02_gate_physics_and_ccomp_loop/`

**Claim.** The matrix transistor runs recorded the predriver gate node (io_buf
`n2`, inv_chain `vout7`, ex2 `n4`). Plotting the two-fixture Ku against it: on
io_buf and inv_chain Ku is a **static function of the gate** (loop ≤ 0.1). On ex2
it is not (loop 0.5–0.75) — until C_comp is corrected: a wrong C_comp books
displacement current as Ku with a sign that flips between rise and fall, opening a
loop. Minimising the loop gives **ex2 = 1.5–1.75 pF on all five widths, declared
5.0**; inv_chain 0.5–0.6 (declared 0.47); io_buf too shallow to decide.

**Evidence.** `ku_gate_hysteresis_ccomp.png` — top row: loop vs C_comp used, per
width (ex2's declared value is at the far right, off the minimum); bottom row:
the Ku-vs-gate loop at the declared value and at the minimum.
Script: `ku_gate_hysteresis_ccomp.py`.

**What it settles.** The gate-map architecture is physically right; our error is
in the gate *dynamics*. Three different physical situations hide under "stress":
io_buf's predriver is truncated by the pulse; inv_chain's completes but late;
ex2's reaches ~70 % regardless (at those widths).

---

## 03 — Applying the measured C_comp makes the model worse  `03_ccomp_correction_negative_result/`

**Claim.** Editing ex2's `.ibs` to the measured 1.7 pF makes **every stressed
metric worse** for ours and native (858 ps: peak +244 → +289 mV, lag +236 → +268
ps), with the control unchanged. The declared 5 pF was compensating about a third
of the gate-timing error by slowing the simulated pad. **Order matters: fix the
gate turn-off first, then correct C_comp.**

**Evidence.** `ex2_ccomp_correction_negative.png` (bars, both models, both
widths), `run.log` (raw numbers), `FINDINGS.md`.

---

## 04 — Pulse trains: nothing accumulates  `04_pulse_train_no_accumulation/`

**Claim.** Eight pulses at 50 % duty: every stressed error moves to a **new
plateau within 3–4 pulses** and stays there; controls are flat to the picosecond.
Two things a single pulse hides: on ex2 the error **flips sign** (+250 mV too
tall on pulse 1, −107 mV too low from pulse 3 — the device itself nearly reaches
full swing once the pad stops returning to zero), and **io_buf native collapses**
on the stressed train (+750 mV, lag pinned −327 ps from pulse 4) while ours holds
at +90 ps.

**Evidence.** `pulse_train.png` (top: stressed, bottom: control, per pulse),
`per_pulse.csv`.

**Caveat.** inv_chain's ~270 ps output delay against 222 ps windows shifts its
per-pulse attribution by one; the plateau conclusion is unaffected.

---

## 05 — Open-drain, three variants  `05_open_drain_three_variants/`

**Claim.** The open-drain ex2 (base, pull-down at half width, predriver at half
width) shows the regime in its purest form: the transistor's low excursion runs
smoothly from ~5 % to ~95 % depth while **both IBIS models pull all the way down
at every width** (Kd = 1.0 at the pad minimum). The transistor's Kd at the
minimum is **linear in depth at R² ≥ 0.99 on all three**, and its real gate at
that instant tracks depth at corr ≥ 0.99.

**Evidence.** `od_three_variants_law.png` — left: Kd at the minimum vs depth,
transistor (solid, with fit) against ours (dashed, flat at 1); middle: the real
gate vs depth; right: model-minus-transistor low error. `sweep_*.png` — the raw
pad waveforms per width for each variant. `cases_*.csv`.

**Two converter facts.** Our build has **no gate-state path for `Open_drain`**
(`subcircuit.py` falls back to legacy Kd control): it rests in the wrong state
(pulled low with the input high — visible at t = 0 in every `sweep_*.png`) and is
~120 ps late on both edges at full swing. **Native malfunctions on od_weak**: Kd
goes to −0.82 and it drives the pad above VCC to 3.6 V (right panel, positive
errors). The single-fixture C_comp loop on the OD closes at 3.0 pF vs push-pull's
1.7 — both effective values, gap open, both far from the declared 5.0.

---

## 06 — io_buf background from 09-07  `06_io_buf_background_0907/`

The io_buf-only results this week's generalisation was testing. Kept here so the
claims above can be checked against where they started:

* `native_st_vs_solved.png` — native's stored trajectory *is* the offline
  two-fixture solve (residual 0.4 % of span). No mystery in the trajectory.
* `silicon_kukd_conditioning.png` — the transistor's coefficients within ~90 ps of
  a reversal are `C_comp·dV/dt` differentiation noise (they do not converge with
  the grid); **not** ill-conditioning (cond 1.4–2.7). Every window in this
  package starts past that zone.
* `full_swing_silicon_kukd.png` — the transistor's Ku overshoots early and
  briefly (+25–30 ps); both IBIS models make it late and broad. Native's Ku is
  1.52× the transistor at full swing.
* `pu_off_conflict.png` — `pu_off` sets both the gate turn-off and its phase
  against the residual spike; the two objectives are monotone in opposite
  directions (best 0.10 vs 0.86), so no single value works.
* `correction_bump.png`, `correction_shapes.png` — the +1.8 ns pull-down turn-on
  bump: transistor's moves 205 ps across the stress range, native 68, ours 6.
  io_buf-only (05 and 01 show the other buffers have no such event).

---

---

## 07 — Slow gate + re-derived map  `07_gate_ramp_prototype/`

**Claim.** Slowing the gate ramp by k and re-deriving the map from the shipped
full-swing gate-part Ku(t) (so full swing is preserved by construction) fixes
io_buf's pedestal (single map, k = 4: +63…+69 → +10 / +9 / +2 / −4 / −20 ps),
takes a quarter off inv_base8's peak excess (dual map, 65 → 49 %) and ~100 ps
off ex2's lag — but **cannot move ex2's peak**, because the peak is set before
the command T-line lets the reversal through. *Check:* `sweep_*.csv`.

## 08 — The command as an RC cascade / delay + one stage  `08_cascade_and_hybrid_command/`

**Claim.** Replacing the command T-lines with an N-stage RC cascade (50 % points
at pu_on / pu_off, maps re-derived) removes ex2's entry-level defect: **ex2_base
+71 % → −9…+8 % at N = 5**, ex2_weak the same, ex2_nomiller N = 5, ex2_skewp
N = 6; full swing kept to Ku rms ≤ 0.003. A pure cascade is catastrophic on
inv_chain (a 100 ps pulse cannot pass it; the real inverter chain regenerates),
where **delay line + one ~60 ps analog stage** halves the peak excess instead
(inv_base8 65 → 22 %). io_buf is neutral. Three families, three structures, each
predicted by the gate probe in 02. *Check:* `prototypes_summary.png`, `sweep_*.csv`.

## 09 — Residual scaled by depth, and fenced in time  `09_residual_depth_rule_and_fence/`

**Claim.** Scaling the falling residual by pad-peak ÷ plateau (the 12/12 law)
matches the old gate-based FRAC on io_buf (Kd rms 0.03 → 0.01–0.02) and, like
it, halves the +1.8 ns bump — until the scale is **fenced** to the truncated fall
(HNX < ~1 ns), which restores the bump to within 5 mV of the transistor with
nothing else lost. On inv/ex2 the rule does nothing: the residual is not their
defect. *Check:* `results_io_buf.csv` rows `fenced_*` vs `frac_depth`.

## 10 — Inside the transistor: stage by stage, and the real gate replayed into the model  `10_transistor_stages_and_gate_replay/`

**Claim A (what the transistor does).** Every internal node probed at full swing
and five stressed widths, each tested against the superposition of its own two
step responses (`stages_vs_linear_*.png`, `pulse_down_the_chain_*.png`):
**io_buf is linear from input to pad** — its stressed pads are its step
responses cut short, nothing else. **ex2** is three slow inverters (n4 reaches
50 % 1.1 ns after a 50 ps input edge); its stages are sub-linear in the *return*
(n4 0.76 vs 0.93 linear at 810 ps) — current-limited stages. **inv_chain's**
seven stages are near-linear (vout7 0.88 vs 1.00) and the pulse dies in the
output inverter (pad 0.49 vs 0.85). *Check:* `stages.csv` columns `meas_max`,
`p2_max`.

**Claim B (one gate, two maps).** ex2 and inv_chain drive P and N from one node;
the transistor's Kd is a static map of it (loop 0.04–0.06,
`kd_gate_hysteresis.png`). Tying the model's GDN to 1 − GUP changes the peak
< 1.5 % (`shared_gate_sweep_*.csv`) — right, not the lever.

**Claim C (the split).** Feed the model the transistor's real gate
(`gate_replay_*.png`). ex2 at C_comp 1.7 pF: **−3…−6 %, 18–24 ps** on all five
widths (shipped +4…+74 %). So ex2's stressed error is predriver + C_comp; the
static-map output stage is right. inv_chain with the IBIS-implied map:
**−14…−69 %** — the map is late in the gate (Ku 0.19 vs silicon 0.57 at
g = 0.7, `maps_inv_chain.png`); with the silicon Ku-vs-gate map, measured at
full swing, the same replay is **+2…+9 %, 9–13 ps** (`silicon_map_replay_inv_chain.png`)
and the full-swing pad improves too. On ex2 the two maps agree to ±0.03. io_buf (two
widths; the deeper three stall ngspice, see FINDINGS §7): peak unchanged, lag 63 → 38 ps. *Check:*
`sweep_*_gate_replay_silicon_full.csv`.

## 11 — Breaking the map/gate tie with physics, and the predriver's non-linearity  `11_physics_prior_and_current_limited_stages/`

**Claim A (map prior).** The three silicon Ku-vs-gate maps share one shape,
`((g − vt)/(1 − vt))^alpha`, vt ≈ 0.5, alpha 0.6–0.8 (`physics_map_gate.png`,
top row). Inverting it on the shipped model's full-swing Ku(t) recovers the real
gate: inv_chain to 10 ps (rms 0.028), ex2 at the 50 % point (middle row). The
tables are not late; the model's RC gate was the wrong partner. *Check:*
`results_physics_map_gate.csv`.

**Claim B (superposition is not enough).** Superposing the derived step
responses predicts io_buf's stressed gate within 0.035 (the shipped RC gate is
0.15–0.27 low), inv_chain within 0.01 at shallow and +0.11 at the deepest width,
ex2 not at all (0.99 vs 0.76) — bottom row.

**Claim C (current-limited stage).** One stage, four numbers fitted at full
swing only, driven by its measured stressed input, predicts ex2's output gate to
0.05 from the input pin (linear: 0.17 off) and each inv_chain stage to rms 0.003
(`*_current_limited_stages_p1.png`, red on black). The drive law under a partial
input (p) is invisible at full swing and must be assumed; p = 1.

**Claim D (how many stages, and from what).** K *identical* stages, four
shared numbers fitted at full swing: ex2 K = 3 predicts the stressed gate within
0.04 (`ex2_chain_shared_K.png`), inv_chain K = 7–9 brackets it. The full-swing
rms plateaus at the real stage count (3 and 7), so K is recoverable from the
tables alone; a free per-stage fit is degenerate and can swallow short pulses
(`*_chain_K.png`). *Check:*
`results_current_limited_stages_p1.csv`, `*_chain_K.csv`.

## 12 — The current-limited chain built in ngspice  `12_current_limited_chain_in_ngspice/`

**Claim A (ex2 solved by the recipe).** Three identical current-limited stages
(four numbers fitted at full swing) with the silicon maps: **−3…−10 %** on all
five stressed widths, lag 60–70 ps (shipped +4…+74 %, 150–300 ps); file-only
(IBIS gate through the prior, prior maps) −10…−28 %. *Check:*
`chain_ex2_c1.7_real_silicon.png`, `sweep_ex2_c1.7_*.csv`.

**Claim B (a converter defect on inv_chain).** The IBIS file declares Vinh 2.0 V
on a 1.8 V part; the digital input switches at 1.4 V and cuts every 50 ps-edge
pulse by 29 ps. With the comparator at mid-supply the shipped model's error
doubles (+31 → +66 % at 104 ps): two errors have been cancelling. *Check:*
`input_threshold_check_2026-09-10.txt`.

**Claim C (the cliff).** On inv_chain the chain reproduces the gate maximum to
0.03 but sits on a pulse-swallowing cliff between K = 7 (collapses at the two
deepest widths) and K = 9 (passes them, returns ~10 ps late, pad +17…+51 %); the
drive law under a partial input cannot be fitted at full swing. io_buf's gates
are placed correctly (0.63 vs 0.67 where the RC gate gave 0.40) but its
residual regime is not re-attached, pad −6…−29 %. *Check:* `chain_inv_chain_c0.6_*.png`,
`chain_io_buf_*.png`.

**Claim E (round 3, `NEXT_STEPS_FINDINGS.md` §6–8).** Calibrating on the probed
gate maximum is the wrong target for fast chains (the pad follows the gate
pulse's width too); calibrating on **the pad peak at one stressed width** — one
extra transistor run, no probe — puts **eleven of twelve buffers inside ±10 % at
every depth** with lags of tens of ps (shipped +35…+77 %, 150–300 ps; native dead
on six). io_buf is the exception (its gate is linear and needs the measured step
response, not a fitted stage). The recipe is one command,
`build_chain_model.py`, verified line-for-line against the prototype. *Check:*
`chain_*_calibpad*.png`, `sweep_*_calibpad*.csv`, `gate_max.json`.

**Claim F (round 4, `NEXT_STEPS_FINDINGS.md` §9–12).** io_buf's command as its
own measured step responses (two edge stopwatches, two pwl tables) draws the
ramp a fitted stage cannot (gate rms 0.029) but the truncated ramp runs 4 %
above its step response and the deep widths stay 13–25 % low; its pad
calibration hit the io_buf ngspice stall. C_comp by the loop method on all nine
variants: ex2 family 1.75–2.0 pF (declared 5.0), inv family 0.3–0.5 (declared
0.47); the pad calibration absorbs the inv differences. The builder now does the
pad calibration itself from a CSV. **The pulse train exposes the next degree of
freedom**: file-only chains calibrated on one pulse are right on pulse 1 and
9 % (ex2) / 23 % (inv_chain) low on the settled train, where the real-gate chain
was within 7 mV — a stressed train is the second characterisation point. *Check:*
`step_io_buf_*.png`, `ccomp_loop.json`, `pulse_train_fileonly.png`.

**Claim G (round 5, `NEXT_STEPS_FINDINGS.md` §13–14).** With a stressed train as
the second characterisation point, ex2's chain (x_lin 0.25) is within ±2 % on
every single-pulse width and within 3 % on the settled train — but 140 ps
late; the x_lin that gets timing right leaves the train 9 % low. One resistive
fraction cannot serve both, and a separate discharge fraction made it worse:
the four-number stage law is now the frontier. inv_chain's train shortfall
(−20 %) does not move with x_lin. The chain's text generation now lives in the
converter package (`chain_command.py`), builder output identical. *Check:*
`train_calib_sweep_*.csv`.

**Claim D (the next steps, `NEXT_STEPS_FINDINGS.md`).** The converter now
clamps input thresholds to the supply (inv_chain 1.4 → 0.9 V). A three-parameter
map prior (saturation before the rail) matches the silicon maps to 0.013–0.036
and, as the map with the real gate, gives ex2 −0.3…+2 %. **One stressed
characterisation point** (the gate maximum at the deepest width) removes the
inv_chain cliff: real gate +2…+19 % / ±9 ps, and **file-only −11…0 % /
−17…+1 ps**; on ex2 file-only −6…+7 %. The ex2 chain tracks a stressed 8-pulse
train to 7 mV / 10 ps after pulse 1 (native −114 mV / +136 ps). io_buf's shallow
widths are fixed by re-attaching the depth residual; its deep widths need the
NOR ramp itself. *Check:* `chain_*_calib*.png`, `pulse_train_ex2_chain.png`.

## What the whole set says about the model, in order

0. The output stage is a static Ku/Kd map of one gate node (10). Assume the
   MOSFET-shaped map (11A), fit K identical current-limited stages so that the
   map of the chain reproduces the tables' Ku(t) (11C, 12A) — done on ex2. Clamp
   the input thresholds to the supply first (12B). For fast chains, one stressed
   characterisation point to place the drive law (12C). Judge every gate
   prototype together with its map.
1. Make the command structure match the predriver: an RC cascade for ex2
   (N = 5–6), delay + one ~60 ps stage for inv_chain, a slow single-map gate for
   io_buf — each derived, each preserving full swing (07, 08). This is the
   entry-level defect from 01 and 05, fixed on ex2 and halved on inv.
2. Then correct C_comp (ex2 ≈ 1.7 pF) — not before (03).
3. Replace io_buf's FRAC with the universal law: residual ∝ depth (01, 05).
4. Add a 50 %-duty stressed train to validation (04).
5. Build an Open_drain gate-state path with a correct rest state (05).

## Retracted along the way (so you do not find them elsewhere and wonder)

* "ill-conditioned solve" as the reason the transistor's near-reversal Ku spikes
  — it is the differentiation grid (06).
* a secondary bump on ex2 — argmax on a monotone tail (05, 01).
* a Kd sign flip on eight buffers — a window artifact; only ex2_slowpre and
  inv_stage4 genuinely cross zero (01).
* `PU_OFF_SCALE = 0.70` as "derived", and my own 0.29 after it (06).
"""


if __name__ == "__main__":
    raise SystemExit(main())
