from __future__ import annotations

import argparse
import csv
import math
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent


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


def port_count_from_suffix(path: Path) -> int:
    suffix = path.suffix.lower()
    if not (suffix.startswith(".s") and suffix.endswith("p")):
        raise ValueError(f"Cannot infer port count from suffix: {path}")
    return int(suffix[2:-1])


def touchstone_pairs_to_matrix(values: list[complex], ports: int) -> np.ndarray:
    if len(values) != ports * ports:
        raise ValueError(f"Expected {ports * ports} S-parameters, got {len(values)}")

    mat = np.zeros((ports, ports), dtype=complex)
    if ports == 2:
        # Touchstone 2-port v1 has the historical order S11, S21, S12, S22.
        order = [(0, 0), (1, 0), (0, 1), (1, 1)]
    else:
        # Touchstone n-port v1 is row-major: S11, S12, ..., S1N, S21, ...
        order = [(row, col) for row in range(ports) for col in range(ports)]
    for value, (row, col) in zip(values, order):
        mat[row, col] = value
    return mat


def read_touchstone(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    ports = port_count_from_suffix(path)
    scale = 1.0
    fmt = "ri"
    z0 = ""
    meta: dict[str, str] = {"ports": str(ports)}
    rows: list[tuple[float, np.ndarray]] = []
    pending: list[float] = []
    row_len = 1 + 2 * ports * ports

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
            if "R" in toks:
                idx = toks.index("R")
                z0 = " ".join(toks[idx + 1 :])
            elif "r" in toks:
                idx = toks.index("r")
                z0 = " ".join(toks[idx + 1 :])
            continue
        if not line:
            continue

        pending.extend(float(tok) for tok in line.split())
        while len(pending) >= row_len:
            chunk = pending[:row_len]
            pending = pending[row_len:]
            freq = chunk[0] * scale
            pairs = [pair_to_complex(chunk[idx], chunk[idx + 1], fmt) for idx in range(1, row_len, 2)]
            rows.append((freq, touchstone_pairs_to_matrix(pairs, ports)))

    if pending:
        raise ValueError(f"Trailing numeric data in {path}: {pending[:12]}")
    if not rows:
        raise ValueError(f"No Touchstone data found in {path}")
    meta["format"] = fmt.upper()
    meta["z0"] = z0
    freqs = np.asarray([row[0] for row in rows], dtype=float)
    s = np.asarray([row[1] for row in rows], dtype=complex)
    return freqs, s, meta


def resolve_path(text: str | None) -> Path | None:
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = ROOT / path
    return path


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1e-15))


def phase_deg(x: np.ndarray) -> np.ndarray:
    return np.unwrap(np.angle(x)) * 180.0 / np.pi


def interp_complex(src_f: np.ndarray, src_y: np.ndarray, dst_f: np.ndarray) -> np.ndarray:
    return np.interp(dst_f, src_f, np.real(src_y)) + 1j * np.interp(dst_f, src_f, np.imag(src_y))


def labels(ports: int) -> list[tuple[str, int, int]]:
    return [(f"S{row + 1}{col + 1}", row, col) for row in range(ports) for col in range(ports)]


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


def fit_metrics(freqs: np.ndarray, original: np.ndarray, fitted: np.ndarray) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    diff = fitted - original
    rows.append(
        {
            "path": "all",
            "complex_rms": float(np.sqrt(np.mean(np.abs(diff) ** 2))),
            "complex_max": float(np.max(np.abs(diff))),
            "mag_db_rms": float(np.sqrt(np.mean((db20(fitted) - db20(original)) ** 2))),
            "mag_db_max": float(np.max(np.abs(db20(fitted) - db20(original)))),
        }
    )
    for name, row, col in labels(original.shape[1]):
        a = original[:, row, col]
        b = fitted[:, row, col]
        mag_a = db20(a)
        mag_b = db20(b)
        phase_a = phase_deg(a)
        phase_b = phase_deg(b)
        above = mag_a > -40.0
        rows.append(
            {
                "path": name,
                "complex_rms": float(np.sqrt(np.mean(np.abs(b - a) ** 2))),
                "complex_max": float(np.max(np.abs(b - a))),
                "mag_db_rms": float(np.sqrt(np.mean((mag_b - mag_a) ** 2))),
                "mag_db_max": float(np.max(np.abs(mag_b - mag_a))),
                "mag_db_max_above_m40": float(np.max(np.abs((mag_b - mag_a)[above]))) if np.any(above) else "",
                "phase_rms_deg": float(np.sqrt(np.mean((phase_b - phase_a) ** 2))),
                "phase_max_deg": float(np.max(np.abs(phase_b - phase_a))),
                "original_mag_min_db": float(np.min(mag_a)),
                "original_mag_max_db": float(np.max(mag_a)),
                "fitted_mag_min_db": float(np.min(mag_b)),
                "fitted_mag_max_db": float(np.max(mag_b)),
            }
        )
    return rows


def dominant_paths(original: np.ndarray, count: int = 6) -> list[tuple[str, int, int]]:
    ports = original.shape[1]
    scored: list[tuple[float, str, int, int]] = []
    for name, row, col in labels(ports):
        if row == col:
            continue
        scored.append((float(np.max(db20(original[:, row, col]))), name, row, col))
    scored.sort(reverse=True)
    return [(name, row, col) for _, name, row, col in scored[:count]]


def plot_matrix(
    path: Path,
    freqs: np.ndarray,
    original: np.ndarray,
    fitted: np.ndarray,
    *,
    title: str,
    kind: str,
    original_label: str,
) -> None:
    ports = original.shape[1]
    fig, axes = plt.subplots(ports, ports, figsize=(3.2 * ports, 2.65 * ports), sharex=True)
    axes_arr = np.asarray(axes).reshape(ports, ports)
    for name, row, col in labels(ports):
        ax = axes_arr[row, col]
        a = original[:, row, col]
        b = fitted[:, row, col]
        if kind == "mag":
            ax.plot(freqs / 1e9, db20(a), lw=1.4, marker="o", ms=1.9, label=original_label)
            ax.plot(freqs / 1e9, db20(b), lw=1.3, marker="x", ms=1.9, ls="--", label="BBS fitted response")
            ax.set_ylabel("Mag (dB)")
        elif kind == "phase":
            ax.plot(freqs / 1e9, phase_deg(a), lw=1.4, label=original_label)
            ax.plot(freqs / 1e9, phase_deg(b), lw=1.3, ls="--", label="BBS fitted response")
            ax.set_ylabel("Phase (deg)")
        elif kind == "error":
            ax.plot(freqs / 1e9, np.abs(b - a), lw=1.4, label="Complex abs error")
            ax2 = ax.twinx()
            ax2.plot(freqs / 1e9, db20(b) - db20(a), lw=1.2, color="tab:orange", alpha=0.8, label="Mag dB error")
            ax.set_ylabel("|dS|")
            ax2.set_ylabel("dB err")
        else:
            raise ValueError(kind)
        ax.set_title(name)
        ax.grid(True, alpha=0.25)
        if row == ports - 1:
            ax.set_xlabel("Frequency (GHz)")
    handles, legend_labels = axes_arr[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, legend_labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 0.995))
    fig.suptitle(title, y=1.025)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_group(
    path: Path,
    freqs: np.ndarray,
    original: np.ndarray,
    fitted: np.ndarray,
    path_defs: list[tuple[str, int, int]],
    *,
    title: str,
    original_label: str,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11.0, 7.4), sharex=True)
    for name, row, col in path_defs:
        axes[0].plot(freqs / 1e9, db20(original[:, row, col]), lw=1.7, label=f"{name} original")
        axes[0].plot(freqs / 1e9, db20(fitted[:, row, col]), lw=1.4, ls="--", label=f"{name} BBS")
        axes[1].plot(freqs / 1e9, db20(fitted[:, row, col]) - db20(original[:, row, col]), lw=1.6, label=name)
    axes[0].set_ylabel("Magnitude (dB)")
    axes[1].set_ylabel("BBS - original (dB)")
    axes[1].set_xlabel("Frequency (GHz)")
    axes[0].grid(True, alpha=0.28)
    axes[1].grid(True, alpha=0.28)
    axes[0].legend(loc="best", ncol=2, fontsize=8)
    axes[1].legend(loc="best", ncol=3, fontsize=8)
    axes[0].set_title(f"{title}: {original_label} vs BBS fitted response")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_error_bar(path: Path, rows: list[dict[str, object]]) -> None:
    path_rows = [row for row in rows if row["path"] != "all"]
    names = [str(row["path"]) for row in path_rows]
    mag_rms = [float(row["mag_db_rms"]) for row in path_rows]
    complex_rms = [float(row["complex_rms"]) for row in path_rows]

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.5), sharex=True)
    x = np.arange(len(names))
    axes[0].bar(x, mag_rms, color="tab:blue", alpha=0.82)
    axes[0].set_ylabel("Mag RMS error (dB)")
    axes[0].grid(axis="y", alpha=0.28)
    axes[1].bar(x, complex_rms, color="tab:orange", alpha=0.82)
    axes[1].set_ylabel("Complex RMS error")
    axes[1].set_xticks(x, names, rotation=45, ha="right")
    axes[1].grid(axis="y", alpha=0.28)
    fig.suptitle("BBS fit error summary by S-parameter path")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def copy_if_exists(src: Path | None, dst: Path) -> Path | None:
    if not src or not src.exists():
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def copy_transient_overlays(study_dir: Path, channel_id: str, out_dir: Path) -> list[Path]:
    src_dir = study_dir / "plots" / "bbs_overlays" / channel_id
    if not src_dir.exists():
        return []
    dst_dir = out_dir / "plots" / "transient_overlays"
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in sorted(src_dir.glob("*.png")):
        dst = dst_dir / src.name
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def read_ranking(study_dir: Path, channel_id: str) -> dict[str, str]:
    ranking = study_dir / "bbs_ranking.csv"
    with ranking.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("channel_id") == channel_id:
                return row
    raise ValueError(f"channel_id {channel_id!r} not found in {ranking}")


def write_readme(
    out_dir: Path,
    channel_id: str,
    original: Path,
    fitted: Path,
    circuit: Path | None,
    wrapper: Path | None,
    orig_meta: dict[str, str],
    fitted_meta: dict[str, str],
    rows: list[dict[str, object]],
    ranking: dict[str, str],
    transient_overlays: list[Path],
) -> None:
    def rel(path: Path | None) -> str:
        if not path:
            return ""
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    metric_lines = [
        "| Path | Complex RMS | Complex max | Mag dB RMS | Mag dB max | Mag dB max above -40 dB | Phase RMS deg |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        metric_lines.append(
            "| {path} | {complex_rms:.6g} | {complex_max:.6g} | {mag_db_rms:.6g} | {mag_db_max:.6g} | {above} | {phase} |".format(
                path=row["path"],
                complex_rms=float(row["complex_rms"]),
                complex_max=float(row["complex_max"]),
                mag_db_rms=float(row["mag_db_rms"]),
                mag_db_max=float(row["mag_db_max"]),
                above=(
                    f"{float(row['mag_db_max_above_m40']):.6g}"
                    if row.get("mag_db_max_above_m40") not in ("", None)
                    else ""
                ),
                phase=(f"{float(row['phase_rms_deg']):.6g}" if row.get("phase_rms_deg") not in ("", None) else ""),
            )
        )

    readme = [
        f"# {channel_id} BBS Touchstone Overlay",
        "",
        "This folder compares an original Touchstone channel with the fitted Touchstone response written by BroadbandSPICE next to the generated General SPICE model.",
        "",
        "Important detail: the frequency-domain comparison uses BBS's exported fitted Touchstone response. That is the BBS model's own S-parameter response, not a separate ngspice AC extraction from the `.sp` wrapper.",
        "",
        "## Inputs",
        "",
        f"- Original Touchstone: `{rel(original)}`",
        f"- BBS fitted Touchstone: `{rel(fitted)}`",
        f"- BBS General SPICE model: `{rel(circuit)}`" if circuit else "- BBS General SPICE model: not found",
        f"- ngspice wrapper: `{rel(wrapper)}`" if wrapper else "- ngspice wrapper: not found",
        "",
        "## Source Metadata",
        "",
        f"- Original option line: `{orig_meta.get('option_line', '')}`",
        f"- Fitted option line: `{fitted_meta.get('option_line', '')}`",
        f"- Ports: `{orig_meta.get('ports', '')}`",
        f"- Original format: `{orig_meta.get('format', '')}`",
        f"- Fitted format: `{fitted_meta.get('format', '')}`",
        f"- Z0: `{orig_meta.get('z0', '')}`",
        "",
        "## BBS Ranking Context",
        "",
        f"- Candidate: `{ranking.get('best_bbs_candidate', '')}`",
        f"- Independent trust class: `{ranking.get('best_bbs_trust_class', '')}`",
        f"- RX trust class: `{ranking.get('best_bbs_rx_trust_class', '')}`",
        f"- Full-model trust class: `{ranking.get('best_bbs_full_model_trust_class', '')}`",
        f"- ngspice smoke pass: `{ranking.get('best_bbs_ngspice_pass', '')}`",
        "",
        "## Plots",
        "",
        "- `plots/01_sparameter_magnitude_matrix_overlay.png`",
        "- `plots/02_sparameter_phase_matrix_overlay.png`",
        "- `plots/03_sparameter_error_matrix.png`",
        "- `plots/04_dominant_transmission_paths.png`",
        "- `plots/05_reflection_paths.png`",
        "- `plots/06_error_summary_by_path.png`",
        "",
    ]
    if transient_overlays:
        readme.extend(
            [
                "Available transient HSPICE-vs-ngspice audit overlays copied from the BBS campaign:",
                "",
            ]
        )
        for path in transient_overlays:
            readme.append(f"- `{rel(path)}`")
        readme.append("")
    readme.extend(
        [
            "## Fit Metrics",
            "",
            *metric_lines,
            "",
            "## Reading The Result",
            "",
            "Use the matrix plots to see whether the converted model preserves the full multiport behavior. The dominant-path plot focuses on the strongest off-diagonal transmission terms, while the reflection plot isolates the diagonal terms.",
            "",
            "A low complex RMS can still hide larger dB error on very small coupling paths. For deciding simulation readiness, this should be read together with transient ngspice/HSPICE correlation, not by frequency fit alone.",
            "",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Make original Touchstone vs BBS fitted Touchstone overlay plots.")
    parser.add_argument("--study-dir", default="results/sparam_bbs_quality_tuning_v1_2026-06-17")
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    study_dir = resolve_path(args.study_dir)
    assert study_dir is not None
    out_dir = resolve_path(args.out_dir)
    assert out_dir is not None
    plots_dir = out_dir / "plots"
    artifacts_dir = out_dir / "artifacts"
    plots_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    ranking = read_ranking(study_dir, args.channel_id)
    original_path = resolve_path(ranking.get("channel_path"))
    fitted_path = resolve_path(ranking.get("best_bbs_fitted_touchstone"))
    circuit_path = resolve_path(ranking.get("best_bbs_circuit_file"))
    wrapper_path = resolve_path(ranking.get("best_bbs_spice_file"))
    if original_path is None or not original_path.exists():
        raise FileNotFoundError(f"Original Touchstone not found: {original_path}")
    if fitted_path is None or not fitted_path.exists():
        raise FileNotFoundError(f"BBS fitted Touchstone not found: {fitted_path}")

    f0, s0, meta0 = read_touchstone(original_path)
    f1, s1, meta1 = read_touchstone(fitted_path)
    if s0.shape[1:] != s1.shape[1:]:
        raise ValueError(f"Port-count mismatch: original {s0.shape[1:]} vs fitted {s1.shape[1:]}")
    if len(f0) != len(f1) or not np.allclose(f0, f1):
        s1_eval = np.empty_like(s0)
        for row in range(s0.shape[1]):
            for col in range(s0.shape[2]):
                s1_eval[:, row, col] = interp_complex(f1, s1[:, row, col], f0)
    else:
        s1_eval = s1

    rows = fit_metrics(f0, s0, s1_eval)
    write_csv(out_dir / "fit_metrics.csv", rows)

    original_copy = copy_if_exists(original_path, artifacts_dir / f"{original_path.stem}_original{original_path.suffix}")
    fitted_copy = copy_if_exists(fitted_path, artifacts_dir / f"{fitted_path.stem}_bbs_fitted{fitted_path.suffix}")
    circuit_copy = copy_if_exists(circuit_path, artifacts_dir / circuit_path.name if circuit_path else artifacts_dir / "missing")
    wrapper_copy = copy_if_exists(wrapper_path, artifacts_dir / wrapper_path.name if wrapper_path else artifacts_dir / "missing")

    original_label = f"Original {original_path.name}"
    title_prefix = f"{args.channel_id}: original vs BBS converted-model fitted response"
    plot_matrix(
        plots_dir / "01_sparameter_magnitude_matrix_overlay.png",
        f0,
        s0,
        s1_eval,
        title=title_prefix,
        kind="mag",
        original_label=original_label,
    )
    plot_matrix(
        plots_dir / "02_sparameter_phase_matrix_overlay.png",
        f0,
        s0,
        s1_eval,
        title=f"{args.channel_id}: phase overlay",
        kind="phase",
        original_label=original_label,
    )
    plot_matrix(
        plots_dir / "03_sparameter_error_matrix.png",
        f0,
        s0,
        s1_eval,
        title=f"{args.channel_id}: BBS fit error",
        kind="error",
        original_label=original_label,
    )
    plot_group(
        plots_dir / "04_dominant_transmission_paths.png",
        f0,
        s0,
        s1_eval,
        dominant_paths(s0, count=min(6, s0.shape[1] * (s0.shape[1] - 1))),
        title=f"{args.channel_id} dominant transmission paths",
        original_label=original_label,
    )
    reflections = [(f"S{idx + 1}{idx + 1}", idx, idx) for idx in range(s0.shape[1])]
    plot_group(
        plots_dir / "05_reflection_paths.png",
        f0,
        s0,
        s1_eval,
        reflections,
        title=f"{args.channel_id} reflection paths",
        original_label=original_label,
    )
    plot_error_bar(plots_dir / "06_error_summary_by_path.png", rows)
    transient_overlays = copy_transient_overlays(study_dir, args.channel_id, out_dir)

    write_readme(
        out_dir,
        args.channel_id,
        original_copy or original_path,
        fitted_copy or fitted_path,
        circuit_copy,
        wrapper_copy,
        meta0,
        meta1,
        rows,
        ranking,
        transient_overlays,
    )
    print(f"OUT_DIR={out_dir}")
    print(f"README={out_dir / 'README.md'}")
    print(f"PLOTS={plots_dir}")


if __name__ == "__main__":
    main()
