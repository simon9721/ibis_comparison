from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0  # noqa: E402


SOURCE_STUDY = (
    ROOT / "results" / "io_buf_hspice_capacitance_driver_strength_2026-07-23"
)
OUT = (
    ROOT
    / "results"
    / "ibis_kukd_handwritten_notes_deck"
    / "hspice_slow_fast_transistor_comparison"
)
PLOTS = OUT / "plots"

SLOW_IBIS = ROOT / "sim" / "hspice" / "sparam" / "io_buf.ibs"
FAST_IBIS = (
    ROOT
    / "results"
    / "io_buf_fast_edge_retest_2026-06-05"
    / "source"
    / "io_buf.ibs"
)
TRANSISTOR = ROOT / "buffers" / "models" / "io_buf.sp"
TRANSISTOR_MODEL = ROOT.parent / "s2ibispy" / "tests" / "hspice.mod"

FLOW_ORDER = ["native_ibis", "native_ibis_fast", "transistor_original_ideal"]
FLOW_LABELS = {
    "native_ibis": "HSPICE IBIS: old slow-characterized file",
    "native_ibis_fast": "HSPICE IBIS: regenerated 5 ps file",
    "transistor_original_ideal": "HSPICE transistor: io_buf.sp",
}
COLORS = {
    "native_ibis": "#E67E22",
    "native_ibis_fast": "#008F83",
    "transistor_original_ideal": "#151515",
}
WIDTHS = {
    "native_ibis": 3.5,
    # A wide teal underlay keeps the fast IBIS visible beneath the nearly
    # identical black transistor trace.
    "native_ibis_fast": 6.0,
    "transistor_original_ideal": 3.0,
}

VDD = 3.3
R_LOAD_OHM = 50.0
C_LOAD_PF = 2.0
RISE_EDGE_NS = 5.0
FALL_EDGE_NS = 15.0


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_metrics() -> list[dict[str, str]]:
    with (SOURCE_STUDY / "metrics.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def flow_row(
    rows: list[dict[str, str]], flow: str, case_id: str = "c2pf_r50"
) -> dict[str, str]:
    for row in rows:
        if row["flow"] == flow and row["case_id"] == case_id:
            return row
    raise KeyError((flow, case_id))


def load_waveforms() -> dict[str, dict[str, np.ndarray]]:
    waveforms: dict[str, dict[str, np.ndarray]] = {}
    for flow in FLOW_ORDER:
        tr0 = SOURCE_STUDY / "runs" / "c2pf_r50" / flow / "run.tr0"
        parsed = parse_hspice_tr0(tr0)
        waveforms[flow] = {
            "time_ns": np.asarray(parsed["time"], dtype=float) * 1e9,
            "pad_v": np.asarray(parsed["v(pad)"], dtype=float),
            "input_v": np.asarray(parsed["v(in_dig)"], dtype=float),
        }
    return waveforms


def interp(
    waveform: dict[str, np.ndarray], grid_ns: np.ndarray, signal: str = "pad_v"
) -> np.ndarray:
    return np.interp(grid_ns, waveform["time_ns"], waveform[signal])


def style_axis(ax: plt.Axes) -> None:
    ax.grid(True, color="#D7D7D7", linewidth=0.8, alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=12)


def mark_command_edges(ax: plt.Axes, include_fall: bool = True) -> None:
    ax.axvline(RISE_EDGE_NS, color="#777777", linewidth=1.5, linestyle="--")
    if include_fall:
        ax.axvline(FALL_EDGE_NS, color="#777777", linewidth=1.5, linestyle="--")


def plot_pad_overlay(
    waveforms: dict[str, dict[str, np.ndarray]],
    filename: str,
    title: str,
    xlim: tuple[float, float],
    include_fall: bool,
    annotation: str | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=180)
    for flow in FLOW_ORDER:
        wave = waveforms[flow]
        ax.plot(
            wave["time_ns"],
            wave["pad_v"],
            color=COLORS[flow],
            linewidth=WIDTHS[flow],
            label=FLOW_LABELS[flow],
            zorder=4 if flow == "transistor_original_ideal" else 3,
        )
    mark_command_edges(ax, include_fall)
    ax.set_xlim(*xlim)
    ax.set_ylim(-0.08, 1.70)
    ax.set_xlabel("time (ns)", fontsize=14)
    ax.set_ylabel("pad voltage (V)", fontsize=14)
    ax.set_title(title, fontsize=18, fontweight="bold", loc="left")
    if annotation:
        ax.text(
            0.985,
            0.06,
            annotation,
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=12,
            color="#222222",
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": "white",
                "edgecolor": "#B5B5B5",
                "alpha": 0.94,
            },
        )
    style_axis(ax)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.02),
        frameon=True,
        fontsize=11,
        ncol=1,
    )
    fig.tight_layout()
    fig.savefig(PLOTS / filename, bbox_inches="tight")
    plt.close(fig)


def plot_timing_summary(rows: list[dict[str, str]]) -> None:
    transistor = flow_row(rows, "transistor_original_ideal")
    old = flow_row(rows, "native_ibis")
    fast = flow_row(rows, "native_ibis_fast")
    reference = {
        "rise": float(transistor["rise_50_delay_ns"]),
        "fall": float(transistor["fall_50_delay_ns"]),
    }
    values = {
        "Old slow-characterized IBIS": [
            1000.0 * (float(old["rise_50_delay_ns"]) - reference["rise"]),
            1000.0 * (float(old["fall_50_delay_ns"]) - reference["fall"]),
        ],
        "Regenerated 5 ps IBIS": [
            1000.0 * (float(fast["rise_50_delay_ns"]) - reference["rise"]),
            1000.0 * (float(fast["fall_50_delay_ns"]) - reference["fall"]),
        ],
    }

    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=180)
    x = np.arange(2)
    width = 0.32
    for index, (label, deltas) in enumerate(values.items()):
        color = COLORS["native_ibis"] if index == 0 else COLORS["native_ibis_fast"]
        bars = ax.bar(
            x + (index - 0.5) * width,
            deltas,
            width,
            label=label,
            color=color,
        )
        for bar, value in zip(bars, deltas, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 12,
                f"{value:.1f} ps",
                ha="center",
                va="bottom",
                fontsize=13,
                fontweight="bold",
                color=color,
            )
    ax.axhline(0, color="#222222", linewidth=1.2)
    ax.set_xticks(x, ["rise", "fall"], fontsize=14)
    ax.set_ylabel("50% timing error vs source transistor (ps)", fontsize=14)
    ax.set_title(
        "Regenerated IBIS removes the stored timing offset",
        fontsize=18,
        fontweight="bold",
        loc="left",
    )
    ax.set_ylim(-25, 700)
    style_axis(ax)
    ax.legend(loc="upper right", frameon=True, fontsize=12)
    fig.tight_layout()
    fig.savefig(PLOTS / "04_timing_error_vs_transistor.png", bbox_inches="tight")
    plt.close(fig)


def plot_driver_strength(rows: list[dict[str, str]]) -> None:
    load_values = [25.0, 50.0, 100.0, 200.0, 1000.0]
    markers = {
        "native_ibis": "^",
        "native_ibis_fast": "s",
        "transistor_original_ideal": "o",
    }
    sizes = {
        "native_ibis": 12,
        "native_ibis_fast": 9,
        "transistor_original_ideal": 6,
    }
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=180)
    for flow in FLOW_ORDER:
        selected = [
            row
            for row in rows
            if row["flow"] == flow
            and float(row["c_load_pf"]) == 2.0
            and float(row["r_load_ohm"]) in load_values
        ]
        selected.sort(key=lambda row: float(row["load_current_high_ma"]))
        current_ma = [float(row["load_current_high_ma"]) for row in selected]
        voltage_v = [float(row["v_high_v"]) for row in selected]
        ax.plot(
            current_ma,
            voltage_v,
            color=COLORS[flow],
            linewidth=2.8,
            marker=markers[flow],
            markersize=sizes[flow],
            markerfacecolor="white",
            markeredgewidth=2.2,
            label=FLOW_LABELS[flow],
        )
    base = flow_row(rows, "native_ibis_fast")
    transistor = flow_row(rows, "transistor_original_ideal")
    note = (
        "At 50 ohm:\n"
        f"IBIS: {float(base['v_high_v']):.4f} V, "
        f"Rout={float(base['effective_pullup_r_ohm']):.2f} ohm\n"
        f"transistor: {float(transistor['v_high_v']):.4f} V, "
        f"Rout={float(transistor['effective_pullup_r_ohm']):.2f} ohm"
    )
    ax.text(
        0.98,
        0.08,
        note,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=12,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": "white",
            "edgecolor": "#B5B5B5",
            "alpha": 0.94,
        },
    )
    ax.set_xlabel("settled load current (mA)", fontsize=14)
    ax.set_ylabel("settled high pad voltage (V)", fontsize=14)
    ax.set_title(
        "Slow and fast IBIS have the same static drive strength",
        fontsize=18,
        fontweight="bold",
        loc="left",
    )
    style_axis(ax)
    ax.legend(loc="upper right", frameon=True, fontsize=11)
    fig.tight_layout()
    fig.savefig(PLOTS / "05_pullup_drive_strength.png", bbox_inches="tight")
    plt.close(fig)


def plot_stored_vt_source() -> None:
    source_check = SOURCE_STUDY / "stored_vt_source_check.csv"
    with source_check.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    labels = [
        "Old IBIS\nstored V-T",
        "5 ps IBIS\nstored V-T",
        "Source transistor\n5 ps characterization",
    ]
    values = [
        float(row["old_ibis_vt_rise_50_ns"]),
        float(row["fast_ibis_vt_rise_50_ns"]),
        float(row["direct_transistor_vt_rise_50_ns"]),
    ]
    colors = [
        COLORS["native_ibis"],
        COLORS["native_ibis_fast"],
        COLORS["transistor_original_ideal"],
    ]
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=180)
    bars = ax.bar(labels, values, color=colors, width=0.58)
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.025,
            f"{value:.4f} ns",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
        )
    ax.set_ylabel("50% time from V-T waveform start (ns)", fontsize=14)
    ax.set_title(
        "The timing difference is already stored in the IBIS V-T table",
        fontsize=18,
        fontweight="bold",
        loc="left",
    )
    ax.set_ylim(0, 2.55)
    style_axis(ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "06_stored_vt_timing_source.png", bbox_inches="tight")
    plt.close(fig)


def write_numeric_outputs(
    rows: list[dict[str, str]], waveforms: dict[str, dict[str, np.ndarray]]
) -> None:
    transistor = flow_row(rows, "transistor_original_ideal")
    summary_fields = [
        "flow",
        "label",
        "rise_50_delay_ns",
        "rise_delta_vs_transistor_ps",
        "fall_50_delay_ns",
        "fall_delta_vs_transistor_ps",
        "settled_high_v",
        "load_current_high_ma",
        "effective_pullup_r_ohm",
        "active_window_rmse_vs_transistor_mv",
    ]
    grid_ns = np.arange(4.5, 18.5001, 0.001)
    aligned_pad = {
        flow: interp(waveforms[flow], grid_ns) for flow in FLOW_ORDER
    }
    aligned_input = interp(
        waveforms["transistor_original_ideal"], grid_ns, "input_v"
    )
    transistor_pad = aligned_pad["transistor_original_ideal"]
    summary_rows: list[dict[str, str | float]] = []
    for flow in FLOW_ORDER:
        row = flow_row(rows, flow)
        pad = interp(waveforms[flow], grid_ns)
        rmse_mv = 1000.0 * float(np.sqrt(np.mean((pad - transistor_pad) ** 2)))
        summary_rows.append(
            {
                "flow": flow,
                "label": FLOW_LABELS[flow],
                "rise_50_delay_ns": float(row["rise_50_delay_ns"]),
                "rise_delta_vs_transistor_ps": 1000.0
                * (
                    float(row["rise_50_delay_ns"])
                    - float(transistor["rise_50_delay_ns"])
                ),
                "fall_50_delay_ns": float(row["fall_50_delay_ns"]),
                "fall_delta_vs_transistor_ps": 1000.0
                * (
                    float(row["fall_50_delay_ns"])
                    - float(transistor["fall_50_delay_ns"])
                ),
                "settled_high_v": float(row["v_high_v"]),
                "load_current_high_ma": float(row["load_current_high_ma"]),
                "effective_pullup_r_ohm": float(row["effective_pullup_r_ohm"]),
                "active_window_rmse_vs_transistor_mv": rmse_mv,
            }
        )
    with (OUT / "comparison_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    aligned_fields = ["time_ns"] + [
        f"{flow}_pad_v" for flow in FLOW_ORDER
    ] + ["input_v"]
    with (OUT / "aligned_waveforms.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=aligned_fields)
        writer.writeheader()
        for index, time_ns in enumerate(grid_ns):
            output: dict[str, float] = {"time_ns": float(time_ns)}
            for flow in FLOW_ORDER:
                output[f"{flow}_pad_v"] = float(aligned_pad[flow][index])
            output["input_v"] = float(aligned_input[index])
            writer.writerow(output)

    strength_fields = [
        "flow",
        "label",
        "r_load_ohm",
        "settled_high_v",
        "load_current_high_ma",
        "effective_pullup_r_ohm",
    ]
    with (OUT / "driver_strength.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=strength_fields)
        writer.writeheader()
        for flow in FLOW_ORDER:
            selected = [
                row
                for row in rows
                if row["flow"] == flow
                and float(row["c_load_pf"]) == 2.0
                and float(row["r_load_ohm"]) in [25.0, 50.0, 100.0, 200.0, 1000.0]
            ]
            selected.sort(key=lambda row: float(row["r_load_ohm"]))
            for row in selected:
                writer.writerow(
                    {
                        "flow": flow,
                        "label": FLOW_LABELS[flow],
                        "r_load_ohm": float(row["r_load_ohm"]),
                        "settled_high_v": float(row["v_high_v"]),
                        "load_current_high_ma": float(row["load_current_high_ma"]),
                        "effective_pullup_r_ohm": float(
                            row["effective_pullup_r_ohm"]
                        ),
                    }
                )

    source_fields = ["role", "path", "sha256"]
    sources = [
        ("old_slow_characterized_ibis", SLOW_IBIS),
        ("regenerated_5ps_ibis", FAST_IBIS),
        ("source_transistor_netlist", TRANSISTOR),
        ("original_hspice_model_card", TRANSISTOR_MODEL),
    ]
    with (OUT / "source_manifest.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=source_fields)
        writer.writeheader()
        for role, path in sources:
            writer.writerow({"role": role, "path": path, "sha256": sha256(path)})


def write_readme(rows: list[dict[str, str]]) -> None:
    old = flow_row(rows, "native_ibis")
    fast = flow_row(rows, "native_ibis_fast")
    transistor = flow_row(rows, "transistor_original_ideal")
    old_rise_delta = 1000.0 * (
        float(old["rise_50_delay_ns"]) - float(transistor["rise_50_delay_ns"])
    )
    fast_rise_delta = 1000.0 * (
        float(fast["rise_50_delay_ns"]) - float(transistor["rise_50_delay_ns"])
    )
    old_fall_delta = 1000.0 * (
        float(old["fall_50_delay_ns"]) - float(transistor["fall_50_delay_ns"])
    )
    fast_fall_delta = 1000.0 * (
        float(fast["fall_50_delay_ns"]) - float(transistor["fall_50_delay_ns"])
    )
    content = f"""# HSPICE slow/fast IBIS versus source transistor

This is a cached-data-only figure package for the IBIS Ku/Kd meeting deck. No
simulation was rerun. All waveforms come from the same HSPICE study and the
same electrical bench.

## Compared models

- Old slow-characterized native IBIS: `{SLOW_IBIS}`.
- Regenerated 5 ps native IBIS: `{FAST_IBIS}`.
- Source transistor: `{TRANSISTOR}` with the original HSPICE model card
  `{TRANSISTOR_MODEL}`.

## Common test bench

- Simulator: HSPICE for all three flows.
- Supply and enable: ideal `3.3 V`.
- Input: `0 -> 3.3 V` at `5 ns`, held high until `15 ns`, then returned low.
- Runtime input rise/fall: `1 ps`.
- Termination: `50 ohm` to ground in parallel with `2 pF` external capacitance.
- IBIS internal capacitance: `C_comp = 1.2 pF` typical in both IBIS files.
- Temperature: `27 C`.
- No channel or transmission line is present in this direct-load comparison.

## Timing result

| Flow | Rise t50 | Error vs transistor | Fall t50 | Error vs transistor |
|---|---:|---:|---:|---:|
| Source transistor | {float(transistor['rise_50_delay_ns']):.4f} ns | reference | {float(transistor['fall_50_delay_ns']):.4f} ns | reference |
| Old slow IBIS | {float(old['rise_50_delay_ns']):.4f} ns | {old_rise_delta:+.1f} ps | {float(old['fall_50_delay_ns']):.4f} ns | {old_fall_delta:+.1f} ps |
| Regenerated 5 ps IBIS | {float(fast['rise_50_delay_ns']):.4f} ns | {fast_rise_delta:+.1f} ps | {float(fast['fall_50_delay_ns']):.4f} ns | {fast_fall_delta:+.1f} ps |

The fast IBIS follows the source transistor closely. The old model stores a
large timing offset in its V-T waveform tables; this is not a static
drive-strength difference.

## Drive strength

At the `50 ohm` loaded-high operating point:

| Flow | Settled high | Load current | Effective pullup resistance |
|---|---:|---:|---:|
| Old slow IBIS | {float(old['v_high_v']):.4f} V | {float(old['load_current_high_ma']):.3f} mA | {float(old['effective_pullup_r_ohm']):.2f} ohm |
| Regenerated 5 ps IBIS | {float(fast['v_high_v']):.4f} V | {float(fast['load_current_high_ma']):.3f} mA | {float(fast['effective_pullup_r_ohm']):.2f} ohm |
| Source transistor | {float(transistor['v_high_v']):.4f} V | {float(transistor['load_current_high_ma']):.3f} mA | {float(transistor['effective_pullup_r_ohm']):.2f} ohm |

The old and fast IBIS files have the same static I-V tables and therefore the
same static pullup strength. This bench quantifies pullup strength; it does not
independently extract a static pulldown resistance.

## Figures

- `plots/01_full_pulse_overlay.png`
- `plots/02_rising_edge_overlay.png`
- `plots/03_falling_edge_overlay.png`
- `plots/04_timing_error_vs_transistor.png`
- `plots/05_pullup_drive_strength.png`
- `plots/06_stored_vt_timing_source.png`
- `plots/contact_sheet.png`

## Numeric data

- `comparison_summary.csv`
- `aligned_waveforms.csv`
- `driver_strength.csv`
- `source_manifest.csv`
"""
    (OUT / "README.md").write_text(content, encoding="utf-8")


def make_contact_sheet() -> None:
    names = [
        "01_full_pulse_overlay.png",
        "02_rising_edge_overlay.png",
        "03_falling_edge_overlay.png",
        "04_timing_error_vs_transistor.png",
        "05_pullup_drive_strength.png",
        "06_stored_vt_timing_source.png",
    ]
    fig, axes = plt.subplots(3, 2, figsize=(16, 13.5), dpi=140)
    for ax, name in zip(axes.flat, names, strict=True):
        image = plt.imread(PLOTS / name)
        ax.imshow(image)
        ax.set_title(name.removesuffix(".png"), fontsize=12, loc="left")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(PLOTS / "contact_sheet.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    rows = read_metrics()
    waveforms = load_waveforms()
    plot_pad_overlay(
        waveforms,
        "01_full_pulse_overlay.png",
        "Same HSPICE bench: slow IBIS, fast IBIS, and source transistor",
        (4.5, 18.2),
        True,
    )
    plot_pad_overlay(
        waveforms,
        "02_rising_edge_overlay.png",
        "Rising edge: regenerated 5 ps IBIS follows the transistor",
        (4.8, 10.0),
        False,
        "50% error vs transistor:\nold IBIS +511.3 ps\n5 ps IBIS +9.0 ps",
    )
    plot_pad_overlay(
        waveforms,
        "03_falling_edge_overlay.png",
        "Falling edge: regenerated 5 ps IBIS follows the transistor",
        (14.8, 18.2),
        True,
        "50% error vs transistor:\nold IBIS +628.0 ps\n5 ps IBIS +3.9 ps",
    )
    plot_timing_summary(rows)
    plot_driver_strength(rows)
    plot_stored_vt_source()
    write_numeric_outputs(rows, waveforms)
    write_readme(rows)
    make_contact_sheet()
    print(OUT)


if __name__ == "__main__":
    main()
