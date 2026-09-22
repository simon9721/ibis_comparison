# Fast-IBIS Runtime Ku/Kd Comparison

This package makes the primary comparison apples-to-apples. Every plotted
coefficient is a runtime signal from the same normal complete-pulse bench:

- HSPICE native IBIS runtime `Ku/Kd`.
- ngspice legacy pybis runtime `Ku/Kd`.
- ngspice directional+residual gate-state runtime `Ku/Kd`.

No HSPICE or ngspice simulations were rerun. The figures and metrics use the
cached aligned data from the corrected 5 ps IBIS study.

## Runtime Finding

- Legacy pybis full-window time-weighted Ku/Kd RMSE versus HSPICE is
  `0.02975` / `0.01789`.
- Outside the first 50 ps impulse after each edge, legacy pybis Ku/Kd RMSE is
  `0.00429` / `0.00349`.
- The legacy model therefore reproduces the main normal coefficient
  trajectories closely, while its immediate edge impulses differ from HSPICE.
- The current gate-state model full-window Ku/Kd RMSE is
  `0.74371` / `0.17373`.
- The gate-state result is invalid as a model-quality claim because its offline
  endpoint/reconstruction gate failed before runtime.

## Offline Diagnostic Is Separate

HSPICE does not provide an exported offline Ku/Kd table in this workflow.
The existing `../figures/fast_ibis_reconstruction_gate.png` compares only:

1. pybis offline-derived coefficient tables, and
2. the gate-state model's offline reconstruction of those tables.

It must not be described as an offline HSPICE-versus-pybis comparison.

## Figures

- `plots/01_runtime_full_transition.png`
- `plots/02_runtime_rising_edge_zoom.png`
- `plots/03_runtime_falling_edge_zoom.png`
- `plots/04_runtime_main_transition_body.png`

## Numeric Data

- `runtime_metrics.csv`: time-weighted RMSE and maximum error by analysis window.
- `runtime_edge_ranges.csv`: Ku/Kd minima and maxima in each 50 ps edge window.
- `normal_runtime_kukd_aligned.csv`: the actual aligned runtime samples.
