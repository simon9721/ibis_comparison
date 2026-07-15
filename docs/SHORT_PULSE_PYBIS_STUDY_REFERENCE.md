# Short-Pulse pybis Study Reference

This document is the reference note for the `io_buf` interrupted-switching work. It explains the baseline problem, the matched HSPICE/ngspice setup, where the frozen baseline artifacts live, and how to prepare a new ngspice+pybis testbench for comparison.

The purpose is to make every later short-pulse experiment answer one clean question:

> If HSPICE native IBIS is the golden reference, does the ngspice+pybis model preserve the same pad waveform and the same switching coefficient history when an input reverses before the previous output transition settles?

## Scope

- Device/model: `hspice/sparam/io_buf.ibs`
- IBIS component: `MCM Driver 1`
- IBIS model: `driver`
- pybis mode for the frozen baseline: `InputDriven`
- HSPICE reference: native IBIS `B` element
- Main baseline result folder: `results/io_buf_switching_coeff_sweep_2026-06-19`
- Main interrupted-switching demo: `results/io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo`

## The Problem

### Long Enough Step Pulse

In the normal control case, the input switches high, stays high long enough for the pad and the internal pullup/pulldown switching functions to mostly settle, then switches low.

For the baseline control:

- Case: `edge_1ps_base_50r_2pf`
- Input edge rate: `1 ps`
- Load: `50 ohm || 2 pF`
- Input high voltage: `3.3 V`
- Input goes high at `5 ns`
- Input goes low at `15 ns`
- Stop time: `25 ns`

The PWL stimulus is:

```spice
Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+        15n      3.3
+    15.001n        0
+        25n        0 )
```

In this case, simple pybis coefficient replay works well because each switching event is effectively complete before the next one starts.

Baseline result:

- Pad active-window RMSE: `5.289 mV`
- Ku RMSE: `0.00434`
- Kd RMSE: `0.00561`
- Classification: `GOOD`

### Short Step Input

In the interrupted case, the input command reverses before the previous output transition settles. That makes the internal state of the pullup/pulldown networks matter.

The original short-pulse demo case is:

- Case: `short_pulse_2ns_high`
- Input edge rate: `1 ps`
- Load: `50 ohm || 2 pF`
- Input high voltage: `3.3 V`
- Input goes high at `5 ns`
- Input goes low at `7 ns`
- Stop time: `14 ns`

The PWL stimulus is:

```spice
Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+         7n      3.3
+     7.001n        0
+        14n        0 )
```

At the reverse command, the pad is still far below its settled-high value:

- Settled high from full-toggle control: `1.545 V`
- HSPICE pad at reverse command: `0.266 V`
- ngspice+pybis pad at reverse command: `0.260 V`

So the second edge arrives while the output is still in the middle of the previous transition.

## What Ku And Kd Mean

`Ku` and `Kd` are IBIS switching coefficients.

- `Ku` is the effective pullup switching function.
- `Kd` is the effective pulldown switching function.
- Roughly, `1` means that network is fully enabled.
- Roughly, `0` means that network is off.

This is not exactly a transistor gate voltage, but it behaves like an effective strength control for the IBIS pullup and pulldown I/V tables.

The important point for this study is that `Ku/Kd` are not just output plots. They are the internal coefficient history that drives the pad waveform. A pad-only match can be misleading if `Ku/Kd` are wrong.

## Baseline Flows

### Flow Diagram

```text
Common input:
  io_buf.ibs + same PWL stimulus + same rails + same 50 ohm/2 pF load

HSPICE reference:
  io_buf.ibs
    -> HSPICE native IBIS B element
    -> pad_ibis, ku, kd
    -> .tr0/.lis golden reference

ngspice baseline:
  io_buf.ibs
    -> pybis2spice generated InputDriven .sub
    -> ngspice XDRV instance
    -> pad, xdrv.ku, xdrv.kd
    -> .raw baseline free-SPICE response

Comparison:
  HSPICE .tr0 + ngspice .raw
    -> common time grid
    -> pad RMSE/max error
    -> Ku RMSE/max error
    -> Kd RMSE/max error
    -> peak/timing/state diagnostics
```

## HSPICE Golden Reference Setup

HSPICE uses its native IBIS element. The important part of the deck is:

```spice
Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rdig dig_q 0 1k
Rload pad_ibis 0 50
Cload pad_ibis 0 2p

.probe tran V(in_dig) V(pad_ibis) V(dig_q) V(ku) V(kd)
.tran 0.001n <stop_time>
```

Notes:

- `xv_pu=ku` exposes HSPICE's native pullup switching coefficient.
- `xv_pd=kd` exposes HSPICE's native pulldown switching coefficient.
- `pad_ibis` is the HSPICE pad/output node.
- The reference uses the same input PWL and same load as the ngspice deck.
- HSPICE is the golden reference for validation only. It is not used to fit pybis parameters.

For the short-pulse baseline, the actual deck is:

`results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/hspice_native_ibis/short_pulse_2ns_high_hspice_native_ibis.sp`

The matching HSPICE outputs are:

- `results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/hspice_native_ibis/short_pulse_2ns_high_hspice_native_ibis.tr0`
- `results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/hspice_native_ibis/short_pulse_2ns_high_hspice_native_ibis.lis`
- `results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/hspice_native_ibis/hspice_stdout.log`

## ngspice+pybis Baseline Setup

The baseline ngspice subcircuit is generated from the same IBIS file:

```powershell
py -3.14 scripts/convert_ibis_to_pybis.py `
  hspice/sparam/io_buf.ibs `
  --component "MCM Driver 1" `
  --model driver `
  --io-type Output `
  --subcircuit-type InputDriven `
  --corner Typical `
  --out results/io_buf_switching_coeff_sweep_2026-06-19/common/driver_OutputInput_Typical.sub
```

The generated subcircuit is:

`results/io_buf_switching_coeff_sweep_2026-06-19/common/driver_OutputInput_Typical.sub`

The short-pulse ngspice deck instantiates that subcircuit like this:

```spice
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n <stop_time>
```

Notes:

- `pad` is the ngspice pad/output node.
- `V(xdrv.ku)` and `V(xdrv.kd)` are pybis-generated coefficient nodes.
- The baseline model type is `InputDriven`.
- The legacy pybis behavior is intentionally not changed when testing new experimental modes.

For the short-pulse baseline, the actual deck is:

`results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/ngspice_pybis/short_pulse_2ns_high_ngspice_pybis.sp`

The matching ngspice outputs are:

- `results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/ngspice_pybis/short_pulse_2ns_high_ngspice_pybis.raw`
- `results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/ngspice_pybis/ngspice_stdout.log`

The local unattended ngspice executable is:

`C:/Users/sh3qm/code/ibis_comparison/.codex_deps/ngspice-46_64/Spice64/bin/ngspice_con.exe`

Run example:

```powershell
& .\.codex_deps\ngspice-46_64\Spice64\bin\ngspice_con.exe `
  -b `
  -r short_pulse_2ns_high_ngspice_pybis.raw `
  short_pulse_2ns_high_ngspice_pybis.sp
```

Run it from the ngspice case folder:

`results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/ngspice_pybis`

## Cached Reference Artifacts

### HSPICE Cache

HSPICE is the golden reference. If the reference setup is unchanged, it should not be rerun.

The current scripts use two reuse layers:

1. Central golden cache:

   `results/_golden_hspice_cache/`

2. Existing per-study output:

   `results/io_buf_switching_coeff_sweep_2026-06-19/cases/<case>/hspice_native_ibis/*.tr0`

The cache key includes:

- Generated HSPICE deck text
- IBIS file hash
- Case id
- Reference family name, currently `io_buf_native_ibis`

That means HSPICE reruns only when the reference really changes, for example:

- The PWL stimulus changes.
- The load changes.
- The IBIS file changes.
- The HSPICE native IBIS options change.
- The stop time or transient setup changes.

If only the ngspice+pybis implementation changes, the HSPICE reference should be restored from cache or reused from existing `.tr0`.

### Baseline ngspice+pybis Cache

The frozen baseline ngspice+pybis results are stored in the baseline result folder, not in the HSPICE golden cache.

For each case, the baseline folder contains:

- The generated legacy `InputDriven` pybis subcircuit
- The ngspice deck
- The ngspice `.raw`
- The ngspice log
- An aligned waveform CSV on the HSPICE time grid

Treat this 2026-06-19 baseline folder as read-only when testing a new algorithm. New candidate runs should write to a new result folder and read these files only as references.

For `short_pulse_2ns_high`:

- Baseline raw:

  `results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/ngspice_pybis/short_pulse_2ns_high_ngspice_pybis.raw`

- Common aligned waveform CSV:

  `results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/aligned_waveforms.csv`

Use this frozen baseline when the question is:

> Did a new pybis algorithm improve over legacy `InputDriven`?

Do not silently overwrite it when preparing comparison plots. New experimental modes should write to a new result folder and read this baseline as a reference.

## Baseline Findings

### Normal Long Pulse

Case: `edge_1ps_base_50r_2pf`

Result:

- Pad active-window RMSE: `5.289 mV`
- Ku RMSE: `0.00434`
- Kd RMSE: `0.00561`
- Classification: `GOOD`

Interpretation:

- The basic HSPICE native IBIS and ngspice+legacy-pybis setup is valid for normal complete switching.
- Load and output I/V behavior are not the main weakness in this control case.

### Interrupted Short Pulse

Case: `short_pulse_2ns_high`

Result:

- Pad active-window RMSE: `361.362 mV`
- Ku RMSE: `0.28330`
- Kd RMSE: `0.23142`
- Classification: `CHECK`

Focused demo numbers:

- HSPICE pad peak: `0.825 V`
- ngspice+pybis pad peak: `1.521 V`
- HSPICE Ku peak: `0.543`
- ngspice+pybis Ku peak: `1.013`
- HSPICE Kd minimum: `-0.07199`
- ngspice+pybis Kd minimum: `-0.07241`
- Kd recovery timing: ngspice+pybis about `360 ps` later than HSPICE

Interpretation:

- HSPICE keeps the interrupted switching event partial.
- Legacy pybis lets `Ku` approach full-on, which creates a much larger pad pulse.
- This is a coefficient-state/history mismatch, not just a load mismatch and not just a small delay.

## Figures To Use As The Baseline Demo

The cleanest baseline figures are in:

`results/io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo/figures`

Main figures:

- `01_interrupted_event_timeline.png`
- `02_ku_kd_state_difference.png`
- `03_pad_consequence.png`
- `04_control_vs_interrupted.png`

The demo README is:

`results/io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo/README.md`

The demo metrics are:

`results/io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo/demo_metrics.csv`

## Standard Figure Set For New Redo Studies

Every new short-pulse redo should use the same small figure set. Keep the figures simple and do not mix unrelated diagnostics into the main overlays.

For each case, write exactly these per-case figures:

- `01_input_pad_overlay.png`: input command plus pad overlays.
- `02_ku_overlay.png`: `Ku` only.
- `03_kd_overlay.png`: `Kd` only.
- `04_value_match_diagnostics.png`: sampled `Ku/Kd`, inferred table start times, match errors, and ambiguity flag.

One study-level summary figure is also expected:

- `summary_bars.png`: pad RMSE, `Ku` RMSE, `Kd` RMSE, `Ku` peak, and `Kd` minimum.

Use these color assignments unless a study explicitly says otherwise:

- HSPICE native IBIS: blue.
- HSPICE transistor-level `io_buf.sp`: purple.
- ngspice legacy pybis: orange.
- ngspice experimental candidate: green.
- Input command: black or dark gray.

Important rule: the transistor-level `io_buf.sp` result belongs only in the pad figure. It has no IBIS `Ku/Kd`, so the coefficient figures compare HSPICE native IBIS against ngspice pybis variants only.

## How To Prepare A New ngspice+pybis Candidate Testbench

Use the HSPICE reference and legacy ngspice baseline as frozen comparisons. Only the candidate pybis subcircuit should change.

### Step 1: Choose A New Result Folder

Example:

```text
results/io_buf_<new_method>_shortpulse_redo_<date>/
```

Recommended subfolders:

```text
common/
cases/
plots/
interrupted_switching_demo/
```

### Step 2: Copy Or Generate The Candidate pybis Subcircuit

For a new experimental mode:

```powershell
py -3.14 scripts/convert_ibis_to_pybis.py `
  hspice/sparam/io_buf.ibs `
  --component "MCM Driver 1" `
  --model driver `
  --io-type Output `
  --subcircuit-type <ExperimentalModeName> `
  --corner Typical `
  --out results/io_buf_<new_method>_shortpulse_redo_<date>/common/driver_OutputInput_Typical.sub
```

The legacy baseline mode remains:

```text
InputDriven
```

Do not modify legacy `InputDriven` behavior during an experimental run.

### Step 3: Use The Same ngspice Deck Shape

The candidate ngspice deck should differ from the baseline only by which `.sub` file it includes.

Keep the same:

- PWL stimulus
- `3.3 V` supply
- Enable signal
- `50 ohm || 2 pF` load
- `.tran 0.001n <stop_time>`
- saved signals

Required saved signals:

```spice
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
```

For diagnostic models, also save the method-specific state nodes, for example:

```spice
.save V(xdrv.qpu) V(xdrv.qpd) V(xdrv.kuchg) V(xdrv.kdchg)
```

Exact diagnostic node names depend on the experimental subcircuit mode.

### Step 4: Compare Against Cached HSPICE

Do not rerun HSPICE unless the reference setup changed.

Use either:

- The central cache restored by the scripts, or
- The existing HSPICE `.tr0` in the baseline result folder.

For `short_pulse_2ns_high`, the reference waveform is:

`results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/hspice_native_ibis/short_pulse_2ns_high_hspice_native_ibis.tr0`

### Optional HSPICE Transistor-Level Pad Reference

For redo studies that need a transistor-level reference, use `models/io_buf.sp` as a pad-only HSPICE reference. Wrap it exactly as a six-pin buffer:

```spice
.include 'hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XSP in_dig oe_ref pad_sp in_sense_sp vdd_ref 0 SPICE_BUF
Rload pad_sp 0 50
Cload pad_sp 0 2p

.probe tran V(in_dig) V(pad_sp) V(in_sense_sp)
```

Use `models/hspice_ngspice.mod` with `models/io_buf.sp`, copy both files into the HSPICE run directory, and cache this reference under the family name `io_buf_transistor_sp`.

This transistor-level flow does not replace the HSPICE native IBIS coefficient reference. It answers a different question: how the transistor-level pad waveform compares under the same PWL/load setup.

### Step 5: Compare Against Cached Legacy pybis

Use the legacy baseline when judging improvement:

`results/io_buf_switching_coeff_sweep_2026-06-19/cases/short_pulse_2ns_high/ngspice_pybis/short_pulse_2ns_high_ngspice_pybis.raw`

The comparison should include:

- HSPICE native IBIS
- Legacy pybis `InputDriven`
- New candidate pybis mode

### Step 6: Report Coefficients First

For short-pulse studies, every result must report:

- Pad RMSE/max error
- Ku RMSE/max error
- Kd RMSE/max error
- Ku peak
- Kd minimum
- Kd recovery timing when meaningful
- Coefficient discontinuity at the reverse edge
- Pad peak and peak time

Pad-only improvement is not enough. A candidate can only be considered physically better if `Ku/Kd` also move closer to HSPICE.

## Acceptance Logic For The Next Redo

For the long-pulse control:

- Candidate pad RMSE should be no worse than legacy by more than `+5 mV`.
- Candidate Ku/Kd RMSE should be no worse than legacy by more than `+0.02`.
- If this fails, the candidate cannot replace legacy behavior.

For short-pulse cases:

- Candidate pad RMSE should improve versus legacy.
- Candidate Ku RMSE should improve versus legacy.
- Candidate Kd RMSE should improve versus legacy, or the failure must be explained.
- Candidate Ku peak should move toward the HSPICE peak.
- Candidate must not create coefficient jumps larger than `0.02` at retrigger.
- Candidate coefficients should stay within the sanity range `[-0.2, 1.2]`.

For `short_pulse_2ns_high`, the baseline target is:

- HSPICE Ku peak: `0.543`
- Legacy pybis Ku peak: `1.013`
- HSPICE pad peak: `0.825 V`
- Legacy pybis pad peak: `1.521 V`

For newer shorter cases, such as `short_pulse_1ns_high`, the target behavior is even more partial:

- HSPICE should produce only a small partial pulse.
- Legacy pybis tends to overdrive `Ku`.
- New methods must avoid full-on coefficient replay.

## Commands For The Baseline Study

Baseline sweep:

```powershell
py -3.14 scripts/run_io_buf_switching_coeff_sweep.py
```

This regenerates:

- `results/io_buf_switching_coeff_sweep_2026-06-19/metrics_by_case.csv`
- `results/io_buf_switching_coeff_sweep_2026-06-19/cases/*`
- `results/io_buf_switching_coeff_sweep_2026-06-19/plots/*`

With the current cache behavior, unchanged HSPICE references should be restored/reused rather than rerun.

Baseline interrupted-switching demo:

```powershell
py -3.14 scripts/make_io_buf_interrupted_switching_demo.py
```

This regenerates:

- `results/io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo/README.md`
- `results/io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo/demo_metrics.csv`
- `results/io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo/figures/*`

Clean value-matched replay redo with transistor reference:

```powershell
py -3.14 scripts/run_io_buf_value_matched_replay_redo.py
```

This writes:

- `results/io_buf_value_matched_replay_redo_2026-06-25/candidate_metrics.csv`
- `results/io_buf_value_matched_replay_redo_2026-06-25/reference_cache_manifest.csv`
- `results/io_buf_value_matched_replay_redo_2026-06-25/figures/<case>/01_input_pad_overlay.png`
- `results/io_buf_value_matched_replay_redo_2026-06-25/figures/<case>/02_ku_overlay.png`
- `results/io_buf_value_matched_replay_redo_2026-06-25/figures/<case>/03_kd_overlay.png`
- `results/io_buf_value_matched_replay_redo_2026-06-25/figures/<case>/04_value_match_diagnostics.png`
- `results/io_buf_value_matched_replay_redo_2026-06-25/figures/summary_bars.png`

## What Should Not Change During A Candidate Experiment

Keep these fixed unless the experiment explicitly says otherwise:

- IBIS file: `hspice/sparam/io_buf.ibs`
- Component/model: `MCM Driver 1` / `driver`
- HSPICE native IBIS settings
- Input PWL timing for the selected case
- Input edge rate for the short-pulse phase: `1 ps`
- Load: `50 ohm || 2 pF`
- Supply: `3.3 V`
- Enable: `3.3 V`
- Transient step/stop setup

The candidate experiment should change only:

- The pybis generated subcircuit mode
- The diagnostic nodes saved from that subcircuit
- The output folder

## Current Baseline Conclusion

The baseline is healthy for normal complete switching and unhealthy for interrupted switching.

- Long-enough pulse: ngspice+legacy-pybis matches HSPICE well.
- Short pulse: ngspice+legacy-pybis replays coefficient behavior as if too much of the transition can complete, especially in `Ku`.
- Therefore, the short-pulse problem is specifically a state/history problem in the pybis input-driven coefficient model.

This document should be used as the fixed baseline reference before rerunning one of the experimental short-pulse algorithms.
