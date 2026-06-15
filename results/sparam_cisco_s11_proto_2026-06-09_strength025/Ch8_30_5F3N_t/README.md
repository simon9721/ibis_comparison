# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.25`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0647191, -0.142351, 0.176433, 0.138085`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.131298`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.009198 | 0.02822 | 18.21 | 3.097 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.007876 | 0.02771 | -0.3371 | -13.73 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.005275 | 0.02578 | 13.09 | 8.693 |
