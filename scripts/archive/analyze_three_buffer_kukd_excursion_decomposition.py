#!/usr/bin/env python3
"""Decompose native and generated Ku/Kd excursions using cached waveforms only."""

from __future__ import annotations

import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
sys.path.insert(0, str(ROOT / "scripts"))

import matplotlib.pyplot as plt
import numpy as np

from eye_diagram import parse_ngspice_raw


COMMON = ROOT / "results" / "three_buffer_common_pulse_sweep_edge50ps_2026-07-30"
SLOW = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
OUT = ROOT / "results" / "three_buffer_kukd_excursion_decomposition_2026-08-04"
DEVICES = ("io_buf", "inv_chain", "ex2")
FLOWS = ("hspice_native_ibis", "gate_state", "hybrid")
COLORS = {
    "hspice_native_ibis": "#111111",
    "gate_state": "#0072B2",
    "hybrid": "#CC3311",
    "legacy": "#777777",
}


def read_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"No rows in {path}")
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def raw_signal(raw: dict[str, np.ndarray], name: str) -> np.ndarray:
    lookup = {key.lower().replace(":", "."): key for key in raw}
    key = lookup.get(name.lower().replace(":", "."))
    if key is None:
        raise KeyError(f"Missing {name}")
    return np.asarray(raw[key], dtype=float)


def waveform(device: str, case: str = "short_high_1ns") -> dict[str, np.ndarray]:
    return read_csv(COMMON / "runs" / device / "waveform_data" / f"{case}.csv")


def raw_path(device: str, flow: str, case: str = "short_high_1ns") -> Path:
    return (
        COMMON
        / "runs"
        / device
        / "edge_50ps"
        / "fast_5ps"
        / "cases"
        / case
        / f"ngspice_{flow}"
        / "run.raw"
    )


def flow_keys(flow: str, quantity: str) -> str:
    if flow == "hspice_native_ibis":
        return f"hspice_ibis_{quantity.lower()}"
    return f"{flow}_{quantity.lower()}"


def build_range_summary() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cases = ("edge_50ps_long_control", "short_high_500ps", "short_high_1ns", "short_high_2ns", "short_low_1ns")
    for device in DEVICES:
        for case in cases:
            data = waveform(device, case)
            for flow in FLOWS:
                for quantity in ("Ku", "Kd"):
                    values = data[flow_keys(flow, quantity)]
                    finite = values[np.isfinite(values)]
                    rows.append(
                        {
                            "device": device,
                            "case_id": case,
                            "flow": flow,
                            "quantity": quantity,
                            "minimum": float(np.min(finite)),
                            "maximum": float(np.max(finite)),
                            "undershoot_below_0": max(0.0, -float(np.min(finite))),
                            "overshoot_above_1": max(0.0, float(np.max(finite)) - 1.0),
                            "outside_0_1_fraction": float(np.mean((finite < 0.0) | (finite > 1.0))),
                        }
                    )
    return rows


def plot_range_summary(rows: list[dict[str, object]]) -> None:
    selected = [row for row in rows if row["case_id"] == "short_high_1ns"]
    fig, axes = plt.subplots(2, 3, figsize=(17.0, 8.4), sharey="row", constrained_layout=True)
    x = np.arange(len(FLOWS), dtype=float)
    labels = ("native IBIS", "gate state", "hybrid")
    for col, device in enumerate(DEVICES):
        for row_index, quantity in enumerate(("Ku", "Kd")):
            ax = axes[row_index, col]
            values = [next(row for row in selected if row["device"] == device and row["flow"] == flow and row["quantity"] == quantity) for flow in FLOWS]
            mins = np.asarray([float(row["minimum"]) for row in values])
            maxs = np.asarray([float(row["maximum"]) for row in values])
            ax.axhspan(0.0, 1.0, color="#E8F5E9", alpha=0.65)
            ax.vlines(x, mins, maxs, color=[COLORS[flow] for flow in FLOWS], linewidth=5)
            ax.scatter(x, mins, color=[COLORS[flow] for flow in FLOWS], marker="v", s=55, zorder=3)
            ax.scatter(x, maxs, color=[COLORS[flow] for flow in FLOWS], marker="^", s=55, zorder=3)
            for index, (minimum, maximum) in enumerate(zip(mins, maxs)):
                ax.text(index, maximum, f" {maximum:.3f}", ha="center", va="bottom", fontsize=9)
                ax.text(index, minimum, f" {minimum:.3f}", ha="center", va="top", fontsize=9)
            ax.axhline(0.0, color="#777777", linewidth=0.8)
            ax.axhline(1.0, color="#777777", linewidth=0.8, linestyle=":")
            ax.set_xticks(x, labels, rotation=18, ha="right")
            ax.grid(True, axis="y", alpha=0.22)
            ax.set_title(f"{device} | {quantity}", loc="left", fontweight="bold")
            if col == 0:
                ax.set_ylabel("coefficient range")
    fig.suptitle("Ku/Kd range during the common 1 ns short-high pulse", fontsize=17, fontweight="bold")
    fig.savefig(OUT / "plots" / "01_three_buffer_short_high_1ns_ranges.png", dpi=190)
    plt.close(fig)


def event_decomposition() -> list[dict[str, object]]:
    raw = parse_ngspice_raw(raw_path("io_buf", "hybrid"))
    t = raw_signal(raw, "time") * 1e9
    names = {
        "kd": "v(xdrv.kd)",
        "kdgate": "v(xdrv.kdgate)",
        "kdleg": "v(xdrv.kdleg)",
        "kdres": "v(xdrv.kdres)",
        "gdn": "v(xdrv.gdn)",
        "gdntarget": "v(xdrv.gdntarget)",
        "gdnrate": "v(xdrv.gdnrate)",
        "active": "v(xdrv.hhybridactive)",
        "ku": "v(xdrv.ku)",
        "kugate": "v(xdrv.kugate)",
        "kures": "v(xdrv.kures)",
    }
    values = {name: raw_signal(raw, source) for name, source in names.items()}
    values["kdgate_base"] = values["kdgate"] - values["kdres"]
    values["kugate_base"] = values["kugate"] - values["kures"]
    step = np.diff(values["kd"], prepend=values["kd"][0])
    event = (t >= 5.85) & (t <= 6.30)
    indices = np.where(event)[0]
    selected = indices[np.argsort(np.abs(step[indices]))[-24:]]
    selected = np.unique(np.concatenate((selected, np.array([np.argmin(values["kd"])]))))
    selected.sort()
    rows: list[dict[str, object]] = []
    for index in selected:
        row: dict[str, object] = {"time_ns": float(t[index]), "kd_step": float(step[index])}
        row.update({name: float(array[index]) for name, array in values.items()})
        rows.append(row)
    return rows


def plot_event_decomposition() -> dict[str, float]:
    raw = parse_ngspice_raw(raw_path("io_buf", "hybrid"))
    t = raw_signal(raw, "time") * 1e9
    kd = raw_signal(raw, "v(xdrv.kd)")
    kdgate = raw_signal(raw, "v(xdrv.kdgate)")
    kdleg = raw_signal(raw, "v(xdrv.kdleg)")
    kdres = raw_signal(raw, "v(xdrv.kdres)")
    kdgate_base = kdgate - kdres
    gdn = raw_signal(raw, "v(xdrv.gdn)")
    gdntarget = raw_signal(raw, "v(xdrv.gdntarget)")
    gdnrate = raw_signal(raw, "v(xdrv.gdnrate)")
    active = raw_signal(raw, "v(xdrv.hhybridactive)")
    wave = waveform("io_buf")
    native_kd = np.interp(t, wave["time_ns"], wave["hspice_ibis_kd"])
    gate_kd = np.interp(t, wave["time_ns"], wave["gate_state_kd"])
    step = np.diff(kd, prepend=kd[0])
    worst_index = int(np.argmax(np.abs(step[(t >= 5.8) & (t <= 6.3)])))
    window_indices = np.where((t >= 5.8) & (t <= 6.3))[0]
    worst_index = int(window_indices[worst_index])

    mask = (t >= 5.75) & (t <= 6.45)
    fig, axes = plt.subplots(4, 1, figsize=(14.5, 12.2), sharex=True, constrained_layout=True)
    axes[0].plot(t[mask], native_kd[mask], color="#111111", lw=3.0, label="HSPICE native IBIS Kd")
    axes[0].plot(t[mask], gate_kd[mask], color="#0072B2", lw=2.2, label="gate-state Kd")
    axes[0].plot(t[mask], kd[mask], color="#CC3311", lw=2.2, label="hybrid Kd")
    axes[0].axhline(0.0, color="#777777", lw=0.8)
    axes[0].set_ylabel("Kd")
    axes[0].legend(frameon=False, ncol=3)

    axes[1].plot(t[mask], kdgate_base[mask], color="#0072B2", lw=2.2, label="directional base map")
    axes[1].plot(t[mask], kdres[mask], color="#E69F00", lw=2.2, label="rate residual")
    axes[1].plot(t[mask], kdgate[mask], color="#CC3311", lw=2.5, label="base + residual")
    axes[1].plot(t[mask], kdleg[mask], color="#777777", lw=1.8, label="legacy Kd")
    axes[1].axhline(0.0, color="#777777", lw=0.8)
    axes[1].set_ylabel("Kd terms")
    axes[1].legend(frameon=False, ncol=4)

    axes[2].plot(t[mask], gdn[mask], color="#009E73", lw=2.5, label="GDN")
    axes[2].plot(t[mask], gdntarget[mask], color="#56B4E9", lw=2.0, label="GDN target")
    axes[2].plot(t[mask], gdnrate[mask], color="#7B2CBF", lw=1.8, label="dGDN/dt diagnostic")
    axes[2].plot(t[mask], active[mask], color="#CC3311", lw=1.6, label="hybrid active")
    axes[2].set_ylabel("state / flag")
    axes[2].legend(frameon=False, ncol=4)

    axes[3].plot(t[mask], step[mask], color="#CC3311", lw=1.8, label="Kd sample-to-sample change")
    axes[3].axhline(0.0, color="#777777", lw=0.8)
    axes[3].set_ylabel("Delta Kd")
    axes[3].set_xlabel("time (ns)")
    for ax in axes:
        ax.axvline(6.0, color="#555555", lw=1.2, ls="--")
        ax.axvline(t[worst_index], color="#CC3311", lw=1.0, ls=":")
        ax.grid(True, alpha=0.22)
    axes[0].set_title("io_buf hybrid Kd excursion decomposition | 1 ns short-high", loc="left", fontweight="bold")
    fig.savefig(OUT / "plots" / "02_io_buf_hybrid_kd_excursion_decomposition.png", dpi=190)
    plt.close(fig)

    return {
        "worst_step_time_ns": float(t[worst_index]),
        "worst_kd_step": float(step[worst_index]),
        "hybrid_kd_at_worst_step": float(kd[worst_index]),
        "native_kd_at_worst_step": float(native_kd[worst_index]),
        "gate_state_kd_at_worst_step": float(gate_kd[worst_index]),
        "directional_base_at_worst_step": float(kdgate_base[worst_index]),
        "rate_residual_at_worst_step": float(kdres[worst_index]),
        "gdn_at_worst_step": float(gdn[worst_index]),
        "gdn_target_at_worst_step": float(gdntarget[worst_index]),
    }


def slow_fast_summary() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    common = read_csv(COMMON / "runs" / "io_buf" / "waveform_data" / "edge_50ps_long_control.csv")
    for flow, prefix in (("native_fast", "hspice_ibis"), ("gate_fast", "gate_state"), ("hybrid_fast", "hybrid")):
        rows.append({
            "profile": "io_buf_fast_5ps",
            "flow": flow,
            "ku_min": float(np.min(common[f"{prefix}_ku"])),
            "ku_max": float(np.max(common[f"{prefix}_ku"])),
            "kd_min": float(np.min(common[f"{prefix}_kd"])),
            "kd_max": float(np.max(common[f"{prefix}_kd"])),
        })
    metrics_path = SLOW / "candidate_metrics.csv"
    with metrics_path.open(newline="", encoding="utf-8") as handle:
        metrics = list(csv.DictReader(handle))
    wanted = {
        "hspice_native_ibis": "native_slow",
        "ngspice_legacy": "legacy_slow",
        "ngspice_two_state_directional_residual": "directional_residual_slow",
    }
    for source, label in wanted.items():
        row = next(item for item in metrics if item["case_id"] == "edge_1ps_base_50r_2pf" and item["flow"] == source)
        rows.append({
            "profile": "io_buf_slow_1ns",
            "flow": label,
            "ku_min": float(row["ku_min"]),
            "ku_max": float(row["ku_peak"]),
            "kd_min": float(row["kd_min"]),
            "kd_max": float(row["kd_max"]),
        })
    return rows


def main() -> None:
    (OUT / "plots").mkdir(parents=True, exist_ok=True)
    ranges = build_range_summary()
    write_csv(OUT / "coefficient_ranges_by_case.csv", ranges)
    plot_range_summary(ranges)
    event_rows = event_decomposition()
    write_csv(OUT / "io_buf_hybrid_event_samples.csv", event_rows)
    event_summary = plot_event_decomposition()
    write_csv(OUT / "io_buf_hybrid_excursion_summary.csv", [event_summary])
    write_csv(OUT / "io_buf_slow_fast_excursion_comparison.csv", slow_fast_summary())

    (OUT / "README.md").write_text(
        f"""# Three-Buffer Ku/Kd Excursion Decomposition

This report uses cached CSV/raw data only. No HSPICE or ngspice simulation was run.

## Findings

1. **Some excursion is native behavior.** HSPICE native-IBIS `Ku/Kd` can leave `[0,1]`, especially for the fast `io_buf` file. These coefficients are fitted current multipliers, not literal transistor gate voltages.
2. **The severity is model dependent.** `inv_chain` stays close to `[0,1]`; `ex2` is moderate; fast `io_buf` is extreme. The old slow `io_buf` IBIS remains close to the nominal interval, so the problem is not universal to pybis.
3. **The hybrid adds an extra artifact.** In `io_buf short_high_1ns`, the largest one-step Kd change is `{event_summary['worst_kd_step']:.3f}` at `{event_summary['worst_step_time_ns']:.3f} ns`. At that instant, hybrid Kd is `{event_summary['hybrid_kd_at_worst_step']:.3f}`, while native IBIS is `{event_summary['native_kd_at_worst_step']:.3f}` and the full gate-state flow is `{event_summary['gate_state_kd_at_worst_step']:.3f}`.
4. **Why it happens.** The directional base map contributes `{event_summary['directional_base_at_worst_step']:.3f}` and the signed rate residual contributes `{event_summary['rate_residual_at_worst_step']:.3f}`. They are keyed by different progress variables during retrigger, then summed. The hybrid switch exposes that inconsistent sum as a discontinuity.
5. **Practical rule.** Do not clip all Ku/Kd to `[0,1]`; that would erase legitimate native excursions. Instead, compare against the native-IBIS envelope and separately reject generated excursions caused by a large discontinuity or by terms whose progress states are inconsistent.

## Files

- `plots/01_three_buffer_short_high_1ns_ranges.png`
- `plots/02_io_buf_hybrid_kd_excursion_decomposition.png`
- `coefficient_ranges_by_case.csv`
- `io_buf_hybrid_event_samples.csv`
- `io_buf_hybrid_excursion_summary.csv`
- `io_buf_slow_fast_excursion_comparison.csv`
""",
        encoding="utf-8",
    )
    print(OUT)


if __name__ == "__main__":
    main()
