# Voltage-Matching V2: Clear Three-Buffer Results

This package compares exactly three simulator/model flows under the same `50 ohm || 2 pF` load and `50 ps` command edges:

- HSPICE native IBIS: coefficient and pad reference.
- ngspice legacy pybis: ordinary elapsed-time Ku/Kd replay.
- ngspice Voltage-Matching V2: pad-voltage snapshot mapped to a shared opposite-table Ku/Kd start time.

HSPICE data are read from the existing cache. Only the six exact-width legacy ngspice reversal cases are simulated for this package.

## Full-Swing Control

The full-swing cases establish the non-interrupted baseline. They directly measure how much the V2 replay transaction changes an otherwise settled rise/fall sequence.

| Buffer | Legacy pad RMSE (mV) | V2 pad RMSE (mV) | Legacy Ku/Kd RMSE | V2 Ku/Kd RMSE |
|---|---:|---:|---:|---:|
| io_buf | 63.994 | 73.123 | 0.46301 | 0.43780 |
| inv_chain | 273.888 | 274.274 | 0.35009 | 0.35014 |
| ex2 | 45.631 | 45.908 | 0.09756 | 0.09787 |

Direct V2-versus-legacy full-swing difference:

| Buffer | Pad RMSE (mV) | Ku RMSE | Kd RMSE |
|---|---:|---:|---:|
| io_buf | 10.781 | 0.10316 | 0.02067 |
| inv_chain | 0.502 | 0.00023 | 0.00172 |
| ex2 | 0.758 | 0.00279 | 0.00222 |

## Interrupted Cases

These are true output-level midpoint reversals selected separately for each buffer. V2 is judged from pad, Ku, and Kd together; a pad-only improvement is not a coefficient-correct result.

| Buffer | Direction | Pulse (ps) | Flow | Pad RMSE (mV) | Ku RMSE | Kd RMSE |
|---|---|---:|---|---:|---:|---:|
| io_buf | short-high | 1503.9 | legacy_pybis | 157.285 | 0.42737 | 0.16991 |
| io_buf | short-high | 1503.9 | voltage_matching_v2 | 52.105 | 0.39821 | 0.31263 |
| io_buf | short-low | 162.5 | legacy_pybis | 496.153 | 0.80756 | 0.54637 |
| io_buf | short-low | 162.5 | voltage_matching_v2 | 167.789 | 0.66370 | 0.40195 |
| inv_chain | short-high | 103.5 | legacy_pybis | 878.405 | 0.50218 | 0.35069 |
| inv_chain | short-high | 103.5 | voltage_matching_v2 | 846.569 | 0.49023 | 0.33278 |
| inv_chain | short-low | 110.2 | legacy_pybis | 642.452 | 0.48985 | 0.51599 |
| inv_chain | short-low | 110.2 | voltage_matching_v2 | 782.474 | 0.58963 | 0.34580 |
| ex2 | short-high | 808.6 | legacy_pybis | 421.570 | 0.42907 | 0.18897 |
| ex2 | short-high | 808.6 | voltage_matching_v2 | 377.172 | 0.39969 | 0.15750 |
| ex2 | short-low | 689.1 | legacy_pybis | 497.095 | 0.38282 | 0.50753 |
| ex2 | short-low | 689.1 | voltage_matching_v2 | 852.622 | 0.62124 | 0.26583 |

## Finding

- Full swing: V2 is nearly identical to legacy for `inv_chain` and `ex2`; `io_buf` shows a larger Ku difference around the settled reverse edge.
- `io_buf` short-low: V2 improves pad, Ku, and Kd together. This is the clearest positive case.
- `inv_chain` and `ex2` short-high: V2 improves all three metrics, but only modestly and the absolute disagreement remains large.
- `io_buf` short-high: pad and Ku improve, but Kd worsens. This is not coefficient-correct overall.
- `inv_chain` and `ex2` short-low: Kd improves while pad and/or Ku become worse. The single sampled pad voltage does not identify a universally correct opposite-table state.

Overall: Voltage-Matching V2 is a useful directional baseline, not a general interrupted-transition solution.

## How To Read The Figures

- Thick black is HSPICE native IBIS; orange circles are legacy pybis; blue diamonds are Voltage-Matching V2.
- Dashed gray lines are the first and reverse input commands.
- The blue dotted line and X marker identify the V2 voltage-sampling event when available.
- Full-swing control is shown first, followed by short-high and short-low midpoint reversals.

## Files

- `01_full_swing_contact_sheet.png`
- `02_interrupted_short_high_contact_sheet.png`
- `03_interrupted_short_low_contact_sheet.png`
- `04_all_results_contact_sheet.png`
- `figures/`: one full-resolution PNG per buffer and case role.
- `waveforms/`: aligned numerical data behind every figure.
- `metrics.csv`: active-window errors against HSPICE native IBIS.
- `v2_vs_legacy_summary.csv`: direct full-swing equivalence and interrupted-case improvement/tradeoff classification.
- `source_manifest.csv`: exact cached/rerun provenance.
