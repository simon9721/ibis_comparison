from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
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


OUT_DIR = ROOT / "results" / "io_buf_coeff_state_retrigger_2026-06-20"
COMMON_DIR = OUT_DIR / "common"
CASES_DIR = OUT_DIR / "cases"
PLOTS_DIR = OUT_DIR / "plots"
DEFAULT_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
DEFAULT_NGSPICE = default_ngspice(console=True)
DEFAULT_HSPICE = default_hspice()


@dataclass(frozen=True)
class SweepCase:
    case_id: str
    description: str
    edge_ns: float
    stop_ns: float
    r_load_ohm: float
    c_load_pf: float
    high_v: float
    pattern: str
    high_time_ns: float = 10.0


def build_cases() -> list[SweepCase]:
    return [
        SweepCase("edge_1ps_base_50r_2pf", "Baseline 1 ps rise/fall, 50 ohm + 2 pF", 0.001, 25.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("edge_5ps_50r_2pf", "5 ps rise/fall, 50 ohm + 2 pF", 0.005, 25.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("edge_50ps_50r_2pf", "50 ps rise/fall, 50 ohm + 2 pF", 0.05, 25.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("edge_500ps_50r_2pf", "500 ps rise/fall, 50 ohm + 2 pF", 0.5, 26.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("edge_2ns_50r_2pf", "2 ns rise/fall, 50 ohm + 2 pF", 2.0, 30.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("load_25r_2pf", "1 ps rise/fall, 25 ohm + 2 pF", 0.001, 25.0, 25.0, 2.0, 3.3, "rise_fall"),
        SweepCase("load_50r_0pf", "1 ps rise/fall, 50 ohm only", 0.001, 25.0, 50.0, 0.0, 3.3, "rise_fall"),
        SweepCase("load_50r_10pf", "1 ps rise/fall, 50 ohm + 10 pF", 0.001, 30.0, 50.0, 10.0, 3.3, "rise_fall"),
        SweepCase("load_100r_2pf", "1 ps rise/fall, 100 ohm + 2 pF", 0.001, 25.0, 100.0, 2.0, 3.3, "rise_fall"),
        SweepCase("double_toggle_1ps", "Two 1 ps toggle cycles, 50 ohm + 2 pF", 0.001, 24.0, 50.0, 2.0, 3.3, "double_toggle"),
        SweepCase("short_pulse_2ns_high", "2 ns high pulse with 1 ps edges, 50 ohm + 2 pF", 0.001, 14.0, 50.0, 2.0, 3.3, "short_pulse", 2.0),
        SweepCase("short_pulse_1ns_high", "1 ns high pulse with 1 ps edges, 50 ohm + 2 pF", 0.001, 13.0, 50.0, 2.0, 3.3, "short_pulse", 1.0),
        SweepCase("short_pulse_500ps_high", "500 ps high pulse with 1 ps edges, 50 ohm + 2 pF", 0.001, 12.5, 50.0, 2.0, 3.3, "short_pulse", 0.5),
    ]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def run_process(cmd: list[str], cwd: Path, log_path: Path, timeout_s: int = 240) -> int:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        log_path.write_text(
            "COMMAND: " + " ".join(cmd) + f"\n\nTIMEOUT after {timeout_s} s\n\n" + stdout,
            encoding="utf-8",
        )
        return -999
    log_path.write_text("COMMAND: " + " ".join(cmd) + "\n\n" + proc.stdout, encoding="utf-8")
    return int(proc.returncode)


def fmt_num(value: float) -> str:
    if abs(value - round(value)) < 1e-12:
        return str(int(round(value)))
    return f"{value:.12g}"


def spice_time_ns(value: float) -> str:
    return f"{fmt_num(value)}n"


def build_pwl_points(case: SweepCase) -> list[tuple[float, float]]:
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
    if case.pattern == "short_pulse":
        fall_start = 5.0 + case.high_time_ns
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + e, hv),
            (fall_start, hv),
            (fall_start + e, 0.0),
            (case.stop_ns, 0.0),
        ]
    if case.pattern == "double_toggle":
        return [
            (0.0, 0.0),
            (3.0, 0.0),
            (3.0 + e, hv),
            (8.0, hv),
            (8.0 + e, 0.0),
            (13.0, 0.0),
            (13.0 + e, hv),
            (18.0, hv),
            (18.0 + e, 0.0),
            (case.stop_ns, 0.0),
        ]
    raise ValueError(f"Unknown pattern: {case.pattern}")


def transition_windows(case: SweepCase) -> list[tuple[float, float]]:
    points = build_pwl_points(case)
    windows: list[tuple[float, float]] = []
    tail = max(3.0, case.edge_ns + 10.0 * case.r_load_ohm * case.c_load_pf * 1e-3)
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if abs(v1 - v0) > 1e-9:
            windows.append((max(0.0, t0 - 0.5), min(case.stop_ns, t1 + tail)))
    return windows


def active_mask(t_ns: np.ndarray, case: SweepCase) -> np.ndarray:
    mask = np.zeros_like(t_ns, dtype=bool)
    for x0, x1 in transition_windows(case):
        mask |= (t_ns >= x0) & (t_ns <= x1)
    return mask


def pwl_text(case: SweepCase) -> str:
    lines = ["Vin in_dig 0 PWL("]
    points = build_pwl_points(case)
    for idx, (time_ns, voltage) in enumerate(points):
        lines.append(f"+ {spice_time_ns(time_ns):>10} {fmt_num(voltage):>8}")
    lines[-1] = lines[-1] + " )"
    return "\n".join(lines)


def c_load_line(node: str, c_load_pf: float) -> str:
    if c_load_pf <= 0:
        return ""
    return f"Cload {node} 0 {fmt_num(c_load_pf)}p\n"


def make_hspice_deck(case: SweepCase) -> str:
    return f"""* io_buf native IBIS HSPICE switching coefficient extraction
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


def make_ngspice_deck(case: SweepCase, coeff_state: bool) -> str:
    extra_save = " V(xdrv.kutarget) V(xdrv.kdtarget)" if coeff_state else ""
    title = "coefficient-state pybis" if coeff_state else "legacy pybis"
    return f"""* io_buf {title}/ngspice switching coefficient extraction
* Sweep case: {case.case_id}
* {case.description}
.title io_buf ngspice {title} Ku/Kd extraction {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{pwl_text(case)}

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 {fmt_num(case.r_load_ohm)}
{c_load_line("pad", case.c_load_pf).rstrip()}

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){extra_save}
.tran 0.001n {spice_time_ns(case.stop_ns)}
.end
"""


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    available = ", ".join(sorted(data.keys()))
    raise KeyError(f"Missing signal {names}; available: {available}")


def to_ns(t_s: np.ndarray) -> np.ndarray:
    return np.asarray(t_s, dtype=float) * 1e9


def interp_to(t_src_ns: np.ndarray, y_src: np.ndarray, t_dst_ns: np.ndarray) -> np.ndarray:
    return np.interp(t_dst_ns, t_src_ns, y_src)


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((a - b) ** 2)))


def maxabs(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0:
        return float("nan")
    return float(np.max(np.abs(a - b)))


def status_for(pad_rmse_v: float, ku_rmse: float, kd_rmse: float) -> str:
    pad_mv = pad_rmse_v * 1e3
    coeff = max(ku_rmse, kd_rmse)
    if pad_mv <= 10.0 and coeff <= 0.01:
        return "GOOD"
    if pad_mv <= 25.0 and coeff <= 0.03:
        return "WARN"
    return "CHECK"


def percent_reduction(old: float, new: float) -> float:
    if not np.isfinite(old) or abs(old) < 1e-30:
        return float("nan")
    return 100.0 * (old - new) / old


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def prepare_common(ibis_path: Path) -> tuple[Path, Path]:
    ensure_dir(COMMON_DIR)
    common_ibis = COMMON_DIR / "io_buf.ibs"
    shutil.copy2(ibis_path, common_ibis)

    legacy = COMMON_DIR / "legacy" / "driver_OutputInput_Typical.sub"
    coeff = COMMON_DIR / "coeff_state" / "driver_OutputInput_Typical.sub"
    convert_ibis_to_pybis(
        ibis_path=common_ibis,
        output_path=legacy,
        component_name="MCM Driver 1",
        model_name="driver",
        io_type="Output",
        subcircuit_type="InputDriven",
        corner="Typical",
    )
    convert_ibis_to_pybis(
        ibis_path=common_ibis,
        output_path=coeff,
        component_name="MCM Driver 1",
        model_name="driver",
        io_type="Output",
        subcircuit_type="InputDrivenCoeffState",
        corner="Typical",
    )
    return legacy, coeff


def run_ngspice_variant(
    case: SweepCase,
    ngspice: Path,
    model_path: Path,
    variant: str,
    coeff_state: bool,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], Path, Path, int]:
    n_dir = CASES_DIR / case.case_id / f"ngspice_{variant}"
    ensure_dir(n_dir)
    shutil.copy2(model_path, n_dir / "driver_OutputInput_Typical.sub")
    stem = f"{case.case_id}_ngspice_{variant}"
    deck = n_dir / f"{stem}.sp"
    raw = n_dir / f"{stem}.raw"
    write_text(deck, make_ngspice_deck(case, coeff_state=coeff_state))
    rc = run_process([str(ngspice), "-b", "-r", raw.name, deck.name], n_dir, n_dir / "ngspice_stdout.log", timeout_s=timeout_s)
    if rc != 0:
        raise RuntimeError(f"ngspice {variant} return code {rc}")
    return parse_ngspice_raw(raw), deck, raw, rc


def run_case(case: SweepCase, ngspice: Path, ibis_path: Path, legacy_model: Path, coeff_model: Path, timeout_s: int) -> dict[str, object]:
    h_dir = CASES_DIR / case.case_id / "hspice_native_ibis"
    ensure_dir(h_dir)
    h_stem = f"{case.case_id}_hspice_native_ibis"
    h_deck = h_dir / f"{h_stem}.sp"
    h_deck_text = make_hspice_deck(case)
    signature_id, signature = reference_signature(
        h_deck_text,
        [ibis_path],
        {"family": "io_buf_native_ibis", "case_id": case.case_id},
    )
    h_cache = cache_dir("io_buf_native_ibis", case.case_id, signature_id)
    hspice_restored = restore_hspice_cache(h_cache, h_dir, h_stem, h_deck_text)
    hspice_existing = (h_dir / f"{h_stem}.tr0").exists()
    if hspice_existing and not hspice_restored:
        save_hspice_cache(h_cache, h_dir, h_stem, h_deck_text, signature)
    if not hspice_restored:
        shutil.copy2(ibis_path, h_dir / "io_buf.ibs")
        write_text(h_deck, h_deck_text)

    row: dict[str, object] = {
        "case_id": case.case_id,
        "description": case.description,
        "pattern": case.pattern,
        "edge_ns": case.edge_ns,
        "pulse_high_ns": case.high_time_ns if case.pattern == "short_pulse" else "",
        "r_load_ohm": case.r_load_ohm,
        "c_load_pf": case.c_load_pf,
        "hspice_deck": str(h_deck.relative_to(ROOT)),
    }

    try:
        if hspice_restored:
            h_rc = 0
            row["hspice_reference"] = "cache"
        elif hspice_existing:
            h_rc = 0
            row["hspice_reference"] = "existing"
        else:
            h_rc = run_process([str(DEFAULT_HSPICE), "-i", h_deck.name, "-o", h_stem], h_dir, h_dir / "hspice_stdout.log", timeout_s=timeout_s)
            if h_rc != 0:
                row.update({"status": "hspice_failed", "error": f"HSPICE return code {h_rc}"})
                return row
            save_hspice_cache(h_cache, h_dir, h_stem, h_deck_text, signature)
            row["hspice_reference"] = "run"

        h_data = parse_hspice_tr0(h_dir / f"{h_stem}.tr0")
        legacy_data, legacy_deck, _, legacy_rc = run_ngspice_variant(case, ngspice, legacy_model, "legacy", False, timeout_s=timeout_s)
        coeff_data, coeff_deck, _, coeff_rc = run_ngspice_variant(case, ngspice, coeff_model, "coeff_state", True, timeout_s=timeout_s)
        row["legacy_ngspice_deck"] = str(legacy_deck.relative_to(ROOT))
        row["coeff_ngspice_deck"] = str(coeff_deck.relative_to(ROOT))
        row["legacy_ngspice_return_code"] = legacy_rc
        row["coeff_ngspice_return_code"] = coeff_rc

        h_t = to_ns(find_signal(h_data, "time"))
        h_pad = find_signal(h_data, "v(pad_ibis)")
        h_ku = find_signal(h_data, "v(ku)")
        h_kd = find_signal(h_data, "v(kd)")
        mask = active_mask(h_t, case)

        def score_variant(prefix: str, data: dict[str, np.ndarray]) -> dict[str, object]:
            n_t = to_ns(find_signal(data, "time"))
            n_pad = interp_to(n_t, find_signal(data, "v(pad)"), h_t)
            n_ku = interp_to(n_t, find_signal(data, "v(xdrv.ku)", "v(xdrv:ku)"), h_t)
            n_kd = interp_to(n_t, find_signal(data, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)
            pad_rmse = rmse(h_pad[mask], n_pad[mask])
            ku_rmse = rmse(h_ku[mask], n_ku[mask])
            kd_rmse = rmse(h_kd[mask], n_kd[mask])
            return {
                f"{prefix}_pad_active_rmse_v": pad_rmse,
                f"{prefix}_pad_active_max_v": maxabs(h_pad[mask], n_pad[mask]),
                f"{prefix}_ku_active_rmse": ku_rmse,
                f"{prefix}_ku_active_max": maxabs(h_ku[mask], n_ku[mask]),
                f"{prefix}_kd_active_rmse": kd_rmse,
                f"{prefix}_kd_active_max": maxabs(h_kd[mask], n_kd[mask]),
                f"{prefix}_ku_peak": float(np.max(n_ku[mask])),
                f"{prefix}_kd_min": float(np.min(n_kd[mask])),
                f"{prefix}_status": status_for(pad_rmse, ku_rmse, kd_rmse),
            }

        row.update(score_variant("legacy", legacy_data))
        row.update(score_variant("coeff", coeff_data))
        row["pad_rmse_reduction_pct"] = percent_reduction(
            float(row["legacy_pad_active_rmse_v"]),
            float(row["coeff_pad_active_rmse_v"]),
        )
        row["ku_rmse_reduction_pct"] = percent_reduction(
            float(row["legacy_ku_active_rmse"]),
            float(row["coeff_ku_active_rmse"]),
        )
        row["kd_rmse_reduction_pct"] = percent_reduction(
            float(row["legacy_kd_active_rmse"]),
            float(row["coeff_kd_active_rmse"]),
        )
        row["coeff_ku_min"] = float(np.min(interp_to(to_ns(find_signal(coeff_data, "time")), find_signal(coeff_data, "v(xdrv.ku)", "v(xdrv:ku)"), h_t)[mask]))
        row["coeff_ku_max"] = float(np.max(interp_to(to_ns(find_signal(coeff_data, "time")), find_signal(coeff_data, "v(xdrv.ku)", "v(xdrv:ku)"), h_t)[mask]))
        row["coeff_kd_min_all"] = float(np.min(interp_to(to_ns(find_signal(coeff_data, "time")), find_signal(coeff_data, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)[mask]))
        row["coeff_kd_max"] = float(np.max(interp_to(to_ns(find_signal(coeff_data, "time")), find_signal(coeff_data, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)[mask]))
        row["coeff_coeff_range_ok"] = (
            float(row["coeff_ku_min"]) >= -0.2
            and float(row["coeff_ku_max"]) <= 1.2
            and float(row["coeff_kd_min_all"]) >= -0.2
            and float(row["coeff_kd_max"]) <= 1.2
        )
        row["status"] = "ok"
        plot_case(case, h_data, legacy_data, coeff_data)
    except Exception as exc:
        row.update({"status": "failed", "error": str(exc)})
    return row


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def plot_case(
    case: SweepCase,
    h_data: dict[str, np.ndarray],
    legacy_data: dict[str, np.ndarray],
    coeff_data: dict[str, np.ndarray],
) -> None:
    ensure_dir(PLOTS_DIR / "cases")
    h_t = to_ns(find_signal(h_data, "time"))
    h_pad = find_signal(h_data, "v(pad_ibis)")
    h_ku = find_signal(h_data, "v(ku)")
    h_kd = find_signal(h_data, "v(kd)")
    legacy_t = to_ns(find_signal(legacy_data, "time"))
    coeff_t = to_ns(find_signal(coeff_data, "time"))

    fig, axes = plt.subplots(3, 1, figsize=(11, 9.2), sharex=True)
    axes[0].plot(h_t, h_pad, lw=2.1, label="HSPICE native IBIS")
    axes[0].plot(legacy_t, find_signal(legacy_data, "v(pad)"), lw=1.6, ls="--", label="ngspice legacy pybis")
    axes[0].plot(coeff_t, find_signal(coeff_data, "v(pad)"), lw=1.7, ls="-.", label="ngspice coeff-state")
    style(axes[0], "Pad voltage (V)")
    axes[0].legend(loc="best")

    axes[1].plot(h_t, h_ku, lw=2.0, color="#1f77b4", label="HSPICE Ku")
    axes[1].plot(h_t, h_kd, lw=2.0, color="#d62728", label="HSPICE Kd")
    axes[1].plot(legacy_t, find_signal(legacy_data, "v(xdrv.ku)", "v(xdrv:ku)"), lw=1.5, ls="--", color="#1f77b4", label="legacy Ku")
    axes[1].plot(legacy_t, find_signal(legacy_data, "v(xdrv.kd)", "v(xdrv:kd)"), lw=1.5, ls="--", color="#d62728", label="legacy Kd")
    axes[1].plot(coeff_t, find_signal(coeff_data, "v(xdrv.ku)", "v(xdrv:ku)"), lw=1.7, ls="-.", color="#1f77b4", label="coeff Ku")
    axes[1].plot(coeff_t, find_signal(coeff_data, "v(xdrv.kd)", "v(xdrv:kd)"), lw=1.7, ls="-.", color="#d62728", label="coeff Kd")
    axes[1].set_ylim(-0.12, 1.15)
    style(axes[1], "Ku / Kd")
    axes[1].legend(loc="best", ncol=3)

    axes[2].plot(coeff_t, find_signal(coeff_data, "v(xdrv.kutarget)", "v(xdrv:kutarget)"), lw=1.8, label="KUTARGET")
    axes[2].plot(coeff_t, find_signal(coeff_data, "v(xdrv.kdtarget)", "v(xdrv:kdtarget)"), lw=1.8, label="KDTARGET")
    axes[2].plot(coeff_t, find_signal(coeff_data, "v(xdrv.ku)", "v(xdrv:ku)"), lw=1.4, ls="--", label="Ku state")
    axes[2].plot(coeff_t, find_signal(coeff_data, "v(xdrv.kd)", "v(xdrv:kd)"), lw=1.4, ls="--", label="Kd state")
    axes[2].set_ylim(-0.12, 1.15)
    style(axes[2], "Coeff diagnostics")
    axes[2].legend(loc="best", ncol=3)
    axes[2].set_xlabel("Time (ns)")

    fig.suptitle(f"{case.case_id}: legacy pybis vs coefficient-state retrigger")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(PLOTS_DIR / "cases" / f"{case.case_id}_legacy_vs_coeff_state.png", dpi=180)
    plt.close(fig)


def plot_summary(rows: list[dict[str, object]]) -> None:
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    if not ok_rows:
        return
    labels = [str(r["case_id"]) for r in ok_rows]
    y = np.arange(len(labels))
    legacy = np.array([float(r["legacy_pad_active_rmse_v"]) * 1e3 for r in ok_rows])
    coeff = np.array([float(r["coeff_pad_active_rmse_v"]) * 1e3 for r in ok_rows])

    ensure_dir(PLOTS_DIR)
    fig, ax = plt.subplots(figsize=(11, max(5.0, 0.42 * len(labels))))
    ax.barh(y - 0.16, legacy, height=0.3, label="legacy pad RMSE (mV)")
    ax.barh(y + 0.16, coeff, height=0.3, label="coeff-state pad RMSE (mV)")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Pad active-window RMSE (mV)")
    ax.grid(True, axis="x", alpha=0.28)
    ax.legend(loc="best")
    ax.set_title("Coefficient-state retrigger A/B summary")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "summary_pad_rmse_legacy_vs_coeff_state.png", dpi=180)
    plt.close(fig)


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summary = []
    for row in rows:
        if row.get("status") != "ok":
            continue
        case_id = str(row["case_id"])
        if case_id.startswith("short_pulse"):
            kind = "short_pulse"
        elif str(row.get("pattern")) in {"rise_fall", "double_toggle"}:
            kind = "complete_edge"
        else:
            kind = "other"
        legacy_pad = float(row["legacy_pad_active_rmse_v"])
        coeff_pad = float(row["coeff_pad_active_rmse_v"])
        legacy_coeff = max(float(row["legacy_ku_active_rmse"]), float(row["legacy_kd_active_rmse"]))
        coeff_coeff = max(float(row["coeff_ku_active_rmse"]), float(row["coeff_kd_active_rmse"]))
        pad_reduction = float(row["pad_rmse_reduction_pct"])
        coeff_range_ok = str(row.get("coeff_coeff_range_ok", "False")) == "True" or row.get("coeff_coeff_range_ok") is True
        if kind == "complete_edge":
            verdict = "PASS" if coeff_pad <= legacy_pad + 0.005 and coeff_coeff <= legacy_coeff + 0.02 and coeff_range_ok else "REGRESSION"
        elif kind == "short_pulse":
            ku_better = float(row["coeff_ku_active_rmse"]) <= float(row["legacy_ku_active_rmse"])
            kd_better = float(row["coeff_kd_active_rmse"]) <= float(row["legacy_kd_active_rmse"])
            pad_better = pad_reduction > 0.0
            if ku_better and kd_better and pad_better and coeff_range_ok:
                verdict = "PASS"
            elif pad_better and not (ku_better and kd_better):
                verdict = "FALSE_PASS_PAD_ONLY"
            else:
                verdict = "NOT_ENOUGH_IMPROVEMENT"
        else:
            verdict = "INFO"
        summary.append(
            {
                "case_id": case_id,
                "kind": kind,
                "legacy_status": row["legacy_status"],
                "coeff_status": row["coeff_status"],
                "legacy_pad_rmse_mv": legacy_pad * 1e3,
                "coeff_pad_rmse_mv": coeff_pad * 1e3,
                "pad_rmse_reduction_pct": pad_reduction,
                "legacy_coeff_rmse": legacy_coeff,
                "coeff_coeff_rmse": coeff_coeff,
                "legacy_ku_rmse": float(row["legacy_ku_active_rmse"]),
                "coeff_ku_rmse": float(row["coeff_ku_active_rmse"]),
                "legacy_kd_rmse": float(row["legacy_kd_active_rmse"]),
                "coeff_kd_rmse": float(row["coeff_kd_active_rmse"]),
                "coeff_range_ok": coeff_range_ok,
                "verdict": verdict,
            }
        )
    return summary


def write_readme(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    complete_regressions = [r for r in summary if r["kind"] == "complete_edge" and r["verdict"] == "REGRESSION"]
    short_pass = [r for r in summary if r["kind"] == "short_pulse" and r["verdict"] == "PASS"]
    false_pass = [r for r in summary if r["verdict"] == "FALSE_PASS_PAD_ONLY"]
    short_total = [r for r in summary if r["kind"] == "short_pulse"]

    lines = [
        "# io_buf Coefficient-State pybis Retrigger Study",
        "",
        "This study compares HSPICE native IBIS against two ngspice pybis models:",
        "",
        "- Legacy `InputDriven`: edge restarts evaluate Ku/Kd from elapsed time since the latest input edge.",
        "- Experimental `InputDrivenCoeffState`: Ku/Kd are independent continuous coefficient states driven by fitted delayed branch states derived from the IBIS coefficient tables.",
        "",
        "## Headline",
        "",
        f"- Completed cases: `{len(ok_rows)}` / `{len(rows)}`.",
        f"- Complete-edge regressions: `{len(complete_regressions)}`.",
        f"- Short-pulse coefficient-first passes: `{len(short_pass)}` / `{len(short_total)}`.",
        f"- Pad-only false passes: `{len(false_pass)}`.",
        "- Current conclusion: `InputDrivenCoeffState` is useful as an experimental short-pulse demo, but it is not default-ready because complete edges regress versus legacy pybis.",
        "",
        "## Outputs",
        "",
        "- `metrics_by_case.csv`",
        "- `legacy_vs_coeff_state_summary.csv`",
        "- `plots/summary_pad_rmse_legacy_vs_coeff_state.png`",
        "- `plots/cases/*_legacy_vs_coeff_state.png`",
        "- `common/legacy/driver_OutputInput_Typical.sub`",
        "- `common/coeff_state/driver_OutputInput_Typical.sub`",
        "",
        "## Case Summary",
        "",
        "| Case | Kind | Legacy | Coeff | Legacy pad RMSE mV | Coeff pad RMSE mV | Legacy Ku/Kd RMSE | Coeff Ku/Kd RMSE | Pad reduction % | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary:
        lines.append(
            "| {case_id} | {kind} | {legacy_status} | {coeff_status} | {legacy_pad_rmse_mv:.3f} | "
            "{coeff_pad_rmse_mv:.3f} | {legacy_coeff_rmse:.3f} | {coeff_coeff_rmse:.3f} | "
            "{pad_rmse_reduction_pct:.1f} | {verdict} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation Guide",
            "",
            "`PASS` for complete-edge cases means the coefficient-state model did not materially regress normal edges.",
            "`PASS` for short-pulse cases requires pad improvement and both Ku and Kd RMSE improvement versus legacy pybis.",
            "`FALSE_PASS_PAD_ONLY` means the pad waveform improved but at least one coefficient got worse, so the model is not physically accepted.",
            "This is still experimental; it should not replace the default `InputDriven` mode unless it preserves normal-edge behavior and improves interrupted transitions for the right coefficient-state reason.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare legacy pybis and experimental coefficient-state retriggering against HSPICE IBIS.")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--ibis", type=Path, default=DEFAULT_IBIS)
    parser.add_argument("--case", action="append", default=[], help="Run only this case_id. May be repeated.")
    parser.add_argument("--resume", action="store_true", help="Reuse existing ok rows in metrics_by_case.csv.")
    parser.add_argument("--summarize-only", action="store_true", help="Regenerate summary files from metrics_by_case.csv without simulations.")
    parser.add_argument("--timeout-s", type=int, default=300, help="Timeout per HSPICE/ngspice process.")
    return parser.parse_args()


def selected_cases(case_ids: list[str]) -> list[SweepCase]:
    cases = build_cases()
    if not case_ids:
        return cases
    case_by_id = {case.case_id: case for case in cases}
    missing = [case_id for case_id in case_ids if case_id not in case_by_id]
    if missing:
        known = ", ".join(sorted(case_by_id))
        raise SystemExit(f"Unknown case(s): {', '.join(missing)}\nKnown cases: {known}")
    return [case_by_id[case_id] for case_id in case_ids]


def write_outputs(rows: list[dict[str, object]]) -> None:
    summary = summarize(rows)
    write_csv(OUT_DIR / "legacy_vs_coeff_state_summary.csv", summary)
    plot_summary(rows)
    write_readme(rows, summary)


def main() -> int:
    args = parse_args()
    ngspice = args.ngspice
    for path in [OUT_DIR, COMMON_DIR, CASES_DIR, PLOTS_DIR]:
        ensure_dir(path)

    if args.summarize_only:
        rows = read_csv(OUT_DIR / "metrics_by_case.csv")
        write_outputs(rows)
        print(f"OUT_DIR={OUT_DIR}")
        print(f"README={OUT_DIR / 'README.md'}")
        return 0

    legacy_model, coeff_model = prepare_common(args.ibis)
    cases = selected_cases(args.case)
    all_case_order = [case.case_id for case in build_cases()]
    row_by_id = {str(row.get("case_id")): row for row in read_csv(OUT_DIR / "metrics_by_case.csv")} if args.resume else {}
    for idx, case in enumerate(cases, start=1):
        existing = row_by_id.get(case.case_id)
        if args.resume and existing and existing.get("status") == "ok":
            print(f"[{idx}/{len(cases)}] {case.case_id} (resume skip)", flush=True)
            continue
        print(f"[{idx}/{len(cases)}] {case.case_id}", flush=True)
        row_by_id[case.case_id] = run_case(case, ngspice, args.ibis, legacy_model, coeff_model, timeout_s=args.timeout_s)
        ordered_rows = [row_by_id[case_id] for case_id in all_case_order if case_id in row_by_id]
        write_csv(OUT_DIR / "metrics_by_case.csv", ordered_rows)

    rows = [row_by_id[case_id] for case_id in all_case_order if case_id in row_by_id]
    write_outputs(rows)

    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
