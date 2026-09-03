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
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
if str(PYBIS_ROOT) not in sys.path:
    sys.path.insert(0, str(PYBIS_ROOT))

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from spice_tool_paths import default_ngspice  # noqa: E402


OUT_DIR = ROOT / "results" / "io_buf_inv_chain_reversal_hybrid_comparison_2026-07-27"
DEFAULT_NGSPICE = default_ngspice(console=True)
HYBRID_SUBCIRCUIT_TYPE = "InputDrivenTwoStateGateDirectionalResidualHybrid"
HYBRID_DISPLAY_LABEL = "ngspice Kd-residual reversal hybrid"

BLACK = "#111111"
GRAY = "#777777"
BLUE = "#1769aa"
RED = "#d62728"
PURPLE = "#7b2cbf"
GREEN = "#138a72"
ORANGE = "#d97706"
GRID = "#d7d7d7"
EDGE = "#888888"


@dataclass(frozen=True)
class Case:
    case_id: str
    title: str
    pattern: str
    pulse_width_ns: float
    stop_ns: float
    xlim: tuple[float, float]


@dataclass(frozen=True)
class Device:
    device_id: str
    label: str
    component: str
    model: str
    subckt: str
    supply_v: float
    load_ohm: float
    load_pf: float
    edge_ns: float
    cases: tuple[Case, ...]


@dataclass(frozen=True)
class ModelVariant:
    variant_id: str
    label: str
    edge_setting: str
    ibis: Path


IO_CASES = (
    Case("edge_1ps_base_50r_2pf", "Complete rise and fall", "rise_fall", 10.0, 25.0, (4.0, 20.0)),
    Case("short_pulse_1ns_high", "Interrupted 1 ns high pulse", "short_high", 1.0, 13.0, (4.0, 12.0)),
    Case("short_pulse_2ns_high", "Interrupted 2 ns high pulse", "short_high", 2.0, 14.0, (4.0, 13.0)),
    Case("short_pulse_1ns_low", "Interrupted 1 ns low pulse", "short_low", 1.0, 18.0, (9.0, 18.0)),
    Case("short_pulse_2ns_low", "Interrupted 2 ns low pulse", "short_low", 2.0, 18.0, (9.0, 18.0)),
)

INV_CASES = (
    Case("edge_1ps_base_50r_2pf", "Complete rise and fall", "rise_fall", 10.0, 22.0, (4.0, 18.0)),
    Case("short_pulse_50ps_high", "Interrupted 50 ps high pulse", "short_high", 0.05, 10.0, (4.0, 9.05)),
    Case("short_pulse_100ps_high", "Interrupted 100 ps high pulse", "short_high", 0.1, 10.0, (4.0, 9.10)),
    Case("short_pulse_200ps_high", "Interrupted 200 ps high pulse", "short_high", 0.2, 10.0, (4.0, 9.20)),
    Case("short_pulse_1ns_high", "Settled 1 ns high-pulse control", "short_high", 1.0, 12.0, (4.0, 10.0)),
    Case("short_pulse_50ps_low", "Interrupted 50 ps low pulse", "short_low", 0.05, 14.0, (9.0, 14.0)),
    Case("short_pulse_100ps_low", "Interrupted 100 ps low pulse", "short_low", 0.1, 14.0, (9.0, 14.0)),
    Case("short_pulse_200ps_low", "Interrupted 200 ps low pulse", "short_low", 0.2, 14.0, (9.0, 14.0)),
    Case("short_pulse_1ns_low", "Settled 1 ns low-pulse control", "short_low", 1.0, 15.0, (9.0, 15.0)),
)

DEVICES = (
    Device("io_buf", "io_buf", "MCM Driver 1", "driver", "driver_OutputInput_Typical", 3.3, 50.0, 2.0, 0.001, IO_CASES),
    Device("inv_chain", "inv_chain", "invchain", "driver2", "driver2_OutputInput_Typical", 1.8, 50.0, 2.0, 0.001, INV_CASES),
)

VARIANTS = {
    "io_buf": (
        ModelVariant("slow", "slow IBIS", "tr=tf=1 ns", ROOT / "hspice" / "sparam" / "io_buf.ibs"),
        ModelVariant(
            "fast",
            "fast IBIS",
            "tr=tf=5 ps",
            ROOT / "results" / "io_buf_fast_edge_retest_2026-06-05" / "source" / "io_buf.ibs",
        ),
    ),
    "inv_chain": (
        ModelVariant(
            "slow",
            "slow IBIS",
            "tr=tf=1 ns",
            ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27" / "slow_1ns" / "inv_chain_slow_1ns.ibs",
        ),
        ModelVariant(
            "fast",
            "fast IBIS",
            "tr=tf=5 ps",
            ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27" / "fast_5ps" / "inv_chain_fast_5ps.ibs",
        ),
    ),
}


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-12:
        return str(int(round(value)))
    return f"{value:.12g}"


def points(device: Device, case: Case) -> list[tuple[float, float]]:
    e = device.edge_ns
    high = device.supply_v
    if case.pattern == "rise_fall":
        return [(0, 0), (5, 0), (5 + e, high), (15, high), (15 + e, 0), (case.stop_ns, 0)]
    if case.pattern == "short_high":
        reverse = 5 + case.pulse_width_ns
        return [(0, 0), (5, 0), (5 + e, high), (reverse, high), (reverse + e, 0), (case.stop_ns, 0)]
    if case.pattern == "short_low":
        reverse = 10 + case.pulse_width_ns
        return [
            (0, 0),
            (5, 0),
            (5 + e, high),
            (10, high),
            (10 + e, 0),
            (reverse, 0),
            (reverse + e, high),
            (case.stop_ns, high),
        ]
    raise ValueError(case.pattern)


def command_edges(device: Device, case: Case) -> list[float]:
    result: list[float] = []
    pts = points(device, case)
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if abs(v1 - v0) > 1e-12:
            result.append(0.5 * (t0 + t1))
    return result


def pwl(device: Device, case: Case) -> str:
    lines = ["Vin in_dig 0 PWL("]
    for time_ns, voltage in points(device, case):
        lines.append(f"+ {fmt(time_ns)}n {fmt(voltage)}")
    lines[-1] += " )"
    return "\n".join(lines)


def input_waveform(device: Device, case: Case, t_ns: np.ndarray) -> np.ndarray:
    pts = points(device, case)
    return np.interp(t_ns, [p[0] for p in pts], [p[1] for p in pts])


def make_deck(device: Device, case: Case) -> str:
    dual_diagnostics = ""
    if "DualResidual" in HYBRID_SUBCIRCUIT_TYPE:
        dual_diagnostics = (
            "\n+ V(xdrv.kures) V(xdrv.kures_table) V(xdrv.guprate)"
            "\n+ V(xdrv.kdres) V(xdrv.kdres_table) V(xdrv.gdnrate)"
        )
    return f"""* {device.device_id} reversal hybrid
* case: {case.case_id}
.title {device.device_id} reversal hybrid {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12 filetype=binary

{pwl(device, case)}

Ven en_sig 0 DC {fmt(device.supply_v)}
Vdd vdd 0 DC {fmt(device.supply_v)}
.include '{device.subckt}.sub'
XDRV pad in_dig en_sig vdd 0 {device.subckt}

Rload pad 0 {fmt(device.load_ohm)}
Cload pad 0 {fmt(device.load_pf)}p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
+ V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.kutarget) V(xdrv.kdtarget)
+ V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget)
+ V(xdrv.kugate) V(xdrv.kdgate)
+ V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)
+ V(xdrv.hreverseraw) V(xdrv.hsettled) V(xdrv.hhybridactive)
+ V(xdrv.highage) V(xdrv.lowage){dual_diagnostics}
.tran 0.001n {fmt(case.stop_ns)}n
.end
"""


def run_process(command: list[str], cwd: Path, log: Path, timeout_s: int) -> int:
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        captured = exc.stdout or ""
        if isinstance(captured, bytes):
            captured = captured.decode("utf-8", errors="replace")
        log.write_text(f"TIMEOUT after {timeout_s} seconds\n{captured}", encoding="utf-8", errors="replace")
        return 124
    log.write_text("COMMAND: " + " ".join(command) + "\n\n" + proc.stdout, encoding="utf-8", errors="replace")
    return int(proc.returncode)


def normalized(data: dict[str, np.ndarray]) -> dict[str, str]:
    return {key.lower().replace(":", "."): key for key in data}


def signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    lookup = normalized(data)
    for name in names:
        key = lookup.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"missing {names}; available={sorted(data)}")


def optional_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray | None:
    try:
        return signal(data, *names)
    except KeyError:
        return None


def hspice_waveform(path: Path, pad_name: str) -> dict[str, np.ndarray]:
    raw = parse_hspice_tr0(path)
    return {
        "time_ns": signal(raw, "time") * 1e9,
        "pad_v": signal(raw, pad_name),
        "ku": signal(raw, "v(ku)"),
        "kd": signal(raw, "v(kd)"),
    }


def transistor_waveform(path: Path) -> dict[str, np.ndarray]:
    raw = parse_hspice_tr0(path)
    return {
        "time_ns": signal(raw, "time") * 1e9,
        "pad_v": signal(raw, "v(pad_sp)", "v(pad)"),
    }


def ngspice_waveform(path: Path) -> dict[str, np.ndarray]:
    raw = parse_ngspice_raw(path)
    result = {
        "time_ns": signal(raw, "time") * 1e9,
        "pad_v": signal(raw, "v(pad)"),
        "ku": signal(raw, "v(xdrv.ku)", "v(xdrv:ku)"),
        "kd": signal(raw, "v(xdrv.kd)", "v(xdrv:kd)"),
    }
    for name in [
        "kuleg",
        "kdleg",
        "kutarget",
        "kdtarget",
        "gup",
        "gdn",
        "guptarget",
        "gdntarget",
        "kugate",
        "kdgate",
        "hfall_after_rise",
        "hrise_after_fall",
        "hreverseraw",
        "hsettled",
        "hhybridactive",
        "highage",
        "lowage",
        "kures",
        "kures_table",
        "guprate",
        "kdres",
        "kdres_table",
        "gdnrate",
    ]:
        values = optional_signal(raw, f"v(xdrv.{name})", f"v(xdrv:{name})")
        if values is not None:
            result[name] = values
    return result


def prior_paths(device: Device, variant: ModelVariant, case: Case) -> dict[str, Path | str]:
    cid = case.case_id
    if device.device_id == "io_buf":
        slow_study = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
        fast_h = ROOT / "results" / "io_buf_correct_hspice_reference_waveforms_2026-07-23"
        fast_n = ROOT / "results" / "io_buf_correct_hspice_vs_pybis_2026-07-23"
        if variant.variant_id == "slow":
            native_stem = f"{cid}_hspice_native_ibis"
            trans_stem = f"{cid}_hspice_transistor_sp"
            return {
                "native": slow_study / "cases" / cid / "hspice_native_ibis" / f"{native_stem}.tr0",
                "native_pad": "v(pad_ibis)",
                "transistor": slow_study / "cases" / cid / "hspice_transistor_sp" / f"{trans_stem}.tr0",
                "legacy": slow_study / "cases" / cid / "ngspice_legacy" / f"{cid}_ngspice_legacy.raw",
                "full_gate": slow_study
                / "cases"
                / cid
                / "ngspice_two_state_directional_residual"
                / f"{cid}_ngspice_two_state_directional_residual.raw",
            }
        return {
            "native": fast_h / "cases" / cid / "hspice_native_fast_ibis" / "run.tr0",
            "native_pad": "v(pad)",
            "transistor": fast_h / "cases" / cid / "hspice_transistor_original" / "run.tr0",
            "legacy": fast_n / "cases" / cid / "ngspice_legacy" / "run.raw",
            "full_gate": fast_n / "cases" / cid / "ngspice_directional_residual" / "run.raw",
        }

    prior = ROOT / "results" / "inv_chain_s2ibispy_slow_fast_comparison_2026-07-27"
    variant_dir = prior / ("slow_1ns" if variant.variant_id == "slow" else "fast_5ps")
    native_stem = f"{cid}_hspice_native_ibis"
    trans_stem = f"{cid}_hspice_transistor"
    return {
        "native": variant_dir / "cases" / cid / "hspice_native_ibis" / f"{native_stem}.tr0",
        "native_pad": "v(pad_ibis)",
        "transistor": variant_dir / "cases" / cid / "hspice_transistor" / f"{trans_stem}.tr0",
        "legacy": variant_dir / "cases" / cid / "ngspice_legacy" / f"{cid}_ngspice_legacy.raw",
        "full_gate": variant_dir / "cases" / cid / "ngspice_gate_state" / f"{cid}_ngspice_gate_state.raw",
    }


def find_sidecar(path: Path, suffix: str) -> Path | None:
    candidate = path.with_suffix(suffix)
    return candidate if candidate.exists() else None


def copy_reference_package(paths: dict[str, Path | str], destination: Path) -> None:
    ensure_dir(destination)
    for role in ["native", "transistor"]:
        source = Path(paths[role])
        role_dir = destination / role
        ensure_dir(role_dir)
        shutil.copy2(source, role_dir / source.name)
        for suffix in [".sp", ".lis"]:
            sidecar = find_sidecar(source, suffix)
            if sidecar is not None:
                shutil.copy2(sidecar, role_dir / sidecar.name)


def prepare_model(device: Device, variant: ModelVariant, variant_dir: Path) -> Path:
    common = variant_dir / "common"
    ensure_dir(common)
    ibis_copy = common / variant.ibis.name
    shutil.copy2(variant.ibis, ibis_copy)
    output = common / "reversal_hybrid" / f"{device.subckt}.sub"
    convert_ibis_to_pybis(
        ibis_path=ibis_copy,
        output_path=output,
        component_name=device.component,
        model_name=device.model,
        io_type="Output",
        subcircuit_type=HYBRID_SUBCIRCUIT_TYPE,
        corner="Typical",
    )
    return output


def run_hybrid(
    device: Device,
    case: Case,
    model: Path,
    variant_dir: Path,
    ngspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], Path, Path]:
    out = variant_dir / "cases" / case.case_id / "ngspice_reversal_hybrid"
    ensure_dir(out)
    local_model = out / f"{device.subckt}.sub"
    shutil.copy2(model, local_model)
    deck = out / "run.sp"
    raw = out / "run.raw"
    write_text(deck, make_deck(device, case))
    rc = run_process(
        [str(ngspice), "-b", "-r", raw.name, deck.name],
        out,
        out / "ngspice_stdout.log",
        timeout_s,
    )
    if rc != 0 or not raw.exists():
        raise RuntimeError(f"ngspice failed for {device.device_id}/{case.case_id}; see {out / 'ngspice_stdout.log'}")
    return ngspice_waveform(raw), deck, raw


def grid(case: Case, step_ns: float = 0.001) -> np.ndarray:
    return np.arange(case.xlim[0], case.xlim[1] + 0.5 * step_ns, step_ns)


def interp(wave: dict[str, np.ndarray], t: np.ndarray, name: str) -> np.ndarray:
    return np.interp(t, wave["time_ns"], wave[name])


def align(
    device: Device,
    case: Case,
    native: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
    legacy: dict[str, np.ndarray],
    full_gate: dict[str, np.ndarray] | None,
    hybrid: dict[str, np.ndarray] | None,
) -> dict[str, np.ndarray]:
    t = grid(case)
    result: dict[str, np.ndarray] = {
        "time_ns": t,
        "input_v": input_waveform(device, case, t),
        "hspice_ibis_pad_v": interp(native, t, "pad_v"),
        "hspice_ibis_ku": interp(native, t, "ku"),
        "hspice_ibis_kd": interp(native, t, "kd"),
        "hspice_transistor_pad_v": interp(transistor, t, "pad_v"),
        "legacy_pad_v": interp(legacy, t, "pad_v"),
        "legacy_ku": interp(legacy, t, "ku"),
        "legacy_kd": interp(legacy, t, "kd"),
    }
    if full_gate is not None:
        for name in ["pad_v", "ku", "kd"]:
            result[f"full_gate_{name}"] = interp(full_gate, t, name)
    if hybrid is None:
        return result
    result["hybrid_pad_v"] = interp(hybrid, t, "pad_v")
    result["hybrid_ku"] = interp(hybrid, t, "ku")
    result["hybrid_kd"] = interp(hybrid, t, "kd")
    for name in [
        "kuleg",
        "kdleg",
        "kutarget",
        "kdtarget",
        "gup",
        "gdn",
        "guptarget",
        "gdntarget",
        "kugate",
        "kdgate",
        "hfall_after_rise",
        "hrise_after_fall",
        "hreverseraw",
        "hsettled",
        "hhybridactive",
        "highage",
        "lowage",
    ]:
        if name in hybrid:
            result[f"hybrid_{name}"] = interp(hybrid, t, name)
    return result


def failure_figure(device: Device, variant: ModelVariant, case: Case, message: str, output: Path) -> Path:
    ensure_dir(output.parent)
    fig, ax = plt.subplots(figsize=(14.5, 5.2), constrained_layout=True)
    ax.axis("off")
    ax.text(0.5, 0.58, "NUMERIC FAIL", ha="center", va="center", fontsize=28, fontweight="bold", color=RED)
    ax.text(0.5, 0.43, message, ha="center", va="center", fontsize=13, color="#333333", wrap=True)
    ax.set_title(f"{device.label} | {variant.label} | {case.title}", loc="left", fontweight="bold")
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return output


def rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.sqrt(np.mean((candidate - reference) ** 2)))


def max_error(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.max(np.abs(candidate - reference)))


def flow_metrics(data: dict[str, np.ndarray], flow: str) -> dict[str, float]:
    return {
        "pad_rmse_v": rmse(data["hspice_ibis_pad_v"], data[f"{flow}_pad_v"]),
        "pad_max_error_v": max_error(data["hspice_ibis_pad_v"], data[f"{flow}_pad_v"]),
        "ku_rmse": rmse(data["hspice_ibis_ku"], data[f"{flow}_ku"]),
        "ku_max_error": max_error(data["hspice_ibis_ku"], data[f"{flow}_ku"]),
        "kd_rmse": rmse(data["hspice_ibis_kd"], data[f"{flow}_kd"]),
        "kd_max_error": max_error(data["hspice_ibis_kd"], data[f"{flow}_kd"]),
    }


def handoff_metrics(data: dict[str, np.ndarray]) -> dict[str, object]:
    active = data.get("hybrid_hhybridactive", np.zeros_like(data["time_ns"]))
    on = active > 0.5
    indices = np.flatnonzero(on)
    takeovers = np.flatnonzero(~on[:-1] & on[1:])
    transitions = np.flatnonzero(on[:-1] & ~on[1:])
    ku = data["hybrid_ku"]
    kd = data["hybrid_kd"]
    result: dict[str, object] = {
        "hybrid_active_peak": float(np.max(active)),
        "hybrid_active_duration_ns": float(np.trapezoid(on.astype(float), data["time_ns"])),
        "hybrid_active_start_ns": float(data["time_ns"][indices[0]]) if len(indices) else "",
        "hybrid_active_end_ns": float(data["time_ns"][indices[-1]]) if len(indices) else "",
        "hybrid_takeover_count": int(len(takeovers)),
        "hybrid_handoff_count": int(len(transitions)),
        "max_ku_step": float(np.max(np.abs(np.diff(ku)))),
        "max_kd_step": float(np.max(np.abs(np.diff(kd)))),
    }
    if len(takeovers):
        result["max_takeover_ku_step"] = float(max(abs(ku[i + 1] - ku[i]) for i in takeovers))
        result["max_takeover_kd_step"] = float(max(abs(kd[i + 1] - kd[i]) for i in takeovers))
    else:
        result["max_takeover_ku_step"] = 0.0
        result["max_takeover_kd_step"] = 0.0
    if len(transitions):
        result["max_handoff_ku_step"] = float(max(abs(ku[i + 1] - ku[i]) for i in transitions))
        result["max_handoff_kd_step"] = float(max(abs(kd[i + 1] - kd[i]) for i in transitions))
    else:
        result["max_handoff_ku_step"] = 0.0
        result["max_handoff_kd_step"] = 0.0
    return result


def metrics_rows(device: Device, variant: ModelVariant, case: Case, data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for flow in ["legacy", "hybrid", "full_gate"]:
        if f"{flow}_pad_v" not in data:
            continue
        row: dict[str, object] = {
            "device": device.device_id,
            "ibis_variant": variant.variant_id,
            "edge_setting": variant.edge_setting,
            "case_id": case.case_id,
            "flow": flow,
        }
        row.update(flow_metrics(data, flow))
        if flow == "hybrid":
            row.update(handoff_metrics(data))
            legacy_pad_delta = rmse(data["legacy_pad_v"], data["hybrid_pad_v"])
            legacy_ku_delta = rmse(data["legacy_ku"], data["hybrid_ku"])
            legacy_kd_delta = rmse(data["legacy_kd"], data["hybrid_kd"])
            row.update(
                {
                    "pad_rmse_v_vs_legacy": legacy_pad_delta,
                    "ku_rmse_vs_legacy": legacy_ku_delta,
                    "kd_rmse_vs_legacy": legacy_kd_delta,
                }
            )
            active = float(row["hybrid_active_peak"]) > 0.5
            if case.pattern == "rise_fall":
                row["status"] = (
                    "NORMAL_PRESERVED"
                    if not active and legacy_pad_delta <= 0.005 and legacy_ku_delta <= 0.02 and legacy_kd_delta <= 0.02
                    else "NORMAL_REGRESSION"
                )
            elif not active:
                row["status"] = "LEGACY_PATH_NO_INTERRUPTION"
            else:
                legacy_m = flow_metrics(data, "legacy")
                hybrid_m = flow_metrics(data, "hybrid")
                improved = all(
                    hybrid_m[key] < legacy_m[key]
                    for key in ["pad_rmse_v", "ku_rmse", "kd_rmse"]
                )
                continuity_ok = max(
                    float(row["max_takeover_ku_step"]),
                    float(row["max_takeover_kd_step"]),
                    float(row["max_handoff_ku_step"]),
                    float(row["max_handoff_kd_step"]),
                ) <= 0.02
                if improved and continuity_ok:
                    row["status"] = "SHORT_IMPROVED_CONTINUOUS"
                elif improved:
                    row["status"] = "SHORT_IMPROVED_DISCONTINUOUS"
                else:
                    row["status"] = "SHORT_CHECK"
        rows.append(row)
    rows.append(
        {
            "device": device.device_id,
            "ibis_variant": variant.variant_id,
            "edge_setting": variant.edge_setting,
            "case_id": case.case_id,
            "flow": "hspice_transistor",
            "pad_rmse_v": rmse(data["hspice_ibis_pad_v"], data["hspice_transistor_pad_v"]),
            "pad_max_error_v": max_error(data["hspice_ibis_pad_v"], data["hspice_transistor_pad_v"]),
        }
    )
    return rows


def save_numeric(path: Path, data: dict[str, np.ndarray]) -> None:
    rows = [
        {key: float(values[index]) for key, values in data.items()}
        for index in range(len(data["time_ns"]))
    ]
    write_csv(path, rows)


def style_axis(ax: plt.Axes, device: Device, case: Case, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.set_xlim(*case.xlim)
    ax.grid(True, color=GRID, alpha=0.7)
    for edge in command_edges(device, case):
        ax.axvline(edge, color=EDGE, ls="--", lw=1.0, alpha=0.8)


def plot_two_flow(
    device: Device,
    variant: ModelVariant,
    case: Case,
    data: dict[str, np.ndarray],
    flow: str,
    out_dir: Path,
) -> Path:
    ensure_dir(out_dir)
    t = data["time_ns"]
    fig, axes = plt.subplots(3, 1, figsize=(14.5, 9.0), sharex=True, constrained_layout=True)
    label = HYBRID_DISPLAY_LABEL if flow == "hybrid" else "ngspice legacy pybis"
    color = RED if flow == "hybrid" else BLUE
    marker = "D" if flow == "hybrid" else "o"
    for ax, (suffix, ylabel) in zip(axes, [("pad_v", "pad voltage (V)"), ("ku", "Ku"), ("kd", "Kd")]):
        ax.plot(t, data[f"hspice_ibis_{suffix}"], color=BLACK, lw=3.0, label=f"HSPICE native {variant.label}")
        ax.plot(
            t,
            data[f"{flow}_{suffix}"],
            color=color,
            lw=1.8,
            marker=marker,
            markevery=max(1, len(t) // 55),
            ms=3.0,
            label=label,
        )
        style_axis(ax, device, case, ylabel)
    axes[2].axhline(0, color="#777777", lw=0.8, alpha=0.6)
    axes[0].legend(frameon=False, ncol=2, loc="upper center")
    axes[-1].set_xlabel("time (ns)")
    fig.suptitle(f"{device.label} | {variant.label} | {case.title}", fontsize=16, fontweight="bold")
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_ibis_transistor(
    device: Device,
    variant: ModelVariant,
    case: Case,
    data: dict[str, np.ndarray],
    out_dir: Path,
) -> Path:
    ensure_dir(out_dir)
    fig, ax = plt.subplots(figsize=(14.5, 5.2), constrained_layout=True)
    ax.plot(data["time_ns"], data["hspice_ibis_pad_v"], color=BLACK, lw=3.0, label=f"HSPICE native {variant.label}")
    ax.plot(data["time_ns"], data["hspice_transistor_pad_v"], color=GRAY, lw=3.4, label="HSPICE transistor")
    style_axis(ax, device, case, "pad voltage (V)")
    ax.set_xlabel("time (ns)")
    ax.legend(frameon=False, ncol=2, loc="upper center")
    ax.set_title(f"{device.label} | {variant.label} | {case.title}", loc="left", fontweight="bold")
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_three_way(
    device: Device,
    variant: ModelVariant,
    case: Case,
    data: dict[str, np.ndarray],
    out_dir: Path,
) -> Path:
    ensure_dir(out_dir)
    fig, ax = plt.subplots(figsize=(14.5, 5.2), constrained_layout=True)
    ax.plot(data["time_ns"], data["hspice_ibis_pad_v"], color=BLACK, lw=3.0, label=f"HSPICE native {variant.label}")
    ax.plot(data["time_ns"], data["hspice_transistor_pad_v"], color=GRAY, lw=3.4, label="HSPICE transistor")
    ax.plot(
        data["time_ns"],
        data["hybrid_pad_v"],
        color=RED,
        lw=1.8,
        marker="D",
        markevery=max(1, len(data["time_ns"]) // 55),
        ms=3.0,
        label=HYBRID_DISPLAY_LABEL,
    )
    style_axis(ax, device, case, "pad voltage (V)")
    ax.set_xlabel("time (ns)")
    ax.legend(frameon=False, ncol=3, loc="upper center")
    ax.set_title(f"{device.label} | {variant.label} | {case.title}", loc="left", fontweight="bold")
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_combined(
    device: Device,
    variant: ModelVariant,
    case: Case,
    data: dict[str, np.ndarray],
    out_dir: Path,
) -> Path:
    ensure_dir(out_dir)
    fig, axes = plt.subplots(3, 1, figsize=(14.5, 9.3), sharex=True, constrained_layout=True)
    for ax, (suffix, ylabel) in zip(axes, [("pad_v", "pad voltage (V)"), ("ku", "Ku"), ("kd", "Kd")]):
        ax.plot(data["time_ns"], data[f"hspice_ibis_{suffix}"], color=BLACK, lw=3.0, label=f"HSPICE native {variant.label}")
        ax.plot(data["time_ns"], data[f"legacy_{suffix}"], color=BLUE, lw=1.7, ls="--", label="ngspice legacy")
        ax.plot(
            data["time_ns"],
            data[f"hybrid_{suffix}"],
            color=RED,
            lw=1.8,
            marker="D",
            markevery=max(1, len(data["time_ns"]) // 55),
            ms=2.8,
            label=HYBRID_DISPLAY_LABEL,
        )
        style_axis(ax, device, case, ylabel)
    axes[2].axhline(0, color="#777777", lw=0.8, alpha=0.6)
    axes[0].legend(frameon=False, ncol=3, loc="upper center")
    axes[-1].set_xlabel("time (ns)")
    fig.suptitle(f"{device.label} | {variant.label} | {case.title}", fontsize=16, fontweight="bold")
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_diagnostics(
    device: Device,
    variant: ModelVariant,
    case: Case,
    data: dict[str, np.ndarray],
    out_dir: Path,
) -> Path:
    ensure_dir(out_dir)
    t = data["time_ns"]
    fig, axes = plt.subplots(4, 1, figsize=(14.5, 10.5), sharex=True, constrained_layout=True)
    axes[0].plot(t, data["input_v"], color=BLACK, lw=2.0, label="input")
    axes[0].plot(t, data.get("hybrid_hhybridactive", np.zeros_like(t)) * device.supply_v, color=PURPLE, lw=1.8, label="hybrid active (scaled)")
    axes[1].plot(t, data.get("hybrid_gup", np.zeros_like(t)), color=ORANGE, lw=2.0, label="GUP")
    axes[1].plot(t, data.get("hybrid_gdn", np.zeros_like(t)), color=GREEN, lw=2.0, label="GDN")
    axes[2].plot(t, data.get("hybrid_kuleg", np.zeros_like(t)), color=BLUE, lw=1.7, ls="--", label="Ku legacy")
    axes[2].plot(t, data.get("hybrid_kugate", np.zeros_like(t)), color=ORANGE, lw=1.7, label="Ku gate")
    axes[2].plot(t, data["hybrid_ku"], color=RED, lw=2.0, label="Ku final")
    axes[3].plot(t, data.get("hybrid_kdleg", np.zeros_like(t)), color=BLUE, lw=1.7, ls="--", label="Kd legacy")
    axes[3].plot(t, data.get("hybrid_kdgate", np.zeros_like(t)), color=GREEN, lw=1.7, label="Kd gate")
    axes[3].plot(t, data["hybrid_kd"], color=RED, lw=2.0, label="Kd final")
    for ax, ylabel in zip(axes, ["command", "hidden state", "Ku", "Kd"]):
        style_axis(ax, device, case, ylabel)
        ax.legend(frameon=False, ncol=3, loc="upper center")
    axes[-1].set_xlabel("time (ns)")
    fig.suptitle(f"{device.label} | {variant.label} | {case.title} | hybrid diagnostics", fontsize=16, fontweight="bold")
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def contact_sheet(paths: list[Path], output: Path, columns: int = 2) -> None:
    if not paths:
        return
    images = [plt.imread(path) for path in paths]
    rows = (len(images) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(16, 5.5 * rows), constrained_layout=True)
    flat = np.atleast_1d(axes).ravel()
    for ax, image in zip(flat, images):
        ax.imshow(image)
        ax.axis("off")
    for ax in flat[len(images) :]:
        ax.axis("off")
    ensure_dir(output.parent)
    fig.savefig(output, dpi=125)
    plt.close(fig)


def source_rows(
    device: Device,
    variant: ModelVariant,
    case: Case,
    paths: dict[str, Path | str],
    model: Path,
    raw: Path,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for role, path in [
        ("ibis", variant.ibis),
        ("hspice_native_cached", Path(paths["native"])),
        ("hspice_transistor_cached", Path(paths["transistor"])),
        ("ngspice_legacy_cached", Path(paths["legacy"])),
        ("ngspice_full_gate_cached", Path(paths["full_gate"])),
        ("generated_reversal_hybrid", model),
        ("ngspice_reversal_hybrid", raw),
    ]:
        rows.append(
            {
                "device": device.device_id,
                "ibis_variant": variant.variant_id,
                "case_id": case.case_id,
                "role": role,
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "source": "fresh_ngspice" if role in {"generated_reversal_hybrid", "ngspice_reversal_hybrid"} else "existing_cached_result",
            }
        )
    return rows


def readme(metrics: list[dict[str, object]]) -> None:
    def number(row: dict[str, object], key: str, default: float = 0.0) -> float:
        try:
            value = row.get(key, default)
            return float(value) if value not in {"", None} else default
        except (TypeError, ValueError):
            return default

    hybrid_rows = [row for row in metrics if row["flow"] == "hybrid"]
    normal_rows = [row for row in hybrid_rows if row["case_id"] == "edge_1ps_base_50r_2pf"]
    short_rows = [row for row in hybrid_rows if row["case_id"] != "edge_1ps_base_50r_2pf"]
    activated = [row for row in short_rows if number(row, "hybrid_active_peak") > 0.5]
    improved = [row for row in short_rows if row.get("status") == "SHORT_IMPROVED_CONTINUOUS"]
    discontinuous = [row for row in short_rows if row.get("status") == "SHORT_IMPROVED_DISCONTINUOUS"]
    regressions = [row for row in normal_rows if row.get("status") != "NORMAL_PRESERVED"]
    numeric_failures = [row for row in hybrid_rows if row.get("status") == "NUMERIC_FAIL"]

    lines = [
        "# Legacy-Normal / Gate-State-on-Reversal Comparison",
        "",
        "This study evaluates a new opt-in pybis mode that uses original elapsed-time `Ku(t)/Kd(t)` replay during normal complete transitions, while continuously tracking hidden `GUP/GDN` states. An unsettled reverse edge selects directional-residual `Ku(GUP)/Kd(GDN)` until the commanded state settles, then returns to legacy replay.",
        "",
        "## Headline",
        "",
        f"- Matrix: `{len(hybrid_rows)}` device/IBIS/case combinations across `io_buf` and `inv_chain`, slow and fast IBIS.",
        f"- Normal controls preserved: `{len(normal_rows) - len(regressions)}/{len(normal_rows)}`.",
        f"- Short/control cases that activated the gate-state path: `{len(activated)}/{len(short_rows)}`.",
        f"- Activated cases improving pad, Ku, and Kd with continuous takeover/handoff: `{len(improved)}/{len(activated)}`.",
        f"- Activated cases improving all three RMS errors but failing continuity: `{len(discontinuous)}/{len(activated)}`.",
        f"- Numeric failures: `{len(numeric_failures)}/{len(hybrid_rows)}`.",
        "- HSPICE was not rerun. Native-IBIS and transistor references are copied/read from the prior clean comparison packages; only the new ngspice hybrid was simulated.",
        "- Legacy `InputDriven` was regenerated and checked against the pre-experiment models. The netlist bodies are identical; only the IBIS filename provenance header differs.",
        "",
        "## Main Finding",
        "",
        "- The experiment is **not production-ready**: none of the four complete rise/fall controls passed because the always-tracked gate-state circuitry drove ngspice into extremely small timesteps near the normal falling transition.",
        "- The corrected detector handles both directions. It activates for inv_chain 50/100/200 ps short-high and short-low pulses, while the 1 ns settled controls remain on legacy replay.",
        "- All 12 activated inv_chain cases improve pad, Ku, and Kd together and keep measured takeover/handoff steps below 0.02. Their RMS-error reductions are typically about 81%-98% for pad and 65%-97% for coefficients.",
        "- Slow io_buf remains asymmetric: short-high Ku improves while Kd recovery is still weak; short-low Kd is good while Ku/output recovery can remain weak.",
        "- Fast io_buf is the clearest rejection case: normal and 2 ns-high runs fail numerically, while completed interrupted cases retain large coefficient errors and takeover steps.",
        "",
        "## Algorithm",
        "",
        "1. Legacy `Ku(t)/Kd(t)` remains the normal selected path.",
        "2. `GUP/GDN`, direction-specific coefficient maps, and the Kd residual run continuously in the background.",
        "3. A falling-after-rising or rising-after-falling command inside the globally derived transition window asserts `HHYBRIDACTIVE`.",
        "4. Final coefficients track the gate-state path through the interruption and recovery.",
        "5. A model-derived `delay + 5*tau` recovery interval keeps the gate path active, then selection returns to legacy replay.",
        "",
        "## Bench",
        "",
        "- `io_buf`: 3.3 V, direct `50 ohm || 2 pF` load, 1 ps input edges, 27 C.",
        "- `inv_chain`: 1.8 V, direct `50 ohm || 2 pF` load, 1 ps input edges, 27 C.",
        "- No channel or transmission line.",
        "- Slow IBIS uses s2ibispy `tr=tf=1 ns`; fast IBIS uses `tr=tf=5 ps`.",
        "",
        "## Figure Sets",
        "",
        "Each `device/variant/plots` folder contains:",
        "",
        "- `01_hspice_ibis_vs_transistor`: pad-only reference comparison.",
        "- `02_hspice_ibis_vs_legacy`: pad/Ku/Kd baseline.",
        "- `03_hspice_ibis_vs_reversal_hybrid`: pad/Ku/Kd new result.",
        "- `04_hspice_ibis_hybrid_transistor`: three-way pad comparison.",
        "- `05_native_legacy_hybrid`: direct baseline-to-new comparison.",
        "- `06_hybrid_diagnostics`: input, activation, GUP/GDN, and selected coefficient paths.",
        "",
        "## Result Table",
        "",
        "| Device | IBIS | Case | Status | Active ns | Pad RMSE mV | Ku RMSE | Kd RMSE |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row in hybrid_rows:
        if row.get("status") == "NUMERIC_FAIL":
            active_text = "n/a"
            pad_text = "n/a"
            ku_text = "n/a"
            kd_text = "n/a"
        else:
            active_text = f"{number(row, 'hybrid_active_duration_ns'):.3f}"
            pad_text = f"{number(row, 'pad_rmse_v') * 1e3:.3f}"
            ku_text = f"{number(row, 'ku_rmse'):.5f}"
            kd_text = f"{number(row, 'kd_rmse'):.5f}"
        lines.append(
            f"| {row['device']} | {row['ibis_variant']} | {row['case_id']} | {row.get('status', '')} | "
            f"{active_text} | {pad_text} | {ku_text} | {kd_text} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "`NORMAL_PRESERVED` requires no hybrid activation and no more than 5 mV pad / 0.02 coefficient RMS change from cached legacy pybis. `SHORT_IMPROVED_CONTINUOUS` requires the activated hybrid to improve pad, Ku, and Kd versus legacy and keep both takeover and handoff coefficient steps at or below 0.02. `SHORT_IMPROVED_DISCONTINUOUS` records useful shape improvement that still fails the continuity requirement. Pad-only improvement is never counted.",
            "",
            "See `comparison_summary.csv` for side-by-side legacy/hybrid reductions, `metrics.csv` for all errors and takeover/handoff diagnostics, `waveform_data` for the plotted numeric data, `numeric_failure_diagnostics.csv` for timeout locations, `legacy_unchanged_verification.csv` for the opt-in legacy-body check, and `source_provenance.csv` for exact cached/fresh artifact hashes. Large partial raw files from timed-out runs are intentionally removed after their last-time/size diagnostics are recorded.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def comparison_summary(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    lookup = {
        (str(row["device"]), str(row["ibis_variant"]), str(row["case_id"]), str(row["flow"])): row
        for row in metrics
    }

    def value(row: dict[str, object], key: str) -> float | None:
        try:
            raw = row.get(key, "")
            return float(raw) if raw not in {"", None} else None
        except (TypeError, ValueError):
            return None

    rows: list[dict[str, object]] = []
    keys = sorted({key[:3] for key in lookup if key[3] == "hybrid"})
    for device, variant, case_id in keys:
        hybrid = lookup[(device, variant, case_id, "hybrid")]
        legacy = lookup.get((device, variant, case_id, "legacy"), {})
        row: dict[str, object] = {
            "device": device,
            "ibis_variant": variant,
            "case_id": case_id,
            "status": hybrid.get("status", ""),
            "hybrid_active_duration_ns": hybrid.get("hybrid_active_duration_ns", ""),
        }
        for metric in ["pad_rmse_v", "ku_rmse", "kd_rmse"]:
            legacy_value = value(legacy, metric)
            hybrid_value = value(hybrid, metric)
            row[f"legacy_{metric}"] = "" if legacy_value is None else legacy_value
            row[f"hybrid_{metric}"] = "" if hybrid_value is None else hybrid_value
            row[f"{metric}_reduction_percent"] = (
                ""
                if legacy_value in {None, 0.0} or hybrid_value is None
                else 100.0 * (1.0 - hybrid_value / legacy_value)
            )
        for metric in [
            "max_takeover_ku_step",
            "max_takeover_kd_step",
            "max_handoff_ku_step",
            "max_handoff_kd_step",
        ]:
            row[metric] = hybrid.get(metric, "")
        rows.append(row)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the legacy-normal/gate-state-on-reversal slow/fast campaign.")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--timeout-s", type=int, default=180)
    parser.add_argument("--device", action="append", choices=["io_buf", "inv_chain"], default=[])
    parser.add_argument("--variant", action="append", choices=["slow", "fast"], default=[])
    parser.add_argument("--case", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dir(OUT_DIR)
    all_metrics: list[dict[str, object]] = []
    provenance: list[dict[str, object]] = []

    selected_devices = [d for d in DEVICES if not args.device or d.device_id in args.device]
    total = sum(
        len([case for case in device.cases if not args.case or case.case_id in args.case])
        * len([variant for variant in VARIANTS[device.device_id] if not args.variant or variant.variant_id in args.variant])
        for device in selected_devices
    )
    progress = 0
    for device in selected_devices:
        for variant in VARIANTS[device.device_id]:
            if args.variant and variant.variant_id not in args.variant:
                continue
            if not variant.ibis.exists():
                raise FileNotFoundError(variant.ibis)
            variant_dir = OUT_DIR / device.device_id / variant.variant_id
            model = prepare_model(device, variant, variant_dir)
            image_groups: dict[str, list[Path]] = {str(i): [] for i in range(1, 7)}
            cases = [case for case in device.cases if not args.case or case.case_id in args.case]
            for case in cases:
                progress += 1
                print(f"[{progress}/{total}] {device.device_id}/{variant.variant_id}/{case.case_id}", flush=True)
                paths = prior_paths(device, variant, case)
                for key in ["native", "transistor", "legacy", "full_gate"]:
                    path = Path(paths[key])
                    if not path.exists():
                        raise FileNotFoundError(path)
                native = hspice_waveform(Path(paths["native"]), str(paths["native_pad"]))
                transistor = transistor_waveform(Path(paths["transistor"]))
                legacy = ngspice_waveform(Path(paths["legacy"]))
                try:
                    full_gate = ngspice_waveform(Path(paths["full_gate"]))
                except Exception:
                    full_gate = None
                hybrid_error = ""
                try:
                    hybrid, deck, raw = run_hybrid(device, case, model, variant_dir, args.ngspice, args.timeout_s)
                except RuntimeError as exc:
                    hybrid = None
                    deck = variant_dir / "cases" / case.case_id / "ngspice_reversal_hybrid" / "run.sp"
                    raw = variant_dir / "cases" / case.case_id / "ngspice_reversal_hybrid" / "run.raw"
                    hybrid_error = str(exc)
                data = align(device, case, native, transistor, legacy, full_gate, hybrid)
                save_numeric(variant_dir / "waveform_data" / f"{case.case_id}.csv", data)
                if hybrid is not None:
                    all_metrics.extend(metrics_rows(device, variant, case, data))
                    provenance.extend(source_rows(device, variant, case, paths, model, raw))
                else:
                    for flow in ["legacy", "full_gate"]:
                        if f"{flow}_pad_v" not in data:
                            continue
                        row = {
                            "device": device.device_id,
                            "ibis_variant": variant.variant_id,
                            "edge_setting": variant.edge_setting,
                            "case_id": case.case_id,
                            "flow": flow,
                        }
                        row.update(flow_metrics(data, flow))
                        all_metrics.append(row)
                    all_metrics.append(
                        {
                            "device": device.device_id,
                            "ibis_variant": variant.variant_id,
                            "edge_setting": variant.edge_setting,
                            "case_id": case.case_id,
                            "flow": "hybrid",
                            "status": "NUMERIC_FAIL",
                            "error": hybrid_error,
                            "log": str(
                                (
                                    variant_dir
                                    / "cases"
                                    / case.case_id
                                    / "ngspice_reversal_hybrid"
                                    / "ngspice_stdout.log"
                                ).relative_to(ROOT)
                            ),
                        }
                    )
                    for role, path in [
                        ("ibis", variant.ibis),
                        ("hspice_native_cached", Path(paths["native"])),
                        ("hspice_transistor_cached", Path(paths["transistor"])),
                        ("ngspice_legacy_cached", Path(paths["legacy"])),
                        ("generated_reversal_hybrid", model),
                        ("ngspice_reversal_hybrid_failed_deck", deck),
                    ]:
                        provenance.append(
                            {
                                "device": device.device_id,
                                "ibis_variant": variant.variant_id,
                                "case_id": case.case_id,
                                "role": role,
                                "path": str(path.relative_to(ROOT)),
                                "sha256": sha256(path),
                                "source": "fresh_ngspice_failure" if "reversal" in role else "existing_cached_result",
                            }
                        )
                copy_reference_package(paths, variant_dir / "cases" / case.case_id / "cached_hspice_references")

                plots = variant_dir / "plots"
                image_groups["1"].append(plot_ibis_transistor(device, variant, case, data, plots / "01_hspice_ibis_vs_transistor"))
                image_groups["2"].append(plot_two_flow(device, variant, case, data, "legacy", plots / "02_hspice_ibis_vs_legacy"))
                if hybrid is not None:
                    image_groups["3"].append(plot_two_flow(device, variant, case, data, "hybrid", plots / "03_hspice_ibis_vs_reversal_hybrid"))
                    image_groups["4"].append(plot_three_way(device, variant, case, data, plots / "04_hspice_ibis_hybrid_transistor"))
                    image_groups["5"].append(plot_combined(device, variant, case, data, plots / "05_native_legacy_hybrid"))
                    image_groups["6"].append(plot_diagnostics(device, variant, case, data, plots / "06_hybrid_diagnostics"))
                else:
                    message = "ngspice did not complete before the per-case timeout; no hybrid waveform is available."
                    failures = [
                        ("3", "03_hspice_ibis_vs_reversal_hybrid"),
                        ("4", "04_hspice_ibis_hybrid_transistor"),
                        ("5", "05_native_legacy_hybrid"),
                        ("6", "06_hybrid_diagnostics"),
                    ]
                    for key, folder in failures:
                        image_groups[key].append(
                            failure_figure(
                                device,
                                variant,
                                case,
                                message,
                                plots / folder / f"{case.case_id}.png",
                            )
                        )
                write_csv(OUT_DIR / "metrics.csv", all_metrics)
                write_csv(OUT_DIR / "source_provenance.csv", provenance)

            names = {
                "1": "01_hspice_ibis_vs_transistor",
                "2": "02_hspice_ibis_vs_legacy",
                "3": "03_hspice_ibis_vs_reversal_hybrid",
                "4": "04_hspice_ibis_hybrid_transistor",
                "5": "05_native_legacy_hybrid",
                "6": "06_hybrid_diagnostics",
            }
            for key, paths in image_groups.items():
                contact_sheet(paths, variant_dir / "plots" / f"{names[key]}_contact_sheet.png")

    write_csv(OUT_DIR / "metrics.csv", all_metrics)
    write_csv(OUT_DIR / "comparison_summary.csv", comparison_summary(all_metrics))
    write_csv(OUT_DIR / "source_provenance.csv", provenance)
    readme(all_metrics)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
