# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.5`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0647191, -0.142351, 0.176433, 0.138085`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.131298`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01047 | 0.02515 | 12.94 | -5.409 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01115 | 0.02464 | -5.627 | -22.05 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.00801 | 0.02264 | 7.379 | -1.479 |
