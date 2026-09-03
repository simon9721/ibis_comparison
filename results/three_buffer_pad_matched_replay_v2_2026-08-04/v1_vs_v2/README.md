# Pad-Matched Replay V1 vs V2

V1 continuously filtered the final legacy coefficients, even when replay was inactive. V2 replaces that with an exact inactive legacy bypass and uses held/replay values only during the reverse-edge transaction.

## Counts

- `v1` `short_high`: `0/48` rows improve all three numerically; `0/48` improve all three by at least 5%.
- `v1` `short_low`: `14/48` rows improve all three numerically; `11/48` improve all three by at least 5%.
- `v2` `short_high`: `3/48` rows improve all three numerically; `0/48` improve all three by at least 5%.
- `v2` `short_low`: `9/48` rows improve all three numerically; `6/48` improve all three by at least 5%.

## Figures

- `v1_vs_v2/plots/01_long_control_preservation_v1_v2.png`
- `v1_vs_v2/plots/02_short_pulse_outcomes_v1_v2.png`

## Data

- `v1_v2_case_outcomes.csv`
