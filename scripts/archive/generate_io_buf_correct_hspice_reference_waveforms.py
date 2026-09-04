from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0  # noqa: E402
from hspice_reference_cache import (  # noqa: E402
    cache_dir,
    reference_signature,
    restore as restore_hspice_cache,
    save as save_hspice_cache,
)
from spice_tool_paths import default_hspice  # noqa: E402


OUT = ROOT / "results" / "io_buf_correct_hspice_reference_waveforms_2026-07-23"
CASES_DIR = OUT / "cases"
FIGURES_DIR = OUT / "figures"
FAST_IBIS = (
    ROOT
    / "results"
    / "io_buf_fast_edge_retest_2026-06-05"
    / "source"
    / "io_buf.ibs"
)
IO_BUF_SP = ROOT / "buffers" / "models" / "io_buf.sp"
ORIGINAL_MODEL = ROOT.parent / "s2ibispy" / "tests" / "hspice.mod"
VDD = 3.3


@dataclass(frozen=True)
class Case:
    case_id: str
    label: str
    pattern: str
    pulse_width_ns: float
    stop_ns: float


CASES = [
    Case(
        "edge_1ps_base_50r_2pf",
        "Normal long pulse",
        "long",
        10.0,
        25.0,
    ),
    Case(
        "short_pulse_1ns_high",
        "Interrupted 1 ns high pulse",
        "short_high",
        1.0,
        14.0,
    ),
    Case(
        "short_pulse_2ns_high",
        "Interrupted 2 ns high pulse",
        "short_high",
        2.0,
        15.0,
    ),
    Case(
        "short_pulse_1ns_low",
        "Interrupted 1 ns low pulse",
        "short_low",
        1.0,
        18.0,
    ),
    Case(
        "short_pulse_2ns_low",
        "Interrupted 2 ns low pulse",
        "short_low",
        2.0,
        18.0,
    ),
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pwl_points(case: Case) -> list[tuple[float, float]]:
    edge = 0.001
    if case.pattern == "long":
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + edge, VDD),
            (15.0, VDD),
            (15.0 + edge, 0.0),
            (case.stop_ns, 0.0),
        ]
    if case.pattern == "short_high":
        reverse = 5.0 + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + edge, VDD),
            (reverse, VDD),
            (reverse + edge, 0.0),
            (case.stop_ns, 0.0),
        ]
    if case.pattern == "short_low":
        reverse = 10.0 + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + edge, VDD),
            (10.0, VDD),
            (10.0 + edge, 0.0),
            (reverse, 0.0),
            (reverse + edge, VDD),
            (case.stop_ns, VDD),
        ]
    raise ValueError(case.pattern)


def edge_times(case: Case) -> list[float]:
    points = pwl_points(case)
    result: list[float] = []
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if abs(v1 - v0) > 1e-9:
            result.append((t0 + t1) / 2)
    return result


def pwl_text(case: Case) -> str:
    lines = ["Vin in_dig 0 PWL("]
    for time_ns, voltage in pwl_points(case):
        lines.append(f"+ {time_ns:.6f}n {voltage:.6f}")
    lines[-1] += " )"
    return "\n".join(lines)


def native_deck(case: Case) -> str:
    return f"""* Corrected io_buf HSPICE native-IBIS reference
* Regenerated 5 ps IBIS; 1 ps runtime command; 50 ohm || 2 pF
.title corrected native IBIS {case.case_id}
.option post=2 probe accurate
.option ingold=2
.temp 27

{pwl_text(case)}

Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rdig dig_q 0 1k
Rload pad 0 50
Cload pad 0 2p

.probe tran V(in_dig) V(pad) V(ku) V(kd)
.tran 0.001n {case.stop_ns:.6f}n
.end
"""


def transistor_deck(case: Case) -> str:
    return f"""* Corrected io_buf HSPICE transistor reference
* Original HSPICE MOS card; ideal supply; 1 ps command; 50 ohm || 2 pF
.title corrected transistor reference {case.case_id}
.option post=2 probe accurate
.option ingold=2
.temp 27

{pwl_text(case)}

Vdd_src vdd_ref 0 DC 3.3
Voe_src oe_ref 0 DC 3.3

.include 'hspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XBUF in_dig oe_ref pad in_sense vdd_ref 0 SPICE_BUF
Rload pad 0 50
Cload pad 0 2p

.probe tran V(in_dig) V(pad) V(xbuf.n2) V(xbuf.n3)
.tran 0.001n {case.stop_ns:.6f}n
.end
"""


def run_process(hspice: Path, run_dir: Path, stem: str, timeout_s: int) -> None:
    log = run_dir / "hspice_stdout.log"
    with log.open("w", encoding="utf-8") as handle:
        try:
            completed = subprocess.run(
                [str(hspice), "-i", f"{stem}.sp", "-o", stem],
                cwd=run_dir,
                stdout=handle,
                stderr=subprocess.STDOUT,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"HSPICE timeout: {run_dir}") from exc
    if completed.returncode != 0 or not (run_dir / f"{stem}.tr0").exists():
        raise RuntimeError(f"HSPICE failed: {run_dir}; see {log}")


def run_reference(
    case: Case,
    flow: str,
    hspice: Path,
    timeout_s: int,
    force_rerun: bool,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    run_dir = CASES_DIR / case.case_id / flow
    ensure_dir(run_dir)
    stem = "run"
    if flow == "hspice_native_fast_ibis":
        deck_text = native_deck(case)
        inputs = [FAST_IBIS]
        shutil.copy2(FAST_IBIS, run_dir / "io_buf.ibs")
    elif flow == "hspice_transistor_original":
        deck_text = transistor_deck(case)
        inputs = [IO_BUF_SP, ORIGINAL_MODEL]
        shutil.copy2(IO_BUF_SP, run_dir / "io_buf.sp")
        shutil.copy2(ORIGINAL_MODEL, run_dir / "hspice.mod")
    else:
        raise ValueError(flow)

    signature_id, signature = reference_signature(
        deck_text,
        inputs,
        {
            "family": "io_buf_correct_hspice_reference",
            "case": case.case_id,
            "flow": flow,
        },
    )
    cached = cache_dir("io_buf_correct_hspice_reference", case.case_id, signature_id)
    source = "run"
    if not force_rerun and restore_hspice_cache(cached, run_dir, stem, deck_text):
        source = "cache"
    else:
        (run_dir / f"{stem}.sp").write_text(deck_text, encoding="ascii")
        run_process(hspice, run_dir, stem, timeout_s)
        save_hspice_cache(cached, run_dir, stem, deck_text, signature)

    tr0 = run_dir / f"{stem}.tr0"
    return parse_hspice_tr0(tr0), {
        "case_id": case.case_id,
        "flow": flow,
        "source": source,
        "deck": str((run_dir / "run.sp").relative_to(ROOT)),
        "tr0": str(tr0.relative_to(ROOT)),
        "lis": str((run_dir / "run.lis").relative_to(ROOT)),
    }


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"Missing {names}; available: {sorted(data)}")


def ns(data: dict[str, np.ndarray]) -> np.ndarray:
    return np.asarray(data["time"], dtype=float) * 1e9


def case_window(case: Case) -> tuple[float, float]:
    if case.pattern == "long":
        return 4.5, 20.0
    return 4.5, case.stop_ns


def input_values(case: Case, time_ns: np.ndarray) -> np.ndarray:
    points = pwl_points(case)
    return np.interp(
        time_ns,
        [item[0] for item in points],
        [item[1] for item in points],
    )


def add_edges(ax: plt.Axes, case: Case) -> None:
    for index, edge in enumerate(edge_times(case)):
        ax.axvline(
            edge,
            color="#777777",
            lw=1.0,
            ls="--",
            alpha=0.8,
            label="input command edge" if index == 0 else None,
        )
    ax.grid(True, alpha=0.22)


def aligned_data(
    case: Case,
    native: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    time_ns = ns(native)
    transistor_t = ns(transistor)
    n2 = find_signal(transistor, "v(xbuf.n2)")
    n3 = find_signal(transistor, "v(xbuf.n3)")
    return {
        "time_ns": time_ns,
        "input_v": input_values(case, time_ns),
        "native_ibis_pad_v": find_signal(native, "v(pad)"),
        "native_ibis_ku": find_signal(native, "v(ku)"),
        "native_ibis_kd": find_signal(native, "v(kd)"),
        "transistor_pad_v": np.interp(
            time_ns, transistor_t, find_signal(transistor, "v(pad)")
        ),
        "transistor_pullup_gate_enable": np.interp(
            time_ns, transistor_t, 1.0 - n2 / VDD
        ),
        "transistor_pulldown_gate_enable": np.interp(
            time_ns, transistor_t, n3 / VDD
        ),
    }


def save_aligned_csv(case: Case, data: dict[str, np.ndarray]) -> None:
    path = CASES_DIR / case.case_id / "aligned_correct_pair_waveforms.csv"
    ensure_dir(path.parent)
    fields = list(data)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for values in zip(*(data[field] for field in fields)):
            writer.writerow([f"{float(value):.12g}" for value in values])


def plot_case(case: Case, data: dict[str, np.ndarray]) -> None:
    case_figures = FIGURES_DIR / case.case_id
    ensure_dir(case_figures)
    time_ns = data["time_ns"]
    x0, x1 = case_window(case)

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(11.5, 6.7),
        sharex=True,
        gridspec_kw={"height_ratios": [0.8, 2.3]},
        constrained_layout=True,
    )
    axes[0].plot(time_ns, data["input_v"], color="#1f77b4", lw=2.0)
    axes[0].set_ylabel("input (V)")
    axes[0].set_title(case.label, loc="left", fontweight="bold")
    axes[1].plot(
        time_ns,
        data["native_ibis_pad_v"],
        color="#111111",
        lw=3.0,
        label="HSPICE native IBIS, regenerated 5 ps file",
    )
    axes[1].plot(
        time_ns,
        data["transistor_pad_v"],
        color="#d62728",
        lw=2.1,
        label="HSPICE transistor, original model card",
    )
    axes[1].set_ylabel("pad voltage (V)")
    axes[1].set_xlabel("time (ns)")
    axes[1].legend(loc="best", fontsize=9)
    for ax in axes:
        ax.set_xlim(x0, x1)
        add_edges(ax, case)
    fig.savefig(case_figures / "01_correct_pair_pad_overlay.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.2), sharex=True, constrained_layout=True)
    axes[0].plot(time_ns, data["native_ibis_ku"], color="#d62728", lw=2.2, label="Ku")
    axes[0].plot(time_ns, data["native_ibis_kd"], color="#1f77b4", lw=2.2, label="Kd")
    axes[0].axhline(0.0, color="#777777", lw=0.8)
    axes[0].set_ylabel("IBIS coefficient")
    axes[0].set_title(
        "Native-IBIS switching coefficients",
        loc="left",
        fontweight="bold",
    )
    axes[0].legend(loc="best")
    axes[1].plot(
        time_ns,
        data["transistor_pullup_gate_enable"],
        color="#d62728",
        lw=2.2,
        label="pullup gate enable, 1 - n2/VDD",
    )
    axes[1].plot(
        time_ns,
        data["transistor_pulldown_gate_enable"],
        color="#1f77b4",
        lw=2.2,
        label="pulldown gate enable, n3/VDD",
    )
    axes[1].set_ylabel("normalized gate control")
    axes[1].set_xlabel("time (ns)")
    axes[1].set_title(
        "Source-transistor output-stage controls",
        loc="left",
        fontweight="bold",
    )
    axes[1].legend(loc="best")
    for ax in axes:
        ax.set_xlim(x0, x1)
        add_edges(ax, case)
    fig.savefig(case_figures / "02_internal_switching_context.png", dpi=180)
    plt.close(fig)


def plot_contact_sheet(all_data: dict[str, dict[str, np.ndarray]]) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(14.0, 12.0), constrained_layout=True)
    for ax in axes.flat:
        ax.axis("off")
    for ax, case in zip(axes.flat, CASES):
        data = all_data[case.case_id]
        time_ns = data["time_ns"]
        ax.axis("on")
        ax.plot(
            time_ns,
            data["native_ibis_pad_v"],
            color="#111111",
            lw=2.8,
            label="HSPICE native IBIS",
        )
        ax.plot(
            time_ns,
            data["transistor_pad_v"],
            color="#d62728",
            lw=1.9,
            label="HSPICE transistor",
        )
        ax.set_xlim(*case_window(case))
        ax.set_title(case.label, loc="left", fontweight="bold")
        ax.set_xlabel("time (ns)")
        ax.set_ylabel("pad voltage (V)")
        add_edges(ax, case)
    axes[0, 0].legend(loc="best", fontsize=9)
    fig.savefig(FIGURES_DIR / "correct_pair_pad_contact_sheet.png", dpi=180)
    plt.close(fig)


def crossing(
    time_ns: np.ndarray,
    values: np.ndarray,
    threshold: float,
    start_ns: float,
    stop_ns: float,
    rising: bool,
) -> float:
    mask = (time_ns >= start_ns) & (time_ns <= stop_ns)
    time = time_ns[mask]
    wave = values[mask]
    if rising:
        indexes = np.where((wave[:-1] < threshold) & (wave[1:] >= threshold))[0]
    else:
        indexes = np.where((wave[:-1] > threshold) & (wave[1:] <= threshold))[0]
    if len(indexes) == 0:
        return float("nan")
    index = int(indexes[0])
    dy = wave[index + 1] - wave[index]
    if abs(dy) < 1e-30:
        return float(time[index])
    return float(
        time[index]
        + (threshold - wave[index])
        * (time[index + 1] - time[index])
        / dy
    )


def calculate_metrics(case: Case, data: dict[str, np.ndarray]) -> dict[str, object]:
    time_ns = data["time_ns"]
    x0, x1 = case_window(case)
    mask = (time_ns >= x0) & (time_ns <= x1)
    native = data["native_ibis_pad_v"][mask]
    transistor = data["transistor_pad_v"][mask]
    error = transistor - native
    row: dict[str, object] = {
        "case_id": case.case_id,
        "case_label": case.label,
        "active_start_ns": x0,
        "active_stop_ns": x1,
        "pad_rmse_mv": float(np.sqrt(np.mean(error**2)) * 1e3),
        "pad_max_error_mv": float(np.max(np.abs(error)) * 1e3),
        "native_pad_min_v": float(np.min(native)),
        "native_pad_max_v": float(np.max(native)),
        "transistor_pad_min_v": float(np.min(transistor)),
        "transistor_pad_max_v": float(np.max(transistor)),
    }
    native_full = data["native_ibis_pad_v"]
    transistor_full = data["transistor_pad_v"]
    if case.pattern == "long":
        native_high = float(np.median(native_full[(time_ns >= 12.0) & (time_ns <= 14.5)]))
        transistor_high = float(
            np.median(transistor_full[(time_ns >= 12.0) & (time_ns <= 14.5)])
        )
        native_rise = crossing(time_ns, native_full, 0.5 * native_high, 5.0, 12.0, True)
        transistor_rise = crossing(
            time_ns, transistor_full, 0.5 * transistor_high, 5.0, 12.0, True
        )
        native_fall = crossing(
            time_ns, native_full, 0.5 * native_high, 15.0, 20.0, False
        )
        transistor_fall = crossing(
            time_ns, transistor_full, 0.5 * transistor_high, 15.0, 20.0, False
        )
        row.update(
            {
                "native_rise_50_ns": native_rise,
                "transistor_rise_50_ns": transistor_rise,
                "rise_50_delta_ps": (native_rise - transistor_rise) * 1e3,
                "native_fall_50_ns": native_fall,
                "transistor_fall_50_ns": transistor_fall,
                "fall_50_delta_ps": (native_fall - transistor_fall) * 1e3,
            }
        )
    elif case.pattern == "short_high":
        pulse_mask = (time_ns >= 5.0) & (time_ns <= case.stop_ns)
        native_index = int(np.argmax(native_full[pulse_mask]))
        transistor_index = int(np.argmax(transistor_full[pulse_mask]))
        pulse_time = time_ns[pulse_mask]
        row.update(
            {
                "native_pulse_peak_v": float(np.max(native_full[pulse_mask])),
                "native_pulse_peak_time_ns": float(pulse_time[native_index]),
                "transistor_pulse_peak_v": float(np.max(transistor_full[pulse_mask])),
                "transistor_pulse_peak_time_ns": float(pulse_time[transistor_index]),
            }
        )
    elif case.pattern == "short_low":
        native_high = float(np.median(native_full[(time_ns >= 9.0) & (time_ns <= 9.8)]))
        transistor_high = float(
            np.median(transistor_full[(time_ns >= 9.0) & (time_ns <= 9.8)])
        )
        reverse = 10.0 + case.pulse_width_ns
        native_recovery = crossing(
            time_ns,
            native_full,
            0.5 * native_high,
            reverse,
            case.stop_ns,
            True,
        )
        transistor_recovery = crossing(
            time_ns,
            transistor_full,
            0.5 * transistor_high,
            reverse,
            case.stop_ns,
            True,
        )
        row.update(
            {
                "native_recovery_50_ns": native_recovery,
                "transistor_recovery_50_ns": transistor_recovery,
                "recovery_50_delta_ns": native_recovery - transistor_recovery,
            }
        )
    return row


def write_readme(metrics: list[dict[str, object]]) -> None:
    by_case = {str(row["case_id"]): row for row in metrics}
    long = by_case["edge_1ps_base_50r_2pf"]
    high_1ns = by_case["short_pulse_1ns_high"]
    high_2ns = by_case["short_pulse_2ns_high"]
    low_1ns = by_case["short_pulse_1ns_low"]
    low_2ns = by_case["short_pulse_2ns_low"]
    rows = []
    for row in metrics:
        rows.append(
            f"| {row['case_id']} | {float(row['pad_rmse_mv']):.3f} | "
            f"{float(row['pad_max_error_mv']):.3f} | "
            f"{float(row['native_pad_min_v']):.4f} to {float(row['native_pad_max_v']):.4f} | "
            f"{float(row['transistor_pad_min_v']):.4f} to {float(row['transistor_pad_max_v']):.4f} |"
        )
    text = f"""# Corrected io_buf HSPICE Reference Waveforms

## Correct Reference Pair

- Native IBIS: `{FAST_IBIS.relative_to(ROOT)}`.
- Transistor source: `{IO_BUF_SP.relative_to(ROOT)}`.
- Original HSPICE MOS card: `{ORIGINAL_MODEL}`.
- Both flows are simulated by HSPICE.
- Runtime stimulus: 3.3 V, 1 ps command edges.
- Load: 50 ohm to ground in parallel with 2 pF.
- Supply: ideal 3.3 V in both flows.

The transistor gate-control traces are shown only as physical context. They are not numerically equivalent to native-IBIS `Ku/Kd`.

## Headline Finding

- Normal complete switching is aligned: native-IBIS versus transistor 50% timing differs by `{float(long['rise_50_delta_ps']):.1f} ps` on rise and `{float(long['fall_50_delta_ps']):.1f} ps` on fall.
- The 1 ns short-high output is tiny in both flows. Native IBIS peaks at `{float(high_1ns['native_pulse_peak_v']):.4f} V`; the transistor peaks at `{float(high_1ns['transistor_pulse_peak_v']):.4f} V`. Small absolute error here does not prove state agreement.
- The 2 ns short-high pulse has similar overall shape, with peaks of `{float(high_2ns['native_pulse_peak_v']):.4f} V` and `{float(high_2ns['transistor_pulse_peak_v']):.4f} V`.
- The 1 ns short-low case remains a real disagreement even with corrected sources. Native IBIS crosses 50% on recovery at `{float(low_1ns['native_recovery_50_ns']):.4f} ns`; the transistor crosses at `{float(low_1ns['transistor_recovery_50_ns']):.4f} ns`, a difference of `{abs(float(low_1ns['recovery_50_delta_ns'])):.4f} ns`.
- The 2 ns short-low case crosses 50% on recovery at `{float(low_2ns['native_recovery_50_ns']):.4f} ns` for native IBIS and `{float(low_2ns['transistor_recovery_50_ns']):.4f} ns` for the transistor, a difference of `{abs(float(low_2ns['recovery_50_delta_ns'])):.4f} ns`.

The corrected result therefore separates two issues. The earlier large complete-edge disagreement was a stale-reference problem. The remaining short-low disagreement is an interrupted-transition/history limitation of native IBIS table playback relative to the source transistor.

## Pad Comparison

| Case | RMSE (mV) | Max error (mV) | Native IBIS range (V) | Transistor range (V) |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

## Figures

- `figures/correct_pair_pad_contact_sheet.png`
- `figures/<case>/01_correct_pair_pad_overlay.png`
- `figures/<case>/02_internal_switching_context.png`

## Numeric Data

- `waveform_metrics.csv`
- `reference_cache_manifest.csv`
- `source_manifest.csv`
- `cases/<case>/aligned_correct_pair_waveforms.csv`

Every HSPICE flow retains its exact `.sp`, `.tr0`, `.lis`, and stdout log under `cases/`.
"""
    (OUT / "README.md").write_text(text, encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--timeout-s", type=int, default=180)
    parser.add_argument("--force-rerun", action="store_true")
    args = parser.parse_args()

    for path in [FAST_IBIS, IO_BUF_SP, ORIGINAL_MODEL, args.hspice]:
        if not path.exists():
            raise FileNotFoundError(path)
    for path in [OUT, CASES_DIR, FIGURES_DIR]:
        ensure_dir(path)

    source_rows = [
        {
            "role": "regenerated_5ps_ibis",
            "path": str(FAST_IBIS),
            "sha256": sha256(FAST_IBIS),
        },
        {
            "role": "transistor_netlist",
            "path": str(IO_BUF_SP),
            "sha256": sha256(IO_BUF_SP),
        },
        {
            "role": "original_hspice_model_card",
            "path": str(ORIGINAL_MODEL),
            "sha256": sha256(ORIGINAL_MODEL),
        },
    ]
    write_csv(OUT / "source_manifest.csv", source_rows)

    cache_rows: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    all_data: dict[str, dict[str, np.ndarray]] = {}
    for index, case in enumerate(CASES, start=1):
        print(f"[{index}/{len(CASES)}] {case.case_id}", flush=True)
        native, native_row = run_reference(
            case,
            "hspice_native_fast_ibis",
            args.hspice,
            args.timeout_s,
            args.force_rerun,
        )
        transistor, transistor_row = run_reference(
            case,
            "hspice_transistor_original",
            args.hspice,
            args.timeout_s,
            args.force_rerun,
        )
        cache_rows.extend([native_row, transistor_row])
        data = aligned_data(case, native, transistor)
        all_data[case.case_id] = data
        save_aligned_csv(case, data)
        plot_case(case, data)
        metrics.append(calculate_metrics(case, data))

    plot_contact_sheet(all_data)
    write_csv(OUT / "reference_cache_manifest.csv", cache_rows)
    write_csv(OUT / "waveform_metrics.csv", metrics)
    write_readme(metrics)
    print(OUT)


if __name__ == "__main__":
    main()
