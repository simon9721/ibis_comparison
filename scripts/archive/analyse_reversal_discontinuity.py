#!/usr/bin/env python3
"""Why some reversal policies will not simulate: the jump they demand.

At a reversal every replay method must choose where to re-enter the opposite
coefficient table. Whatever it chooses, the coefficient generally does not equal
what it was an instant earlier, and the difference is a step discontinuity the
solver has to pass through. A big enough step and the timestep collapses.

This computes that step for each policy without needing the simulation to
succeed, which matters because the ones that fail leave no waveform behind:

  time      re-enter at the same elapsed offset -- match nothing
  value     re-enter where the opposite table holds the present coefficient
  gate      re-enter at the time the opposite gate trajectory holds the present
            hidden state, taken separately for Ku and Kd

The coefficient at the reversal is read from a run that did converge, so the
starting point is real rather than assumed.
"""
from __future__ import annotations

import argparse
import csv
import glob
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools" / "pybis2spice"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit as sc  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from run_stress_method_matrix import case_tag, stress_cases  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
# The run whose coefficients define "where we were" at the reversal. Any
# converged model would do; this one solves all thirty cases.
SOURCE = "hybrid"


def tables(device):
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                        model_name=device.model, component_name=device.component)
    kr = pb.solve_k_params_output(data, corner=1, waveform_type="Rising")
    kf = pb.solve_k_params_output(data, corner=1, waveform_type="Falling")
    return kr, kf, sc.gate_state_fit(kr, kf)


def first_crossing(t_ns, values, target):
    """Earliest time the table passes through `target`, or nan."""
    idx = np.where(np.diff(np.sign(values - target)) != 0)[0]
    return float(t_ns[idx[0]]) if len(idx) else float("nan")


def analyse():
    rows = []
    for device in base.DEVICES:
        kr, kf, fit = tables(device)
        tr, tf = kr[:, 0] * 1e9, kf[:, 0] * 1e9
        for dev_id, direction, widths in stress_cases():
            if dev_id != device.device_id:
                continue
            for target, width_ps in widths:
                tag = case_tag(dev_id, direction, width_ps)
                hits = glob.glob(str(MATRIX / SOURCE / "ngspice_runs" / dev_id / "*" / "*" /
                                     "cases" / f"{tag.split(dev_id + '_')[1]}_*" /
                                     "ngspice_gate_state" / "run.raw"))
                path = MATRIX / SOURCE / "waveforms" / f"{tag}.csv"
                if not hits or not path.exists():
                    continue
                raw = parse_ngspice_raw(Path(hits[0]))
                key = {k.lower(): k for k in raw}
                t = np.asarray(raw[key["time"]]) * 1e9
                edge_ns = 5.0 if direction == "short_high" else 10.0
                t_rev = edge_ns + width_ps / 1000.0
                elapsed = t_rev - edge_ns

                ku_now = float(np.interp(t_rev, t, np.asarray(raw[key["v(xdrv.ku)"]])))
                kd_now = float(np.interp(t_rev, t, np.asarray(raw[key["v(xdrv.kd)"]])))
                gup = float(np.interp(t_rev, t, np.asarray(raw[key["v(xdrv.gup)"]])))
                gdn = float(np.interp(t_rev, t, np.asarray(raw[key["v(xdrv.gdn)"]])))

                # The opposite direction's tables: a short-high pulse reverses
                # into the falling edge, and vice versa.
                if direction == "short_high":
                    ot, oku, okd = tf, kf[:, 1], kf[:, 2]
                    vu, tu = sc.gate_inverse_time_table(fit["pu_off_delay"], fit["pu_off_tau"], 1.0, 0.0)
                    vd, td = sc.gate_inverse_time_table(fit["pd_on_delay"], fit["pd_on_tau"], 0.0, 1.0)
                else:
                    ot, oku, okd = tr, kr[:, 1], kr[:, 2]
                    vu, tu = sc.gate_inverse_time_table(fit["pu_on_delay"], fit["pu_on_tau"], 0.0, 1.0)
                    vd, td = sc.gate_inverse_time_table(fit["pd_off_delay"], fit["pd_off_tau"], 1.0, 0.0)

                entry = {
                    "time": (elapsed, elapsed),
                    "value": (first_crossing(ot, oku, ku_now), first_crossing(ot, okd, kd_now)),
                    "gate": (float(np.interp(gup, vu, tu)), float(np.interp(gdn, vd, td))),
                }
                row = {"device": dev_id, "direction": direction, "target_percent": target,
                       "ku_at_reversal": round(ku_now, 4), "kd_at_reversal": round(kd_now, 4)}
                for name, (t_u, t_d) in entry.items():
                    ku_new = float(np.interp(t_u, ot, oku)) if np.isfinite(t_u) else np.nan
                    kd_new = float(np.interp(t_d, ot, okd)) if np.isfinite(t_d) else np.nan
                    row[f"{name}_ku_jump"] = round(abs(ku_new - ku_now), 4)
                    row[f"{name}_kd_jump"] = round(abs(kd_new - kd_now), 4)
                    row[f"{name}_total_jump"] = round(
                        abs(ku_new - ku_now) + abs(kd_new - kd_now), 4)
                rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "reversal_discontinuity_2026-08-20")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    rows = analyse()
    if not rows:
        print("no cases available")
        return 1

    with (out / "jumps.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("Coefficient step demanded at the reversal, |dKu| + |dKd|")
    print(f"{'case':30s} {'time':>9s} {'value':>9s} {'gate':>9s}")
    for r in rows:
        name = f"{r['device']} {r['direction'].replace('short_', '')} {r['target_percent']}%"
        print(f"{name:30s} {r['time_total_jump']:9.3f} {r['value_total_jump']:9.3f} "
              f"{r['gate_total_jump']:9.3f}")
    print()
    for policy in ("time", "value", "gate"):
        v = [r[f"{policy}_total_jump"] for r in rows if np.isfinite(r[f"{policy}_total_jump"])]
        print(f"  {policy:6s} mean {np.mean(v):6.3f}   median {np.median(v):6.3f}   "
              f"worst {np.max(v):6.3f}")

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    order = ["time", "value", "gate"]
    colours = {"time": "#C02626", "value": "#D97706", "gate": "#7B2CBF"}
    ax = axes[0]
    for i, policy in enumerate(order):
        v = [r[f"{policy}_total_jump"] for r in rows if np.isfinite(r[f"{policy}_total_jump"])]
        ax.scatter(np.full(len(v), i) + np.linspace(-0.16, 0.16, len(v)), v,
                   color=colours[policy], s=34, alpha=0.85, edgecolor="white", linewidth=0.6)
        ax.plot([i - 0.28, i + 0.28], [np.median(v)] * 2, color="#151E28", lw=2.4, zorder=5)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(["time-matched", "value-matched", "Vc-matched"], fontsize=11)
    ax.set_ylabel("|ΔKu| + |ΔKd| demanded at the reversal", fontsize=11)
    ax.set_title("The step each policy asks the solver to take", fontsize=12.5, fontweight="bold")
    ax.grid(alpha=0.25, axis="y")
    ax.axhline(0, color="#8A8A8A", lw=1)

    ax = axes[1]
    for policy in order:
        v = np.sort([r[f"{policy}_total_jump"] for r in rows
                     if np.isfinite(r[f"{policy}_total_jump"])])
        ax.plot(v, np.linspace(0, 100, len(v)), color=colours[policy], lw=2.4,
                marker="o", ms=4, label=policy)
    ax.set_xlabel("|ΔKu| + |ΔKd|", fontsize=11)
    ax.set_ylabel("percent of cases at or below", fontsize=11)
    ax.set_title("Distribution across all thirty cases", fontsize=12.5, fontweight="bold")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "reversal_jump.png", dpi=150)
    plt.close(fig)
    print(f"\nwrote {(out / 'reversal_jump.png').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
