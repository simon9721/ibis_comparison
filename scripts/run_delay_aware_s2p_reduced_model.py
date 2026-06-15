from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from add_s11_tx_correction import fit_tx_fast  # noqa: E402
from compare_sparam_transient_audits import compare_case  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from run_delay_aware_parallel_sparam_model import (  # noqa: E402
    active_error,
    crossing,
    lowpass,
    model_waveform,
    source_voltage,
    tx_model_waveform,
)
from run_native_hspice_sparam_audit import hspice_metrics, lis_notes  # noqa: E402
from run_sparam_conversion_quality_study import (  # noqa: E402
    DEFAULT_HSPICE,
    DEFAULT_NGSPICE,
    audit_cases,
    edge_crossings,
    rel,
    run_hspice_case,
    run_ngspice_cases,
    waveform_levels,
)


CASE_BY_EDGE = {
    5: "audit_amp1p5_edge5_r50",
    50: "audit_amp1p5_edge50_r50",
    500: "audit_amp1p5_edge500_r50",
}


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


def strength_label(strength: float) -> str:
    return f"{strength:.3f}".rstrip("0").rstrip(".").replace(".", "p")


def parse_strengths(text: str) -> list[float]:
    out: list[float] = []
    for item in text.split(","):
        item = item.strip()
        if item:
            out.append(float(item))
    return out or [0.0]


def parse_float_list(text: str) -> list[float]:
    out: list[float] = []
    for item in text.split(","):
        item = item.strip()
        if item:
            out.append(float(item))
    return out


def parse_tau_pairs(text: str) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Expected fast:slow tau pair, got {item!r}")
        fast, slow = item.split(":", 1)
        pairs.append((float(fast), float(slow)))
    return pairs


def run_native_hspice(
    touchstone: Path,
    hspice: Path,
    out_dir: Path,
    stop_ns: float,
    timeout: int,
    reuse_existing: bool,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in audit_cases(stop_ns):
        prefix = out_dir.resolve() / f"{case.name}_hspice"
        if reuse_existing and prefix.with_suffix(".tr0").exists():
            row: dict[str, object] = {
                "case": case.name,
                "hspice_return_code": "reused",
                "hspice_tr0": rel(prefix.with_suffix(".tr0")),
                "hspice_lis": rel(prefix.with_suffix(".lis")),
            }
        else:
            row = run_hspice_case(hspice.resolve(), touchstone.resolve(), 2, out_dir.resolve(), case, timeout)
        tr0 = ROOT / str(row.get("hspice_tr0", ""))
        lis = ROOT / str(row.get("hspice_lis", ""))
        if tr0.exists():
            row.update(hspice_metrics(tr0, 2, case.amplitude_v))
        row.update(lis_notes(lis))
        rows.append(row)
    write_csv(out_dir / "native_hspice_audit.csv", rows)
    return rows


def load_refs(hspice_dir: Path, stop_ns: float, step_ps: float) -> dict[int, dict[str, np.ndarray]]:
    refs: dict[int, dict[str, np.ndarray]] = {}
    step_s = step_ps * 1e-12
    grid = np.arange(0.0, stop_ns * 1e-9 + 0.5 * step_s, step_s)
    for edge, case in CASE_BY_EDGE.items():
        data = parse_hspice_tr0(hspice_dir / f"{case}_hspice.tr0")
        p1 = np.interp(grid, data["time"], data["v(p1)"])
        p2 = np.interp(grid, data["time"], data["v(p2)"])
        tx_low, tx_active, tx_threshold, tx_active_high = waveform_levels(grid, p1)
        rx_low, rx_active, rx_threshold, rx_active_high = waveform_levels(grid, p2)
        tx_rise, tx_fall = edge_crossings(grid, p1, tx_threshold, tx_active_high)
        rx_rise, rx_fall = edge_crossings(grid, p2, rx_threshold, rx_active_high)
        refs[edge] = {
            "time": grid,
            "v_p1": p1,
            "v_p2": p2,
            "v_p3": p2,
            "tx_low": tx_low,
            "tx_active": tx_active,
            "tx_threshold": tx_threshold,
            "tx_active_high": tx_active_high,
            "rx_low": rx_low,
            "rx_active": rx_active,
            "threshold": rx_threshold,
            "rx_active_high": rx_active_high,
            "tx_rise": tx_rise,
            "tx_fall": tx_fall,
            "rise": rx_rise,
            "fall": rx_fall,
        }
    return refs


def estimate_initial_delay_ns(refs: dict[int, dict[str, np.ndarray]]) -> float:
    delays: list[float] = []
    for ref in refs.values():
        for tx_key, rx_key in (("tx_rise", "rise"), ("tx_fall", "fall")):
            tx = ref.get(tx_key)
            rx = ref.get(rx_key)
            if tx is not None and rx is not None:
                delays.append((float(rx) - float(tx)) * 1e9)
    if delays:
        return float(np.nanmedian(delays))
    return 0.2


def estimate_loaded_gain(refs: dict[int, dict[str, np.ndarray]], amplitude_v: float = 1.5) -> float:
    gains: list[float] = []
    matched_step_v = 0.5 * amplitude_v
    for ref in refs.values():
        low = float(ref["rx_low"])
        active = float(ref["rx_active"])
        if matched_step_v > 0:
            gains.append((active - low) / matched_step_v)
    if gains:
        return float(np.nanmedian(gains))
    return 0.8


def fit_s21_model(
    refs: dict[int, dict[str, np.ndarray]],
    branches: int,
    initial_delay_ns: float,
    delay_window_ns: float,
    tail_branches: int,
    maxiter: int,
    popsize: int,
) -> dict[str, object]:
    from scipy.optimize import differential_evolution, minimize

    target_gain = estimate_loaded_gain(refs)
    gain_bound = max(2.5, abs(target_gain) + 1.0)
    bounds: list[tuple[float, float]] = [(initial_delay_ns - delay_window_ns, initial_delay_ns + delay_window_ns)]
    bounds.extend([(-2.5, 1.3)] * branches)  # log10 tau ns
    bounds.extend([(-gain_bound, gain_bound)] * branches)
    for _ in range(tail_branches):
        bounds.extend([(-2.5, 0.4), (-1.2, 1.7), (-1.5, 1.5)])

    def unpack(vec: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        delay_s = float(vec[0]) * 1e-9
        tau_ns = 10 ** np.asarray(vec[1 : 1 + branches], dtype=float)
        gains = np.asarray(vec[1 + branches : 1 + 2 * branches], dtype=float)
        tail_offset = 1 + 2 * branches
        tail_fast_ns: list[float] = []
        tail_slow_ns: list[float] = []
        tail_gains: list[float] = []
        for idx in range(tail_branches):
            base = tail_offset + 3 * idx
            tail_fast_ns.append(float(10 ** vec[base]))
            tail_slow_ns.append(float(10 ** vec[base + 1]))
            tail_gains.append(float(vec[base + 2]))
        order = np.argsort(tau_ns)
        tail_fast = np.asarray(tail_fast_ns, dtype=float)
        tail_slow = np.asarray(tail_slow_ns, dtype=float)
        tail_gain_array = np.asarray(tail_gains, dtype=float)
        tail_order = np.argsort(tail_slow) if len(tail_slow) else np.asarray([], dtype=int)
        return (
            delay_s,
            tau_ns[order] * 1e-9,
            gains[order],
            tail_fast[tail_order] * 1e-9,
            tail_slow[tail_order] * 1e-9,
            tail_gain_array[tail_order],
        )

    def objective(vec: np.ndarray) -> float:
        delay_s, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains = unpack(vec)
        if len(tail_slow_s) and np.any(tail_slow_s <= 1.05 * tail_fast_s):
            return 1e3 + float(np.sum(np.maximum(0.0, 1.05 * tail_fast_s - tail_slow_s))) * 1e12
        total = 0.0
        for edge, ref in refs.items():
            t = ref["time"]
            pred = model_waveform(t, edge, delay_s, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains)
            rmse, maxabs = active_error(ref["v_p2"], pred)
            total += rmse + 0.25 * maxabs
            first = crossing(t, pred, float(ref["threshold"]), bool(ref["rx_active_high"]), 0.5e-9)
            second = crossing(t, pred, float(ref["threshold"]), not bool(ref["rx_active_high"]), 8.5e-9)
            if first is None or second is None or ref["rise"] is None or ref["fall"] is None:
                total += 10.0
            else:
                total += 2e8 * abs(first - float(ref["rise"]))
                total += 2e8 * abs(second - float(ref["fall"]))
        total += 0.004 * abs(float(np.sum(gains)) - target_gain)
        total += 0.0015 * float(np.sum(np.abs(gains)))
        total += 0.001 * float(np.sum(np.abs(tail_gains)))
        return float(total)

    tau_guess = np.geomspace(0.03, 4.0, branches)
    gain_guess = np.full(branches, target_gain / max(branches, 1))
    tail_seed: list[float] = []
    for idx in range(tail_branches):
        tail_seed.extend([math.log10(0.05 * (idx + 1)), math.log10(3.0 * (idx + 1)), 0.02])
    seed = np.array([initial_delay_ns, *np.log10(tau_guess), *gain_guess, *tail_seed])
    de = differential_evolution(objective, bounds, seed=23, maxiter=maxiter, popsize=popsize, tol=2e-4, polish=False, workers=1)
    best_start = de.x if de.fun < objective(seed) else seed
    local = minimize(objective, best_start, method="Nelder-Mead", options={"maxiter": 2500, "xatol": 1e-6, "fatol": 1e-7})
    best = local.x if local.fun <= de.fun else de.x
    delay_s, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains = unpack(best)
    return {
        "delay_s": delay_s,
        "delay_ns": delay_s * 1e9,
        "taus_s": taus_s,
        "taus_ns": taus_s * 1e9,
        "gains": gains,
        "tail_fast_s": tail_fast_s,
        "tail_fast_ns": tail_fast_s * 1e9,
        "tail_slow_s": tail_slow_s,
        "tail_slow_ns": tail_slow_s * 1e9,
        "tail_gains": tail_gains,
        "dc_gain_to_load": float(np.sum(gains)),
        "target_gain_to_load": target_gain,
        "objective": objective(best),
    }


def ring_basis_waveform(t: np.ndarray, edge_ps: float, delay_s: float, fast_s: float, slow_s: float) -> np.ndarray:
    x = 0.5 * source_voltage(t - delay_s, edge_ps)
    return lowpass(t, x, fast_s) - lowpass(t, x, slow_s)


def s21_model_waveform(t: np.ndarray, edge_ps: float, fit: dict[str, object]) -> np.ndarray:
    y = model_waveform(
        t,
        edge_ps,
        float(fit["delay_s"]),
        np.asarray(fit["taus_s"], dtype=float),
        np.asarray(fit["gains"], dtype=float),
        np.asarray(fit.get("tail_fast_s", []), dtype=float),
        np.asarray(fit.get("tail_slow_s", []), dtype=float),
        np.asarray(fit.get("tail_gains", []), dtype=float),
    )
    ring_delay_s = np.asarray(fit.get("ring_delay_s", []), dtype=float)
    ring_fast_s = np.asarray(fit.get("ring_fast_s", []), dtype=float)
    ring_slow_s = np.asarray(fit.get("ring_slow_s", []), dtype=float)
    ring_gains = np.asarray(fit.get("ring_gains", []), dtype=float)
    for delay_s, fast_s, slow_s, gain in zip(ring_delay_s, ring_fast_s, ring_slow_s, ring_gains):
        y += float(gain) * ring_basis_waveform(t, edge_ps, float(delay_s), float(fast_s), float(slow_s))
    return y


def fit_ring_correction(
    refs: dict[int, dict[str, np.ndarray]],
    fit: dict[str, object],
    delay_ns: list[float],
    tau_pairs_ns: list[tuple[float, float]],
    reg: float,
    gain_bound: float,
) -> dict[str, object]:
    if not delay_ns or not tau_pairs_ns:
        return {
            "ring_delay_s": np.asarray([], dtype=float),
            "ring_delay_ns": np.asarray([], dtype=float),
            "ring_fast_s": np.asarray([], dtype=float),
            "ring_fast_ns": np.asarray([], dtype=float),
            "ring_slow_s": np.asarray([], dtype=float),
            "ring_slow_ns": np.asarray([], dtype=float),
            "ring_gains": np.asarray([], dtype=float),
            "ring_fit_cost": 0.0,
        }
    from scipy.optimize import lsq_linear

    specs: list[tuple[float, float, float]] = []
    for delay in delay_ns:
        for fast, slow in tau_pairs_ns:
            if slow <= fast:
                raise ValueError(f"Ring slow tau must be greater than fast tau: {fast}:{slow}")
            specs.append((delay, fast, slow))

    basis_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    for edge, ref in refs.items():
        t = ref["time"]
        base = s21_model_waveform(t, edge, fit)
        residual = ref["v_p2"] - base
        high_residual = np.abs(residual) >= max(0.01, 0.10 * float(np.nanmax(np.abs(residual))))
        active = np.abs(ref["v_p2"] - float(ref["rx_low"])) >= 0.01 * max(abs(float(ref["rx_active"]) - float(ref["rx_low"])), 1e-12)
        mask = high_residual | active
        cols = [
            ring_basis_waveform(t, edge, float(delay) * 1e-9, float(fast) * 1e-9, float(slow) * 1e-9)
            for delay, fast, slow in specs
        ]
        basis_rows.append(np.column_stack(cols)[mask])
        target_rows.append(residual[mask])

    matrix = np.vstack(basis_rows)
    target = np.concatenate(target_rows)
    if reg > 0:
        matrix = np.vstack([matrix, reg * np.eye(matrix.shape[1])])
        target = np.concatenate([target, np.zeros(matrix.shape[1])])
    result = lsq_linear(matrix, target, bounds=(-gain_bound, gain_bound), lsmr_tol="auto", max_iter=500)
    coeff = result.x
    delays = np.asarray([spec[0] for spec in specs], dtype=float)
    fasts = np.asarray([spec[1] for spec in specs], dtype=float)
    slows = np.asarray([spec[2] for spec in specs], dtype=float)
    return {
        "ring_delay_s": delays * 1e-9,
        "ring_delay_ns": delays,
        "ring_fast_s": fasts * 1e-9,
        "ring_fast_ns": fasts,
        "ring_slow_s": slows * 1e-9,
        "ring_slow_ns": slows,
        "ring_gains": coeff,
        "ring_fit_cost": float(result.cost),
    }


def tx_correction_model_lines(fit: dict[str, object], strength: float, r_stage: float = 1000.0) -> list[str]:
    lines = ["* S11-like 50 ohm bench input correction.", "Rtxsum txsum 0 1"]
    tx_taus_ns = np.asarray(fit.get("tx_taus_ns", []), dtype=float)
    tx_gains = np.asarray(fit.get("tx_gains", []), dtype=float)
    for idx, (tau_ns, gain) in enumerate(zip(tx_taus_ns, tx_gains), start=1):
        cap_f = (float(tau_ns) * 1e-9) / r_stage
        lines.extend(
            [
                f"Etxsrc{idx} txsrc{idx} 0 pin 0 1",
                f"Rtx{idx} txsrc{idx} tx{idx} {r_stage:.12g}",
                f"Ctx{idx} tx{idx} 0 {cap_f:.12g}",
                f"Gtx{idx} 0 txsum tx{idx} 0 {float(strength * gain):.12g}",
            ]
        )
    tx_tail_fast_ns = np.asarray(fit.get("tx_tail_fast_ns", []), dtype=float)
    tx_tail_slow_ns = np.asarray(fit.get("tx_tail_slow_ns", []), dtype=float)
    tx_tail_gains = np.asarray(fit.get("tx_tail_gains", []), dtype=float)
    for idx, (fast_ns, slow_ns, gain) in enumerate(zip(tx_tail_fast_ns, tx_tail_slow_ns, tx_tail_gains), start=1):
        fast_cap_f = (float(fast_ns) * 1e-9) / r_stage
        slow_cap_f = (float(slow_ns) * 1e-9) / r_stage
        lines.extend(
            [
                f"Etxtailfsrc{idx} txtailfsrc{idx} 0 pin 0 1",
                f"Rtxtailf{idx} txtailfsrc{idx} txtailf{idx} {r_stage:.12g}",
                f"Ctx_tailf{idx} txtailf{idx} 0 {fast_cap_f:.12g}",
                f"Gtxtailf{idx} 0 txsum txtailf{idx} 0 {float(strength * gain):.12g}",
                f"Etxtailssrc{idx} txtailssrc{idx} 0 pin 0 1",
                f"Rtxtails{idx} txtailssrc{idx} txtails{idx} {r_stage:.12g}",
                f"Ctx_tails{idx} txtails{idx} 0 {slow_cap_f:.12g}",
                f"Gtxtails{idx} 0 txsum txtails{idx} 0 {-float(strength * gain):.12g}",
            ]
        )
    lines.extend(["Etxport p1 pin txsum 0 1", "Rpin_leak pin 0 1e12"])
    return lines


def write_s2p_model(path: Path, fit: dict[str, object], s11_strength: float = 0.0, r_stage: float = 1000.0) -> None:
    delay_ns = float(fit["delay_ns"])
    taus_ns = np.asarray(fit["taus_ns"], dtype=float)
    gains = np.asarray(fit["gains"], dtype=float)
    tail_fast_ns = np.asarray(fit.get("tail_fast_ns", []), dtype=float)
    tail_slow_ns = np.asarray(fit.get("tail_slow_ns", []), dtype=float)
    tail_gains = np.asarray(fit.get("tail_gains", []), dtype=float)
    ring_delay_ns = np.asarray(fit.get("ring_delay_ns", []), dtype=float)
    ring_fast_ns = np.asarray(fit.get("ring_fast_ns", []), dtype=float)
    ring_slow_ns = np.asarray(fit.get("ring_slow_ns", []), dtype=float)
    ring_gains = np.asarray(fit.get("ring_gains", []), dtype=float)
    has_tx_correction = abs(s11_strength) > 0 and (
        len(np.asarray(fit.get("tx_gains", []), dtype=float))
        or len(np.asarray(fit.get("tx_tail_gains", []), dtype=float))
    )
    input_node = "pin" if has_tx_correction else "p1"
    lines = [
        "* 2-port delay-aware reduced S-parameter macromodel",
        "* Fitted for the 50 ohm HSPICE audit bench.",
        ".subckt s_equivalent p1 p2",
    ]
    if has_tx_correction:
        lines.extend(tx_correction_model_lines(fit, s11_strength, r_stage=r_stage))
    lines.extend(
        [
            f"Tdelay {input_node} 0 ndelay 0 Z0=50 TD={delay_ns:.12g}n",
            "Rdelay_term ndelay 0 50",
            "Rsum sum 0 1",
        ]
    )
    for idx, (tau_ns, gain) in enumerate(zip(taus_ns, gains), start=1):
        cap_f = (float(tau_ns) * 1e-9) / r_stage
        lines.extend(
            [
                f"Ebrsrc{idx} brsrc{idx} 0 ndelay 0 1",
                f"Rbr{idx} brsrc{idx} br{idx} {r_stage:.12g}",
                f"Cbr{idx} br{idx} 0 {cap_f:.12g}",
                f"Gsum{idx} 0 sum br{idx} 0 {float(gain):.12g}",
            ]
        )
    for idx, (fast_ns, slow_ns, gain) in enumerate(zip(tail_fast_ns, tail_slow_ns, tail_gains), start=1):
        fast_cap_f = (float(fast_ns) * 1e-9) / r_stage
        slow_cap_f = (float(slow_ns) * 1e-9) / r_stage
        lines.extend(
            [
                f"Etailfsrc{idx} tailfsrc{idx} 0 ndelay 0 1",
                f"Rtailf{idx} tailfsrc{idx} tailf{idx} {r_stage:.12g}",
                f"Ctailf{idx} tailf{idx} 0 {fast_cap_f:.12g}",
                f"Gtailf{idx} 0 sum tailf{idx} 0 {float(gain):.12g}",
                f"Etailssrc{idx} tailssrc{idx} 0 ndelay 0 1",
                f"Rtails{idx} tailssrc{idx} tails{idx} {r_stage:.12g}",
                f"Ctails{idx} tails{idx} 0 {slow_cap_f:.12g}",
                f"Gtails{idx} 0 sum tails{idx} 0 {-float(gain):.12g}",
            ]
        )
    for idx, (delay_ns, fast_ns, slow_ns, gain) in enumerate(
        zip(ring_delay_ns, ring_fast_ns, ring_slow_ns, ring_gains),
        start=1,
    ):
        fast_cap_f = (float(fast_ns) * 1e-9) / r_stage
        slow_cap_f = (float(slow_ns) * 1e-9) / r_stage
        base = f"ringbase{idx}"
        if abs(float(delay_ns)) > 1e-15:
            lines.extend(
                [
                    f"Tringdelay{idx} {input_node} 0 {base} 0 Z0=1e12 TD={float(delay_ns):.12g}n",
                    f"Rringdelay_term{idx} {base} 0 1e12",
                ]
            )
        else:
            lines.append(f"Eringbase{idx} {base} 0 {input_node} 0 1")
        lines.extend(
            [
                f"Eringfsrc{idx} ringfsrc{idx} 0 {base} 0 1",
                f"Rringf{idx} ringfsrc{idx} ringf{idx} {r_stage:.12g}",
                f"Cringf{idx} ringf{idx} 0 {fast_cap_f:.12g}",
                f"Gringf{idx} 0 sum ringf{idx} 0 {float(gain):.12g}",
                f"Eringssrc{idx} ringssrc{idx} 0 {base} 0 1",
                f"Rrings{idx} ringssrc{idx} rings{idx} {r_stage:.12g}",
                f"Crings{idx} rings{idx} 0 {slow_cap_f:.12g}",
                f"Grings{idx} 0 sum rings{idx} 0 {-float(gain):.12g}",
            ]
        )
    lines.extend(["Eout outdrv 0 sum 0 2", "Rout outdrv p2 50", ".ends s_equivalent", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="ascii")


def plot_fit_preview(refs: dict[int, dict[str, np.ndarray]], fit: dict[str, object], path: Path) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(14, 8.2), sharex=True, constrained_layout=True)
    delay_s = float(fit["delay_s"])
    taus_s = np.asarray(fit["taus_s"], dtype=float)
    gains = np.asarray(fit["gains"], dtype=float)
    tail_fast_s = np.asarray(fit.get("tail_fast_s", []), dtype=float)
    tail_slow_s = np.asarray(fit.get("tail_slow_s", []), dtype=float)
    tail_gains = np.asarray(fit.get("tail_gains", []), dtype=float)
    tx_taus_s = np.asarray(fit.get("tx_taus_s", []), dtype=float)
    tx_gains = np.asarray(fit.get("tx_gains", []), dtype=float)
    tx_tail_fast_s = np.asarray(fit.get("tx_tail_fast_s", []), dtype=float)
    tx_tail_slow_s = np.asarray(fit.get("tx_tail_slow_s", []), dtype=float)
    tx_tail_gains = np.asarray(fit.get("tx_tail_gains", []), dtype=float)
    for row_idx, edge in enumerate(sorted(refs)):
        ref = refs[edge]
        tx_pred = tx_model_waveform(ref["time"], edge, tx_taus_s, tx_gains, tx_tail_fast_s, tx_tail_slow_s, tx_tail_gains)
        rx_pred = s21_model_waveform(ref["time"], edge, fit)
        axes[row_idx, 0].plot(ref["time"] * 1e9, ref["v_p1"], label="HSPICE native S", linewidth=1.8)
        axes[row_idx, 0].plot(ref["time"] * 1e9, tx_pred, "--", label="TX correction fit", linewidth=1.45)
        axes[row_idx, 1].plot(ref["time"] * 1e9, ref["v_p2"], label="HSPICE native S", linewidth=1.8)
        axes[row_idx, 1].plot(ref["time"] * 1e9, rx_pred, "--", label="S21 fit", linewidth=1.45)
        axes[row_idx, 0].set_title(f"{edge} ps edge - TX/S11", loc="left", fontweight="bold")
        axes[row_idx, 1].set_title(f"{edge} ps edge - RX/S21", loc="left", fontweight="bold")
        for ax in axes[row_idx, :]:
            ax.grid(True, color="#d7dde6")
            ax.legend(frameon=False)
            ax.set_ylabel("Voltage (V)")
    axes[-1, 0].set_xlabel("Time (ns)")
    axes[-1, 1].set_xlabel("Time (ns)")
    fig.suptitle("2-port reduced model analytic fit preview", fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_selected_overview(hspice_dir: Path, ngspice_dir: Path, path: Path, title: str) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(14, 8.2), sharex=True, constrained_layout=True)
    for row_idx, (edge, case) in enumerate(CASE_BY_EDGE.items()):
        h = parse_hspice_tr0(hspice_dir / f"{case}_hspice.tr0")
        n = parse_ngspice_raw(ngspice_dir / f"{case}.raw")
        for col, sig, label in ((0, "v(p1)", "TX / input port"), (1, "v(p2)", "RX / output port")):
            ax = axes[row_idx, col]
            ax.plot(h["time"] * 1e9, h[sig], label="HSPICE native S", linewidth=1.8)
            ax.plot(n["time"] * 1e9, n[sig], "--", label="ngspice reduced", linewidth=1.45)
            ax.set_title(f"{edge} ps edge - {label}", loc="left", fontweight="bold")
            ax.set_ylabel("Voltage (V)")
            ax.grid(True, color="#d7dde6")
            ax.legend(frameon=False)
    axes[-1, 0].set_xlabel("Time (ns)")
    axes[-1, 1].set_xlabel("Time (ns)")
    fig.suptitle(title, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def summarize_rows(strength: float, compare_rows: list[dict[str, object]]) -> dict[str, object]:
    rx_rmse = [float(r["rx_active_rmse_v"]) for r in compare_rows if r.get("rx_active_rmse_v", "") != ""]
    rx_max = [float(r["rx_active_maxabs_v"]) for r in compare_rows if r.get("rx_active_maxabs_v", "") != ""]
    tx_rmse = [float(r["tx_active_rmse_v"]) for r in compare_rows if r.get("tx_active_rmse_v", "") != ""]
    rise_delta = [abs(float(r["rx_rise50_delta_ps"])) for r in compare_rows if r.get("rx_rise50_delta_ps", "") != ""]
    fall_delta = [abs(float(r["rx_fall50_delta_ps"])) for r in compare_rows if r.get("rx_fall50_delta_ps", "") != ""]
    fail_count = sum(1 for row in compare_rows if row.get("case_class") != "PASS")
    mean_rx = float(np.nanmean(rx_rmse)) if rx_rmse else float("nan")
    mean_tx = float(np.nanmean(tx_rmse)) if tx_rmse else float("nan")
    max_delay = max(rise_delta + fall_delta) if rise_delta or fall_delta else float("nan")
    score = fail_count * 100.0
    if math.isfinite(mean_rx):
        score += mean_rx / 0.02
    if math.isfinite(mean_tx):
        score += 0.8 * mean_tx / 0.05
    if math.isfinite(max_delay):
        score += 0.4 * max_delay / 25.0
    return {
        "s11_strength": strength,
        "case_count": len(compare_rows),
        "pass_count": len(compare_rows) - fail_count,
        "fail_count": fail_count,
        "rx_active_rmse_mean_v": mean_rx,
        "rx_active_rmse_max_v": max(rx_rmse) if rx_rmse else float("nan"),
        "rx_active_maxabs_max_v": max(rx_max) if rx_max else float("nan"),
        "tx_active_rmse_mean_v": mean_tx,
        "tx_active_rmse_max_v": max(tx_rmse) if tx_rmse else float("nan"),
        "max_abs_rx_edge_delta_ps": max_delay,
        "selection_score": score,
    }


def write_report(
    out_dir: Path,
    touchstone: Path,
    fit: dict[str, object],
    selected: dict[str, object],
    summaries: list[dict[str, object]],
) -> None:
    lines = [
        "# 2-port Delay-aware Reduced S-parameter Model",
        "",
        f"- Touchstone: `{rel(touchstone.resolve())}`",
        f"- Selected S11 strength: `{float(selected['s11_strength']):.4g}`",
        f"- Selected strength directory: `{selected['strength_dir']}`",
        f"- Selected overview plot: `{selected['overview_plot']}`",
        "",
        "## Fitted S21 Path",
        "",
        f"- Initial target gain to load: `{float(fit['target_gain_to_load']):.6g}`",
        f"- Fitted DC gain to load: `{float(fit['dc_gain_to_load']):.6g}`",
        f"- Explicit delay: `{float(fit['delay_ns']):.6g} ns`",
        f"- Branch taus: `{', '.join(f'{v:.6g} ns' for v in np.asarray(fit['taus_ns'], dtype=float))}`",
        f"- Branch gains: `{', '.join(f'{v:.6g}' for v in np.asarray(fit['gains'], dtype=float))}`",
    ]
    tail_gains = np.asarray(fit.get("tail_gains", []), dtype=float)
    if len(tail_gains):
        lines.extend(
            [
                f"- Tail fast taus: `{', '.join(f'{v:.6g} ns' for v in np.asarray(fit['tail_fast_ns'], dtype=float))}`",
                f"- Tail slow taus: `{', '.join(f'{v:.6g} ns' for v in np.asarray(fit['tail_slow_ns'], dtype=float))}`",
                f"- Tail gains: `{', '.join(f'{v:.6g}' for v in tail_gains)}`",
            ]
        )
    ring_gains = np.asarray(fit.get("ring_gains", []), dtype=float)
    if len(ring_gains):
        nonzero = int(np.sum(np.abs(ring_gains) > 1e-5))
        lines.extend(
            [
                f"- Ring/feedthrough basis terms: `{len(ring_gains)}` total, `{nonzero}` nonzero-ish",
                f"- Ring gain max abs: `{float(np.nanmax(np.abs(ring_gains))):.6g}`",
                f"- Ring delays: `{', '.join(f'{v:.6g} ns' for v in np.unique(np.asarray(fit['ring_delay_ns'], dtype=float)))}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Strength Sweep",
            "",
            "| S11 strength | pass | mean RX RMSE (mV) | max RX edge delta (ps) | mean TX RMSE (mV) | score |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summaries:
        lines.append(
            f"| {float(row['s11_strength']):.4g} | {int(row['pass_count'])}/{int(row['case_count'])} | "
            f"{1000 * float(row['rx_active_rmse_mean_v']):.4g} | "
            f"{float(row['max_abs_rx_edge_delta_ps']):.4g} | "
            f"{1000 * float(row['tx_active_rmse_mean_v']):.4g} | "
            f"{float(row['selection_score']):.4g} |"
        )
    lines.extend(
        [
            "",
            "## Key Files",
            "",
            "- `native_hspice/native_hspice_audit.csv`: HSPICE S-element run summary",
            "- `fit_preview.png`: analytic S21/S11 fit before ngspice",
            "- `strength_sweep.csv`: per-strength summary",
            "- `selected_model.sp`: duplicate of the selected ngspice model",
            "- `selected_comparison.csv`: duplicate of the selected HSPICE-vs-ngspice comparison table",
            "",
            "Note: the S11 correction is still bench-scoped. It improves this 50 ohm source/load audit, but it is not yet a general passive two-port reconstruction of S11/S12/S22.",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fit and audit a 2-port delay-aware reduced ngspice S-parameter model.")
    parser.add_argument("--touchstone", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--hspice", type=Path, default=DEFAULT_HSPICE)
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--stop-ns", type=float, default=12.0)
    parser.add_argument("--fit-step-ps", type=float, default=10.0)
    parser.add_argument("--initial-delay-ns", type=float, default=None)
    parser.add_argument("--delay-window-ns", type=float, default=0.75)
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--tail-branches", type=int, default=1)
    parser.add_argument("--tx-branches", type=int, default=5)
    parser.add_argument("--tx-tail-branches", type=int, default=2)
    parser.add_argument("--ring-delays-ns", default="0,0.04,0.08,0.14,0.22", help="Comma-separated fixed input-feedthrough pulse delays.")
    parser.add_argument("--ring-tau-pairs-ns", default="0.005:0.03,0.015:0.10,0.05:0.35", help="Comma-separated fast:slow zero-DC pulse tau pairs.")
    parser.add_argument("--ring-reg", type=float, default=0.01)
    parser.add_argument("--ring-gain-bound", type=float, default=5.0)
    parser.add_argument("--s11-strengths", default="0,0.25,0.5,0.75,1")
    parser.add_argument("--fit-maxiter", type=int, default=80)
    parser.add_argument("--fit-popsize", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--reuse-hspice-existing", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    hspice_dir = args.out_dir / "native_hspice"
    run_native_hspice(args.touchstone, args.hspice, hspice_dir, args.stop_ns, args.timeout, args.reuse_hspice_existing)

    refs = load_refs(hspice_dir.resolve(), args.stop_ns, args.fit_step_ps)
    initial_delay_ns = estimate_initial_delay_ns(refs) if args.initial_delay_ns is None else float(args.initial_delay_ns)
    fit = fit_s21_model(
        refs,
        branches=args.branches,
        initial_delay_ns=initial_delay_ns,
        delay_window_ns=args.delay_window_ns,
        tail_branches=args.tail_branches,
        maxiter=args.fit_maxiter,
        popsize=args.fit_popsize,
    )
    fit.update(
        fit_ring_correction(
            refs,
            fit,
            parse_float_list(args.ring_delays_ns),
            parse_tau_pairs(args.ring_tau_pairs_ns),
            args.ring_reg,
            args.ring_gain_bound,
        )
    )
    fit.update(fit_tx_fast(refs, args.tx_branches, args.tx_tail_branches))
    plot_fit_preview(refs, fit, args.out_dir / "fit_preview.png")

    summaries: list[dict[str, object]] = []
    by_strength: list[tuple[dict[str, object], Path, Path, Path, list[dict[str, object]]]] = []
    for strength in parse_strengths(args.s11_strengths):
        strength_dir = args.out_dir / f"s11_strength_{strength_label(strength)}"
        model_path = strength_dir / "models" / "s_equivalent_s2p_reduced.sp"
        write_s2p_model(model_path, fit, s11_strength=strength)
        ng_dir = strength_dir / "ngspice"
        run_rows = run_ngspice_cases(args.ngspice.resolve(), model_path.resolve(), 2, ng_dir, audit_cases(args.stop_ns), args.timeout)
        write_csv(strength_dir / "ngspice_run.csv", run_rows)
        compare_dir = strength_dir / "comparison"
        compare_rows: list[dict[str, object]] = []
        for case in CASE_BY_EDGE.values():
            n_raw = ng_dir / f"{case}.raw"
            h_tr0 = hspice_dir.resolve() / f"{case}_hspice.tr0"
            if not n_raw.exists():
                compare_rows.append(
                    {
                        "case": case,
                        "case_class": "FAIL",
                        "case_reason": "missing_ngspice_raw",
                        "hspice_tr0": rel(h_tr0),
                        "ngspice_raw": rel(n_raw),
                    }
                )
                continue
            compare_rows.append(
                compare_case(
                    case,
                    h_tr0,
                    n_raw,
                    2,
                    compare_dir,
                    "ngspice s2p reduced",
                    argparse.Namespace(
                        rx_active_rmse_pass_v=0.02,
                        rx_active_maxabs_pass_v=0.075,
                        tx_active_rmse_pass_v=0.05,
                        delay_pass_ps=25.0,
                    ),
                )
            )
        write_csv(compare_dir / "comparison.csv", compare_rows)
        summary = summarize_rows(strength, compare_rows)
        summary["strength_dir"] = rel(strength_dir.resolve())
        summary["model"] = rel(model_path.resolve())
        summaries.append(summary)
        by_strength.append((summary, strength_dir, model_path, ng_dir, compare_rows))

    selected_summary, selected_dir, selected_model, selected_ng_dir, selected_rows = min(
        by_strength,
        key=lambda item: (float(item[0]["selection_score"]), float(item[0]["s11_strength"])),
    )
    selected_comparison = args.out_dir / "selected_comparison.csv"
    selected_model_copy = args.out_dir / "selected_model.sp"
    overview = args.out_dir / "selected_overview.png"
    write_csv(args.out_dir / "strength_sweep.csv", summaries)
    write_csv(selected_comparison, selected_rows)
    selected_model_copy.write_text(selected_model.read_text(encoding="ascii"), encoding="ascii")
    plot_selected_overview(hspice_dir.resolve(), selected_ng_dir.resolve(), overview, f"{args.touchstone.name}: selected 2-port reduced model")

    selected = dict(selected_summary)
    selected["strength_dir"] = rel(selected_dir.resolve())
    selected["overview_plot"] = rel(overview.resolve())
    write_report(args.out_dir, args.touchstone, fit, selected, summaries)

    print(args.out_dir)
    print("touchstone", args.touchstone)
    print("initial_delay_ns", initial_delay_ns)
    print("selected_strength", selected_summary["s11_strength"])
    print("selected_score", selected_summary["selection_score"])
    print("selected_pass", f"{selected_summary['pass_count']}/{selected_summary['case_count']}")
    print("selected_mean_rx_rmse_v", selected_summary["rx_active_rmse_mean_v"])
    print("selected_mean_tx_rmse_v", selected_summary["tx_active_rmse_mean_v"])
    print("overview", overview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
