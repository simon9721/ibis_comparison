# Three-Buffer Fast-Edge Results Package

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

This package contains 28 detailed case figures and 28
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
