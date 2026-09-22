# Interrupted Switching Demo

This demo shows why the `short_pulse_2ns_high` case mismatches between HSPICE native IBIS and ngspice pybis.

The second input command arrives before the first output transition settles. That makes the switching coefficient history matter.

## Figures

- `figures/01_interrupted_event_timeline.png`: input command, pad voltage, and Ku/Kd coefficients on the same time axis.
- `figures/02_ku_kd_state_difference.png`: focused view of the coefficient-state split.
- `figures/03_pad_consequence.png`: output waveform consequence of the coefficient split.
- `figures/04_control_vs_interrupted.png`: normal full-toggle control vs interrupted switching.

## Key Numbers

- Settled high from the normal full-toggle bench: `1.545 V`.
- At the reverse command, HSPICE pad is only `0.266 V`, so the previous transition is not settled.
- HSPICE Ku peak during interrupted pulse: `0.543`.
- pybis Ku peak during interrupted pulse: `1.013`.
- HSPICE pad peak: `0.825 V`.
- pybis pad peak: `1.521 V`.
- Kd recovery 50 percent timing: pybis is about `360 ps` later than HSPICE.

## Interpretation

HSPICE does not let the pull-up coefficient complete a normal full transition after the input reverses. Ku remains partial, and the pad produces a partial pulse.

pybis allows Ku to reach near full strength before recovering. That creates a much larger output pulse. This is a state/history mismatch, not just a small timing offset.

So the risk condition is: a new switching event arrives before the previous output transition has settled. In that case, coefficient history and native IBIS state-machine behavior become important.
