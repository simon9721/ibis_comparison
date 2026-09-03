# S-parameter Transient Audit Comparison

- HSPICE dir: `results/sparam_cisco_native_hspice_2026-06-08/Ch10_35_5F3N_t_long`
- ngspice dir: `results/sparam_cisco_delay_parallel_2026-06-08/Ch10_35_5F3N_t/ngspice_corrected`
- Cases compared: 3
- PASS: 3
- FAIL: 0

## Thresholds

- RX active RMSE pass: `0.02 V`
- RX active maxabs pass: `0.075 V`
- Incremental delay delta pass: `25.0 ps`
- TX active RMSE pass: `0.08 V`

## Cases

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | plot |
|---|---:|---:|---:|---:|---:|---|
| `audit_amp1p5_edge500_r50` | `PASS` | 0.006172 | 0.03387 | 12.02 | 16.56 | `results/sparam_cisco_delay_parallel_2026-06-08/Ch10_35_5F3N_t/comparison_corrected/audit_amp1p5_edge500_r50_hspice_vs_ngspice.png` |
| `audit_amp1p5_edge50_r50` | `PASS` | 0.003995 | 0.02184 | 3.643 | 2.007 | `results/sparam_cisco_delay_parallel_2026-06-08/Ch10_35_5F3N_t/comparison_corrected/audit_amp1p5_edge50_r50_hspice_vs_ngspice.png` |
| `audit_amp1p5_edge5_r50` | `PASS` | 0.003632 | 0.0102 | 5.798 | 3.654 | `results/sparam_cisco_delay_parallel_2026-06-08/Ch10_35_5F3N_t/comparison_corrected/audit_amp1p5_edge5_r50_hspice_vs_ngspice.png` |
