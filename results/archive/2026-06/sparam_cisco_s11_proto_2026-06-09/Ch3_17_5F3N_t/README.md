# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `0.0436984, 0.0783579, -0.0626887, 0.00965885`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `-0.149022`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.0141 | 0.0242 | 4.046 | 0.179 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01427 | 0.02391 | 1.164 | -1.784 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01357 | 0.02127 | -0.1612 | -11.9 |
