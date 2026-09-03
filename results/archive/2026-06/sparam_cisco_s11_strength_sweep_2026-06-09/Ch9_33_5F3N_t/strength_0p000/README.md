# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.133724, -0.179875, 0.271924, 0.134337`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.225084`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.0077 | 0.02944 | -19.26 | 1.742 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.006328 | 0.02937 | -7.602 | -5.682 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.006018 | 0.02761 | 20.25 | 12.59 |
