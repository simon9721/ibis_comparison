# PIC18F1xQ20 Resistive Validation (All Output Models)

- Converted mode: `InputDriven`
- Corner: `Typical`
- Bench: direct `50 ohm` termination to ground
- IBIS comparison target: waveform block nearest `R_fixture=50`, `V_fixture=0`

- Cases attempted: `108`
- Cases successful: `108`
- Cases failed: `0`

## Worst 20 by combined score

| Rank | Package | Model | Rise RMS (V) | Fall RMS (V) | Rise Max Abs (V) | Fall Max Abs (V) | Rise dT (ns) | Fall dT (ns) |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `PIC18F1xQ20_vqfn20_LV` | `ptc_i3c_std` | 0.207928 | 0.169676 | 0.428825 | 0.438755 | 7.304 | -5.876 |
| 2 | `PIC18F1xQ20_ssop20_LV` | `ptc_i3c_std` | 0.208502 | 0.169107 | 0.429199 | 0.437585 | 7.321 | -5.864 |
| 3 | `PIC18F1xQ20_soic20_LV` | `ptc_i3c_std` | 0.209337 | 0.168285 | 0.430414 | 0.435878 | 7.345 | -5.842 |
| 4 | `PIC18F1xQ20_pdip20_LV` | `ptc_i3c_std` | 0.210578 | 0.167095 | 0.432905 | 0.433455 | 7.377 | -5.814 |
| 5 | `PIC18F1xQ20_vqfn20_LV` | `io_vrefh10_slctrl` | 0.049774 | 0.050075 | 0.088663 | 0.120189 | 0.273 | -0.079 |
| 6 | `PIC18F1xQ20_ssop20_LV` | `io_vrefh10_slctrl` | 0.049859 | 0.048411 | 0.088746 | 0.112144 | 0.293 | -0.063 |
| 7 | `PIC18F1xQ20_soic20_LV` | `io_vrefh10_slctrl` | 0.049934 | 0.047247 | 0.088796 | 0.108255 | 0.319 | -0.039 |
| 8 | `PIC18F1xQ20_vqfn20_LV` | `io_vrefh10_std` | 0.059781 | 0.052345 | 0.089131 | 0.105560 | 0.050 | -0.430 |
| 9 | `PIC18F1xQ20_pdip20_LV` | `io_vrefh10_slctrl` | 0.050039 | 0.046444 | 0.088868 | 0.101595 | 0.355 | -0.006 |
| 10 | `PIC18F1xQ20_ssop20_LV` | `io_vrefh10_std` | 0.060055 | 0.050358 | 0.089216 | 0.097906 | 0.067 | -0.414 |
| 11 | `PIC18F1xQ20_soic20_LV` | `io_vrefh10_std` | 0.060850 | 0.048860 | 0.089267 | 0.094243 | 0.091 | -0.390 |
| 12 | `PIC18F1xQ20_pdip20_LV` | `io_vrefh10_std` | 0.062155 | 0.047556 | 0.089341 | 0.090107 | 0.124 | -0.356 |
| 13 | `PIC18F1xQ20_pdip20_LV` | `io_zxover_std` | 0.027437 | 0.030751 | 0.079120 | 0.056359 | 0.064 | -0.127 |
| 14 | `PIC18F1xQ20_soic20_LV` | `io_zxover_std` | 0.025707 | 0.022750 | 0.079056 | 0.045764 | 0.042 | -0.149 |
| 15 | `PIC18F1xQ20_ssop20_LV` | `io_zxover_std` | 0.024671 | 0.016536 | 0.079000 | 0.034124 | 0.022 | -0.169 |
| 16 | `PIC18F1xQ20_vqfn20_LV` | `io_zxover_std` | 0.024483 | 0.014950 | 0.078960 | 0.030005 | 0.013 | -0.179 |
| 17 | `PIC18F1xQ20_pdip20_LV` | `io_vrefh5_std` | 0.024964 | 0.028196 | 0.072734 | 0.052120 | 0.097 | -0.078 |
| 18 | `PIC18F1xQ20_soic20_LV` | `io_vrefh5_std` | 0.023802 | 0.022542 | 0.072669 | 0.049212 | 0.075 | -0.099 |
| 19 | `PIC18F1xQ20_ssop20_LV` | `io_vrefh5_std` | 0.023046 | 0.018293 | 0.072614 | 0.052877 | 0.054 | -0.121 |
| 20 | `PIC18F1xQ20_vqfn20_LV` | `io_vrefh5_std` | 0.023057 | 0.018196 | 0.072573 | 0.055355 | 0.045 | -0.131 |

## Best 20 by combined score

| Rank | Package | Model | Rise RMS (V) | Fall RMS (V) |
| ---: | --- | --- | ---: | ---: |
| 108 | `PIC18F1xQ20_vqfn20_LV` | `ptc_i2c_slctrl_fmp` | 0.001215 | 0.008362 |
| 107 | `PIC18F1xQ20_vqfn20_LV` | `ptc_i2c_std` | 0.005098 | 0.009257 |
| 106 | `PIC18F1xQ20_ssop20_LV` | `ptc_i2c_slctrl_fmp` | 0.001231 | 0.010266 |
| 105 | `PIC18F1xQ20_ssop20_LV` | `ptc_i2c_std` | 0.005911 | 0.011010 |
| 104 | `PIC18F1xQ20_vqfn20_LV` | `ptc_i2c_slctrl` | 0.002642 | 0.013051 |
| 103 | `PIC18F1xQ20_ssop20_LV` | `ptc_i2c_slctrl` | 0.002655 | 0.014449 |
| 102 | `PIC18F1xQ20_ssop20_LV` | `ptc_i2c_std_fmp` | 0.007620 | 0.013236 |
| 101 | `PIC18F1xQ20_vqfn20_LV` | `ptc_i2c_std_fmp` | 0.007119 | 0.011809 |
| 100 | `PIC18F1xQ20_vqfn20_LV` | `io_wpd_slctrl` | 0.000949 | 0.013095 |
| 99 | `PIC18F1xQ20_vqfn20_LV` | `io_wpd_std` | 0.010051 | 0.013331 |
| 98 | `PIC18F1xQ20_ssop20_LV` | `io_wpd_std` | 0.010632 | 0.015777 |
| 97 | `PIC18F1xQ20_vqfn20_LV` | `io_dig_slctrl` | 0.000972 | 0.013341 |
| 96 | `PIC18F1xQ20_soic20_LV` | `ptc_i2c_std` | 0.008425 | 0.015925 |
| 95 | `PIC18F1xQ20_ssop20_LV` | `io_osc2_slctrl` | 0.001555 | 0.015669 |
| 94 | `PIC18F1xQ20_soic20_LV` | `ptc_i2c_slctrl_fmp` | 0.001264 | 0.015316 |
| 93 | `PIC18F1xQ20_vqfn20_LV` | `io_osc2_slctrl` | 0.001536 | 0.014159 |
| 92 | `PIC18F1xQ20_ssop20_LV` | `io_vrefl_slctrl` | 0.001103 | 0.016563 |
| 91 | `PIC18F1xQ20_ssop20_LV` | `io_wpd_slctrl` | 0.000976 | 0.015831 |
| 90 | `PIC18F1xQ20_vqfn20_LV` | `io_vrefh8_std` | 0.014161 | 0.014550 |
| 89 | `PIC18F1xQ20_ssop20_LV` | `io_vrefh8_std` | 0.014310 | 0.015078 |