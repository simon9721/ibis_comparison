# C_comp Zero Experiment

- Package variant: `vqfn20`
- Source IBIS: `PIC18F1xQ20_vqfn20_LV.ibs`
- Comparison target: corresponding `R_fixture=50`, `V_fixture=0` IBIS waveforms
- Note: this only zeros `C_comp` in the runtime SPICE model.
- The precomputed `Ku/Kd` tables are still the ones extracted with the original `C_comp` present.

| Model | C_comp (pF) | Original Score | C_comp=0 Score | Improvement (`orig - zero`) | Plot |
| --- | ---: | ---: | ---: | ---: | --- |
| `io_zxover_std` | 3.179 | 0.078960 | 0.095220 | -0.016260 | `io_zxover_std_ccomp0_compare.png` |
| `ptc_i3c_std` | 13.619 | 0.438755 | 0.466904 | -0.028149 | `ptc_i3c_std_ccomp0_compare.png` |
| `io_dig_slctrl` | 2.465 | 0.030872 | 0.074316 | -0.043444 | `io_dig_slctrl_ccomp0_compare.png` |
| `io_vrefh5_std` | 4.850 | 0.072573 | 0.152765 | -0.080192 | `io_vrefh5_std_ccomp0_compare.png` |
| `io_vrefh10_slctrl` | 8.721 | 0.121311 | 0.254809 | -0.133499 | `io_vrefh10_slctrl_ccomp0_compare.png` |
| `io_vrefh10_std` | 8.721 | 0.106330 | 0.244138 | -0.137808 | `io_vrefh10_std_ccomp0_compare.png` |