# External IBIS Algorithm Comparison

This package places the full-swing result and all interrupted-transition algorithm figures together for each IBIS model.

## Headline Findings

- No experimental algorithm is a universal winner across all models and both reversal directions.
- `value_match_v2` versus legacy on `129` paired completed cases: class improved/same/worse `11`/`112`/`6`.
- `gate_state_full` versus legacy on `131` paired completed cases: class improved/same/worse `69`/`54`/`8`.
- `gate_state_hybrid` versus legacy on `125` paired completed cases: class improved/same/worse `58`/`65`/`2`.
- Gate-state full produces the most class improvements; gate-state hybrid has the fewest class regressions. Value matching is usually unchanged from legacy.
- Timeout rows are numerical-availability findings, not waveform CHECK classifications; no missing curve is counted as a fit failure.

## Algorithms

- `legacy`: existing InputDriven table replay baseline.
- `value_match_v2`: corrected value-matched opposite-table replay.
- `gate_state_full`: directional+rate-residual gate-state model used for all transitions.
- `gate_state_hybrid`: legacy normal behavior with directional+rate-residual gate-state handling during interruption.

## Coverage

- Applicable models: `84`.
- `value_match_v2`: completed `129` / `168`; GOOD/WARN/CHECK `11`/`11`/`107`.
- `gate_state_full`: completed `131` / `168`; GOOD/WARN/CHECK `27`/`52`/`52`.
- `gate_state_hybrid`: completed `125` / `168`; GOOD/WARN/CHECK `23`/`49`/`53`.

## Files

- `simulated_ibis_models.csv` and `SIMULATED_IBIS_MODELS.md`: exact file/model inventory and status.
- `algorithm_metrics.csv`: per-algorithm stress metrics.
- `algorithm_summary.csv`: completion and class counts by algorithm/direction.
- `algorithm_vs_legacy.csv`: paired class improvement/same/regression counts.
- `figures/<case>/00_full_swing.png`: full-swing baseline.
- `figures/<case>/01_short_high_algorithms.png`: fall-after-rise algorithms.
- `figures/<case>/02_short_low_algorithms.png`: rise-after-fall algorithms.
- `cases/<case>/<direction>/<algorithm>/`: generated subcircuit, deck, raw, and log.

## Explicit Failures

- `buffer.ibs / driver / short_high / value_match_v2`: `CONVERSION_FAIL` - RuntimeError: pybis2spice conversion failed with return code 1
- `buffer.ibs / driver / short_high / gate_state_full`: `CONVERSION_FAIL` - RuntimeError: pybis2spice conversion failed with return code 1
- `buffer.ibs / driver / short_high / gate_state_hybrid`: `CONVERSION_FAIL` - RuntimeError: pybis2spice conversion failed with return code 1
- `buffer.ibs / driver / short_low / value_match_v2`: `CONVERSION_FAIL` - RuntimeError: pybis2spice conversion failed with return code 1
- `buffer.ibs / driver / short_low / gate_state_full`: `CONVERSION_FAIL` - RuntimeError: pybis2spice conversion failed with return code 1
- `buffer.ibs / driver / short_low / gate_state_hybrid`: `CONVERSION_FAIL` - RuntimeError: pybis2spice conversion failed with return code 1
- `io_buf_s2i_7_1.ibs / driver / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `sn74lvc2t45.ibs / LVC2T45_IO_A_18 / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `sn74lvc2t45.ibs / LVC2T45_IO_B_18 / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd_lv / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd_lv / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd_lv / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd_lv / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd_lv / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd_lv / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu_lv / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu_lv / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu_lv / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu_lv / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu_lv / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu_lv / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_lv / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_lv / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_lv / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_lv / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_lv / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_lv / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu / short_high / gate_state_full`: `NGSPICE_FAIL` - ngspice return code 4294967295
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_pd_lv / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_pu_lv / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_lv / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pd_lv / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pd_lv / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pd_lv / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pu_lv / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pu_lv / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pu_lv / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pu_lv / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_lv / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_lv / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_lv / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_lv / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pd / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pu / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed_pd / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pd / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pd / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pd / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pd / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pd / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pd / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pd / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pd / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pd / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pd / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pd / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pd / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_highspeed_pu / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed_pu / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed_pu / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed_pu / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pu / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pu / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pu / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pu / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pu / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pu / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pu / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pu / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pu / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pu / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pu / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pd / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pd / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pd / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pd / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pd / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pd / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_mediumspeed_pu / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_mediumspeed_pu / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pu / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pu / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pu / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pu / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pu / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pu / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_mediumspeed / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed / short_high / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed / short_high / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed / short_low / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
