# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `1`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.168179, -0.196258, 0.280964, 0.168031`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.277434`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.0149 | 0.01664 | -3.899 | -20.03 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01459 | 0.01582 | -6.604 | -21.39 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01329 | 0.01333 | 1.218 | -6.743 |
