# Kd Recovery Hold-Time Diagnostic

This diagnostic measures the HSPICE short-high Kd recovery hold time after the input reverse edge. It uses cached HSPICE native-IBIS data only; no simulations are run here.

## Headline Finding

- HSPICE `T_hold50 = Kd_recover50 - reverse_edge` is not perfectly constant: constant-hold spread is `23.0%` with RMS residual `195.7 ps`.
- A linear hold law fits these three widths much better: `T_hold50 = 1.7153 + 0.3119 * pulse_width` ns, RMS residual `21.5 ps`.
- The Kd 10%-90% recovery-rate tau remains nearly constant, spread `1.086x`, so the next model should change release/hold timing first, not the ramp tau.
- Verdict: `HOLD_PLUS_WIDTH_DRIFT_PREFERRED`.

## HSPICE Hold Measurements

| Case | Pulse ns | Reverse ns | Kd min ns | Recover10 ns | Recover50 ns | Recover90 ns | T_hold50 ns | Tau10-90 ns |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| short_pulse_500ps_high | 0.500 | 5.5005 | 5.8725 | 7.1708 | 7.3519 | 7.5525 | 1.8514 | 0.1737 |
| short_pulse_1ns_high | 1.000 | 6.0005 | 6.3866 | 7.8490 | 8.0576 | 8.2637 | 2.0571 | 0.1887 |
| short_pulse_2ns_high | 2.000 | 7.0005 | 7.5387 | 9.1250 | 9.3298 | 9.5329 | 2.3293 | 0.1857 |

## Candidate Hold Comparison

| Case | Flow | T_hold50 ns | Error vs HSPICE ps | Recovery pulse max |
|---|---|---:|---:|---:|
| short_pulse_500ps_high | hspice_native_ibis | 1.8563 | 4.9 |  |
| short_pulse_500ps_high | ngspice_two_state_directional_residual | 2.7233 | 871.9 | 0.0 |
| short_pulse_500ps_high | ngspice_two_state_directional_residual_recover_mean | 2.1941 | 342.7 | 1.124925605049616 |
| short_pulse_500ps_high | ngspice_two_state_directional_residual_recover_fast | 1.6433 | -208.1 | 1.121638515875909 |
| short_pulse_1ns_high | hspice_native_ibis | 2.0706 | 13.5 |  |
| short_pulse_1ns_high | ngspice_two_state_directional_residual | 2.7125 | 655.4 | 0.0 |
| short_pulse_1ns_high | ngspice_two_state_directional_residual_recover_mean | 2.1912 | 134.1 | 1.124851942516704 |
| short_pulse_1ns_high | ngspice_two_state_directional_residual_recover_fast | 1.6696 | -387.4 | 1.124999724356583 |
| short_pulse_2ns_high | hspice_native_ibis | 2.3464 | 17.2 |  |
| short_pulse_2ns_high | ngspice_two_state_directional_residual | 2.7168 | 387.5 | 0.0 |
| short_pulse_2ns_high | ngspice_two_state_directional_residual_recover_mean | 2.1932 | -136.1 | 1.121497395636678 |
| short_pulse_2ns_high | ngspice_two_state_directional_residual_recover_fast | 1.6733 | -656.0 | 1.122628947081138 |

## Interpretation

- The existing mean/fast recovery candidates are fixed shifts, so they cross HSPICE at one pulse width and miss at the others.
- The measured HSPICE law is better represented as `reverse_edge + hold(pulse_width)` followed by a nearly fixed fast recovery ramp.
- A next candidate should implement this only on the short-high interrupted-turn-off path. Short-low behavior is already the healthier quadrant and should be used as a leakage/regression check.

Figures:

- `hspice_kd_hold_time_fit.png`
- `candidate_hold_time_comparison.png`

CSVs:

- `hspice_kd_hold_time.csv`
- `candidate_hold_time_comparison.csv`
- `hold_law_fit_summary.csv`
