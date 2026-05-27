# VREFH10 Inspection Notes

These notes explain why `io_vrefh10_std` and `io_vrefh10_slctrl` improved in the
full `C_comp=0` experiment while `io_vrefh5_std` and `io_zxover_std` did not.

## Key observations

1. The base pullup/pulldown IV tables are effectively the same across:
   - `io_vrefh10_std`
   - `io_vrefh10_slctrl`
   - `io_vrefh5_std`
   - `io_zxover_std`
   - `io_dig_slctrl`

   The meaningful differences are in:
   - clamp behavior
   - VT waveform shape / endpoint
   - `C_comp`

2. `io_vrefh10_*` has a non-negligible **ground clamp current in the normal operating range**:
   - about `0.282 mA` at `0.8 V`
   - about `0.997 mA` at `1.2 V`
   - about `1.747 mA` at `1.6 V`
   - about `4.426 mA` at `3.0 V`

   By comparison, `io_vrefh5_std`, `io_zxover_std`, and `io_dig_slctrl` have
   essentially zero ground-clamp current over the same range.

3. The selected `R_fixture=50, V_fixture=0` waveform for `io_vrefh10_*` is reduced-swing:
   - rise ends near `1.232 V`
   - fall starts near `1.232 V`

   The second waveform used in the solve (`R_fixture=50, V_fixture=3.3`) also does
   not fully reach rail:
   - rise ends near `3.193 V`

   For `io_vrefh5_std` and `io_zxover_std`, the corresponding second waveform reaches
   approximately `3.3 V`.

4. The `C_comp` term is large enough to materially perturb the `Ku/Kd` solve for `io_vrefh10_*`.
   Representative ratios of `|I_ccomp| / |I_rfix|`:
   - `io_vrefh10_slctrl` rising waveform 2: about `0.147`
   - `io_vrefh10_slctrl` falling waveform 1: about `0.218`
   - `io_vrefh10_std` rising waveform 1: about `0.163`
   - `io_vrefh10_std` falling waveform 1: about `0.215`

   For the comparison models:
   - `io_vrefh5_std`: roughly `0.09` to `0.13`
   - `io_zxover_std`: roughly `0.06` to `0.09`
   - `io_dig_slctrl`: roughly `0.05` to `0.07` on the dominant edges

## What actually improved

For `io_vrefh10_*`, the full-zero experiment improved the **falling edge** much more
than the rising edge.

- `io_vrefh10_slctrl`
  - rise RMS: `49.77 mV -> 49.70 mV`
  - fall RMS: `50.27 mV -> 40.60 mV`
  - score: `0.1213 -> 0.0887`

- `io_vrefh10_std`
  - rise RMS: `59.78 mV -> 58.83 mV`
  - fall RMS: `52.56 mV -> 42.89 mV`
  - score: `0.1063 -> 0.0935`

The solve itself shows why. In the falling-edge `Ku` table, the full-zero extraction
keeps `Ku` higher for longer during the first few nanoseconds:

- `io_vrefh10_slctrl`, falling:
  - at `3 ns`: `Ku 1.263 -> 1.289`
  - at `5 ns`: `Ku 0.240 -> 0.322`

- `io_vrefh10_std`, falling:
  - at `5 ns`: `Ku 0.239 -> 0.347`

This means the pullup stays active longer during the early fall, which slows the fall
and matches the IBIS waveform better.

## Why the same thing does not help `io_vrefh5_std` / `io_zxover_std`

For `io_vrefh5_std` and `io_zxover_std`, the full-zero extraction slightly improves the
fall RMS, but worsens the rise max error enough to make the overall score worse.

- `io_vrefh5_std`
  - fall RMS: `18.20 mV -> 9.10 mV`
  - rise max error increases: `72.57 mV -> 80.56 mV`
  - at `15 ns` on the rise: `Ku 0.924 -> 0.910`

- `io_zxover_std`
  - fall RMS: `14.95 mV -> 12.81 mV`
  - rise max error increases: `78.96 mV -> 83.24 mV`
  - at `15 ns` on the rise: `Ku 0.909 -> 0.902`

So in those more ordinary models, removing `C_comp` mainly makes the rise slightly too
weak / too slow around the late-rise region.

## Conclusion

The improvement in `io_vrefh10_*` is **not** explained by "`C_comp` is large" alone.
It appears to come from the combination of:

- relatively large `C_comp`
- non-zero in-band ground clamp current
- reduced-swing / non-full-rail waveform pair

That combination makes the standard `PU/PD + static clamps + C_comp` decomposition more
sensitive. For these models, including `C_comp` in the normal solve seems to turn off the
pullup too early on the falling edge.
