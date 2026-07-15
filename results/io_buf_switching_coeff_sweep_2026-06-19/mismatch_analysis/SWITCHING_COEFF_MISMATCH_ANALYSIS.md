# io_buf Switching Coefficient Mismatch Analysis

This report focuses on the WARN/CHECK cases from the switching-coefficient sweep.
The goal is to separate simple waveform error from the underlying Ku/Kd state behavior.

## Key Takeaway

The largest mismatch is not load-dependent. It appears when the input stimulus makes the IBIS switching state ambiguous: slow input ramps and interrupted transitions.

## Case Summary

| Case | Status | Pad RMSE (mV) | Ku RMSE | Kd RMSE | Max coeff err | Max coeff 50% delta (ps) | Max pad 50% delta (ps) | Mechanism |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| edge_5ps_50r_2pf | WARN | 7.9 | 0.0153 | 0.0209 | 0.164 | 22.4 | 11.1 | Small but visible coefficient timing skew. The pad waveform is still close; coefficient RMSE crosses the GOOD threshold first. |
| edge_50ps_50r_2pf | WARN | 11.4 | 0.0103 | 0.0148 | 0.070 | 19.1 | 16.0 | Moderate slow-edge skew. Ku/Kd still follow the same general shape, but the pad and coefficient transitions no longer line up at the few-ps level. |
| edge_500ps_50r_2pf | CHECK | 134.8 | 0.1027 | 0.1317 | 0.447 | 178.7 | 176.5 | The input ramp is slow enough that HSPICE and pybis make different switching-decision timing choices. Coefficient turn-off/turn-on timing diverges by hundreds of ps. |
| edge_2ns_50r_2pf | CHECK | 393.2 | 0.2808 | 0.3365 | 1.005 | 721.4 | 721.7 | Very slow input ramp. HSPICE switches the output much earlier on the rising edge and later on the falling edge; pybis lags/advances differently, creating large pad error. |
| short_pulse_2ns_high | CHECK | 361.4 | 0.2833 | 0.2314 | 0.798 | 361.7 | 393.9 | Interrupted transition. HSPICE never lets Ku reach a full pull-up state before reversal, while pybis drives Ku close to full on, causing a much larger pad pulse. |

## Event-Level 50% Timing

Positive timing delta means ngspice/pybis crosses later than HSPICE. Negative means ngspice/pybis crosses earlier.

| Case | Event | Input | Coeff | Coeff dir | Coeff 50% delta (ps) | Pad 50% delta (ps) | Peak delta |
|---|---:|---|---|---|---:|---:|---:|
| edge_5ps_50r_2pf | 1 | rise | kd | fall | 4.4 | 7.3 | 0.002 |
| edge_5ps_50r_2pf | 1 | rise | ku | rise | 12.5 | 7.3 | -0.007 |
| edge_5ps_50r_2pf | 2 | fall | ku | fall | 16.3 | 11.1 | 0.002 |
| edge_5ps_50r_2pf | 2 | fall | kd | rise | 22.4 | 11.1 | -0.004 |
| edge_50ps_50r_2pf | 1 | rise | kd | fall | 12.0 | 16.0 | 0.001 |
| edge_50ps_50r_2pf | 1 | rise | ku | rise | 19.1 | 16.0 | -0.009 |
| edge_50ps_50r_2pf | 2 | fall | ku | fall | -14.9 | -13.5 | 0.003 |
| edge_50ps_50r_2pf | 2 | fall | kd | rise | -12.5 | -13.5 | 0.002 |
| edge_500ps_50r_2pf | 1 | rise | kd | fall | 98.6 | 98.9 | 0.003 |
| edge_500ps_50r_2pf | 1 | rise | ku | rise | 100.6 | 98.9 | -0.023 |
| edge_500ps_50r_2pf | 2 | fall | ku | fall | -174.0 | -176.5 | 0.004 |
| edge_500ps_50r_2pf | 2 | fall | kd | rise | -178.7 | -176.5 | 0.028 |
| edge_2ns_50r_2pf | 1 | rise | kd | fall | 365.8 | 370.9 | 0.002 |
| edge_2ns_50r_2pf | 1 | rise | ku | rise | 372.2 | 370.9 | -0.027 |
| edge_2ns_50r_2pf | 2 | fall | ku | fall | -721.4 | -721.7 | 0.009 |
| edge_2ns_50r_2pf | 2 | fall | kd | rise | -718.5 | -721.7 | 0.023 |
| short_pulse_2ns_high | 1 | rise | kd | fall | 4.6 | -79.0 | -0.000 |
| short_pulse_2ns_high | 1 | rise | ku | rise | -277.4 | -79.0 | 0.469 |
| short_pulse_2ns_high | 2 | fall | ku | fall | 361.7 | 393.9 | -0.001 |
| short_pulse_2ns_high | 2 | fall | kd | rise | 360.4 | 393.9 | -0.045 |

## Interpretation

For normal fast toggles, HSPICE and pybis generate nearly identical Ku/Kd trajectories. The mismatch grows when the input ramp itself is slow because the two implementations do not make the same switching-state timing decision.

For the short-pulse case, the issue is not just a timing offset. The transition is interrupted before the pad settles. HSPICE keeps the pull-up coefficient partial, while pybis allows the pull-up coefficient to reach near full strength before recovery. That creates a much larger output pulse in ngspice/pybis.

## Diagnostic Plots

- `plots/edge_5ps_50r_2pf_diagnostic.png`
- `plots/edge_50ps_50r_2pf_diagnostic.png`
- `plots/edge_500ps_50r_2pf_diagnostic.png`
- `plots/edge_2ns_50r_2pf_diagnostic.png`
- `plots/short_pulse_2ns_high_diagnostic.png`
