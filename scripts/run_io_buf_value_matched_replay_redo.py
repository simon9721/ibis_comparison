from __future__ import annotations

import argparse
import csv
import math
import os
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

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from hspice_reference_cache import cache_dir, reference_signature, restore as restore_hspice_cache, save as save_hspice_cache  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


OUT_DIR = ROOT / "results" / "io_buf_value_matched_replay_redo_2026-06-25"
COMMON_DIR = OUT_DIR / "common"
CASES_DIR = OUT_DIR / "cases"
FIGURES_DIR = OUT_DIR / "figures"
DEFAULT_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
DEFAULT_IO_BUF_SP = ROOT / "models" / "io_buf.sp"
DEFAULT_MOS_MODEL = ROOT / "models" / "hspice_ngspice.mod"
DEFAULT_NGSPICE = default_ngspice(console=True)
DEFAULT_HSPICE = default_hspice()


COLORS = {
    "input": "#222222",
    "hspice_native": "#1f77b4",
    "hspice_transistor": "#6f2dbd",
    "legacy": "#ff7f0e",
    "value_matched": "#2ca02c",
    "diag_a": "#17becf",
    "diag_b": "#d62728",
    "diag_c": "#9467bd",
    "diag_d": "#7f7f7f",
}


@dataclass(frozen=True)
class StudyCase:
    case_id: str
    description: str
    edge_ns: float
    stop_ns: float
    r_load_ohm: float
    c_load_pf: float
    high_v: float
    pattern: str
    pulse_width_ns: float = 10.0


@dataclass(frozen=True)
class Variant:
    variant_id: str
    label: str
    subcircuit_type: str
    save_diagnostics: bool = False


VARIANTS = [
    Variant("legacy", "ngspice legacy pybis", "InputDriven", False),
    Variant("value_matched", "ngspice ValueMatchedReplayHybrid", "InputDrivenValueMatchedReplayHybrid", True),
]


def build_cases() -> list[StudyCase]:
    return [
        StudyCase("edge_1ps_base_50r_2pf", "Long-pulse control, 1 ps edges, 50 ohm + 2 pF", 0.001, 25.0, 50.0, 2.0, 3.3, "rise_fall"),
        StudyCase("short_pulse_1ns_high", "1 ns high pulse before output settles, 1 ps edges, 50 ohm + 2 pF", 0.001, 13.0, 50.0, 2.0, 3.3, "short_high", 1.0),
        StudyCase("short_pulse_2ns_high", "2 ns high pulse before output settles, 1 ps edges, 50 ohm + 2 pF", 0.001, 14.0, 50.0, 2.0, 3.3, "short_high", 2.0),
    ]


def case_by_id(case_id: str) -> StudyCase:
    cases = {case.case_id: case for case in build_cases()}
    if case_id not in cases:
        raise KeyError(case_id)
    return cases[case_id]


def selected_cases(case_ids: list[str]) -> list[StudyCase]:
    if not case_ids:
        return build_cases()
    return [case_by_id(case_id) for case_id in case_ids]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


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
    log_path.write_text("COMMAND: " + " ".join(cmd) + "\n\n" + proc.stdout, encoding="utf-8", errors="replace")
    return int(proc.returncode)


def fmt_num(value: float) -> str:
    if abs(value - round(value)) < 1e-12:
        return str(int(round(value)))
    return f"{value:.12g}"


def spice_time_ns(value: float) -> str:
    return f"{fmt_num(value)}n"


def c_load_line(node: str, c_load_pf: float) -> str:
    if c_load_pf <= 0:
        return ""
    return f"Cload {node} 0 {fmt_num(c_load_pf)}p\n"


def build_pwl_points(case: StudyCase) -> list[tuple[float, float]]:
    e = case.edge_ns
    hv = case.high_v
    if case.pattern == "rise_fall":
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + e, hv),
            (15.0, hv),
            (15.0 + e, 0.0),
            (case.stop_ns, 0.0),
        ]
    if case.pattern == "short_high":
        fall_start = 5.0 + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + e, hv),
            (fall_start, hv),
            (fall_start + e, 0.0),
            (case.stop_ns, 0.0),
        ]
    raise ValueError(case.pattern)


def pwl_text(case: StudyCase) -> str:
    lines = ["Vin in_dig 0 PWL("]
    for time_ns, voltage in build_pwl_points(case):
        lines.append(f"+ {spice_time_ns(time_ns):>10} {fmt_num(voltage):>8}")
    lines[-1] = lines[-1] + " )"
    return "\n".join(lines)


def transition_windows(case: StudyCase) -> list[tuple[float, float]]:
    points = build_pwl_points(case)
    windows: list[tuple[float, float]] = []
    tail = max(3.0, case.edge_ns + 10.0 * case.r_load_ohm * case.c_load_pf * 1e-3)
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if abs(v1 - v0) > 1e-9:
            windows.append((max(0.0, t0 - 0.5), min(case.stop_ns, t1 + tail)))
    return windows


def active_mask(t_ns: np.ndarray, case: StudyCase) -> np.ndarray:
    mask = np.zeros_like(t_ns, dtype=bool)
    for x0, x1 in transition_windows(case):
        mask |= (t_ns >= x0) & (t_ns <= x1)
    return mask


def command_times(case: StudyCase) -> tuple[float, float]:
    edge = case.edge_ns
    if case.pattern == "short_high":
        return 5.0 + 0.5 * edge, 5.0 + case.pulse_width_ns + 0.5 * edge
    return 5.0 + 0.5 * edge, 15.0 + 0.5 * edge


def input_waveform(case: StudyCase, t_ns: np.ndarray) -> np.ndarray:
    points = build_pwl_points(case)
    return np.interp(t_ns, [p[0] for p in points], [p[1] for p in points])


def make_hspice_native_deck(case: StudyCase) -> str:
    return f"""* io_buf native IBIS HSPICE value-matched replay redo reference
* Sweep case: {case.case_id}
* {case.description}
.title io_buf HSPICE native IBIS Ku/Kd reference {case.case_id}
.option post=2 probe accurate
.option ingold=2
.temp 27

{pwl_text(case)}

Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig en_sig dig_q pc_ref gc_ref
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
Rload pad_ibis 0 {fmt_num(case.r_load_ohm)}
{c_load_line("pad_ibis", case.c_load_pf).rstrip()}

.probe tran V(in_dig) V(pad_ibis) V(dig_q) V(ku) V(kd)
.tran 0.001n {spice_time_ns(case.stop_ns)}
.end
"""


def make_hspice_transistor_deck(case: StudyCase) -> str:
    return f"""* io_buf transistor-level HSPICE value-matched replay redo reference
* Sweep case: {case.case_id}
* {case.description}
.title io_buf HSPICE transistor io_buf.sp pad reference {case.case_id}
.option post=2 probe accurate
.option ingold=2
.temp 27

{pwl_text(case)}

Vdd_src vdd_src 0 DC 3.3
Rvdd vdd_src vdd_ref 1
Cdec vdd_ref 0 10p
Voe_src oe_src 0 DC 3.3
Roe oe_src oe_ref 1

.include 'hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XSP in_dig oe_ref pad_sp in_sense_sp vdd_ref 0 SPICE_BUF
Rload pad_sp 0 {fmt_num(case.r_load_ohm)}
{c_load_line("pad_sp", case.c_load_pf).rstrip()}

.probe tran V(in_dig) V(pad_sp) V(in_sense_sp)
.tran 0.001n {spice_time_ns(case.stop_ns)}
.end
"""


def make_ngspice_deck(case: StudyCase, variant: Variant) -> str:
    extra = ""
    if variant.save_diagnostics:
        extra = (
            " V(xdrv.kutarget) V(xdrv.kdtarget)"
            " V(xdrv.kuleg) V(xdrv.kdleg)"
            " V(xdrv.kusamp) V(xdrv.kdsamp)"
            " V(xdrv.tf_ku) V(xdrv.tf_kd) V(xdrv.tf_start)"
            " V(xdrv.tr_ku) V(xdrv.tr_kd) V(xdrv.tr_start)"
            " V(xdrv.vmstart) V(xdrv.vmarg)"
            " V(xdrv.match_err_ku) V(xdrv.match_err_kd)"
            " V(xdrv.start_disagree) V(xdrv.match_ambiguous) V(xdrv.hvmatch)"
            " V(xdrv.kumatch) V(xdrv.kdmatch)"
        )
    return f"""* io_buf {variant.label} value-matched replay redo
* Sweep case: {case.case_id}
* {case.description}
.title io_buf ngspice {variant.label} {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{pwl_text(case)}

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 {fmt_num(case.r_load_ohm)}
{c_load_line("pad", case.c_load_pf).rstrip()}

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){extra}
.tran 0.001n {spice_time_ns(case.stop_ns)}
.end
"""


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


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"Missing signal {names}; available: {', '.join(sorted(data))}")


def optional_signal(data: dict[str, np.ndarray], t_src_ns: np.ndarray, t_dst_ns: np.ndarray, *names: str) -> np.ndarray | None:
    try:
        return interp_to(t_src_ns, find_signal(data, *names), t_dst_ns)
    except KeyError:
        return None


def to_ns(t_s: np.ndarray) -> np.ndarray:
    return np.asarray(t_s, dtype=float) * 1e9


def interp_to(t_src_ns: np.ndarray, y_src: np.ndarray, t_dst_ns: np.ndarray) -> np.ndarray:
    return np.interp(t_dst_ns, t_src_ns, y_src)


def rmse(ref: np.ndarray, dut: np.ndarray) -> float:
    if len(ref) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((dut - ref) ** 2)))


def maxabs(ref: np.ndarray, dut: np.ndarray) -> float:
    if len(ref) == 0:
        return float("nan")
    return float(np.max(np.abs(dut - ref)))


def coefficient_jump(t_ns: np.ndarray, values: np.ndarray, center_ns: float) -> float:
    mask = (t_ns >= center_ns - 0.02) & (t_ns <= center_ns + 0.02)
    if np.count_nonzero(mask) < 2:
        return 0.0
    return float(np.max(np.abs(np.diff(values[mask]))))


def finite_min(values: np.ndarray, mask: np.ndarray) -> float:
    return float(np.min(values[mask])) if np.count_nonzero(mask) else float("nan")


def finite_max(values: np.ndarray, mask: np.ndarray) -> float:
    return float(np.max(values[mask])) if np.count_nonzero(mask) else float("nan")


def time_of_extreme(t_ns: np.ndarray, values: np.ndarray, mask: np.ndarray, kind: str) -> float:
    if np.count_nonzero(mask) == 0:
        return float("nan")
    idxs = np.where(mask)[0]
    local = values[mask]
    idx = int(np.argmax(local) if kind == "max" else np.argmin(local))
    return float(t_ns[idxs[idx]])


def cache_status_for_hspice(
    family: str,
    case: StudyCase,
    deck_text: str,
    input_paths: list[Path],
    out_dir: Path,
    stem: str,
    timeout_s: int,
    hspice: Path,
    extra: dict[str, object],
) -> tuple[str, Path]:
    deck = out_dir / f"{stem}.sp"
    signature_id, signature = reference_signature(deck_text, input_paths, {"family": family, "case_id": case.case_id, **extra})
    h_cache = cache_dir(family, case.case_id, signature_id)
    if restore_hspice_cache(h_cache, out_dir, stem, deck_text):
        return "cache", deck
    if (out_dir / f"{stem}.tr0").exists():
        save_hspice_cache(h_cache, out_dir, stem, deck_text, signature)
        return "existing", deck
    write_text(deck, deck_text)
    rc = run_process([str(hspice), "-i", deck.name, "-o", stem], out_dir, out_dir / "hspice_stdout.log", timeout_s)
    if rc != 0:
        raise RuntimeError(f"HSPICE {family} {case.case_id} failed with return code {rc}; see {out_dir / 'hspice_stdout.log'}")
    save_hspice_cache(h_cache, out_dir, stem, deck_text, signature)
    return "run", deck


def run_hspice_native(case: StudyCase, ibis_path: Path, hspice: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], Path, dict[str, object]]:
    out_dir = CASES_DIR / case.case_id / "hspice_native_ibis"
    ensure_dir(out_dir)
    shutil.copy2(ibis_path, out_dir / "io_buf.ibs")
    stem = f"{case.case_id}_hspice_native_ibis"
    deck_text = make_hspice_native_deck(case)
    source, deck = cache_status_for_hspice(
        "io_buf_native_ibis",
        case,
        deck_text,
        [ibis_path],
        out_dir,
        stem,
        timeout_s,
        hspice,
        {"reference": "native_ibis"},
    )
    row = {
        "case_id": case.case_id,
        "reference": "hspice_native_ibis",
        "source": source,
        "deck": str(deck.relative_to(ROOT)),
        "tr0": str((out_dir / f"{stem}.tr0").relative_to(ROOT)),
        "lis": str((out_dir / f"{stem}.lis").relative_to(ROOT)),
    }
    return parse_hspice_tr0(out_dir / f"{stem}.tr0"), deck, row


def run_hspice_transistor(case: StudyCase, io_buf_sp: Path, mos_model: Path, hspice: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], Path, dict[str, object]]:
    out_dir = CASES_DIR / case.case_id / "hspice_transistor_sp"
    ensure_dir(out_dir)
    shutil.copy2(io_buf_sp, out_dir / "io_buf.sp")
    shutil.copy2(mos_model, out_dir / "hspice_ngspice.mod")
    stem = f"{case.case_id}_hspice_transistor_sp"
    deck_text = make_hspice_transistor_deck(case)
    source, deck = cache_status_for_hspice(
        "io_buf_transistor_sp",
        case,
        deck_text,
        [io_buf_sp, mos_model],
        out_dir,
        stem,
        timeout_s,
        hspice,
        {"reference": "transistor_sp"},
    )
    row = {
        "case_id": case.case_id,
        "reference": "hspice_transistor_sp",
        "source": source,
        "deck": str(deck.relative_to(ROOT)),
        "tr0": str((out_dir / f"{stem}.tr0").relative_to(ROOT)),
        "lis": str((out_dir / f"{stem}.lis").relative_to(ROOT)),
    }
    return parse_hspice_tr0(out_dir / f"{stem}.tr0"), deck, row


def prepare_common(ibis_path: Path) -> dict[str, Path]:
    ensure_dir(COMMON_DIR)
    common_ibis = COMMON_DIR / "io_buf.ibs"
    shutil.copy2(ibis_path, common_ibis)
    model_paths: dict[str, Path] = {}
    for variant in VARIANTS:
        out = COMMON_DIR / variant.variant_id / "driver_OutputInput_Typical.sub"
        convert_ibis_to_pybis(
            ibis_path=common_ibis,
            output_path=out,
            component_name="MCM Driver 1",
            model_name="driver",
            io_type="Output",
            subcircuit_type=variant.subcircuit_type,
            corner="Typical",
        )
        model_paths[variant.variant_id] = out
    return model_paths


def run_ngspice_variant(case: StudyCase, variant: Variant, model_path: Path, ngspice: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], Path, Path]:
    out_dir = CASES_DIR / case.case_id / f"ngspice_{variant.variant_id}"
    ensure_dir(out_dir)
    shutil.copy2(model_path, out_dir / "driver_OutputInput_Typical.sub")
    stem = f"{case.case_id}_ngspice_{variant.variant_id}"
    deck = out_dir / f"{stem}.sp"
    raw = out_dir / f"{stem}.raw"
    write_text(deck, make_ngspice_deck(case, variant))
    rc = run_process([str(ngspice), "-b", "-r", raw.name, deck.name], out_dir, out_dir / "ngspice_stdout.log", timeout_s)
    if rc != 0:
        if raw.exists():
            raw.unlink()
        raise RuntimeError(f"ngspice {variant.variant_id} {case.case_id} failed with return code {rc}; see {out_dir / 'ngspice_stdout.log'}")
    return parse_ngspice_raw(raw), deck, raw


def status_for(case: StudyCase, row: dict[str, object]) -> str:
    if row.get("flow") == "hspice_native_ibis":
        return "REFERENCE"
    if row.get("flow") == "hspice_transistor_sp":
        pad_rmse = float(row.get("pad_vs_hspice_native_rmse_v", float("nan")))
        return "PAD_REFERENCE" if np.isfinite(pad_rmse) else "CHECK"
    pad_rmse = float(row.get("pad_active_rmse_v", float("nan")))
    ku_rmse = float(row.get("ku_active_rmse", float("nan")))
    kd_rmse = float(row.get("kd_active_rmse", float("nan")))
    if not all(np.isfinite([pad_rmse, ku_rmse, kd_rmse])):
        return "FAILED"
    if case.pattern == "rise_fall":
        if pad_rmse <= 0.010 and max(ku_rmse, kd_rmse) <= 0.01:
            return "GOOD"
        if pad_rmse <= 0.025 and max(ku_rmse, kd_rmse) <= 0.03:
            return "WARN"
        return "CHECK"
    disagree = float(row.get("start_disagree_max", 0.0) or 0.0)
    ambiguous = float(row.get("match_ambiguous_max", 0.0) or 0.0) > 0.5 or disagree > 0.5
    if ambiguous:
        return "VALUE_MATCH_AMBIGUOUS"
    if pad_rmse <= 0.025 and max(ku_rmse, kd_rmse) <= 0.03:
        return "GOOD"
    return "CHECK"


def score_reference_rows(case: StudyCase, h_native: dict[str, np.ndarray], h_sp: dict[str, np.ndarray]) -> list[dict[str, object]]:
    h_t = to_ns(find_signal(h_native, "time"))
    mask = active_mask(h_t, case)
    h_pad = find_signal(h_native, "v(pad_ibis)")
    h_ku = find_signal(h_native, "v(ku)")
    h_kd = find_signal(h_native, "v(kd)")
    sp_t = to_ns(find_signal(h_sp, "time"))
    sp_pad = interp_to(sp_t, find_signal(h_sp, "v(pad_sp)"), h_t)
    rows = [
        {
            "case_id": case.case_id,
            "flow": "hspice_native_ibis",
            "flow_label": "HSPICE native IBIS",
            "status": "REFERENCE",
            "pad_peak_v": finite_max(h_pad, mask),
            "pad_min_v": finite_min(h_pad, mask),
            "pad_peak_time_ns": time_of_extreme(h_t, h_pad, mask, "max"),
            "ku_peak": finite_max(h_ku, mask),
            "ku_min": finite_min(h_ku, mask),
            "kd_min": finite_min(h_kd, mask),
            "kd_max": finite_max(h_kd, mask),
        },
        {
            "case_id": case.case_id,
            "flow": "hspice_transistor_sp",
            "flow_label": "HSPICE io_buf.sp transistor",
            "pad_vs_hspice_native_rmse_v": rmse(h_pad[mask], sp_pad[mask]),
            "pad_vs_hspice_native_max_v": maxabs(h_pad[mask], sp_pad[mask]),
            "pad_peak_v": finite_max(sp_pad, mask),
            "pad_min_v": finite_min(sp_pad, mask),
            "pad_peak_time_ns": time_of_extreme(h_t, sp_pad, mask, "max"),
        },
    ]
    rows[1]["status"] = status_for(case, rows[1])
    return rows


def score_ngspice_row(case: StudyCase, variant: Variant, h_native: dict[str, np.ndarray], n_data: dict[str, np.ndarray], deck: Path, raw: Path) -> dict[str, object]:
    h_t = to_ns(find_signal(h_native, "time"))
    n_t = to_ns(find_signal(n_data, "time"))
    mask = active_mask(h_t, case)
    _, second_edge_ns = command_times(case)
    h_pad = find_signal(h_native, "v(pad_ibis)")
    h_ku = find_signal(h_native, "v(ku)")
    h_kd = find_signal(h_native, "v(kd)")
    n_pad = interp_to(n_t, find_signal(n_data, "v(pad)"), h_t)
    n_ku = interp_to(n_t, find_signal(n_data, "v(xdrv.ku)", "v(xdrv:ku)"), h_t)
    n_kd = interp_to(n_t, find_signal(n_data, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)
    row: dict[str, object] = {
        "case_id": case.case_id,
        "flow": f"ngspice_{variant.variant_id}",
        "flow_label": variant.label,
        "ngspice_deck": str(deck.relative_to(ROOT)),
        "ngspice_raw": str(raw.relative_to(ROOT)),
        "pad_active_rmse_v": rmse(h_pad[mask], n_pad[mask]),
        "pad_active_max_v": maxabs(h_pad[mask], n_pad[mask]),
        "ku_active_rmse": rmse(h_ku[mask], n_ku[mask]),
        "ku_active_max": maxabs(h_ku[mask], n_ku[mask]),
        "kd_active_rmse": rmse(h_kd[mask], n_kd[mask]),
        "kd_active_max": maxabs(h_kd[mask], n_kd[mask]),
        "pad_peak_v": finite_max(n_pad, mask),
        "pad_min_v": finite_min(n_pad, mask),
        "pad_peak_time_ns": time_of_extreme(h_t, n_pad, mask, "max"),
        "ku_peak": finite_max(n_ku, mask),
        "ku_min": finite_min(n_ku, mask),
        "kd_min": finite_min(n_kd, mask),
        "kd_max": finite_max(n_kd, mask),
        "ku_jump_at_retrigger": coefficient_jump(h_t, n_ku, second_edge_ns),
        "kd_jump_at_retrigger": coefficient_jump(h_t, n_kd, second_edge_ns),
        "coeff_range_ok": bool(finite_min(n_ku, mask) >= -0.2 and finite_max(n_ku, mask) <= 1.2 and finite_min(n_kd, mask) >= -0.2 and finite_max(n_kd, mask) <= 1.2),
    }
    for name in [
        "kusamp",
        "kdsamp",
        "tf_ku",
        "tf_kd",
        "tf_start",
        "tr_ku",
        "tr_kd",
        "tr_start",
        "vmstart",
        "vmarg",
        "match_err_ku",
        "match_err_kd",
        "start_disagree",
        "match_ambiguous",
        "hvmatch",
        "kumatch",
        "kdmatch",
    ]:
        sig = optional_signal(n_data, n_t, h_t, f"v(xdrv.{name})", f"v(xdrv:{name})")
        if sig is None:
            continue
        row[f"{name}_min"] = finite_min(sig, mask)
        row[f"{name}_max"] = finite_max(sig, mask)
        if name in {"hvmatch", "match_ambiguous"}:
            active = mask & (sig > 0.5)
            row[f"{name}_active_count"] = int(np.count_nonzero(active))
    row["status"] = status_for(case, row)
    return row


def load_waveforms(case: StudyCase) -> dict[str, np.ndarray]:
    h = parse_hspice_tr0(CASES_DIR / case.case_id / "hspice_native_ibis" / f"{case.case_id}_hspice_native_ibis.tr0")
    sp = parse_hspice_tr0(CASES_DIR / case.case_id / "hspice_transistor_sp" / f"{case.case_id}_hspice_transistor_sp.tr0")
    t = to_ns(find_signal(h, "time"))
    data: dict[str, np.ndarray] = {
        "time_ns": t,
        "input": input_waveform(case, t),
        "hspice_native_pad": find_signal(h, "v(pad_ibis)"),
        "hspice_ku": find_signal(h, "v(ku)"),
        "hspice_kd": find_signal(h, "v(kd)"),
        "hspice_transistor_pad": interp_to(to_ns(find_signal(sp, "time")), find_signal(sp, "v(pad_sp)"), t),
    }
    for variant in VARIANTS:
        raw = CASES_DIR / case.case_id / f"ngspice_{variant.variant_id}" / f"{case.case_id}_ngspice_{variant.variant_id}.raw"
        if not raw.exists():
            continue
        n = parse_ngspice_raw(raw)
        nt = to_ns(find_signal(n, "time"))
        prefix = variant.variant_id
        data[f"{prefix}_pad"] = interp_to(nt, find_signal(n, "v(pad)"), t)
        data[f"{prefix}_ku"] = interp_to(nt, find_signal(n, "v(xdrv.ku)", "v(xdrv:ku)"), t)
        data[f"{prefix}_kd"] = interp_to(nt, find_signal(n, "v(xdrv.kd)", "v(xdrv:kd)"), t)
        for name in [
            "kusamp",
            "kdsamp",
            "tf_ku",
            "tf_kd",
            "tf_start",
            "tr_ku",
            "tr_kd",
            "tr_start",
            "vmstart",
            "vmarg",
            "match_err_ku",
            "match_err_kd",
            "start_disagree",
            "match_ambiguous",
            "hvmatch",
            "kumatch",
            "kdmatch",
        ]:
            sig = optional_signal(n, nt, t, f"v(xdrv.{name})", f"v(xdrv:{name})")
            if sig is not None:
                data[f"{prefix}_{name}"] = sig
    return data


def mark_commands(ax, case: StudyCase) -> None:
    first, second = command_times(case)
    ax.axvline(first, color="#999999", lw=1.0, alpha=0.45)
    ax.axvline(second, color="#999999", lw=1.0, alpha=0.45)


def xlim_for_case(case: StudyCase) -> tuple[float, float]:
    first, second = command_times(case)
    if case.pattern == "rise_fall":
        return max(0.0, first - 1.0), min(case.stop_ns, second + 4.0)
    return max(0.0, first - 0.75), min(case.stop_ns, second + 5.0)


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#d8dde6", alpha=0.85)


def plot_case_figures(case: StudyCase) -> None:
    data = load_waveforms(case)
    t = data["time_ns"]
    out_dir = FIGURES_DIR / case.case_id
    ensure_dir(out_dir)
    xlim = xlim_for_case(case)
    metric_lookup = {
        (row.get("case_id"), row.get("flow")): row
        for row in read_csv(OUT_DIR / "candidate_metrics.csv")
    }
    value_match_row = metric_lookup.get((case.case_id, "ngspice_value_matched"), {})

    fig, ax = plt.subplots(figsize=(10.8, 5.0), constrained_layout=True)
    ax.plot(t, data["input"] / case.high_v * max(np.nanmax(data["hspice_native_pad"]), 1.0), color=COLORS["input"], lw=1.5, alpha=0.55, label="input command (scaled)")
    ax.plot(t, data["hspice_native_pad"], color=COLORS["hspice_native"], lw=2.0, label="HSPICE native IBIS pad")
    ax.plot(t, data["hspice_transistor_pad"], color=COLORS["hspice_transistor"], lw=1.9, label="HSPICE io_buf.sp pad")
    ax.plot(t, data["legacy_pad"], color=COLORS["legacy"], lw=1.75, label="ngspice legacy pybis pad")
    if "value_matched_pad" in data:
        ax.plot(t, data["value_matched_pad"], color=COLORS["value_matched"], lw=1.75, label="ngspice value-matched pad")
    mark_commands(ax, case)
    ax.set_xlim(*xlim)
    style(ax, "Voltage (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_title(f"{case.case_id}: input and pad overlay", loc="left", fontweight="bold")
    ax.legend(loc="best", ncol=2, frameon=False)
    fig.savefig(out_dir / "01_input_pad_overlay.png", dpi=180)
    plt.close(fig)

    for coeff, ylabel, filename in [("ku", "Ku", "02_ku_overlay.png"), ("kd", "Kd", "03_kd_overlay.png")]:
        fig, ax = plt.subplots(figsize=(10.8, 4.4), constrained_layout=True)
        ax.plot(t, data[f"hspice_{coeff}"], color=COLORS["hspice_native"], lw=2.0, label=f"HSPICE native IBIS {ylabel}")
        ax.plot(t, data[f"legacy_{coeff}"], color=COLORS["legacy"], lw=1.75, label=f"legacy pybis {ylabel}")
        if f"value_matched_{coeff}" in data:
            ax.plot(t, data[f"value_matched_{coeff}"], color=COLORS["value_matched"], lw=1.75, label=f"value-matched {ylabel}")
        mark_commands(ax, case)
        ax.set_xlim(*xlim)
        ax.set_ylim(-0.15, 1.18)
        style(ax, ylabel)
        ax.set_xlabel("Time (ns)")
        ax.set_title(f"{case.case_id}: {ylabel} overlay", loc="left", fontweight="bold")
        ax.legend(loc="best", frameon=False)
        fig.savefig(out_dir / filename, dpi=180)
        plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(10.8, 8.0), sharex=True, constrained_layout=True)
    for ax in axes:
        mark_commands(ax, case)
        ax.set_xlim(*xlim)
    has_value_match_diag = "value_matched_kusamp" in data
    if has_value_match_diag:
        axes[0].plot(t, data["value_matched_kusamp"], color=COLORS["diag_a"], lw=1.6, label="KUSAMP")
        axes[0].plot(t, data["value_matched_kdsamp"], color=COLORS["diag_b"], lw=1.6, label="KDSAMP")
        axes[0].plot(t, data.get("value_matched_kumatch", np.full_like(t, np.nan)), color=COLORS["value_matched"], lw=1.2, label="KUMATCH")
        axes[0].plot(t, data.get("value_matched_kdmatch", np.full_like(t, np.nan)), color=COLORS["hspice_transistor"], lw=1.2, label="KDMATCH")
        axes[1].plot(t, data["value_matched_tf_ku"], color=COLORS["diag_a"], lw=1.5, label="TF_KU")
        axes[1].plot(t, data["value_matched_tf_kd"], color=COLORS["diag_b"], lw=1.5, label="TF_KD")
        axes[1].plot(t, data["value_matched_tf_start"], color=COLORS["value_matched"], lw=2.0, label="TF_START")
        axes[1].plot(t, data["value_matched_vmstart"], color=COLORS["diag_c"], lw=1.5, label="VMSTART")
        axes[2].plot(t, data["value_matched_match_err_ku"], color=COLORS["diag_a"], lw=1.4, label="MATCH_ERR_KU")
        axes[2].plot(t, data["value_matched_match_err_kd"], color=COLORS["diag_b"], lw=1.4, label="MATCH_ERR_KD")
        axes[2].plot(t, data["value_matched_start_disagree"], color=COLORS["diag_d"], lw=1.4, label="START_DISAGREE")
        axes[2].plot(t, data["value_matched_match_ambiguous"], color=COLORS["diag_c"], lw=1.4, label="MATCH_AMBIGUOUS")
    else:
        axes[0].plot(t, data["hspice_native_pad"], color=COLORS["hspice_native"], lw=2.0, label="HSPICE native IBIS pad")
        axes[0].plot(t, data["legacy_pad"], color=COLORS["legacy"], lw=1.6, label="legacy pybis pad")
        axes[1].plot(t, data["hspice_ku"], color=COLORS["hspice_native"], lw=1.8, label="HSPICE Ku")
        axes[1].plot(t, data["legacy_ku"], color=COLORS["legacy"], lw=1.4, label="legacy Ku")
        axes[1].plot(t, data["hspice_kd"], color=COLORS["diag_b"], lw=1.8, label="HSPICE Kd")
        axes[1].plot(t, data["legacy_kd"], color=COLORS["diag_c"], lw=1.4, label="legacy Kd")
        status = value_match_row.get("status", "unavailable")
        error = str(value_match_row.get("error", "")).strip()
        full_error = error
        if len(error) > 140:
            error = error[:137] + "..."
        if str(status).upper() == "FAILED" and "timed out" in full_error.lower():
            status_text = "value-matched diagnostics unavailable: ngspice timeout"
        elif str(status).upper() == "FAILED":
            status_text = "value-matched diagnostics unavailable: ngspice did not complete"
        else:
            status_text = f"value-matched diagnostics unavailable: {status}"
        axes[2].text(
            0.5,
            0.68,
            status_text,
            transform=axes[2].transAxes,
            ha="center",
            va="center",
            color=COLORS["diag_d"],
            fontsize=12,
            fontweight="bold",
        )
        axes[2].text(
            0.5,
            0.52,
            "No value-match diagnostics were plotted because the value-matched ngspice run did not complete.",
            transform=axes[2].transAxes,
            ha="center",
            va="center",
            color=COLORS["diag_d"],
            fontsize=12,
        )
        if error:
            axes[2].text(
                0.5,
                0.38,
                error,
                transform=axes[2].transAxes,
                ha="center",
                va="center",
                color=COLORS["diag_d"],
                fontsize=9,
                wrap=True,
            )
    if has_value_match_diag:
        style(axes[0], "Coeff")
        style(axes[1], "Table time (ns)")
        style(axes[2], "Error / flag")
    else:
        style(axes[0], "Pad voltage (V)")
        style(axes[1], "Ku / Kd")
        style(axes[2], "Failure note")
        axes[2].set_ylim(0, 1)
    axes[2].set_xlabel("Time (ns)")
    for ax in axes:
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc="best", ncol=4, frameon=False)
    fig.suptitle(f"{case.case_id}: value-match diagnostics", fontweight="bold")
    fig.savefig(out_dir / "04_value_match_diagnostics.png", dpi=180)
    plt.close(fig)


def plot_summary(rows: list[dict[str, object]]) -> None:
    lookup = {(str(row.get("case_id")), str(row.get("flow"))): row for row in rows}
    cases = build_cases()
    metrics = [
        ("pad_active_rmse_v", "Pad RMSE (mV)", 1e3),
        ("ku_active_rmse", "Ku RMSE", 1.0),
        ("kd_active_rmse", "Kd RMSE", 1.0),
        ("ku_peak", "Ku peak", 1.0),
        ("kd_min", "Kd minimum", 1.0),
    ]
    flows = [
        ("ngspice_legacy", "legacy", COLORS["legacy"]),
        ("ngspice_value_matched", "value matched", COLORS["value_matched"]),
    ]
    fig, axes = plt.subplots(len(metrics), 1, figsize=(11.8, 12.0), sharex=True, constrained_layout=True)
    x = np.arange(len(cases))
    width = 0.34
    for ax, (key, ylabel, scale) in zip(axes, metrics):
        for idx, (flow, label, color) in enumerate(flows):
            values = []
            for case in cases:
                value = lookup.get((case.case_id, flow), {}).get(key, "")
                try:
                    values.append(float(value) * scale)
                except (TypeError, ValueError):
                    values.append(np.nan)
            ax.bar(x + (idx - 0.5) * width, values, width=width, color=color, label=label)
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", color="#d8dde6")
    axes[0].legend(frameon=False)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels([case.case_id for case in cases], rotation=18, ha="right")
    axes[-1].set_xlabel("Case")
    fig.suptitle("Value-matched replay redo summary", fontweight="bold")
    ensure_dir(FIGURES_DIR)
    fig.savefig(FIGURES_DIR / "summary_bars.png", dpi=180)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]], cache_rows: list[dict[str, object]]) -> None:
    lookup = {(str(row.get("case_id")), str(row.get("flow"))): row for row in rows}

    def fnum(case_id: str, flow: str, key: str, scale: float = 1.0, fmt: str = ".4g") -> str:
        value = lookup.get((case_id, flow), {}).get(key, "")
        try:
            return format(float(value) * scale, fmt)
        except (TypeError, ValueError):
            return "n/a"

    control_legacy_rmse = lookup.get(("edge_1ps_base_50r_2pf", "ngspice_legacy"), {}).get("pad_active_rmse_v", "")
    control_vm_rmse = lookup.get(("edge_1ps_base_50r_2pf", "ngspice_value_matched"), {}).get("pad_active_rmse_v", "")
    try:
        control_delta_mv = (float(control_vm_rmse) - float(control_legacy_rmse)) * 1e3
    except (TypeError, ValueError):
        control_delta_mv = float("nan")
    ambiguous_cases = [
        row["case_id"]
        for row in rows
        if row.get("flow") == "ngspice_value_matched" and row.get("status") == "VALUE_MATCH_AMBIGUOUS"
    ]
    failed_cases = [
        row["case_id"]
        for row in rows
        if row.get("flow") == "ngspice_value_matched" and row.get("status") == "FAILED"
    ]
    lines = [
        "# io_buf Value-Matched Replay Redo",
        "",
        "This is the clean redo of the value-matched replay baseline. It compares HSPICE native IBIS, HSPICE transistor-level `io_buf.sp`, ngspice legacy pybis, and ngspice value-matched pybis.",
        "",
        "## Headline",
        "",
        f"- Required cases: `{', '.join(case.case_id for case in build_cases())}`",
        f"- Long-pulse value-matched pad RMSE delta versus legacy: `{control_delta_mv:.3f} mV`" if np.isfinite(control_delta_mv) else "- Long-pulse value-matched pad RMSE delta versus legacy: `n/a`",
        f"- Value-match ambiguous cases: `{', '.join(ambiguous_cases) if ambiguous_cases else 'none'}`",
        f"- Value-matched failed cases: `{', '.join(failed_cases) if failed_cases else 'none'}`",
        "- HSPICE transistor-level `io_buf.sp` is pad-only; `Ku/Kd` validation uses HSPICE native IBIS.",
        "",
        "## Findings",
        "",
        "- Long-pulse control is preserved. Value-matched replay stays close to legacy and HSPICE native IBIS, with only a small pad RMSE increase on the control case.",
        "- `short_pulse_1ns_high` shows the useful part of value matching: pad RMSE drops from legacy's large full-pulse error to a small partial-pulse error, and `Ku` peak moves much closer to HSPICE native IBIS.",
        "- The same `short_pulse_1ns_high` case also shows the core limitation: `Kd` is wrong. The value-matched replay keeps `Kd` too high, so this is not coefficient-correct even though the pad waveform looks much better.",
        "- `short_pulse_2ns_high` is not simulation-ready for this method. The value-matched ngspice run times out, so the method fails the numerical robustness gate for this redo.",
        "- The `short_pulse_2ns_high` timeout was investigated separately. It is not zero-progress: shorter stop-time runs complete through `7.25 ns`, but timestep collapse after the reverse edge prevents the full run from finishing with the default `coeff_tau=1p`.",
        "- The transistor-level `io_buf.sp` reference is useful as a pad-level sanity reference, but it is not expected to match native IBIS exactly because it is a different model abstraction and has no exposed `Ku/Kd`.",
        "",
        "## Short-Pulse 1 ns Detail",
        "",
        f"- HSPICE native IBIS pad peak: `{fnum('short_pulse_1ns_high', 'hspice_native_ibis', 'pad_peak_v', 1.0, '.4f')} V`; transistor `io_buf.sp` pad peak: `{fnum('short_pulse_1ns_high', 'hspice_transistor_sp', 'pad_peak_v', 1.0, '.4f')} V`.",
        f"- Legacy pybis pad peak: `{fnum('short_pulse_1ns_high', 'ngspice_legacy', 'pad_peak_v', 1.0, '.4f')} V`; value-matched pad peak: `{fnum('short_pulse_1ns_high', 'ngspice_value_matched', 'pad_peak_v', 1.0, '.4f')} V`.",
        f"- HSPICE native IBIS `Ku` peak: `{fnum('short_pulse_1ns_high', 'hspice_native_ibis', 'ku_peak', 1.0, '.4f')}`; legacy pybis `Ku` peak: `{fnum('short_pulse_1ns_high', 'ngspice_legacy', 'ku_peak', 1.0, '.4f')}`; value-matched `Ku` peak: `{fnum('short_pulse_1ns_high', 'ngspice_value_matched', 'ku_peak', 1.0, '.4f')}`.",
        f"- HSPICE native IBIS `Kd` minimum: `{fnum('short_pulse_1ns_high', 'hspice_native_ibis', 'kd_min', 1.0, '.4f')}`; legacy pybis `Kd` minimum: `{fnum('short_pulse_1ns_high', 'ngspice_legacy', 'kd_min', 1.0, '.4f')}`; value-matched `Kd` minimum: `{fnum('short_pulse_1ns_high', 'ngspice_value_matched', 'kd_min', 1.0, '.4f')}`.",
        f"- Value-matched inferred falling-table start disagreement reaches `{fnum('short_pulse_1ns_high', 'ngspice_value_matched', 'start_disagree_max', 1.0, '.3f')} ns`, so the case is classified as `VALUE_MATCH_AMBIGUOUS`.",
        "",
        "## Key Files",
        "",
        "- `candidate_metrics.csv`: per-flow metrics.",
        "- `reference_cache_manifest.csv`: HSPICE cache/run source.",
        "- `figures/<case>/01_input_pad_overlay.png`",
        "- `figures/<case>/02_ku_overlay.png`",
        "- `figures/<case>/03_kd_overlay.png`",
        "- `figures/<case>/04_value_match_diagnostics.png`",
        "- `figures/summary_bars.png`",
        "- `timeout_investigation/README.md`: root-cause analysis for the 2 ns value-matched timeout.",
        "",
        "## Case Summary",
        "",
        "| Case | Flow | Status | Pad RMSE mV | Ku RMSE | Kd RMSE | Pad peak V | Ku peak | Kd min |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in build_cases():
        for flow in ["hspice_native_ibis", "hspice_transistor_sp", "ngspice_legacy", "ngspice_value_matched"]:
            row = lookup.get((case.case_id, flow), {})
            lines.append(
                "| {case} | {flow} | {status} | {pad_rmse} | {ku_rmse} | {kd_rmse} | {pad_peak} | {ku_peak} | {kd_min} |".format(
                    case=case.case_id,
                    flow=flow,
                    status=row.get("status", ""),
                    pad_rmse=fnum(case.case_id, flow, "pad_active_rmse_v", 1e3, ".3f") if flow.startswith("ngspice") else fnum(case.case_id, flow, "pad_vs_hspice_native_rmse_v", 1e3, ".3f"),
                    ku_rmse=fnum(case.case_id, flow, "ku_active_rmse", 1.0, ".5f"),
                    kd_rmse=fnum(case.case_id, flow, "kd_active_rmse", 1.0, ".5f"),
                    pad_peak=fnum(case.case_id, flow, "pad_peak_v", 1.0, ".4f"),
                    ku_peak=fnum(case.case_id, flow, "ku_peak", 1.0, ".4f"),
                    kd_min=fnum(case.case_id, flow, "kd_min", 1.0, ".4f"),
                )
            )
    lines.extend(
        [
            "",
            "## HSPICE Reference Cache",
            "",
            "| Case | Reference | Source |",
            "|---|---|---:|",
        ]
    )
    for row in cache_rows:
        lines.append(f"| {row.get('case_id', '')} | {row.get('reference', '')} | {row.get('source', '')} |")
    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "Pad-only improvement is not enough. The value-matched method must improve `Ku` and `Kd` agreement with HSPICE native IBIS, and cases with large `TF_KU`/`TF_KD` disagreement are classified as `VALUE_MATCH_AMBIGUOUS`.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def run_case(case: StudyCase, args: argparse.Namespace, model_paths: dict[str, Path]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    h_native, _, native_cache = run_hspice_native(case, args.ibis, args.hspice, args.timeout_s)
    h_sp, _, sp_cache = run_hspice_transistor(case, args.io_buf_sp, args.mos_model, args.hspice, args.timeout_s)
    rows = score_reference_rows(case, h_native, h_sp)
    for variant in VARIANTS:
        try:
            n_data, deck, raw = run_ngspice_variant(case, variant, model_paths[variant.variant_id], args.ngspice, args.timeout_s)
            rows.append(score_ngspice_row(case, variant, h_native, n_data, deck, raw))
        except Exception as exc:
            rows.append(
                {
                    "case_id": case.case_id,
                    "flow": f"ngspice_{variant.variant_id}",
                    "flow_label": variant.label,
                    "status": "FAILED",
                    "error": str(exc),
                }
            )
    return rows, [native_cache, sp_cache]


def verify_generated_models(model_paths: dict[str, Path]) -> None:
    text = model_paths["value_matched"].read_text(encoding="utf-8", errors="replace")
    required = ["KUSAMP", "KDSAMP", "TF_START", "VMSTART", "MATCH_ERR_KU", "MATCH_ERR_KD"]
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(f"Generated value-matched model is missing diagnostics: {', '.join(missing)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean io_buf short-pulse value-matched replay redo.")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--hspice", type=Path, default=DEFAULT_HSPICE)
    parser.add_argument("--ibis", type=Path, default=DEFAULT_IBIS)
    parser.add_argument("--io-buf-sp", type=Path, default=DEFAULT_IO_BUF_SP)
    parser.add_argument("--mos-model", type=Path, default=DEFAULT_MOS_MODEL)
    parser.add_argument("--case", action="append", default=[], help="Run only this case id. May be repeated.")
    parser.add_argument("--resume", action="store_true", help="Skip cases already present for all four flows.")
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=240)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in [OUT_DIR, COMMON_DIR, CASES_DIR, FIGURES_DIR]:
        ensure_dir(path)
    if args.summarize_only:
        rows = [dict(row) for row in read_csv(OUT_DIR / "candidate_metrics.csv")]
        cache_rows = [dict(row) for row in read_csv(OUT_DIR / "reference_cache_manifest.csv")]
        for case in selected_cases(args.case):
            plot_case_figures(case)
        plot_summary(rows)
        write_readme(rows, cache_rows)
        print(f"OUT_DIR={OUT_DIR}")
        return 0

    model_paths = prepare_common(args.ibis)
    verify_generated_models(model_paths)
    existing_rows = [dict(row) for row in read_csv(OUT_DIR / "candidate_metrics.csv")] if args.resume else []
    existing_cache = [dict(row) for row in read_csv(OUT_DIR / "reference_cache_manifest.csv")] if args.resume else []
    done = {(row.get("case_id"), row.get("flow")) for row in existing_rows}
    all_rows = list(existing_rows)
    cache_rows = list(existing_cache)
    expected_flows = {"hspice_native_ibis", "hspice_transistor_sp", "ngspice_legacy", "ngspice_value_matched"}
    cases = selected_cases(args.case)
    for idx, case in enumerate(cases, start=1):
        if args.resume and {flow for cid, flow in done if cid == case.case_id} >= expected_flows:
            print(f"[{idx}/{len(cases)}] {case.case_id} (resume skip)", flush=True)
            continue
        print(f"[{idx}/{len(cases)}] {case.case_id}", flush=True)
        all_rows = [row for row in all_rows if row.get("case_id") != case.case_id]
        cache_rows = [row for row in cache_rows if row.get("case_id") != case.case_id]
        rows, refs = run_case(case, args, model_paths)
        all_rows.extend(rows)
        cache_rows.extend(refs)
        write_csv(OUT_DIR / "candidate_metrics.csv", all_rows)
        write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)
        plot_case_figures(case)
    order = {case.case_id: i for i, case in enumerate(build_cases())}
    flow_order = {flow: i for i, flow in enumerate(["hspice_native_ibis", "hspice_transistor_sp", "ngspice_legacy", "ngspice_value_matched"])}
    all_rows.sort(key=lambda row: (order.get(str(row.get("case_id")), 999), flow_order.get(str(row.get("flow")), 999)))
    cache_rows.sort(key=lambda row: (order.get(str(row.get("case_id")), 999), str(row.get("reference", ""))))
    write_csv(OUT_DIR / "candidate_metrics.csv", all_rows)
    write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)
    plot_summary(all_rows)
    write_readme(all_rows, cache_rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
