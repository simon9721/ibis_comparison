# S-parameter Transient Audit Comparison

- HSPICE dir: `results/sparam_cisco_native_hspice_2026-06-08/Ch10_35_5F3N_t_long`
- ngspice dir: `results/sparam_cisco_delay_reduced_2026-06-08/Ch10_35_5F3N_t/ngspice`
- Cases compared: 3
- PASS: 0
- FAIL: 3

## Thresholds

- RX active RMSE pass: `0.02 V`
- RX active maxabs pass: `0.075 V`
- Incremental delay delta pass: `25.0 ps`
- TX active RMSE pass: `0.08 V`

## Cases

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | plot |
|---|---:|---:|---:|---:|---:|---|
| `audit_amp1p5_edge500_r50` | `FAIL` | 0.02191 | 0.05424 | 56.79 | 52.67 | `results/sparam_cisco_delay_reduced_2026-06-08/Ch10_35_5F3N_t/comparison/audit_amp1p5_edge500_r50_hspice_vs_ngspice.png` |
| `audit_amp1p5_edge50_r50` | `FAIL` | 0.02224 | 0.06876 | 70.76 | 64.72 | `results/sparam_cisco_delay_reduced_2026-06-08/Ch10_35_5F3N_t/comparison/audit_amp1p5_edge50_r50_hspice_vs_ngspice.png` |
| `audit_amp1p5_edge5_r50` | `FAIL` | 0.02257 | 0.07265 | 72.9 | 67.24 | `results/sparam_cisco_delay_reduced_2026-06-08/Ch10_35_5F3N_t/comparison/audit_amp1p5_edge5_r50_hspice_vs_ngspice.png` |
