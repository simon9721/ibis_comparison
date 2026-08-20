#!/usr/bin/env python3
"""Plot the 90%-50% stress sweep: every method, every level, all three buffers.

Two views, because they answer different questions.

`{device}_stress.png` is the waveform grid -- five stress levels across, both
directions down, every method overlaid on silicon. This is where shape defects
live: an extra dip, a response that starts before the input edge, an excursion
that overshoots. A mean error cannot show any of those.

`error_vs_stress.png` is the same data as curves of error against stress level.
It answers the question the sweep was built to ask -- not which method is best
on average, but how each one degrades as the pulse gets harder, and where the
orderings cross.

An earlier version plotted only the mildest and harshest level, which left
three of the five with no cross-method figure at all.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))
sys.path.insert(0, str(ROOT / "scripts"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from run_stress_method_matrix import METHODS, case_tag, stress_cases  # noqa: E402

SILICON = "#111111"
NATIVE = "#2B6CA3"
METHOD_COLORS = {
    "gate_state": "#C02626",
    "delay_cmd": "#1B7F5A",
    "predriver_cmd": "#7B2CBF",
    "legacy": "#8A8A8A",
    "coeff_match": "#D97706",
    "pad_match": "#0E7490",
    "pad_match_slew": "#9A3412",
    "hybrid": "#A16207",
}


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def time_rmse(a, b, t):
    ok = np.isfinite(a) & np.isfinite(b)
    a, b, t = a[ok], b[ok], t[ok]
    if len(t) < 2 or t[-1] <= t[0]:
        return float("nan")
    return float(np.sqrt(np.trapezoid((a - b) ** 2, t) / (t[-1] - t[0])))


def waveform_grid(root, out_dir, available):
    grouped = {}
    for device, direction, widths in stress_cases():
        grouped.setdefault(device, []).append((direction, widths))

    for device, entries in grouped.items():
        levels = len(entries[0][1])
        fig, axes = plt.subplots(len(entries), levels,
                                 figsize=(3.5 * levels, 4.0 * len(entries)),
                                 squeeze=False)
        drew = False
        for row, (direction, widths) in enumerate(entries):
            for col, (target, width_ps) in enumerate(widths):
                axis = axes[row][col]
                tag = case_tag(device, direction, width_ps)
                edge_ns = 5.0 if direction == "short_high" else 10.0
                t_rev = edge_ns + width_ps / 1000.0
                first = True
                for key in available:
                    path = root / key / "waveforms" / f"{tag}.csv"
                    if not path.exists():
                        continue
                    d = load(path)
                    t = d["time_ns"]
                    if first:
                        axis.plot(t, d["silicon_pad"], color=SILICON, lw=2.6,
                                  label="silicon (transistor)", zorder=6)
                        axis.plot(t, d["hspice_pad"], color=NATIVE, lw=1.6,
                                  label="HSPICE native IBIS", zorder=5)
                        axis.axvline(t_rev, color="0.5", ls="--", lw=1.0, zorder=1)
                        axis.set_xlim(edge_ns - 0.2, t_rev + 3.5)
                        first, drew = False, True
                    axis.plot(t, d["pybis_pad"], lw=1.3,
                              color=METHOD_COLORS.get(key, "#444"), label=key, zorder=3)
                axis.set_title(f"{target}% swing · {width_ps:.0f} ps", fontsize=9.5)
                axis.grid(alpha=0.22)
                axis.tick_params(labelsize=8)
                if col == 0:
                    axis.set_ylabel(f"{direction.replace('short_', 'short ')}\nPad (V)",
                                    fontsize=9)
                if row == len(entries) - 1:
                    axis.set_xlabel("Time (ns)", fontsize=9)
        if not drew:
            plt.close(fig)
            continue
        handles, labels = axes[0][0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=min(6, len(labels)),
                   fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.005))
        fig.suptitle(f"{device} — 90% to 50% loaded-swing stress, every method against silicon",
                     fontsize=12.5)
        fig.tight_layout(rect=(0, 0.045, 1, 0.965))
        path = out_dir / f"{device}_stress.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        print(f"wrote {path.relative_to(ROOT)}")


def error_curves(root, out_dir, available):
    combos = stress_cases()
    fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.0), squeeze=False)
    order = {("short_high", d): (0, i) for i, d in enumerate(["ex2", "inv_chain", "io_buf"])}
    order.update({("short_low", d): (1, i) for i, d in enumerate(["ex2", "inv_chain", "io_buf"])})
    drew = False
    for device, direction, widths in combos:
        if (direction, device) not in order:
            continue
        r, c = order[(direction, device)]
        axis = axes[r][c]
        targets = [t for t, _ in widths]
        native_series = []
        for key in ["native"] + available:
            values = []
            for target, width_ps in widths:
                path = None
                for candidate in available:
                    p = root / candidate / "waveforms" / f"{case_tag(device, direction, width_ps)}.csv"
                    if p.exists():
                        path = p
                        break
                if key != "native":
                    path = root / key / "waveforms" / f"{case_tag(device, direction, width_ps)}.csv"
                    if not path.exists():
                        values.append(np.nan)
                        continue
                if path is None:
                    values.append(np.nan)
                    continue
                d = load(path)
                src = "hspice" if key == "native" else "pybis"
                values.append(time_rmse(d[f"{src}_pad"], d["silicon_pad"], d["time_ns"]) * 1000)
            if all(not np.isfinite(v) for v in values):
                continue
            drew = True
            if key == "native":
                native_series = values
                axis.plot(targets, values, color=NATIVE, lw=2.4, marker="s", ms=5,
                          label="HSPICE native IBIS", zorder=5)
            else:
                axis.plot(targets, values, lw=1.6, marker="o", ms=4,
                          color=METHOD_COLORS.get(key, "#444"), label=key, zorder=3)
        axis.set_title(f"{device} {direction.replace('short_', 'short-')}", fontsize=10.5)
        axis.set_xticks(targets)
        axis.invert_xaxis()          # harsher stress to the right
        axis.grid(alpha=0.22)
        axis.tick_params(labelsize=8.5)
        if c == 0:
            axis.set_ylabel("pad error vs silicon (mV)", fontsize=9.5)
        if r == 1:
            axis.set_xlabel("target swing before reversal (%) — harsher →", fontsize=9)
    if not drew:
        return
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=min(6, len(labels)),
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("How each method degrades along the stress axis", fontsize=13)
    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    path = out_dir / "error_vs_stress.png"
    fig.savefig(path, dpi=145)
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT)}")


def per_case(root, out_dir, available):
    """
    One figure per stress case: Ku, Kd and pad, every method against silicon.

    Follows the layout the earlier short-pulse studies used, except that all
    methods share the axes rather than each getting its own plot. The
    coefficients matter as much as the pad here -- two methods can land the same
    pad voltage through a different Ku/Kd split, and only these panels show it.
    """
    case_dir = out_dir / "cases"
    case_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for device, direction, widths in stress_cases():
        for target, width_ps in widths:
            tag = case_tag(device, direction, width_ps)
            edge_ns = 5.0 if direction == "short_high" else 10.0
            t_rev = edge_ns + width_ps / 1000.0
            fig, axes = plt.subplots(3, 1, figsize=(11.0, 9.4), sharex=True)
            first = True
            for key in available:
                path = root / key / "waveforms" / f"{tag}.csv"
                if not path.exists():
                    continue
                d = load(path)
                t = d["time_ns"]
                for axis, field in zip(axes, ("ku", "kd", "pad")):
                    if first:
                        axis.plot(t, d[f"silicon_{field}"], color=SILICON, lw=2.8,
                                  label="silicon (transistor)", zorder=6)
                        axis.plot(t, d[f"hspice_{field}"], color=NATIVE, lw=1.7,
                                  label="HSPICE native IBIS", zorder=5)
                        axis.axvline(t_rev, color="0.45", ls="--", lw=1.1, zorder=1)
                        if field != "pad":
                            axis.axhspan(-0.05, 1.05, color="0.93", zorder=0)
                    axis.plot(t, d[f"pybis_{field}"], lw=1.4,
                              color=METHOD_COLORS.get(key, "#444"), label=key, zorder=3)
                first = False
            if first:
                plt.close(fig)
                continue
            for axis, label in zip(axes, ("Ku", "Kd", "Pad voltage (V)")):
                axis.set_ylabel(label)
                axis.grid(alpha=0.25, zorder=0)
                # The two-fixture solve spikes briefly at the input edge; view
                # from the bulk or that spike flattens every real feature.
                stacked = np.concatenate([line.get_ydata() for line in axis.get_lines()
                                          if len(line.get_ydata()) > 2])
                stacked = stacked[np.isfinite(stacked)]
                if len(stacked):
                    low, high = np.percentile(stacked, [0.5, 99.5])
                    pad_y = max(0.08, 0.10 * (high - low))
                    axis.set_ylim(low - pad_y, high + pad_y)
            axes[0].set_xlim(edge_ns - 0.2, t_rev + 3.5)
            axes[0].set_title(
                f"{device} {direction.replace('short_', 'short-')} · {target}% swing · "
                f"{width_ps:.0f} ps pulse", fontsize=11)
            axes[0].legend(fontsize=8.5, ncol=3, loc="best")
            axes[2].set_xlabel("Time (ns)")
            fig.tight_layout()
            path = case_dir / f"{device}_{direction}_{target}pct.png"
            fig.savefig(path, dpi=140)
            plt.close(fig)
            written += 1
    print(f"wrote {written} per-case figures to {case_dir.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path,
                        default=ROOT / "results" / "stress_method_matrix_2026-08-20")
    args = parser.parse_args()
    root = args.matrix if args.matrix.is_absolute() else ROOT / args.matrix
    out_dir = root / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    available = [k for k, _, _ in METHODS if (root / k / "waveforms").exists()]
    if not available:
        print(f"no method output under {root}")
        return 1
    waveform_grid(root, out_dir, available)
    error_curves(root, out_dir, available)
    per_case(root, out_dir, available)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
