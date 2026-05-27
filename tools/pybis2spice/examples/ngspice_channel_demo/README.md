# ngspice Channel Demo

This folder shows the basic shape of a channel simulation using pybis2spice's
generic SPICE output.

Files:

- `HCT1G08_OUTN_50-Output-Typical-generic.sub`: generated generic output buffer
- `HCT1G08_IN_50-Input-Typical.sub`: generated input buffer
- `channel_demo.cir`: ngspice-style channel testbench

Run from this directory with:

```powershell
ngspice channel_demo.cir
```

The circuit is:

```text
driver pad -> series resistor -> ideal transmission line -> receiver input
```

The generated output model has one external pin and internal waveform stimulus.
Set `FREQ`, `DUTY`, `RSER`, `TD`, `ZO`, and `CLOAD` in `channel_demo.cir` to
change the channel conditions.

Important note:

- this demo uses the **Generic** output model, which is self-stimulating
  internally
- this is useful as a simple ngspice syntax/channel example
- for externally driven PRBS/channel simulation, use the
  `InputDriven` subcircuit type instead, which exposes
  `OUT IN EN VCC VSS` pins and uses the SPISim-style elapsed-time / T-line
  runtime flow
