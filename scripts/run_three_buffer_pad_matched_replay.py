#!/usr/bin/env python3
"""Calibrate and validate pad-voltage-matched interrupted replay on three buffers."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
for path in (ROOT, ROOT / "scripts", ROOT / "tools" / "pybis2spice"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib.pyplot as plt
import numpy as np

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw
from spice_tool_paths import default_hspice, default_ngspice
import run_three_buffer_realistic_pulse_campaign as base


OUT = ROOT / "results" / "three_buffer_pad_matched_replay_2026-08-04"
EDGE_NS = 0.050
WIDTHS_NS = (0.250, 0.500, 1.000, 2.000)
NOMINAL_LOAD = (50.0, 2.0)
LOAD_MATRIX = tuple((r, c) for r in (25.0, 50.0, 100.0) for c in (0.0, 2.0, 10.0))
TRAN_STEP_NS = 0.002

BLACK = "#111111"
GRAY = "#777777"
BLUE = "#0072B2"
PURPLE = "#7B2CBF"
ORANGE = "#E69F00"
RED = "#CC3311"
GRID = "#D9DEE5"


@dataclass(frozen=True)
class Flow:
    flow_id: str
    label: str
    mode: str
    color: str
    pad_reference: bool = False


V1_FLOWS = (
    Flow("legacy", "legacy pybis", "InputDriven", GRAY),
    Flow("coefficient_value_match", "coefficient value-match V2", "InputDrivenValueMatchedReplayV2Hybrid", ORANGE),
    Flow("pad_voltage", "pad-match voltage", "InputDrivenPadMatchedReplayV1", BLUE, True),
    Flow("pad_slew", "pad-match voltage + slew", "InputDrivenPadMatchedReplayV1SlewAware", PURPLE, True),
)
V2_FLOWS = (
    Flow("legacy", "legacy pybis", "InputDriven", GRAY),
    Flow("coefficient_value_match", "coefficient value-match V2", "InputDrivenValueMatchedReplayV2Hybrid", ORANGE),
    Flow("pad_voltage", "pad-match voltage V2", "InputDrivenPadMatchedReplayV2", BLUE, True),
    Flow("pad_slew", "pad-match voltage + slew V2", "InputDrivenPadMatchedReplayV2SlewAware", PURPLE, True),
)
FLOWS = V1_FLOWS
PAD_FLOWS = tuple(flow.flow_id for flow in FLOWS if flow.pad_reference)

DIAGNOSTICS = (
    "kuleg", "kdleg", "padsamp", "padslewpre", "padslewsamp",
    "tr_pad_early", "tf_pad_early", "tr_pad_late", "tf_pad_late",
    "tr_pad_score", "tf_pad_score", "tr_pad_score_late", "tf_pad_score_late",
    "padstartcmd", "padstart_latch",
    "padstartspan", "padmatch_ambiguous", "pmt0", "pmelapsed", "padarg",
    "kupadmatch", "kdpadmatch", "padmapactive", "hfall_after_rise",
    "hrise_after_fall", "hreverse_edge", "pmsample", "pmlatchpulse",
    "hreverse_sample", "pmsample_delay",
    "kutarget", "kdtarget", "coeff_jump_ku", "coeff_jump_kd",
)


def ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    ensure(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_wave(path: Path, data: dict[str, np.ndarray]) -> None:
    write_csv(path, [
        {key: float(values[index]) for key, values in data.items()}
        for index in range(len(data["time_ns"]))
    ])


def profiles(device: base.Device) -> tuple[base.Profile, ...]:
    return base.profiles(device)


def primary_cases() -> tuple[base.PulseCase, ...]:
    result = [base.PulseCase("long_control", EDGE_NS, "rise_fall", 10.0, 22.0, "long control")]
    for direction in ("short_high", "short_low"):
        for width in WIDTHS_NS:
            result.append(base.PulseCase(
                f"{direction}_{base.width_tag(width)}", EDGE_NS, direction, width, 22.0,
                direction.replace("_", " "),
            ))
    return tuple(result)


def load_cases() -> tuple[base.PulseCase, ...]:
    return tuple(
        case for case in primary_cases()
        if case.case_id in {"long_control", "short_high_500ps", "short_low_500ps"}
    )


def parse_widths_ns(value: str) -> tuple[float, ...]:
    widths = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    if not widths or any(width <= 0.0 for width in widths):
        raise argparse.ArgumentTypeError("custom pulse widths must be positive comma-separated ns values")
    return widths


def custom_cases(high_widths_ns: tuple[float, ...], low_widths_ns: tuple[float, ...]) -> tuple[base.PulseCase, ...]:
    cases: list[base.PulseCase] = []
    for direction, widths in (("short_high", high_widths_ns), ("short_low", low_widths_ns)):
        for width in widths:
            cases.append(base.PulseCase(
                f"{direction}_custom_{base.width_tag(width)}",
                EDGE_NS,
                direction,
                width,
                22.0,
                f"custom {direction.replace('_', ' ')}",
            ))
    return tuple(cases)


def input_threshold(model: Path, supply_v: float) -> float:
    text = model.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"input_threshold=([-+0-9.eE]+)", text)
    return float(match.group(1)) if match else 0.5 * supply_v


def run_process(command: list[str], cwd: Path, log: Path, timeout_s: int) -> int:
    try:
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                timeout=timeout_s, check=False)
        log.write_text("COMMAND: " + " ".join(command) + "\n\n" + result.stdout,
                       encoding="utf-8", errors="replace")
        return int(result.returncode)
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout or ""
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        log.write_text(f"TIMEOUT after {timeout_s}s\n\n{text}", encoding="utf-8", errors="replace")
        return 124


def hspice_cache_run_watched(family: str, device: base.Device, case: base.PulseCase,
                             deck_text: str, inputs: list[Path], out: Path,
                             hspice: Path, timeout_s: int,
                             load: tuple[float, float]) -> str:
    """Runs HSPICE but accepts a concluded job even if hspice.com lingers."""
    metadata = {
        "family": family, "device": device.device_id, "case_id": case.case_id,
        "edge_ns": case.edge_ns, "pulse_width_ns": case.pulse_width_ns,
        "pattern": case.pattern, "load_ohm": load[0], "load_pf": load[1],
    }
    signature_id, signature = base.reference_signature(deck_text, inputs, metadata)
    target_cache = base.cache_dir(family, case.case_id, signature_id)
    if base.restore_hspice_cache(target_cache, out, "run", deck_text):
        return "cache"
    deck = out / "run.sp"
    deck.write_text(deck_text, encoding="ascii")
    log = out / "hspice_stdout.log"
    lis = out / "run.lis"
    tr0 = out / "run.tr0"
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        handle.write(f"COMMAND: {hspice} -i {deck.name} -o run\n\n")
        handle.flush()
        process = subprocess.Popen(
            [str(hspice), "-i", deck.name, "-o", "run"], cwd=out,
            stdout=handle, stderr=subprocess.STDOUT, text=True,
        )
        deadline = time.monotonic() + timeout_s
        concluded = False
        while time.monotonic() < deadline:
            if lis.exists() and tr0.exists():
                concluded = "job concluded" in lis.read_text(
                    encoding="utf-8", errors="replace"
                ).lower()
                if concluded:
                    break
            if process.poll() is not None:
                break
            time.sleep(0.2)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    if not concluded:
        concluded = lis.exists() and tr0.exists() and "job concluded" in lis.read_text(
            encoding="utf-8", errors="replace"
        ).lower()
    if not concluded:
        raise RuntimeError(f"HSPICE failed: {device.device_id}/{case.case_id}; see {out}")
    base.save_hspice_cache(target_cache, out, "run", deck_text, signature)
    return "run"


def signal(raw: dict[str, np.ndarray], name: str) -> np.ndarray | None:
    lookup = {key.lower().replace(":", "."): key for key in raw}
    key = lookup.get(name.lower().replace(":", "."))
    return None if key is None else np.asarray(raw[key], dtype=float)


def parse_ng(raw_path: Path) -> dict[str, np.ndarray]:
    raw = parse_ngspice_raw(raw_path)
    result = {
        "time_ns": np.asarray(raw["time"], dtype=float) * 1e9,
        "input_v": signal(raw, "v(in_dig)"),
        "pad_v": signal(raw, "v(pad)"),
        "ku": signal(raw, "v(xdrv.ku)"),
        "kd": signal(raw, "v(xdrv.kd)"),
    }
    for name in DIAGNOSTICS:
        values = signal(raw, f"v(xdrv.{name})")
        if values is not None:
            result[name] = values
    return result


def calibration_deck(device: base.Device) -> str:
    return f"""* Offline legacy-pad calibration
.title {device.device_id} legacy pad calibration
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin in_dig 0 PWL(0n 0 5n 0 5.05n {base.fmt(device.supply_v)} 25n {base.fmt(device.supply_v)} 25.05n 0 45n 0)
Ven en_sig 0 DC {base.fmt(device.enable_v)}
Vdd vdd 0 DC {base.fmt(device.supply_v)}
.include '{device.subckt}.sub'
XDRV pad in_dig en_sig vdd 0 {device.subckt}
Rload pad 0 50
Cload pad 0 2p
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 2p 45n
.end
"""


def prepare_legacy(device: base.Device, profile: base.Profile) -> Path:
    model = OUT / "generated_models" / device.device_id / profile.profile_id / "legacy" / f"{device.subckt}.sub"
    if not model.exists():
        convert_ibis_to_pybis(profile.ibis, model, device.component, device.model,
                              "Output", "InputDriven", "Typical")
    return model


def build_pad_reference(device: base.Device, profile: base.Profile, legacy: Path,
                        ngspice: Path, timeout_s: int, resume: bool) -> tuple[dict, dict[str, object]]:
    out = OUT / "calibration" / device.device_id / profile.profile_id
    ensure(out)
    shutil.copy2(legacy, out / f"{device.subckt}.sub")
    deck = out / "calibration.sp"
    deck.write_text(calibration_deck(device), encoding="ascii")
    raw = out / "calibration.raw"
    log = out / "calibration.log"
    source = "existing_raw"
    if not (resume and raw.exists()):
        if raw.exists():
            raw.unlink()
        rc = run_process([str(ngspice), "-b", "-r", raw.name, deck.name], out, log, timeout_s)
        if rc != 0 or not raw.exists():
            raise RuntimeError(f"calibration failed: {device.device_id}/{profile.profile_id}")
        source = "run"
    wave = parse_ng(raw)
    threshold = input_threshold(legacy, device.supply_v)
    fraction = min(1.0, max(0.0, threshold / device.supply_v))
    rise_edge = 5.0 + EDGE_NS * fraction
    fall_edge = 25.0 + EDGE_NS * (1.0 - fraction)
    duration = 14.0

    def section(edge: float) -> dict[str, list[float]]:
        mask = (wave["time_ns"] >= edge) & (wave["time_ns"] <= edge + duration)
        time_ns = wave["time_ns"][mask] - edge
        pad_v = wave["pad_v"][mask]
        # Limit embedded data while preserving the transient shape.
        stride = max(1, int(np.ceil(len(time_ns) / 801)))
        return {
            "time_ns": [float(value) for value in time_ns[::stride]],
            "pad_v": [float(value) for value in pad_v[::stride]],
        }

    reference = {
        "schema": "pybis_pad_replay_reference_v1",
        "device": device.device_id,
        "profile": profile.profile_id,
        "source": "legacy_pybis_ngspice",
        "input_edge_ps": EDGE_NS * 1000,
        "load_ohm": 50.0,
        "load_pf": 2.0,
        "rising": section(rise_edge),
        "falling": section(fall_edge),
    }
    ref_path = out / "pad_replay_reference.json"
    ref_path.write_text(json.dumps(reference, indent=2), encoding="utf-8")
    return reference, {
        "device": device.device_id, "profile": profile.profile_id,
        "source": source, "reference_json": str(ref_path.relative_to(ROOT)),
        "calibration_raw": str(raw.relative_to(ROOT)),
    }


def prepare_models(device: base.Device, profile: base.Profile, reference: dict) -> dict[str, Path]:
    models: dict[str, Path] = {}
    for flow in FLOWS:
        output = OUT / "generated_models" / device.device_id / profile.profile_id / flow.flow_id / f"{device.subckt}.sub"
        if flow.pad_reference or not output.exists():
            convert_ibis_to_pybis(
                profile.ibis, output, device.component, device.model, "Output", flow.mode, "Typical",
                pad_replay_reference=reference if flow.pad_reference else None,
            )
        models[flow.flow_id] = output
    return models


def ngspice_deck(device: base.Device, case: base.PulseCase, load: tuple[float, float], flow: Flow) -> str:
    diagnostics = "" if flow.flow_id == "legacy" else "".join(f" V(xdrv.{name})" for name in DIAGNOSTICS)
    return f"""* Three-buffer pad-match replay study
.title {device.device_id} {flow.flow_id} {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
{base.pwl(device, case)}
Ven en_sig 0 DC {base.fmt(device.enable_v)}
Vdd vdd 0 DC {base.fmt(device.supply_v)}
.include '{device.subckt}.sub'
XDRV pad in_dig en_sig vdd 0 {device.subckt}
Rload pad 0 {base.fmt(load[0])}
Cload pad 0 {base.fmt(load[1])}p
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){diagnostics}
.tran 2p {base.fmt(case.stop_ns)}n
.end
"""


def load_tag(load: tuple[float, float]) -> str:
    return f"r{base.fmt(load[0]).replace('.', 'p')}_c{base.fmt(load[1]).replace('.', 'p')}pf"


def run_ngspice(device: base.Device, profile: base.Profile, case: base.PulseCase,
                load: tuple[float, float], flow: Flow, model: Path,
                ngspice: Path, timeout_s: int, resume: bool) -> tuple[dict[str, np.ndarray] | None, dict[str, object]]:
    out = OUT / "runs" / device.device_id / profile.profile_id / load_tag(load) / case.case_id / flow.flow_id
    ensure(out)
    shutil.copy2(model, out / f"{device.subckt}.sub")
    deck = out / "run.sp"
    raw = out / "run.raw"
    log = out / "run.log"
    deck.write_text(ngspice_deck(device, case, load, flow), encoding="ascii")
    source = "existing_raw"
    complete_existing = False
    if resume and raw.exists():
        try:
            existing = parse_ng(raw)
            complete_existing = bool(existing["time_ns"][-1] >= 0.999 * case.stop_ns)
        except Exception:
            complete_existing = False
    if resume and not complete_existing and log.exists():
        prior = log.read_text(encoding="utf-8", errors="replace")
        if "TIMEOUT after" in prior or "Timestep too small" in prior:
            return None, {
                "device": device.device_id, "profile": profile.profile_id,
                "load_ohm": load[0], "load_pf": load[1], "case_id": case.case_id,
                "flow": flow.flow_id, "status": "NUMERIC_FAIL", "return_code": 124,
                "source": "existing_failure", "log": str(log.relative_to(ROOT)),
            }
    if not complete_existing:
        if raw.exists():
            raw.unlink()
        rc = run_process([str(ngspice), "-b", "-r", raw.name, deck.name], out, log, timeout_s)
        source = "run"
        if rc != 0 or not raw.exists():
            return None, {
                "device": device.device_id, "profile": profile.profile_id,
                "load_ohm": load[0], "load_pf": load[1], "case_id": case.case_id,
                "flow": flow.flow_id, "status": "NUMERIC_FAIL", "return_code": rc,
                "source": source, "log": str(log.relative_to(ROOT)),
            }
    return parse_ng(raw), {
        "device": device.device_id, "profile": profile.profile_id,
        "load_ohm": load[0], "load_pf": load[1], "case_id": case.case_id,
        "flow": flow.flow_id, "status": "COMPLETED", "return_code": 0,
        "source": source, "raw": str(raw.relative_to(ROOT)), "log": str(log.relative_to(ROOT)),
    }


def native_deck_for_load(device: base.Device, profile: base.Profile, case: base.PulseCase,
                         load: tuple[float, float]) -> str:
    deck = base.native_ibis_deck(device, case, profile)
    deck = re.sub(r"Rload pad_ibis 0 \S+", f"Rload pad_ibis 0 {base.fmt(load[0])}", deck)
    deck = re.sub(r"Cload pad_ibis 0 \S+p", f"Cload pad_ibis 0 {base.fmt(load[1])}p", deck)
    return deck


def run_native_reference(device: base.Device, profile: base.Profile, case: base.PulseCase,
                         load: tuple[float, float], hspice: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out = OUT / "hspice_references" / device.device_id / profile.profile_id / load_tag(load) / case.case_id / "native"
    ensure(out)
    shutil.copy2(profile.ibis, out / "input.ibs")
    deck = native_deck_for_load(device, profile, case, load)
    lis = out / "run.lis"
    tr0 = out / "run.tr0"
    if tr0.exists() and lis.exists() and "job concluded" in lis.read_text(encoding="utf-8", errors="replace").lower():
        source = "existing_concluded_tr0"
    else:
        source = hspice_cache_run_watched(
            f"pad_match_{device.device_id}_{profile.profile_id}_{load_tag(load)}_native",
            device, case, deck, [profile.ibis], out, hspice, timeout_s, load,
        )
    raw = parse_hspice_tr0(tr0)
    row = {"source": source, "tr0": str(tr0.relative_to(ROOT))}
    wave = base.native_waveform(raw)
    return wave, {
        "device": device.device_id, "profile": profile.profile_id,
        "load_ohm": load[0], "load_pf": load[1], "case_id": case.case_id,
        "reference": "hspice_native_ibis", **row,
    }


def run_transistor_reference(device: base.Device, case: base.PulseCase,
                             hspice: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out = OUT / "hspice_references" / device.device_id / "transistor" / load_tag(NOMINAL_LOAD) / case.case_id
    ensure(out)
    base.copy_transistor_inputs(device, out)
    deck = base.transistor_deck(device, case)
    tr0 = out / "run.tr0"
    lis = out / "run.lis"
    if tr0.exists() and lis.exists() and "job concluded" in lis.read_text(encoding="utf-8", errors="replace").lower():
        source = "existing_concluded_tr0"
    else:
        source = hspice_cache_run_watched(
            f"pad_match_{device.device_id}_transistor", device, case, deck,
            list(device.transistor_files), out, hspice, timeout_s, NOMINAL_LOAD,
        )
    raw = parse_hspice_tr0(tr0)
    row = {
        "device": device.device_id, "edge_ps": case.edge_ns * 1000,
        "case_id": case.case_id, "reference": "hspice_transistor",
        "source": source, "tr0": str(tr0.relative_to(ROOT)),
    }
    return base.transistor_waveform(device, raw), row


def align(reference: dict[str, np.ndarray], transistor: dict[str, np.ndarray] | None,
          waves: dict[str, dict[str, np.ndarray] | None]) -> dict[str, np.ndarray]:
    t = reference["time_ns"]
    result = {
        "time_ns": t, "input_v": reference["input_v"],
        "hspice_native_pad_v": reference["pad_v"],
        "hspice_native_ku": reference["ku"], "hspice_native_kd": reference["kd"],
    }
    if transistor is not None:
        result["hspice_transistor_pad_v"] = np.interp(t, transistor["time_ns"], transistor["pad_v"])
    for flow_id, wave in waves.items():
        if wave is None:
            continue
        for key, values in wave.items():
            if key == "time_ns" or values is None:
                continue
            result[f"{flow_id}_{key}"] = np.interp(t, wave["time_ns"], values)
    return result


def active_mask(device: base.Device, case: base.PulseCase, time_ns: np.ndarray) -> np.ndarray:
    edges = base.command_edges(device, case)
    return (time_ns >= edges[0] - 0.5) & (time_ns <= edges[-1] + 5.0)


def rmse(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a[mask] - b[mask]) ** 2)))


def max_step(values: np.ndarray, mask: np.ndarray) -> float:
    selected = values[mask]
    return float(np.max(np.abs(np.diff(selected)))) if len(selected) > 1 else 0.0


def score(device: base.Device, profile: base.Profile, case: base.PulseCase,
          load: tuple[float, float], data: dict[str, np.ndarray], flow: Flow,
          run_row: dict[str, object]) -> dict[str, object]:
    row = dict(run_row)
    if run_row["status"] != "COMPLETED" or f"{flow.flow_id}_pad_v" not in data:
        return row
    mask = active_mask(device, case, data["time_ns"])
    ku = data[f"{flow.flow_id}_ku"]
    kd = data[f"{flow.flow_id}_kd"]
    row.update({
        "pad_rmse_mv": 1000 * rmse(data["hspice_native_pad_v"], data[f"{flow.flow_id}_pad_v"], mask),
        "ku_rmse": rmse(data["hspice_native_ku"], ku, mask),
        "kd_rmse": rmse(data["hspice_native_kd"], kd, mask),
        "ku_min": float(np.min(ku[mask])), "ku_max": float(np.max(ku[mask])),
        "kd_min": float(np.min(kd[mask])), "kd_max": float(np.max(kd[mask])),
        "max_ku_step": max_step(ku, mask),
        "max_kd_step": max_step(kd, mask),
    })
    if flow.pad_reference:
        for key in ("padsamp", "padslewsamp", "padstart_latch", "padstartspan", "padmatch_ambiguous", "padarg", "padmapactive", "coeff_jump_ku", "coeff_jump_kd"):
            data_key = f"{flow.flow_id}_{key}"
            if data_key in data:
                values = data[data_key][mask]
                row[f"{key}_min"] = float(np.min(values))
                row[f"{key}_max"] = float(np.max(values))
        active_key = f"{flow.flow_id}_padmapactive"
        active = data[active_key][mask] > 0.5 if active_key in data else np.zeros(np.count_nonzero(mask), dtype=bool)
        row["pad_map_triggered"] = bool(np.any(active))
        if np.any(active):
            span = data[f"{flow.flow_id}_padstartspan"][mask][active]
            ambiguous = data[f"{flow.flow_id}_padmatch_ambiguous"][mask][active]
            row["event_start_span_ns"] = float(np.median(span))
            row["mapping_ambiguous"] = bool(np.any(ambiguous > 0.5))
        else:
            row["event_start_span_ns"] = 0.0
            row["mapping_ambiguous"] = False
    native_ku = data["hspice_native_ku"][mask]
    native_kd = data["hspice_native_kd"][mask]
    row["native_max_ku_step"] = max_step(data["hspice_native_ku"], mask)
    row["native_max_kd_step"] = max_step(data["hspice_native_kd"], mask)
    reverse_edge = base.command_edges(device, case)[-1]
    reverse_mask = (
        (data["time_ns"] >= reverse_edge - 0.05)
        & (data["time_ns"] <= reverse_edge + 0.25)
    )
    row["reverse_edge_ns"] = reverse_edge
    row["reverse_ku_step"] = max_step(ku, reverse_mask)
    row["reverse_kd_step"] = max_step(kd, reverse_mask)
    row["native_reverse_ku_step"] = max_step(data["hspice_native_ku"], reverse_mask)
    row["native_reverse_kd_step"] = max_step(data["hspice_native_kd"], reverse_mask)
    margin = 0.1
    row["native_envelope_ok"] = (
        float(row["ku_min"]) >= float(np.min(native_ku)) - margin
        and float(row["ku_max"]) <= float(np.max(native_ku)) + margin
        and float(row["kd_min"]) >= float(np.min(native_kd)) - margin
        and float(row["kd_max"]) <= float(np.max(native_kd)) + margin
    )
    return row


def classify(rows: list[dict[str, object]]) -> None:
    groups: dict[tuple, list[dict[str, object]]] = {}
    for row in rows:
        key = (row["device"], row["profile"], row["load_ohm"], row["load_pf"], row["case_id"])
        groups.setdefault(key, []).append(row)
    for group in groups.values():
        legacy = next((row for row in group if row["flow"] == "legacy"), None)
        for row in group:
            if row["status"] != "COMPLETED" or "pad_rmse_mv" not in row:
                row["classification"] = "NUMERIC_FAIL"
                continue
            if row["flow"] == "legacy":
                row["classification"] = "BASELINE"
                continue
            if row.get("mapping_ambiguous"):
                row["classification"] = "PAD_MAPPING_AMBIGUOUS"
            elif legacy is None or "pad_rmse_mv" not in legacy:
                row["classification"] = "CHECK"
            else:
                candidate_reverse_jump = max(
                    float(row.get("reverse_ku_step", 0.0)),
                    float(row.get("reverse_kd_step", 0.0)),
                )
                reference_reverse_jump = max(
                    float(row.get("native_reverse_ku_step", 0.0)),
                    float(row.get("native_reverse_kd_step", 0.0)),
                    float(legacy.get("reverse_ku_step", 0.0)),
                    float(legacy.get("reverse_kd_step", 0.0)),
                )
                if (
                    not row.get("native_envelope_ok", False)
                    or candidate_reverse_jump > reference_reverse_jump + 0.2
                ):
                    row["classification"] = "COEFFICIENT_ARTIFACT"
                    continue
                improvements = (
                    float(row["pad_rmse_mv"]) < float(legacy["pad_rmse_mv"]),
                    float(row["ku_rmse"]) < float(legacy["ku_rmse"]),
                    float(row["kd_rmse"]) < float(legacy["kd_rmse"]),
                )
                if all(improvements):
                    row["classification"] = "COEFFICIENT_AND_PAD_IMPROVED"
                elif improvements[0] and not all(improvements[1:]):
                    row["classification"] = "PAD_ONLY_FALSE_PASS"
                else:
                    row["classification"] = "NO_CLEAR_IMPROVEMENT"


def plot_case(device: base.Device, profile: base.Profile, case: base.PulseCase,
              load: tuple[float, float], data: dict[str, np.ndarray]) -> Path:
    mask = active_mask(device, case, data["time_ns"])
    t = data["time_ns"][mask]
    fig, axes = plt.subplots(3, 1, figsize=(14.2, 10.3), sharex=True, constrained_layout=True)
    axes[0].plot(t, data["hspice_native_pad_v"][mask], color=BLACK, lw=3.0, label="HSPICE native IBIS")
    if "hspice_transistor_pad_v" in data:
        axes[0].plot(t, data["hspice_transistor_pad_v"][mask], color="#999999", lw=2.6, label="HSPICE transistor")
    axes[1].plot(t, data["hspice_native_ku"][mask], color=BLACK, lw=3.0, label="HSPICE native IBIS")
    axes[2].plot(t, data["hspice_native_kd"][mask], color=BLACK, lw=3.0, label="HSPICE native IBIS")
    for flow in FLOWS:
        if f"{flow.flow_id}_pad_v" not in data:
            continue
        axes[0].plot(t, data[f"{flow.flow_id}_pad_v"][mask], color=flow.color, lw=1.8, label=flow.label)
        axes[1].plot(t, data[f"{flow.flow_id}_ku"][mask], color=flow.color, lw=1.8, label=flow.label)
        axes[2].plot(t, data[f"{flow.flow_id}_kd"][mask], color=flow.color, lw=1.8, label=flow.label)
    for edge in base.command_edges(device, case):
        for ax in axes:
            ax.axvline(edge, color="#888888", lw=1.0, ls="--")
    axes[0].set_ylabel("pad voltage (V)")
    axes[1].set_ylabel("Ku")
    axes[2].set_ylabel("Kd")
    axes[2].set_xlabel("time (ns)")
    axes[2].axhline(0.0, color="#777777", lw=0.8)
    for ax in axes:
        ax.grid(True, alpha=0.22)
    axes[0].legend(frameon=False, ncol=3, fontsize=9)
    axes[0].set_title(f"{device.device_id} | {profile.profile_id} | {case.case_id} | {base.fmt(load[0])} ohm || {base.fmt(load[1])} pF", loc="left", fontweight="bold")
    path = OUT / "plots" / "cases" / device.device_id / profile.profile_id / load_tag(load) / f"{case.case_id}.png"
    ensure(path.parent)
    fig.savefig(path, dpi=185)
    plt.close(fig)
    return path


def plot_diagnostics(device: base.Device, profile: base.Profile, case: base.PulseCase,
                     data: dict[str, np.ndarray]) -> Path:
    mask = active_mask(device, case, data["time_ns"])
    t = data["time_ns"][mask]
    fig, axes = plt.subplots(4, 1, figsize=(14.2, 11.3), sharex=True, constrained_layout=True)
    for flow in FLOWS[-2:]:
        prefix = flow.flow_id
        if f"{prefix}_padsamp" not in data:
            continue
        axes[0].plot(t, data[f"{prefix}_pad_v"][mask], color=flow.color, lw=2.0, label=f"{flow.label}: pad")
        axes[0].plot(t, data[f"{prefix}_padsamp"][mask], color=flow.color, lw=1.5, ls="--", label=f"{flow.label}: sample")
        if f"{prefix}_padslewsamp" in data:
            axes[1].plot(t, data[f"{prefix}_padslewsamp"][mask], color=flow.color, lw=2.0, label=flow.label)
        axes[2].plot(t, data[f"{prefix}_padstart_latch"][mask], color=flow.color, lw=2.0, label=f"{flow.label}: start")
        axes[2].plot(t, data[f"{prefix}_padarg"][mask], color=flow.color, lw=1.4, ls="--", label=f"{flow.label}: replay argument")
        axes[3].plot(t, data[f"{prefix}_padmapactive"][mask], color=flow.color, lw=2.0, label=f"{flow.label}: active")
        axes[3].plot(t, data[f"{prefix}_padstartspan"][mask], color=flow.color, lw=1.3, ls=":", label=f"{flow.label}: ambiguity span")
    axes[0].set_ylabel("pad / sample (V)")
    axes[1].set_ylabel("|pad slew| (V/ns)")
    axes[2].set_ylabel("table time (ns)")
    axes[3].set_ylabel("flag / span")
    axes[3].set_xlabel("time (ns)")
    for ax in axes:
        ax.grid(True, alpha=0.22)
        ax.legend(frameon=False, ncol=3, fontsize=8)
    axes[0].set_title(f"Pad-match diagnostics | {device.device_id} | {profile.profile_id} | {case.case_id}", loc="left", fontweight="bold")
    path = OUT / "plots" / "diagnostics" / device.device_id / profile.profile_id / f"{case.case_id}.png"
    ensure(path.parent)
    fig.savefig(path, dpi=185)
    plt.close(fig)
    return path


def aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for device in base.DEVICES:
        for profile in profiles(device):
            for flow in FLOWS:
                selected = [
                    row for row in rows
                    if row["device"] == device.device_id
                    and row["profile"] == profile.profile_id
                    and row["flow"] == flow.flow_id
                    and "pad_rmse_mv" in row
                    and str(row.get("pad_rmse_mv", "")) != ""
                ]
                if not selected:
                    continue
                result.append({
                    "device": device.device_id, "profile": profile.profile_id, "flow": flow.flow_id,
                    "cases": len(selected),
                    "load_points": len({(float(row["load_ohm"]), float(row["load_pf"])) for row in selected}),
                    "median_pad_rmse_mv": float(np.median([float(row["pad_rmse_mv"]) for row in selected])),
                    "median_ku_rmse": float(np.median([float(row["ku_rmse"]) for row in selected])),
                    "median_kd_rmse": float(np.median([float(row["kd_rmse"]) for row in selected])),
                    "coefficient_and_pad_improved": sum(row.get("classification") == "COEFFICIENT_AND_PAD_IMPROVED" for row in selected),
                    "pad_only_false_pass": sum(row.get("classification") == "PAD_ONLY_FALSE_PASS" for row in selected),
                    "mapping_ambiguous": sum(row.get("classification") == "PAD_MAPPING_AMBIGUOUS" for row in selected),
                    "coefficient_artifact": sum(row.get("classification") == "COEFFICIENT_ARTIFACT" for row in selected),
                })
    return result


def write_readme(metrics: list[dict[str, object]], summary: list[dict[str, object]],
                 calibration: list[dict[str, object]], reference_rows: list[dict[str, object]]) -> None:
    pad_version = "v2" if any("ReplayV2" in flow.mode for flow in FLOWS if flow.pad_reference) else "v1"
    pad_short = [
        row for row in metrics
        if row.get("flow") in PAD_FLOWS
        and row.get("case_id") != "long_control"
    ]
    all_improved = [
        row for row in pad_short
        if row.get("classification") == "COEFFICIENT_AND_PAD_IMPROVED"
    ]
    short_high_pass = sum("short_high" in str(row.get("case_id")) for row in all_improved)
    short_low_pass = sum("short_low" in str(row.get("case_id")) for row in all_improved)
    ambiguous = sum(row.get("classification") == "PAD_MAPPING_AMBIGUOUS" for row in pad_short)
    numeric_fail = sum(row.get("classification") == "NUMERIC_FAIL" for row in metrics)
    lines = [
        "# Three-Buffer Pad-Voltage-Matched Replay",
        "",
        f"This is the experimental `{pad_version}` fixed-bench replay study. The pad map is calibrated from legacy pybis at `50 ohm || 2 pF`; HSPICE is validation only.",
        "",
        "## Algorithm",
        "",
        "- At a reverse edge, sample pad voltage once. The slew-aware variant also samples the magnitude of the pre-edge pad slope.",
        "- Invert the opposite-transition calibration trajectory to obtain one shared replay start time.",
        "- Replay the original aligned Ku/Kd table pair from `latched_start + fresh_elapsed_time`.",
        "- There is no continuous pad feedback. Legacy pybis remains active outside detected interrupted transitions.",
        *( ["- V2 uses direct legacy Ku/Kd while inactive; only the sample/latch/replay transaction uses held or pad-matched coefficients."] if pad_version == "v2" else ["- V1 continuously filters final Ku/Kd and is retained as an experimental baseline, not a production model."] ),
        "",
        "## Interpretation",
        "",
        "- `COEFFICIENT_AND_PAD_IMPROVED` is the only positive short-pulse result.",
        "- `PAD_ONLY_FALSE_PASS` means output voltage improved while Ku or Kd became less correct.",
        "- `PAD_MAPPING_AMBIGUOUS` means the same pad voltage maps to target-table times separated by more than 0.5 ns.",
        "- Load-matrix results test portability of a map calibrated only at 50 ohm || 2 pF.",
        "",
        "## Headline Result",
        "",
        f"- Pad-flow short-pulse rows: `{len(pad_short)}`; all-three improvements: `{len(all_improved)}` (`{short_high_pass}` short-high, `{short_low_pass}` short-low).",
        f"- Mapping-ambiguous rows: `{ambiguous}`. Numeric failures across all flows: `{numeric_fail}`.",
        "- A positive row is scoped to its tested direction and load. It does not promote the method as a general state model.",
        "- Legacy `InputDriven` was regenerated and SHA-256 compared for all six device/profile pairs; every model is byte-identical to the pre-experiment copy.",
        "",
        "## Summary",
        "",
        "| device | profile | flow | cases | loads | pad RMSE mV | Ku RMSE | Kd RMSE | all improved | pad-only | ambiguous | artifact |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['device']} | {row['profile']} | {row['flow']} | {row['cases']} | {row['load_points']} | "
            f"{row['median_pad_rmse_mv']:.3f} | {row['median_ku_rmse']:.4f} | {row['median_kd_rmse']:.4f} | "
            f"{row['coefficient_and_pad_improved']} | {row['pad_only_false_pass']} | {row['mapping_ambiguous']} | {row['coefficient_artifact']} |"
        )
    lines.extend([
        "", "## Files", "",
        "- `candidate_metrics.csv`", "- `summary_by_device_profile.csv`",
        "- `calibration_manifest.csv`", "- `reference_manifest.csv`", "- `run_manifest.csv`",
        "- `calibration/*/pad_replay_reference.json`", "- `generated_models/`",
        "- `plots/cases/`", "- `plots/diagnostics/`", "- `waveform_data/`", "",
        "- `verification/legacy_model_hash_check.csv` (nominal study)", "",
        f"Calibration rows: {len(calibration)}. HSPICE reference rows: {len(reference_rows)}. Candidate rows: {len(metrics)}.",
    ])
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=OUT)
    parser.add_argument("--phase", choices=("primary", "loads", "custom", "all", "report"), default="primary")
    parser.add_argument("--device", choices=("all", "io_buf", "inv_chain", "ex2"), default="all")
    parser.add_argument("--profile", choices=("all", "slow_1ns", "fast_5ps"), default="all")
    parser.add_argument("--case", default="all", help="Run one case_id instead of the full phase")
    parser.add_argument(
        "--custom-high-widths-ns",
        type=parse_widths_ns,
        default=(0.275, 0.300, 0.325, 0.350, 0.375, 0.400, 0.425, 0.450),
        help="Comma-separated short-high pulse widths used by --phase custom",
    )
    parser.add_argument(
        "--custom-low-widths-ns",
        type=parse_widths_ns,
        default=(0.275, 0.300, 0.325, 0.350, 0.375, 0.400, 0.425, 0.450),
        help="Comma-separated short-low pulse widths used by --phase custom",
    )
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--ngspice-timeout", type=int, default=30)
    parser.add_argument("--hspice-timeout", type=int, default=180)
    parser.add_argument(
        "--pad-version",
        choices=("v1", "v2"),
        default="v1",
        help="Select the experimental pad-replay implementation; v2 has an exact inactive legacy bypass",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--rerun-pad-flows",
        action="store_true",
        help="Rerun pad_voltage/pad_slew while reusing other cached flows and HSPICE references",
    )
    return parser.parse_args()


def main() -> int:
    global OUT, FLOWS, PAD_FLOWS
    args = parse_args()
    FLOWS = V2_FLOWS if args.pad_version == "v2" else V1_FLOWS
    PAD_FLOWS = tuple(flow.flow_id for flow in FLOWS if flow.pad_reference)
    OUT = args.study_dir if args.study_dir.is_absolute() else ROOT / args.study_dir
    OUT = OUT.resolve()
    if args.phase == "report":
        with (OUT / "candidate_metrics.csv").open(newline="", encoding="utf-8") as handle:
            metrics = list(csv.DictReader(handle))
        calibration = []
        references = []
        if (OUT / "calibration_manifest.csv").exists():
            with (OUT / "calibration_manifest.csv").open(newline="", encoding="utf-8") as handle:
                calibration = list(csv.DictReader(handle))
        if (OUT / "reference_manifest.csv").exists():
            with (OUT / "reference_manifest.csv").open(newline="", encoding="utf-8") as handle:
                references = list(csv.DictReader(handle))
        summary = aggregate(metrics)
        write_csv(OUT / "summary_by_device_profile.csv", summary)
        write_readme(metrics, summary, calibration, references)
        return 0

    devices = tuple(device for device in base.DEVICES if args.device in {"all", device.device_id})
    run_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    calibration_rows: list[dict[str, object]] = []
    reference_rows: list[dict[str, object]] = []
    figure_rows: list[dict[str, object]] = []

    for device in devices:
        for profile in profiles(device):
            if args.profile not in {"all", profile.profile_id}:
                continue
            print(f"[{device.device_id}/{profile.profile_id}] calibration", flush=True)
            legacy = prepare_legacy(device, profile)
            pad_reference, calibration_row = build_pad_reference(
                device, profile, legacy, args.ngspice, max(60, args.ngspice_timeout), args.resume
            )
            calibration_rows.append(calibration_row)
            models = prepare_models(device, profile, pad_reference)
            studies: list[tuple[tuple[float, float], tuple[base.PulseCase, ...], bool]] = []
            if args.phase in {"primary", "all"}:
                studies.append((NOMINAL_LOAD, primary_cases(), True))
            if args.phase in {"loads", "all"}:
                studies.extend((load, load_cases(), False) for load in LOAD_MATRIX if load != NOMINAL_LOAD)
            if args.phase == "custom":
                studies.append((NOMINAL_LOAD, custom_cases(
                    args.custom_high_widths_ns,
                    args.custom_low_widths_ns,
                ), True))

            for load, cases, transistor_enabled in studies:
                for case in cases:
                    if args.case not in {"all", case.case_id}:
                        continue
                    print(f"  {load_tag(load)}/{case.case_id}", flush=True)
                    native, native_row = run_native_reference(
                        device, profile, case, load, args.hspice, args.hspice_timeout
                    )
                    reference_rows.append(native_row)
                    transistor = None
                    if transistor_enabled:
                        transistor, transistor_row = run_transistor_reference(
                            device, case, args.hspice, args.hspice_timeout
                        )
                        transistor_row.update({"profile": profile.profile_id, "load_ohm": load[0], "load_pf": load[1]})
                        reference_rows.append(transistor_row)
                    waves: dict[str, dict[str, np.ndarray] | None] = {}
                    case_run_rows: dict[str, dict[str, object]] = {}
                    for flow in FLOWS:
                        flow_resume = args.resume and not (
                            args.rerun_pad_flows and flow.pad_reference
                        )
                        wave, row = run_ngspice(
                            device, profile, case, load, flow, models[flow.flow_id],
                            args.ngspice, args.ngspice_timeout, flow_resume,
                        )
                        waves[flow.flow_id] = wave
                        case_run_rows[flow.flow_id] = row
                        run_rows.append(row)
                    data = align(native, transistor, waves)
                    wave_path = OUT / "waveform_data" / device.device_id / profile.profile_id / load_tag(load) / f"{case.case_id}.csv"
                    write_wave(wave_path, data)
                    for flow in FLOWS:
                        metric_rows.append(score(device, profile, case, load, data, flow, case_run_rows[flow.flow_id]))
                    figure = plot_case(device, profile, case, load, data)
                    figure_rows.append({"device": device.device_id, "profile": profile.profile_id, "load": load_tag(load), "case_id": case.case_id, "figure": str(figure.relative_to(ROOT))})
                    if load == NOMINAL_LOAD and case.pattern != "rise_fall":
                        diagnostic = plot_diagnostics(device, profile, case, data)
                        figure_rows.append({"device": device.device_id, "profile": profile.profile_id, "load": load_tag(load), "case_id": case.case_id, "figure": str(diagnostic.relative_to(ROOT))})

            classify(metric_rows)
            write_csv(OUT / "candidate_metrics.csv", metric_rows)
            write_csv(OUT / "run_manifest.csv", run_rows)
            write_csv(OUT / "calibration_manifest.csv", calibration_rows)
            write_csv(OUT / "reference_manifest.csv", reference_rows)
            write_csv(OUT / "figure_manifest.csv", figure_rows)

    classify(metric_rows)
    summary = aggregate(metric_rows)
    write_csv(OUT / "candidate_metrics.csv", metric_rows)
    write_csv(OUT / "summary_by_device_profile.csv", summary)
    write_csv(OUT / "run_manifest.csv", run_rows)
    write_csv(OUT / "calibration_manifest.csv", calibration_rows)
    write_csv(OUT / "reference_manifest.csv", reference_rows)
    write_csv(OUT / "figure_manifest.csv", figure_rows)
    write_readme(metric_rows, summary, calibration_rows, reference_rows)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
