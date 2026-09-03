# Parallel Delay-aware Reduced S-parameter Model

This prototype uses a 50 ohm explicit delay line plus parallel RC residual branches.

## Fitted Parameters

- Explicit delay: `12.4564 ns`
- DC gain to loaded output: `0.900336`
- Branch taus: `0.0698811 ns, 0.0846455 ns, 0.145768 ns, 1.02341 ns`
- Branch gains: `0.00202938, 0.0944389, 0.549042, 0.254826`

## Initial HSPICE Correlation

The initial fitted delay was close, but the 500 ps edge missed the rise timing
gate by about `6.8 ps`.

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | `PASS` | 0.007199 | 0.04095 | -8.922 | 11.52 | 0.02944 |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.006761 | 0.03159 | 2.751 | 4.329 | 0.02937 |
| `audit_amp1p5_edge500_r50` | `FAIL` | 0.008255 | 0.03394 | 31.78 | 23.59 | 0.02761 |

## Accepted Trimmed Correlation

Accepted trim: `-10 ps`, giving effective delay `12.4464 ns`.

Accepted model/results are in `trim_sweep/trim_m10ps/`.

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | PASS | 0.007983 | 0.04842 | -19.12 | 0.90 | 0.02944 |
| `audit_amp1p5_edge50_r50` | PASS | 0.006883 | 0.02876 | -6.74 | -5.47 | 0.02937 |
| `audit_amp1p5_edge500_r50` | PASS | 0.006463 | 0.03035 | 21.79 | 13.60 | 0.02761 |
