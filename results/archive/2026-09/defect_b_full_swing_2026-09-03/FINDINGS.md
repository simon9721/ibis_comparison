# Defect B is stress-specific: the command layer is fine on a clean edge

Defect B is the gate-state model's falling 50% crossing running **69–99 ps late**
against the HSPICE transistor on io_buf's five stress targets (truncated pulses at
90/80/70/60/50% width), where native IBIS on the same cases is **5–26 ps early**.
Nothing had been tried on it.

The golden-waveform test ruled out the shared reconstruction layer (io_buf replays
its own full-swing V-T tables to within 8 ps). That left three candidates: the
gate-state command layer, the stress condition itself, or the bench. This splits
them with one measurement — run io_buf **full swing**, no truncation, and see
whether the lateness is still there.

## The measurement

io_buf, full swing, 50 Ω + 2 pF. Transistor swings −0.013 to 1.588 V; 50% = 0.788 V,
falling crossing at 15.3070 ns.

| build | rise vs transistor | **fall vs transistor** |
|---|---:|---:|
| native IBIS | +14.3 ps | **+34.6 ps** |
| pybis InputDriven | +25.2 ps | **+38.4 ps** |
| pybis gate-state (campaign opts) | +27.7 ps | **+43.6 ps** |
| pybis gate-state (relaxed opts) | +27.0 ps | **+43.4 ps** |
| pybis gate-state (loose opts) | +29.7 ps | **+43.5 ps** |

The gate-state number is stable at **+43.5 ps** across three different solver
settings, so it is the model's, not the solver's.

## The answer

**On a clean full-swing edge the gate-state build is only ~9 ps worse than native**
(43.5 vs 34.6). Under stress that gap explodes to ~75–125 ps (69…99 against
−5…−26).

| condition | gate-state vs transistor | native vs transistor | gap |
|---|---:|---:|---:|
| full swing | +43.5 ps | +34.6 ps | **~9 ps** |
| stress (truncated) | +69 … +99 ps | −5 … −26 ps | **~75–125 ps** |

So defect B is **not** the command layer's fitted delays. Those are nanosecond
scale (io_buf `pd_on` 1.83 ns, `pd_off` 0.85 ns) and a systematic error in them
would show on every edge, full swing included. It does not — full swing is nearly
as good as native.

**Defect B is the command layer's response to a truncated pulse.** The layer
behaves on a clean edge and only diverges once the pulse is cut short.

That points at the same root cause family the *offset* defect was traced to:
`GUPCMD` is an open-loop integrator with no DC path, charged by a fixed packet per
input edge, so a truncated pulse leaves net charge behind. The offset is that
residue showing up in the settled level; the timing shift is plausibly the same
residue delaying the next transition. Worth testing directly — the two defects
were treated as unrelated, and this says they may not be.

## A second observation: native moves too

Native IBIS is **+34.6 ps late** on full swing but was reported **5–26 ps early**
on the stress cases — a swing of 40–60 ps for the *reference*, same model, same
simulator. Part of defect B's headline magnitude is therefore native getting
better under stress while we get worse.

That matters for how the number is quoted. Measured against the transistor, defect
B is 69–99 ps. Measured as model-versus-native — the comparison that isolates our
machinery — it is ~75–125 ps under stress against ~9 ps on full swing. The second
framing is the one that localises the defect.

## Incidental: the gate-state build has a convergence floor

The first attempt used `reltol=1e-5, abstol=1e-10, vntol=1e-7` with a 0.5 ps step —
the settings that were right for the InputDriven convergence work — and ngspice
aborted at t ≈ 15.29 ns, exactly the falling edge, emitting one timepoint. Three
looser settings (including the campaign's own) all run to completion and agree to
0.2 ps.

So the gate-state build does not tolerate the tight tolerances the plain build
does. Anything comparing the two must not assume one solver setting suits both,
or the tighter one will silently look like a model failure.

## Files

- `defect_b_full_swing.png` — rising and falling edges, all builds
- `transistor/`, `native/`, `pybis_plain/`, `pybis_gate_state*/` — the runs
- `scripts/defect_b_full_swing_probe.py`
