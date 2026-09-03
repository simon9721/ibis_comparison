# Three-Buffer Pad-Matched Replay V2: Mid-Transition Evidence

This focused package combines the completed three-buffer v2 study with a custom-width inv_chain sweep. The report builder itself runs no simulations.

## Headline Result

- Confirmed pad-match activation: `6/6` selected reversals.
- Pad, Ku, and Kd all improve together: `0/6` cases.
- Short-high pad RMSE improves versus legacy: `3/3` buffers, but coefficient agreement does not improve consistently.
- Short-low pad RMSE regresses versus legacy: `3/3` buffers.
- Pad inverse mapping is explicitly ambiguous in `2/6` selected cases.
- Conclusion: pad voltage alone is not a sufficient hidden state for reliable reverse-edge replay across these three buffers.

## Common Bench

- Input transition: `50 ps` rise and fall for every selected case.
- Load: `50 ohm || 2 pF` directly at the output pad.
- Supplies: io_buf `3.3 V`, inv_chain `1.8 V`, ex2 `3.3 V`.
- References: HSPICE native IBIS supplies pad plus Ku/Kd; HSPICE transistor SPICE supplies pad only.
- Candidate: ngspice `InputDrivenPadMatchedReplayV2`; `slow_1ns` and `fast_5ps` identify the IBIS source profile, not the 50 ps input edge.

## Selection Rule

- Compute native-IBIS Ku/Kd transition progress immediately before the reverse edge.
- Require pad-match v2 to trigger and prefer progress in the 10%-90% interval.
- Select the case closest to 50% composite Ku/Kd progress for each buffer and direction.
- Composite progress confirms an unsettled transition; the Ku and Kd progress columns in the CSV retain directional asymmetry rather than hiding it.

## Selected Cases

| Buffer | Direction | Profile | Width | Native progress | Trigger | Ambiguous | V2 class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---:|---:|---|---|---|---:|---:|---:|
| io_buf | short_high | slow_1ns | 2 ns | 0.618 | True | False | COEFFICIENT_ARTIFACT | 234.528 | 0.1892 | 0.4923 |
| io_buf | short_low | slow_1ns | 2 ns | 0.500 | True | False | NO_CLEAR_IMPROVEMENT | 590.683 | 0.3685 | 0.3128 |
| inv_chain | short_high | fast_5ps | 0.275 ns | 0.474 | True | True | PAD_MAPPING_AMBIGUOUS | 276.509 | 0.4534 | 0.3908 |
| inv_chain | short_low | fast_5ps | 0.3 ns | 0.384 | True | False | NO_CLEAR_IMPROVEMENT | 691.984 | 0.4631 | 0.3916 |
| ex2 | short_high | fast_5ps | 1 ns | 0.555 | True | True | PAD_MAPPING_AMBIGUOUS | 129.354 | 0.2391 | 0.1190 |
| ex2 | short_low | fast_5ps | 1 ns | 0.397 | True | False | NO_CLEAR_IMPROVEMENT | 727.073 | 0.4956 | 0.3224 |

## Figures

- `00_all_buffers_pad_contact_sheet.png`: pad-level overview for all six selected reversals.
- `<buffer>/01_short_high_pad_match_v2.png`: input, pad, Ku, and Kd for fall-after-rise.
- `<buffer>/01_short_low_pad_match_v2.png`: input, pad, Ku, and Kd for rise-after-fall.
- `<buffer>/03_trigger_diagnostics.png`: sampled pad voltage, inferred table start, replay argument, and active/ambiguity flags.
- `<buffer>/*_waveforms.csv`: numeric data behind each focused figure.
- `candidate_midtransition_progress.csv`: native Ku/Kd progress for every pulse considered by the selector.

## Interpretation

The figures must be read coefficient-first: a visually improved pad is not sufficient when either Ku or Kd disagrees with native IBIS. `PAD_MAPPING_AMBIGUOUS` is retained as an experimental result, not hidden.
