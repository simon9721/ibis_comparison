# Pad-Matched Replay Load Portability

The replay map was calibrated only at `50 ohm || 2 pF`. These rows test eight other 25/50/100 ohm and 0/2/10 pF combinations.

## Result

- 500 ps short-low all-three improvements: `46` of `96` pad-flow rows.
- 500 ps short-high all-three improvements: `0` of `96` pad-flow rows.
- A heatmap value below one means pad, Ku, and Kd all beat legacy; the cell displays the worst of the three ratios.
- Numeric failure, ambiguity, and envelope/discontinuity classification remain hard caveats even when a ratio is below one.

## Figures

- `portability_evidence/plots/01_short_low_500ps_worst_ratio.png`
- `portability_evidence/plots/02_short_high_500ps_worst_ratio.png`
- `portability_evidence/plots/03_long_control_worst_ratio.png`

## Data

- `load_case_outcomes.csv`
- `../candidate_metrics.csv`
