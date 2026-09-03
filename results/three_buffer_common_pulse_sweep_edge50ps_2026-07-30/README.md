# Three-Buffer Common-Pulse Sweep

This study uses one common stimulus grid for `io_buf`, `inv_chain`, and `ex2`.
The pulse widths were chosen directly and do not use the adaptive pulse-selection result.

## Fixed Setup

- Fast-edge IBIS files only.
- Runtime rise/fall time: `50 ps` for every device and case.
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
- `plots/06_io_buf_gate_proxy_overview.png`: `io_buf` physical-gate coefficient proxy.
- `plots/07_inv_chain_gate_proxy_overview.png`: `inv_chain` physical-gate coefficient proxy.
- `plots/08_ex2_gate_proxy_overview.png`: `ex2` physical-gate coefficient proxy.
- `plots/09_edge_50ps_vs_100ps_response.png`: input-slew sensitivity, when available.
- `plots/by_pulse_width/`: direct three-buffer comparisons at each common width.

## Data

- `metrics.csv`: candidate errors and validity flags.
- `summary_by_device.csv`: compact device/flow summary.
- `native_ibis_coefficient_ranges.csv`: native HSPICE `Ku/Kd` extrema.
- `response_vs_common_pulse_width.csv`: pad and coefficient trends versus width.
- `transistor_gate_proxy_metrics.csv`: linear physical-gate proxy errors versus native Ku/Kd.
- `edge_50ps_vs_100ps_response.csv`: direct slew sensitivity, when available.
- `run_manifest.csv`: cache/run status and raw-result paths.
- `runs/<device>/waveform_data/`: exact data behind every figure.

## Headline Findings

- `inv_chain` is effectively too fast for this pulse grid to create partial output behavior. At 250 ps, transistor short-high/short-low responses are `100.3%` / `101.5%` of full swing.
- `ex2` has a clear threshold between 500 ps and 1 ns. For short-high, the transistor moves only `0.6%` at 500 ps but `92.7%` at 1 ns.
- Native IBIS overpredicts sub-nanosecond `ex2` response. At 500 ps it predicts `11.4%` short-high and `62.6%` short-low, versus transistor `0.6%` and `2.3%`.
- `io_buf` is strongly direction-asymmetric. At 250 ps, transistor short-high movement is `1.0%`, while short-low movement is `78.7%`.
- Native IBIS underpredicts the fast `io_buf` short-low response: at 250 ps the native result is `26.0%` versus transistor `78.7%`.
- All simulator runs completed, but completion is not validity. `io_buf` candidates retain coefficient discontinuity/envelope failures; `ex2` is strongest at 1-2 ns; and the hybrid often remains inactive for `inv_chain` because its final-stage transition has already settled.

## Interpretation

Using identical stimuli reveals the buffers' effective pulse filtering directly: `inv_chain` is fastest, `ex2` is intermediate, and `io_buf` has separate fast and slow directions. A common pulse cannot guarantee a mid-transition reversal in every buffer; that is a measured device result, not a defect in this study.

## 50 ps Versus 100 ps Input Slew

The transistor responses are nearly unchanged, confirming that both edges primarily measure buffer pulse filtering. The largest transistor response-fraction change is `4.4` percentage points for `io_buf / short_low / 250 ps`.

Native IBIS is more slew-sensitive. Its largest change is `15.8` percentage points for `ex2 / short_high / 500 ps`. This is model behavior rather than a corresponding transistor-level change.

## Transistor Gate-Voltage Proxy

The proxy uses the measured final-stage gate voltage to preserve physical timing:

- `Ku_proxy = 1 - V(PMOS_gate)/VDD`.
- `Kd_proxy = V(NMOS_gate)/VDD`.
- For shared-gate output stages, both proxies come from the same gate voltage.

This is a diagnostic proxy, not a true IBIS coefficient extraction. Gate voltage does not include transistor threshold, nonlinear transconductance, drain-voltage dependence, or parallel-device current sharing. Exact effective Ku/Kd requires probing pullup and pulldown currents separately and normalizing them against the corresponding static IBIS I-V tables at the instantaneous pad voltage.

Measured median proxy RMSE (`Ku`, `Kd`):

- `io_buf`: `0.1528`, `0.0972`.
- `inv_chain`: `0.0239`, `0.0479`.
- `ex2`: `0.1453`, `0.1241`.

The simple proxy is therefore genuinely informative for `inv_chain`, but not accurate enough to replace Ku/Kd for `io_buf` or `ex2`.

Numerical failures: `0`.
