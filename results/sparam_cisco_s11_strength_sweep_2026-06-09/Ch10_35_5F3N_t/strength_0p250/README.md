# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.25`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.168179, -0.196258, 0.280964, 0.168031`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.277434`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.009548 | 0.02287 | -2.249 | -12.35 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.00925 | 0.02235 | -4.945 | -13.78 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.008743 | 0.02066 | 3.773 | 2.396 |
