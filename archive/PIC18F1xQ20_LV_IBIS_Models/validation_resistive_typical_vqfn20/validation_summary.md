# PIC18F1xQ20 Resistive Validation

- Source IBIS: `C:\Users\simom\Desktop\IBIS_Comparison\PIC18F1xQ20_LV_IBIS_Models\PIC18F1xQ20_vqfn20_LV.ibs`
- Package variant: `vqfn20`
- Converted mode: `InputDriven`
- Corner: `Typical`
- Bench: direct `50 ohm` termination to ground to match `R_fixture=50`, `V_fixture=0`
- Input pulse: rise at `50.0 ns`, fall at `700.0 ns`

| Model | Rise RMS Err (V) | Rise Max Abs Err (V) | Fall RMS Err (V) | Fall Max Abs Err (V) | Plot |
| --- | ---: | ---: | ---: | ---: | --- |
| `io_dig_std` | 0.013253 | 0.039696 | 0.014099 | 0.028303 | `io_dig_std_ibis_vs_pybis_resistive_50ohm.png` |
| `io_dig_slctrl` | 0.000972 | 0.004700 | 0.013341 | 0.030872 | `io_dig_slctrl_ibis_vs_pybis_resistive_50ohm.png` |
| `ptc_i3c_std` | 0.207928 | 0.428825 | 0.169676 | 0.438755 | `ptc_i3c_std_ibis_vs_pybis_resistive_50ohm.png` |