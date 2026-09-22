# S-parameter Conversion Quality Study

Generated: 2026-06-08 09:34:19

## Summary

- Candidate metric rows: 330
- Selected channels: 8
- Failed channels: 16
- HSPICE correlation rows: 24
- Successful HSPICE correlations: 21

## Key Files

- `manifest.csv`: Touchstone inventory
- `metrics.csv`: HSPICE-independent fit/passivity metrics
- `ngspice_smoke.csv`: ngspice transient smoke metrics
- `ranking.csv`: selected model per channel
- `hspice_correlation.csv`: HSPICE native S-element audit metrics

## Selected Models

- `Clarity_example_acf20e4a`: `vector_3r3c`, order `9`, RMS `0.0004875`, max SV `0.9984`
- `hfss_twoport_e975fe9f`: `auto_fit`, order `5`, RMS `0.0001147`, max SV `0.9926`
- `ntwk2_e1c16499`: `vector_5r5c`, order `15`, RMS `3.131e-10`, max SV `1`
- `ntwk3_ad74ab42`: `vector_4r4c`, order `12`, RMS `5.57e-10`, max SV `1`
- `ntwk2_24638a5f`: `vector_5r5c`, order `15`, RMS `3.131e-10`, max SV `1`
- `ntwk3_8f8a2430`: `vector_4r4c`, order `12`, RMS `5.57e-10`, max SV `1`
- `thru_a0b4754f`: `vector_1r1c`, order `3`, RMS `1.43e-16`, max SV `1`
- `Clarity_example_4669a7eb`: `vector_3r3c`, order `9`, RMS `0.0004875`, max SV `0.9984`

## Failed Channels

- `Agilent_E5071B_4f4fd1d7`: no candidate passed math + ngspice gates
- `cst_example_4ports_e82e6e67`: no candidate passed math + ngspice gates
- `designer_variable_coupler_ideal_20deg_e31d0708`: no candidate passed math + ngspice gates
- `designer_variable_coupler_ideal_75deg_50e48e76`: no candidate passed math + ngspice gates
- `fet_7e5200ad`: no candidate passed math + ngspice gates
- `LFCN-2352__Plus125degC_4793e65c`: no candidate passed math + ngspice gates
- `LFCN-2352__Plus25degC_d04142bc`: no candidate passed math + ngspice gates
- `ntwk1_f450e450`: no candidate passed math + ngspice gates
- `ntwk4_806cfc7d`: no candidate passed math + ngspice gates
- `ntwk4_n_6d3c414e`: no candidate passed math + ngspice gates
- `ntwk_arbitrary_frequency_3e8760a8`: no candidate passed math + ngspice gates
- `ntwk_noise_65eeb4e4`: no candidate passed math + ngspice gates
- `ntwk_noise_interp_a132609e`: no candidate passed math + ngspice gates
- `ntwk1_e20029da`: no candidate passed math + ngspice gates
- `RS_ZNB8_23e14c3f`: no candidate passed math + ngspice gates
- `RS_ZVR_1.20_beta_f_6cd9e598`: no candidate passed math + ngspice gates
