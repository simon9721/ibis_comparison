# Three-Buffer Gate Voltage vs. Ku/Kd Figures

Presentation-ready figures generated from cached data only. No simulations were rerun.

## Figures

- `plots/io_buf_gate_voltage_vs_kukd.png`
- `plots/inv_chain_gate_voltage_vs_kukd.png`
- `plots/ex2_gate_voltage_vs_kukd.png`

Each figure compares the normal 10 ns high control with the same 1 ns short-high pulse.
The stimulus uses 50 ps rise/fall time and a 50 ohm || 2 pF load.

## Meaning

- Black: HSPICE native-IBIS runtime `Ku` or `Kd`.
- Blue: physical PMOS/shared-gate voltage represented as `1 - Vgate/VDD`.
- Orange: physical NMOS/shared-gate voltage represented as `Vgate/VDD`.
- The colored curves are gate-voltage proxies. They preserve physical gate timing but are not exact transistor `Ku/Kd` extractions.
- The secondary right axes convert the normalized proxy back into actual gate volts.

## Gate Probes

- `io_buf`: PMOS `v(xdut.n2)` and NMOS `v(xdut.n3)`.
- `inv_chain`: shared final-stage control `v(xdut.vout7)`.
- `ex2`: shared output-stage control `v(xdut.n4)`.

## Numeric Data

- `source_data/*.csv`: exact active-window data plotted in each column.
- `proxy_metrics_active_window.csv`: proxy RMSE over the displayed windows.

Source study: `results/three_buffer_common_pulse_sweep_edge50ps_2026-07-30`.
