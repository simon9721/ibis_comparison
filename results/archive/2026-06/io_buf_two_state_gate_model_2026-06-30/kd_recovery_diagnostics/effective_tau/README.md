# Effective Kd Recovery Tau Diagnostic

This diagnostic fits the HSPICE native-IBIS Kd recovery after the post-reverse Kd minimum, not directly from the input reverse edge. That matters because in short-high pulses Kd is still near its on-state at the input falling edge; the delayed rising-edge response turns Kd off first, then Kd recovers.

- Apparent min-to-final tau spread: `1.720x`
- Main-slope 10%-90% tau spread: `1.086x`
- Verdict: `NONLINEAR_OR_MULTI_STAGE_RECOVERY`
- The apparent exponential fit is intentionally reported with RMSE/R2. Poor R2 means the recovery is not a clean one-pole exponential; use the tau as a diagnostic, not as a direct parameter table.

| Case | Pulse ns | HSPICE Kd min | Kd off-depth | Apparent tau ns | 10-90 tau ns | Min-to-10 delay ns | Fit RMSE | Fit R2 | Residual GDN at input reverse | Residual GDN min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| short_pulse_500ps_high | 0.500 | -0.0225 | 1.0214 | 1.0008 | 0.1737 | 1.2983 | 0.32296 | -0.0524 | 1.0000 | 0.0016 |
| short_pulse_1ns_high | 1.000 | -0.0632 | 1.0605 | 1.5465 | 0.1887 | 1.4623 | 0.33564 | 0.1160 | 1.0000 | 0.0002 |
| short_pulse_2ns_high | 2.000 | -0.0720 | 1.0567 | 1.7217 | 0.1857 | 1.5863 | 0.35702 | -0.0213 | 0.0977 | 0.0000 |

## Interpretation

- If the apparent HSPICE tau changes strongly with pulse width or Kd off-depth, the NMOS re-turn-on is not well represented by one constant recovery law.
- If the 10%-90% tau is steadier than the apparent tau, then much of the width-dependence is delayed/flat early recovery rather than the main slope itself.
- `Residual GDN at input reverse` is included as a sanity check. In this delayed-gate model it stays near 1 at the input reverse edge, so it is not a useful interruption-depth variable by itself.
- `HSPICE Kd min` / `Kd off-depth` is the better observable depth proxy because it comes from the golden coefficient waveform.

Figures:

- `hspice_effective_tau_vs_depth.png`
- `hspice_kd_recovery_tau_fits.png`
