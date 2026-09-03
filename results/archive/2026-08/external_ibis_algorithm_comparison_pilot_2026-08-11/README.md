# External IBIS Algorithm Comparison

This package places the full-swing result and all interrupted-transition algorithm figures together for each IBIS model.

## Algorithms

- `legacy`: existing InputDriven table replay baseline.
- `value_match_v2`: corrected value-matched opposite-table replay.
- `gate_state_full`: directional+rate-residual gate-state model used for all transitions.
- `gate_state_hybrid`: legacy normal behavior with directional+rate-residual gate-state handling during interruption.

## Coverage

- Applicable models: `4`.
- `value_match_v2`: completed `7` / `8`; GOOD/WARN/CHECK `2`/`1`/`4`.
- `gate_state_full`: completed `7` / `8`; GOOD/WARN/CHECK `0`/`2`/`5`.
- `gate_state_hybrid`: completed `7` / `8`; GOOD/WARN/CHECK `2`/`1`/`4`.

## Files

- `simulated_ibis_models.csv` and `SIMULATED_IBIS_MODELS.md`: exact file/model inventory and status.
- `algorithm_metrics.csv`: per-algorithm stress metrics.
- `figures/<case>/00_full_swing.png`: full-swing baseline.
- `figures/<case>/01_short_high_algorithms.png`: fall-after-rise algorithms.
- `figures/<case>/02_short_low_algorithms.png`: rise-after-fall algorithms.
- `cases/<case>/<direction>/<algorithm>/`: generated subcircuit, deck, raw, and log.

## Explicit Failures

- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_lv / short_high / gate_state_full`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_lv / short_low / value_match_v2`: `NGSPICE_TIMEOUT` - ngspice timeout
- `stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_lv / short_low / gate_state_hybrid`: `NGSPICE_TIMEOUT` - ngspice timeout
