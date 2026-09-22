# Pybis Spike Trend Report

Generated: 2026-05-12

For the clearer standalone behavior taxonomy, see:

- `docs/reports/PYBIS_TWO_BEHAVIORS_2026-05-13.md`

## Purpose

The corrected stressed PRBS comparison showed a pybis-only receiver spike near
56.7 ns.  This sweep isolates short local bit histories to find when that
behavior appears, whether it is simulator-specific, and whether there are other
repeatable pybis-vs-refspice behaviors.

## Test Setup

- Pattern family: `0000 + 1*pre_high + 0*low_gap + 1*post_high + 0000`
- UI: 2 ns
- Input transition time: 200 ps
- Channel for main history sweep: 30 cm coarse10 RLGC, loss scale 5
- Termination: 50 ohm to ground
- Pybis model: corrected edge50/tailflat4p2 pybis model
- Main reference comparison: Xyce pybis vs Xyce refspice
- Simulator cross-check: corrected ngspice pybis vs Xyce pybis on all 64 fixed-channel histories

The rise metric is the maximum absolute `pybis - refspice` receiver voltage
difference in a 1.4 ns window after the target rising input edge.

## Main Rise-Spike Trend

For the fixed 30 cm/loss5 stressed channel, the positive receiver spike is a
one-UI-low-gap phenomenon.

| Low gap before target rise | Cases | Min max error | Mean max error | Max max error |
| --- | ---: | ---: | ---: | ---: |
| 1 UI | 16 | 1.204 V | 1.296 V | 1.519 V |
| 2 UI | 16 | 0.109 V | 0.137 V | 0.163 V |
| 3 UI | 16 | 0.050 V | 0.058 V | 0.074 V |
| 4 UI | 16 | 0.048 V | 0.054 V | 0.063 V |

The early spike is almost independent of the following high run length
(`post_high`).  That makes sense because the measurement window is immediately
after the target rise, before later bits can influence the receiver.

The previous high-run length changes the amplitude but not the trigger rule:
all `low_gap = 1 UI` cases are large.  The strongest fixed-channel case is
`hist_h1_g1_p*`, where the pybis receiver reaches about 1.53 V while refspice is
only about 0.91 V in the same window.

## Channel Trend

For the strongest-history pattern (`1 UI high / 1 UI low / 3 UI high`), channel
length is the dominant control.  Loss slightly reduces the spike, but does not
remove it once the length is in the 20-30 cm range.

| Channel length | Loss x1 | Loss x3 | Loss x5 |
| ---: | ---: | ---: | ---: |
| 10 cm | 0.193 V | 0.180 V | 0.168 V |
| 20 cm | 1.451 V | 1.417 V | 1.384 V |
| 30 cm | 1.630 V | 1.573 V | 1.519 V |

The 10 cm cases do not show the same positive spike.  Their largest difference
is negative, meaning pybis is below refspice in the measured window.  The large
positive spike appears once the channel delay/reflection timing lines up with
the one-UI low-gap history.

## Ngspice vs Xyce Pybis Cross-Check

The corrected ngspice pybis model was run on all 64 fixed-channel histories and
compared directly to the Xyce pybis output.

| Metric | Result |
| --- | ---: |
| Corrected ngspice cases completed | 64 / 64 |
| Mean max ngspice-vs-Xyce rise difference | 45.9 mV |
| Worst max ngspice-vs-Xyce rise difference | 136.4 mV |
| Mean max ngspice-vs-Xyce fall-window difference | 25.2 mV |
| Worst max ngspice-vs-Xyce fall-window difference | 57.9 mV |

The worst simulator-to-simulator difference happens in the same strongest
`low_gap = 1 UI` spike cases.  Even there, the ngspice/Xyce pybis disagreement
is much smaller than the pybis/refspice disagreement.  So the spike trend is not
an ngspice-only or Xyce-only artifact.

## Secondary Behavior Found

The sweep also found a repeatable negative pybis-vs-refspice error after
exactly a 2 UI high run.  This is measured in the 1.4 ns window after the target
falling input edge.

| Post-high run length | Cases | Min max error | Mean max error | Max max error |
| --- | ---: | ---: | ---: | ---: |
| 1 UI | 16 | 0.234 V | 0.278 V | 0.335 V |
| 2 UI | 16 | 0.707 V | 0.739 V | 0.766 V |
| 3 UI | 16 | 0.055 V | 0.075 V | 0.108 V |
| 4 UI | 16 | 0.055 V | 0.062 V | 0.071 V |

This is not the same as the positive rise spike.  Around the fall window after a
2 UI high burst, pybis is still substantially below refspice, then catches up.
So it looks more like a run-length/settling mismatch than a separate positive
overshoot.

## Current Interpretation

The strongest evidence points to channel memory interacting with the pybis
driver's edge-state behavior:

- In the spike cases, the receiver jumps high while the pybis source-side
  `tx_out` is still near low.  For the top fixed-channel case, pybis receiver
  max is about 1.53 V while pybis `tx_out` max is only about 0.11 V in the same
  rise window.
- A single low UI after a previous high pulse leaves enough stored/reflected
  channel energy to create a large receiver event on the next target rise.
- Waiting 2 UI or more before the target rise mostly removes the effect.
- Longer channels put the reflected/stored energy in the bad time window; a
  short 10 cm channel does not show the same positive spike.
- Added loss damps the amplitude slightly, but the channel timing is the
  stronger factor in this sweep.

This is a model/testbench behavior, not an eye-diagram plotting artifact.  The
corrected ngspice and Xyce pybis runs show the same trend.

## Key Files

- `spike_trend_summary.csv`: Xyce refspice vs Xyce pybis per-case metrics
- `ngspice_validation_fixed_channel_full.csv`: corrected ngspice pybis vs Xyce pybis for all fixed-channel histories
- `plots/fixed_channel_spike_history_heatmap.png`: rise-spike dependence on local bit history
- `plots/channel_spike_strength_heatmap.png`: rise-spike dependence on channel length/loss
- `plots/representative_rise_spike_cases.png`: waveform examples for the rise spike
- `plots/representative_fall_run_length_cases.png`: waveform examples for the secondary fall-window behavior
- `plots/ngspice_xyce_pybis_fixed_channel_agreement_heatmap.png`: corrected ngspice/Xyce pybis agreement
