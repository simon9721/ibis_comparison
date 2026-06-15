# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.5`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.168179, -0.196258, 0.280964, 0.168031`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.277434`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01047 | 0.02065 | 7.208 | -5.012 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01031 | 0.02005 | 4.503 | -6.361 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.0105 | 0.01816 | 12.92 | 9.334 |
