#!/usr/bin/env python3
"""Figures for the 2026-08-20 talk: hybrid and pad-matching only.

Deliberately narrower than the current state of the work. Transistor-derived
Ku/Kd and the newer command formulations are held back, so everything here is
scored against HSPICE native IBIS and the transistor pad, which is what the
audience has seen before.

Three figures:

  gate_capacitors   the hidden gate states GUP/GDN on a few cases, to show they
                    stay inside [0,1]. Only the gate-state family has them;
                    pad-matched replay carries no hidden capacitor at all.

  coefficient_range Ku and Kd for the model and for native IBIS, with dV/dt
                    underneath. The coefficients leave [0,1] and the pad slew
                    underneath shows why: the current an IBIS buffer must supply
                    includes C_comp*dV/dt, and near a sharp edge that term is
                    larger than either device can source, so no combination of
                    two coefficients inside [0,1] can produce it.

  stress_<device>   all five stress levels, both directions, hybrid and
                    pad-matching against native IBIS and the transistor.
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402
from run_stress_method_matrix import case_tag, stress_cases  # noqa: E402

MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"

TRANSISTOR = "#111111"
NATIVE = "#2B6CA3"
HYBRID = "#A16207"
PADMATCH = "#7B2CBF"   # distinct from the native-IBIS blue
GUP = "#C02626"
GDN = "#1B7F5A"
WARN_SOFT = "#F7EBE2"

SHOWN = [("hybrid", "hybrid", HYBRID), ("pad_match", "pad-matched replay", PADMATCH)]

# Distinct line styles as well as colours. Overlaid traces on a shared axis are
# hard to tell apart by hue alone, especially where they nearly coincide, and
# hue is the first thing lost to a projector.
STYLE = {"hybrid": (HYBRID, "--", 1.9), "pad_match": (PADMATCH, "-.", 1.9)}


def active_end(t, traces, t_rev, tol=0.02, margin=0.45):
    """Returns a crop time just past the last real activity.

    These records run to 22 ns and settle within a nanosecond or two of the
    reversal, so a fixed window leaves most of the panel flat -- worst on
    inv_chain, whose pulses are around 110 ps. Crop where every trace has come
    within `tol` of its own final value and stayed there.
    """
    last = t_rev
    for y in traces:
        y = np.asarray(y, dtype=float)
        ok = np.isfinite(y)
        if ok.sum() < 5:
            continue
        settled = y[ok][-1]
        moving = np.where(np.abs(y[ok] - settled) > tol)[0]
        if len(moving):
            last = max(last, float(t[ok][moving[-1]]))
    return min(last + margin, float(t[-1]))



def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def find_raw(method: str, device: str, tag: str):
    hits = glob.glob(str(MATRIX / method / "ngspice_runs" / device / "*" / "*" /
                         "cases" / f"{tag.split(device + '_')[1]}_*" /
                         "ngspice_gate_state" / "run.raw"))
    return Path(hits[0]) if hits else None


def gate_capacitors(out_dir: Path, picks) -> None:
    fig, axes = plt.subplots(2, len(picks), figsize=(4.6 * len(picks), 7.4), squeeze=False)
    drew = False
    for col, (device, direction, target, width_ps) in enumerate(picks):
        tag = case_tag(device, direction, width_ps)
        raw = find_raw("hybrid", device, tag)
        if raw is None:
            continue
        r = parse_ngspice_raw(raw)
        k = {x.lower(): x for x in r}
        t = np.asarray(r[k["time"]]) * 1e9
        gup = np.asarray(r[k["v(xdrv.gup)"]])
        gdn = np.asarray(r[k["v(xdrv.gdn)"]])
        pad = np.asarray(r[k["v(pad)"]])
        edge_ns = 5.0 if direction == "short_high" else 10.0
        t_rev = edge_ns + width_ps / 1000.0

        top = axes[0][col]
        top.axhspan(0.0, 1.0, color="#E4EDF7", zorder=0, label="[0, 1]")
        top.plot(t, gup, color=GUP, lw=1.8, label="GUP (pullup gate state)", zorder=3)
        top.plot(t, gdn, color=GDN, lw=1.8, label="GDN (pulldown gate state)", zorder=3)
        top.axhline(0.0, color="0.6", lw=0.8)
        top.axhline(1.0, color="0.6", lw=0.8)
        top.axvline(t_rev, color="0.45", ls="--", lw=1.1)
        top.set_ylim(-0.14, 1.14)
        top.set_title(f"{device} {direction.replace('short_', 'short-')} · {target}% swing",
                      fontsize=10.5)
        top.grid(alpha=0.22)
        lo, hi = float(min(gup.min(), gdn.min())), float(max(gup.max(), gdn.max()))
        top.text(0.02, 0.04, f"range {lo:.4f} … {hi:.4f}", transform=top.transAxes,
                 fontsize=9, family="monospace",
                 bbox=dict(fc="white", ec="#B6C2CD", pad=3.5))

        # Annotate the state the pulse switches *on* -- the pullup on a
        # short-high, the pulldown on a short-low. Its peak is the number that
        # matters: how far the transition actually travelled before the reverse
        # command caught it. Picking by largest excursion instead would label the
        # state that fully switches and recovers, which shows nothing.
        window = (t >= edge_ns) & (t <= t_rev + 2.0)
        switching_on = gup if direction == "short_high" else gdn
        if not window.any():
            continue
        reached = float(np.nanmax(switching_on[window]))
        t_at = float(t[window][int(np.nanargmax(switching_on[window]))])
        caption = (f"reached {reached:.3f}\nbefore reversing" if reached < 0.99
                   else f"fully switched\n({reached:.3f})")
        top.plot([t_at], [reached], "o", color="#151E28", ms=7, zorder=6)
        top.annotate(caption, (t_at, reached), textcoords="offset points", xytext=(12, -34),
                     fontsize=9, fontweight="bold", color="#151E28",
                     bbox=dict(fc="white", ec="#B6C2CD", alpha=0.92, pad=3),
                     arrowprops=dict(arrowstyle="->", color="#151E28", lw=1.1))
        if col == 0:
            top.set_ylabel("hidden gate state")
            top.legend(fontsize=8.5, loc="center right")

        bottom = axes[1][col]
        bottom.plot(t, pad, color=HYBRID, lw=1.6)
        bottom.axvline(t_rev, color="0.45", ls="--", lw=1.1)
        bottom.grid(alpha=0.22)
        bottom.set_xlabel("Time (ns)")
        if col == 0:
            bottom.set_ylabel("Pad (V)")
        end = active_end(t, [gup, gdn, pad], t_rev, tol=0.01, margin=0.35)
        for axis in (top, bottom):
            axis.set_xlim(edge_ns - 0.3, end)
        drew = True
    if not drew:
        plt.close(fig)
        return
    fig.suptitle("Hidden gate states stay inside [0, 1] — the model is bounded by construction",
                 fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    path = out_dir / "gate_capacitors.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT)}")


def coefficient_range(out_dir: Path, picks) -> None:
    """Ku/Kd for model and native IBIS, with pad slew underneath to explain range."""
    fig, axes = plt.subplots(3, len(picks), figsize=(4.6 * len(picks), 9.6), squeeze=False)
    drew = False
    for col, (device, direction, target, width_ps) in enumerate(picks):
        tag = case_tag(device, direction, width_ps)
        path = MATRIX / "hybrid" / "waveforms" / f"{tag}.csv"
        if not path.exists():
            continue
        d = load(path)
        t = d["time_ns"]
        edge_ns = 5.0 if direction == "short_high" else 10.0
        t_rev = edge_ns + width_ps / 1000.0
        window = (t >= edge_ns - 0.3) & (t <= t_rev + 3.0)

        for row, coeff in enumerate(("ku", "kd")):
            axis = axes[row][col]
            axis.axhspan(0.0, 1.0, color="#E4EDF7", zorder=0)
            axis.axhline(0.0, color="0.6", lw=0.8)
            axis.axhline(1.0, color="0.6", lw=0.8)
            axis.plot(t, d[f"hspice_{coeff}"], color=NATIVE, lw=1.7,
                      label="HSPICE native IBIS", zorder=3)
            axis.plot(t, d[f"pybis_{coeff}"], color=HYBRID, lw=1.7,
                      label="hybrid model", zorder=4)
            axis.axvline(t_rev, color="0.45", ls="--", lw=1.1)
            axis.grid(alpha=0.22)
            both = np.concatenate([d[f"hspice_{coeff}"][window], d[f"pybis_{coeff}"][window]])
            both = both[np.isfinite(both)]
            if len(both):
                lo, hi = np.percentile(both, [0.2, 99.8])
                span = max(0.12, 0.12 * (hi - lo))
                axis.set_ylim(min(lo - span, -0.12), max(hi + span, 1.12))
            if col == 0:
                axis.set_ylabel(coeff.replace("k", "K"))
            if row == 0:
                axis.set_title(f"{device} {direction.replace('short_', 'short-')} · {target}%",
                               fontsize=10.5)
                axis.legend(fontsize=8.5, loc="best")

        slew = axes[2][col]
        for src, colour, label in (("hspice", NATIVE, "native IBIS"),
                                   ("pybis", HYBRID, "hybrid model")):
            pad = d[f"{src}_pad"]
            dv = np.gradient(pad, t)          # V/ns
            slew.plot(t, dv, color=colour, lw=1.5, label=label)
        slew.axvline(t_rev, color="0.45", ls="--", lw=1.1)
        slew.axhline(0.0, color="0.6", lw=0.8)
        slew.grid(alpha=0.22)
        slew.set_xlabel("Time (ns)")
        if col == 0:
            slew.set_ylabel("pad slew dV/dt (V/ns)")
            slew.legend(fontsize=8.5, loc="best")
        for row in range(3):
            axes[row][col].set_xlim(edge_ns - 0.3, t_rev + 3.0)
        drew = True
    if not drew:
        plt.close(fig)
        return
    fig.suptitle("Ku and Kd leave [0, 1] — and the pad slew underneath shows why",
                 fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    path = out_dir / "coefficient_range.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT)}")


def stress_grids(out_dir: Path) -> None:
    grouped: dict[str, list] = {}
    for device, direction, widths in stress_cases():
        grouped.setdefault(device, []).append((direction, widths))
    for device, entries in grouped.items():
        levels = len(entries[0][1])
        fig, axes = plt.subplots(len(entries), levels,
                                 figsize=(3.5 * levels, 4.0 * len(entries)), squeeze=False)
        drew = False
        for row, (direction, widths) in enumerate(entries):
            for col, (target, width_ps) in enumerate(widths):
                axis = axes[row][col]
                tag = case_tag(device, direction, width_ps)
                edge_ns = 5.0 if direction == "short_high" else 10.0
                t_rev = edge_ns + width_ps / 1000.0
                first = True
                traces = []
                for key, label, colour in SHOWN:
                    p = MATRIX / key / "waveforms" / f"{tag}.csv"
                    if not p.exists():
                        continue
                    d = load(p)
                    t = d["time_ns"]
                    if first:
                        axis.plot(t, d["silicon_pad"], color=TRANSISTOR, lw=2.8,
                                  label="HSPICE transistor", zorder=6)
                        axis.plot(t, d["hspice_pad"], color=NATIVE, lw=1.7, ls=":",
                                  label="HSPICE native IBIS", zorder=5)
                        axis.axvline(t_rev, color="0.5", ls="--", lw=1.0)
                        traces += [d["silicon_pad"], d["hspice_pad"]]
                        first, drew = False, True
                    style_colour, dashes, width = STYLE[key]
                    axis.plot(t, d["pybis_pad"], lw=width, ls=dashes,
                              color=style_colour, label=label, zorder=3)
                    traces.append(d["pybis_pad"])
                if traces:
                    axis.set_xlim(edge_ns - 0.2, active_end(t, traces, t_rev))
                axis.set_title(f"{target}% swing · {width_ps:.0f} ps", fontsize=9.5)
                axis.grid(alpha=0.22)
                axis.tick_params(labelsize=8)
                if col == 0:
                    axis.set_ylabel(f"{direction.replace('short_', 'short ')}\nPad (V)", fontsize=9)
                if row == len(entries) - 1:
                    axis.set_xlabel("Time (ns)", fontsize=9)
        if not drew:
            plt.close(fig)
            continue
        handles, labels = axes[0][0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=9.5,
                   frameon=False, bbox_to_anchor=(0.5, -0.005))
        fig.suptitle(f"{device} — 90% to 50% loaded-swing stress", fontsize=12.5)
        fig.tight_layout(rect=(0, 0.045, 1, 0.965))
        path = out_dir / f"stress_{device}.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        print(f"wrote {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "presentation_2026-08-20" / "figures")
    args = parser.parse_args()
    out_dir = args.out if args.out.is_absolute() else ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    # One case per buffer, at a stress level where the reversal is unmistakable.
    # Chosen so each panel shows a transition genuinely caught in flight.
    picks = [("inv_chain", "short_low", 90, 115.992),
             ("ex2", "short_high", 70, 857.6),
             ("io_buf", "short_high", 70, 1852.6)]

    gate_capacitors(out_dir, picks)
    pad_matching_walkthrough(out_dir)
    coefficient_range(out_dir, picks)
    stress_grids(out_dir)
    return 0



def pad_matching_walkthrough(out_dir: Path, device="io_buf", direction="short_high",
                             target=80, width_ps=2090.0) -> None:
    """The pad-matching method drawn on its own real data.

    The case is chosen so the pad is genuinely mid-transition when the input
    reverses. On buffers with a long propagation delay -- ex2 is about a
    nanosecond -- the pad has not started moving at the reverse edge, the
    latched voltage falls outside the opposite trajectory entirely, and the
    lookup has nothing to resolve.

    Three panels following the method in order: the two reference trajectories
    recorded offline, the voltage-to-time lookup built by inverting them, and a
    real reversal resolved through that lookup. Nothing here is schematic -- the
    trajectories are the calibration JSON the model was built from, and the
    reversal is a case out of the stress sweep.
    """
    import json

    ref_path = (MATRIX / "pad_match" / "calibration" / device / "fast_5ps"
                / "pad_replay_reference.json")
    wave_path = MATRIX / "pad_match" / "waveforms" / f"{case_tag(device, direction, width_ps)}.csv"
    if not (ref_path.exists() and wave_path.exists()):
        print(f"walkthrough: missing inputs for {device}")
        return
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    rise_t = np.asarray(ref["rising"]["time_ns"], dtype=float)
    rise_v = np.asarray(ref["rising"]["pad_v"], dtype=float)
    fall_t = np.asarray(ref["falling"]["time_ns"], dtype=float)
    fall_v = np.asarray(ref["falling"]["pad_v"], dtype=float)

    # Crop each reference to where it is still moving; both records run to 14 ns
    # and are flat for most of it.
    def crop(t, v):
        settled = v[-1]
        moving = np.where(np.abs(v - settled) > 0.02)[0]
        end = t[moving[-1]] + 0.4 if len(moving) else t[-1]
        keep = t <= end
        return t[keep], v[keep]

    rise_t, rise_v = crop(rise_t, rise_v)
    fall_t, fall_v = crop(fall_t, fall_v)

    d = load(wave_path)
    t = d["time_ns"]
    edge_ns = 5.0 if direction == "short_high" else 10.0
    t_rev = edge_ns + width_ps / 1000.0
    v_latched = float(np.interp(t_rev, t, d["pybis_pad"]))

    # The reversal on a short-high pulse is a falling edge, so the opposite
    # trajectory is the falling one; find where it first holds the latched pad.
    opp_t, opp_v = (fall_t, fall_v) if direction == "short_high" else (rise_t, rise_v)
    crossings = np.where(np.diff(np.sign(opp_v - v_latched)) != 0)[0]
    t0 = float(opp_t[crossings[0]]) if len(crossings) else float("nan")

    fig, axes = plt.subplots(1, 3, figsize=(15.0, 5.0))

    ax = axes[0]
    ax.plot(rise_t, rise_v, color="#C02626", lw=2.0, label="rising reference")
    ax.plot(fall_t, fall_v, color="#1B7F5A", lw=2.0, label="falling reference")
    ax.set_title("1 · recorded offline, once per buffer", fontsize=10.5)
    ax.set_xlabel("time since edge (ns)")
    ax.set_ylabel("pad (V)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9)

    ax = axes[1]
    # Where the trajectory is flat in voltage the inverse is near-vertical, so a
    # few millivolts of pad error map to a large time error. Shading those bands
    # states the method's real limit rather than leaving it to be inferred.
    with np.errstate(divide="ignore", invalid="ignore"):
        dtdv = np.gradient(opp_t, opp_v)
    steep = np.abs(dtdv) > 5.0 * np.nanmedian(np.abs(dtdv))
    if steep.any():
        lo_v, hi_v = float(np.nanmin(opp_v)), float(np.nanmax(opp_v))
        span = hi_v - lo_v
        for edge_lo, edge_hi in ((lo_v, lo_v + 0.06 * span), (hi_v - 0.06 * span, hi_v)):
            ax.axvspan(edge_lo, edge_hi, color=WARN_SOFT, zorder=0)
        ax.text(0.5, 0.94, "shaded: lookup ill-conditioned", transform=ax.transAxes,
                ha="center", fontsize=8.5, color="#AE4E19")
    ax.plot(opp_v, opp_t, color="#1B7F5A" if direction == "short_high" else "#C02626", lw=2.0)
    ax.axvline(v_latched, color=PADMATCH, ls="-.", lw=1.8)
    if np.isfinite(t0):
        ax.plot([v_latched], [t0], "o", color=PADMATCH, ms=9, zorder=5)
        ax.annotate(f"t₀ = {t0:.3f} ns", (v_latched, t0), textcoords="offset points",
                    xytext=(12, 10), fontsize=9.5, color=PADMATCH, fontweight="bold")
    # Show the ambiguity honestly: how many times the trajectory holds this value.
    ax.set_title(f"2 · inverted to voltage → time  ({len(crossings)} crossing"
                 f"{'s' if len(crossings) != 1 else ''} at this voltage)", fontsize=10.5)
    ax.set_xlabel("pad voltage (V)")
    ax.set_ylabel("time along the opposite edge (ns)")
    ax.grid(alpha=0.25)

    ax = axes[2]
    end = active_end(t, [d["silicon_pad"], d["hspice_pad"], d["pybis_pad"]], t_rev)
    ax.plot(t, d["silicon_pad"], color=TRANSISTOR, lw=2.8, label="HSPICE transistor")
    ax.plot(t, d["pybis_pad"], color=PADMATCH, ls="-.", lw=1.9, label="pad-matched replay")
    ax.axvline(t_rev, color="0.45", ls="--", lw=1.2)
    ax.axhline(v_latched, color=PADMATCH, lw=0.9, alpha=0.6)
    ax.plot([t_rev], [v_latched], "o", color=PADMATCH, ms=9, zorder=6)
    ax.annotate(f"pad latched once\n{v_latched:.3f} V", (t_rev, v_latched),
                textcoords="offset points", xytext=(14, -34), fontsize=9.5,
                color=PADMATCH, fontweight="bold")
    ax.set_xlim(edge_ns - 0.2, end)
    ax.set_title(f"3 · run time — {device} {direction.replace('short_', 'short-')} {target}%",
                 fontsize=10.5)
    ax.set_xlabel("time (ns)")
    ax.set_ylabel("pad (V)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9, loc="best")

    fig.suptitle("Pad-matched replay on its own data: record, invert, then re-enter at the match",
                 fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    path = out_dir / "pad_matching_walkthrough.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT)}")

if __name__ == "__main__":
    raise SystemExit(main())
