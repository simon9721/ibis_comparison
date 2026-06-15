# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line, parallel RC residual branches, and optional zero-DC tail branches.

## Fitted Parameters

- Explicit delay: `12.44 ns`
- DC gain to loaded output: `0.901092`
- Branch taus: `0.0615234 ns, 0.191642 ns, 0.301851 ns, 0.352142 ns`
- Branch gains: `0.386835, 0.758314, -0.421735, 0.177678`
- Tail fast taus: `0.0350172 ns`
- Tail slow taus: `1.02267 ns`
- Tail gains: `-0.262692`

## HSPICE Correlation

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.006842 | 0.04008 | -9.259 | 11.73 | 0.02944 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.006172 | 0.02947 | 2.385 | 4.315 | 0.02937 |
| `audit_amp1p5_edge500_r50` | `FAIL` | 0.007786 | 0.03215 | 30.25 | 22.59 | 0.02761 |
