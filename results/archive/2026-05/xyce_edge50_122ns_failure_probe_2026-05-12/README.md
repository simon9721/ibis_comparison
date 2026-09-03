# Xyce Edge50 122 ns Failure Probe

Focused Xyce-only probe for the `edge50_flat4p2` model under the stressed
2 ns UI / 30 cm coarse RLGC / loss x5 setup.

## Runs

| Run | Bits | Loss | Return | Timeout | End ns | Completed | Note |
|---|---:|---:|---:|---:|---:|---:|---|
| prbs60_loss5_pass | 60 | 5 | 0 | False | 120.000 | True | verified passing boundary run |
| prbs62_loss5_fail | 62 | 5 | timeout | True | 122.260 | False | includes the 122 ns 00->10 edge |
| prbs62_loss1_check | 62 | 1 | timeout | True | 122.260 | False | same edge with lower channel loss |

## Key Files

- `run_summary.csv`: run status and stop time
- `edge_contexts_prbs62.csv`: PRBS edge contexts through the failing edge
- `tail_prbs62_loss5_fail.csv`: last printed values before timeout
- `plots/edge50_prbs62_fail_internal_window.png`: internal controls around 122 ns
- `plots/edge50_pass_fail_boundary_overlay.png`: pass/fail boundary comparison
