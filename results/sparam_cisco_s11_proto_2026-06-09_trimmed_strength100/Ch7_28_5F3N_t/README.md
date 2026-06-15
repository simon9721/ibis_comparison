# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `1`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.175347, -0.187701, 0.274945, 0.182152`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.298717`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01122 | 0.01394 | 11.16 | -17.06 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01093 | 0.01334 | -4.359 | -6.61 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01022 | 0.01337 | 4.467 | 3.546 |
