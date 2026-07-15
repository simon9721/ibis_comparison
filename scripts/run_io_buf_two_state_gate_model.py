from __future__ import annotations

import argparse
import csv
import math
import shutil
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
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
if str(PYBIS_ROOT) not in sys.path:
    sys.path.insert(0, str(PYBIS_ROOT))

import run_io_buf_value_matched_replay_v2 as base  # noqa: E402
from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from pybis2spice import pybis2spice, subcircuit  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


OUT_DIR = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
COMMON_DIR = OUT_DIR / "common"
CASES_DIR = OUT_DIR / "cases"
FIGURES_DIR = OUT_DIR / "figures"
FIT_DIR = OUT_DIR / "fit_diagnostics"
DEFAULT_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
DEFAULT_IO_BUF_SP = ROOT / "models" / "io_buf.sp"
DEFAULT_MOS_MODEL = ROOT / "models" / "hspice_ngspice.mod"
DEFAULT_NGSPICE = default_ngspice(console=True)
DEFAULT_HSPICE = default_hspice()


@dataclass(frozen=True)
class Variant:
    variant_id: str
    label: str
    subcircuit_type: str
    save_diagnostics: bool = False


VARIANTS = [
    Variant("legacy", "ngspice legacy pybis", "InputDriven", False),
    Variant("value_match_v2", "ngspice value-match v2 balanced", "InputDrivenValueMatchedReplayV2Hybrid", True),
    Variant("two_state_identity", "ngspice two-state identity full", "InputDrivenTwoStateGateIdentityFull", True),
    Variant("two_state_pwl", "ngspice two-state PWL full", "InputDrivenTwoStateGatePwlFull", True),
    Variant("two_state_hybrid", "ngspice two-state PWL hybrid", "InputDrivenTwoStateGatePwlHybrid", True),
    Variant("two_state_directional", "ngspice two-state directional maps", "InputDrivenTwoStateGateDirectionalFull", True),
    Variant("two_state_directional_residual", "ngspice two-state directional + Kd residual", "InputDrivenTwoStateGateDirectionalResidualFull", True),
    Variant("two_state_directional_residual_recover_mean", "ngspice two-state residual + mean Kd recover", "InputDrivenTwoStateGateDirectionalResidualRecoverMeanFull", True),
    Variant("two_state_directional_residual_recover_fast", "ngspice two-state residual + fast Kd recover", "InputDrivenTwoStateGateDirectionalResidualRecoverFastFull", True),
]


COLORS = {
    "input": "#222222",
    "hspice_native": "#1f77b4",
    "hspice_transistor": "#6f2dbd",
    "legacy": "#ff7f0e",
    "value_match_v2": "#2ca02c",
    "two_state_identity": "#17becf",
    "two_state_pwl": "#d62728",
    "two_state_hybrid": "#9467bd",
    "two_state_directional": "#8c564b",
    "two_state_directional_residual": "#e377c2",
    "two_state_directional_residual_recover_mean": "#bcbd22",
    "two_state_directional_residual_recover_fast": "#7f7f7f",
    "diag_a": "#2a9d8f",
    "diag_b": "#e76f51",
    "diag_c": "#457b9d",
    "diag_d": "#7f7f7f",
}


def configure_base_globals() -> None:
    base.OUT_DIR = OUT_DIR
    base.COMMON_DIR = COMMON_DIR
    base.CASES_DIR = CASES_DIR
    base.FIGURES_DIR = FIGURES_DIR
    base.VARIANTS = VARIANTS


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


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_cases(include_low: bool = True) -> list[base.StudyCase]:
    return base.build_cases(include_low=include_low)


def selected_cases(case_ids: list[str], include_low: bool = True) -> list[base.StudyCase]:
    return base.selected_cases(case_ids, include_low=include_low)


def make_ngspice_deck(case: base.StudyCase, variant: Variant) -> str:
    extra = ""
    if variant.save_diagnostics:
        extra = (
            " V(xdrv.kutarget) V(xdrv.kdtarget)"
            " V(xdrv.kuleg) V(xdrv.kdleg)"
            " V(xdrv.gup) V(xdrv.gdn)"
            " V(xdrv.guptarget) V(xdrv.gdntarget)"
            " V(xdrv.kugate) V(xdrv.kdgate)"
            " V(xdrv.kugate_on) V(xdrv.kugate_off)"
            " V(xdrv.kdgate_on) V(xdrv.kdgate_off)"
            " V(xdrv.gdnrate) V(xdrv.kdres) V(xdrv.kdres_table)"
            " V(xdrv.pdrecoveredge) V(xdrv.pdnormalfall)"
            " V(xdrv.pdonp_norm) V(xdrv.pdonp_recover)"
            " V(xdrv.hshort_high_recovery) V(xdrv.hnx)"
            " V(xdrv.h2stateactive) V(xdrv.koverlap)"
            " V(xdrv.vmarg) V(xdrv.vmstart_latch) V(xdrv.vmelapsed)"
            " V(xdrv.start_disagree) V(xdrv.match_ambiguous)"
        )
    return f"""* io_buf {variant.label} two-state gate study
* Sweep case: {case.case_id}
* {case.description}
.title io_buf ngspice {variant.label} {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{base.pwl_text(case)}

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 {base.fmt_num(case.r_load_ohm)}
{base.c_load_line("pad", case.c_load_pf).rstrip()}

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){extra}
.tran 0.001n {base.spice_time_ns(case.stop_ns)}
.end
"""


def load_io_buf_k_tables(ibis_path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    ibis = pybis2spice.get_ibis_model_ecdtools(str(ibis_path))
    data_model = pybis2spice.DataModel(ibis, model_name="driver", component_name="MCM Driver 1")
    corner_idx = subcircuit.convert_corner_str_to_index("Typical") + 1
    kr = pybis2spice.solve_k_params_output(data_model, corner=corner_idx, waveform_type="Rising")
    kf = pybis2spice.solve_k_params_output(data_model, corner=corner_idx, waveform_type="Falling")
    kr = pybis2spice.compress_param(kr, threshold=1e-3)
    kf = pybis2spice.compress_param(kf, threshold=1e-3)
    fit = subcircuit.gate_state_fit(kr, kf)
    return kr, kf, fit


def interp_gate_map(g: np.ndarray, fit: dict[str, object], coeff: str, identity: bool = False) -> np.ndarray:
    g = np.clip(np.asarray(g, dtype=float), 0.0, 1.0)
    if coeff == "ku":
        if identity:
            return float(fit["ku_off"]) + (float(fit["ku_on"]) - float(fit["ku_off"])) * g
        return np.interp(g, np.asarray(fit["ku_map_x"], dtype=float), np.asarray(fit["ku_map_y"], dtype=float))
    if identity:
        return float(fit["kd_off"]) + (float(fit["kd_on"]) - float(fit["kd_off"])) * g
    return np.interp(g, np.asarray(fit["kd_map_x"], dtype=float), np.asarray(fit["kd_map_y"], dtype=float))


def rmse(ref: np.ndarray, dut: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(dut) - np.asarray(ref)) ** 2))) if len(ref) else float("nan")


def maxabs(ref: np.ndarray, dut: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(dut) - np.asarray(ref)))) if len(ref) else float("nan")


def reconstruction_rows_and_data(kr: np.ndarray, kf: np.ndarray, fit: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, np.ndarray]]:
    dfit = subcircuit.two_state_directional_gate_fit(kr, kf)
    tr = np.asarray(kr[:, subcircuit._TIME], dtype=float) * 1e9
    tf = np.asarray(kf[:, subcircuit._TIME], dtype=float) * 1e9
    data: dict[str, np.ndarray] = {
        "tr": tr,
        "tf": tf,
        "ku_rise_orig": np.asarray(kr[:, subcircuit._KU], dtype=float),
        "kd_rise_orig": np.asarray(kr[:, subcircuit._KD], dtype=float),
        "ku_fall_orig": np.asarray(kf[:, subcircuit._KU], dtype=float),
        "kd_fall_orig": np.asarray(kf[:, subcircuit._KD], dtype=float),
    }
    data["gup_rise"] = subcircuit.gate_response(tr, fit["pu_on_delay"], fit["pu_on_tau"], 0.0, 1.0)
    data["gup_fall"] = subcircuit.gate_response(tf, fit["pu_off_delay"], fit["pu_off_tau"], 1.0, 0.0)
    data["gdn_rise"] = subcircuit.gate_response(tr, fit["pd_off_delay"], fit["pd_off_tau"], 1.0, 0.0)
    data["gdn_fall"] = subcircuit.gate_response(tf, fit["pd_on_delay"], fit["pd_on_tau"], 0.0, 1.0)
    for identity in [False, True]:
        tag = "identity" if identity else "pwl"
        data[f"ku_rise_{tag}"] = interp_gate_map(data["gup_rise"], fit, "ku", identity)
        data[f"ku_fall_{tag}"] = interp_gate_map(data["gup_fall"], fit, "ku", identity)
        data[f"kd_rise_{tag}"] = interp_gate_map(data["gdn_rise"], fit, "kd", identity)
        data[f"kd_fall_{tag}"] = interp_gate_map(data["gdn_fall"], fit, "kd", identity)
    data["ku_rise_directional"] = np.interp(data["gup_rise"], dfit["ku_on_map_x"], dfit["ku_on_map_y"])
    data["ku_fall_directional"] = np.interp(data["gup_fall"], dfit["ku_off_map_x"], dfit["ku_off_map_y"])
    data["kd_rise_directional"] = np.interp(data["gdn_rise"], dfit["kd_off_map_x"], dfit["kd_off_map_y"])
    data["kd_fall_directional"] = np.interp(data["gdn_fall"], dfit["kd_on_map_x"], dfit["kd_on_map_y"])
    data["gdn_rise_rate"] = subcircuit.gate_state_rate(tr, dfit["pd_off_delay"], dfit["pd_off_tau"], 1.0, 0.0)
    data["gdn_fall_rate"] = subcircuit.gate_state_rate(tf, dfit["pd_on_delay"], dfit["pd_on_tau"], 0.0, 1.0)
    data["kd_rise_rate_residual"] = dfit["kd_rate_gain_ns"] * data["gdn_rise_rate"]
    data["kd_fall_rate_residual"] = dfit["kd_rate_gain_ns"] * data["gdn_fall_rate"]
    data["kd_rise_table_residual"] = np.asarray(dfit["kd_rise_residual"], dtype=float)
    data["kd_fall_table_residual"] = np.asarray(dfit["kd_fall_residual"], dtype=float)
    data["kd_rise_directional_residual"] = data["kd_rise_directional"] + data["kd_rise_table_residual"] + data["kd_rise_rate_residual"]
    data["kd_fall_directional_residual"] = data["kd_fall_directional"] + data["kd_fall_table_residual"] + data["kd_fall_rate_residual"]
    data["ku_rise_directional_residual"] = data["ku_rise_directional"]
    data["ku_fall_directional_residual"] = data["ku_fall_directional"]
    rows: list[dict[str, object]] = []
    for tag in ["pwl", "identity", "directional", "directional_residual"]:
        for name in ["ku_rise", "ku_fall", "kd_rise", "kd_fall"]:
            orig = data[f"{name}_orig"]
            recon = data[f"{name}_{tag}"]
            rows.append(
                {
                    "candidate": tag,
                    "table": name,
                    "rmse": rmse(orig, recon),
                    "max_error": maxabs(orig, recon),
                }
            )
    return rows, data


def write_fit_diagnostics(ibis_path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    ensure_dir(FIT_DIR)
    kr, kf, fit = load_io_buf_k_tables(ibis_path)
    recon_rows, data = reconstruction_rows_and_data(kr, kf, fit)
    fit_rows = [
        {
            "model": "io_buf",
            "corner": "Typical",
            "ku_off": fit["ku_off"],
            "ku_on": fit["ku_on"],
            "kd_off": fit["kd_off"],
            "kd_on": fit["kd_on"],
            "pu_on_delay_ns": fit["pu_on_delay"],
            "pu_off_delay_ns": fit["pu_off_delay"],
            "pd_on_delay_ns": fit["pd_on_delay"],
            "pd_off_delay_ns": fit["pd_off_delay"],
            "pu_on_tau_ns": fit["pu_on_tau"],
            "pu_off_tau_ns": fit["pu_off_tau"],
            "pd_on_tau_ns": fit["pd_on_tau"],
            "pd_off_tau_ns": fit["pd_off_tau"],
            "interrupt_window_ns": fit["interrupt_window_ns"],
        }
    ]
    all_pwl_errors = [float(row["rmse"]) for row in recon_rows if row["candidate"] == "pwl"]
    all_pwl_max = [float(row["max_error"]) for row in recon_rows if row["candidate"] == "pwl"]
    all_directional_errors = [float(row["rmse"]) for row in recon_rows if row["candidate"] == "directional"]
    all_directional_max = [float(row["max_error"]) for row in recon_rows if row["candidate"] == "directional"]
    all_residual_errors = [float(row["rmse"]) for row in recon_rows if row["candidate"] == "directional_residual"]
    all_residual_max = [float(row["max_error"]) for row in recon_rows if row["candidate"] == "directional_residual"]
    dfit = subcircuit.two_state_directional_gate_fit(kr, kf)
    fit_rows[0]["pwl_reconstruction_rmse_max"] = max(all_pwl_errors)
    fit_rows[0]["pwl_reconstruction_max_error_max"] = max(all_pwl_max)
    fit_rows[0]["directional_reconstruction_rmse_max"] = max(all_directional_errors)
    fit_rows[0]["directional_reconstruction_max_error_max"] = max(all_directional_max)
    fit_rows[0]["directional_residual_reconstruction_rmse_max"] = max(all_residual_errors)
    fit_rows[0]["directional_residual_reconstruction_max_error_max"] = max(all_residual_max)
    fit_rows[0]["kd_rate_gain_ns"] = dfit["kd_rate_gain_ns"]
    fit_rows[0]["pwl_table_gate"] = (
        "PASS" if max(all_pwl_errors) <= 0.02 and max(all_pwl_max) <= 0.08 else "FAIL"
    )
    fit_rows[0]["directional_table_gate"] = (
        "PASS" if max(all_directional_errors) <= 0.02 and max(all_directional_max) <= 0.08 else "FAIL"
    )
    fit_rows[0]["directional_residual_table_gate"] = (
        "PASS" if max(all_residual_errors) <= 0.02 and max(all_residual_max) <= 0.08 else "FAIL"
    )
    fit_rows[0]["normal_table_gate"] = fit_rows[0]["directional_residual_table_gate"]
    write_csv(OUT_DIR / "gate_fit_summary.csv", fit_rows)
    write_csv(OUT_DIR / "normal_k_reconstruction.csv", recon_rows)
    plot_fit_diagnostics(fit, data)
    return fit_rows, recon_rows


def plot_fit_diagnostics(fit: dict[str, object], data: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), constrained_layout=True)
    specs = [
        ("tr", "ku_rise", "Ku rising"),
        ("tf", "ku_fall", "Ku falling"),
        ("tr", "kd_rise", "Kd rising"),
        ("tf", "kd_fall", "Kd falling"),
    ]
    for ax, (tkey, prefix, title) in zip(axes.flat, specs):
        t = data[tkey]
        ax.plot(t, data[f"{prefix}_orig"], color="#1f77b4", lw=2.0, label="original table")
        ax.plot(t, data[f"{prefix}_pwl"], color="#d62728", lw=1.8, label="two-state PWL")
        ax.plot(t, data[f"{prefix}_identity"], color="#17becf", lw=1.4, label="identity diagnostic")
        ax.plot(t, data[f"{prefix}_directional"], color="#8c564b", lw=1.8, label="directional maps")
        ax.plot(t, data[f"{prefix}_directional_residual"], color="#e377c2", lw=1.4, label="directional + Kd residual")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Table time (ns)")
        ax.set_ylabel(prefix.split("_")[0].upper())
        ax.grid(True, color="#d8dde6", alpha=0.85)
        ax.legend(frameon=False)
    fig.suptitle("Original complete-edge Ku/Kd tables vs two-state reconstruction", fontweight="bold")
    fig.savefig(FIT_DIR / "ku_kd_table_reconstruction.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    axes[0].scatter(data["gup_rise"], data["ku_rise_orig"], s=18, color="#1f77b4", label="rise cloud")
    axes[0].scatter(data["gup_fall"], data["ku_fall_orig"], s=18, color="#ff7f0e", label="fall cloud")
    axes[0].plot(fit["ku_map_x"], fit["ku_map_y"], color="#d62728", lw=2.2, label="PWL map")
    axes[0].set_title("f_pu(GUP) map", loc="left", fontweight="bold")
    axes[0].set_xlabel("GUP")
    axes[0].set_ylabel("Ku")
    axes[1].scatter(data["gdn_rise"], data["kd_rise_orig"], s=18, color="#1f77b4", label="rise cloud")
    axes[1].scatter(data["gdn_fall"], data["kd_fall_orig"], s=18, color="#ff7f0e", label="fall cloud")
    axes[1].plot(fit["kd_map_x"], fit["kd_map_y"], color="#d62728", lw=2.2, label="PWL map")
    axes[1].set_title("f_pd(GDN) map", loc="left", fontweight="bold")
    axes[1].set_xlabel("GDN")
    axes[1].set_ylabel("Kd")
    for ax in axes:
        ax.grid(True, color="#d8dde6", alpha=0.85)
        ax.legend(frameon=False)
    fig.suptitle("Gate-state map collapse check", fontweight="bold")
    fig.savefig(FIT_DIR / "gate_to_coefficient_maps.png", dpi=180)
    plt.close(fig)

    dfit = subcircuit.two_state_directional_gate_fit(
        np.column_stack([data["tr"] * 1e-9, data["ku_rise_orig"], data["kd_rise_orig"]]),
        np.column_stack([data["tf"] * 1e-9, data["ku_fall_orig"], data["kd_fall_orig"]]),
    )
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), constrained_layout=True)
    axes[0, 0].plot(dfit["ku_on_map_x"], dfit["ku_on_map_y"], color="#1f77b4", lw=2.0, label="Ku on map")
    axes[0, 0].plot(dfit["ku_off_map_x"], dfit["ku_off_map_y"], color="#ff7f0e", lw=2.0, label="Ku off map")
    axes[0, 1].plot(dfit["kd_off_map_x"], dfit["kd_off_map_y"], color="#1f77b4", lw=2.0, label="Kd off map")
    axes[0, 1].plot(dfit["kd_on_map_x"], dfit["kd_on_map_y"], color="#ff7f0e", lw=2.0, label="Kd on map")
    axes[1, 0].plot(data["tr"], data["gdn_rise_rate"], color="#1f77b4", lw=1.8, label="dGDN/dt during rising input")
    axes[1, 0].plot(data["tf"], data["gdn_fall_rate"], color="#ff7f0e", lw=1.8, label="dGDN/dt during falling input")
    axes[1, 1].plot(data["tr"], data["kd_rise_directional_residual"] - data["kd_rise_directional"], color="#1f77b4", lw=1.8, label="Kd residual rise")
    axes[1, 1].plot(data["tf"], data["kd_fall_directional_residual"] - data["kd_fall_directional"], color="#ff7f0e", lw=1.8, label="Kd residual fall")
    for ax in axes.flat:
        ax.grid(True, color="#d8dde6", alpha=0.85)
        ax.legend(frameon=False)
    axes[0, 0].set_title("Direction-specific Ku maps", loc="left", fontweight="bold")
    axes[0, 1].set_title("Direction-specific Kd maps", loc="left", fontweight="bold")
    axes[1, 0].set_title("GDN rate diagnostic", loc="left", fontweight="bold")
    axes[1, 1].set_title("Kd residual contribution", loc="left", fontweight="bold")
    axes[0, 0].set_xlabel("GUP")
    axes[0, 1].set_xlabel("GDN")
    axes[1, 0].set_xlabel("Table time (ns)")
    axes[1, 1].set_xlabel("Table time (ns)")
    fig.suptitle("Direction-specific map and residual diagnostics", fontweight="bold")
    fig.savefig(FIT_DIR / "directional_maps_and_residual.png", dpi=180)
    plt.close(fig)


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


def run_ngspice_variant(case: base.StudyCase, variant: Variant, model_path: Path, ngspice: Path, timeout_s: int):
    out_dir = CASES_DIR / case.case_id / f"ngspice_{variant.variant_id}"
    ensure_dir(out_dir)
    shutil.copy2(model_path, out_dir / "driver_OutputInput_Typical.sub")
    stem = f"{case.case_id}_ngspice_{variant.variant_id}"
    deck = out_dir / f"{stem}.sp"
    raw = out_dir / f"{stem}.raw"
    write_text(deck, make_ngspice_deck(case, variant))
    rc = base.run_process([str(ngspice), "-b", "-r", raw.name, deck.name], out_dir, out_dir / "ngspice_stdout.log", timeout_s)
    if rc != 0:
        if raw.exists():
            raw.unlink()
        raise RuntimeError(f"ngspice {variant.variant_id} {case.case_id} failed with return code {rc}; see {out_dir / 'ngspice_stdout.log'}")
    return parse_ngspice_raw(raw), deck, raw


def score_ngspice_row(case: base.StudyCase, variant: Variant, h_native: dict[str, np.ndarray], n_data: dict[str, np.ndarray], deck: Path, raw: Path) -> dict[str, object]:
    row = base.score_ngspice_row(case, variant, h_native, n_data, deck, raw)
    h_t = base.to_ns(base.find_signal(h_native, "time"))
    n_t = base.to_ns(base.find_signal(n_data, "time"))
    mask = base.active_mask(h_t, case)
    for name in [
        "gup", "gdn", "guptarget", "gdntarget", "kugate", "kdgate", "kuleg", "kdleg",
        "kugate_on", "kugate_off", "kdgate_on", "kdgate_off", "gdnrate", "kdres", "kdres_table",
        "pdrecoveredge", "pdnormalfall", "pdonp_norm", "pdonp_recover", "hshort_high_recovery",
        "hnx", "h2stateactive", "koverlap",
    ]:
        sig = base.optional_signal(n_data, n_t, h_t, f"v(xdrv.{name})", f"v(xdrv:{name})")
        if sig is None:
            continue
        row[f"{name}_min"] = base.finite_min(sig, mask)
        row[f"{name}_max"] = base.finite_max(sig, mask)
    row["coeff_range_ok"] = bool(
        float(row.get("ku_min", 0.0)) >= -0.2
        and float(row.get("ku_peak", 0.0)) <= 1.2
        and float(row.get("kd_min", 0.0)) >= -0.2
        and float(row.get("kd_max", 0.0)) <= 1.2
    )
    return row


def load_waveforms(case: base.StudyCase) -> dict[str, np.ndarray]:
    h = parse_hspice_tr0(CASES_DIR / case.case_id / "hspice_native_ibis" / f"{case.case_id}_hspice_native_ibis.tr0")
    sp = parse_hspice_tr0(CASES_DIR / case.case_id / "hspice_transistor_sp" / f"{case.case_id}_hspice_transistor_sp.tr0")
    t = base.to_ns(base.find_signal(h, "time"))
    data: dict[str, np.ndarray] = {
        "time_ns": t,
        "input": base.input_waveform(case, t),
        "hspice_native_pad": base.find_signal(h, "v(pad_ibis)"),
        "hspice_ku": base.find_signal(h, "v(ku)"),
        "hspice_kd": base.find_signal(h, "v(kd)"),
        "hspice_transistor_pad": base.interp_to(base.to_ns(base.find_signal(sp, "time")), base.find_signal(sp, "v(pad_sp)"), t),
    }
    for variant in VARIANTS:
        raw = CASES_DIR / case.case_id / f"ngspice_{variant.variant_id}" / f"{case.case_id}_ngspice_{variant.variant_id}.raw"
        if not raw.exists():
            continue
        n = parse_ngspice_raw(raw)
        nt = base.to_ns(base.find_signal(n, "time"))
        prefix = variant.variant_id
        data[f"{prefix}_pad"] = base.interp_to(nt, base.find_signal(n, "v(pad)"), t)
        data[f"{prefix}_ku"] = base.interp_to(nt, base.find_signal(n, "v(xdrv.ku)", "v(xdrv:ku)"), t)
        data[f"{prefix}_kd"] = base.interp_to(nt, base.find_signal(n, "v(xdrv.kd)", "v(xdrv:kd)"), t)
        for name in [
            "gup", "gdn", "guptarget", "gdntarget", "kugate", "kdgate", "kuleg", "kdleg",
            "kugate_on", "kugate_off", "kdgate_on", "kdgate_off", "gdnrate", "kdres", "kdres_table",
            "pdrecoveredge", "pdnormalfall", "pdonp_norm", "pdonp_recover", "hshort_high_recovery",
            "hnx", "h2stateactive", "koverlap",
        ]:
            sig = base.optional_signal(n, nt, t, f"v(xdrv.{name})", f"v(xdrv:{name})")
            if sig is not None:
                data[f"{prefix}_{name}"] = sig
    return data


def plot_case_figures(case: base.StudyCase) -> None:
    data = load_waveforms(case)
    t = data["time_ns"]
    out_dir = FIGURES_DIR / case.case_id
    ensure_dir(out_dir)
    xlim = base.xlim_for_case(case)
    variant_specs = [
        ("legacy", "legacy pybis", COLORS["legacy"]),
        ("value_match_v2", "value-match v2", COLORS["value_match_v2"]),
        ("two_state_identity", "two-state identity", COLORS["two_state_identity"]),
        ("two_state_pwl", "two-state PWL", COLORS["two_state_pwl"]),
        ("two_state_hybrid", "two-state hybrid", COLORS["two_state_hybrid"]),
        ("two_state_directional", "two-state directional", COLORS["two_state_directional"]),
        ("two_state_directional_residual", "two-state residual", COLORS["two_state_directional_residual"]),
        ("two_state_directional_residual_recover_mean", "residual mean recover", COLORS["two_state_directional_residual_recover_mean"]),
        ("two_state_directional_residual_recover_fast", "residual fast recover", COLORS["two_state_directional_residual_recover_fast"]),
    ]

    fig, ax = plt.subplots(figsize=(10.8, 5.0), constrained_layout=True)
    scale = max(float(np.nanmax(data["hspice_native_pad"])), 1.0)
    ax.plot(t, data["input"] / case.high_v * scale, color=COLORS["input"], lw=1.4, alpha=0.55, label="input command (scaled)")
    ax.plot(t, data["hspice_native_pad"], color=COLORS["hspice_native"], lw=2.0, label="HSPICE native IBIS pad")
    ax.plot(t, data["hspice_transistor_pad"], color=COLORS["hspice_transistor"], lw=1.9, label="HSPICE io_buf.sp pad")
    for variant_id, label, color in variant_specs:
        if f"{variant_id}_pad" in data:
            ax.plot(t, data[f"{variant_id}_pad"], color=color, lw=1.6, label=f"{label} pad")
    base.mark_commands(ax, case)
    ax.set_xlim(*xlim)
    base.style(ax, "Voltage (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_title(f"{case.case_id}: input and pad overlay", loc="left", fontweight="bold")
    ax.legend(loc="best", ncol=2, frameon=False)
    fig.savefig(out_dir / "01_input_pad_overlay.png", dpi=180)
    plt.close(fig)

    for coeff, ylabel, filename in [("ku", "Ku", "02_ku_overlay.png"), ("kd", "Kd", "03_kd_overlay.png")]:
        fig, ax = plt.subplots(figsize=(10.8, 4.4), constrained_layout=True)
        ax.plot(t, data[f"hspice_{coeff}"], color=COLORS["hspice_native"], lw=2.0, label=f"HSPICE native IBIS {ylabel}")
        for variant_id, label, color in variant_specs:
            if f"{variant_id}_{coeff}" in data:
                ax.plot(t, data[f"{variant_id}_{coeff}"], color=color, lw=1.55, label=f"{label} {ylabel}")
        base.mark_commands(ax, case)
        ax.set_xlim(*xlim)
        ax.set_ylim(-0.15, 1.18)
        base.style(ax, ylabel)
        ax.set_xlabel("Time (ns)")
        ax.set_title(f"{case.case_id}: {ylabel} overlay", loc="left", fontweight="bold")
        ax.legend(loc="best", frameon=False)
        fig.savefig(out_dir / filename, dpi=180)
        plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(10.8, 8.0), sharex=True, constrained_layout=True)
    for ax in axes:
        base.mark_commands(ax, case)
        ax.set_xlim(*xlim)
    prefix = "two_state_directional_residual_recover_mean" if "two_state_directional_residual_recover_mean_gup" in data else (
        "two_state_directional_residual" if "two_state_directional_residual_gup" in data else "two_state_pwl"
    )
    if f"{prefix}_gup" in data:
        axes[0].plot(t, data[f"{prefix}_gup"], color=COLORS["diag_a"], lw=1.6, label="GUP")
        axes[0].plot(t, data[f"{prefix}_gdn"], color=COLORS["diag_b"], lw=1.6, label="GDN")
        axes[0].plot(t, data[f"{prefix}_guptarget"], color=COLORS["diag_a"], lw=1.0, alpha=0.55, label="GUPTARGET")
        axes[0].plot(t, data[f"{prefix}_gdntarget"], color=COLORS["diag_b"], lw=1.0, alpha=0.55, label="GDNTARGET")
        axes[1].plot(t, data[f"{prefix}_kugate"], color=COLORS["two_state_pwl"], lw=1.6, label="KUGATE")
        axes[1].plot(t, data[f"{prefix}_kdgate"], color=COLORS["two_state_hybrid"], lw=1.6, label="KDGATE")
        axes[1].plot(t, data[f"{prefix}_kuleg"], color=COLORS["legacy"], lw=1.1, alpha=0.7, label="KULEG")
        axes[1].plot(t, data[f"{prefix}_kdleg"], color=COLORS["value_match_v2"], lw=1.1, alpha=0.7, label="KDLEG")
        axes[2].plot(t, data.get(f"{prefix}_h2stateactive", np.zeros_like(t)), color=COLORS["diag_c"], lw=1.4, label="H2STATEACTIVE")
        axes[2].plot(t, data.get(f"{prefix}_hshort_high_recovery", np.zeros_like(t)), color=COLORS["two_state_directional_residual_recover_mean"], lw=1.3, label="HSHORT_HIGH_RECOVERY")
        axes[2].plot(t, data.get(f"{prefix}_pdonp_recover", np.zeros_like(t)), color=COLORS["two_state_directional_residual_recover_fast"], lw=1.0, alpha=0.8, label="PDONP_RECOVER")
        axes[2].plot(t, data.get(f"{prefix}_koverlap", np.zeros_like(t)), color=COLORS["diag_d"], lw=1.4, label="KOVERLAP")
        if f"{prefix}_kdres" in data:
            axes[2].plot(t, data[f"{prefix}_kdres"], color=COLORS["two_state_directional_residual"], lw=1.2, label="KDRES")
    for ax, ylabel in zip(axes, ["Gate state", "Coeff target", "Flag / overlap"]):
        base.style(ax, ylabel)
        ax.legend(loc="best", ncol=4, frameon=False)
    axes[-1].set_xlabel("Time (ns)")
    fig.suptitle(f"{case.case_id}: two-state gate diagnostics", fontweight="bold")
    fig.savefig(out_dir / "04_gate_state_diagnostics.png", dpi=180)
    plt.close(fig)

    metric_lookup = {(row.get("case_id"), row.get("flow")): row for row in read_csv(OUT_DIR / "candidate_metrics.csv")}
    metrics = [
        ("pad_active_rmse_v", "Pad RMSE (mV)", 1e3),
        ("ku_active_rmse", "Ku RMSE", 1.0),
        ("kd_active_rmse", "Kd RMSE", 1.0),
        ("ku_peak", "Ku peak", 1.0),
        ("kd_min", "Kd minimum", 1.0),
    ]
    flows = [spec[0] for spec in variant_specs]
    labels = [spec[1] for spec in variant_specs]
    colors = [spec[2] for spec in variant_specs]
    fig, axes = plt.subplots(len(metrics), 1, figsize=(11.2, 10.0), sharex=True, constrained_layout=True)
    x = np.arange(len(flows))
    for ax, (key, ylabel, scale_factor) in zip(axes, metrics):
        values = []
        for flow in flows:
            value = metric_lookup.get((case.case_id, f"ngspice_{flow}"), {}).get(key, "")
            try:
                values.append(float(value) * scale_factor)
            except (TypeError, ValueError):
                values.append(np.nan)
        ax.bar(x, values, color=colors)
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", color="#d8dde6")
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(labels, rotation=18, ha="right")
    fig.suptitle(f"{case.case_id}: two-state gate summary", fontweight="bold")
    fig.savefig(out_dir / "05_summary_bars.png", dpi=180)
    plt.close(fig)


def plot_summary(rows: list[dict[str, object]]) -> None:
    lookup = {(str(row.get("case_id")), str(row.get("flow"))): row for row in rows}
    cases = build_cases(include_low=True)
    flows = [
        ("ngspice_legacy", "legacy", COLORS["legacy"]),
        ("ngspice_value_match_v2", "value-match v2", COLORS["value_match_v2"]),
        ("ngspice_two_state_identity", "identity", COLORS["two_state_identity"]),
        ("ngspice_two_state_pwl", "PWL full", COLORS["two_state_pwl"]),
        ("ngspice_two_state_hybrid", "PWL hybrid", COLORS["two_state_hybrid"]),
        ("ngspice_two_state_directional", "directional", COLORS["two_state_directional"]),
        ("ngspice_two_state_directional_residual", "residual", COLORS["two_state_directional_residual"]),
        ("ngspice_two_state_directional_residual_recover_mean", "mean recover", COLORS["two_state_directional_residual_recover_mean"]),
        ("ngspice_two_state_directional_residual_recover_fast", "fast recover", COLORS["two_state_directional_residual_recover_fast"]),
    ]
    metrics = [
        ("pad_active_rmse_v", "Pad RMSE (mV)", 1e3),
        ("ku_active_rmse", "Ku RMSE", 1.0),
        ("kd_active_rmse", "Kd RMSE", 1.0),
    ]
    fig, axes = plt.subplots(len(metrics), 1, figsize=(12.0, 9.0), sharex=True, constrained_layout=True)
    x = np.arange(len(cases))
    width = min(0.12, 0.78 / max(len(flows), 1))
    offset_center = 0.5 * (len(flows) - 1)
    for ax, (key, ylabel, scale_factor) in zip(axes, metrics):
        for idx, (flow, label, color) in enumerate(flows):
            values = []
            for case in cases:
                value = lookup.get((case.case_id, flow), {}).get(key, "")
                try:
                    values.append(float(value) * scale_factor)
                except (TypeError, ValueError):
                    values.append(np.nan)
            ax.bar(x + (idx - offset_center) * width, values, width=width, label=label, color=color)
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", color="#d8dde6")
    axes[0].legend(frameon=False, ncol=3)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels([case.case_id for case in cases], rotation=18, ha="right")
    fig.suptitle("Two-state gate model summary", fontweight="bold")
    ensure_dir(FIGURES_DIR)
    fig.savefig(FIGURES_DIR / "summary_bars.png", dpi=180)
    plt.close(fig)


def crossing_time(t_ns: np.ndarray, y: np.ndarray, level: float, start_ns: float, direction: str) -> float:
    mask = (t_ns >= start_ns) & np.isfinite(y)
    tt = np.asarray(t_ns[mask], dtype=float)
    yy = np.asarray(y[mask], dtype=float)
    if len(tt) < 2:
        return float("nan")
    delta = yy - level
    if direction == "rising":
        idx = np.where((delta[:-1] < 0.0) & (delta[1:] >= 0.0))[0]
    else:
        idx = np.where((delta[:-1] > 0.0) & (delta[1:] <= 0.0))[0]
    if len(idx) == 0:
        return float("nan")
    i = int(idx[0])
    if yy[i + 1] == yy[i]:
        return float(tt[i])
    return float(tt[i] + (level - yy[i]) * (tt[i + 1] - tt[i]) / (yy[i + 1] - yy[i]))


def window_stats(t_ns: np.ndarray, err: np.ndarray, start_ns: float, end_ns: float) -> dict[str, float]:
    if not (math.isfinite(start_ns) and math.isfinite(end_ns)) or end_ns <= start_ns:
        return {"rmse": float("nan"), "mean_abs": float("nan"), "max_abs": float("nan"), "sse": 0.0, "duration_ns": 0.0}
    mask = (t_ns >= start_ns) & (t_ns <= end_ns) & np.isfinite(err)
    if not np.any(mask):
        return {"rmse": float("nan"), "mean_abs": float("nan"), "max_abs": float("nan"), "sse": 0.0, "duration_ns": end_ns - start_ns}
    values = np.asarray(err[mask], dtype=float)
    return {
        "rmse": float(np.sqrt(np.mean(values * values))),
        "mean_abs": float(np.mean(np.abs(values))),
        "max_abs": float(np.max(np.abs(values))),
        "sse": float(np.sum(values * values)),
        "duration_ns": float(end_ns - start_ns),
    }


def write_kd_recovery_window_diagnostics() -> list[dict[str, object]]:
    """
    Splits short-high Kd error into an onset-dominated window and a post-50% shape window.

    Window A follows the requested diagnostic: reverse edge to the model Kd 50%
    recovery crossing. Window B starts after both HSPICE and the model are past
    50% recovered. If Window B still carries large error after timing is nearly
    corrected, recovery shape is also wrong.
    """
    out_dir = OUT_DIR / "kd_recovery_diagnostics"
    ensure_dir(out_dir)
    short_high_cases = [case for case in build_cases(include_low=True) if case.pattern == "short_high"]
    flows = [
        "ngspice_legacy",
        "ngspice_two_state_directional_residual",
        "ngspice_two_state_directional_residual_recover_mean",
        "ngspice_two_state_directional_residual_recover_fast",
    ]
    rows: list[dict[str, object]] = []
    for case in short_high_cases:
        h = parse_hspice_tr0(CASES_DIR / case.case_id / "hspice_native_ibis" / f"{case.case_id}_hspice_native_ibis.tr0")
        h_t = base.to_ns(base.find_signal(h, "time"))
        h_kd = base.find_signal(h, "v(kd)")
        _, reverse_ns = base.command_times(case)
        active_end_ns = max(end for _, end in base.transition_windows(case))
        h_rec50_ns = crossing_time(h_t, h_kd, 0.5, reverse_ns, "rising")
        for flow in flows:
            variant_id = flow.removeprefix("ngspice_")
            raw = CASES_DIR / case.case_id / flow / f"{case.case_id}_{flow}.raw"
            if not raw.exists():
                continue
            n = parse_ngspice_raw(raw)
            n_t = base.to_ns(base.find_signal(n, "time"))
            n_kd = base.interp_to(n_t, base.find_signal(n, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)
            err = n_kd - h_kd
            model_rec50_ns = crossing_time(h_t, n_kd, 0.5, reverse_ns, "rising")
            onset_start_ns = reverse_ns
            onset_end_ns = model_rec50_ns
            post_start_ns = max(h_rec50_ns, model_rec50_ns)
            post_end_ns = active_end_ns
            total = window_stats(h_t, err, reverse_ns, active_end_ns)
            onset = window_stats(h_t, err, onset_start_ns, onset_end_ns)
            post = window_stats(h_t, err, post_start_ns, post_end_ns)
            transition_gap = window_stats(h_t, err, min(h_rec50_ns, model_rec50_ns), max(h_rec50_ns, model_rec50_ns))
            total_sse = total["sse"] if total["sse"] > 0 else float("nan")
            rows.append(
                {
                    "case_id": case.case_id,
                    "flow": flow,
                    "reverse_edge_ns": reverse_ns,
                    "active_end_ns": active_end_ns,
                    "hspice_kd_recover_50_ns": h_rec50_ns,
                    "model_kd_recover_50_ns": model_rec50_ns,
                    "model_recover_lag_ps": (model_rec50_ns - h_rec50_ns) * 1000.0 if math.isfinite(model_rec50_ns) and math.isfinite(h_rec50_ns) else float("nan"),
                    "total_kd_rmse": total["rmse"],
                    "onset_window_start_ns": onset_start_ns,
                    "onset_window_end_ns": onset_end_ns,
                    "onset_kd_rmse": onset["rmse"],
                    "onset_sse_fraction": onset["sse"] / total_sse if math.isfinite(total_sse) else float("nan"),
                    "crossing_gap_kd_rmse": transition_gap["rmse"],
                    "crossing_gap_sse_fraction": transition_gap["sse"] / total_sse if math.isfinite(total_sse) else float("nan"),
                    "post_both_50_start_ns": post_start_ns,
                    "post_both_50_end_ns": post_end_ns,
                    "post_both_50_kd_rmse": post["rmse"],
                    "post_both_50_sse_fraction": post["sse"] / total_sse if math.isfinite(total_sse) else float("nan"),
                    "classification_hint": (
                        "pre_50_dominated_with_shape_tail"
                        if onset["sse"] > 0.7 * total["sse"] and post["rmse"] > 0.1
                        else "onset_dominated"
                        if onset["sse"] > 0.7 * total["sse"]
                        else "shape_dominated_after_timing"
                        if abs((model_rec50_ns - h_rec50_ns) * 1000.0) <= 200.0 and post["rmse"] > 0.1
                        else "mixed_onset_and_shape"
                    ),
                }
            )
    write_csv(out_dir / "kd_error_window_split.csv", rows)
    plot_kd_error_window_diagnostics(rows)
    return rows


def plot_kd_error_window_diagnostics(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    out_dir = OUT_DIR / "kd_recovery_diagnostics"
    ensure_dir(out_dir)
    case_id = "short_pulse_1ns_high"
    flow = "ngspice_two_state_directional_residual_recover_mean"
    row = next((item for item in rows if item.get("case_id") == case_id and item.get("flow") == flow), None)
    if row is None:
        return
    case = base.case_by_id(case_id, include_low=True)
    h = parse_hspice_tr0(CASES_DIR / case.case_id / "hspice_native_ibis" / f"{case.case_id}_hspice_native_ibis.tr0")
    n = parse_ngspice_raw(CASES_DIR / case.case_id / flow / f"{case.case_id}_{flow}.raw")
    h_t = base.to_ns(base.find_signal(h, "time"))
    h_kd = base.find_signal(h, "v(kd)")
    n_t = base.to_ns(base.find_signal(n, "time"))
    n_kd = base.interp_to(n_t, base.find_signal(n, "v(xdrv.kd)", "v(xdrv:kd)"), h_t)
    err = n_kd - h_kd
    reverse_ns = float(row["reverse_edge_ns"])
    model_50 = float(row["model_kd_recover_50_ns"])
    post_start = float(row["post_both_50_start_ns"])
    post_end = float(row["post_both_50_end_ns"])
    x0, x1 = reverse_ns - 0.25, post_end + 0.25
    fig, axes = plt.subplots(2, 1, figsize=(10.8, 7.0), sharex=True, constrained_layout=True)
    axes[0].axvspan(reverse_ns, model_50, color="#f2c94c", alpha=0.18, label="onset window")
    axes[0].axvspan(post_start, post_end, color="#56cc9d", alpha=0.16, label="post-both-50 window")
    axes[0].plot(h_t, h_kd, color=COLORS["hspice_native"], lw=2.0, label="HSPICE native IBIS Kd")
    axes[0].plot(h_t, n_kd, color=COLORS["two_state_directional_residual_recover_mean"], lw=1.8, label="mean-recovery Kd")
    axes[0].axvline(float(row["hspice_kd_recover_50_ns"]), color=COLORS["hspice_native"], lw=1.2, ls=":", label="HSPICE 50% recovery")
    axes[0].axvline(model_50, color=COLORS["two_state_directional_residual_recover_mean"], lw=1.2, ls=":", label="model 50% recovery")
    axes[1].axvspan(reverse_ns, model_50, color="#f2c94c", alpha=0.18)
    axes[1].axvspan(post_start, post_end, color="#56cc9d", alpha=0.16)
    axes[1].plot(h_t, err, color="#d62728", lw=1.7, label="model - HSPICE Kd error")
    axes[1].axhline(0.0, color="#333333", lw=0.8)
    for ax, ylabel in [(axes[0], "Kd"), (axes[1], "Kd error")]:
        ax.set_xlim(x0, x1)
        base.mark_commands(ax, case)
        base.style(ax, ylabel)
        ax.legend(loc="best", frameon=False)
    axes[-1].set_xlabel("Time (ns)")
    fig.suptitle(
        f"{case_id}: Kd error split for mean-recovery candidate\n"
        f"onset RMSE={float(row['onset_kd_rmse']):.3f}, post-both-50 RMSE={float(row['post_both_50_kd_rmse']):.3f}",
        fontweight="bold",
    )
    fig.savefig(out_dir / "short_pulse_1ns_high_mean_recovery_kd_error_windows.png", dpi=180)
    plt.close(fig)


def run_case(case: base.StudyCase, args: argparse.Namespace, model_paths: dict[str, Path]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    h_native, _, native_cache = base.run_hspice_native(case, args.ibis, args.hspice, args.timeout_s)
    h_sp, _, sp_cache = base.run_hspice_transistor(case, args.io_buf_sp, args.mos_model, args.hspice, args.timeout_s)
    rows = base.score_reference_rows(case, h_native, h_sp)
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
                    "status": "NUMERIC_FAIL",
                    "error": str(exc),
                }
            )
    return rows, [native_cache, sp_cache]


def verify_generated_models(model_paths: dict[str, Path]) -> None:
    for variant_id in [
        "two_state_identity",
        "two_state_pwl",
        "two_state_hybrid",
        "two_state_directional",
        "two_state_directional_residual",
        "two_state_directional_residual_recover_mean",
        "two_state_directional_residual_recover_fast",
    ]:
        text = model_paths[variant_id].read_text(encoding="utf-8", errors="replace")
        required = ["Two-state gate input-driven waveform coefficient control", "GUP", "GDN", "GUPTARGET", "GDNTARGET", "KUGATE", "KDGATE", "KULEG", "KDLEG", "KOVERLAP"]
        missing = [token for token in required if token not in text]
        if missing:
            raise RuntimeError(f"Generated {variant_id} model is missing diagnostics: {', '.join(missing)}")
    legacy = model_paths["legacy"].read_text(encoding="utf-8", errors="replace")
    if "Two-state gate input-driven waveform coefficient control" in legacy or "GUPTARGET" in legacy:
        raise RuntimeError("Legacy InputDriven model unexpectedly contains two-state gate circuitry")


def write_readme(rows: list[dict[str, object]], cache_rows: list[dict[str, object]], fit_rows: list[dict[str, object]]) -> None:
    lookup = {(str(row.get("case_id")), str(row.get("flow"))): row for row in rows}
    fit = fit_rows[0] if fit_rows else {}
    kd_window_rows = read_csv(OUT_DIR / "kd_recovery_diagnostics" / "kd_error_window_split.csv")
    kd_window_lookup = {(row.get("case_id"), row.get("flow")): row for row in kd_window_rows}
    kd_tau_rows = read_csv(OUT_DIR / "kd_recovery_diagnostics" / "effective_tau" / "hspice_effective_kd_recovery_tau.csv")
    kd_hold_rows = read_csv(OUT_DIR / "kd_recovery_diagnostics" / "hold_time" / "hold_law_fit_summary.csv")
    kd_hold_fit = kd_hold_rows[0] if kd_hold_rows else {}
    kd_gdn_hold_rows = read_csv(OUT_DIR / "kd_recovery_diagnostics" / "gdn_hold_time" / "gdn_hold_fit_summary.csv")
    kd_gdn_primary = next((row for row in kd_gdn_hold_rows if row.get("flow") == "ngspice_two_state_directional_residual"), {})
    kd_command_age_rows = read_csv(OUT_DIR / "kd_recovery_diagnostics" / "command_age_hold" / "command_age_hold_validation_summary.csv")
    kd_command_age_fit = kd_command_age_rows[0] if kd_command_age_rows else {}
    reference_truth_rows = read_csv(OUT_DIR / "reference_truth_audit" / "pad_rescore_vs_references.csv")

    def fnum(case_id: str, flow: str, key: str, scale_factor: float = 1.0, fmt: str = ".4g") -> str:
        value = lookup.get((case_id, flow), {}).get(key, "")
        try:
            return format(float(value) * scale_factor, fmt)
        except (TypeError, ValueError):
            return "n/a"

    def wnum(case_id: str, flow: str, key: str, scale_factor: float = 1.0, fmt: str = ".4g") -> str:
        value = kd_window_lookup.get((case_id, flow), {}).get(key, "")
        try:
            return format(float(value) * scale_factor, fmt)
        except (TypeError, ValueError):
            return "n/a"

    def tau_values(key: str) -> list[float]:
        values: list[float] = []
        for row in kd_tau_rows:
            try:
                value = float(row.get(key, ""))
            except (TypeError, ValueError):
                continue
            if math.isfinite(value):
                values.append(value)
        return values

    def spread_text(key: str) -> str:
        values = tau_values(key)
        if not values:
            return "n/a"
        return f"{(max(values) / min(values)):.3f}x"

    def hold_fit_text(key: str, scale_factor: float = 1.0, fmt: str = ".4g") -> str:
        value = kd_hold_fit.get(key, "")
        try:
            return format(float(value) * scale_factor, fmt)
        except (TypeError, ValueError):
            return "n/a"

    def gdn_fit_text(key: str, scale_factor: float = 1.0, fmt: str = ".4g") -> str:
        value = kd_gdn_primary.get(key, "")
        try:
            return format(float(value) * scale_factor, fmt)
        except (TypeError, ValueError):
            return "n/a"

    def command_age_text(key: str, scale_factor: float = 1.0, fmt: str = ".4g") -> str:
        value = kd_command_age_fit.get(key, "")
        try:
            return format(float(value) * scale_factor, fmt)
        except (TypeError, ValueError):
            return "n/a"

    def ref_truth(case_id: str, flow: str, key: str, scale_factor: float = 1.0, fmt: str = ".4g") -> str:
        row = next((item for item in reference_truth_rows if item.get("case_id") == case_id and item.get("flow") == flow), {})
        value = row.get(key, "")
        try:
            return format(float(value) * scale_factor, fmt)
        except (TypeError, ValueError):
            return "n/a"

    lines = [
        "# io_buf Two-State Gate pybis Model",
        "",
        "This study tests an opt-in hidden-gate pybis model. The normal complete-edge coefficient reconstruction is the first gate: if the model cannot reproduce original `Ku/Kd` tables, short-pulse results are diagnostic only.",
        "",
        "## Headline Finding",
        "",
        "- The original single-map PWL two-state implementation is **not validated** because it fails the normal complete-edge `Ku/Kd` reconstruction gate.",
        "- This rerun adds direction-specific on/off maps plus a Kd rate-residual candidate, then applies the same normal gate before short-pulse interpretation.",
        "- Direction-specific maps plus the Kd residual now pass the offline complete-edge table reconstruction gate, which is real structural progress.",
        "- The same residual model is still **not default-ready** in transient: the normal long-pulse case is worse than legacy, and short-high Kd recovery remains wrong even when Kd undershoot is restored.",
        "- This update adds two retrigger-aware Kd recovery-onset candidates. They keep the same directional maps/residual, but route detected short-high pulldown re-turn-on through an IBIS-derived mean or fast recovery delay.",
        "- The mean recovery candidate confirms the missing lever is Kd onset timing: it improves short-high Kd RMSE without materially changing the long-pulse control. It still is **not default-ready** because one fixed recovery delay is early for some widths and late for others.",
        "- Short-low behavior improves more than short-high behavior, which says the remaining problem is directional/retrigger recovery, not just static map shape.",
        "- A short-pulse pad improvement is still not enough; `Ku` and `Kd` must also agree, especially the Kd undershoot and recovery timing.",
        "",
        "## Normal Ku/Kd Reconstruction Gate",
        "",
        f"- Original PWL gate result: `{fit.get('pwl_table_gate', 'n/a')}`",
        f"- Directional-map gate result: `{fit.get('directional_table_gate', 'n/a')}`",
        f"- Directional + residual gate result: `{fit.get('directional_residual_table_gate', 'n/a')}`",
        f"- Worst PWL table RMSE / max error: `{float(fit.get('pwl_reconstruction_rmse_max', float('nan'))):.5g}` / `{float(fit.get('pwl_reconstruction_max_error_max', float('nan'))):.5g}`",
        f"- Worst directional table RMSE / max error: `{float(fit.get('directional_reconstruction_rmse_max', float('nan'))):.5g}` / `{float(fit.get('directional_reconstruction_max_error_max', float('nan'))):.5g}`",
        f"- Worst directional + residual table RMSE / max error: `{float(fit.get('directional_residual_reconstruction_rmse_max', float('nan'))):.5g}` / `{float(fit.get('directional_residual_reconstruction_max_error_max', float('nan'))):.5g}`",
        f"- Kd rate residual gain: `{fit.get('kd_rate_gain_ns', 'n/a')}` ns",
        f"- PU on/off tau: `{fit.get('pu_on_tau_ns', 'n/a')}` / `{fit.get('pu_off_tau_ns', 'n/a')}` ns",
        f"- PD on/off tau: `{fit.get('pd_on_tau_ns', 'n/a')}` / `{fit.get('pd_off_tau_ns', 'n/a')}` ns",
        "",
        "## Measured Transient Takeaways",
        "",
        f"- Long-pulse legacy pad / Ku / Kd RMSE: `{fnum('edge_1ps_base_50r_2pf', 'ngspice_legacy', 'pad_active_rmse_v', 1e3, '.3f')} mV`, `{fnum('edge_1ps_base_50r_2pf', 'ngspice_legacy', 'ku_active_rmse', 1.0, '.5f')}`, `{fnum('edge_1ps_base_50r_2pf', 'ngspice_legacy', 'kd_active_rmse', 1.0, '.5f')}`.",
        f"- Long-pulse directional+residual pad / Ku / Kd RMSE: `{fnum('edge_1ps_base_50r_2pf', 'ngspice_two_state_directional_residual', 'pad_active_rmse_v', 1e3, '.3f')} mV`, `{fnum('edge_1ps_base_50r_2pf', 'ngspice_two_state_directional_residual', 'ku_active_rmse', 1.0, '.5f')}`, `{fnum('edge_1ps_base_50r_2pf', 'ngspice_two_state_directional_residual', 'kd_active_rmse', 1.0, '.5f')}`.",
        f"- Long-pulse mean-recovery pad / Ku / Kd RMSE: `{fnum('edge_1ps_base_50r_2pf', 'ngspice_two_state_directional_residual_recover_mean', 'pad_active_rmse_v', 1e3, '.3f')} mV`, `{fnum('edge_1ps_base_50r_2pf', 'ngspice_two_state_directional_residual_recover_mean', 'ku_active_rmse', 1.0, '.5f')}`, `{fnum('edge_1ps_base_50r_2pf', 'ngspice_two_state_directional_residual_recover_mean', 'kd_active_rmse', 1.0, '.5f')}`.",
        f"- `short_pulse_1ns_high`: directional+residual pad improves to `{fnum('short_pulse_1ns_high', 'ngspice_two_state_directional_residual', 'pad_active_rmse_v', 1e3, '.3f')} mV`, but Kd RMSE remains `{fnum('short_pulse_1ns_high', 'ngspice_two_state_directional_residual', 'kd_active_rmse', 1.0, '.5f')}`.",
        f"- `short_pulse_1ns_high` with mean recovery: Kd RMSE improves to `{fnum('short_pulse_1ns_high', 'ngspice_two_state_directional_residual_recover_mean', 'kd_active_rmse', 1.0, '.5f')}`, but status remains `{lookup.get(('short_pulse_1ns_high', 'ngspice_two_state_directional_residual_recover_mean'), {}).get('status', 'n/a')}` because Kd is still not coefficient-correct.",
        f"- `short_pulse_2ns_high` with mean recovery: Kd RMSE improves from `{fnum('short_pulse_2ns_high', 'ngspice_two_state_directional_residual', 'kd_active_rmse', 1.0, '.5f')}` to `{fnum('short_pulse_2ns_high', 'ngspice_two_state_directional_residual_recover_mean', 'kd_active_rmse', 1.0, '.5f')}`.",
        f"- `short_pulse_2ns_low`: directional+residual reaches status `{lookup.get(('short_pulse_2ns_low', 'ngspice_two_state_directional_residual'), {}).get('status', 'n/a')}` with pad / Ku / Kd RMSE `{fnum('short_pulse_2ns_low', 'ngspice_two_state_directional_residual', 'pad_active_rmse_v', 1e3, '.3f')} mV`, `{fnum('short_pulse_2ns_low', 'ngspice_two_state_directional_residual', 'ku_active_rmse', 1.0, '.5f')}`, `{fnum('short_pulse_2ns_low', 'ngspice_two_state_directional_residual', 'kd_active_rmse', 1.0, '.5f')}`.",
        "- Kd recovery timing details are saved in `kd_recovery_diagnostics/recovery_timing_summary.csv`; the fixed mean/fast delays improve onset but do not yet solve all pulse widths.",
        f"- Windowed Kd error split for `short_pulse_1ns_high` mean recovery, measured from reverse edge to active-window end: total RMSE `{wnum('short_pulse_1ns_high', 'ngspice_two_state_directional_residual_recover_mean', 'total_kd_rmse', 1.0, '.5f')}`, pre-50/onset-window RMSE `{wnum('short_pulse_1ns_high', 'ngspice_two_state_directional_residual_recover_mean', 'onset_kd_rmse', 1.0, '.5f')}`, post-both-50 RMSE `{wnum('short_pulse_1ns_high', 'ngspice_two_state_directional_residual_recover_mean', 'post_both_50_kd_rmse', 1.0, '.5f')}`, pre-50 SSE fraction `{wnum('short_pulse_1ns_high', 'ngspice_two_state_directional_residual_recover_mean', 'onset_sse_fraction', 100.0, '.1f')}%`. Classification hint: `{kd_window_lookup.get(('short_pulse_1ns_high', 'ngspice_two_state_directional_residual_recover_mean'), {}).get('classification_hint', 'n/a')}`.",
        f"- HSPICE Kd recovery extraction shows apparent min-to-final tau spread `{spread_text('hspice_effective_tau_ns')}`, but the actual 10%-90% main-slope tau spread is only `{spread_text('hspice_main_slope_tau_10_90_ns')}`. This says the remaining short-high issue is mostly recovery staging/early trajectory, not a simple fixed tau change.",
        f"- HSPICE hold-time extraction prefers a width-drift law over one constant hold: `T_hold50 = {hold_fit_text('h2_intercept_ns', 1.0, '.4f')} + {hold_fit_text('h2_slope_ns_per_ns', 1.0, '.4f')} * pulse_width` ns, with H2 residual `{hold_fit_text('h2_residual_rms_ns', 1e3, '.1f')} ps` versus constant-hold residual `{hold_fit_text('h1_residual_rms_ns', 1e3, '.1f')} ps`. Verdict: `{kd_hold_fit.get('verdict', 'n/a')}`.",
        f"- GDN-keyed hold extraction shows the present `GDN@reverse` is not the right latch variable: primary GDN fit residual `{gdn_fit_text('rms_ns', 1e3, '.1f')} ps`, origin-forced residual `{gdn_fit_text('origin_forced_rms_ns', 1e3, '.1f')} ps`, verdict `{kd_gdn_primary.get('verdict', 'n/a')}`. The current GDN state collapses 500 ps and 1 ns pulses to the same value.",
        f"- Held-out command-age validation on a new `1.5 ns` short-high HSPICE case gives error `{command_age_text('heldout_error_ps', 1.0, '+.1f')} ps` against a `+/-{command_age_text('tolerance_ps', 1.0, '.0f')} ps` gate. Verdict: `{kd_command_age_fit.get('verdict', 'n/a')}`. This means the simple two-parameter command-age line should not be implemented as the next candidate without a better law.",
        f"- Reference-truth audit changes the framing: HSPICE native IBIS and transistor `io_buf.sp` differ by `{ref_truth('edge_1ps_base_50r_2pf', 'hspice_transistor_sp', 'vs_native_rmse_mV', 1.0, '.1f')} mV` on the long-pulse pad and `{ref_truth('short_pulse_1ns_high', 'hspice_transistor_sp', 'vs_native_rmse_mV', 1.0, '.1f')} mV` on `short_pulse_1ns_high`. Coefficient RMSE should be read as native-IBIS playback agreement, not automatically transistor truth.",
        "- The double-toggle case does **not** prove full-table commitment because it ends with a sustained final high. Pure short-high native-IBIS Ku peaks are partial, so the remaining reference concern is specifically Kd recovery/hold behavior.",
        "",
        "Figures:",
        "",
        "- `fit_diagnostics/ku_kd_table_reconstruction.png`",
        "- `fit_diagnostics/gate_to_coefficient_maps.png`",
        "- `fit_diagnostics/directional_maps_and_residual.png`",
        "",
        "## Transient Case Summary",
        "",
        "| Case | Flow | Status | Pad RMSE mV | Ku RMSE | Kd RMSE | Ku peak | Kd min | Coeff range ok |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    flow_order = [
        "hspice_native_ibis",
        "hspice_transistor_sp",
        "ngspice_legacy",
        "ngspice_value_match_v2",
        "ngspice_two_state_identity",
        "ngspice_two_state_pwl",
        "ngspice_two_state_hybrid",
        "ngspice_two_state_directional",
        "ngspice_two_state_directional_residual",
        "ngspice_two_state_directional_residual_recover_mean",
        "ngspice_two_state_directional_residual_recover_fast",
    ]
    for case in build_cases(include_low=True):
        for flow in flow_order:
            row = lookup.get((case.case_id, flow), {})
            if not row:
                continue
            lines.append(
                "| {case} | {flow} | {status} | {pad_rmse} | {ku_rmse} | {kd_rmse} | {ku_peak} | {kd_min} | {range_ok} |".format(
                    case=case.case_id,
                    flow=flow,
                    status=row.get("status", ""),
                    pad_rmse=fnum(case.case_id, flow, "pad_active_rmse_v", 1e3, ".3f") if flow.startswith("ngspice") else fnum(case.case_id, flow, "pad_vs_hspice_native_rmse_v", 1e3, ".3f"),
                    ku_rmse=fnum(case.case_id, flow, "ku_active_rmse", 1.0, ".5f"),
                    kd_rmse=fnum(case.case_id, flow, "kd_active_rmse", 1.0, ".5f"),
                    ku_peak=fnum(case.case_id, flow, "ku_peak", 1.0, ".4f"),
                    kd_min=fnum(case.case_id, flow, "kd_min", 1.0, ".4f"),
                    range_ok=row.get("coeff_range_ok", ""),
                )
            )
    lines.extend(
        [
            "",
            "## Output Figures",
            "",
            "- `figures/<case>/01_input_pad_overlay.png`",
            "- `figures/<case>/02_ku_overlay.png`",
            "- `figures/<case>/03_kd_overlay.png`",
            "- `figures/<case>/04_gate_state_diagnostics.png`",
        "- `figures/<case>/05_summary_bars.png`",
        "- `figures/summary_bars.png`",
        "- `kd_recovery_diagnostics/kd_error_window_split.csv`",
        "- `kd_recovery_diagnostics/short_pulse_1ns_high_mean_recovery_kd_error_windows.png`",
        "- `kd_recovery_diagnostics/effective_tau/hspice_effective_kd_recovery_tau.csv`",
        "- `kd_recovery_diagnostics/effective_tau/hspice_effective_tau_vs_depth.png`",
        "- `kd_recovery_diagnostics/effective_tau/hspice_kd_recovery_tau_fits.png`",
        "- `kd_recovery_diagnostics/hold_time/hspice_kd_hold_time.csv`",
        "- `kd_recovery_diagnostics/hold_time/hold_law_fit_summary.csv`",
        "- `kd_recovery_diagnostics/hold_time/hspice_kd_hold_time_fit.png`",
        "- `kd_recovery_diagnostics/hold_time/candidate_hold_time_comparison.png`",
        "- `kd_recovery_diagnostics/gdn_hold_time/gdn_hold_samples.csv`",
        "- `kd_recovery_diagnostics/gdn_hold_time/gdn_hold_fit_summary.csv`",
        "- `kd_recovery_diagnostics/gdn_hold_time/gdn_keyed_hold_fit.png`",
        "- `kd_recovery_diagnostics/gdn_hold_time/gdn_at_reverse_by_variant.png`",
        "- `kd_recovery_diagnostics/command_age_hold/command_age_hold_training_and_heldout.csv`",
        "- `kd_recovery_diagnostics/command_age_hold/command_age_hold_validation_summary.csv`",
        "- `kd_recovery_diagnostics/command_age_hold/command_age_hold_heldout_validation.png`",
        "- `reference_truth_audit/pad_rescore_vs_references.csv`",
        "- `reference_truth_audit/pad_ranking_by_reference.csv`",
        "- `reference_truth_audit/short_high_pad_timing.csv`",
        "- `reference_truth_audit/double_toggle_commitment.csv`",
        "- `reference_truth_audit/plots/*_pad_reference_overlay.png`",
        "- `reference_truth_audit/plots/double_toggle_full_table_commitment.png`",
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
            "No two-state variant is a success unless it first passes normal `Ku/Kd` reconstruction and then improves short pulses in pad, `Ku`, and `Kd` together. Pad-only improvement remains a false pass.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="io_buf two-state hidden-gate pybis validation study.")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--hspice", type=Path, default=DEFAULT_HSPICE)
    parser.add_argument("--ibis", type=Path, default=DEFAULT_IBIS)
    parser.add_argument("--io-buf-sp", type=Path, default=DEFAULT_IO_BUF_SP)
    parser.add_argument("--mos-model", type=Path, default=DEFAULT_MOS_MODEL)
    parser.add_argument("--case", action="append", default=[], help="Run only this case id. May be repeated.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=240)
    return parser.parse_args()


def main() -> int:
    configure_base_globals()
    args = parse_args()
    for path in [OUT_DIR, COMMON_DIR, CASES_DIR, FIGURES_DIR, FIT_DIR]:
        ensure_dir(path)
    fit_rows, _ = write_fit_diagnostics(args.ibis)
    if args.summarize_only:
        rows = [dict(row) for row in read_csv(OUT_DIR / "candidate_metrics.csv")]
        cache_rows = [dict(row) for row in read_csv(OUT_DIR / "reference_cache_manifest.csv")]
        write_kd_recovery_window_diagnostics()
        for case in selected_cases(args.case, include_low=True):
            plot_case_figures(case)
        plot_summary(rows)
        write_readme(rows, cache_rows, fit_rows)
        print(f"OUT_DIR={OUT_DIR}")
        return 0

    model_paths = prepare_common(args.ibis)
    verify_generated_models(model_paths)
    existing_rows = [dict(row) for row in read_csv(OUT_DIR / "candidate_metrics.csv")] if args.resume else []
    existing_cache = [dict(row) for row in read_csv(OUT_DIR / "reference_cache_manifest.csv")] if args.resume else []
    done = {(row.get("case_id"), row.get("flow")) for row in existing_rows}
    all_rows = list(existing_rows)
    cache_rows = list(existing_cache)
    expected_flows = {
        "hspice_native_ibis",
        "hspice_transistor_sp",
        "ngspice_legacy",
        "ngspice_value_match_v2",
        "ngspice_two_state_identity",
        "ngspice_two_state_pwl",
        "ngspice_two_state_hybrid",
        "ngspice_two_state_directional",
        "ngspice_two_state_directional_residual",
        "ngspice_two_state_directional_residual_recover_mean",
        "ngspice_two_state_directional_residual_recover_fast",
    }
    cases = selected_cases(args.case, include_low=True)
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
    order = {case.case_id: i for i, case in enumerate(build_cases(include_low=True))}
    flow_order = {flow: i for i, flow in enumerate(sorted(expected_flows))}
    all_rows.sort(key=lambda row: (order.get(str(row.get("case_id")), 999), flow_order.get(str(row.get("flow")), 999)))
    cache_rows.sort(key=lambda row: (order.get(str(row.get("case_id")), 999), str(row.get("reference", ""))))
    write_csv(OUT_DIR / "candidate_metrics.csv", all_rows)
    write_csv(OUT_DIR / "reference_cache_manifest.csv", cache_rows)
    write_kd_recovery_window_diagnostics()
    plot_summary(all_rows)
    write_readme(all_rows, cache_rows, fit_rows)
    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
