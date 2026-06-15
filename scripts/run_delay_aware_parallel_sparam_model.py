from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compare_sparam_transient_audits import compare_case  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
from run_sparam_conversion_quality_study import DEFAULT_NGSPICE, SmokeCase, audit_cases, rel, source_lines  # noqa: E402


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


def source_voltage(t: np.ndarray, edge_ps: float, amplitude_v: float = 1.5) -> np.ndarray:
    edge = edge_ps * 1e-12
    xp = np.array([0.0, 1.0e-9, 1.0e-9 + edge, 9.0e-9, 9.0e-9 + edge, max(float(t[-1]) + 1e-9, 1.0)])
    yp = np.array([0.0, 0.0, amplitude_v, amplitude_v, 0.0, 0.0])
    return np.interp(t, xp, yp)


def lowpass(t: np.ndarray, x: np.ndarray, tau_s: float) -> np.ndarray:
    tau_s = max(float(tau_s), 1e-15)
    out = np.empty_like(x)
    out[0] = x[0]
    for idx in range(1, len(x)):
        alpha = math.exp(-float(t[idx] - t[idx - 1]) / tau_s)
        out[idx] = x[idx] + (out[idx - 1] - x[idx]) * alpha
    return out


def model_waveform(
    t: np.ndarray,
    edge_ps: float,
    delay_s: float,
    taus_s: np.ndarray,
    gains: np.ndarray,
    tail_fast_s: np.ndarray | None = None,
    tail_slow_s: np.ndarray | None = None,
    tail_gains: np.ndarray | None = None,
) -> np.ndarray:
    line_v = 0.5 * source_voltage(t - delay_s, edge_ps)
    y = np.zeros_like(line_v)
    for tau_s, gain in zip(taus_s, gains):
        y += float(gain) * lowpass(t, line_v, float(tau_s))
    if tail_fast_s is not None and tail_slow_s is not None and tail_gains is not None:
        for fast_s, slow_s, gain in zip(tail_fast_s, tail_slow_s, tail_gains):
            y += float(gain) * (lowpass(t, line_v, float(fast_s)) - lowpass(t, line_v, float(slow_s)))
    return y


def tx_baseline(t: np.ndarray, edge_ps: float) -> np.ndarray:
    return 0.5 * source_voltage(t, edge_ps)


def tx_correction_waveform(
    t: np.ndarray,
    edge_ps: float,
    taus_s: np.ndarray,
    gains: np.ndarray,
    tail_fast_s: np.ndarray | None = None,
    tail_slow_s: np.ndarray | None = None,
    tail_gains: np.ndarray | None = None,
) -> np.ndarray:
    pin_v = tx_baseline(t, edge_ps)
    y = np.zeros_like(pin_v)
    for tau_s, gain in zip(taus_s, gains):
        y += float(gain) * lowpass(t, pin_v, float(tau_s))
    if tail_fast_s is not None and tail_slow_s is not None and tail_gains is not None:
        for fast_s, slow_s, gain in zip(tail_fast_s, tail_slow_s, tail_gains):
            y += float(gain) * (lowpass(t, pin_v, float(fast_s)) - lowpass(t, pin_v, float(slow_s)))
    return y


def tx_model_waveform(
    t: np.ndarray,
    edge_ps: float,
    taus_s: np.ndarray,
    gains: np.ndarray,
    tail_fast_s: np.ndarray | None = None,
    tail_slow_s: np.ndarray | None = None,
    tail_gains: np.ndarray | None = None,
) -> np.ndarray:
    return tx_baseline(t, edge_ps) + tx_correction_waveform(t, edge_ps, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains)


def active_error(ref: np.ndarray, pred: np.ndarray) -> tuple[float, float]:
    high = float(np.nanpercentile(ref, 95.0))
    low = float(np.nanpercentile(ref, 5.0))
    swing = max(abs(high - low), 1e-12)
    mask = (np.abs(ref - low) >= 0.02 * swing) | (np.abs(pred - low) >= 0.02 * swing)
    diff = pred[mask] - ref[mask]
    return float(np.sqrt(np.mean(diff**2))), float(np.max(np.abs(diff)))


def crossing(t: np.ndarray, y: np.ndarray, threshold: float, rise: bool, after: float) -> float | None:
    if rise:
        idxs = np.where((y[:-1] < threshold) & (y[1:] >= threshold))[0]
    else:
        idxs = np.where((y[:-1] >= threshold) & (y[1:] < threshold))[0]
    idxs = [idx for idx in idxs if t[idx] >= after]
    if not idxs:
        return None
    idx = idxs[0]
    if y[idx + 1] == y[idx]:
        return float(t[idx])
    return float(t[idx] + (threshold - y[idx]) * (t[idx + 1] - t[idx]) / (y[idx + 1] - y[idx]))


def load_refs(hspice_dir: Path, stop_ns: float, step_ps: float) -> dict[int, dict[str, np.ndarray]]:
    refs: dict[int, dict[str, np.ndarray]] = {}
    grid = np.arange(0.0, stop_ns * 1e-9 + step_ps * 1e-12 * 0.5, step_ps * 1e-12)
    for edge, case in CASE_BY_EDGE.items():
        data = parse_hspice_tr0(hspice_dir / f"{case}_hspice.tr0")
        p3 = np.interp(grid, data["time"], data["v(p3)"])
        p1 = np.interp(grid, data["time"], data["v(p1)"])
        low = float(np.nanpercentile(p3, 5.0))
        high = float(np.nanpercentile(p3, 95.0))
        threshold = 0.5 * (low + high)
        refs[edge] = {
            "time": grid,
            "v_p1": p1,
            "v_p3": p3,
            "threshold": threshold,
            "rise": crossing(grid, p3, threshold, True, 0.5e-9),
            "fall": crossing(grid, p3, threshold, False, 8.5e-9),
        }
    return refs


def fit_model(refs: dict[int, dict[str, np.ndarray]], branches: int, initial_delay_ns: float, tail_branches: int):
    from scipy.optimize import differential_evolution, minimize

    bounds = [(initial_delay_ns - 0.5, initial_delay_ns + 0.5)]
    bounds.extend([(-2.0, 1.0)] * branches)  # log10 tau ns
    bounds.extend([(-0.5, 1.8)] * branches)  # branch gains to loaded output
    for _ in range(tail_branches):
        bounds.extend([(-2.0, 0.3), (-1.0, 1.7), (-1.0, 1.0)])  # log10 fast ns, log10 slow ns, zero-DC tail gain

    def unpack(vec: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        delay_s = float(vec[0]) * 1e-9
        tau_ns = 10 ** np.asarray(vec[1 : 1 + branches], dtype=float)
        gains = np.asarray(vec[1 + branches :], dtype=float)
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
        return delay_s, tau_ns[order] * 1e-9, gains[order], tail_fast[tail_order] * 1e-9, tail_slow[tail_order] * 1e-9, tail_gain_array[tail_order]

    def objective(vec: np.ndarray) -> float:
        delay_s, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains = unpack(vec)
        if abs(float(np.sum(gains)) - 0.89) > 1.5:
            return 1e3
        if len(tail_slow_s) and np.any(tail_slow_s <= 1.05 * tail_fast_s):
            return 1e3 + float(np.sum(np.maximum(0.0, 1.05 * tail_fast_s - tail_slow_s))) * 1e12
        total = 0.0
        for edge, ref in refs.items():
            t = ref["time"]
            pred = model_waveform(t, edge, delay_s, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains)
            rmse, maxabs = active_error(ref["v_p3"], pred)
            total += rmse + 0.25 * maxabs
            pred_rise = crossing(t, pred, float(ref["threshold"]), True, 0.5e-9)
            pred_fall = crossing(t, pred, float(ref["threshold"]), False, 8.5e-9)
            if pred_rise is None or pred_fall is None:
                total += 10.0
            else:
                total += 2e8 * abs(pred_rise - float(ref["rise"]))
                total += 2e8 * abs(pred_fall - float(ref["fall"]))
        total += 0.002 * float(np.sum(np.abs(gains)))
        total += 0.001 * float(np.sum(np.abs(tail_gains)))
        return float(total)

    tau_guess = np.geomspace(0.04, 3.0, branches)
    gain_guess = np.full(branches, 0.89 / branches)
    tail_seed: list[float] = []
    for idx in range(tail_branches):
        tail_seed.extend([math.log10(0.08 * (idx + 1)), math.log10(5.0 * (idx + 1)), 0.04])
    seed = np.array([initial_delay_ns, *np.log10(tau_guess), *gain_guess, *tail_seed])
    de = differential_evolution(objective, bounds, seed=11, maxiter=100, popsize=12, tol=1e-4, polish=False, workers=1)
    best_start = de.x if de.fun < objective(seed) else seed
    local = minimize(objective, best_start, method="Nelder-Mead", options={"maxiter": 3000, "xatol": 1e-6, "fatol": 1e-7})
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
        "objective": objective(best),
    }


def fit_tx_correction_model(refs: dict[int, dict[str, np.ndarray]], branches: int, tail_branches: int):
    from scipy.optimize import differential_evolution, minimize

    if branches <= 0 and tail_branches <= 0:
        return {
            "tx_taus_s": np.asarray([], dtype=float),
            "tx_taus_ns": np.asarray([], dtype=float),
            "tx_gains": np.asarray([], dtype=float),
            "tx_tail_fast_s": np.asarray([], dtype=float),
            "tx_tail_fast_ns": np.asarray([], dtype=float),
            "tx_tail_slow_s": np.asarray([], dtype=float),
            "tx_tail_slow_ns": np.asarray([], dtype=float),
            "tx_tail_gains": np.asarray([], dtype=float),
            "tx_objective": 0.0,
        }

    bounds: list[tuple[float, float]] = []
    bounds.extend([(-2.5, 1.5)] * branches)  # log10 tau ns
    bounds.extend([(-0.5, 0.5)] * branches)  # series correction gains
    for _ in range(tail_branches):
        bounds.extend([(-2.5, 0.5), (-1.0, 1.7), (-0.5, 0.5)])

    def unpack(vec: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        tau_ns = 10 ** np.asarray(vec[:branches], dtype=float)
        gains = np.asarray(vec[branches : 2 * branches], dtype=float)
        tail_offset = 2 * branches
        tail_fast_ns: list[float] = []
        tail_slow_ns: list[float] = []
        tail_gains: list[float] = []
        for idx in range(tail_branches):
            base = tail_offset + 3 * idx
            tail_fast_ns.append(float(10 ** vec[base]))
            tail_slow_ns.append(float(10 ** vec[base + 1]))
            tail_gains.append(float(vec[base + 2]))
        order = np.argsort(tau_ns) if len(tau_ns) else np.asarray([], dtype=int)
        tail_fast = np.asarray(tail_fast_ns, dtype=float)
        tail_slow = np.asarray(tail_slow_ns, dtype=float)
        tail_gain_array = np.asarray(tail_gains, dtype=float)
        tail_order = np.argsort(tail_slow) if len(tail_slow) else np.asarray([], dtype=int)
        return tau_ns[order] * 1e-9, gains[order], tail_fast[tail_order] * 1e-9, tail_slow[tail_order] * 1e-9, tail_gain_array[tail_order]

    def objective(vec: np.ndarray) -> float:
        taus_s, gains, tail_fast_s, tail_slow_s, tail_gains = unpack(vec)
        if len(tail_slow_s) and np.any(tail_slow_s <= 1.05 * tail_fast_s):
            return 1e3
        total = 0.0
        for edge, ref in refs.items():
            t = ref["time"]
            pred = tx_model_waveform(t, edge, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains)
            rmse, maxabs = active_error(ref["v_p1"], pred)
            total += rmse + 0.20 * maxabs
        total += 0.001 * float(np.sum(np.abs(gains)))
        total += 0.001 * float(np.sum(np.abs(tail_gains)))
        return float(total)

    tau_guess = np.geomspace(0.02, 8.0, max(branches, 1))[:branches]
    gain_guess = np.zeros(branches)
    tail_seed: list[float] = []
    for idx in range(tail_branches):
        tail_seed.extend([math.log10(0.05 * (idx + 1)), math.log10(2.0 * (idx + 1)), 0.02])
    seed = np.array([*np.log10(tau_guess), *gain_guess, *tail_seed])
    de = differential_evolution(objective, bounds, seed=19, maxiter=80, popsize=10, tol=2e-4, polish=False, workers=1)
    best_start = de.x if de.fun < objective(seed) else seed
    local = minimize(objective, best_start, method="Nelder-Mead", options={"maxiter": 2500, "xatol": 1e-6, "fatol": 1e-7})
    best = local.x if local.fun <= de.fun else de.x
    taus_s, gains, tail_fast_s, tail_slow_s, tail_gains = unpack(best)
    return {
        "tx_taus_s": taus_s,
        "tx_taus_ns": taus_s * 1e9,
        "tx_gains": gains,
        "tx_tail_fast_s": tail_fast_s,
        "tx_tail_fast_ns": tail_fast_s * 1e9,
        "tx_tail_slow_s": tail_slow_s,
        "tx_tail_slow_ns": tail_slow_s * 1e9,
        "tx_tail_gains": tail_gains,
        "tx_objective": objective(best),
    }


def write_model(path: Path, fit: dict[str, object], r_stage: float = 1000.0) -> None:
    delay_ns = float(fit["delay_ns"])
    taus_ns = np.asarray(fit["taus_ns"], dtype=float)
    gains = np.asarray(fit["gains"], dtype=float)
    tx_taus_ns = np.asarray(fit.get("tx_taus_ns", []), dtype=float)
    tx_gains = np.asarray(fit.get("tx_gains", []), dtype=float)
    tx_tail_fast_ns = np.asarray(fit.get("tx_tail_fast_ns", []), dtype=float)
    tx_tail_slow_ns = np.asarray(fit.get("tx_tail_slow_ns", []), dtype=float)
    tx_tail_gains = np.asarray(fit.get("tx_tail_gains", []), dtype=float)
    has_tx_correction = bool(len(tx_gains) or len(tx_tail_gains))
    input_node = "pin" if has_tx_correction else "p1"
    lines = [
        "* Parallel delay-aware Cisco S-parameter macromodel",
        "* Fitted for 50 ohm source/load transient waveform correlation.",
        ".subckt s_equivalent p1 p2 p3 p4",
    ]
    if has_tx_correction:
        lines.extend(
            [
                "* S11-like input reflection correction for the 50 ohm audit bench.",
                "Rtxsum txsum 0 1",
            ]
        )
        for idx, (tau_ns, gain) in enumerate(zip(tx_taus_ns, tx_gains), start=1):
            cap_f = (float(tau_ns) * 1e-9) / r_stage
            lines.extend(
                [
                    f"Etxsrc{idx} txsrc{idx} 0 pin 0 1",
                    f"Rtx{idx} txsrc{idx} tx{idx} {r_stage:.12g}",
                    f"Ctx{idx} tx{idx} 0 {cap_f:.12g}",
                    f"Gtx{idx} 0 txsum tx{idx} 0 {float(gain):.12g}",
                ]
            )
        for idx, (fast_ns, slow_ns, gain) in enumerate(zip(tx_tail_fast_ns, tx_tail_slow_ns, tx_tail_gains), start=1):
            fast_cap_f = (float(fast_ns) * 1e-9) / r_stage
            slow_cap_f = (float(slow_ns) * 1e-9) / r_stage
            lines.extend(
                [
                    f"Etxtailfsrc{idx} txtailfsrc{idx} 0 pin 0 1",
                    f"Rtxtailf{idx} txtailfsrc{idx} txtailf{idx} {r_stage:.12g}",
                    f"Ctx_tailf{idx} txtailf{idx} 0 {fast_cap_f:.12g}",
                    f"Gtxtailf{idx} 0 txsum txtailf{idx} 0 {float(gain):.12g}",
                    f"Etxtailssrc{idx} txtailssrc{idx} 0 pin 0 1",
                    f"Rtxtails{idx} txtailssrc{idx} txtails{idx} {r_stage:.12g}",
                    f"Ctx_tails{idx} txtails{idx} 0 {slow_cap_f:.12g}",
                    f"Gtxtails{idx} 0 txsum txtails{idx} 0 {-float(gain):.12g}",
                ]
            )
        lines.extend(
            [
                "Etxport p1 pin txsum 0 1",
                "Rpin_leak pin 0 1e12",
            ]
        )
    lines.extend(
        [
        f"Tdelay {input_node} 0 ndelay 0 Z0=50 TD={delay_ns:.12g}n",
        "Rdelay_term ndelay 0 50",
        "Rleak_p2 p2 0 1e12",
        "Rleak_p4 p4 0 1e12",
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
    tail_fast_ns = np.asarray(fit.get("tail_fast_ns", []), dtype=float)
    tail_slow_ns = np.asarray(fit.get("tail_slow_ns", []), dtype=float)
    tail_gains = np.asarray(fit.get("tail_gains", []), dtype=float)
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
    lines.extend(
        [
            "Eout outdrv 0 sum 0 2",
            "Rout outdrv p3 50",
            ".ends s_equivalent",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="ascii")


def write_ngspice_deck(deck: Path, model_spice: Path, case: SmokeCase) -> None:
    src, _ = source_lines(case, "p1")
    include_text = str(model_spice.resolve()).replace("\\", "/")
    text = "\n".join(
        [
            f"* delay-aware parallel ngspice audit: {case.name}",
            ".temp 27",
            ".options method=gear maxord=2 reltol=1e-5 abstol=1e-11 vntol=1e-7 gmin=1e-12",
            *src,
            f".include '{include_text}'",
            "Xchannel  p1  p2  p3  p4  s_equivalent",
            "Rnear_neg  p2  0  50",
            "Rterm_pos  p3  0  50",
            "Rterm_neg  p4  0  50",
            ".save V(src) V(p1) V(p2) V(p3) V(p4)",
            f".tran 5p {case.stop_ns * 1e-9:.12g}",
            ".end",
            "",
        ]
    )
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(text, encoding="ascii")


def run_ngspice(ngspice: Path, model_spice: Path, out_dir: Path, stop_ns: float, timeout: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in audit_cases(stop_ns):
        deck = out_dir / f"{case.name}.sp"
        raw = deck.with_suffix(".raw")
        log = deck.with_suffix(".log")
        write_ngspice_deck(deck, model_spice, case)
        completed = subprocess.run(
            [str(ngspice), "-b", "-o", log.name, "-r", raw.name, deck.name],
            cwd=out_dir,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        row: dict[str, object] = {"case": case.name, "return_code": completed.returncode, "raw": rel(raw), "log": rel(log)}
        if raw.exists():
            data = parse_ngspice_raw(raw)
            row["points"] = len(data["time"])
            row["v(p1)_max_v"] = float(np.nanmax(data["v(p1)"]))
            row["v(p3)_max_v"] = float(np.nanmax(data["v(p3)"]))
        rows.append(row)
    return rows


def plot_fit_preview(refs: dict[int, dict[str, np.ndarray]], fit: dict[str, object], path: Path) -> None:
    has_tx = len(np.asarray(fit.get("tx_gains", []), dtype=float)) or len(np.asarray(fit.get("tx_tail_gains", []), dtype=float))
    ncols = 2 if has_tx else 1
    fig, axes = plt.subplots(3, ncols, figsize=(15 if has_tx else 10, 8), sharex=True, constrained_layout=True)
    if not has_tx:
        axes = np.asarray(axes).reshape(3, 1)
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
        pred = model_waveform(ref["time"], edge, delay_s, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains)
        ax_rx = axes[row_idx, 0 if not has_tx else 1]
        ax_rx.plot(ref["time"] * 1e9, ref["v_p3"], label="HSPICE native S", linewidth=1.8)
        ax_rx.plot(ref["time"] * 1e9, pred, "--", label="RX fit", linewidth=1.5)
        ax_rx.set_title(f"{edge} ps edge - RX", loc="left", fontweight="bold")
        ax_rx.set_ylabel("V(p3) (V)")
        ax_rx.grid(True, color="#d7dde6")
        ax_rx.legend(frameon=False)
        if has_tx:
            tx_pred = tx_model_waveform(ref["time"], edge, tx_taus_s, tx_gains, tx_tail_fast_s, tx_tail_slow_s, tx_tail_gains)
            ax_tx = axes[row_idx, 0]
            ax_tx.plot(ref["time"] * 1e9, ref["v_p1"], label="HSPICE native S", linewidth=1.8)
            ax_tx.plot(ref["time"] * 1e9, tx_pred, "--", label="TX correction fit", linewidth=1.5)
            ax_tx.set_title(f"{edge} ps edge - TX", loc="left", fontweight="bold")
            ax_tx.set_ylabel("V(p1) (V)")
            ax_tx.grid(True, color="#d7dde6")
            ax_tx.legend(frameon=False)
    for ax in axes[-1, :]:
        ax.set_xlabel("Time (ns)")
    fig.suptitle("Analytic parallel-residual fit preview", fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def write_report(out_dir: Path, fit: dict[str, object], compare_rows: list[dict[str, object]]) -> None:
    tail_fast_ns = np.asarray(fit.get("tail_fast_ns", []), dtype=float)
    tail_slow_ns = np.asarray(fit.get("tail_slow_ns", []), dtype=float)
    tail_gains = np.asarray(fit.get("tail_gains", []), dtype=float)
    lines = [
        "# Parallel Delay-aware Reduced S-parameter Model",
        "",
        "This prototype uses a 50 ohm explicit delay line, parallel RC residual branches, and optional zero-DC tail branches.",
        "",
        "## Fitted Parameters",
        "",
        f"- Explicit delay: `{float(fit['delay_ns']):.6g} ns`",
        f"- DC gain to loaded output: `{float(fit['dc_gain_to_load']):.6g}`",
        f"- Branch taus: `{', '.join(f'{v:.6g} ns' for v in np.asarray(fit['taus_ns'], dtype=float))}`",
        f"- Branch gains: `{', '.join(f'{v:.6g}' for v in np.asarray(fit['gains'], dtype=float))}`",
    ]
    if len(tail_gains):
        lines.extend(
            [
                f"- Tail fast taus: `{', '.join(f'{v:.6g} ns' for v in tail_fast_ns)}`",
                f"- Tail slow taus: `{', '.join(f'{v:.6g} ns' for v in tail_slow_ns)}`",
                f"- Tail gains: `{', '.join(f'{v:.6g}' for v in tail_gains)}`",
            ]
        )
    tx_taus_ns = np.asarray(fit.get("tx_taus_ns", []), dtype=float)
    tx_gains = np.asarray(fit.get("tx_gains", []), dtype=float)
    tx_tail_fast_ns = np.asarray(fit.get("tx_tail_fast_ns", []), dtype=float)
    tx_tail_slow_ns = np.asarray(fit.get("tx_tail_slow_ns", []), dtype=float)
    tx_tail_gains = np.asarray(fit.get("tx_tail_gains", []), dtype=float)
    if len(tx_gains) or len(tx_tail_gains):
        lines.extend(
            [
                "",
                "## TX/S11-like Correction",
                "",
                "The TX correction is a bench-scoped series voltage correction at `p1` driven by the internal matched input node.",
                f"- TX correction taus: `{', '.join(f'{v:.6g} ns' for v in tx_taus_ns)}`",
                f"- TX correction gains: `{', '.join(f'{v:.6g}' for v in tx_gains)}`",
                f"- TX tail fast taus: `{', '.join(f'{v:.6g} ns' for v in tx_tail_fast_ns)}`",
                f"- TX tail slow taus: `{', '.join(f'{v:.6g} ns' for v in tx_tail_slow_ns)}`",
                f"- TX tail gains: `{', '.join(f'{v:.6g}' for v in tx_tail_gains)}`",
            ]
        )
    lines.extend(
        [
            "",
            "## HSPICE Correlation",
            "",
            "| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in compare_rows:
        lines.append(
            f"| `{row['case']}` | `{row.get('case_class', '')}` | "
            f"{float(row.get('rx_active_rmse_v', float('nan'))):.4g} | "
            f"{float(row.get('rx_active_maxabs_v', float('nan'))):.4g} | "
            f"{float(row.get('rx_rise50_delta_ps', float('nan'))):.4g} | "
            f"{float(row.get('rx_fall50_delta_ps', float('nan'))):.4g} | "
            f"{float(row.get('tx_active_rmse_v', float('nan'))):.4g} |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fit a parallel explicit-delay ngspice model against native HSPICE S-parameter transients.")
    parser.add_argument("--hspice-dir", type=Path, default=ROOT / "results" / "sparam_cisco_native_hspice_2026-06-08" / "Ch10_35_5F3N_t_long")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "sparam_cisco_delay_parallel_2026-06-08" / "Ch10_35_5F3N_t")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--stop-ns", type=float, default=35.0)
    parser.add_argument("--fit-step-ps", type=float, default=10.0)
    parser.add_argument("--initial-delay-ns", type=float, default=13.79)
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--tail-branches", type=int, default=1)
    parser.add_argument("--tx-branches", type=int, default=0, help="Fit S11-like TX correction branches at the driven port.")
    parser.add_argument("--tx-tail-branches", type=int, default=0, help="Fit zero-DC tail branches for the TX/S11-like correction.")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    refs = load_refs(args.hspice_dir.resolve(), args.stop_ns, args.fit_step_ps)
    fit = fit_model(refs, args.branches, args.initial_delay_ns, args.tail_branches)
    fit.update(fit_tx_correction_model(refs, args.tx_branches, args.tx_tail_branches))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.out_dir / "models" / "s_equivalent_delay_parallel.sp"
    write_model(model_path, fit)
    plot_fit_preview(refs, fit, args.out_dir / "fit_preview.png")
    ng_dir = args.out_dir / "ngspice"
    run_rows = run_ngspice(args.ngspice.resolve(), model_path.resolve(), ng_dir, args.stop_ns, args.timeout)
    write_csv(args.out_dir / "ngspice_run.csv", run_rows)
    compare_dir = args.out_dir / "comparison"
    compare_rows = [
        compare_case(case, args.hspice_dir.resolve() / f"{case}_hspice.tr0", ng_dir / f"{case}.raw", 4, compare_dir, "ngspice delay-parallel", argparse.Namespace(rx_active_rmse_pass_v=0.02, rx_active_maxabs_pass_v=0.075, tx_active_rmse_pass_v=0.08, delay_pass_ps=25.0))
        for case in CASE_BY_EDGE.values()
    ]
    write_csv(compare_dir / "comparison.csv", compare_rows)
    write_report(args.out_dir, fit, compare_rows)
    print(args.out_dir)
    print("delay_ns", fit["delay_ns"], "taus_ns", fit["taus_ns"], "gains", fit["gains"])
    if len(np.asarray(fit.get("tail_gains", []), dtype=float)):
        print("tail_fast_ns", fit["tail_fast_ns"], "tail_slow_ns", fit["tail_slow_ns"], "tail_gains", fit["tail_gains"])
    if len(np.asarray(fit.get("tx_gains", []), dtype=float)) or len(np.asarray(fit.get("tx_tail_gains", []), dtype=float)):
        print("tx_taus_ns", fit["tx_taus_ns"], "tx_gains", fit["tx_gains"])
        print("tx_tail_fast_ns", fit["tx_tail_fast_ns"], "tx_tail_slow_ns", fit["tx_tail_slow_ns"], "tx_tail_gains", fit["tx_tail_gains"])
    for row in compare_rows:
        print(
            row["case"],
            row["case_class"],
            "rx_rmse",
            row.get("rx_active_rmse_v"),
            "tx_rmse",
            row.get("tx_active_rmse_v"),
            "rise_delta_ps",
            row.get("rx_rise50_delta_ps"),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
