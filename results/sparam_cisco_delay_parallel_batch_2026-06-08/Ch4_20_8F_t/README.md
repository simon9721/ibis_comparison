# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line, parallel RC residual branches, and optional zero-DC tail branches.

## Fitted Parameters

- Explicit delay: `8.93811 ns`
- DC gain to loaded output: `0.941677`
- Branch taus: `0.0303511 ns, 0.0774982 ns, 1.0122 ns, 2.41046 ns`
- Branch gains: `-0.127045, 0.935813, 0.146579, -0.0136705`
- Tail fast taus: `0.0165295 ns`
- Tail slow taus: `0.661578 ns`
- Tail gains: `-0.0423542`

## HSPICE Correlation

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.009448 | 0.04244 | -0.8893 | 13.88 | 0.02465 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.008296 | 0.03519 | 2.039 | 6.778 | 0.02327 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.006321 | 0.02758 | 18.6 | 9.062 | 0.01871 |
