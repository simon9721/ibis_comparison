# S11-like TX Correction Prototype

This augments an accepted S31 reduced model with a bench-scoped input reflection correction.

- Correction strength: `0.25`
- TX taus: `0.02 ns, 0.147361 ns, 1.08577 ns, 8 ns`
- TX gains: `-0.0130415, -0.0738412, 0.126733, 0.0291392`
- TX tail fast taus: `0.05 ns`
- TX tail slow taus: `2 ns`
- TX tail gains: `0.0230419`

| case | class | RX RMSE (V) | TX RMSE (V) | RX rise delta (ps) | RX fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01476 | 0.03535 | -4.111 | 3.672 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01456 | 0.03454 | -6.049 | 0.7153 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01381 | 0.03242 | 0.09558 | -3.93 |
