import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from hspice_reference_cache import cache_dir, reference_signature, restore as restore_hspice_cache, save as save_hspice_cache  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402
from run_io_buf_coeff_state_retrigger import (  # noqa: E402
    c_load_line,
    ensure_dir,
    find_signal,
    fmt_num,
    interp_to,
    maxabs,
    read_csv,
    rmse,
    run_process,
    spice_time_ns,
    status_for,
    to_ns,
    write_csv,
    write_text,
)


OUT_DIR = ROOT / "results" / "io_buf_directional_gate_state_retrigger_2026-06-22"
COMMON_DIR = OUT_DIR / "common"
CASES_DIR = OUT_DIR / "cases"
DEMO_DIR = OUT_DIR / "interrupted_switching_demo"
FIGURES_DIR = DEMO_DIR / "figures"
DEFAULT_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
DEFAULT_NGSPICE = default_ngspice(console=True)
DEFAULT_HSPICE = default_hspice()

REQUIRED_CASE_IDS = [
    "edge_1ps_base_50r_2pf",
    "short_pulse_500ps_high",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
    "short_pulse_500ps_low",
    "short_pulse_1ns_low",
    "short_pulse_2ns_low",
]
CONTROL_CASE = "edge_1ps_base_50r_2pf"
DEMO_CASE = "short_pulse_1ns_high"

COLORS = {
    "hspice": "#1f77b4",
    "legacy": "#ff7f0e",
    "short_hybrid": "#9467bd",
    "gate_hybrid": "#d62728",
    "dir_hybrid": "#2ca02c",
    "dir_full": "#8c564b",
    "input": "#222222",
    "target": "#7f7f7f",
    "state": "#17becf",
    "align": "#bcbd22",
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
    include_main_plots: bool = True


VARIANTS = [
    Variant("legacy", "legacy pybis", "InputDriven"),
    Variant("short_hybrid", "ShortPulseHybrid", "InputDrivenShortPulseHybrid", save_diagnostics=True),
    Variant("gate_hybrid", "GateStateHybrid", "InputDrivenGateStateHybrid", save_diagnostics=True),
    Variant(
        "dir_hybrid",
        "DirectionalGateStateHybrid",
        "InputDrivenDirectionalGateStateHybrid",
        save_diagnostics=True,
    ),
    Variant(
        "dir_full",
        "DirectionalGateStateFull diagnostic",
        "InputDrivenDirectionalGateStateFull",
        save_diagnostics=True,
        include_main_plots=False,
    ),
]


def build_cases() -> list[StudyCase]:
    return [
        StudyCase("edge_1ps_base_50r_2pf", "Baseline 1 ps rise/fall, 50 ohm + 2 pF", 0.001, 25.0, 50.0, 2.0, 3.3, "rise_fall"),
        StudyCase("short_pulse_500ps_high", "500 ps high pulse with 1 ps edges, 50 ohm + 2 pF", 0.001, 12.5, 50.0, 2.0, 3.3, "short_high", 0.5),
        StudyCase("short_pulse_1ns_high", "1 ns high pulse with 1 ps edges, 50 ohm + 2 pF", 0.001, 13.0, 50.0, 2.0, 3.3, "short_high", 1.0),
        StudyCase("short_pulse_2ns_high", "2 ns high pulse with 1 ps edges, 50 ohm + 2 pF", 0.001, 14.0, 50.0, 2.0, 3.3, "short_high", 2.0),
        StudyCase("short_pulse_500ps_low", "500 ps low pulse after settled high, 50 ohm + 2 pF", 0.001, 16.0, 50.0, 2.0, 3.3, "short_low", 0.5),
        StudyCase("short_pulse_1ns_low", "1 ns low pulse after settled high, 50 ohm + 2 pF", 0.001, 16.5, 50.0, 2.0, 3.3, "short_low", 1.0),
        StudyCase("short_pulse_2ns_low", "2 ns low pulse after settled high, 50 ohm + 2 pF", 0.001, 17.5, 50.0, 2.0, 3.3, "short_low", 2.0),
    ]


def case_by_id(case_id: str) -> StudyCase:
    return {case.case_id: case for case in build_cases()}[case_id]


def selected_cases(case_ids: list[str]) -> list[StudyCase]:
    available = {case.case_id: case for case in build_cases()}
    ids = case_ids or REQUIRED_CASE_IDS
    missing = [case_id for case_id in ids if case_id not in available]
    if missing:
        raise SystemExit(f"Unknown case(s): {', '.join(missing)}")
    return [available[case_id] for case_id in ids]


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
    if case.pattern == "short_low":
        fall_start = 8.0
        rise_start = 8.0 + case.pulse_width_ns
        return [
            (0.0, 0.0),
            (3.0, 0.0),
            (3.0 + e, hv),
            (fall_start, hv),
            (fall_start + e, 0.0),
            (rise_start, 0.0),
            (rise_start + e, hv),
            (case.stop_ns, hv),
        ]
    raise ValueError(f"Unknown pattern: {case.pattern}")


def transition_windows(case: StudyCase) -> list[tuple[float, float]]:
    points = build_pwl_points(case)
    windows: list[tuple[float, float]] = []
    tail = max(3.0, case.edge_ns + 10.0 * case.r_load_ohm * case.c_load_pf * 1e-3)
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if abs(v1 - v0) <= 1e-9:
            continue
        if case.pattern == "short_low" and t0 < 7.5:
            continue
        windows.append((max(0.0, t0 - 0.5), min(case.stop_ns, t1 + tail)))
    return windows


def active_mask(t_ns: np.ndarray, case: StudyCase) -> np.ndarray:
    mask = np.zeros_like(t_ns, dtype=bool)
    for x0, x1 in transition_windows(case):
        mask |= (t_ns >= x0) & (t_ns <= x1)
    return mask


def pwl_text(case: StudyCase) -> str:
    lines = ["Vin in_dig 0 PWL("]
    for time_ns, voltage in build_pwl_points(case):
        lines.append(f"+ {spice_time_ns(time_ns):>10} {fmt_num(voltage):>8}")
    lines[-1] = lines[-1] + " )"
    return "\n".join(lines)


def make_hspice_deck(case: StudyCase) -> str:
    return f"""* io_buf native IBIS HSPICE directional Ku/Kd extraction
* Sweep case: {case.case_id}
* {case.description}
.title io_buf HSPICE native IBIS Ku/Kd extraction {case.case_id}
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


def make_ngspice_deck(case: StudyCase, variant: Variant) -> str:
    extra = ""
    if variant.save_diagnostics:
        extra = (
            " V(xdrv.kutarget) V(xdrv.kdtarget)"
            " V(xdrv.kuleg) V(xdrv.kdleg)"
            " V(xdrv.hinterrupt) V(xdrv.hshort)"
            " V(xdrv.highage) V(xdrv.lowage)"
            " V(xdrv.koverlap)"
            " V(xdrv.gup) V(xdrv.gdn) V(xdrv.kugate) V(xdrv.kdgate)"
            " V(xdrv.ku_on) V(xdrv.ku_off) V(xdrv.kd_off) V(xdrv.kd_on)"
            " V(xdrv.kudir) V(xdrv.kddir)"
            " V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)"
            " V(xdrv.hdiractive) V(xdrv.halign) V(xdrv.haligned)"
        )
    return f"""* io_buf {variant.label}/ngspice directional Ku/Kd extraction
* Sweep case: {case.case_id}
* {case.description}
.title io_buf ngspice {variant.label} Ku/Kd extraction {case.case_id}
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


def command_times(case: StudyCase) -> tuple[float, float]:
    edge = case.edge_ns
    if case.pattern == "short_high":
        return 5.0 + 0.5 * edge, 5.0 + case.pulse_width_ns + 0.5 * edge
    if case.pattern == "short_low":
        return 8.0 + 0.5 * edge, 8.0 + case.pulse_width_ns + 0.5 * edge
    return 5.0 + 0.5 * edge, 15.0 + 0.5 * edge


def input_waveform(case: StudyCase, t_ns: np.ndarray) -> np.ndarray:
    points = build_pwl_points(case)
    return np.interp(t_ns, [p[0] for p in points], [p[1] for p in points])


def prepare_common(ibis_path: Path) -> dict[str, Path]:
    ensure_dir(COMMON_DIR)
    common_ibis = COMMON_DIR / "io_buf.ibs"
    shutil.copy2(ibis_path, common_ibis)
    paths: dict[str, Path] = {}
    for variant in VARIANTS:
        output_path = COMMON_DIR / variant.variant_id / "driver_OutputInput_Typical.sub"
        convert_ibis_to_pybis(
            ibis_path=common_ibis,
            output_path=output_path,
            component_name="MCM Driver 1",
            model_name="driver",
            io_type="Output",
            subcircuit_type=variant.subcircuit_type,
            corner="Typical",
        )
        paths[variant.variant_id] = output_path
    return paths


def run_hspice_case(case: StudyCase, ibis_path: Path, timeout_s: int) -> tuple[dict[str, np.ndarray], Path]:
    h_dir = CASES_DIR / case.case_id / "hspice_native_ibis"
    ensure_dir(h_dir)
    stem = f"{case.case_id}_hspice_native_ibis"
    deck = h_dir / f"{stem}.sp"
    deck_text = make_hspice_deck(case)
    signature_id, signature = reference_signature(
        deck_text,
        [ibis_path],
        {"family": "io_buf_native_ibis", "case_id": case.case_id},
    )
    h_cache = cache_dir("io_buf_native_ibis", case.case_id, signature_id)
    if restore_hspice_cache(h_cache, h_dir, stem, deck_text):
        return parse_hspice_tr0(h_dir / f"{stem}.tr0"), deck
    if (h_dir / f"{stem}.tr0").exists():
        save_hspice_cache(h_cache, h_dir, stem, deck_text, signature)
        return parse_hspice_tr0(h_dir / f"{stem}.tr0"), deck

    shutil.copy2(ibis_path, h_dir / "io_buf.ibs")
    write_text(deck, deck_text)
    rc = run_process([str(DEFAULT_HSPICE), "-i", deck.name, "-o", stem], h_dir, h_dir / "hspice_stdout.log", timeout_s=timeout_s)
    if rc != 0:
        raise RuntimeError(f"HSPICE return code {rc}")
    save_hspice_cache(h_cache, h_dir, stem, deck_text, signature)
    return parse_hspice_tr0(h_dir / f"{stem}.tr0"), deck


def run_ngspice_variant(
    case: StudyCase,
    variant: Variant,
    model_path: Path,
    ngspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], Path, Path]:
    n_dir = CASES_DIR / case.case_id / f"ngspice_{variant.variant_id}"
    ensure_dir(n_dir)
    shutil.copy2(model_path, n_dir / "driver_OutputInput_Typical.sub")
    stem = f"{case.case_id}_ngspice_{variant.variant_id}"
    deck = n_dir / f"{stem}.sp"
    raw = n_dir / f"{stem}.raw"
    write_text(deck, make_ngspice_deck(case, variant))
    rc = run_process([str(ngspice), "-b", "-r", raw.name, deck.name], n_dir, n_dir / "ngspice_stdout.log", timeout_s=timeout_s)
    if rc != 0:
        raise RuntimeError(f"ngspice {variant.variant_id} return code {rc}")
    return parse_ngspice_raw(raw), deck, raw


def coefficient_jump(t_ns: np.ndarray, values: np.ndarray, center_ns: float) -> float:
    mask = (t_ns >= center_ns - 0.02) & (t_ns <= center_ns + 0.02)
    if np.count_nonzero(mask) < 2:
        return 0.0
    return float(np.max(np.abs(np.diff(values[mask]))))


def overlap_energy(t_ns: np.ndarray, ku: np.ndarray, kd: np.ndarray, mask: np.ndarray) -> float:
    if np.count_nonzero(mask) < 2:
        return 0.0
    return float(np.trapezoid(np.maximum(ku[mask], 0.0) * np.maximum(kd[mask], 0.0), t_ns[mask]))


def recovery_cross_ns(case: StudyCase, t_ns: np.ndarray, kd: np.ndarray) -> float:
    _, second = command_times(case)
    mask = t_ns >= second
    if np.count_nonzero(mask) == 0:
        return float("nan")
    tt = t_ns[mask]
    yy = kd[mask]
    if case.pattern == "short_high":
        hit = np.where(yy >= 0.9)[0]
    elif case.pattern == "short_low":
        hit = np.where(yy <= 0.1)[0]
    else:
        return float("nan")
    if len(hit) == 0:
        return float("nan")
    return float(tt[int(hit[0])] - second)


def optional_signal(data: dict[str, np.ndarray], t_src_ns: np.ndarray, t_dst_ns: np.ndarray, *names: str) -> np.ndarray | None:
    try:
        return interp_to(t_src_ns, find_signal(data, *names), t_dst_ns)
    except KeyError:
        return None


def score_variant(
    case: StudyCase,
    variant: Variant,
    h_data: dict[str, np.ndarray],
    n_data: dict[str, np.ndarray],
    hspice_deck: Path,
    ngspice_deck: Path,
    raw_path: Path,
) -> dict[str, object]:
    h_t = to_ns(find_signal(h_data, "time"))
    n_t = to_ns(find_signal(n_data, "time"))
    mask = active_mask(h_t, case)
    _, second_edge_ns = command_times(case)

    h_pad = find_signal(h_data, "v(pad_ibis)")
    h_ku = find_signal(h_data, "v(ku)")
    h_kd = find_signal(h_data, "v(kd)")
    n_pad = interp_to(n_t, find_signal(n_data, "v(pad)"), h_t)
    n_ku = interp_to(n_t, find_signal(n_data, "v(xdrv.ku)", "v(xdrv:ku)"), h_t)
    n_kd = interp_to(n_t, find_signal(n_data, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)

    pad_rmse = rmse(h_pad[mask], n_pad[mask])
    ku_rmse = rmse(h_ku[mask], n_ku[mask])
    kd_rmse = rmse(h_kd[mask], n_kd[mask])
    h_kd_recovery = recovery_cross_ns(case, h_t, h_kd)
    n_kd_recovery = recovery_cross_ns(case, h_t, n_kd)
    row: dict[str, object] = {
        "case_id": case.case_id,
        "description": case.description,
        "pattern": case.pattern,
        "pulse_width_ns": case.pulse_width_ns if case.pattern.startswith("short_") else "",
        "variant": variant.variant_id,
        "variant_label": variant.label,
        "edge_ns": case.edge_ns,
        "r_load_ohm": case.r_load_ohm,
        "c_load_pf": case.c_load_pf,
        "hspice_deck": str(hspice_deck.relative_to(ROOT)),
        "ngspice_deck": str(ngspice_deck.relative_to(ROOT)),
        "ngspice_raw": str(raw_path.relative_to(ROOT)),
        "pad_active_rmse_v": pad_rmse,
        "pad_active_max_v": maxabs(h_pad[mask], n_pad[mask]),
        "ku_active_rmse": ku_rmse,
        "ku_active_max": maxabs(h_ku[mask], n_ku[mask]),
        "kd_active_rmse": kd_rmse,
        "kd_active_max": maxabs(h_kd[mask], n_kd[mask]),
        "hspice_ku_peak": float(np.max(h_ku[mask])),
        "ku_peak": float(np.max(n_ku[mask])),
        "hspice_kd_min": float(np.min(h_kd[mask])),
        "kd_min": float(np.min(n_kd[mask])),
        "ku_min": float(np.min(n_ku[mask])),
        "kd_max": float(np.max(n_kd[mask])),
        "coeff_range_ok": bool(
            np.min(n_ku[mask]) >= -0.2
            and np.max(n_ku[mask]) <= 1.2
            and np.min(n_kd[mask]) >= -0.2
            and np.max(n_kd[mask]) <= 1.2
        ),
        "ku_jump_at_retrigger": coefficient_jump(h_t, n_ku, second_edge_ns),
        "kd_jump_at_retrigger": coefficient_jump(h_t, n_kd, second_edge_ns),
        "overlap_energy_ns": overlap_energy(h_t, n_ku, n_kd, mask),
        "hspice_kd_recovery_ns": h_kd_recovery,
        "kd_recovery_ns": n_kd_recovery,
        "kd_recovery_delta_ns": n_kd_recovery - h_kd_recovery if np.isfinite(h_kd_recovery) and np.isfinite(n_kd_recovery) else "",
        "status": status_for(pad_rmse, ku_rmse, kd_rmse),
    }
    for name in [
        "kutarget",
        "kdtarget",
        "kuleg",
        "kdleg",
        "hinterrupt",
        "hshort",
        "highage",
        "lowage",
        "gup",
        "gdn",
        "kugate",
        "kdgate",
        "ku_on",
        "ku_off",
        "kd_off",
        "kd_on",
        "kudir",
        "kddir",
        "hfall_after_rise",
        "hrise_after_fall",
        "hdiractive",
        "halign",
        "haligned",
        "koverlap",
    ]:
        sig = optional_signal(n_data, n_t, h_t, f"v(xdrv.{name})", f"v(xdrv:{name})")
        if sig is None:
            row[f"{name}_min"] = ""
            row[f"{name}_max"] = ""
        else:
            row[f"{name}_min"] = float(np.min(sig[mask]))
            row[f"{name}_max"] = float(np.max(sig[mask]))
    return row


def run_case(case: StudyCase, ngspice: Path, ibis_path: Path, model_paths: dict[str, Path], timeout_s: int) -> list[dict[str, object]]:
    h_data, h_deck = run_hspice_case(case, ibis_path, timeout_s)
    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        try:
            n_data, n_deck, raw = run_ngspice_variant(case, variant, model_paths[variant.variant_id], ngspice, timeout_s)
            rows.append(score_variant(case, variant, h_data, n_data, h_deck, n_deck, raw))
        except Exception as exc:
            rows.append(
                {
                    "case_id": case.case_id,
                    "description": case.description,
                    "pattern": case.pattern,
                    "pulse_width_ns": case.pulse_width_ns if case.pattern.startswith("short_") else "",
                    "variant": variant.variant_id,
                    "variant_label": variant.label,
                    "status": "failed",
                    "error": str(exc),
                    "hspice_deck": str(h_deck.relative_to(ROOT)),
                }
            )
    return rows


def write_wide_metrics(rows: list[dict[str, object]]) -> None:
    by_case: dict[str, dict[str, object]] = {}
    for row in rows:
        case_id = str(row["case_id"])
        variant = str(row["variant"])
        out = by_case.setdefault(
            case_id,
            {
                "case_id": case_id,
                "description": row.get("description", ""),
                "pattern": row.get("pattern", ""),
                "pulse_width_ns": row.get("pulse_width_ns", ""),
            },
        )
        for key in [
            "pad_active_rmse_v",
            "ku_active_rmse",
            "kd_active_rmse",
            "ku_peak",
            "kd_min",
            "kd_recovery_delta_ns",
            "overlap_energy_ns",
            "coeff_range_ok",
            "status",
        ]:
            out[f"{variant}_{key}"] = row.get(key, "")
    ordered = [by_case[case_id] for case_id in REQUIRED_CASE_IDS if case_id in by_case]
    write_csv(OUT_DIR / "metrics_by_case.csv", ordered)


def read_waveforms(case_id: str) -> dict[str, np.ndarray]:
    case_dir = CASES_DIR / case_id
    h_path = case_dir / "hspice_native_ibis" / f"{case_id}_hspice_native_ibis.tr0"
    h = parse_hspice_tr0(h_path)
    t = to_ns(find_signal(h, "time"))
    out = {
        "time_ns": t,
        "hspice_pad": find_signal(h, "v(pad_ibis)"),
        "hspice_ku": find_signal(h, "v(ku)"),
        "hspice_kd": find_signal(h, "v(kd)"),
    }
    for variant in VARIANTS:
        path = case_dir / f"ngspice_{variant.variant_id}" / f"{case_id}_ngspice_{variant.variant_id}.raw"
        if not path.exists():
            continue
        data = parse_ngspice_raw(path)
        nt = to_ns(find_signal(data, "time"))
        out[f"{variant.variant_id}_pad"] = interp_to(nt, find_signal(data, "v(pad)"), t)
        out[f"{variant.variant_id}_ku"] = interp_to(nt, find_signal(data, "v(xdrv.ku)", "v(xdrv:ku)"), t)
        out[f"{variant.variant_id}_kd"] = interp_to(nt, find_signal(data, "v(xdrv.kd)", "v(xdrv:kd)"), t)
        for name in [
            "kutarget",
            "kdtarget",
            "kuleg",
            "kdleg",
            "highage",
            "lowage",
            "ku_on",
            "ku_off",
            "kd_off",
            "kd_on",
            "kudir",
            "kddir",
            "hfall_after_rise",
            "hrise_after_fall",
            "hdiractive",
            "halign",
            "haligned",
            "koverlap",
        ]:
            sig = optional_signal(data, nt, t, f"v(xdrv.{name})", f"v(xdrv:{name})")
            if sig is not None:
                out[f"{variant.variant_id}_{name}"] = sig
    return out


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def mark_commands(ax, case: StudyCase) -> None:
    first_ns, second_ns = command_times(case)
    ax.axvline(first_ns, color="0.25", lw=1.0, ls=":", alpha=0.85)
    ax.axvline(second_ns, color="0.25", lw=1.0, ls=":", alpha=0.85)
    ax.axvspan(first_ns, second_ns, color="#f2c94c", alpha=0.12, lw=0)


def plot_main_case(case_id: str) -> None:
    ensure_dir(FIGURES_DIR)
    case = case_by_id(case_id)
    data = read_waveforms(case_id)
    t = data["time_ns"]
    x0, x1 = command_times(case)
    xlim = (x0 - 0.75, min(case.stop_ns, x1 + 5.0))
    flows = [
        ("hspice", "HSPICE native IBIS"),
        ("legacy", "legacy pybis"),
        ("short_hybrid", "ShortPulseHybrid"),
        ("gate_hybrid", "GateStateHybrid"),
        ("dir_hybrid", "DirectionalGateStateHybrid"),
    ]

    fig, axes = plt.subplots(2, 1, figsize=(11.2, 6.7), sharex=True, height_ratios=[0.72, 1.35])
    for ax in axes:
        mark_commands(ax, case)
    axes[0].plot(t, input_waveform(case, t), color=COLORS["input"], lw=2.2, label="input command")
    style(axes[0], "Input (V)")
    axes[0].legend(loc="upper right")
    for key, label in flows:
        axes[1].plot(t, data[f"{key}_pad"], color=COLORS[key], lw=2.0, label=label)
    style(axes[1], "Pad (V)")
    axes[1].set_xlabel("Time (ns)")
    axes[1].legend(loc="best", ncol=2)
    axes[1].set_xlim(*xlim)
    fig.suptitle(f"{case_id}: input and pad overlay")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / f"{case_id}_01_input_pad_overlay.png", dpi=180)
    plt.close(fig)

    for coeff in ["ku", "kd"]:
        fig, ax = plt.subplots(figsize=(11.2, 4.3))
        mark_commands(ax, case)
        for key, label in flows:
            ax.plot(t, data[f"{key}_{coeff}"], color=COLORS[key], lw=2.0, label=f"{label} {coeff.upper()}")
        ax.set_ylim(-0.12, 1.16)
        ax.set_xlim(*xlim)
        style(ax, coeff.upper())
        ax.set_xlabel("Time (ns)")
        ax.legend(loc="best", ncol=2)
        fig.suptitle(f"{case_id}: {coeff.upper()} only")
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        fig.savefig(FIGURES_DIR / f"{case_id}_02_{coeff}_only.png", dpi=180)
        plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(11.2, 6.8), sharex=True)
    for ax in axes:
        mark_commands(ax, case)
    axes[0].plot(t, data["dir_hybrid_ku_on"], color="#2ca02c", lw=1.9, label="KU_ON")
    axes[0].plot(t, data["dir_hybrid_ku_off"], color="#98df8a", lw=1.9, label="KU_OFF")
    axes[0].plot(t, data["dir_hybrid_kd_off"], color="#1f77b4", lw=1.9, label="KD_OFF")
    axes[0].plot(t, data["dir_hybrid_kd_on"], color="#aec7e8", lw=1.9, label="KD_ON")
    style(axes[0], "Directional states")
    axes[0].legend(loc="best", ncol=4)
    axes[1].plot(t, data["dir_hybrid_kudir"], color=COLORS["dir_hybrid"], lw=2.0, label="KUDIR")
    axes[1].plot(t, data["dir_hybrid_kddir"], color=COLORS["state"], lw=2.0, label="KDDIR")
    axes[1].plot(t, data["dir_hybrid_kuleg"], color=COLORS["legacy"], lw=1.5, label="KULEG")
    axes[1].plot(t, data["dir_hybrid_kdleg"], color="#ffbb78", lw=1.5, label="KDLEG")
    axes[1].set_ylim(-0.12, 1.16)
    style(axes[1], "Coefficient candidates")
    axes[1].legend(loc="best", ncol=4)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_xlim(*xlim)
    fig.suptitle(f"{case_id}: directional state diagnostics")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / f"{case_id}_03_directional_state_diagnostics.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(11.2, 6.5), sharex=True)
    for ax in axes:
        mark_commands(ax, case)
    axes[0].plot(t, data["dir_hybrid_hfall_after_rise"], color="#d62728", lw=1.8, label="HFALL_AFTER_RISE")
    axes[0].plot(t, data["dir_hybrid_hrise_after_fall"], color="#2ca02c", lw=1.8, label="HRISE_AFTER_FALL")
    axes[0].plot(t, data["dir_hybrid_hdiractive"], color="#9467bd", lw=1.8, label="HDIRACTIVE")
    axes[0].plot(t, data["dir_hybrid_halign"], color=COLORS["align"], lw=2.1, label="HALIGN")
    axes[0].set_ylim(-0.1, 1.12)
    style(axes[0], "Detect/blend")
    axes[0].legend(loc="best", ncol=4)
    axes[1].plot(t, data["dir_hybrid_kutarget"], color="#2ca02c", lw=1.8, label="KUTARGET")
    axes[1].plot(t, data["dir_hybrid_kdtarget"], color="#1f77b4", lw=1.8, label="KDTARGET")
    axes[1].plot(t, data["dir_hybrid_highage"], color="#7f7f7f", lw=1.4, label="HIGHAGE ns")
    axes[1].plot(t, data["dir_hybrid_lowage"], color="#bcbd22", lw=1.4, label="LOWAGE ns")
    style(axes[1], "Target / age")
    axes[1].legend(loc="best", ncol=4)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_xlim(*xlim)
    fig.suptitle(f"{case_id}: alignment and detector diagnostics")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / f"{case_id}_04_alignment_diagnostics.png", dpi=180)
    plt.close(fig)


def plot_high_low_comparison() -> None:
    high = read_waveforms("short_pulse_1ns_high")
    low = read_waveforms("short_pulse_1ns_low")
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.5), sharex=False)
    for ax, case_id, data, coeff in [
        (axes[0, 0], "short_pulse_1ns_high", high, "ku"),
        (axes[0, 1], "short_pulse_1ns_low", low, "ku"),
        (axes[1, 0], "short_pulse_1ns_high", high, "kd"),
        (axes[1, 1], "short_pulse_1ns_low", low, "kd"),
    ]:
        case = case_by_id(case_id)
        mark_commands(ax, case)
        t = data["time_ns"]
        for key, label in [
            ("hspice", "HSPICE"),
            ("legacy", "legacy"),
            ("gate_hybrid", "GateState"),
            ("dir_hybrid", "Directional"),
        ]:
            ax.plot(t, data[f"{key}_{coeff}"], color=COLORS[key], lw=1.9, label=label)
        x0, x1 = command_times(case)
        ax.set_xlim(x0 - 0.75, min(case.stop_ns, x1 + 5.0))
        style(ax, coeff.upper())
        ax.set_title(case_id)
    axes[1, 0].set_xlabel("Time (ns)")
    axes[1, 1].set_xlabel("Time (ns)")
    axes[0, 1].legend(loc="best", ncol=2)
    fig.suptitle("Directional check: short high pulse vs mirrored short low pulse")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES_DIR / "high_vs_low_pulse_comparison.png", dpi=180)
    plt.close(fig)


def plot_summary_bars(rows: list[dict[str, object]]) -> None:
    short_ids = [
        "short_pulse_500ps_high",
        "short_pulse_1ns_high",
        "short_pulse_2ns_high",
        "short_pulse_500ps_low",
        "short_pulse_1ns_low",
        "short_pulse_2ns_low",
    ]
    metrics = [
        ("pad_active_rmse_v", "Pad RMSE (mV)", 1e3),
        ("ku_active_rmse", "Ku RMSE", 1.0),
        ("kd_active_rmse", "Kd RMSE", 1.0),
        ("ku_peak", "Ku peak", 1.0),
        ("kd_min", "Kd minimum", 1.0),
        ("kd_recovery_delta_ns", "Kd recovery delta (ns)", 1.0),
        ("overlap_energy_ns", "Ku*Kd overlap (ns)", 1.0),
    ]
    variants = [
        ("legacy", "legacy", COLORS["legacy"]),
        ("short_hybrid", "ShortHybrid", COLORS["short_hybrid"]),
        ("gate_hybrid", "GateState", COLORS["gate_hybrid"]),
        ("dir_hybrid", "Directional", COLORS["dir_hybrid"]),
    ]
    row_lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    fig, axes = plt.subplots(len(metrics), 1, figsize=(13.4, 16.2), sharex=True)
    x = np.arange(len(short_ids))
    width = 0.19
    for ax, (metric, ylabel, scale) in zip(axes, metrics):
        for offset, (variant, label, color) in zip([-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width], variants):
            values = []
            for case_id in short_ids:
                value = row_lookup[(case_id, variant)].get(metric, "")
                try:
                    values.append(float(value) * scale)
                except (TypeError, ValueError):
                    values.append(np.nan)
            ax.bar(x + offset, values, width=width, color=color, alpha=0.88, label=label)
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", alpha=0.28)
    axes[0].legend(loc="best", ncol=4)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(["500ps high", "1ns high", "2ns high", "500ps low", "1ns low", "2ns low"], rotation=25, ha="right")
    axes[-1].set_xlabel("Interrupted pulse case")
    fig.suptitle("Directional gate-state interrupted-pulse summary")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(FIGURES_DIR / "short_pulse_summary_bars.png", dpi=180)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]]) -> None:
    lookup = {(str(r["case_id"]), str(r["variant"])): r for r in rows}
    control_legacy = lookup[(CONTROL_CASE, "legacy")]
    control_dir = lookup[(CONTROL_CASE, "dir_hybrid")]
    control_pad_delta_mv = (float(control_dir["pad_active_rmse_v"]) - float(control_legacy["pad_active_rmse_v"])) * 1e3
    control_coeff_delta = max(float(control_dir["ku_active_rmse"]), float(control_dir["kd_active_rmse"])) - max(
        float(control_legacy["ku_active_rmse"]),
        float(control_legacy["kd_active_rmse"]),
    )

    short_ids = [case_id for case_id in REQUIRED_CASE_IDS if case_id.startswith("short_")]
    dir_better_legacy = 0
    dir_better_gate_kd = 0
    dir_better_gate_all = 0
    for case_id in short_ids:
        directional = lookup[(case_id, "dir_hybrid")]
        legacy = lookup[(case_id, "legacy")]
        gate = lookup[(case_id, "gate_hybrid")]
        if (
            float(directional["pad_active_rmse_v"]) < float(legacy["pad_active_rmse_v"])
            and float(directional["ku_active_rmse"]) < float(legacy["ku_active_rmse"])
            and float(directional["kd_active_rmse"]) < float(legacy["kd_active_rmse"])
        ):
            dir_better_legacy += 1
        if float(directional["kd_active_rmse"]) < float(gate["kd_active_rmse"]):
            dir_better_gate_kd += 1
        if (
            float(directional["pad_active_rmse_v"]) < float(gate["pad_active_rmse_v"])
            and float(directional["ku_active_rmse"]) < float(gate["ku_active_rmse"])
            and float(directional["kd_active_rmse"]) < float(gate["kd_active_rmse"])
        ):
            dir_better_gate_all += 1

    one_ns = lookup[(DEMO_CASE, "dir_hybrid")]
    gate_one_ns = lookup[(DEMO_CASE, "gate_hybrid")]
    short_one_ns = lookup[(DEMO_CASE, "short_hybrid")]
    legacy_one_ns = lookup[(DEMO_CASE, "legacy")]
    h_data = parse_hspice_tr0(CASES_DIR / DEMO_CASE / "hspice_native_ibis" / f"{DEMO_CASE}_hspice_native_ibis.tr0")
    h_t = to_ns(find_signal(h_data, "time"))
    h_mask = active_mask(h_t, case_by_id(DEMO_CASE))
    h_ku_peak = float(np.max(find_signal(h_data, "v(ku)")[h_mask]))

    lines = [
        "# io_buf Directional Gate-State pybis Retrigger Study",
        "",
        "This study tests `InputDrivenDirectionalGateStateHybrid`, which splits interrupted switching into Ku turn-on, Ku turn-off, Kd turn-off, and Kd turn-on states.",
        "",
        "## Headline",
        "",
        f"- Long-pulse control pad RMSE delta versus legacy: `{control_pad_delta_mv:.3f} mV`.",
        f"- Long-pulse control max Ku/Kd RMSE delta versus legacy: `{control_coeff_delta:.5f}`.",
        f"- Directional coefficient-first improvements versus legacy: `{dir_better_legacy}` / `{len(short_ids)}` interrupted cases.",
        f"- Directional Kd RMSE improvements versus GateStateHybrid: `{dir_better_gate_kd}` / `{len(short_ids)}` interrupted cases.",
        f"- Directional all-metric improvements versus GateStateHybrid: `{dir_better_gate_all}` / `{len(short_ids)}` interrupted cases.",
        "- `InputDrivenDirectionalGateStateFull` is diagnostic only and is not considered for default behavior.",
        "",
        "## short_pulse_1ns_high Specific Numbers",
        "",
        f"- HSPICE Ku peak: `{h_ku_peak:.4f}`",
        f"- legacy Ku peak: `{float(legacy_one_ns['ku_peak']):.4f}`",
        f"- ShortPulseHybrid Ku peak: `{float(short_one_ns['ku_peak']):.4f}`",
        f"- GateStateHybrid Ku peak: `{float(gate_one_ns['ku_peak']):.4f}`",
        f"- DirectionalGateStateHybrid Ku peak: `{float(one_ns['ku_peak']):.4f}`",
        "",
        "## Interrupted-Pulse Metric Table",
        "",
        "| Case | Flow | Pad RMSE mV | Ku RMSE | Kd RMSE | Ku peak | Kd minimum | Kd rec. delta ns | Overlap ns |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case_id in short_ids:
        for variant_id, flow_name in [
            ("legacy", "legacy pybis"),
            ("short_hybrid", "ShortPulseHybrid"),
            ("gate_hybrid", "GateStateHybrid"),
            ("dir_hybrid", "DirectionalGateStateHybrid"),
            ("dir_full", "DirectionalGateStateFull"),
        ]:
            row = lookup.get((case_id, variant_id))
            if row is None or row.get("status") == "failed":
                lines.append(f"| {case_id} | {flow_name} | failed |  |  |  |  |  |  |")
                continue
            rec = row.get("kd_recovery_delta_ns", "")
            try:
                rec_txt = f"{float(rec):.4f}"
            except (TypeError, ValueError):
                rec_txt = ""
            lines.append(
                f"| {case_id} | {flow_name} | {float(row['pad_active_rmse_v']) * 1e3:.3f} | "
                f"{float(row['ku_active_rmse']):.4f} | {float(row['kd_active_rmse']):.4f} | "
                f"{float(row['ku_peak']):.4f} | {float(row['kd_min']):.4f} | {rec_txt} | "
                f"{float(row['overlap_energy_ns']):.4f} |"
            )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "- `figures/*_01_input_pad_overlay.png`: input plus pad overlay.",
            "- `figures/*_02_ku_only.png`: Ku-only comparison.",
            "- `figures/*_02_kd_only.png`: Kd-only comparison.",
            "- `figures/*_03_directional_state_diagnostics.png`: KU_ON/KU_OFF/KD_OFF/KD_ON and composed KUDIR/KDDIR.",
            "- `figures/*_04_alignment_diagnostics.png`: fall-after-rise / rise-after-fall detectors and HALIGN blend.",
            "- `figures/high_vs_low_pulse_comparison.png`: mirrored interruption-direction comparison.",
            "- `figures/short_pulse_summary_bars.png`: summary metrics and overlap energy.",
            "",
            "## Interpretation",
            "",
            "A real pass requires Ku, Kd, and pad agreement. Lower pad RMSE alone is not enough.",
            "The directional model remains experimental unless it preserves the long-pulse control and improves Kd recovery versus the previous GateStateHybrid.",
            "",
        ]
    )
    write_text(DEMO_DIR / "README.md", "\n".join(lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# io_buf Directional Gate-State pybis Retrigger Study",
                "",
                "Canonical demo: `interrupted_switching_demo/README.md`",
                "",
                "Primary CSVs:",
                "",
                "- `candidate_metrics.csv`",
                "- `metrics_by_case.csv`",
                "- `interrupted_switching_demo/demo_metrics.csv`",
                "",
            ]
        ),
    )


def write_demo_metrics(rows: list[dict[str, object]]) -> None:
    selected = [r for r in rows if str(r.get("case_id", "")).startswith("short_")]
    write_csv(DEMO_DIR / "demo_metrics.csv", selected)


def generate_report(rows: list[dict[str, object]]) -> None:
    write_wide_metrics(rows)
    write_demo_metrics(rows)
    for case_id in [case_id for case_id in REQUIRED_CASE_IDS if case_id != CONTROL_CASE]:
        plot_main_case(case_id)
    plot_high_low_comparison()
    plot_summary_bars(rows)
    write_readme(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Directional gate-state pybis retrigger study.")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--ibis", type=Path, default=DEFAULT_IBIS)
    parser.add_argument("--case", action="append", default=[], help="Run only this case_id. May be repeated.")
    parser.add_argument("--resume", action="store_true", help="Skip completed case/variant rows.")
    parser.add_argument("--summarize-only", action="store_true", help="Regenerate plots/report from candidate_metrics.csv.")
    parser.add_argument("--timeout-s", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in [OUT_DIR, COMMON_DIR, CASES_DIR, DEMO_DIR, FIGURES_DIR]:
        ensure_dir(path)

    if args.summarize_only:
        rows = [r for r in read_csv(OUT_DIR / "candidate_metrics.csv") if r.get("variant") != "case_error"]
        generate_report(rows)
        print(f"OUT_DIR={OUT_DIR}")
        print(f"DEMO={DEMO_DIR / 'README.md'}")
        return 0

    model_paths = prepare_common(args.ibis)
    cases = selected_cases(args.case)
    existing_rows = read_csv(OUT_DIR / "candidate_metrics.csv") if args.resume else []
    done = {(str(r.get("case_id")), str(r.get("variant"))) for r in existing_rows}
    rows = list(existing_rows)
    case_order = [case.case_id for case in selected_cases([])]
    order = {(case_id, variant.variant_id): (i, j) for i, case_id in enumerate(case_order) for j, variant in enumerate(VARIANTS)}

    for idx, case in enumerate(cases, start=1):
        if args.resume and all((case.case_id, variant.variant_id) in done for variant in VARIANTS):
            print(f"[{idx}/{len(cases)}] {case.case_id} (resume skip)", flush=True)
            continue
        print(f"[{idx}/{len(cases)}] {case.case_id}", flush=True)
        rows = [r for r in rows if str(r.get("case_id")) != case.case_id]
        try:
            rows.extend(run_case(case, args.ngspice, args.ibis, model_paths, args.timeout_s))
        except Exception as exc:
            rows.append({"case_id": case.case_id, "variant": "case_error", "status": "failed", "error": str(exc)})
        rows.sort(key=lambda r: order.get((str(r.get("case_id")), str(r.get("variant"))), (9999, 9999)))
        write_csv(OUT_DIR / "candidate_metrics.csv", rows)

    ok_rows = [r for r in rows if r.get("variant") != "case_error"]
    generate_report(ok_rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"DEMO={DEMO_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
