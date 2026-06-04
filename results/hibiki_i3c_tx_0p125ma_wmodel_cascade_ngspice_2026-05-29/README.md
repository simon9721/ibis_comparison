# Hibiki I3C_TX_0p125mA_tx with cascaded Wmodel baseline traces

This run cascades the three Wmodel traces in this order:

1. `Wmodel_Trace01::Sig`
2. `Wmodel_Trace02::Sig`
3. `Wmodel_Trace03::Sig`

Important limitations:

- The HSPICE W-element definitions are not directly usable as ngspice channels.
- This run converts only `Ro`, `Lo`, `Go`, and `Co` into RLGC ladders.
- `Rs` skin-effect loss is ignored in this baseline.
- `Gd` dielectric-loss is ignored; in this file it is zero for all three traces.
- `Wmodel.sp` has model definitions but no channel instance length, so each trace assumes `100 mm`.

Simulation setup:

- IBIS: `pcbauto\Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs`
- Component: `A11486_IBIS-00001760`
- Model: `I3C_TX_0p125mA_tx`
- Stimulus: five `20 ns` high / `20 ns` low pulses, `5 ps` input edge
- Load: `1160 ohm` to ground at the end of Trace03
- Total assumed channel length: `300 mm`
- Ideal LC delay estimate for full cascade: `1.618 ns`
- RLGC ladder sections: `80` per trace, `240` total

Artifacts:

- Bench: `benches\hibiki_wmodel_cascade.sp`
- Raw: `raw\hibiki_wmodel_cascade.raw`
- Log: `raw\hibiki_wmodel_cascade.log`
- Conversion summary: `cascade_wmodel_conversion.csv`
- Waveform metrics: `cascade_waveform_metrics.csv`
- Plot: `plots\hibiki_wmodel_cascade_full_overlay.png`
- Plot: `plots\hibiki_wmodel_cascade_far_end_only.png`
- Plot: `plots\hibiki_wmodel_cascade_far_end_first_rise_zoom.png`
- Plot: `plots\hibiki_wmodel_cascade_first_rise_zoom.png`
- Plot: `plots\hibiki_wmodel_cascade_nodes_plus_kukd.png`