# Hibiki I3C_TX_0p125mA_tx with Wmodel baseline channel conversion

This is a first-pass ngspice-compatible baseline conversion of `pcbauto/Wmodel.sp`.

Important limitations:

- The HSPICE W-element definitions are not directly usable as ngspice channels.
- This run converts only `Ro`, `Lo`, `Go`, and `Co` into an RLGC ladder.
- `Rs` skin-effect loss is ignored in this baseline.
- `Gd` dielectric-loss is ignored; in this file it is zero for all three traces.
- `Wmodel.sp` has model definitions but no channel instance length, so this run assumes `100 mm`.

Simulation setup:

- IBIS: `pcbauto\Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs`
- Component: `A11486_IBIS-00001760`
- Model: `I3C_TX_0p125mA_tx`
- Stimulus: five `20 ns` high / `20 ns` low pulses, `5 ps` input edge
- Load: `1160 ohm` to ground at the far end of each trace
- Channel length assumption: `100 mm`
- RLGC ladder sections: `80`

Artifacts:

- Bench: `benches\hibiki_wmodel_baseline.sp`
- Raw: `raw\hibiki_wmodel_baseline.raw`
- Log: `raw\hibiki_wmodel_baseline.log`
- Conversion summary: `wmodel_baseline_conversion.csv`
- Waveform metrics: `waveform_metrics.csv`
- Plot: `plots\hibiki_wmodel_baseline_pad_overlay.png`
- Plot: `plots\hibiki_wmodel_baseline_source_vs_load.png`
- Plot: `plots\hibiki_wmodel_baseline_first_rise_zoom.png`

Trace summary:

| Trace | Wmodel | Z0 approx | Delay for 100 mm | Rs ignored |
|---|---|---:|---:|---:|
| `trace01` | `Wmodel_Trace01::Sig` | `122.49 ohm` | `0.535 ns` | `0.00126077` |
| `trace02` | `Wmodel_Trace02::Sig` | `122.49 ohm` | `0.535 ns` | `0.00126077` |
| `trace03` | `Wmodel_Trace03::Sig` | `65.95 ohm` | `0.548 ns` | `0.0017154` |