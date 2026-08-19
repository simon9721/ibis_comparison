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


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import generate_io_buf_correct_hspice_reference_waveforms as refs  # noqa: E402
import run_io_buf_two_state_gate_model as gate_study  # noqa: E402
from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from spice_tool_paths import default_ngspice  # noqa: E402


OUT = ROOT / "results" / "io_buf_correct_hspice_vs_pybis_2026-07-23"
COMMON = OUT / "common"
CASES_DIR = OUT / "cases"
FIGURES_DIR = OUT / "figures"
HSPICE_RESULTS = (
    ROOT / "results" / "io_buf_correct_hspice_reference_waveforms_2026-07-23"
)


@dataclass(frozen=True)
class Variant:
    variant_id: str
    label: str
    subcircuit_type: str
    color: str
    linestyle: str


VARIANTS = [
    Variant(
        "legacy",
        "ngspice legacy pybis",
        "InputDriven",
        "#e68613",
        ":",
    ),
    Variant(
        "directional_residual",
        "ngspice two-state directional + residual",
        "InputDrivenTwoStateGateDirectionalResidualFull",
        "#d62728",
        "--",
    ),
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def make_ngspice_deck(case: refs.Case, variant: Variant) -> str:
    diagnostics = ""
    if variant.variant_id == "directional_residual":
        diagnostics = (
            " V(xdrv.gup) V(xdrv.gdn)"
            " V(xdrv.guptarget) V(xdrv.gdntarget)"
            " V(xdrv.kugate) V(xdrv.kdgate)"
            " V(xdrv.kdres) V(xdrv.gdnrate)"
        )
    return f"""* Corrected-reference pybis comparison
* Model generated from regenerated 5 ps io_buf.ibs
* Variant: {variant.subcircuit_type}
.title corrected HSPICE versus pybis {case.case_id} {variant.variant_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{refs.pwl_text(case)}

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){diagnostics}
.tran 0.001n {case.stop_ns:.6f}n
.end
"""


def generate_models() -> dict[str, Path]:
    ensure_dir(COMMON)
    models: dict[str, Path] = {}
    for variant in VARIANTS:
        path = COMMON / variant.variant_id / "driver_OutputInput_Typical.sub"
        convert_ibis_to_pybis(
            ibis_path=refs.FAST_IBIS,
            output_path=path,
            component_name="MCM Driver 1",
            model_name="driver",
            io_type="Output",
            subcircuit_type=variant.subcircuit_type,
            corner="Typical",
        )
        models[variant.variant_id] = path
    return models


def run_ngspice(
    case: refs.Case,
    variant: Variant,
    model: Path,
    ngspice: Path,
    timeout_s: int,
    force_rerun: bool,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    run_dir = CASES_DIR / case.case_id / f"ngspice_{variant.variant_id}"
    ensure_dir(run_dir)
    local_model = run_dir / "driver_OutputInput_Typical.sub"
    shutil.copy2(model, local_model)
    deck = run_dir / "run.sp"
    raw = run_dir / "run.raw"
    log = run_dir / "ngspice_stdout.log"
    signature_path = run_dir / "run_signature.txt"
    failed_signature_path = run_dir / "failed_signature.txt"
    deck_text = make_ngspice_deck(case, variant)
    deck.write_text(deck_text, encoding="ascii")
    signature = sha256_bytes(
        deck_text.encode("ascii") + local_model.read_bytes() + str(ngspice).encode("utf-8")
    )
    source = "run"
    if (
        not force_rerun
        and raw.exists()
        and log.exists()
        and signature_path.exists()
        and signature_path.read_text(encoding="ascii").strip() == signature
    ):
        source = "cache"
    elif (
        not force_rerun
        and failed_signature_path.exists()
        and failed_signature_path.read_text(encoding="ascii").strip() == signature
    ):
        raise RuntimeError(f"cached ngspice numeric failure: {run_dir}")
    elif (
        not force_rerun
        and raw.exists()
        and log.exists()
        and "TIMEOUT after" in log.read_text(encoding="utf-8", errors="replace")
    ):
        failed_signature_path.write_text(signature + "\n", encoding="ascii")
        raise RuntimeError(f"cached ngspice timeout: {run_dir}")
    else:
        try:
            completed = subprocess.run(
                [str(ngspice), "-b", "-r", raw.name, deck.name],
                cwd=run_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            log.write_text(
                f"TIMEOUT after {timeout_s} seconds\n\n{output}",
                encoding="utf-8",
            )
            failed_signature_path.write_text(signature + "\n", encoding="ascii")
            raise RuntimeError(f"ngspice timeout: {run_dir}") from exc
        log.write_text(completed.stdout, encoding="utf-8", errors="replace")
        if completed.returncode != 0 or not raw.exists():
            failed_signature_path.write_text(signature + "\n", encoding="ascii")
            raise RuntimeError(f"ngspice failed: {run_dir}; see {log}")
        signature_path.write_text(signature + "\n", encoding="ascii")
        if failed_signature_path.exists():
            failed_signature_path.unlink()
    return parse_ngspice_raw(raw), {
        "case_id": case.case_id,
        "flow": variant.variant_id,
        "source": source,
        "deck": str(deck.relative_to(ROOT)),
        "raw": str(raw.relative_to(ROOT)),
        "log": str(log.relative_to(ROOT)),
        "model": str(local_model.relative_to(ROOT)),
    }


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"Missing {names}; available: {sorted(data)}")


def optional_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray | None:
    try:
        return find_signal(data, *names)
    except KeyError:
        return None


def load_hspice_pair(
    case: refs.Case,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    native = parse_hspice_tr0(
        HSPICE_RESULTS
        / "cases"
        / case.case_id
        / "hspice_native_fast_ibis"
        / "run.tr0"
    )
    transistor = parse_hspice_tr0(
        HSPICE_RESULTS
        / "cases"
        / case.case_id
        / "hspice_transistor_original"
        / "run.tr0"
    )
    return native, transistor


def align_case(
    case: refs.Case,
    native: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
    ngspice_data: dict[str, dict[str, np.ndarray]],
) -> dict[str, np.ndarray]:
    time_ns = np.asarray(native["time"], dtype=float) * 1e9
    transistor_t = np.asarray(transistor["time"], dtype=float) * 1e9
    result: dict[str, np.ndarray] = {
        "time_ns": time_ns,
        "input_v": refs.input_values(case, time_ns),
        "native_pad_v": find_signal(native, "v(pad)"),
        "native_ku": find_signal(native, "v(ku)"),
        "native_kd": find_signal(native, "v(kd)"),
        "transistor_pad_v": np.interp(
            time_ns, transistor_t, find_signal(transistor, "v(pad)")
        ),
    }
    for variant in VARIANTS:
        if variant.variant_id not in ngspice_data:
            continue
        data = ngspice_data[variant.variant_id]
        source_t = np.asarray(data["time"], dtype=float) * 1e9
        result[f"{variant.variant_id}_pad_v"] = np.interp(
            time_ns, source_t, find_signal(data, "v(pad)")
        )
        result[f"{variant.variant_id}_ku"] = np.interp(
            time_ns,
            source_t,
            find_signal(data, "v(xdrv.ku)", "v(xdrv:ku)", "v(ku)"),
        )
        result[f"{variant.variant_id}_kd"] = np.interp(
            time_ns,
            source_t,
            find_signal(data, "v(xdrv.kd)", "v(xdrv:kd)", "v(kd)"),
        )
        for name in [
            "gup",
            "gdn",
            "guptarget",
            "gdntarget",
            "kugate",
            "kdgate",
            "kdres",
            "gdnrate",
        ]:
            signal = optional_signal(data, f"v(xdrv.{name})", f"v(xdrv:{name})")
            if signal is not None:
                result[f"{variant.variant_id}_{name}"] = np.interp(
                    time_ns, source_t, signal
                )
    return result


def save_aligned(case: refs.Case, data: dict[str, np.ndarray]) -> None:
    path = CASES_DIR / case.case_id / "aligned_correct_references_vs_pybis.csv"
    ensure_dir(path.parent)
    fields = list(data)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for values in zip(*(data[field] for field in fields)):
            writer.writerow([f"{float(value):.12g}" for value in values])


def active_mask(case: refs.Case, time_ns: np.ndarray) -> np.ndarray:
    x0, x1 = refs.case_window(case)
    return (time_ns >= x0) & (time_ns <= x1)


def score_case(case: refs.Case, data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    time_ns = data["time_ns"]
    mask = active_mask(case, time_ns)
    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        if f"{variant.variant_id}_pad_v" not in data:
            continue
        pad = data[f"{variant.variant_id}_pad_v"]
        ku = data[f"{variant.variant_id}_ku"]
        kd = data[f"{variant.variant_id}_kd"]
        native_pad_error = pad[mask] - data["native_pad_v"][mask]
        transistor_pad_error = pad[mask] - data["transistor_pad_v"][mask]
        ku_error = ku[mask] - data["native_ku"][mask]
        kd_error = kd[mask] - data["native_kd"][mask]
        row: dict[str, object] = {
            "case_id": case.case_id,
            "flow": variant.variant_id,
            "flow_label": variant.label,
            "pad_rmse_vs_native_mv": float(
                np.sqrt(np.mean(native_pad_error**2)) * 1e3
            ),
            "pad_max_vs_native_mv": float(np.max(np.abs(native_pad_error)) * 1e3),
            "pad_rmse_vs_transistor_mv": float(
                np.sqrt(np.mean(transistor_pad_error**2)) * 1e3
            ),
            "pad_max_vs_transistor_mv": float(
                np.max(np.abs(transistor_pad_error)) * 1e3
            ),
            "ku_rmse_vs_native": float(np.sqrt(np.mean(ku_error**2))),
            "ku_max_vs_native": float(np.max(np.abs(ku_error))),
            "kd_rmse_vs_native": float(np.sqrt(np.mean(kd_error**2))),
            "kd_max_vs_native": float(np.max(np.abs(kd_error))),
            "ku_min": float(np.min(ku[mask])),
            "ku_max": float(np.max(ku[mask])),
            "kd_min": float(np.min(kd[mask])),
            "kd_max": float(np.max(kd[mask])),
        }
        if case.pattern == "short_high":
            row["pad_peak_v"] = float(np.max(pad[mask]))
        if case.pattern == "short_low":
            high = float(np.median(pad[(time_ns >= 9.0) & (time_ns <= 9.8)]))
            reverse = 10.0 + case.pulse_width_ns
            row["recovery_50_ns"] = refs.crossing(
                time_ns,
                pad,
                0.5 * high,
                reverse,
                case.stop_ns,
                True,
            )
        rows.append(row)
    return rows


def add_edges(ax: plt.Axes, case: refs.Case) -> None:
    for edge in refs.edge_times(case):
        ax.axvline(edge, color="#888888", lw=1.0, ls="--", alpha=0.75)
    ax.grid(True, alpha=0.22)


def plot_case(case: refs.Case, data: dict[str, np.ndarray]) -> None:
    out = FIGURES_DIR / case.case_id
    ensure_dir(out)
    time_ns = data["time_ns"]
    x0, x1 = refs.case_window(case)

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(12.0, 7.0),
        sharex=True,
        gridspec_kw={"height_ratios": [0.8, 2.4]},
        constrained_layout=True,
    )
    axes[0].plot(time_ns, data["input_v"], color="#1f77b4", lw=2.0)
    axes[0].set_ylabel("input (V)")
    axes[0].set_title(case.label, loc="left", fontweight="bold")
    axes[1].plot(
        time_ns,
        data["native_pad_v"],
        color="#111111",
        lw=3.2,
        label="HSPICE native IBIS",
        zorder=2,
    )
    axes[1].plot(
        time_ns,
        data["transistor_pad_v"],
        color="#7f7f7f",
        lw=2.6,
        label="HSPICE source transistor",
        zorder=1,
    )
    for variant in VARIANTS:
        if f"{variant.variant_id}_pad_v" not in data:
            continue
        axes[1].plot(
            time_ns,
            data[f"{variant.variant_id}_pad_v"],
            color=variant.color,
            lw=2.0,
            ls=variant.linestyle,
            label=variant.label,
            zorder=3,
        )
    axes[1].set_ylabel("pad voltage (V)")
    axes[1].set_xlabel("time (ns)")
    axes[1].legend(loc="best", fontsize=9)
    for ax in axes:
        ax.set_xlim(x0, x1)
        add_edges(ax, case)
    fig.savefig(out / "01_all_flows_pad_overlay.png", dpi=180)
    plt.close(fig)

    algorithm = "directional_residual"
    fig, axes = plt.subplots(3, 1, figsize=(12.0, 9.0), sharex=True, constrained_layout=True)
    panels = [
        ("pad_v", "pad voltage (V)", None),
        ("ku", "Ku", 0.0),
        ("kd", "Kd", 0.0),
    ]
    for ax, (suffix, ylabel, zero) in zip(axes, panels):
        ax.plot(
            time_ns,
            data[f"native_{suffix}"],
            color="#111111",
            lw=3.0,
            label="HSPICE native IBIS",
        )
        if f"{algorithm}_{suffix}" in data:
            ax.plot(
                time_ns,
                data[f"{algorithm}_{suffix}"],
                color="#d62728",
                lw=2.1,
                ls="--",
                label="ngspice directional + residual",
            )
        else:
            ax.text(
                0.98,
                0.88,
                "directional-residual: NUMERIC FAIL",
                transform=ax.transAxes,
                ha="right",
                va="top",
                color="#d62728",
                fontsize=10,
                fontweight="bold",
            )
        if zero is not None:
            ax.axhline(zero, color="#777777", lw=0.8)
        ax.set_ylabel(ylabel)
        ax.set_xlim(x0, x1)
        add_edges(ax, case)
    axes[0].set_title(
        f"{case.label}: coefficient-correctness comparison",
        loc="left",
        fontweight="bold",
    )
    axes[0].legend(loc="best")
    axes[-1].set_xlabel("time (ns)")
    fig.savefig(out / "02_algorithm_vs_hspice_native_ibis.png", dpi=180)
    plt.close(fig)

    legacy = "legacy"
    fig, axes = plt.subplots(3, 1, figsize=(12.0, 9.0), sharex=True, constrained_layout=True)
    for ax, (suffix, ylabel, zero) in zip(axes, panels):
        ax.plot(
            time_ns,
            data[f"native_{suffix}"],
            color="#111111",
            lw=3.0,
            label="HSPICE native IBIS",
        )
        if f"{legacy}_{suffix}" in data:
            ax.plot(
                time_ns,
                data[f"{legacy}_{suffix}"],
                color="#e68613",
                lw=2.1,
                ls=":",
                label="ngspice legacy pybis",
            )
        if zero is not None:
            ax.axhline(zero, color="#777777", lw=0.8)
        ax.set_ylabel(ylabel)
        ax.set_xlim(x0, x1)
        add_edges(ax, case)
    axes[0].set_title(
        f"{case.label}: legacy coefficient playback",
        loc="left",
        fontweight="bold",
    )
    axes[0].legend(loc="best")
    axes[-1].set_xlabel("time (ns)")
    fig.savefig(out / "04_legacy_vs_hspice_native_ibis.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(12.0, 7.0),
        sharex=True,
        gridspec_kw={"height_ratios": [0.8, 2.4]},
        constrained_layout=True,
    )
    axes[0].plot(time_ns, data["input_v"], color="#1f77b4", lw=2.0)
    axes[0].set_ylabel("input (V)")
    axes[0].set_title(
        f"{case.label}: transistor-truth pad comparison",
        loc="left",
        fontweight="bold",
    )
    axes[1].plot(
        time_ns,
        data["transistor_pad_v"],
        color="#111111",
        lw=3.1,
        label="HSPICE source transistor",
    )
    if f"{algorithm}_pad_v" in data:
        axes[1].plot(
            time_ns,
            data[f"{algorithm}_pad_v"],
            color="#d62728",
            lw=2.1,
            ls="--",
            label="ngspice directional + residual",
        )
    else:
        axes[1].text(
            0.98,
            0.88,
            "directional-residual: NUMERIC FAIL",
            transform=axes[1].transAxes,
            ha="right",
            va="top",
            color="#d62728",
            fontsize=10,
            fontweight="bold",
        )
    axes[1].set_ylabel("pad voltage (V)")
    axes[1].set_xlabel("time (ns)")
    axes[1].legend(loc="best")
    for ax in axes:
        ax.set_xlim(x0, x1)
        add_edges(ax, case)
    fig.savefig(out / "03_algorithm_vs_hspice_transistor.png", dpi=180)
    plt.close(fig)


def plot_contact_sheet(all_data: dict[str, dict[str, np.ndarray]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.0, 8.5), constrained_layout=True)
    for ax, case in zip(axes.flat, refs.CASES):
        data = all_data[case.case_id]
        time_ns = data["time_ns"]
        ax.plot(
            time_ns,
            data["native_pad_v"],
            color="#111111",
            lw=2.8,
            label="HSPICE native IBIS",
        )
        ax.plot(
            time_ns,
            data["transistor_pad_v"],
            color="#7f7f7f",
            lw=2.3,
            label="HSPICE transistor",
        )
        if "directional_residual_pad_v" in data:
            ax.plot(
                time_ns,
                data["directional_residual_pad_v"],
                color="#d62728",
                lw=1.9,
                ls="--",
                label="ngspice directional + residual",
            )
        else:
            ax.text(
                0.98,
                0.90,
                "algorithm: NUMERIC FAIL",
                transform=ax.transAxes,
                ha="right",
                va="top",
                color="#d62728",
                fontsize=9,
                fontweight="bold",
            )
        ax.set_xlim(*refs.case_window(case))
        ax.set_title(case.label, loc="left", fontweight="bold")
        ax.set_xlabel("time (ns)")
        ax.set_ylabel("pad voltage (V)")
        add_edges(ax, case)
    axes[0, 0].legend(loc="best", fontsize=8.5)
    fig.savefig(FIGURES_DIR / "algorithm_vs_correct_references_contact_sheet.png", dpi=180)
    plt.close(fig)


def reconstruction_gate() -> tuple[list[dict[str, object]], dict[str, object]]:
    kr, kf, fit = gate_study.load_io_buf_k_tables(refs.FAST_IBIS)
    rows, data = gate_study.reconstruction_rows_and_data(kr, kf, fit)
    selected = [row for row in rows if row["candidate"] == "directional_residual"]
    summary: dict[str, object] = {
        "candidate": "directional_residual",
        "worst_rmse": max(float(row["rmse"]) for row in selected),
        "worst_max_error": max(float(row["max_error"]) for row in selected),
        "gate": (
            "PASS"
            if max(float(row["rmse"]) for row in selected) <= 0.02
            and max(float(row["max_error"]) for row in selected) <= 0.08
            else "FAIL"
        ),
        "ku_off": fit["ku_off"],
        "ku_on": fit["ku_on"],
        "kd_off": fit["kd_off"],
        "kd_on": fit["kd_on"],
    }

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.2), constrained_layout=True)
    specs = [
        ("tr", "ku_rise", "Ku rising"),
        ("tf", "ku_fall", "Ku falling"),
        ("tr", "kd_rise", "Kd rising"),
        ("tf", "kd_fall", "Kd falling"),
    ]
    for ax, (time_key, prefix, title) in zip(axes.flat, specs):
        ax.plot(
            data[time_key],
            data[f"{prefix}_orig"],
            color="#111111",
            lw=3.0,
            label="corrected IBIS coefficient table",
        )
        ax.plot(
            data[time_key],
            data[f"{prefix}_directional_residual"],
            color="#d62728",
            lw=2.0,
            ls="--",
            label="directional-residual reconstruction",
        )
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("table time (ns)")
        ax.set_ylabel(prefix.split("_")[0].upper())
        ax.grid(True, alpha=0.22)
    axes[0, 0].legend(loc="best", fontsize=8.5)
    fig.suptitle(
        f"Corrected 5 ps IBIS reconstruction gate: {summary['gate']}",
        fontweight="bold",
    )
    fig.savefig(FIGURES_DIR / "fast_ibis_reconstruction_gate.png", dpi=180)
    plt.close(fig)
    return rows, summary


def write_readme(
    metrics: list[dict[str, object]],
    gate_summary: dict[str, object],
    run_rows: list[dict[str, object]],
) -> None:
    by_key = {(str(row["case_id"]), str(row["flow"])): row for row in metrics}
    with (HSPICE_RESULTS / "waveform_metrics.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        reference_by_case = {
            row["case_id"]: row for row in csv.DictReader(handle)
        }
    lines = []
    for case in refs.CASES:
        for variant in VARIANTS:
            row = by_key.get((case.case_id, variant.variant_id))
            if row is None:
                lines.append(
                    f"| {case.case_id} | {variant.variant_id} | "
                    "NUMERIC FAIL | NUMERIC FAIL | NUMERIC FAIL | NUMERIC FAIL |"
                )
            else:
                lines.append(
                    f"| {case.case_id} | {variant.variant_id} | "
                    f"{float(row['pad_rmse_vs_native_mv']):.3f} | "
                    f"{float(row['pad_rmse_vs_transistor_mv']):.3f} | "
                    f"{float(row['ku_rmse_vs_native']):.5f} | "
                    f"{float(row['kd_rmse_vs_native']):.5f} |"
                )
    def metric(case_id: str, flow: str, field: str) -> str:
        row = by_key.get((case_id, flow))
        if row is None:
            return "n/a"
        return f"{float(row[field]):.5f}"

    failures = [
        row
        for row in run_rows
        if str(row.get("status", "completed")) != "completed"
    ]
    failure_text = ", ".join(
        f"{row['case_id']} ({row.get('failure_reason', 'failed')})"
        for row in failures
    ) or "none"
    normal_legacy = by_key[("edge_1ps_base_50r_2pf", "legacy")]
    short_high_legacy = by_key[("short_pulse_1ns_high", "legacy")]
    short_low_legacy = by_key[("short_pulse_1ns_low", "legacy")]
    high_reference = reference_by_case["short_pulse_1ns_high"]
    low_reference = reference_by_case["short_pulse_1ns_low"]
    low_recovery_delta_ps = (
        float(short_low_legacy["recovery_50_ns"])
        - float(low_reference["transistor_recovery_50_ns"])
    ) * 1e3
    text = f"""# Corrected HSPICE References versus pybis

## Setup

- Both pybis models were regenerated from `{refs.FAST_IBIS.relative_to(ROOT)}`.
- Legacy baseline: `InputDriven`.
- Current best structural method: `InputDrivenTwoStateGateDirectionalResidualFull`.
- HSPICE native-IBIS and original-transistor references are reused from `{HSPICE_RESULTS.relative_to(ROOT)}`.
- No HSPICE simulations are rerun by this comparison script.
- Common runtime setup: 3.3 V, 1 ps command edges, ideal 3.3 V supply, 50 ohm || 2 pF.

## Headline Finding

- The directional-residual model fails the corrected-file offline reconstruction gate: worst RMSE `{float(gate_summary['worst_rmse']):.5f}`, worst max error `{float(gate_summary['worst_max_error']):.5f}`, verdict `{gate_summary['gate']}`.
- Its inferred endpoint states are not settled logic states: `Ku off/on = {float(gate_summary['ku_off']):.4f}/{float(gate_summary['ku_on']):.4f}` and `Kd off/on = {float(gate_summary['kd_off']):.4f}/{float(gate_summary['kd_on']):.4f}`.
- Legacy pybis still reproduces the normal pad well: `{float(normal_legacy['pad_rmse_vs_native_mv']):.1f} mV` RMSE versus native IBIS and `{float(normal_legacy['pad_rmse_vs_transistor_mv']):.1f} mV` versus the transistor.
- Legacy pybis fails the 1 ns short-high pulse: it peaks at `{float(short_high_legacy['pad_peak_v']):.3f} V`, while corrected native IBIS and transistor references peak at `{float(high_reference['native_pulse_peak_v']):.3f} V` and `{float(high_reference['transistor_pulse_peak_v']):.3f} V`.
- In the 1 ns short-low case, legacy pybis follows the transistor pad much better than native IBIS does: `{float(short_low_legacy['pad_rmse_vs_transistor_mv']):.1f} mV` RMSE and recovery only `{low_recovery_delta_ps:+.1f} ps` from the transistor. Its Ku/Kd still disagree with native-IBIS playback, so this is transistor-pad agreement, not coefficient agreement.
- For 1 ns short-high, native-IBIS Ku/Kd RMSE is legacy `{metric('short_pulse_1ns_high', 'legacy', 'ku_rmse_vs_native')}/{metric('short_pulse_1ns_high', 'legacy', 'kd_rmse_vs_native')}` versus directional-residual `{metric('short_pulse_1ns_high', 'directional_residual', 'ku_rmse_vs_native')}/{metric('short_pulse_1ns_high', 'directional_residual', 'kd_rmse_vs_native')}`. These algorithm values are diagnostic only because the reconstruction gate failed.
- Directional-residual transient failures: `{failure_text}`.
- The transistor-reference pad score is reported independently. A pybis model can agree with native IBIS coefficients while still missing transistor history, or move toward transistor behavior while disagreeing with native table playback.

## Metrics

| Case | Flow | Pad RMSE vs native (mV) | Pad RMSE vs transistor (mV) | Ku RMSE vs native | Kd RMSE vs native |
|---|---|---:|---:|---:|---:|
{chr(10).join(lines)}

## Figures

- `figures/algorithm_vs_correct_references_contact_sheet.png`
- `figures/fast_ibis_reconstruction_gate.png`
- `figures/<case>/01_all_flows_pad_overlay.png`
- `figures/<case>/02_algorithm_vs_hspice_native_ibis.png`
- `figures/<case>/03_algorithm_vs_hspice_transistor.png`
- `figures/<case>/04_legacy_vs_hspice_native_ibis.png`

## Numeric Data

- `comparison_metrics.csv`
- `fast_ibis_reconstruction_metrics.csv`
- `fast_ibis_reconstruction_summary.csv`
- `ngspice_run_manifest.csv`
- `model_manifest.csv`
- `cases/<case>/aligned_correct_references_vs_pybis.csv`

Each ngspice run retains its exact generated model, deck, raw output, and log.
"""
    (OUT / "README.md").write_text(text, encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    parser.add_argument("--timeout-s", type=int, default=180)
    parser.add_argument("--force-rerun", action="store_true")
    args = parser.parse_args()

    for path in [refs.FAST_IBIS, HSPICE_RESULTS, args.ngspice]:
        if not path.exists():
            raise FileNotFoundError(path)
    for path in [OUT, COMMON, CASES_DIR, FIGURES_DIR]:
        ensure_dir(path)

    models = generate_models()
    write_csv(
        OUT / "model_manifest.csv",
        [
            {
                "variant": variant.variant_id,
                "subcircuit_type": variant.subcircuit_type,
                "source_ibis": str(refs.FAST_IBIS),
                "source_ibis_sha256": sha256_file(refs.FAST_IBIS),
                "generated_model": str(models[variant.variant_id]),
                "generated_model_sha256": sha256_file(models[variant.variant_id]),
            }
            for variant in VARIANTS
        ],
    )

    reconstruction_rows, gate_summary = reconstruction_gate()
    write_csv(OUT / "fast_ibis_reconstruction_metrics.csv", reconstruction_rows)
    write_csv(OUT / "fast_ibis_reconstruction_summary.csv", [gate_summary])

    run_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    all_data: dict[str, dict[str, np.ndarray]] = {}
    for index, case in enumerate(refs.CASES, start=1):
        print(f"[{index}/{len(refs.CASES)}] {case.case_id}", flush=True)
        native, transistor = load_hspice_pair(case)
        ngspice_data: dict[str, dict[str, np.ndarray]] = {}
        for variant in VARIANTS:
            try:
                data, run_row = run_ngspice(
                    case,
                    variant,
                    models[variant.variant_id],
                    args.ngspice,
                    args.timeout_s,
                    args.force_rerun,
                )
                run_row["status"] = "completed"
                ngspice_data[variant.variant_id] = data
                run_rows.append(run_row)
            except RuntimeError as exc:
                run_dir = CASES_DIR / case.case_id / f"ngspice_{variant.variant_id}"
                run_rows.append(
                    {
                        "case_id": case.case_id,
                        "flow": variant.variant_id,
                        "source": "run",
                        "status": "failed",
                        "failure_reason": str(exc),
                        "deck": str((run_dir / "run.sp").relative_to(ROOT)),
                        "raw": str((run_dir / "run.raw").relative_to(ROOT)),
                        "log": str((run_dir / "ngspice_stdout.log").relative_to(ROOT)),
                        "model": str(
                            (run_dir / "driver_OutputInput_Typical.sub").relative_to(ROOT)
                        ),
                    }
                )
        aligned = align_case(case, native, transistor, ngspice_data)
        all_data[case.case_id] = aligned
        save_aligned(case, aligned)
        metric_rows.extend(score_case(case, aligned))
        plot_case(case, aligned)

    plot_contact_sheet(all_data)
    write_csv(OUT / "ngspice_run_manifest.csv", run_rows)
    write_csv(OUT / "comparison_metrics.csv", metric_rows)
    write_readme(metric_rows, gate_summary, run_rows)
    print(OUT)


if __name__ == "__main__":
    main()
