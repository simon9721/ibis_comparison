from __future__ import annotations

import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "results" / "three_buffer_realistic_pulse_2026-07-30"
PACKAGE = STUDY / "fast_edge_results_package"
PROFILE = "fast_5ps"
DEVICES = ("io_buf", "inv_chain", "ex2")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def copy_file(source: Path, destination: Path) -> None:
    ensure_dir(destination.parent)
    shutil.copy2(source, destination)


def filter_profile(path: Path) -> list[dict[str, str]]:
    return [row for row in read_csv(path) if row.get("profile") == PROFILE]


def remove_profile_column(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{key: value for key, value in row.items() if key != "profile"} for row in rows]


def relative(path: Path) -> str:
    return path.relative_to(PACKAGE).as_posix()


def build_package() -> None:
    ensure_dir(PACKAGE)
    for stale in (
        PACKAGE / "plots" / "01_io_buf_fast_edge_overview.png",
        PACKAGE / "plots" / "02_inv_chain_fast_edge_overview.png",
        PACKAGE / "plots" / "03_ex2_fast_edge_overview.png",
        PACKAGE / "tables" / "metrics_fast_5ps.csv",
        PACKAGE / "tables" / "summary_by_device_fast_5ps.csv",
        PACKAGE / "tables" / "partial_short_high_summary_fast_5ps.csv",
        PACKAGE / "tables" / "numeric_failures_fast_5ps.csv",
        PACKAGE / "tables" / "reference_cache_manifest_fast_5ps.csv",
    ):
        if stale.exists():
            stale.unlink()
    manifest: list[dict[str, str]] = []

    selection_source = STUDY / "plots" / "00_transistor_pulse_selection.png"
    selection_target = PACKAGE / "plots" / "00_transistor_pulse_selection.png"
    copy_file(selection_source, selection_target)
    manifest.append(
        {
            "kind": "experiment_design_plot",
            "device": "all",
            "edge": "all",
            "case": "pulse_width_selection",
            "package_path": relative(selection_target),
            "source_path": str(selection_source.relative_to(ROOT)),
        }
    )

    figure_count = 0
    data_count = 0
    for device_index, device in enumerate(DEVICES, start=1):
        source_root = STUDY / "selected_runs" / device
        overview_source = source_root / PROFILE / "contact_sheet.png"
        overview_target = PACKAGE / "plots" / f"0{device_index}_{device}_overview.png"
        copy_file(overview_source, overview_target)
        manifest.append(
            {
                "kind": "device_overview_plot",
                "device": device,
                "edge": "all",
                "case": "all_fast_edge_cases",
                "package_path": relative(overview_target),
                "source_path": str(overview_source.relative_to(ROOT)),
            }
        )

        for waveform in sorted(source_root.glob(f"edge_*/{PROFILE}/waveform_data/*.csv")):
            edge = waveform.parents[2].name
            case = waveform.stem
            source_plot = waveform.parents[1] / "plots" / f"{case}.png"
            if not source_plot.exists():
                raise FileNotFoundError(source_plot)

            plot_target = PACKAGE / "plots" / "cases" / device / edge / source_plot.name
            data_target = PACKAGE / "data" / device / edge / waveform.name
            copy_file(source_plot, plot_target)
            copy_file(waveform, data_target)
            figure_count += 1
            data_count += 1
            manifest.extend(
                [
                    {
                        "kind": "case_plot",
                        "device": device,
                        "edge": edge,
                        "case": case,
                        "package_path": relative(plot_target),
                        "source_path": str(source_plot.relative_to(ROOT)),
                    },
                    {
                        "kind": "waveform_data",
                        "device": device,
                        "edge": edge,
                        "case": case,
                        "package_path": relative(data_target),
                        "source_path": str(waveform.relative_to(ROOT)),
                    },
                ]
            )

    fast_metrics = filter_profile(STUDY / "metrics.csv")
    native_ranges = [
        {
            "device": row["device"],
            "edge_ps": row["edge_ps"],
            "target_label": row["target_label"],
            "case_id": row["case_id"],
            "pulse_width_ps": row["pulse_width_ps"],
            "ku_min": row["native_ku_min"],
            "ku_max": row["native_ku_max"],
            "kd_min": row["native_kd_min"],
            "kd_max": row["native_kd_max"],
            "outside_nominal_coefficient_range": row["native_reference_extended_range"],
        }
        for row in fast_metrics
        if row["flow"] == "hspice_transistor"
    ]
    table_specs = (
        ("metrics.csv", remove_profile_column(fast_metrics)),
        (
            "summary_by_device.csv",
            remove_profile_column(filter_profile(STUDY / "summary_by_device_profile.csv")),
        ),
        (
            "partial_short_high_summary.csv",
            remove_profile_column(filter_profile(STUDY / "partial_short_high_summary.csv")),
        ),
        (
            "numeric_failures.csv",
            remove_profile_column(filter_profile(STUDY / "numeric_failures.csv")),
        ),
        (
            "reference_cache_manifest.csv",
            remove_profile_column(
                [
                    row
                    for row in read_csv(STUDY / "reference_cache_manifest.csv")
                    if row.get("profile") in {"", PROFILE}
                ]
            ),
        ),
        ("native_ibis_coefficient_ranges.csv", native_ranges),
        ("selected_realistic_cases.csv", read_csv(STUDY / "selected_realistic_cases.csv")),
        (
            "normal_transition_characterization.csv",
            read_csv(STUDY / "normal_transition_characterization.csv"),
        ),
    )
    for name, rows in table_specs:
        target = PACKAGE / "tables" / name
        write_csv(target, rows)
        manifest.append(
            {
                "kind": "table",
                "device": "all",
                "edge": "all",
                "case": name.removesuffix(".csv"),
                "package_path": relative(target),
                "source_path": "",
            }
        )

    write_csv(PACKAGE / "manifest.csv", manifest)
    readme = f"""# Three-Buffer Fast-Edge Results Package

This is the consolidated presentation and data package for the fast-edge IBIS
files in the realistic-pulse study. It was assembled from existing cached
results; no HSPICE or ngspice simulation was rerun.

## Start Here

- `plots/00_transistor_pulse_selection.png`: transistor-only pulse-width
  selection evidence. This explains why each stress pulse was chosen.
- `plots/01_io_buf_overview.png`: all selected `io_buf` cases.
- `plots/02_inv_chain_overview.png`: all selected `inv_chain` cases.
- `plots/03_ex2_overview.png`: all selected `ex2` cases.

## Detailed Results

- `plots/cases/<device>/<edge>/`: one four-panel figure per selected case.
- `data/<device>/<edge>/`: exact CSV data behind every case figure.
- `tables/metrics.csv`: all model metrics in this package.
- `tables/summary_by_device.csv`: compact device/edge/flow summary.
- `tables/partial_short_high_summary.csv`: pad-partial short-high summary.
- `tables/numeric_failures.csv`: explicit failed runs.
- `tables/native_ibis_coefficient_ranges.csv`: native HSPICE IBIS `Ku/Kd`
  extrema for every selected case.
- `tables/selected_realistic_cases.csv`: pulse-width selection and transistor
  internal-control evidence.
- `manifest.csv`: package-to-source provenance for every copied result.

## Figure Conventions

- Panel 1: loaded pad voltage.
- Panel 2: native-IBIS and candidate `Ku`.
- Panel 3: native-IBIS and candidate `Kd`.
- Panel 4: external input and HSPICE transistor final-stage controls.

The fourth-panel transistor controls are plotted as `1 - V(gate)/VDD`, so an
external rising input and its delayed final-stage command both appear rising.
This is a display-only polarity normalization. The CSV files retain the actual
HSPICE transistor gate voltages.

## Scope

This package contains {figure_count} detailed case figures and {data_count}
matching waveform CSVs. Slow-profile results remain in the parent study for
provenance but are intentionally excluded here.

## How Edge And Pulse Values Were Chosen

- Runtime edges are 100 ps and 250 ps. For the 0.18 um-class transistor
  libraries, 100 ps is the aggressive practical stress and 250 ps is the
  moderate case. A separate 50 ps edge was used only during normal-transition
  characterization, not as a selected short-pulse comparison edge.
- Pulse width is measured between the input's rising and falling 50% crossings.
  Every pulse is full swing; reducing the width does not reduce its amplitude.
- HSPICE transistor-only sweeps were run first into 50 ohm in parallel with
  2 pF. Loaded-pad movement was normalized to the complete normal-transition
  swing. The closest tested widths to 20%, 55%, and 85% movement became the
  visible, mid-transition, and near-settled cases.
- The width selection is therefore based on transistor response, not chosen to
  make either IBIS or pybis look favorable.

## Native-IBIS Coefficient Evidence

- `io_buf` has the least well-conditioned fast-edge coefficients. Complete
  transitions reach roughly Ku=-0.7..2.4 and Kd=-0.61..1.18, far outside the
  intuitive 0..1 range. Its coefficient and numerical failures must not be
  interpreted as ordinary short-pulse behavior.
- `inv_chain` stays near the expected coefficient range, approximately
  -0.08..1.03. However, even 102-125 ps short-high commands produce nearly
  complete native-IBIS Ku/Kd excursions after the external input has reversed.
  The native IBIS response therefore does not reproduce the transistor's
  internal pulse rejection in these cases.
- `ex2` is intermediate: its coefficients overshoot moderately, around
  Ku=-0.39..1.26 and Kd=-0.26..1.11, and short-high cases also reach almost
  complete coefficient excursions. Its transistor pad remains substantially
  smaller, showing another separation between IBIS table playback and circuit
  propagation.
- Across devices, 100 ps versus 250 ps input slew changes the coefficient
  envelopes much less than changing the buffer. Device structure and the
  generated IBIS waveform tables dominate the observed behavior.
- The central lesson is that native HSPICE Ku/Kd are the reference for IBIS
  playback agreement, but not automatically transistor truth. Panel 4 and the
  transistor pad must remain separate checks.
"""
    (PACKAGE / "README.md").write_text(readme, encoding="ascii")


if __name__ == "__main__":
    build_package()
