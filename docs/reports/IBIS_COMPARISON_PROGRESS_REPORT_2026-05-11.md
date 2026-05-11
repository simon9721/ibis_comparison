# IBIS Comparison Progress Report

Date: 2026-05-11

Workspace: `C:\Users\simom\Desktop\IBIS_Comparison`

## 1. Executive Summary

The project has made substantial progress. The open-source flow is now working
for the main scoped benchmark: PRBS7 stimulus, 5 ns UI, 200 ps input edges, and
the new 50 ohm 10-section RLGC channel.

The clearest current conclusion is:

- `ngspice + io_buf.sp` works for the transistor-level reference PRBS/RLGC run.
- `Xyce + io_buf.sp` also works and closely matches ngspice for the same
  transistor-level reference run.
- `ngspice + pybis2spice` works for the accepted PRBS/RLGC benchmark after
  known model/setup fixes.
- `Xyce + pybis2spice` works for the accepted PRBS/RLGC benchmark only with a
  Xyce-specific continuation model and timestep controls. The direct/unrelaxed
  pybis model is still not robust for repeated switching.
- HSPICE native IBIS `.tr0` files exist and are useful for trend comparison,
  but there is no current matched HSPICE run for `io_buf.sp` transistor-level
  SPICE subcircuit.
- The eye tool has been corrected back to physical clock/UI-grid folding. It
  should not compensate waveform distortion to make a visually prettier eye.

The "weird eye" behavior is not just an eye-tool artifact. It is present in the
direct transient results, including the `io_buf.sp` transistor-level cases. The
tool can make that distortion more or less visually obvious depending on how the
folding phase is chosen, but the underlying rise/fall timing asymmetry is in the
waveform.

## 2. Original Plan Position

The original plan set up six experiments:

| Plan experiment | Target | Current status | Stability assessment |
|---|---|---|---|
| Exp 1 | ngspice + transistor-level `io_buf.sp` | Done | Stable for current PRBS7 + RLGC acceptance bench |
| Exp 2 | ngspice + pybis2spice | Done for accepted RLGC bench | Stable enough with known fixes/options; not universal |
| Exp 3 | ngspice + SPISim converted examples | Partial | Reference examples inspected/run; not a full apples-to-apples case |
| Exp 4 | HSPICE native IBIS | Deferred/formal matched run missing | Blocked by license/current matched run availability |
| Exp 5 | Xyce + transistor-level `io_buf.sp` | Done | Stable and fast |
| Exp 6 | Xyce + pybis2spice | Partial/practical workaround works | Direct model not robust; relaxed/ported model works for accepted RLGC PRBS |

So the open-source comparison is well advanced, but the full plan is not
finished. The remaining gaps are mostly HSPICE and formalizing the Xyce pybis
model status.

## 3. Current Accepted Benchmark

The current "accepted" benchmark is:

- Stimulus: PRBS7
- UI: 5 ns, or 200 Mbps
- Input transition: 200 ps
- Duration: 1000 ns
- Channel: new 50 ohm 10-section RLGC ladder
- Termination: 50 ohm to ground
- Stimulus source: voltage-source PWL, not behavioral-source PWL

The move to a voltage-source PWL is important. In ngspice, a V-source PWL puts
breakpoints into the timestep event queue. A behavioral `pwl()` expression hides
those breakpoints from the timestep controller and caused excessive tiny-step
work.

The new 50 ohm RLGC channel is also important. It is a damped lumped channel
made from ordinary R/L/C/G primitives, so it is portable across ngspice, Xyce,
and HSPICE. It is much less numerically harsh than the ideal lossless T-line
PRBS stress case.

## 4. Clean PRBS/RLGC Result

The clean ngspice/Xyce pybis rerun is stored in:

- `results/prbs_rlgc_clean_2026-05-10/`

Summary:

| Case | Completed 1000 ns | Samples | Runtime | V(n10b) min | V(n10b) max | Notes |
|---|---:|---:|---:|---:|---:|---|
| ngspice direct pybis | yes | 100884 | 6.619 s | -0.0082 V | 1.5405 V | Direct pybis model with ngspice-compatible setup |
| Xyce `edge15_flat4p2` | yes | 100001 | 4.866 s | -0.0070 V | 1.5411 V | Xyce-specific relaxed/tail-conditioned pybis model |
| Xyce vs ngspice | yes | 20001 comparison points | n/a | n/a | n/a | 26.64 mV RMSE, 50.38 mV max abs error |

Interpretation:

The accepted PRBS/RLGC benchmark now runs successfully in both ngspice and
Xyce. However, this does not mean both simulators are equally robust for every
possible pybis/load combination. It means we have a documented, repeatable
passing path for the benchmark that the current plan accepts.

## 5. Transistor-Level `io_buf.sp` Status

The direct transistor-level reference is important because `io_buf.ibs` was
generated from `io_buf.sp`. If the eye distortion is already present in the
`io_buf.sp` transient response, then the eye tool should show it rather than
hide it.

Current physical eye results for `io_buf.sp` are in:

- `results/io_buf_sp_physical_eye_2026-05-11/ngspice/`
- `results/io_buf_sp_physical_eye_2026-05-11/xyce/`

These were generated after removing the non-physical edge-aligned eye mode.
They use clock/UI-grid folding with:

- `n_ui = 2`
- `phase_ui = 0`
- no per-edge alignment
- no rise/fall phase compensation

Metrics at `V(n10b)`:

| Case | Samples | V min | V max | Rise 20-80 | Fall 20-80 | Eye height | Eye width |
|---|---:|---:|---:|---:|---:|---:|---:|
| ngspice + `io_buf.sp` | 100973 | -0.0210 V | 1.5166 V | 932.1 ps | 167.7 ps | 296.4 mV | 2617.5 ps |
| Xyce + `io_buf.sp` | 22275 | -0.0248 V | 1.5177 V | 928.1 ps | 168.1 ps | 305.4 mV | 2622.5 ps |

Interpretation:

The ngspice and Xyce transistor-level `io_buf.sp` results agree closely. Both
show a very asymmetric receiver waveform: the rising transition is much slower
than the falling transition. That asymmetry explains why a physical clock-folded
eye can look unusual.

This is currently the strongest evidence that the strange eye shape is not an
eye-tool-only problem and not only a pybis-converter artifact.

## 6. Rise/Fall Phase Distortion Finding

A separate comparison looked at the 50 percent crossing delay of rising and
falling edges. This was useful because the user noticed that the eye did not
look like a conventional symmetrical eye.

At `V(n10b)`:

| Case | Bench | Rise 50 delay | Fall 50 delay | Rise/fall split |
|---|---|---:|---:|---:|
| HSPICE native IBIS, experiments `.tr0` | PRBS11, old approx. 76 ohm channel, Rterm=85 | 3.094 ns | 1.774 ns | 1.320 ns |
| ngspice `io_buf.sp` | PRBS7, new 50 ohm channel, Rterm=50 | 2.281 ns | 0.954 ns | 1.327 ns |
| ngspice pybis clean | PRBS7, new 50 ohm channel, Rterm=50 | 2.938 ns | 1.571 ns | 1.367 ns |
| Xyce pybis clean | PRBS7, new 50 ohm channel, Rterm=50 | 2.932 ns | 1.568 ns | 1.364 ns |

Interpretation:

All the meaningful cases show roughly the same dominant duty-cycle distortion:
about 1.3 ns, or about 0.26 to 0.27 UI at 5 ns UI. The absolute delay and swing
differ because the benches are not all identical, but the timing distortion is
consistent.

The `hspice/native_ibis_exp1/tb_exp1.tr0` HSPICE native IBIS result was not used
as the main reference because that waveform rings badly, with approximately
-1.50 V to 3.84 V at `V(n10b)`. The cleaner HSPICE native IBIS `.tr0` is the
`experiments/tb_exp1.tr0` file.

## 7. HSPICE Status

What exists:

- `hspice/native_ibis_exp1/tb_exp1.tr0`
- `experiments/tb_exp1.tr0`

Both are HSPICE native IBIS style runs, not HSPICE transistor-level `io_buf.sp`
subcircuit runs.

There is a candidate HSPICE transistor-level deck:

- `experiments/tb_exp2.sp`

It wraps `io_buf.sp` as:

```spice
.subckt SPICE_BUF  in  oe  out  in_sense  vdd  vss
.include 'hspice.mod'
.include '../models/io_buf.sp'
.ends SPICE_BUF
```

But no corresponding HSPICE result exists:

- no `tb_exp2.tr0`
- no `tb_exp2.lis`
- no `tb_exp2.st0`

Likely setup issue before future HSPICE run:

- if run from `experiments/`, `.include 'io_buf.sp'` probably needs to become
  `.include '../models/io_buf.sp'`
- if run from repo root, `hspice.mod` path may need to be checked
- current HSPICE license availability remains the practical blocker

Conclusion:

We do not yet have HSPICE + `io_buf.sp` transient evidence. The HSPICE evidence
we have is native IBIS, useful for trend comparison but not a completed version
of the plan's transistor-level HSPICE comparison.

## 8. ngspice Findings

### 8.1 What works in ngspice

ngspice works for:

- `io_buf.sp` transistor-level PRBS/RLGC reference
- pybis2spice PRBS/RLGC accepted benchmark
- SPISim-style small T-line validation cases for pybis
- deterministic pulse/bit-pattern/channel checks

The key working setup choices are:

- use V-source PWL stimulus, not B-source PWL
- use the new damped 50 ohm RLGC channel for the main acceptance case
- avoid unnecessary `uic` for the ngspice pybis PRBS/RLGC case
- use pybis model fixes already applied, including exact zero package params
  and corrected disabled-driver `Kd`
- use solver settings that are tolerant of behavioral-source stiffness

### 8.2 What did not work in ngspice

ngspice is not universally stable across all topologies:

| Case | Outcome | Why it matters |
|---|---|---|
| pybis PRBS + ideal lossless T-line | stalls before full run | Lossless T-line is a harsher numerical stress case than RLGC |
| pybis PRBS + ideal T-line + `uic/ic` | fails/stalls early | Startup treatment can make pybis internal state inconsistent |
| pybis PRBS + new 50 ohm RLGC + added `uic/ic` | stalls around 372 ns | The accepted ngspice pybis path should avoid `uic` |
| combined refspice + pybis in one ngspice bench | fragile | Separate benches plus post-processed overlays are more reliable |
| long ideal-T-line PRBS with no source damping | stalls near 125.6 ns | Shows topology-specific instability even in ngspice |

The ngspice PRBS/T-line source-damping sweep showed that a small series
resistance can help the ideal T-line stress case, but the effect is
non-monotonic. Around 1.75 to 2 ohm helped ngspice complete longer T-line
windows, while too little or too much did not.

Interpretation:

ngspice is the most reliable pybis path right now, but "reliable" means
reliable for the accepted RLGC benchmark, not guaranteed for every load or
startup condition.

## 9. Xyce Findings

### 9.1 What works in Xyce

Xyce works very well for the transistor-level `io_buf.sp` reference:

- Xyce accepts the BSIM3 model as level 9
- the PRBS/RLGC `io_buf.sp` run completes to 1000 ns
- Xyce and ngspice `io_buf.sp` physical-eye metrics agree closely

Xyce also works for pybis on the accepted PRBS/RLGC benchmark with the current
best continuation model:

- `driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub`
- deck: `results/prbs_rlgc_clean_2026-05-10/xyce/tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir`
- timestep controls: Backward-Euler style plus nonlinear-iteration timestep
  control
- completed to 1000 ns in the clean run
- compared to ngspice pybis with about 26.6 mV RMSE at `V(n10b)`

### 9.2 What did not work in Xyce

The direct pybis2spice model is not robust in Xyce:

| Case | Outcome | Observed failure mode |
|---|---|---|
| direct pybis PRBS/RLGC without `uic` | failed DCOP | DC operating point did not converge |
| direct pybis PRBS/RLGC with `uic` | stalls near first transition | excessive tiny timesteps |
| direct pybis compact pulse | stalls near first input transition | behavioral-source/timestep trap |
| direct `tanh200` repeated switching | partial progress only | not robust for repeated edges |
| Xyce pybis PRBS + ideal T-line | does not complete 100 ns for tested zero-damping profiles | harsher topology than RLGC |

The direct model can be syntax-ported to Xyce, but syntax compatibility is not
enough. The numerical issue is in the B-source/table/tanh/timing-control
structure.

### 9.3 Xyce root cause details

The strongest root-cause isolation was done on the practical 200 ps
rise-fall-rise ideal-T-line bench using a `tanh92` Xyce pybis model.

Observed behavior:

- stopping at 21 ns passes
- stopping at 22 ns times out around 21.89 ns
- output volume is not the cause; minimal print list still stalls
- loosening `DELMAX` is not the cause; `DELMAX=100p` still stalls
- replacing the T-line with an Rload changes the failure timing, so the load
  matters, but the T-line alone is not the whole explanation

The important internal state was the pybis rising waveform coefficient timing
tail:

- internal elapsed-time node `NX` continues sweeping after the visible input
  transition
- the bad region is around `NX = 4.2 to 4.8 ns`
- capping or flattening both rising `KUR` and `KDR` table tails after about
  4.2 ns lets the RFR T-line case complete
- capping only `KUR` or only `KDR` is not enough

So one root cause is the late rising waveform coefficient-table tail. For the
long PRBS/RLGC case, an additional issue appears in the edge detector/latch
block. That is why the best long-PRBS model relaxes the edge/latch block more
strongly than the final selector block.

### 9.4 Xyce model variants and what they mean

The key Xyce variants are:

| Variant | Meaning | Status |
|---|---|---|
| direct `tanh200` | closest to direct pybis | simple edges only; repeated switching not robust |
| `tanh92` | minimal deterministic smoothing candidate | good small cases; not full PRBS |
| `tanh50` / `edge50_flat4p2` | short PRBS and T-line compromise | better short stress behavior; not full 1000 ns PRBS |
| old all-`tanh15` | broad smoothing | full PRBS works but waveform error is larger |
| `edge15_flat4p2` | edge/latch `tanh15`, selector mostly `tanh92`, rising tail flat after 4.2 ns | current best full PRBS/RLGC path |

The best current practical full-run Xyce pybis setup is `edge15_flat4p2`.
However, it is not "minimal modification" in the strictest sense. It is a
numerical continuation setup that trades some model purity for a robust full
PRBS/RLGC run.

## 10. SPISim Reference Status

SPISim source/tool execution is not available in this environment. What we have
are static SPISim FreeSpice example decks and guidance.

What was useful from SPISim examples:

- ideal 50 ohm T-line validation is a useful small pre-PRBS gate
- single-pulse, rise-fall-rise, and deterministic patterns are better staging
  points than jumping straight to PRBS
- output and stimulus nodes should be kept simple and explicit

What remains partial:

- no direct SPISim conversion of our exact `io_buf.ibs` through a runnable
  SPISim tool
- no apples-to-apples SPISim metric row comparable to ngspice pybis and Xyce
  pybis for the final PRBS/RLGC benchmark

Conclusion:

SPISim is useful as a reference style and validation pattern source, but not
currently a completed experiment in the matrix.

## 11. Eye Tool Status

The eye diagram tool has gone through an important correction.

Earlier, an edge-aligned mode was added to make plots look more like a
conventional visual eye. That mode detected threshold crossings and redrew
transition families at both UI boundaries. It was useful diagnostically, but it
was not physically correct for this investigation because it removed the very
duty-cycle distortion we were trying to measure.

Current state:

- `scripts/eye_diagram.py` now uses clock/UI-grid folding only
- edge-aligned mode has been removed from the CLI
- `--fold_mode edge`, `--edge_include_clock_rails`, and
  `--edge_transition_only` are gone
- optional `--phase_ui` and `--auto_phase` still exist, but they apply one
  common phase offset to the entire waveform, not independent rise/fall shifts
- generated metrics now record `fold_mode = clock`

Important interpretation:

If the physical eye looks strange, the tool should show that. The tool should
not compensate for the transient distortion to create a visually ideal eye.

The report notes in `results/prbs_rlgc_clean_2026-05-10/EYE_NOTES.txt` were
also updated to state that the old edge-aligned folders are diagnostic only.

## 12. What Is Working and Why

### 12.1 ngspice + `io_buf.sp`

Working because:

- the MOS-level model is directly simulated, not behavioral-table controlled
- `hspice_ngspice.mod` contains model parameter adjustments needed for ngspice
  convergence
- the new RLGC channel provides realistic damping and a DC path
- V-source PWL stimulus provides clean timestep breakpoints

### 12.2 Xyce + `io_buf.sp`

Working because:

- Xyce supports the BSIM3 model form well enough for this deck
- the channel is made of primitive R/L/C/G elements
- output is direct CSV through `.PRINT TRAN FORMAT=CSV`
- the transistor-level deck avoids the pybis B-source timing machinery

### 12.3 ngspice + pybis2spice

Working for the accepted RLGC benchmark because:

- pybis model bugs were fixed
- package parasitic zeros were forced to exact zeros
- disabled-driver `Kd` behavior was corrected
- V-source PWL stimulus exposes event breakpoints
- `uic` is avoided in the accepted pybis RLGC run
- the RLGC channel is less pathological than the ideal T-line

### 12.4 Xyce + pybis2spice continuation setup

Working for the accepted RLGC benchmark because:

- pybis syntax was converted to Xyce expression syntax
- `pwl()` constructs were converted to Xyce `table()` equivalents
- Xyce time integration was tuned toward Backward-Euler/non-LTE control
- the edge/latch tanh gates were relaxed enough to avoid repeated-switching
  traps
- the rising coefficient table tail was flattened after the bad late-tail
  region

This is a practical engineering path, not yet a proof that the direct pybis
model is natively robust in Xyce.

## 13. What Is Not Working and Why

### 13.1 Direct Xyce pybis full PRBS

Not working because the direct pybis behavioral model is numerically too stiff
for Xyce during repeated switching.

Main contributors:

- sharp `tanh(200*...)` gates
- edge detector/latch logic around input transitions
- waveform coefficient lookup tables
- internal time/tail tracking through `NX`
- coupling to reactive loads such as T-lines and RLGC channels

The direct model is not just a syntax problem. It parses after conversion, but
the transient solve becomes pathological.

### 13.2 Ideal T-line PRBS as a universal acceptance case

Not working as a universal benchmark because it is a severe numerical stress
case. It exposes solver/model interactions that are not present in the accepted
RLGC benchmark.

Evidence:

- ngspice direct pybis stalls around 125.6 ns for long ideal-T-line PRBS with
  no damping
- Xyce profiles also fail or only partially pass the ideal-T-line PRBS case
- small source damping helps ngspice and helps Xyce short windows, but does not
  fully solve Xyce long T-line PRBS

Conclusion:

The ideal T-line PRBS case is valuable as a stress test, but it should not be
the primary pass/fail gate for the current project unless the project goal is
explicitly changed to lossless-line robustness.

### 13.3 HSPICE + `io_buf.sp`

Not working yet because it has not been run successfully or at least no result
has been saved.

The deck exists, but:

- no output files were found
- include paths likely need cleanup
- HSPICE license availability is unresolved

### 13.4 Eye tool compensation mode

Not working conceptually because it was non-physical for this purpose.

The edge-aligned mode made the plot look closer to a conventional eye by moving
transition families onto desired boundaries. That is not acceptable when the
question is whether the transient waveform itself has rise/fall phase
distortion.

The mode has been removed.

## 14. Current Stability Classification

| Flow | Stability label | Explanation |
|---|---|---|
| ngspice + `io_buf.sp` + PRBS/RLGC | Stable | Completes accepted benchmark and agrees with Xyce |
| Xyce + `io_buf.sp` + PRBS/RLGC | Stable | Completes accepted benchmark quickly and agrees with ngspice |
| ngspice + direct pybis + PRBS/RLGC | Stable for accepted benchmark | Completes full 1000 ns; still topology/startup sensitive |
| Xyce + direct pybis + PRBS/RLGC | Not stable | DCOP/stall issues remain |
| Xyce + `edge15_flat4p2` pybis + PRBS/RLGC | Practical pass | Completes full 1000 ns with good ngspice agreement, but modified model |
| ngspice + pybis + PRBS/ideal T-line | Not stable for long run | Stalls near 125.6 ns without damping |
| Xyce + pybis + PRBS/ideal T-line | Not stable for long run | No tested profile completes long T-line PRBS |
| HSPICE native IBIS | Historical data only | `.tr0` files exist, but not current matched benchmark |
| HSPICE + `io_buf.sp` | Not done | Deck exists, no transient result |

## 15. Testbench Setup and Syntax Reference

This section is the practical setup reference extracted from the experiments.
It is deliberately more syntax-oriented than the earlier status sections.

### 15.1 Cross-Simulator Rules Learned

| Setup item | Working rule | What failed or was risky | Why |
|---|---|---|---|
| PRBS source | Use an independent voltage source with inline `PWL(...)` include | Behavioral `B` source with `pwl()` | V-source PWL exposes breakpoints to the timestep controller; behavioral PWL hides them |
| PRBS initial state | Use inverted PRBS mapping so the initial output state is LOW | HIGH-first PRBS startup for pybis | The pybis DC operating point naturally starts with `Ku=0`, `Kd=1`; HIGH-first starts with inconsistent internal state |
| Main channel | Use the new 50 ohm RLGC ladder | Treat ideal lossless T-line PRBS as the main acceptance case | RLGC has damping and is portable; ideal T-line is a harsher solver stress case |
| Output probing | Save/print only needed nodes for long runs | Excessive internal probes in long PRBS | Output volume is not the main root cause, but it can make runs slower and files huge |
| Eye folding | Use physical clock/UI-grid fold | Per-edge alignment to force a pretty eye | Per-edge alignment hides real duty-cycle distortion |
| One-bench comparison | Prefer separate refspice and pybis benches with post-processing overlay | Combined refspice+pybis bench | Combined nonlinear systems were more fragile and harder to debug |

### 15.2 PRBS Stimulus Syntax

The current portable PRBS include style is:

```spice
Vstim  in_dig  0  PWL(0.000000000e+00 0.0000
+ 5.000000000e-09  0.0000
+ ...
)
```

This works in ngspice and Xyce. It replaced older HSPICE-oriented syntax such
as:

```spice
Vstim  in_dig  0  PWL PWLFILE='prbs11.pwl'
```

The `PWLFILE=` form is not the preferred common syntax for this open-source
flow. Inline PWL includes are easier to share across ngspice and Xyce.

The project should continue avoiding this form for PRBS:

```spice
Bstim in_dig 0 V = pwl(time, ...)
```

The behavioral-source form was a major performance risk because the simulator
does not see the PRBS transition times as source breakpoints.

### 15.3 ngspice Syntax and Setup Matrix

| ngspice setup | Representative file | Result | Interpretation |
|---|---|---|---|
| `io_buf.sp` refspice, RLGC, `.tran ... uic`, `.ic` on output/channel | `ngspice_refspice/tb_refspice_prbs7_new50ohm_batch.sp` | Pass to 1000 ns | Good setup for transistor-level reference; `uic` avoids problematic OP on reactive channel |
| pybis, RLGC, no `uic`, V-source PWL | `ngspice_pybis/tb_pybis_prbs7_new50ohm.sp` and clean rerun deck | Pass to 1000 ns | Current accepted ngspice pybis style |
| pybis, RLGC, refspice-style input `Rin=1`, no `uic` | `tb_pybis_prbs7_new50ohm_step1_rin.sp` | Pass to 1000 ns | `Rin=1` is safe and improves source/node conditioning |
| pybis, RLGC, add `.ic` + `uic` | `tb_pybis_prbs7_new50ohm_step2_uic.sp` | Stall at 372.127 ns | First regression point in alignment study |
| pybis, RLGC, `uic` plus stronger solver options | `tb_pybis_prbs7_new50ohm_step3_solver.sp` | Stall at 396.059 ns | Solver tweaks did not rescue the `uic` regression |
| pybis, RLGC, `uic` plus refspice-like power feed/decap | `tb_pybis_prbs7_new50ohm_step4_pwr.sp` | Stall at 396.069 ns | Power feed changes did not fix the pybis `uic` issue |
| pybis, ideal T-line PRBS, no damping | `tb_pybis_prbs7_batch.sp` / PRBS T-line runner | Fails long run; stalls near 125.6 ns in stress sweep | Ideal T-line PRBS is a topology stress case, not the accepted path |
| pybis, ideal T-line PRBS, `RISO` about 1.75-2 ohm | PRBS/T-line damping sweep | Passes 130 ns and 200 ns in ngspice | Small source damping can fix this topology, but effect is non-monotonic |
| pybis, ideal T-line PRBS, too little or too much `RISO` | `RISO=0`, `0.1`, `0.5`, `1.0`, `1.5`, `5.0` ohm | Fails/stalls | Damping is not monotonic; 5 ohm created a new slow case |

The most important ngspice-specific lesson is that `uic` is not universally
good or bad. It helps the transistor-level refspice reactive-channel bench, but
it hurts the pybis PRBS/RLGC bench. The accepted ngspice pybis setup should
therefore use normal operating point, no `uic`.

The current accepted ngspice pybis option block is:

```spice
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7
.tran 10p 1000n
```

The current ngspice refspice option/transient style is:

```spice
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran 10p 1000n uic
```

That difference should be kept. Trying to force the pybis bench to look exactly
like the refspice bench was one of the ways we found the setup boundary.

### 15.4 ngspice Output and Probing

ngspice decks use `.save` to restrict raw output:

```spice
.save V(in_dig) V(pad) V(tx_out) V(n10b)
```

The actual `.raw` files are then parsed by Python. For long PRBS runs, this is
preferable to dumping every internal pybis node by default.

Internal pybis nodes are still useful in short diagnostics:

- `v(xdrv.ku)`
- `v(xdrv.kd)`
- internal timing nodes when available

But for long acceptance runs, they should be limited unless actively debugging.

### 15.5 Xyce Syntax Porting Rules

Xyce needed real syntax conversion for the pybis behavioral model.

| ngspice/pybis form | Xyce form | Reason |
|---|---|---|
| `Bxx n1 n2 V = expression` | `Bxx n1 n2 V={expression}` | Xyce requires expression braces |
| `Bxx n1 n2 I = expression` | `Bxx n1 n2 I={expression}` | Same for current sources |
| `pwl(x, ...)` inside expressions | `table(x, ...)` | Xyce expression support differs |
| ngspice `.save` | `.print tran format=csv ...` | Xyce writes CSV/PRN through `.print` |
| ngspice internal probe `v(xdrv.ku)` | Xyce probe `V(XDRV:Ku)` | Xyce subcircuit internal node syntax |
| ngspice behavioral shunt `G value={1e-6*v(n,0)}` | `R_G n 0 1meg` | Linear resistor is simpler and Xyce-portable |

The Xyce channel file therefore replaces each ngspice behavioral conductance:

```spice
G1 n1b 0 value={1e-6*v(n1b,0)}
```

with:

```spice
R_G1 n1b 0 1meg
```

This is electrically equivalent for the intended shunt conductance and avoids
unnecessary behavioral syntax in the channel.

### 15.6 Xyce Setup Matrix

| Xyce setup | Representative file | Result | Interpretation |
|---|---|---|---|
| `io_buf.sp` refspice, RLGC, `.ic`, `uic` | `xyce_refspice/tb_refspice_prbs7_new50ohm_xyce.cir` | Pass to 1000 ns | Good transistor-level Xyce reference setup |
| direct pybis, RLGC, no `uic` | `xyce_pybis/tb_pybis_prbs7_new50ohm_xyce.cir` | Fails DCOP | Syntax-valid direct model still not numerically robust |
| direct pybis, RLGC, `.ic` + `uic`, 100 ns diagnostic | `xyce_pybis/tb_pybis_prbs7_new50ohm_xyce_uic_100n.cir` | Stalls near first PRBS rising edge | Skipping OP alone does not solve direct pybis stiffness |
| direct pybis, simple delayed Rload edge, BE/non-LTE options | time-integration diagnostic decks | Pass | Xyce can handle simple direct-model edges with the right transient controls |
| direct pybis, repeated switching | pulse-train/bit-pattern diagnostics | Timeout/partial | Repeated switching remains the direct-model boundary |
| relaxed pybis `tanh92`, T-line pulse200p | SPISim-style validation | Pass | Good minimal-modification single-pulse candidate |
| relaxed pybis `tanh92`, T-line RFR200p | root-cause bench | Timeout around 21.89 ns | Late rising coefficient-tail issue |
| tail flat/cap at 4.2 ns | tail-fix benches | Fixes T-line RFR200p | Confirms late `KUR/KDR` tail root cause |
| `edge50_flat4p2`, channel PRBS 200 ns | tail-fix summary | Pass | Good short-PRBS compromise |
| `edge50_flat4p2`, channel PRBS 1000 ns | tail-fix summary | Timeout at 205.27 ns | Not enough for full accepted run |
| `edge15_flat4p2`, channel PRBS 1000 ns | clean Xyce rerun | Pass to 1000 ns | Current best full PRBS/RLGC setup |
| `edge15_flat4p2`, ideal T-line PRBS | PRBS/T-line runner | Fails short/long T-line stress | Full-RLGC winner is not universal |
| `edge50_flat4p2` with `RISO=2` on ideal T-line PRBS 100 ns | damping sweep | Passes 100 ns | Source damping helps Xyce T-line stress, but not enough for 200 ns |

The current accepted Xyce pybis transient setup is:

```spice
.ic V(pad)=0 V(tx_out)=0 V(n10b)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
.options output initial_interval=10p
.tran 10p 1000n uic
.print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
```

The `method=trap maxord=1` setting effectively limits the method to
Backward-Euler behavior. Combined with `erroption=1`, `delmax=20p`, and the
`nlmin/nlmax` bounds, it made Xyce much more capable on the pybis behavioral
model than the default transient controls.

The `.options output initial_interval=10p` line is not a convergence fix. It
reduces output file size and can improve runtime, but tests showed it does not
solve a true solver stall by itself.

### 15.7 Xyce `.ic` / `uic` Lessons

For Xyce pybis, `uic` is currently required for the practical path, but only
when paired with explicit internal state initialization. The important internal
state values are:

```spice
V(XDRV:Ku)=0
V(XDRV:Kd)=1
V(XDRV:NX)=0
V(XDRV:N6)=0
V(XDRV:N8)=0
```

Without this, the pybis internal latch/timing state can begin in a state that
does not match the PRBS input/output state.

For direct pybis, even this is not enough for full repeated switching. It
allows some simple cases, but the direct model still stalls in repeated-edge
cases.

For Xyce refspice, `.ic + uic` is simpler: initialize the output/channel nodes
and skip DCOP.

```spice
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran 10p 1000n uic
```

### 15.8 Setup Results from SPISim-Style Validation

The SPISim-style small benches are now useful as setup gates before PRBS.

| Setup | ngspice direct pybis | Xyce direct pybis | Xyce relaxed candidates |
|---|---:|---:|---:|
| T-line pulse, 5 ps edge | Pass | Fail/partial | Fail/partial |
| T-line pulse, 200 ps edge | Pass | Partial to 12.26 ns | `tanh92`, `tanh50`, `tanh20`, `tanh15` pass |
| T-line RFR, 5 ps edge | Pass | Fail/partial | Fail/partial |
| T-line RFR, 200 ps edge | Pass | Partial to 9.37 ns | Initial relaxed variants still partial around 21.9-22.5 ns |

This taught two setup rules:

1. 5 ps SPISim-style edges are too severe for Xyce pybis acceptance. They are
   stress tests.
2. 200 ps edges match the main project stimulus and should be the first Xyce
   validation gate.

### 15.9 Root-Cause Setup Isolation for Xyce RFR/T-Line

The key root-cause setup matrix was:

| Experiment | Result | Meaning |
|---|---|---|
| Stop at 21 ns | Pass | Before bad coefficient-tail region |
| Stop at 22 ns | Timeout at 21.89 ns | Failure starts around this region |
| Minimal print list | Timeout at same time | Output volume not causal |
| `DELMAX=100p` | Timeout at same time | Max-step cap not causal |
| Rload instead of T-line | Timeout later at 25.26 ns | T-line contributes, but there is also falling-edge stiffness |
| Cap `NX` at 4.0-4.2 ns | Pass | Internal elapsed-time tail is involved |
| Cap only `KUR` at 4.2 ns | Fail | Pullup rising coefficient alone not enough |
| Cap only `KDR` at 4.2 ns | Fail | Pulldown rising coefficient alone not enough |
| Cap both `KUR` and `KDR` at 4.2 ns | Pass | Confirms coupled rising coefficient-tail issue |

This is why later Xyce candidates flatten both rising coefficient tails after
4.2 ns.

### 15.10 Recommended Setup Profiles

Use these profiles as the current reference setups:

| Purpose | Simulator | Recommended setup |
|---|---|---|
| Transistor-level reference | ngspice | `io_buf.sp`, `hspice_ngspice.mod`, RLGC, `Rin=1`, `.ic`, `.tran ... uic` |
| Transistor-level reference | Xyce | Same topology, Xyce channel resistor shunts, `.print tran format=csv`, `.ic`, `.tran ... uic` |
| pybis accepted PRBS/RLGC | ngspice | direct pybis, RLGC, no `uic`, Gear options, V-source PWL |
| pybis accepted PRBS/RLGC | Xyce | `edge15_flat4p2`, explicit internal `.ic`, BE/non-LTE options, output throttling |
| pybis small validation | ngspice | SPISim-style ideal T-line, 200 ps pulse/RFR, direct pybis |
| pybis small validation | Xyce | start with pulse200p and `tanh92`/`edge50_flat4p2`; use RFR200p as stress gate |
| ideal T-line PRBS stress | ngspice | direct pybis with source damping sweep; `RISO=1.75-2 ohm` can help |
| ideal T-line PRBS stress | Xyce | not solved for long windows; `edge50_flat4p2 + RISO=2` only passes 100 ns |

### 15.11 Setups to Avoid as Defaults

| Avoid as default | Reason |
|---|---|
| ngspice pybis PRBS/RLGC with `uic` | It was the first known regression point and caused stalls |
| Xyce direct pybis PRBS/RLGC without internal `.ic` | DCOP fails or first transition stalls |
| ideal lossless T-line PRBS as acceptance gate | It fails even ngspice long-run without damping; use as stress test only |
| 5 ps input edges for Xyce pybis acceptance | Too severe and not aligned with the main 200 ps project stimulus |
| B-source PRBS stimulus | Hides breakpoints and causes tiny-step overhead |
| edge-aligned eye plots as final evidence | They remove real rise/fall phase distortion |
| combined refspice+pybis long bench | More fragile than separate runs and post-processing overlay |

### 15.12 Parameter Sensitivity Beyond `uic`

The setup study was not limited to `uic`. Several other categories were tested:

- solver method and order
- tolerances and timestep controls
- source isolation and damping resistors
- channel topology
- stimulus edge rate
- behavioral smoothing factor
- coefficient-table tail conditioning
- output throttling
- probe list size
- startup state and internal `.ic` values

The table below summarizes what we learned.

| Parameter category | Values/forms tested | Main result | Practical rule |
|---|---|---|---|
| ngspice integration method/order | Gear, `maxord=1`, `maxord=2` | pybis accepted bench uses Gear `maxord=1`; refspice uses Gear `maxord=2`; changing pybis to refspice-like solver did not rescue the `uic` regression | Keep separate solver profiles for refspice and pybis |
| ngspice tolerances | `reltol`, `abstol`, `vntol`, `gmin`, `trtol`, `itl4`, `itl5` | More relaxed pybis tolerances help the behavioral model run; stricter refspice-like tolerances did not fix pybis when startup was wrong | Use the known pybis option block for pybis; do not blindly copy refspice options |
| ngspice input isolation | direct source vs `Rin=1` | Adding `Rin=1` to the pybis PRBS/RLGC path still passed 1000 ns | `Rin=1` is safe and useful for source/node conditioning |
| ngspice power/enable feed | direct DC sources vs source-to-node `1 ohm` feed plus decap | Did not rescue the pybis `uic` failure | Power-feed cleanup is not the main pybis failure mechanism |
| Channel topology | RLGC ladder vs ideal T-line | RLGC PRBS passes; ideal T-line PRBS is a stress case and stalls long runs | Use RLGC as acceptance channel; keep ideal T-line as stress test |
| Source damping in ideal T-line PRBS | `RISO=0`, `0.1`, `0.5`, `1.0`, `1.25`, `1.5`, `1.75`, `2.0`, `5.0` ohm | ngspice passes long T-line windows around `1.75-2.0 ohm`; too little or too much damping fails | Damping helps but is non-monotonic; do not assume larger `RISO` is always better |
| Input edge rate | 5 ps vs 200 ps | ngspice passes both SPISim-style small benches; Xyce pybis fails/partials on 5 ps but handles 200 ps single-pulse variants | Use 200 ps as project validation edge; 5 ps is a stress case |
| Xyce time integration | default, Gear LTE, Gear non-LTE, BE/non-LTE | BE/non-LTE was the first option set that made repeated-switching `tanh20` pulse train pass 40 ns | Use BE/non-LTE controls for Xyce pybis |
| Xyce timestep bounds | `DELMAX=20p` vs `DELMAX=100p` in root-cause case | T-line RFR stalled at the same late-tail point; `DELMAX` alone was not causal | `DELMAX` is useful, but not a root-cause fix by itself |
| Xyce nonlinear timestep controls | `erroption=1`, `nlmin=3`, `nlmax=8`, `timestepsreversal=1` | Needed for practical Xyce pybis progress, especially with BE-like integration | Keep as part of Xyce pybis profile |
| Xyce output throttling | `.options output initial_interval=10p` | Reduced CSV size and runtime; did not solve solver stalls | Use for long outputs, not as a convergence fix |
| Xyce probe list size | full vs minimal print list | Minimal print still stalled at same root-cause point | Output volume was not the root cause of the RFR/T-line stall |
| Behavioral smoothing | direct `tanh200`, `tanh100`, `98`, `95`, `94`, `92`, `90`, `75`, `60`, `50`, `30`, `20`, `18`, `17`, `16`, `15`, `12`, `10` | Pass/fail is non-monotonic; `tanh92` passes deterministic pulse train, `tanh50` helps short PRBS, `tanh15` enables full PRBS/RLGC | Treat smoothing as a targeted continuation parameter, not a simple "more smoothing is better" knob |
| Xyce coefficient tail | no cap, `NX` cap, `KUR` cap, `KDR` cap, both `KUR/KDR` cap or flat tail at 4.2 ns | Only both rising `KUR/KDR` tail conditioning fixed the RFR/T-line stall | Tail conditioning must apply to both rising coefficient tables |
| Xyce edge/latch vs selector smoothing | selector-only smoothing, edge/latch smoothing, mixed variants | Selector smoothing did not solve PRBS; edge/latch smoothing was the important PRBS knob | PRBS instability is primarily in edge/latch timing logic, not final Ku/Kd selector |

#### ngspice solver/tolerance details

The accepted ngspice pybis setup uses:

```spice
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7
```

The refspice setup uses:

```spice
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10
```

The alignment study intentionally tried making pybis more refspice-like after
adding `uic`. That failed. The lesson is that the solver profile alone was not
the deciding factor; the startup/internal-state condition created by `uic` was
the larger issue for ngspice pybis.

#### Xyce time-integration sweep

The Xyce repeated-pulse parameter sweep showed:

| Xyce setup | Result | Final time |
|---|---:|---:|
| `tanh20` default | fail | 26.67 ns |
| `tanh20` Gear LTE | fail | 21.62 ns |
| `tanh20` Gear non-LTE | fail | 38.98 ns |
| `tanh20` BE/non-LTE | pass | 40 ns |
| direct `tanh200` BE/non-LTE | fail | 33.94 ns |

So the integration controls mattered a lot. They were enough to make some
relaxed repeated-switching cases pass, but not enough for the direct model.

The most useful Xyce block remains:

```spice
.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
```

`method=trap maxord=1` is effectively the Backward-Euler-like profile we used.

#### Xyce smoothing-factor sweep

The deterministic 40 ns pulse-train sweep showed non-monotonic behavior:

| Factor | Result |
|---:|---|
| direct `tanh200` | fail at 33.94 ns |
| `tanh100` | fail at 36.81 ns |
| `tanh98` / `95` / `94` | fail around 28.97 ns |
| `tanh92` | pass 40 ns |
| `tanh90` | pass 40 ns |
| `tanh75` | pass 40 ns |
| `tanh60` | fail at 31.77 ns |
| `tanh50` | pass 40 ns |
| `tanh30` | fail at 9.00 ns |
| `tanh20` | pass 40 ns |

The PRBS sweep gave a different hierarchy:

| Candidate | PRBS result |
|---|---|
| `tanh15` | pass 1000 ns |
| `tanh20` | fail at 110.07 ns |
| `tanh50` | pass 200 ns, fail 1000 ns at 205.27 ns |
| `tanh75` | fail 200 ns at 105.40 ns |
| `tanh90` | fail 200 ns at 95.32 ns |
| `tanh10` | fail 200 ns at 125.26 ns |

This is why the report distinguishes:

- `tanh92`: good deterministic minimal-modification candidate
- `tanh50`: good short-PRBS compromise
- `edge15_flat4p2`: current full PRBS/RLGC practical pass

#### Source damping sweep

The PRBS/T-line damping study is important because it shows load/topology
parameters matter too:

| Simulator/setup | Damping | Result |
|---|---:|---|
| ngspice direct pybis, 130 ns T-line PRBS | `RISO=0` | fail at 125.56 ns |
| ngspice direct pybis, 130 ns T-line PRBS | `RISO=1.75` | pass |
| ngspice direct pybis, 130 ns T-line PRBS | `RISO=2.0` | pass |
| ngspice direct pybis, 200 ns T-line PRBS | `RISO=2.0` | pass |
| ngspice direct pybis, 200 ns T-line PRBS | `RISO=5.0` | fail at 109.99 ns |
| Xyce `edge50_flat4p2`, 100 ns T-line PRBS | `RISO=0` | fail at 95.44 ns |
| Xyce `edge50_flat4p2`, 100 ns T-line PRBS | `RISO=2.0` | pass |
| Xyce `edge50_flat4p2`, 200 ns T-line PRBS | `RISO=2.0` | fail at 106.06 ns |

This confirms the ideal T-line case is topology-sensitive and not equivalent to
the accepted RLGC channel case.

## 16. Artifact Map

Important current artifacts:

- Plan: `ibis_comparison_plan.md`
- Frozen final benchmark folder:
  `results/final_prbs_rlgc_comparison_2026-05-11/`
- Final benchmark builder:
  `scripts/build_final_prbs_rlgc_comparison.py`
- One-command accepted benchmark regression:
  `scripts/run_accepted_prbs_rlgc_regression.py`
- Xyce pybis minimum-modification ladder:
  `scripts/run_xyce_pybis_minmod_ladder.py`
- Xyce pybis ladder results:
  `results/xyce_pybis_minmod_ladder_2026-05-11/`
- Xyce result notes: `docs/reports/XYCE_RESULTS_2026-05-09.md`
- ngspice alignment notes: `docs/reports/ALIGNMENT_FINDINGS_2026-05-07.md`
- Clean pybis PRBS/RLGC run: `results/prbs_rlgc_clean_2026-05-10/`
- HSPICE `.tr0` comparison: `results/hspice_tr0_comparison_2026-05-11/`
- Physical `io_buf.sp` eyes: `results/io_buf_sp_physical_eye_2026-05-11/`
- Xyce pybis root-cause metrics:
  `plots/xyce_pybis/xyce_pybis_rootcause_experiments.csv`
- Xyce tail-fix summary:
  `plots/xyce_pybis/xyce_pybis_tailfix_recommendation_summary.csv`
- PRBS/T-line stress summary:
  `plots/xyce_pybis/xyce_pybis_prbs_tline_damping_summary.csv`

## 17. Current Action Status and Next Steps

### Step 1: Freeze the current accepted benchmark - done

The accepted benchmark is now explicitly frozen as:

- PRBS7
- 5 ns UI
- 200 ps input transition
- 1000 ns transient
- new 50 ohm RLGC channel
- 50 ohm termination
- physical clock-folded eye only

The frozen result package is:

`results/final_prbs_rlgc_comparison_2026-05-11/`

This prevents the project from mixing "accepted SI benchmark" and "stress test"
results in the same pass/fail bucket.

### Step 2: Update `ibis_comparison_plan.md` - done

The plan now records the current status:

- ngspice `io_buf.sp`: done
- Xyce `io_buf.sp`: done
- ngspice pybis: done for accepted RLGC benchmark
- Xyce pybis: practical pass with modified continuation model
- SPISim: partial reference only
- HSPICE native/HSPICE `io_buf.sp`: deferred/not done

### Step 3: Treat Xyce pybis as two separate questions - done

Question A: Can Xyce run the accepted pybis benchmark?

Answer: yes, with `edge15_flat4p2`.

Question B: Can Xyce run the direct/minimally modified pybis model robustly?

Answer: not yet.

These should remain separate because they have different scientific meanings.

### Step 4: Run HSPICE + `io_buf.sp` when possible - deferred

When the HSPICE license is available:

1. fix include paths in `experiments/tb_exp2.sp`
2. align the bench to PRBS7 + new 50 ohm RLGC + 50 ohm termination
3. run `.TRAN 10p 1000n`
4. parse `.tr0` with the current physical eye tool
5. add the result to the same metrics table as ngspice/Xyce `io_buf.sp`

This is the main missing commercial-tool reference.

### Step 5: Keep ideal T-line PRBS as a stress test - active

The ideal T-line PRBS case should remain in the report, but should be labeled
as a stress case. It is useful for solver research, not the current acceptance
gate.

### Step 6: Avoid visual compensation in eye plots - active

Future eye diagrams should be generated with the physical clock-folded tool. If
an edge-aligned diagnostic is ever reintroduced, it should be a separate script
or explicitly named diagnostic plot, not the default eye diagram.

## 18. Bottom Line

The current open-source pipeline is usable for PRBS/RLGC comparison. The
transistor-level `io_buf.sp` path is strong in both ngspice and Xyce. The
ngspice pybis path is also strong for the accepted RLGC benchmark. The Xyce
pybis path is promising but should be described carefully: the current full
PRBS/RLGC pass is achieved through a controlled Xyce-specific continuation
model, not through the direct pybis model.

The main unresolved pieces are:

1. formal HSPICE + `io_buf.sp` transient result
2. deciding whether the Xyce relaxed pybis model is acceptable for the study or
   should remain labeled as a workaround
3. continuing direct/minimal-modification Xyce pybis research only if that
   becomes a core objective
