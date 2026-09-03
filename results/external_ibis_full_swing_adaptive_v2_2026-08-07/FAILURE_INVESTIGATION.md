# Failure Investigation

## `buffer.ibs / driver`

- HSPICE native IBIS completed and produced a valid `.tr0`.
- pybis solved the rising coefficient pair, but its falling two-fixture linear system is singular.
- The retained conversion error is: `Falling coefficient extraction: LinAlgError: Singular matrix`.
- This is an extraction/data-conditioning failure, not an HSPICE deck failure.

## `io6_ft_1v8_lowspeed_pu`

- HSPICE native IBIS completed the adaptive 870.964 ns bench.
- Default ngspice advanced to 417.6969 ns, 0.2357 ns after the 417.4613 ns falling edge, then repeatedly retried the same time point until the 240 s timeout.
- A retained robust fallback (`run_robust.sp`) relaxed tolerances, enabled `rshunt`, raised `itl4`, and used first-order Gear. It advanced only to about 418.657 ns and stalled in the same falling-edge region.
- This is classified as a numerical/event-transition failure in the legacy `InputDriven` model, not merely a too-short timeout.
- The partial default and fallback raw/log files are retained under the model's `ngspice_legacy_pybis` case directory.
