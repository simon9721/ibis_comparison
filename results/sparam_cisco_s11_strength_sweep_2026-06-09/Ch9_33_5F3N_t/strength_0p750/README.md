# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.75`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.133724, -0.179875, 0.271924, 0.134337`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.225084`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01409 | 0.02144 | -20.75 | -7.992 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01361 | 0.0212 | -9.091 | -15.38 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01217 | 0.01893 | 17.82 | -0.758 |
