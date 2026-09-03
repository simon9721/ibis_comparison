# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line, parallel RC residual branches, and optional zero-DC tail branches.

## Fitted Parameters

- Explicit delay: `12.435 ns`
- DC gain to loaded output: `0.912253`
- Branch taus: `0.0218218 ns, 0.0640552 ns, 0.183078 ns, 1.00407 ns`
- Branch gains: `-0.0759482, 0.306934, 0.510556, 0.170711`
- Tail fast taus: `0.399004 ns`
- Tail slow taus: `1.94708 ns`
- Tail gains: `-0.0635044`

## HSPICE Correlation

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.008638 | 0.0749 | 18.48 | 6.739 | 0.03141 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.006398 | 0.03334 | -0.03761 | -10.34 | 0.0309 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.004557 | 0.01789 | 13.8 | 13.92 | 0.02902 |
