from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_hspice_rsf_io_buf_inv_chain as hspice_rsf  # noqa: E402


OUT_DIR = ROOT / "results" / "io_buf_fast_edge_retest_2026-06-05"
SOURCE_DIR = OUT_DIR / "source"
HSPICE_DIR = OUT_DIR / "hspice"
BENCH_DIR = HSPICE_DIR / "benches"
PLOT_DIR = HSPICE_DIR / "plots"


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


def make_case() -> hspice_rsf.Case:
    return hspice_rsf.Case(
        key="io_buf",
        title="io_buf regenerated tr/tf=5ps",
        source_dir=SOURCE_DIR,
        ibis_name="io_buf.ibs",
        ibis_model="driver",
        model_type="io",
        supply_v=3.3,
        rise_start_ns=1.0,
        fall_start_ns=9.0,
        edge_ps=5.0,
        high_time_ns=8.0,
        native_stop_ns=12.0,
        spice_stop_ns=14.0,
        pybis_raw_name="__no_ngspice_pybis_for_this_hspice_retest__.raw",
        ref_raw_name="__no_ngspice_ref_for_this_hspice_retest__.raw",
        pybis_pad_signal="v(pad)",
        pybis_load_signal="v(ntst)",
        ref_pad_signal="v(pad_ref)",
        ref_load_signal="v(ntst_ref)",
    )


def prepare_sources() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("io_buf.sp", "hspice_ngspice.mod"):
        shutil.copy2(ROOT / "clean_ibis_vs_pybis_matched_pkg" / name, SOURCE_DIR / name)


def run_hspice_retest() -> list[dict[str, object]]:
    prepare_sources()
    case = make_case()
    hspice_rsf.copy_common_files(case, BENCH_DIR)

    native_deck = BENCH_DIR / "io_buf_fast_native_ibis.sp"
    spice_deck = BENCH_DIR / "io_buf_fast_spice_subckt.sp"
    native_deck.write_text(hspice_rsf.make_native_deck(case), encoding="ascii")
    spice_deck.write_text(hspice_rsf.make_spice_deck(case), encoding="ascii")

    run_rows: list[dict[str, object]] = []
    for kind, deck, prefix in (
        ("native_ibis", native_deck, "io_buf_fast_native_ibis"),
        ("spice_subckt", spice_deck, "io_buf_fast_spice_subckt"),
    ):
        rc, stdout_path = hspice_rsf.run_hspice(deck, prefix)
        run_rows.append(
            {
                "case": "io_buf_fast",
                "kind": kind,
                "return_code": rc,
                "stdout": str(stdout_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
        print(f"{kind}: return_code={rc} stdout={stdout_path}")

    write_csv(HSPICE_DIR / "run_summary.csv", run_rows)
    failed = [row for row in run_rows if row["return_code"] != 0]
    if failed:
        raise RuntimeError(f"HSPICE run failed: {failed}")

    native = hspice_rsf.parse_hspice_tr0(BENCH_DIR / "io_buf_fast_native_ibis.tr0")
    spice = hspice_rsf.parse_hspice_tr0(BENCH_DIR / "io_buf_fast_spice_subckt.tr0")
    waveforms = hspice_rsf.parse_ibis_waveforms(BENCH_DIR / "io_buf.ibs")
    rise_wf = hspice_rsf.choose_waveform(waveforms, "Rising")
    fall_wf = hspice_rsf.choose_waveform(waveforms, "Falling")

    hspice_rsf.plot_case(case, native, spice, rise_wf, fall_wf, PLOT_DIR)
    metric_rows = hspice_rsf.metrics_for_case(case, native, spice, rise_wf, fall_wf)
    for row in metric_rows:
        row["case"] = "io_buf_fast"
    write_csv(HSPICE_DIR / "metrics_summary.csv", metric_rows)
    return metric_rows


def main() -> int:
    if not (SOURCE_DIR / "io_buf.ibs").exists():
        raise FileNotFoundError(SOURCE_DIR / "io_buf.ibs")

    rows = run_hspice_retest()
    for row in rows:
        print(
            "{node}: rise {rise:.2f} ps, fall {fall:.2f} ps, RMSE {rmse:.2f} mV".format(
                node=row["node"],
                rise=float(row["native_minus_spice_rise_50_ps"]),
                fall=float(row["native_minus_spice_fall_50_ps"]),
                rmse=float(row["native_vs_spice_rmse_mv"]),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
