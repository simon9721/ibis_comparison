# 2-port Delay-aware Reduced S-parameter Model

- Touchstone: `hspice/sparam/Clarity_example.S2P`
- Selected S11 strength: `0.25`
- Selected strength directory: `results/sparam_s2p_reduced_2026-06-09/Clarity_example_richring/s11_strength_0p25`
- Selected overview plot: `results/sparam_s2p_reduced_2026-06-09/Clarity_example_richring/selected_overview.png`

## Fitted S21 Path

- Initial target gain to load: `0.992747`
- Fitted DC gain to load: `1.02545`
- Explicit delay: `0.28707 ns`
- Branch taus: `0.0797081 ns, 0.0913658 ns, 0.400294 ns, 19.3189 ns`
- Branch gains: `-0.72542, 1.88684, -0.184577, 0.0486086`
- Tail fast taus: `0.208726 ns`
- Tail slow taus: `0.219401 ns`
- Tail gains: `-1.17875`
- Ring/feedthrough basis terms: `32` total, `32` nonzero-ish
- Ring gain max abs: `10`
- Ring delays: `0 ns, 0.02 ns, 0.04 ns, 0.06 ns, 0.08 ns, 0.12 ns, 0.18 ns, 0.25 ns`

## Strength Sweep

| S11 strength | pass | mean RX RMSE (mV) | max RX edge delta (ps) | mean TX RMSE (mV) | score |
|---:|---:|---:|---:|---:|---:|
| 0.25 | 2/3 | 12.47 | 310.7 | 11.82 | 105.8 |

## Key Files

- `native_hspice/native_hspice_audit.csv`: HSPICE S-element run summary
- `fit_preview.png`: analytic S21/S11 fit before ngspice
- `strength_sweep.csv`: per-strength summary
- `selected_model.sp`: duplicate of the selected ngspice model
- `selected_comparison.csv`: duplicate of the selected HSPICE-vs-ngspice comparison table

Note: the S11 correction is still bench-scoped. It improves this 50 ohm source/load audit, but it is not yet a general passive two-port reconstruction of S11/S12/S22.
