# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0723256, -0.0996775, 0.167455, 0.0320188`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.132041`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.009441 | 0.02465 | -0.8447 | 13.85 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.008296 | 0.02327 | 2.038 | 6.802 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.006321 | 0.01871 | 18.6 | 9.062 |
