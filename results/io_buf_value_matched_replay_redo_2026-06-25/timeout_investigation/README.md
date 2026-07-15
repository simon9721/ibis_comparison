# Value-Matched Replay Timeout Investigation

This folder analyzes why `short_pulse_2ns_high` produced no value-matched waveform in the canonical redo.

## Findings

- The value-matched run is not zero-progress. It completes to `7.25 ns`, but accepted timesteps collapse after the falling/reverse edge at `7.0 ns`.
- Stop-time bracketing shows the row explosion directly: `7.25 ns` completes with about 196k rows, while `7.5 ns` and later do not complete within the debug timeout.
- The immediate mechanism is stiffness in the capacitor-backed `Ku/Kd` states with `coeff_tau=1p` while tracking a discontinuous/jagged value-matched target.
- The deeper algorithmic issue is that `VMARG` briefly includes the old rising-edge elapsed time before the delayed legacy edge timer resets. Around the falling edge, `VMARG` jumps from the old-transition region into the value-matched falling-table region.
- Ku-derived and Kd-derived falling-table start times disagree by nearly `1.94 ns`, so the balanced table-start assumption is physically ambiguous.
- Increasing only `coeff_tau` to `5p` or larger makes ngspice complete, proving the timeout is a stiffness/numerical robustness issue, but coefficient accuracy remains poor, especially `Kd`.

## Presentation Explanation

There are two separate effects:

1. Why the `KuTarget` / `KdTarget` traces look strange.
2. Why the full ngspice run times out.

`KuTarget` and `KdTarget` are internal pybis value-match commands, not HSPICE reference signals. The generated logic is:

```spice
VMSTART = inferred opposite-table start time
VMARG = VMSTART + edge_elapsed_time
KUMATCH = opposite Ku table evaluated at VMARG
KDMATCH = opposite Kd table evaluated at VMARG
KuTarget = value_match_active ? KUMATCH : legacy_Ku
KdTarget = value_match_active ? KDMATCH : legacy_Kd
Ku/Kd follow those targets with coeff_tau=1p
```

For `short_pulse_2ns_high`, the falling edge arrives while the rising transition is genuinely mid-transition. At that instant the current `Ku` and `Kd` can still be explained by one rising-table time, but they cannot be explained by one falling-table time. The inferred falling-table starts are far apart: `TF_KU ~= 0.86 ns` and `TF_KD ~= 2.48 ns` from the table snapshot, with the raw run showing disagreement around `1.87 ns`.

The algorithm forces one shared midpoint anyway. That means the replay argument points to a falling-table region where `Ku` is already nearly off, while `Kd` is being driven strongly back on. This is why Figure 05 shows `KuTarget` dropping and `KdTarget` jumping/ramping high. The target behavior is not a physical HSPICE behavior; it is the value-match algorithm exposing its own bad assumption.

The timeout is the numerical consequence of that bad target. `Ku` and `Kd` are capacitor-backed state nodes driven toward `KuTarget`/`KdTarget` with `coeff_tau=1p`. When the target is discontinuous/jagged, ngspice must take extremely tiny timesteps to follow the 1 ps state equations. Stop-time bracketing shows the collapse:

| Stop time | Status | Rows | Minimum dt |
|---:|---|---:|---:|
| `7.01 ns` | complete | `9,422` | `8.47e-08 ns` |
| `7.05 ns` | complete | `9,735` | `2.00e-11 ns` |
| `7.10 ns` | complete | `12,313` | `9.24e-14 ns` |
| `7.25 ns` | complete | `195,732` | `4.44e-15 ns` |
| `7.50 ns` | timeout / unusable | `1` | n/a |

This is why the canonical full run times out: the simulator does not hit a clean syntax error; it gets trapped taking near-zero timesteps after the reverse edge.

The `coeff_tau` sweep confirms the root cause. When `coeff_tau` is relaxed to `5p` or larger, the same logic completes to `14 ns`, but the coefficients are still wrong, especially `Kd`. So the timeout is not the main scientific failure. The main failure is the shared value-match replay assumption; the timeout is what happens when that flawed target is driven through a very stiff 1 ps follower.

## Artifacts

- `timeout_bracket.csv`: stop-time bracketing and timestep statistics.
- `coeff_tau_sweep.csv`: controlled tau variants for the same value-matched logic.
- `01_internal_diagnostics_stop_7p25ns.png`: internal waveforms and timestep collapse.
- `02_coeff_tau_sweep_metrics.png`: completed tau-variant metric summary.

## Tau Sweep Summary

| coeff_tau | status | pad RMSE mV | Ku RMSE | Kd RMSE | pad peak V | Ku peak | Kd min |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1p | partial_unusable | n/a | n/a | n/a | n/a | n/a | n/a |
| 2p | partial_unusable | n/a | n/a | n/a | n/a | n/a | n/a |
| 5p | complete | 255.251 | 0.157 | 0.6159 | 0.2543 | 0.262 | 0.05426 |
| 10p | complete | 254.431 | 0.1693 | 0.4796 | 0.2484 | 0.2576 | -0.01758 |
| 20p | complete | 254.920 | 0.1692 | 0.4615 | 0.2382 | 0.2474 | -0.01585 |
| 50p | complete | 253.069 | 0.1676 | 0.4465 | 0.2137 | 0.2193 | -0.01427 |
| 100p | complete | 248.978 | 0.1643 | 0.4394 | 0.1836 | 0.1887 | -0.01026 |

Best completed pad RMSE in this diagnostic sweep is `coeff_tau=100p`, but this is not a proposed fix because `Kd` RMSE remains high.
