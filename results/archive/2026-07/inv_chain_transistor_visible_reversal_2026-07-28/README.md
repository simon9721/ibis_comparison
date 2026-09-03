# inv_chain Transistor-Visible Reversal Sweep

This focused sweep asks whether an input pulse can both produce a measurable, incomplete HSPICE transistor output pulse and reverse the fitted pybis hidden states while both remain between 5% and 95%.

## Headline Finding

- No pulse width satisfies the strict requirement that the transistor respond while both `GUP` and `GDN` remain partial.
- Useful one-state directional cases do exist. A `100 ps` high pulse produces a `36.8%` transistor output excursion while `GUP` remains partial. A `110 ps` low pulse produces a `47.8%` excursion while `GDN` remains partial.
- These cases are valid tests of one coefficient network reversing from history. They are not proof of simultaneous pullup and pulldown retrigger behavior.
- For the representative slow and fast IBIS comparisons, the hybrid improves pad, `Ku`, and `Kd` RMSE versus the always-on gate-state model.

## Bench

- Supply: `1.8 V`.
- Load: `50 ohm || 2 pF`.
- Input rise/fall: `1 ps`.
- Temperature: `27 C`.
- Pulse widths: `55, 60, 65, 70, 75, 80, 90, 92, 94, 96, 98, 100, 102, 104, 106, 108, 110, 115, 120, 150, 180, 200 ps`.
- The transistor reference is independent of the slow/fast IBIS profile and is cached by the transistor deck/model signature.

## Criteria

- Transistor-visible partial pulse: output excursion is from `5%` to `95%` of the loaded settled swing.
- Strict two-state reversal: both `GUP` and `GDN` are between `0.05` and `0.95` at their own delayed reverse commands.
- One-state directional reversal: at least one of `GUP/GDN` is still partial. This is a real interrupted transition, but the other network has already settled.
- A candidate must also satisfy the transistor-visible partial-pulse criterion.

## Strict Two-State Candidates

| Profile | Direction | Width (ps) | Transistor excursion | GUP | GDN |
|---|---|---:|---:|---:|---:|
| none | none | n/a | n/a | n/a | n/a |

## One-State Directional Candidates

| Profile | Direction | Width (ps) | Transistor excursion | GUP | GDN |
|---|---|---:|---:|---:|---:|
| slow_1ns | short_high | 96 | 7.0% | 0.923 | 0.041 |
| slow_1ns | short_high | 98 | 21.5% | 0.943 | 0.045 |
| slow_1ns | short_high | 100 | 36.8% | 0.940 | 0.032 |
| slow_1ns | short_high | 106 | 62.8% | 0.935 | 0.038 |
| slow_1ns | short_low | 106 | 7.2% | 0.009 | 0.828 |
| slow_1ns | short_low | 108 | 22.8% | 0.008 | 0.837 |
| slow_1ns | short_high | 110 | 71.4% | 0.949 | 0.029 |
| slow_1ns | short_low | 110 | 47.8% | 0.008 | 0.845 |
| slow_1ns | short_high | 115 | 78.0% | 0.949 | 0.049 |
| slow_1ns | short_low | 115 | 86.9% | 0.007 | 0.865 |
| fast_5ps | short_high | 96 | 7.0% | 0.944 | 0.046 |
| fast_5ps | short_high | 98 | 21.5% | 0.941 | 0.045 |
| fast_5ps | short_high | 100 | 36.8% | 0.935 | 0.043 |
| fast_5ps | short_high | 102 | 48.6% | 0.947 | 0.031 |
| fast_5ps | short_low | 106 | 7.2% | 0.009 | 0.832 |
| fast_5ps | short_low | 108 | 22.8% | 0.008 | 0.841 |
| fast_5ps | short_high | 110 | 71.4% | 0.944 | 0.041 |
| fast_5ps | short_low | 110 | 47.8% | 0.008 | 0.849 |
| fast_5ps | short_low | 115 | 86.9% | 0.006 | 0.868 |

## Representative Full Comparisons

| Profile | Case | Gate pad (mV) | Hybrid pad (mV) | Gate Ku | Hybrid Ku | Gate Kd | Hybrid Kd |
|---|---|---:|---:|---:|---:|---:|---:|
| slow_1ns | visible_sweep_100ps_high | 34.055 | 21.772 | 0.03762 | 0.02092 | 0.03727 | 0.02422 |
| slow_1ns | visible_sweep_110ps_low | 36.109 | 16.686 | 0.03845 | 0.02140 | 0.02972 | 0.01548 |
| fast_5ps | visible_sweep_100ps_high | 35.673 | 26.259 | 0.03828 | 0.02167 | 0.03821 | 0.02616 |
| fast_5ps | visible_sweep_110ps_low | 34.470 | 25.880 | 0.04015 | 0.02368 | 0.02599 | 0.01947 |

## Outputs

- `sweep_summary.csv`: numeric result for every width/profile/direction.
- `plots/01_overlap_summary.png`: transistor excursion and hidden-state depth versus pulse width.
- `plots/candidates/`: waveform/state evidence for every joint candidate.
- `plots/representative_comparisons/`: HSPICE native IBIS, HSPICE transistor, gate-state, and hybrid overlays for the 100 ps high and 110 ps low cases.
- `representative_comparison_metrics.csv`: numeric errors for those full comparisons.

## Interpretation

A transistor-visible short pulse and a pybis hidden-state reversal are separate tests. The strict two-state and one-state directional classifications must remain distinct; a one-state case is useful for testing that coefficient's reversal, but it cannot validate simultaneous pullup and pulldown state recovery.