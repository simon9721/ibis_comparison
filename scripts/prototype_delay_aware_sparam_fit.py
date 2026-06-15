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

from run_sparam_conversion_quality_study import (  # noqa: E402
    ensure_skrf,
    fitted_s_matrices,
    fmt,
    frequency_metrics,
    max_singular_from_mats,
)


THROUGH_PAIRS_4P = [(2, 0), (0, 2), (3, 1), (1, 3)]


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


def estimate_group_delay(freqs: np.ndarray, response: np.ndarray) -> float:
    mag = np.abs(response)
    if not np.any(mag):
        return 0.0
    mask = mag > max(1e-4, 0.10 * float(np.nanmax(mag)))
    if np.count_nonzero(mask) < 8:
        mask = mag > max(1e-5, 0.01 * float(np.nanmax(mag)))
    omega = 2 * np.pi * freqs
    phase = np.unwrap(np.angle(response))
    gd = -np.gradient(phase, omega)
    return float(np.nanmedian(gd[mask])) if np.any(mask) else 0.0


def dominant_delay(freqs: np.ndarray, s: np.ndarray) -> float:
    delays = [estimate_group_delay(freqs, s[:, i, j]) for i, j in THROUGH_PAIRS_4P]
    delays = [value for value in delays if np.isfinite(value) and value > 0]
    return float(np.median(delays)) if delays else 0.0


def delay_matrix(freqs: np.ndarray, s: np.ndarray, mode: str, tau: float) -> np.ndarray:
    delays = np.zeros((s.shape[1], s.shape[2]), dtype=float)
    if mode == "none":
        return delays
    if mode == "global_all":
        delays[:, :] = tau
        return delays
    if mode == "through_only":
        for i, j in THROUGH_PAIRS_4P:
            delays[i, j] = tau
        return delays
    if mode == "per_entry":
        for i in range(s.shape[1]):
            for j in range(s.shape[2]):
                delay = estimate_group_delay(freqs, s[:, i, j])
                delays[i, j] = delay if np.isfinite(delay) and delay > 1e-9 else 0.0
        return delays
    raise ValueError(mode)


def apply_delay_transform(s: np.ndarray, freqs: np.ndarray, delays: np.ndarray, sign: float) -> np.ndarray:
    out = np.array(s, copy=True)
    omega = 2 * np.pi * freqs
    for i in range(out.shape[1]):
        for j in range(out.shape[2]):
            if delays[i, j]:
                out[:, i, j] *= np.exp(sign * 1j * omega * delays[i, j])
    return out


def make_network_like(skrf, nw, s: np.ndarray, name: str):
    out = nw.copy()
    out.s = s
    out.name = name
    return out


def vector_fit_network(nw, order: int):
    _, VectorFitting = ensure_skrf()
    vf = VectorFitting(nw)
    vf.vector_fit(n_poles_real=order, n_poles_cmplx=order)
    return vf


def plot_through(freqs: np.ndarray, original: np.ndarray, fitted: np.ndarray, path: Path, title: str) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    pairs = [("S31", 2, 0), ("S42", 3, 1)]
    for label, i, j in pairs:
        axes[0].plot(freqs * 1e-9, 20 * np.log10(np.maximum(np.abs(original[:, i, j]), 1e-30)), label=f"{label} Touchstone")
        axes[0].plot(freqs * 1e-9, 20 * np.log10(np.maximum(np.abs(fitted[:, i, j]), 1e-30)), "--", label=f"{label} fit")
        phase_err = np.rad2deg(np.angle(fitted[:, i, j] * np.conj(original[:, i, j])))
        axes[1].plot(freqs * 1e-9, phase_err, label=f"{label} phase error")
    axes[0].set_ylabel("Magnitude (dB)")
    axes[1].set_ylabel("Phase Error (deg)")
    axes[1].set_xlabel("Frequency (GHz)")
    for ax in axes:
        ax.grid(True, color="#d7dde6")
        ax.legend(frameon=False)
    fig.suptitle(title, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(args: argparse.Namespace) -> int:
    skrf, _ = ensure_skrf(args.skrf_target)
    nw = skrf.Network(str(args.touchstone.resolve()))
    freqs = np.asarray(nw.frequency.f, dtype=float)
    original_s = np.asarray(nw.s, dtype=complex)
    tau = args.delay_s if args.delay_s is not None else dominant_delay(freqs, original_s)

    rows: list[dict[str, object]] = []
    for mode in args.modes.split(","):
        mode = mode.strip()
        delays = delay_matrix(freqs, original_s, mode, tau)
        residual_s = apply_delay_transform(original_s, freqs, delays, sign=+1.0)
        residual_nw = make_network_like(skrf, nw, residual_s, f"{nw.name}_{mode}_residual")
        for order in args.orders:
            row: dict[str, object] = {
                "mode": mode,
                "order": order,
                "estimated_delay_s": tau,
                "estimated_delay_ns": tau * 1e9,
            }
            try:
                vf = vector_fit_network(residual_nw, order)
                residual_fit = fitted_s_matrices(vf, freqs)
                fitted_original = apply_delay_transform(residual_fit, freqs, delays, sign=-1.0)
                metrics = frequency_metrics(nw, fitted_original)
                row.update(metrics)
                max_sv, max_idx = max_singular_from_mats(fitted_original)
                row["fit_max_sv_samples"] = max_sv
                row["fit_max_sv_samples_freq_hz"] = float(freqs[max_idx])
                try:
                    row["residual_fit_is_passive"] = bool(vf.is_passive())
                except Exception as exc:
                    row["residual_fit_is_passive"] = False
                    row["passivity_error"] = str(exc)
                plot_path = args.out_dir / f"{mode}_order{order}_through_fit.png"
                plot_through(freqs, original_s, fitted_original, plot_path, f"{args.touchstone.name}: {mode}, order {order}")
                row["plot"] = str(plot_path.resolve().relative_to(ROOT)).replace("\\", "/")
            except Exception as exc:
                row["fit_error"] = str(exc)
            rows.append(row)
            print(mode, order, {k: row.get(k) for k in ("fit_complex_rms", "fit_mag_db_max_above_m40", "fit_group_delay_rms_ps", "fit_max_sv_samples", "fit_error")})

    write_csv(args.out_dir / "delay_residual_fit_metrics.csv", rows)
    (args.out_dir / "README.md").write_text(
        "\n".join(
            [
                "# Delay-Aware S-parameter Fit Prototype",
                "",
                f"Touchstone: `{args.touchstone}`",
                f"Estimated dominant delay: `{fmt(tau)}` s (`{fmt(tau * 1e9)}` ns)",
                "",
                "This is a diagnostic residual-fit experiment. It does not yet emit an ngspice-ready delayed macromodel.",
                "",
                "Results: `delay_residual_fit_metrics.csv`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prototype delay-removal residual fitting for long S-parameter channels.")
    parser.add_argument("--touchstone", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--skrf-target", type=Path, default=None)
    parser.add_argument("--orders", type=int, nargs="+", default=[8, 16])
    parser.add_argument("--modes", default="none,global_all,through_only,per_entry")
    parser.add_argument("--delay-s", type=float, default=None)
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
