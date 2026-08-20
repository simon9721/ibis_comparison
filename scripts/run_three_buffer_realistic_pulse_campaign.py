from __future__ import annotations

import argparse
import csv
import hashlib
import math
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
SCRIPTS = ROOT / "scripts"
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
for path in [ROOT, SCRIPTS, PYBIS_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from hspice_reference_cache import (  # noqa: E402
    cache_dir,
    reference_signature,
    restore as restore_hspice_cache,
    save as save_hspice_cache,
)
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402
from tools.figure_editor.figure_document import (  # noqa: E402
    FigureRecipe,
    FigureStyle,
    SeriesStyle,
)


OUT_DIR = ROOT / "results" / "three_buffer_realistic_pulse_2026-07-30"
DEFAULT_HSPICE = default_hspice()
DEFAULT_NGSPICE = default_ngspice(console=True)

EDGE_RATES_NS = (0.100, 0.250)
EDGE_CHARACTERIZATION_NS = (0.050, 0.100, 0.250)
TARGET_EXCURSIONS = (0.20, 0.55, 0.85)
TARGET_LABELS = ("visible", "mid_transition", "near_settled")
LOAD_OHM = 50.0
LOAD_PF = 2.0
TRAN_STEP_NS = 0.002
COEFFICIENT_ENVELOPE_MARGIN = 0.10

FULL_MODE = "InputDrivenTwoStateGateDirectionalDualResidualFull"
HYBRID_MODE = "InputDrivenTwoStateGateDirectionalDualResidualHybrid"

BLACK = "#111111"
GRAY = "#777777"
RED = "#d62728"
PURPLE = "#7b2cbf"
BLUE = "#1769aa"
GREEN = "#008b6e"
ORANGE = "#d97706"
GRID = "#d9dde3"
EDGE_COLOR = "#8b8b8b"
TRANSISTOR_CONTROL_LABELS = {
    "io_buf": (
        "n2: PMOS pullup gate / VDD",
        "n3: NMOS pulldown gate / VDD",
    ),
    "inv_chain": ("VOUT7: final inverter input / VDD",),
    "ex2": ("n4: output-stage gate / VDD",),
}


@dataclass(frozen=True)
class Device:
    device_id: str
    label: str
    process: str
    supply_v: float
    component: str
    model: str
    subckt: str
    enable_v: float
    slow_ibis: Path
    fast_ibis: Path
    transistor_files: tuple[Path, ...]
    transistor_probe_nodes: tuple[str, ...]


@dataclass(frozen=True)
class Profile:
    profile_id: str
    label: str
    ibis: Path


@dataclass(frozen=True)
class PulseCase:
    case_id: str
    edge_ns: float
    pattern: str
    pulse_width_ns: float
    stop_ns: float
    target_label: str = ""
    target_excursion: float = float("nan")


DEVICES = (
    Device(
        "io_buf",
        "io_buf",
        "TSMC-style 0.18 um BSIM3 output buffer",
        3.3,
        "MCM Driver 1",
        "driver",
        "driver_OutputInput_Typical",
        3.3,
        ROOT / "hspice" / "sparam" / "io_buf.ibs",
        # Regenerated at a 50 ps characterization edge. The former 5 ps file put
        # the whole C_comp*dV/dt term into its first sample, which corrupted the
        # endpoint, onset-delay and gate-map fits and made the gate-state model
        # fail to converge. A 20 ps candidate fixed the fits but still stalled
        # ngspice on this study's stimuli; 50 ps is the fastest edge that
        # converges. See results/io_buf_fast_edge_regen_2026-08-19/README.md
        ROOT / "results" / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs",
        # Stock card, not hspice_ngspice.mod. The RDSW=0 variant exists to stop
        # ngspice stalling on the small devices, but this reference runs under
        # HSPICE and zeroing RDSW makes the output stage ~12% stronger than the
        # I-V tables io_buf.ibs was characterised from -- a settled Kd of 1.118
        # that we were reading as a defect in the IBIS file.
        (ROOT / "models" / "io_buf.sp", ROOT / "models" / "hspice.mod"),
        ("v(xdut.n2)", "v(xdut.n3)"),
    ),
    Device(
        "inv_chain",
        "inv_chain",
        "HL18G 0.18 um eight-stage tapered inverter chain",
        1.8,
        "invchain",
        "driver2",
        "driver2_OutputInput_Typical",
        1.8,
        ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27" / "slow_1ns" / "inv_chain_slow_1ns.ibs",
        ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27" / "fast_5ps" / "inv_chain_fast_5ps.ibs",
        (
            ROOT / "inv_chain" / "clean_ibis_vs_pybis_matched_pkg" / "invchain_ref_ngspice.sub",
            ROOT / "inv_chain" / "clean_ibis_vs_pybis_matched_pkg" / "HL18G-S3.7S.lib",
        ),
        ("v(xdut.vout7)",),
    ),
    Device(
        "ex2",
        "ex2",
        "TSMC-style 0.18 um extracted four-stage output buffer",
        3.3,
        "MCM Driver 1",
        "driver",
        "driver_OutputInput_Typical",
        0.0,
        ROOT / "results" / "ex2_s2ibispy_slow_fast_2026-07-28" / "slow_1ns" / "ex2_slow_1ns.ibs",
        ROOT / "results" / "ex2_s2ibispy_slow_fast_2026-07-28" / "fast_5ps" / "ex2_fast_5ps.ibs",
        (ROOT / "ex2" / "buffer.sp", ROOT / "ex2" / "hspice.mod"),
        ("v(xdut.n4)",),
    ),
)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="ascii")


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


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-12:
        return str(int(round(value)))
    return f"{value:.12g}"


def edge_tag(edge_ns: float) -> str:
    return f"edge_{int(round(edge_ns * 1000))}ps"


def width_tag(width_ns: float) -> str:
    ps = int(round(width_ns * 1000))
    return f"{ps}ps" if ps < 1000 else f"{fmt(width_ns).replace('.', 'p')}ns"


def profiles(device: Device) -> tuple[Profile, ...]:
    return (
        Profile("slow_1ns", "slow 1 ns characterization IBIS", device.slow_ibis),
        Profile("fast_5ps", "fast 5 ps characterization IBIS", device.fast_ibis),
    )


def points(device: Device, case: PulseCase) -> list[tuple[float, float]]:
    edge = case.edge_ns
    high = device.supply_v
    if case.pattern in ("short_high", "short_low") and case.pulse_width_ns < edge:
        # The reverse edge would be emitted before the first edge finishes,
        # producing a PWL whose time column runs backwards. HSPICE accepts the
        # deck and returns something, so this must fail loudly rather than
        # yield a plausible-looking waveform from a malformed stimulus.
        raise ValueError(
            f"pulse width {case.pulse_width_ns * 1000:.3f} ps is shorter than the "
            f"{edge * 1000:.3f} ps input edge for case {case.case_id!r}; the input "
            "never reaches its full level, so this stimulus is not a valid "
            "short-pulse test. Use a faster input edge to reach this stress level."
        )
    if case.pattern == "rise_fall":
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + edge, high),
            (15.0, high),
            (15.0 + edge, 0.0),
            (case.stop_ns, 0.0),
        ]
    if case.pattern == "short_high":
        reverse = 5.0 + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + edge, high),
            (reverse, high),
            (reverse + edge, 0.0),
            (case.stop_ns, 0.0),
        ]
    if case.pattern == "short_low":
        reverse = 10.0 + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + edge, high),
            (10.0, high),
            (10.0 + edge, 0.0),
            (reverse, 0.0),
            (reverse + edge, high),
            (case.stop_ns, high),
        ]
    raise ValueError(case.pattern)


def pwl(device: Device, case: PulseCase) -> str:
    lines = ["Vin in_dig 0 PWL("]
    for time_ns, voltage in points(device, case):
        lines.append(f"+ {fmt(time_ns)}n {fmt(voltage)}")
    lines[-1] += " )"
    return "\n".join(lines)


def command_edges(device: Device, case: PulseCase) -> list[float]:
    result: list[float] = []
    pts = points(device, case)
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if abs(v1 - v0) > 1e-12:
            result.append(0.5 * (t0 + t1))
    return result


def input_waveform(device: Device, case: PulseCase, time_ns: np.ndarray) -> np.ndarray:
    pts = points(device, case)
    return np.interp(time_ns, [item[0] for item in pts], [item[1] for item in pts])


def _no_window_flags() -> int:
    """Windows creation flags that keep a child simulator off the desktop.

    A campaign launches hundreds of simulator processes. Without this each one
    can flash or park a console window, which makes a long run impossible to sit
    beside and can steal focus. Zero elsewhere, where the flag does not exist.
    """
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_process(command: list[str], cwd: Path, log_path: Path, timeout_s: int) -> int:
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s,
            check=False,
            creationflags=_no_window_flags(),
        )
    except subprocess.TimeoutExpired as exc:
        captured = exc.stdout or ""
        if isinstance(captured, bytes):
            captured = captured.decode("utf-8", errors="replace")
        log_path.write_text(
            "COMMAND: " + " ".join(command) + f"\n\nTIMEOUT after {timeout_s} seconds\n\n{captured}",
            encoding="utf-8",
            errors="replace",
        )
        return 124
    log_path.write_text(
        "COMMAND: " + " ".join(command) + "\n\n" + process.stdout,
        encoding="utf-8",
        errors="replace",
    )
    return int(process.returncode)


def normalized(raw: dict[str, np.ndarray]) -> dict[str, str]:
    return {key.lower().replace(":", "."): key for key in raw}


def signal(raw: dict[str, np.ndarray], *names: str) -> np.ndarray:
    lookup = normalized(raw)
    for name in names:
        key = lookup.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(raw[key], dtype=float)
    raise KeyError(f"missing {names}; available={sorted(raw)}")


def optional_signal(raw: dict[str, np.ndarray], *names: str) -> np.ndarray | None:
    try:
        return signal(raw, *names)
    except KeyError:
        return None


def hspice_cache_run(
    family: str,
    device: Device,
    case: PulseCase,
    deck_text: str,
    inputs: list[Path],
    out_dir: Path,
    stem: str,
    hspice: Path,
    timeout_s: int,
) -> str:
    metadata = {
        "family": family,
        "device": device.device_id,
        "case_id": case.case_id,
        "edge_ns": case.edge_ns,
        "pulse_width_ns": case.pulse_width_ns,
        "pattern": case.pattern,
        "load_ohm": LOAD_OHM,
        "load_pf": LOAD_PF,
    }
    signature_id, signature = reference_signature(deck_text, inputs, metadata)
    target_cache = cache_dir(family, case.case_id, signature_id)
    if restore_hspice_cache(target_cache, out_dir, stem, deck_text):
        return "cache"
    deck_path = out_dir / f"{stem}.sp"
    write_text(deck_path, deck_text)
    rc = run_process(
        [str(hspice), "-i", deck_path.name, "-o", stem],
        out_dir,
        out_dir / "hspice_stdout.log",
        timeout_s,
    )
    if rc != 0 or not (out_dir / f"{stem}.tr0").exists():
        raise RuntimeError(f"HSPICE failed: {device.device_id}/{case.case_id}; see {out_dir}")
    save_hspice_cache(target_cache, out_dir, stem, deck_text, signature)
    return "run"


def transistor_deck(device: Device, case: PulseCase) -> str:
    probes = " ".join(device.transistor_probe_nodes)
    if device.device_id == "io_buf":
        include = """.include 'hspice.mod'
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
    return f"""* realistic-pulse transistor reference
.title {device.device_id} transistor {case.case_id}
.option post=2 probe accurate ingold=2
.temp 27

{pwl(device, case)}

{include}
Rload pad_sp 0 {fmt(LOAD_OHM)}
Cload pad_sp 0 {fmt(LOAD_PF)}p

.probe tran V(in_dig) V(pad_sp) {probes}
.tran {fmt(TRAN_STEP_NS)}n {fmt(case.stop_ns)}n
.end
"""


def native_ibis_deck(device: Device, case: PulseCase, profile: Profile) -> str:
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
        instance = f"""VPU pu_ref 0 DC {fmt(device.supply_v)}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {fmt(device.supply_v)}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='input.ibs' model='{device.model}' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd"""
    return f"""* realistic-pulse HSPICE native IBIS
.title {device.device_id} {profile.profile_id} native IBIS {case.case_id}
.option post=2 probe accurate ingold=2
.temp 27

{pwl(device, case)}

{instance}
Rload pad_ibis 0 {fmt(LOAD_OHM)}
Cload pad_ibis 0 {fmt(LOAD_PF)}p

.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran {fmt(TRAN_STEP_NS)}n {fmt(case.stop_ns)}n
.end
"""


def ngspice_deck(device: Device, case: PulseCase, subckt_type: str) -> str:
    diagnostics = ""
    if subckt_type != "InputDriven":
        diagnostics = (
            " V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget)"
            " V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kuleg) V(xdrv.kdleg)"
            " V(xdrv.kutarget) V(xdrv.kdtarget)"
            " V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)"
            " V(xdrv.hreverseraw) V(xdrv.hsettled) V(xdrv.hhybridactive)"
            " V(xdrv.kures) V(xdrv.kdres) V(xdrv.guprate) V(xdrv.gdnrate)"
        )
    if subckt_type == "InputDrivenTwoStateGateLevelCommandFull":
        # The level-command block replaces the edge-integrating one, so its
        # nodes are absent from the shared diagnostic list above. Without them a
        # divergence can only be inferred from downstream signals.
        diagnostics += " V(xdrv.gupcmd) V(xdrv.gdncmd) V(xdrv.ninx) V(xdrv.hnx)"
    if subckt_type == "InputDrivenTwoStateGateDelayCommandFull":
        # Both delayed copies as well as the command, so a mistimed command can
        # be attributed to the delay line or to the way the two are combined.
        diagnostics += (
            " V(xdrv.gupcmd) V(xdrv.gdncmd) V(xdrv.ninx)"
            " V(xdrv.pucmda) V(xdrv.pucmdb) V(xdrv.pucmdlvl)"
            " V(xdrv.pdcmda) V(xdrv.pdcmdb) V(xdrv.pdcmdlvl)"
        )
    if subckt_type == "InputDrivenHybridV3AlignedReplay":
        diagnostics += (
            " V(xdrv.v3revedge) V(xdrv.v3latchpulse) V(xdrv.v3activate)"
            " V(xdrv.v3kupre) V(xdrv.v3kdpre)"
            " V(xdrv.v3kuvissamp) V(xdrv.v3kdvissamp)"
            " V(xdrv.v3kugatesamp) V(xdrv.v3kdgatesamp)"
            " V(xdrv.v3alignerrku) V(xdrv.v3alignerrkd) V(xdrv.v3gatealigned)"
            " V(xdrv.v3kuanchor) V(xdrv.v3kdanchor) V(xdrv.v3dir)"
            " V(xdrv.v3trku) V(xdrv.v3trkd) V(xdrv.v3tfku) V(xdrv.v3tfkd)"
            " V(xdrv.v3kustart) V(xdrv.v3kdstart)"
            " V(xdrv.v3t0) V(xdrv.v3elapsed) V(xdrv.v3kuarg) V(xdrv.v3kdarg)"
            " V(xdrv.v3kuprogress) V(xdrv.v3kdprogress)"
            " V(xdrv.v3kureplay) V(xdrv.v3kdreplay)"
            " V(xdrv.v3enderrku) V(xdrv.v3enderrkd) V(xdrv.v3done)"
            " V(xdrv.hv3active) V(xdrv.hv3pending) V(xdrv.v3prehold)"
        )
    return f"""* realistic-pulse ngspice
.title {device.device_id} {subckt_type} {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{pwl(device, case)}

Ven en_sig 0 DC {fmt(device.enable_v)}
Vdd vdd 0 DC {fmt(device.supply_v)}
.include '{device.subckt}.sub'
XDRV pad in_dig en_sig vdd 0 {device.subckt}
Rload pad 0 {fmt(LOAD_OHM)}
Cload pad 0 {fmt(LOAD_PF)}p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){diagnostics}
.tran {fmt(TRAN_STEP_NS)}n {fmt(case.stop_ns)}n
.end
"""


def copy_transistor_inputs(device: Device, out_dir: Path) -> None:
    if device.device_id == "io_buf":
        names = ("io_buf.sp", "hspice.mod")
    elif device.device_id == "inv_chain":
        names = ("invchain_ref_ngspice.sub", "HL18G-S3.7S.lib")
    else:
        names = ("buffer.sp", "hspice.mod")
    for source, name in zip(device.transistor_files, names):
        shutil.copy2(source, out_dir / name)


def run_transistor(
    device: Device,
    case: PulseCase,
    out_root: Path,
    hspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = out_root / device.device_id / edge_tag(case.edge_ns) / "transistor" / case.case_id
    ensure_dir(out_dir)
    copy_transistor_inputs(device, out_dir)
    stem = "run"
    deck = transistor_deck(device, case)
    source = hspice_cache_run(
        f"realistic_pulse_{device.device_id}_transistor",
        device,
        case,
        deck,
        list(device.transistor_files),
        out_dir,
        stem,
        hspice,
        timeout_s,
    )
    raw = parse_hspice_tr0(out_dir / "run.tr0")
    return raw, {
        "device": device.device_id,
        "edge_ps": case.edge_ns * 1000,
        "case_id": case.case_id,
        "reference": "hspice_transistor",
        "source": source,
        "tr0": str((out_dir / "run.tr0").relative_to(ROOT)),
    }


def run_native_ibis(
    device: Device,
    profile: Profile,
    case: PulseCase,
    out_root: Path,
    hspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = out_root / device.device_id / edge_tag(case.edge_ns) / profile.profile_id / "cases" / case.case_id / "hspice_native_ibis"
    ensure_dir(out_dir)
    shutil.copy2(profile.ibis, out_dir / "input.ibs")
    deck = native_ibis_deck(device, case, profile)
    source = hspice_cache_run(
        f"realistic_pulse_{device.device_id}_{profile.profile_id}_native",
        device,
        case,
        deck,
        [profile.ibis],
        out_dir,
        "run",
        hspice,
        timeout_s,
    )
    raw = parse_hspice_tr0(out_dir / "run.tr0")
    return raw, {
        "device": device.device_id,
        "profile": profile.profile_id,
        "edge_ps": case.edge_ns * 1000,
        "case_id": case.case_id,
        "reference": "hspice_native_ibis",
        "source": source,
        "tr0": str((out_dir / "run.tr0").relative_to(ROOT)),
    }


def prepare_ngspice_models(
    device: Device,
    profile: Profile,
    common_dir: Path,
) -> dict[str, Path]:
    ensure_dir(common_dir)
    ibis_copy = common_dir / "input.ibs"
    shutil.copy2(profile.ibis, ibis_copy)
    specs = {
        "gate_state": FULL_MODE,
        "hybrid": HYBRID_MODE,
    }
    result: dict[str, Path] = {}
    for flow, mode in specs.items():
        output = common_dir / flow / f"{device.subckt}.sub"
        convert_ibis_to_pybis(
            ibis_path=ibis_copy,
            output_path=output,
            component_name=device.component,
            model_name=device.model,
            io_type="Output",
            subcircuit_type=mode,
            corner="Typical",
        )
        result[flow] = output
    return result


def run_ngspice(
    device: Device,
    profile: Profile,
    case: PulseCase,
    flow: str,
    mode: str,
    model: Path,
    out_root: Path,
    ngspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray] | None, dict[str, object]]:
    out_dir = out_root / device.device_id / edge_tag(case.edge_ns) / profile.profile_id / "cases" / case.case_id / f"ngspice_{flow}"
    ensure_dir(out_dir)
    shutil.copy2(model, out_dir / f"{device.subckt}.sub")
    deck_path = out_dir / "run.sp"
    raw_path = out_dir / "run.raw"
    log_path = out_dir / "ngspice_stdout.log"
    if log_path.exists():
        prior_text = log_path.read_text(encoding="utf-8", errors="replace")
        if "TIMEOUT after" in prior_text or "Timestep too small" in prior_text:
            return None, {
                "device": device.device_id,
                "profile": profile.profile_id,
                "edge_ps": case.edge_ns * 1000,
                "case_id": case.case_id,
                "flow": flow,
                "return_code": 124,
                "status": "NUMERIC_FAIL",
                "source": "existing_failure",
                "raw": "",
                "log": str(log_path.relative_to(ROOT)),
            }
    if raw_path.exists():
        return parse_ngspice_raw(raw_path), {
            "device": device.device_id,
            "profile": profile.profile_id,
            "edge_ps": case.edge_ns * 1000,
            "case_id": case.case_id,
            "flow": flow,
            "return_code": 0,
            "status": "COMPLETED",
            "source": "existing_raw",
            "raw": str(raw_path.relative_to(ROOT)),
            "log": str(log_path.relative_to(ROOT)) if log_path.exists() else "",
        }
    write_text(deck_path, ngspice_deck(device, case, mode))
    rc = run_process(
        [str(ngspice), "-b", "-r", raw_path.name, deck_path.name],
        out_dir,
        log_path,
        timeout_s,
    )
    row: dict[str, object] = {
        "device": device.device_id,
        "profile": profile.profile_id,
        "edge_ps": case.edge_ns * 1000,
        "case_id": case.case_id,
        "flow": flow,
        "return_code": rc,
        "status": "COMPLETED" if rc == 0 and raw_path.exists() else "NUMERIC_FAIL",
        "source": "run",
        "raw": str(raw_path.relative_to(ROOT)) if raw_path.exists() else "",
        "log": str((out_dir / "ngspice_stdout.log").relative_to(ROOT)),
    }
    if rc != 0 or not raw_path.exists():
        return None, row
    return parse_ngspice_raw(raw_path), row


def crossing_time(
    time_ns: np.ndarray,
    values: np.ndarray,
    threshold: float,
    start_ns: float,
    stop_ns: float,
    rising: bool,
) -> float:
    mask = (time_ns >= start_ns) & (time_ns <= stop_ns)
    indexes = np.flatnonzero(mask)
    if len(indexes) < 2:
        return float("nan")
    for left, right in zip(indexes[:-1], indexes[1:]):
        y0 = values[left]
        y1 = values[right]
        crossed = y0 <= threshold < y1 if rising else y0 >= threshold > y1
        if not crossed or y1 == y0:
            continue
        fraction = (threshold - y0) / (y1 - y0)
        return float(time_ns[left] + fraction * (time_ns[right] - time_ns[left]))
    return float("nan")


def transistor_waveform(device: Device, raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    result = {
        "time_ns": signal(raw, "time") * 1e9,
        "input_v": signal(raw, "v(in_dig)"),
        "pad_v": signal(raw, "v(pad_sp)"),
    }
    for index, probe in enumerate(device.transistor_probe_nodes, start=1):
        values = optional_signal(raw, probe)
        if values is not None:
            result[f"control_{index}_v"] = values
    return result


def native_waveform(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "time_ns": signal(raw, "time") * 1e9,
        "input_v": signal(raw, "v(in_dig)"),
        "pad_v": signal(raw, "v(pad_ibis)"),
        "ku": signal(raw, "v(ku)"),
        "kd": signal(raw, "v(kd)"),
    }


def ngspice_waveform(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    result = {
        "time_ns": signal(raw, "time") * 1e9,
        "input_v": signal(raw, "v(in_dig)"),
        "pad_v": signal(raw, "v(pad)"),
        "ku": signal(raw, "v(xdrv.ku)", "v(xdrv:ku)"),
        "kd": signal(raw, "v(xdrv.kd)", "v(xdrv:kd)"),
    }
    for name in [
        "gup",
        "gdn",
        "guptarget",
        "gdntarget",
        "kugate",
        "kdgate",
        "kuleg",
        "kdleg",
        "kutarget",
        "kdtarget",
        "hfall_after_rise",
        "hrise_after_fall",
        "hreverseraw",
        "hsettled",
        "hhybridactive",
        "hhybridv2active",
        "v2kusamp",
        "v2kdsamp",
        "v2elapsed",
        "v2kuprogress",
        "v2kdprogress",
        "v2kureplay",
        "v2kdreplay",
        "v2starterrku",
        "v2starterrkd",
        "v2sample",
        "v3revedge",
        "v3latchpulse",
        "v3activate",
        "v3kupre",
        "v3kdpre",
        "v3kuvissamp",
        "v3kdvissamp",
        "v3kugatesamp",
        "v3kdgatesamp",
        "v3alignerrku",
        "v3alignerrkd",
        "v3gatealigned",
        "v3kuanchor",
        "v3kdanchor",
        "v3dir",
        "v3trku",
        "v3trkd",
        "v3tfku",
        "v3tfkd",
        "v3kustart",
        "v3kdstart",
        "v3t0",
        "v3elapsed",
        "v3kuarg",
        "v3kdarg",
        "v3kuprogress",
        "v3kdprogress",
        "v3kureplay",
        "v3kdreplay",
        "v3enderrku",
        "v3enderrkd",
        "v3done",
        "hv3active",
        "hv3pending",
        "v3prehold",
        "kures",
        "kdres",
        "guprate",
        "gdnrate",
    ]:
        values = optional_signal(raw, f"v(xdrv.{name})", f"v(xdrv:{name})")
        if values is not None:
            result[name] = values
    return result


def settled_levels(wave: dict[str, np.ndarray]) -> tuple[float, float]:
    time_ns = wave["time_ns"]
    pad = wave["pad_v"]
    low = float(np.median(pad[(time_ns >= 3.5) & (time_ns <= 4.8)]))
    high = float(np.median(pad[(time_ns >= 11.5) & (time_ns <= 14.5)]))
    return low, high


def characterize_normal(device: Device, case: PulseCase, wave: dict[str, np.ndarray]) -> dict[str, object]:
    time_ns = wave["time_ns"]
    pad = wave["pad_v"]
    low, high = settled_levels(wave)
    swing = high - low
    input_mid = 0.5 * device.supply_v
    pad_10 = low + 0.1 * swing
    pad_50 = low + 0.5 * swing
    pad_90 = low + 0.9 * swing
    in_rise = crossing_time(time_ns, wave["input_v"], input_mid, 4.5, 7.0, True)
    out_r10 = crossing_time(time_ns, pad, pad_10, 4.5, 10.0, True)
    out_r50 = crossing_time(time_ns, pad, pad_50, 4.5, 10.0, True)
    out_r90 = crossing_time(time_ns, pad, pad_90, 4.5, 10.0, True)
    in_fall = crossing_time(time_ns, wave["input_v"], input_mid, 14.5, 17.0, False)
    out_f90 = crossing_time(time_ns, pad, pad_90, 14.5, 20.0, False)
    out_f50 = crossing_time(time_ns, pad, pad_50, 14.5, 20.0, False)
    out_f10 = crossing_time(time_ns, pad, pad_10, 14.5, 20.0, False)
    return {
        "device": device.device_id,
        "process": device.process,
        "edge_ps": case.edge_ns * 1000,
        "loaded_low_v": low,
        "loaded_high_v": high,
        "loaded_swing_v": swing,
        "rise_delay_50_ps": (out_r50 - in_rise) * 1000,
        "rise_10_90_ps": (out_r90 - out_r10) * 1000,
        "fall_delay_50_ps": (out_f50 - in_fall) * 1000,
        "fall_90_10_ps": (out_f10 - out_f90) * 1000,
    }


def pulse_metrics(
    device: Device,
    case: PulseCase,
    wave: dict[str, np.ndarray],
    low: float,
    high: float,
) -> dict[str, object]:
    time_ns = wave["time_ns"]
    pad = wave["pad_v"]
    swing = max(high - low, 1e-12)
    edges = command_edges(device, case)
    reverse = edges[-1]
    window = (time_ns >= edges[0] - 0.5) & (time_ns <= reverse + 4.0)
    if case.pattern == "short_high":
        extreme = float(np.max(pad[window]))
        excursion = (extreme - low) / swing
        extreme_time = float(time_ns[np.flatnonzero(window)[int(np.argmax(pad[window]))]])
    else:
        extreme = float(np.min(pad[window]))
        excursion = (high - extreme) / swing
        extreme_time = float(time_ns[np.flatnonzero(window)[int(np.argmin(pad[window]))]])
    row: dict[str, object] = {
        "device": device.device_id,
        "edge_ps": case.edge_ns * 1000,
        "case_id": case.case_id,
        "direction": case.pattern,
        "pulse_width_ps": case.pulse_width_ns * 1000,
        "transistor_pad_extreme_v": extreme,
        "transistor_pad_extreme_time_ns": extreme_time,
        "transistor_excursion_fraction": excursion,
        "transistor_visible": excursion >= 0.05,
        "transistor_partial": 0.05 <= excursion <= 0.95,
    }
    for index in range(1, len(device.transistor_probe_nodes) + 1):
        key = f"control_{index}_v"
        if key not in wave:
            continue
        values = wave[key][window]
        minimum = float(np.min(values))
        maximum = float(np.max(values))
        row[f"control_{index}_min_v"] = minimum
        row[f"control_{index}_max_v"] = maximum
        row[f"control_{index}_low_fraction"] = minimum / device.supply_v
        row[f"control_{index}_high_fraction"] = maximum / device.supply_v
    return row


def candidate_widths(edge_ns: float, normal: dict[str, object], direction: str) -> list[float]:
    delay_ps = float(normal["rise_delay_50_ps"] if direction == "short_high" else normal["fall_delay_50_ps"])
    slew_ps = float(normal["rise_10_90_ps"] if direction == "short_high" else normal["fall_90_10_ps"])
    characteristic_ns = max(edge_ns, (max(delay_ps, 0.0) + max(slew_ps, 0.0)) * 1e-3)
    raw = [
        edge_ns,
        1.25 * edge_ns,
        1.5 * edge_ns,
        2.0 * edge_ns,
        0.35 * characteristic_ns,
        0.50 * characteristic_ns,
        0.70 * characteristic_ns,
        0.90 * characteristic_ns,
        1.10 * characteristic_ns,
        1.35 * characteristic_ns,
        1.70 * characteristic_ns,
        2.20 * characteristic_ns,
    ]
    return sorted({round(min(max(value, edge_ns), 4.0), 3) for value in raw})


def selected_cases(
    device: Device,
    edge_ns: float,
    direction: str,
    rows: list[dict[str, object]],
) -> list[PulseCase]:
    available = [
        row
        for row in rows
        if row["device"] == device.device_id
        and abs(float(row["edge_ps"]) - edge_ns * 1000) < 1e-6
        and row["direction"] == direction
    ]
    selected: list[PulseCase] = []
    used: set[str] = set()
    for label, target in zip(TARGET_LABELS, TARGET_EXCURSIONS):
        best = min(
            available,
            key=lambda row: (
                abs(float(row["transistor_excursion_fraction"]) - target),
                float(row["pulse_width_ps"]),
            ),
        )
        case_id = str(best["case_id"])
        if case_id in used:
            continue
        used.add(case_id)
        width_ns = float(best["pulse_width_ps"]) * 1e-3
        selected.append(
            PulseCase(
                case_id=f"{edge_tag(edge_ns)}_{label}_{direction}_{width_tag(width_ns)}",
                edge_ns=edge_ns,
                pattern=direction,
                pulse_width_ns=width_ns,
                stop_ns=20.0,
                target_label=label,
                target_excursion=target,
            )
        )
    return selected


def refinement_width(
    rows: list[dict[str, object]],
    target: float,
    edge_ns: float,
) -> float | None:
    ordered = sorted(rows, key=lambda row: float(row["pulse_width_ps"]))
    for left, right in zip(ordered[:-1], ordered[1:]):
        y0 = float(left["transistor_excursion_fraction"])
        y1 = float(right["transistor_excursion_fraction"])
        if (y0 - target) * (y1 - target) > 0 or abs(y1 - y0) < 1e-12:
            continue
        x0 = float(left["pulse_width_ps"]) * 1e-3
        x1 = float(right["pulse_width_ps"]) * 1e-3
        fraction = (target - y0) / (y1 - y0)
        return round(max(edge_ns, x0 + fraction * (x1 - x0)), 3)
    return None


def interp(wave: dict[str, np.ndarray], time_ns: np.ndarray, key: str) -> np.ndarray:
    return np.interp(time_ns, wave["time_ns"], wave[key])


def aligned_data(
    device: Device,
    case: PulseCase,
    transistor: dict[str, np.ndarray],
    native: dict[str, np.ndarray],
    flows: dict[str, dict[str, np.ndarray] | None],
) -> dict[str, np.ndarray]:
    edges = command_edges(device, case)
    start = max(0.0, edges[0] - 1.0)
    stop = min(case.stop_ns, edges[-1] + 5.0)
    time_ns = np.arange(start, stop + 0.5 * TRAN_STEP_NS, TRAN_STEP_NS)
    result = {
        "time_ns": time_ns,
        "input_v": input_waveform(device, case, time_ns),
        "hspice_transistor_pad_v": interp(transistor, time_ns, "pad_v"),
        "hspice_ibis_pad_v": interp(native, time_ns, "pad_v"),
        "hspice_ibis_ku": interp(native, time_ns, "ku"),
        "hspice_ibis_kd": interp(native, time_ns, "kd"),
    }
    for index in range(1, len(device.transistor_probe_nodes) + 1):
        key = f"control_{index}_v"
        if key in transistor:
            result[f"transistor_{key}"] = interp(transistor, time_ns, key)
    for flow, wave in flows.items():
        if wave is None:
            continue
        for key in ["pad_v", "ku", "kd"]:
            result[f"{flow}_{key}"] = interp(wave, time_ns, key)
        for key in [
            "gup",
            "gdn",
            "guptarget",
            "gdntarget",
            "hfall_after_rise",
            "hrise_after_fall",
            "hhybridactive",
        ]:
            if key in wave:
                result[f"{flow}_{key}"] = interp(wave, time_ns, key)
    return result


def rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.sqrt(np.mean((candidate - reference) ** 2)))


def comparison_metrics(
    device: Device,
    profile: Profile,
    case: PulseCase,
    data: dict[str, np.ndarray],
    run_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    native_limits = {
        "ku_min": float(np.min(data["hspice_ibis_ku"])),
        "ku_max": float(np.max(data["hspice_ibis_ku"])),
        "kd_min": float(np.min(data["hspice_ibis_kd"])),
        "kd_max": float(np.max(data["hspice_ibis_kd"])),
    }
    native_reference_extended_range = (
        native_limits["ku_min"] < -0.2
        or native_limits["ku_max"] > 1.2
        or native_limits["kd_min"] < -0.2
        or native_limits["kd_max"] > 1.2
    )
    rows: list[dict[str, object]] = [
        {
            "device": device.device_id,
            "profile": profile.profile_id,
            "edge_ps": case.edge_ns * 1000,
            "case_id": case.case_id,
            "target_label": case.target_label,
            "pulse_width_ps": case.pulse_width_ns * 1000,
            "flow": "hspice_transistor",
            "status": "REFERENCE",
            "pad_rmse_v": rmse(data["hspice_ibis_pad_v"], data["hspice_transistor_pad_v"]),
            **{f"native_{key}": value for key, value in native_limits.items()},
            "native_reference_extended_range": native_reference_extended_range,
        }
    ]
    statuses = {str(row["flow"]): str(row["status"]) for row in run_rows}
    for flow in ["gate_state", "hybrid"]:
        row: dict[str, object] = {
            "device": device.device_id,
            "profile": profile.profile_id,
            "edge_ps": case.edge_ns * 1000,
            "case_id": case.case_id,
            "target_label": case.target_label,
            "pulse_width_ps": case.pulse_width_ns * 1000,
            "flow": flow,
            "status": statuses.get(flow, "UNAVAILABLE"),
            **{f"native_{key}": value for key, value in native_limits.items()},
            "native_reference_extended_range": native_reference_extended_range,
            "native_envelope_margin": COEFFICIENT_ENVELOPE_MARGIN,
        }
        if f"{flow}_pad_v" in data:
            row.update(
                {
                    "pad_rmse_v": rmse(data["hspice_ibis_pad_v"], data[f"{flow}_pad_v"]),
                    "ku_rmse": rmse(data["hspice_ibis_ku"], data[f"{flow}_ku"]),
                    "kd_rmse": rmse(data["hspice_ibis_kd"], data[f"{flow}_kd"]),
                    "ku_min": float(np.min(data[f"{flow}_ku"])),
                    "ku_max": float(np.max(data[f"{flow}_ku"])),
                    "kd_min": float(np.min(data[f"{flow}_kd"])),
                    "kd_max": float(np.max(data[f"{flow}_kd"])),
                    "max_ku_step": float(np.max(np.abs(np.diff(data[f"{flow}_ku"])))),
                    "max_kd_step": float(np.max(np.abs(np.diff(data[f"{flow}_kd"])))),
                }
            )
            coefficient_absolute_range_ok = (
                float(row["ku_min"]) >= -0.2
                and float(row["ku_max"]) <= 1.2
                and float(row["kd_min"]) >= -0.2
                and float(row["kd_max"]) <= 1.2
            )
            coefficient_native_envelope_ok = (
                float(row["ku_min"]) >= native_limits["ku_min"] - COEFFICIENT_ENVELOPE_MARGIN
                and float(row["ku_max"]) <= native_limits["ku_max"] + COEFFICIENT_ENVELOPE_MARGIN
                and float(row["kd_min"]) >= native_limits["kd_min"] - COEFFICIENT_ENVELOPE_MARGIN
                and float(row["kd_max"]) <= native_limits["kd_max"] + COEFFICIENT_ENVELOPE_MARGIN
            )
            row["coefficient_absolute_range_ok"] = coefficient_absolute_range_ok
            row["coefficient_native_envelope_ok"] = coefficient_native_envelope_ok
            # Backward-compatible alias: validity is now judged against the
            # actual native reference, not a universal coefficient interval.
            row["coefficient_range_ok"] = coefficient_native_envelope_ok
            if not coefficient_native_envelope_ok:
                row["status"] = "COEFFICIENT_OUTSIDE_NATIVE_ENVELOPE"
            elif max(float(row["max_ku_step"]), float(row["max_kd_step"])) > 0.1:
                row["status"] = "COEFFICIENT_DISCONTINUITY"
            if flow == "hybrid" and "hybrid_hhybridactive" in data:
                active = data["hybrid_hhybridactive"] > 0.5
                row["hybrid_active"] = bool(np.any(active))
                row["hybrid_active_duration_ns"] = float(np.trapezoid(active.astype(float), data["time_ns"]))
        rows.append(row)
    return rows


def save_waveform(path: Path, data: dict[str, np.ndarray]) -> None:
    write_csv(
        path,
        [
            {key: float(values[index]) for key, values in data.items()}
            for index in range(len(data["time_ns"]))
        ],
    )


def save_editable_recipes(
    device: Device,
    profile: Profile,
    case: PulseCase,
    waveform: Path,
) -> list[Path]:
    recipe_dir = waveform.parent.parent / "editable_figures"
    ensure_dir(recipe_dir)
    title_prefix = (
        f"{device.label} | "
        f"{fmt(case.edge_ns * 1000)} ps edge, {fmt(case.pulse_width_ns * 1000)} ps pulse"
    )
    definitions = {
        "pad": (
            "Pad voltage (V)",
            [
                SeriesStyle("hspice_ibis_pad_v", "HSPICE native IBIS", BLACK, 3.1, zorder=5),
                SeriesStyle("hspice_transistor_pad_v", "HSPICE transistor", GRAY, 2.8, zorder=2),
                SeriesStyle("gate_state_pad_v", "Gate state model", RED, 2.0, zorder=4),
                SeriesStyle("hybrid_pad_v", "Hybrid model", PURPLE, 2.0, zorder=3),
            ],
        ),
        "ku": (
            "Ku",
            [
                SeriesStyle("hspice_ibis_ku", "HSPICE native IBIS", BLACK, 3.1, zorder=5),
                SeriesStyle("gate_state_ku", "Gate state model", RED, 2.0, zorder=4),
                SeriesStyle("hybrid_ku", "Hybrid model", PURPLE, 2.0, zorder=3),
            ],
        ),
        "kd": (
            "Kd",
            [
                SeriesStyle("hspice_ibis_kd", "HSPICE native IBIS", BLACK, 3.1, zorder=5),
                SeriesStyle("gate_state_kd", "Gate state model", RED, 2.0, zorder=4),
                SeriesStyle("hybrid_kd", "Hybrid model", PURPLE, 2.0, zorder=3),
            ],
        ),
    }
    outputs: list[Path] = []
    for name, (ylabel, series) in definitions.items():
        recipe = FigureRecipe(
            csv_path=str(waveform.resolve()),
            x_column="time_ns",
            series=series,
            figure=FigureStyle(
                title=f"{title_prefix} | {ylabel}",
                xlabel="Time (ns)",
                ylabel=ylabel,
                title_size=15,
                label_size=12,
                tick_size=10,
                legend_size=10,
                legend_columns=2,
                width_in=11.5,
                height_in=6.2,
                dpi=180,
            ),
        )
        output = recipe_dir / f"{case.case_id}_{name}.json"
        recipe.save(output)
        outputs.append(output)
    return outputs


def plot_case(
    device: Device,
    profile: Profile,
    case: PulseCase,
    data: dict[str, np.ndarray],
    output: Path,
    invert_transistor_controls: bool = False,
) -> Path:
    ensure_dir(output.parent)
    fig, axes = plt.subplots(4, 1, figsize=(14.5, 11.2), sharex=True)
    t = data["time_ns"]
    panels = [
        ("pad_v", "Pad voltage (V)"),
        ("ku", "Ku"),
        ("kd", "Kd"),
    ]
    for ax, (suffix, ylabel) in zip(axes[:3], panels):
        ax.plot(t, data[f"hspice_ibis_{suffix}"], color=BLACK, lw=3.1, label="HSPICE native IBIS", zorder=5)
        if suffix == "pad_v":
            ax.plot(t, data["hspice_transistor_pad_v"], color=GRAY, lw=2.8, label="HSPICE transistor", zorder=2)
        if f"gate_state_{suffix}" in data:
            ax.plot(t, data[f"gate_state_{suffix}"], color=RED, lw=1.9, label="Gate state model", zorder=4)
        if f"hybrid_{suffix}" in data:
            ax.plot(t, data[f"hybrid_{suffix}"], color=PURPLE, lw=1.9, label="Hybrid model", zorder=3)
        ax.set_ylabel(ylabel)
        ax.grid(True, color=GRID, alpha=0.75)
        for edge in command_edges(device, case):
            ax.axvline(edge, color=EDGE_COLOR, ls="--", lw=1.0)
    axes[2].axhline(0.0, color="#999999", lw=0.8)

    axes[3].plot(t, data["input_v"] / device.supply_v, color=BLUE, lw=1.8, label="Input / VDD")
    for index in range(1, len(device.transistor_probe_nodes) + 1):
        key = f"transistor_control_{index}_v"
        if key in data:
            control = data[key] / device.supply_v
            label = TRANSISTOR_CONTROL_LABELS[device.device_id][index - 1]
            if invert_transistor_controls:
                control = 1.0 - control
                label = f"polarity-normalized: 1 - V({label.split(':', 1)[0]}) / VDD"
            axes[3].plot(
                t,
                control,
                lw=1.8,
                color=[GREEN, ORANGE][(index - 1) % 2],
                label=label,
            )
    if invert_transistor_controls:
        axes[3].set_ylabel("Input and transistor controls\n(rising-command polarity)")
    else:
        axes[3].set_ylabel("Input and transistor gates\n(normalized to VDD)")
    axes[3].set_xlabel("Time (ns)")
    axes[3].set_ylim(-0.08, 1.08)
    axes[3].grid(True, color=GRID, alpha=0.75)
    for edge in command_edges(device, case):
        axes[3].axvline(edge, color=EDGE_COLOR, ls="--", lw=1.0)

    handles: list[object] = []
    labels: list[str] = []
    for ax in axes:
        for handle, label in zip(*ax.get_legend_handles_labels()):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.955),
        ncol=min(5, len(labels)),
        frameon=False,
    )
    fig.suptitle(
        f"{device.label} | {case.target_label} | "
        f"{fmt(case.edge_ns * 1000)} ps edge, {fmt(case.pulse_width_ns * 1000)} ps pulse",
        fontweight="bold",
        y=0.992,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.91))
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def contact_sheet(paths: list[Path], output: Path, columns: int = 2) -> None:
    if not paths:
        return
    images = [plt.imread(path) for path in paths]
    rows = int(math.ceil(len(images) / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(15.0, 5.8 * rows), constrained_layout=True)
    flat = np.asarray(axes, dtype=object).reshape(-1)
    for ax, image, path in zip(flat, images, paths):
        ax.imshow(image)
        ax.set_title(path.stem, fontsize=10, loc="left")
        ax.axis("off")
    for ax in flat[len(images):]:
        ax.axis("off")
    ensure_dir(output.parent)
    fig.savefig(output, dpi=130)
    plt.close(fig)


def plot_transistor_selection(rows: list[dict[str, object]], output: Path) -> None:
    fig, axes = plt.subplots(3, 4, figsize=(17.0, 11.0), sharey=True, constrained_layout=True)
    for row_index, device in enumerate(DEVICES):
        for edge_index, edge_ns in enumerate(EDGE_RATES_NS):
            for direction_index, direction in enumerate(["short_high", "short_low"]):
                column = edge_index * 2 + direction_index
                ax = axes[row_index, column]
                selected = sorted(
                    (
                        row
                        for row in rows
                        if row["device"] == device.device_id
                        and abs(float(row["edge_ps"]) - edge_ns * 1000) < 1e-6
                        and row["direction"] == direction
                    ),
                    key=lambda row: float(row["pulse_width_ps"]),
                )
                widths = [float(row["pulse_width_ps"]) for row in selected]
                excursion = [float(row["transistor_excursion_fraction"]) for row in selected]
                ax.plot(widths, excursion, color=BLUE, marker="o", lw=2.0)
                chosen_ids: set[str] = set()
                chosen_rows: list[dict[str, object]] = []
                for target in TARGET_EXCURSIONS:
                    best = min(
                        selected,
                        key=lambda row: (
                            abs(float(row["transistor_excursion_fraction"]) - target),
                            float(row["pulse_width_ps"]),
                        ),
                    )
                    case_id = str(best["case_id"])
                    if case_id not in chosen_ids:
                        chosen_ids.add(case_id)
                        chosen_rows.append(best)
                ax.scatter(
                    [float(row["pulse_width_ps"]) for row in chosen_rows],
                    [float(row["transistor_excursion_fraction"]) for row in chosen_rows],
                    s=90,
                    facecolors="none",
                    edgecolors=ORANGE,
                    linewidths=2.2,
                    zorder=5,
                )
                for target in TARGET_EXCURSIONS:
                    ax.axhline(target, color="#b0b0b0", ls=":", lw=0.9)
                ax.axhspan(0.05, 0.95, color="#eef6ee", alpha=0.7)
                ax.set_title(f"{device.label} | {int(edge_ns * 1000)} ps | {direction.replace('_', ' ')}", loc="left", fontsize=10)
                ax.set_xlabel("Pulse width (ps)")
                ax.grid(True, color=GRID, alpha=0.7)
                if column == 0:
                    ax.set_ylabel("Peak pad movement / normal swing\n0 = none, 1 = complete")
    fig.suptitle(
        "Adaptive pulse selection from HSPICE transistor response\n"
        "Blue dots: tested widths | Orange rings: selected cases | Green band: partial output (5-95%)",
        fontweight="bold",
    )
    ensure_dir(output.parent)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def characterize_phase(args: argparse.Namespace) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    normal_rows: list[dict[str, object]] = []
    sweep_rows: list[dict[str, object]] = []
    cache_rows: list[dict[str, object]] = []
    normal_waves: dict[tuple[str, float], dict[str, np.ndarray]] = {}

    for device in DEVICES:
        for edge_ns in EDGE_CHARACTERIZATION_NS:
            case = PulseCase(f"{edge_tag(edge_ns)}_long_control", edge_ns, "rise_fall", 10.0, 22.0)
            raw, cache = run_transistor(device, case, OUT_DIR / "characterization", args.hspice, args.timeout_s)
            wave = transistor_waveform(device, raw)
            normal_waves[(device.device_id, edge_ns)] = wave
            normal_rows.append(characterize_normal(device, case, wave))
            cache_rows.append(cache)

    normal_lookup = {
        (str(row["device"]), float(row["edge_ps"]) * 1e-3): row
        for row in normal_rows
    }
    for device in DEVICES:
        for edge_ns in EDGE_RATES_NS:
            normal = normal_lookup[(device.device_id, edge_ns)]
            low, high = settled_levels(normal_waves[(device.device_id, edge_ns)])
            for direction in ["short_high", "short_low"]:
                for width_ns in candidate_widths(edge_ns, normal, direction):
                    case = PulseCase(
                        f"{edge_tag(edge_ns)}_sweep_{direction}_{width_tag(width_ns)}",
                        edge_ns,
                        direction,
                        width_ns,
                        20.0,
                    )
                    raw, cache = run_transistor(device, case, OUT_DIR / "characterization", args.hspice, args.timeout_s)
                    wave = transistor_waveform(device, raw)
                    sweep_rows.append(pulse_metrics(device, case, wave, low, high))
                    cache_rows.append(cache)

    # Two interpolation/refinement rounds tighten the measured 20/55/85% points.
    # A missing bracket is preserved as evidence that a full-amplitude pulse does
    # not produce a partial output region at this runtime slew.
    for _round in range(2):
        additions: list[tuple[Device, float, str, float]] = []
        for device in DEVICES:
            for edge_ns in EDGE_RATES_NS:
                for direction in ["short_high", "short_low"]:
                    subset = [
                        row
                        for row in sweep_rows
                        if row["device"] == device.device_id
                        and abs(float(row["edge_ps"]) - edge_ns * 1000) < 1e-6
                        and row["direction"] == direction
                    ]
                    existing = {
                        round(float(row["pulse_width_ps"]) * 1e-3, 3)
                        for row in subset
                    }
                    for target in TARGET_EXCURSIONS:
                        width_ns = refinement_width(subset, target, edge_ns)
                        if width_ns is not None and width_ns not in existing:
                            additions.append((device, edge_ns, direction, width_ns))
                            existing.add(width_ns)
        for device, edge_ns, direction, width_ns in additions:
            normal_wave = normal_waves[(device.device_id, edge_ns)]
            low, high = settled_levels(normal_wave)
            case = PulseCase(
                f"{edge_tag(edge_ns)}_refine_{direction}_{width_tag(width_ns)}",
                edge_ns,
                direction,
                width_ns,
                20.0,
            )
            raw, cache = run_transistor(
                device,
                case,
                OUT_DIR / "characterization",
                args.hspice,
                args.timeout_s,
            )
            wave = transistor_waveform(device, raw)
            sweep_rows.append(pulse_metrics(device, case, wave, low, high))
            cache_rows.append(cache)

    write_csv(OUT_DIR / "normal_transition_characterization.csv", normal_rows)
    write_csv(OUT_DIR / "transistor_pulse_sweep.csv", sweep_rows)
    write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)
    plot_transistor_selection(sweep_rows, OUT_DIR / "plots" / "00_transistor_pulse_selection.png")
    return normal_rows, sweep_rows, cache_rows


def selected_case_rows(sweep_rows: list[dict[str, object]]) -> tuple[list[PulseCase], list[dict[str, object]]]:
    cases: list[PulseCase] = []
    rows: list[dict[str, object]] = []
    sweep_lookup = {
        (
            str(row["device"]),
            round(float(row["edge_ps"]), 6),
            str(row["direction"]),
            round(float(row["pulse_width_ps"]), 6),
        ): row
        for row in sweep_rows
    }
    for device in DEVICES:
        for edge_ns in EDGE_RATES_NS:
            control = PulseCase(
                case_id=f"{edge_tag(edge_ns)}_long_control",
                edge_ns=edge_ns,
                pattern="rise_fall",
                pulse_width_ns=10.0,
                stop_ns=22.0,
                target_label="long_control",
            )
            cases.append(control)
            rows.append(
                {
                    "device": device.device_id,
                    "edge_ps": edge_ns * 1000,
                    "direction": "rise_fall",
                    "target_label": "long_control",
                    "target_excursion_fraction": "",
                    "selected_case_id": control.case_id,
                    "source_sweep_case_id": control.case_id,
                    "pulse_width_ps": 10000.0,
                    "measured_transistor_excursion_fraction": 1.0,
                    "target_absolute_error": "",
                    "selection_quality": "NORMAL_CONTROL",
                    "transistor_visible": True,
                    "transistor_partial": False,
                }
            )
            for direction in ["short_high", "short_low"]:
                for case in selected_cases(device, edge_ns, direction, sweep_rows):
                    cases.append(case)
                    source = sweep_lookup[
                        (
                            device.device_id,
                            round(edge_ns * 1000, 6),
                            direction,
                            round(case.pulse_width_ns * 1000, 6),
                        )
                    ]
                    excursion = float(source["transistor_excursion_fraction"])
                    direction_rows = [
                        row
                        for row in sweep_rows
                        if row["device"] == device.device_id
                        and abs(float(row["edge_ps"]) - edge_ns * 1000) < 1e-6
                        and row["direction"] == direction
                    ]
                    bracketed = refinement_width(
                        direction_rows,
                        case.target_excursion,
                        edge_ns,
                    ) is not None or abs(excursion - case.target_excursion) <= 0.05
                    selection_quality = (
                        "TARGET_REACHED"
                        if abs(excursion - case.target_excursion) <= 0.05
                        else "TARGET_BRACKETED_NEAREST"
                        if bracketed
                        else "NO_PARTIAL_REGION_AT_MIN_FULL_AMPLITUDE_PULSE"
                        if min(float(row["transistor_excursion_fraction"]) for row in direction_rows) > 0.95
                        else "TARGET_NOT_REACHED"
                    )
                    rows.append(
                        {
                            "device": device.device_id,
                            "edge_ps": edge_ns * 1000,
                            "direction": direction,
                            "target_label": case.target_label,
                            "target_excursion_fraction": case.target_excursion,
                            "selected_case_id": case.case_id,
                            "source_sweep_case_id": source["case_id"],
                            "pulse_width_ps": case.pulse_width_ns * 1000,
                            "measured_transistor_excursion_fraction": source["transistor_excursion_fraction"],
                            "target_absolute_error": abs(excursion - case.target_excursion),
                            "selection_quality": selection_quality,
                            "transistor_visible": source["transistor_visible"],
                            "transistor_partial": source["transistor_partial"],
                            **{
                                key: value
                                for key, value in source.items()
                                if str(key).startswith("control_")
                            },
                        }
                    )
    write_csv(OUT_DIR / "selected_realistic_cases.csv", rows)
    return cases, rows


def campaign_phase(
    args: argparse.Namespace,
    sweep_rows: list[dict[str, object]],
    cache_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    all_metrics: list[dict[str, object]] = []
    failure_rows: list[dict[str, object]] = []
    _cases, selected_rows = selected_case_rows(sweep_rows)
    case_lookup = {
        (str(row["device"]), str(row["selected_case_id"])): row
        for row in selected_rows
    }

    for device in DEVICES:
        # Rebuild from device-owned rows. Case IDs intentionally omit the
        # device, so filtering a global PulseCase list by ID would duplicate
        # common controls and minimum-width cases across the three devices.
        device_cases = [
            PulseCase(
                case_id=str(row["selected_case_id"]),
                edge_ns=float(row["edge_ps"]) * 1e-3,
                pattern=str(row["direction"]),
                pulse_width_ns=float(row["pulse_width_ps"]) * 1e-3,
                stop_ns=22.0 if row["direction"] == "rise_fall" else 20.0,
                target_label=str(row["target_label"]),
                target_excursion=(
                    float(row["target_excursion_fraction"])
                    if row["target_excursion_fraction"] not in {"", None}
                    else float("nan")
                ),
            )
            for row in selected_rows
            if row["device"] == device.device_id
        ]
        transistor_cache: dict[str, dict[str, np.ndarray]] = {}
        for case in device_cases:
            selected = case_lookup[(device.device_id, case.case_id)]
            source_case_id = str(selected["source_sweep_case_id"])
            tr0 = (
                OUT_DIR
                / "characterization"
                / device.device_id
                / edge_tag(case.edge_ns)
                / "transistor"
                / source_case_id
                / "run.tr0"
            )
            if not tr0.exists():
                raise FileNotFoundError(
                    f"Selected transistor source is missing: {tr0}. "
                    "Run characterization before the selected campaign."
                )
            transistor_cache[case.case_id] = transistor_waveform(
                device,
                parse_hspice_tr0(tr0),
            )
            cache_rows.append(
                {
                    "device": device.device_id,
                    "edge_ps": case.edge_ns * 1000,
                    "case_id": case.case_id,
                    "reference": "hspice_transistor",
                    "source": "reuse_characterization",
                    "source_case_id": source_case_id,
                    "tr0": str(tr0.relative_to(ROOT)),
                }
            )
        for profile in profiles(device):
            common = OUT_DIR / "selected_runs" / device.device_id / profile.profile_id / "common"
            try:
                models = prepare_ngspice_models(device, profile, common)
            except Exception as exc:
                failure_rows.append(
                    {
                        "device": device.device_id,
                        "profile": profile.profile_id,
                        "case_id": "ALL",
                        "flow": "model_generation",
                        "error": str(exc),
                    }
                )
                continue
            plot_paths: list[Path] = []
            for case in device_cases:
                native_raw, cache = run_native_ibis(
                    device,
                    profile,
                    case,
                    OUT_DIR / "selected_runs",
                    args.hspice,
                    args.timeout_s,
                )
                cache_rows.append(cache)
                native = native_waveform(native_raw)
                flow_waves: dict[str, dict[str, np.ndarray] | None] = {}
                run_rows: list[dict[str, object]] = []
                for flow, mode in [("gate_state", FULL_MODE), ("hybrid", HYBRID_MODE)]:
                    raw, run_row = run_ngspice(
                        device,
                        profile,
                        case,
                        flow,
                        mode,
                        models[flow],
                        OUT_DIR / "selected_runs",
                        args.ngspice,
                        args.timeout_s,
                    )
                    run_rows.append(run_row)
                    flow_waves[flow] = ngspice_waveform(raw) if raw is not None else None
                    if raw is None:
                        failure_rows.append(run_row)
                data = aligned_data(device, case, transistor_cache[case.case_id], native, flow_waves)
                waveform = (
                    OUT_DIR
                    / "selected_runs"
                    / device.device_id
                    / edge_tag(case.edge_ns)
                    / profile.profile_id
                    / "waveform_data"
                    / f"{case.case_id}.csv"
                )
                save_waveform(waveform, data)
                save_editable_recipes(device, profile, case, waveform)
                all_metrics.extend(comparison_metrics(device, profile, case, data, run_rows))
                plot_path = (
                    OUT_DIR
                    / "selected_runs"
                    / device.device_id
                    / edge_tag(case.edge_ns)
                    / profile.profile_id
                    / "plots"
                    / f"{case.case_id}.png"
                )
                plot_case(device, profile, case, data, plot_path)
                plot_paths.append(plot_path)
            contact_sheet(
                plot_paths,
                OUT_DIR / "selected_runs" / device.device_id / profile.profile_id / "contact_sheet.png",
                columns=2,
            )

    write_csv(OUT_DIR / "metrics.csv", all_metrics)
    write_csv(OUT_DIR / "numeric_failures.csv", failure_rows)
    write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)
    return all_metrics


def headline_summary(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    def has_finite(row: dict[str, object], key: str) -> bool:
        try:
            return bool(np.isfinite(float(row.get(key, ""))))
        except (TypeError, ValueError):
            return False

    rows: list[dict[str, object]] = []
    keys = sorted(
        {
            (str(row["device"]), str(row["profile"]), float(row["edge_ps"]))
            for row in metrics
            if row.get("flow") in {"gate_state", "hybrid"}
        }
    )
    for device, profile, edge_ps in keys:
        selected = [
            row
            for row in metrics
            if row.get("device") == device
            and row.get("profile") == profile
            and float(row.get("edge_ps", -1)) == edge_ps
            and row.get("flow") in {"gate_state", "hybrid"}
            and has_finite(row, "pad_rmse_v")
        ]
        for flow in ["gate_state", "hybrid"]:
            flow_rows = [
                row
                for row in selected
                if row["flow"] == flow
                and has_finite(row, "pad_rmse_v")
                and has_finite(row, "ku_rmse")
                and has_finite(row, "kd_rmse")
            ]
            rows.append(
                {
                    "device": device,
                    "profile": profile,
                    "edge_ps": edge_ps,
                    "flow": flow,
                    "completed_cases": len(flow_rows),
                    "physically_valid_cases": sum(
                        str(row.get("coefficient_native_envelope_ok", "")).lower() == "true"
                        and row.get("status") not in {"COEFFICIENT_DISCONTINUITY"}
                        for row in flow_rows
                    ),
                    "native_envelope_valid_cases": sum(
                        str(row.get("coefficient_native_envelope_ok", "")).lower() == "true"
                        for row in flow_rows
                    ),
                    "absolute_range_valid_cases": sum(
                        str(row.get("coefficient_absolute_range_ok", "")).lower() == "true"
                        for row in flow_rows
                    ),
                    "native_extended_range_cases": sum(
                        str(row.get("native_reference_extended_range", "")).lower() == "true"
                        for row in flow_rows
                    ),
                    "median_pad_rmse_mv": 1000 * float(np.median([float(row["pad_rmse_v"]) for row in flow_rows])) if flow_rows else "",
                    "median_ku_rmse": float(np.median([float(row["ku_rmse"]) for row in flow_rows])) if flow_rows else "",
                    "median_kd_rmse": float(np.median([float(row["kd_rmse"]) for row in flow_rows])) if flow_rows else "",
                }
            )
    write_csv(OUT_DIR / "summary_by_device_profile.csv", rows)
    return rows


def write_readme(
    normal_rows: list[dict[str, object]],
    selected_rows: list[dict[str, str]],
    metrics: list[dict[str, object]],
    summary_rows: list[dict[str, object]],
) -> None:
    def finite_value(row: dict[str, object], key: str) -> float | None:
        try:
            value = float(row.get(key, ""))
        except (TypeError, ValueError):
            return None
        return value if np.isfinite(value) else None

    selected_partial = sum(str(row.get("transistor_partial", "")).lower() == "true" for row in selected_rows)
    selected_total = len(selected_rows)
    partial_ids = {
        (row["device"], row["selected_case_id"])
        for row in selected_rows
        if row["direction"] == "short_high"
        and str(row.get("transistor_partial", "")).lower() == "true"
    }
    partial_short_low = sum(
        row["direction"] == "short_low"
        and str(row.get("transistor_partial", "")).lower() == "true"
        for row in selected_rows
    )
    partial_summary: list[dict[str, object]] = []
    for device in [item.device_id for item in DEVICES]:
        for profile in ["slow_1ns", "fast_5ps"]:
            for flow in ["gate_state", "hybrid"]:
                all_flow_rows = [
                    row
                    for row in metrics
                    if row.get("device") == device
                    and row.get("profile") == profile
                    and row.get("flow") == flow
                    and (device, row.get("case_id")) in partial_ids
                ]
                flow_rows = [
                    row
                    for row in all_flow_rows
                    if finite_value(row, "pad_rmse_v") is not None
                ]
                if not flow_rows:
                    continue
                partial_summary.append(
                    {
                        "device": device,
                        "profile": profile,
                        "flow": flow,
                        "cases": len(all_flow_rows),
                        "measured_cases": len(flow_rows),
                        "median_pad_rmse_mv": 1000
                        * float(np.median([finite_value(row, "pad_rmse_v") for row in flow_rows])),
                        "median_ku_rmse": float(
                            np.median([finite_value(row, "ku_rmse") for row in flow_rows])
                        ),
                        "median_kd_rmse": float(
                            np.median([finite_value(row, "kd_rmse") for row in flow_rows])
                        ),
                        "completed": sum(row.get("status") == "COMPLETED" for row in flow_rows),
                        "coefficient_step_warnings": sum(
                            row.get("status") == "COEFFICIENT_DISCONTINUITY"
                            for row in flow_rows
                        ),
                        "outside_native_envelope": sum(
                            row.get("status") == "COEFFICIENT_OUTSIDE_NATIVE_ENVELOPE"
                            for row in all_flow_rows
                        ),
                        "numeric_failures": sum(
                            row.get("status") == "NUMERIC_FAIL"
                            for row in all_flow_rows
                        ),
                    }
                )
    write_csv(OUT_DIR / "partial_short_high_summary.csv", partial_summary)
    reference_extended_profiles = sorted(
        {
            f"{row.get('device')}/{row.get('profile')}"
            for row in metrics
            if str(row.get("native_reference_extended_range", "")).lower() == "true"
        }
    )
    long_hybrid = [
        row
        for row in metrics
        if row.get("flow") == "hybrid" and row.get("target_label") == "long_control"
    ]
    long_hybrid_inactive = sum(
        str(row.get("hybrid_active", "")).lower() == "false"
        for row in long_hybrid
    )
    failures = [
        row
        for row in metrics
        if row.get("flow") in {"gate_state", "hybrid"} and row.get("status") != "COMPLETED"
    ]
    lines = [
        "# Three-Buffer Realistic-Pulse Campaign",
        "",
        "This campaign replaces the earlier 1 ps stimulus with transistor-library-aware 100 ps and 250 ps input slews. Pulse widths are selected from HSPICE transistor response rather than named `short` in advance.",
        "",
        "## Headline Findings",
        "",
        f"- The transistor sweep found `{selected_partial}` pad-partial cases among `{selected_total}` selected controls/stress cases. All pad-partial cases are short-high; pad-partial short-low cases: `{partial_short_low}`.",
        "- The internal-control panel shows that pad-partial does not always mean the final output-stage gate was already mid-transition at the external reverse edge. This distinction is especially important for the multistage `inv_chain` and `ex2` buffers.",
        "- The minimum full-swing short-low command already produces a complete output excursion in all three transistor circuits. The pipeline preserves that as regeneration evidence instead of inventing a shorter reduced-amplitude pulse.",
        "- `inv_chain` has a narrow partial short-high region at 100 ps input slew (102-125 ps pulse width), but its minimum 250 ps full-swing pulse already produces a complete transition.",
        f"- The hybrid reversal detector stayed inactive in `{long_hybrid_inactive}/{len(long_hybrid)}` long-pulse controls. The normal-operation branch therefore remained on legacy replay as designed.",
        "- The hybrid is not a universal winner. It reduces median errors in several partial-pulse groups, but coefficient-step warnings expose the switching handoff; the full gate-state path is usually more continuous.",
        "- Fast `io_buf` remains the clearest structural failure: both candidate paths frequently leave the native coefficient envelope, and the full gate-state model has numeric failures.",
        f"- Native-reference coefficients themselves exceed the old nominal `[-0.2, 1.2]` interval for: `{', '.join(reference_extended_profiles) or 'none'}`. Candidate validity is therefore checked against each case's native envelope with a `{COEFFICIENT_ENVELOPE_MARGIN:.2f}` margin; the absolute interval is retained only as context.",
        "",
        "## Experiment Design",
        "",
        "- All three transistor libraries are 0.18 um-class models.",
        "- `100 ps` is the aggressive realistic stress slew; `250 ps` is the moderate slew.",
        "- The libraries do not specify a board-interface slew limit, so these are engineering stress points validated against measured transistor timing, not claimed datasheet limits.",
        "- Load remains `50 ohm || 2 pF`, matching the earlier studies.",
        "- A transistor-only sweep chooses widths nearest 20%, 55%, and 85% output excursion for each device, direction, and slew.",
        "- The selected widths are then compared across HSPICE transistor, HSPICE native IBIS, ngspice full gate-state, and ngspice legacy-normal/gate-on-reversal hybrid.",
        "- Slow 1 ns and fast 5 ps characterized IBIS files are both retained. Their characterization slew is a model property; the runtime input slew in this study is 100 ps or 250 ps.",
        "",
        "## What Counts As Mid-Transition",
        "",
        "The report does not infer mid-transition from pulse width alone. It records the transistor pad excursion and, where available, the final output-stage control-node extrema. A selected case is partial when the transistor output excursion lies between 5% and 95% of its loaded full swing.",
        "",
        f"- Selected cases with partial transistor output: `{selected_partial}/{selected_total}`.",
        f"- ngspice candidate failures preserved: `{len(failures)}`.",
        "",
        "## Transistor Pad-Partial Short-High Results",
        "",
        "This table excludes long controls and regenerated/full-swing cases. `Completed` means no envelope, discontinuity, or numeric warning under the recorded checks.",
        "",
        "| Device | IBIS profile | Flow | Cases | Completed | Step warnings | Outside native envelope | Numeric failures | Median pad RMSE mV | Median Ku RMSE | Median Kd RMSE |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in partial_summary:
        lines.append(
            f"| {row['device']} | {row['profile']} | {row['flow']} | {row['cases']} | "
            f"{row['completed']} | {row['coefficient_step_warnings']} | "
            f"{row['outside_native_envelope']} | {row['numeric_failures']} | "
            f"{float(row['median_pad_rmse_mv']):.3f} | "
            f"{float(row['median_ku_rmse']):.5f} | {float(row['median_kd_rmse']):.5f} |"
        )
    lines.extend(
        [
        "",
        "## Normal Transition Characterization",
        "",
        "| Device | Edge ps | Rise delay ps | Rise 10-90 ps | Fall delay ps | Fall 90-10 ps | Loaded swing V |",
        "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in normal_rows:
        lines.append(
            f"| {row['device']} | {float(row['edge_ps']):.0f} | "
            f"{float(row['rise_delay_50_ps']):.1f} | {float(row['rise_10_90_ps']):.1f} | "
            f"{float(row['fall_delay_50_ps']):.1f} | {float(row['fall_90_10_ps']):.1f} | "
            f"{float(row['loaded_swing_v']):.4f} |"
        )
    lines.extend(
        [
            "",
            "## Selected Widths",
            "",
            "| Device | Edge ps | Direction | Target | Width ps | Measured transistor excursion | Partial |",
            "|---|---:|---|---|---:|---:|---|",
        ]
    )
    for row in selected_rows:
        lines.append(
            f"| {row['device']} | {float(row['edge_ps']):.0f} | {row['direction']} | "
            f"{row['target_label']} | {float(row['pulse_width_ps']):.0f} | "
            f"{100 * float(row['measured_transistor_excursion_fraction']):.1f}% | {row['transistor_partial']} |"
        )
    lines.extend(
        [
            "",
            "## Candidate Summary",
            "",
            "| Device | IBIS profile | Edge ps | Flow | Cases | Native-envelope valid | Native reference outside nominal range | Median pad RMSE mV | Median Ku RMSE | Median Kd RMSE |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| {row['device']} | {row['profile']} | {float(row['edge_ps']):.0f} | {row['flow']} | "
            f"{row['completed_cases']} | {row['native_envelope_valid_cases']} | "
            f"{row['native_extended_range_cases']} | {float(row['median_pad_rmse_mv']):.3f} | "
            f"{float(row['median_ku_rmse']):.5f} | {float(row['median_kd_rmse']):.5f} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `normal_transition_characterization.csv`: measured transistor timing at 50, 100, and 250 ps input slew.",
            "- `transistor_pulse_sweep.csv`: every transistor-only pulse candidate.",
            "- `selected_realistic_cases.csv`: adaptive width choices and internal control extrema.",
            "- `metrics.csv`: candidate errors versus HSPICE native IBIS.",
            "- `partial_short_high_summary.csv`: model statistics restricted to transistor-confirmed partial short-high cases.",
            "- `selected_runs/<device>/<edge>/<profile>/waveform_data/`: exact plotted data.",
            "- `selected_runs/<device>/<edge>/<profile>/plots/`: four-panel evidence figures.",
            "- `selected_runs/<device>/<edge>/<profile>/editable_figures/`: editable one-panel pad, Ku, and Kd JSON recipes.",
            "- `plots/00_transistor_pulse_selection.png`: selection evidence.",
            "- `reference_cache_manifest.csv`: cache/run provenance for every HSPICE result.",
            "",
            "## Fast-Edge Figure View",
            "",
            "The current presentation view uses only `fast_5ps` IBIS results. Fast-only contact sheets are:",
            "",
            "- `selected_runs/io_buf/fast_5ps/contact_sheet.png`",
            "- `selected_runs/inv_chain/fast_5ps/contact_sheet.png`",
            "- `selected_runs/ex2/fast_5ps/contact_sheet.png`",
            "",
            "In the fourth panel, measured transistor gate controls are displayed as "
            "`1 - V(gate)/VDD`. This is a plotting-only polarity normalization: the raw CSV "
            "still contains the actual HSPICE gate voltage. It makes an external rising "
            "command and its delayed final-stage control both appear as rising signals.",
            "",
            "`plots/00_transistor_pulse_selection.png` is not an IBIS-model comparison. "
            "It is the transistor-only experiment-design figure used to choose pulse widths "
            "that produce visible, partial, and near-settled loaded-pad motion. Therefore it "
            "is shared by both IBIS characterization profiles and remains relevant when the "
            "comparison view is restricted to `fast_5ps`.",
            "",
            "Open any editable recipe with:",
            "",
            "```powershell",
            "& .\\scripts\\launch_figure_editor.cmd .\\path\\to\\figure_recipe.json",
            "```",
            "",
            "## Interpretation Limits",
            "",
            "HSPICE transistor pad is the circuit-level output reference. Native-IBIS Ku/Kd are native-IBIS diagnostics, not transistor-internal truth. A small pad error does not by itself validate coefficient behavior, and a partial pad response does not guarantee both pullup and pulldown internal controls are partial.",
        ]
    )
    write_text(OUT_DIR / "README.md", "\n".join(lines) + "\n")


def regenerate_reports(
    plot_profile: str = "all",
    invert_transistor_controls: bool = False,
) -> int:
    normal_rows = [{key: value for key, value in row.items()} for row in read_csv(OUT_DIR / "normal_transition_characterization.csv")]
    sweep_rows = [{key: value for key, value in row.items()} for row in read_csv(OUT_DIR / "transistor_pulse_sweep.csv")]
    selected_rows = read_csv(OUT_DIR / "selected_realistic_cases.csv")
    metrics = [{key: value for key, value in row.items()} for row in read_csv(OUT_DIR / "metrics.csv")]
    if not normal_rows or not sweep_rows or not selected_rows:
        raise RuntimeError("Campaign CSVs are incomplete; report-only regeneration is not available yet")
    plot_transistor_selection(sweep_rows, OUT_DIR / "plots" / "00_transistor_pulse_selection.png")
    for device in DEVICES:
        device_rows = [row for row in selected_rows if row["device"] == device.device_id]
        for profile in profiles(device):
            if plot_profile != "all" and profile.profile_id != plot_profile:
                continue
            profile_paths: list[Path] = []
            for row in device_rows:
                edge_ns = float(row["edge_ps"]) * 1e-3
                case = PulseCase(
                    case_id=row["selected_case_id"],
                    edge_ns=edge_ns,
                    pattern=row["direction"],
                    pulse_width_ns=float(row["pulse_width_ps"]) * 1e-3,
                    stop_ns=20.0,
                    target_label=row["target_label"],
                    target_excursion=(
                        float(row["target_excursion_fraction"])
                        if row["target_excursion_fraction"] not in {"", None}
                        else float("nan")
                    ),
                )
                waveform = (
                    OUT_DIR
                    / "selected_runs"
                    / device.device_id
                    / edge_tag(edge_ns)
                    / profile.profile_id
                    / "waveform_data"
                    / f"{case.case_id}.csv"
                )
                if not waveform.exists():
                    continue
                numeric_rows = read_csv(waveform)
                data = {
                    key: np.asarray([float(item[key]) for item in numeric_rows], dtype=float)
                    for key in numeric_rows[0]
                }
                save_editable_recipes(device, profile, case, waveform)
                output = (
                    OUT_DIR
                    / "selected_runs"
                    / device.device_id
                    / edge_tag(edge_ns)
                    / profile.profile_id
                    / "plots"
                    / f"{case.case_id}.png"
                )
                plot_case(
                    device,
                    profile,
                    case,
                    data,
                    output,
                    invert_transistor_controls=invert_transistor_controls,
                )
                profile_paths.append(output)
            contact_sheet(
                profile_paths,
                OUT_DIR / "selected_runs" / device.device_id / profile.profile_id / "contact_sheet.png",
                columns=2,
            )
    summary_rows = headline_summary(metrics) if metrics else []
    write_readme(normal_rows, selected_rows, metrics, summary_rows)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Three-buffer realistic-pulse campaign.")
    parser.add_argument("--hspice", type=Path, default=DEFAULT_HSPICE)
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--timeout-s", type=int, default=180)
    parser.add_argument("--characterize-only", action="store_true")
    parser.add_argument("--report-only", action="store_true", help="Regenerate plots/README from existing CSVs without simulation.")
    parser.add_argument(
        "--plot-profile",
        choices=("all", "slow_1ns", "fast_5ps"),
        default="all",
        help="Limit report-only plot regeneration to one IBIS characterization profile.",
    )
    parser.add_argument(
        "--invert-transistor-controls",
        action="store_true",
        help="Plot transistor controls as 1-Vgate/VDD so a rising input command appears as a rising control.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dir(OUT_DIR)
    if args.report_only:
        return regenerate_reports(
            plot_profile=args.plot_profile,
            invert_transistor_controls=args.invert_transistor_controls,
        )
    for device in DEVICES:
        for path in [device.slow_ibis, device.fast_ibis, *device.transistor_files]:
            if not path.exists():
                raise FileNotFoundError(path)
    normal_rows, sweep_rows, cache_rows = characterize_phase(args)
    _, selected_rows = selected_case_rows(sweep_rows)
    if args.characterize_only:
        write_readme(normal_rows, [{key: str(value) for key, value in row.items()} for row in selected_rows], [], [])
        return 0
    metrics = campaign_phase(args, sweep_rows, cache_rows)
    summary_rows = headline_summary(metrics)
    write_readme(
        normal_rows,
        [{key: str(value) for key, value in row.items()} for row in selected_rows],
        metrics,
        summary_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
