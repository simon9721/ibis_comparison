#!/usr/bin/env python3
"""One figure per case, flat and numbered, for dropping straight into slides.

Follows the layout of the 2026-08-18 hybrid sweep set so the two are directly
comparable: wide single-panel pad plots, stacked Ku/Kd plots, a bold
`buffer | direction | target` title, the transistor drawn thick and grey behind
native IBIS in black, and the reverse edge marked.

Three types per case rather than two. The gate-state plot is new: GUP and GDN
for every case, not just the few that made the talk, so a claim about the hidden
states can be checked anywhere rather than trusted from a sample.

Panels are cropped where the traces stop moving. inv_chain pulses are around
110 ps and these records run to 22 ns, so a fixed window is mostly flat.
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

TRANSISTOR = "#808080"
NATIVE = "#000000"
HYBRID = "#7B3FBF"
PADMATCH = "#D62728"
GUP_C = "#C02626"
GDN_C = "#1B7F5A"

# Buffer order matches the 2026-08-18 set so figure N lines up with figure N.
DEVICE_ORDER = ["io_buf", "inv_chain", "ex2"]
DPI = 180
WIDE = (14.2, 6.0)
STACK = (14.2, 8.4)


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, values = rows[0], np.array([[float(x) for x in r] for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(header)}


def find_raw(method: str, device: str, tag: str):
    hits = glob.glob(str(MATRIX / method / "ngspice_runs" / device / "*" / "*" /
                         "cases" / f"{tag.split(device + '_')[1]}_*" /
                         "ngspice_gate_state" / "run.raw"))
    return Path(hits[0]) if hits else None


def active_window(t, traces, edge_ns, t_rev, tol=0.02, margin=0.5, minimum=1.2):
    last = t_rev
    for y in traces:
        y = np.asarray(y, dtype=float)
        ok = np.isfinite(y)
        if ok.sum() < 5:
            continue
        moving = np.where(np.abs(y[ok] - y[ok][-1]) > tol)[0]
        if len(moving):
            last = max(last, float(t[ok][moving[-1]]))
    start = edge_ns - 0.25
    end = min(max(last + margin, start + minimum), float(t[-1]))
    return start, end


def style(axis, title=None):
    axis.grid(alpha=0.3, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=11)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")
    if title:
        axis.set_title(title, fontsize=17, fontweight="bold", pad=12)


def pad_figure(path, label, d, edge_ns, t_rev, pad_match):
    t = d["time_ns"]
    fig, axis = plt.subplots(figsize=WIDE)
    axis.plot(t, d["silicon_pad"], color=TRANSISTOR, lw=5.0, label="HSPICE transistor", zorder=2)
    axis.plot(t, d["hspice_pad"], color=NATIVE, lw=3.0, label="HSPICE native IBIS", zorder=3)
    axis.plot(t, d["pybis_pad"], color=HYBRID, lw=2.2, label="hybrid", zorder=4)
    traces = [d["silicon_pad"], d["hspice_pad"], d["pybis_pad"]]
    if pad_match is not None:
        axis.plot(pad_match["time_ns"], pad_match["pybis_pad"], color=PADMATCH, lw=2.2,
                  label="pad-matched replay", zorder=5)
        traces.append(pad_match["pybis_pad"])
    axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.6, label="reverse edge", zorder=1)
    axis.set_xlim(*active_window(t, traces, edge_ns, t_rev))
    axis.set_xlabel("Time (ns)", fontsize=12)
    axis.set_ylabel("Pad voltage (V)", fontsize=12)
    style(axis, label)
    axis.legend(fontsize=11, ncol=2, loc="upper right", framealpha=0.92)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def kukd_figure(path, label, d, edge_ns, t_rev, pad_match):
    t = d["time_ns"]
    fig, axes = plt.subplots(2, 1, figsize=STACK, sharex=True)
    traces = [d["silicon_pad"], d["hspice_pad"], d["pybis_pad"]]
    for axis, coeff in zip(axes, ("ku", "kd")):
        axis.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        axis.plot(t, d[f"hspice_{coeff}"], color=NATIVE, lw=3.0,
                  label="HSPICE native IBIS", zorder=3)
        axis.plot(t, d[f"pybis_{coeff}"], color=HYBRID, lw=2.2, label="hybrid", zorder=4)
        if pad_match is not None:
            axis.plot(pad_match["time_ns"], pad_match[f"pybis_{coeff}"], color=PADMATCH,
                      lw=2.2, label="pad-matched replay", zorder=5)
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.6, zorder=1)
        axis.set_ylabel(coeff.replace("k", "K"), fontsize=13)
        style(axis)
    axes[0].set_title(label, fontsize=17, fontweight="bold", pad=12)
    axes[0].legend(fontsize=11, ncol=3, loc="lower center", framealpha=0.92)
    axes[1].set_xlabel("Time (ns)", fontsize=12)
    axes[0].set_xlim(*active_window(t, traces, edge_ns, t_rev))
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def gate_figure(path, label, device, tag, edge_ns, t_rev, direction):
    raw = find_raw("hybrid", device, tag)
    if raw is None:
        return False
    r = parse_ngspice_raw(raw)
    k = {x.lower(): x for x in r}
    if "v(xdrv.gup)" not in k:
        return False
    t = np.asarray(r[k["time"]]) * 1e9
    gup = np.asarray(r[k["v(xdrv.gup)"]])
    gdn = np.asarray(r[k["v(xdrv.gdn)"]])
    pad = np.asarray(r[k["v(pad)"]])

    fig, axes = plt.subplots(2, 1, figsize=STACK, sharex=True)
    top, bottom = axes
    top.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0, label="[0, 1]")
    top.plot(t, gup, color=GUP_C, lw=2.6, label="GUP (pullup gate state)", zorder=3)
    top.plot(t, gdn, color=GDN_C, lw=2.6, label="GDN (pulldown gate state)", zorder=3)
    for level in (0.0, 1.0):
        top.axhline(level, color="#8A8A8A", lw=1.0)
    top.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.6, zorder=1)
    top.set_ylim(-0.15, 1.15)
    top.set_ylabel("hidden gate state", fontsize=12)

    window = (t >= edge_ns) & (t <= t_rev + 2.0)
    switching_on = gup if direction == "short_high" else gdn
    if window.any():
        reached = float(np.nanmax(switching_on[window]))
        t_at = float(t[window][int(np.nanargmax(switching_on[window]))])
        top.plot([t_at], [reached], "o", color="#151E28", ms=9, zorder=6)
        top.annotate(f"reached {reached:.3f} before reversing" if reached < 0.99
                     else f"fully switched ({reached:.3f})",
                     (t_at, reached), textcoords="offset points", xytext=(14, -30),
                     fontsize=11, fontweight="bold", color="#151E28",
                     bbox=dict(fc="white", ec="#8A96A3", alpha=0.93, pad=4),
                     arrowprops=dict(arrowstyle="->", color="#151E28", lw=1.3))
    lo = float(min(gup.min(), gdn.min()))
    hi = float(max(gup.max(), gdn.max()))
    top.text(0.008, 0.05, f"range {lo:.4f} … {hi:.4f}", transform=top.transAxes,
             fontsize=11, family="monospace",
             bbox=dict(fc="white", ec="#8A96A3", pad=4))
    style(top)
    top.set_title(label, fontsize=17, fontweight="bold", pad=12)
    top.legend(fontsize=11, ncol=3, loc="center right", framealpha=0.92)

    bottom.plot(t, pad, color=HYBRID, lw=2.4)
    bottom.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.6, zorder=1)
    bottom.set_ylabel("Pad voltage (V)", fontsize=12)
    bottom.set_xlabel("Time (ns)", fontsize=12)
    style(bottom)
    top.set_xlim(*active_window(t, [gup, gdn, pad], edge_ns, t_rev, tol=0.01))
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "presentation_2026-08-20" / "all_figures_flat")
    # The talk walks the stress cases twice: once before pad-matching is
    # introduced and once after. Two sets, identical apart from that one trace,
    # so the second pass reads as an addition rather than a different figure.
    parser.add_argument("--with-pad-match", action="store_true")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    ordered = []
    by_device = {}
    for device, direction, widths in stress_cases():
        by_device.setdefault(device, {})[direction] = widths
    for device in DEVICE_ORDER:
        for direction in ("short_high", "short_low"):
            for target, width_ps in by_device.get(device, {}).get(direction, []):
                ordered.append((device, direction, target, width_ps))

    manifest = []
    n = 0
    for device, direction, target, width_ps in ordered:
        tag = case_tag(device, direction, width_ps)
        hyb = MATRIX / "hybrid" / "waveforms" / f"{tag}.csv"
        if not hyb.exists():
            print(f"skip {tag}: no hybrid waveform")
            continue
        d = load(hyb)
        pm_path = MATRIX / "pad_match" / "waveforms" / f"{tag}.csv"
        pad_match = (load(pm_path) if (args.with_pad_match and pm_path.exists()) else None)
        edge_ns = 5.0 if direction == "short_high" else 10.0
        t_rev = edge_ns + width_ps / 1000.0
        label = f"{device} | {direction.replace('_', ' ')} | target {target}%"
        stem = f"{device}_{direction}_{target}pct"

        for kind in ("pad_voltage", "ku_kd", "gate_state"):
            n += 1
            name = f"{n:02d}_{stem}_{kind}.png"
            path = out / name
            if kind == "pad_voltage":
                pad_figure(path, label, d, edge_ns, t_rev, pad_match)
            elif kind == "ku_kd":
                kukd_figure(path, label, d, edge_ns, t_rev, pad_match)
            else:
                if not gate_figure(path, label, device, tag, edge_ns, t_rev, direction):
                    n -= 1
                    continue
            manifest.append({"order": n, "buffer": device, "direction": direction,
                             "target_percent": target, "pulse_width_ps": round(width_ps, 1),
                             "figure_type": kind, "filename": name})

    with (out / "figure_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)
    if args.with_pad_match:
        walkthrough(out)
    print(f"wrote {len(manifest)} figures to {out.relative_to(ROOT)}")
    return 0



def walkthrough(out: Path, device="io_buf", direction="short_high",
                target=80, width_ps=2090.0) -> None:
    """Follow one real reversal through the pad-matching lookup, step by step.

    Reads left to right: the reversal as it happens, the recorded opposite-edge
    trajectory the latched voltage is matched against, and the replay that
    results. The case is chosen so the pad is genuinely mid-transition when the
    input reverses -- on a buffer with a long propagation delay the pad has not
    moved yet, the latched voltage falls outside the trajectory, and the lookup
    has nothing to resolve.
    """
    import json

    ref_path = MATRIX / "pad_match" / "calibration" / device / "fast_5ps" / "pad_replay_reference.json"
    tag = case_tag(device, direction, width_ps)
    wave_path = MATRIX / "pad_match" / "waveforms" / f"{tag}.csv"
    if not (ref_path.exists() and wave_path.exists()):
        print("walkthrough: inputs missing")
        return
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    opp = "falling" if direction == "short_high" else "rising"
    opp_t = np.asarray(ref[opp]["time_ns"], dtype=float)
    opp_v = np.asarray(ref[opp]["pad_v"], dtype=float)
    moving = np.where(np.abs(opp_v - opp_v[-1]) > 0.02)[0]
    keep = opp_t <= (opp_t[moving[-1]] + 0.4 if len(moving) else opp_t[-1])
    opp_t, opp_v = opp_t[keep], opp_v[keep]

    d = load(wave_path)
    t = d["time_ns"]
    edge_ns = 5.0 if direction == "short_high" else 10.0
    t_rev = edge_ns + width_ps / 1000.0
    v_latched = float(np.interp(t_rev, t, d["pybis_pad"]))
    cross = np.where(np.diff(np.sign(opp_v - v_latched)) != 0)[0]
    t0 = float(opp_t[cross[0]]) if len(cross) else float("nan")

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.6))
    STEP = "#7B2CBF"

    # -- 1 -- the reversal, as it happens
    ax = axes[0]
    lo, hi = active_window(t, [d["silicon_pad"], d["pybis_pad"]], edge_ns, t_rev)
    ax.plot(t, d["silicon_pad"], color=TRANSISTOR, lw=4.2, label="HSPICE transistor")
    ax.plot(t, d["pybis_pad"], color=PADMATCH, lw=2.2, label="pad-matched replay")
    ax.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8)
    ax.axhline(v_latched, color=STEP, lw=1.2, alpha=0.7)
    ax.plot([t_rev], [v_latched], "o", color=STEP, ms=12, zorder=6)
    ax.annotate(f"input reverses here\npad = {v_latched:.3f} V", (t_rev, v_latched),
                textcoords="offset points", xytext=(-125, -70), fontsize=11,
                fontweight="bold", color=STEP,
                bbox=dict(fc="white", ec=STEP, alpha=0.95, pad=5),
                arrowprops=dict(arrowstyle="->", color=STEP, lw=1.6))
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Time (ns)", fontsize=11)
    ax.set_ylabel("Pad voltage (V)", fontsize=11)
    style(ax, "① the reversal")
    ax.legend(fontsize=10, loc="upper left")

    # -- 2 -- match that voltage on the recorded opposite edge
    ax = axes[1]
    ax.plot(opp_t, opp_v, color=GDN_C if direction == "short_high" else GUP_C, lw=3.0,
            label=f"recorded {opp} edge")
    ax.axhline(v_latched, color=STEP, ls="-.", lw=2.0)
    if np.isfinite(t0):
        ax.axvline(t0, color=STEP, ls="--", lw=1.6)
        ax.plot([t0], [v_latched], "o", color=STEP, ms=12, zorder=6)
        ax.annotate(f"same voltage occurs\nat t₀ = {t0:.3f} ns", (t0, v_latched),
                    textcoords="offset points", xytext=(40, 40), fontsize=11,
                    fontweight="bold", color=STEP,
                    bbox=dict(fc="white", ec=STEP, alpha=0.95, pad=5),
                    arrowprops=dict(arrowstyle="->", color=STEP, lw=1.6))
    ax.set_xlabel("time along the recorded edge (ns)", fontsize=11)
    ax.set_ylabel("Pad voltage (V)", fontsize=11)
    style(ax, "② match the latched voltage")
    ax.legend(fontsize=10, loc="upper right")

    # -- 3 -- resume both coefficients from there
    ax = axes[2]
    ax.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
    ax.plot(t, d["pybis_ku"], color=GUP_C, lw=2.4, label="Ku (replayed)")
    ax.plot(t, d["pybis_kd"], color=GDN_C, lw=2.4, label="Kd (replayed)")
    ax.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8)
    ax.axvspan(t_rev, min(t_rev + 2.0, hi), color=STEP, alpha=0.09, zorder=0)
    ax.annotate(f"both coefficients resume\nthe {opp} tables from t₀",
                (t_rev, 0.5), textcoords="offset points", xytext=(26, 46), fontsize=11,
                fontweight="bold", color=STEP,
                bbox=dict(fc="white", ec=STEP, alpha=0.95, pad=5),
                arrowprops=dict(arrowstyle="->", color=STEP, lw=1.6))
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Time (ns)", fontsize=11)
    ax.set_ylabel("coefficient", fontsize=11)
    style(ax, "③ replay from t₀")
    ax.legend(fontsize=10, loc="upper right")

    fig.suptitle(f"Pad-matched replay, one real reversal   ·   {device} "
                 f"{direction.replace('_', ' ')} {target}%",
                 fontsize=17, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    path = out / "00_pad_matching_walkthrough.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT)}")

if __name__ == "__main__":
    raise SystemExit(main())
