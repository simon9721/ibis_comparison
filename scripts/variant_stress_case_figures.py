#!/usr/bin/env python3
"""Per-case Ku/Kd and pad figures for the nine buffer variants, with a 50% floor.

`variant_stress_depth_sweep.py` produced a summary CSV and nothing else: no
figures, and no Ku/Kd at all -- it probes only the pad. The 496 per-case figures
in this study cover the three *base* buffers, so the variants have never been
plotted. This fills that gap.

Two changes from that sweep:

**A 50% depth floor.** Four of its 36 cases landed below half the transistor's
full excursion (ex2_base 11%, ex2_nomiller 11%, ex2_slowpre 19%, ex2_skewp 46%).
Those are precisely the rows that had to be excluded from the timing summary as
uninterpretable -- where the models make a transition several times larger than
the transistor, no crossing-based metric separates timing from amplitude. Depth
targets are 90/80/70/60/50% of each variant's own full-swing excursion -- the
same five levels the base-buffer stress matrix uses -- so every case is both
measurable and directly comparable to the existing figures.

**Ku/Kd is recorded and plotted.** Two builds can land the same pad voltage
through a different Ku/Kd split, and only the coefficients show it:

  * silicon -- the transistor driven into two fixtures, then the same
    two-equation solve pybis uses (`extract_silicon_kukd.solve_silicon_kukd`).
    Ground truth, not native IBIS's opinion.
  * native  -- HSPICE exposes its own state variables through `xv_pu` / `xv_pd`,
    which the manual documents as St_pu / St_pd varying 0 to 1.
  * pybis   -- the generated subcircuits carry internal `Ku` / `Kd` nodes.

Figures follow `plot_stress_matrix_methods.py`'s colours and conventions, except
that Ku/Kd and pad go to **separate files** per case rather than three stacked
panels in one figure.

    py -3.14 scripts/variant_stress_case_figures.py
    py -3.14 scripts/variant_stress_case_figures.py --variant ex2_base
"""
from __future__ import annotations

import argparse
import csv
import re
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
from pybis2spice import subcircuit  # noqa: E402

import variant_stress_depth_sweep as vs  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402

OUT = ROOT / "results" / "variant_stress_cases_2026-09-04"
PRIOR = ROOT / "results" / "variant_stress_depth_2026-09-03" / "variant_stress_depth.csv"

# The study's own stress convention, from
# results/three_buffer_loaded_swing_stress_sweep_2026-08-14/selection.csv:
# five stressed levels, no full-swing case. Matching it is what makes these
# variant figures readable beside the 496 base-buffer ones.
DEPTH_TARGETS = (90, 80, 70, 60, 50)
R_FIXTURE = 50.0

# Same palette as plot_stress_matrix_methods.py, so the variant figures can be
# read side by side with the 496 base-buffer ones.
SILICON = "#111111"
NATIVE = "#2B6CA3"
NATIVE1 = "#7FB3D5"
METHOD_COLORS = {"gate_state": "#C02626", "delay_cmd": "#1B7F5A"}

BUILDS = (("gate_state", "InputDrivenTwoStateGateDirectionalDualResidualFull"),
          ("delay_cmd", "InputDrivenTwoStateGateDelayCommandFull"))


# --------------------------------------------------------------------------- #
# Choosing widths that meet the depth floor
# --------------------------------------------------------------------------- #

def prior_depths() -> dict[str, list[tuple[float, float]]]:
    """(width_ps, excursion_V) already simulated, per variant, from the sweep."""
    out: dict[str, list[tuple[float, float]]] = {}
    if not PRIOR.exists():
        return out
    for r in csv.DictReader(PRIOR.open()):
        out.setdefault(r["variant"], []).append(
            (float(r["width_ps"]), float(r["tx_excursion_v"])))
    for v in out:
        out[v].sort()
    return out


FLOOR_PCT = 50.0


def widths_for_targets(key: str, fam: str, inputs: Path, sup: float,
                       known: list[tuple[float, float]], d: Path) -> list[tuple[int, float]]:
    """Widths (ps) for each depth target, never landing below the 50% floor.

    Interpolating the known (width, excursion) pairs cannot reach below the
    narrowest width already simulated. On three variants that width is *already*
    above 70% of full swing -- inv_stage4 80%, inv_skewp 72%, ex2_weak 82% -- so
    the 50% and 70% targets both clamp onto it, collapsing into a duplicate case
    and leaving the shallow end uncovered.

    Collapses are resolved by probing narrower, bounded to at most two extra
    transistor runs per collapsed target: try 85% of the narrowest known width,
    and if that undershoots the floor, split the difference back upward. The floor
    is the requirement here, not hitting 50/70/85 exactly, so a short guarded
    search buys real shallow coverage without a full bisection.
    """
    pts = sorted(known)
    if not pts:
        raise SystemExit(f"{key}: no prior widths to interpolate from")
    full = max(e for _, e in pts)

    def depth_at(w: float) -> float | None:
        """Excursion at width `w` ps, simulating only if not already known."""
        w = round(w, 1)
        hit = next((e for ww, e in pts if abs(ww - w) < 1.0), None)
        if hit is not None:
            return hit
        tr = vs.transistor(d / f"probe_w{int(round(w))}ps", fam, inputs, sup, w / 1000.0)
        if tr is None:
            return None
        tt, si = tr
        base = float(np.median(si[tt < vs.RISE_NS - 0.5]))
        hit = float(si.max() - base)
        pts.append((w, hit))
        pts.sort()
        return hit

    def interp(want: float) -> float:
        return float(np.interp(want, [e for _, e in pts], [w for w, _ in pts]))

    chosen: list[tuple[int, float]] = []
    for target in DEPTH_TARGETS:
        if target == 100:
            chosen.append((target, max(w for w, _ in pts)))
            continue
        want = full * target / 100.0
        w = interp(want)
        got = depth_at(w)
        if got is not None and abs(got - want) / full > 0.05:
            w = interp(want)                      # refine once with the new point
        chosen.append((target, round(w, 1)))

    # Break collapses, shallowest target first.
    for i, (target, w) in enumerate(chosen):
        if target == 100 or sum(1 for _, x in chosen if abs(x - w) < 1.0) == 1:
            continue
        best = w
        lo, hi = 0.85 * min(ww for ww, _ in pts), min(ww for ww, _ in pts)
        for _ in range(2):
            got = depth_at(lo)
            if got is None:
                break
            if 100.0 * got / full >= FLOOR_PCT:
                best = lo                          # narrower and still above floor
                break
            lo = 0.5 * (lo + hi)                   # undershot -- back off upward
        chosen[i] = (target, round(best, 1))
    return chosen


# --------------------------------------------------------------------------- #
# Runs that expose the coefficients
# --------------------------------------------------------------------------- #

def transistor_fixture(d: Path, fam: str, inputs: Path, sup: float, width: float,
                       v_fixture: float):
    """Transistor into an IBIS-style fixture, so Ku/Kd can be solved for."""
    d.mkdir(parents=True, exist_ok=True)
    deck = vs.transistor_deck(fam, inputs, sup, width, d)
    lines: list[str] = []
    for line in deck.splitlines():
        low = line.strip().lower()
        if low.startswith("rload") or low.startswith("cload"):
            continue
        if low.startswith(".probe"):
            lines.append(f"Vfix fix 0 DC {v_fixture:g}")
            lines.append(f"Rfix pad fix {R_FIXTURE:g}")
            lines.append(".probe tran V(pad)")
            continue
        lines.append(line)
    tr0 = vs._cached_hspice(d, "\n".join(lines) + "\n")
    if tr0 is None:
        return None
    r = sl.parse_hspice_tr0(tr0)
    return sl.time_ns(r), sl.signal(r, "v(pad)")


def native_state(d: Path, ibis: Path, model: str, sup: float, width: float, mode: int):
    """Native IBIS with its own St_pu / St_pd exposed as nodes ku / kd."""
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ibis, d / "input.ibs")
    deck = f"""* variant stressed native rwf{mode}, state probed
.title stressed native rwf{mode} state
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 {vs.short_high_pwl(sup, width)}
VPU pu_ref 0 DC {sup}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {sup}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='input.ibs' model='{model}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf={mode} ramp_fwf={mode} xv_pu=ku xv_pd=kd
Rload pad 0 {vs.R_LOAD}
Cload pad 0 {vs.C_LOAD_PF}p
.probe tran V(pad) V(ku) V(kd)
.tran 0.002n {vs.STOP_NS}n
.end
"""
    tr0 = vs._cached_hspice(d, deck)
    if tr0 is None:
        return None
    r = sl.parse_hspice_tr0(tr0)
    t = sl.time_ns(r)

    def opt(name):
        try:
            return sl.signal(r, name)
        except Exception:                              # noqa: BLE001
            return np.full(len(t), np.nan)

    return t, sl.signal(r, "v(pad)"), opt("v(ku)"), opt("v(kd)")


def pybis_state(d: Path, ibis: Path, model: str, comp: str, sup: float,
                width: float, subckt_type: str):
    """pybis build with its internal Ku / Kd nodes saved alongside the pad."""
    d.mkdir(parents=True, exist_ok=True)
    try:
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)),
                            model_name=model, component_name=comp)
        subcircuit.generate_spice_model("Output", subckt_type, data, "Typical",
                                        str(d / "driver.sub"))
    except Exception:                                  # noqa: BLE001
        return None
    if not (d / "driver.sub").exists():
        return None
    text = (d / "driver.sub").read_text(errors="ignore")
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    nd = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
    nodes = [nd.get(p.upper(), p) for p in pins]
    en = 0.0 if re.search(r"NENABLE\s+0\s+V\s*=\s*\(\s*V\(EN[^)]*\)\s*<", text) else sup
    deck = f"""* variant stressed pybis, state probed
.options reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC {sup}
Vin IN 0 {vs.short_high_pwl(sup, width)}
Ven EN 0 DC {en:g}
X1 {' '.join(nodes)} {m.group(1)}
Rload OUT 0 {vs.R_LOAD}
Cload OUT 0 {vs.C_LOAD_PF}p
.tran 0.002n {vs.STOP_NS}n
.save V(OUT) V(X1.Ku) V(X1.Kd)
.end
"""
    sp, prev = d / "run.sp", d / "run.raw"
    if prev.exists() and sp.exists() and sp.read_text(encoding="utf-8") == deck:
        raw = prev
    else:
        sp.write_text(deck, encoding="utf-8")
        raw = sl.ngspice(d, timeout_s=900)
    if raw is None:
        return None
    r = sl.parse_ngspice_raw(raw)
    t = sl.time_ns(r)

    def opt(*names):
        try:
            return sl.signal(r, *names)
        except Exception:                              # noqa: BLE001
            return np.full(len(t), np.nan)

    return t, sl.trace(r, "out"), opt("v(x1.ku)", "x1.ku"), opt("v(x1.kd)", "x1.kd")


# --------------------------------------------------------------------------- #
# Silicon coefficients
# --------------------------------------------------------------------------- #

def silicon_kukd(ibis: Path, model: str, comp: str, low, high, sup: float, grid):
    """Ku/Kd the transistor actually follows, from its two fixture responses.

    The I-V tables come from the IBIS file -- they describe the DC device
    characteristic, which is not what is in question here; only the switching
    coefficients over time are. Both come from the same netlist via s2ibispy, so
    they are mutually consistent.
    """
    try:
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)),
                            model_name=model, component_name=comp)
    except Exception:                                  # noqa: BLE001
        return None
    lo = np.column_stack([low[0] * 1e-9, low[1]])
    hi = np.column_stack([high[0] * 1e-9, high[1]])
    try:
        sol = solve_silicon_kukd(data, lo, hi, sup)
    except Exception as exc:                           # noqa: BLE001
        print(f"      silicon Ku/Kd solve failed: {exc}")
        return None
    t = sol[:, 0] * 1e9
    return (np.interp(grid, t, sol[:, 1]), np.interp(grid, t, sol[:, 2]),
            np.interp(grid, t, sol[:, 3]))


# --------------------------------------------------------------------------- #
# Figures -- Ku/Kd and pad to separate files
# --------------------------------------------------------------------------- #

def _window(t_edge: float, t_rev: float):
    """Time window scaled to the pulse, not fixed.

    The base-buffer figures used a flat t_rev + 3.5 ns tail, which suits ex2's
    nanosecond pulses but leaves an inv_chain 104 ps case with 85% of the axis
    empty. Ten pulse widths of tail shows the full recovery in both families."""
    width = t_rev - t_edge
    return t_edge - 0.15, t_rev + float(np.clip(10.0 * width, 0.5, 3.5))


def _autoscale(axis):
    """View from the bulk: the two-fixture solve spikes briefly at the input
    edge, and a full-range view flattens every real feature."""
    stacked = np.concatenate([ln.get_ydata() for ln in axis.get_lines()
                              if len(ln.get_ydata()) > 2] or [np.zeros(1)])
    stacked = stacked[np.isfinite(stacked)]
    if len(stacked):
        low, high = np.percentile(stacked, [0.5, 99.5])
        pad = max(0.08, 0.10 * (high - low))
        axis.set_ylim(low - pad, high + pad)


def plot_case(case_dir: Path, title: str, t, series: dict, t_rev: float,
              t_edge: float) -> list[Path]:
    """Two files: coefficients, and pad voltage."""
    written = []

    fig, axes = plt.subplots(2, 1, figsize=(11.0, 7.0), sharex=True)
    for axis, field, label in ((axes[0], "ku", "Ku"), (axes[1], "kd", "Kd")):
        for name, (colour, lw, z) in ORDER.items():
            y = series.get(f"{name}_{field}")
            if y is None or not np.any(np.isfinite(y)):
                continue
            axis.plot(t, y, color=colour, lw=lw, label=name.replace("_", " "), zorder=z)
        axis.axvline(t_rev, color="0.45", ls="--", lw=1.1, zorder=1)
        axis.axhspan(-0.05, 1.05, color="0.93", zorder=0)
        axis.set_ylabel(label)
        axis.grid(alpha=0.25, zorder=0)
        _autoscale(axis)
    axes[0].set_xlim(*_window(t_edge, t_rev))
    axes[0].set_title(f"{title} — switching coefficients", fontsize=11)
    axes[0].legend(fontsize=8.5, ncol=3, loc="best")
    axes[1].set_xlabel("Time (ns)")
    fig.tight_layout()
    p = case_dir / "kukd.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    written.append(p)

    fig, axis = plt.subplots(figsize=(11.0, 4.6))
    for name, (colour, lw, z) in ORDER.items():
        y = series.get(f"{name}_pad")
        if y is None or not np.any(np.isfinite(y)):
            continue
        axis.plot(t, y, color=colour, lw=lw, label=name.replace("_", " "), zorder=z)
    axis.axvline(t_rev, color="0.45", ls="--", lw=1.1, zorder=1)
    axis.set_ylabel("Pad voltage (V)")
    axis.set_xlabel("Time (ns)")
    axis.set_xlim(*_window(t_edge, t_rev))
    axis.grid(alpha=0.25, zorder=0)
    axis.set_title(f"{title} — pad voltage", fontsize=11)
    axis.legend(fontsize=8.5, ncol=3, loc="best")
    fig.tight_layout()
    p = case_dir / "pad.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    written.append(p)
    return written


ORDER = {
    "silicon": (SILICON, 2.8, 6),
    "native": (NATIVE, 1.7, 5),
    "native_rwf1": (NATIVE1, 1.4, 4),
    "gate_state": (METHOD_COLORS["gate_state"], 1.4, 3),
    "delay_cmd": (METHOD_COLORS["delay_cmd"], 1.4, 3),
}


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--variant", action="append",
                    help="restrict to these variant keys (repeatable)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    known = prior_depths()
    full_exc: dict[str, float] = {}
    wanted = set(args.variant or [v[0] for v in vs.VARIANTS])
    summary = []

    for key, fam, sup, ibis, inputs, model, comp, _old in vs.VARIANTS:
        if key not in wanted:
            continue
        if not ibis.exists():
            print(f"{key}: model missing", flush=True)
            continue
        d = OUT / key
        d.mkdir(parents=True, exist_ok=True)
        print(f"\n=== {key} ===", flush=True)
        targets = widths_for_targets(key, fam, inputs, sup, known.get(key, []), d)
        full_exc[key] = max(e for _, e in known.get(key, [(0, 1.0)]))
        print("    depth target -> width: "
              + ", ".join(f"{t}%={w:.0f}ps" for t, w in targets), flush=True)

        for target, width_ps in targets:
            w = width_ps / 1000.0
            cdir = d / f"depth{target}_w{int(round(width_ps))}ps"
            cdir.mkdir(parents=True, exist_ok=True)
            tr = vs.transistor(cdir / "transistor", fam, inputs, sup, w)
            if tr is None:
                print(f"    depth{target}: transistor failed", flush=True)
                continue
            t, si = tr
            base = float(np.median(si[t < vs.RISE_NS - 0.5]))
            exc = float(si.max() - base)
            series = {"silicon_pad": si}

            lo = transistor_fixture(cdir / "fixture_0", fam, inputs, sup, w, 0.0)
            hi = transistor_fixture(cdir / "fixture_vcc", fam, inputs, sup, w, sup)
            if lo is not None and hi is not None:
                sol = silicon_kukd(ibis, model, comp, lo, hi, sup, t)
                if sol is not None:
                    series["silicon_ku"], series["silicon_kd"], cond = sol
                    series["silicon_cond"] = cond

            for tag, mode in (("native", 2), ("native_rwf1", 1)):
                got = native_state(cdir / tag, ibis, model, sup, w, mode)
                if got is None:
                    continue
                tn, pad, ku, kd = got
                series[f"{tag}_pad"] = np.interp(t, tn, pad)
                series[f"{tag}_ku"] = np.interp(t, tn, ku)
                series[f"{tag}_kd"] = np.interp(t, tn, kd)

            for tag, subckt in BUILDS:
                got = pybis_state(cdir / tag, ibis, model, comp, sup, w, subckt)
                if got is None:
                    continue
                tp, pad, ku, kd = got
                series[f"{tag}_pad"] = np.interp(t, tp, pad)
                series[f"{tag}_ku"] = np.interp(t, tp, ku)
                series[f"{tag}_kd"] = np.interp(t, tp, kd)

            cols = ["time_ns"] + sorted(series)
            with (cdir / "waveforms.csv").open("w", newline="", encoding="utf-8") as h:
                wr = csv.writer(h)
                wr.writerow(cols)
                data = [t] + [series[c] for c in cols[1:]]
                wr.writerows(np.column_stack(data))

            t_edge, t_rev = vs.RISE_NS, vs.RISE_NS + w
            # The label must be the depth reached, not the bin aimed at: where
            # the interpolation clamps at the narrowest simulated width, a "50%"
            # target can land at 58%, and a figure captioned 50% would be wrong.
            achieved = 100.0 * exc / full_exc[key]
            title = (f"{key} short-high · {achieved:.0f}% of full swing · "
                     f"{width_ps:.0f} ps pulse")
            figs = plot_case(cdir, title, t, series, t_rev, t_edge)
            have = [n for n in ORDER if f"{n}_ku" in series
                    and np.any(np.isfinite(series[f"{n}_ku"]))]
            print(f"    depth{target:>3}%  {width_ps:>7.0f}ps  exc={exc:.3f} V  "
                  f"ku from: {','.join(have) or 'none'}  -> {figs[0].parent.name}/",
                  flush=True)
            summary.append({"variant": key, "depth_target": target,
                            "width_ps": round(width_ps, 1),
                            "tx_excursion_v": round(exc, 4),
                            "depth_achieved_pct": None})

    if summary:
        for row in summary:
            same = [r for r in summary if r["variant"] == row["variant"]]
            full = max(r["tx_excursion_v"] for r in same)
            row["depth_achieved_pct"] = round(100 * row["tx_excursion_v"] / full, 1)
        csv_path = OUT / "cases.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as h:
            wr = csv.DictWriter(h, fieldnames=list(summary[0]))
            wr.writeheader()
            wr.writerows(summary)
        below = [r for r in summary if r["depth_achieved_pct"] < 50]
        print(f"\nwrote {csv_path}")
        print(f"cases below the 50% floor: {len(below)}"
              + ("" if not below else "  " + ", ".join(
                  f"{r['variant']} {r['depth_achieved_pct']}%" for r in below)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
