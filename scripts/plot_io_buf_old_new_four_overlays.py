from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
import run_hspice_rsf_io_buf_inv_chain as rsf  # noqa: E402


OUT_DIR = ROOT / "results" / "io_buf_old_new_four_overlays_2026-06-05"
OLD_NG_DIR = ROOT / "clean_ibis_vs_pybis_matched_pkg"
OLD_HSPICE_DIR = ROOT / "results" / "hspice_rsf_io_buf_inv_chain_2026-06-04" / "io_buf" / "benches"
NEW_DIR = ROOT / "results" / "io_buf_fast_edge_retest_2026-06-05"
NEW_NG_DIR = NEW_DIR / "ngspice" / "benches"
NEW_HSPICE_DIR = NEW_DIR / "hspice" / "benches"


@dataclass(frozen=True)
class OverlayCase:
    key: str
    title: str
    simulator: str
    model_label: str
    reference_label: str
    model_path: Path
    reference_path: Path
    model_signal: str
    reference_signal: str
    ibis_path: Path
    colors: tuple[str, str]


def read_waveform(path: Path, simulator: str, signal: str) -> tuple[np.ndarray, np.ndarray]:
    if simulator == "ngspice":
        data = parse_ngspice_raw(path)
    elif simulator == "hspice":
        data = parse_hspice_tr0(path)
    else:
        raise ValueError(simulator)
    return rsf.resolve(data, "time"), rsf.resolve(data, signal)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def threshold_from_ibis(ibis_path: Path) -> float:
    waveforms = rsf.parse_ibis_waveforms(ibis_path)
    rise = rsf.choose_waveform(waveforms, "Rising")
    return 0.5 * (float(rise.v_typ[0]) + float(rise.v_typ[-1]))


def metrics_for_case(
    case: OverlayCase,
    model_t: np.ndarray,
    model_y: np.ndarray,
    ref_t: np.ndarray,
    ref_y: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    rise_start = 1.0e-9
    fall_start = 9.0e-9
    stop = min(float(model_t[-1]), float(ref_t[-1]), 12.0e-9)
    model_rise = rsf.crossing_time(model_t, model_y, threshold, rise_start, fall_start, True)
    ref_rise = rsf.crossing_time(ref_t, ref_y, threshold, rise_start, fall_start, True)
    model_fall = rsf.crossing_time(model_t, model_y, threshold, fall_start, stop, False)
    ref_fall = rsf.crossing_time(ref_t, ref_y, threshold, fall_start, stop, False)
    rmse, maxabs = rsf.rmse_on_common_grid(ref_t, ref_y, model_t, model_y, 0.0, stop)
    return {
        "figure": case.key,
        "threshold_v": threshold,
        "model_rise_50_ns": rsf.ns(model_rise) if model_rise is not None else "",
        "reference_rise_50_ns": rsf.ns(ref_rise) if ref_rise is not None else "",
        "model_minus_reference_rise_50_ps": rsf.ps(model_rise - ref_rise)
        if model_rise is not None and ref_rise is not None
        else "",
        "model_fall_50_ns": rsf.ns(model_fall) if model_fall is not None else "",
        "reference_fall_50_ns": rsf.ns(ref_fall) if ref_fall is not None else "",
        "model_minus_reference_fall_50_ps": rsf.ps(model_fall - ref_fall)
        if model_fall is not None and ref_fall is not None
        else "",
        "rmse_mv": rmse * 1e3,
        "maxabs_mv": maxabs * 1e3,
    }


def plot_case(case: OverlayCase) -> dict[str, object]:
    model_t, model_y = read_waveform(case.model_path, case.simulator, case.model_signal)
    ref_t, ref_y = read_waveform(case.reference_path, case.simulator, case.reference_signal)
    threshold = threshold_from_ibis(case.ibis_path)
    metric = metrics_for_case(case, model_t, model_y, ref_t, ref_y, threshold)

    windows = [
        ("full rise then fall", 0.0, 12.0),
        ("rise detail", 1.8, 4.8),
        ("fall detail", 8.9, 11.1),
    ]
    y_min = min(float(np.nanmin(model_y)), float(np.nanmin(ref_y)), 0.0) - 0.12
    y_max = max(float(np.nanmax(model_y)), float(np.nanmax(ref_y)), threshold) + 0.15
    y_max = min(max(y_max, 1.8), 2.2)

    fig, axes = plt.subplots(3, 1, figsize=(12.5, 9.0), sharey=False)
    model_color, ref_color = case.colors
    for ax, (label, start_ns, end_ns) in zip(axes, windows):
        ax.plot(rsf.ns(model_t), model_y, label=case.model_label, color=model_color, linewidth=2.0)
        ax.plot(rsf.ns(ref_t), ref_y, label=case.reference_label, color=ref_color, linewidth=2.0, linestyle="--")
        ax.axhline(threshold, color="0.25", linewidth=0.8, linestyle=":", label="50% threshold" if label == windows[0][0] else None)
        ax.axvline(1.0, color="0.45", linewidth=0.8, linestyle=":")
        ax.axvline(9.0, color="0.45", linewidth=0.8, linestyle=":")
        ax.set_xlim(start_ns, end_ns)
        ax.set_ylim(y_min, y_max)
        ax.set_title(label)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Pad voltage (V)")
        ax.grid(True, alpha=0.25)

    delta_rise = float(metric["model_minus_reference_rise_50_ps"])
    delta_fall = float(metric["model_minus_reference_fall_50_ps"])
    rmse = float(metric["rmse_mv"])
    fig.suptitle(case.title, y=0.99, fontsize=15)
    fig.text(
        0.5,
        0.935,
        f"50% delta, model - reference: rise {delta_rise:+.1f} ps, fall {delta_fall:+.1f} ps; RMSE {rmse:.1f} mV",
        ha="center",
        va="center",
        fontsize=10.5,
    )
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.915), ncol=3, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    output = OUT_DIR / f"{case.key}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)

    metric["path"] = str(output.relative_to(ROOT)).replace("\\", "/")
    return metric


def main() -> int:
    cases = [
        OverlayCase(
            key="01_ngspice_old_slow_io_buf_pybis_vs_refspice",
            title="ngspice: old slow io_buf.ibs pybis vs refspice io_buf.sp",
            simulator="ngspice",
            model_label="ngspice pybis from old slow io_buf.ibs",
            reference_label="ngspice refspice io_buf.sp",
            model_path=OLD_NG_DIR / "tb_ibis_vs_pybis_rsf_12n_batch.raw",
            reference_path=OLD_NG_DIR / "tb_refspice_rsf_14n_batch.raw",
            model_signal="v(pad)",
            reference_signal="v(pad_ref)",
            ibis_path=OLD_NG_DIR / "io_buf.ibs",
            colors=("#2ca02c", "#9467bd"),
        ),
        OverlayCase(
            key="02_hspice_old_slow_io_buf_ibis_vs_spice",
            title="HSPICE: old slow io_buf.ibs native IBIS vs io_buf.sp",
            simulator="hspice",
            model_label="HSPICE native IBIS from old slow io_buf.ibs",
            reference_label="HSPICE SPICE subckt io_buf.sp",
            model_path=OLD_HSPICE_DIR / "io_buf_native_ibis.tr0",
            reference_path=OLD_HSPICE_DIR / "io_buf_spice_subckt.tr0",
            model_signal="v(pad_ibis)",
            reference_signal="v(pad_ref)",
            ibis_path=OLD_HSPICE_DIR / "io_buf.ibs",
            colors=("#1f77b4", "#d62728"),
        ),
        OverlayCase(
            key="03_ngspice_new_fast_io_buf_pybis_vs_refspice",
            title="ngspice: new fast-edge io_buf.ibs pybis vs refspice io_buf.sp",
            simulator="ngspice",
            model_label="ngspice pybis from new fast-edge io_buf.ibs",
            reference_label="ngspice refspice io_buf.sp",
            model_path=NEW_NG_DIR / "tb_ibis_vs_pybis_rsf_12n_batch.raw",
            reference_path=NEW_NG_DIR / "tb_refspice_rsf_14n_batch.raw",
            model_signal="v(pad)",
            reference_signal="v(pad_ref)",
            ibis_path=NEW_NG_DIR / "io_buf.ibs",
            colors=("#2ca02c", "#9467bd"),
        ),
        OverlayCase(
            key="04_hspice_new_fast_io_buf_ibis_vs_spice",
            title="HSPICE: new fast-edge io_buf.ibs native IBIS vs io_buf.sp",
            simulator="hspice",
            model_label="HSPICE native IBIS from new fast-edge io_buf.ibs",
            reference_label="HSPICE SPICE subckt io_buf.sp",
            model_path=NEW_HSPICE_DIR / "io_buf_fast_native_ibis.tr0",
            reference_path=NEW_HSPICE_DIR / "io_buf_fast_spice_subckt.tr0",
            model_signal="v(pad_ibis)",
            reference_signal="v(pad_ref)",
            ibis_path=NEW_HSPICE_DIR / "io_buf.ibs",
            colors=("#1f77b4", "#d62728"),
        ),
    ]

    rows = [plot_case(case) for case in cases]
    write_csv(OUT_DIR / "figure_metrics.csv", rows)
    readme_lines = [
        "# io_buf Old/New Overlay Figures",
        "",
        "Four presentation figures comparing the old slow `io_buf.ibs` and regenerated fast-edge `io_buf.ibs`.",
        "Each figure shows the pad waveform over the full rise-then-fall interval plus rise/fall detail panels.",
        "",
        "| Figure | Rise delta | Fall delta | RMSE |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        readme_lines.append(
            f"| `{row['path']}` | {float(row['model_minus_reference_rise_50_ps']):+.1f} ps | "
            f"{float(row['model_minus_reference_fall_50_ps']):+.1f} ps | {float(row['rmse_mv']):.1f} mV |"
        )
    readme_lines.append("")
    (OUT_DIR / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    for row in rows:
        print(f"{row['path']}: rise {float(row['model_minus_reference_rise_50_ps']):+.1f} ps, "
              f"fall {float(row['model_minus_reference_fall_50_ps']):+.1f} ps, "
              f"RMSE {float(row['rmse_mv']):.1f} mV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
