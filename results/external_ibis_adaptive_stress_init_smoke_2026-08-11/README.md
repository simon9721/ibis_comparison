# External IBIS Adaptive Stress Campaign

This study reverses each input while its preceding native-IBIS Ku/Kd transition is near 50% composite progress.

## Bench

- Typical corner, model-derived supply/reference voltages, and `50 ohm || 2 pF` load.
- Input rise/fall time remains 50 ps; only pulse timing changes by model and direction.
- `short_high`: falling edge arrives during the preceding rising output transition.
- `short_low`: the model is first settled high, then a rising edge arrives during the preceding falling output transition.
- Stress width is selected from the cached full-transition HSPICE Ku/Kd trajectory; HSPICE is used only to design and validate the stress bench, not to alter pybis.

## Results

- Unique applicable models: `1`; requested direction cases: `2`.
- Completed HSPICE/ngspice comparisons: `2`.
- `short_high`: GOOD `0`, WARN `0`, CHECK `1`
- `short_low`: GOOD `0`, WARN `0`, CHECK `1`

## Incomplete Cases

None.

## Case Table

| File | Model | Direction | Width ns | Progress | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---:|---:|---|---|---:|---:|---:|
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_lv | short_high | 2.462 | 0.500 | COMPLETED | CHECK | 156.513 | 0.1700 | 0.4958 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_lv | short_low | 4.989 | 0.500 | COMPLETED | CHECK | 23.128 | 0.0247 | 0.1930 |

## Files

- `stress_selection.csv`: selected per-model pulse widths and HSPICE state at reversal.
- `metrics.csv`: simulator status and pad/Ku/Kd comparison metrics.
- `cases/<model>/<direction>/`: exact decks, copied IBIS/model, raw output, and logs.
- `plots/<model>/<direction>.png`: pad, Ku, and Kd overlays.
- `plots/summary_outcomes.png` and `summary_error_vs_pulse_width.png`: campaign summaries.
