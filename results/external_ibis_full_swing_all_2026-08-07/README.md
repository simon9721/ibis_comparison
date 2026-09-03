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

## All Results

Selected models: `84`.
- Run status `COMPLETED`: `83`
- Run status `CONVERSION_OR_ANALYSIS_FAIL`: `1`
- Comparison class `CHECK`: `37`
- Comparison class `GOOD`: `36`
- Comparison class `WARN`: `10`

| File | Model | Type | VCC | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---:|---|---|---:|---:|---:|
| buffer.ibs | driver | Output | 3.30 | CONVERSION_OR_ANALYSIS_FAIL |  | n/a | n/a | n/a |
| hct1g08.ibs | HCT1G08_OUTN_50 | Output | 5.00 | COMPLETED | GOOD | 56.762 | 0.0131 | 0.0170 |
| inv_s2i.ibs | driver3 | Output | 1.80 | COMPLETED | CHECK | 300.046 | 0.5078 | 0.5136 |
| inv_t2b.ibs | driver3 | Output | 1.80 | COMPLETED | CHECK | 140.094 | 0.1360 | 0.1328 |
| invchain_test_0615_v5.ibs | driver2 | Output | 1.80 | COMPLETED | CHECK | 140.094 | 0.1360 | 0.1328 |
| io_buf.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 10.360 | 0.0091 | 0.0130 |
| io_buf_s2i_7_1.ibs | driver | I/O | 3.30 | COMPLETED | WARN | 20.847 | 0.0528 | 0.0718 |
| io_buf_s_v32.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 12.947 | 0.0116 | 0.0155 |
| io_buf_s_v42.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 11.402 | 0.0103 | 0.0133 |
| io_buf_t2b_7_1.ibs | driver | I/O | 3.30 | COMPLETED | CHECK | 62.838 | 0.2081 | 0.0427 |
| sample1(original).ibs | BPOZ2F | 3-state | 3.30 | COMPLETED | GOOD | 5.908 | 0.0084 | 0.0308 |
| sample1(original).ibs | BPOZ4F | 3-state | 3.30 | COMPLETED | CHECK | 21.309 | 0.0705 | 0.1056 |
| sample1(original).ibs | BPS2P10F_PU50K | I/O | 3.30 | COMPLETED | CHECK | 159.539 | 0.0273 | 0.0399 |
| sample1(original).ibs | BPS2P4F_PD50K | I/O | 3.30 | COMPLETED | GOOD | 20.248 | 0.0299 | 0.0478 |
| sample1(original).ibs | BPS2P4F_PU50K | I/O | 3.30 | COMPLETED | WARN | 24.487 | 0.0317 | 0.0986 |
| sample1(original).ibs | BT2Z50CX | I/O | 3.30 | COMPLETED | CHECK | 113.509 | 0.0268 | 0.0297 |
| sample1(original).ibs | BT2Z50CX_PU50K | I/O | 3.30 | COMPLETED | CHECK | 107.884 | 0.0265 | 0.0282 |
| sample1.ibs | BPOZ2F | 3-state | 3.30 | COMPLETED | CHECK | 142.503 | 0.6603 | 0.3744 |
| sample1.ibs | BPOZ4F | 3-state | 3.30 | COMPLETED | CHECK | 204.363 | 2.5860 | 1.6925 |
| sample1.ibs | BPS2P10F_PU50K | I/O | 3.30 | COMPLETED | CHECK | 233.485 | 1.4786 | 2.2962 |
| sample1.ibs | BPS2P4F_PD50K | I/O | 3.30 | COMPLETED | CHECK | 171.969 | 3.0570 | 2.0331 |
| sample1.ibs | BPS2P4F_PU50K | I/O | 3.30 | COMPLETED | CHECK | 176.222 | 0.6440 | 0.3662 |
| sample1.ibs | BT2Z50CX | I/O | 3.30 | COMPLETED | CHECK | 113.509 | 0.0268 | 0.0297 |
| sample1.ibs | BT2Z50CX_PU50K | I/O | 3.30 | COMPLETED | CHECK | 107.362 | 0.0258 | 0.0281 |
| sample2.ibs | O_SSTL2 | Output | 3.30 | COMPLETED | WARN | 27.515 | 0.0317 | 0.0301 |
| sample2.ibs | XYZ123sstl3 | Output | 3.30 | COMPLETED | WARN | 32.714 | 0.0271 | 0.0282 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_18 | I/O | 1.80 | COMPLETED | WARN | 28.643 | 0.0521 | 0.0307 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_25 | I/O | 2.50 | COMPLETED | WARN | 43.562 | 0.0688 | 0.0441 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_33 | I/O | 3.30 | COMPLETED | GOOD | 38.683 | 0.0473 | 0.0363 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_50 | I/O | 5.00 | COMPLETED | WARN | 94.351 | 0.0660 | 0.0739 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_18 | I/O | 1.80 | COMPLETED | WARN | 30.208 | 0.0531 | 0.0249 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_25 | I/O | 2.50 | COMPLETED | WARN | 42.860 | 0.0690 | 0.0452 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_33 | I/O | 3.30 | COMPLETED | GOOD | 35.327 | 0.0486 | 0.0397 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_50 | I/O | 5.00 | COMPLETED | WARN | 98.988 | 0.0708 | 0.0802 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | CHECK | 293.700 | 0.3154 | 0.0206 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pu_lv | I/O | 1.80 | COMPLETED | CHECK | 292.990 | 0.3128 | 0.0198 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_lv | I/O | 1.80 | COMPLETED | CHECK | 283.569 | 0.3045 | 0.0124 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd | I/O | 3.30 | COMPLETED | CHECK | 816.304 | 0.3787 | 0.0435 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pu | I/O | 3.30 | COMPLETED | CHECK | 624.471 | 0.2659 | 0.0253 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft | I/O | 3.30 | COMPLETED | CHECK | 829.242 | 0.3825 | 0.0270 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | GOOD | 7.023 | 0.0106 | 0.0152 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pu_lv | I/O | 1.80 | COMPLETED | GOOD | 5.763 | 0.0093 | 0.0196 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_lv | I/O | 1.80 | COMPLETED | GOOD | 6.191 | 0.0107 | 0.0178 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pd | I/O | 3.30 | COMPLETED | GOOD | 20.323 | 0.0136 | 0.0207 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pu | I/O | 3.30 | COMPLETED | GOOD | 20.840 | 0.0165 | 0.0177 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft | I/O | 3.30 | COMPLETED | GOOD | 22.481 | 0.0192 | 0.0189 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | CHECK | 172.175 | 0.1978 | 0.0184 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pu_lv | I/O | 1.80 | COMPLETED | CHECK | 176.333 | 0.2026 | 0.0154 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_lv | I/O | 1.80 | COMPLETED | CHECK | 180.017 | 0.2039 | 0.0103 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pd | I/O | 3.30 | COMPLETED | GOOD | 14.516 | 0.0107 | 0.0157 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pu | I/O | 3.30 | COMPLETED | GOOD | 14.171 | 0.0113 | 0.0138 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft | I/O | 3.30 | COMPLETED | GOOD | 14.432 | 0.0111 | 0.0166 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | GOOD | 3.437 | 0.0077 | 0.0076 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pu_lv | I/O | 1.80 | COMPLETED | GOOD | 3.175 | 0.0064 | 0.0091 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_lv | I/O | 1.80 | COMPLETED | GOOD | 3.111 | 0.0071 | 0.0076 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pd | I/O | 3.30 | COMPLETED | GOOD | 22.740 | 0.0108 | 0.0216 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pu | I/O | 3.30 | COMPLETED | GOOD | 21.486 | 0.0121 | 0.0228 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft | I/O | 3.30 | COMPLETED | GOOD | 22.083 | 0.0115 | 0.0221 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed_pd | I/O | 1.80 | COMPLETED | GOOD | 3.330 | 0.0079 | 0.0108 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed_pd | I/O | 1.80 | COMPLETED | GOOD | 3.009 | 0.0072 | 0.0112 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed_pd | I/O | 1.80 | COMPLETED | CHECK | 139.909 | 0.2445 | 0.0143 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed_pd | I/O | 1.80 | COMPLETED | CHECK | 124.794 | 0.2199 | 0.9342 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed_pu | I/O | 1.80 | COMPLETED | GOOD | 3.043 | 0.0075 | 0.0076 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed_pu | I/O | 1.80 | COMPLETED | GOOD | 3.182 | 0.0075 | 0.0101 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed_pu | I/O | 1.80 | COMPLETED | CHECK | 141.768 | 0.2450 | 0.0140 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed_pu | I/O | 1.80 | COMPLETED | CHECK | 121.462 | 0.2127 | 0.0181 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed | I/O | 1.80 | COMPLETED | GOOD | 3.247 | 0.0073 | 0.0078 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed | I/O | 1.80 | COMPLETED | GOOD | 2.964 | 0.0071 | 0.0080 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed | I/O | 1.80 | COMPLETED | CHECK | 141.138 | 0.2438 | 0.0135 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed | I/O | 1.80 | COMPLETED | CHECK | 113.773 | 0.1991 | 0.9437 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed_pd | I/O | 3.30 | COMPLETED | GOOD | 16.563 | 0.0118 | 0.0329 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed_pd | I/O | 3.30 | COMPLETED | GOOD | 13.821 | 0.0112 | 0.0305 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed_pd | I/O | 3.30 | COMPLETED | CHECK | 105.362 | 0.0970 | 0.0351 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed_pd | I/O | 3.30 | COMPLETED | CHECK | 351.107 | 0.2091 | 0.7371 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed_pu | I/O | 3.30 | COMPLETED | GOOD | 17.028 | 0.0131 | 0.0315 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed_pu | I/O | 3.30 | COMPLETED | GOOD | 12.972 | 0.0115 | 0.0315 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed_pu | I/O | 3.30 | COMPLETED | CHECK | 95.607 | 0.0704 | 0.0189 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed_pu | I/O | 3.30 | COMPLETED | CHECK | 334.806 | 0.1696 | 0.7478 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed | I/O | 3.30 | COMPLETED | GOOD | 16.872 | 0.0138 | 0.0314 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed | I/O | 3.30 | COMPLETED | GOOD | 14.149 | 0.0118 | 0.0318 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed | I/O | 3.30 | COMPLETED | CHECK | 94.681 | 0.0683 | 0.0224 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed | I/O | 3.30 | COMPLETED | CHECK | 324.476 | 0.2041 | 0.7473 |
| t2b_0616.ibs | driver2 | Output | 1.80 | COMPLETED | CHECK | 152.427 | 0.1118 | 0.1417 |
| test.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 19.478 | 0.0251 | 0.0140 |

## Files

- `inventory.csv`: every parsed model and explicit applicability reason.
- `parse_errors.csv`: malformed/unparsed files, if any.
- `selected_models.csv`: exact campaign selection.
- `metrics.csv`: run status and waveform comparison metrics.
- `cases/<case>/`: copied IBIS, generated pybis model, exact decks, logs, and raw outputs.
- `plots/<case>.png`: pad, Ku, and Kd overlays.

## Interpretation

A failure may mean unsupported IBIS content, pybis extraction limitations, simulator compatibility, or waveform disagreement. It is retained as evidence and is not silently removed.
