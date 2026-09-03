# S-parameter Transient Audit Comparison

- HSPICE dir: `results/sparam_cisco_native_hspice_2026-06-08/Ch10_35_5F3N_t_long`
- ngspice dir: `results/sparam_cisco_ngspice_forced_2026-06-08/Ch10_35_5F3N_t_vector16`
- Cases compared: 3
- PASS: 0
- FAIL: 3

## Thresholds

- RX active RMSE pass: `0.02 V`
- RX active maxabs pass: `0.075 V`
- Incremental delay delta pass: `25.0 ps`
- TX active RMSE pass: `0.05 V`

## Cases

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | plot |
|---|---:|---:|---:|---:|---:|---|
| `audit_amp1p5_edge500_r50` | `FAIL` | 0.1152 | 0.3014 | 462.8 | -276.9 | `results/sparam_cisco_ngspice_forced_2026-06-08/Ch10_35_5F3N_t_vector16_compare_v2/audit_amp1p5_edge500_r50_hspice_vs_ngspice.png` |
| `audit_amp1p5_edge50_r50` | `FAIL` | 0.1181 | 0.3292 | 474.7 | -213.3 | `results/sparam_cisco_ngspice_forced_2026-06-08/Ch10_35_5F3N_t_vector16_compare_v2/audit_amp1p5_edge50_r50_hspice_vs_ngspice.png` |
| `audit_amp1p5_edge5_r50` | `FAIL` | 0.1184 | 0.3417 | 468.1 | -202 | `results/sparam_cisco_ngspice_forced_2026-06-08/Ch10_35_5F3N_t_vector16_compare_v2/audit_amp1p5_edge5_r50_hspice_vs_ngspice.png` |
