# I3C_TX_0p125mA_tx 1160 ohm ground-terminated 5-pulse ngspice run

- Source IBIS: `pcbauto\Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs`
- Component: `A11486_IBIS-00001760`
- Corner: `Typical`
- Simulator: ngspice via pybis2spice InputDriven subcircuit
- Termination: `1160 ohm` from pad to ground
- Input: `5` high pulses, `20 ns` high and `20 ns` low
- Rise/fall edge setting: `5 ps`

Average settled low/high levels are approximately `0.0005 V` and `0.6034 V`. The average rise 10-90 is `3.561 ns`; the average fall 90-10 is `3.677 ns`.

| Edge | Type | Input edge | 50% crossing | 10-90 / 90-10 | Low | High |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `1` | `rise` | `10.000 ns` | `11.997 ns` | `3.560 ns` | `0.0000 V` | `0.6034 V` |
| `2` | `fall` | `30.000 ns` | `31.867 ns` | `3.619 ns` | `0.0007 V` | `0.6035 V` |
| `3` | `rise` | `50.000 ns` | `51.996 ns` | `3.560 ns` | `0.0007 V` | `0.6034 V` |
| `4` | `fall` | `70.000 ns` | `71.867 ns` | `3.619 ns` | `0.0007 V` | `0.6035 V` |
| `5` | `rise` | `90.000 ns` | `91.997 ns` | `3.560 ns` | `0.0007 V` | `0.6034 V` |
| `6` | `fall` | `110.000 ns` | `112.228 ns` | `3.898 ns` | `0.0007 V` | `0.6035 V` |
| `7` | `rise` | `130.000 ns` | `132.014 ns` | `3.565 ns` | `0.0007 V` | `0.6034 V` |
| `8` | `fall` | `150.000 ns` | `151.866 ns` | `3.619 ns` | `0.0007 V` | `0.6035 V` |
| `9` | `rise` | `170.000 ns` | `171.996 ns` | `3.560 ns` | `0.0007 V` | `0.6034 V` |
| `10` | `fall` | `190.000 ns` | `191.868 ns` | `3.629 ns` | `0.0007 V` | `0.6035 V` |

Generated files:

- `benches\I3C_TX_0p125mA_tx_1160ohm_ground_5pulse.sp`
- `raw\I3C_TX_0p125mA_tx_1160ohm_ground_5pulse.raw`
- `edge_summary.csv`
- `plots\I3C_TX_0p125mA_tx_1160ohm_ground_5pulse_full.png`
- `plots\I3C_TX_0p125mA_tx_1160ohm_ground_5pulse_edge_overlay.png`