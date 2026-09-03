# External IBIS Full-Transition Pilot

This study inventories `C:\Users\sh3qm\code\IBIS files` and runs matched HSPICE native-IBIS versus ngspice legacy-pybis full transitions for selected compatible push-pull models.

## Bench

- Typical corner and model-derived supply/reference voltages.
- Input: 50 ps rise/fall, rising at 5 ns, falling at 20.05 ns.
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

## Pilot Results

Selected models: `2`.
- Run status `COMPLETED`: `1`
- Run status `CONVERSION_OR_ANALYSIS_FAIL`: `1`
- Comparison class `GOOD`: `1`

| File | Model | Type | VCC | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---:|---|---|---:|---:|---:|
| buffer.ibs | driver | Output | 3.30 | CONVERSION_OR_ANALYSIS_FAIL |  | n/a | n/a | n/a |
| hct1g08.ibs | HCT1G08_OUTN_50 | Output | 5.00 | COMPLETED | GOOD | 56.762 | 0.0131 | 0.0170 |

## Files

- `inventory.csv`: every parsed model and explicit applicability reason.
- `parse_errors.csv`: malformed/unparsed files, if any.
- `selected_models.csv`: exact campaign selection.
- `metrics.csv`: run status and waveform comparison metrics.
- `cases/<case>/`: copied IBIS, generated pybis model, exact decks, logs, and raw outputs.
- `plots/<case>.png`: pad, Ku, and Kd overlays.

## Interpretation

A failure may mean unsupported IBIS content, pybis extraction limitations, simulator compatibility, or waveform disagreement. It is retained as evidence and is not silently removed.
