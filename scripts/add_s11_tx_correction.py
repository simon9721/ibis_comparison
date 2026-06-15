from __future__ import annotations

import argparse
import csv
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

from compare_sparam_transient_audits import compare_case  # noqa: E402
from run_delay_aware_parallel_sparam_model import (  # noqa: E402
    CASE_BY_EDGE,
    active_error,
    load_refs,
    lowpass,
    run_ngspice,
    tx_model_waveform,
)
from run_sparam_conversion_quality_study import DEFAULT_NGSPICE, rel  # noqa: E402


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


def unpack_tx(vec: np.ndarray, branches: int, tail_branches: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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


def tx_residual(vec: np.ndarray, refs: dict[int, dict[str, np.ndarray]], branches: int, tail_branches: int) -> np.ndarray:
    taus_s, gains, tail_fast_s, tail_slow_s, tail_gains = unpack_tx(vec, branches, tail_branches)
    residuals: list[np.ndarray] = []
    for edge, ref in refs.items():
        pred = tx_model_waveform(ref["time"], edge, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains)
        high = float(np.nanpercentile(ref["v_p1"], 95.0))
        low = float(np.nanpercentile(ref["v_p1"], 5.0))
        swing = max(abs(high - low), 1e-12)
        mask = np.abs(ref["v_p1"] - low) >= 0.01 * swing
        residuals.append((pred[mask] - ref["v_p1"][mask]) / 0.03)
    residuals.append(0.05 * gains)
    residuals.append(0.05 * tail_gains)
    return np.concatenate(residuals)


def fit_tx_fast(refs: dict[int, dict[str, np.ndarray]], branches: int, tail_branches: int) -> dict[str, object]:
    from scipy.optimize import lsq_linear

    tx_taus_ns = np.geomspace(0.02, 8.0, max(branches, 1))[:branches]
    tail_fast_ns = np.asarray([0.05 * (idx + 1) for idx in range(tail_branches)], dtype=float)
    tail_slow_ns = np.asarray([2.0 * (idx + 1) for idx in range(tail_branches)], dtype=float)
    basis_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    for edge, ref in refs.items():
        # tx_model_waveform with no correction returns the 50 ohm matched input.
        pin_v = tx_model_waveform(ref["time"], edge, np.asarray([], dtype=float), np.asarray([], dtype=float))
        high = float(np.nanpercentile(ref["v_p1"], 95.0))
        low = float(np.nanpercentile(ref["v_p1"], 5.0))
        swing = max(abs(high - low), 1e-12)
        mask = np.abs(ref["v_p1"] - low) >= 0.01 * swing
        cols: list[np.ndarray] = []
        for tau_ns in tx_taus_ns:
            cols.append(lowpass(ref["time"], pin_v, float(tau_ns) * 1e-9))
        for fast_ns, slow_ns in zip(tail_fast_ns, tail_slow_ns):
            cols.append(lowpass(ref["time"], pin_v, float(fast_ns) * 1e-9) - lowpass(ref["time"], pin_v, float(slow_ns) * 1e-9))
        basis_rows.append(np.column_stack(cols)[mask])
        target_rows.append((ref["v_p1"] - pin_v)[mask])

    matrix = np.vstack(basis_rows)
    target = np.concatenate(target_rows)
    reg = 0.015
    matrix_aug = np.vstack([matrix, reg * np.eye(matrix.shape[1])])
    target_aug = np.concatenate([target, np.zeros(matrix.shape[1])])
    result = lsq_linear(matrix_aug, target_aug, bounds=(-0.5, 0.5), lsmr_tol="auto", max_iter=500)
    coeff = result.x
    taus_s = tx_taus_ns * 1e-9
    gains = coeff[:branches]
    tail_fast_s = tail_fast_ns * 1e-9
    tail_slow_s = tail_slow_ns * 1e-9
    tail_gains = coeff[branches:]
    best_cost = float(result.cost)
    metrics: dict[str, object] = {
        "tx_taus_s": taus_s,
        "tx_taus_ns": taus_s * 1e9,
        "tx_gains": gains,
        "tx_tail_fast_s": tail_fast_s,
        "tx_tail_fast_ns": tail_fast_s * 1e9,
        "tx_tail_slow_s": tail_slow_s,
        "tx_tail_slow_ns": tail_slow_s * 1e9,
        "tx_tail_gains": tail_gains,
        "tx_fit_cost": best_cost,
    }
    for edge, ref in refs.items():
        pred = tx_model_waveform(ref["time"], edge, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains)
        rmse, maxabs = active_error(ref["v_p1"], pred)
        metrics[f"edge{edge}_analytic_tx_active_rmse_v"] = rmse
        metrics[f"edge{edge}_analytic_tx_active_maxabs_v"] = maxabs
    return metrics


def tx_correction_lines(fit: dict[str, object], r_stage: float = 1000.0, strength: float = 1.0) -> list[str]:
    lines = [
        "* S11-like input reflection correction for the 50 ohm audit bench.",
        "Rtxsum txsum 0 1",
    ]
    tx_taus_ns = np.asarray(fit["tx_taus_ns"], dtype=float)
    tx_gains = np.asarray(fit["tx_gains"], dtype=float)
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
    tail_fast_ns = np.asarray(fit["tx_tail_fast_ns"], dtype=float)
    tail_slow_ns = np.asarray(fit["tx_tail_slow_ns"], dtype=float)
    tail_gains = np.asarray(fit["tx_tail_gains"], dtype=float)
    for idx, (fast_ns, slow_ns, gain) in enumerate(zip(tail_fast_ns, tail_slow_ns, tail_gains), start=1):
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


def augment_model(base_model: Path, out_model: Path, fit: dict[str, object], strength: float) -> None:
    text = base_model.read_text(encoding="ascii")
    if "Etxport" in text:
        raise ValueError(f"{base_model} already appears to include TX correction")
    lines = text.splitlines()
    out: list[str] = []
    inserted = False
    replaced = False
    for line in lines:
        out.append(line)
        if line.startswith(".subckt ") and not inserted:
            out.extend(tx_correction_lines(fit, strength=strength))
            inserted = True
    out = [line.replace("Tdelay p1 0", "Tdelay pin 0") if line.startswith("Tdelay p1 0") else line for line in out]
    replaced = any(line.startswith("Tdelay pin 0") for line in out)
    if not inserted or not replaced:
        raise ValueError(f"Could not augment {base_model}; expected .subckt and Tdelay p1")
    out_model.parent.mkdir(parents=True, exist_ok=True)
    out_model.write_text("\n".join(out) + "\n", encoding="ascii")


def plot_tx_fit(refs: dict[int, dict[str, np.ndarray]], fit: dict[str, object], path: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    taus_s = np.asarray(fit["tx_taus_s"], dtype=float)
    gains = np.asarray(fit["tx_gains"], dtype=float)
    tail_fast_s = np.asarray(fit["tx_tail_fast_s"], dtype=float)
    tail_slow_s = np.asarray(fit["tx_tail_slow_s"], dtype=float)
    tail_gains = np.asarray(fit["tx_tail_gains"], dtype=float)
    for ax, edge in zip(axes, sorted(refs)):
        ref = refs[edge]
        pred = tx_model_waveform(ref["time"], edge, taus_s, gains, tail_fast_s, tail_slow_s, tail_gains)
        ax.plot(ref["time"] * 1e9, ref["v_p1"], label="HSPICE native S", linewidth=1.8)
        ax.plot(ref["time"] * 1e9, pred, "--", label="analytic TX correction fit", linewidth=1.5)
        ax.set_title(f"{edge} ps edge", loc="left", fontweight="bold")
        ax.set_ylabel("V(p1)")
        ax.grid(True, color="#d7dde6")
        ax.legend(frameon=False)
    axes[-1].set_xlabel("Time (ns)")
    fig.suptitle("S11-like TX correction analytic preview", fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def write_report(out_dir: Path, fit: dict[str, object], compare_rows: list[dict[str, object]], strength: float) -> None:
    lines = [
        "# S11-like TX Correction Prototype",
        "",
        "This augments an accepted S31 reduced model with a bench-scoped input reflection correction.",
        "",
        f"- Correction strength: `{strength:.6g}`",
        f"- TX taus: `{', '.join(f'{v:.6g} ns' for v in np.asarray(fit['tx_taus_ns'], dtype=float))}`",
        f"- TX gains: `{', '.join(f'{v:.6g}' for v in np.asarray(fit['tx_gains'], dtype=float))}`",
        f"- TX tail fast taus: `{', '.join(f'{v:.6g} ns' for v in np.asarray(fit['tx_tail_fast_ns'], dtype=float))}`",
        f"- TX tail slow taus: `{', '.join(f'{v:.6g} ns' for v in np.asarray(fit['tx_tail_slow_ns'], dtype=float))}`",
        f"- TX tail gains: `{', '.join(f'{v:.6g}' for v in np.asarray(fit['tx_tail_gains'], dtype=float))}`",
        "",
        "| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in compare_rows:
        lines.append(
            f"| `{row['case']}` | `{row.get('case_class', '')}` | "
            f"{float(row.get('rx_active_rmse_v', float('nan'))):.4g} | "
            f"{float(row.get('tx_active_rmse_v', float('nan'))):.4g} | "
            f"{float(row.get('rx_rise50_delta_ps', float('nan'))):.4g} | "
            f"{float(row.get('rx_fall50_delta_ps', float('nan'))):.4g} |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Augment an accepted delay-parallel model with an S11-like TX correction.")
    parser.add_argument("--hspice-dir", type=Path, required=True)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--stop-ns", type=float, default=35.0)
    parser.add_argument("--fit-step-ps", type=float, default=10.0)
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--tail-branches", type=int, default=1)
    parser.add_argument("--strength", type=float, default=1.0, help="Scale fitted TX correction gains before writing SPICE.")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    refs = load_refs(args.hspice_dir.resolve(), args.stop_ns, args.fit_step_ps)
    fit = fit_tx_fast(refs, args.branches, args.tail_branches)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.out_dir / "models" / "s_equivalent_delay_parallel_s11.sp"
    augment_model(args.base_model.resolve(), model_path, fit, args.strength)
    plot_tx_fit(refs, fit, args.out_dir / "tx_fit_preview.png")
    ng_dir = args.out_dir / "ngspice"
    run_rows = run_ngspice(args.ngspice.resolve(), model_path.resolve(), ng_dir, args.stop_ns, args.timeout)
    write_csv(args.out_dir / "ngspice_run.csv", run_rows)
    compare_dir = args.out_dir / "comparison"
    import argparse as _argparse

    compare_rows = [
        compare_case(case, args.hspice_dir.resolve() / f"{case}_hspice.tr0", ng_dir / f"{case}.raw", 4, compare_dir, "ngspice S31+S11 proto", _argparse.Namespace(rx_active_rmse_pass_v=0.02, rx_active_maxabs_pass_v=0.075, tx_active_rmse_pass_v=0.08, delay_pass_ps=25.0))
        for case in CASE_BY_EDGE.values()
    ]
    write_csv(compare_dir / "comparison.csv", compare_rows)
    write_report(args.out_dir, fit, compare_rows, args.strength)
    print(args.out_dir)
    for row in compare_rows:
        print(row["case"], row["case_class"], "rx_rmse", row.get("rx_active_rmse_v"), "tx_rmse", row.get("tx_active_rmse_v"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
