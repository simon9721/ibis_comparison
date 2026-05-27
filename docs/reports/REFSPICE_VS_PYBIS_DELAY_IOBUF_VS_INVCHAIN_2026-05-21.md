## Refspice vs pybis Delay: `io_buf` vs `inv_chain`

Date: 2026-05-21

### Goal

Compare the refspice-to-pybis time offset in two separate cases:

- `io_buf`
- `inv_chain`

and learn whether the observed delay behaves like:

- a nearly constant shift,
- a polarity-dependent shift,
- or a deeper shape/slew mismatch.

### Summary

The two cases behave very differently.

- `io_buf` shows a **large** delay, around `0.6 to 0.7 ns`, with clear polarity and threshold dependence.
- `inv_chain` shows a **tiny** delay, around `0 to 15 ps`, with much smaller dependence on threshold, edge polarity, and bench setup.

This means the large `io_buf` skew is **not** an inherent property of the `InputDriven` / T-line approach itself. If it were, `inv_chain` would show a comparable systematic delay, and it does not.

### Threshold-Dependence Check

To test whether the offset is a rigid time shift or partly a shape mismatch, crossing delays were compared at three voltage thresholds:

- `25%`
- `50%`
- `75%`

of the selected IBIS waveform swing.

Reported delay is always:

- `pybis crossing time - refspice crossing time`

So positive means pybis is later than refspice.

#### `io_buf` simple fixture

IBIS swing used:

- low = `0.000 V`
- high = `1.541 V`

Delays:

- rise:
  - `25%`: `0.617269 ns`
  - `50%`: `0.580455 ns`
  - `75%`: `0.590437 ns`
- fall:
  - `25%`: `0.666276 ns`
  - `50%`: `0.638753 ns`
  - `75%`: `0.734204 ns`

Observation:

- The rise delay changes by about `37 ps` across thresholds.
- The fall delay changes by about `95 ps` across thresholds.
- So this is **not** just a pure rigid shift, especially on the fall.

#### `io_buf` actual channel / tx pad

Delays:

- rise:
  - `25%`: `0.586618 ns`
  - `50%`: `0.650615 ns`
  - `75%`: `0.625038 ns`
- fall:
  - `25%`: `0.755106 ns`
  - `50%`: `0.622208 ns`
  - `75%`: `0.689887 ns`

#### `io_buf` actual channel / rx load

Delays:

- rise:
  - `25%`: `0.592822 ns`
  - `50%`: `0.619415 ns`
  - `75%`: `0.637624 ns`
- fall:
  - `25%`: `0.705615 ns`
  - `50%`: `0.656475 ns`
  - `75%`: `0.618787 ns`

Observation:

- The actual-channel case still shows significant threshold dependence.
- This reinforces that `io_buf` is not well described by one exact global shift.

#### `inv_chain` simple fixture

IBIS swing used:

- low = `0.000 V`
- high = `1.422230 V`

Delays:

- rise:
  - `25%`: `0.012768 ns`
  - `50%`: `0.014640 ns`
  - `75%`: `0.015485 ns`
- fall:
  - `25%`: `-0.003881 ns`
  - `50%`: `-0.003463 ns`
  - `75%`: `-0.003256 ns`

Observation:

- Rise delay changes by only about `2.7 ps`.
- Fall delay changes by only about `0.6 ps`.
- This is very close to a rigid shift.

#### `inv_chain` 2 pF capacitive load

Delays:

- rise:
  - `25%`: `0.013455 ns`
  - `50%`: `0.015125 ns`
  - `75%`: `0.015550 ns`
- fall:
  - `25%`: `0.005407 ns`
  - `50%`: `0.007177 ns`
  - `75%`: `0.008139 ns`

Observation:

- Again, only a few picoseconds of threshold dependence.
- The load change also only shifts the answer by a few picoseconds.

### Multi-Transition Constancy

#### `io_buf` existing multi-edge results at `50%`

From the earlier multi-edge study:

- simple fixture / pad:
  - mean = `0.632261 ns`
  - std = `0.033959 ns`
  - span = `0.101413 ns`

- actual channel / tx pad:
  - mean = `0.640085 ns`
  - std = `0.015225 ns`
  - span = `0.034408 ns`
  - rises cluster near `0.655 ns`
  - falls cluster near `0.625 ns`

- actual channel / rx load:
  - mean = `0.641621 ns`
  - std = `0.017267 ns`
  - span = `0.041342 ns`
  - rises cluster near `0.625 ns`
  - falls cluster near `0.659 ns`

Observation:

- `io_buf` is fairly consistent in average delay, but it has a real polarity split.
- The channel case is better described as **two nearly constant delays**, not one.

#### `inv_chain` 2 pF capacitive load multi-edge results at `50%`

Per-edge delays:

- rise 1: `0.015125 ns`
- fall 2: `0.007177 ns`
- rise 3: `0.002537 ns`
- fall 4: `0.006054 ns`
- rise 5: `0.006544 ns`
- fall 6: `0.005131 ns`

Summary:

- mean = `0.007095 ns`
- std = `0.003884 ns`
- span = `0.012589 ns`

Observation:

- The delay is tiny and reasonably stable across multiple transitions.
- Even the full spread is only about `12.6 ps`.

### What We Learn From The Two Cases

#### 1. The converter architecture itself is not imposing a big fixed lag

The same `InputDriven` / elapsed-time / T-line method gives:

- about `0.64 ns` skew in `io_buf`
- about `0.01 ns` skew in `inv_chain`

So the large `io_buf` offset is **not** coming from the mere existence of the T-line elapsed-time logic.

#### 2. `io_buf` behaves like a real correlation problem, not just an alignment problem

`io_buf` shows:

- large absolute delay,
- polarity dependence,
- threshold dependence,
- and bench dependence.

That means one can align it approximately with a shift, but the mismatch is not fully reducible to a rigid offset.

#### 3. `inv_chain` behaves much more like a clean near-constant shift

`inv_chain` shows:

- tiny absolute delay,
- very small threshold dependence,
- and only small load dependence.

So in that case, using a simple alignment offset is much more defensible.

#### 4. The likely difference is case-specific source/model correlation

A reasonable inference is:

- `inv_chain` is a much tighter source pair:
  - direct transistor chain
  - direct T2B-generated IBIS
  - zero package
  - simpler output behavior

- `io_buf` is a looser source pair:
  - more complex transistor behavior
  - richer feedthrough / shape effects
  - separate refspice/ngspice adaptation
  - and a known timing skew relative to the IBIS waveform timing

So the dominant lesson is that **delay is case-dependent**, not converter-intrinsic.

### Practical Takeaway

- For `io_buf`:
  - a single global offset around `0.64 ns` is only a first-order plotting aid
  - polarity-specific offsets are better
  - even then, some residual shape mismatch remains

- For `inv_chain`:
  - a single small offset on the order of `5 to 15 ps` is a reasonable alignment tool
  - the remaining mismatch is small enough that the comparison is much cleaner
