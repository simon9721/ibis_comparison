#!/usr/bin/env python3
"""Build a complete causal view of the io_buf short-high offset.

The figure follows one event through the model:

    input -> command capacitor -> gate state -> Ku/Kd -> pad

HSPICE native IBIS is shown for Ku, Kd and pad. The HSPICE transistor pad is
shown directly, while transistor Ku/Kd are derived from two cached fixture
runs on the corrected uniform 5 ps solve grid.
"""
from __future__ import annotations

import csv
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
for path in (
    ROOT / "scripts",
    ROOT / "tools" / "pybis2spice",
    ROOT / ".codex_deps" / "presentation" / "python",
    ROOT,
):
    sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402
from extract_silicon_kukd import run_fixture, solve_silicon_kukd  # noqa: E402
from pybis2spice import pybis2spice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402

OUT = ROOT / "results" / "settled_offset_diagnosis_2026-08-27"
REFERENCE_CSV = (
    ROOT / "results" / "stress_method_matrix_2026-08-20" / "hybrid"
    / "waveforms" / "io_buf_short_high_w1792ps.csv"
)
SOURCE_RUN = (
    ROOT / "results" / "stress_method_matrix_2026-08-20" / "hybrid"
    / "ngspice_runs" / "io_buf" / "edge_50ps" / "fast_5ps" / "cases"
    / "short_high_w1792ps_1792ps" / "ngspice_gate_state"
)

EDGE_NS = 5.0
WIDTH_NS = 1.792
REVERSE_NS = EDGE_NS + WIDTH_NS
RESTORE_NS = REVERSE_NS + 2.95830593904
FIXED_RESTORE_NS = REVERSE_NS + 1.83130459214
WINDOW = (4.5, 14.5)

TRANSISTOR_C = "#111111"
NATIVE_C = "#2B6CA3"
MODEL_C = "#C05621"
FIXED_C = "#7A3E9D"
PU_C = "#C05621"
PD_C = "#2E8B57"
MARKER_C = "#777777"


def load_csv(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(value) for value in row] for row in rows[1:]])
    return {name: values[:, index] for index, name in enumerate(rows[0])}


def probe_ngspice() -> dict[str, np.ndarray]:
    probe_dir = OUT / "full_event_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    raw_path = probe_dir / "run.raw"
    if not raw_path.exists() or raw_path.stat().st_size < 1024:
        for name in ("run.sp", "driver_OutputInput_Typical.sub"):
            shutil.copy2(SOURCE_RUN / name, probe_dir / name)
        deck_path = probe_dir / "run.sp"
        extras = (
            "V(xdrv.gupcmd)", "V(xdrv.gdncmd)", "V(xdrv.cmdsettled)",
            "V(xdrv.hnx)", "V(xdrv.puonp)", "V(xdrv.puoffp)",
            "V(xdrv.pdoffp)", "V(xdrv.pdonp)",
        )
        lines: list[str] = []
        for line in deck_path.read_text(encoding="utf-8").splitlines():
            if line.lower().startswith(".save"):
                words = line.split()
                line = " ".join(words + [item for item in extras if item not in words])
            lines.append(line)
        deck_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log_path = probe_dir / "ngspice_stdout.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [str(default_ngspice(console=True)), "-b", "-r", "run.raw", "run.sp"],
                cwd=probe_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=300,
                check=False,
            )
        if result.returncode != 0 or not raw_path.exists():
            raise RuntimeError(f"ngspice probe failed; see {log_path}")
    return parse_ngspice_raw(raw_path)


def probe_fixed_ngspice() -> dict[str, np.ndarray]:
    """Run/cache the tested earlier, faster command-restore variant."""
    probe_dir = OUT / "full_event_fix_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    raw_path = probe_dir / "run.raw"
    if not raw_path.exists() or raw_path.stat().st_size < 1024:
        shutil.copy2(OUT / "full_event_probe" / "run.sp", probe_dir / "run.sp")
        source_sub = (OUT / "full_event_probe" / "driver_OutputInput_Typical.sub")
        sub_text = source_sub.read_text(encoding="utf-8")
        sub_text = sub_text.replace(
            "BCMDSETTLED CMDSETTLED 0 V = (V(HNX) > 2.95830593904) ? 1.0 : 0.0",
            "BCMDSETTLED CMDSETTLED 0 V = (V(HNX) > 1.83130459214) ? 1.0 : 0.0",
        )
        sub_text = sub_text.replace("/ 1.12696960112n", "/ 0.25n")
        (probe_dir / "driver_OutputInput_Typical.sub").write_text(
            sub_text, encoding="utf-8"
        )
        log_path = probe_dir / "ngspice_stdout.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [str(default_ngspice(console=True)), "-b", "-r", "run.raw", "run.sp"],
                cwd=probe_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=300,
                check=False,
            )
        if result.returncode != 0 or not raw_path.exists():
            raise RuntimeError(f"fixed ngspice probe failed; see {log_path}")
    return parse_ngspice_raw(raw_path)


def transistor_coefficients() -> np.ndarray:
    device = next(item for item in base.DEVICES if item.device_id == "io_buf")
    case = base.PulseCase(
        "short_high_w1792ps_chain",
        0.050,
        "short_high",
        WIDTH_NS,
        22.0,
        "offset chain",
    )
    fixture_root = OUT / "full_event_transistor_kukd"
    low = run_fixture(
        device, case, 0.0, fixture_root / "vfix_0",
        default_hspice(), 300,
    )
    high = run_fixture(
        device, case, device.supply_v, fixture_root / "vfix_vcc",
        default_hspice(), 300,
    )
    ibis_data = pybis2spice.DataModel(
        pybis2spice.get_ibis_model_ecdtools(str(device.fast_ibis)),
        model_name=device.model,
        component_name=device.component,
    )
    solved = solve_silicon_kukd(ibis_data, low, high, device.supply_v)
    csv_path = fixture_root / "transistor_derived_kukd_uniform_5ps.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_ns", "transistor_ku", "transistor_kd", "condition_number"])
        writer.writerows(np.column_stack([solved[:, 0] * 1e9, solved[:, 1:]]))
    return solved


def signal(raw: dict[str, np.ndarray], name: str) -> np.ndarray:
    keys = {key.lower(): key for key in raw}
    return np.asarray(raw[keys[name.lower()]], dtype=float)


def add_event_markers(axis: plt.Axes) -> None:
    for when in (EDGE_NS, REVERSE_NS, RESTORE_NS):
        axis.axvline(when, color=MARKER_C, ls="--", lw=1.25, zorder=0)
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=10.8)
    axis.set_xlim(*WINDOW)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")


def add_fix_comparison_markers(axis: plt.Axes) -> None:
    for when in (EDGE_NS, REVERSE_NS):
        axis.axvline(when, color=MARKER_C, ls="--", lw=1.25, zorder=0)
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
    axis.tick_params(labelsize=10.8)
    axis.set_xlim(*WINDOW)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reference = load_csv(REFERENCE_CSV)
    raw = probe_ngspice()
    fixed_raw = probe_fixed_ngspice()
    silicon = transistor_coefficients()

    model_time = signal(raw, "time") * 1e9
    fixed_time = signal(fixed_raw, "time") * 1e9
    silicon_time = silicon[:, 0] * 1e9

    fig, axes = plt.subplots(6, 1, figsize=(14.0, 17.0), sharex=True)

    axes[0].plot(model_time, signal(raw, "v(in_dig)"), color="#444444", lw=2.8)
    axes[0].set_ylabel("Input (V)", fontsize=13)
    axes[0].set_ylim(-0.2, 3.6)
    axes[0].set_title("1. Input stimulus", loc="left", fontsize=14, fontweight="bold")

    axes[1].plot(model_time, signal(raw, "v(xdrv.gupcmd)"), color=PU_C, lw=2.8,
                 label="GUPCMD")
    axes[1].plot(model_time, signal(raw, "v(xdrv.guptarget)"), color=PU_C, lw=1.8,
                 ls=(0, (5, 2.2)), label="GUPTARGET after clamp")
    axes[1].plot(model_time, signal(raw, "v(xdrv.gdncmd)"), color=PD_C, lw=2.8,
                 label="GDNCMD")
    axes[1].plot(model_time, signal(raw, "v(xdrv.gdntarget)"), color=PD_C, lw=1.8,
                 ls=(0, (5, 2.2)), label="GDNTARGET after clamp")
    axes[1].set_ylabel("Command", fontsize=13)
    axes[1].set_ylim(-0.12, 1.12)
    axes[1].set_title("2. Command capacitors and clamped targets", loc="left",
                      fontsize=14, fontweight="bold")
    axes[1].legend(loc="center right", fontsize=10.5, ncol=2, framealpha=0.95)

    axes[2].plot(model_time, signal(raw, "v(xdrv.gup)"), color=PU_C, lw=2.8,
                 label="GUP")
    axes[2].plot(model_time, signal(raw, "v(xdrv.gdn)"), color=PD_C, lw=2.8,
                 label="GDN")
    axes[2].set_ylabel("Gate state", fontsize=13)
    axes[2].set_ylim(-0.12, 1.12)
    axes[2].set_title("3. Continuous gate states", loc="left", fontsize=14,
                      fontweight="bold")
    axes[2].legend(loc="center right", fontsize=10.5, framealpha=0.95)

    for axis, coeff, number in ((axes[3], "ku", 4), (axes[4], "kd", 5)):
        axis.plot(silicon_time, silicon[:, 1 if coeff == "ku" else 2],
                  color=TRANSISTOR_C, lw=3.4, label="HSPICE transistor-derived")
        axis.plot(reference["time_ns"], reference[f"hspice_{coeff}"],
                  color=NATIVE_C, lw=2.7, label="HSPICE native IBIS")
        axis.plot(model_time, signal(raw, f"v(xdrv.{coeff})"),
                  color=MODEL_C, lw=2.4, label="gate-state hybrid")
        axis.axhline(0.0, color="#555555", lw=1.0)
        axis.set_ylabel(coeff.capitalize(), fontsize=13)
        axis.set_ylim(-0.18, 1.18)
        axis.set_title(f"{number}. Effective {coeff.capitalize()} coefficient",
                       loc="left", fontsize=14, fontweight="bold")
    axes[3].legend(loc="center right", fontsize=10.5, framealpha=0.95)

    axes[5].plot(reference["time_ns"], reference["silicon_pad"],
                 color=TRANSISTOR_C, lw=3.4, label="HSPICE transistor")
    axes[5].plot(reference["time_ns"], reference["hspice_pad"],
                 color=NATIVE_C, lw=2.7, label="HSPICE native IBIS")
    axes[5].plot(model_time, signal(raw, "v(pad)"),
                 color=MODEL_C, lw=2.4, label="gate-state hybrid")
    axes[5].axhline(0.0, color="#555555", lw=1.0)
    axes[5].set_ylabel("Pad (V)", fontsize=13)
    axes[5].set_ylim(-0.10, 1.48)
    axes[5].set_title("6. Loaded pad voltage", loc="left", fontsize=14,
                      fontweight="bold")
    axes[5].legend(loc="center right", fontsize=10.5, framealpha=0.95)
    axes[5].set_xlabel("Time (ns)", fontsize=13)

    for axis in axes:
        add_event_markers(axis)
    axes[0].text(EDGE_NS, 3.48, "rising edge", ha="center", va="top",
                 fontsize=10.5, color="#555555")
    axes[0].text(REVERSE_NS, 3.48, "falling edge", ha="center", va="top",
                 fontsize=10.5, color="#555555")
    axes[0].text(RESTORE_NS, 3.48, "cleanup starts", ha="center", va="top",
                 fontsize=10.5, color="#555555")

    fig.suptitle("io_buf | short high | 1792 ps | command-to-pad chain",
                 fontsize=19, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    figure_path = OUT / "08_comprehensive_offset_chain.png"
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)

    grid = np.arange(WINDOW[0], WINDOW[1] + 0.0025, 0.005)
    csv_path = OUT / "08_comprehensive_offset_chain.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "time_ns", "input_v", "gupcmd", "guptarget", "gup",
            "gdncmd", "gdntarget", "gdn", "transistor_ku", "native_ku",
            "model_ku", "transistor_kd", "native_kd", "model_kd",
            "transistor_pad_v", "native_pad_v", "model_pad_v",
        ])
        writer.writerows(zip(
            grid,
            np.interp(grid, model_time, signal(raw, "v(in_dig)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gupcmd)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.guptarget)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gup)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gdncmd)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gdntarget)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gdn)")),
            np.interp(grid, silicon_time, silicon[:, 1]),
            np.interp(grid, reference["time_ns"], reference["hspice_ku"]),
            np.interp(grid, model_time, signal(raw, "v(xdrv.ku)")),
            np.interp(grid, silicon_time, silicon[:, 2]),
            np.interp(grid, reference["time_ns"], reference["hspice_kd"]),
            np.interp(grid, model_time, signal(raw, "v(xdrv.kd)")),
            np.interp(grid, reference["time_ns"], reference["silicon_pad"]),
            np.interp(grid, reference["time_ns"], reference["hspice_pad"]),
            np.interp(grid, model_time, signal(raw, "v(pad)")),
        ))

    # A second figure keeps the same causal reading order, but overlays the
    # tested restore-term fix at every layer where it can affect the result.
    fig, axes = plt.subplots(8, 1, figsize=(14.0, 21.0), sharex=True)

    axes[0].plot(model_time, signal(raw, "v(in_dig)"), color="#444444", lw=2.8)
    axes[0].set_ylabel("Input (V)", fontsize=13)
    axes[0].set_ylim(-0.2, 3.6)
    axes[0].set_title("1. Input stimulus", loc="left", fontsize=14, fontweight="bold")

    axes[1].plot(model_time, signal(raw, "v(xdrv.gupcmd)"), color=MODEL_C, lw=2.8,
                 label="original GUPCMD")
    axes[1].plot(fixed_time, signal(fixed_raw, "v(xdrv.gupcmd)"), color=FIXED_C, lw=2.5,
                 label="fix GUPCMD")
    axes[1].set_ylabel("Pullup command", fontsize=13)
    axes[1].set_ylim(-0.12, 1.12)
    axes[1].set_title("2. Pullup command capacitor", loc="left",
                      fontsize=14, fontweight="bold")
    axes[1].legend(loc="upper right", fontsize=10.2, framealpha=0.95)

    axes[2].plot(model_time, signal(raw, "v(xdrv.gdncmd)"), color=MODEL_C, lw=2.8,
                 label="original GDNCMD")
    axes[2].plot(fixed_time, signal(fixed_raw, "v(xdrv.gdncmd)"), color=FIXED_C, lw=2.5,
                 label="fix GDNCMD")
    axes[2].set_ylabel("Pulldown command", fontsize=13)
    axes[2].set_ylim(-0.12, 1.12)
    axes[2].set_title("3. Pulldown command capacitor", loc="left",
                      fontsize=14, fontweight="bold")
    axes[2].legend(loc="upper right", fontsize=10.2, framealpha=0.95)

    axes[3].plot(model_time, signal(raw, "v(xdrv.gup)"), color=MODEL_C, lw=2.8,
                 label="original GUP")
    axes[3].plot(fixed_time, signal(fixed_raw, "v(xdrv.gup)"), color=FIXED_C, lw=2.5,
                 label="fix GUP")
    axes[3].set_ylabel("GUP", fontsize=13)
    axes[3].set_ylim(-0.12, 1.12)
    axes[3].set_title("4. Continuous pullup state", loc="left", fontsize=14,
                      fontweight="bold")
    axes[3].legend(loc="center right", fontsize=10.5, framealpha=0.95)

    axes[4].plot(model_time, signal(raw, "v(xdrv.gdn)"), color=MODEL_C, lw=2.8,
                 label="original GDN")
    axes[4].plot(fixed_time, signal(fixed_raw, "v(xdrv.gdn)"), color=FIXED_C, lw=2.5,
                 label="fix GDN")
    axes[4].set_ylabel("GDN", fontsize=13)
    axes[4].set_ylim(-0.12, 1.12)
    axes[4].set_title("5. Continuous pulldown state", loc="left", fontsize=14,
                      fontweight="bold")
    axes[4].legend(loc="center right", fontsize=10.5, framealpha=0.95)

    for axis, coeff, number in ((axes[5], "ku", 6), (axes[6], "kd", 7)):
        axis.plot(silicon_time, silicon[:, 1 if coeff == "ku" else 2],
                  color=TRANSISTOR_C, lw=3.4, label="HSPICE transistor-derived")
        axis.plot(reference["time_ns"], reference[f"hspice_{coeff}"],
                  color=NATIVE_C, lw=2.7, label="HSPICE native IBIS")
        axis.plot(model_time, signal(raw, f"v(xdrv.{coeff})"),
                  color=MODEL_C, lw=2.4, label="original")
        axis.plot(fixed_time, signal(fixed_raw, f"v(xdrv.{coeff})"),
                  color=FIXED_C, lw=2.2, label="fix")
        axis.axhline(0.0, color="#555555", lw=1.0)
        axis.set_ylabel(coeff.capitalize(), fontsize=13)
        axis.set_ylim(-0.18, 1.18)
        axis.set_title(f"{number}. Effective {coeff.capitalize()} coefficient",
                       loc="left", fontsize=14, fontweight="bold")
    axes[5].legend(loc="center right", fontsize=10.0, framealpha=0.95)

    axes[7].plot(reference["time_ns"], reference["silicon_pad"],
                 color=TRANSISTOR_C, lw=3.4, label="HSPICE transistor")
    axes[7].plot(reference["time_ns"], reference["hspice_pad"],
                 color=NATIVE_C, lw=2.7, label="HSPICE native IBIS")
    axes[7].plot(model_time, signal(raw, "v(pad)"),
                 color=MODEL_C, lw=2.4, label="original")
    axes[7].plot(fixed_time, signal(fixed_raw, "v(pad)"),
                 color=FIXED_C, lw=2.2, label="fix")
    axes[7].axhline(0.0, color="#555555", lw=1.0)
    axes[7].set_ylabel("Pad (V)", fontsize=13)
    axes[7].set_ylim(-0.10, 1.48)
    axes[7].set_title("8. Loaded pad voltage", loc="left", fontsize=14,
                      fontweight="bold")
    axes[7].legend(loc="center right", fontsize=10.0, framealpha=0.95)
    axes[7].set_xlabel("Time (ns)", fontsize=13)

    for axis in axes:
        add_fix_comparison_markers(axis)
    axes[0].text(EDGE_NS, 3.48, "rising edge", ha="center", va="top",
                 fontsize=10.5, color="#555555")
    axes[0].text(REVERSE_NS, 3.48, "falling edge", ha="center", va="top",
                 fontsize=10.5, color="#555555")

    fig.suptitle("io_buf | short high | 1792 ps | original vs fix chain",
                 fontsize=19, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    fixed_figure_path = OUT / "09_comprehensive_offset_fix_comparison.png"
    fig.savefig(fixed_figure_path, dpi=180)
    plt.close(fig)

    fixed_csv_path = OUT / "09_comprehensive_offset_fix_comparison.csv"
    with fixed_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "time_ns", "input_v", "original_gupcmd", "fix_gupcmd",
            "original_guptarget", "fix_guptarget", "original_gup", "fix_gup",
            "original_gdncmd", "fix_gdncmd", "original_gdntarget", "fix_gdntarget",
            "original_gdn", "fix_gdn", "transistor_ku", "native_ku",
            "original_ku", "fix_ku", "transistor_kd", "native_kd",
            "original_kd", "fix_kd", "transistor_pad_v", "native_pad_v",
            "original_pad_v", "fix_pad_v",
        ])
        writer.writerows(zip(
            grid,
            np.interp(grid, model_time, signal(raw, "v(in_dig)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gupcmd)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(xdrv.gupcmd)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.guptarget)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(xdrv.guptarget)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gup)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(xdrv.gup)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gdncmd)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(xdrv.gdncmd)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gdntarget)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(xdrv.gdntarget)")),
            np.interp(grid, model_time, signal(raw, "v(xdrv.gdn)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(xdrv.gdn)")),
            np.interp(grid, silicon_time, silicon[:, 1]),
            np.interp(grid, reference["time_ns"], reference["hspice_ku"]),
            np.interp(grid, model_time, signal(raw, "v(xdrv.ku)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(xdrv.ku)")),
            np.interp(grid, silicon_time, silicon[:, 2]),
            np.interp(grid, reference["time_ns"], reference["hspice_kd"]),
            np.interp(grid, model_time, signal(raw, "v(xdrv.kd)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(xdrv.kd)")),
            np.interp(grid, reference["time_ns"], reference["silicon_pad"]),
            np.interp(grid, reference["time_ns"], reference["hspice_pad"]),
            np.interp(grid, model_time, signal(raw, "v(pad)")),
            np.interp(grid, fixed_time, signal(fixed_raw, "v(pad)")),
        ))

    # This separate view starts before the delayed command changes, then uses
    # a second command panel to make the small residual visible on its own
    # scale.  The remaining panels follow that residual to the pad.
    residual_window = (4.8, 11.25)
    tail_window = (8.35, 11.25)
    fig, axes = plt.subplots(6, 1, figsize=(13.5, 16.5), sharex=True)

    axes[0].plot(model_time, signal(raw, "v(in_dig)"), color="#444444", lw=2.8)
    axes[0].set_ylabel("Input (V)", fontsize=13)
    axes[0].set_ylim(-0.2, 3.6)
    axes[0].set_title("1. Input stimulus", loc="left", fontsize=14,
                      fontweight="bold")

    for axis in (axes[1], axes[2]):
        axis.plot(model_time, signal(raw, "v(xdrv.gupcmd)"), color=MODEL_C, lw=3.0,
                  label="original GUPCMD")
        axis.plot(fixed_time, signal(fixed_raw, "v(xdrv.gupcmd)"), color=FIXED_C,
                  lw=2.7, label="fix GUPCMD")
    axes[1].set_ylabel("GUPCMD", fontsize=13)
    axes[1].set_ylim(-0.05, 1.08)
    axes[1].set_title("2. Pullup command switching", loc="left", fontsize=14,
                      fontweight="bold")
    axes[1].legend(loc="upper right", fontsize=10.5, framealpha=0.95)
    axes[2].set_ylabel("GUPCMD", fontsize=13)
    axes[2].set_ylim(-0.003, 0.043)
    axes[2].set_title("3. Command residual after turn-off", loc="left", fontsize=14,
                      fontweight="bold")

    axes[3].plot(model_time, signal(raw, "v(xdrv.gup)"), color=MODEL_C, lw=3.0,
                 label="original GUP")
    axes[3].plot(fixed_time, signal(fixed_raw, "v(xdrv.gup)"), color=FIXED_C,
                 lw=2.7, label="fix GUP")
    axes[3].set_ylabel("GUP", fontsize=13)
    axes[3].set_ylim(-0.03, 0.58)
    axes[3].set_title("4. Stored pullup state", loc="left", fontsize=14,
                      fontweight="bold")
    axes[3].legend(loc="upper right", fontsize=10.5, framealpha=0.95)

    axes[4].plot(silicon_time, silicon[:, 1], color=TRANSISTOR_C, lw=3.4,
                 label="HSPICE transistor-derived")
    axes[4].plot(reference["time_ns"], reference["hspice_ku"], color=NATIVE_C,
                 lw=2.7, label="HSPICE native IBIS")
    axes[4].plot(model_time, signal(raw, "v(xdrv.ku)"), color=MODEL_C, lw=2.6,
                 label="original")
    axes[4].plot(fixed_time, signal(fixed_raw, "v(xdrv.ku)"), color=FIXED_C,
                 lw=2.4, label="fix")
    axes[4].set_ylabel("Ku", fontsize=13)
    axes[4].set_ylim(-0.15, 1.02)
    axes[4].set_title("5. Pullup coefficient", loc="left", fontsize=14,
                      fontweight="bold")
    axes[4].legend(loc="upper right", fontsize=10.0, framealpha=0.95)

    axes[5].plot(reference["time_ns"], reference["silicon_pad"],
                 color=TRANSISTOR_C, lw=3.4, label="HSPICE transistor")
    axes[5].plot(reference["time_ns"], reference["hspice_pad"], color=NATIVE_C,
                 lw=2.7, label="HSPICE native IBIS")
    axes[5].plot(model_time, signal(raw, "v(pad)"), color=MODEL_C, lw=2.6,
                 label="original")
    axes[5].plot(fixed_time, signal(fixed_raw, "v(pad)"), color=FIXED_C,
                 lw=2.4, label="fix")
    axes[5].set_ylabel("Pad (V)", fontsize=13)
    axes[5].set_ylim(-0.10, 1.02)
    axes[5].set_title("6. Loaded pad voltage", loc="left", fontsize=14,
                      fontweight="bold")
    axes[5].legend(loc="upper right", fontsize=10.0, framealpha=0.95)
    axes[5].set_xlabel("Time (ns)", fontsize=13)

    for axis in axes:
        for when in (EDGE_NS, REVERSE_NS):
            axis.axvline(when, color=MARKER_C, ls="--", lw=1.15)
        axis.axhline(0.0, color="#555555", lw=0.9)
        axis.set_xlim(*residual_window)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=10.8)
        for spine in axis.spines.values():
            spine.set_color("#3A4753")
    axes[0].text(EDGE_NS, 3.48, "rising edge", ha="center", va="top",
                 fontsize=10.2, color="#555555")
    axes[0].text(REVERSE_NS, 3.48, "falling edge", ha="center", va="top",
                 fontsize=10.2, color="#555555")
    fig.suptitle("io_buf | short high | 1792 ps | command switching and residual",
                 fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.974))
    tail_figure_path = OUT / "10_offset_fix_tail_zoom.png"
    fig.savefig(tail_figure_path, dpi=190)
    plt.close(fig)

    # Pad-only presentation view: preserve the complete voltage event, then
    # show the same traces in millivolts where the cleanup difference lives.
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 8.6))
    pad_traces = (
        (reference["time_ns"], reference["silicon_pad"], TRANSISTOR_C, 3.4,
         "HSPICE transistor"),
        (reference["time_ns"], reference["hspice_pad"], NATIVE_C, 2.7,
         "HSPICE native IBIS"),
        (model_time, signal(raw, "v(pad)"), MODEL_C, 2.6,
         "original"),
        (fixed_time, signal(fixed_raw, "v(pad)"), FIXED_C, 2.4,
         "fix"),
    )
    for time_values, pad_values, color, width, label in pad_traces:
        axes[0].plot(time_values, pad_values, color=color, lw=width, label=label)
        axes[1].plot(time_values, 1e3 * pad_values, color=color, lw=width, label=label)

    pad_event_window = (6.9, 11.25)
    pad_tail_window = (7.4, 11.25)
    axes[0].set_xlim(*pad_event_window)
    axes[0].set_ylim(-0.10, 1.05)
    axes[0].set_ylabel("Pad (V)", fontsize=13)
    axes[0].set_title("Response from approximately 7 ns", loc="left", fontsize=14,
                      fontweight="bold")
    for when in (EDGE_NS, REVERSE_NS):
        axes[0].axvline(when, color=MARKER_C, ls="--", lw=1.25)
    axes[0].legend(loc="upper right", fontsize=10.3, framealpha=0.95, ncol=2)

    axes[1].set_xlim(*pad_tail_window)
    axes[1].set_ylim(-10.0, 220.0)
    axes[1].set_ylabel("Pad (mV)", fontsize=13)
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    axes[1].set_title("Post-reversal tail zoom", loc="left", fontsize=14,
                      fontweight="bold")

    for axis in axes:
        axis.axhline(0.0, color="#555555", lw=0.9)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=10.8)
        for spine in axis.spines.values():
            spine.set_color("#3A4753")
    fig.suptitle("io_buf | short high | 1792 ps | pad voltage: original vs fix",
                 fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    pad_figure_path = OUT / "11_pad_voltage_fix_comparison.png"
    fig.savefig(pad_figure_path, dpi=190)
    plt.close(fig)

    # Internal-state view.  Use the post-reversal interval so the small stored
    # offset is visible instead of being compressed by the full turn-on peak.
    state_window = (7.0, 11.25)
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 8.6), sharex=True)
    internal_traces = (
        ("v(xdrv.gup)", "GUP", (-0.005, 0.26)),
        ("v(xdrv.ku)", "Ku", (-0.010, 0.275)),
    )
    for axis, (node, ylabel, ylim) in zip(axes, internal_traces):
        axis.plot(model_time, signal(raw, node), color=MODEL_C, lw=2.9,
                  label="original")
        axis.plot(fixed_time, signal(fixed_raw, node), color=FIXED_C, lw=2.6,
                  label="fix")
        axis.axhline(0.0, color="#555555", lw=0.9)
        axis.set_xlim(*state_window)
        axis.set_ylim(*ylim)
        axis.set_ylabel(ylabel, fontsize=13)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=10.8)
        axis.legend(loc="upper right", fontsize=10.5, framealpha=0.95)
        for spine in axis.spines.values():
            spine.set_color("#3A4753")
    axes[0].set_title("Pullup gate state", loc="left", fontsize=14,
                      fontweight="bold")
    axes[1].set_title("Pullup coefficient", loc="left", fontsize=14,
                      fontweight="bold")
    axes[1].set_xlabel("Time (ns)", fontsize=13)
    fig.suptitle("io_buf | short high | 1792 ps | GUP and Ku: original vs fix",
                 fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    gup_ku_figure_path = OUT / "12_gup_ku_fix_comparison.png"
    fig.savefig(gup_ku_figure_path, dpi=190)
    plt.close(fig)

    print(figure_path)
    print(csv_path)
    print(fixed_figure_path)
    print(fixed_csv_path)
    print(tail_figure_path)
    print(pad_figure_path)
    print(gup_ku_figure_path)
    print(OUT / "full_event_probe")
    print(OUT / "full_event_fix_probe")
    print(OUT / "full_event_transistor_kukd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
