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
from run_sparam_conversion_quality_study import (  # noqa: E402
    DEFAULT_NGSPICE,
    SmokeCase,
    audit_cases,
    rel,
    source_lines,
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


def source_voltage(t: np.ndarray, edge_ps: float, amplitude_v: float = 1.5) -> np.ndarray:
    edge = edge_ps * 1e-12
    xp = np.array([0.0, 1.0e-9, 1.0e-9 + edge, 9.0e-9, 9.0e-9 + edge, 1.0], dtype=float)
    yp = np.array([0.0, 0.0, amplitude_v, amplitude_v, 0.0, 0.0], dtype=float)
    xp[-1] = max(float(t[-1]) + 1e-9, 1.0)
    return np.interp(t, xp, yp)


def cascaded_lowpass(t: np.ndarray, x: np.ndarray, taus_s: np.ndarray) -> np.ndarray:
    y = np.asarray(x, dtype=float)
    for tau in taus_s:
        tau = max(float(tau), 1e-15)
        out = np.empty_like(y)
        out[0] = y[0]
        for idx in range(1, len(y)):
            dt = float(t[idx] - t[idx - 1])
            alpha = math.exp(-dt / tau)
            out[idx] = y[idx] + (out[idx - 1] - y[idx]) * alpha
        y = out
    return y


def model_waveform(t: np.ndarray, edge_ps: float, delay_s: float, gain: float, taus_s: np.ndarray) -> np.ndarray:
    delayed_time = t - delay_s
    line_v = 0.5 * source_voltage(delayed_time, edge_ps)
    return gain * cascaded_lowpass(t, line_v, taus_s)


def active_error(ref: np.ndarray, pred: np.ndarray) -> tuple[float, float]:
    high = float(np.nanpercentile(ref, 95.0))
    low = float(np.nanpercentile(ref, 5.0))
    swing = max(abs(high - low), 1e-12)
    mask = (np.abs(ref - low) >= 0.02 * swing) | (np.abs(pred - low) >= 0.02 * swing)
    if not np.any(mask):
        return float("nan"), float("nan")
    diff = pred[mask] - ref[mask]
    return float(np.sqrt(np.mean(diff**2))), float(np.max(np.abs(diff)))


def load_refs(hspice_dir: Path, stop_ns: float, step_ps: float) -> dict[int, dict[str, np.ndarray]]:
    refs: dict[int, dict[str, np.ndarray]] = {}
    grid = np.arange(0.0, stop_ns * 1e-9 + step_ps * 1e-12 * 0.5, step_ps * 1e-12)
    for edge, case in CASE_BY_EDGE.items():
        tr0 = hspice_dir / f"{case}_hspice.tr0"
        data = parse_hspice_tr0(tr0)
        refs[edge] = {
            "time": grid,
            "v_p1": np.interp(grid, data["time"], data["v(p1)"]),
            "v_p3": np.interp(grid, data["time"], data["v(p3)"]),
        }
    return refs


def fit_model(refs: dict[int, dict[str, np.ndarray]], poles: int, initial_delay_ns: float):
    try:
        from scipy.optimize import differential_evolution, minimize
    except ImportError as exc:
        raise RuntimeError("scipy is required for fitting this reduced model") from exc

    bounds = [(initial_delay_ns - 0.5, initial_delay_ns + 0.5), (0.4, 1.4)]
    bounds.extend([(-2.0, 1.1)] * poles)  # log10(tau_ns)

    def unpack(vec: np.ndarray) -> tuple[float, float, np.ndarray]:
        delay_s = float(vec[0]) * 1e-9
        gain = float(vec[1])
        taus_ns = np.sort(10 ** np.asarray(vec[2:], dtype=float))
        return delay_s, gain, taus_ns * 1e-9

    def objective(vec: np.ndarray) -> float:
        delay_s, gain, taus_s = unpack(vec)
        total = 0.0
        for edge, ref in refs.items():
            t = ref["time"]
            pred = model_waveform(t, edge, delay_s, gain, taus_s)
            rmse, maxabs = active_error(ref["v_p3"], pred)
            total += rmse + 0.15 * maxabs
        return float(total)

    seed = np.array([initial_delay_ns, 0.9] + [math.log10(v) for v in np.geomspace(0.08, 2.5, poles)])
    de = differential_evolution(objective, bounds, seed=7, polish=False, maxiter=80, popsize=10, tol=1e-4, workers=1)
    best_start = de.x if de.fun < objective(seed) else seed
    local = minimize(objective, best_start, method="Nelder-Mead", options={"maxiter": 2500, "xatol": 1e-5, "fatol": 1e-6})
    best = local.x if local.fun <= de.fun else de.x
    delay_s, gain, taus_s = unpack(best)
    return {
        "delay_s": delay_s,
        "delay_ns": delay_s * 1e9,
        "gain_to_load": gain,
        "taus_s": taus_s,
        "taus_ns": taus_s * 1e9,
        "objective": objective(best),
    }


def write_model(path: Path, fit: dict[str, object], r_stage: float = 1000.0) -> None:
    delay_ns = float(fit["delay_ns"])
    gain_to_load = float(fit["gain_to_load"])
    taus_ns = np.asarray(fit["taus_ns"], dtype=float)
    lines = [
        "* Reduced delay-aware Cisco S-parameter macromodel",
        "* Fitted for 50 ohm source/load transient waveform correlation.",
        ".subckt s_equivalent p1 p2 p3 p4",
        f"Tdelay p1 0 ndelay 0 Z0=50 TD={delay_ns:.12g}n",
        "Rdelay_term ndelay 0 50",
        "Rleak_p2 p2 0 1e12",
        "Rleak_p4 p4 0 1e12",
        "Ebuf0 fsrc0 0 ndelay 0 1",
    ]
    prev = "fsrc0"
    for idx, tau_ns in enumerate(taus_ns, start=1):
        src = prev if idx == 1 else f"fsrc{idx - 1}"
        node = f"f{idx}"
        cap_f = (float(tau_ns) * 1e-9) / r_stage
        lines.append(f"Rlp{idx} {src} {node} {r_stage:.12g}")
        lines.append(f"Clp{idx} {node} 0 {cap_f:.12g}")
        if idx < len(taus_ns):
            lines.append(f"Ebuf{idx} fsrc{idx} 0 {node} 0 1")
        prev = node
    # Rout=50 with external 50 ohm termination halves the controlled source.
    lines.extend(
        [
            f"Eout outdrv 0 {prev} 0 {2.0 * gain_to_load:.12g}",
            "Rout outdrv p3 50",
            ".ends s_equivalent",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="ascii")


def write_ngspice_deck(deck: Path, model_spice: Path, case: SmokeCase) -> None:
    src, src_node = source_lines(case, "p1")
    include = Path(model_spice).resolve().relative_to(deck.parent.resolve()) if False else None
    include_text = str(Path(model_spice).resolve())
    include_text = include_text.replace("\\", "/")
    text = "\n".join(
        [
            f"* delay-aware reduced ngspice audit: {case.name}",
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
        try:
            completed = subprocess.run(
                [str(ngspice), "-b", "-o", log.name, "-r", raw.name, deck.name],
                cwd=out_dir,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            row: dict[str, object] = {
                "case": case.name,
                "return_code": completed.returncode,
                "raw": rel(raw),
                "log": rel(log),
            }
            if raw.exists():
                data = parse_ngspice_raw(raw)
                row["points"] = len(data["time"])
                row["stop_ns"] = float(data["time"][-1] * 1e9)
                row["v(p1)_min_v"] = float(np.nanmin(data["v(p1)"]))
                row["v(p1)_max_v"] = float(np.nanmax(data["v(p1)"]))
                row["v(p3)_min_v"] = float(np.nanmin(data["v(p3)"]))
                row["v(p3)_max_v"] = float(np.nanmax(data["v(p3)"]))
        except Exception as exc:
            row = {"case": case.name, "return_code": -999, "run_error": str(exc), "raw": rel(raw), "log": rel(log)}
        rows.append(row)
    return rows


def plot_fit_preview(refs: dict[int, dict[str, np.ndarray]], fit: dict[str, object], path: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    delay_s = float(fit["delay_s"])
    gain = float(fit["gain_to_load"])
    taus_s = np.asarray(fit["taus_s"], dtype=float)
    for ax, edge in zip(axes, sorted(refs)):
        ref = refs[edge]
        pred = model_waveform(ref["time"], edge, delay_s, gain, taus_s)
        ax.plot(ref["time"] * 1e9, ref["v_p3"], label="HSPICE native S", linewidth=1.8)
        ax.plot(ref["time"] * 1e9, pred, "--", label="reduced model fit", linewidth=1.5)
        ax.set_title(f"{edge} ps edge", loc="left", fontweight="bold")
        ax.set_ylabel("V(p3) (V)")
        ax.grid(True, color="#d7dde6")
        ax.legend(frameon=False)
    axes[-1].set_xlabel("Time (ns)")
    fig.suptitle("Analytic fit preview before ngspice run", fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def write_report(out_dir: Path, fit: dict[str, object], compare_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Delay-aware Reduced S-parameter Model",
        "",
        "This is a waveform-matching prototype for the Cisco representative channel.",
        "It is not yet a general-purpose passive multiport S-parameter replacement.",
        "",
        "## Fitted Parameters",
        "",
        f"- Explicit delay: `{float(fit['delay_ns']):.6g} ns`",
        f"- Load gain after delay/filter: `{float(fit['gain_to_load']):.6g}`",
        f"- RC pole taus: `{', '.join(f'{v:.6g} ns' for v in np.asarray(fit['taus_ns'], dtype=float))}`",
        f"- Fit objective: `{float(fit['objective']):.6g}`",
        "",
        "## HSPICE Correlation",
        "",
        "| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in compare_rows:
        lines.append(
            f"| `{row['case']}` | `{row.get('case_class', '')}` | "
            f"{float(row.get('rx_active_rmse_v', float('nan'))):.4g} | "
            f"{float(row.get('rx_active_maxabs_v', float('nan'))):.4g} | "
            f"{float(row.get('rx_rise50_delta_ps', float('nan'))):.4g} | "
            f"{float(row.get('rx_fall50_delta_ps', float('nan'))):.4g} | "
            f"{float(row.get('tx_active_rmse_v', float('nan'))):.4g} |"
        )
    lines.extend(
        [
            "",
            "## Key Files",
            "",
            "- `models/s_equivalent_delay_reduced.sp`: generated ngspice subcircuit",
            "- `ngspice/`: ngspice decks/raw/logs",
            "- `comparison/`: HSPICE-vs-ngspice overlays and CSV",
            "- `fit_preview.png`: analytic fit before running ngspice",
            "",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fit and run a reduced explicit-delay ngspice model against native HSPICE S-parameter transients.")
    parser.add_argument("--hspice-dir", type=Path, default=ROOT / "results" / "sparam_cisco_native_hspice_2026-06-08" / "Ch10_35_5F3N_t_long")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "sparam_cisco_delay_reduced_2026-06-08" / "Ch10_35_5F3N_t")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--stop-ns", type=float, default=35.0)
    parser.add_argument("--fit-step-ps", type=float, default=10.0)
    parser.add_argument("--initial-delay-ns", type=float, default=13.9221)
    parser.add_argument("--poles", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    refs = load_refs(args.hspice_dir.resolve(), args.stop_ns, args.fit_step_ps)
    fit = fit_model(refs, args.poles, args.initial_delay_ns)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.out_dir / "models" / "s_equivalent_delay_reduced.sp"
    write_model(model_path, fit)
    plot_fit_preview(refs, fit, args.out_dir / "fit_preview.png")

    ng_dir = args.out_dir / "ngspice"
    run_rows = run_ngspice(args.ngspice.resolve(), model_path.resolve(), ng_dir, args.stop_ns, args.timeout)
    write_csv(args.out_dir / "ngspice_run.csv", run_rows)

    compare_dir = args.out_dir / "comparison"
    compare_rows: list[dict[str, object]] = []
    for edge, case in CASE_BY_EDGE.items():
        h_tr0 = args.hspice_dir.resolve() / f"{case}_hspice.tr0"
        n_raw = ng_dir / f"{case}.raw"
        compare_rows.append(compare_case(case, h_tr0, n_raw, 4, compare_dir, "ngspice delay-reduced", argparse.Namespace(rx_active_rmse_pass_v=0.02, rx_active_maxabs_pass_v=0.075, tx_active_rmse_pass_v=0.05, delay_pass_ps=25.0)))
    write_csv(compare_dir / "comparison.csv", compare_rows)
    write_report(args.out_dir, fit, compare_rows)
    print(args.out_dir)
    print("delay_ns", fit["delay_ns"], "gain", fit["gain_to_load"], "taus_ns", fit["taus_ns"])
    for row in compare_rows:
        print(row["case"], row["case_class"], "rx_rmse", row.get("rx_active_rmse_v"), "rise_delta_ps", row.get("rx_rise50_delta_ps"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
