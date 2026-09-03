from __future__ import annotations

import csv
import math
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results" / "clarity_bbs_s2p_overlay_2026-06-19"
PLOTS_DIR = OUT_DIR / "plots"
ARTIFACTS_DIR = OUT_DIR / "artifacts"

ORIGINAL_S2P = ROOT / "hspice" / "sparam" / "Clarity_example.S2P"
BBS_STUDY = ROOT / "results" / "sparam_bbs_quality_tuning_v1_2026-06-17"
BBS_FITTED_S2P = (
    BBS_STUDY
    / "channels"
    / "Clarity_example_09b58d4b"
    / "bbs"
    / "clean"
    / "passivity2"
    / "gspice"
    / "BBSResult_Clarity_example"
    / "Clarity_example_Fitted.s2p"
)
BBS_GSPICE = BBS_FITTED_S2P.with_name("Clarity_example_GSPICE.txt")
BBS_NGSPICE_WRAPPER = (
    BBS_STUDY
    / "channels"
    / "Clarity_example_09b58d4b"
    / "models"
    / "bbs_passivity2_gspice_clean"
    / "Clarity_example_09b58d4b_bbs_passivity2_gspice_clean_ngspice_wrapper.sp"
)
TRANSIENT_OVERLAY_ROOT = BBS_STUDY / "plots" / "bbs_overlays" / "Clarity_example_09b58d4b"

S2P_ORDER = [("S11", 0, 0), ("S21", 1, 0), ("S12", 0, 1), ("S22", 1, 1)]


def unit_scale(unit: str) -> float:
    lookup = {
        "hz": 1.0,
        "khz": 1e3,
        "mhz": 1e6,
        "ghz": 1e9,
    }
    key = unit.lower()
    if key not in lookup:
        raise ValueError(f"Unsupported Touchstone frequency unit: {unit}")
    return lookup[key]


def pair_to_complex(a: float, b: float, fmt: str) -> complex:
    key = fmt.lower()
    if key == "ri":
        return complex(a, b)
    if key == "ma":
        return a * complex(math.cos(math.radians(b)), math.sin(math.radians(b)))
    if key == "db":
        mag = 10 ** (a / 20.0)
        return mag * complex(math.cos(math.radians(b)), math.sin(math.radians(b)))
    raise ValueError(f"Unsupported Touchstone data format: {fmt}")


def read_s2p(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    scale = 1.0
    fmt = "ri"
    meta: dict[str, str] = {}
    rows: list[tuple[float, np.ndarray]] = []
    pending: list[float] = []

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("!"):
            continue
        if "!" in line:
            line = line.split("!", 1)[0].strip()
        if line.startswith("#"):
            toks = line[1:].strip().split()
            meta["option_line"] = line
            if len(toks) >= 3:
                scale = unit_scale(toks[0])
                fmt = toks[2]
            continue
        if not line:
            continue
        pending.extend(float(tok) for tok in line.split())
        while len(pending) >= 9:
            chunk = pending[:9]
            pending = pending[9:]
            freq = chunk[0] * scale
            values = [pair_to_complex(chunk[i], chunk[i + 1], fmt) for i in range(1, 9, 2)]
            mat = np.zeros((2, 2), dtype=complex)
            # Touchstone v1 2-port order: S11, S21, S12, S22.
            mat[0, 0] = values[0]
            mat[1, 0] = values[1]
            mat[0, 1] = values[2]
            mat[1, 1] = values[3]
            rows.append((freq, mat))

    if pending:
        raise ValueError(f"Trailing numeric data in {path}: {pending}")
    if not rows:
        raise ValueError(f"No S2P data found in {path}")
    freqs = np.asarray([row[0] for row in rows], dtype=float)
    s = np.asarray([row[1] for row in rows], dtype=complex)
    meta["format"] = fmt.upper()
    return freqs, s, meta


def interp_complex(src_f: np.ndarray, src_y: np.ndarray, dst_f: np.ndarray) -> np.ndarray:
    return np.interp(dst_f, src_f, np.real(src_y)) + 1j * np.interp(dst_f, src_f, np.imag(src_y))


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1e-15))


def phase_deg(x: np.ndarray) -> np.ndarray:
    return np.unwrap(np.angle(x)) * 180.0 / np.pi


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


def metrics(freqs: np.ndarray, original: np.ndarray, fitted: np.ndarray) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    all_diff = fitted - original
    rows.append(
        {
            "path": "all",
            "complex_rms": float(np.sqrt(np.mean(np.abs(all_diff) ** 2))),
            "complex_max": float(np.max(np.abs(all_diff))),
            "mag_db_rms": float(np.sqrt(np.mean((db20(fitted) - db20(original)) ** 2))),
            "mag_db_max": float(np.max(np.abs(db20(fitted) - db20(original)))),
        }
    )
    for name, i, j in S2P_ORDER:
        a = original[:, i, j]
        b = fitted[:, i, j]
        diff = b - a
        mag_a = db20(a)
        mag_b = db20(b)
        phase_a = phase_deg(a)
        phase_b = phase_deg(b)
        above = mag_a > -40.0
        rows.append(
            {
                "path": name,
                "complex_rms": float(np.sqrt(np.mean(np.abs(diff) ** 2))),
                "complex_max": float(np.max(np.abs(diff))),
                "mag_db_rms": float(np.sqrt(np.mean((mag_b - mag_a) ** 2))),
                "mag_db_max": float(np.max(np.abs(mag_b - mag_a))),
                "mag_db_max_above_m40": float(np.max(np.abs((mag_b - mag_a)[above]))) if np.any(above) else "",
                "phase_rms_deg": float(np.sqrt(np.mean((phase_b - phase_a) ** 2))),
                "phase_max_deg": float(np.max(np.abs(phase_b - phase_a))),
                "original_mag_min_db": float(np.min(mag_a)),
                "original_mag_max_db": float(np.max(mag_a)),
            }
        )
    return rows


def plot_mag_phase(freqs: np.ndarray, original: np.ndarray, fitted: np.ndarray) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), sharex=True)
    for ax, (name, i, j) in zip(axes.flat, S2P_ORDER):
        ax.plot(freqs / 1e9, db20(original[:, i, j]), lw=1.8, marker="o", ms=3.0, label="Original Clarity_example.S2P")
        ax.plot(freqs / 1e9, db20(fitted[:, i, j]), lw=1.7, marker="x", ms=3.0, ls="--", label="BBS fitted response")
        ax.set_title(name)
        ax.set_ylabel("Magnitude (dB)")
        ax.grid(True, alpha=0.28)
    axes[1, 0].set_xlabel("Frequency (GHz)")
    axes[1, 1].set_xlabel("Frequency (GHz)")
    axes[0, 0].legend(loc="best")
    fig.suptitle("Clarity_example: original S2P vs BBS converted-model fitted response")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(PLOTS_DIR / "01_sparameter_magnitude_overlay.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), sharex=True)
    for ax, (name, i, j) in zip(axes.flat, S2P_ORDER):
        ax.plot(freqs / 1e9, phase_deg(original[:, i, j]), lw=2.0, label="Original Clarity_example.S2P")
        ax.plot(freqs / 1e9, phase_deg(fitted[:, i, j]), lw=1.9, ls="--", label="BBS fitted response")
        ax.set_title(name)
        ax.set_ylabel("Unwrapped phase (deg)")
        ax.grid(True, alpha=0.28)
    axes[1, 0].set_xlabel("Frequency (GHz)")
    axes[1, 1].set_xlabel("Frequency (GHz)")
    axes[0, 0].legend(loc="best")
    fig.suptitle("Clarity_example: phase overlay")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(PLOTS_DIR / "02_sparameter_phase_overlay.png", dpi=180)
    plt.close(fig)


def plot_source_check(freqs: np.ndarray, original: np.ndarray, fitted: np.ndarray) -> None:
    s21 = db20(original[:, 1, 0])
    s12 = db20(original[:, 0, 1])
    b21 = db20(fitted[:, 1, 0])
    b12 = db20(fitted[:, 0, 1])

    rows = []
    for idx, freq in enumerate(freqs):
        rows.append(
            {
                "freq_ghz": freq / 1e9,
                "original_s21_db": s21[idx],
                "original_s12_db": s12[idx],
                "bbs_s21_db": b21[idx],
                "bbs_s12_db": b12[idx],
                "original_s21_real": float(np.real(original[idx, 1, 0])),
                "original_s21_imag": float(np.imag(original[idx, 1, 0])),
            }
        )
    write_csv(OUT_DIR / "source_check_s21_s12_points.csv", rows)

    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.0), sharex=True)
    axes[0].plot(freqs / 1e9, s21, lw=1.7, marker="o", ms=3.5, label="Original S21 raw points")
    axes[0].plot(freqs / 1e9, s12, lw=1.3, marker="s", ms=3.0, ls=":", label="Original S12 raw points")
    axes[0].plot(freqs / 1e9, b21, lw=1.6, marker="x", ms=3.5, ls="--", label="BBS S21 fitted")
    axes[0].set_ylabel("Magnitude (dB)")
    axes[0].grid(True, alpha=0.28)
    axes[0].legend(loc="best")
    axes[0].set_title("Source check: original S21/S12 are raw Touchstone points, not a fitted straight line")

    axes[1].plot(freqs / 1e9, b21 - s21, lw=1.8, marker="x", ms=3.5, label="BBS S21 - original S21")
    axes[1].plot(freqs / 1e9, b12 - s12, lw=1.5, marker="s", ms=3.0, ls=":", label="BBS S12 - original S12")
    axes[1].axhline(0.0, color="black", lw=0.8)
    axes[1].set_ylabel("Magnitude error (dB)")
    axes[1].set_xlabel("Frequency (GHz)")
    axes[1].grid(True, alpha=0.28)
    axes[1].legend(loc="best")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "04_source_check_s21_s12_raw_points.png", dpi=180)
    plt.close(fig)


def plot_error(freqs: np.ndarray, original: np.ndarray, fitted: np.ndarray) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11.0, 7.2), sharex=True)
    for name, i, j in S2P_ORDER:
        axes[0].plot(freqs / 1e9, np.abs(fitted[:, i, j] - original[:, i, j]), lw=1.8, label=name)
        axes[1].plot(freqs / 1e9, db20(fitted[:, i, j]) - db20(original[:, i, j]), lw=1.8, label=name)
    axes[0].set_ylabel("Complex abs error")
    axes[1].set_ylabel("Magnitude error (dB)")
    axes[1].set_xlabel("Frequency (GHz)")
    for ax in axes:
        ax.grid(True, alpha=0.28)
        ax.legend(loc="best", ncol=4)
    fig.suptitle("Clarity_example: BBS fitted response error vs original S2P")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(PLOTS_DIR / "03_sparameter_error.png", dpi=180)
    plt.close(fig)


def copy_artifacts() -> dict[str, str]:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for label, src, name in (
        ("original_s2p", ORIGINAL_S2P, "Clarity_example_original.S2P"),
        ("bbs_fitted_s2p", BBS_FITTED_S2P, "Clarity_example_BBS_Fitted.s2p"),
        ("bbs_gspice_model", BBS_GSPICE, "Clarity_example_GSPICE.txt"),
        ("bbs_ngspice_wrapper", BBS_NGSPICE_WRAPPER, "Clarity_example_ngspice_wrapper.sp"),
    ):
        dst = ARTIFACTS_DIR / name
        shutil.copy2(src, dst)
        copied[label] = str(dst.relative_to(ROOT))

    overlay_files = {
        "transient_combined_overlay": TRANSIENT_OVERLAY_ROOT / "bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50.png",
        "transient_rx_overlay": TRANSIENT_OVERLAY_ROOT / "rx" / "bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_rx.png",
        "transient_tx_overlay": TRANSIENT_OVERLAY_ROOT / "tx" / "bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_tx.png",
    }
    for label, src in overlay_files.items():
        if src.exists():
            dst = PLOTS_DIR / src.name
            shutil.copy2(src, dst)
            copied[label] = str(dst.relative_to(ROOT))
    return copied


def write_readme(copied: dict[str, str], metric_rows: list[dict[str, object]]) -> None:
    by_path = {row["path"]: row for row in metric_rows}
    lines = [
        "# Clarity_example BBS Overlay",
        "",
        "This folder compares the original `Clarity_example.S2P` with the BBS clean/passivity2 General SPICE conversion.",
        "",
        "Important detail: the frequency-domain plots use `Clarity_example_Fitted.s2p`, which BroadbandSPICE writes next to `Clarity_example_GSPICE.txt`. That fitted Touchstone is BBS's exported frequency response for the generated SPICE macromodel.",
        "",
        "## Inputs",
        "",
        f"- Original S2P: `{copied['original_s2p']}`",
        f"- BBS fitted response: `{copied['bbs_fitted_s2p']}`",
        f"- BBS General SPICE model: `{copied['bbs_gspice_model']}`",
        f"- ngspice wrapper: `{copied['bbs_ngspice_wrapper']}`",
        "",
        "## Plots",
        "",
        "- `plots/01_sparameter_magnitude_overlay.png`",
        "- `plots/02_sparameter_phase_overlay.png`",
        "- `plots/03_sparameter_error.png`",
        "- `plots/04_source_check_s21_s12_raw_points.png`: raw-point check for the nearly-straight original through paths",
    ]
    if "transient_combined_overlay" in copied:
        lines.extend(
            [
                "- `plots/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50.png`: transient HSPICE original S-element vs ngspice BBS model",
                "- `plots/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_rx.png`: RX-only transient overlay",
                "- `plots/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_tx.png`: TX-only transient overlay",
            ]
        )
    lines.extend(
        [
            "",
            "## Fit Metrics",
            "",
            "| Path | Complex RMS | Complex max | Mag dB RMS | Mag dB max | Phase RMS deg |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for path in ("all", "S11", "S21", "S12", "S22"):
        row = by_path[path]
        lines.append(
            "| {path} | {cr:.6g} | {cm:.6g} | {mr:.6g} | {mm:.6g} | {pr} |".format(
                path=path,
                cr=float(row["complex_rms"]),
                cm=float(row["complex_max"]),
                mr=float(row["mag_db_rms"]),
                mm=float(row["mag_db_max"]),
                pr="" if row.get("phase_rms_deg", "") == "" else f"{float(row['phase_rms_deg']):.6g}",
            )
        )
    lines.extend(
        [
            "",
            "## Reading The Result",
            "",
            "The BBS frequency fit is quite close in complex RMS, especially on the dominant through paths. The largest visible frequency-domain discrepancies are in magnitude ripple/error on some paths rather than a gross miss.",
            "",
            "The original S21/S12 magnitude curves look almost straight because the source Touchstone itself is very smooth and nearly monotonic in dB: S21 moves from about -0.020 dB at 50 MHz to about -0.480 dB at 2 GHz. The source-check plot uses markers to show the raw 40 Touchstone samples directly.",
            "",
            "The existing transient audit overlay is included because it answers a different question: whether the generated General SPICE model in ngspice correlates with HSPICE's native S-element transient behavior.",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    for path in (ORIGINAL_S2P, BBS_FITTED_S2P, BBS_GSPICE, BBS_NGSPICE_WRAPPER):
        if not path.exists():
            raise FileNotFoundError(path)

    f0, s0, _ = read_s2p(ORIGINAL_S2P)
    f1, s1, _ = read_s2p(BBS_FITTED_S2P)
    if len(f0) != len(f1) or np.max(np.abs(f0 - f1)) > 1e-6:
        fitted = np.zeros_like(s0)
        for i in range(2):
            for j in range(2):
                fitted[:, i, j] = interp_complex(f1, s1[:, i, j], f0)
    else:
        fitted = s1

    plot_mag_phase(f0, s0, fitted)
    plot_source_check(f0, s0, fitted)
    plot_error(f0, s0, fitted)
    metric_rows = metrics(f0, s0, fitted)
    write_csv(OUT_DIR / "fit_metrics.csv", metric_rows)
    copied = copy_artifacts()
    write_readme(copied, metric_rows)

    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"PLOTS={PLOTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
