# External IBIS Full-Transition Campaign

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
- Unique applicable models selected: `84` of `86` (exact duplicate files suppressed).

## All Results

Selected models: `84`.
- Run status `COMPLETED`: `82`
- Run status `CONVERSION_OR_ANALYSIS_FAIL`: `1`
- Run status `NGSPICE_TIMEOUT`: `1`
- Comparison class `CHECK`: `5`
- Comparison class `GOOD`: `69`
- Comparison class `WARN`: `8`
- `GOOD` share of completed comparisons: `84.1%`.

## Explicit Failures

- `buffer.ibs / driver`: `CONVERSION_OR_ANALYSIS_FAIL` - RuntimeError: pybis2spice conversion failed with return code 1; Falling coefficient extraction: LinAlgError: Singular matrix
- `stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_lowspeed_pu`: `NGSPICE_TIMEOUT` - ngspice timeout

## Results By File

| File | GOOD | WARN | CHECK | Failed run |
|---|---:|---:|---:|---:|
| buffer.ibs | 0 | 0 | 0 | 1 |
| hct1g08.ibs | 1 | 0 | 0 | 0 |
| inv_s2i.ibs | 0 | 1 | 0 | 0 |
| inv_t2b.ibs | 1 | 0 | 0 | 0 |
| invchain_test_0615_v5.ibs | 1 | 0 | 0 | 0 |
| io_buf.ibs | 1 | 0 | 0 | 0 |
| io_buf_s2i_7_1.ibs | 1 | 0 | 0 | 0 |
| io_buf_s_v32.ibs | 1 | 0 | 0 | 0 |
| io_buf_s_v42.ibs | 1 | 0 | 0 | 0 |
| io_buf_t2b_7_1.ibs | 0 | 1 | 0 | 0 |
| sample1(original).ibs | 5 | 2 | 0 | 0 |
| sample1.ibs | 0 | 2 | 5 | 0 |
| sample2.ibs | 2 | 0 | 0 | 0 |
| sn74lvc2t45.ibs | 6 | 2 | 0 | 0 |
| stm32g031_041_ufqfpn32.ibs | 47 | 0 | 0 | 1 |
| t2b_0616.ibs | 1 | 0 | 0 | 0 |
| test.ibs | 1 | 0 | 0 | 0 |

| File | Model | Type | VCC | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---:|---|---|---:|---:|---:|
| buffer.ibs | driver | Output | 3.30 | CONVERSION_OR_ANALYSIS_FAIL |  | n/a | n/a | n/a |
| hct1g08.ibs | HCT1G08_OUTN_50 | Output | 5.00 | COMPLETED | GOOD | 24.287 | 0.0060 | 0.0056 |
| inv_s2i.ibs | driver3 | Output | 1.80 | COMPLETED | WARN | 33.592 | 0.0465 | 0.0436 |
| inv_t2b.ibs | driver3 | Output | 1.80 | COMPLETED | GOOD | 14.455 | 0.0148 | 0.0140 |
| invchain_test_0615_v5.ibs | driver2 | Output | 1.80 | COMPLETED | GOOD | 14.455 | 0.0148 | 0.0140 |
| io_buf.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 6.868 | 0.0061 | 0.0057 |
| io_buf_s2i_7_1.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 11.028 | 0.0165 | 0.0174 |
| io_buf_s_v32.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 7.222 | 0.0065 | 0.0059 |
| io_buf_s_v42.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 6.810 | 0.0061 | 0.0057 |
| io_buf_t2b_7_1.ibs | driver | I/O | 3.30 | COMPLETED | WARN | 40.751 | 0.0222 | 0.0154 |
| sample1(original).ibs | BPOZ2F | 3-state | 3.30 | COMPLETED | GOOD | 4.350 | 0.0071 | 0.0187 |
| sample1(original).ibs | BPOZ4F | 3-state | 3.30 | COMPLETED | GOOD | 9.851 | 0.0143 | 0.0211 |
| sample1(original).ibs | BPS2P10F_PU50K | I/O | 3.30 | COMPLETED | GOOD | 45.212 | 0.0155 | 0.0201 |
| sample1(original).ibs | BPS2P4F_PD50K | I/O | 3.30 | COMPLETED | GOOD | 9.997 | 0.0127 | 0.0225 |
| sample1(original).ibs | BPS2P4F_PU50K | I/O | 3.30 | COMPLETED | GOOD | 11.676 | 0.0157 | 0.0259 |
| sample1(original).ibs | BT2Z50CX | I/O | 3.30 | COMPLETED | WARN | 32.812 | 0.0119 | 0.0088 |
| sample1(original).ibs | BT2Z50CX_PU50K | I/O | 3.30 | COMPLETED | WARN | 32.290 | 0.0107 | 0.0117 |
| sample1.ibs | BPOZ2F | 3-state | 3.30 | COMPLETED | CHECK | 51.543 | 0.1663 | 0.0892 |
| sample1.ibs | BPOZ4F | 3-state | 3.30 | COMPLETED | CHECK | 61.701 | 0.8784 | 0.5799 |
| sample1.ibs | BPS2P10F_PU50K | I/O | 3.30 | COMPLETED | CHECK | 75.085 | 0.2080 | 0.3229 |
| sample1.ibs | BPS2P4F_PD50K | I/O | 3.30 | COMPLETED | CHECK | 60.051 | 0.8148 | 0.5422 |
| sample1.ibs | BPS2P4F_PU50K | I/O | 3.30 | COMPLETED | CHECK | 51.587 | 0.1632 | 0.0949 |
| sample1.ibs | BT2Z50CX | I/O | 3.30 | COMPLETED | WARN | 32.812 | 0.0119 | 0.0088 |
| sample1.ibs | BT2Z50CX_PU50K | I/O | 3.30 | COMPLETED | WARN | 32.044 | 0.0100 | 0.0120 |
| sample2.ibs | O_SSTL2 | Output | 3.30 | COMPLETED | GOOD | 12.876 | 0.0097 | 0.0084 |
| sample2.ibs | XYZ123sstl3 | Output | 3.30 | COMPLETED | GOOD | 15.591 | 0.0104 | 0.0088 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_18 | I/O | 1.80 | COMPLETED | WARN | 30.127 | 0.0450 | 0.0165 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_25 | I/O | 2.50 | COMPLETED | GOOD | 32.411 | 0.0458 | 0.0211 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_33 | I/O | 3.30 | COMPLETED | GOOD | 29.120 | 0.0382 | 0.0165 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_50 | I/O | 5.00 | COMPLETED | GOOD | 40.374 | 0.0329 | 0.0236 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_18 | I/O | 1.80 | COMPLETED | WARN | 31.411 | 0.0528 | 0.0221 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_25 | I/O | 2.50 | COMPLETED | GOOD | 32.376 | 0.0461 | 0.0209 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_33 | I/O | 3.30 | COMPLETED | GOOD | 28.970 | 0.0395 | 0.0191 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_50 | I/O | 5.00 | COMPLETED | GOOD | 41.514 | 0.0335 | 0.0233 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | GOOD | 3.925 | 0.0047 | 0.0059 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pu_lv | I/O | 1.80 | COMPLETED | GOOD | 3.636 | 0.0043 | 0.0060 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_lv | I/O | 1.80 | COMPLETED | GOOD | 4.511 | 0.0056 | 0.0032 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd | I/O | 3.30 | COMPLETED | GOOD | 21.983 | 0.0117 | 0.0174 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pu | I/O | 3.30 | COMPLETED | GOOD | 10.621 | 0.0047 | 0.0107 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft | I/O | 3.30 | COMPLETED | GOOD | 29.414 | 0.0136 | 0.0113 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | GOOD | 2.402 | 0.0036 | 0.0061 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pu_lv | I/O | 1.80 | COMPLETED | GOOD | 2.507 | 0.0037 | 0.0059 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_lv | I/O | 1.80 | COMPLETED | GOOD | 2.443 | 0.0038 | 0.0058 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pd | I/O | 3.30 | COMPLETED | GOOD | 9.370 | 0.0068 | 0.0077 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pu | I/O | 3.30 | COMPLETED | GOOD | 9.176 | 0.0067 | 0.0075 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft | I/O | 3.30 | COMPLETED | GOOD | 9.387 | 0.0069 | 0.0076 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | GOOD | 1.445 | 0.0019 | 0.0035 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pu_lv | I/O | 1.80 | COMPLETED | GOOD | 1.849 | 0.0023 | 0.0026 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_lv | I/O | 1.80 | COMPLETED | GOOD | 1.437 | 0.0019 | 0.0022 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pd | I/O | 3.30 | COMPLETED | GOOD | 5.728 | 0.0035 | 0.0043 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pu | I/O | 3.30 | COMPLETED | GOOD | 5.427 | 0.0035 | 0.0037 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft | I/O | 3.30 | COMPLETED | GOOD | 5.864 | 0.0038 | 0.0040 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pd_lv | I/O | 1.80 | COMPLETED | GOOD | 1.987 | 0.0033 | 0.0036 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pu_lv | I/O | 1.80 | COMPLETED | GOOD | 3.310 | 0.0057 | 0.0039 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_lv | I/O | 1.80 | COMPLETED | GOOD | 1.869 | 0.0034 | 0.0029 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pd | I/O | 3.30 | COMPLETED | GOOD | 10.291 | 0.0049 | 0.0067 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pu | I/O | 3.30 | COMPLETED | GOOD | 10.077 | 0.0051 | 0.0066 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft | I/O | 3.30 | COMPLETED | GOOD | 10.301 | 0.0052 | 0.0066 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed_pd | I/O | 1.80 | COMPLETED | GOOD | 1.834 | 0.0036 | 0.0058 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed_pd | I/O | 1.80 | COMPLETED | GOOD | 1.516 | 0.0028 | 0.0050 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed_pd | I/O | 1.80 | COMPLETED | GOOD | 1.188 | 0.0024 | 0.0052 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed_pd | I/O | 1.80 | COMPLETED | GOOD | 1.219 | 0.0025 | 0.0054 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed_pu | I/O | 1.80 | COMPLETED | GOOD | 2.430 | 0.0042 | 0.0040 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed_pu | I/O | 1.80 | COMPLETED | GOOD | 2.090 | 0.0039 | 0.0033 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed_pu | I/O | 1.80 | COMPLETED | GOOD | 2.137 | 0.0037 | 0.0032 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed_pu | I/O | 1.80 | NGSPICE_TIMEOUT |  | n/a | n/a | n/a |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed | I/O | 1.80 | COMPLETED | GOOD | 1.813 | 0.0035 | 0.0036 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed | I/O | 1.80 | COMPLETED | GOOD | 1.482 | 0.0028 | 0.0027 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed | I/O | 1.80 | COMPLETED | GOOD | 1.289 | 0.0021 | 0.0026 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed | I/O | 1.80 | COMPLETED | GOOD | 1.128 | 0.0013 | 0.0045 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed_pd | I/O | 3.30 | COMPLETED | GOOD | 8.166 | 0.0054 | 0.0089 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed_pd | I/O | 3.30 | COMPLETED | GOOD | 7.132 | 0.0050 | 0.0083 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed_pd | I/O | 3.30 | COMPLETED | GOOD | 4.796 | 0.0053 | 0.0063 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed_pd | I/O | 3.30 | COMPLETED | GOOD | 3.720 | 0.0025 | 0.0055 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed_pu | I/O | 3.30 | COMPLETED | GOOD | 8.087 | 0.0054 | 0.0086 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed_pu | I/O | 3.30 | COMPLETED | GOOD | 7.032 | 0.0050 | 0.0080 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed_pu | I/O | 3.30 | COMPLETED | GOOD | 5.423 | 0.0038 | 0.0044 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed_pu | I/O | 3.30 | COMPLETED | GOOD | 8.729 | 0.0094 | 0.0051 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed | I/O | 3.30 | COMPLETED | GOOD | 8.156 | 0.0055 | 0.0085 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed | I/O | 3.30 | COMPLETED | GOOD | 6.996 | 0.0053 | 0.0079 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed | I/O | 3.30 | COMPLETED | GOOD | 4.777 | 0.0034 | 0.0041 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed | I/O | 3.30 | COMPLETED | GOOD | 3.682 | 0.0026 | 0.0058 |
| t2b_0616.ibs | driver2 | Output | 1.80 | COMPLETED | GOOD | 15.151 | 0.0146 | 0.0142 |
| test.ibs | driver | I/O | 3.30 | COMPLETED | GOOD | 7.967 | 0.0091 | 0.0060 |

## Files

- `inventory.csv`: every parsed model and explicit applicability reason.
- `parse_errors.csv`: malformed/unparsed files, if any.
- `selected_models.csv`: exact campaign selection.
- `metrics.csv`: run status and waveform comparison metrics.
- `cases/<case>/`: copied IBIS, generated pybis model, exact decks, logs, and raw outputs.
- `plots/<case>.png`: pad, Ku, and Kd overlays.
- `plots/summary_outcomes.png`: campaign counts.
- `plots/summary_error_scatter.png`: pad error versus coefficient error.
- `plots/summary_timing_coverage.png`: agreement versus required model settling time.
- `FAILURE_INVESTIGATION.md`: retained root-cause analysis for the two incomplete comparisons.

## Interpretation

- `GOOD`: pad RMSE <= 2% of HSPICE loaded swing and both Ku/Kd RMSE <= 0.05.
- `WARN`: pad RMSE <= 5% and both Ku/Kd RMSE <= 0.10, but the stricter gate was missed.
- `CHECK`: at least one waveform or coefficient metric exceeds the WARN limits.
- Timing deltas are reported in `metrics.csv` but are not used as a class gate in this first full-transition screen.
- A failed run may mean unsupported IBIS content, pybis extraction limitations, or simulator compatibility. It is retained as evidence and is not silently removed.
- The earlier fixed-15-ns campaign is preliminary only: it interrupted slow vendor transitions and must not be used as the full-swing conclusion.
