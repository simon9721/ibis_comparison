# Arbel I3C Validation

- Source IBIS: `C:\Users\simom\Desktop\IBIS_Comparison\pcbauto\mpad_1_S7_1P2_I3C_ibis_vs_pybis\Arbel_I3C_IBIS.ibs`
- Component: `Arbel`
- Model: `mpad_1_S7_1P2_I3C`
- Converted mode: `InputDriven`
- Corner: `Typical`
- Bench family: `1 kOhm` to `V_fixture` in parallel with `20 pF` to ground
- Input pulse: rise at `5.0 ns`, fall at `35.0 ns`

| Fixture | Rise RMS (V) | Rise Max (V) | Fall RMS (V) | Fall Max (V) | Rise Plot | Fall Plot |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `vfix_0p0` | 0.004349 | 0.012719 | 0.000551 | 0.001356 | `mpad_1_S7_1P2_I3C_rise_vfix_0p0.png` | `mpad_1_S7_1P2_I3C_fall_vfix_0p0.png` |
| `vfix_1p2` | 0.001403 | 0.006161 | 0.000638 | 0.003239 | `mpad_1_S7_1P2_I3C_rise_vfix_1p2.png` | `mpad_1_S7_1P2_I3C_fall_vfix_1p2.png` |