# Ku/Kd Excursion and Pad-Matched Replay Study

## Purpose

This study answers two separate questions:

1. Why do extracted or generated `Ku/Kd` coefficients sometimes leave the nominal `[0,1]` interval?
2. Can pad voltage sampled at an interrupted edge provide a useful starting point for replaying the opposite `Ku(t)/Kd(t)` table pair?

The three buffers are `io_buf`, `inv_chain`, and `ex2`. Each is tested with the repo's slow and fast IBIS variants. HSPICE native IBIS is the coefficient reference; transistor HSPICE is pad-only because it has no IBIS `Ku/Kd` nodes.

## What Ku and Kd Mean

`Ku` and `Kd` are scalar multipliers on the static pullup and pulldown current tables. They are effective current-decomposition coefficients, not literal PMOS/NMOS gate voltages. A value outside `[0,1]` is therefore not automatically invalid.

At each waveform sample, pybis solves the two-fixture linear system

```text
[ Ipu_fixture_1  Ipd_fixture_1 ] [ Ku ]   [ Irequired_fixture_1 ]
[ Ipu_fixture_2  Ipd_fixture_2 ] [ Kd ] = [ Irequired_fixture_2 ]
```

The required-current vector includes fixture current, clamps, `C_comp*dV/dt`, and fixture-capacitance current. Restricting both coefficients to `[0,1]` would only allow a convex combination of the two static output networks. A sharp waveform can demand current outside that restricted set.

## Excursion Findings

### Native extraction

- The 2x2 matrices are not close to singular. Across the audit, p95 condition numbers are approximately `2.3` to `5.4`.
- The largest offline excursion is fast-`io_buf` falling, where `Ku=2.193` at `6 ps`; matrix condition is only `2.919`.
- At that point, modeled capacitive current is `45.7 mA` versus `23.3 mA` fixture current. The dynamic right-hand side, especially `C_comp*dV/dt`, explains the coefficient demand better than matrix conditioning.
- `inv_chain` has tiny dynamic-current ratios and stays close to `[0,1]`. `ex2` is intermediate. Excursion severity is model- and direction-dependent.

### Generated-model artifact

The fast-`io_buf` hybrid has a different failure. During the 1 ns short-high reversal:

```text
time                         6.036863 ns
one-step hybrid Kd change   -0.968819
hybrid Kd                   -1.209604
native HSPICE Kd             0.483414
full gate-state Kd          -0.210368
directional base            -0.423443
rate residual               -0.786161
GDN                          0.369654
GDN target                   0.438663
```

The base map and signed rate residual are keyed by different progress variables during reversal and are then added. The hybrid handoff exposes their inconsistent sum as a discontinuity. This is an algorithm-created excursion, not native coefficient behavior.

### Validation rule

Do not globally clip Ku/Kd to `[0,1]`. Instead:

1. Compare the candidate range against the native-IBIS event envelope.
2. Measure one-step coefficient discontinuity around the reverse edge.
3. Reject extra excursion caused by inconsistent state terms or handoff.
4. Keep native-like overshoot/undershoot if it is continuous and required by the extracted current balance.

## Pad-Matched Replay Hypothesis

The tested hypothesis is that the pad voltage at reversal may identify where to begin the opposite coefficient-table pair.

### Offline preparation

For each buffer/profile, legacy pybis is simulated with:

```text
input edge     50 ps
load           50 ohm || 2 pF
supply         buffer-specific nominal supply
rising event   5 ns
falling event  25 ns
```

The resulting rising and falling pad trajectories are stored in `pad_replay_reference.json`. This is calibration from legacy pybis only; HSPICE is not used to choose the map.

For each trajectory, all segment crossings of a candidate pad voltage are found. This matters because ringing makes the inverse relation multivalued. The generator records earliest and latest crossing times rather than assuming the trajectory is monotonic.

The voltage-plus-slew diagnostic forms an offline score

```text
score = normalized_pad_voltage
      + 0.25 * normalized_absolute_pad_slew
```

It still uses one scalar and is not assumed to be a unique physical state.

### Runtime operation

At a detected reverse edge:

1. Sample `V(OUT)` once. The slew variant also samples the magnitude of the pre-edge pad slope.
2. Invert the opposite-transition calibration path to obtain one replay start time.
3. Latch that start time.
4. Start a fresh elapsed timer.
5. Evaluate both opposite `Ku/Kd` tables from the shared argument:

```text
PADARG = PADSTART_LATCH + PMELAPSED
```

There is no continuous pad feedback. HSPICE data is not used at runtime or for fitting.

## V1 and V2

### V1

V1 successfully demonstrated the mapping experiment but continuously passed final `Ku/Kd` through a 5 ps capacitor-backed filter. That filter was active even when pad replay was inactive, so some normal controls changed. V1 is retained as evidence and is not a default candidate.

### V2

V2 separates ordinary legacy output from the replay transaction:

- no reverse event: final `Ku/Kd` are direct `KULEG/KDLEG`
- sample/latch window: hold the pre-reversal coefficient values
- replay active: blend continuously into the pad-matched opposite-table pair
- replay complete: blend back to settled legacy coefficients

The voltage-only V2 has no pad-history RC load. The voltage-plus-slew mode retains an explicit `1 kohm / 10 fF` observation RC and is diagnostic because that network can perturb very fast cases.

## V1 Experimental Results

### Nominal 50 ohm / 2 pF matrix

- There are `96` short-pulse pad-flow rows.
- `14` rows improve pad, Ku, and Kd numerically; `11` improve all three by at least 5%.
- Every all-three improvement is short-low. No short-high case passes all three checks.
- Voltage plus absolute slew does not consistently outperform voltage alone.
- `16` rows are mapping-ambiguous.

### Load portability

The same map calibrated at `50 ohm || 2 pF` was tested at eight other combinations of 25/50/100 ohm and 0/2/10 pF.

- Short-low 500 ps: `46/96` rows improve all three relative metrics.
- Short-high 500 ps: `0/96` rows improve all three.
- Improvements cluster in `ex2` and fast `io_buf`; `inv_chain` consistently worsens.
- Even some relative improvements retain large absolute errors, so they are evidence of directionality, not model readiness.

## V2 Experimental Results

V2 was run over the same nominal 216-row matrix. All 108 HSPICE reference rows came from existing `.tr0` files or the shared cache; the V2 campaign did not rerun the golden reference.

### Normal controls

- No V2 pad flow has a numeric failure on the six long controls.
- The median worst pad/Ku/Kd error ratio versus legacy is `1.019`; the worst is `1.143`.
- Slow `io_buf` and both `inv_chain` profiles remain very close to legacy. Fast `io_buf` remains timestep-sensitive because its extracted coefficient table begins with a large dynamic spike.
- The V2 voltage-only path removes the V1 continuous coefficient filter and has no pad-history RC. The slew-aware path keeps the explicit 10 fF observation network and remains diagnostic.

### Short pulses

- `12/96` pad-flow rows improve pad, Ku, and Kd numerically: 3 short-high and 9 short-low.
- Only `6/96` improve all three by at least 5%, and all six are short-low.
- No short-high row is a material all-three improvement.
- The event classifier finds 34 ambiguous mappings, 24 coefficient artifacts, 22 no-clear-improvement rows, and 4 pad-only false passes.
- V2 therefore fixes the V1 implementation regression but does not rescue the underlying pad-state hypothesis.

## Current Interpretation

Pad voltage is not a general internal-state coordinate. It depends on load, static pullup/pulldown behavior, clamps, package parasitics, and both coefficient histories. The same voltage can occur at multiple times and with different internal states. Absolute slew helps distinguish some crossings but does not make the mapping unique.

The experiment is nevertheless valuable:

- It establishes a clean, testable baseline for pad-based retiming.
- It finds real short-low improvements in selected buffers.
- It clearly fails the mirrored short-high requirement.
- It demonstrates why pad agreement alone cannot prove coefficient correctness.

## Evidence Locations

- Ku/Kd decomposition: `results/three_buffer_kukd_excursion_decomposition_2026-08-04`
- Solve conditioning: `results/three_buffer_kukd_excursion_decomposition_2026-08-04/solve_conditioning`
- V1 nominal campaign: `results/three_buffer_pad_matched_replay_2026-08-04`
- V1 event evidence: `results/three_buffer_pad_matched_replay_2026-08-04/event_evidence`
- V1 load portability: `results/three_buffer_pad_matched_replay_load_portability_2026-08-04`
- V2 campaign: `results/three_buffer_pad_matched_replay_v2_2026-08-04`

## Implementation Ownership

- Model generation: `tools/pybis2spice/pybis2spice/subcircuit.py`
- Conversion CLI plumbing: `scripts/convert_ibis_to_pybis.py`
- Campaign runner: `scripts/run_three_buffer_pad_matched_replay.py`
- Event analysis: `scripts/analyze_three_buffer_pad_matched_replay.py`
- Load analysis: `scripts/analyze_pad_matched_load_portability.py`
- Ku/Kd decomposition: `scripts/analyze_three_buffer_kukd_excursion_decomposition.py`
- Solve audit: `scripts/analyze_kukd_solve_conditioning.py`
