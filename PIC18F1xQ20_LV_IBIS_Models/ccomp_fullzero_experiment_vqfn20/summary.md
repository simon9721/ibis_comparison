# Full C_comp Zero Experiment

- Package variant: `vqfn20`
- Source IBIS: `PIC18F1xQ20_vqfn20_LV.ibs`
- Three variants are compared:
  - original converted model
  - runtime `C_comp=0` only
  - re-extract `Ku/Kd` with `C_comp=0` and simulate with `C_comp=0`

| Model | C_comp (pF) | Original | Runtime Zero | Full Zero | Full Zero Improvement vs Original | Plot |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `io_vrefh10_slctrl` | 8.721 | 0.121311 | 0.254809 | 0.088669 | 0.032642 | `io_vrefh10_slctrl_fullzero_compare.png` |
| `io_vrefh10_std` | 8.721 | 0.106330 | 0.244138 | 0.093500 | 0.012830 | `io_vrefh10_std_fullzero_compare.png` |
| `io_dig_slctrl` | 2.465 | 0.030872 | 0.074316 | 0.018861 | 0.012012 | `io_dig_slctrl_fullzero_compare.png` |
| `io_zxover_std` | 3.179 | 0.078960 | 0.095220 | 0.083235 | -0.004276 | `io_zxover_std_fullzero_compare.png` |
| `io_vrefh5_std` | 4.850 | 0.072573 | 0.152765 | 0.080561 | -0.007988 | `io_vrefh5_std_fullzero_compare.png` |
| `ptc_i3c_std` | 13.619 | 0.438755 | 0.466904 | 0.449673 | -0.010918 | `ptc_i3c_std_fullzero_compare.png` |