"""Validate the pybis spike trend in corrected ngspice against Xyce pybis.

This script reuses the Xyce pybis outputs from run_pybis_spike_trend_sweep.py
and runs the corrected ngspice pybis deck for all 64 fixed-channel bit-history
cases.  It does not rerun the Xyce sweep.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from run_edge_family_stress_crossflow import StressCase
from run_pybis_spike_trend_sweep import (
    NGSPICE,
    OUT_DIR,
    UI,
    PatternCase,
    ensure_ngspice_edge50_model,
    load_signal,
    make_ngspice_pybis_deck,
    run_ngspice,
)


def fixed_cases() -> list[PatternCase]:
    fixed_channel = StressCase(
        "sweep_30cm_loss5_coarse10",
        UI,
        3,
        5.0,
        "2 ns UI, 30 cm channel, R/G loss x5, 10 coarse sections",
        n_sections_override=10,
    )
    return [
        PatternCase(f"hist_h{pre}_g{gap}_p{post}_30cm_loss5", pre, gap, post, fixed_channel)
        for pre in [1, 2, 3, 4]
        for gap in [1, 2, 3, 4]
        for post in [1, 2, 3, 4]
    ]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def compare_window(
    t_a: np.ndarray,
    v_a: np.ndarray,
    t_b: np.ndarray,
    v_b: np.ndarray,
    x0: float,
    x1: float,
) -> dict[str, float]:
    grid = np.arange(x0, x1, 2e-12)
    a_i = np.interp(grid, t_a, v_a)
    b_i = np.interp(grid, t_b, v_b)
    d = a_i - b_i
    j = int(np.argmax(np.abs(d)))
    return {
        "rmse_v": float(np.sqrt(np.mean(d * d))),
        "maxabs_v": float(np.max(np.abs(d))),
        "maxabs_signed_v": float(d[j]),
        "maxabs_ns": float(grid[j] * 1e9),
        "a_max_v": float(np.max(a_i)),
        "b_max_v": float(np.max(b_i)),
        "a_min_v": float(np.min(a_i)),
        "b_min_v": float(np.min(b_i)),
    }


def run_case(case: PatternCase, model: Path) -> dict[str, object]:
    run_dir = OUT_DIR / "runs" / case.key / "ngspice_pybis_corrected"
    run_dir.mkdir(parents=True, exist_ok=True)
    deck = run_dir / f"{case.key}_ngspice_pybis_corrected.sp"
    raw = run_dir / f"{case.key}_ngspice_pybis_corrected.raw"
    deck.write_text(make_ngspice_pybis_deck(case, run_dir, model), encoding="ascii")
    raw.unlink(missing_ok=True)
    rc, timed_out, wall = run_ngspice(deck, raw)
    row: dict[str, object] = {
        "case": case.key,
        "pre_high": case.pre_high,
        "low_gap": case.low_gap,
        "post_high": case.post_high,
        "ngspice_rc": rc,
        "ngspice_timed_out": timed_out,
        "ngspice_wall_s": wall,
        "ngspice_output": raw.exists(),
    }
    xy_path = OUT_DIR / "runs" / case.key / "xyce_pybis" / f"{case.key}_xyce_pybis.cir.csv"
    row["xyce_pybis_output"] = xy_path.exists()
    if rc == 0 and raw.exists() and xy_path.exists():
        t_ng, v_ng = load_signal(raw, "ngspice", "v(n10b)")
        t_xy, v_xy = load_signal(xy_path, "xyce", "v(n10b)")
        rise = compare_window(t_ng, v_ng, t_xy, v_xy, case.target_rise_s, case.target_rise_s + 1.4e-9)
        fall = compare_window(t_ng, v_ng, t_xy, v_xy, case.target_fall_s, case.target_fall_s + 1.4e-9)
        row.update(
            {
                "rise_rmse_ng_minus_xy_v": rise["rmse_v"],
                "rise_maxabs_ng_minus_xy_v": rise["maxabs_v"],
                "rise_signed_at_maxabs_ng_minus_xy_v": rise["maxabs_signed_v"],
                "rise_maxabs_ns": rise["maxabs_ns"],
                "ng_rise_max_v": rise["a_max_v"],
                "xy_rise_max_v": rise["b_max_v"],
                "fall_rmse_ng_minus_xy_v": fall["rmse_v"],
                "fall_maxabs_ng_minus_xy_v": fall["maxabs_v"],
                "fall_signed_at_maxabs_ng_minus_xy_v": fall["maxabs_signed_v"],
                "fall_maxabs_ns": fall["maxabs_ns"],
                "ng_fall_min_v": fall["a_min_v"],
                "xy_fall_min_v": fall["b_min_v"],
            }
        )
    return row


def plot_agreement(rows: list[dict[str, object]]) -> None:
    plot_dir = OUT_DIR / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    post_values = sorted({int(r["post_high"]) for r in rows})
    fig, axes = plt.subplots(1, len(post_values), figsize=(5.0 * len(post_values), 4.4), sharey=True)
    if len(post_values) == 1:
        axes = [axes]
    vmax = max(float(r.get("rise_maxabs_ng_minus_xy_v", 0.0)) for r in rows)
    for ax, post in zip(axes, post_values):
        sub = [r for r in rows if int(r["post_high"]) == post]
        pre_vals = sorted({int(r["pre_high"]) for r in sub})
        gap_vals = sorted({int(r["low_gap"]) for r in sub})
        z = np.full((len(pre_vals), len(gap_vals)), np.nan)
        for r in sub:
            if "rise_maxabs_ng_minus_xy_v" not in r:
                continue
            i = pre_vals.index(int(r["pre_high"]))
            j = gap_vals.index(int(r["low_gap"]))
            z[i, j] = float(r["rise_maxabs_ng_minus_xy_v"])
        im = ax.imshow(z, origin="lower", aspect="auto", cmap="magma", vmin=0, vmax=vmax)
        ax.set_xticks(range(len(gap_vals)), [str(v) for v in gap_vals])
        ax.set_yticks(range(len(pre_vals)), [str(v) for v in pre_vals])
        ax.set_xlabel("Low gap before target rise (UI)")
        ax.set_title(f"Post-high run = {post} UI")
        for i in range(len(pre_vals)):
            for j in range(len(gap_vals)):
                ax.text(j, i, f"{z[i, j]:.2f}", ha="center", va="center", color="white", fontsize=8)
    axes[0].set_ylabel("Previous high run (UI)")
    fig.colorbar(im, ax=axes, label="Max |ngspice pybis - Xyce pybis| after rise (V)")
    fig.suptitle("Corrected ngspice pybis vs Xyce pybis agreement, fixed stressed channel")
    fig.savefig(plot_dir / "ngspice_xyce_pybis_fixed_channel_agreement_heatmap.png", dpi=180)
    plt.close(fig)


def main() -> int:
    if not NGSPICE.exists():
        raise FileNotFoundError(NGSPICE)
    model = ensure_ngspice_edge50_model()
    rows: list[dict[str, object]] = []
    cases = fixed_cases()
    for idx, case in enumerate(cases, 1):
        print(f"[{idx:02d}/{len(cases):02d}] {case.key}", flush=True)
        rows.append(run_case(case, model))
        write_csv(OUT_DIR / "ngspice_validation_fixed_channel_full_partial.csv", rows)
    write_csv(OUT_DIR / "ngspice_validation_fixed_channel_full.csv", rows)
    plot_agreement(rows)
    print(f"Wrote {OUT_DIR / 'ngspice_validation_fixed_channel_full.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
