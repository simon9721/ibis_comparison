#!/usr/bin/env python3
"""Two figures for the machinery walkthrough, drawn from probed netlist nodes.

21  event vs continuous   the integrator's state moves smoothly and latches
                          nothing; the replay's sample and entry are staircases,
                          and every step is an event that had to be detected.

22  why the residual       the map alone does not reproduce the recorded Ku, and
                          the residual is exactly that shortfall. Vc-matching
                          reads the recorded table directly, so it has no map to
                          correct.

Both read the raw ngspice output rather than the resampled CSVs, because the
staircases in figure 21 are step changes a union grid would smear.

    py -3.14 scripts/build_machinery_explainer_figures.py
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / ".codex_deps" / "presentation" / "python", ROOT / "scripts",
          ROOT / "tools" / "pybis2spice", ROOT):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"
OUT = ROOT / "results" / "ibis_intro_figures_2026-08-25" / "figures_methods"

CASE = "w2226ps"
EDGE_NS, WIDTH_NS = 5.0, 2.2259
WINDOW = (4.7, 9.0)

SHARED = "#4A6FA5"
GATE = "#1B6B4F"
REPLAY = "#B4600A"
FAINT = "#8492A0"
DPI = 180


def raw(method):
    hits = glob.glob(str(MATRIX / method / "ngspice_runs" / "**" / f"*{CASE}*" /
                         "**" / "run.raw"), recursive=True)
    if not hits:
        raise SystemExit(f"no raw for {method} {CASE}")
    r = parse_ngspice_raw(Path(hits[0]))
    k = {x.lower(): x for x in r}
    t = np.asarray(r[k["time"]]) * 1e9
    return t, {n: np.asarray(r[k[f"v(xdrv.{n})"]]) for n in
               (x[7:-1] for x in k if x.startswith("v(xdrv."))}


def style(axis, ylabel, title=None):
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=11.5)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")
    axis.set_ylabel(ylabel, fontsize=12.5)
    if title:
        axis.set_title(title, fontsize=17, fontweight="bold", pad=11)


def event_figure(path, t_rev):
    tg, g = raw("gate_state")
    tv, v = raw("gate_match_equiv_delaycmd")
    fig, axes = plt.subplots(2, 1, figsize=(14.2, 8.6), sharex=True)

    axes[0].plot(tg, g["guptarget"], color=SHARED, lw=2.4, label="GUPTARGET  the command")
    axes[0].plot(tg, g["gup"], color=GATE, lw=3.2, label="GUP  the state")
    style(axes[0], "gate state",
          "Gate-state: the state follows the command, and latches nothing")
    axes[0].legend(fontsize=12, loc="upper left", framealpha=0.94)

    axes[1].plot(tv, v["gup"], color=FAINT, lw=2.0, label="GUP  (still running underneath)")
    axes[1].plot(tv, v["gusamp"], color=REPLAY, lw=3.0,
                 label="GUSAMP  the sampled gate  — one step per event")
    axes[1].plot(tv, np.clip(v["gmtu"], 0, 1.3), color="#7B2CBF", lw=2.4, ls=(0, (5, 2.2)),
                 label="GMTU  the entry time (ns)  — one step per event")
    style(axes[1], "gate state  /  entry time",
          "Vc-matching: every step is an event that had to be detected")
    axes[1].legend(fontsize=12, loc="upper left", framealpha=0.94)
    axes[1].set_xlabel("Time (ns)", fontsize=12.5)

    for axis in axes:
        axis.axvline(EDGE_NS, color="#8A8A8A", ls=":", lw=1.6)
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8)
        axis.set_xlim(*WINDOW)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)

    steps = int(np.sum(np.abs(np.diff(v["gusamp"])) > 0.02))
    return steps


def residual_figure(path, _t_rev):
    """The residual straight from the fit, not from a simulation.

    Drawn from the recorded tables and the fitted map rather than probed nodes:
    the residual is defined at fit time as recorded minus mapped, and in a live
    run it is buried under solver chatter that has nothing to do with the idea.
    """
    from pybis2spice import pybis2spice as pb, subcircuit as sc
    import run_three_buffer_realistic_pulse_campaign as base

    dev = next(d for d in base.DEVICES if d.device_id == "io_buf")
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(dev.fast_ibis)),
                        model_name=dev.model, component_name=dev.component)
    kr = pb.solve_k_params_output(data, corner=1, waveform_type="Rising")
    kf = pb.solve_k_params_output(data, corner=1, waveform_type="Falling")
    fit = sc.two_state_directional_gate_fit(kr, kf)

    panels = [
        ("rising edge — the pullup turning on", kr, 1, "pu_on", "ku_on_map"),
        ("falling edge — the pullup turning off", kf, 1, "pu_off", "ku_off_map"),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(14.2, 8.6))
    worst = 0.0
    for axis, (title, table, col, key, mapkey) in zip(axes, panels):
        t = table[:, 0] * 1e9
        recorded = table[:, col]
        lo, hi = (0.0, 1.0) if key.endswith("on") else (1.0, 0.0)
        gate = sc.gate_response(t, fit[key + "_delay"], fit[key + "_tau"], lo, hi)
        mapped = np.interp(gate, fit[mapkey + "_x"], fit[mapkey + "_y"])
        residual = recorded - mapped
        worst = max(worst, float(np.max(np.abs(residual))))

        axis.fill_between(t, mapped, recorded, color=REPLAY, alpha=0.22,
                          label="residual — the gap the map leaves")
        axis.plot(t, recorded, color=GATE, lw=3.0, label="recorded Ku")
        axis.plot(t, mapped, color=SHARED, lw=2.2, ls=(0, (5, 2.2)),
                  label="what the map predicts   pwl(gate)")
        style(axis, "Ku", title)
        axis.legend(fontsize=11.5, loc="best", framealpha=0.94)
        axis.set_xlim(0, 3.0)
    axes[1].set_xlabel("Time since the edge (ns)", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return worst


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    t_rev = EDGE_NS + WIDTH_NS

    steps = event_figure(out / "21_event_vs_continuous.png", t_rev)
    worst = residual_figure(out / "22_why_the_residual.png", t_rev)
    print(f"21  GUSAMP takes {steps} step changes in the window; GUP takes none")
    print(f"22  residual reaches {worst:.3f} in Ku — the map alone is short by that much")
    print(f"\nwrote to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
