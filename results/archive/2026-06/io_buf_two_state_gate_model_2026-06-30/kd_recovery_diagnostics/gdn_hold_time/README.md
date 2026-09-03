# GDN-Keyed Kd Recovery Hold Diagnostic

This diagnostic checks whether the short-high Kd hold law can be keyed to `GDN` at the reverse edge, which would be a causal gate-state variable. It uses cached HSPICE and ngspice raw data only.

## Headline Finding

- Pulse-width/command-age fit remains strong: RMS `21.5 ps`.
- Current `ngspice_two_state_directional_residual` `GDN@reverse` fit is weaker: RMS `84.0 ps`.
- The current GDN state collapses 500 ps and 1 ns to essentially the same value, so it cannot distinguish their different HSPICE hold times.
- Linear GDN physical-limit check predicts hold `1.9542 ns` at `GDN_ON=1`, not `0 ns`; the origin-forced depth form has RMS `1597.8 ps`.
- Verdict: `GDN_AT_REVERSE_COLLAPSES_WIDTHS`. Do not implement the next candidate using the present `GDN@reverse` alone.

## Primary Samples

| Case | Pulse ns | HSPICE T_hold50 ns | GDN@reverse | GDN min after reverse | Main tau ns |
|---|---:|---:|---:|---:|---:|
| short_pulse_500ps_high | 0.500 | 1.8514 | 1.0000 | 0.0016 | 0.1737 |
| short_pulse_1ns_high | 1.000 | 2.0571 | 1.0000 | 0.0002 | 0.1887 |
| short_pulse_2ns_high | 2.000 | 2.3293 | 0.0977 | 0.0000 | 0.1857 |

## Fit Summary

| Predictor | Flow | Intercept | Slope | RMS ps | Limit at GDN_ON ns | Origin-forced RMS ps | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| pulse_width_reference |  | 1.7153 | 0.3119 | 21.5 |  |  | REFERENCE_CAUSAL_AGE_BUT_NOT_GATE_STATE |
| gdn_at_reverse | ngspice_two_state_identity | 2.3699 | -0.4156 | 84.0 | 1.9542 | 1597.8 | GDN_AT_REVERSE_COLLAPSES_WIDTHS |
| gdn_at_reverse | ngspice_two_state_pwl | 2.3699 | -0.4156 | 84.0 | 1.9542 | 1597.8 | GDN_AT_REVERSE_COLLAPSES_WIDTHS |
| gdn_at_reverse | ngspice_two_state_directional | 2.3699 | -0.4156 | 84.0 | 1.9542 | 1597.8 | GDN_AT_REVERSE_COLLAPSES_WIDTHS |
| gdn_at_reverse | ngspice_two_state_directional_residual | 2.3699 | -0.4156 | 84.0 | 1.9542 | 1597.8 | GDN_AT_REVERSE_COLLAPSES_WIDTHS |
| gdn_at_reverse | ngspice_two_state_directional_residual_recover_mean | 2.3699 | -0.4156 | 84.0 | 1.9542 | 1597.8 | GDN_AT_REVERSE_COLLAPSES_WIDTHS |
| gdn_at_reverse | ngspice_two_state_directional_residual_recover_fast | 2.3699 | -0.4156 | 84.0 | 1.9542 | 1597.8 | GDN_AT_REVERSE_COLLAPSES_WIDTHS |

## Interpretation

- The GDN-keyed idea is physically attractive, but the current generated `GDN` state is delayed relative to the pending NMOS-off command.
- At the reverse edge, 500 ps and 1 ns both report `GDN ~= 1`, even though HSPICE later shows different Kd recovery holds. That means `GDN@reverse` has not yet stored the relevant pending turn-off information.
- The next candidate should use a causal variable that is actually available and discriminative at retrigger: latched command age / pending NMOS-off phase, or a redesigned gate state that moves when the pending off command is launched.
- A literal pulse-width law is still not a production model claim. It is better described as command-age keyed at the reverse edge, and it needs a held-out pulse width before promotion.

Figures:

- `gdn_keyed_hold_fit.png`
- `gdn_at_reverse_by_variant.png`

CSVs:

- `gdn_hold_samples.csv`
- `gdn_hold_fit_summary.csv`
