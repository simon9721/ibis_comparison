# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line plus parallel RC residual branches.

## Fitted Parameters

- Explicit delay: `5.89917 ns`
- DC gain to loaded output: `0.807607`
- Branch taus: `0.0154737 ns, 0.0278394 ns, 0.0388427 ns, 0.21274 ns`
- Branch gains: `-0.206605, -0.0855772, 0.635546, 0.464243`
- Tail fast taus: `2.04212 ns`
- Tail slow taus: `10.2192 ns`
- Tail gains: `0.166911`

## HSPICE Correlation

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.007463 | 0.01383 | 3.041 | 0.9568 | 0.02388 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.008121 | 0.02047 | 7.187 | 4.947 | 0.02316 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.008379 | 0.03259 | 19.1 | 24.42 | 0.02288 |
