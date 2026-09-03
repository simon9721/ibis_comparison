# inv_chain HSPICE Native-IBIS / Transistor Match Analysis

This analysis searches for nontrivial pulse cases where the HSPICE native IBIS pad waveform agrees with the HSPICE transistor chain. Cases in which both outputs reject the pulse are excluded from the match claim.

## Headline Finding

- Pad matches occur only with the fast `5 ps` IBIS model in this sweep; the slow `1 ns` IBIS model does not pass the waveform, amplitude, and timing gates.
- The earliest partial-output match is the `130 ps` short-high case: transistor excursion is `88.6%`, pad RMSE is about `72.6 mV`, peak error is about `61.2 mV`, and peak timing differs by `17 ps`.
- Native-IBIS `Ku/Kd` are nevertheless almost fully exercised in that case. The pad match therefore does not prove that the IBIS coefficients represent the transistor's hidden internal state.

## Match Gates

- Pad RMSE <= `75 mV`.
- Pad peak/minimum error <= `100 mV`.
- Peak/minimum timing error <= `100 ps`.
- Transistor excursion >= `5%` of loaded settled swing.

## Passing Cases

| Profile | Direction | Width (ps) | Excursion | Partial | Pad RMSE (mV) | Extreme error (mV) | Timing delta (ps) | Ku peak | Kd min | Ku > 0.5 (ps) | Kd < 0.5 (ps) |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| fast_5ps | short_high | 130 | 88.6% | True | 72.56 | 61.16 | +17.0 | 1.0162 | -0.0745 | 113.0 | 168.0 |
| fast_5ps | short_high | 135 | 90.7% | True | 66.43 | 46.58 | +14.0 | 1.0163 | -0.0737 | 118.0 | 173.0 |
| fast_5ps | short_high | 140 | 92.3% | True | 61.33 | 35.83 | +15.0 | 1.0163 | -0.0730 | 123.0 | 178.0 |
| fast_5ps | short_high | 145 | 93.6% | True | 57.04 | 28.84 | +14.0 | 1.0164 | -0.0740 | 128.0 | 183.0 |
| fast_5ps | short_high | 150 | 94.6% | True | 53.78 | 22.85 | +12.0 | 1.0163 | -0.0743 | 133.0 | 188.0 |
| fast_5ps | short_high | 180 | 98.3% | False | 40.77 | 5.22 | +7.0 | 1.0164 | -0.0735 | 162.0 | 218.0 |
| fast_5ps | short_high | 200 | 99.3% | False | 37.71 | 1.61 | +9.0 | 1.0162 | -0.0735 | 182.0 | 238.0 |
| fast_5ps | short_low | 135 | 100.7% | False | 66.30 | 6.16 | +21.0 | 1.0222 | -0.0707 | 2200.0 | 2200.0 |
| fast_5ps | short_low | 140 | 101.0% | False | 59.14 | 2.69 | +18.0 | 1.0114 | -0.0712 | 2200.0 | 2200.0 |
| fast_5ps | short_low | 145 | 101.2% | False | 53.71 | 0.93 | +18.0 | 1.0182 | -0.0717 | 2200.0 | 2200.0 |
| fast_5ps | short_low | 150 | 101.3% | False | 49.76 | 0.53 | +15.0 | 1.0130 | -0.0728 | 2200.0 | 2200.0 |
| fast_5ps | short_low | 180 | 101.5% | False | 39.32 | 1.85 | +10.0 | 1.0128 | -0.0736 | 2200.0 | 2200.0 |
| fast_5ps | short_low | 200 | 101.5% | False | 36.79 | 2.09 | +10.0 | 1.0184 | -0.0714 | 2200.0 | 2200.0 |

## Earliest Partial Match Ku/Kd

- Case: `fast_5ps / visible_sweep_130ps_high`.
- Native Ku peak: `1.0162`; Ku remains above `0.5` for `113.0 ps`.
- Native Kd minimum: `-0.0745`; Kd remains below `0.5` for `168.0 ps`.
- These are near full coefficient endpoints even though the transistor pad pulse remains slightly below its settled loaded level.

## Best Visible Cases

| Rank | Profile | Direction | Width (ps) | Score | Pad RMSE (mV) | Extreme error (mV) | Timing delta (ps) |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | fast_5ps | short_high | 200 | 0.609 | 37.71 | 1.61 | +9.0 |
| 2 | fast_5ps | short_low | 200 | 0.611 | 36.79 | 2.09 | +10.0 |
| 3 | fast_5ps | short_low | 180 | 0.643 | 39.32 | 1.85 | +10.0 |
| 4 | fast_5ps | short_high | 180 | 0.666 | 40.77 | 5.22 | +7.0 |
| 5 | fast_5ps | short_low | 150 | 0.819 | 49.76 | 0.53 | +15.0 |
| 6 | fast_5ps | short_low | 145 | 0.905 | 53.71 | 0.93 | +18.0 |
| 7 | fast_5ps | short_low | 140 | 0.995 | 59.14 | 2.69 | +18.0 |
| 8 | fast_5ps | short_high | 150 | 1.066 | 53.78 | 22.85 | +12.0 |

## Outputs

- `pad_match_metrics.csv`: every width/profile/direction.
- `plots/01_pad_match_sweep.png`: native-IBIS and transistor extrema versus pulse width.
- `plots/matched_cases/`: pad plus native-IBIS Ku/Kd for every passing case.
- `waveform_data/`: aligned numeric data for passing cases.