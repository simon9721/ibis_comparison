# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.25`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `0.0436984, 0.0783579, -0.0626887, 0.00965885`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `-0.149022`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.007287 | 0.03446 | 4.889 | 4.811 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.007778 | 0.0345 | 2.008 | 2.874 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.007451 | 0.03231 | 3.58 | 4.282 |
