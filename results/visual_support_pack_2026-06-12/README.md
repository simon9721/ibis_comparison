# Visual Support Pack

This folder is a presentation-oriented summary of the latest ngspice/HSPICE S-parameter trust work plus the earlier IO buffer IBIS edge-rate study.

## Headline

- Canonical S-parameter study: `results/sparam_rx_trust_v2_2026-06-11`
- IO buffer edge-rate study: `results/io_buf_old_new_four_overlays_2026-06-05`
- Selected S-parameter channels: `149`
- HSPICE audit rows: `93`; valid waveform correlations: `80`
- HSPICE audit PASS/WARN/FAIL/ERROR: `5/68/7/13`
- RX voltage-shape independent PASS vs HSPICE PASS: `21/21`
- Holdout RX voltage-shape PASS vs HSPICE PASS: `3/3`
- RX timing independent PASS produced HSPICE WARN in `3` of `9` audited rows
- Scoped shape-only status `RX_SHAPE_READY_TIMING_WARN`: `7` channels
- Combined `RX_READY` remains `0`; full-model ready remains `0`.

## Figures

- [00_io_buf_edge_rate_study.png](00_io_buf_edge_rate_study.png)
- [01_headline_readiness.png](01_headline_readiness.png)
- [02_independent_pass_vs_hspice.png](02_independent_pass_vs_hspice.png)
- [03_rx_shape_pass_hspice_confirmed.png](03_rx_shape_pass_hspice_confirmed.png)
- [04_delayeq_reduced_4p_examples.png](04_delayeq_reduced_4p_examples.png)
- [05_clarity_fast_edge_mismatch.png](05_clarity_fast_edge_mismatch.png)
- [06_reflection_metric_gap_examples.png](06_reflection_metric_gap_examples.png)
- [07_rx_shape_pass_rx_zoom.png](07_rx_shape_pass_rx_zoom.png)
- [08_delayeq_rx_zoom.png](08_delayeq_rx_zoom.png)
- [09_rx_shape_error_scatter.png](09_rx_shape_error_scatter.png)

## How To Read This

- `RX_SHAPE_READY_TIMING_WARN` means the independent flow predicts RX waveform shape well, but threshold timing is not certified.
- Reduced `.s4p` models are scoped to matched-50-ohm RX-through behavior; they are not full 4-port replacements.
- HSPICE audit rows marked `ERROR` are missing native HSPICE `.tr0` data, not ngspice waveform mismatches.

## Candidate Family Audit Rows

- `full_vector_fit`: `9` audited rows
- `reduced_4p_rx_delayeq_rc_ring`: `15` audited rows
- `reduced_4p_rx_dominant_delay_rc`: `69` audited rows

## Example Overlay Index

See `visual_case_examples.csv` for the exact channel/case list and copied overlay paths.

- `rx_shape_pass`: `Ch3_17_8F_f7_49b5a47c` `audit_amp1p5_edge50_r50` status `RX_SHAPE_READY_TIMING_WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/rx_shape_pass/Ch3_17_8F_f7_49b5a47c_audit_amp1p5_edge50_r50.png`
- `rx_shape_pass`: `Ch10_35_5F3N_f4_fc94db99` `audit_amp1p5_edge50_r50` status `RX_SHAPE_READY_TIMING_WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/rx_shape_pass/Ch10_35_5F3N_f4_fc94db99_audit_amp1p5_edge50_r50.png`
- `rx_shape_pass`: `Ch10_35_8F_f4_71660fc2` `audit_amp1p5_edge50_r50` status `RX_SHAPE_READY_TIMING_WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/rx_shape_pass/Ch10_35_8F_f4_71660fc2_audit_amp1p5_edge50_r50.png`
- `rx_shape_pass`: `Ch3_17_5F3N_f3_c08ef229` `audit_amp1p5_edge50_r50` status `RX_SHAPE_READY_TIMING_WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/rx_shape_pass/Ch3_17_5F3N_f3_c08ef229_audit_amp1p5_edge50_r50.png`
- `rx_shape_pass`: `Ch3_17_5F3N_f4_efc6aab7` `audit_amp1p5_edge50_r50` status `RX_SHAPE_READY_TIMING_WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/rx_shape_pass/Ch3_17_5F3N_f4_efc6aab7_audit_amp1p5_edge50_r50.png`
- `rx_shape_pass`: `Ch3_17_8F_f3_00c873e8` `audit_amp1p5_edge50_r50` status `RX_SHAPE_READY_TIMING_WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/rx_shape_pass/Ch3_17_8F_f3_00c873e8_audit_amp1p5_edge50_r50.png`
- `delayeq_rx_shape_pass`: `Ch8_30_8F_f7_dca3d683` `audit_amp1p5_edge50_r50` status `WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/delayeq_rx_shape_pass/Ch8_30_8F_f7_dca3d683_audit_amp1p5_edge50_r50.png`
- `delayeq_rx_shape_pass`: `Ch9_33_8F_f4_a831b05b` `audit_amp1p5_edge50_r50` status `WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/delayeq_rx_shape_pass/Ch9_33_8F_f4_a831b05b_audit_amp1p5_edge50_r50.png`
- `delayeq_rx_shape_pass`: `Ch8_30_5F3N_f3_5fb04c7e` `audit_amp1p5_edge50_r50` status `WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/delayeq_rx_shape_pass/Ch8_30_5F3N_f3_5fb04c7e_audit_amp1p5_edge50_r50.png`
- `delayeq_rx_shape_pass`: `Ch8_30_8F_f3_9c3ef384` `audit_amp1p5_edge50_r50` status `WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/delayeq_rx_shape_pass/Ch8_30_8F_f3_9c3ef384_audit_amp1p5_edge50_r50.png`
- `delayeq_rx_shape_pass`: `Ch9_33_5F3N_f4_dd88a4a4` `audit_amp1p5_edge50_r50` status `WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/delayeq_rx_shape_pass/Ch9_33_5F3N_f4_dd88a4a4_audit_amp1p5_edge50_r50.png`
- `clarity_fast_edge_fail`: `Clarity_example_acf20e4a` `audit_amp1p5_edge50_r50` status `RX_WARN_VOLTAGE_MARGIN`, HSPICE RX shape/timing `FAIL/PASS`, overlay `example_overlays/clarity_fast_edge_fail/Clarity_example_acf20e4a_audit_amp1p5_edge50_r50.png`
- `reflection_metric_gap`: `Ch10_35_5F3N_f5_3a904f20` `audit_amp1p5_edge50_r50` status `WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/reflection_metric_gap/Ch10_35_5F3N_f5_3a904f20_audit_amp1p5_edge50_r50.png`
- `reflection_metric_gap`: `Ch1_10_5F3N_f2_47dc69c2` `audit_amp1p5_edge50_r50` status `WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/reflection_metric_gap/Ch1_10_5F3N_f2_47dc69c2_audit_amp1p5_edge50_r50.png`
- `reflection_metric_gap`: `Ch2_12_5F3N_f4_5d940b85` `audit_amp1p5_edge50_r50` status `WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/reflection_metric_gap/Ch2_12_5F3N_f4_5d940b85_audit_amp1p5_edge50_r50.png`
- `reflection_metric_gap`: `Ch3_17_8F_f7_49b5a47c` `audit_amp1p5_edge50_r50` status `RX_SHAPE_READY_TIMING_WARN`, HSPICE RX shape/timing `PASS/WARN`, overlay `example_overlays/reflection_metric_gap/Ch3_17_8F_f7_49b5a47c_audit_amp1p5_edge50_r50.png`
