# Xyce Repeat Results

Date: `2026-05-09`

## Scope

Repeated the working ngspice plan items in Xyce where practical:

- transistor-level reference buffer + new 50-ohm RLGC channel
- pybis2spice converted buffer + compact validation load
- pybis2spice converted buffer + new 50-ohm RLGC channel

Xyce used:

`C:\Program Files\XyceNF_7.10\bin\Xyce.exe`

Version:

`XyceNF Release 7.10.0`

## New Folders

- `xyce_refspice/`
- `xyce_pybis/`

## Xyce Syntax Porting

For pybis2spice:

- Converted ngspice behavioral source syntax from `V = expr` / `I = expr` to Xyce `V={expr}` / `I={expr}`.
- Converted expression `pwl(...)` calls to Xyce `table(...)`.
- Replaced the channel shunt behavioral conductances with equivalent `1meg` shunt resistors in `channel_xyce.sp`.
- Replaced ngspice `.save` output with Xyce `.print tran format=csv`.

For refspice:

- Used the same `hspice_ngspice.mod` and `io_buf.sp`.
- Xyce accepted the BSIM3 models as `M level 9 (BSIM3)`.
- Xyce warned that `XL` and `XW` model parameters were ignored.

## Results

| Case | Deck | Outcome |
|---|---|---|
| Refspice pulse, 20 ns | `xyce_refspice/tb_refspice_pulse_new50ohm_xyce.cir` | PASS |
| Refspice PRBS7, 1000 ns | `xyce_refspice/tb_refspice_prbs7_new50ohm_xyce.cir` | PASS |
| pybis compact pulse, 20 ns | `xyce_pybis/tb_validation_pulse_xyce_pybis.cir` | FAIL/STALL |
| pybis PRBS7 new50ohm, no `uic` | `xyce_pybis/tb_pybis_prbs7_new50ohm_xyce.cir` | FAIL at DCOP |
| pybis PRBS7 new50ohm, `uic`, 100 ns diagnostic | `xyce_pybis/tb_pybis_prbs7_new50ohm_xyce_uic_100n.cir` | FAIL/STALL at first PRBS rising edge |
| pybis delayed rise, Rload, relaxed gates | `xyce_pybis/tb_test_rise_late_xyce_uic_relaxed.cir` | PASS |
| pybis fast rise/fall, Rload, relaxed gates | `xyce_pybis/tb_test_rfr_xyce_uic_relaxed.cir` | PASS |
| pybis slow rise/fall, Rload, relaxed gates | `xyce_pybis/tb_test_rfall_late_xyce_uic_relaxed.cir` | PASS |
| pybis 200 ps pulse, ideal T-line, relaxed gates | `xyce_pybis/tb_validation_pulse_200p_tline_xyce_relaxed.cir` | PASS |
| pybis 200 ps rise, new 50-ohm RLGC channel, relaxed gates | `xyce_pybis/tb_channel_rise_200p_xyce_relaxed.cir` | PASS |
| pybis 200 ps rise/fall, new 50-ohm RLGC channel, relaxed gates | `xyce_pybis/tb_channel_rfr_200p_xyce_relaxed.cir` | PASS |

## Refspice PASS Details

### Pulse

Output:

`xyce_refspice/tb_refspice_pulse_new50ohm_xyce.cir.csv`

- rows: `1167`
- final time: `20 ns`
- elapsed runtime: `0.163 s`
- failed linear solves: `0`
- nonlinear convergence failures: `0`
- `V(n10b)` range: `-0.0666 V` to `1.1868 V`

### PRBS7

Output:

`xyce_refspice/tb_refspice_prbs7_new50ohm_xyce.cir.csv`

- rows: `22275`
- final time: `1000 ns`
- elapsed runtime: `2.46 s`
- successful transient steps: `22274`
- failed transient steps attempted: `348`
- failed linear solves: `0`
- nonlinear convergence failures: `0`
- `V(n10b)` range: `-0.0248 V` to `1.5177 V`

## pybis FAIL Details

### Compact Pulse

Output:

`xyce_pybis/tb_validation_pulse_xyce_pybis.cir.csv`

The deck parses and starts after Xyce syntax conversion, but stalls near the
first input transition.

- requested stop time: `20 ns`
- interrupted after: `~120 s`
- final written time: `1.092 ns`
- rows written: `207378`
- file size: `~22 MB`

### PRBS7, no `uic`

Log:

`xyce_pybis/tb_pybis_prbs7_new50ohm_xyce.log`

The no-`uic` version fails before transient stepping:

- DC operating point failed
- failed linear solves: `25`
- nonlinear convergence failures: `1`
- no CSV waveform produced

### PRBS7, `uic` 100 ns Diagnostic

Output:

`xyce_pybis/tb_pybis_prbs7_new50ohm_xyce_uic_100n.cir.csv`

The `uic` variant skips DCOP and advances through the initial low run, then
stalls at the first PRBS rising edge.

- requested stop time: `100 ns`
- interrupted after: `60 s`
- final written time: `35.174 ns`
- rows written: `329035`
- file size: `~39.8 MB`
- `V(in_dig)` had begun rising from `0 V` toward `3.3 V`

## Interpretation

Xyce successfully repeats the transistor-level reference experiment with the
same new 50-ohm RLGC channel. That gives a clean Xyce-vs-ngspice simulator
portability baseline for the MOS-level buffer.

Xyce does not currently repeat the pybis2spice behavioral-model pass. The
converted model can be made syntactically valid in Xyce, but the B-source /
table / timing-control network is numerically fragile:

- without `uic`, the PRBS deck fails DCOP
- with `uic`, both compact pulse and PRBS diagnostics hit timestep traps near
  the first input transition

This supports the plan's risk note that the pybis waveform-derived B-source
implementation is simulator-sensitive and not just a generic SPICE netlist.

## pybis Simpler-Case Progress

After the initial pybis failures, simpler Rload-only cases were tested before
returning to any PRBS stream.

### Original Xyce-converted pybis model

The direct Xyce syntax port of `driver_OutputInput_Typical.sub` still fails
simple Rload decks without `uic`:

- `tb_test_rise_xyce.cir`
- `tb_test_rfr_xyce.cir`
- `tb_test_rise_fall_xyce.cir`

All three fail DCOP with a singular matrix.

With `uic`, the immediate-rise case reaches 20 ns but is not physically useful:
the input edge starts at `t=0`, the internal `NX`/`N6` timing path freezes, and
`V(pad)` remains essentially zero. Delayed-edge and rise/fall cases still stall
near the first threshold crossing.

### Relaxed Xyce pybis model

A Xyce-only copy was created:

`xyce_pybis/driver_OutputInput_Typical_xyce_relaxed.sub`

Change:

- all sharp `tanh(200*...)` gates were relaxed to `tanh(20*...)`

This is a numerical-continuation experiment, not yet an accuracy-approved model.
It widens the threshold smoothing enough for Xyce Newton iterations to progress.

Passing simple cases:

| Deck | Load | Edge | Final time | Notes |
|---|---|---|---|---|
| `tb_test_rise_late_xyce_uic_relaxed.cir` | 50 ohm Rload | delayed 200 ps rise | `20 ns` | `V(pad)` max `1.494 V` |
| `tb_test_rfr_xyce_uic_relaxed.cir` | 50 ohm Rload | 200 ps rise/fall | `20 ns` | `V(pad)` max `1.557 V` |
| `tb_test_rfall_late_xyce_uic_relaxed.cir` | 50 ohm Rload | delayed 2 ns rise/fall | `20 ns` | `V(pad)` max `1.557 V` |
| `tb_validation_pulse_200p_tline_xyce_relaxed.cir` | ideal 50 ohm T-line + 50 ohm load | 200 ps pulse | `20 ns` | `V(ntst)` max `1.557 V`; no failed linear solves |
| `tb_channel_rise_200p_xyce_relaxed.cir` | new 50-ohm RLGC channel | delayed 200 ps rise | `30 ns` | `V(n10b)` max `1.490 V`; no failed linear solves |
| `tb_channel_rfr_200p_xyce_relaxed.cir` | new 50-ohm RLGC channel | delayed 200 ps rise/fall | `30 ns` | `V(n10b)` max `1.559 V`; no failed linear solves |
| `tb_channel_twopulse_200p_xyce_relaxed.cir` | new 50-ohm RLGC channel | two isolated 200 ps pulses | `20 ns` | `V(n10b)` range `-0.081 V` to `1.786 V`; no failed linear solves |

Important boundary:

- relaxed gates + `uic` are currently required for these simple pybis Xyce passes
- no-`uic` relaxed Rload decks still fail DCOP
- the original compact validation deck uses a 5 ps edge and still stalls, even
  with relaxed gates
- a 40 ns repeated pulse train with `tanh(20*...)` was interrupted after `90 s`
  at `26.671 ns`, so repeated switching is still the main boundary for that
  model

Additional diagnostic:

`xyce_pybis/driver_OutputInput_Typical_xyce_relaxed10.sub` was created by
relaxing the same gates further to `tanh(10*...)`. This is less faithful than
the `tanh20` experiment, but it completes the 40 ns repeated pulse-train case:

| Deck | Load | Edge | Final time | Notes |
|---|---|---|---|---|
| `tb_channel_pulsetrain_200p_xyce_relaxed10.cir` | new 50-ohm RLGC channel | repeated 200 ps pulses | `40 ns` | `V(n10b)` range `0 V` to `1.718 V`; runtime `3.6 s` |

### Pulse-train smoothing sweep

The repeated pulse train was swept across several `tanh(k*...)` gate factors to
find the smallest tested relaxation that completes. Results are in
`plots/xyce_pybis/xyce_pybis_pulsetrain_smoothing_sweep.csv`.

| Gate factor | Result | Final time | Notes |
|---:|---|---:|---|
| `20` | timeout | `26.671 ns` | original relaxed model |
| `18` | timeout | `33.911 ns` | progressed farther but still trapped |
| `17` | timeout | `9.050 ns` | non-monotonic solver trap |
| `16` | timeout | `3.890 ns` | trapped early |
| `15` | pass | `40 ns` | first passing bracket point; runtime `4.35 s` |
| `12` | pass | `40 ns` | runtime `3.78 s` |
| `10` | pass | `40 ns` | runtime `3.61 s` |

`tanh15` is therefore the current best practical Xyce continuation point for
repeated switching: it is less smoothed than `tanh10`, but still completes this
deterministic pulse-train case.

### Deterministic bit pattern

A non-PRBS bit-pattern case was added:

`xyce_pybis/tb_channel_bitpattern_200p_xyce_relaxed15.cir`

Pattern: `1 0 1 1 0 0 1 0`, 5 ns UI, 200 ps transitions, new 50-ohm RLGC
channel, `tanh15` pybis model.

Result:

- completed to `45 ns`
- runtime: `4.2 s`
- `V(n10b)` range: `0 V` to `1.573 V`
- `V(pad)` range: `0 V` to `1.577 V`

Recommended next step:

Use `driver_OutputInput_Typical_xyce_relaxed.sub` only for Xyce numerical
experiments, and continue with simple deterministic inputs before PRBS:

1. compare `tanh20` and `tanh10` against ngspice pybis for the single-edge,
   rise/fall, two-pulse, and pulse-train cases
2. tune the smallest smoothing relaxation that lets Xyce complete repeated
   switching without distorting the waveform too much
3. then try a short deterministic bit pattern with only a few transitions
4. only after that return to a short PRBS window

## Review Plots

Generated:

- `plots/xyce_pybis/xyce_pybis_relaxed_rload_cases.png`
- `plots/xyce_pybis/xyce_vs_ngspice_pybis_rload_overlay.png`
- `plots/xyce_pybis/xyce_vs_ngspice_pybis_rload_metrics.csv`
- `plots/xyce_pybis/xyce_pybis_relaxed_channel_cases.png`
- `plots/xyce_pybis/xyce_pybis_relaxed_pulsetrain_timeout.png`
- `plots/xyce_pybis/xyce_pybis_relaxed_twopulse.png`
- `plots/xyce_pybis/xyce_pybis_relaxed10_pulsetrain.png`
- `plots/xyce_pybis/xyce_pybis_pulsetrain_smoothing_sweep.png`
- `plots/xyce_pybis/xyce_pybis_pulsetrain_smoothing_sweep.csv`
- `plots/xyce_pybis/xyce_pybis_relaxed15_bitpattern.png`
- `plots/xyce_pybis/xyce_pybis_relaxed_metrics.csv`

The ngspice overlay is meaningful for the first two Rload cases:

| Case | ngspice pad max | Xyce relaxed pad max | Pad RMSE |
|---|---:|---:|---:|
| Single delayed rise | `1.539 V` | `1.494 V` | `39.6 mV` |
| Fast rise/fall | `1.556 V` | `1.557 V` | `12.0 mV` |

The stored `ngspice_pybis/tb_test_rfall_late.raw` only reaches `2.625 ns`, so
it is plotted with an early-stop caveat rather than treated as a full golden
comparison. A fresh batch rerun of `ngspice_pybis/tb_test_rfall_late.sp` was
killed after `120 s` without producing a completed replacement raw file.

The pulse-train diagnostic is the current next boundary:

- deck: `xyce_pybis/tb_channel_pulsetrain_200p_xyce_relaxed.cir`
- requested stop time: `40 ns`
- interrupted after: `90 s`
- final written time: `26.671 ns`
- rows written: `211683`
- `V(n10b)` range: `-0.0415 V` to `1.7045 V`

Interpretation: `tanh20` relaxed pybis is now viable through isolated single
transitions, one rise/fall pair, and two isolated pulses with the new RLGC
channel. Repeated switching still causes excessive timestep work at `tanh20`,
but the `tanh10` diagnostic shows that additional smoothing can make the same
pulse train complete. The next useful work is accuracy comparison against the
ngspice pybis waveforms, not jumping to PRBS yet.

## 2026-05-10 Xyce Time-Integration Update

The Xyce user guide was checked for transient convergence controls. Two items
were directly useful:

- Gear/Backward-Euler integration can help convergence when Trap struggles.
- `.OPTIONS TIMEINT ERROPTION=1` switches to nonlinear-iteration-based timestep
  control; the guide recommends pairing it with `DELMAX`.

The most useful Xyce option block so far is:

```spice
.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
```

This is Backward-Euler plus non-LTE timestep control.

### Direct pybis model

The unrelaxed direct Xyce pybis model is improved but still not fully usable:

| Deck | Model | Result | Notes |
|---|---|---|---|
| `tb_test_rise_late_xyce_uic_timeint_nlte_be.cir` | direct `tanh200` | pass to `20 ns` | `V(pad)` max `1.540 V`; close to ngspice delayed-rise max |
| `tb_test_rfr_xyce_uic_timeint_nlte_be.cir` | direct `tanh200` | pass to `20 ns` | `V(pad)` max `1.558 V` |
| `tb_channel_pulsetrain_200p_xyce_direct_timeint_nlte_be.cir` | direct `tanh200` | timeout | reached `33.936 ns` of requested `40 ns` |
| `tb_channel_bitpattern_200p_xyce_direct_timeint_nlte_be.cir` | direct `tanh200` | timeout | reached `11.695 ns` of requested `45 ns` |

Conclusion: Xyce timestep options rescue simple direct-model edges, but not
repeated direct-model switching.

### `tanh20` relaxed model with Xyce timestep controls

The `tanh20` relaxed model no longer needs to fall back to `tanh15` for the
short repeated pulse train if Backward-Euler/non-LTE timestep control is used:

| Deck | Result | Notes |
|---|---|---|
| `tb_channel_pulsetrain_200p_xyce_relaxed_timeint_nlte_be.cir` | pass to `40 ns` | runtime about `8 s`; `V(n10b)` max `1.691 V` |
| `tb_channel_bitpattern_200p_xyce_relaxed_timeint_nlte_be.cir` | pass to `45 ns` | `V(n10b)` max `1.558 V` |
| `tb_pybis_prbs7_new50ohm_xyce_relaxed_timeint_nlte_be_100n.cir` | pass to `100 ns` | runtime `5.46 s`; `V(n10b)` max `1.557 V` |
| `tb_pybis_prbs7_new50ohm_xyce_relaxed_timeint_nlte_be_1000n.cir` | timeout | reached `110.070 ns` before `240 s` timeout |

Conclusion: `tanh20` plus BE/non-LTE is now a good deterministic setup and a
short-PRBS setup, but it still does not complete full PRBS7.

### `tanh15` relaxed model with Xyce timestep controls

`tanh15` plus the same Backward-Euler/non-LTE timestep control is now the first
Xyce pybis setup that completes the full accepted PRBS window:

| Deck | Result | Notes |
|---|---|---|
| `tb_pybis_prbs7_new50ohm_xyce_relaxed15_timeint_nlte_be_200n.cir` | pass to `200 ns` | runtime `0.93 s`; `V(n10b)` max `1.539 V` |
| `tb_pybis_prbs7_new50ohm_xyce_relaxed15_timeint_nlte_be_1000n.cir` | pass to `1000 ns` | runtime `4.44 s`; `V(n10b)` max `1.539 V` |

The `tanh10` PRBS 200 ns diagnostic unexpectedly timed out at `125.259 ns`.
The smoothing/runtime behavior remains non-monotonic, so `tanh15` is currently
the best practical setting rather than simply "more smoothing is better."

### New ngspice comparison baselines

Two matching ngspice deterministic baselines were added and run:

- `ngspice_pybis/tb_channel_pulsetrain_200p_ngspice_pybis.sp`
- `ngspice_pybis/tb_channel_bitpattern_200p_ngspice_pybis.sp`

Both completed quickly and produced raw files for direct overlays.

### New review plots

Generated:

- `plots/xyce_pybis/xyce_pybis_timeint_option_results.png`
- `plots/xyce_pybis/xyce_pybis_timeint_option_results.csv`
- `plots/xyce_pybis/xyce_vs_ngspice_pybis_channel_deterministic.png`
- `plots/xyce_pybis/xyce_vs_ngspice_pybis_channel_deterministic_metrics.csv`
- `plots/xyce_pybis/xyce_vs_ngspice_pybis_prbs1000_overlay.png`
- `plots/xyce_pybis/xyce_vs_ngspice_pybis_prbs1000_metrics.csv`

PRBS7 1000 ns comparison against ngspice pybis:

| Metric | ngspice pybis | Xyce `tanh15` BE/non-LTE | Delta |
|---|---:|---:|---:|
| `V(n10b)` min | `-0.008 V` | `0.000 V` | `+0.008 V` |
| `V(n10b)` max | `1.540 V` | `1.539 V` | `-0.001 V` |
| `V(n10b)` RMSE | -- | -- | `75.1 mV` |
| `V(pad)` max | `1.564 V` | `1.572 V` | `+0.008 V` |

Conclusion: Xyce pybis can now reproduce the accepted ngspice PRBS duration
with a relaxed `tanh15` model and Xyce-specific timestep controls. The amplitude
envelope is close, but the RMSE indicates waveform-level differences still need
eye/transition metric review before calling it accuracy-equivalent.

## 2026-05-10 Minimal-Modification Sweep

After the first full-PRBS success with `tanh15`, the next question was whether
Xyce could move closer to the direct pybis model. The direct pybis model uses
sharp `tanh(200*...)` gates, so larger `tanh(k*...)` factors are less modified.

The same Backward-Euler/non-LTE Xyce options were used:

```spice
.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
```

### Deterministic pulse-train sweep

For the 40 ns repeated 200 ps pulse-train case, the new high-factor sweep found:

| Model | Result | Final time |
|---|---|---:|
| direct `tanh200` | timeout | `33.936 ns` |
| `tanh100` | timeout | `36.807 ns` |
| `tanh98` | timeout | `28.966 ns` |
| `tanh95` | timeout | `28.966 ns` |
| `tanh94` | timeout | `28.966 ns` |
| `tanh92` | pass | `40 ns` |
| `tanh90` | pass | `40 ns` |
| `tanh75` | pass | `40 ns` |
| `tanh60` | timeout | `31.765 ns` |
| `tanh50` | pass | `40 ns` |
| `tanh30` | timeout | `9.000 ns` |
| `tanh20` | pass | `40 ns` |

The pass/fail behavior is non-monotonic. Still, `tanh92` is the best
minimal-modification deterministic pass found so far. It is much closer to the
direct `tanh200` pybis model than the earlier `tanh15` full-PRBS setup.

New artifacts:

- `plots/xyce_pybis/xyce_pybis_minimal_relaxation_sweep.png`
- `plots/xyce_pybis/xyce_pybis_minimal_relaxation_sweep.csv`

### PRBS minimal-modification sweep

The high-factor deterministic passes do not automatically translate to PRBS
passes:

| Model/window | Result | Final time | Notes |
|---|---|---:|---|
| `tanh15`, PRBS 1000 ns | pass | `1000 ns` | current practical full-run setup |
| `tanh20`, PRBS 1000 ns | timeout | `110.070 ns` | short PRBS works, full does not |
| `tanh50`, PRBS 200 ns | pass | `200 ns` | best short-PRBS minimal-modification pass |
| `tanh50`, PRBS 1000 ns, 10 ps output interval | timeout | `205.270 ns` | output throttling reduced file size, not solver stall |
| `tanh75`, PRBS 200 ns | timeout | `105.396 ns` | fails before 200 ns |
| `tanh90`, PRBS 200 ns | timeout | `95.316 ns` | fails before 200 ns |
| `tanh10`, PRBS 200 ns | timeout | `125.259 ns` | more smoothing is not always better |

`tanh50` is therefore the best short-PRBS minimal-modification candidate so far,
but `tanh15` remains the only model that completes the accepted 1000 ns PRBS7
window.

New artifacts:

- `plots/xyce_pybis/xyce_pybis_prbs_relaxation_candidates.png`
- `plots/xyce_pybis/xyce_pybis_prbs_relaxation_candidates.csv`

### Output throttling

The Xyce user guide's `.OPTIONS OUTPUT INITIAL_INTERVAL=<interval>` was tested
on the `tanh50` PRBS run:

```spice
.options output initial_interval=10p
```

For the `tanh50` 200 ns PRBS run, this reduced the CSV from about `58.8 MB` to
about `2.7 MB` and runtime from about `28.1 s` to `21.7 s`. It did not solve
the 1000 ns stall; the throttled full run still stopped at `205.270 ns`.

Current hierarchy:

1. Direct unrelaxed pybis: simple Rload edges only.
2. `tanh92`: best deterministic repeated-switching minimal modification.
3. `tanh50`: best short-PRBS minimal modification.
4. `tanh15`: only full 1000 ns PRBS pass so far.

## 2026-05-10 SPISim-Style T-Line Validation Matrix

The SPISim reference examples suggested adding a small validation gate before
the RLGC channel and PRBS cases. A repeatable runner was added:

```powershell
python .\scripts\run_spisim_style_pybis_validation.py --timeout 30
```

The runner generates ngspice and Xyce benches using:

- one pybis driver
- ideal `Z0=50`, `Td=30p` transmission line
- 50 ohm far-end termination
- probes at input, pad, far-end `ntst`, and `Ku/Kd`

Generated review artifacts:

- `plots/xyce_pybis/xyce_pybis_spisim_tline_validation_overlay.png`
- `plots/xyce_pybis/xyce_pybis_spisim_tline_validation_matrix.png`
- `plots/xyce_pybis/xyce_pybis_spisim_tline_validation_metrics.csv`

### ngspice baselines

After keeping the ngspice decks close to SPISim style, all four baselines pass:

| Stimulus | Result | Final time | `V(ntst)` max |
|---|---|---:|---:|
| SPISim pulse, 5 ps edges | pass | `20 ns` | `1.556 V` |
| practical pulse, 200 ps edges | pass | `20 ns` | `1.556 V` |
| rise-fall-rise, 5 ps edges | pass | `26 ns` | `1.557 V` |
| rise-fall-rise, 200 ps edges | pass | `26 ns` | `1.557 V` |

This gives a clean small-bench ngspice baseline for Xyce candidate testing.

### Xyce findings

For the practical 200 ps single-pulse T-line validation:

| Xyce model | Result | Final time | `V(ntst)` RMSE vs ngspice |
|---|---|---:|---:|
| direct `tanh200` | timeout | `12.26 ns` | `2.9 mV` over partial window |
| `tanh92` | pass | `20 ns` | `3.7 mV` |
| `tanh50` | pass | `20 ns` | `5.9 mV` |
| `tanh20` | pass | `20 ns` | `22.1 mV` |
| `tanh15` | pass | `20 ns` | `46.8 mV` |

For practical 200 ps rise-fall-rise, no Xyce variant completed even with a
longer 90 s rerun, but the partial data is informative:

| Xyce model | Final time | `V(ntst)` RMSE vs ngspice over partial window |
|---|---:|---:|
| direct `tanh200` | `9.37 ns` | `5.0 mV` |
| `tanh92` | `21.90 ns` | `3.1 mV` |
| `tanh50` | `21.89 ns` | `3.0 mV` |
| `tanh20` | `21.91 ns` | `28.4 mV` |
| `tanh15` | `22.48 ns` | `74.4 mV` |

The 5 ps SPISim-edge Xyce cases are severe stress tests; none completed. They
are useful for exposing stiffness, but they should not be the acceptance gate
for the Xyce pybis path because the project stimulus/channel work uses 200 ps
edges.

### Setup changes learned

- Keep ngspice validation decks close to SPISim: normal OP, minimal probes,
  ideal 30 ps/50 ohm line, then compare `pad` and `ntst`.
- Keep Xyce validation decks explicit: `uic`, internal pybis `.ic` values,
  Backward-Euler/non-LTE options, and output throttling.
- Use `pulse200p` as the first official Xyce candidate gate.
- Use `rfr200p` as the repeated-transition stress gate before RLGC/PRBS.
- Do not jump from a single edge directly to PRBS; the ideal T-line RFR case
  already shows the repeated-transition stall around `22 ns`.

## 2026-05-10 Xyce pybis Root Cause

A targeted root-cause runner was added:

```powershell
python .\scripts\probe_xyce_pybis_root_cause.py --timeout 30
```

New artifacts:

- `plots/xyce_pybis/xyce_pybis_rootcause_experiments.csv`
- `plots/xyce_pybis/xyce_pybis_rootcause_experiments.png`
- `plots/xyce_pybis/xyce_pybis_rootcause_coeff_tail.png`

The failing reference case is the practical 200 ps rise-fall-rise ideal-T-line
bench using the `tanh92` model.

### Isolation results

| Experiment | Result | Final time | Key state |
|---|---|---:|---|
| Original T-line, stop at `21 ns` | pass | `21.000 ns` | `NX=3.91 ns` |
| Original T-line, stop at `22 ns` | timeout | `21.890 ns` | `NX=4.80 ns` |
| Same T-line, minimal print list | timeout | `21.890 ns` | output volume not causal |
| Same T-line, `DELMAX=100p` | timeout | `21.890 ns` | max-step limit not causal |
| Rload instead of T-line | timeout later | `25.260 ns` | separate final-fall stiffness |
| Cap internal `NX` at `4.0 ns` | pass | `26.000 ns` | full bench completes |
| Cap internal `NX` at `4.1 ns` | pass | `26.000 ns` | full bench completes |
| Cap internal `NX` at `4.2 ns` | pass | `26.000 ns` | full bench completes |
| Cap internal `NX` at `4.3 ns` | timeout | `25.410 ns` | not robust |
| Cap internal `NX` at `4.5 ns` | timeout | `21.680 ns` | not robust |
| Keep `NX` normal, cap only `KUR` at `4.2 ns` | timeout | `21.960 ns` | not enough |
| Keep `NX` normal, cap only `KDR` at `4.2 ns` | timeout | `21.930 ns` | not enough |
| Keep `NX` normal, cap both `KUR` and `KDR` at `4.2 ns` | pass | `26.000 ns` | full bench completes |

The passing `KUR/KDR` cap case has about `25.7 mV` full-window `V(ntst)` RMSE
against the ngspice baseline. This is good enough as a diagnostic, but it is not
yet an accuracy-approved model change.

### Root cause

The main Xyce ideal-T-line RFR stall is caused by the late rising waveform
coefficient-table tail. In this model, the internal elapsed-time node `NX`
continues to sweep the rising `KUR/KDR` coefficient tables for several
nanoseconds after the visible input transition. Xyce handles the early part of
that sweep, but around `NX=4.2-4.8 ns` the coupled B-source/table/T-line system
becomes pathologically slow. Ngspice completes the same SPISim-style bench.

This is not primarily:

- CSV output volume: minimal printing stalls at the same time
- external ideal-T-line load alone: capping `KUR/KDR` fixes the T-line case
- `DELMAX=20p`: loosening to `100p` stalls at the same time
- the requested stop time: stopping before the bad `NX` region passes quickly

There is also a separate falling-edge stiffness visible in the Rload cross-check
near `25.26 ns`, but that is not the cause of the earlier `21.89 ns` T-line
stall.

Practical next direction: test a controlled coefficient-tail conditioning
strategy, such as freezing or smoothing the rising `KUR/KDR` tables after about
`4.2 ns`, then compare against ngspice on the small T-line, RLGC deterministic,
and PRBS cases before accepting it.

## 2026-05-10 Tail-Fix Direction Experiments

Added:

```powershell
python .\scripts\test_xyce_pybis_tail_fixes.py
python .\scripts\summarize_xyce_tailfix_results.py
```

New review artifacts:

- `plots/xyce_pybis/xyce_pybis_tailfix_recommendation_summary.csv`
- `plots/xyce_pybis/xyce_pybis_tailfix_recommendation_matrix.png`
- `plots/xyce_pybis/xyce_pybis_tailfix_prbs1000_edge15_vs_tanh15.png`
- `plots/xyce_pybis/xyce_pybis_tailfix_rfr_key_candidates.png`

### Coefficient-tail candidates

The first fix direction kept the `tanh92` control logic and changed only the
rising waveform coefficient tail:

| Candidate | Pulse200p T-line | RFR200p T-line | Channel pulse | Channel bit pattern | PRBS |
|---|---:|---:|---:|---:|---|
| baseline `tanh92` | pass, `4.1 mV` | timeout at `21.89 ns` | pass, `27.4 mV` | pass, `11.0 mV` | not robust |
| `hard4p2` | pass, `4.1 mV` | pass, `26.3 mV` | pass, `27.4 mV` | pass, `19.8 mV` | timeout at `70.2 ns` |
| `flat4p2` | pass, `4.1 mV` | pass, `26.3 mV` | pass, `27.4 mV` | pass, `19.8 mV` | not taken forward |

Conclusion: conditioning both rising `KUR/KDR` lookup tails at `4.2 ns` fixes
the ideal-T-line RFR root cause, and flattening the table tail is the cleaner
form because it changes table data instead of adding a hard expression cap.
This does not solve PRBS by itself.

### Edge/latch versus selector controls

The PRBS stall is not the same as the RFR tail stall. With `hard4p2`, the
200 ns PRBS run times out at `70.2 ns` with `NX` near `0.11 ns`, i.e. early in
a new edge, not in the late rising tail.

Targeted hybrids showed:

| Candidate | What changed | PRBS result |
|---|---|---|
| `sel50_flat4p2` | final `Ku/Kd` selector `B24-B29` to `tanh50` | timeout at `70.2 ns` |
| `edge50_flat4p2` | edge/latch `B10-B18` to `tanh50` | pass 200 ns, `32.0 mV` |
| `edge52_flat4p2` | edge/latch `B10-B18` to `tanh52` | timeout at `155.11 ns` |
| `edge55_flat4p2` | edge/latch `B10-B18` to `tanh55` | timeout at `125.19 ns` |
| `edge60_flat4p2` | edge/latch `B10-B18` to `tanh60` | timeout at `105.17 ns` |
| `edge75_flat4p2` | edge/latch `B10-B18` to `tanh75` | timeout at `105.39 ns` |

Conclusion: the short-PRBS failure is driven by the edge detector/latch block,
not by the final `Ku/Kd` selector. `edge50_flat4p2` is the best 200 ns PRBS
compromise found so far, but it still times out at `205.27 ns` on the 1000 ns
PRBS run.

### Full PRBS profile

For full 1000 ns PRBS, a deeper edge/latch relaxation was needed:

| Candidate | T-line pulse200p | T-line RFR200p | Channel pulse | Channel bit pattern | PRBS1000 |
|---|---:|---:|---:|---:|---:|
| old all-`tanh15` | pass, `50.4 mV` | timeout at `22.47 ns` | pass, `56.2 mV` | pass, `64.9 mV` | pass, `75.1 mV` |
| `edge15_flat4p2` | timeout at `14.95 ns` | pass, `26.3 mV` | pass, `29.7 mV` | pass, `19.7 mV` | pass, `26.6 mV` |

`edge15_flat4p2` keeps the final selector block at `tanh92`, changes only the
edge/latch block `B10-B18` to `tanh15`, and flattens the rising `KUR/KDR`
table tails after `4.2 ns`. It is substantially closer to ngspice than the
older all-`tanh15` fallback on the channel and PRBS comparisons.

Important caveat: no single candidate tested so far passes every small T-line
gate plus full PRBS. The practical profiles are currently:

- T-line/short PRBS compromise: `edge50_flat4p2`
- long PRBS/channel profile: `edge15_flat4p2`

## 2026-05-10 PRBS + Ideal T-Line Stress Case

Added:

```powershell
python .\scripts\run_xyce_pybis_prbs_tline.py
```

This runner fills the missing matrix cell: PRBS7 stimulus into the pybis driver
with an ideal 30 ps, 50-ohm T-line and a 50-ohm far-end load.

### ngspice status

ngspice direct pybis is stable for short windows but not for the longer
PRBS/T-line stress window:

| Stop time | Result | Final time | Wall time |
|---:|---|---:|---:|
| `100 ns` | pass | `100.00 ns` | `2.11 s` |
| `120 ns` | pass | `120.00 ns` | `3.03 s` |
| `130 ns` | timeout | `125.56 ns` | `90.01 s` |
| `200 ns` | timeout | `125.58 ns` | `180 s` |

This means ngspice is stable on the accepted direct-pybis RLGC-channel PRBS1000
baseline, but not automatically stable on every direct-pybis PRBS/load
combination. The ideal lossless T-line PRBS case exposes a separate ngspice
slowdown near `125.6 ns`.

### Xyce status at 100 ns

No tested Xyce profile completed `100 ns` on the ideal-T-line PRBS stress case:

| Xyce profile | Final time | Notes |
|---|---:|---|
| `tanh92` | `65.25 ns` | close waveform before stall, low partial-window RMSE |
| `flat4p2` | `65.44 ns` | tail fix alone does not solve PRBS/T-line |
| `edge15_flat4p2` | `45.08 ns` | long-RLGC-PRBS winner is poor here |
| `edge20_flat4p2` | `65.38 ns` | no improvement |
| `edge30_flat4p2` | `65.59 ns` | no improvement |
| `edge50_flat4p2` | `95.44 ns` | best progress so far |
| `edge55_flat4p2` | `70.20 ns` | worse than edge50 |
| `edge60_flat4p2` | `95.44 ns` | same practical boundary as edge50 |
| `edge75_flat4p2` | `65.30 ns` | no improvement |
| `B18` only to `tanh15` + tail flat | `65.43 ns` | no improvement |
| `B17/B18` to `tanh15` + tail flat | `65.57 ns` | no improvement |
| `B15/B17/B18` to `tanh15` + tail flat | `65.40 ns` | no improvement |
| `B10/B11` to `tanh15` + tail flat | `35.40 ns` | worse |

Interpretation: the PRBS + ideal T-line case is not just a simpler version of
PRBS + RLGC. It is a harsher numerical stress case for both simulators. For
Xyce, the known tail fix and edge/latch smoothing are not sufficient. For
ngspice, direct pybis also develops a long-run slowdown in this topology.

Artifacts:

- `plots/xyce_pybis/xyce_pybis_prbs_tline_100n_metrics.csv`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_100n_overlay.png`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_120n_metrics.csv`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_130n_metrics.csv`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_200n_metrics.csv`

## 2026-05-10 PRBS/T-Line Source-Damping Sweep

The PRBS/T-line runner was extended with `--riso`, a driver-to-line series
resistance between the pybis pad and the ideal T-line.

### ngspice direct pybis

| `RISO` | `130 ns` result | `200 ns` result |
|---:|---|---|
| `0 ohm` | timeout at `125.56 ns` | timeout at `125.58 ns` |
| `0.1 ohm` | timeout at `125.55 ns` | not run |
| `0.5 ohm` | timeout at `110.31 ns` | not run |
| `1.0 ohm` | timeout at `125.60 ns` | not run |
| `1.25 ohm` | timeout at `125.60 ns` | not run |
| `1.5 ohm` | timeout at `105.47 ns` | not run |
| `1.75 ohm` | pass in about `5.1 s` | pass to `200 ns` |
| `2.0 ohm` | pass in about `4.9 s` | pass to `200 ns` |
| `5.0 ohm` | not run | timeout at `109.99 ns` |

This confirms that the ngspice PRBS/T-line instability is tied strongly to the
ideal lossless line/load topology. Damping helps, but the effect is
non-monotonic: too little does not help, and too much (`5 ohm`) creates a new
slow case.

### Xyce

For Xyce, the same source damping helps but does not solve the full PRBS/T-line
case:

| Xyce profile | `RISO` | Stop | Result |
|---|---:|---:|---|
| `edge50_flat4p2` | `0 ohm` | `100 ns` | timeout at `95.44 ns` |
| `edge50_flat4p2` | `2.0 ohm` | `100 ns` | pass in `8.19 s`, RMSE `45.2 mV` |
| `edge50_flat4p2` | `1.75 ohm` | `200 ns` | timeout at `67.69 ns` |
| `edge50_flat4p2` | `2.0 ohm` | `200 ns` | timeout at `106.06 ns` |

Interpretation: source damping turns the ideal PRBS/T-line case from "no Xyce
profile reaches 100 ns" into "the short/T-line profile reaches 100 ns", but it
does not yet make Xyce complete `200 ns`.

Artifacts:

- `plots/xyce_pybis/xyce_pybis_prbs_tline_damping_summary.csv`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_damping_summary.png`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_100n_riso2_metrics.csv`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_100n_riso2_overlay.png`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_200n_riso2_metrics.csv`
- `plots/xyce_pybis/xyce_pybis_prbs_tline_200n_riso2_overlay.png`
