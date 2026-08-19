from __future__ import annotations

import argparse
import csv
import hashlib
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import run_three_buffer_realistic_pulse_campaign as base


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "three_buffer_prbs_phase1_2026-07-31"

EDGE_NS = 0.050
UI_VALUES_NS = (2.000, 1.000, 0.500, 0.250)
LOAD_OHM = 50.0
LOAD_PF = 2.0
TRAN_STEP_NS = 0.005
PRBS_ORDER = 7
PRBS_PERIOD = (1 << PRBS_ORDER) - 1
NGSPICE_ANALYSIS_BIT_OFFSET = 0
NGSPICE_ANALYSIS_BIT_COUNT = 31
HYBRID_V2_MODE = "InputDrivenHybridV2StateInitializedReplay"

BLACK = "#111111"
GRAY = "#737373"
RED = "#d62728"
BLUE = "#1769aa"
GREEN = "#008b6e"
ORANGE = "#d97706"
GRID = "#d9dde3"
FLOW_COLORS = {
    "hspice_transistor": GRAY,
    "hspice_native_ibis": BLACK,
    "ngspice_gate_state": RED,
    "ngspice_hybrid": BLUE,
}
FLOW_LABELS = {
    "hspice_transistor": "HSPICE transistor",
    "hspice_native_ibis": "HSPICE native IBIS",
    "ngspice_gate_state": "ngspice gate-state",
    "ngspice_hybrid": "ngspice hybrid",
}
SOLVER_PROFILES = {
    "gear_strict": (
        "method=gear maxord=2 reltol=1e-4 abstol=1e-10 "
        "vntol=1e-6 gmin=1e-12"
    ),
    "gear_relaxed": (
        "method=gear maxord=2 reltol=1e-3 abstol=1e-9 "
        "vntol=1e-5 gmin=1e-10 trtol=10 itl4=100"
    ),
    "trap_relaxed": (
        "method=trap reltol=1e-3 abstol=1e-9 "
        "vntol=1e-5 gmin=1e-10 trtol=10 itl4=100"
    ),
}


@dataclass(frozen=True)
class PrbsCase:
    case_id: str
    ui_ns: float
    edge_ns: float
    preamble_ns: float
    analysis_start_ns: float
    analysis_end_ns: float
    stop_ns: float
    pattern: str = "prbs7"
    pulse_width_ns: float = 0.0


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="ascii")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    base.write_csv(path, rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    return base.read_csv(path)


def upsert_rows(
    path: Path,
    new_rows: list[dict[str, object]],
    key_fields: tuple[str, ...],
) -> None:
    existing: list[dict[str, object]] = [dict(row) for row in read_csv(path)]
    by_key = {
        tuple(str(row.get(field, "")) for field in key_fields): row
        for row in existing
    }
    for row in new_rows:
        key = tuple(str(row.get(field, "")) for field in key_fields)
        by_key[key] = row
    write_csv(path, list(by_key.values()))


def preserve_solver_attempts() -> None:
    """Keep earlier numerical-profile failures as evidence when retrying."""
    manifest_path = OUT_DIR / "run_manifest.csv"
    attempts_path = OUT_DIR / "solver_attempts.csv"
    existing = read_csv(manifest_path)
    migrated: list[dict[str, object]] = []
    for row in existing:
        if not str(row.get("flow", "")).startswith("ngspice_"):
            continue
        copied: dict[str, object] = dict(row)
        if not copied.get("solver_profile"):
            copied["solver_profile"] = "gear_strict"
            copied["attempt_note"] = "pre-profile pilot"
        migrated.append(copied)
    if migrated:
        upsert_rows(
            attempts_path,
            migrated,
            ("device", "case_id", "flow", "solver_profile", "log"),
        )


def scan_solver_attempts() -> None:
    """Inventory completed, timed-out, and interrupted ngspice attempts."""
    runs_dir = OUT_DIR / "runs"
    if not runs_dir.exists():
        return
    known_cases = {case.case_id: case for case in cases()}
    rows: list[dict[str, object]] = []
    for log_path in runs_dir.glob(
        "*/prbs7_ui_*_edge_50ps/ngspice_*/*/ngspice_stdout.log"
    ):
        solver_profile = log_path.parent.name
        flow = log_path.parents[1].name
        case_id = log_path.parents[2].name
        device_id = log_path.parents[3].name
        text = log_path.read_text(encoding="utf-8", errors="replace")
        raw_path = log_path.parent / "run.raw"
        if raw_path.exists():
            status = "COMPLETED"
        elif "TIMEOUT after" in text:
            status = "NUMERIC_TIMEOUT"
        elif "ngspice-46 done" in text and "Error during 'write'" in text:
            status = "OUTPUT_WRITE_FAIL"
        elif text.strip():
            status = "INTERRUPTED_OR_NUMERIC_FAIL"
        else:
            status = "INTERRUPTED_NO_LOG"
        references = re.findall(
            r"Reference value\s*:\s*([+-]?[0-9.]+e[+-][0-9]+)",
            text,
            flags=re.IGNORECASE,
        )
        last_reference_s = float(references[-1]) if references else float("nan")
        case = known_cases.get(case_id)
        rows.append(
            {
                "device": device_id,
                "case_id": case_id,
                "ui_ps": case.ui_ns * 1000 if case is not None else "",
                "flow": flow,
                "solver_profile": solver_profile,
                "status": status,
                "last_reference_time_ns": (
                    last_reference_s * 1e9
                    if math.isfinite(last_reference_s)
                    else ""
                ),
                "raw": str(raw_path.relative_to(ROOT)) if raw_path.exists() else "",
                "log": str(log_path.relative_to(ROOT)),
            }
        )
    if rows:
        upsert_rows(
            OUT_DIR / "solver_attempts.csv",
            rows,
            ("device", "case_id", "flow", "solver_profile", "log"),
        )


def prbs7_bits() -> list[int]:
    """Return one deterministic maximal-length x^7 + x^6 + 1 sequence."""
    state = 0x7F
    initial = state
    result: list[int] = []
    for _ in range(PRBS_PERIOD):
        result.append((state >> 6) & 1)
        feedback = ((state >> 6) ^ (state >> 5)) & 1
        state = ((state << 1) & 0x7F) | feedback
    if state != initial or len(result) != 127 or sum(result) != 64:
        raise RuntimeError("PRBS7 generator failed its period/balance check")
    return result


BITS = prbs7_bits()


def make_case(ui_ns: float) -> PrbsCase:
    preamble_ns = max(5.0, 5.0 * ui_ns)
    analysis_start_ns = preamble_ns + NGSPICE_ANALYSIS_BIT_OFFSET * ui_ns
    analysis_end_ns = (
        preamble_ns
        + (NGSPICE_ANALYSIS_BIT_OFFSET + NGSPICE_ANALYSIS_BIT_COUNT) * ui_ns
    )
    postamble_ns = max(8.0, 12.0 * ui_ns)
    full_sequence_end_ns = preamble_ns + 2.0 * PRBS_PERIOD * ui_ns
    return PrbsCase(
        case_id=f"prbs7_ui_{base.width_tag(ui_ns)}_edge_50ps",
        ui_ns=ui_ns,
        edge_ns=EDGE_NS,
        preamble_ns=preamble_ns,
        analysis_start_ns=analysis_start_ns,
        analysis_end_ns=analysis_end_ns,
        stop_ns=full_sequence_end_ns + postamble_ns,
    )


def cases(ui_values: tuple[float, ...] = UI_VALUES_NS) -> list[PrbsCase]:
    return [make_case(value) for value in ui_values]


def bit_starts(case: PrbsCase) -> np.ndarray:
    return (
        case.analysis_start_ns
        + np.arange(NGSPICE_ANALYSIS_BIT_COUNT, dtype=float) * case.ui_ns
    )


def analysis_bits() -> list[int]:
    return BITS[
        NGSPICE_ANALYSIS_BIT_OFFSET:
        NGSPICE_ANALYSIS_BIT_OFFSET + NGSPICE_ANALYSIS_BIT_COUNT
    ]


def candidate_stop_ns(case: PrbsCase) -> float:
    return case.analysis_end_ns + max(5.0, 4.0 * case.ui_ns)


def prbs_points(device: base.Device, case: PrbsCase) -> list[tuple[float, float]]:
    values = BITS * 2
    points: list[tuple[float, float]] = [(0.0, 0.0), (case.preamble_ns, 0.0)]
    current = 0.0
    for index, bit in enumerate(values):
        boundary_ns = case.preamble_ns + index * case.ui_ns
        target = device.supply_v if bit else 0.0
        if abs(target - current) <= 1e-15:
            continue
        points.append((boundary_ns, current))
        points.append((boundary_ns + case.edge_ns, target))
        current = target
    sequence_end_ns = case.preamble_ns + len(values) * case.ui_ns
    points.append((sequence_end_ns, current))
    points.append((case.stop_ns, current))

    cleaned: list[tuple[float, float]] = []
    for point in points:
        if cleaned and point == cleaned[-1]:
            continue
        cleaned.append(point)
    return cleaned


def prbs_pwl(device: base.Device, case: PrbsCase) -> str:
    lines = ["Vin in_dig 0 PWL("]
    for time_ns, voltage in prbs_points(device, case):
        lines.append(f"+ {base.fmt(time_ns)}n {base.fmt(voltage)}")
    lines[-1] += " )"
    return "\n".join(lines)


def input_waveform(
    device: base.Device,
    case: PrbsCase,
    time_ns: np.ndarray,
) -> np.ndarray:
    points = prbs_points(device, case)
    return np.interp(
        time_ns,
        [point[0] for point in points],
        [point[1] for point in points],
    )


def fast_profile(device: base.Device) -> base.Profile:
    return base.Profile("fast_edge", "fast-edge IBIS", device.fast_ibis)


def transistor_deck(device: base.Device, case: PrbsCase) -> str:
    probes = " ".join(device.transistor_probe_nodes)
    if device.device_id == "io_buf":
        include = """.include 'hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF
Vdd_src vdd_src 0 DC 3.3
Rvdd vdd_src vdd 1
Cdec vdd 0 10p
Voe oe 0 DC 3.3
XDUT in_dig oe pad_sp in_sense vdd 0 SPICE_BUF"""
    elif device.device_id == "inv_chain":
        include = """.include 'invchain_ref_ngspice.sub'
Vdd vdd 0 DC 1.8
XDUT in_dig pad_sp vdd 0 invchain_ref"""
    else:
        include = """.include 'hspice.mod'
.subckt EX2_BUFFER in out vdd gnd
.include 'buffer.sp'
.ends EX2_BUFFER
Vdd vdd 0 DC 3.3
XDUT in_dig pad_sp vdd 0 EX2_BUFFER"""
    return f"""* Phase-1 direct-load PRBS7 transistor reference
.title {device.device_id} PRBS7 UI={base.fmt(case.ui_ns)}ns transistor
.option post=2 probe accurate ingold=2
.temp 27

{prbs_pwl(device, case)}

{include}
Rload pad_sp 0 {base.fmt(LOAD_OHM)}
Cload pad_sp 0 {base.fmt(LOAD_PF)}p

.probe tran V(in_dig) V(pad_sp) {probes}
.tran {base.fmt(TRAN_STEP_NS)}n {base.fmt(case.stop_ns)}n
.end
"""


def native_ibis_deck(
    device: base.Device,
    case: PrbsCase,
    profile: base.Profile,
) -> str:
    if device.device_id == "io_buf":
        instance = """Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad_ibis in_dig en_sig dig_q pc_ref gc_ref
+ file='input.ibs' model='driver' typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd
Rdig dig_q 0 1k"""
    else:
        instance = f"""VPU pu_ref 0 DC {base.fmt(device.supply_v)}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {base.fmt(device.supply_v)}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='input.ibs' model='{device.model}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd"""
    return f"""* Phase-1 direct-load PRBS7 HSPICE native IBIS
.title {device.device_id} PRBS7 UI={base.fmt(case.ui_ns)}ns native IBIS
.option post=2 probe accurate ingold=2
.temp 27

{prbs_pwl(device, case)}

{instance}
Rload pad_ibis 0 {base.fmt(LOAD_OHM)}
Cload pad_ibis 0 {base.fmt(LOAD_PF)}p

.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran {base.fmt(TRAN_STEP_NS)}n {base.fmt(case.stop_ns)}n
.end
"""


def ngspice_deck(
    device: base.Device,
    case: PrbsCase,
    mode: str,
    solver_profile: str,
) -> str:
    diagnostics = (
        " V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget)"
        " V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kuleg) V(xdrv.kdleg)"
        " V(xdrv.kutarget) V(xdrv.kdtarget)"
    )
    if mode.endswith("Hybrid"):
        diagnostics += (
            " V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)"
            " V(xdrv.hreverseraw) V(xdrv.hsettled) V(xdrv.hhybridactive)"
        )
    if mode == HYBRID_V2_MODE:
        diagnostics += (
            " V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)"
            " V(xdrv.hreverseraw) V(xdrv.hsettled) V(xdrv.hhybridactive)"
            " V(xdrv.hhybridv2active) V(xdrv.v2kusamp) V(xdrv.v2kdsamp)"
            " V(xdrv.v2elapsed) V(xdrv.v2kuprogress) V(xdrv.v2kdprogress)"
            " V(xdrv.v2kureplay) V(xdrv.v2kdreplay)"
            " V(xdrv.v2starterrku) V(xdrv.v2starterrkd) V(xdrv.v2sample)"
        )
    return f"""* Phase-1 direct-load PRBS7 ngspice
.title {device.device_id} PRBS7 UI={base.fmt(case.ui_ns)}ns {mode}
.temp 27
.options {SOLVER_PROFILES[solver_profile]}

{prbs_pwl(device, case)}

Ven en_sig 0 DC {base.fmt(device.enable_v)}
Vdd vdd 0 DC {base.fmt(device.supply_v)}
.include '{device.subckt}.sub'
XDRV pad in_dig en_sig vdd 0 {device.subckt}
Rload pad 0 {base.fmt(LOAD_OHM)}
Cload pad 0 {base.fmt(LOAD_PF)}p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){diagnostics}
.tran {base.fmt(TRAN_STEP_NS)}n {base.fmt(candidate_stop_ns(case))}n

.control
set filetype=binary
run
linearize
write run.raw V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){diagnostics}
quit
.endc
.end
"""


def copy_transistor_inputs(device: base.Device, out_dir: Path) -> None:
    base.copy_transistor_inputs(device, out_dir)


def run_hspice_transistor(
    device: base.Device,
    case: PrbsCase,
    hspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = OUT_DIR / "runs" / device.device_id / case.case_id / "hspice_transistor"
    ensure_dir(out_dir)
    copy_transistor_inputs(device, out_dir)
    deck = transistor_deck(device, case)
    source = base.hspice_cache_run(
        f"prbs_phase1_{device.device_id}_transistor",
        device,
        case,
        deck,
        list(device.transistor_files),
        out_dir,
        "run",
        hspice,
        timeout_s,
    )
    raw = base.parse_hspice_tr0(out_dir / "run.tr0")
    return raw, {
        "device": device.device_id,
        "case_id": case.case_id,
        "ui_ps": case.ui_ns * 1000,
        "flow": "hspice_transistor",
        "status": "COMPLETED",
        "source": source,
        "raw": str((out_dir / "run.tr0").relative_to(ROOT)),
        "log": str((out_dir / "run.lis").relative_to(ROOT)),
    }


def run_hspice_native(
    device: base.Device,
    case: PrbsCase,
    profile: base.Profile,
    hspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = OUT_DIR / "runs" / device.device_id / case.case_id / "hspice_native_ibis"
    ensure_dir(out_dir)
    shutil.copy2(profile.ibis, out_dir / "input.ibs")
    deck = native_ibis_deck(device, case, profile)
    source = base.hspice_cache_run(
        f"prbs_phase1_{device.device_id}_native_ibis",
        device,
        case,
        deck,
        [profile.ibis],
        out_dir,
        "run",
        hspice,
        timeout_s,
    )
    raw = base.parse_hspice_tr0(out_dir / "run.tr0")
    return raw, {
        "device": device.device_id,
        "case_id": case.case_id,
        "ui_ps": case.ui_ns * 1000,
        "flow": "hspice_native_ibis",
        "status": "COMPLETED",
        "source": source,
        "raw": str((out_dir / "run.tr0").relative_to(ROOT)),
        "log": str((out_dir / "run.lis").relative_to(ROOT)),
    }


def run_ngspice(
    device: base.Device,
    case: PrbsCase,
    flow: str,
    mode: str,
    model_path: Path,
    ngspice: Path,
    timeout_s: int,
    retry_failures: bool,
    solver_profile: str,
) -> tuple[dict[str, np.ndarray] | None, dict[str, object]]:
    out_dir = (
        OUT_DIR
        / "runs"
        / device.device_id
        / case.case_id
        / flow
        / solver_profile
    )
    ensure_dir(out_dir)
    local_model = out_dir / f"{device.subckt}.sub"
    shutil.copy2(model_path, local_model)
    deck = ngspice_deck(device, case, mode, solver_profile)
    deck_path = out_dir / "run.sp"
    raw_path = out_dir / "run.raw"
    log_path = out_dir / "ngspice_stdout.log"
    signature_path = out_dir / "run_signature.txt"
    signature = hashlib.sha256(
        deck.encode("ascii") + local_model.read_bytes()
    ).hexdigest()

    signature_matches = (
        signature_path.exists()
        and signature_path.read_text(encoding="ascii").strip() == signature
    )
    if signature_matches and raw_path.exists():
        return base.parse_ngspice_raw(raw_path), {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000,
            "flow": flow,
            "status": "COMPLETED",
            "return_code": 0,
            "source": "existing_raw",
            "solver_profile": solver_profile,
            "raw": str(raw_path.relative_to(ROOT)),
            "log": str(log_path.relative_to(ROOT)) if log_path.exists() else "",
        }
    if (
        signature_matches
        and log_path.exists()
        and not retry_failures
        and (
            "TIMEOUT after" in log_path.read_text(encoding="utf-8", errors="replace")
            or "Timestep too small"
            in log_path.read_text(encoding="utf-8", errors="replace")
        )
    ):
        return None, {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000,
            "flow": flow,
            "status": "NUMERIC_FAIL",
            "return_code": 124,
            "source": "existing_failure",
            "solver_profile": solver_profile,
            "raw": "",
            "log": str(log_path.relative_to(ROOT)),
        }

    write_text(deck_path, deck)
    if raw_path.exists():
        raw_path.unlink()
    rc = base.run_process(
        [str(ngspice), "-b", deck_path.name],
        out_dir,
        log_path,
        timeout_s,
    )
    signature_path.write_text(signature + "\n", encoding="ascii")
    status = "COMPLETED" if rc == 0 and raw_path.exists() else "NUMERIC_FAIL"
    row: dict[str, object] = {
        "device": device.device_id,
        "case_id": case.case_id,
        "ui_ps": case.ui_ns * 1000,
        "flow": flow,
        "status": status,
        "return_code": rc,
        "source": "run",
        "solver_profile": solver_profile,
        "raw": str(raw_path.relative_to(ROOT)) if raw_path.exists() else "",
        "log": str(log_path.relative_to(ROOT)),
    }
    if status != "COMPLETED":
        return None, row
    try:
        return base.parse_ngspice_raw(raw_path), row
    except Exception as exc:
        row["status"] = "PARSE_FAIL"
        row["parse_error"] = str(exc)
        return None, row


def interp(
    wave: dict[str, np.ndarray],
    time_ns: np.ndarray,
    key: str,
) -> np.ndarray:
    return np.interp(time_ns, wave["time_ns"], wave[key])


def aligned_data(
    device: base.Device,
    case: PrbsCase,
    transistor: dict[str, np.ndarray],
    native: dict[str, np.ndarray],
    candidates: dict[str, dict[str, np.ndarray] | None],
) -> dict[str, np.ndarray]:
    start_ns = max(0.0, case.analysis_start_ns - 2.0 * case.ui_ns)
    stop_ns = min(
        candidate_stop_ns(case),
        case.analysis_end_ns + max(5.0, 4.0 * case.ui_ns),
    )
    time_ns = np.arange(
        start_ns,
        stop_ns + 0.5 * TRAN_STEP_NS,
        TRAN_STEP_NS,
    )
    result: dict[str, np.ndarray] = {
        "time_ns": time_ns,
        "input_v": input_waveform(device, case, time_ns),
        "hspice_transistor_pad_v": interp(transistor, time_ns, "pad_v"),
        "hspice_native_ibis_pad_v": interp(native, time_ns, "pad_v"),
        "hspice_native_ibis_ku": interp(native, time_ns, "ku"),
        "hspice_native_ibis_kd": interp(native, time_ns, "kd"),
    }
    for index in range(1, len(device.transistor_probe_nodes) + 1):
        key = f"control_{index}_v"
        if key in transistor:
            result[f"hspice_transistor_{key}"] = interp(
                transistor,
                time_ns,
                key,
            )
    for flow, wave in candidates.items():
        if wave is None:
            continue
        for key in ("pad_v", "ku", "kd"):
            result[f"{flow}_{key}"] = interp(wave, time_ns, key)
        for key in (
            "gup",
            "gdn",
            "guptarget",
            "gdntarget",
            "hfall_after_rise",
            "hrise_after_fall",
            "hhybridactive",
        ):
            if key in wave:
                result[f"{flow}_{key}"] = interp(wave, time_ns, key)
    return result


def save_waveform(path: Path, data: dict[str, np.ndarray]) -> None:
    ensure_dir(path.parent)
    names = list(data)
    array = np.column_stack([data[name] for name in names])
    np.savetxt(
        path,
        array,
        delimiter=",",
        header=",".join(names),
        comments="",
        fmt="%.10g",
    )


def load_waveform(path: Path) -> dict[str, np.ndarray]:
    structured = np.genfromtxt(path, delimiter=",", names=True, dtype=float)
    return {name: np.asarray(structured[name], dtype=float) for name in structured.dtype.names or ()}


def waveform_path(device: base.Device, case: PrbsCase) -> Path:
    return OUT_DIR / "waveforms" / device.device_id / f"{case.case_id}.csv"


def rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.sqrt(np.mean((candidate - reference) ** 2)))


def analysis_mask(case: PrbsCase, time_ns: np.ndarray) -> np.ndarray:
    return (time_ns >= case.analysis_start_ns) & (time_ns < case.analysis_end_ns)


def flow_signal_key(flow: str, signal_name: str) -> str:
    return f"{flow}_{signal_name}"


def eye_score(bits: np.ndarray, samples: np.ndarray) -> tuple[float, float, float]:
    low = samples[bits == 0]
    high = samples[bits == 1]
    if len(low) < 4 or len(high) < 4:
        return float("nan"), float("nan"), float("nan")
    low_upper = float(np.percentile(low, 95))
    high_lower = float(np.percentile(high, 5))
    return high_lower - low_upper, float(np.median(low)), float(np.median(high))


def optimize_eye(
    case: PrbsCase,
    time_ns: np.ndarray,
    values: np.ndarray,
) -> dict[str, float]:
    starts = bit_starts(case)
    bits = np.asarray(analysis_bits(), dtype=int)
    max_delay_ns = min(
        max(6.0, 12.0 * case.ui_ns),
        float(time_ns[-1] - starts[-1] - 0.5 * case.ui_ns),
    )
    delays = np.arange(0.0, max_delay_ns + 0.5 * TRAN_STEP_NS, TRAN_STEP_NS)
    scores = np.empty_like(delays)
    low_medians = np.empty_like(delays)
    high_medians = np.empty_like(delays)
    for index, delay_ns in enumerate(delays):
        samples = np.interp(starts + delay_ns, time_ns, values)
        score, low, high = eye_score(bits, samples)
        scores[index] = score
        low_medians[index] = low
        high_medians[index] = high
    if not np.any(np.isfinite(scores)):
        return {
            "best_delay_ns": float("nan"),
            "eye_height_v": float("nan"),
            "eye_width_ns": float("nan"),
            "sample_low_v": float("nan"),
            "sample_high_v": float("nan"),
            "sample_ber": float("nan"),
        }
    best_index = int(np.nanargmax(scores))
    best_delay = float(delays[best_index])
    samples = np.interp(starts + best_delay, time_ns, values)
    low = samples[bits == 0]
    high = samples[bits == 1]
    threshold = 0.5 * (
        float(low_medians[best_index]) + float(high_medians[best_index])
    )
    errors = int(np.count_nonzero(low > threshold) + np.count_nonzero(high < threshold))

    offsets = np.linspace(-0.5 * case.ui_ns, 0.5 * case.ui_ns, 201)
    offset_scores = np.asarray(
        [
            eye_score(
                bits,
                np.interp(starts + best_delay + offset, time_ns, values),
            )[0]
            for offset in offsets
        ],
        dtype=float,
    )
    center = int(np.argmin(np.abs(offsets)))
    if not np.isfinite(offset_scores[center]) or offset_scores[center] <= 0:
        width_ns = 0.0
    else:
        left = center
        right = center
        while left > 0 and offset_scores[left - 1] > 0:
            left -= 1
        while right + 1 < len(offsets) and offset_scores[right + 1] > 0:
            right += 1
        width_ns = float(offsets[right] - offsets[left])
    return {
        "best_delay_ns": best_delay,
        "eye_height_v": float(scores[best_index]),
        "eye_width_ns": width_ns,
        "sample_low_v": float(low_medians[best_index]),
        "sample_high_v": float(high_medians[best_index]),
        "sample_ber": errors / len(bits),
    }


def metric_rows(
    device: base.Device,
    case: PrbsCase,
    data: dict[str, np.ndarray],
    run_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    mask = analysis_mask(case, data["time_ns"])
    native_pad = data["hspice_native_ibis_pad_v"][mask]
    transistor_pad = data["hspice_transistor_pad_v"][mask]
    rows: list[dict[str, object]] = [
        {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000,
            "flow": "hspice_transistor",
            "status": "REFERENCE",
            "pad_rmse_vs_native_v": rmse(native_pad, transistor_pad),
        },
        {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000,
            "flow": "hspice_native_ibis",
            "status": "REFERENCE",
            "pad_rmse_vs_native_v": 0.0,
            "ku_rmse_vs_native": 0.0,
            "kd_rmse_vs_native": 0.0,
        },
    ]
    statuses = {str(row["flow"]): str(row["status"]) for row in run_rows}
    for flow in ("ngspice_gate_state", "ngspice_hybrid"):
        key = flow_signal_key(flow, "pad_v")
        row: dict[str, object] = {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000,
            "flow": flow,
            "status": statuses.get(flow, "UNAVAILABLE"),
        }
        if key in data:
            pad = data[key][mask]
            ku = data[flow_signal_key(flow, "ku")][mask]
            kd = data[flow_signal_key(flow, "kd")][mask]
            native_ku = data["hspice_native_ibis_ku"][mask]
            native_kd = data["hspice_native_ibis_kd"][mask]
            row.update(
                {
                    "pad_rmse_vs_native_v": rmse(native_pad, pad),
                    "pad_rmse_vs_transistor_v": rmse(transistor_pad, pad),
                    "pad_max_error_vs_native_v": float(np.max(np.abs(pad - native_pad))),
                    "ku_rmse_vs_native": rmse(native_ku, ku),
                    "kd_rmse_vs_native": rmse(native_kd, kd),
                    "ku_max_error_vs_native": float(np.max(np.abs(ku - native_ku))),
                    "kd_max_error_vs_native": float(np.max(np.abs(kd - native_kd))),
                    "ku_min": float(np.min(ku)),
                    "ku_max": float(np.max(ku)),
                    "kd_min": float(np.min(kd)),
                    "kd_max": float(np.max(kd)),
                    "max_ku_step": float(np.max(np.abs(np.diff(ku)))),
                    "max_kd_step": float(np.max(np.abs(np.diff(kd)))),
                    "coefficient_range_ok": bool(
                        np.min(ku) >= -0.2
                        and np.max(ku) <= 1.2
                        and np.min(kd) >= -0.2
                        and np.max(kd) <= 1.2
                    ),
                }
            )
            if flow == "ngspice_hybrid" and f"{flow}_hhybridactive" in data:
                active = data[f"{flow}_hhybridactive"][mask] > 0.5
                row["hybrid_active_fraction"] = float(np.mean(active))
                row["hybrid_activation_count"] = int(
                    np.count_nonzero(np.diff(active.astype(int)) == 1)
                )
        rows.append(row)
    return rows


def eye_rows(
    device: base.Device,
    case: PrbsCase,
    data: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for flow in FLOW_LABELS:
        key = flow_signal_key(flow, "pad_v")
        if key not in data:
            continue
        rows.append(
            {
                "device": device.device_id,
                "case_id": case.case_id,
                "ui_ps": case.ui_ns * 1000,
                "flow": flow,
                **optimize_eye(case, data["time_ns"], data[key]),
            }
        )
    return rows


def pattern_rows(
    device: base.Device,
    case: PrbsCase,
    data: dict[str, np.ndarray],
    eyes: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    starts = bit_starts(case)
    bits_list = analysis_bits()
    bits = np.asarray(bits_list, dtype=int)
    patterns = [
        (
            f"{BITS[(NGSPICE_ANALYSIS_BIT_OFFSET + index - 1) % PRBS_PERIOD]}"
            f"{BITS[NGSPICE_ANALYSIS_BIT_OFFSET + index]}"
            f"{BITS[(NGSPICE_ANALYSIS_BIT_OFFSET + index + 1) % PRBS_PERIOD]}"
        )
        for index in range(NGSPICE_ANALYSIS_BIT_COUNT)
    ]
    detail: list[dict[str, object]] = []
    summary: list[dict[str, object]] = []
    eye_by_flow = {str(row["flow"]): row for row in eyes}
    for flow, eye in eye_by_flow.items():
        key = flow_signal_key(flow, "pad_v")
        delay_ns = float(eye["best_delay_ns"])
        samples = np.interp(starts + delay_ns, data["time_ns"], data[key])
        low_median = float(np.median(samples[bits == 0]))
        high_median = float(np.median(samples[bits == 1]))
        swing = max(high_median - low_median, 1e-12)
        medians_by_pattern: dict[str, float] = {}
        for pattern in sorted(set(patterns)):
            mask = np.asarray([value == pattern for value in patterns], dtype=bool)
            values = samples[mask]
            median = float(np.median(values))
            medians_by_pattern[pattern] = median
            detail.append(
                {
                    "device": device.device_id,
                    "case_id": case.case_id,
                    "ui_ps": case.ui_ns * 1000,
                    "flow": flow,
                    "pattern": pattern,
                    "count": len(values),
                    "sample_median_v": median,
                    "sample_p05_v": float(np.percentile(values, 5)),
                    "sample_p95_v": float(np.percentile(values, 95)),
                    "sample_normalized": (median - low_median) / swing,
                    "best_delay_ns": delay_ns,
                }
            )
        low_values = [
            value
            for pattern, value in medians_by_pattern.items()
            if pattern[1] == "0"
        ]
        high_values = [
            value
            for pattern, value in medians_by_pattern.items()
            if pattern[1] == "1"
        ]
        low_spread = max(low_values) - min(low_values)
        high_spread = max(high_values) - min(high_values)
        summary.append(
            {
                "device": device.device_id,
                "case_id": case.case_id,
                "ui_ps": case.ui_ns * 1000,
                "flow": flow,
                "low_history_spread_v": low_spread,
                "high_history_spread_v": high_spread,
                "worst_history_spread_v": max(low_spread, high_spread),
                "worst_history_spread_fraction": max(low_spread, high_spread) / swing,
            }
        )
    return detail, summary


def worst_bit_rows(
    device: base.Device,
    case: PrbsCase,
    data: dict[str, np.ndarray],
    eyes: list[dict[str, object]],
) -> list[dict[str, object]]:
    eye_by_flow = {str(row["flow"]): row for row in eyes}
    native_delay = float(eye_by_flow["hspice_native_ibis"]["best_delay_ns"])
    starts = bit_starts(case)
    rows: list[dict[str, object]] = []
    for flow in ("ngspice_gate_state", "ngspice_hybrid"):
        key = flow_signal_key(flow, "pad_v")
        if key not in data:
            continue
        errors: list[float] = []
        for start_ns in starts:
            sample_times = np.linspace(
                start_ns + native_delay - 0.5 * case.ui_ns,
                start_ns + native_delay + 0.5 * case.ui_ns,
                101,
            )
            reference = np.interp(
                sample_times,
                data["time_ns"],
                data["hspice_native_ibis_pad_v"],
            )
            candidate = np.interp(sample_times, data["time_ns"], data[key])
            errors.append(rmse(reference, candidate))
        worst_index = int(np.argmax(errors))
        source_index = NGSPICE_ANALYSIS_BIT_OFFSET + worst_index
        rows.append(
            {
                "device": device.device_id,
                "case_id": case.case_id,
                "ui_ps": case.ui_ns * 1000,
                "flow": flow,
                "worst_bit_index": worst_index,
                "source_prbs_bit_index": source_index,
                "previous_bit": BITS[(source_index - 1) % PRBS_PERIOD],
                "current_bit": BITS[source_index],
                "next_bit": BITS[(source_index + 1) % PRBS_PERIOD],
                "pattern": (
                    f"{BITS[(source_index - 1) % PRBS_PERIOD]}"
                    f"{BITS[source_index]}"
                    f"{BITS[(source_index + 1) % PRBS_PERIOD]}"
                ),
                "worst_bit_rmse_v": errors[worst_index],
                "native_sample_delay_ns": native_delay,
            }
        )
    return rows


def style_axis(axis: plt.Axes) -> None:
    axis.grid(True, color=GRID, linewidth=0.7, alpha=0.75)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)


def plot_setup() -> None:
    ensure_dir(OUT_DIR / "plots")
    figure, axes = plt.subplots(
        2,
        1,
        figsize=(16, 8.5),
        gridspec_kw={"height_ratios": [0.9, 1.1]},
        constrained_layout=True,
    )
    axis = axes[0]
    blocks = [
        (0.03, 0.33, 0.17, 0.34, "PRBS7 PWL\n50 ps edges"),
        (0.29, 0.33, 0.18, 0.34, "buffer under test\nio_buf / inv_chain / ex2"),
        (0.57, 0.33, 0.13, 0.34, "pad"),
        (0.79, 0.24, 0.16, 0.52, "50 ohm\n||\n2 pF"),
    ]
    for x, y, width, height, label in blocks:
        axis.add_patch(
            plt.Rectangle(
                (x, y),
                width,
                height,
                transform=axis.transAxes,
                facecolor="#f4f6f8",
                edgecolor="#444444",
                linewidth=1.5,
            )
        )
        axis.text(
            x + width / 2,
            y + height / 2,
            label,
            transform=axis.transAxes,
            ha="center",
            va="center",
            fontsize=12,
        )
    for x0, x1 in ((0.20, 0.29), (0.47, 0.57), (0.70, 0.79)):
        axis.annotate(
            "",
            xy=(x1, 0.5),
            xytext=(x0, 0.5),
            xycoords="axes fraction",
            arrowprops={"arrowstyle": "->", "lw": 1.8, "color": "#333333"},
        )
    axis.set_axis_off()
    axis.set_title("Phase 1: driver-only PRBS history test", fontsize=18, pad=10)

    case = make_case(0.5)
    device = base.DEVICES[0]
    start_ns = case.analysis_start_ns
    time_ns = np.linspace(start_ns, start_ns + 24 * case.ui_ns, 2401)
    waveform = input_waveform(device, case, time_ns) / device.supply_v
    axes[1].plot(
        (time_ns - start_ns) / case.ui_ns,
        waveform,
        color=BLUE,
        linewidth=2.0,
    )
    axes[1].set_xlim(0, 24)
    axes[1].set_ylim(-0.08, 1.08)
    axes[1].set_xlabel("Bit position (UI)")
    axes[1].set_ylabel("Normalized input")
    axes[1].set_title(
        "Identical deterministic PRBS7 bit sequence for every device and UI"
    )
    style_axis(axes[1])
    figure.savefig(OUT_DIR / "plots" / "00_testbench_and_stimulus.png", dpi=180)
    plt.close(figure)


def eye_segments(
    case: PrbsCase,
    data: dict[str, np.ndarray],
    key: str,
    delay_ns: float,
) -> tuple[np.ndarray, list[np.ndarray]]:
    # Two UIs around the selected sampling point make both the eye opening and
    # the neighboring transitions visible. The previous one-UI view made
    # settled traces look like a single heavy pulse.
    relative_ns = np.linspace(-case.ui_ns, case.ui_ns, 321)
    segments: list[np.ndarray] = []
    for start_ns in bit_starts(case):
        sample_time = start_ns + delay_ns + relative_ns
        if sample_time[0] < data["time_ns"][0] or sample_time[-1] > data["time_ns"][-1]:
            continue
        segments.append(np.interp(sample_time, data["time_ns"], data[key]))
    return relative_ns / case.ui_ns, segments


def hybrid_active_intervals(
    case: PrbsCase,
    data: dict[str, np.ndarray],
) -> list[tuple[int, int]]:
    key = "ngspice_hybrid_hhybridactive"
    if key not in data:
        return []
    in_window = analysis_mask(case, data["time_ns"])
    active = (data[key] > 0.5) & in_window
    transitions = np.diff(active.astype(np.int8), prepend=0, append=0)
    starts = np.flatnonzero(transitions == 1)
    stops = np.flatnonzero(transitions == -1) - 1
    return list(zip(starts.tolist(), stops.tolist()))


def hybrid_event_rows(
    device: base.Device,
    case: PrbsCase,
    data: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    time_ns = data["time_ns"]
    fall_key = "ngspice_hybrid_hfall_after_rise"
    rise_key = "ngspice_hybrid_hrise_after_fall"
    for event_index, (start_index, stop_index) in enumerate(
        hybrid_active_intervals(case, data),
        start=1,
    ):
        event_slice = slice(start_index, stop_index + 1)
        fall_active = bool(
            fall_key in data and np.any(data[fall_key][event_slice] > 0.5)
        )
        rise_active = bool(
            rise_key in data and np.any(data[rise_key][event_slice] > 0.5)
        )
        if fall_active and rise_active:
            event_kind = "BOTH_DIRECTIONS"
        elif fall_active:
            event_kind = "FALL_AFTER_RISE"
        elif rise_active:
            event_kind = "RISE_AFTER_FALL"
        else:
            event_kind = "ACTIVE_UNCLASSIFIED"
        start_ns = float(time_ns[start_index])
        stop_ns = float(time_ns[stop_index])
        duration_ns = max(0.0, stop_ns - start_ns)
        row: dict[str, object] = {
            "device": device.device_id,
            "case_id": case.case_id,
            "ui_ps": case.ui_ns * 1000.0,
            "event_index": event_index,
            "event_kind": event_kind,
            "start_ns": start_ns,
            "stop_ns": stop_ns,
            "duration_ns": duration_ns,
            "start_ui": (start_ns - case.analysis_start_ns) / case.ui_ns,
            "stop_ui": (stop_ns - case.analysis_start_ns) / case.ui_ns,
            "duration_ui": duration_ns / case.ui_ns,
            "input_at_start_v": float(data["input_v"][start_index]),
        }
        for output_name, data_key in (
            ("pad_native_start_v", "hspice_native_ibis_pad_v"),
            ("pad_hybrid_start_v", "ngspice_hybrid_pad_v"),
            ("ku_native_start", "hspice_native_ibis_ku"),
            ("kd_native_start", "hspice_native_ibis_kd"),
            ("ku_hybrid_start", "ngspice_hybrid_ku"),
            ("kd_hybrid_start", "ngspice_hybrid_kd"),
            ("gup_start", "ngspice_hybrid_gup"),
            ("gdn_start", "ngspice_hybrid_gdn"),
        ):
            row[output_name] = (
                float(data[data_key][start_index]) if data_key in data else float("nan")
            )
        for output_name, candidate_key, reference_key in (
            ("max_pad_error_during_event_v", "ngspice_hybrid_pad_v", "hspice_native_ibis_pad_v"),
            ("max_ku_error_during_event", "ngspice_hybrid_ku", "hspice_native_ibis_ku"),
            ("max_kd_error_during_event", "ngspice_hybrid_kd", "hspice_native_ibis_kd"),
        ):
            if candidate_key in data and reference_key in data:
                row[output_name] = float(
                    np.max(
                        np.abs(
                            data[candidate_key][event_slice]
                            - data[reference_key][event_slice]
                        )
                    )
                )
            else:
                row[output_name] = float("nan")
        rows.append(row)
    return rows


def plot_case(
    device: base.Device,
    case: PrbsCase,
    data: dict[str, np.ndarray],
    eyes: list[dict[str, object]],
    patterns: list[dict[str, object]],
    worst_rows: list[dict[str, object]],
) -> list[Path]:
    out_dir = OUT_DIR / "plots" / "cases" / device.device_id / case.case_id
    ensure_dir(out_dir)
    eye_by_flow = {str(row["flow"]): row for row in eyes}
    outputs: list[Path] = []

    # A readable 32-UI excerpt from the analyzed period.
    start_ns = case.analysis_start_ns
    stop_ns = start_ns + 32.0 * case.ui_ns
    mask = (data["time_ns"] >= start_ns) & (data["time_ns"] <= stop_ns)
    x_ui = (data["time_ns"][mask] - start_ns) / case.ui_ns
    figure, axes = plt.subplots(
        4,
        1,
        figsize=(16, 11),
        sharex=True,
    )
    axes[0].plot(x_ui, data["input_v"][mask], color=GREEN, linewidth=1.8)
    axes[0].set_ylabel("Input (V)")
    pad_keys = {
        "hspice_transistor": "hspice_transistor_pad_v",
        "hspice_native_ibis": "hspice_native_ibis_pad_v",
        "ngspice_gate_state": "ngspice_gate_state_pad_v",
        "ngspice_hybrid": "ngspice_hybrid_pad_v",
    }
    for flow, key in pad_keys.items():
        if key not in data:
            continue
        linewidth = 3.5 if flow == "hspice_native_ibis" else 2.0
        zorder = 1 if flow in {"hspice_transistor", "hspice_native_ibis"} else 4
        axes[1].plot(
            x_ui,
            data[key][mask],
            color=FLOW_COLORS[flow],
            linewidth=linewidth,
            label=FLOW_LABELS[flow],
            zorder=zorder,
        )
    axes[1].set_ylabel("Pad (V)")
    for signal_name, axis in (("ku", axes[2]), ("kd", axes[3])):
        for flow in (
            "hspice_native_ibis",
            "ngspice_gate_state",
            "ngspice_hybrid",
        ):
            key = flow_signal_key(flow, signal_name)
            if key not in data:
                continue
            axis.plot(
                x_ui,
                data[key][mask],
                color=FLOW_COLORS[flow],
                linewidth=3.2 if flow == "hspice_native_ibis" else 1.8,
                zorder=1 if flow == "hspice_native_ibis" else 4,
            )
        axis.set_ylabel(signal_name.capitalize())
    axes[3].axhline(0.0, color="#999999", linewidth=0.8)
    axes[3].set_xlabel("Bit position in analyzed PRBS period (UI)")
    for axis in axes:
        style_axis(axis)
    handles, labels = axes[1].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.965),
        ncol=4,
        frameon=False,
    )
    figure.suptitle(
        f"{device.label}: PRBS7, UI = {base.fmt(case.ui_ns * 1000)} ps",
        fontsize=17,
        y=0.995,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.925), h_pad=0.7)
    output = out_dir / "01_sequence_overlay.png"
    figure.savefig(output, dpi=180)
    plt.close(figure)
    outputs.append(output)

    # Four independent pad eyes on common axes. Individual traces remain
    # visible; a heavy median trace can hide a closed or pattern-dependent eye.
    figure, axes = plt.subplots(
        2,
        2,
        figsize=(18, 11),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )
    for panel_index, (axis, flow) in enumerate(zip(axes.flat, FLOW_LABELS)):
        key = flow_signal_key(flow, "pad_v")
        if key not in data or flow not in eye_by_flow:
            axis.set_axis_off()
            continue
        delay_ns = float(eye_by_flow[flow]["best_delay_ns"])
        x, segments = eye_segments(case, data, key, delay_ns)
        for segment in segments:
            axis.plot(
                x,
                segment,
                color=FLOW_COLORS[flow],
                linewidth=0.9,
                alpha=0.34,
            )
        if segments:
            center_index = int(np.argmin(np.abs(x)))
            center_samples = np.asarray(segments)[:, center_index]
            axis.scatter(
                np.zeros_like(center_samples),
                center_samples,
                color=FLOW_COLORS[flow],
                edgecolor="white",
                linewidth=0.35,
                s=20,
                alpha=0.9,
                zorder=5,
            )
        low = float(eye_by_flow[flow]["sample_low_v"])
        high = float(eye_by_flow[flow]["sample_high_v"])
        if math.isfinite(low) and math.isfinite(high):
            axis.axhline(
                0.5 * (low + high),
                color="#777777",
                linestyle=":",
                linewidth=1.0,
            )
        axis.axvline(0.0, color="#999999", linestyle="--", linewidth=1.0)
        axis.set_title(
            f"{FLOW_LABELS[flow]}\n"
            f"sample delay {delay_ns:.3f} ns, "
            f"eye {float(eye_by_flow[flow]['eye_height_v']):.3f} V"
        )
        if panel_index >= 2:
            axis.set_xlabel("Time from best sample (UI)")
        axis.set_ylabel("Pad (V)")
        axis.set_xlim(-1.0, 1.0)
        style_axis(axis)
    figure.suptitle(
        f"{device.label}: two-UI pad eyes at {base.fmt(case.ui_ns * 1000)} ps UI",
        fontsize=17,
    )
    output = out_dir / "02_pad_eyes.png"
    figure.savefig(output, dpi=180)
    plt.close(figure)
    outputs.append(output)

    # Native and candidate coefficient eyes use each flow's pad-derived sample delay.
    coefficient_flows = [
        "hspice_native_ibis",
        "ngspice_gate_state",
        "ngspice_hybrid",
    ]
    figure, axes = plt.subplots(
        2,
        3,
        figsize=(18, 10),
        sharex=True,
        sharey="row",
        constrained_layout=True,
    )
    for column, flow in enumerate(coefficient_flows):
        if flow not in eye_by_flow:
            axes[0, column].set_axis_off()
            axes[1, column].set_axis_off()
            continue
        delay_ns = float(eye_by_flow[flow]["best_delay_ns"])
        for row_index, signal_name in enumerate(("ku", "kd")):
            axis = axes[row_index, column]
            key = flow_signal_key(flow, signal_name)
            if key not in data:
                axis.set_axis_off()
                continue
            x, segments = eye_segments(case, data, key, delay_ns)
            for segment in segments:
                axis.plot(
                    x,
                    segment,
                    color=FLOW_COLORS[flow],
                    linewidth=0.85,
                    alpha=0.32,
                )
            if segments:
                center_index = int(np.argmin(np.abs(x)))
                center_samples = np.asarray(segments)[:, center_index]
                axis.scatter(
                    np.zeros_like(center_samples),
                    center_samples,
                    color=FLOW_COLORS[flow],
                    edgecolor="white",
                    linewidth=0.3,
                    s=16,
                    alpha=0.9,
                    zorder=5,
                )
            axis.axhline(0.0, color="#999999", linewidth=0.8)
            axis.axvline(0.0, color="#999999", linestyle="--", linewidth=1.0)
            if row_index == 1:
                axis.set_xlabel("Time from best pad sample (UI)")
            axis.set_ylabel(signal_name.capitalize())
            axis.set_xlim(-1.0, 1.0)
            style_axis(axis)
        axes[0, column].set_title(FLOW_LABELS[flow])
    figure.suptitle(
        f"{device.label}: two-UI Ku/Kd eyes at {base.fmt(case.ui_ns * 1000)} ps UI",
        fontsize=17,
    )
    output = out_dir / "03_coefficient_eyes.png"
    figure.savefig(output, dpi=180)
    plt.close(figure)
    outputs.append(output)

    # Three-bit history classes, sampled at each flow's own best eye point.
    pattern_names = sorted({str(row["pattern"]) for row in patterns})
    figure, axes = plt.subplots(2, 1, figsize=(16, 9), sharex=True, constrained_layout=True)
    for flow in FLOW_LABELS:
        selected = [row for row in patterns if row["flow"] == flow]
        if not selected:
            continue
        values = {
            str(row["pattern"]): float(row["sample_normalized"])
            for row in selected
        }
        y = [values[name] for name in pattern_names]
        axes[0].plot(
            range(len(pattern_names)),
            y,
            color=FLOW_COLORS[flow],
            linewidth=2.0,
            marker="o",
            markersize=5,
            label=FLOW_LABELS[flow],
        )
        native_values = {
            str(row["pattern"]): float(row["sample_normalized"])
            for row in patterns
            if row["flow"] == "hspice_native_ibis"
        }
        if flow not in {"hspice_native_ibis", "hspice_transistor"} and native_values:
            error = [values[name] - native_values[name] for name in pattern_names]
            axes[1].plot(
                range(len(pattern_names)),
                error,
                color=FLOW_COLORS[flow],
                linewidth=2.0,
                marker="o",
                markersize=5,
                label=FLOW_LABELS[flow],
            )
    axes[0].set_ylabel("Normalized pad sample")
    axes[1].set_ylabel("Model - native")
    axes[1].set_xlabel("Previous / current / next bit")
    axes[1].set_xticks(range(len(pattern_names)), pattern_names)
    axes[1].axhline(0.0, color=BLACK, linewidth=1.0)
    axes[0].legend(ncol=4, frameon=False, loc="best")
    axes[1].legend(ncol=2, frameon=False, loc="best")
    for axis in axes:
        style_axis(axis)
    figure.suptitle(
        f"{device.label}: three-bit history response at "
        f"{base.fmt(case.ui_ns * 1000)} ps UI",
        fontsize=17,
    )
    output = out_dir / "04_pattern_context.png"
    figure.savefig(output, dpi=180)
    plt.close(figure)
    outputs.append(output)

    # Worst native-IBIS discrepancy for each candidate.
    figure, axes = plt.subplots(2, 2, figsize=(16, 9), sharex="col", constrained_layout=True)
    rows_by_flow = {str(row["flow"]): row for row in worst_rows}
    native_delay = float(eye_by_flow["hspice_native_ibis"]["best_delay_ns"])
    for column, flow in enumerate(("ngspice_gate_state", "ngspice_hybrid")):
        row = rows_by_flow.get(flow)
        if row is None:
            axes[0, column].set_axis_off()
            axes[1, column].set_axis_off()
            continue
        bit_index = int(row["worst_bit_index"])
        center_ns = bit_starts(case)[bit_index] + native_delay
        start_plot = center_ns - 1.5 * case.ui_ns
        stop_plot = center_ns + 1.5 * case.ui_ns
        mask = (data["time_ns"] >= start_plot) & (data["time_ns"] <= stop_plot)
        x = (data["time_ns"][mask] - center_ns) / case.ui_ns
        axes[0, column].plot(x, data["input_v"][mask], color=GREEN, linewidth=1.8)
        for pad_flow, key in (
            ("hspice_transistor", "hspice_transistor_pad_v"),
            ("hspice_native_ibis", "hspice_native_ibis_pad_v"),
            (flow, f"{flow}_pad_v"),
        ):
            axes[1, column].plot(
                x,
                data[key][mask],
                color=FLOW_COLORS[pad_flow],
                linewidth=3.2 if pad_flow == "hspice_native_ibis" else 2.0,
                label=FLOW_LABELS[pad_flow],
                zorder=1 if pad_flow != flow else 4,
            )
        axes[0, column].set_title(
            f"{FLOW_LABELS[flow]} worst bit: pattern {row['pattern']}"
        )
        axes[0, column].set_ylabel("Input (V)")
        axes[1, column].set_ylabel("Pad (V)")
        axes[1, column].set_xlabel("Time from native sample (UI)")
        axes[1, column].legend(frameon=False, loc="best")
        for axis in (axes[0, column], axes[1, column]):
            axis.axvline(0.0, color="#999999", linestyle="--", linewidth=1.0)
            style_axis(axis)
    figure.suptitle(
        f"{device.label}: worst PRBS bit windows at "
        f"{base.fmt(case.ui_ns * 1000)} ps UI",
        fontsize=17,
    )
    output = out_dir / "05_worst_bit.png"
    figure.savefig(output, dpi=180)
    plt.close(figure)
    outputs.append(output)

    # Show exactly when the hybrid switched from legacy replay to gate state.
    hybrid_key = "ngspice_hybrid_hhybridactive"
    if hybrid_key in data and "ngspice_hybrid_pad_v" in data:
        mask = analysis_mask(case, data["time_ns"])
        x_ui = (data["time_ns"][mask] - case.analysis_start_ns) / case.ui_ns
        figure, axes = plt.subplots(
            5,
            1,
            figsize=(16, 12),
            sharex=True,
            constrained_layout=True,
        )
        axes[0].plot(x_ui, data["input_v"][mask], color=GREEN, linewidth=1.7)
        axes[0].set_ylabel("Input (V)")
        axes[1].plot(
            x_ui,
            data["hspice_native_ibis_pad_v"][mask],
            color=BLACK,
            linewidth=3.0,
            label="HSPICE native IBIS",
        )
        axes[1].plot(
            x_ui,
            data["ngspice_hybrid_pad_v"][mask],
            color=BLUE,
            linewidth=1.8,
            label="ngspice hybrid",
        )
        axes[1].set_ylabel("Pad (V)")
        axes[1].legend(frameon=False, loc="best")
        for axis, coefficient in ((axes[2], "ku"), (axes[3], "kd")):
            axis.plot(
                x_ui,
                data[f"hspice_native_ibis_{coefficient}"][mask],
                color=BLACK,
                linewidth=2.8,
                label="HSPICE native IBIS",
            )
            axis.plot(
                x_ui,
                data[f"ngspice_hybrid_{coefficient}"][mask],
                color=BLUE,
                linewidth=1.7,
                label="ngspice hybrid",
            )
            axis.set_ylabel(coefficient.capitalize())
            axis.axhline(0.0, color="#999999", linewidth=0.8)
        axes[4].plot(
            x_ui,
            data[hybrid_key][mask],
            color="#7b2cbf",
            linewidth=2.2,
            label="gate-state active",
        )
        for key, color, label in (
            ("ngspice_hybrid_hfall_after_rise", ORANGE, "fall after rise"),
            ("ngspice_hybrid_hrise_after_fall", GREEN, "rise after fall"),
        ):
            if key in data:
                axes[4].plot(
                    x_ui,
                    data[key][mask],
                    color=color,
                    linewidth=1.6,
                    label=label,
                )
        axes[4].set_ylabel("Hybrid flags")
        axes[4].set_ylim(-0.08, 1.18)
        axes[4].set_xlabel("Bit position in analyzed PRBS window (UI)")
        intervals = hybrid_active_intervals(case, data)
        for event_index, (start_index, stop_index) in enumerate(intervals, start=1):
            start_ui = (
                data["time_ns"][start_index] - case.analysis_start_ns
            ) / case.ui_ns
            stop_ui = (
                data["time_ns"][stop_index] - case.analysis_start_ns
            ) / case.ui_ns
            for axis in axes:
                axis.axvspan(start_ui, stop_ui, color="#7b2cbf", alpha=0.08)
            axes[4].text(
                0.5 * (start_ui + stop_ui),
                1.05,
                f"E{event_index}",
                color="#5a189a",
                fontsize=9,
                ha="center",
                va="bottom",
            )
        axes[4].legend(ncol=3, frameon=False, loc="upper right")
        for axis in axes:
            style_axis(axis)
        activation_text = (
            f"{len(intervals)} activation event(s)"
            if intervals
            else "no gate-state activation"
        )
        figure.suptitle(
            f"{device.label}: hybrid activation at "
            f"{base.fmt(case.ui_ns * 1000)} ps UI ({activation_text})",
            fontsize=17,
        )
        output = out_dir / "06_hybrid_activation_events.png"
        figure.savefig(output, dpi=180)
        plt.close(figure)
        outputs.append(output)
    return outputs


def float_value(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except (TypeError, ValueError):
        return float("nan")


def summary_plots() -> None:
    metrics = read_csv(OUT_DIR / "metrics.csv")
    eyes = read_csv(OUT_DIR / "eye_metrics.csv")
    history = read_csv(OUT_DIR / "history_metrics.csv")
    if not metrics or not eyes:
        return
    ensure_dir(OUT_DIR / "plots")
    devices = [device for device in base.DEVICES if any(row["device"] == device.device_id for row in eyes)]

    figure, axes = plt.subplots(len(devices), 1, figsize=(14, 4.1 * len(devices)), constrained_layout=True)
    axes_array = np.atleast_1d(axes)
    for axis, device in zip(axes_array, devices):
        for flow in FLOW_LABELS:
            selected = sorted(
                [
                    row
                    for row in eyes
                    if row["device"] == device.device_id and row["flow"] == flow
                ],
                key=lambda row: float_value(row, "ui_ps"),
            )
            if not selected:
                continue
            axis.plot(
                [float_value(row, "ui_ps") for row in selected],
                [float_value(row, "eye_height_v") for row in selected],
                color=FLOW_COLORS[flow],
                marker="o",
                linewidth=2.0,
                label=FLOW_LABELS[flow],
            )
        axis.set_title(device.label)
        axis.set_xlabel("UI (ps)")
        axis.set_ylabel("Best eye height (V)")
        axis.set_xscale("log")
        axis.set_xticks([250, 500, 1000, 2000], ["250", "500", "1000", "2000"])
        axis.legend(ncol=4, frameon=False, loc="best")
        style_axis(axis)
    figure.suptitle("Direct-load PRBS7 eye height versus UI", fontsize=18)
    figure.savefig(OUT_DIR / "plots" / "01_eye_height_vs_ui.png", dpi=180)
    plt.close(figure)

    figure, axes = plt.subplots(len(devices), 1, figsize=(14, 4.1 * len(devices)), constrained_layout=True)
    axes_array = np.atleast_1d(axes)
    for axis, device in zip(axes_array, devices):
        native_transistor = sorted(
            [
                row
                for row in metrics
                if row["device"] == device.device_id and row["flow"] == "hspice_transistor"
            ],
            key=lambda row: float_value(row, "ui_ps"),
        )
        if native_transistor:
            axis.plot(
                [float_value(row, "ui_ps") for row in native_transistor],
                [1000.0 * float_value(row, "pad_rmse_vs_native_v") for row in native_transistor],
                color=GRAY,
                marker="o",
                linewidth=2.0,
                label="native IBIS vs transistor",
            )
        for flow in ("ngspice_gate_state", "ngspice_hybrid"):
            selected = sorted(
                [
                    row
                    for row in metrics
                    if row["device"] == device.device_id and row["flow"] == flow
                ],
                key=lambda row: float_value(row, "ui_ps"),
            )
            if not selected:
                continue
            axis.plot(
                [float_value(row, "ui_ps") for row in selected],
                [1000.0 * float_value(row, "pad_rmse_vs_native_v") for row in selected],
                color=FLOW_COLORS[flow],
                marker="o",
                linewidth=2.0,
                label=f"{FLOW_LABELS[flow]} vs native",
            )
        axis.set_title(device.label)
        axis.set_xlabel("UI (ps)")
        axis.set_ylabel("Pad RMSE (mV)")
        axis.set_xscale("log")
        axis.set_xticks([250, 500, 1000, 2000], ["250", "500", "1000", "2000"])
        axis.legend(ncol=3, frameon=False, loc="best")
        style_axis(axis)
    figure.suptitle("Absolute-time PRBS7 pad correlation", fontsize=18)
    figure.savefig(OUT_DIR / "plots" / "02_pad_rmse_vs_ui.png", dpi=180)
    plt.close(figure)

    figure, axes = plt.subplots(len(devices), 2, figsize=(16, 4.1 * len(devices)), constrained_layout=True)
    axes_array = np.asarray(axes).reshape(len(devices), 2)
    for row_index, device in enumerate(devices):
        for column, coefficient in enumerate(("ku", "kd")):
            axis = axes_array[row_index, column]
            for flow in ("ngspice_gate_state", "ngspice_hybrid"):
                selected = sorted(
                    [
                        row
                        for row in metrics
                        if row["device"] == device.device_id and row["flow"] == flow
                    ],
                    key=lambda row: float_value(row, "ui_ps"),
                )
                if not selected:
                    continue
                axis.plot(
                    [float_value(row, "ui_ps") for row in selected],
                    [float_value(row, f"{coefficient}_rmse_vs_native") for row in selected],
                    color=FLOW_COLORS[flow],
                    marker="o",
                    linewidth=2.0,
                    label=FLOW_LABELS[flow],
                )
            axis.set_title(f"{device.label}: {coefficient.capitalize()}")
            axis.set_xlabel("UI (ps)")
            axis.set_ylabel("Coefficient RMSE")
            axis.set_xscale("log")
            axis.set_xticks([250, 500, 1000, 2000], ["250", "500", "1000", "2000"])
            axis.legend(frameon=False, loc="best")
            style_axis(axis)
    figure.suptitle("PRBS7 coefficient correlation versus native IBIS", fontsize=18)
    figure.savefig(OUT_DIR / "plots" / "03_coefficient_rmse_vs_ui.png", dpi=180)
    plt.close(figure)

    if history:
        figure, axes = plt.subplots(len(devices), 1, figsize=(14, 4.1 * len(devices)), constrained_layout=True)
        axes_array = np.atleast_1d(axes)
        for axis, device in zip(axes_array, devices):
            for flow in FLOW_LABELS:
                selected = sorted(
                    [
                        row
                        for row in history
                        if row["device"] == device.device_id and row["flow"] == flow
                    ],
                    key=lambda row: float_value(row, "ui_ps"),
                )
                if not selected:
                    continue
                axis.plot(
                    [float_value(row, "ui_ps") for row in selected],
                    [100.0 * float_value(row, "worst_history_spread_fraction") for row in selected],
                    color=FLOW_COLORS[flow],
                    marker="o",
                    linewidth=2.0,
                    label=FLOW_LABELS[flow],
                )
            axis.set_title(device.label)
            axis.set_xlabel("UI (ps)")
            axis.set_ylabel("3-bit history spread (% swing)")
            axis.set_xscale("log")
            axis.set_xticks([250, 500, 1000, 2000], ["250", "500", "1000", "2000"])
            axis.legend(ncol=4, frameon=False, loc="best")
            style_axis(axis)
        figure.suptitle("Pattern-dependent sample spread", fontsize=18)
        figure.savefig(OUT_DIR / "plots" / "04_history_spread_vs_ui.png", dpi=180)
        plt.close(figure)

    figure, axes = plt.subplots(
        len(devices),
        1,
        figsize=(14, 3.8 * len(devices)),
        constrained_layout=True,
    )
    axes_array = np.atleast_1d(axes)
    for axis, device in zip(axes_array, devices):
        selected = sorted(
            [
                row
                for row in metrics
                if row["device"] == device.device_id
                and row["flow"] == "ngspice_hybrid"
                and math.isfinite(float_value(row, "hybrid_active_fraction"))
            ],
            key=lambda row: float_value(row, "ui_ps"),
        )
        if selected:
            ui_values = [float_value(row, "ui_ps") for row in selected]
            fractions = [
                100.0 * float_value(row, "hybrid_active_fraction")
                for row in selected
            ]
            axis.plot(
                ui_values,
                fractions,
                color="#7b2cbf",
                marker="o",
                markersize=7,
                linewidth=2.2,
            )
            for row, x, y in zip(selected, ui_values, fractions):
                count = int(float_value(row, "hybrid_activation_count"))
                axis.annotate(
                    f"{count} event{'s' if count != 1 else ''}",
                    (x, y),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=9,
                )
        axis.set_title(device.label)
        axis.set_xlabel("UI (ps)")
        axis.set_ylabel("Gate-state active time (%)")
        axis.set_xscale("log")
        axis.set_xticks([250, 500, 1000, 2000], ["250", "500", "1000", "2000"])
        axis.set_ylim(-4.0, 100.0)
        style_axis(axis)
    figure.suptitle("Hybrid gate-state activation", fontsize=18)
    figure.savefig(OUT_DIR / "plots" / "05_hybrid_activation_vs_ui.png", dpi=180)
    plt.close(figure)


def write_plan() -> None:
    lines = [
        "# Phase 1 Plan: Direct-Load PRBS7 History Study",
        "",
        "## Objective",
        "",
        "Measure whether the three buffer representations preserve waveform and internal-state history under a realistic repeated bit stream before a channel is introduced.",
        "",
        "## Fixed Electrical Setup",
        "",
        "- Devices: `io_buf`, `inv_chain`, and `ex2`.",
        "- IBIS input: fast-edge model for each device.",
        "- PRBS: deterministic PRBS7, polynomial `x^7 + x^6 + 1`, 127 bits.",
        "- Runtime edge: 50 ps.",
        "- UI sweep: 2 ns, 1 ns, 500 ps, and 250 ps.",
        "- Load: direct `50 ohm || 2 pF`.",
        "- HSPICE simulates two full PRBS periods.",
        "- ngspice simulates and analyzes the first 31 PRBS7 bits plus recovery.",
        "- Those 31 bits contain all eight possible previous/current/next-bit contexts.",
        "- The bounded ngspice window is required because longer gate-state runs exposed a reproducible numerical stall.",
        "",
        "## Flows",
        "",
        "1. HSPICE transistor reference.",
        "2. HSPICE native IBIS.",
        "3. ngspice full gate-state model.",
        "4. ngspice legacy-normal/gate-on-reversal hybrid.",
        "",
        "## Evidence",
        "",
        "- Absolute-time pad, Ku, and Kd agreement.",
        "- Independently optimized eye height, eye width, and sample delay.",
        "- Three-bit (`previous/current/next`) history classes.",
        "- Worst-bit waveform windows.",
        "- Full numeric waveforms behind every case.",
        "",
        "## Interpretation Boundary",
        "",
        "No transmission line is used in Phase 1. This intentionally isolates buffer and switching-state behavior. A matched line belongs in Phase 2 after this direct-load baseline is understood.",
        "",
        "The bounded ngspice window contains every three-bit context. Longer-stream failure attempts remain in `solver_attempts.csv`; they are evidence, not discarded runs.",
    ]
    write_text(OUT_DIR / "PHASE1_PLAN.md", "\n".join(lines) + "\n")


def sequence_contact_sheet(paths: list[Path], output: Path) -> None:
    if not paths:
        return
    images = [plt.imread(path) for path in paths]
    columns = 2
    rows = int(math.ceil(len(images) / columns))
    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(15.0, 5.8 * rows),
        constrained_layout=True,
    )
    flat = np.asarray(axes, dtype=object).reshape(-1)
    for axis, image in zip(flat, images):
        axis.imshow(image)
        axis.axis("off")
    for axis in flat[len(images) :]:
        axis.axis("off")
    ensure_dir(output.parent)
    figure.savefig(output, dpi=130)
    plt.close(figure)


def report() -> None:
    scan_solver_attempts()
    plot_setup()
    run_manifest = read_csv(OUT_DIR / "run_manifest.csv")
    metrics = read_csv(OUT_DIR / "metrics.csv")
    eye_data = read_csv(OUT_DIR / "eye_metrics.csv")
    pattern_data = read_csv(OUT_DIR / "pattern_metrics.csv")
    worst_data = read_csv(OUT_DIR / "worst_bit_metrics.csv")
    all_case_plots: dict[str, list[Path]] = {}
    all_hybrid_events: list[dict[str, object]] = []
    hybrid_event_summary: list[dict[str, object]] = []
    for device in base.DEVICES:
        for case in cases():
            path = waveform_path(device, case)
            if not path.exists():
                continue
            data = load_waveform(path)
            case_eyes = [
                dict(row)
                for row in eye_data
                if row["device"] == device.device_id and row["case_id"] == case.case_id
            ]
            case_patterns = [
                dict(row)
                for row in pattern_data
                if row["device"] == device.device_id and row["case_id"] == case.case_id
            ]
            case_worst = [
                dict(row)
                for row in worst_data
                if row["device"] == device.device_id and row["case_id"] == case.case_id
            ]
            if not case_eyes:
                continue
            case_events = hybrid_event_rows(device, case, data)
            all_hybrid_events.extend(case_events)
            hybrid_key = "ngspice_hybrid_hhybridactive"
            if hybrid_key in data:
                active_mask = analysis_mask(case, data["time_ns"])
                active = data[hybrid_key][active_mask] > 0.5
                active_fraction = float(np.mean(active))
                active_duration_ns = float(np.count_nonzero(active) * TRAN_STEP_NS)
                availability = "AVAILABLE"
            else:
                active_fraction = float("nan")
                active_duration_ns = float("nan")
                availability = "UNAVAILABLE"
            event_kinds = sorted({str(row["event_kind"]) for row in case_events})
            hybrid_event_summary.append(
                {
                    "device": device.device_id,
                    "case_id": case.case_id,
                    "ui_ps": case.ui_ns * 1000.0,
                    "hybrid_data_status": availability,
                    "activation_count": len(case_events),
                    "active_fraction": active_fraction,
                    "active_percent": 100.0 * active_fraction,
                    "active_duration_ns": active_duration_ns,
                    "event_kinds": ";".join(event_kinds),
                }
            )
            outputs = plot_case(
                device,
                case,
                data,
                case_eyes,
                case_patterns,
                case_worst,
            )
            all_case_plots.setdefault(device.device_id, []).append(outputs[0])
    write_csv(OUT_DIR / "hybrid_events.csv", all_hybrid_events)
    write_csv(OUT_DIR / "hybrid_event_summary.csv", hybrid_event_summary)
    for device_id, paths in all_case_plots.items():
        sequence_contact_sheet(
            paths,
            OUT_DIR / "plots" / f"10_{device_id}_sequence_overview.png",
        )
    summary_plots()

    completed = sum(row.get("status") == "COMPLETED" for row in run_manifest)
    failures = [row for row in run_manifest if row.get("status") not in {"COMPLETED", ""}]
    simulated_cases = {
        (row.get("device", ""), row.get("case_id", ""))
        for row in run_manifest
        if row.get("status") == "COMPLETED"
    }

    lines = [
        "# Three-Buffer Direct-Load PRBS7 Phase 1",
        "",
        "This study replaces isolated pulses with a repeated PRBS7 stream while keeping the electrical bench deliberately simple.",
        "",
        "## Fixed Setup",
        "",
        "- Fast-edge IBIS files only.",
        "- Deterministic PRBS7: `x^7 + x^6 + 1`, 127 bits.",
        "- HSPICE: two complete periods.",
        "- ngspice: first 31 PRBS7 bits plus recovery; all eight three-bit histories are present.",
        "- Longer ngspice failures are retained in `solver_attempts.csv`.",
        "- Runtime rise/fall: 50 ps.",
        "- UI sweep: 2 ns, 1 ns, 500 ps, 250 ps.",
        "- Direct load: `50 ohm || 2 pF`.",
        "- Flows: HSPICE transistor, HSPICE native IBIS, ngspice gate-state, ngspice hybrid.",
        "- No transmission line in Phase 1.",
        "",
        "## Start Here",
        "",
        "- `plots/00_testbench_and_stimulus.png`: exact Phase 1 concept and PRBS stimulus.",
        "- `plots/01_eye_height_vs_ui.png`: eye opening across buffers and UI.",
        "- `plots/02_pad_rmse_vs_ui.png`: absolute-time pad correlation.",
        "- `plots/03_coefficient_rmse_vs_ui.png`: Ku/Kd agreement with native IBIS.",
        "- `plots/04_history_spread_vs_ui.png`: pattern-history sensitivity.",
        "- `plots/05_hybrid_activation_vs_ui.png`: when and how often the hybrid actually used gate state.",
        "- `plots/10_<device>_sequence_overview.png`: 32-UI excerpts for each UI.",
        "- `plots/cases/<device>/<case>/02_pad_eyes.png`: readable two-UI pad eyes on common axes.",
        "- `plots/cases/<device>/<case>/03_coefficient_eyes.png`: two-UI Ku/Kd eyes.",
        "- `plots/cases/<device>/<case>/06_hybrid_activation_events.png`: event-by-event hybrid mode trace.",
        "",
        "## Reproduce Or Resume",
        "",
        "```powershell",
        "py -3.14 scripts/run_three_buffer_prbs_phase1.py `",
        "  --study-dir results/three_buffer_prbs_phase1_2026-07-31 `",
        "  --solver-profile gear_relaxed `",
        "  --timeout-s 900",
        "```",
        "",
        "The runner reuses completed artifacts. Add `--retry-failures` only when intentionally retrying numeric failures. Rebuild plots without simulation using:",
        "",
        "```powershell",
        "py -3.14 scripts/run_three_buffer_prbs_phase1.py `",
        "  --study-dir results/three_buffer_prbs_phase1_2026-07-31 `",
        "  --report-only",
        "```",
        "",
        "## Numeric Data",
        "",
        "- `waveforms/<device>/<case>.csv`: full aligned numeric waveform data.",
        "- `metrics.csv`: pad and coefficient correlation.",
        "- `eye_metrics.csv`: eye height, width, delay, and sample BER.",
        "- `pattern_metrics.csv`: all three-bit history-class samples.",
        "- `history_metrics.csv`: compact history-spread metrics.",
        "- `worst_bit_metrics.csv`: worst candidate bit per case.",
        "- `hybrid_event_summary.csv`: activation count and active time for every hybrid run.",
        "- `hybrid_events.csv`: start/stop, direction, state, and error values for each activation event.",
        "- `run_manifest.csv`: raw/log paths and resume/cache provenance.",
        "- `prbs7_bits.csv`: exact 127-bit sequence.",
        "",
        "## Run Status",
        "",
        f"- Completed simulator flows: `{completed}`.",
        f"- Completed device/UI combinations represented: `{len(simulated_cases)}`.",
        f"- Failed or incomplete flows: `{len(failures)}`.",
    ]
    if metrics and eye_data:
        def selected_row(
            rows: list[dict[str, str]],
            device_id: str,
            ui_ps: float,
            flow: str,
        ) -> dict[str, str]:
            return next(
                (
                    row
                    for row in rows
                    if row.get("device") == device_id
                    and row.get("flow") == flow
                    and abs(float_value(row, "ui_ps") - ui_ps) < 1e-6
                ),
                {},
            )

        def eye(device_id: str, ui_ps: float, flow: str) -> float:
            return float_value(
                selected_row(eye_data, device_id, ui_ps, flow),
                "eye_height_v",
            )

        def metric(device_id: str, ui_ps: float, flow: str, name: str) -> float:
            return float_value(
                selected_row(metrics, device_id, ui_ps, flow),
                name,
            )

        lines.extend(["", "## Measured Findings", ""])
        lines.extend(
            [
                "### Reference behavior",
                "",
                f"- `inv_chain` is the clean reference case. At 250 ps UI, the "
                f"transistor/native-IBIS eye heights are `{eye('inv_chain', 250, 'hspice_transistor'):.3f} / "
                f"{eye('inv_chain', 250, 'hspice_native_ibis'):.3f} V`; both references remain open at every UI.",
                f"- `ex2` has a clear physical bandwidth boundary. The transistor/native-IBIS eyes are "
                f"`{eye('ex2', 1000, 'hspice_transistor'):.3f} / {eye('ex2', 1000, 'hspice_native_ibis'):.3f} V` "
                f"at 1 ns, but `{eye('ex2', 500, 'hspice_transistor'):.3f} / "
                f"{eye('ex2', 500, 'hspice_native_ibis'):.3f} V` at 500 ps.",
                f"- `io_buf` is already marginal at 1 ns. Its transistor/native-IBIS eyes are "
                f"`{eye('io_buf', 2000, 'hspice_transistor'):.3f} / {eye('io_buf', 2000, 'hspice_native_ibis'):.3f} V` "
                f"at 2 ns and `{eye('io_buf', 1000, 'hspice_transistor'):.3f} / "
                f"{eye('io_buf', 1000, 'hspice_native_ibis'):.3f} V` at 1 ns.",
                "",
                "### Candidate behavior",
                "",
                f"- For `inv_chain`, the hybrid preserves a `{eye('inv_chain', 500, 'ngspice_hybrid'):.3f} V` "
                f"eye at 500 ps, but its gate-state active fraction is "
                f"`{metric('inv_chain', 500, 'ngspice_hybrid', 'hybrid_active_fraction'):.3f}`. "
                "That is legacy-path preservation, not proof that the reversal correction improved the stream.",
                f"- For `ex2` at 500 ps, both HSPICE references are closed while the hybrid reports a "
                f"`{eye('ex2', 500, 'ngspice_hybrid'):.3f} V` eye. This is a false-open result; the hybrid cannot "
                "be trusted at that stress point.",
                f"- For `io_buf` at 1 ns, the hybrid reports a `{eye('io_buf', 1000, 'ngspice_hybrid'):.3f} V` eye "
                "while both references are marginal or closed. Its Ku/Kd also leave the accepted coefficient range.",
                "- Gate state was actually triggered in completed runs for `io_buf` at 1 ns, 500 ps, and 250 ps; "
                "for `ex2` at 500 ps and 250 ps; and for `inv_chain` only at 250 ps.",
                "- It was not triggered for completed `inv_chain` runs at 1 ns or 500 ps, or `ex2` runs at 2 ns or 1 ns. "
                "Any hybrid advantage there is legacy-path preservation, not gate-state improvement.",
                "- Across the completed cases, neither the full gate-state nor hybrid candidate is generally trustworthy. "
                "The result depends strongly on buffer structure and UI.",
                "",
                "### How to read the plots",
                "",
                "- Eye height is optimized independently for each flow at that flow's best sampling phase. It measures usable opening, not absolute timing agreement.",
                "- Each eye panel now spans two UIs around the best sample. Colored dots at time zero are the actual bit samples; the dotted horizontal line is that flow's decision threshold.",
                "- Pad RMSE uses the common absolute time axis. A candidate can have an open eye and still have poor waveform or timing correlation.",
                "- A candidate eye that stays open after both HSPICE references close is a false-open warning, not an improvement.",
                "- These are direct-load results. The observed closure and history dependence cannot be blamed on transmission-line reflection or channel ISI.",
            ]
        )

        solver_profiles = sorted(
            {
                row.get("solver_profile", "")
                for row in run_manifest
                if row.get("flow", "").startswith("ngspice")
                and row.get("solver_profile", "")
            }
        )
        lines.extend(
            [
                "",
                "## Numerical Scope",
                "",
                f"- Selected ngspice solver profile(s): `{', '.join(solver_profiles)}`.",
                "- The final matrix uses a bounded 31-bit window because longer gate-state PRBS runs reproducibly stopped making progress.",
                "- The bounded window still contains all eight three-bit histories, so it is sufficient for this Phase 1 history comparison.",
                "- The long-stream stalls and three final numeric failures mean the experimental state models are not yet production-scalable.",
                "- `solver_attempts.csv` retains the strict-Gear, relaxed-Gear, and relaxed-Trap attempts; failed work was not discarded.",
                "",
                "## Phase 1 Conclusion",
                "",
                "The direct-load PRBS study is complete enough to answer the first question: repeated-data behavior is not universally fixed by the current gate-state or hybrid model. "
                "`inv_chain` remains the strongest case, while `io_buf` exposes coefficient-range, waveform, and solver-sensitivity problems, and `ex2` exposes a clear false-open hybrid eye at 500 ps.",
                "",
                "The next experiment should not add a transmission line yet. First, make the ngspice state implementation numerically bounded for a full 127-bit period and add an automatic "
                "false-open gate that rejects any candidate whose eye remains open after both HSPICE references close. Once that passes, Phase 2 can add a matched line to separate driver-history error from channel ISI.",
            ]
        )
    if failures:
        lines.extend(["", "## Failed/Incomplete Flows", ""])
        for row in failures:
            lines.append(
                f"- `{row.get('device')} / {row.get('case_id')} / "
                f"{row.get('flow')}`: `{row.get('status')}`"
            )
    write_text(OUT_DIR / "README.md", "\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> None:
    selected_devices = [
        device for device in base.DEVICES if device.device_id in args.devices
    ]
    selected_cases = cases(tuple(args.uis_ns))
    total = len(selected_devices) * len(selected_cases)
    index = 0
    for device in selected_devices:
        profile = fast_profile(device)
        models = base.prepare_ngspice_models(
            device,
            profile,
            OUT_DIR / "models" / device.device_id,
        )
        for case in selected_cases:
            index += 1
            print(
                f"[{index}/{total}] {device.device_id} | UI "
                f"{base.fmt(case.ui_ns * 1000)} ps",
                flush=True,
            )
            case_run_rows: list[dict[str, object]] = []
            try:
                transistor_raw, row = run_hspice_transistor(
                    device,
                    case,
                    args.hspice,
                    args.timeout_s,
                )
                case_run_rows.append(row)
            except Exception as exc:
                case_run_rows.append(
                    {
                        "device": device.device_id,
                        "case_id": case.case_id,
                        "ui_ps": case.ui_ns * 1000,
                        "flow": "hspice_transistor",
                        "status": "FAILED",
                        "error": str(exc),
                    }
                )
                upsert_rows(
                    OUT_DIR / "run_manifest.csv",
                    case_run_rows,
                    ("device", "case_id", "flow"),
                )
                print(f"  HSPICE transistor failed: {exc}", flush=True)
                continue
            try:
                native_raw, row = run_hspice_native(
                    device,
                    case,
                    profile,
                    args.hspice,
                    args.timeout_s,
                )
                case_run_rows.append(row)
            except Exception as exc:
                case_run_rows.append(
                    {
                        "device": device.device_id,
                        "case_id": case.case_id,
                        "ui_ps": case.ui_ns * 1000,
                        "flow": "hspice_native_ibis",
                        "status": "FAILED",
                        "error": str(exc),
                    }
                )
                upsert_rows(
                    OUT_DIR / "run_manifest.csv",
                    case_run_rows,
                    ("device", "case_id", "flow"),
                )
                print(f"  HSPICE native IBIS failed: {exc}", flush=True)
                continue

            transistor = base.transistor_waveform(device, transistor_raw)
            native = base.native_waveform(native_raw)
            candidates: dict[str, dict[str, np.ndarray] | None] = {}
            for flow, mode, model_key in (
                (
                    "ngspice_gate_state",
                    base.FULL_MODE,
                    "gate_state",
                ),
                (
                    "ngspice_hybrid",
                    base.HYBRID_MODE,
                    "hybrid",
                ),
            ):
                raw, row = run_ngspice(
                    device,
                    case,
                    flow,
                    mode,
                    models[model_key],
                    args.ngspice,
                    args.timeout_s,
                    args.retry_failures,
                    args.solver_profile,
                )
                case_run_rows.append(row)
                candidates[flow] = base.ngspice_waveform(raw) if raw is not None else None

            upsert_rows(
                OUT_DIR / "run_manifest.csv",
                case_run_rows,
                ("device", "case_id", "flow"),
            )
            upsert_rows(
                OUT_DIR / "solver_attempts.csv",
                [
                    row
                    for row in case_run_rows
                    if str(row.get("flow", "")).startswith("ngspice_")
                ],
                ("device", "case_id", "flow", "solver_profile", "log"),
            )
            scan_solver_attempts()
            data = aligned_data(device, case, transistor, native, candidates)
            save_waveform(waveform_path(device, case), data)
            metrics = metric_rows(device, case, data, case_run_rows)
            eyes = eye_rows(device, case, data)
            patterns, history = pattern_rows(device, case, data, eyes)
            worst = worst_bit_rows(device, case, data, eyes)
            upsert_rows(
                OUT_DIR / "metrics.csv",
                metrics,
                ("device", "case_id", "flow"),
            )
            upsert_rows(
                OUT_DIR / "eye_metrics.csv",
                eyes,
                ("device", "case_id", "flow"),
            )
            upsert_rows(
                OUT_DIR / "pattern_metrics.csv",
                patterns,
                ("device", "case_id", "flow", "pattern"),
            )
            upsert_rows(
                OUT_DIR / "history_metrics.csv",
                history,
                ("device", "case_id", "flow"),
            )
            upsert_rows(
                OUT_DIR / "worst_bit_metrics.csv",
                worst,
                ("device", "case_id", "flow"),
            )
            print("  case data and metrics written", flush=True)
    report()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase-1 direct-load PRBS7 study for the three buffer cases."
    )
    parser.add_argument("--hspice", type=Path, default=base.DEFAULT_HSPICE)
    parser.add_argument("--ngspice", type=Path, default=base.DEFAULT_NGSPICE)
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument(
        "--devices",
        nargs="+",
        choices=[device.device_id for device in base.DEVICES],
        default=[device.device_id for device in base.DEVICES],
    )
    parser.add_argument(
        "--uis-ns",
        nargs="+",
        type=float,
        default=list(UI_VALUES_NS),
    )
    parser.add_argument("--retry-failures", action="store_true")
    parser.add_argument(
        "--solver-profile",
        choices=sorted(SOLVER_PROFILES),
        default="trap_relaxed",
        help="ngspice numerical profile; model equations are unchanged",
    )
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--study-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    global OUT_DIR
    args = parse_args()
    if args.study_dir is not None:
        OUT_DIR = args.study_dir if args.study_dir.is_absolute() else ROOT / args.study_dir
    ensure_dir(OUT_DIR)
    preserve_solver_attempts()
    write_plan()
    write_csv(
        OUT_DIR / "prbs7_bits.csv",
        [
            {"bit_index": index, "bit": bit}
            for index, bit in enumerate(BITS)
        ],
    )
    if args.report_only:
        report()
    else:
        run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
