# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line, parallel RC residual branches, and optional zero-DC tail branches.

## Fitted Parameters

- Explicit delay: `7.39758 ns`
- DC gain to loaded output: `0.872583`
- Branch taus: `0.069538 ns, 0.154324 ns, 0.231396 ns, 1.28162 ns`
- Branch gains: `0.278441, 0.0661333, 0.437027, 0.0909822`
- Tail fast taus: `0.875053 ns`
- Tail slow taus: `2.21006 ns`
- Tail gains: `0.0261652`

## HSPICE Correlation

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.01247 | 0.04018 | 17.12 | -5.029 | 0.02391 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.01203 | 0.02119 | 1.619 | 5.445 | 0.02354 |
| `audit_amp1p5_edge500_r50` | `PASS` | 0.01261 | 0.02071 | 10.44 | 18.89 | 0.02391 |
