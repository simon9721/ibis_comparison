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
NEW_DIR = ROOT / "results" / "io_buf_fast_edge_retest_2026-06-05"
NG_DIR = NEW_DIR / "ngspice" / "benches"
HSPICE_DIR = NEW_DIR / "hspice" / "benches"


@dataclass(frozen=True)
class Trace:
    key: str
    label: str
    simulator: str
    path: Path
    signal: str
    color: str
    linestyle: str
    linewidth: float = 2.0


def parse_trace(trace: Trace) -> tuple[np.ndarray, np.ndarray]:
    if trace.simulator == "ngspice":
        data = parse_ngspice_raw(trace.path)
    elif trace.simulator == "hspice":
        data = parse_hspice_tr0(trace.path)
    else:
        raise ValueError(trace.simulator)
    return rsf.resolve(data, "time"), rsf.resolve(data, trace.signal)


def threshold_from_new_ibis() -> float:
    waveforms = rsf.parse_ibis_waveforms(NG_DIR / "io_buf.ibs")
    rise = rsf.choose_waveform(waveforms, "Rising")
    return 0.5 * (float(rise.v_typ[0]) + float(rise.v_typ[-1]))


def crossing_rows(traces: list[Trace], parsed: dict[str, tuple[np.ndarray, np.ndarray]], threshold: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for trace in traces:
        time_s, values = parsed[trace.key]
        rise = rsf.crossing_time(time_s, values, threshold, 1.0e-9, 9.0e-9, True)
        fall = rsf.crossing_time(time_s, values, threshold, 9.0e-9, min(float(time_s[-1]), 12.0e-9), False)
        rows.append(
            {
                "trace": trace.key,
                "label": trace.label,
                "threshold_v": threshold,
                "rise_50_ns": rsf.ns(rise) if rise is not None else "",
                "fall_50_ns": rsf.ns(fall) if fall is not None else "",
            }
        )
    return rows


def pair_metrics(
    model_key: str,
    ref_key: str,
    parsed: dict[str, tuple[np.ndarray, np.ndarray]],
    threshold: float,
) -> dict[str, object]:
    model_t, model_y = parsed[model_key]
    ref_t, ref_y = parsed[ref_key]
    stop = min(float(model_t[-1]), float(ref_t[-1]), 12.0e-9)
    model_rise = rsf.crossing_time(model_t, model_y, threshold, 1.0e-9, 9.0e-9, True)
    ref_rise = rsf.crossing_time(ref_t, ref_y, threshold, 1.0e-9, 9.0e-9, True)
    model_fall = rsf.crossing_time(model_t, model_y, threshold, 9.0e-9, stop, False)
    ref_fall = rsf.crossing_time(ref_t, ref_y, threshold, 9.0e-9, stop, False)
    rmse, maxabs = rsf.rmse_on_common_grid(ref_t, ref_y, model_t, model_y, 0.0, stop)
    return {
        "model": model_key,
        "reference": ref_key,
        "threshold_v": threshold,
        "model_minus_reference_rise_50_ps": rsf.ps(model_rise - ref_rise)
        if model_rise is not None and ref_rise is not None
        else "",
        "model_minus_reference_fall_50_ps": rsf.ps(model_fall - ref_fall)
        if model_fall is not None and ref_fall is not None
        else "",
        "rmse_mv": rmse * 1e3,
        "maxabs_mv": maxabs * 1e3,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_traces(
    traces: list[Trace],
    parsed: dict[str, tuple[np.ndarray, np.ndarray]],
    threshold: float,
    title: str,
    subtitle: str,
    output: Path,
) -> None:
    windows = [
        ("full rise then fall", 0.0, 12.0),
        ("rise detail", 1.8, 4.8),
        ("fall detail", 8.9, 11.1),
    ]

    all_values = [parsed[trace.key][1] for trace in traces]
    y_min = min(float(np.nanmin(values)) for values in all_values + [np.asarray([0.0])]) - 0.12
    y_max = max(float(np.nanmax(values)) for values in all_values + [np.asarray([threshold])]) + 0.15

    fig, axes = plt.subplots(3, 1, figsize=(13.0, 9.2), sharey=False)
    for ax, (window_title, start_ns, end_ns) in zip(axes, windows):
        for trace in traces:
            time_s, values = parsed[trace.key]
            ax.plot(
                rsf.ns(time_s),
                values,
                label=trace.label,
                color=trace.color,
                linestyle=trace.linestyle,
                linewidth=trace.linewidth,
            )
        ax.axhline(threshold, color="0.25", linewidth=0.8, linestyle=":", label="50% threshold" if ax is axes[0] else None)
        ax.axvline(1.0, color="0.45", linewidth=0.8, linestyle=":")
        ax.axvline(9.0, color="0.45", linewidth=0.8, linestyle=":")
        ax.set_xlim(start_ns, end_ns)
        ax.set_ylim(y_min, y_max)
        ax.set_title(window_title)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Pad voltage (V)")
        ax.grid(True, alpha=0.25)

    fig.suptitle(title, y=0.99, fontsize=15)
    fig.text(0.5, 0.935, subtitle, ha="center", va="center", fontsize=10.5)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.915), ncol=3, fontsize=9.0)
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    traces = [
        Trace(
            key="ngspice_pybis",
            label="ngspice pybis from new io_buf.ibs",
            simulator="ngspice",
            path=NG_DIR / "tb_ibis_vs_pybis_rsf_12n_batch.raw",
            signal="v(pad)",
            color="#2ca02c",
            linestyle="-",
        ),
        Trace(
            key="ngspice_refspice",
            label="ngspice refspice io_buf.sp",
            simulator="ngspice",
            path=NG_DIR / "tb_refspice_rsf_14n_batch.raw",
            signal="v(pad_ref)",
            color="#9467bd",
            linestyle="--",
        ),
        Trace(
            key="hspice_native_ibis",
            label="HSPICE native IBIS from new io_buf.ibs",
            simulator="hspice",
            path=HSPICE_DIR / "io_buf_fast_native_ibis.tr0",
            signal="v(pad_ibis)",
            color="#1f77b4",
            linestyle="-",
        ),
        Trace(
            key="hspice_refspice",
            label="HSPICE SPICE subckt io_buf.sp",
            simulator="hspice",
            path=HSPICE_DIR / "io_buf_fast_spice_subckt.tr0",
            signal="v(pad_ref)",
            color="#d62728",
            linestyle="--",
        ),
    ]
    parsed = {trace.key: parse_trace(trace) for trace in traces}
    threshold = threshold_from_new_ibis()

    crossing = crossing_rows(traces, parsed, threshold)
    pair = pair_metrics("ngspice_pybis", "hspice_native_ibis", parsed, threshold)
    write_csv(OUT_DIR / "new_io_buf_combined_crossing_times.csv", crossing)
    write_csv(OUT_DIR / "new_io_buf_pybis_vs_hspice_ibis_metrics.csv", [pair])

    plot_traces(
        traces,
        parsed,
        threshold,
        "new fast-edge io_buf.ibs: ngspice and HSPICE pad overlays",
        "Four curves: ngspice pybis/refspice and HSPICE native-IBIS/SPICE, all at the pad node",
        OUT_DIR / "05_new_io_buf_all_four_ngspice_hspice_overlay.png",
    )

    plot_traces(
        [traces[0], traces[2]],
        parsed,
        threshold,
        "new fast-edge io_buf.ibs: ngspice pybis vs HSPICE native IBIS",
        "50% delta, ngspice pybis - HSPICE native IBIS: "
        f"rise {float(pair['model_minus_reference_rise_50_ps']):+.1f} ps, "
        f"fall {float(pair['model_minus_reference_fall_50_ps']):+.1f} ps; "
        f"RMSE {float(pair['rmse_mv']):.1f} mV",
        OUT_DIR / "06_new_io_buf_ngspice_pybis_vs_hspice_ibis.png",
    )

    readme = OUT_DIR / "README.md"
    existing = readme.read_text(encoding="utf-8") if readme.exists() else "# io_buf Old/New Overlay Figures\n"
    marker = "## Additional New-IBIS Figures"
    addition = f"""

## Additional New-IBIS Figures

- `results/io_buf_old_new_four_overlays_2026-06-05/05_new_io_buf_all_four_ngspice_hspice_overlay.png`: all four new-IBIS pad curves, two from ngspice and two from HSPICE.
- `results/io_buf_old_new_four_overlays_2026-06-05/06_new_io_buf_ngspice_pybis_vs_hspice_ibis.png`: focused ngspice-pybis vs HSPICE-native-IBIS comparison.

For the focused comparison, ngspice pybis minus HSPICE native IBIS is {float(pair['model_minus_reference_rise_50_ps']):+.1f} ps on rise and {float(pair['model_minus_reference_fall_50_ps']):+.1f} ps on fall.
"""
    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip()
    readme.write_text(existing.rstrip() + addition, encoding="utf-8")

    print(OUT_DIR / "05_new_io_buf_all_four_ngspice_hspice_overlay.png")
    print(OUT_DIR / "06_new_io_buf_ngspice_pybis_vs_hspice_ibis.png")
    print(
        "ngspice pybis - HSPICE native IBIS: "
        f"rise {float(pair['model_minus_reference_rise_50_ps']):+.2f} ps, "
        f"fall {float(pair['model_minus_reference_fall_50_ps']):+.2f} ps, "
        f"RMSE {float(pair['rmse_mv']):.2f} mV"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
