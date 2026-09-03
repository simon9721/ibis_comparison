# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `1`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0723256, -0.0996775, 0.167455, 0.0320188`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.132041`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01227 | 0.02193 | -1.285 | 11.41 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01146 | 0.02025 | 1.64 | 4.348 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.009814 | 0.01494 | 18.25 | 3.594 |
