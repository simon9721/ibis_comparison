#!/usr/bin/env python3
"""Inventory an IBIS folder and compare native HSPICE with legacy pybis/ngspice."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
for path in (LOCAL_DEPS, ROOT / "scripts", PYBIS_ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


from convert_ibis_to_pybis import convert  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from pybis2spice import pybis2spice  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


DEFAULT_SOURCE = Path(r"C:\Users\sh3qm\code\IBIS files")
DEFAULT_STUDY = ROOT / "results" / "external_ibis_full_swing_pilot_2026-08-07"
SUPPORTED_TYPES = {"output", "i/o", "3-state", "open_drain", "i/o_open_drain"}

PILOT_MODELS = {
    ("buffer.ibs", "driver"),
    ("hct1g08.ibs", "HCT1G08_OUTN_50"),
    ("invchain_test_0615_v5.ibs", "driver2"),
    ("io_buf.ibs", "driver"),
    ("io_buf_s_v32.ibs", "driver"),
    ("io_buf_s_v42.ibs", "driver"),
    ("sample1.ibs", "BPOZ2F"),
    ("sample1.ibs", "BPS2P10F_PU50K"),
    ("sample2.ibs", "O_SSTL2"),
    ("sample2.ibs", "XYZ123sstl3"),
    ("sn74lvc2t45.ibs", "LVC2T45_IO_A_33"),
    ("sn74lvc2t45.ibs", "LVC2T45_IO_B_18"),
    ("stm32g031_041_ufqfpn32.ibs", "iols8p_sudq_ft"),
    ("stm32g031_041_ufqfpn32.ibs", "iohs8p_sudq_ft"),
    ("stm32g031_041_ufqfpn32.ibs", "io6_ft_3v3_lowspeed"),
    ("stm32g031_041_ufqfpn32.ibs", "io6_ft_3v3_highspeed"),
}


@dataclass(frozen=True)
class Candidate:
    source_path: Path
    file_name: str
    declared_file_name: str
    component: str
    model: str
    model_type: str
    enable: str
    vcc: float
    pullup_ref: float
    pulldown_ref: float
    power_clamp_ref: float
    gnd_clamp_ref: float
    rising_waveforms: int
    falling_waveforms: int
    rise_settle_ns: float
    fall_settle_ns: float
    waveform_duration_ns: float
    sha256: str
    duplicate_group: str
    applicability: str
    reason: str

    @property
    def case_id(self) -> str:
        raw = f"{self.source_path.stem}__{self.model}"
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_")

    @property
    def rise_edge_ns(self) -> float:
        return 5.0

    @property
    def input_edge_ns(self) -> float:
        return 0.05

    @property
    def high_width_ns(self) -> float:
        return max(15.0, 1.25 * self.rise_settle_ns + 1.0)

    @property
    def fall_edge_ns(self) -> float:
        return self.rise_edge_ns + self.input_edge_ns + self.high_width_ns

    @property
    def stop_ns(self) -> float:
        return self.fall_edge_ns + self.input_edge_ns + max(10.0, 1.25 * self.fall_settle_ns + 1.0)

    @property
    def output_step_ns(self) -> float:
        # Legacy InputDriven uses a 10 ps delay-line edge detector. Keep at
        # least ten output steps across it, including for very slow IBIS data.
        return 0.001


def scalar_typical(value, default: float | None = None) -> float | None:
    if value is None:
        return default
    raw = getattr(value, "typical", value)
    try:
        result = float(raw)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def model_supply(model) -> float:
    for attr in ("voltage_range", "pullup_reference", "power_clamp_reference"):
        value = scalar_typical(getattr(model, attr, None))
        if value is not None and value > 0:
            return value
    name = str(model.name).lower()
    for token, value in (("1v2", 1.2), ("1v8", 1.8), ("2v5", 2.5), ("3v3", 3.3), ("5v0", 5.0)):
        if token in name:
            return value
    return 3.3


def waveform_timing(model) -> tuple[float, float, float]:
    """Estimate complete-transition settling from the actual IBIS V-t tables."""
    all_durations: list[float] = []

    def direction_settle(waveforms) -> float:
        settle_times: list[float] = []
        for waveform in waveforms or []:
            samples = np.asarray(waveform.table.samples, dtype=float)
            if samples.ndim != 2 or samples.shape[0] < 3 or samples.shape[1] < 2:
                continue
            t = samples[:, 0]
            y = samples[:, 1]
            finite = np.isfinite(t) & np.isfinite(y)
            t, y = t[finite], y[finite]
            if len(t) < 3:
                continue
            all_durations.append(float(t[-1] * 1e9))
            endpoint_count = max(3, min(20, len(y) // 20))
            initial = float(np.median(y[:endpoint_count]))
            final = float(np.median(y[-endpoint_count:]))
            tolerance = max(0.01 * abs(final - initial), 1e-6)
            outside = np.flatnonzero(np.abs(y - final) > tolerance)
            if len(outside):
                settle_index = min(int(outside[-1]) + 1, len(t) - 1)
                settle_times.append(float(t[settle_index] * 1e9))
            else:
                settle_times.append(0.0)
        return max(settle_times, default=0.0)

    rise_settle = direction_settle(model.rising_waveforms)
    fall_settle = direction_settle(model.falling_waveforms)
    return rise_settle, fall_settle, max(all_durations, default=0.0)


def applicability(model) -> tuple[str, str]:
    model_type = str(model.model_type).lower()
    rising = len(model.rising_waveforms or [])
    falling = len(model.falling_waveforms or [])
    if model_type in {"input", "input_ecl"}:
        return "SKIP_INPUT_ONLY", "input-only model"
    if model_type not in SUPPORTED_TYPES:
        return "SKIP_UNSUPPORTED_TYPE", f"legacy pybis does not support {model.model_type}"
    if model_type in {"open_drain", "i/o_open_drain"}:
        if rising < 1 or falling < 1:
            return "SKIP_MISSING_WAVEFORMS", "open-drain extraction requires rising and falling waveforms"
        if model_type == "i/o_open_drain":
            return "SKIP_UNSUPPORTED_TYPE", "legacy generator only recognizes open_drain, not i/o_open_drain"
        return "READY_OPEN_DRAIN", "requires a pullup-specific bench"
    if rising < 2 or falling < 2:
        return "SKIP_MISSING_WAVEFORMS", "push-pull extraction requires two rising and two falling waveform fixtures"
    return "READY_PUSH_PULL", "compatible output model with two waveform fixtures per direction"


def inventory(source_dir: Path) -> tuple[list[Candidate], list[dict[str, object]]]:
    files = sorted(source_dir.rglob("*.ibs"), key=lambda p: str(p).lower())
    hash_to_files: dict[str, list[str]] = {}
    hashes: dict[Path, str] = {}
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[path] = digest
        hash_to_files.setdefault(digest, []).append(path.name)

    candidates: list[Candidate] = []
    errors: list[dict[str, object]] = []
    for path in files:
        digest = hashes[path]
        duplicate_group = digest[:12] if len(hash_to_files[digest]) > 1 else ""
        source_text = path.read_text(encoding="latin-1", errors="replace")
        file_name_match = re.search(r"(?im)^\s*\[File\s+Name\]\s+([^|\r\n]+)", source_text)
        declared_file_name = Path(file_name_match.group(1).strip()).name if file_name_match else path.name
        try:
            parsed = pybis2spice.get_ibis_model_ecdtools(str(path))
        except Exception as exc:  # retain malformed corpus entries
            errors.append({"file": path.name, "status": "PARSE_FAIL", "error": str(exc)})
            continue
        components = pybis2spice.list_components(parsed)
        component = components[0] if components else ""
        for model in parsed.models:
            vcc = model_supply(model)
            status, reason = applicability(model)
            rise_settle_ns, fall_settle_ns, waveform_duration_ns = waveform_timing(model)
            candidates.append(
                Candidate(
                    source_path=path,
                    file_name=path.name,
                    declared_file_name=declared_file_name,
                    component=component,
                    model=str(model.name),
                    model_type=str(model.model_type),
                    enable=str(model.enable or ""),
                    vcc=vcc,
                    pullup_ref=scalar_typical(model.pullup_reference, vcc) or vcc,
                    pulldown_ref=scalar_typical(model.pulldown_reference, 0.0) or 0.0,
                    power_clamp_ref=scalar_typical(model.power_clamp_reference, vcc) or vcc,
                    gnd_clamp_ref=scalar_typical(model.gnd_clamp_reference, 0.0) or 0.0,
                    rising_waveforms=len(model.rising_waveforms or []),
                    falling_waveforms=len(model.falling_waveforms or []),
                    rise_settle_ns=rise_settle_ns,
                    fall_settle_ns=fall_settle_ns,
                    waveform_duration_ns=waveform_duration_ns,
                    sha256=digest,
                    duplicate_group=duplicate_group,
                    applicability=status,
                    reason=reason,
                )
            )
    return candidates, errors


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.stat().st_size:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def candidate_row(candidate: Candidate) -> dict[str, object]:
    return {
        "file": candidate.file_name,
        "declared_file_name": candidate.declared_file_name,
        "component": candidate.component,
        "model": candidate.model,
        "model_type": candidate.model_type,
        "enable": candidate.enable,
        "vcc_v": candidate.vcc,
        "pullup_ref_v": candidate.pullup_ref,
        "pulldown_ref_v": candidate.pulldown_ref,
        "power_clamp_ref_v": candidate.power_clamp_ref,
        "gnd_clamp_ref_v": candidate.gnd_clamp_ref,
        "rising_waveforms": candidate.rising_waveforms,
        "falling_waveforms": candidate.falling_waveforms,
        "rise_settle_ns": candidate.rise_settle_ns,
        "fall_settle_ns": candidate.fall_settle_ns,
        "waveform_duration_ns": candidate.waveform_duration_ns,
        "bench_high_width_ns": candidate.high_width_ns,
        "bench_fall_edge_ns": candidate.fall_edge_ns,
        "bench_stop_ns": candidate.stop_ns,
        "bench_output_step_ns": candidate.output_step_ns,
        "sha256": candidate.sha256,
        "duplicate_group": candidate.duplicate_group,
        "applicability": candidate.applicability,
        "reason": candidate.reason,
        "pilot_selected": (candidate.file_name, candidate.model) in PILOT_MODELS,
    }


def run_process(
    command: list[str],
    cwd: Path,
    log: Path,
    timeout_s: float,
    completion_file: Path | None = None,
    completion_text: str | None = None,
) -> tuple[int | None, float, str]:
    started = time.perf_counter()
    timed_out = False
    completed_by_sentinel = False
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        while proc.poll() is None:
            elapsed = time.perf_counter() - started
            if completion_file is not None and completion_file.exists() and completion_text:
                try:
                    completed_by_sentinel = completion_text.lower() in completion_file.read_text(
                        encoding="utf-8", errors="replace"
                    ).lower()
                except OSError:
                    completed_by_sentinel = False
                if completed_by_sentinel:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=2.0)
                    break
            if elapsed >= timeout_s:
                timed_out = True
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2.0)
                break
            time.sleep(0.1)
    output = log.read_text(encoding="utf-8", errors="replace")
    runtime = time.perf_counter() - started
    if timed_out:
        output += "\nTIMEOUT\n"
        log.write_text(output, encoding="utf-8", errors="replace")
        return None, runtime, output
    if completed_by_sentinel:
        return 0, runtime, output
    return proc.returncode, runtime, output


def hspice_deck(candidate: Candidate) -> str:
    model_type = candidate.model_type.lower()
    enable_v = 0.0 if "active-low" in candidate.enable.lower() else candidate.vcc
    if model_type == "output":
        instance_nodes = "pu_ref pd_ref pad_h in_dig pc_ref gc_ref"
        enable_source = ""
        digital_load = ""
    elif model_type == "3-state":
        instance_nodes = "pu_ref pd_ref pad_h in_dig en_sig pc_ref gc_ref"
        enable_source = f"Ven en_sig 0 DC {enable_v:.12g}\n"
        digital_load = ""
    elif model_type == "i/o":
        instance_nodes = "pu_ref pd_ref pad_h in_dig en_sig dig_q pc_ref gc_ref"
        enable_source = f"Ven en_sig 0 DC {enable_v:.12g}\n"
        digital_load = "Rdig dig_q 0 1k\n"
    else:
        raise ValueError(f"unsupported native HSPICE model type: {candidate.model_type}")
    return f"""* Generic full-transition native-IBIS comparison
.title {candidate.file_name} / {candidate.model}
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PULSE(0 {candidate.vcc:.12g} {candidate.rise_edge_ns:.12g}n {candidate.input_edge_ns:.12g}n {candidate.input_edge_ns:.12g}n {candidate.high_width_ns:.12g}n {2.0 * candidate.stop_ns:.12g}n)
{enable_source.rstrip()}
VPU pu_ref 0 DC {candidate.pullup_ref:.12g}
VPD pd_ref 0 DC {candidate.pulldown_ref:.12g}
VPC pc_ref 0 DC {candidate.power_clamp_ref:.12g}
VGC gc_ref 0 DC {candidate.gnd_clamp_ref:.12g}

BIBIS {instance_nodes}
+ file='{candidate.declared_file_name}'
+ model='{candidate.model}'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

{digital_load.rstrip()}
Rload pad_h 0 50
Cload pad_h 0 2p

.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran {candidate.output_step_ns:.12g}n {candidate.stop_ns:.12g}n
.end
"""


def ngspice_deck(candidate: Candidate, subckt_name: str) -> str:
    enable_v = 0.0 if "active-low" in candidate.enable.lower() else candidate.vcc
    return f"""* Generic full-transition legacy-pybis comparison
.title {candidate.file_name} / {candidate.model}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PULSE(0 {candidate.vcc:.12g} {candidate.rise_edge_ns:.12g}n {candidate.input_edge_ns:.12g}n {candidate.input_edge_ns:.12g}n {candidate.high_width_ns:.12g}n {2.0 * candidate.stop_ns:.12g}n)
Ven en_sig 0 DC {enable_v:.12g}
Vdd vdd 0 DC {candidate.vcc:.12g}

.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 {subckt_name}

Rload pad_n 0 50
Cload pad_n 0 2p

.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran {candidate.output_step_ns:.12g}n {candidate.stop_ns:.12g}n
.end
"""


def diagnose_pybis_extraction(candidate: Candidate, ibis_path: Path) -> str:
    """Return the first coefficient-solver failure hidden by the legacy generator."""
    try:
        ibis = pybis2spice.get_ibis_model_ecdtools(str(ibis_path))
        data_model = pybis2spice.DataModel(
            ibis,
            model_name=candidate.model,
            component_name=candidate.component,
        )
        for waveform_type in ("Rising", "Falling"):
            try:
                pybis2spice.solve_k_params_output(
                    data_model,
                    corner=1,
                    waveform_type=waveform_type,
                )
            except Exception as exc:
                return f"{waveform_type} coefficient extraction: {type(exc).__name__}: {exc}"
    except Exception as exc:
        return f"diagnostic setup: {type(exc).__name__}: {exc}"
    return "coefficient extraction completed; failure occurred during netlist generation"


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", ".").replace(" ", ""): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", ".").replace(" ", ""))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"missing {names}; available={sorted(data)}")


def extract_hspice(data: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "time": find_signal(data, "time"),
        "input": find_signal(data, "v(in_dig)", "in_dig"),
        "pad": find_signal(data, "v(pad_h)", "pad_h"),
        "ku": find_signal(data, "v(ku)", "ku"),
        "kd": find_signal(data, "v(kd)", "kd"),
    }


def extract_ngspice(data: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "time": find_signal(data, "time"),
        "input": find_signal(data, "v(in_dig)", "in_dig"),
        "pad": find_signal(data, "v(pad_n)", "pad_n"),
        "ku": find_signal(data, "v(xdrv.ku)", "xdrv.ku"),
        "kd": find_signal(data, "v(xdrv.kd)", "xdrv.kd"),
    }


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(a - b))))


def crossing_time(t: np.ndarray, y: np.ndarray, threshold: float, rising: bool, start: float, stop: float) -> float:
    mask = (t >= start) & (t <= stop)
    tx, yx = t[mask], y[mask]
    if len(tx) < 2:
        return math.nan
    hits = np.where((yx[:-1] <= threshold) & (yx[1:] > threshold))[0] if rising else np.where((yx[:-1] >= threshold) & (yx[1:] < threshold))[0]
    if not len(hits):
        return math.nan
    idx = int(hits[0])
    fraction = (threshold - yx[idx]) / (yx[idx + 1] - yx[idx]) if yx[idx + 1] != yx[idx] else 0.0
    return float(tx[idx] + fraction * (tx[idx + 1] - tx[idx]))


def compare(candidate: Candidate, h: dict[str, np.ndarray], n: dict[str, np.ndarray]) -> dict[str, object]:
    t = h["time"]
    rise_edge = candidate.rise_edge_ns * 1e-9
    fall_edge = candidate.fall_edge_ns * 1e-9
    stop = candidate.stop_ns * 1e-9
    eval_t = np.linspace(max(0.0, rise_edge - 1e-9), stop, 20001)
    h_eval = {key: np.interp(eval_t, t, value) for key, value in h.items() if key != "time"}
    n_eval = {key: np.interp(eval_t, n["time"], value) for key, value in n.items() if key != "time"}
    low_sample_time = max(0.0, rise_edge - 0.5e-9)
    high_margin = max(0.5e-9, min(5e-9, 0.05 * candidate.high_width_ns * 1e-9))
    high_sample_time = fall_edge - high_margin
    h_low = float(np.interp(low_sample_time, t, h["pad"]))
    h_high = float(np.interp(high_sample_time, t, h["pad"]))
    threshold = 0.5 * (h_low + h_high)
    h_rise = crossing_time(eval_t, h_eval["pad"], threshold, True, rise_edge - 0.5e-9, fall_edge - high_margin)
    n_rise = crossing_time(eval_t, n_eval["pad"], threshold, True, rise_edge - 0.5e-9, fall_edge - high_margin)
    h_fall = crossing_time(eval_t, h_eval["pad"], threshold, False, fall_edge - 0.5e-9, stop)
    n_fall = crossing_time(eval_t, n_eval["pad"], threshold, False, fall_edge - 0.5e-9, stop)
    pad_error = rmse(h_eval["pad"], n_eval["pad"])
    ku_error = rmse(h_eval["ku"], n_eval["ku"])
    kd_error = rmse(h_eval["kd"], n_eval["kd"])
    swing = max(abs(h_high - h_low), 1e-6)
    if pad_error <= 0.02 * swing and ku_error <= 0.05 and kd_error <= 0.05:
        comparison_class = "GOOD"
    elif pad_error <= 0.05 * swing and ku_error <= 0.10 and kd_error <= 0.10:
        comparison_class = "WARN"
    else:
        comparison_class = "CHECK"
    return {
        "comparison_class": comparison_class,
        "pad_rmse_mv": pad_error * 1e3,
        "pad_rmse_pct_swing": 100.0 * pad_error / swing,
        "ku_rmse": ku_error,
        "kd_rmse": kd_error,
        "hspice_low_v": h_low,
        "hspice_high_v": h_high,
        "hspice_swing_v": h_high - h_low,
        "ngspice_low_v": float(np.interp(low_sample_time, n["time"], n["pad"])),
        "ngspice_high_v": float(np.interp(high_sample_time, n["time"], n["pad"])),
        "rise_50_delta_ps": (n_rise - h_rise) * 1e12 if math.isfinite(h_rise) and math.isfinite(n_rise) else math.nan,
        "fall_50_delta_ps": (n_fall - h_fall) * 1e12 if math.isfinite(h_fall) and math.isfinite(n_fall) else math.nan,
        "hspice_ku_min": float(np.min(h_eval["ku"])),
        "hspice_ku_max": float(np.max(h_eval["ku"])),
        "hspice_kd_min": float(np.min(h_eval["kd"])),
        "hspice_kd_max": float(np.max(h_eval["kd"])),
        "ngspice_ku_min": float(np.min(n_eval["ku"])),
        "ngspice_ku_max": float(np.max(n_eval["ku"])),
        "ngspice_kd_min": float(np.min(n_eval["kd"])),
        "ngspice_kd_max": float(np.max(n_eval["kd"])),
    }


def plot_case(candidate: Candidate, h: dict[str, np.ndarray], n: dict[str, np.ndarray], output: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True, constrained_layout=True)
    ht, nt = h["time"] * 1e9, n["time"] * 1e9
    axes[0].plot(ht, h["pad"], color="black", lw=2.7, label="HSPICE native IBIS")
    axes[0].plot(nt, n["pad"], color="#0072B2", lw=1.9, label="ngspice legacy pybis")
    ax_input = axes[0].twinx()
    ax_input.plot(ht, h["input"], color="#888888", lw=1.0, alpha=0.55, label="input")
    ax_input.set_ylabel("input (V)", color="#666666")
    axes[0].set_ylabel("pad (V)")
    axes[0].legend(loc="best")
    axes[1].plot(ht, h["ku"], color="black", lw=2.7, label="HSPICE native IBIS")
    axes[1].plot(nt, n["ku"], color="#D55E00", lw=1.9, label="ngspice legacy pybis")
    axes[1].set_ylabel("Ku")
    axes[2].plot(ht, h["kd"], color="black", lw=2.7, label="HSPICE native IBIS")
    axes[2].plot(nt, n["kd"], color="#009E73", lw=1.9, label="ngspice legacy pybis")
    axes[2].axhline(0, color="#999999", lw=0.8)
    axes[2].set_ylabel("Kd")
    axes[2].set_xlabel("time (ns)")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.axvline(candidate.rise_edge_ns, color="#666666", ls="--", lw=1.0)
        ax.axvline(candidate.fall_edge_ns, color="#666666", ls="--", lw=1.0)
        ax.set_xlim(max(0.0, candidate.rise_edge_ns - 1.5), candidate.stop_ns)
    axes[1].legend(loc="best")
    axes[2].legend(loc="best")
    fig.suptitle(f"{candidate.file_name} | {candidate.model} | {candidate.model_type} | {candidate.vcc:g} V")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170)
    plt.close(fig)


def plot_summary(study: Path, results: list[dict[str, object]]) -> None:
    completed = [row for row in results if row.get("status") == "COMPLETED"]
    class_colors = {"GOOD": "#009E73", "WARN": "#E69F00", "CHECK": "#D55E00"}
    plots = study / "plots"
    plots.mkdir(parents=True, exist_ok=True)

    status_order = ["GOOD", "WARN", "CHECK", "NGSPICE_TIMEOUT", "CONVERSION_OR_ANALYSIS_FAIL"]
    status_counts = {
        "GOOD": sum(row.get("comparison_class") == "GOOD" for row in completed),
        "WARN": sum(row.get("comparison_class") == "WARN" for row in completed),
        "CHECK": sum(row.get("comparison_class") == "CHECK" for row in completed),
        "NGSPICE_TIMEOUT": sum(row.get("status") == "NGSPICE_TIMEOUT" for row in results),
        "CONVERSION_OR_ANALYSIS_FAIL": sum(row.get("status") == "CONVERSION_OR_ANALYSIS_FAIL" for row in results),
    }
    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
    colors = [class_colors.get(key, "#777777") for key in status_order]
    bars = ax.bar(["GOOD", "WARN", "CHECK", "ngspice\ntimeout", "conversion\nfail"], [status_counts[k] for k in status_order], color=colors)
    ax.bar_label(bars, padding=4, fontsize=12)
    ax.set_ylabel("model count")
    ax.set_title("Adaptive full-transition campaign outcomes")
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(plots / "summary_outcomes.png", dpi=180)
    plt.close(fig)

    if not completed:
        return
    fig, ax = plt.subplots(figsize=(13, 8), constrained_layout=True)
    for comparison_class in ("GOOD", "WARN", "CHECK"):
        rows = [row for row in completed if row.get("comparison_class") == comparison_class]
        if not rows:
            continue
        x = [max(float(row["pad_rmse_pct_swing"]), 1e-3) for row in rows]
        y = [max(float(row["ku_rmse"]), float(row["kd_rmse"]), 1e-4) for row in rows]
        ax.scatter(x, y, s=58, alpha=0.82, color=class_colors[comparison_class], label=f"{comparison_class} ({len(rows)})")
    ax.axvline(2.0, color="#666666", ls="--", lw=1.0)
    ax.axvline(5.0, color="#999999", ls=":", lw=1.0)
    ax.axhline(0.05, color="#666666", ls="--", lw=1.0)
    ax.axhline(0.10, color="#999999", ls=":", lw=1.0)
    for row in completed:
        if row.get("comparison_class") == "CHECK":
            ax.annotate(
                str(row["model"]),
                (max(float(row["pad_rmse_pct_swing"]), 1e-3), max(float(row["ku_rmse"]), float(row["kd_rmse"]), 1e-4)),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=8,
            )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("pad RMSE (% of HSPICE loaded swing)")
    ax.set_ylabel("max(Ku RMSE, Kd RMSE)")
    ax.set_title("Pad and coefficient agreement")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend()
    fig.savefig(plots / "summary_error_scatter.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 7), constrained_layout=True)
    for comparison_class in ("GOOD", "WARN", "CHECK"):
        rows = [row for row in completed if row.get("comparison_class") == comparison_class]
        ax.scatter(
            [float(row["bench_high_width_ns"]) for row in rows],
            [max(float(row["pad_rmse_pct_swing"]), 1e-3) for row in rows],
            s=55,
            alpha=0.82,
            color=class_colors[comparison_class],
            label=comparison_class,
        )
    ax.axvline(15.0, color="#666666", ls="--", lw=1.0, label="minimum 15 ns hold")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("model-adaptive high-pulse width (ns)")
    ax.set_ylabel("pad RMSE (% of HSPICE loaded swing)")
    ax.set_title("Agreement across fast and slow IBIS transitions")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend()
    fig.savefig(plots / "summary_timing_coverage.png", dpi=180)
    plt.close(fig)


def run_candidate(candidate: Candidate, study: Path, hspice: Path, ngspice: Path, timeout_s: float, resume: bool) -> dict[str, object]:
    case_dir = study / "cases" / candidate.case_id
    h_dir = case_dir / "hspice_native_ibis"
    n_dir = case_dir / "ngspice_legacy_pybis"
    h_dir.mkdir(parents=True, exist_ok=True)
    n_dir.mkdir(parents=True, exist_ok=True)
    local_ibis = h_dir / candidate.declared_file_name
    if not local_ibis.exists() or local_ibis.read_bytes() != candidate.source_path.read_bytes():
        shutil.copy2(candidate.source_path, local_ibis)
    h_deck = h_dir / "run.sp"
    h_deck.write_text(hspice_deck(candidate), encoding="ascii")
    h_tr0 = h_dir / "run.tr0"

    row: dict[str, object] = {
        **candidate_row(candidate),
        "case_id": candidate.case_id,
        "status": "PENDING",
        "hspice_deck": str(h_deck.relative_to(ROOT)),
        "ngspice_deck": "",
        "hspice_tr0": str(h_tr0.relative_to(ROOT)),
        "ngspice_raw": "",
        "plot": "",
    }
    try:
        if not (resume and h_tr0.exists()):
            for stale in (h_tr0, h_dir / "run.lis"):
                if stale.exists():
                    stale.unlink()
            rc, runtime, _ = run_process(
                [str(hspice), "-i", h_deck.name, "-o", "run"],
                h_dir,
                h_dir / "stdout.log",
                timeout_s,
                completion_file=h_dir / "run.lis",
                completion_text="job concluded",
            )
            row["hspice_runtime_s"] = runtime
            if rc is None:
                row.update(status="HSPICE_TIMEOUT", error="HSPICE timeout")
                return row
            if rc != 0 or not h_tr0.exists():
                row.update(status="HSPICE_FAIL", error=f"HSPICE return code {rc}")
                return row
        else:
            row["hspice_runtime_s"] = 0.0

        local_ng_ibis = n_dir / candidate.declared_file_name
        shutil.copy2(candidate.source_path, local_ng_ibis)
        (n_dir / ".spiceinit").write_text("set filetype=binary\n", encoding="ascii")
        subckt = n_dir / "legacy.sub"
        conversion_started = time.perf_counter()
        if not (resume and subckt.exists()):
            try:
                convert(local_ng_ibis, subckt, candidate.component, candidate.model, "Output", "InputDriven", "Typical")
            except RuntimeError as exc:
                detail = diagnose_pybis_extraction(candidate, local_ng_ibis)
                raise RuntimeError(f"{exc}; {detail}") from exc
        row["conversion_runtime_s"] = time.perf_counter() - conversion_started
        match = re.search(r"(?im)^\s*\.subckt\s+(\S+)", subckt.read_text(encoding="utf-8", errors="replace"))
        if not match:
            raise RuntimeError("generated model has no .subckt declaration")
        subckt_name = match.group(1)
        n_deck = n_dir / "run.sp"
        n_deck.write_text(ngspice_deck(candidate, subckt_name), encoding="ascii")
        n_raw = n_dir / "run.raw"
        row["ngspice_deck"] = str(n_deck.relative_to(ROOT))
        row["ngspice_raw"] = str(n_raw.relative_to(ROOT))
        if not (resume and n_raw.exists()):
            rc, runtime, _ = run_process([str(ngspice), "-b", "-r", n_raw.name, n_deck.name], n_dir, n_dir / "stdout.log", timeout_s)
            row["ngspice_runtime_s"] = runtime
            if rc is None:
                row.update(status="NGSPICE_TIMEOUT", error="ngspice timeout")
                return row
            if rc != 0 or not n_raw.exists():
                row.update(status="NGSPICE_FAIL", error=f"ngspice return code {rc}")
                return row
        else:
            row["ngspice_runtime_s"] = 0.0

        h = extract_hspice(parse_hspice_tr0(h_tr0))
        n = extract_ngspice(parse_ngspice_raw(n_raw))
        row.update(compare(candidate, h, n))
        plot_path = study / "plots" / f"{candidate.case_id}.png"
        plot_case(candidate, h, n, plot_path)
        row["plot"] = str(plot_path.relative_to(ROOT))
        row["status"] = "COMPLETED"
        row["error"] = ""
    except Exception as exc:
        row["status"] = "CONVERSION_OR_ANALYSIS_FAIL"
        row["error"] = f"{type(exc).__name__}: {exc}"
        (case_dir / "exception.txt").write_text(row["error"], encoding="utf-8")
    return row


def write_report(study: Path, candidates: list[Candidate], selected: list[Candidate], results: list[dict[str, object]], errors: list[dict[str, object]], profile: str) -> None:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.applicability] = counts.get(candidate.applicability, 0) + 1
    status_counts: dict[str, int] = {}
    class_counts: dict[str, int] = {}
    for row in results:
        status_counts[str(row.get("status", ""))] = status_counts.get(str(row.get("status", "")), 0) + 1
        if row.get("comparison_class"):
            class_counts[str(row["comparison_class"])] = class_counts.get(str(row["comparison_class"]), 0) + 1
    lines = [
        "# External IBIS Full-Transition Campaign",
        "",
        "This study inventories `C:\\Users\\sh3qm\\code\\IBIS files` and runs matched HSPICE native-IBIS versus ngspice legacy-pybis full transitions for selected compatible push-pull models.",
        "",
        "## Bench",
        "",
        "- Typical corner and model-derived supply/reference voltages.",
        "- Input: 50 ps rise/fall, rising at 5 ns.",
        "- High-pulse and recovery durations are model-adaptive: each is at least 125% of the 1%-settling time measured from the model's own IBIS V-t fixtures.",
        "- The output interval remains 1 ps because legacy pybis uses a 10 ps delay-line edge detector; ngspice raw files are binary to keep long runs manageable.",
        "- Load: `50 ohm || 2 pF` to ground.",
        "- HSPICE: native IBIS B-element with Ku/Kd probes.",
        "- ngspice: generated legacy `InputDriven` pybis subcircuit.",
        "- This is a complete-transition compatibility/correlation screen, not a short-pulse test.",
        "",
        "## Inventory",
        "",
        f"- Parsed model rows: `{len(candidates)}`; parse failures: `{len(errors)}`.",
    ]
    for key in sorted(counts):
        lines.append(f"- `{key}`: `{counts[key]}`")
    ready_count = counts.get("READY_PUSH_PULL", 0)
    if selected:
        lines.append(f"- Unique applicable models selected: `{len(selected)}` of `{ready_count}` (exact duplicate files suppressed).")
    lines.extend(["", f"## {profile.title()} Results", "", f"Selected models: `{len(selected)}`."])
    for key in sorted(status_counts):
        lines.append(f"- Run status `{key}`: `{status_counts[key]}`")
    for key in sorted(class_counts):
        lines.append(f"- Comparison class `{key}`: `{class_counts[key]}`")
    completed_count = status_counts.get("COMPLETED", 0)
    good_count = class_counts.get("GOOD", 0)
    if completed_count:
        lines.append(f"- `GOOD` share of completed comparisons: `{100.0 * good_count / completed_count:.1f}%`.")
    failures = [row for row in results if row.get("status") != "COMPLETED"]
    if failures:
        lines.extend(["", "## Explicit Failures", ""])
        for row in failures:
            lines.append(f"- `{row['file']} / {row['model']}`: `{row['status']}` - {row.get('error', '')}")
    file_summary: dict[str, dict[str, int]] = {}
    for row in results:
        entry = file_summary.setdefault(str(row.get("file", "")), {"GOOD": 0, "WARN": 0, "CHECK": 0, "FAIL": 0})
        comparison_class = str(row.get("comparison_class", ""))
        if row.get("status") == "COMPLETED" and comparison_class in entry:
            entry[comparison_class] += 1
        else:
            entry["FAIL"] += 1
    if file_summary:
        lines.extend([
            "",
            "## Results By File",
            "",
            "| File | GOOD | WARN | CHECK | Failed run |",
            "|---|---:|---:|---:|---:|",
        ])
        for file_name, values in sorted(file_summary.items()):
            lines.append(f"| {file_name} | {values['GOOD']} | {values['WARN']} | {values['CHECK']} | {values['FAIL']} |")
    lines.extend([
        "",
        "| File | Model | Type | VCC | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |",
        "|---|---|---|---:|---|---|---:|---:|---:|",
    ])
    for row in results:
        def fmt(key: str, digits: int) -> str:
            try:
                return f"{float(row[key]):.{digits}f}"
            except (KeyError, TypeError, ValueError):
                return "n/a"
        lines.append(
            f"| {row['file']} | {row['model']} | {row['model_type']} | {fmt('vcc_v', 2)} | "
            f"{row['status']} | {row.get('comparison_class', '')} | {fmt('pad_rmse_mv', 3)} | "
            f"{fmt('ku_rmse', 4)} | {fmt('kd_rmse', 4)} |"
        )
    lines.extend([
        "",
        "## Files",
        "",
        "- `inventory.csv`: every parsed model and explicit applicability reason.",
        "- `parse_errors.csv`: malformed/unparsed files, if any.",
        "- `selected_models.csv`: exact campaign selection.",
        "- `metrics.csv`: run status and waveform comparison metrics.",
        "- `cases/<case>/`: copied IBIS, generated pybis model, exact decks, logs, and raw outputs.",
        "- `plots/<case>.png`: pad, Ku, and Kd overlays.",
        "- `plots/summary_outcomes.png`: campaign counts.",
        "- `plots/summary_error_scatter.png`: pad error versus coefficient error.",
        "- `plots/summary_timing_coverage.png`: agreement versus required model settling time.",
        "- `FAILURE_INVESTIGATION.md`: retained root-cause analysis for the two incomplete comparisons.",
        "",
        "## Interpretation",
        "",
        "- `GOOD`: pad RMSE <= 2% of HSPICE loaded swing and both Ku/Kd RMSE <= 0.05.",
        "- `WARN`: pad RMSE <= 5% and both Ku/Kd RMSE <= 0.10, but the stricter gate was missed.",
        "- `CHECK`: at least one waveform or coefficient metric exceeds the WARN limits.",
        "- Timing deltas are reported in `metrics.csv` but are not used as a class gate in this first full-transition screen.",
        "- A failed run may mean unsupported IBIS content, pybis extraction limitations, or simulator compatibility. It is retained as evidence and is not silently removed.",
        "- The earlier fixed-15-ns campaign is preliminary only: it interrupted slow vendor transitions and must not be used as the full-swing conclusion.",
    ])
    (study / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--profile", choices=("inventory", "pilot", "all"), default="pilot")
    parser.add_argument("--max-models", type=int)
    parser.add_argument("--select-regex", help="Only run file/model pairs matching this regular expression")
    parser.add_argument("--timeout-s", type=float, default=240.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report-only", action="store_true", help="Regenerate figures/report from existing CSVs")
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    study = args.study_dir.resolve()
    study.mkdir(parents=True, exist_ok=True)
    candidates, errors = inventory(source_dir)
    write_csv(study / "inventory.csv", [candidate_row(c) for c in candidates])
    write_csv(study / "parse_errors.csv", errors)

    if args.report_only:
        results = read_csv(study / "metrics.csv")
        selected_rows = read_csv(study / "selected_models.csv")
        plot_summary(study, results)
        write_report(study, candidates, selected_rows, results, errors, args.profile)
        print(f"Regenerated report in {study}")
        return 0

    if args.profile == "inventory":
        write_report(study, candidates, [], [], errors, args.profile)
        print(f"Inventoried {len(candidates)} models in {study}")
        return 0

    ready = [c for c in candidates if c.applicability == "READY_PUSH_PULL"]
    if args.profile == "pilot":
        selected = [c for c in ready if (c.file_name, c.model) in PILOT_MODELS]
    else:
        canonical_by_hash: dict[str, str] = {}
        for candidate in ready:
            canonical_by_hash.setdefault(candidate.sha256, candidate.file_name)
        selected = [c for c in ready if c.file_name == canonical_by_hash[c.sha256]]
    if args.select_regex:
        selected_pattern = re.compile(args.select_regex, re.IGNORECASE)
        selected = [c for c in selected if selected_pattern.search(f"{c.file_name}/{c.model}")]
    if args.max_models is not None:
        selected = selected[: args.max_models]
    write_csv(study / "selected_models.csv", [candidate_row(c) for c in selected])

    if not args.hspice.exists():
        raise FileNotFoundError(f"HSPICE not found: {args.hspice}")
    if not args.ngspice.exists():
        raise FileNotFoundError(f"ngspice not found: {args.ngspice}")

    results: list[dict[str, object]] = []
    for index, candidate in enumerate(selected, 1):
        print(f"[{index}/{len(selected)}] {candidate.file_name} / {candidate.model}", flush=True)
        row = run_candidate(candidate, study, args.hspice, args.ngspice, args.timeout_s, args.resume)
        results.append(row)
        write_csv(study / "metrics.csv", results)
        print(f"  {row['status']} {row.get('comparison_class', '')} {row.get('error', '')}", flush=True)
    plot_summary(study, results)
    write_report(study, candidates, selected, results, errors, args.profile)
    print(f"Wrote {study}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
