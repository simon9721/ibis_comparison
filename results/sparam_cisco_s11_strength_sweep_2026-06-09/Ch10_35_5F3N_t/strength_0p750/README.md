# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.75`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.168179, -0.196258, 0.280964, 0.168031`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.277434`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01303 | 0.01856 | -3.359 | -17.51 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01273 | 0.01786 | -6.053 | -18.91 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01161 | 0.01571 | 2.07 | -3.712 |
