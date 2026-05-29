# ngspice Lab CLI and GUI

`scripts/ngspice_lab.py` is a reusable ngspice testbench generator, runner, and plotter for buffer experiments.

It supports:

- IBIS DUTs converted through `pybis2spice`
- SPICE subcircuit DUTs through `.include` plus pin-order mapping
- multiple DUTs in one run, driven by the same stimulus
- resistive termination to ground or a user-defined voltage
- optional ideal transmission-line channel
- pulse-train, bit-pattern, and PRBS7 input stimulus
- generated ngspice deck, raw file, log, schematic preview, overlay plot, and side-by-side plot
- Tkinter GUI with embedded matplotlib result viewer

## Launch GUI

Run with the pybis2spice virtualenv Python:

```powershell
& 'C:\Users\simom\Desktop\Projects\spice\pybis2spice\.venv\Scripts\python.exe' scripts\ngspice_lab.py gui
```

The GUI lets you:

- choose IBIS or SPICE DUTs
- scan an IBIS file into component/model/corner dropdowns so the common path does not require typing names
- add multiple DUTs before running
- set termination, optional ideal T-line or lossy RLGC ladder channel, and stimulus parameters
- use a scrollable `Setup` tab with controls grouped into Run, Stimulus, Termination/Channel, Add DUT, and DUT list sections
- show only the fields relevant to the selected stimulus kind, channel mode, and DUT type
- use always-visible top buttons for `Generate Schematic`, `Run Sim`, and `Save Config`
- generate a schematic before simulation and view it inside the `Setup` tab as a setup sanity check
- run ngspice and view results in the `Output` tab
- switch dynamically between `transient_overlay` and `transient_side_by_side` after a run
- use embedded waveform-view controls for zooming and horizontal/vertical markers

The lossy RLGC ladder channel is discretized as repeated series `R`/`L` and shunt `C`/`G` sections. The GUI exposes length, section count, and per-mm `R`, `L`, `G`, and `C` values.

For SPICE DUTs, use the pin-order field to map the subcircuit pins. Recognized pin names include `OUT`, `PAD`, `IN`, `EN`, `VDD`, `VCC`, `VSS`, and `GND`. Unknown names are passed through as literal node names.

## Direct CLI Example

This runs the Hibiki I3C 0.125 mA IBIS model with five pulses into `1160 ohm` to ground:

```powershell
& 'C:\Users\simom\Desktop\Projects\spice\pybis2spice\.venv\Scripts\python.exe' scripts\ngspice_lab.py run `
  --ibis pcbauto\Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs `
  --component A11486_IBIS-00001760 `
  --model I3C_TX_0p125mA_tx `
  --label hibiki_i3c `
  --r-ohm 1160 `
  --v-term 0 `
  --stimulus pulse_train `
  --pulses 5 `
  --high-ns 20 `
  --low-ns 20 `
  --edge-ps 5 `
  --vdd 1.2 `
  --output-dir results\ngspice_lab_hibiki_1160_5pulse
```

## Config-Driven CLI

Write an example config:

```powershell
& 'C:\Users\simom\Desktop\Projects\spice\pybis2spice\.venv\Scripts\python.exe' scripts\ngspice_lab.py example-config results\ngspice_lab_example_config.json
```

Run from config:

```powershell
& 'C:\Users\simom\Desktop\Projects\spice\pybis2spice\.venv\Scripts\python.exe' scripts\ngspice_lab.py run --config results\ngspice_lab_example_config.json
```

Each run writes:

- `config_used.json`
- `benches/ngspice_lab_testbench.sp`
- `raw/ngspice_lab_testbench.raw`
- `raw/ngspice_lab_testbench.log`
- `plots/testbench_schematic.png`
- `plots/transient_overlay.png`
- `plots/transient_side_by_side.png`
- `run_summary.csv`
- `README.md`

## Current Smoke-Tested Case

The tool was verified on:

- IBIS: `pcbauto/Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs`
- Component: `A11486_IBIS-00001760`
- Model: `I3C_TX_0p125mA_tx`
- Termination: `1160 ohm` to ground
- Stimulus: five `20 ns` high / `20 ns` low pulses with `5 ps` input edges

Generated verified output:

- `results/ngspice_lab_hibiki_1160_5pulse/plots/transient_overlay.png`
- `results/ngspice_lab_hibiki_1160_5pulse/plots/testbench_schematic.png`
