# External IBIS Adaptive Stress Campaign

This study reverses each input while its preceding native-IBIS Ku/Kd transition is near 50% composite progress.

## Bench

- Typical corner, model-derived supply/reference voltages, and `50 ohm || 2 pF` load.
- Input rise/fall time remains 50 ps; only pulse timing changes by model and direction.
- `short_high`: falling edge arrives during the preceding rising output transition.
- `short_low`: the input starts high at the DC operating point; a rising edge then arrives during the preceding falling output transition.
- The copied pybis short-low model is held at settled `Ku=1, Kd=0` only through the first falling-edge detector interval; the override is released before the measured reverse edge.
- Stress width is selected from the cached full-transition HSPICE Ku/Kd trajectory; HSPICE is used only to design and validate the stress bench, not to alter pybis.

## Stress Selection

Each coefficient is normalized from its initial value to its settled value. The selection signal is
`progress = 0.5 * (normalized_Ku + normalized_Kd)`; the input reverses at the first monotonic-envelope crossing of `progress=0.5`.
This does not require both coefficients to equal 0.5. A break-before-make interval can have one path already off while the other has not yet turned on.
The stress reruns reproduce the cached coefficient state at reversal within `0.0130` Ku and `0.0143` Kd in the worst case.

## Classification

- `GOOD`: pad RMSE <= 2% of VCC and both coefficient RMSE values <= 0.05.
- `WARN`: pad RMSE <= 5% of VCC and both coefficient RMSE values <= 0.10.
- `CHECK`: any completed comparison outside those limits. It is evidence of disagreement, not a simulator execution failure.

## Results

- Unique applicable models: `84`; requested direction cases: `168`.
- Completed HSPICE/ngspice comparisons: `166`.
- Overall: GOOD `10` (6.0%), WARN `19` (11.4%), CHECK `137` (82.5%).
- `short_high`: GOOD `3`, WARN `8`, CHECK `72`
  Selected width range `0.208..7.260 ns` (median `1.498 ns`); median pad/Ku/Kd RMSE `171.7 mV / 0.161 / 0.092`.
- `short_low`: GOOD `7`, WARN `11`, CHECK `65`
  Selected width range `0.318..11.571 ns` (median `1.676 ns`); median pad/Ku/Kd RMSE `71.1 mV / 0.050 / 0.167`.

## Headline Findings

- Legacy table replay is generally not reliable for a measured mid-transition reversal: `137/166` completed cases require CHECK.
- Failure is not universal. The inverter-derived `inv_t2b`, `invchain_test_0615_v5`, and `t2b_0616` models are GOOD in both directions at about 0.30-0.33 ns.
- `io_buf` and its related variants are CHECK in both directions; their post-reversal coefficient histories visibly diverge even though the state at the reverse edge initially agrees.
- Pulse width alone is not a quality predictor. Similar-width models can be GOOD or CHECK because the opposite-table restart shape and Ku/Kd staging differ by model.
- The narrow coefficient jump at the reverse edge in CHECK plots is the legacy restart behavior under test, not the short-low DC initialization.

## Incomplete Cases

- `buffer.ibs / driver / short_high`: `PYBIS_UNAVAILABLE` - full-transition legacy pybis conversion is unavailable
- `buffer.ibs / driver / short_low`: `PYBIS_UNAVAILABLE` - full-transition legacy pybis conversion is unavailable

## Case Table

| File | Model | Direction | Width ns | Progress | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---:|---:|---|---|---:|---:|---:|
| buffer.ibs | driver | short_high | 0.966 | 0.501 | PYBIS_UNAVAILABLE |  | n/a | n/a | n/a |
| buffer.ibs | driver | short_low | 0.967 | 0.500 | PYBIS_UNAVAILABLE |  | n/a | n/a | n/a |
| hct1g08.ibs | HCT1G08_OUTN_50 | short_high | 0.792 | 0.500 | COMPLETED | CHECK | 469.854 | 0.1337 | 0.1057 |
| hct1g08.ibs | HCT1G08_OUTN_50 | short_low | 1.333 | 0.500 | COMPLETED | CHECK | 633.095 | 0.1966 | 0.1590 |
| inv_s2i.ibs | driver3 | short_high | 0.287 | 0.513 | COMPLETED | WARN | 41.425 | 0.0576 | 0.0599 |
| inv_s2i.ibs | driver3 | short_low | 0.318 | 0.519 | COMPLETED | WARN | 48.740 | 0.0686 | 0.0641 |
| inv_t2b.ibs | driver3 | short_high | 0.296 | 0.512 | COMPLETED | GOOD | 20.088 | 0.0212 | 0.0208 |
| inv_t2b.ibs | driver3 | short_low | 0.327 | 0.509 | COMPLETED | GOOD | 23.261 | 0.0225 | 0.0236 |
| invchain_test_0615_v5.ibs | driver2 | short_high | 0.296 | 0.512 | COMPLETED | GOOD | 20.088 | 0.0212 | 0.0208 |
| invchain_test_0615_v5.ibs | driver2 | short_low | 0.327 | 0.509 | COMPLETED | GOOD | 23.289 | 0.0225 | 0.0236 |
| io_buf.ibs | driver | short_high | 1.854 | 0.500 | COMPLETED | CHECK | 238.246 | 0.1614 | 0.1273 |
| io_buf.ibs | driver | short_low | 1.209 | 0.500 | COMPLETED | CHECK | 148.166 | 0.0901 | 0.3543 |
| io_buf_s2i_7_1.ibs | driver | short_high | 1.295 | 0.500 | COMPLETED | CHECK | 132.895 | 0.0961 | 0.1050 |
| io_buf_s2i_7_1.ibs | driver | short_low | 0.570 | 0.500 | COMPLETED | CHECK | 560.319 | 0.3722 | 0.2929 |
| io_buf_s_v32.ibs | driver | short_high | 1.882 | 0.500 | COMPLETED | CHECK | 236.754 | 0.1600 | 0.1224 |
| io_buf_s_v32.ibs | driver | short_low | 1.247 | 0.500 | COMPLETED | CHECK | 129.298 | 0.0783 | 0.3526 |
| io_buf_s_v42.ibs | driver | short_high | 1.854 | 0.500 | COMPLETED | CHECK | 238.251 | 0.1614 | 0.1273 |
| io_buf_s_v42.ibs | driver | short_low | 1.214 | 0.500 | COMPLETED | CHECK | 145.652 | 0.0885 | 0.3537 |
| io_buf_t2b_7_1.ibs | driver | short_high | 1.313 | 0.500 | COMPLETED | CHECK | 125.913 | 0.1004 | 0.1013 |
| io_buf_t2b_7_1.ibs | driver | short_low | 1.111 | 0.500 | COMPLETED | CHECK | 567.256 | 0.3676 | 0.2868 |
| sample1(original).ibs | BPOZ2F | short_high | 0.208 | 0.500 | COMPLETED | CHECK | 151.870 | 0.2292 | 0.1950 |
| sample1(original).ibs | BPOZ2F | short_low | 0.661 | 0.500 | COMPLETED | GOOD | 14.253 | 0.0194 | 0.0398 |
| sample1(original).ibs | BPOZ4F | short_high | 0.312 | 0.500 | COMPLETED | CHECK | 150.021 | 0.1684 | 0.1734 |
| sample1(original).ibs | BPOZ4F | short_low | 0.602 | 0.500 | COMPLETED | WARN | 31.474 | 0.0269 | 0.0513 |
| sample1(original).ibs | BPS2P10F_PU50K | short_high | 0.326 | 0.502 | COMPLETED | CHECK | 241.085 | 0.0808 | 0.0746 |
| sample1(original).ibs | BPS2P10F_PU50K | short_low | 0.610 | 0.500 | COMPLETED | CHECK | 262.134 | 0.0775 | 0.1252 |
| sample1(original).ibs | BPS2P4F_PD50K | short_high | 0.311 | 0.501 | COMPLETED | CHECK | 150.974 | 0.1714 | 0.1747 |
| sample1(original).ibs | BPS2P4F_PD50K | short_low | 0.611 | 0.500 | COMPLETED | WARN | 31.679 | 0.0273 | 0.0506 |
| sample1(original).ibs | BPS2P4F_PU50K | short_high | 0.312 | 0.500 | COMPLETED | CHECK | 151.043 | 0.1716 | 0.1765 |
| sample1(original).ibs | BPS2P4F_PU50K | short_low | 0.609 | 0.500 | COMPLETED | GOOD | 30.487 | 0.0271 | 0.0484 |
| sample1(original).ibs | BT2Z50CX | short_high | 0.375 | 0.501 | COMPLETED | CHECK | 159.883 | 0.1070 | 0.0820 |
| sample1(original).ibs | BT2Z50CX | short_low | 0.503 | 0.500 | COMPLETED | WARN | 71.516 | 0.0501 | 0.0341 |
| sample1(original).ibs | BT2Z50CX_PU50K | short_high | 0.375 | 0.500 | COMPLETED | CHECK | 160.071 | 0.1074 | 0.0841 |
| sample1(original).ibs | BT2Z50CX_PU50K | short_low | 0.503 | 0.501 | COMPLETED | GOOD | 61.279 | 0.0480 | 0.0293 |
| sample1.ibs | BPOZ2F | short_high | 0.208 | 0.500 | COMPLETED | CHECK | 164.190 | 0.3380 | 0.2366 |
| sample1.ibs | BPOZ2F | short_low | 0.661 | 0.500 | COMPLETED | CHECK | 82.167 | 0.2291 | 0.1176 |
| sample1.ibs | BPOZ4F | short_high | 0.312 | 0.500 | COMPLETED | CHECK | 172.811 | 1.3999 | 0.9327 |
| sample1.ibs | BPOZ4F | short_low | 0.602 | 0.500 | COMPLETED | CHECK | 105.743 | 1.3830 | 0.9289 |
| sample1.ibs | BPS2P10F_PU50K | short_high | 0.326 | 0.502 | COMPLETED | CHECK | 256.019 | 0.3427 | 0.5227 |
| sample1.ibs | BPS2P10F_PU50K | short_low | 0.610 | 0.500 | COMPLETED | CHECK | 313.032 | 0.3641 | 0.5155 |
| sample1.ibs | BPS2P4F_PD50K | short_high | 0.311 | 0.501 | COMPLETED | CHECK | 181.249 | 1.2657 | 0.8531 |
| sample1.ibs | BPS2P4F_PD50K | short_low | 0.611 | 0.500 | COMPLETED | CHECK | 99.008 | 1.2557 | 0.8563 |
| sample1.ibs | BPS2P4F_PU50K | short_high | 0.312 | 0.500 | COMPLETED | CHECK | 162.195 | 0.2991 | 0.2251 |
| sample1.ibs | BPS2P4F_PU50K | short_low | 0.609 | 0.500 | COMPLETED | CHECK | 96.094 | 0.2480 | 0.1458 |
| sample1.ibs | BT2Z50CX | short_high | 0.375 | 0.501 | COMPLETED | CHECK | 159.883 | 0.1070 | 0.0820 |
| sample1.ibs | BT2Z50CX | short_low | 0.503 | 0.500 | COMPLETED | WARN | 71.516 | 0.0501 | 0.0341 |
| sample1.ibs | BT2Z50CX_PU50K | short_high | 0.375 | 0.500 | COMPLETED | CHECK | 160.752 | 0.1078 | 0.0842 |
| sample1.ibs | BT2Z50CX_PU50K | short_low | 0.503 | 0.501 | COMPLETED | GOOD | 60.546 | 0.0476 | 0.0292 |
| sample2.ibs | O_SSTL2 | short_high | 0.523 | 0.501 | COMPLETED | CHECK | 205.846 | 0.2100 | 0.1689 |
| sample2.ibs | O_SSTL2 | short_low | 0.770 | 0.500 | COMPLETED | CHECK | 135.391 | 0.1258 | 0.1721 |
| sample2.ibs | XYZ123sstl3 | short_high | 0.524 | 0.501 | COMPLETED | CHECK | 218.579 | 0.1900 | 0.1548 |
| sample2.ibs | XYZ123sstl3 | short_low | 0.765 | 0.501 | COMPLETED | CHECK | 161.665 | 0.1309 | 0.1855 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_18 | short_high | 7.258 | 0.500 | COMPLETED | CHECK | 163.958 | 0.2267 | 0.0268 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_18 | short_low | 6.601 | 0.500 | COMPLETED | CHECK | 41.043 | 0.0629 | 0.2202 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_25 | short_high | 4.720 | 0.500 | COMPLETED | CHECK | 221.881 | 0.1574 | 0.0294 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_25 | short_low | 4.429 | 0.501 | COMPLETED | CHECK | 61.595 | 0.0485 | 0.1548 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_33 | short_high | 3.604 | 0.501 | COMPLETED | CHECK | 292.296 | 0.1462 | 0.0267 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_33 | short_low | 3.622 | 0.501 | COMPLETED | CHECK | 72.469 | 0.0417 | 0.1076 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_50 | short_high | 2.891 | 0.504 | COMPLETED | CHECK | 342.707 | 0.1177 | 0.0338 |
| sn74lvc2t45.ibs | LVC2T45_IO_A_50 | short_low | 2.938 | 0.500 | COMPLETED | WARN | 120.393 | 0.0374 | 0.0989 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_18 | short_high | 7.260 | 0.500 | COMPLETED | CHECK | 162.807 | 0.2252 | 0.0256 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_18 | short_low | 6.595 | 0.500 | COMPLETED | CHECK | 42.298 | 0.0641 | 0.2179 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_25 | short_high | 4.723 | 0.500 | COMPLETED | CHECK | 219.630 | 0.1562 | 0.0291 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_25 | short_low | 4.429 | 0.501 | COMPLETED | CHECK | 61.362 | 0.0482 | 0.1544 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_33 | short_high | 3.597 | 0.501 | COMPLETED | CHECK | 294.251 | 0.1471 | 0.0293 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_33 | short_low | 3.617 | 0.501 | COMPLETED | CHECK | 74.074 | 0.0399 | 0.1072 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_50 | short_high | 2.869 | 0.502 | COMPLETED | CHECK | 365.195 | 0.1224 | 0.0329 |
| sn74lvc2t45.ibs | LVC2T45_IO_B_50 | short_low | 2.941 | 0.500 | COMPLETED | WARN | 126.090 | 0.0397 | 0.0940 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd_lv | short_high | 3.995 | 0.500 | COMPLETED | CHECK | 81.006 | 0.0874 | 0.4616 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd_lv | short_low | 4.837 | 0.500 | COMPLETED | CHECK | 402.606 | 0.4317 | 0.1102 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pu_lv | short_high | 3.995 | 0.500 | COMPLETED | WARN | 59.543 | 0.0641 | 0.0155 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pu_lv | short_low | 3.551 | 0.500 | COMPLETED | CHECK | 54.536 | 0.0575 | 0.1078 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_lv | short_high | 2.962 | 0.500 | COMPLETED | WARN | 67.353 | 0.0729 | 0.0087 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_lv | short_low | 3.060 | 0.500 | COMPLETED | WARN | 11.008 | 0.0127 | 0.0902 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd | short_high | 2.877 | 0.500 | COMPLETED | CHECK | 260.645 | 0.1088 | 0.4228 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pd | short_low | 2.946 | 0.500 | COMPLETED | CHECK | 650.491 | 0.2571 | 0.1151 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pu | short_high | 2.694 | 0.500 | COMPLETED | CHECK | 148.877 | 0.0537 | 0.4737 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft_pu | short_low | 1.960 | 0.500 | COMPLETED | CHECK | 886.394 | 0.4148 | 0.1054 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft | short_high | 1.929 | 0.500 | COMPLETED | CHECK | 194.655 | 0.0799 | 0.4492 |
| stm32g031_041_ufqfpn32.ibs | iols8p_sudq_ft | short_low | 1.974 | 0.500 | COMPLETED | CHECK | 898.465 | 0.4109 | 0.0794 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pd_lv | short_high | 2.337 | 0.500 | COMPLETED | CHECK | 229.460 | 0.2485 | 0.0877 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pd_lv | short_low | 4.007 | 0.500 | COMPLETED | CHECK | 67.961 | 0.0706 | 0.2399 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pu_lv | short_high | 2.837 | 0.500 | COMPLETED | CHECK | 233.583 | 0.2527 | 0.0752 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pu_lv | short_low | 4.053 | 0.500 | COMPLETED | CHECK | 36.378 | 0.0382 | 0.2742 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_lv | short_high | 2.338 | 0.500 | COMPLETED | CHECK | 232.506 | 0.2512 | 0.0891 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_lv | short_low | 4.029 | 0.500 | COMPLETED | CHECK | 70.648 | 0.0739 | 0.2489 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pd | short_high | 1.503 | 0.500 | COMPLETED | CHECK | 529.002 | 0.2250 | 0.0712 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pd | short_low | 1.625 | 0.500 | COMPLETED | CHECK | 162.690 | 0.0618 | 0.2322 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pu | short_high | 1.502 | 0.500 | COMPLETED | CHECK | 525.490 | 0.2234 | 0.0711 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft_pu | short_low | 1.628 | 0.500 | COMPLETED | CHECK | 174.292 | 0.0664 | 0.2333 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft | short_high | 1.504 | 0.500 | COMPLETED | CHECK | 521.862 | 0.2217 | 0.0708 |
| stm32g031_041_ufqfpn32.ibs | iofs8p_sudq_ft | short_low | 1.623 | 0.500 | COMPLETED | CHECK | 171.232 | 0.0652 | 0.2284 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pd_lv | short_high | 2.460 | 0.500 | COMPLETED | CHECK | 149.841 | 0.1630 | 0.0933 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pd_lv | short_low | 4.827 | 0.500 | COMPLETED | CHECK | 369.401 | 0.3967 | 0.1925 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pu_lv | short_high | 2.462 | 0.500 | COMPLETED | CHECK | 157.646 | 0.1712 | 0.0701 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pu_lv | short_low | 4.963 | 0.500 | COMPLETED | CHECK | 98.243 | 0.1026 | 0.1907 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_lv | short_high | 2.462 | 0.500 | COMPLETED | CHECK | 156.513 | 0.1700 | 0.4958 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_lv | short_low | 4.989 | 0.500 | COMPLETED | CHECK | 23.128 | 0.0247 | 0.1930 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pd | short_high | 0.890 | 0.500 | COMPLETED | CHECK | 350.978 | 0.1415 | 0.4354 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pd | short_low | 1.676 | 0.500 | COMPLETED | CHECK | 136.788 | 0.0516 | 0.1675 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pu | short_high | 0.890 | 0.500 | COMPLETED | CHECK | 307.686 | 0.1238 | 0.1174 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft_pu | short_low | 1.703 | 0.500 | COMPLETED | CHECK | 136.470 | 0.0517 | 0.1676 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft | short_high | 0.891 | 0.500 | COMPLETED | CHECK | 343.865 | 0.1385 | 0.4264 |
| stm32g031_041_ufqfpn32.ibs | ioms8p_sudq_ft | short_low | 1.691 | 0.500 | COMPLETED | CHECK | 137.680 | 0.0522 | 0.1673 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pd_lv | short_high | 2.295 | 0.500 | COMPLETED | CHECK | 244.523 | 0.2705 | 0.0899 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pd_lv | short_low | 2.640 | 0.500 | COMPLETED | CHECK | 45.948 | 0.0481 | 0.2673 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pu_lv | short_high | 2.295 | 0.500 | COMPLETED | CHECK | 244.972 | 0.2705 | 0.0908 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pu_lv | short_low | 2.644 | 0.500 | COMPLETED | CHECK | 44.427 | 0.0472 | 0.2595 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_lv | short_high | 2.295 | 0.500 | COMPLETED | CHECK | 245.737 | 0.2712 | 0.0913 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_lv | short_low | 2.642 | 0.500 | COMPLETED | CHECK | 45.631 | 0.0481 | 0.2650 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pd | short_high | 0.863 | 0.501 | COMPLETED | CHECK | 406.118 | 0.1690 | 0.0924 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pd | short_low | 0.977 | 0.500 | COMPLETED | CHECK | 156.470 | 0.0587 | 0.1773 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pu | short_high | 0.861 | 0.502 | COMPLETED | CHECK | 407.244 | 0.1692 | 0.0931 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft_pu | short_low | 0.977 | 0.500 | COMPLETED | CHECK | 156.265 | 0.0587 | 0.1769 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft | short_high | 0.862 | 0.501 | COMPLETED | CHECK | 406.591 | 0.1689 | 0.0932 |
| stm32g031_041_ufqfpn32.ibs | iohs8p_sudq_ft | short_low | 0.977 | 0.500 | COMPLETED | CHECK | 156.791 | 0.0589 | 0.1773 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed_pd | short_high | 2.324 | 0.500 | COMPLETED | CHECK | 138.483 | 0.2446 | 0.0727 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed_pd | short_low | 2.167 | 0.500 | COMPLETED | CHECK | 16.306 | 0.0274 | 0.2390 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed_pd | short_high | 1.490 | 0.500 | COMPLETED | CHECK | 102.947 | 0.1814 | 0.4458 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed_pd | short_low | 3.480 | 0.500 | COMPLETED | CHECK | 12.068 | 0.0203 | 0.2164 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed_pd | short_high | 1.800 | 0.500 | COMPLETED | CHECK | 61.942 | 0.1079 | 0.4864 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed_pd | short_low | 9.113 | 0.500 | COMPLETED | CHECK | 265.689 | 0.4501 | 0.1314 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed_pd | short_high | 2.961 | 0.500 | COMPLETED | CHECK | 40.398 | 0.0691 | 0.5514 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed_pd | short_low | 2.840 | 0.500 | COMPLETED | CHECK | 270.984 | 0.4557 | 0.0800 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed_pu | short_high | 2.290 | 0.500 | COMPLETED | CHECK | 141.216 | 0.2481 | 0.0775 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed_pu | short_low | 2.175 | 0.500 | COMPLETED | CHECK | 16.084 | 0.0277 | 0.2401 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed_pu | short_high | 3.584 | 0.500 | COMPLETED | CHECK | 175.992 | 0.2987 | 0.0400 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed_pu | short_low | 5.193 | 0.500 | COMPLETED | CHECK | 8.240 | 0.0141 | 0.2881 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed_pu | short_high | 1.687 | 0.500 | COMPLETED | CHECK | 59.585 | 0.1040 | 0.0231 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed_pu | short_low | 6.911 | 0.500 | COMPLETED | CHECK | 26.875 | 0.0447 | 0.1279 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed_pu | short_high | 2.151 | 0.500 | COMPLETED | WARN | 31.697 | 0.0548 | 0.0067 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed_pu | short_low | 2.043 | 0.500 | COMPLETED | WARN | 2.509 | 0.0041 | 0.0663 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed | short_high | 2.313 | 0.500 | COMPLETED | CHECK | 139.520 | 0.2456 | 0.0752 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_highspeed | short_low | 2.178 | 0.500 | COMPLETED | CHECK | 16.321 | 0.0282 | 0.2360 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed | short_high | 1.498 | 0.500 | COMPLETED | CHECK | 102.674 | 0.1808 | 0.4487 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_fastspeed | short_low | 3.432 | 0.500 | COMPLETED | CHECK | 12.287 | 0.0209 | 0.2167 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed | short_high | 1.688 | 0.500 | COMPLETED | CHECK | 57.546 | 0.1005 | 0.4820 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_mediumspeed | short_low | 11.571 | 0.500 | COMPLETED | CHECK | 6.923 | 0.0121 | 0.1239 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed | short_high | 1.977 | 0.500 | COMPLETED | CHECK | 27.526 | 0.0482 | 0.5571 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_1v8_lowspeed | short_low | 1.963 | 0.500 | COMPLETED | CHECK | 302.128 | 0.5107 | 0.0601 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed_pd | short_high | 0.666 | 0.500 | COMPLETED | CHECK | 297.136 | 0.1744 | 0.1012 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed_pd | short_low | 0.770 | 0.500 | COMPLETED | CHECK | 69.817 | 0.0369 | 0.1652 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed_pd | short_high | 0.671 | 0.500 | COMPLETED | CHECK | 307.581 | 0.1799 | 0.2262 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed_pd | short_low | 1.086 | 0.500 | COMPLETED | CHECK | 54.408 | 0.0297 | 0.1984 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed_pd | short_high | 1.831 | 0.500 | COMPLETED | CHECK | 345.240 | 0.1979 | 0.0284 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed_pd | short_low | 2.384 | 0.500 | COMPLETED | CHECK | 17.048 | 0.0110 | 0.2083 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed_pd | short_high | 1.159 | 0.500 | COMPLETED | WARN | 110.477 | 0.0633 | 0.0092 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed_pd | short_low | 1.236 | 0.500 | COMPLETED | WARN | 14.477 | 0.0077 | 0.0694 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed_pu | short_high | 0.669 | 0.500 | COMPLETED | CHECK | 289.272 | 0.1694 | 0.0952 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed_pu | short_low | 0.768 | 0.500 | COMPLETED | CHECK | 75.130 | 0.0402 | 0.1671 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed_pu | short_high | 0.670 | 0.500 | COMPLETED | CHECK | 309.454 | 0.1808 | 0.1508 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed_pu | short_low | 1.093 | 0.500 | COMPLETED | CHECK | 53.901 | 0.0297 | 0.2000 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed_pu | short_high | 0.675 | 0.500 | COMPLETED | CHECK | 171.722 | 0.1003 | 0.0336 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed_pu | short_low | 2.473 | 0.500 | COMPLETED | CHECK | 39.785 | 0.0215 | 0.1196 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed_pu | short_high | 1.960 | 0.500 | COMPLETED | WARN | 82.531 | 0.0416 | 0.0166 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed_pu | short_low | 1.827 | 0.500 | COMPLETED | CHECK | 780.328 | 0.4569 | 0.0959 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed | short_high | 0.668 | 0.500 | COMPLETED | CHECK | 297.163 | 0.1740 | 0.1019 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_highspeed | short_low | 0.770 | 0.500 | COMPLETED | CHECK | 71.127 | 0.0378 | 0.1656 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed | short_high | 0.672 | 0.500 | COMPLETED | CHECK | 307.940 | 0.1800 | 0.3748 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_fastspeed | short_low | 1.098 | 0.500 | COMPLETED | CHECK | 55.467 | 0.0309 | 0.2013 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed | short_high | 0.675 | 0.500 | COMPLETED | CHECK | 170.717 | 0.0999 | 0.4299 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_mediumspeed | short_low | 2.605 | 0.500 | COMPLETED | CHECK | 40.480 | 0.0222 | 0.1186 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed | short_high | 0.772 | 0.500 | COMPLETED | WARN | 77.793 | 0.0459 | 0.0101 |
| stm32g031_041_ufqfpn32.ibs | io6_ft_3v3_lowspeed | short_low | 0.923 | 0.500 | COMPLETED | WARN | 9.434 | 0.0061 | 0.0551 |
| t2b_0616.ibs | driver2 | short_high | 0.299 | 0.503 | COMPLETED | GOOD | 22.163 | 0.0223 | 0.0218 |
| t2b_0616.ibs | driver2 | short_low | 0.329 | 0.502 | COMPLETED | GOOD | 24.520 | 0.0228 | 0.0243 |
| test.ibs | driver | short_high | 1.316 | 0.500 | COMPLETED | WARN | 117.657 | 0.0825 | 0.0686 |
| test.ibs | driver | short_low | 0.631 | 0.500 | COMPLETED | CHECK | 392.728 | 0.2686 | 0.2910 |

## Files

- `stress_selection.csv`: selected per-model pulse widths and HSPICE state at reversal.
- `metrics.csv`: simulator status and pad/Ku/Kd comparison metrics.
- `cases/<model>/<direction>/`: exact decks, copied IBIS/model, raw output, and logs.
- `plots/<model>/<direction>.png`: pad, Ku, and Kd overlays.
- `plots/summary_outcomes.png` and `summary_error_vs_pulse_width.png`: campaign summaries.
