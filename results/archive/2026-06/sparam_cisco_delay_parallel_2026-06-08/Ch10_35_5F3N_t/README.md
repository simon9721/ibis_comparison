# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line plus parallel RC residual branches.

## Fitted Parameters

- Explicit delay: `13.9203 ns`
- DC gain to loaded output: `0.89348`
- Branch taus: `0.112563 ns, 0.280437 ns, 0.664271 ns, 1.7238 ns`
- Branch gains: `0.30177, 0.405099, 0.0142327, 0.172379`

## Corrected HSPICE Correlation

Corrected ngspice raw files are in `ngspice_corrected/`.

Comparison output is in `comparison_corrected/`.

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | PASS | 0.003632 | 0.01020 | 5.80 | 3.65 | 0.02518 |
| `audit_amp1p5_edge50_r50` | PASS | 0.003995 | 0.02184 | 3.64 | 2.01 | 0.02473 |
| `audit_amp1p5_edge500_r50` | PASS | 0.006172 | 0.03387 | 12.02 | 16.56 | 0.02320 |

Preview plot: `fit_preview.png`.

The original `ngspice/` and `comparison/` folders came from a pre-fix run with
inverted VCCS summing orientation. Use `ngspice_corrected/` and
`comparison_corrected/` for accepted results.
