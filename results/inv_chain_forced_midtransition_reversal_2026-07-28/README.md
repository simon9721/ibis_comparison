# inv_chain Forced Mid-Transition Reversal Study

This study replaces nominally short 50/100/200 ps tests with pulse widths chosen from the fitted directional delays and taus. A case is accepted as a genuine reversal only when both GUP and GDN are between 0.05 and 0.95 when their own delayed reverse commands arrive.

## Bench

- Supply: `1.8 V`; load: `50 ohm || 2 pF`; temperature: `27 C`.
- Applied input edge: `1 ps`.
- High-pulse widths: `35, 45, 50 ps`.
- Low-pulse widths: `40, 45, 50 ps`.
- HSPICE native IBIS and transistor runs use the new stimuli and are cached by deck/model signature.

## Why The Old Set Was Weak

- The input pulse width is not the duration seen by each hidden state because pullup and pulldown on/off delays differ.
- For short-high, GUP motion is approximately `width - 21 ps`, while GDN motion is approximately `width + 35-36 ps`.
- For short-low, the skew reverses. The old 100 ps and 200 ps cases are mostly settled; 50 ps is near the boundary and remains partial for both states in this measured setup.
- A screened 25 ps high candidate was also too early: GUP was below the 5% state threshold when its reverse command arrived. Its completed artifacts remain under `slow_1ns/cases/midrev_25ps_high/`.

## Reversal Certification

| Profile | Case | GUP at reverse | GDN at reverse | Both partial |
|---|---|---:|---:|---|
| slow_1ns | midrev_35ps_high | 0.334 | 0.125 | True |
| slow_1ns | midrev_45ps_high | 0.579 | 0.102 | True |
| slow_1ns | short_pulse_50ps_high | 0.666 | 0.077 | True |
| slow_1ns | midrev_40ps_low | 0.116 | 0.056 | True |
| slow_1ns | midrev_45ps_low | 0.094 | 0.133 | True |
| slow_1ns | short_pulse_50ps_low | 0.077 | 0.240 | True |
| fast_5ps | midrev_35ps_high | 0.331 | 0.119 | True |
| fast_5ps | midrev_45ps_high | 0.586 | 0.110 | True |
| fast_5ps | short_pulse_50ps_high | 0.658 | 0.084 | True |
| fast_5ps | midrev_40ps_low | 0.118 | 0.061 | True |
| fast_5ps | midrev_45ps_low | 0.092 | 0.151 | True |
| fast_5ps | short_pulse_50ps_low | 0.076 | 0.257 | True |

## Coefficient-First Results

| Profile | Case | Flow | Pad RMSE (mV) | Ku RMSE | Kd RMSE |
|---|---|---|---:|---:|---:|
| slow_1ns | midrev_35ps_high | gate_state | 12.415 | 0.01932 | 0.05150 |
| slow_1ns | midrev_45ps_high | gate_state | 18.458 | 0.03112 | 0.04360 |
| slow_1ns | short_pulse_50ps_high | gate_state | 17.373 | 0.02834 | 0.03747 |
| slow_1ns | midrev_40ps_low | gate_state | 36.245 | 0.05883 | 0.01915 |
| slow_1ns | midrev_45ps_low | gate_state | 43.629 | 0.06137 | 0.02107 |
| slow_1ns | short_pulse_50ps_low | gate_state | 39.625 | 0.05080 | 0.01986 |
| fast_5ps | midrev_35ps_high | gate_state | 12.170 | 0.01826 | 0.05401 |
| fast_5ps | midrev_45ps_high | gate_state | 16.664 | 0.02951 | 0.04153 |
| fast_5ps | short_pulse_50ps_high | gate_state | 16.600 | 0.02815 | 0.03775 |
| fast_5ps | midrev_40ps_low | gate_state | 35.785 | 0.05989 | 0.01724 |
| fast_5ps | midrev_45ps_low | gate_state | 44.616 | 0.06220 | 0.02004 |
| fast_5ps | short_pulse_50ps_low | gate_state | 45.086 | 0.06019 | 0.01924 |

## Localized Response Extremes

These values are measured only around the delayed output response. They prevent a broad-window RMSE from hiding a short but important amplitude error.

| Profile | Case | Native IBIS pad | Transistor pad | Gate-state pad | Gate minus native |
|---|---|---:|---:|---:|---:|
| slow_1ns | midrev_35ps_high | 0.075 | 0.000 | 0.178 | +0.103 |
| slow_1ns | midrev_45ps_high | 0.286 | 0.000 | 0.343 | +0.057 |
| slow_1ns | short_pulse_50ps_high | 0.466 | 0.000 | 0.455 | -0.011 |
| slow_1ns | midrev_40ps_low | 1.356 | 1.422 | 0.967 | -0.389 |
| slow_1ns | midrev_45ps_low | 1.304 | 1.422 | 0.836 | -0.468 |
| slow_1ns | short_pulse_50ps_low | 1.112 | 1.422 | 0.740 | -0.372 |
| fast_5ps | midrev_35ps_high | 0.062 | 0.000 | 0.171 | +0.109 |
| fast_5ps | midrev_45ps_high | 0.296 | 0.000 | 0.335 | +0.039 |
| fast_5ps | short_pulse_50ps_high | 0.448 | 0.000 | 0.427 | -0.021 |
| fast_5ps | midrev_40ps_low | 1.346 | 1.422 | 0.958 | -0.388 |
| fast_5ps | midrev_45ps_low | 1.291 | 1.422 | 0.820 | -0.471 |
| fast_5ps | short_pulse_50ps_low | 1.205 | 1.422 | 0.743 | -0.461 |

## Outputs

- `<profile>/plots/01_waveform_comparison/`: pad, Ku, and Kd overlays.
- `<profile>/plots/02_reversal_state_evidence/`: input, GUP/GDN, targets, and sampled state values.
- `<profile>/waveform_data/`: aligned numeric waveforms.
- `plots/03_reversal_depth_summary.png`: measured GUP/GDN state depth at every reverse command.
- `plots/04_response_extrema_summary.png`: localized pad peaks/minima across pulse widths.
- `reversal_state_summary.csv`: measured state-at-reverse certification.
- `localized_response_extrema.csv`: pad and coefficient extrema around each interrupted response.
- `metrics.csv`: pad/Ku/Kd comparison metrics.
- Legacy pybis metrics remain in `metrics.csv` for provenance, but legacy is intentionally omitted from presentation figures and report tables because its reversal failure is already established.

Certified forced reversals: `12/12`.
HSPICE reference records: `28`.

## Interpretation

- These cases test actual hidden-state reversals rather than merely short input pulses.
- Gate-state playback is dramatically better than legacy full-table replay in all certified cases.
- It is not uniformly amplitude-correct: the shortest short-high response can overshoot native IBIS, and short-low pad dips are substantially too deep.
- HSPICE transistor output largely rejects these 35-50 ps pulses. Matching native-IBIS Ku/Kd is therefore an IBIS-playback claim, not a claim that the IBIS model reproduces transistor minimum-pulse filtering.
- The normal reconstruction gate still applies before any gate-state result is considered generally valid.