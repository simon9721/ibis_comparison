# Transient And Eye Review Plots

Date: 2026-05-13

This folder contains the clean review plots for two comparison cases:

- `normal_prbs_channel/`: accepted PRBS7 + 50 ohm RLGC channel benchmark
- `stressed_edge50_prbs80_channel/`: corrected stressed edge50 PRBS80/channel case

Each subfolder contains this common plot set, plus case-specific diagnostic
plots listed below:

| File | Meaning |
|---|---|
| `01_ngspice_refspice_individual.png` | ngspice transistor-level `io_buf.sp` receiver transient |
| `02_ngspice_pybis_individual.png` | ngspice pybis receiver transient |
| `03_xyce_refspice_individual.png` | Xyce transistor-level `io_buf.sp` receiver transient |
| `04_xyce_pybis_individual.png` | Xyce pybis receiver transient |
| `05_ngspice_refspice_vs_pybis.png` | ngspice refspice vs pybis transient overlay |
| `06_xyce_refspice_vs_pybis.png` | Xyce refspice vs pybis transient overlay |
| `07_all_refspice_pybis_overlay.png` | all four transient traces together |
| `08_eye_ngspice_refspice.png` | ngspice refspice physical eye |
| `09_eye_ngspice_pybis.png` | ngspice pybis physical eye |
| `10_eye_xyce_refspice.png` | Xyce refspice physical eye |
| `11_eye_xyce_pybis.png` | Xyce pybis physical eye |
| `12_ngspice_pybis_kukd.png` | ngspice pybis `Ku/Kd` diagnostic with `V(n10b)` context |
| `13_xyce_pybis_kukd.png` | Xyce pybis `Ku/Kd` diagnostic with `V(n10b)` context |
| `14_ngspice_xyce_pybis_kukd_overlay.png` | ngspice vs Xyce pybis `Ku/Kd` and `V(n10b)` overlay |
| `kukd_metrics.csv` | `Ku/Kd` min/max/mean summary for full and zoom windows |

The eye diagrams use clock/UI-grid folding.  They do not use per-edge alignment
or rise/fall phase compensation.

The `Ku/Kd` diagnostic plots show the pybis behavioral pull-up/pull-down
coefficients.  Each individual plot includes `V(n10b)` in the upper row and
`Ku/Kd` in the lower row, with a full-window view and a zoom-window view.  The
overlay plot compares ngspice pybis against Xyce pybis for `V(n10b)`, `Ku`, and
`Kd`.

## Normal PRBS + Channel Case

Configuration:

- Stimulus: PRBS7
- Bit count: 200 bits
- UI: 5 ns
- Stop time: 1000 ns
- Input transition: 200 ps
- Channel: accepted 50 ohm 10-section RLGC channel
- Source files:
  - `ngspice_refspice/tb_refspice_prbs7_new50ohm_batch.raw`
  - `results/prbs_rlgc_clean_2026-05-10/ngspice/tb_clean_prbs_rlgc_ngspice.raw`
  - `xyce_refspice/tb_refspice_prbs7_new50ohm_xyce.cir.csv`
  - `results/prbs_rlgc_clean_2026-05-10/xyce/tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir.csv`

Observation:

The normal-case eyes have highly aligned rising and falling edge families.  The
case is deterministic, relatively gentle, and already covers more than one full
PRBS7 sequence period.  Increasing the bit count alone should mostly increase
plot density rather than fundamentally changing the eye shape.

`Ku/Kd` diagnostic note:

The original ngspice review RAW only saved external waveform nodes.  For the
normal-case `Ku/Kd` plots, ngspice was rerun from the same pybis/channel setup
with `V(xdrv.ku)`, `V(xdrv.kd)`, and `V(xdrv.nx)` added to `.save`.  The accepted
normal ngspice RAW predates later edits to `ngspice_pybis/driver_OutputInput_Typical.sub`,
so the diagnostic rerun intentionally uses the preserved matching model snapshot:
`results/ngspice_kukd_ab_context38_2026-05-11/driver_OutputInput_Typical_pre_kukd_3e0bf44.sub`.
To keep the internal-node diagnostic practical, this rerun covers `0-80 ns`;
the plotted review window remains `0-75 ns` and the zoom panel uses `50-70 ns`.
The Xyce plot uses the existing 1000 ns CSV but is plotted on the same review
window.

Additional normal-case source-edge files:

| File | Meaning |
|---|---|
| `15_normal_source_edge_response_map.png` | explicit source-side map: input edge, sustained pybis coefficient response, pybis `tx_out`, and refspice `tx_out` |
| `normal_source_edge_response_map_metrics.csv` | timestamps used by the normal source-side edge-response map |

The normal source-edge map shows aligned behavior between ngspice and Xyce:
input rises at `35.10 ns` and `70.10 ns` drive sustained `Ku` around
`38.76-38.78 ns` and `73.78 ns`; the input fall at `65.10 ns` drives sustained
`Kd` around `68.02-68.03 ns`.  The pybis source voltage stays in the same range
as refspice, unlike the stressed source pulse.  The first Xyce input crossing
has a one-sample `Ku` blip; the metrics use sustained crossings so that blip is
not counted as the real coefficient response.

## Stressed Edge50 PRBS80/Channel Case

Configuration:

- Stimulus: PRBS7-80
- Bit count: 80 bits
- UI: 2 ns
- Stop time: 160 ns
- Input transition: 200 ps
- Channel: 30 cm coarse10 RLGC, loss scale x5
- Source bundle:
  - `results/stressed_edge50_corrected_crossflow_2026-05-12_clean/`

Source files:

- `runs/ui2_len30cm_loss5_coarse10/ngspice_refspice/ui2_len30cm_loss5_coarse10_ngspice_refspice.raw`
- `runs/ui2_len30cm_loss5_coarse10/ngspice_pybis_edge50_corrected/ui2_len30cm_loss5_coarse10_ngspice_pybis_edge50_corrected.raw`
- `runs/ui2_len30cm_loss5_coarse10/xyce_refspice/ui2_len30cm_loss5_coarse10_xyce_refspice.cir.csv`
- `runs/ui2_len30cm_loss5_coarse10/xyce_pybis_edge50/ui2_len30cm_loss5_coarse10_xyce_pybis_edge50.cir.csv`

Observation:

The stressed-case eyes show much more edge spread and history-dependent
structure.  This is mainly caused by the shorter UI, harsher channel, and pybis
edge50 behavior.  It is not simply a consequence of having more bits; this case
actually uses fewer bits than the normal benchmark.

`Ku/Kd` diagnostic note:

The stressed-case `Ku/Kd` zoom is `55.5-58.8 ns`, with the marker placed at
`56.69 ns`, the measured pybis receiver spike peak region from the pybis/refspice
comparison.  As with the normal case, the ngspice pybis run was regenerated only
to add the internal `Ku/Kd/NX` saved nodes; the circuit setup and model are the
same corrected edge50/tailflat4p2 setup used for the transient review.

Additional stressed-case spike-history files:

| File | Meaning |
|---|---|
| `15_stressed_spike_leadin_kukd_history.png` | focused lead-in plot showing input, transmitter pad, receiver output, `Ku`, `Kd`, and `NX` from `53.6-58.9 ns` |
| `16_stressed_spike_chain_kukd_top_transient_bottom.png` | simplified chain-of-event plot with `Ku/Kd` on top and transient waveforms below |
| `17_stressed_pybis_tx_vs_kukd_no_channel.png` | minimal source-side plot: pybis `Ku/Kd` vs `tx_out` before the RLGC channel |
| `18_stressed_pybis_tx_kukd_source_context.png` | wider source-side context plot showing the prior rise, problematic fall/source pulse, and next rise |
| `19_stressed_source_edge_response_map.png` | explicit edge-response map: input edge, pybis coefficient response, pybis `tx_out`, and refspice `tx_out` |
| `spike_leadin_metrics.csv` | peak/crossing metrics for the stressed pybis spike lead-in |
| `source_edge_response_map_metrics.csv` | timestamps used by the source-side edge-response map |

This focused plot shows that the large receiver spike near `56.69 ns` is not
caused by a same-time `Ku` turn-on.  At the receiver spike peak, both pybis
flows still have `Ku` near zero and `Kd` near one.  The spike tracks back to a
large pybis transmitter-side pad launch around `54.24 ns`, immediately after
the prior falling input edge, followed by roughly `2.45 ns` of channel delay.

## Tooling

Transient plots were generated with:

- `scripts/transient_plot.py`

`Ku/Kd` diagnostic plots were generated with:

- `scripts/plot_review_kukd.py`

Eye diagrams were generated with:

- `scripts/eye_diagram.py`

The eye tool was updated during this work to support:

- exact eye PNG output path via `--eye-out`
- clean eye-only review output via `--no-transitions --no-metrics`
- brighter overlay traces with adaptive opacity
