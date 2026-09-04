from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
PYBIS_ROOT = ROOT / "tools" / "pybis2spice"
for path in [SCRIPTS, PYBIS_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_inv_chain_gate_state_clean_comparison as clean  # noqa: E402
from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from pybis2spice import pybis2spice, subcircuit  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


OUT_ROOT = ROOT / "results" / "ex2_slow_fast_gate_state_comparison_2026-07-28"
REGEN_ROOT = ROOT / "results" / "ex2_s2ibispy_slow_fast_2026-07-28"
ORIGINAL_IBIS = ROOT / "buffers" / "ex2" / "buffer.ibs"
TRANSISTOR_SP = ROOT / "buffers" / "ex2" / "buffer.sp"
TRANSISTOR_MODELS = ROOT / "buffers" / "ex2" / "hspice.mod"

COMPONENT_NAME = "MCM Driver 1"
MODEL_NAME = "driver"
SUPPLY_V = 3.3
LOAD_OHM = 50.0
LOAD_PF = 2.0
EDGE_NS = 0.001

PROFILES = {
    "slow_1ns": REGEN_ROOT / "slow_1ns" / "ex2_slow_1ns.ibs",
    "fast_5ps": REGEN_ROOT / "fast_5ps" / "ex2_fast_5ps.ibs",
}

CASES = [
    clean.Case("edge_1ps_base_50r_2pf", "Complete rise and fall", "rise_fall", 10.0, 22.0),
    clean.Case("short_pulse_50ps_high", "50 ps high pulse", "short_high", 0.05, 12.0),
    clean.Case("short_pulse_500ps_high", "500 ps high pulse", "short_high", 0.5, 13.0),
    clean.Case("short_pulse_1ns_high", "1 ns high pulse", "short_high", 1.0, 14.0),
    clean.Case("short_pulse_2ns_high", "2 ns high pulse", "short_high", 2.0, 15.0),
    clean.Case("short_pulse_50ps_low", "50 ps low pulse", "short_low", 0.05, 17.0),
    clean.Case("short_pulse_500ps_low", "500 ps low pulse", "short_low", 0.5, 17.0),
    clean.Case("short_pulse_1ns_low", "1 ns low pulse", "short_low", 1.0, 18.0),
    clean.Case("short_pulse_2ns_low", "2 ns low pulse", "short_low", 2.0, 19.0),
]

FLOW_SPECS = {
    "legacy": ("InputDriven", "ngspice legacy pybis", "#1769aa", "o"),
    "gate_full": (
        "InputDrivenTwoStateGateDirectionalResidualFull",
        "ngspice directional-residual full",
        "#d62728",
        "D",
    ),
    "gate_stable": (
        "InputDrivenTwoStateGateDirectionalResidualStableFull",
        "ngspice directional-residual stable",
        "#009e73",
        "^",
    ),
    "dual_hybrid": (
        "InputDrivenTwoStateGateDirectionalDualResidualHybrid",
        "ngspice dual-residual reversal hybrid",
        "#7b2cbf",
        "s",
    ),
}


def configure_clean(profile_dir: Path) -> None:
    clean.OUT_DIR = profile_dir
    clean.COMMON_DIR = profile_dir / "common"
    clean.CASES_DIR = profile_dir / "cases"
    clean.PLOTS_DIR = profile_dir / "plots"
    clean.DATA_DIR = profile_dir / "waveform_data"
    clean.FIT_DIR = profile_dir / "fit_diagnostics"
    clean.COMPONENT_NAME = COMPONENT_NAME
    clean.MODEL_NAME = MODEL_NAME
    clean.SUPPLY_V = SUPPLY_V
    clean.LOAD_OHM = LOAD_OHM
    clean.LOAD_PF = LOAD_PF
    clean.EDGE_NS = EDGE_NS
    clean.CASES = CASES


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


def read_csv(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def hspice_native_deck(case: clean.Case) -> str:
    return f"""* ex2 HSPICE native IBIS
.title ex2 native IBIS {case.case_id}
.option post=2 probe accurate ingold=2
.temp 27

{clean.pwl(case)}

VPU pu_ref 0 DC {SUPPLY_V}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUPPLY_V}
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='ex2.ibs'
+ model='driver'
+ buffer=2 typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
+ xv_pu=ku xv_pd=kd

Rload pad_ibis 0 {LOAD_OHM}
Cload pad_ibis 0 {LOAD_PF}p
.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran 0.002n {clean.fmt(case.stop_ns)}n
.end
"""


def hspice_transistor_deck(case: clean.Case) -> str:
    return f"""* ex2 HSPICE transistor reference
.title ex2 transistor {case.case_id}
.option post=2 probe accurate ingold=2
.temp 27

{clean.pwl(case)}

Vdd vdd 0 DC {SUPPLY_V}
.include 'hspice.mod'
.subckt ex2_buffer in out vdd gnd
.include 'buffer.sp'
.ends ex2_buffer
XREF in_dig pad_sp vdd 0 ex2_buffer

Rload pad_sp 0 {LOAD_OHM}
Cload pad_sp 0 {LOAD_PF}p
.probe tran V(in_dig) V(pad_sp)
.tran 0.002n {clean.fmt(case.stop_ns)}n
.end
"""


def ngspice_deck(case: clean.Case, flow: str) -> str:
    diagnostics = ""
    if flow != "legacy":
        diagnostics = (
            " V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget)"
            " V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kuleg) V(xdrv.kdleg)"
        )
    return f"""* ex2 ngspice {flow}
.title ex2 ngspice {flow} {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{clean.pwl(case)}

* The generated Output model inherits active-low enable; tie it active.
Ven en_sig 0 DC 0
Vdd vdd 0 DC {SUPPLY_V}
.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical
Rload pad 0 {LOAD_OHM}
Cload pad 0 {LOAD_PF}p
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){diagnostics}
.tran 0.002n {clean.fmt(case.stop_ns)}n
.end
"""


def run_native(
    case: clean.Case,
    ibis: Path,
    profile: str,
    hspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = clean.CASES_DIR / case.case_id / "hspice_native_ibis"
    clean.ensure_dir(out_dir)
    shutil.copy2(ibis, out_dir / "ex2.ibs")
    stem = f"{case.case_id}_hspice_native_ibis"
    deck = hspice_native_deck(case)
    source = clean.cache_hspice(
        f"ex2_{profile}_native_ibis_direct_50r_2pf",
        case,
        deck,
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
        "tr0": str(tr0.relative_to(ROOT)),
    }


def run_transistor(
    case: clean.Case,
    hspice: Path,
    timeout_s: int,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    out_dir = clean.CASES_DIR / case.case_id / "hspice_transistor"
    clean.ensure_dir(out_dir)
    shutil.copy2(TRANSISTOR_SP, out_dir / "buffer.sp")
    shutil.copy2(TRANSISTOR_MODELS, out_dir / "hspice.mod")
    stem = f"{case.case_id}_hspice_transistor"
    deck = hspice_transistor_deck(case)
    source = clean.cache_hspice(
        "ex2_transistor_direct_50r_2pf",
        case,
        deck,
        [TRANSISTOR_SP, TRANSISTOR_MODELS],
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
        "tr0": str(tr0.relative_to(ROOT)),
    }


def prepare_models(ibis: Path, active_flows: list[str]) -> dict[str, Path]:
    common_ibis = clean.COMMON_DIR / "ex2.ibs"
    clean.ensure_dir(clean.COMMON_DIR)
    shutil.copy2(ibis, common_ibis)
    models: dict[str, Path] = {}
    for flow in active_flows:
        subckt_type = FLOW_SPECS[flow][0]
        output = clean.COMMON_DIR / flow / "driver_OutputInput_Typical.sub"
        convert_ibis_to_pybis(
            ibis_path=common_ibis,
            output_path=output,
            component_name=COMPONENT_NAME,
            model_name=MODEL_NAME,
            io_type="Output",
            subcircuit_type=subckt_type,
            corner="Typical",
        )
        models[flow] = output
    return models


def run_ngspice(
    case: clean.Case,
    flow: str,
    model: Path,
    ngspice: Path,
    timeout_s: int,
) -> dict[str, np.ndarray]:
    out_dir = clean.CASES_DIR / case.case_id / f"ngspice_{flow}"
    clean.ensure_dir(out_dir)
    shutil.copy2(model, out_dir / "driver_OutputInput_Typical.sub")
    stem = f"{case.case_id}_ngspice_{flow}"
    deck = out_dir / f"{stem}.sp"
    raw = out_dir / f"{stem}.raw"
    clean.write_text(deck, ngspice_deck(case, flow))
    rc = clean.run_process(
        [str(ngspice), "-b", "-r", raw.name, deck.name],
        out_dir,
        out_dir / "ngspice_stdout.log",
        timeout_s,
    )
    if rc != 0 or not raw.exists():
        raise RuntimeError(f"ngspice failed for {flow}/{case.case_id}")
    return parse_ngspice_raw(raw)


def offline_fit(ibis: Path, profile_dir: Path) -> dict[str, object]:
    parsed = pybis2spice.get_ibis_model_ecdtools(str(ibis))
    model = pybis2spice.DataModel(parsed, model_name=MODEL_NAME, component_name=COMPONENT_NAME)
    kr = pybis2spice.solve_k_params_output(model, corner=1, waveform_type="Rising")
    kf = pybis2spice.solve_k_params_output(model, corner=1, waveform_type="Falling")
    kr = pybis2spice.compress_param(kr, threshold=1e-3)
    kf = pybis2spice.compress_param(kf, threshold=1e-3)
    fit = subcircuit.gate_state_fit(kr, kf)
    rows, data = clean.gate_helpers.reconstruction_rows_and_data(kr, kf, fit)
    write_csv(profile_dir / "normal_k_reconstruction.csv", rows)
    selected = [row for row in rows if row["candidate"] == "directional_residual"]
    worst_rmse = max(float(row["rmse"]) for row in selected)
    worst_max = max(float(row["max_error"]) for row in selected)
    summary = {
        "profile": profile_dir.name,
        "worst_rmse": worst_rmse,
        "worst_max_error": worst_max,
        "gate": "PASS" if worst_rmse <= 0.02 and worst_max <= 0.08 else "FAIL",
        "pu_on_delay_ns": fit["pu_on_delay"],
        "pu_on_tau_ns": fit["pu_on_tau"],
        "pu_off_delay_ns": fit["pu_off_delay"],
        "pu_off_tau_ns": fit["pu_off_tau"],
        "pd_on_delay_ns": fit["pd_on_delay"],
        "pd_on_tau_ns": fit["pd_on_tau"],
        "pd_off_delay_ns": fit["pd_off_delay"],
        "pd_off_tau_ns": fit["pd_off_tau"],
    }
    write_csv(profile_dir / "gate_fit_summary.csv", [summary])
    clean.ensure_dir(clean.FIT_DIR)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for ax, tkey, key, title in [
        (axes[0, 0], "tr", "ku_rise", "Ku rising"),
        (axes[0, 1], "tf", "ku_fall", "Ku falling"),
        (axes[1, 0], "tr", "kd_rise", "Kd rising"),
        (axes[1, 1], "tf", "kd_fall", "Kd falling"),
    ]:
        ax.plot(data[tkey], data[f"{key}_orig"], color="#111111", lw=2.8, label="IBIS-derived")
        ax.plot(
            data[tkey],
            data[f"{key}_directional_residual"],
            color="#d62728",
            lw=1.8,
            label="directional-residual",
        )
        ax.set(title=title, xlabel="table time (ns)", ylabel=key.split("_")[0].upper())
        ax.grid(True, color="#dddddd")
    axes[0, 0].legend(frameon=False)
    fig.suptitle(f"ex2 {profile_dir.name}: normal Ku/Kd reconstruction")
    fig.savefig(clean.FIT_DIR / "ku_kd_table_reconstruction.png", dpi=180)
    plt.close(fig)
    return summary


def align(
    case: clean.Case,
    native: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
    ng: dict[str, dict[str, np.ndarray]],
) -> dict[str, np.ndarray]:
    t = clean.to_ns(clean.find_signal(native, "time"))
    data = {
        "time_ns": t,
        "input_v": clean.input_waveform(case, t),
        "hspice_ibis_pad_v": clean.find_signal(native, "v(pad_ibis)"),
        "hspice_ibis_ku": clean.find_signal(native, "v(ku)"),
        "hspice_ibis_kd": clean.find_signal(native, "v(kd)"),
    }
    tt = clean.to_ns(clean.find_signal(transistor, "time"))
    data["hspice_transistor_pad_v"] = np.interp(
        t, tt, clean.find_signal(transistor, "v(pad_sp)")
    )
    for flow, raw in ng.items():
        nt = clean.to_ns(clean.find_signal(raw, "time"))
        for suffix, signal in [
            ("pad_v", "v(pad)"),
            ("ku", "v(xdrv.ku)"),
            ("kd", "v(xdrv.kd)"),
        ]:
            data[f"{flow}_{suffix}"] = np.interp(t, nt, clean.find_signal(raw, signal))
    write_csv(
        clean.DATA_DIR / f"{case.case_id}.csv",
        [{key: float(value[i]) for key, value in data.items()} for i in range(len(t))],
    )
    return data


def metrics(case: clean.Case, data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    mask = clean.active_mask(case, data["time_ns"])
    rows: list[dict[str, object]] = []
    for flow in [name for name in FLOW_SPECS if f"{name}_pad_v" in data]:
        row: dict[str, object] = {"case_id": case.case_id, "flow": flow}
        for signal in ["pad_v", "ku", "kd"]:
            reference = data[f"hspice_ibis_{signal}"][mask]
            candidate = data[f"{flow}_{signal}"][mask]
            row[f"{signal}_rmse"] = clean.rmse(reference, candidate)
            row[f"{signal}_max_error"] = clean.max_error(reference, candidate)
        row["pad_peak_v"] = float(np.max(data[f"{flow}_pad_v"][mask]))
        row["pad_min_v"] = float(np.min(data[f"{flow}_pad_v"][mask]))
        row["ku_peak"] = float(np.max(data[f"{flow}_ku"][mask]))
        row["kd_min"] = float(np.min(data[f"{flow}_kd"][mask]))
        rows.append(row)
    rows.append(
        {
            "case_id": case.case_id,
            "flow": "hspice_transistor",
            "pad_v_rmse": clean.rmse(
                data["hspice_ibis_pad_v"][mask], data["hspice_transistor_pad_v"][mask]
            ),
            "pad_v_max_error": clean.max_error(
                data["hspice_ibis_pad_v"][mask], data["hspice_transistor_pad_v"][mask]
            ),
            "pad_peak_v": float(np.max(data["hspice_transistor_pad_v"][mask])),
            "pad_min_v": float(np.min(data["hspice_transistor_pad_v"][mask])),
        }
    )
    return rows


def plot_flow(
    case: clean.Case,
    data: dict[str, np.ndarray],
    flow: str,
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    _, label, color, marker = FLOW_SPECS[flow]
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True, constrained_layout=True)
    for ax, suffix, ylabel in [
        (axes[0], "pad_v", "pad voltage (V)"),
        (axes[1], "ku", "Ku"),
        (axes[2], "kd", "Kd"),
    ]:
        ax.plot(
            data["time_ns"],
            data[f"hspice_ibis_{suffix}"],
            color="#111111",
            lw=3.0,
            label="HSPICE native IBIS",
        )
        ax.plot(
            data["time_ns"],
            data[f"{flow}_{suffix}"],
            color=color,
            lw=1.9,
            marker=marker,
            markevery=max(1, len(data["time_ns"]) // 50),
            ms=3.0,
            label=label,
        )
        clean.style_axis(ax, ylabel, case)
    axes[2].axhline(0, color="#777777", lw=0.8)
    axes[0].legend(frameon=False, loc="upper center")
    axes[2].set_xlabel("time (ns)")
    fig.suptitle(case.title, fontweight="bold")
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return output


def plot_pad_all(case: clean.Case, data: dict[str, np.ndarray], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 5.4), constrained_layout=True)
    ax.plot(data["time_ns"], data["hspice_ibis_pad_v"], color="#111111", lw=3, label="HSPICE native IBIS")
    ax.plot(
        data["time_ns"],
        data["hspice_transistor_pad_v"],
        color="#888888",
        lw=3.8,
        label="HSPICE transistor",
    )
    for flow in ["legacy", "gate_full", "gate_stable", "dual_hybrid"]:
        if f"{flow}_pad_v" not in data:
            continue
        _, label, color, marker = FLOW_SPECS[flow]
        ax.plot(
            data["time_ns"],
            data[f"{flow}_pad_v"],
            color=color,
            lw=1.8,
            marker=marker,
            markevery=max(1, len(data["time_ns"]) // 50),
            ms=3,
            label=label,
        )
    clean.style_axis(ax, "pad voltage (V)", case)
    ax.set_xlabel("time (ns)")
    ax.set_title(case.title, fontweight="bold")
    ax.legend(frameon=False, ncol=3, loc="upper center")
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return output


def original_observability_report() -> None:
    output = OUT_ROOT / "original_ibis_observability"
    output.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "ibis": str(ORIGINAL_IBIS.relative_to(ROOT)),
            "rising_solve": "finite_but_ill_conditioned",
            "falling_solve": "singular_matrix",
            "classification": "PYBIS_UNOBSERVABLE",
            "cause": "same-rail high-resistance fixtures produce identical early equations",
        }
    ]
    write_csv(output / "observability_summary.csv", rows)
    def scaled(token: str) -> float:
        text = token.strip().lower().rstrip("v")
        for suffix, factor in [
            ("meg", 1e6),
            ("k", 1e3),
            ("m", 1e-3),
            ("u", 1e-6),
            ("n", 1e-9),
            ("p", 1e-12),
            ("f", 1e-15),
            ("s", 1.0),
        ]:
            if text.endswith(suffix):
                return float(text[: -len(suffix)]) * factor
        return float(text)

    waves: list[dict[str, object]] = []
    lines = ORIGINAL_IBIS.read_text(errors="replace").splitlines()
    index = 0
    while index < len(lines):
        header = lines[index].strip().lower()
        if header not in {"[rising waveform]", "[falling waveform]"}:
            index += 1
            continue
        kind = "Rising" if "rising" in header else "Falling"
        index += 1
        resistance = None
        fixture = None
        samples: list[tuple[float, float]] = []
        while index < len(lines) and not lines[index].strip().startswith("["):
            text = lines[index].strip()
            lower = text.lower()
            if lower.startswith("r_fixture"):
                resistance = scaled(text.split("=", 1)[1])
            elif lower.startswith("v_fixture"):
                fixture = scaled(text.split("=", 1)[1])
            elif text and not text.startswith("|"):
                parts = text.split()
                if len(parts) >= 2:
                    try:
                        samples.append((scaled(parts[0]) * 1e9, scaled(parts[1])))
                    except ValueError:
                        pass
            index += 1
        if resistance is not None and fixture is not None and samples:
            waves.append(
                {
                    "kind": kind,
                    "resistance": resistance,
                    "fixture": fixture,
                    "samples": np.asarray(samples, dtype=float),
                }
            )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    for ax, kind in zip(axes, ["Rising", "Falling"]):
        selected = [wave for wave in waves if wave["kind"] == kind]
        for wave, color in zip(selected, ["#1769aa", "#d62728"]):
            samples = np.asarray(wave["samples"], dtype=float)
            ax.plot(
                samples[:, 0],
                samples[:, 1],
                lw=2,
                color=color,
                label=f"{float(wave['resistance']):g} ohm to {float(wave['fixture']):g} V",
            )
        ax.set(title=kind, xlabel="table time (ns)", ylabel="fixture voltage (V)")
        ax.grid(True, color="#dddddd")
        ax.legend(frameon=False)
    fig.suptitle("Original ex2 IBIS waveform fixtures")
    fig.savefig(output / "original_fixture_waveforms.png", dpi=180)
    plt.close(fig)


def load_waveform_csv(profile: str, case: clean.Case) -> dict[str, np.ndarray]:
    path = OUT_ROOT / profile / "waveform_data" / f"{case.case_id}.csv"
    rows = read_csv(path)
    if not rows:
        raise FileNotFoundError(path)
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def cross_profile_plots() -> None:
    out_dir = OUT_ROOT / "cross_profile_plots"
    groups: dict[str, list[Path]] = {
        "hspice_pad": [],
        "hspice_k": [],
        "legacy": [],
    }
    for case in CASES:
        slow = load_waveform_csv("slow_1ns", case)
        fast = load_waveform_csv("fast_5ps", case)

        fig, ax = plt.subplots(figsize=(14, 5.4), constrained_layout=True)
        ax.plot(
            slow["time_ns"],
            slow["hspice_ibis_pad_v"],
            color="#1769aa",
            lw=2.5,
            label="HSPICE IBIS, 1 ns characterization edge",
        )
        ax.plot(
            fast["time_ns"],
            fast["hspice_ibis_pad_v"],
            color="#d62728",
            lw=2.2,
            label="HSPICE IBIS, 5 ps characterization edge",
        )
        ax.plot(
            slow["time_ns"],
            slow["hspice_transistor_pad_v"],
            color="#777777",
            lw=3.5,
            label="HSPICE transistor",
        )
        clean.style_axis(ax, "pad voltage (V)", case)
        ax.set_xlabel("time (ns)")
        ax.set_title(case.title, fontweight="bold")
        ax.legend(frameon=False, loc="upper center", ncol=3)
        path = out_dir / "01_hspice_slow_fast_transistor_pad" / f"{case.case_id}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=170)
        plt.close(fig)
        groups["hspice_pad"].append(path)

        fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True, constrained_layout=True)
        for ax, suffix, label in [
            (axes[0], "ku", "Ku"),
            (axes[1], "kd", "Kd"),
        ]:
            ax.plot(
                slow["time_ns"],
                slow[f"hspice_ibis_{suffix}"],
                color="#1769aa",
                lw=2.5,
                label="HSPICE IBIS, 1 ns",
            )
            ax.plot(
                fast["time_ns"],
                fast[f"hspice_ibis_{suffix}"],
                color="#d62728",
                lw=2.2,
                label="HSPICE IBIS, 5 ps",
            )
            clean.style_axis(ax, label, case)
        axes[1].axhline(0, color="#777777", lw=0.8)
        axes[0].legend(frameon=False, loc="upper center")
        axes[1].set_xlabel("time (ns)")
        fig.suptitle(case.title, fontweight="bold")
        path = out_dir / "02_hspice_slow_fast_ku_kd" / f"{case.case_id}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=170)
        plt.close(fig)
        groups["hspice_k"].append(path)

        fig, axes = plt.subplots(3, 2, figsize=(16, 9), sharex="col", constrained_layout=True)
        for column, (profile_name, data) in enumerate(
            [("slow, 1 ns", slow), ("fast, 5 ps", fast)]
        ):
            for row, (suffix, ylabel) in enumerate(
                [("pad_v", "pad voltage (V)"), ("ku", "Ku"), ("kd", "Kd")]
            ):
                ax = axes[row, column]
                ax.plot(
                    data["time_ns"],
                    data[f"hspice_ibis_{suffix}"],
                    color="#111111",
                    lw=2.7,
                    label="HSPICE native IBIS",
                )
                ax.plot(
                    data["time_ns"],
                    data[f"legacy_{suffix}"],
                    color="#1769aa",
                    lw=1.8,
                    label="ngspice legacy pybis",
                )
                clean.style_axis(ax, ylabel, case)
                if row == 0:
                    ax.set_title(profile_name, fontweight="bold")
                if row == 2:
                    ax.set_xlabel("time (ns)")
            axes[2, column].axhline(0, color="#777777", lw=0.8)
        axes[0, 0].legend(frameon=False, loc="upper center")
        fig.suptitle(case.title, fontweight="bold")
        path = out_dir / "03_legacy_slow_fast_vs_hspice" / f"{case.case_id}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=170)
        plt.close(fig)
        groups["legacy"].append(path)

    for name, paths in groups.items():
        clean.contact_sheet(paths, out_dir / f"{name}_contact_sheet.png", columns=2)


def write_numeric_failures() -> list[dict[str, object]]:
    candidates = [
        (
            "slow_1ns",
            "dual_hybrid",
            "edge_1ps_base_50r_2pf",
            "hybrid_state_timestep_collapse",
            OUT_ROOT
            / "slow_1ns"
            / "cases"
            / "edge_1ps_base_50r_2pf"
            / "ngspice_dual_hybrid",
        ),
        (
            "fast_5ps",
            "gate_full",
            "edge_1ps_base_50r_2pf",
            "directional_map_branch_chatter_near_settled_state",
            OUT_ROOT
            / "fast_5ps"
            / "cases"
            / "edge_1ps_base_50r_2pf"
            / "ngspice_gate_full",
        ),
    ]
    rows: list[dict[str, object]] = []
    for profile, flow, case_id, reason, directory in candidates:
        log = directory / "ngspice_stdout.log"
        raw_files = list(directory.glob("*.raw"))
        text = log.read_text(errors="replace") if log.exists() else ""
        rows.append(
            {
                "profile": profile,
                "case_id": case_id,
                "flow": flow,
                "status": "NUMERIC_FAIL" if "TIMEOUT" in text else "NOT_RUN",
                "reason": reason if "TIMEOUT" in text else "",
                "timeout_s": 240 if "TIMEOUT after 240 seconds" in text else "",
                "partial_raw_bytes": raw_files[0].stat().st_size if raw_files else 0,
                "log": str(log.relative_to(ROOT)) if log.exists() else "",
            }
        )
    write_csv(OUT_ROOT / "numeric_failures.csv", rows)
    return rows


def write_readme(
    fit_rows: list[dict[str, object]],
    metric_rows: list[dict[str, object]],
    cache_rows: list[dict[str, object]],
) -> None:
    lookup = {
        (str(row["profile"]), str(row["case_id"]), str(row["flow"])): row
        for row in metric_rows
    }
    lines = [
        "# ex2 Slow/Fast IBIS and Gate-State Experiment",
        "",
        "## Headline Findings",
        "",
        "- The original `ex2/buffer.ibs` is a valid native-IBIS artifact but is not usable for reliable pybis Ku/Kd extraction: its falling solve is singular and its rising solve is strongly ill-conditioned.",
        "- Controlled regeneration with complementary `50 ohm to 0 V` and `50 ohm to 3.3 V` fixtures removes the singularity for both 1 ns and 5 ps input-edge models.",
        "- The corrected tables have clean settled endpoints in both profiles; unlike fast `io_buf`, ex2 does not show a boundary-sample coefficient impulse.",
        "- The directional-residual reconstruction still misses the strict normal-table gate in both profiles. Gate-state transient results are therefore diagnostic, not production-ready.",
        "- The dual-residual reversal hybrid timed out on the slow-profile complete-edge control after collapsing to tiny timesteps near the falling edge. Its partial raw/log artifacts are preserved as a numerical-failure result; it was not repeated across the matrix.",
        "- The original fast-profile full gate-state model times out because roundoff near a settled state repeatedly switches between unequal directional PWL maps.",
        "- A stable-selector diagnostic keeps the same fit and state equations but selects direction from the delayed command target. It completes all fast-profile cases without timestep collapse.",
        "- `ex2` has a shared final-stage gate (`n4`) for both PMOS and NMOS networks, so structurally it is closer to `inv_chain` than to the independently gated tri-state `io_buf` output stage.",
        "- Slow profile: legacy is best for the complete edge (`5.6 mV` pad RMSE), while gate-state is much better for 1 ns interrupted high/low pulses (`24.8/28.4 mV` versus legacy `670.7/426.2 mV`).",
        "- Slow profile: that improvement does not extend to every width. At 500 ps high, gate-state still has `239.9 mV` pad RMSE and Ku/Kd RMSE `0.264/0.293`; at 50 ps high the small pad error hides a large Kd error (`0.461`).",
        "- Fast profile: legacy remains strong for complete and 2 ns pulses (`7.0-16.2 mV` pad RMSE), but fails 50-500 ps pulses by replaying a nearly full edge.",
        "- Fast profile: stable gate-state improves the 1 ns high pulse from `207.4 mV` to `22.3 mV` pad RMSE and Ku/Kd RMSE from `0.302/0.059` to `0.060/0.044`.",
        "- Fast profile: the stable result is not general. At 50 ps high its `12.6 mV` pad RMSE hides `0.442` Kd RMSE; at 1 ns low Kd improves but Ku and pad do not.",
        "- The fast native-IBIS complete edge is much closer to transistor timing than the slow native-IBIS edge (`36.1 mV` versus `777.7 mV` pad RMSE). The characterization slew is therefore materially encoded in this model's V-T timing.",
        "",
        "## Test Bench",
        "",
        "- Supply: `3.3 V`; temperature: `27 C`.",
        "- Direct load: `50 ohm || 2 pF`; no channel or transmission line.",
        "- Under this heavy load, the transistor output settles near `1.545 V`, sourcing about `30.9 mA`; this corresponds to an effective pullup resistance of about `56.8 ohm`.",
        "- Digital stimulus edge: `1 ps` in every comparison.",
        "- HSPICE transistor reference: `ex2/buffer.sp` plus `ex2/hspice.mod`.",
        "- HSPICE native IBIS reference and every ngspice model use the same PWL command and load.",
        "",
        "## Offline Gate",
        "",
        "| Profile | Worst RMSE | Worst max error | Gate |",
        "|---|---:|---:|---|",
    ]
    for row in fit_rows:
        lines.append(
            f"| {row['profile']} | {float(row['worst_rmse']):.6f} | "
            f"{float(row['worst_max_error']):.6f} | {row['gate']} |"
        )
    lines.extend(
        [
            "",
            "## Relation To io_buf And inv_chain",
            "",
            "| Property | inv_chain | ex2 | io_buf |",
            "|---|---|---|---|",
            "| Final-stage control | Shared inverter gate | Shared `n4` gate | Separate pullup `n2` and pulldown `n3` gates |",
            "| Fast fitted state tau | About `0.020-0.038 ns` | About `0.177-0.262 ns` | Fast extraction has corrupted boundary state; slow tau spans `0.237-1.284 ns` |",
            "| Normal reconstruction | PASS for slow and fast | FAIL for slow and fast | Slow residual PASS; fast model invalid for this fit |",
            "| Main interpretation | Fast, clean single-state behavior | Shared-gate topology but slower and more waveform-structured | Independent tri-state paths and strongly asymmetric internal timing |",
            "",
            "`ex2` is structurally closer to `inv_chain`, but dynamically it is an intermediate case. "
            "Its hidden state is much slower than `inv_chain`, while its endpoints are cleaner and its output control is less independent than `io_buf`.",
            "",
            "## Clean Outputs",
            "",
            "- `<profile>/plots/01_legacy_vs_hspice_ibis/`: pad, Ku, and Kd.",
            "- `<profile>/plots/02_gate_full_vs_hspice_ibis/`: full directional-residual model.",
            "- `<profile>/plots/02b_gate_stable_vs_hspice_ibis/`: stable-selector directional-residual diagnostic.",
            "- `<profile>/plots/03_dual_hybrid_vs_hspice_ibis/`: present only for completed optional hybrid runs.",
            "- `<profile>/plots/04_all_pad_references/`: native IBIS, transistor, and completed ngspice pad traces.",
        "- `<profile>/waveform_data/`: aligned numeric CSV behind the plots.",
        "- `cross_profile_plots/`: direct slow-IBIS, fast-IBIS, transistor, and legacy profile comparisons.",
        "- `numeric_failures.csv`: preserved hybrid/fast-gate timeout classifications and partial-raw sizes.",
            "- `metrics.csv`: all profile/case/flow metrics.",
            "",
            "## Selected Metrics",
            "",
            "| Profile | Case | Flow | Pad RMSE (mV) | Ku RMSE | Kd RMSE |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for profile in PROFILES:
        for case in CASES:
            for flow in ["legacy", "gate_full", "gate_stable", "dual_hybrid"]:
                row = lookup.get((profile, case.case_id, flow))
                if row is None:
                    continue
                lines.append(
                    f"| {profile} | {case.case_id} | {flow} | "
                    f"{float(row['pad_v_rmse']) * 1e3:.3f} | "
                    f"{float(row['ku_rmse']):.5f} | {float(row['kd_rmse']):.5f} |"
                )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A low pad error alone is not a pass. The regenerated IBIS must first support a stable Ku/Kd solve, then a candidate must preserve normal Ku/Kd and improve interrupted pad, Ku, and Kd together. Neither gate-state profile passes that full claim yet.",
            "",
            f"HSPICE reference records: `{len(cache_rows)}`.",
        ]
    )
    (OUT_ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ex2 slow/fast clean comparison.")
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--timeout-s", type=int, default=240)
    parser.add_argument("--profile", action="append", choices=sorted(PROFILES), default=[])
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument(
        "--include-dual-hybrid",
        action="store_true",
        help="Run the known-stiff reversal hybrid in addition to legacy and gate-full.",
    )
    parser.add_argument(
        "--flow",
        action="append",
        choices=["legacy", "gate_full", "gate_stable"],
        default=[],
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    original_observability_report()
    selected_profiles = args.profile or list(PROFILES)
    active_flows = args.flow or ["legacy", "gate_full"]
    if args.include_dual_hybrid:
        active_flows.append("dual_hybrid")
    selected_cases = CASES
    if args.case:
        by_id = {case.case_id: case for case in CASES}
        selected_cases = [by_id[case_id] for case_id in args.case]

    all_metrics: list[dict[str, object]] = (
        read_csv(OUT_ROOT / "metrics.csv") if args.resume else []
    )
    all_cache: list[dict[str, object]] = (
        read_csv(OUT_ROOT / "reference_cache_manifest.csv") if args.resume else []
    )
    all_fits: list[dict[str, object]] = (
        read_csv(OUT_ROOT / "gate_fit_summary.csv") if args.resume else []
    )
    if args.report_only:
        all_metrics = read_csv(OUT_ROOT / "metrics.csv")
        all_cache = read_csv(OUT_ROOT / "reference_cache_manifest.csv")
        all_fits = read_csv(OUT_ROOT / "gate_fit_summary.csv")
        cross_profile_plots()
        write_numeric_failures()
        write_readme(all_fits, all_metrics, all_cache)
        print(f"OUT_ROOT={OUT_ROOT}")
        return 0
    for profile in selected_profiles:
        ibis = PROFILES[profile]
        profile_dir = OUT_ROOT / profile
        configure_clean(profile_dir)
        for path in [
            clean.OUT_DIR,
            clean.COMMON_DIR,
            clean.CASES_DIR,
            clean.PLOTS_DIR,
            clean.DATA_DIR,
            clean.FIT_DIR,
        ]:
            clean.ensure_dir(path)
        fit = offline_fit(ibis, profile_dir)
        all_fits = [row for row in all_fits if str(row.get("profile")) != profile]
        all_fits.append(fit)
        models = prepare_models(ibis, active_flows)
        image_groups: dict[str, list[Path]] = {flow: [] for flow in active_flows}
        image_groups["pad_all"] = []
        for index, case in enumerate(selected_cases, start=1):
            print(f"[{profile} {index}/{len(selected_cases)}] {case.case_id}", flush=True)
            native, native_cache = run_native(case, ibis, profile, args.hspice, args.timeout_s)
            transistor, transistor_cache = run_transistor(case, args.hspice, args.timeout_s)
            ng = {
                flow: run_ngspice(case, flow, model, args.ngspice, args.timeout_s)
                for flow, model in models.items()
            }
            data = align(case, native, transistor, ng)
            rows = metrics(case, data)
            for row in rows:
                row["profile"] = profile
            replaced_flows = {str(row["flow"]) for row in rows}
            all_metrics = [
                row
                for row in all_metrics
                if not (
                    str(row.get("profile")) == profile
                    and str(row.get("case_id")) == case.case_id
                    and str(row.get("flow")) in replaced_flows
                )
            ]
            all_metrics.extend(rows)
            native_cache["profile"] = profile
            transistor_cache["profile"] = profile
            all_cache = [
                row
                for row in all_cache
                if not (
                    str(row.get("profile")) == profile
                    and str(row.get("case_id")) == case.case_id
                )
            ]
            all_cache.extend([native_cache, transistor_cache])
            for folder, flow in [
                ("01_legacy_vs_hspice_ibis", "legacy"),
                ("02_gate_full_vs_hspice_ibis", "gate_full"),
                ("02b_gate_stable_vs_hspice_ibis", "gate_stable"),
                ("03_dual_hybrid_vs_hspice_ibis", "dual_hybrid"),
            ]:
                if flow not in active_flows:
                    continue
                image_groups[flow].append(
                    plot_flow(
                        case,
                        data,
                        flow,
                        clean.PLOTS_DIR / folder / f"{case.case_id}.png",
                    )
                )
            image_groups["pad_all"].append(
                plot_pad_all(
                    case,
                    data,
                    clean.PLOTS_DIR / "04_all_pad_references" / f"{case.case_id}.png",
                )
            )
            write_csv(OUT_ROOT / "metrics.csv", all_metrics)
            write_csv(OUT_ROOT / "reference_cache_manifest.csv", all_cache)
        for flow, images in image_groups.items():
            clean.contact_sheet(
                images,
                clean.PLOTS_DIR / f"{flow}_contact_sheet.png",
                columns=2,
            )
    write_csv(OUT_ROOT / "gate_fit_summary.csv", all_fits)
    write_csv(OUT_ROOT / "metrics.csv", all_metrics)
    write_csv(OUT_ROOT / "reference_cache_manifest.csv", all_cache)
    write_readme(all_fits, all_metrics, all_cache)
    print(f"OUT_ROOT={OUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
