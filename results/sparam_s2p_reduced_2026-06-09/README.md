# 2-port Reduced S-parameter Prototype

This run applies the Cisco reduced-model strategy to true `.s2p` channels:

- S21/RX path: explicit delay, parallel RC residual branches, one zero-DC tail branch, and a new zero-DC input feedthrough/ringing basis.
- S11/TX path: the existing bench-scoped 50 ohm input correction with a strength sweep.
- Audit: HSPICE native S-element vs ngspice generated subcircuit, using 1.5 V, 50 ohm source, 5 ps / 50 ps / 500 ps edges.

## Summary

| Touchstone | selected S11 strength | pass | mean RX RMSE | mean TX RMSE | note |
|---|---:|---:|---:|---:|---|
| `Clarity_example.S2P` | 0.25 | 2/3 | 9.408 mV | 11.821 mV | 5 ps fall fails because HSPICE's early ring crosses the 50% threshold before the main fall; the waveform overlay is much closer after the ring/feedthrough basis. |
| `ch_model_fit.s2p` | 1.0 | 2/3 | 16.582 mV | 6.324 mV | 50 ps case misses the strict RX RMSE/maxabs thresholds, but timing is within about 20 ps. |

## Key Outputs

- `summary.csv`: compact selected-result summary.
- `Clarity_example/selected_overview.png`: selected HSPICE-vs-ngspice overlay for `Clarity_example.S2P`.
- `Clarity_example/selected_comparison.csv`: selected per-edge metrics for `Clarity_example.S2P`.
- `ch_model_fit/selected_overview.png`: selected HSPICE-vs-ngspice overlay for `ch_model_fit.s2p`.
- `ch_model_fit/selected_comparison.csv`: selected per-edge metrics for `ch_model_fit.s2p`.

The feedthrough/ringing basis is the main new finding: without it, `Clarity_example.S2P` had about 39 mV mean RX RMSE and only 1/3 passing cases; with it, the mean RX RMSE drops to about 9.4 mV and 2/3 cases pass.
