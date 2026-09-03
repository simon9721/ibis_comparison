# 2-port Delay-aware Reduced S-parameter Model

- Touchstone: `hspice/sparam/ch_model_fit.s2p`
- Selected S11 strength: `1`
- Selected strength directory: `results/sparam_s2p_reduced_2026-06-09/ch_model_fit/s11_strength_1`
- Selected overview plot: `results/sparam_s2p_reduced_2026-06-09/ch_model_fit/selected_overview.png`

## Fitted S21 Path

- Initial target gain to load: `0.994192`
- Fitted DC gain to load: `1.04401`
- Explicit delay: `0.326788 ns`
- Branch taus: `0.00409153 ns, 0.00476366 ns, 0.052767 ns, 0.0543909 ns`
- Branch gains: `1.01766, -0.739945, 0.221757, 0.544532`
- Tail fast taus: `0.0764465 ns`
- Tail slow taus: `19.7969 ns`
- Tail gains: `-0.0656688`
- Ring/feedthrough basis terms: `15` total, `15` nonzero-ish
- Ring gain max abs: `1.66`
- Ring delays: `0 ns, 0.04 ns, 0.08 ns, 0.14 ns, 0.22 ns`

## Strength Sweep

| S11 strength | pass | mean RX RMSE (mV) | max RX edge delta (ps) | mean TX RMSE (mV) | score |
|---:|---:|---:|---:|---:|---:|
| 0 | 2/3 | 14.35 | 23.43 | 11.79 | 101.3 |
| 0.25 | 2/3 | 14.86 | 22.6 | 10.38 | 101.3 |
| 0.5 | 2/3 | 15.2 | 21.76 | 8.993 | 101.3 |
| 0.75 | 2/3 | 15.93 | 20.94 | 7.638 | 101.3 |
| 1 | 2/3 | 16.58 | 20.1 | 6.324 | 101.3 |

## Key Files

- `native_hspice/native_hspice_audit.csv`: HSPICE S-element run summary
- `fit_preview.png`: analytic S21/S11 fit before ngspice
- `strength_sweep.csv`: per-strength summary
- `selected_model.sp`: duplicate of the selected ngspice model
- `selected_comparison.csv`: duplicate of the selected HSPICE-vs-ngspice comparison table

Note: the S11 correction is still bench-scoped. It improves this 50 ohm source/load audit, but it is not yet a general passive two-port reconstruction of S11/S12/S22.
