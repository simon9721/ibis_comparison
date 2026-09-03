# Ku/Kd Analysis: Loaded-Swing Stress Sweep

## Scope

This report analyzes all 30 loaded-swing reversal cases:

- Buffers: `io_buf`, `inv_chain`, and `ex2`
- Directions: short-high and short-low
- HSPICE transistor loaded-swing targets: 90%, 80%, 70%, 60%, and 50%
- References: cached HSPICE native-IBIS `Ku/Kd`
- ngspice candidates: full directional dual-residual gate-state and directional dual-residual hybrid

The HSPICE transistor waveform selected each pulse width. The same stimulus was applied to native HSPICE IBIS and both ngspice candidates. No HSPICE simulation was rerun for this extension.

## First Interpretation Constraint

The 90%-to-50% target is based on the transistor pad swing, not on native-IBIS coefficient progress. Equal target labels therefore do not mean equal native-IBIS stress.

At the 50% transistor target:

| Buffer | Short-high native-IBIS swing | Short-low native-IBIS swing |
|---|---:|---:|
| io_buf | 29.73% | 8.80% |
| inv_chain | 91.83% | 88.51% |
| ex2 | 85.11% | 94.86% |

This large separation is itself a finding. It explains why one universal error-versus-target trend does not exist across the three buffers.

## Native HSPICE IBIS Behavior

### io_buf

- Short-high has a real partial-state sequence. Native `Ku` at the reverse edge decreases from 0.723 at the 90% target to 0.348 at 50%, while native `Kd` remains near off at 0.009 to 0.024.
- Short-low behaves differently. Native `Ku/Kd` are still approximately 1/0 at the reverse edge for every target. The low command has not yet produced the coefficient trajectory that the full gate-state model has already begun.
- Native fast-IBIS coefficients include large excursions. Across the short-low active windows, native `Ku` reaches approximately -0.653 to 2.413 and native `Kd` reaches approximately -0.609 to 0.759. These excursions are present in the reference and must not be confused with gate-state-only overshoot.

### inv_chain

- At the reverse edge, native coefficients remain at their settled values for all five stress targets: about 0/1 for short-high and 1/0 for short-low.
- The meaningful native response appears after the reverse command. The delayed response to the first edge and the response to the reverse edge overlap in time.
- This is why errors are nearly zero before reversal but large afterward. The main challenge is delayed event interaction/recovery, not initial-state estimation.

### ex2

- Native and gate-state coefficients agree closely before reversal in both directions.
- Short-high remains the most reproducible gate-state case. Its native and gate-state trajectories preserve the same multi-stage shape and excursions over all five targets.
- Short-low shows a sharp regime change between the 80% and 70% transistor targets. The native recovery changes earlier than the gate-state recovery, and the first-order hidden state does not reproduce that staging.

## Full Gate-State Findings

Aggregate active-window RMSE:

| Buffer | Direction | Pad RMSE | Ku RMSE | Kd RMSE | Main error location |
|---|---|---:|---:|---:|---|
| io_buf | short-high | 446.48 mV | 0.3945 | 0.2619 | before and after reverse |
| io_buf | short-low | 547.23 mV | 0.7925 | 0.5574 | before and after reverse |
| inv_chain | short-high | 342.94 mV | 0.3584 | 0.2985 | after reverse |
| inv_chain | short-low | 370.82 mV | 0.4567 | 0.3722 | after reverse |
| ex2 | short-high | 35.15 mV | 0.0868 | 0.0567 | mostly after reverse, low magnitude |
| ex2 | short-low | 185.33 mV | 0.2185 | 0.1474 | after reverse; boundary at 80% to 70% |

### Concrete full-model bug in io_buf

The generated fast `io_buf` full model initializes `Ku=0.3116` and `Kd=0.7871`. Native HSPICE begins in the settled low state at `Ku=0`, `Kd=1`.

The full model uses coefficient-table endpoint values as capacitor initial conditions. For this fast `io_buf` characterization, those fitted endpoints are not the native runtime logical initialization. The result is a baseline coefficient mismatch before an interruption is even evaluated.

This is not the only `io_buf` problem, but it is a definite implementation defect. The short-low case also shows a command-to-coefficient timing mismatch: native HSPICE remains at 1/0 at reversal while the full hidden state has already moved substantially.

### Root-cause split

- `io_buf`: base-state initialization and command timing are wrong, then recovery is also wrong.
- `inv_chain`: base behavior is correct before reversal; delayed retrigger/recovery shape is wrong.
- `ex2`: base behavior is correct; the model is useful for short-high, while short-low exposes a nonlinear/multi-stage recovery boundary.

## Hybrid Findings

The hybrid uses legacy table replay outside interruption and gate-state coefficients while `HHYBRIDACTIVE` is asserted.

Coverage:

- Completed: 30/30
- Hybrid detector activated: 30/30
- Better than full gate-state: pad 15/30, Ku 20/30, Kd 18/30

Aggregate active-window RMSE:

| Buffer | Direction | Pad RMSE | Ku RMSE | Kd RMSE | Result versus full gate-state |
|---|---|---:|---:|---:|---|
| io_buf | short-high | 193.16 mV | 0.3563 | 0.1600 | substantial containment, still inaccurate |
| io_buf | short-low | 561.86 mV | 0.7825 | 0.5524 | no useful improvement |
| inv_chain | short-high | 342.93 mV | 0.3167 | 0.2891 | coefficients modestly improve; pad is unchanged |
| inv_chain | short-low | 363.65 mV | 0.4167 | 0.3264 | modest coefficient improvement |
| ex2 | short-high | 57.26 mV | 0.1090 | 0.0821 | regresses the best full-gate result |
| ex2 | short-low | 185.54 mV | 0.2110 | 0.1580 | mixed; no robust improvement |

### Why hybrid helps some cases

- Before interruption, hybrid uses legacy replay. This removes the full-model `io_buf` initial-state error and preserves the nearly exact `inv_chain` settled behavior.
- During interruption, it still uses the same gate-state trajectory. It therefore cannot fix a bad recovery law; it only limits where that law is used.

### Confirmed hybrid switching bug

The current generated hybrid selects its final coefficients with a hard conditional between legacy and gate-state paths. It does not align or blend the two values before switching.

Measured consequences:

- Coefficient jump greater than 0.10 in 17/30 cases
- Every `io_buf` case exceeds the 0.10 jump gate
- Seven of ten `ex2` cases exceed the gate
- Worst measured jump: 1.758 for `io_buf Ku` in the active-boundary measurement
- `inv_chain` did not show a large final-output jump in the sampled waveforms, despite the two internal paths following different trajectories

The hybrid is therefore not continuous by construction. Any apparent pad improvement must be checked against this coefficient switch defect.

### Fixed-duration activation limitation

Hybrid active duration varies little with stress depth:

| Buffer | Active-duration range |
|---|---:|
| io_buf | 3.928 to 4.756 ns |
| inv_chain | 0.435 to 0.467 ns |
| ex2 | 2.189 to 2.295 ns |

The window is primarily tied to each IBIS-derived recovery duration, not to actual state agreement between the legacy and gate paths. This makes the handoff too long for some cases and too short or mistimed for others.

## Trend Conclusions

1. Stronger transistor stress does not guarantee monotonic Ku/Kd error because the native IBIS model may experience a very different effective stress.
2. `ex2` short-high is the only consistently strong full gate-state region. Hybrid should not replace it there.
3. `ex2` short-low has a real 80%-to-70% boundary caused by recovery staging, not by initial-state mismatch.
4. `inv_chain` isolates a retrigger/recovery problem: pre-reversal coefficients are essentially exact, while nearly all error occurs after reversal.
5. `io_buf` exposes two earlier failures: wrong full-model coefficient initialization and wrong command-to-state timing, especially for short-low.
6. The current hybrid contains some baseline errors but adds a hard-switch discontinuity. It is a diagnostic experiment, not a production candidate.

## Recommended Next Work

1. Normalize or separately define runtime logical initial conditions. Do not initialize full gate-state coefficients directly from problematic fast-table endpoints.
2. Add explicit command-delay state so the hidden gate state does not move before native IBIS coefficient activity begins.
3. Replace the hard hybrid selector with a state-aligned handoff. Entry should begin only when legacy and gate-state coefficients are close, or use a continuous blend whose jump is independently bounded.
4. End hybrid mode based on coefficient/state agreement, not only a fixed recovery timer.
5. Re-test first on the diagnostic cases:
   - `inv_chain` for pure post-reversal recovery
   - `ex2` short-high as the no-regression control
   - `ex2` short-low around 80%/70% for the recovery boundary
   - `io_buf` short-low only after initialization and delay are corrected

## Evidence Files

- `comparison_metrics.csv`
- `coefficient_diagnostics.csv`
- `summary_by_device_direction.csv`
- `analysis_plots/01_kukd_rmse_vs_stress.png`
- `analysis_plots/02_pre_vs_post_reverse_error.png`
- `analysis_plots/03_hybrid_switch_jumps.png`
- `figures/<buffer>/<direction>/swing_<target>/waveforms.csv`
