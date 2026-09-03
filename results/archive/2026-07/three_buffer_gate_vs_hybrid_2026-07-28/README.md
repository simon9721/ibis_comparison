# Three-Buffer Full Gate-State vs Reversal Hybrid

Presentation figures intentionally omit legacy pybis. The comparison is HSPICE native IBIS versus the always-active full gate-state model and the legacy-normal/gate-on-reversal hybrid. HSPICE transistor output is included on pad panels only.

## Scope

- Cases plotted: `32` across `io_buf`, `inv_chain`, and `ex2`, slow and fast IBIS.
- Completed hybrid cases: `31/32`.
- Hybrid improves pad, Ku, and Kd RMSE together versus full gate-state in `19/31` completed cases.
- HSPICE was not rerun. Existing aligned HSPICE/full-gate data were reused; only missing hybrid ngspice cases were simulated.
- The hybrid still contains legacy replay internally for settled operation, but no standalone legacy waveform is plotted.

## Important Limits

- `inv_chain` uses the newly certified forced-reversal widths.
- `io_buf` uses the established 1 ns and 2 ns interrupted cases. Its pullup and pulldown delays are so asymmetric that both hidden states cannot generally be partial at the same delayed reverse instant.
- `ex2` uses 50 ps, 500 ps, and 1 ns interrupted cases. The full gate-state reconstruction gate remains failed, so these are diagnostic comparisons.
- Prior normal-control hybrid runs were numerically stiff because hidden states are tracked continuously. This package does not promote the hybrid as production-ready.

## Figures

- `<device>/<profile>/plots/`: one three-panel pad/Ku/Kd figure per case.
- `<device>/<profile>/contact_sheet.png`: profile-level overview.
- Black: HSPICE native IBIS; gray: HSPICE transistor pad; red: gate state model; purple: hybrid model.

## Numeric Outputs

- `metrics.csv`: independent full-gate and hybrid errors versus native IBIS.
- `comparison_summary.csv`: direct hybrid-minus-full RMSE deltas.
- `<device>/<profile>/waveform_data/*.csv`: exact plotted data.
- `hybrid_failures.csv`: any ngspice hybrid failures and preserved log paths.

## Hybrid Failures

- `io_buf/fast/short_pulse_2ns_high`: prior hybrid ngspice run did not complete