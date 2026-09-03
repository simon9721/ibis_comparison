# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.5`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0693889, -0.0138006, 0.0484658, 0.111244`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.0692338`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.009722 | 0.01915 | 2.293 | -2.161 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01014 | 0.01828 | 6.51 | 1.883 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01004 | 0.018 | 18.25 | 18.24 |
