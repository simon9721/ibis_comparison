# io_buf Charge-Limited Gate-State pybis Retrigger Study

This study tests `InputDrivenChargeLimitedGateHybrid`, which replaces additive directional event taps with bounded pullup/pulldown charge states `QPU` and `QPD`.

## Headline

- Long-pulse control pad RMSE delta versus legacy: `4.069 mV`.
- Long-pulse control max Ku/Kd RMSE delta versus legacy: `0.00501`.
- ChargeLimitedHybrid coefficient-first improvements versus legacy: `3` / `6` interrupted cases.
- ChargeLimitedHybrid Kd RMSE improvements versus DirectionalHybrid: `4` / `6` interrupted cases.
- Charge-state over-cancel checks passed: `6` / `6` interrupted cases.
- Short-low `HRISE_AFTER_FALL` activations: `3` / `3` mirrored low-pulse cases.
- Primary `ChargeLimitedHybrid` uses the charge path for fall-after-rise short-high pulses only; `HRISE_AFTER_FALL` is reported as a diagnostic because enabling it in the primary hybrid regressed the long-pulse control.
- `ChargeLimitedFastRecover` keeps the mirrored-low path active as an experimental comparison; `ChargeLimitedFull` shows the bounded charge model itself can improve Kd, but with pad/Ku tradeoffs.
- `double_toggle_1ps` remains a stress failure for primary `ChargeLimitedHybrid`; this mode is not default-ready.
- `InputDrivenChargeLimitedGateFull` is diagnostic only and is not considered for default behavior.
- HSPICE is used only for validation; all charge-limited timing comes from IBIS/pybis coefficient tables.

## short_pulse_1ns_high Specific Numbers

- HSPICE Ku peak: `0.0746`
- legacy Ku peak: `1.0125`
- GateStateHybrid Ku peak: `0.0586`
- DirectionalHybrid Ku peak: `0.0440`
- ChargeLimitedHybrid Ku peak: `0.0586`
- ChargeLimitedFastRecover Ku peak: `0.5868`
- HSPICE pad peak: `0.0616 V`
- legacy pad peak: `1.5155 V`
- GateStateHybrid pad peak: `0.0802 V`
- DirectionalHybrid pad peak: `0.0253 V`
- ChargeLimitedHybrid pad peak: `0.0893 V`

## How To Read The Figures

- `*_01_input_pad_overlay.png`: input command and pad waveform, HSPICE vs each ngspice pybis mode.
- `*_02_ku_only.png`: Ku coefficient overlay only.
- `*_02_kd_only.png`: Kd coefficient overlay only.
- `*_03_charge_hybrid_charge_diagnostics.png`: QPU/QPD states, charge-mapped coefficients, and detector/latch activity.
- `high_vs_low_pulse_comparison.png`: mirrored 1 ns short-high vs short-low behavior.
- `short_pulse_summary_bars.png`: summary metrics beyond RMSE, including peaks, recovery, and overlap.

## Output Files

- `candidate_metrics.csv`: detailed per-case/per-variant metrics.
- `metrics_by_case.csv`: compact case comparison.
- `interrupted_switching_demo/demo_metrics.csv`: short-pulse-focused metrics.
