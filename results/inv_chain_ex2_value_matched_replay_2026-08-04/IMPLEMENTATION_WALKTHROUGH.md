# Value-Matched Replay V2: Exact Implementation

## First Correction: The Matching Variable

The implemented algorithm does **not** map pad voltage onto the opposite transition. It samples the currently active coefficient pair `Ku/Kd`. Pad voltage is load- and channel-dependent, while the coefficient tables belong to the driver model.

At a fall-after-rise reversal, the algorithm maps `KUSAMP` and `KDSAMP` independently onto the falling tables. At a rise-after-fall reversal, it maps them onto the rising tables.

The intended inverse operation is:

```text
t_Ku = argmin_t |Ku_opposite(t) - Ku_sample|
t_Kd = argmin_t |Kd_opposite(t) - Kd_sample|
t_shared = 0.5 * (t_Ku + t_Kd)
table_argument(t) = t_start_latched + elapsed_since_replay_activation
```

The split policy uses `t_Ku` for Ku and `t_Kd` for Kd instead of `t_shared`.

## Offline Generation

1. pybis2spice solves the complete rising and falling arrays `kr=[time,Ku,Kd]` and `kf=[time,Ku,Kd]` from the two IBIS fixture waveforms.
2. `inverse_time_lookup_table()` builds numerically legal inverse PWL tables `coefficient -> table time` for all four coefficient/direction combinations. It sorts by coefficient value, collapses duplicate values to their earliest time, and interpolates 81 points. This removes chronology: a non-monotonic table can have several physically different times for one coefficient value.
3. `create_ngspice_value_matched_replay_v2_input_control_netlist()` writes those forward and inverse PWL tables into the generated ngspice subcircuit.

## Runtime Sequence

1. `RISEEDGE/FALLEDGE` detect a digital input reversal.
2. `KUPRE/KDPRE` read the previous transition table before the replay direction changes.
3. `VMSAMPLE` briefly enables capacitor-backed latches `KUSAMP/KDSAMP`.
4. `TR_KU/TR_KD/TF_KU/TF_KD` inverse-map the samples to candidate starts on the opposite tables.
5. Policy chooses the start: balanced averages the two inferred times; Ku-only or Kd-only uses one; split keeps separate Ku and Kd starts.
6. `VMSTART_LATCH`, `KUSTART_LATCH`, and `KDSTART_LATCH` hold those starts. `VMT0` stores the replay activation time.
7. `VMELAPSED = max(0, current_time - VMT0 - edge_delay)` creates a fresh timer. V2 never reuses the legacy elapsed timer `HNX` as V1 did.
8. `VMARG`, or separate `KUARG/KDARG`, advances through the selected opposite table.
9. `KUMATCH/KDMATCH` become the live replay coefficients until the table ends, then control returns to legacy replay.
10. Final `Ku/Kd` are direct behavioral-voltage outputs of `KUTARGET/KDTARGET`; the sample and start nodes are capacitor-backed, but final V2 coefficients are not separately RC-smoothed.

## Core Generated SPICE

```spice
BKUSAMPLE KUSAMP 0 I = -{sample_c}*V(VMSAMPLE)*(V(KUPRE)-V(KUSAMP))/sample_tau
BKDSAMPLE KDSAMP 0 I = -{sample_c}*V(VMSAMPLE)*(V(KDPRE)-V(KDSAMP))/sample_tau
B32 TF_KU 0 V = pwl(V(KUSAMP), ... inverse Ku_fall ...)
B33 TF_KD 0 V = pwl(V(KDSAMP), ... inverse Kd_fall ...)
B35 TF_START 0 V = 0.5*(V(TF_KU)+V(TF_KD))
B37 VMELAPSED 0 V = (V(HVMATCH)>0.05) ? max(0,time*1e9-V(VMT0)-0.01) : 0
B37A VMARG 0 V = V(VMSTART_LATCH)+V(VMELAPSED)
B44 KUMATCH 0 V = (V(NINX)>0.5) ? V(KURM) : V(KUFM)
B45 KDMATCH 0 V = (V(NINX)>0.5) ? V(KDRM) : V(KDFM)
```

## Detector And Policies

- Fall-after-rise currently activates when a falling edge arrives while the legacy elapsed coordinate `HNX` is below the global 4 ns interruption window. It does not prove the physical coefficient state is unsettled.
- Rise-after-fall additionally requires `Ku > 0.05` or `Kd < 0.95`. This asymmetry is why many short-low cases do not activate replay.
- Balanced uses one shared start: `(t_from_Ku + t_from_Kd)/2`.
- Ku-only and Kd-only force both coefficients to use one coefficient's inferred start.
- Split lets Ku and Kd use separate table arguments. It diagnoses the shared-coordinate assumption, but it does not restore missing delayed-event history.

## Known Limits Exposed By This Study

1. A coefficient value alone is not a complete state when a delayed response is pending. `inv_chain` can still have `Ku ~= 0, Kd ~= 1` at reversal while the already-launched rising response appears later.
2. Inverting a non-monotonic coefficient table is multi-valued. Sorting by coefficient makes a legal ngspice PWL source, but cannot determine which occurrence is physically correct.
3. Ku-derived and Kd-derived opposite-table times can disagree. Separate starts avoid averaging, but do not make the pair a self-consistent driver state.
4. The current 4 ns command-age detector can activate after a fast buffer is effectively settled.
5. Pad-voltage matching was deliberately not implemented because pad voltage changes with load, clamps, package, and channel; it would not define a reusable driver-internal replay state.

The exact generated subcircuits are under `generated_models/<device>/<profile>/<policy>/`. Every simulation deck and raw file is retained under `runs/`.

Representative files to read end-to-end:

- `generated_models/inv_chain/fast_5ps/v2_balanced/driver2_OutputInput_Typical.sub`
- `runs/inv_chain/fast_5ps/short_pulse_50ps_high/v2_balanced/run.sp`
- `generated_models/ex2/slow_1ns/v2_balanced/driver_OutputInput_Typical.sub`
- `runs/ex2/slow_1ns/short_pulse_1ns_high/v2_balanced/run.sp`

Authoritative generator: `tools/pybis2spice/pybis2spice/subcircuit.py`.
Relevant functions: `inverse_time_lookup_table`, `create_inverse_time_lookup_source`, and `create_ngspice_value_matched_replay_v2_input_control_netlist`.
