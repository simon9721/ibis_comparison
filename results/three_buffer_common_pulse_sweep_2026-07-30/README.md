# Three-Buffer Common-Pulse Sweep

This study uses one common stimulus grid for `io_buf`, `inv_chain`, and `ex2`.
The pulse widths were chosen directly and do not use the adaptive pulse-selection result.

## Fixed Setup

- Fast-edge IBIS files only.
- Runtime rise/fall time: `100 ps` for every device and case.
- Full-swing pulse widths: `250 ps`, `500 ps`, `1 ns`, and `2 ns`.
- Both short-high and short-low directions.
- Normal long-pulse control.
- Load: `50 ohm || 2 pF`.
- HSPICE transistor and native-IBIS references.
- ngspice gate-state and hybrid candidates.
- Transistor controls shown as `1 - V(gate)/VDD` for rising-command polarity.

## Start Here

- `plots/00_common_input_stimuli.png`: exact common input grid.
- `plots/01_io_buf_overview.png`: all `io_buf` cases.
- `plots/02_inv_chain_overview.png`: all `inv_chain` cases.
- `plots/03_ex2_overview.png`: all `ex2` cases.
- `plots/04_response_vs_common_pulse_width.png`: pad response trends.
- `plots/05_native_kukd_vs_common_pulse_width.png`: native coefficient trends.
- `plots/by_pulse_width/`: direct three-buffer comparisons at each common width.

## Data

- `metrics.csv`: candidate errors and validity flags.
- `summary_by_device.csv`: compact device/flow summary.
- `native_ibis_coefficient_ranges.csv`: native HSPICE `Ku/Kd` extrema.
- `response_vs_common_pulse_width.csv`: pad and coefficient trends versus width.
- `run_manifest.csv`: cache/run status and raw-result paths.
- `runs/<device>/waveform_data/`: exact data behind every figure.

## Headline Findings

- `inv_chain` is effectively too fast for this pulse grid to create partial output behavior. At 250 ps, transistor short-high/short-low responses are `100.3%` / `101.5%` of full swing.
- `ex2` has a clear threshold between 500 ps and 1 ns. For short-high, the transistor moves only `0.6%` at 500 ps but `92.8%` at 1 ns.
- Native IBIS overpredicts sub-nanosecond `ex2` response. At 500 ps it predicts `27.2%` short-high and `55.2%` short-low, versus transistor `0.6%` and `2.1%`.
- `io_buf` is strongly direction-asymmetric. At 250 ps, transistor short-high movement is `0.9%`, while short-low movement is `74.3%`.
- Native IBIS underpredicts the fast `io_buf` short-low response: at 250 ps the native result is `17.2%` versus transistor `74.3%`.
- All simulator runs completed, but completion is not validity. `io_buf` candidates retain coefficient discontinuity/envelope failures; `ex2` is strongest at 1-2 ns; and the hybrid often remains inactive for `inv_chain` because its final-stage transition has already settled.

## Interpretation

Using identical stimuli reveals the buffers' effective pulse filtering directly: `inv_chain` is fastest, `ex2` is intermediate, and `io_buf` has separate fast and slow directions. A common pulse cannot guarantee a mid-transition reversal in every buffer; that is a measured device result, not a defect in this study.

Numerical failures: `0`.
