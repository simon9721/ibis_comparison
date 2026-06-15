from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import shutil
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from convert_ibis_to_pybis import convert  # noqa: E402
from eye_diagram import parse_ngspice_raw  # noqa: E402
import run_hspice_rsf_io_buf_inv_chain as hspice_rsf  # noqa: E402


DEFAULT_NGSPICE = Path(
    r"\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin\ngspice.exe"
)
OUT_DIR = ROOT / "results" / "io_buf_fast_edge_retest_2026-06-05"
SOURCE_DIR = OUT_DIR / "source"
NGSPICE_DIR = OUT_DIR / "ngspice"
BENCH_DIR = NGSPICE_DIR / "benches"
PLOT_DIR = NGSPICE_DIR / "plots"


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


def prepare_benches() -> None:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    for name in (
        "tb_ibis_vs_pybis_rsf_12n_batch.sp",
        "tb_refspice_rsf_14n_batch.sp",
        "io_buf.sp",
        "hspice_ngspice.mod",
    ):
        shutil.copy2(ROOT / "clean_ibis_vs_pybis_matched_pkg" / name, BENCH_DIR / name)
    shutil.copy2(SOURCE_DIR / "io_buf.ibs", BENCH_DIR / "io_buf.ibs")

    convert(
        ibis_path=SOURCE_DIR / "io_buf.ibs",
        output_path=BENCH_DIR / "driver_OutputInput_Typical.sub",
        component_name="MCM Driver 1",
        model_name="driver",
        io_type="Output",
        subcircuit_type="InputDriven",
        corner="Typical",
    )

    # Second conversion check for the companion buffer used in this study.
    convert(
        ibis_path=ROOT / "inv_chain" / "clean_ibis_vs_pybis_matched_pkg" / "t2b_0615_v5.ibs",
        output_path=NGSPICE_DIR / "driver2_OutputInput_Typical.sub",
        component_name="invchain",
        model_name="driver2",
        io_type="Output",
        subcircuit_type="InputDriven",
        corner="Typical",
    )


def run_ngspice(ngspice: Path, deck: Path, raw_name: str) -> dict[str, object]:
    raw = deck.parent / raw_name
    log = deck.with_suffix(".log")
    cmd = [str(ngspice), "-b", "-r", raw.name, deck.name]
    completed = subprocess.run(
        cmd,
        cwd=deck.parent,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    log.write_text(
        "COMMAND: " + " ".join(cmd) + "\n"
        f"RETURN_CODE: {completed.returncode}\n\n"
        "STDOUT:\n" + completed.stdout + "\n\n"
        "STDERR:\n" + completed.stderr,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "deck": str(deck.relative_to(ROOT)).replace("\\", "/"),
        "raw": str(raw.relative_to(ROOT)).replace("\\", "/"),
        "log": str(log.relative_to(ROOT)).replace("\\", "/"),
        "return_code": completed.returncode,
    }


def resolve(data: dict[str, np.ndarray], signal: str) -> np.ndarray:
    return hspice_rsf.resolve(data, signal)


def make_metrics(pybis_raw: Path, ref_raw: Path) -> list[dict[str, object]]:
    pybis = parse_ngspice_raw(pybis_raw)
    ref = parse_ngspice_raw(ref_raw)
    waveforms = hspice_rsf.parse_ibis_waveforms(SOURCE_DIR / "io_buf.ibs")
    rise_wf = hspice_rsf.choose_waveform(waveforms, "Rising")

    low = float(rise_wf.v_typ[0])
    high = float(rise_wf.v_typ[-1])
    threshold = 0.5 * (low + high)
    rise_start = 1e-9
    fall_start = 9e-9
    t_pybis = resolve(pybis, "time")
    t_ref = resolve(ref, "time")
    t_max = min(float(t_pybis[-1]), float(t_ref[-1]), 12e-9)

    rows: list[dict[str, object]] = []
    for node, pybis_signal, ref_signal in (
        ("pad", "v(pad)", "v(pad_ref)"),
        ("load", "v(ntst)", "v(ntst_ref)"),
    ):
        y_pybis = resolve(pybis, pybis_signal)
        y_ref = resolve(ref, ref_signal)
        pybis_rise = hspice_rsf.crossing_time(t_pybis, y_pybis, threshold, rise_start, fall_start, True)
        ref_rise = hspice_rsf.crossing_time(t_ref, y_ref, threshold, rise_start, fall_start, True)
        pybis_fall = hspice_rsf.crossing_time(t_pybis, y_pybis, threshold, fall_start, t_max, False)
        ref_fall = hspice_rsf.crossing_time(t_ref, y_ref, threshold, fall_start, t_max, False)
        rmse, maxabs = hspice_rsf.rmse_on_common_grid(t_ref, y_ref, t_pybis, y_pybis, 0.0, t_max)
        rows.append(
            {
                "case": "io_buf_fast",
                "node": node,
                "threshold_v": threshold,
                "pybis_rise_50_ns": hspice_rsf.ns(pybis_rise) if pybis_rise is not None else "",
                "refspice_rise_50_ns": hspice_rsf.ns(ref_rise) if ref_rise is not None else "",
                "pybis_minus_refspice_rise_50_ps": hspice_rsf.ps(pybis_rise - ref_rise)
                if pybis_rise is not None and ref_rise is not None
                else "",
                "pybis_fall_50_ns": hspice_rsf.ns(pybis_fall) if pybis_fall is not None else "",
                "refspice_fall_50_ns": hspice_rsf.ns(ref_fall) if ref_fall is not None else "",
                "pybis_minus_refspice_fall_50_ps": hspice_rsf.ps(pybis_fall - ref_fall)
                if pybis_fall is not None and ref_fall is not None
                else "",
                "pybis_vs_refspice_rmse_mv": rmse * 1e3,
                "pybis_vs_refspice_maxabs_mv": maxabs * 1e3,
                "pybis_stop_ns": hspice_rsf.ns(t_pybis[-1]),
                "refspice_stop_ns": hspice_rsf.ns(t_ref[-1]),
            }
        )
    return rows


def plot_node(
    pybis: dict[str, np.ndarray],
    ref: dict[str, np.ndarray],
    pybis_signal: str,
    ref_signal: str,
    ylabel: str,
    path: Path,
) -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    t_pybis = resolve(pybis, "time")
    t_ref = resolve(ref, "time")
    y_pybis = resolve(pybis, pybis_signal)
    y_ref = resolve(ref, ref_signal)
    y_input = resolve(pybis, "v(in_dig)")
    windows = [
        ("full", 0.0, 12.0),
        ("rise zoom", 0.9, 4.8),
        ("fall zoom", 8.9, 11.2),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharey=False)
    for ax, (title, start_ns, end_ns) in zip(axes, windows):
        ax.plot(hspice_rsf.ns(t_pybis), y_pybis, label="ngspice pybis", linewidth=1.8, color="#2ca02c")
        ax.plot(hspice_rsf.ns(t_ref), y_ref, label="ngspice refspice", linewidth=1.8, color="#9467bd", linestyle="--")
        ax.plot(hspice_rsf.ns(t_pybis), y_input, label="input", linewidth=0.9, color="0.45", alpha=0.65)
        ax.axvline(1.0, color="0.25", linestyle=":", linewidth=0.8)
        ax.axvline(9.0, color="0.25", linestyle=":", linewidth=0.8)
        ax.set_xlim(start_ns, end_ns)
        ax.set_title(title)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.suptitle("io_buf regenerated IBIS: ngspice pybis vs ngspice refspice", y=0.99)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.96), ncol=3, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.89))
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_plots(pybis_raw: Path, ref_raw: Path) -> None:
    pybis = parse_ngspice_raw(pybis_raw)
    ref = parse_ngspice_raw(ref_raw)
    plot_node(
        pybis,
        ref,
        "v(pad)",
        "v(pad_ref)",
        "Pad voltage (V)",
        PLOT_DIR / "io_buf_ngspice_pybis_ref_pad_overlay.png",
    )
    plot_node(
        pybis,
        ref,
        "v(ntst)",
        "v(ntst_ref)",
        "Load voltage (V)",
        PLOT_DIR / "io_buf_ngspice_pybis_ref_load_overlay.png",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify this machine can run ngspice + pybis2spice.")
    parser.add_argument("--ngspice", type=Path, default=Path(os.environ.get("NGSPICE_EXE", DEFAULT_NGSPICE)))
    args = parser.parse_args()

    prepare_benches()
    runs = [
        run_ngspice(args.ngspice, BENCH_DIR / "tb_ibis_vs_pybis_rsf_12n_batch.sp", "tb_ibis_vs_pybis_rsf_12n_batch.raw"),
        run_ngspice(args.ngspice, BENCH_DIR / "tb_refspice_rsf_14n_batch.sp", "tb_refspice_rsf_14n_batch.raw"),
    ]
    write_csv(NGSPICE_DIR / "run_summary.csv", runs)
    failures = [row for row in runs if row["return_code"] != 0]
    if failures:
        raise RuntimeError(f"ngspice run failed: {failures}")

    pybis_raw = BENCH_DIR / "tb_ibis_vs_pybis_rsf_12n_batch.raw"
    ref_raw = BENCH_DIR / "tb_refspice_rsf_14n_batch.raw"
    rows = make_metrics(pybis_raw, ref_raw)
    write_csv(NGSPICE_DIR / "metrics_summary.csv", rows)
    make_plots(pybis_raw, ref_raw)

    for row in rows:
        print(
            "{node}: pybis-ref rise {rise:.2f} ps, fall {fall:.2f} ps, RMSE {rmse:.2f} mV".format(
                node=row["node"],
                rise=float(row["pybis_minus_refspice_rise_50_ps"]),
                fall=float(row["pybis_minus_refspice_fall_50_ps"]),
                rmse=float(row["pybis_vs_refspice_rmse_mv"]),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
