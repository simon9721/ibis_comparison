# How native IBIS handles truncated pulses — and it is device-dependent

## The question

On io_buf, native IBIS under-swings the transistor under stress and the error
tracks how complete the transition was (r = +0.94). That was one device and one
direction. This tests whether it is a law by re-running the analysis on every
device and direction in the width-sweep family.

## It is not a law. Native behaves qualitatively differently per device.

Peak excursion, transistor vs native vs pybis, short_high:

**inv_chain** — native barely responds to truncation at all

| width | transistor | native | pybis | native err | pybis err |
|---|---:|---:|---:|---:|---:|
| 104 ps | 0.682 | 1.297 | 0.915 | **+615 mV** | +233 mV |
| 106 ps | 0.837 | 1.298 | 0.937 | **+461 mV** | +99 mV |
| 111 ps | 0.989 | 1.311 | 0.980 | **+322 mV** | −10 mV |
| 119 ps | 1.073 | 1.289 | 1.026 | **+216 mV** | −48 mV |
| 135 ps | 1.195 | 1.290 | 1.111 | **+96 mV** | −84 mV |

Native's excursion is essentially **constant at ~1.29 V** while the transistor's
moves 0.68 -> 1.20. It delivers a near-complete transition no matter how short the
pulse, over-swinging by up to 615 mV.

**ex2** — same shape, milder: native 1.316 -> 1.423 while the transistor moves
0.770 -> 1.404. Over-swings by up to 545 mV.

**io_buf** — the opposite. Native *does* track the truncation (0.453 -> 1.160
against the transistor's 0.569 -> 1.220) but sits consistently ~10% low,
under-swinging by 60-124 mV.

## Correction to an earlier claim

I previously wrote that native IBIS "systematically under-swings under stress".
**That is true only of io_buf.** On ex2 and inv_chain native *over*-swings, and
by far more (up to +615 mV against io_buf's −124 mV). Generalising from one
device was wrong, and testing out of sample is what caught it.

The per-device correlations are still strong (|r| = 0.94 to 0.999), so native is
predictable *within* a device. But the slope reverses sign between devices, so
there is no single cross-device law and no universal correction factor.

## What this suggests about the mechanism

Native replays recorded V-T tables describing a complete transition. On io_buf
the stressed pulses are long (1505-2354 ps) and native has time to follow the
truncation. On inv_chain they are ~100 ps — barely longer than the buffer's own
edge — and native essentially cannot express a transition that short, so it
plays out something close to the full recorded waveform regardless.

That is consistent with the architecture but is **not yet demonstrated**: it
predicts the over-swing should scale with (pulse width / edge width), which has
not been tested. Recorded as a hypothesis, not a finding.

## pybis versus native on the same cases

| device | pybis closer on |
|---|---|
| inv_chain short_high | **5 / 5** |
| ex2 short_high | **4 / 5** |
| io_buf short_high | **9 / 9** |

**18 of 19.** On truncated pulses our model reproduces the transistor's amplitude
better than native IBIS does, on all three silicons — and on inv_chain the margin
is large (native +615 mV against pybis +233 mV at the shortest pulse).

This is the reverse of the full-swing picture, where native is the better model
and we chase it. It is worth saying plainly: **native IBIS is not a reliable
yardstick under stress.** Comparing our stressed timing against native's is
comparing against a reference that is itself device-dependently wrong, which is
part of why "native is early, we are late" was hard to interpret.

## Caveats

- short_low families were excluded: the excursion measure used here does not
  isolate a downward dip from a high plateau, so those numbers were not
  trustworthy. Needs a direction-aware measure.
- 5 points each for ex2 and inv_chain, 9 for io_buf.
- Width-sweep family only. The depth-target family, on which defect B was quoted,
  has not been measured this way.

## Files

- `native_stress_law.png`
- `scripts/native_stress_law.py`
