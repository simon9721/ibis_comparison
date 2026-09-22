# I3C_TX_0p125mA_tx 1160 ohm matched-load ngspice run

- Source IBIS: `pcbauto\Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs`
- Component: `A11486_IBIS-00001760`
- Corner: `Typical`
- Converted model: `converted\I3C_TX_0p125mA_tx_OutputInput_Typical.sub`
- Simulator: ngspice via pybis2spice InputDriven subcircuit
- Load: `1160 ohm`
- Stimulus: `0 V -> 1.2 V -> 0 V`, rise at `10.0 ns`, fall at `130.0 ns`

This is not a direct IBIS VT-table validation because the source IBIS only provides VT tables with `R_fixture=50 ohm`. These runs test the converted pybis/ngspice model under a 1160 ohm load.

Important interpretation note: a 1160 ohm DC termination changes the load line, so these are not full-swing capacitive I3C bus edges. The `1160ohm_to_0v` case settles near half supply, while the `1160ohm_to_1p2v` case biases the pad high and can exceed VDD because the IBIS pullup IV curve is being evaluated against a 1.2 V fixture.

| Case | Low before | High hold | Low after | Rise swing | Rise 10-90 | Fall 90-10 | Plot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `1160ohm_to_0v` | `0.0000 V` | `0.6045 V` | `0.0000 V` | `0.6045 V` | `3.585 ns` | `3.635 ns` | `plots\I3C_TX_0p125mA_tx_1160ohm_to_0v_ngspice.png` |
| `1160ohm_to_1p2v` | `0.7123 V` | `1.3049 V` | `0.7123 V` | `0.5926 V` | `3.577 ns` | `3.630 ns` | `plots\I3C_TX_0p125mA_tx_1160ohm_to_1p2v_ngspice.png` |

Generated files:

- `matched_load_summary.csv`
- `plots/I3C_TX_0p125mA_tx_1160ohm_overlay.png`
- `plots/I3C_TX_0p125mA_tx_1160ohm_to_0v_ngspice.png`
- `plots/I3C_TX_0p125mA_tx_1160ohm_to_1p2v_ngspice.png`