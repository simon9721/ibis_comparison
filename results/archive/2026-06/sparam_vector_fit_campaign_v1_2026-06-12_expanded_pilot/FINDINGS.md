# Expanded scikit-rf Vector-Fit Pilot Findings

Study folder: `results/sparam_vector_fit_campaign_v1_2026-06-12_expanded_pilot`

This run tested full scikit-rf vector-fit SPICE macromodels on three representative inputs:

- `Clarity_example.S2P`
- `Ch10_35_5F3N_f4.s4p`
- `Ch3_17_5F3N_f3.s4p`

The candidate sweep covered fixed vector-fit orders `3r3c`, `5r5c`, `8r8c`, `10r10c`, and `12r12c`, with `lin` and `log` initial pole spacing, four preprocessing modes, and passivity-enforced variants when applicable.

## Headline Result

The expanded vector-fit campaign did not yet produce a reliable general full-model path.

Out of `232` candidate rows:

- `2` passed the independent frequency/passivity math gates.
- Both passing candidates were the same Clarity raw `vector_3r3c_lin` fit, before and after passivity enforcement.
- No Cisco `.s4p` full vector-fit candidate passed the independent fit gates.
- After ngspice smoke testing, the selected Clarity vector-fit model was downgraded from `PASS` to `WARN`.
- HSPICE audit confirmed the warning: Clarity passed the slow `500 ps` edge but failed the fast `5 ps` and `50 ps` edges.

## Selected Model

Only one selected vector model exists in this pilot:

`selected_vector_models/Clarity_example_4ef781de.sp`

Candidate:

- `raw_vector_3r3c_lin`
- full scikit-rf vector-fit exported as an ngspice `.SUBCKT s_equivalent ...`
- model order: `9`
- full S-matrix complex RMS error: `4.875e-4`
- RX-path complex RMS error: `3.955e-4`
- reflection complex RMS error: `5.649e-4`
- sampled passive: `True`
- dense high-frequency max singular value: `0.998`

This is a good frequency-domain fit for Clarity, but it is not enough to guarantee fast-edge transient agreement.

## HSPICE Audit Result

The HSPICE audit used native HSPICE S-element behavior as the reference and compared it to ngspice running the selected vector-fit `.sp`.

| Edge | RX active RMSE | RX active max error | HSPICE audit class | Main reason |
| --- | ---: | ---: | --- | --- |
| `5 ps` | `47.15 mV` | `196.67 mV` | `FAIL` | RX shape error |
| `50 ps` | `23.35 mV` | `98.34 mV` | `FAIL` | RX shape error |
| `500 ps` | `6.42 mV` | `19.63 mV` | `PASS` | shape and timing passed |

This matches the earlier pattern: vector fitting can look excellent in frequency-domain error, but the fast-edge time-domain response can still diverge from HSPICE.

## Additional Demo Case: Cisco Ch10

To show quality variation, a second vector-fit case was forced through the same HSPICE/ngspice audit even though it was not selected by the quality gates:

- Channel: `Ch10_35_5F3N_f4_cdb7d8f1`
- Candidate: `raw_vector_12r12c_lin`
- Model order: `36`
- RX-path complex RMS fit error: `1.07e-4`
- full S-matrix complex RMS fit error: `8.51e-2`
- reflection/S11-side complex RMS fit error: `1.67e-1`

This candidate is useful because it demonstrates a mixed-quality fit: the RX-through path is very close in both frequency-domain fit and HSPICE RX waveform shape, but the full multiport/reflection fit is poor enough that the candidate was correctly rejected as a general full-model replacement.

HSPICE audit for the forced Ch10 case:

| Edge | RX active RMSE | RX active max error | HSPICE audit class | Main reason |
| --- | ---: | ---: | --- | --- |
| `5 ps` | `0.045 mV` | `0.163 mV` | `WARN` | voltage passed, timing low-confidence |
| `50 ps` | `0.064 mV` | `0.147 mV` | `WARN` | voltage passed, timing low-confidence |
| `500 ps` | `0.048 mV` | `0.073 mV` | `WARN` | voltage passed, timing low-confidence |

The clean RX agreement here does not make the model `FULL_MODEL_READY`; it shows why path-level trust labels are needed.

## What Worked

- The vector-fit campaign script can now run inventory, fit, ngspice smoke, HSPICE audit, and report generation.
- scikit-rf export produced a valid ngspice-ready `.sp` for the Clarity case.
- The independent smoke check was useful: it downgraded Clarity to `WARN` before HSPICE was consulted.
- HSPICE audit did not change selection; it only calibrated whether the independent classification was trustworthy.

## What Did Not Work

- Higher fixed orders did not rescue the pilot. `5r5c`, `8r8c`, `10r10c`, and `12r12c` produced no selected model.
- `dc_hold` did not help in this pilot.
- `freq_trim_0p9` and `freq_trim_0p75` did not help in this pilot.
- Passivity enforcement did not create a better selected model.
- The two Cisco `.s4p` full vector-fit candidates failed mostly on S-matrix complex RMS and magnitude dB error, sometimes with additional dense singular-value or passivity failures.

## Interpretation

The vector-fit path is not disproven, but this pilot says the simple "fit the whole S-matrix and export it" approach is not yet strong enough for the channels we care about.

For `.s2p` Clarity, the full vector-fit path is promising for slower edges but not yet reliable for sharp transitions.

For Cisco `.s4p`, the full single-ended 4-port vector fit is currently much weaker than the reduced RX-through approach. This likely means the next vector-fit experiments need to address port basis, dominant differential behavior, delay handling, and path weighting instead of only increasing pole count.

## Next Steps

1. Add a vector-fit variant that converts `.s4p` channels into mixed-mode/differential form before fitting, then compare against the current single-ended fit.
2. Add delay extraction/removal before vector fitting, especially for the dominant RX through path, then reinsert delay explicitly in the exported model if possible.
3. Add a path-weighted or staged fit experiment: preserve full-model output, but score and optionally refit with emphasis on `S21/S31` and `S11`.
4. Keep the reduced RX-through model as the current practical RX baseline, because it is still performing better for Cisco RX behavior.
5. Build the next visible report around a side-by-side comparison:
   - reduced RX-through model vs HSPICE
   - full vector-fit model vs HSPICE
   - frequency fit/passivity plots for the vector-fit candidates
   - clear explanation that vector-fit is being developed toward full-model readiness, while reduced models are scoped RX tools.

## Key Files

- `README.md`
- `vf_metrics.csv`
- `vf_ranking.csv`
- `vf_ngspice_smoke.csv`
- `vf_hspice_correlation.csv`
- `vf_calibration_summary.csv`
- `selected_vector_models/Clarity_example_4ef781de.sp`
- `plots/frequency_fit/Clarity_example_4ef781de_raw_vector_3r3c_lin.png`
- `plots/passivity/Clarity_example_4ef781de_raw_vector_3r3c_lin.png`
- `plots/hspice_overlays/Clarity_example_4ef781de_raw_vector_3r3c_lin_audit_amp1p5_edge5_r50.png`
- `plots/hspice_overlays/Clarity_example_4ef781de_raw_vector_3r3c_lin_audit_amp1p5_edge50_r50.png`
- `plots/hspice_overlays/Clarity_example_4ef781de_raw_vector_3r3c_lin_audit_amp1p5_edge500_r50.png`
