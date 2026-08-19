# Gate-State Capacitor and Ku/Kd Excursion Findings

This note indexes the cached evidence for two earlier questions:

1. What do the actual capacitor-backed `GUP/GDN` state waveforms look like?
2. Why can `Ku/Kd` overshoot above 1 or undershoot below 0 near transition boundaries?

No new simulation is required for this evidence.

## 1. Direct Capacitor-State Waveforms

The generated ngspice gate-state model uses `GUP` and `GDN` as capacitor voltages. They are normalized hidden progress states:

- `GUP = 0`: pullup gate-drive state is at its low endpoint.
- `GUP = 1`: pullup gate-drive state is at its high endpoint.
- `GDN = 0`: pulldown gate-drive state is at its low endpoint.
- `GDN = 1`: pulldown gate-drive state is at its high endpoint.

The state equations are implemented by a behavioral current source and a capacitor:

```spice
BGUP GUP 0 I=-Cgate*(V(GUPTARGET)-V(GUP))/tau_selected
CGUP GUP 0 Cgate ic=0

BGDN GDN 0 I=-Cgate*(V(GDNTARGET)-V(GDN))/tau_selected
CGDN GDN 0 Cgate ic=1
```

Because `I = C*dV/dt`, these elements implement:

```text
dGUP/dt = (GUPTARGET - GUP) / tau_selected
dGDN/dt = (GDNTARGET - GDN) / tau_selected
```

At an interrupted transition, the targets can reverse quickly, but the capacitor voltages do not reset. `GUP/GDN` continue from their current values and change direction continuously.

### Figures

- [io_buf GUP/GDN waveforms](../results/three_buffer_gup_gdn_waveforms_2026-08-04/plots/io_buf_gup_gdn_waveforms.png)
- [inv_chain GUP/GDN waveforms](../results/three_buffer_gup_gdn_waveforms_2026-08-04/plots/inv_chain_gup_gdn_waveforms.png)
- [ex2 GUP/GDN waveforms](../results/three_buffer_gup_gdn_waveforms_2026-08-04/plots/ex2_gup_gdn_waveforms.png)
- [Runtime reversal example](../results/ibis_kukd_handwritten_notes_deck/generated_assets/04_real_gup_gdn_reversal.png)

The direct three-buffer figures contain three columns:

- Complete 10 ns high transition.
- Interrupted 1 ns high transition.
- Interrupted 1 ns low transition.

Blue is the capacitor-backed state, gray is its command target, red is the mapped coefficient, and black is HSPICE native-IBIS `Ku/Kd`.

The numerical data behind every panel are under:

`results/three_buffer_gup_gdn_waveforms_2026-08-04/source_data/`

## 2. GUP/GDN and Ku/Kd Are Different Quantities

`GUP/GDN` are bounded memory states. `Ku/Kd` are effective current multipliers applied to the static IBIS pullup and pulldown I/V tables:

```text
I_output = Ku * I_pullup(V) + Kd * I_pulldown(V) + clamps + capacitive current
```

The directional maps produce the final coefficients:

```text
Ku = f_pullup,direction(GUP)
Kd = f_pulldown,direction(GDN) + residual
```

Therefore a bounded state does not imply a bounded coefficient. In the cached runs, every `GUP/GDN` trace stayed inside `[0,1]`, while both native and generated `Ku/Kd` sometimes left that interval.

### Measured Long-Transition Ranges

| Buffer | Flow | Ku range | Kd range | GUP range | GDN range |
|---|---|---|---|---|---|
| io_buf | HSPICE native IBIS | -0.687 to 2.395 | -0.609 to 1.179 | n/a | n/a |
| io_buf | gate-state model | -0.118 to 1.668 | -0.376 to 1.145 | 0.000 to 0.997 | 0.00005 to 1.000 |
| inv_chain | HSPICE native IBIS | -0.075 to 1.010 | -0.072 to 1.028 | n/a | n/a |
| inv_chain | gate-state model | -0.027 to 1.001 | -0.053 to 1.014 | 0.000 to 0.968 | 0.029 to 1.000 |
| ex2 | HSPICE native IBIS | -0.375 to 1.256 | -0.264 to 1.111 | n/a | n/a |
| ex2 | gate-state model | -0.379 to 1.230 | -0.234 to 1.081 | 0.000 to 1.000 | 0.000 to 1.000 |

The overview figure is:

- [Coefficient excursions versus bounded hidden states](../results/three_buffer_kukd_excursion_analysis_2026-08-04/plots/three_buffer_kukd_excursions_vs_gate_states.png)

The corresponding numbers are:

- [coefficient_excursion_summary.csv](../results/three_buffer_kukd_excursion_analysis_2026-08-04/coefficient_excursion_summary.csv)

## 3. Why Native Ku/Kd Leave 0 to 1

The original pybis extraction uses two IBIS waveform fixtures and solves a 2-by-2 current-balance system at each sample:

```text
[Ipu_fixture1  Ipd_fixture1] [Ku] = [Irequired_fixture1]
[Ipu_fixture2  Ipd_fixture2] [Kd]   [Irequired_fixture2]
```

The required-current vector includes fixture current, clamp current, `C_comp*dV/dt`, and fixture-capacitance terms. During a very sharp edge, the capacitive-current term can be larger than the fixture current. A coefficient outside `[0,1]` may then be required because no convex combination of the two static I/V currents can balance the dynamic waveform current.

For the worst fast `io_buf` falling-table sample:

- Time into table: about 6 ps.
- Extracted `Ku`: 2.193.
- 2-by-2 matrix condition number: 2.919.
- Modeled capacitive current: 45.7 mA.
- Fixture current: 23.3 mA.
- Capacitive/fixture current ratio: 1.96.

The solve was not close to singular. The excursion was driven primarily by the dynamic right-hand side, especially `C_comp*dV/dt`.

Evidence:

- [Solve-conditioning report](../results/three_buffer_kukd_excursion_decomposition_2026-08-04/solve_conditioning/README.md)
- [Conditioning versus excursion figure](../results/three_buffer_kukd_excursion_decomposition_2026-08-04/solve_conditioning/solve_conditioning_vs_excursion.png)

## 4. Fast and Slow io_buf Behave Differently

The large `io_buf` excursions are associated with the fast-edge IBIS data, not with every version of that buffer.

| io_buf profile | Flow | Ku range | Kd range |
|---|---|---|---|
| fast 5 ps | native IBIS | -0.687 to 2.395 | -0.609 to 1.179 |
| fast 5 ps | gate-state | -0.118 to 1.668 | -0.376 to 1.145 |
| fast 5 ps | hybrid | -0.089 to 1.988 | -0.399 to 1.171 |
| slow 1 ns | native IBIS | -0.023 to 1.013 | -0.072 to 1.005 |
| slow 1 ns | legacy pybis | -0.022 to 1.012 | -0.072 to 1.006 |
| slow 1 ns | directional residual | -0.006 to 0.996 | -0.072 to 1.005 |

This is why clipping every coefficient to `[0,1]` is not correct. It would erase excursions already present in the native HSPICE IBIS behavior, especially the negative Kd feature used by the reconstruction gate.

## 5. Legitimate Excursion Versus Generated Artifact

Two separate effects must not be confused:

1. Native/extracted excursion caused by dynamic current balance.
2. An additional discontinuity created by the generated algorithm.

The clearest generated artifact occurred in the `io_buf`, 1 ns short-high hybrid case:

- Largest one-step Kd change: `-0.969` at `6.0369 ns`.
- Hybrid Kd immediately reached about `-1.210`.
- HSPICE native-IBIS Kd at that instant: `0.483`.
- Full gate-state Kd at that instant: `-0.210`.
- Directional base-map term: `-0.423`.
- Signed rate-residual term: `-0.786`.

The base map and residual were keyed by inconsistent progress information during retrigger, and the hybrid handoff exposed their sum as a discontinuity.

Evidence:

- [Hybrid Kd excursion decomposition](../results/three_buffer_kukd_excursion_decomposition_2026-08-04/plots/02_io_buf_hybrid_kd_excursion_decomposition.png)
- [Hybrid event samples](../results/three_buffer_kukd_excursion_decomposition_2026-08-04/io_buf_hybrid_event_samples.csv)
- [Hybrid excursion summary](../results/three_buffer_kukd_excursion_decomposition_2026-08-04/io_buf_hybrid_excursion_summary.csv)

## 6. Practical Rule

Do not classify a model as bad merely because `Ku/Kd` leave `[0,1]`.

Use these checks instead:

1. Confirm `GUP/GDN` remain finite, bounded, and continuous.
2. Compare generated `Ku/Kd` against the native-IBIS coefficient envelope for the same model and stimulus.
3. Check coefficient jump magnitude at map-direction or hybrid handoff events.
4. Decompose any large generated excursion into base-map, residual, rate, and blend contributions.
5. Reject excursions that are substantially outside the native envelope or are caused by a generated discontinuity.

This preserves legitimate IBIS coefficient behavior while still catching the hybrid `Kd=-1.21` type of algorithm artifact.
