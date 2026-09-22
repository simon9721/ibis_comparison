# Slow/Fast IBIS Ku/Kd and Gate-State Comparison

## What Is Compared

1. Native-HSPICE runtime `Ku/Kd` from the old slow IBIS and regenerated 5 ps IBIS.
2. The `two_state_directional_residual` ngspice model generated separately from each IBIS.
3. Each gate-state result is scored only against the native-HSPICE run using the same IBIS file.

Common bench: 3.3 V ideal supply and enable, 1 ps input command edges, 50 ohm to ground in parallel with 2 pF, 27 C, and no channel.

## Main Finding

- Slow IBIS offline gate-state reconstruction: worst RMSE `0.01994`, worst max error `0.04869`, `PASS`.
- Fast 5 ps IBIS offline gate-state reconstruction: worst RMSE `0.46428`, worst max error `0.69980`, `FAIL`.
- Normal complete-pulse slow gate-state runtime errors are pad `10.9622 mV`, Ku `0.0108`, Kd `0.0056`.
- Normal complete-pulse fast gate-state runtime errors are pad `1105.3125 mV`, Ku `0.7173`, Kd `0.1745`.
- The fast 2 ns high gate-state run is a numeric failure; it is shown as such rather than plotting a partial raw file.
- Slow short-high remains incomplete: Ku is often reasonable, but Kd recovery is wrong.
- Slow short-low is the mirror: Kd can be accurate while Ku recovery is wrong; the 2 ns low case is the strongest slow-IBIS result.
- Fast gate-state transient curves are diagnostic only because the offline reconstruction gate fails before simulation.

## Figures

- `plots\01_hspice_native_slow_vs_fast_contact_sheet.png`
- `plots\02_gate_state_slow_fast_contact_sheet.png`
- `plots\03_reconstruction_gate_slow_vs_fast.png`
- `plots\04_gate_state_matching_reference_rmse.png`
- `plots\05_gate_state_vs_old_ibis_clean_contact_sheet.png`
- `plots\06_old_ibis_gate_state_transistor_pad_clean_contact_sheet.png`
- `plots/01_hspice_native_slow_vs_fast/<case>_hspice_slow_vs_fast_kukd.png`
- `plots/02_gate_state_vs_matching_hspice/<case>_gate_state_slow_fast.png`
- `plots/05_gate_state_vs_old_ibis_clean/<case>_gate_state_vs_hspice_old_ibis.png`
- `plots/06_old_ibis_gate_state_transistor_pad_clean/<case>_pad_three_way.png`

## Numeric Evidence

- `comparison_metrics.csv`
- `source_manifest.csv`
- `numeric/<case>_aligned_waveforms.csv`

No HSPICE simulations were run by this report. Existing `.tr0` references were read from cache. The missing fast 2 ns low ngspice gate-state case was generated before this report; its exact deck, model, raw file, and log remain in the fast comparison study.
