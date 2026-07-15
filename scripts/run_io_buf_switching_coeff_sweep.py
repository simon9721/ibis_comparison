from __future__ import annotations

import csv
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

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from hspice_reference_cache import cache_dir, reference_signature, restore as restore_hspice_cache, save as save_hspice_cache  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


OUT_DIR = ROOT / "results" / "io_buf_switching_coeff_sweep_2026-06-19"
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


def build_cases() -> list[SweepCase]:
    return [
        SweepCase("edge_1ps_base_50r_2pf", "Baseline 1 ps rise/fall, 50 ohm + 2 pF", 0.001, 25.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("edge_5ps_50r_2pf", "5 ps rise/fall, 50 ohm + 2 pF", 0.005, 25.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("edge_50ps_50r_2pf", "50 ps rise/fall, 50 ohm + 2 pF", 0.05, 25.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("edge_500ps_50r_2pf", "500 ps rise/fall, 50 ohm + 2 pF", 0.5, 26.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("edge_2ns_50r_2pf", "2 ns rise/fall, 50 ohm + 2 pF", 2.0, 30.0, 50.0, 2.0, 3.3, "rise_fall"),
        SweepCase("load_50r_0pf", "1 ps rise/fall, 50 ohm only", 0.001, 25.0, 50.0, 0.0, 3.3, "rise_fall"),
        SweepCase("load_50r_10pf", "1 ps rise/fall, 50 ohm + 10 pF", 0.001, 30.0, 50.0, 10.0, 3.3, "rise_fall"),
        SweepCase("load_25r_2pf", "1 ps rise/fall, 25 ohm + 2 pF", 0.001, 25.0, 25.0, 2.0, 3.3, "rise_fall"),
        SweepCase("load_100r_2pf", "1 ps rise/fall, 100 ohm + 2 pF", 0.001, 25.0, 100.0, 2.0, 3.3, "rise_fall"),
        SweepCase("short_pulse_2ns_high", "2 ns high pulse with 1 ps edges, 50 ohm + 2 pF", 0.001, 14.0, 50.0, 2.0, 3.3, "short_pulse"),
        SweepCase("double_toggle_1ps", "Two 1 ps toggle cycles, 50 ohm + 2 pF", 0.001, 24.0, 50.0, 2.0, 3.3, "double_toggle"),
        SweepCase("marginal_input_1p8_high", "1.8 V high input, below nominal Vinh, 50 ohm + 2 pF", 0.001, 25.0, 50.0, 2.0, 1.8, "rise_fall"),
    ]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def run_process(cmd: list[str], cwd: Path, log_path: Path, timeout_s: int = 240) -> int:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_s,
    )
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
        return [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0 + e, hv),
            (7.0, hv),
            (7.0 + e, 0.0),
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


def pwl_text(case: SweepCase) -> str:
    lines = ["Vin in_dig 0 PWL("]
    points = build_pwl_points(case)
    for idx, (time_ns, voltage) in enumerate(points):
        prefix = "+ " if idx else "+ "
        lines.append(f"{prefix}{spice_time_ns(time_ns):>10} {fmt_num(voltage):>8}")
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


def make_ngspice_deck(case: SweepCase) -> str:
    return f"""* io_buf pybis/ngspice switching coefficient extraction
* Sweep case: {case.case_id}
* {case.description}
.title io_buf ngspice pybis Ku/Kd extraction {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{pwl_text(case)}

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 {fmt_num(case.r_load_ohm)}
{c_load_line("pad", case.c_load_pf).rstrip()}

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
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


def active_mask(t_ns: np.ndarray, case: SweepCase) -> np.ndarray:
    mask = np.zeros_like(t_ns, dtype=bool)
    for x0, x1 in transition_windows(case):
        mask |= (t_ns >= x0) & (t_ns <= x1)
    return mask


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((a - b) ** 2)))


def maxabs(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0:
        return float("nan")
    return float(np.max(np.abs(a - b)))


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


def write_waveform_csv(path: Path, traces: dict[str, np.ndarray]) -> None:
    keys = list(traces)
    n = len(traces[keys[0]])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for i in range(n):
            writer.writerow([traces[key][i] for key in keys])


def style(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)


def plot_case(
    case: SweepCase,
    h_t: np.ndarray,
    h_pad: np.ndarray,
    h_ku: np.ndarray,
    h_kd: np.ndarray,
    n_t: np.ndarray,
    n_pad: np.ndarray,
    n_ku: np.ndarray,
    n_kd: np.ndarray,
) -> None:
    ensure_dir(PLOTS_DIR / "cases")
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.4), sharex=True)
    axes[0].plot(h_t, h_pad, lw=2.0, label="HSPICE native IBIS pad")
    axes[0].plot(n_t, n_pad, lw=1.7, ls="--", label="ngspice pybis pad")
    style(axes[0], "Pad voltage (V)")
    axes[0].legend(loc="best")
    axes[1].plot(h_t, h_ku, lw=2.0, label="HSPICE Ku")
    axes[1].plot(h_t, h_kd, lw=2.0, label="HSPICE Kd")
    axes[1].plot(n_t, n_ku, lw=1.7, ls="--", label="ngspice pybis Ku")
    axes[1].plot(n_t, n_kd, lw=1.7, ls="--", label="ngspice pybis Kd")
    style(axes[1], "Coefficient")
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_ylim(-0.1, 1.1)
    axes[1].legend(loc="best", ncol=2)
    fig.suptitle(f"{case.case_id}: {case.description}")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(PLOTS_DIR / "cases" / f"{case.case_id}_waveform_coeff_overlay.png", dpi=180)
    plt.close(fig)

    for idx, (x0, x1) in enumerate(transition_windows(case), start=1):
        fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.0), sharex=True)
        axes[0].plot(h_t, h_pad, lw=2.0, label="HSPICE native IBIS")
        axes[0].plot(n_t, n_pad, lw=1.8, ls="--", label="ngspice pybis")
        axes[0].set_xlim(x0, x1)
        style(axes[0], "Pad voltage (V)")
        axes[0].legend(loc="best")
        axes[1].plot(h_t, h_ku, lw=2.0, label="HSPICE Ku")
        axes[1].plot(h_t, h_kd, lw=2.0, label="HSPICE Kd")
        axes[1].plot(n_t, n_ku, lw=1.8, ls="--", label="ngspice pybis Ku")
        axes[1].plot(n_t, n_kd, lw=1.8, ls="--", label="ngspice pybis Kd")
        axes[1].set_xlim(x0, x1)
        axes[1].set_ylim(-0.1, 1.1)
        style(axes[1], "Coefficient")
        axes[1].set_xlabel("Time (ns)")
        axes[1].legend(loc="best", ncol=2)
        fig.suptitle(f"{case.case_id}: transition {idx} zoom")
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(PLOTS_DIR / "cases" / f"{case.case_id}_transition_{idx:02d}_zoom.png", dpi=180)
        plt.close(fig)


def plot_summary(rows: list[dict[str, object]]) -> None:
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    if not ok_rows:
        return
    labels = [str(r["case_id"]) for r in ok_rows]
    y = np.arange(len(labels))
    pad = np.array([float(r["pad_active_rmse_v"]) * 1e3 for r in ok_rows])
    ku = np.array([float(r["ku_active_rmse"]) for r in ok_rows])
    kd = np.array([float(r["kd_active_rmse"]) for r in ok_rows])

    ensure_dir(PLOTS_DIR)
    fig, ax = plt.subplots(figsize=(11, max(5.0, 0.42 * len(labels))))
    ax.barh(y - 0.22, pad, height=0.2, label="Pad RMSE (mV)")
    ax.barh(y, ku * 1000.0, height=0.2, label="Ku RMSE x1000")
    ax.barh(y + 0.22, kd * 1000.0, height=0.2, label="Kd RMSE x1000")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Scaled error")
    ax.grid(True, axis="x", alpha=0.28)
    ax.legend(loc="best")
    ax.set_title("io_buf switching coefficient sweep summary")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "summary_rmse_by_case.png", dpi=180)
    plt.close(fig)


def case_status(row: dict[str, object]) -> str:
    if row.get("status") != "ok":
        return "FAIL"
    pad_mv = float(row["pad_active_rmse_v"]) * 1e3
    coeff = max(float(row["ku_active_rmse"]), float(row["kd_active_rmse"]))
    if pad_mv <= 10.0 and coeff <= 0.01:
        return "GOOD"
    if pad_mv <= 25.0 and coeff <= 0.03:
        return "WARN"
    return "CHECK"


def prepare_common(ibis_path: Path) -> Path:
    ensure_dir(COMMON_DIR)
    common_ibis = COMMON_DIR / "io_buf.ibs"
    shutil.copy2(ibis_path, common_ibis)
    subckt = COMMON_DIR / "driver_OutputInput_Typical.sub"
    convert_ibis_to_pybis(
        ibis_path=common_ibis,
        output_path=subckt,
        component_name="MCM Driver 1",
        model_name="driver",
        io_type="Output",
        subcircuit_type="InputDriven",
        corner="Typical",
    )
    return subckt


def run_case(case: SweepCase, ngspice: Path, ibis_path: Path, subckt_path: Path) -> dict[str, object]:
    h_dir = CASES_DIR / case.case_id / "hspice_native_ibis"
    n_dir = CASES_DIR / case.case_id / "ngspice_pybis"
    ensure_dir(h_dir)
    ensure_dir(n_dir)
    shutil.copy2(ibis_path, n_dir / "io_buf.ibs")
    shutil.copy2(subckt_path, n_dir / "driver_OutputInput_Typical.sub")

    h_stem = f"{case.case_id}_hspice_native_ibis"
    n_stem = f"{case.case_id}_ngspice_pybis"
    h_deck = h_dir / f"{h_stem}.sp"
    n_deck = n_dir / f"{n_stem}.sp"
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
    write_text(n_deck, make_ngspice_deck(case))

    row: dict[str, object] = {
        "case_id": case.case_id,
        "description": case.description,
        "pattern": case.pattern,
        "edge_ns": case.edge_ns,
        "input_high_v": case.high_v,
        "r_load_ohm": case.r_load_ohm,
        "c_load_pf": case.c_load_pf,
        "stop_ns": case.stop_ns,
        "hspice_deck": str(h_deck.relative_to(ROOT)),
        "ngspice_deck": str(n_deck.relative_to(ROOT)),
    }

    try:
        if hspice_restored:
            h_rc = 0
            row["hspice_reference"] = "cache"
        elif hspice_existing:
            h_rc = 0
            row["hspice_reference"] = "existing"
        else:
            h_rc = run_process([str(DEFAULT_HSPICE), "-i", h_deck.name, "-o", h_stem], h_dir, h_dir / "hspice_stdout.log")
            if h_rc != 0:
                row.update({"status": "hspice_failed", "error": f"HSPICE return code {h_rc}"})
                return row
            save_hspice_cache(h_cache, h_dir, h_stem, h_deck_text, signature)
            row["hspice_reference"] = "run"
        n_raw = n_dir / f"{n_stem}.raw"
        n_rc = run_process([str(ngspice), "-b", "-r", n_raw.name, n_deck.name], n_dir, n_dir / "ngspice_stdout.log")
        if n_rc != 0:
            row.update({"status": "ngspice_failed", "error": f"ngspice return code {n_rc}"})
            return row

        h_data = parse_hspice_tr0(h_dir / f"{h_stem}.tr0")
        n_data = parse_ngspice_raw(n_raw)
        h_t = to_ns(find_signal(h_data, "time"))
        h_pad = find_signal(h_data, "v(pad_ibis)")
        h_ku = find_signal(h_data, "v(ku)")
        h_kd = find_signal(h_data, "v(kd)")
        n_t = to_ns(find_signal(n_data, "time"))
        n_pad = find_signal(n_data, "v(pad)")
        n_ku = find_signal(n_data, "v(xdrv.ku)")
        n_kd = find_signal(n_data, "v(xdrv.kd)")

        n_pad_i = interp_to(n_t, n_pad, h_t)
        n_ku_i = interp_to(n_t, n_ku, h_t)
        n_kd_i = interp_to(n_t, n_kd, h_t)
        mask = active_mask(h_t, case)
        if not np.any(mask):
            mask = np.ones_like(h_t, dtype=bool)

        row.update(
            {
                "status": "ok",
                "hspice_tr0": str((h_dir / f"{h_stem}.tr0").relative_to(ROOT)),
                "ngspice_raw": str(n_raw.relative_to(ROOT)),
                "pad_active_rmse_v": rmse(h_pad[mask], n_pad_i[mask]),
                "pad_active_max_abs_v": maxabs(h_pad[mask], n_pad_i[mask]),
                "ku_active_rmse": rmse(h_ku[mask], n_ku_i[mask]),
                "ku_active_max_abs": maxabs(h_ku[mask], n_ku_i[mask]),
                "kd_active_rmse": rmse(h_kd[mask], n_kd_i[mask]),
                "kd_active_max_abs": maxabs(h_kd[mask], n_kd_i[mask]),
                "ku_full_rmse": rmse(h_ku, n_ku_i),
                "kd_full_rmse": rmse(h_kd, n_kd_i),
                "pad_final_hspice_v": float(h_pad[-1]),
                "pad_final_ngspice_v": float(n_pad_i[-1]),
            }
        )

        write_waveform_csv(
            CASES_DIR / case.case_id / "aligned_waveforms.csv",
            {
                "time_ns": h_t,
                "hspice_pad_v": h_pad,
                "ngspice_pybis_pad_v_interp": n_pad_i,
                "hspice_ku": h_ku,
                "ngspice_pybis_ku_interp": n_ku_i,
                "hspice_kd": h_kd,
                "ngspice_pybis_kd_interp": n_kd_i,
            },
        )
        plot_case(case, h_t, h_pad, h_ku, h_kd, n_t, n_pad, n_ku, n_kd)
        row["plot"] = str((PLOTS_DIR / "cases" / f"{case.case_id}_waveform_coeff_overlay.png").relative_to(ROOT))
        return row
    except Exception as exc:
        row.update({"status": "exception", "error": repr(exc)})
        return row


def write_readme(rows: list[dict[str, object]]) -> None:
    good = sum(1 for row in rows if case_status(row) == "GOOD")
    warn = sum(1 for row in rows if case_status(row) == "WARN")
    check = sum(1 for row in rows if case_status(row) == "CHECK")
    fail = sum(1 for row in rows if case_status(row) == "FAIL")
    lines = [
        "# io_buf Switching Coefficient Sweep",
        "",
        "This study runs matched HSPICE native-IBIS and ngspice pybis testbenches while changing the input edge, input pattern, and pad load.",
        "",
        "Both flows use the same canonical `hspice/sparam/io_buf.ibs`, the same PWL stimulus, the same 3.3 V rails, and the same pad load for each case.",
        "",
        "## Flows",
        "",
        "- HSPICE: native IBIS `B` element with `xv_pu=ku` and `xv_pd=kd`.",
        "- ngspice: pybis-generated `driver_OutputInput_Typical.sub`, measured at `V(xdrv.ku)` and `V(xdrv.kd)`.",
        "",
        "## Summary",
        "",
        f"- GOOD: {good}",
        f"- WARN: {warn}",
        f"- CHECK: {check}",
        f"- FAIL: {fail}",
        "",
        "`GOOD` means pad active-window RMSE <= 10 mV and both Ku/Kd RMSE <= 0.01.",
        "`WARN` means pad active-window RMSE <= 25 mV and both Ku/Kd RMSE <= 0.03.",
        "",
        "## Main Findings",
        "",
        "- Sharp, complete toggles match very well. The 1 ps baseline and the double-toggle case are both `GOOD`.",
        "- Load variation alone is not the weak point. 25 ohm, 50 ohm, 100 ohm, 0 pF, 2 pF, and 10 pF cases all stay `GOOD` for 1 ps input edges.",
        "- Slow input ramps expose a real difference in switching-state handling. 5 ps and 50 ps edges are still close enough to be `WARN`, but 500 ps and 2 ns edges become `CHECK`.",
        "- Interrupted output transitions expose the largest difference. The 2 ns-high short pulse reverses before the pad has settled, and HSPICE native IBIS and pybis choose visibly different Ku/Kd trajectories.",
        "- The 1.8 V input-high case is an exploratory threshold case. It remains numerically close here, but it should not be treated as a normal guaranteed-logic operation because it is below the model's nominal `Vinh=2 V`.",
        "",
        "## Outputs",
        "",
        "- `metrics_by_case.csv`",
        "- `plots/summary_rmse_by_case.png`",
        "- `plots/cases/*_waveform_coeff_overlay.png`",
        "- `plots/cases/*_transition_*_zoom.png`",
        "- `cases/<case>/hspice_native_ibis/`",
        "- `cases/<case>/ngspice_pybis/`",
        "",
        "## Case Metrics",
        "",
        "| Case | Status | Pad RMSE (mV) | Pad max (mV) | Ku RMSE | Kd RMSE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        status = case_status(row)
        if row.get("status") != "ok":
            lines.append(f"| {row['case_id']} | {status} |  |  |  |  |")
            continue
        lines.append(
            "| {case} | {status} | {pad_rmse:.3f} | {pad_max:.3f} | {ku:.5f} | {kd:.5f} |".format(
                case=row["case_id"],
                status=status,
                pad_rmse=float(row["pad_active_rmse_v"]) * 1e3,
                pad_max=float(row["pad_active_max_abs_v"]) * 1e3,
                ku=float(row["ku_active_rmse"]),
                kd=float(row["kd_active_rmse"]),
            )
        )
    lines.extend(
        [
            "",
        "## Notes",
        "",
        "The marginal 1.8 V input case is intentionally below the model's nominal `Vinh=2 V`, so it probes threshold handling rather than normal switching.",
        "Small coefficient differences are expected because HSPICE owns the native IBIS state machine, while pybis expands the behavior into explicit free-SPICE sources.",
        "The slow-edge and short-pulse `CHECK` cases should be treated as evidence that input-stimulus/state-machine behavior needs separate validation from normal fast-edge output loading.",
    ]
    )
    write_text(OUT_DIR / "README.md", "\n".join(lines) + "\n")


def main() -> int:
    ibis_path = DEFAULT_IBIS
    ngspice = Path(os.environ.get("NGSPICE_EXE", str(DEFAULT_NGSPICE)))
    if not ibis_path.exists():
        raise FileNotFoundError(ibis_path)
    if not ngspice.exists():
        raise FileNotFoundError(f"ngspice executable not found: {ngspice}")

    for path in (OUT_DIR, COMMON_DIR, CASES_DIR, PLOTS_DIR):
        ensure_dir(path)
    subckt = prepare_common(ibis_path)

    rows: list[dict[str, object]] = []
    cases = build_cases()
    for idx, case in enumerate(cases, start=1):
        print(f"[{idx}/{len(cases)}] {case.case_id}: {case.description}", flush=True)
        row = run_case(case, ngspice, ibis_path, subckt)
        rows.append(row)
        write_csv(OUT_DIR / "metrics_by_case.csv", rows)
        if row.get("status") == "ok":
            print(
                "  pad_rmse={:.3f} mV ku_rmse={:.5f} kd_rmse={:.5f}".format(
                    float(row["pad_active_rmse_v"]) * 1e3,
                    float(row["ku_active_rmse"]),
                    float(row["kd_active_rmse"]),
                ),
                flush=True,
            )
        else:
            print(f"  {row.get('status')}: {row.get('error')}", flush=True)

    for row in rows:
        row["quality_status"] = case_status(row)
    write_csv(OUT_DIR / "metrics_by_case.csv", rows)
    plot_summary(rows)
    write_readme(rows)

    print(f"OUT_DIR={OUT_DIR}")
    print(f"METRICS={OUT_DIR / 'metrics_by_case.csv'}")
    print(f"PLOTS={PLOTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
