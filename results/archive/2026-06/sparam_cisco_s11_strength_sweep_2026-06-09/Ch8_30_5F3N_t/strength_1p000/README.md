# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `1`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0647191, -0.142351, 0.176433, 0.138085`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.131298`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01654 | 0.01955 | 12.43 | -12.07 |
| `audit_amp1p5_edge50_r50` | `FAIL` | 0.01762 | 0.01906 | -6.201 | -28.28 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01484 | 0.01671 | 5.967 | -11.65 |
