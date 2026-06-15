# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.25`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.175347, -0.187701, 0.274945, 0.182152`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.298717`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.0117 | 0.02128 | 11.88 | -11.78 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01134 | 0.02088 | -3.602 | -1.416 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01145 | 0.02121 | 5.199 | 11.29 |
