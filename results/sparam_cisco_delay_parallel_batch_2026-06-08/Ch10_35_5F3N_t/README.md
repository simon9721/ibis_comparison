# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line, parallel RC residual branches, and optional zero-DC tail branches.

## Fitted Parameters

- Explicit delay: `13.9 ns`
- DC gain to loaded output: `0.886963`
- Branch taus: `0.0267921 ns, 0.0281355 ns, 0.136379 ns, 0.999698 ns`
- Branch gains: `-0.105489, -0.0496818, 0.722031, 0.320102`
- Tail fast taus: `0.0831441 ns`
- Tail slow taus: `0.12765 ns`
- Tail gains: `-0.062306`

## HSPICE Correlation

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.007458 | 0.01576 | 8.284 | 0.2839 | 0.02518 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.007349 | 0.01615 | 5.6 | -1.154 | 0.02473 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.008703 | 0.03271 | 14.63 | 15.48 | 0.0232 |
