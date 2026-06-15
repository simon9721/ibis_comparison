# ngspice S-Parameter Equivalent Compatibility Notes

Test target:

```text
hspice/sparam_ngspice/Clarity_example.sp
```

This is a scikit-rf vector-fitted equivalent generated from:

```text
hspice/sparam/Clarity_example.S2P
```

## Findings

The raw Touchstone samples look passive at the sampled frequencies:

- Frequency range: `50 MHz` to `2 GHz`
- Points: `40`
- Maximum sampled singular value: `0.9981438316`
- Maximum sampled `|S21|`: `0.9976552222`
- Maximum sampled `|S11|`: `0.0811776582`

The ngspice equivalent parses correctly. The issue is transient stability.

## Channel-Only Tests

Sweep script:

```text
scripts/sweep_sparam_ngspice_channel.py
```

Sweep outputs:

```text
hspice/sparam_ngspice/channel_sweep/summary.csv
```

Main result:

| Drive setup | Result |
|---|---|
| Ideal voltage source directly into `p1` | Fails for all tested amplitudes and edge rates |
| `0.1 ohm` to `25 ohm` source resistance | Fails later, but still blows up |
| `50 ohm` source resistance and `50 ohm` load | Completes to `12 ns` for 5 ps, 50 ps, and 500 ps edges |
| `100 ohm` source resistance | Fails early |

Representative failures:

- Direct ideal source, 1.5 V, 5 ps edge: aborts near `5.110 ns`, raw output grows to about `1e23 V` on `ntst`.
- Direct ideal source, 0.05 V, 5 ps edge: still aborts near `5.386 ns`, so this is not only a large-signal issue.

Representative passes:

- `50 ohm` source, 1.5 V, 5 ps edge: completes to `12 ns`, finite but visibly underdamped.
- `50 ohm` source, 1.5 V, 500 ps edge: completes to `12 ns`, bounded response.
- `50 ohm` source, 0.05 V, 5 ps edge: completes to `12 ns`, bounded response.

## Interpretation

The exported `s_equivalent` behaves like a port-normalized macromodel that is numerically stable only when driven in a near-`Z0=50 ohm` environment. It is not robust when an ideal voltage source, a very low source impedance, or the pybis driver directly drives the port.

The HSPICE deck is not using this exported equivalent. It uses the native HSPICE S-element:

```text
.MODEL ch_model S
+ TSTONEFILE='Clarity_example.S2P'
+ Z0=50
+ RATIONAL_FUNC=1
+ INTERPOLATION=HYBRID
+ LOWPASS=1
+ HIGHPASS=3
+ PASSIVE=1
```

Those HSPICE options explicitly request rational fitting, extrapolation handling, and passivity enforcement. The scikit-rf exported ngspice subcircuit does not carry equivalent simulator-side `PASSIVE`, `LOWPASS`, or `HIGHPASS` behavior.

## Practical Next Steps

For ngspice, avoid driving `Clarity_example.sp` directly from a low-impedance source. At minimum, use a `50 ohm` source environment for standalone channel validation.

For driver/channel co-simulation, the better fix is to regenerate the ngspice-compatible macromodel with passivity enforcement and controlled high-frequency extrapolation, or to synthesize a simpler stable RLGC / W-element-like channel for time-domain comparison.
