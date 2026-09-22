# ngspice lab run

- Bench: `benches\ngspice_lab_testbench.sp`
- Raw: `raw\ngspice_lab_testbench.raw`
- Log: `raw\ngspice_lab_testbench.log`
- Schematic: `plots\testbench_schematic.png`
- Termination: `1160 ohm` to `0 V`
- Channel: `none`
- Stimulus: `pulse_train`
- Stop time: `230 ns`

DUTs:
- `hibiki_i3c_0p125ma`: `ibis` using `I3C_TX_0p125mA_tx_OutputInput_Typical`

Plots:
- `plots\transient_overlay.png`
- `plots\transient_side_by_side.png`

Summary CSV:

- `run_summary.csv`