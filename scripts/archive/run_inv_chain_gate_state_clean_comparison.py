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
from hspice_reference_cache import (  # noqa: E402
    cache_dir,
    reference_signature,
    restore as restore_hspice_cache,
    save as save_hspice_cache,
)
from pybis2spice import pybis2spice, subcircuit  # noqa: E402
import run_io_buf_two_state_gate_model as gate_helpers  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


OUT_DIR = ROOT / "results" / "inv_chain_gate_state_clean_comparison_2026-07-27"
COMMON_DIR = OUT_DIR / "common"
CASES_DIR = OUT_DIR / "cases"
PLOTS_DIR = OUT_DIR / "plots"
DATA_DIR = OUT_DIR / "waveform_data"
FIT_DIR = OUT_DIR / "fit_diagnostics"

DEFAULT_IBIS = ROOT / "inv_chain" / "t2b_0615_v5.ibs"
DEFAULT_TRANSISTOR_WRAPPER = ROOT / "inv_chain" / "clean_ibis_vs_pybis_matched_pkg" / "invchain_ref_ngspice.sub"
DEFAULT_TRANSISTOR_LIBRARY = ROOT / "inv_chain" / "clean_ibis_vs_pybis_matched_pkg" / "HL18G-S3.7S.lib"
DEFAULT_NGSPICE = default_ngspice(console=True)
DEFAULT_HSPICE = default_hspice()

COMPONENT_NAME = "invchain"
MODEL_NAME = "driver2"
SUPPLY_V = 1.8
LOAD_OHM = 50.0
LOAD_PF = 2.0
EDGE_NS = 0.001

BLACK = "#111111"
GRAY = "#8a8a8a"
RED = "#d62728"
BLUE = "#1769aa"
EDGE_COLOR = "#8d8d8d"


@dataclass(frozen=True)
class Case:
    case_id: str
    title: str
    pattern: str
    pulse_width_ns: float
    stop_ns: float


CASES = [
    Case("edge_1ps_base_50r_2pf", "Complete rise and fall", "rise_fall", 10.0, 22.0),
    Case("short_pulse_50ps_high", "Interrupted 50 ps high pulse", "short_high", 0.05, 10.0),
    Case("short_pulse_100ps_high", "Interrupted 100 ps high pulse", "short_high", 0.1, 10.0),
    Case("short_pulse_200ps_high", "Interrupted 200 ps high pulse", "short_high", 0.2, 10.0),
    Case("short_pulse_1ns_high", "Settled 1 ns high-pulse control", "short_high", 1.0, 12.0),
    Case("short_pulse_50ps_low", "Interrupted 50 ps low pulse", "short_low", 0.05, 14.0),
    Case("short_pulse_100ps_low", "Interrupted 100 ps low pulse", "short_low", 0.1, 14.0),
    Case("short_pulse_200ps_low", "Interrupted 200 ps low pulse", "short_low", 0.2, 14.0),
    Case("short_pulse_1ns_low", "Settled 1 ns low-pulse control", "short_low", 1.0, 15.0),
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_process(cmd: list[str], cwd: Path, log_path: Path, timeout_s: int) -> int:
    try:
        proc = subprocess.run(
            cmd,
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
        log_path.write_text(
            "COMMAND: " + " ".join(cmd) + f"\n\nTIMEOUT after {timeout_s} seconds\n\n" + str(captured),
            encoding="utf-8",
            errors="replace",
        )
        return 124
    log_path.write_text(
        "COMMAND: " + " ".join(cmd) + "\n\n" + proc.stdout,
        encoding="utf-8",
        errors="replace",
    )
    return int(proc.returncode)


def fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-12:
        return str(int(round(value)))
    return f"{value:.12g}"


def points(case: Case) -> list[tuple[float, float]]:
    e = EDGE_NS
    if case.pattern == "rise_fall":
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + e, SUPPLY_V),
            (15.0, SUPPLY_V),
            (15.0 + e, 0.0),
            (case.stop_ns, 0.0),
        ]
    if case.pattern == "short_high":
        reverse = 5.0 + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + e, SUPPLY_V),
            (reverse, SUPPLY_V),
            (reverse + e, 0.0),
            (case.stop_ns, 0.0),
        ]
    if case.pattern == "short_low":
        reverse = 10.0 + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + e, SUPPLY_V),
            (10.0, SUPPLY_V),
            (10.0 + e, 0.0),
            (reverse, 0.0),
            (reverse + e, SUPPLY_V),
            (case.stop_ns, SUPPLY_V),
        ]
    if case.pattern == "double_toggle":
        fall = 5.0 + case.pulse_width_ns
        rise2 = fall + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + e, SUPPLY_V),
            (fall, SUPPLY_V),
            (fall + e, 0.0),
            (rise2, 0.0),
            (rise2 + e, SUPPLY_V),
            (case.stop_ns, SUPPLY_V),
        ]
    raise ValueError(case.pattern)


def pwl(case: Case) -> str:
    lines = ["Vin in_dig 0 PWL("]
    for time_ns, voltage in points(case):
        lines.append(f"+ {fmt(time_ns)}n {fmt(voltage)}")
    lines[-1] += " )"
    return "\n".join(lines)


def command_edges(case: Case) -> list[float]:
    result: list[float] = []
    pts = points(case)
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if abs(v1 - v0) > 1e-12:
            result.append(0.5 * (t0 + t1))
    return result


def xlim(case: Case) -> tuple[float, float]:
    edges = command_edges(case)
    if case.pattern == "rise_fall":
        return 4.0, min(case.stop_ns, edges[-1] + 3.0)
    return max(0.0, edges[0] - 1.0), min(case.stop_ns, edges[-1] + 4.0)


def input_waveform(case: Case, t_ns: np.ndarray) -> np.ndarray:
    pts = points(case)
    return np.interp(t_ns, [p[0] for p in pts], [p[1] for p in pts])


def active_mask(case: Case, t_ns: np.ndarray) -> np.ndarray:
    lo, hi = xlim(case)
    return (t_ns >= lo) & (t_ns <= hi)


def make_hspice_native_deck(case: Case) -> str:
    return f"""* inv_chain HSPICE native IBIS reference
* case: {case.case_id}
.title inv_chain native IBIS {case.case_id}
.option post=2 probe accurate
.option ingold=2
.temp 27

{pwl(case)}

VPU pu_ref 0 DC {SUPPLY_V}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUPPLY_V}
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='t2b_0615_v5.ibs'
+ model='driver2'
+ buffer=2
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rload pad_ibis 0 {LOAD_OHM}
Cload pad_ibis 0 {LOAD_PF}p

.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran 0.001n {fmt(case.stop_ns)}n
.end
"""


def make_hspice_transistor_deck(case: Case) -> str:
    return f"""* inv_chain HSPICE transistor reference
* case: {case.case_id}
.title inv_chain transistor {case.case_id}
.option post=2 probe accurate
.option ingold=2
.temp 27

{pwl(case)}

Vdd vdd 0 DC {SUPPLY_V}
.include 'invchain_ref_ngspice.sub'
XREF in_dig pad_sp vdd 0 invchain_ref

Rload pad_sp 0 {LOAD_OHM}
Cload pad_sp 0 {LOAD_PF}p

.probe tran V(in_dig) V(pad_sp)
.tran 0.001n {fmt(case.stop_ns)}n
.end
"""


def make_ngspice_deck(case: Case, flow: str) -> str:
    extra = ""
    if flow == "gate_state":
        extra = (
            " V(xdrv.gup) V(xdrv.gdn)"
            " V(xdrv.guptarget) V(xdrv.gdntarget)"
            " V(xdrv.kugate) V(xdrv.kdgate)"
        )
    elif flow == "reversal_hybrid":
        extra = (
            " V(xdrv.gup) V(xdrv.gdn)"
            " V(xdrv.guptarget) V(xdrv.gdntarget)"
            " V(xdrv.kugate) V(xdrv.kdgate)"
            " V(xdrv.kuleg) V(xdrv.kdleg)"
            " V(xdrv.kutarget) V(xdrv.kdtarget)"
            " V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)"
            " V(xdrv.hreverseraw) V(xdrv.hsettled)"
            " V(xdrv.hhybridactive)"
            " V(xdrv.highage) V(xdrv.lowage)"
        )
    return f"""* inv_chain ngspice {flow}
* case: {case.case_id}
.title inv_chain ngspice {flow} {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{pwl(case)}

Ven en_sig 0 DC {SUPPLY_V}
Vdd vdd 0 DC {SUPPLY_V}
.include 'driver2_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver2_OutputInput_Typical

Rload pad 0 {LOAD_OHM}
Cload pad 0 {LOAD_PF}p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){extra}
.tran 0.001n {fmt(case.stop_ns)}n
.end
"""


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"missing signal {names}; available: {', '.join(sorted(data))}")


def optional_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray | None:
    try:
        return find_signal(data, *names)
    except KeyError:
        return None


def to_ns(values: np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=float) * 1e9


def interp(t_src: np.ndarray, values: np.ndarray, t_dst: np.ndarray) -> np.ndarray:
    return np.interp(t_dst, t_src, values)


def rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.sqrt(np.mean((candidate - reference) ** 2)))


def max_error(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.max(np.abs(candidate - reference)))


def cache_hspice(
    family: str,
    case: Case,
    deck_text: str,
    input_paths: list[Path],
    out_dir: Path,
    stem: str,
    hspice: Path,
    timeout_s: int,
) -> str:
    signature_id, signature = reference_signature(
        deck_text,
        input_paths,
        {
            "family": family,
            "case_id": case.case_id,
            "supply_v": SUPPLY_V,
            "load_ohm": LOAD_OHM,
            "load_pf": LOAD_PF,
            "edge_ns": EDGE_NS,
        },
    )
    h_cache = cache_dir(family, case.case_id, signature_id)
    if restore_hspice_cache(h_cache, out_dir, stem, deck_text):
        return "cache"
    deck = out_dir / f"{stem}.sp"
    write_text(deck, deck_text)
    rc = run_process(
        [str(hspice), "-i", deck.name, "-o", stem],
        out_dir,
        out_dir / "hspice_stdout.log",
        timeout_s,
    )
    if rc != 0:
        raise RuntimeError(f"HSPICE failed for {family}/{case.case_id}; see {out_dir / 'hspice_stdout.log'}")
    if not (out_dir / f"{stem}.tr0").exists():
        raise RuntimeError(f"HSPICE did not write {stem}.tr0")
    save_hspice_cache(h_cache, out_dir, stem, deck_text, signature)
    return "run"


def run_hspice_native(case: Case, ibis: Path, hspice: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = CASES_DIR / case.case_id / "hspice_native_ibis"
    ensure_dir(out_dir)
    shutil.copy2(ibis, out_dir / "t2b_0615_v5.ibs")
    stem = f"{case.case_id}_hspice_native_ibis"
    deck_text = make_hspice_native_deck(case)
    source = cache_hspice(
        "inv_chain_native_ibis_direct_50r_2pf",
        case,
        deck_text,
        [ibis],
        out_dir,
        stem,
        hspice,
        timeout_s,
    )
    tr0 = out_dir / f"{stem}.tr0"
    return parse_hspice_tr0(tr0), {
        "case_id": case.case_id,
        "reference": "hspice_native_ibis",
        "source": source,
        "deck": str((out_dir / f"{stem}.sp").relative_to(ROOT)),
        "tr0": str(tr0.relative_to(ROOT)),
        "lis": str((out_dir / f"{stem}.lis").relative_to(ROOT)),
    }


def run_hspice_transistor(
    case: Case,
    wrapper: Path,
    library: Path,
    hspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = CASES_DIR / case.case_id / "hspice_transistor"
    ensure_dir(out_dir)
    shutil.copy2(wrapper, out_dir / "invchain_ref_ngspice.sub")
    shutil.copy2(library, out_dir / "HL18G-S3.7S.lib")
    stem = f"{case.case_id}_hspice_transistor"
    deck_text = make_hspice_transistor_deck(case)
    source = cache_hspice(
        "inv_chain_transistor_direct_50r_2pf",
        case,
        deck_text,
        [wrapper, library],
        out_dir,
        stem,
        hspice,
        timeout_s,
    )
    tr0 = out_dir / f"{stem}.tr0"
    return parse_hspice_tr0(tr0), {
        "case_id": case.case_id,
        "reference": "hspice_transistor",
        "source": source,
        "deck": str((out_dir / f"{stem}.sp").relative_to(ROOT)),
        "tr0": str(tr0.relative_to(ROOT)),
        "lis": str((out_dir / f"{stem}.lis").relative_to(ROOT)),
    }


def run_ngspice(
    case: Case,
    flow: str,
    model_path: Path,
    ngspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], Path, Path]:
    out_dir = CASES_DIR / case.case_id / f"ngspice_{flow}"
    ensure_dir(out_dir)
    shutil.copy2(model_path, out_dir / "driver2_OutputInput_Typical.sub")
    stem = f"{case.case_id}_ngspice_{flow}"
    deck = out_dir / f"{stem}.sp"
    raw = out_dir / f"{stem}.raw"
    write_text(deck, make_ngspice_deck(case, flow))
    rc = run_process(
        [str(ngspice), "-b", "-r", raw.name, deck.name],
        out_dir,
        out_dir / "ngspice_stdout.log",
        timeout_s,
    )
    if rc != 0 or not raw.exists():
        raise RuntimeError(f"ngspice failed for {flow}/{case.case_id}; see {out_dir / 'ngspice_stdout.log'}")
    return parse_ngspice_raw(raw), deck, raw


def prepare_models(ibis: Path) -> dict[str, Path]:
    ensure_dir(COMMON_DIR)
    common_ibis = COMMON_DIR / "t2b_0615_v5.ibs"
    shutil.copy2(ibis, common_ibis)
    specs = {
        "legacy": "InputDriven",
        "gate_state": "InputDrivenTwoStateGateDirectionalResidualFull",
    }
    result: dict[str, Path] = {}
    for flow, subcircuit_type in specs.items():
        out = COMMON_DIR / flow / "driver2_OutputInput_Typical.sub"
        convert_ibis_to_pybis(
            ibis_path=common_ibis,
            output_path=out,
            component_name=COMPONENT_NAME,
            model_name=MODEL_NAME,
            io_type="Output",
            subcircuit_type=subcircuit_type,
            corner="Typical",
        )
        result[flow] = out
    return result


def offline_fit(ibis: Path) -> dict[str, object]:
    ensure_dir(FIT_DIR)
    parsed = pybis2spice.get_ibis_model_ecdtools(str(ibis))
    model = pybis2spice.DataModel(parsed, model_name=MODEL_NAME, component_name=COMPONENT_NAME)
    corner = subcircuit.convert_corner_str_to_index("Typical") + 1
    kr = pybis2spice.compress_param(
        pybis2spice.solve_k_params_output(model, corner=corner, waveform_type="Rising"),
        threshold=1e-3,
    )
    kf = pybis2spice.compress_param(
        pybis2spice.solve_k_params_output(model, corner=corner, waveform_type="Falling"),
        threshold=1e-3,
    )
    fit = subcircuit.gate_state_fit(kr, kf)
    rows, data = gate_helpers.reconstruction_rows_and_data(kr, kf, fit)
    write_csv(OUT_DIR / "normal_k_reconstruction.csv", rows)
    residual_rows = [row for row in rows if row["candidate"] == "directional_residual"]
    summary: dict[str, object] = {
        "component": COMPONENT_NAME,
        "model": MODEL_NAME,
        "ibis": str(ibis.relative_to(ROOT)),
        "ibis_sha256": file_sha256(ibis),
        "worst_rmse": max(float(row["rmse"]) for row in residual_rows),
        "worst_max_error": max(float(row["max_error"]) for row in residual_rows),
        "gate": "PASS"
        if max(float(row["rmse"]) for row in residual_rows) <= 0.02
        and max(float(row["max_error"]) for row in residual_rows) <= 0.08
        else "FAIL",
        "pu_on_delay_ns": fit["pu_on_delay"],
        "pu_off_delay_ns": fit["pu_off_delay"],
        "pd_on_delay_ns": fit["pd_on_delay"],
        "pd_off_delay_ns": fit["pd_off_delay"],
        "pu_on_tau_ns": fit["pu_on_tau"],
        "pu_off_tau_ns": fit["pu_off_tau"],
        "pd_on_tau_ns": fit["pd_on_tau"],
        "pd_off_tau_ns": fit["pd_off_tau"],
    }
    write_csv(OUT_DIR / "gate_fit_summary.csv", [summary])

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), constrained_layout=True)
    specs = [
        ("tr", "ku_rise", "Ku rising"),
        ("tf", "ku_fall", "Ku falling"),
        ("tr", "kd_rise", "Kd rising"),
        ("tf", "kd_fall", "Kd falling"),
    ]
    for ax, (tkey, key, title) in zip(axes.flat, specs):
        ax.plot(data[tkey], data[f"{key}_orig"], color=BLACK, lw=2.6, label="IBIS-derived table")
        ax.plot(
            data[tkey],
            data[f"{key}_directional_residual"],
            color=RED,
            lw=1.8,
            marker="D",
            markevery=max(1, len(data[tkey]) // 24),
            ms=3.0,
            label="directional-residual reconstruction",
        )
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("table time (ns)")
        ax.set_ylabel(key.split("_")[0].upper())
        ax.grid(True, color="#d7d7d7", alpha=0.7)
    axes[0, 0].legend(frameon=False)
    fig.suptitle("inv_chain complete-edge coefficient reconstruction", fontweight="bold")
    fig.savefig(FIT_DIR / "ku_kd_table_reconstruction.png", dpi=180)
    plt.close(fig)
    return summary


def align_case(
    case: Case,
    h_native: dict[str, np.ndarray],
    h_transistor: dict[str, np.ndarray],
    ng_legacy: dict[str, np.ndarray],
    ng_gate: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    t = to_ns(find_signal(h_native, "time"))
    result: dict[str, np.ndarray] = {
        "time_ns": t,
        "input_v": input_waveform(case, t),
        "hspice_ibis_pad_v": find_signal(h_native, "v(pad_ibis)"),
        "hspice_ibis_ku": find_signal(h_native, "v(ku)"),
        "hspice_ibis_kd": find_signal(h_native, "v(kd)"),
    }
    ht = to_ns(find_signal(h_transistor, "time"))
    result["hspice_transistor_pad_v"] = interp(ht, find_signal(h_transistor, "v(pad_sp)"), t)
    for prefix, raw in [("legacy", ng_legacy), ("gate_state", ng_gate)]:
        nt = to_ns(find_signal(raw, "time"))
        result[f"{prefix}_pad_v"] = interp(nt, find_signal(raw, "v(pad)"), t)
        result[f"{prefix}_ku"] = interp(nt, find_signal(raw, "v(xdrv.ku)", "v(xdrv:ku)"), t)
        result[f"{prefix}_kd"] = interp(nt, find_signal(raw, "v(xdrv.kd)", "v(xdrv:kd)"), t)
        if prefix == "gate_state":
            for signal in ["gup", "gdn", "guptarget", "gdntarget", "kugate", "kdgate"]:
                values = optional_signal(raw, f"v(xdrv.{signal})", f"v(xdrv:{signal})")
                if values is not None:
                    result[f"gate_state_{signal}"] = interp(nt, values, t)
    rows = [
        {
            key: float(values[idx])
            for key, values in result.items()
        }
        for idx in range(len(t))
    ]
    write_csv(DATA_DIR / f"{case.case_id}.csv", rows)
    return result


def case_metrics(case: Case, data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    mask = active_mask(case, data["time_ns"])
    rows: list[dict[str, object]] = []
    for flow in ["legacy", "gate_state"]:
        rows.append(
            {
                "case_id": case.case_id,
                "flow": flow,
                "pad_rmse_v_vs_hspice_ibis": rmse(
                    data["hspice_ibis_pad_v"][mask],
                    data[f"{flow}_pad_v"][mask],
                ),
                "pad_max_error_v_vs_hspice_ibis": max_error(
                    data["hspice_ibis_pad_v"][mask],
                    data[f"{flow}_pad_v"][mask],
                ),
                "ku_rmse_vs_hspice_ibis": rmse(
                    data["hspice_ibis_ku"][mask],
                    data[f"{flow}_ku"][mask],
                ),
                "ku_max_error_vs_hspice_ibis": max_error(
                    data["hspice_ibis_ku"][mask],
                    data[f"{flow}_ku"][mask],
                ),
                "kd_rmse_vs_hspice_ibis": rmse(
                    data["hspice_ibis_kd"][mask],
                    data[f"{flow}_kd"][mask],
                ),
                "kd_max_error_vs_hspice_ibis": max_error(
                    data["hspice_ibis_kd"][mask],
                    data[f"{flow}_kd"][mask],
                ),
                "pad_min_v": float(np.min(data[f"{flow}_pad_v"][mask])),
                "pad_max_v": float(np.max(data[f"{flow}_pad_v"][mask])),
                "ku_min": float(np.min(data[f"{flow}_ku"][mask])),
                "ku_max": float(np.max(data[f"{flow}_ku"][mask])),
                "kd_min": float(np.min(data[f"{flow}_kd"][mask])),
                "kd_max": float(np.max(data[f"{flow}_kd"][mask])),
            }
        )
    rows.append(
        {
            "case_id": case.case_id,
            "flow": "hspice_transistor",
            "pad_rmse_v_vs_hspice_ibis": rmse(
                data["hspice_ibis_pad_v"][mask],
                data["hspice_transistor_pad_v"][mask],
            ),
            "pad_max_error_v_vs_hspice_ibis": max_error(
                data["hspice_ibis_pad_v"][mask],
                data["hspice_transistor_pad_v"][mask],
            ),
            "pad_min_v": float(np.min(data["hspice_transistor_pad_v"][mask])),
            "pad_max_v": float(np.max(data["hspice_transistor_pad_v"][mask])),
        }
    )
    rows.append(
        {
            "case_id": case.case_id,
            "flow": "hspice_native_ibis",
            "pad_min_v": float(np.min(data["hspice_ibis_pad_v"][mask])),
            "pad_max_v": float(np.max(data["hspice_ibis_pad_v"][mask])),
            "ku_min": float(np.min(data["hspice_ibis_ku"][mask])),
            "ku_max": float(np.max(data["hspice_ibis_ku"][mask])),
            "kd_min": float(np.min(data["hspice_ibis_kd"][mask])),
            "kd_max": float(np.max(data["hspice_ibis_kd"][mask])),
        }
    )
    return rows


def style_axis(ax: plt.Axes, ylabel: str, case: Case) -> None:
    ax.set_ylabel(ylabel)
    ax.set_xlim(*xlim(case))
    ax.grid(True, color="#d8d8d8", alpha=0.62)
    for edge in command_edges(case):
        ax.axvline(edge, color=EDGE_COLOR, lw=1.0, ls="--", alpha=0.78)


def plot_two_flow(case: Case, data: dict[str, np.ndarray], flow: str, label: str, out_dir: Path) -> Path:
    ensure_dir(out_dir)
    t = data["time_ns"]
    fig, axes = plt.subplots(3, 1, figsize=(14.0, 9.0), sharex=True, constrained_layout=True)
    specs = [
        ("pad_v", "pad voltage (V)"),
        ("ku", "Ku"),
        ("kd", "Kd"),
    ]
    for ax, (suffix, ylabel) in zip(axes, specs):
        ax.plot(t, data[f"hspice_ibis_{suffix}"], color=BLACK, lw=3.0, label="HSPICE native IBIS")
        ax.plot(
            t,
            data[f"{flow}_{suffix}"],
            color=RED if flow == "gate_state" else BLUE,
            lw=1.9,
            marker="D" if flow == "gate_state" else "o",
            markevery=max(1, len(t) // 45),
            ms=3.0,
            label=label,
        )
        style_axis(ax, ylabel, case)
    axes[2].axhline(0.0, color="#777777", lw=0.8, alpha=0.55)
    axes[0].legend(frameon=False, ncol=3, loc="upper center")
    axes[-1].set_xlabel("time (ns)")
    fig.suptitle(case.title, fontweight="bold", fontsize=16)
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_pad_three_way(case: Case, data: dict[str, np.ndarray], out_dir: Path) -> Path:
    ensure_dir(out_dir)
    t = data["time_ns"]
    fig, ax = plt.subplots(figsize=(14.0, 5.2), constrained_layout=True)
    ax.plot(t, data["hspice_ibis_pad_v"], color=BLACK, lw=3.0, label="HSPICE native IBIS")
    ax.plot(t, data["hspice_transistor_pad_v"], color=GRAY, lw=4.0, alpha=0.92, label="HSPICE transistor")
    ax.plot(
        t,
        data["gate_state_pad_v"],
        color=RED,
        lw=2.0,
        marker="D",
        markevery=max(1, len(t) // 45),
        ms=3.2,
        label="ngspice gate-state",
    )
    style_axis(ax, "pad voltage (V)", case)
    ax.set_xlabel("time (ns)")
    ax.legend(frameon=False, ncol=4, loc="upper center")
    ax.set_title(case.title, fontweight="bold", fontsize=16)
    path = out_dir / f"{case.case_id}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def contact_sheet(image_paths: list[Path], output: Path, columns: int = 2) -> None:
    images = [plt.imread(path) for path in image_paths]
    rows = (len(images) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(15.0, 5.4 * rows), constrained_layout=True)
    axes_array = np.atleast_1d(axes).ravel()
    for ax, image in zip(axes_array, images):
        ax.imshow(image)
        ax.axis("off")
    for ax in axes_array[len(images):]:
        ax.axis("off")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=130)
    plt.close(fig)


def write_readme(
    fit: dict[str, object],
    metrics: list[dict[str, object]],
    cache_rows: list[dict[str, object]],
    ibis: Path,
    wrapper: Path,
    library: Path,
) -> None:
    lookup = {(str(row["case_id"]), str(row["flow"])): row for row in metrics}
    lines = [
        "# inv_chain Clean IBIS / pybis / Transistor Comparison",
        "",
        "This study applies the same clean comparison format used for `io_buf` to the established `inv_chain` buffer.",
        "",
        "## Headline Findings",
        "",
        "- `inv_chain` is much faster than `io_buf`: its complete-edge coefficient activity is concentrated near `0.2-0.4 ns`, so `1 ns` pulses are settled controls, not interrupted-pulse tests.",
        "- On the complete-edge control, legacy pybis remains better than gate-state: pad RMSE is `59.1 mV` vs `110.2 mV`.",
        "- On 50/100/200 ps short-high pulses, gate-state reduces pad RMSE from `1006/831/695 mV` to `110/108/114 mV` versus native HSPICE IBIS.",
        "- On 50/100/200 ps short-low pulses, gate-state reduces pad RMSE from `704/459/412 mV` to `151/97/103 mV` versus native HSPICE IBIS.",
        "- This is improved native-IBIS playback, not transistor-level validation. The transistor chain suppresses the 50 ps high pulse and the 100 ps low pulse. Native IBIS and gate-state still produce approximately `0.46 V` and `0.50 V` for the 50 ps high case.",
        "- The directional-residual offline reconstruction gate still fails on `Ku` rise, and the gate-state model leaves visible coefficient/tail errors. It is not a default replacement.",
        "",
        "## Setup",
        "",
        f"- IBIS: `{ibis.relative_to(ROOT)}`",
        f"- IBIS component/model: `{COMPONENT_NAME}` / `{MODEL_NAME}`",
        f"- Transistor wrapper: `{wrapper.relative_to(ROOT)}`",
        f"- Transistor library: `{library.relative_to(ROOT)}`",
        f"- Supply: `{SUPPLY_V} V`",
        f"- Load in every flow: `{LOAD_OHM:.0f} ohm || {LOAD_PF:g} pF`",
        "- Loaded steady high is approximately `1.42 V`, or `28.4 mA` into 50 ohm; this corresponds to about `13.3 ohm` effective pullup resistance at that operating point.",
        f"- Input edge: `{EDGE_NS * 1e3:g} ps`",
        "- Temperature: `27 C`",
        "- No channel or transmission line is present.",
        "",
        "## Model Provenance",
        "",
        "`t2b_0615_v5.ibs` is the established direct T2B `driver2` model used by the prior matched inv_chain study. `t2b_0616_v3.ibs` is a coarser export of the same model, not a separate fast-edge model, so it is not presented as a slow/fast pair.",
        "",
        "## Offline Reconstruction Gate",
        "",
        f"- Directional-residual worst table RMSE: `{float(fit['worst_rmse']):.6f}`",
        f"- Directional-residual worst table max error: `{float(fit['worst_max_error']):.6f}`",
        f"- Gate result: **{fit['gate']}**",
        "",
        "The gate-state transient figures are diagnostic when this gate is `FAIL`; they are not a validated replacement for legacy pybis.",
        "",
        "## Clean Figure Sets",
        "",
        "- `plots/01_legacy_vs_hspice_ibis/`: original pybis vs native HSPICE IBIS, pad/Ku/Kd.",
        "- `plots/02_gate_state_vs_hspice_ibis/`: directional-residual gate-state vs native HSPICE IBIS, pad/Ku/Kd.",
        "- `plots/03_ibis_gate_state_transistor_pad/`: pad-only native IBIS, gate-state, and transistor overlays.",
        "- `plots/*_contact_sheet.png`: one-page overviews.",
        "- `waveform_data/*.csv`: aligned numeric data behind every figure.",
        "- `metrics.csv`: pad/Ku/Kd error and extrema values.",
        "- `source_provenance.csv`: source and generated-model hashes.",
        "",
        "## Metrics",
        "",
        "| Case | Flow | Pad RMSE (mV) | Ku RMSE | Kd RMSE |",
        "|---|---|---:|---:|---:|",
    ]
    for case in CASES:
        for flow in ["legacy", "gate_state", "hspice_transistor"]:
            row = lookup.get((case.case_id, flow), {})
            pad = float(row.get("pad_rmse_v_vs_hspice_ibis", float("nan"))) * 1e3
            ku = float(row.get("ku_rmse_vs_hspice_ibis", float("nan")))
            kd = float(row.get("kd_rmse_vs_hspice_ibis", float("nan")))
            lines.append(
                f"| {case.case_id} | {flow} | {pad:.3f} | "
                f"{ku:.5f}" if np.isfinite(ku) else f"| {case.case_id} | {flow} | {pad:.3f} | n/a"
            )
            if np.isfinite(ku):
                lines[-1] += f" | {kd:.5f} |"
            else:
                lines[-1] += " | n/a |"
    lines.extend(
        [
            "",
            "## HSPICE Cache",
            "",
            "| Case | Reference | Source |",
            "|---|---|---|",
        ]
    )
    for row in cache_rows:
        lines.append(f"| {row['case_id']} | {row['reference']} | {row['source']} |")
    lines.append("")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_provenance(
    ibis: Path,
    wrapper: Path,
    library: Path,
    models: dict[str, Path],
) -> None:
    rows: list[dict[str, object]] = []
    for role, path in [
        ("ibis", ibis),
        ("transistor_wrapper", wrapper),
        ("transistor_library", library),
        ("generated_legacy_model", models["legacy"]),
        ("generated_gate_state_model", models["gate_state"]),
    ]:
        rows.append(
            {
                "role": role,
                "path": str(path.relative_to(ROOT)),
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    write_csv(OUT_DIR / "source_provenance.csv", rows)


def select_cases(case_ids: list[str]) -> list[Case]:
    if not case_ids:
        return CASES
    lookup = {case.case_id: case for case in CASES}
    missing = [case_id for case_id in case_ids if case_id not in lookup]
    if missing:
        raise ValueError(f"unknown case(s): {', '.join(missing)}")
    return [lookup[case_id] for case_id in case_ids]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean inv_chain HSPICE / pybis gate-state comparison.")
    parser.add_argument("--ibis", type=Path, default=DEFAULT_IBIS)
    parser.add_argument("--transistor-wrapper", type=Path, default=DEFAULT_TRANSISTOR_WRAPPER)
    parser.add_argument("--transistor-library", type=Path, default=DEFAULT_TRANSISTOR_LIBRARY)
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--hspice", type=Path, default=DEFAULT_HSPICE)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--timeout-s", type=int, default=240)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in [OUT_DIR, COMMON_DIR, CASES_DIR, PLOTS_DIR, DATA_DIR, FIT_DIR]:
        ensure_dir(path)
    fit = offline_fit(args.ibis)
    models = prepare_models(args.ibis)
    write_provenance(
        args.ibis,
        args.transistor_wrapper,
        args.transistor_library,
        models,
    )
    metrics: list[dict[str, object]] = []
    cache_rows: list[dict[str, object]] = []
    legacy_images: list[Path] = []
    gate_images: list[Path] = []
    three_way_images: list[Path] = []

    cases = select_cases(args.case)
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id}", flush=True)
        h_native, cache_native = run_hspice_native(case, args.ibis, args.hspice, args.timeout_s)
        h_transistor, cache_transistor = run_hspice_transistor(
            case,
            args.transistor_wrapper,
            args.transistor_library,
            args.hspice,
            args.timeout_s,
        )
        ng_legacy, _, _ = run_ngspice(case, "legacy", models["legacy"], args.ngspice, args.timeout_s)
        ng_gate, _, _ = run_ngspice(case, "gate_state", models["gate_state"], args.ngspice, args.timeout_s)
        data = align_case(case, h_native, h_transistor, ng_legacy, ng_gate)
        metrics.extend(case_metrics(case, data))
        cache_rows.extend([cache_native, cache_transistor])
        legacy_images.append(
            plot_two_flow(
                case,
                data,
                "legacy",
                "ngspice legacy pybis",
                PLOTS_DIR / "01_legacy_vs_hspice_ibis",
            )
        )
        gate_images.append(
            plot_two_flow(
                case,
                data,
                "gate_state",
                "ngspice gate-state",
                PLOTS_DIR / "02_gate_state_vs_hspice_ibis",
            )
        )
        three_way_images.append(
            plot_pad_three_way(
                case,
                data,
                PLOTS_DIR / "03_ibis_gate_state_transistor_pad",
            )
        )
        write_csv(OUT_DIR / "metrics.csv", metrics)
        write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)

    contact_sheet(legacy_images, PLOTS_DIR / "01_legacy_vs_hspice_ibis_contact_sheet.png")
    contact_sheet(gate_images, PLOTS_DIR / "02_gate_state_vs_hspice_ibis_contact_sheet.png")
    contact_sheet(three_way_images, PLOTS_DIR / "03_ibis_gate_state_transistor_pad_contact_sheet.png")
    write_csv(OUT_DIR / "metrics.csv", metrics)
    write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)
    write_readme(
        fit,
        metrics,
        cache_rows,
        args.ibis,
        args.transistor_wrapper,
        args.transistor_library,
    )
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
