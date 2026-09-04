# Never grade against `hspice_ngspice.mod`

*2026-09-04*

## The rule

| Simulator | Card | Why |
|---|---|---|
| **HSPICE** — any transistor reference | `buffers/models/hspice.mod` | the stock TSMC 180 nm BSIM3v3 card the IBIS models were characterised from |
| **ngspice** — pybis subcircuits only | `buffers/models/hspice_ngspice.mod` | RDSW/PRWG/PRWB zeroed so ngspice does not stall |

`hspice_ngspice.mod` exists for one reason: with `RDSW > 0`, ngspice creates
explicit source/drain internal nodes, and on a small device (`W = 0.3 µm`,
`RDSW = 150` → `R_source ≈ 500 Ω`, `C = 0.215 fF`, `τ ≈ 54 fs`) the timestep
collapses and the run stalls. Zeroing it is a solver workaround, not a model.

```
hspice.mod          RDSW = 150          PRWG = 0.5   PRWB = -0.2
hspice_ngspice.mod  RDSW = 0            PRWG = 0     PRWB = 0
```

Zeroing the source/drain resistance makes the output stage **~12% stronger** than
the I-V tables the IBIS model was built from. A transistor reference on that card
is not the silicon the model is meant to reproduce.

## What it looks like when you get it wrong

Measured on io_buf, first rising edge, absolute crossing times — the edge before
any reversal, where all three should agree:

```
                                 0.10 V   0.20 V   0.30 V
native-anchored sweep transistor 6.1322   6.2665   6.3414   ← ~110 ps early
stress matrix transistor         6.2403   6.3987   6.4874
full-swing transistor            6.2260   6.3828   6.4684
native IBIS (identical in all)   6.2696   6.4167   6.5007
```

Native IBIS is the same to four decimal places in every dataset. Only the
transistor moves, and only in the tree whose decks include the ngspice card. It
reads as the *model* being ~150 ps late; it is the reference being ~110 ps early.

The symptom already had a second sighting: the same card produces a settled Kd of
1.118 on io_buf, which was read as a defect in the IBIS file.

## How it is enforced

`spicelab.hspice()` raises if the deck it is about to run includes
`hspice_ngspice.mod`. Documentation did not prevent this — `hspice.mod`'s own
header already carried the warning — so the check is in the code path every
HSPICE run goes through. `allow_ngspice_card=True` overrides it, and exists only
for deliberately reproducing an old result.

Audit the tree at any time:

```
py -3.14 scripts/audit_model_cards.py
```

## Results already affected

**536 HSPICE runs across 17 result trees** were built with the wrong card before
the check existed. The ones that matter most:

| tree | runs | why it matters |
|---|---:|---|
| `three_buffer_loaded_swing_stress_sweep_2026-08-14` | 14 | defines the study's stress axis |
| `three_buffer_native_anchored_stress_sweep_2026-08-19` | 11 | source of the 0904 deck's recap figure |
| `silicon_kukd_recovery_2026-08-19` | 12 | the silicon Ku/Kd target |
| `_baseline_edgecmd` | 10 | per-case waveforms used in several figures |
| `three_buffer_realistic_pulse_2026-07-30` | 65 | |
| `_golden_hspice_cache` | 190 | cached references |

**Known clean** (they include `hspice.mod`): `stress_method_matrix_2026-08-20`,
`defect_b_full_swing_2026-09-03`, `variant_stress_cases_2026-09-04`,
`variant_stress_depth_2026-09-03`.

Any timing number taken from an affected tree is measured against a transistor
~110 ps fast on io_buf. Amplitude comparisons are less affected but not immune —
a 12% stronger device reaches a higher peak. Re-run before quoting, or take the
number from a clean tree.
