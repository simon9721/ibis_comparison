#!/usr/bin/env python3
"""Split the three-buffer stress evidence into two separately-scoped studies.

The two references disagree about what a stressed short pulse even is, and they
disagree in opposite directions depending on the buffer. `inv_chain` and `ex2`
native IBIS over-responds, so a native-anchored width leaves the transistor at
0-20%. `io_buf` native IBIS under-responds, so the same procedure leaves the
transistor at 68-102%. No single axis stresses both references across all three
buffers, so one combined study cannot answer both questions without misleading
on one of them.

This builds the two studies separately.

Study A -- silicon accuracy. Transistor-anchored, so silicon is genuinely
stressed. Reports the total error against the transistor and splits it into the
part contributed by IBIS itself and the part contributed by pybis.

Study B -- algorithm fidelity. Native-IBIS-anchored, so the reference pybis is
graded against is genuinely stressed. Reports pybis against native IBIS only.

A full-edge baseline is included because it is what makes Study A's split
interpretable: on an uninterrupted edge native IBIS tracks the transistor
closely, so the stressed-case gap is a statement about interrupted transitions
rather than about the IBIS models being wrong in general.

Cached data only; no simulator is launched.
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
for path in (LOCAL_DEPS, ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_hspice_tr0  # noqa: E402

# Study A sources, searched in order. `io_buf`'s fast IBIS was regenerated at a
# 50 ps characterization edge on 2026-08-19, so any Study A case for that buffer
# produced before then describes a model built from the superseded 5 ps file.
# A refresh directory therefore takes precedence when it carries the case.
STUDY_A_SOURCES = (
    ROOT / "results" / "three_buffer_transistor_anchored_refresh_2026-08-19",
    ROOT / "results" / "three_buffer_loaded_swing_stress_sweep_hybrid_2026-08-18",
)
STALE_FAST_IBIS_DEVICES = ("io_buf",)
STUDY_B = ROOT / "results" / "three_buffer_native_anchored_stress_sweep_2026-08-19"
FULL_EDGE = ROOT / "results" / "three_buffer_loaded_swing_stress_sweep_2026-08-14" / "hspice_references"
DEFAULT_OUT = ROOT / "results" / "two_study_error_decomposition_2026-08-19"

DEVICES = ("io_buf", "inv_chain", "ex2")
DIRECTIONS = ("short_high", "short_low")
TARGETS = (90, 80, 70, 60, 50)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Writes rows whose columns may differ.

    Study A rows are assembled from more than one source study, and those do not
    all carry the same flows: a sweep run with only the gate-state model has no
    `hybrid_*` columns. Taking the header from the first row alone would reject
    any later row carrying extra fields.
    """
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)


def wave(path: Path) -> dict[str, np.ndarray]:
    rows = read_csv(path)
    if not rows:
        return {}
    out: dict[str, np.ndarray] = {}
    for key in rows[0]:
        values = []
        for row in rows:
            try:
                values.append(float(row[key]))
            except (TypeError, ValueError):
                values.append(np.nan)
        out[key] = np.asarray(values, dtype=float)
    return out


def rmse_mv(a: np.ndarray, b: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    if not ok.any():
        return float("nan")
    return float(np.sqrt(np.mean((a[ok] - b[ok]) ** 2))) * 1000.0


def full_edge_baseline() -> list[dict[str, object]]:
    """Native IBIS versus the transistor on a complete, uninterrupted edge."""
    rows: list[dict[str, object]] = []
    for device in DEVICES:
        native = FULL_EDGE / device / "fast_5ps" / "r50_c2pf" / "long_control" / "native" / "run.tr0"
        transistor = FULL_EDGE / device / "transistor" / "r50_c2pf" / "long_control" / "run.tr0"
        if not (native.exists() and transistor.exists()):
            continue
        nat, tra = parse_hspice_tr0(native), parse_hspice_tr0(transistor)
        tn = np.asarray(nat["time"]) * 1e9
        tt = np.asarray(tra["time"]) * 1e9
        pn = np.asarray(nat[next(k for k in nat if "pad" in k)])
        pt = np.asarray(tra[next(k for k in tra if "pad" in k)])
        grid = np.linspace(max(tn[0], tt[0]), min(tn[-1], tt[-1]), 6000)
        a, b = np.interp(grid, tn, pn), np.interp(grid, tt, pt)
        rows.append({
            "device": device,
            "native_vs_transistor_rmse_mv": round(rmse_mv(a, b), 2),
            "swing_ratio": round((a.max() - a.min()) / max(b.max() - b.min(), 1e-12), 4),
        })
    return rows


def study_a_rows() -> tuple[list[dict[str, object]], list[str]]:
    """Transistor-anchored: total silicon error, split into IBIS and pybis parts.

    Also returns any cases that could only be satisfied from a source predating
    the `io_buf` IBIS regeneration, so a stale model cannot be reported as
    current without saying so.
    """
    rows: list[dict[str, object]] = []
    stale: list[str] = []
    for device in DEVICES:
        # Once a device has been refreshed, a case missing from the refresh is
        # reported as missing rather than back-filled from the superseded model.
        # Mixing the two would put a number from a broken file beside numbers
        # from a working one, in the same column, with no visible difference.
        refreshed = (
            device in STALE_FAST_IBIS_DEVICES
            and (STUDY_A_SOURCES[0] / "figures" / device).is_dir()
        )
        sources = STUDY_A_SOURCES[:1] if refreshed else STUDY_A_SOURCES
        for direction in DIRECTIONS:
            for target in TARGETS:
                data: dict[str, np.ndarray] = {}
                source_index = None
                for index, source in enumerate(sources):
                    data = wave(source / "figures" / device / direction / f"swing_{target}" / "waveforms.csv")
                    if data:
                        source_index = index
                        break
                if not data:
                    if refreshed:
                        stale.append(f"{device}/{direction}/{target}%")
                    continue
                if source_index and device in STALE_FAST_IBIS_DEVICES:
                    stale.append(f"{device}/{direction}/{target}%")
                transistor = data["hspice_transistor_pad_v"]
                native = data["hspice_native_pad_v"]
                entry: dict[str, object] = {
                    "device": device,
                    "direction": direction,
                    "transistor_swing_target_percent": target,
                    "ibis_format_gap_mv": round(rmse_mv(native, transistor), 1),
                }
                for flow, column in (("gate_state", "gate_state_pad_v"), ("hybrid", "hybrid_pad_v")):
                    if column not in data:
                        continue
                    entry[f"{flow}_pybis_gap_mv"] = round(rmse_mv(data[column], native), 1)
                    entry[f"{flow}_total_vs_silicon_mv"] = round(rmse_mv(data[column], transistor), 1)
                entry["source"] = STUDY_A_SOURCES[source_index].name
                rows.append(entry)
    return rows, stale


def study_b_rows() -> list[dict[str, object]]:
    """Native-anchored: pybis against the reference it is meant to reproduce."""
    rows: list[dict[str, object]] = []
    selection = {
        (r["device"], r["direction"], str(int(float(r["target_percent"])))): r
        for r in read_csv(STUDY_B / "selection.csv")
    }
    for device in DEVICES:
        for direction in DIRECTIONS:
            for target in TARGETS:
                data = wave(STUDY_B / "figures" / device / direction / f"swing_{target}" / "waveforms.csv")
                if not data:
                    continue
                chosen = selection.get((device, direction, str(target)))
                if chosen is None:
                    # No selection row means the case did not complete. Waveform
                    # files can still be present from an earlier attempt, and
                    # reporting them would present a failed case as a result.
                    continue
                native = data["hspice_native_pad_v"]
                rows.append({
                    "device": device,
                    "direction": direction,
                    "native_swing_target_percent": target,
                    "native_achieved_percent": round(float(chosen.get("native_achieved_percent", "nan")), 1),
                    "transistor_swing_percent": round(float(chosen.get("transistor_achieved_percent", "nan")), 1),
                    "pulse_width_ps": round(float(chosen.get("pulse_width_ps", "nan")), 1),
                    "gate_state_pad_rmse_mv": round(rmse_mv(data["gate_state_pad_v"], native), 1),
                    "gate_state_ku_rmse": round(float(np.sqrt(np.nanmean(
                        (data["gate_state_ku"] - data["hspice_native_ku"]) ** 2))), 4),
                    "gate_state_kd_rmse": round(float(np.sqrt(np.nanmean(
                        (data["gate_state_kd"] - data["hspice_native_kd"]) ** 2))), 4),
                    "target_reachable": chosen.get("target_reachable", ""),
                })
    return rows


def plot_decomposition(path: Path, rows: list[dict[str, object]]) -> None:
    """Study A's two error contributions beside the total they produce.

    Deliberately grouped rather than stacked. The two gaps are RMSEs of signed
    errors that can point in opposite directions, so they do not add: on
    `inv_chain` short-high the total against silicon is smaller than either
    contribution because pybis error partly cancels IBIS error. A stacked bar
    would assert an additivity the data does not have.
    """
    usable = [r for r in rows if "gate_state_total_vs_silicon_mv" in r]
    if not usable:
        return
    labels = [f"{r['device']}\n{r['direction'].replace('short_', '')} {r['transistor_swing_target_percent']}%"
              for r in usable]
    ibis = np.array([float(r["ibis_format_gap_mv"]) for r in usable])
    pybis = np.array([float(r["gate_state_pybis_gap_mv"]) for r in usable])
    total = np.array([float(r["gate_state_total_vs_silicon_mv"]) for r in usable])
    x = np.arange(len(usable))
    width = 0.27
    fig, ax = plt.subplots(figsize=(max(12.0, 0.46 * len(usable)), 5.6))
    ax.bar(x - width, ibis, width, label="IBIS format gap (native IBIS vs transistor)", color="#b3541e")
    ax.bar(x, pybis, width, label="pybis gap (gate-state vs native IBIS)", color="#2b6ca3")
    ax.bar(x + width, total, width, label="total vs silicon (gate-state vs transistor)", color="#6b6b6b")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.5, rotation=90)
    ax.set_ylabel("Pad RMSE (mV)")
    ax.set_title("Study A: contributions to the error against silicon (transistor-anchored)")
    ax.legend(loc="upper left", fontsize=8.5)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_stress_axes(path: Path, rows: list[dict[str, object]]) -> None:
    """How far apart the two references are once a native-anchored width is set.

    The disagreement is not one-directional. `inv_chain` and `ex2` native IBIS
    over-responds, so a native-anchored width is short and the transistor barely
    moves. `io_buf` native IBIS under-responds, so the width is long and the
    transistor is fully swung. Only where a buffer's points fall inside the
    shaded band are both references meaningfully stressed at once.
    """
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    ax.fill_between([20, 100], [20, 20], [100, 100], color="#cfe3c8", alpha=0.45,
                    label="both references stressed (20-100%)", zorder=0)
    for device, colour in zip(DEVICES, ("#2b6ca3", "#b3541e", "#3c8d3c")):
        subset = [r for r in rows if r["device"] == device and np.isfinite(float(r["transistor_swing_percent"]))]
        if not subset:
            continue
        ax.scatter(
            [float(r["native_achieved_percent"]) for r in subset],
            [float(r["transistor_swing_percent"]) for r in subset],
            label=device, color=colour, s=46, zorder=3,
        )
    ax.plot([0, 105], [0, 105], "--", color="0.45", lw=1, label="references agree", zorder=2)
    ax.set_xlabel("native IBIS swing at the chosen pulse width (%)")
    ax.set_ylabel("transistor swing at the same width (%)")
    ax.set_title("Where the two references disagree, and by how much")
    ax.set_xlim(0, 105)
    ax.set_ylim(-5, 110)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=8.5, framealpha=0.92)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_readme(out: Path, baseline, a_rows, b_rows, stale) -> None:
    def mean_of(rows, key):
        values = [float(r[key]) for r in rows if key in r and np.isfinite(float(r[key]))]
        return float(np.mean(values)) if values else float("nan")

    lines = [
        "# Three-buffer stress evidence, split into two studies",
        "",
        "The two references disagree about what a stressed short pulse is, and they",
        "disagree in opposite directions depending on the buffer:",
        "",
        "- `inv_chain` and `ex2` native IBIS **over-responds**. A native-anchored width",
        "  is short, and at that width the transistor has moved 0-20%.",
        "- `io_buf` native IBIS **under-responds**. A native-anchored width is long, and",
        "  at that width the transistor is at 68-102%.",
        "",
        "So there is no single axis that stresses both references across all three",
        "buffers, and the evidence is split by question rather than forced onto one.",
        "The one place they do overlap usefully is `io_buf` short-high, where a",
        "native-anchored sweep leaves the transistor at 68-98% -- both references are",
        "meaningfully stressed and that column of Study B is also a silicon result.",
        "",
        "Never compare a target percentage across the two studies: the same nominal",
        "figure is a different pulse width in each.",
        "",
        "## Full-edge baseline",
        "",
        "On a complete, uninterrupted edge native IBIS tracks the transistor closely.",
        "This is what makes Study A's split meaningful -- the stressed-case gap is a",
        "statement about interrupted transitions, not about the IBIS models being poor",
        "in general.",
        "",
        "| device | native IBIS vs transistor | swing ratio |",
        "| ------ | ------------------------: | ----------: |",
    ]
    for row in baseline:
        lines.append(
            f"| `{row['device']}` | {row['native_vs_transistor_rmse_mv']} mV | "
            f"{row['swing_ratio']} |"
        )
    lines += [
        "",
        "## Study A -- silicon accuracy",
        "",
        "**Question:** does the flow predict silicon?  ",
        "**Anchor:** HSPICE transistor, so silicon is genuinely stressed.  ",
        "**Reference:** HSPICE transistor.",
        "",
        "The total error is split into the part IBIS contributes and the part pybis",
        "contributes:",
        "",
        "```text",
        "transistor --[IBIS format gap]-- native IBIS --[pybis gap]-- pybis",
        "```",
        "",
        f"Across {len(a_rows)} cases, mean IBIS format gap is "
        f"**{mean_of(a_rows, 'ibis_format_gap_mv'):.0f} mV** and mean pybis gap is "
        f"**{mean_of(a_rows, 'gate_state_pybis_gap_mv'):.0f} mV**. Where the first",
        "dominates, no amount of pybis work can close the remaining distance.",
        "",
        "**The two gaps do not add.** They are RMSEs of signed errors that can point",
        "in opposite directions. On `inv_chain` short-high the total against silicon is",
        "*smaller* than either contribution, because pybis error partly cancels IBIS",
        "error -- the model is closer to silicon than the reference it was fitted to,",
        "by luck rather than by merit. The figure groups the three quantities rather",
        "than stacking them for exactly this reason.",
        "",
        "Data: [study_a_silicon_accuracy.csv](./study_a_silicon_accuracy.csv)  ",
        "Figure: [plots/01_study_a_error_decomposition.png](./plots/01_study_a_error_decomposition.png)",
        "",
    ]
    if stale:
        lines += [
            f"> **{len(stale)} case(s) are absent.** `io_buf`'s fast IBIS was regenerated at",
            "> a 50 ps characterization edge on 2026-08-19. These cases did not complete in",
            "> the refreshed sweep -- the gate-state model hit an ngspice timestep collapse",
            "> -- and are reported as missing rather than back-filled from the superseded",
            "> 5 ps file, whose fitted endpoints and delays are invalid. A pre-regeneration",
            "> number placed in this column would not be comparable with the rest of it.",
            "",
            "> Affected: " + ", ".join(f"`{case}`" for case in stale),
            "",
        ]
    lines += [
        "## Study B -- algorithm fidelity",
        "",
        "**Question:** does pybis reproduce the IBIS algorithm in ngspice?  ",
        "**Anchor:** HSPICE native IBIS, so the graded reference is genuinely stressed.  ",
        "**Reference:** HSPICE native IBIS.",
        "",
        "This is the question pybis can actually be held to: it converts an `.ibs` file",
        "into an ngspice subcircuit and owns nothing upstream of that. It says nothing",
        "about silicon accuracy -- the transistor is nearly static in these cases, as",
        "the `transistor_swing_percent` column records.",
        "",
        "Data: [study_b_algorithm_fidelity.csv](./study_b_algorithm_fidelity.csv)  ",
        "Figure: [plots/02_reference_disagreement.png](./plots/02_reference_disagreement.png)",
        "",
        "## Regenerating",
        "",
        "```powershell",
        "py -3.14 scripts/build_two_study_error_decomposition.py",
        "```",
        "",
        "Cached data only; no simulator is launched.",
    ]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    out = DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    baseline = full_edge_baseline()
    a_rows, stale = study_a_rows()
    b_rows = study_b_rows()
    if stale:
        print(f"WARNING: {len(stale)} Study A case(s) are missing or not comparable with")
        print("         the current io_buf fast IBIS:")
        for case in stale:
            print(f"           {case}")
    write_csv(out / "full_edge_baseline.csv", baseline)
    write_csv(out / "study_a_silicon_accuracy.csv", a_rows)
    write_csv(out / "study_b_algorithm_fidelity.csv", b_rows)
    plot_decomposition(out / "plots" / "01_study_a_error_decomposition.png", a_rows)
    plot_stress_axes(out / "plots" / "02_reference_disagreement.png", b_rows)
    write_readme(out, baseline, a_rows, b_rows, stale)
    print(f"full-edge baseline rows : {len(baseline)}")
    print(f"study A cases           : {len(a_rows)}")
    print(f"study B cases           : {len(b_rows)}")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

