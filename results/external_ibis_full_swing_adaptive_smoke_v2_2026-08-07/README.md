# External IBIS Full-Transition Pilot

This study inventories `C:\Users\sh3qm\code\IBIS files` and runs matched HSPICE native-IBIS versus ngspice legacy-pybis full transitions for selected compatible push-pull models.

## Bench

- Typical corner and model-derived supply/reference voltages.
- Input: 50 ps rise/fall, rising at 5 ns.
- High-pulse and recovery durations are model-adaptive: each is at least 125% of the 1%-settling time measured from the model's own IBIS V-t fixtures.
- The output interval remains 1 ps because legacy pybis uses a 10 ps delay-line edge detector; ngspice raw files are binary to keep long runs manageable.
- Load: `50 ohm || 2 pF` to ground.
- HSPICE: native IBIS B-element with Ku/Kd probes.
- ngspice: generated legacy `InputDriven` pybis subcircuit.
- This is a complete-transition compatibility/correlation screen, not a short-pulse test.

## Inventory

- Parsed model rows: `141`; parse failures: `0`.
- `READY_PUSH_PULL`: `86`
- `SKIP_INPUT_ONLY`: `23`
- `SKIP_MISSING_WAVEFORMS`: `21`
- `SKIP_UNSUPPORTED_TYPE`: `11`

## All Results

Selected models: `1`.
- Run status `COMPLETED`: `1`
- Comparison class `GOOD`: `1`

| File | Model | Type | VCC | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---:|---|---|---:|---:|---:|
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | GOOD | 3.925 | 0.0047 | 0.0059 |

## Files

- `inventory.csv`: every parsed model and explicit applicability reason.
- `parse_errors.csv`: malformed/unparsed files, if any.
- `selected_models.csv`: exact campaign selection.
- `metrics.csv`: run status and waveform comparison metrics.
- `cases/<case>/`: copied IBIS, generated pybis model, exact decks, logs, and raw outputs.
- `plots/<case>.png`: pad, Ku, and Kd overlays.

## Interpretation

A failure may mean unsupported IBIS content, pybis extraction limitations, simulator compatibility, or waveform disagreement. It is retained as evidence and is not silently removed.
