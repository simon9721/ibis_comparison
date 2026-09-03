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

Selected models: `16`.
- Run status `COMPLETED`: `15`
- Run status `CONVERSION_OR_ANALYSIS_FAIL`: `1`
- Comparison class `CHECK`: `5`
- Comparison class `GOOD`: `7`
- Comparison class `WARN`: `3`

| File | Model | Type | VCC | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---:|---|---|---:|---:|---:|
| buffer.ibs | driver | Output | 3.30 | CONVERSION_OR_ANALYSIS_FAIL |  | n/a | n/a | n/a |
| hct1g08.ibs | HCT1G08_OUTN_50 | Output | 5.00 | COMPLETED | GOOD | 56.762 | 0.0131 | 0.0170 |
| invchain_test_0615_v5.ibs | driver2 | Output | 1.80 | COMPLETED | CHECK | 140.094 | 0.1360 | 0.1328 |
| io_buf.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 10.360 | 0.0091 | 0.0130 |
| io_buf_s_v32.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 12.947 | 0.0116 | 0.0155 |
| io_buf_s_v42.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 11.402 | 0.0103 | 0.0133 |
| sample1.ibs | BPOZ2F | 3-state | 3.30 | COMPLETED | CHECK | 142.503 | 0.6603 | 0.3744 |
| sample1.ibs | BPS2P10F_PU50K | I/O | 3.30 | COMPLETED | CHECK | 233.485 | 1.4786 | 2.2962 |
| sample2.ibs | O_SSTL2 | Output | 3.30 | COMPLETED | WARN | 27.515 | 0.0317 | 0.0301 |
| sample2.ibs | XYZ123sstl3 | Output | 3.30 | COMPLETED | WARN | 32.714 | 0.0271 | 0.0282 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_33 | I/O | 3.30 | COMPLETED | GOOD | 38.683 | 0.0473 | 0.0363 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_18 | I/O | 1.80 | COMPLETED | WARN | 30.208 | 0.0531 | 0.0249 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft | I/O | 3.30 | COMPLETED | CHECK | 829.242 | 0.3825 | 0.0270 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft | I/O | 3.30 | COMPLETED | GOOD | 22.083 | 0.0115 | 0.0221 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed | I/O | 3.30 | COMPLETED | GOOD | 16.872 | 0.0138 | 0.0314 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed | I/O | 3.30 | COMPLETED | CHECK | 324.476 | 0.2041 | 0.7473 |

## Files

- `inventory.csv`: every parsed model and explicit applicability reason.
- `parse_errors.csv`: malformed/unparsed files, if any.
- `selected_models.csv`: exact campaign selection.
- `metrics.csv`: run status and waveform comparison metrics.
- `cases/<case>/`: copied IBIS, generated pybis model, exact decks, logs, and raw outputs.
- `plots/<case>.png`: pad, Ku, and Kd overlays.

## Interpretation

A failure may mean unsupported IBIS content, pybis extraction limitations, simulator compatibility, or waveform disagreement. It is retained as evidence and is not silently removed.
