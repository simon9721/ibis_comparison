# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line plus parallel RC residual branches.

## Fitted Parameters

- Explicit delay: `2.39846 ns`
- DC gain to loaded output: `0.92147`
- Branch taus: `0.00309308 ns, 0.0259597 ns, 0.0324944 ns, 0.0773777 ns`
- Branch gains: `-0.0586233, 0.0123264, 0.908633, 0.0591336`
- Tail fast taus: `0.0923622 ns`
- Tail slow taus: `0.191852 ns`
- Tail gains: `-0.356664`

## HSPICE Correlation

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01283 | 0.06259 | 0.8991 | 9.262 | 0.03909 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01216 | 0.02644 | -1.029 | 6.372 | 0.03829 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01249 | 0.03424 | 5.77 | 5.599 | 0.03643 |
