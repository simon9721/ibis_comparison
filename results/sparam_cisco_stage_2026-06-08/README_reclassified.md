# Reclassified S-parameter Quality Results

## Updated Gates

- Low-frequency coverage: first Touchstone point must be <= `5e+09` Hz
- Minimum frequency points: `8`
- HSPICE timing pass: Rx RMSE <= `0.1` V and abs 50% delay deltas <= `25` ps
- HSPICE edge pass: Rx RMSE <= `0.02` V, Rx max abs <= `0.075` V, and abs 50% delay deltas <= `5` ps

## Summary

- Metric PASS channels: 0
- Metric FAIL channels: 5
- HSPICE timing channel PASS: 0
- HSPICE timing channel FAIL: 0
- HSPICE timing NO_AUDIT channels: 5
- HSPICE edge channel PASS: 0
- HSPICE edge channel FAIL: 0
- HSPICE edge NO_AUDIT channels: 5
- Overall channel PASS: 0
- Overall channel FAIL: 5
- Overall channel NO_AUDIT: 0

## Channel Classification

| Channel | Selected Model | Metric | Timing | Edge | Overall | Reason |
|---|---|---|---|---|---|---|
| `Ch10_35_5F3N_f5_3a904f20` | `` | `FAIL` | `NO_AUDIT` | `NO_AUDIT` | `FAIL` | no candidate passed updated math + ngspice gates |
| `Ch10_35_5F3N_n3_a9ef8f2b` | `` | `FAIL` | `NO_AUDIT` | `NO_AUDIT` | `FAIL` | no candidate passed updated math + ngspice gates |
| `Ch10_35_5F3N_t_d3c7dddc` | `` | `FAIL` | `NO_AUDIT` | `NO_AUDIT` | `FAIL` | no candidate passed updated math + ngspice gates |
| `Ch10_35_8F_f8_95b91b5e` | `` | `FAIL` | `NO_AUDIT` | `NO_AUDIT` | `FAIL` | no candidate passed updated math + ngspice gates |
| `Ch10_35_8F_t_99349b74` | `` | `FAIL` | `NO_AUDIT` | `NO_AUDIT` | `FAIL` | no candidate passed updated math + ngspice gates |

## HSPICE Audit Cases

| Channel | Case | Candidate | Metric | Timing | Edge | Overall | Rx RMSE (V) | Rx Max Abs (V) | Rise Delta (ps) | Fall Delta (ps) |
|---|---|---|---|---|---|---|---:|---:|---:|---:|
