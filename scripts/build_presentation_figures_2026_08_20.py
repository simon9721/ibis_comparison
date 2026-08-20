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

ROOT = Path(__file__).resolve().parents[1]
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

SHOWN = [("hybrid", "hybrid", HYBRID), ("pad_match", "pad-matched replay", PADMATCH)]


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
        for axis in (top, bottom):
            axis.set_xlim(edge_ns - 0.3, t_rev + 3.5)
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
                for key, label, colour in SHOWN:
                    p = MATRIX / key / "waveforms" / f"{tag}.csv"
                    if not p.exists():
                        continue
                    d = load(p)
                    t = d["time_ns"]
                    if first:
                        axis.plot(t, d["silicon_pad"], color=TRANSISTOR, lw=2.6,
                                  label="HSPICE transistor", zorder=6)
                        axis.plot(t, d["hspice_pad"], color=NATIVE, lw=1.6,
                                  label="HSPICE native IBIS", zorder=5)
                        axis.axvline(t_rev, color="0.5", ls="--", lw=1.0)
                        axis.set_xlim(edge_ns - 0.2, t_rev + 3.5)
                        first, drew = False, True
                    axis.plot(t, d["pybis_pad"], lw=1.5, color=colour, label=label, zorder=3)
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
    picks = [("inv_chain", "short_low", 90, 115.992),
             ("ex2", "short_high", 70, 857.6),
             ("io_buf", "short_low", 70, 220.1)]

    gate_capacitors(out_dir, picks)
    coefficient_range(out_dir, picks)
    stress_grids(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
