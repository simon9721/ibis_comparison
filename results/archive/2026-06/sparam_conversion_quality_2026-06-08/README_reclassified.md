# Reclassified S-parameter Quality Results

## Updated Gates

- Low-frequency coverage: first Touchstone point must be <= `5e+09` Hz
- Minimum frequency points: `8`
- HSPICE waveform pass: Rx RMSE <= `0.1` V and abs 50% delay deltas <= `25` ps

## Summary

- Metric PASS channels: 6
- Metric FAIL channels: 18
- HSPICE channel PASS: 6
- HSPICE channel FAIL: 1
- HSPICE NO_AUDIT channels: 17
- Overall channel PASS: 6
- Overall channel FAIL: 18
- Overall channel NO_AUDIT: 0

## Channel Classification

| Channel | Selected Model | Metric | HSPICE | Overall | Reason |
|---|---|---|---|---|---|
| `Agilent_E5071B_4f4fd1d7` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `Clarity_example_acf20e4a` | `vector_3r3c` | `PASS` | `PASS` | `PASS` | metric and HSPICE audit passed |
| `cst_example_4ports_e82e6e67` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `designer_variable_coupler_ideal_20deg_e31d0708` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | too_few_frequency_points:1<8; no candidate passed math + ngspice gates |
| `designer_variable_coupler_ideal_75deg_50e48e76` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | too_few_frequency_points:1<8; no candidate passed math + ngspice gates |
| `fet_7e5200ad` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | low_frequency_coverage:3e+10>5e+09Hz; no candidate passed math + ngspice gates |
| `hfss_twoport_e975fe9f` | `auto_fit` | `FAIL` | `FAIL` | `FAIL` | low_frequency_coverage:7.5e+10>5e+09Hz |
| `LFCN-2352__Plus125degC_4793e65c` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `LFCN-2352__Plus25degC_d04142bc` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `ntwk1_f450e450` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `ntwk2_e1c16499` | `vector_5r5c` | `PASS` | `PASS` | `PASS` | metric and HSPICE audit passed |
| `ntwk3_ad74ab42` | `vector_4r4c` | `PASS` | `PASS` | `PASS` | metric and HSPICE audit passed |
| `ntwk4_806cfc7d` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | low_frequency_coverage:7e+10>5e+09Hz; no candidate passed math + ngspice gates |
| `ntwk4_n_6d3c414e` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | low_frequency_coverage:7e+10>5e+09Hz; no candidate passed math + ngspice gates |
| `ntwk_arbitrary_frequency_3e8760a8` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | too_few_frequency_points:4<8; no candidate passed math + ngspice gates |
| `ntwk_noise_65eeb4e4` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `ntwk_noise_interp_a132609e` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `ntwk1_e20029da` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `ntwk2_24638a5f` | `vector_5r5c` | `PASS` | `PASS` | `PASS` | metric and HSPICE audit passed |
| `ntwk3_8f8a2430` | `vector_4r4c` | `PASS` | `PASS` | `PASS` | metric and HSPICE audit passed |
| `RS_ZNB8_23e14c3f` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | no candidate passed math + ngspice gates |
| `RS_ZVR_1.20_beta_f_6cd9e598` | `` | `FAIL` | `NO_AUDIT` | `FAIL` | too_few_frequency_points:1<8; no candidate passed math + ngspice gates |
| `thru_a0b4754f` | `vector_1r1c` | `FAIL` | `NO_AUDIT` | `FAIL` | too_few_frequency_points:4<8 |
| `Clarity_example_4669a7eb` | `vector_3r3c` | `PASS` | `PASS` | `PASS` | metric and HSPICE audit passed |

## HSPICE Audit Cases

| Channel | Case | Candidate | Metric | HSPICE | Rx RMSE (V) | Rise Delta (ps) | Fall Delta (ps) |
|---|---|---|---|---|---:|---:|---:|
| `Clarity_example_acf20e4a` | `audit_amp1p5_edge5_r50` | `vector_3r3c` | `PASS` | `PASS` | 0.08387 | 9.899 | 11.15 |
| `Clarity_example_acf20e4a` | `audit_amp1p5_edge50_r50` | `vector_3r3c` | `PASS` | `PASS` | 0.0498 | 11.88 | 12.41 |
| `Clarity_example_acf20e4a` | `audit_amp1p5_edge500_r50` | `vector_3r3c` | `PASS` | `PASS` | 0.006231 | -16.23 | -14.47 |
| `hfss_twoport_e975fe9f` | `audit_amp1p5_edge5_r50` | `auto_fit` | `FAIL` | `FAIL` | 0.2203 | 0.8173 | -1.069 |
| `hfss_twoport_e975fe9f` | `audit_amp1p5_edge50_r50` | `auto_fit` | `FAIL` | `FAIL` | 0.22 | 9.518 | -9.914 |
| `hfss_twoport_e975fe9f` | `audit_amp1p5_edge500_r50` | `auto_fit` | `FAIL` | `FAIL` | 0.2176 | 96.94 | -97.37 |
| `ntwk2_e1c16499` | `audit_amp1p5_edge5_r50` | `vector_5r5c` | `PASS` | `PASS` | 0.002306 | 1.617 | 1.863 |
| `ntwk2_e1c16499` | `audit_amp1p5_edge50_r50` | `vector_5r5c` | `PASS` | `PASS` | 0.0009505 | -0.01556 | -0.009076 |
| `ntwk2_e1c16499` | `audit_amp1p5_edge500_r50` | `vector_5r5c` | `PASS` | `PASS` | 0.000886 | 0.1286 | -0.4771 |
| `ntwk3_ad74ab42` | `audit_amp1p5_edge5_r50` | `vector_4r4c` | `PASS` | `PASS` | 0.00407 | 1.042 | 1.086 |
| `ntwk3_ad74ab42` | `audit_amp1p5_edge50_r50` | `vector_4r4c` | `PASS` | `PASS` | 0.0004573 | 0.3693 | 0.2989 |
| `ntwk3_ad74ab42` | `audit_amp1p5_edge500_r50` | `vector_4r4c` | `PASS` | `PASS` | 0.0002339 | -0.06715 | 0.1732 |
| `ntwk2_24638a5f` | `audit_amp1p5_edge5_r50` | `vector_5r5c` | `PASS` | `PASS` | 0.002306 | 1.617 | 1.863 |
| `ntwk2_24638a5f` | `audit_amp1p5_edge50_r50` | `vector_5r5c` | `PASS` | `PASS` | 0.0009505 | -0.01556 | -0.009076 |
| `ntwk2_24638a5f` | `audit_amp1p5_edge500_r50` | `vector_5r5c` | `PASS` | `PASS` | 0.000886 | 0.1286 | -0.4771 |
| `ntwk3_8f8a2430` | `audit_amp1p5_edge5_r50` | `vector_4r4c` | `PASS` | `PASS` | 0.00407 | 1.042 | 1.086 |
| `ntwk3_8f8a2430` | `audit_amp1p5_edge50_r50` | `vector_4r4c` | `PASS` | `PASS` | 0.0004573 | 0.3693 | 0.2989 |
| `ntwk3_8f8a2430` | `audit_amp1p5_edge500_r50` | `vector_4r4c` | `PASS` | `PASS` | 0.0002339 | -0.06715 | 0.1732 |
| `thru_a0b4754f` | `audit_amp1p5_edge5_r50` | `vector_1r1c` | `FAIL` | `NO_AUDIT` |  |  |  |
| `thru_a0b4754f` | `audit_amp1p5_edge50_r50` | `vector_1r1c` | `FAIL` | `NO_AUDIT` |  |  |  |
| `thru_a0b4754f` | `audit_amp1p5_edge500_r50` | `vector_1r1c` | `FAIL` | `NO_AUDIT` |  |  |  |
| `Clarity_example_4669a7eb` | `audit_amp1p5_edge5_r50` | `vector_3r3c` | `PASS` | `PASS` | 0.08387 | 9.899 | 11.15 |
| `Clarity_example_4669a7eb` | `audit_amp1p5_edge50_r50` | `vector_3r3c` | `PASS` | `PASS` | 0.0498 | 11.88 | 12.41 |
| `Clarity_example_4669a7eb` | `audit_amp1p5_edge500_r50` | `vector_3r3c` | `PASS` | `PASS` | 0.006231 | -16.23 | -14.47 |
