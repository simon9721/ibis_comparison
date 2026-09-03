# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.5`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0130415, -0.0738412, 0.126733, 0.0291392`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.0230419`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01712 | 0.03178 | 0.8541 | 8.053 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01664 | 0.03095 | -1.091 | 5.103 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01631 | 0.02852 | 4.423 | -3.387 |
