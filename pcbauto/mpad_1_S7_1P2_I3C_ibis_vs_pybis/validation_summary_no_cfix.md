# Arbel I3C Validation (Without C_fixture In Solve)

- Source IBIS: `C:\Users\simom\Desktop\IBIS_Comparison\pcbauto\mpad_1_S7_1P2_I3C_ibis_vs_pybis\Arbel_I3C_IBIS.ibs`
- Component: `Arbel`
- Model: `mpad_1_S7_1P2_I3C`
- Converted mode: `InputDriven`
- Corner: `Typical`
- Bench family: `1 kOhm` to `V_fixture` in parallel with `20 pF` to ground
- Extraction mode: `C_fixture forced to 0 during Ku/Kd solve`

| Fixture | Rise RMS (V) | Rise Max (V) | Fall RMS (V) | Fall Max (V) | Rise Plot | Fall Plot |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `vfix_0p0` | 0.153966 | 0.237913 | 0.167371 | 0.313486 | `mpad_1_S7_1P2_I3C_rise_vfix_0p0_no_cfix.png` | `mpad_1_S7_1P2_I3C_fall_vfix_0p0_no_cfix.png` |
| `vfix_1p2` | 0.175214 | 0.291641 | 0.152262 | 0.288679 | `mpad_1_S7_1P2_I3C_rise_vfix_1p2_no_cfix.png` | `mpad_1_S7_1P2_I3C_fall_vfix_1p2_no_cfix.png` |