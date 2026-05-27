## Timing Offset Constancy Study

Date: 2026-05-20

### Goal

Check whether the time offset between the original refspice model and the converted pybis model is close to constant:

1. within one testbench across many transitions
2. across different testbench setups

### Benches

Two testbench families were used, both driven by the same deterministic multi-transition pattern:

- simple fixture:
  - `50 ohm` matched load
  - `30 ps` observation line
- actual channel:
  - `channel.sp` 10-section RLGC ladder
  - `85 ohm` termination

The input pattern after initial low is:

`1 0 1 1 0 0 1 0`

which gives six analyzed transitions:

`R F R F R F`

### Measurement

For each transition, the output crossing time was measured at:

- threshold = `0.75 V`

Reported delay is:

- `pybis crossing time - refspice crossing time`

So positive delay means pybis is later than refspice.

### Results Summary

#### Simple fixture / pad

- mean delay: `0.632261 ns`
- std dev: `0.033959 ns`
- span: `0.101413 ns`

Per-edge delays:

- rise 1: `0.624429 ns`
- fall 2: `0.627937 ns`
- rise 3: `0.603618 ns`
- fall 4: `0.626572 ns`
- rise 5: `0.605979 ns`
- fall 6: `0.705032 ns`

Observation:

- mostly clustered around `0.61 to 0.63 ns`
- last falling edge is noticeably larger

#### Actual channel / tx pad

- mean delay: `0.640085 ns`
- std dev: `0.015225 ns`
- span: `0.034408 ns`

Per-edge delays:

- rise 1: `0.648359 ns`
- fall 2: `0.624369 ns`
- rise 3: `0.658776 ns`
- fall 4: `0.625218 ns`
- rise 5: `0.657679 ns`
- fall 6: `0.626107 ns`

Observation:

- not one constant delay across all edges
- but very consistent inside each polarity family
  - rises around `0.655 ns`
  - falls around `0.625 ns`

#### Actual channel / rx load

- mean delay: `0.641621 ns`
- std dev: `0.017267 ns`
- span: `0.041342 ns`

Per-edge delays:

- rise 1: `0.618389 ns`
- fall 2: `0.658612 ns`
- rise 3: `0.626456 ns`
- fall 4: `0.657361 ns`
- rise 5: `0.629175 ns`
- fall 6: `0.659731 ns`

Observation:

- again, not one constant delay across all edges
- strong polarity split
  - rises around `0.62 to 0.63 ns`
  - falls around `0.658 to 0.660 ns`

### Conclusions

1. The offset is **not perfectly constant for all transitions**.
2. The offset is **close to constant within a given testbench**, but not exact.
3. In the actual-channel test, the offset is better described as **two nearly constant values**, one for rises and one for falls.
4. The average delay level is similar across benches, around `0.63 to 0.64 ns`, but the edge-to-edge structure is different.
5. Therefore, a **single global time shift** is only a first-order approximation.

### Practical Recommendation

If an offset is needed for plotting/alignment:

- better than nothing:
  - use one global shift around `0.64 ns`
- better for the actual-channel case:
  - use separate rise and fall shifts

Suggested first-pass channel shifts from this study:

- tx pad:
  - rise: about `0.655 ns`
  - fall: about `0.625 ns`
- rx load:
  - rise: about `0.625 ns`
  - fall: about `0.659 ns`

### Artifacts

- raw measurements:
  - `timing_offset_constancy.csv`
- text summary:
  - `timing_offset_constancy_summary.txt`
- plot:
  - `plots/timing_offset_constancy.png`
