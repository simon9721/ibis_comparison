# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line plus parallel RC residual branches.

## Fitted Parameters

- Explicit delay: `4.40859 ns`
- DC gain to loaded output: `0.800421`
- Branch taus: `0.0697571 ns, 0.405687 ns, 0.530984 ns, 1.82003 ns`
- Branch gains: `0.5358, 0.0487083, 0.157403, 0.0585096`
- Tail fast taus: `0.059584 ns`
- Tail slow taus: `11.7956 ns`
- Tail gains: `0.15642`

## HSPICE Correlation

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.00593 | 0.02371 | 5.17 | 6.492 | 0.03826 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.006515 | 0.02048 | 2.308 | 4.538 | 0.0384 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.006522 | 0.02657 | 4.823 | 9.825 | 0.03629 |
