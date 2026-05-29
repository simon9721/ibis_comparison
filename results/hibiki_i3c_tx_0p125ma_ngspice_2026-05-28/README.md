# I3C_TX_0p125mA_tx ngspice validation

- Source IBIS: `pcbauto\Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs`
- Component: `A11486_IBIS-00001760`
- Corner: `Typical`
- Converted model: `converted\I3C_TX_0p125mA_tx_OutputInput_Typical.sub`
- Simulator: ngspice via pybis2spice InputDriven subcircuit
- Stimulus: `0 V -> 1.2 V -> 0 V`, rise at `10.0 ns`, fall at `130.0 ns`
- Fixtures simulated: `50 ohm` to `0 V`, and `50 ohm` to `1.2 V`

The 0.125 mA driver has a small 50 ohm fixture swing. Plots show `pad - V_fixture` in millivolts so the waveform is readable.

| Fixture | Rise swing | Fall swing | Rise RMSE | Fall RMSE | Plot |
| --- | ---: | ---: | ---: | ---: | --- |
| `vfixture_0v` | `43.053 mV` | `-43.053 mV` | `0.640 mV` | `0.912 mV` | `plots\I3C_TX_0p125mA_tx_vfixture_0v_ngspice_vs_ibis.png` |
| `vfixture_1p2v` | `41.550 mV` | `-41.540 mV` | `1.467 mV` | `1.158 mV` | `plots\I3C_TX_0p125mA_tx_vfixture_1p2v_ngspice_vs_ibis.png` |

Generated files:

- `validation_summary.csv`
- `plots/error_summary.png`
- `plots/I3C_TX_0p125mA_tx_vfixture_0v_ngspice_vs_ibis.png`
- `plots/I3C_TX_0p125mA_tx_vfixture_1p2v_ngspice_vs_ibis.png`