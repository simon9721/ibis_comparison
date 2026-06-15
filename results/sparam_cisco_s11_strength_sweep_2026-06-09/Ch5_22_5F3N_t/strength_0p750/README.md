# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.75`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0693889, -0.0138006, 0.0484658, 0.111244`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.0692338`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01136 | 0.01693 | -3.084 | -8.675 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01149 | 0.01595 | 1.143 | -4.618 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01104 | 0.01567 | 12.82 | 10.17 |
