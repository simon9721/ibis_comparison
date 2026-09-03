# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.5`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0723256, -0.0996775, 0.167455, 0.0320188`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.132041`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.0105 | 0.02311 | -1.072 | 12.67 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.009494 | 0.02157 | 1.823 | 5.547 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.007661 | 0.01663 | 18.42 | 6.317 |
